#!/usr/bin/env python3
"""
Finzora AI - Swing Trade Sistemi v2.0
Ichimoku + Hacim + ATR

Kullanım:
  python scripts/swing_ichimoku.py NEM,AROC        # aday tarama
  python scripts/swing_ichimoku.py --aktif          # aktif pozisyon güncelleme
  python scripts/swing_ichimoku.py --watchlist      # watchlist tarama
  python scripts/swing_ichimoku.py NEM --detay      # tek hisse detaylı analiz
"""

# --- olay kaydı ---
import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / 'scripts'))
try:
    from event_logger import log as _log
    _log.kaynak = 'swing_ichimoku'
except ImportError:
    class _FB:
        kaynak='swing_ichimoku'
        def __getattr__(self, n): return lambda *a, **kw: None
    _log = _FB()
# --- /olay kaydı ---

import requests
import json
import argparse
import os
import sys
from datetime import datetime, timedelta

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 10 May 2026 — canonical fmp_client'a migrasyon (None preservation wrapper)
import sys as _sys_fmp
from pathlib import Path as _Path_fmp

_AGENT_DIR = _Path_fmp(__file__).resolve().parent.parent / "agent"
if str(_AGENT_DIR) not in _sys_fmp.path:
    _sys_fmp.path.insert(0, str(_AGENT_DIR))

try:
    from fmp_client import fmp_get as _canonical_fmp_get

    def fmp_get(endpoint, params=None):
        """fmp_client wrapper. Hata/boş veride None döner."""
        result = _canonical_fmp_get(endpoint, params)
        if isinstance(result, dict) and 'Error Message' in result:
            return None
        return result if result else None
except ImportError:
    def fmp_get(endpoint, params=None):
        if params is None:
            params = {}
        params['apikey'] = FMP_API_KEY
        try:
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and 'Error Message' in data:
                return None
            return data
        except:
            return None


# ============================================================
# 1. ICHIMOKU HESAPLAMA
# ============================================================

def calc_ichimoku(prices_sorted):
    """
    Tam ichimoku hesaplama. prices_sorted = eskiden yeniye sıralı OHLCV listesi.
    En az 60 gün veri gerekli (52 gün senkou B + buffer).
    """
    highs = [d['high'] for d in prices_sorted]
    lows = [d['low'] for d in prices_sorted]
    closes = [d['close'] for d in prices_sorted]
    n = len(prices_sorted)

    if n < 55:
        return None

    def period_hl(end_idx, period):
        start = max(0, end_idx - period + 1)
        return max(highs[start:end_idx+1]), min(lows[start:end_idx+1])

    i = n - 1  # son gün

    # tenkan-sen (9 günlük yüksek+düşük ortalaması)
    th, tl = period_hl(i, 9)
    tenkan = (th + tl) / 2

    # kijun-sen (26 günlük)
    kh, kl = period_hl(i, 26)
    kijun = (kh + kl) / 2

    # senkou span A (tenkan+kijun / 2, 26 gün ileriye yansıtılır ama biz şu anki için hesaplıyoruz)
    senkou_a = (tenkan + kijun) / 2

    # senkou span B (52 günlük yüksek+düşük / 2)
    sh, sl = period_hl(i, 52)
    senkou_b = (sh + sl) / 2

    kumo_top = max(senkou_a, senkou_b)
    kumo_bottom = min(senkou_a, senkou_b)
    kumo_kalinlik = kumo_top - kumo_bottom

    # chikou span (bugünkü kapanış vs 26 gün önceki kapanış)
    chikou_ref = closes[i - 26] if i >= 26 else None

    # dünkü değerler (sinyal tespiti için)
    i_prev = i - 1
    th_p, tl_p = period_hl(i_prev, 9)
    tenkan_prev = (th_p + tl_p) / 2
    kh_p, kl_p = period_hl(i_prev, 26)
    kijun_prev = (kh_p + kl_p) / 2

    sa_prev = (tenkan_prev + kijun_prev) / 2
    sh_p, sl_p = period_hl(i_prev, 52)
    sb_prev = (sh_p + sl_p) / 2
    kumo_top_prev = max(sa_prev, sb_prev)
    kumo_bottom_prev = min(sa_prev, sb_prev)

    price = closes[i]
    price_prev = closes[i_prev]

    # gelecek kumo (26 gün sonrası tahmini - trend yönü)
    # basitleştirilmiş: senkou A/B'nin yönüne bak
    kumo_renk = "yesil" if senkou_a > senkou_b else "kirmizi"

    return {
        "price": round(price, 2),
        "price_prev": round(price_prev, 2),
        "tenkan": round(tenkan, 2),
        "tenkan_prev": round(tenkan_prev, 2),
        "kijun": round(kijun, 2),
        "kijun_prev": round(kijun_prev, 2),
        "senkou_a": round(senkou_a, 2),
        "senkou_b": round(senkou_b, 2),
        "kumo_top": round(kumo_top, 2),
        "kumo_bottom": round(kumo_bottom, 2),
        "kumo_top_prev": round(kumo_top_prev, 2),
        "kumo_bottom_prev": round(kumo_bottom_prev, 2),
        "kumo_kalinlik": round(kumo_kalinlik, 2),
        "kumo_renk": kumo_renk,
        "chikou_ref": round(chikou_ref, 2) if chikou_ref else None,
    }


# ============================================================
# 2. GİRİŞ SİNYALİ TESPİTİ
# ============================================================

def detect_entry_signals(ichi):
    """Ichimoku giriş sinyallerini tespit et."""
    signals = []
    p = ichi

    # --- KUMO KIRILIMI ---
    # dün kumo içinde veya altındaydı, bugün kumo üstünde kapandı
    if p['price_prev'] <= p['kumo_top_prev'] and p['price'] > p['kumo_top']:
        loc = "kumo_ustu"
        signals.append({
            "tip": "kumo_kirilimi",
            "guc": "yuksek",
            "aciklama": f"fiyat kumo'yu yukarı kırdı (${p['price']:.2f} > kumo üst ${p['kumo_top']:.2f})",
            "konum": loc,
        })

    # --- TK CROSS kaldırıldı (v2.1) ---
    # tek başına anlamlı sinyal üretmiyordu, sahte sinyaller çoktu.
    # TK cross aşağı çıkış sinyali olarak korunuyor (detect_exit_signals).

    # --- KİJUN BOUNCE ---
    # fiyat kumo üzerinde, kijun'a dokundu ve sıçradı
    if (p['price'] > p['kumo_top'] and p['tenkan'] > p['kijun']):
        kijun_mesafe_prev = abs(p['price_prev'] - p['kijun_prev']) / p['kijun_prev'] * 100
        if kijun_mesafe_prev < 1.0 and p['price'] > p['kijun']:
            signals.append({
                "tip": "kijun_bounce",
                "guc": "orta",
                "aciklama": f"kijun'dan sekme (${p['kijun']:.2f} desteğinden dönüş)",
                "konum": "kumo_ustu",
            })

    return signals


# ============================================================
# 3. ÇIKIŞ SİNYALİ TESPİTİ
# ============================================================

def detect_exit_signals(ichi):
    """Ichimoku çıkış sinyallerini tespit et."""
    signals = []
    p = ichi

    # --- KİJUN ALTI KAPANIŞ ---
    if p['price'] < p['kijun']:
        fark_pct = (p['kijun'] - p['price']) / p['kijun'] * 100
        if fark_pct > 0.5:
            signals.append({
                "tip": "kijun_alti_kapanis",
                "acil": True,
                "aciklama": f"fiyat kijun altında kapandı (${p['price']:.2f} < kijun ${p['kijun']:.2f}, fark %{fark_pct:.1f})",
            })
        else:
            signals.append({
                "tip": "kijun_alti_yakin",
                "acil": False,
                "aciklama": f"fiyat kijun'a çok yakın kapandı (fark %{fark_pct:.1f}), yarın teyit bekle",
            })

    # --- TK CROSS AŞAĞI (bearish) ---
    if p['tenkan_prev'] >= p['kijun_prev'] and p['tenkan'] < p['kijun']:
        signals.append({
            "tip": "tk_cross_asagi",
            "acil": True,
            "aciklama": f"bearish TK cross: tenkan (${p['tenkan']:.2f}) < kijun (${p['kijun']:.2f})",
        })

    # --- KUMO'YA GİRİŞ ---
    if p['price_prev'] > p['kumo_top_prev'] and p['price'] <= p['kumo_top'] and p['price'] >= p['kumo_bottom']:
        signals.append({
            "tip": "kumo_girisi",
            "acil": False,
            "aciklama": f"fiyat kumo'ya girdi (${p['price']:.2f}, kumo: ${p['kumo_bottom']:.2f}-${p['kumo_top']:.2f}). kısmi çıkış düşün",
        })

    return signals


# ============================================================
# 4. DURUM BELİRLEME (pozisyon nerede?)
# ============================================================

def determine_position(ichi):
    """Fiyatın ichimoku yapısındaki konumunu belirle."""
    p = ichi

    # fiyat konumu
    if p['price'] > p['kumo_top']:
        konum = "kumo_ustu"
    elif p['price'] >= p['kumo_bottom']:
        konum = "kumo_icinde"
    else:
        konum = "kumo_alti"

    # trend
    if p['tenkan'] > p['kijun']:
        trend = "yukselis"
    elif abs(p['tenkan'] - p['kijun']) / p['kijun'] < 0.003:
        trend = "notr"
    else:
        trend = "dusus"

    # chikou
    if p['chikou_ref']:
        chikou = "pozitif" if p['price'] > p['chikou_ref'] else "negatif"
    else:
        chikou = "bilinmiyor"

    # genel sinyal
    bullish_count = 0
    if konum == "kumo_ustu": bullish_count += 1
    if trend == "yukselis": bullish_count += 1
    if chikou == "pozitif": bullish_count += 1
    if p['kumo_renk'] == "yesil": bullish_count += 1

    if bullish_count >= 3:
        genel = "guclu_yukselis"
    elif bullish_count == 2:
        genel = "yukselis"
    elif bullish_count == 1:
        genel = "notr"
    else:
        genel = "dusus"

    return {
        "konum": konum,
        "trend": trend,
        "chikou": chikou,
        "kumo_renk": p['kumo_renk'],
        "bullish_sayi": bullish_count,
        "genel": genel,
    }


# ============================================================
# 5. ATR HESAPLAMA
# ============================================================

def calc_atr(prices_sorted, period=14):
    """ATR(14) hesapla."""
    if len(prices_sorted) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(prices_sorted)):
        high = prices_sorted[i]['high']
        low = prices_sorted[i]['low']
        prev_close = prices_sorted[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    # son 14 günün ortalaması
    atr = sum(true_ranges[-period:]) / period
    return round(atr, 4)


# ============================================================
# 6. HACİM ANALİZİ
# ============================================================

def analyze_volume(prices_sorted):
    """Hacim analizi: oran + OBV trendi."""
    if len(prices_sorted) < 22:
        return None

    volumes = [d['volume'] for d in prices_sorted]
    closes = [d['close'] for d in prices_sorted]

    # bugünkü hacim vs 20 günlük ortalama
    today_vol = volumes[-1]
    avg_vol_20 = sum(volumes[-21:-1]) / 20
    ratio = today_vol / avg_vol_20 if avg_vol_20 > 0 else 0

    today_chg = closes[-1] - closes[-2]

    # OBV son 10 gün trendi
    obv = [0]
    for i in range(1, min(11, len(closes))):
        idx = len(closes) - 11 + i
        if idx < 1:
            continue
        if closes[idx] > closes[idx-1]:
            obv.append(obv[-1] + volumes[idx])
        elif closes[idx] < closes[idx-1]:
            obv.append(obv[-1] - volumes[idx])
        else:
            obv.append(obv[-1])

    # OBV trendi: son 5 gün vs önceki 5 gün
    if len(obv) >= 10:
        obv_recent = obv[-5:]
        obv_older = obv[-10:-5]
        avg_recent = sum(obv_recent) / 5
        avg_older = sum(obv_older) / 5
        if avg_recent > avg_older * 1.02:
            obv_trend = "yukselis"
        elif avg_recent < avg_older * 0.98:
            obv_trend = "dusus"
        else:
            obv_trend = "notr"
    else:
        obv_trend = "bilinmiyor"

    # hacim uyarısı: 3 ardışık gün düşen hacim + yükselen fiyat
    volume_divergence = False
    if len(volumes) >= 4 and len(closes) >= 4:
        vol_decreasing = volumes[-1] < volumes[-2] < volumes[-3]
        price_increasing = closes[-1] > closes[-2] > closes[-3]
        if vol_decreasing and price_increasing:
            volume_divergence = True

    # hacim teyidi seviyesi
    if ratio >= 1.5 and today_chg > 0:
        teyit = "guclu"
    elif ratio >= 1.2 and today_chg > 0:
        teyit = "normal"
    elif ratio >= 0.8:
        teyit = "zayif"
    else:
        teyit = "yok"

    return {
        "gunluk_hacim": int(today_vol),
        "ortalama_hacim": int(avg_vol_20),
        "oran": round(ratio, 2),
        "gunluk_fiyat_degisim": round(today_chg, 2),
        "obv_trend": obv_trend,
        "hacim_uyarisi": volume_divergence,
        "teyit": teyit,
    }


# ============================================================
# 7. STOP SEVİYESİ BELİRLEME
# ============================================================

def determine_stop(ichi, atr):
    """Dinamik stop seviyesi belirle."""
    p = ichi

    if p['price'] > p['kumo_top']:
        # kumo üstünde: varsayılan stop = kijun
        stop = p['kijun']
        stop_tipi = "kijun"

        # kijun çok yakınsa kumo'ya genişlet
        mesafe_kijun = (p['price'] - p['kijun']) / p['price'] * 100
        if mesafe_kijun < 1.0 and atr:
            stop = p['kumo_top']
            stop_tipi = "kumo_ust"

    elif p['price'] >= p['kumo_bottom']:
        # kumo içinde: stop = kumo alt
        stop = p['kumo_bottom']
        stop_tipi = "kumo_alt"
    else:
        # kumo altında: bu pozisyonda olmamalısın
        stop = p['price'] * 0.95  # acil %5 fallback
        stop_tipi = "acil_%5"

    # ATR doğrulaması
    stop_mesafesi = p['price'] - stop
    atr_check = None
    if atr and atr > 0:
        atr_ratio = stop_mesafesi / atr
        if atr_ratio < 0.5:
            atr_check = "cok_dar"
            # kumo'ya genişlet
            if p['price'] > p['kumo_top']:
                stop = p['kumo_bottom']
                stop_tipi = "kumo_alt_genisletme"
        elif atr_ratio > 3.0:
            atr_check = "cok_genis"
        else:
            atr_check = f"uygun ({atr_ratio:.1f}x ATR)"

    return {
        "stop": round(stop, 2),
        "stop_tipi": stop_tipi,
        "stop_mesafesi": round(stop_mesafesi, 2),
        "stop_mesafesi_pct": round((stop_mesafesi / p['price']) * 100, 2),
        "atr_check": atr_check,
    }


# ============================================================
# 8. POZİSYON BOYUTLANDIRMA
# ============================================================

def calc_position_size(price, stop, atr, account_size=10000, vix=None, sektor_tipi="duyarli"):
    """
    K-13 v4.1 sektör bazlı ATR pozisyon boyutu.

    sektor_tipi: "faydalanici" veya "duyarli" (jeopolitik/savaş krizi varsayılan)
    Faydalanıcı: enerji, savunma, altın, sağlık, staples, telekom, utilities, siber güvenlik
    Duyarlı   : tech/AI yarıiletken, tüketim döngüsel, havacılık, REIT, küçük cap

    K-13 v4.1 VIX bant matrisi:
      VIX < 22            → tam pozisyon (her iki sektör)
      VIX 22-28 faydal.  → tam pozisyon
      VIX 22-28 duyarlı  → yarım pozisyon
      VIX 28-35 faydal.  → yarım  + formül: standart × (22/VIX)
      VIX 28-35 duyarlı  → giriş yok → None döner
      VIX 35+   faydal.  → çeyrek + formül
      VIX 35+   duyarlı  → giriş yok → None döner

    Not: VIX None gelirse get_vix_level() ile Yahoo Finance'ten çekilir.
    """
    # Gerçek VIX seviyesini al
    if vix is None:
        try:
            import urllib.request as _ur
            req = _ur.Request(
                "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = json.loads(_ur.urlopen(req, timeout=8).read())
            vix = float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
        except Exception:
            vix = 20.0  # bağlantı yoksa sakin bant varsay

    faydalanici = (sektor_tipi.lower() == "faydalanici")

    # K-13 v4.1 bant kararı
    if vix < 22:
        multiplier = 1.0          # tam
    elif vix < 28:
        multiplier = 1.0 if faydalanici else 0.5   # faydal=tam, duyarlı=yarım
    elif vix < 35:
        if not faydalanici:
            return None           # duyarlı → giriş yok
        multiplier = 0.5 * (22 / vix)  # faydal=yarım + formül
    else:
        if not faydalanici:
            return None           # duyarlı → giriş yok
        multiplier = 0.25 * (22 / vix) # faydal=çeyrek + formül

    # VIX 28+ ek kural: risk %3 max (normal %5 yerine)
    base_risk_pct = 0.01
    if vix >= 28:
        base_risk_pct = 0.005   # %0.5 risk (daha temkinli)

    risk_pct = base_risk_pct * multiplier

    risk_amount = account_size * risk_pct
    stop_distance = price - stop

    if stop_distance <= 0:
        return None

    shares = int(risk_amount / stop_distance)
    position_value = shares * price
    max_position = account_size * 0.125  # %12.5

    if position_value > max_position:
        shares = int(max_position / price)
        position_value = shares * price

    return {
        "hisse_adedi": shares,
        "pozisyon_tutari": round(position_value, 2),
        "risk_tutari": round(risk_amount, 2),
        "risk_yuzdesi": risk_pct * 100,
        "pozisyon_agirligi": round((position_value / account_size) * 100, 1),
    }


# ============================================================
# 9. SMA200 UZUN VADELİ TREND FİLTRESİ
# ============================================================

def check_sma200(symbol, price):
    """SMA200 uzun vadeli trend filtresi. ichimoku'nun kapsamadığı 200 günlük perspektif."""
    sma200_data = fmp_get("technical-indicators/sma", {
        "symbol": symbol, "periodLength": 200, "timeframe": "1day"
    })
    if not sma200_data or len(sma200_data) < 2:
        return None

    sma200 = sma200_data[0].get("sma", 0)
    sma200_prev = sma200_data[1].get("sma", 0)

    if sma200 <= 0:
        return None

    above = price > sma200
    fark_pct = ((price - sma200) / sma200) * 100
    sma_trend = "yukselis" if sma200 > sma200_prev else "dusus"

    return {
        "sma200": round(sma200, 2),
        "above": above,
        "fark_pct": round(fark_pct, 2),
        "sma_trend": sma_trend,
    }


# ============================================================
# 11. TAM ANALİZ
# ============================================================

def full_analysis(symbol, detay=False):
    """Bir sembol için tam ichimoku + hacim + ATR analizi."""
    print(f"\n{'='*55}")
    print(f"  {symbol} — ichimoku + hacim + ATR analiz")
    print(f"{'='*55}")

    # fiyat verisi çek (120 gün)
    prices_raw = fmp_get("historical-price-eod/full", {"symbol": symbol, "limit": 120})
    if not prices_raw or len(prices_raw) < 55:
        print(f"  ❌ yetersiz veri ({len(prices_raw) if prices_raw else 0} gün)")
        return None

    prices = sorted(prices_raw, key=lambda x: x['date'])

    # 1. ichimoku
    ichi = calc_ichimoku(prices)
    if not ichi:
        print("  ❌ ichimoku hesaplanamadı")
        return None

    # 2. ATR
    atr = calc_atr(prices)

    # 3. hacim
    vol = analyze_volume(prices)

    # 4. durum
    pos = determine_position(ichi)

    # 5. giriş sinyalleri
    entry_signals = detect_entry_signals(ichi)

    # 6. çıkış sinyalleri
    exit_signals = detect_exit_signals(ichi)

    # 7. stop seviyesi
    stop_info = determine_stop(ichi, atr)

    # 8. SMA200 uzun vadeli filtre
    sma200_info = check_sma200(symbol, ichi['price'])

    # === ÇIKTI ===

    # ichimoku tablosu
    print(f"\n  📊 ICHİMOKU")
    print(f"     fiyat: ${ichi['price']}")
    print(f"     tenkan (9):  ${ichi['tenkan']}  {'↑' if ichi['tenkan'] > ichi['tenkan_prev'] else '↓'}")
    print(f"     kijun (26):  ${ichi['kijun']}  {'↑' if ichi['kijun'] > ichi['kijun_prev'] else '↓'}")
    print(f"     kumo: ${ichi['kumo_bottom']} — ${ichi['kumo_top']} ({ichi['kumo_renk']}, kalınlık: ${ichi['kumo_kalinlik']})")

    # konum
    konum_emoji = {"kumo_ustu": "🟢", "kumo_icinde": "🟡", "kumo_alti": "🔴"}
    trend_emoji = {"yukselis": "↑", "notr": "→", "dusus": "↓"}
    print(f"\n  📍 KONUM: {konum_emoji.get(pos['konum'], '?')} {pos['konum']}")
    print(f"     trend: {trend_emoji.get(pos['trend'], '?')} {pos['trend']} (tenkan vs kijun)")
    print(f"     chikou: {pos['chikou']}")
    print(f"     kumo renk: {pos['kumo_renk']}")
    print(f"     genel: {pos['genel']} ({pos['bullish_sayi']}/4)")

    # ATR
    if atr:
        print(f"\n  📏 ATR(14): ${atr}")
        print(f"     günlük ort. hareket: ±${atr:.2f} (±%{(atr/ichi['price']*100):.1f})")

    # hacim
    if vol:
        obv_emoji = {"yukselis": "↑", "dusus": "↓", "notr": "→"}
        print(f"\n  📊 HACİM")
        print(f"     bugün: {vol['gunluk_hacim']:,} ({vol['oran']:.1f}x ortalama)")
        print(f"     OBV trend: {obv_emoji.get(vol['obv_trend'], '?')} {vol['obv_trend']}")
        print(f"     teyit: {vol['teyit']}")
        if vol['hacim_uyarisi']:
            print(f"     ⚠️ hacim ayrışması: düşen hacim + yükselen fiyat")

    # stop
    print(f"\n  🛑 STOP")
    print(f"     seviye: ${stop_info['stop']} ({stop_info['stop_tipi']})")
    print(f"     mesafe: ${stop_info['stop_mesafesi']} (-%{stop_info['stop_mesafesi_pct']})")
    if stop_info['atr_check']:
        print(f"     ATR kontrol: {stop_info['atr_check']}")

    # giriş sinyalleri
    print(f"\n  🚀 GİRİŞ SİNYALLERİ")
    if entry_signals:
        for s in entry_signals:
            guc_emoji = {"yuksek": "🟢", "orta": "🟡", "zayif": "🔴"}
            print(f"     {guc_emoji.get(s['guc'], '?')} [{s['tip']}] {s['aciklama']}")
    else:
        print(f"     — bugün aktif giriş sinyali yok")

    # çıkış sinyalleri
    if exit_signals:
        print(f"\n  🚪 ÇIKIŞ SİNYALLERİ")
        for s in exit_signals:
            acil = "🔴" if s.get('acil') else "🟡"
            print(f"     {acil} [{s['tip']}] {s['aciklama']}")

    # SMA200
    if sma200_info:
        s200_emoji = "✅" if sma200_info['above'] else "❌"
        trend_icon = "↑" if sma200_info['sma_trend'] == "yukselis" else "↓"
        print(f"\n  📈 SMA200: ${sma200_info['sma200']} {trend_icon}")
        print(f"     {s200_emoji} fiyat {'üstünde' if sma200_info['above'] else 'altında'} ({sma200_info['fark_pct']:+.1f}%)")

    # === KARAR ===
    print(f"\n  {'─'*45}")

    # karar mantığı (temel analiz claude tarafından ayrıca değerlendirilir)
    sma200_above = sma200_info['above'] if sma200_info else True

    # kijun bounce'ta stop mesafesi dar olacağı için kumo alt'a genişlet
    effective_stop = stop_info
    if entry_signals:
        sinyal_tipleri = [s['tip'] for s in entry_signals]
        if 'kijun_bounce' in sinyal_tipleri and stop_info['stop_mesafesi_pct'] < 5.0:
            # kijun bounce: stop'u kumo alt kenarına genişlet
            kumo_alt_stop_mesafesi = ichi['price'] - ichi['kumo_bottom']
            kumo_alt_stop_pct = (kumo_alt_stop_mesafesi / ichi['price']) * 100
            effective_stop = {
                'stop': round(ichi['kumo_bottom'], 2),
                'stop_tipi': 'kumo_alt_bounce',
                'stop_mesafesi': round(kumo_alt_stop_mesafesi, 2),
                'stop_mesafesi_pct': round(kumo_alt_stop_pct, 2),
                'atr_check': stop_info['atr_check'],
            }
            print(f"\n  ℹ️ kijun bounce: stop kijun→kumo alt genişletildi (${ichi['kijun']:.2f}→${ichi['kumo_bottom']:.2f}, -%{kumo_alt_stop_pct:.1f})")

    if pos['konum'] == "kumo_alti" and pos['trend'] == "dusus":
        karar = "GİRME ❌ (kumo altı + düşüş trendi)"
    elif entry_signals:
        sinyal_tipleri = [s['tip'] for s in entry_signals]
        # <%5 filtresi sadece kumo kırılımı girişine uygulanır
        if 'kumo_kirilimi' in sinyal_tipleri and 'kijun_bounce' not in sinyal_tipleri and effective_stop['stop_mesafesi_pct'] < 5.0:
            karar = "GİRME ❌ (kumo kırılımı + stop mesafesi <%5, whipsaw riski)"
        elif effective_stop['stop_mesafesi_pct'] < 2.0:
            karar = "GİRME ❌ (stop mesafesi <%2, kumo genişletme sonrası bile çok dar)"
        else:
            en_guclu = max(entry_signals, key=lambda x: {"yuksek": 3, "orta": 2, "zayif": 1}.get(x['guc'], 0))
            if not sma200_above:
                if en_guclu['guc'] == "yuksek" and vol and vol['teyit'] in ('guclu', 'normal'):
                    karar = "GİRİŞ ⚠️ (SMA200 altı, yarım pozisyon)"
                else:
                    karar = "BEKLE ⏳ (SMA200 altı, güçlü sinyal bekle)"
            else:
                if en_guclu['guc'] == "yuksek" and vol and vol['teyit'] in ('guclu', 'normal'):
                    karar = "GİRİŞ ✅"
                elif en_guclu['guc'] == "yuksek" and vol and vol['teyit'] == 'zayif':
                    karar = "GİRİŞ ⚠️ (hacim zayıf, yarım pozisyon)"
                elif en_guclu['guc'] == "orta":
                    karar = "DİKKATLİ GİRİŞ ⚠️"
                else:
                    karar = "BEKLE ⏳ (zayıf sinyal)"
    elif stop_info['stop_mesafesi_pct'] < 5.0 and not entry_signals:
        karar = "GİRME ❌ (stop mesafesi <%5, whipsaw riski yüksek)"
    elif pos['genel'] in ('guclu_yukselis', 'yukselis') and not exit_signals:
        karar = "TREND DEVAM — giriş sinyali bekle"
    elif exit_signals:
        acil_var = any(s.get('acil') for s in exit_signals)
        if acil_var:
            karar = "ÇIKIŞ 🔴"
        else:
            karar = "UYARI — çıkış yakın ⚠️"
    else:
        karar = "BEKLE ⏳"

    print(f"  KARAR: {karar}")
    print(f"  {'─'*45}")

    return {
        "symbol": symbol,
        "ichimoku": ichi,
        "atr": atr,
        "volume": vol,
        "sma200": sma200_info,
        "position": pos,
        "entry_signals": entry_signals,
        "exit_signals": exit_signals,
        "stop": stop_info,
        "effective_stop": effective_stop,
        "karar": karar,
    }


# ============================================================
# 11. AKTİF POZİSYON GÜNCELLEME
# ============================================================

def update_active_positions():
    """Aktif swing pozisyonları için ichimoku seviyelerini güncelle."""
    active_path = os.path.join(REPO_ROOT, "data/swing/active.json")
    with open(active_path) as f:
        data = json.load(f)

    if not data.get('aktif_pozisyonlar'):
        print("  aktif pozisyon yok")
        return

    print(f"\n{'='*60}")
    print(f"  AKTİF POZİSYON GÜNCELLEMESİ")
    print(f"{'='*60}")

    for pos in data['aktif_pozisyonlar']:
        sym = pos['sembol']
        result = full_analysis(sym)
        if not result:
            continue

        ichi = result['ichimoku']
        stop_info = result['stop']

        # ichimoku seviyelerini güncelle
        pos['kijun_sen'] = ichi['kijun']
        pos['tenkan_sen'] = ichi['tenkan']
        pos['kumo_ust'] = ichi['kumo_top']
        pos['kumo_alt'] = ichi['kumo_bottom']
        pos['atr_14'] = result['atr']

        if result['volume']:
            pos['hacim_oran'] = result['volume']['oran']
            pos['obv_trend'] = result['volume']['obv_trend']

        # stop güncelle (sadece yukarı)
        yeni_stop = stop_info['stop']
        eski_stop = pos.get('stop_en_yuksek', pos.get('stop_loss', 0))

        if yeni_stop > eski_stop:
            pos['stop_loss'] = yeni_stop
            pos['stop_en_yuksek'] = yeni_stop
            pos['stop_tipi'] = stop_info['stop_tipi']
            print(f"\n  ↑ {sym} stop güncellendi: ${eski_stop:.2f} → ${yeni_stop:.2f} ({stop_info['stop_tipi']})")
        else:
            pos['stop_loss'] = eski_stop  # eski stop koru
            print(f"\n  → {sym} stop korundu: ${eski_stop:.2f} (kijun: ${ichi['kijun']:.2f})")

        # çıkış sinyali var mı?
        if result['exit_signals']:
            for s in result['exit_signals']:
                acil = "🔴" if s.get('acil') else "🟡"
                print(f"  {acil} ÇIKIŞ SİNYALİ: {s['aciklama']}")
                if s.get('acil'):
                    _log.kritik(
                        f"ACİL ÇIKIŞ SİNYALİ: {sym}",
                        f"{s['aciklama']}\n"
                        f"Fiyat: ${pos.get('guncel_fiyat',pos.get('son_fiyat',0)):.2f} | Stop: ${pos.get('stop_loss',0):.2f}\n"
                        f"P&L: {pos.get('pnl_pct',0):+.1f}%",
                        kaynak="swing_ichimoku"
                    )
                else:
                    _log.uyari(
                        f"Çıkış sinyali: {sym}",
                        f"{s['aciklama']}\n"
                        f"Fiyat: ${pos.get('guncel_fiyat',pos.get('son_fiyat',0)):.2f}",
                        kaynak="swing_ichimoku"
                    )

    data['son_guncelleme'] = datetime.now().isoformat()

    with open(active_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ active.json güncellendi")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Swing Trade v2.0 — Ichimoku + Hacim + ATR")
    parser.add_argument("symbols", nargs="?", help="Sembol(ler), virgülle ayır: NEM,AROC")
    parser.add_argument("--aktif", action="store_true", help="Aktif pozisyonları güncelle")
    parser.add_argument("--watchlist", action="store_true", help="Watchlist tara")
    parser.add_argument("--detay", action="store_true", help="Detaylı analiz")
    parser.add_argument("--json", action="store_true", help="JSON çıktı")
    args = parser.parse_args()

    if args.aktif:
        update_active_positions()
        return

    symbols = []

    if args.watchlist:
        wl_path = os.path.join(REPO_ROOT, "data/watchlist.json")
        if os.path.exists(wl_path):
            with open(wl_path) as f:
                wl = json.load(f)
            symbols = [w["sembol"] for w in wl.get("izleme_listesi", [])]
        else:
            print("HATA: data/watchlist.json bulunamadı")
            sys.exit(1)
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        print("Kullanım:")
        print("  python scripts/swing_ichimoku.py NEM,AROC       # aday tarama")
        print("  python scripts/swing_ichimoku.py --aktif         # aktif güncelle")
        print("  python scripts/swing_ichimoku.py --watchlist     # watchlist tara")
        sys.exit(1)

    all_results = []
    for sym in symbols:
        result = full_analysis(sym, detay=args.detay)
        if result:
            all_results.append(result)

    # özet tablo
    if len(all_results) > 1:
        print(f"\n{'='*65}")
        print(f"  ÖZET TABLO")
        print(f"{'='*65}")
        print(f"  {'sembol':6s} | {'konum':10s} | {'trend':8s} | {'sinyal':5s} | {'hacim':6s} | {'SMA200':6s} | {'stop':>8s} | karar")
        print(f"  {'─'*6} | {'─'*10} | {'─'*8} | {'─'*5} | {'─'*6} | {'─'*6} | {'─'*8} | {'─'*20}")
        for r in all_results:
            pos = r['position']
            vol_t = r['volume']['teyit'] if r['volume'] else '?'
            sinyal = len(r['entry_signals'])
            s200 = "✅" if r.get('sma200', {}).get('above', True) else "❌"
            print(f"  {r['symbol']:6s} | {pos['konum']:10s} | {pos['trend']:8s} | {sinyal:5d} | {vol_t:6s} | {s200:6s} | ${r['stop']['stop']:>7.2f} | {r['karar']}")


if __name__ == "__main__":
    main()
