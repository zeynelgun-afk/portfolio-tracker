#!/usr/bin/env python3
"""
Fair Value Panel — Simplified

For each open position in data/portfolio.json:
- Fetch FMP price-target-news (latest analyst targets, default 20 most recent)
- Compute fair value = (latest target + highest target) / 2
- Compare to current price → discount/premium %
- Send a compact table to Zeynel's Telegram DM

Output:
- reports/daily/FAIR_VALUE_YYYY-MM-DD.md  (English markdown)
- Telegram DM message (Turkish summary)

Usage:
    python3 scripts/fair_value_panel.py            # write + send
    python3 scripts/fair_value_panel.py --dry-run  # write only
    python3 scripts/fair_value_panel.py --target group|dm   # override target

13 May 2026 — finzora ai
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Make `agent` importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.fmp import fmp_get  # noqa: E402
from agent.portfolio import load_portfolio, get_positions  # noqa: E402
from agent.telegram import send_to_dm, send_to_group  # noqa: E402


# ────────────────────────────── core logic ──────────────────────────────


def fetch_analyst_targets(symbol: str, lookback_count: int = 20) -> list[dict]:
    """
    Fetch the most recent N analyst price-target updates for a symbol.

    Returns a list of {publishedDate, priceTarget, analystCompany, ...} dicts
    sorted newest-first (as FMP returns them). Empty list on error/no data.
    """
    data = fmp_get("price-target-news", {"symbol": symbol, "limit": lookback_count})
    if not data:
        return []
    # FMP returns newest-first already, but filter out entries with no price target
    cleaned = [
        d for d in data
        if d.get("priceTarget") and isinstance(d["priceTarget"], (int, float))
    ]
    return cleaned


def compute_fair_value(targets: list[dict]) -> Optional[dict]:
    """
    Fair value = (latest target + highest target) / 2

    Returns a dict with keys: fair_value, latest_target, highest_target,
    latest_date, highest_analyst, sample_size. Returns None if no data.
    """
    if not targets:
        return None
    # Newest-first: index 0 is the latest
    latest = targets[0]
    latest_price = float(latest["priceTarget"])
    latest_date = latest.get("publishedDate", "")[:10]

    # Highest across the lookback window
    highest = max(targets, key=lambda d: d["priceTarget"])
    highest_price = float(highest["priceTarget"])
    highest_analyst = highest.get("analystCompany", "")

    fair = (latest_price + highest_price) / 2.0
    return {
        "fair_value": fair,
        "latest_target": latest_price,
        "latest_date": latest_date,
        "latest_analyst": latest.get("analystCompany", ""),
        "highest_target": highest_price,
        "highest_analyst": highest_analyst,
        "sample_size": len(targets),
    }


def discount_pct(current: float, fair: float) -> float:
    """Return discount (% positive = below fair, negative = above fair)."""
    if fair <= 0:
        return 0.0
    return (fair - current) / current * 100.0


def signal_label(disc: float) -> str:
    """
    UCUZ if discount > +10% (price is at least 10% below fair)
    ADİL if -10% ≤ discount ≤ +10%
    PAHALI if discount < -10%
    """
    if disc > 10.0:
        return "UCUZ"
    if disc < -10.0:
        return "PAHALI"
    return "ADİL"


# ────────────────────────────── reporting ──────────────────────────────


def build_panel_rows(portfolio_data: dict) -> list[dict]:
    """Compute fair value for every open position. Returns list of row dicts."""
    rows = []
    open_positions = portfolio_data.get("open_positions", [])
    for pos in open_positions:
        symbol = pos["symbol"]
        current = pos.get("current_price")
        targets = fetch_analyst_targets(symbol)
        fv = compute_fair_value(targets)

        row = {
            "symbol": symbol,
            "current": current,
            "fair_value": fv["fair_value"] if fv else None,
            "latest_target": fv["latest_target"] if fv else None,
            "latest_date": fv["latest_date"] if fv else None,
            "highest_target": fv["highest_target"] if fv else None,
            "sample_size": fv["sample_size"] if fv else 0,
            "discount_pct": discount_pct(current, fv["fair_value"]) if (fv and current) else None,
        }
        row["signal"] = signal_label(row["discount_pct"]) if row["discount_pct"] is not None else "N/A"
        rows.append(row)
    return rows


def render_markdown(rows: list[dict]) -> str:
    """Write an English markdown report."""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Fair Value Panel — {today}",
        "",
        "Fair value = (most recent analyst target + highest analyst target) / 2",
        "Lookback: latest 20 analyst price-target updates per symbol",
        "",
        "| Symbol | Current | Fair | Discount/Premium | Signal | Latest target | Highest | Sample |",
        "|---|---|---|---|---|---|---|---|",
    ]
    # Sort: cheapest first
    rows_sorted = sorted(
        rows,
        key=lambda r: (r["discount_pct"] if r["discount_pct"] is not None else -999),
        reverse=True,
    )
    for r in rows_sorted:
        if r["fair_value"] is None:
            lines.append(
                f"| {r['symbol']} | ${r['current']:.2f} | N/A | — | — | — | — | 0 |"
            )
        else:
            lines.append(
                f"| {r['symbol']} | ${r['current']:.2f} | ${r['fair_value']:.2f} | "
                f"{r['discount_pct']:+.1f}% | {r['signal']} | "
                f"${r['latest_target']:.2f} ({r['latest_date']}) | "
                f"${r['highest_target']:.2f} | {r['sample_size']} |"
            )

    # Summary buckets
    n_ucuz = sum(1 for r in rows if r["signal"] == "UCUZ")
    n_adil = sum(1 for r in rows if r["signal"] == "ADİL")
    n_pahali = sum(1 for r in rows if r["signal"] == "PAHALI")
    n_na = sum(1 for r in rows if r["signal"] == "N/A")
    lines.extend([
        "",
        "## Summary",
        f"- UCUZ (discount > +10%): {n_ucuz}",
        f"- ADİL (within ±10%): {n_adil}",
        f"- PAHALI (premium > 10%): {n_pahali}",
        f"- N/A (no analyst targets): {n_na}",
    ])
    return "\n".join(lines)


def render_telegram(rows: list[dict]) -> str:
    """Compact Turkish summary for Telegram DM."""
    today = datetime.now().strftime("%d %b %Y")
    rows_sorted = sorted(
        rows,
        key=lambda r: (r["discount_pct"] if r["discount_pct"] is not None else -999),
        reverse=True,
    )
    lines = [
        f"📊 <b>ADİL DEĞER PANELİ — {today}</b>",
        "",
        "Formül: (en yeni hedef + en yüksek hedef) / 2",
        "",
        "<pre>",
        f"{'HİSSE':<6} {'MEVCUT':>9} {'ADİL':>9} {'FARK':>8}  SİNYAL",
    ]
    for r in rows_sorted:
        sym = r["symbol"]
        cur_str = f"${r['current']:.2f}" if r["current"] else "N/A"
        if r["fair_value"] is None:
            lines.append(f"{sym:<6} {cur_str:>9} {'N/A':>9} {'—':>8}  —")
        else:
            fv_str = f"${r['fair_value']:.2f}"
            disc_str = f"{r['discount_pct']:+.1f}%"
            lines.append(
                f"{sym:<6} {cur_str:>9} {fv_str:>9} {disc_str:>8}  {r['signal']}"
            )
    lines.append("</pre>")
    # Buckets
    n_ucuz = sum(1 for r in rows if r["signal"] == "UCUZ")
    n_pahali = sum(1 for r in rows if r["signal"] == "PAHALI")
    lines.extend([
        "",
        f"UCUZ: {n_ucuz} · PAHALI: {n_pahali}",
        "",
        "<i>Analist hedef bazlı bilgilendirme — karar değil.</i>",
    ])
    return "\n".join(lines)


# ────────────────────────────── main ──────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Don't send Telegram")
    ap.add_argument("--target", choices=["dm", "group"], default="dm",
                    help="Telegram target (default: dm)")
    args = ap.parse_args()

    enriched_positions = get_positions(enrich=True)
    portfolio = {"open_positions": enriched_positions}
    n = len(enriched_positions)
    print(f"[fair_value] Computing fair value for {n} open positions...")

    rows = build_panel_rows(portfolio)
    md = render_markdown(rows)

    # Write report file
    out_dir = REPO_ROOT / "reports" / "daily"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"FAIR_VALUE_{datetime.now().strftime('%Y-%m-%d')}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"[fair_value] Report written: {out_path}")
    print(f"[fair_value] Size: {len(md):,} chars")

    # Telegram
    if args.dry_run:
        print("[fair_value] Dry-run: Telegram skipped.")
        return 0

    tg_text = render_telegram(rows)
    sender = send_to_dm if args.target == "dm" else send_to_group
    ok = sender(tg_text, parse_mode="HTML")
    print(f"[fair_value] Telegram sent ({args.target}): {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
