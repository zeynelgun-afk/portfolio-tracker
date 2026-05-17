"""agent/scanners/thematic.py:apply_themes kalibratör entegrasyonu testleri.

Faz 2 — Adım 10b-iii-C-ii: thematic_discovery'ye Polymarket kalibratör hook.

KAPSAM:
    - CALIBRATOR_ENABLED=false → mevcut davranış (score_components'a polymarket_calibration yok)
    - CALIBRATOR_ENABLED=true + eşleşme → score_components'a polymarket_calibration eklenir
    - CALIBRATOR_ENABLED=true + eşleşme yok → polymarket_calibration eklenmez
    - Sönüş aşamasındaki temalar watchlist'e eklenmez (kalibratör de çağrılmaz)
    - ETF'ler filtreleniyor (kalibratör de çağrılmaz)
    - Kalibratör init exception → tarama devam eder
    - Per-ticker calibrate exception → o ticker calibration_info=None
"""
from __future__ import annotations

import pytest


def _setup_thematic_mocks(monkeypatch, wl_add_calls):
    """Ortak mock kurulumu — apply_themes için."""
    from agent.scanners import thematic

    # watchlist_add → çağrıları kaydet, "added" döndür
    def fake_wl_add(**kwargs):
        wl_add_calls.append(kwargs)
        return {"action": "added"}
    monkeypatch.setattr(thematic, "watchlist_add", fake_wl_add)

    # add_theme → no-op
    monkeypatch.setattr(thematic, "add_theme",
                        lambda **kwargs: {"action": "added"})

    return thematic


# ── Flag kapalı ────────────────────────────────────────────────────────────────


class TestThematicCalibratorFlagOff:
    def test_no_calibrator_no_polymarket_field(self, monkeypatch):
        monkeypatch.delenv("CALIBRATOR_ENABLED", raising=False)
        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "ai_chips",
                "name": "AI Chips",
                "description": "...",
                "related_tickers": ["NVDA", "AMD"],
                "lifecycle_stage": "yukselis",
                "momentum_score": 75,
                "signals": {},
                "evidence": [],
            }
        ]}
        result = thematic.apply_themes(payload, mode="daily")

        # 2 ticker watchlist'e eklendi
        assert result["watchlist_added"] == 2
        assert len(wl_add_calls) == 2
        # Hiçbirinde polymarket_calibration yok
        for call in wl_add_calls:
            sc = call["score_components"]
            assert "polymarket_calibration" not in sc
            # Mevcut alanlar hâlâ var
            assert sc["thematic_momentum"] == 75


# ── Flag açık ──────────────────────────────────────────────────────────────────


class TestThematicCalibratorFlagOn:
    def _setup_calibrator(self, monkeypatch, tmp_path, theme_config, market_data):
        """PolymarketCalibrator + themes + cache mock."""
        # Tracker'ı tmp'ye yönlendir
        from agent.scanners import calibrator as cal_module
        original_init = cal_module.PolymarketCalibrator.__init__
        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("performance_log_path", tmp_path / "perf.json")
            original_init(self, *args, **kwargs)
        monkeypatch.setattr(cal_module.PolymarketCalibrator, "__init__", patched_init)

        from agent import polymarket
        monkeypatch.setattr(polymarket, "load_themes",
                            lambda: {"themes": theme_config})
        monkeypatch.setattr(polymarket, "load_cache",
                            lambda: {"markets": market_data})

    def test_positive_ticker_matches(self, monkeypatch, tmp_path):
        """LMT positive_tickers'da → pm_confirm score_components'a kaydedilir."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        self._setup_calibrator(monkeypatch, tmp_path, theme_config={
            "china_taiwan": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["taiwan"], "min_volume_usd": 0,
            }
        }, market_data={"taiwan": {"delta_24h": 0.15, "volume": 1000000}})

        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "defense_2026",
                "name": "Defense 2026",
                "description": "...",
                "related_tickers": ["LMT"],
                "lifecycle_stage": "yukselis",
                "momentum_score": 80,
                "signals": {},
                "evidence": [],
            }
        ]}
        thematic.apply_themes(payload, mode="daily")

        assert len(wl_add_calls) == 1
        sc = wl_add_calls[0]["score_components"]
        assert "polymarket_calibration" in sc
        assert "pm_confirm" in sc["polymarket_calibration"]["flags"]
        assert sc["polymarket_calibration"]["multiplier"] == 1.20
        # Mevcut tematik alanları korundu
        assert sc["thematic_momentum"] == 80
        assert sc["thematic_id"] == "defense_2026"

    def test_negative_ticker_conflict(self, monkeypatch, tmp_path):
        """TSM negative_tickers'da, market yükselişi → pm_conflict."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        self._setup_calibrator(monkeypatch, tmp_path, theme_config={
            "china_taiwan": {
                "positive_tickers": [], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["taiwan"], "min_volume_usd": 0,
            }
        }, market_data={"taiwan": {"delta_24h": 0.15, "volume": 1000000}})

        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "semiconductor",
                "name": "Semi",
                "description": "...",
                "related_tickers": ["TSM"],
                "lifecycle_stage": "yukselis",
                "momentum_score": 70,
                "signals": {},
                "evidence": [],
            }
        ]}
        thematic.apply_themes(payload, mode="daily")

        sc = wl_add_calls[0]["score_components"]
        assert "polymarket_calibration" in sc
        assert "pm_conflict" in sc["polymarket_calibration"]["flags"]

    def test_no_match_no_polymarket_field(self, monkeypatch, tmp_path):
        """Hiçbir temada olmayan ticker → polymarket_calibration eklenmez."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        self._setup_calibrator(monkeypatch, tmp_path, theme_config={
            "china_taiwan": {
                "positive_tickers": ["LMT"], "negative_tickers": ["TSM"],
                "polymarket_slugs": ["taiwan"], "min_volume_usd": 0,
            }
        }, market_data={"taiwan": {"delta_24h": 0.15, "volume": 1000000}})

        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "ai_chips",
                "name": "AI Chips",
                "description": "...",
                "related_tickers": ["NVDA"],
                "lifecycle_stage": "yukselis",
                "momentum_score": 70,
                "signals": {},
                "evidence": [],
            }
        ]}
        thematic.apply_themes(payload, mode="daily")

        sc = wl_add_calls[0]["score_components"]
        assert "polymarket_calibration" not in sc
        # Mevcut alanlar var
        assert sc["thematic_momentum"] == 70

    def test_dying_theme_no_calibration(self, monkeypatch, tmp_path):
        """Sönüş temaları zaten watchlist'e gitmiyor → kalibrasyon da çağrılmaz."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        self._setup_calibrator(monkeypatch, tmp_path, theme_config={
            "any_theme": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["s1"], "min_volume_usd": 0,
            }
        }, market_data={"s1": {"delta_24h": 0.15, "volume": 1000000}})

        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "dying",
                "name": "Dying",
                "description": "...",
                "related_tickers": ["LMT"],
                "lifecycle_stage": "sönüs",  # sönüş = watchlist'e eklenmez
                "momentum_score": 30,
                "signals": {},
                "evidence": [],
            }
        ]}
        result = thematic.apply_themes(payload, mode="daily")

        # Watchlist'e hiç eklenmedi
        assert result["watchlist_added"] == 0
        assert len(wl_add_calls) == 0

    def test_etf_filtered_no_calibration(self, monkeypatch, tmp_path):
        """ETF'ler zaten watchlist'e eklenmiyor → kalibrasyon da yapılmaz."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        self._setup_calibrator(monkeypatch, tmp_path, theme_config={
            "any_theme": {
                "positive_tickers": ["SPY"], "negative_tickers": [],
                "polymarket_slugs": ["s1"], "min_volume_usd": 0,
            }
        }, market_data={"s1": {"delta_24h": 0.15, "volume": 1000000}})

        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "market_etfs",
                "name": "Market ETFs",
                "description": "...",
                "related_tickers": ["SPY"],  # ETF, filtreleniyor
                "lifecycle_stage": "yukselis",
                "momentum_score": 70,
                "signals": {},
                "evidence": [],
            }
        ]}
        thematic.apply_themes(payload, mode="daily")

        # SPY ETF olduğu için watchlist'e eklenmedi
        assert len(wl_add_calls) == 0


# ── Resilience ─────────────────────────────────────────────────────────────────


class TestThematicCalibratorResilience:
    def test_calibrator_init_error_continues(self, monkeypatch):
        """PolymarketCalibrator() exception → apply_themes devam eder."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        from agent.scanners import calibrator as cal_module

        class _BrokenCal:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("init failed")

        monkeypatch.setattr(cal_module, "PolymarketCalibrator", _BrokenCal)

        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "t1", "name": "Test", "description": "",
                "related_tickers": ["XYZ"],
                "lifecycle_stage": "yukselis", "momentum_score": 60,
                "signals": {}, "evidence": [],
            }
        ]}
        result = thematic.apply_themes(payload, mode="daily")

        # Tarama tamamlandı, watchlist'e eklendi (polymarket_calibration yok)
        assert result["watchlist_added"] == 1
        sc = wl_add_calls[0]["score_components"]
        assert "polymarket_calibration" not in sc

    def test_per_ticker_calibrate_exception_continues(self, monkeypatch):
        """Bir ticker'ın kalibrasyonu çökerse sonraki ticker etkilenmez."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        from agent.scanners import calibrator as cal_module
        call_count = {"n": 0}

        class _PartiallyBrokenCal:
            def __init__(self, *args, **kwargs):
                pass

            def calibrate(self, candidates):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise RuntimeError("cache corrupt")
                # 2. ticker için: hiçbir bayrak yok (None themes)
                return candidates

        monkeypatch.setattr(cal_module, "PolymarketCalibrator", _PartiallyBrokenCal)

        wl_add_calls = []
        thematic = _setup_thematic_mocks(monkeypatch, wl_add_calls)

        payload = {"themes": [
            {
                "id": "multi", "name": "Multi", "description": "",
                "related_tickers": ["AAA", "BBB"],
                "lifecycle_stage": "yukselis", "momentum_score": 60,
                "signals": {}, "evidence": [],
            }
        ]}
        result = thematic.apply_themes(payload, mode="daily")

        # 2 ticker eklendi (her ikisinde de polymarket_calibration yok)
        assert result["watchlist_added"] == 2
        for call in wl_add_calls:
            assert "polymarket_calibration" not in call["score_components"]
        # Kalibrate iki kez çağrıldı
        assert call_count["n"] == 2
