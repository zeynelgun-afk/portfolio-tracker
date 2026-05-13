"""
Analist Takip — Ana Orchestrator

Telegram bot thread'inden her 60 saniyede çağrılır:
    from agent.analist_takip import analist_takip_tick
    analist_takip_tick()

İçeride saat kontrolü:
  13:00-16:30 (TR): 60dk polling (pre-NYSE)
  16:30-23:30 (TR): 30dk polling (NYSE açık)
  23:30-01:30 (TR): 30dk polling (after-hours)
  Cumartesi 10:00: Haftalık özet + catchup

Her polling'de:
  1. Watchlist yenile (portföy + son 14 gün bilanço)
  2. Her ticker için son 48h revizyonları çek (3 endpoint)
  3. Threshold-based karar üret
  4. Yeni & sinyal varsa DM gönder (cooldown 4 saat)
  5. Audit log: data/analist_takip/signals.jsonl
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from .config import (
    PRE_NYSE_START_HOUR, PRE_NYSE_END_HOUR, PRE_NYSE_INTERVAL_MIN,
    NYSE_OPEN_START_HOUR, NYSE_OPEN_END_HOUR, NYSE_OPEN_INTERVAL_MIN,
    AFTER_HOURS_START_HOUR, AFTER_HOURS_END_HOUR, AFTER_HOURS_INTERVAL_MIN,
    SATURDAY_CATCHUP_HOUR, SATURDAY_CATCHUP_MINUTE,
    SIGNAL_WINDOW_TOTAL_HOURS,
    ANALIST_LOG,
    DRY_RUN,
)
from .revision_fetcher import (
    fetch_all_signals,
    get_current_price,
    get_market_cap_b,
    get_last_actual_earnings_date,
    get_target_consensus,
)
from .signal_analyzer import analyze_signals
from .state_tracker import (
    filter_unseen, mark_revision_seen, record_signal,
    already_signaled_recently,
)
from .dm_notifier import notify_signal, notify_status
from .watchlist import build_watchlist, save_watchlist


TR_TZ = ZoneInfo("Europe/Istanbul")

# Tick rate limiting per window
_last_tick_window: dict[str, datetime] = {}

# Watchlist cache (her ~6 saatte yenile)
_watchlist_cache: dict = {}
_watchlist_built_at: Optional[datetime] = None
_WATCHLIST_CACHE_HOURS = 6


def _log(msg: str) -> None:
    """Basit dosya log."""
    try:
        log_path = Path(ANALIST_LOG)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            ts = datetime.utcnow().isoformat()
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass
    print(f"[AnalistTakip] {msg}")


def _tr_now() -> datetime:
    return datetime.now(TR_TZ)


def _in_window(now: datetime, start_hour: int, end_hour: int) -> bool:
    """Saat aralığında mı? end_hour > 24 ise ertesi güne sarar."""
    hour = now.hour
    if end_hour <= 24:
        return start_hour <= hour < end_hour
    # Wrap-around (23-26 = 23-02)
    return hour >= start_hour or hour < (end_hour - 24)


def _interval_passed(window_name: str, interval_min: int, now: datetime) -> bool:
    last = _last_tick_window.get(window_name)
    if last is None:
        _last_tick_window[window_name] = now
        return True
    if (now - last).total_seconds() >= interval_min * 60:
        _last_tick_window[window_name] = now
        return True
    return False


def _is_one_shot_time(now: datetime, target_hour: int, target_minute: int = 0) -> bool:
    """Belirli dakikaya isabet etti mi (60s tolerans)?"""
    if now.hour != target_hour:
        return False
    if not (target_minute <= now.minute <= target_minute + 1):
        return False
    key = f"oneshot_{target_hour:02d}{target_minute:02d}_{now.date().isoformat()}"
    if key in _last_tick_window:
        return False
    _last_tick_window[key] = now
    return True


def _refresh_watchlist_if_needed(now_utc: datetime) -> list[str]:
    """6 saatte bir watchlist yenile, cache'le."""
    global _watchlist_cache, _watchlist_built_at

    needs_rebuild = (
        _watchlist_built_at is None
        or (now_utc - _watchlist_built_at).total_seconds() >= _WATCHLIST_CACHE_HOURS * 3600
    )

    if needs_rebuild:
        _log("Watchlist yenileniyor...")
        try:
            _watchlist_cache = build_watchlist()
            save_watchlist(_watchlist_cache)
            _watchlist_built_at = now_utc
            _log(f"Watchlist: {_watchlist_cache['total_count']} ticker "
                 f"(portföy {_watchlist_cache['portfolio_count']}, "
                 f"bilanço {_watchlist_cache['recent_earnings_count']}, "
                 f"manuel {_watchlist_cache['manual_count']})")
        except Exception as e:
            _log(f"Watchlist build hatası: {e}")
            if not _watchlist_cache:
                _watchlist_cache = {"combined": []}

    return _watchlist_cache.get("combined", [])


def analist_takip_tick() -> None:
    """
    Ana tick fonksiyonu. Telegram bot her 60 saniyede çağırır.
    """
    now = _tr_now()
    now_utc = datetime.now(timezone.utc)

    # Hangi pencere aktif?
    is_weekend = now.weekday() >= 5

    # Cumartesi 10:00 catchup
    if now.weekday() == 5 and _is_one_shot_time(now, SATURDAY_CATCHUP_HOUR, SATURDAY_CATCHUP_MINUTE):
        _log("Cumartesi haftalık catchup başlıyor")
        _run_polling_cycle(now_utc, label="Cmt catchup", priority="catchup")
        return

    if is_weekend:
        return  # Diğer haftasonu sessiz

    # Pencereler (sıralı kontrol, ilk match'leyen çalışır)
    if _in_window(now, AFTER_HOURS_START_HOUR, AFTER_HOURS_END_HOUR):
        if _interval_passed("after_hours", AFTER_HOURS_INTERVAL_MIN, now):
            _run_polling_cycle(now_utc, label="After-hours")
            return

    if _in_window(now, NYSE_OPEN_START_HOUR, NYSE_OPEN_END_HOUR):
        if _interval_passed("nyse_open", NYSE_OPEN_INTERVAL_MIN, now):
            _run_polling_cycle(now_utc, label="NYSE açık")
            return

    if _in_window(now, PRE_NYSE_START_HOUR, PRE_NYSE_END_HOUR):
        if _interval_passed("pre_nyse", PRE_NYSE_INTERVAL_MIN, now):
            _run_polling_cycle(now_utc, label="Pre-NYSE")
            return


def _run_polling_cycle(
    now_utc: datetime,
    label: str = "polling",
    priority: str = "normal",
) -> None:
    """
    Bir polling cycle: watchlist için tüm sinyalleri çek + karar üret + DM.
    """
    tickers = _refresh_watchlist_if_needed(now_utc)
    if not tickers:
        _log(f"{label}: watchlist boş, polling atlandı")
        return

    _log(f"{label}: {len(tickers)} ticker polling")

    since = now_utc - timedelta(hours=SIGNAL_WINDOW_TOTAL_HOURS)
    signals_found = 0
    decisions_sent = 0

    for ticker in tickers:
        try:
            # 1. Sinyalleri çek
            signals = fetch_all_signals(ticker, since)
            if not signals:
                continue

            # 2. İşlenmemiş olanları filtrele (idempotency)
            unseen = filter_unseen(signals)

            # 3. Son tamamlanmış bilanço tarihini al (drift filter için)
            last_earnings = get_last_actual_earnings_date(ticker)

            # 4. Karar üret (post-earnings drift mantığıyla)
            decision = analyze_signals(
                ticker, signals,
                now=now_utc,
                last_earnings_date=last_earnings,
                require_post_earnings=True,
            )

            # 4. Anlamlı bir karar mı? DM filter ayarlarına göre kontrol
            #    (Zeynel /analist dm komutuyla preset değiştirebilir)
            from .dm_settings import should_send_dm
            if not should_send_dm(decision):
                # Filter dışı — sadece state'e işaretle, DM atma
                for s in unseen:
                    mark_revision_seen(s)
                continue

            # 5. Cooldown: aynı ticker + aynı decision son 4h içinde DM atıldı mı?
            if already_signaled_recently(ticker, decision["decision"], cooldown_hours=4):
                # Mark et ama DM atma
                for s in unseen:
                    mark_revision_seen(s)
                continue

            # 6. DM göndermeden önce yeni revizyonların var olduğunu doğrula
            if not unseen:
                # Tüm sinyaller daha önce görülmüş; bu karar zaten DM edildi sayılır
                continue

            # 7. Mevcut fiyat + mcap + analist hedef özeti fetch
            current_price = None
            market_cap_b = None
            target_consensus = None
            try:
                from .revision_fetcher import _fmp_get
                quote_data = _fmp_get("quote", symbol=ticker)
                if isinstance(quote_data, list) and quote_data:
                    q = quote_data[0]
                    current_price = q.get("price")
                    market_cap_b = round(q.get("marketCap", 0) / 1e9, 2) if q.get("marketCap") else None
                target_consensus = get_target_consensus(ticker)
            except Exception:
                pass

            # 8. DM gönder
            success = notify_signal(
                decision,
                current_price=current_price,
                market_cap_b=market_cap_b,
                target_consensus=target_consensus,
            )

            # 9. State'e kaydet
            for s in unseen:
                mark_revision_seen(s)
            record_signal({
                **decision,
                "current_price": current_price,
                "market_cap_b": market_cap_b,
                "label": label,
            })

            # 10. AL kararları için performans watchlist'ine otomatik ekle
            if decision["decision"] in ("BUY", "STRONG_BUY"):
                try:
                    from .performance_tracker import add_to_watchlist
                    add_to_watchlist(
                        ticker,
                        decision,
                        current_price=current_price,
                        market_cap_b=market_cap_b,
                        manual=False,
                    )
                except Exception as e:
                    _log(f"{ticker} performans watchlist ekleme hatası: {e}")

                # 10b. Ana havuza da ekle (data/watchlist.json — Asama 3, 13 May 2026)
                # Sadece STRONG_BUY tetiğinde — düşük güvenli BUY'lar gönderilmiyor
                if decision["decision"] == "STRONG_BUY":
                    try:
                        from agent.watchlist import add as pool_add
                        avg_pct = decision.get("avg_revision_pct")
                        raised_count = decision.get("raised_count")
                        rationale = (
                            f"analist_takip STRONG_BUY: {raised_count or '?'} raise"
                            + (f", avg +{avg_pct:.1f}%" if avg_pct else "")
                        )
                        result = pool_add(
                            symbol=ticker,
                            source="analist_takip_strong_buy",
                            rationale=rationale,
                            price=current_price,
                            score_components={
                                "analist_takip": {
                                    "raised_count": raised_count,
                                    "avg_revision_pct": avg_pct,
                                    "decision_confidence": decision.get("confidence"),
                                },
                            },
                        )
                        if result["action"] in ("added", "updated"):
                            _log(f"{ticker} ana havuza eklendi/güncellendi: {result['action']}")
                    except Exception as e:
                        _log(f"{ticker} ana havuz ekleme hatası: {e}")

            if success:
                decisions_sent += 1
                _log(f"{ticker} → {decision['decision']} ({decision['confidence']}) — DM gönderildi")
            else:
                _log(f"{ticker} → {decision['decision']} — DM gönderim BAŞARISIZ")

            signals_found += len(unseen)

        except Exception as e:
            _log(f"{ticker} polling hatası: {e}")
            continue

    if decisions_sent > 0:
        _log(f"{label} tamamlandı: {decisions_sent} sinyal DM, {signals_found} yeni revizyon işlendi")
    elif signals_found > 0:
        _log(f"{label} tamamlandı: 0 DM (sinyaller WATCH/NEUTRAL veya cooldown'da), {signals_found} yeni revizyon")


def force_run_now(
    tickers: Optional[list[str]] = None,
    hours_back: Optional[int] = None,
) -> dict:
    """
    Test/debug için: tick zamanlaması gözetmeksizin polling çalıştır.

    Args:
        tickers: Spesifik ticker listesi (None ise watchlist kullanır)
        hours_back: Pencere genişliği saat olarak (None ise config default kullanır)

    Returns:
        Sonuç özeti
    """
    now_utc = datetime.now(timezone.utc)
    if tickers is None:
        tickers = _refresh_watchlist_if_needed(now_utc)

    window_hours = hours_back if hours_back is not None else SIGNAL_WINDOW_TOTAL_HOURS
    since = now_utc - timedelta(hours=window_hours)

    results = []

    for ticker in tickers:
        try:
            signals = fetch_all_signals(ticker, since)
            last_earnings = get_last_actual_earnings_date(ticker)
            decision = analyze_signals(
                ticker, signals,
                now=now_utc,
                window_hours=window_hours,
                last_earnings_date=last_earnings,
                require_post_earnings=True,
            )
            results.append({
                "ticker": ticker,
                "decision": decision["decision"],
                "confidence": decision["confidence"],
                "raised_48h": decision["raised_count_48h"],
                "lowered_48h": decision["lowered_count_48h"],
                "avg_pct": decision["avg_revision_pct"],
                "rationale": decision["rationale"],
                "biggest_raise": decision.get("biggest_raise"),
                "biggest_cut": decision.get("biggest_cut"),
                "drift_status": decision.get("drift_status"),
                "days_since_earnings": decision.get("days_since_earnings"),
                "last_earnings_date": decision.get("last_earnings_date"),
            })
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    return {
        "checked": len(results),
        "actionable": [r for r in results if r.get("decision") in ("BUY", "STRONG_BUY", "SELL", "STRONG_SELL")],
        "all": results,
        "window_hours": window_hours,
        "ran_at": now_utc.isoformat(),
    }
