#!/usr/bin/env python3
"""
Trade Autopsy & Parameter Optimizer
Analyzes closed trades, finds patterns, suggests parameter changes.

Usage:
    python3 autopsy.py                    # Analiz et
    python3 autopsy.py --apply            # Parametreleri otomatik güncelle
    python3 autopsy.py --report           # Haftalık rapor oluştur
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
REPORTS_DIR = SCRIPT_DIR.parent / "reports"

MIN_TRADES_FOR_OPTIMIZATION = 15  # Minimum trade sayısı parametre değişikliği için


def load_json(filename: str) -> any:
    path = DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def save_json(filename: str, data: any):
    with open(DATA_DIR / filename, "w") as f:
        json.dump(data, f, indent=2)


def analyze_results(results: list) -> dict:
    """Kapanmış trade'lerin derinlemesine analizi"""

    if not results:
        return {"error": "No results to analyze"}

    analysis = {
        "total_trades": len(results),
        "analysis_date": datetime.now().isoformat(),
    }

    # ═══════════════════════════════════════════════════════════════
    # 1. GENEL İSTATİSTİKLER
    # ═══════════════════════════════════════════════════════════════

    wins = [r for r in results if r["exit"]["pnl_pct"] > 0]
    losses = [r for r in results if r["exit"]["pnl_pct"] <= 0]
    pnls = [r["exit"]["pnl_pct"] for r in results]

    analysis["overall"] = {
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": round(len(wins) / len(results) * 100, 1),
        "avg_pnl_pct": round(sum(pnls) / len(pnls), 2),
        "avg_win_pct": round(sum(r["exit"]["pnl_pct"] for r in wins) / len(wins), 2) if wins else 0,
        "avg_loss_pct": round(sum(r["exit"]["pnl_pct"] for r in losses) / len(losses), 2) if losses else 0,
        "best_trade": max(pnls),
        "worst_trade": min(pnls),
        "avg_hold_days": round(sum(r["exit"]["days_held"] for r in results) / len(results), 1),
        "profit_factor": round(
            abs(sum(r["exit"]["pnl_pct"] for r in wins)) /
            abs(sum(r["exit"]["pnl_pct"] for r in losses))
            if losses else 999, 2
        ),
    }

    # Expectancy
    wr = len(wins) / len(results)
    avg_w = analysis["overall"]["avg_win_pct"]
    avg_l = abs(analysis["overall"]["avg_loss_pct"])
    analysis["overall"]["expectancy"] = round(wr * avg_w - (1 - wr) * avg_l, 2)

    # ═══════════════════════════════════════════════════════════════
    # 2. STRATEJİ BAZLI ANALİZ
    # ═══════════════════════════════════════════════════════════════

    by_strategy = defaultdict(list)
    for r in results:
        by_strategy[r.get("strategy", "UNKNOWN")].append(r)

    analysis["by_strategy"] = {}
    for strat, trades in by_strategy.items():
        strat_wins = [t for t in trades if t["exit"]["pnl_pct"] > 0]
        strat_pnls = [t["exit"]["pnl_pct"] for t in trades]
        analysis["by_strategy"][strat] = {
            "count": len(trades),
            "win_rate_pct": round(len(strat_wins) / len(trades) * 100, 1),
            "avg_pnl_pct": round(sum(strat_pnls) / len(strat_pnls), 2),
            "avg_hold_days": round(sum(t["exit"]["days_held"] for t in trades) / len(trades), 1),
        }

    # ═══════════════════════════════════════════════════════════════
    # 3. SEKTÖR BAZLI ANALİZ
    # ═══════════════════════════════════════════════════════════════

    by_sector = defaultdict(list)
    for r in results:
        by_sector[r.get("sector", "Unknown")].append(r)

    analysis["by_sector"] = {}
    for sector, trades in by_sector.items():
        sector_wins = [t for t in trades if t["exit"]["pnl_pct"] > 0]
        analysis["by_sector"][sector] = {
            "count": len(trades),
            "win_rate_pct": round(len(sector_wins) / len(trades) * 100, 1) if trades else 0,
            "avg_pnl_pct": round(sum(t["exit"]["pnl_pct"] for t in trades) / len(trades), 2),
        }

    # ═══════════════════════════════════════════════════════════════
    # 4. ÇIKIŞ NEDENİ ANALİZİ
    # ═══════════════════════════════════════════════════════════════

    by_exit = defaultdict(list)
    for r in results:
        by_exit[r["exit"]["reason"]].append(r)

    analysis["by_exit_reason"] = {}
    for reason, trades in by_exit.items():
        analysis["by_exit_reason"][reason] = {
            "count": len(trades),
            "avg_pnl_pct": round(sum(t["exit"]["pnl_pct"] for t in trades) / len(trades), 2),
            "pct_of_total": round(len(trades) / len(results) * 100, 1)
        }

    # ═══════════════════════════════════════════════════════════════
    # 5. MFE/MAE ANALİZİ (Excursion)
    # ═══════════════════════════════════════════════════════════════

    mfes = [r["excursion"]["mfe_pct"] for r in results if "excursion" in r]
    maes = [r["excursion"]["mae_pct"] for r in results if "excursion" in r]
    captures = [r["excursion"]["capture_ratio"] for r in results
                if "excursion" in r and r["excursion"]["capture_ratio"] > 0]

    analysis["excursion"] = {
        "avg_mfe_pct": round(sum(mfes) / len(mfes), 2) if mfes else 0,
        "avg_mae_pct": round(sum(maes) / len(maes), 2) if maes else 0,
        "avg_capture_ratio": round(sum(captures) / len(captures), 1) if captures else 0,
        "insight": ""
    }

    # Capture ratio insight
    avg_cap = analysis["excursion"]["avg_capture_ratio"]
    if avg_cap < 30:
        analysis["excursion"]["insight"] = "Çıkışlar çok erken — kazançların sadece %{:.0f}'ini yakalıyorsun. Trailing stop'u gevşet.".format(avg_cap)
    elif avg_cap > 80:
        analysis["excursion"]["insight"] = "Çıkış zamanlaması mükemmel — kazançların %{:.0f}'ini yakalıyorsun.".format(avg_cap)
    else:
        analysis["excursion"]["insight"] = "Çıkış zamanlaması orta — kazançların %{:.0f}'ini yakalıyorsun.".format(avg_cap)

    # ═══════════════════════════════════════════════════════════════
    # 6. ALTERNATİF SENARYO ANALİZİ
    # ═══════════════════════════════════════════════════════════════

    alt_totals = defaultdict(list)
    for r in results:
        for key, val in r.get("alternative_scenarios", {}).items():
            if val is not None:
                alt_totals[key].append(val)

    analysis["alternative_scenarios"] = {}
    for key, vals in alt_totals.items():
        analysis["alternative_scenarios"][key] = {
            "avg_pnl_pct": round(sum(vals) / len(vals), 2),
            "count": len(vals)
        }

    # ═══════════════════════════════════════════════════════════════
    # 7. POST-EXIT ANALİZİ (Erken çıkış mı?)
    # ═══════════════════════════════════════════════════════════════

    left_on_table = [r["post_exit"]["left_on_table"]
                     for r in results
                     if "post_exit" in r and r["post_exit"].get("left_on_table")]

    analysis["post_exit"] = {
        "avg_left_on_table_pct": round(sum(left_on_table) / len(left_on_table), 2) if left_on_table else 0,
        "trades_with_missed_gains": len([x for x in left_on_table if x > 3]),
        "insight": ""
    }

    avg_lot = analysis["post_exit"]["avg_left_on_table_pct"]
    if avg_lot > 5:
        analysis["post_exit"]["insight"] = f"Ortalama %{avg_lot:.1f} masada bırakıyorsun. Hold süresini veya trailing stop'u genilet."

    return analysis


def generate_recommendations(analysis: dict) -> list:
    """Analiz sonuçlarından parametre önerileri üret"""
    recs = []

    total = analysis.get("total_trades", 0)
    if total < MIN_TRADES_FOR_OPTIMIZATION:
        recs.append({
            "type": "INFO",
            "message": f"Henüz {total} trade var, minimum {MIN_TRADES_FOR_OPTIMIZATION} gerekli. Öneriler güvenilir değil.",
            "confidence": "LOW"
        })
        return recs

    overall = analysis.get("overall", {})

    # Win rate çok düşük
    if overall.get("win_rate_pct", 0) < 40:
        recs.append({
            "type": "ENTRY",
            "param": "min_score",
            "current": 65,
            "suggested": 75,
            "reason": f"Win rate çok düşük (%{overall['win_rate_pct']}). Sinyal kalitesini artır.",
            "confidence": "HIGH"
        })

    # Stop loss çok sık tetikleniyor
    exit_reasons = analysis.get("by_exit_reason", {})
    stop_pct = exit_reasons.get("STOP_LOSS", {}).get("pct_of_total", 0)
    if stop_pct > 40:
        recs.append({
            "type": "EXIT",
            "param": "stop_loss_pct",
            "current": -7.0,
            "suggested": -10.0,
            "reason": f"Stop loss %{stop_pct:.0f} oranında tetikleniyor. Stop'u genilet.",
            "confidence": "MEDIUM"
        })

    # Trailing stop erken çıkış
    trail_pct = exit_reasons.get("TRAILING_STOP", {}).get("pct_of_total", 0)
    left_on_table = analysis.get("post_exit", {}).get("avg_left_on_table_pct", 0)
    if trail_pct > 30 and left_on_table > 3:
        recs.append({
            "type": "EXIT",
            "param": "trailing_stop_pct",
            "current": -5.0,
            "suggested": -7.0,
            "reason": f"Trailing stop %{trail_pct:.0f} tetikleniyor ve ortalama %{left_on_table:.1f} masada kalıyor.",
            "confidence": "HIGH"
        })

    # Timeout çok fazla
    timeout_pct = exit_reasons.get("TIMEOUT", {}).get("pct_of_total", 0)
    timeout_avg_pnl = exit_reasons.get("TIMEOUT", {}).get("avg_pnl_pct", 0)
    if timeout_pct > 30 and timeout_avg_pnl < 0:
        recs.append({
            "type": "EXIT",
            "param": "max_hold_days",
            "current": 15,
            "suggested": 10,
            "reason": f"Timeout'lar %{timeout_pct:.0f} ve ortalama {timeout_avg_pnl:+.1f}%. Süresi dolanlarda para kaybediyorsun.",
            "confidence": "MEDIUM"
        })

    # Strateji bazlı öneriler
    by_strat = analysis.get("by_strategy", {})
    for strat, stats in by_strat.items():
        if stats["count"] >= 5 and stats["win_rate_pct"] < 30:
            recs.append({
                "type": "STRATEGY",
                "param": f"disable_{strat.lower()}",
                "reason": f"{strat} stratejisi sadece %{stats['win_rate_pct']} win rate. Devre dışı bırakmayı düşün.",
                "confidence": "MEDIUM"
            })

    # Sektör bazlı öneriler
    by_sector = analysis.get("by_sector", {})
    for sector, stats in by_sector.items():
        if stats["count"] >= 3 and stats["avg_pnl_pct"] < -3:
            recs.append({
                "type": "SECTOR",
                "param": f"avoid_{sector.lower().replace(' ', '_')}",
                "reason": f"{sector} sektöründe ortalama {stats['avg_pnl_pct']:+.1f}% getiri. Bu sektörden kaçın.",
                "confidence": "MEDIUM" if stats["count"] >= 5 else "LOW"
            })

    # Alternatif senaryo bazlı
    alt = analysis.get("alternative_scenarios", {})
    current_avg = overall.get("avg_pnl_pct", 0)
    best_alt = None
    best_alt_pnl = current_avg

    for key, val in alt.items():
        if val["avg_pnl_pct"] > best_alt_pnl and val["count"] >= 10:
            best_alt = key
            best_alt_pnl = val["avg_pnl_pct"]

    if best_alt and best_alt_pnl > current_avg + 1.0:
        recs.append({
            "type": "OPTIMIZATION",
            "param": best_alt,
            "current_avg_pnl": current_avg,
            "suggested_avg_pnl": best_alt_pnl,
            "reason": f"'{best_alt}' parametresiyle ortalama getiri {current_avg:+.1f}%'den {best_alt_pnl:+.1f}%'e çıkar.",
            "confidence": "HIGH"
        })

    return recs


def apply_recommendations(recs: list, params: dict) -> dict:
    """Önerileri strategy_params.json'a uygula"""
    changes = []
    for rec in recs:
        if rec.get("confidence") != "HIGH":
            continue
        if rec["type"] == "ENTRY" and "suggested" in rec:
            old = params.get("entry_rules", {}).get(rec["param"])
            params.setdefault("entry_rules", {})[rec["param"]] = rec["suggested"]
            changes.append(f"{rec['param']}: {old} → {rec['suggested']}")
        elif rec["type"] == "EXIT" and "suggested" in rec:
            old = params.get("exit_rules", {}).get(rec["param"])
            params.setdefault("exit_rules", {})[rec["param"]] = rec["suggested"]
            changes.append(f"{rec['param']}: {old} → {rec['suggested']}")

    if changes:
        # Version bump
        params["version"] = params.get("version", 1) + 1
        params["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        params.setdefault("update_history", []).append({
            "date": datetime.now().isoformat(),
            "version": params["version"],
            "changes": changes
        })
    return params


def generate_report(analysis: dict, recs: list) -> str:
    """Markdown rapor oluştur"""
    lines = []
    o = analysis.get("overall", {})

    lines.append(f"# 📊 Swing Trade Otopsi Raporu")
    lines.append(f"**Tarih:** {analysis.get('analysis_date', '')[:10]}")
    lines.append(f"**Toplam Trade:** {analysis.get('total_trades', 0)}")
    lines.append("")

    lines.append(f"## Genel Performans")
    lines.append("")
    lines.append(f"| Metrik | Değer |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Win Rate | %{o.get('win_rate_pct', 0)} ({o.get('win_count', 0)}/{analysis.get('total_trades', 0)}) |")
    lines.append(f"| Ortalama Getiri | {o.get('avg_pnl_pct', 0):+.2f}% |")
    lines.append(f"| Ort. Kazanç | {o.get('avg_win_pct', 0):+.2f}% |")
    lines.append(f"| Ort. Kayıp | {o.get('avg_loss_pct', 0):.2f}% |")
    lines.append(f"| Profit Factor | {o.get('profit_factor', 0)} |")
    lines.append(f"| Expectancy | {o.get('expectancy', 0):+.2f}% |")
    lines.append(f"| Ort. Holding | {o.get('avg_hold_days', 0)} gün |")
    lines.append("")

    # Strateji
    lines.append(f"## Strateji Bazlı")
    lines.append("")
    for strat, stats in analysis.get("by_strategy", {}).items():
        emoji = "✅" if stats["avg_pnl_pct"] > 0 else "❌"
        lines.append(f"- {emoji} **{strat}**: {stats['count']} trade, %{stats['win_rate_pct']} WR, {stats['avg_pnl_pct']:+.1f}% avg")
    lines.append("")

    # Sektör
    lines.append(f"## Sektör Bazlı")
    lines.append("")
    for sector, stats in sorted(analysis.get("by_sector", {}).items(),
                                 key=lambda x: x[1]["avg_pnl_pct"], reverse=True):
        emoji = "✅" if stats["avg_pnl_pct"] > 0 else "❌"
        lines.append(f"- {emoji} **{sector}**: {stats['count']} trade, %{stats['win_rate_pct']} WR, {stats['avg_pnl_pct']:+.1f}%")
    lines.append("")

    # Excursion
    exc = analysis.get("excursion", {})
    lines.append(f"## Giriş/Çıkış Kalitesi")
    lines.append("")
    lines.append(f"- Ortalama MFE (en iyi an): +{exc.get('avg_mfe_pct', 0)}%")
    lines.append(f"- Ortalama MAE (en kötü an): {exc.get('avg_mae_pct', 0)}%")
    lines.append(f"- Capture Ratio: %{exc.get('avg_capture_ratio', 0)} (kazancın ne kadarını yakalıyorsun)")
    if exc.get("insight"):
        lines.append(f"- 💡 {exc['insight']}")
    lines.append("")

    # Öneriler
    if recs:
        lines.append(f"## 🎯 Parametre Önerileri")
        lines.append("")
        for rec in recs:
            conf_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}.get(rec.get("confidence"), "⚪")
            lines.append(f"- {conf_emoji} **[{rec.get('confidence', 'LOW')}]** {rec.get('reason', '')}")
            if "suggested" in rec:
                lines.append(f"  - Öneri: `{rec.get('param')}` = {rec['suggested']} (şu an: {rec.get('current')})")
        lines.append("")

    lines.append("---")
    lines.append("*Bu rapor otomatik oluşturulmuştur.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="HIGH confidence önerileri otomatik uygula")
    parser.add_argument("--report", action="store_true", help="Rapor oluştur")
    args = parser.parse_args()

    # Load data
    results = load_json("backtest_results.json")
    if not results:
        print("📭 No backtest results yet. Run signal_tracker.py first.")
        return

    # Analyze
    print(f"🔬 Analyzing {len(results)} closed trades...")
    analysis = analyze_results(results)
    recs = generate_recommendations(analysis)

    # Save analysis
    save_json("lessons_learned.json", {
        "analysis": analysis,
        "recommendations": recs,
        "last_updated": datetime.now().isoformat()
    })
    print(f"💾 Analysis saved to lessons_learned.json")

    # Print summary
    o = analysis.get("overall", {})
    print(f"\n{'═' * 60}")
    print(f"📊 OTOPSİ SONUÇLARI")
    print(f"{'═' * 60}")
    print(f"  Win Rate: %{o.get('win_rate_pct', 0)}")
    print(f"  Expectancy: {o.get('expectancy', 0):+.2f}%")
    print(f"  Profit Factor: {o.get('profit_factor', 0)}")
    print(f"  Avg Capture: %{analysis.get('excursion', {}).get('avg_capture_ratio', 0)}")

    if recs:
        print(f"\n🎯 ÖNERİLER ({len(recs)}):")
        for rec in recs:
            print(f"  [{rec.get('confidence')}] {rec.get('reason', '')[:80]}")

    # Apply if requested
    if args.apply:
        high_recs = [r for r in recs if r.get("confidence") == "HIGH"]
        if high_recs:
            params = load_json("strategy_params.json") or {}
            params = apply_recommendations(recs, params)
            save_json("strategy_params.json", params)
            print(f"\n✅ {len(high_recs)} HIGH confidence öneri uygulandı (v{params.get('version', '?')})")

            # Log changes
            changelog = load_json("param_changelog.json") or []
            changelog.append({
                "date": datetime.now().isoformat(),
                "version": params.get("version"),
                "changes": params.get("update_history", [{}])[-1].get("changes", []),
                "trigger": "autopsy"
            })
            save_json("param_changelog.json", changelog)

    # Generate report
    if args.report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report = generate_report(analysis, recs)
        date_str = datetime.now().strftime("%Y-%m-%d")
        report_path = REPORTS_DIR / f"swing_autopsy_{date_str}.md"
        with open(report_path, "w") as f:
            f.write(report)
        print(f"📄 Report: {report_path}")


if __name__ == "__main__":
    main()
