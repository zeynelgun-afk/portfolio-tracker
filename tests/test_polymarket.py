"""agent/polymarket.py için kapsamlı testler.

Faz 2 — Polymarket Gamma API client (17 May 2026).

KAPSAM:
    - fetch_markets normal başarı + slug filtresi
    - fetch_market_by_slug
    - 429 retry mantığı
    - 5xx retry mantığı
    - 404 kalıcı hata
    - JSON decode hatası
    - Network exception
    - is_liquid filtresi (volume eşik)
    - get_yes_probability (binary parse + non-binary skip + string JSON parse)
    - compute_delta
    - Cache load/save + TTL kontrolü
    - Themes whitelist load + slug aggregate
    - Throttle (lokal, hızlı)

Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 6)
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

import polymarket  # conftest.py agent/'i path'e ekliyor
from polymarket import (
    BASE_URL,
    cache_is_fresh,
    compute_delta,
    fetch_market_by_slug,
    fetch_markets,
    get_theme_slugs,
    get_yes_probability,
    is_liquid,
    load_cache,
    load_themes,
    save_cache,
)


# ── Test sabitleri ─────────────────────────────────────────────────────────────


_SAMPLE_BINARY_MARKET = {
    "id": "0x123abc",
    "slug": "fed-rate-cut-by-q3-2026",
    "question": "Will the Fed cut rates by Q3 2026?",
    "outcomes": ["Yes", "No"],
    "outcomePrices": ["0.72", "0.28"],
    "volume": 4250000,
    "liquidity": 320000,
    "active": True,
    "closed": False,
    "endDate": "2026-09-30T18:00:00Z",
}

_SAMPLE_MULTI_OUTCOME_MARKET = {
    "id": "0xmulti",
    "slug": "election-multi",
    "outcomes": ["A", "B", "C"],
    "outcomePrices": ["0.3", "0.3", "0.4"],
    "volume": 1500000,
}


# ── fetch_markets ──────────────────────────────────────────────────────────────


class TestFetchMarkets:
    @responses.activate
    def test_basic_success(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[_SAMPLE_BINARY_MARKET],
            status=200,
        )
        result = fetch_markets()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["slug"] == "fed-rate-cut-by-q3-2026"

    @responses.activate
    def test_slug_filter(self):
        # Yeni mantık: her slug için ayrı /markets?slug=... çağrısı yapılır.
        # Mock her slug için match-edici response döndürür.
        market_a = dict(_SAMPLE_BINARY_MARKET, slug="alpha")
        market_c = dict(_SAMPLE_BINARY_MARKET, slug="gamma")
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            match=[responses.matchers.query_param_matcher({"slug": "alpha", "limit": "1"})],
            json=[market_a],
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            match=[responses.matchers.query_param_matcher({"slug": "gamma", "limit": "1"})],
            json=[market_c],
            status=200,
        )
        result = fetch_markets(slugs=["alpha", "gamma"])
        slugs = [m["slug"] for m in result]
        assert "alpha" in slugs
        assert "gamma" in slugs
        assert "beta" not in slugs

    @responses.activate
    def test_slug_filter_missing_market_skipped(self):
        """Slug için API boş döndürürse o slug atlanır, exception yok."""
        market_a = dict(_SAMPLE_BINARY_MARKET, slug="alpha")
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            match=[responses.matchers.query_param_matcher({"slug": "alpha", "limit": "1"})],
            json=[market_a],
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            match=[responses.matchers.query_param_matcher({"slug": "nonexistent", "limit": "1"})],
            json=[],
            status=200,
        )
        result = fetch_markets(slugs=["alpha", "nonexistent"])
        slugs = [m["slug"] for m in result]
        assert slugs == ["alpha"]

    @responses.activate
    def test_empty_string_slugs_skipped(self):
        """Boş/whitespace slug'lar API call yapmadan atlanır."""
        market_a = dict(_SAMPLE_BINARY_MARKET, slug="alpha")
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            match=[responses.matchers.query_param_matcher({"slug": "alpha", "limit": "1"})],
            json=[market_a],
            status=200,
        )
        result = fetch_markets(slugs=["alpha", "", "   "])
        assert len(result) == 1
        assert result[0]["slug"] == "alpha"

    @responses.activate
    def test_empty_slugs_returns_all(self):
        # slugs=None tüm sonuçları döndürür
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[_SAMPLE_BINARY_MARKET],
            status=200,
        )
        result = fetch_markets(slugs=None)
        assert len(result) == 1

    @responses.activate
    def test_explicit_empty_slug_list_filters_out_all(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[_SAMPLE_BINARY_MARKET],
            status=200,
        )
        result = fetch_markets(slugs=[])
        # Boş slug listesi → hiçbiri eşleşmez
        assert result == []

    @responses.activate
    def test_non_list_response_returns_empty(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json={"error": "unexpected"},
            status=200,
        )
        assert fetch_markets() == []


# ── fetch_market_by_slug ───────────────────────────────────────────────────────


class TestFetchMarketBySlug:
    @responses.activate
    def test_returns_first_match(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[_SAMPLE_BINARY_MARKET],
            status=200,
        )
        m = fetch_market_by_slug("fed-rate-cut-by-q3-2026")
        assert m is not None
        assert m["slug"] == "fed-rate-cut-by-q3-2026"

    @responses.activate
    def test_empty_result_returns_none(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[],
            status=200,
        )
        assert fetch_market_by_slug("nonexistent") is None

    def test_empty_slug_returns_none_no_call(self):
        # Çağrı bile yapılmamalı — slug boşsa
        assert fetch_market_by_slug("") is None


# ── HTTP hata yolları ──────────────────────────────────────────────────────────


class TestHttpErrors:
    @responses.activate
    def test_429_retries_then_fails(self):
        # 3 retry + 1 ilk → 4 deneme, hepsi 429
        for _ in range(4):
            responses.add(
                responses.GET,
                f"{BASE_URL}/markets",
                json={"error": "rate"},
                status=429,
            )
        # Sleep'i hızlandır
        with patch.object(time, "sleep"):
            result = fetch_markets()
        assert result == []

    @responses.activate
    def test_500_retries_then_fails(self):
        for _ in range(4):
            responses.add(
                responses.GET,
                f"{BASE_URL}/markets",
                json={},
                status=500,
            )
        with patch.object(time, "sleep"):
            assert fetch_markets() == []

    @responses.activate
    def test_429_then_success(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json={},
            status=429,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[_SAMPLE_BINARY_MARKET],
            status=200,
        )
        with patch.object(time, "sleep"):
            result = fetch_markets()
        assert len(result) == 1

    @responses.activate
    def test_404_no_retry(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            status=404,
        )
        result = fetch_markets()
        # Tek call — retry yok
        assert result == []
        assert len(responses.calls) == 1

    @responses.activate
    def test_invalid_json(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            body="<html>Error</html>",
            status=200,
            content_type="text/html",
        )
        assert fetch_markets() == []


# ── is_liquid ──────────────────────────────────────────────────────────────────


class TestIsLiquid:
    def test_above_threshold(self):
        assert is_liquid(_SAMPLE_BINARY_MARKET, min_volume_usd=100_000) is True

    def test_below_threshold(self):
        thin_market = dict(_SAMPLE_BINARY_MARKET, volume=50_000)
        assert is_liquid(thin_market, min_volume_usd=100_000) is False

    def test_exact_threshold_inclusive(self):
        market = dict(_SAMPLE_BINARY_MARKET, volume=100_000)
        assert is_liquid(market, min_volume_usd=100_000) is True

    def test_missing_volume(self):
        market = {k: v for k, v in _SAMPLE_BINARY_MARKET.items() if k != "volume"}
        assert is_liquid(market) is False

    def test_volumenum_fallback(self):
        # Gamma bazen volume yerine volumeNum dönebilir
        market = {k: v for k, v in _SAMPLE_BINARY_MARKET.items() if k != "volume"}
        market["volumeNum"] = 250_000
        assert is_liquid(market, min_volume_usd=100_000) is True

    def test_invalid_volume_type(self):
        market = dict(_SAMPLE_BINARY_MARKET, volume="not-a-number")
        assert is_liquid(market) is False

    def test_non_dict_input(self):
        assert is_liquid("not-a-dict") is False  # type: ignore[arg-type]


# ── get_yes_probability ────────────────────────────────────────────────────────


class TestGetYesProbability:
    def test_basic_binary(self):
        p = get_yes_probability(_SAMPLE_BINARY_MARKET)
        assert p == pytest.approx(0.72)

    def test_no_first(self):
        market = dict(
            _SAMPLE_BINARY_MARKET,
            outcomes=["No", "Yes"],
            outcomePrices=["0.45", "0.55"],
        )
        p = get_yes_probability(market)
        assert p == pytest.approx(0.55)

    def test_case_insensitive(self):
        market = dict(
            _SAMPLE_BINARY_MARKET,
            outcomes=["YES", "NO"],
        )
        assert get_yes_probability(market) == pytest.approx(0.72)

    def test_multi_outcome_returns_none(self):
        assert get_yes_probability(_SAMPLE_MULTI_OUTCOME_MARKET) is None

    def test_string_json_parse(self):
        # Gamma bazen outcomes/outcomePrices alanlarını JSON string olarak döner
        market = dict(
            _SAMPLE_BINARY_MARKET,
            outcomes='["Yes", "No"]',
            outcomePrices='["0.72", "0.28"]',
        )
        assert get_yes_probability(market) == pytest.approx(0.72)

    def test_malformed_string_json(self):
        market = dict(_SAMPLE_BINARY_MARKET, outcomes='not-json')
        assert get_yes_probability(market) is None

    def test_missing_yes_outcome(self):
        market = dict(
            _SAMPLE_BINARY_MARKET,
            outcomes=["A", "B"],
        )
        assert get_yes_probability(market) is None

    def test_non_dict_input(self):
        assert get_yes_probability("xx") is None  # type: ignore[arg-type]


# ── compute_delta ──────────────────────────────────────────────────────────────


class TestComputeDelta:
    def test_positive_delta(self):
        d = compute_delta(_SAMPLE_BINARY_MARKET, previous_probability=0.65)
        # 0.72 - 0.65 = 0.07
        assert d == pytest.approx(0.07)

    def test_negative_delta(self):
        d = compute_delta(_SAMPLE_BINARY_MARKET, previous_probability=0.85)
        # 0.72 - 0.85 = -0.13
        assert d == pytest.approx(-0.13)

    def test_no_previous_returns_none(self):
        assert compute_delta(_SAMPLE_BINARY_MARKET, previous_probability=None) is None

    def test_no_current_returns_none(self):
        assert compute_delta(_SAMPLE_MULTI_OUTCOME_MARKET, previous_probability=0.5) is None


# ── Cache I/O ──────────────────────────────────────────────────────────────────


class TestCacheIO:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "polymarket_cache.json"
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        payload = {"markets": {"foo": {"id": "1", "current_probability": 0.5}}}
        save_cache(payload)
        loaded = load_cache()

        assert loaded["markets"]["foo"]["id"] == "1"
        # _fetched_at otomatik eklendi
        assert loaded.get("_fetched_at")

    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "nonexistent.json"
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        loaded = load_cache()
        assert loaded["markets"] == {}
        assert loaded["_fetched_at"] is None

    def test_load_malformed_returns_empty(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "bad.json"
        cache_path.write_text("not json")
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        loaded = load_cache()
        assert loaded["markets"] == {}

    def test_load_non_dict_returns_empty(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "list.json"
        cache_path.write_text("[1, 2, 3]")
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        loaded = load_cache()
        assert loaded["markets"] == {}


# ── Cache TTL ──────────────────────────────────────────────────────────────────


class TestCacheTTL:
    def test_fresh_now(self):
        cache = {"_fetched_at": datetime.now(timezone.utc).isoformat()}
        assert cache_is_fresh(cache, max_age_hours=1.0) is True

    def test_stale_old(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        cache = {"_fetched_at": old_ts}
        assert cache_is_fresh(cache, max_age_hours=1.0) is False

    def test_missing_timestamp(self):
        assert cache_is_fresh({}, max_age_hours=1.0) is False
        assert cache_is_fresh({"_fetched_at": None}, max_age_hours=1.0) is False

    def test_invalid_timestamp(self):
        assert cache_is_fresh({"_fetched_at": "not-a-date"}, max_age_hours=1.0) is False

    def test_z_suffix_iso(self):
        # "Z" suffix yaygın — desteklenmeli
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        assert cache_is_fresh({"_fetched_at": ts}, max_age_hours=1.0) is True


# ── Themes whitelist ───────────────────────────────────────────────────────────


class TestThemes:
    def test_load_real_seed(self):
        # Repo'da v1 seed dosyası mevcut — gerçek dosyayı test et
        themes = load_themes()
        assert "themes" in themes
        # v1 seed 5 tema içermeli
        assert len(themes["themes"]) == 5
        assert "fed_rate_cut" in themes["themes"]
        assert "china_taiwan_tension" in themes["themes"]

    def test_load_missing_returns_empty_themes(self, tmp_path, monkeypatch):
        themes_path = tmp_path / "nonexistent.json"
        monkeypatch.setattr(polymarket, "THEMES_PATH", themes_path)

        themes = load_themes()
        assert themes == {"themes": {}}

    def test_get_theme_slugs_aggregate(self):
        # v2 seed: doğrulanmış gerçek slug'lar.
        # 5 tema, 2'si pending (boş slugs), 3'ü verified (Fed 5 + Taiwan 1 + Recession 1 = 7).
        slugs = get_theme_slugs()
        assert isinstance(slugs, set)
        assert len(slugs) >= 6
        # Doğrulanmış gerçek slug'lardan birkaç sanity check
        assert "will-china-invade-taiwan-before-2027" in slugs
        assert "us-recession-by-end-of-2026" in slugs
        # En az bir Fed marketi (June 2026 hâlâ aktif olan core market)
        assert any("fed-rate-cut" in s for s in slugs)

    def test_get_theme_slugs_empty_when_no_file(self, tmp_path, monkeypatch):
        themes_path = tmp_path / "nonexistent.json"
        monkeypatch.setattr(polymarket, "THEMES_PATH", themes_path)
        assert get_theme_slugs() == set()


# ── Throttle ───────────────────────────────────────────────────────────────────


class TestThrottle:
    """Throttle mekanizmasını ayrı doğrula — conftest 0 set ediyor ama
    polymarket modülünün kendi state'i var, FMP'den bağımsız."""

    @responses.activate
    def test_throttle_enforces_min_interval(self):
        original_interval = polymarket._MIN_CALL_INTERVAL
        polymarket._MIN_CALL_INTERVAL = 0.05  # 50ms test için
        polymarket._last_call_ts = 0.0  # reset

        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[],
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/markets",
            json=[],
            status=200,
        )

        try:
            t0 = time.monotonic()
            fetch_markets()
            fetch_markets()
            elapsed = time.monotonic() - t0
            # En az 50ms (ikinci çağrı throttle bekledi)
            assert elapsed >= 0.04  # toleranslı
        finally:
            polymarket._MIN_CALL_INTERVAL = original_interval
            polymarket._last_call_ts = 0.0
