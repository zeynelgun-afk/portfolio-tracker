#!/usr/bin/env python3
"""
full_universe_screener.py — Finzora AI v2
1000+ hisse akıllı tarayıcı: 4 kademeli eleme
  FAZ 1: FMP screener → 1000+ US hisse
  FAZ 2: Batch fiyat + analist tahminleri (hepsi)
  FAZ 3: PEG < MAX_PEG + min analist filtresi → ~top 200
  FAZ 4: Fundamenteller + TEKNİK (sadece top 200, rate limit yok)
  FAZ 5: K-kural skorlaması + sıralama

Süre: ~45-60 saniye | Çıktı: data/daily_full_scan.json
Kullanım:
  python3 scripts/full_universe_screener.py
  python3 scripts/full_universe_screener.py --sector Healthcare --max-peg 1.5
  python3 scripts/full_universe_screener.py --min-mcap 200000000 --max-peg 3.0
"""

import urllib.request, json, math, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_KEY = 'g1GFJZtV5rCP49UCir4WuP56VjhmA6F8'
BASE    = 'https://financialmodelingprep.com/stable'
TODAY   = datetime.now().strftime('%Y-%m-%d')
NOW     = datetime.now().isoformat()
CUR_YR  = 2026
FWD_YR  = 2028

K13_FAYDALANICI = {
    'Energy', 'Utilities', 'Healthcare',
    'Consumer Defensive', 'Communication Services', 'Financial Services'
}
K13_DUYARLI = {
    'Technology', 'Consumer Cyclical',
    'Industrials', 'Basic Materials', 'Real Estate'
}

# ─── Yardımcı ─────────────────────────────────────────────────────────────────

def fetch(url, timeout=12, retries=2):
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            if '429' in str(e) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                return None
    return None

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ─── FAZ 1: Sembol Listesi ─────────────────────────────────────────────────────

def get_universe(min_mcap, min_price, min_vol):
    log(f"Screener: mcap>${min_mcap/1e6:.0f}M fiyat>${min_price} vol>{min_vol:,}...")
    url = (f'{BASE}/company-screener?marketCapMoreThan={int(min_mcap)}'
           f'&priceMoreThan={min_price}&volumeMoreThan={min_vol}'
           f'&country=US&isActivelyTrading=true&limit=2000&apikey={API_KEY}')
    data = fetch(url, timeout=20) or []
    filtered = [
        d for d in data
        if not d.get('isEtf') and not d.get('isFund')
        and d.get('exchangeShortName') in ('NYSE', 'NASDAQ', 'AMEX')
        and d.get('symbol','').replace('-','').replace('.','').replace('^','').isalnum()
    ]
    log(f"Screener: {len(data)} → filtre: {len(filtered)} US hisse")
    return filtered

# ─── FAZ 2: Batch Fiyat ───────────────────────────────────────────────────────

def get_batch_quotes(symbols):
    log(f"Batch-quote: {len(symbols)} sembol...")
    quotes = {}
    for i in range(0, len(symbols), 100):
        batch = symbols[i:i+100]
        data = fetch(f'{BASE}/batch-quote?symbols={",".join(batch)}&apikey={API_KEY}') or []
        for q in data:
            quotes[q['symbol']] = q
        time.sleep(0.05)
    log(f"Fiyat: {len(quotes)} sembol")
    return quotes

# ─── FAZ 3: Paralel Analist Tahminleri ────────────────────────────────────────

def _single_estimate(sym):
    data = fetch(f'{BASE}/analyst-estimates?symbol={sym}&period=annual&apikey={API_KEY}') or []
    by_yr = {e['date'][:4]: e for e in data}
    return sym, {
        'eps_cur': by_yr.get(str(CUR_YR), {}).get('epsAvg'),
        'eps_fwd': by_yr.get(str(FWD_YR), {}).get('epsAvg'),
        'n':       by_yr.get(str(CUR_YR), {}).get('numAnalystsEps', 0),
    }

def get_all_estimates(symbols, workers=12):
    log(f"Analist tahminleri: {len(symbols)} sembol ({workers} worker)...")
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sym, d in [f.result() for f in as_completed({ex.submit(_single_estimate, s): s for s in symbols})]:
            out[sym] = d
    log(f"Tahmin: {sum(1 for v in out.values() if v['eps_cur'])}/{len(out)} veri var")
    return out

# ─── FAZ 4a: Fundamenteller (sadece kısa liste) ───────────────────────────────

def _single_fundamental(sym):
    rat = fetch(f'{BASE}/ratios-ttm?symbol={sym}&apikey={API_KEY}') or []
    km  = fetch(f'{BASE}/key-metrics-ttm?symbol={sym}&apikey={API_KEY}') or []
    r = rat[0] if rat else {}
    k = km[0] if km else {}
    return sym, {
        'yield':     (r.get('dividendYieldTTM')        or 0) * 100,
        'payout':    (r.get('dividendPayoutRatioTTM')   or 0) * 100,
        'de':         r.get('debtToEquityRatioTTM')     or 0,
        'npm':       (r.get('netProfitMarginTTM')       or 0) * 100,
        'roic':      (k.get('returnOnInvestedCapitalTTM') or 0) * 100,
        'fcf_yield': (k.get('freeCashFlowYieldTTM')    or 0) * 100,
        'roe':       (k.get('returnOnEquityTTM')        or 0) * 100,
    }

def get_fundamentals(symbols, workers=8):
    log(f"Fundamenteller: {len(symbols)} sembol...")
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sym, d in [f.result() for f in as_completed({ex.submit(_single_fundamental, s): s for s in symbols})]:
            out[sym] = d
    log(f"Fundamental: {len(out)} sembol")
    return out

# ─── FAZ 4b: Teknik (sadece kısa liste, rate limit yok) ───────────────────────

def _single_technical(sym):
    hist = fetch(f'{BASE}/historical-price-eod/full?symbol={sym}&apikey={API_KEY}')
    rsi_d = fetch(f'{BASE}/technical-indicators/rsi?symbol={sym}&periodLength=14&timeframe=1day&apikey={API_KEY}')
    
    price = sma50 = sma200 = rsi = None
    
    if isinstance(hist, list) and len(hist) >= 50:
        closes = [h['close'] for h in hist[:210]]
        price  = closes[0]
        sma50  = sum(closes[:50]) / 50
        sma200 = sum(closes[:200]) / 200 if len(closes) >= 200 else None
        # RSI manuel (yedek)
        g = [max(closes[i-1]-closes[i],0) for i in range(1,15)]
        l = [max(closes[i]-closes[i-1],0) for i in range(1,15)]
        ag, al = sum(g)/14, sum(l)/14
        rsi = 100.0 if al==0 else 100.0 - 100.0/(1.0+ag/al)
    
    # FMP RSI (daha hassas, öncelikli)
    if isinstance(rsi_d, list) and rsi_d and rsi_d[0].get('rsi'):
        rsi = rsi_d[0]['rsi']
    
    return sym, {
        'price':      price,
        'rsi':        rsi,
        'sma50':      sma50,
        'sma200':     sma200,
        'above_sma50':  (price > sma50)  if price and sma50  else None,
        'above_sma200': (price > sma200) if price and sma200 else None,
    }

def get_technicals(symbols, workers=6):
    log(f"Teknik ({len(symbols)} sembol, {workers} worker — rate limit korumalı)...")
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sym, d in [f.result() for f in as_completed({ex.submit(_single_technical, s): s for s in symbols})]:
            out[sym] = d
    log(f"Teknik: {len([v for v in out.values() if v.get('rsi')])}/{len(out)} RSI alındı")
    return out

# ─── FAZ 5: PEG Hesabı + Ön Filtre ───────────────────────────────────────────

def compute_peg(universe, quotes, estimates, min_analysts):
    rows = []
    for item in universe:
        sym  = item['symbol']
        q    = quotes.get(sym, {})
        est  = estimates.get(sym, {})
        price = q.get('price', 0)
        if not price: continue

        eps_c = est.get('eps_cur')
        eps_f = est.get('eps_fwd')
        n     = est.get('n', 0)
        if n < min_analysts: continue

        fwd_pe = eps_growth = peg = None
        declining = False

        if eps_c and eps_c > 0:
            fwd_pe = price / eps_c

        if eps_c and eps_f:
            if eps_c > 0 and eps_f > 0:
                eps_growth = (math.pow(eps_f / eps_c, 0.5) - 1) * 100
                if fwd_pe and eps_growth > 0:
                    peg = fwd_pe / eps_growth
            elif eps_f < eps_c:
                declining = True

        rows.append({
            'symbol': sym, 'company': item.get('companyName',''),
            'sector': item.get('sector','Unknown'),
            'price': round(price, 2),
            'mcap_b': round(item.get('marketCap',0)/1e9, 1),
            'fwd_pe': round(fwd_pe,1) if fwd_pe else None,
            'eps_growth_2y': round(eps_growth,1) if eps_growth else None,
            'peg': round(peg,2) if peg else None,
            'declining_eps': declining,
            'n_analysts': n,
        })
    return rows

# ─── FAZ 6: Nihai Skor ────────────────────────────────────────────────────────

def apply_scores(rows, fundamentals, technicals):
    K13_F = K13_FAYDALANICI
    out = []
    for r in rows:
        sym  = r['symbol']
        fun  = fundamentals.get(sym, {})
        tec  = technicals.get(sym, {})
        sector = r['sector']

        peg    = r.get('peg')
        fwd_pe = r.get('fwd_pe')
        eps_g  = r.get('eps_growth_2y')
        rsi    = tec.get('rsi')
        sma50  = tec.get('sma50')
        sma200 = tec.get('sma200')
        price  = tec.get('price') or r['price']

        above_50  = tec.get('above_sma50')
        above_200 = tec.get('above_sma200')
        k04_pass     = above_50 is True
        k04_oversold = (rsi and rsi < 35) and not k04_pass

        k13 = ('faydalanici' if sector in K13_F
                else 'duyarli' if sector in K13_DUYARLI else 'notr')

        score = 0
        if peg:
            score += 5 if peg<0.8 else 4 if peg<1.0 else 3 if peg<1.5 else 2 if peg<2.0 else 1
        if fwd_pe:
            score += 3 if fwd_pe<12 else 2 if fwd_pe<18 else 1 if fwd_pe<25 else 0
        if eps_g and eps_g>0:
            score += 3 if eps_g>20 else 2 if eps_g>10 else 1 if eps_g>5 else 0
        if k04_pass:    score += 2
        if above_200:   score += 1
        roic = fun.get('roic', 0)
        fcf  = fun.get('fcf_yield', 0)
        npm  = fun.get('npm', 0)
        if roic > 15:   score += 2
        elif roic > 8:  score += 1
        if fcf > 8:     score += 2
        elif fcf > 4:   score += 1
        if npm > 10:    score += 1
        if r['n_analysts'] >= 10: score += 1

        out.append({
            **r,
            'yield_pct':  round(fun.get('yield',0), 2),
            'payout_pct': round(fun.get('payout',0), 0),
            'de_ratio':   round(fun.get('de',0), 1),
            'roic':       round(roic, 1),
            'fcf_yield':  round(fcf, 1),
            'npm':        round(npm, 1),
            'rsi':        round(rsi,1) if rsi else None,
            'above_sma50':  above_50,
            'above_sma200': above_200,
            'k04_pass':    k04_pass,
            'k04_oversold':k04_oversold,
            'k13_category': k13,
            'score': score,
        })
    return out

# ─── ANA ──────────────────────────────────────────────────────────────────────

def run(args):
    t0 = time.time()
    log("=== FULL UNIVERSE SCREENER v2 ===")

    # Faz 1
    universe = get_universe(args.min_mcap, args.min_price, args.min_vol)
    if args.sector:
        universe = [u for u in universe if args.sector.lower() in u.get('sector','').lower()]
        log(f"Sektör filtresi '{args.sector}': {len(universe)} hisse")
    symbols = [u['symbol'] for u in universe]

    # Faz 2
    quotes = get_batch_quotes(symbols)
    symbols = [s for s in symbols if quotes.get(s, {}).get('price', 0) > args.min_price]
    log(f"Fiyat filtresi: {len(symbols)} sembol")

    # Faz 3
    estimates = get_all_estimates(symbols, workers=args.workers)

    # Ön PEG hesabı (henüz teknik/fundamental yok)
    all_rows = compute_peg(universe, quotes, estimates, args.min_analysts)
    valid_peg = [r for r in all_rows if r['peg'] and r['peg'] <= args.max_peg and not r['declining_eps']]
    declining  = [r for r in all_rows if r['declining_eps']]
    valid_peg.sort(key=lambda x: x['peg'])
    log(f"PEG≤{args.max_peg} büyüyen: {len(valid_peg)} | Düşen: {len(declining)}")

    # AKILLI FİLTRE: Teknik + fundamental sadece top N için
    top_n = min(len(valid_peg), 200)
    shortlist_syms = [r['symbol'] for r in valid_peg[:top_n]]
    log(f"Shortlist: ilk {top_n} hisse için teknik+fundamental çekiliyor...")

    # Faz 4a: Fundamenteller
    fundamentals = get_fundamentals(shortlist_syms, workers=args.workers)

    # Faz 4b: Teknik (sınırlı, rate limit yok)
    technicals = get_technicals(shortlist_syms, workers=6)

    # Faz 5+6: Skor
    shortlist_rows = [r for r in valid_peg[:top_n]]
    scored = apply_scores(shortlist_rows, fundamentals, technicals)
    scored.sort(key=lambda x: -(x['score']*10 - (x['peg'] or 99)*2))

    t1 = time.time()
    log(f"=== TAMAMLANDI {t1-t0:.0f}s | {len(valid_peg)} PEG geçer | {len(scored)} skorlanmış ===")

    # Kaydet
    output = {
        'tarih': TODAY, 'son_guncelleme': NOW,
        'toplam_taranan': len(symbols),
        'peg_filtreli': len(valid_peg),
        'declining_eps': len(declining),
        'filtreler': vars(args),
        'sonuclar': scored,
        'declining_list': [r['symbol'] for r in declining[:30]],
    }
    with open('data/daily_full_scan.json', 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    log(f"Kaydedildi: {len(scored)} hisse → data/daily_full_scan.json")

    # Terminal
    K13_F = K13_FAYDALANICI
    print(f"\n{'#':>3} | {'SYM':5} | {'SEKTÖR':22} | {'P/E':>6} | {'EPS%':>6} | {'PEG':>5} | {'RSI':>4} | {'K04':>3} | {'S200':>4} | {'ROIC':>5} | {'FCF':>5} | {'YLD':>5} | SKOR | K13")
    print("─" * 120)
    for i, r in enumerate(scored[:60], 1):
        k13 = '🟢' if r['sector'] in K13_F else '🔴'
        k04 = '✅' if r['k04_pass'] else '⚠️' if r['k04_oversold'] else '❌'
        s200 = '✅' if r.get('above_sma200') else '❌'
        print(f"{i:>3} | {r['symbol']:5} | {r['sector'][:22]:22} | "
              f"{r['fwd_pe']:.0f}x" if r['fwd_pe'] else f"{'?':>6}" , end='')
        fpe  = f"{r['fwd_pe']:.0f}x"  if r['fwd_pe'] else "?"
        eg   = f"{r['eps_growth_2y']:+.0f}%" if r['eps_growth_2y'] else "?"
        pg   = f"{r['peg']:.2f}"        if r['peg']   else "?"
        rsi  = f"{r['rsi']:.0f}"        if r['rsi']   else "?"
        roic = f"{r['roic']:.0f}%"      if r.get('roic') else "?"
        fcf  = f"{r['fcf_yield']:.0f}%" if r.get('fcf_yield') else "?"
        yld  = f"{r['yield_pct']:.1f}%" if r.get('yield_pct') else "0%"
        print(f"\r{i:>3} | {r['symbol']:5} | {r['sector'][:22]:22} | {fpe:>6} | {eg:>6} | {pg:>5} | {rsi:>4} | {k04:>3} | {s200:>4} | {roic:>5} | {fcf:>5} | {yld:>5} | {r['score']:>4} | {k13}")
    return output

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--min-mcap',     type=float, default=200_000_000)
    p.add_argument('--min-price',    type=float, default=10)
    p.add_argument('--min-vol',      type=int,   default=200_000)
    p.add_argument('--min-analysts', type=int,   default=3)
    p.add_argument('--max-peg',      type=float, default=2.5)
    p.add_argument('--sector',       type=str,   default='')
    p.add_argument('--workers',      type=int,   default=12)
    run(p.parse_args())
