"""
Finzora Valuation Framework v5 — Aggregator
=============================================
Pipeline:
  1. classify ticker → archetype
  2. fetch data once
  3. run each applicable method
  4. outlier detection (3× MAD)
  5. weighted aggregation
  6. classification-fit-adjusted confidence
  7. structured output (JSON schema)
"""

from __future__ import annotations
import sys
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

from valuation.archetypes import get_archetype, ARCHETYPES
from valuation.classifier import classify
from valuation.methods import fetch_all_data
from valuation.methods.registry import get_method


def _outlier_filter(method_values: list, threshold_factor: float = 3.0) -> tuple[list, list]:
    """
    MAD-based outlier detection.
    Returns: (kept, excluded_as_outlier)
    """
    if len(method_values) < 3:
        return method_values, []

    vals = [mv["fair_value"] for mv in method_values]
    med = median(vals)
    abs_devs = [abs(v - med) for v in vals]
    mad = median(abs_devs) or 0.01

    kept = []
    outliers = []
    for mv in method_values:
        if abs(mv["fair_value"] - med) > threshold_factor * mad:
            mv_copy = dict(mv)
            mv_copy["outlier_reason"] = f"{abs(mv['fair_value'] - med) / mad:.1f}×MAD from median ${med:.2f}"
            outliers.append(mv_copy)
        else:
            kept.append(mv)

    return kept, outliers


def _compute_confidence(
    archetype_confidence: float,
    method_results: list,
    applicable_weight_sum: float,
    potential_weight_sum: float,
    current_price: float,
    fair_value: float
) -> tuple[int, list, list]:
    """
    Confidence = (classification fit × method agreement) × 100
    Returns: (score, factors, red_flags)
    """
    factors = []
    red_flags = []

    # 1. Classification fit (0-1)
    class_fit = archetype_confidence
    factors.append(f"archetype_confidence={class_fit:.0%}")

    # 2. Applicable method weight coverage
    weight_coverage = (applicable_weight_sum / potential_weight_sum) if potential_weight_sum > 0 else 0
    factors.append(f"method_coverage={weight_coverage:.0%}")

    # 3. Method agreement (dispersion)
    if len(method_results) >= 2:
        vals = [m["fair_value"] for m in method_results]
        med = median(vals)
        if med > 0:
            cv = sum(abs(v - med) for v in vals) / len(vals) / med  # coefficient of variation
            # CV <0.15 → excellent agreement; >0.40 → poor
            agreement = max(0, 1.0 - (cv / 0.4))
            factors.append(f"dispersion_CV={cv:.0%}")
            if cv > 0.5:
                red_flags.append(f"methods_disagree (CV={cv:.0%})")
        else:
            agreement = 0.3
            red_flags.append("negative_median_fair_value")
    else:
        agreement = 0.5
        red_flags.append("only_one_method_applicable")

    # 4. Combine
    raw = (class_fit * 0.35) + (weight_coverage * 0.35) + (agreement * 0.30)
    score = int(round(raw * 100))

    # 5. Edge case flags
    if fair_value > 0 and current_price > 0:
        upside = (fair_value / current_price) - 1.0
        if abs(upside) > 1.0:
            red_flags.append(f"large_deviation_from_market ({upside:+.0%})")
        if abs(upside) < 0.05:
            factors.append("converges_with_market")

    if len(method_results) < 3:
        red_flags.append(f"few_methods_applicable ({len(method_results)})")

    return score, factors, red_flags


def valuate(ticker: str, verbose: bool = False, apply_regime: bool = True) -> dict:
    """
    Ana giriş noktası — ticker → full valuation report.

    Args:
        ticker: örn "AAPL"
        verbose: stdout log
        apply_regime: True ise fair value SPY SMA21 rejimine göre çarpanla düzeltilir
                      (BOGA: ×1.12, AYI: ×0.87)
    """
    # 1. Classify
    cls = classify(ticker)
    archetype_key = cls["archetype"]
    archetype = get_archetype(archetype_key)

    if verbose:
        print(f"[Valuation v5] {ticker} → archetype: {archetype_key} ({cls['confidence']:.0%})")
        print(f"[Valuation v5] Trigger: {cls['signals'].get('trigger')}")

    # 2. Fetch data
    data = fetch_all_data(ticker)

    if data.get("price", 0) <= 0:
        return {
            "ticker": ticker,
            "error": "price_not_available",
            "archetype": archetype_key,
        }

    # 3. Run each method
    methods_used = []
    methods_excluded = []
    methods_failed = []
    total_weight_potential = 0.0
    total_weight_applicable = 0.0

    for method_name, weight, tier in archetype.all_methods():
        total_weight_potential += weight

        fn = get_method(method_name)
        if fn is None:
            methods_failed.append({
                "name": method_name, "weight": weight, "tier": tier,
                "reason": "not_implemented_yet"
            })
            continue

        try:
            result = fn(data)
        except Exception as e:
            methods_failed.append({
                "name": method_name, "weight": weight, "tier": tier,
                "reason": f"exception: {e}"
            })
            continue

        if result is None:
            methods_failed.append({
                "name": method_name, "weight": weight, "tier": tier,
                "reason": "data_insufficient"
            })
            continue

        methods_used.append({
            "name": method_name,
            "weight": weight,
            "tier": tier,
            "fair_value": result["fair_value"],
            "notes": result.get("notes", ""),
        })
        total_weight_applicable += weight

    # Excluded (hard exclusions from archetype)
    for method_name, reason in archetype.excluded.items():
        methods_excluded.append({
            "name": method_name,
            "reason": reason,
        })

    if not methods_used:
        return {
            "ticker": ticker,
            "archetype": archetype_key,
            "error": "no_methods_applicable",
            "methods_failed": methods_failed,
        }

    # 4. Outlier detection
    kept, outliers = _outlier_filter(methods_used, threshold_factor=3.0)

    # Ağırlıkları yeniden normalize et (outlier'lar çıkarıldıktan sonra)
    kept_weight_sum = sum(m["weight"] for m in kept)
    if kept_weight_sum == 0:
        return {
            "ticker": ticker,
            "archetype": archetype_key,
            "error": "all_methods_outliers",
            "outliers": outliers,
        }

    # 5. Weighted aggregation
    fair_value = sum(m["fair_value"] * m["weight"] for m in kept) / kept_weight_sum

    vals = [m["fair_value"] for m in kept]
    range_low = min(vals)
    range_high = max(vals)

    # 5b. Market regime multiplier (opsiyonel)
    regime_info = None
    if apply_regime:
        try:
            from valuation.market_regime import get_market_regime, get_regime_multiplier
            rejim, spy_p, sma21, detay = get_market_regime()
            mult = get_regime_multiplier()
            fair_value_raw = fair_value
            fair_value = fair_value * mult
            range_low = range_low * mult
            range_high = range_high * mult
            regime_info = {
                "rejim": rejim,
                "multiplier": mult,
                "spy_price": spy_p,
                "sma21": sma21,
                "detay": detay,
                "fair_value_pre_regime": round(fair_value_raw, 2),
            }
        except Exception as e:
            if verbose:
                print(f"[Valuation v5] Regime multiplier atlandı: {e}")

    price = data["price"]
    upside_pct = ((fair_value / price) - 1.0) * 100 if price > 0 else 0

    # 6. Confidence
    confidence, conf_factors, red_flags = _compute_confidence(
        archetype_confidence=cls["confidence"],
        method_results=kept,
        applicable_weight_sum=kept_weight_sum,
        potential_weight_sum=total_weight_potential,
        current_price=price,
        fair_value=fair_value,
    )

    # Outlier red flag
    if outliers:
        red_flags.append(f"{len(outliers)}_outliers_removed")

    # SBC dilution warning
    if data.get("sbc_intensity", 0) > 0.10:
        red_flags.append(f"high_sbc_{data['sbc_intensity']:.0%}_rev")

    # 7. Output
    karar_etiket = "YETERSİZ VERİ"
    if confidence >= 70:
        if upside_pct > 15:
            karar_etiket = "UCUZ"
        elif upside_pct > 5:
            karar_etiket = "ADİL-UCUZ"
        elif upside_pct > -5:
            karar_etiket = "ADİL"
        elif upside_pct > -15:
            karar_etiket = "ADİL-PAHALI"
        else:
            karar_etiket = "PAHALI"
    elif confidence >= 50:
        if upside_pct > 10:
            karar_etiket = "UCUZ (düşük güven)"
        elif upside_pct < -10:
            karar_etiket = "PAHALI (düşük güven)"
        else:
            karar_etiket = "ADİL (düşük güven)"
    else:
        karar_etiket = "YETERSİZ GÜVEN"

    return {
        "ticker": ticker,
        "framework_version": "v5.0",
        "timestamp": __import__("datetime").datetime.now().isoformat(),

        "classification": {
            "archetype": archetype_key,
            "archetype_label": archetype.label,
            "confidence": cls["confidence"],
            "trigger": cls["signals"].get("trigger"),
            "fallback_used": cls.get("fallback_used", False),
        },

        "fair_value": {
            "point":       round(fair_value, 2),
            "range_low":   round(range_low, 2),
            "range_high":  round(range_high, 2),
            "current_price": round(price, 2),
            "upside_pct":  round(upside_pct, 1),
            "karar":       karar_etiket,
        },

        "confidence": {
            "score":     confidence,
            "factors":   conf_factors,
            "red_flags": red_flags,
        },

        "methods_used": kept,
        "methods_outliers": outliers,
        "methods_excluded": methods_excluded,
        "methods_failed": methods_failed,

        "market_regime": regime_info,

        "data_snapshot": {
            "sector":       data.get("sector"),
            "industry":     data.get("industry"),
            "mcap":         data.get("mcap"),
            "pe_ttm":       data.get("pe_ttm"),
            "rev_growth":   data.get("rev_growth_ttm"),
            "op_margin":    data.get("op_margin"),
            "fcf_margin":   data.get("fcf_margin"),
            "sbc_intensity": data.get("sbc_intensity"),
            "roe":          data.get("roe"),
            "roic":         data.get("roic"),
            "analyst_count": data.get("analyst_count"),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTED OUTPUT (bot / terminal için)
# ─────────────────────────────────────────────────────────────────────────────

def format_report(result: dict, style: str = "terminal") -> str:
    """Terminal veya Telegram HTML için formatla."""
    if result.get("error"):
        return f"❌ {result['ticker']}: {result['error']}"

    t = result["ticker"]
    cls = result["classification"]
    fv = result["fair_value"]
    conf = result["confidence"]

    if style == "telegram":
        # HTML format
        ico = "🟢" if fv["upside_pct"] > 5 else "🔴" if fv["upside_pct"] < -5 else "🟡"
        out = [
            f"<b>{t} — v5 Adil Değer</b>",
            f"<i>{cls['archetype_label']} (güven %{cls['confidence']*100:.0f})</i>",
            "",
            f"{ico} <b>${fv['current_price']:.2f}</b> → hedef <b>${fv['point']:.2f}</b> ({fv['upside_pct']:+.1f}%)",
            f"Aralık: ${fv['range_low']:.2f} — ${fv['range_high']:.2f}",
            f"Karar: <b>{fv['karar']}</b>",
            f"Güven skoru: <b>{conf['score']}/100</b>",
        ]
        regime = result.get("market_regime")
        if regime:
            out.append(f"{regime['detay']} (×{regime['multiplier']:.2f})")
        out.append("")
        out.append(f"<b>Kullanılan metodlar:</b>")
        for m in result["methods_used"]:
            ic = "⭐" if m["tier"] == "primary" else "◽"
            out.append(f"  {ic} {m['name']:28} ${m['fair_value']:.2f}  (w={m['weight']:.0%})")

        if result.get("methods_outliers"):
            out.append("")
            out.append(f"<b>⚠ Outlier'lar ({len(result['methods_outliers'])}):</b>")
            for o in result["methods_outliers"]:
                out.append(f"  ✗ {o['name']:28} ${o['fair_value']:.2f} ({o.get('outlier_reason','')})")

        excl = result.get("methods_excluded", [])
        if excl:
            out.append("")
            out.append(f"<b>Yasaklı ({len(excl)}):</b> {', '.join(e['name'] for e in excl[:5])}...")

        if conf["red_flags"]:
            out.append("")
            out.append(f"<b>⚠ Red flags:</b> {', '.join(conf['red_flags'])}")

        return "\n".join(out)

    # Terminal format
    out = [
        "=" * 62,
        f"  ADİL DEĞER v5 — {t}",
        f"  {cls['archetype_label']}",
        f"  Archetype confidence: %{cls['confidence']*100:.0f}",
        "=" * 62,
        "",
        f"  Güncel fiyat:   ${fv['current_price']:.2f}",
        f"  Adil değer:     ${fv['point']:.2f}",
        f"  Aralık:         ${fv['range_low']:.2f} — ${fv['range_high']:.2f}",
        f"  Fark:           {fv['upside_pct']:+.1f}%  →  {fv['karar']}",
        f"  Güven skoru:    {conf['score']}/100",
        "",
        f"  Trigger: {cls['trigger']}",
        "",
        "  Kullanılan Metotlar (ağırlıklı):",
    ]
    for m in result["methods_used"]:
        star = "⭐" if m["tier"] == "primary" else " "
        out.append(f"    {star} {m['name']:28} ${m['fair_value']:8.2f}  w={m['weight']:.0%}  — {m['notes'][:40]}")

    if result.get("methods_outliers"):
        out.append("")
        out.append(f"  ⚠ Outlier'lar (dahil edilmedi):")
        for o in result["methods_outliers"]:
            out.append(f"    ✗ {o['name']:28} ${o['fair_value']:8.2f}  — {o.get('outlier_reason','')}")

    excluded = result.get("methods_excluded", [])
    if excluded:
        out.append("")
        out.append(f"  🚫 Yasaklı metotlar ({len(excluded)}):")
        for e in excluded[:5]:
            out.append(f"    ✗ {e['name']:28} — {e['reason']}")

    if conf.get("red_flags"):
        out.append("")
        out.append(f"  ⚠ Red flags: {', '.join(conf['red_flags'])}")

    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    # Smoke test
    import os
    import json

    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["ALAB", "MSFT", "JPM", "O", "KO", "TSLA", "NVDA"]

    for t in tickers:
        try:
            result = valuate(t, verbose=True)
            print(format_report(result))
        except Exception as e:
            print(f"❌ {t}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        print()
