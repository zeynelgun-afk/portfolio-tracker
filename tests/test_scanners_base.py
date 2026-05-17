"""agent/scanners/base.py için kapsamlı testler.

Faz 2 — Scanner konsolidasyonu (17 May 2026).

KAPSAM:
    - Candidate yaratım + normalize (symbol uppercase, score sınırı)
    - calibrated_score property
    - has_calibration property
    - apply_calibration tekli çağrı (confirm, conflict)
    - apply_calibration çoklu çağrı (en aşırı kazanır + downside protection)
    - Bayrak whitelist enforcement
    - to_dict serialize
    - BaseScanner ABC enforcement (abstract scan zorunlu)
"""
from __future__ import annotations

import pytest

from agent.scanners.base import (
    ALLOWED_FLAGS,
    BaseScanner,
    CALIBRATION_MAX,
    CALIBRATION_MIN,
    CALIBRATION_NEUTRAL,
    Candidate,
    KNOWN_SOURCES,
)


# ── Candidate yaratım ──────────────────────────────────────────────────────────


class TestCandidateCreation:
    def test_basic(self):
        c = Candidate(symbol="aapl", score=0.7, reason="test", source="thematic")
        assert c.symbol == "AAPL"  # uppercase normalize
        assert c.score == 0.7
        assert c.calibration_multiplier == CALIBRATION_NEUTRAL
        assert c.calibration_flags == []

    def test_symbol_strip_uppercase(self):
        c = Candidate(symbol=" tsm ", score=0.5, reason="r", source="news")
        assert c.symbol == "TSM"

    def test_empty_symbol_rejected(self):
        with pytest.raises(ValueError, match="symbol boş"):
            Candidate(symbol="", score=0.5, reason="r", source="news")
        with pytest.raises(ValueError, match="symbol boş"):
            Candidate(symbol="   ", score=0.5, reason="r", source="news")

    def test_score_lower_bound(self):
        # 0.0 geçerli (sınır)
        Candidate(symbol="X", score=0.0, reason="r", source="news")
        with pytest.raises(ValueError, match="score"):
            Candidate(symbol="X", score=-0.1, reason="r", source="news")

    def test_score_upper_bound(self):
        Candidate(symbol="X", score=1.0, reason="r", source="news")
        with pytest.raises(ValueError, match="score"):
            Candidate(symbol="X", score=1.1, reason="r", source="news")

    def test_unknown_source_allowed(self):
        # Yeni scanner geliştirilirken esneklik — uyarı yok hata yok
        c = Candidate(symbol="X", score=0.5, reason="r", source="future_scanner")
        assert c.source == "future_scanner"

    def test_all_known_sources_work(self):
        for source in KNOWN_SOURCES:
            c = Candidate(symbol="X", score=0.5, reason="r", source=source)
            assert c.source == source


# ── Constructor'da kalibrasyon alanları ────────────────────────────────────────


class TestCandidateConstructorCalibration:
    def test_multiplier_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="multiplier"):
            Candidate(
                symbol="X", score=0.5, reason="r", source="news",
                calibration_multiplier=0.5,  # min altı
            )
        with pytest.raises(ValueError, match="multiplier"):
            Candidate(
                symbol="X", score=0.5, reason="r", source="news",
                calibration_multiplier=1.5,  # max üstü
            )

    def test_unknown_flag_rejected(self):
        with pytest.raises(ValueError, match="Bilinmeyen calibration_flag"):
            Candidate(
                symbol="X", score=0.5, reason="r", source="news",
                calibration_flags=["random_flag"],
            )

    def test_constructor_with_known_flag(self):
        c = Candidate(
            symbol="X", score=0.5, reason="r", source="news",
            calibration_multiplier=1.20,
            calibration_flags=["pm_confirm"],
        )
        assert "pm_confirm" in c.calibration_flags


# ── calibrated_score property ──────────────────────────────────────────────────


class TestCalibratedScore:
    def test_neutral_returns_score(self):
        c = Candidate(symbol="X", score=0.6, reason="r", source="news")
        assert c.calibrated_score == 0.6

    def test_amplify(self):
        c = Candidate(symbol="X", score=0.6, reason="r", source="news")
        c.apply_calibration(1.20, ["pm_confirm"])
        # 0.6 * 1.20 = 0.72
        assert abs(c.calibrated_score - 0.72) < 1e-9

    def test_reduce(self):
        c = Candidate(symbol="X", score=0.8, reason="r", source="news")
        c.apply_calibration(0.75, ["pm_conflict"])
        # 0.8 * 0.75 = 0.60
        assert abs(c.calibrated_score - 0.6) < 1e-9

    def test_clipped_at_one(self):
        c = Candidate(symbol="X", score=0.95, reason="r", source="news")
        c.apply_calibration(1.20, ["pm_confirm"])
        # 0.95 * 1.20 = 1.14, clipped → 1.0
        assert c.calibrated_score == 1.0


# ── has_calibration ────────────────────────────────────────────────────────────


class TestHasCalibration:
    def test_neutral_no_calibration(self):
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        assert c.has_calibration is False

    def test_after_apply(self):
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c.apply_calibration(1.10, ["pm_confirm_weak"])
        assert c.has_calibration is True


# ── apply_calibration çoklu çağrı (en aşırı kazanır) ───────────────────────────


class TestApplyCalibrationMulti:
    """Tasarım Bölüm 17: En aşırı çarpan kazanır, çelişki önceliklidir."""

    def test_two_confirms_higher_wins(self):
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c.apply_calibration(1.10, ["pm_confirm_weak"])
        c.apply_calibration(1.20, ["pm_confirm"])
        # En yüksek doğrulama kazanır
        assert c.calibration_multiplier == 1.20
        # İki bayrak da listede
        assert "pm_confirm_weak" in c.calibration_flags
        assert "pm_confirm" in c.calibration_flags

    def test_two_confirms_order_independent(self):
        c1 = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c1.apply_calibration(1.20, ["pm_confirm"])
        c1.apply_calibration(1.10, ["pm_confirm_weak"])

        c2 = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c2.apply_calibration(1.10, ["pm_confirm_weak"])
        c2.apply_calibration(1.20, ["pm_confirm"])

        assert c1.calibration_multiplier == c2.calibration_multiplier == 1.20

    def test_two_conflicts_lower_wins(self):
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c.apply_calibration(0.90, ["pm_conflict_weak"])
        c.apply_calibration(0.75, ["pm_conflict"])
        assert c.calibration_multiplier == 0.75

    def test_mixed_conflict_wins_downside_protection(self):
        """Bir çelişki + bir doğrulama → çelişki kazanır (downside protection)."""
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c.apply_calibration(1.20, ["pm_confirm"])
        c.apply_calibration(0.75, ["pm_conflict"])
        # 1.20 yerine 0.75 — çelişki önceliklidir
        assert c.calibration_multiplier == 0.75
        # Bayraklar birikti
        assert "pm_confirm" in c.calibration_flags
        assert "pm_conflict" in c.calibration_flags

    def test_mixed_order_independent(self):
        c1 = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c1.apply_calibration(1.20, ["pm_confirm"])
        c1.apply_calibration(0.75, ["pm_conflict"])

        c2 = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c2.apply_calibration(0.75, ["pm_conflict"])
        c2.apply_calibration(1.20, ["pm_confirm"])

        assert c1.calibration_multiplier == c2.calibration_multiplier == 0.75

    def test_duplicate_flags_deduped(self):
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        c.apply_calibration(1.20, ["pm_confirm"])
        c.apply_calibration(1.20, ["pm_confirm"])
        assert c.calibration_flags.count("pm_confirm") == 1


# ── apply_calibration validation ───────────────────────────────────────────────


class TestApplyCalibrationValidation:
    def test_invalid_multiplier(self):
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        with pytest.raises(ValueError):
            c.apply_calibration(0.5, ["pm_conflict"])
        with pytest.raises(ValueError):
            c.apply_calibration(1.5, ["pm_confirm"])

    def test_invalid_flag(self):
        c = Candidate(symbol="X", score=0.5, reason="r", source="news")
        with pytest.raises(ValueError, match="Bilinmeyen flag"):
            c.apply_calibration(1.10, ["random_flag"])


# ── to_dict serialize ──────────────────────────────────────────────────────────


class TestToDict:
    def test_serialize_neutral(self):
        c = Candidate(
            symbol="AAPL", score=0.7, reason="strong AL",
            source="thematic", metadata={"theme": "ai"},
        )
        d = c.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["score"] == 0.7
        assert d["calibrated_score"] == 0.7
        assert d["source"] == "thematic"
        assert d["metadata"] == {"theme": "ai"}
        assert d["calibration_multiplier"] == 1.0
        assert d["calibration_flags"] == []

    def test_serialize_calibrated(self):
        c = Candidate(symbol="TSM", score=0.8, reason="r", source="thematic")
        c.apply_calibration(0.75, ["pm_conflict"])
        d = c.to_dict()
        assert d["calibrated_score"] == pytest.approx(0.6)
        assert d["calibration_multiplier"] == 0.75
        assert d["calibration_flags"] == ["pm_conflict"]


# ── BaseScanner ABC ────────────────────────────────────────────────────────────


class TestBaseScannerABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseScanner()  # type: ignore[abstract]

    def test_concrete_scanner_works(self):
        class _DummyScanner(BaseScanner):
            name = "dummy"

            def scan(self) -> list[Candidate]:
                return [Candidate(symbol="X", score=0.5, reason="r", source="news")]

        s = _DummyScanner()
        results = s.scan()
        assert len(results) == 1
        assert results[0].symbol == "X"

    def test_health_check_default(self):
        class _DummyScanner(BaseScanner):
            name = "dummy"

            def scan(self) -> list[Candidate]:
                return []

        s = _DummyScanner()
        h = s.health_check()
        assert h["name"] == "dummy"
        assert h["ok"] is True

    def test_health_check_override(self):
        class _DummyScanner(BaseScanner):
            name = "dummy"

            def scan(self) -> list[Candidate]:
                return []

            def health_check(self) -> dict:
                return {"name": self.name, "ok": False, "reason": "API down"}

        s = _DummyScanner()
        h = s.health_check()
        assert h["ok"] is False
        assert h["reason"] == "API down"


# ── Sabitler kontrol ───────────────────────────────────────────────────────────


class TestConstants:
    def test_calibration_range_sane(self):
        assert CALIBRATION_MIN < CALIBRATION_NEUTRAL < CALIBRATION_MAX
        assert CALIBRATION_MIN == 0.75
        assert CALIBRATION_MAX == 1.20

    def test_all_flag_pairs_present(self):
        """Tasarım Bölüm 8'deki 4 bayrak listede."""
        expected = {"pm_confirm", "pm_confirm_weak", "pm_conflict_weak", "pm_conflict"}
        assert expected == ALLOWED_FLAGS
