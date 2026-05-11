"""
Forward Projection Engine — Adil Değer Skill v5.0
==================================================

5 yıllık P&L projeksiyonu + çarpan projeksiyonu + normalizasyon yılı tespiti.

Mantık:
1. Sektör bazlı marj rampup eğrileri (preset)
2. Peer şirketlerin gerçek tarihsel marj evrimi (canlı, opsiyonel)
3. Yıllık gelir + brüt + faaliyet + net + EPS tablosu
4. Forward P/E, P/S, EV/EBITDA çarpanları (mevcut fiyat sabit varsayımıyla)
5. "Hangi yıl sektör medyanına oturur?" yorumu

v5.0 — 11 Mayıs 2026
finzora ai
"""

from datetime import datetime


# =============================================================================
# SEKTÖR MARJ PROFİLLERİ
# =============================================================================
# Her profil 6 yıl: [Yıl 0 (TTM gerçek), Yıl 1, Yıl 2, Yıl 3, Yıl 4, Yıl 5]
#
# Veri kaynakları:
# - NVDA 2018-2024 income statement (semicon_design_growth_ai için baz)
# - AMD 2017-2023 (semicon_design_growth için baz)
# - AVGO, MRVL, KLAC olgun yıllar (semicon_design_mature için baz)
# - MSFT, ADBE, NOW (tech_software_mature için baz)
# - SNOW, NET, DDOG 2019-2024 (tech_software_growth için baz)

SECTOR_MARGIN_PROFILES = {
    # ----- HIZLA BÜYÜYEN AI / SEMICON -----
    'semicon_design_growth_ai': {
        'description': 'AI saf oyuncu, hızla büyüyen (CBRS, ARM erken yıllar, NVDA 2018-2020 gibi)',
        'gross_margin_curve':    [0.39, 0.42, 0.46, 0.50, 0.52, 0.54],
        'op_margin_curve':       [-0.28, -0.03, 0.10, 0.17, 0.22, 0.25],
        'net_margin_curve':      [-0.15, -0.08, 0.06, 0.12, 0.16, 0.19],
        'effective_tax_curve':   [0.00, 0.00, 0.10, 0.15, 0.18, 0.21],
        'capex_pct_revenue':     [0.08, 0.12, 0.10, 0.08, 0.07, 0.06],
    },
    'semicon_design_growth': {
        'description': 'Olgunlaşmaya doğru ilerleyen büyüyen yarı iletken (AMD 2017-2020 gibi)',
        'gross_margin_curve':    [0.45, 0.47, 0.49, 0.51, 0.53, 0.54],
        'op_margin_curve':       [0.05, 0.10, 0.15, 0.20, 0.24, 0.27],
        'net_margin_curve':      [0.03, 0.07, 0.12, 0.16, 0.20, 0.22],
        'effective_tax_curve':   [0.15, 0.16, 0.18, 0.20, 0.21, 0.21],
        'capex_pct_revenue':     [0.06, 0.07, 0.06, 0.05, 0.05, 0.04],
    },
    'semicon_design_mature': {
        'description': 'Olgun, güçlü marjlı yarı iletken (NVDA 2024, AVGO, MRVL gibi)',
        'gross_margin_curve':    [0.55, 0.56, 0.57, 0.57, 0.58, 0.58],
        'op_margin_curve':       [0.32, 0.33, 0.34, 0.34, 0.35, 0.35],
        'net_margin_curve':      [0.26, 0.27, 0.28, 0.28, 0.29, 0.29],
        'effective_tax_curve':   [0.21, 0.21, 0.21, 0.21, 0.21, 0.21],
        'capex_pct_revenue':     [0.04, 0.04, 0.04, 0.04, 0.04, 0.04],
    },
    'semicon_equipment': {
        'description': 'Semicon equipment (ASML, AMAT, LRCX, KLAC gibi)',
        'gross_margin_curve':    [0.48, 0.49, 0.50, 0.50, 0.51, 0.51],
        'op_margin_curve':       [0.28, 0.29, 0.30, 0.31, 0.31, 0.32],
        'net_margin_curve':      [0.23, 0.24, 0.25, 0.25, 0.26, 0.26],
        'effective_tax_curve':   [0.18, 0.18, 0.18, 0.18, 0.18, 0.18],
        'capex_pct_revenue':     [0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
    },
    'semicon_osat': {
        'description': 'OSAT (foundry, packaging — AMKR, ASE gibi)',
        'gross_margin_curve':    [0.15, 0.16, 0.17, 0.17, 0.18, 0.18],
        'op_margin_curve':       [0.05, 0.06, 0.07, 0.08, 0.09, 0.09],
        'net_margin_curve':      [0.04, 0.05, 0.06, 0.06, 0.07, 0.07],
        'effective_tax_curve':   [0.15, 0.15, 0.15, 0.15, 0.15, 0.15],
        'capex_pct_revenue':     [0.18, 0.18, 0.16, 0.15, 0.14, 0.13],
    },
    # ----- YAZILIM -----
    'tech_software_growth': {
        'description': 'Hızla büyüyen SaaS, kâra geçmemiş (SNOW, NET, DDOG 2020-2022 gibi)',
        'gross_margin_curve':    [0.70, 0.73, 0.75, 0.77, 0.78, 0.79],
        'op_margin_curve':       [-0.20, -0.10, 0.00, 0.08, 0.15, 0.20],
        'net_margin_curve':      [-0.15, -0.08, 0.00, 0.06, 0.12, 0.16],
        'effective_tax_curve':   [0.00, 0.00, 0.10, 0.15, 0.18, 0.20],
        'capex_pct_revenue':     [0.04, 0.04, 0.04, 0.03, 0.03, 0.03],
    },
    'tech_software_mature_saas': {
        'description': 'Olgun SaaS (MSFT, ADBE, NOW, CRM gibi)',
        'gross_margin_curve':    [0.78, 0.79, 0.80, 0.80, 0.81, 0.81],
        'op_margin_curve':       [0.30, 0.32, 0.33, 0.34, 0.34, 0.35],
        'net_margin_curve':      [0.24, 0.25, 0.26, 0.27, 0.27, 0.28],
        'effective_tax_curve':   [0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
        'capex_pct_revenue':     [0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
    },
    'tech_hardware': {
        'description': 'Tech donanım (DELL, HPE, SMCI gibi)',
        'gross_margin_curve':    [0.20, 0.21, 0.22, 0.22, 0.23, 0.23],
        'op_margin_curve':       [0.08, 0.09, 0.10, 0.10, 0.11, 0.11],
        'net_margin_curve':      [0.06, 0.07, 0.07, 0.08, 0.08, 0.09],
        'effective_tax_curve':   [0.18, 0.18, 0.18, 0.18, 0.18, 0.18],
        'capex_pct_revenue':     [0.03, 0.03, 0.03, 0.03, 0.03, 0.03],
    },
    # ----- SAĞLIK -----
    'healthcare_biotech_pre_revenue': {
        'description': 'Pre-revenue veya minimal revenue biotech (klinik aşama)',
        'gross_margin_curve':    [0.85, 0.85, 0.85, 0.85, 0.85, 0.85],
        'op_margin_curve':       [-2.00, -1.50, -0.80, -0.20, 0.10, 0.25],
        'net_margin_curve':      [-2.00, -1.50, -0.80, -0.20, 0.08, 0.20],
        'effective_tax_curve':   [0.00, 0.00, 0.00, 0.00, 0.10, 0.21],
        'capex_pct_revenue':     [0.02, 0.02, 0.02, 0.02, 0.02, 0.02],
    },
    'healthcare_biotech': {
        'description': 'Ticari biotech (kâr veren)',
        'gross_margin_curve':    [0.82, 0.83, 0.84, 0.85, 0.86, 0.86],
        'op_margin_curve':       [0.25, 0.27, 0.29, 0.30, 0.31, 0.32],
        'net_margin_curve':      [0.20, 0.22, 0.23, 0.24, 0.25, 0.25],
        'effective_tax_curve':   [0.18, 0.18, 0.18, 0.18, 0.18, 0.18],
        'capex_pct_revenue':     [0.03, 0.03, 0.03, 0.03, 0.03, 0.03],
    },
    'healthcare_pharma': {
        'description': 'Büyük ilaç şirketleri (PFE, JNJ, LLY gibi)',
        'gross_margin_curve':    [0.75, 0.76, 0.76, 0.77, 0.77, 0.78],
        'op_margin_curve':       [0.30, 0.31, 0.32, 0.32, 0.33, 0.33],
        'net_margin_curve':      [0.22, 0.23, 0.24, 0.24, 0.25, 0.25],
        'effective_tax_curve':   [0.16, 0.16, 0.16, 0.16, 0.16, 0.16],
        'capex_pct_revenue':     [0.04, 0.04, 0.04, 0.04, 0.04, 0.04],
    },
    'healthcare_devices': {
        'description': 'Medical devices (ISRG, EW, BSX, MDT gibi)',
        'gross_margin_curve':    [0.65, 0.66, 0.66, 0.67, 0.67, 0.68],
        'op_margin_curve':       [0.22, 0.23, 0.24, 0.24, 0.25, 0.25],
        'net_margin_curve':      [0.17, 0.18, 0.18, 0.19, 0.19, 0.20],
        'effective_tax_curve':   [0.18, 0.18, 0.18, 0.18, 0.18, 0.18],
        'capex_pct_revenue':     [0.04, 0.04, 0.04, 0.04, 0.04, 0.04],
    },
    # ----- DİĞER -----
    'consumer_staples': {
        'description': 'KO, PG, PEP, COST gibi',
        'gross_margin_curve':    [0.45, 0.45, 0.46, 0.46, 0.46, 0.47],
        'op_margin_curve':       [0.22, 0.22, 0.23, 0.23, 0.23, 0.24],
        'net_margin_curve':      [0.17, 0.17, 0.18, 0.18, 0.18, 0.18],
        'effective_tax_curve':   [0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
        'capex_pct_revenue':     [0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
    },
    'industrials': {
        'description': 'Sanayi şirketleri (CAT, HON, GE, RTX gibi)',
        'gross_margin_curve':    [0.30, 0.30, 0.31, 0.31, 0.31, 0.32],
        'op_margin_curve':       [0.13, 0.13, 0.14, 0.14, 0.15, 0.15],
        'net_margin_curve':      [0.09, 0.09, 0.10, 0.10, 0.10, 0.11],
        'effective_tax_curve':   [0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
        'capex_pct_revenue':     [0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
    },
    'energy': {
        'description': 'Enerji (XOM, CVX, OXY gibi)',
        'gross_margin_curve':    [0.30, 0.30, 0.30, 0.30, 0.30, 0.30],
        'op_margin_curve':       [0.14, 0.14, 0.14, 0.14, 0.14, 0.14],
        'net_margin_curve':      [0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
        'effective_tax_curve':   [0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
        'capex_pct_revenue':     [0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
    },
    'financials_bank': {
        'description': 'Bankalar (JPM, BAC, WFC gibi)',
        'gross_margin_curve':    [0.55, 0.55, 0.55, 0.55, 0.55, 0.55],
        'op_margin_curve':       [0.30, 0.30, 0.30, 0.30, 0.30, 0.30],
        'net_margin_curve':      [0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
        'effective_tax_curve':   [0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
        'capex_pct_revenue':     [0.02, 0.02, 0.02, 0.02, 0.02, 0.02],
    },
    # ----- GENERIC FALLBACK -----
    'generic': {
        'description': 'Genel (sektör tespit edilemedi)',
        'gross_margin_curve':    [0.40, 0.41, 0.42, 0.42, 0.43, 0.43],
        'op_margin_curve':       [0.15, 0.16, 0.16, 0.17, 0.17, 0.18],
        'net_margin_curve':      [0.10, 0.11, 0.11, 0.12, 0.12, 0.13],
        'effective_tax_curve':   [0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
        'capex_pct_revenue':     [0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
    },
}


# =============================================================================
# MOD TESPİTİ - Sektör + Büyüme Aşaması → Profil
# =============================================================================

def detect_margin_profile(sector_key, current_op_margin, revenue_yoy_growth, is_pre_revenue=False):
    """
    Şirketin sektör + büyüme aşaması → marj profili seçer.
    
    Args:
        sector_key: 'semicon_design', 'tech_software' gibi
        current_op_margin: mevcut faaliyet marjı (örn -0.28 veya 0.32)
        revenue_yoy_growth: yıllık gelir büyümesi (örn 0.76)
        is_pre_revenue: çok düşük gelir (biotech)
    
    Returns: profile_key (SECTOR_MARGIN_PROFILES anahtarı)
    """
    sector_key = (sector_key or 'generic').lower()
    
    # Biotech özel
    if is_pre_revenue and 'biotech' in sector_key:
        return 'healthcare_biotech_pre_revenue'
    
    # Yarı iletken
    if 'semicon_design' in sector_key:
        if current_op_margin < 0.05 and revenue_yoy_growth > 0.50:
            return 'semicon_design_growth_ai'
        elif current_op_margin < 0.20:
            return 'semicon_design_growth'
        else:
            return 'semicon_design_mature'
    
    if 'semicon_equipment' in sector_key:
        return 'semicon_equipment'
    
    if 'semicon_osat' in sector_key:
        return 'semicon_osat'
    
    # Yazılım
    if 'software' in sector_key or 'tech_software' in sector_key:
        if current_op_margin < 0.10 and revenue_yoy_growth > 0.30:
            return 'tech_software_growth'
        else:
            return 'tech_software_mature_saas'
    
    if 'hardware' in sector_key:
        return 'tech_hardware'
    
    # Sağlık
    if 'biotech' in sector_key:
        return 'healthcare_biotech'
    if 'pharma' in sector_key:
        return 'healthcare_pharma'
    if 'devices' in sector_key:
        return 'healthcare_devices'
    
    # Diğer
    if 'consumer_staples' in sector_key:
        return 'consumer_staples'
    if 'industrials' in sector_key:
        return 'industrials'
    if 'energy' in sector_key:
        return 'energy'
    if 'bank' in sector_key:
        return 'financials_bank'
    
    return 'generic'


# =============================================================================
# YILLIK P&L PROJEKSİYONU
# =============================================================================

def project_revenue_5y(revenue_ttm, revenue_yoy_growth, analyst_rev_1y=None, analyst_rev_2y=None,
                       custom_revenues=None, ttm_year=None, analyst_revenues_dict=None):
    """
    5 yıllık gelir projeksiyonu.
    
    Yıl yapılandırması:
    - Yıl 0 = ttm_year (default: current_year - 1) — TTM ACTUAL (geçmiş bilanço)
    - Yıl 1-5 = ttm_year + 1 ... ttm_year + 5 — projeksiyon
    
    v5.0 Etap 9 öncelik sırası (yüksekten düşüğe):
    1. custom_revenues (pre-IPO veya manuel)
    2. analyst_revenues_dict (FMP analyst-estimates, yıl yıl) — YENİ
    3. analyst_rev_1y / analyst_rev_2y (eski tek nokta parametreler)
    4. revenue_yoy_growth ile extrapolation
    
    analyst_revenues_dict şeması:
        {2027: 368e9, 2028: 486e9, 2029: 567e9, ...} ($ cinsinden)
    
    Returns: list of (year, revenue) tuples, 6 element (yıl 0 TTM + 5 yıl projection)
    """
    if ttm_year is None:
        ttm_year = datetime.now().year - 1
    
    revenues = [(ttm_year, revenue_ttm)]
    
    if custom_revenues:
        for i in range(1, 6):
            year = ttm_year + i
            if year in custom_revenues:
                revenues.append((year, custom_revenues[year]))
            else:
                # Önceki yıldan %20 büyüme fallback
                prev = revenues[-1][1]
                revenues.append((year, prev * 1.20))
        return revenues
    
    # v5.0 Etap 9: analyst_revenues_dict varsa onu öncele
    if analyst_revenues_dict:
        for i in range(1, 6):
            year = ttm_year + i
            if year in analyst_revenues_dict and analyst_revenues_dict[year]:
                revenues.append((year, analyst_revenues_dict[year]))
            else:
                # Yıl bulunamadıysa önceki yıldan profile fallback
                prev = revenues[-1][1]
                # Geriye gidip yıl bazlı büyüme oranı tahmin et
                if len(revenues) >= 2:
                    last_growth = (revenues[-1][1] / revenues[-2][1] - 1) if revenues[-2][1] > 0 else 0.15
                    last_growth = max(0.05, min(0.50, last_growth * 0.7))  # decay + cap
                else:
                    last_growth = 0.15
                revenues.append((year, prev * (1 + last_growth)))
        return revenues
    
    # Yıl 1 (eski tek-nokta parametreler)
    if analyst_rev_1y and analyst_rev_1y > 0:
        rev_y1 = analyst_rev_1y
    else:
        rev_y1 = revenue_ttm * (1 + revenue_yoy_growth)
    revenues.append((ttm_year + 1, rev_y1))
    
    # Yıl 2
    if analyst_rev_2y and analyst_rev_2y > 0:
        rev_y2 = analyst_rev_2y
    else:
        rev_y2 = rev_y1 * (1 + revenue_yoy_growth * 0.85)
    revenues.append((ttm_year + 2, rev_y2))
    
    # Yıl 3, 4, 5 — kademeli azalan büyüme (v5.0 Etap 5: AMD gibi aşırı agresif decay sorununu çöz)
    # Y2 analist konsensüsü genelde optimistic; Y3-Y5 daha sert decay + mutlak cap
    y1_y2_growth = (rev_y2 / rev_y1) - 1 if rev_y1 > 0 else 0.20
    
    # Mutlak cap: yüksek y1_y2_growth (örn %90 AMD) Y3-Y5'e doğrudan yansımamalı
    g_y3 = min(max(0.10, y1_y2_growth * 0.55), 0.30)  # max %30
    g_y4 = min(max(0.08, y1_y2_growth * 0.35), 0.22)  # max %22
    g_y5 = min(max(0.05, y1_y2_growth * 0.20), 0.15)  # max %15
    
    rev_y3 = rev_y2 * (1 + g_y3)
    rev_y4 = rev_y3 * (1 + g_y4)
    rev_y5 = rev_y4 * (1 + g_y5)
    
    revenues.append((ttm_year + 3, rev_y3))
    revenues.append((ttm_year + 4, rev_y4))
    revenues.append((ttm_year + 5, rev_y5))
    
    return revenues


def project_pnl_5y(revenue_list, profile_key, shares_basic, shares_diluted=None,
                   interest_expense_annual=0, override_curves=None,
                   actual_ttm_margins=None):
    """
    5 yıllık tam P&L tablosu.
    
    v5.0 Etap 10: actual_ttm_margins verildiğinde DELTA-BASED projection.
    Profile mutlak değer yerine "trend" olarak yorumlanır:
    - Y0 = şirketin gerçek TTM marjı
    - Y1-Y5 = profile delta'ları (Y1-Y0, Y2-Y1, ...) TTM üzerine uygulanır
    
    Bu sayede NVDA (TTM gross %75) ve INTC (TTM gross %32) aynı 
    `semicon_design_mature` profilini kullanır ama doğru başlar.
    
    Args:
        revenue_list: project_revenue_5y çıktısı [(year, revenue), ...]
        profile_key: SECTOR_MARGIN_PROFILES anahtarı
        shares_basic: basic shares outstanding
        shares_diluted: fully diluted shares (yoksa basic kullanılır)
        interest_expense_annual: yıllık faiz gideri ($)
        override_curves: {'gross_margin_curve': [...], ...} — profile yerine bunları kullan
        actual_ttm_margins: {'gross': 0.75, 'op': 0.31, 'net': 0.26, 'tax': 0.21, 'capex': 0.04}
                            Verilirse delta-based projection devreye girer.
                            None ise eski mutlak profil davranışı.
    
    Returns: list of dicts (6 yıl: yıl 0 TTM + 5 yıl projeksiyon)
    """
    profile = SECTOR_MARGIN_PROFILES.get(profile_key, SECTOR_MARGIN_PROFILES['generic'])
    
    gm_raw = profile['gross_margin_curve'][:]
    op_m_raw = profile['op_margin_curve'][:]
    net_m_raw = profile['net_margin_curve'][:]
    tax_r_raw = profile['effective_tax_curve'][:]
    capex_p_raw = profile['capex_pct_revenue'][:]
    
    if override_curves:
        gm_raw = override_curves.get('gross_margin_curve', gm_raw)
        op_m_raw = override_curves.get('op_margin_curve', op_m_raw)
        net_m_raw = override_curves.get('net_margin_curve', net_m_raw)
        tax_r_raw = override_curves.get('effective_tax_curve', tax_r_raw)
        capex_p_raw = override_curves.get('capex_pct_revenue', capex_p_raw)
    
    # v5.0 Etap 10: DELTA-BASED hesaplama
    if actual_ttm_margins:
        ttm_gross = actual_ttm_margins.get('gross', gm_raw[0])
        ttm_op = actual_ttm_margins.get('op', op_m_raw[0])
        ttm_net = actual_ttm_margins.get('net', net_m_raw[0])
        ttm_tax = actual_ttm_margins.get('tax', tax_r_raw[0])
        ttm_capex = actual_ttm_margins.get('capex', capex_p_raw[0])
        
        # Profile'dan delta serisi hesapla (Y1-Y0, Y2-Y1, ..., Y5-Y4)
        # Y0 = 0 (TTM gerçek, delta sıfır)
        def deltas(curve):
            return [0.0] + [curve[i] - curve[i-1] for i in range(1, 6)]
        
        gm_d = deltas(gm_raw)
        op_d = deltas(op_m_raw)
        net_d = deltas(net_m_raw)
        tax_d = deltas(tax_r_raw)
        capex_d = deltas(capex_p_raw)
        
        # Kümülatif: Y0 = TTM, Yi = Yi-1 + delta_i
        gm = [ttm_gross + sum(gm_d[:i+1]) for i in range(6)]
        op_m = [ttm_op + sum(op_d[:i+1]) for i in range(6)]
        net_m = [ttm_net + sum(net_d[:i+1]) for i in range(6)]
        tax_r = [ttm_tax + sum(tax_d[:i+1]) for i in range(6)]
        capex_p = [ttm_capex + sum(capex_d[:i+1]) for i in range(6)]
        
        # Sınır kontrolü (marjlar -100% ile +100% arası, vergi 0-50%, capex 0-50%)
        gm = [max(-1.0, min(1.0, v)) for v in gm]
        op_m = [max(-2.0, min(1.0, v)) for v in op_m]
        net_m = [max(-2.0, min(1.0, v)) for v in net_m]
        tax_r = [max(0.0, min(0.50, v)) for v in tax_r]
        capex_p = [max(0.0, min(0.50, v)) for v in capex_p]
    else:
        # Eski mutlak davranış (geriye uyum)
        gm = gm_raw
        op_m = op_m_raw
        net_m = net_m_raw
        tax_r = tax_r_raw
        capex_p = capex_p_raw
    
    if shares_diluted is None or shares_diluted <= 0:
        shares_diluted = shares_basic
    
    pnl = []
    for i, (year, rev) in enumerate(revenue_list[:6]):
        gross_profit = rev * gm[i]
        operating_income = rev * op_m[i]
        opex = gross_profit - operating_income
        
        pretax = operating_income - interest_expense_annual
        tax = max(0, pretax * tax_r[i])  # negatif pretax'ta vergi sıfır
        net_income = pretax - tax
        
        # Net marj override (büyük non-cash kazanç vs vergi olmadan eklenmemeli)
        # Sadece tutarlılık için: net_income / rev ≈ net_m[i] kontrolü
        # Eğer profile net_margin daha düşükse onu kullan (daha güvenli)
        net_income_alt = rev * net_m[i]
        # En düşük olanı al — muhafazakar
        net_income_final = min(net_income, net_income_alt) if net_income > 0 else net_income
        
        eps_basic = net_income_final / shares_basic if shares_basic > 0 else 0
        eps_diluted = net_income_final / shares_diluted if shares_diluted > 0 else 0
        
        capex = rev * capex_p[i]
        
        pnl.append({
            'year': year,
            'revenue': rev,
            'revenue_growth': (rev / revenue_list[i-1][1] - 1) if i > 0 else None,
            'gross_margin': gm[i],
            'gross_profit': gross_profit,
            'op_margin': op_m[i],
            'operating_income': operating_income,
            'opex': opex,
            'interest_expense': interest_expense_annual,
            'pretax_income': pretax,
            'effective_tax_rate': tax_r[i],
            'tax': tax,
            'net_income': net_income_final,
            'net_margin': net_income_final / rev if rev > 0 else 0,
            'eps_basic': eps_basic,
            'eps_diluted': eps_diluted,
            'capex': capex,
        })
    
    return pnl


# =============================================================================
# YILLIK ÇARPAN PROJEKSİYONU (mevcut fiyat sabit varsayımıyla)
# =============================================================================

def project_multiples_5y(pnl_table, current_price, shares_basic, current_cash=0, current_debt=0):
    """
    Yıllık forward çarpanlar — fiyat sabit kalırsa hisse hangi yıl 'ucuz' olur?
    
    Args:
        pnl_table: project_pnl_5y çıktısı
        current_price: bugünkü fiyat
        shares_basic
        current_cash, current_debt: EV hesabı için (sabit varsayılır - basitlik için)
    
    Returns: list of dicts
    """
    market_cap = current_price * shares_basic
    enterprise_value = market_cap - current_cash + current_debt
    
    multiples = []
    for row in pnl_table:
        rev = row['revenue']
        ni = row['net_income']
        eps = row['eps_basic']
        op_income = row['operating_income']
        ebitda_proxy = op_income + (rev * 0.05)  # D&A proxy: ~%5 revenue
        
        fwd_pe = (current_price / eps) if eps > 0 else None
        fwd_ps = (market_cap / rev) if rev > 0 else None
        fwd_ev_sales = (enterprise_value / rev) if rev > 0 else None
        fwd_ev_ebitda = (enterprise_value / ebitda_proxy) if ebitda_proxy > 0 else None
        fwd_ev_ebit = (enterprise_value / op_income) if op_income > 0 else None
        
        multiples.append({
            'year': row['year'],
            'revenue': rev,
            'net_income': ni,
            'eps': eps,
            'fwd_pe': fwd_pe,
            'fwd_ps': fwd_ps,
            'fwd_ev_sales': fwd_ev_sales,
            'fwd_ev_ebitda': fwd_ev_ebitda,
            'fwd_ev_ebit': fwd_ev_ebit,
        })
    
    return multiples


def detect_normalization_year(multiples_table, sector_median_pe=25, sector_median_ev_sales=8):
    """
    Hangi yılda hisse sektör medyan çarpanlarına 'oturur'?
    
    Returns: dict {pe_normalization_year, ev_sales_normalization_year, label}
    """
    pe_year = None
    ev_sales_year = None
    
    for row in multiples_table[1:]:  # yıl 0'ı atla
        if pe_year is None and row['fwd_pe'] is not None and row['fwd_pe'] <= sector_median_pe * 1.20:
            pe_year = row['year']
        if ev_sales_year is None and row['fwd_ev_sales'] is not None and row['fwd_ev_sales'] <= sector_median_ev_sales * 1.20:
            ev_sales_year = row['year']
    
    return {
        'pe_normalization_year': pe_year,
        'ev_sales_normalization_year': ev_sales_year,
        'sector_median_pe': sector_median_pe,
        'sector_median_ev_sales': sector_median_ev_sales,
    }


# =============================================================================
# MARKDOWN ÇIKTI ÜRETİMİ
# =============================================================================

def format_pnl_table_markdown(pnl_table, currency_symbol='$'):
    """Markdown formatlı P&L tablosu."""
    lines = []
    lines.append("| Kalem | " + " | ".join(str(row['year']) for row in pnl_table) + " |")
    lines.append("|" + "---|" * (len(pnl_table) + 1))
    
    def fmt_money(v):
        if v is None:
            return "N/A"
        if abs(v) >= 1e9:
            return f"{currency_symbol}{v/1e9:.2f}B"
        elif abs(v) >= 1e6:
            return f"{currency_symbol}{v/1e6:.0f}M"
        else:
            return f"{currency_symbol}{v:.0f}"
    
    def fmt_pct(v):
        if v is None:
            return "N/A"
        return f"%{v*100:.1f}"
    
    def fmt_eps(v):
        if v is None:
            return "N/A"
        return f"{currency_symbol}{v:.2f}"
    
    rows_def = [
        ("**Gelir**", [fmt_money(r['revenue']) for r in pnl_table]),
        ("Gelir Büyüme", [fmt_pct(r['revenue_growth']) if r['revenue_growth'] is not None else "—" for r in pnl_table]),
        ("Brüt Marj", [fmt_pct(r['gross_margin']) for r in pnl_table]),
        ("Brüt Kâr", [fmt_money(r['gross_profit']) for r in pnl_table]),
        ("Faaliyet Marjı", [fmt_pct(r['op_margin']) for r in pnl_table]),
        ("**Faaliyet Kârı**", [fmt_money(r['operating_income']) for r in pnl_table]),
        ("Faiz Gideri", [fmt_money(-r['interest_expense']) if r['interest_expense'] else "—" for r in pnl_table]),
        ("Vergi Öncesi", [fmt_money(r['pretax_income']) for r in pnl_table]),
        ("Vergi", [fmt_money(-r['tax']) if r['tax'] else "—" for r in pnl_table]),
        ("**Net Kâr**", [fmt_money(r['net_income']) for r in pnl_table]),
        ("Net Marj", [fmt_pct(r['net_margin']) for r in pnl_table]),
        ("**EPS (basic)**", [fmt_eps(r['eps_basic']) for r in pnl_table]),
        ("EPS (diluted)", [fmt_eps(r['eps_diluted']) for r in pnl_table]),
    ]
    
    for label, values in rows_def:
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    
    return "\n".join(lines)


def format_multiples_table_markdown(multiples_table, current_price, currency_symbol='$'):
    """Markdown formatlı çarpan tablosu."""
    lines = []
    lines.append(f"_Fiyat sabit varsayımı: {currency_symbol}{current_price:.2f}_\n")
    lines.append("| Çarpan | " + " | ".join(str(row['year']) for row in multiples_table) + " |")
    lines.append("|" + "---|" * (len(multiples_table) + 1))
    
    def fmt_mult(v, suffix='x'):
        if v is None or v < 0:
            return "N/A"
        if v > 999:
            return ">999"
        return f"{v:.1f}{suffix}"
    
    rows_def = [
        ("**Forward P/E**", [fmt_mult(r['fwd_pe']) for r in multiples_table]),
        ("**Forward P/S**", [fmt_mult(r['fwd_ps']) for r in multiples_table]),
        ("Forward EV/Sales", [fmt_mult(r['fwd_ev_sales']) for r in multiples_table]),
        ("Forward EV/EBITDA", [fmt_mult(r['fwd_ev_ebitda']) for r in multiples_table]),
        ("Forward EV/EBIT", [fmt_mult(r['fwd_ev_ebit']) for r in multiples_table]),
    ]
    
    for label, values in rows_def:
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    
    return "\n".join(lines)


def format_normalization_summary(normalization, multiples_table, sector_label='sektör'):
    """Normalizasyon yılı yorumu."""
    lines = []
    pe_year = normalization['pe_normalization_year']
    sector_pe = normalization['sector_median_pe']
    
    if pe_year is None:
        last_pe = multiples_table[-1]['fwd_pe']
        if last_pe:
            lines.append(f"⚠️  5 yıllık projeksiyon içinde Forward P/E {sector_label} medyanı {sector_pe}x'in altına inmiyor (yıl {multiples_table[-1]['year']}: {last_pe:.0f}x).")
            lines.append(f"   Bu fiyat seviyesinde **çok uzun vadeli** yatırım gerektirir veya hisse pahalı.")
        else:
            lines.append(f"⚠️  Şirket 5 yıl içinde kâra geçmiyor (P/E hesaplanamadı). Spekülatif yatırım.")
    else:
        years_to_wait = pe_year - datetime.now().year
        if years_to_wait <= 2:
            lines.append(f"🟢 Forward P/E {sector_label} medyanı {sector_pe}x'e **{pe_year} yılında** oturur ({years_to_wait} yıl bekleme).")
            lines.append(f"   Yakın vadede makul fiyat görünümü.")
        elif years_to_wait <= 4:
            lines.append(f"🟡 Forward P/E {sector_label} medyanı {sector_pe}x'e **{pe_year} yılında** oturur ({years_to_wait} yıl bekleme).")
            lines.append(f"   Orta vadeli sabır gerekli.")
        else:
            lines.append(f"🟠 Forward P/E {sector_label} medyanı {sector_pe}x'e **{pe_year} yılında** oturur ({years_to_wait} yıl bekleme).")
            lines.append(f"   Uzun vadeli yatırım, yol boyunca volatilite yüksek.")
    
    return "\n".join(lines)
