"""
Analist Takip — Signal Analyzer

Toplanan revizyonlardan kararlar üretir:
  STRONG_BUY / BUY / WATCH / SELL / STRONG_SELL / NEUTRAL
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import (
    SIGNAL_WINDOW_RECENT_HOURS,
    SIGNAL_WINDOW_TOTAL_HOURS,
    STRONG_BUY_MIN_RAISED,
    STRONG_BUY_MIN_AVG_PCT,
    STRONG_BUY_MAX_LOWERED,
    BUY_BIG_RAISE_PCT,
    BUY_MIN_NET_RAISED,
    SELL_MIN_LOWERED,
    SELL_BIG_CUT_PCT,
    STRONG_SELL_MIN_LOWERED,
    STRONG_SELL_DOWNGRADE_REQUIRED,
)


def analyze_signals(
    ticker: str,
    signals: list[dict],
    now: Optional[datetime] = None,
    window_hours: Optional[int] = None,
) -> dict:
    """
    Toplanan revizyon listesinden karar üretir.

    Args:
        ticker: Hisse sembolü
        signals: fetch_all_signals'dan dönen liste
        now: Şu an (test için override)
        window_hours: Pencere genişliği (None ise config default SIGNAL_WINDOW_TOTAL_HOURS)

    Returns:
        {decision, confidence, raised_count_48h, lowered_count_48h, ...}
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    total_window = window_hours if window_hours is not None else SIGNAL_WINDOW_TOTAL_HOURS
    # Recent pencere: total / 2 (örn 48h total → 24h recent)
    recent_window = max(SIGNAL_WINDOW_RECENT_HOURS, total_window // 2)

    cutoff_total = now - timedelta(hours=total_window)
    cutoff_recent = now - timedelta(hours=recent_window)

    # Pencere içindeki sinyalleri filtrele
    in_window = [s for s in signals if s["published_at"] >= cutoff_total]

    # Hedef revizyonları (raised / lowered)
    raised = []
    lowered = []
    upgrades = []
    downgrades = []
    initiations = []

    for s in in_window:
        direction = s.get("direction") or s.get("action", "")
        change_pct = s.get("change_pct")

        # Hedef değişikliği
        if direction == "raised" or change_pct is not None and change_pct > 1:
            raised.append(s)
        elif direction == "lowered" or change_pct is not None and change_pct < -1:
            lowered.append(s)

        # Grade değişikliği
        if direction == "upgrade" or s.get("action") == "upgrade":
            upgrades.append(s)
        elif direction == "downgrade" or s.get("action") == "downgrade":
            downgrades.append(s)
        elif s.get("action") == "initiate" or direction == "initiated":
            initiations.append(s)

    # Son 24h ayrı say
    raised_24h = [s for s in raised if s["published_at"] >= cutoff_recent]
    lowered_24h = [s for s in lowered if s["published_at"] >= cutoff_recent]
    downgrades_24h = [s for s in downgrades if s["published_at"] >= cutoff_recent]

    # Ortalama revize %
    pcts = [s["change_pct"] for s in raised + lowered if s.get("change_pct") is not None]
    avg_revision_pct = round(sum(pcts) / len(pcts), 2) if pcts else None

    # En büyük revize
    biggest_raise = None
    if raised:
        valid_raises = [r for r in raised if r.get("change_pct") is not None]
        if valid_raises:
            biggest = max(valid_raises, key=lambda x: x["change_pct"])
            biggest_raise = {
                "company": biggest.get("analyst_company") or biggest.get("grading_company"),
                "pct": round(biggest["change_pct"], 1),
                "old": biggest.get("old_target"),
                "new": biggest.get("new_target") or biggest.get("price_target"),
                "date": biggest["published_at"].isoformat(),
            }

    biggest_cut = None
    if lowered:
        valid_cuts = [r for r in lowered if r.get("change_pct") is not None]
        if valid_cuts:
            worst = min(valid_cuts, key=lambda x: x["change_pct"])
            biggest_cut = {
                "company": worst.get("analyst_company") or worst.get("grading_company"),
                "pct": round(worst["change_pct"], 1),
                "old": worst.get("old_target"),
                "new": worst.get("new_target") or worst.get("price_target"),
                "date": worst["published_at"].isoformat(),
            }

    # === KARAR MANTIĞI ===
    decision = "NEUTRAL"
    rationale_parts = []
    evidence = []
    confidence = "low"

    # STRONG_SELL kontrolü (öncelik)
    if (len(lowered) >= STRONG_SELL_MIN_LOWERED
            and (downgrades or not STRONG_SELL_DOWNGRADE_REQUIRED)):
        decision = "STRONG_SELL"
        confidence = "high"
        rationale_parts.append(f"{len(lowered)} analist hedef düşürdü")
        if downgrades:
            rationale_parts.append(f"{len(downgrades)} downgrade")

    elif len(lowered) >= SELL_MIN_LOWERED or (
            biggest_cut and biggest_cut["pct"] <= SELL_BIG_CUT_PCT):
        decision = "SELL"
        confidence = "medium"
        if len(lowered) >= SELL_MIN_LOWERED:
            rationale_parts.append(f"{len(lowered)} analist hedef düşürdü")
        if biggest_cut and biggest_cut["pct"] <= SELL_BIG_CUT_PCT:
            rationale_parts.append(f"{biggest_cut['company']} büyük cut ({biggest_cut['pct']:.1f}%)")

    # STRONG_BUY kontrolü
    elif (len(raised) >= STRONG_BUY_MIN_RAISED
            and (avg_revision_pct or 0) >= STRONG_BUY_MIN_AVG_PCT
            and len(lowered) <= STRONG_BUY_MAX_LOWERED):
        decision = "STRONG_BUY"
        confidence = "high"
        rationale_parts.append(f"{len(raised)} analist hedef yükseltti")
        rationale_parts.append(f"avg revize +{avg_revision_pct}%")
        rationale_parts.append("0 düşüş")

    # BUY kontrolü
    elif (biggest_raise and biggest_raise["pct"] >= BUY_BIG_RAISE_PCT) or \
         len(raised) >= BUY_MIN_NET_RAISED:
        decision = "BUY"
        confidence = "medium" if len(raised) >= BUY_MIN_NET_RAISED else "high"
        if biggest_raise and biggest_raise["pct"] >= BUY_BIG_RAISE_PCT:
            rationale_parts.append(
                f"{biggest_raise['company']} büyük raise (+{biggest_raise['pct']:.0f}%)"
            )
        if len(raised) >= BUY_MIN_NET_RAISED:
            rationale_parts.append(f"{len(raised)} analist yükseltti")

    # WATCH (karışık)
    elif raised or lowered or upgrades or downgrades:
        decision = "WATCH"
        confidence = "low"
        rationale_parts.append(f"{len(raised)}↑ / {len(lowered)}↓ — karışık")

    # Upgrade/downgrade'i decision'a güçlendir
    if upgrades and decision in ("BUY", "STRONG_BUY", "WATCH"):
        rationale_parts.append(f"+{len(upgrades)} upgrade")
    if downgrades and decision in ("SELL", "STRONG_SELL", "WATCH"):
        rationale_parts.append(f"+{len(downgrades)} downgrade")

    rationale = " | ".join(rationale_parts) if rationale_parts else "Sinyal yok"

    # Evidence (DM mesajına yazılacak)
    for s in sorted(raised + lowered + upgrades + downgrades,
                    key=lambda x: x["published_at"], reverse=True)[:5]:
        evidence.append({
            "date": s["published_at"].isoformat(),
            "company": s.get("analyst_company") or s.get("grading_company"),
            "action": s.get("direction") or s.get("action"),
            "old_target": s.get("old_target"),
            "new_target": s.get("new_target") or s.get("price_target"),
            "change_pct": s.get("change_pct"),
            "previous_grade": s.get("previous_grade"),
            "new_grade": s.get("new_grade"),
            "title": s.get("title") or s.get("news_title"),
        })

    return {
        "ticker": ticker,
        "decision": decision,
        "confidence": confidence,
        "raised_count_48h": len(raised),
        "lowered_count_48h": len(lowered),
        "raised_count_24h": len(raised_24h),
        "lowered_count_24h": len(lowered_24h),
        "upgrades_count": len(upgrades),
        "downgrades_count": len(downgrades),
        "downgrades_count_24h": len(downgrades_24h),
        "avg_revision_pct": avg_revision_pct,
        "biggest_raise": biggest_raise,
        "biggest_cut": biggest_cut,
        "rationale": rationale,
        "evidence": evidence,
        "total_signals_in_window": len(in_window),
        "analyzed_at": now.isoformat(),
    }
