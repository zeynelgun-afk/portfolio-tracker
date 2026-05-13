"""
Weekly summary report — runs on Sundays around TR 12:00.

Produces a one-week look-back covering:
  Section 0 — Macro week (1-week change for SPY/QQQ/IWM/VIX/GLD/TLT)
  Section 1 — Sector rotation (11 SPDR sector ETFs sorted by 1W performance)
  Section 2 — Portfolio week (per-position 1W move + closed-this-week summary)
  Section 3 — Watchlist (stops still near, abnormal moves accumulating)

Output:
  - reports/weekly/WEEKLY_YYYY-MM-DD.md  (English, Sunday's date)
  - Telegram group message (Turkish, concise summary)

FMP `stock-price-change` endpoint provides 1D/5D/1M/3M/6M/ytd/1Y in a single
call per symbol. We use the `5D` field as the "week" proxy (5 trading days).
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent.portfolio import get_positions, get_closed  # noqa: E402
from agent.fmp import fmp_get                          # noqa: E402
from agent.reports.morning import (                    # noqa: E402
    _safe_float, _fmt, _fmt_pct,
)
from agent.telegram import send_to_group               # noqa: E402

REPORTS_DIR = _REPO_ROOT / "reports" / "weekly"

MACRO_WEEKLY = ["SPY", "QQQ", "IWM", "DIA", "GLD", "TLT"]

# 11 SPDR sector ETFs covering the GICS sectors
SECTOR_ETFS = {
    "XLK":  "Technology",
    "XLF":  "Financials",
    "XLV":  "Health Care",
    "XLE":  "Energy",
    "XLI":  "Industrials",
    "XLY":  "Consumer Discretionary",
    "XLP":  "Consumer Staples",
    "XLU":  "Utilities",
    "XLB":  "Materials",
    "XLRE": "Real Estate",
    "XLC":  "Communication Services",
}


# ---------- FMP weekly change ----------

def fetch_weekly_changes(symbols: list[str]) -> dict[str, dict]:
    """
    Call stock-price-change for each symbol and return:
      {symbol: {"price_change_1D": x, "price_change_5D": x, "price_change_1M": x}}
    Returns empty dict on failure.
    """
    result: dict[str, dict] = {}
    for sym in symbols:
        data = fmp_get("stock-price-change", {"symbol": sym})
        if not isinstance(data, list) or not data:
            continue
        row = data[0]
        result[sym] = {
            "1D": _safe_float(row.get("1D")),
            "5D": _safe_float(row.get("5D")),
            "1M": _safe_float(row.get("1M")),
        }
    return result


# ---------- This week's closed trades ----------

def closed_this_week(today: datetime) -> list[dict]:
    """Return positions whose exit_date is within last 7 days."""
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    out = []
    for p in get_closed():
        ed = p.get("exit_date")
        if ed and ed >= week_ago:
            out.append(p)
    return out


# ---------- Markdown report ----------

def render_report(
    macro_w: dict, sector_w: dict, portfolio_w: dict,
    closed_week: list[dict], positions: list[dict], today: str,
) -> str:
    lines: list[str] = []
    lines.append(f"# WEEKLY SUMMARY — week ending {today}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now():%Y-%m-%d %H:%M}*  ")
    lines.append("*Source: finzora ai (agent v2)*")
    lines.append("")

    # ---- Section 0: Macro week ----
    lines.append("## 0. Macro week (5D change)")
    lines.append("")
    lines.append("| Symbol | 5D % | 1M % |")
    lines.append("|--------|-----:|-----:|")
    for sym in MACRO_WEEKLY:
        row = macro_w.get(sym, {})
        d5 = row.get("5D")
        m1 = row.get("1M")
        lines.append(f"| **{sym}** | {_fmt_pct(d5)} | {_fmt_pct(m1)} |")
    lines.append("")

    # ---- Section 1: Sector rotation ----
    lines.append("## 1. Sector rotation (SPDR sector ETFs, 5D)")
    lines.append("")
    sector_rows = []
    for etf, name in SECTOR_ETFS.items():
        d5 = sector_w.get(etf, {}).get("5D")
        sector_rows.append((etf, name, d5))
    # Sort by 5D desc, None last
    sector_rows.sort(key=lambda r: (r[2] is None, -(r[2] or 0)))

    lines.append("| ETF | Sector | 5D % | Tone |")
    lines.append("|-----|--------|-----:|------|")
    for etf, name, d5 in sector_rows:
        tone = "—"
        if d5 is not None:
            if d5 >= 3:
                tone = "🟢 strong"
            elif d5 >= 1:
                tone = "🟢 up"
            elif d5 <= -3:
                tone = "🔴 weak"
            elif d5 <= -1:
                tone = "🔴 down"
            else:
                tone = "↔ flat"
        lines.append(f"| **{etf}** | {name} | {_fmt_pct(d5)} | {tone} |")
    lines.append("")

    # Sector leaders/laggers for narrative
    valid = [(etf, name, d5) for etf, name, d5 in sector_rows if d5 is not None]
    if valid:
        leaders = valid[:3]
        laggers = valid[-3:][::-1]  # bottom 3 in worst-first order
        lines.append(f"**Leaders:** {', '.join(f'{l[0]} ({l[2]:+.1f}%)' for l in leaders)}  ")
        lines.append(f"**Laggers:** {', '.join(f'{l[0]} ({l[2]:+.1f}%)' for l in laggers)}")
        lines.append("")

    # ---- Section 2: Portfolio week ----
    lines.append("## 2. Portfolio week")
    lines.append("")

    # Per-position 5D change
    rows = []
    for p in positions:
        sym = p.get("symbol")
        d5 = portfolio_w.get(sym, {}).get("5D")
        if d5 is None:
            continue
        rows.append((sym, p.get("sector") or "—", d5))
    rows.sort(key=lambda r: -r[2])

    if rows:
        lines.append("### Position 5D performance")
        lines.append("")
        lines.append("| Symbol | Sector | 5D % |")
        lines.append("|--------|--------|-----:|")
        for sym, sec, d5 in rows:
            lines.append(f"| **{sym}** | {sec[:25]} | {_fmt_pct(d5)} |")
        lines.append("")

    # Closed-this-week summary
    lines.append("### Trades closed this week")
    lines.append("")
    if closed_week:
        winning = [c for c in closed_week if (c.get("pnl_pct") or 0) > 0]
        losing = [c for c in closed_week if (c.get("pnl_pct") or 0) <= 0]
        avg_pnl = sum(c.get("pnl_pct") or 0 for c in closed_week) / len(closed_week)
        lines.append(
            f"**{len(closed_week)} trades closed** — "
            f"{len(winning)} winners / {len(losing)} losers, "
            f"avg P&L {avg_pnl:+.2f}%"
        )
        lines.append("")
        lines.append("| Symbol | Entry → Exit | P&L % | Reason |")
        lines.append("|--------|-------------:|------:|--------|")
        for c in sorted(closed_week, key=lambda x: -(x.get("pnl_pct") or 0)):
            ep = _safe_float(c.get("entry_price"))
            xp = _safe_float(c.get("exit_price"))
            pnl = _safe_float(c.get("pnl_pct"))
            lines.append(
                f"| **{c.get('symbol', '?')}** | "
                f"${_fmt(ep)} → ${_fmt(xp)} | "
                f"{_fmt_pct(pnl)} | "
                f"{(c.get('exit_reason') or '—')[:40]} |"
            )
        lines.append("")
    else:
        lines.append("No positions closed this week.")
        lines.append("")

    # ---- Section 3: Watchlist ----
    lines.append("## 3. Watchlist for next week")
    lines.append("")
    near = [
        p for p in positions
        if p.get("stop_distance_pct") is not None and p["stop_distance_pct"] < 5
    ]
    near.sort(key=lambda x: x["stop_distance_pct"])
    if near:
        lines.append("### Stops within 5%")
        lines.append("")
        lines.append("| Symbol | Current | Stop | Distance |")
        lines.append("|--------|--------:|-----:|---------:|")
        for p in near:
            lines.append(
                f"| **{p['symbol']}** | ${_fmt(p.get('current_price'))} | "
                f"${p['stop_loss']:.2f} | {p['stop_distance_pct']:+.2f}% |"
            )
        lines.append("")
    else:
        lines.append("All positions comfortably above stops.")
        lines.append("")

    return "\n".join(lines)


def render_telegram_summary(
    macro_w: dict, sector_w: dict, closed_week: list[dict],
    positions: list[dict], today: str,
) -> str:
    spy_5d = macro_w.get("SPY", {}).get("5D")
    qqq_5d = macro_w.get("QQQ", {}).get("5D")
    vix_5d = macro_w.get("VIX", {}).get("5D")  # may be missing, FMP ^VIX in stock-price-change?

    # Best/worst sectors this week
    sec_rows = [
        (etf, _safe_float(sector_w.get(etf, {}).get("5D")))
        for etf in SECTOR_ETFS
    ]
    sec_rows = [(e, v) for e, v in sec_rows if v is not None]
    sec_rows.sort(key=lambda x: -x[1])

    lines = [
        f"<b>📅 HAFTALIK ÖZET — {today}</b>",
        "",
        f"📊 <b>Piyasa 5G:</b>",
        f"  SPY: {_fmt_pct(spy_5d)}",
        f"  QQQ: {_fmt_pct(qqq_5d)}",
    ]

    if sec_rows:
        lines.append("")
        lines.append("🔄 <b>Sektör rotasyonu:</b>")
        top3 = sec_rows[:3]
        bot3 = sec_rows[-3:][::-1]
        lines.append("  Lider: " + ", ".join(f"{e} ({v:+.1f}%)" for e, v in top3))
        lines.append("  Geri kalan: " + ", ".join(f"{e} ({v:+.1f}%)" for e, v in bot3))

    # Portfolio: best/worst position this week
    p_rows = []
    portfolio_5d = {p.get("symbol"): None for p in positions}
    # Actually we need per-position 5D from a separate fetch; do a simple sort by
    # the macro-style data we have. Skip if absent.

    # Closed-this-week summary
    if closed_week:
        winning = [c for c in closed_week if (c.get("pnl_pct") or 0) > 0]
        avg_pnl = sum(c.get("pnl_pct") or 0 for c in closed_week) / len(closed_week)
        lines.append("")
        lines.append(
            f"🔚 <b>Bu hafta kapanan:</b> {len(closed_week)} trade "
            f"({len(winning)} kâr / {len(closed_week)-len(winning)} zarar, "
            f"ort {avg_pnl:+.2f}%)"
        )
        for c in sorted(closed_week, key=lambda x: -(x.get("pnl_pct") or 0))[:5]:
            pnl = _safe_float(c.get("pnl_pct"))
            lines.append(f"  {c.get('symbol', '?')}: {_fmt_pct(pnl)}")
    else:
        lines.append("")
        lines.append("🔚 Bu hafta kapanan trade yok")

    # Near-stop watchlist
    near = [
        p for p in positions
        if p.get("stop_distance_pct") is not None and p["stop_distance_pct"] < 2
    ]
    if near:
        lines.append("")
        lines.append(f"⚠️ <b>Stop yakın</b> ({len(near)} pozisyon):")
        for p in near[:3]:
            lines.append(
                f"  {p['symbol']}: ${_fmt(p.get('current_price'))} → "
                f"stop ${p['stop_loss']:.2f} ({p['stop_distance_pct']:+.2f}%)"
            )

    lines.append("")
    lines.append("<i>Detay: reports/weekly/ klasöründe</i>")
    return "\n".join(lines)


# ---------- Main entry point ----------

def generate_weekly_report(send_telegram: bool = False) -> dict:
    """Build this week's summary and write to disk; optionally post to Telegram."""
    today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")

    positions = get_positions(enrich=True)
    closed_week = closed_this_week(today_dt)

    # Fetch 5D changes for all relevant symbols (macro + sectors + position symbols)
    portfolio_syms = [p["symbol"] for p in positions if p.get("symbol")]
    macro_w = fetch_weekly_changes(MACRO_WEEKLY)
    sector_w = fetch_weekly_changes(list(SECTOR_ETFS.keys()))
    portfolio_w = fetch_weekly_changes(portfolio_syms)

    report_md = render_report(
        macro_w, sector_w, portfolio_w, closed_week, positions, today
    )
    telegram_summary = render_telegram_summary(
        macro_w, sector_w, closed_week, positions, today
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"WEEKLY_{today}.md"
    report_path.write_text(report_md, encoding="utf-8")

    sent_to_group = False
    if send_telegram:
        sent_to_group = send_to_group(telegram_summary, parse_mode="HTML")

    return {
        "report_path": str(report_path),
        "report_size_chars": len(report_md),
        "closed_this_week": len(closed_week),
        "macro_fetched": len(macro_w),
        "sectors_fetched": len(sector_w),
        "positions_fetched": len(portfolio_w),
        "telegram_sent": sent_to_group,
    }


def _cli():
    import argparse
    p = argparse.ArgumentParser(description="Generate weekly summary report.")
    p.add_argument("--send", action="store_true",
                   help="Post Turkish summary to Finzora group chat")
    args = p.parse_args()

    result = generate_weekly_report(send_telegram=args.send)
    print(f"Report written:    {result['report_path']}")
    print(f"Size:              {result['report_size_chars']:,} chars")
    print(f"Closed this week:  {result['closed_this_week']}")
    print(f"Macro fetched:     {result['macro_fetched']}/{len(MACRO_WEEKLY)}")
    print(f"Sectors fetched:   {result['sectors_fetched']}/{len(SECTOR_ETFS)}")
    print(f"Positions fetched: {result['positions_fetched']}/{len(get_positions())}")
    print(f"Telegram sent:     {result['telegram_sent']}"
          + ("" if args.send else " (use --send to deliver)"))


if __name__ == "__main__":
    _cli()
