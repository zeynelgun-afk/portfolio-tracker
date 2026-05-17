"""agent/reports/weekly.py Polymarket Pulse bölümü testleri.

Faz 2 — Adım 12: Pazar raporuna kalibratör özet bölümü.

KAPSAM:
    - _load_calibrator_events: dosya yok / bozuk / geçerli
    - _load_calibrator_started_at: ts parse
    - _filter_events_last_7d: cutoff doğru
    - _build_polymarket_pulse_section:
        * Boş events → "henüz event yok" notu
        * Son 7g event yok ama eskileri var → uygun mesaj
        * Tek confirm event → header + tema
        * Tek conflict event → header + tema
        * Çoklu event → counts doğru
        * Theme counts doğru sıralı
        * Delta tablosu büyükten küçüğe sıralı
        * Phase 10 progress satırı
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.reports import weekly


def _make_event(symbol: str, theme: str, flag: str, delta: float, mult: float,
                ts: datetime, src: str = "thematic") -> dict:
    return {
        "id": f"cal_evt_{symbol}",
        "ts": ts.isoformat(),
        "candidate_symbol": symbol,
        "candidate_source": src,
        "candidate_original_score": 0.5,
        "applied_flag": flag,
        "applied_multiplier": mult,
        "matched_theme": theme,
        "matched_side": "negative" if flag.startswith("pm_conflict") else "positive",
        "market_slug": "test-market",
        "market_delta_24h": delta,
        "outcome_7d": None,
        "outcome_14d": None,
        "outcome_30d": None,
    }


def _write_tracker(tmp_path: Path, events: list[dict],
                    started_at: datetime | None = None) -> Path:
    """Test için sahte tracker dosyası yaz, path döndür."""
    path = tmp_path / "polymarket_calibrator_performance.json"
    data: dict = {"_version": "v1", "events": events}
    if started_at:
        data["_started_at"] = started_at.isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── _load_calibrator_events ────────────────────────────────────────────────────


class TestLoadEvents:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "nonexistent.json")
        assert weekly._load_calibrator_events() == []

    def test_corrupt_json_returns_empty(self, tmp_path, monkeypatch):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json")
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)
        assert weekly._load_calibrator_events() == []

    def test_missing_events_key_returns_empty(self, tmp_path, monkeypatch):
        path = tmp_path / "noevents.json"
        path.write_text(json.dumps({"_version": "v1"}))
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)
        assert weekly._load_calibrator_events() == []

    def test_valid_events_loaded(self, tmp_path, monkeypatch):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [_make_event("TSM", "ct", "pm_conflict", 0.15, 0.75, now)]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)
        loaded = weekly._load_calibrator_events()
        assert len(loaded) == 1
        assert loaded[0]["candidate_symbol"] == "TSM"

    def test_events_non_list_returns_empty(self, tmp_path, monkeypatch):
        path = tmp_path / "weird.json"
        path.write_text(json.dumps({"events": "not-a-list"}))
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)
        assert weekly._load_calibrator_events() == []


# ── _load_calibrator_started_at ────────────────────────────────────────────────


class TestLoadStartedAt:
    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "missing.json")
        assert weekly._load_calibrator_started_at() is None

    def test_missing_started_at_field(self, tmp_path, monkeypatch):
        path = _write_tracker(tmp_path, [])
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)
        assert weekly._load_calibrator_started_at() is None

    def test_valid_started_at(self, tmp_path, monkeypatch):
        start = datetime(2026, 5, 1, tzinfo=timezone.utc)
        path = _write_tracker(tmp_path, [], started_at=start)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)
        loaded = weekly._load_calibrator_started_at()
        assert loaded == start

    def test_invalid_started_at_format(self, tmp_path, monkeypatch):
        path = tmp_path / "bad-ts.json"
        path.write_text(json.dumps({
            "events": [],
            "_started_at": "not-a-date",
        }))
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)
        assert weekly._load_calibrator_started_at() is None


# ── _filter_events_last_7d ─────────────────────────────────────────────────────


class TestFilterRecent:
    def test_filter_cutoff(self):
        now = datetime(2026, 5, 17, 12, 0, tzinfo=timezone.utc)
        events = [
            _make_event("OLD", "t1", "pm_confirm", 0.1, 1.2,
                        now - timedelta(days=8)),  # 8g önce - excluded
            _make_event("EDGE", "t1", "pm_confirm", 0.1, 1.2,
                        now - timedelta(days=7, hours=-1)),  # ~6.96g - included
            _make_event("NEW", "t1", "pm_confirm", 0.1, 1.2,
                        now - timedelta(hours=1)),  # 1h - included
        ]
        recent = weekly._filter_events_last_7d(events, now)
        symbols = [e["candidate_symbol"] for e in recent]
        assert "OLD" not in symbols
        assert "NEW" in symbols

    def test_invalid_ts_skipped(self):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            {"ts": "garbage", "candidate_symbol": "BAD"},
            {"ts": now.isoformat(), "candidate_symbol": "GOOD"},
            {"candidate_symbol": "NO_TS"},  # ts yok
        ]
        recent = weekly._filter_events_last_7d(events, now)
        symbols = [e["candidate_symbol"] for e in recent]
        assert symbols == ["GOOD"]

    def test_non_dict_skipped(self):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            "not-a-dict",
            _make_event("GOOD", "t1", "pm_confirm", 0.1, 1.2, now),
        ]
        recent = weekly._filter_events_last_7d(events, now)
        assert len(recent) == 1


# ── _build_polymarket_pulse_section ────────────────────────────────────────────


class TestBuildPulseSection:
    def test_empty_tracker(self, tmp_path, monkeypatch):
        """Hiç event yok → 'henüz event yok' notu."""
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "missing.json")
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        assert "Prediction Markets Pulse" in text
        assert "Henüz kalibratör event" in text

    def test_no_recent_events(self, tmp_path, monkeypatch):
        """Eski event'ler var ama son 7g yok."""
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        old_event = _make_event("OLD", "t1", "pm_confirm", 0.1, 1.2,
                                now - timedelta(days=30))
        path = _write_tracker(tmp_path, [old_event])
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        assert "Son 7 günde kalibratör event'i yok" in text

    def test_single_confirm_event(self, tmp_path, monkeypatch):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("LMT", "defense_2026", "pm_confirm", 0.12, 1.20,
                        now - timedelta(hours=12)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        assert "1 doğrulama" in text
        assert "0 çelişki" in text
        assert "defense_2026" in text
        assert "LMT" in text
        assert "🟢" in text  # confirm icon
        assert "1.20x" in text
        assert "+12.0pp" in text

    def test_single_conflict_event(self, tmp_path, monkeypatch):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("TSM", "china_taiwan", "pm_conflict", 0.15, 0.75,
                        now - timedelta(hours=4)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        assert "0 doğrulama" in text
        assert "1 çelişki" in text
        assert "🔴" in text  # conflict icon
        assert "0.75x" in text

    def test_mixed_events_counts(self, tmp_path, monkeypatch):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("LMT", "t1", "pm_confirm", 0.1, 1.20,
                        now - timedelta(days=1)),
            _make_event("RTX", "t1", "pm_confirm_weak", 0.05, 1.10,
                        now - timedelta(days=2)),
            _make_event("TSM", "t2", "pm_conflict", 0.15, 0.75,
                        now - timedelta(days=3)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        assert "Toplam event:** 3" in text
        assert "2 doğrulama, 1 çelişki" in text

    def test_theme_counts_sorted(self, tmp_path, monkeypatch):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        # theme_a 3 kez, theme_b 1 kez
        events = [
            _make_event("A1", "theme_a", "pm_confirm", 0.1, 1.2,
                        now - timedelta(hours=i))
            for i in range(3)
        ] + [
            _make_event("B1", "theme_b", "pm_confirm", 0.1, 1.2,
                        now - timedelta(hours=4)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        # theme_a önce gelmeli (3 event)
        idx_a = text.find("theme_a")
        idx_b = text.find("theme_b")
        assert idx_a < idx_b
        assert "theme_a`: 3 event" in text
        assert "theme_b`: 1 event" in text

    def test_delta_table_sorted_by_abs_value(self, tmp_path, monkeypatch):
        """En sert hareketler (abs delta) önce gösterilir."""
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("SMALL", "t1", "pm_confirm_weak", 0.04, 1.1,
                        now - timedelta(hours=1)),
            _make_event("HUGE", "t1", "pm_conflict", 0.20, 0.75,
                        now - timedelta(hours=2)),
            _make_event("MED", "t1", "pm_confirm", 0.10, 1.2,
                        now - timedelta(hours=3)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        # HUGE (0.20) önce, sonra MED (0.10), sonra SMALL (0.04)
        idx_huge = text.find("HUGE")
        idx_med = text.find("MED")
        idx_small = text.find("SMALL")
        assert idx_huge < idx_med < idx_small

    def test_phase10_progress_line(self, tmp_path, monkeypatch):
        """Tracker'da _started_at varsa progress satırı eklenir."""
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        start = now - timedelta(days=10)
        events = [
            _make_event("LMT", "t1", "pm_confirm", 0.1, 1.2,
                        now - timedelta(hours=1)),
        ]
        path = _write_tracker(tmp_path, events, started_at=start)
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        assert "Tracker:" in text
        assert "10.0 gün" in text
        assert "Phase 10" in text
        # 10/30 = 33%
        assert "33%" in text

    def test_started_at_missing_no_progress_line(self, tmp_path, monkeypatch):
        """_started_at yoksa progress satırı gösterilmez."""
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("LMT", "t1", "pm_confirm", 0.1, 1.2,
                        now - timedelta(hours=1)),
        ]
        path = _write_tracker(tmp_path, events)  # started_at yok
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH", path)

        lines = weekly._build_polymarket_pulse_section(now)
        text = "\n".join(lines)
        assert "Tracker:" not in text


# ── render_report entegrasyonu ─────────────────────────────────────────────────


class TestRenderReportIntegration:
    def test_pulse_section_included(self, tmp_path, monkeypatch):
        """render_report çıktısında Section 6 görünüyor."""
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "missing.json")

        # render_report minimum input
        report = weekly.render_report(
            macro_w={}, sector_w={}, portfolio_w={},
            closed_week=[], positions=[],
            today="2026-05-17",
        )
        # Pulse bölüm başlığı raporda olmalı
        assert "6. Prediction Markets Pulse" in report
        # Boş tracker → "henüz event yok" notu
        assert "Henüz kalibratör event" in report

    def test_pulse_section_order(self, tmp_path, monkeypatch):
        """Section 6 raporun son bölümü, "Stops within 5%" sonrasında."""
        monkeypatch.setattr(weekly, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "missing.json")

        report = weekly.render_report(
            macro_w={}, sector_w={}, portfolio_w={},
            closed_week=[], positions=[],
            today="2026-05-17",
        )
        idx_macro = report.find("## 0. Macro week")
        idx_pulse = report.find("## 6. Prediction Markets")
        assert idx_macro < idx_pulse  # Section 6 sonda
