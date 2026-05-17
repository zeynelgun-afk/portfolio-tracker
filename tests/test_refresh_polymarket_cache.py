"""scripts/refresh_polymarket_cache.py için testler.

Faz 2 — Adım 10b-i: Polymarket fetch scheduler entry-point.

KAPSAM:
    - main() argümansız çağırıldığında dry-run değil — gerçek save
    - --dry-run save_cache çağırmaz
    - --verbose her market için log basar
    - Boş whitelist durumunda graceful exit
    - refresh_cache_for_themes exception durumunda return 1
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "refresh_polymarket_cache.py"


def _load_script_module():
    """Scripti modül olarak yükle — runpy yerine importlib ile test edilebilir."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("refresh_polymarket_cache", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRefreshScript:
    def test_main_dry_run(self, monkeypatch, tmp_path, capsys):
        """--dry-run save çağrısı yapmamalı."""
        from agent import polymarket

        mock_themes = {"themes": {"t1": {"polymarket_slugs": ["slug-1"]}}}
        mock_markets = [{
            "slug": "slug-1",
            "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.6", "0.4"],
            "volume": 1000000,
        }]

        save_calls = []
        monkeypatch.setattr(polymarket, "load_themes", lambda: mock_themes)
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {}})
        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: mock_markets)
        monkeypatch.setattr(polymarket, "save_cache",
                            lambda payload: save_calls.append(payload))

        module = _load_script_module()
        rc = module.main(["--dry-run"])
        captured = capsys.readouterr()

        assert rc == 0
        assert len(save_calls) == 0  # dry-run: save yapılmadı
        assert "DRY-RUN: cache disk'e YAZILMADI" in captured.out

    def test_main_normal_run_saves(self, monkeypatch, tmp_path):
        """--dry-run yoksa save_cache çağrılmalı."""
        from agent import polymarket

        mock_themes = {"themes": {"t1": {"polymarket_slugs": ["slug-1"]}}}
        mock_markets = [{
            "slug": "slug-1",
            "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.6", "0.4"],
            "volume": 1000000,
        }]

        save_calls = []
        monkeypatch.setattr(polymarket, "load_themes", lambda: mock_themes)
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {}})
        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: mock_markets)
        monkeypatch.setattr(polymarket, "save_cache",
                            lambda payload: save_calls.append(payload))

        module = _load_script_module()
        rc = module.main([])

        assert rc == 0
        assert len(save_calls) == 1  # save bir kez çağrıldı
        saved = save_calls[0]
        assert "slug-1" in saved.get("markets", {})

    def test_main_empty_whitelist_graceful(self, monkeypatch, capsys):
        """Whitelist boşsa hata değil, uyarı log + rc=0."""
        from agent import polymarket

        monkeypatch.setattr(polymarket, "load_themes", lambda: {"themes": {}})
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {}})

        called_fetch = []
        monkeypatch.setattr(polymarket, "fetch_markets",
                            lambda **kw: called_fetch.append(kw) or [])

        module = _load_script_module()
        rc = module.main([])
        captured = capsys.readouterr()

        assert rc == 0
        assert len(called_fetch) == 0  # fetch çağrılmadı
        assert "Whitelist boş" in captured.out

    def test_main_refresh_exception_returns_1(self, monkeypatch, capsys):
        """refresh_cache_for_themes patladığında rc=1."""
        from agent import polymarket

        mock_themes = {"themes": {"t1": {"polymarket_slugs": ["slug-1"]}}}
        monkeypatch.setattr(polymarket, "load_themes", lambda: mock_themes)
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {}})

        def _boom(**kwargs):
            raise RuntimeError("Gamma API down")

        monkeypatch.setattr(polymarket, "refresh_cache_for_themes", _boom)

        module = _load_script_module()
        rc = module.main([])
        captured = capsys.readouterr()

        assert rc == 1
        assert "HATA" in captured.out

    def test_main_verbose_logs_each_market(self, monkeypatch, capsys):
        """--verbose her slug için log üretir."""
        from agent import polymarket

        mock_themes = {"themes": {"t1": {"polymarket_slugs": ["alpha-slug", "beta-slug"]}}}
        mock_markets = [
            {"slug": "alpha-slug", "outcomes": ["Yes", "No"],
             "outcomePrices": ["0.6", "0.4"], "volume": 1000000},
            {"slug": "beta-slug", "outcomes": ["Yes", "No"],
             "outcomePrices": ["0.3", "0.7"], "volume": 800000},
        ]
        monkeypatch.setattr(polymarket, "load_themes", lambda: mock_themes)
        monkeypatch.setattr(polymarket, "load_cache", lambda: {"markets": {}})
        monkeypatch.setattr(polymarket, "fetch_markets", lambda **kw: mock_markets)
        monkeypatch.setattr(polymarket, "save_cache", lambda payload: None)

        module = _load_script_module()
        rc = module.main(["--verbose"])
        captured = capsys.readouterr()

        assert rc == 0
        # Whitelist log'unda iki slug var
        assert "alpha-slug" in captured.out
        assert "beta-slug" in captured.out
