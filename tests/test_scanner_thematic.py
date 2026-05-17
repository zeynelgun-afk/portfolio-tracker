"""agent/scanners/thematic.py için testler.

Faz 2 — Adım 5: ThematicDiscoveryScanner adaptörü.

KAPSAM:
    - _build_candidates_from_llm_payload pure transform (yan etki yok)
    - Yaşam evresi filtresi (sönüş → Candidate yok)
    - ETF filtresi (related_tickers içinden ETF çıkarma)
    - Momentum score normalize (0-100 → 0.0-1.0)
    - Bozuk payload handling (eksik alanlar, type hataları)
    - ThematicDiscoveryScanner instantiation + mode validation
    - health_check
    - Boş/null payload → boş Candidate listesi

scan() metodu network bağımlı (LLM API + FMP), entegrasyon testi smoke
test ile yapılıyor (yukarıdaki commit'te elle doğrulandı).
"""
from __future__ import annotations

import pytest


# ── _build_candidates pure transform ───────────────────────────────────────────


class TestBuildCandidates:
    def _import(self):
        # Test runtime'da import — modül yüklenirken yan etki olmasın
        from agent.scanners.thematic import _build_candidates_from_llm_payload
        return _build_candidates_from_llm_payload

    def test_basic_growing_theme(self):
        build = self._import()
        payload = {
            "themes": [{
                "id": "ai_supply",
                "name": "AI Supply Chain",
                "lifecycle_stage": "yukselis",
                "momentum_score": 80,
                "related_tickers": ["NVDA", "AMAT"],
            }]
        }
        candidates = build(payload, mode="daily")
        assert len(candidates) == 2
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AMAT", "NVDA"]
        # 80 / 100 = 0.80
        assert all(c.score == pytest.approx(0.8) for c in candidates)
        assert all(c.source == "thematic" for c in candidates)

    def test_dying_theme_filtered_out(self):
        build = self._import()
        payload = {
            "themes": [
                {
                    "id": "rising",
                    "name": "Rising",
                    "lifecycle_stage": "yukselis",
                    "momentum_score": 70,
                    "related_tickers": ["AAA"],
                },
                {
                    "id": "dying",
                    "name": "Dying",
                    "lifecycle_stage": "sönüs",
                    "momentum_score": 20,
                    "related_tickers": ["BBB", "CCC"],
                },
            ]
        }
        candidates = build(payload, mode="daily")
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AAA"]
        assert "BBB" not in symbols
        assert "CCC" not in symbols

    def test_etf_filtered_from_tickers(self):
        build = self._import()
        # SECTOR_ETFS + diğer yaygın ETF'ler filtrelenir
        payload = {
            "themes": [{
                "id": "mixed",
                "name": "Mixed",
                "lifecycle_stage": "olgun",
                "momentum_score": 60,
                "related_tickers": ["NVDA", "XLK", "SPY", "QQQ", "TSM", "VNQ"],
            }]
        }
        candidates = build(payload, mode="daily")
        symbols = sorted(c.symbol for c in candidates)
        # XLK, SPY, QQQ, VNQ ETF — sadece NVDA + TSM kalır
        assert symbols == ["NVDA", "TSM"]

    def test_momentum_normalize_clipping(self):
        build = self._import()
        payload = {
            "themes": [
                {"id": "a", "name": "A", "lifecycle_stage": "yukselis",
                 "momentum_score": 150, "related_tickers": ["AAA"]},
                {"id": "b", "name": "B", "lifecycle_stage": "yukselis",
                 "momentum_score": -20, "related_tickers": ["BBB"]},
            ]
        }
        candidates = build(payload, mode="daily")
        scores = {c.symbol: c.score for c in candidates}
        # 150 → 1.0 (max), -20 → 0.0 (min)
        assert scores["AAA"] == 1.0
        assert scores["BBB"] == 0.0

    def test_invalid_momentum_falls_back(self):
        build = self._import()
        payload = {
            "themes": [{
                "id": "bad",
                "name": "Bad",
                "lifecycle_stage": "yukselis",
                "momentum_score": "not-a-number",
                "related_tickers": ["AAA"],
            }]
        }
        candidates = build(payload, mode="daily")
        # Fallback 0.5
        assert candidates[0].score == 0.5

    def test_lowercase_ticker_normalized(self):
        build = self._import()
        payload = {
            "themes": [{
                "id": "x",
                "name": "X",
                "lifecycle_stage": "yukselis",
                "momentum_score": 50,
                "related_tickers": ["nvda", " tsm "],
            }]
        }
        candidates = build(payload, mode="daily")
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["NVDA", "TSM"]

    def test_empty_payload(self):
        build = self._import()
        assert build({}, mode="daily") == []
        assert build({"themes": []}, mode="daily") == []
        assert build(None, mode="daily") == []  # type: ignore[arg-type]

    def test_non_dict_payload(self):
        build = self._import()
        assert build("not-a-dict", mode="daily") == []  # type: ignore[arg-type]
        assert build([1, 2, 3], mode="daily") == []  # type: ignore[arg-type]

    def test_missing_related_tickers(self):
        build = self._import()
        payload = {
            "themes": [{
                "id": "no_tickers",
                "name": "Theme without tickers",
                "lifecycle_stage": "yukselis",
                "momentum_score": 70,
                # related_tickers eksik
            }]
        }
        assert build(payload, mode="daily") == []

    def test_non_string_ticker_skipped(self):
        build = self._import()
        payload = {
            "themes": [{
                "id": "weird",
                "name": "W",
                "lifecycle_stage": "yukselis",
                "momentum_score": 50,
                "related_tickers": ["NVDA", 123, None, "", "  ", "AMAT"],
            }]
        }
        candidates = build(payload, mode="daily")
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AMAT", "NVDA"]

    def test_metadata_preserved(self):
        build = self._import()
        payload = {
            "themes": [{
                "id": "ai_supply",
                "name": "AI Supply Chain",
                "lifecycle_stage": "olgun",
                "momentum_score": 75,
                "related_tickers": ["NVDA"],
            }]
        }
        candidates = build(payload, mode="weekly")
        c = candidates[0]
        assert c.metadata["theme_id"] == "ai_supply"
        assert c.metadata["theme_name"] == "AI Supply Chain"
        assert c.metadata["lifecycle_stage"] == "olgun"
        assert c.metadata["momentum_score"] == 75
        assert c.metadata["mode"] == "weekly"

    def test_all_three_growing_stages(self):
        """dogus / yukselis / olgun → hepsi Candidate üretir."""
        build = self._import()
        payload = {
            "themes": [
                {"id": "a", "name": "A", "lifecycle_stage": "dogus",
                 "momentum_score": 50, "related_tickers": ["AAA"]},
                {"id": "b", "name": "B", "lifecycle_stage": "yukselis",
                 "momentum_score": 50, "related_tickers": ["BBB"]},
                {"id": "c", "name": "C", "lifecycle_stage": "olgun",
                 "momentum_score": 50, "related_tickers": ["CCC"]},
            ]
        }
        candidates = build(payload, mode="daily")
        symbols = sorted(c.symbol for c in candidates)
        assert symbols == ["AAA", "BBB", "CCC"]


# ── ThematicDiscoveryScanner sınıfı ────────────────────────────────────────────


class TestScannerClass:
    def test_default_mode(self):
        from agent.scanners.thematic import ThematicDiscoveryScanner
        s = ThematicDiscoveryScanner()
        assert s.name == "thematic"
        assert s.mode == "daily"

    def test_weekly_mode(self):
        from agent.scanners.thematic import ThematicDiscoveryScanner
        s = ThematicDiscoveryScanner(mode="weekly")
        assert s.mode == "weekly"

    def test_invalid_mode_rejected(self):
        from agent.scanners.thematic import ThematicDiscoveryScanner
        with pytest.raises(ValueError, match="mode"):
            ThematicDiscoveryScanner(mode="monthly")

    def test_health_check_no_api_key(self, monkeypatch):
        # OPENROUTER_API_KEY yokken health_check ok=False döner
        from agent.scanners import thematic
        monkeypatch.setattr(thematic, "OPENROUTER_API_KEY", "")
        s = thematic.ThematicDiscoveryScanner()
        h = s.health_check()
        assert h["ok"] is False
        assert h["name"] == "thematic"

    def test_health_check_with_api_key(self, monkeypatch):
        from agent.scanners import thematic
        monkeypatch.setattr(thematic, "OPENROUTER_API_KEY", "test_key")
        s = thematic.ThematicDiscoveryScanner()
        h = s.health_check()
        assert h["ok"] is True

    def test_scan_without_api_key_raises(self, monkeypatch):
        from agent.scanners import thematic
        monkeypatch.setattr(thematic, "OPENROUTER_API_KEY", "")
        s = thematic.ThematicDiscoveryScanner()
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            s.scan()
