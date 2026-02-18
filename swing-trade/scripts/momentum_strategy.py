#!/usr/bin/env python3
"""
Momentum Rotation Strategy
- Always fully invested (no idle cash)
- Monthly rebalance: buy top N strongest stocks
- Dual timeframe momentum (3M + 6M + 12M weighted)
- Market regime filter: SPY > 200 DMA → risk-on, else cash
- Hold winners, cut losers

Backtest: 2024-01-02 → today
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

# ═══════════════════════════════════════════════════════════
# MOMENTUM SCORING
# ═══════════════════════════════════════════════════════════

def calc_momentum_score(close_series, date_idx):
    """
    Composite momentum: weighted average of multiple timeframes
    Excludes last 1 month (mean reversion skip-month effect)
    """
    if date_idx < 252:
        return None

    px_now = close_series.iloc[date_idx]
    
    # Skip most recent month (21 trading days) - avoids mean reversion
    px_1m = close_series.iloc[date_idx - 21] if date_idx >= 21 else px_now

    px_3m = close_series.iloc[date_idx - 63] if date_idx >= 63 else None
    px_6m = close_series.iloc[date_idx - 126] if date_idx >= 126 else None
    px_12m = close_series.iloc[date_idx - 252] if date_idx >= 252 else None

    if any(x is None or pd.isna(x) or x <= 0 for x in [px_3m, px_6m, px_12m]):
        return None

    # Returns (skip-month adjusted)
    ret_3m = (px_1m / px_3m - 1) * 100
    ret_6m = (px_1m / px_6m - 1) * 100
    ret_12m = (px_1m / px_12m - 1) * 100

    # Weighted composite (recent momentum heavier)
    score = ret_3m * 0.40 + ret_6m * 0.35 + ret_12m * 0.25

    return score


def calc_volatility(close_series, date_idx, period=63):
    """Annualized volatility over period"""
    if date_idx < period + 1:
        return None
    returns = close_series.iloc[date_idx-period:date_idx].pct_change().dropna()
    if len(returns) < period - 5:
        return None
    return returns.std() * np.sqrt(252) * 100


def calc_risk_adjusted_momentum(mom_score, volatility):
    """Momentum / Volatility = risk-adjusted momentum"""
    if mom_score is None or volatility is None or volatility < 1:
        return None
    return mom_score / volatility


# ═══════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════

def run_momentum_backtest(start="2024-01-02", top_n=10, rebal_freq=21,
                           use_regime=True, risk_adjust=True, min_adv=1_000_000):
    ALL_SYMBOLS = get_full_universe()

    print("=" * 70)
    print(f"🚀 MOMENTUM ROTATION STRATEGY")
    print(f"   Period: {start} → today")
    print(f"   Universe: {len(ALL_SYMBOLS)} stocks")
    print(f"   Top holdings: {top_n} | Rebalance: every {rebal_freq} days")
    print(f"   Regime filter: {'ON' if use_regime else 'OFF'}")
    print(f"   Risk-adjusted: {'ON' if risk_adjust else 'OFF'}")
    print("=" * 70)

    # Download data
    print(f"\n📥 Downloading prices...")
    t0 = time.time()
    all_dl = ALL_SYMBOLS + ["SPY"]
    prices = yf.download(all_dl, start=start, progress=False)
    print(f"   ✅ {len(prices)} days in {time.time()-t0:.0f}s")

    if prices.empty:
        print("❌ No data"); return

    trading_days = prices.index.tolist()

    # Extract close/volume per symbol
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

    # SPY for regime filter
    spy_close = prices['Close']['SPY'].dropna()
    spy_200dma = spy_close.rolling(200).mean()

    print(f"   {len(sym_close)} symbols with 1yr+ data")

    # ═══════════════════════════════════════════════════════
    # SIMULATE
    # ═══════════════════════════════════════════════════════
    INITIAL = 100_000
    capital = INITIAL
    holdings = {}  # symbol -> {"shares": n, "entry_price": p, "entry_date": d}
    
    daily_equity = []
    all_trades = []
    rebalances = []
    days_in_cash = 0

    sim_start = 260  # Need 252 days for 12M momentum + buffer
    sim_days = trading_days[sim_start:]

    print(f"\n🚀 Simulating {len(sim_days)} days ({sim_days[0].strftime('%Y-%m-%d')} → {sim_days[-1].strftime('%Y-%m-%d')})")

    last_rebal = -999

    for day_idx_global in range(sim_start, len(trading_days)):
        day = trading_days[day_idx_global]
        day_str = day.strftime('%Y-%m-%d')
        days_since_rebal = day_idx_global - last_rebal

        # Portfolio value
        port_value = capital
        for sym, h in holdings.items():
            if sym in sym_close and day in sym_close[sym].index:
                port_value += h["shares"] * sym_close[sym].loc[day]

        daily_equity.append({"date": day_str, "value": round(port_value, 2)})

        # ── REBALANCE? ──
        if days_since_rebal < rebal_freq:
            continue

        last_rebal = day_idx_global

        # ── REGIME CHECK ──
        regime_ok = True
        if use_regime and day in spy_200dma.index:
            spy_px = spy_close.loc[day] if day in spy_close.index else None
            spy_ma = spy_200dma.loc[day] if day in spy_200dma.index else None
            if spy_px is not None and spy_ma is not None and not pd.isna(spy_ma):
                regime_ok = spy_px > spy_ma

        if not regime_ok:
            # Sell everything → cash
            for sym, h in list(holdings.items()):
                if sym in sym_close and day in sym_close[sym].index:
                    exit_px = sym_close[sym].loc[day]
                    pnl_pct = (exit_px - h["entry_price"]) / h["entry_price"] * 100
                    capital += h["shares"] * exit_px
                    all_trades.append({
                        "symbol": sym, "entry_date": h["entry_date"], "exit_date": day_str,
                        "entry_price": round(h["entry_price"], 2),
                        "exit_price": round(exit_px, 2),
                        "pnl_pct": round(pnl_pct, 2),
                        "pnl_dollar": round(h["shares"] * (exit_px - h["entry_price"]), 2),
                        "exit_reason": "REGIME_OFF",
                        "days_held": (day - pd.Timestamp(h["entry_date"])).days
                    })
            holdings = {}
            days_in_cash += rebal_freq
            rebalances.append({"date": day_str, "action": "ALL_CASH", "regime": "BEAR"})
            continue

        # ── SCORE ALL SYMBOLS ──
        scores = []
        for sym in sym_close:
            if day not in sym_close[sym].index:
                continue

            # Find index in this symbol's series
            try:
                idx = sym_close[sym].index.get_loc(day)
            except:
                continue

            # Minimum average daily volume
            if sym in sym_vol and day in sym_vol[sym].index:
                vol_idx = sym_vol[sym].index.get_loc(day)
                if vol_idx >= 20:
                    avg_vol = sym_vol[sym].iloc[vol_idx-20:vol_idx].mean()
                    avg_px = sym_close[sym].iloc[idx]
                    adv = avg_vol * avg_px
                    if adv < min_adv:
                        continue

            # Above 200 DMA? (trend filter)
            if idx >= 200:
                ma200 = sym_close[sym].iloc[idx-200:idx].mean()
                if sym_close[sym].iloc[idx] < ma200:
                    continue

            mom = calc_momentum_score(sym_close[sym], idx)
            if mom is None:
                continue

            if risk_adjust:
                vol = calc_volatility(sym_close[sym], idx)
                ram = calc_risk_adjusted_momentum(mom, vol)
                if ram is None:
                    continue
                scores.append({"symbol": sym, "score": ram, "mom": mom, "vol": vol})
            else:
                scores.append({"symbol": sym, "score": mom, "mom": mom, "vol": None})

        scores.sort(key=lambda x: x["score"], reverse=True)
        target_syms = [s["symbol"] for s in scores[:top_n]]
        target_set = set(target_syms)

        # ── SELL holdings not in target ──
        for sym in list(holdings.keys()):
            if sym not in target_set:
                if sym in sym_close and day in sym_close[sym].index:
                    exit_px = sym_close[sym].loc[day]
                    h = holdings[sym]
                    pnl_pct = (exit_px - h["entry_price"]) / h["entry_price"] * 100
                    capital += h["shares"] * exit_px
                    all_trades.append({
                        "symbol": sym, "entry_date": h["entry_date"], "exit_date": day_str,
                        "entry_price": round(h["entry_price"], 2),
                        "exit_price": round(exit_px, 2),
                        "pnl_pct": round(pnl_pct, 2),
                        "pnl_dollar": round(h["shares"] * (exit_px - h["entry_price"]), 2),
                        "exit_reason": "ROTATION",
                        "days_held": (day - pd.Timestamp(h["entry_date"])).days
                    })
                    del holdings[sym]

        # ── BUY new targets (equal weight) ──
        current_value = capital
        for sym in holdings:
            if sym in sym_close and day in sym_close[sym].index:
                current_value += holdings[sym]["shares"] * sym_close[sym].loc[day]

        target_alloc = current_value / top_n

        for sym in target_syms:
            if sym in holdings:
                continue  # Already holding
            if sym not in sym_close or day not in sym_close[sym].index:
                continue

            px = sym_close[sym].loc[day]
            shares = int(target_alloc / px)
            if shares < 1 or shares * px > capital:
                continue

            capital -= shares * px
            holdings[sym] = {
                "shares": shares,
                "entry_price": px,
                "entry_date": day_str
            }

        rebalances.append({
            "date": day_str,
            "action": "REBALANCE",
            "holdings": list(holdings.keys()),
            "top_5_scores": [{"sym": s["symbol"], "score": round(s["score"], 2), 
                              "mom": round(s["mom"], 1)} for s in scores[:5]],
            "regime": "BULL"
        })

        # Progress
        if len(rebalances) % 5 == 0:
            wr = len([t for t in all_trades if t["pnl_pct"] > 0]) / len(all_trades) * 100 if all_trades else 0
            print(f"   Rebal #{len(rebalances)} ({day_str}) | "
                  f"Equity: ${port_value:,.0f} | Trades: {len(all_trades)} | WR: {wr:.0f}%")

    # Close remaining
    last_day = sim_days[-1]
    final_value = capital
    for sym, h in holdings.items():
        if sym in sym_close and last_day in sym_close[sym].index:
            exit_px = sym_close[sym].loc[last_day]
            pnl_pct = (exit_px - h["entry_price"]) / h["entry_price"] * 100
            final_value += h["shares"] * exit_px
            all_trades.append({
                "symbol": sym, "entry_date": h["entry_date"],
                "exit_date": last_day.strftime('%Y-%m-%d'),
                "entry_price": round(h["entry_price"], 2),
                "exit_price": round(exit_px, 2),
                "pnl_pct": round(pnl_pct, 2),
                "pnl_dollar": round(h["shares"] * (exit_px - h["entry_price"]), 2),
                "exit_reason": "END_OF_SIM",
                "days_held": (last_day - pd.Timestamp(h["entry_date"])).days
            })

    # ═══════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════
    total_return = (final_value - INITIAL) / INITIAL * 100
    equity_vals = [e["value"] for e in daily_equity]
    peak = equity_vals[0]
    max_dd = 0
    for v in equity_vals:
        peak = max(peak, v)
        dd = (v - peak) / peak * 100
        max_dd = min(max_dd, dd)

    sim_months = len(set(e["date"][:7] for e in daily_equity))
    annual_return = total_return * (12 / max(1, sim_months))

    wins = [t for t in all_trades if t["pnl_pct"] > 0]
    losses = [t for t in all_trades if t["pnl_pct"] <= 0]
    pnls = [t["pnl_pct"] for t in all_trades]

    print(f"\n{'═' * 70}")
    print(f"💰 MOMENTUM STRATEGY PERFORMANSI")
    print(f"{'═' * 70}")
    print(f"\n  Başlangıç:          ${INITIAL:>12,}")
    print(f"  Final:              ${final_value:>12,.0f}")
    print(f"  Net Kâr/Zarar:      ${final_value-INITIAL:>+12,.0f}")
    print(f"  Toplam Getiri:      {total_return:>+11.2f}%")
    print(f"  Yıllık Getiri:      {annual_return:>+11.2f}% (tahmini)")
    print(f"  Max Drawdown:       {max_dd:>11.2f}%")
    print(f"  Süre:               {sim_months} ay")
    print(f"  Rebalance sayısı:   {len(rebalances)}")
    print(f"  Nakit gün sayısı:   {days_in_cash}")

    print(f"\n{'─' * 70}")
    print(f"📊 TRADE İSTATİSTİKLERİ")
    print(f"{'─' * 70}")
    print(f"  Toplam trade:       {len(all_trades)}")
    if all_trades:
        print(f"  Kazanan:            {len(wins)} ({len(wins)/len(all_trades)*100:.1f}%)")
        avg_win = sum(t["pnl_pct"] for t in wins)/len(wins) if wins else 0
        avg_loss = sum(t["pnl_pct"] for t in losses)/len(losses) if losses else 0
        w_dol = sum(t["pnl_dollar"] for t in wins)
        l_dol = sum(t["pnl_dollar"] for t in losses)
        pf = abs(w_dol / l_dol) if l_dol != 0 else 99
        print(f"  Ort. Kazanç:        +{avg_win:.2f}%")
        print(f"  Ort. Kayıp:         {avg_loss:.2f}%")
        print(f"  Profit Factor:      {pf:.2f}")
        print(f"  En İyi:             {max(pnls):+.2f}%")
        print(f"  En Kötü:            {min(pnls):+.2f}%")
        print(f"  Ort. Hold:          {sum(t['days_held'] for t in all_trades)/len(all_trades):.0f} gün")

    # Monthly
    print(f"\n{'─' * 70}")
    print(f"📅 AYLIK PERFORMANS")
    print(f"{'─' * 70}")
    months_eq = defaultdict(lambda: {"start": 0, "end": 0})
    for e in daily_equity:
        m = e["date"][:7]
        if months_eq[m]["start"] == 0:
            months_eq[m]["start"] = e["value"]
        months_eq[m]["end"] = e["value"]

    print(f"  {'Ay':>8} | {'Başlangıç':>12} | {'Bitiş':>12} | {'Getiri':>8}")
    print(f"  {'─'*55}")
    for m in sorted(months_eq.keys()):
        d = months_eq[m]
        if d["start"] == 0: continue
        ret = (d["end"] - d["start"]) / d["start"] * 100
        emoji = "🟢" if ret > 1 else "🔴" if ret < -1 else "⚪"
        print(f"  {m:>8} | ${d['start']:>11,.0f} | ${d['end']:>11,.0f} | {ret:>+7.2f}% {emoji}")

    # SPY benchmark
    print(f"\n{'─' * 70}")
    print(f"📈 vs BENCHMARK")
    print(f"{'─' * 70}")
    try:
        sim_start_date = sim_days[0].strftime('%Y-%m-%d')
        sim_end_date = sim_days[-1].strftime('%Y-%m-%d')
        
        spy_s = spy_close.loc[sim_days[0]] if sim_days[0] in spy_close.index else None
        spy_e = spy_close.loc[sim_days[-1]] if sim_days[-1] in spy_close.index else None
        if spy_s and spy_e:
            spy_ret = (spy_e - spy_s) / spy_s * 100
            alpha = total_return - spy_ret
            print(f"  SPY:      {spy_ret:+.2f}%")
            print(f"  Sistem:   {total_return:+.2f}%")
            print(f"  ALPHA:    {alpha:+.2f}% {'🏆' if alpha > 0 else '❌'}")
    except Exception as e:
        print(f"  Benchmark error: {e}")

    # Top trades
    print(f"\n{'─' * 70}")
    print(f"🏆 EN İYİ 10 TRADE")
    for t in sorted(all_trades, key=lambda x: x["pnl_dollar"], reverse=True)[:10]:
        print(f"  {t['symbol']:>5} | {t['entry_date']}→{t['exit_date']} | "
              f"{t['pnl_pct']:+6.1f}% | ${t['pnl_dollar']:>+8,.0f} | {t['days_held']}d | {t['exit_reason']}")

    print(f"\n💀 EN KÖTÜ 5 TRADE")
    for t in sorted(all_trades, key=lambda x: x["pnl_dollar"])[:5]:
        print(f"  {t['symbol']:>5} | {t['entry_date']}→{t['exit_date']} | "
              f"{t['pnl_pct']:+6.1f}% | ${t['pnl_dollar']:>+8,.0f} | {t['days_held']}d | {t['exit_reason']}")

    # Most traded symbols
    print(f"\n{'─' * 70}")
    print(f"📋 EN ÇOK İŞLEM YAPILAN HİSSELER")
    sym_stats = defaultdict(lambda: {"count": 0, "total_pnl": 0, "wins": 0})
    for t in all_trades:
        sym_stats[t["symbol"]]["count"] += 1
        sym_stats[t["symbol"]]["total_pnl"] += t["pnl_dollar"]
        if t["pnl_pct"] > 0:
            sym_stats[t["symbol"]]["wins"] += 1

    for sym in sorted(sym_stats, key=lambda s: sym_stats[s]["total_pnl"], reverse=True)[:15]:
        s = sym_stats[sym]
        print(f"  {sym:>5}: {s['count']} trade | WR: {s['wins']/s['count']*100:.0f}% | "
              f"Toplam: ${s['total_pnl']:>+8,.0f}")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "strategy": "momentum_rotation",
        "run_date": datetime.now().isoformat(),
        "params": {"top_n": top_n, "rebal_freq": rebal_freq,
                    "use_regime": use_regime, "risk_adjust": risk_adjust},
        "performance": {
            "initial": INITIAL, "final": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "annual_return_pct": round(annual_return, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "total_trades": len(all_trades),
            "win_rate": round(len(wins)/len(all_trades)*100, 1) if all_trades else 0,
        },
        "daily_equity": daily_equity,
        "trades": all_trades,
        "rebalances": rebalances
    }
    with open(DATA_DIR / "momentum_backtest.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 momentum_backtest.json saved")

    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-01-02")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--rebal", type=int, default=21, help="Rebalance frequency in trading days")
    parser.add_argument("--no-regime", action="store_true")
    parser.add_argument("--no-risk-adjust", action="store_true")
    args = parser.parse_args()

    run_momentum_backtest(
        start=args.start, top_n=args.top, rebal_freq=args.rebal,
        use_regime=not args.no_regime, risk_adjust=not args.no_risk_adjust
    )


if __name__ == "__main__":
    main()
