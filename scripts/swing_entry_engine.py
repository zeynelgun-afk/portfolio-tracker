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

# ── KALITE FILTRELERI (28 Nis 2026 reform) ───────────────────────────────────
def check_volume_strength(prices: list) -> dict:
    """
    Hacim doğrulaması: Bugünkü hacim son 20 gun ortalamasinin uzerinde mi?
    Kuvvetli sinyal icin hacim teyidi sart.
    
    Backtest dersi: Zayif hacimli oversold_bounce sinyalleri 20g sonra -%6.
    Hacim teyidi olmadan sinyal yarim guclu.
    """
    if len(prices) < 21:
        return {"gucu": 1.0, "ortalama_uzeri": False, "rasyo": 0.0}
    
    bugun_hacim = prices[-1].get("volume", 0) or 0
    son20 = prices[-21:-1]
    ort20 = sum(p.get("volume", 0) or 0 for p in son20) / 20 if son20 else 0
    
    if not ort20:
        return {"gucu": 1.0, "ortalama_uzeri": False, "rasyo": 0.0}
    
    rasyo = bugun_hacim / ort20
    
    # Hacim çarpani: <0.7 zayif, 0.7-1.0 orta, 1.0-1.5 iyi, >1.5 mukemmel
    if rasyo >= 1.5:
        gucu = 1.5  # Bonus
    elif rasyo >= 1.0:
        gucu = 1.2
    elif rasyo >= 0.7:
        gucu = 1.0
    else:
        gucu = 0.7  # Zayif hacim ceza
    
    return {
        "gucu": gucu,
        "ortalama_uzeri": rasyo >= 1.0,
        "rasyo": round(rasyo, 2),
    }


def check_sector_strength(symbol: str) -> dict:
    """
    Sektörün SPY'a karşı gücü — symbol'ün sektör ETF'si SPY'ı geçiyor mu?
    Backtest dersi: Zayif sektörlerden swing alımları 20g sonra -%11.
    
    FMP profile'dan sektör al, sonra ETF map ile SPY karşılaştır (10g performance).
    """
    SEKTOR_ETF_MAP = {
        "Technology": "XLK", "Healthcare": "XLV", "Financial Services": "XLF",
        "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
        "Industrials": "XLI", "Energy": "XLE", "Communication Services": "XLC",
        "Utilities": "XLU", "Real Estate": "XLRE", "Basic Materials": "XLB",
    }
    
    try:
        # Profile'dan sektör
        prof = fmp_get("profile", {"symbol": symbol})
        if not isinstance(prof, list) or not prof:
            return {"gucu": 1.0, "outperform": None}
        sektor = prof[0].get("sector", "")
        etf = SEKTOR_ETF_MAP.get(sektor)
        if not etf:
            return {"gucu": 1.0, "outperform": None}
        
        # Hem sektör ETF hem SPY için son 10 gün performans
        etf_h = fmp_get("historical-price-eod/full", {"symbol": etf, "limit": 12})
        spy_h = fmp_get("historical-price-eod/full", {"symbol": "SPY", "limit": 12})
        
        if not (isinstance(etf_h, list) and isinstance(spy_h, list)):
            return {"gucu": 1.0, "outperform": None}
        if len(etf_h) < 11 or len(spy_h) < 11:
            return {"gucu": 1.0, "outperform": None}
        
        # FMP yeni→eski sıralı, son 10g getiri
        etf_perf = (etf_h[0]["close"] - etf_h[10]["close"]) / etf_h[10]["close"] * 100
        spy_perf = (spy_h[0]["close"] - spy_h[10]["close"]) / spy_h[10]["close"] * 100
        
        diff = etf_perf - spy_perf
        outperform = diff > 0
        
        # Çarpan: outperform varsa bonus, underperform ceza
        if diff > 2:
            gucu = 1.3
        elif diff > 0:
            gucu = 1.1
        elif diff > -2:
            gucu = 0.9
        else:
            gucu = 0.7
        
        return {
            "gucu": gucu,
            "outperform": outperform,
            "sektor_perf": round(etf_perf, 2),
            "spy_perf": round(spy_perf, 2),
            "fark": round(diff, 2),
            "etf": etf,
            "sektor": sektor,
        }
    except Exception:
        return {"gucu": 1.0, "outperform": None}


def check_market_regime() -> dict:
    """
    Piyasa rejimi: SPY 21EMA üstünde + yükseliş eğiminde mi?
    Memory: 'SPY above 21EMA + upward slope' swing kuralı.
    """
    try:
        h = fmp_get("historical-price-eod/full", {"symbol": "SPY", "limit": 30})
        if not isinstance(h, list) or len(h) < 22:
            return {"gucu": 1.0, "rejim": "bilinmiyor"}
        
        # 21EMA hesapla (FMP yeni→eski)
        h_asc = list(reversed(h[:25]))
        closes = [c["close"] for c in h_asc]
        # EMA(21) approximation: SMA(21)
        sma21 = sum(closes[-21:]) / 21
        bugun = closes[-1]
        dun = closes[-2]
        
        ustunde = bugun > sma21
        yukseliyor = bugun > dun
        
        if ustunde and yukseliyor:
            rejim = "risk-on"
            gucu = 1.2
        elif ustunde and not yukseliyor:
            rejim = "risk-on-zayif"
            gucu = 1.0
        elif not ustunde and yukseliyor:
            rejim = "risk-off-toparlanma"
            gucu = 0.8
        else:
            rejim = "risk-off"
            gucu = 0.6
        
        return {
            "gucu": gucu,
            "rejim": rejim,
            "spy_fiyat": round(bugun, 2),
            "spy_sma21": round(sma21, 2),
            "ustunde": ustunde,
        }
    except Exception:
        return {"gucu": 1.0, "rejim": "bilinmiyor"}


def calculate_kalite_skoru(signals: list, position: dict, volume: dict, 
                            sektor: dict, regime: dict, atr: float, price: float) -> dict:
    """
    Composite kalite skoru (0-100): Bir sinyalin ne kadar kuvvetli oldugunu
    tek bir sayida toplar.
    
    Bilesenler:
    - Sinyal sayisi ve turu (40 puan)
    - Ichimoku konum (4/4 → 20 puan)
    - Hacim teyidi (15 puan)
    - Sektor gucu (15 puan)
    - Piyasa rejimi (10 puan)
    
    Skor 70+ → guclu giris (2.0x convicted bet)
    Skor 55-70 → orta (1.5x)
    Skor 40-55 → zayif (1.0x)
    Skor <40 → giris yapma (0x)
    """
    skor = 0
    detay = {}
    
    # 1. Sinyal sayisi + turu (40 puan)
    if signals:
        sinyal_tipleri = [s.get("tip", "") for s in signals]
        # En guclu sinyal tipine göre
        if any(t in ("tenkan_bounce", "ichimoku", "kumo_kirilim") for t in sinyal_tipleri):
            sinyal_skor = 25  # Backtest +%8 sinyaller
        elif any(t == "consolidation_breakout" for t in sinyal_tipleri):
            sinyal_skor = 20
        elif any(t in ("sma50_bounce", "kijun_bounce_v2", "nr7_sikisma") for t in sinyal_tipleri):
            sinyal_skor = 15
        elif "oversold_bounce" in sinyal_tipleri:
            sinyal_skor = 8  # Backtest -%6, dusuk skor
        else:
            sinyal_skor = 10
        # Multi-sinyal bonus
        if len(sinyal_tipleri) >= 3:
            sinyal_skor += 15
        elif len(sinyal_tipleri) == 2:
            sinyal_skor += 8
        skor += min(sinyal_skor, 40)
        detay["sinyal"] = min(sinyal_skor, 40)
    else:
        detay["sinyal"] = 0
    
    # 2. Ichimoku konum (20 puan)
    pos_str = position.get("genel", "") if isinstance(position, dict) else ""
    if "4/4" in pos_str:
        skor += 20
        detay["ichimoku"] = 20
    elif "3/4" in pos_str:
        skor += 12
        detay["ichimoku"] = 12
    elif "2/4" in pos_str:
        skor += 5
        detay["ichimoku"] = 5
    else:
        detay["ichimoku"] = 0
    
    # 3. Hacim teyidi (15 puan)
    rasyo = volume.get("rasyo", 0)
    if rasyo >= 1.5:
        h_skor = 15
    elif rasyo >= 1.0:
        h_skor = 10
    elif rasyo >= 0.7:
        h_skor = 5
    else:
        h_skor = 0
    skor += h_skor
    detay["hacim"] = h_skor
    
    # 4. Sektor gucu (15 puan)
    sektor_diff = sektor.get("fark", 0) or 0
    if sektor_diff > 2:
        s_skor = 15
    elif sektor_diff > 0:
        s_skor = 10
    elif sektor_diff > -2:
        s_skor = 5
    else:
        s_skor = 0
    skor += s_skor
    detay["sektor"] = s_skor
    
    # 5. Piyasa rejimi (10 puan)
    rejim = regime.get("rejim", "bilinmiyor")
    if rejim == "risk-on":
        r_skor = 10
    elif rejim == "risk-on-zayif":
        r_skor = 7
    elif rejim == "risk-off-toparlanma":
        r_skor = 4
    else:
        r_skor = 0
    skor += r_skor
    detay["rejim"] = r_skor
    
    # Karar
    if skor >= 70:
        karar = "GUCLU"
        carpan_oneri = 2.0
    elif skor >= 55:
        karar = "ORTA"
        carpan_oneri = 1.5
    elif skor >= 40:
        karar = "ZAYIF"
        carpan_oneri = 1.0
    else:
        karar = "GECERSIZ"
        carpan_oneri = 0  # Giris yapma
    
    return {
        "skor": skor,
        "karar": karar,
        "carpan_oneri": carpan_oneri,
        "detay": detay,
    }


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

    # ── KALITE FILTRELERI (28 Nis 2026 reform) ─────────────────────────────
    # Volume + Sektor gucu + Piyasa rejimi
    volume_check = check_volume_strength(prices)
    sektor_check = check_sector_strength(symbol)
    regime_check = check_market_regime()
    kalite = calculate_kalite_skoru(signals, position, volume_check, 
                                      sektor_check, regime_check, 0, price)

    # Stop ve hedef
    kijun     = ichi.get("kijun", 0)
    tenkan    = ichi.get("tenkan", 0)
    stop_lvl  = kijun if kijun else price * 0.93
    stop_dist = (price - stop_lvl) / price * 100
    target    = price + (price - stop_lvl) * 2.5  # R:R 2.5:1

    # ── DRUCKENMILLER CONVICTED BET (28 Nis 2026 — backtest dersine dayali)
    # Sinyal turune gore pozisyon boyutu carpani:
    #   tenkan_bounce  → 1.5x (backtest +%8.23 / 10g — kuvvetli)
    #   ichimoku       → 1.5x (backtest +%7.90 / 10g — kuvvetli)
    #   sma50_bounce   → 1.0x (tek ornek, daha fazla veri lazim)
    #   nr7_sikisma    → 1.0x (volatilite kirilim)
    #   kijun_bounce_v2 → 1.0x (orta)
    #   oversold_bounce → 0.5x (backtest -%6.28 / 20g — zayif)
    #
    # Ayrica multi-sinyal varsa carpan toplaniyor (max 2.5x):
    #   2 kuvvetli sinyal (orn tenkan + ichimoku) = 2.0x
    #   3+ sinyal = max 2.5x
    KUVVET_KATSAYI = {
        "tenkan_bounce":   1.5,
        "ichimoku":        1.5,
        "kumo_kirilim":    1.5,
        "sma50_bounce":    1.0,
        "nr7_sikisma":     1.0,
        "kijun_bounce_v2": 1.0,
        "oversold_bounce": 0.5,
        "consolidation_breakout": 1.2,
    }
    sinyal_tipleri = [s.get("tip", "") for s in signals] if signals else []
    if not sinyal_tipleri:
        carpan = 1.0
    else:
        # En yuksek skorlu sinyali al + ek sinyal varsa bonus
        max_carpan = max((KUVVET_KATSAYI.get(t, 1.0) for t in sinyal_tipleri), default=1.0)
        ek_sinyal = max(0, len(sinyal_tipleri) - 1)
        carpan = min(2.5, max_carpan + (ek_sinyal * 0.25))
    
    # 4/4 ichimoku konumu varsa +0.25 bonus (memory: ichimoku 4/4 mandatory)
    pos_str_for_bonus = position.get("genel", "") if isinstance(position, dict) else ""
    if "4/4" in pos_str_for_bonus:
        carpan = min(2.5, carpan + 0.25)
    
    # ── KALITE FILTRESI: composite skoru carpana entegre et
    # Skor 70+ (GUCLU) → 2x carpan onerilir → mevcut carpan korunur veya artar
    # Skor 55-70 (ORTA) → 1.5x onerilir → mevcut carpan max 1.5'a sinirlanir
    # Skor 40-55 (ZAYIF) → 1.0x onerilir → mevcut carpan max 1.0'e sinirlanir
    # Skor <40 (GECERSIZ) → carpan = 0, GIRIS YAPMA
    kalite_skor = kalite.get("skor", 0)
    kalite_karar = kalite.get("karar", "GECERSIZ")
    if kalite_karar == "GECERSIZ":
        carpan = 0
    elif kalite_karar == "ZAYIF":
        carpan = min(carpan, 1.0)
    elif kalite_karar == "ORTA":
        carpan = min(carpan, 1.7)
    # GUCLU ise mevcut carpan korunur (zaten 2x'e yaklasik)

    # Pozisyon boyutu — convicted bet
    base_account = 5000  # baz
    account = int(base_account * carpan)
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
    elif kalite_karar == "GECERSIZ":
        # Yeni filtre (28 Nis 2026): Düşük kalite skoru = giriş yok
        karar = f"BEKLE — kalite skoru düşük ({kalite_skor}/100)"
        sinyal_str = f"{len(signals)} sinyal var ama kalite filtresi geçemedi"
    else:
        en_guclu = max(signals, key=lambda s: {"cok_yuksek": 4, "yuksek": 3, "orta": 2}.get(s["guc"], 1))
        # Kalite kararına göre etiket güncelle
        kalite_etiket = ""
        if kalite_karar == "GUCLU":
            kalite_etiket = " ⭐"
        elif kalite_karar == "ZAYIF":
            kalite_etiket = " ⚠️"
        karar    = f"GİRİŞ ✅ ({en_guclu['tip']}){kalite_etiket} skor:{kalite_skor}"
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
        "carpan":      round(carpan, 2),       # Druckenmiller convicted bet
        "account_size": account,                # base*carpan
        "kalite_skor": kalite_skor,             # Composite 0-100
        "kalite_karar": kalite_karar,           # GUCLU/ORTA/ZAYIF/GECERSIZ
        "kalite_detay": kalite.get("detay", {}),
        "volume_rasyo": volume_check.get("rasyo"),
        "sektor_fark": sektor_check.get("fark"),
        "rejim": regime_check.get("rejim"),
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

def _detect_crisis_rally(verbose: bool = False) -> tuple[bool, str]:
    """
    K-21 Kriz Rallisi Yasağı (28 Nis 2026 backtest dersi)
    ====================================================
    Backtest 17 swing girişten 4'ünün 'kriz rallisi' kategorisinde olduğunu
    gösterdi (HAL/KTOS/CEG, 2 Mart 2026 Iran krizi). Bu 4 alımın 20 gün
    sonraki ortalama getirisi -%4.87, KTOS tek başına -%32.3.

    Kural: Son 5 işgününde VIX %20'den fazla sıçradıysa o gün swing
    girişi yapma. T+1 ve sonrası RSI<35 + ichimoku 3/4 ile devam.

    Dön: (yasak_mı, açıklama)
    """
    try:
        # VIX son 5 günü çek
        d = fmp_get("historical-price-eod/full",
                    {"symbol": "^VIX", "limit": 6})
        if not isinstance(d, list) or len(d) < 5:
            return False, "VIX verisi yok, kontrol atlandı"

        # FMP yeni→eski sıralı
        d_asc = sorted(d, key=lambda x: x.get("date", ""))
        son5 = d_asc[-6:-1]  # son 5 işgünü (bugün hariç)
        if len(son5) < 5:
            return False, "Yetersiz VIX verisi"

        vix_5g_min = min(p.get("low") or p.get("close", 999) for p in son5)
        vix_bugun = d_asc[-1].get("close", 0)
        if vix_5g_min and vix_bugun:
            sicrama_pct = (vix_bugun - vix_5g_min) / vix_5g_min * 100
            if verbose:
                print(f"  VIX 5g min: {vix_5g_min:.2f} | bugün: {vix_bugun:.2f} | sıçrama: {sicrama_pct:+.1f}%")
            if sicrama_pct >= 20:
                return True, f"VIX 5g'de %{sicrama_pct:.0f} sıçradı ({vix_5g_min:.1f}→{vix_bugun:.1f})"
        return False, "VIX normal"
    except Exception as e:
        return False, f"Kontrol hatası: {e}"


def scan_for_entries(symbols: list[str], verbose: bool = False) -> list[dict]:
    """
    Sembol listesini tarar, giriş sinyali olanları döner.
    """
    # K-21 Kriz Rallisi kontrolü (28 Nis 2026)
    kriz_var, kriz_aciklama = _detect_crisis_rally(verbose)
    if kriz_var:
        print(f"\n[SwingEntry] ⛔ K-21 KRİZ RALLİSİ TESPİT EDİLDİ")
        print(f"  {kriz_aciklama}")
        print(f"  Bugün swing girişi YAPILMAZ. Yarın RSI<35 + ichimoku 3/4 ile tekrar dene.")
        try:
            _log.olay("k21_crisis_rally_blok",
                      {"aciklama": kriz_aciklama, "blok_edildi": True},
                      severity="warning")
        except Exception:
            pass
        return [], []

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

    for r in sorted(giris_var, key=lambda x: -x.get("kalite_skor", 0)):
        sym   = r["symbol"]
        price = r["price"]
        stop  = r["stop"]
        sdist = r["stop_dist"]
        tgt   = r["target"]
        rsi   = r.get("rsi") or 0
        sigs  = ", ".join(s["tip"] for s in r.get("sinyaller", []))
        skor  = r.get("kalite_skor", 0)
        karar_kalite = r.get("kalite_karar", "?")
        carpan = r.get("carpan", 1.0)
        print(f"{sym:6} ${price:7.2f} ${stop:7.2f} {sdist:5.1f}% ${tgt:7.2f} {rsi:4.0f} {sigs}")
        print(f"       Adet: {r['shares']} | ATR: ${r['atr']:.2f} | KALITE: {skor}/100 ({karar_kalite}) | CARPAN: {carpan:.2f}x | {r.get('karar','')}")
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
