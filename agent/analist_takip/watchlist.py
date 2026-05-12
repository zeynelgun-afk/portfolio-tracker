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
    """3 portföy + swing active ticker'larını döner."""
    tickers = set()

    for portfolio_file in PORTFOLIO_FILES:
        p = Path(portfolio_file)
        if not p.exists():
            continue
        try:
            with open(p) as f:
                data = json.load(f)
            # Portföy JSON şemasında pozisyonlar farklı isimle olabilir
            positions = data.get("positions") or data.get("holdings") or []
            for pos in positions:
                if isinstance(pos, dict):
                    t = pos.get("symbol") or pos.get("ticker")
                    if t:
                        tickers.add(t.upper())
        except Exception:
            continue

    # Swing
    sp = Path(SWING_ACTIVE_FILE)
    if sp.exists():
        try:
            with open(sp) as f:
                data = json.load(f)
            positions = data.get("positions", []) if isinstance(data, dict) else data
            for pos in positions:
                if isinstance(pos, dict):
                    t = pos.get("symbol") or pos.get("ticker")
                    if t:
                        tickers.add(t.upper())
        except Exception:
            pass

    return tickers


def get_recent_earnings_tickers(days_back: int = POST_EARNINGS_WATCH_DAYS) -> set[str]:
    """
    Son `days_back` gün içinde bilanço açıklayan ABD hisseleri.
    Sadece ABD borsaları: NYSE, NASDAQ. Suffix'li ticker'lar (KS, HK, TO) hariç.
    """
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

    tickers = set()
    for e in r.json():
        t = e.get("symbol")
        if not t:
            continue
        # ABD ticker filtreleri (sıkı):
        # - Maks 5 karakter (BRK.B 5 karakter dahil)
        # - Suffix'siz: AAPL, GOOGL
        # - Veya tek nokta + tek harf: BRK.B, BF.B
        # - Tüm karakterler harf olmalı (rakam yok, başka karakter yok)
        if "." in t:
            parts = t.split(".")
            if len(parts) != 2:
                continue
            main, suffix = parts
            # Suffix tek harf olmalı (.B, .A gibi)
            if len(suffix) != 1 or not suffix.isalpha():
                continue
            # Main 1-4 harf olmalı (BRK, BF gibi)
            if not (1 <= len(main) <= 4 and main.isalpha()):
                continue
        else:
            # Suffix'siz ticker: 1-5 harf, sadece alfabe
            if not (1 <= len(t) <= 5 and t.isalpha()):
                continue
        tickers.add(t.upper())

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
    Tüm kaynaklardan watchlist'i birleştir ve döner.
    """
    portfolio = get_portfolio_tickers()
    manual = get_manual_watchlist()

    if include_recent_earnings:
        recent_earnings = get_recent_earnings_tickers()
    else:
        recent_earnings = set()

    combined = portfolio | recent_earnings | manual

    return {
        "portfolio": sorted(portfolio),
        "recent_earnings": sorted(recent_earnings),
        "manual": sorted(manual),
        "combined": sorted(combined),
        "portfolio_count": len(portfolio),
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
