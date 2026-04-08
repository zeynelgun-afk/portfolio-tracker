#!/usr/bin/env python3
"""
Finzora AI — Portföy Fırsat Tarama Ortak Kütüphanesi v1.0

FMP API ile doğru alan isimleri üzerinden 3 portföy (dengeli, agresif, temettü) için
fundamental ve teknik veri toplar, skor hesaplar.

KRİTİK: FMP stable endpoint doğru alan isimleri (8 nisan 2026 tespit):
- priceToEarningsRatioTTM (NOT priceEarningsRatioTTM)
- priceToBookRatioTTM
- debtToEquityRatioTTM (NOT debtEquityRatioTTM)
- dividendYieldTTM
- dividendPayoutRatioTTM (NOT payoutRatioTTM)
- returnOnInvestedCapitalTTM
- returnOnEquityTTM
- freeCashFlowYieldTTM

v3 endpoint'ler legacy, kullanma. Sadece stable/ endpoint'i.
"""

import requests
import os
import time

FMP_API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_BASE = "https://financialmodelingprep.com/stable"


def fmp_get(endpoint, params=None, timeout=10):
    """FMP stable endpoint'ten veri çek."""
    if params is None:
        params = {}
    params['apikey'] = FMP_API_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and 'Error Message' in data:
            return None
        return data
    except Exception:
        return None


def get_fundamentals(symbol):
    """
    Bir sembol için tam fundamental veri seti döndürür.
    
    Returns dict with:
    - pe (float): price/earnings TTM
    - pb (float): price/book TTM
    - ps (float): price/sales TTM
    - de (float): debt/equity TTM
    - yield_pct (float): dividend yield % (ör: 2.87)
    - payout_pct (float): dividend payout ratio % (ör: 44.8)
    - roic_pct (float): ROIC % (ör: 20.8)
    - roe_pct (float): ROE %
    - fcf_yield_pct (float): FCF yield %
    - current_ratio (float)
    - market_cap (float)
    
    Değer 0 veya None ise FMP verinin mevcut olmadığı anlamına gelir, 0.0 döndürür.
    """
    ratios = fmp_get("ratios-ttm", {"symbol": symbol})
    km = fmp_get("key-metrics-ttm", {"symbol": symbol})
    
    ratios = ratios[0] if ratios and isinstance(ratios, list) else {}
    km = km[0] if km and isinstance(km, list) else {}
    
    return {
        'symbol': symbol,
        'pe': ratios.get('priceToEarningsRatioTTM', 0) or 0,
        'pb': ratios.get('priceToBookRatioTTM', 0) or 0,
        'ps': ratios.get('priceToSalesRatioTTM', 0) or 0,
        'de': ratios.get('debtToEquityRatioTTM', 0) or 0,
        'yield_pct': (ratios.get('dividendYieldTTM', 0) or 0) * 100,
        'payout_pct': (ratios.get('dividendPayoutRatioTTM', 0) or 0) * 100,
        'roic_pct': (km.get('returnOnInvestedCapitalTTM', 0) or 0) * 100,
        'roe_pct': (km.get('returnOnEquityTTM', 0) or 0) * 100,
        'fcf_yield_pct': (km.get('freeCashFlowYieldTTM', 0) or 0) * 100,
        'current_ratio': ratios.get('currentRatioTTM', 0) or 0,
        'market_cap': km.get('marketCap', 0) or 0,
        'net_margin_pct': (ratios.get('netProfitMarginTTM', 0) or 0) * 100,
    }


def get_technical(symbol):
    """
    Bir sembol için teknik gösterge seti döndürür.
    
    Returns dict with:
    - price, prev_close, day_change_pct
    - rsi_14
    - sma_20, sma_50, sma_200
    - above_sma_50 (bool), above_sma_200 (bool), golden_cross (bool)
    - m1m, m3m, m6m (1/3/6 ay getiri %)
    """
    quote = fmp_get("batch-quote", {"symbols": symbol})
    if not quote:
        return None
    q = quote[0] if isinstance(quote, list) else {}
    
    def ind(indicator, period):
        r = fmp_get(f"technical-indicators/{indicator}", 
                    {"symbol": symbol, "periodLength": period, "timeframe": "1day"})
        return r[0] if r and isinstance(r, list) else {}
    
    rsi_data = ind('rsi', 14)
    sma_20_data = ind('sma', 20)
    sma_50_data = ind('sma', 50)
    sma_200_data = ind('sma', 200)
    
    pc_data = fmp_get("stock-price-change", {"symbol": symbol})
    pc = pc_data[0] if pc_data and isinstance(pc_data, list) else {}
    
    price = q.get('price', 0) or 0
    prev = q.get('previousClose', 0) or 0
    day_chg = ((price - prev) / prev * 100) if prev else 0
    
    sma_20 = sma_20_data.get('sma', 0) or 0
    sma_50 = sma_50_data.get('sma', 0) or 0
    sma_200 = sma_200_data.get('sma', 0) or 0
    
    return {
        'symbol': symbol,
        'price': price,
        'prev_close': prev,
        'day_change_pct': day_chg,
        'rsi_14': rsi_data.get('rsi', 0) or 0,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'sma_200': sma_200,
        'above_sma_20': price > sma_20 if sma_20 else False,
        'above_sma_50': price > sma_50 if sma_50 else False,
        'above_sma_200': price > sma_200 if sma_200 else False,
        'golden_cross': sma_50 > sma_200 if sma_50 and sma_200 else False,
        'm1m': pc.get('1M', 0) or 0,
        'm3m': pc.get('3M', 0) or 0,
        'm6m': pc.get('6M', 0) or 0,
    }


def get_full_data(symbol, delay=0.05):
    """
    Bir sembol için fundamentals + technical birlikte.
    Batch kullanımlar için delay parametresi.
    """
    fund = get_fundamentals(symbol)
    tech = get_technical(symbol)
    time.sleep(delay)
    return {**fund, **(tech or {})}


# ============================================================
# SKOR HESAPLAMA
# ============================================================

def score_dengeli(data):
    """
    Dengeli portföy skoru (max ~18).
    Kriterler: P/E, ROIC, momentum, SMA, RSI, sektör çeşitliliği, FCF.
    """
    score = 0
    detail = []
    
    # Fundamental
    if data.get('pe', 0) > 0 and data['pe'] < 15:
        score += 2; detail.append("P/E <15: +2")
    elif data.get('pe', 0) > 0 and data['pe'] < 25:
        score += 1; detail.append(f"P/E {data['pe']:.1f} <25: +1")
    
    roic = data.get('roic_pct', 0)
    if roic > 15:
        score += 3; detail.append(f"ROIC {roic:.1f}% >15: +3")
    elif roic > 12:
        score += 2; detail.append(f"ROIC {roic:.1f}% >12: +2")
    elif roic > 10:
        score += 1; detail.append(f"ROIC {roic:.1f}% >10: +1")
    
    # Momentum
    m6m = data.get('m6m', 0)
    if m6m > 20:
        score += 3; detail.append(f"6M {m6m:.1f}% >20: +3")
    elif m6m > 10:
        score += 2; detail.append(f"6M {m6m:.1f}% >10: +2")
    elif m6m > 0:
        score += 1; detail.append(f"6M {m6m:.1f}% >0: +1")
    
    # Technical
    rsi = data.get('rsi_14', 0)
    if 40 <= rsi <= 60:
        score += 2; detail.append(f"RSI {rsi:.0f} nötr: +2")
    
    if data.get('above_sma_50'):
        score += 2; detail.append("SMA50 üstü: +2")
    
    if data.get('golden_cross'):
        score += 1; detail.append("Golden cross: +1")
    
    # FCF (kalite göstergesi)
    fcf = data.get('fcf_yield_pct', 0)
    if fcf > 5:
        score += 2; detail.append(f"FCF yield {fcf:.1f}% >5%: +2")
    elif fcf > 3:
        score += 1; detail.append(f"FCF yield {fcf:.1f}% >3%: +1")
    
    return score, detail


def score_agresif(data):
    """
    Agresif portföy skoru (max ~18).
    Kriterler: Momentum, RS, teknik, fundamental kalite.
    P/E eşiği YOK (büyüme hisseleri pahalı olabilir) ama 60+ aşırı pahalı cezası var.
    Quality guard rails: negatif P/E, negatif ROIC, düşük ROIC cezalandırılır.
    """
    score = 0
    detail = []
    
    # Momentum ağırlıklı
    m1m = data.get('m1m', 0)
    if m1m > 20:
        score += 3; detail.append(f"1M {m1m:.1f}% >20: +3")
    elif m1m > 10:
        score += 2; detail.append(f"1M {m1m:.1f}% >10: +2")
    elif m1m > 0:
        score += 1; detail.append(f"1M {m1m:.1f}% >0: +1")
    
    m6m = data.get('m6m', 0)
    if m6m > 50:
        score += 3; detail.append(f"6M {m6m:.1f}% >50: +3")
    elif m6m > 30:
        score += 2; detail.append(f"6M {m6m:.1f}% >30: +2")
    elif m6m > 15:
        score += 1; detail.append(f"6M {m6m:.1f}% >15: +1")
    
    # Fundamental kalite (QUALITY GUARD RAILS)
    pe = data.get('pe', 0)
    if pe < 0:
        score -= 3; detail.append(f"P/E {pe:.1f} NEGATİF: -3")
    elif pe > 80:
        score -= 3; detail.append(f"P/E {pe:.1f} >80 AŞIRI PAHALI: -3")
    elif pe > 60:
        score -= 2; detail.append(f"P/E {pe:.1f} >60 pahalı: -2")
    elif pe > 40:
        score -= 1; detail.append(f"P/E {pe:.1f} >40 yüksek: -1")
    
    roic = data.get('roic_pct', 0)
    if roic > 25:
        score += 3; detail.append(f"ROIC {roic:.1f}% >25: +3")
    elif roic > 15:
        score += 2; detail.append(f"ROIC {roic:.1f}% >15: +2")
    elif roic > 10:
        score += 1; detail.append(f"ROIC {roic:.1f}% >10: +1")
    elif roic < 0:
        score -= 3; detail.append(f"ROIC {roic:.1f}% NEGATİF: -3")
    elif roic < 8:
        score -= 1; detail.append(f"ROIC {roic:.1f}% düşük: -1")
    
    # Teknik
    rsi = data.get('rsi_14', 0)
    if 50 <= rsi <= 70:
        score += 2; detail.append(f"RSI {rsi:.0f} güçlü: +2")
    elif 40 <= rsi < 50:
        score += 1; detail.append(f"RSI {rsi:.0f} nötr-zayıf: +1")
    elif rsi > 75:
        score -= 1; detail.append(f"RSI {rsi:.0f} aşırı alım: -1")
    
    if data.get('above_sma_50'):
        score += 2; detail.append("SMA50 üstü: +2")
    
    if data.get('golden_cross'):
        score += 2; detail.append("Golden cross: +2")
    
    # 3M hızlı momentum
    m3m = data.get('m3m', 0)
    if m3m > 15:
        score += 2; detail.append(f"3M {m3m:.1f}% >15: +2")
    
    return score, detail


def score_temettü(data):
    """
    Değer + Temettü portföy skoru (max ~16).
    Kriterler: Yield, payout sürdürülebilirliği, P/E, ROIC, trend.
    
    KRİTİK: payout >100% = yield trap, -5 puan + uyarı.
    """
    score = 0
    detail = []
    
    # Yield (sürdürülebilir aralık)
    yld = data.get('yield_pct', 0)
    if 5 <= yld <= 7:
        score += 3; detail.append(f"yield {yld:.2f}% 5-7%: +3")
    elif 4 <= yld < 5:
        score += 2; detail.append(f"yield {yld:.2f}% 4-5%: +2")
    elif 3 <= yld < 4:
        score += 1; detail.append(f"yield {yld:.2f}% 3-4%: +1")
    elif yld > 8:
        score -= 2; detail.append(f"yield {yld:.2f}% >8% UYARI: -2")
    
    # Payout ratio — KRİTİK
    payout = data.get('payout_pct', 0)
    if payout > 100:
        score -= 5; detail.append(f"payout {payout:.1f}% >100% YIELD TRAP: -5")
    elif payout < 50:
        score += 3; detail.append(f"payout {payout:.1f}% <50%: +3")
    elif payout < 65:
        score += 2; detail.append(f"payout {payout:.1f}% <65%: +2")
    elif payout < 75:
        score += 1; detail.append(f"payout {payout:.1f}% <75%: +1")
    
    # Value
    pe = data.get('pe', 0)
    if 0 < pe < 12:
        score += 3; detail.append(f"P/E {pe:.1f} <12: +3")
    elif 0 < pe < 15:
        score += 2; detail.append(f"P/E {pe:.1f} <15: +2")
    elif 0 < pe < 18:
        score += 1; detail.append(f"P/E {pe:.1f} <18: +1")
    elif pe < 0:
        score -= 3; detail.append(f"P/E {pe:.1f} NEGATİF: -3")
    
    # Kalite
    roic = data.get('roic_pct', 0)
    if roic > 15:
        score += 2; detail.append(f"ROIC {roic:.1f}% >15: +2")
    elif roic > 10:
        score += 1; detail.append(f"ROIC {roic:.1f}% >10: +1")
    
    # FCF (temettü sürdürülebilirliği için kritik)
    fcf = data.get('fcf_yield_pct', 0)
    if fcf > 5:
        score += 2; detail.append(f"FCF yield {fcf:.1f}% >5%: +2")
    elif fcf > 0:
        score += 1; detail.append(f"FCF yield {fcf:.1f}% >0: +1")
    elif fcf < 0:
        score -= 2; detail.append(f"FCF yield {fcf:.1f}% NEGATİF: -2")
    
    # Trend
    if data.get('above_sma_50'):
        score += 1; detail.append("SMA50 üstü: +1")
    if data.get('above_sma_200'):
        score += 1; detail.append("SMA200 üstü: +1")
    
    return score, detail


# ============================================================
# EŞİKLER (karar matrisi için)
# ============================================================

THRESHOLDS = {
    'dengeli':  {'ekle': 9, 'izle': 6},
    'agresif':  {'ekle': 14, 'izle': 10},
    'temettü':  {'ekle': 9, 'izle': 6},
}


def get_decision(score, portfolio):
    """Skora göre karar ver: EKLE / İZLE / GEÇ."""
    t = THRESHOLDS.get(portfolio, {'ekle': 12, 'izle': 8})
    if score >= t['ekle']:
        return 'EKLE'
    elif score >= t['izle']:
        return 'İZLE'
    else:
        return 'GEÇ'


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Kullanım: python portfolio_scan_common.py SEMBOL PORTFOLY")
        print("Örnek:   python portfolio_scan_common.py UNH dengeli")
        sys.exit(1)
    
    sym = sys.argv[1].upper()
    port = sys.argv[2].lower()
    
    print(f"\n=== {sym} — {port.upper()} skor analizi ===\n")
    data = get_full_data(sym)
    
    print(f"Fiyat: ${data.get('price',0):.2f}")
    print(f"P/E: {data.get('pe',0):.1f}")
    print(f"ROIC: {data.get('roic_pct',0):.1f}%")
    print(f"Yield: {data.get('yield_pct',0):.2f}%")
    print(f"Payout: {data.get('payout_pct',0):.1f}%")
    print(f"RSI: {data.get('rsi_14',0):.1f}")
    print(f"SMA50 üstü: {data.get('above_sma_50')}")
    print(f"1M: {data.get('m1m',0):+.1f}%, 6M: {data.get('m6m',0):+.1f}%")
    
    if port == 'dengeli':
        score, detail = score_dengeli(data)
    elif port == 'agresif':
        score, detail = score_agresif(data)
    elif port == 'temettü':
        score, detail = score_temettü(data)
    else:
        print(f"Bilinmeyen portföy: {port}")
        sys.exit(1)
    
    karar = get_decision(score, port)
    eşik = THRESHOLDS[port]
    
    print(f"\nSkor detay:")
    for d in detail:
        print(f"  {d}")
    
    print(f"\n{'='*50}")
    print(f"TOPLAM SKOR: {score}")
    print(f"Eşikler ({port}): EKLE≥{eşik['ekle']}, İZLE≥{eşik['izle']}")
    print(f"KARAR: {karar}")
    print(f"{'='*50}\n")
