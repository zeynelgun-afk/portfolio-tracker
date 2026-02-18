#!/usr/bin/env python3
"""
Momentum Signal System — Per-Stock Basis
Her sinyal bağımsız bir trade. Portföy yönetimi yok.
- Haftalık scan: top N momentum hissesi
- Entry: sinyal günü kapanış
- Exit: listeden düştüğü hafta kapanış
- Her trade bağımsız P&L
"""

import json, sys, time, argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    sys.exit("pip install yfinance pandas numpy")

sys.path.insert(0, str(Path(__file__).parent))
from universe import get_full_universe

DATA_DIR = Path(__file__).parent.parent / "data"


def calc_momentum(close, idx):
    if idx < 252: return None
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


def run_backtest(start="2024-01-02", top_n=5, rebal_freq=5):
    ALL_SYMBOLS = get_full_universe()

    print("=" * 70)
    print(f"📊 MOMENTUM SİNYAL SİSTEMİ — Hisse Bazlı Backtest")
    print(f"   Period: {start} → today")
    print(f"   Universe: {len(ALL_SYMBOLS)} | Top {top_n} | Rebal: {rebal_freq}d")
    print("=" * 70)

    print(f"\n📥 Downloading prices...")
    t0 = time.time()
    prices = yf.download(ALL_SYMBOLS + ["SPY"], start=start, progress=False)
    print(f"   ✅ {len(prices)} days in {time.time()-t0:.0f}s")

    trading_days = prices.index.tolist()

    sym_close = {}
    sym_vol = {}
    for sym in ALL_SYMBOLS:
        try:
            c = prices['Close'][sym].dropna()
            v = prices['Volume'][sym].dropna()
            if len(c) > 252:
                sym_close[sym] = c
                sym_vol[sym] = v
        except:
            continue

    spy_close = prices['Close']['SPY'].dropna()
    print(f"   {len(sym_close)} symbols ready")

    # ═══════════════════════════════════════════════════════
    # SIMULATE — each stock independently
    # ═══════════════════════════════════════════════════════
    sim_start = 260
    all_trades = []         # completed trades
    open_signals = {}       # sym -> {entry_price, entry_date, entry_score}
    weekly_snapshots = []

    last_rebal = -999

    for day_idx in range(sim_start, len(trading_days)):
        day = trading_days[day_idx]
        day_str = day.strftime('%Y-%m-%d')

        if day_idx - last_rebal < rebal_freq:
            continue
        last_rebal = day_idx

        # Score all
        scores = []
        for sym in sym_close:
            if day not in sym_close[sym].index:
                continue
            try:
                idx = sym_close[sym].index.get_loc(day)
            except:
                continue

            if idx < 252: continue

            # 200 DMA
            ma200 = sym_close[sym].iloc[idx-200:idx].mean()
            if sym_close[sym].iloc[idx] < ma200:
                continue

            # ADV
            if sym in sym_vol and day in sym_vol[sym].index:
                vol_idx = sym_vol[sym].index.get_loc(day)
                if vol_idx >= 20:
                    avg_vol = sym_vol[sym].iloc[vol_idx-20:vol_idx].mean()
                    if avg_vol * sym_close[sym].iloc[idx] < 1_000_000:
                        continue

            mom = calc_momentum(sym_close[sym], idx)
            if mom is not None:
                scores.append({"symbol": sym, "score": mom, "price": float(sym_close[sym].iloc[idx])})

        scores.sort(key=lambda x: x["score"], reverse=True)
        top_set = set(s["symbol"] for s in scores[:top_n])

        # Close signals not in top anymore
        for sym in list(open_signals.keys()):
            if sym not in top_set:
                if sym in sym_close and day in sym_close[sym].index:
                    exit_px = float(sym_close[sym].loc[day])
                    sig = open_signals[sym]
                    pnl = (exit_px - sig["entry_price"]) / sig["entry_price"] * 100
                    days_held = (day - pd.Timestamp(sig["entry_date"])).days

                    all_trades.append({
                        "symbol": sym,
                        "entry_date": sig["entry_date"],
                        "exit_date": day_str,
                        "entry_price": round(sig["entry_price"], 2),
                        "exit_price": round(exit_px, 2),
                        "pnl_pct": round(pnl, 2),
                        "days_held": days_held,
                        "entry_score": round(sig["entry_score"], 1)
                    })
                del open_signals[sym]

        # Open new signals
        for s in scores[:top_n]:
            if s["symbol"] not in open_signals:
                open_signals[s["symbol"]] = {
                    "entry_price": s["price"],
                    "entry_date": day_str,
                    "entry_score": s["score"]
                }

        weekly_snapshots.append({
            "date": day_str,
            "top5": [s["symbol"] for s in scores[:top_n]],
            "open_trades": len(open_signals)
        })

        if len(weekly_snapshots) % 10 == 0:
            completed = len(all_trades)
            wr = len([t for t in all_trades if t["pnl_pct"] > 0]) / completed * 100 if completed else 0
            avg = sum(t["pnl_pct"] for t in all_trades) / completed if completed else 0
            print(f"   Week {len(weekly_snapshots)} ({day_str}) | "
                  f"Trades: {completed} | WR: {wr:.0f}% | Avg: {avg:+.1f}%")

    # Close remaining
    last_day = trading_days[-1]
    last_str = last_day.strftime('%Y-%m-%d')
    for sym, sig in open_signals.items():
        if sym in sym_close and last_day in sym_close[sym].index:
            exit_px = float(sym_close[sym].loc[last_day])
            pnl = (exit_px - sig["entry_price"]) / sig["entry_price"] * 100
            days_held = (last_day - pd.Timestamp(sig["entry_date"])).days
            all_trades.append({
                "symbol": sym, "entry_date": sig["entry_date"], "exit_date": last_str,
                "entry_price": round(sig["entry_price"], 2), "exit_price": round(exit_px, 2),
                "pnl_pct": round(pnl, 2), "days_held": days_held,
                "entry_score": round(sig["entry_score"], 1)
            })

    # ═══════════════════════════════════════════════════════
    # RESULTS — Per Trade Analysis
    # ═══════════════════════════════════════════════════════
    if not all_trades:
        print("No trades!"); return

    pnls = [t["pnl_pct"] for t in all_trades]
    wins = [t for t in all_trades if t["pnl_pct"] > 0]
    losses = [t for t in all_trades if t["pnl_pct"] <= 0]
    avg_pnl = sum(pnls) / len(pnls)
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    total_gain = sum(t["pnl_pct"] for t in wins)
    total_loss = sum(t["pnl_pct"] for t in losses)
    pf = abs(total_gain / total_loss) if total_loss != 0 else 99
    avg_days = sum(t["days_held"] for t in all_trades) / len(all_trades)

    # Cumulative return (compounded)
    cumulative = 1.0
    for t in sorted(all_trades, key=lambda x: x["entry_date"]):
        cumulative *= (1 + t["pnl_pct"] / 100)
    compound_return = (cumulative - 1) * 100

    # Monthly P&L
    monthly = defaultdict(list)
    for t in all_trades:
        m = t["exit_date"][:7]
        monthly[m].append(t["pnl_pct"])

    # SPY benchmark (same period)
    sim_start_date = weekly_snapshots[0]["date"] if weekly_snapshots else start
    sim_end_date = last_str
    try:
        spy_s = float(spy_close.loc[pd.Timestamp(sim_start_date)])
        spy_e = float(spy_close.loc[last_day])
        spy_ret = (spy_e - spy_s) / spy_s * 100
    except:
        spy_ret = 0

    sim_months = len(set(t["exit_date"][:7] for t in all_trades))

    print(f"\n{'═' * 70}")
    print(f"📊 HİSSE BAZLI PERFORMANS")
    print(f"{'═' * 70}")
    print(f"  Dönem:              {sim_start_date} → {sim_end_date} ({sim_months} ay)")
    print(f"  Toplam trade:       {len(all_trades)}")
    print(f"  Kazanan:            {len(wins)} ({len(wins)/len(all_trades)*100:.1f}%)")
    print(f"  Kaybeden:           {len(losses)} ({len(losses)/len(all_trades)*100:.1f}%)")

    print(f"\n{'─' * 70}")
    print(f"  Ort. Getiri/Trade:  {avg_pnl:>+8.2f}%")
    print(f"  Ort. Kazanç:        {avg_win:>+8.2f}%")
    print(f"  Ort. Kayıp:         {avg_loss:>+8.2f}%")
    print(f"  En İyi:             {max(pnls):>+8.2f}%")
    print(f"  En Kötü:            {min(pnls):>+8.2f}%")
    print(f"  Medyan:             {sorted(pnls)[len(pnls)//2]:>+8.2f}%")
    print(f"  Profit Factor:      {pf:>8.2f}")
    print(f"  Ort. Tutma Süresi:  {avg_days:>7.0f} gün")

    print(f"\n{'─' * 70}")
    print(f"  Toplam Kazanç:      {total_gain:>+8.1f}% ({len(wins)} trade)")
    print(f"  Toplam Kayıp:       {total_loss:>+8.1f}% ({len(losses)} trade)")
    print(f"  Net Toplam:         {sum(pnls):>+8.1f}%")
    print(f"  Bileşik Getiri:     {compound_return:>+8.1f}%")

    print(f"\n{'─' * 70}")
    print(f"  SPY ({sim_start_date}→{sim_end_date}): {spy_ret:+.1f}%")
    print(f"  Ort. trade getirisi × trade sayısı büyük resmi gösterir")

    # Monthly breakdown
    print(f"\n{'═' * 70}")
    print(f"📅 AYLIK TRADE PERFORMANSI")
    print(f"{'═' * 70}")
    print(f"  {'Ay':>8} | {'Trade':>5} | {'WR':>5} | {'Ort.':>8} | {'Toplam':>8} | {'En İyi':>8} | {'En Kötü':>8}")
    print(f"  {'─'*70}")

    for m in sorted(monthly.keys()):
        trades_m = monthly[m]
        w = len([p for p in trades_m if p > 0])
        wr = w / len(trades_m) * 100
        avg = sum(trades_m) / len(trades_m)
        total = sum(trades_m)
        best = max(trades_m)
        worst = min(trades_m)
        emoji = "🟢" if avg > 1 else "🔴" if avg < -1 else "⚪"
        print(f"  {m:>8} | {len(trades_m):>5} | {wr:>4.0f}% | {avg:>+7.1f}% | {total:>+7.1f}% | {best:>+7.1f}% | {worst:>+7.1f}% {emoji}")

    # By symbol — most profitable
    print(f"\n{'═' * 70}")
    print(f"🏆 HİSSE BAZLI TOPLAM PERFORMANS")
    print(f"{'═' * 70}")
    sym_stats = defaultdict(lambda: {"trades": [], "total": 0, "wins": 0})
    for t in all_trades:
        sym_stats[t["symbol"]]["trades"].append(t)
        sym_stats[t["symbol"]]["total"] += t["pnl_pct"]
        if t["pnl_pct"] > 0:
            sym_stats[t["symbol"]]["wins"] += 1

    sorted_syms = sorted(sym_stats.items(), key=lambda x: x[1]["total"], reverse=True)

    print(f"  {'Hisse':>6} | {'Trade':>5} | {'WR':>5} | {'Ort.':>8} | {'Toplam':>8} | {'En İyi':>8}")
    print(f"  {'─'*60}")
    for sym, s in sorted_syms[:20]:
        n = len(s["trades"])
        wr = s["wins"] / n * 100
        avg = s["total"] / n
        best = max(t["pnl_pct"] for t in s["trades"])
        emoji = "🟢" if s["total"] > 10 else "🔴" if s["total"] < -10 else "⚪"
        print(f"  {sym:>6} | {n:>5} | {wr:>4.0f}% | {avg:>+7.1f}% | {s['total']:>+7.1f}% | {best:>+7.1f}% {emoji}")

    print(f"\n  ... en kötüler:")
    for sym, s in sorted_syms[-10:]:
        n = len(s["trades"])
        wr = s["wins"] / n * 100
        avg = s["total"] / n
        worst = min(t["pnl_pct"] for t in s["trades"])
        print(f"  {sym:>6} | {n:>5} | {wr:>4.0f}% | {avg:>+7.1f}% | {s['total']:>+7.1f}% | {worst:>+7.1f}% 🔴")

    # Top individual trades
    print(f"\n{'═' * 70}")
    print(f"🏆 EN İYİ 15 TRADE")
    print(f"{'═' * 70}")
    for t in sorted(all_trades, key=lambda x: x["pnl_pct"], reverse=True)[:15]:
        print(f"  {t['symbol']:>5} | {t['entry_date']}→{t['exit_date']} | "
              f"{t['pnl_pct']:>+7.1f}% | {t['days_held']:>3}d | Mom:{t['entry_score']:>.0f}")

    print(f"\n💀 EN KÖTÜ 10 TRADE")
    for t in sorted(all_trades, key=lambda x: x["pnl_pct"])[:10]:
        print(f"  {t['symbol']:>5} | {t['entry_date']}→{t['exit_date']} | "
              f"{t['pnl_pct']:>+7.1f}% | {t['days_held']:>3}d | Mom:{t['entry_score']:>.0f}")

    # Holding period analysis
    print(f"\n{'═' * 70}")
    print(f"📊 TUTMA SÜRESİ ANALİZİ")
    print(f"{'═' * 70}")
    brackets = [(0, 7, "≤1 hafta"), (8, 21, "1-3 hafta"), (22, 60, "1-2 ay"), (61, 999, "2+ ay")]
    for lo, hi, label in brackets:
        subset = [t for t in all_trades if lo <= t["days_held"] <= hi]
        if subset:
            avg = sum(t["pnl_pct"] for t in subset) / len(subset)
            wr = len([t for t in subset if t["pnl_pct"] > 0]) / len(subset) * 100
            print(f"  {label:>10}: {len(subset):>3} trade | WR: {wr:.0f}% | Ort: {avg:+.1f}%")

    # Score bracket analysis
    print(f"\n{'═' * 70}")
    print(f"📊 MOMENTUM SKOR ANALİZİ")
    print(f"{'═' * 70}")
    score_brackets = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 999)]
    for lo, hi in score_brackets:
        subset = [t for t in all_trades if lo <= t["entry_score"] < hi]
        if subset:
            avg = sum(t["pnl_pct"] for t in subset) / len(subset)
            wr = len([t for t in subset if t["pnl_pct"] > 0]) / len(subset) * 100
            label = f"{lo}-{hi}" if hi < 999 else f"{lo}+"
            print(f"  Score {label:>8}: {len(subset):>3} trade | WR: {wr:.0f}% | Ort: {avg:+.1f}%")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "momentum_backtest.json", "w") as f:
        json.dump({
            "strategy": "momentum_per_stock",
            "run_date": datetime.now().isoformat(),
            "period": f"{sim_start_date} to {sim_end_date}",
            "params": {"top_n": top_n, "rebal_freq": rebal_freq},
            "stats": {
                "total_trades": len(all_trades),
                "win_rate": round(len(wins)/len(all_trades)*100, 1),
                "avg_pnl": round(avg_pnl, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(pf, 2),
                "compound_return": round(compound_return, 1),
                "spy_return": round(spy_ret, 1),
                "avg_days_held": round(avg_days, 0)
            },
            "trades": all_trades
        }, f, indent=2)
    print(f"\n💾 momentum_backtest.json saved")

    return all_trades


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-01-02")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--rebal", type=int, default=5)
    args = parser.parse_args()
    run_backtest(start=args.start, top_n=args.top, rebal_freq=args.rebal)


if __name__ == "__main__":
    main()
