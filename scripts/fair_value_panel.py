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


def discover_undervalued_tickers(
    min_potential_pct: float = 25.0,
    universe: Optional[list[str]] = None,
) -> dict:
    """
    Aşama 3 (13 May 2026): Geniş evren tarama (analist_takip'in evreni ~200
    ticker) ile %25+ analyst target potansiyeli olan hisseleri keşfet ve
    watchlist'e ekle.

    Mantık (Zeynel standardı):
        FV = (en yeni analyst hedef + en yüksek hedef) / 2
        potansiyel_pct = (FV - current_price) / current_price * 100
        Eğer potansiyel_pct >= 25 → watchlist'e ekle

    Args:
        min_potential_pct: Threshold (default %25)
        universe: Opsiyonel — özel ticker listesi. None ise analist_takip
                  evreni kullanılır.

    Returns:
        {"scanned": N, "discovered": N, "added": [(sym, pct)]}
    """
    if universe is not None:
        tickers = universe
    else:
        try:
            from agent.legacy.analist_takip.watchlist import build_watchlist
        except ImportError as e:
            print(f"[fair_value] discover import hatası: {e}")
            return {"scanned": 0, "discovered": 0, "added": []}

        try:
            u = build_watchlist()
            if isinstance(u, dict):
                tickers = list(u.keys()) if u else []
            else:
                tickers = list(u)
        except Exception as e:
            print(f"[fair_value] universe oluşturulamadı: {e}")
            return {"scanned": 0, "discovered": 0, "added": []}

    try:
        from agent.watchlist import add as wl_add, is_in_pool, is_in_portfolio, is_excluded
    except ImportError as e:
        print(f"[fair_value] watchlist import hatası: {e}")
        return {"scanned": 0, "discovered": 0, "added": []}

    if not tickers:
        return {"scanned": 0, "discovered": 0, "added": []}

    print(f"[fair_value] Geniş evren tarama: {len(tickers)} ticker")
    discovered = []
    added = []

    for symbol in tickers:
        # Skip eğer zaten portföyde, watchlist'te veya excluded
        if is_in_portfolio(symbol) or is_in_pool(symbol) or is_excluded(symbol):
            continue

        try:
            quote = fmp_get("quote", {"symbol": symbol})
            if not quote or not isinstance(quote, list):
                continue
            current = quote[0].get("price")
            if not current or current <= 0:
                continue

            targets = fetch_analyst_targets(symbol)
            fv = compute_fair_value(targets)
            if not fv:
                continue

            potential_pct = (fv["fair_value"] - current) / current * 100
            if potential_pct < min_potential_pct:
                continue

            discovered.append((symbol, potential_pct, fv["fair_value"]))

            # Asama 8 (14 May 2026): LLM gate — her sinyal AI'dan gecer
            try:
                from agent.ai_gate import evaluate_signal as ai_gate_eval
                gate_result = ai_gate_eval(
                    symbol=symbol,
                    signal_type="fair_value_iskonto",
                    signal_data={
                        "fair_value": fv["fair_value"],
                        "current_price": current,
                        "potential_pct": round(potential_pct, 2),
                        "latest_target": fv["latest_target"],
                        "highest_target": fv["highest_target"],
                        "sample_size": fv["sample_size"],
                    },
                )
                if gate_result["action"] != "EKLE":
                    print(f"[fair_value] {symbol} AI gate REDDETTI: {gate_result['reason']}")
                    continue
                ai_score = gate_result["score"]
                ai_reason = gate_result["reason"]
                ai_theme = gate_result.get("theme_match")
                ai_cautions = gate_result.get("cautions", [])
            except Exception as e:
                print(f"[fair_value] {symbol} AI gate hatası: {e} — eski mantığa fallback")
                ai_score = 50
                ai_reason = "AI gate başarısız"
                ai_theme = None
                ai_cautions = ["gate_failed"]

            # Watchlist'e ekle (AI onayı + zenginleştirme ile)
            result = wl_add(
                symbol=symbol,
                source="analyst_target_discount",
                rationale=f"FV ${fv['fair_value']:.2f} = +%{potential_pct:.1f} "
                          f"(en yeni ${fv['latest_target']}, en yüksek ${fv['highest_target']}) "
                          f"+ AI gate: {ai_reason}",
                price=current,
                score=ai_score,
                score_components={
                    "fair_value_discount_pct": round(potential_pct, 2),
                    "fair_value_target": fv["fair_value"],
                    "fair_value_latest_target": fv["latest_target"],
                    "fair_value_highest_target": fv["highest_target"],
                    "fair_value_sample_size": fv["sample_size"],
                    "ai_gate": {
                        "score": ai_score,
                        "theme_match": ai_theme,
                        "cautions": ai_cautions,
                    },
                },
            )
            if result["action"] == "added":
                added.append((symbol, potential_pct))
        except Exception as e:
            print(f"[fair_value] {symbol} discover hatası: {e}")
            continue

    if discovered:
        print(f"[fair_value] %{min_potential_pct:.0f}+ potansiyel: {len(discovered)} keşfedildi")
        for sym, pct, fv in sorted(discovered, key=lambda x: -x[1])[:10]:
            in_pool_marker = "✓ EKLENDİ" if any(s == sym for s, _ in added) else "(zaten var)"
            print(f"  {sym}: +%{pct:.1f} (FV ${fv:.2f}) {in_pool_marker}")

    return {
        "scanned": len(tickers),
        "discovered": len(discovered),
        "added": added,
    }


def update_watchlist_fair_values() -> dict:
    """
    Aşama 3 (13 May 2026): Watchlist hisseleri için adil değer hesapla,
    score_components.fair_value_discount_pct alanını güncelle.

    Rapor formatını değiştirmez — sessiz update. AI orchestrator (Aşama 5)
    bu skorları okur ve "öncelikli alım" önerilerinde kullanır.

    Returns:
        {"checked": N, "updated": N, "deep_discounts": [(sym, disc)]}
    """
    try:
        from agent.watchlist import all_symbols, add as wl_add
    except ImportError:
        return {"checked": 0, "updated": 0, "deep_discounts": []}

    symbols = all_symbols()
    if not symbols:
        return {"checked": 0, "updated": 0, "deep_discounts": []}

    print(f"[fair_value] Watchlist tarama: {len(symbols)} ticker")
    deep_discounts = []  # %25+ iskontolu olanlar (Zeynel standardı)
    updated = 0

    for symbol in symbols:
        try:
            # Current price — FMP quote
            quote = fmp_get("quote", {"symbol": symbol})
            if not quote or not isinstance(quote, list):
                continue
            current = quote[0].get("price")
            if not current:
                continue

            # Fair value calculation (aynı portfolyo akışıyla)
            targets = fetch_analyst_targets(symbol)
            fv = compute_fair_value(targets)
            if not fv:
                continue

            disc = discount_pct(current, fv["fair_value"])
            if disc is None:
                continue

            # Sessiz update — multi-source merge
            wl_add(
                symbol=symbol,
                source="fair_value_panel",
                rationale=f"FV ${fv['fair_value']:.2f}, %{disc:+.1f} iskonto",
                score_components={
                    "fair_value_discount_pct": round(disc, 2),
                    "fair_value_target": fv["fair_value"],
                    "fair_value_latest_target": fv["latest_target"],
                    "fair_value_highest_target": fv["highest_target"],
                    "fair_value_sample_size": fv["sample_size"],
                },
            )
            updated += 1

            if disc >= 25:
                deep_discounts.append((symbol, disc, fv["fair_value"]))
        except Exception as e:
            print(f"[fair_value] {symbol} hata: {e}")
            continue

    if deep_discounts:
        print(f"[fair_value] %25+ iskontolu watchlist: {len(deep_discounts)}")
        for sym, disc, fv in sorted(deep_discounts, key=lambda x: -x[1]):
            print(f"  {sym}: %{disc:.1f} (FV ${fv:.2f})")

    return {
        "checked": len(symbols),
        "updated": updated,
        "deep_discounts": deep_discounts,
    }


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

    # Aşama 3 (13 May 2026): Watchlist hisselerinin adil değer skorlarını
    # da güncelle (sessiz update — rapor formatı değişmez, AI orchestrator
    # bu bilgiyi kullanır).
    try:
        wl_result = update_watchlist_fair_values()
        if wl_result["updated"]:
            print(f"[fair_value] Watchlist score_components güncellendi: "
                  f"{wl_result['updated']}/{wl_result['checked']} ticker")
    except Exception as e:
        print(f"[fair_value] Watchlist tarama hatası: {e}")

    # Aşama 3 (13 May 2026): Geniş evren tarama — %25+ analyst target
    # potansiyeli olan yeni hisseleri keşfet, watchlist'e ekle.
    try:
        disc_result = discover_undervalued_tickers(min_potential_pct=25.0)
        if disc_result["added"]:
            print(f"[fair_value] Watchlist'e {len(disc_result['added'])} yeni hisse eklendi (%25+ potansiyel)")
    except Exception as e:
        print(f"[fair_value] Discover hatası: {e}")

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
