"""
Adil Değer Hesaplayıcı — FMP API ile
Pine Script v3.5.2 mantığını Python'a uyarlar.

Kullanım:
  python3 adil_deger_calculator.py AMD
  python3 adil_deger_calculator.py NVDA --pe-modu rate
  python3 adil_deger_calculator.py MSFT --pe-modu manuel --manuel-pe 22
"""

import requests, math, sys, argparse
from datetime import datetime

# -------------------------------------------------------------------------
FMP_API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE    = "https://financialmodelingprep.com/stable"
# -------------------------------------------------------------------------

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
    if val is None: return default
    if isinstance(val, (int, float)) and not math.isnan(val): return val
    return default

def avg(lst):
    lst = [x for x in lst if x is not None and isinstance(x, (int, float)) and not math.isnan(x) and x > 0]
    return sum(lst) / len(lst) if lst else None

# =========================================================================
# SEKTÖR TESPİTİ VE AĞIRLIKLARI (Pine Script mantığı)
# =========================================================================
SECTOR_WEIGHTS = {
    # [PE, ROE, EvEbit, EvEbitda, EvRev, FwdPE, FwdPS, FCF, Graham, DCF]
    'tech':       [0.10, 0.05, 0.10, 0.13, 0.18, 0.13, 0.18, 0.05, 0.00, 0.08],
    'financial':  [0.18, 0.27, 0.00, 0.00, 0.00, 0.13, 0.00, 0.10, 0.22, 0.10],
    'industrial': [0.10, 0.05, 0.18, 0.18, 0.05, 0.08, 0.05, 0.13, 0.08, 0.10],
    'consumer':   [0.13, 0.10, 0.13, 0.13, 0.10, 0.10, 0.10, 0.10, 0.05, 0.06],
    'energy':     [0.10, 0.10, 0.18, 0.20, 0.05, 0.05, 0.00, 0.17, 0.05, 0.10],
    'healthcare': [0.13, 0.10, 0.10, 0.13, 0.10, 0.13, 0.10, 0.10, 0.05, 0.06],
    'utilities':  [0.13, 0.08, 0.13, 0.18, 0.05, 0.08, 0.00, 0.13, 0.10, 0.12],
    'other':      [0.12, 0.12, 0.12, 0.12, 0.10, 0.12, 0.10, 0.10, 0.05, 0.05],
}

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
# DCF HESAPLAMASI
# =========================================================================
def calc_dcf(base_fcf, growth_rate, wacc, terminal_growth, years, net_debt, shares):
    if not all([base_fcf, base_fcf > 0, shares > 0, wacc > terminal_growth]):
        return None
    total_pv, cur_cf = 0.0, base_fcf
    for yr in range(1, years + 1):
        cur_cf  *= (1 + growth_rate)
        total_pv += cur_cf / (1 + wacc) ** yr
    terminal_pv = (cur_cf * (1 + terminal_growth) / (wacc - terminal_growth)) / (1 + wacc) ** years
    equity_val  = total_pv + terminal_pv - net_debt
    return max(0, equity_val / shares) if equity_val > 0 else None

# =========================================================================
# ANA HESAPLAMA
# =========================================================================

def fetch_avg_pe_252(symbol, shares, fmp_get_fn):
    """Pine Script historicalLookback=252 mantığı: 252 günlük dinamik TTM P/E ortalaması."""
    from datetime import datetime, timedelta
    today    = datetime.now().strftime("%Y-%m-%d")
    from_dt  = (datetime.now() - timedelta(days=380)).strftime("%Y-%m-%d")
    prices   = fmp_get_fn("historical-price-eod/light", {"symbol": symbol, "from": from_dt, "to": today})
    inc_q    = fmp_get_fn("income-statement", {"symbol": symbol, "period": "quarter", "limit": 8})
    if not prices or not inc_q or len(inc_q) < 4:
        return None
    # TTM EPS per quarter end date
    ttm_eps_map = {}
    for i in range(len(inc_q) - 3):
        ttm_ni = sum((q.get("netIncome") or 0) for q in inc_q[i:i+4])
        ttm_eps_map[inc_q[i]["date"]] = ttm_ni / shares
    sorted_eps_dates = sorted(ttm_eps_map.keys(), reverse=True)
    def eps_for(dt):
        for d in sorted_eps_dates:
            if dt >= d:
                return ttm_eps_map[d]
        return list(ttm_eps_map.values())[-1]
    # 252g P/E
    pe_vals = []
    for p in prices[:252]:
        eps = eps_for(p["date"])
        if eps and eps > 0:
            pe_vals.append(p["price"] / eps)
    return sum(pe_vals) / len(pe_vals) if pe_vals else None

def hesapla(symbol: str, pe_modu: str = 'rate', manuel_pe: float = None, fwd_eps_input: float = None,
            ev_ebit_hedef: float = 15.0, ev_ebitda_hedef: float = 20.0,
            ev_rev_hedef: float = 3.0):

    print(f"\n{'='*62}")
    print(f"  ADİL DEĞER HESAPLAYICI — {symbol.upper()}")
    print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  PE Modu: {pe_modu.upper()}")
    print(f"{'='*62}\n")

    # ----- VERİ ÇEKME -----
    print("Veriler çekiliyor...")

    quote    = fmp_get("quote", {"symbol": symbol})
    if not quote:
        print("Sembol bulunamadı."); return
    q        = quote[0]
    price    = q['price']
    mktcap   = q['marketCap']
    shares   = mktcap / price

    profile  = fmp_get("profile", {"symbol": symbol})
    sector   = profile[0].get('sector', '') if profile else ''
    sector_cat = detect_sector(sector)

    rtm      = fmp_get("ratios-ttm", {"symbol": symbol})[0]
    mttm     = fmp_get("key-metrics-ttm", {"symbol": symbol})[0]

    # Temel TTM metrikler
    eps_ttm  = safe(rtm.get('netIncomePerShareTTM'))
    bvps     = safe(rtm.get('bookValuePerShareTTM'))
    fcf_ps   = safe(rtm.get('freeCashFlowPerShareTTM'))
    roe      = safe(mttm.get('returnOnEquityTTM'))
    ev       = safe(mttm.get('enterpriseValueTTM'))

    # Bilanço — net borç
    bal      = fmp_get("balance-sheet-statement", {"symbol": symbol, "period": "quarter", "limit": 1})
    b        = bal[0] if bal else {}
    cash     = safe(b.get('cashAndCashEquivalents'), 0) + safe(b.get('shortTermInvestments'), 0)
    net_debt = safe(b.get('totalDebt'), 0) - cash

    # TTM gelir tablosu (son 4 çeyrek toplamı)
    inc4     = fmp_get("income-statement", {"symbol": symbol, "period": "quarter", "limit": 4}) or []
    ttm_rev  = sum((q.get('revenue') or 0) for q in inc4)
    ttm_ebit = sum((q.get('operatingIncome') or 0) for q in inc4)
    ttm_ebitda = sum((q.get('ebitda') or 0) for q in inc4)

    # TTM FCF (son 4 çeyrek) ve büyüme
    cf8      = fmp_get("cash-flow-statement", {"symbol": symbol, "period": "quarter", "limit": 8}) or []
    ttm_fcf  = sum((q.get('freeCashFlow') or 0) for q in cf8[:4])
    prev_fcf = sum((q.get('freeCashFlow') or 0) for q in cf8[4:])
    fcf_growth = min(0.30, max(-0.20, ttm_fcf / prev_fcf - 1.0)) if prev_fcf > 0 else 0.10

    # EPS büyüme (son 2 yıl)
    inc_ann  = fmp_get("income-statement", {"symbol": symbol, "period": "annual", "limit": 2}) or []
    if len(inc_ann) >= 2 and (inc_ann[1].get('eps') or 0) > 0:
        eps_growth = min(0.30, max(-0.20, (inc_ann[0].get('eps', 0) / inc_ann[1].get('eps', 1)) - 1.0))
    else:
        eps_growth = 0.12

    # Hazine faizi (10Y)
    today    = datetime.now().strftime("%Y-%m-%d")
    tr       = fmp_get("treasury-rates", {"from": "2026-04-01", "to": today})
    bond_y   = safe(tr[0].get('year10')) if tr else 4.5
    rate_pe  = max(4.0, min(30.0, 100.0 / bond_y))

    # ----- PE ÇARPANI SEÇİMİ -----
    if pe_modu == 'manuel' and manuel_pe:
        kullanilan_pe = manuel_pe
    elif pe_modu == 'rate':
        kullanilan_pe = rate_pe
    else:  # 'average' — 252 günlük dinamik TTM P/E ortalaması (Pine Script mantığı)
        dinamik_pe = fetch_avg_pe_252(symbol, shares, fmp_get)
        kullanilan_pe = dinamik_pe if dinamik_pe else rate_pe

    # ----- ÖZET BİLGİ -----
    print(f"  Sembol     : {symbol.upper()} | Sektör: {sector} ({sector_cat})")
    print(f"  Fiyat      : ${price:.2f} | Piy. Değ.: ${mktcap/1e9:.1f}B | EV: ${ev/1e9:.1f}B")
    print(f"  EPS TTM    : ${eps_ttm:.2f}" if eps_ttm else "  EPS TTM    : N/A")
    print(f"  FCF/Hisse  : ${fcf_ps:.2f}" if fcf_ps else "  FCF/Hisse  : N/A")
    print(f"  BVPS       : ${bvps:.2f}" if bvps else "  BVPS       : N/A")
    print(f"  ROE        : {roe*100:.2f}%" if roe else "  ROE        : N/A")
    print(f"  10Y Hazine : {bond_y:.2f}%  →  Faize Dayalı F/K: {rate_pe:.1f}x")
    print(f"  Kullanılan F/K: {kullanilan_pe:.1f}x ({pe_modu})")
    print(f"  Net Borç   : ${net_debt/1e9:.2f}B {'(Net Nakit ✓)' if net_debt < 0 else ''}")
    kullanilan_fwd_eps = fwd_eps_input if fwd_eps_input else (eps_ttm * (1 + eps_growth) if eps_ttm else None)
    print(f"  Forward EPS: ${kullanilan_fwd_eps:.2f}" + (" (analist)" if fwd_eps_input else " (TTM×büyüme)") if kullanilan_fwd_eps else "")
    print(f"  FCF Büyüme : {fcf_growth*100:.1f}% YoY | EPS Büyüme: {eps_growth*100:.1f}% YoY")
    print()

    # =========================================================================
    # 10 DEĞERLEME METODU
    # =========================================================================
    metotlar = {}

    # 1. Net Kazanç P/E
    if eps_ttm and eps_ttm > 0:
        metotlar['Net Kazanç P/E'] = eps_ttm * kullanilan_pe

    # 2. ROE bazlı
    if roe and roe > 0 and bvps:
        metotlar['ROE Bazlı'] = (roe * bvps) * kullanilan_pe

    # 3. EV/EBIT — hedef çarpan kullanıcı tarafından ayarlanabilir
    if ttm_ebit > 0:
        ev_fair = ttm_ebit * ev_ebit_hedef
        metotlar['EV/EBIT'] = max(0, (ev_fair - net_debt) / shares)

    # 4. EV/EBITDA — ayrı hedef çarpan
    if ttm_ebitda > 0:
        ev_fair = ttm_ebitda * ev_ebitda_hedef
        metotlar['EV/EBITDA'] = max(0, (ev_fair - net_debt) / shares)

    # 5. EV/Ciro
    if ttm_rev > 0:
        ev_fair = ttm_rev * ev_rev_hedef
        metotlar['EV/Ciro'] = max(0, (ev_fair - net_debt) / shares)

    # 6. Forward P/E — manuel analist EPS varsa onu kullan, yoksa TTM × büyüme
    if eps_ttm and eps_ttm > 0:
        fwd_eps = fwd_eps_input if fwd_eps_input else (eps_ttm * (1 + eps_growth))
        metotlar['Forward P/E'] = fwd_eps * kullanilan_pe

    # 7. Forward P/S (TTM ciro × büyüme ile tahmin)
    if ttm_rev > 0:
        ps_ttm = price / (ttm_rev / shares)
        fwd_ps = min(ps_ttm, 10.0)
        # fwd_eps_input varsa büyüme oranını oradan türet
        rev_growth = (fwd_eps_input / eps_ttm - 1) if (fwd_eps_input and eps_ttm) else eps_growth
        fwd_rev_ps = (ttm_rev * (1 + rev_growth)) / shares
        metotlar['Forward P/S'] = fwd_rev_ps * fwd_ps

    # 8. P/FCF (Serbest Nakit Akışı)
    if fcf_ps and fcf_ps > 0:
        pfcf_hedef = min(40.0, kullanilan_pe * 1.5)  # PE'nin 1.5x'i, max 40x
        metotlar['P/SNA (P/FCF)'] = fcf_ps * pfcf_hedef

    # 9. Graham Sayısı — √(22.5 × EPS × BVPS)
    graham_fmp = safe(mttm.get('grahamNumberTTM'))
    if eps_ttm and eps_ttm > 0 and bvps and bvps > 0:
        graham_calc = math.sqrt(22.5 * eps_ttm * bvps)
        metotlar['Graham Sayısı'] = graham_calc
    elif graham_fmp:
        metotlar['Graham Sayısı'] = graham_fmp

    # 10. DCF (İndirgenmiş Nakit Akışı)
    if ttm_fcf > 0:
        wacc = bond_y / 100 + 0.05  # risk-free + ERP %5
        dcf_val = calc_dcf(ttm_fcf, fcf_growth, wacc, 0.025, 5, net_debt, shares)
        if dcf_val:
            metotlar['DCF'] = dcf_val

    # =========================================================================
    # SEKTÖR AĞIRLIKLI TOPLAM
    # =========================================================================
    metot_sirasi = ['Net Kazanç P/E', 'ROE Bazlı', 'EV/EBIT', 'EV/EBITDA', 'EV/Ciro',
                    'Forward P/E', 'Forward P/S', 'P/SNA (P/FCF)', 'Graham Sayısı', 'DCF']
    agirliklar   = SECTOR_WEIGHTS.get(sector_cat, SECTOR_WEIGHTS['other'])

    print(f"  {'─'*62}")
    print(f"  {'METOT':<22} {'ADİL DEĞER':>12} {'FARK%':>8} {'AĞ%':>5}  YORUM")
    print(f"  {'─'*62}")

    weighted_sum  = 0.0
    total_weight  = 0.0
    tum_degerler  = []

    for metot, agirlik in zip(metot_sirasi, agirliklar):
        val = metotlar.get(metot)
        if val and val > 0:
            diff = (price / val - 1) * 100
            yorum = "↑ PAHALI" if diff > 20 else "↓ UCUZ " if diff < -20 else "≈ ADİL "
            print(f"  {metot:<22} ${val:>10.2f} {diff:>+7.1f}% {agirlik*100:>4.0f}%  {yorum}")
            tum_degerler.append(val)
            if agirlik > 0:
                weighted_sum += val * agirlik
                total_weight += agirlik
        else:
            print(f"  {metot:<22} {'N/A':>12} {'':>8} {agirlik*100:>4.0f}%")

    print(f"  {'─'*62}")

    if total_weight > 0 and tum_degerler:
        adil_deger = weighted_sum / total_weight
        fark_pct   = (price / adil_deger - 1) * 100
        durum      = "PAHALI 🔴" if fark_pct > 20 else "UCUZ 🟢" if fark_pct < -20 else "ADİL 🟡"

        # Güven skoru
        ort = sum(tum_degerler) / len(tum_degerler)
        std = math.sqrt(sum((v - ort)**2 for v in tum_degerler) / len(tum_degerler))
        cv  = abs(std / ort) * 100 if ort else 100
        guven = max(0, min(100, round(100 - cv)))

        print(f"\n  {'ADİL DEĞER (Ağırlıklı):':<26} ${adil_deger:>10.2f}")
        print(f"  {'Güncel Fiyat:':<26} ${price:>10.2f}")
        print(f"  {'Fark:':<26} {fark_pct:>+10.1f}%  →  {durum}")
        print(f"  {'Güven Skoru:':<26} {guven}/100")
        print(f"\n  Bantlar:  %20 Prim → ${adil_deger*1.2:.2f} | %20 İskonto → ${adil_deger*0.8:.2f}")
        if graham_fmp:
            print(f"  Graham Sayısı (FMP doğrulama): ${graham_fmp:.2f}")

    print(f"\n  {'─'*62}")
    print(f"  NOT: EV/EBIT hedef={ev_ebit_hedef}x | EV/EBITDA hedef={ev_ebitda_hedef}x | EV/Ciro={ev_rev_hedef}x")
    print(f"  Sektör: {sector_cat} ağırlıkları kullanıldı.")
    print(f"{'='*62}\n")

# =========================================================================
# CLI
# =========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adil Değer Hesaplayıcı")
    parser.add_argument("symbol", help="Hisse sembolü (ör. AMD, NVDA)")
    parser.add_argument("--pe-modu", default="rate", choices=["rate", "manuel", "average"],
                        help="F/K kaynağı: rate (faize dayalı) | manuel | average (TTM cap'li)")
    parser.add_argument("--manuel-pe", type=float, help="Manuel F/K değeri")
    parser.add_argument("--fwd-eps",    type=float, help="Manuel analist Forward EPS (ör. 5.00)")
    parser.add_argument("--ev-ebit",   type=float, default=15.0, help="Hedef EV/EBIT çarpanı")
    parser.add_argument("--ev-ebitda", type=float, default=20.0, help="Hedef EV/EBITDA çarpanı")
    parser.add_argument("--ev-rev",    type=float, default=3.0,  help="Hedef EV/Ciro çarpanı")
    args = parser.parse_args()

    hesapla(
        symbol          = args.symbol,
        pe_modu         = args.pe_modu,
        manuel_pe       = args.manuel_pe,
        fwd_eps_input   = args.fwd_eps,
        ev_ebit_hedef   = args.ev_ebit,
        ev_ebitda_hedef = args.ev_ebitda,
        ev_rev_hedef    = args.ev_rev,
    )
