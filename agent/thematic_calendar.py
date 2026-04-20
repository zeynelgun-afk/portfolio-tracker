#!/usr/bin/env python3
"""
Tematik Katalist Takvimi — Orkestratör Entegrasyonu
====================================================

Yıllık tematik teknoloji etkinliklerini takvimleyip:
  (a) Etkinlik öncesi 2 iş günü pre-event watchlist sinyali,
  (b) Etkinlik günü tematik rapor sinyali,
  (c) Etkinlik sonrası 5 iş günü post-event sweep sinyali
üretir.

14 Nisan 2026 NVIDIA Ising (World Quantum Day) kaçırılması sonrası eklendi.
Detaylı doküman: docs/THEMATIC_CATALYST_CALENDAR.md

Kullanım:
    from thematic_calendar import check_thematic_event, build_thematic_context
    status, event = check_thematic_event()   # status: None | "pre" | "event" | "post"
    thematic_md = build_thematic_context()   # orchestrator.collect_context için
"""

from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Tuple

import pytz

TR_TZ = pytz.timezone("Europe/Istanbul")


# ── Etkinlik tanımları ──────────────────────────────────────────────────────────
#
# date_type: "fixed" → MM-DD sabit (her yıl aynı tarih)
#            "approximate" → MM-DD yaklaşık (her yıl Ocak'ta resmi takvimle güncelle)
#
# theme: Genel tema etiketi
# primary: Birincil oyuncular (duyuru yapan şirket + doğrudan rakipleri)
# ecosystem: Tedarik zinciri / ekosistem hisseleri
# speculative: Saf-oyuncu ama normal screener'a girmeyen (EPS negatif vb.) hisseler
#              Bunlar yalnız thematic override ile izlenir, normal alım önerisi yapılmaz.

THEMATIC_EVENTS = {
    # ── Ocak ──
    "01-07": {
        "name": "CES",
        "date_type": "approximate",
        "theme": "Tüketici teknolojisi, otonom araç, AI PC, akıllı ev",
        "primary": ["NVDA", "AMD", "INTC", "QCOM", "SONY", "AAPL"],
        "ecosystem": ["MSFT", "META", "GOOGL", "AVGO", "MRVL", "ARM", "ROKU", "TTD"],
        "speculative": [],
    },

    # ── Mart ──
    "03-25": {
        "name": "NVIDIA GTC Spring (San Jose)",
        "date_type": "approximate",
        "theme": "AI altyapı, GPU, kuantum-GPU, otonom, robotik, biyolojik AI",
        "primary": ["NVDA"],
        "ecosystem": [
            # 6 katman AI tedarik zinciri
            "AMAT", "LRCX", "KLAC", "ASML",             # ekipman
            "ENTG", "MKSI", "AVY", "CBT",               # kimyasal/malzeme
            "CRDO", "LITE", "CIEN", "COHR", "ANET",     # optik
            "VRT", "ETN", "GEV", "POWI", "MPWR",        # güç
            "VST", "CEG", "TLN", "NEE",                 # enerji
            "ISRG", "TER",                              # robotik
            "RXRX", "TEM",                              # biyolojik AI
        ],
        "speculative": ["IONQ", "RGTI", "QBTS", "QUBT"],  # kuantum-GPU teması
    },

    # ── Nisan ──
    "04-14": {
        "name": "World Quantum Day",
        "date_type": "fixed",  # 4.14 = Planck sabiti, her yıl sabit
        "theme": "Kuantum bilgisayar, kuantum AI, hata düzeltme, kalibrasyon",
        "primary": ["NVDA", "IBM", "GOOGL", "MSFT", "AMZN"],
        "ecosystem": ["HON", "INTC", "JNPR"],
        "speculative": ["IONQ", "RGTI", "QBTS", "QUBT"],
        "historical_note": (
            "14 Nis 2026 NVIDIA Ising duyurusu: IONQ +%54.9, QBTS +%48.1, "
            "QUBT +%31.6, RGTI +%30.9 (13-17 Nisan). Kaçırıldı."
        ),
    },

    # ── Mayıs ──
    "05-19": {
        "name": "Microsoft Build",
        "date_type": "approximate",
        "theme": "Kurumsal AI, Copilot, Azure, yazılım geliştirici",
        "primary": ["MSFT"],
        "ecosystem": ["GOOGL", "CRM", "NOW", "ADBE", "ORCL", "SAP",
                      "NVDA", "AMD", "AVGO",
                      "SNOW", "DDOG", "MDB", "CFLT", "ESTC"],
        "speculative": [],
    },
    "05-20": {
        "name": "Google I/O",
        "date_type": "approximate",
        "theme": "Android, arama, Gemini, Cloud, Pixel/Tensor",
        "primary": ["GOOGL"],
        "ecosystem": ["AVGO", "NVDA", "AAPL", "QCOM", "ARM",
                      "META", "TTD", "APP"],
        "speculative": [],
    },

    # ── Haziran ──
    "06-03": {
        "name": "Computex (Taipei)",
        "date_type": "approximate",
        "theme": "PC, GPU, sunucu, yarı iletken, AI donanım",
        "primary": ["NVDA", "AMD", "INTC", "QCOM"],
        "ecosystem": ["TSM", "ASML", "HPQ", "DELL", "SMCI", "MU", "AVGO"],
        "speculative": [],
    },
    "06-09": {
        "name": "Apple WWDC",
        "date_type": "approximate",
        "theme": "iOS/macOS, Vision Pro, Apple Intelligence",
        "primary": ["AAPL"],
        "ecosystem": ["QCOM", "SWKS", "QRVO", "AVGO", "CRUS",
                      "TSM", "MU",
                      "GOOGL", "MSFT", "META", "SPOT", "NFLX"],
        "speculative": [],
    },
    "06-10": {
        "name": "Snowflake Summit & Databricks Data+AI Summit",
        "date_type": "approximate",
        "theme": "Veri gölü, analitik, AI veri altyapısı",
        "primary": ["SNOW", "DDOG"],
        "ecosystem": ["MDB", "CFLT", "ESTC", "NET"],
        "speculative": [],
    },

    # ── Eylül ──
    "09-16": {
        "name": "Intel Innovation",
        "date_type": "approximate",
        "theme": "CPU, Foundry, AI PC, Gaudi",
        "primary": ["INTC"],
        "ecosystem": ["AMD", "NVDA", "TSM", "ARM", "DELL", "HPQ", "SMCI"],
        "speculative": [],
    },
    "09-29": {
        "name": "Salesforce Dreamforce",
        "date_type": "approximate",
        "theme": "Kurumsal SaaS, CRM, Agentforce",
        "primary": ["CRM"],
        "ecosystem": ["NOW", "WDAY", "HUBS", "TEAM", "SNOW", "DDOG", "MDB"],
        "speculative": [],
    },

    # ── Ekim ──
    "10-27": {
        "name": "NVIDIA GTC Washington",
        "date_type": "approximate",
        "theme": "AI savunma, devlet, enerji, bilimsel hesaplama",
        "primary": ["NVDA"],
        "ecosystem": ["LMT", "RTX", "NOC", "GD", "PLTR", "KTOS", "AVAV",
                      "VST", "CEG", "TLN", "GEV", "RXRX", "TEM"],
        "speculative": ["RGTI"],  # kuantum-bilim hesaplama
    },
    "10-30": {
        "name": "OpenAI Dev Day",
        "date_type": "approximate",
        "theme": "LLM, geliştirici API, ajan altyapısı",
        "primary": ["MSFT", "NVDA"],
        "ecosystem": ["GOOGL", "META", "AMZN", "CRM", "NOW", "ADBE", "DDOG"],
        "speculative": [],
    },

    # ── Kasım / Aralık ──
    "12-01": {
        "name": "AWS re:Invent",
        "date_type": "approximate",
        "theme": "Bulut, Bedrock, Trainium/Inferentia, kurumsal AI",
        "primary": ["AMZN"],
        "ecosystem": ["MSFT", "GOOGL", "ORCL",
                      "NVDA", "AVGO", "MRVL",
                      "SNOW", "DDOG", "MDB", "CFLT"],
        "speculative": [],
    },
}


# ── Ana fonksiyonlar ────────────────────────────────────────────────────────────

def _today_key(today: Optional[date] = None) -> str:
    today = today or datetime.now(TR_TZ).date()
    return today.strftime("%m-%d")


def _date_to_key(d: date) -> str:
    return d.strftime("%m-%d")


def _days_between_keys(from_key: str, to_key: str, year: int) -> int:
    """Aynı yıl içinde iki MM-DD anahtarı arasındaki gün farkı (işaretli)."""
    try:
        d_from = datetime.strptime(f"{year}-{from_key}", "%Y-%m-%d").date()
        d_to   = datetime.strptime(f"{year}-{to_key}",   "%Y-%m-%d").date()
        return (d_to - d_from).days
    except ValueError:
        return 9999


def check_thematic_event(today: Optional[date] = None) -> Tuple[Optional[str], Optional[dict]]:
    """
    Bugünün tematik durumunu tespit eder.

    Döner:
        (status, event_info)
        status ∈ {None, "pre", "event", "post"}
        event_info: THEMATIC_EVENTS sözlüğünden ilgili etkinlik kaydı + "key", "days_delta"

    Kurallar:
        "pre"   → Etkinlik 1 veya 2 takvim günü sonra
        "event" → Etkinlik bugün
        "post"  → Etkinlik 1-5 takvim günü önce oldu
        None    → Hiçbir etkinliğe yakın değil
    """
    today = today or datetime.now(TR_TZ).date()
    year  = today.year
    today_key = _today_key(today)

    best_status = None
    best_event  = None
    best_abs_delta = 999

    for key, event in THEMATIC_EVENTS.items():
        # delta < 0 → etkinlik geçmişte, > 0 → gelecekte
        delta = _days_between_keys(today_key, key, year)

        if delta == 0:
            # Bugün etkinlik → her zaman kazanır
            event_out = dict(event)
            event_out["key"] = key
            event_out["days_delta"] = 0
            return ("event", event_out)

        status = None
        if 1 <= delta <= 2:
            status = "pre"
        elif -5 <= delta <= -1:
            status = "post"

        if status and abs(delta) < best_abs_delta:
            best_status = status
            best_event  = dict(event)
            best_event["key"] = key
            best_event["days_delta"] = delta
            best_abs_delta = abs(delta)

    return (best_status, best_event)


def get_pre_event_watchlist(event: dict, include_speculative: bool = True) -> list[str]:
    """Pre-event watchlist için izlenecek ticker listesi."""
    tickers: list[str] = []
    tickers.extend(event.get("primary", []))
    tickers.extend(event.get("ecosystem", []))
    if include_speculative:
        tickers.extend(event.get("speculative", []))
    # Tekrarları kaldır, sırayı koru
    seen = set()
    result = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def build_thematic_context(today: Optional[date] = None) -> str:
    """
    Orkestratör `collect_context` fonksiyonu için hazır markdown bağlamı döner.

    Hiçbir etkinliğe yakın değilse boş string döner (prompt'u kirletmez).
    """
    status, event = check_thematic_event(today=today)
    if not status or not event:
        return ""

    name  = event["name"]
    theme = event.get("theme", "")
    delta = event.get("days_delta", 0)

    header_map = {
        "pre":   f"### Tematik Durum: PRE-EVENT ({abs(delta)} iş günü sonra)",
        "event": f"### Tematik Durum: EVENT DAY (BUGÜN)",
        "post":  f"### Tematik Durum: POST-EVENT ({abs(delta)} iş günü önce)",
    }
    action_map = {
        "pre": (
            "Pre-event watchlist kontrolü yap. Tema hisseleri için son 10 gün volatilitesi, "
            "RSI<65 ve 50SMA üstü filtresini uygula. Giriş için henüz erken; takipte kal."
        ),
        "event": (
            "KOVALAMA YASAK. Sadece izle. Canlı keynote TR saati ile takip et. "
            "Duyurular sonrası tematik sweep hazırlığı yap. Giriş penceresi ertesi iş günü açılır."
        ),
        "post": (
            "Post-event penceresi aktif. Giriş kuralları (crisis rally dersi): "
            "1. gün yasak, 2. gün RSI<75 ise yarım pozisyon, 3-5. gün volume ve RSI kontrolü, "
            "5. gün sonrası geç giriş riski yüksek. Detay: docs/THEMATIC_CATALYST_CALENDAR.md"
        ),
    }

    lines = [
        header_map[status],
        f"**Etkinlik:** {name}",
        f"**Tema:** {theme}",
        "",
        f"**Aksiyon:** {action_map[status]}",
    ]

    primary    = event.get("primary", [])
    ecosystem  = event.get("ecosystem", [])
    speculative = event.get("speculative", [])

    if primary:
        lines.append(f"**Birincil oyuncular:** {', '.join(primary)}")
    if ecosystem:
        lines.append(f"**Ekosistem:** {', '.join(ecosystem)}")
    if speculative:
        lines.append(
            f"**Saf oyuncular (screener dışı, yalnız thematic override):** "
            f"{', '.join(speculative)}"
        )

    note = event.get("historical_note")
    if note:
        lines.append("")
        lines.append(f"**Geçmiş not:** {note}")

    return "\n".join(lines)


# ── CLI testi ──────────────────────────────────────────────────────────────────

def _cli():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="Test tarihi YYYY-MM-DD (varsayılan: bugün)")
    p.add_argument("--json", action="store_true", help="JSON formatında ham çıktı")
    args = p.parse_args()

    test_date = None
    if args.date:
        test_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    status, event = check_thematic_event(today=test_date)

    if args.json:
        out = {"status": status, "event": event}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if not status:
            print(f"[thematic_calendar] {test_date or 'bugün'} için aktif etkinlik yok.")
            return
        print(f"[thematic_calendar] Status: {status}")
        print(f"[thematic_calendar] Etkinlik: {event['name']} ({event['key']})")
        print(f"[thematic_calendar] days_delta: {event['days_delta']}")
        print()
        print(build_thematic_context(today=test_date))


if __name__ == "__main__":
    _cli()
