"""agent/scanners/analyst_revisions.py için testler.

Faz 2 — Adım 8: AnalystRevisionsScanner adaptörü.

KAPSAM:
    - _build_candidate_from_decision: 9 (decision × confidence) kombinasyonu
    - NEUTRAL/SELL/STRONG_SELL → None
    - Eksik/bozuk decision dict → None
    - Eksik ticker → None
    - Default confidence (medium) fallback
    - AnalystRevisionsScanner instantiation + validation
    - _resolve_universe custom vs default davranışı
    - Scanner.scan() mocked legacy fonksiyonlarla end-to-end
    - Scanner.scan() ticker hatası diğerlerini etkilemez
    - health_check

Bu scanner DİĞERLERİNDEN FARKLI: kaynak dosya (monitor.py) yerinde kalıyor,
agent/scanners/analyst_revisions.py paralel bir adaptör. Test buna göre
yapılandırıldı — eski analist_takip_tick test edilmiyor (mevcut testler
ayrı, kapsam dışı).
"""
from __future__ import annotations

import pytest


# ── _build_candidate_from_decision: tablo doğrulama ────────────────────────────


class TestBuildCandidate:
    def _import(self):
        from agent.scanners.analyst_revisions import _build_candidate_from_decision
        return _build_candidate_from_decision

    @pytest.mark.parametrize("decision,confidence,expected_score", [
        ("STRONG_BUY", "high", 0.95),
        ("STRONG_BUY", "medium", 0.855),
        ("STRONG_BUY", "low", 0.76),
        ("BUY", "high", 0.70),
        ("BUY", "medium", 0.63),
        ("BUY", "low", 0.56),
        ("WATCH", "high", 0.40),
        ("WATCH", "medium", 0.36),
        ("WATCH", "low", 0.32),
    ])
    def test_score_table(self, decision, confidence, expected_score):
        build = self._import()
        d = {
            "ticker": "X",
            "decision": decision,
            "confidence": confidence,
            "raised_count_48h": 2,
            "lowered_count_48h": 0,
            "avg_revision_pct": 15.0,
            "rationale": "test",
        }
        c = build(d)
        assert c is not None
        assert c.score == pytest.approx(expected_score, abs=1e-6)
        assert c.source == "analyst_revisions"
        assert c.symbol == "X"

    @pytest.mark.parametrize("filtered_decision", ["NEUTRAL", "SELL", "STRONG_SELL"])
    def test_bearish_filtered(self, filtered_decision):
        build = self._import()
        d = {
            "ticker": "X",
            "decision": filtered_decision,
            "confidence": "high",
            "raised_count_48h": 0,
            "lowered_count_48h": 5,
        }
        assert build(d) is None

    def test_unknown_decision_returns_none(self):
        build = self._import()
        d = {"ticker": "X", "decision": "MAYBE", "confidence": "high"}
        assert build(d) is None

    def test_missing_decision_returns_none(self):
        build = self._import()
        d = {"ticker": "X", "confidence": "high"}
        assert build(d) is None

    def test_missing_ticker_returns_none(self):
        build = self._import()
        d = {"decision": "BUY", "confidence": "high"}
        assert build(d) is None

    def test_empty_ticker_returns_none(self):
        build = self._import()
        d = {"ticker": "  ", "decision": "BUY", "confidence": "high"}
        assert build(d) is None

    def test_non_dict_returns_none(self):
        build = self._import()
        assert build(None) is None  # type: ignore[arg-type]
        assert build("string") is None  # type: ignore[arg-type]
        assert build([]) is None  # type: ignore[arg-type]

    def test_default_confidence_is_medium(self):
        build = self._import()
        d = {
            "ticker": "X",
            "decision": "BUY",
            # confidence eksik → default 'medium'
            "raised_count_48h": 1,
            "lowered_count_48h": 0,
        }
        c = build(d)
        assert c is not None
        # BUY × medium = 0.63
        assert c.score == pytest.approx(0.63)

    def test_unknown_confidence_falls_back_to_medium(self):
        build = self._import()
        d = {
            "ticker": "X",
            "decision": "BUY",
            "confidence": "extreme",  # bilinmeyen
            "raised_count_48h": 1,
            "lowered_count_48h": 0,
        }
        c = build(d)
        # Fallback medium → BUY × 0.9 = 0.63
        assert c.score == pytest.approx(0.63)

    def test_case_insensitive_decision(self):
        build = self._import()
        d = {
            "ticker": "X",
            "decision": "strong_buy",  # lowercase
            "confidence": "HIGH",
        }
        c = build(d)
        assert c is not None
        assert c.score == 0.95

    def test_metadata_preserved(self):
        build = self._import()
        d = {
            "ticker": "NVDA",
            "decision": "STRONG_BUY",
            "confidence": "high",
            "raised_count_48h": 3,
            "lowered_count_48h": 0,
            "raised_count_24h": 2,
            "lowered_count_24h": 0,
            "avg_revision_pct": 25.5,
            "biggest_raise": {"firm": "JPM", "from": 100, "to": 150},
            "biggest_cut": None,
            "drift_status": "post_earnings_drift_active",
            "days_since_earnings": 3,
            "gap_quality": "HIGH",
            "upside_avg_pct": 30.2,
            "risk_reward": 4.5,
            "rationale": "3 bank raised, post-earnings drift active",
        }
        c = build(d)
        assert c is not None
        assert c.metadata["decision"] == "STRONG_BUY"
        assert c.metadata["confidence"] == "high"
        assert c.metadata["raised_count_48h"] == 3
        assert c.metadata["raised_count_24h"] == 2
        assert c.metadata["avg_revision_pct"] == 25.5
        assert c.metadata["biggest_raise"] == {"firm": "JPM", "from": 100, "to": 150}
        assert c.metadata["drift_status"] == "post_earnings_drift_active"
        assert c.metadata["gap_quality"] == "HIGH"
        assert c.metadata["upside_avg_pct"] == 30.2
        # Rationale reason'a girdi
        assert "3 bank raised" in c.reason


# ── Scanner sınıfı ─────────────────────────────────────────────────────────────


class TestScannerClass:
    def test_default_init(self):
        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        s = AnalystRevisionsScanner()
        assert s.name == "analyst_revisions"
        assert s.signal_window_hours == 48
        assert s.universe is None
        assert s.require_post_earnings is True

    def test_custom_init(self):
        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        s = AnalystRevisionsScanner(
            signal_window_hours=24,
            universe=["AAPL", "NVDA"],
            require_post_earnings=False,
        )
        assert s.signal_window_hours == 24
        assert s.universe == ["AAPL", "NVDA"]
        assert s.require_post_earnings is False

    def test_invalid_window_rejected(self):
        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        with pytest.raises(ValueError, match="signal_window_hours"):
            AnalystRevisionsScanner(signal_window_hours=0)
        with pytest.raises(ValueError, match="signal_window_hours"):
            AnalystRevisionsScanner(signal_window_hours=-12)

    def test_resolve_custom_universe(self):
        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        u = ["AAPL", "NVDA", "TSM"]
        s = AnalystRevisionsScanner(universe=u)
        assert s._resolve_universe() == u

    def test_empty_universe_scan_returns_empty(self):
        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        s = AnalystRevisionsScanner(universe=[])
        assert s.scan() == []


# ── Scan() end-to-end mock ─────────────────────────────────────────────────────


class TestScanEndToEnd:
    """Scanner.scan() içinde legacy fonksiyonları mock'la."""

    def test_scan_with_mocked_legacy(self, monkeypatch):
        """fetch_all_signals + analyze_signals mock → Candidate üretimi."""
        # Mock'ları legacy modüllerine kur
        import sys

        # Mock module objects
        class _FakeFetcher:
            @staticmethod
            def fetch_all_signals(ticker, since):
                if ticker == "NVDA":
                    return [{"id": "x", "fake": "signal"}]
                if ticker == "DOWN":
                    return [{"id": "y", "fake": "signal"}]
                return []

            @staticmethod
            def get_last_actual_earnings_date(ticker):
                return None

            @staticmethod
            def get_target_consensus(ticker):
                return None

            @staticmethod
            def _fmp_get(endpoint, **params):
                return [{"price": 100.0}]

        class _FakeAnalyzer:
            @staticmethod
            def analyze_signals(ticker, signals, **kwargs):
                if ticker == "NVDA":
                    return {
                        "ticker": "NVDA",
                        "decision": "STRONG_BUY",
                        "confidence": "high",
                        "raised_count_48h": 3,
                        "lowered_count_48h": 0,
                        "avg_revision_pct": 25.0,
                        "rationale": "3 banka yükseltti",
                    }
                if ticker == "DOWN":
                    return {
                        "ticker": "DOWN",
                        "decision": "SELL",
                        "confidence": "high",
                        "raised_count_48h": 0,
                        "lowered_count_48h": 4,
                    }
                return {"ticker": ticker, "decision": "NEUTRAL", "confidence": "low"}

        monkeypatch.setitem(sys.modules, "agent.legacy.analist_takip.revision_fetcher", _FakeFetcher)
        monkeypatch.setitem(sys.modules, "agent.legacy.analist_takip.signal_analyzer", _FakeAnalyzer)

        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        s = AnalystRevisionsScanner(universe=["NVDA", "DOWN", "NEUTRAL_X"])
        candidates = s.scan()

        # Sadece NVDA Candidate üretir (STRONG_BUY); DOWN filtrelenir (SELL),
        # NEUTRAL_X filtrelenir (NEUTRAL)
        assert len(candidates) == 1
        assert candidates[0].symbol == "NVDA"
        assert candidates[0].score == 0.95

    def test_scan_ticker_error_continues(self, monkeypatch):
        """Bir ticker'da hata → diğer ticker'lar etkilenmemeli."""
        import sys

        class _FakeFetcher:
            @staticmethod
            def fetch_all_signals(ticker, since):
                if ticker == "BROKEN":
                    raise RuntimeError("API down")
                return [{"id": "x", "fake": "signal"}]

            @staticmethod
            def get_last_actual_earnings_date(ticker):
                return None

            @staticmethod
            def get_target_consensus(ticker):
                return None

            @staticmethod
            def _fmp_get(endpoint, **params):
                return [{"price": 100.0}]

        class _FakeAnalyzer:
            @staticmethod
            def analyze_signals(ticker, signals, **kwargs):
                return {
                    "ticker": ticker,
                    "decision": "BUY",
                    "confidence": "medium",
                    "raised_count_48h": 2,
                    "lowered_count_48h": 0,
                }

        monkeypatch.setitem(sys.modules, "agent.legacy.analist_takip.revision_fetcher", _FakeFetcher)
        monkeypatch.setitem(sys.modules, "agent.legacy.analist_takip.signal_analyzer", _FakeAnalyzer)

        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        s = AnalystRevisionsScanner(universe=["BROKEN", "OK1", "OK2"])
        candidates = s.scan()

        # OK1 ve OK2 BUY üretir, BROKEN skip edilir
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["OK1", "OK2"]

    def test_scan_legacy_import_failure_returns_empty(self, monkeypatch):
        """Legacy import çökerse scan() boş döner, exception fırlatmaz."""
        import sys

        # legacy modüllerini sil ki ImportError gelsin
        for mod_name in [
            "agent.legacy.analist_takip.revision_fetcher",
            "agent.legacy.analist_takip.signal_analyzer",
        ]:
            sys.modules.pop(mod_name, None)

        # Sahte ImportError üreten import path
        class _ImportBlocker:
            def find_module(self, name, path=None):
                if "analist_takip" in name and (
                    "revision_fetcher" in name or "signal_analyzer" in name
                ):
                    return self
                return None

            def load_module(self, name):
                raise ImportError(f"blocked: {name}")

        sys.meta_path.insert(0, _ImportBlocker())
        try:
            from agent.scanners.analyst_revisions import AnalystRevisionsScanner
            s = AnalystRevisionsScanner(universe=["AAPL"])
            result = s.scan()
            assert result == []
        finally:
            sys.meta_path.pop(0)


# ── Health check ───────────────────────────────────────────────────────────────


class TestHealthCheck:
    def test_no_fmp_key(self, monkeypatch):
        monkeypatch.delenv("FMP_API_KEY", raising=False)
        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        s = AnalystRevisionsScanner()
        h = s.health_check()
        assert h["ok"] is False
        assert h["name"] == "analyst_revisions"

    def test_with_fmp_key(self, monkeypatch):
        monkeypatch.setenv("FMP_API_KEY", "test")
        from agent.scanners.analyst_revisions import AnalystRevisionsScanner
        s = AnalystRevisionsScanner(universe=["A", "B"], signal_window_hours=24)
        h = s.health_check()
        assert h["ok"] is True
        assert h["universe_size"] == 2
        assert h["signal_window_hours"] == 24
        assert h["require_post_earnings"] is True
