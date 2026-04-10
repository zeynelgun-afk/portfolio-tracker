#!/usr/bin/env python3
"""
Finzora Agent — Araç Fonksiyonları
====================================
FMP veri çekme, Telegram gönderme, portföy okuma.
Phase 1: Tüm fonksiyonlar sadece OKUR, yazmaz.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

FMP_KEY      = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_BASE     = "https://financialmodelingprep.com/stable"
BOT_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
PRIVATE_CHAT = os.environ.get("TELEGRAM_PRIVATE_CHAT", "1403072107")  # Zeynel private
REPO_ROOT    = Path(__file__).parent.parent


# ── FMP Yardımcısı ────────────────────────────────────────────────────────────

def fmp_get(endpoint: str, params: dict = None) -> list | dict:
    """FMP stable API'den veri çeker."""
    p = params or {}
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[FMP] Hata ({endpoint}): {e}")
        return []


# ── Portföy Okuma ─────────────────────────────────────────────────────────────

def get_portfolio_snapshot() -> dict:
    """
    3 portföyü okur, canlı fiyatları FMP'den çeker.
    Dönen dict: {aggressive: {...}, balanced: {...}, dividend: {...}}
    """
    portfolios = {}
    symbols    = set()

    for name in ["aggressive", "balanced", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{name}.json"
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        portfolios[name] = data

        for pos in data.get("pozisyonlar", []):
            sym = pos.get("sembol") or pos.get("symbol")
            if sym:
                symbols.add(sym)

    # Canlı fiyatları çek
    if symbols:
        quotes = fmp_get("batch-quote", {"symbols": ",".join(symbols)})
        price_map = {q["symbol"]: q for q in quotes} if isinstance(quotes, list) else {}

        for name, data in portfolios.items():
            for pos in data.get("pozisyonlar", []):
                sym = pos.get("sembol") or pos.get("symbol")
                if sym and sym in price_map:
                    q = price_map[sym]
                    pos["guncel_fiyat"]   = q.get("price")
                    pos["gunluk_degisim"] = q.get("changesPercentage")
                    pos["hacim"]          = q.get("volume")

    return portfolios


def get_market_context() -> dict:
    """SPY, QQQ, VIXY anlık durum."""
    syms   = ["SPY", "QQQ", "VIXY", "GLD", "TLT"]
    quotes = fmp_get("batch-quote", {"symbols": ",".join(syms)})

    result = {}
    if isinstance(quotes, list):
        for q in quotes:
            result[q["symbol"]] = {
                "price": q.get("price"),
                "chg":   q.get("changesPercentage"),
                "vol":   q.get("volume"),
            }
    return result


def get_swing_status() -> dict:
    """Aktif swing pozisyonlarını okur."""
    path = REPO_ROOT / "data" / "swing" / "active.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_watchlist() -> dict:
    """Watchlist'i okur."""
    path = REPO_ROOT / "data" / "watchlist.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Telegram ─────────────────────────────────────────────────────────────────

def send_private_telegram(message: str) -> bool:
    """
    Zeynel'e özel Telegram mesajı gönderir.
    Finzora kanalına YAZMIYOR — sadece private chat.
    """
    if not BOT_TOKEN or not PRIVATE_CHAT:
        print(f"[Telegram] Config eksik. BOT_TOKEN={bool(BOT_TOKEN)}, CHAT={bool(PRIVATE_CHAT)}")
        print(f"[Telegram] Mesaj (gönderilmedi):\n{message[:200]}")
        return False

    # Telegram 4096 karakter limiti
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]

    success = True
    for chunk in chunks:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": PRIVATE_CHAT,
                    "text":    chunk,
                    # parse_mode yok — düz metin, markdown hatası olmaz
                },
                timeout=10,
            )
            if not r.ok:
                print(f"[Telegram] Hata: {r.status_code} {r.text[:100]}")
                success = False
        except Exception as e:
            print(f"[Telegram] İstisna: {e}")
            success = False

    return success
