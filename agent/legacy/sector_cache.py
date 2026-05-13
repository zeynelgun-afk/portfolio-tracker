#!/usr/bin/env python3
"""
Finzora — Sektör Cache
========================
Sembol → sektör eşleştirmesini FMP profile'dan çeker ve disk cache'ler.

risk_engine.SECTOR_MAP 26 sembol hardcoded'du → POWL, MRVL, PM, SM, KOS vs.
eksik. Konsantrasyon analizi yanlış çıkıyordu.

Kullanım:
    from sector_cache import get_sector, bulk_get_sectors
    s = get_sector("POWL")      # "Industrials" gibi
    m = bulk_get_sectors(["POWL","MRVL","SM"])  # {symbol: sector}
"""

import os
import json
import time
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CACHE_PATH = _REPO_ROOT / "data" / "sector_cache.json"
_CACHE_TTL_SEC = 7 * 24 * 3600  # 7 gün — sektör nadiren değişir

_FMP_KEY = os.environ.get("FMP_API_KEY", "")
_FMP_BASE = "https://financialmodelingprep.com/stable"

# Hardcoded fallback (tanıdığımız semboller için API patlamasına karşı)
_HARDCODED = {
    "SPY": "index", "QQQ": "index", "IWM": "index", "DIA": "index",
    "GLD": "commodities", "SLV": "commodities", "USO": "commodities",
    "TLT": "bonds", "HYG": "bonds", "AGG": "bonds",
    "VIX": "volatility", "VIXY": "volatility",
}


def _load_cache() -> dict:
    if not _CACHE_PATH.exists():
        return {"sectors": {}, "updated": {}}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"sectors": {}, "updated": {}}


def _save_cache(data: dict) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[sector_cache] cache yazımı atlandı: {e}")


def _fetch_sector_fmp(symbol: str) -> str | None:
    """FMP profile'dan sektör çek."""
    if not _FMP_KEY:
        return None
    try:
        import requests
        r = requests.get(
            f"{_FMP_BASE}/profile",
            params={"symbol": symbol, "apikey": _FMP_KEY},
            timeout=6,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list) and data:
            sector = data[0].get("sector") or ""
            if sector:
                # Normalize — risk_engine'in beklediği formata yakınlaştır
                return sector.strip().lower().replace(" ", "_").replace("-", "_")
        return None
    except Exception:
        return None


def get_sector(symbol: str, force_refresh: bool = False) -> str:
    """
    Sembol için sektör döner. Cache öncelikli.

    Returns: normalize edilmiş sektör string'i (lower_snake_case)
             ya da "diger" (hiçbir kaynak bulamazsa)
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return "diger"

    # Hardcoded mappingler önce (risk_engine ile uyum için)
    if symbol in _HARDCODED:
        return _HARDCODED[symbol]

    cache = _load_cache()
    sectors = cache.get("sectors", {})
    updated = cache.get("updated", {})

    if not force_refresh and symbol in sectors:
        last = updated.get(symbol, 0)
        age = time.time() - last
        if age < _CACHE_TTL_SEC:
            return sectors[symbol]

    # FMP'den çek
    sector = _fetch_sector_fmp(symbol)
    if sector:
        sectors[symbol] = sector
        updated[symbol] = int(time.time())
        cache["sectors"] = sectors
        cache["updated"] = updated
        _save_cache(cache)
        return sector

    # Başarısız — varsa eski cache'e düş
    if symbol in sectors:
        return sectors[symbol]

    return "diger"


def bulk_get_sectors(symbols: Iterable[str]) -> dict[str, str]:
    """Çoklu sembol için tek çağrıda (sıralı FMP) sektör eşleştirmesi."""
    return {s: get_sector(s) for s in symbols}


if __name__ == "__main__":
    import sys
    syms = sys.argv[1:] if len(sys.argv) > 1 else ["POWL", "MRVL", "SM", "KOS", "AAPL"]
    print("Sembol sektörleri:")
    for s in syms:
        print(f"  {s:6} → {get_sector(s)}")
