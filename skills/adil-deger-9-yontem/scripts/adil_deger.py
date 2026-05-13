#!/usr/bin/env python3
"""
Adil Değer - 9 Yöntem × 3 Senaryo Hesaplayıcı v5.3
Finzora AI v3.7.2 metodolojisi

v5.3 Değişiklikleri (12 Mayıs 2026):
- PEG GROWTH SOURCE HİYERARŞİ: Wall Street long-term growth standardı (analist multi-year CAGR).
  Hiyerarşi: 3y forward CAGR (FY1→FY4) → 2y forward CAGR (FY1→FY3) → 2y geometric (v5.2 fallback).
  Sustainable cap her durumda korunur (high-growth %50, mature %35).
  FMP docs: "We use compound annual growth rate to estimate revenue" — analyst-estimates
  zaten CAGR-based, multi-year extraction ile gerçek LTG elde edilir.
  LQDA: v5.2 raw growth %377 → cap'li %50 → v5.3 3y CAGR %36.6 (gerçek sürdürülebilir).
  est_list limit 4 → 6 yükseltildi (3y CAGR için en az 4 forward yıl gerekli).

v5.2 Değişiklikleri (12 Mayıs 2026 - LQDA v5.1 çıktısı analiz sonrası):
- PEG GROWTH CAP: forward_growth Lynch standardı sürdürülebilirlik tavanı.
  Sektör bazlı: high-growth (semicon/tech/biotech/comm) %50, mature %35.
  Inflection biotech (LQDA: raw 2y CAGR %377) PEG = $1590 saçma değer üretiyordu.
  v5.2: cap'li %50 → PEG ~makul aralık. forward_growth_capped flag + not eklendi.
- DCF FCF INFLECTION OVERRIDE: inflection_point + fcf_ttm > 0 ise
  fcf_normalized = fcf_ttm (TTM FCF, son 4 çeyrek toplamı).
  Önceki: cf_list[:4] yıllık ortalama → 3 yıl zarar dahil olduğu için DCF bastırılıyordu.
  LQDA fcf_ttm ~$41M (Q1-26 +$50M + Q4-25 +$42M + Q3-25 -$11M + Q2-25 -$40M) → DCF anlamlı.
- EV/FWD EBITDA PROXY: ebitda_fwd_2y yok/negatif (ALGORITHMIC quality veya analist eksik) iken
  rev_fwd × sektör_net_margin × marj çarpan ile proxy EBITDA hesaplanır.
  Çarpan: healthcare 1.5x, tech 1.4x, generic 1.3x. ebitda_proxy_used flag + not.

v5.1 Değişiklikleri (12 Mayıs 2026 - LQDA testi sonrası):
- INFLECTION POINT TESPİTİ (Forward outlier flag düzeltmesi):
  Son 2 çeyrek POZİTİF EPS + önceki 2 çeyrek NEGATİF EPS → gerçek karlılık dönüşümü
  → forward_outlier flag iptal, Forward P/E + PEG + EV/FWD yöntemleri korunur
  Tetikleyici örnek: LQDA Q4-2025 (+$0.17) + Q1-2026 (+$0.60) sonrası
  EPS_FWD/EPS_TTM = 21.56x ratio'ya rağmen Forward yöntemleri ELENMEDİ
  Önceki davranış: Inflection biotech'ler yanlışlıkla outlier sayılıp Forward elenirdi

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

try:
    import transcript_analyzer
    _TRANSCRIPT_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ transcript_analyzer yüklenemedi ({e})", file=sys.stderr)
    _TRANSCRIPT_ANALYZER_AVAILABLE = False

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
    
    # v5.0: Canlı PE override varsa kullan, yoksa statik tablodan al
    pe_mult = data.get('live_pe_override') or sector_mults['pe']
    # Forward P/E için canlı PE'yi biraz daha düşük kullan (klasik TTM>FWD ilişkisi)
    fwd_pe_mult = (data.get('live_pe_override') * 0.88) if data.get('live_pe_override') else sector_mults['fwd_pe']
    
    # v5.0: Dinamik WACC varsa DCF için kullan, yoksa statik tablodan
    wacc = data.get('dynamic_wacc') or adj['wacc']
    
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
    
    # 1. Net P/E (canlı PE override öncelikli)
    if eps_ttm and eps_ttm > 0:
        traditional['Net P/E'] = eps_ttm * pe_mult * adj['pe'] * ai_mult['pe'] * qm
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
    
    # 5. Forward P/E (canlı PE override öncelikli)
    if eps_fwd and eps_fwd > 0 and not forward_outlier:
        forward['Forward P/E'] = eps_fwd * fwd_pe_mult * adj['fwd_pe'] * ai_mult['fwd_pe'] * qm
    else:
        forward['Forward P/E'] = None
        if forward_outlier:
            notes['Forward P/E'] = "⚠️ ELENDİ (forward outlier: EPS_FWD/EPS_TTM > 2.5x)"
    
    # 6. DCF (dinamik WACC + gerçek revenue growth override öncelikli)
    # v5.0: Statik g_high yerine canlı revenue_yoy kullan (sektör multiple üst sınır 50%)
    static_g_high = sector_mults['g_high'] + adj['g_high_adj']
    actual_growth = data.get('revenue_growth_yoy')
    if actual_growth and actual_growth > static_g_high:
        # Gerçek büyüme statik tablodan yüksekse onu kullan, ama 50%'de cap'le
        g_high_eff = min(actual_growth, 0.50)
    else:
        g_high_eff = static_g_high
    
    forward['DCF'] = dcf_calculate(
        start_fcf=fcf_norm if fcf_norm and fcf_norm > 0 else (data['ocf_ttm'] * 0.3 if data['ocf_ttm'] else 0),
        g_high=g_high_eff,
        g_mid=g_high_eff * 0.6,
        g_term=adj['g_term'],
        wacc=wacc,
        cash=cash,
        debt=debt,
        shares=shares
    )
    if forward['DCF'] and forward['DCF'] <= 0:
        forward['DCF'] = None
    
    # === GROWTH (3 yöntem - v5.0: Rule of 40 çıkarıldı) ===
    
    # Forward growth oranı (PEG için)
    # v5.3 HİYERARŞİ:
    #   1. Birincil: 3y forward EPS CAGR (FY1→FY4) — Wall Street long-term standardı
    #   2. Fallback: 2y forward EPS CAGR (FY1→FY3)
    #   3. Fallback: 2y geometric (eps_fwd_2y/eps_ttm)^0.5 - 1 — v5.2 davranışı
    #   Tüm seçeneklerde sektör cap'i uygulanır (high-growth %50, mature %35).
    #
    # FMP analyst-estimates kendi "CAGR formula" ile türetilmiş yıllık tahminleri sağlar
    # (FMP docs onaylı). Multi-year CAGR bu yüzden en güvenilir LTG kaynağıdır.
    # Inflection biotech (LQDA: TTM EPS $0.26 → FWD EPS $5.46) için 2y geometric %377
    # saçma değer üretirken, multi-year CAGR %29-37 makul aralık verir.
    forward_growth = None
    forward_growth_raw = None
    forward_growth_capped = False
    forward_growth_source = None  # 'analyst_3y_cagr' / 'analyst_2y_cagr' / 'fwd_eps_geometric' / 'sector_default'
    
    # Sektör bazlı sürdürülebilirlik cap'i (her zaman uygulanır)
    if sector_key in {'semicon_design', 'semicon_growing', 'tech_software',
                      'healthcare_biotech', 'communication'}:
        sustainable_cap = 0.50  # %50 (high-growth sektörler)
    else:
        sustainable_cap = 0.35  # %35 (olgun/mature sektörler)
    
    # 1. ÖNCE: 3y analyst CAGR (Wall Street LTG standardı)
    cagr_3y = data.get('forward_eps_3y_cagr')
    cagr_2y = data.get('forward_eps_2y_cagr')
    
    if cagr_3y is not None and cagr_3y > 0:
        forward_growth_raw = cagr_3y
        forward_growth_source = 'analyst_3y_cagr'
    elif cagr_2y is not None and cagr_2y > 0:
        forward_growth_raw = cagr_2y
        forward_growth_source = 'analyst_2y_cagr'
    elif eps_fwd and eps_ttm and eps_ttm > 0:
        # Fallback: v5.2 2y geometric
        forward_growth_raw = (eps_fwd / eps_ttm) ** 0.5 - 1
        forward_growth_source = 'fwd_eps_geometric'
    
    if forward_growth_raw is not None:
        forward_growth = min(forward_growth_raw, sustainable_cap)
        forward_growth_capped = forward_growth_raw > sustainable_cap
    
    # 7. PEG
    if forward_outlier:
        growth['PEG'] = None
        notes['PEG'] = "⚠️ ELENDİ (forward outlier)"
    else:
        eps_for_peg = eps_fwd_1y
        if not eps_for_peg and eps_ttm and eps_ttm > 0 and forward_growth:
            eps_for_peg = eps_ttm * (1 + forward_growth)
        growth['PEG'] = calc_peg(eps_for_peg, forward_growth, adj['peg_target'])
        # v5.3: Hangi kaynak kullanıldığını + cap durumunu notla
        if growth['PEG']:
            source_labels = {
                'analyst_3y_cagr': '3y analist CAGR',
                'analyst_2y_cagr': '2y analist CAGR (fallback)',
                'fwd_eps_geometric': 'FWD EPS / TTM EPS geometric (v5.2 fallback)',
            }
            source_label = source_labels.get(forward_growth_source, forward_growth_source)
            base_note = f"📊 v5.3 GROWTH: %{forward_growth*100:.1f} ({source_label})"
            if forward_growth_capped:
                base_note += f" — raw %{forward_growth_raw*100:.0f} sustainable cap'le düşürüldü ({sector_key})"
            notes['PEG'] = base_note
    
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
        # v5.2: ebitda_fwd yok/negatif ise rev_fwd × sektör tipik EBITDA marjı ile proxy
        # Bu özellikle inflection biotech için kritik — analist EBITDA tahmini
        # ALGORITHMIC quality'de yanlış işaretli veya eksik gelebiliyor.
        ebitda_for_calc = ebitda_fwd
        ebitda_proxy_used = False
        ebitda_margin_proxy = None
        
        if (not ebitda_fwd or ebitda_fwd <= 0) and rev_fwd and rev_fwd > 0:
            # Sektör tipik EBITDA marjı: net_margin_target × marj çarpan
            # Healthcare/Pharma: × 1.5 (yüksek brüt + R&D)
            # Tech/SaaS: × 1.4 (yazılım marj profili)
            # Generic mature: × 1.3
            if 'healthcare' in sector_key:
                margin_mult = 1.5
            elif sector_key in {'tech_software', 'semicon_design', 'semicon_growing'}:
                margin_mult = 1.4
            else:
                margin_mult = 1.3
            net_margin_t = sector_mults.get('net_margin_target', 0.15)
            ebitda_margin_proxy = net_margin_t * margin_mult
            ebitda_for_calc = rev_fwd * ebitda_margin_proxy
            ebitda_proxy_used = True
        
        growth['EV/FWD EBITDA'] = calc_ev_forward_ebitda(
            ebitda_for_calc, sector_mults['ev_ebitda'] * adj['ev_ebitda'] * ai_mult['ev_ebitda'] * qm,
            cash, debt, shares
        )
        if ebitda_proxy_used and growth['EV/FWD EBITDA']:
            notes['EV/FWD EBITDA'] = (
                f"⚠️ v5.2 PROXY: Forward EBITDA yok/negatif "
                f"(analist tahmin eksik veya ALGORITHMIC). "
                f"Rev_fwd × %{ebitda_margin_proxy*100:.1f} sektör EBITDA marjı kullanıldı."
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
    est_list = fetch("analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 6}) or []
    
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
    
    # Forward EPS, Revenue, EBITDA — dinamik yıl seçimi (v5.0 Etap 12)
    # ÖNEMLİ: "eps_fwd_2y" adı tarihsel, gerçekte FY1 (next fiscal year, ~1y forward) alır.
    # Sektör standardı Forward P/E = NTM veya FY1, FY+2 değil.
    eps_fwd_2y = None
    eps_fwd_1y = None
    rev_fwd_2y = None
    ebitda_fwd_2y = None
    analyst_count_fwd = 0  # Forward verisi için güven göstergesi
    forward_data_quality = 'UNKNOWN'  # CONSENSUS / SINGLE / ALGORITHMIC / UNKNOWN
    
    if est_list:
        sorted_est = sorted(est_list, key=lambda x: x.get('date', ''))
        this_year = datetime.now().year
        # FY+1 = next fiscal year (gerçek 1-1.5y forward, sektör standart)
        target_year_2y = str(this_year + 1)  # 2026 → "2027" (FY1)
        target_year_1y = str(this_year)      # 2026 → "2026" (current FY)
        
        # FY1 estimate — eps_fwd_2y olarak kullan (next fiscal year, sektör standart)
        # Veri kalitesini kaybetmeyiz, sadece flagleriz (ALGORITHMIC dahil)
        for est in sorted_est:
            date = est.get('date', '')
            if not date or date < target_year_2y:
                continue
            eps_fwd_2y = safe_get(est, 'epsAvg')
            rev_fwd_2y = safe_get(est, 'revenueAvg')
            ebitda_fwd_2y = safe_get(est, 'ebitdaAvg')
            n_eps = est.get('numAnalystsEps', 0) or 0
            n_rev = est.get('numAnalystsRevenue', 0) or 0
            analyst_count_fwd = max(n_eps, n_rev)
            if analyst_count_fwd >= 2:
                forward_data_quality = 'CONSENSUS'
            elif analyst_count_fwd == 1:
                forward_data_quality = 'SINGLE'
            else:
                forward_data_quality = 'ALGORITHMIC'  # FMP extrapolation
            break
        # Fallback: en uzak yıl (en azından bir veri varsa kullan)
        if not eps_fwd_2y and sorted_est:
            last = sorted_est[-1]
            eps_fwd_2y = safe_get(last, 'epsAvg')
            rev_fwd_2y = safe_get(last, 'revenueAvg')
            ebitda_fwd_2y = safe_get(last, 'ebitdaAvg')
            n_eps = last.get('numAnalystsEps', 0) or 0
            n_rev = last.get('numAnalystsRevenue', 0) or 0
            analyst_count_fwd = max(n_eps, n_rev)
            forward_data_quality = 'CONSENSUS' if analyst_count_fwd >= 2 else ('SINGLE' if analyst_count_fwd == 1 else 'ALGORITHMIC')
        
        # 1 yıl ileri estimate (PEG için NTM EPS) - current FY veya FY1
        for est in sorted_est:
            date = est.get('date', '')
            if not date or date < target_year_1y or date >= target_year_2y:
                continue
            eps_fwd_1y = safe_get(est, 'epsAvg')
            break
        if not eps_fwd_1y:
            # Fallback: ilk geçerli yıl (kalite ne olursa olsun)
            for est in sorted_est:
                date = est.get('date', '')
                if not date or date < target_year_1y:
                    continue
                eps_fwd_1y = safe_get(est, 'epsAvg')
                break
    
    # v5.3: Multi-year forward EPS CAGR (Wall Street long-term growth standardı)
    # FMP analyst-estimates "CAGR formula" ile türetilmiş olduğunu kendi dokümantasyonunda açıklıyor.
    # PEG için bu en iyi kaynak — 3y CAGR (FY+1 → FY+4) öncelikli, 2y CAGR fallback.
    # Inflection biotech ve hyper-growth tech için sürdürülebilir büyüme oranı sağlar.
    forward_eps_3y_cagr = None
    forward_eps_2y_cagr = None
    forward_cagr_source = None  # 3y_consensus / 2y_consensus / unavailable
    forward_cagr_analyst_min = None  # FY1 ve uzak yıl analist sayısının min'i
    
    if est_list:
        sorted_est_for_cagr = sorted(est_list, key=lambda x: x.get('date', ''))
        # Forward yıllar: bu yıl ve sonrası
        forward_years = [e for e in sorted_est_for_cagr if e.get('date', '') >= target_year_1y]
        # Sadece pozitif EPS olan forward yıllar (negatif EPS CAGR'ı bozar)
        forward_years_pos = [e for e in forward_years if safe_get(e, 'epsAvg') > 0]
        
        if len(forward_years_pos) >= 4:
            # 3y CAGR (FY1 → FY4, 3 yıl atlama) — Wall Street long-term standardı
            eps_fy1 = safe_get(forward_years_pos[0], 'epsAvg')
            eps_fy4 = safe_get(forward_years_pos[3], 'epsAvg')
            if eps_fy1 > 0 and eps_fy4 > 0:
                forward_eps_3y_cagr = (eps_fy4 / eps_fy1) ** (1/3) - 1
                forward_cagr_source = '3y_consensus'
                n1 = forward_years_pos[0].get('numAnalystsEps', 0) or 0
                n4 = forward_years_pos[3].get('numAnalystsEps', 0) or 0
                forward_cagr_analyst_min = min(n1, n4) if (n1 and n4) else max(n1, n4)
        
        if len(forward_years_pos) >= 3 and forward_eps_3y_cagr is None:
            # Fallback: 2y CAGR (FY1 → FY3, 2 yıl atlama)
            eps_fy1 = safe_get(forward_years_pos[0], 'epsAvg')
            eps_fy3 = safe_get(forward_years_pos[2], 'epsAvg')
            if eps_fy1 > 0 and eps_fy3 > 0:
                forward_eps_2y_cagr = (eps_fy3 / eps_fy1) ** (1/2) - 1
                forward_cagr_source = '2y_consensus'
                n1 = forward_years_pos[0].get('numAnalystsEps', 0) or 0
                n3 = forward_years_pos[2].get('numAnalystsEps', 0) or 0
                forward_cagr_analyst_min = min(n1, n3) if (n1 and n3) else max(n1, n3)
    
    # Birleşik forward_cagr — birincil 3y, fallback 2y
    forward_cagr_consensus = forward_eps_3y_cagr if forward_eps_3y_cagr is not None else forward_eps_2y_cagr
    
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
    
    # Forward outlier (v5.1: inflection-aware)
    # v5.1 değişikliği: Son 2 çeyrek POZİTİF + önceki 2 çeyrek NEGATİF EPS varsa
    # gerçek "inflection point" → outlier flag iptal (LQDA gibi biotech ramp örnekleri).
    # Aksi halde forward_growth_ratio > 2.5 ise outlier (FWD şişkin = base değişikliği).
    forward_growth_ratio = None
    forward_outlier = False
    inflection_point = False
    inflection_note = None
    
    # v5.1: Quarterly EPS bazlı inflection tespiti
    if len(qinc_list) >= 4:
        try:
            q_eps = [safe_get(qinc_list[i], 'eps') for i in range(4)]
            # qinc_list newest-first: [Q-son, Q-1, Q-2, Q-3]
            # İnflection: son 2 ardışık pozitif + önceki 2 ardışık negatif
            if (q_eps[0] is not None and q_eps[1] is not None and
                q_eps[2] is not None and q_eps[3] is not None and
                q_eps[0] > 0 and q_eps[1] > 0 and
                q_eps[2] < 0 and q_eps[3] < 0):
                inflection_point = True
                inflection_note = (
                    f"INFLECTION POINT teyit: Son 2 çeyrek EPS pozitif "
                    f"(${q_eps[1]:.2f} → ${q_eps[0]:.2f}), önceki 2 çeyrek negatif "
                    f"(${q_eps[3]:.2f}, ${q_eps[2]:.2f}). Forward outlier flag iptal."
                )
        except (IndexError, TypeError, KeyError):
            pass
    
    if eps_fwd_2y and eps_ttm and eps_ttm > 0:
        forward_growth_ratio = eps_fwd_2y / eps_ttm
        # v5.1: Inflection point varsa outlier flag DEVRE DIŞI
        if inflection_point:
            forward_outlier = False
        else:
            forward_outlier = forward_growth_ratio > 2.5
    
    # v5.2: Inflection point sonrası DCF için fcf_normalized override
    # Geçmiş yıllık FCF anlamsız (zararlı dönem dahil, ortalama bastırıyor).
    # TTM FCF (son 4 çeyrek toplamı) inflection sonrası gerçek karlılık koşu hızını yansıtır.
    fcf_normalize_overridden = False
    if inflection_point and fcf_ttm and fcf_ttm > 0:
        original_fcf_norm = fcf_normalized
        fcf_normalized = fcf_ttm
        fcf_normalize_overridden = True
    
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
        # v5.3: Multi-year analyst EPS CAGR (Wall Street LTG)
        'forward_eps_3y_cagr': forward_eps_3y_cagr,
        'forward_eps_2y_cagr': forward_eps_2y_cagr,
        'forward_cagr_consensus': forward_cagr_consensus,
        'forward_cagr_source': forward_cagr_source,
        'forward_cagr_analyst_min': forward_cagr_analyst_min,
    }
    
    # =========================================================================
    # v5.0 KALIBRASYON SİNYALLERİ — calculate_methods'tan ÖNCE topla
    # (Bu değerler yöntem hesaplarını override eder)
    # =========================================================================
    
    v5_signals = {}
    if _V5_MODULES_AVAILABLE:
        try:
            # Canlı sektör/industry P/E — Net P/E + Forward P/E hesaplarını override eder
            static_pe = SECTOR_MULTIPLES.get(sector_key, SECTOR_MULTIPLES['generic']).get('pe', 20)
            live_pe, live_pe_source = fmp_layer.get_live_pe_for_sector_key(sector_key, static_fallback_pe=static_pe)
            v5_signals['live_pe'] = {
                'value': round(live_pe, 2) if live_pe else None,
                'source': live_pe_source,
                'static_fallback': static_pe,
                'delta_pct': round((live_pe - static_pe) / static_pe * 100, 1) if (live_pe and static_pe) else None,
            }
            # Sadece canlı veri geldiyse (statik fallback değilse) override yap
            if live_pe and live_pe_source in ('industry', 'sector'):
                # %50'den fazla sapma varsa şüpheli — orta nokta al
                if abs((live_pe - static_pe) / static_pe) > 0.5:
                    blended_pe = (live_pe + static_pe) / 2
                    data_pack['live_pe_override'] = blended_pe
                    v5_signals['live_pe']['applied_value'] = round(blended_pe, 2)
                    v5_signals['live_pe']['blend_note'] = f"Statik {static_pe}x ile canlı {live_pe:.1f}x ortalandı (sapma >%50)"
                else:
                    data_pack['live_pe_override'] = live_pe
                    v5_signals['live_pe']['applied_value'] = round(live_pe, 2)
            
            # Dinamik WACC (CAPM) — DCF hesabını override eder
            dyn_wacc, wacc_source = fmp_layer.calculate_dynamic_wacc(beta=safe_get(profile, 'beta', 1.2))
            v5_signals['dynamic_wacc'] = {
                'value': round(dyn_wacc * 100, 2),
                'source': wacc_source,
                'static_fallback': round(REGIME_ADJ[market['regime'].lower()]['wacc'] * 100, 1),
            }
            # CAPM hesabı geçerliyse override yap (sınır 8-18%)
            if 'CAPM' in wacc_source and 0.08 <= dyn_wacc <= 0.18:
                data_pack['dynamic_wacc'] = dyn_wacc
                v5_signals['dynamic_wacc']['applied'] = True
            else:
                v5_signals['dynamic_wacc']['applied'] = False
        except Exception as e:
            print(f"⚠️ v5.0 kalibrasyon sinyalleri toplanırken hata: {e}", file=sys.stderr)
    
    # 3 senaryoda hesapla (v4: quality_mult ile, v4.1: forward_outlier ile, v5: canlı PE + WACC override)
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
    heritage_decision = decision  # 9 yöntem bazlı orijinal karar (referans)
    heritage_median = summaries['normal']['main'].get('median') if summaries['normal']['main'] else None
    
    # v5.0 Etap 13 Fix-2: Forward-First Hibrit — projection oluşunca aşağıda override edilir
    forward_first_active = False
    forward_normalized_value = None
    
    # =========================================================================
    # v5.0 EKSTRA SİNYALLER — calculate_methods SONRASI (bizim DCF ile karşılaştırma)
    # (live_pe + dynamic_wacc zaten calculate_methods öncesi toplandı, burada eklenmez)
    # =========================================================================
    
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
            
            # FMP'nin kendi DCF (sanity check) — bizim DCF ile karşılaştırma
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
            
            # Pre-IPO tespiti (genelde False döner, IPO calendar'daysa True)
            pre_ipo = fmp_layer.is_ticker_pre_ipo(ticker)
            if pre_ipo:
                v5_signals['pre_ipo'] = pre_ipo
        
        except Exception as e:
            print(f"⚠️ v5.0 sinyalleri toplanırken hata: {e}", file=sys.stderr)
    
    # =========================================================================
    # v5.0 — 5 YILLIK PROJEKSİYON (projection_engine)
    # =========================================================================
    
    projection = None
    if _V5_MODULES_AVAILABLE:
        try:
            # Op margin TTM
            op_margin_ttm = (ebit_ttm / revenue_ttm) if (ebit_ttm and revenue_ttm and revenue_ttm > 0) else 0
            
            # v5.0 Etap 10: TTM gerçek marjları topla (delta-based projection için)
            # FMP ratios-ttm'den geliyor (zaten çekildi), yoksa income statement'tan türet
            ratios_ttm_for_margins = fmp_layer.get_ratios_ttm(ticker) if _V5_MODULES_AVAILABLE else None
            
            actual_ttm_margins = None
            if ratios_ttm_for_margins:
                actual_ttm_margins = {
                    'gross': ratios_ttm_for_margins.get('grossProfitMarginTTM') or 0.40,
                    'op': ratios_ttm_for_margins.get('operatingProfitMarginTTM') or op_margin_ttm,
                    'net': ratios_ttm_for_margins.get('netProfitMarginTTM') or 0.10,
                    'tax': ratios_ttm_for_margins.get('effectiveTaxRateTTM') or 0.21,
                    'capex': 0.05,  # placeholder, ratios-ttm'de yok, cash-flow'dan türetilir
                }
                # capex/revenue cash flow'dan
                cash_flows_for_capex = data.get('cash_flows', []) if 'data' in dir() else []
                if cash_flows_for_capex and revenue_ttm > 0:
                    capex_ttm = sum(abs(cf.get('capitalExpenditure', 0) or 0) for cf in cash_flows_for_capex[:4]) / 4
                    if capex_ttm > 0:
                        actual_ttm_margins['capex'] = capex_ttm / revenue_ttm
            
            # Margin profil tespiti
            profile_key = projection_engine.detect_margin_profile(
                sector_key=sector_key,
                current_op_margin=op_margin_ttm,
                revenue_yoy_growth=revenue_growth_yoy or 0.10,
                is_pre_revenue=(revenue_ttm < 50e6),
            )
            
            # Revenue projection (Etap 9: multi-year analyst estimates)
            # FMP analyst-estimates'ten 5 yıla kadar konsensüs çek
            analyst_revenues_dict = None
            try:
                multi_year = fmp_layer.get_analyst_estimates_multi_year(ticker, years=5)
                if multi_year:
                    analyst_revenues_dict = {
                        year: data['revenue_avg']
                        for year, data in multi_year.items()
                        if data.get('revenue_avg') and data['revenue_avg'] > 0
                    }
            except Exception as e:
                print(f"⚠️ Multi-year analyst estimates alınamadı: {e}", file=sys.stderr)
            
            revenues = projection_engine.project_revenue_5y(
                revenue_ttm=revenue_ttm,
                revenue_yoy_growth=revenue_growth_yoy or 0.15,
                analyst_rev_1y=None,
                analyst_rev_2y=rev_fwd_2y,
                ttm_year=datetime.now().year - 1,
                analyst_revenues_dict=analyst_revenues_dict,
            )
            
            # P&L projection (Etap 10: actual_ttm_margins ile delta-based)
            pnl = projection_engine.project_pnl_5y(
                revenue_list=revenues,
                profile_key=profile_key,
                shares_basic=shares,
                actual_ttm_margins=actual_ttm_margins,
            )
            
            # Multiples projection
            mults = projection_engine.project_multiples_5y(
                pnl_table=pnl,
                current_price=price,
                shares_basic=shares,
                current_cash=cash,
                current_debt=total_debt,
            )
            
            # Normalizasyon yılı (canlı sektör PE ile)
            normalization_pe = v5_signals.get('live_pe', {}).get('value') or SECTOR_MULTIPLES.get(sector_key, {}).get('pe', 25)
            normalization_ev_sales = SECTOR_MULTIPLES.get(sector_key, {}).get('ev_rev', 8)
            norm = projection_engine.detect_normalization_year(
                multiples_table=mults,
                sector_median_pe=normalization_pe,
                sector_median_ev_sales=normalization_ev_sales,
            )
            
            projection = {
                'profile_key': profile_key,
                'profile_description': projection_engine.SECTOR_MARGIN_PROFILES.get(profile_key, {}).get('description', ''),
                'pnl': pnl,
                'multiples': mults,
                'normalization': norm,
                'sector_median_pe_used': normalization_pe,
            }
            
            # v5.0 Etap 13 Fix-2: Hibrit Forward Normalize Değerleme
            # Sub-industry premium tespiti
            description_text = profile.get('description', '') or ''
            sub_premium, sub_premium_key, sub_premium_reason = projection_engine.detect_sub_industry_premium(
                sector=profile.get('sector'),
                industry=profile.get('industry'),
                description=description_text,
                revenue_yoy=revenue_growth_yoy or 0,
                is_ai_megacap=is_ai_megacap,
            )
            
            # Hibrit hesap için sektör Forward P/E seçimi:
            # - Sub-industry premium varsa (AI_INFRASTRUCTURE, CLOUD_SAAS): canlı sektör PE × 1.0 premium
            #   (canlı PE growth fiyatlamayı zaten yansıtıyor, ek premium yok)
            # - Sub-industry yoksa (mature/value): statik SECTOR_MULTIPLES median
            #   (mature için canlı PE risklidir, sabit median daha güvenli)
            # - AI_MEGACAP istisna: statik × 1.25 premium (NVDA gibi yerleşik)
            static_sector_pe = SECTOR_MULTIPLES.get(sector_key, {}).get('fwd_pe', 18)
            if sub_premium_key in ('AI_INFRASTRUCTURE', 'CLOUD_NATIVE_SAAS'):
                # Canlı sektör PE kullan, premium 1.0 (zaten dahil)
                sector_fwd_pe_for_norm = normalization_pe if normalization_pe else static_sector_pe
                sub_premium = 1.0
                sub_premium_reason = f"{sub_premium_key} tespit: canlı sektör PE ({sector_fwd_pe_for_norm:.1f}x) growth fiyatlamayı zaten yansıtır, ayrı premium yok"
            elif sub_premium_key == 'AI_MEGACAP':
                sector_fwd_pe_for_norm = static_sector_pe
                # sub_premium 1.25 zaten
            else:
                # Mature/default: statik PE
                sector_fwd_pe_for_norm = static_sector_pe
            # WACC: dinamik varsa onu kullan, yoksa default %10
            wacc_for_norm = data_pack.get('dynamic_wacc') or 0.10
            
            # Analyst raw EPS dict (Fix-2.1: PNL fallback yerine analyst öncelikli)
            analyst_eps_dict_for_norm = None
            if multi_year:
                analyst_eps_dict_for_norm = {
                    year: data['eps_avg']
                    for year, data in multi_year.items()
                    if data.get('eps_avg') is not None
                }
            
            forward_normalized = projection_engine.calculate_forward_normalized_value(
                pnl=pnl,
                normalization=norm,
                sector_forward_pe=sector_fwd_pe_for_norm,
                wacc=wacc_for_norm,
                sub_industry_premium=sub_premium,
                analyst_eps_dict=analyst_eps_dict_for_norm,
            )
            
            if forward_normalized:
                forward_normalized['sub_industry_key'] = sub_premium_key
                forward_normalized['sub_industry_reason'] = sub_premium_reason
                projection['forward_normalized'] = forward_normalized
            
            # Pivot tespiti (FY+1 = next fiscal year = current_year + 1)
            analyst_rev_fy1 = None
            if analyst_revenues_dict:
                analyst_rev_fy1 = analyst_revenues_dict.get(datetime.now().year + 1)
                # Fallback: ilk pozitif yıl
                if not analyst_rev_fy1:
                    for year in sorted(analyst_revenues_dict.keys()):
                        if year > datetime.now().year and analyst_revenues_dict[year]:
                            analyst_rev_fy1 = analyst_revenues_dict[year]
                            break
            
            pivot_detected, pivot_reason = projection_engine.detect_pivot_mode(
                revenue_ttm=revenue_ttm,
                revenue_yoy=revenue_growth_yoy,
                ttm_op_margin=(ebit_ttm / revenue_ttm) if (ebit_ttm and revenue_ttm and revenue_ttm > 0) else None,
                analyst_rev_fwd_1y=analyst_rev_fy1,
                forward_data_quality=forward_data_quality,
            )
            projection['pivot_detected'] = pivot_detected
            projection['pivot_reason'] = pivot_reason
        except Exception as e:
            print(f"⚠️ Projection üretilirken hata: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    # v5.0 Etap 13 Fix-2: Forward-First Hibrit karar override
    # Projection ve forward_normalized hazırlandıktan sonra çalışır
    if projection and projection.get('forward_normalized'):
        fn = projection['forward_normalized']
        if (fn.get('eps_source') == 'analyst_raw' and
            forward_data_quality in ('CONSENSUS', 'SINGLE')):
            forward_first_active = True
            forward_normalized_value = fn['value']
            
            # Hibrit değerine göre yeni karar (basit ratio bandı)
            if forward_normalized_value > 0:
                ratio = price / forward_normalized_value
                if ratio <= 0.70:
                    decision = ("🟢 GÜÇLÜ AL", f"Hibrit Forward (${forward_normalized_value:.2f}) — fiyat %{(1-ratio)*100:.0f} altında, derin değer.")
                elif ratio <= 0.90:
                    decision = ("🟢 AL", f"Hibrit Forward (${forward_normalized_value:.2f}) — fiyat %{(1-ratio)*100:.0f} altında.")
                elif ratio <= 1.10:
                    decision = ("🟡 İZLE", f"Hibrit Forward (${forward_normalized_value:.2f}) — fiyat adil değer civarında (±%10).")
                elif ratio <= 1.30:
                    decision = ("🟠 PAHALI / İZLE", f"Hibrit Forward (${forward_normalized_value:.2f}) — fiyat %{(ratio-1)*100:.0f} üstünde.")
                else:
                    decision = ("🔴 GEÇ / KAÇIN", f"Hibrit Forward (${forward_normalized_value:.2f}) — fiyat %{(ratio-1)*100:.0f} üstünde.")
    
    # v5.0 Etap 13 Fix-3: Bilanço Sonrası Tazelik Analizi
    # Son earnings tarihi ≤10 gün ise transcript çek + Kimi K2 Thinking ile analiz et
    freshness = None
    if _TRANSCRIPT_ANALYZER_AVAILABLE:
        try:
            freshness = transcript_analyzer.get_freshness_analysis(fetch, ticker)
        except Exception as e:
            sys.stderr.write(f"⚠️ Freshness analizi hatası: {e}\n")
    
    return {
        'ticker': ticker,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'version': '5.3',
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
        'company_description': profile.get('description', '') or '',
        'freshness': freshness,  # v5.0 Etap 13 Fix-3: Bilanço tazelik + transcript analizi
        'sector_key': sector_key, 'is_ai_megacap': is_ai_megacap,
        'quality_mult': quality_mult,
        'quality_detail': quality_detail,
        'market_regime': market, 'pure_forward': pure_forward,
        'forward_outlier': forward_outlier,
        'forward_growth_ratio': round(forward_growth_ratio, 2) if forward_growth_ratio else None,
        'inflection_point': inflection_point,
        'inflection_note': inflection_note,
        # v5.2: Inflection sonrası FCF override teyidi
        'fcf_normalize_overridden': fcf_normalize_overridden,
        # v5.3: Multi-year forward CAGR (Wall Street LTG) - PEG için kullanıldı
        'forward_eps_3y_cagr': round(forward_eps_3y_cagr * 100, 1) if forward_eps_3y_cagr else None,
        'forward_eps_2y_cagr': round(forward_eps_2y_cagr * 100, 1) if forward_eps_2y_cagr else None,
        'forward_cagr_consensus': round(forward_cagr_consensus * 100, 1) if forward_cagr_consensus else None,
        'forward_cagr_source': forward_cagr_source,
        'forward_cagr_analyst_min': forward_cagr_analyst_min,
        'analyst_count_fwd': analyst_count_fwd,  # v5.0 Etap 12: forward verisi güven göstergesi
        'forward_data_quality': forward_data_quality,  # CONSENSUS/SINGLE/ALGORITHMIC/UNKNOWN
        # v5.0 Etap 13 Fix-2: Forward-First Hibrit
        'forward_first_active': forward_first_active,
        'forward_normalized_value': forward_normalized_value,
        'heritage_decision': {'action': heritage_decision[0], 'reasoning': heritage_decision[1]} if heritage_decision else None,
        'heritage_median': round(heritage_median, 2) if heritage_median else None,
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
        'projection': projection,
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
    
    # v5.1: Inflection point teyidi
    if result.get('inflection_point'):
        out.append(f"  🌱 v5.1 INFLECTION POINT: Forward yöntemler korundu")
        if result.get('inflection_note'):
            out.append(f"     {result['inflection_note']}")
        # v5.2: FCF normalize override
        if result.get('fcf_normalize_overridden'):
            out.append(f"  🌱 v5.2 DCF FCF override: Geçmiş yıllık ortalama yerine TTM FCF kullanıldı")
    
    # v5.3: PEG growth kaynağı
    cagr_source = result.get('forward_cagr_source')
    cagr_value = result.get('forward_cagr_consensus')
    cagr_analysts = result.get('forward_cagr_analyst_min')
    if cagr_source and cagr_value is not None:
        source_label = {'3y_consensus': '3y CAGR (FY1→FY4)',
                        '2y_consensus': '2y CAGR (FY1→FY3, fallback)'}.get(cagr_source, cagr_source)
        out.append(f"  📊 v5.3 PEG GROWTH KAYNAĞI: %{cagr_value} ({source_label}, min analyst#={cagr_analysts})")
    
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
    
    # v5.0 — 5 YILLIK PROJEKSİYON
    proj = result.get('projection')
    if proj:
        out.append("")
        out.append("─" * 75)
        out.append("  📅 5 YILLIK FİNANSAL PROJEKSİYON (v5.0 Yeni)")
        out.append("─" * 75)
        out.append(f"\n  Profil: {proj['profile_key']}")
        if proj.get('profile_description'):
            out.append(f"  {proj['profile_description']}")
        
        pnl = proj.get('pnl', [])
        if pnl:
            out.append("\n  📊 P&L Tablosu:")
            # Header
            years = [str(r['year']) for r in pnl]
            out.append(f"  {'Kalem':<22}" + "".join(f"{y:>12}" for y in years))
            
            def fmt_money(v, width=12):
                if v is None:
                    return f"{'N/A':>{width}}"
                if abs(v) >= 1e9:
                    return f"{('$%.2fB' % (v/1e9)):>{width}}"
                elif abs(v) >= 1e6:
                    return f"{('$%.0fM' % (v/1e6)):>{width}}"
                else:
                    return f"{('$%.0f' % v):>{width}}"
            
            def fmt_pct(v, width=12):
                if v is None:
                    return f"{'N/A':>{width}}"
                return f"{('%' + ('%.1f' % (v*100))):>{width}}"
            
            def fmt_eps(v, width=12):
                if v is None:
                    return f"{'N/A':>{width}}"
                return f"{('$%.2f' % v):>{width}}"
            
            out.append(f"  {'Gelir':<22}" + "".join(fmt_money(r['revenue']) for r in pnl))
            out.append(f"  {'  Büyüme':<22}" + "".join(fmt_pct(r['revenue_growth']) for r in pnl))
            out.append(f"  {'Brüt Marj':<22}" + "".join(fmt_pct(r['gross_margin']) for r in pnl))
            out.append(f"  {'Faaliyet Marjı':<22}" + "".join(fmt_pct(r['op_margin']) for r in pnl))
            out.append(f"  {'Faaliyet Kârı':<22}" + "".join(fmt_money(r['operating_income']) for r in pnl))
            out.append(f"  {'Net Marj':<22}" + "".join(fmt_pct(r['net_margin']) for r in pnl))
            out.append(f"  {'Net Kâr':<22}" + "".join(fmt_money(r['net_income']) for r in pnl))
            out.append(f"  {'EPS (basic)':<22}" + "".join(fmt_eps(r['eps_basic']) for r in pnl))
        
        mults = proj.get('multiples', [])
        if mults:
            out.append("\n  💹 Forward Çarpanlar (fiyat sabit varsayımı):")
            years = [str(r['year']) for r in mults]
            out.append(f"  {'Çarpan':<22}" + "".join(f"{y:>12}" for y in years))
            
            def fmt_mult(v, width=12):
                if v is None or v < 0 or v > 999:
                    return f"{'N/A':>{width}}"
                return f"{('%.1fx' % v):>{width}}"
            
            out.append(f"  {'Forward P/E':<22}" + "".join(fmt_mult(r['fwd_pe']) for r in mults))
            out.append(f"  {'Forward P/S':<22}" + "".join(fmt_mult(r['fwd_ps']) for r in mults))
            out.append(f"  {'Forward EV/Sales':<22}" + "".join(fmt_mult(r['fwd_ev_sales']) for r in mults))
            out.append(f"  {'Forward EV/EBITDA':<22}" + "".join(fmt_mult(r['fwd_ev_ebitda']) for r in mults))
        
        norm = proj.get('normalization')
        if norm:
            out.append("\n  🎯 Normalizasyon Yılı:")
            sector_pe_label = f"{proj.get('sector_median_pe_used', norm['sector_median_pe']):.0f}x"
            pe_year = norm.get('pe_normalization_year')
            if pe_year:
                years_to_wait = pe_year - datetime.now().year
                emoji = "🟢" if years_to_wait <= 2 else ("🟡" if years_to_wait <= 4 else "🟠")
                out.append(f"  {emoji} Forward P/E sektör medyanı ({sector_pe_label}) {pe_year}'da oturuyor ({years_to_wait} yıl bekleme)")
            else:
                last_pe = mults[-1].get('fwd_pe') if mults else None
                if last_pe:
                    out.append(f"  🔴 5 yıl sonunda bile P/E sektör medyanı altına inmiyor ({mults[-1]['year']}: {last_pe:.0f}x)")
                else:
                    out.append(f"  ⚠️ 5 yıl içinde kâra geçmiyor")
    
    out.append("")
    return "\n".join(out)


def analyze_pre_ipo(input_json_path):
    """
    Pre-IPO modu — FMP'de olmayan şirketler için manuel JSON input.
    
    Sadece projection_engine kullanır (9 yöntem TTM hesabı atlanır, TTM verisi yok).
    
    JSON şema (test_data/cbrs_pre_ipo.json örneği):
    {
        "ticker": "CBRS",
        "company": "Cerebras Systems Inc.",
        "sector_key": "semicon_design",
        "revenue_ttm": 510000000,
        "revenue_yoy_growth": 0.76,
        "shares_basic": 224000000,
        "shares_diluted": 257000000,
        "ipo_price_mid": 155,
        "ipo_date": "2026-05-13",
        "custom_revenues": {"2026": 1200000000, "2027": 2700000000, ...},
        "interest_expense_annual": 60000000,
        "current_op_margin": -0.28,
        "is_pre_revenue": false,
        "current_cash": 4200000000,
        "current_debt": 1000000000,
        "notes": "OpenAI MRA + AWS Bedrock..."
    }
    """
    if not _V5_MODULES_AVAILABLE:
        return {'error': 'v5.0 modülleri yüklü değil, pre-IPO modu kullanılamaz'}
    
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            d = json.load(f)
    except Exception as e:
        return {'error': f'JSON dosyası okunamadı: {e}'}
    
    ticker = d.get('ticker', 'UNKNOWN')
    company = d.get('company', ticker)
    sector_key = d.get('sector_key', 'generic')
    revenue_ttm = d.get('revenue_ttm', 0)
    revenue_yoy = d.get('revenue_yoy_growth', 0.20)
    shares_basic = d.get('shares_basic', 0)
    shares_diluted = d.get('shares_diluted') or shares_basic
    ipo_price = d.get('ipo_price_mid') or d.get('ipo_price_low', 0)
    
    custom_revenues_str = d.get('custom_revenues', {})
    custom_revenues = {int(k): float(v) for k, v in custom_revenues_str.items()}
    
    interest_expense = d.get('interest_expense_annual', 0)
    op_margin = d.get('current_op_margin', 0)
    is_pre_revenue = d.get('is_pre_revenue', revenue_ttm < 50e6)
    cash = d.get('current_cash', 0)
    debt = d.get('current_debt', 0)
    
    # Profil tespiti
    profile_key = projection_engine.detect_margin_profile(
        sector_key=sector_key,
        current_op_margin=op_margin,
        revenue_yoy_growth=revenue_yoy,
        is_pre_revenue=is_pre_revenue,
    )
    
    # Revenue projection
    ttm_year = datetime.now().year - 1
    revenues = projection_engine.project_revenue_5y(
        revenue_ttm=revenue_ttm,
        revenue_yoy_growth=revenue_yoy,
        custom_revenues=custom_revenues if custom_revenues else None,
        ttm_year=ttm_year,
    )
    
    # P&L projection
    pnl = projection_engine.project_pnl_5y(
        revenue_list=revenues,
        profile_key=profile_key,
        shares_basic=shares_basic,
        shares_diluted=shares_diluted,
        interest_expense_annual=interest_expense,
    )
    
    # Multiples projection
    mults = projection_engine.project_multiples_5y(
        pnl_table=pnl,
        current_price=ipo_price,
        shares_basic=shares_basic,
        current_cash=cash,
        current_debt=debt,
    )
    
    # Sektör medyan PE (statik tablodan veya canlı)
    static_pe = SECTOR_MULTIPLES.get(sector_key, SECTOR_MULTIPLES['generic']).get('pe', 25)
    try:
        live_pe, source = fmp_layer.get_live_pe_for_sector_key(sector_key, static_fallback_pe=static_pe)
        sector_pe_used = live_pe if source != 'static' else static_pe
    except Exception:
        sector_pe_used = static_pe
        source = 'static'
    
    static_ev_sales = SECTOR_MULTIPLES.get(sector_key, {}).get('ev_rev', 8)
    norm = projection_engine.detect_normalization_year(
        multiples_table=mults,
        sector_median_pe=sector_pe_used,
        sector_median_ev_sales=static_ev_sales,
    )
    
    return {
        'ticker': ticker,
        'company': company,
        'mode': 'PRE_IPO',
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'version': '5.3',
        'sector_key': sector_key,
        'ipo_price_mid': ipo_price,
        'ipo_date': d.get('ipo_date'),
        'ipo_price_low': d.get('ipo_price_low'),
        'ipo_price_high': d.get('ipo_price_high'),
        'notes': d.get('notes', ''),
        'inputs': {
            'revenue_ttm': revenue_ttm,
            'revenue_yoy_growth': revenue_yoy,
            'shares_basic': shares_basic,
            'shares_diluted': shares_diluted,
            'op_margin_ttm': op_margin,
            'cash': cash,
            'debt': debt,
            'interest_expense_annual': interest_expense,
        },
        'projection': {
            'profile_key': profile_key,
            'profile_description': projection_engine.SECTOR_MARGIN_PROFILES.get(profile_key, {}).get('description', ''),
            'pnl': pnl,
            'multiples': mults,
            'normalization': norm,
            'sector_median_pe_used': sector_pe_used,
            'sector_pe_source': source,
        },
    }


def format_pre_ipo_output(result):
    """Pre-IPO modu için sade çıktı formatı."""
    out = []
    out.append("")
    out.append("=" * 75)
    out.append(f"  {result['ticker']} - {result['company']} | v{result['version']} | PRE-IPO MODU")
    out.append(f"  IPO Tarihi: {result.get('ipo_date', 'N/A')}  |  Sektör: {result['sector_key']}")
    if result.get('ipo_price_low') and result.get('ipo_price_high'):
        out.append(f"  IPO Aralık: ${result['ipo_price_low']}-${result['ipo_price_high']}  |  Orta: ${result['ipo_price_mid']}")
    else:
        out.append(f"  IPO Fiyat (mid): ${result['ipo_price_mid']}")
    out.append("=" * 75)
    
    if result.get('notes'):
        out.append(f"\nNotlar: {result['notes']}")
    
    inp = result['inputs']
    out.append("\n📊 GİRDİ ÖZETİ:")
    out.append(f"  Revenue TTM: ${inp['revenue_ttm']/1e6:.0f}M (+%{inp['revenue_yoy_growth']*100:.0f})")
    out.append(f"  Shares: {inp['shares_basic']/1e6:.0f}M (basic) / {inp['shares_diluted']/1e6:.0f}M (diluted)")
    out.append(f"  Op Margin TTM: %{inp['op_margin_ttm']*100:.1f}")
    out.append(f"  Cash: ${inp['cash']/1e9:.2f}B  |  Debt: ${inp['debt']/1e9:.2f}B")
    out.append(f"  Faiz Gideri Yıllık: ${inp['interest_expense_annual']/1e6:.0f}M")
    
    proj = result['projection']
    out.append("\n" + "─" * 75)
    out.append(f"  📅 5 YILLIK PROJEKSİYON ({proj['profile_key']})")
    out.append("─" * 75)
    out.append(f"  {proj['profile_description']}")
    
    pnl = proj.get('pnl', [])
    if pnl:
        years = [str(r['year']) for r in pnl]
        out.append("\n  📊 P&L:")
        out.append(f"  {'Kalem':<22}" + "".join(f"{y:>12}" for y in years))
        
        def fmt_money(v, w=12):
            if v is None: return f"{'N/A':>{w}}"
            if abs(v) >= 1e9: return f"{('$%.2fB' % (v/1e9)):>{w}}"
            elif abs(v) >= 1e6: return f"{('$%.0fM' % (v/1e6)):>{w}}"
            else: return f"{('$%.0f' % v):>{w}}"
        def fmt_pct(v, w=12):
            if v is None: return f"{'N/A':>{w}}"
            return f"{('%' + ('%.1f' % (v*100))):>{w}}"
        def fmt_eps(v, w=12):
            if v is None: return f"{'N/A':>{w}}"
            return f"{('$%.2f' % v):>{w}}"
        
        out.append(f"  {'Gelir':<22}" + "".join(fmt_money(r['revenue']) for r in pnl))
        out.append(f"  {'  Büyüme':<22}" + "".join(fmt_pct(r['revenue_growth']) for r in pnl))
        out.append(f"  {'Brüt Marj':<22}" + "".join(fmt_pct(r['gross_margin']) for r in pnl))
        out.append(f"  {'Faaliyet Marjı':<22}" + "".join(fmt_pct(r['op_margin']) for r in pnl))
        out.append(f"  {'Faaliyet Kârı':<22}" + "".join(fmt_money(r['operating_income']) for r in pnl))
        out.append(f"  {'Net Marj':<22}" + "".join(fmt_pct(r['net_margin']) for r in pnl))
        out.append(f"  {'Net Kâr':<22}" + "".join(fmt_money(r['net_income']) for r in pnl))
        out.append(f"  {'EPS (basic)':<22}" + "".join(fmt_eps(r['eps_basic']) for r in pnl))
        out.append(f"  {'EPS (diluted)':<22}" + "".join(fmt_eps(r['eps_diluted']) for r in pnl))
    
    mults = proj.get('multiples', [])
    if mults:
        out.append("\n  💹 Forward Çarpanlar (IPO fiyatı sabit):")
        out.append(f"  {'Çarpan':<22}" + "".join(f"{y:>12}" for y in years))
        
        def fmt_mult(v, w=12):
            if v is None or v < 0 or v > 999: return f"{'N/A':>{w}}"
            return f"{('%.1fx' % v):>{w}}"
        
        out.append(f"  {'Forward P/E':<22}" + "".join(fmt_mult(r['fwd_pe']) for r in mults))
        out.append(f"  {'Forward P/S':<22}" + "".join(fmt_mult(r['fwd_ps']) for r in mults))
        out.append(f"  {'Forward EV/Sales':<22}" + "".join(fmt_mult(r['fwd_ev_sales']) for r in mults))
        out.append(f"  {'Forward EV/EBITDA':<22}" + "".join(fmt_mult(r['fwd_ev_ebitda']) for r in mults))
    
    norm = proj.get('normalization')
    if norm:
        sector_pe_label = f"{proj.get('sector_median_pe_used'):.0f}x"
        pe_year = norm.get('pe_normalization_year')
        out.append("\n  🎯 Normalizasyon Yılı:")
        if pe_year:
            years_to_wait = pe_year - datetime.now().year
            emoji = "🟢" if years_to_wait <= 2 else ("🟡" if years_to_wait <= 4 else "🟠")
            out.append(f"  {emoji} Forward P/E sektör medyanı ({sector_pe_label}) {pe_year}'da oturuyor ({years_to_wait} yıl bekleme)")
        else:
            last_pe = mults[-1].get('fwd_pe') if mults else None
            if last_pe and last_pe > 0:
                out.append(f"  🔴 5 yıl sonunda bile P/E sektör medyanı altına inmiyor ({mults[-1]['year']}: {last_pe:.0f}x)")
            else:
                out.append(f"  ⚠️ 5 yıl içinde kâra geçmiyor — spekülatif yatırım")
    
    out.append("")
    out.append("⚠️ NOT: Pre-IPO analizi sadece projeksiyon temelli. TTM TTM bazlı 9 yöntem hesaplanmadı.")
    out.append("    Analist konsensüsü ve canlı veri olmadan: girdiler manuel/S-1 bazlı varsayımdır.")
    out.append("")
    return "\n".join(out)


def format_markdown_report(result, output_path=None):
    """
    v5.0 — 12 bölümlü protokol uyumlu markdown rapor üretir.
    
    Adil Değer Rapor Protokolü (docs/ADIL_DEGER_RAPOR_PROTOKOLU.md) bölümleri:
    1. Yönetici Özeti
    2. 9 Yöntem Bazlı Değerlendirme
    3. Ağırlıklı Adil Değer Tablosu
    4. Senaryo Matrisi
    5. Bear Case (en az 5 madde)
    6. Bull Case (en az 5 madde)
    7. "Neden Yanlış Olabilirim" (en az 5 madde)
    8. v5.0 Yeni Sinyaller (Risk + Sentiment + DCF Sanity + Konsantrasyon) [v5.0 ek]
    9. Portföy Karar Matrisi
    10. Giriş Planı
    11. İzleme Tetikleyicileri
    12. 5 Yıllık Finansal Projeksiyon [v5.0 ek]
    
    output_path verilirse dosyaya yazar. Her durumda markdown string döner.
    """
    ticker = result['ticker']
    p = result['profile']
    di = result['data_inputs']
    v5 = result.get('v5_signals', {})
    proj = result.get('projection')
    price = p['price']
    today = datetime.now().strftime('%Y-%m-%d')
    
    md = []
    md.append(f"# {ticker} — Adil Değer Raporu")
    md.append(f"**Tarih**: {today}  |  **Şirket**: {p['name']}  |  **Sektör**: {p['sector']} / {p['industry']}")
    md.append(f"**Kaynak**: finzora ai  |  **Skill**: Adil Değer v{result['version']}  |  **Mod**: {result['mode']}")
    md.append("")
    md.append("---")
    md.append("")
    
    # ========================================
    # ŞİRKET TANIMI (FMP description)
    # ========================================
    company_desc = result.get('company_description', '') or ''
    if company_desc:
        md.append("## Şirket Hakkında")
        md.append("")
        # İlk cümleyi al + maks 400 karakter
        # FMP description çoğunlukla "X Corporation does Y." şeklinde başlar
        first_sentence_end = company_desc.find('. ', 50)  # en az 50 char sonra ilk nokta
        if first_sentence_end > 0 and first_sentence_end < 400:
            short_desc = company_desc[:first_sentence_end + 1]
        else:
            short_desc = company_desc[:400].rstrip()
            # Son kelimeyi kırpma
            last_space = short_desc.rfind(' ')
            if last_space > 300:
                short_desc = short_desc[:last_space] + '...'
        md.append(short_desc)
        md.append("")
    
    # ========================================
    # BÖLÜM 1: Yönetici Özeti
    # ========================================
    md.append("## 1. Yönetici Özeti")
    md.append("")
    
    # Beklenen Adil Değer = normal medyan (main)
    normal_main = result['summaries']['normal'].get('main', {})
    normal_median = normal_main.get('median') if normal_main else None
    bear_median = (result['summaries']['bear'].get('main') or {}).get('median')
    bull_median = (result['summaries']['bull'].get('main') or {}).get('median')
    
    upside_pct = ((normal_median - price) / price * 100) if normal_median else None
    
    confidence = "ORTA"
    if v5.get('altman_z', {}).get('label') == 'GÜVENLİ' and v5.get('piotroski', {}).get('value', 0) >= 7:
        confidence = "YÜKSEK"
    elif v5.get('altman_z', {}).get('label') == 'İFLAS RİSKİ' or v5.get('piotroski', {}).get('value', 9) <= 3:
        confidence = "DÜŞÜK"
    
    # v5.0 Etap 12: Forward veri kalitesi confidence'a etki eder
    fdq = result.get('forward_data_quality', 'UNKNOWN')
    if fdq == 'UNKNOWN':
        confidence = "DÜŞÜK"  # Hiç forward yok
    elif fdq == 'ALGORITHMIC' and confidence == "YÜKSEK":
        confidence = "ORTA"  # Algorithmic + Piotroski/Altman güçlü olsa bile YÜKSEK olmasın
    elif fdq == 'SINGLE' and confidence == "YÜKSEK":
        confidence = "ORTA"
    
    # v5.0 Etap 12: Piotroski ≤ 4 (zayıf kalite) → confidence en fazla ORTA olabilir
    pio_val = v5.get('piotroski', {}).get('value', 9)
    if pio_val <= 4 and confidence == "YÜKSEK":
        confidence = "ORTA"
    
    # v5.0 Etap 13 Fix-2: Forward-First Hibrit — ana adil değer hibrit hesabı olur
    forward_first = result.get('forward_first_active', False)
    fn_value = result.get('forward_normalized_value')
    heritage_median = result.get('heritage_median')
    
    if forward_first and fn_value:
        # Hibrit ana, 9 yöntem heritage olarak göster
        primary_adil_deger = fn_value
        upside_pct_primary = ((primary_adil_deger - price) / price * 100) if price else None
        md.append(f"**Adil Değer (Hibrit Forward Normalize)**: ${primary_adil_deger:.2f}")
        if heritage_median is not None:
            md.append(f"**9 Yöntem Medyanı (referans)**: ${heritage_median:.2f}")
        if upside_pct_primary is not None:
            yon = "yukarı" if upside_pct_primary > 0 else "aşağı"
            md.append(f"**Potansiyel**: %{abs(upside_pct_primary):.1f} {yon} (mevcut ${price:.2f})")
    else:
        # Eski mantık — 9 yöntem medyanı ana
        if normal_median:
            md.append(f"**Beklenen Adil Değer (normal medyan)**: ${normal_median:.2f}")
        else:
            md.append("**Beklenen Adil Değer**: hesaplanamadı")
        if upside_pct is not None:
            yon = "yukarı" if upside_pct > 0 else "aşağı"
            md.append(f"**Potansiyel**: %{abs(upside_pct):.1f} {yon} (mevcut ${price:.2f})")
    md.append(f"**Confidence**: {confidence}")
    md.append("")
    
    md.append("### Snapshot")
    md.append("")
    md.append("| Metrik | Değer |")
    md.append("|---|---|")
    md.append(f"| Mevcut Fiyat | ${price:.2f} |")
    md.append(f"| Piyasa Değeri | ${(p['market_cap'] or 0)/1e9:.1f}B |")
    md.append(f"| Beta | {p.get('beta', 'N/A')} |")
    md.append(f"| 52w High / Low | ${p.get('year_high', 'N/A')} / ${p.get('year_low', 'N/A')} |")
    md.append(f"| SMA 50 / 200 | ${p.get('sma_50', 'N/A')} / ${p.get('sma_200', 'N/A')} |")
    md.append(f"| EPS TTM | ${di['eps_ttm']} |")
    md.append(f"| EPS FWD 1y (FY1) | ${di.get('eps_fwd_2y', 'N/A')} |")
    md.append(f"| Revenue TTM | ${di['revenue_ttm_billions']}B |")
    md.append(f"| Revenue FWD 1y (FY1) | ${di.get('revenue_fwd_2y_billions', 'N/A')}B |")
    md.append(f"| ROE | %{di['roe_pct']} |")
    md.append(f"| Net Margin | %{di['net_margin_pct']} |")
    md.append(f"| Revenue YoY | %{di.get('revenue_growth_yoy_pct', 'N/A')} |")
    md.append(f"| AI Mega-Cap | {'⭐ EVET' if result['is_ai_megacap'] else 'Hayır'} |")
    md.append(f"| Quality Premium | {result.get('quality_mult', 1.0):.2f}x |")
    # v5.0 Etap 12: Analyst coverage göstergesi
    acf = result.get('analyst_count_fwd', 0)
    fdq = result.get('forward_data_quality', 'UNKNOWN')
    if fdq == 'CONSENSUS':
        coverage_label = f"✅ {acf} analyst (gerçek konsensüs)"
    elif fdq == 'SINGLE':
        coverage_label = f"⚠️ 1 analyst (zayıf)"
    elif fdq == 'ALGORITHMIC':
        coverage_label = f"🟡 FMP algorithmic (analyst sayısı 0, muhtemelen yönetim guidance bazlı)"
    else:
        coverage_label = "🔴 KAPSAM YOK"
    md.append(f"| Forward Veri Kalitesi | {coverage_label} |")
    
    # v5.0 Etap 13 Fix-2: Forward-First Hibrit detayları
    if forward_first and fn_value:
        proj = result.get('projection', {}) or {}
        fn_detail = proj.get('forward_normalized', {})
        md.append(f"| Hibrit Hesap Modu | Forward-First (analyst raw EPS bazlı) |")
        md.append(f"| Normalize Yıl | {fn_detail.get('normalization_year', 'N/A')} (en yüksek EPS yılı) |")
        md.append(f"| Normalize EPS | ${fn_detail.get('normalize_eps', 0):.2f} (tek yıl, tepe kazanç) |")
        sub_key = fn_detail.get('sub_industry_key', '')
        sub_mult = fn_detail.get('sub_industry_premium', 1.0)
        sector_pe_used = fn_detail.get('sector_forward_pe', 0)
        if sub_key == 'AI_INFRASTRUCTURE':
            md.append(f"| Sub-Industry | AI Infrastructure → canlı sektör P/E kullanıldı |")
            md.append(f"| Sektör Forward P/E | {sector_pe_used:.1f}x (canlı, growth dahil) |")
        elif sub_key == 'CLOUD_NATIVE_SAAS':
            md.append(f"| Sub-Industry | Cloud-native SaaS → canlı sektör P/E kullanıldı |")
            md.append(f"| Sektör Forward P/E | {sector_pe_used:.1f}x (canlı, growth dahil) |")
        elif sub_key == 'AI_MEGACAP':
            md.append(f"| Sub-Industry | AI Mega-Cap → statik sektör P/E × {sub_mult:.2f}x premium |")
            md.append(f"| Sektör Forward P/E | {sector_pe_used:.1f}x (statik) |")
        else:
            md.append(f"| Sektör Forward P/E | {sector_pe_used:.1f}x (statik) |")
        wacc = fn_detail.get('wacc', 0.10)
        years_norm = fn_detail.get('years_to_normalize', 0)
        df = fn_detail.get('discount_factor', 1.0)
        md.append(f"| WACC | %{wacc*100:.1f} |")
        if years_norm > 0:
            md.append(f"| Diskonto ({years_norm} yıl) | ÷ {df:.3f} |")
    
    # Pivot bayrağı (varsa)
    if (result.get('projection') or {}).get('pivot_detected'):
        md.append(f"| Pivot Mode | 🔄 EVET — Şirket dramatic dönüşüm aşamasında |")
    md.append(f"| Piyasa Rejimi | {result['market_regime']['regime']} (VIX {result['market_regime']['vix']}) |")
    md.append("")
    
    # ========================================
    # HESABIN ADIMLARI (Forward-First Hibrit aktifse)
    # ========================================
    if forward_first and fn_value:
        proj = result.get('projection', {}) or {}
        fn_detail = proj.get('forward_normalized', {})
        
        md.append("### Hibrit Forward Normalize — Hesabın Adımları")
        md.append("")
        md.append("| Adım | Hesap | Değer |")
        md.append("|---|---|---|")
        
        # Adım 1: Analyst forward EPS verisi (sıralı)
        analyst_eps_dict_md = {}
        # Yeniden multi_year'dan çek (bu fonksiyonda multi_year değişkeni yok, projection'a saklamadık)
        # Bunun yerine eps_values_used'ı gösterelim ve normalize yılı belirtelim
        eps_used = fn_detail.get('eps_values_used', [])
        norm_yr = fn_detail.get('normalization_year', 0)
        norm_eps = fn_detail.get('normalize_eps', 0)
        sector_pe = fn_detail.get('sector_forward_pe', 0)
        sub_mult = fn_detail.get('sub_industry_premium', 1.0)
        wacc_val = fn_detail.get('wacc', 0.10)
        years_n = fn_detail.get('years_to_normalize', 0)
        df_val = fn_detail.get('discount_factor', 1.0)
        mature = fn_detail.get('mature_value', 0)
        
        # EPS dökümü - en yüksek tek yıl
        if eps_used and norm_yr:
            md.append(f"| 1. Analyst forward EPS taraması | Tüm pozitif yıllar arasından en yüksek | {fn_detail.get('eps_source', '')} |")
        
        md.append(f"| 2. Normalize yıl seçimi | En yüksek pozitif EPS yılı | {norm_yr} |")
        
        md.append(f"| 3. Normalize EPS | Y{norm_yr} EPS (tek yıl, tepe kazanç) | ${norm_eps:.2f} |")
        
        sub_key = fn_detail.get('sub_industry_key', '')
        if sub_key and sub_key != 'GROWTH_DEFAULT':
            sub_label = {
                'AI_INFRASTRUCTURE': 'AI Infrastructure (canlı sektör P/E)',
                'CLOUD_NATIVE_SAAS': 'Cloud-native SaaS (canlı sektör P/E)',
                'AI_MEGACAP': f'AI Mega-Cap (statik × {sub_mult:.2f}x premium)',
            }.get(sub_key, sub_key)
            md.append(f"| 4. Sub-Industry tespiti | {sub_label} | premium {sub_mult:.2f}x |")
        
        md.append(f"| 5. Sektör Forward P/E | Information Technology Services | {sector_pe:.2f}x |")
        
        if sub_mult != 1.0:
            md.append(f"| 6. Mature value (normalize yılında) | ${norm_eps:.2f} × {sector_pe:.2f} × {sub_mult:.2f} | ${mature:.2f} |")
        else:
            md.append(f"| 6. Mature value (normalize yılında) | ${norm_eps:.2f} × {sector_pe:.2f} | ${mature:.2f} |")
        
        if years_n > 0:
            md.append(f"| 7. Years to normalize | {norm_yr} - {datetime.now().year} | {years_n} yıl |")
            md.append(f"| 8. Discount factor | (1 + %{wacc_val*100:.1f})^{years_n} | × {df_val:.3f} |")
            md.append(f"| 9. Adil değer (bugün) | ${mature:.2f} / {df_val:.3f} | **${fn_value:.2f}** |")
        else:
            md.append(f"| 7. Years to normalize | {norm_yr} ≤ {datetime.now().year} (diskonto yok) | 0 yıl |")
            md.append(f"| 8. Adil değer (bugün) | Mature value doğrudan | **${fn_value:.2f}** |")
        md.append("")
    
    # ========================================
    # FRESHNESS — Bilanço Sonrası Transcript Analizi (Etap 13 Fix-3)
    # ========================================
    freshness = result.get('freshness')
    if freshness and _TRANSCRIPT_ANALYZER_AVAILABLE:
        freshness_lines = transcript_analyzer.format_freshness_markdown(freshness)
        if freshness_lines:
            md.extend(freshness_lines)
    
    # ========================================
    # BÖLÜM 2: 9 Yöntem Bazlı Değerlendirme
    # ========================================
    md.append("## 2. 9 Yöntem Bazlı Değerlendirme")
    md.append("")
    md.append("v5.0 yöntem listesi (Graham, EV/EBIT, Justified P-B, Rule of 40 v5.0'da kaldırıldı).")
    md.append("")
    
    normal_methods = result['methods_by_regime']['normal']
    method_order = [
        ('Net P/E', 'traditional'),
        ('EV/EBITDA', 'traditional'),
        ('EV/Revenue', 'traditional'),
        ('P/FCF', 'traditional'),
        ('Forward P/E', 'forward'),
        ('DCF', 'forward'),
        ('PEG', 'growth'),
        ('EV/FWD Revenue', 'growth'),
        ('EV/FWD EBITDA', 'growth'),
    ]
    
    md.append("| Yöntem | Kategori | Normal Değer | Durum |")
    md.append("|---|---|---|---|")
    for method_name, cat in method_order:
        val = normal_methods.get(cat, {}).get(method_name)
        if val is not None and val > 0:
            durum = "KULLANILABİLİR"
            val_str = f"${val:.2f}"
        else:
            durum = "KULLANILAMAZ"
            val_str = "N/A"
            # Sebep notu (varsa)
            note = (result.get('method_notes', {}).get('normal') or {}).get(method_name)
            if note:
                durum = f"ELENDİ ({note.replace('⚠️ ', '')})"
        md.append(f"| {method_name} | {cat} | {val_str} | {durum} |")
    md.append("")
    
    # ========================================
    # BÖLÜM 3: Senaryo Matrisi
    # (Eski Bölüm 3 'Ağırlıklı Adil Değer Tablosu' kaldırıldı — Hibrit ana hesap olduğunda
    # Heritage 9 yöntem medyanı zaten Yönetici Özeti'nde referans olarak görünüyor.)
    # (Eski Bölüm 4 → Bölüm 3, numaralandırma 1 azaldı)
    # ========================================
    md.append("## 3. Senaryo Matrisi")
    md.append("")
    
    # v5.0 Etap 13 Fix-2: Forward-First aktifse senaryolar Hibrit değerine göre
    # Aksi halde eski Heritage senaryoları
    if forward_first and fn_value:
        primary = fn_value
        scenario_bear = primary * 0.70
        scenario_base = primary
        scenario_bull = primary * 1.30
        md.append("**Hesap tabanı**: Hibrit Forward Normalize (Bear = ×0.70, Bull = ×1.30)")
        md.append("")
        md.append("| Senaryo | Adil Değer | Mevcut Fiyata Göre | Olasılık | Gerekçe |")
        md.append("|---|---|---|---|---|")
        bear_diff_h = ((scenario_bear - price) / price * 100)
        base_diff_h = ((scenario_base - price) / price * 100)
        bull_diff_h = ((scenario_bull - price) / price * 100)
        sign_b = "+" if bear_diff_h > 0 else ""
        sign_n = "+" if base_diff_h > 0 else ""
        sign_u = "+" if bull_diff_h > 0 else ""
        md.append(f"| 🐻 Bear | ${scenario_bear:.2f} | %{sign_b}{bear_diff_h:.1f} | %25-30 | Forward EPS yarısı gerçekleşmez, multiple compression |")
        md.append(f"| ⚖️ Base | ${scenario_base:.2f} | %{sign_n}{base_diff_h:.1f} | %45-50 | Analyst konsensüs doğru çıkar, normalize yıl ulaşılır |")
        md.append(f"| 🐂 Bull | ${scenario_bull:.2f} | %{sign_u}{bull_diff_h:.1f} | %20-25 | Tepe EPS aşılır veya multiple expansion |")
        # Beklenen Değer
        ev = scenario_bear * 0.275 + scenario_base * 0.475 + scenario_bull * 0.225
        ev_diff = ((ev - price) / price * 100)
        sign_ev = "+" if ev_diff > 0 else ""
        md.append(f"| **Beklenen Değer** | **${ev:.2f}** | **%{sign_ev}{ev_diff:.1f}** | %100 | Senaryo ağırlıklı |")
    else:
        # Heritage senaryolar
        bear_diff = ((bear_median - price) / price * 100) if bear_median else None
        normal_diff = upside_pct
        bull_diff = ((bull_median - price) / price * 100) if bull_median else None
        
        md.append("| Senaryo | Adil Değer | Mevcut Fiyata Göre | Olasılık | Gerekçe |")
        md.append("|---|---|---|---|---|")
        if bear_median:
            sign = "+" if bear_diff > 0 else ""
            md.append(f"| 🐻 Bear | ${bear_median:.2f} | %{sign}{bear_diff:.1f} | %25-30 | Multiple compression, sektör rotasyonu |")
        if normal_median:
            sign = "+" if normal_diff > 0 else ""
            md.append(f"| ⚖️ Base | ${normal_median:.2f} | %{sign}{normal_diff:.1f} | %45-50 | Mevcut piyasa rejimi, analist konsensüs uyumlu |")
        if bull_median:
            sign = "+" if bull_diff > 0 else ""
            md.append(f"| 🐂 Bull | ${bull_median:.2f} | %{sign}{bull_diff:.1f} | %20-25 | Sektör tailwind, AI mega-cap premium |")
        if bear_median and normal_median and bull_median:
            ev = bear_median * 0.275 + normal_median * 0.475 + bull_median * 0.225
            ev_diff = ((ev - price) / price * 100)
            sign = "+" if ev_diff > 0 else ""
            md.append(f"| **Beklenen Değer** | **${ev:.2f}** | **%{sign}{ev_diff:.1f}** | %100 | Senaryo ağırlıklı |")
    md.append("")
    
    # ========================================
    # BÖLÜM 4: Bear Case (otomatik iskelet + manuel)
    # ========================================
    md.append("## 4. Bear Case (en az 5 madde)")
    md.append("")
    bear_items = []
    
    # Otomatik bear maddeleri (v5.0 sinyallerinden)
    if v5.get('altman_z', {}).get('label') in ('İFLAS RİSKİ', 'BELİRSİZ'):
        bear_items.append(f"**Altman Z {v5['altman_z']['value']}** — {v5['altman_z']['label']} bölgesinde (KESİN). İflas/finansal stres riski yükseliyor.")
    
    if v5.get('piotroski', {}).get('value', 9) <= 4:
        bear_items.append(f"**Piotroski {v5['piotroski']['value']}/9** — {v5['piotroski']['label']} kalite skoru (KESİN). Fundamental zayıflık var.")
    
    if v5.get('upgrade_momentum', {}).get('direction') == 'downgrade':
        bear_items.append(f"**Analist downgrade momentum**: {v5['upgrade_momentum']['label']} (KESİN). Son 6 ayda analist sentiment'i kötüleşiyor.")
    
    # Ürün konsantrasyonu — pivot/yüksek-growth durumda segmentation eski iş kolunu
    # yansıtır, yanıltıcı olabilir. forward_first aktif + yüksek revenue growth varsa gizle.
    is_pivot_or_growth = (
        (result.get('forward_first_active') and (di.get('revenue_growth_yoy_pct') or 0) > 50)
        or (result.get('projection') or {}).get('pivot_detected')
    )
    if v5.get('concentration_risk_product', {}).get('top_share_pct', 0) >= 50 and not is_pivot_or_growth:
        cr = v5['concentration_risk_product']
        bear_items.append(f"**Ürün konsantrasyonu KRİTİK**: {cr['top_segment']} %{cr['top_share_pct']} gelir (KESİN). Tek müşteri/segment kaybı şirketi sarsabilir.")
    elif v5.get('concentration_risk_product', {}).get('top_share_pct', 0) >= 50 and is_pivot_or_growth:
        cr = v5['concentration_risk_product']
        bear_items.append(f"**FMP segmentation eski veri olabilir**: {cr['top_segment']} %{cr['top_share_pct']} (KESİN). Şirket pivot/yüksek büyüme aşamasında, son çeyrek raporlarından gerçek mix doğrulanmalı.")
    
    if v5.get('concentration_risk_geo', {}).get('top_share_pct', 0) >= 60:
        cr = v5['concentration_risk_geo']
        bear_items.append(f"**Coğrafi konsantrasyon**: {cr['top_segment']} %{cr['top_share_pct']} gelir (KESİN). Tarife/regülasyon riskine maruz.")
    
    if v5.get('live_pe', {}).get('delta_pct', 0) and abs(v5['live_pe']['delta_pct']) > 50:
        bear_items.append(f"**Sektör multiple inflation**: Canlı sektör P/E statik tabloya göre %{v5['live_pe']['delta_pct']:+.0f} sapmış (KESİN). Multiple compression riski.")
    
    if di.get('revenue_growth_yoy_pct', 0) and di['revenue_growth_yoy_pct'] < 0:
        bear_items.append(f"**Revenue küçülüyor**: YoY %{di['revenue_growth_yoy_pct']:.1f} (KESİN). Büyüme hikayesi bozuluyor.")
    
    # Generic bear maddeleri (her hisse için)
    if len(bear_items) < 5:
        bear_items.append("**Multiple compression riski**: Sektör çarpanları tarihsel medyana doğru sıkışırsa adil değer düşer (MUHTEMEL).")
    if len(bear_items) < 5:
        bear_items.append("**Recession/durgunluk**: Genel ekonomik yavaşlama özellikle döngüsel iş kollarını etkiler (SPEKÜLATİF).")
    if len(bear_items) < 5:
        bear_items.append("**Rakip baskısı**: Yeni rakipler veya alternatif ürünler pazar payı erozyonu yaratabilir (SPEKÜLATİF).")
    if len(bear_items) < 5:
        bear_items.append("**Regülasyon riski**: Antitrust, ihracat kontrolü veya yeni vergi rejimleri marj baskısı yapabilir (SPEKÜLATİF).")
    
    for i, item in enumerate(bear_items, 1):
        md.append(f"{i}. {item}")
    md.append("")
    
    # ========================================
    # BÖLÜM 5: Bull Case
    # ========================================
    md.append("## 5. Bull Case (en az 5 madde)")
    md.append("")
    bull_items = []
    
    if v5.get('altman_z', {}).get('label') == 'GÜVENLİ' and v5['altman_z']['value'] >= 5:
        bull_items.append(f"**Altman Z {v5['altman_z']['value']}** — çok güvenli finansal yapı (KESİN). İflas riski sıfıra yakın, savunmacı pozisyon.")
    
    if v5.get('piotroski', {}).get('value', 0) >= 7:
        bull_items.append(f"**Piotroski {v5['piotroski']['value']}/9** — {v5['piotroski']['label']} fundamental kalite (KESİN). Karlı, verimli, sağlam bilanço.")
    
    if v5.get('upgrade_momentum', {}).get('direction') == 'upgrade':
        bull_items.append(f"**Analist upgrade momentum**: {v5['upgrade_momentum']['label']} (KESİN). Son 6 ayda sentiment iyileşiyor.")
    
    if di.get('revenue_growth_yoy_pct', 0) and di['revenue_growth_yoy_pct'] > 30:
        bull_items.append(f"**Güçlü gelir büyümesi**: YoY %{di['revenue_growth_yoy_pct']:.1f} (KESİN). Tepe çizgisi momentum'u devam ediyor.")
    
    if di.get('roe_pct', 0) > 20:
        bull_items.append(f"**Yüksek ROE %{di['roe_pct']}** (KESİN). Sermaye verimliliği üst quartil, kapital allocation güçlü.")
    
    if result['is_ai_megacap']:
        bull_items.append(f"**AI mega-cap premium aktif** (KESİN). Sektör trendi + ölçek + ekosistem avantajları.")
    
    if result.get('quality_mult', 1.0) >= 1.3:
        bull_items.append(f"**Quality Premium {result['quality_mult']:.2f}x** (KESİN). ROE + Net Margin sektör hedeflerinin üstünde — fiyat gücü ve marj koruması yüksek.")
    
    if proj and proj.get('normalization', {}).get('pe_normalization_year'):
        pe_year = proj['normalization']['pe_normalization_year']
        years_to_wait = pe_year - datetime.now().year
        if years_to_wait <= 2:
            bull_items.append(f"**Hızlı normalizasyon**: {pe_year}'da Forward P/E sektör medyanına oturuyor ({years_to_wait} yıl bekleme, MUHTEMEL). Yakın vadede makul değerleme.")
    
    if v5.get('fmp_dcf', {}).get('value') and normal_median:
        fmp_dcf_val = v5['fmp_dcf']['value']
        if fmp_dcf_val > price * 1.20:
            bull_items.append(f"**FMP DCF ${fmp_dcf_val:.2f}** mevcut fiyatın %{((fmp_dcf_val/price-1)*100):.0f} üstünde (MUHTEMEL). Bağımsız DCF onay sinyali.")
    
    # v5.0 Etap 13 Fix-3: Analyst Buy konsensüs sinyali
    ar = v5.get('grades_consensus', {})
    if ar:
        total_buy = ar.get('strong_buy', 0) + ar.get('buy', 0)
        total_sell = ar.get('strong_sell', 0) + ar.get('sell', 0)
        total_all = total_buy + ar.get('hold', 0) + total_sell
        if total_all >= 5 and total_buy / total_all >= 0.80 and total_sell == 0:
            bull_items.append(f"**Analyst Buy konsensüsü**: {total_buy}/{total_all} analyst Buy/Strong Buy, 0 Sell (KESİN). Wall Street uyumlu pozitif görünüm.")
    
    # v5.0 Etap 13 Fix-3: Forward-First Hibrit aktifse
    if result.get('forward_first_active') and result.get('forward_normalized_value'):
        fn_val_b = result['forward_normalized_value']
        if fn_val_b > price * 1.20:
            bull_items.append(f"**Hibrit Forward Normalize ${fn_val_b:.2f}** — analyst raw EPS bazlı, mevcut fiyatın %{((fn_val_b/price-1)*100):.0f} üstünde (KESİN). Tepe kazanç gücü diskonto edilmiş.")
    
    # v5.0 Etap 13 Fix-3: Sub-Industry premium (AI Infrastructure, Cloud SaaS)
    proj_fn = (proj or {}).get('forward_normalized', {})
    sub_key_b = proj_fn.get('sub_industry_key', '')
    if sub_key_b == 'AI_INFRASTRUCTURE':
        bull_items.append(f"**AI Infrastructure tematik**: Sektör 3-5 yıllık structural AI tailwind, hyperscaler capex artıyor (MUHTEMEL). Şirket bu trend içinde konumlu.")
    elif sub_key_b == 'CLOUD_NATIVE_SAAS':
        bull_items.append(f"**Cloud-native SaaS tematik**: SaaS market structural büyümede, sticky recurring revenue (MUHTEMEL).")
    
    # Generic bull
    if len(bull_items) < 5:
        bull_items.append("**Sektör tailwind**: Sektör 3-5 yıllık structural growth trendinde, şirket payı koruyor (MUHTEMEL).")
    if len(bull_items) < 5:
        bull_items.append("**Hisse geri alımı potansiyeli**: Nakit pozisyonu güçlü, kullanmadığı sermaye buyback'a dönüşebilir (SPEKÜLATİF).")
    
    for i, item in enumerate(bull_items, 1):
        md.append(f"{i}. {item}")
    md.append("")
    
    # ========================================
    # BÖLÜM 6: Neden Yanlış Olabilirim
    # ========================================
    md.append("## 6. Neden Yanlış Olabilirim (en az 5 madde)")
    md.append("")
    wrong_items = []
    
    # Otomatik şüphe maddeleri
    if v5.get('live_pe', {}).get('delta_pct') and abs(v5['live_pe']['delta_pct']) > 50:
        wrong_items.append(f"**Sektör multiple seçimi sübjektif**: Canlı semicon P/E 62x, statik tablo 28x, ben blend %50/50 kullanıyorum. Doğru çarpan tartışmalı (SPEKÜLATİF).")
    
    if v5.get('fmp_dcf', {}).get('value') and normal_methods.get('forward', {}).get('DCF'):
        our_dcf = normal_methods['forward']['DCF']
        fmp_dcf = v5['fmp_dcf']['value']
        diff = abs((our_dcf - fmp_dcf) / fmp_dcf * 100)
        if diff > 30:
            wrong_items.append(f"**DCF varsayım farkı**: Bizim DCF ${our_dcf:.0f}, FMP DCF ${fmp_dcf:.0f} (%{diff:.0f} fark). Terminal growth/WACC/capex varsayımları farklı (SPEKÜLATİF).")
    
    if di.get('revenue_growth_yoy_pct', 0) and di['revenue_growth_yoy_pct'] > 40:
        wrong_items.append(f"**Forward varsayımlar agresif**: YoY %{di['revenue_growth_yoy_pct']:.0f} gibi yüksek büyüme uzun vadeli sürdürülemez. Y3-Y5 projeksiyon hatalı olabilir (MUHTEMEL).")
    
    if result.get('forward_outlier'):
        wrong_items.append(f"**Forward EPS şişkin**: EPS_FWD/EPS_TTM oranı {result.get('forward_growth_ratio', 'N/A')}x — base değişikliği veya tek seferlik kazanç olabilir. Forward yöntemler elendi (KESİN).")
    
    # Generic
    if len(wrong_items) < 5:
        wrong_items.append("**TTM verilerin temsiliyeti**: Son 12 ay tek seferlik olaylar (vergi avantajı, varlık satışı, restructuring) içerebilir (MUHTEMEL).")
    if len(wrong_items) < 5:
        wrong_items.append("**Analyst coverage zayıflığı**: Forward EPS/Revenue tahminleri analyst konsensüsüne dayanır; analyst'ler son 6 ay sürpriz olmuşsa modelleri eski olabilir (MUHTEMEL).")
    if len(wrong_items) < 5:
        wrong_items.append("**Capex / FCF varsayımları**: Yöntemlerden P/FCF ve DCF normalized FCF kullanır (4 yıl ortalama). Capex döngüsel ise normalize FCF gerçek FCF'i yansıtmaz (SPEKÜLATİF).")
    if len(wrong_items) < 5:
        wrong_items.append("**Sektör multiple aralığının geniş olması**: Aynı sektörde +/-30% spread var (örn semicon: AVGO 50x vs INTC 12x). Tek bir 'sektör medyanı' yanıltıcı olabilir (MUHTEMEL).")
    if len(wrong_items) < 5:
        wrong_items.append("**Recency bias**: Son 1 yıl performansı modele aşırı yansımış olabilir; tarihsel ortalamayla farkı doğrulamadım (SPEKÜLATİF).")
    
    for i, item in enumerate(wrong_items, 1):
        md.append(f"{i}. {item}")
    md.append("")
    
    # ========================================
    # BÖLÜM 7: v5.0 Yeni Sinyaller (Risk + Sentiment + DCF Sanity + Konsantrasyon)
    # ========================================
    md.append("## 7. v5.0 Yeni Sinyaller")
    md.append("")
    
    if v5:
        md.append("### 7.1 Risk Skorları")
        if v5.get('altman_z'):
            az = v5['altman_z']
            md.append(f"- **Altman Z (iflas riski)**: {az['value']:.2f} → {az['emoji']} **{az['label']}** (KESİN)")
        if v5.get('piotroski'):
            pi = v5['piotroski']
            md.append(f"- **Piotroski F-Score**: {pi['value']}/9 → {pi['emoji']} **{pi['label']}** (KESİN)")
        md.append("")
        
        if v5.get('grades_consensus'):
            gc = v5['grades_consensus']
            total = gc['strong_buy'] + gc['buy'] + gc['hold'] + gc['sell'] + gc['strong_sell']
            md.append("### 7.2 Analist Sentiment")
            md.append(f"- Toplam {total} analist: Strong Buy {gc['strong_buy']} / Buy {gc['buy']} / Hold {gc['hold']} / Sell {gc['sell']} / Strong Sell {gc['strong_sell']}")
            md.append(f"- Konsensüs: **{gc.get('consensus_label', 'N/A')}**")
            if v5.get('upgrade_momentum'):
                md.append(f"- Son 6 ay momentum: {v5['upgrade_momentum']['label']}")
            md.append("")
        
        if v5.get('fmp_dcf'):
            md.append("### 7.3 DCF Sanity Check")
            md.append(f"- FMP DCF (unlevered): ${v5['fmp_dcf']['value']:.2f}")
            if v5.get('fmp_dcf_levered'):
                md.append(f"- FMP DCF (levered): ${v5['fmp_dcf_levered']['value']:.2f}")
            our_dcf = normal_methods.get('forward', {}).get('DCF')
            if our_dcf:
                diff_pct = (our_dcf - v5['fmp_dcf']['value']) / v5['fmp_dcf']['value'] * 100
                md.append(f"- Bizim DCF (normal): ${our_dcf:.2f}  |  Fark: %{diff_pct:+.0f}")
            md.append("")
        
        if v5.get('concentration_risk_product') or v5.get('concentration_risk_geo'):
            md.append("### 7.4 Konsantrasyon Riski")
            # v5.0 Etap 13 Fix-3: Pivot/yüksek-growth durumunda eski FMP segmentation yumuşat
            is_pivot_or_growth_74 = (
                (result.get('forward_first_active') and (di.get('revenue_growth_yoy_pct') or 0) > 50)
                or (result.get('projection') or {}).get('pivot_detected')
            )
            if v5.get('concentration_risk_product'):
                cr = v5['concentration_risk_product']
                if cr.get('top_share_pct', 0) >= 50 and is_pivot_or_growth_74:
                    md.append(f"- **Ürün/Segment** ({cr['fiscal_year']}): 🟡 ESKİ VERİ OLABİLİR — şirket pivot/yüksek büyüme aşamasında")
                    md.append(f"  - FMP segmentation: {cr['top_segment']} %{cr['top_share_pct']} (eski iş kolu, son çeyrek raporlarından doğrula)")
                else:
                    md.append(f"- **Ürün/Segment** ({cr['fiscal_year']}): {cr['label']}")
                    md.append(f"  - Top: {cr['top_segment']} %{cr['top_share_pct']}  |  Top 2: %{cr['top2_share_pct']}")
            if v5.get('concentration_risk_geo'):
                cr = v5['concentration_risk_geo']
                md.append(f"- **Coğrafya** ({cr['fiscal_year']}): {cr['label']}")
                md.append(f"  - Top: {cr['top_segment']} %{cr['top_share_pct']}  |  Top 2: %{cr['top2_share_pct']}")
            md.append("")
        
        if v5.get('live_pe', {}).get('value'):
            lp = v5['live_pe']
            md.append("### 7.5 Canlı Sektör P/E")
            md.append(f"- Canlı: {lp['value']:.1f}x ({lp['source']})  |  Statik fallback: {lp['static_fallback']}x")
            if lp.get('delta_pct') is not None:
                md.append(f"- Sapma: %{lp['delta_pct']:+.1f}")
            if lp.get('blend_note'):
                md.append(f"- Not: {lp['blend_note']}")
            md.append("")
        
        if v5.get('dynamic_wacc'):
            dw = v5['dynamic_wacc']
            md.append("### 7.6 Dinamik CAPM WACC")
            md.append(f"- WACC: %{dw['value']:.2f}  |  Statik fallback: %{dw['static_fallback']}")
            md.append(f"- Hesaplama: {dw['source']}")
            md.append("")
    
    
    # ========================================
    # BÖLÜM 8: İzleme Tetikleyicileri
    # ========================================
    md.append("## 8. İzleme Tetikleyicileri (en az 5 madde)")
    md.append("")
    
    triggers = []
    # Bir sonraki kazanç
    triggers.append(f"**Bir sonraki kazanç açıklaması**: EPS_TTM ${di['eps_ttm']} → revize: yeni rakam ±%10 dışındaysa modeli yenile (KESİN).")
    
    if v5.get('live_pe', {}).get('value'):
        lp = v5['live_pe']
        triggers.append(f"**Sektör P/E değişimi**: Canlı {lp['value']:.0f}x → %20+ azalırsa multiple compression sinyali (KESİN).")
    
    if v5.get('upgrade_momentum'):
        triggers.append(f"**Analist rating değişimleri**: Şu an momentum {v5['upgrade_momentum']['direction']} — yön ters dönerse pozisyon revize (KESİN).")
    
    if v5.get('concentration_risk_product', {}).get('top_share_pct', 0) >= 50:
        cr = v5['concentration_risk_product']
        triggers.append(f"**Müşteri konsantrasyonu izle**: {cr['top_segment']} %{cr['top_share_pct']} payı — segmentation raporlarında değişim takip et (KESİN).")
    
    # v5.0 Etap 13 Fix-3: Forward-First aktifse İzleme tetikleyicileri Hibrit senaryolardan
    if result.get('forward_first_active') and result.get('forward_normalized_value'):
        fn_val_tr = result['forward_normalized_value']
        bear_scenario = fn_val_tr * 0.70
        bull_scenario = fn_val_tr * 1.30
        triggers.append(f"**Bear senaryo altına düşüş** (Hibrit): Fiyat ${bear_scenario:.2f} altına inerse pozisyon büyüt veya stop tetikle (KESİN).")
        triggers.append(f"**Bull senaryo üstüne çıkış** (Hibrit): Fiyat ${bull_scenario:.2f} üstüne çıkarsa kısmi kâr al (KESİN).")
    else:
        if bear_median:
            triggers.append(f"**Bear medyan altına düşüş**: Fiyat ${bear_median:.2f} altına inerse pozisyon büyüt veya stop tetikle (KESİN).")
        if bull_median:
            triggers.append(f"**Boğa medyanını geçiş**: Fiyat ${bull_median:.2f} üstüne çıkarsa kısmi kâr al (KESİN).")
    
    triggers.append("**VIX > 28**: Bear regime tetiklenir, tüm yöntemler -%25-35 düşer. Pozisyon revize (KESİN).")
    
    if proj and proj.get('normalization', {}).get('pe_normalization_year'):
        pe_year = proj['normalization']['pe_normalization_year']
        triggers.append(f"**{pe_year} kazanç dönemi**: Projeksiyona göre normalizasyon yılı, EPS hedefinin yarısı altında kalırsa tez bozuldu sayılır (MUHTEMEL).")
    
    for i, item in enumerate(triggers[:8], 1):
        md.append(f"{i}. {item}")
    md.append("")
    
    # ========================================
    # BÖLÜM 9: 5 Yıllık Finansal Projeksiyon (v5.0)
    # ========================================
    if proj:
        md.append("## 9. 5 Yıllık Finansal Projeksiyon (v5.0)")
        md.append("")
        md.append(f"**Profil**: `{proj['profile_key']}` — {proj.get('profile_description', '')}")
        md.append("")
        
        pnl = proj.get('pnl', [])
        if pnl:
            md.append("### P&L Projeksiyonu")
            md.append("")
            years = [str(r['year']) for r in pnl]
            md.append("| Kalem | " + " | ".join(years) + " |")
            md.append("|" + "---|" * (len(years) + 1))
            
            def fmt_money(v):
                if v is None: return "N/A"
                if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
                elif abs(v) >= 1e6: return f"${v/1e6:.0f}M"
                else: return f"${v:.0f}"
            def fmt_pct(v):
                if v is None: return "—"
                return f"%{v*100:.1f}"
            def fmt_eps(v):
                if v is None: return "N/A"
                return f"${v:.2f}"
            
            md.append("| **Gelir** | " + " | ".join(fmt_money(r['revenue']) for r in pnl) + " |")
            md.append("| Büyüme | " + " | ".join(fmt_pct(r['revenue_growth']) for r in pnl) + " |")
            md.append("| Brüt Marj | " + " | ".join(fmt_pct(r['gross_margin']) for r in pnl) + " |")
            md.append("| Faaliyet Marjı | " + " | ".join(fmt_pct(r['op_margin']) for r in pnl) + " |")
            md.append("| **Faaliyet Kârı** | " + " | ".join(fmt_money(r['operating_income']) for r in pnl) + " |")
            md.append("| Net Marj | " + " | ".join(fmt_pct(r['net_margin']) for r in pnl) + " |")
            md.append("| **Net Kâr** | " + " | ".join(fmt_money(r['net_income']) for r in pnl) + " |")
            md.append("| **EPS (basic)** | " + " | ".join(fmt_eps(r['eps_basic']) for r in pnl) + " |")
            md.append("")
        
        mults = proj.get('multiples', [])
        if mults:
            md.append("### Forward Çarpanlar (Mevcut fiyat sabit varsayımı)")
            md.append("")
            md.append("| Çarpan | " + " | ".join(years) + " |")
            md.append("|" + "---|" * (len(years) + 1))
            
            def fmt_mult(v):
                if v is None or v < 0: return "N/A"
                if v > 999: return ">999"
                return f"{v:.1f}x"
            
            md.append("| **Forward P/E** | " + " | ".join(fmt_mult(r['fwd_pe']) for r in mults) + " |")
            md.append("| Forward P/S | " + " | ".join(fmt_mult(r['fwd_ps']) for r in mults) + " |")
            md.append("| Forward EV/Sales | " + " | ".join(fmt_mult(r['fwd_ev_sales']) for r in mults) + " |")
            md.append("| Forward EV/EBITDA | " + " | ".join(fmt_mult(r['fwd_ev_ebitda']) for r in mults) + " |")
            md.append("")
        
        norm = proj.get('normalization')
        if norm:
            md.append("### Normalizasyon Yılı")
            md.append("")
            sector_pe_label = f"{proj.get('sector_median_pe_used', norm['sector_median_pe']):.0f}x"
            pe_year = norm.get('pe_normalization_year')
            if pe_year:
                years_to_wait = pe_year - datetime.now().year
                emoji = "🟢" if years_to_wait <= 2 else ("🟡" if years_to_wait <= 4 else "🟠")
                md.append(f"{emoji} **Forward P/E** sektör medyanı ({sector_pe_label})'e **{pe_year}** yılında oturuyor ({years_to_wait} yıl bekleme).")
            else:
                md.append(f"🔴 5 yıl sonunda bile P/E sektör medyanı altına inmiyor — uzun vadeli yatırım gerekli veya hisse pahalı.")
            md.append("")
    
    # ========================================
    # SON: Sonuç Notu + v5 Risk Uyarıları
    # ========================================
    md.append("---")
    md.append("")
    md.append("## Otomatik Karar")
    md.append("")
    md.append(f"**{result['decision']['action']}**")
    md.append("")
    md.append(f"_{result['decision']['reasoning']}_")
    md.append("")
    
    # v5.0 risk overlay - kararı override etmez ama uyarı ekler
    risk_warnings = []
    # v5.0 Etap 13 Fix-3: pivot/yüksek-growth durumunda eski FMP segmentation yumuşat
    is_pivot_or_growth_rw = (
        (result.get('forward_first_active') and (di.get('revenue_growth_yoy_pct') or 0) > 50)
        or (result.get('projection') or {}).get('pivot_detected')
    )
    if v5.get('piotroski', {}).get('value', 9) <= 4:
        risk_warnings.append(f"⚠️ Piotroski {v5['piotroski']['value']}/9 — fundamental kalite ZAYIF, kararın gerektirdiği güveni düşürür")
    if v5.get('altman_z', {}).get('label') == 'İFLAS RİSKİ':
        risk_warnings.append(f"⚠️ Altman Z {v5['altman_z']['value']:.2f} — İFLAS RİSKİ, pozisyon almadan önce gözden geçir")
    if v5.get('upgrade_momentum', {}).get('direction') == 'downgrade':
        risk_warnings.append(f"⚠️ {v5['upgrade_momentum']['label']} — analist sentiment'i kötüleşiyor")
    if v5.get('concentration_risk_product', {}).get('top_share_pct', 0) >= 80:
        cr = v5['concentration_risk_product']
        if is_pivot_or_growth_rw:
            risk_warnings.append(f"🟡 FMP segmentation ({cr['fiscal_year']}): {cr['top_segment']} %{cr['top_share_pct']} — eski veri, şirket pivot/yüksek büyüme aşamasında")
        else:
            risk_warnings.append(f"⚠️ Ürün konsantrasyonu KRİTİK: {cr['top_segment']} %{cr['top_share_pct']}")
    if v5.get('fmp_dcf', {}).get('value', 0) < 0:
        risk_warnings.append(f"⚠️ FMP DCF NEGATİF (${v5['fmp_dcf']['value']:.2f}) — şirket negatif FCF üretiyor, modeli sorgula")
    
    # v5.0 Etap 13 Fix-3: P&L projeksiyon vs Analyst konsensüs çelişkisi
    # Skill'in dahili 5y projeksiyonu negatif EPS gösteriyor, ama analyst konsensüsü pozitif
    if result.get('forward_first_active'):
        proj_pnl_list = (result.get('projection') or {}).get('pnl', []) or []
        fn_data = (result.get('projection') or {}).get('forward_normalized', {})
        norm_yr_rw = fn_data.get('normalization_year', 0)
        if norm_yr_rw and proj_pnl_list:
            # Liste içinden normalize yılını bul
            skill_eps_at_norm = None
            for row in proj_pnl_list:
                if row.get('year') == norm_yr_rw:
                    skill_eps_at_norm = row.get('eps_basic')
                    break
            analyst_eps_at_norm = fn_data.get('normalize_eps', 0)
            if skill_eps_at_norm is not None and analyst_eps_at_norm:
                # Skill negatif, analyst pozitif ise çelişki var
                if skill_eps_at_norm < 0 and analyst_eps_at_norm > 0:
                    risk_warnings.append(
                        f"🚨 PROJEKSİYON ÇELİŞKİSİ — Skill'in dahili 5y modeli Y{norm_yr_rw} EPS ${skill_eps_at_norm:.2f} hesaplıyor (negatif), "
                        f"analyst konsensüsü ${analyst_eps_at_norm:.2f} (pozitif). Skill profili APLD gibi pivot/data-center şirketleri için "
                        f"uygun olmayabilir. Forward-First analyst verisini kullandı, ancak çelişki kararı sorgulatır."
                    )
                elif abs(skill_eps_at_norm - analyst_eps_at_norm) / max(abs(analyst_eps_at_norm), 0.01) > 0.50:
                    risk_warnings.append(
                        f"🟡 PROJEKSİYON SAPMASI — Skill'in dahili modeli Y{norm_yr_rw} EPS ${skill_eps_at_norm:.2f}, "
                        f"analyst konsensüsü ${analyst_eps_at_norm:.2f}. %{abs(skill_eps_at_norm - analyst_eps_at_norm) / abs(analyst_eps_at_norm) * 100:.0f} sapma."
                    )
    
    # v5.0 Etap 12: Forward veri kalitesi uyarıları (skip değil, flag)
    acf = result.get('analyst_count_fwd', 0)
    fdq = result.get('forward_data_quality', 'UNKNOWN')
    if fdq == 'ALGORITHMIC':
        risk_warnings.append(f"🟡 Forward veri FMP ALGORITHMIC — gerçek analyst konsensüsü değil, muhtemelen yönetim guidance/capacity rakamlarından extrapolated. Tek başına 'gelecek kesin' olarak alma; bull case görünümlü olabilir.")
    elif fdq == 'SINGLE':
        risk_warnings.append(f"⚠️ Tek analyst forward kapsamı — outlier riski yüksek, geniş güven aralığı bekle.")
    elif fdq == 'UNKNOWN':
        risk_warnings.append(f"🔴 ANALYST KAPSAMI YOK — Forward yöntemler kullanılamadı. Adil değer sadece TTM/Traditional veriden hesaplandı.")
    
    # v5.0 Etap 12: Kalite tuzağı tespiti (Piotroski zayıf + FMP DCF negatif kombinasyonu)
    pio_val = v5.get('piotroski', {}).get('value', 9)
    fmp_dcf_val = (v5.get('fmp_dcf') or {}).get('value', 0)
    if pio_val <= 3 and fmp_dcf_val and fmp_dcf_val < 0:
        risk_warnings.append(f"🚨 KALİTE TUZAĞI SİNYALİ — Piotroski {pio_val}/9 + FMP DCF negatif kombinasyonu klasik value trap deseni. Adil değer ucuz görünebilir ama fundamental dayanak zayıf.")
    
    if risk_warnings:
        md.append("### v5.0 Risk Uyarıları")
        md.append("")
        for w in risk_warnings:
            md.append(f"- {w}")
        md.append("")
        md.append("_Otomatik karar yalnızca fiyat vs adil değer karşılaştırmasına dayanır. Yukarıdaki sinyaller pozisyon büyüklüğü ve giriş zamanlamasına etki etmeli._")
        md.append("")
    
    md.append(f"**Kaynak**: finzora ai — Adil Değer Skill v{result['version']}")
    md.append("")
    
    md_text = "\n".join(md)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_text)
        print(f"📄 Rapor yazıldı: {output_path}", file=sys.stderr)
    
    return md_text


def update_research_index(result, md_path, repo_root=None):
    """
    data/research/index.json içindeki 'analizler' dizisine yeni giriş ekler.
    
    repo_root: portfolio-tracker repo kökü (auto-detect: script dizininden 3 üst)
    """
    if repo_root is None:
        # scripts/adil_deger.py → skills/adil-deger-9-yontem/scripts → skills/adil-deger-9-yontem → skills → portfolio-tracker
        repo_root = os.path.abspath(os.path.join(_SCRIPT_DIR, '..', '..', '..'))
    
    index_path = os.path.join(repo_root, 'data', 'research', 'index.json')
    
    # Index dosyasını oku
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    else:
        index_data = {
            "son_guncelleme": "",
            "toplam_analiz": 0,
            "aktif_izleme": 0,
            "beklemede": 0,
            "beat_tahmin": 0,
            "miss_tahmin": 0,
            "dogru_tahmin_orani": None,
            "analizler": [],
        }
    
    analizler = index_data.get('analizler', [])
    
    # Pre-IPO modu mu standart mı?
    ticker = result['ticker']
    today = datetime.now().strftime('%Y-%m-%d')
    entry_id = f"{ticker}_ADIL_DEGER_{today}"
    
    # Mevcut girişi temizle (aynı id varsa)
    analizler = [a for a in analizler if a.get('id') != entry_id]
    
    # Pre-IPO için ayrı şema
    if result.get('mode') == 'PRE_IPO':
        proj = result.get('projection', {})
        pnl_table = proj.get('pnl', [])
        # Normalize edilmiş forward EPS
        eps_y2 = next((r['eps_basic'] for r in pnl_table if r['year'] == datetime.now().year + 1), None)
        
        entry = {
            "id": entry_id,
            "ticker": ticker,
            "sirket": result.get('company', ticker),
            "sektor": result.get('sector_key', 'unknown'),
            "analiz_tarihi": today,
            "ipo_tarihi": result.get('ipo_date'),
            "analiz_turu": "pre_ipo_adil_deger",
            "durum": "aktif_izleme",
            "dosya": os.path.relpath(md_path, repo_root) if md_path else None,
            "ipo_fiyat_aralik": [result.get('ipo_price_low'), result.get('ipo_price_high')],
            "ipo_fiyat_orta": result.get('ipo_price_mid'),
            "projeksiyon": {
                "profile_key": proj.get('profile_key'),
                "normalizasyon_yili": proj.get('normalization', {}).get('pe_normalization_year'),
                "sektor_pe_medyan": proj.get('sector_median_pe_used'),
                "5y_son_eps": pnl_table[-1].get('eps_basic') if pnl_table else None,
                "5y_son_revenue_b": (pnl_table[-1].get('revenue', 0) / 1e9) if pnl_table else None,
            },
            "notlar": result.get('notes', ''),
            "gerceklesen": {
                "ipo_aktivasyon": None,
                "ilk_islem_fiyati": None,
                "1ay_sonra": None,
                "3ay_sonra": None,
                "12ay_sonra": None,
            },
            "etiketler": ["pre_ipo", "v5.0_skill"],
        }
    else:
        # Standart akış
        p = result['profile']
        di = result['data_inputs']
        v5 = result.get('v5_signals', {})
        proj = result.get('projection', {})
        normal_main = (result['summaries']['normal'].get('main') or {})
        bear_main = (result['summaries']['bear'].get('main') or {})
        bull_main = (result['summaries']['bull'].get('main') or {})
        normal_median = normal_main.get('median')
        price = p['price']
        
        # Confidence — v5 sinyallerinden türet
        confidence = "ORTA"
        if v5.get('altman_z', {}).get('label') == 'GÜVENLİ' and v5.get('piotroski', {}).get('value', 0) >= 7:
            confidence = "YUKSEK"
        elif v5.get('altman_z', {}).get('label') == 'İFLAS RİSKİ' or v5.get('piotroski', {}).get('value', 9) <= 3:
            confidence = "DUSUK"
        
        normal_methods = result['methods_by_regime']['normal']
        kullanilabilir = sum(1 for cat in ['traditional', 'forward', 'growth']
                             for v in normal_methods.get(cat, {}).values() if v is not None and v > 0)
        kullanilamaz = 9 - kullanilabilir
        
        # Senaryo getirileri
        bear_med = bear_main.get('median')
        bull_med = bull_main.get('median')
        
        # Stop loss (~%13 altı)
        stop_loss = round(price * 0.87, 2)
        
        # Portföy önerileri (markdown'dakiyle aynı mantık)
        mode = result['mode']
        is_growth = (mode == 'GROWTH')
        is_ai = result['is_ai_megacap']
        altman_safe = (v5.get('altman_z', {}).get('label') == 'GÜVENLİ')
        roe = di.get('roe_pct', 0)
        
        dengeli = "uygun" if (altman_safe and not v5.get('upgrade_momentum', {}).get('direction') == 'downgrade') else "uygun_kosullu"
        agresif = "uygun" if (is_growth or is_ai) else "uygun_kosullu"
        if roe > 15 and altman_safe and not is_growth:
            temettu = "uygun"
        elif is_growth:
            temettu = "uygun_degil"
        else:
            temettu = "uygun_kosullu"
        
        entry = {
            "id": entry_id,
            "ticker": ticker,
            "sirket": p.get('name', ticker),
            "sektor": f"{p.get('sector', '')} / {p.get('industry', '')}",
            "analiz_tarihi": today,
            "analiz_turu": "adil_deger_hesabi",
            "durum": "aktif_izleme",
            "dosya": os.path.relpath(md_path, repo_root) if md_path else None,
            "adil_deger": {
                "yontem_v": "v5.0",
                "mod": mode,
                "kullanilabilir_yontem_sayisi": kullanilabilir,
                "kullanilamayan_yontem_sayisi": kullanilamaz,
                "agirlikli_adil_deger": round(normal_median, 2) if normal_median else None,
                "confidence": confidence,
                "quality_premium": round(result.get('quality_mult', 1.0), 3),
                "ai_mega_cap": is_ai,
            },
            "on_beklenti": {
                "senaryo_boga": {"fiyat_hedef": round(bull_med, 2) if bull_med else None,
                                 "getiri_pct": round((bull_med - price) / price * 100, 1) if bull_med else None,
                                 "olasilik": 0.225},
                "senaryo_baz": {"fiyat_hedef": round(normal_median, 2) if normal_median else None,
                                "getiri_pct": round((normal_median - price) / price * 100, 1) if normal_median else None,
                                "olasilik": 0.475},
                "senaryo_ayi": {"fiyat_hedef": round(bear_med, 2) if bear_med else None,
                                "getiri_pct": round((bear_med - price) / price * 100, 1) if bear_med else None,
                                "olasilik": 0.30},
            },
            "analiz_fiyati": price,
            "temel_metrikler": {
                "pe_ttm": round(price / di['eps_ttm'], 2) if di['eps_ttm'] and di['eps_ttm'] > 0 else None,
                "forward_pe": round(price / di.get('eps_fwd_2y', 0), 2) if di.get('eps_fwd_2y') else None,
                "roe_ttm_pct": di['roe_pct'],
                "net_margin_pct": di['net_margin_pct'],
                "revenue_growth_yoy_pct": di.get('revenue_growth_yoy_pct'),
                "piyasa_degeri_m": round((p.get('market_cap') or 0) / 1e6, 0),
                "beta": p.get('beta'),
                "vix_at_analysis": result['market_regime']['vix'],
            },
            "v5_sinyaller": {
                "altman_z": v5.get('altman_z'),
                "piotroski": v5.get('piotroski'),
                "analist_sentiment": v5.get('grades_consensus'),
                "upgrade_momentum": v5.get('upgrade_momentum'),
                "fmp_dcf_unlevered": v5.get('fmp_dcf', {}).get('value') if v5.get('fmp_dcf') else None,
                "konsantrasyon_urun": v5.get('concentration_risk_product'),
                "konsantrasyon_cografya": v5.get('concentration_risk_geo'),
                "canli_sektor_pe": v5.get('live_pe', {}).get('value') if v5.get('live_pe') else None,
                "dinamik_wacc": v5.get('dynamic_wacc', {}).get('value') if v5.get('dynamic_wacc') else None,
            },
            "projeksiyon": {
                "profile_key": proj.get('profile_key') if proj else None,
                "normalizasyon_yili": proj.get('normalization', {}).get('pe_normalization_year') if proj else None,
            } if proj else None,
            "portfoy_onerisi": {
                "dengeli": dengeli,
                "agresif": agresif,
                "temettu": temettu,
            },
            "giris_plani": {
                "stop_loss": stop_loss,
                "hedef_1": round(normal_median, 2) if normal_median else None,
                "hedef_2": round(bull_med, 2) if bull_med else None,
            },
            "karar": result['decision']['action'],
            "karar_gerekce": result['decision']['reasoning'],
            "gerceklesen": {
                "tespit_fiyati": price,
                "simdiki_fiyat": None,
                "fiyat_tepkisi_pct": 0,
                "tez_tuttu": None,
                "ders": None,
            },
            "etiketler": [mode.lower(), "v5.0_skill"] + (["ai_megacap"] if is_ai else []) + ([s for s in [proj.get('profile_key')] if s and proj]),
        }
    
    analizler.append(entry)
    
    # Üst-seviye sayaçları güncelle
    index_data['analizler'] = analizler
    index_data['son_guncelleme'] = today
    index_data['toplam_analiz'] = len(analizler)
    index_data['aktif_izleme'] = sum(1 for a in analizler if a.get('durum') == 'aktif_izleme')
    
    # Yaz
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print(f"📋 index.json güncellendi ({index_path}): {entry_id}", file=sys.stderr)
    return index_path


def git_commit_and_push(ticker, md_path, index_path, repo_root=None, push=True):
    """
    Markdown rapor + index.json'ı git'e kaydet, push et.
    """
    import subprocess
    
    if repo_root is None:
        repo_root = os.path.abspath(os.path.join(_SCRIPT_DIR, '..', '..', '..'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Dosya yollarını relatif yap
    md_rel = os.path.relpath(md_path, repo_root) if os.path.isabs(md_path) else md_path
    index_rel = os.path.relpath(index_path, repo_root) if os.path.isabs(index_path) else index_path
    
    try:
        # git add
        subprocess.run(['git', 'add', md_rel, index_rel], cwd=repo_root, check=True, capture_output=True)
        
        # Değişiklik var mı?
        diff = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=repo_root, capture_output=True)
        if diff.returncode == 0:
            print(f"⚠️ Değişiklik yok, commit atlanıyor", file=sys.stderr)
            return False
        
        # commit
        commit_msg = f"[VALUATION] {ticker} adil değer hesabı eklendi ({today})"
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_root, check=True, capture_output=True)
        print(f"💾 Commit: {commit_msg}", file=sys.stderr)
        
        if push:
            # Push (rebase ile)
            try:
                subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], cwd=repo_root, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                pass  # Önemli değil, ana push deneyelim
            
            push_result = subprocess.run(['git', 'push', 'origin', 'main'], cwd=repo_root, capture_output=True)
            if push_result.returncode == 0:
                print(f"📤 Push edildi: origin/main", file=sys.stderr)
                return True
            else:
                print(f"❌ Push başarısız: {push_result.stderr.decode()}", file=sys.stderr)
                return False
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git hatası: {e.stderr.decode() if e.stderr else e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Kullanım:")
        print("  python adil_deger.py TICKER [--json] [--md] [--md-out PATH] [--commit] [--no-push]")
        print("  python adil_deger.py --pre-ipo input.json [--md] [--commit]")
        print()
        print("Flag'ler:")
        print("  --json        JSON çıktı (tüm result dict)")
        print("  --md          Markdown rapor üret + chat'te göster + dosyaya yaz")
        print("  --md-out PATH Custom markdown output path (default: reports/research/X_ADIL_DEGER_DATE.md)")
        print("  --commit      Markdown + index.json + git commit + push (--md ile birlikte)")
        print("  --no-push     --commit ile commit yapar ama push etmez")
        sys.exit(1)
    
    json_only = '--json' in sys.argv
    md_only = '--md' in sys.argv
    commit_flag = '--commit' in sys.argv
    no_push = '--no-push' in sys.argv
    
    # --commit aktif ise otomatik --md
    if commit_flag:
        md_only = True
    
    md_out_path = None
    if '--md-out' in sys.argv:
        idx = sys.argv.index('--md-out')
        if idx + 1 < len(sys.argv):
            md_out_path = sys.argv[idx + 1]
    
    # Pre-IPO modu
    if '--pre-ipo' in sys.argv:
        idx = sys.argv.index('--pre-ipo')
        if idx + 1 >= len(sys.argv):
            print("HATA: --pre-ipo sonrasında JSON dosya yolu lazım")
            sys.exit(1)
        input_path = sys.argv[idx + 1]
        result = analyze_pre_ipo(input_path)
        
        if 'error' in result:
            print(f"HATA: {result['error']}")
            sys.exit(1)
        
        if json_only:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
            return
        
        if md_only:
            # Pre-IPO için sade markdown - şu an protokol markdown'ı sadece standart için
            # Pre-IPO için minimal markdown üret
            today = datetime.now().strftime('%Y-%m-%d')
            if not md_out_path:
                # Repo köküne göre
                repo_root = os.path.abspath(os.path.join(_SCRIPT_DIR, '..', '..', '..'))
                md_out_path = os.path.join(repo_root, 'reports', 'research', f"{result['ticker']}_ADIL_DEGER_{today}.md")
            
            md_text = format_pre_ipo_output(result)
            os.makedirs(os.path.dirname(md_out_path), exist_ok=True)
            with open(md_out_path, 'w', encoding='utf-8') as f:
                f.write(f"# {result['ticker']} - {result['company']} | Pre-IPO Adil Değer Raporu\n\n")
                f.write(f"**Tarih**: {today}  |  **Mod**: PRE_IPO  |  **Skill**: Adil Değer v{result['version']}\n\n")
                f.write("```\n")
                f.write(md_text)
                f.write("\n```\n\nKaynak: finzora ai\n")
            print(f"📄 Pre-IPO rapor yazıldı: {md_out_path}", file=sys.stderr)
            print(md_text)
            
            if commit_flag:
                index_path = update_research_index(result, md_out_path)
                git_commit_and_push(result['ticker'], md_out_path, index_path, push=not no_push)
        else:
            print(format_pre_ipo_output(result))
        return
    
    # Standart akış
    ticker = sys.argv[1].upper()
    
    result = analyze(ticker)
    
    if 'error' in result:
        print(f"HATA: {result['error']}")
        sys.exit(1)
    
    if json_only:
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        return
    
    if md_only:
        today = datetime.now().strftime('%Y-%m-%d')
        if not md_out_path:
            repo_root = os.path.abspath(os.path.join(_SCRIPT_DIR, '..', '..', '..'))
            md_out_path = os.path.join(repo_root, 'reports', 'research', f"{ticker}_ADIL_DEGER_{today}.md")
        md_text = format_markdown_report(result, output_path=md_out_path)
        print(md_text)
        
        if commit_flag:
            index_path = update_research_index(result, md_out_path)
            git_commit_and_push(ticker, md_out_path, index_path, push=not no_push)
        return
    
    print(format_output(result))


if __name__ == "__main__":
    main()
