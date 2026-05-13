#!/usr/bin/env python3
"""
full_universe_screener.py — Finzora AI v3.1
3 portföy için ayrı tarama motoru.

v3.2 (10 Nisan 2026) — 2500 çağrı/dk limitine göre optimize:
  - Workers 20'ye çıkarıldı (fundamentals+technicals+estimates)
  - RSI tarihi veriden hesaplanır (ayrı API çağrısı yok, ~1000 çağrı tasarruf)
  - Batch quote sleep kaldırıldı
  - Tüm FMP endpoint'leri ?symbol= parametreli (path param değil)
  - analyst-estimates: epsAvg/epsHigh/numAnalystsEps (estimatedEps* değil)
  - Temettü yield: lastAnnualDividend / price (dividendYield alanı yok)
  - Tarih eşleştirme: en yakın 2 tahmini al (fiscal yıl bazında)

Modlar:  --mode balanced | dividend | aggressive | all
Çıktı:   data/daily_scan_{mode}.json + data/daily_full_scan.json
Süre:    --mode all için ~15-25 dk
"""

import os
import urllib.request, json, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

API_KEY   = os.environ.get("FMP_API_KEY", "")
BASE      = 'https://financialmodelingprep.com/stable'
TODAY     = datetime.now().strftime('%Y-%m-%d')
NOW       = datetime.now().isoformat()
CUTOFF_DT = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

def calc_rsi(closes, period=14):
    """Kapanış fiyatlarından RSI hesapla (closes: newest first)."""
    if len(closes) < period + 2:
        return None
    # newest first → en eski→yeni sırasına çevir
    c = list(reversed(closes[:period * 3 + 5]))
    gains, losses = [], []
    for i in range(1, len(c)):
        delta = c[i] - c[i-1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    if len(gains) < period:
        return None
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - (100 / (1 + rs)), 2)


AI_UNIVERSE = {
    'ASML','AMAT','LRCX','KLAC','CAMT','ONTO','TER','UCTT','ACMR',
    'ENTG','MKSI','PLAB','LIN','APD','MP','FCX',
    'COHR','LITE','GLW','AAOI','FN','ANET','CRDO',
    'POWL','VRT','ETN','PWR','HUBB','TT',
    'DLR','EQIX',
    'QCOM','AVGO','MRVL','NVDA','AMD','TXN','ARM','TSM',
    'MU','WDC','STX',
    'MSFT','META','GOOGL','ORCL','SNOW','PLTR',
}

K13_FAYDALANICI = {
    'Energy','Utilities','Healthcare',
    'Financial Services','Consumer Defensive',
    'Communication Services','Real Estate',
}

def log(msg): print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)

# ─── HTTP ─────────────────────────────────────────────────────────────────────
def fetch(url, timeout=20, retries=4):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt < retries - 1:
                wait = 3 * (2 ** attempt)  # 3s, 6s, 12s
                log(f'  fetch retry {attempt+1}/{retries-1} — {wait}s bekleniyor ({e})')
                time.sleep(wait)
            else:
                log(f'  fetch başarısız (4 deneme): {url[:80]}')
    return None

# ─── FAZ 1: Screener'lar ─────────────────────────────────────────────────────
def screener_balanced():
    url = (f'{BASE}/company-screener?marketCapMoreThan=3000000000'
           f'&priceMoreThan=10&volumeMoreThan=500000'
           f'&country=US&isActivelyTrading=true&limit=2000&apikey={API_KEY}')
    for attempt in range(3):
        data = fetch(url, timeout=30) or []
        if data:
            log(f'  Dengeli screener: {len(data)} hisse')
            return data
        log(f'  Dengeli screener boş döndü (deneme {attempt+1}/3) — 10s bekleniyor')
        time.sleep(10)
    log('  ⚠️  Dengeli screener 3 denemede de boş — API sorunu olabilir')
    return []

def screener_dividend():
    url = (f'{BASE}/company-screener?marketCapMoreThan=5000000000'
           f'&priceMoreThan=10&volumeMoreThan=300000'
           f'&dividendMoreThan=0.5&peRatioLessThan=30'
           f'&country=US&isActivelyTrading=true&limit=1000&apikey={API_KEY}')
    for attempt in range(3):
        data = fetch(url, timeout=30) or []
        if data:
            log(f'  Temettü screener: {len(data)} hisse')
            return data
        log(f'  Temettü screener boş (deneme {attempt+1}/3) — 10s bekleniyor')
        time.sleep(10)
    log('  ⚠️  Temettü screener 3 denemede boş')
    return []

def screener_aggressive():
    url = (f'{BASE}/company-screener?marketCapMoreThan=2000000000'
           f'&priceMoreThan=15&volumeMoreThan=1000000'
           f'&country=US&isActivelyTrading=true&limit=2000&apikey={API_KEY}')
    data = []
    for attempt in range(3):
        data = fetch(url, timeout=30) or []
        if data:
            break
        log(f'  Agresif screener boş (deneme {attempt+1}/3) — 10s bekleniyor')
        time.sleep(10)
    if not data:
        log('  ⚠️  Agresif screener boş — sadece AI evreni kullanılıyor')
    existing = {r['symbol'] for r in data}
    for sym in AI_UNIVERSE:
        if sym not in existing:
            data.append({'symbol': sym, 'marketCap': 0, 'price': 0,
                         'sector': '', 'companyName': sym,
                         'lastAnnualDividend': 0})
    log(f'  Agresif screener: {len(data)} hisse (AI evreni dahil)')
    return data

# ─── FAZ 2: Batch fiyatlar ────────────────────────────────────────────────────
def get_batch_quotes(symbols):
    quotes = {}
    for i in range(0, len(symbols), 100):
        batch = symbols[i:i+100]
        data = fetch(f'{BASE}/batch-quote?symbols={",".join(batch)}&apikey={API_KEY}') or []
        for q in data:
            quotes[q['symbol']] = q
    return quotes

# ─── FAZ 3: Analist tahminleri ────────────────────────────────────────────────
def _estimate(sym):
    # ✅ Doğru format: ?symbol= parametresi, annual
    data = fetch(f'{BASE}/analyst-estimates?symbol={sym}&period=annual&limit=6&apikey={API_KEY}') or []
    return sym, data

def get_all_estimates(symbols, workers=20):
    log(f'Analist tahminleri: {len(symbols)} sembol ({workers} worker)...')
    result = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_estimate, s): s for s in symbols}
        for fut in as_completed(futs):
            sym, data = fut.result()
            result[sym] = data
    return result

# ─── PEG + EPS satırı ─────────────────────────────────────────────────────────
def compute_row(raw, quote, estimates):
    sym   = raw['symbol']
    price = (quote or {}).get('price') or raw.get('price') or 0
    if not price or price < 5:
        return None

    mcap = raw.get('marketCap') or 0
    est  = estimates.get(sym, [])

    # En yakın 2 gelecek tahmini bul (son 6 aydan itibaren)
    upcoming = [e for e in est if e.get('date', '') >= CUTOFF_DT]
    upcoming.sort(key=lambda x: x.get('date', ''))

    eps_now = eps_fwd = fwd_pe = None
    n_analysts = max((e.get('numAnalystsEps', 0) for e in est), default=0) if est else 0

    if len(upcoming) >= 1:
        e0 = upcoming[0]
        # ✅ Doğru alan: epsAvg (estimatedEpsAvg değil)
        eps_now = e0.get('epsAvg') or e0.get('epsHigh')
        if eps_now and eps_now > 0:
            fwd_pe = price / eps_now

    if len(upcoming) >= 2:
        e1 = upcoming[1]
        eps_fwd = e1.get('epsAvg') or e1.get('epsHigh')

    eps_growth = declining = None
    if eps_now is not None and eps_fwd is not None and eps_now != 0:
        eps_growth = ((eps_fwd - eps_now) / abs(eps_now)) * 100
        declining  = eps_growth < 0
    elif eps_now is not None and eps_now <= 0:
        declining = True

    peg = None
    if fwd_pe and eps_growth and eps_growth > 0:
        peg = fwd_pe / eps_growth

    # ✅ Temettü yield: lastAnnualDividend / price (dividendYield alanı yok)
    last_div  = raw.get('lastAnnualDividend') or 0
    yield_pct = (last_div / price * 100) if price > 0 else 0
    sector    = raw.get('sector', '')

    return {
        'symbol':        sym,
        'company':       raw.get('companyName', sym),
        'sector':        sector,
        'price':         round(price, 2),
        'mcap_b':        round(mcap/1e9, 2),
        'fwd_pe':        round(fwd_pe, 1) if fwd_pe else None,
        'eps_growth_2y': round(eps_growth, 1) if eps_growth is not None else None,
        'peg':           round(peg, 2) if peg else None,
        'declining_eps': bool(declining),
        'n_analysts':    n_analysts,
        'yield_pct':     round(yield_pct, 1),
        'k13_category':  'faydalanici' if sector in K13_FAYDALANICI else 'duyarli',
    }

# ─── FAZ 4a: Fundamenteller ───────────────────────────────────────────────────
def _fundamental(sym):
    # ✅ Doğru format: ?symbol= parametresi
    rat = fetch(f'{BASE}/ratios-ttm?symbol={sym}&apikey={API_KEY}') or [{}]
    km  = fetch(f'{BASE}/key-metrics-ttm?symbol={sym}&apikey={API_KEY}') or [{}]
    r = rat[0] if isinstance(rat, list) and rat else {}
    k = km[0]  if isinstance(km,  list) and km  else {}
    return sym, {
        'payout_pct': round((r.get('dividendPayoutRatioTTM') or 0) * 100, 1),
        'de_ratio':   round(r.get('debtToEquityRatioTTM') or 0, 2),
        'roic':       round((k.get('returnOnInvestedCapitalTTM') or 0) * 100, 1),
        'fcf_yield':  round((k.get('freeCashFlowYieldTTM') or 0) * 100, 1),
        'npm':        round((r.get('netProfitMarginTTM') or 0) * 100, 1),
    }

def get_fundamentals(symbols, workers=20):
    log(f'Fundamenteller: {len(symbols)} sembol ({workers} worker)...')
    result = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_fundamental, s): s for s in symbols}
        for fut in as_completed(futs):
            sym, data = fut.result()
            result[sym] = data
    return result

# ─── FAZ 4b: Teknik ───────────────────────────────────────────────────────────
def _technical(sym):
    # Tek çağrı: tarihi fiyat (RSI de buradan hesaplanır, ayrı API çağrısı yok)
    hist = fetch(f'{BASE}/historical-price-eod/full?symbol={sym}&limit=210&apikey={API_KEY}') or []

    price = sma50 = sma200 = rsi = mom1m = mom3m = mom6m = None

    if isinstance(hist, list) and hist:
        closes = [d['close'] for d in hist if 'close' in d]
        if closes:
            price  = closes[0]
            if len(closes) >= 50:  sma50  = sum(closes[:50])  / 50
            if len(closes) >= 200: sma200 = sum(closes[:200]) / 200
            if len(closes) > 21:   mom1m  = (closes[0] - closes[21]) / closes[21] * 100
            if len(closes) > 63:   mom3m  = (closes[0] - closes[63]) / closes[63] * 100
            if len(closes) > 126:  mom6m  = (closes[0] - closes[126]) / closes[126] * 100
            rsi = calc_rsi(closes)  # tarihi veriden hesapla

    return sym, {
        'rsi':          rsi,
        'mom1m':        round(mom1m, 1)  if mom1m  is not None else None,
        'mom3m':        round(mom3m, 1)  if mom3m  is not None else None,
        'mom6m':        round(mom6m, 1)  if mom6m  is not None else None,
        'above_sma50':  (price > sma50)  if price and sma50  else None,
        'above_sma200': (price > sma200) if price and sma200 else None,
        'golden_cross': (sma50 > sma200) if sma50  and sma200 else None,
    }

def get_technicals(symbols, workers=20):
    log(f'Teknik: {len(symbols)} sembol ({workers} worker)...')
    result = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_technical, s): s for s in symbols}
        for fut in as_completed(futs):
            sym, data = fut.result()
            result[sym] = data
    return result

# ─── SKORLAMA ─────────────────────────────────────────────────────────────────
def score_balanced(row, fund, tec):
    s = 0
    pe = row.get('fwd_pe') or 0
    if   0 < pe < 12: s += 3
    elif 0 < pe < 18: s += 2
    elif 0 < pe < 25: s += 1
    elif pe > 35:     s -= 1

    roic = fund.get('roic') or 0
    if   roic > 20: s += 3
    elif roic > 15: s += 2
    elif roic > 12: s += 1
    elif roic < 5:  s -= 1

    mom6m = tec.get('mom6m') or 0
    if   mom6m > 25: s += 3
    elif mom6m > 12: s += 2
    elif mom6m > 3:  s += 1
    elif mom6m < -15: s -= 2

    rsi = tec.get('rsi') or 0
    if   40 <= rsi <= 62: s += 2
    elif 35 <= rsi <= 70: s += 1
    elif rsi > 75:        s -= 1

    if tec.get('above_sma50'):  s += 2
    if tec.get('golden_cross'): s += 1

    fcf = fund.get('fcf_yield') or 0
    if   fcf > 6: s += 2
    elif fcf > 3: s += 1
    elif fcf < 0: s -= 1

    peg = row.get('peg') or 0
    if 0 < peg < 0.5: s += 1
    return s

def score_dividend(row, fund, tec):
    s = 0
    yld = row.get('yield_pct') or 0
    if   5 <= yld <= 8:   s += 4
    elif 4 <= yld < 5:    s += 3
    elif 3 <= yld < 4:    s += 2
    elif 2.5 <= yld < 3:  s += 1
    elif yld > 9:         s -= 3

    payout = fund.get('payout_pct') or 0
    if   0 < payout < 40:  s += 3
    elif 0 < payout < 55:  s += 2
    elif 0 < payout < 70:  s += 1
    elif payout > 90:      s -= 3
    if payout > 100:       s -= 5  # YIELD TRAP

    pe = row.get('fwd_pe') or 0
    if   0 < pe < 12: s += 3
    elif 0 < pe < 16: s += 2
    elif 0 < pe < 20: s += 1
    elif pe > 25:     s -= 1
    elif pe <= 0:     s -= 3

    roic = fund.get('roic') or 0
    if   roic > 15: s += 2
    elif roic > 10: s += 1

    fcf = fund.get('fcf_yield') or 0
    if   fcf > 6: s += 2
    elif fcf > 3: s += 1
    elif fcf < 0: s -= 3

    if tec.get('above_sma50'):  s += 1
    if tec.get('above_sma200'): s += 1

    de = fund.get('de_ratio') or 0
    if de < 0.5: s += 1
    elif de > 2: s -= 1

    rsi = tec.get('rsi') or 0
    if rsi and rsi < 40: s += 1
    return s

def score_aggressive(row, fund, tec):
    s = 0
    eps = row.get('eps_growth_2y') or 0
    if   eps > 50: s += 4
    elif eps > 30: s += 3
    elif eps > 20: s += 2
    elif eps > 10: s += 1

    mom1m = tec.get('mom1m') or 0
    if   mom1m > 15: s += 3
    elif mom1m > 5:  s += 2
    elif mom1m > 0:  s += 1
    elif mom1m < -10: s -= 2

    mom3m = tec.get('mom3m') or 0
    if   mom3m > 15: s += 2
    elif mom3m > 5:  s += 1

    mom6m = tec.get('mom6m') or 0
    if   mom6m > 40: s += 3
    elif mom6m > 20: s += 2
    elif mom6m > 10: s += 1

    roic = fund.get('roic') or 0
    if   roic > 25: s += 3
    elif roic > 15: s += 2
    elif roic > 10: s += 1
    elif roic < 0:  s -= 3
    elif roic < 8:  s -= 1

    rsi = tec.get('rsi') or 0
    if   50 <= rsi <= 70: s += 2
    elif 40 <= rsi < 50:  s += 1
    elif rsi > 75:        s -= 1
    elif 0 < rsi < 35:   s -= 2

    if tec.get('above_sma50'):  s += 2
    if tec.get('above_sma200'): s += 1
    if tec.get('golden_cross'): s += 1

    pe = row.get('fwd_pe') or 0
    if pe < 0:    s -= 3
    elif pe > 80: s -= 3
    elif pe > 60: s -= 2
    elif pe > 40: s -= 1

    fcf = fund.get('fcf_yield') or 0
    if fcf > 10: s += 2
    elif fcf > 5: s += 1

    if row['symbol'] in AI_UNIVERSE: s += 2
    return s

SCORE_FN = {
    'balanced':   score_balanced,
    'dividend':   score_dividend,
    'aggressive': score_aggressive,
}
THRESHOLDS = {
    'balanced':   {'ekle': 9,  'izle': 6},
    'dividend':   {'ekle': 9,  'izle': 6},
    'aggressive': {'ekle': 16, 'izle': 12},
}

def passes_prefilter(row, mode):
    if mode == 'balanced':
        return (row.get('peg') and row['peg'] <= 2.5
                and not row.get('declining_eps')
                and row.get('n_analysts', 0) >= 3)
    elif mode == 'dividend':
        return row.get('yield_pct', 0) >= 2.5
    elif mode == 'aggressive':
        return ((row.get('eps_growth_2y') or 0) >= 10
                or row['symbol'] in AI_UNIVERSE)
    return False

# ─── KONSOL ÇIKTISI ───────────────────────────────────────────────────────────
def print_results(scored, mode, n=50):
    th = THRESHOLDS[mode]
    print(f'\n{"#":>3} {"SYM":<6} {"Scr":>3} {"RSI":>4} {"EPS":>5} {"1M":>6} {"6M":>6} '
          f'{"50":>3} {"200":>3} {"ROIC":>6} {"FCF":>5} {"YLD":>5} {"K13":<14} Sektör')
    print('-'*110)
    for i, r in enumerate(scored[:n], 1):
        s50  = '✅' if r.get('above_sma50')  else '❌'
        s200 = '✅' if r.get('above_sma200') else '❌'
        sc   = r['score']
        karar = 'EKLE' if sc >= th['ekle'] else ('İZLE' if sc >= th['izle'] else 'GEÇ')
        print(f"{i:>3} {r['symbol']:<6} {sc:>3} "
              f"{r.get('rsi') or 0:>4.0f} "
              f"{r.get('eps_growth_2y') or 0:>5.0f}% "
              f"{r.get('mom1m') or 0:>6.1f}% "
              f"{r.get('mom6m') or 0:>6.1f}% "
              f"{s50:>3} {s200:>3} "
              f"{r.get('roic') or 0:>6.1f}% "
              f"{r.get('fcf_yield') or 0:>5.1f}% "
              f"{r.get('yield_pct') or 0:>5.1f}% "
              f"{r.get('k13_category','?'):<14} "
              f"{r.get('sector','?')} [{karar}]")

# ─── ANA AKIŞ ─────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['balanced','dividend','aggressive','all'], default='all')
    p.add_argument('--workers', type=int, default=20)
    args = p.parse_args()

    modes = ['balanced','dividend','aggressive'] if args.mode == 'all' else [args.mode]
    t0 = time.time()

    # FAZ 1: Screener'lar
    log('FAZ 1: Screener\'lar çekiliyor...')
    universe_map = {}
    if 'balanced'   in modes: [universe_map.update({r['symbol']:r}) for r in screener_balanced()]
    if 'dividend'   in modes: [universe_map.update({r['symbol']:r}) for r in screener_dividend()]
    if 'aggressive' in modes: [universe_map.update({r['symbol']:r}) for r in screener_aggressive()]
    log(f'Toplam tekil sembol: {len(universe_map)}')

    # FAZ 2: Fiyatlar
    log('FAZ 2: Fiyatlar...')
    all_syms = list(universe_map.keys())
    quotes   = get_batch_quotes(all_syms)
    all_syms = [s for s in all_syms if quotes.get(s, {}).get('price', 0) > 5]
    log(f'Fiyat filtresi sonrası: {len(all_syms)} sembol')

    # FAZ 3: Tahminler (tek seferlik, tüm evren)
    estimates = get_all_estimates(all_syms, workers=20)

    # Ham satır hesabı
    log('Ham satır (PEG/EPS/yield) hesabı...')
    all_rows = {}
    for sym in all_syms:
        r = compute_row(universe_map.get(sym, {'symbol': sym}), quotes.get(sym), estimates)
        if r:
            all_rows[sym] = r

    peg_ok  = sum(1 for r in all_rows.values() if r.get('peg') and r['peg'] <= 2.5)
    yld_ok  = sum(1 for r in all_rows.values() if r.get('yield_pct', 0) >= 2.5)
    eps_ok  = sum(1 for r in all_rows.values() if (r.get('eps_growth_2y') or 0) >= 10 or r['symbol'] in AI_UNIVERSE)
    log(f'Ham satır özeti: {len(all_rows)} toplam | PEG≤2.5: {peg_ok} | Yield≥2.5%: {yld_ok} | EPS≥10%/AI: {eps_ok}')

    # Birleşik shortlist
    shortlist = {sym for sym, r in all_rows.items()
                 if any(passes_prefilter(r, m) for m in modes)}
    log(f'Shortlist (3 mod): {len(shortlist)} sembol → teknik+fundamental çekiliyor...')

    # FAZ 4: Fundamental + Teknik
    fundamentals = get_fundamentals(list(shortlist), workers=min(args.workers * 2, 25))
    technicals   = get_technicals(list(shortlist), workers=10)

    # FAZ 5: Skorlama + kayıt
    all_results = {}
    for mode in modes:
        log(f'=== Skorlama: {mode.upper()} ===')
        valid = [r for r in all_rows.values() if passes_prefilter(r, mode)]
        log(f'  Ön filtre: {len(valid)} hisse')

        scored = []
        for r in valid:
            sym  = r['symbol']
            fund = fundamentals.get(sym, {})
            tec  = technicals.get(sym, {})
            sc   = SCORE_FN[mode](r, fund, tec)
            scored.append({
                **r, **fund,
                'rsi':          tec.get('rsi'),
                'mom1m':        tec.get('mom1m'),
                'mom3m':        tec.get('mom3m'),
                'mom6m':        tec.get('mom6m'),
                'above_sma50':  tec.get('above_sma50'),
                'above_sma200': tec.get('above_sma200'),
                'golden_cross': tec.get('golden_cross'),
                'score':        sc,
                'mode':         mode,
                'yield_trap':   (fund.get('payout_pct') or 0) > 100,
            })

        scored.sort(key=lambda x: -x['score'])
        all_results[mode] = scored

        th     = THRESHOLDS[mode]
        n_ekle = sum(1 for s in scored if s['score'] >= th['ekle'])
        n_izle = sum(1 for s in scored if th['izle'] <= s['score'] < th['ekle'])

        output = {
            'tarih':         TODAY,
            'son_guncelleme':NOW,
            'mod':           mode,
            'toplam_taranan':len(all_syms),
            'filtre_gecen':  len(valid),
            'skorlanan':     len(scored),
            'ekle_adaylari': n_ekle,
            'izle_adaylari': n_izle,
            'esikler':       th,
            'sonuclar':      scored,
        }
        fname = f'data/daily_scan_{mode}.json'
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        log(f'  EKLE:{n_ekle} | İZLE:{n_izle} → {fname}')
        print_results(scored, mode, n=50)

    # Geriye dönük uyumluluk
    if 'balanced' in modes:
        bal = all_results['balanced']
        with open('data/daily_full_scan.json', 'w', encoding='utf-8') as f:
            json.dump({
                'tarih':         TODAY,
                'son_guncelleme':NOW,
                'toplam_taranan':len(all_syms),
                'peg_filtreli':  peg_ok,
                'declining_eps': sum(1 for r in all_rows.values() if r.get('declining_eps')),
                'filtreler':     {'mod':'balanced','workers':args.workers},
                'sonuclar':      bal,
                'declining_list':[s for s,r in all_rows.items() if r.get('declining_eps')][:30],
            }, f, ensure_ascii=False, indent=2)

    t1 = time.time()
    log(f'=== TAMAMLANDI {(t1-t0)/60:.1f} dk ===')
    for mode in modes:
        sc = all_results.get(mode, [])
        th = THRESHOLDS[mode]
        log(f'  {mode:<12}: {len(sc):>3} skorlandı | '
            f'EKLE≥{th["ekle"]}:{sum(1 for s in sc if s["score"]>=th["ekle"])} | '
            f'İZLE≥{th["izle"]}:{sum(1 for s in sc if th["izle"]<=s["score"]<th["ekle"])}')

if __name__ == '__main__':
    main()
