"""agent/scanners/fair_value.py:discover_undervalued_tickers
kalibratör entegrasyonu testleri.

Faz 2 — Adım 10b-iii-C-i: gerçek üretim akışına Polymarket kalibratör hook.

KAPSAM:
    - CALIBRATOR_ENABLED=false → mevcut davranış (kalibratör çağrılmaz)
    - CALIBRATOR_ENABLED=true → kalibratör instance + ai_gate'e calibration_info iletilir
    - Kalibratör eşleşmesi varsa (positive ticker) → bayraklar AI Gate'e gider
    - Kalibratör eşleşmesi yoksa (unrelated ticker) → calibration_info=None
    - Kalibrasyon yan etki: watchlist score_components'a 'polymarket_calibration' eklenir
    - Kalibratör hata fırlatırsa AI Gate akışı kırılmaz (graceful)
    - Kalibratör başlatma hatası → tarama devam eder, calibrator=None
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ── Test helpers ───────────────────────────────────────────────────────────────


def _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls,
                             cal_calibrate_calls=None):
    """Ortak mock kurulumu — discover_undervalued_tickers için."""
    from agent.scanners import fair_value
    from agent import ai_gate as ai_gate_module

    # FMP mock
    monkeypatch.setattr(fair_value, "fmp_get", lambda endpoint, params: [
        {"price": 100.0}
    ])

    # fetch_analyst_targets mock — target $150 üreten basit veri
    monkeypatch.setattr(fair_value, "fetch_analyst_targets",
                        lambda symbol, lookback_count=20: [
                            {"priceTarget": 150.0, "publishedDate": "2026-05-01"}
                        ])

    # compute_fair_value mock — sabit FV $150 (current $100 → +%50 potansiyel)
    monkeypatch.setattr(fair_value, "compute_fair_value", lambda targets: {
        "fair_value": 150.0,
        "latest_target": 150.0,
        "highest_target": 150.0,
        "sample_size": 1,
    })

    # Watchlist module mock — hiçbir ticker portföyde değil
    import agent.watchlist as wl
    monkeypatch.setattr(wl, "is_in_portfolio", lambda s: False)
    monkeypatch.setattr(wl, "is_in_pool", lambda s: False)
    monkeypatch.setattr(wl, "is_excluded", lambda s: False)

    # wl.add → çağrıları kaydet, başarı döndür
    def fake_wl_add(**kwargs):
        wl_add_calls.append(kwargs)
        return {"action": "added"}
    monkeypatch.setattr(wl, "add", fake_wl_add)

    # ai_gate.evaluate_signal — çağrıları kaydet, EKLE döndür
    def fake_ai_gate(**kwargs):
        ai_gate_calls.append(kwargs)
        return {
            "action": "EKLE",
            "score": 75,
            "reason": "test",
            "theme_match": None,
            "cautions": [],
        }
    monkeypatch.setattr(ai_gate_module, "evaluate_signal", fake_ai_gate)

    return fair_value


# ── Feature flag senaryoları ───────────────────────────────────────────────────


class TestCalibratorFlagOff:
    """CALIBRATOR_ENABLED kapalıyken mevcut davranış aynı kalmalı."""

    def test_no_calibrator_no_calibration_info(self, monkeypatch):
        monkeypatch.delenv("CALIBRATOR_ENABLED", raising=False)
        ai_gate_calls = []
        wl_add_calls = []
        fv = _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls)

        result = fv.discover_undervalued_tickers(
            min_potential_pct=25.0,
            universe=["AAPL"],
        )

        # Tarama yapıldı, eklendi
        assert result["scanned"] == 1
        assert result["discovered"] == 1
        assert len(result["added"]) == 1

        # AI Gate çağrıldı ama calibration_info=None
        assert len(ai_gate_calls) == 1
        assert ai_gate_calls[0].get("calibration_info") is None

        # Watchlist'e eklendi ama polymarket_calibration alanı YOK
        assert len(wl_add_calls) == 1
        sc = wl_add_calls[0]["score_components"]
        assert "polymarket_calibration" not in sc
        # ai_gate alanı hâlâ var (eski davranış)
        assert "ai_gate" in sc

    def test_explicit_false_flag(self, monkeypatch):
        monkeypatch.setenv("CALIBRATOR_ENABLED", "false")
        ai_gate_calls = []
        wl_add_calls = []
        fv = _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls)

        fv.discover_undervalued_tickers(universe=["NVDA"])
        assert ai_gate_calls[0].get("calibration_info") is None


class TestCalibratorFlagOn:
    """CALIBRATOR_ENABLED açıkken kalibratör entegre çalışır."""

    def _setup_calibrator(self, monkeypatch, theme_config, market_data):
        """PolymarketCalibrator'ı themes + cache mock'larıyla kur."""
        from agent import polymarket
        monkeypatch.setattr(polymarket, "load_themes",
                            lambda: {"themes": theme_config})
        monkeypatch.setattr(polymarket, "load_cache",
                            lambda: {"markets": market_data})

    def test_calibrator_matches_positive_ticker(self, monkeypatch, tmp_path):
        """LMT positive_tickers'da → pm_confirm bayrağı AI Gate'e iletilir."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        # Tracker'ı tmp'ye yönlendir
        from agent.scanners import calibrator as cal_module
        original_init = cal_module.PolymarketCalibrator.__init__
        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("performance_log_path", tmp_path / "perf.json")
            original_init(self, *args, **kwargs)
        monkeypatch.setattr(cal_module.PolymarketCalibrator, "__init__", patched_init)

        # Kalibratör için themes + cache
        self._setup_calibrator(monkeypatch, theme_config={
            "china_taiwan": {
                "positive_tickers": ["LMT"],
                "negative_tickers": [],
                "polymarket_slugs": ["taiwan-2026"],
                "min_volume_usd": 0,
            }
        }, market_data={
            "taiwan-2026": {"delta_24h": 0.15, "volume": 1000000}
        })

        ai_gate_calls = []
        wl_add_calls = []
        fv = _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls)

        fv.discover_undervalued_tickers(universe=["LMT"])

        # AI Gate çağrısına calibration_info iletildi
        assert len(ai_gate_calls) == 1
        cal_info = ai_gate_calls[0].get("calibration_info")
        assert cal_info is not None
        assert "pm_confirm" in cal_info["flags"]
        assert cal_info["multiplier"] == 1.20

        # Watchlist'e polymarket_calibration eklendi
        assert len(wl_add_calls) == 1
        sc = wl_add_calls[0]["score_components"]
        assert "polymarket_calibration" in sc
        assert sc["polymarket_calibration"]["flags"] == ["pm_confirm"]
        assert sc["polymarket_calibration"]["multiplier"] == 1.20

    def test_calibrator_matches_negative_ticker(self, monkeypatch, tmp_path):
        """TSM negative_tickers'da, market yükselişi → pm_conflict."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        from agent.scanners import calibrator as cal_module
        original_init = cal_module.PolymarketCalibrator.__init__
        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("performance_log_path", tmp_path / "perf.json")
            original_init(self, *args, **kwargs)
        monkeypatch.setattr(cal_module.PolymarketCalibrator, "__init__", patched_init)

        self._setup_calibrator(monkeypatch, theme_config={
            "china_taiwan": {
                "positive_tickers": [],
                "negative_tickers": ["TSM"],
                "polymarket_slugs": ["taiwan-2026"],
                "min_volume_usd": 0,
            }
        }, market_data={
            "taiwan-2026": {"delta_24h": 0.15, "volume": 1000000}
        })

        ai_gate_calls = []
        wl_add_calls = []
        fv = _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls)

        fv.discover_undervalued_tickers(universe=["TSM"])

        cal_info = ai_gate_calls[0].get("calibration_info")
        assert cal_info is not None
        assert "pm_conflict" in cal_info["flags"]
        assert cal_info["multiplier"] == 0.75

    def test_calibrator_no_match_returns_none(self, monkeypatch, tmp_path):
        """Hiçbir temada olmayan ticker → calibration_info=None."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        from agent.scanners import calibrator as cal_module
        original_init = cal_module.PolymarketCalibrator.__init__
        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("performance_log_path", tmp_path / "perf.json")
            original_init(self, *args, **kwargs)
        monkeypatch.setattr(cal_module.PolymarketCalibrator, "__init__", patched_init)

        # Themes mevcut ama AAPL hiçbirinde yok
        self._setup_calibrator(monkeypatch, theme_config={
            "china_taiwan": {
                "positive_tickers": ["LMT"],
                "negative_tickers": ["TSM"],
                "polymarket_slugs": ["taiwan-2026"],
                "min_volume_usd": 0,
            }
        }, market_data={
            "taiwan-2026": {"delta_24h": 0.15, "volume": 1000000}
        })

        ai_gate_calls = []
        wl_add_calls = []
        fv = _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls)

        fv.discover_undervalued_tickers(universe=["AAPL"])

        # AAPL eşleşme yok → calibration_info None
        assert ai_gate_calls[0].get("calibration_info") is None

        # Watchlist'e polymarket_calibration eklenmedi
        sc = wl_add_calls[0]["score_components"]
        assert "polymarket_calibration" not in sc


class TestCalibratorErrorResilience:
    """Kalibratör hataları üretim akışını kırmamalı."""

    def test_calibrator_init_error_continues(self, monkeypatch):
        """PolymarketCalibrator() exception fırlatırsa tarama devam eder."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        # Calibrator'ı patch'le → init'te exception
        from agent.scanners import calibrator as cal_module

        class _BrokenCal:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("init failed")

        monkeypatch.setattr(cal_module, "PolymarketCalibrator", _BrokenCal)

        ai_gate_calls = []
        wl_add_calls = []
        fv = _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls)

        result = fv.discover_undervalued_tickers(universe=["AAPL"])

        # Tarama tamamlandı, calibration_info None
        assert result["discovered"] == 1
        assert ai_gate_calls[0].get("calibration_info") is None

    def test_calibrate_exception_per_ticker_continues(self, monkeypatch, tmp_path):
        """Kalibrate fonksiyonu exception fırlatırsa o ticker AI Gate'e
        calibration_info=None ile gider, sonraki ticker etkilenmez."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        from agent.scanners import calibrator as cal_module

        # Mock calibrator: ilk çağrıda exception, ikincide normal
        call_count = {"n": 0}

        class _PartiallyBrokenCal:
            def __init__(self, *args, **kwargs):
                pass

            def calibrate(self, candidates):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise RuntimeError("Polymarket cache corrupt")
                # İkinci çağrıda: hiçbir bayrak uygulanmaz (boş themes)
                return candidates

        monkeypatch.setattr(cal_module, "PolymarketCalibrator", _PartiallyBrokenCal)

        ai_gate_calls = []
        wl_add_calls = []
        fv = _setup_fair_value_mocks(monkeypatch, ai_gate_calls, wl_add_calls)

        result = fv.discover_undervalued_tickers(universe=["AAA", "BBB"])

        # 2 ticker tarandı, 2 AI Gate çağrısı
        assert len(ai_gate_calls) == 2
        # İkisi de calibration_info=None (ilki exception, ikincisi has_calibration=False)
        assert ai_gate_calls[0].get("calibration_info") is None
        assert ai_gate_calls[1].get("calibration_info") is None
        # Kalibrate iki kez çağrıldı (her ticker için bir tekrar)
        assert call_count["n"] == 2
