#!/usr/bin/env python3
"""
Finzora AI - Swing Trade Teknik Analiz Modülü
Ichimoku + RSI + MACD + SMA + Hacim ile çok katmanlı giriş sinyali.

Kullanım:
  python scripts/swing_technical.py NEM            # tek hisse
  python scripts/swing_technical.py NEM,ONTO,AROC  # çoklu
  python scripts/swing_technical.py --watchlist     # tüm watchlist tara

Giriş kararı: minimum 5/8 puan gerekli (ichimoku 3 + klasik 5)
"""

import requests
import json
import argparse
import os
import sys
from datetime import datetime

FMP_API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_BASE = "https://financialmodelingprep.com/stable"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
# 1. ICHIMOKU HESAPLAMA (FMP'de yok, fiyat verisinden hesaplıyoruz)
# ============================================================

def calc_ichimoku(symbol):
    """Ichimoku bileşenlerini hesapla."""
    prices = fmp_get("historical-price-eod/full", {"symbol": symbol, "limit": 120})
    if not prices or len(prices) < 52:
        return None

    data = sorted(prices, key=lambda x: x['date'])
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    closes = [d['close'] for d in data]

    n = len(data)
    i = n - 1

    def period_hl(end, period):
        start = max(0, end - period + 1)
        return max(highs[start:end+1]), min(lows[start:end+1])

    # tenkan-sen (9)
    th, tl = period_hl(i, 9)
    tenkan = (th + tl) / 2

    # kijun-sen (26)
    kh, kl = period_hl(i, 26)
    kijun = (kh + kl) / 2

    # senkou span A & B
    senkou_a = (tenkan + kijun) / 2
    sh, sl = period_hl(i, 52)
    senkou_b = (sh + sl) / 2

    kumo_top = max(senkou_a, senkou_b)
    kumo_bottom = min(senkou_a, senkou_b)

    # chikou span
    chikou_ref = closes[i - 26] if i >= 26 else None

    price = closes[i]

    # --- ichimoku sinyalleri (3 puan) ---
    signals = {}

    # S1: fiyat vs kumo
    if price > kumo_top:
        signals["kumo"] = ("fiyat > kumo (yukselis)", 1)
    elif price > kumo_bottom:
        signals["kumo"] = ("fiyat kumo icinde (notr)", 0.5)
    else:
        signals["kumo"] = ("fiyat < kumo (dusus)", 0)

    # S2: tenkan vs kijun (TK cross)
    if tenkan > kijun:
        signals["tk_cross"] = ("tenkan > kijun (yukselis)", 1)
    elif abs(tenkan - kijun) / kijun < 0.005:
        signals["tk_cross"] = ("tenkan ~ kijun (yakinlasiyor)", 0.5)
    else:
        signals["tk_cross"] = ("tenkan < kijun (dusus)", 0)

    # S3: chikou span vs 26 gun onceki fiyat
    if chikou_ref:
        if price > chikou_ref:
            signals["chikou"] = ("chikou > 26g onceki (yukselis)", 1)
        else:
            signals["chikou"] = ("chikou < 26g onceki (dusus)", 0)
    else:
        signals["chikou"] = ("chikou veri yok", 0)

    ichimoku_score = sum(v[1] for v in signals.values())

    return {
        "price": round(price, 2),
        "tenkan": round(tenkan, 2),
        "kijun": round(kijun, 2),
        "senkou_a": round(senkou_a, 2),
        "senkou_b": round(senkou_b, 2),
        "kumo_top": round(kumo_top, 2),
        "kumo_bottom": round(kumo_bottom, 2),
        "kumo_renk": "yesil" if senkou_a > senkou_b else "kirmizi",
        "chikou_ref": round(chikou_ref, 2) if chikou_ref else None,
        "signals": signals,
        "score": ichimoku_score,
        "max_score": 3,
    }


# ============================================================
# 2. RSI DÖNÜŞ TESPİTİ
# ============================================================

def check_rsi(symbol):
    """RSI ve dönüş sinyali."""
    rsi_data = fmp_get("technical-indicators/rsi", {
        "symbol": symbol, "periodLength": 14, "timeframe": "1day"
    })
    if not rsi_data or len(rsi_data) < 3:
        return None

    cur = rsi_data[0].get("rsi", 50)
    prev = rsi_data[1].get("rsi", 50)
    prev2 = rsi_data[2].get("rsi", 50)

    # sinyal: RSI donus teyidi (30 altindan cikis VEYA yukselen RSI trendi)
    score = 0
    if prev < 30 and cur > 30:
        label = f"RSI donus teyidi ({prev:.0f} -> {cur:.0f})"
        score = 1
    elif cur > prev > prev2 and cur < 50:
        label = f"RSI yukselen trend ({prev2:.0f} -> {prev:.0f} -> {cur:.0f})"
        score = 0.5
    elif cur > 50 and cur < 70:
        label = f"RSI notr-pozitif ({cur:.0f})"
        score = 0.5
    elif cur >= 70:
        label = f"RSI asiri alim ({cur:.0f}) - DIKKAT"
        score = 0
    else:
        label = f"RSI zayif ({cur:.0f})"
        score = 0

    return {
        "current": round(cur, 1),
        "prev": round(prev, 1),
        "prev2": round(prev2, 1),
        "label": label,
        "score": score,
        "max_score": 1,
    }


# ============================================================
# 3. MACD SİNYALİ (FMP'de mevcut değil, kendimiz hesaplıyoruz)
# ============================================================

def calc_ema(values, period):
    """EMA hesapla."""
    if len(values) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = [sum(values[:period]) / period]  # ilk değer SMA
    for price in values[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def check_macd(symbol):
    """MACD hesapla (EMA12 - EMA26, signal EMA9)."""
    prices = fmp_get("historical-price-eod/full", {"symbol": symbol, "limit": 80})
    if not prices or len(prices) < 35:
        return None

    closes = [d['close'] for d in sorted(prices, key=lambda x: x['date'])]

    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)

    # MACD line = EMA12 - EMA26 (hizala: ema26 daha kısa)
    offset = len(ema12) - len(ema26)
    macd_line = [ema12[offset + i] - ema26[i] for i in range(len(ema26))]

    if len(macd_line) < 9:
        return None

    signal_line = calc_ema(macd_line, 9)

    # histogram (son 3 gün)
    offset2 = len(macd_line) - len(signal_line)
    histograms = [macd_line[offset2 + i] - signal_line[i] for i in range(len(signal_line))]

    if len(histograms) < 3:
        return None

    cur_macd = macd_line[-1]
    cur_signal = signal_line[-1]
    cur_hist = histograms[-1]
    prev_hist = histograms[-2]
    prev2_hist = histograms[-3]

    prev_macd = macd_line[-2]
    prev_signal = signal_line[-2]

    score = 0
    reasons = []

    # bullish cross (MACD sinyal çizgisini yukarı kesiyor)
    if prev_macd < prev_signal and cur_macd > cur_signal:
        reasons.append("bullish cross")
        score = 1
    # histogram yükseliyor (momentum artıyor)
    elif cur_hist > prev_hist > prev2_hist:
        reasons.append("histogram yukseliyor")
        score = 0.5
    # histogram negatiften sıfıra yaklaşıyor
    elif cur_hist > prev_hist and cur_hist < 0:
        reasons.append("histogram toparlanma basliyor")
        score = 0.25
    else:
        reasons.append("negatif/zayif")
        score = 0

    label = f"MACD: {', '.join(reasons)} (hist:{cur_hist:.3f})"

    return {
        "macd": round(cur_macd, 3),
        "signal": round(cur_signal, 3),
        "histogram": round(cur_hist, 3),
        "label": label,
        "score": score,
        "max_score": 1,
    }


# ============================================================
# 4. SMA POZİSYONU
# ============================================================

def check_sma(symbol):
    """Fiyat vs SMA20/50 pozisyonu."""
    quote = fmp_get("quote", {"symbol": symbol})
    if not quote or len(quote) < 1:
        return None

    price = quote[0].get("price", 0)

    sma20_data = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 20, "timeframe": "1day"})
    sma50_data = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 50, "timeframe": "1day"})

    s20 = sma20_data[0].get("sma", 0) if sma20_data and len(sma20_data) > 0 else 0
    s50 = sma50_data[0].get("sma", 0) if sma50_data and len(sma50_data) > 0 else 0

    # SMA20 kontrolü de önceki günlerle
    prev_s20 = sma20_data[1].get("sma", 0) if sma20_data and len(sma20_data) > 1 else 0

    score = 0
    reasons = []

    if price > s20:
        reasons.append("fiyat > SMA20")
        score += 0.5
    if price > s50:
        reasons.append("fiyat > SMA50")
        score += 0.5
    if price < s20 and price > s20 * 0.98:
        reasons.append("SMA20'ye yakin (potansiyel kirilim)")
        score += 0.25

    if not reasons:
        reasons.append("tum SMA'larin altinda")

    label = f"SMA: {', '.join(reasons)}"

    return {
        "price": round(price, 2),
        "sma20": round(s20, 2),
        "sma50": round(s50, 2),
        "label": label,
        "score": min(score, 1),
        "max_score": 1,
    }


# ============================================================
# 5. HACİM ANALİZİ
# ============================================================

def check_volume(symbol):
    """Hacim artışı kontrolü (ort. hacmi historical data'dan hesapla)."""
    prices = fmp_get("historical-price-eod/full", {"symbol": symbol, "limit": 25})
    if not prices or len(prices) < 5:
        return None

    data = sorted(prices, key=lambda x: x['date'])
    volumes = [d['volume'] for d in data]
    closes = [d['close'] for d in data]

    today_vol = volumes[-1]
    avg_vol_20 = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1
    today_chg = ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) >= 2 else 0

    ratio = today_vol / avg_vol_20 if avg_vol_20 > 0 else 0

    score = 0
    if ratio >= 1.5 and today_chg > 0:
        label = f"hacim {ratio:.1f}x ortalama + pozitif gun (GUCLU)"
        score = 1
    elif ratio >= 1.2 and today_chg > 0:
        label = f"hacim {ratio:.1f}x ortalama + pozitif gun"
        score = 0.5
    elif ratio >= 1.5 and today_chg < 0:
        label = f"hacim {ratio:.1f}x ortalama ama negatif gun (satis baskisi)"
        score = 0
    else:
        label = f"hacim {ratio:.1f}x ortalama (normal)"
        score = 0.25

    return {
        "volume": today_vol,
        "avg_volume": round(avg_vol_20, 0),
        "ratio": round(ratio, 2),
        "daily_change": round(today_chg, 2),
        "label": label,
        "score": score,
        "max_score": 1,
    }


# ============================================================
# 6. TEMEL ANALİZ FİLTRESİ
# ============================================================

def check_fundamentals(symbol):
    """Temel analiz minimum eşik kontrolü. Geçer/kalır filtresi."""
    flags = []      # kırmızı bayraklar
    positives = []  # olumlu noktalar
    passed = True

    # Gelir tablosu (son 2 çeyrek)
    inc = fmp_get("income-statement", {"symbol": symbol, "period": "quarter", "limit": 6})
    if inc and len(inc) >= 2:
        # Son çeyrek
        rev_last = inc[0].get('revenue', 0)
        ni_last = inc[0].get('netIncome', 0)

        # Net marj
        net_margin = (ni_last / rev_last * 100) if rev_last > 0 else 0
        if net_margin > 10:
            positives.append(f"net marj %{net_margin:.1f} (guclu)")
        elif net_margin > 0:
            positives.append(f"net marj %{net_margin:.1f} (pozitif)")
        else:
            flags.append(f"net marj %{net_margin:.1f} (NEGATIF)")

        # YoY gelir büyümesi (son çeyrek vs 4 çeyrek önce)
        if len(inc) >= 5:
            rev_yoy = inc[4].get('revenue', 0)
            if rev_yoy > 0:
                rev_growth = ((rev_last - rev_yoy) / rev_yoy) * 100
                if rev_growth > 5:
                    positives.append(f"gelir buyume %{rev_growth:.1f} YoY")
                elif rev_growth > 0:
                    positives.append(f"gelir buyume %{rev_growth:.1f} YoY (yavas)")
                else:
                    flags.append(f"gelir KUCULUYOR %{rev_growth:.1f} YoY")

        # Net kâr trendi (son 3 çeyrek)
        if len(inc) >= 3:
            ni_trend = [inc[i].get('netIncome', 0) for i in range(3)]
            if ni_trend[0] > ni_trend[1] > ni_trend[2]:
                positives.append("net kar trendi yukseliyor (3 ceyrek)")
            elif ni_trend[0] < ni_trend[1] < ni_trend[2]:
                flags.append("net kar trendi DUSUYOR (3 ceyrek)")

    # Bilanço
    bs = fmp_get("balance-sheet-statement", {"symbol": symbol, "period": "quarter", "limit": 1})
    if bs and len(bs) > 0:
        b = bs[0]
        total_debt = b.get('totalDebt', 0)
        equity = b.get('totalStockholdersEquity', 0)
        cash = b.get('cashAndCashEquivalents', 0)

        # D/E oranı
        if equity > 0:
            de_ratio = total_debt / equity
            if de_ratio > 3:
                flags.append(f"D/E {de_ratio:.2f} (COK YUKSEK)")
                passed = False  # kritik eşik
            elif de_ratio > 2:
                flags.append(f"D/E {de_ratio:.2f} (yuksek)")
            elif de_ratio < 1:
                positives.append(f"D/E {de_ratio:.2f} (dusuk)")
            else:
                positives.append(f"D/E {de_ratio:.2f} (makul)")

        # Nakit durumu
        if total_debt > 0 and cash > 0:
            cash_debt_pct = (cash / total_debt) * 100
            if cash_debt_pct < 1:
                flags.append(f"nakit/borc %{cash_debt_pct:.1f} (KRITIK DUSUK)")
            elif cash_debt_pct < 5:
                flags.append(f"nakit/borc %{cash_debt_pct:.1f} (dusuk)")
            else:
                positives.append(f"nakit/borc %{cash_debt_pct:.1f}")

    # Nakit akışı (TTM)
    cf = fmp_get("cash-flow-statement", {"symbol": symbol, "period": "quarter", "limit": 4})
    if cf:
        ttm_fcf = sum(c.get('freeCashFlow', 0) for c in cf)
        ttm_ocf = sum(c.get('operatingCashFlow', 0) for c in cf)
        if ttm_fcf > 0:
            positives.append(f"FCF pozitif ${ttm_fcf/1e6:.0f}M (TTM)")
        else:
            flags.append(f"FCF NEGATIF ${ttm_fcf/1e6:.0f}M (TTM)")
        if ttm_ocf > 0:
            positives.append(f"isletme nakit akisi ${ttm_ocf/1e6:.0f}M (TTM)")

    # Analist konsensüsü
    gc = fmp_get("grades-consensus", {"symbol": symbol})
    if gc and len(gc) > 0:
        g = gc[0]
        buy = g.get('strongBuy', 0) + g.get('buy', 0)
        sell = g.get('sell', 0) + g.get('strongSell', 0)
        hold = g.get('hold', 0)
        total_analysts = buy + sell + hold
        if total_analysts > 0:
            buy_pct = (buy / total_analysts) * 100
            if buy_pct >= 70:
                positives.append(f"analist %{buy_pct:.0f} al ({buy}/{total_analysts})")
            elif sell > buy:
                flags.append(f"analist SAT agirlikli ({sell} sat vs {buy} al)")

    # Sonuç
    # kritik kırmızı bayrak sayısı
    critical_flags = [f for f in flags if any(w in f for w in ["COK YUKSEK", "NEGATIF", "KRITIK", "KUCULUYOR"])]

    if len(critical_flags) >= 2:
        passed = False

    label_parts = []
    if positives:
        label_parts.append(f"{len(positives)} olumlu")
    if flags:
        label_parts.append(f"{len(flags)} uyari")
    if critical_flags:
        label_parts.append(f"{len(critical_flags)} kritik")

    return {
        "passed": passed,
        "positives": positives,
        "flags": flags,
        "critical_flags": critical_flags,
        "label": f"Temel: {', '.join(label_parts)}",
        "verdict": "GECTI ✅" if passed else "KALDI ❌",
    }


# ============================================================
# KAPSAMLI ANALİZ
# ============================================================

def full_analysis(symbol):
    """Teknik + temel analiz birleştir ve skor ver."""
    print(f"\n{'='*50}")
    print(f"  {symbol} - TEKNİK + TEMEL ANALİZ")
    print(f"{'='*50}")

    results = {}

    # 0. TEMEL ANALİZ FİLTRESİ (önce kontrol)
    fund = check_fundamentals(symbol)
    if fund:
        results["fundamentals"] = fund
        emoji = "✅" if fund["passed"] else "❌"
        print(f"\n  🏢 TEMEL ANALİZ ({fund['verdict']})")
        if fund["positives"]:
            for p in fund["positives"]:
                print(f"     ✅ {p}")
        if fund["flags"]:
            for f in fund["flags"]:
                is_critical = any(w in f for w in ["COK YUKSEK", "NEGATIF", "KRITIK", "KUCULUYOR"])
                e = "🔴" if is_critical else "⚠️"
                print(f"     {e} {f}")

    # 1. Ichimoku
    ichi = calc_ichimoku(symbol)
    if ichi:
        results["ichimoku"] = ichi
        print(f"\n  📊 ICHIMOKU (skor: {ichi['score']}/{ichi['max_score']})")
        print(f"     fiyat: ${ichi['price']} | tenkan: ${ichi['tenkan']} | kijun: ${ichi['kijun']}")
        print(f"     kumo: ${ichi['kumo_bottom']} - ${ichi['kumo_top']} ({ichi['kumo_renk']})")
        for key, (label, sc) in ichi["signals"].items():
            emoji = "✅" if sc >= 1 else "⚠️" if sc > 0 else "❌"
            print(f"     {emoji} {label}")

    # 2. RSI
    rsi = check_rsi(symbol)
    if rsi:
        results["rsi"] = rsi
        emoji = "✅" if rsi["score"] >= 1 else "⚠️" if rsi["score"] > 0 else "❌"
        print(f"\n  📈 RSI (skor: {rsi['score']}/{rsi['max_score']})")
        print(f"     {emoji} {rsi['label']}")

    # 3. MACD
    macd = check_macd(symbol)
    if macd:
        results["macd"] = macd
        emoji = "✅" if macd["score"] >= 1 else "⚠️" if macd["score"] > 0 else "❌"
        print(f"\n  📉 MACD (skor: {macd['score']}/{macd['max_score']})")
        print(f"     {emoji} {macd['label']}")

    # 4. SMA
    sma = check_sma(symbol)
    if sma:
        results["sma"] = sma
        emoji = "✅" if sma["score"] >= 1 else "⚠️" if sma["score"] > 0 else "❌"
        print(f"\n  📏 SMA (skor: {sma['score']}/{sma['max_score']})")
        print(f"     {emoji} {sma['label']}")
        print(f"     SMA20: ${sma['sma20']} | SMA50: ${sma['sma50']}")

    # 5. Hacim
    vol = check_volume(symbol)
    if vol:
        results["volume"] = vol
        emoji = "✅" if vol["score"] >= 1 else "⚠️" if vol["score"] > 0 else "❌"
        print(f"\n  📊 HACİM (skor: {vol['score']}/{vol['max_score']})")
        print(f"     {emoji} {vol['label']}")

    # TOPLAM TEKNİK SKOR (temel analiz skordan hariç, filtre olarak çalışır)
    total = 0
    max_total = 0
    for key, r in results.items():
        if key == "fundamentals":
            continue  # temel analiz puanlamaya dahil değil
        total += r.get("score", 0)
        max_total += r.get("max_score", 0)

    pct = (total / max_total * 100) if max_total > 0 else 0

    # Temel analiz filtresi
    fund_passed = results.get("fundamentals", {}).get("passed", True)
    fund_critical = len(results.get("fundamentals", {}).get("critical_flags", []))

    print(f"\n  {'─'*40}")
    print(f"  TEKNİK SKOR: {total:.1f}/{max_total} ({pct:.0f}%)")
    print(f"  TEMEL FİLTRE: {'GECTI ✅' if fund_passed else 'KALDI ❌'}")

    # Karar: temel kaldıysa teknik ne olursa olsun girme
    if not fund_passed:
        verdict = "GİRME ❌ (temel analiz RED)"
    elif pct >= 70:
        verdict = "GİRİŞ UYGUN ✅" if fund_critical == 0 else "DİKKATLİ GİRİŞ ⚠️ (temel uyarilar var)"
    elif pct >= 50:
        verdict = "DİKKATLİ GİRİŞ ⚠️ (yakin izle)"
    elif pct >= 35:
        verdict = "ERKEN - BEKLE ⏳ (donus teyidi yok)"
    else:
        verdict = "GİRME ❌ (trend dusus)"

    print(f"  KARAR: {verdict}")
    print(f"  {'─'*40}")

    return {
        "symbol": symbol,
        "total_score": round(total, 1),
        "max_score": max_total,
        "pct": round(pct, 0),
        "fund_passed": fund_passed,
        "fund_flags": fund_critical,
        "verdict": verdict,
        "details": results
    }


# ============================================================
# ANA FONKSİYON
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Swing Trade Teknik Analiz")
    parser.add_argument("symbols", nargs="?", help="Sembol(ler), virgülle ayır: NEM,ONTO,AROC")
    parser.add_argument("--watchlist", action="store_true", help="Tüm watchlist'i tara")
    parser.add_argument("--json", action="store_true", help="Sonuçları JSON olarak çıktıla")
    args = parser.parse_args()

    symbols = []

    if args.watchlist:
        wl_path = os.path.join(REPO_ROOT, "data/watchlist.json")
        with open(wl_path, "r") as f:
            wl = json.load(f)
        symbols = [w["sembol"] for w in wl.get("izleme_listesi", [])]
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        print("Kullanım: python scripts/swing_technical.py NEM,ONTO veya --watchlist")
        sys.exit(1)

    all_results = []
    for sym in symbols:
        result = full_analysis(sym)
        all_results.append(result)

    # Özet tablo
    if len(all_results) > 1:
        print(f"\n{'='*60}")
        print(f"  ÖZET TABLO")
        print(f"{'='*60}")
        for r in sorted(all_results, key=lambda x: x["pct"], reverse=True):
            fund_icon = "✅" if r.get("fund_passed", True) else "❌"
            print(f"  {r['symbol']:6} | teknik:{r['total_score']:.1f}/{r['max_score']} ({r['pct']:.0f}%) | temel:{fund_icon} | {r['verdict']}")

    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
