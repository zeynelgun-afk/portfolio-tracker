#!/usr/bin/env python3
"""
Adil Değer - 9 Yöntem × 3 Senaryo Hesaplayıcı v5.0
Finzora AI v3.7.2 metodolojisi

v5.0 Değişiklikleri (11 Mayıs 2026):
- SADELEŞTIRME: 4 yöntem kaldırıldı (Graham Number, EV/EBIT, Justified P-B, Rule of 40)
  → Skill ismindeki "9 Yöntem" ile içerik tutarlı: 4 Traditional + 2 Forward + 3 Growth = 9
- FMP Ultimate plan entegrasyonu (fmp_layer.py):
  * ratios-ttm + key-metrics-ttm hazır oranlar (manuel hesap kaldırıldı)
  * sector-pe-snapshot + industry-pe-snapshot canlı sektör P/E (statik SECTOR_MULTIPLES fallback)
  * financial-scores: Altman Z + Piotroski risk skorları
  * grades-consensus + historical: analist sentiment + upgrade momentum
  * discounted-cash-flow: FMP'nin kendi DCF (sanity check)
  * revenue-product/geographic-segmentation: konsantrasyon riski otomatik
  * enterprise-values 5y: tarihsel multiple bandı
  * treasury-rates + CAPM: dinamik WACC
  * ipos-calendar: otomatik pre-IPO tespit
- YIL YIL PROJEKSİYON: projection_engine.py entegrasyonu
  * 5 yıllık tam P&L (gelir, brüt, faaliyet, vergi, net, EPS)
  * Forward P/E, P/S, EV/Sales yıl yıl projeksiyon
  * "Hangi yıl sektör medyanına oturur?" yorumu
- Reverse DCF yöntem listesinden çıkarıldı, bilgi notu olarak çıkış aşağıda

v4.1: Mantık denetimi sonrası 8 hata düzeltildi
v4.0: Quality/Moat Premium
v3.0: DUAL-MODE GROWTH vs BLENDED
v2.0: k_e cap, RIM fallback, CV uyarı, Forward outlier, AI mega-cap, Analist konsensüs
v1.0: 9 yöntem temel hesap
"""

import os
import sys
import json
import time
import requests
import statistics
from datetime import datetime

# v5.0: fmp_layer ve projection_engine modüllerini import et
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:
    import fmp_layer
    import projection_engine
    _V5_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ v5.0 modülleri yüklenemedi ({e}), v4.1 mode'a düşülüyor", file=sys.stderr)
    _V5_MODULES_AVAILABLE = False

API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
BASE = "https://financialmodelingprep.com/stable"
HEADERS = {"User-Agent": "finzora-ai-adil-deger/5.0"}


def fetch(endpoint, params=None, timeout=30, max_retries=3, retry_delay=1.5):
    """
    FMP API çağrısı.
    
    v4.1 düzeltmesi: Retry mekanizması (429/503/network için 3 deneme).
    Eskiden transient hatalarda sessizce None dönerek tüm pipeline'ın
    yanlış sonuç vermesine yol açıyordu (örn. 'eksik veri' yanılgısı).
    
    - 200: başarılı
    - 429 (rate limit): exponential backoff
    - 503 (overload): sabit retry_delay
    - Network error: retry
    - Diğer 4xx: kalıcı hata, None
    """
    p = {"apikey": API_KEY}
    if params:
        p.update(params)
    
    last_error = None
    for attempt in range(max_retries):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params=p, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                wait = retry_delay * (2 ** attempt)
                print(f"  [retry] {endpoint} 429 rate limit, {wait}s bekleniyor (deneme {attempt+1}/{max_retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            elif r.status_code == 503:
                print(f"  [retry] {endpoint} 503 overload, {retry_delay}s bekleniyor (deneme {attempt+1}/{max_retries})", file=sys.stderr)
                time.sleep(retry_delay)
                continue
            else:
                # 4xx kalıcı hata
                return None
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"  [retry] {endpoint} network error, {retry_delay}s bekleniyor (deneme {attempt+1}/{max_retries})", file=sys.stderr)
                time.sleep(retry_delay)
                continue
        except Exception as e:
            last_error = e
            break
    
    if last_error:
        print(f"FMP hata {endpoint}: {last_error}", file=sys.stderr)
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
    'tech_software':       {'pe': 28, 'fwd_pe': 24, 'ev_ebit': 22, 'ev_ebitda': 18, 'ev_rev': 6.0, 'p_fcf': 28, 'roe_target': 0.20, 'net_margin_target': 0.20, 'g_high': 0.12},
    'tech_hardware':       {'pe': 22, 'fwd_pe': 20, 'ev_ebit': 17, 'ev_ebitda': 13, 'ev_rev': 3.5, 'p_fcf': 22, 'roe_target': 0.18, 'net_margin_target': 0.12, 'g_high': 0.08},
    'semicon_design':      {'pe': 28, 'fwd_pe': 24, 'ev_ebit': 22, 'ev_ebitda': 18, 'ev_rev': 7.0, 'p_fcf': 30, 'roe_target': 0.25, 'net_margin_target': 0.20, 'g_high': 0.15},
    'semicon_osat':        {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 2.0, 'p_fcf': 22, 'roe_target': 0.15, 'net_margin_target': 0.08, 'g_high': 0.08},
    'semicon_equipment':   {'pe': 26, 'fwd_pe': 22, 'ev_ebit': 20, 'ev_ebitda': 16, 'ev_rev': 6.0, 'p_fcf': 26, 'roe_target': 0.22, 'net_margin_target': 0.22, 'g_high': 0.12},
    'financials_bank':     {'pe': 11, 'fwd_pe': 10, 'ev_ebit': 9, 'ev_ebitda': 8, 'ev_rev': 3.0, 'p_fcf': 12, 'roe_target': 0.12, 'net_margin_target': 0.22, 'g_high': 0.05},
    'financials_insurance':{'pe': 12, 'fwd_pe': 11, 'ev_ebit': 10, 'ev_ebitda': 9, 'ev_rev': 2.0, 'p_fcf': 12, 'roe_target': 0.12, 'net_margin_target': 0.10, 'g_high': 0.05},
    'financials_other':    {'pe': 14, 'fwd_pe': 13, 'ev_ebit': 12, 'ev_ebitda': 10, 'ev_rev': 3.0, 'p_fcf': 14, 'roe_target': 0.13, 'net_margin_target': 0.15, 'g_high': 0.06},
    'healthcare_pharma':   {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 15, 'ev_ebitda': 12, 'ev_rev': 4.0, 'p_fcf': 20, 'roe_target': 0.18, 'net_margin_target': 0.18, 'g_high': 0.06},
    'healthcare_biotech':  {'pe': 25, 'fwd_pe': 22, 'ev_ebit': 20, 'ev_ebitda': 16, 'ev_rev': 6.0, 'p_fcf': 25, 'roe_target': 0.15, 'net_margin_target': 0.15, 'g_high': 0.12},
    'healthcare_devices':  {'pe': 24, 'fwd_pe': 20, 'ev_ebit': 18, 'ev_ebitda': 15, 'ev_rev': 5.0, 'p_fcf': 24, 'roe_target': 0.18, 'net_margin_target': 0.16, 'g_high': 0.08},
    'consumer_staples':    {'pe': 20, 'fwd_pe': 18, 'ev_ebit': 16, 'ev_ebitda': 13, 'ev_rev': 2.5, 'p_fcf': 22, 'roe_target': 0.18, 'net_margin_target': 0.12, 'g_high': 0.05},
    'consumer_discretionary':{'pe':18,'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 2.0, 'p_fcf': 20, 'roe_target': 0.15, 'net_margin_target': 0.07, 'g_high': 0.07},
    'industrials':         {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 2.0, 'p_fcf': 20, 'roe_target': 0.15, 'net_margin_target': 0.10, 'g_high': 0.06},
    'energy':              {'pe': 12, 'fwd_pe': 10, 'ev_ebit': 8, 'ev_ebitda': 6, 'ev_rev': 1.5, 'p_fcf': 12, 'roe_target': 0.12, 'net_margin_target': 0.10, 'g_high': 0.03},
    'reits':               {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 16, 'ev_rev': 7.0, 'p_fcf': 18, 'roe_target': 0.10, 'net_margin_target': 0.20, 'g_high': 0.04},
    'utilities':           {'pe': 18, 'fwd_pe': 16, 'ev_ebit': 14, 'ev_ebitda': 11, 'ev_rev': 3.0, 'p_fcf': 18, 'roe_target': 0.10, 'net_margin_target': 0.10, 'g_high': 0.04},
    'communication':       {'pe': 20, 'fwd_pe': 18, 'ev_ebit': 15, 'ev_ebitda': 10, 'ev_rev': 3.0, 'p_fcf': 20, 'roe_target': 0.15, 'net_margin_target': 0.15, 'g_high': 0.06},
    'generic':             {'pe': 20, 'fwd_pe': 17, 'ev_ebit': 15, 'ev_ebitda': 12, 'ev_rev': 2.5, 'p_fcf': 22, 'roe_target': 0.15, 'net_margin_target': 0.10, 'g_high': 0.07},
}


# =============================================================================
# QUALITY/MOAT PREMIUM (v4 yeni)
# =============================================================================

def calculate_quality_premium(roe, net_margin, sector_mults):
    """
    Sektör lideri/kalite şirketleri için premium multiplier.
    
    İki bileşen geometrik ortalama:
    - ROE premium: ROE / sektör hedef (1.0-1.50 cap)
    - Margin premium: Net Margin / sektör hedef (1.0-1.30 cap)
    
    Final cap: 1.50x (en kaliteli şirketlerde bile %50 prim üst sınırı)
    
    Sadece çarpan bazlı yöntemlere uygulanır:
    - P/E, Forward P/E, EV/EBIT, EV/EBITDA, EV/Revenue, P/FCF, EV/FWD x
    
    Skip edilenler (çift sayım önleme):
    - Justified P-B (zaten ROE'yi içerir)
    - Graham (klasik formül)
    - DCF (büyüme bazlı)
    - PEG (büyüme bazlı)
    - Rule of 40 (margin'i zaten içerir)
    """
    if not roe or roe <= 0 or not net_margin or net_margin <= 0:
        return 1.0, {'roe_ratio': 1.0, 'margin_ratio': 1.0, 'note': 'Veri yetersiz'}
    
    sector_roe = sector_mults.get('roe_target', 0.15)
    sector_margin = sector_mults.get('net_margin_target', 0.10)
    
    roe_ratio = roe / sector_roe
    margin_ratio = net_margin / sector_margin
    
    # Cap'ler
    roe_premium = max(1.0, min(1.50, roe_ratio))
    margin_premium = max(1.0, min(1.30, margin_ratio))
    
    # Geometrik ortalama
    quality_mult = (roe_premium * margin_premium) ** 0.5
    quality_mult = min(1.50, quality_mult)
    
    # Yorum
    if quality_mult >= 1.30:
        note = f"⭐ KALİTE ÖNCÜSÜ ({quality_mult:.2f}x prim)"
    elif quality_mult >= 1.15:
        note = f"💎 Kalite şirket ({quality_mult:.2f}x prim)"
    elif quality_mult >= 1.05:
        note = f"Hafif kalite primi ({quality_mult:.2f}x)"
    else:
        note = "Sektör ortalaması"
    
    return quality_mult, {
        'roe_ratio': round(roe_ratio, 2),
        'margin_ratio': round(margin_ratio, 2),
        'roe_premium_capped': round(roe_premium, 2),
        'margin_premium_capped': round(margin_premium, 2),
        'final': round(quality_mult, 2),
        'note': note,
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
    
    # Sadece REGIME_ADJ'da bulunan key'leri kullan ('bear', 'normal', 'bull')
    # 'bear_light' kaldırıldı (REGIME_ADJ'da tanımlı değildi, ölü kod)
    regime = 'normal'
    if vix is not None and spy_dist is not None:
        if vix < 16 and spy_dist > 0.05:
            regime = 'bull'
        elif vix > 28 or spy_dist < -0.05:
            regime = 'bear'
        elif vix > 22:
            # Eski 'bear_light' yerine bear'a düş (REGIME_ADJ tutarlı kalır)
            regime = 'bear'
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
    
    v4.1 düzeltmeleri:
    - Negatif FCF'de None döner (önceki: 1M'lık baz alıp anlamsız growth çıkarırdı)
    - Binary search ceiling'e (%50) yapışma kontrolü — sonuç >= %49 ise None (anlamsız)
    """
    if shares <= 0 or current_price <= 0:
        return None
    if start_fcf <= 0:
        # Negatif/sıfır FCF'de reverse DCF anlamsız
        return None
    
    target_equity = current_price * shares
    target_ev = target_equity + debt - cash
    
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
    
    # Ceiling yapışma kontrolü — anlamsız sonuç
    if implied_growth >= 0.49:
        return None  # Mevcut fiyat %50+ yıllık büyüme implied ediyor — saçma
    if implied_growth <= 0.001:
        return None  # 0% growth — yine anlamsız (FCF'i mevcut fiyatı haklı çıkarıyor)
    
    return implied_growth


# =============================================================================
# YENİ v3: GROWTH YÖNTEMLERİ
# =============================================================================

def calc_peg(eps_fwd_1y, growth_pct, peg_target):
    """
    PEG Ratio yöntemi: Adil Forward P/E = PEG_target × growth(%)
    Adil Fiyat = NTM EPS (1 yıl ileri) × Adil Forward P/E
    
    DİKKAT: 1 yıl ileri EPS (NTM) kullanılır, 2 yıl ileri DEĞİL.
    2 yıl ileri EPS × P/E hesabı 2 yıl sonraki future-priced fair value verir,
    bugünkü adil değer için iskonto edilmesi gerekirdi. Bunun yerine 1y ileri EPS direkt kullan.
    
    v4.1 düzeltmesi (v4.0'da eps_fwd_2y kullanıyordu, %30+ fazla yüksek değer veriyordu).
    """
    if not eps_fwd_1y or eps_fwd_1y <= 0 or growth_pct is None:
        return None
    if growth_pct < 0.05:
        return None  # Düşük büyümede PEG anlamsız
    growth_pct_for_peg = growth_pct * 100  # %30 büyüme = 30
    target_pe = peg_target * growth_pct_for_peg
    return eps_fwd_1y * target_pe


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

def calculate_methods(data, regime_key, sector_key, is_ai_megacap, mode, quality_mult=1.0, forward_outlier=False):
    """
    v5.0: 13 yöntem → 9 yöntem (Graham, EV/EBIT, Justified P-B, Rule of 40 çıkarıldı).
    Toplam: 4 Traditional + 2 Forward + 3 Growth = 9
    
    mode: 'GROWTH' veya 'BLENDED'
    quality_mult: v4 - Sektör lideri/kalite premium çarpanı (1.0-1.50)
    forward_outlier: v4.1 - True ise Forward P/E ve EV/FWD x yöntemleri None'a düşürülür
    """
    sector_mults = SECTOR_MULTIPLES.get(sector_key, SECTOR_MULTIPLES['generic'])
    adj = REGIME_ADJ[regime_key]
    
    eps_ttm = data['eps_ttm']
    eps_fwd_1y = data.get('eps_fwd_1y')  # v4.1: PEG için 1y ileri EPS
    eps_fwd = data['eps_fwd_2y']
    revenue = data['revenue_ttm']
    rev_fwd = data['revenue_fwd_2y']
    ebitda = data['ebitda_ttm']
    ebitda_fwd = data['ebitda_fwd_2y']
    fcf_norm = data['fcf_normalized']
    cash = data['cash']
    debt = data['total_debt']
    shares = data['shares']
    
    # AI mega-cap boğa primi (v5.0: ev_ebit çıkarıldı)
    if is_ai_megacap and regime_key == 'bull':
        ai_mult = AI_MEGACAP_BULL_PREMIUM
    else:
        ai_mult = {k: 1.0 for k in ['pe', 'fwd_pe', 'ev_ebitda', 'ev_rev', 'p_fcf']}
    
    # v4: Quality premium hangi yöntemlere uygulanır
    # v5.0: Justified P-B + Graham + Rule of 40 zaten kaldırıldı
    qm = quality_mult  # Kısaltma
    
    traditional = {}
    forward = {}
    growth = {}
    notes = {}
    
    # === TRADITIONAL (TTM bazlı 4 yöntem - v5.0) ===
    
    # 1. Net P/E
    if eps_ttm and eps_ttm > 0:
        traditional['Net P/E'] = eps_ttm * sector_mults['pe'] * adj['pe'] * ai_mult['pe'] * qm
    else:
        traditional['Net P/E'] = None
    
    # 2. EV/EBITDA (EV/EBIT v5.0'da kaldırıldı, EV/EBITDA ile yer değiştirme zaten)
    if ebitda and ebitda > 0 and shares > 0:
        ev = ebitda * sector_mults['ev_ebitda'] * adj['ev_ebitda'] * ai_mult['ev_ebitda'] * qm
        traditional['EV/EBITDA'] = (ev + cash - debt) / shares
    else:
        traditional['EV/EBITDA'] = None
    
    # 3. EV/Revenue
    if revenue and revenue > 0 and shares > 0:
        ev = revenue * sector_mults['ev_rev'] * adj['ev_rev'] * ai_mult['ev_rev'] * qm
        traditional['EV/Revenue'] = (ev + cash - debt) / shares
    else:
        traditional['EV/Revenue'] = None
    
    # 4. P/FCF
    if fcf_norm and fcf_norm > 0 and shares > 0:
        traditional['P/FCF'] = (fcf_norm / shares) * sector_mults['p_fcf'] * adj['p_fcf'] * ai_mult['p_fcf'] * qm
    else:
        traditional['P/FCF'] = None
    
    # NOT: v5.0 çıkarılan yöntemler:
    # - Justified P-B (Gordon/RIM) — karmaşık, modern büyüme şirketlerinde yanıltıcı
    # - Graham Number — 1949'dan kalma, kalite şirketleri ve AI/tech için saçma sonuç
    # - EV/EBIT — EV/EBITDA ile tekrar; D&A farkı ihmal edilebilir
    
    # === FORWARD (2 yöntem) ===
    
    # 5. Forward P/E
    if eps_fwd and eps_fwd > 0 and not forward_outlier:
        forward['Forward P/E'] = eps_fwd * sector_mults['fwd_pe'] * adj['fwd_pe'] * ai_mult['fwd_pe'] * qm
    else:
        forward['Forward P/E'] = None
        if forward_outlier:
            notes['Forward P/E'] = "⚠️ ELENDİ (forward outlier: EPS_FWD/EPS_TTM > 2.5x)"
    
    # 6. DCF
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
    
    # === GROWTH (3 yöntem - v5.0: Rule of 40 çıkarıldı) ===
    
    # Forward growth oranı (PEG için)
    forward_growth = None
    if eps_fwd and eps_ttm and eps_ttm > 0:
        # 2 yıllık büyüme → yıllık geometrik
        forward_growth = (eps_fwd / eps_ttm) ** 0.5 - 1
    
    # 7. PEG
    if forward_outlier:
        growth['PEG'] = None
        notes['PEG'] = "⚠️ ELENDİ (forward outlier)"
    else:
        eps_for_peg = eps_fwd_1y
        if not eps_for_peg and eps_ttm and eps_ttm > 0 and forward_growth:
            eps_for_peg = eps_ttm * (1 + forward_growth)
        growth['PEG'] = calc_peg(eps_for_peg, forward_growth, adj['peg_target'])
    
    # 8. EV/Forward Revenue
    if forward_outlier:
        growth['EV/FWD Revenue'] = None
        notes['EV/FWD Revenue'] = "⚠️ ELENDİ (forward outlier)"
    else:
        growth['EV/FWD Revenue'] = calc_ev_forward_revenue(
            rev_fwd, sector_mults['ev_rev'] * adj['ev_rev'] * ai_mult['ev_rev'] * qm,
            cash, debt, shares
        )
    
    # 9. EV/Forward EBITDA
    if forward_outlier:
        growth['EV/FWD EBITDA'] = None
        notes['EV/FWD EBITDA'] = "⚠️ ELENDİ (forward outlier)"
    else:
        growth['EV/FWD EBITDA'] = calc_ev_forward_ebitda(
            ebitda_fwd, sector_mults['ev_ebitda'] * adj['ev_ebitda'] * ai_mult['ev_ebitda'] * qm,
            cash, debt, shares
        )
    
    # NOT: Rule of 40 v5.0'da çıkarıldı — saf SaaS şirketleri için, portföyde yok
    
    # Reverse DCF (sadece bilgi amaçlı, yöntem listesinde değil)
    # Çıktıya not olarak eklenecek
    
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
    """
    BLENDED modu için ağırlıklı medyan.
    
    Eğer summary'lerden biri yoksa veya kritik alanı (p25/median/p75) None ise:
    - Diğerine 100% ağırlık ver (fallback)
    - Eğer ikisi de yoksa None döner
    
    Mevcut bug (v4.0'da): None × float TypeError verirdi (RUNTIME CRASH).
    v4.1: None değerleri akıllı atlatma + ağırlık yeniden normalize.
    """
    has_trad = traditional_summary is not None
    has_fwd = forward_growth_summary is not None
    
    if not has_trad and not has_fwd:
        return None
    if not has_trad:
        # Sadece forward+growth varsa direkt kullan
        return {**forward_growth_summary, "weights": {"traditional": 0.0, "forward_growth": 1.0}}
    if not has_fwd:
        # Sadece traditional varsa direkt kullan
        return {**traditional_summary, "weights": {"traditional": 1.0, "forward_growth": 0.0}}
    
    out = {"weights": {"traditional": w_trad, "forward_growth": w_fwd}}
    for key in ("p25", "median", "p75", "mean"):
        t_val = traditional_summary.get(key)
        f_val = forward_growth_summary.get(key)
        # Akıllı None handling — birinin değeri yoksa diğerine 100% düş
        if t_val is None and f_val is None:
            out[key] = None
        elif t_val is None:
            out[key] = f_val
        elif f_val is None:
            out[key] = t_val
        else:
            out[key] = t_val * w_trad + f_val * w_fwd
    return out


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
    
    # Forward EPS, Revenue, EBITDA — dinamik yıl seçimi (v4.1)
    # 2 yıl ileri (Forward P/E, EV/FWD x için) ve 1 yıl ileri (PEG için NTM EPS)
    eps_fwd_2y = None
    eps_fwd_1y = None
    rev_fwd_2y = None
    ebitda_fwd_2y = None
    if est_list:
        sorted_est = sorted(est_list, key=lambda x: x.get('date', ''))
        this_year = datetime.now().year
        target_year_2y = str(this_year + 2)  # Bugün 2026 → 2028
        target_year_1y = str(this_year + 1)  # Bugün 2026 → 2027
        
        # 2 yıl ileri estimate
        for est in sorted_est:
            date = est.get('date', '')
            if date and date >= target_year_2y:
                eps_fwd_2y = safe_get(est, 'epsAvg')
                rev_fwd_2y = safe_get(est, 'revenueAvg')
                ebitda_fwd_2y = safe_get(est, 'ebitdaAvg')
                break
        # Fallback: en uzak yıl
        if not eps_fwd_2y and sorted_est:
            last = sorted_est[-1]
            eps_fwd_2y = safe_get(last, 'epsAvg')
            rev_fwd_2y = safe_get(last, 'revenueAvg')
            ebitda_fwd_2y = safe_get(last, 'ebitdaAvg')
        
        # 1 yıl ileri estimate (PEG için NTM EPS)
        for est in sorted_est:
            date = est.get('date', '')
            if date and date >= target_year_1y and date < target_year_2y:
                eps_fwd_1y = safe_get(est, 'epsAvg')
                break
        if not eps_fwd_1y and sorted_est:
            # Fallback: 2 yıl ileri yoksa ilk available
            for est in sorted_est:
                date = est.get('date', '')
                if date >= target_year_1y:
                    eps_fwd_1y = safe_get(est, 'epsAvg')
                    break
    
    market_cap = safe_get(quote, 'marketCap') or safe_get(profile, 'mktCap')
    price = safe_get(quote, 'price') or safe_get(profile, 'price')
    
    # v4.1 düzeltmesi: shares hesabında çok katmanlı fallback
    # Eskiden sadece mcap/price — eğer ikisi de 0 ise shares=0 olur (tüm hesaplar bozulur).
    # Yeni: sharesOutstanding (FMP) öncelik, mcap/price fallback.
    shares = (
        safe_get(profile, 'sharesOutstanding')  # FMP profile'da varsa direkt
        or safe_get(quote, 'sharesOutstanding')   # Quote'ta varsa
        or (market_cap / price if price > 0 else 0)  # Hesaplı fallback
    )
    
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
    
    # v4 YENİ: Quality/Moat Premium hesabı
    sector_mults_for_qm = SECTOR_MULTIPLES.get(sector_key, SECTOR_MULTIPLES['generic'])
    quality_mult, quality_detail = calculate_quality_premium(roe, net_margin, sector_mults_for_qm)
    
    data_pack = {
        'eps_ttm': eps_ttm, 'eps_fwd_1y': eps_fwd_1y, 'eps_fwd_2y': eps_fwd_2y, 'bvps': bvps,
        'revenue_ttm': revenue_ttm, 'revenue_fwd_2y': rev_fwd_2y,
        'ebit_ttm': ebit_ttm, 'ebitda_ttm': ebitda_ttm, 'ebitda_fwd_2y': ebitda_fwd_2y,
        'fcf_normalized': fcf_normalized, 'ocf_ttm': ocf_ttm,
        'cash': cash, 'total_debt': total_debt, 'shares': shares,
        'roe': roe, 'beta': safe_get(profile, 'beta', 1.0) or 1.0,
        'revenue_growth_yoy': revenue_growth_yoy,
    }
    
    # 3 senaryoda hesapla (v4: quality_mult ile, v4.1: forward_outlier ile)
    results = {}
    notes_all = {}
    for regime in ['bear', 'normal', 'bull']:
        m = calculate_methods(data_pack, regime, sector_key, is_ai_megacap, mode, quality_mult,
                              forward_outlier=forward_outlier)
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
    
    # =========================================================================
    # v5.0 EKSTRA SİNYALLER (fmp_layer)
    # =========================================================================
    
    v5_signals = {}
    if _V5_MODULES_AVAILABLE:
        try:
            # Altman Z + Piotroski (risk skorları)
            scores = fmp_layer.get_financial_scores(ticker)
            if scores:
                z_val, z_lbl, z_emoji = fmp_layer.interpret_altman_z(scores.get('altmanZScore'))
                if z_val is not None:
                    v5_signals['altman_z'] = {'value': round(z_val, 2), 'label': z_lbl, 'emoji': z_emoji}
                p_val, p_lbl, p_emoji = fmp_layer.interpret_piotroski(scores.get('piotroskiScore'))
                if p_val is not None:
                    v5_signals['piotroski'] = {'value': p_val, 'label': p_lbl, 'emoji': p_emoji}
            
            # Analist sentiment + momentum
            consensus = fmp_layer.get_grades_consensus(ticker)
            if consensus:
                v5_signals['grades_consensus'] = {
                    'strong_buy': consensus.get('strongBuy', 0),
                    'buy': consensus.get('buy', 0),
                    'hold': consensus.get('hold', 0),
                    'sell': consensus.get('sell', 0),
                    'strong_sell': consensus.get('strongSell', 0),
                    'consensus_label': consensus.get('consensus'),
                }
            
            grades_hist = fmp_layer.get_grades_historical(ticker)
            momentum = fmp_layer.detect_upgrade_momentum(grades_hist, lookback_months=6)
            if momentum:
                v5_signals['upgrade_momentum'] = momentum
            
            # FMP'nin kendi DCF (sanity check)
            fmp_dcf = fmp_layer.get_fmp_dcf(ticker)
            if fmp_dcf and fmp_dcf.get('dcf'):
                v5_signals['fmp_dcf'] = {
                    'value': round(float(fmp_dcf.get('dcf', 0)), 2),
                    'stock_price': fmp_dcf.get('Stock Price'),
                }
            
            fmp_dcf_lev = fmp_layer.get_fmp_dcf(ticker, levered=True)
            if fmp_dcf_lev and fmp_dcf_lev.get('dcf'):
                v5_signals['fmp_dcf_levered'] = {'value': round(float(fmp_dcf_lev.get('dcf', 0)), 2)}
            
            # Konsantrasyon riski (product + geographic)
            prod_segs = fmp_layer.get_revenue_product_segmentation(ticker)
            prod_risk = fmp_layer.detect_concentration_risk(prod_segs)
            if prod_risk:
                v5_signals['concentration_risk_product'] = prod_risk
            
            geo_segs = fmp_layer.get_revenue_geographic_segmentation(ticker)
            geo_risk = fmp_layer.detect_concentration_risk(geo_segs)
            if geo_risk:
                v5_signals['concentration_risk_geo'] = geo_risk
            
            # Canlı sektör/industry P/E
            static_pe = SECTOR_MULTIPLES.get(sector_key, SECTOR_MULTIPLES['generic']).get('pe', 20)
            live_pe, live_pe_source = fmp_layer.get_live_pe_for_sector_key(sector_key, static_fallback_pe=static_pe)
            v5_signals['live_pe'] = {
                'value': round(live_pe, 2) if live_pe else None,
                'source': live_pe_source,
                'static_fallback': static_pe,
                'delta_pct': round((live_pe - static_pe) / static_pe * 100, 1) if (live_pe and static_pe) else None,
            }
            
            # Dinamik WACC (CAPM ile)
            dyn_wacc, wacc_source = fmp_layer.calculate_dynamic_wacc(beta=safe_get(profile, 'beta', 1.2))
            v5_signals['dynamic_wacc'] = {
                'value': round(dyn_wacc * 100, 2),
                'source': wacc_source,
                'static_fallback': round(REGIME_ADJ[market['regime'].lower()]['wacc'] * 100, 1),
            }
            
            # Pre-IPO tespiti (genelde False döner, IPO calendar'daysa True)
            pre_ipo = fmp_layer.is_ticker_pre_ipo(ticker)
            if pre_ipo:
                v5_signals['pre_ipo'] = pre_ipo
        
        except Exception as e:
            print(f"⚠️ v5.0 sinyalleri toplanırken hata: {e}", file=sys.stderr)
    
    return {
        'ticker': ticker,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'version': '5.0',
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
        'quality_mult': quality_mult,
        'quality_detail': quality_detail,
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
        'v5_signals': v5_signals,
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
    
    # v4: Quality premium bilgisi
    qd = result.get('quality_detail', {})
    if qd and qd.get('final', 1.0) > 1.05:
        out.append(f"  {qd['note']}")
        out.append(f"     ROE oranı: {qd['roe_ratio']}x sektör hedef | Margin oranı: {qd['margin_ratio']}x sektör hedef")
    
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
    
    # v5.0 YENİ SİNYALLER
    v5 = result.get('v5_signals', {})
    if v5:
        out.append("")
        out.append("─" * 75)
        out.append("  v5.0 EK SİNYALLER (Ultimate FMP Plan)")
        out.append("─" * 75)
        
        # Risk skorları
        if v5.get('altman_z') or v5.get('piotroski'):
            out.append("\n🛡️  RİSK SKORLARI:")
            if v5.get('altman_z'):
                az = v5['altman_z']
                out.append(f"  Altman Z (iflas riski): {az['value']:.2f} → {az['emoji']} {az['label']}")
            if v5.get('piotroski'):
                pi = v5['piotroski']
                out.append(f"  Piotroski (kalite): {pi['value']}/9 → {pi['emoji']} {pi['label']}")
        
        # Analist sentiment
        if v5.get('grades_consensus'):
            gc = v5['grades_consensus']
            total = gc['strong_buy'] + gc['buy'] + gc['hold'] + gc['sell'] + gc['strong_sell']
            out.append(f"\n📊 ANALİST SENTIMENT (toplam {total}):")
            out.append(f"  💚 Strong Buy: {gc['strong_buy']}  |  Buy: {gc['buy']}  |  ⚪ Hold: {gc['hold']}  |  Sell: {gc['sell']}  |  ❤️ Strong Sell: {gc['strong_sell']}")
            if gc.get('consensus_label'):
                out.append(f"  Konsensüs: {gc['consensus_label']}")
        
        if v5.get('upgrade_momentum'):
            um = v5['upgrade_momentum']
            out.append(f"  Son 6 ay: {um['label']}")
        
        # FMP DCF karşılaştırma
        if v5.get('fmp_dcf'):
            fd = v5['fmp_dcf']
            our_dcf_normal = None
            try:
                our_dcf_normal = result['methods_by_regime']['normal']['forward'].get('DCF')
            except (KeyError, TypeError):
                pass
            out.append(f"\n📐 DCF SANITY CHECK:")
            out.append(f"  FMP DCF (unlevered): ${fd['value']:.2f}")
            if v5.get('fmp_dcf_levered'):
                out.append(f"  FMP DCF (levered):   ${v5['fmp_dcf_levered']['value']:.2f}")
            if our_dcf_normal:
                out.append(f"  Bizim DCF (normal):  ${our_dcf_normal:.2f}")
                diff_pct = (our_dcf_normal - fd['value']) / fd['value'] * 100
                if abs(diff_pct) > 30:
                    out.append(f"  ⚠️ Fark %{diff_pct:+.0f} — varsayımlar farklı, gözden geçir")
                else:
                    out.append(f"  Fark %{diff_pct:+.0f} (uyumlu)")
        
        # Konsantrasyon riski
        if v5.get('concentration_risk_product') or v5.get('concentration_risk_geo'):
            out.append(f"\n🎯 KONSANTRASYON RİSKİ:")
            if v5.get('concentration_risk_product'):
                cr = v5['concentration_risk_product']
                out.append(f"  Ürün/Segment ({cr['fiscal_year']}): {cr['label']}")
                out.append(f"    Top: {cr['top_segment']} %{cr['top_share_pct']} | Top 2: %{cr['top2_share_pct']}")
            if v5.get('concentration_risk_geo'):
                cr = v5['concentration_risk_geo']
                out.append(f"  Coğrafya ({cr['fiscal_year']}): {cr['label']}")
                out.append(f"    Top: {cr['top_segment']} %{cr['top_share_pct']} | Top 2: %{cr['top2_share_pct']}")
        
        # Canlı sektör P/E vs statik
        if v5.get('live_pe') and v5['live_pe'].get('value'):
            lp = v5['live_pe']
            out.append(f"\n🌐 CANLI SEKTÖR P/E:")
            src_label = {'industry': 'industry-pe-snapshot', 'sector': 'sector-pe-snapshot', 'static': 'statik tablo (API down)'}.get(lp['source'], lp['source'])
            out.append(f"  Canlı: {lp['value']:.1f}x ({src_label})  |  Statik (skill içi): {lp['static_fallback']}x")
            if lp.get('delta_pct') is not None and abs(lp['delta_pct']) > 15:
                yon = "yukarıda" if lp['delta_pct'] > 0 else "aşağıda"
                out.append(f"  ⚠️ Statik tablo %{lp['delta_pct']:+.0f} sapmış — sektör eskimiş tabloya göre {yon}")
        
        # Dinamik WACC
        if v5.get('dynamic_wacc'):
            dw = v5['dynamic_wacc']
            out.append(f"\n💰 DİNAMİK WACC (CAPM):")
            out.append(f"  Canlı: %{dw['value']:.2f} ({dw['source']})  |  Statik fallback: %{dw['static_fallback']}")
        
        # Pre-IPO uyarısı
        if v5.get('pre_ipo'):
            pi = v5['pre_ipo']
            out.append(f"\n🆕 PRE-IPO UYARISI:")
            out.append(f"  IPO Tarihi: {pi.get('ipo_date')}  |  Aralık: {pi.get('price_range')}")
            out.append(f"  ⚠️ Pre-IPO veri eksik — FMP TTM yok, manuel analiz gerekli")
    
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
