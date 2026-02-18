#!/usr/bin/env python3
"""
Swing Trade Scanner v2 — FMP Only
Two-phase: Quick momentum screen → Deep fundamental scan
Reads strategy_params.json for evolving parameters.

Usage: python3 scanner.py --api-key KEY
"""

import json
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fmp_client import FMPClient

DATA_DIR = Path(__file__).parent.parent / "data"

# ═══════════════════════════════════════════════════════════
# SCAN UNIVERSE
# ═══════════════════════════════════════════════════════════

UNIVERSE = {
    "Technology": [
        "NVDA", "AMD", "AVGO", "MRVL", "ANET", "CRWD", "PANW", "NOW",
        "DDOG", "NET", "PLTR", "DELL", "SMCI", "VRT", "COIN",
        "ADBE", "CRM", "ORCL", "MSFT", "GOOGL", "META", "AMZN", "AAPL",
        "TSM", "QCOM", "MU", "LRCX", "AMAT", "ARM"
    ],
    "Communication": [
        "NFLX", "DIS", "SPOT", "RBLX", "TTWO", "TTD", "ROKU"
    ],
    "Energy": [
        "VST", "CEG", "CCJ", "NRG", "GEV", "ETN", "PWR",
        "FSLR", "NEE", "XLE", "SM", "FCX", "SCCO"
    ],
    "Healthcare": [
        "LLY", "ABBV", "MRNA", "REGN", "VRTX", "ISRG", "BSX", "SYK"
    ],
    "Defense": [
        "LMT", "RTX", "NOC", "GD", "LHX", "AVAV", "AXON"
    ],
    "Financials": [
        "GS", "MS", "V", "MA", "HOOD", "SOFI", "NU"
    ],
    "Materials": [
        "RGLD", "NEM", "GOLD", "FCX", "SCCO", "ALB"
    ]
}


def load_params() -> dict:
    path = DATA_DIR / "strategy_params.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "entry_rules": {"min_score": 60, "avoid_earnings_within_days": 7,
                        "prefer_52w_range": [30, 85]},
        "exit_rules": {"stop_loss_pct": -7.0, "trailing_stop_pct": -5.0,
                       "profit_target_pct": 15.0, "max_hold_days": 15},
        "version": 1
    }


# ═══════════════════════════════════════════════════════════
# PHASE 1: QUICK MOMENTUM SCREEN (quote only)
# ═══════════════════════════════════════════════════════════

def phase1_momentum_score(q: dict) -> dict:
    """Quote verisinden hızlı momentum skoru (0-40)"""
    score = 0
    reasons = []
    px = q.get("price", 0)
    avg50 = q.get("priceAvg50", 0)
    avg200 = q.get("priceAvg200", 0)
    yh = q.get("yearHigh", 0)
    yl = q.get("yearLow", 0)

    if px <= 0 or avg200 <= 0:
        return {"score": 0, "reasons": ["No data"]}

    # 1. Above 200 DMA? (gerekli)
    if px < avg200:
        return {"score": 0, "reasons": ["Below 200 DMA"]}

    dist_200 = (px / avg200 - 1) * 100

    # 2. Above 50 DMA = trend güçlü (0-12)
    if avg50 > 0:
        dist_50 = (px / avg50 - 1) * 100
        if -3 <= dist_50 <= 3:
            # Fiyat 50 DMA civarında = pullback fırsatı
            score += 12
            reasons.append(f"Near 50DMA ({dist_50:+.1f}%) — pullback zone")
        elif dist_50 > 3:
            score += 8
            reasons.append(f"Above 50DMA (+{dist_50:.1f}%)")
        elif dist_50 > -5:
            score += 4
            reasons.append(f"Slightly below 50DMA ({dist_50:.1f}%)")
        # else: too far below, no points

    # 3. 50 DMA > 200 DMA = golden cross (0-8)
    if avg50 > avg200:
        score += 8
        reasons.append("50DMA > 200DMA (bullish structure)")

    # 4. 52-week position (0-12)
    if yh > yl:
        pos_52w = (px - yl) / (yh - yl) * 100
        if 40 <= pos_52w <= 80:
            score += 12
            reasons.append(f"52W sweet spot ({pos_52w:.0f}%)")
        elif 80 < pos_52w <= 95:
            score += 8
            reasons.append(f"Near 52W high ({pos_52w:.0f}%)")
        elif 20 <= pos_52w < 40:
            score += 4
            reasons.append(f"Low in range ({pos_52w:.0f}%)")
        elif pos_52w > 95:
            score += 2
            reasons.append(f"At 52W high ({pos_52w:.0f}%) — risky")

    # 5. Daily change momentum (0-8)
    chg = q.get("changePercentage", 0)
    if 0.5 <= chg <= 4:
        score += 8
        reasons.append(f"Positive momentum today ({chg:+.1f}%)")
    elif chg > 4:
        score += 4
        reasons.append(f"Strong move today ({chg:+.1f}%) — possible overextension")
    elif -1 <= chg < 0:
        score += 4
        reasons.append(f"Mild pullback ({chg:.1f}%)")

    return {"score": score, "reasons": reasons, "price": px,
            "dist_50": (px / avg50 - 1) * 100 if avg50 > 0 else None,
            "dist_200": dist_200,
            "pos_52w": (px - yl) / (yh - yl) * 100 if yh > yl else None}


# ═══════════════════════════════════════════════════════════
# PHASE 2: DEEP FUNDAMENTAL SCAN
# ═══════════════════════════════════════════════════════════

def phase2_fundamental_score(client: FMPClient, symbol: str) -> dict:
    """Fundamental derinlik skoru (0-60)"""
    score = 0
    reasons = []

    # ── Growth (0-25) ──
    growth = client.financial_growth(symbol, limit=4)
    if growth and len(growth) >= 2:
        latest = growth[0]
        prev = growth[1]

        rev_g = latest.get("revenueGrowth", 0) or 0
        eps_g = latest.get("epsgrowth", 0) or 0
        fcf_g = latest.get("freeCashFlowGrowth", 0) or 0

        # Revenue growth (0-10)
        if rev_g > 0.25:
            score += 10
            reasons.append(f"Revenue +{rev_g*100:.0f}% YoY 🔥")
        elif rev_g > 0.10:
            score += 7
            reasons.append(f"Revenue +{rev_g*100:.0f}% YoY")
        elif rev_g > 0:
            score += 3
            reasons.append(f"Revenue +{rev_g*100:.0f}% YoY (slow)")

        # EPS growth (0-10)
        if eps_g > 0.25:
            score += 10
            reasons.append(f"EPS +{eps_g*100:.0f}% YoY")
        elif eps_g > 0.10:
            score += 7
            reasons.append(f"EPS +{eps_g*100:.0f}% YoY")
        elif eps_g > 0:
            score += 3
            reasons.append(f"EPS +{eps_g*100:.0f}% YoY (slow)")

        # Growth acceleration (0-5)
        prev_rev = prev.get("revenueGrowth", 0) or 0
        if rev_g > prev_rev and rev_g > 0:
            score += 5
            reasons.append("Revenue growth ACCELERATING ⚡")
        elif rev_g > 0 and rev_g < prev_rev:
            reasons.append("Revenue growth decelerating")

    # ── Quality (0-20) ──
    ratios = client.ratios_ttm(symbol)
    if ratios:
        gm = ratios.get("grossProfitMarginTTM", 0) or 0
        om = ratios.get("operatingProfitMarginTTM", 0) or 0
        roe = ratios.get("returnOnEquityTTM", 0) or 0
        cr = ratios.get("currentRatioTTM", 0) or 0

        # Gross margin (0-6)
        if gm > 0.60:
            score += 6
            reasons.append(f"Excellent margins (GM: {gm*100:.0f}%)")
        elif gm > 0.40:
            score += 4
            reasons.append(f"Good margins (GM: {gm*100:.0f}%)")
        elif gm > 0.25:
            score += 2

        # Operating margin (0-5)
        if om > 0.25:
            score += 5
            reasons.append(f"High operating margin ({om*100:.0f}%)")
        elif om > 0.15:
            score += 3

        # ROE (0-5)
        if roe > 0.20:
            score += 5
            reasons.append(f"Strong ROE ({roe*100:.0f}%)")
        elif roe > 0.10:
            score += 3

        # Balance sheet (0-4)
        de = ratios.get("debtEquityRatioTTM", 0) or 0
        if de < 1.0 and cr > 1.5:
            score += 4
            reasons.append("Healthy balance sheet")
        elif cr > 1.0:
            score += 2

    # ── Valuation sanity check (0-10) ──
    if ratios:
        pe = ratios.get("peRatioTTM", 0) or 0
        peg = ratios.get("pegRatioTTM", 0) or 0
        ps = ratios.get("priceToSalesRatioTTM", 0) or 0

        # PEG ratio (0-5)
        if 0 < peg <= 1.0:
            score += 5
            reasons.append(f"Undervalued PEG ({peg:.1f})")
        elif 0 < peg <= 2.0:
            score += 3
            reasons.append(f"Fair PEG ({peg:.1f})")
        elif peg > 3.0:
            score -= 3
            reasons.append(f"Expensive PEG ({peg:.1f}) ⚠️")

        # PE sanity (0-5)
        if 0 < pe <= 25:
            score += 5
            reasons.append(f"Reasonable PE ({pe:.0f})")
        elif 0 < pe <= 40:
            score += 3
        elif pe > 60:
            score -= 2
            reasons.append(f"High PE ({pe:.0f})")

    # ── Analyst estimates (0-5) ──
    estimates = client.analyst_estimates(symbol, limit=4)
    if estimates and len(estimates) >= 2:
        # Forward revenue trend
        next_q = estimates[-1]  # nearest future quarter
        rev_avg = next_q.get("revenueAvg", 0) or 0
        if rev_avg > 0:
            score += 3
            reasons.append(f"Analyst coverage active")

    return {"score": max(0, score), "reasons": reasons}


# ═══════════════════════════════════════════════════════════
# SIGNAL BUILDER
# ═══════════════════════════════════════════════════════════

def build_signal(symbol: str, sector: str, quote_data: dict,
                 p1: dict, p2: dict, params: dict) -> dict:
    """Sinyal oluştur"""
    px = quote_data["price"]
    total_score = p1["score"] + p2["score"]
    rules = params.get("exit_rules", {})

    # Stop loss: fiyatın %'si (parametre bazlı)
    stop_pct = rules.get("stop_loss_pct", -7.0)
    stop = round(px * (1 + stop_pct / 100), 2)

    # Targets: risk/reward bazlı
    risk = px - stop
    t1 = round(px + risk * 2, 2)   # 2R
    t2 = round(px + risk * 3, 2)   # 3R

    today = datetime.now().strftime("%Y-%m-%d")
    all_reasons = p1["reasons"] + p2["reasons"]

    return {
        "id": f"SIG-{today.replace('-','')}-{symbol}",
        "symbol": symbol,
        "action": "BUY",
        "entry_price": round(px, 2),
        "stop_loss": stop,
        "target_1": t1,
        "target_2": t2,
        "trailing_stop_pct": rules.get("trailing_stop_pct", -5.0),
        "confidence": min(10, max(1, total_score // 10)),
        "score": total_score,
        "momentum_score": p1["score"],
        "fundamental_score": p2["score"],
        "max_hold_days": rules.get("max_hold_days", 15),
        "sector": sector,
        "dist_50dma": p1.get("dist_50"),
        "dist_200dma": p1.get("dist_200"),
        "pos_52w": p1.get("pos_52w"),
        "thesis": "; ".join(all_reasons[:6]),
        "generated_at": today,
        "expires_at": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "status": "ACTIVE"
    }


# ═══════════════════════════════════════════════════════════
# MAIN SCAN
# ═══════════════════════════════════════════════════════════

def run_scan(client: FMPClient, params: dict, max_signals: int = 5):
    print("=" * 65)
    print(f"🔍 SWING TRADE SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Strategy params v{params.get('version', 1)}")
    print("=" * 65)

    # ── PHASE 1: Quick momentum screen (quotes only) ──
    print(f"\n📡 PHASE 1: Momentum screen...")
    phase1_results = []
    symbol_sectors = {}

    for sector, symbols in UNIVERSE.items():
        for sym in symbols:
            symbol_sectors[sym] = sector

    all_symbols = list(symbol_sectors.keys())
    print(f"   Scanning {len(all_symbols)} symbols...")

    for i, sym in enumerate(all_symbols):
        q = client.quote(sym)
        if not q:
            continue

        p1 = phase1_momentum_score(q)
        if p1["score"] >= 8:  # Minimum momentum threshold
            phase1_results.append({
                "symbol": sym,
                "sector": symbol_sectors[sym],
                "quote": q,
                "p1": p1
            })

        if (i + 1) % 20 == 0:
            print(f"   ... {i+1}/{len(all_symbols)} scanned")

    # Sort by P1 score
    phase1_results.sort(key=lambda x: x["p1"]["score"], reverse=True)
    print(f"   ✅ {len(phase1_results)} passed momentum filter")

    # ── PHASE 2: Deep fundamental scan (top 20) ──
    top_n = min(20, len(phase1_results))
    print(f"\n🔬 PHASE 2: Fundamental deep scan (top {top_n})...")
    final_signals = []

    for item in phase1_results[:top_n]:
        sym = item["symbol"]
        print(f"   Analyzing {sym}...", end="")

        p2 = phase2_fundamental_score(client, sym)
        total = item["p1"]["score"] + p2["score"]
        print(f" P1:{item['p1']['score']} + P2:{p2['score']} = {total}")

        min_score = params.get("entry_rules", {}).get("min_score", 60)
        if total >= min_score:
            signal = build_signal(
                sym, item["sector"], item["quote"],
                item["p1"], p2, params
            )
            final_signals.append(signal)

    # Sort final
    final_signals.sort(key=lambda x: x["score"], reverse=True)

    # ── SAVE ──
    signals_out = {
        "updated_at": datetime.now().isoformat(),
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "strategy_version": params.get("version", 1),
        "total_scanned": len(all_symbols),
        "passed_momentum": len(phase1_results),
        "total_signals": len(final_signals),
        "active_signals": final_signals[:max_signals],
        "watching": [
            {"symbol": s["symbol"], "score": s["score"], "sector": s["sector"],
             "entry_price": s["entry_price"]}
            for s in final_signals[max_signals:max_signals+10]
        ],
        "recently_closed": []
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "signals.json", "w") as f:
        json.dump(signals_out, f, indent=2)

    # Append to history
    hist_path = DATA_DIR / "signal_history.json"
    history = []
    if hist_path.exists():
        with open(hist_path) as f:
            history = json.load(f)
    for sig in final_signals:
        history.append(sig)
    with open(hist_path, "w") as f:
        json.dump(history, f, indent=2)

    # ── PRINT RESULTS ──
    print(f"\n{'═' * 65}")
    print(f"🎯 TOP {min(max_signals, len(final_signals))} SİNYAL")
    print(f"{'═' * 65}")

    for i, s in enumerate(final_signals[:max_signals], 1):
        print(f"\n{'─' * 65}")
        print(f" {i}. {s['symbol']} ({s['sector']}) — Score: {s['score']}/100")
        print(f"    Entry: ${s['entry_price']:.2f} | Stop: ${s['stop_loss']:.2f} | "
              f"T1: ${s['target_1']:.2f} | T2: ${s['target_2']:.2f}")
        print(f"    50DMA: {s['dist_50dma']:+.1f}% | 200DMA: {s['dist_200dma']:+.1f}% | "
              f"52W: {s['pos_52w']:.0f}%")
        print(f"    Confidence: {s['confidence']}/10")
        print(f"    📝 {s['thesis'][:90]}")

    if final_signals[max_signals:]:
        print(f"\n📋 WATCHLIST:")
        for s in final_signals[max_signals:max_signals+5]:
            print(f"   {s['symbol']} ({s['sector']}) Score:{s['score']} ${s['entry_price']:.2f}")

    print(f"\n📡 FMP API calls: {client.call_count}")
    print(f"💾 signals.json saved → Finzora can fetch from GitHub")

    return final_signals


def main():
    parser = argparse.ArgumentParser(description="Swing Trade Scanner")
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY", ""))
    parser.add_argument("--max-signals", type=int, default=5)
    args = parser.parse_args()

    if not args.api_key:
        print("❌ FMP_API_KEY required")
        sys.exit(1)

    client = FMPClient(args.api_key)
    params = load_params()
    run_scan(client, params, args.max_signals)


if __name__ == "__main__":
    main()
