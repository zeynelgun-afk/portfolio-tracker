#!/usr/bin/env python3
"""
Adil Değer - 9 Yöntem × 3 Senaryo Hesaplayıcı
Finzora AI v3.7.2 metodolojisi

Kullanım:
    python adil_deger.py AMKR
    python adil_deger.py MSFT --json
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
# SEKTÖR TESPİTİ
# =============================================================================

def detect_sector(profile):
    sector = (profile.get('sector') or '').lower()
    industry = (profile.get('industry') or '').lower()
    desc = (profile.get('description') or '').lower()
    
    if 'semiconduct' in industry:
        if any(k in desc for k in ['osat', 'packaging', 'assembly and test']):
            return 'semicon_osat'
        if 'equipment' in industry or any(k in desc for k in ['lithography', 'fabrication equipment']):
            return 'semicon_equipment'
        return 'semicon_design'
    
    if sector == 'technology':
        if 'software' in industry:
            return 'tech_software'
        return 'tech_hardware'
    
    if sector == 'financial services':
        if 'bank' in industry:
            return 'financials_bank'
        if 'insurance' in industry:
            return 'financials_insurance'
        return 'financials_other'
    
    if sector == 'healthcare':
        if 'biotech' in industry or 'biotechnology' in industry:
            return 'healthcare_biotech'
        if 'drug' in industry or 'pharma' in industry:
            return 'healthcare_pharma'
        return 'healthcare_devices'
    
    if sector == 'consumer defensive':
        return 'consumer_staples'
    if sector == 'consumer cyclical':
        return 'consumer_discretionary'
    
    if sector == 'industrials':
        return 'industrials'
    if sector == 'energy':
        return 'energy'
    if sector == 'real estate':
        return 'reits'
    if sector == 'utilities':
        return 'utilities'
    if sector == 'communication services':
        return 'communication'
    
    return 'generic'


# =============================================================================
# SEKTÖR MEDYAN ÇARPANLARI (Normal Piyasa)
# =============================================================================

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


# =============================================================================
# PİYASA REJİMİ ÇARPAN AYARLARI
# =============================================================================

REGIME_ADJ = {
    'bear':   {'pe': 0.70, 'fwd_pe': 0.72, 'ev_ebit': 0.72, 'ev_ebitda': 0.75, 'ev_rev': 0.65, 'p_fcf': 0.70, 'graham_k': 18, 'wacc': 0.12, 'g_high_adj': -0.05, 'g_term': 0.02, 'k_e_adj': 0.02, 'g_pb_adj': -0.01},
    'normal': {'pe': 1.00, 'fwd_pe': 1.00, 'ev_ebit': 1.00, 'ev_ebitda': 1.00, 'ev_rev': 1.00, 'p_fcf': 1.00, 'graham_k': 22.5, 'wacc': 0.10, 'g_high_adj': 0.00, 'g_term': 0.03, 'k_e_adj': 0.00, 'g_pb_adj': 0.00},
    'bull':   {'pe': 1.25, 'fwd_pe': 1.22, 'ev_ebit': 1.22, 'ev_ebitda': 1.20, 'ev_rev': 1.30, 'p_fcf': 1.25, 'graham_k': 28, 'wacc': 0.08, 'g_high_adj': 0.05, 'g_term': 0.03, 'k_e_adj': -0.01, 'g_pb_adj': 0.01},
}


# =============================================================================
# VİX VE PİYASA REJİMİ TESPİTİ
# =============================================================================

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


# =============================================================================
# DCF
# =============================================================================

def dcf_calculate(start_fcf, g_high, g_mid, g_term, wacc, cash, debt, shares, years_high=5, years_total=10):
    """10 yıllık DCF + Terminal Value"""
    if start_fcf <= 0:
        # Negatif FCF varsa, 0.05 × revenue tahmini ile başla (placeholder)
        # Yıl 3'te FCF +'ya döner varsayımı
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
        return None  # Geçersiz parametre
    terminal_value = terminal_fcf / (wacc - g_term)
    pv_terminal = terminal_value / ((1 + wacc) ** years_total)
    
    ev = pv_fcfs + pv_terminal
    equity = ev + cash - debt
    if shares > 0:
        return equity / shares
    return None


# =============================================================================
# 9 YÖNTEM HESAP
# =============================================================================

def calculate_9_methods(data, regime_key, sector_key):
    """data: tüm FMP verisi içeren dict"""
    
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
    
    results = {}
    
    # 1. Net P/E
    if eps_ttm > 0:
        target_pe = sector_mults['pe'] * adj['pe']
        results['Net P/E'] = eps_ttm * target_pe
    else:
        results['Net P/E'] = None
    
    # 2. Forward P/E
    if eps_fwd and eps_fwd > 0:
        target_fwd = sector_mults['fwd_pe'] * adj['fwd_pe']
        results['Forward P/E'] = eps_fwd * target_fwd
    else:
        results['Forward P/E'] = None
    
    # 3. EV/EBIT
    if ebit > 0 and shares > 0:
        target = sector_mults['ev_ebit'] * adj['ev_ebit']
        ev = ebit * target
        equity = ev + cash - debt
        results['EV/EBIT'] = equity / shares
    else:
        results['EV/EBIT'] = None
    
    # 4. EV/EBITDA
    if ebitda > 0 and shares > 0:
        target = sector_mults['ev_ebitda'] * adj['ev_ebitda']
        ev = ebitda * target
        equity = ev + cash - debt
        results['EV/EBITDA'] = equity / shares
    else:
        results['EV/EBITDA'] = None
    
    # 5. EV/Revenue
    if revenue > 0 and shares > 0:
        target = sector_mults['ev_rev'] * adj['ev_rev']
        ev = revenue * target
        equity = ev + cash - debt
        results['EV/Revenue'] = equity / shares
    else:
        results['EV/Revenue'] = None
    
    # 6. P/FCF
    if fcf_norm > 0 and shares > 0:
        target = sector_mults['p_fcf'] * adj['p_fcf']
        results['P/FCF'] = (fcf_norm / shares) * target
    else:
        results['P/FCF'] = None
    
    # 7. Justified P-B (Gordon)
    if bvps > 0 and roe > 0.05:
        rf = 0.045
        erp = 0.055
        k_e = rf + (beta * erp) + adj['k_e_adj']
        # Sürdürülebilir g (max %5)
        g = min(roe * 0.5, 0.05) + adj['g_pb_adj']
        if k_e > g and roe > g:
            justified_pb = (roe - g) / (k_e - g)
            justified_pb = max(0.5, min(6.0, justified_pb))  # sınır
            results['Justified P-B'] = bvps * justified_pb
        else:
            results['Justified P-B'] = None
    else:
        results['Justified P-B'] = None
    
    # 8. Graham
    if eps_ttm > 0 and bvps > 0:
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
        start_fcf=fcf_norm if fcf_norm > 0 else data['ocf_ttm'] * 0.3,
        g_high=g_high,
        g_mid=g_mid,
        g_term=g_term,
        wacc=wacc,
        cash=cash,
        debt=debt,
        shares=shares
    )
    results['DCF'] = dcf_val if dcf_val and dcf_val > 0 else None
    
    return results


# =============================================================================
# CV (COEFFICIENT OF VARIATION)
# =============================================================================

def calc_cv(values):
    valid = [v for v in values if v is not None and v > 0]
    if len(valid) < 3:
        return None
    mean = statistics.mean(valid)
    if mean == 0:
        return None
    stdev = statistics.stdev(valid)
    return stdev / mean


def percentile(values, p):
    valid = sorted([v for v in values if v is not None and v > 0])
    if not valid:
        return None
    k = (len(valid) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(valid) - 1)
    return valid[f] + (valid[c] - valid[f]) * (k - f)


# =============================================================================
# ANA FONKSİYON
# =============================================================================

def analyze(ticker):
    print(f"# {ticker} verileri çekiliyor...", file=sys.stderr)
    
    profile_list = fetch("profile", {"symbol": ticker})
    if not profile_list or not isinstance(profile_list, list):
        return {"error": f"{ticker} profile çekilemedi"}
    profile = profile_list[0]
    
    quote_list = fetch("quote", {"symbol": ticker})
    quote = quote_list[0] if quote_list else {}
    
    ratios_list = fetch("ratios-ttm", {"symbol": ticker})
    ratios = ratios_list[0] if ratios_list else {}
    
    km_list = fetch("key-metrics-ttm", {"symbol": ticker})
    km = km_list[0] if km_list else {}
    
    income_list = fetch("income-statement", {"symbol": ticker, "limit": 5}) or []
    cf_list = fetch("cash-flow-statement", {"symbol": ticker, "limit": 5}) or []
    bs_list = fetch("balance-sheet-statement", {"symbol": ticker, "limit": 1}) or []
    
    qinc_list = fetch("income-statement", {"symbol": ticker, "period": "quarter", "limit": 5}) or []
    
    est_list = fetch("analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 4}) or []
    
    if not income_list or not bs_list:
        return {"error": "finansal tablolar eksik"}
    
    bs = bs_list[0]
    
    # TTM hesapları (son 4 çeyrek toplamı)
    if len(qinc_list) >= 4:
        revenue_ttm = sum(safe_get(q, 'revenue') for q in qinc_list[:4])
        ni_ttm = sum(safe_get(q, 'netIncome') for q in qinc_list[:4])
        ebit_ttm = sum(safe_get(q, 'operatingIncome') for q in qinc_list[:4])
        ebitda_ttm = sum(safe_get(q, 'ebitda') for q in qinc_list[:4])
    else:
        # fallback annual
        last = income_list[0]
        revenue_ttm = safe_get(last, 'revenue')
        ni_ttm = safe_get(last, 'netIncome')
        ebit_ttm = safe_get(last, 'operatingIncome')
        ebitda_ttm = safe_get(last, 'ebitda')
    
    # OCF TTM (son 4 çeyrek yoksa annual)
    qcf_list = fetch("cash-flow-statement", {"symbol": ticker, "period": "quarter", "limit": 4}) or []
    if len(qcf_list) >= 4:
        ocf_ttm = sum(safe_get(q, 'operatingCashFlow') for q in qcf_list[:4])
        capex_ttm = sum(safe_get(q, 'capitalExpenditure') for q in qcf_list[:4])
    elif cf_list:
        ocf_ttm = safe_get(cf_list[0], 'operatingCashFlow')
        capex_ttm = safe_get(cf_list[0], 'capitalExpenditure')
    else:
        ocf_ttm = 0
        capex_ttm = 0
    
    fcf_ttm = ocf_ttm + capex_ttm  # capex zaten negatif
    
    # Normalize FCF (4 yıl ortalama)
    if cf_list:
        fcfs = [safe_get(c, 'freeCashFlow') for c in cf_list[:4] if safe_get(c, 'freeCashFlow')]
        fcf_normalized = statistics.mean(fcfs) if fcfs else fcf_ttm
    else:
        fcf_normalized = fcf_ttm
    
    # Forward EPS (2 yıl ileri)
    eps_fwd_2y = None
    if est_list:
        # En yeni iki yılı al
        sorted_est = sorted(est_list, key=lambda x: x.get('date', ''))
        if len(sorted_est) >= 2:
            # current year + 2 yıl ileri (genellikle indeks 2)
            for est in sorted_est:
                date = est.get('date', '')
                if date and date >= '2027':  # 2 yıl ileri (current 2026)
                    eps_fwd_2y = safe_get(est, 'epsAvg')
                    break
        if not eps_fwd_2y and sorted_est:
            eps_fwd_2y = safe_get(sorted_est[-1], 'epsAvg')
    
    # Hisse sayısı
    market_cap = safe_get(quote, 'marketCap') or safe_get(profile, 'mktCap')
    price = safe_get(quote, 'price') or safe_get(profile, 'price')
    shares = market_cap / price if price > 0 else 0
    
    # Bilanço
    cash = safe_get(bs, 'cashAndCashEquivalents') + safe_get(bs, 'shortTermInvestments')
    total_debt = safe_get(bs, 'totalDebt')
    equity = safe_get(bs, 'totalStockholdersEquity')
    
    bvps = equity / shares if shares > 0 else 0
    eps_ttm = ni_ttm / shares if shares > 0 else 0
    roe = ni_ttm / equity if equity > 0 else 0
    
    # Pure forward auto-trigger
    net_margin = ni_ttm / revenue_ttm if revenue_ttm > 0 else 0
    pure_forward = net_margin < 0.03 or ni_ttm < 0
    
    sector_key = detect_sector(profile)
    
    market = detect_market_regime()
    
    data_pack = {
        'eps_ttm': eps_ttm,
        'eps_fwd_2y': eps_fwd_2y,
        'bvps': bvps,
        'revenue_ttm': revenue_ttm,
        'ebit_ttm': ebit_ttm,
        'ebitda_ttm': ebitda_ttm,
        'fcf_normalized': fcf_normalized,
        'ocf_ttm': ocf_ttm,
        'cash': cash,
        'total_debt': total_debt,
        'shares': shares,
        'roe': roe,
        'beta': safe_get(profile, 'beta', 1.0) or 1.0,
    }
    
    # 3 senaryoda hesapla
    results = {}
    for regime in ['bear', 'normal', 'bull']:
        results[regime] = calculate_9_methods(data_pack, regime, sector_key)
    
    # Senaryo özetleri (median ± IQR/2)
    summary = {}
    for regime in ['bear', 'normal', 'bull']:
        vals = list(results[regime].values())
        valid = [v for v in vals if v is not None and v > 0]
        if valid:
            summary[regime] = {
                'p25': percentile(valid, 25),
                'median': statistics.median(valid),
                'p75': percentile(valid, 75),
                'mean': statistics.mean(valid),
                'cv': calc_cv(vals),
                'count': len(valid),
            }
    
    return {
        'ticker': ticker,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'profile': {
            'name': profile.get('companyName'),
            'sector': profile.get('sector'),
            'industry': profile.get('industry'),
            'price': price,
            'market_cap': market_cap,
            'beta': safe_get(profile, 'beta'),
            'year_high': safe_get(quote, 'yearHigh'),
            'year_low': safe_get(quote, 'yearLow'),
            'sma_50': safe_get(quote, 'priceAvg50'),
            'sma_200': safe_get(quote, 'priceAvg200'),
        },
        'sector_key': sector_key,
        'market_regime': market,
        'pure_forward': pure_forward,
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
        'methods_by_regime': {
            r: {k: (round(v, 2) if v else None) for k, v in results[r].items()}
            for r in ['bear', 'normal', 'bull']
        },
        'summary': {
            r: {k: (round(v, 2) if isinstance(v, (int, float)) and v else v) for k, v in summary.get(r, {}).items()}
            for r in ['bear', 'normal', 'bull']
        }
    }


def main():
    if len(sys.argv) < 2:
        print("Kullanım: python adil_deger.py TICKER [--json]")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    json_only = '--json' in sys.argv
    
    result = analyze(ticker)
    
    if json_only:
        print(json.dumps(result, indent=2, default=str))
        return
    
    if 'error' in result:
        print(f"HATA: {result['error']}")
        sys.exit(1)
    
    # İnsan-okur format
    p = result['profile']
    print(f"\n{'='*70}")
    print(f"  {result['ticker']} - {p['name']}")
    print(f"  Sektör: {p['sector']} / {p['industry']}")
    print(f"  Preset: {result['sector_key']}")
    print(f"  Mevcut Fiyat: ${p['price']}")
    print(f"  Piyasa Rejimi: {result['market_regime']['regime']} (VIX: {result['market_regime']['vix']})")
    print(f"  Pure Forward Modu: {'AKTİF' if result['pure_forward'] else 'pasif'}")
    print(f"{'='*70}\n")
    
    print("VERİ GİRDİLERİ:")
    for k, v in result['data_inputs'].items():
        print(f"  {k}: {v}")
    
    print("\n9 YÖNTEM × 3 SENARYO:")
    print(f"{'Yöntem':<20} {'Ayı ($)':<12} {'Normal ($)':<12} {'Boğa ($)':<12}")
    print("-" * 60)
    methods = list(result['methods_by_regime']['normal'].keys())
    for m in methods:
        b = result['methods_by_regime']['bear'].get(m)
        n = result['methods_by_regime']['normal'].get(m)
        bl = result['methods_by_regime']['bull'].get(m)
        b_s = f"${b:.2f}" if b else "N/A"
        n_s = f"${n:.2f}" if n else "N/A"
        bl_s = f"${bl:.2f}" if bl else "N/A"
        print(f"{m:<20} {b_s:<12} {n_s:<12} {bl_s:<12}")
    
    print("\nSENARYO EDER ARALIKLARI (P25-Median-P75):")
    for regime, label in [('bear', '🐻 Ayı'), ('normal', '⚖️ Normal'), ('bull', '🐂 Boğa')]:
        s = result['summary'].get(regime, {})
        if s:
            print(f"  {label:<12} P25: ${s.get('p25', 0):.2f}  Median: ${s.get('median', 0):.2f}  P75: ${s.get('p75', 0):.2f}  CV: {s.get('cv', 0)*100:.1f}%")
    
    # Karşılaştırma
    price = p['price']
    print(f"\nMEVCUT FİYAT ($ {price}) - SENARYOLARLA KARŞILAŞTIRMA:")
    for regime, label in [('bear', '🐻 Ayı'), ('normal', '⚖️ Normal'), ('bull', '🐂 Boğa')]:
        s = result['summary'].get(regime, {})
        if s and s.get('median'):
            diff = (price - s['median']) / s['median'] * 100
            sign = "+" if diff > 0 else ""
            print(f"  {label} medyan ${s['median']:.2f} → %{sign}{diff:.1f} {'pahalı' if diff > 0 else 'ucuz'}")


if __name__ == "__main__":
    main()
