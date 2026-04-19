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

# Merkezi config (eksik env'de uyarı verir, crash etmez)
try:
    from _config import FMP_KEY, FMP_BASE, TELEGRAM_TOKEN, TELEGRAM_PRIVATE_CHAT
    BOT_TOKEN = TELEGRAM_TOKEN
    PRIVATE_CHAT = TELEGRAM_PRIVATE_CHAT
except ImportError:
    # Geriye uyumluluk: _config.py yoksa direkt env'den oku
    FMP_KEY = os.environ.get("FMP_API_KEY", "")
    FMP_BASE = "https://financialmodelingprep.com/stable"
    BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    PRIVATE_CHAT = os.environ.get("TELEGRAM_PRIVATE_CHAT", "")

REPO_ROOT = Path(__file__).parent.parent


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
        err_str = str(e)
        print(f"[FMP] Hata ({endpoint}): {err_str}")
        # Kritik HTTP hataları Telegram'a git
        if any(code in err_str for code in ["402", "429", "500", "503", "ConnectionError", "Timeout"]):
            _log.hata(
                f"FMP API hatası: {endpoint}",
                f"Hata: {err_str[:150]}",
                kaynak="tools.fmp_get"
            )
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
    VIX değerini çeker (merkezi vix_fetcher üzerinden).
    Kaynak zinciri: cache → Yahoo q1 → Yahoo q2 → FMP → stale cache → default
    VIXY/UVXY doğrudan kullanılmaz — contango nedeniyle yanıltıcı.
    """
    def _seviye(price):
        if price is None: return "UNKNOWN"
        if price < 18:   return "DÜŞÜK (Risk-On)"
        if price < 25:   return "NORMAL"
        if price < 30:   return "YÜKSEK — K-13 aktif"
        return "EKSTREM — yeni giriş dur"

    # Merkezi vix_fetcher (cache + Yahoo + FMP fallback)
    try:
        from vix_fetcher import get_vix
        price, source = get_vix()
    except Exception as e:
        print(f"[VIX] vix_fetcher hatası: {e}")
        price, source = 20.0, "error_default"

    # Dünkü kapanışı + değişim hesabı için Yahoo'dan 5 gün çekme denemesi
    # (sadece chg hesabı için; ana VIX fiyatı yukarıda merkezi modülden geldi)
    chg = None
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
            params={"interval": "1d", "range": "5d"},
            headers={"User-Agent": "Mozilla/5.0 (compatible; Finzora/1.0)"},
            timeout=6,
        ).json()
        result = r["chart"]["result"][0]
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        valid  = [c for c in closes if c is not None]
        if price and len(valid) >= 2:
            prev = valid[-2]
            chg  = round((price - prev) / prev * 100, 2) if prev else None
    except Exception:
        pass

    return {
        "price":     round(float(price), 2),
        "chg":       chg,
        "seviye":    _seviye(price),
        "kaynak":    f"vix_fetcher:{source}",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


def _old_get_real_vix_legacy_reference() -> dict:
    """Referans amaçlı eski multi-source implementasyon (kullanılmıyor)."""
    def _seviye(price):
        if price is None: return "UNKNOWN"
        if price < 18:   return "DÜŞÜK (Risk-On)"
        if price < 25:   return "NORMAL"
        if price < 30:   return "YÜKSEK — K-13 aktif"
        return "EKSTREM — yeni giriş dur"

    # ── 1. Yahoo Finance ──────────────────────────────────────────────────────
    for yahoo_url in [
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
        "https://query2.finance.yahoo.com/v8/finance/chart/%5EVIX",
    ]:
        try:
            r = requests.get(
                yahoo_url,
                params={"interval": "1d", "range": "5d"},
                headers={"User-Agent": "Mozilla/5.0 (compatible; Finzora/1.0)"},
                timeout=8,
            ).json()
            result = r["chart"]["result"][0]
            price  = result["meta"].get("regularMarketPrice")
            closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            valid  = [c for c in closes if c is not None]
            prev   = valid[-2] if len(valid) >= 2 else None
            chg    = round((price - prev) / prev * 100, 2) if price and prev else None
            if price:
                vix_result = {"price": price, "chg": chg,
                        "seviye": _seviye(price), "kaynak": "CBOE/Yahoo",
                        "timestamp": __import__("datetime").datetime.now().isoformat()}
                try:
                    import json as _jc
                    _jc.dump(vix_result, open(
                        str(Path(__file__).parent.parent / "data" / "vix_cache.json"), "w"))
                except Exception:
                    pass
                return vix_result
        except Exception:
            continue

    # ── 2. FMP fallback ───────────────────────────────────────────────────────
    try:
        fmp_key = os.environ.get("FMP_API_KEY", "")
        r = requests.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": "VIXY", "apikey": fmp_key},
            timeout=8,
        ).json()
        if r and isinstance(r, list):
            vixy_price = float(r[0].get("price", 0))
            vixy_prev  = float(r[0].get("previousClose", vixy_price))
            vixy_chg   = (vixy_price - vixy_prev) / vixy_prev * 100 if vixy_prev else 0
            # VIXY → VIX kaba dönüşüm (yaklaşık 0.5x çarpan — contango)
            vix_est = round(vixy_price / 0.5, 2)
            print(f"[VIX] FMP/VIXY proxy: VIXY={vixy_price:.2f} → VIX≈{vix_est:.1f} (yaklaşık)")
            return {"price": vix_est, "chg": round(vixy_chg, 2),
                    "seviye": _seviye(vix_est), "kaynak": "FMP/VIXY-proxy",
                    "uyari": "VIXY proxy — yaklaşık değer"}
    except Exception as e2:
        print(f"[VIX] FMP fallback hatası: {e2}")

    # ── 3. Cache ──────────────────────────────────────────────────────────────
    try:
        cache_path = Path(__file__).parent.parent / "data" / "vix_cache.json"
        if cache_path.exists():
            import json as _j
            cached = _j.load(open(cache_path))
            age_min = (datetime.now() - datetime.fromisoformat(cached["timestamp"])).seconds // 60
            if age_min < 120:  # 2 saatten eskiyse kullanma
                print(f"[VIX] Cache kullanıldı ({age_min}dk önce): {cached['price']}")
                cached["kaynak"] = f"cache({age_min}dk önce)"
                return cached
    except Exception:
        pass

    print("[VIX] Tüm kaynaklar başarısız — UNKNOWN döndürülüyor")
    _log.uyari("VIX verisi alınamadı — tüm kaynaklar denendi", kaynak="tools.get_real_vix")
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


def get_portfolio_news(saat: int = 24) -> str:
    """
    Aktif portföy hisselerinin son N saatlik haberlerini FMP'den çeker.
    Orchestrator'ın Claude bağlamına eklenir — haber bazlı tez analizi için.
    Döndürür: Düz metin (prompt'a doğrudan eklenebilir).
    """
    from datetime import timezone, timedelta

    # Tüm portföy sembollerini topla
    semboller = set()
    for pf in ["aggressive", "balanced", "dividend"]:
        p = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if p.exists():
            try:
                d = json.load(open(p, encoding="utf-8"))
                for pos in d.get("pozisyonlar", []):
                    s = pos.get("sembol") or pos.get("symbol")
                    if s:
                        semboller.add(s)
            except Exception:
                pass

    if not semboller:
        return ""

    haberler = fmp_get("news/stock", {"symbols": ",".join(semboller), "limit": 60})
    if not haberler or not isinstance(haberler, list):
        return ""

    sinir = datetime.now(timezone.utc) - timedelta(hours=saat)
    guncel = []
    for h in haberler:
        try:
            pub = h.get("publishedDate", "")
            if "T" in pub:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(pub[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if dt < sinir:
                continue
            yas_s = int((datetime.now(timezone.utc) - dt).total_seconds() / 3600)
            guncel.append((yas_s, h))
        except Exception:
            continue

    if not guncel:
        return f"[Portföy Haberleri] Son {saat} saatte haber yok."

    guncel.sort(key=lambda x: x[0])

    satirlar = [f"=== PORTFÖY HABERLERİ (son {saat} saat, {len(guncel)} haber) ==="]
    # Sembol başına max 3 haber, toplam max 15
    sembol_sayac: dict[str, int] = {}
    for yas_s, h in guncel:
        sym = h.get("symbol", "?")
        if sembol_sayac.get(sym, 0) >= 3:
            continue
        if sum(sembol_sayac.values()) >= 15:
            break
        sembol_sayac[sym] = sembol_sayac.get(sym, 0) + 1
        satirlar.append(
            f"[{sym} — {yas_s}s önce — {h.get('site','')}]\n"
            f"  {h.get('title','')}\n"
            f"  {(h.get('text') or '')[:200]}"
        )

    return "\n".join(satirlar)


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

# ── Canlı RSI Batch Fetch ──────────────────────────────────────────────────────

def get_rsi_batch(symbols: list, period: int = 14) -> dict:
    """
    Verilen semboller için FMP'den güncel RSI değerlerini çeker.
    Döner: {symbol: rsi_float}  — başarısız semboller eksik kalır.
    
    Kullanım: monitor modunda portföy + swing RSI gerçek zamanlı alınır.
    API: /stable/technical-indicators/rsi?symbol=X&periodLength=14&timeframe=1day
    """
    rsi_map = {}
    if not symbols:
        return rsi_map

    print(f"[RSI] {len(symbols)} sembol için canlı RSI çekiliyor...")
    for sym in symbols:
        try:
            data = fmp_get(
                "technical-indicators/rsi",
                {"symbol": sym, "periodLength": period, "timeframe": "1day"}
            )
            if isinstance(data, list) and data:
                val = data[0].get("rsi")
                if val is not None:
                    rsi_map[sym] = round(float(val), 2)
        except Exception as e:
            print(f"[RSI] {sym} hatası: {e}")

    found = len(rsi_map)
    print(f"[RSI] Tamamlandı: {found}/{len(symbols)} sembol → {rsi_map}")
    return rsi_map

# ── Grup Telegram ─────────────────────────────────────────────────────────────

GROUP_CHAT = "-1003827034395"  # Finzora grubu

def send_group_telegram(message: str) -> bool:
    """Finzora grubuna mesaj gönderir.
    Sadece: alım/satım aksiyonları + günlük kapanış özeti.
    Detaylı raporlar finzora.ai üzerinden erişilebilir.
    """
    if not BOT_TOKEN:
        print("[Telegram/Grup] BOT_TOKEN yok")
        return False
    try:
        import requests as _req
        r = _req.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id":    GROUP_CHAT,
                "text":       message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        ok = r.json().get("ok", False)
        if not ok:
            print(f"[Telegram/Grup] Hata: {r.json().get('description','?')}")
        return ok
    except Exception as e:
        print(f"[Telegram/Grup] Exception: {e}")
        return False

