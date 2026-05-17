"""agent/scanners/pipeline.py için testler.

Faz 2 — Adım 10b-ii: scan_and_calibrate orchestration helper.

KAPSAM:
    - is_calibrator_enabled feature flag env var davranışı
    - Truthy/falsy değerler (case-insensitive)
    - scan_and_calibrate flag kapalı → raw scan çıktısı
    - scan_and_calibrate flag açık + candidate'lar → kalibrasyon
    - scan_and_calibrate flag açık + boş scan → kalibratör çağrılmaz
    - scan_and_calibrate explicit flag override env var
    - scan_and_calibrate explicit calibrator instance kullanılır
    - Lazy import: flag kapalıyken PolymarketCalibrator import edilmez
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.scanners.base import BaseScanner, Candidate
from agent.scanners.pipeline import scan_and_calibrate, is_calibrator_enabled


# ── Test scanner helper ────────────────────────────────────────────────────────


class _StubScanner(BaseScanner):
    """Verilen candidate listesini scan() ile döndüren stub."""
    name = "stub"

    def __init__(self, candidates: list[Candidate]):
        self._candidates = candidates
        self.scan_call_count = 0

    def scan(self) -> list[Candidate]:
        self.scan_call_count += 1
        return list(self._candidates)  # copy


class _ExceptionScanner(BaseScanner):
    """scan() exception fırlatan scanner — error propagation testi."""
    name = "exception"

    def scan(self) -> list[Candidate]:
        raise RuntimeError("scan failed")


# ── is_calibrator_enabled ──────────────────────────────────────────────────────


class TestIsCalibratorEnabled:
    def test_env_var_missing_returns_false(self, monkeypatch):
        monkeypatch.delenv("CALIBRATOR_ENABLED", raising=False)
        assert is_calibrator_enabled() is False

    @pytest.mark.parametrize("value", [
        "true", "TRUE", "True", "tRuE",
        "1",
        "yes", "YES", "Yes",
    ])
    def test_truthy_values(self, monkeypatch, value):
        monkeypatch.setenv("CALIBRATOR_ENABLED", value)
        assert is_calibrator_enabled() is True

    @pytest.mark.parametrize("value", [
        "false", "FALSE", "False",
        "0",
        "no", "NO",
        "",
        "  ",
        "something_else",
        "2",  # sadece "1" truthy
        "y",  # sadece "yes" truthy, "y" değil
        "on",  # bilerek desteklemiyoruz
    ])
    def test_falsy_values(self, monkeypatch, value):
        monkeypatch.setenv("CALIBRATOR_ENABLED", value)
        assert is_calibrator_enabled() is False

    def test_whitespace_trimmed(self, monkeypatch):
        """Trailing/leading whitespace temizlenir."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "  true  ")
        assert is_calibrator_enabled() is True


# ── scan_and_calibrate ─────────────────────────────────────────────────────────


class TestScanAndCalibrate:
    def _candidate(self, symbol: str, score: float = 0.7) -> Candidate:
        return Candidate(
            symbol=symbol, score=score, reason="test", source="thematic"
        )

    def test_flag_disabled_returns_raw(self, monkeypatch):
        """Flag kapalı → kalibratör çağrılmaz, raw scan çıktısı döner."""
        monkeypatch.delenv("CALIBRATOR_ENABLED", raising=False)
        scanner = _StubScanner([
            self._candidate("LMT"),
            self._candidate("AAPL"),
        ])
        result = scan_and_calibrate(scanner)
        assert len(result) == 2
        # Hiçbiri kalibre edilmedi
        assert all(not c.has_calibration for c in result)
        # scan() bir kez çağrıldı
        assert scanner.scan_call_count == 1

    def test_flag_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("CALIBRATOR_ENABLED", "false")
        scanner = _StubScanner([self._candidate("LMT")])
        result = scan_and_calibrate(scanner)
        assert not result[0].has_calibration

    def test_flag_enabled_applies_calibration(self, monkeypatch, tmp_path):
        """Flag açık + match → kalibrasyon uygulanır."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        from agent.scanners.calibrator import PolymarketCalibrator
        cal = PolymarketCalibrator(
            themes_loader=lambda: {"themes": {
                "t1": {
                    "positive_tickers": ["LMT"], "negative_tickers": [],
                    "polymarket_slugs": ["slug-1"], "min_volume_usd": 0,
                }
            }},
            cache_loader=lambda: {"markets": {
                "slug-1": {"delta_24h": 0.15, "volume": 1000000}
            }},
            performance_log_path=tmp_path / "perf.json",
        )

        scanner = _StubScanner([self._candidate("LMT", 0.5)])
        result = scan_and_calibrate(scanner, calibrator=cal)

        assert len(result) == 1
        assert result[0].calibration_multiplier == 1.20
        assert "pm_confirm" in result[0].calibration_flags

    def test_explicit_flag_overrides_env(self, monkeypatch, tmp_path):
        """calibrator_enabled=True env var false olsa da uygulanır."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "false")  # env kapalı

        from agent.scanners.calibrator import PolymarketCalibrator
        cal = PolymarketCalibrator(
            themes_loader=lambda: {"themes": {
                "t1": {
                    "positive_tickers": ["LMT"], "negative_tickers": [],
                    "polymarket_slugs": ["s1"], "min_volume_usd": 0,
                }
            }},
            cache_loader=lambda: {"markets": {
                "s1": {"delta_24h": 0.15, "volume": 1000000}
            }},
            performance_log_path=tmp_path / "perf.json",
        )

        scanner = _StubScanner([self._candidate("LMT")])
        # Override ile aktive et
        result = scan_and_calibrate(scanner, calibrator_enabled=True, calibrator=cal)
        assert result[0].has_calibration is True

    def test_explicit_flag_false_overrides_env(self, monkeypatch):
        """calibrator_enabled=False env var true olsa da uygulanmaz."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        scanner = _StubScanner([self._candidate("LMT")])
        result = scan_and_calibrate(scanner, calibrator_enabled=False)
        assert result[0].has_calibration is False

    def test_empty_candidates_skips_calibrator(self, monkeypatch, tmp_path):
        """Boş scan çıktısı → kalibratör hiç çağrılmaz (gereksiz I/O atlanır)."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        # Calibrator instance — calibrate() çağrılırsa exception fırlatsın
        class _BoomCal:
            def calibrate(self, candidates):
                raise AssertionError("Boş listede kalibratör çağrılmamalı")

        scanner = _StubScanner([])  # boş scan
        result = scan_and_calibrate(scanner, calibrator=_BoomCal())
        assert result == []

    def test_scan_exception_propagates(self, monkeypatch):
        """scan() exception → scan_and_calibrate propagate eder."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        scanner = _ExceptionScanner()
        with pytest.raises(RuntimeError, match="scan failed"):
            scan_and_calibrate(scanner)

    def test_default_calibrator_lazy_import(self, monkeypatch, tmp_path):
        """Calibrator=None ise default PolymarketCalibrator yüklenir."""
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")

        # Default loader'ları stub'la — gerçek dosyaya dokunma
        from agent import polymarket
        monkeypatch.setattr(polymarket, "load_themes", lambda: {"themes": {}})
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {}})

        # Tracker'ı tmp_path'e yönlendir
        from agent.scanners import calibrator as cal_module
        original_init = cal_module.PolymarketCalibrator.__init__

        def _patched_init(self, *args, **kwargs):
            kwargs.setdefault("performance_log_path", tmp_path / "perf.json")
            original_init(self, *args, **kwargs)

        monkeypatch.setattr(cal_module.PolymarketCalibrator, "__init__", _patched_init)

        scanner = _StubScanner([self._candidate("AAPL")])
        result = scan_and_calibrate(scanner)
        # AAPL hiçbir temada yok → kalibratör çalışsa bile no-op
        assert len(result) == 1
        assert result[0].has_calibration is False

    def test_lazy_import_when_flag_disabled(self, monkeypatch):
        """Flag kapalıyken PolymarketCalibrator import edilmemeli.

        Bunu strict olarak test etmek zor (modül cache'lenmiş olabilir).
        Daha pratik: flag kapalıyken scan_and_calibrate exception fırlatmamalı,
        kalibratör instance'ı verilmemiş olsa bile.
        """
        monkeypatch.delenv("CALIBRATOR_ENABLED", raising=False)
        scanner = _StubScanner([self._candidate("LMT")])
        # calibrator=None ama flag kapalı → kalibratör hiç çağrılmaz
        # PolymarketCalibrator import zorunlu değil → exception yok
        result = scan_and_calibrate(scanner, calibrator=None)
        assert len(result) == 1
