#!/usr/bin/env python3
"""
Multi-Pass Parameter Optimizer
Runs backtest iteratively, learns from each pass.
Pass 1: Default params → learn
Pass 2: Optimized params → learn more
...
Pass N: Converged params → final strategy

Usage: python3 optimizer.py --api-key KEY --passes 5
"""

import json, sys, os, argparse, copy
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fmp_client import FMPClient

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    sys.exit("pip install yfinance pandas numpy")

# Import backtest engine components
from universe import get_full_universe
from backtester import (
    ALL_SYMBOLS, SYMBOL_SECTOR,
    add_technicals, fetch_fundamentals,
    score_pullback, score_breakout, get_fundamental_score
)

DATA_DIR = Path(__file__).parent.parent / "data"


def run_single_pass(sym_data, fund_data, trading_days, params, pass_num):
    """Tek bir backtest pass'ı çalıştır"""
    rules = params["exit_rules"]
    min_score = params["entry_rules"]["min_score"]
    weak_sectors = params["entry_rules"].get("weak_sectors", [])
    disable_breakout = params.get("disable_breakout", False)
    max_positions = 5
    scan_interval = 5

    sim_start_idx = 210
    sim_days = trading_days[sim_start_idx:]

    open_positions = {}
    closed_trades = []
    signals_generated = 0

    for day_idx, day in enumerate(sim_days):
        day_str = day.strftime('%Y-%m-%d')

        # Update open positions
        to_close = []
        for sym, pos in open_positions.items():
            if sym not in sym_data or day not in sym_data[sym].index:
                continue

            row = sym_data[sym].loc[day]
            px = row['Close']
            day_high = row['High']
            day_low = row['Low']

            pos["days_held"] += 1
            if day_high > pos["max_price"]:
                pos["max_price"] = day_high
                pos["trailing_stop"] = pos["max_price"] * (1 + rules["trailing_stop_pct"] / 100)
            if day_low < pos["min_price"]:
                pos["min_price"] = day_low

            entry = pos["entry_price"]
            exit_reason = None
            exit_price = None

            if day_low <= pos["stop_loss"]:
                exit_reason = "STOP_LOSS"; exit_price = pos["stop_loss"]
            elif pos["days_held"] > 1 and day_low <= pos["trailing_stop"]:
                exit_reason = "TRAILING_STOP"; exit_price = round(pos["trailing_stop"], 2)
            elif day_high >= pos["target_2"]:
                exit_reason = "TARGET_2"; exit_price = round(pos["target_2"], 2)
            elif day_high >= pos["target_1"]:
                exit_reason = "TARGET_1"; exit_price = round(pos["target_1"], 2)
            elif pos["days_held"] >= rules["max_hold_days"]:
                exit_reason = "TIMEOUT"; exit_price = round(px, 2)

            if exit_reason:
                final_pnl = (exit_price - entry) / entry * 100
                mfe = (pos["max_price"] - entry) / entry * 100
                mae = (pos["min_price"] - entry) / entry * 100

                post_5d = None
                if sym in sym_data:
                    future_idx = sym_data[sym].index.get_loc(day)
                    if future_idx + 5 < len(sym_data[sym]):
                        post_px = sym_data[sym].iloc[future_idx + 5]['Close']
                        post_5d = round((post_px - exit_price) / exit_price * 100, 2)

                closed_trades.append({
                    "symbol": sym, "sector": SYMBOL_SECTOR.get(sym, "?"),
                    "strategy": pos["strategy"],
                    "entry_date": pos["entry_date"], "entry_price": entry,
                    "exit_date": day_str, "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl_pct": round(final_pnl, 2), "days_held": pos["days_held"],
                    "mfe_pct": round(mfe, 2), "mae_pct": round(mae, 2),
                    "capture_ratio": round(final_pnl / mfe * 100, 1) if mfe > 0.1 else 0,
                    "score": pos["score"],
                    "post_exit_5d_pct": post_5d,
                    "left_on_table": round(mfe - final_pnl, 2) if mfe > final_pnl else 0
                })
                to_close.append(sym)

        for sym in to_close:
            del open_positions[sym]

        # Scan
        if day_idx % scan_interval != 0 or len(open_positions) >= max_positions:
            continue

        candidates = []
        for sym in sym_data:
            if sym in open_positions or day not in sym_data[sym].index:
                continue
            if SYMBOL_SECTOR.get(sym, "") in weak_sectors:
                continue

            row = sym_data[sym].loc[day]
            if pd.isna(row.get('EMA200')):
                continue

            pb_score, pb_reasons = score_pullback(row, params)
            bo_score, bo_reasons = score_breakout(row, params)

            if disable_breakout:
                bo_score = 0

            if pb_score >= bo_score:
                tech_score, tech_reasons, strategy = pb_score, pb_reasons, "PULLBACK"
            else:
                tech_score, tech_reasons, strategy = bo_score, bo_reasons, "BREAKOUT"

            if tech_score < 15:
                continue

            fund_score, fund_reasons = get_fundamental_score(sym, day_str, fund_data)
            total = tech_score + fund_score

            if total >= min_score:
                candidates.append({
                    "symbol": sym, "strategy": strategy, "score": total,
                    "close": row['Close'], "atr_pct": row.get('ATR_pct', 2.0)
                })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        slots = max_positions - len(open_positions)

        for cand in candidates[:slots]:
            px = cand["close"]
            stop = round(px * (1 + rules["stop_loss_pct"] / 100), 2)
            risk = px - stop
            t1 = round(px + risk * 2, 2)
            t2 = round(px + risk * 3, 2)

            open_positions[cand["symbol"]] = {
                "entry_date": day_str, "entry_price": round(px, 2),
                "stop_loss": stop, "target_1": t1, "target_2": t2,
                "trailing_stop": px * (1 + rules["trailing_stop_pct"] / 100),
                "max_price": px, "min_price": px, "days_held": 0,
                "strategy": cand["strategy"], "score": cand["score"],
            }
            signals_generated += 1

    # Close remaining
    last_day = sim_days[-1]
    for sym, pos in list(open_positions.items()):
        if sym in sym_data and last_day in sym_data[sym].index:
            px = sym_data[sym].loc[last_day]['Close']
            final_pnl = (px - pos["entry_price"]) / pos["entry_price"] * 100
            mfe = (pos["max_price"] - pos["entry_price"]) / pos["entry_price"] * 100
            mae = (pos["min_price"] - pos["entry_price"]) / pos["entry_price"] * 100
            closed_trades.append({
                "symbol": sym, "sector": SYMBOL_SECTOR.get(sym, "?"),
                "strategy": pos["strategy"],
                "entry_date": pos["entry_date"], "entry_price": pos["entry_price"],
                "exit_date": last_day.strftime('%Y-%m-%d'), "exit_price": round(px, 2),
                "exit_reason": "END_OF_SIM", "pnl_pct": round(final_pnl, 2),
                "days_held": pos["days_held"],
                "mfe_pct": round(mfe, 2), "mae_pct": round(mae, 2),
                "capture_ratio": round(final_pnl / mfe * 100, 1) if mfe > 0.1 else 0,
                "score": pos["score"], "post_exit_5d_pct": None, "left_on_table": 0
            })

    return closed_trades


def analyze_and_optimize(trades, params, pass_num):
    """Trade sonuçlarını analiz et ve parametreleri optimize et"""
    if not trades:
        return params, {}

    new_params = copy.deepcopy(params)
    rules = new_params["exit_rules"]

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    pnls = [t["pnl_pct"] for t in trades]
    win_pnls = [t["pnl_pct"] for t in wins]
    loss_pnls = [t["pnl_pct"] for t in losses]

    wr = len(wins) / len(trades) * 100
    avg_pnl = sum(pnls) / len(pnls)
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
    pf = abs(sum(win_pnls) / sum(loss_pnls)) if loss_pnls and sum(loss_pnls) != 0 else 99
    expectancy = wr/100 * avg_win + (1 - wr/100) * avg_loss

    from collections import defaultdict
    by_exit = defaultdict(list)
    by_sector = defaultdict(list)
    by_strat = defaultdict(list)
    for t in trades:
        by_exit[t["exit_reason"]].append(t["pnl_pct"])
        by_sector[t["sector"]].append(t["pnl_pct"])
        by_strat[t["strategy"]].append(t["pnl_pct"])

    stats = {
        "trades": len(trades), "win_rate": round(wr, 1),
        "avg_pnl": round(avg_pnl, 2), "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2), "profit_factor": round(pf, 2),
        "expectancy": round(expectancy, 2)
    }

    changes = []

    # ── TRAILING STOP ──
    trail_exits = by_exit.get("TRAILING_STOP", [])
    trail_rate = len(trail_exits) / len(trades) * 100
    lots = [t["left_on_table"] for t in trades if t["left_on_table"] > 0]
    avg_lot = sum(lots) / len(lots) if lots else 0

    if trail_rate > 60 and avg_lot > 3.0:
        old = rules["trailing_stop_pct"]
        rules["trailing_stop_pct"] = round(old - 2, 1)
        changes.append(f"trailing_stop: {old}→{rules['trailing_stop_pct']} (trail rate {trail_rate:.0f}%, left {avg_lot:.1f}%)")

    # ── STOP LOSS ──
    stop_exits = by_exit.get("STOP_LOSS", [])
    stop_rate = len(stop_exits) / len(trades) * 100

    if stop_rate > 30:
        old = rules["stop_loss_pct"]
        rules["stop_loss_pct"] = round(old - 2, 1)
        changes.append(f"stop_loss: {old}→{rules['stop_loss_pct']} (hit rate {stop_rate:.0f}%)")
    elif stop_rate < 10 and avg_loss < -5:
        old = rules["stop_loss_pct"]
        rules["stop_loss_pct"] = round(old + 1, 1)
        changes.append(f"stop_loss: {old}→{rules['stop_loss_pct']} (rarely hit, tighten)")

    # ── MAX HOLD DAYS ──
    timeouts = by_exit.get("TIMEOUT", [])
    if timeouts:
        timeout_avg = sum(timeouts) / len(timeouts)
        if timeout_avg > 2.0:
            old = rules["max_hold_days"]
            rules["max_hold_days"] = min(30, old + 5)
            changes.append(f"max_hold: {old}→{rules['max_hold_days']} (timeout avg +{timeout_avg:.1f}%)")
        elif timeout_avg < -2.0:
            old = rules["max_hold_days"]
            rules["max_hold_days"] = max(7, old - 3)
            changes.append(f"max_hold: {old}→{rules['max_hold_days']} (timeout avg {timeout_avg:.1f}%)")

    # ── MIN SCORE ──
    low_score = [t for t in trades if t["score"] < 60]
    if low_score:
        low_wr = len([t for t in low_score if t["pnl_pct"] > 0]) / len(low_score) * 100
        if low_wr < 35:
            old = new_params["entry_rules"]["min_score"]
            new_params["entry_rules"]["min_score"] = old + 5
            changes.append(f"min_score: {old}→{new_params['entry_rules']['min_score']} (low score WR {low_wr:.0f}%)")

    # ── SECTOR FILTER ──
    weak = []
    for sec, pnl_list in by_sector.items():
        if len(pnl_list) >= 3 and sum(pnl_list)/len(pnl_list) < -2.0:
            weak.append(sec)
    if weak:
        new_params["entry_rules"]["weak_sectors"] = weak
        changes.append(f"weak_sectors: {weak}")

    # ── BREAKOUT STRATEGY ──
    bo = by_strat.get("BREAKOUT", [])
    if bo and len(bo) >= 5:
        bo_wr = len([p for p in bo if p > 0]) / len(bo) * 100
        if bo_wr < 30:
            new_params["disable_breakout"] = True
            changes.append(f"breakout disabled (WR {bo_wr:.0f}%)")

    new_params["version"] = pass_num
    return new_params, {"stats": stats, "changes": changes}


def main():
    parser = argparse.ArgumentParser(description="Multi-Pass Optimizer")
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY", ""))
    parser.add_argument("--passes", type=int, default=5)
    parser.add_argument("--start", default="2024-01-02")
    args = parser.parse_args()

    if not args.api_key:
        print("❌ FMP_API_KEY required"); sys.exit(1)

    client = FMPClient(args.api_key)

    print("=" * 70)
    print(f"🧪 MULTI-PASS PARAMETER OPTIMIZER")
    print(f"   Passes: {args.passes} | Period: {args.start} → today")
    print("=" * 70)

    # ── DATA LOAD (once) ──
    print(f"\n📥 Loading price data...")
    prices = yf.download(ALL_SYMBOLS, start=args.start, progress=False)
    trading_days = prices.index.tolist()
    print(f"   ✅ {len(trading_days)} days")

    print(f"\n🔧 Computing technicals...")
    sym_data = {}
    for sym in ALL_SYMBOLS:
        try:
            df = pd.DataFrame({
                'Close': prices['Close'][sym], 'High': prices['High'][sym],
                'Low': prices['Low'][sym], 'Open': prices['Open'][sym],
                'Volume': prices['Volume'][sym]
            }).dropna()
            if len(df) < 210: continue
            df = add_technicals(df)
            sym_data[sym] = df
        except:
            continue
    print(f"   ✅ {len(sym_data)} symbols")

    fund_data = fetch_fundamentals(client)

    # ── ITERATE ──
    params = {
        "entry_rules": {"min_score": 55, "weak_sectors": []},
        "exit_rules": {
            "stop_loss_pct": -7.0, "trailing_stop_pct": -5.0,
            "max_hold_days": 15, "panic_stop_pct": -3.0
        },
        "disable_breakout": False,
        "version": 0
    }

    all_results = []

    for p in range(1, args.passes + 1):
        print(f"\n{'═' * 70}")
        print(f"🔄 PASS {p}/{args.passes}")
        print(f"   Params: stop={params['exit_rules']['stop_loss_pct']}% "
              f"trail={params['exit_rules']['trailing_stop_pct']}% "
              f"hold={params['exit_rules']['max_hold_days']}d "
              f"min_score={params['entry_rules']['min_score']} "
              f"breakout={'OFF' if params.get('disable_breakout') else 'ON'}")
        print(f"{'═' * 70}")

        trades = run_single_pass(sym_data, fund_data, trading_days, params, p)
        params, result = analyze_and_optimize(trades, params, p)

        stats = result.get("stats", {})
        changes = result.get("changes", [])

        print(f"\n  📊 Results: {stats.get('trades',0)} trades | "
              f"WR: {stats.get('win_rate',0)}% | "
              f"Avg: {stats.get('avg_pnl',0):+.2f}% | "
              f"PF: {stats.get('profit_factor',0):.2f} | "
              f"Exp: {stats.get('expectancy',0):+.2f}%")

        if changes:
            print(f"  🔧 Changes:")
            for c in changes:
                print(f"     → {c}")
        else:
            print(f"  ✅ No changes needed — converged!")

        all_results.append({"pass": p, **result})

        if not changes:
            print(f"\n🎯 Converged at pass {p}!")
            break

    # ── FINAL SUMMARY ──
    print(f"\n{'═' * 70}")
    print(f"📈 OPTIMIZATION JOURNEY")
    print(f"{'═' * 70}")
    print(f"{'Pass':>4} | {'Trades':>6} | {'WR':>5} | {'AvgPnL':>7} | {'PF':>5} | {'Expect':>7} | Changes")
    print(f"{'─'*80}")
    for r in all_results:
        s = r.get("stats", {})
        ch = len(r.get("changes", []))
        print(f"  {r['pass']:>2}  | {s.get('trades',0):>6} | {s.get('win_rate',0):>4.1f}% | "
              f"{s.get('avg_pnl',0):>+6.2f}% | {s.get('profit_factor',0):>5.2f} | "
              f"{s.get('expectancy',0):>+6.2f}% | {ch} changes")

    # Save final params
    params["backtested_on"] = datetime.now().strftime("%Y-%m-%d")
    params["optimization_passes"] = args.passes
    params["final_stats"] = all_results[-1].get("stats", {}) if all_results else {}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "strategy_params.json", "w") as f:
        json.dump(params, f, indent=2)

    with open(DATA_DIR / "optimization_history.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n💾 Final params saved → strategy_params.json (v{params['version']})")
    print(f"💾 History saved → optimization_history.json")

    print(f"\n{'═' * 70}")
    print(f"🎯 FINAL OPTIMIZED PARAMETERS:")
    print(f"{'═' * 70}")
    print(f"  Stop loss:      {params['exit_rules']['stop_loss_pct']}%")
    print(f"  Trailing stop:  {params['exit_rules']['trailing_stop_pct']}%")
    print(f"  Max hold days:  {params['exit_rules']['max_hold_days']}")
    print(f"  Min score:      {params['entry_rules']['min_score']}")
    print(f"  Weak sectors:   {params['entry_rules'].get('weak_sectors', [])}")
    print(f"  Breakout:       {'DISABLED' if params.get('disable_breakout') else 'ENABLED'}")
    print(f"\n📡 FMP calls: {client.call_count}")


if __name__ == "__main__":
    main()
