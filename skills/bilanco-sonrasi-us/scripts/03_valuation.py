#!/usr/bin/env python3
"""
Aşama 3: Adil Değer + Analist Target Sağlamlık Filtresi

4 yöntem ağırlıklı adil değer:
  1) Analyst price target consensus (FMP) — 30%
  2) Forward P/E × NTM EPS (sektör çarpanı) — 30%
  3) PEG = 1 fair value (TTM EPS × growth) — 20%
  4) EV/EBITDA peer median × EBITDA − Net debt — 20%

Sağlamlık filtresi:
  - Analyst target ZATEN min +25% upside (en güvenilir tek metrik)
  - En az 1 fundamental yöntem (Forward P/E veya EV/EBITDA) +20% pozitif teyit
  - L2P hisselerde PEG ağırlığı düşürülür

Kullanım:
    python 03_valuation.py --in 02_growth_passed.json --out 03_solid_shortlist.json --top 45

Çıktı: 03_solid_shortlist.json
"""
import os
import sys
import json
import time
import argparse
import requests
from statistics import mean, stdev

API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
BASE = "https://financialmodelingprep.com/stable"

# Sektör çarpanları (referans, dinamikleştirilebilir)
SECTOR_PE_FAIR = {
    "Technology": 28, "Healthcare": 22, "Financial Services": 14, 
    "Consumer Cyclical": 20, "Consumer Defensive": 22, 
    "Communication Services": 22, "Industrials": 22,
    "Energy": 12, "Utilities": 18, "Basic Materials": 16, "Real Estate": 18,
}

SECTOR_EVEBITDA_FAIR = {
    "Technology": 18, "Healthcare": 14, "Financial Services": 10,
    "Consumer Cyclical": 12, "Consumer Defensive": 14,
    "Communication Services": 12, "Industrials": 13,
    "Energy": 7, "Utilities": 11, "Basic Materials": 9, "Real Estate": 14,
}


def fmp_get(endpoint, params=None, max_retries=3, retry_delay=1.5):
    """FMP API çağrısı. 429/503/network için retry, 4xx için None döner."""
    if params is None:
        params = {}
    params["apikey"] = API_KEY
    for attempt in range(max_retries):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            elif r.status_code == 503:
                time.sleep(retry_delay)
                continue
            else:
                return None
        except (requests.ConnectionError, requests.Timeout):
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
        except Exception:
            break
    return None


def calculate_fair_value(stock):
    """4 yöntem ağırlıklı adil değer hesabı."""
    sym = stock["symbol"]
    sector = stock.get("sector") or "Industrials"
    price = stock.get("price") or 0
    mcap = stock.get("mcap") or 0
    
    # 1) Analyst price target consensus
    pt = fmp_get("price-target-consensus", {"symbol": sym})
    target_consensus = None
    if pt and isinstance(pt, list) and len(pt) > 0:
        target_consensus = pt[0].get("targetConsensus") or pt[0].get("targetMedian")
    
    # 2) Forward P/E × NTM EPS
    est = fmp_get("analyst-estimates", {"symbol": sym, "period": "annual", "limit": 2})
    ntm_eps = None
    if est and isinstance(est, list) and len(est) > 0:
        ntm_eps = est[0].get("epsAvg")
    fwd_pe_fair = SECTOR_PE_FAIR.get(sector, 18)
    forward_pe_value = ntm_eps * fwd_pe_fair if ntm_eps and ntm_eps > 0 else None
    
    # 3) PEG = 1 fair value
    ratios = fmp_get("ratios-ttm", {"symbol": sym})
    ttm_eps = None
    if ratios and isinstance(ratios, list) and len(ratios) > 0:
        ttm_eps = ratios[0].get("netIncomePerShareTTM") or ratios[0].get("epsTTM")
    yoy_rev = stock.get("yoy_rev_pct") or 0
    growth_for_peg = max(min(yoy_rev, 30), 5)
    peg_value = ttm_eps * growth_for_peg if ttm_eps and ttm_eps > 0 else None
    
    # 4) EV/EBITDA peer median
    inc_quarters = fmp_get("income-statement", {"symbol": sym, "period": "quarter", "limit": 4})
    ebitda_ttm = None
    if inc_quarters and isinstance(inc_quarters, list) and len(inc_quarters) >= 4:
        ebitda_ttm = sum((q.get("ebitda") or 0) for q in inc_quarters)
    
    bs = fmp_get("balance-sheet-statement", {"symbol": sym, "period": "quarter", "limit": 1})
    net_debt = None
    if bs and isinstance(bs, list) and len(bs) > 0:
        b = bs[0]
        total_debt = b.get("totalDebt") or 0
        cash = b.get("cashAndShortTermInvestments") or b.get("cashAndCashEquivalents") or 0
        net_debt = total_debt - cash
    
    shares_out = mcap / price if price else 0
    evebitda_fair = SECTOR_EVEBITDA_FAIR.get(sector, 12)
    evebitda_value = None
    if ebitda_ttm and ebitda_ttm > 0 and net_debt is not None and shares_out > 0:
        ev_target = ebitda_ttm * evebitda_fair
        equity_target = ev_target - net_debt
        evebitda_value = equity_target / shares_out
    
    # Ağırlıklı yöntemler
    methods = {}
    if target_consensus and target_consensus > 0:
        methods["analyst_target"] = (target_consensus, 0.30)
    if forward_pe_value and forward_pe_value > 0:
        methods["forward_pe"] = (forward_pe_value, 0.30)
    if peg_value and peg_value > 0:
        methods["peg"] = (peg_value, 0.20)
    if evebitda_value and evebitda_value > 0:
        methods["ev_ebitda"] = (evebitda_value, 0.20)
    
    if len(methods) < 2:
        return None  # Yetersiz veri
    
    total_w = sum(w for _, w in methods.values())
    fair_value = sum(v * w for v, w in methods.values()) / total_w
    upside_pct = (fair_value - price) / price * 100 if price else 0
    
    # L2P düzeltmesi: PEG'i çıkar, kalan yöntemlerle yeniden hesapla
    fair_value_adj = fair_value
    upside_pct_adj = upside_pct
    if stock.get("loss_to_profit_yoy"):
        adj_methods = {k: v for k, v in methods.items() if k != "peg"}
        if len(adj_methods) >= 2:
            total_w_adj = sum(w for _, w in adj_methods.values())
            fair_value_adj = sum(v * w for v, w in adj_methods.values()) / total_w_adj
            upside_pct_adj = (fair_value_adj - price) / price * 100 if price else 0
    
    # Confidence (CV)
    vals = [v for v, _ in methods.values()]
    mu = mean(vals)
    sd = stdev(vals) if len(vals) > 1 else 0
    cv = sd / mu if mu > 0 else 1
    if cv < 0.20:
        confidence = "YUKSEK"
    elif cv < 0.40:
        confidence = "ORTA"
    else:
        confidence = "DUSUK"
    
    return {
        **stock,
        "ttm_eps": ttm_eps, "ntm_eps": ntm_eps,
        "ebitda_ttm": ebitda_ttm, "net_debt": net_debt,
        "method_values": {k: v for k, (v, _) in methods.items()},
        "method_count": len(methods),
        "fair_value": fair_value,
        "upside_pct": upside_pct,
        "fair_value_adj": fair_value_adj,
        "upside_pct_adj": upside_pct_adj,
        "cv": cv,
        "confidence": confidence,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="02_growth_passed.json")
    ap.add_argument("--out", default="03_solid_shortlist.json")
    ap.add_argument("--top", type=int, default=45, help="Adil değer hesaplanacak max hisse sayısı")
    ap.add_argument("--min-analyst-upside", type=float, default=25.0, help="Min analyst target upside %")
    ap.add_argument("--min-fundamental-upside", type=float, default=20.0, help="Min fundamental confirmation upside %")
    args = ap.parse_args()
    
    with open(args.inp) as f:
        candidates = json.load(f)
    print(f"Giriş: {len(candidates)} hisse, ilk {args.top} işlenecek")
    
    valued = []
    for i, c in enumerate(candidates[:args.top]):
        v = calculate_fair_value(c)
        if v:
            valued.append(v)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{min(len(candidates), args.top)} adil değer hesaplandı")
    
    # Sağlamlık filtresi
    solid = []
    for r in valued:
        mv = r["method_values"]
        price = r["price"]
        at = mv.get("analyst_target")
        if not at:
            continue
        at_upside = (at - price) / price * 100
        if at_upside < args.min_analyst_upside:
            continue
        
        fundamentals_pos = sum(
            1 for k in ["forward_pe", "ev_ebitda"]
            if mv.get(k) and (mv[k] - price) / price * 100 >= args.min_fundamental_upside
        )
        if fundamentals_pos < 1:
            continue
        
        r["analyst_target_upside"] = at_upside
        r["fundamentals_confirmed"] = fundamentals_pos
        solid.append(r)
    
    solid.sort(key=lambda x: x["analyst_target_upside"], reverse=True)
    
    with open(args.out, "w") as f:
        json.dump(solid, f, indent=2, default=str)
    
    print(f"\n=== Sağlam shortlist: {len(solid)} hisse ===\n")
    print(f"{'Sym':6s} {'Sektör':22s} {'Fiyat':>8s} {'A.Tgt':>8s} {'A.Up':>7s} {'Fwd':>8s} {'EV/EB':>8s} {'YoY-R':>7s}")
    print("-" * 95)
    for r in solid:
        mv = r["method_values"]
        fwd = f"${mv.get('forward_pe', 0):.0f}" if mv.get('forward_pe') else "-"
        eve = f"${mv.get('ev_ebitda', 0):.0f}" if mv.get('ev_ebitda') else "-"
        print(f"{r['symbol']:6s} {(r.get('sector') or 'N/A')[:22]:22s} ${r['price']:>7.2f} ${mv['analyst_target']:>7.2f} {r['analyst_target_upside']:>6.1f}% {fwd:>8s} {eve:>8s} {r['yoy_rev_pct']:>6.1f}%")
    
    print(f"\nKaydedildi: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
