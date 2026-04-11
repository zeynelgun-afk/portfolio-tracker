#!/usr/bin/env python3
"""
Finzora Agent — Araç Fonksiyonları
====================================
FMP veri çekme, Telegram gönderme, portföy okuma.
Phase 1: Tüm fonksiyonlar sadece OKUR, yazmaz.
"""

# --- olay kaydı ---
import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / 'scripts'))
try:
    from event_logger import log as _log
    _log.kaynak = 'tools'
except ImportError:
    class _FB:
        kaynak='tools'
        def __getattr__(self, n): return lambda *a, **kw: None
    _log = _FB()
# --- /olay kaydı ---

import os
import json
import requests
from pathlib import Path
from datetime import datetime

FMP_KEY      = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_BASE     = "https://financialmodelingprep.com/stable"
BOT_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "") or "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI"
PRIVATE_CHAT = os.environ.get("TELEGRAM_PRIVATE_CHAT", "") or "1403072107"
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


def get_real_vix() -> dict:
    """
    Yahoo Finance'dan gerçek CBOE VIX değerini çeker.
    VIXY/UVXY kullanma — contango nedeniyle yanıltıcı.
    """
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
            params={"interval": "1d", "range": "5d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        ).json()

        result = r["chart"]["result"][0]
        meta   = result["meta"]
        price  = meta.get("regularMarketPrice")

        # Önceki kapanışı geçmiş veriden al
        closes    = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        valid     = [c for c in closes if c is not None]
        prev      = valid[-2] if len(valid) >= 2 else None
        chg       = round((price - prev) / prev * 100, 2) if price and prev else None

        # Seviye yorumu (K-13 v4.1 bazlı)
        if price is None:
            seviye = "UNKNOWN"
        elif price < 18:
            seviye = "DÜŞÜK (Risk-On)"
        elif price < 25:
            seviye = "NORMAL"
        elif price < 30:
            seviye = "YÜKSEK — K-13 aktif"
        else:
            seviye = "EKSTREM — yeni giriş dur"

        return {
            "price":   price,
            "chg":     chg,
            "seviye":  seviye,
            "kaynak":  "CBOE/Yahoo",
        }

    except Exception as e:
        print(f"[VIX] Yahoo Finance hatası: {e}")
        return {"price": None, "chg": None, "seviye": "UNKNOWN", "kaynak": "hata"}


def get_market_context() -> dict:
    """SPY, QQQ, portföy hisseleri anlık durum + gerçek VIX."""
    import json
    from pathlib import Path

    base_syms = ["SPY", "QQQ", "GLD", "TLT", "IWM"]

    # Portföy + swing hisselerini ekle
    repo = Path(__file__).parent.parent
    pf_syms = set()
    for pf in ["aggressive", "balanced", "dividend"]:
        p = repo / "data" / "portfolios" / f"{pf}.json"
        if p.exists():
            try:
                d = json.load(open(p))
                for pos in d.get("pozisyonlar", []):
                    pf_syms.add(pos.get("sembol", ""))
            except Exception:
                pass

    swing_p = repo / "data" / "swing" / "active.json"
    if swing_p.exists():
        try:
            sw = json.load(open(swing_p))
            for pos in sw.get("aktif_pozisyonlar", []):
                pf_syms.add(pos.get("sembol", ""))
        except Exception:
            pass

    all_syms = list(set(base_syms) | pf_syms - {""})
    quotes   = fmp_get("batch-quote", {"symbols": ",".join(all_syms)})

    result = {}
    if isinstance(quotes, list):
        for q in quotes:
            sym   = q["symbol"]
            price = q.get("price")
            prev  = q.get("previousClose")

            chg = q.get("changesPercentage")
            if chg is None and price and prev and float(prev) != 0:
                chg = round((float(price) - float(prev)) / float(prev) * 100, 2)

            result[sym] = {
                "price":         price,
                "chg":           chg,
                "previousClose": prev,
                "volume":        q.get("volume"),
                "dayHigh":       q.get("dayHigh"),
                "dayLow":        q.get("dayLow"),
            }

    result["VIX"] = get_real_vix()
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
