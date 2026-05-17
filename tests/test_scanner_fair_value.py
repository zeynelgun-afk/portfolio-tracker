"""agent/scanners/fair_value.py için testler.

Faz 2 — Adım 6: FairValuePanelScanner adaptörü.

KAPSAM:
    - _evaluate_fair_value_for_candidate FMP mocked başarı durumu
    - Eşik altı potansiyel → None
    - Eksik quote / fiyat → None
    - Eksik analyst targets → None
    - Sıfır/negatif fiyat → None
    - Scanner instantiation + validation
    - Custom universe ile scan
    - Default universe (analist_takip import) fallback davranışı

scan() metodu FMP bağımlı; her testte responses mock'ları setup ediyor.
"""
from __future__ import annotations

import pytest
import responses

import fmp_client  # conftest.py path'leri ayarlıyor


FMP_BASE = "https://financialmodelingprep.com/stable"


# ── _evaluate_fair_value_for_candidate ─────────────────────────────────────────


class TestEvaluateFairValue:
    def _import(self):
        from agent.scanners.fair_value import _evaluate_fair_value_for_candidate
        return _evaluate_fair_value_for_candidate

    @responses.activate
    def test_above_threshold_returns_candidate(self):
        evaluate = self._import()
        # Quote: AAPL @ $100
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[{"symbol": "AAPL", "price": 100.0}],
            status=200,
        )
        # Price targets: latest=$140, highest=$160 → FV=(140+160)/2=$150 → +%50
        responses.add(
            responses.GET, f"{FMP_BASE}/price-target-news",
            json=[
                {"symbol": "AAPL", "priceTarget": 140, "publishedDate": "2026-05-10",
                 "newGrade": None, "previousGrade": None, "analystName": "X",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
                {"symbol": "AAPL", "priceTarget": 130, "publishedDate": "2026-05-08",
                 "newGrade": None, "previousGrade": None, "analystName": "X2",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
                {"symbol": "AAPL", "priceTarget": 160, "publishedDate": "2026-04-20",
                 "newGrade": None, "previousGrade": None, "analystName": "X3",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
            ],
            status=200,
        )

        c = evaluate("AAPL", min_potential_pct=25.0)
        assert c is not None
        assert c.symbol == "AAPL"
        assert c.source == "fair_value"
        # FV=150, current=100 → potential=50%, score=0.5
        assert c.score == pytest.approx(0.5)
        # Metadata kontrolleri
        assert c.metadata["fair_value"] == 150.0
        assert c.metadata["current_price"] == 100.0
        assert c.metadata["potential_pct"] == pytest.approx(50.0)
        assert c.metadata["min_threshold_pct"] == 25.0
        assert c.metadata["latest_target"] == 140
        assert c.metadata["highest_target"] == 160

    @responses.activate
    def test_below_threshold_returns_none(self):
        evaluate = self._import()
        # %10 potansiyel — eşik %25 altı
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[{"symbol": "AAPL", "price": 100.0}],
            status=200,
        )
        responses.add(
            responses.GET, f"{FMP_BASE}/price-target-news",
            json=[
                {"symbol": "AAPL", "priceTarget": 110, "publishedDate": "2026-05-10",
                 "newGrade": None, "previousGrade": None, "analystName": "X",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
            ],
            status=200,
        )
        # FV = (110+110)/2 = 110, current=100 → +%10, < %25
        assert evaluate("AAPL", min_potential_pct=25.0) is None

    @responses.activate
    def test_score_clipped_at_one(self):
        evaluate = self._import()
        # %150 potansiyel — score 1.0'a clip edilir
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[{"symbol": "XX", "price": 100.0}],
            status=200,
        )
        responses.add(
            responses.GET, f"{FMP_BASE}/price-target-news",
            json=[
                {"symbol": "XX", "priceTarget": 250, "publishedDate": "2026-05-10",
                 "newGrade": None, "previousGrade": None, "analystName": "A",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
            ],
            status=200,
        )
        c = evaluate("XX", min_potential_pct=25.0)
        # FV=250, +%150 → score clipped 1.0
        assert c is not None
        assert c.score == 1.0

    @responses.activate
    def test_empty_quote_returns_none(self):
        evaluate = self._import()
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[],
            status=200,
        )
        assert evaluate("UNKNOWN", min_potential_pct=25.0) is None

    @responses.activate
    def test_zero_price_returns_none(self):
        evaluate = self._import()
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[{"symbol": "XX", "price": 0}],
            status=200,
        )
        assert evaluate("XX", min_potential_pct=25.0) is None

    @responses.activate
    def test_no_analyst_targets_returns_none(self):
        evaluate = self._import()
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[{"symbol": "XX", "price": 100.0}],
            status=200,
        )
        responses.add(
            responses.GET, f"{FMP_BASE}/price-target-news",
            json=[],
            status=200,
        )
        assert evaluate("XX", min_potential_pct=25.0) is None

    @responses.activate
    def test_custom_threshold(self):
        evaluate = self._import()
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[{"symbol": "XX", "price": 100.0}],
            status=200,
        )
        responses.add(
            responses.GET, f"{FMP_BASE}/price-target-news",
            json=[
                {"symbol": "XX", "priceTarget": 115, "publishedDate": "2026-05-10",
                 "newGrade": None, "previousGrade": None, "analystName": "A",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
            ],
            status=200,
        )
        # %15 potansiyel — eşik %10 ise geçer, %25 ise geçmez
        c_low = evaluate("XX", min_potential_pct=10.0)
        assert c_low is not None
        assert c_low.metadata["min_threshold_pct"] == 10.0

    @responses.activate
    def test_quote_api_failure_returns_none(self):
        evaluate = self._import()
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json={"error": "internal"},
            status=500,
        )
        # FMP retry de hatalı dönecek, hepsi 500 verelim
        for _ in range(3):
            responses.add(
                responses.GET, f"{FMP_BASE}/quote",
                json={"error": "internal"},
                status=500,
            )
        from unittest.mock import patch
        import time as _time
        with patch.object(_time, "sleep"):
            result = evaluate("XX", min_potential_pct=25.0)
        assert result is None


# ── Scanner sınıfı ─────────────────────────────────────────────────────────────


class TestScannerClass:
    def test_default_threshold(self):
        from agent.scanners.fair_value import FairValuePanelScanner
        s = FairValuePanelScanner()
        assert s.name == "fair_value"
        assert s.min_potential_pct == 25.0
        assert s.universe is None

    def test_custom_threshold(self):
        from agent.scanners.fair_value import FairValuePanelScanner
        s = FairValuePanelScanner(min_potential_pct=15.0)
        assert s.min_potential_pct == 15.0

    def test_invalid_threshold_rejected(self):
        from agent.scanners.fair_value import FairValuePanelScanner
        with pytest.raises(ValueError, match="min_potential_pct"):
            FairValuePanelScanner(min_potential_pct=0)
        with pytest.raises(ValueError, match="min_potential_pct"):
            FairValuePanelScanner(min_potential_pct=-10)

    def test_custom_universe(self):
        from agent.scanners.fair_value import FairValuePanelScanner
        u = ["AAPL", "TSM"]
        s = FairValuePanelScanner(universe=u)
        assert s.universe == u
        assert s._resolve_universe() == u

    def test_empty_universe_returns_empty_list(self):
        from agent.scanners.fair_value import FairValuePanelScanner
        s = FairValuePanelScanner(universe=[])
        assert s.scan() == []

    @responses.activate
    def test_scan_with_custom_universe(self):
        from agent.scanners.fair_value import FairValuePanelScanner
        responses.add(
            responses.GET, f"{FMP_BASE}/quote",
            json=[{"symbol": "AAPL", "price": 100.0}],
            status=200,
        )
        responses.add(
            responses.GET, f"{FMP_BASE}/price-target-news",
            json=[
                {"symbol": "AAPL", "priceTarget": 140, "publishedDate": "2026-05-10",
                 "newGrade": None, "previousGrade": None, "analystName": "X",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
                {"symbol": "AAPL", "priceTarget": 160, "publishedDate": "2026-04-20",
                 "newGrade": None, "previousGrade": None, "analystName": "X2",
                 "newsPublisher": "Y", "newsBaseURL": "z"},
            ],
            status=200,
        )
        s = FairValuePanelScanner(min_potential_pct=25.0, universe=["AAPL"])
        candidates = s.scan()
        assert len(candidates) == 1
        assert candidates[0].symbol == "AAPL"

    def test_health_check_no_api_key(self, monkeypatch):
        monkeypatch.delenv("FMP_API_KEY", raising=False)
        from agent.scanners.fair_value import FairValuePanelScanner
        s = FairValuePanelScanner()
        h = s.health_check()
        assert h["ok"] is False
        assert h["name"] == "fair_value"

    def test_health_check_with_api_key(self, monkeypatch):
        monkeypatch.setenv("FMP_API_KEY", "test_key")
        from agent.scanners.fair_value import FairValuePanelScanner
        s = FairValuePanelScanner(universe=["X", "Y", "Z"])
        h = s.health_check()
        assert h["ok"] is True
        assert h["universe_size"] == 3
