#!/usr/bin/env python3
"""
Momentum Tracker — Weekly Portfolio Rebalance
- Reads current signals.json (top 5)
- Compares with last week's holdings
- Logs all rotation trades to portfolio_log.json
- Tracks cumulative P&L
"""

import json, sys
from datetime import datetime
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    sys.exit("pip install yfinance pandas")

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent.parent / "data"


def run_track():
    signals_path = DATA_DIR / "signals.json"
    log_path = DATA_DIR / "portfolio_log.json"
    
    if not signals_path.exists():
        print("❌ No signals.json"); return

    signals = json.load(open(signals_path))
    today = signals.get("scan_date", datetime.now().strftime("%Y-%m-%d"))

    # Load portfolio log
    if log_path.exists():
        log = json.load(open(log_path))
    else:
        log = {
            "initial_capital": 100_000,
            "current_holdings": {},
            "closed_trades": [],
            "cash": 100_000,
            "history": []
        }

    current = log["current_holdings"]  # {sym: {shares, entry_price, entry_date}}
    cash = log["cash"]

    # What scanner says to hold
    new_top = {s["symbol"]: s for s in signals.get("active_signals", [])}
    buys = set(new_top.keys()) - set(current.keys())
    sells = set(current.keys()) - set(new_top.keys())
    holds = set(current.keys()) & set(new_top.keys())

    # Get current prices
    all_syms = list(set(list(current.keys()) + list(new_top.keys())))
    if not all_syms:
        print("No symbols to track"); return

    prices = yf.download(all_syms, period="5d", progress=False)
    if prices.empty:
        print("❌ No price data"); return

    def get_price(sym):
        try:
            return float(prices['Close'][sym].dropna().iloc[-1])
        except:
            return None

    # Portfolio value before rebalance
    port_value = cash
    for sym, h in current.items():
        px = get_price(sym)
        if px:
            port_value += h["shares"] * px

    print(f"{'═' * 60}")
    print(f"📊 MOMENTUM TRACKER — {today}")
    print(f"   Portfolio: ${port_value:,.0f} | Cash: ${cash:,.0f}")
    print(f"{'═' * 60}")

    # SELL
    for sym in sells:
        px = get_price(sym)
        if not px or sym not in current:
            continue
        h = current[sym]
        pnl_pct = (px - h["entry_price"]) / h["entry_price"] * 100
        pnl_dollar = h["shares"] * (px - h["entry_price"])
        cash += h["shares"] * px

        log["closed_trades"].append({
            "symbol": sym, "action": "SELL",
            "entry_date": h["entry_date"], "exit_date": today,
            "entry_price": h["entry_price"], "exit_price": round(px, 2),
            "shares": h["shares"],
            "pnl_pct": round(pnl_pct, 2),
            "pnl_dollar": round(pnl_dollar, 2),
            "reason": "ROTATION"
        })
        print(f"   🔴 SELL {sym}: ${h['entry_price']:.2f} → ${px:.2f} ({pnl_pct:+.1f}%) ${pnl_dollar:+,.0f}")
        del current[sym]

    # BUY (equal weight)
    if buys:
        alloc_per = port_value / 5  # Equal weight across 5 positions
        for sym in buys:
            px = get_price(sym)
            if not px:
                continue
            shares = int(alloc_per / px)
            if shares < 1 or shares * px > cash:
                continue
            cash -= shares * px
            current[sym] = {
                "shares": shares,
                "entry_price": round(px, 2),
                "entry_date": today
            }
            print(f"   🟢 BUY  {sym}: {shares} shares @ ${px:.2f} (${shares*px:,.0f})")

    # Current state
    final_value = cash
    print(f"\n{'─' * 60}")
    print(f"📋 PORTFÖY:")
    for sym, h in sorted(current.items()):
        px = get_price(sym)
        if px:
            pnl = (px - h["entry_price"]) / h["entry_price"] * 100
            val = h["shares"] * px
            final_value += val
            print(f"   {sym:>5}: {h['shares']} shares @ ${h['entry_price']:.2f} → ${px:.2f} ({pnl:+.1f}%) ${val:,.0f}")

    total_return = (final_value - log["initial_capital"]) / log["initial_capital"] * 100

    print(f"\n{'─' * 60}")
    print(f"   Toplam Değer:  ${final_value:,.0f}")
    print(f"   Nakit:         ${cash:,.0f}")
    print(f"   Toplam Getiri: {total_return:+.2f}%")
    print(f"   Kapalı Trade:  {len(log['closed_trades'])}")

    # Update log
    log["cash"] = round(cash, 2)
    log["current_holdings"] = current
    log["history"].append({
        "date": today,
        "portfolio_value": round(final_value, 2),
        "cash": round(cash, 2),
        "holdings": list(current.keys()),
        "return_pct": round(total_return, 2)
    })

    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n💾 portfolio_log.json saved")


if __name__ == "__main__":
    run_track()
