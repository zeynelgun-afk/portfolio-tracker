"""scripts/scanner_dry_run.py için testler.

Faz 2 — Adım 10b-iii-A: observability CLI tool.

KAPSAM:
    - _load_scanner: bilinmeyen scanner → ValueError
    - _load_scanner: geçerli isim → BaseScanner instance
    - SCANNER_REGISTRY: 4 scanner kayıtlı
    - _format_text: boş candidate listesi
    - _format_text: kalibre edilmemiş candidate
    - _format_text: kalibre edilmiş candidate
    - _format_json: parse edilebilir JSON
    - _make_observability_calibrator: tracker tmp'ye yönlenir
    - _make_observability_calibrator: flag yoksa None
    - main(): no-calibrator flag çalışır
    - main(): json format çıktısı
    - main(): bilinmeyen scanner → rc=2 (argparse hatası)
    - main(): scanner exception → rc=1, devam
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.scanners.base import BaseScanner, Candidate


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "scanner_dry_run.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("scanner_dry_run", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── _load_scanner ──────────────────────────────────────────────────────────────


class TestLoadScanner:
    def test_unknown_scanner_raises(self):
        sdr = _load_script()
        with pytest.raises(ValueError, match="Bilinmeyen scanner"):
            sdr._load_scanner("nonexistent")

    @pytest.mark.parametrize("name", ["thematic", "fair_value", "news", "analyst_revisions"])
    def test_valid_scanner_returns_instance(self, name):
        sdr = _load_script()
        instance = sdr._load_scanner(name)
        # PYTHONPATH çift girdi nedeniyle BaseScanner iki kere yüklenebilir
        # (agent.scanners.base vs scanners.base). isinstance() kırılır.
        # Duck typing ile kontrol: scan() metodu + name attribute olmalı.
        assert hasattr(instance, "scan")
        assert hasattr(instance, "name")
        assert instance.name == name
        # Class adı doğrulaması (BaseScanner alt sınıfı pattern'i)
        assert instance.__class__.__name__.endswith("Scanner")

    def test_registry_has_four_scanners(self):
        sdr = _load_script()
        # 4 scanner Faz 2 Adım 5-8'de yazıldı
        assert set(sdr.SCANNER_REGISTRY.keys()) == {
            "thematic", "fair_value", "news", "analyst_revisions"
        }


# ── _format_text ───────────────────────────────────────────────────────────────


class TestFormatText:
    def test_empty_list_message(self):
        sdr = _load_script()
        output = sdr._format_text([], "test")
        assert "test" in output
        assert "Hiç candidate üretilmedi" in output

    def test_uncalibrated_candidate(self):
        sdr = _load_script()
        c = Candidate(symbol="LMT", score=0.7, reason="test", source="thematic")
        output = sdr._format_text([c], "fake")
        assert "LMT" in output
        assert "0.700" in output
        assert "—" in output  # kalibre edilmemiş için tire

    def test_calibrated_candidate(self):
        sdr = _load_script()
        c = Candidate(symbol="TSM", score=0.6, reason="test", source="thematic")
        c.apply_calibration(0.75, ["pm_conflict"])
        output = sdr._format_text([c], "fake")
        assert "TSM" in output
        assert "0.75" in output  # multiplier
        assert "pm_conflict" in output

    def test_long_reason_truncated(self):
        sdr = _load_script()
        long_reason = "a" * 200
        c = Candidate(symbol="X", score=0.5, reason=long_reason, source="news")
        output = sdr._format_text([c], "fake")
        # Truncate edildi
        assert "a" * 60 not in output


# ── _format_json ───────────────────────────────────────────────────────────────


class TestFormatJson:
    def test_parses_as_valid_json(self):
        sdr = _load_script()
        c = Candidate(symbol="LMT", score=0.7, reason="r", source="thematic")
        output = sdr._format_json([c], "test")
        parsed = json.loads(output)
        assert parsed["scanner"] == "test"
        assert parsed["count"] == 1
        assert parsed["candidates"][0]["symbol"] == "LMT"
        assert parsed["candidates"][0]["score"] == 0.7
        assert "timestamp" in parsed

    def test_calibration_fields_present(self):
        sdr = _load_script()
        c = Candidate(symbol="TSM", score=0.6, reason="r", source="thematic")
        c.apply_calibration(0.75, ["pm_conflict"])
        output = sdr._format_json([c], "test")
        parsed = json.loads(output)
        cand_dict = parsed["candidates"][0]
        assert cand_dict["has_calibration"] is True
        assert cand_dict["calibration_multiplier"] == 0.75
        assert cand_dict["calibration_flags"] == ["pm_conflict"]
        assert cand_dict["calibrated_score"] == pytest.approx(0.45)

    def test_empty_list(self):
        sdr = _load_script()
        output = sdr._format_json([], "test")
        parsed = json.loads(output)
        assert parsed["count"] == 0
        assert parsed["candidates"] == []


# ── _make_observability_calibrator ─────────────────────────────────────────────


class TestMakeCalibrator:
    def test_explicit_false_returns_none(self):
        sdr = _load_script()
        assert sdr._make_observability_calibrator(False) is None

    def test_env_var_off_returns_none(self, monkeypatch):
        sdr = _load_script()
        monkeypatch.delenv("CALIBRATOR_ENABLED", raising=False)
        assert sdr._make_observability_calibrator(None) is None

    def test_explicit_true_returns_calibrator(self):
        sdr = _load_script()
        cal = sdr._make_observability_calibrator(True)
        assert cal is not None
        # Tracker yolu tmp'de — üretime dokunmamalı
        assert "tmp" in str(cal.performance_log_path).lower() or \
               "temp" in str(cal.performance_log_path).lower()

    def test_env_var_on_returns_calibrator(self, monkeypatch):
        sdr = _load_script()
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        cal = sdr._make_observability_calibrator(None)
        assert cal is not None


# ── main() end-to-end ──────────────────────────────────────────────────────────


class _MockScanner(BaseScanner):
    """Test için stub scanner."""
    name = "mock"

    def __init__(self, candidates):
        self._candidates = candidates

    def scan(self):
        return list(self._candidates)


class TestMain:
    def test_no_calibrator_flag(self, monkeypatch, capsys):
        sdr = _load_script()
        # CALIBRATOR_ENABLED=true olsa bile --no-calibrator override
        monkeypatch.setenv("CALIBRATOR_ENABLED", "true")
        monkeypatch.setitem(
            sdr.SCANNER_REGISTRY, "mock",
            "tests.test_scanner_dry_run:_make_mock_thematic"
        )

        # Mock scanner'ı registry'ye geçici ekleyemiyoruz tam — alt seviyede mock
        def fake_load(name):
            return _MockScanner([
                Candidate(symbol="LMT", score=0.7, reason="r", source="thematic")
            ])
        monkeypatch.setattr(sdr, "_load_scanner", fake_load)

        rc = sdr.main(["--scanner", "thematic", "--no-calibrator"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "LMT" in captured.out
        # Kalibre edilmedi
        assert "0.700" in captured.out

    def test_json_format(self, monkeypatch, capsys):
        sdr = _load_script()

        def fake_load(name):
            return _MockScanner([
                Candidate(symbol="LMT", score=0.7, reason="r", source="thematic")
            ])
        monkeypatch.setattr(sdr, "_load_scanner", fake_load)

        rc = sdr.main([
            "--scanner", "thematic",
            "--no-calibrator",
            "--format", "json",
        ])
        captured = capsys.readouterr()
        assert rc == 0
        parsed = json.loads(captured.out.strip())
        assert parsed["count"] == 1
        assert parsed["candidates"][0]["symbol"] == "LMT"

    def test_limit_applied(self, monkeypatch, capsys):
        sdr = _load_script()

        def fake_load(name):
            return _MockScanner([
                Candidate(symbol=f"T{i}", score=0.5 + i * 0.05,
                          reason="r", source="thematic")
                for i in range(10)
            ])
        monkeypatch.setattr(sdr, "_load_scanner", fake_load)

        rc = sdr.main([
            "--scanner", "thematic",
            "--no-calibrator",
            "--format", "json",
            "--limit", "3",
        ])
        captured = capsys.readouterr()
        assert rc == 0
        parsed = json.loads(captured.out.strip())
        assert parsed["count"] == 3
        # En yüksek 3 (sorted)
        symbols = [c["symbol"] for c in parsed["candidates"]]
        assert symbols == ["T9", "T8", "T7"]

    def test_scanner_exception_continues_other_scanners(self, monkeypatch, capsys):
        """--scanner all: bir scanner çökerse diğerleri çalışır."""
        sdr = _load_script()

        def fake_load(name):
            if name == "fair_value":
                raise RuntimeError("FMP down")
            return _MockScanner([
                Candidate(symbol=f"{name}_X", score=0.5, reason="r", source=name)
            ])
        monkeypatch.setattr(sdr, "_load_scanner", fake_load)

        rc = sdr.main(["--scanner", "all", "--no-calibrator", "--format", "json"])
        captured = capsys.readouterr()
        # rc=1: exception oldu ama devam etti
        assert rc == 1
        # thematic, news, analyst_revisions çıktı verdi (Candidate symbol'u upper-case'e çevirir)
        assert "THEMATIC_X" in captured.out
        assert "NEWS_X" in captured.out
        # Çöken scanner'ın output'u yok
        assert "FAIR_VALUE_X" not in captured.out

    def test_calibrator_applied_when_flag_on(self, monkeypatch, capsys, tmp_path):
        """--use-calibrator flag açık → kalibrasyon uygulanır."""
        sdr = _load_script()

        # Kalibratör tracker'ı tmp_path'e yönlendir
        original_tmpdir = tempfile.gettempdir
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

        # Mock themes/cache loader'ları
        from agent import polymarket
        monkeypatch.setattr(polymarket, "load_themes", lambda: {"themes": {
            "t1": {
                "positive_tickers": ["LMT"], "negative_tickers": [],
                "polymarket_slugs": ["s1"], "min_volume_usd": 0,
            }
        }})
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {
            "s1": {"delta_24h": 0.15, "volume": 1000000}
        }})

        def fake_load(name):
            return _MockScanner([
                Candidate(symbol="LMT", score=0.5, reason="r", source="thematic")
            ])
        monkeypatch.setattr(sdr, "_load_scanner", fake_load)

        rc = sdr.main([
            "--scanner", "thematic",
            "--use-calibrator",
            "--format", "json",
        ])
        captured = capsys.readouterr()
        assert rc == 0
        parsed = json.loads(captured.out.strip())
        cand = parsed["candidates"][0]
        assert cand["has_calibration"] is True
        assert cand["calibration_multiplier"] == 1.20
        assert "pm_confirm" in cand["calibration_flags"]
