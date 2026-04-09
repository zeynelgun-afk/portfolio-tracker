#!/usr/bin/env python3
"""
full_universe_screener.py — Finzora AI
1000+ hisse tarayıcı: Forward P/E + PEG + Teknik + K-Kural filtreleri
Çalışma süresi: ~3-5 dakika
Çıktı: data/daily_full_scan.json
Kullanım: python3 scripts/full_universe_screener.py [--sector SECTOR] [--min-peg 0.5] [--max-peg 2.0]
"""

import urllib.request, json, math, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_KEY = 'g1GFJZtV5rCP49UCir4WuP56VjhmA6F8'
BASE = 'https://financialmodelingprep.com/stable'
NOW = datetime.now().isoformat()
TODAY = datetime.now().strftime('%Y-%m-%d')
CUR_YEAR = 2026
FWD2_YEAR = 2028

# K-13 v4.1 — Jeopolitik/Savaş kriz tablosu
K13_FAYDALANICI = {
    'Energy','Utilities','Healthcare','Consumer Defensive',
    'Communication Services','Financial Services'
}
K13_DUYARLI = {
    'Technology','Consumer Cyclical','Industrials','Basic Materials','Real Estate'
}

# ─── Yardımcı ─────────────────────────────────────────────────────────────────

def fetch(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except:
        return None

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ─── FAZ 1: Sembol Listesi ─────────────────────────────────────────────────────

def get_universe(min_mcap=500_000_000, min_price=10, min_vol=300_000):
    log(f"Screener çekiliyor (mcap>${min_mcap/1e9:.0f}B, fiyat>${min_price}, vol>{min_vol:,})...")
    url = (f'{BASE}/company-screener?marketCapMoreThan={min_mcap}'
           f'&priceMoreThan={min_price}&volumeMoreThan={min_vol}'
           f'&country=US&isActivelyTrading=true&limit=2000&apikey={API_KEY}')
    data = fetch(url, timeout=20) or []
    
    # Sadece US borsaları, ETF/Fund değil
    filtered = [
        d for d in data
        if not d.get('isEtf') and not d.get('isFund')
        and d.get('exchangeShortName') in ('NYSE','NASDAQ','AMEX')
        and d.get('symbol','').replace('-','').replace('.','').isalnum()
    ]
    
    log(f"Screener: {len(data)} hisse → filtre sonrası {len(filtered)} US hisse")
    return filtered

# ─── FAZ 2: Batch Fiyat ───────────────────────────────────────────────────────

def get_batch_quotes(symbols):
    log(f"Batch-quote çekiliyor ({len(symbols)} sembol)...")
    quotes = {}
    chunk = 100
    for i in range(0, len(symbols), chunk):
        batch = symbols[i:i+chunk]
        url = f'{BASE}/batch-quote?symbols={",".join(batch)}&apikey={API_KEY}'
        data = fetch(url) or []
        for q in data:
            quotes[q['symbol']] = q
        time.sleep(0.05)
    log(f"Fiyat alınan: {len(quotes)} sembol")
    return quotes

# ─── FAZ 3: Paralel Analist Tahminleri ────────────────────────────────────────

def get_single_estimates(sym):
    url = f'{BASE}/analyst-estimates?symbol={sym}&period=annual&apikey={API_KEY}'
    data = fetch(url) or []
    by_year = {e['date'][:4]: e for e in data}
    eps_26 = by_year.get(str(CUR_YEAR), {}).get('epsAvg')
    eps_28 = by_year.get(str(FWD2_YEAR), {}).get('epsAvg')
    n = by_year.get(str(CUR_YEAR), {}).get('numAnalystsEps', 0)
    return sym, eps_26, eps_28, n

def get_all_estimates(symbols, workers=10):
    log(f"Analist tahminleri çekiliyor ({len(symbols)} sembol, {workers} worker)...")
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(get_single_estimates, s): s for s in symbols}
        for f in as_completed(futures):
            sym, eps_26, eps_28, n = f.result()
            results[sym] = {'eps_26': eps_26, 'eps_28': eps_28, 'n_analysts': n}
    has_data = sum(1 for v in results.values() if v['eps_26'])
    log(f"Tahmin alınan: {has_data}/{len(symbols)} sembol")
    return results

# ─── FAZ 4: Paralel Fundamenteller ────────────────────────────────────────────

def get_single_fundamentals(sym):
    rat = fetch(f'{BASE}/ratios-ttm?symbol={sym}&apikey={API_KEY}') or []
    km  = fetch(f'{BASE}/key-metrics-ttm?symbol={sym}&apikey={API_KEY}') or []
    r = rat[0] if rat else {}
    k = km[0] if km else {}
    return sym, {
        'yield_pct': (r.get('dividendYieldTTM') or 0) * 100,
        'payout_pct': (r.get('dividendPayoutRatioTTM') or 0) * 100,
        'de_ratio': r.get('debtToEquityRatioTTM') or 0,
        'roic': (k.get('returnOnInvestedCapitalTTM') or 0) * 100,
        'fcf_yield': (k.get('freeCashFlowYieldTTM') or 0) * 100,
    }

def get_all_fundamentals(symbols, workers=10):
    log(f"Fundamenteller çekiliyor ({len(symbols)} sembol)...")
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(get_single_fundamentals, s): s for s in symbols}
        for f in as_completed(futures):
            sym, data = f.result()
            results[sym] = data
    log(f"Fundamental alınan: {len(results)} sembol")
    return results

# ─── FAZ 5: Paralel Teknik Göstergeler ────────────────────────────────────────

def get_single_technical(sym):
    rsi_d = fetch(f'{BASE}/technical-indicators/rsi?symbol={sym}&periodLength=14&timeframe=1day&apikey={API_KEY}') or []
    hist  = fetch(f'{BASE}/historical-price-eod/full?symbol={sym}&apikey={API_KEY}') or []
    
    rsi = rsi_d[0]['rsi'] if rsi_d else None
    price = sma50 = sma200 = None
    
    if hist:
        closes = [h['close'] for h in hist[:210]]
        price = closes[0] if closes else None
        sma50 = sum(closes[:50])/50 if len(closes) >= 50 else None
        sma200 = sum(closes[:200])/200 if len(closes) >= 200 else None
    
    return sym, {'rsi': rsi, 'sma50': sma50, 'sma200': sma200, 'price_confirm': price}

def get_all_technicals(symbols, workers=8):
    log(f"Teknik göstergeler hesaplanıyor ({len(symbols)} sembol)...")
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(get_single_technical, s): s for s in symbols}
        for f in as_completed(futures):
            sym, data = f.result()
            results[sym] = data
    log(f"Teknik alınan: {len(results)} sembol")
    return results

# ─── FAZ 6: Hesap ve Sıralama ─────────────────────────────────────────────────

def compute_scores(universe_data, quotes, estimates, fundamentals, technicals):
    results = []
    
    for item in universe_data:
        sym = item['symbol']
        q   = quotes.get(sym, {})
        est = estimates.get(sym, {})
        fun = fundamentals.get(sym, {})
        tec = technicals.get(sym, {})
        
        price  = q.get('price') or tec.get('price_confirm') or 0
        mcap   = item.get('marketCap', 0)
        sector = item.get('sector', 'Unknown')
        
        if not price: continue
        
        # Forward P/E + PEG
        eps_26 = est.get('eps_26')
        eps_28 = est.get('eps_28')
        n_an   = est.get('n_analysts', 0)
        
        fwd_pe = eps_growth = peg = None
        declining = False
        
        if eps_26 and eps_26 > 0:
            fwd_pe = price / eps_26
        
        if eps_26 and eps_28:
            if eps_26 > 0 and eps_28 > 0:
                eps_growth = (math.pow(eps_28 / eps_26, 0.5) - 1) * 100
                if fwd_pe and eps_growth > 0:
                    peg = fwd_pe / eps_growth
            elif eps_28 < eps_26:
                declining = True
        
        # Teknik
        rsi    = tec.get('rsi')
        sma50  = tec.get('sma50')
        sma200 = tec.get('sma200')
        
        above_sma50  = price > sma50  if sma50  else None
        above_sma200 = price > sma200 if sma200 else None
        
        # K-04
        k04_pass = above_sma50 is True
        k04_oversold = (rsi and rsi < 35) if not k04_pass else False
        
        # K-13
        k13_cat = ('faydalanici' if sector in K13_FAYDALANICI
                   else 'duyarli'    if sector in K13_DUYARLI
                   else 'notr')
        
        # Skor hesabı (0-20)
        score = 0
        if peg:
            if peg < 0.8: score += 5
            elif peg < 1.0: score += 4
            elif peg < 1.5: score += 3
            elif peg < 2.0: score += 2
            elif peg < 2.5: score += 1
        if fwd_pe:
            if fwd_pe < 12: score += 3
            elif fwd_pe < 18: score += 2
            elif fwd_pe < 25: score += 1
        if eps_growth and eps_growth > 0:
            if eps_growth > 20: score += 3
            elif eps_growth > 10: score += 2
            elif eps_growth > 5: score += 1
        if k04_pass: score += 2
        if above_sma200: score += 1
        if fun.get('roic',0) > 15: score += 2
        elif fun.get('roic',0) > 8: score += 1
        if fun.get('fcf_yield',0) > 8: score += 2
        elif fun.get('fcf_yield',0) > 4: score += 1
        if n_an >= 10: score += 1
        
        results.append({
            'symbol': sym,
            'company': item.get('companyName',''),
            'sector': sector,
            'price': round(price, 2),
            'mcap_b': round(mcap/1e9, 1),
            'fwd_pe': round(fwd_pe, 1) if fwd_pe else None,
            'eps_growth_2y': round(eps_growth, 1) if eps_growth else None,
            'peg': round(peg, 2) if peg else None,
            'declining_eps': declining,
            'n_analysts': n_an,
            'yield_pct': round(fun.get('yield_pct',0), 2),
            'payout_pct': round(fun.get('payout_pct',0), 0),
            'de_ratio': round(fun.get('de_ratio',0), 1),
            'roic': round(fun.get('roic',0), 1),
            'fcf_yield': round(fun.get('fcf_yield',0), 1),
            'rsi': round(rsi, 1) if rsi else None,
            'above_sma50': above_sma50,
            'above_sma200': above_sma200,
            'k04_pass': k04_pass,
            'k04_oversold': k04_oversold,
            'k13_category': k13_cat,
            'score': score,
        })
    
    results.sort(key=lambda x: x['peg'] if x['peg'] else 999)
    return results

# ─── ANA FONKSİYON ────────────────────────────────────────────────────────────

def run(args):
    t_start = time.time()
    log("=== FULL UNIVERSE SCREENER BAŞLIYOR ===")
    
    # FAZ 1: Sembol listesi
    universe = get_universe(
        min_mcap=args.min_mcap,
        min_price=args.min_price,
        min_vol=args.min_vol
    )
    
    # Sektör filtresi (opsiyonel)
    if args.sector:
        universe = [u for u in universe if args.sector.lower() in u.get('sector','').lower()]
        log(f"Sektör filtresi '{args.sector}': {len(universe)} hisse")
    
    symbols = [u['symbol'] for u in universe]
    sym_set = set(symbols)
    
    # FAZ 2: Fiyatlar
    quotes = get_batch_quotes(symbols)
    
    # Fiyat filtresi — geçersizleri çıkar
    symbols = [s for s in symbols if s in quotes and quotes[s].get('price',0) > args.min_price]
    log(f"Fiyat filtresi sonrası: {len(symbols)} sembol")
    
    # FAZ 3: Analist tahminleri
    estimates = get_all_estimates(symbols, workers=args.workers)
    
    # Analist filtresi — en az 3 analist
    symbols_with_est = [s for s in symbols 
                        if estimates.get(s,{}).get('eps_26') 
                        and estimates.get(s,{}).get('n_analysts',0) >= args.min_analysts]
    log(f"Min {args.min_analysts} analist filtresi: {len(symbols_with_est)} sembol")
    
    # FAZ 4: Fundamenteller (sadece tahmin olanlar)
    fundamentals = get_all_fundamentals(symbols_with_est, workers=args.workers)
    
    # FAZ 5: Teknikler
    technicals = get_all_technicals(symbols_with_est, workers=args.workers)
    
    # FAZ 6: Skor hesabı
    universe_filtered = [u for u in universe if u['symbol'] in set(symbols_with_est)]
    results = compute_scores(universe_filtered, quotes, estimates, fundamentals, technicals)
    
    # Son filtreler
    valid = [r for r in results if not r['declining_eps'] and r['peg'] and r['peg'] <= args.max_peg]
    decline = [r for r in results if r['declining_eps']]
    no_growth = [r for r in results if not r['peg'] and not r['declining_eps']]
    
    t_end = time.time()
    log(f"=== TAMAMLANDI: {t_end-t_start:.0f}s ===")
    log(f"Büyüyen & PEG≤{args.max_peg}: {len(valid)} | Düşen: {len(decline)} | Veri yok: {len(no_growth)}")
    
    # Kaydet
    output = {
        'tarih': TODAY,
        'son_guncelleme': NOW,
        'toplam_taranan': len(symbols),
        'tahmin_olan': len(symbols_with_est),
        'buyuyen_peg_filtreli': len(valid),
        'dusurus': len(decline),
        'filtreler': {
            'min_mcap_b': args.min_mcap/1e9,
            'min_price': args.min_price,
            'min_vol': args.min_vol,
            'min_analysts': args.min_analysts,
            'max_peg': args.max_peg
        },
        'sonuclar': valid[:200],   # İlk 200 kaydet
        'declining_eps': [r['symbol'] for r in decline],
    }
    
    with open('data/daily_full_scan.json', 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    log(f"Kaydedildi: data/daily_full_scan.json ({len(valid)} satır)")
    
    # Terminal özet
    print(f"\n{'SIRA':>4} | {'SYM':5} | {'SEKTÖR':22} | {'FWD P/E':>8} | {'2Y EPS%':>8} | {'PEG':>6} | {'RSI':>5} | {'K04':>4} | {'SKOR':>5}")
    print("-" * 90)
    for i, r in enumerate(valid[:50], 1):
        fpe = f"{r['fwd_pe']:.1f}x" if r['fwd_pe'] else "N/A"
        eg  = f"{r['eps_growth_2y']:+.1f}%" if r['eps_growth_2y'] else "N/A"
        pg  = f"{r['peg']:.2f}"
        rsi = f"{r['rsi']:.0f}" if r['rsi'] else "?"
        k04 = "✅" if r['k04_pass'] else "⚠️" if r['k04_oversold'] else "❌"
        sector_short = r['sector'][:22]
        print(f"{i:>4} | {r['symbol']:5} | {sector_short:22} | {fpe:>8} | {eg:>8} | {pg:>6} | {rsi:>5} | {k04:>4} | {r['score']:>5}")
    
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Full Universe Stock Screener')
    parser.add_argument('--min-mcap', type=float, default=500_000_000, help='Min market cap (default 500M)')
    parser.add_argument('--min-price', type=float, default=10, help='Min stock price (default 10)')
    parser.add_argument('--min-vol', type=int, default=300_000, help='Min volume (default 300K)')
    parser.add_argument('--min-analysts', type=int, default=3, help='Min analyst count (default 3)')
    parser.add_argument('--max-peg', type=float, default=2.5, help='Max PEG ratio (default 2.5)')
    parser.add_argument('--sector', type=str, default='', help='Sektör filtresi (opsiyonel)')
    parser.add_argument('--workers', type=int, default=10, help='Paralel worker sayısı (default 10)')
    args = parser.parse_args()
    run(args)
