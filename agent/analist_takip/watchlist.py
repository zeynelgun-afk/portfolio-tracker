"""
Analist Takip — Watchlist Yöneticisi

Hangi ticker'ları takip ediyoruz:
1. Portföydeki tüm ticker'lar (3 portföy + swing active)
2. Son 14 gün bilanço açıklayan ABD hisseleri
3. Manuel watchlist (data/analist_takip/manual_watchlist.json)
"""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

from .config import (
    PORTFOLIO_FILES,
    SWING_ACTIVE_FILE,
    WATCHLIST_PATH,
    POST_EARNINGS_WATCH_DAYS,
    FMP_BASE,
    get_fmp_key,
)


def get_portfolio_tickers() -> set[str]:
    """3 portföy + swing active ticker'larını döner.
    
    Portföy JSON Türkçe şema: {'pozisyonlar': [{'sembol': 'PPG', ...}, ...]}
    Swing JSON: {'aktif_pozisyonlar': [...]}
    """
    tickers = set()

    # Portföyler (pozisyonlar / sembol)
    for portfolio_file in PORTFOLIO_FILES:
        p = Path(portfolio_file)
        if not p.exists():
            continue
        try:
            with open(p) as f:
                data = json.load(f)
            # Türkçe + İngilizce + alternatif anahtarlar
            positions = (
                data.get("pozisyonlar")
                or data.get("positions")
                or data.get("holdings")
                or []
            )
            for pos in positions:
                if isinstance(pos, dict):
                    t = (
                        pos.get("sembol")
                        or pos.get("symbol")
                        or pos.get("ticker")
                    )
                    if t:
                        tickers.add(t.upper())
        except Exception:
            continue

    # Swing pozisyonları (aktif_pozisyonlar / sembol)
    sp = Path(SWING_ACTIVE_FILE)
    if sp.exists():
        try:
            with open(sp) as f:
                data = json.load(f)
            if isinstance(data, dict):
                positions = (
                    data.get("aktif_pozisyonlar")
                    or data.get("pozisyonlar")
                    or data.get("positions")
                    or []
                )
            elif isinstance(data, list):
                positions = data
            else:
                positions = []
            for pos in positions:
                if isinstance(pos, dict):
                    t = (
                        pos.get("sembol")
                        or pos.get("symbol")
                        or pos.get("ticker")
                    )
                    if t:
                        tickers.add(t.upper())
        except Exception:
            pass

    return tickers


def _fetch_market_caps_batch(tickers: list[str], fmp_key: str) -> dict[str, float]:
    """
    Verilen ticker listesi için market cap'leri toplu çek.
    FMP quote endpoint tek tek çağrılır (parallel toplu yok)
    ama sadece bilanço açıklayan ~150-300 ticker için yapılır.
    """
    caps = {}
    for t in tickers:
        try:
            r = requests.get(
                f"{FMP_BASE}/quote",
                params={"symbol": t, "apikey": fmp_key},
                timeout=8,
            )
            if r.ok:
                data = r.json()
                if isinstance(data, list) and data:
                    mcap = data[0].get("marketCap", 0)
                    caps[t] = mcap / 1e9 if mcap else 0
        except Exception:
            caps[t] = 0
    return caps


def get_recent_earnings_tickers(
    days_back: int = POST_EARNINGS_WATCH_DAYS,
    min_market_cap_b: Optional[float] = None,
) -> set[str]:
    """
    Son `days_back` gün içinde bilanço açıklayan ABD mid-cap+ hisseleri.
    """
    from .config import MIN_MARKET_CAP_B
    if min_market_cap_b is None:
        min_market_cap_b = MIN_MARKET_CAP_B

    end = date.today()
    start = end - timedelta(days=days_back)

    fmp_key = get_fmp_key()
    try:
        r = requests.get(
            f"{FMP_BASE}/earnings-calendar",
            params={"from": start.isoformat(), "to": end.isoformat(), "apikey": fmp_key},
            timeout=30,
        )
        if not r.ok:
            return set()
    except Exception:
        return set()

    # Önce ABD ticker filter
    candidates = set()
    for e in r.json():
        t = e.get("symbol")
        if not t:
            continue
        if "." in t:
            parts = t.split(".")
            if len(parts) != 2:
                continue
            main, suffix = parts
            if len(suffix) != 1 or not suffix.isalpha():
                continue
            if not (1 <= len(main) <= 4 and main.isalpha()):
                continue
        else:
            if not (1 <= len(t) <= 5 and t.isalpha()):
                continue
        candidates.add(t.upper())

    # Market cap filter — batch fetch
    if not candidates:
        return set()

    caps = _fetch_market_caps_batch(list(candidates), fmp_key)
    tickers = {t for t, mcap in caps.items() if mcap >= min_market_cap_b}

    return tickers


def get_manual_watchlist() -> set[str]:
    """data/analist_takip/manual_watchlist.json — opsiyonel."""
    manual_file = Path(WATCHLIST_PATH).parent / "manual_watchlist.json"
    if not manual_file.exists():
        return set()
    try:
        with open(manual_file) as f:
            data = json.load(f)
        if isinstance(data, list):
            return {t.upper() for t in data if isinstance(t, str)}
        elif isinstance(data, dict) and "tickers" in data:
            return {t.upper() for t in data["tickers"]}
    except Exception:
        pass
    return set()


def build_watchlist(include_recent_earnings: bool = True) -> dict:
    """
    Sinyal kaynağı watchlist'i (polling için).
    
    Kaynaklar:
    1. Son 14 gün bilanço açıklayan ABD mid-cap+ hisseler (asıl kaynak)
    2. Manuel watchlist (data/analist_takip/manual_watchlist.json)
    
    NOT: Portföy ticker'ları artık watchlist'e DAHIL EDİLMİYOR (12 May).
    Portföy izleme = data/portfolios/*.json'da ayrı sistem.
    Analist Takip = bağımsız sinyal arama sistemi.
    """
    manual = get_manual_watchlist()

    if include_recent_earnings:
        recent_earnings = get_recent_earnings_tickers()
    else:
        recent_earnings = set()

    combined = recent_earnings | manual

    return {
        "portfolio": [],  # KALDIRILDI
        "recent_earnings": sorted(recent_earnings),
        "manual": sorted(manual),
        "combined": sorted(combined),
        "portfolio_count": 0,
        "recent_earnings_count": len(recent_earnings),
        "manual_count": len(manual),
        "total_count": len(combined),
        "built_at": datetime.utcnow().isoformat() + "Z",
    }


def save_watchlist(watchlist: dict) -> None:
    """Watchlist'i diske kaydet (debug / audit için)."""
    p = Path(WATCHLIST_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(watchlist, f, indent=2, ensure_ascii=False)


def load_watchlist() -> dict:
    """En son kaydedilen watchlist'i oku."""
    p = Path(WATCHLIST_PATH)
    if not p.exists():
        return build_watchlist()
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return build_watchlist()
