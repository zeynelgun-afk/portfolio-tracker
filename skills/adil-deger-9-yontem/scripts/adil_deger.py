#!/usr/bin/env python3
"""
Adil Değer - 9 Yöntem × 3 Senaryo Hesaplayıcı v2.0
Finzora AI v3.7.2 metodolojisi

v2.0 Değişiklikleri:
- k_e %15 cap + ROE < k_e fallback (Residual Income Model)
- CV ≥ %50 kırmızı uyarı, ≥ %35 turuncu uyarı
- Forward P/E outlier filtreleme (EPS_FWD/EPS_TTM > 2.5x)
- AI mega-cap auto-detection (market cap > $300B + 1y return > %100 + semi)
- Analist konsensüs entegrasyonu (FMP price-target)
- Dual-track raporlama (Mevcut vs Beklenti bazlı)
- Otomatik karar matrisi
"""

import requests
import json
import sys
import statistics
from datetime import datetime

API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
BASE = "https://financialmodelingprep.com/stable"


def fetch(endpoint, params=None, timeout=30):
    p = {"apikey": API_KEY}
    if params:
        p.update(params)
    try:
        r = requests.get(f"{BASE}/{endpoint}", params=p, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"FMP hata: {e}", file=sys.stderr)
        return None


def safe_get(d, key, default=0):
    v = d.get(key) if d else None
    return v if v is not None else default


# =============================================================================
# SEKTÖR TESPİTİ + AI MEGA-CAP DETECTION
# =============================================================================

def detect_sector(profile, market_cap, year_low, current_price):
    sector = (profile.get('sector') or '').lower()
    industry = (profile.get('industry') or '').lower()
    desc = (profile.get('description') or '').lower()
    
    # AI Mega-Cap detection (yeni v2)
    is_ai_megacap = False
    if market_cap and market_cap > 300e9:
        if year_low and year_low > 0:
            yearly_return = (current_price - year_low) / year_low
            if yearly_return > 1.0:  # %100+ getiri
                if 'semiconduct' in industry or sector == 'technology':
                    is_ai_megacap = True
    
    if 'semiconduct' in industry:
        if any(k in desc for k in ['osat', 'packaging', 'assembly and test']):
            return ('semicon_osat', is_ai_megacap)
        if 'equipment' in industry or any(k in desc for k in ['lithography', 'fabrication equipment']):
            return ('semicon_equipment', is_ai_megacap)
        return ('semicon_design', is_ai_megacap)
    
    if sector == 'technology':
        if 'software' in industry:
            return ('tech_software', is_ai_megacap)
        return ('tech_hardware', is_ai_megacap)
    
    if sector == 'financial services':
        if 'bank' in industry:
            return ('financials_bank', False)
        if 'insurance' in industry:
            return ('financials_insurance', False)
        return ('financials_other', False)
    
    if sector == 'healthcare':
        if 'biotech' in industry or 'biotechnology' in industry:
            return ('healthcare_biotech', False)
        if 'drug' in industry or 'pharma' in industry:
            return ('healthcare_pharma', False)
        return ('healthcare_devices', False)
    
    if sector == 'consumer defensive':
        return ('consumer_staples', False)
    if sector == 'consumer cyclical':
        return ('consumer_discretionary', False)
    
    if sector == 'industrials':
        return ('industrials', False)
    if sector == 'energy':
        return ('energy', False)
    if sector == 'real estate':
        return ('reits', False)
    if sector == 'utilities':
        return ('utilities', False)
    if sector == 'communication services':
        return ('communication', is_ai_megacap)
    
    return ('generic', False)


SECTOR_MULTIPLES = {
    'tech_software':       {'pe': 28, 'fwd_pe': 24, 'ev_ebit': 22, 'ev_ebitda': 18, 'ev_rev': 6.0, 'p_fcf': 28, 'roe_target': 0.20, 'g_high': 0.12},
    'tech_hardware':       {'pe': 22, 'fwd_pe': 20, 'ev_ebit': 17, 'ev_ebitda': 13, 'ev_rev': 3.5, 'p_fcf': 22, 'roe_target': 0.18, 'g_high': 0.08},
    'semicon_design':      {'pe': 28, 'fwd_pe': 24, 'ev_ebit': 22, 'ev_ebitda': 18, 'ev_rev': 7.0, 'p_fcf': 30, 'roe_target': 0.25, 'g_high': 0.15},
    'semicon_osat':        {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 2.0, 'p_fcf': 22, 'roe_target': 0.15, 'g_high': 0.08},
    'semicon_equipment':   {'pe': 26, 'fwd_pe': 22, 'ev_ebit': 20, 'ev_ebitda': 16, 'ev_rev': 6.0, 'p_fcf': 26, 'roe_target': 0.22, 'g_high': 0.12},
    'financials_bank':     {'pe': 11, 'fwd_pe': 10, 'ev_ebit': 9, 'ev_ebitda': 8, 'ev_rev': 3.0, 'p_fcf': 12, 'roe_target': 0.12, 'g_high': 0.05},
    'financials_insurance':{'pe': 12, 'fwd_pe': 11, 'ev_ebit': 10, 'ev_ebitda': 9, 'ev_rev': 2.0, 'p_fcf': 12, 'roe_target': 0.12, 'g_high': 0.05},
    'financials_other':    {'pe': 14, 'fwd_pe': 13, 'ev_ebit': 12, 'ev_ebitda': 10, 'ev_rev': 3.0, 'p_fcf': 14, 'roe_target': 0.13, 'g_high': 0.06},
    'healthcare_pharma':   {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 15, 'ev_ebitda': 12, 'ev_rev': 4.0, 'p_fcf': 20, 'roe_target': 0.18, 'g_high': 0.06},
    'healthcare_biotech':  {'pe': 25, 'fwd_pe': 22, 'ev_ebit': 20, 'ev_ebitda': 16, 'ev_rev': 6.0, 'p_fcf': 25, 'roe_target': 0.15, 'g_high': 0.12},
    'healthcare_devices':  {'pe': 24, 'fwd_pe': 20, 'ev_ebit': 18, 'ev_ebitda': 15, 'ev_rev': 5.0, 'p_fcf': 24, 'roe_target': 0.18, 'g_high': 0.08},
    'consumer_staples':    {'pe': 20, 'fwd_pe': 18, 'ev_ebit': 16, 'ev_ebitda': 13, 'ev_rev': 2.5, 'p_fcf': 22, 'roe_target': 0.18, 'g_high': 0.05},
    'consumer_discretionary':{'pe':18,'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 2.0, 'p_fcf': 20, 'roe_target': 0.15, 'g_high': 0.07},
    'industrials':         {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 2.0, 'p_fcf': 20, 'roe_target': 0.15, 'g_high': 0.06},
    'energy':              {'pe': 12, 'fwd_pe': 10, 'ev_ebit': 8, 'ev_ebitda': 6, 'ev_rev': 1.5, 'p_fcf': 12, 'roe_target': 0.12, 'g_high': 0.03},
    'reits':               {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 16, 'ev_rev': 7.0, 'p_fcf': 18, 'roe_target': 0.10, 'g_high': 0.04},
    'utilities':           {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 3.0, 'p_fcf': 18, 'roe_target': 0.10, 'g_high': 0.04},
    'communication':       {'pe': 20, 'fwd_pe': 18, 'ev_ebit': 15, 'ev_ebitda': 10, 'ev_rev': 3.0, 'p_fcf': 20, 'roe_target': 0.15, 'g_high': 0.06},
    'generic':             {'pe': 20, 'fwd_pe': 17, 'ev_ebit': 15, 'ev_ebitda': 12, 'ev_rev': 2.5, 'p_fcf': 22, 'roe_target': 0.15, 'g_high': 0.07},
}

# AI MEGA-CAP boğa primi
AI_MEGACAP_BULL_PREMIUM = {
    'pe': 1.50, 'fwd_pe': 1.45, 'ev_ebit': 1.45, 'ev_ebitda': 1.40, 'ev_rev': 1.55, 'p_fcf': 1.50,
}

REGIME_ADJ = {
    'bear':   {'pe': 0.70, 'fwd_pe': 0.72, 'ev_ebit': 0.72, 'ev_ebitda': 0.75, 'ev_rev': 0.65, 'p_fcf': 0.70, 'graham_k': 18, 'wacc': 0.12, 'g_high_adj': -0.05, 'g_term': 0.02, 'k_e_adj': 0.02, 'g_pb_adj': -0.01},
    'normal': {'pe': 1.00, 'fwd_pe': 1.00, 'ev_ebit': 1.00, 'ev_ebitda': 1.00, 'ev_rev': 1.00, 'p_fcf': 1.00, 'graham_k': 22.5, 'wacc': 0.10, 'g_high_adj': 0.00, 'g_term': 0.03, 'k_e_adj': 0.00, 'g_pb_adj': 0.00},
    'bull':   {'pe': 1.25, 'fwd_pe': 1.22, 'ev_ebit': 1.22, 'ev_ebitda': 1.20, 'ev_rev': 1.30, 'p_fcf': 1.25, 'graham_k': 28, 'wacc': 0.08, 'g_high_adj': 0.05, 'g_term': 0.03, 'k_e_adj': -0.01, 'g_pb_adj': 0.01},
}


def calculate_cost_of_equity(beta, regime_adj):
    """k_e = Rf + Beta × ERP, max %15 cap (v2)"""
    rf = 0.045
    erp = 0.055
    k_e = rf + (beta * erp) + regime_adj
    return min(k_e, 0.15)


def residual_income_value(eps_ttm, bvps, roe, k_e, growth_years=5, terminal_g=0.03):
    """Residual Income Model (v2 - ROE < k_e fallback)"""
    if eps_ttm is None or bvps <= 0 or k_e <= 0:
        return None
    
    book_value = bvps
    pv_ri = 0
    last_ri = 0
    
    for t in range(1, growth_years + 1):
        ri = (roe - k_e) * book_value
        last_ri = ri
        pv_ri += ri / ((1 + k_e) ** t)
        book_value = book_value + ri
    
    if k_e > terminal_g:
        terminal_ri = last_ri * (1 + terminal_g)
        pv_terminal = (terminal_ri / (k_e - terminal_g)) / ((1 + k_e) ** growth_years)
        pv_ri += pv_terminal
    
    value = bvps + pv_ri
    return max(value, bvps * 0.5)  # Minimum BVPS'in %50'si


def detect_market_regime():
    vix_q = fetch("quote", {"symbol": "^VIX"})
    spy_q = fetch("quote", {"symbol": "SPY"})
    
    vix = None
    spy_dist = None
    
    if vix_q and isinstance(vix_q, list) and len(vix_q) > 0:
        vix = vix_q[0].get('price')
    
    if spy_q and isinstance(spy_q, list) and len(spy_q) > 0:
        spy = spy_q[0]
        price = spy.get('price', 0)
        sma200 = spy.get('priceAvg200', 0)
        if sma200 > 0:
            spy_dist = (price - sma200) / sma200
    
    regime = 'normal'
    if vix is not None and spy_dist is not None:
        if vix < 16 and spy_dist > 0.05:
            regime = 'bull'
        elif vix > 28 or spy_dist < -0.05:
            regime = 'bear'
        elif vix > 22:
            regime = 'bear_light'
        else:
            regime = 'normal'
    
    return {'vix': vix, 'spy_distance_to_200sma': spy_dist, 'regime': regime}


def dcf_calculate(start_fcf, g_high, g_mid, g_term, wacc, cash, debt, shares, years_high=5, years_total=10):
    if start_fcf <= 0:
        fcfs = []
        for yr in range(1, years_total + 1):
            if yr <= 2:
                base = start_fcf * (0.5 if yr == 1 else 0.2)
            elif yr <= years_high:
                base = abs(start_fcf) * 0.3 * ((1 + g_high) ** (yr - 2))
            else:
                base = abs(start_fcf) * 0.3 * ((1 + g_high) ** (years_high - 2)) * ((1 + g_mid) ** (yr - years_high))
            fcfs.append(base)
    else:
        fcfs = []
        current = start_fcf
        for yr in range(1, years_total + 1):
            g = g_high if yr <= years_high else g_mid
            current = current * (1 + g)
            fcfs.append(current)
    
    pv_fcfs = sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcfs))
    
    terminal_fcf = fcfs[-1] * (1 + g_term)
    if wacc <= g_term:
        return None
    terminal_value = terminal_fcf / (wacc - g_term)
    pv_terminal = terminal_value / ((1 + wacc) ** years_total)
    
    ev = pv_fcfs + pv_terminal
    equity = ev + cash - debt
    if shares > 0:
        return equity / shares
    return None


def calculate_9_methods(data, regime_key, sector_key, is_ai_megacap):
    sector_mults = SECTOR_MULTIPLES.get(sector_key, SECTOR_MULTIPLES['generic'])
    adj = REGIME_ADJ[regime_key]
    
    eps_ttm = data['eps_ttm']
    eps_fwd = data['eps_fwd_2y']
    bvps = data['bvps']
    revenue = data['revenue_ttm']
    ebit = data['ebit_ttm']
    ebitda = data['ebitda_ttm']
    fcf_norm = data['fcf_normalized']
    cash = data['cash']
    debt = data['total_debt']
    shares = data['shares']
    roe = data['roe']
    beta = data['beta']
    
    # AI mega-cap boğa primi (sadece bull senaryoda)
    if is_ai_megacap and regime_key == 'bull':
        ai_mult = AI_MEGACAP_BULL_PREMIUM
    else:
        ai_mult = {k: 1.0 for k in ['pe', 'fwd_pe', 'ev_ebit', 'ev_ebitda', 'ev_rev', 'p_fcf']}
    
    results = {}
    method_notes = {}
    
    # 1. Net P/E
    if eps_ttm and eps_ttm > 0:
        target_pe = sector_mults['pe'] * adj['pe'] * ai_mult['pe']
        results['Net P/E'] = eps_ttm * target_pe
    else:
        results['Net P/E'] = None
    
    # 2. Forward P/E
    if eps_fwd and eps_fwd > 0:
        target_fwd = sector_mults['fwd_pe'] * adj['fwd_pe'] * ai_mult['fwd_pe']
        results['Forward P/E'] = eps_fwd * target_fwd
    else:
        results['Forward P/E'] = None
    
    # 3. EV/EBIT
    if ebit and ebit > 0 and shares > 0:
        target = sector_mults['ev_ebit'] * adj['ev_ebit'] * ai_mult['ev_ebit']
        ev = ebit * target
        equity = ev + cash - debt
        results['EV/EBIT'] = equity / shares
    else:
        results['EV/EBIT'] = None
    
    # 4. EV/EBITDA
    if ebitda and ebitda > 0 and shares > 0:
        target = sector_mults['ev_ebitda'] * adj['ev_ebitda'] * ai_mult['ev_ebitda']
        ev = ebitda * target
        equity = ev + cash - debt
        results['EV/EBITDA'] = equity / shares
    else:
        results['EV/EBITDA'] = None
    
    # 5. EV/Revenue
    if revenue and revenue > 0 and shares > 0:
        target = sector_mults['ev_rev'] * adj['ev_rev'] * ai_mult['ev_rev']
        ev = revenue * target
        equity = ev + cash - debt
        results['EV/Revenue'] = equity / shares
    else:
        results['EV/Revenue'] = None
    
    # 6. P/FCF
    if fcf_norm and fcf_norm > 0 and shares > 0:
        target = sector_mults['p_fcf'] * adj['p_fcf'] * ai_mult['p_fcf']
        results['P/FCF'] = (fcf_norm / shares) * target
    else:
        results['P/FCF'] = None
    
    # 7. Justified P-B (v2: k_e cap + ROE<k_e fallback)
    k_e = calculate_cost_of_equity(beta, adj['k_e_adj'])
    
    if bvps and bvps > 0:
        if roe and roe > 0.05 and roe > k_e:  # Klasik Gordon
            g = min(roe * 0.5, 0.05) + adj['g_pb_adj']
            if k_e > g:
                justified_pb = (roe - g) / (k_e - g)
                justified_pb = max(0.5, min(6.0, justified_pb))
                results['Justified P-B'] = bvps * justified_pb
                method_notes['Justified P-B'] = f"Gordon (k_e={k_e*100:.1f}%, g={g*100:.1f}%)"
            else:
                results['Justified P-B'] = None
        elif roe and roe > 0 and roe <= k_e:  # ROE < k_e: RIM fallback
            ri_value = residual_income_value(eps_ttm, bvps, roe, k_e, terminal_g=adj['g_term'])
            results['Justified P-B'] = ri_value
            method_notes['Justified P-B'] = f"⚠️ RIM (ROE %{roe*100:.1f} < k_e %{k_e*100:.1f})"
        else:
            results['Justified P-B'] = None
    else:
        results['Justified P-B'] = None
    
    # 8. Graham
    if eps_ttm and eps_ttm > 0 and bvps and bvps > 0:
        k = adj['graham_k']
        results['Graham'] = (k * eps_ttm * bvps) ** 0.5
    else:
        results['Graham'] = None
    
    # 9. DCF
    g_high = sector_mults['g_high'] + adj['g_high_adj']
    g_mid = g_high * 0.6
    g_term = adj['g_term']
    wacc = adj['wacc']
    
    dcf_val = dcf_calculate(
        start_fcf=fcf_norm if fcf_norm and fcf_norm > 0 else (data['ocf_ttm'] * 0.3 if data['ocf_ttm'] else 0),
        g_high=g_high,
        g_mid=g_mid,
        g_term=g_term,
        wacc=wacc,
        cash=cash,
        debt=debt,
        shares=shares
    )
    results['DCF'] = dcf_val if dcf_val and dcf_val > 0 else None
    
    return results, method_notes


def calc_cv(values):
    valid = [v for v in values if v is not None and v > 0]
    if len(valid) < 3:
        return None
    mean = statistics.mean(valid)
    if mean == 0:
        return None
    stdev = statistics.stdev(valid)
    return stdev / mean


def cv_warning_level(cv):
    if cv is None:
        return ('?', 'CV hesaplanamadı')
    if cv >= 0.50:
        return ('🔴', 'KRİTİK: Model güvenilir değil')
    if cv >= 0.35:
        return ('🟠', 'YÜKSEK: Tutarsızlık var')
    if cv >= 0.20:
        return ('🟡', 'ORTA: Normal')
    return ('🟢', 'DÜŞÜK: Hizalı')


def percentile(values, p):
    valid = sorted([v for v in values if v is not None and v > 0])
    if not valid:
        return None
    k = (len(valid) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(valid) - 1)
    return valid[f] + (valid[c] - valid[f]) * (k - f)


# DUAL-TRACK ayrımı
TRADITIONAL_METHODS = ['Net P/E', 'EV/EBIT', 'EV/EBITDA', 'EV/Revenue', 'P/FCF', 'Justified P-B', 'Graham']
FORWARD_METHODS = ['Forward P/E', 'DCF']


def split_methods(results):
    traditional = {k: v for k, v in results.items() if k in TRADITIONAL_METHODS and v}
    forward = {k: v for k, v in results.items() if k in FORWARD_METHODS and v}
    return traditional, forward


def auto_decision(price, summary, forward_outlier=False):
    """Mevcut fiyatı senaryolarla karşılaştırarak GİR/İZLE/GEÇ kararı"""
    bear_med = summary.get('bear', {}).get('median')
    normal_med = summary.get('normal', {}).get('median')
    normal_p75 = summary.get('normal', {}).get('p75')
    bull_med = summary.get('bull', {}).get('median')
    bull_p75 = summary.get('bull', {}).get('p75')
    
    if not all([bear_med, normal_med, bull_med]):
        return ("❓ BELİRSİZ", "Yetersiz veri")
    
    if price <= bear_med:
        return ("🟢 GÜÇLÜ AL", "Mevcut fiyat ayı senaryosu medyanının altında. Güvenli marj yüksek.")
    
    if price <= normal_med:
        return ("🟢 AL", "Mevcut fiyat normal senaryo medyanı altında. İyi giriş seviyesi.")
    
    if normal_p75 and price <= normal_p75:
        return ("🟡 İZLE / KÜÇÜK POZİSYON", "Mevcut fiyat normal aralıkta üst yarısında.")
    
    if price <= bull_med:
        return ("🟡 İZLE", "Mevcut fiyat boğa medyanı altında. Boğa sürerse haklı çıkar.")
    
    if bull_p75 and price <= bull_p75:
        warn = " (Forward beklentilerine bağlı)" if forward_outlier else ""
        return ("🟠 PAHALI / İZLE", f"Boğa P25-P75 aralığı.{warn}")
    
    if bull_p75 and price <= bull_p75 * 1.20:
        return ("🟠 ÇOK PAHALI", "Boğa P75 üstünde. Düzeltme riski yüksek.")
    
    return ("🔴 GEÇ / KAÇIN", "Tüm senaryoların üstünde. Aşırı pahalı.")


def fetch_analyst_consensus(ticker):
    """FMP price-target endpoint (v2)"""
    data = fetch("price-target-consensus", {"symbol": ticker})
    if data and isinstance(data, list) and len(data) > 0:
        d = data[0]
        return {
            'targetHigh': safe_get(d, 'targetHigh'),
            'targetLow': safe_get(d, 'targetLow'),
            'targetConsensus': safe_get(d, 'targetConsensus'),
            'targetMedian': safe_get(d, 'targetMedian'),
        }
    return None


def analyze(ticker):
    print(f"# {ticker} verileri çekiliyor (v2.0)...", file=sys.stderr)
    
    profile_list = fetch("profile", {"symbol": ticker})
    if not profile_list or not isinstance(profile_list, list):
        return {"error": f"{ticker} profile çekilemedi"}
    profile = profile_list[0]
    
    quote_list = fetch("quote", {"symbol": ticker})
    quote = quote_list[0] if quote_list else {}
    
    income_list = fetch("income-statement", {"symbol": ticker, "limit": 5}) or []
    cf_list = fetch("cash-flow-statement", {"symbol": ticker, "limit": 5}) or []
    bs_list = fetch("balance-sheet-statement", {"symbol": ticker, "limit": 1}) or []
    qinc_list = fetch("income-statement", {"symbol": ticker, "period": "quarter", "limit": 5}) or []
    qcf_list = fetch("cash-flow-statement", {"symbol": ticker, "period": "quarter", "limit": 4}) or []
    est_list = fetch("analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 4}) or []
    
    analyst_targets = fetch_analyst_consensus(ticker)
    
    if not income_list or not bs_list:
        return {"error": "finansal tablolar eksik"}
    
    bs = bs_list[0]
    
    if len(qinc_list) >= 4:
        revenue_ttm = sum(safe_get(q, 'revenue') for q in qinc_list[:4])
        ni_ttm = sum(safe_get(q, 'netIncome') for q in qinc_list[:4])
        ebit_ttm = sum(safe_get(q, 'operatingIncome') for q in qinc_list[:4])
        ebitda_ttm = sum(safe_get(q, 'ebitda') for q in qinc_list[:4])
    else:
        last = income_list[0]
        revenue_ttm = safe_get(last, 'revenue')
        ni_ttm = safe_get(last, 'netIncome')
        ebit_ttm = safe_get(last, 'operatingIncome')
        ebitda_ttm = safe_get(last, 'ebitda')
    
    if len(qcf_list) >= 4:
        ocf_ttm = sum(safe_get(q, 'operatingCashFlow') for q in qcf_list[:4])
        capex_ttm = sum(safe_get(q, 'capitalExpenditure') for q in qcf_list[:4])
    elif cf_list:
        ocf_ttm = safe_get(cf_list[0], 'operatingCashFlow')
        capex_ttm = safe_get(cf_list[0], 'capitalExpenditure')
    else:
        ocf_ttm = 0
        capex_ttm = 0
    
    fcf_ttm = ocf_ttm + capex_ttm
    
    if cf_list:
        fcfs = [safe_get(c, 'freeCashFlow') for c in cf_list[:4] if safe_get(c, 'freeCashFlow')]
        fcf_normalized = statistics.mean(fcfs) if fcfs else fcf_ttm
    else:
        fcf_normalized = fcf_ttm
    
    eps_fwd_2y = None
    if est_list:
        sorted_est = sorted(est_list, key=lambda x: x.get('date', ''))
        for est in sorted_est:
            date = est.get('date', '')
            if date and date >= '2027':
                eps_fwd_2y = safe_get(est, 'epsAvg')
                break
        if not eps_fwd_2y and sorted_est:
            eps_fwd_2y = safe_get(sorted_est[-1], 'epsAvg')
    
    market_cap = safe_get(quote, 'marketCap') or safe_get(profile, 'mktCap')
    price = safe_get(quote, 'price') or safe_get(profile, 'price')
    shares = market_cap / price if price > 0 else 0
    
    cash = safe_get(bs, 'cashAndCashEquivalents') + safe_get(bs, 'shortTermInvestments')
    total_debt = safe_get(bs, 'totalDebt')
    equity = safe_get(bs, 'totalStockholdersEquity')
    
    bvps = equity / shares if shares > 0 else 0
    eps_ttm = ni_ttm / shares if shares > 0 else 0
    roe = ni_ttm / equity if equity > 0 else 0
    
    net_margin = ni_ttm / revenue_ttm if revenue_ttm > 0 else 0
    pure_forward = net_margin < 0.03 or ni_ttm < 0
    
    # Forward outlier (v2)
    forward_growth_ratio = None
    forward_outlier = False
    if eps_fwd_2y and eps_ttm and eps_ttm > 0:
        forward_growth_ratio = eps_fwd_2y / eps_ttm
        forward_outlier = forward_growth_ratio > 2.5
    
    # AI mega-cap (v2)
    year_low = safe_get(quote, 'yearLow')
    sector_key, is_ai_megacap = detect_sector(profile, market_cap, year_low, price)
    
    market = detect_market_regime()
    
    data_pack = {
        'eps_ttm': eps_ttm, 'eps_fwd_2y': eps_fwd_2y, 'bvps': bvps,
        'revenue_ttm': revenue_ttm, 'ebit_ttm': ebit_ttm, 'ebitda_ttm': ebitda_ttm,
        'fcf_normalized': fcf_normalized, 'ocf_ttm': ocf_ttm,
        'cash': cash, 'total_debt': total_debt, 'shares': shares,
        'roe': roe, 'beta': safe_get(profile, 'beta', 1.0) or 1.0,
    }
    
    results = {}
    method_notes_all = {}
    for regime in ['bear', 'normal', 'bull']:
        results[regime], notes = calculate_9_methods(data_pack, regime, sector_key, is_ai_megacap)
        method_notes_all[regime] = notes
    
    summary_full = {}
    summary_traditional = {}
    summary_forward = {}
    
    for regime in ['bear', 'normal', 'bull']:
        all_vals = list(results[regime].values())
        valid_all = [v for v in all_vals if v is not None and v > 0]
        if valid_all:
            summary_full[regime] = {
                'p25': percentile(valid_all, 25),
                'median': statistics.median(valid_all),
                'p75': percentile(valid_all, 75),
                'mean': statistics.mean(valid_all),
                'cv': calc_cv(all_vals),
                'count': len(valid_all),
            }
        
        trad_results, fwd_results = split_methods(results[regime])
        trad_vals = [v for v in trad_results.values() if v and v > 0]
        if trad_vals:
            summary_traditional[regime] = {
                'p25': percentile(trad_vals, 25),
                'median': statistics.median(trad_vals),
                'p75': percentile(trad_vals, 75),
                'cv': calc_cv(trad_vals),
                'count': len(trad_vals),
            }
        
        fwd_vals = [v for v in fwd_results.values() if v and v > 0]
        if fwd_vals:
            summary_forward[regime] = {
                'p25': percentile(fwd_vals, 25),
                'median': statistics.median(fwd_vals),
                'p75': percentile(fwd_vals, 75),
                'cv': calc_cv(fwd_vals),
                'count': len(fwd_vals),
            }
    
    decision_full = auto_decision(price, summary_full, forward_outlier)
    decision_trad = auto_decision(price, summary_traditional, forward_outlier)
    
    return {
        'ticker': ticker,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'version': '2.0',
        'profile': {
            'name': profile.get('companyName'), 'sector': profile.get('sector'),
            'industry': profile.get('industry'), 'price': price,
            'market_cap': market_cap, 'beta': safe_get(profile, 'beta'),
            'year_high': safe_get(quote, 'yearHigh'), 'year_low': safe_get(quote, 'yearLow'),
            'sma_50': safe_get(quote, 'priceAvg50'), 'sma_200': safe_get(quote, 'priceAvg200'),
        },
        'sector_key': sector_key, 'is_ai_megacap': is_ai_megacap,
        'market_regime': market, 'pure_forward': pure_forward,
        'forward_outlier': forward_outlier,
        'forward_growth_ratio': round(forward_growth_ratio, 2) if forward_growth_ratio else None,
        'data_inputs': {
            'eps_ttm': round(eps_ttm, 2),
            'eps_fwd_2y': round(eps_fwd_2y, 2) if eps_fwd_2y else None,
            'bvps': round(bvps, 2),
            'revenue_ttm_billions': round(revenue_ttm / 1e9, 2),
            'ebit_ttm_millions': round(ebit_ttm / 1e6, 1),
            'ebitda_ttm_billions': round(ebitda_ttm / 1e9, 2),
            'fcf_normalized_billions': round(fcf_normalized / 1e9, 2),
            'fcf_ttm_billions': round(fcf_ttm / 1e9, 2),
            'cash_billions': round(cash / 1e9, 2),
            'total_debt_billions': round(total_debt / 1e9, 2),
            'shares_millions': round(shares / 1e6, 1),
            'roe_pct': round(roe * 100, 2),
            'net_margin_pct': round(net_margin * 100, 2),
        },
        'analyst_targets': analyst_targets,
        'methods_by_regime': {r: {k: (round(v, 2) if v else None) for k, v in results[r].items()} for r in ['bear', 'normal', 'bull']},
        'method_notes': method_notes_all,
        'summary_full': {r: {k: (round(v, 2) if isinstance(v, (int, float)) and v else v) for k, v in summary_full.get(r, {}).items()} for r in ['bear', 'normal', 'bull']},
        'summary_traditional': {r: {k: (round(v, 2) if isinstance(v, (int, float)) and v else v) for k, v in summary_traditional.get(r, {}).items()} for r in ['bear', 'normal', 'bull']},
        'summary_forward': {r: {k: (round(v, 2) if isinstance(v, (int, float)) and v else v) for k, v in summary_forward.get(r, {}).items()} for r in ['bear', 'normal', 'bull']},
        'decision_full': {'action': decision_full[0], 'reasoning': decision_full[1]},
        'decision_traditional': {'action': decision_trad[0], 'reasoning': decision_trad[1]},
    }


def format_output(result):
    p = result['profile']
    out = []
    out.append("")
    out.append("=" * 72)
    out.append(f"  {result['ticker']} - {p['name']} | v{result['version']}")
    out.append(f"  Sektör: {p['sector']} / {p['industry']}")
    ai_tag = " ⭐ AI MEGA-CAP" if result['is_ai_megacap'] else ""
    out.append(f"  Preset: {result['sector_key']}{ai_tag}")
    out.append(f"  Mevcut Fiyat: ${p['price']}")
    out.append(f"  Piyasa Rejimi: {result['market_regime']['regime']} (VIX: {result['market_regime']['vix']})")
    
    if result['pure_forward']:
        out.append(f"  ⚠️ Pure Forward Modu: AKTİF")
    
    if result['forward_outlier']:
        out.append(f"  ⚠️ FORWARD OUTLIER: EPS_FWD/EPS_TTM = {result['forward_growth_ratio']}x (>2.5)")
    
    out.append("=" * 72)
    
    out.append("\n📊 VERİ GİRDİLERİ:")
    di = result['data_inputs']
    out.append(f"  EPS TTM: ${di['eps_ttm']} | EPS FWD 2Y: ${di['eps_fwd_2y']} | BVPS: ${di['bvps']}")
    out.append(f"  Revenue TTM: ${di['revenue_ttm_billions']}B | EBITDA: ${di['ebitda_ttm_billions']}B")
    out.append(f"  FCF Norm: ${di['fcf_normalized_billions']}B | Cash: ${di['cash_billions']}B | Debt: ${di['total_debt_billions']}B")
    out.append(f"  ROE: %{di['roe_pct']} | Net Margin: %{di['net_margin_pct']}")
    
    out.append("\n📐 9 YÖNTEM × 3 SENARYO:")
    out.append(f"  {'Yöntem':<20} {'Ayı':<12} {'Normal':<12} {'Boğa':<12}  Not")
    out.append("  " + "-" * 70)
    methods = list(result['methods_by_regime']['normal'].keys())
    for m in methods:
        b = result['methods_by_regime']['bear'].get(m)
        n = result['methods_by_regime']['normal'].get(m)
        bl = result['methods_by_regime']['bull'].get(m)
        b_s = f"${b:.2f}" if b else "N/A"
        n_s = f"${n:.2f}" if n else "N/A"
        bl_s = f"${bl:.2f}" if bl else "N/A"
        note = result['method_notes'].get('normal', {}).get(m, '')
        out.append(f"  {m:<20} {b_s:<12} {n_s:<12} {bl_s:<12}  {note}")
    
    out.append("\n📈 DUAL-TRACK SENARYO ÖZETLERİ:")
    out.append("\n  🔵 TRADITIONAL (TTM bazlı, 7 yöntem):")
    for regime, label in [('bear', '🐻 Ayı'), ('normal', '⚖️ Normal'), ('bull', '🐂 Boğa')]:
        s = result['summary_traditional'].get(regime, {})
        if s:
            cv_icon, cv_msg = cv_warning_level(s.get('cv'))
            out.append(f"    {label:<12} P25-Med-P75: ${s.get('p25', 0):.2f} / ${s.get('median', 0):.2f} / ${s.get('p75', 0):.2f}  CV: {s.get('cv', 0)*100:.0f}% {cv_icon}")
    
    out.append("\n  🟣 FORWARD (Beklenti bazlı, 2 yöntem):")
    for regime, label in [('bear', '🐻 Ayı'), ('normal', '⚖️ Normal'), ('bull', '🐂 Boğa')]:
        s = result['summary_forward'].get(regime, {})
        if s:
            out.append(f"    {label:<12} P25-Med-P75: ${s.get('p25', 0):.2f} / ${s.get('median', 0):.2f} / ${s.get('p75', 0):.2f}")
    
    out.append("\n  ⚪ FULL (9 Yöntem birleşik):")
    for regime, label in [('bear', '🐻 Ayı'), ('normal', '⚖️ Normal'), ('bull', '🐂 Boğa')]:
        s = result['summary_full'].get(regime, {})
        if s:
            cv_icon, cv_msg = cv_warning_level(s.get('cv'))
            out.append(f"    {label:<12} Median: ${s.get('median', 0):.2f}  CV: {s.get('cv', 0)*100:.0f}% {cv_icon} {cv_msg}")
    
    price = p['price']
    out.append(f"\n💰 MEVCUT FİYAT (${price}) - TRADITIONAL bazlı karşılaştırma:")
    for regime, label in [('bear', '🐻 Ayı'), ('normal', '⚖️ Normal'), ('bull', '🐂 Boğa')]:
        s = result['summary_traditional'].get(regime, {})
        if s and s.get('median'):
            diff = (price - s['median']) / s['median'] * 100
            sign = "+" if diff > 0 else ""
            yorum = "pahalı" if diff > 0 else "ucuz"
            out.append(f"    {label} medyan ${s['median']:.2f} → %{sign}{diff:.1f} {yorum}")
    
    if result['analyst_targets']:
        at = result['analyst_targets']
        out.append(f"\n🎯 ANALİST HEDEF KONSENSÜSÜ:")
        out.append(f"    Düşük: ${at.get('targetLow', 0)} | Medyan: ${at.get('targetMedian', 0)} | Konsensüs: ${at.get('targetConsensus', 0)} | Yüksek: ${at.get('targetHigh', 0)}")
        if at.get('targetConsensus'):
            cd = (price - at['targetConsensus']) / at['targetConsensus'] * 100
            sign = "+" if cd > 0 else ""
            out.append(f"    Mevcut fiyat konsensüsten %{sign}{cd:.1f} {'yukarda' if cd > 0 else 'aşağıda'}")
    
    out.append(f"\n🎲 OTOMATIK KARAR:")
    out.append(f"  Traditional: {result['decision_traditional']['action']}")
    out.append(f"     {result['decision_traditional']['reasoning']}")
    if result['forward_outlier']:
        out.append(f"  Full (FWD dahil): {result['decision_full']['action']}")
        out.append(f"     ⚠️ Forward outlier var, agresif analist beklentilerine bağlı")
    
    out.append("")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("Kullanım: python adil_deger.py TICKER [--json]")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    json_only = '--json' in sys.argv
    
    result = analyze(ticker)
    
    if json_only:
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        return
    
    if 'error' in result:
        print(f"HATA: {result['error']}")
        sys.exit(1)
    
    print(format_output(result))


if __name__ == "__main__":
    main()
