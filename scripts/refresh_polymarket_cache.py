#!/usr/bin/env python3
"""Polymarket cache refresh — Gamma API'den whitelist tema marketleri çek.

Faz 2 — Adım 10b-i (17 May 2026).

Bu script:
    1. data/polymarket_themes.json whitelist'inden slug'ları topla
    2. Gamma API'den fetch_markets(slugs=...) çağır
    3. Her market için snapshot ekle (sliding window 48h)
    4. current_probability + delta_24h hesapla
    5. data/polymarket_cache.json'a yaz

Çağrı:
    python3 scripts/refresh_polymarket_cache.py [--dry-run] [--verbose]

Production scheduler:
    .github/workflows/polymarket_refresh.yml (workflow_dispatch only — manuel)

NOT: Bu Adım 10b-i kapsamı. Kalibratör henüz scanner pipeline'a bağlı değil
(Adım 10b-ii'de yapılacak). Bu script şu an SADECE veri toplama yapıyor;
kalibratör çalışırsa zaten cache'i kullanacak.

Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 6, 13)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root'u path'e ekle
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def log(msg: str) -> None:
    """Basit log helper (stdout + flush)."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [polymarket-refresh] {msg}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Cache'i disk'e yazma, sadece konsola ne çekildiğini bas",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Her market için ayrıntılı log",
    )
    args = parser.parse_args(argv)

    log("Başlat: Polymarket cache refresh")

    # Lazy import — modül yüklenirken yan etki olmasın
    from agent.polymarket import (
        load_themes,
        load_cache,
        refresh_cache_for_themes,
        get_theme_slugs,
    )

    themes = load_themes()
    slugs = get_theme_slugs()
    log(f"Whitelist: {len(themes.get('themes', {}))} tema, {len(slugs)} slug")

    if args.verbose:
        for slug in sorted(slugs):
            log(f"  - {slug}")

    if not slugs:
        log("UYARI: Whitelist boş, fetch atlandı")
        return 0

    # Mevcut cache'i yükle (snapshot history korunsun)
    cache = load_cache()
    market_count_before = len(cache.get("markets", {}))
    log(f"Mevcut cache: {market_count_before} market (snapshot history)")

    # Refresh
    try:
        result = refresh_cache_for_themes(
            themes_config=themes,
            cache=cache,
            save=not args.dry_run,
        )
    except Exception as e:
        log(f"HATA: refresh_cache_for_themes patladı: {e}")
        return 1

    markets = result.get("markets", {})
    log(f"Refresh sonrası: {len(markets)} market")

    # Özet rapor
    new_count = 0
    updated_count = 0
    delta_available = 0
    for slug, entry in markets.items():
        snapshots = entry.get("snapshots", [])
        if len(snapshots) == 1:
            new_count += 1
        else:
            updated_count += 1
        if entry.get("delta_24h") is not None:
            delta_available += 1
        if args.verbose:
            current = entry.get("current_probability")
            delta = entry.get("delta_24h")
            delta_str = f"{delta:+.3f}" if isinstance(delta, (int, float)) else "—"
            log(
                f"  {slug}: current={current}, "
                f"snapshots={len(snapshots)}, delta_24h={delta_str}"
            )

    log(
        f"Özet: {new_count} yeni, {updated_count} mevcut snapshot eklendi, "
        f"{delta_available} market için delta_24h hazır"
    )

    if args.dry_run:
        log("DRY-RUN: cache disk'e YAZILMADI")
    else:
        from agent.polymarket import CACHE_PATH
        log(f"Cache yazıldı: {CACHE_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
