#!/usr/bin/env python3
"""Watchlist Sağlık Taraması — Polymarket çelişki uyarıları.

Faz 2 — Adım 11 (17 May 2026). Pozisyon #3 implementasyonu.

Bu script:
    1. Watchlist'teki tüm ticker'ları yükler
    2. PolymarketCalibrator.watchlist_health_check(symbols) çağırır
    3. Çelişki bayrakları (pm_conflict / pm_conflict_weak) için alert üretir
    4. Yeni çelişkiler (önceden raporlanmamış) için Zeynel DM gönderir

State dosyası:
    data/watchlist_health_state.json
    Idempotency için: aynı (symbol, theme, flag) tuple'ı 24 saat içinde
    tekrar DM atılmaz.

Çalışma modeli:
    Adım 11 — workflow_dispatch only, cron yok (manuel veya 10b-iii flag
    rollout sonrası açılır). Production'da günde 1 kez (örn. session öncesi
    UTC 12:00 = TR 15:00) çalıştırılması önerilir.

Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 2 Pozisyon #3)
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


# State dosyası — daha önce raporlanmış alertları izler
_STATE_PATH = _REPO_ROOT / "data" / "watchlist_health_state.json"

# Aynı (symbol, theme_id, flag) tuple'ı için cooldown
_ALERT_COOLDOWN_HOURS = 24


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [watchlist-health] {msg}", flush=True)


def _load_state() -> dict:
    """State dosyası: {alerts: [{symbol, theme_id, flag, ts}, ...]}"""
    if not _STATE_PATH.exists():
        return {"alerts": []}
    try:
        with _STATE_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"alerts": []}
            return data
    except Exception as e:
        log(f"State yükleme hatası, sıfırdan başlanıyor: {e}")
        return {"alerts": []}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _prune_old_state(state: dict, now: datetime) -> dict:
    """24h+ eski alert kayıtlarını state'ten temizle."""
    cutoff = now - timedelta(hours=_ALERT_COOLDOWN_HOURS)
    pruned = []
    for entry in state.get("alerts", []):
        if not isinstance(entry, dict):
            continue
        try:
            entry_ts = datetime.fromisoformat(
                entry.get("ts", "").replace("Z", "+00:00")
            )
            if entry_ts >= cutoff:
                pruned.append(entry)
        except (ValueError, TypeError):
            continue  # bozuk entry, atla
    state["alerts"] = pruned
    return state


def _is_new_alert(alert: dict, state: dict) -> bool:
    """Bu (symbol, theme_id, flag) tuple'ı son 24 saatte raporlandı mı?"""
    key = (alert["symbol"], alert["theme_id"], alert["flag"])
    for entry in state.get("alerts", []):
        existing = (entry.get("symbol"), entry.get("theme_id"), entry.get("flag"))
        if existing == key:
            return False
    return True


def _format_alert(alert: dict) -> str:
    """Tek alert için Telegram-uyumlu satır (markdown)."""
    severity_icon = "🔴" if alert["severity"] == "strong" else "🟡"
    delta_pct = alert.get("delta_24h", 0) * 100
    return (
        f"{severity_icon} *{alert['symbol']}* — `{alert['theme_id']}` "
        f"({alert.get('matched_side', '?')})\n"
        f"   Polymarket 24h delta: {delta_pct:+.1f}pp · "
        f"Market: `{alert['market_slug']}`\n"
        f"   Bayrak: `{alert['flag']}` ({alert['severity']})"
    )


def _format_dm(new_alerts: list[dict]) -> str:
    """Toplu DM mesajı."""
    n_strong = sum(1 for a in new_alerts if a["severity"] == "strong")
    n_weak = sum(1 for a in new_alerts if a["severity"] == "weak")

    header = (
        "⚠️ *Watchlist Sağlık Uyarısı* (Polymarket çelişki)\n"
        f"Yeni alert: {len(new_alerts)} "
        f"({n_strong} güçlü, {n_weak} zayıf)\n"
        f"_Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n\n"
    )
    body = "\n\n".join(_format_alert(a) for a in new_alerts)
    footer = (
        "\n\n_Bu hisseler watchlist'te kalıyor — kalibratör veto yapmıyor. "
        "Tezin hâlâ geçerli mi gözden geçir._"
    )
    return header + body + footer


def _send_dm(text: str, dry_run: bool = False) -> bool:
    """Zeynel DM hedefine mesaj gönder."""
    if dry_run:
        log("DRY-RUN: DM gönderilmedi")
        print("=" * 60)
        print(text)
        print("=" * 60)
        return True

    try:
        from scripts.telegram_notify import send_message, TELEGRAM_PRIVATE_ID
        return send_message(text, parse_mode="Markdown",
                            chat_id=TELEGRAM_PRIVATE_ID)
    except Exception as e:
        log(f"DM gönderim hatası: {e}")
        return False


def run_check(
    symbols: Optional[list[str]] = None,
    calibrator=None,
    state: Optional[dict] = None,
    now: Optional[datetime] = None,
    dry_run: bool = False,
) -> dict:
    """Sağlık taramasını çalıştır + yeni alertler için DM.

    Args:
        symbols: opsiyonel — None ise watchlist.all_symbols() kullanılır
        calibrator: opsiyonel kalibratör instance (test için)
        state: opsiyonel state dict (test için)
        now: opsiyonel datetime (test için)
        dry_run: True ise DM atılmaz, sadece konsola yazdırılır

    Returns:
        {"total_alerts": N, "new_alerts": N, "dm_sent": bool}
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Watchlist symbols
    if symbols is None:
        try:
            from agent.watchlist import all_symbols
            symbols = all_symbols()
        except Exception as e:
            log(f"Watchlist yükleme hatası: {e}")
            return {"total_alerts": 0, "new_alerts": 0, "dm_sent": False}

    if not symbols:
        log("Watchlist boş")
        return {"total_alerts": 0, "new_alerts": 0, "dm_sent": False}

    log(f"Watchlist: {len(symbols)} ticker")

    # Kalibratör instance
    if calibrator is None:
        try:
            from agent.scanners.calibrator import PolymarketCalibrator
            calibrator = PolymarketCalibrator()
        except Exception as e:
            log(f"Kalibratör başlatma hatası: {e}")
            return {"total_alerts": 0, "new_alerts": 0, "dm_sent": False}

    # Tarama
    try:
        alerts = calibrator.watchlist_health_check(symbols)
    except Exception as e:
        log(f"Sağlık taraması hatası: {e}")
        return {"total_alerts": 0, "new_alerts": 0, "dm_sent": False}

    log(f"Toplam alert: {len(alerts)}")
    if not alerts:
        return {"total_alerts": 0, "new_alerts": 0, "dm_sent": False}

    # State + idempotency
    if state is None:
        state = _load_state()
    state = _prune_old_state(state, now)

    new_alerts = [a for a in alerts if _is_new_alert(a, state)]
    log(f"Yeni alert (24h cooldown sonrası): {len(new_alerts)}")

    if not new_alerts:
        log("Yeni alert yok, DM atılmadı")
        # State'i yine de yaz (prune değişikliği kaydedilsin)
        _save_state(state)
        return {"total_alerts": len(alerts), "new_alerts": 0, "dm_sent": False}

    # DM gönder
    dm_text = _format_dm(new_alerts)
    dm_sent = _send_dm(dm_text, dry_run=dry_run)

    # State güncelle (DM başarılı veya dry-run sonrası kaydet — idempotency)
    if dm_sent or dry_run:
        for alert in new_alerts:
            state["alerts"].append({
                "symbol": alert["symbol"],
                "theme_id": alert["theme_id"],
                "flag": alert["flag"],
                "ts": now.isoformat(),
            })
        _save_state(state)

    return {
        "total_alerts": len(alerts),
        "new_alerts": len(new_alerts),
        "dm_sent": dm_sent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="DM atma, sadece konsola yazdır + state güncelle",
    )
    args = parser.parse_args(argv)

    log("Watchlist sağlık taraması başlıyor")
    try:
        result = run_check(dry_run=args.dry_run)
    except Exception as e:
        log(f"HATA: tarama çöktü: {e}")
        return 1

    log(
        f"Bitti — toplam={result['total_alerts']}, "
        f"yeni={result['new_alerts']}, dm_sent={result['dm_sent']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
