"""
Adil Değer Hesaplayıcı — FMP API ile
Pine Script v3.5.2 mantığını Python'a uyarlar.

Tüm oranlar FMP'den otomatik olarak 252 günlük tarihsel ortalama ile hesaplanır.
Pine Script historicalLookback=252 mantığına birebir karşılık gelir.

Kullanım:
  python3 scripts/adil_deger_calculator.py AMD
  python3 scripts/adil_deger_calculator.py NVDA --pe-modu rate
  python3 scripts/adil_deger_calculator.py MSFT --pe-modu manuel --manuel-pe 22
  python3 scripts/adil_deger_calculator.py AMD --fwd-eps 5.00
"""

import requests, math, argparse
from datetime import datetime, timedelta

FMP_API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE    = "https://financialmodelingprep.com/stable"

SECTOR_WEIGHTS = {
    # Sıra: [PE, ROE, EvEbit, EvEbitda, EvRev, FwdPE, FwdPS, FCF, Graham, DCF]
    'tech':       [0.10, 0.05, 0.10, 0.13, 0.18, 0.13, 0.18, 0.05, 0.00, 0.08],
    'financial':  [0.18, 0.27, 0.00, 0.00, 0.00, 0.13, 0.00, 0.10, 0.22, 0.10],
    'industrial': [0.10, 0.05, 0.18, 0.18, 0.05, 0.08, 0.05, 0.13, 0.08, 0.10],
    'consumer':   [0.13, 0.10, 0.13, 0.13, 0.10, 0.10, 0.10, 0.10, 0.05, 0.06],
    'energy':     [0.10, 0.10, 0.18, 0.20, 0.05, 0.05, 0.00, 0.17, 0.05, 0.10],
    'healthcare': [0.13, 0.10, 0.10, 0.13, 0.10, 0.13, 0.10, 0.10, 0.05, 0.06],
    'utilities':  [0.13, 0.08, 0.13, 0.18, 0.05, 0.08, 0.00, 0.13, 0.10, 0.12],
    'other':      [0.12, 0.12, 0.12, 0.12, 0.10, 0.12, 0.10, 0.10, 0.05, 0.05],
}

def fmp_get(endpoint, params=None):
    if params is None:
        params = {}
    params['apikey'] = FMP_API_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [FMP HATA] {endpoint}: {e}")
        return None

def safe(val, default=None):
    if val is None:
        return default
    if isinstance(val, (int, float)) and not math.isnan(val):
        return val
    return default

def detect_sector(sector_str: str) -> str:
    s = (sector_str or '').lower()
    if any(x in s for x in ['tech', 'software', 'semiconductor', 'electronic', 'communication']):
        return 'tech'
    if any(x in s for x in ['finance', 'bank', 'insurance']):
        return 'financial'
    if any(x in s for x in ['health', 'pharma', 'biotech', 'medical']):
        return 'healthcare'
    if any(x in s for x in ['energy', 'oil', 'gas', 'mineral']):
        return 'energy'
    if any(x in s for x in ['utilit']):
        return 'utilities'
    if any(x in s for x in ['manufactur', 'industrial', 'transport', 'machinery']):
        return 'industrial'
    if any(x in s for x in ['retail', 'consumer', 'food', 'beverage', 'service']):
        return 'consumer'
    return 'other'


# =========================================================================
# 252 GÜNLÜK TARİHSEL ORAN HESAPLAMA
# Pine Script historicalLookback=252 mantığı — tek geçişte tüm oranlar
# =========================================================================
def fetch_all_252g_ratios(symbol: str, shares: float) -> dict:
    """
    Günlük piyasa değeri + çeyreklik finansallar kullanarak
    252 günlük tarihsel ortalama hesaplar.

    Döndürür: {pe, ps, pfcf, ev_ebit, ev_ebitda, ev_rev}

    Yöntem (Pine Script'e birebir karşılık):
    - Günlük EV  = günlük mktcap + en son çeyreklik net borç
    - TTM metrik = en son 4 çeyreğin kayan toplamı
    - Oran       = EV / TTM_metrik  (veya Fiyat / Hisse_başı_metrik)
    - Ortalama   = 252 günün ortalaması
    """
    today   = datetime.now().strftime("%Y-%m-%d")
    from_dt = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")

    print("  252g tarihsel oranlar hesaplanıyor...", end=" ", flush=True)

    mktcap_hist = fmp_get("historical-market-capitalization",
                          {"symbol": symbol, "from": from_dt, "to": today})
    bal_q = fmp_get("balance-sheet-statement",
                    {"symbol": symbol, "period": "quarter", "limit": 8})
    inc_q = fmp_get("income-statement",
                    {"symbol": symbol, "period": "quarter", "limit": 8})
    cf_q  = fmp_get("cash-flow-statement",
                    {"symbol": symbol, "period": "quarter", "limit": 8})

    if not all([mktcap_hist, bal_q, inc_q, cf_q]):
        print("veri eksik.")
        return {}

    # Net borç haritası: {tarih: net_borç}
    nd_map = {}
    for b in bal_q:
        cash = safe(b.get('cashAndCashEquivalents'), 0) + safe(b.get('shortTermInvestments'), 0)
        nd_map[b['date']] = safe(b.get('totalDebt'), 0) - cash

    # TTM finansal harita: {çeyrek_bitiş_tarihi: {ni, ebit, ebitda, rev, fcf}}
    ttm_map = {}
    min_q = min(len(inc_q), len(cf_q))
    for i in range(min_q - 3):
        g_i = inc_q[i:i+4]
        g_c = cf_q[i:i+4]
        ttm_map[inc_q[i]['date']] = {
            'ni':     sum((q.get('netIncome')       or 0) for q in g_i),
            'ebit':   sum((q.get('operatingIncome') or 0) for q in g_i),
            'ebitda': sum((q.get('ebitda')          or 0) for q in g_i),
            'rev':    sum((q.get('revenue')         or 0) for q in g_i),
            'fcf':    sum((q.get('freeCashFlow')    or 0) for q in g_c),
        }

    s_nd  = sorted(nd_map.keys(),  reverse=True)
    s_ttm = sorted(ttm_map.keys(), reverse=True)

    def get_nd(dt):
        for d in s_nd:
            if dt >= d: return nd_map[d]
        return nd_map[s_nd[-1]]

    def get_ttm(dt):
        for d in s_ttm:
            if dt >= d: return ttm_map[d]
        return ttm_map[s_ttm[-1]]

    # 252 gün döngüsü
    vals = {k: [] for k in ['pe', 'ps', 'pfcf', 'ev_ebit', 'ev_ebitda', 'ev_rev']}

    for row in mktcap_hist[:252]:
        day    = row['date']
        mktcap = row['marketCap']
        nd     = get_nd(day)
        ttm    = get_ttm(day)
        ev     = mktcap + nd
        # Günlük fiyat (mktcap / sabit hisse sayısı — hisse değişimi minimal)
        price_day = mktcap / shares if shares > 0 else 0

        # Hisse başı metrikler
        eps_d = ttm['ni']  / shares if shares > 0 else 0
        rps_d = ttm['rev'] / shares if shares > 0 else 0
        fps_d = ttm['fcf'] / shares if shares > 0 else 0

        if eps_d   > 0 and price_day > 0: vals['pe'].append(price_day   / eps_d)
        if rps_d   > 0 and price_day > 0: vals['ps'].append(price_day   / rps_d)
        if fps_d   > 0 and price_day > 0: vals['pfcf'].append(price_day / fps_d)
        if ttm['ebit']   > 0:             vals['ev_ebit'].append(ev   / ttm['ebit'])
        if ttm['ebitda'] > 0:             vals['ev_ebitda'].append(ev / ttm['ebitda'])
        if ttm['rev']    > 0:             vals['ev_rev'].append(ev   / ttm['rev'])

    result = {}
    for k, lst in vals.items():
        result[k] = sum(lst) / len(lst) if lst else None

    gün = len(mktcap_hist[:252])
    print(f"{gün} gün tamamlandı.")
    return result


# =========================================================================
# DCF
# =========================================================================
def calc_dcf(base_fcf, growth_rate, wacc, terminal_growth, years, net_debt, shares):
    if not (base_fcf and base_fcf > 0 and shares > 0 and wacc > terminal_growth):
        return None
    total_pv, cur_cf = 0.0, base_fcf
    for yr in range(1, years + 1):
        cur_cf   *= (1 + growth_rate)
        total_pv += cur_cf / (1 + wacc) ** yr
    terminal_pv = (cur_cf * (1 + terminal_growth) / (wacc - terminal_growth)) / (1 + wacc) ** years
    equity_val  = total_pv + terminal_pv - net_debt
    return max(0, equity_val / shares) if equity_val > 0 else None


# =========================================================================
# ANA HESAPLAMA
# =========================================================================
def hesapla(symbol: str, pe_modu: str = 'average',
            manuel_pe: float = None,
            fwd_eps_input: float = None):

    print(f"\n{'='*62}")
    print(f"  ADİL DEĞER HESAPLAYICI — {symbol.upper()}")
    print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  PE Modu: {pe_modu.upper()}")
    print(f"{'='*62}\n")

    # --- TEMEL VERİ ---
    quote = fmp_get("quote", {"symbol": symbol})
    if not quote:
        print("Sembol bulunamadı."); return
    q       = quote[0]
    price   = q['price']
    mktcap  = q['marketCap']
    shares  = mktcap / price

    profile    = fmp_get("profile", {"symbol": symbol})
    sector_str = profile[0].get('sector', '') if profile else ''
    sector_cat = detect_sector(sector_str)

    ratios_ttm = fmp_get("ratios-ttm", {"symbol": symbol})[0]
    metrics_ttm= fmp_get("key-metrics-ttm", {"symbol": symbol})[0]

    eps_ttm = safe(ratios_ttm.get('netIncomePerShareTTM'))
    bvps    = safe(ratios_ttm.get('bookValuePerShareTTM'))
    fcf_ps  = safe(ratios_ttm.get('freeCashFlowPerShareTTM'))
    roe     = safe(metrics_ttm.get('returnOnEquityTTM'))
    ev      = safe(metrics_ttm.get('enterpriseValueTTM'))
    graham_fmp = safe(metrics_ttm.get('grahamNumberTTM'))

    # Bilanço — net borç
    bal   = fmp_get("balance-sheet-statement", {"symbol": symbol, "period": "quarter", "limit": 1})
    b     = bal[0] if bal else {}
    cash  = safe(b.get('cashAndCashEquivalents'), 0) + safe(b.get('shortTermInvestments'), 0)
    nd    = safe(b.get('totalDebt'), 0) - cash  # negatif = net nakit

    # TTM gelir (son 4 çeyrek)
    inc4     = fmp_get("income-statement", {"symbol": symbol, "period": "quarter", "limit": 4}) or []
    ttm_rev  = sum((q.get('revenue')          or 0) for q in inc4)
    ttm_ebit = sum((q.get('operatingIncome')  or 0) for q in inc4)
    ttm_ebitda = sum((q.get('ebitda')         or 0) for q in inc4)

    # FCF büyüme (4 vs 4 çeyrek)
    cf8      = fmp_get("cash-flow-statement", {"symbol": symbol, "period": "quarter", "limit": 8}) or []
    ttm_fcf  = sum((q.get('freeCashFlow') or 0) for q in cf8[:4])
    prev_fcf = sum((q.get('freeCashFlow') or 0) for q in cf8[4:])
    fcf_gr   = min(0.30, max(-0.20, ttm_fcf / prev_fcf - 1.0)) if prev_fcf > 0 else 0.12

    # EPS ve Ciro büyümesi (yıllık)
    inc_ann  = fmp_get("income-statement", {"symbol": symbol, "period": "annual", "limit": 2}) or []
    if len(inc_ann) >= 2 and (inc_ann[1].get('eps') or 0) > 0:
        eps_gr = min(0.30, max(-0.20, (inc_ann[0].get('eps', 0) / inc_ann[1].get('eps', 1)) - 1.0))
    else:
        eps_gr = 0.12
    # Ciro büyümesi — Forward P/S için ayrıca hesapla
    if len(inc_ann) >= 2 and (inc_ann[1].get('revenue') or 0) > 0:
        rev_gr = min(0.35, max(-0.10, (inc_ann[0].get('revenue', 0) / inc_ann[1].get('revenue', 1)) - 1.0))
    else:
        rev_gr = eps_gr * 0.5  # ciro tipik olarak EPS kadar hızlı büyümez

    # 10Y hazine → faize dayalı P/E
    today   = datetime.now().strftime("%Y-%m-%d")
    tr      = fmp_get("treasury-rates", {"from": "2026-04-01", "to": today})
    bond_y  = safe(tr[0].get('year10')) if tr else 4.5
    rate_pe = max(4.0, min(30.0, 100.0 / bond_y))

    # =========================================================
    # 252G TARİHSEL ORANLAR (Pine Script historicalLookback=252)
    # =========================================================
    h = fetch_all_252g_ratios(symbol, shares)

    avg_pe     = h.get('pe')      # 252g TTM P/E
    avg_ps     = h.get('ps')      # 252g P/S
    avg_pfcf   = h.get('pfcf')    # 252g P/FCF
    avg_evebit = h.get('ev_ebit') # 252g EV/EBIT
    avg_ev_ebitda = h.get('ev_ebitda')
    avg_ev_rev = h.get('ev_rev')

    # --- PE ÇARPANI SEÇİMİ ---
    if pe_modu == 'manuel' and manuel_pe:
        kullanilan_pe = manuel_pe
    elif pe_modu == 'rate':
        kullanilan_pe = rate_pe
    else:  # 'average' — 252g dinamik (Pine Script birebir)
        kullanilan_pe = avg_pe if avg_pe else rate_pe

    # --- FORWARD EPS ---
    # FMP Premium analist EPS vermiyor → kullanıcı --fwd-eps ile girebilir
    # Girilmezse: mevcut forward P/E = fiyat / fwd_eps → fwd P/E fair ≈ fiyat (döngüsel)
    # Çözüm: TTM EPS × (1 + eps_gr) kullan ama 252g P/E yerine mevcut fwd P/E (fiyat / fwd_eps)
    if fwd_eps_input:
        fwd_eps = fwd_eps_input
        fwd_pe_mult = price / fwd_eps    # piyasanın mevcut forward P/E'si
        fwd_ps_rev  = ttm_rev * (1 + rev_gr) / shares  # ciro büyümesiyle → daha gerçekçi
    else:
        fwd_eps = eps_ttm * (1 + eps_gr) if eps_ttm else None
        fwd_pe_mult = kullanilan_pe       # analist yoksa tarihsel P/E kullan
        fwd_ps_rev  = ttm_rev * (1 + rev_gr) / shares if ttm_rev else None

    # --- ÖZET ---
    print(f"  Sembol      : {symbol.upper()} | Sektör: {sector_str} ({sector_cat})")
    print(f"  Fiyat       : ${price:.2f} | Piy. Değ.: ${mktcap/1e9:.1f}B | EV: ${ev/1e9:.1f}B")
    print(f"  EPS TTM     : ${eps_ttm:.2f}" if eps_ttm else "  EPS TTM     : N/A")
    print(f"  FCF/Hisse   : ${fcf_ps:.2f}" if fcf_ps else "  FCF/Hisse   : N/A")
    print(f"  BVPS / ROE  : ${bvps:.2f} / {roe*100:.1f}%" if bvps and roe else "")
    print(f"  Net Borç    : ${nd/1e9:.2f}B {'(Net Nakit ✓)' if nd < 0 else ''}")
    print(f"  10Y Hazine  : {bond_y:.2f}%  →  Faize Dayalı F/K: {rate_pe:.1f}x")
    print()
    print(f"  252G TARİHSEL ORANLAR (Pine Script historicalLookback=252):")
    print(f"    P/E: {avg_pe:.1f}x" if avg_pe else "    P/E: N/A", end="  |  ")
    print(f"P/S: {avg_ps:.1f}x" if avg_ps else "P/S: N/A", end="  |  ")
    print(f"P/FCF: {avg_pfcf:.1f}x" if avg_pfcf else "P/FCF: N/A")
    print(f"    EV/EBIT: {avg_evebit:.1f}x" if avg_evebit else "    EV/EBIT: N/A", end="  |  ")
    print(f"EV/EBITDA: {avg_ev_ebitda:.1f}x" if avg_ev_ebitda else "EV/EBITDA: N/A", end="  |  ")
    print(f"EV/Ciro: {avg_ev_rev:.1f}x" if avg_ev_rev else "EV/Ciro: N/A")
    print()
    print(f"  Kullanılan F/K  : {kullanilan_pe:.1f}x ({pe_modu})")
    fwd_kaynak = "analist" if fwd_eps_input else "TTM×büyüme"
    print(f"  Forward EPS     : ${fwd_eps:.2f} ({fwd_kaynak})  |  Fwd P/E çarpanı: {fwd_pe_mult:.1f}x" if fwd_eps else "  Forward EPS     : N/A")
    print(f"  FCF Büyüme      : {fcf_gr*100:.1f}% YoY | EPS Büyüme: {eps_gr*100:.1f}% YoY | Ciro Büyüme: {rev_gr*100:.1f}% YoY")
    print()

    # =========================================================
    # 10 DEĞERLEME METODU
    # =========================================================
    def ev2p(ev_fair):
        return max(0, (ev_fair - nd) / shares)

    metotlar = {}

    # 1. Net Kazanç P/E
    if eps_ttm and eps_ttm > 0:
        metotlar['Net Kazanç P/E'] = eps_ttm * kullanilan_pe

    # 2. ROE Bazlı
    if roe and roe > 0 and bvps:
        metotlar['ROE Bazlı'] = (roe * bvps) * kullanilan_pe

    # 3. EV/EBIT — 252g tarihsel ortalama (otomatik)
    if ttm_ebit > 0 and avg_evebit:
        metotlar['EV/EBIT'] = ev2p(ttm_ebit * avg_evebit)

    # 4. EV/EBITDA — 252g tarihsel ortalama (otomatik)
    if ttm_ebitda > 0 and avg_ev_ebitda:
        metotlar['EV/EBITDA'] = ev2p(ttm_ebitda * avg_ev_ebitda)

    # 5. EV/Ciro — 252g tarihsel ortalama (otomatik)
    if ttm_rev > 0 and avg_ev_rev:
        metotlar['EV/Ciro'] = ev2p(ttm_rev * avg_ev_rev)

    # 6. Forward P/E
    # Analist EPS varsa: mevcut fwd P/E çarpanı kullan (piyasanın fiyatladığı)
    # Yoksa: TTM×büyüme EPS + tarihsel P/E
    if fwd_eps and fwd_eps > 0:
        metotlar['Forward P/E'] = fwd_eps * fwd_pe_mult

    # 7. Forward P/S — 252g tarihsel P/S × ileri ciro/hisse
    if fwd_ps_rev and fwd_ps_rev > 0 and avg_ps:
        metotlar['Forward P/S'] = fwd_ps_rev * avg_ps

    # 8. P/FCF — 252g tarihsel P/FCF
    if fcf_ps and fcf_ps > 0 and avg_pfcf:
        metotlar['P/FCF'] = fcf_ps * avg_pfcf

    # 9. Graham Sayısı
    if eps_ttm and eps_ttm > 0 and bvps and bvps > 0:
        metotlar['Graham Sayısı'] = math.sqrt(22.5 * eps_ttm * bvps)
    elif graham_fmp:
        metotlar['Graham Sayısı'] = graham_fmp

    # 10. DCF
    if ttm_fcf > 0:
        wacc    = bond_y / 100 + 0.05
        dcf_val = calc_dcf(ttm_fcf, fcf_gr, wacc, 0.025, 5, nd, shares)
        if dcf_val:
            metotlar['DCF'] = dcf_val

    # =========================================================
    # SEKTÖR AĞIRLIKLI TOPLAM
    # =========================================================
    metot_sirasi = ['Net Kazanç P/E', 'ROE Bazlı', 'EV/EBIT', 'EV/EBITDA', 'EV/Ciro',
                    'Forward P/E', 'Forward P/S', 'P/FCF', 'Graham Sayısı', 'DCF']
    agirliklar   = SECTOR_WEIGHTS.get(sector_cat, SECTOR_WEIGHTS['other'])

    print(f"  {'─'*62}")
    print(f"  {'METOT':<18} {'ADİL DEĞER':>12} {'FARK%':>8} {'AĞ%':>5}  YORUM")
    print(f"  {'─'*62}")

    ws, tw = 0.0, 0.0
    tum_deger = []

    for metot, agirlik in zip(metot_sirasi, agirliklar):
        val = metotlar.get(metot)
        if val and val > 0:
            diff  = (price / val - 1) * 100
            yorum = "↑ PAHALI" if diff > 20 else "↓ UCUZ " if diff < -20 else "≈ ADİL "
            print(f"  {metot:<18} ${val:>10.2f} {diff:>+7.1f}% {agirlik*100:>4.0f}%  {yorum}")
            tum_deger.append(val)
            if agirlik > 0:
                ws += val * agirlik; tw += agirlik
        else:
            print(f"  {metot:<18} {'N/A':>12} {'':>8} {agirlik*100:>4.0f}%")

    print(f"  {'─'*62}")

    if tw > 0 and tum_deger:
        adil  = ws / tw
        fark  = (price / adil - 1) * 100
        durum = "PAHALI 🔴" if fark > 20 else "UCUZ 🟢" if fark < -20 else "ADİL 🟡"

        ort = sum(tum_deger) / len(tum_deger)
        std = math.sqrt(sum((v - ort)**2 for v in tum_deger) / len(tum_deger))
        cv  = abs(std / ort) * 100 if ort else 100
        guven = max(0, min(100, round(100 - cv)))

        print(f"\n  {'ADİL DEĞER (Ağırlıklı):':<26} ${adil:>10.2f}")
        print(f"  {'Güncel Fiyat:':<26} ${price:>10.2f}")
        print(f"  {'Fark:':<26} {fark:>+10.1f}%  →  {durum}")
        print(f"  {'Güven Skoru:':<26} {guven}/100")
        print(f"\n  Bantlar:  %20 Prim → ${adil*1.2:.2f} | %20 İskonto → ${adil*0.8:.2f}")
        if graham_fmp:
            print(f"  Graham Sayısı (FMP): ${graham_fmp:.2f}")
        if safe(fmp_get("price-target-summary", {"symbol": symbol})[0].get('lastQuarterAvgPriceTarget')):
            pt = fmp_get("price-target-summary", {"symbol": symbol})[0]
            print(f"  Analist Fiyat Hedefi (son çeyrek): ${pt['lastQuarterAvgPriceTarget']:.2f}")

    print(f"\n  {'─'*62}")
    print(f"  Sektör: {sector_cat} ağırlıkları  |  252g otomatik EV + P oranları")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adil Değer Hesaplayıcı — Pine Script v3.5.2 Python uyarlaması")
    parser.add_argument("symbol",          help="Hisse sembolü (ör. AMD, NVDA, AAPL)")
    parser.add_argument("--pe-modu",       default="average",
                        choices=["rate", "manuel", "average"],
                        help="F/K kaynağı: average (252g dinamik, varsayılan) | rate (faize dayalı) | manuel")
    parser.add_argument("--manuel-pe",     type=float, help="Manuel F/K değeri (--pe-modu manuel ile)")
    parser.add_argument("--fwd-eps",       type=float,
                        help="Forward EPS — analist konsensüsü (ör. 5.00). "
                             "Girilmezse TTM×büyüme kullanılır ve mevcut piyasa fwd P/E'si esas alınır.")
    args = parser.parse_args()
    hesapla(
        symbol       = args.symbol,
        pe_modu      = args.pe_modu,
        manuel_pe    = args.manuel_pe,
        fwd_eps_input= args.fwd_eps,
    )
