#!/usr/bin/env python3
"""
Aşama 2: YoY/QoQ İyileşme Filtresi

Mid-cap+ filtreli hisseler için son 5 çeyrek income-statement çekip:
- YoY ciro artışı ≥ 8%
- YoY net kâr artışı ≥ 15% VEYA zarardan kâra geçiş (L2P)
- QoQ ciro artışı ≥ 3%
- QoQ net kâr iyileşmesi
4 kriterden en az 3'ü geçmeli + YoY ciro zorunlu.

Outlier: yoy_rev > 500% (IPO/M&A artefaktı) elenir.

Kullanım:
    python 02_growth_filter.py --in 01_filtered_midcap.json --out 02_growth_passed.json

Çıktı: 02_growth_passed.json
"""
import os
import sys
import json
import time
import argparse
import requests

API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
BASE = "https://financialmodelingprep.com/stable"


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


def calc_growth(stock):
    """Hisse için YoY/QoQ büyüme metrikleri hesapla, kriter geçişini değerlendir."""
    sym = stock["symbol"]
    inc = fmp_get("income-statement", {"symbol": sym, "period": "quarter", "limit": 5})
    if not inc or not isinstance(inc, list) or len(inc) < 5:
        return None  # yetersiz veri
    
    q0, q1, q4 = inc[0], inc[1], inc[4]
    
    rev0 = q0.get("revenue") or 0
    rev1 = q1.get("revenue") or 0
    rev4 = q4.get("revenue") or 0
    
    ni0 = q0.get("netIncome") or 0
    ni1 = q1.get("netIncome") or 0
    ni4 = q4.get("netIncome") or 0
    
    eps0 = q0.get("epsDiluted") or q0.get("eps") or 0
    eps4 = q4.get("epsDiluted") or q4.get("eps") or 0
    
    yoy_rev = ((rev0 - rev4) / abs(rev4) * 100) if rev4 else None
    yoy_ni_pct = ((ni0 - ni4) / abs(ni4) * 100) if ni4 else None
    yoy_eps_pct = ((eps0 - eps4) / abs(eps4) * 100) if eps4 else None
    qoq_rev = ((rev0 - rev1) / abs(rev1) * 100) if rev1 else None
    qoq_ni_pct = ((ni0 - ni1) / abs(ni1) * 100) if ni1 else None
    
    loss_to_profit_yoy = (ni4 < 0 and ni0 > 0)
    loss_to_profit_qoq = (ni1 < 0 and ni0 > 0)
    
    # Loss narrowing: her iki çeyrek de zarar ama zarar daraldı (örn. -100 -> -50)
    # Bu da pozitif bir geçiş sinyalidir — turnaround sürecinde
    loss_narrowing_yoy = (ni4 < 0 and ni0 < 0 and abs(ni0) < abs(ni4) * 0.5)  # Zarar yarıdan az
    loss_narrowing_qoq = (ni1 < 0 and ni0 < 0 and abs(ni0) < abs(ni1) * 0.7)  # QoQ zarar daralma daha yumuşak
    
    # Kriter geçişleri
    pass_yoy_rev = (yoy_rev is not None and yoy_rev >= 8)
    pass_yoy_ni = (loss_to_profit_yoy or loss_narrowing_yoy
                   or (yoy_ni_pct is not None and ni4 > 0 and yoy_ni_pct >= 15))
    pass_qoq_rev = (qoq_rev is not None and qoq_rev >= 3)
    pass_qoq_ni = (loss_to_profit_qoq or loss_narrowing_qoq
                   or (qoq_ni_pct is not None and ni1 > 0 and qoq_ni_pct >= 0))
    
    passed = sum([pass_yoy_rev, pass_yoy_ni, pass_qoq_rev, pass_qoq_ni])
    if not pass_yoy_rev or passed < 3:
        return None  # Filtre geçemedi
    
    # Outlier filtre
    if yoy_rev > 500:
        return None  # IPO/M&A artefaktı
    
    return {
        **stock,
        "q0_date": q0.get("date"),
        "q0_period": q0.get("period"),
        "rev0": rev0, "rev1": rev1, "rev4": rev4,
        "ni0": ni0, "ni1": ni1, "ni4": ni4,
        "eps0": eps0, "eps4": eps4,
        "yoy_rev_pct": yoy_rev,
        "yoy_ni_pct": yoy_ni_pct,
        "yoy_eps_pct": yoy_eps_pct,
        "qoq_rev_pct": qoq_rev,
        "qoq_ni_pct": qoq_ni_pct,
        "loss_to_profit_yoy": loss_to_profit_yoy,
        "loss_to_profit_qoq": loss_to_profit_qoq,
        "loss_narrowing_yoy": loss_narrowing_yoy,
        "loss_narrowing_qoq": loss_narrowing_qoq,
        "passed_count": passed,
    }


def score(r):
    """İlk skor — büyüme kalitesi (sıralama için)."""
    s = 0
    s += min((r.get("yoy_rev_pct") or 0), 100)
    if r.get("yoy_eps_pct") is not None:
        s += min(max((r["yoy_eps_pct"] or 0), -50), 200) * 0.5
    if r.get("qoq_rev_pct") is not None:
        s += (r["qoq_rev_pct"] or 0) * 2
    if r.get("loss_to_profit_yoy"):
        s += 50
    if r.get("loss_to_profit_qoq"):
        s += 30
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="01_filtered_midcap.json")
    ap.add_argument("--out", default="02_growth_passed.json")
    args = ap.parse_args()
    
    with open(args.inp) as f:
        universe = json.load(f)
    print(f"Giriş: {len(universe)} hisse")
    
    results = []
    for i, stock in enumerate(universe):
        r = calc_growth(stock)
        if r:
            r["growth_score"] = score(r)
            results.append(r)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(universe)} işlendi, {len(results)} geçti")
    
    results.sort(key=lambda x: x["growth_score"], reverse=True)
    
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n=== İyileşen hisseler: {len(results)} ===")
    print(f"\nTop 25:")
    print(f"{'Sym':8s} {'Sektör':22s} {'YoY-R':>7s} {'YoY-NI':>10s} {'QoQ-R':>7s} {'L2P':>4s} {'Skor':>7s}")
    print("-" * 80)
    for r in results[:25]:
        yoy_ni = f"{r['yoy_ni_pct']:.0f}%" if r.get("yoy_ni_pct") is not None else "N/A"
        if r.get("loss_to_profit_yoy"):
            yoy_ni = "L2P"
        print(f"{r['symbol']:8s} {(r.get('sector') or 'N/A')[:22]:22s} {r['yoy_rev_pct']:>6.1f}% {yoy_ni:>10s} {r['qoq_rev_pct']:>6.1f}% {('Y' if r.get('loss_to_profit_yoy') else '-'):>4s} {r['growth_score']:>7.1f}")
    print(f"\nKaydedildi: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
