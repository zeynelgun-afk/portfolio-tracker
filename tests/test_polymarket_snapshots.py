"""agent/polymarket.py snapshot rotation testleri.

Faz 2 — Adım 10a: Cache rotation + 24h delta hesabı.

KAPSAM:
    - add_snapshot: yeni snapshot ekleme, market_data merge
    - Sliding window 48h: eski snapshot'lar temizlenir
    - Snapshot sıralama (out-of-order yazımları normalize)
    - current_probability + delta_24h üst seviyeye yazılır
    - compute_24h_delta_from_snapshots: 24h ± 2h tolerans
    - Yetersiz snapshot durumlarında None
    - refresh_cache_for_themes: Gamma fetch + snapshot ekleme + save
    - Edge case'ler: boş themes, eksik slug, get_yes_probability None
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

import polymarket  # conftest agent/ path'inde


# ── add_snapshot ───────────────────────────────────────────────────────────────


class TestAddSnapshot:
    def _now(self):
        return datetime(2026, 5, 17, 15, 0, 0, tzinfo=timezone.utc)

    def test_first_snapshot(self):
        cache = {"markets": {}}
        now = self._now()
        result = polymarket.add_snapshot(cache, "slug-1", 0.50, now=now)
        entry = result["markets"]["slug-1"]
        assert entry["slug"] == "slug-1"
        assert entry["current_probability"] == 0.50
        assert len(entry["snapshots"]) == 1
        assert entry["snapshots"][0]["probability"] == 0.50
        # Tek snapshot → delta_24h yok
        assert "delta_24h" not in entry

    def test_market_metadata_merged(self):
        cache = {"markets": {}}
        now = self._now()
        polymarket.add_snapshot(
            cache, "slug-1", 0.50,
            market_data={
                "question": "Will X?",
                "volume": 1500000,
                "id": "0xabc",
            },
            now=now,
        )
        entry = cache["markets"]["slug-1"]
        assert entry["question"] == "Will X?"
        assert entry["volume"] == 1500000
        assert entry["id"] == "0xabc"

    def test_metadata_snapshots_field_ignored(self):
        """market_data içindeki 'snapshots' field'ı yok sayılmalı."""
        cache = {"markets": {}}
        now = self._now()
        polymarket.add_snapshot(
            cache, "slug-1", 0.50,
            market_data={"snapshots": [{"fake": "data"}]},
            now=now,
        )
        # Bizim snapshot ekleyici sadece yeni snapshot ekledi
        entry = cache["markets"]["slug-1"]
        assert len(entry["snapshots"]) == 1
        assert "fake" not in entry["snapshots"][0]

    def test_multiple_snapshots_sorted(self):
        cache = {"markets": {}}
        now = self._now()
        # 3 farklı zamanlamada snapshot ekle
        polymarket.add_snapshot(cache, "slug", 0.50, now=now - timedelta(hours=10))
        polymarket.add_snapshot(cache, "slug", 0.55, now=now - timedelta(hours=5))
        polymarket.add_snapshot(cache, "slug", 0.60, now=now)

        entry = cache["markets"]["slug"]
        assert len(entry["snapshots"]) == 3
        # Sıralı (en eski → en yeni)
        probs = [s["probability"] for s in entry["snapshots"]]
        assert probs == [0.50, 0.55, 0.60]
        assert entry["current_probability"] == 0.60

    def test_window_cleanup_48h(self):
        """48h+ eski snapshot'lar temizlenir."""
        cache = {"markets": {}}
        now = self._now()
        # 49h önceki — eski
        polymarket.add_snapshot(cache, "slug", 0.40, now=now - timedelta(hours=49))
        # 47h önceki — sınırın içinde
        polymarket.add_snapshot(cache, "slug", 0.45, now=now - timedelta(hours=47))
        # Şimdi
        polymarket.add_snapshot(cache, "slug", 0.60, now=now)

        snaps = cache["markets"]["slug"]["snapshots"]
        probs = sorted(s["probability"] for s in snaps)
        # 0.40 (49h) temizlendi, 0.45 (47h) ve 0.60 (now) kaldı
        assert 0.40 not in probs
        assert 0.45 in probs
        assert 0.60 in probs

    def test_window_boundary_exactly_48h_inclusive(self):
        """Tam 48h önceki snapshot dahil edilir."""
        cache = {"markets": {}}
        now = self._now()
        polymarket.add_snapshot(cache, "slug", 0.45, now=now - timedelta(hours=48))
        polymarket.add_snapshot(cache, "slug", 0.60, now=now)

        snaps = cache["markets"]["slug"]["snapshots"]
        probs = [s["probability"] for s in snaps]
        assert 0.45 in probs

    def test_delta_computed_after_24h_window(self):
        """24h önceki snapshot varsa delta_24h hesaplanır."""
        cache = {"markets": {}}
        now = self._now()
        polymarket.add_snapshot(cache, "slug", 0.50, now=now - timedelta(hours=24))
        polymarket.add_snapshot(cache, "slug", 0.65, now=now)

        entry = cache["markets"]["slug"]
        assert entry["current_probability"] == 0.65
        assert entry["probability_24h_ago"] == 0.50
        assert entry["delta_24h"] == pytest.approx(0.15)

    def test_non_dict_cache_replaced(self):
        """cache None gelirse yeni empty cache başlat."""
        result = polymarket.add_snapshot(None, "slug", 0.50, now=self._now())  # type: ignore[arg-type]
        assert "markets" in result
        assert "slug" in result["markets"]


# ── compute_24h_delta_from_snapshots ───────────────────────────────────────────


class TestCompute24hDelta:
    def _now(self):
        return datetime(2026, 5, 17, 15, 0, 0, tzinfo=timezone.utc)

    def test_exact_24h_window(self):
        now = self._now()
        snapshots = [
            {"ts": (now - timedelta(hours=24)).isoformat(), "probability": 0.50},
            {"ts": now.isoformat(), "probability": 0.65},
        ]
        result = polymarket.compute_24h_delta_from_snapshots(snapshots, now=now)
        assert result is not None
        assert result["probability_24h_ago"] == 0.50
        assert result["delta_24h"] == pytest.approx(0.15)
        assert result["matched_hours_ago"] == 24.0

    def test_within_tolerance_window(self):
        """22-26h arası snapshot kabul (±2h tolerans)."""
        now = self._now()
        # 22.5h önceki — pencere içinde
        snapshots = [
            {"ts": (now - timedelta(hours=22, minutes=30)).isoformat(), "probability": 0.50},
            {"ts": now.isoformat(), "probability": 0.65},
        ]
        result = polymarket.compute_24h_delta_from_snapshots(snapshots, now=now)
        assert result is not None
        assert result["probability_24h_ago"] == 0.50

    def test_outside_tolerance_returns_none(self):
        """20h önceki snapshot toleransın altında — None."""
        now = self._now()
        snapshots = [
            {"ts": (now - timedelta(hours=20)).isoformat(), "probability": 0.50},
            {"ts": now.isoformat(), "probability": 0.65},
        ]
        result = polymarket.compute_24h_delta_from_snapshots(snapshots, now=now)
        assert result is None

    def test_too_old_returns_none(self):
        """30h+ önceki snapshot toleransın üstünde — None."""
        now = self._now()
        snapshots = [
            {"ts": (now - timedelta(hours=30)).isoformat(), "probability": 0.50},
            {"ts": now.isoformat(), "probability": 0.65},
        ]
        result = polymarket.compute_24h_delta_from_snapshots(snapshots, now=now)
        assert result is None

    def test_closest_to_target_wins(self):
        """Birden fazla snapshot toleransta — 24h'a en yakın kazanır."""
        now = self._now()
        snapshots = [
            {"ts": (now - timedelta(hours=22)).isoformat(), "probability": 0.40},
            {"ts": (now - timedelta(hours=24)).isoformat(), "probability": 0.50},  # tam 24h
            {"ts": (now - timedelta(hours=25, minutes=30)).isoformat(), "probability": 0.55},
            {"ts": now.isoformat(), "probability": 0.65},
        ]
        result = polymarket.compute_24h_delta_from_snapshots(snapshots, now=now)
        assert result is not None
        # 24h tam matchli olan kazanır
        assert result["probability_24h_ago"] == 0.50

    def test_empty_snapshots(self):
        assert polymarket.compute_24h_delta_from_snapshots([], now=self._now()) is None

    def test_single_snapshot(self):
        now = self._now()
        snapshots = [{"ts": now.isoformat(), "probability": 0.50}]
        assert polymarket.compute_24h_delta_from_snapshots(snapshots, now=now) is None

    def test_malformed_snapshot_skipped(self):
        """Bozuk ts veya probability olan snapshot'lar atlanır."""
        now = self._now()
        snapshots = [
            {"ts": "not-a-date", "probability": 0.40},  # bozuk
            {"ts": (now - timedelta(hours=24)).isoformat(), "probability": 0.50},
            {"ts": now.isoformat(), "probability": "not-a-number"},  # bozuk
            {"ts": now.isoformat(), "probability": 0.65},
        ]
        result = polymarket.compute_24h_delta_from_snapshots(snapshots, now=now)
        # Bozuklar atlandı, 0.50 ve 0.65 kullanıldı
        assert result is not None
        assert result["probability_24h_ago"] == 0.50

    def test_non_list_input(self):
        assert polymarket.compute_24h_delta_from_snapshots(None, now=self._now()) is None  # type: ignore[arg-type]
        assert polymarket.compute_24h_delta_from_snapshots("not-a-list", now=self._now()) is None  # type: ignore[arg-type]

    def test_z_suffix_iso_parsed(self):
        """'Z' suffix ISO formatı parse edilebilmeli."""
        now = self._now()
        ts_24h_ago = (now - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
        ts_now = now.isoformat().replace("+00:00", "Z")
        snapshots = [
            {"ts": ts_24h_ago, "probability": 0.50},
            {"ts": ts_now, "probability": 0.65},
        ]
        result = polymarket.compute_24h_delta_from_snapshots(snapshots, now=now)
        assert result is not None
        assert result["probability_24h_ago"] == 0.50


# ── refresh_cache_for_themes ───────────────────────────────────────────────────


class TestRefreshCache:
    def test_refresh_with_mock_market(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        mock_themes = {"themes": {
            "t1": {"polymarket_slugs": ["slug-1", "slug-2"]}
        }}
        mock_markets = [
            {
                "id": "0x1", "slug": "slug-1",
                "question": "Q1",
                "outcomes": ["Yes", "No"],
                "outcomePrices": ["0.65", "0.35"],
                "volume": 1500000,
            },
            {
                "id": "0x2", "slug": "slug-2",
                "question": "Q2",
                "outcomes": ["Yes", "No"],
                "outcomePrices": ["0.45", "0.55"],
                "volume": 800000,
            },
        ]
        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: mock_markets)

        now = datetime(2026, 5, 17, 15, 0, 0, tzinfo=timezone.utc)
        result = polymarket.refresh_cache_for_themes(
            themes_config=mock_themes, now=now
        )

        assert "slug-1" in result["markets"]
        assert "slug-2" in result["markets"]
        assert result["markets"]["slug-1"]["current_probability"] == 0.65
        assert result["markets"]["slug-2"]["current_probability"] == 0.45
        assert result["_fetched_at"] == now.isoformat()
        # Dosya yazıldı
        assert cache_path.exists()
        saved = json.loads(cache_path.read_text())
        assert "slug-1" in saved["markets"]

    def test_refresh_save_false_no_disk_write(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        mock_themes = {"themes": {"t1": {"polymarket_slugs": ["x"]}}}
        mock_market = {
            "slug": "x", "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.5", "0.5"],
            "volume": 1000000,
        }
        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: [mock_market])

        polymarket.refresh_cache_for_themes(
            themes_config=mock_themes, save=False
        )
        # Disk yazılmadı
        assert not cache_path.exists()

    def test_refresh_no_themes(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)
        # fetch_markets çağrılmamalı — boş themes
        called = []
        monkeypatch.setattr(polymarket, "fetch_markets",
                            lambda **kw: called.append(kw) or [])
        polymarket.refresh_cache_for_themes(themes_config={"themes": {}})
        assert len(called) == 0  # Hiç fetch yok

    def test_refresh_skips_non_binary_markets(self, tmp_path, monkeypatch):
        """Binary olmayan (3+ outcome) marketler atlanır."""
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        mock_themes = {"themes": {"t1": {"polymarket_slugs": ["multi"]}}}
        mock_market = {
            "slug": "multi",
            "outcomes": ["A", "B", "C"],  # binary değil
            "outcomePrices": ["0.3", "0.3", "0.4"],
            "volume": 1000000,
        }
        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: [mock_market])

        result = polymarket.refresh_cache_for_themes(themes_config=mock_themes, save=False)
        # multi market eklenmedi
        assert "multi" not in result.get("markets", {})

    def test_refresh_accumulates_snapshots(self, tmp_path, monkeypatch):
        """İki ardışık refresh → 2 snapshot, ikinci'sinde delta hesaplanır (24h aralıklı)."""
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(polymarket, "CACHE_PATH", cache_path)

        mock_themes = {"themes": {"t1": {"polymarket_slugs": ["x"]}}}
        market_v1 = {
            "slug": "x", "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.50", "0.50"], "volume": 1000000,
        }
        market_v2 = {
            "slug": "x", "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.65", "0.35"], "volume": 1100000,
        }

        t0 = datetime(2026, 5, 16, 15, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(hours=24)

        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: [market_v1])
        polymarket.refresh_cache_for_themes(themes_config=mock_themes, now=t0)

        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: [market_v2])
        result = polymarket.refresh_cache_for_themes(themes_config=mock_themes, now=t1)

        entry = result["markets"]["x"]
        assert len(entry["snapshots"]) == 2
        assert entry["current_probability"] == 0.65
        assert entry["probability_24h_ago"] == 0.50
        assert entry["delta_24h"] == pytest.approx(0.15)
