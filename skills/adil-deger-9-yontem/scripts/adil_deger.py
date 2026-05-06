#!/usr/bin/env python3
"""
Adil Değer - 9 Yöntem × 3 Senaryo Hesaplayıcı v3.0
Finzora AI v3.7.2 metodolojisi

v3.0 Değişiklikleri:
- DUAL-MODE: 🚀 GROWTH (hızlı büyüyen) vs ⚖️ BLENDED (olgun)
- GROWTH modunda Traditional yöntemler kaldırıldı (sadece zemin gösterir)
- Yeni yöntemler: PEG Ratio, EV/Forward Revenue, EV/Forward EBITDA, Rule of 40, Reverse DCF
- BLENDED modunda Forward growth ratio'ya göre ağırlıklandırma
- Otomatik mod tespiti (5 kriter)

v2.0: k_e cap, RIM fallback, CV uyarı, Forward outlier, AI mega-cap, Analist konsensüs, Dual-track
v1.0: 9 yöntem temel hesap
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
# SEKTÖR & PRESET
# =============================================================================

GROWTH_FRIENDLY_SECTORS = {'semicon_design', 'tech_software', 'healthcare_biotech', 'communication'}


def detect_sector(profile, market_cap, year_low, current_price):
    sector = (profile.get('sector') or '').lower()
    industry = (profile.get('industry') or '').lower()
    desc = (profile.get('description') or '').lower()
    
    is_ai_megacap = False
    if market_cap and market_cap > 300e9:
        if year_low and year_low > 0:
            yearly_return = (current_price - year_low) / year_low
            if yearly_return > 1.0:
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
        if 'bank' in industry: return ('financials_bank', False)
        if 'insurance' in industry: return ('financials_insurance', False)
        return ('financials_other', False)
    
    if sector == 'healthcare':
        if 'biotech' in industry: return ('healthcare_biotech', False)
        if 'drug' in industry or 'pharma' in industry: return ('healthcare_pharma', False)
        return ('healthcare_devices', False)
    
    if sector == 'consumer defensive': return ('consumer_staples', False)
    if sector == 'consumer cyclical': return ('consumer_discretionary', False)
    if sector == 'industrials': return ('industrials', False)
    if sector == 'energy': return ('energy', False)
    if sector == 'real estate': return ('reits', False)
    if sector == 'utilities': return ('utilities', False)
    if sector == 'communication services': return ('communication', is_ai_megacap)
    
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

AI_MEGACAP_BULL_PREMIUM = {
    'pe': 1.50, 'fwd_pe': 1.45, 'ev_ebit': 1.45, 'ev_ebitda': 1.40, 'ev_rev': 1.55, 'p_fcf': 1.50,
}

REGIME_ADJ = {
    'bear':   {'pe': 0.70, 'fwd_pe': 0.72, 'ev_ebit': 0.72, 'ev_ebitda': 0.75, 'ev_rev': 0.65, 'p_fcf': 0.70, 'graham_k': 18, 'wacc': 0.12, 'g_high_adj': -0.05, 'g_term': 0.02, 'k_e_adj': 0.02, 'g_pb_adj': -0.01, 'peg_target': 0.8},
    'normal': {'pe': 1.00, 'fwd_pe': 1.00, 'ev_ebit': 1.00, 'ev_ebitda': 1.00, 'ev_rev': 1.00, 'p_fcf': 1.00, 'graham_k': 22.5, 'wacc': 0.10, 'g_high_adj': 0.00, 'g_term': 0.03, 'k_e_adj': 0.00, 'g_pb_adj': 0.00, 'peg_target': 1.0},
    'bull':   {'pe': 1.25, 'fwd_pe': 1.22, 'ev_ebit': 1.22, 'ev_ebitda': 1.20, 'ev_rev': 1.30, 'p_fcf': 1.25, 'graham_k': 28, 'wacc': 0.08, 'g_high_adj': 0.05, 'g_term': 0.03, 'k_e_adj': -0.01, 'g_pb_adj': 0.01, 'peg_target': 1.5},
}


# =============================================================================
# YENİ v3: MOD TESPİTİ (Growth vs Blended)
# =============================================================================

def detect_valuation_mode(forward_growth_ratio, revenue_3y_cagr, sector_key, is_ai_megacap, price_1y_return):
    """
    GROWTH modu için 5 kriter (≥3 sağlanırsa GROWTH):
    1. Forward growth ratio > 2.0
    2. Revenue 3y CAGR > %20
    3. Sektör Growth-friendly listede
    4. AI mega-cap
    5. 1y fiyat performansı > %50
    """
    criteria_met = 0
    criteria_detail = []
    
    if forward_growth_ratio and forward_growth_ratio > 2.0:
        criteria_met += 1
        criteria_detail.append(f"Forward büyüme {forward_growth_ratio:.1f}x (>2.0)")
    
    if revenue_3y_cagr and revenue_3y_cagr > 0.20:
        criteria_met += 1
        criteria_detail.append(f"Revenue 3y CAGR %{revenue_3y_cagr*100:.0f} (>%20)")
    
    if sector_key in GROWTH_FRIENDLY_SECTORS:
        criteria_met += 1
        criteria_detail.append(f"Growth-friendly sektör ({sector_key})")
    
    if is_ai_megacap:
        criteria_met += 1
        criteria_detail.append("AI mega-cap")
    
    if price_1y_return and price_1y_return > 0.50:
        criteria_met += 1
        criteria_detail.append(f"1y fiyat +%{price_1y_return*100:.0f} (>%50)")
    
    if criteria_met >= 3:
        return ('GROWTH', criteria_met, criteria_detail)
    return ('BLENDED', criteria_met, criteria_detail)


def blended_weights(forward_growth_ratio):
    """BLENDED modunda Traditional/Forward ağırlıkları"""
    if forward_growth_ratio is None:
        return (0.80, 0.20)
    if forward_growth_ratio > 1.5:
        return (0.50, 0.50)
    elif forward_growth_ratio > 1.2:
        return (0.65, 0.35)
    else:
        return (0.80, 0.20)


# =============================================================================
# COST OF EQUITY (k_e) - %15 cap
# =============================================================================

def calculate_cost_of_equity(beta, regime_adj):
    rf = 0.045
    erp = 0.055
    k_e = rf + (beta * erp) + regime_adj
    return min(k_e, 0.15)


def residual_income_value(eps_ttm, bvps, roe, k_e, growth_years=5, terminal_g=0.03):
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
    return max(value, bvps * 0.5)


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


# =============================================================================
# REVERSE DCF (v3 yeni)
# =============================================================================

def reverse_dcf(current_price, shares, cash, debt, start_fcf, wacc=0.10, g_term=0.03, years_high=5, years_total=10):
    """
    Mevcut fiyatın implied ettiği yıllık büyüme oranını çözer.
    
    Iterative search: 0% ile %50 arasında binary search.
    """
    if shares <= 0 or current_price <= 0:
        return None
    
    target_equity = current_price * shares
    target_ev = target_equity + debt - cash
    
    if start_fcf <= 0:
        start_fcf = max(1e6, start_fcf)  # ufak pozitif değer
    
    def calc_dcf_with_growth(g):
        fcfs = []
        current = start_fcf
        for yr in range(1, years_total + 1):
            grow = g if yr <= years_high else g * 0.6
            current = current * (1 + grow)
            fcfs.append(current)
        pv_fcfs = sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcfs))
        terminal_fcf = fcfs[-1] * (1 + g_term)
        if wacc <= g_term:
            return float('inf')
        tv = terminal_fcf / (wacc - g_term)
        pv_tv = tv / ((1 + wacc) ** years_total)
        return pv_fcfs + pv_tv
    
    # Binary search %0 ile %50 arasında
    low, high = 0.0, 0.50
    for _ in range(40):
        mid = (low + high) / 2
        ev_at_mid = calc_dcf_with_growth(mid)
        if ev_at_mid > target_ev:
            high = mid
        else:
            low = mid
        if abs(high - low) < 0.001:
            break
    
    implied_growth = (low + high) / 2
    return implied_growth


# =============================================================================
# YENİ v3: GROWTH YÖNTEMLERİ
# =============================================================================

def calc_peg(eps_fwd_2y, eps_ttm, growth_pct, peg_target):
    """PEG Ratio yöntemi: Adil Forward P/E = PEG_target × growth"""
    if not eps_fwd_2y or eps_fwd_2y <= 0 or growth_pct is None:
        return None
    if growth_pct < 0.05:
        return None  # Düşük büyümede PEG anlamsız
    growth_pct_for_peg = growth_pct * 100  # %30 büyüme = 30
    target_pe = peg_target * growth_pct_for_peg
    return eps_fwd_2y * target_pe


def calc_ev_forward_revenue(rev_fwd_2y, ev_rev_target, cash, debt, shares):
    if not rev_fwd_2y or rev_fwd_2y <= 0 or shares <= 0:
        return None
    ev = rev_fwd_2y * ev_rev_target
    equity = ev + cash - debt
    return equity / shares


def calc_ev_forward_ebitda(ebitda_fwd_2y, ev_ebitda_target, cash, debt, shares):
    if not ebitda_fwd_2y or ebitda_fwd_2y <= 0 or shares <= 0:
        return None
    ev = ebitda_fwd_2y * ev_ebitda_target
    equity = ev + cash - debt
    return equity / shares


def calc_rule_of_40(revenue_growth_pct, fcf_margin_pct, revenue_ttm, cash, debt, shares, ai_premium=1.0):
    """
    Rule of 40: Revenue Growth + FCF Margin >= 40 = premium hak ediyor
    
    Adil EV/Revenue = base + (Rule_of_40 - 40) × 0.2 (eğer >= 40)
    Adil EV/Revenue = max(2, base - (40 - Rule_of_40) × 0.1) (eğer < 40)
    """
    if revenue_growth_pct is None or fcf_margin_pct is None:
        return None
    rule = (revenue_growth_pct * 100) + (fcf_margin_pct * 100)
    base = 5
    if rule >= 40:
        ev_rev_target = base + (rule - 40) * 0.2
    else:
        ev_rev_target = max(2, base - (40 - rule) * 0.1)
    ev_rev_target *= ai_premium
    
    if revenue_ttm <= 0 or shares <= 0:
        return None
    ev = revenue_ttm * ev_rev_target
    equity = ev + cash - debt
    return equity / shares


# =============================================================================
# 9 YÖNTEM (mevcut) + GROWTH yöntemler
# =============================================================================

def calculate_methods(data, regime_key, sector_key, is_ai_megacap, mode):
    """
    mode: 'GROWTH' veya 'BLENDED'
    GROWTH'da Traditional dahil ama ayrı işaretlenir, sonuç hesaplamaya katılmaz
    """
    sector_mults = SECTOR_MULTIPLES.get(sector_key, SECTOR_MULTIPLES['generic'])
    adj = REGIME_ADJ[regime_key]
    
    eps_ttm = data['eps_ttm']
    eps_fwd = data['eps_fwd_2y']
    bvps = data['bvps']
    revenue = data['revenue_ttm']
    rev_fwd = data['revenue_fwd_2y']
    ebit = data['ebit_ttm']
    ebitda = data['ebitda_ttm']
    ebitda_fwd = data['ebitda_fwd_2y']
    fcf_norm = data['fcf_normalized']
    cash = data['cash']
    debt = data['total_debt']
    shares = data['shares']
    roe = data['roe']
    beta = data['beta']
    
    # AI mega-cap boğa primi
    if is_ai_megacap and regime_key == 'bull':
        ai_mult = AI_MEGACAP_BULL_PREMIUM
    else:
        ai_mult = {k: 1.0 for k in ['pe', 'fwd_pe', 'ev_ebit', 'ev_ebitda', 'ev_rev', 'p_fcf']}
    
    traditional = {}
    forward = {}
    growth = {}
    notes = {}
    
    # === TRADITIONAL (TTM bazlı 7 yöntem) ===
    
    if eps_ttm and eps_ttm > 0:
        traditional['Net P/E'] = eps_ttm * sector_mults['pe'] * adj['pe'] * ai_mult['pe']
    else:
        traditional['Net P/E'] = None
    
    if ebit and ebit > 0 and shares > 0:
        ev = ebit * sector_mults['ev_ebit'] * adj['ev_ebit'] * ai_mult['ev_ebit']
        traditional['EV/EBIT'] = (ev + cash - debt) / shares
    else:
        traditional['EV/EBIT'] = None
    
    if ebitda and ebitda > 0 and shares > 0:
        ev = ebitda * sector_mults['ev_ebitda'] * adj['ev_ebitda'] * ai_mult['ev_ebitda']
        traditional['EV/EBITDA'] = (ev + cash - debt) / shares
    else:
        traditional['EV/EBITDA'] = None
    
    if revenue and revenue > 0 and shares > 0:
        ev = revenue * sector_mults['ev_rev'] * adj['ev_rev'] * ai_mult['ev_rev']
        traditional['EV/Revenue'] = (ev + cash - debt) / shares
    else:
        traditional['EV/Revenue'] = None
    
    if fcf_norm and fcf_norm > 0 and shares > 0:
        traditional['P/FCF'] = (fcf_norm / shares) * sector_mults['p_fcf'] * adj['p_fcf'] * ai_mult['p_fcf']
    else:
        traditional['P/FCF'] = None
    
    # Justified P-B
    k_e = calculate_cost_of_equity(beta, adj['k_e_adj'])
    if bvps and bvps > 0:
        if roe and roe > 0.05 and roe > k_e:
            g = min(roe * 0.5, 0.05) + adj['g_pb_adj']
            if k_e > g:
                jpb = max(0.5, min(6.0, (roe - g) / (k_e - g)))
                traditional['Justified P-B'] = bvps * jpb
                notes['Justified P-B'] = f"Gordon (k_e={k_e*100:.0f}%, g={g*100:.0f}%)"
            else:
                traditional['Justified P-B'] = None
        elif roe and roe > 0 and roe <= k_e:
            ri = residual_income_value(eps_ttm, bvps, roe, k_e, terminal_g=adj['g_term'])
            traditional['Justified P-B'] = ri
            notes['Justified P-B'] = f"⚠️ RIM (ROE %{roe*100:.0f} < k_e %{k_e*100:.0f})"
        else:
            traditional['Justified P-B'] = None
    else:
        traditional['Justified P-B'] = None
    
    if eps_ttm and eps_ttm > 0 and bvps and bvps > 0:
        traditional['Graham'] = (adj['graham_k'] * eps_ttm * bvps) ** 0.5
    else:
        traditional['Graham'] = None
    
    # === FORWARD (klasik 2 yöntem) ===
    
    if eps_fwd and eps_fwd > 0:
        forward['Forward P/E'] = eps_fwd * sector_mults['fwd_pe'] * adj['fwd_pe'] * ai_mult['fwd_pe']
    else:
        forward['Forward P/E'] = None
    
    g_high = sector_mults['g_high'] + adj['g_high_adj']
    forward['DCF'] = dcf_calculate(
        start_fcf=fcf_norm if fcf_norm and fcf_norm > 0 else (data['ocf_ttm'] * 0.3 if data['ocf_ttm'] else 0),
        g_high=g_high,
        g_mid=g_high * 0.6,
        g_term=adj['g_term'],
        wacc=adj['wacc'],
        cash=cash,
        debt=debt,
        shares=shares
    )
    if forward['DCF'] and forward['DCF'] <= 0:
        forward['DCF'] = None
    
    # === GROWTH (yeni v3 yöntemler) ===
    
    # Forward growth oranı (PEG için)
    forward_growth = None
    if eps_fwd and eps_ttm and eps_ttm > 0:
        # 2 yıllık büyüme → yıllık geometrik
        forward_growth = (eps_fwd / eps_ttm) ** 0.5 - 1
    
    # PEG
    growth['PEG'] = calc_peg(eps_fwd, eps_ttm, forward_growth, adj['peg_target'])
    
    # EV/Forward Revenue
    growth['EV/FWD Revenue'] = calc_ev_forward_revenue(
        rev_fwd, sector_mults['ev_rev'] * adj['ev_rev'] * ai_mult['ev_rev'],
        cash, debt, shares
    )
    
    # EV/Forward EBITDA
    growth['EV/FWD EBITDA'] = calc_ev_forward_ebitda(
        ebitda_fwd, sector_mults['ev_ebitda'] * adj['ev_ebitda'] * ai_mult['ev_ebitda'],
        cash, debt, shares
    )
    
    # Rule of 40 (büyüme ve FCF margin lazım)
    rev_growth = data.get('revenue_growth_yoy')
    fcf_margin = (fcf_norm / revenue) if (fcf_norm and revenue and revenue > 0) else None
    growth['Rule of 40'] = calc_rule_of_40(
        rev_growth, fcf_margin, revenue, cash, debt, shares,
        ai_premium=ai_mult.get('ev_rev', 1.0)
    )
    
    # Reverse DCF (sadece bilgi amaçlı, "implied" sayılmadan değil)
    # Bu bir adil değer DEĞİL, mevcut fiyatın implied büyümesini gösterir
    # Çıktıya not olarak eklenecek, methods listesinde olmayacak
    
    return {
        'traditional': traditional,
        'forward': forward,
        'growth': growth,
        'notes': notes,
    }


# =============================================================================
# CV + ÖZETLEME
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


def summarize(values_dict):
    """Yöntem dict'inden özet çıkar"""
    vals = [v for v in values_dict.values() if v is not None and v > 0]
    if not vals:
        return None
    return {
        'p25': percentile(vals, 25),
        'median': statistics.median(vals),
        'p75': percentile(vals, 75),
        'mean': statistics.mean(vals),
        'cv': calc_cv(list(values_dict.values())),
        'count': len(vals),
        'methods_used': [k for k, v in values_dict.items() if v and v > 0],
    }


def weighted_summary(traditional_summary, forward_growth_summary, w_trad, w_fwd):
    """BLENDED modu için ağırlıklı medyan"""
    if not traditional_summary or not forward_growth_summary:
        return None
    
    return {
        'p25': traditional_summary.get('p25', 0) * w_trad + forward_growth_summary.get('p25', 0) * w_fwd,
        'median': traditional_summary.get('median', 0) * w_trad + forward_growth_summary.get('median', 0) * w_fwd,
        'p75': traditional_summary.get('p75', 0) * w_trad + forward_growth_summary.get('p75', 0) * w_fwd,
        'weights': {'traditional': w_trad, 'forward_growth': w_fwd},
    }


def auto_decision(price, summary):
    bear_med = summary.get('bear', {}).get('median')
    normal_med = summary.get('normal', {}).get('median')
    normal_p75 = summary.get('normal', {}).get('p75')
    bull_med = summary.get('bull', {}).get('median')
    bull_p75 = summary.get('bull', {}).get('p75')
    
    if not all([bear_med, normal_med, bull_med]):
        return ("❓ BELİRSİZ", "Yetersiz veri")
    
    if price <= bear_med:
        return ("🟢 GÜÇLÜ AL", "Mevcut fiyat ayı medyanının altında. Güvenli marj yüksek.")
    if price <= normal_med:
        return ("🟢 AL", "Mevcut fiyat normal medyan altında. İyi giriş seviyesi.")
    if normal_p75 and price <= normal_p75:
        return ("🟡 İZLE / KÜÇÜK POZİSYON", "Mevcut fiyat normal aralıkta üst yarısı.")
    if price <= bull_med:
        return ("🟡 İZLE", "Mevcut fiyat boğa medyanı altında.")
    if bull_p75 and price <= bull_p75:
        return ("🟠 PAHALI / İZLE", "Boğa P25-P75 aralığı.")
    if bull_p75 and price <= bull_p75 * 1.20:
        return ("🟠 ÇOK PAHALI", "Boğa P75 üstünde.")
    return ("🔴 GEÇ / KAÇIN", "Tüm senaryoların üstünde.")


def fetch_analyst_consensus(ticker):
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


# =============================================================================
# ANA FONKSİYON
# =============================================================================

def analyze(ticker):
    print(f"# {ticker} verileri çekiliyor (v3.0)...", file=sys.stderr)
    
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
    
    # Forward EPS, Revenue, EBITDA (2 yıl ileri)
    eps_fwd_2y = None
    rev_fwd_2y = None
    ebitda_fwd_2y = None
    if est_list:
        sorted_est = sorted(est_list, key=lambda x: x.get('date', ''))
        for est in sorted_est:
            date = est.get('date', '')
            if date and date >= '2027':
                eps_fwd_2y = safe_get(est, 'epsAvg')
                rev_fwd_2y = safe_get(est, 'revenueAvg')
                ebitda_fwd_2y = safe_get(est, 'ebitdaAvg')
                break
        if not eps_fwd_2y and sorted_est:
            last = sorted_est[-1]
            eps_fwd_2y = safe_get(last, 'epsAvg')
            rev_fwd_2y = safe_get(last, 'revenueAvg')
            ebitda_fwd_2y = safe_get(last, 'ebitdaAvg')
    
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
    
    # Revenue 3y CAGR (annual)
    revenue_3y_cagr = None
    if len(income_list) >= 4:
        rev_now = safe_get(income_list[0], 'revenue')
        rev_3y_ago = safe_get(income_list[3], 'revenue')
        if rev_now > 0 and rev_3y_ago > 0:
            revenue_3y_cagr = (rev_now / rev_3y_ago) ** (1/3) - 1
    
    # Revenue YoY growth
    revenue_growth_yoy = None
    if len(income_list) >= 2:
        rev_now = safe_get(income_list[0], 'revenue')
        rev_prev = safe_get(income_list[1], 'revenue')
        if rev_now > 0 and rev_prev > 0:
            revenue_growth_yoy = (rev_now - rev_prev) / rev_prev
    
    # Forward outlier
    forward_growth_ratio = None
    forward_outlier = False
    if eps_fwd_2y and eps_ttm and eps_ttm > 0:
        forward_growth_ratio = eps_fwd_2y / eps_ttm
        forward_outlier = forward_growth_ratio > 2.5
    
    # 1y price return
    price_1y_return = None
    year_low = safe_get(quote, 'yearLow')
    if year_low and year_low > 0:
        price_1y_return = (price - year_low) / year_low
    
    # AI mega-cap
    sector_key, is_ai_megacap = detect_sector(profile, market_cap, year_low, price)
    
    # MOD TESPİTİ (v3 yeni)
    mode, criteria_count, criteria_detail = detect_valuation_mode(
        forward_growth_ratio, revenue_3y_cagr, sector_key, is_ai_megacap, price_1y_return
    )
    
    market = detect_market_regime()
    
    data_pack = {
        'eps_ttm': eps_ttm, 'eps_fwd_2y': eps_fwd_2y, 'bvps': bvps,
        'revenue_ttm': revenue_ttm, 'revenue_fwd_2y': rev_fwd_2y,
        'ebit_ttm': ebit_ttm, 'ebitda_ttm': ebitda_ttm, 'ebitda_fwd_2y': ebitda_fwd_2y,
        'fcf_normalized': fcf_normalized, 'ocf_ttm': ocf_ttm,
        'cash': cash, 'total_debt': total_debt, 'shares': shares,
        'roe': roe, 'beta': safe_get(profile, 'beta', 1.0) or 1.0,
        'revenue_growth_yoy': revenue_growth_yoy,
    }
    
    # 3 senaryoda hesapla
    results = {}
    notes_all = {}
    for regime in ['bear', 'normal', 'bull']:
        m = calculate_methods(data_pack, regime, sector_key, is_ai_megacap, mode)
        results[regime] = m
        notes_all[regime] = m.get('notes', {})
    
    # Reverse DCF (mode'a bakmaksızın hesapla, bilgi amaçlı)
    implied_growth = reverse_dcf(
        price, shares, cash, total_debt,
        fcf_normalized if fcf_normalized > 0 else (ocf_ttm * 0.3),
        wacc=0.10
    )
    
    # ÖZETLER
    summaries = {}
    for regime in ['bear', 'normal', 'bull']:
        trad_sum = summarize(results[regime]['traditional'])
        fwd_sum = summarize(results[regime]['forward'])
        growth_sum = summarize(results[regime]['growth'])
        
        # Forward + Growth birleşik (büyüme görünümü)
        combined_fwd_growth = {**results[regime]['forward'], **results[regime]['growth']}
        fwd_growth_sum = summarize(combined_fwd_growth)
        
        # Ana sonuç moda göre
        if mode == 'GROWTH':
            # Sadece Forward + Growth
            main_sum = fwd_growth_sum
            main_label = 'Büyüme Yöntemleri'
        else:  # BLENDED
            # Ağırlıklı medyan
            w_trad, w_fwd = blended_weights(forward_growth_ratio)
            blended_sum = weighted_summary(trad_sum, fwd_growth_sum, w_trad, w_fwd)
            main_sum = blended_sum if blended_sum else trad_sum
            main_label = f'Ağırlıklı (Trad %{int(w_trad*100)} / FwdGrowth %{int(w_fwd*100)})'
        
        summaries[regime] = {
            'traditional': trad_sum,
            'forward': fwd_sum,
            'growth': growth_sum,
            'forward_growth_combined': fwd_growth_sum,
            'main': main_sum,
            'main_label': main_label,
        }
    
    decision = auto_decision(price, {r: summaries[r]['main'] or {} for r in ['bear', 'normal', 'bull']})
    
    return {
        'ticker': ticker,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'version': '3.0',
        'mode': mode,
        'mode_criteria_met': criteria_count,
        'mode_criteria_detail': criteria_detail,
        'profile': {
            'name': profile.get('companyName'), 'sector': profile.get('sector'),
            'industry': profile.get('industry'), 'price': price,
            'market_cap': market_cap, 'beta': safe_get(profile, 'beta'),
            'year_high': safe_get(quote, 'yearHigh'), 'year_low': year_low,
            'sma_50': safe_get(quote, 'priceAvg50'), 'sma_200': safe_get(quote, 'priceAvg200'),
        },
        'sector_key': sector_key, 'is_ai_megacap': is_ai_megacap,
        'market_regime': market, 'pure_forward': pure_forward,
        'forward_outlier': forward_outlier,
        'forward_growth_ratio': round(forward_growth_ratio, 2) if forward_growth_ratio else None,
        'revenue_3y_cagr': round(revenue_3y_cagr * 100, 1) if revenue_3y_cagr else None,
        'price_1y_return_pct': round(price_1y_return * 100, 1) if price_1y_return else None,
        'implied_growth_pct': round(implied_growth * 100, 1) if implied_growth else None,
        'data_inputs': {
            'eps_ttm': round(eps_ttm, 2),
            'eps_fwd_2y': round(eps_fwd_2y, 2) if eps_fwd_2y else None,
            'bvps': round(bvps, 2),
            'revenue_ttm_billions': round(revenue_ttm / 1e9, 2),
            'revenue_fwd_2y_billions': round(rev_fwd_2y / 1e9, 2) if rev_fwd_2y else None,
            'ebitda_ttm_billions': round(ebitda_ttm / 1e9, 2),
            'ebitda_fwd_2y_billions': round(ebitda_fwd_2y / 1e9, 2) if ebitda_fwd_2y else None,
            'fcf_normalized_billions': round(fcf_normalized / 1e9, 2),
            'cash_billions': round(cash / 1e9, 2),
            'total_debt_billions': round(total_debt / 1e9, 2),
            'shares_millions': round(shares / 1e6, 1),
            'roe_pct': round(roe * 100, 2),
            'net_margin_pct': round(net_margin * 100, 2),
            'revenue_growth_yoy_pct': round(revenue_growth_yoy * 100, 1) if revenue_growth_yoy else None,
        },
        'analyst_targets': analyst_targets,
        'methods_by_regime': results,
        'method_notes': notes_all,
        'summaries': summaries,
        'decision': {'action': decision[0], 'reasoning': decision[1]},
    }


def format_output(result):
    p = result['profile']
    out = []
    mode = result['mode']
    mode_emoji = '🚀' if mode == 'GROWTH' else '⚖️'
    
    out.append("")
    out.append("=" * 75)
    out.append(f"  {result['ticker']} - {p['name']} | v{result['version']}")
    out.append(f"  Sektör: {p['sector']} / {p['industry']} → {result['sector_key']}" + (" ⭐ AI MEGA-CAP" if result['is_ai_megacap'] else ""))
    out.append(f"  Mevcut Fiyat: ${p['price']}  |  Piyasa: {result['market_regime']['regime']} (VIX: {result['market_regime']['vix']})")
    out.append("")
    out.append(f"  {mode_emoji} MOD: {mode} ({result['mode_criteria_met']}/5 kriter)")
    for c in result['mode_criteria_detail']:
        out.append(f"     ✓ {c}")
    
    if result['forward_outlier']:
        out.append(f"  ⚠️ Forward outlier: EPS_FWD/EPS_TTM = {result['forward_growth_ratio']}x")
    
    out.append("=" * 75)
    
    di = result['data_inputs']
    out.append("\n📊 VERİ GİRDİLERİ:")
    out.append(f"  EPS TTM: ${di['eps_ttm']} | EPS FWD 2Y: ${di['eps_fwd_2y']}")
    out.append(f"  Revenue TTM: ${di['revenue_ttm_billions']}B | FWD 2Y: ${di['revenue_fwd_2y_billions']}B")
    out.append(f"  EBITDA TTM: ${di['ebitda_ttm_billions']}B | FWD 2Y: ${di['ebitda_fwd_2y_billions']}B")
    out.append(f"  FCF Norm: ${di['fcf_normalized_billions']}B | Cash: ${di['cash_billions']}B | Debt: ${di['total_debt_billions']}B")
    out.append(f"  ROE: %{di['roe_pct']} | Net Margin: %{di['net_margin_pct']} | Revenue YoY: %{di.get('revenue_growth_yoy_pct')}")
    if result.get('revenue_3y_cagr'):
        out.append(f"  Revenue 3y CAGR: %{result['revenue_3y_cagr']} | 1y Fiyat: %{result['price_1y_return_pct']}")
    
    # Yöntemler
    if mode == 'GROWTH':
        out.append("\n🚀 BÜYÜME YÖNTEMLERİ × 3 SENARYO (Traditional KULLANILMADI):")
        all_methods = list(result['methods_by_regime']['normal']['forward'].keys()) + list(result['methods_by_regime']['normal']['growth'].keys())
        out.append(f"  {'Yöntem':<22} {'Ayı':<12} {'Normal':<12} {'Boğa':<12}")
        out.append("  " + "-" * 60)
        for m in all_methods:
            for category in ['forward', 'growth']:
                if m in result['methods_by_regime']['normal'].get(category, {}):
                    b = result['methods_by_regime']['bear'][category].get(m)
                    n = result['methods_by_regime']['normal'][category].get(m)
                    bl = result['methods_by_regime']['bull'][category].get(m)
                    b_s = f"${b:.2f}" if b else "N/A"
                    n_s = f"${n:.2f}" if n else "N/A"
                    bl_s = f"${bl:.2f}" if bl else "N/A"
                    out.append(f"  {m:<22} {b_s:<12} {n_s:<12} {bl_s:<12}")
                    break
        
        # Reverse DCF
        if result.get('implied_growth_pct') is not None:
            out.append(f"\n  📊 Reverse DCF: Mevcut fiyat yıllık %{result['implied_growth_pct']} büyüme implied ediyor")
            out.append(f"     (Bu büyüme oranı 10 yıl boyunca sürerse mevcut fiyat haklı çıkar)")
        
        # Margin of safety zemini
        out.append("\n🛡️ MARGIN OF SAFETY ZEMİNİ (Traditional yöntemler - sadece referans):")
        for regime, label in [('bear', '🐻'), ('normal', '⚖️'), ('bull', '🐂')]:
            t = result['summaries'][regime].get('traditional')
            if t:
                out.append(f"  {label} {regime.capitalize():<8} medyan: ${t['median']:.2f}  (eğer büyüme durursa zemin)")
    
    else:  # BLENDED
        out.append("\n📐 9 YÖNTEM × 3 SENARYO + GROWTH METRİKLERİ:")
        out.append(f"  {'Yöntem':<22} {'Ayı':<12} {'Normal':<12} {'Boğa':<12}  Not")
        out.append("  " + "-" * 70)
        # Tüm yöntemler
        all_categories = ['traditional', 'forward', 'growth']
        for category in all_categories:
            cat_methods = list(result['methods_by_regime']['normal'].get(category, {}).keys())
            for m in cat_methods:
                b = result['methods_by_regime']['bear'][category].get(m)
                n = result['methods_by_regime']['normal'][category].get(m)
                bl = result['methods_by_regime']['bull'][category].get(m)
                b_s = f"${b:.2f}" if b else "N/A"
                n_s = f"${n:.2f}" if n else "N/A"
                bl_s = f"${bl:.2f}" if bl else "N/A"
                note = result['method_notes'].get('normal', {}).get(m, '')
                out.append(f"  {m:<22} {b_s:<12} {n_s:<12} {bl_s:<12}  {note}")
        
        if result.get('implied_growth_pct') is not None:
            out.append(f"\n  📊 Reverse DCF: Mevcut fiyat yıllık %{result['implied_growth_pct']} büyüme implied ediyor")
    
    # ANA SONUÇ
    out.append(f"\n📈 ANA SENARYO SONUÇLARI ({result['summaries']['normal']['main_label'] if result['summaries']['normal']['main'] else 'N/A'}):")
    for regime, label in [('bear', '🐻 Ayı'), ('normal', '⚖️ Normal'), ('bull', '🐂 Boğa')]:
        s = result['summaries'][regime].get('main')
        if s:
            out.append(f"  {label:<12} P25-Med-P75: ${s.get('p25', 0):.2f} / ${s.get('median', 0):.2f} / ${s.get('p75', 0):.2f}")
    
    # Detay özetler
    out.append("\n📊 ALT KATEGORİ ÖZETLERİ:")
    for cat_key, cat_label in [('traditional', '🔵 Traditional (TTM bazlı)'), 
                                ('forward', '🟣 Forward (FWD P/E + DCF)'),
                                ('growth', '🟢 Growth (PEG, EV/FWD, Rule of 40)')]:
        out.append(f"  {cat_label}:")
        for regime, label in [('bear', 'Ayı'), ('normal', 'Normal'), ('bull', 'Boğa')]:
            s = result['summaries'][regime].get(cat_key)
            if s:
                cv_icon, _ = cv_warning_level(s.get('cv'))
                out.append(f"    {label:<8} ${s.get('p25', 0):.2f} / ${s.get('median', 0):.2f} / ${s.get('p75', 0):.2f}  CV: {(s.get('cv') or 0)*100:.0f}% {cv_icon}")
    
    # Mevcut fiyat karşılaştırma
    price = p['price']
    out.append(f"\n💰 MEVCUT FİYAT (${price}) - Ana senaryo karşılaştırma:")
    for regime, label in [('bear', '🐻'), ('normal', '⚖️'), ('bull', '🐂')]:
        s = result['summaries'][regime].get('main')
        if s and s.get('median'):
            diff = (price - s['median']) / s['median'] * 100
            sign = "+" if diff > 0 else ""
            yorum = "pahalı" if diff > 0 else "ucuz"
            out.append(f"  {label} {regime.capitalize()} medyan ${s['median']:.2f} → %{sign}{diff:.1f} {yorum}")
    
    # Analist konsensüs
    if result['analyst_targets']:
        at = result['analyst_targets']
        out.append(f"\n🎯 ANALİST KONSENSÜSÜ:")
        out.append(f"  Aralık: ${at.get('targetLow', 0)} - ${at.get('targetHigh', 0)}  |  Medyan: ${at.get('targetMedian', 0)}  |  Konsensüs: ${at.get('targetConsensus', 0)}")
        if at.get('targetConsensus'):
            cd = (price - at['targetConsensus']) / at['targetConsensus'] * 100
            sign = "+" if cd > 0 else ""
            out.append(f"  Mevcut fiyat konsensüsten %{sign}{cd:.1f} {'yukarda' if cd > 0 else 'aşağıda'}")
    
    # Karar
    out.append(f"\n🎲 OTOMATIK KARAR ({result['summaries']['normal']['main_label'] if result['summaries']['normal']['main'] else 'N/A'} bazlı):")
    out.append(f"  {result['decision']['action']}")
    out.append(f"     {result['decision']['reasoning']}")
    
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
