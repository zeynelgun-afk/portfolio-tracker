#!/usr/bin/env python3
"""
Momentum Scanner — Production (Aggressive)
- Raw momentum scoring (3M×0.40 + 6M×0.35 + 12M×0.25, skip last month)
- Top 5 holdings, weekly rebalance
- No regime filter — always fully invested
- 200 DMA trend filter per stock
- Min $1M avg daily volume

Output: signals.json for Finzora
"""

import json, sys, os, argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    sys.exit("pip install yfinance pandas numpy")

sys.path.insert(0, str(Path(__file__).parent))
from universe import get_full_universe

DATA_DIR = Path(__file__).parent.parent / "data"
TOP_N = 5
MIN_ADV = 1_000_000


def calc_momentum_score(close, idx):
    """Raw composite momentum — skip last 21 days"""
    if idx < 252:
        return None
    px_now = close.iloc[idx]
    px_1m = close.iloc[idx - 21]
    px_3m = close.iloc[idx - 63]
    px_6m = close.iloc[idx - 126]
    px_12m = close.iloc[idx - 252]
    if any(pd.isna(x) or x <= 0 for x in [px_1m, px_3m, px_6m, px_12m]):
        return None
    r3 = (px_1m / px_3m - 1) * 100
    r6 = (px_1m / px_6m - 1) * 100
    r12 = (px_1m / px_12m - 1) * 100
    return r3 * 0.40 + r6 * 0.35 + r12 * 0.25


def run_scan():
    ALL_SYMBOLS = get_full_universe()

    print("=" * 65)
    print(f"🚀 MOMENTUM SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Universe: {len(ALL_SYMBOLS)} | Top {TOP_N} | Raw Momentum")
    print("=" * 65)

    # Download
    print(f"\n📥 Downloading 2yr prices...")
    all_dl = ALL_SYMBOLS + ["SPY"]
    prices = yf.download(all_dl, period="2y", progress=False)
    if prices.empty:
        print("❌ No data"); return

    today = prices.index[-1]
    today_str = today.strftime('%Y-%m-%d')

    # Score all symbols
    print(f"\n🔧 Scoring {len(ALL_SYMBOLS)} symbols...")
    scores = []
    valid = 0
    above_200 = 0

    for sym in ALL_SYMBOLS:
        try:
            close = prices['Close'][sym].dropna()
            vol = prices['Volume'][sym].dropna()
            if len(close) < 260:
                continue
            valid += 1

            idx = len(close) - 1

            # 200 DMA filter
            ma200 = close.iloc[idx-200:idx].mean()
            if close.iloc[idx] < ma200:
                continue
            above_200 += 1

            # ADV filter
            if len(vol) >= 20:
                avg_vol = vol.iloc[-20:].mean()
                adv = avg_vol * close.iloc[idx]
                if adv < MIN_ADV:
                    continue

            mom = calc_momentum_score(close, idx)
            if mom is None:
                continue

            # Extra data
            px = close.iloc[idx]
            ret_1w = (px / close.iloc[idx-5] - 1) * 100 if idx >= 5 else 0
            ret_1m = (px / close.iloc[idx-21] - 1) * 100 if idx >= 21 else 0
            ret_3m = (px / close.iloc[idx-63] - 1) * 100 if idx >= 63 else 0
            high_52w = close.iloc[idx-252:idx].max()
            pct_from_high = (px / high_52w - 1) * 100

            scores.append({
                "symbol": sym,
                "score": round(mom, 2),
                "price": round(px, 2),
                "ret_1w": round(ret_1w, 1),
                "ret_1m": round(ret_1m, 1),
                "ret_3m": round(ret_3m, 1),
                "pct_from_52w_high": round(pct_from_high, 1),
            })
        except:
            continue

    scores.sort(key=lambda x: x["score"], reverse=True)

    print(f"   Valid: {valid} | Above 200 DMA: {above_200} | Scored: {len(scores)}")

    # Load current holdings
    signals_path = DATA_DIR / "signals.json"
    current_holdings = []
    if signals_path.exists():
        try:
            old = json.load(open(signals_path))
            current_holdings = [s["symbol"] for s in old.get("active_signals", [])]
        except:
            pass

    # Top N
    top = scores[:TOP_N]
    new_syms = set(s["symbol"] for s in top)
    old_syms = set(current_holdings)

    buys = new_syms - old_syms
    sells = old_syms - new_syms
    holds = new_syms & old_syms

    # Build signals
    active_signals = []
    for s in top:
        action = "HOLD" if s["symbol"] in holds else "BUY"
        active_signals.append({
            "id": f"MOM-{today_str.replace('-','')}-{s['symbol']}",
            "symbol": s["symbol"],
            "strategy": "MOMENTUM",
            "action": action,
            "entry_price": s["price"],
            "score": s["score"],
            "ret_1w": s["ret_1w"],
            "ret_1m": s["ret_1m"],
            "ret_3m": s["ret_3m"],
            "pct_from_52w_high": s["pct_from_52w_high"],
            "weight": round(100 / TOP_N, 1),
            "generated_at": today_str,
            "status": "ACTIVE"
        })

    # Watchlist (rank 6-20)
    watching = []
    for s in scores[TOP_N:20]:
        watching.append({
            "symbol": s["symbol"],
            "score": s["score"],
            "price": s["price"],
            "ret_3m": s["ret_3m"],
            "pct_from_52w_high": s["pct_from_52w_high"]
        })

    # SPY info
    spy_close = prices['Close']['SPY'].dropna()
    spy_px = spy_close.iloc[-1]
    spy_ma200 = spy_close.iloc[-200:].mean()
    spy_regime = "BULL" if spy_px > spy_ma200 else "BEAR"

    output = {
        "updated_at": datetime.now().isoformat(),
        "scan_date": today_str,
        "strategy": "momentum_aggressive",
        "strategy_version": "E1",
        "universe_size": len(ALL_SYMBOLS),
        "valid_symbols": valid,
        "above_200dma": above_200,
        "scored": len(scores),
        "total_signals": len(active_signals),
        "rebalance": "WEEKLY",
        "top_n": TOP_N,
        "market": {
            "spy_price": round(float(spy_px), 2),
            "spy_200dma": round(float(spy_ma200), 2),
            "regime": spy_regime,
            "breadth_pct": round(above_200 / valid * 100, 1) if valid > 0 else 0
        },
        "changes": {
            "buys": sorted(buys),
            "sells": sorted(sells),
            "holds": sorted(holds)
        },
        "active_signals": active_signals,
        "watching": watching,
        "recently_sold": [{"symbol": s} for s in sorted(sells)]
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(signals_path, "w") as f:
        json.dump(output, f, indent=2)

    # Signal history
    hist_path = DATA_DIR / "signal_history.json"
    history = json.load(open(hist_path)) if hist_path.exists() else []
    history.append({
        "date": today_str,
        "top5": [s["symbol"] for s in active_signals],
        "scores": {s["symbol"]: s["score"] for s in active_signals}
    })
    with open(hist_path, "w") as f:
        json.dump(history[-200:], f, indent=2)

    # Print
    print(f"\n{'═' * 65}")
    print(f"🎯 TOP {TOP_N} MOMENTUM — Haftalık Rebalance")
    print(f"{'═' * 65}")
    print(f"   SPY: ${float(spy_px):.2f} ({spy_regime}) | "
          f"Breadth: {above_200}/{valid} ({above_200/valid*100:.0f}%)")

    if buys:
        print(f"\n   🟢 YENİ AL: {', '.join(sorted(buys))}")
    if sells:
        print(f"   🔴 SAT:     {', '.join(sorted(sells))}")
    if holds:
        print(f"   ⚪ TUT:     {', '.join(sorted(holds))}")

    for i, s in enumerate(active_signals, 1):
        print(f"\n{'─' * 65}")
        print(f" {i}. {s['symbol']} — Mom Score: {s['score']:.1f}  [{s['action']}]")
        print(f"    Price: ${s['entry_price']:.2f} | "
              f"1W: {s['ret_1w']:+.1f}% | 1M: {s['ret_1m']:+.1f}% | 3M: {s['ret_3m']:+.1f}%")
        print(f"    From 52W High: {s['pct_from_52w_high']:+.1f}% | Weight: {s['weight']}%")

    print(f"\n📋 WATCHLIST (6-20):")
    for w in watching[:10]:
        print(f"   {w['symbol']:>5} Mom:{w['score']:>6.1f} ${w['price']:>8.2f} "
              f"3M:{w['ret_3m']:>+6.1f}% Hi:{w['pct_from_52w_high']:>+5.1f}%")

    print(f"\n💾 signals.json saved")
    return output


if __name__ == "__main__":
    run_scan()
