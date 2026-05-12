"""
Bilanço Müdürü — Ana Orchestrator

Telegram bot thread'inden her 60 saniyede çağrılır:
    from agent.bilanco_muduru import bilanco_muduru_tick
    bilanco_muduru_tick()

İçeride saat kontrolü yapılıp uygun pencerede iş çıkarılır:
  08:30 → catchup_morning (gece+hafta sonu 8-K kontrol)
  13:00-16:30 (15dk) → bmo_window (BMO bilançolar)
  17:00 → record_t_minus_1_snapshots (yarın açıklayacak şirketler için)
  22:00-01:30 (15dk) → amc_window (AMC bilançolar)
  02:00 → catchup_late (AMC geç bilançolar)
"""
from __future__ import annotations
import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from .config import (
    AMC_EARLY_START_HOUR, AMC_EARLY_END_HOUR, AMC_EARLY_INTERVAL_MIN,
    BMO_START_HOUR, BMO_END_HOUR, BMO_INTERVAL_MIN,
    T_MINUS_1_SNAPSHOT_HOUR, T_MINUS_1_SNAPSHOT_MINUTE,
    CATCHUP_MORNING_HOUR, CATCHUP_MORNING_MINUTE,
    CATCHUP_LATE_HOUR, CATCHUP_LATE_MINUTE,
    MAX_DAILY_KIMI_CALLS,
    EARNINGS_SNAPSHOTS_DIR,
    EARNINGS_RESULTS_DIR,
    BILANCO_MUDURU_LOG,
    DRY_RUN,
    get_openrouter_key,
)
from .state_tracker import is_processed, mark_processed, get_today_kimi_call_count
from .earnings_scanner import (
    find_today_earnings_companies,
    find_latest_earnings_8k,
    fetch_press_release_text,
)
from .dm_notifier import notify_decision, notify_status


# Tick "lock" — aynı pencerede 2 tick aynı anda çakışmasın
_last_tick_window: dict[str, datetime] = {}

TR_TZ = ZoneInfo("Europe/Istanbul")


def _log(msg: str) -> None:
    """Basit dosya log."""
    try:
        log_path = Path(BILANCO_MUDURU_LOG)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            ts = datetime.utcnow().isoformat()
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass
    print(f"[BilancoMuduru] {msg}")


def _tr_now() -> datetime:
    return datetime.now(TR_TZ)


def _in_window(now: datetime, start_hour: int, end_hour: int) -> bool:
    """
    Saat aralığında mı? end_hour > 24 ise ertesi güne sarar (örn 22-25 = 22-01).
    """
    hour = now.hour
    if end_hour <= 24:
        return start_hour <= hour < end_hour
    # Wrap-around (22-25 → 22-24 veya 00-01)
    return hour >= start_hour or hour < (end_hour - 24)


def _interval_passed(window_name: str, interval_min: int, now: datetime) -> bool:
    """
    Belirli pencere için son tick'ten interval_min geçti mi?
    """
    last = _last_tick_window.get(window_name)
    if last is None:
        _last_tick_window[window_name] = now
        return True
    if (now - last).total_seconds() >= interval_min * 60:
        _last_tick_window[window_name] = now
        return True
    return False


def _is_one_shot_time(now: datetime, target_hour: int, target_minute: int = 0) -> bool:
    """
    Tek seferlik tetik — belirli dakikaya isabet etti mi (60s tolerans)?
    Aynı gün tekrar tetiklenmesini önlemek için window_name = "{hour}:{minute}_{date}"
    """
    if now.hour != target_hour:
        return False
    if not (target_minute <= now.minute <= target_minute + 1):
        return False
    key = f"oneshot_{target_hour:02d}{target_minute:02d}_{now.date().isoformat()}"
    if key in _last_tick_window:
        return False
    _last_tick_window[key] = now
    return True


def bilanco_muduru_tick() -> None:
    """
    Ana tick fonksiyonu. Telegram bot her 60 saniyede çağırır.
    İçeride saat kontrol → uygun pencerede iş yap.
    """
    now = _tr_now()

    # Hafta sonu: sadece catchup yap (NYSE kapalı, bilanço açıklamaları minimal)
    is_weekend = now.weekday() >= 5  # 5=Cmt, 6=Pzr

    # 1. 08:30 — Sabah catchup (gece + hafta sonu kaçanlar)
    if _is_one_shot_time(now, CATCHUP_MORNING_HOUR, CATCHUP_MORNING_MINUTE):
        _log("Sabah catchup başlıyor")
        _run_catchup_scan(now, scan_window="amc_late_and_morning")

    if is_weekend:
        return  # Hafta sonu sadece sabah catchup

    # 2. 13:00-16:30 — BMO penceresi (15dk)
    if _in_window(now, BMO_START_HOUR, BMO_END_HOUR):
        if _interval_passed("bmo_window", BMO_INTERVAL_MIN, now):
            _log("BMO pencere tarama")
            _run_earnings_scan(now, window="bmo")

    # 3. 17:00 — T-1 snapshot kayıt (yarın AMC açıklayacaklar için)
    if _is_one_shot_time(now, T_MINUS_1_SNAPSHOT_HOUR, T_MINUS_1_SNAPSHOT_MINUTE):
        _log("T-1 snapshot kayıt başlıyor")
        _record_t_minus_1_snapshots(now)

    # 4. 22:00-01:30 — AMC erken penceresi (15dk)
    if _in_window(now, AMC_EARLY_START_HOUR, AMC_EARLY_END_HOUR):
        if _interval_passed("amc_window", AMC_EARLY_INTERVAL_MIN, now):
            _log("AMC pencere tarama")
            _run_earnings_scan(now, window="amc")

    # 5. 02:00 — AMC geç catchup
    if _is_one_shot_time(now, CATCHUP_LATE_HOUR, CATCHUP_LATE_MINUTE):
        _log("Gece geç catchup başlıyor")
        _run_catchup_scan(now, scan_window="amc_late")


def _run_earnings_scan(now: datetime, window: str) -> None:
    """
    Belirli pencere için bilanço açıklayacak şirketleri tara,
    yeni 8-K'ları işle.
    """
    # Maliyet koruması
    if get_today_kimi_call_count() >= MAX_DAILY_KIMI_CALLS:
        _log(f"Günlük Kimi limit doldu ({MAX_DAILY_KIMI_CALLS}) — tarama atlandı")
        return

    target_date = now.date()
    # AMC penceresinde 22:00 sonrası: bugünün bilançoları
    # AMC penceresinde 00:00-01:30: dün AMC bilançoları (since gün başına geçti)
    if window == "amc" and now.hour < 12:
        target_date = (now - timedelta(days=1)).date()

    try:
        companies = find_today_earnings_companies(target_date=target_date, window=window)
    except Exception as e:
        _log(f"Earnings calendar fetch hatası: {e}")
        return

    if not companies:
        _log(f"{window} {target_date}: bilanço açıklayan şirket yok")
        return

    _log(f"{window} {target_date}: {len(companies)} aday şirket")

    processed_count = 0
    candidates_checked = 0
    for company in companies[:200]:  # Maks 200 ticker tara (FMP earnings calendar 2000+ olabiliyor)
        candidates_checked += 1
        ticker = company["ticker"]

        # 8-K dosyalandı mı? (free, SEC EDGAR)
        filing = find_latest_earnings_8k(ticker, since_date=target_date - timedelta(days=2))
        if not filing:
            continue

        fiscal_period = _estimate_fiscal_period(ticker, filing["filing_date"])
        if is_processed(ticker, fiscal_period):
            continue

        # 8-K var → şimdi mcap kontrol (FMP quote, 1 çağrı)
        from .earnings_scanner import get_market_cap_b
        from .config import MIN_MARKET_CAP_B
        mcap = get_market_cap_b(ticker)
        if mcap is None or mcap < MIN_MARKET_CAP_B:
            _log(f"{ticker} mcap kontrol başarısız (mcap=${mcap}B < ${MIN_MARKET_CAP_B}B) — atlandı")
            continue

        # Process et
        try:
            _process_earnings_8k(ticker, fiscal_period, filing, current_price_hint=None)
            processed_count += 1
        except Exception as e:
            _log(f"{ticker} işleme hatası: {e}")
            mark_processed(
                ticker=ticker,
                fiscal_period=fiscal_period,
                filing_date=filing["filing_date"],
                decision="HATA",
                dry_run=DRY_RUN,
                error=str(e),
            )

    if processed_count > 0:
        _log(f"{window} {target_date}: {candidates_checked} aday kontrol, {processed_count} bilanço işlendi")


def _run_catchup_scan(now: datetime, scan_window: str) -> None:
    """
    Geriye dönük (kaçırılan) 8-K'ları tara.
    Sabah catchup: dün AMC + bu hafta sonu
    Gece catchup: bugün AMC geç (01:30-02:00 arası açıklayanlar)
    """
    if scan_window == "amc_late_and_morning":
        # Dün AMC + bu sabah
        target_dates = [
            (now - timedelta(days=1)).date(),  # Dün
            (now - timedelta(days=2)).date(),  # Önceki gün (haftasonu için)
            (now - timedelta(days=3)).date(),
        ]
    else:  # amc_late
        target_dates = [now.date()]

    seen_companies = set()
    for d in target_dates:
        try:
            companies = find_today_earnings_companies(target_date=d, window="all")
        except Exception as e:
            _log(f"Catchup {d} hatası: {e}")
            continue

        for company in companies[:30]:
            ticker = company["ticker"]
            if ticker in seen_companies:
                continue
            seen_companies.add(ticker)

            filing = find_latest_earnings_8k(ticker, since_date=d - timedelta(days=1))
            if not filing:
                continue

            fiscal_period = _estimate_fiscal_period(ticker, filing["filing_date"])
            if is_processed(ticker, fiscal_period):
                continue

            try:
                _process_earnings_8k(ticker, fiscal_period, filing)
            except Exception as e:
                _log(f"Catchup {ticker} hatası: {e}")


def _process_earnings_8k(
    ticker: str,
    fiscal_period: str,
    filing: dict,
    current_price_hint: Optional[float] = None,
) -> None:
    """
    Tek bir bilanço 8-K'yı tam pipeline'dan geçir:
      1. Exhibit 99.1 fetch
      2. Kimi parse
      3. Snapshot oku (varsa)
      4. Implied multiple valuation
      5. DM bildirim
      6. State'e mark
    """
    # 1. Exhibit 99.1 fetch
    ex991_url = filing.get("exhibit_99_1_url")
    if not ex991_url:
        raise ValueError(f"Exhibit 99.1 link'i bulunamadı")

    press_text = fetch_press_release_text(ex991_url)
    if not press_text or len(press_text) < 1000:
        raise ValueError(f"Press release fetch başarısız veya çok kısa")

    # 2. Kimi parse
    from agent.earnings_night import KimiEarningsParser, implied_multiple_valuation
    parser = KimiEarningsParser(api_key=get_openrouter_key())
    result = parser.parse_8k(
        ticker=ticker,
        company_name=ticker,  # Şirket adı opsiyonel, ticker yeterli
        filing_date=filing["filing_date"],
        fiscal_period=fiscal_period,
        document_text=press_text,
    )

    if not result.success:
        raise ValueError(f"Kimi parse başarısız: {result.error}")

    parsed = result.parsed

    # Parsed çıktıyı kaydet
    results_dir = Path(EARNINGS_RESULTS_DIR)
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / f"{ticker}_{fiscal_period.replace(' ', '_')}_parsed.json", "w") as f:
        f.write(parsed.model_dump_json(indent=2))

    # 3. Snapshot oku (varsa kullan)
    snapshot = _load_snapshot(ticker)
    valuation = None
    if snapshot:
        try:
            from .snapshot_recorder_bridge import snapshot_to_valuation_inputs
            inputs = snapshot_to_valuation_inputs(snapshot)
            valuation = implied_multiple_valuation(
                parse_result=parsed,
                **inputs,
                apply_multiple_revision=True,
                use_normalized_eps=True,
            )
        except Exception as e:
            _log(f"{ticker} valuation hatası: {e}")

    # 4. DM bildirim
    if valuation:
        notify_decision(ticker, fiscal_period, parsed, valuation, snapshot or {})
        decision = valuation.get("decision", "?")
        target_avg = valuation.get("new_targets", {}).get("target_avg")
        target_high = valuation.get("new_targets", {}).get("target_high")
        current_price = valuation.get("current_price")
    else:
        # Snapshot yok — sadece parse sonucu bildir
        msg = f"⚠️ {ticker} {fiscal_period}: Pre-earnings snapshot yok, sadece parse yapıldı."
        notify_status(msg, level="WARN")
        decision = "SNAPSHOT_YOK"
        target_avg = target_high = current_price = None

    # 5. State'e mark
    mark_processed(
        ticker=ticker,
        fiscal_period=fiscal_period,
        filing_date=filing["filing_date"],
        decision=decision,
        target_avg=target_avg,
        target_high=target_high,
        current_price=current_price,
        dry_run=DRY_RUN,
        kimi_cost_usd=result.cost_usd,
    )

    _log(f"{ticker} {fiscal_period} işlendi: {decision} (cost: ${result.cost_usd:.4f})")


def _load_snapshot(ticker: str) -> Optional[dict]:
    """data/earnings_snapshots/ klasöründen en son snapshot'ı yükle."""
    snap_dir = Path(EARNINGS_SNAPSHOTS_DIR)
    if not snap_dir.exists():
        return None
    candidates = sorted(snap_dir.glob(f"{ticker}_*.json"), reverse=True)
    if not candidates:
        return None
    try:
        with open(candidates[0]) as f:
            return json.load(f)
    except Exception:
        return None


def _record_t_minus_1_snapshots(now: datetime) -> None:
    """
    Yarın AMC + bugün BMO açıklayacak şirketler için snapshot kaydet.
    """
    tomorrow = (now + timedelta(days=1)).date()
    today = now.date()

    # Yarın AMC + yarın BMO + (Cuma akşamı çalışıyorsak Pazartesi'yi de kapsa)
    target_dates = [tomorrow]
    if now.weekday() == 4:  # Cuma
        target_dates.append(tomorrow + timedelta(days=3))  # Pazartesi

    tickers = set()
    for d in target_dates:
        try:
            companies = find_today_earnings_companies(target_date=d, window="all")
            tickers.update(c["ticker"] for c in companies)
        except Exception as e:
            _log(f"Calendar fetch {d} hatası: {e}")

    if not tickers:
        notify_status(f"T-1 snapshot: yarın/önümüz için bilanço bulunamadı", level="INFO")
        return

    from .snapshot_recorder_bridge import record_snapshot_safe
    success_count = 0
    fail_count = 0
    for ticker in list(tickers)[:30]:
        if record_snapshot_safe(ticker):
            success_count += 1
        else:
            fail_count += 1

    notify_status(
        f"T-1 snapshot kaydı tamamlandı: {success_count} başarılı, {fail_count} hata",
        level="SUCCESS" if success_count else "WARN"
    )


def _estimate_fiscal_period(ticker: str, filing_date: str) -> str:
    """
    Filing tarihinden çeyrek tahmini.
    NVDA fiscal year farklı; çoğu şirket calendar year takip eder.
    """
    try:
        dt = datetime.fromisoformat(filing_date)
        month = dt.month
        year = dt.year
        # NVDA fiscal year offset (Ocak sonu biter)
        if ticker.upper() == "NVDA":
            # Şubat = Q4 FY önceki + 1, Mayıs = Q1 FY current, Ağustos = Q2, Kasım = Q3
            if month <= 2:
                return f"Q4 FY{year}"  # Şubat 2026 raporu = Q4 FY26
            elif month <= 5:
                return f"Q1 FY{year + 1}"  # Mayıs 2026 raporu = Q1 FY27
            elif month <= 8:
                return f"Q2 FY{year + 1}"
            else:
                return f"Q3 FY{year + 1}"
        # Standart calendar year
        q = (month - 1) // 3
        if q == 0:
            return f"Q4 {year - 1}"  # Şubat raporu = Q4 önceki yıl
        else:
            return f"Q{q} {year}"
    except Exception:
        return f"Unknown_{filing_date}"
