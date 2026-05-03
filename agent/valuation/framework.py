"""
Finzora Valuation Framework v6 — Aggregator + AI Consultation
================================================================
Pipeline:
  1. classify ticker → archetype
  2. fetch data once
  3. detect cycle phase (siklik sektörler için)
  4. run each applicable method
  5. cycle-phase weight adjustment (mid-cycle vs growth metodları)
  6. outlier detection (3× MAD)
  7. weighted aggregation
  8. konsensüs sapma cezası → confidence düşürme + manuel review
  9. AI consultation tetikleyici kontrolü → AI'ye danış
 10. final fair value blend (framework × (1-w) + claude × w)
 11. senaryolu çıktı (bear/base/bull)
 12. structured output (JSON schema v6)

v6 değişiklikler (2026-04-25):
  - cycle_detector.py entegrasyonu
  - ai_consultant.py entegrasyonu
  - konsensüs sapması artık karar etkiliyor (sadece red flag değil)
  - bear/base/bull senaryolar
  - MANUEL_REVIEW karar etiketi
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

# v6: cycle phase + AI consultation (opsiyonel — modül yoksa sessizce geç)
try:
    from valuation.cycle_detector import detect_cycle_phase, adjust_method_weights
    _CYCLE_AVAILABLE = True
except ImportError:
    detect_cycle_phase = None
    adjust_method_weights = None
    _CYCLE_AVAILABLE = False

try:
    from valuation.ai_consultant import consult_claude, should_consult
    _AI_CONSULT_AVAILABLE = True
except ImportError:
    consult_claude = None
    should_consult = None
    _AI_CONSULT_AVAILABLE = False


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


# ─────────────────────────────────────────────────────────────────────────────
# IN-MEMORY TTL CACHE
# ─────────────────────────────────────────────────────────────────────────────
# Aynı ticker 5 dakika içinde tekrar valuate edilirse cache'den döner.
# Bot batch, portfolio_scan ve opportunity_finder paralel çağrılarda
# gereksiz ~11 FMP call'u engeller.

_VALUATION_CACHE: dict = {}
_CACHE_TTL_SECONDS = 300  # 5 dakika


def _cache_key(ticker: str, apply_regime: bool) -> str:
    return f"{ticker.upper()}:{int(apply_regime)}"


def _cache_get(ticker: str, apply_regime: bool) -> dict | None:
    key = _cache_key(ticker, apply_regime)
    if key not in _VALUATION_CACHE:
        return None
    entry = _VALUATION_CACHE[key]
    import time as _t
    if _t.time() - entry["t"] > _CACHE_TTL_SECONDS:
        del _VALUATION_CACHE[key]
        return None
    return entry["result"]


def _cache_set(ticker: str, apply_regime: bool, result: dict) -> None:
    import time as _t
    _VALUATION_CACHE[_cache_key(ticker, apply_regime)] = {
        "t": _t.time(),
        "result": result,
    }
    # Cache overflow koruması (max 200 ticker)
    if len(_VALUATION_CACHE) > 200:
        oldest = min(_VALUATION_CACHE.items(), key=lambda x: x[1]["t"])
        del _VALUATION_CACHE[oldest[0]]


def clear_cache() -> None:
    """Test / force-refresh için."""
    global _VALUATION_CACHE
    _VALUATION_CACHE = {}


def valuate(ticker: str, verbose: bool = False, apply_regime: bool = True,
            use_cache: bool = True, consult_ai: str = "auto") -> dict:
    """
    Ana giriş noktası — ticker → full valuation report.

    Args:
        ticker: örn "AAPL"
        verbose: stdout log
        apply_regime: True ise fair value SPY SMA21 rejimine göre çarpanla düzeltilir
                      (BOGA: ×1.12, AYI: ×0.87)
        use_cache: True ise 5 dakikalık in-memory cache kullanılır (varsayılan)
        consult_ai: "auto" (default) — büyük sapma/düşük güven/yüksek dispersion'da
                                       otomatik AI'ye danış
                    "always" — her değerlemede AI'ye danış (yavaş, ANTHROPIC_KEY harcar)
                    "never"  — AI consultation kapalı
    """
    ticker = ticker.upper().strip()  # tutarlı cache + FMP case-insensitive

    # Cache key'e consult_ai dahil — farklı modlar farklı cache
    cache_extra_key = f"{apply_regime}:{consult_ai}"

    # ── Cache hit? ────────────────────────────────────────────────
    if use_cache:
        cached = _cache_get(ticker, apply_regime)
        # consult_ai "auto" ise cache normal çalışır
        # "always" → cache atla (her seferinde fresh AI consult)
        if cached is not None and consult_ai != "always":
            if verbose:
                print(f"[Valuation v6] {ticker} → cache hit")
            return cached

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

    # 2b. v6: Cycle phase detection (siklik sektörler için)
    cycle_info = None
    if _CYCLE_AVAILABLE and detect_cycle_phase is not None:
        try:
            cycle_info = detect_cycle_phase(data, archetype=archetype_key)
            if verbose:
                print(f"[Valuation v6] cycle phase: {cycle_info['phase']} "
                      f"(confidence {cycle_info['confidence']:.0%})")
                if cycle_info.get("structural_regime_suspect"):
                    print(f"[Valuation v6] ⚠ Yapısal rejim şüphesi: "
                          f"{cycle_info.get('structural_regime_type')}")
        except Exception as e:
            if verbose:
                print(f"[Valuation v6] cycle detection atlandı: {e}")
            cycle_info = None

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
            result = fn(data, archetype=archetype_key)
        except TypeError:
            # Eski signature (archetype parameter yok) ile uyumluluk
            try:
                result = fn(data)
            except Exception as e:
                methods_failed.append({
                    "name": method_name, "weight": weight, "tier": tier,
                    "reason": f"exception: {e}"
                })
                continue
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

    # 4b. v6: Cycle-based metod ağırlık ayarlaması
    cycle_adjustment_log = None
    if cycle_info and _CYCLE_AVAILABLE and adjust_method_weights is not None:
        try:
            kept, cycle_adjustment_log = adjust_method_weights(kept, cycle_info)
            if verbose and cycle_adjustment_log.get("applied"):
                print(f"[Valuation v6] Metod ağırlık ayarlaması uygulandı "
                      f"(phase={cycle_adjustment_log['phase']}, "
                      f"{len(cycle_adjustment_log['changes'])} metod etkilendi)")
        except Exception as e:
            if verbose:
                print(f"[Valuation v6] weight adjustment atlandı: {e}")

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

    # 5a. Analyst consensus reality check
    analyst_target = data.get("analyst_target_consensus") or data.get("analyst_target_median") or 0
    analyst_info = None
    framework_vs_analyst = None
    if analyst_target > 0:
        gap_pct = ((fair_value / analyst_target) - 1.0) * 100
        framework_vs_analyst = round(gap_pct, 1)
        analyst_info = {
            "consensus": round(analyst_target, 2),
            "median": round(data.get("analyst_target_median", 0), 2),
            "high": round(data.get("analyst_target_high", 0), 2),
            "low": round(data.get("analyst_target_low", 0), 2),
            "framework_gap_pct": framework_vs_analyst,
        }

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

    # Analyst alignment — v6: artık sadece red flag değil, KONFIDANS ETKİLİYOR
    manuel_review_required = False
    consensus_penalty = 0
    if framework_vs_analyst is not None:
        gap_abs = abs(framework_vs_analyst)
        if gap_abs < 15:
            conf_factors.append(f"analyst_consensus_aligned (gap={framework_vs_analyst:+.0f}%)")
            confidence = min(100, confidence + 5)
        elif gap_abs < 30:
            # Hafif sapma — sadece flag, ceza yok
            if framework_vs_analyst > 0:
                red_flags.append(f"framework_bullish_vs_analysts ({framework_vs_analyst:+.0f}% above consensus ${analyst_target:.0f})")
            else:
                red_flags.append(f"framework_bearish_vs_analysts ({framework_vs_analyst:+.0f}% below consensus ${analyst_target:.0f})")
        elif gap_abs < 50:
            # Orta sapma — confidence -10
            consensus_penalty = 10
            confidence = max(0, confidence - 10)
            direction = "bullish" if framework_vs_analyst > 0 else "bearish"
            red_flags.append(f"konsensüs_orta_sapma_{direction} ({framework_vs_analyst:+.0f}% vs ${analyst_target:.0f}, conf -10)")
        elif gap_abs < 70:
            # Büyük sapma — confidence -25, manuel review uyarısı
            consensus_penalty = 25
            confidence = max(0, confidence - 25)
            manuel_review_required = True
            direction = "bullish" if framework_vs_analyst > 0 else "bearish"
            red_flags.append(f"konsensüs_büyük_sapma_{direction} ({framework_vs_analyst:+.0f}% vs ${analyst_target:.0f}, conf -25)")
        else:
            # Aşırı sapma — confidence -40, manuel review zorunlu
            consensus_penalty = 40
            confidence = max(0, confidence - 40)
            manuel_review_required = True
            direction = "bullish" if framework_vs_analyst > 0 else "bearish"
            red_flags.append(f"konsensüs_aşırı_sapma_{direction} ({framework_vs_analyst:+.0f}% vs ${analyst_target:.0f}, conf -40)")

    # v6: Cycle phase penalty/bonus
    if cycle_info:
        if cycle_info.get("structural_regime_suspect"):
            red_flags.append(f"yapısal_rejim_şüphesi ({cycle_info.get('structural_regime_type')})")
            # Yapısal rejim şüphesi → güven -10 (mid-cycle metodları belirsiz)
            confidence = max(0, confidence - 10)
        if cycle_info.get("phase") == "reset":
            red_flags.append("cycle_reset_yapısal_değişim")
        elif cycle_info.get("phase") == "peak":
            conf_factors.append(f"cycle_peak (mean reversion bekleniyor)")

    # 7. Karar etiketi — v6: manuel review öncelikli
    karar_etiket = "YETERSİZ VERİ"
    if manuel_review_required:
        karar_etiket = "MANUEL_REVIEW"
    elif confidence >= 70:
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

    output = {
        "ticker": ticker,
        "framework_version": "v6.0",
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
            "consensus_penalty": consensus_penalty,
            "manuel_review_required": manuel_review_required,
        },

        "methods_used": kept,
        "methods_outliers": outliers,
        "methods_excluded": methods_excluded,
        "methods_failed": methods_failed,

        "market_regime": regime_info,
        "analyst_consensus": analyst_info,

        # v6: cycle phase bilgisi
        "cycle_phase": cycle_info,
        "cycle_weight_adjustment": cycle_adjustment_log,

        "data_snapshot": {
            "sector":       data.get("sector"),
            "industry":     data.get("industry"),
            "mcap":         data.get("mcap"),
            "pe_ttm":       data.get("pe_ttm"),
            "fwd_pe":       data.get("fwd_pe_ny1"),
            "peg_fmp":      data.get("peg_fmp"),
            "rev_growth":   data.get("rev_growth_ttm"),
            "eps_growth":   data.get("eps_growth_ttm"),
            "op_margin":    data.get("op_margin"),
            "fcf_margin":   data.get("fcf_margin"),
            "sbc_intensity": data.get("sbc_intensity"),
            "roe":          data.get("roe"),
            "roic":         data.get("roic"),
            "analyst_count": data.get("analyst_count"),
        },
    }

    # v6: AI consultation tetikleyici kontrolü
    ai_result = None
    consult_decision = {"consulted": False, "reason": "", "severity": 0.0}

    if consult_ai != "never" and _AI_CONSULT_AVAILABLE and consult_claude is not None:
        if consult_ai == "always":
            should = True
            severity = 0.50
            consult_reason = "force_always"
        else:  # "auto"
            should, severity, consult_reason = should_consult(output)

        consult_decision = {
            "consulted": False,
            "should_consult": should,
            "severity": round(severity, 2),
            "reason": consult_reason,
        }

        if should:
            if verbose:
                print(f"[Valuation v6] AI consultation tetiklendi: "
                      f"severity={severity:.2f}, reason={consult_reason}")
            try:
                ai_result = consult_claude(output, severity=severity, verbose=verbose)
                # v6 fix: consult_claude artık error dict de döndürebilir
                if ai_result and "_error" in ai_result:
                    consult_decision["consulted"] = False
                    consult_decision["error"] = ai_result["_error"]
                    if "model_attempted" in ai_result:
                        consult_decision["model_attempted"] = ai_result["model_attempted"]
                    if "raw_response_preview" in ai_result:
                        consult_decision["raw_preview"] = ai_result["raw_response_preview"][:200]
                    ai_result = None  # Blend yapma
                elif ai_result:
                    consult_decision["consulted"] = True
                    consult_decision["model"] = ai_result.get("model")
                    consult_decision["duration_ms"] = ai_result.get("duration_ms")

                    # Final fair value: framework × (1-w) + claude × w
                    blended = ai_result.get("blended_fair_value")
                    blend_w = ai_result.get("blend_weight", 0.30)

                    if blended:
                        # Karar etiketini AI tavsiyesiyle revize et
                        claude_tavsiye = ai_result.get("tavsiye_etiket", "").upper()
                        new_upside = ((blended / price) - 1.0) * 100

                        # AI MANUEL_REVIEW dediyse veya framework manuel review'daysa → manuel
                        if claude_tavsiye == "MANUEL_REVIEW" or manuel_review_required:
                            new_karar = "MANUEL_REVIEW"
                        elif new_upside > 15:
                            new_karar = "UCUZ" if claude_tavsiye in ("UCUZ", "ADIL", "") else f"UCUZ (AI: {claude_tavsiye})"
                        elif new_upside > 5:
                            new_karar = "ADİL-UCUZ"
                        elif new_upside > -5:
                            new_karar = "ADİL"
                        elif new_upside > -15:
                            new_karar = "ADİL-PAHALI"
                        else:
                            new_karar = "PAHALI" if claude_tavsiye in ("PAHALI", "ADIL", "") else f"PAHALI (AI: {claude_tavsiye})"

                        output["fair_value_v6_blended"] = {
                            "point": round(blended, 2),
                            "framework_fv": round(fair_value, 2),
                            "claude_fv": round(ai_result.get("claude_fair_value", 0), 2),
                            "blend_weight": blend_w,
                            "upside_pct_blended": round(new_upside, 1),
                            "karar_blended": new_karar,
                        }

                    output["ai_consultation"] = {
                        "scenarios": ai_result.get("scenarios"),
                        "rejim_degisikligi": ai_result.get("rejim_degisikligi"),
                        "cycle_phase": ai_result.get("cycle_phase"),
                        "framework_kritik": ai_result.get("framework_kritik"),
                        "konsensus_aciklama": ai_result.get("konsensus_aciklama"),
                        "tavsiye": ai_result.get("tavsiye"),
                        "tavsiye_etiket": ai_result.get("tavsiye_etiket"),
                        "claude_confidence": ai_result.get("confidence"),
                        "model": ai_result.get("model"),
                    }
            except Exception as e:
                if verbose:
                    print(f"[Valuation v6] AI consultation hatası: {e}")
                consult_decision["error"] = str(e)

    output["consultation"] = consult_decision

    # v6: Senaryolu çıktı (bear/base/bull) — AI varsa onunkini, yoksa framework'tan üret
    if ai_result and ai_result.get("scenarios"):
        output["scenarios"] = ai_result["scenarios"]
    else:
        # Framework-only senaryolar: range_low (bear), point (base), analyst_high veya range_high × 1.2 (bull)
        bull_price = analyst_info.get("high") if analyst_info else (range_high * 1.20)
        if not bull_price or bull_price < fair_value:
            bull_price = fair_value * 1.30
        output["scenarios"] = {
            "bear": {"price": round(range_low, 2), "thesis": "Mid-cycle mean reversion, multiple sıkışması"},
            "base": {"price": round(fair_value, 2), "thesis": "Framework ağırlıklı ortalama"},
            "bull": {"price": round(bull_price, 2), "thesis": "Analist high target / yapısal rejim devam"},
        }

    # Prediction log — her valuate() çağrısı kayda geçer (backtest altyapısı)
    try:
        from valuation.prediction_log import log_valuation
        log_valuation(output)
    except Exception:
        pass  # log hatası kritik değil

    # Cache kaydı (sonraki 5 dk için)
    if use_cache:
        _cache_set(ticker, apply_regime, output)

    return output


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
        # ─── KISA versiyon (default) — başlık + 1 cümle sebep + 1 satır senaryo ───
        blended = result.get("fair_value_v6_blended")
        if blended:
            target = blended["point"]
            upside = blended["upside_pct_blended"]
            karar = blended["karar_blended"]
        else:
            target = fv["point"]
            upside = fv["upside_pct"]
            karar = fv["karar"]

        # İkon: turuncu = manuel review
        if "MANUEL_REVIEW" in karar:
            ico = "🟠"
        elif upside > 5:
            ico = "🟢"
        elif upside < -5:
            ico = "🔴"
        else:
            ico = "🟡"

        # 1 cümle sebep
        sebep = ""
        ai = result.get("ai_consultation") or {}
        if blended and ai:
            # AI varsa: framework vs AI özet
            fw_fv = blended["framework_fv"]
            cl_fv = blended["claude_fv"]
            kritik = (ai.get("framework_kritik") or "").strip()
            if kritik:
                # Kritik cümlesini 100 karakterle kes
                if len(kritik) > 100:
                    kritik = kritik[:97].rstrip() + "..."
                sebep = f"Framework ${fw_fv:.0f} (mid-cycle) vs AI ${cl_fv:.0f}: {kritik}"
            else:
                rejim = ai.get("rejim_degisikligi", {}).get("tip") or "?"
                sebep = f"Framework ${fw_fv:.0f} vs AI ${cl_fv:.0f} (rejim: {rejim})"
        else:
            # AI yoksa: en kritik flag veya cycle
            flags = conf.get("red_flags", [])
            cycle = result.get("cycle_phase") or {}
            if cycle.get("structural_regime_suspect"):
                sebep = f"Yapısal rejim şüphesi: {cycle.get('structural_regime_type')}, framework lowball edebilir"
            elif flags:
                sebep = flags[0]
            else:
                sebep = f"{cls['archetype_label']}, cycle {cycle.get('phase', 'normal')}"

        out = [
            f"{ico} <b>{t}</b> ${fv['current_price']:.2f} → <b>${target:.0f}</b> ({upside:+.1f}%) <b>{karar}</b>",
            "",
            sebep,
        ]

        # Senaryolar tek satır (sadece anlamlı farklılarsa)
        scen = result.get("scenarios")
        if scen:
            out.append(f"Bear ${scen['bear']['price']:.0f} · Base ${scen['base']['price']:.0f} · Bull ${scen['bull']['price']:.0f}")

        # Footer mini bilgi
        cycle = result.get("cycle_phase")
        ac = result.get("analyst_consensus")
        footer_parts = []
        if cycle and cycle.get("phase") and cycle["phase"] != "n/a":
            footer_parts.append(f"cycle {cycle['phase']}")
        if ac:
            footer_parts.append(f"konsensüs ${ac['consensus']:.0f}")
        footer_parts.append(f"güven {conf['score']}")
        out.append("· ".join(footer_parts))

        out.append("")
        out.append(f"<i>Detay için: /detay {t}</i>")

        return "\n".join(out)

    if style == "telegram_full":
        # ─── UZUN versiyon — eski v6 detaylı çıktı, /detay için ───
        # HTML format
        ico = "🟢" if fv["upside_pct"] > 5 else "🔴" if fv["upside_pct"] < -5 else "🟡"
        # v6: manuel review için özel ikon
        if "MANUEL_REVIEW" in fv.get("karar", ""):
            ico = "🟠"
        out = [
            f"<b>{t} — v6 Adil Değer</b>",
            f"<i>{cls['archetype_label']} (güven %{cls['confidence']*100:.0f})</i>",
            "",
            f"{ico} <b>${fv['current_price']:.2f}</b> → hedef <b>${fv['point']:.2f}</b> ({fv['upside_pct']:+.1f}%)",
            f"Aralık: ${fv['range_low']:.2f} — ${fv['range_high']:.2f}",
            f"Karar: <b>{fv['karar']}</b>",
            f"Güven skoru: <b>{conf['score']}/100</b>",
        ]

        # v6: Blended fair value (AI consultation sonrası)
        blended = result.get("fair_value_v6_blended")
        if blended:
            out.append("")
            out.append(f"🤖 <b>AI Blend:</b> ${blended['point']:.2f} "
                       f"(framework ${blended['framework_fv']:.2f} × {1-blended['blend_weight']:.0%} + "
                       f"AI ${blended['claude_fv']:.2f} × {blended['blend_weight']:.0%})")
            out.append(f"Blend upside: {blended['upside_pct_blended']:+.1f}% → <b>{blended['karar_blended']}</b>")

        regime = result.get("market_regime")
        if regime:
            out.append(f"{regime['detay']} (×{regime['multiplier']:.2f})")

        # v6: Cycle phase
        cycle = result.get("cycle_phase")
        if cycle and cycle.get("is_cyclical"):
            phase_ico = {"bottom": "⬇️", "early": "↗️", "mid": "▶️",
                         "late": "⚠️", "peak": "🔺", "reset": "🔄"}.get(cycle["phase"], "")
            out.append(f"{phase_ico} Cycle: <b>{cycle['phase']}</b> (güven %{cycle['confidence']*100:.0f})")
            if cycle.get("structural_regime_suspect"):
                out.append(f"⚠ Yapısal rejim şüphesi: {cycle.get('structural_regime_type')}")

        ac = result.get("analyst_consensus")
        if ac:
            gap = ac["framework_gap_pct"]
            gap_ico = "≈" if abs(gap) < 10 else ("↑" if gap > 0 else "↓")
            out.append(f"📊 Analist hedef: ${ac['consensus']:.0f} (range ${ac['low']:.0f}-${ac['high']:.0f}), framework vs {gap_ico}{gap:+.0f}%")

        # v6: Senaryolar
        scen = result.get("scenarios")
        if scen:
            out.append("")
            out.append(f"<b>Senaryolar:</b>")
            out.append(f"  🐻 Bear: ${scen['bear']['price']:.2f} — {scen['bear']['thesis'][:60]}")
            out.append(f"  ➖ Base: ${scen['base']['price']:.2f} — {scen['base']['thesis'][:60]}")
            out.append(f"  🐂 Bull: ${scen['bull']['price']:.2f} — {scen['bull']['thesis'][:60]}")

        # v6: AI consultation özeti
        ai = result.get("ai_consultation")
        if ai:
            out.append("")
            out.append(f"<b>🤖 AI görüşü ({ai.get('model', '?')}):</b>")
            if ai.get("rejim_degisikligi", {}).get("var_mi"):
                out.append(f"  Rejim değişimi: <b>{ai['rejim_degisikligi'].get('tip')}</b>")
                out.append(f"  → {ai['rejim_degisikligi'].get('aciklama', '')[:120]}")
            if ai.get("framework_kritik"):
                out.append(f"  Framework kritiği: {ai['framework_kritik'][:150]}")
            if ai.get("tavsiye"):
                out.append(f"  Tavsiye: {ai['tavsiye'][:150]}")
        else:
            # v6: AI consultation yapılmadıysa nedenini göster (debug için kritik)
            consult = result.get("consultation", {})
            if consult.get("should_consult"):
                out.append("")
                if consult.get("error"):
                    out.append(f"<b>⚠ AI consultation BAŞARISIZ:</b>")
                    out.append(f"  Sebep: {consult['error'][:200]}")
                    if consult.get("model_attempted"):
                        out.append(f"  Model: {consult['model_attempted']}")
                    if consult.get("raw_preview"):
                        out.append(f"  Cevap önizleme: <code>{consult['raw_preview'][:150]}</code>")
                else:
                    out.append(f"<b>⚠ AI consultation tetiklenmesi gerekti</b> "
                               f"(severity={consult.get('severity', 0):.2f}, "
                               f"reason={consult.get('reason', '?')[:60]}) ama yapılmadı")

        out.append("")
        out.append(f"<b>Kullanılan metodlar:</b>")
        for m in result["methods_used"]:
            ic = "⭐" if m["tier"] == "primary" else "◽"
            w_str = f"w={m['weight']:.0%}"
            if m.get("original_weight") and abs(m["original_weight"] - m["weight"]) > 0.001:
                w_str = f"w={m['weight']:.0%} (was {m['original_weight']:.0%})"
            out.append(f"  {ic} {m['name']:28} ${m['fair_value']:.2f}  ({w_str})")

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
        f"  ADİL DEĞER v6 — {t}",
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
    ]

    # v6: blended fair value
    blended = result.get("fair_value_v6_blended")
    if blended:
        out.append(f"  🤖 AI BLEND:    ${blended['point']:.2f} ({blended['upside_pct_blended']:+.1f}%)")
        out.append(f"     framework ${blended['framework_fv']:.2f} × {1-blended['blend_weight']:.0%} + "
                   f"AI ${blended['claude_fv']:.2f} × {blended['blend_weight']:.0%}")
        out.append(f"     Blend kararı: {blended['karar_blended']}")
        out.append("")

    # v6: cycle phase
    cycle = result.get("cycle_phase")
    if cycle and cycle.get("is_cyclical"):
        out.append(f"  🔄 Cycle phase: {cycle['phase']} (güven {cycle['confidence']:.0%})")
        if cycle.get("structural_regime_suspect"):
            out.append(f"     ⚠ Yapısal rejim şüphesi: {cycle.get('structural_regime_type')}")
        adj = result.get("cycle_weight_adjustment")
        if adj and adj.get("applied"):
            out.append(f"     Metod ağırlık ayarlaması: {len(adj['changes'])} metod etkilendi")
        out.append("")

    ac = result.get("analyst_consensus")
    if ac:
        gap = ac["framework_gap_pct"]
        out.append(f"  📊 Analist konsensüsü: ${ac['consensus']:.2f} (${ac['low']:.0f}–${ac['high']:.0f}), framework vs {gap:+.1f}%")
        if conf.get("consensus_penalty"):
            out.append(f"     ⚠ Konsensüs sapma cezası: -{conf['consensus_penalty']} confidence")
        out.append("")

    # v6: senaryolar
    scen = result.get("scenarios")
    if scen:
        out.append(f"  Senaryolar:")
        out.append(f"    🐻 Bear: ${scen['bear']['price']:.2f} — {scen['bear']['thesis']}")
        out.append(f"    ➖ Base: ${scen['base']['price']:.2f} — {scen['base']['thesis']}")
        out.append(f"    🐂 Bull: ${scen['bull']['price']:.2f} — {scen['bull']['thesis']}")
        out.append("")

    # v6: AI consultation
    ai = result.get("ai_consultation")
    if ai:
        out.append(f"  🤖 AI görüşü ({ai.get('model', '?')}):")
        if ai.get("rejim_degisikligi", {}).get("var_mi"):
            out.append(f"     Rejim değişimi: {ai['rejim_degisikligi'].get('tip')}")
            out.append(f"     → {ai['rejim_degisikligi'].get('aciklama', '')}")
        if ai.get("framework_kritik"):
            out.append(f"     Framework kritiği: {ai['framework_kritik']}")
        if ai.get("tavsiye"):
            out.append(f"     Tavsiye: {ai['tavsiye']}")
        out.append("")
    else:
        consult = result.get("consultation", {})
        if consult.get("should_consult") and not consult.get("consulted"):
            out.append(f"  🤖 AI consultation tetiklenmesi gerekti ama yapılmadı: "
                       f"{consult.get('reason', '?')}")
            if consult.get("error"):
                out.append(f"     Hata: {consult['error']}")
            out.append("")

    out.append("  Kullanılan Metotlar (ağırlıklı):")
    for m in result["methods_used"]:
        star = "⭐" if m["tier"] == "primary" else " "
        w_disp = f"w={m['weight']:.0%}"
        if m.get("original_weight") and abs(m["original_weight"] - m["weight"]) > 0.001:
            w_disp = f"w={m['weight']:.0%}(orig {m['original_weight']:.0%})"
        out.append(f"    {star} {m['name']:30} ${m['fair_value']:8.2f}  {w_disp}  — {m['notes'][:40]}")

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
