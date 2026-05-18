"""agent/reports/stats.py adaptive multiplier testleri.

Faz 2 — C-3: passive adaptive multiplier önerileri.

KAPSAM:
    - _suggest_multiplier:
        * insufficient: sample < 10 veya hit_rate None
        * unknown flag → insufficient
        * Yüksek hit rate → effect büyür (suggested 1'den uzaklaşır)
        * Düşük hit rate → effect küçülür (suggested 1'e yaklaşır)
        * pm_conflict (negative effect) için aynı mantık
        * Clamp [0.50, 1.50]
        * Confidence kademeleri (low/medium/high)
        * Note metni delta'ya göre değişir
    - _calc_adaptive_suggestions:
        * 4 bayrak için sıralı liste
        * hit_rates yoksa boş liste
    - query_calibrator_stats:
        * adaptive_suggestions return alanı dolu (hit_rates varsa)
        * boş tracker → []
    - format_calibrator_section:
        * Tablo render — başlık + 4 satır
        * Insufficient için "—" gösterimi
        * Yorum metinleri (high confidence vs low)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.reports import stats


# ── _suggest_multiplier ────────────────────────────────────────────────────────


class TestSuggestMultiplier:
    def test_insufficient_low_sample(self):
        r = stats._suggest_multiplier("pm_confirm", hit_rate_pct=80.0,
                                       sample_size=5)
        assert r["confidence"] == "insufficient"
        assert r["suggested"] is None
        assert r["delta"] is None
        # current hâlâ tablodan
        assert r["current"] == 1.20

    def test_insufficient_none_hit_rate(self):
        r = stats._suggest_multiplier("pm_confirm", hit_rate_pct=None,
                                       sample_size=30)
        assert r["confidence"] == "insufficient"
        assert r["suggested"] is None

    def test_unknown_flag(self):
        r = stats._suggest_multiplier("weird_flag", hit_rate_pct=80.0,
                                       sample_size=30)
        assert r["confidence"] == "insufficient"
        assert r["current"] is None

    def test_high_hit_rate_amplifies_positive_effect(self):
        """pm_confirm hit %80 → effect büyür, çarpan 1.20'den 1.27'ye."""
        r = stats._suggest_multiplier("pm_confirm", hit_rate_pct=80.0,
                                       sample_size=30)
        # effect = 0.20, suggested_effect = 0.20 * 80/60 = 0.267
        # suggested = 1.267
        assert r["suggested"] == pytest.approx(1.27, abs=0.01)
        assert r["delta"] > 0
        assert r["confidence"] == "medium"

    def test_low_hit_rate_dampens_positive_effect(self):
        """pm_confirm hit %30 → effect azalır, çarpan 1.20'den 1.10'a."""
        r = stats._suggest_multiplier("pm_confirm", hit_rate_pct=30.0,
                                       sample_size=30)
        # effect = 0.20 * 30/60 = 0.10, suggested = 1.10
        assert r["suggested"] == pytest.approx(1.10, abs=0.01)
        assert r["delta"] < 0

    def test_negative_effect_pm_conflict(self):
        """pm_conflict (negative effect) için aynı mantık ters yönde."""
        # current 0.75, effect = -0.25
        # hit %80 → suggested_effect = -0.25 * 80/60 = -0.333
        # suggested = 0.667
        r = stats._suggest_multiplier("pm_conflict", hit_rate_pct=80.0,
                                       sample_size=30)
        assert r["suggested"] == pytest.approx(0.667, abs=0.01)
        # current 0.75 → 0.667: delta negatif (daha agresif çelişki)
        assert r["delta"] < 0

    def test_low_hit_rate_pm_conflict_dampens(self):
        """pm_conflict hit %30 → effect azalır, 0.75'ten 0.875'e (1'e yaklaşır)."""
        r = stats._suggest_multiplier("pm_conflict", hit_rate_pct=30.0,
                                       sample_size=30)
        # effect = -0.25 * 30/60 = -0.125, suggested = 0.875
        assert r["suggested"] == pytest.approx(0.875, abs=0.01)
        # 0.75 → 0.875: delta pozitif (çarpan etkisini azalttı)
        assert r["delta"] > 0

    def test_clamp_upper(self):
        """Hit rate çok yüksekse suggested 1.50'de durmalı."""
        r = stats._suggest_multiplier("pm_confirm", hit_rate_pct=500.0,
                                       sample_size=30)
        assert r["suggested"] == 1.50

    def test_clamp_lower(self):
        """pm_conflict hit rate çok yüksekse suggested 0.50'de durmalı."""
        # effect = -0.25 * 500/60 = -2.08 → suggested = -1.08
        # Clamp 0.50
        r = stats._suggest_multiplier("pm_conflict", hit_rate_pct=500.0,
                                       sample_size=30)
        assert r["suggested"] == 0.50

    def test_confidence_levels(self):
        """Sample size'a göre confidence."""
        r10 = stats._suggest_multiplier("pm_confirm", hit_rate_pct=60.0,
                                          sample_size=10)
        r20 = stats._suggest_multiplier("pm_confirm", hit_rate_pct=60.0,
                                          sample_size=20)
        r50 = stats._suggest_multiplier("pm_confirm", hit_rate_pct=60.0,
                                          sample_size=50)
        assert r10["confidence"] == "low"
        assert r20["confidence"] == "medium"
        assert r50["confidence"] == "high"

    def test_minimal_delta_note(self):
        """|delta| < 0.02 → 'minimal değişiklik' notu."""
        # current 1.20, hit %60 → suggested = 1.20 (effect korunur)
        r = stats._suggest_multiplier("pm_confirm", hit_rate_pct=60.0,
                                       sample_size=30)
        assert abs(r["delta"]) < 0.02
        assert "iyi" in r["note"].lower() or "minimal" in r["note"].lower()

    def test_increase_decrease_notes(self):
        r_up = stats._suggest_multiplier("pm_confirm", hit_rate_pct=80.0,
                                           sample_size=30)
        r_dn = stats._suggest_multiplier("pm_confirm", hit_rate_pct=30.0,
                                           sample_size=30)
        # Yüksek hit rate → çarpan etkisini artır (delta > 0)
        assert "artırma" in r_up["note"].lower()
        # Düşük hit rate → çarpan etkisini azalt (delta < 0)
        assert "azaltma" in r_dn["note"].lower()


# ── _calc_adaptive_suggestions ─────────────────────────────────────────────────


class TestCalcAdaptive:
    def test_empty_hit_rates(self):
        assert stats._calc_adaptive_suggestions({}) == []
        assert stats._calc_adaptive_suggestions(None) == []

    def test_returns_four_flag_order(self):
        """4 bayrak sıralı liste döndürür."""
        hit_rates = {
            "by_flag_horizon": {
                "pm_confirm": {
                    "outcome_7d": {"hits": 8, "total": 10, "rate_pct": 80.0},
                },
            }
        }
        result = stats._calc_adaptive_suggestions(hit_rates)
        assert len(result) == 4
        flags = [r["flag"] for r in result]
        assert flags == ["pm_confirm", "pm_confirm_weak",
                         "pm_conflict_weak", "pm_conflict"]

    def test_missing_flags_get_insufficient(self):
        """Hit rates'te olmayan bayraklar için insufficient öneri."""
        hit_rates = {
            "by_flag_horizon": {
                "pm_confirm": {
                    "outcome_7d": {"hits": 12, "total": 15, "rate_pct": 80.0},
                },
                # diğerleri yok
            }
        }
        result = stats._calc_adaptive_suggestions(hit_rates)
        # pm_confirm hesaplandı (sample 15 = low)
        confirm = next(r for r in result if r["flag"] == "pm_confirm")
        assert confirm["confidence"] == "low"
        assert confirm["suggested"] is not None
        # Diğerleri insufficient
        weak = next(r for r in result if r["flag"] == "pm_confirm_weak")
        assert weak["confidence"] == "insufficient"
        assert weak["sample_size"] == 0


# ── query_calibrator_stats entegrasyonu ────────────────────────────────────────


class TestQueryStatsAdaptive:
    def _write_tracker(self, tmp_path, events, started_at=None):
        path = tmp_path / "tracker.json"
        data = {"_version": "v1", "events": events}
        if started_at:
            data["_started_at"] = started_at.isoformat()
        path.write_text(json.dumps(data))
        return path

    def _make_event(self, symbol, flag, ts, outcome_7d=None):
        return {
            "id": f"e_{symbol}", "ts": ts.isoformat(),
            "candidate_symbol": symbol, "candidate_source": "thematic",
            "applied_flag": flag,
            "applied_multiplier": 1.20 if "confirm" in flag else 0.75,
            "matched_theme": "test", "matched_side": "positive",
            "market_slug": "s1", "market_delta_24h": 0.1,
            "outcome_7d": outcome_7d, "outcome_14d": None, "outcome_30d": None,
        }

    def test_empty_tracker_no_suggestions(self, tmp_path, monkeypatch):
        path = self._write_tracker(tmp_path, [])
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=30)
        assert result["adaptive_suggestions"] == []

    def test_pending_no_outcomes_no_suggestions(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        events = [self._make_event("A", "pm_confirm",
                                    now - timedelta(days=2))]
        path = self._write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=30)
        # outcome yok → hit_rates None → suggestions []
        assert result["adaptive_suggestions"] == []

    def test_filled_outcomes_returns_suggestions(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        # 12 pm_confirm event, 9 HIT
        events = [
            self._make_event(f"S{i}", "pm_confirm",
                             now - timedelta(days=10),
                             outcome_7d=0.05 if i < 9 else -0.02)
            for i in range(12)
        ]
        path = self._write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=30)
        suggestions = result["adaptive_suggestions"]
        assert len(suggestions) == 4

        # pm_confirm dolu (75% hit rate, 12 sample = low)
        confirm = next(s for s in suggestions if s["flag"] == "pm_confirm")
        assert confirm["hit_rate_pct"] == 75.0
        assert confirm["sample_size"] == 12
        assert confirm["confidence"] == "low"
        assert confirm["suggested"] is not None


# ── format_calibrator_section render ───────────────────────────────────────────


class TestFormatAdaptiveSection:
    def test_no_suggestions_no_table(self):
        section = stats.format_calibrator_section({
            "total_events": 1, "by_flag": {"pm_confirm": 1},
            "by_multiplier": {"1.20x": 1}, "by_source": {"thematic": 1},
            "top_themes": [], "top_symbols": [],
            "days_collected": 5.0, "phase10_progress_pct": 16.7,
            "outcome_status": "pending_phase10",
            "hit_rates": None,
            "adaptive_suggestions": [],
        })
        text = "\n".join(section)
        assert "Adaptive Multiplier" not in text

    def test_with_suggestions_renders_table(self):
        suggestions = [
            {"flag": "pm_confirm", "current": 1.20, "suggested": 1.27,
             "delta": 0.07, "hit_rate_pct": 80.0, "sample_size": 15,
             "confidence": "low",
             "note": "Çarpan etkisini artırma önerisi (+0.07)"},
            {"flag": "pm_confirm_weak", "current": 1.10, "suggested": None,
             "delta": None, "hit_rate_pct": None, "sample_size": 0,
             "confidence": "insufficient", "note": "Yetersiz veri"},
            {"flag": "pm_conflict_weak", "current": 0.90, "suggested": None,
             "delta": None, "hit_rate_pct": None, "sample_size": 0,
             "confidence": "insufficient", "note": "Yetersiz veri"},
            {"flag": "pm_conflict", "current": 0.75, "suggested": 0.83,
             "delta": 0.08, "hit_rate_pct": 40.0, "sample_size": 10,
             "confidence": "low", "note": "Çarpan etkisini azaltma"},
        ]
        section = stats.format_calibrator_section({
            "total_events": 25, "by_flag": {"pm_confirm": 15, "pm_conflict": 10},
            "by_multiplier": {"1.20x": 15, "0.75x": 10},
            "by_source": {"thematic": 25},
            "top_themes": [], "top_symbols": [],
            "days_collected": 15.0, "phase10_progress_pct": 50.0,
            "outcome_status": "phase10_ready",
            "hit_rates": {
                "overall": {
                    "outcome_7d": {"hits": 16, "total": 25, "rate_pct": 64.0},
                    "outcome_14d": {"hits": 0, "total": 0, "rate_pct": None},
                    "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
                },
                "by_flag_horizon": {}, "by_source": {}, "by_theme": {},
            },
            "adaptive_suggestions": suggestions,
        })
        text = "\n".join(section)

        # Tablo başlığı + 4 satır
        assert "Adaptive Multiplier Önerileri" in text
        assert "passive" in text
        assert "Sabit tablo şu an değişmiyor" in text

        # 4 bayrak hepsi tabloda
        assert "pm_confirm" in text
        assert "pm_confirm_weak" in text
        assert "pm_conflict" in text
        assert "pm_conflict_weak" in text

        # Bazı somut değerler
        assert "1.20x" in text  # current
        assert "1.27x" in text  # suggested
        assert "+0.07" in text  # delta
        assert "80.0%" in text  # hit rate
        assert "`low`" in text  # confidence

        # Insufficient için tire gösterimi
        assert "—" in text

    def test_high_confidence_actionable_note(self):
        """Yüksek güven + büyük sapma → 'Phase 10 gündeminde' notu."""
        suggestions = [
            {"flag": "pm_confirm", "current": 1.20, "suggested": 1.40,
             "delta": 0.20, "hit_rate_pct": 90.0, "sample_size": 100,
             "confidence": "high", "note": "artır"},
            {"flag": "pm_confirm_weak", "current": 1.10, "suggested": None,
             "delta": None, "hit_rate_pct": None, "sample_size": 0,
             "confidence": "insufficient", "note": "Yetersiz veri"},
            {"flag": "pm_conflict_weak", "current": 0.90, "suggested": None,
             "delta": None, "hit_rate_pct": None, "sample_size": 0,
             "confidence": "insufficient", "note": "Yetersiz veri"},
            {"flag": "pm_conflict", "current": 0.75, "suggested": None,
             "delta": None, "hit_rate_pct": None, "sample_size": 0,
             "confidence": "insufficient", "note": "Yetersiz veri"},
        ]
        section = stats.format_calibrator_section({
            "total_events": 100, "by_flag": {"pm_confirm": 100},
            "by_multiplier": {"1.20x": 100}, "by_source": {"thematic": 100},
            "top_themes": [], "top_symbols": [],
            "days_collected": 35.0, "phase10_progress_pct": 100.0,
            "outcome_status": "phase10_ready",
            "hit_rates": {
                "overall": {
                    "outcome_7d": {"hits": 90, "total": 100, "rate_pct": 90.0},
                    "outcome_14d": {"hits": 0, "total": 0, "rate_pct": None},
                    "outcome_30d": {"hits": 0, "total": 0, "rate_pct": None},
                },
                "by_flag_horizon": {}, "by_source": {}, "by_theme": {},
            },
            "adaptive_suggestions": suggestions,
        })
        text = "\n".join(section)
        # Yüksek güven + actionable delta → öneri notu
        assert "Phase 10" in text and "gündeminde" in text
