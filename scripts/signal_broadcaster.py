#!/usr/bin/env python3
"""
Finzora AI — Signal Broadcaster (Aşama 6)
==========================================

Seans-içi 30dk'da bir, en son orchestrator çıktısı üzerinden ALIM
SİNYALİ koşullarını sağlayan hisseler için GROUP'a bildirim yayınlar.

Tetik koşulları (HEPSİ olması gerekli):
  - score ≥ 85
  - Anlık fiyat entry zone üst sınırının +%5 toleransı içinde
  - Hisse mevcut portföyde yok
  - Bugün gönderilen sinyal sayısı < 2 (günlük üst sınır)
  - Aynı hisse için son 24h içinde sinyal gönderilmedi

Trail stop uyarısı (ek):
  - Portföydeki bir hisse sönüş aşamasındaki temaya bağlıysa:
  - DM'ye "stop sıkılaştırma önerisi" uyarısı

NOT: Bot ÖNERİDE bulunur, portfolio.json'a yazmaz. Zeynel pozisyon
büyüklüğü + portfolio.json yazımı + broker uygulamasını yapar.

Tetikleyici (Railway scheduler, seans-içi 30dk):
    python scripts/signal_broadcaster.py --telegram

14 May 2026 — Aşama 6 (sinyal yayını).
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
from agent.watchlist import load as load_watchlist
from agent.themes import get_dying_themes, get_portfolio_theme_map

EVENTS_LOG = REPO_ROOT / "logs" / "events.jsonl"
PORTFOLIO_PATH = REPO_ROOT / "data" / "portfolio.json"

SCORE_THRESHOLD = 85
ENTRY_TOLERANCE_PCT = 5.0  # zone üstü + %5
MAX_SIGNALS_PER_DAY = 2
DUPLICATE_LOOKBACK_HOURS = 24


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [signal] {msg}")


# ────────────────────────── Event Log Helpers ──────────────────────────


def read_events(event_type: Optional[str] = None,
                since: Optional[datetime] = None) -> list[dict]:
    """events.jsonl'dan filtreli oku."""
    if not EVENTS_LOG.exists():
        return []
    results = []
    try:
        for line in EVENTS_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type and e.get("type") != event_type:
                continue
            if since:
                ts = e.get("ts") or e.get("timestamp")
                if ts:
                    try:
                        ev_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if ev_time < since:
                            continue
                    except (ValueError, TypeError):
                        continue
            results.append(e)
    except OSError:
        return []
    return results


def write_event(event: dict) -> None:
    """events.jsonl'a tek satır JSON yaz."""
    event["ts"] = datetime.now(timezone.utc).isoformat()
    EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def signals_today() -> list[dict]:
    """Bugün gönderilen sinyalleri döndür."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return read_events(event_type="signal_sent", since=today_start)


def last_signal_for(symbol: str, hours: int = 24) -> Optional[dict]:
    """Bir hisse için son sinyali bul (hours içinde)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = read_events(event_type="signal_sent", since=cutoff)
    matches = [e for e in events if e.get("symbol", "").upper() == symbol.upper()]
    return matches[-1] if matches else None


# ────────────────────────── Portfolio ──────────────────────────


def portfolio_symbols() -> set[str]:
    """Portföydeki hisseleri döndür."""
    if not PORTFOLIO_PATH.exists():
        return set()
    try:
        d = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        return {p.get("symbol", "").upper() for p in d.get("positions", [])
                if p.get("symbol")}
    except (json.JSONDecodeError, OSError):
        return set()


# ────────────────────────── Entry Zone Parse ──────────────────────────


def parse_entry_zone(zone_str: str) -> Optional[tuple[float, float]]:
    """
    '$220-225' veya '$1550-1580' veya '$285-290' → (alt, üst)
    Para sembolü, virgül, boşluk temizlenir.
    """
    if not zone_str or not isinstance(zone_str, str):
        return None
    clean = zone_str.replace("$", "").replace(",", "").strip()
    # 'X-Y' formatı
    if "-" in clean:
        parts = clean.split("-")
        if len(parts) == 2:
            try:
                lo = float(parts[0].strip())
                hi = float(parts[1].strip())
                return (lo, hi)
            except ValueError:
                return None
    # Tek değer
    try:
        v = float(clean)
        return (v * 0.99, v * 1.01)
    except ValueError:
        return None


# ────────────────────────── Candidate Selection ──────────────────────────


def find_signal_candidates() -> list[dict]:
    """
    Watchlist'ten Aşama 5 orchestrator çıktılarına bakar,
    sinyal koşullarını sağlayan adayları döndürür.
    """
    wl = load_watchlist()
    tickers = wl.get("tickers", {})
    pf_syms = portfolio_symbols()

    today_signals = signals_today()
    sent_today = {e.get("symbol", "").upper() for e in today_signals}
    sent_count = len(today_signals)
    log(f"  Bugün gönderilen sinyal sayısı: {sent_count}/{MAX_SIGNALS_PER_DAY}")

    if sent_count >= MAX_SIGNALS_PER_DAY:
        log("  Günlük limit doldu, hiç sinyal aranmıyor.")
        return []

    # Score'a göre sırala (yüksek önce)
    sorted_tickers = sorted(
        tickers.items(),
        key=lambda kv: -(kv[1].get("score") or 0),
    )

    candidates = []
    for sym, entry in sorted_tickers:
        score = entry.get("score")
        if not score or score < SCORE_THRESHOLD:
            continue  # geri kalanlar da düşük (sıralı), aslında break de olur

        sym_upper = sym.upper()

        # Portföyde varsa atla
        if sym_upper in pf_syms:
            continue

        # Bugün aynı hisseye sinyal gönderildi mi?
        if sym_upper in sent_today:
            continue

        # Son 24h içinde sinyal var mı?
        if last_signal_for(sym_upper, hours=DUPLICATE_LOOKBACK_HOURS):
            continue

        # Orchestrator'ın önerisi var mı?
        sc = entry.get("score_components", {})
        entry_zone_str = sc.get("orchestrator_entry")
        if not entry_zone_str:
            continue

        zone = parse_entry_zone(entry_zone_str)
        if not zone:
            continue

        # Anlık fiyat çek
        try:
            quote = fmp_get("quote", {"symbol": sym_upper})
            if not quote or not isinstance(quote, list):
                continue
            current = quote[0].get("price")
            if not current:
                continue
        except Exception as e:
            log(f"  {sym_upper} quote hatası: {e}")
            continue

        # Entry zone + %5 tolerans kontrolü
        zone_lo, zone_hi = zone
        max_acceptable = zone_hi * (1 + ENTRY_TOLERANCE_PCT / 100)
        if current > max_acceptable:
            continue  # çok kaçırdık

        candidates.append({
            "symbol": sym_upper,
            "score": score,
            "current_price": current,
            "entry_zone": entry_zone_str,
            "zone_lo": zone_lo,
            "zone_hi": zone_hi,
            "max_acceptable": round(max_acceptable, 2),
            "in_zone": zone_lo <= current <= zone_hi,
            "stop_loss": sc.get("orchestrator_stop"),
            "target": sc.get("orchestrator_target"),
            "risk_reward": sc.get("orchestrator_rr"),
            "reason": sc.get("orchestrator_reason", ""),
            "rank": sc.get("orchestrator_rank"),
            "thematic_id": sc.get("thematic_id"),
        })

        # Günlük limit (toplam = bugün gönderilen + bu run'da bulunacak)
        if sent_count + len(candidates) >= MAX_SIGNALS_PER_DAY:
            break

    return candidates


# ────────────────────────── Signal Message ──────────────────────────


def format_signal_message(c: dict) -> str:
    """Group'a gidecek alım sinyali mesajı."""
    zone_status = "✅ zone içinde" if c["in_zone"] else \
                   f"⚠️ zone +%{((c['current_price']/c['zone_hi']-1)*100):.1f} (max ${c['max_acceptable']})"

    lines = [
        f"🎯 <b>ALIM SİNYALİ — {c['symbol']}</b>",
        f"<i>Orchestrator önerisi (rank #{c['rank']}, skor {c['score']:.0f})</i>",
        "",
        f"💰 Anlık fiyat: <b>${c['current_price']:.2f}</b>",
        f"📊 Entry zone: {c['entry_zone']} {zone_status}",
        f"🛑 Stop: ${c['stop_loss']} | 🎯 Target: ${c['target']} | R/R: {c['risk_reward']}",
        "",
        f"<i>Tez:</i> {c['reason']}",
    ]

    if c["thematic_id"]:
        lines.append(f"<i>Tema:</i> {c['thematic_id']}")

    lines.append("")
    lines.append("<i>finzora ai — Aşama 6 sinyal yayını</i>")
    return "\n".join(lines)


# ────────────────────────── Trail Stop (Sönüş) ──────────────────────────


def trail_stop_warnings() -> list[dict]:
    """
    Portföydeki hisseler sönüş aşamasındaki temaya bağlıysa,
    trail stop sıkılaştırma uyarısı için liste döndür.
    Tekrar bildirim 7 gün lookback ile önlenir.
    """
    dying = get_dying_themes()
    if not dying:
        return []

    pf_map = get_portfolio_theme_map()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    existing = read_events(event_type="trail_stop_warning", since=cutoff)
    already_warned = {e.get("symbol", "").upper() for e in existing}

    warnings_list = []
    for sym, theme_ids in pf_map.items():
        affecting = [tid for tid in theme_ids if tid in dying]
        if not affecting:
            continue
        if sym.upper() in already_warned:
            continue
        warnings_list.append({
            "symbol": sym,
            "dying_theme_ids": affecting,
            "theme_details": [
                {"id": tid, "name": dying[tid].get("name"),
                 "score": dying[tid].get("momentum_score")}
                for tid in affecting
            ],
        })
    return warnings_list


def format_trail_stop_message(w: dict) -> str:
    """DM'ye gidecek trail stop uyarısı."""
    theme_str = ", ".join(td["name"] for td in w["theme_details"])
    lines = [
        f"⚠️ <b>TRAIL STOP ÖNERİSİ — {w['symbol']}</b>",
        "",
        f"Bağlı olduğun tema(lar) sönüş aşamasına düştü:",
        f"  • {theme_str}",
        "",
        f"<b>Öneri:</b> Mevcut stop'u yukarı çek (kâr koruma).",
        f"Stop seviyesi belirleme: son 3 gün düşüğü - 1×ATR(14)",
        "",
        f"<i>finzora ai — sönüş tema bildirimi</i>",
    ]
    return "\n".join(lines)


# ────────────────────────── Main ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram", action="store_true",
                        help="Group'a alım sinyali, DM'ye trail stop uyarısı gönder")
    parser.add_argument("--dry-run", action="store_true",
                        help="Hiçbir mesaj gönderme, sadece aday listesini yazdır")
    args = parser.parse_args()

    log("Başlat: sinyal taraması")

    # 1. Alım sinyali adayları
    candidates = find_signal_candidates()
    log(f"Sinyal adayı sayısı: {len(candidates)}")

    # 2. Trail stop uyarıları
    warnings_list = trail_stop_warnings()
    log(f"Trail stop uyarısı sayısı: {len(warnings_list)}")

    if not candidates and not warnings_list:
        log("Bildirim için aday yok. Çıkıyor.")
        return 0

    # 3. Yayın
    for c in candidates:
        msg = format_signal_message(c)
        print("\n" + msg.replace("<b>", "**").replace("</b>", "**")
                  .replace("<i>", "_").replace("</i>", "_"))

        if args.telegram and not args.dry_run:
            try:
                from agent.telegram import send_to_group
                send_to_group(msg)
                log(f"  {c['symbol']} GROUP'a gönderildi")
                write_event({
                    "type": "signal_sent",
                    "symbol": c["symbol"],
                    "score": c["score"],
                    "current_price": c["current_price"],
                    "entry_zone": c["entry_zone"],
                    "stop_loss": c["stop_loss"],
                    "target": c["target"],
                    "in_zone": c["in_zone"],
                })
            except Exception as e:
                log(f"  GROUP gönderim hatası: {e}")
        elif args.dry_run:
            log(f"  DRY RUN — {c['symbol']} gönderilmedi (yine de yazdırıldı)")

    for w in warnings_list:
        msg = format_trail_stop_message(w)
        print("\n" + msg.replace("<b>", "**").replace("</b>", "**")
                  .replace("<i>", "_").replace("</i>", "_"))

        if args.telegram and not args.dry_run:
            try:
                from agent.telegram import send_to_dm
                send_to_dm(msg)
                log(f"  {w['symbol']} trail stop DM gönderildi")
                write_event({
                    "type": "trail_stop_warning",
                    "symbol": w["symbol"],
                    "dying_themes": w["dying_theme_ids"],
                })
            except Exception as e:
                log(f"  DM gönderim hatası: {e}")
        elif args.dry_run:
            log(f"  DRY RUN — {w['symbol']} trail stop uyarısı yazdırıldı")

    return 0


if __name__ == "__main__":
    sys.exit(main())
