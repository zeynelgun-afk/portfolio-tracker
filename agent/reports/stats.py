#!/usr/bin/env python3
"""
Finzora Stats — Observability Raporu
=====================================
Kullanım:
  python scripts/finzora_stats.py                  # son 7 gün özet
  python scripts/finzora_stats.py --days 30        # son 30 gün
  python scripts/finzora_stats.py --today          # bugün
  python scripts/finzora_stats.py --telegram       # Telegram'a gönder
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# agent/ modüllerine ulaş
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "agent"))

try:
    from observability import (
        query_claude_cost,
        query_fmp_stats,
        query_decision_hitrate,
        DB_PATH,
    )
except ImportError as e:
    print(f"ERROR: observability modülü yüklenemedi: {e}")
    sys.exit(1)


# ─────────────────────── Polymarket Kalibratör İstatistikleri ───────────────────
# Faz 2 Adım 13 (17 May 2026). Tracker JSON'dan event analizi.
# Faz 2 C-2 (17 May 2026). Hit rate hesaplama.

_CALIBRATOR_LOG_PATH = _REPO_ROOT / "data" / "polymarket_calibrator_performance.json"

# Hit rate hesaplaması için outcome eşiği (0 default).
# pm_confirm: outcome > _HIT_THRESHOLD → HIT
# pm_conflict: outcome < -_HIT_THRESHOLD → HIT
_HIT_THRESHOLD = 0.0

# Hangi horizon'lar hesaplanır
_OUTCOME_FIELDS = ["outcome_7d", "outcome_14d", "outcome_30d"]


def _is_hit(flag: str, outcome: Optional[float]) -> Optional[bool]:
    """Event'in hit/miss durumunu belirle.

    Args:
        flag: applied_flag (pm_confirm / pm_confirm_weak /
                            pm_conflict / pm_conflict_weak)
        outcome: outcome_Nd değeri (None ise henüz dolu değil)

    Returns:
        True (HIT), False (MISS), None (outcome dolu değil veya
        bilinmeyen flag).

    Semantik:
        pm_confirm*  : Polymarket DESTEKLEDİ → hisse YÜKSELMELİ
                       outcome > 0 → HIT, outcome <= 0 → MISS
        pm_conflict* : Polymarket ÇELİŞTİ → hisse DÜŞMELİ
                       outcome < 0 → HIT, outcome >= 0 → MISS
    """
    if outcome is None or not isinstance(outcome, (int, float)):
        return None
    if not isinstance(flag, str):
        return None

    if flag.startswith("pm_confirm"):
        return outcome > _HIT_THRESHOLD
    if flag.startswith("pm_conflict"):
        return outcome < -_HIT_THRESHOLD
    return None


def _calc_hit_rates(events: list[dict]) -> dict:
    """Per-flag × per-horizon hit rate'leri hesapla.

    Returns:
        {
          "by_flag_horizon": {
            "pm_confirm": {
              "outcome_7d": {"hits": N, "total": N, "rate_pct": N},
              "outcome_14d": {...},
              "outcome_30d": {...},
            },
            "pm_conflict": {...},
            ...
          },
          "by_source": {
            "thematic": {
              "outcome_7d": {"hits": N, "total": N, "rate_pct": N},
              ...
            },
            "fair_value": {...},
            ...
          },
          "by_theme": {
            "china_taiwan": {
              "outcome_7d": {...},
              ...
            },
            ...
          },
          "overall": {
            "outcome_7d": {"hits": N, "total": N, "rate_pct": N},
            "outcome_14d": {...},
            "outcome_30d": {...},
          },
        }

    Total = outcome dolu olan event sayısı (None olanlar dahil değil).
    rate_pct = None eğer total=0.
    """
    by_flag_horizon: dict[str, dict[str, dict]] = {}
    by_source: dict[str, dict[str, dict]] = {}
    by_theme: dict[str, dict[str, dict]] = {}
    overall: dict[str, dict] = {h: {"hits": 0, "total": 0} for h in _OUTCOME_FIELDS}

    def _ensure(d: dict, key: str) -> dict:
        if key not in d:
            d[key] = {h: {"hits": 0, "total": 0} for h in _OUTCOME_FIELDS}
        return d[key]

    for e in events:
        if not isinstance(e, dict):
            continue
        flag = e.get("applied_flag")
        source = e.get("candidate_source")
        theme = e.get("matched_theme")

        for h in _OUTCOME_FIELDS:
            outcome = e.get(h)
            hit = _is_hit(flag, outcome)
            if hit is None:
                continue  # outcome dolu değil veya bilinmeyen flag

            # Overall
            overall[h]["total"] += 1
            if hit:
                overall[h]["hits"] += 1

            # Per-flag
            if isinstance(flag, str):
                flag_bucket = _ensure(by_flag_horizon, flag)
                flag_bucket[h]["total"] += 1
                if hit:
                    flag_bucket[h]["hits"] += 1

            # Per-source
            if isinstance(source, str):
                src_bucket = _ensure(by_source, source)
                src_bucket[h]["total"] += 1
                if hit:
                    src_bucket[h]["hits"] += 1

            # Per-theme
            if isinstance(theme, str):
                theme_bucket = _ensure(by_theme, theme)
                theme_bucket[h]["total"] += 1
                if hit:
                    theme_bucket[h]["hits"] += 1

    # rate_pct ekle
    def _add_rate(buckets: dict) -> None:
        for key, horizons in buckets.items():
            for h, stats in horizons.items():
                total = stats["total"]
                if total > 0:
                    stats["rate_pct"] = round(stats["hits"] / total * 100, 1)
                else:
                    stats["rate_pct"] = None

    _add_rate(by_flag_horizon)
    _add_rate(by_source)
    _add_rate(by_theme)
    # Overall (flat dict)
    for h in _OUTCOME_FIELDS:
        total = overall[h]["total"]
        if total > 0:
            overall[h]["rate_pct"] = round(overall[h]["hits"] / total * 100, 1)
        else:
            overall[h]["rate_pct"] = None

    return {
        "by_flag_horizon": by_flag_horizon,
        "by_source": by_source,
        "by_theme": by_theme,
        "overall": overall,
    }


def _load_calibrator_tracker() -> dict:
    """Tracker dosyasını yükle. Dosya yoksa boş dict, bozuksa {}."""
    if not _CALIBRATOR_LOG_PATH.exists():
        return {}
    try:
        with _CALIBRATOR_LOG_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def query_calibrator_stats(days: int) -> dict:
    """Son `days` günkü kalibratör event'lerinin istatistiklerini çıkar.

    Returns:
        {
          "total_events": N,
          "by_flag": {"pm_confirm": N, "pm_confirm_weak": N, ...},
          "by_multiplier": {"1.20x": N, "1.10x": N, "0.90x": N, "0.75x": N},
          "by_source": {"thematic": N, "fair_value": N},
          "top_themes": [(theme, count), ...],
          "top_symbols": [(symbol, count), ...],
          "days_collected": float,  # tracker _started_at'ten itibaren
          "phase10_progress_pct": float,  # 0-100, 30 gün hedef
          "outcome_status": "pending_phase10",  # outcome_*_d hâlâ None
          "error": opsiyonel str,
        }
    """
    tracker = _load_calibrator_tracker()
    if not tracker:
        return {"error": "Tracker dosyası yok veya bozuk", "total_events": 0}

    events = tracker.get("events", [])
    if not isinstance(events, list):
        return {"error": "Events alanı geçersiz", "total_events": 0}

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Filtreleme — son `days` günü
    recent = []
    for evt in events:
        if not isinstance(evt, dict):
            continue
        ts_str = evt.get("ts", "")
        if not isinstance(ts_str, str):
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts >= cutoff:
                recent.append(evt)
        except (ValueError, TypeError):
            continue

    if not recent:
        return {
            "total_events": 0,
            "by_flag": {},
            "by_multiplier": {},
            "by_source": {},
            "top_themes": [],
            "top_symbols": [],
            "days_collected": _calc_days_collected(tracker, now),
            "phase10_progress_pct": _calc_phase10_progress(tracker, now),
            "outcome_status": "no_data",
            "hit_rates": None,
            "adaptive_suggestions": [],
        }

    # Flag dağılımı
    by_flag: dict[str, int] = {}
    for e in recent:
        flag = e.get("applied_flag", "unknown")
        if isinstance(flag, str):
            by_flag[flag] = by_flag.get(flag, 0) + 1

    # Multiplier dağılımı (1.20 / 1.10 / 0.90 / 0.75)
    by_multiplier: dict[str, int] = {}
    for e in recent:
        mult = e.get("applied_multiplier")
        if isinstance(mult, (int, float)):
            key = f"{mult:.2f}x"
            by_multiplier[key] = by_multiplier.get(key, 0) + 1

    # Source dağılımı (thematic/fair_value)
    by_source: dict[str, int] = {}
    for e in recent:
        src = e.get("candidate_source", "unknown")
        if isinstance(src, str):
            by_source[src] = by_source.get(src, 0) + 1

    # Top themes (top 5)
    theme_counts: dict[str, int] = {}
    for e in recent:
        theme = e.get("matched_theme")
        if isinstance(theme, str):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
    top_themes = sorted(theme_counts.items(), key=lambda x: -x[1])[:5]

    # Top symbols (top 5)
    sym_counts: dict[str, int] = {}
    for e in recent:
        sym = e.get("candidate_symbol")
        if isinstance(sym, str):
            sym_counts[sym] = sym_counts.get(sym, 0) + 1
    top_symbols = sorted(sym_counts.items(), key=lambda x: -x[1])[:5]

    # Outcome status — outcome_7d/14d/30d henüz Phase 10'da dolacak
    outcome_filled = sum(
        1 for e in recent
        if e.get("outcome_7d") is not None or e.get("outcome_14d") is not None
        or e.get("outcome_30d") is not None
    )

    # Faz 2 C-2 (17 May 2026): Hit rate hesaplama
    hit_rates = _calc_hit_rates(recent) if outcome_filled > 0 else None

    # Outcome status detayı:
    #   no_data        : hiç event yok (yukarıda erken return)
    #   pending_phase10: event'ler var ama outcome'lar None (C-1 öncesi durum)
    #   partial        : bazı event'lerin outcome'u dolu
    #   phase10_ready  : 7g+ olgun event'lerin %80'inden fazlası dolu
    if outcome_filled == 0:
        outcome_status = "pending_phase10"
    else:
        # phase10_ready: 7g+ olgun olan event'lerin yeterli oranı dolu
        mature_7d = sum(
            1 for e in recent
            if _parse_event_ts(e) and
            (now - _parse_event_ts(e)).total_seconds() >= 7 * 86400
        )
        filled_7d = sum(1 for e in recent if e.get("outcome_7d") is not None)
        if mature_7d > 0 and filled_7d / mature_7d >= 0.8:
            outcome_status = "phase10_ready"
        else:
            outcome_status = "partial"

    return {
        "total_events": len(recent),
        "by_flag": by_flag,
        "by_multiplier": by_multiplier,
        "by_source": by_source,
        "top_themes": top_themes,
        "top_symbols": top_symbols,
        "days_collected": _calc_days_collected(tracker, now),
        "phase10_progress_pct": _calc_phase10_progress(tracker, now),
        "outcome_status": outcome_status,
        "hit_rates": hit_rates,
        "adaptive_suggestions": (
            _calc_adaptive_suggestions(hit_rates) if hit_rates else []
        ),
    }


def _parse_event_ts(event: dict) -> Optional[datetime]:
    """Helper: event['ts']'i parse et. Bozuksa None."""
    ts_str = event.get("ts")
    if not isinstance(ts_str, str):
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# ─────────────────────── Adaptive Multiplier (C-3) ──────────────────────────
# Faz 2 C-3 (17 May 2026). PASSIVE raporlama — sabit tablo değişmez,
# sadece "verinin önerdiği çarpan" hesaplanır. Phase 10'da bu sayılar
# kullanılarak _MULTIPLIER_FLAG_TABLE adaptive hale gelecek.

# Mevcut sabit çarpanlar (calibrator.py:_MULTIPLIER_FLAG_TABLE'dan yansıtılır).
_CURRENT_MULTIPLIERS = {
    "pm_confirm":       1.20,
    "pm_confirm_weak":  1.10,
    "pm_conflict_weak": 0.90,
    "pm_conflict":      0.75,
}

# Adaptive tuning parametreleri
_REFERENCE_HIT_RATE = 60.0  # % — "kalibratör ortalama doğru" beklentisi
_MIN_SAMPLE_SIZE = 10       # Bu altında öneri yok, "yetersiz veri"
_MULTIPLIER_CLAMP = (0.50, 1.50)  # Aşırı uçlara gitme


def _suggest_multiplier(flag: str, hit_rate_pct: Optional[float],
                         sample_size: int,
                         current: Optional[float] = None) -> dict:
    """Bir bayrak için "verinin önerdiği çarpan"ı hesapla.

    Args:
        flag: bayrak adı (pm_confirm, pm_confirm_weak, ...)
        hit_rate_pct: hit rate yüzdesi (0-100), None ise henüz hesaplanmadı
        sample_size: kaç event'le hesaplandı
        current: mevcut çarpan (None ise _CURRENT_MULTIPLIERS'tan)

    Returns:
        {
          "flag": str,
          "current": float | None,
          "suggested": float | None,
          "delta": float | None,
          "hit_rate_pct": float | None,
          "sample_size": int,
          "confidence": "high" | "medium" | "low" | "insufficient",
          "note": str,
        }

    Mantık:
        effect = current - 1.0  (pm_confirm: +0.20, pm_conflict: -0.25)
        suggested_effect = effect × (hit_rate / reference)
        suggested = 1.0 + suggested_effect  (clamp [0.50, 1.50])

    Confidence:
        insufficient: sample_size < 10 (öneri None)
        low: 10-19 sample
        medium: 20-49 sample
        high: 50+ sample
    """
    if current is None:
        current = _CURRENT_MULTIPLIERS.get(flag)

    if current is None:
        return {
            "flag": flag,
            "current": None,
            "suggested": None,
            "delta": None,
            "hit_rate_pct": hit_rate_pct,
            "sample_size": sample_size,
            "confidence": "insufficient",
            "note": "Bilinmeyen bayrak — sabit tabloda kayıt yok",
        }

    if hit_rate_pct is None or sample_size < _MIN_SAMPLE_SIZE:
        return {
            "flag": flag,
            "current": current,
            "suggested": None,
            "delta": None,
            "hit_rate_pct": hit_rate_pct,
            "sample_size": sample_size,
            "confidence": "insufficient",
            "note": f"Yetersiz veri ({sample_size} event, min {_MIN_SAMPLE_SIZE})",
        }

    # Adaptive hesap
    effect = current - 1.0
    suggested_effect = effect * (hit_rate_pct / _REFERENCE_HIT_RATE)
    suggested_raw = 1.0 + suggested_effect

    # Clamp
    suggested = max(_MULTIPLIER_CLAMP[0],
                    min(_MULTIPLIER_CLAMP[1], suggested_raw))
    delta = suggested - current

    # Confidence
    if sample_size >= 50:
        confidence = "high"
    elif sample_size >= 20:
        confidence = "medium"
    else:
        confidence = "low"

    # Note
    if abs(delta) < 0.02:
        note = "Mevcut çarpan iyi — minimal değişiklik önerisi"
    elif delta > 0:
        note = f"Çarpan etkisini artırma önerisi (+{delta:.2f})"
    else:
        note = f"Çarpan etkisini azaltma önerisi ({delta:.2f})"

    return {
        "flag": flag,
        "current": round(current, 4),
        "suggested": round(suggested, 4),
        "delta": round(delta, 4),
        "hit_rate_pct": hit_rate_pct,
        "sample_size": sample_size,
        "confidence": confidence,
        "note": note,
    }


def _calc_adaptive_suggestions(hit_rates: dict) -> list[dict]:
    """Tüm bayraklar için adaptive multiplier önerileri (outcome_7d bazlı).

    Returns:
        list[dict] — her bayrak için _suggest_multiplier çıktısı.
        Sıralama: tablo sırası (pm_confirm → pm_confirm_weak →
        pm_conflict_weak → pm_conflict)
    """
    if not hit_rates:
        return []

    bfh = hit_rates.get("by_flag_horizon", {})
    suggestions = []
    flag_order = ["pm_confirm", "pm_confirm_weak",
                  "pm_conflict_weak", "pm_conflict"]

    for flag in flag_order:
        bucket = bfh.get(flag, {}).get("outcome_7d", {})
        hit_rate = bucket.get("rate_pct")
        sample = bucket.get("total", 0)
        suggestions.append(_suggest_multiplier(flag, hit_rate, sample))

    return suggestions


def _calc_days_collected(tracker: dict, now: datetime) -> float:
    """_started_at'ten itibaren kaç gün geçti."""
    started_str = tracker.get("_started_at")
    if not isinstance(started_str, str):
        return 0.0
    try:
        started = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
        return (now - started).total_seconds() / 86400
    except (ValueError, TypeError):
        return 0.0


def _calc_phase10_progress(tracker: dict, now: datetime) -> float:
    """0-100 progress (30 gün hedef)."""
    days = _calc_days_collected(tracker, now)
    return min(100.0, days / 30 * 100)


def format_calibrator_section(stats: dict) -> list[str]:
    """Markdown bölüm satırları."""
    lines = ["\n## Polymarket Kalibratör İstatistikleri\n"]

    if "error" in stats:
        lines.append(f"⚠️ {stats['error']}")
        lines.append(
            "_Kalibratör henüz çalışmadı veya tracker dosyası oluşmadı. "
            "CALIBRATOR_ENABLED=true ile aktif olduktan ve ilk eşleşme "
            "tespit edildikten sonra dolacak._"
        )
        return lines

    total = stats.get("total_events", 0)
    progress = stats.get("phase10_progress_pct", 0)
    days = stats.get("days_collected", 0)

    if total == 0:
        lines.append(f"- Toplam event: **0** (henüz yok)")
        lines.append(
            f"- Tracker: {days:.1f} gün ({progress:.0f}% — "
            f"Phase 10 için 30 gün gerek)"
        )
        return lines

    lines.append(f"- Toplam event: **{total}**")
    lines.append(
        f"- Tracker: {days:.1f} gün ({progress:.0f}% — "
        f"Phase 10 için 30 gün gerek)"
    )

    # Flag dağılımı
    by_flag = stats.get("by_flag", {})
    if by_flag:
        lines.append("\n### Bayrak Dağılımı\n")
        lines.append("| Bayrak | Sayı | % |")
        lines.append("|---|---:|---:|")
        for flag in sorted(by_flag.keys()):
            count = by_flag[flag]
            pct = count / total * 100
            lines.append(f"| `{flag}` | {count} | {pct:.1f}% |")

    # Multiplier dağılımı
    by_mult = stats.get("by_multiplier", {})
    if by_mult:
        lines.append("\n### Çarpan Dağılımı\n")
        lines.append("| Çarpan | Sayı |")
        lines.append("|---|---:|")
        # Yüksek çarpandan düşüğe
        for mult in sorted(by_mult.keys(), reverse=True):
            lines.append(f"| {mult} | {by_mult[mult]} |")

    # Source dağılımı
    by_src = stats.get("by_source", {})
    if by_src:
        lines.append("\n### Kaynak Dağılımı (scanner)\n")
        for src, count in sorted(by_src.items(), key=lambda x: -x[1]):
            lines.append(f"- `{src}`: {count}")

    # Top temalar
    top_themes = stats.get("top_themes", [])
    if top_themes:
        lines.append("\n### En Aktif Temalar (top 5)\n")
        for theme, count in top_themes:
            lines.append(f"- `{theme}`: {count} event")

    # Top semboller
    top_syms = stats.get("top_symbols", [])
    if top_syms:
        lines.append("\n### En Çok Eşleşen Hisseler (top 5)\n")
        for sym, count in top_syms:
            lines.append(f"- **{sym}**: {count} event")

    # Outcome durumu + hit rate raporu (Faz 2 C-2)
    outcome = stats.get("outcome_status", "pending_phase10")
    hit_rates = stats.get("hit_rates")
    lines.append("")

    if outcome == "pending_phase10":
        lines.append(
            "_Hit rate: Phase 10'da hesaplanacak. outcome_7d/14d/30d "
            "field'ları henüz boş — Phase 10 implementasyonunda price "
            "snapshot mantığı eklenince hit rate raporlanır._"
        )
    elif outcome == "partial" and hit_rates is None:
        lines.append("_Hit rate: kısmi veri var, Phase 10 değerlendirmesi gerek._")
    elif hit_rates is not None:
        # Hit rate tabloları
        lines.append(f"### Hit Rate (outcome_status: `{outcome}`)\n")

        # Overall (genel toplam)
        overall = hit_rates.get("overall", {})
        if any(o.get("total", 0) > 0 for o in overall.values()):
            lines.append("**Genel Hit Rate:**\n")
            lines.append("| Horizon | Hit | Toplam | Oran |")
            lines.append("|---|---:|---:|---:|")
            for h in ["outcome_7d", "outcome_14d", "outcome_30d"]:
                o = overall.get(h, {})
                hits = o.get("hits", 0)
                total = o.get("total", 0)
                rate = o.get("rate_pct")
                rate_str = f"{rate:.1f}%" if rate is not None else "—"
                lines.append(f"| {h} | {hits} | {total} | {rate_str} |")
            lines.append("")

        # Per-flag
        bfh = hit_rates.get("by_flag_horizon", {})
        if bfh:
            lines.append("**Bayrak Bazında Hit Rate (outcome_7d):**\n")
            lines.append("| Bayrak | Hit | Toplam | Oran |")
            lines.append("|---|---:|---:|---:|")
            for flag in sorted(bfh.keys()):
                o = bfh[flag].get("outcome_7d", {})
                hits = o.get("hits", 0)
                total = o.get("total", 0)
                rate = o.get("rate_pct")
                rate_str = f"{rate:.1f}%" if rate is not None else "—"
                lines.append(f"| `{flag}` | {hits} | {total} | {rate_str} |")
            lines.append("")

        # Per-source
        bs = hit_rates.get("by_source", {})
        if bs:
            lines.append("**Kaynak Bazında Hit Rate (outcome_7d):**\n")
            lines.append("| Kaynak | Hit | Toplam | Oran |")
            lines.append("|---|---:|---:|---:|")
            for src in sorted(bs.keys()):
                o = bs[src].get("outcome_7d", {})
                hits = o.get("hits", 0)
                total = o.get("total", 0)
                rate = o.get("rate_pct")
                rate_str = f"{rate:.1f}%" if rate is not None else "—"
                lines.append(f"| `{src}` | {hits} | {total} | {rate_str} |")
            lines.append("")

        # Per-theme (top 5 by total)
        bt = hit_rates.get("by_theme", {})
        if bt:
            # Toplam event sayısına göre sırala
            theme_items = sorted(
                bt.items(),
                key=lambda kv: -(kv[1].get("outcome_7d", {}).get("total", 0)),
            )[:5]
            if any(t.get("outcome_7d", {}).get("total", 0) > 0 for _, t in theme_items):
                lines.append("**Tema Bazında Hit Rate (top 5, outcome_7d):**\n")
                lines.append("| Tema | Hit | Toplam | Oran |")
                lines.append("|---|---:|---:|---:|")
                for theme, horizons in theme_items:
                    o = horizons.get("outcome_7d", {})
                    hits = o.get("hits", 0)
                    total = o.get("total", 0)
                    if total == 0:
                        continue
                    rate = o.get("rate_pct")
                    rate_str = f"{rate:.1f}%" if rate is not None else "—"
                    lines.append(f"| `{theme}` | {hits} | {total} | {rate_str} |")
                lines.append("")

        # Yorum: yüksek vs düşük hit rate
        if outcome == "phase10_ready":
            lines.append(
                "_phase10_ready: 7g olgun event'lerin ≥%80'i outcome'a sahip. "
                "Çarpan tuning (Phase 10) için yeterli veri._"
            )
        else:
            lines.append(
                "_partial: outcome doldurma sürüyor. "
                "phase10_ready için 7g olgun event'lerin ≥%80'inin dolu olması gerek._"
            )

        # Adaptive multiplier önerileri (Faz 2 C-3)
        suggestions = stats.get("adaptive_suggestions", [])
        if suggestions:
            lines.append("")
            lines.append("### Adaptive Multiplier Önerileri (passive)\n")
            lines.append(
                "_Sabit tablo şu an değişmiyor. Aşağıdaki tablo, hit rate'lere "
                "göre **veri-önerili** çarpanları gösterir. Phase 10'da "
                "_MULTIPLIER_FLAG_TABLE bu sayılarla replace edilir._\n"
            )
            lines.append("| Bayrak | Mevcut | Veri Önerisi | Δ | Hit Rate | Sample | Güven |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|")
            for s in suggestions:
                flag = s.get("flag", "?")
                current = s.get("current")
                suggested = s.get("suggested")
                delta = s.get("delta")
                hit = s.get("hit_rate_pct")
                sample = s.get("sample_size", 0)
                conf = s.get("confidence", "?")

                cur_str = f"{current:.2f}x" if isinstance(current, (int, float)) else "—"
                if suggested is None:
                    sug_str = "—"
                    delta_str = "—"
                else:
                    sug_str = f"{suggested:.2f}x"
                    delta_str = f"{delta:+.2f}"
                hit_str = f"{hit:.1f}%" if isinstance(hit, (int, float)) else "—"
                lines.append(
                    f"| `{flag}` | {cur_str} | {sug_str} | {delta_str} | "
                    f"{hit_str} | {sample} | `{conf}` |"
                )
            lines.append("")

            # Genel yorum
            has_high_confidence = any(s["confidence"] == "high" for s in suggestions)
            has_actionable = any(
                isinstance(s.get("delta"), (int, float)) and abs(s["delta"]) >= 0.05
                for s in suggestions
            )
            if has_high_confidence and has_actionable:
                lines.append(
                    "_Bazı bayraklar için ≥%5 sapma var ve `high` güven seviyesinde. "
                    "Phase 10 çarpan tuning gündeminde değerlendirilebilir._"
                )
            elif has_actionable:
                lines.append(
                    "_Bazı sapmalar görünüyor ama güven düşük — daha fazla event "
                    "biriksin._"
                )

    return lines


def format_report(days: int) -> str:
    """Markdown rapor."""
    lines = []
    lines.append(f"# Finzora Observability Raporu — Son {days} Gün\n")

    if not DB_PATH.exists():
        lines.append("⚠️ Veritabanı henüz oluşmadı. İlk AI veya FMP çağrısından sonra dolacak.")
        return "\n".join(lines)

    # LLM maliyet
    lines.append("## LLM API Kullanımı\n")
    cost = query_claude_cost(days)
    if "error" in cost:
        lines.append(f"❌ {cost['error']}")
    else:
        lines.append(f"- Toplam çağrı: **{cost['calls']}**")
        lines.append(f"- Başarısız: {cost['failures']}")
        lines.append(f"- Input token: {cost['input_tokens']:,}")
        lines.append(f"- Output token: {cost['output_tokens']:,}")
        lines.append(f"- Tahmini maliyet: **${cost['cost_usd']:.2f}**")
        if days > 0 and cost['cost_usd'] > 0:
            monthly = cost['cost_usd'] * (30 / days)
            lines.append(f"- Aylık projeksiyon: ~${monthly:.2f}")

    # FMP stats
    lines.append("\n## FMP API Endpoint İstatistikleri\n")
    stats = query_fmp_stats(days)
    if stats and "error" in stats[0]:
        lines.append(f"❌ {stats[0]['error']}")
    elif not stats:
        lines.append("Henüz FMP çağrısı yok.")
    else:
        lines.append("| Endpoint | Çağrı | Ort. ms | Başarısız |")
        lines.append("|---|---:|---:|---:|")
        for s in stats[:15]:
            lines.append(
                f"| {s['endpoint']} | {s['calls']} | {s['avg_ms']:.0f} | {s['failures']} |"
            )
        total_calls = sum(s['calls'] for s in stats)
        total_fails = sum(s['failures'] for s in stats)
        lines.append(f"\n**Toplam çağrı: {total_calls}** | Başarısız: {total_fails}")

    # Decision hitrate
    lines.append("\n## Karar Tipi Dağılımı\n")
    hr = query_decision_hitrate(days)
    if "error" in hr:
        lines.append(f"❌ {hr['error']}")
    elif not hr.get("by_type"):
        lines.append("Henüz karar kaydı yok.")
    else:
        lines.append("| Tip | Toplam | Uygulanan | Oran |")
        lines.append("|---|---:|---:|---:|")
        for r in hr["by_type"]:
            lines.append(
                f"| {r['tip']} | {r['count']} | {r['executed']} | {r['rate_pct']}% |"
            )

    # Polymarket Kalibratör (Faz 2 Adım 13)
    cal_stats = query_calibrator_stats(days)
    lines.extend(format_calibrator_section(cal_stats))

    return "\n".join(lines)


def send_to_telegram(text: str) -> bool:
    import os
    import requests

    # Env fallback: hem eski (TELEGRAM_TOKEN/PRIVATE_CHAT) hem standart (BOT_TOKEN/PRIVATE_ID) destekli
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_PRIVATE_CHAT") or os.environ.get("TELEGRAM_PRIVATE_ID", "")
    if not token or not chat:
        print("UYARI: TELEGRAM token veya private chat ID tanımsız "
              "(TELEGRAM_BOT_TOKEN+TELEGRAM_PRIVATE_ID veya legacy TELEGRAM_TOKEN+TELEGRAM_PRIVATE_CHAT)")
        return False

    # Telegram max 4096 karakter
    text = text[:4090] + "..." if len(text) > 4096 else text

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Finzora observability raporu")
    ap.add_argument("--days", type=int, default=7, help="Kaç günlük rapor (default 7)")
    ap.add_argument("--today", action="store_true", help="Sadece bugün")
    ap.add_argument("--telegram", action="store_true", help="Telegram'a gönder")
    args = ap.parse_args()

    days = 1 if args.today else args.days
    report = format_report(days)

    print(report)

    if args.telegram:
        ok = send_to_telegram(report)
        print(f"\nTelegram: {'✓' if ok else '✗'}")


if __name__ == "__main__":
    main()
