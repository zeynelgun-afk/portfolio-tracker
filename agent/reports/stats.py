#!/usr/bin/env python3
"""
Finzora Stats — Observability Raporu
=====================================
Kullanım:
  python scripts/finzora_stats.py                  # son 7 gün özet
  python scripts/finzora_stats.py --days 30        # son 30 gün
  python scripts/finzora_stats.py --today          # bugün
  python scripts/finzora_stats.py --telegram       # Telegram'a gönder
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# agent/ modüllerine ulaş
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "agent"))

try:
    from observability import (
        query_claude_cost,
        query_fmp_stats,
        query_decision_hitrate,
        DB_PATH,
    )
except ImportError as e:
    print(f"ERROR: observability modülü yüklenemedi: {e}")
    sys.exit(1)


# ─────────────────────── Polymarket Kalibratör İstatistikleri ───────────────────
# Faz 2 Adım 13 (17 May 2026). Tracker JSON'dan event analizi.

_CALIBRATOR_LOG_PATH = _REPO_ROOT / "data" / "polymarket_calibrator_performance.json"


def _load_calibrator_tracker() -> dict:
    """Tracker dosyasını yükle. Dosya yoksa boş dict, bozuksa {}."""
    if not _CALIBRATOR_LOG_PATH.exists():
        return {}
    try:
        with _CALIBRATOR_LOG_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def query_calibrator_stats(days: int) -> dict:
    """Son `days` günkü kalibratör event'lerinin istatistiklerini çıkar.

    Returns:
        {
          "total_events": N,
          "by_flag": {"pm_confirm": N, "pm_confirm_weak": N, ...},
          "by_multiplier": {"1.20x": N, "1.10x": N, "0.90x": N, "0.75x": N},
          "by_source": {"thematic": N, "fair_value": N},
          "top_themes": [(theme, count), ...],
          "top_symbols": [(symbol, count), ...],
          "days_collected": float,  # tracker _started_at'ten itibaren
          "phase10_progress_pct": float,  # 0-100, 30 gün hedef
          "outcome_status": "pending_phase10",  # outcome_*_d hâlâ None
          "error": opsiyonel str,
        }
    """
    tracker = _load_calibrator_tracker()
    if not tracker:
        return {"error": "Tracker dosyası yok veya bozuk", "total_events": 0}

    events = tracker.get("events", [])
    if not isinstance(events, list):
        return {"error": "Events alanı geçersiz", "total_events": 0}

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Filtreleme — son `days` günü
    recent = []
    for evt in events:
        if not isinstance(evt, dict):
            continue
        ts_str = evt.get("ts", "")
        if not isinstance(ts_str, str):
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts >= cutoff:
                recent.append(evt)
        except (ValueError, TypeError):
            continue

    if not recent:
        return {
            "total_events": 0,
            "by_flag": {},
            "by_multiplier": {},
            "by_source": {},
            "top_themes": [],
            "top_symbols": [],
            "days_collected": _calc_days_collected(tracker, now),
            "phase10_progress_pct": _calc_phase10_progress(tracker, now),
            "outcome_status": "no_data",
        }

    # Flag dağılımı
    by_flag: dict[str, int] = {}
    for e in recent:
        flag = e.get("applied_flag", "unknown")
        if isinstance(flag, str):
            by_flag[flag] = by_flag.get(flag, 0) + 1

    # Multiplier dağılımı (1.20 / 1.10 / 0.90 / 0.75)
    by_multiplier: dict[str, int] = {}
    for e in recent:
        mult = e.get("applied_multiplier")
        if isinstance(mult, (int, float)):
            key = f"{mult:.2f}x"
            by_multiplier[key] = by_multiplier.get(key, 0) + 1

    # Source dağılımı (thematic/fair_value)
    by_source: dict[str, int] = {}
    for e in recent:
        src = e.get("candidate_source", "unknown")
        if isinstance(src, str):
            by_source[src] = by_source.get(src, 0) + 1

    # Top themes (top 5)
    theme_counts: dict[str, int] = {}
    for e in recent:
        theme = e.get("matched_theme")
        if isinstance(theme, str):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
    top_themes = sorted(theme_counts.items(), key=lambda x: -x[1])[:5]

    # Top symbols (top 5)
    sym_counts: dict[str, int] = {}
    for e in recent:
        sym = e.get("candidate_symbol")
        if isinstance(sym, str):
            sym_counts[sym] = sym_counts.get(sym, 0) + 1
    top_symbols = sorted(sym_counts.items(), key=lambda x: -x[1])[:5]

    # Outcome status — outcome_7d/14d/30d henüz Phase 10'da dolacak
    outcome_filled = sum(
        1 for e in recent
        if e.get("outcome_7d") is not None or e.get("outcome_14d") is not None
        or e.get("outcome_30d") is not None
    )

    return {
        "total_events": len(recent),
        "by_flag": by_flag,
        "by_multiplier": by_multiplier,
        "by_source": by_source,
        "top_themes": top_themes,
        "top_symbols": top_symbols,
        "days_collected": _calc_days_collected(tracker, now),
        "phase10_progress_pct": _calc_phase10_progress(tracker, now),
        "outcome_status": ("pending_phase10" if outcome_filled == 0
                           else "partial"),
    }


def _calc_days_collected(tracker: dict, now: datetime) -> float:
    """_started_at'ten itibaren kaç gün geçti."""
    started_str = tracker.get("_started_at")
    if not isinstance(started_str, str):
        return 0.0
    try:
        started = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
        return (now - started).total_seconds() / 86400
    except (ValueError, TypeError):
        return 0.0


def _calc_phase10_progress(tracker: dict, now: datetime) -> float:
    """0-100 progress (30 gün hedef)."""
    days = _calc_days_collected(tracker, now)
    return min(100.0, days / 30 * 100)


def format_calibrator_section(stats: dict) -> list[str]:
    """Markdown bölüm satırları."""
    lines = ["\n## Polymarket Kalibratör İstatistikleri\n"]

    if "error" in stats:
        lines.append(f"⚠️ {stats['error']}")
        lines.append(
            "_Kalibratör henüz çalışmadı veya tracker dosyası oluşmadı. "
            "CALIBRATOR_ENABLED=true ile aktif olduktan ve ilk eşleşme "
            "tespit edildikten sonra dolacak._"
        )
        return lines

    total = stats.get("total_events", 0)
    progress = stats.get("phase10_progress_pct", 0)
    days = stats.get("days_collected", 0)

    if total == 0:
        lines.append(f"- Toplam event: **0** (henüz yok)")
        lines.append(
            f"- Tracker: {days:.1f} gün ({progress:.0f}% — "
            f"Phase 10 için 30 gün gerek)"
        )
        return lines

    lines.append(f"- Toplam event: **{total}**")
    lines.append(
        f"- Tracker: {days:.1f} gün ({progress:.0f}% — "
        f"Phase 10 için 30 gün gerek)"
    )

    # Flag dağılımı
    by_flag = stats.get("by_flag", {})
    if by_flag:
        lines.append("\n### Bayrak Dağılımı\n")
        lines.append("| Bayrak | Sayı | % |")
        lines.append("|---|---:|---:|")
        for flag in sorted(by_flag.keys()):
            count = by_flag[flag]
            pct = count / total * 100
            lines.append(f"| `{flag}` | {count} | {pct:.1f}% |")

    # Multiplier dağılımı
    by_mult = stats.get("by_multiplier", {})
    if by_mult:
        lines.append("\n### Çarpan Dağılımı\n")
        lines.append("| Çarpan | Sayı |")
        lines.append("|---|---:|")
        # Yüksek çarpandan düşüğe
        for mult in sorted(by_mult.keys(), reverse=True):
            lines.append(f"| {mult} | {by_mult[mult]} |")

    # Source dağılımı
    by_src = stats.get("by_source", {})
    if by_src:
        lines.append("\n### Kaynak Dağılımı (scanner)\n")
        for src, count in sorted(by_src.items(), key=lambda x: -x[1]):
            lines.append(f"- `{src}`: {count}")

    # Top temalar
    top_themes = stats.get("top_themes", [])
    if top_themes:
        lines.append("\n### En Aktif Temalar (top 5)\n")
        for theme, count in top_themes:
            lines.append(f"- `{theme}`: {count} event")

    # Top semboller
    top_syms = stats.get("top_symbols", [])
    if top_syms:
        lines.append("\n### En Çok Eşleşen Hisseler (top 5)\n")
        for sym, count in top_syms:
            lines.append(f"- **{sym}**: {count} event")

    # Outcome durumu
    outcome = stats.get("outcome_status", "pending_phase10")
    lines.append("")
    if outcome == "pending_phase10":
        lines.append(
            "_Hit rate: Phase 10'da hesaplanacak. outcome_7d/14d/30d "
            "field'ları henüz boş — Phase 10 implementasyonunda price "
            "snapshot mantığı eklenince hit rate raporlanır._"
        )
    elif outcome == "partial":
        lines.append("_Hit rate: kısmi veri var, Phase 10 değerlendirmesi gerek._")

    return lines


def format_report(days: int) -> str:
    """Markdown rapor."""
    lines = []
    lines.append(f"# Finzora Observability Raporu — Son {days} Gün\n")

    if not DB_PATH.exists():
        lines.append("⚠️ Veritabanı henüz oluşmadı. İlk AI veya FMP çağrısından sonra dolacak.")
        return "\n".join(lines)

    # LLM maliyet
    lines.append("## LLM API Kullanımı\n")
    cost = query_claude_cost(days)
    if "error" in cost:
        lines.append(f"❌ {cost['error']}")
    else:
        lines.append(f"- Toplam çağrı: **{cost['calls']}**")
        lines.append(f"- Başarısız: {cost['failures']}")
        lines.append(f"- Input token: {cost['input_tokens']:,}")
        lines.append(f"- Output token: {cost['output_tokens']:,}")
        lines.append(f"- Tahmini maliyet: **${cost['cost_usd']:.2f}**")
        if days > 0 and cost['cost_usd'] > 0:
            monthly = cost['cost_usd'] * (30 / days)
            lines.append(f"- Aylık projeksiyon: ~${monthly:.2f}")

    # FMP stats
    lines.append("\n## FMP API Endpoint İstatistikleri\n")
    stats = query_fmp_stats(days)
    if stats and "error" in stats[0]:
        lines.append(f"❌ {stats[0]['error']}")
    elif not stats:
        lines.append("Henüz FMP çağrısı yok.")
    else:
        lines.append("| Endpoint | Çağrı | Ort. ms | Başarısız |")
        lines.append("|---|---:|---:|---:|")
        for s in stats[:15]:
            lines.append(
                f"| {s['endpoint']} | {s['calls']} | {s['avg_ms']:.0f} | {s['failures']} |"
            )
        total_calls = sum(s['calls'] for s in stats)
        total_fails = sum(s['failures'] for s in stats)
        lines.append(f"\n**Toplam çağrı: {total_calls}** | Başarısız: {total_fails}")

    # Decision hitrate
    lines.append("\n## Karar Tipi Dağılımı\n")
    hr = query_decision_hitrate(days)
    if "error" in hr:
        lines.append(f"❌ {hr['error']}")
    elif not hr.get("by_type"):
        lines.append("Henüz karar kaydı yok.")
    else:
        lines.append("| Tip | Toplam | Uygulanan | Oran |")
        lines.append("|---|---:|---:|---:|")
        for r in hr["by_type"]:
            lines.append(
                f"| {r['tip']} | {r['count']} | {r['executed']} | {r['rate_pct']}% |"
            )

    # Polymarket Kalibratör (Faz 2 Adım 13)
    cal_stats = query_calibrator_stats(days)
    lines.extend(format_calibrator_section(cal_stats))

    return "\n".join(lines)


def send_to_telegram(text: str) -> bool:
    import os
    import requests

    # Env fallback: hem eski (TELEGRAM_TOKEN/PRIVATE_CHAT) hem standart (BOT_TOKEN/PRIVATE_ID) destekli
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_PRIVATE_CHAT") or os.environ.get("TELEGRAM_PRIVATE_ID", "")
    if not token or not chat:
        print("UYARI: TELEGRAM token veya private chat ID tanımsız "
              "(TELEGRAM_BOT_TOKEN+TELEGRAM_PRIVATE_ID veya legacy TELEGRAM_TOKEN+TELEGRAM_PRIVATE_CHAT)")
        return False

    # Telegram max 4096 karakter
    text = text[:4090] + "..." if len(text) > 4096 else text

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Finzora observability raporu")
    ap.add_argument("--days", type=int, default=7, help="Kaç günlük rapor (default 7)")
    ap.add_argument("--today", action="store_true", help="Sadece bugün")
    ap.add_argument("--telegram", action="store_true", help="Telegram'a gönder")
    args = ap.parse_args()

    days = 1 if args.today else args.days
    report = format_report(days)

    print(report)

    if args.telegram:
        ok = send_to_telegram(report)
        print(f"\nTelegram: {'✓' if ok else '✗'}")


if __name__ == "__main__":
    main()
