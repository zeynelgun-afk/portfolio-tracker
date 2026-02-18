#!/usr/bin/env python3
"""
Signal Tracker — FMP Only
Checks active signals daily via FMP quotes.
Tracks: stop hit, target hit, timeout, MFE/MAE.
Feeds closed signals to autopsy engine.

Usage: python3 signal_tracker.py --api-key KEY
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


def track_signals(client: FMPClient):
    """Aktif sinyalleri kontrol et"""
    signals = load_json("signals.json")
    if not signals or not signals.get("active_signals"):
        print("📭 No active signals to track.")
        return

    results = load_json("backtest_results.json") or []
    tracking = load_json("signal_tracking.json") or {}
    today = datetime.now().strftime("%Y-%m-%d")
    closed_this_run = []
    updated_signals = []

    print(f"📊 Tracking {len(signals['active_signals'])} active signals...")
    print(f"   Date: {today}\n")

    for sig in signals["active_signals"]:
        sid = sig["id"]
        sym = sig["symbol"]
        entry = sig["entry_price"]
        stop = sig["stop_loss"]
        t1 = sig["target_1"]
        t2 = sig.get("target_2", t1 * 1.1)
        trail_pct = abs(sig.get("trailing_stop_pct", 5.0))
        max_days = sig.get("max_hold_days", 15)
        gen_date = sig["generated_at"]

        # Get current quote
        q = client.quote(sym)
        if not q:
            print(f"  ⚠️ {sym}: No quote data")
            updated_signals.append(sig)
            continue

        px = q["price"]
        day_low = q.get("dayLow", px)
        day_high = q.get("dayHigh", px)

        # Load/init tracking state
        state = tracking.get(sid, {
            "max_price": entry,
            "min_price": entry,
            "trailing_stop": entry * (1 - trail_pct / 100),
            "days_tracked": 0,
            "daily_closes": []
        })

        # Update state
        state["days_tracked"] += 1
        if day_high > state["max_price"]:
            state["max_price"] = day_high
            state["trailing_stop"] = state["max_price"] * (1 - trail_pct / 100)
        if day_low < state["min_price"]:
            state["min_price"] = day_low

        state["daily_closes"].append({"date": today, "close": px, "high": day_high, "low": day_low})

        # Days since entry
        try:
            entry_dt = datetime.strptime(gen_date, "%Y-%m-%d")
            days_held = (datetime.now() - entry_dt).days
        except:
            days_held = state["days_tracked"]

        pnl_pct = (px - entry) / entry * 100
        mfe_pct = (state["max_price"] - entry) / entry * 100
        mae_pct = (state["min_price"] - entry) / entry * 100

        # ── CHECK EXIT CONDITIONS ──
        exit_reason = None
        exit_price = None

        # Stop loss
        if day_low <= stop:
            exit_reason = "STOP_LOSS"
            exit_price = stop

        # Trailing stop
        elif day_low <= state["trailing_stop"] and days_held > 1:
            exit_reason = "TRAILING_STOP"
            exit_price = round(state["trailing_stop"], 2)

        # Panic stop (>3% intraday drop)
        elif q.get("open") and ((day_low - q["open"]) / q["open"] * 100) < -3.0:
            exit_reason = "PANIC_STOP"
            exit_price = round(day_low, 2)

        # Target 2
        elif day_high >= t2:
            exit_reason = "TARGET_2"
            exit_price = round(t2, 2)

        # Target 1
        elif day_high >= t1:
            exit_reason = "TARGET_1"
            exit_price = round(t1, 2)

        # Timeout
        elif days_held >= max_days:
            exit_reason = "TIMEOUT"
            exit_price = round(px, 2)

        # ── RESULT ──
        if exit_reason:
            final_pnl = (exit_price - entry) / entry * 100
            emoji = "✅" if final_pnl > 0 else "❌"
            print(f"  {emoji} {sym}: CLOSED — {exit_reason}")
            print(f"     Entry: ${entry:.2f} → Exit: ${exit_price:.2f} ({final_pnl:+.1f}%)")
            print(f"     MFE: +{mfe_pct:.1f}% | MAE: {mae_pct:.1f}% | Days: {days_held}")

            closed_result = {
                **sig,
                "tracking_status": "CLOSED",
                "exit": {
                    "date": today,
                    "price": exit_price,
                    "reason": exit_reason,
                    "pnl_pct": round(final_pnl, 2),
                    "days_held": days_held
                },
                "excursion": {
                    "mfe_pct": round(mfe_pct, 2),
                    "mae_pct": round(mae_pct, 2),
                    "mfe_price": round(state["max_price"], 2),
                    "mae_price": round(state["min_price"], 2),
                    "capture_ratio": round(final_pnl / mfe_pct * 100, 1) if mfe_pct > 0 else 0
                },
                "alternative_scenarios": {}
            }

            # Alt scenarios: different stop levels
            for alt in [-5, -7, -10]:
                alt_stop = entry * (1 + alt / 100)
                hit = False
                for dc in state["daily_closes"]:
                    if dc["low"] <= alt_stop:
                        hit = True
                        break
                closed_result["alternative_scenarios"][f"stop_{abs(alt)}pct"] = \
                    round(alt, 1) if hit else round(final_pnl, 2)

            results.append(closed_result)
            closed_this_run.append(closed_result)

            # Remove from tracking
            if sid in tracking:
                del tracking[sid]
        else:
            print(f"  📈 {sym}: ${px:.2f} ({pnl_pct:+.1f}%) — Day {days_held}")
            print(f"     MFE: +{mfe_pct:.1f}% | Trail stop: ${state['trailing_stop']:.2f}")
            updated_signals.append(sig)
            tracking[sid] = state

    # Save updated signals
    signals["active_signals"] = updated_signals
    if closed_this_run:
        signals.setdefault("recently_closed", [])
        signals["recently_closed"] = closed_this_run + signals["recently_closed"][:20]
    signals["updated_at"] = datetime.now().isoformat()
    save_json("signals.json", signals)
    save_json("signal_tracking.json", tracking)
    save_json("backtest_results.json", results)

    # Summary
    if results:
        wins = [r for r in results if r["exit"]["pnl_pct"] > 0]
        pnls = [r["exit"]["pnl_pct"] for r in results]
        print(f"\n{'═' * 55}")
        print(f"📊 CUMULATIVE: {len(results)} closed | "
              f"WR: {len(wins)/len(results)*100:.0f}% | "
              f"Avg: {sum(pnls)/len(pnls):+.1f}%")
        print(f"{'═' * 55}")

    print(f"\n📡 FMP calls: {client.call_count}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY", ""))
    args = parser.parse_args()

    if not args.api_key:
        print("❌ FMP_API_KEY required")
        sys.exit(1)

    client = FMPClient(args.api_key)
    track_signals(client)


if __name__ == "__main__":
    main()
