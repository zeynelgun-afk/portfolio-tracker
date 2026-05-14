#!/usr/bin/env python3
"""
Finzora AI — Signal Performance Tracker (Aşama 9)
==================================================

logs/events.jsonl'dan tüm signal_sent kayıtlarını okur, her sinyalin
7g/14g/30g sonraki performansını FMP'den çekip data/signal_performance.json'a
kaydeder. 30 gün veri biriktiğinde Aşama 10 (öğrenme) için temel olur.

YAŞAM DÖNGÜSÜ:
  Sinyal gönderildi    → t=0
  +7g checkpoint       → 7g sonra fiyat + max_high + min_low
  +14g checkpoint      → 14g sonra
  +30g checkpoint      → 30g sonra (final değerlendirme)
  Hit target           → status="hit_target", checkpoint durdurulur
  Hit stop             → status="hit_stop", checkpoint durdurulur
  30g timeout          → status="timeout_30d", final hesap

KOŞUM:
  Günde 1 kez (23:30 TR, gün sonu). Idempotent — aynı checkpoint
  iki kez yazılmaz.

SAĞLIK KONTROLÜ (Pazar bonus):
  - Son 7g sinyal sayısı (0 ise uyarı: AI gate çok mu sıkı?)
  - Hit oranı (target hit / total) trend
  - Skor kalibrasyon (yüksek skorlar gerçekten kazandı mı?)

ÇIKTI:
  - data/signal_performance.json (kalıcı veri)
  - Pazar günleri: DM özet rapor
  - /sinyaller komutu için kaynak

14 May 2026 — Aşama 9 (sinyal performans takip).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.fmp import fmp_get

EVENTS_LOG = REPO_ROOT / "logs" / "events.jsonl"
PERFORMANCE_FILE = REPO_ROOT / "data" / "signal_performance.json"

CHECKPOINTS = [7, 14, 30]  # gün
MIN_SIGNALS_WARNING = 1  # son 7 günde 1'den az sinyal varsa uyarı


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [tracker] {msg}")


# ────────────────────────── I/O ──────────────────────────


def load_performance() -> dict:
    """signal_performance.json yükle."""
    if not PERFORMANCE_FILE.exists():
        return {
            "_son_guncelleme": "",
            "_aciklama": "Aşama 9 — Sinyal performans takibi (7g/14g/30g checkpoint)",
            "_schema_version": "1.0",
            "signals": {},  # signal_id → entry
            "stats": {
                "total_signals": 0,
                "tracking": 0,
                "completed": 0,
                "hit_target": 0,
                "hit_stop": 0,
                "timeout": 0,
            },
        }
    return json.loads(PERFORMANCE_FILE.read_text(encoding="utf-8"))


def save_performance(data: dict) -> None:
    data["_son_guncelleme"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    PERFORMANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_signal_sent_events() -> list[dict]:
    """events.jsonl'dan tüm signal_sent kayıtlarını oku."""
    if not EVENTS_LOG.exists():
        return []
    results = []
    try:
        for line in EVENTS_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
                if e.get("type") == "signal_sent":
                    results.append(e)
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return results


# ────────────────────────── Checkpoint Logic ──────────────────────────


def build_signal_id(event: dict) -> str:
    """Bir signal_sent event'ten benzersiz ID oluştur."""
    sym = event.get("symbol", "?")
    ts = event.get("ts", "?")[:16].replace(":", "-").replace("T", "_")
    return f"{sym}_{ts}"


def fetch_price_range(symbol: str, start_iso: str, end_iso: str) -> Optional[dict]:
    """
    İki tarih arası historical-price-eod/light → max_high, min_low, close.
    start_iso/end_iso: YYYY-MM-DD format.
    """
    try:
        bars = fmp_get("historical-price-eod/light", {
            "symbol": symbol,
            "from": start_iso,
            "to": end_iso,
        })
        if not bars or not isinstance(bars, list):
            return None
        prices = [b.get("price") or b.get("close") for b in bars]
        prices = [p for p in prices if p]
        highs = [b.get("price") or b.get("close") for b in bars]
        highs = [h for h in highs if h]
        if not prices:
            return None
        return {
            "close": prices[0],  # most recent (FMP'de en yeni başta)
            "max_high": max(prices),
            "min_low": min(prices),
            "bars": len(prices),
        }
    except Exception as e:
        log(f"  {symbol} fiyat çekme hatası: {e}")
        return None


def process_checkpoint(signal: dict, checkpoint_days: int,
                        signal_sent_dt: datetime) -> Optional[dict]:
    """
    Bir sinyal için bir checkpoint günü değerlendirmesi yap.
    Returns: {date, price, pct, max_high, min_low, hit_target, hit_stop}
    None: checkpoint günü henüz gelmedi.
    """
    target_dt = signal_sent_dt + timedelta(days=checkpoint_days)
    now = datetime.now(timezone.utc)
    if target_dt > now:
        return None  # henüz erken

    sym = signal["symbol"]
    entry = signal["entry"]
    stop = signal.get("stop_loss")
    target = signal.get("target")

    # Sinyal başlangıcından checkpoint'e kadar fiyat aralığı
    start_iso = signal_sent_dt.strftime("%Y-%m-%d")
    end_iso = target_dt.strftime("%Y-%m-%d")
    price_data = fetch_price_range(sym, start_iso, end_iso)
    if not price_data:
        return None

    close = price_data["close"]
    max_high = price_data["max_high"]
    min_low = price_data["min_low"]

    # Hit kontrolleri
    hit_target = False
    hit_stop = False
    if target and max_high >= float(target):
        hit_target = True
    if stop and min_low <= float(stop):
        hit_stop = True

    pct = ((close - entry) / entry) * 100 if entry else 0

    return {
        "date": target_dt.strftime("%Y-%m-%d"),
        "close": round(close, 2),
        "pct": round(pct, 2),
        "max_high": round(max_high, 2),
        "min_low": round(min_low, 2),
        "hit_target": hit_target,
        "hit_stop": hit_stop,
        "bars_count": price_data["bars"],
    }


def update_signal_tracking(signal_id: str, event: dict,
                            existing: dict) -> dict:
    """
    Tek bir sinyalin track verisini güncelle (mevcut checkpoint'lere
    eklemeden, sadece eksik olanları işle).
    """
    # Yeni signal ise
    if signal_id not in existing:
        existing[signal_id] = {
            "signal_id": signal_id,
            "symbol": event.get("symbol"),
            "sent_at": event.get("ts"),
            "entry": event.get("current_price") or event.get("entry"),
            "stop_loss": event.get("stop_loss"),
            "target": event.get("target"),
            "score": event.get("score"),
            "entry_zone": event.get("entry_zone"),
            "in_zone": event.get("in_zone"),
            "checkpoints": {},
            "status": "tracking",
        }

    sig = existing[signal_id]
    if sig["status"] != "tracking":
        return sig  # Zaten kapanmış, dokunma

    try:
        sent_dt = datetime.fromisoformat(sig["sent_at"].replace("Z", "+00:00"))
    except Exception:
        return sig

    # Her checkpoint için işle
    for cp_days in CHECKPOINTS:
        cp_key = f"{cp_days}d"
        if cp_key in sig["checkpoints"]:
            continue  # zaten işlenmiş

        cp_result = process_checkpoint(sig, cp_days, sent_dt)
        if cp_result is None:
            continue  # henüz erken

        sig["checkpoints"][cp_key] = cp_result
        log(f"  {sig['symbol']} {cp_key}: %{cp_result['pct']:+.2f}, "
            f"target={cp_result['hit_target']}, stop={cp_result['hit_stop']}")

        # Early termination: hit_target veya hit_stop
        if cp_result["hit_target"]:
            sig["status"] = "hit_target"
            sig["closed_at"] = cp_result["date"]
            break
        if cp_result["hit_stop"]:
            sig["status"] = "hit_stop"
            sig["closed_at"] = cp_result["date"]
            break

    # 30d checkpoint geldiyse ve hala tracking ise → timeout
    if "30d" in sig["checkpoints"] and sig["status"] == "tracking":
        sig["status"] = "timeout_30d"
        sig["closed_at"] = sig["checkpoints"]["30d"]["date"]

    return sig


# ────────────────────────── Stats ──────────────────────────


def compute_stats(signals: dict) -> dict:
    """Tüm sinyallerden istatistik üret."""
    total = len(signals)
    tracking = sum(1 for s in signals.values() if s["status"] == "tracking")
    hit_target = sum(1 for s in signals.values() if s["status"] == "hit_target")
    hit_stop = sum(1 for s in signals.values() if s["status"] == "hit_stop")
    timeout = sum(1 for s in signals.values() if s["status"] == "timeout_30d")
    completed = hit_target + hit_stop + timeout

    # 30d return ortalaması (kapanan + tracking olanların son checkpoint'i)
    returns = []
    score_winners = []
    score_losers = []
    for s in signals.values():
        last_cp = None
        for cp in ["30d", "14d", "7d"]:
            if cp in s["checkpoints"]:
                last_cp = s["checkpoints"][cp]
                break
        if last_cp:
            returns.append(last_cp["pct"])
            if last_cp["pct"] > 0:
                score_winners.append(s.get("score", 0))
            else:
                score_losers.append(s.get("score", 0))

    avg_return = sum(returns) / len(returns) if returns else None
    avg_score_winners = sum(score_winners) / len(score_winners) if score_winners else None
    avg_score_losers = sum(score_losers) / len(score_losers) if score_losers else None

    hit_rate = hit_target / completed if completed > 0 else None

    return {
        "total_signals": total,
        "tracking": tracking,
        "completed": completed,
        "hit_target": hit_target,
        "hit_stop": hit_stop,
        "timeout": timeout,
        "hit_rate": round(hit_rate, 3) if hit_rate is not None else None,
        "avg_return_pct": round(avg_return, 2) if avg_return is not None else None,
        "avg_score_winners": round(avg_score_winners, 1) if avg_score_winners is not None else None,
        "avg_score_losers": round(avg_score_losers, 1) if avg_score_losers is not None else None,
    }


# ────────────────────────── Health Check ──────────────────────────


def health_check(signals: dict, events: list) -> dict:
    """Sistem sağlığını değerlendir."""
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    signals_7d = 0
    signals_30d = 0
    for e in events:
        try:
            ts = datetime.fromisoformat(e.get("ts", "").replace("Z", "+00:00"))
            if ts >= cutoff_7d:
                signals_7d += 1
            if ts >= cutoff_30d:
                signals_30d += 1
        except Exception:
            continue

    warnings = []
    if signals_7d < MIN_SIGNALS_WARNING and signals_30d > 0:
        warnings.append(
            f"Son 7g sinyal sayısı düşük ({signals_7d}). AI gate çok mu sıkı?"
        )
    if signals_30d == 0:
        warnings.append("Son 30g hiç sinyal gönderilmedi. Sistem henüz yeni veya bir sorun var.")

    return {
        "signals_last_7d": signals_7d,
        "signals_last_30d": signals_30d,
        "warnings": warnings,
    }


# ────────────────────────── Rapor ──────────────────────────


def build_summary_report(data: dict, health: dict, sunday: bool = False) -> str:
    """DM rapor mesajı."""
    s = data["stats"]
    lines = [
        f"📊 <b>Sinyal Performans Takibi {'(Haftalık)' if sunday else ''}</b>",
        f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>",
        "",
    ]

    if s["total_signals"] == 0:
        lines.append("<i>Henüz takip edilen sinyal yok. Aşama 6 sinyal yayını koşumlarından sonra veri birikmeye başlayacak.</i>")
        lines.append("")
        lines.append("<i>finzora ai — Aşama 9 sinyal tracker</i>")
        return "\n".join(lines)

    # Genel istatistik
    lines.append(f"<b>Toplam:</b> {s['total_signals']} sinyal")
    lines.append(f"  • Takipte:   {s['tracking']}")
    lines.append(f"  • Hit target: {s['hit_target']} 🟢")
    lines.append(f"  • Hit stop:  {s['hit_stop']} 🔴")
    lines.append(f"  • Timeout 30g: {s['timeout']} ⚪")

    if s["hit_rate"] is not None:
        hit_pct = s["hit_rate"] * 100
        lines.append(f"  • Hit oranı: %{hit_pct:.1f}")
    if s["avg_return_pct"] is not None:
        lines.append(f"  • Ort getiri: %{s['avg_return_pct']:+.2f}")

    # Skor kalibrasyon
    if s.get("avg_score_winners") and s.get("avg_score_losers"):
        diff = s["avg_score_winners"] - s["avg_score_losers"]
        lines.append("")
        lines.append("<b>Skor kalibrasyonu:</b>")
        lines.append(f"  Kazananlar ort skor: {s['avg_score_winners']}")
        lines.append(f"  Kaybedenler ort skor: {s['avg_score_losers']}")
        if diff > 3:
            lines.append(f"  ✓ Skor öngörü gücü iyi (+{diff:.1f} fark)")
        elif diff > 0:
            lines.append(f"  ⚠️ Skor öngörü gücü zayıf ({diff:+.1f} fark)")
        else:
            lines.append(f"  ⚠️ Skor TERS çalışıyor olabilir ({diff:+.1f} fark)")

    # Health
    lines.append("")
    lines.append(f"<b>Sağlık:</b>")
    lines.append(f"  Son 7g sinyal: {health['signals_last_7d']}")
    lines.append(f"  Son 30g sinyal: {health['signals_last_30d']}")
    if health["warnings"]:
        for w in health["warnings"]:
            lines.append(f"  ⚠️ {w}")

    lines.append("")
    lines.append("<i>finzora ai — Aşama 9 sinyal tracker</i>")
    return "\n".join(lines)


# ────────────────────────── Main ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dm", action="store_true",
                        help="DM rapor gönder (sadece Pazar gönderim önerilir)")
    parser.add_argument("--sunday", action="store_true",
                        help="Haftalık özet modu — sağlık + analiz dahil")
    args = parser.parse_args()

    log("Sinyal tracker başlat")

    # 1. events.jsonl'dan tüm signal_sent'leri al
    events = read_signal_sent_events()
    log(f"Toplam signal_sent kaydı: {len(events)}")

    # 2. Mevcut performance verisini yükle
    data = load_performance()

    # 3. Her event için track güncelle (idempotent)
    for ev in events:
        sid = build_signal_id(ev)
        update_signal_tracking(sid, ev, data["signals"])

    # 4. Stats güncelle
    data["stats"] = compute_stats(data["signals"])

    # 5. Health check
    health = health_check(data["signals"], events)

    # 6. Kaydet
    save_performance(data)
    log(f"  {len(data['signals'])} sinyal track ediliyor, "
        f"{data['stats']['completed']} tamamlandı, "
        f"hit_rate={data['stats']['hit_rate']}, "
        f"avg_return=%{data['stats']['avg_return_pct']}")

    # 7. Rapor
    report = build_summary_report(data, health, sunday=args.sunday)
    print()
    print(report.replace("<b>", "**").replace("</b>", "**")
              .replace("<i>", "_").replace("</i>", "_"))

    if args.dm:
        try:
            from agent.telegram import send_to_dm
            send_to_dm(report)
            log("DM gönderildi")
        except Exception as e:
            log(f"DM gönderim hatası: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
