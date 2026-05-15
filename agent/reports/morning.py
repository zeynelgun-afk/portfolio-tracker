"""
Daily morning report generator.

Produces a structured pre-session report covering:
  Section 0 — Market intelligence (VIX, SPY/QQQ/DIA/IWM trend, treasury, gold)
  Section 1 — Portfolio health (P&L, top winners/losers, sector breakdown)
  Section 2 — Risk attention list (stop proximity, abnormal moves, drawdown)
  Section 3 — Today's calendar (placeholder — earnings/macro to be added later)

Output:
  - reports/daily/DAILY_MORNING_YYYY-MM-DD.md  (English, full report)
  - Telegram group message (Turkish, concise summary)

Designed to run pre-session (TR 14:00 or so). Safe to run multiple times per day;
output file is overwritten. Telegram delivery is gated by --send flag to allow
dry runs.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Repo root on sys.path so `agent.X` imports work when launched directly
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent.portfolio import get_positions, portfolio_metrics  # noqa: E402
from agent.fmp import (                                       # noqa: E402
    batch_quote, vix_quote, earnings_calendar, aftermarket_batch
)
from agent.telegram import send_to_group                       # noqa: E402

REPORTS_DIR = _REPO_ROOT / "reports" / "daily"
MACRO_SYMBOLS = ["SPY", "QQQ", "DIA", "IWM", "GLD", "TLT"]


# ---------- Section 0: Market intelligence ----------

def gather_macro() -> dict:
    """Fetch current quotes for the macro symbols + VIX."""
    quotes = batch_quote(MACRO_SYMBOLS)
    vix = vix_quote() or {}
    return {
        "macro": quotes,
        "vix": {
            "price": _safe_float(vix.get("price")),
            "change": _safe_float(vix.get("change")),
            "change_pct": _safe_float(vix.get("changePercentage")),
        },
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def _vix_regime(price: Optional[float]) -> str:
    if price is None:
        return "unknown"
    if price < 18:
        return "low (risk-on)"
    if price < 25:
        return "normal"
    if price < 30:
        return "elevated"
    if price < 35:
        return "high — K-13 warning"
    return "extreme — K-13 escalation"


# ---------- Section 1 & 2: Portfolio health ----------

def gather_portfolio() -> dict:
    """Load and enrich positions, compute aggregate metrics + breakdowns."""
    positions = get_positions(enrich=True)
    metrics = portfolio_metrics(positions)

    # Sector breakdown
    sectors: dict[str, dict] = defaultdict(lambda: {"count": 0, "value": 0.0, "cost": 0.0})
    for p in positions:
        sec = p.get("sector") or "—"
        sectors[sec]["count"] += 1
        sectors[sec]["cost"] += (p.get("entry_price") or 0) * (p.get("shares") or 0)
        if p.get("market_value") is not None:
            sectors[sec]["value"] += p["market_value"]

    # Sort positions by unrealized P&L%
    pnl_positions = [p for p in positions if p.get("unrealized_pnl_pct") is not None]
    winners = sorted(pnl_positions, key=lambda x: x["unrealized_pnl_pct"], reverse=True)[:3]
    losers = sorted(pnl_positions, key=lambda x: x["unrealized_pnl_pct"])[:3]

    # Risk attention
    stop_near = [
        p for p in positions
        if p.get("stop_distance_pct") is not None and p["stop_distance_pct"] < 5
    ]
    stop_near.sort(key=lambda x: x["stop_distance_pct"])

    return {
        "positions": positions,
        "metrics": metrics,
        "sectors": dict(sectors),
        "winners": winners,
        "losers": losers,
        "stop_near": stop_near,
    }


# ---------- Markdown report ----------

def render_report(macro: dict, portfolio: dict, today: str) -> str:
    lines: list[str] = []
    lines.append(f"# DAILY MORNING REPORT — {today}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now():%Y-%m-%d %H:%M %Z}*  ")
    lines.append("*Source: finzora ai (agent v2)*")
    lines.append("")

    # ---- Section 0: Market ----
    lines.append("## 0. Market intelligence")
    lines.append("")
    vix_price = macro["vix"]["price"]
    vix_chg = macro["vix"]["change_pct"]
    lines.append(f"**VIX:** {_fmt(vix_price)}"
                 + (f" ({vix_chg:+.2f}%)" if vix_chg is not None else "")
                 + f" — *regime: {_vix_regime(vix_price)}*")
    lines.append("")
    lines.append("| Symbol | Price | Day % | Note |")
    lines.append("|--------|------:|------:|------|")
    for sym in MACRO_SYMBOLS:
        q = macro["macro"].get(sym) or {}
        price = _safe_float(q.get("price"))
        chg = _safe_float(q.get("changePercentage"))
        note = _classify_macro_move(sym, chg)
        lines.append(f"| **{sym}** | {_fmt(price)} | {_fmt_pct(chg)} | {note} |")
    lines.append("")

    # ---- Section 1: Portfolio health ----
    m = portfolio["metrics"]
    lines.append("## 1. Portfolio health")
    lines.append("")
    lines.append(f"- **Open positions:** {m.get('position_count', 0)}")
    if "total_market_value" in m:
        lines.append(f"- **Market value:** ${m['total_market_value']:,.0f}")
        lines.append(f"- **Unrealized P&L:** {m['total_unrealized_pnl']:+,.0f} USD "
                     f"({m['total_unrealized_pnl_pct']:+.2f}%)")
    lines.append("")

    # Winners / losers
    if portfolio["winners"]:
        lines.append("### Top 3 winners")
        lines.append("")
        lines.append("| Symbol | Entry | Current | P&L % | Weight % |")
        lines.append("|--------|------:|--------:|------:|---------:|")
        for p in portfolio["winners"]:
            lines.append(
                f"| **{p['symbol']}** | ${p['entry_price']:.2f} | "
                f"${_fmt(p.get('current_price'))} | "
                f"{p['unrealized_pnl_pct']:+.2f}% | "
                f"{_fmt(p.get('weight_pct'))}% |"
            )
        lines.append("")

    if portfolio["losers"]:
        lines.append("### Bottom 3 losers")
        lines.append("")
        lines.append("| Symbol | Entry | Current | P&L % | Weight % |")
        lines.append("|--------|------:|--------:|------:|---------:|")
        for p in portfolio["losers"]:
            lines.append(
                f"| **{p['symbol']}** | ${p['entry_price']:.2f} | "
                f"${_fmt(p.get('current_price'))} | "
                f"{p['unrealized_pnl_pct']:+.2f}% | "
                f"{_fmt(p.get('weight_pct'))}% |"
            )
        lines.append("")

    # Sector breakdown
    if portfolio["sectors"]:
        lines.append("### Sector breakdown")
        lines.append("")
        lines.append("| Sector | Positions | Cost basis | Market value |")
        lines.append("|--------|----------:|-----------:|-------------:|")
        sorted_sectors = sorted(
            portfolio["sectors"].items(),
            key=lambda x: x[1]["cost"],
            reverse=True,
        )
        for sec, data in sorted_sectors:
            mv = f"${data['value']:,.0f}" if data["value"] > 0 else "—"
            lines.append(
                f"| {sec} | {data['count']} | ${data['cost']:,.0f} | {mv} |"
            )
        lines.append("")

    # ---- Section 2: Risk attention ----
    lines.append("## 2. Risk attention")
    lines.append("")
    if portfolio["stop_near"]:
        lines.append("### Stops within 5%")
        lines.append("")
        lines.append("| Symbol | Current | Stop | Distance | Status |")
        lines.append("|--------|--------:|-----:|---------:|--------|")
        for p in portfolio["stop_near"]:
            dist = p["stop_distance_pct"]
            if dist < 0:
                status = "🔴 STOP HIT"
            elif dist < 2:
                status = "🟡 NEAR (<2%)"
            else:
                status = "🟢 ok"
            lines.append(
                f"| **{p['symbol']}** | ${_fmt(p.get('current_price'))} | "
                f"${p['stop_loss']:.2f} | {dist:+.2f}% | {status} |"
            )
        lines.append("")
    else:
        lines.append("No positions within 5% of stop. ✅")
        lines.append("")

    # ---- Section 3: Calendar (placeholder) ----
    lines.append("## 3. Today's calendar")
    lines.append("")
    lines.append("*Earnings + macro release schedule — to be wired in next iteration.*")
    lines.append("")

    return "\n".join(lines)


def _fetch_today_earnings(symbols: set[str], today: str) -> list[dict]:
    """
    Bugün earnings açıklayacak portföy sembollerini döndür.
    Sabah TR 16:00 = ET 09:00 (pre-market). Bugün BMO veya AMC olabilir,
    FMP stable endpoint time/timing field vermiyor — sadece tarih.
    """
    try:
        cal = earnings_calendar(today, today)
        return [e for e in cal if e.get("symbol") in symbols]
    except Exception as e:
        print(f"[morning] earnings_calendar failed: {e}")
        return []


def _fetch_premarket_movers(positions: list[dict]) -> list[dict]:
    """
    Portföy pozisyonları için pre-market hareketi (>1.5% mutlak) tespiti.
    Aftermarket-quote endpoint mid (bid+ask)/2 verir; previousClose ile
    karşılaştırılarak % değişim hesaplanır.
    Graceful: data yoksa veya endpoint hata verirse boş döner.
    """
    syms = [p.get("symbol") for p in positions if p.get("symbol")]
    if not syms:
        return []
    try:
        am = aftermarket_batch(syms)
    except Exception as e:
        print(f"[morning] aftermarket_batch failed: {e}")
        return []
    if not am:
        return []

    movers = []
    for p in positions:
        sym = p.get("symbol")
        prev_close = _safe_float(p.get("current_price"))  # dünkü kapanış (enrich price)
        am_data = am.get(sym) or {}
        bid = _safe_float(am_data.get("bidPrice"))
        ask = _safe_float(am_data.get("askPrice"))
        if not (bid and ask and prev_close):
            continue
        mid = (bid + ask) / 2
        if mid <= 0:
            continue
        chg_pct = (mid - prev_close) / prev_close * 100
        if abs(chg_pct) >= 1.5:
            movers.append({
                "symbol": sym,
                "premarket_price": round(mid, 2),
                "prev_close": prev_close,
                "premarket_chg_pct": round(chg_pct, 2),
            })
    movers.sort(key=lambda x: abs(x["premarket_chg_pct"]), reverse=True)
    return movers


def render_telegram_summary(macro: dict, portfolio: dict, today: str) -> str:
    """
    Sabah raporu Telegram özeti — AKSIYON ODAKLI format (2026-05-15 yeni).

    Yapı:
      • Piyasa başlığı (VIX/SPY/QQQ)
      • ⚠ Stop'a yakın pozisyonlar (stop_distance < 3%)
      • 🎯 Hedefe yakın pozisyonlar (target_distance < 5%)
      • 📅 Bugün earnings açıklayacak portföy hisseleri
      • 🌐 Pre-market'te hareketli portföy hisseleri (|chg| ≥ 1.5%)
      • 📊 Alt özet (pozitif/toplam, ortalama K/Z%)

    Dolar tutarları (toplam piyasa değeri, P&K USD) tamamen çıkarıldı.
    Premarket data graceful — endpoint başarısız olursa o blok atlanır.
    """
    vix_price = macro["vix"]["price"]
    spy = macro["macro"].get("SPY", {})
    qqq = macro["macro"].get("QQQ", {})
    positions = portfolio["positions"]
    sortable = [p for p in positions if p.get("unrealized_pnl_pct") is not None]

    lines = [
        f"<b>🌅 SABAH — {today}</b>",
        "",
        f"📊 VIX {_fmt(vix_price)} ({_vix_regime(vix_price)}) | "
        f"SPY {_fmt_pct(_safe_float(spy.get('changePercentage')))} | "
        f"QQQ {_fmt_pct(_safe_float(qqq.get('changePercentage')))}",
        "",
    ]

    # ---- STOP'A YAKIN ----
    stop_near = [
        p for p in positions
        if p.get("stop_distance_pct") is not None and p["stop_distance_pct"] < 3
    ]
    stop_near.sort(key=lambda x: x["stop_distance_pct"])
    if stop_near:
        lines.append(f"⚠️ <b>STOP'A YAKIN</b> ({len(stop_near)}):")
        for p in stop_near:
            cp = _safe_float(p.get("current_price"))
            sl = _safe_float(p.get("stop_loss"))
            dist = p["stop_distance_pct"]
            tag = " <b>STOP ALTI!</b>" if dist < 0 else ""
            lines.append(
                f"  <b>{p['symbol']}</b>: ${_fmt(cp)} → stop ${_fmt(sl)} "
                f"({dist:+.2f}%){tag}"
            )
        lines.append("")

    # ---- HEDEFE YAKIN ----
    target_near = [
        p for p in positions
        if p.get("target_distance_pct") is not None and 0 <= p["target_distance_pct"] < 5
    ]
    target_near.sort(key=lambda x: x["target_distance_pct"])
    # Hedefi geçenler ayrı: target_distance < 0
    target_passed = [
        p for p in positions
        if p.get("target_distance_pct") is not None and p["target_distance_pct"] < 0
    ]
    if target_passed:
        lines.append(f"🎯 <b>HEDEF GEÇİLDİ</b> ({len(target_passed)}) — kar alımı düşün:")
        for p in target_passed:
            cp = _safe_float(p.get("current_price"))
            tg = _safe_float(p.get("target"))
            pnl = p.get("unrealized_pnl_pct")
            lines.append(
                f"  <b>{p['symbol']}</b>: ${_fmt(cp)} > target ${_fmt(tg)} "
                f"(K/Z: {_fmt_pct(pnl)})"
            )
        lines.append("")
    if target_near:
        lines.append(f"🎯 <b>HEDEFE YAKIN</b> ({len(target_near)}):")
        for p in target_near:
            cp = _safe_float(p.get("current_price"))
            tg = _safe_float(p.get("target"))
            dist = p["target_distance_pct"]
            lines.append(
                f"  <b>{p['symbol']}</b>: ${_fmt(cp)} → target ${_fmt(tg)} "
                f"({dist:+.2f}% kaldı)"
            )
        lines.append("")

    # ---- BUGÜN EARNINGS ----
    portfolio_syms = {p.get("symbol") for p in positions if p.get("symbol")}
    earnings_today = _fetch_today_earnings(portfolio_syms, today)
    if earnings_today:
        lines.append(f"📅 <b>BUGÜN EARNINGS</b> ({len(earnings_today)}):")
        for e in earnings_today:
            eps_est = e.get("epsEstimated")
            rev_est = e.get("revenueEstimated")
            details = []
            if eps_est is not None:
                details.append(f"EPS est ${eps_est:.2f}")
            if rev_est:
                details.append(f"rev est ${rev_est/1e9:.2f}B")
            detail_s = f" — {', '.join(details)}" if details else ""
            lines.append(f"  <b>{e['symbol']}</b>{detail_s}")
        lines.append("")

    # ---- PREMARKET HAREKETLİ ----
    premarket = _fetch_premarket_movers(positions)
    if premarket:
        lines.append(f"🌐 <b>PREMARKET HAREKETLİ</b> ({len(premarket)}):")
        for m in premarket[:5]:
            arrow = "↑" if m["premarket_chg_pct"] > 0 else "↓"
            lines.append(
                f"  {arrow} <b>{m['symbol']}</b>: ${m['prev_close']:.2f} → "
                f"${m['premarket_price']:.2f} ({m['premarket_chg_pct']:+.2f}%)"
            )
        lines.append("")

    # ---- ALT ÖZET ----
    if sortable:
        wins = sum(1 for p in sortable if p["unrealized_pnl_pct"] > 0)
        avg = sum(p["unrealized_pnl_pct"] for p in sortable) / len(sortable)
        lines.append(
            f"📊 {len(sortable)} pozisyon | Pozitif: <b>{wins}/{len(sortable)}</b> | "
            f"Ort. K/Z: <b>{avg:+.2f}%</b>"
        )

    lines.append("")
    lines.append("<i>Detay: reports/daily/ klasöründe</i>")
    return "\n".join(lines)


# ---------- Helpers ----------

def _safe_float(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def _fmt(x, dp: int = 2) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):,.{dp}f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(x, dp: int = 2) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):+.{dp}f}%"
    except (TypeError, ValueError):
        return "—"


def _classify_macro_move(sym: str, chg: Optional[float]) -> str:
    """Light annotation: arrow + magnitude tag."""
    if chg is None:
        return "—"
    if chg >= 1.5:
        return "🟢 strong up"
    if chg >= 0.3:
        return "🟢 up"
    if chg <= -1.5:
        return "🔴 strong down"
    if chg <= -0.3:
        return "🔴 down"
    return "↔ flat"


# ---------- Main entry point ----------

def generate_morning_report(send_telegram: bool = False) -> dict:
    """
    Build today's morning report. Returns a dict with paths and counts.

    Side effects:
      - writes reports/daily/DAILY_MORNING_<date>.md
      - if send_telegram: posts a Turkish summary to the Finzora group
    """
    today = datetime.now().strftime("%Y-%m-%d")

    macro = gather_macro()
    portfolio = gather_portfolio()

    report_md = render_report(macro, portfolio, today)
    telegram_summary = render_telegram_summary(macro, portfolio, today)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"DAILY_MORNING_{today}.md"
    report_path.write_text(report_md, encoding="utf-8")

    sent_to_group = False
    if send_telegram:
        sent_to_group = send_to_group(telegram_summary, parse_mode="HTML")

    return {
        "report_path": str(report_path),
        "report_size_chars": len(report_md),
        "telegram_sent": sent_to_group,
        "telegram_preview_lines": telegram_summary.count("\n") + 1,
    }


def _cli():
    import argparse
    p = argparse.ArgumentParser(description="Generate daily morning report.")
    p.add_argument("--send", action="store_true",
                   help="Post Turkish summary to Finzora group chat")
    args = p.parse_args()

    result = generate_morning_report(send_telegram=args.send)
    print(f"Report written: {result['report_path']}")
    print(f"Size:           {result['report_size_chars']:,} chars")
    print(f"Telegram sent:  {result['telegram_sent']}"
          + ("" if args.send else " (use --send to deliver)"))


if __name__ == "__main__":
    _cli()
