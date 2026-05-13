#!/usr/bin/env python3
"""
Finzora — Merkezi VIX Fetcher
=================================
Tüm agent + scripts VIX ihtiyacını buradan karşılar.
6 farklı yerde kopyalanmış VIX çekme mantığını tek yere topladı.

Sıralı kaynaklar (19 Nisan 2026 güncellemesi — FMP ^VIX stabil çalışıyor):
  1. data/vix_cache.json (≤ 15 dakika eski) — rate limit'i koruma
  2. FMP stable ^VIX — birincil kaynak (19 Nisan 2026'da doğrulandı, 17.48 döndü)
  3. Yahoo Finance query1 (^VIX endpoint) — fallback
  4. Yahoo Finance query2 — son fallback

Cache: data/vix_cache.json
  {"value": 21.04, "ts": "2026-04-19T17:30:00Z", "source": "fmp"}
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CACHE_PATH = _REPO_ROOT / "data" / "vix_cache.json"
_CACHE_TTL_SEC = 15 * 60  # 15 dakika

_HEADERS = {"User-Agent": "Mozilla/5.0 (Finzora VIX Fetcher)"}
_TIMEOUT = 6


def _load_cache() -> dict | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        ts_str = data.get("ts", "")
        if not ts_str:
            return None
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > _CACHE_TTL_SEC:
            return None
        return data
    except Exception:
        return None


def _save_cache(value: float, source: str) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps({
                "value":  round(float(value), 2),
                "ts":     datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source": source,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[vix_fetcher] cache yazımı atlandı: {e}")


def _yahoo(host: str) -> float | None:
    """Yahoo Finance (^VIX) üzerinden anlık VIX çek."""
    url = f"https://{host}.finance.yahoo.com/v8/finance/chart/%5EVIX"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT,
                         params={"interval": "1d", "range": "1d"})
        if r.status_code != 200:
            return None
        data = r.json()
        result = data.get("chart", {}).get("result") or []
        if not result:
            return None
        price = result[0].get("meta", {}).get("regularMarketPrice")
        if price:
            return float(price)
    except Exception:
        return None
    return None


def _fmp() -> float | None:
    """FMP stable ^VIX — 19 Nisan 2026 doğrulandı: stabil çalışıyor (birincil kaynak)."""
    api_key = os.environ.get("FMP_API_KEY", "")
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": "^VIX", "apikey": api_key},
            timeout=_TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list) and data:
            price = data[0].get("price")
            if price:
                return float(price)
    except Exception:
        return None
    return None


def get_vix(force_refresh: bool = False, default: float = 20.0) -> tuple[float, str]:
    """
    Güncel VIX değerini döner (cache öncelikli).

    Args:
        force_refresh: True ise cache atla
        default: tüm kaynaklar patlarsa dönülecek değer

    Returns: (value, source)
        source ∈ {"cache", "yahoo_q1", "yahoo_q2", "fmp", "default"}
    """
    if not force_refresh:
        cached = _load_cache()
        if cached and "value" in cached:
            return float(cached["value"]), "cache"

    # FMP ^VIX — birincil (19 Nisan 2026 doğrulandı)
    v = _fmp()
    if v is not None and 0 < v < 200:
        _save_cache(v, "fmp")
        return v, "fmp"

    # Yahoo q1 fallback
    v = _yahoo("query1")
    if v is not None and 0 < v < 200:
        _save_cache(v, "yahoo_q1")
        return v, "yahoo_q1"

    # Yahoo q2 fallback
    v = _yahoo("query2")
    if v is not None and 0 < v < 200:
        _save_cache(v, "yahoo_q2")
        return v, "yahoo_q2"

    # Eski cache varsa (TTL geçmiş bile olsa) default'tan iyidir
    try:
        if _CACHE_PATH.exists():
            stale = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            if stale.get("value"):
                return float(stale["value"]), "cache_stale"
    except Exception:
        pass

    return default, "default"


if __name__ == "__main__":
    v, src = get_vix(force_refresh=True)
    print(f"VIX: {v} (source: {src})")
