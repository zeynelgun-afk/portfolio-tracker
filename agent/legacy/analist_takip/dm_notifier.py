"""
Analist Takip — DM Notifier

DM 1403072107'ye HTML-formatlı bildirim. GRUP'a ASLA bir şey gönderilmez.
[DRY-RUN] prefix DRY_RUN modunda.
"""
from __future__ import annotations
import os
import requests
from datetime import datetime
from typing import Optional

from .config import (
    TELEGRAM_DM_CHAT_ID,
    TELEGRAM_BOT_TOKEN_FALLBACK,
    DRY_RUN,
)


def _get_bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN") or TELEGRAM_BOT_TOKEN_FALLBACK


def send_dm(text: str, parse_mode: str = "HTML") -> bool:
    """DM 1403072107'ye gönder. GRUP YASAK."""
    token = _get_bot_token()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_DM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        return r.ok
    except Exception as e:
        print(f"[AnalistTakip] DM send failed: {e}")
        return False


DECISION_EMOJI = {
    "STRONG_BUY":  "🟢🟢",
    "BUY":         "🟢",
    "WATCH":       "🟡",
    "NEUTRAL":     "⚪",
    "SELL":        "🔴",
    "STRONG_SELL": "🔴🔴",
}

DECISION_TITLE = {
    "STRONG_BUY":  "GÜÇLÜ AL",
    "BUY":         "AL",
    "WATCH":       "İZLE",
    "NEUTRAL":     "NÖTR",
    "SELL":        "SAT",
    "STRONG_SELL": "GÜÇLÜ SAT",
}


def _format_evidence_line(e: dict) -> str:
    """Tek bir evidence satırını formatla."""
    company = e.get("company", "?")
    action = e.get("action", "?")
    # Tarih kısalt
    date_str = e.get("date", "")[:10]

    parts = [f"<b>{company}</b>"]

    # Grade değişikliği
    prev = e.get("previous_grade")
    new_g = e.get("new_grade")
    if prev and new_g and prev != new_g:
        parts.append(f"{prev}→{new_g}")
    elif new_g and not prev:
        parts.append(f"initiated {new_g}")

    # Hedef değişikliği
    old = e.get("old_target")
    new = e.get("new_target")
    pct = e.get("change_pct")
    if old and new:
        emoji = "📈" if (pct or 0) > 0 else "📉"
        pct_str = f" ({pct:+.0f}%)" if pct is not None else ""
        parts.append(f"{emoji} ${old:.0f}→${new:.0f}{pct_str}")
    elif new:
        parts.append(f"hedef ${new:.0f}")

    parts.append(f"<i>{date_str}</i>")
    return "  • " + " ".join(parts)


def format_signal_message(
    signal: dict,
    current_price: Optional[float] = None,
    market_cap_b: Optional[float] = None,
    target_consensus: Optional[dict] = None,
) -> str:
    """
    analyze_signals çıktısını DM mesajına çevir.

    Args:
        signal: signal_analyzer çıktısı
        current_price: Mevcut fiyat
        market_cap_b: Market cap (USD billion)
        target_consensus: {'avg', 'high', 'low', 'median', 'num_analysts'}
    """
    prefix = "🧪 <b>[DRY-RUN]</b> " if DRY_RUN else ""
    ticker = signal["ticker"]
    decision = signal["decision"]
    emoji = DECISION_EMOJI.get(decision, "")
    title = DECISION_TITLE.get(decision, decision)
    confidence = signal.get("confidence", "?")

    lines = [
        f"{prefix}{emoji} <b>{title}: {ticker}</b>",
        "",
    ]

    # Mevcut fiyat + mcap
    price_line_parts = []
    if current_price is not None:
        price_line_parts.append(f"💵 ${current_price:.2f}")
    if market_cap_b is not None:
        price_line_parts.append(f"📊 ${market_cap_b:.1f}B mcap")
    if price_line_parts:
        lines.append(" | ".join(price_line_parts))
        lines.append("")

    # Analist hedef özeti (avg/high/low)
    if target_consensus:
        avg = target_consensus.get("avg")
        high = target_consensus.get("high")
        low = target_consensus.get("low")
        num_analysts = target_consensus.get("num_analysts")

        if avg or high or low:
            lines.append(f"<b>🎯 Analist Hedef Aralığı</b>")
            target_parts = []
            if low is not None:
                upside_low = ((low / current_price - 1) * 100) if current_price and current_price > 0 else None
                low_str = f"  Düşük: ${low:.2f}"
                if upside_low is not None:
                    low_str += f" ({upside_low:+.0f}%)"
                target_parts.append(low_str)
            if avg is not None:
                upside_avg = ((avg / current_price - 1) * 100) if current_price and current_price > 0 else None
                avg_str = f"  Ortalama: ${avg:.2f}"
                if upside_avg is not None:
                    avg_str += f" ({upside_avg:+.0f}%)"
                target_parts.append(avg_str)
            if high is not None:
                upside_high = ((high / current_price - 1) * 100) if current_price and current_price > 0 else None
                high_str = f"  Yüksek: ${high:.2f}"
                if upside_high is not None:
                    high_str += f" ({upside_high:+.0f}%)"
                target_parts.append(high_str)
            lines.extend(target_parts)
            if num_analysts:
                lines.append(f"  <i>({num_analysts} analist)</i>")
            lines.append("")

    # Sinyal özeti
    lines.append(f"<b>📊 Analist Hareketi (son 48s)</b>")
    raised = signal.get("raised_count_48h", 0)
    lowered = signal.get("lowered_count_48h", 0)
    raised_24 = signal.get("raised_count_24h", 0)
    lowered_24 = signal.get("lowered_count_24h", 0)
    upgrades = signal.get("upgrades_count", 0)
    downgrades = signal.get("downgrades_count", 0)
    avg_pct = signal.get("avg_revision_pct")

    lines.append(f"  📈 Hedef yükselten: {raised} ({raised_24} son 24s)")
    lines.append(f"  📉 Hedef düşüren: {lowered} ({lowered_24} son 24s)")
    if upgrades:
        lines.append(f"  ⬆️ Upgrade: {upgrades}")
    if downgrades:
        # Downgrade çok önemli - vurgulu göster
        lines.append(f"  🚨 <b>Downgrade: {downgrades}</b>")
    if avg_pct is not None:
        lines.append(f"  Ortalama revize: {avg_pct:+.1f}%")

    # En büyük revize
    biggest_raise = signal.get("biggest_raise")
    biggest_cut = signal.get("biggest_cut")
    if biggest_raise:
        lines.append("")
        lines.append(f"<b>🚀 En büyük yükseliş:</b>")
        lines.append(f"  {biggest_raise['company']}: "
                     f"${biggest_raise.get('old', '?'):.0f}→${biggest_raise.get('new', '?'):.0f} "
                     f"({biggest_raise['pct']:+.0f}%)")
    if biggest_cut:
        lines.append("")
        lines.append(f"<b>⚠️ En büyük düşüş:</b>")
        lines.append(f"  {biggest_cut['company']}: "
                     f"${biggest_cut.get('old', '?'):.0f}→${biggest_cut.get('new', '?'):.0f} "
                     f"({biggest_cut['pct']:+.0f}%)")

    # Evidence (son 3-5 hareket)
    evidence = signal.get("evidence", [])
    if evidence:
        lines.append("")
        lines.append(f"<b>📰 Son hareketler:</b>")
        for e in evidence[:5]:
            lines.append(_format_evidence_line(e))

    # === Price-Target Gap Gate bilgisi (15 May 2026) ===
    gap_quality = signal.get("gap_quality")
    upside_avg = signal.get("upside_avg_pct")
    upside_max = signal.get("upside_max_pct")
    risk_reward = signal.get("risk_reward")
    gate_applied = signal.get("gate_applied", False)
    original_decision = signal.get("original_decision")

    if gap_quality and gap_quality != "UNKNOWN":
        lines.append("")
        gap_emoji = {
            "STRONG": "🟢",
            "MEDIUM": "🟡",
            "WATCH": "🟠",
            "SKIP": "🔴",
        }.get(gap_quality, "")
        lines.append(f"<b>📐 Fiyat-Hedef Boşluğu: {gap_emoji} {gap_quality}</b>")
        gap_parts = []
        if upside_avg is not None:
            gap_parts.append(f"  Avg upside: {upside_avg:+.1f}%")
        if upside_max is not None:
            gap_parts.append(f"  Max upside: {upside_max:+.1f}%")
        if risk_reward is not None:
            gap_parts.append(f"  R/R: {risk_reward:.2f}")
        lines.extend(gap_parts)

        if gate_applied and original_decision:
            orig_title = DECISION_TITLE.get(original_decision, original_decision)
            new_title = DECISION_TITLE.get(decision, decision)
            lines.append(f"  ⚠️ <i>{orig_title} → {new_title}'a düşürüldü</i>")

    # Karar + rationale
    lines.append("")
    lines.append(f"<b>► KARAR: {title} ({confidence})</b>")
    lines.append(f"<i>{signal.get('rationale', '')}</i>")

    return "\n".join(lines)


def notify_signal(
    signal: dict,
    current_price: Optional[float] = None,
    market_cap_b: Optional[float] = None,
    target_consensus: Optional[dict] = None,
) -> bool:
    """Sinyal DM bildirimi gönder."""
    msg = format_signal_message(
        signal,
        current_price=current_price,
        market_cap_b=market_cap_b,
        target_consensus=target_consensus,
    )
    return send_dm(msg)


def notify_status(message: str, level: str = "INFO") -> bool:
    """Sistem durumu mesajı."""
    emoji = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "🔴", "SUCCESS": "✅"}.get(level, "")
    prefix = "🧪 [DRY-RUN] " if DRY_RUN else ""
    msg = f"{prefix}{emoji} <b>[AnalistTakip]</b> {message}"
    return send_dm(msg)
