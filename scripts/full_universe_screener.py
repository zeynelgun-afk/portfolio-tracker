#!/usr/bin/env python3
"""
full_universe_screener.py — Finzora AI v3
3 portföy için ayrı tarama motoru:

  --mode balanced   → Dengeli: PEG + değer + momentum
  --mode dividend   → Temettü: yield kalitesi + payout güvenliği
  --mode aggressive → Agresif: büyüme + momentum + AI tedarik zinciri
  --mode all        → 3 modu sırayla çalıştır (sabah rutini)

Çıktı dosyaları:
  data/daily_scan_balanced.json
  data/daily_scan_dividend.json
  data/daily_scan_aggressive.json
  data/daily_full_scan.json  ← geriye dönük uyumluluk (balanced sonuçları)

Süre: --mode all için ~20-30 dk
"""

import urllib.request, json, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_KEY = 'g1GFJZtV5rCP49UCir4WuP56VjhmA6F8'
BASE    = 'https://financialmodelingprep.com/stable'
TODAY   = datetime.now().strftime('%Y-%m-%d')
NOW     = datetime.now().isoformat()
CUR_YR  = 2026
FWD_YR  = 2028

# ─── AI Tedarik Zinciri Evreni — Agresif için her zaman dahil ────────────────
AI_UNIVERSE = {
    # Yarı iletken ekipman
    'ASML','AMAT','LRCX','KLAC','CAMT','ONTO','TER','UCTT','ACMR',
    # Kimyasal/malzeme
    'ENTG','MKSI','PLAB','LIN','APD','MP','FCX',
    # Optik/bağlantı
    'COHR','LITE','GLW','AAOI','FN','ANET','CRDO',
    # Güç/soğutma
    'POWL','VRT','ETN','PWR','HUBB','TT',
    # Veri merkezi
    'DLR','EQIX',
    # Chip/mobil
    'QCOM','AVGO','MRVL','NVDA','AMD','TXN','ARM','TSM',
    # Bellek
    'MU','WDC','STX',
    # Yazılım/platform
    'MSFT','META','GOOGL','ORCL','SNOW','PLTR',
}

K13_FAYDALANICI = {
    'Energy','Utilities','Healthcare',
    'Financial Services','Consumer Defensive',
    'Communication Services','Real Estate',
}

def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)

# ─── HTTP ─────────────────────────────────────────────────────────────────────
def fetch(url, timeout=15, retries=2):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    return None

# ─── FAZ 1: Mod-spesifik screener'lar ────────────────────────────────────────
def screener_balanced():
    url = (f'{BASE}/company-screener?marketCapMoreThan=3000000000'
           f'&priceMoreThan=10&volumeMoreThan=500000'
           f'&country=US&isActivelyTrading=true&limit=2000&apikey={API_KEY}')
    data = fetch(url, timeout=25) or []
    log(f'  Dengeli screener: {len(data)} hisse')
    return data

def screener_dividend():
    url = (f'{BASE}/company-screener?marketCapMoreThan=5000000000'
           f'&priceMoreThan=10&volumeMoreThan=300000'
           f'&dividendMoreThan=0.025&peRatioLessThan=30'
           f'&country=US&isActivelyTrading=true&limit=1000&apikey={API_KEY}')
    data = fetch(url, timeout=25) or []
    log(f'  Temettü screener: {len(data)} hisse')
    return data

def screener_aggressive():
    url = (f'{BASE}/company-screener?marketCapMoreThan=2000000000'
           f'&priceMoreThan=15&volumeMoreThan=1000000'
           f'&country=US&isActivelyTrading=true&limit=2000&apikey={API_KEY}')
    data = fetch(url, timeout=25) or []
    existing = {r['symbol'] for r in data}
    # AI evreni her zaman ekle
    for sym in AI_UNIVERSE:
        if sym not in existing:
            data.append({'symbol': sym, 'marketCap': 0, 'price': 0,
                         'sector': '', 'companyName': sym})
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
        time.sleep(0.05)
    return quotes

# ─── FAZ 3: Analist tahminleri ────────────────────────────────────────────────
def _estimate(sym):
    data = fetch(f'{BASE}/analyst-estimates/{sym}?limit=4&apikey={API_KEY}') or []
    return sym, data

def get_all_estimates(symbols, workers=12):
    log(f'Analist tahminleri: {len(symbols)} sembol ({workers} worker)...')
    result = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sym, data in (f.result() for f in as_completed(
                ex.submit(_estimate, s) for s in symbols)):
            result[sym] = data
    return result

# ─── PEG satırı hesabı ────────────────────────────────────────────────────────
def compute_row(raw, quote, estimates):
    sym   = raw['symbol']
    price = (quote or {}).get('price') or raw.get('price') or 0
    if not price:
        return None

    mcap  = raw.get('marketCap') or 0
    est   = estimates.get(sym, [])

    eps_now = eps_fwd = fwd_pe = None
    n_analysts = 0
    for e in est:
        yr = str(e.get('date',''))[:4]
        n  = max(e.get('numberAnalystEstimatedRevenue') or 0,
                 e.get('numberAnalystsEstimatedEps') or 0)
        if n > n_analysts: n_analysts = n
        avg = e.get('estimatedEpsAvg') or e.get('estimatedEpsHigh')
        if yr == str(CUR_YR):
            eps_now = avg
            if avg and avg > 0: fwd_pe = price / avg
        if yr == str(FWD_YR):
            eps_fwd = avg

    eps_growth = declining = None
    if eps_now is not None and eps_fwd is not None and eps_now != 0:
        eps_growth = ((eps_fwd - eps_now) / abs(eps_now)) * 100
        declining  = eps_growth < 0
    elif eps_now is not None and eps_now <= 0:
        declining = True

    peg = None
    if fwd_pe and eps_growth and eps_growth > 0:
        peg = fwd_pe / eps_growth

    yield_pct = (raw.get('dividendYield') or 0) * 100
    sector    = raw.get('sector','')

    return {
        'symbol':       sym,
        'company':      raw.get('companyName', sym),
        'sector':       sector,
        'price':        round(price, 2),
        'mcap_b':       round(mcap/1e9, 2),
        'fwd_pe':       round(fwd_pe, 1) if fwd_pe else None,
        'eps_growth_2y':round(eps_growth,1) if eps_growth is not None else None,
        'peg':          round(peg, 2) if peg else None,
        'declining_eps':bool(declining),
        'n_analysts':   n_analysts,
        'yield_pct':    round(yield_pct, 1),
        'k13_category': 'faydalanici' if sector in K13_FAYDALANICI else 'duyarli',
    }

# ─── FAZ 4a: Fundamenteller ───────────────────────────────────────────────────
def _fundamental(sym):
    rat = fetch(f'{BASE}/ratios-ttm/{sym}?apikey={API_KEY}') or [{}]
    km  = fetch(f'{BASE}/key-metrics-ttm/{sym}?apikey={API_KEY}') or [{}]
    r, k = (rat[0] if rat else {}), (km[0] if km else {})
    return sym, {
        'payout_pct': round((r.get('dividendPayoutRatioTTM') or 0)*100, 1),
        'de_ratio':   round(r.get('debtToEquityRatioTTM') or 0, 2),
        'roic':       round((k.get('returnOnInvestedCapitalTTM') or 0)*100, 1),
        'fcf_yield':  round((k.get('freeCashFlowYieldTTM') or 0)*100, 1),
        'npm':        round((r.get('netProfitMarginTTM') or 0)*100, 1),
    }

def get_fundamentals(symbols, workers=8):
    log(f'Fundamenteller: {len(symbols)} sembol ({workers} worker)...')
    result = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sym, data in (f.result() for f in as_completed(
                ex.submit(_fundamental, s) for s in symbols)):
            result[sym] = data
    return result

# ─── FAZ 4b: Teknik ───────────────────────────────────────────────────────────
def _technical(sym):
    hist = fetch(f'{BASE}/historical-price-eod/full/{sym}?limit=210&apikey={API_KEY}') or []
    rsi_data = fetch(f'{BASE}/technical-indicators/rsi/{sym}?periodLength=14&timeframe=1day&apikey={API_KEY}') or []

    price = sma50 = sma200 = rsi = mom1m = mom3m = mom6m = None
    if hist:
        closes = [d['close'] for d in hist if 'close' in d]
        if closes:
            price  = closes[0]
            if len(closes) >= 50:  sma50  = sum(closes[:50])  / 50
            if len(closes) >= 200: sma200 = sum(closes[:200]) / 200
            if len(closes) > 21:   mom1m  = (closes[0]-closes[21])/closes[21]*100
            if len(closes) > 63:   mom3m  = (closes[0]-closes[63])/closes[63]*100
            if len(closes) > 126:  mom6m  = (closes[0]-closes[126])/closes[126]*100

    if isinstance(rsi_data, list) and rsi_data:
        rsi = rsi_data[0].get('rsi')

    return sym, {
        'rsi':         rsi,
        'mom1m':       round(mom1m,1) if mom1m is not None else None,
        'mom3m':       round(mom3m,1) if mom3m is not None else None,
        'mom6m':       round(mom6m,1) if mom6m is not None else None,
        'above_sma50':  (price > sma50)  if price and sma50  else None,
        'above_sma200': (price > sma200) if price and sma200 else None,
        'golden_cross': (sma50 > sma200) if sma50 and sma200 else None,
    }

def get_technicals(symbols, workers=10):
    log(f'Teknik: {len(symbols)} sembol ({workers} worker)...')
    result = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sym, data in (f.result() for f in as_completed(
                ex.submit(_technical, s) for s in symbols)):
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
    elif yld > 9:         s -= 3   # yield trap uyarısı

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
    if rsi and rsi < 40: s += 1  # aşırı satım = alım fırsatı
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
    if pe < 0:   s -= 3
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

# ─── ÇIKTI / KONSOL ───────────────────────────────────────────────────────────
def print_results(scored, mode, n=40):
    th = THRESHOLDS[mode]
    labels = {True:'EKLE', None:'İZLE', False:'GEÇ'}
    print(f'\n{"#":>3} {"SYM":<6} {"Scr":>3} {"RSI":>4} {"EPS":>5} {"1M":>5} {"6M":>5} '
          f'{"50":>3} {"200":>3} {"ROIC":>5} {"FCF":>5} {"YLD":>5} {"K13":<14} Sektör')
    print('-'*105)
    for i, r in enumerate(scored[:n], 1):
        s50  = '✅' if r.get('above_sma50')  else '❌'
        s200 = '✅' if r.get('above_sma200') else '❌'
        sc = r['score']
        karar = 'EKLE' if sc >= th['ekle'] else ('İZLE' if sc >= th['izle'] else 'GEÇ')
        print(f"{i:>3} {r['symbol']:<6} {sc:>3} "
              f"{r.get('rsi') or 0:>4.0f} "
              f"{r.get('eps_growth_2y') or 0:>5.0f}% "
              f"{r.get('mom1m') or 0:>5.1f}% "
              f"{r.get('mom6m') or 0:>5.1f}% "
              f"{s50:>3} {s200:>3} "
              f"{r.get('roic') or 0:>5.1f}% "
              f"{r.get('fcf_yield') or 0:>5.1f}% "
              f"{r.get('yield_pct') or 0:>5.1f}% "
              f"{r.get('k13_category','?'):<14} "
              f"{r.get('sector','?')} [{karar}]")

# ─── ANA AKIŞ ─────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['balanced','dividend','aggressive','all'], default='all')
    p.add_argument('--workers', type=int, default=12)
    args = p.parse_args()

    modes = ['balanced','dividend','aggressive'] if args.mode == 'all' else [args.mode]
    t0 = time.time()

    # FAZ 1: Screener'lar — gerekli modlar için
    log('FAZ 1: Screener\'lar çekiliyor...')
    universe_map = {}  # sym → raw_row
    if 'balanced'   in modes: [universe_map.update({r['symbol']:r}) for r in screener_balanced()]
    if 'dividend'   in modes: [universe_map.update({r['symbol']:r}) for r in screener_dividend()]
    if 'aggressive' in modes: [universe_map.update({r['symbol']:r}) for r in screener_aggressive()]
    log(f'Toplam tekil sembol: {len(universe_map)}')

    # FAZ 2: Batch fiyatlar
    log('FAZ 2: Fiyatlar...')
    all_syms = list(universe_map.keys())
    quotes   = get_batch_quotes(all_syms)

    # FAZ 3: Analist tahminleri (tüm evren, bir kez)
    estimates = get_all_estimates(all_syms, workers=args.workers)

    # Ham satır hesabı
    log('Ham satır hesabı (PEG/EPS)...')
    all_rows = {}
    for sym in all_syms:
        r = compute_row(universe_map[sym], quotes.get(sym), estimates)
        if r:
            all_rows[sym] = r

    # FAZ 4: Teknik + fundamental için birleşik shortlist
    shortlist = {sym for sym, r in all_rows.items()
                 if any(passes_prefilter(r, m) for m in modes)}
    log(f'Shortlist (3 mod birleşimi): {len(shortlist)} sembol')
    fundamentals = get_fundamentals(list(shortlist), workers=args.workers)
    technicals   = get_technicals(list(shortlist),   workers=10)

    # FAZ 5: Mod bazlı skorlama + kayıt
    all_results = {}
    for mode in modes:
        log(f'=== Skorlama: {mode.upper()} ===')
        valid = [r for r in all_rows.values() if passes_prefilter(r, mode)]
        log(f'  Ön filtre geçen: {len(valid)}')

        scored = []
        for r in valid:
            sym  = r['symbol']
            fund = fundamentals.get(sym, {})
            tec  = technicals.get(sym, {})
            sc   = SCORE_FN[mode](r, fund, tec)
            row  = {**r, **fund,
                    'rsi':         tec.get('rsi'),
                    'mom1m':       tec.get('mom1m'),
                    'mom3m':       tec.get('mom3m'),
                    'mom6m':       tec.get('mom6m'),
                    'above_sma50': tec.get('above_sma50'),
                    'above_sma200':tec.get('above_sma200'),
                    'golden_cross':tec.get('golden_cross'),
                    'score':       sc,
                    'mode':        mode,
                    'yield_trap':  (fund.get('payout_pct') or 0) > 100}
            scored.append(row)

        scored.sort(key=lambda x: -x['score'])
        all_results[mode] = scored

        th    = THRESHOLDS[mode]
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

    # Geriye dönük uyumluluk: balanced → daily_full_scan.json
    if 'balanced' in modes:
        bal = all_results['balanced']
        compat = {
            'tarih':         TODAY,
            'son_guncelleme':NOW,
            'toplam_taranan':len(all_syms),
            'peg_filtreli':  len([r for r in all_rows.values()
                                  if r.get('peg') and r['peg'] <= 2.5]),
            'declining_eps': sum(1 for r in all_rows.values() if r.get('declining_eps')),
            'filtreler':     {'mod':'balanced','workers':args.workers},
            'sonuclar':      bal,
            'declining_list':[s for s,r in all_rows.items() if r.get('declining_eps')][:30],
        }
        with open('data/daily_full_scan.json','w',encoding='utf-8') as f:
            json.dump(compat, f, ensure_ascii=False, indent=2)

    t1 = time.time()
    log(f'=== TAMAMLANDI {(t1-t0)/60:.1f} dk ===')
    for mode in modes:
        sc = all_results[mode]
        th = THRESHOLDS[mode]
        log(f'  {mode:<12}: {len(sc):>3} skorlandı | '
            f'EKLE≥{th["ekle"]}:{sum(1 for s in sc if s["score"]>=th["ekle"])} | '
            f'İZLE≥{th["izle"]}:{sum(1 for s in sc if th["izle"]<=s["score"]<th["ekle"])}')

if __name__ == '__main__':
    main()
