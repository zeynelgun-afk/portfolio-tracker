#!/usr/bin/env python3
"""Calibrator Outcome Doldurma — Phase 10 veri altyapısı.

Faz 2 — C-1 (17 May 2026).

Bu script:
    1. data/polymarket_calibrator_performance.json'dan event listesini yükler
    2. Her event için, ts'inden bu yana N gün geçtiyse ve outcome_Nd None ise:
       a. FMP'den candidate_symbol için event_date civarında historical fiyat çek
          (event_date-3d, event_date+33d aralığı — tek call)
       b. Event tarihindeki kapanış (T0) ve T+7/+14/+30 günlerindeki kapanışları
          en yakın trading günü mantığı ile seç
       c. outcome_Nd = (price_at_T+N - price_at_T0) / price_at_T0
    3. Tracker'ı kaydeder

outcome anlamı:
    - pm_confirm bayrağı (Polymarket DESTEKLEDİ): hisse yükselmeli → outcome > 0 = HIT
    - pm_conflict bayrağı (Polymarket ÇELİŞTİ): hisse düşmeli → outcome < 0 = HIT
    Phase 10'da hit rate analizi bu field'ları kullanır.

Cron önerisi: günlük UTC 06:00 (TR 09:00) — session öncesi.
Workflow: .github/workflows/fill_calibrator_outcomes.yml

Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm C-1)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_TRACKER_PATH = _REPO_ROOT / "data" / "polymarket_calibrator_performance.json"

# Outcome horizons (gün)
_HORIZONS = [
    ("outcome_7d", 7),
    ("outcome_14d", 14),
    ("outcome_30d", 30),
]


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [fill-outcomes] {msg}", flush=True)


def _load_tracker() -> dict:
    """Tracker dosyasını yükle."""
    if not _TRACKER_PATH.exists():
        return {}
    try:
        with _TRACKER_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Tracker yükleme hatası: {e}")
        return {}


def _save_tracker(tracker: dict) -> None:
    _TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TRACKER_PATH.open("w", encoding="utf-8") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)


def _parse_ts(ts_str: str) -> Optional[datetime]:
    """ISO format datetime parse — UTC."""
    if not isinstance(ts_str, str):
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def fetch_price_history(symbol: str, from_date: datetime,
                         to_date: datetime) -> list[dict]:
    """FMP'den symbol için from_date - to_date aralığında historical fiyat.

    Returns:
        list[{"date": "YYYY-MM-DD", "adjClose": float}] — tarih ascending.
        Hata veya boş veri → [].
    """
    try:
        from agent.fmp_client import fmp_get
    except ImportError:
        try:
            from agent.fmp import fmp_get
        except ImportError as e:
            log(f"FMP client import hatası: {e}")
            return []

    try:
        data = fmp_get("historical-price-eod/full", {
            "symbol": symbol,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        })
    except Exception as e:
        log(f"  {symbol}: FMP fetch hatası: {e}")
        return []

    if not data:
        return []

    # FMP historical-price-eod/full şu formatlardan biriyle döner:
    # - {"historical": [{"date": "...", "adjClose": ...}, ...]}
    # - [{"date": "...", "adjClose": ...}, ...]
    if isinstance(data, dict):
        rows = data.get("historical", [])
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    if not isinstance(rows, list):
        return []

    # Tarih ascending sırala (FMP genelde descending döner)
    rows = sorted(
        [r for r in rows if isinstance(r, dict) and r.get("date")],
        key=lambda r: r["date"],
    )
    return rows


def find_nearest_trading_day(rows: list[dict],
                              target_date: datetime) -> Optional[dict]:
    """Hedef tarihe en yakın (sonrasındaki) trading day row'unu döndür.

    Args:
        rows: ascending sıralı {"date": "YYYY-MM-DD", "adjClose": ...} listesi
        target_date: aranan tarih

    Returns:
        En yakın row veya None.

    Mantık: target_date'in O GÜN OLAN veya İLK SONRAKİ trading günü seçilir.
    Eğer target_date hafta sonu/tatil ise sonraki trading günü.
    Eğer rows listesinin sonunda hâlâ target_date'e ulaşılmamışsa None.
    """
    target_str = target_date.strftime("%Y-%m-%d")
    for r in rows:
        if r["date"] >= target_str:
            return r
    return None


def compute_outcome_for_event(event: dict, horizon_days: int,
                                rows: list[dict]) -> Optional[float]:
    """Event için T0 ve T+N fiyatlarını bulup outcome hesapla.

    Returns:
        outcome (float, 0.05 = +%5) veya None (yetersiz veri).
    """
    ts = _parse_ts(event.get("ts", ""))
    if ts is None:
        return None

    t0_row = find_nearest_trading_day(rows, ts)
    tn_row = find_nearest_trading_day(
        rows, ts + timedelta(days=horizon_days)
    )

    if t0_row is None or tn_row is None:
        return None

    try:
        p0 = float(t0_row.get("adjClose", 0))
        pn = float(tn_row.get("adjClose", 0))
    except (TypeError, ValueError):
        return None

    if p0 <= 0:
        return None

    return (pn - p0) / p0


def fill_event_outcomes(event: dict, now: datetime,
                         dry_run: bool = False) -> dict:
    """Tek event için outcome doldur. Mutates `event` in-place.

    Returns:
        {"filled": ["outcome_7d", ...], "skipped": ["outcome_30d (henüz olgun değil)", ...]}
    """
    result = {"filled": [], "skipped": []}

    ts = _parse_ts(event.get("ts", ""))
    if ts is None:
        result["skipped"].append("invalid ts")
        return result

    symbol = event.get("candidate_symbol")
    if not symbol or not isinstance(symbol, str):
        result["skipped"].append("invalid symbol")
        return result

    # Hangi horizon'lar olgun?
    mature_horizons = []
    for field, days in _HORIZONS:
        # Doluysa atla
        if event.get(field) is not None:
            continue
        # Olgun mu?
        if (now - ts).total_seconds() >= days * 86400:
            mature_horizons.append((field, days))
        else:
            wait_days = days - (now - ts).total_seconds() / 86400
            result["skipped"].append(
                f"{field} (henüz olgun değil, ~{wait_days:.1f}g sonra)"
            )

    if not mature_horizons:
        return result

    # Tek FMP call ile tüm horizon'lar için geniş aralık çek
    from_date = ts - timedelta(days=3)
    to_date = ts + timedelta(days=33)
    rows = fetch_price_history(symbol, from_date, to_date)

    if not rows:
        for field, _ in mature_horizons:
            result["skipped"].append(f"{field} (FMP veri yok)")
        return result

    for field, days in mature_horizons:
        outcome = compute_outcome_for_event(event, days, rows)
        if outcome is None:
            result["skipped"].append(f"{field} (T0 veya T+N fiyat eksik)")
            continue
        if dry_run:
            log(f"  {symbol} {field}: {outcome*100:+.2f}% (dry-run, yazılmadı)")
        else:
            event[field] = round(outcome, 6)
        result["filled"].append(field)

    return result


def run_fill(dry_run: bool = False,
              now: Optional[datetime] = None) -> dict:
    """Ana doldurma pipeline'ı.

    Returns:
        {"total_events": N, "events_processed": N, "outcomes_filled": N,
         "errors": [...]}
    """
    if now is None:
        now = datetime.now(timezone.utc)

    tracker = _load_tracker()
    if not tracker:
        log("Tracker dosyası yok veya bozuk")
        return {"total_events": 0, "events_processed": 0,
                "outcomes_filled": 0, "errors": []}

    events = tracker.get("events", [])
    if not isinstance(events, list):
        log("Tracker.events liste değil")
        return {"total_events": 0, "events_processed": 0,
                "outcomes_filled": 0, "errors": []}

    if not events:
        log("Hiç event yok — outcome doldurma için bir şey gerek değil")
        return {"total_events": 0, "events_processed": 0,
                "outcomes_filled": 0, "errors": []}

    log(f"Tarama: {len(events)} event")

    total_filled = 0
    events_processed = 0
    errors = []

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"Event #{idx}: dict değil")
            continue

        symbol = event.get("candidate_symbol", "?")

        try:
            outcome_result = fill_event_outcomes(event, now, dry_run=dry_run)
            if outcome_result["filled"]:
                events_processed += 1
                total_filled += len(outcome_result["filled"])
                log(f"  {symbol}: dolduruldu {outcome_result['filled']}")
        except Exception as e:
            errors.append(f"{symbol}: {e}")
            log(f"  {symbol}: HATA: {e}")

    if not dry_run and total_filled > 0:
        _save_tracker(tracker)
        log(f"Tracker güncellendi: {total_filled} outcome yazıldı")
    elif dry_run:
        log(f"DRY-RUN: {total_filled} outcome hesaplandı ama yazılmadı")
    else:
        log("Yeni outcome yok, tracker değişmedi")

    return {
        "total_events": len(events),
        "events_processed": events_processed,
        "outcomes_filled": total_filled,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Outcome hesapla ama tracker'a yazma",
    )
    args = parser.parse_args(argv)

    log("Calibrator outcome doldurma başlıyor")
    try:
        result = run_fill(dry_run=args.dry_run)
    except Exception as e:
        log(f"HATA: pipeline çöktü: {e}")
        return 1

    log(
        f"Bitti — total={result['total_events']}, "
        f"processed={result['events_processed']}, "
        f"filled={result['outcomes_filled']}, "
        f"errors={len(result['errors'])}"
    )

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
