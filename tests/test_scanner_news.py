"""agent/scanners/news.py için testler.

Faz 2 — Adım 7: NewsRadarScanner adaptörü.

KAPSAM:
    - _build_candidates_from_news_results pure transform
    - Yön filtresi (sadece bullish Candidate üretir)
    - Aciliyet × sure score tablosu
    - Çoklu ticker per news result
    - Bozuk input handling (None, list of non-dict, missing fields)
    - Ticker normalize (strip + uppercase)
    - Boş tickers → Candidate yok
    - NewsRadarScanner instantiation + validation
    - Scanner.scan() mocked fetch + analyze
    - health_check

GitHub API yan etkisi (gh_put_file) ve Telegram send CLI tarafında —
scanner test kapsamında değil.
"""
from __future__ import annotations

import pytest


# ── _build_candidates pure transform ───────────────────────────────────────────


class TestBuildCandidates:
    def _import(self):
        from agent.scanners.news import _build_candidates_from_news_results
        return _build_candidates_from_news_results

    def test_basic_bullish_result(self):
        build = self._import()
        results = [{
            "baslik": "AI chip rally",
            "neden_onemli": "HBM tedariki sıkışıyor",
            "yon": "bullish",
            "aciliyet": "yüksek",
            "sure": "kısa",
            "etkilenen_hisseler": ["NVDA", "AMAT"],
            "kaynak_url": "https://example.com",
        }]
        candidates = build(results)
        assert len(candidates) == 2
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AMAT", "NVDA"]
        # yüksek × kısa = 0.90 (en yüksek)
        assert all(c.score == 0.90 for c in candidates)
        assert all(c.source == "news" for c in candidates)

    def test_bearish_filtered_out(self):
        build = self._import()
        results = [
            {"yon": "bullish", "aciliyet": "orta", "sure": "kısa",
             "etkilenen_hisseler": ["AAA"], "baslik": "A", "neden_onemli": "X"},
            {"yon": "bearish", "aciliyet": "yüksek", "sure": "kısa",
             "etkilenen_hisseler": ["BBB"], "baslik": "B", "neden_onemli": "Y"},
        ]
        candidates = build(results)
        symbols = [c.symbol for c in candidates]
        assert "AAA" in symbols
        assert "BBB" not in symbols

    def test_score_table_all_combinations(self):
        """9 kombinasyon × score tablosu."""
        build = self._import()
        expected = {
            ("yüksek", "kısa"): 0.90,
            ("yüksek", "orta"): 0.85,
            ("yüksek", "uzun"): 0.75,
            ("orta",   "kısa"): 0.70,
            ("orta",   "orta"): 0.65,
            ("orta",   "uzun"): 0.55,
            ("düşük",  "kısa"): 0.45,
            ("düşük",  "orta"): 0.40,
            ("düşük",  "uzun"): 0.30,
        }
        for (acil, sure), expected_score in expected.items():
            results = [{
                "yon": "bullish", "aciliyet": acil, "sure": sure,
                "etkilenen_hisseler": ["X"], "baslik": f"{acil}/{sure}",
                "neden_onemli": "test",
            }]
            candidates = build(results)
            assert len(candidates) == 1
            assert candidates[0].score == expected_score, \
                f"({acil},{sure}) → beklenen {expected_score}, alındı {candidates[0].score}"

    def test_unknown_aciliyet_or_sure_uses_default(self):
        build = self._import()
        results = [{
            "yon": "bullish", "aciliyet": "wat", "sure": "ever",
            "etkilenen_hisseler": ["XXX"], "baslik": "T", "neden_onemli": "x",
        }]
        candidates = build(results)
        # _NEWS_DEFAULT_SCORE = 0.50
        assert candidates[0].score == 0.50

    def test_ticker_normalize(self):
        build = self._import()
        results = [{
            "yon": "bullish", "aciliyet": "orta", "sure": "kısa",
            "etkilenen_hisseler": ["nvda", " tsm ", "AMAT"],
            "baslik": "T", "neden_onemli": "x",
        }]
        candidates = build(results)
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AMAT", "NVDA", "TSM"]

    def test_empty_tickers_skipped(self):
        build = self._import()
        results = [{
            "yon": "bullish", "aciliyet": "orta", "sure": "kısa",
            "etkilenen_hisseler": [],
            "baslik": "T", "neden_onemli": "x",
        }]
        assert build(results) == []

    def test_missing_tickers_field_skipped(self):
        build = self._import()
        results = [{
            "yon": "bullish", "aciliyet": "orta", "sure": "kısa",
            # etkilenen_hisseler eksik
            "baslik": "T", "neden_onemli": "x",
        }]
        assert build(results) == []

    def test_non_string_ticker_skipped(self):
        build = self._import()
        results = [{
            "yon": "bullish", "aciliyet": "orta", "sure": "kısa",
            "etkilenen_hisseler": ["NVDA", 123, None, "", "  ", "AMAT"],
            "baslik": "T", "neden_onemli": "x",
        }]
        candidates = build(results)
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AMAT", "NVDA"]

    def test_yon_case_insensitive(self):
        build = self._import()
        results = [
            {"yon": "BULLISH", "aciliyet": "orta", "sure": "kısa",
             "etkilenen_hisseler": ["AAA"], "baslik": "A", "neden_onemli": "x"},
            {"yon": " Bullish ", "aciliyet": "orta", "sure": "kısa",
             "etkilenen_hisseler": ["BBB"], "baslik": "B", "neden_onemli": "x"},
        ]
        candidates = build(results)
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AAA", "BBB"]

    def test_metadata_preserved(self):
        build = self._import()
        results = [{
            "baslik": "NVDA breakthrough",
            "neden_onemli": "Big news",
            "yon": "bullish",
            "aciliyet": "yüksek",
            "sure": "kısa",
            "etkilenen_hisseler": ["NVDA"],
            "kaynak_url": "https://news.example.com/1",
        }]
        c = build(results)[0]
        assert c.metadata["baslik"] == "NVDA breakthrough"
        assert c.metadata["yon"] == "bullish"
        assert c.metadata["aciliyet"] == "yüksek"
        assert c.metadata["sure"] == "kısa"
        assert c.metadata["kaynak_url"] == "https://news.example.com/1"
        assert c.metadata["neden_onemli"] == "Big news"

    def test_empty_input(self):
        build = self._import()
        assert build([]) == []
        assert build(None) == []  # type: ignore[arg-type]
        assert build("not-a-list") == []  # type: ignore[arg-type]

    def test_non_dict_item_skipped(self):
        build = self._import()
        results = [
            "not a dict",
            None,
            {"yon": "bullish", "aciliyet": "orta", "sure": "kısa",
             "etkilenen_hisseler": ["AAA"], "baslik": "A", "neden_onemli": "x"},
        ]
        candidates = build(results)
        assert len(candidates) == 1
        assert candidates[0].symbol == "AAA"

    def test_multiple_results_aggregated(self):
        build = self._import()
        results = [
            {"yon": "bullish", "aciliyet": "yüksek", "sure": "kısa",
             "etkilenen_hisseler": ["AAA"], "baslik": "A", "neden_onemli": "x"},
            {"yon": "bullish", "aciliyet": "orta", "sure": "orta",
             "etkilenen_hisseler": ["BBB", "CCC"], "baslik": "B", "neden_onemli": "y"},
        ]
        candidates = build(results)
        assert len(candidates) == 3
        scores = {c.symbol: c.score for c in candidates}
        assert scores["AAA"] == 0.90
        assert scores["BBB"] == 0.65
        assert scores["CCC"] == 0.65


# ── Scanner sınıfı ─────────────────────────────────────────────────────────────


class TestScannerClass:
    def test_default_lookback(self):
        from agent.scanners.news import NewsRadarScanner, NEWS_LOOKBACK_HOURS
        s = NewsRadarScanner()
        assert s.name == "news"
        assert s.lookback_hours == NEWS_LOOKBACK_HOURS

    def test_custom_lookback(self):
        from agent.scanners.news import NewsRadarScanner
        s = NewsRadarScanner(lookback_hours=8)
        assert s.lookback_hours == 8

    def test_invalid_lookback_rejected(self):
        from agent.scanners.news import NewsRadarScanner
        with pytest.raises(ValueError, match="lookback_hours"):
            NewsRadarScanner(lookback_hours=0)
        with pytest.raises(ValueError, match="lookback_hours"):
            NewsRadarScanner(lookback_hours=-5)

    def test_scan_with_empty_news(self, monkeypatch):
        """fetch_recent_news boş dönerse scan boş Candidate listesi."""
        from agent.scanners import news as news_module
        monkeypatch.setattr(news_module, "fetch_recent_news", lambda **kw: [])
        s = news_module.NewsRadarScanner()
        assert s.scan() == []

    def test_scan_with_mocked_llm(self, monkeypatch):
        """fetch + analyze mock'lanır, Candidate üretimi end-to-end."""
        from agent.scanners import news as news_module
        mock_news = [{"title": "x", "source": "y", "pub": "z", "text": "t", "url": "u"}]
        mock_results = [{
            "yon": "bullish", "aciliyet": "yüksek", "sure": "kısa",
            "etkilenen_hisseler": ["NVDA"], "baslik": "B", "neden_onemli": "X",
            "kaynak_url": "https://x.com",
        }]
        monkeypatch.setattr(news_module, "fetch_recent_news", lambda **kw: mock_news)
        monkeypatch.setattr(news_module, "analyze_with_claude", lambda items: mock_results)

        s = news_module.NewsRadarScanner()
        candidates = s.scan()
        assert len(candidates) == 1
        assert candidates[0].symbol == "NVDA"
        assert candidates[0].score == 0.90

    def test_scan_fetch_exception(self, monkeypatch):
        """fetch_recent_news exception fırlattığında graceful degradation."""
        from agent.scanners import news as news_module

        def _boom(**kw):
            raise RuntimeError("API down")

        monkeypatch.setattr(news_module, "fetch_recent_news", _boom)
        s = news_module.NewsRadarScanner()
        assert s.scan() == []

    def test_scan_llm_exception(self, monkeypatch):
        """analyze_with_claude exception → scan() boş döner, çökmez."""
        from agent.scanners import news as news_module
        mock_news = [{"title": "x", "source": "y", "pub": "z", "text": "t", "url": "u"}]
        monkeypatch.setattr(news_module, "fetch_recent_news", lambda **kw: mock_news)

        def _boom(items):
            raise RuntimeError("LLM down")

        monkeypatch.setattr(news_module, "analyze_with_claude", _boom)
        s = news_module.NewsRadarScanner()
        assert s.scan() == []

    def test_health_check_no_fmp(self, monkeypatch):
        from agent.scanners import news as news_module
        monkeypatch.setattr(news_module, "FMP_KEY", "")
        s = news_module.NewsRadarScanner()
        h = s.health_check()
        assert h["ok"] is False
        assert h["name"] == "news"

    def test_health_check_with_fmp(self, monkeypatch):
        from agent.scanners import news as news_module
        monkeypatch.setattr(news_module, "FMP_KEY", "test_key")
        s = news_module.NewsRadarScanner(lookback_hours=12)
        h = s.health_check()
        assert h["ok"] is True
        assert h["lookback_hours"] == 12
