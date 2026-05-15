"""
Tarihsel signals.jsonl uzerinden Price-Target Gap Gate replay analizi.

Her tarihsel sinyali alir, mevcut fiyat/hedef verisi ile yeni gate'i
uygular ve karar farklarini raporlar.

15 May 2026 — VIK gozleminden dogan gate icin retroaktif degerlendirme.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent" / "legacy"))

from agent.legacy.analist_takip.signal_analyzer import (
    price_target_gap_gate,
    _apply_gate_cap,
)
from agent.legacy.analist_takip.revision_fetcher import get_target_consensus


SIGNALS_PATH = "data/analist_takip/signals.jsonl"


def load_signals():
    p = Path(SIGNALS_PATH)
    if not p.exists():
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def replay():
    signals = load_signals()
    print(f"\n=== PRICE-TARGET GAP GATE REPLAY ===")
    print(f"Tarihsel sinyal sayisi: {len(signals)}\n")

    if not signals:
        print("Hic tarihsel sinyal yok — replay atlandi.")
        return

    rows = []
    summary = {"unchanged": 0, "downgraded": 0, "no_data": 0}

    for s in signals:
        ticker = s["ticker"]
        original_decision = s["decision"]
        current_price = s.get("current_price")

        # Tarihsel kayitlarda target_consensus yok — FMP'den live cek
        # NOT: Tarihsel anda kapanis fiyati ile karsilastirmiyoruz, su anki
        # consensus ile karsilastiriyoruz (kabaca yaklasik gosterge).
        try:
            target_consensus = get_target_consensus(ticker)
        except Exception as e:
            target_consensus = None

        gate = price_target_gap_gate(current_price, target_consensus)

        if not gate["enabled"]:
            summary["no_data"] += 1
            rows.append({
                "ticker": ticker,
                "orig": original_decision,
                "new": original_decision,
                "gap": "NO_DATA",
                "note": gate["reason"],
            })
            continue

        new_decision = _apply_gate_cap(original_decision, gate["max_decision"])

        if new_decision != original_decision:
            summary["downgraded"] += 1
        else:
            summary["unchanged"] += 1

        rows.append({
            "ticker": ticker,
            "orig": original_decision,
            "new": new_decision,
            "gap": gate["gap_quality"],
            "upside_avg": gate["upside_avg_pct"],
            "upside_max": gate["upside_max_pct"],
            "rr": gate["risk_reward"],
            "current_price": current_price,
        })

    # Tablo
    print(f"{'Ticker':<8} {'Original':<14} {'New':<14} {'Gap':<8} {'Avg%':>8} {'Max%':>8} {'R/R':>6}")
    print("-" * 80)
    for r in rows:
        avg = f"{r['upside_avg']:+.1f}" if r.get("upside_avg") is not None else "-"
        mx = f"{r['upside_max']:+.1f}" if r.get("upside_max") is not None else "-"
        rr = f"{r['rr']:.2f}" if r.get("rr") is not None else "-"
        flag = "  ⚠️ DROPPED" if r["orig"] != r["new"] else ""
        print(f"{r['ticker']:<8} {r['orig']:<14} {r['new']:<14} {r['gap']:<8} {avg:>8} {mx:>8} {rr:>6}{flag}")

    print()
    print(f"Sonuc ozeti:")
    print(f"  Degismedi:  {summary['unchanged']}")
    print(f"  Dusuruldu:  {summary['downgraded']}")
    print(f"  Veri yok:   {summary['no_data']}")

    # AL kararlari icin ayri kirilim
    al_signals = [r for r in rows if r["orig"] in ("BUY", "STRONG_BUY")]
    if al_signals:
        al_dropped = [r for r in al_signals if r["orig"] != r["new"]]
        print(f"\nAL kararlari ({len(al_signals)} toplam):")
        print(f"  Gate sonrasi dusurulen: {len(al_dropped)} ({len(al_dropped)/len(al_signals)*100:.0f}%)")


if __name__ == "__main__":
    replay()
