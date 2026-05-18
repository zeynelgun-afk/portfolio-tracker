"""agent/legacy/analist_takip/monitor.py kalibratör entegrasyonu testleri.

Faz 2 — Adım 10b-iii-C-iii: monitor.py'a Polymarket kalibratör hook.

KAPSAM: monitor.py karmaşık bağımlılıklara (DM_settings, signal_log,
revision_fetcher, Telegram, FMP) sahip — full _run_polling_cycle simülasyonu
yerine kalibratör entegrasyonunun kritik noktalarını doğrularız.

    - _run_polling_cycle imzasında calibrator init kod yolu test edilir
    - STRONG_BUY blokundaki AI Gate çağrısının calibration_info parametresi
    - score_components'a polymarket_calibration ekleme
    - Geriye uyumluluk: flag kapalıyken hiçbir şey değişmedi
"""
from __future__ import annotations

import inspect
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ── Sözdizimsel doğrulama (kod yolu var mı) ─────────────────────────────────────


class TestSourceLevelIntegration:
    """monitor.py kaynak kodunda entegrasyon doğru noktada mı?"""

    def test_calibrator_init_present(self):
        """_run_polling_cycle fonksiyonu calibrator init kod yoluna sahip."""
        from agent.legacy.analist_takip import monitor
        src = inspect.getsource(monitor._run_polling_cycle)
        # Calibrator import + instantiation patterns
        assert "is_calibrator_enabled" in src
        assert "PolymarketCalibrator" in src
        assert "calibrator = None" in src
        assert "calibrator" in src

    def test_calibration_info_to_ai_gate(self):
        """AI Gate çağrısına calibration_info parametresi geçiliyor."""
        from agent.legacy.analist_takip import monitor
        src = inspect.getsource(monitor._run_polling_cycle)
        # ai_gate_eval çağrısında parametre var mı
        assert "calibration_info=calibration_info" in src

    def test_score_components_calibration_field(self):
        """score_components'a polymarket_calibration alanı eklenebilir mi."""
        from agent.legacy.analist_takip import monitor
        src = inspect.getsource(monitor._run_polling_cycle)
        assert "polymarket_calibration" in src
        assert 'score_components_dict["polymarket_calibration"]' in src or \
               "polymarket_calibration\"]" in src

    def test_defensive_calibrator_init_try_except(self):
        """Calibrator init try/except içinde — exception graceful."""
        from agent.legacy.analist_takip import monitor
        src = inspect.getsource(monitor._run_polling_cycle)
        # Try bloku + except + calibrator = None
        assert "try:" in src
        assert "except Exception" in src
        # Init hatası graceful — calibrator None'a düşer
        assert "Kalibratör başlatma hatası" in src

    def test_defensive_per_ticker_calibrate_try_except(self):
        """Probe.calibrate exception graceful — calibration_info=None."""
        from agent.legacy.analist_takip import monitor
        src = inspect.getsource(monitor._run_polling_cycle)
        # Per-ticker exception mesajı
        assert "kalibrasyon hatası" in src.lower()


# ── Davranış doğrulaması — kalibratör enable kontrolü ──────────────────────────


class TestCalibratorEnableLogic:
    """Flag açık/kapalı kod yolu doğru çalışıyor mu."""

    def test_flag_off_no_calibrator(self, monkeypatch):
        """CALIBRATOR_ENABLED=false → is_calibrator_enabled False döner."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "false")
        from agent.scanners.pipeline import is_calibrator_enabled
        assert is_calibrator_enabled() is False

    def test_flag_on_calibrator(self, monkeypatch):
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        from agent.scanners.pipeline import is_calibrator_enabled
        assert is_calibrator_enabled() is True

    def test_flag_unset_default_false(self, monkeypatch):
        monkeypatch.delenv("CALIBRATOR_ENABLED", raising=False)
        from agent.scanners.pipeline import is_calibrator_enabled
        assert is_calibrator_enabled() is False


# ── Kalibratör probe akışı (izole) ─────────────────────────────────────────────


class TestCalibratorProbePattern:
    """monitor.py'daki probe pattern'i tek başına çalıştırılabilir mi."""

    def test_probe_calibration_with_match(self, monkeypatch, tmp_path):
        """Tek elemanlı probe ile kalibrasyon → has_calibration True."""
        # Tracker'ı tmp'ye yönlendir
        from agent.scanners import calibrator as cal_module
        original_init = cal_module.PolymarketCalibrator.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("performance_log_path", tmp_path / "perf.json")
            original_init(self, *args, **kwargs)
        monkeypatch.setattr(cal_module.PolymarketCalibrator, "__init__", patched_init)

        # Themes + cache mock
        from agent import polymarket
        monkeypatch.setattr(polymarket, "load_themes", lambda: {"themes": {
            "test_theme": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["s1"], "min_volume_usd": 0,
            }
        }})
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {
            "s1": {"delta_24h": 0.15, "volume": 1000000}
        }})

        # Probe pattern (monitor.py'dan)
        from agent.scanners.calibrator import PolymarketCalibrator
        from agent.scanners.base import Candidate

        cal = PolymarketCalibrator()
        probe = Candidate(symbol="LMT", score=0.5,
                          reason="analyst_revisions probe",
                          source="analyst_revisions")
        cal.calibrate([probe])

        assert probe.has_calibration is True
        assert "pm_confirm" in probe.calibration_flags
        assert probe.calibration_multiplier == 1.20

        # monitor.py'daki calibration_info dict oluşturma
        calibration_info = {
            "flags": probe.calibration_flags,
            "multiplier": probe.calibration_multiplier,
            "original_score": probe.score,
            "calibrated_score": probe.calibrated_score,
        }
        assert calibration_info["flags"] == ["pm_confirm"]
        assert calibration_info["multiplier"] == 1.20

    def test_probe_no_match_returns_no_calibration(self, monkeypatch, tmp_path):
        """Eşleşme yoksa probe.has_calibration False — calibration_info=None."""
        from agent.scanners import calibrator as cal_module
        original_init = cal_module.PolymarketCalibrator.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("performance_log_path", tmp_path / "perf.json")
            original_init(self, *args, **kwargs)
        monkeypatch.setattr(cal_module.PolymarketCalibrator, "__init__", patched_init)

        from agent import polymarket
        monkeypatch.setattr(polymarket, "load_themes", lambda: {"themes": {
            "test_theme": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["s1"], "min_volume_usd": 0,
            }
        }})
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {
            "s1": {"delta_24h": 0.15, "volume": 1000000}
        }})

        from agent.scanners.calibrator import PolymarketCalibrator
        from agent.scanners.base import Candidate

        cal = PolymarketCalibrator()
        # NVDA hiçbir temada yok
        probe = Candidate(symbol="NVDA", score=0.5,
                          reason="probe", source="analyst_revisions")
        cal.calibrate([probe])

        assert probe.has_calibration is False
        # monitor.py mantığı: has_calibration False → calibration_info None bırak
        calibration_info = None
        if probe.has_calibration:
            calibration_info = {"flags": probe.calibration_flags}
        assert calibration_info is None
