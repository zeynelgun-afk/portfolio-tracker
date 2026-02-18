#!/usr/bin/env python3
"""
Momentum Scanner — Per-Stock Signals
Portföy yok. Her hisse bağımsız bir AL/SAT sinyali.
- Haftalık scan: top 5 momentum hissesi
- Yeni giren = BUY sinyali
- Listeden çıkan = SELL sinyali
- Her trade bağımsız takip edilir
"""

import json, sys
from datetime import datetime
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


def run_scan():
    ALL_SYMBOLS = get_full_universe()

    print("=" * 65)
    print(f"🚀 MOMENTUM SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Universe: {len(ALL_SYMBOLS)} | Top {TOP_N} | Hisse Bazlı")
    print("=" * 65)

    # Download
    print(f"\n📥 Downloading 2yr prices...")
    all_dl = ALL_SYMBOLS + ["SPY"]
    prices = yf.download(all_dl, period="2y", progress=False)
    if prices.empty:
        print("❌ No data"); return

    today = prices.index[-1]
    today_str = today.strftime('%Y-%m-%d')

    # Score
    print(f"\n🔧 Scoring...")
    scores = []
    valid = 0
    above_200 = 0

    for sym in ALL_SYMBOLS:
        try:
            close = prices['Close'][sym].dropna()
            vol = prices['Volume'][sym].dropna()
            if len(close) < 260: continue
            valid += 1

            idx = len(close) - 1
            ma200 = close.iloc[idx-200:idx].mean()
            if close.iloc[idx] < ma200: continue
            above_200 += 1

            if len(vol) >= 20:
                avg_vol = vol.iloc[-20:].mean()
                if avg_vol * close.iloc[idx] < MIN_ADV: continue

            mom = calc_momentum(close, idx)
            if mom is None: continue

            px = close.iloc[idx]
            ret_1w = (px / close.iloc[idx-5] - 1) * 100 if idx >= 5 else 0
            ret_1m = (px / close.iloc[idx-21] - 1) * 100 if idx >= 21 else 0
            ret_3m = (px / close.iloc[idx-63] - 1) * 100 if idx >= 63 else 0
            high_52w = close.iloc[idx-252:idx].max()
            pct_from_high = (px / high_52w - 1) * 100

            scores.append({
                "symbol": sym, "score": round(mom, 2),
                "price": round(float(px), 2),
                "ret_1w": round(ret_1w, 1), "ret_1m": round(ret_1m, 1),
                "ret_3m": round(ret_3m, 1),
                "pct_from_52w_high": round(pct_from_high, 1),
            })
        except:
            continue

    scores.sort(key=lambda x: x["score"], reverse=True)
    print(f"   Valid: {valid} | Above 200 DMA: {above_200} | Scored: {len(scores)}")

    # Load previous signals
    signals_path = DATA_DIR / "signals.json"
    trades_path = DATA_DIR / "trades.json"

    prev_active = {}
    if signals_path.exists():
        try:
            old = json.load(open(signals_path))
            for s in old.get("active_signals", []):
                prev_active[s["symbol"]] = s
        except:
            pass

    # Load trade history
    trade_history = json.load(open(trades_path)) if trades_path.exists() else []

    new_top = {s["symbol"]: s for s in scores[:TOP_N]}
    prev_set = set(prev_active.keys())
    new_set = set(new_top.keys())

    buys = new_set - prev_set
    sells = prev_set - new_set
    holds = prev_set & new_set

    # ── CLOSE sold signals ──
    for sym in sells:
        if sym in prev_active:
            old = prev_active[sym]
            entry_px = old.get("entry_price", 0)
            exit_px = new_top.get(sym, {}).get("price", 0)
            # Get current price for sold symbols
            for s in scores:
                if s["symbol"] == sym:
                    exit_px = s["price"]
                    break
            if exit_px == 0:
                try:
                    exit_px = float(prices['Close'][sym].dropna().iloc[-1])
                except:
                    exit_px = entry_px

            pnl = (exit_px - entry_px) / entry_px * 100 if entry_px > 0 else 0

            trade_history.append({
                "symbol": sym,
                "entry_date": old.get("entry_date", ""),
                "exit_date": today_str,
                "entry_price": entry_px,
                "exit_price": round(exit_px, 2),
                "entry_score": old.get("score", 0),
                "pnl_pct": round(pnl, 2),
                "days_held": (today - pd.Timestamp(old.get("entry_date", today_str))).days if old.get("entry_date") else 0,
                "status": "CLOSED"
            })

    # ── BUILD active signals ──
    active_signals = []
    for s in scores[:TOP_N]:
        sym = s["symbol"]
        if sym in holds and sym in prev_active:
            # Keep original entry
            old = prev_active[sym]
            active_signals.append({
                "symbol": sym,
                "action": "HOLD",
                "entry_date": old.get("entry_date", today_str),
                "entry_price": old.get("entry_price", s["price"]),
                "current_price": s["price"],
                "score": s["score"],
                "unrealized_pnl": round((s["price"] - old.get("entry_price", s["price"])) / old.get("entry_price", s["price"]) * 100, 2) if old.get("entry_price") else 0,
                "days_held": (today - pd.Timestamp(old.get("entry_date", today_str))).days if old.get("entry_date") else 0,
                "ret_1w": s["ret_1w"], "ret_1m": s["ret_1m"], "ret_3m": s["ret_3m"],
                "pct_from_52w_high": s["pct_from_52w_high"],
            })
        else:
            # New BUY
            active_signals.append({
                "symbol": sym,
                "action": "BUY",
                "entry_date": today_str,
                "entry_price": s["price"],
                "current_price": s["price"],
                "score": s["score"],
                "unrealized_pnl": 0,
                "days_held": 0,
                "ret_1w": s["ret_1w"], "ret_1m": s["ret_1m"], "ret_3m": s["ret_3m"],
                "pct_from_52w_high": s["pct_from_52w_high"],
            })

    # Watchlist
    watching = []
    for s in scores[TOP_N:20]:
        watching.append({
            "symbol": s["symbol"], "score": s["score"],
            "price": s["price"], "ret_3m": s["ret_3m"],
            "pct_from_52w_high": s["pct_from_52w_high"]
        })

    # SPY
    spy_close = prices['Close']['SPY'].dropna()
    spy_px = float(spy_close.iloc[-1])
    spy_ma200 = float(spy_close.iloc[-200:].mean())

    # Trade stats
    closed = trade_history
    total_closed = len(closed)
    if total_closed > 0:
        wins = [t for t in closed if t["pnl_pct"] > 0]
        losses = [t for t in closed if t["pnl_pct"] <= 0]
        win_rate = len(wins) / total_closed * 100
        avg_pnl = sum(t["pnl_pct"] for t in closed) / total_closed
        avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    else:
        win_rate = avg_pnl = avg_win = avg_loss = 0

    output = {
        "updated_at": datetime.now().isoformat(),
        "scan_date": today_str,
        "strategy": "momentum_per_stock",
        "version": "E2",
        "universe_size": len(ALL_SYMBOLS),
        "above_200dma": above_200,
        "scored": len(scores),
        "market": {
            "spy_price": round(spy_px, 2),
            "spy_200dma": round(spy_ma200, 2),
            "regime": "BULL" if spy_px > spy_ma200 else "BEAR",
            "breadth_pct": round(above_200 / valid * 100, 1) if valid > 0 else 0
        },
        "changes": {
            "new_buys": sorted(buys),
            "sells": sorted(sells),
            "holds": sorted(holds)
        },
        "active_signals": active_signals,
        "watching": watching,
        "lifetime_stats": {
            "total_closed": total_closed,
            "win_rate": round(win_rate, 1),
            "avg_pnl_per_trade": round(avg_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
        }
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(signals_path, "w") as f:
        json.dump(output, f, indent=2)
    with open(trades_path, "w") as f:
        json.dump(trade_history, f, indent=2)

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

    # ── PRINT ──
    print(f"\n{'═' * 65}")
    print(f"🎯 TOP {TOP_N} MOMENTUM SİNYALLERİ")
    print(f"{'═' * 65}")
    print(f"   SPY: ${spy_px:.2f} ({'BULL' if spy_px > spy_ma200 else 'BEAR'}) | "
          f"Breadth: {above_200}/{valid} ({above_200/valid*100:.0f}%)")

    if buys: print(f"\n   🟢 YENİ AL: {', '.join(sorted(buys))}")
    if sells: print(f"   🔴 SAT:     {', '.join(sorted(sells))}")
    if holds: print(f"   ⚪ TUT:     {', '.join(sorted(holds))}")

    # Closed trade P&L
    if sells:
        print(f"\n   📋 KAPANAN TRADE'LER:")
        for t in trade_history[-len(sells):]:
            emoji = "✅" if t["pnl_pct"] > 0 else "❌"
            print(f"      {t['symbol']:>5}: {t['entry_price']:.2f} → {t['exit_price']:.2f} | "
                  f"{t['pnl_pct']:+.1f}% | {t['days_held']}d {emoji}")

    for i, s in enumerate(active_signals, 1):
        print(f"\n{'─' * 65}")
        action_emoji = "🟢" if s["action"] == "BUY" else "⚪"
        pnl_str = f"P&L: {s['unrealized_pnl']:+.1f}%" if s["days_held"] > 0 else "YENİ"
        print(f" {i}. {s['symbol']} — Mom: {s['score']:.1f} [{s['action']}] {action_emoji}")
        print(f"    Giriş: ${s['entry_price']:.2f} | Şimdi: ${s['current_price']:.2f} | {pnl_str}")
        print(f"    1W: {s['ret_1w']:+.1f}% | 1M: {s['ret_1m']:+.1f}% | 3M: {s['ret_3m']:+.1f}% | "
              f"52W Hi: {s['pct_from_52w_high']:+.1f}%")

    print(f"\n📋 WATCHLIST:")
    for w in watching[:10]:
        print(f"   {w['symbol']:>5} Mom:{w['score']:>6.1f} ${w['price']:>8.2f} 3M:{w['ret_3m']:>+5.1f}%")

    if total_closed > 0:
        print(f"\n{'─' * 65}")
        print(f"📈 TOPLAM İSTATİSTİK ({total_closed} kapalı trade)")
        print(f"   WR: {win_rate:.0f}% | Ort: {avg_pnl:+.1f}% | "
              f"Kazanç: {avg_win:+.1f}% | Kayıp: {avg_loss:+.1f}%")

    print(f"\n💾 signals.json + trades.json saved")
    return output


if __name__ == "__main__":
    run_scan()
