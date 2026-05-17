"""agent/scanners/calibrator.py için kapsamlı testler.

Faz 2 — Adım 9: PolymarketCalibrator.

KAPSAM:
    - _classify_delta: 5 kategori × 2 side
    - _delta_to_multiplier_flag: çarpan tablosu
    - Bayrak whitelist (BaseScanner ALLOWED_FLAGS) ile uyum
    - _find_theme_matches: positive/negative/none
    - Çoklu tema eşleşmesi (en aşırı kazanır — Candidate.apply_calibration)
    - calibrate end-to-end: 4 senaryo (confirm, conflict, neutral, no-match)
    - Volume filtresi (manipulation guard)
    - delta None ise no-op
    - Tek candidate hatası diğerlerini etkilemez
    - Boş input handling
    - watchlist_health_check: alert üretimi
    - Performance tracker: initialize + event recording + stats
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ── _classify_delta ────────────────────────────────────────────────────────────


class TestClassifyDelta:
    def _import(self):
        from agent.scanners.calibrator import _classify_delta
        return _classify_delta

    @pytest.mark.parametrize("delta,side,expected", [
        # Positive side
        (0.15, "positive", "strong_confirm"),
        (0.10, "positive", "strong_confirm"),  # sınır dahil
        (0.05, "positive", "weak_confirm"),
        (0.03, "positive", "weak_confirm"),  # sınır dahil
        (0.01, "positive", "neutral"),
        (0.0, "positive", "neutral"),
        (-0.01, "positive", "neutral"),
        (-0.05, "positive", "weak_conflict"),
        (-0.15, "positive", "strong_conflict"),
        # Negative side — delta ters çevrilir
        (0.15, "negative", "strong_conflict"),
        (0.05, "negative", "weak_conflict"),
        (0.01, "negative", "neutral"),
        (-0.05, "negative", "weak_confirm"),
        (-0.15, "negative", "strong_confirm"),
    ])
    def test_classification(self, delta, side, expected):
        classify = self._import()
        assert classify(delta, side) == expected

    def test_invalid_side_rejected(self):
        classify = self._import()
        with pytest.raises(ValueError, match="side"):
            classify(0.1, "invalid")

    def test_boundary_exactly_at_weak_threshold(self):
        """%3 sınırı tam üstünde weak_confirm, altında neutral."""
        classify = self._import()
        # 0.029 < 0.03 → neutral
        assert classify(0.029, "positive") == "neutral"
        # 0.03 >= 0.03 → weak_confirm
        assert classify(0.03, "positive") == "weak_confirm"


# ── _delta_to_multiplier_flag ──────────────────────────────────────────────────


class TestDeltaToMultiplierFlag:
    def _import(self):
        from agent.scanners.calibrator import _delta_to_multiplier_flag
        return _delta_to_multiplier_flag

    def test_strong_confirm(self):
        fn = self._import()
        mult, flag = fn(0.15, "positive")
        assert mult == 1.20
        assert flag == "pm_confirm"

    def test_weak_confirm(self):
        fn = self._import()
        mult, flag = fn(0.05, "positive")
        assert mult == 1.10
        assert flag == "pm_confirm_weak"

    def test_neutral_returns_none(self):
        fn = self._import()
        mult, flag = fn(0.01, "positive")
        assert mult is None
        assert flag is None

    def test_weak_conflict(self):
        fn = self._import()
        mult, flag = fn(-0.05, "positive")
        assert mult == 0.90
        assert flag == "pm_conflict_weak"

    def test_strong_conflict(self):
        fn = self._import()
        mult, flag = fn(-0.15, "positive")
        assert mult == 0.75
        assert flag == "pm_conflict"

    def test_negative_side_inverts(self):
        """negative side için aynı delta → ters yön."""
        fn = self._import()
        # delta +0.15, negative side → strong conflict
        mult, flag = fn(0.15, "negative")
        assert mult == 0.75
        assert flag == "pm_conflict"
        # delta -0.15, negative side → strong confirm
        mult, flag = fn(-0.15, "negative")
        assert mult == 1.20
        assert flag == "pm_confirm"

    def test_all_flags_in_base_whitelist(self):
        """Üretilen tüm bayraklar BaseScanner ALLOWED_FLAGS içinde olmalı."""
        from agent.scanners.base import ALLOWED_FLAGS
        fn = self._import()
        for delta in [0.15, 0.05, -0.05, -0.15]:
            for side in ["positive", "negative"]:
                _, flag = fn(delta, side)
                if flag is not None:
                    assert flag in ALLOWED_FLAGS, f"Bayrak whitelist dışı: {flag}"


# ── _find_theme_matches ────────────────────────────────────────────────────────


class TestFindThemeMatches:
    def _import(self):
        from agent.scanners.calibrator import _find_theme_matches
        return _find_theme_matches

    def test_positive_match(self):
        find = self._import()
        themes = {"themes": {
            "t1": {"positive_tickers": ["LMT", "RTX"], "negative_tickers": []}
        }}
        result = find("LMT", themes)
        assert len(result) == 1
        theme_id, side, cfg = result[0]
        assert theme_id == "t1"
        assert side == "positive"

    def test_negative_match(self):
        find = self._import()
        themes = {"themes": {
            "t1": {"positive_tickers": [], "negative_tickers": ["TSM"]}
        }}
        result = find("TSM", themes)
        assert len(result) == 1
        assert result[0][1] == "negative"

    def test_multiple_themes(self):
        """TSM hem china_taiwan (negative) hem tariff (negative) listesinde."""
        find = self._import()
        themes = {"themes": {
            "china_taiwan": {"positive_tickers": [], "negative_tickers": ["TSM"]},
            "tariff": {"positive_tickers": [], "negative_tickers": ["TSM"]},
        }}
        result = find("TSM", themes)
        assert len(result) == 2
        theme_ids = {m[0] for m in result}
        assert theme_ids == {"china_taiwan", "tariff"}

    def test_no_match(self):
        find = self._import()
        themes = {"themes": {
            "t1": {"positive_tickers": ["LMT"], "negative_tickers": []}
        }}
        assert find("AAPL", themes) == []

    def test_empty_themes(self):
        find = self._import()
        assert find("AAPL", {"themes": {}}) == []
        assert find("AAPL", {}) == []
        assert find("AAPL", None) == []  # type: ignore[arg-type]

    def test_empty_symbol(self):
        find = self._import()
        themes = {"themes": {"t1": {"positive_tickers": ["LMT"]}}}
        assert find("", themes) == []
        assert find("  ", themes) == []

    def test_case_insensitive_matching(self):
        find = self._import()
        themes = {"themes": {
            "t1": {"positive_tickers": ["tsm"], "negative_tickers": []}
        }}
        result = find("TSM", themes)
        assert len(result) == 1

    def test_malformed_theme_config_skipped(self):
        find = self._import()
        themes = {"themes": {
            "good": {"positive_tickers": ["A"]},
            "bad": "not-a-dict",  # bozuk
        }}
        result = find("A", themes)
        assert len(result) == 1
        assert result[0][0] == "good"


# ── PolymarketCalibrator.calibrate ─────────────────────────────────────────────


class TestCalibrate:
    def _make(self, themes, cache, tmp_path):
        """Helper — kalibratör + tracker path."""
        from agent.scanners.calibrator import PolymarketCalibrator
        tracker = tmp_path / "perf.json"
        cal = PolymarketCalibrator(
            themes_loader=lambda: themes,
            cache_loader=lambda: cache,
            performance_log_path=tracker,
        )
        return cal, tracker

    def _make_candidate(self, symbol, score=0.7):
        from agent.scanners.base import Candidate
        return Candidate(symbol=symbol, score=score, reason="test", source="thematic")

    def test_no_match_no_change(self, tmp_path):
        themes = {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["slug-1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"slug-1": {"delta_24h": 0.15, "volume": 1000000}}}
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("AAPL")]
        cal.calibrate(cands)
        assert cands[0].has_calibration is False

    def test_strong_confirm_positive(self, tmp_path):
        themes = {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["slug-1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"slug-1": {"delta_24h": 0.15, "volume": 1000000}}}
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("LMT", score=0.6)]
        cal.calibrate(cands)
        assert cands[0].calibration_multiplier == 1.20
        assert "pm_confirm" in cands[0].calibration_flags
        assert cands[0].calibrated_score == pytest.approx(0.72)

    def test_strong_conflict_negative_side(self, tmp_path):
        """Negative liste + market yükselişi → conflict."""
        themes = {"themes": {
            "china_taiwan": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["taiwan"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"taiwan": {"delta_24h": 0.15, "volume": 1000000}}}
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("TSM", score=0.8)]
        cal.calibrate(cands)
        assert cands[0].calibration_multiplier == 0.75
        assert "pm_conflict" in cands[0].calibration_flags
        assert cands[0].calibrated_score == pytest.approx(0.60)

    def test_neutral_zone_no_change(self, tmp_path):
        themes = {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["slug-1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"slug-1": {"delta_24h": 0.01, "volume": 1000000}}}
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("LMT")]
        cal.calibrate(cands)
        assert cands[0].has_calibration is False

    def test_volume_filter_blocks_low_liquidity(self, tmp_path):
        """min_volume_usd altındaki marketler atlanır."""
        themes = {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["slug-1"], "min_volume_usd": 500000,
            }
        }}
        # Volume 100k < 500k threshold
        cache = {"markets": {"slug-1": {"delta_24h": 0.15, "volume": 100000}}}
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("LMT")]
        cal.calibrate(cands)
        assert cands[0].has_calibration is False

    def test_volume_at_threshold_passes(self, tmp_path):
        themes = {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["slug-1"], "min_volume_usd": 500000,
            }
        }}
        cache = {"markets": {"slug-1": {"delta_24h": 0.15, "volume": 500000}}}
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("LMT")]
        cal.calibrate(cands)
        assert cands[0].has_calibration is True

    def test_missing_delta_skipped(self, tmp_path):
        """delta_24h yoksa kalibratör atlamalı (cache henüz dolmamış senaryo)."""
        themes = {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["slug-1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"slug-1": {"volume": 1000000}}}  # delta_24h yok
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("LMT")]
        cal.calibrate(cands)
        assert cands[0].has_calibration is False

    def test_multiple_theme_matches_extreme_wins(self, tmp_path):
        """TSM hem t1'de hem t2'de negatif; t1 confirm_weak, t2 strong_conflict.
        Sonuç: çelişki kazanır (Candidate.apply_calibration downside protection)."""
        themes = {"themes": {
            "t1": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["m1"], "min_volume_usd": 0,
            },
            "t2": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["m2"], "min_volume_usd": 0,
            },
        }}
        cache = {"markets": {
            "m1": {"delta_24h": -0.05, "volume": 1000000},  # negatif side, -0.05 → +eff → weak_confirm 1.10
            "m2": {"delta_24h": 0.15, "volume": 1000000},   # negatif side, +0.15 → strong_conflict 0.75
        }}
        cal, _ = self._make(themes, cache, tmp_path)

        cands = [self._make_candidate("TSM", score=0.8)]
        cal.calibrate(cands)
        # Çoklu eşleşmede çelişki kazanır (downside protection)
        assert cands[0].calibration_multiplier == 0.75
        # Her iki bayrak da listede
        assert "pm_confirm_weak" in cands[0].calibration_flags
        assert "pm_conflict" in cands[0].calibration_flags

    def test_empty_candidates(self, tmp_path):
        themes = {"themes": {}}
        cache = {"markets": {}}
        cal, _ = self._make(themes, cache, tmp_path)
        assert cal.calibrate([]) == []

    def test_loader_exception_graceful(self, tmp_path):
        """themes_loader exception fırlatırsa kalibratör çökmez."""
        from agent.scanners.calibrator import PolymarketCalibrator
        from agent.scanners.base import Candidate

        def _boom():
            raise RuntimeError("loader down")

        cal = PolymarketCalibrator(
            themes_loader=_boom,
            cache_loader=lambda: {"markets": {}},
            performance_log_path=tmp_path / "perf.json",
        )
        cands = [Candidate(symbol="X", score=0.5, reason="r", source="news")]
        result = cal.calibrate(cands)
        # Mutate olmadı, çökmedi
        assert result[0].has_calibration is False


# ── Performance tracker ────────────────────────────────────────────────────────


class TestPerformanceTracker:
    def test_initialize_creates_file(self, tmp_path):
        from agent.scanners.calibrator import PolymarketCalibrator
        tracker = tmp_path / "perf.json"
        cal = PolymarketCalibrator(
            themes_loader=lambda: {"themes": {}},
            cache_loader=lambda: {"markets": {}},
            performance_log_path=tracker,
        )
        cal.initialize_tracker()
        assert tracker.exists()
        log = json.loads(tracker.read_text())
        assert log["_version"] == "v1"
        assert log["events"] == []
        assert "stats" in log

    def test_initialize_idempotent(self, tmp_path):
        """İkinci kez çağrı dosyayı sıfırlamamalı."""
        from agent.scanners.calibrator import PolymarketCalibrator
        tracker = tmp_path / "perf.json"
        cal = PolymarketCalibrator(
            themes_loader=lambda: {"themes": {}},
            cache_loader=lambda: {"markets": {}},
            performance_log_path=tracker,
        )
        cal.initialize_tracker()
        # Dosyaya bir event ekle
        log = json.loads(tracker.read_text())
        log["events"].append({"id": "x"})
        tracker.write_text(json.dumps(log))
        # Yeniden initialize çağır
        cal.initialize_tracker()
        # Event hâlâ orada
        log2 = json.loads(tracker.read_text())
        assert len(log2["events"]) == 1

    def test_calibrate_records_events(self, tmp_path):
        from agent.scanners.calibrator import PolymarketCalibrator
        from agent.scanners.base import Candidate

        themes = {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["slug-1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"slug-1": {"delta_24h": 0.15, "volume": 1000000}}}
        tracker = tmp_path / "perf.json"
        cal = PolymarketCalibrator(
            themes_loader=lambda: themes,
            cache_loader=lambda: cache,
            performance_log_path=tracker,
        )
        cands = [Candidate(symbol="LMT", score=0.6, reason="r", source="thematic")]
        cal.calibrate(cands)

        log = cal.load_performance_log()
        assert log["stats"]["total_events"] == 1
        assert log["stats"]["confirms"] == 1
        assert log["stats"]["conflicts"] == 0
        evt = log["events"][0]
        assert evt["candidate_symbol"] == "LMT"
        assert evt["applied_flag"] == "pm_confirm"
        assert evt["applied_multiplier"] == 1.20
        assert evt["matched_theme"] == "t1"
        assert evt["matched_side"] == "positive"
        assert evt["market_slug"] == "slug-1"
        assert evt["market_delta_24h"] == 0.15
        # Outcomes geri-doldurma için None
        assert evt["outcome_7d"] is None

    def test_stats_aggregation(self, tmp_path):
        """Birden fazla event sonrası stats doğru."""
        from agent.scanners.calibrator import PolymarketCalibrator
        from agent.scanners.base import Candidate

        themes = {"themes": {
            "t_pos": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["m1"], "min_volume_usd": 0,
            },
            "t_neg": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["m2"], "min_volume_usd": 0,
            },
        }}
        cache = {"markets": {
            "m1": {"delta_24h": 0.15, "volume": 1000000},  # LMT confirm
            "m2": {"delta_24h": 0.15, "volume": 1000000},  # TSM conflict (negative side)
        }}
        tracker = tmp_path / "perf.json"
        cal = PolymarketCalibrator(
            themes_loader=lambda: themes,
            cache_loader=lambda: cache,
            performance_log_path=tracker,
        )
        cands = [
            Candidate(symbol="LMT", score=0.6, reason="r", source="thematic"),
            Candidate(symbol="TSM", score=0.7, reason="r", source="thematic"),
        ]
        cal.calibrate(cands)

        log = cal.load_performance_log()
        assert log["stats"]["total_events"] == 2
        assert log["stats"]["confirms"] == 1
        assert log["stats"]["conflicts"] == 1


# ── Watchlist health check (Pozisyon #3) ───────────────────────────────────────


class TestWatchlistHealthCheck:
    def _make(self, themes, cache, tmp_path):
        from agent.scanners.calibrator import PolymarketCalibrator
        return PolymarketCalibrator(
            themes_loader=lambda: themes,
            cache_loader=lambda: cache,
            performance_log_path=tmp_path / "perf.json",
        )

    def test_only_conflicts_alert(self, tmp_path):
        """confirm bayrakları alert üretmemeli — sadece conflict."""
        themes = {"themes": {
            "china_taiwan": {
                "label": "Çin-Tayvan",
                "positive_tickers": ["LMT"], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["taiwan"], "min_volume_usd": 0,
            }
        }}
        # delta +0.15: TSM negative → conflict, LMT positive → confirm
        cache = {"markets": {"taiwan": {"delta_24h": 0.15, "volume": 1000000}}}
        cal = self._make(themes, cache, tmp_path)

        alerts = cal.watchlist_health_check(["TSM", "LMT"])
        # Sadece TSM çelişkide
        symbols = [a["symbol"] for a in alerts]
        assert "TSM" in symbols
        assert "LMT" not in symbols
        # TSM alert detayları
        tsm_alert = next(a for a in alerts if a["symbol"] == "TSM")
        assert tsm_alert["flag"] == "pm_conflict"
        assert tsm_alert["severity"] == "strong"
        assert tsm_alert["theme_id"] == "china_taiwan"
        assert tsm_alert["theme_label"] == "Çin-Tayvan"
        assert tsm_alert["delta_24h"] == 0.15

    def test_weak_conflict_alert(self, tmp_path):
        themes = {"themes": {
            "t1": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["m1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"m1": {"delta_24h": 0.05, "volume": 1000000}}}
        cal = self._make(themes, cache, tmp_path)
        alerts = cal.watchlist_health_check(["TSM"])
        assert len(alerts) == 1
        assert alerts[0]["flag"] == "pm_conflict_weak"
        assert alerts[0]["severity"] == "weak"

    def test_no_alerts_when_neutral(self, tmp_path):
        themes = {"themes": {
            "t1": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["m1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"m1": {"delta_24h": 0.01, "volume": 1000000}}}
        cal = self._make(themes, cache, tmp_path)
        assert cal.watchlist_health_check(["TSM"]) == []

    def test_no_match_no_alerts(self, tmp_path):
        themes = {"themes": {}}
        cache = {"markets": {}}
        cal = self._make(themes, cache, tmp_path)
        assert cal.watchlist_health_check(["AAPL", "NVDA"]) == []

    def test_empty_watchlist(self, tmp_path):
        themes = {"themes": {}}
        cache = {"markets": {}}
        cal = self._make(themes, cache, tmp_path)
        assert cal.watchlist_health_check([]) == []

    def test_invalid_symbols_skipped(self, tmp_path):
        themes = {"themes": {
            "t1": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["m1"], "min_volume_usd": 0,
            }
        }}
        cache = {"markets": {"m1": {"delta_24h": 0.15, "volume": 1000000}}}
        cal = self._make(themes, cache, tmp_path)
        alerts = cal.watchlist_health_check([None, "", "  ", "TSM"])  # type: ignore[list-item]
        # Sadece TSM
        assert len(alerts) == 1
        assert alerts[0]["symbol"] == "TSM"
