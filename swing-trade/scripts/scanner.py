#!/usr/bin/env python3
"""
Swing Trade Scanner v3 — Hybrid: yfinance (technicals) + FMP (fundamentals)
Uses the same scoring engine as the backtester for consistency.
Reads optimized params from strategy_params.json.

Usage: python3 scanner.py --api-key KEY [--max-signals 5]
"""

import json, sys, os, argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fmp_client import FMPClient

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    sys.exit("pip install yfinance pandas numpy")

from backtester import (
    ALL_SYMBOLS, SYMBOL_SECTOR, UNIVERSE,
    add_technicals, score_pullback, score_breakout, get_fundamental_score
)

DATA_DIR = Path(__file__).parent.parent / "data"


def load_params() -> dict:
    path = DATA_DIR / "strategy_params.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "entry_rules": {"min_score": 55, "weak_sectors": []},
        "exit_rules": {"stop_loss_pct": -7.0, "trailing_stop_pct": -7.0,
                       "max_hold_days": 30, "panic_stop_pct": -3.0},
        "disable_breakout": False, "version": 0
    }


def run_scan(client: FMPClient, params: dict, max_signals: int = 5):
    rules = params.get("exit_rules", {})
    min_score = params.get("entry_rules", {}).get("min_score", 55)
    weak_sectors = params.get("entry_rules", {}).get("weak_sectors", [])
    disable_bo = params.get("disable_breakout", False)

    print("=" * 65)
    print(f"🔍 SWING TRADE SCANNER v3 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Strategy v{params.get('version', 0)} | "
          f"stop={rules.get('stop_loss_pct',-7)}% trail={rules.get('trailing_stop_pct',-7)}% "
          f"hold={rules.get('max_hold_days',30)}d")
    if weak_sectors:
        print(f"   Avoiding: {weak_sectors}")
    print("=" * 65)

    # ── 1. YFINANCE: Daily prices + technicals ──
    scan_symbols = [s for s in ALL_SYMBOLS if SYMBOL_SECTOR.get(s,"") not in weak_sectors]
    print(f"\n📥 Downloading prices for {len(scan_symbols)} symbols...")
    prices = yf.download(scan_symbols, period="1y", progress=False)
    if prices.empty:
        print("❌ No data"); return []

    sym_data = {}
    for sym in scan_symbols:
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
    print(f"   ✅ {len(sym_data)} symbols ready")

    # ── 2. TECHNICAL SCORING (today's data) ──
    print(f"\n🔧 Phase 1: Technical scoring...")
    today = prices.index[-1]
    today_str = today.strftime('%Y-%m-%d')
    candidates = []

    for sym, df in sym_data.items():
        if today not in df.index: continue
        row = df.loc[today]
        if pd.isna(row.get('EMA200')): continue

        pb_score, pb_reasons = score_pullback(row, params)
        bo_score, bo_reasons = score_breakout(row, params)

        if disable_bo:
            bo_score = 0

        if pb_score >= bo_score:
            tech_score, tech_reasons, strategy = pb_score, pb_reasons, "PULLBACK"
        else:
            tech_score, tech_reasons, strategy = bo_score, bo_reasons, "BREAKOUT"

        if tech_score >= 15:
            candidates.append({
                "symbol": sym, "strategy": strategy,
                "tech_score": tech_score, "tech_reasons": tech_reasons,
                "close": row['Close'],
                "atr_pct": row.get('ATR_pct', 2.5),
                "rsi": row.get('RSI', 50),
                "ema8": row.get('EMA8', 0), "ema21": row.get('EMA21', 0),
                "ema50": row.get('EMA50', 0), "ema200": row.get('EMA200', 0),
            })

    candidates.sort(key=lambda x: x["tech_score"], reverse=True)
    print(f"   ✅ {len(candidates)} passed technical filter")

    # ── 3. FMP FUNDAMENTAL SCORING (top 25) ──
    top_n = min(25, len(candidates))
    print(f"\n🔬 Phase 2: Fundamental scan (top {top_n})...")

    # Build fund_data for top candidates
    fund_data = {}
    for cand in candidates[:top_n]:
        sym = cand["symbol"]
        fg = client.financial_growth(sym, limit=8)
        ratios = client.ratios_ttm(sym)
        if fg:
            fund_data[sym] = {
                "growth_quarters": [
                    {"date": q["date"],
                     "rev_growth": q.get("revenueGrowth",0) or 0,
                     "eps_growth": q.get("epsgrowth",0) or 0,
                     "fcf_growth": q.get("freeCashFlowGrowth",0) or 0,
                     "op_income_growth": q.get("operatingIncomeGrowth",0) or 0}
                    for q in fg
                ],
                "ratios": ratios or {}
            }

    # Score
    final_signals = []
    for cand in candidates[:top_n]:
        sym = cand["symbol"]
        fund_score, fund_reasons = get_fundamental_score(sym, today_str, fund_data)
        total = cand["tech_score"] + fund_score

        print(f"   {sym:>5}: Tech:{cand['tech_score']:>2} + Fund:{fund_score:>2} = {total:>3} "
              f"({cand['strategy']})")

        if total >= min_score:
            px = cand["close"]
            stop_pct = rules.get("stop_loss_pct", -7.0)
            stop = round(px * (1 + stop_pct / 100), 2)
            risk = px - stop
            t1 = round(px + risk * 2, 2)
            t2 = round(px + risk * 3, 2)

            all_reasons = cand["tech_reasons"] + fund_reasons

            final_signals.append({
                "id": f"SIG-{today_str.replace('-','')}-{sym}",
                "symbol": sym,
                "strategy": cand["strategy"],
                "action": "BUY",
                "entry_price": round(px, 2),
                "stop_loss": stop,
                "target_1": t1,
                "target_2": t2,
                "trailing_stop_pct": rules.get("trailing_stop_pct", -7.0),
                "confidence": min(10, max(1, total // 10)),
                "score": total,
                "tech_score": cand["tech_score"],
                "fund_score": fund_score,
                "max_hold_days": rules.get("max_hold_days", 30),
                "sector": SYMBOL_SECTOR.get(sym, "?"),
                "rsi": round(cand["rsi"], 1) if not pd.isna(cand["rsi"]) else None,
                "thesis": "; ".join(all_reasons[:6]),
                "generated_at": today_str,
                "expires_at": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
                "status": "ACTIVE"
            })

    final_signals.sort(key=lambda x: x["score"], reverse=True)

    # ── SAVE ──
    signals_out = {
        "updated_at": datetime.now().isoformat(),
        "scan_date": today_str,
        "strategy_version": params.get("version", 0),
        "total_scanned": len(scan_symbols),
        "passed_technical": len(candidates),
        "total_signals": len(final_signals),
        "active_signals": final_signals[:max_signals],
        "watching": [
            {"symbol": s["symbol"], "score": s["score"], "sector": s["sector"],
             "entry_price": s["entry_price"], "strategy": s["strategy"]}
            for s in final_signals[max_signals:max_signals+10]
        ],
        "recently_closed": []
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "signals.json", "w") as f:
        json.dump(signals_out, f, indent=2)

    # Append to history
    hist_path = DATA_DIR / "signal_history.json"
    history = json.load(open(hist_path)) if hist_path.exists() else []
    history.extend(final_signals)
    with open(hist_path, "w") as f:
        json.dump(history, f, indent=2)

    # ── PRINT ──
    print(f"\n{'═' * 65}")
    print(f"🎯 TOP {min(max_signals, len(final_signals))} SİNYAL (v{params.get('version',0)})")
    print(f"{'═' * 65}")

    for i, s in enumerate(final_signals[:max_signals], 1):
        print(f"\n{'─' * 65}")
        print(f" {i}. {s['symbol']} ({s['sector']}) — {s['strategy']} Score: {s['score']}")
        print(f"    Entry: ${s['entry_price']:.2f} | Stop: ${s['stop_loss']:.2f} | "
              f"T1: ${s['target_1']:.2f} | T2: ${s['target_2']:.2f}")
        if s.get('rsi'):
            print(f"    RSI: {s['rsi']} | Confidence: {s['confidence']}/10")
        print(f"    📝 {s['thesis'][:100]}")

    if final_signals[max_signals:]:
        print(f"\n📋 WATCHLIST:")
        for s in final_signals[max_signals:max_signals+5]:
            print(f"   {s['symbol']} ({s['sector']}) {s['strategy']} "
                  f"Score:{s['score']} ${s['entry_price']:.2f}")

    print(f"\n📡 FMP API calls: {client.call_count}")
    print(f"💾 signals.json saved")

    return final_signals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY", ""))
    parser.add_argument("--max-signals", type=int, default=5)
    args = parser.parse_args()

    if not args.api_key:
        print("❌ FMP_API_KEY required"); sys.exit(1)

    client = FMPClient(args.api_key)
    params = load_params()
    run_scan(client, params, args.max_signals)


if __name__ == "__main__":
    main()
