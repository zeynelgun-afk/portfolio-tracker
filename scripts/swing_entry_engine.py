#!/usr/bin/env python3
"""
Finzora Swing Entry Engine v2.0
=================================
Mevcut sorun: Sistem 4/4 gören ama "giriş sinyali yok" diyor.
Neden? Çünkü sadece 2 sinyal var: kumo kırılımı + kijun bounce.

Yeni giriş sinyalleri (araştırma bazlı):
  1. Tenkan Bounce    → Güçlü trend içinde tenkan'a geri çekilme
  2. 50SMA Bounce     → Yükselen 50SMA'ya geri çekilme + hacim
  3. Dar Konsolidasyon Kırılımı → 5+ gün dar bant, sonra yukarı kırılım
  4. Pre-market Gap Up → Haber + gap + hacim
  5. Kijun Bounce (geliştirilmiş) → %3 mesafeye kadar genişletildi
  6. RS Kopuşu        → Sektörünü 2 haftadır geçen hisse yeni ATH kırıyor

Çıkış kuralları (K-11 entegrasyonu):
  - Chandelier exit (3x ATR trailing)
  - K-11 kısmi kâr: RSI 70+ + %15 kâr → %25-30 sat
  - Hedef: R:R min 2:1, max 15 gün tutma
"""

# --- olay kaydı ---
import os
import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / 'scripts'))
try:
    from event_logger import log as _log
    _log.kaynak = 'swing_entry'
except ImportError:
    class _FB:
        kaynak='swing_entry'
        def __getattr__(self, n): return lambda *a, **kw: None
    _log = _FB()
# --- /olay kaydı ---

import requests
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

FMP_KEY  = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"

REPO_ROOT = Path(__file__).parent.parent


def fmp_get(endpoint: str, params: dict = None, timeout: int = 12):
    p = (params or {})
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"  ⚠ FMP hatası ({endpoint}): {e}")
        return None


def get_price_history(symbol: str, limit: int = 60) -> list:
    """OHLCV verisi — eskiden yeniye sıralı."""
    data = fmp_get(f"historical-price-eod/full", {"symbol": symbol, "limit": limit})
    if isinstance(data, list):
        return list(reversed(data))  # eskiden yeniye
    return []


# ── ENTRY SİNYALLERİ ─────────────────────────────────────────────────────────

def detect_tenkan_bounce(prices: list, ichi: dict) -> dict | None:
    """
    Tenkan Bounce — güçlü trend içinde en sık karşılaşılan giriş.
    
    Koşul:
    - Fiyat kumo üstünde (4/4 bullish)
    - Son 3 günde fiyat tenkan'a %2 içine geriledi
    - Bugün tenkan üstünde kapandı + dünden yüksek
    - Hacim ortalamanın üstünde
    """
    if not ichi or len(prices) < 5:
        return None

    price   = ichi.get("price", 0)
    tenkan  = ichi.get("tenkan", 0)
    kijun   = ichi.get("kijun", 0)
    kumo_top = ichi.get("kumo_top", 0)

    if not all([price, tenkan, kijun, kumo_top]):
        return None

    # 4/4 bullish kontrolü
    if price <= kumo_top or tenkan <= kijun:
        return None

    # Son 3 günde tenkan'a yaklaşım kontrolü
    last3 = prices[-4:-1]  # son 3 gün (dün dahil)
    tenkan_touches = [
        d for d in last3
        if abs(d["low"] - tenkan) / tenkan < 0.025  # %2.5 içinde
        or abs(d["close"] - tenkan) / tenkan < 0.020
    ]

    if not tenkan_touches:
        return None

    # Bugün kapanış tenkan üstünde ve dünden yüksek
    today = prices[-1]
    prev  = prices[-2] if len(prices) >= 2 else today

    if today["close"] <= tenkan or today["close"] <= prev["close"]:
        return None

    # Hacim kontrolü
    avg_vol = sum(d["volume"] for d in prices[-20:]) / 20 if len(prices) >= 20 else 0
    vol_ok  = today["volume"] >= avg_vol * 0.8

    return {
        "tip":       "tenkan_bounce",
        "guc":       "yuksek" if vol_ok else "orta",
        "aciklama":  f"Tenkan bounce (${tenkan:.2f}) → güçlü trend içi giriş noktası",
        "konum":     "kumo_ustu",
        "hacim_teyit": vol_ok,
    }


def detect_sma50_bounce(prices: list, ichi: dict) -> dict | None:
    """
    50SMA Bounce — trend sürmekte, SMA50'ye geri çekilme.
    
    ATLAS bulgusu: Yükselen 50SMA'ya geri çekilmeler en yüksek
    başarı oranına sahip swing setup'larından biri.
    """
    if len(prices) < 55:
        return None

    price    = ichi.get("price", 0)
    kumo_top = ichi.get("kumo_top", 0)

    # SMA50 hesapla
    closes = [d["close"] for d in prices]
    sma50  = sum(closes[-50:]) / 50
    sma50_prev = sum(closes[-51:-1]) / 50

    # SMA50 yükseliyor mu?
    if sma50 <= sma50_prev:
        return None

    # Fiyat SMA50'ye dokundu mu son 3 günde?
    last3 = prices[-4:-1]
    touches = [
        d for d in last3
        if abs(d["low"] - sma50) / sma50 < 0.015  # %1.5 içinde
        or (d["low"] <= sma50 <= d["high"])
    ]

    if not touches:
        return None

    # Fiyat SMA50 üstünde ve kumo üstünde
    if price <= sma50 or price <= kumo_top:
        return None

    today = prices[-1]
    prev  = prices[-2]

    # Bugün yükseliş
    if today["close"] <= prev["close"]:
        return None

    avg_vol = sum(d["volume"] for d in prices[-20:]) / 20
    vol_ok  = today["volume"] >= avg_vol

    return {
        "tip":       "sma50_bounce",
        "guc":       "yuksek",
        "aciklama":  f"50SMA bounce (${sma50:.2f}) → yükselen trend içi destek",
        "konum":     "kumo_ustu",
        "hacim_teyit": vol_ok,
        "sma50":     round(sma50, 2),
    }


def detect_consolidation_breakout(prices: list, ichi: dict) -> dict | None:
    """
    Dar Konsolidasyon Kırılımı (Flat Base / NR7 konsepti).
    
    Koşul:
    - 5-15 gün dar bant (günlük hareket < ATR × 0.7)
    - Bugün yukarı kırılım + hacim spike
    - Fiyat kumo üstünde
    
    Araştırma: O'Neil'ın "flat base" formasyonu — en güvenilir breakout setup.
    """
    if len(prices) < 20:
        return None

    price    = ichi.get("price", 0)
    kumo_top = ichi.get("kumo_top", 0)

    if price <= kumo_top:
        return None

    # ATR hesapla
    recent = prices[-15:]
    atrs   = [
        max(d["high"] - d["low"],
            abs(d["high"] - prices[i-1]["close"]),
            abs(d["low"]  - prices[i-1]["close"]))
        for i, d in enumerate(recent[1:], 1)
    ]
    atr = sum(atrs) / len(atrs) if atrs else 0

    if atr == 0:
        return None

    # 5-10 günlük konsolidasyon tespit et
    cons_window = prices[-11:-1]  # son 10 gün (bugün hariç)
    if len(cons_window) < 5:
        return None

    highs  = [d["high"] for d in cons_window]
    lows   = [d["low"] for d in cons_window]
    band   = max(highs) - min(lows)
    band_ratio = band / (prices[-11]["close"] or 1)  # bant / fiyat

    # Dar bant: fiyatın %6'sından az
    if band_ratio > 0.06:
        return None

    # Bugün kırılım: dünkü yüksek'i geçti + kapanış güçlü
    today     = prices[-1]
    prev_high = max(d["high"] for d in cons_window)
    avg_vol   = sum(d["volume"] for d in prices[-20:]) / 20

    if today["close"] <= prev_high * 1.005:  # kırılım eşiği
        return None

    vol_spike = today["volume"] >= avg_vol * 1.5  # %50 hacim artışı

    return {
        "tip":       "konsolidasyon_kirilim",
        "guc":       "cok_yuksek" if vol_spike else "yuksek",
        "aciklama":  f"Dar konsolidasyon kırılımı (bant %{band_ratio*100:.1f}, {len(cons_window)}g)",
        "konum":     "kumo_ustu",
        "hacim_teyit": vol_spike,
        "onceki_direnc": round(prev_high, 2),
    }


def detect_kijun_bounce_v2(prices: list, ichi: dict) -> dict | None:
    """
    Kijun Bounce v2 — mesafe eşiği %1'den %3'e genişletildi.
    Mevcut sistemde %1 çok sıkı, gerçek bounce'ları kaçırıyor.
    """
    if not ichi:
        return None

    price    = ichi.get("price", 0)
    tenkan   = ichi.get("tenkan", 0)
    kijun    = ichi.get("kijun", 0)
    kumo_top = ichi.get("kumo_top", 0)

    if price <= kumo_top or tenkan <= kijun:
        return None

    # Son 3 günde kijun'a %3 içinde yaklaşım
    last3 = prices[-4:-1]
    touches = [
        d for d in last3
        if abs(d["low"] - kijun) / kijun < 0.03
        or (d["low"] <= kijun * 1.02 and d["close"] > kijun)
    ]

    if not touches:
        return None

    today = prices[-1]
    if today["close"] <= kijun or today["close"] <= prices[-2]["close"]:
        return None

    avg_vol = sum(d["volume"] for d in prices[-20:]) / 20
    vol_ok  = today["volume"] >= avg_vol * 0.8

    return {
        "tip":       "kijun_bounce_v2",
        "guc":       "yuksek" if vol_ok else "orta",
        "aciklama":  f"Kijun bounce v2 (${kijun:.2f}) → %3 mesafe toleransı",
        "konum":     "kumo_ustu",
        "hacim_teyit": vol_ok,
    }


def detect_nr7_setup(prices: list, ichi: dict) -> dict | None:
    """
    NR7 (Narrowest Range 7) — O'Neil'ın klasik volatilite sıkışması.
    Bugünkü gün aralığı son 7 günün en dardı → patlama yaklaşıyor.
    """
    if len(prices) < 9:
        return None

    price    = ichi.get("price", 0)
    kumo_top = ichi.get("kumo_top", 0)

    if price <= kumo_top:
        return None

    today   = prices[-1]
    last7   = prices[-8:-1]
    ranges7 = [d["high"] - d["low"] for d in last7]
    today_range = today["high"] - today["low"]

    if not ranges7 or today_range >= min(ranges7):
        return None  # NR7 değil

    # Trend yukarı olmalı
    closes_5 = [d["close"] for d in prices[-6:]]
    trend_up  = closes_5[-1] > closes_5[0]

    if not trend_up:
        return None

    return {
        "tip":       "nr7_sikisma",
        "guc":       "orta",
        "aciklama":  f"NR7 volatilite sıkışması → patlama potansiyeli (aralık: ${today_range:.2f})",
        "konum":     "kumo_ustu",
        "hacim_teyit": False,
    }


# ── TAM ANALİZ ────────────────────────────────────────────────────────────────

def enhanced_entry_analysis(symbol: str) -> dict:
    """
    Gelişmiş swing giriş analizi.
    Mevcut swing_ichimoku'ya ek 4 sinyal.
    """
    # Fiyat verisi
    prices = get_price_history(symbol, limit=60)
    if len(prices) < 30:
        return {"symbol": symbol, "error": "yetersiz veri"}

    today  = prices[-1]
    price  = today["close"]

    # Ichimoku hesapla (mevcut fonksiyonu çağır)
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from swing_ichimoku import calc_ichimoku, calc_atr, determine_position
        ichi     = calc_ichimoku(prices)
        atr      = calc_atr(prices)
        position = determine_position(ichi)
    except Exception as e:
        return {"symbol": symbol, "error": f"ichimoku hatası: {e}"}

    # Mevcut + yeni giriş sinyalleri
    signals = []

    # Yeni sinyaller
    for detector in [
        detect_tenkan_bounce,
        detect_sma50_bounce,
        detect_consolidation_breakout,
        detect_kijun_bounce_v2,
        detect_nr7_setup,
    ]:
        sig = detector(prices, ichi)
        if sig:
            signals.append(sig)

    # Stop ve hedef
    kijun     = ichi.get("kijun", 0)
    tenkan    = ichi.get("tenkan", 0)
    stop_lvl  = kijun if kijun else price * 0.93
    stop_dist = (price - stop_lvl) / price * 100
    target    = price + (price - stop_lvl) * 2.5  # R:R 2.5:1

    # Pozisyon boyutu ($5K standart — K-14 kaldırıldı, restart konsepti yok)
    account   = 5000
    risk_per  = account * 0.05  # %5 risk
    shares    = int(risk_per / (price - stop_lvl)) if price > stop_lvl else 0

    # RSI hesapla
    closes  = [d["close"] for d in prices]
    rsi     = _calc_rsi(closes)

    # Ichimoku pozisyon gücü
    pos_str = position.get("genel", "") if isinstance(position, dict) else ""
    is_4_4  = "4/4" in pos_str or "guclu" in pos_str.lower()

    # Karar
    if not signals:
        karar = "BEKLE — sinyal yok"
        sinyal_str = "Giriş sinyali beklenıyor"
    elif not is_4_4:
        karar = "BEKLE — 4/4 değil"
        sinyal_str = f"{len(signals)} sinyal var ama Ichimoku gücü yetersiz"
    elif stop_dist < 3:
        karar = "BEKLE — stop çok yakın (whipsaw riski)"
        sinyal_str = f"{len(signals)} sinyal, stop:%{stop_dist:.1f} dar"
    elif stop_dist > 12:
        karar = "BEKLE — stop çok uzak (risk yüksek)"
        sinyal_str = f"{len(signals)} sinyal, stop:%{stop_dist:.1f} geniş"
    else:
        en_guclu = max(signals, key=lambda s: {"cok_yuksek": 4, "yuksek": 3, "orta": 2}.get(s["guc"], 1))
        karar    = f"GİRİŞ ✅ ({en_guclu['tip']})"
        sinyal_str = " | ".join(s["tip"] for s in signals)

    # Güçlü sinyal varsa logla
    if signals and karar in ("GİR", "GÜÇLÜ_GİR"):
        _log.basarili(
            f"Swing sinyal: {symbol}",
            f"Karar: {karar} | Sinyaller: {sinyal_str}\n"
            f"Giriş: ${price:.2f} | Stop: ${stop_lvl:.2f} | R:R 2.5:1 | RSI: {round(rsi,1) if rsi else '?'}",
            kaynak="swing_entry"
        )

    return {
        "symbol":      symbol,
        "price":       round(price, 2),
        "karar":       karar,
        "sinyaller":   signals,
        "sinyal_str":  sinyal_str,
        "is_4_4":      is_4_4,
        "stop":        round(stop_lvl, 2),
        "stop_dist":   round(stop_dist, 1),
        "target":      round(target, 2),
        "rr_ratio":    2.5,
        "atr":         round(atr, 2),
        "shares":      shares,
        "rsi":         round(rsi, 1) if rsi else None,
        "position":    pos_str,
    }


def _calc_rsi(closes: list, period: int = 14) -> float | None:
    if len(closes) < period + 2:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(abs(min(d, 0)))
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))


# ── TOPLU TARAMA ─────────────────────────────────────────────────────────────

def scan_for_entries(symbols: list[str], verbose: bool = False) -> list[dict]:
    """
    Sembol listesini tarar, giriş sinyali olanları döner.
    """
    print(f"\n[SwingEntry] {len(symbols)} hisse taranıyor...")
    results   = []
    giris_var = []

    for i, sym in enumerate(symbols, 1):
        print(f"  [{i:2}/{len(symbols)}] {sym}...", end=" ", flush=True)
        result = enhanced_entry_analysis(sym)

        if "GİRİŞ" in result.get("karar", ""):
            giris_var.append(result)
            print(f"✅ {result['karar']}")
        elif verbose:
            print(f"— {result.get('karar', '?')[:50]}")
        else:
            print("—")

        results.append(result)

    print(f"\n[SwingEntry] Sonuç: {len(giris_var)}/{len(symbols)} giriş sinyali")
    return results, giris_var


def print_entry_report(giris_var: list[dict]):
    """Giriş sinyali olanları raporla."""
    if not giris_var:
        print("\nGiriş sinyali yok.")
        return

    print(f"\n{'='*70}")
    print(f"GİRİŞ SİNYALLERİ ({len(giris_var)} hisse)")
    print(f"{'='*70}")
    print(f"{'SYM':6} {'Fiyat':>7} {'Stop':>7} {'Stop%':>6} {'Hedef':>7} {'RSI':>4} Sinyal")
    print("-" * 70)

    for r in sorted(giris_var, key=lambda x: -len(x.get("sinyaller", []))):
        sym   = r["symbol"]
        price = r["price"]
        stop  = r["stop"]
        sdist = r["stop_dist"]
        tgt   = r["target"]
        rsi   = r.get("rsi") or 0
        sigs  = ", ".join(s["tip"] for s in r.get("sinyaller", []))
        print(f"{sym:6} ${price:7.2f} ${stop:7.2f} {sdist:5.1f}% ${tgt:7.2f} {rsi:4.0f} {sigs}")
        print(f"       Adet: {r['shares']} | ATR: ${r['atr']:.2f} | {r.get('karar','')}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Swing Entry Engine v2.0")
    parser.add_argument("symbols", nargs="?", default="",
                        help="Virgülle ayrılmış semboller veya --watchlist")
    parser.add_argument("--watchlist", action="store_true",
                        help="Watchlist'i tara")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.watchlist:
        wl   = json.load(open(REPO_ROOT / "data" / "watchlist.json"))
        syms = [h.get("sembol") for h in wl.get("izleme_listesi", []) if h.get("sembol")]
    elif args.symbols:
        syms = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        # Alpha screener EKLE listesinden al
        scan = json.load(open(REPO_ROOT / "data" / "alpha_scan_growth.json"))
        syms = [h["symbol"] for h in scan.get("ekle", []) + scan.get("izle", [])][:20]
        print(f"Alpha screener'dan {len(syms)} hisse alındı")

    # ── Kapasite kontrolü (max 8 pozisyon) ──────────────────────
    try:
        active = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
        current = len(active.get("aktif_pozisyonlar", []))
        MAX_SWING = 8
        bos_slot  = MAX_SWING - current
        print(f"\n[Kapasite] {current}/{MAX_SWING} pozisyon aktif — {bos_slot} boş slot")
        if bos_slot <= 0:
            print("⛔ Kapasite DOLU — yeni giriş yapılamaz. Çıkış bekleyip tekrar çalıştırın.")
            raise SystemExit(0)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        print("⚠️  Kapasite kontrolü atlandı (active.json okunamadı)")

    all_results, giris = scan_for_entries(syms, verbose=args.verbose)
    print_entry_report(giris)
