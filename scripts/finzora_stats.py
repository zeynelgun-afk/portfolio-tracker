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
import argparse
from pathlib import Path

# agent/ modüllerine ulaş
_REPO_ROOT = Path(__file__).resolve().parent.parent
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
