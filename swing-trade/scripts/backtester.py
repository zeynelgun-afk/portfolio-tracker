#!/usr/bin/env python3
"""
Historical Backtester — yfinance (daily prices/technicals) + FMP (fundamentals)
Simulates the scanner daily from 2024-01-02 to today.
Tracks every signal, calculates MFE/MAE, runs autopsy, optimizes params.

Usage: python3 backtester.py --api-key FMP_KEY [--start 2024-01-02] [--top 5]
"""

import json, sys, os, argparse, math
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from fmp_client import FMPClient

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("pip install yfinance pandas numpy")
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "data"
REPORT_DIR = Path(__file__).parent.parent / "reports"

# ═══════════════════════════════════════════════════════════
# UNIVERSE
# ═══════════════════════════════════════════════════════════
UNIVERSE = {
    "Technology": [
        "NVDA","AMD","AVGO","MRVL","ANET","CRWD","PANW","NOW",
        "DDOG","NET","PLTR","DELL","SMCI","VRT","COIN",
        "ADBE","CRM","ORCL","MSFT","GOOGL","META","AMZN","AAPL",
        "TSM","QCOM","MU","LRCX","AMAT","ARM"
    ],
    "Communication": ["NFLX","DIS","SPOT","RBLX","TTWO","TTD","ROKU"],
    "Energy": ["VST","CEG","CCJ","NRG","GEV","ETN","PWR","FSLR","NEE","SM","FCX","SCCO"],
    "Healthcare": ["LLY","ABBV","MRNA","REGN","VRTX","ISRG","BSX","SYK"],
    "Defense": ["LMT","RTX","NOC","GD","LHX","AVAV","AXON"],
    "Financials": ["GS","MS","V","MA","HOOD","SOFI","NU"],
    "Materials": ["RGLD","NEM","GOLD","ALB"]
}

SYMBOL_SECTOR = {}
ALL_SYMBOLS = []
for sec, syms in UNIVERSE.items():
    for s in syms:
        if s not in SYMBOL_SECTOR:
            SYMBOL_SECTOR[s] = sec
            ALL_SYMBOLS.append(s)


# ═══════════════════════════════════════════════════════════
# TECHNICAL INDICATORS (vectorized)
# ═══════════════════════════════════════════════════════════

def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(series, fast)
    ema_slow = calc_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_bb(series, period=20, std_dev=2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    bandwidth = ((upper - lower) / mid * 100).fillna(0)
    return upper, mid, lower, bandwidth

def calc_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def add_technicals(df):
    """DataFrame'e tüm teknik göstergeleri ekle (her sembol için)"""
    c = df['Close']
    h = df['High']
    l = df['Low']
    v = df['Volume']

    df['EMA8'] = calc_ema(c, 8)
    df['EMA21'] = calc_ema(c, 21)
    df['EMA50'] = calc_ema(c, 50)
    df['EMA200'] = calc_ema(c, 200)
    df['RSI'] = calc_rsi(c)
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = calc_macd(c)
    df['BB_Upper'], df['BB_Mid'], df['BB_Lower'], df['BB_BW'] = calc_bb(c)
    df['ATR'] = calc_atr(h, l, c)
    df['ATR_pct'] = df['ATR'] / c * 100
    df['Vol_SMA20'] = v.rolling(20).mean()
    df['Vol_Ratio'] = v / df['Vol_SMA20'].replace(0, 1)
    df['High_52w'] = h.rolling(252).max()
    df['Low_52w'] = l.rolling(252).min()
    df['Range_10d'] = (h.rolling(10).max() - l.rolling(10).min()) / c * 100

    return df


# ═══════════════════════════════════════════════════════════
# FUNDAMENTAL DATA (FMP - quarterly, cached)
# ═══════════════════════════════════════════════════════════

def fetch_fundamentals(client: FMPClient) -> dict:
    """Her hisse için çeyreklik fundamental veri çek"""
    fund = {}
    print(f"\n📊 Fetching fundamentals for {len(ALL_SYMBOLS)} symbols...")

    for i, sym in enumerate(ALL_SYMBOLS):
        if (i + 1) % 15 == 0:
            print(f"   ... {i+1}/{len(ALL_SYMBOLS)}")

        fg = client.financial_growth(sym, limit=8)
        ratios = client.ratios_ttm(sym)

        if not fg:
            continue

        fund[sym] = {
            "growth_quarters": [],
            "ratios": ratios or {}
        }

        for q in fg:
            fund[sym]["growth_quarters"].append({
                "date": q["date"],
                "rev_growth": q.get("revenueGrowth", 0) or 0,
                "eps_growth": q.get("epsgrowth", 0) or 0,
                "fcf_growth": q.get("freeCashFlowGrowth", 0) or 0,
                "op_income_growth": q.get("operatingIncomeGrowth", 0) or 0,
            })

    print(f"   ✅ Got fundamentals for {len(fund)} symbols")
    return fund


def get_fundamental_score(sym: str, date: str, fund_data: dict) -> tuple:
    """Belirli tarihte fundamental skor (o tarihe kadar olan en son çeyrek)"""
    if sym not in fund_data:
        return 0, []

    info = fund_data[sym]
    reasons = []
    score = 0

    # En son çeyrek (tarihe göre)
    quarters = [q for q in info["growth_quarters"] if q["date"] <= date]
    if not quarters:
        return 0, []

    latest = quarters[0]  # Zaten tarih sıralı (en yeniden)
    prev = quarters[1] if len(quarters) > 1 else None

    rg = latest["rev_growth"]
    eg = latest["eps_growth"]

    # Revenue growth (0-10)
    if rg > 0.25:
        score += 10; reasons.append(f"Rev +{rg*100:.0f}% 🔥")
    elif rg > 0.10:
        score += 7; reasons.append(f"Rev +{rg*100:.0f}%")
    elif rg > 0:
        score += 3; reasons.append(f"Rev +{rg*100:.0f}%")

    # EPS growth (0-10)
    if eg > 0.25:
        score += 10; reasons.append(f"EPS +{eg*100:.0f}%")
    elif eg > 0.10:
        score += 7; reasons.append(f"EPS +{eg*100:.0f}%")
    elif eg > 0:
        score += 3

    # Acceleration (0-5)
    if prev:
        if rg > prev["rev_growth"] and rg > 0:
            score += 5; reasons.append("Accelerating ⚡")

    # Ratios
    ratios = info.get("ratios", {})
    gm = ratios.get("grossProfitMarginTTM", 0) or 0
    om = ratios.get("operatingProfitMarginTTM", 0) or 0
    peg = ratios.get("pegRatioTTM", 0) or 0

    if gm > 0.60:
        score += 5; reasons.append(f"GM {gm*100:.0f}%")
    elif gm > 0.40:
        score += 3

    if om > 0.25:
        score += 4

    if 0 < peg <= 1.0:
        score += 5; reasons.append(f"PEG {peg:.1f}")
    elif 0 < peg <= 2.0:
        score += 3
    elif peg > 3.0:
        score -= 3; reasons.append(f"Expensive PEG {peg:.1f}")

    return max(0, score), reasons


# ═══════════════════════════════════════════════════════════
# SCORING ENGINE
# ═══════════════════════════════════════════════════════════

def score_pullback(row, params) -> tuple:
    """Pullback stratejisi skoru (0-50)"""
    score = 0
    reasons = []
    c = row['Close']

    if pd.isna(row.get('EMA200')) or c < row['EMA200']:
        return 0, ["Below 200 DMA"]

    # EMA stack (0-12)
    if row['EMA8'] > row['EMA21'] > row['EMA50'] > row['EMA200']:
        score += 12; reasons.append("EMA stack bullish")
    elif row['EMA50'] > row['EMA200']:
        score += 6; reasons.append("50>200 bullish")

    # Pullback to EMA21 or EMA50 (0-12)
    if row['EMA21'] > 0:
        dist21 = (c / row['EMA21'] - 1) * 100
        if -3 <= dist21 <= 1:
            score += 12; reasons.append(f"Pullback to EMA21 ({dist21:+.1f}%)")
        elif -5 <= dist21 < -3:
            score += 6; reasons.append(f"Deep pullback ({dist21:+.1f}%)")
    if score < 12 and row['EMA50'] > 0:
        dist50 = (c / row['EMA50'] - 1) * 100
        if -3 <= dist50 <= 2:
            score += 10; reasons.append(f"Near EMA50 ({dist50:+.1f}%)")

    # RSI sweet spot (0-10)
    rsi = row.get('RSI', 50)
    if 30 <= rsi <= 45:
        score += 10; reasons.append(f"RSI oversold zone ({rsi:.0f})")
    elif 45 < rsi <= 60:
        score += 6; reasons.append(f"RSI neutral ({rsi:.0f})")
    elif rsi > 75:
        score -= 5; reasons.append(f"RSI overbought ({rsi:.0f})")

    # MACD (0-8)
    if row.get('MACD_Hist', 0) > 0:
        score += 8; reasons.append("MACD positive")
    elif row.get('MACD', 0) > row.get('MACD_Signal', 0):
        score += 4

    # Low volume pullback (0-8)
    vr = row.get('Vol_Ratio', 1)
    if 0.3 < vr < 0.8:
        score += 8; reasons.append(f"Low vol pullback ({vr:.1f}x)")

    return max(0, score), reasons


def score_breakout(row, params) -> tuple:
    """Breakout stratejisi skoru (0-50)"""
    score = 0
    reasons = []
    c = row['Close']

    if pd.isna(row.get('EMA200')) or c < row['EMA200']:
        return 0, ["Below 200 DMA"]

    # Tight consolidation (0-12)
    range_10d = row.get('Range_10d', 99)
    if range_10d <= 6:
        score += 12; reasons.append(f"Tight range ({range_10d:.1f}%)")
    elif range_10d <= 10:
        score += 6; reasons.append(f"Moderate range ({range_10d:.1f}%)")

    # Bollinger squeeze (0-10)
    bb_bw = row.get('BB_BW', 99)
    if bb_bw < 8:
        score += 10; reasons.append(f"BB squeeze ({bb_bw:.1f}%)")
    elif bb_bw < 12:
        score += 5

    # Near/above BB upper (0-8)
    if row.get('BB_Upper', 0) > 0:
        dist_bb = (c / row['BB_Upper'] - 1) * 100
        if -2 <= dist_bb <= 2:
            score += 8; reasons.append("Near BB upper")

    # Volume surge (0-10)
    vr = row.get('Vol_Ratio', 1)
    if vr > 2.0:
        score += 10; reasons.append(f"Volume surge ({vr:.1f}x) 🔥")
    elif vr > 1.5:
        score += 6; reasons.append(f"Above avg volume ({vr:.1f}x)")

    # RSI > 50 (0-5)
    rsi = row.get('RSI', 50)
    if rsi > 55:
        score += 5

    # MACD positive (0-5)
    if row.get('MACD_Hist', 0) > 0:
        score += 5

    return max(0, score), reasons


# ═══════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════

def run_backtest(client: FMPClient, start_date: str, top_n: int = 5, params: dict = None):
    if params is None:
        params = {
            "entry_rules": {"min_score": 55},
            "exit_rules": {
                "stop_loss_pct": -7.0,
                "trailing_stop_pct": -5.0,
                "max_hold_days": 15,
                "panic_stop_pct": -3.0
            }
        }

    rules = params["exit_rules"]
    min_score = params["entry_rules"]["min_score"]

    print("=" * 70)
    print(f"📈 SWING TRADE BACKTESTER")
    print(f"   Period: {start_date} → today")
    print(f"   Universe: {len(ALL_SYMBOLS)} stocks")
    print(f"   Params: stop={rules['stop_loss_pct']}% trail={rules['trailing_stop_pct']}% "
          f"max_days={rules['max_hold_days']} min_score={min_score}")
    print("=" * 70)

    # ── 1. FETCH PRICES ──
    print(f"\n📥 Downloading daily prices from yfinance...")
    prices = yf.download(ALL_SYMBOLS, start=start_date, progress=False)
    if prices.empty:
        print("❌ No price data")
        return

    trading_days = prices.index.tolist()
    print(f"   ✅ {len(trading_days)} trading days loaded")

    # ── 2. COMPUTE TECHNICALS ──
    print(f"\n🔧 Computing technicals for each symbol...")
    sym_data = {}
    for sym in ALL_SYMBOLS:
        try:
            df = pd.DataFrame({
                'Close': prices['Close'][sym],
                'High': prices['High'][sym],
                'Low': prices['Low'][sym],
                'Open': prices['Open'][sym],
                'Volume': prices['Volume'][sym]
            }).dropna()
            if len(df) < 210:
                continue
            df = add_technicals(df)
            sym_data[sym] = df
        except:
            continue
    print(f"   ✅ {len(sym_data)} symbols have sufficient data")

    # ── 3. FETCH FUNDAMENTALS ──
    fund_data = fetch_fundamentals(client)

    # ── 4. SIMULATE DAY BY DAY ──
    # Start after 200 days (need EMA200)
    sim_start_idx = 210
    sim_days = trading_days[sim_start_idx:]

    print(f"\n🚀 Simulating {len(sim_days)} trading days...")
    print(f"   Sim start: {sim_days[0].strftime('%Y-%m-%d')}")

    # State
    open_positions = {}   # symbol -> position dict
    closed_trades = []
    daily_pnl = []
    signals_generated = 0
    max_positions = top_n
    scan_interval = 5  # Her 5 günde tarama yap (weekly scan)

    for day_idx, day in enumerate(sim_days):
        day_str = day.strftime('%Y-%m-%d')

        # ── UPDATE OPEN POSITIONS ──
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
            pnl_pct = (px - entry) / entry * 100

            # Exit conditions
            exit_reason = None
            exit_price = None

            if day_low <= pos["stop_loss"]:
                exit_reason = "STOP_LOSS"
                exit_price = pos["stop_loss"]
            elif pos["days_held"] > 1 and day_low <= pos["trailing_stop"]:
                exit_reason = "TRAILING_STOP"
                exit_price = round(pos["trailing_stop"], 2)
            elif day_high >= pos["target_2"]:
                exit_reason = "TARGET_2"
                exit_price = round(pos["target_2"], 2)
            elif day_high >= pos["target_1"]:
                exit_reason = "TARGET_1"
                exit_price = round(pos["target_1"], 2)
            elif pos["days_held"] >= rules["max_hold_days"]:
                exit_reason = "TIMEOUT"
                exit_price = round(px, 2)

            if exit_reason:
                final_pnl = (exit_price - entry) / entry * 100
                mfe = (pos["max_price"] - entry) / entry * 100
                mae = (pos["min_price"] - entry) / entry * 100

                # Post-exit: 5 gün sonra fiyat
                post_5d = None
                future_idx = sym_data[sym].index.get_loc(day)
                if future_idx + 5 < len(sym_data[sym]):
                    post_px = sym_data[sym].iloc[future_idx + 5]['Close']
                    post_5d = round((post_px - exit_price) / exit_price * 100, 2)

                closed_trades.append({
                    "symbol": sym,
                    "sector": SYMBOL_SECTOR.get(sym, "?"),
                    "strategy": pos["strategy"],
                    "entry_date": pos["entry_date"],
                    "entry_price": entry,
                    "exit_date": day_str,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl_pct": round(final_pnl, 2),
                    "days_held": pos["days_held"],
                    "mfe_pct": round(mfe, 2),
                    "mae_pct": round(mae, 2),
                    "capture_ratio": round(final_pnl / mfe * 100, 1) if mfe > 0.1 else 0,
                    "score": pos["score"],
                    "post_exit_5d_pct": post_5d,
                    "left_on_table": round(mfe - final_pnl, 2) if mfe > final_pnl else 0
                })
                to_close.append(sym)

        for sym in to_close:
            del open_positions[sym]

        # ── SCAN FOR NEW SIGNALS (every scan_interval days) ──
        if day_idx % scan_interval != 0:
            continue
        if len(open_positions) >= max_positions:
            continue

        candidates = []
        for sym in sym_data:
            if sym in open_positions:
                continue
            if day not in sym_data[sym].index:
                continue

            row = sym_data[sym].loc[day]
            if pd.isna(row.get('EMA200')):
                continue

            # Score both strategies
            pb_score, pb_reasons = score_pullback(row, params)
            bo_score, bo_reasons = score_breakout(row, params)

            # Pick better strategy
            if pb_score >= bo_score:
                tech_score, tech_reasons, strategy = pb_score, pb_reasons, "PULLBACK"
            else:
                tech_score, tech_reasons, strategy = bo_score, bo_reasons, "BREAKOUT"

            if tech_score < 15:
                continue

            # Fundamental score
            fund_score, fund_reasons = get_fundamental_score(sym, day_str, fund_data)
            total = tech_score + fund_score

            if total >= min_score:
                candidates.append({
                    "symbol": sym,
                    "strategy": strategy,
                    "score": total,
                    "tech_score": tech_score,
                    "fund_score": fund_score,
                    "reasons": tech_reasons + fund_reasons,
                    "close": row['Close'],
                    "atr_pct": row.get('ATR_pct', 2.0)
                })

        # Top candidates
        candidates.sort(key=lambda x: x["score"], reverse=True)
        slots = max_positions - len(open_positions)

        for cand in candidates[:slots]:
            sym = cand["symbol"]
            px = cand["close"]
            atr_pct = cand["atr_pct"] if not pd.isna(cand["atr_pct"]) else 3.0

            stop_pct = rules["stop_loss_pct"]
            stop = round(px * (1 + stop_pct / 100), 2)
            risk = px - stop
            t1 = round(px + risk * 2, 2)
            t2 = round(px + risk * 3, 2)

            open_positions[sym] = {
                "entry_date": day_str,
                "entry_price": round(px, 2),
                "stop_loss": stop,
                "target_1": t1,
                "target_2": t2,
                "trailing_stop": px * (1 + rules["trailing_stop_pct"] / 100),
                "max_price": px,
                "min_price": px,
                "days_held": 0,
                "strategy": cand["strategy"],
                "score": cand["score"],
            }
            signals_generated += 1

        # Progress
        if (day_idx + 1) % 50 == 0:
            wins = [t for t in closed_trades if t["pnl_pct"] > 0]
            wr = len(wins)/len(closed_trades)*100 if closed_trades else 0
            print(f"   Day {day_idx+1}/{len(sim_days)} ({day_str}) | "
                  f"Trades: {len(closed_trades)} | WR: {wr:.0f}% | Open: {len(open_positions)}")

    # Close remaining open positions at last price
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

    # ═══════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════
    print(f"\n{'═' * 70}")
    print(f"📊 BACKTEST RESULTS")
    print(f"{'═' * 70}")

    if not closed_trades:
        print("No trades generated!")
        return

    wins = [t for t in closed_trades if t["pnl_pct"] > 0]
    losses = [t for t in closed_trades if t["pnl_pct"] <= 0]
    pnls = [t["pnl_pct"] for t in closed_trades]
    win_pnls = [t["pnl_pct"] for t in wins]
    loss_pnls = [t["pnl_pct"] for t in losses]

    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
    expectancy = (len(wins)/len(closed_trades) * avg_win +
                  len(losses)/len(closed_trades) * avg_loss) if closed_trades else 0
    profit_factor = abs(sum(win_pnls) / sum(loss_pnls)) if loss_pnls and sum(loss_pnls) != 0 else 99

    print(f"\n  Total trades:    {len(closed_trades)}")
    print(f"  Signals scanned: {signals_generated}")
    print(f"  Win rate:        {len(wins)/len(closed_trades)*100:.1f}%")
    print(f"  Avg PnL:         {sum(pnls)/len(pnls):+.2f}%")
    print(f"  Avg Win:         +{avg_win:.2f}%")
    print(f"  Avg Loss:        {avg_loss:.2f}%")
    print(f"  Best trade:      {max(pnls):+.2f}%")
    print(f"  Worst trade:     {min(pnls):+.2f}%")
    print(f"  Profit factor:   {profit_factor:.2f}")
    print(f"  Expectancy:      {expectancy:+.2f}% per trade")
    print(f"  Cum. return:     {sum(pnls):+.1f}% (sum of all trades)")

    # Strategy breakdown
    print(f"\n{'─' * 50}")
    print(f"  📋 BY STRATEGY:")
    for strat in ["PULLBACK", "BREAKOUT"]:
        st = [t for t in closed_trades if t["strategy"] == strat]
        if not st: continue
        sw = [t for t in st if t["pnl_pct"] > 0]
        sp = [t["pnl_pct"] for t in st]
        print(f"    {strat:>10}: {len(st)} trades | WR: {len(sw)/len(st)*100:.0f}% | "
              f"Avg: {sum(sp)/len(sp):+.2f}%")

    # Sector breakdown
    print(f"\n{'─' * 50}")
    print(f"  🏭 BY SECTOR:")
    by_sector = defaultdict(list)
    for t in closed_trades:
        by_sector[t["sector"]].append(t["pnl_pct"])
    for sec in sorted(by_sector, key=lambda s: sum(by_sector[s])/len(by_sector[s]), reverse=True):
        pnl_list = by_sector[sec]
        w = len([p for p in pnl_list if p > 0])
        print(f"    {sec:>15}: {len(pnl_list)} trades | WR: {w/len(pnl_list)*100:.0f}% | "
              f"Avg: {sum(pnl_list)/len(pnl_list):+.2f}%")

    # Exit reason breakdown
    print(f"\n{'─' * 50}")
    print(f"  🚪 BY EXIT REASON:")
    by_exit = defaultdict(list)
    for t in closed_trades:
        by_exit[t["exit_reason"]].append(t["pnl_pct"])
    for reason in sorted(by_exit, key=lambda r: len(by_exit[r]), reverse=True):
        pnl_list = by_exit[reason]
        print(f"    {reason:>15}: {len(pnl_list)} ({len(pnl_list)/len(closed_trades)*100:.0f}%) | "
              f"Avg: {sum(pnl_list)/len(pnl_list):+.2f}%")

    # MFE/MAE analysis
    print(f"\n{'─' * 50}")
    print(f"  📐 MFE/MAE ANALYSIS:")
    mfes = [t["mfe_pct"] for t in closed_trades]
    maes = [t["mae_pct"] for t in closed_trades]
    caps = [t["capture_ratio"] for t in closed_trades if t["capture_ratio"] > 0]
    lots = [t["left_on_table"] for t in closed_trades if t["left_on_table"] > 0]
    print(f"    Avg MFE:           +{sum(mfes)/len(mfes):.2f}%")
    print(f"    Avg MAE:           {sum(maes)/len(maes):.2f}%")
    if caps:
        print(f"    Avg Capture ratio: {sum(caps)/len(caps):.0f}%")
    if lots:
        print(f"    Avg Left on table: +{sum(lots)/len(lots):.2f}%")

    # Post-exit analysis
    post = [t for t in closed_trades if t["post_exit_5d_pct"] is not None]
    if post:
        post_vals = [t["post_exit_5d_pct"] for t in post]
        early_exits = [t for t in post if t["post_exit_5d_pct"] > 2.0]
        print(f"\n{'─' * 50}")
        print(f"  ⏰ POST-EXIT (5 day):")
        print(f"    Avg move after exit: {sum(post_vals)/len(post_vals):+.2f}%")
        print(f"    Early exits (>2% left): {len(early_exits)}/{len(post)} "
              f"({len(early_exits)/len(post)*100:.0f}%)")

    # ═══════════════════════════════════════════════════════
    # PARAMETER OPTIMIZATION
    # ═══════════════════════════════════════════════════════
    print(f"\n{'═' * 70}")
    print(f"🧠 LESSONS LEARNED & PARAMETER RECOMMENDATIONS")
    print(f"{'═' * 70}")

    recommendations = []

    # 1. Stop loss optimization
    stop_exits = [t for t in closed_trades if t["exit_reason"] == "STOP_LOSS"]
    stop_rate = len(stop_exits) / len(closed_trades) * 100 if closed_trades else 0
    if stop_rate > 35:
        recommendations.append({
            "param": "stop_loss_pct",
            "current": rules["stop_loss_pct"],
            "suggested": rules["stop_loss_pct"] - 3,
            "reason": f"Stop hit rate too high ({stop_rate:.0f}%), widen stop",
            "confidence": "HIGH" if stop_rate > 45 else "MEDIUM"
        })
    elif stop_rate < 15 and avg_loss < -5:
        recommendations.append({
            "param": "stop_loss_pct",
            "current": rules["stop_loss_pct"],
            "suggested": rules["stop_loss_pct"] + 2,
            "reason": f"Stops rarely hit but losses large, tighten stop",
            "confidence": "MEDIUM"
        })

    # 2. Trailing stop
    trail_exits = [t for t in closed_trades if t["exit_reason"] == "TRAILING_STOP"]
    if lots and sum(lots)/len(lots) > 3.0:
        recommendations.append({
            "param": "trailing_stop_pct",
            "current": rules["trailing_stop_pct"],
            "suggested": rules["trailing_stop_pct"] - 2,
            "reason": f"Avg {sum(lots)/len(lots):.1f}% left on table, loosen trailing",
            "confidence": "HIGH"
        })

    # 3. Max hold days
    timeout_trades = [t for t in closed_trades if t["exit_reason"] == "TIMEOUT"]
    if timeout_trades:
        timeout_avg = sum(t["pnl_pct"] for t in timeout_trades) / len(timeout_trades)
        if timeout_avg < -1.0:
            recommendations.append({
                "param": "max_hold_days",
                "current": rules["max_hold_days"],
                "suggested": max(7, rules["max_hold_days"] - 5),
                "reason": f"Timeouts avg {timeout_avg:+.1f}%, reduce hold period",
                "confidence": "MEDIUM"
            })

    # 4. Min score
    low_score_trades = [t for t in closed_trades if t["score"] < 60]
    if low_score_trades:
        low_wr = len([t for t in low_score_trades if t["pnl_pct"] > 0]) / len(low_score_trades) * 100
        if low_wr < 35:
            recommendations.append({
                "param": "min_score",
                "current": min_score,
                "suggested": min_score + 10,
                "reason": f"Low-score trades WR only {low_wr:.0f}%, increase threshold",
                "confidence": "HIGH"
            })

    # 5. Sector avoid
    for sec, pnl_list in by_sector.items():
        sec_avg = sum(pnl_list) / len(pnl_list)
        if sec_avg < -3.0 and len(pnl_list) >= 3:
            recommendations.append({
                "param": f"avoid_sector_{sec}",
                "current": "enabled",
                "suggested": "disable",
                "reason": f"{sec} avg PnL {sec_avg:+.1f}% across {len(pnl_list)} trades",
                "confidence": "MEDIUM"
            })

    # 6. Strategy disable
    for strat in ["PULLBACK", "BREAKOUT"]:
        st = [t for t in closed_trades if t["strategy"] == strat]
        if st:
            strat_wr = len([t for t in st if t["pnl_pct"] > 0]) / len(st) * 100
            if strat_wr < 30 and len(st) >= 5:
                recommendations.append({
                    "param": f"strategy_{strat.lower()}",
                    "current": "enabled",
                    "suggested": "disable",
                    "reason": f"{strat} WR only {strat_wr:.0f}% ({len(st)} trades)",
                    "confidence": "HIGH" if strat_wr < 25 else "MEDIUM"
                })

    for rec in recommendations:
        emoji = "🔴" if rec["confidence"] == "HIGH" else "🟡"
        print(f"\n  {emoji} [{rec['confidence']}] {rec['param']}")
        print(f"     Current: {rec['current']} → Suggested: {rec['suggested']}")
        print(f"     Reason: {rec['reason']}")

    if not recommendations:
        print("\n  ✅ No parameter changes recommended (system performing well)")

    # ═══════════════════════════════════════════════════════
    # APPLY & SAVE
    # ═══════════════════════════════════════════════════════
    optimized_params = dict(params)
    applied = []
    for rec in recommendations:
        if rec["confidence"] == "HIGH" and not rec["param"].startswith("avoid_") and not rec["param"].startswith("strategy_"):
            if rec["param"] in optimized_params["exit_rules"]:
                optimized_params["exit_rules"][rec["param"]] = rec["suggested"]
                applied.append(rec)
            elif rec["param"] in optimized_params["entry_rules"]:
                optimized_params["entry_rules"][rec["param"]] = rec["suggested"]
                applied.append(rec)

    optimized_params["version"] = params.get("version", 0) + 1
    optimized_params["backtested_on"] = datetime.now().strftime("%Y-%m-%d")
    optimized_params["backtest_stats"] = {
        "total_trades": len(closed_trades),
        "win_rate": round(len(wins)/len(closed_trades)*100, 1),
        "avg_pnl": round(sum(pnls)/len(pnls), 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 2),
    }

    # Add sector/strategy lessons
    avoid_sectors = []
    for rec in recommendations:
        if rec["param"].startswith("avoid_sector_") and rec["confidence"] in ["HIGH","MEDIUM"]:
            avoid_sectors.append(rec["param"].replace("avoid_sector_",""))
    if avoid_sectors:
        optimized_params["entry_rules"]["weak_sectors"] = avoid_sectors

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_path = DATA_DIR / "strategy_params.json"
    with open(save_path, "w") as f:
        json.dump(optimized_params, f, indent=2)
    print(f"\n💾 Optimized params saved → strategy_params.json (v{optimized_params['version']})")

    if applied:
        print(f"   Applied {len(applied)} HIGH-confidence changes:")
        for a in applied:
            print(f"   • {a['param']}: {a['current']} → {a['suggested']}")

    # Save full backtest results
    bt_results = {
        "run_date": datetime.now().isoformat(),
        "period": f"{start_date} to {sim_days[-1].strftime('%Y-%m-%d')}",
        "params_used": params,
        "stats": optimized_params["backtest_stats"],
        "recommendations": recommendations,
        "trades": closed_trades
    }
    with open(DATA_DIR / "backtest_full.json", "w") as f:
        json.dump(bt_results, f, indent=2)

    # Top 10 trades
    print(f"\n{'═' * 70}")
    print(f"🏆 TOP 10 TRADES:")
    for t in sorted(closed_trades, key=lambda x: x["pnl_pct"], reverse=True)[:10]:
        print(f"   {t['symbol']:>5} {t['strategy']:>10} | {t['entry_date']}→{t['exit_date']} | "
              f"{t['pnl_pct']:+6.1f}% | {t['exit_reason']}")

    print(f"\n💀 WORST 5 TRADES:")
    for t in sorted(closed_trades, key=lambda x: x["pnl_pct"])[:5]:
        print(f"   {t['symbol']:>5} {t['strategy']:>10} | {t['entry_date']}→{t['exit_date']} | "
              f"{t['pnl_pct']:+6.1f}% | {t['exit_reason']}")

    print(f"\n📡 FMP API calls: {client.call_count}")

    return bt_results


def main():
    parser = argparse.ArgumentParser(description="Historical Backtester")
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY", ""))
    parser.add_argument("--start", default="2024-01-02")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    if not args.api_key:
        print("❌ FMP_API_KEY required")
        sys.exit(1)

    client = FMPClient(args.api_key)
    run_backtest(client, args.start, args.top)


if __name__ == "__main__":
    main()
