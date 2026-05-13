"""
Portfolio data layer — single source of truth.

Reads/writes data/portfolio.json (post-2026-05-13 schema, 8 fields).
Provides:
  - load_portfolio(): raw dict from disk
  - get_positions(): list of open positions (with optional FMP live enrichment)
  - get_closed(): list of closed positions
  - add_position(): create new position
  - close_position(): move a position from open → closed
  - portfolio_metrics(): aggregate metrics (total value, unrealized P&L, etc)

Schema (open position):
  symbol, sector, entry_date, entry_price, shares, entry_reason,
  stop_loss (required), target (optional)

On close, the following fields are added:
  exit_date, exit_price, exit_reason, pnl_pct (auto), lessons (optional)

All code in English. Telegram-facing messages remain Turkish (separate module).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = REPO_ROOT / "data" / "portfolio.json"


# ---------- File I/O ----------

def load_portfolio() -> dict:
    """Load raw portfolio.json from disk."""
    if not PORTFOLIO_PATH.exists():
        raise FileNotFoundError(f"Portfolio file not found: {PORTFOLIO_PATH}")
    with open(PORTFOLIO_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(data: dict) -> None:
    """Write portfolio.json to disk with stable formatting."""
    data["_last_updated"] = datetime.now().isoformat(timespec="seconds")
    PORTFOLIO_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------- Read helpers ----------

def get_positions(enrich: bool = False) -> list[dict]:
    """
    Return list of open positions.

    If enrich=True, adds live FMP fields to each position (in-memory only,
    not persisted): current_price, day_change_pct, market_value,
    unrealized_pnl, unrealized_pnl_pct, weight_pct, stop_distance_pct.
    """
    data = load_portfolio()
    positions = [p for p in data.get("positions", []) if isinstance(p, dict)]

    if enrich and positions:
        positions = _enrich_with_quotes(positions)

    return positions


def get_closed() -> list[dict]:
    """Return list of closed positions (historical)."""
    data = load_portfolio()
    return [p for p in data.get("closed", []) if isinstance(p, dict)]


# ---------- Write helpers ----------

def add_position(
    symbol: str,
    sector: str,
    entry_price: float,
    shares: float,
    entry_reason: str,
    stop_loss: float,
    target: Optional[float] = None,
    entry_date: Optional[str] = None,
) -> dict:
    """
    Add a new position to data/portfolio.json.

    stop_loss is REQUIRED (post-simplification rule). target is optional.
    Returns the inserted position dict.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("symbol must be a non-empty string")
    if stop_loss is None:
        raise ValueError("stop_loss is required for new positions")
    if entry_price <= 0 or shares <= 0:
        raise ValueError("entry_price and shares must be positive")

    new_pos = {
        "symbol": symbol.upper(),
        "sector": sector,
        "entry_date": entry_date or datetime.now().strftime("%Y-%m-%d"),
        "entry_price": round(float(entry_price), 4),
        "shares": shares,
        "entry_reason": entry_reason,
        "stop_loss": round(float(stop_loss), 4),
        "target": round(float(target), 4) if target is not None else None,
    }

    data = load_portfolio()
    data.setdefault("positions", []).append(new_pos)
    save_portfolio(data)
    return new_pos


def close_position(
    symbol: str,
    exit_price: float,
    exit_reason: str,
    exit_date: Optional[str] = None,
    lessons: str = "",
    entry_date_match: Optional[str] = None,
) -> dict:
    """
    Move a position from open → closed.

    If multiple positions exist with the same symbol (shouldn't happen post-
    simplification, but defensive), entry_date_match disambiguates.

    Computes pnl_pct automatically. Returns the closed position dict.
    """
    data = load_portfolio()
    positions = data.get("positions", [])

    # Find target position
    candidates = [
        (i, p) for i, p in enumerate(positions)
        if p.get("symbol", "").upper() == symbol.upper()
        and (entry_date_match is None or p.get("entry_date") == entry_date_match)
    ]

    if not candidates:
        raise ValueError(f"No open position found for {symbol}")
    if len(candidates) > 1 and entry_date_match is None:
        raise ValueError(
            f"Multiple positions for {symbol}, specify entry_date_match"
        )

    idx, pos = candidates[0]

    # Compute realized P&L
    entry_price = pos["entry_price"]
    pnl_pct = round((float(exit_price) - float(entry_price)) / float(entry_price) * 100, 2)

    closed_pos = {
        **pos,
        "exit_date": exit_date or datetime.now().strftime("%Y-%m-%d"),
        "exit_price": round(float(exit_price), 4),
        "exit_reason": exit_reason,
        "pnl_pct": pnl_pct,
        "lessons": lessons,
    }

    # Move from open → closed
    positions.pop(idx)
    data.setdefault("closed", []).append(closed_pos)
    save_portfolio(data)
    return closed_pos


# ---------- Metrics ----------

def portfolio_metrics(enriched_positions: Optional[list[dict]] = None) -> dict:
    """
    Aggregate metrics across all open positions.

    Pass enriched positions (from get_positions(enrich=True)) for live values.
    Without enrichment, only cost-basis metrics are returned.
    """
    positions = enriched_positions if enriched_positions is not None else get_positions(enrich=False)

    total_cost = sum(p.get("entry_price", 0) * p.get("shares", 0) for p in positions)
    metrics = {
        "position_count": len(positions),
        "total_cost_basis": round(total_cost, 2),
    }

    # Live metrics only available if positions are enriched
    if positions and any("market_value" in p for p in positions):
        total_value = sum(p.get("market_value", 0) or 0 for p in positions)
        total_pnl = total_value - total_cost
        pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0
        metrics.update({
            "total_market_value": round(total_value, 2),
            "total_unrealized_pnl": round(total_pnl, 2),
            "total_unrealized_pnl_pct": round(pnl_pct, 2),
        })

    return metrics


# ---------- FMP price enrichment ----------

def _enrich_with_quotes(positions: list[dict]) -> list[dict]:
    """
    Add live price fields to each position. Returns a new list of dicts
    (does not mutate input). Falls back gracefully if FMP unreachable.
    """
    try:
        # Use the legacy fmp_client for now; will replace with agent/fmp.py later
        from agent.legacy.fmp_client import fmp_get
    except ImportError:
        # FMP client not available — return positions without enrichment
        return positions

    symbols = sorted({p["symbol"] for p in positions if p.get("symbol")})
    if not symbols:
        return positions

    try:
        quotes = fmp_get("batch-quote", {"symbols": ",".join(symbols)})
        if not isinstance(quotes, list):
            return positions
        price_map = {q.get("symbol"): q for q in quotes if isinstance(q, dict)}
    except Exception:
        return positions

    # Compute total cost basis for weight calculation
    total_cost = sum(
        p.get("entry_price", 0) * p.get("shares", 0) for p in positions
    ) or 1

    enriched = []
    for p in positions:
        sym = p.get("symbol")
        q = price_map.get(sym, {})
        price = q.get("price")
        prev_close = q.get("previousClose")

        # Day change
        day_chg_pct = None
        if price is not None and prev_close:
            try:
                day_chg_pct = round((float(price) - float(prev_close)) / float(prev_close) * 100, 2)
            except (TypeError, ValueError):
                pass
        if day_chg_pct is None and q.get("changePercentage") is not None:
            try:
                day_chg_pct = round(float(q["changePercentage"]), 2)
            except (TypeError, ValueError):
                pass

        # Position-level metrics
        cost = (p.get("entry_price") or 0) * (p.get("shares") or 0)
        market_value = (price or 0) * (p.get("shares") or 0) if price else None
        unrealized_pnl = (market_value - cost) if market_value is not None else None
        unrealized_pnl_pct = (
            round(unrealized_pnl / cost * 100, 2)
            if (unrealized_pnl is not None and cost)
            else None
        )
        weight_pct = round((cost / total_cost) * 100, 2) if total_cost else None
        stop_distance_pct = None
        if p.get("stop_loss") and price:
            try:
                stop_distance_pct = round(
                    (float(price) - float(p["stop_loss"])) / float(price) * 100, 2
                )
            except (TypeError, ValueError):
                pass

        enriched.append({
            **p,
            "current_price": price,
            "day_change_pct": day_chg_pct,
            "market_value": round(market_value, 2) if market_value is not None else None,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "weight_pct": weight_pct,
            "stop_distance_pct": stop_distance_pct,
        })

    return enriched


# ---------- CLI for quick inspection ----------

def _cli_summary():
    """Print a quick summary to stdout. Useful for manual checks."""
    positions = get_positions(enrich=True)
    metrics = portfolio_metrics(positions)

    print(f"=== Finzora portfolio summary ({datetime.now():%Y-%m-%d %H:%M}) ===")
    print(f"Open positions: {metrics['position_count']}")
    print(f"Cost basis:     ${metrics['total_cost_basis']:,.2f}")
    if "total_market_value" in metrics:
        print(f"Market value:   ${metrics['total_market_value']:,.2f}")
        sign = "+" if metrics["total_unrealized_pnl"] >= 0 else ""
        print(f"Unrealized P&L: {sign}${metrics['total_unrealized_pnl']:,.2f} "
              f"({sign}{metrics['total_unrealized_pnl_pct']}%)")
    print()
    print(f"{'Symbol':<6} {'Sector':<22} {'Shares':>8} {'Entry':>10} "
          f"{'Current':>10} {'P&L%':>7} {'Weight%':>8}")
    print("-" * 80)
    for p in positions:
        sym = p.get("symbol", "?")
        sec = (p.get("sector") or "—")[:22]
        sh = p.get("shares") or 0
        ep = p.get("entry_price") or 0
        cp = p.get("current_price")
        pnl = p.get("unrealized_pnl_pct")
        w = p.get("weight_pct")
        cp_s = f"${cp:.2f}" if cp else "—"
        pnl_s = f"{pnl:+.1f}%" if pnl is not None else "—"
        w_s = f"{w:.1f}%" if w is not None else "—"
        print(f"{sym:<6} {sec:<22} {sh:>8} ${ep:>9.2f} {cp_s:>10} {pnl_s:>7} {w_s:>8}")


if __name__ == "__main__":
    _cli_summary()
