"""
Position & risk monitor — fires DM alerts to Zeynel.

Designed to be called every 30 minutes during US market session (16:30–23:00 TR).
All alerts go to DM. Group chat receives nothing from this module (per Finzora
convention: group is for trade actions and reports only).

Alert types (each rate-limited via data/monitor_state.json):
  K-13     VIX crisis      VIX > 30 (or > 35 escalation)
  K-23     Drawdown        portfolio unrealized P&L crosses -10/-15/-20%
  STOP     Stop proximity  position stop_distance_pct < 2%
  MOVE     Abnormal move   today's |change| > 2 × ATR(14)

State semantics:
  Each alert type tracks the date it was last fired. Re-fires only when the
  date changes (so at most one alert per type per day per symbol).
  Drawdown threshold escalates: if -10% fired, only -15% or -20% can fire
  again same day.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Ensure repo root is on sys.path so `agent.X` imports resolve when this
# script is launched directly (e.g. `python agent/monitor.py`).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent.portfolio import get_positions, portfolio_metrics  # noqa: E402
from agent.telegram import send_to_dm, md_to_telegram         # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = REPO_ROOT / "data" / "monitor_state.json"

# Tunables
VIX_WARN_LEVEL     = 30.0
VIX_EXTREME_LEVEL  = 35.0
DRAWDOWN_THRESHOLDS = [-10.0, -15.0, -20.0]   # percentages
STOP_PROXIMITY_PCT = 2.0
ATR_MOVE_MULTIPLE  = 2.0
ATR_PERIOD         = 14


# ---------- State management ----------

def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"last_run": None, "alerts": {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"last_run": None, "alerts": {}}


def _save_state(state: dict) -> None:
    state["last_run"] = datetime.now().isoformat(timespec="seconds")
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _fired_today(state: dict, key: str) -> bool:
    """Return True if alert with `key` was already fired today."""
    return state.get("alerts", {}).get(key) == _today_str()


def _mark_fired(state: dict, key: str) -> None:
    state.setdefault("alerts", {})[key] = _today_str()


# ---------- VIX (K-13) ----------

def check_vix(state: dict) -> Optional[str]:
    """Return Turkish alert text if VIX crisis threshold is crossed today."""
    try:
        from agent.fmp import vix_quote
        q = vix_quote()
        if not q:
            return None
        price = q.get("price")
        source = "fmp"
    except Exception as e:
        print(f"[monitor] VIX fetch failed: {e}", file=sys.stderr)
        return None

    if price is None:
        return None
    price = float(price)

    if price >= VIX_EXTREME_LEVEL and not _fired_today(state, "vix_extreme"):
        _mark_fired(state, "vix_extreme")
        return (
            f"🔴 <b>K-13 — VIX ekstrem</b>\n"
            f"VIX: <b>{price:.2f}</b> (kaynak: {source})\n"
            f"VIX 35+ aralığında. Piyasada ciddi panik var. "
            f"Yeni giriş kararlarını gözden geçirmen mantıklı."
        )

    if price >= VIX_WARN_LEVEL and not _fired_today(state, "vix_warn"):
        _mark_fired(state, "vix_warn")
        return (
            f"🟡 <b>K-13 — VIX yüksek</b>\n"
            f"VIX: <b>{price:.2f}</b> (kaynak: {source})\n"
            f"VIX 30 üstüne çıktı. Ortam değişti, mevcut pozisyonları "
            f"gözden geçirmek isteyebilirsin."
        )

    return None


# ---------- Drawdown (K-23) ----------

def check_drawdown(metrics: dict, state: dict) -> Optional[str]:
    """Return alert if unrealized portfolio P&L crosses a threshold today."""
    pnl_pct = metrics.get("total_unrealized_pnl_pct")
    if pnl_pct is None:
        return None

    # Find deepest threshold that's been crossed
    crossed = [t for t in DRAWDOWN_THRESHOLDS if pnl_pct <= t]
    if not crossed:
        return None
    deepest = min(crossed)  # -20 is deeper than -10

    key = f"drawdown_{int(abs(deepest))}"
    if _fired_today(state, key):
        return None
    _mark_fired(state, key)

    total_value = metrics.get("total_market_value", 0)
    total_pnl   = metrics.get("total_unrealized_pnl", 0)
    return (
        f"⚠️ <b>K-23 — Drawdown {deepest:.0f}%</b>\n"
        f"Portföy realize olmamış P&K: <b>{pnl_pct:+.2f}%</b> "
        f"(${total_pnl:,.0f})\n"
        f"Toplam değer: ${total_value:,.0f}\n"
        f"Farkındalık amaçlı uyarı. Karar dayatmaz."
    )


# ---------- Stop proximity (STOP) ----------

def check_stop_proximity(positions: list[dict], state: dict) -> list[str]:
    """Return list of alerts for positions whose stop is < 2% away."""
    alerts = []
    for p in positions:
        sym = p.get("symbol")
        dist = p.get("stop_distance_pct")
        if dist is None or sym is None:
            continue

        # Already triggered (price < stop)
        if dist < 0:
            key = f"stop_breached:{sym}"
            if _fired_today(state, key):
                continue
            _mark_fired(state, key)
            alerts.append(
                f"🔴 <b>STOP TETİKLENDİ — {sym}</b>\n"
                f"Fiyat ${p.get('current_price', 0):.2f} stop ${p['stop_loss']:.2f} altına geçti.\n"
                f"Mesafe: {dist:+.2f}%"
            )
            continue

        if dist < STOP_PROXIMITY_PCT:
            key = f"stop_near:{sym}"
            if _fired_today(state, key):
                continue
            _mark_fired(state, key)
            alerts.append(
                f"🟡 <b>Stop yakın — {sym}</b>\n"
                f"Fiyat ${p.get('current_price', 0):.2f}, stop ${p['stop_loss']:.2f}\n"
                f"Mesafe: <b>{dist:.2f}%</b> (eşik: %{STOP_PROXIMITY_PCT})"
            )
    return alerts


# ---------- Abnormal moves (MOVE > 2 × ATR) ----------

def _fetch_atr14(symbol: str) -> Optional[float]:
    """
    Compute ATR(14) from 15 most recent daily bars.
    Returns the absolute ATR value in dollars, or None on failure.
    """
    try:
        from agent.fmp import historical_eod
    except ImportError:
        return None

    try:
        bars = historical_eod(symbol, limit=ATR_PERIOD + 1)
    except Exception:
        return None
    if not isinstance(bars, list) or len(bars) < ATR_PERIOD + 1:
        return None

    # historical-eod is newest-first per FMP convention
    bars = bars[: ATR_PERIOD + 1]
    bars = sorted(bars, key=lambda b: b.get("date", ""))  # oldest → newest

    trs = []
    prev_close = None
    for b in bars:
        try:
            h = float(b["high"])
            l = float(b["low"])
            c = float(b["close"])
        except (KeyError, TypeError, ValueError):
            return None
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c

    # Use the last ATR_PERIOD true-range values
    return sum(trs[-ATR_PERIOD:]) / ATR_PERIOD if trs else None


def check_abnormal_moves(positions: list[dict], state: dict) -> list[str]:
    """
    Fire an alert for any position whose today's |price change| in dollars
    exceeds ATR_MOVE_MULTIPLE × ATR(14).
    """
    alerts = []
    for p in positions:
        sym = p.get("symbol")
        price = p.get("current_price")
        day_chg_pct = p.get("day_change_pct")
        if not sym or price is None or day_chg_pct is None:
            continue

        # Today's dollar move
        day_chg_abs = abs(price * day_chg_pct / 100)

        atr = _fetch_atr14(sym)
        if atr is None or atr == 0:
            continue

        if day_chg_abs >= ATR_MOVE_MULTIPLE * atr:
            key = f"abnormal:{sym}"
            if _fired_today(state, key):
                continue
            _mark_fired(state, key)
            direction = "yukarı" if day_chg_pct > 0 else "aşağı"
            alerts.append(
                f"⚡ <b>Anormal hareket — {sym}</b>\n"
                f"Bugünkü hareket: <b>{day_chg_pct:+.2f}%</b> "
                f"(${day_chg_abs:.2f}) — {direction}\n"
                f"ATR(14) = ${atr:.2f}, hareket = {day_chg_abs/atr:.1f}× ATR"
            )
    return alerts


# ---------- Main entry point ----------

def run_monitor(send_alerts: bool = True) -> dict:
    """
    Run all checks, fire DM alerts for fresh triggers, persist state.

    Returns a summary dict useful for logs / dry-run testing:
        {
          "vix": str | None,
          "drawdown": str | None,
          "stop": [str, ...],
          "abnormal": [str, ...],
          "sent_count": int,
        }
    """
    state = _load_state()

    # Enrich once; reuse for every check
    positions = get_positions(enrich=True)
    metrics = portfolio_metrics(positions)

    vix_alert       = check_vix(state)
    drawdown_alert  = check_drawdown(metrics, state)
    stop_alerts     = check_stop_proximity(positions, state)
    abnormal_alerts = check_abnormal_moves(positions, state)

    messages = []
    if vix_alert:
        messages.append(vix_alert)
    if drawdown_alert:
        messages.append(drawdown_alert)
    messages.extend(stop_alerts)
    messages.extend(abnormal_alerts)

    sent = 0
    if send_alerts:
        for m in messages:
            # Already-HTML text — bypass md_to_telegram
            if send_to_dm(m, parse_mode="HTML"):
                sent += 1

    _save_state(state)

    return {
        "vix": vix_alert,
        "drawdown": drawdown_alert,
        "stop": stop_alerts,
        "abnormal": abnormal_alerts,
        "sent_count": sent,
        "total_alerts": len(messages),
    }


# ---------- CLI ----------

def _cli():
    import argparse
    p = argparse.ArgumentParser(description="Run Finzora monitor checks.")
    p.add_argument("--dry-run", action="store_true",
                   help="Run checks but don't send Telegram messages")
    p.add_argument("--reset-state", action="store_true",
                   help="Delete monitor_state.json (will re-fire all triggers)")
    args = p.parse_args()

    if args.reset_state and STATE_PATH.exists():
        STATE_PATH.unlink()
        print("[monitor] State reset")

    result = run_monitor(send_alerts=not args.dry_run)
    print(f"VIX alert:       {bool(result['vix'])}")
    print(f"Drawdown alert:  {bool(result['drawdown'])}")
    print(f"Stop alerts:     {len(result['stop'])}")
    print(f"Abnormal alerts: {len(result['abnormal'])}")
    print(f"Total triggered: {result['total_alerts']}")
    print(f"Sent to DM:      {result['sent_count']}"
          f"{' (dry run, none sent)' if args.dry_run else ''}")


if __name__ == "__main__":
    _cli()
