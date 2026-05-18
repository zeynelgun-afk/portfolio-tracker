"""agent/reports/stats.py hit rate hesaplama testleri.

Faz 2 — C-2: outcome → hit rate metrikleri.

KAPSAM:
    - _is_hit semantiği (confirm hit, conflict hit, miss durumları)
    - _calc_hit_rates per-flag/source/theme/overall
    - query_calibrator_stats outcome_status mantığı:
        * pending_phase10 (outcome yok)
        * partial (outcome var ama <80%)
        * phase10_ready (≥80% outcome dolu)
    - format_calibrator_section hit rate tablo render
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.reports import stats


def _make_event(symbol: str, theme: str, flag: str,
                ts: datetime, src: str = "thematic",
                outcome_7d: float | None = None,
                outcome_14d: float | None = None,
                outcome_30d: float | None = None) -> dict:
    return {
        "id": f"evt_{symbol}",
        "ts": ts.isoformat(),
        "candidate_symbol": symbol,
        "candidate_source": src,
        "applied_flag": flag,
        "applied_multiplier": 1.20 if "confirm" in flag else 0.75,
        "matched_theme": theme,
        "matched_side": "negative" if "conflict" in flag else "positive",
        "market_slug": "test",
        "market_delta_24h": 0.1,
        "outcome_7d": outcome_7d,
        "outcome_14d": outcome_14d,
        "outcome_30d": outcome_30d,
    }


def _write_tracker(tmp_path: Path, events: list[dict],
                    started_at: datetime | None = None) -> Path:
    path = tmp_path / "tracker.json"
    data: dict = {"_version": "v1", "events": events}
    if started_at:
        data["_started_at"] = started_at.isoformat()
    path.write_text(json.dumps(data))
    return path


# ── _is_hit ────────────────────────────────────────────────────────────────────


class TestIsHit:
    def test_confirm_positive_outcome_is_hit(self):
        assert stats._is_hit("pm_confirm", 0.05) is True
        assert stats._is_hit("pm_confirm_weak", 0.02) is True

    def test_confirm_negative_outcome_is_miss(self):
        assert stats._is_hit("pm_confirm", -0.05) is False
        assert stats._is_hit("pm_confirm_weak", -0.02) is False

    def test_confirm_zero_outcome_is_miss(self):
        # 0 → confirm için MISS (yükselmedi)
        assert stats._is_hit("pm_confirm", 0.0) is False

    def test_conflict_negative_outcome_is_hit(self):
        assert stats._is_hit("pm_conflict", -0.05) is True
        assert stats._is_hit("pm_conflict_weak", -0.02) is True

    def test_conflict_positive_outcome_is_miss(self):
        assert stats._is_hit("pm_conflict", 0.05) is False
        assert stats._is_hit("pm_conflict_weak", 0.02) is False

    def test_none_outcome_returns_none(self):
        assert stats._is_hit("pm_confirm", None) is None
        assert stats._is_hit("pm_conflict", None) is None

    def test_unknown_flag_returns_none(self):
        assert stats._is_hit("unknown_flag", 0.05) is None
        assert stats._is_hit(None, 0.05) is None

    def test_non_numeric_outcome_returns_none(self):
        assert stats._is_hit("pm_confirm", "not-a-number") is None


# ── _calc_hit_rates ────────────────────────────────────────────────────────────


class TestCalcHitRates:
    def test_empty_events(self):
        result = stats._calc_hit_rates([])
        # Hiç event yok → tüm bucket boş, ama overall structure var
        assert result["by_flag_horizon"] == {}
        assert result["by_source"] == {}
        assert result["by_theme"] == {}
        assert result["overall"]["outcome_7d"]["total"] == 0
        assert result["overall"]["outcome_7d"]["rate_pct"] is None

    def test_single_confirm_hit(self):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("LMT", "defense", "pm_confirm", now - timedelta(days=15),
                        src="thematic", outcome_7d=0.05),
        ]
        result = stats._calc_hit_rates(events)
        # Overall
        assert result["overall"]["outcome_7d"]["hits"] == 1
        assert result["overall"]["outcome_7d"]["total"] == 1
        assert result["overall"]["outcome_7d"]["rate_pct"] == 100.0
        # Per-flag
        assert result["by_flag_horizon"]["pm_confirm"]["outcome_7d"]["hits"] == 1
        # Per-source
        assert result["by_source"]["thematic"]["outcome_7d"]["hits"] == 1
        # Per-theme
        assert result["by_theme"]["defense"]["outcome_7d"]["hits"] == 1

    def test_mixed_hits_and_misses(self):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            # 2 confirm hit, 1 confirm miss
            _make_event("A", "t1", "pm_confirm", now - timedelta(days=15),
                        outcome_7d=0.05),  # HIT
            _make_event("B", "t1", "pm_confirm", now - timedelta(days=15),
                        outcome_7d=0.03),  # HIT
            _make_event("C", "t1", "pm_confirm", now - timedelta(days=15),
                        outcome_7d=-0.02),  # MISS
            # 1 conflict hit, 1 conflict miss
            _make_event("D", "t1", "pm_conflict", now - timedelta(days=15),
                        outcome_7d=-0.04),  # HIT
            _make_event("E", "t1", "pm_conflict", now - timedelta(days=15),
                        outcome_7d=0.02),  # MISS
        ]
        result = stats._calc_hit_rates(events)
        # Overall: 3 hit / 5 total = 60%
        assert result["overall"]["outcome_7d"]["hits"] == 3
        assert result["overall"]["outcome_7d"]["total"] == 5
        assert result["overall"]["outcome_7d"]["rate_pct"] == 60.0
        # pm_confirm: 2/3
        assert result["by_flag_horizon"]["pm_confirm"]["outcome_7d"]["hits"] == 2
        assert result["by_flag_horizon"]["pm_confirm"]["outcome_7d"]["rate_pct"] == pytest.approx(66.7, abs=0.1)
        # pm_conflict: 1/2
        assert result["by_flag_horizon"]["pm_conflict"]["outcome_7d"]["hits"] == 1
        assert result["by_flag_horizon"]["pm_conflict"]["outcome_7d"]["rate_pct"] == 50.0

    def test_per_horizon_independent(self):
        """outcome_7d dolu ama outcome_14d None → 7d sayılır, 14d sayılmaz."""
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("A", "t1", "pm_confirm", now - timedelta(days=10),
                        outcome_7d=0.05, outcome_14d=None),
        ]
        result = stats._calc_hit_rates(events)
        # 7d sayılır
        assert result["overall"]["outcome_7d"]["total"] == 1
        # 14d sayılmaz (None)
        assert result["overall"]["outcome_14d"]["total"] == 0

    def test_unknown_flag_ignored(self):
        now = datetime(2026, 5, 17, tzinfo=timezone.utc)
        events = [
            _make_event("A", "t1", "weird_flag", now - timedelta(days=10),
                        outcome_7d=0.05),
        ]
        result = stats._calc_hit_rates(events)
        # Bilinmeyen flag → sayılmaz
        assert result["overall"]["outcome_7d"]["total"] == 0


# ── query_calibrator_stats hit_rates entegrasyonu ──────────────────────────────


class TestQueryStatsHitRates:
    def test_pending_phase10_no_hit_rates(self, tmp_path, monkeypatch):
        """Outcome yok → hit_rates None, status pending_phase10."""
        now = datetime.now(timezone.utc)
        events = [
            _make_event("A", "t1", "pm_confirm", now - timedelta(days=2)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=30)
        assert result["outcome_status"] == "pending_phase10"
        assert result["hit_rates"] is None

    def test_partial_status_under_80_pct(self, tmp_path, monkeypatch):
        """%80'in altında outcome dolu → partial."""
        now = datetime.now(timezone.utc)
        events = [
            # 5 olgun 7d event, 2'sinin outcome_7d dolu (40%)
            _make_event("A", "t1", "pm_confirm", now - timedelta(days=10),
                        outcome_7d=0.05),
            _make_event("B", "t1", "pm_confirm", now - timedelta(days=10),
                        outcome_7d=0.03),
            _make_event("C", "t1", "pm_confirm", now - timedelta(days=10)),
            _make_event("D", "t1", "pm_confirm", now - timedelta(days=10)),
            _make_event("E", "t1", "pm_confirm", now - timedelta(days=10)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=30)
        assert result["outcome_status"] == "partial"
        # 2 event'in outcome'u dolu → hit_rates hesaplanır
        assert result["hit_rates"] is not None

    def test_phase10_ready_status(self, tmp_path, monkeypatch):
        """≥80% outcome dolu → phase10_ready."""
        now = datetime.now(timezone.utc)
        events = [
            _make_event(f"X{i}", "t1", "pm_confirm",
                        now - timedelta(days=10),
                        outcome_7d=0.05) for i in range(5)
        ]
        # 5/5 = 100% → phase10_ready
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=30)
        assert result["outcome_status"] == "phase10_ready"
        assert result["hit_rates"] is not None
        # Hit rate %100
        assert result["hit_rates"]["overall"]["outcome_7d"]["rate_pct"] == 100.0


# ── format_calibrator_section hit rate render ──────────────────────────────────


class TestFormatHitRates:
    def test_pending_no_hit_rate_tables(self):
        section = stats.format_calibrator_section({
            "total_events": 1,
            "by_flag": {"pm_confirm": 1},
            "by_multiplier": {"1.20x": 1},
            "by_source": {"thematic": 1},
            "top_themes": [],
            "top_symbols": [],
            "days_collected": 5.0,
            "phase10_progress_pct": 16.7,
            "outcome_status": "pending_phase10",
            "hit_rates": None,
        })
        text = "\n".join(section)
        assert "Phase 10'da hesaplanacak" in text
        # Hit rate tabloları YOK
        assert "Genel Hit Rate" not in text

    def test_phase10_ready_full_tables(self):
        hit_rates = {
            "overall": {
                "outcome_7d": {"hits": 6, "total": 10, "rate_pct": 60.0},
                "outcome_14d": {"hits": 4, "total": 5, "rate_pct": 80.0},
                "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
            },
            "by_flag_horizon": {
                "pm_confirm": {
                    "outcome_7d": {"hits": 4, "total": 5, "rate_pct": 80.0},
                    "outcome_14d": {"hits": 0, "total": 0, "rate_pct": None},
                    "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
                },
                "pm_conflict": {
                    "outcome_7d": {"hits": 2, "total": 5, "rate_pct": 40.0},
                    "outcome_14d": {"hits": 0, "total": 0, "rate_pct": None},
                    "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
                },
            },
            "by_source": {
                "thematic": {
                    "outcome_7d": {"hits": 5, "total": 7, "rate_pct": 71.4},
                    "outcome_14d": {"hits": 0, "total": 0, "rate_pct": None},
                    "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
                },
            },
            "by_theme": {
                "defense": {
                    "outcome_7d": {"hits": 3, "total": 4, "rate_pct": 75.0},
                    "outcome_14d": {"hits": 0, "total": 0, "rate_pct": None},
                    "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
                },
            },
        }

        section = stats.format_calibrator_section({
            "total_events": 10,
            "by_flag": {"pm_confirm": 5, "pm_conflict": 5},
            "by_multiplier": {"1.20x": 5, "0.75x": 5},
            "by_source": {"thematic": 7, "fair_value": 3},
            "top_themes": [("defense", 4)],
            "top_symbols": [("LMT", 3)],
            "days_collected": 30.0,
            "phase10_progress_pct": 100.0,
            "outcome_status": "phase10_ready",
            "hit_rates": hit_rates,
        })
        text = "\n".join(section)

        # 4 hit rate tablosu
        assert "Genel Hit Rate" in text
        assert "Bayrak Bazında Hit Rate" in text
        assert "Kaynak Bazında Hit Rate" in text
        assert "Tema Bazında Hit Rate" in text

        # Bazı somut değerler
        assert "60.0%" in text  # overall 7d
        assert "80.0%" in text  # pm_confirm 7d
        assert "phase10_ready" in text

    def test_partial_status_message(self):
        section = stats.format_calibrator_section({
            "total_events": 5,
            "by_flag": {"pm_confirm": 5},
            "by_multiplier": {"1.20x": 5},
            "by_source": {"thematic": 5},
            "top_themes": [],
            "top_symbols": [],
            "days_collected": 35.0,
            "phase10_progress_pct": 100.0,
            "outcome_status": "partial",
            "hit_rates": {
                "overall": {
                    "outcome_7d": {"hits": 1, "total": 2, "rate_pct": 50.0},
                    "outcome_14d": {"hits": 0, "total": 0, "rate_pct": None},
                    "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
                },
                "by_flag_horizon": {},
                "by_source": {},
                "by_theme": {},
            },
        })
        text = "\n".join(section)
        # Partial mesajı
        assert "outcome doldurma sürüyor" in text
        # Yine de hit rate tablosu görünür
        assert "Genel Hit Rate" in text
