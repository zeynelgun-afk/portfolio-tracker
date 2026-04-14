"""
Adil Değer Hesaplayıcı v2.0 — FMP API + Yahoo Finance
Pine Script v3.5.2 Python uyarlaması. Tamamen otonom çalışır.

Yenilikler v2.0:
- Forward EPS otomatik türetme (FMP forwardPEG × büyüme)
- 11. Metot: PEG/Forward PEG değerleme
- Multi-stage DCF (3 aşamalı, gerçekçi büyüme)
- Hisse tipi tespiti (büyüme/temettü/değer/döngüsel)
- Peer median sanity check + prim uyarısı
- Batch modu: birden fazla sembol
- --portfolio ile JSON portföy okuma
- --report ile markdown çıktı
- --telegram ile Telegram bildirimi

Kullanım:
  python3 scripts/adil_deger_calculator.py AMD
  python3 scripts/adil_deger_calculator.py AMD MU PLTR NVDA
  python3 scripts/adil_deger_calculator.py --portfolio balanced
  python3 scripts/adil_deger_calculator.py AMD --report --telegram
"""

import requests, math, argparse, json, os, sys
from datetime import datetime, timedelta

FMP_API_KEY  = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE     = "https://financialmodelingprep.com/stable"
TG_TOKEN     = "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI"
TG_CHAT      = "-1003827034395"
REPO_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECTOR_WEIGHTS = {
    # [PE, ROE, EvEbit, EvEbitda, EvRev, FwdPE, FwdPS, FCF, Graham, DCF, PEG]
    'tech':       [0.09, 0.04, 0.09, 0.11, 0.16, 0.11, 0.16, 0.04, 0.00, 0.07, 0.13],
    'financial':  [0.17, 0.25, 0.00, 0.00, 0.00, 0.12, 0.00, 0.09, 0.20, 0.09, 0.08],
    'industrial': [0.09, 0.05, 0.16, 0.16, 0.04, 0.07, 0.04, 0.12, 0.07, 0.09, 0.11],
    'consumer':   [0.11, 0.09, 0.11, 0.11, 0.09, 0.09, 0.09, 0.09, 0.04, 0.05, 0.13],
    'energy':     [0.09, 0.09, 0.17, 0.19, 0.04, 0.04, 0.00, 0.16, 0.04, 0.09, 0.09],
    'healthcare': [0.11, 0.09, 0.09, 0.11, 0.09, 0.11, 0.09, 0.09, 0.04, 0.05, 0.13],
    'utilities':  [0.11, 0.07, 0.11, 0.16, 0.04, 0.07, 0.00, 0.11, 0.09, 0.11, 0.13],
    'other':      [0.10, 0.10, 0.10, 0.10, 0.09, 0.10, 0.09, 0.09, 0.04, 0.05, 0.14],
}

# Hisse tipi için P/E eşikleri
BUYUME_PE_ESIK    = 150   # üstü → büyüme/narratif uyarısı
TEMETTU_YIELD_MIN = 3.0   # % üstü → temettü modu
PEER_PRIM_ESIK    = 3.0   # peer ortalamasının 3x üstü → prim uyarısı


# ─── YARDIMCI FONKSİYONLAR ─────────────────────────────────────────────────

def fmp_get(endpoint, params=None):
    if params is None: params = {}
    params['apikey'] = FMP_API_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def safe(val, default=None):
    if val is None: return default
    if isinstance(val, (int, float)) and not math.isnan(val): return val
    return default

def detect_sector(s):
    s = (s or '').lower()
    if any(x in s for x in ['tech','software','semiconductor','electronic','communication']): return 'tech'
    if any(x in s for x in ['finance','bank','insurance']): return 'financial'
    if any(x in s for x in ['health','pharma','biotech','medical']): return 'healthcare'
    if any(x in s for x in ['energy','oil','gas','mineral']): return 'energy'
    if any(x in s for x in ['utilit']): return 'utilities'
    if any(x in s for x in ['manufactur','industrial','transport','machinery']): return 'industrial'
    if any(x in s for x in ['retail','consumer','food','beverage','service']): return 'consumer'
    return 'other'

def tg_send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={'chat_id': TG_CHAT, 'text': msg, 'parse_mode': 'HTML'},
            timeout=10
        )
    except: pass


# ─── 252G TARİHSEL ORAN HESAPLAMA ──────────────────────────────────────────

def fetch_all_252g_ratios(symbol, shares):
    today   = datetime.now().strftime("%Y-%m-%d")
    from_dt = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
    print("  252g oranlar...", end=" ", flush=True)

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

    nd_map = {}
    for b in bal_q:
        cash = safe(b.get('cashAndCashEquivalents'), 0) + safe(b.get('shortTermInvestments'), 0)
        nd_map[b['date']] = safe(b.get('totalDebt'), 0) - cash

    ttm_map = {}
    min_q = min(len(inc_q), len(cf_q))
    for i in range(min_q - 3):
        gi, gc = inc_q[i:i+4], cf_q[i:i+4]
        ttm_map[inc_q[i]['date']] = {
            'ni':     sum((q.get('netIncome')       or 0) for q in gi),
            'ebit':   sum((q.get('operatingIncome') or 0) for q in gi),
            'ebitda': sum((q.get('ebitda')          or 0) for q in gi),
            'rev':    sum((q.get('revenue')         or 0) for q in gi),
            'fcf':    sum((q.get('freeCashFlow')    or 0) for q in gc),
        }

    s_nd  = sorted(nd_map.keys(),  reverse=True)
    s_ttm = sorted(ttm_map.keys(), reverse=True)

    def gnd(dt):
        for d in s_nd:
            if dt >= d: return nd_map[d]
        return nd_map[s_nd[-1]]

    def gttm(dt):
        for d in s_ttm:
            if dt >= d: return ttm_map[d]
        return ttm_map[s_ttm[-1]]

    vals = {k: [] for k in ['pe','ps','pfcf','ev_ebit','ev_ebitda','ev_rev']}
    for row in mktcap_hist[:252]:
        day    = row['date']
        mktcap = row['marketCap']
        nd     = gnd(day)
        ttm    = gttm(day)
        ev     = mktcap + nd
        pd_    = mktcap / shares if shares > 0 else 0

        eps_d = ttm['ni']  / shares if shares > 0 else 0
        rps_d = ttm['rev'] / shares if shares > 0 else 0
        fps_d = ttm['fcf'] / shares if shares > 0 else 0

        if eps_d   > 0 and pd_ > 0: vals['pe'].append(pd_   / eps_d)
        if rps_d   > 0 and pd_ > 0: vals['ps'].append(pd_   / rps_d)
        if fps_d   > 0 and pd_ > 0: vals['pfcf'].append(pd_ / fps_d)
        if ttm['ebit']   > 0:       vals['ev_ebit'].append(ev   / ttm['ebit'])
        if ttm['ebitda'] > 0:       vals['ev_ebitda'].append(ev / ttm['ebitda'])
        if ttm['rev']    > 0:       vals['ev_rev'].append(ev   / ttm['rev'])

    result = {k: (sum(v)/len(v) if v else None) for k, v in vals.items()}
    print(f"{len(mktcap_hist[:252])} gün tamamlandı.")
    return result


# ─── MULTI-STAGE DCF ────────────────────────────────────────────────────────

def calc_dcf_multistage(base_fcf, growth_rate, wacc, terminal_growth, net_debt, shares):
    """
    3 aşamalı DCF:
    Aşama 1: 3 yıl × growth_rate (cap %60)
    Aşama 2: 2 yıl × ortalama(growth_rate, %15) normalleşme
    Terminal: terminal_growth
    """
    if not (base_fcf and base_fcf > 0 and shares > 0 and wacc > terminal_growth):
        return None

    g1 = min(growth_rate, 0.60)        # aşama 1: gerçek büyüme
    g2 = (g1 + 0.15) / 2              # aşama 2: normalleşme
    total_pv, cur_cf = 0.0, base_fcf

    for yr in range(1, 4):             # 3 yıl yüksek büyüme
        cur_cf   *= (1 + g1)
        total_pv += cur_cf / (1 + wacc) ** yr

    for yr in range(4, 6):             # 2 yıl normalleşme
        cur_cf   *= (1 + g2)
        total_pv += cur_cf / (1 + wacc) ** yr

    terminal_pv = (cur_cf * (1 + terminal_growth) / (wacc - terminal_growth)) / (1 + wacc) ** 5
    equity_val  = total_pv + terminal_pv - net_debt
    return max(0, equity_val / shares) if equity_val > 0 else None


# ─── AKILlI PEER SEÇİCİ ────────────────────────────────────────────────────

# Brüt marj yüksek büyüme/SaaS için küratörlü evren
SAAS_EVREN = [
    'DDOG','SNOW','NET','ZS','CRWD','NOW','APP','AXON','GTLB',
    'SMAR','MNDY','HUBS','MDB','CFLT','KVYO','ASAN','TWLO','TTD',
    'OKTA','DOCU','ZOOM','ESTC','PYCR','SPSC','VEEV','WDAY','ADSK',
]

def _get_peer_profile(sym):
    """Tek peer için büyüme profili çeker."""
    try:
        inc = fmp_get("income-statement", {"symbol": sym, "period": "annual", "limit": 2})
        m   = fmp_get("key-metrics-ttm",  {"symbol": sym})
        r   = fmp_get("ratios-ttm",        {"symbol": sym})
        cf  = fmp_get("cash-flow-statement", {"symbol": sym, "period": "annual", "limit": 1})
        if not (inc and len(inc) >= 2 and m and r): return None
        rev_now  = inc[0].get("revenue") or 0
        rev_prev = inc[1].get("revenue") or 1
        fcf_m = 0
        if cf and rev_now > 0:
            fcf_m = ((cf[0].get("freeCashFlow") or 0) / rev_now) * 100
        return {
            "sym":    sym,
            "rev_gr": (rev_now / rev_prev - 1) * 100,
            "gp_m":   (r[0].get("grossProfitMarginTTM") or 0) * 100,
            "fcf_m":  fcf_m,
            "ev_rev": m[0].get("evToSalesTTM"),
            "mktcap": (m[0].get("marketCap") or 0) / 1e9,
            "rev_ttm": rev_now,
        }
    except: return None

def _similarity(subj, tgt):
    """Düşük skor = daha benzer. Brüt marj + büyüme ağırlıklı."""
    if not tgt or tgt.get("rev_gr") is None or tgt.get("gp_m") is None:
        return float("inf")
    rev_diff = abs(subj["rev_gr"] - tgt["rev_gr"]) / max(abs(subj["rev_gr"]), 1)
    gp_diff  = abs(subj["gp_m"]  - tgt["gp_m"])   / max(abs(subj["gp_m"]),  1)
    mc_diff  = abs(math.log(subj["mktcap"]+1) - math.log(tgt["mktcap"]+1)) / max(math.log(subj["mktcap"]+1), 1)
    return 0.50*rev_diff + 0.40*gp_diff + 0.10*mc_diff

def fetch_smart_peer_evrev(symbol, subj_profile, hisse_tipi):
    """
    Akıllı peer seçici:
    - Büyüme/narratif hisseler → brüt marj + büyüme benzerliği ile SaaS evreninden seç
    - Diğerleri → FMP peer listesini kullan, basit filtre
    Döndürür: (medyan_evrev, growth_adj_evrev, peer_listesi, rof40_skoru)
    """
    # Rule of 40 skoru her zaman hesapla
    rof40 = (subj_profile.get("rev_gr") or 0) + (subj_profile.get("fcf_m") or 0)

    if hisse_tipi == "buyume":
        # Büyüme hissesi → SaaS evreninden benzer profil bul
        kandidatlar = []
        for sym in SAAS_EVREN:
            if sym == symbol: continue
            p = _get_peer_profile(sym)
            if not p: continue
            if (p.get("gp_m") or 0) < 55: continue      # brüt marj filtresi
            if (p.get("mktcap") or 0) < 5: continue      # min. $5B market cap
            score = _similarity(subj_profile, p)
            if p.get("ev_rev") and score < 0.65:
                kandidatlar.append({**p, "score": score})

        kandidatlar.sort(key=lambda x: x["score"])
        secilen = kandidatlar[:8]
        if not secilen: return None, None, [], rof40

        evrev_list = sorted([p["ev_rev"] for p in secilen])
        raw_median = evrev_list[len(evrev_list)//2]

        # Büyüme düzeltmesi (kendi büyümesi / peer ortalama büyüme, max 3x)
        peer_avg_gr = sum(p["rev_gr"] for p in secilen) / len(secilen)
        subj_gr     = subj_profile.get("rev_gr") or peer_avg_gr
        growth_adj  = min(subj_gr / max(peer_avg_gr, 1), 3.0)
        adj_median  = raw_median * growth_adj

        # Rule of 40 bazlı EV/Rev (peer medyan katsayısı × konu RoF40)
        peer_rof40s = [(p["rev_gr"] + p.get("fcf_m", 0)) for p in secilen]
        peer_evrevs = [p["ev_rev"] for p in secilen]
        k_list = [ev/rof for ev, rof in zip(peer_evrevs, peer_rof40s) if rof > 0]
        k_list.sort()
        k_median    = k_list[len(k_list)//2] if k_list else 0.2
        rof40_evrev = k_median * rof40

        peer_syms = [p["sym"] for p in secilen]
        return raw_median, adj_median, peer_syms, rof40, rof40_evrev
    else:
        # Normal hisse → FMP peer listesi, basit filtre
        fmp_peers = fmp_get("stock-peers", {"symbol": symbol})
        if not fmp_peers: return None, None, [], rof40, None
        peer_syms = [p["symbol"] for p in fmp_peers[:8]]
        evrev_list = []
        for sym in peer_syms:
            try:
                m = fmp_get("key-metrics-ttm", {"symbol": sym})
                if m:
                    v = m[0].get("evToSalesTTM")
                    if v and 0 < v < 200:
                        evrev_list.append(v)
            except: pass
        evrev_list.sort()
        median = evrev_list[len(evrev_list)//2] if evrev_list else None
        return median, median, peer_syms, rof40, None


# ─── FORWARD EPS OTOMATİK TÜRETİM ─────────────────────────────────────────

def derive_fwd_eps(price, ratios_ttm, eps_ttm, eps_gr):
    """
    FMP forwardPriceToEarningsGrowthRatioTTM (forward PEG) kullanarak
    forward EPS türetir. Dış API gerektirmez.

    Formula: forward_pe = forward_peg × growth_pct
             fwd_eps    = price / forward_pe
    """
    fwd_peg = safe(ratios_ttm.get('forwardPriceToEarningsGrowthRatioTTM'))
    if fwd_peg and fwd_peg > 0 and eps_gr and eps_gr > 0:
        growth_pct = eps_gr * 100      # 0.30 → 30
        fwd_pe     = fwd_peg * growth_pct
        if fwd_pe > 0:
            return price / fwd_pe, 'fwd_peg_türetme'

    # Fallback: TTM × büyüme
    if eps_ttm and eps_ttm > 0:
        return eps_ttm * (1 + eps_gr), 'ttm_büyüme'

    return None, None


# ─── ANA HESAPLAMA ──────────────────────────────────────────────────────────

def hesapla(symbol, pe_modu='average', manuel_pe=None, fwd_eps_input=None, sessiz=False):
    """Tek hisse için adil değer hesaplar. Dict sonuç döndürür."""

    if not sessiz:
        print(f"\n{'='*62}")
        print(f"  ADİL DEĞER v2.0 — {symbol.upper()}")
        print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        print(f"{'='*62}\n")

    # ── TEMEL VERİ ──────────────────────────────────────────────
    quote = fmp_get("quote", {"symbol": symbol})
    if not quote: return None
    q       = quote[0]
    price   = q['price']
    mktcap  = q['marketCap']
    shares  = mktcap / price

    profile    = fmp_get("profile", {"symbol": symbol})
    sector_str = profile[0].get('sector', '') if profile else ''
    sector_cat = detect_sector(sector_str)

    rtm  = fmp_get("ratios-ttm",      {"symbol": symbol})[0]
    mttm = fmp_get("key-metrics-ttm", {"symbol": symbol})[0]

    eps_ttm = safe(rtm.get('netIncomePerShareTTM'))
    bvps    = safe(rtm.get('bookValuePerShareTTM'))
    fcf_ps  = safe(rtm.get('freeCashFlowPerShareTTM'))
    roe     = safe(mttm.get('returnOnEquityTTM'))
    ev      = safe(mttm.get('enterpriseValueTTM'))
    div_y   = safe(rtm.get('dividendYieldTTM'), 0) * 100  # % olarak
    peg_fmp = safe(rtm.get('priceToEarningsGrowthRatioTTM'))
    fwd_peg = safe(rtm.get('forwardPriceToEarningsGrowthRatioTTM'))
    graham_fmp = safe(mttm.get('grahamNumberTTM'))

    bal  = fmp_get("balance-sheet-statement", {"symbol": symbol, "period": "quarter", "limit": 1})
    b    = bal[0] if bal else {}
    cash = safe(b.get('cashAndCashEquivalents'), 0) + safe(b.get('shortTermInvestments'), 0)
    nd   = safe(b.get('totalDebt'), 0) - cash

    inc4 = fmp_get("income-statement", {"symbol": symbol, "period": "quarter", "limit": 4}) or []
    ttm_rev    = sum((q.get('revenue')         or 0) for q in inc4)
    ttm_ebit   = sum((q.get('operatingIncome') or 0) for q in inc4)
    ttm_ebitda = sum((q.get('ebitda')          or 0) for q in inc4)

    cf8     = fmp_get("cash-flow-statement", {"symbol": symbol, "period": "quarter", "limit": 8}) or []
    ttm_fcf = sum((q.get('freeCashFlow') or 0) for q in cf8[:4])
    prev_fcf= sum((q.get('freeCashFlow') or 0) for q in cf8[4:])
    # Sektöre göre FCF büyüme tavanı — utilities/financial daha muhafazakâr
    _fcf_cap = {'utilities': 0.12, 'financial': 0.12, 'energy': 0.20,
                'industrial': 0.20, 'consumer': 0.20}.get(sector_cat, 0.50)
    if prev_fcf > 0 and abs(prev_fcf) > ttm_fcf * 10:
        # prev_fcf çok küçük/negatifse yıllık gelir tablosundan büyüme al
        fcf_gr = min(_fcf_cap, max(-0.20, rev_gr))
    else:
        fcf_gr  = min(_fcf_cap, max(-0.20, ttm_fcf / prev_fcf - 1.0)) if prev_fcf > 0 else min(0.10, rev_gr)

    inc_ann = fmp_get("income-statement", {"symbol": symbol, "period": "annual", "limit": 2}) or []
    if len(inc_ann) >= 2 and (inc_ann[1].get('eps') or 0) > 0:
        eps_gr = min(0.60, max(-0.20, (inc_ann[0].get('eps', 0) / inc_ann[1].get('eps', 1)) - 1.0))
        rev_gr = min(0.50, max(-0.10, (inc_ann[0].get('revenue', 0) / inc_ann[1].get('revenue', 1)) - 1.0)) if (inc_ann[1].get('revenue') or 0) > 0 else eps_gr * 0.5
    else:
        eps_gr, rev_gr = 0.12, 0.08

    today  = datetime.now().strftime("%Y-%m-%d")
    tr     = fmp_get("treasury-rates", {"from": "2026-04-01", "to": today})
    bond_y = safe(tr[0].get('year10')) if tr else 4.5
    rate_pe = max(4.0, min(30.0, 100.0 / bond_y))

    # ── HİSSE TİPİ TESPİTİ ─────────────────────────────────────
    his_252g = fetch_all_252g_ratios(symbol, shares)
    avg_pe   = his_252g.get('pe')

    hisse_tipi = 'deger'
    if avg_pe and avg_pe > BUYUME_PE_ESIK:
        hisse_tipi = 'buyume'
    elif div_y >= TEMETTU_YIELD_MIN:
        hisse_tipi = 'temettu'
    elif sector_cat in ['energy', 'industrial']:
        hisse_tipi = 'dongusel'

    # ── PE ÇARPANI ──────────────────────────────────────────────
    if pe_modu == 'manuel' and manuel_pe:
        kullanilan_pe = manuel_pe
    elif pe_modu == 'rate':
        kullanilan_pe = rate_pe
    else:
        kullanilan_pe = avg_pe if avg_pe else rate_pe

    # ── FORWARD EPS (OTOMATIK) ──────────────────────────────────
    if fwd_eps_input:
        fwd_eps, fwd_kaynak = fwd_eps_input, 'manuel_giriş'
    else:
        fwd_eps, fwd_kaynak = derive_fwd_eps(price, rtm, eps_ttm, eps_gr)

    fwd_pe_mult = (price / fwd_eps) if (fwd_eps and fwd_eps > 0) else kullanilan_pe

    # ── AKILlI PEER SEÇİCİ ──────────────────────────────────────
    _fcf_m    = (ttm_fcf / ttm_rev * 100) if ttm_rev > 0 else 0
    subj_profile = {
        "rev_gr": rev_gr * 100,
        "gp_m":   (safe(rtm.get("grossProfitMarginTTM"), 0)) * 100,
        "fcf_m":  _fcf_m,
        "mktcap": mktcap / 1e9,
    }
    sirkket_ev_rev = his_252g.get("ev_rev")
    peer_result  = fetch_smart_peer_evrev(symbol, subj_profile, hisse_tipi)
    peer_raw_median, peer_adj_median, peer_list, rof40_skoru, rof40_evrev = peer_result
    prim_uyarisi = (
        peer_raw_median and sirkket_ev_rev and
        sirkket_ev_rev > peer_raw_median * PEER_PRIM_ESIK
    )

    # ── ÖZET ────────────────────────────────────────────────────
    if not sessiz:
        tip_label = {'buyume':'🚀 BÜYÜME/NARATİF','temettu':'💰 TEMETTÜ',
                     'dongusel':'🔄 DÖNGÜSEL','deger':'📊 DEĞER'}.get(hisse_tipi, '')
        print(f"  {symbol} | {sector_str} | {tip_label}")
        print(f"  Fiyat: ${price:.2f} | Piy.Değ: ${mktcap/1e9:.1f}B | EV: ${ev/1e9:.1f}B")
        print(f"  EPS TTM: ${eps_ttm:.2f} | FCF/H: ${fcf_ps:.2f} | BVPS: ${bvps:.2f} | ROE: {roe*100:.1f}%" if all([eps_ttm,fcf_ps,bvps,roe]) else "")
        print(f"  Net Borç: ${nd/1e9:.2f}B {'(Net Nakit ✓)' if nd<0 else ''}")
        print(f"  10Y: {bond_y:.2f}% → F/K faiz bazlı: {rate_pe:.1f}x")
        print(f"  PEG: {peg_fmp:.2f} | Fwd PEG: {fwd_peg:.2f}" if peg_fmp and fwd_peg else "")
        print()
        print(f"  252G ORANLAR: P/E={avg_pe:.1f}x | P/S={his_252g.get('ps'):.1f}x | "
              f"EV/EBITDA={his_252g.get('ev_ebitda'):.1f}x | EV/Ciro={sirkket_ev_rev:.1f}x"
              if all([avg_pe, his_252g.get('ps'), his_252g.get('ev_ebitda'), sirkket_ev_rev]) else "")

        if peer_raw_median:
            print(f"  Peer seçimi ({len(peer_list)} şirket): {', '.join(peer_list[:6])}")
            print(f"  Peer EV/Ciro: ham={peer_raw_median:.1f}x | büyüme-düzeltmeli={peer_adj_median:.1f}x", end="")
            if prim_uyarisi:
                print(f"  ⚠️  PRİM: kendi 252g {sirkket_ev_rev:.1f}x > peer {peer_raw_median:.1f}x × {PEER_PRIM_ESIK}x")
            else:
                print()
        if rof40_skoru:
            print(f"  Rule of 40: {rof40_skoru:.1f} (büyüme {subj_profile['rev_gr']:.1f}% + FCF marj {_fcf_m:.1f}%)")
            if rof40_evrev:
                print(f"  RoF40 hedef EV/Ciro: {rof40_evrev:.1f}x")

        if hisse_tipi == 'buyume':
            print(f"  ⚠️  252g P/E {avg_pe:.0f}x > {BUYUME_PE_ESIK}x — büyüme/narratif hissesi, güveni düşük olabilir")

        print(f"  Kullanılan F/K: {kullanilan_pe:.1f}x ({pe_modu})")
        print(f"  Forward EPS: ${fwd_eps:.2f} ({fwd_kaynak}) | Fwd P/E: {fwd_pe_mult:.1f}x" if fwd_eps else "")
        print(f"  EPS büyüme: {eps_gr*100:.1f}% | Ciro büyüme: {rev_gr*100:.1f}% | FCF büyüme: {fcf_gr*100:.1f}%")
        print()

    # ── 11 DEĞERLEME METODU ─────────────────────────────────────
    def ev2p(ev_fair):
        return max(0, (ev_fair - nd) / shares)

    M = {}

    # 1. Net Kazanç P/E
    if eps_ttm and eps_ttm > 0:
        M['Net Kazanç P/E'] = eps_ttm * kullanilan_pe

    # 2. ROE Bazlı
    if roe and roe > 0 and bvps:
        M['ROE Bazlı'] = (roe * bvps) * kullanilan_pe

    # 3. EV/EBIT (252g ort.)
    if ttm_ebit > 0 and his_252g.get('ev_ebit'):
        M['EV/EBIT'] = ev2p(ttm_ebit * his_252g['ev_ebit'])

    # 4. EV/EBITDA (252g ort.)
    if ttm_ebitda > 0 and his_252g.get('ev_ebitda'):
        M['EV/EBITDA'] = ev2p(ttm_ebitda * his_252g['ev_ebitda'])

    # 5. EV/Ciro
    # Büyüme hisseleri için büyüme-düzeltmeli peer median kullan
    # Diğerleri için 252g kendi tarihsel ortalaması
    if ttm_rev > 0:
        if hisse_tipi == "buyume" and peer_adj_median:
            M["EV/Ciro"] = ev2p(ttm_rev * peer_adj_median)
        elif sirkket_ev_rev:
            M["EV/Ciro"] = ev2p(ttm_rev * sirkket_ev_rev)

    # 6. Forward P/E
    if fwd_eps and fwd_eps > 0:
        M['Forward P/E'] = fwd_eps * fwd_pe_mult

    # 7. Forward P/S (252g P/S × ileri ciro)
    if ttm_rev > 0 and his_252g.get('ps'):
        M['Forward P/S'] = (ttm_rev * (1 + rev_gr) / shares) * his_252g['ps']

    # 8. P/FCF (252g ort.)
    if fcf_ps and fcf_ps > 0 and his_252g.get('pfcf'):
        M['P/FCF'] = fcf_ps * his_252g['pfcf']

    # 9. Graham
    if eps_ttm and eps_ttm > 0 and bvps and bvps > 0:
        M["Graham"] = math.sqrt(22.5 * eps_ttm * bvps)
    elif graham_fmp:
        M["Graham"] = graham_fmp

    # 9b. Rule of 40 EV/Ciro (büyüme hisseleri için ek mercek — ağırlıklı toplama dahil değil, sadece gösterim)
    if hisse_tipi == "buyume" and rof40_evrev and ttm_rev > 0:
        M["RoF40 EV/Ciro*"] = ev2p(ttm_rev * rof40_evrev)

    # 10. Multi-stage DCF
    if ttm_fcf > 0:
        wacc = bond_y / 100 + 0.05
        dcf  = calc_dcf_multistage(ttm_fcf, fcf_gr, wacc, 0.025, nd, shares)
        if dcf: M['DCF (3 aşama)'] = dcf

    # 11. PEG Bazlı (Forward PEG = 1.0 → adil değer)
    # Sadece makul büyüme varsa ve PEG pozitifse hesapla
    if fwd_peg and fwd_peg > 0 and fwd_eps and fwd_eps > 0 and eps_gr > 0.05:
        fair_pe_peg = 1.0 * (eps_gr * 100)   # PEG=1 → P/E = büyüme %
        fair_pe_peg = max(fair_pe_peg, rate_pe)  # en az faize dayalı P/E
        M["PEG Bazlı"] = fwd_eps * fair_pe_peg

    # ── AĞIRLIKLI TOPLAM ────────────────────────────────────────
    sirasi  = ["Net Kazanç P/E","ROE Bazlı","EV/EBIT","EV/EBITDA","EV/Ciro",
               "Forward P/E","Forward P/S","P/FCF","Graham","DCF (3 aşama)","PEG Bazlı"]
    agirlar = SECTOR_WEIGHTS.get(sector_cat, SECTOR_WEIGHTS["other"])
    # RoF40 EV/Ciro → ağırlıksız, sadece gösterim
    if "RoF40 EV/Ciro*" in M:
        sirasi.append("RoF40 EV/Ciro*")
        agirlar = list(agirlar) + [0]

    if not sessiz:
        print(f"  {'─'*62}")
        print(f"  {'METOT':<18} {'ADİL DEĞER':>12} {'FARK%':>8} {'AĞ%':>5}  DURUM")
        print(f"  {'─'*62}")

    ws, tw = 0.0, 0.0
    tum = []
    for metot, ag in zip(sirasi, agirlar):
        val = M.get(metot)
        if val and val > 0:
            diff  = (price / val - 1) * 100
            durum = "↑ PAHALI" if diff > 20 else "↓ UCUZ " if diff < -20 else "≈ ADİL "
            if not sessiz:
                print(f"  {metot:<18} ${val:>10.2f} {diff:>+7.1f}% {ag*100:>4.0f}%  {durum}")
            tum.append(val)
            if ag > 0: ws += val * ag; tw += ag
        elif not sessiz:
            print(f"  {metot:<18} {'N/A':>12} {'':>8} {ag*100:>4.0f}%")

    adil = ws / tw if tw > 0 else None
    fark = (price / adil - 1) * 100 if adil else None

    # Güven skoru — IQR bazlı outlier filtresi sonrası CV
    guven = 0
    if tum and len(tum) >= 3:
        s = sorted(tum)
        q1, q3 = s[len(s)//4], s[3*len(s)//4]
        iqr = q3 - q1
        # Outlier = medyanın 3x IQR dışındakiler
        median_v = s[len(s)//2]
        temiz = [v for v in tum if abs(v - median_v) <= 3 * max(iqr, median_v * 0.5)]
        if len(temiz) >= 2:
            ort = sum(temiz) / len(temiz)
            std = math.sqrt(sum((v-ort)**2 for v in temiz) / len(temiz))
            cv  = abs(std/ort)*100 if ort else 100
            guven = max(0, min(100, round(100-cv)))

    # Analist hedefi
    pt_data = fmp_get("price-target-summary", {"symbol": symbol})
    analyst_target = safe(pt_data[0].get('lastQuarterAvgPriceTarget')) if pt_data else None

    if not sessiz and adil:
        yon = "PAHALI 🔴" if fark > 20 else "UCUZ 🟢" if fark < -20 else "ADİL 🟡"
        print(f"  {'─'*62}")
        print(f"\n  ADİL DEĞER (Ağırlıklı):    ${adil:>10.2f}")
        print(f"  Güncel Fiyat:              ${price:>10.2f}")
        print(f"  Fark:                      {fark:>+10.1f}%  →  {yon}")
        print(f"  Güven Skoru:               {guven}/100")
        if analyst_target:
            at_diff = (price / analyst_target - 1) * 100
            print(f"  Analist Hedefi:            ${analyst_target:>10.2f}  ({at_diff:+.1f}%)")
        print(f"\n  Bantlar: %20 Prim → ${adil*1.2:.2f} | %20 İskonto → ${adil*0.8:.2f}")
        if hisse_tipi == "buyume":
            rof40_fv = M.get("RoF40 EV/Ciro*")
            narrative_prim = ((price - rof40_fv) / price * 100) if rof40_fv else None
            print(f"\n  Rule of 40 EV/Ciro bazlı adil değer: ${rof40_fv:.2f}" if rof40_fv else "")
            if narrative_prim:
                print(f"  Narrative prim (RoF40 üstü)       : %{narrative_prim:.0f}")
                print(f"  → Piyasa bu farkı AI platform opsiyonelliğine bağlıyor")
            print(f"\n  ⚠️  Güven skoru: {guven}/100 — narratif hisseler için")
            print(f"  DCF, PEG ve RoF40 merceklerine öncelik verin.")
            print(f"  Analist konsensüs ${analyst_target:.2f} referans olarak kullanın." if analyst_target else "")
        print(f"\n{'='*62}")

    return {
        'symbol': symbol, 'price': price, 'adil_deger': adil, 'fark_pct': fark,
        'guven': guven, 'hisse_tipi': hisse_tipi, 'analyst_target': analyst_target,
        'sector': sector_str, 'peg': peg_fmp, 'fwd_peg': fwd_peg,
        'metotlar': M, '252g': his_252g,
    }


# ─── BATCH / PORTFOLIO MODU ─────────────────────────────────────────────────

def batch_ozet(sonuclar):
    print(f"\n{'═'*70}")
    print(f"  ÖZET TABLO — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'═'*70}")
    print(f"  {'SEM':<6} {'FİYAT':>8} {'ADİL':>8} {'FARK%':>7} {'GÜVEN':>6} {'TİP':<12}  {'PEG':>5}  DURUM")
    print(f"  {'─'*68}")
    for s in sonuclar:
        if not s: continue
        adil = s['adil_deger'] or 0
        fark = s['fark_pct'] or 0
        yon  = "🔴" if fark > 20 else "🟢" if fark < -20 else "🟡"
        tip  = s['hisse_tipi'][:8]
        peg  = f"{s['peg']:.1f}" if s['peg'] else 'N/A'
        print(f"  {s['symbol']:<6} ${s['price']:>7.2f} ${adil:>7.2f} {fark:>+6.1f}% {s['guven']:>5}/100 {tip:<12} {peg:>5}  {yon}")
    print(f"{'═'*70}\n")


def markdown_rapor(sonuclar):
    """Markdown rapor oluşturur ve döndürür."""
    tarih = datetime.now().strftime('%Y-%m-%d')
    md = [f"# Adil Değer Raporu — {tarih}\n"]
    md.append("| Sembol | Fiyat | Adil Değer | Fark | Güven | Tip | PEG | Fwd PEG |")
    md.append("|--------|-------|------------|------|-------|-----|-----|---------|")
    for s in sonuclar:
        if not s: continue
        adil = f"${s['adil_deger']:.2f}" if s['adil_deger'] else 'N/A'
        fark = f"{s['fark_pct']:+.1f}%" if s['fark_pct'] else 'N/A'
        peg  = f"{s['peg']:.2f}" if s['peg'] else 'N/A'
        fpeg = f"{s['fwd_peg']:.2f}" if s['fwd_peg'] else 'N/A'
        md.append(f"| {s['symbol']} | ${s['price']:.2f} | {adil} | {fark} | {s['guven']}/100 | {s['hisse_tipi']} | {peg} | {fpeg} |")
    return "\n".join(md)


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adil Değer Hesaplayıcı v2.0")
    parser.add_argument("symbols", nargs='*', help="Sembol(ler): AMD MU PLTR")
    parser.add_argument("--portfolio", choices=['balanced','aggressive','dividend'],
                        help="Portfolio JSON'dan semboller oku")
    parser.add_argument("--pe-modu",   default="average",
                        choices=["rate","manuel","average"])
    parser.add_argument("--manuel-pe", type=float)
    parser.add_argument("--fwd-eps",   type=float,
                        help="Manuel forward EPS (girilmezse FMP forwardPEG ile türetilir)")
    parser.add_argument("--report",    action="store_true",
                        help="Markdown rapor yaz")
    parser.add_argument("--telegram",  action="store_true",
                        help="Telegram'a gönder")
    args = parser.parse_args()

    # Sembol listesi oluştur
    symbols = list(args.symbols)
    if args.portfolio:
        pf_path = os.path.join(REPO_ROOT, "data", "portfolios", f"{args.portfolio}.json")
        try:
            with open(pf_path) as f:
                pf = json.load(f)
            symbols = [p['symbol'] for p in pf.get('positions', [])]
            print(f"Portfolio '{args.portfolio}': {symbols}")
        except Exception as e:
            print(f"Portfolio okunamadı: {e}")
            sys.exit(1)

    if not symbols:
        parser.print_help(); sys.exit(1)

    # Her sembol için hesapla
    sonuclar = []
    sessiz   = len(symbols) > 1
    for sym in symbols:
        if sessiz: print(f"\n► {sym.upper()} hesaplanıyor...")
        s = hesapla(sym.upper(), pe_modu=args.pe_modu,
                    manuel_pe=args.manuel_pe,
                    fwd_eps_input=args.fwd_eps,
                    sessiz=sessiz)
        sonuclar.append(s)

    # Birden fazla sembol → özet tablo
    if sessiz:
        batch_ozet(sonuclar)

    # Rapor
    if args.report:
        tarih   = datetime.now().strftime('%Y-%m-%d')
        rp_path = os.path.join(REPO_ROOT, "reports", "daily", f"ADIL_DEGER_{tarih}.md")
        os.makedirs(os.path.dirname(rp_path), exist_ok=True)
        with open(rp_path, 'w') as f:
            f.write(markdown_rapor(sonuclar))
        print(f"Rapor yazıldı: {rp_path}")

    # Telegram
    if args.telegram and sonuclar:
        lines = [f"<b>📊 Adil Değer — {datetime.now().strftime('%d.%m.%Y')}</b>\n"]
        for s in sonuclar:
            if not s: continue
            adil = f"${s['adil_deger']:.2f}" if s['adil_deger'] else 'N/A'
            fark = f"{s['fark_pct']:+.1f}%" if s['fark_pct'] else ''
            yon  = "🔴" if (s['fark_pct'] or 0) > 20 else "🟢" if (s['fark_pct'] or 0) < -20 else "🟡"
            lines.append(f"{yon} <b>{s['symbol']}</b> ${s['price']:.2f} → {adil} ({fark}) Güven:{s['guven']}/100")
        tg_send("\n".join(lines))
        print("Telegram bildirimi gönderildi.")
