"""
Analist Takip — Signal Analyzer

Toplanan revizyonlardan kararlar üretir:
  STRONG_BUY / BUY / WATCH / SELL / STRONG_SELL / NEUTRAL
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

from datetime import date as _date_type

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
    POST_EARNINGS_WATCH_DAYS,
)


# Post-earnings drift penceresi: bilanço sonrası kaç gün anlamlı revizyonlar
DRIFT_WINDOW_DAYS = 14


def analyze_signals(
    ticker: str,
    signals: list[dict],
    now: Optional[datetime] = None,
    window_hours: Optional[int] = None,
    last_earnings_date: Optional[_date_type] = None,
    require_post_earnings: bool = True,
) -> dict:
    """
    Toplanan revizyon listesinden karar üretir.

    Args:
        ticker: Hisse sembolü
        signals: fetch_all_signals'dan dönen liste
        now: Şu an (test için override)
        window_hours: Pencere genişliği (None ise config default)
        last_earnings_date: Son tamamlanmış bilanço tarihi
        require_post_earnings: True ise, sadece bilanço sonrası revizyonlar sayılır
                              ve >14 gün geçmişse NEUTRAL döner

    Returns:
        {decision, confidence, raised_count_48h, lowered_count_48h, ...}
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    total_window = window_hours if window_hours is not None else SIGNAL_WINDOW_TOTAL_HOURS
    recent_window = max(SIGNAL_WINDOW_RECENT_HOURS, total_window // 2)

    cutoff_total = now - timedelta(hours=total_window)
    cutoff_recent = now - timedelta(hours=recent_window)

    # === BİLANÇO CUTOFF MANTIĞI ===
    # Eğer last_earnings_date varsa:
    # 1. Pre-earnings revizyonları sayma (bilanço beklentilerine yönelik, sinyal değil)
    # 2. Bilançodan >14 gün geçmişse drift penceresi bitti → NEUTRAL
    earnings_cutoff = None
    drift_status = None  # "active" | "expired" | "no_recent_earnings"
    days_since_earnings = None

    if require_post_earnings and last_earnings_date:
        earnings_cutoff = datetime.combine(
            last_earnings_date,
            datetime.min.time(),
        ).replace(tzinfo=timezone.utc)
        days_since_earnings = (now.date() - last_earnings_date).days
        if days_since_earnings > DRIFT_WINDOW_DAYS:
            drift_status = "expired"
        else:
            drift_status = "active"

        # cutoff_total'ı bilanço tarihinden geri gitmeyecek şekilde ayarla
        if cutoff_total < earnings_cutoff:
            cutoff_total = earnings_cutoff
    elif require_post_earnings and not last_earnings_date:
        drift_status = "no_recent_earnings"

    # Eğer drift penceresi geçmişse → çoğunlukla NEUTRAL,
    # AMA: tek büyük raise (>%30) varsa WATCH üret (kaçırma riski azalt)
    if drift_status == "expired":
        # Pre-check: drift dışında olsa bile büyük raise var mı?
        # Bunu bulmak için tüm signals'a (cutoff_total override öncesi) bak
        big_raise_drift_expired = None
        for s in signals:
            if s["published_at"] < earnings_cutoff:
                continue  # bilanço öncesi hariç
            pct = s.get("change_pct")
            if pct is not None and pct >= 30.0:
                # Bu büyüklükte raise drift dışında bile dikkat çekici
                if big_raise_drift_expired is None or pct > big_raise_drift_expired["pct"]:
                    big_raise_drift_expired = {
                        "company": s.get("analyst_company") or s.get("grading_company"),
                        "pct": round(pct, 1),
                        "old": s.get("old_target"),
                        "new": s.get("new_target") or s.get("price_target"),
                        "date": s["published_at"].isoformat(),
                    }

        if big_raise_drift_expired:
            return {
                "ticker": ticker,
                "decision": "WATCH",
                "confidence": "low",
                "raised_count_48h": 1,
                "lowered_count_48h": 0,
                "raised_count_24h": 0,
                "lowered_count_24h": 0,
                "upgrades_count": 0,
                "downgrades_count": 0,
                "downgrades_count_24h": 0,
                "avg_revision_pct": big_raise_drift_expired["pct"],
                "biggest_raise": big_raise_drift_expired,
                "biggest_cut": None,
                "rationale": (
                    f"Drift penceresi geçmiş ({days_since_earnings}d) "
                    f"AMA {big_raise_drift_expired['company']} büyük raise "
                    f"(+{big_raise_drift_expired['pct']:.0f}%) → izle"
                ),
                "evidence": [{
                    "date": big_raise_drift_expired["date"],
                    "company": big_raise_drift_expired["company"],
                    "action": "raised",
                    "old_target": big_raise_drift_expired["old"],
                    "new_target": big_raise_drift_expired["new"],
                    "change_pct": big_raise_drift_expired["pct"],
                }],
                "total_signals_in_window": 1,
                "analyzed_at": now.isoformat(),
                "drift_status": drift_status,
                "days_since_earnings": days_since_earnings,
                "last_earnings_date": last_earnings_date.isoformat() if last_earnings_date else None,
            }

        # Büyük raise yoksa NEUTRAL
        return {
            "ticker": ticker,
            "decision": "NEUTRAL",
            "confidence": "low",
            "raised_count_48h": 0,
            "lowered_count_48h": 0,
            "raised_count_24h": 0,
            "lowered_count_24h": 0,
            "upgrades_count": 0,
            "downgrades_count": 0,
            "downgrades_count_24h": 0,
            "avg_revision_pct": None,
            "biggest_raise": None,
            "biggest_cut": None,
            "rationale": (
                f"Post-earnings drift penceresi geçmiş "
                f"(son bilanço {days_since_earnings}d önce, >{DRIFT_WINDOW_DAYS}d eşik)"
            ),
            "evidence": [],
            "total_signals_in_window": 0,
            "analyzed_at": now.isoformat(),
            "drift_status": drift_status,
            "days_since_earnings": days_since_earnings,
            "last_earnings_date": last_earnings_date.isoformat() if last_earnings_date else None,
        }

    # Pencere içindeki sinyalleri filtrele
    in_window = [s for s in signals if s["published_at"] >= cutoff_total]

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

    # VETO kuralları:
    # - 2+ downgrade veto eder (çoğunluk şart). 1 downgrade tolere edilir.
    # - Net pozitif sinyal varsa AL üretilebilir
    multi_downgrade_veto = len(downgrades) >= 2
    has_recent_downgrade = len(downgrades) > 0
    has_recent_upgrade = len(upgrades) > 0
    has_mixed_signals = (raised and lowered) or (upgrades and downgrades)
    # Net pozitif sinyal: raise sayısı ≥ (lowered + downgrades) + 1
    net_signal_positive = len(raised) - len(lowered) - len(downgrades) >= 1

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

    # VETO: 2+ downgrade varsa AL kararları YASAK
    elif multi_downgrade_veto:
        decision = "WATCH"
        confidence = "low"
        rationale_parts.append(f"KARIŞIK: {len(raised)} raise + {len(downgrades)} downgrade")
        rationale_parts.append("AL veto: 2+ downgrade")

    # STRONG_BUY kontrolü (1 downgrade'i tolere et ama avg ve count daha sıkı)
    elif (len(raised) >= STRONG_BUY_MIN_RAISED
            and (avg_revision_pct or 0) >= STRONG_BUY_MIN_AVG_PCT
            and len(lowered) <= STRONG_BUY_MAX_LOWERED
            and len(downgrades) == 0):  # STRONG_BUY için 0 downgrade şart
        decision = "STRONG_BUY"
        confidence = "high"
        rationale_parts.append(f"{len(raised)} analist hedef yükseltti")
        rationale_parts.append(f"avg revize +{avg_revision_pct}%")
        rationale_parts.append("0 düşüş, 0 downgrade")

    # BUY kontrolü — Bu blok'a giriyorsak zaten:
    #   • Büyük raise (>%25) VAR, VEYA
    #   • Net raised ≥ 2 VAR
    # 2+ downgrade yukarıda zaten veto etti → buradayız demek 1 veya 0 downgrade.
    # Bu durumda 1 downgrade tolere edilir (çoğunluk pozitif).
    elif ((biggest_raise and biggest_raise["pct"] >= BUY_BIG_RAISE_PCT) or
          len(raised) >= BUY_MIN_NET_RAISED):
        decision = "BUY"
        confidence = "medium" if len(raised) >= BUY_MIN_NET_RAISED else "high"
        if biggest_raise and biggest_raise["pct"] >= BUY_BIG_RAISE_PCT:
            rationale_parts.append(
                f"{biggest_raise['company']} büyük raise (+{biggest_raise['pct']:.0f}%)"
            )
        if len(raised) >= BUY_MIN_NET_RAISED:
            rationale_parts.append(f"{len(raised)} analist yükseltti")
        if has_recent_downgrade:
            rationale_parts.append(f"({len(downgrades)} downgrade tolere edildi)")

    # WATCH (karışık veya tek hafif hareket)
    elif raised or lowered or upgrades or downgrades:
        decision = "WATCH"
        confidence = "low"
        if has_mixed_signals or has_recent_downgrade:
            rationale_parts.append(f"KARIŞIK: {len(raised)}↑ / {len(lowered)}↓")
            if downgrades:
                rationale_parts.append(f"{len(downgrades)} downgrade")
            if upgrades:
                rationale_parts.append(f"{len(upgrades)} upgrade")
        else:
            rationale_parts.append(f"{len(raised)}↑ / {len(lowered)}↓ — eşik altı")

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
        "drift_status": drift_status,
        "days_since_earnings": days_since_earnings,
        "last_earnings_date": last_earnings_date.isoformat() if last_earnings_date else None,
    }
