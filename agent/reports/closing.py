"""
Daily closing report generator.

Produces a post-session summary covering:
  Section 0 — Market close (VIX, SPY/QQQ/DIA/IWM/GLD/TLT — close + day change)
  Section 1 — Portfolio day (P&L change, biggest movers TODAY)
  Section 2 — Trades closed today (from data/portfolio.json `closed` list)
  Section 3 — Tomorrow's watchlist (stops still near, abnormal moves)

Output:
  - reports/daily/DAILY_CLOSING_YYYY-MM-DD.md  (English, full report)
  - Telegram group message (Turkish, concise summary)

Designed to run post-close (TR 00:30 next day). Re-uses the macro and
portfolio gathering helpers from agent.reports.morning to avoid duplication.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent.portfolio import get_closed  # noqa: E402
from agent.reports.morning import (    # noqa: E402
    gather_macro,
    gather_portfolio,
    MACRO_SYMBOLS,
    _vix_regime,
    _safe_float,
    _fmt,
    _fmt_pct,
    _classify_macro_move,
)
from agent.telegram import send_to_group  # noqa: E402

REPORTS_DIR = _REPO_ROOT / "reports" / "daily"


# ---------- Trades closed today ----------

def closed_today(target_date: str) -> list[dict]:
    """Return closed positions whose exit_date equals target_date (YYYY-MM-DD)."""
    return [p for p in get_closed() if p.get("exit_date") == target_date]


def _hold_days(entry_date: Optional[str], today: str) -> Optional[int]:
    """Tutma süresi (gün) — entry_date'ten today'e kadar."""
    if not entry_date:
        return None
    try:
        ed = datetime.strptime(entry_date, "%Y-%m-%d").date()
        td = datetime.strptime(today, "%Y-%m-%d").date()
        return (td - ed).days
    except (TypeError, ValueError):
        return None


# ---------- Day movers ----------

def biggest_movers(positions: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Return (top_gainers, top_losers) by today's percentage change.
    Different from morning's winners/losers, which uses unrealized P&L since entry.
    """
    moved = [p for p in positions if p.get("day_change_pct") is not None]
    gainers = sorted(moved, key=lambda x: x["day_change_pct"], reverse=True)[:3]
    losers = sorted(moved, key=lambda x: x["day_change_pct"])[:3]
    return gainers, losers


# ---------- Markdown report ----------

def render_report(macro: dict, portfolio: dict, today: str) -> str:
    lines: list[str] = []
    lines.append(f"# DAILY CLOSING REPORT — {today}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now():%Y-%m-%d %H:%M}*  ")
    lines.append("*Source: finzora ai (agent v2)*")
    lines.append("")

    # ---- Section 0: Market close ----
    lines.append("## 0. Market close")
    lines.append("")
    vix_price = macro["vix"]["price"]
    vix_chg = macro["vix"]["change_pct"]
    lines.append(
        f"**VIX close:** {_fmt(vix_price)}"
        + (f" ({vix_chg:+.2f}%)" if vix_chg is not None else "")
        + f" — *regime: {_vix_regime(vix_price)}*"
    )
    lines.append("")
    lines.append("| Symbol | Close | Day % | Tone |")
    lines.append("|--------|------:|------:|------|")
    for sym in MACRO_SYMBOLS:
        q = macro["macro"].get(sym) or {}
        price = _safe_float(q.get("price"))
        chg = _safe_float(q.get("changePercentage"))
        lines.append(
            f"| **{sym}** | {_fmt(price)} | {_fmt_pct(chg)} | "
            f"{_classify_macro_move(sym, chg)} |"
        )
    lines.append("")

    # ---- Section 1: Portfolio day ----
    m = portfolio["metrics"]
    positions = portfolio["positions"]
    lines.append("## 1. Portfolio day")
    lines.append("")
    lines.append(f"- **Open positions:** {m.get('position_count', 0)}")
    if "total_market_value" in m:
        lines.append(f"- **Market value (close):** ${m['total_market_value']:,.0f}")
        lines.append(
            f"- **Unrealized P&L:** {m['total_unrealized_pnl']:+,.0f} USD "
            f"({m['total_unrealized_pnl_pct']:+.2f}%)"
        )

    # Approximate today's portfolio dollar change using each position's day move.
    day_dollar = 0.0
    day_known = False
    for p in positions:
        chg_pct = p.get("day_change_pct")
        mv = p.get("market_value")
        if chg_pct is not None and mv is not None:
            # mv is close-of-day; prior close ≈ mv / (1 + chg_pct/100)
            try:
                prior = mv / (1 + chg_pct / 100)
                day_dollar += mv - prior
                day_known = True
            except ZeroDivisionError:
                pass
    if day_known:
        total_prior = (m.get("total_market_value", 0) or 0) - day_dollar
        day_pct = (day_dollar / total_prior * 100) if total_prior else 0
        lines.append(
            f"- **Today's portfolio change:** {day_dollar:+,.0f} USD "
            f"({day_pct:+.2f}%)"
        )
    lines.append("")

    # Today's biggest movers
    gainers, losers = biggest_movers(positions)
    if gainers:
        lines.append("### Top 3 gainers today")
        lines.append("")
        lines.append("| Symbol | Day % | Close | Position P&L % |")
        lines.append("|--------|------:|------:|---------------:|")
        for p in gainers:
            lines.append(
                f"| **{p['symbol']}** | {p['day_change_pct']:+.2f}% | "
                f"${_fmt(p.get('current_price'))} | "
                f"{_fmt_pct(p.get('unrealized_pnl_pct'))} |"
            )
        lines.append("")

    if losers:
        lines.append("### Top 3 losers today")
        lines.append("")
        lines.append("| Symbol | Day % | Close | Position P&L % |")
        lines.append("|--------|------:|------:|---------------:|")
        for p in losers:
            lines.append(
                f"| **{p['symbol']}** | {p['day_change_pct']:+.2f}% | "
                f"${_fmt(p.get('current_price'))} | "
                f"{_fmt_pct(p.get('unrealized_pnl_pct'))} |"
            )
        lines.append("")

    # ---- Section 2: Trades closed today ----
    closed = closed_today(today)
    lines.append("## 2. Trades closed today")
    lines.append("")
    if closed:
        lines.append("| Symbol | Entry → Exit | P&L % | Reason |")
        lines.append("|--------|-------------:|------:|--------|")
        for c in closed:
            ep = _safe_float(c.get("entry_price"))
            xp = _safe_float(c.get("exit_price"))
            pnl = _safe_float(c.get("pnl_pct"))
            lines.append(
                f"| **{c.get('symbol', '?')}** | "
                f"${_fmt(ep)} → ${_fmt(xp)} | "
                f"{_fmt_pct(pnl)} | "
                f"{c.get('exit_reason') or '—'} |"
            )
        lines.append("")
    else:
        lines.append("No positions closed today.")
        lines.append("")

    # ---- Section 3: Tomorrow's watchlist ----
    lines.append("## 3. Tomorrow's watchlist")
    lines.append("")
    stop_near = portfolio.get("stop_near", [])
    if stop_near:
        lines.append("### Stops still close to trigger")
        lines.append("")
        lines.append("| Symbol | Close | Stop | Distance |")
        lines.append("|--------|------:|-----:|---------:|")
        for p in stop_near:
            dist = p["stop_distance_pct"]
            lines.append(
                f"| **{p['symbol']}** | ${_fmt(p.get('current_price'))} | "
                f"${p['stop_loss']:.2f} | {dist:+.2f}% |"
            )
        lines.append("")
    else:
        lines.append("No positions within 5% of stop. ✅")
        lines.append("")

    return "\n".join(lines)


def render_telegram_summary(macro: dict, portfolio: dict, today: str) -> str:
    """
    Concise Turkish summary for the Finzora group chat.

    Yeni format (2026-05-15): pozisyon bazlı detay tablosu.
      - Her hisse için: alış fiyatı, kapanış, K/Z%, tutma süresi
      - Sıralama: K/Z% azalan (kazançlılar üstte)
      - ⚠ işareti: stop'a 3%'ten yakın pozisyonlar
      - Dolar tutarları (piyasa değeri, günlük dolar değişimi) kaldırıldı
    """
    vix_price = macro["vix"]["price"]
    spy = macro["macro"].get("SPY", {})
    qqq = macro["macro"].get("QQQ", {})
    positions = portfolio["positions"]

    lines = [
        f"<b>🌙 KAPANIŞ — {today}</b>",
        "",
        f"📊 VIX {_fmt(vix_price)} ({_vix_regime(vix_price)}) | "
        f"SPY {_fmt_pct(_safe_float(spy.get('changePercentage')))} | "
        f"QQQ {_fmt_pct(_safe_float(qqq.get('changePercentage')))}",
        "",
    ]

    # Pozisyonları K/Z%'ye göre azalan sırala (kazananlar üstte)
    sortable = [p for p in positions if p.get("unrealized_pnl_pct") is not None]
    sortable.sort(key=lambda x: x["unrealized_pnl_pct"], reverse=True)

    lines.append(f"💼 <b>{len(sortable)} açık pozisyon</b>")
    lines.append("")

    # Monospace tablo (Telegram <pre>)
    rows: list[str] = []
    rows.append("HİSSE  GİRİŞ → KAPANIŞ        K/Z%   GÜN")
    rows.append("─" * 42)
    for p in sortable:
        sym = (p.get("symbol") or "?")
        sym_s = sym.ljust(5)[:5]
        ep = _safe_float(p.get("entry_price"))
        cp = _safe_float(p.get("current_price"))
        pct = p.get("unrealized_pnl_pct")
        days = _hold_days(p.get("entry_date"), today)
        # Stop'a 3%'ten yakın pozisyonları işaretle
        stop_dist = p.get("stop_distance_pct")
        marker = "⚠" if (stop_dist is not None and stop_dist < 3) else " "
        entry_s = f"${ep:7.2f}" if ep is not None else "      —"
        close_s = f"${cp:7.2f}" if cp is not None else "      —"
        pct_s = f"{pct:+6.2f}%" if pct is not None else "    —  "
        day_s = f"{days:>3}g" if days is not None else " — "
        rows.append(f"{marker}{sym_s}  {entry_s} → {close_s}  {pct_s}  {day_s}")

    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines.append("")

    # Bugün kapanan pozisyonlar
    closed = closed_today(today)
    if closed:
        lines.append(f"🔚 <b>Bugün kapanan</b> ({len(closed)} poz):")
        for c in closed[:5]:
            pnl = _safe_float(c.get("pnl_pct"))
            lines.append(
                f"  {c.get('symbol', '?')}: {_fmt_pct(pnl)} — "
                f"{c.get('exit_reason') or '—'}"
            )
        lines.append("")

    # Pozisyon-bazlı özet (dolar tutarları YOK — kasıtlı)
    if sortable:
        wins = sum(1 for p in sortable if p["unrealized_pnl_pct"] > 0)
        avg = sum(p["unrealized_pnl_pct"] for p in sortable) / len(sortable)
        lines.append(
            f"📊 Pozitif: <b>{wins}/{len(sortable)}</b> | "
            f"Ortalama K/Z: <b>{avg:+.2f}%</b>"
        )

    lines.append("")
    lines.append("<i>Detay: reports/daily/ klasöründe</i>")
    return "\n".join(lines)


# ---------- Main entry point ----------

def generate_closing_report(send_telegram: bool = False) -> dict:
    """
    Build today's closing report.

    Side effects:
      - writes reports/daily/DAILY_CLOSING_<date>.md
      - if send_telegram: posts a Turkish summary to the Finzora group
    """
    today = datetime.now().strftime("%Y-%m-%d")

    macro = gather_macro()
    portfolio = gather_portfolio()

    report_md = render_report(macro, portfolio, today)
    telegram_summary = render_telegram_summary(macro, portfolio, today)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"DAILY_CLOSING_{today}.md"
    report_path.write_text(report_md, encoding="utf-8")

    sent_to_group = False
    if send_telegram:
        sent_to_group = send_to_group(telegram_summary, parse_mode="HTML")

    return {
        "report_path": str(report_path),
        "report_size_chars": len(report_md),
        "telegram_sent": sent_to_group,
        "closed_today_count": len(closed_today(today)),
    }


def _cli():
    import argparse
    p = argparse.ArgumentParser(description="Generate daily closing report.")
    p.add_argument("--send", action="store_true",
                   help="Post Turkish summary to Finzora group chat")
    args = p.parse_args()

    result = generate_closing_report(send_telegram=args.send)
    print(f"Report written:  {result['report_path']}")
    print(f"Size:            {result['report_size_chars']:,} chars")
    print(f"Closed today:    {result['closed_today_count']}")
    print(f"Telegram sent:   {result['telegram_sent']}"
          + ("" if args.send else " (use --send to deliver)"))


if __name__ == "__main__":
    _cli()
