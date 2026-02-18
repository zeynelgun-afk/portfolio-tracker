#!/usr/bin/env python3
"""
Signal Tracker v2 — yfinance for daily prices + FMP fallback
Tracks active signals, manages exits, computes MFE/MAE.

Usage: python3 signal_tracker.py [--api-key KEY]
"""

import json, sys, os, argparse
from datetime import datetime
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    sys.exit("pip install yfinance")

DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename):
    path = DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None

def save_json(filename, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / filename, "w") as f:
        json.dump(data, f, indent=2)


def track_signals():
    signals = load_json("signals.json")
    if not signals or not signals.get("active_signals"):
        print("📭 No active signals to track.")
        return

    params = load_json("strategy_params.json") or {}
    rules = params.get("exit_rules", {
        "stop_loss_pct": -7.0, "trailing_stop_pct": -7.0,
        "max_hold_days": 30, "panic_stop_pct": -3.0
    })

    results = load_json("backtest_results.json") or []
    tracking = load_json("signal_tracking.json") or {}
    today = datetime.now().strftime("%Y-%m-%d")

    active = signals["active_signals"]
    syms = [s["symbol"] for s in active]

    # Batch download today's data
    print(f"📊 Tracking {len(active)} signals... ({today})")
    quotes = yf.download(syms, period="5d", progress=False)

    closed_this_run = []
    updated_signals = []

    for sig in active:
        sid = sig["id"]
        sym = sig["symbol"]
        entry = sig["entry_price"]
        stop = sig["stop_loss"]
        t1 = sig["target_1"]
        t2 = sig.get("target_2", t1 * 1.1)
        trail_pct = abs(sig.get("trailing_stop_pct", rules.get("trailing_stop_pct", 7.0)))
        max_days = sig.get("max_hold_days", rules.get("max_hold_days", 30))

        try:
            if len(syms) > 1:
                px = float(quotes['Close'][sym].iloc[-1])
                day_high = float(quotes['High'][sym].iloc[-1])
                day_low = float(quotes['Low'][sym].iloc[-1])
                day_open = float(quotes['Open'][sym].iloc[-1])
            else:
                px = float(quotes['Close'].iloc[-1])
                day_high = float(quotes['High'].iloc[-1])
                day_low = float(quotes['Low'].iloc[-1])
                day_open = float(quotes['Open'].iloc[-1])
        except:
            print(f"  ⚠️ {sym}: No data")
            updated_signals.append(sig)
            continue

        # Track state
        state = tracking.get(sid, {
            "max_price": entry, "min_price": entry,
            "trailing_stop": entry * (1 - trail_pct / 100),
            "days_tracked": 0, "daily_closes": []
        })

        state["days_tracked"] += 1
        if day_high > state["max_price"]:
            state["max_price"] = day_high
            state["trailing_stop"] = state["max_price"] * (1 - trail_pct / 100)
        if day_low < state["min_price"]:
            state["min_price"] = day_low

        state["daily_closes"].append({
            "date": today, "close": round(px,2),
            "high": round(day_high,2), "low": round(day_low,2)
        })

        try:
            days_held = (datetime.now() - datetime.strptime(sig["generated_at"], "%Y-%m-%d")).days
        except:
            days_held = state["days_tracked"]

        pnl_pct = (px - entry) / entry * 100
        mfe_pct = (state["max_price"] - entry) / entry * 100
        mae_pct = (state["min_price"] - entry) / entry * 100

        # Exit conditions
        exit_reason = None
        exit_price = None

        if day_low <= stop:
            exit_reason = "STOP_LOSS"; exit_price = stop
        elif state["days_tracked"] > 1 and day_low <= state["trailing_stop"]:
            exit_reason = "TRAILING_STOP"; exit_price = round(state["trailing_stop"], 2)
        elif (day_low - day_open) / day_open * 100 < rules.get("panic_stop_pct", -3.0):
            exit_reason = "PANIC_STOP"; exit_price = round(day_low, 2)
        elif day_high >= t2:
            exit_reason = "TARGET_2"; exit_price = round(t2, 2)
        elif day_high >= t1:
            exit_reason = "TARGET_1"; exit_price = round(t1, 2)
        elif days_held >= max_days:
            exit_reason = "TIMEOUT"; exit_price = round(px, 2)

        if exit_reason:
            final_pnl = (exit_price - entry) / entry * 100
            emoji = "✅" if final_pnl > 0 else "❌"
            print(f"  {emoji} {sym}: CLOSED — {exit_reason}")
            print(f"     Entry: ${entry:.2f} → Exit: ${exit_price:.2f} ({final_pnl:+.1f}%)")
            print(f"     MFE: +{mfe_pct:.1f}% | MAE: {mae_pct:.1f}% | Days: {days_held}")

            results.append({
                **sig,
                "tracking_status": "CLOSED",
                "exit": {"date": today, "price": exit_price,
                         "reason": exit_reason, "pnl_pct": round(final_pnl, 2),
                         "days_held": days_held},
                "excursion": {"mfe_pct": round(mfe_pct, 2), "mae_pct": round(mae_pct, 2),
                              "capture_ratio": round(final_pnl/mfe_pct*100,1) if mfe_pct > 0.1 else 0}
            })
            closed_this_run.append(sig)
            if sid in tracking: del tracking[sid]
        else:
            print(f"  📈 {sym}: ${px:.2f} ({pnl_pct:+.1f}%) — Day {days_held}")
            print(f"     MFE: +{mfe_pct:.1f}% | Trail: ${state['trailing_stop']:.2f}")
            updated_signals.append(sig)
            tracking[sid] = state

    # Save
    signals["active_signals"] = updated_signals
    if closed_this_run:
        signals.setdefault("recently_closed", [])
        signals["recently_closed"] = [
            {"symbol": s["symbol"], "pnl_pct": next(
                (r["exit"]["pnl_pct"] for r in results if r["id"] == s["id"]), 0
            )} for s in closed_this_run
        ] + signals.get("recently_closed", [])[:20]
    signals["updated_at"] = datetime.now().isoformat()

    save_json("signals.json", signals)
    save_json("signal_tracking.json", tracking)
    save_json("backtest_results.json", results)

    if results:
        wins = [r for r in results if r["exit"]["pnl_pct"] > 0]
        pnls = [r["exit"]["pnl_pct"] for r in results]
        print(f"\n{'═' * 55}")
        print(f"📊 TOTAL: {len(results)} closed | "
              f"WR: {len(wins)/len(results)*100:.0f}% | "
              f"Avg: {sum(pnls)/len(pnls):+.1f}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()
    track_signals()
    check_learning_trigger()

if __name__ == "__main__":
    main()


def check_learning_trigger():
    """Yeterli veri birikince otomatik öğrenme tetikle"""
    results = load_json("backtest_results.json") or []
    params = load_json("strategy_params.json") or {}

    closed = [r for r in results if "exit" in r]
    if len(closed) < 10:
        return False

    # Son optimizasyondan beri kaç yeni trade?
    last_autopsy = params.get("last_autopsy", "2000-01-01")
    new_trades = [t for t in closed if t["exit"].get("date", "") > last_autopsy]

    if len(new_trades) >= 15:
        print(f"\n🧠 {len(new_trades)} new trades since last learning — triggering autopsy...")

        # Write trigger file for workflow
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "learning_trigger.json", "w") as f:
            json.dump({
                "triggered_at": datetime.now().isoformat(),
                "new_trades": len(new_trades),
                "total_trades": len(closed),
                "reason": "sufficient_new_data"
            }, f, indent=2)
        return True
    return False
