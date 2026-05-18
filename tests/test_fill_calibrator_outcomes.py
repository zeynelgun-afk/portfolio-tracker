"""scripts/fill_calibrator_outcomes.py için testler.

Faz 2 — C-1: outcome doldurma altyapısı.

KAPSAM:
    - _parse_ts: geçerli/bozuk
    - find_nearest_trading_day: tam tarih / hafta sonu sonrası / range dışı
    - compute_outcome_for_event: pozitif/negatif outcome, fiyat 0/None
    - fill_event_outcomes:
        * Tüm horizon'lar olgun → 3 outcome dolar
        * Henüz olgun değil → skipped listede
        * Zaten dolu olan tekrar yazılmaz
        * FMP veri yok → skipped
    - run_fill:
        * Boş tracker → 0 fill
        * Tek event olgun → outcome'lar yazılır
        * Dry-run → tracker değişmez
        * Bozuk event → errors listede
"""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "fill_calibrator_outcomes.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "fill_calibrator_outcomes", _SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_synthetic_rows(start_date: datetime, days: int,
                          start_price: float = 100,
                          daily_pct: float = 0.005) -> list[dict]:
    """Hafta sonu hariç N gün sentetik price history."""
    rows = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        if d.weekday() >= 5:  # cumartesi/pazar
            continue
        price = start_price * (1 + daily_pct * i)
        rows.append({"date": d.strftime("%Y-%m-%d"),
                     "adjClose": round(price, 2)})
    return rows


# ── _parse_ts ──────────────────────────────────────────────────────────────────


class TestParseTs:
    def test_valid_iso(self):
        fc = _load_script()
        ts = fc._parse_ts("2026-05-17T12:00:00+00:00")
        assert ts is not None
        assert ts.year == 2026

    def test_z_suffix(self):
        fc = _load_script()
        ts = fc._parse_ts("2026-05-17T12:00:00Z")
        assert ts is not None

    def test_invalid_returns_none(self):
        fc = _load_script()
        assert fc._parse_ts("not-a-date") is None
        assert fc._parse_ts(None) is None
        assert fc._parse_ts(123) is None


# ── find_nearest_trading_day ───────────────────────────────────────────────────


class TestFindNearest:
    def test_exact_match(self):
        fc = _load_script()
        rows = [
            {"date": "2026-05-15", "adjClose": 100},
            {"date": "2026-05-18", "adjClose": 102},
        ]
        target = datetime(2026, 5, 15, tzinfo=timezone.utc)
        result = fc.find_nearest_trading_day(rows, target)
        assert result["date"] == "2026-05-15"

    def test_weekend_returns_next_trading_day(self):
        fc = _load_script()
        rows = [
            {"date": "2026-05-15", "adjClose": 100},  # Cuma
            {"date": "2026-05-18", "adjClose": 102},  # Pazartesi
        ]
        # 2026-05-16 = Cumartesi
        target = datetime(2026, 5, 16, tzinfo=timezone.utc)
        result = fc.find_nearest_trading_day(rows, target)
        assert result["date"] == "2026-05-18"

    def test_no_row_after_target(self):
        fc = _load_script()
        rows = [{"date": "2026-05-15", "adjClose": 100}]
        target = datetime(2026, 6, 1, tzinfo=timezone.utc)
        assert fc.find_nearest_trading_day(rows, target) is None


# ── compute_outcome_for_event ──────────────────────────────────────────────────


class TestComputeOutcome:
    def test_positive_outcome(self):
        fc = _load_script()
        event_date = datetime(2026, 4, 14, tzinfo=timezone.utc)  # Salı
        event = {"ts": event_date.isoformat(), "candidate_symbol": "TEST"}
        rows = _make_synthetic_rows(event_date - timedelta(days=3), 40,
                                     start_price=100, daily_pct=0.005)

        out = fc.compute_outcome_for_event(event, 7, rows)
        assert out is not None
        assert out > 0  # yükseliş

    def test_negative_outcome(self):
        fc = _load_script()
        event_date = datetime(2026, 4, 14, tzinfo=timezone.utc)
        event = {"ts": event_date.isoformat(), "candidate_symbol": "TEST"}
        rows = _make_synthetic_rows(event_date - timedelta(days=3), 40,
                                     start_price=100, daily_pct=-0.005)  # düşüş

        out = fc.compute_outcome_for_event(event, 7, rows)
        assert out is not None
        assert out < 0

    def test_missing_t0(self):
        fc = _load_script()
        event_date = datetime(2026, 4, 14, tzinfo=timezone.utc)
        event = {"ts": event_date.isoformat(), "candidate_symbol": "TEST"}
        # rows event_date sonrası yok
        rows = [{"date": "2026-01-01", "adjClose": 100}]
        assert fc.compute_outcome_for_event(event, 7, rows) is None

    def test_zero_price_returns_none(self):
        fc = _load_script()
        event_date = datetime(2026, 4, 14, tzinfo=timezone.utc)
        event = {"ts": event_date.isoformat(), "candidate_symbol": "TEST"}
        rows = [
            {"date": "2026-04-14", "adjClose": 0},  # sıfır fiyat
            {"date": "2026-04-21", "adjClose": 100},
        ]
        assert fc.compute_outcome_for_event(event, 7, rows) is None

    def test_invalid_ts_returns_none(self):
        fc = _load_script()
        event = {"ts": "bad", "candidate_symbol": "X"}
        assert fc.compute_outcome_for_event(event, 7, []) is None


# ── fill_event_outcomes ────────────────────────────────────────────────────────


class TestFillEventOutcomes:
    def test_all_mature_horizons(self, monkeypatch):
        """Event 35g önce ise tüm 3 horizon olgun."""
        fc = _load_script()
        event_date = datetime(2026, 4, 5, tzinfo=timezone.utc)
        event = {
            "ts": event_date.isoformat(),
            "candidate_symbol": "TEST",
            "outcome_7d": None, "outcome_14d": None, "outcome_30d": None,
        }

        # Mock FMP fetch
        rows = _make_synthetic_rows(event_date - timedelta(days=3), 40,
                                     start_price=100, daily_pct=0.01)
        monkeypatch.setattr(fc, "fetch_price_history",
                            lambda s, f, t: rows)

        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        result = fc.fill_event_outcomes(event, now, dry_run=False)

        assert set(result["filled"]) == {"outcome_7d", "outcome_14d", "outcome_30d"}
        assert event["outcome_7d"] is not None
        assert event["outcome_14d"] is not None
        assert event["outcome_30d"] is not None

    def test_only_7d_mature(self, monkeypatch):
        """Event 10g önce ise sadece outcome_7d olgun."""
        fc = _load_script()
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        event_date = now - timedelta(days=10)
        event = {
            "ts": event_date.isoformat(),
            "candidate_symbol": "TEST",
            "outcome_7d": None, "outcome_14d": None, "outcome_30d": None,
        }

        rows = _make_synthetic_rows(event_date - timedelta(days=3), 20,
                                     start_price=100, daily_pct=0.005)
        monkeypatch.setattr(fc, "fetch_price_history", lambda s, f, t: rows)

        result = fc.fill_event_outcomes(event, now)
        assert result["filled"] == ["outcome_7d"]
        # 14d/30d skip notlu
        skipped_str = " ".join(result["skipped"])
        assert "outcome_14d" in skipped_str
        assert "outcome_30d" in skipped_str
        assert event["outcome_14d"] is None

    def test_already_filled_skipped(self, monkeypatch):
        """outcome_7d zaten dolu → tekrar yazılmaz."""
        fc = _load_script()
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        event_date = now - timedelta(days=35)
        event = {
            "ts": event_date.isoformat(),
            "candidate_symbol": "TEST",
            "outcome_7d": 0.05,  # zaten dolu
            "outcome_14d": None, "outcome_30d": None,
        }
        rows = _make_synthetic_rows(event_date - timedelta(days=3), 40,
                                     start_price=100, daily_pct=0.01)
        monkeypatch.setattr(fc, "fetch_price_history", lambda s, f, t: rows)

        result = fc.fill_event_outcomes(event, now)
        # outcome_7d filled listesinde olmamalı (zaten doluydu)
        assert "outcome_7d" not in result["filled"]
        # Mevcut değer korundu
        assert event["outcome_7d"] == 0.05
        # Diğer ikisi dolduruldu
        assert "outcome_14d" in result["filled"]
        assert "outcome_30d" in result["filled"]

    def test_fmp_empty_skipped(self, monkeypatch):
        """FMP boş döndürürse outcome'lar skip edilir."""
        fc = _load_script()
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        event_date = now - timedelta(days=35)
        event = {
            "ts": event_date.isoformat(),
            "candidate_symbol": "TEST",
            "outcome_7d": None, "outcome_14d": None, "outcome_30d": None,
        }
        monkeypatch.setattr(fc, "fetch_price_history", lambda s, f, t: [])

        result = fc.fill_event_outcomes(event, now)
        assert result["filled"] == []
        assert any("FMP veri yok" in s for s in result["skipped"])

    def test_invalid_ts_skipped(self):
        fc = _load_script()
        event = {"ts": "bad", "candidate_symbol": "X"}
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        result = fc.fill_event_outcomes(event, now)
        assert result["filled"] == []
        assert "invalid ts" in result["skipped"]

    def test_dry_run_no_write(self, monkeypatch):
        """dry_run=True → event[field] güncellenmez."""
        fc = _load_script()
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        event_date = now - timedelta(days=35)
        event = {
            "ts": event_date.isoformat(),
            "candidate_symbol": "TEST",
            "outcome_7d": None, "outcome_14d": None, "outcome_30d": None,
        }
        rows = _make_synthetic_rows(event_date - timedelta(days=3), 40,
                                     start_price=100, daily_pct=0.01)
        monkeypatch.setattr(fc, "fetch_price_history", lambda s, f, t: rows)

        result = fc.fill_event_outcomes(event, now, dry_run=True)
        # filled listede ama event'te değer YAZILMAMIŞ
        assert len(result["filled"]) == 3
        assert event["outcome_7d"] is None  # dry-run
        assert event["outcome_14d"] is None
        assert event["outcome_30d"] is None


# ── run_fill ───────────────────────────────────────────────────────────────────


class TestRunFill:
    def test_empty_tracker(self, tmp_path, monkeypatch):
        fc = _load_script()
        monkeypatch.setattr(fc, "_TRACKER_PATH", tmp_path / "missing.json")

        result = fc.run_fill()
        assert result["total_events"] == 0
        assert result["outcomes_filled"] == 0

    def test_no_events(self, tmp_path, monkeypatch):
        fc = _load_script()
        path = tmp_path / "tracker.json"
        path.write_text(json.dumps({"events": []}))
        monkeypatch.setattr(fc, "_TRACKER_PATH", path)

        result = fc.run_fill()
        assert result["total_events"] == 0

    def test_single_mature_event(self, tmp_path, monkeypatch):
        fc = _load_script()
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        event_date = now - timedelta(days=35)

        tracker = {
            "_version": "v1",
            "events": [{
                "id": "evt1",
                "ts": event_date.isoformat(),
                "candidate_symbol": "TEST",
                "applied_flag": "pm_confirm",
                "outcome_7d": None, "outcome_14d": None, "outcome_30d": None,
            }]
        }
        path = tmp_path / "tracker.json"
        path.write_text(json.dumps(tracker))
        monkeypatch.setattr(fc, "_TRACKER_PATH", path)

        rows = _make_synthetic_rows(event_date - timedelta(days=3), 40,
                                     start_price=100, daily_pct=0.01)
        monkeypatch.setattr(fc, "fetch_price_history", lambda s, f, t: rows)

        result = fc.run_fill(now=now)
        assert result["total_events"] == 1
        assert result["events_processed"] == 1
        assert result["outcomes_filled"] == 3

        # Tracker disk'e yazıldı
        updated = json.loads(path.read_text())
        assert updated["events"][0]["outcome_7d"] is not None
        assert updated["events"][0]["outcome_30d"] is not None

    def test_dry_run_no_disk_write(self, tmp_path, monkeypatch):
        fc = _load_script()
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        event_date = now - timedelta(days=35)

        tracker = {
            "_version": "v1",
            "events": [{
                "id": "evt1",
                "ts": event_date.isoformat(),
                "candidate_symbol": "TEST",
                "outcome_7d": None, "outcome_14d": None, "outcome_30d": None,
            }]
        }
        path = tmp_path / "tracker.json"
        path.write_text(json.dumps(tracker))
        monkeypatch.setattr(fc, "_TRACKER_PATH", path)

        rows = _make_synthetic_rows(event_date - timedelta(days=3), 40,
                                     start_price=100, daily_pct=0.01)
        monkeypatch.setattr(fc, "fetch_price_history", lambda s, f, t: rows)

        result = fc.run_fill(now=now, dry_run=True)
        assert result["outcomes_filled"] == 3

        # Disk'te outcome'lar HÂLÂ None
        on_disk = json.loads(path.read_text())
        assert on_disk["events"][0]["outcome_7d"] is None

    def test_invalid_event_in_errors(self, tmp_path, monkeypatch):
        """Listede dict olmayan element error olarak kaydedilir."""
        fc = _load_script()
        tracker = {"events": ["not-a-dict", {"ts": "bad", "candidate_symbol": "X"}]}
        path = tmp_path / "tracker.json"
        path.write_text(json.dumps(tracker))
        monkeypatch.setattr(fc, "_TRACKER_PATH", path)

        result = fc.run_fill()
        # İlk eleman dict değil → errors'a girer
        assert any("dict değil" in e for e in result["errors"])


# ── main() ─────────────────────────────────────────────────────────────────────


class TestMain:
    def test_main_dry_run_rc_zero(self, tmp_path, monkeypatch):
        fc = _load_script()
        monkeypatch.setattr(fc, "_TRACKER_PATH", tmp_path / "missing.json")
        rc = fc.main(["--dry-run"])
        assert rc == 0
