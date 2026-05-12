"""
Bilanço Müdürü — DM Notifier

Sadece DM 1403072107'ye gönderir. GRUP'a ASLA bir şey gönderilmez (memory satır 9).

Mesaj türleri:
1. Bilanço aksiyon raporu (decision: AL/İZLE/GEÇ)
2. Sistem hata/uyarı
3. Pipeline durum (snapshot kayıt, catchup özet)
"""
from __future__ import annotations
import os
import requests
from typing import Optional

from .config import (
    TELEGRAM_DM_CHAT_ID,
    TELEGRAM_BOT_TOKEN_ENV,
    TELEGRAM_BOT_TOKEN_FALLBACK,
    DRY_RUN,
)


def _get_bot_token() -> str:
    return os.environ.get(TELEGRAM_BOT_TOKEN_ENV) or TELEGRAM_BOT_TOKEN_FALLBACK


def send_dm(text: str, parse_mode: str = "HTML") -> bool:
    """
    Zeynel'in DM'ine mesaj gönderir.
    GRUP'a göndermek için bu fonksiyon KULLANILAMAZ.
    """
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
        # Logla ama crashleme
        print(f"[BilancoMuduru] DM send failed: {e}")
        return False


def format_decision_message(
    ticker: str,
    fiscal_period: str,
    parse_result,
    valuation: dict,
    snapshot_used: dict,
) -> str:
    """
    Bilanço gecesi karar mesajını formatlar.
    """
    prefix = "🧪 <b>[DRY-RUN]</b> " if DRY_RUN else ""
    decision = valuation.get("decision", "?")
    decision_emoji = {"AL": "🟢", "İZLE": "🟡", "GEÇ": "🔴", "VERİ YETERSİZ": "⚪"}.get(decision, "⚪")

    ra = parse_result.results_actual
    qs = parse_result.qualitative_signals
    new_targets = valuation.get("new_targets", {})
    upside = valuation.get("upside_pct", {})
    revision = valuation.get("multiple_revision", {})

    revenue_str = f"${ra.revenue_usd_b:.2f}B" if ra.revenue_usd_b else "?"
    yoy_str = f"+{ra.yoy_revenue_growth_pct:.0f}%" if ra.yoy_revenue_growth_pct else "?"
    eps_str = (
        f"${ra.non_gaap_eps:.2f}" if ra.non_gaap_eps
        else f"${ra.gaap_eps:.2f} (GAAP)" if ra.gaap_eps
        else "?"
    )

    target_avg = new_targets.get("target_avg")
    target_high = new_targets.get("target_high")
    upside_avg = upside.get("avg")
    upside_high = upside.get("high")
    current_price = valuation.get("current_price")

    target_str = f"${target_avg:.2f}" if target_avg else "?"
    target_high_str = f"${target_high:.2f}" if target_high else "?"
    upside_str = f"({upside_avg:+.1f}%)" if upside_avg is not None else ""
    upside_high_str = f"({upside_high:+.1f}%)" if upside_high is not None else ""

    revision_str = ""
    if revision and revision.get("revision_pct"):
        revision_str = f"\n  Çarpan revize: {revision['revision_pct']:+.0%} → {revision['rationale']}"

    forward_inputs = valuation.get("forward_inputs", {})
    fwd_src = forward_inputs.get("forward_eps_source", "?")

    lines = [
        f"{prefix}{decision_emoji} <b>BİLANÇO GECESİ: {ticker} {fiscal_period}</b>",
        "",
        f"📊 <b>Sonuçlar</b>",
        f"  Gelir: {revenue_str} ({yoy_str} YoY)",
        f"  EPS: {eps_str}",
    ]

    if ra.gross_margin_pct:
        lines.append(f"  Brüt marj: {ra.gross_margin_pct:.1f}%")
    if ra.operating_margin_pct:
        lines.append(f"  Faaliyet marjı: {ra.operating_margin_pct:.1f}%")

    # Guidance varsa göster
    gq = parse_result.guidance_next_quarter
    gfy = parse_result.guidance_full_year
    if gq.provided and gq.revenue_mid_b:
        lines.append("")
        lines.append(f"🎯 <b>Guidance (Sonraki Çeyrek)</b>")
        lines.append(f"  Gelir: ${gq.revenue_mid_b:.1f}B")
        if gq.revenue_low_b and gq.revenue_high_b:
            lines.append(f"    Aralık: ${gq.revenue_low_b:.1f}B - ${gq.revenue_high_b:.1f}B")
    elif not gq.provided and not gfy.provided:
        lines.append("")
        lines.append(f"⚠️ <b>Şirket guidance vermedi</b> (fallback: {fwd_src})")

    # Hedef fiyatlar
    lines.append("")
    lines.append(f"💰 <b>İmpli Hedef Fiyatlar</b>")
    lines.append(f"  Mevcut: ${current_price:.2f}" if current_price else "  Mevcut: ?")
    lines.append(f"  Ortalama: {target_str} {upside_str}")
    lines.append(f"  Yüksek: {target_high_str} {upside_high_str}")
    if revision_str:
        lines.append(revision_str.strip())

    # Karar
    lines.append("")
    lines.append(f"<b>► KARAR: {decision}</b>")
    if qs.tone_score:
        tone_emoji = "🚀" if qs.tone_score >= 4 else "📈" if qs.tone_score >= 1 else "⚠️" if qs.tone_score <= -1 else "➖"
        lines.append(f"  Ton skoru: {qs.tone_score:+d}/5 {tone_emoji} ({qs.tone_label})")

    # Warning phrases
    if qs.warning_phrases:
        lines.append("")
        lines.append(f"⚠️ <b>Uyarı sinyalleri</b>")
        for w in qs.warning_phrases[:3]:
            lines.append(f"  • {w[:100]}")

    # Ambiguous methodology change
    method_change = next(
        (ai for ai in parse_result.ambiguous_items if "methodology" in ai.field.lower()),
        None
    )
    if method_change:
        lines.append("")
        lines.append(f"🚨 <b>Muhasebe değişikliği</b>")
        lines.append(f"  {method_change.explanation[:200]}")

    return "\n".join(lines)


def format_pipeline_status(message: str, level: str = "INFO") -> str:
    """Sistem durumu mesajı (snapshot kayıt, catchup özet, hata)."""
    emoji = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "🔴", "SUCCESS": "✅"}.get(level, "")
    prefix = "🧪 [DRY-RUN] " if DRY_RUN else ""
    return f"{prefix}{emoji} <b>[BilançoMüdürü]</b> {message}"


def notify_decision(
    ticker: str,
    fiscal_period: str,
    parse_result,
    valuation: dict,
    snapshot_used: dict,
) -> bool:
    """Bilanço gecesi karar mesajını DM'e gönderir."""
    msg = format_decision_message(ticker, fiscal_period, parse_result, valuation, snapshot_used)
    return send_dm(msg)


def notify_status(message: str, level: str = "INFO") -> bool:
    """Sistem durumunu DM'e bildir."""
    msg = format_pipeline_status(message, level)
    return send_dm(msg)
