#!/usr/bin/env python3
"""
Trade Autopsy v2 — Analyzes closed trades, triggers optimizer if needed.
Reads from backtest_results.json (signal_tracker output).

Usage:
    python3 autopsy.py                    # Analyze
    python3 autopsy.py --apply            # Auto-apply HIGH confidence changes
    python3 autopsy.py --report           # Generate markdown report
"""

import json, sys, argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
REPORTS_DIR = Path(__file__).parent.parent / "reports"

MIN_TRADES = 10


def load_json(f):
    p = DATA_DIR / f
    return json.load(open(p)) if p.exists() else None

def save_json(f, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(DATA_DIR / f, "w"), indent=2)


def run_autopsy(apply=False, report=False):
    results = load_json("backtest_results.json")
    if not results:
        print("📭 No closed trades yet."); return

    # Filter valid closed trades
    trades = [r for r in results if "exit" in r and "pnl_pct" in r.get("exit", {})]
    if len(trades) < 3:
        print(f"📭 Only {len(trades)} trades — need more data."); return

    params = load_json("strategy_params.json") or {}
    rules = params.get("exit_rules", {})

    print(f"{'═' * 60}")
    print(f"🔬 TRADE AUTOPSY — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"   Analyzing {len(trades)} closed trades")
    print(f"{'═' * 60}")

    # ── GENERAL STATS ──
    pnls = [t["exit"]["pnl_pct"] for t in trades]
    wins = [t for t in trades if t["exit"]["pnl_pct"] > 0]
    losses = [t for t in trades if t["exit"]["pnl_pct"] <= 0]
    win_pnls = [t["exit"]["pnl_pct"] for t in wins]
    loss_pnls = [t["exit"]["pnl_pct"] for t in losses]

    wr = len(wins) / len(trades) * 100
    avg_pnl = sum(pnls) / len(pnls)
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
    pf = abs(sum(win_pnls) / sum(loss_pnls)) if loss_pnls and sum(loss_pnls) != 0 else 99

    print(f"\n  📊 OVERVIEW")
    print(f"  Trades: {len(trades)} | WR: {wr:.1f}% | Avg: {avg_pnl:+.2f}%")
    print(f"  Avg Win: +{avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")
    print(f"  PF: {pf:.2f} | Best: {max(pnls):+.1f}% | Worst: {min(pnls):+.1f}%")

    # ── BY STRATEGY ──
    by_strat = defaultdict(list)
    for t in trades:
        by_strat[t.get("strategy", "UNKNOWN")].append(t)

    print(f"\n  📋 BY STRATEGY")
    for strat, st in by_strat.items():
        sw = [t for t in st if t["exit"]["pnl_pct"] > 0]
        sp = [t["exit"]["pnl_pct"] for t in st]
        print(f"    {strat:>10}: {len(st)} trades | WR: {len(sw)/len(st)*100:.0f}% | "
              f"Avg: {sum(sp)/len(sp):+.2f}%")

    # ── BY SECTOR ──
    by_sector = defaultdict(list)
    for t in trades:
        by_sector[t.get("sector", "?")].append(t)

    print(f"\n  🏭 BY SECTOR")
    for sec in sorted(by_sector, key=lambda s: sum(t["exit"]["pnl_pct"] for t in by_sector[s])/len(by_sector[s]), reverse=True):
        st = by_sector[sec]
        sw = [t for t in st if t["exit"]["pnl_pct"] > 0]
        sp = [t["exit"]["pnl_pct"] for t in st]
        print(f"    {sec:>15}: {len(st)} | WR: {len(sw)/len(st)*100:.0f}% | "
              f"Avg: {sum(sp)/len(sp):+.2f}%")

    # ── BY EXIT REASON ──
    by_exit = defaultdict(list)
    for t in trades:
        by_exit[t["exit"]["reason"]].append(t)

    print(f"\n  🚪 BY EXIT")
    for reason in sorted(by_exit, key=lambda r: len(by_exit[r]), reverse=True):
        st = by_exit[reason]
        sp = [t["exit"]["pnl_pct"] for t in st]
        pct = len(st) / len(trades) * 100
        print(f"    {reason:>15}: {len(st)} ({pct:.0f}%) | Avg: {sum(sp)/len(sp):+.2f}%")

    # ── MFE/MAE ──
    exc_trades = [t for t in trades if "excursion" in t]
    if exc_trades:
        mfes = [t["excursion"]["mfe_pct"] for t in exc_trades]
        maes = [t["excursion"]["mae_pct"] for t in exc_trades]
        caps = [t["excursion"]["capture_ratio"] for t in exc_trades if t["excursion"].get("capture_ratio", 0) > 0]
        print(f"\n  📐 MFE/MAE")
        print(f"    Avg MFE: +{sum(mfes)/len(mfes):.2f}% | Avg MAE: {sum(maes)/len(maes):.2f}%")
        if caps:
            print(f"    Capture: {sum(caps)/len(caps):.0f}%")

    # ═══════════════════════════════════════════════════════
    # RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════
    recommendations = []

    if len(trades) >= MIN_TRADES:
        # Trailing stop
        trail_exits = by_exit.get("TRAILING_STOP", [])
        trail_rate = len(trail_exits) / len(trades) * 100
        if trail_rate > 55:
            trail_avg = sum(t["exit"]["pnl_pct"] for t in trail_exits) / len(trail_exits)
            if trail_avg < 1.0:
                cur = rules.get("trailing_stop_pct", -7.0)
                recommendations.append({
                    "param": "trailing_stop_pct", "current": cur,
                    "suggested": round(cur - 2, 1),
                    "reason": f"Trail exits {trail_rate:.0f}% of trades, avg only {trail_avg:+.1f}%",
                    "confidence": "HIGH"
                })

        # Stop loss
        stop_exits = by_exit.get("STOP_LOSS", [])
        stop_rate = len(stop_exits) / len(trades) * 100
        if stop_rate > 30:
            cur = rules.get("stop_loss_pct", -7.0)
            recommendations.append({
                "param": "stop_loss_pct", "current": cur,
                "suggested": round(cur - 2, 1),
                "reason": f"Stop hit {stop_rate:.0f}% — too tight",
                "confidence": "HIGH" if stop_rate > 40 else "MEDIUM"
            })

        # Max hold
        timeouts = by_exit.get("TIMEOUT", [])
        if timeouts:
            to_avg = sum(t["exit"]["pnl_pct"] for t in timeouts) / len(timeouts)
            cur = rules.get("max_hold_days", 30)
            if to_avg > 2.0 and cur < 30:
                recommendations.append({
                    "param": "max_hold_days", "current": cur,
                    "suggested": min(30, cur + 5),
                    "reason": f"Timeouts avg {to_avg:+.1f}% — hold longer",
                    "confidence": "MEDIUM"
                })

        # Weak sectors
        for sec, st in by_sector.items():
            if len(st) >= 3:
                sec_avg = sum(t["exit"]["pnl_pct"] for t in st) / len(st)
                if sec_avg < -2.5:
                    recommendations.append({
                        "param": f"weak_sector:{sec}", "current": "active",
                        "suggested": "filtered",
                        "reason": f"{sec} avg {sec_avg:+.1f}% over {len(st)} trades",
                        "confidence": "MEDIUM"
                    })

        # Min score
        low = [t for t in trades if t.get("score", 100) < 55]
        if low:
            low_wr = len([t for t in low if t["exit"]["pnl_pct"] > 0]) / len(low) * 100
            if low_wr < 30:
                cur = params.get("entry_rules", {}).get("min_score", 55)
                recommendations.append({
                    "param": "min_score", "current": cur,
                    "suggested": cur + 5,
                    "reason": f"Low-score trades WR {low_wr:.0f}%",
                    "confidence": "HIGH"
                })

    if recommendations:
        print(f"\n  💡 RECOMMENDATIONS ({len(recommendations)}):")
        for r in recommendations:
            emoji = "🔴" if r["confidence"] == "HIGH" else "🟡"
            print(f"    {emoji} {r['param']}: {r['current']} → {r['suggested']}")
            print(f"       {r['reason']}")
    else:
        print(f"\n  ✅ No changes needed")

    # ── APPLY ──
    if apply and recommendations:
        applied = 0
        weak = params.get("entry_rules", {}).get("weak_sectors", [])

        for r in recommendations:
            if r["confidence"] != "HIGH":
                continue
            if r["param"] in rules:
                rules[r["param"]] = r["suggested"]
                applied += 1
            elif r["param"] == "min_score":
                params.setdefault("entry_rules", {})["min_score"] = r["suggested"]
                applied += 1
            elif r["param"].startswith("weak_sector:"):
                sec = r["param"].split(":")[1]
                if sec not in weak:
                    weak.append(sec)
                    applied += 1

        if applied:
            params.setdefault("entry_rules", {})["weak_sectors"] = weak
            params["version"] = params.get("version", 0) + 1
            params["last_autopsy"] = datetime.now().strftime("%Y-%m-%d")
            save_json("strategy_params.json", params)
            print(f"\n  ✅ Applied {applied} HIGH-confidence changes → v{params['version']}")

    # ── SAVE LESSONS ──
    lessons = {
        "date": datetime.now().isoformat(),
        "trades_analyzed": len(trades),
        "stats": {"win_rate": round(wr, 1), "avg_pnl": round(avg_pnl, 2), "profit_factor": round(pf, 2)},
        "recommendations": recommendations,
    }
    save_json("lessons_learned.json", lessons)

    # ── REPORT ──
    if report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        rpt = REPORTS_DIR / f"autopsy_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(rpt, "w") as f:
            f.write(f"# Swing Trade Autopsy — {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write(f"## Overview\n")
            f.write(f"- **Trades:** {len(trades)} | **WR:** {wr:.1f}% | **Avg PnL:** {avg_pnl:+.2f}%\n")
            f.write(f"- **Avg Win:** +{avg_win:.2f}% | **Avg Loss:** {avg_loss:.2f}% | **PF:** {pf:.2f}\n\n")

            f.write(f"## By Strategy\n")
            for strat, st in by_strat.items():
                sp = [t["exit"]["pnl_pct"] for t in st]
                sw = [p for p in sp if p > 0]
                f.write(f"- **{strat}:** {len(st)} trades, WR {len(sw)/len(st)*100:.0f}%, Avg {sum(sp)/len(sp):+.2f}%\n")

            f.write(f"\n## By Sector\n")
            for sec in sorted(by_sector, key=lambda s: sum(t["exit"]["pnl_pct"] for t in by_sector[s])/len(by_sector[s]), reverse=True):
                st = by_sector[sec]
                sp = [t["exit"]["pnl_pct"] for t in st]
                f.write(f"- **{sec}:** {len(st)} trades, Avg {sum(sp)/len(sp):+.2f}%\n")

            f.write(f"\n## By Exit Reason\n")
            for reason, st in sorted(by_exit.items(), key=lambda x: len(x[1]), reverse=True):
                sp = [t["exit"]["pnl_pct"] for t in st]
                f.write(f"- **{reason}:** {len(st)} ({len(st)/len(trades)*100:.0f}%), Avg {sum(sp)/len(sp):+.2f}%\n")

            if recommendations:
                f.write(f"\n## Recommendations\n")
                for r in recommendations:
                    f.write(f"- [{r['confidence']}] `{r['param']}`: {r['current']} → {r['suggested']} — {r['reason']}\n")

        print(f"\n  📝 Report → {rpt.name}")

    # ── CHECK: Should we trigger full re-optimization? ──
    needs_reoptim = False
    prev_stats = params.get("backtest_stats", {}) or params.get("final_stats", {})
    if prev_stats:
        prev_wr = prev_stats.get("win_rate", 0)
        prev_pf = prev_stats.get("profit_factor", 0)
        # Trigger if live performance degrades significantly
        if wr < prev_wr - 10 or (pf < 0.9 and prev_pf >= 1.0):
            needs_reoptim = True
            print(f"\n  ⚠️ Performance degraded (WR {prev_wr:.0f}%→{wr:.0f}%, PF {prev_pf:.1f}→{pf:.1f})")
            print(f"  🔄 Full re-optimization recommended!")

    # Signal to workflow
    if needs_reoptim:
        save_json("needs_reoptimization.json", {
            "trigger": "performance_degradation",
            "date": datetime.now().isoformat(),
            "live_wr": round(wr, 1), "live_pf": round(pf, 2),
            "backtest_wr": prev_stats.get("win_rate"), "backtest_pf": prev_stats.get("profit_factor")
        })

    return lessons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    run_autopsy(apply=args.apply, report=args.report)

if __name__ == "__main__":
    main()
