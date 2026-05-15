"""
Analist Takip — Telegram Komut Yardımcıları

scripts/telegram_bot.py içinden çağrılacak format/sorgu fonksiyonları:
  - analyze_single_ticker_now()  ← /analist TICKER
  - format_watchlist_summary()   ← /analist watchlist
  - format_system_status()       ← /analist status
  - run_scan_now()               ← /analist tara

Bu modül DM göndermez (telegram_bot.py gönderir).
Sadece formatlı string döndürür.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .config import (
    SIGNAL_WINDOW_TOTAL_HOURS,
    SIGNAL_HISTORY_PATH,
    WATCHLIST_PATH,
    DRY_RUN,
    POST_EARNINGS_WATCH_DAYS,
)
from .revision_fetcher import (
    fetch_all_signals,
    get_target_consensus,
    get_last_actual_earnings_date,
    _fmp_get,
)
from .signal_analyzer import analyze_signals
from .dm_notifier import format_signal_message, DECISION_EMOJI, DECISION_TITLE
from .state_tracker import get_recent_signals
from .watchlist import build_watchlist, load_watchlist


def analyze_single_ticker_now(ticker: str, hours_back: int = 168) -> str:
    """
    Tek bir ticker için anlık analist sinyali çıkar ve formatla.

    Args:
        ticker: Hisse sembolü
        hours_back: Pencere genişliği saat (varsayılan 168=7gün)

    Returns:
        HTML formatlı Telegram mesajı
    """
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 6:
        return f"❌ Geçersiz ticker: <code>{ticker}</code>"

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours_back)

    # 1. Sinyalleri çek
    try:
        signals = fetch_all_signals(ticker, since)
    except Exception as e:
        return f"❌ <b>{ticker}</b> FMP veri alınamadı: {e}"

    # 2. Bilanço tarihi
    last_e = get_last_actual_earnings_date(ticker)

    # 3. Fiyat + mcap + consensus (gate için analyze_signals'dan ÖNCE)
    current_price = None
    market_cap_b = None
    target_consensus = None
    try:
        q = _fmp_get("quote", symbol=ticker)
        if isinstance(q, list) and q:
            current_price = q[0].get("price")
            mcap = q[0].get("marketCap", 0)
            market_cap_b = round(mcap / 1e9, 2) if mcap else None
        target_consensus = get_target_consensus(ticker)
    except Exception:
        pass

    # 4. Karar üret (price-target gap gate dahil)
    decision = analyze_signals(
        ticker, signals,
        now=now,
        window_hours=hours_back,
        last_earnings_date=last_e,
        require_post_earnings=True,
        current_price=current_price,
        target_consensus=target_consensus,
    )

    # 5. Tam DM formatını kullan
    msg = format_signal_message(
        decision,
        current_price=current_price,
        market_cap_b=market_cap_b,
        target_consensus=target_consensus,
    )

    # Manuel sorgu olduğunu işaretle
    msg = "<i>🔍 Manuel sorgu</i>\n\n" + msg

    # Drift bilgisi ekle
    if decision.get("drift_status"):
        days = decision.get("days_since_earnings")
        last_ed = decision.get("last_earnings_date")
        drift = decision["drift_status"]
        drift_line = ""
        if drift == "expired":
            drift_line = f"\n\n⏳ <i>Drift penceresi geçmiş ({days}d, eşik 14d)</i>"
        elif drift == "active":
            drift_line = f"\n\n📅 <i>Bilanço {days}d önce ({last_ed})</i>"
        elif drift == "no_recent_earnings":
            drift_line = f"\n\n📅 <i>Yakın bilanço bilgisi yok</i>"
        msg += drift_line

    return msg


def format_watchlist_summary() -> str:
    """
    Mevcut watchlist'in özetini döner.
    """
    # Cache'den oku (varsa)
    wl = load_watchlist()
    if not wl or not wl.get("combined"):
        # Cache yoksa yeniden build et (yavaş)
        wl = build_watchlist()

    lines = [
        f"<b>👀 Analist Takip Watchlist</b>",
        "",
        f"<b>Toplam:</b> {wl.get('total_count', 0)} ticker",
        f"  • Portföy: {wl.get('portfolio_count', 0)}",
        f"  • Son {POST_EARNINGS_WATCH_DAYS}g bilanço (mid-cap+): "
        f"{wl.get('recent_earnings_count', 0)}",
        f"  • Manuel: {wl.get('manual_count', 0)}",
    ]

    # Yapı: built_at göster
    built = wl.get("built_at", "")
    if built:
        lines.append(f"<i>Güncellendi: {built[:19]} UTC</i>")

    # Portföy ticker'ları
    portfolio = wl.get("portfolio", [])
    if portfolio:
        lines.append("")
        lines.append("<b>📊 Portföy:</b>")
        lines.append("  " + ", ".join(f"<code>{t}</code>" for t in portfolio[:30]))
        if len(portfolio) > 30:
            lines.append(f"  <i>... ve {len(portfolio) - 30} tane daha</i>")

    # Son bilanço açıklayanlar (en fazla 20)
    recent_e = wl.get("recent_earnings", [])
    if recent_e:
        lines.append("")
        lines.append(f"<b>📰 Son {POST_EARNINGS_WATCH_DAYS}g bilanço açıklayanlar (ilk 20):</b>")
        lines.append("  " + ", ".join(f"<code>{t}</code>" for t in recent_e[:20]))
        if len(recent_e) > 20:
            lines.append(f"  <i>... ve {len(recent_e) - 20} tane daha</i>")

    manual = wl.get("manual", [])
    if manual:
        lines.append("")
        lines.append("<b>✋ Manuel:</b>")
        lines.append("  " + ", ".join(f"<code>{t}</code>" for t in manual))

    return "\n".join(lines)


def format_system_status() -> str:
    """
    Sistem durumu: son 24h sinyalleri + DRY_RUN + watchlist sayısı.
    """
    recent = get_recent_signals(n=20)

    # Son 24h içindekiler
    cutoff = datetime.utcnow() - timedelta(hours=24)
    cutoff_iso = cutoff.isoformat()
    recent_24h = [r for r in recent
                  if r.get("recorded_at", "").replace("Z", "") >= cutoff_iso]

    # Watchlist
    try:
        wl = load_watchlist()
        wl_count = wl.get("total_count", 0) if wl else 0
    except Exception:
        wl_count = 0

    # State dosyaları
    state_dir = Path("data/analist_takip")
    processed_count = 0
    if state_dir.exists():
        p = state_dir / "processed_revisions.jsonl"
        if p.exists():
            try:
                with open(p) as f:
                    processed_count = sum(1 for _ in f)
            except Exception:
                pass

    mode = "🧪 DRY-RUN" if DRY_RUN else "🟢 PRODUCTION"

    lines = [
        f"<b>📡 Analist Takip Sistem Durumu</b>",
        "",
        f"<b>Mod:</b> {mode}",
        f"<b>Watchlist:</b> {wl_count} ticker",
        f"<b>İşlenen revizyon:</b> {processed_count} (toplam)",
        f"<b>Son 24h sinyal:</b> {len(recent_24h)}",
        "",
    ]

    # Son sinyaller (en yeni 10)
    if recent_24h:
        lines.append("<b>📜 Son 24h sinyalleri:</b>")
        for r in recent_24h[-10:][::-1]:  # Son 10, en yeni başta
            ticker = r.get("ticker", "?")
            decision = r.get("decision", "?")
            emoji = DECISION_EMOJI.get(decision, "")
            title = DECISION_TITLE.get(decision, decision)
            ts = r.get("recorded_at", "")[:16].replace("T", " ")
            cp = r.get("current_price")
            cp_str = f" @${cp:.2f}" if cp else ""
            rationale = r.get("rationale", "")[:50]
            lines.append(f"  {ts} | {emoji} <b>{ticker}</b>{cp_str} → {title}")
            if rationale:
                lines.append(f"     <i>{rationale}</i>")
    elif recent:
        # Son 24h boşsa son 5'i göster
        lines.append("<b>📜 Son sinyaller (>24h):</b>")
        for r in recent[-5:][::-1]:
            ticker = r.get("ticker", "?")
            decision = r.get("decision", "?")
            emoji = DECISION_EMOJI.get(decision, "")
            ts = r.get("recorded_at", "")[:16].replace("T", " ")
            lines.append(f"  {ts} | {emoji} <b>{ticker}</b> → {decision}")
    else:
        lines.append("<i>Henüz sinyal kaydı yok</i>")

    return "\n".join(lines)


def run_scan_now() -> str:
    """
    Manuel tarama tetikle (force_run_now wrapper).
    Sadece özet döner — DM'leri otomatik olarak normal polling cycle gönderir,
    bu komut sadece anlık snapshot verir.
    """
    from .monitor import force_run_now

    wl = load_watchlist()
    tickers = wl.get("combined", []) if wl else []
    if not tickers:
        return "❌ Watchlist boş. Önce <code>/analist watchlist</code> ile durumu kontrol et."

    # Sadece portföy + son 7 günde bilanço açıklayanları tara (hızlı olsun)
    target_tickers = list(set(wl.get("portfolio", []) + wl.get("recent_earnings", [])[:50]))

    if not target_tickers:
        return "❌ Tarama yapılacak ticker yok."

    try:
        result = force_run_now(tickers=target_tickers, hours_back=168)
    except Exception as e:
        return f"❌ Tarama hatası: {e}"

    actionable = result.get("actionable", [])
    all_results = result.get("all", [])

    lines = [
        f"<b>🔍 Manuel Tarama Sonucu</b>",
        "",
        f"<b>Toplam:</b> {result.get('checked', 0)} ticker tarandı",
        f"<b>Aksiyon kararı:</b> {len(actionable)}",
        f"<i>Pencere: son {result.get('window_hours', 168)}h</i>",
        "",
    ]

    if actionable:
        lines.append("<b>📍 Aksiyon kararları:</b>")
        for r in actionable[:15]:
            emoji = DECISION_EMOJI.get(r["decision"], "")
            title = DECISION_TITLE.get(r["decision"], r["decision"])
            raised = r.get("raised_48h", 0)
            lowered = r.get("lowered_48h", 0)
            avg = r.get("avg_pct")
            avg_str = f" avg={avg:+.0f}%" if avg is not None else ""
            lines.append(
                f"  {emoji} <code>{r['ticker']}</code> → <b>{title}</b> "
                f"({raised}↑/{lowered}↓{avg_str})"
            )
            rationale = r.get("rationale", "")[:60]
            if rationale:
                lines.append(f"     <i>{rationale}</i>")

    # Drift expired ama büyük raise olanlar (WATCH özel)
    watch_special = [r for r in all_results
                     if r.get("decision") == "WATCH"
                     and r.get("drift_status") == "expired"
                     and r.get("biggest_raise")
                     and (r["biggest_raise"].get("pct") or 0) >= 30]
    if watch_special:
        lines.append("")
        lines.append("<b>🟡 Drift dışı büyük raise (WATCH):</b>")
        for r in watch_special[:10]:
            br = r["biggest_raise"]
            lines.append(
                f"  <code>{r['ticker']}</code> {br.get('company', '?')} "
                f"+{br.get('pct', 0):.0f}% ({r.get('days_since_earnings', '?')}d)"
            )

    if not actionable and not watch_special:
        lines.append("<i>Bu turda anlamlı aksiyon kararı yok.</i>")

    return "\n".join(lines)


def format_analist_help() -> str:
    """Komut listesi."""
    return """<b>📡 Analist Takip — Komutlar</b>

<b>Sorgu:</b>
<code>/analist TICKER</code> — Tek hissenin anlık analist sinyali
   Örnek: <code>/analist AAOI</code>

<b>İzleme Listesi (Performans):</b>
<code>/analist liste</code> — İzleme listesi + performans tablosu
<code>/analist ekle TICKER [not]</code> — Listeye manuel ekle
   Örnek: <code>/analist ekle CEVA AI chip IP play</code>
<code>/analist sil TICKER</code> — Listeden çıkar

<b>📨 DM Filter:</b>
<code>/analist dm</code> — Mevcut DM ayarlarını göster
<code>/analist dm sadece-al</code> — Sadece BUY/STRONG_BUY DM
<code>/analist dm al-ve-izle</code> — AL + drift dışı büyük raise WATCH
<code>/analist dm sat-da</code> — + SELL/STRONG_SELL DM
<code>/analist dm hepsi</code> — Aksiyon + drift dışı WATCH
<code>/analist dm sadece-guclu</code> — Sadece STRONG_*

<b>Sistem:</b>
<code>/analist watchlist</code> — Sinyal taranan ticker'lar (otomatik)
<code>/analist status</code> — Son 24h sinyaller + sistem durumu
<code>/analist tara</code> — Şimdi manuel polling tara

<i>Sistem BUY/STRONG_BUY ürettiği her hisseyi otomatik listeye ekler.
30 günden eski (manuel olmayan) kayıtlar arşivlenir.</i>"""


def format_performance_watchlist() -> str:
    """
    /analist liste — Performans tablosu.
    """
    from .performance_tracker import get_watchlist_with_performance, get_statistics, cleanup_old

    # Önce eski kayıtları temizle
    cleanup_old()

    perf = get_watchlist_with_performance()
    stats = get_statistics()

    if not perf:
        return ("<b>👀 İzleme Listesi (boş)</b>\n\n"
                "Henüz hisse yok. Sistem BUY/STRONG_BUY ürettiğinde otomatik eklenir.\n"
                "Manuel ekle: <code>/analist ekle TICKER</code>")

    lines = [
        f"<b>👀 İzleme Listesi Performansı</b>",
        f"<i>{stats['total']} hisse, ortalama {stats['avg_performance']:+.1f}%</i>"
        if stats['avg_performance'] is not None
        else f"<i>{stats['total']} hisse</i>",
        "",
    ]

    # Decision'a göre grupla
    by_decision = {}
    for p in perf:
        d = p.get("added_decision", "MANUAL")
        by_decision.setdefault(d, []).append(p)

    decision_order = ["STRONG_BUY", "BUY", "MANUAL", "WATCH", "SELL", "STRONG_SELL"]
    decision_title = {
        "STRONG_BUY": "🟢🟢 GÜÇLÜ AL",
        "BUY": "🟢 AL",
        "MANUAL": "✋ Manuel",
        "WATCH": "🟡 İZLE",
        "SELL": "🔴 SAT",
        "STRONG_SELL": "🔴🔴 GÜÇLÜ SAT",
    }

    for d in decision_order:
        if d not in by_decision:
            continue
        group = by_decision[d]
        lines.append(f"<b>{decision_title.get(d, d)} ({len(group)}):</b>")
        for p in group[:8]:  # Her gruptan max 8
            sym = p["symbol"]
            added_at = p.get("added_at", "")[:10]
            added_p = p.get("added_price")
            current_p = p.get("current_price")
            perf_pct = p.get("performance_pct")
            hold = p.get("hold_days", "?")

            line_parts = [f"<code>{sym}</code>"]
            if added_p and current_p:
                line_parts.append(f"${added_p:.2f}→${current_p:.2f}")
            if perf_pct is not None:
                emoji = "✅" if perf_pct > 1 else ("❌" if perf_pct < -1 else "⏸️")
                line_parts.append(f"<b>{perf_pct:+.1f}%</b> {emoji}")
            line_parts.append(f"<i>{added_at} ({hold}d)</i>")
            lines.append("  " + " ".join(line_parts))
        if len(group) > 8:
            lines.append(f"  <i>... ve {len(group) - 8} tane daha</i>")
        lines.append("")

    # İstatistikler
    lines.append(f"<b>📊 İstatistikler:</b>")
    lines.append(f"  Pozitif: {stats['positive']} | Negatif: {stats['negative']} | Nötr: {stats['neutral']}")
    if stats['hit_rate'] is not None:
        lines.append(f"  İsabet oranı: <b>{stats['hit_rate']}%</b>")

    if stats['best']:
        b = stats['best']
        lines.append(f"  🏆 En iyi: <code>{b['symbol']}</code> {b['performance_pct']:+.1f}%")
    if stats['worst'] and stats['worst'] != stats['best']:
        w = stats['worst']
        lines.append(f"  📉 En kötü: <code>{w['symbol']}</code> {w['performance_pct']:+.1f}%")

    return "\n".join(lines)


def add_ticker_command(arg: str) -> str:
    """
    /analist ekle TICKER [açıklama] komutu.
    """
    from .performance_tracker import add_manual_ticker

    parts = arg.strip().split(maxsplit=1)
    if not parts:
        return "❌ Kullanım: <code>/analist ekle TICKER [açıklama]</code>"

    ticker = parts[0].upper().replace("$", "")
    notes = parts[1] if len(parts) > 1 else ""

    if not (1 <= len(ticker) <= 6):
        return f"❌ Geçersiz ticker: <code>{ticker}</code>"

    result = add_manual_ticker(ticker, notes=notes)
    if not result["added"]:
        return f"⚠️ <code>{ticker}</code> eklenemedi: {result.get('reason', '')}"

    entry = result["entry"]
    price_str = f"${entry['added_price']:.2f}" if entry.get("added_price") else "fiyat alınamadı"
    return (
        f"✅ <code>{ticker}</code> izleme listesine eklendi\n"
        f"  Fiyat: {price_str}\n"
        f"  Not: <i>{notes if notes else 'manuel ekleme'}</i>\n\n"
        f"<i>Performansı görmek için: /analist liste</i>"
    )


def remove_ticker_command(arg: str) -> str:
    """
    /analist sil TICKER komutu.
    """
    from .performance_tracker import remove_from_watchlist

    ticker = arg.strip().upper().replace("$", "")
    if not (1 <= len(ticker) <= 6):
        return f"❌ Geçersiz ticker: <code>{ticker}</code>"

    result = remove_from_watchlist(ticker)
    if not result["removed"]:
        return f"⚠️ <code>{ticker}</code> listede yok"

    entry = result["entry"]
    added_at = entry.get("added_at", "")[:10]
    decision = entry.get("added_decision", "?")
    return (
        f"✅ <code>{ticker}</code> listeden çıkarıldı\n"
        f"  Eklendiği gün: {added_at}\n"
        f"  Kararı: {decision}"
    )
