"""
Finzora Valuation Framework v6 — Kimi K2 Thinking AI Consultant (via OpenRouter)
=================================================================================
When the framework alone cannot decide (large consensus deviation, low confidence,
high method dispersion), get a second opinion from Kimi via OpenRouter.

Tetikleyiciler:
  1. abs(framework_vs_analyst) >= 50%
  2. confidence_score < 50
  3. method_dispersion_cv >= 0.40
  4. manuel istek (force=True)

Çıktı:
  - claude_fair_value: tek nokta tahmin
  - confidence: 0-100
  - bear / base / bull senaryoları
  - rationale (Türkçe)
  - rejim_yorumu (yapısal/siklik değişim varsayımları)

Final fair value:
  framework_fv × (1 - blend) + claude_fv × blend
  blend = consultation_severity'ye göre 0.30 - 0.50

Tasarım: 2026-04-25 — MU $167 vs $429 konsensüs sapma sonrası v6 düzeltme.
"""

from __future__ import annotations
import os
import json
import re
import time
from typing import Optional

# LLM client — via OpenRouter (Kimi K2 thinking)
import sys as _sys
from pathlib import Path as _Path
_agent_dir = _Path(__file__).resolve().parent.parent
if str(_agent_dir) not in _sys.path:
    _sys.path.insert(0, str(_agent_dir))
from llm_client import chat as _llm_chat, get_api_key as _get_api_key, DEFAULT_MODEL as _DEFAULT_MODEL

CLAUDE_MODEL = os.environ.get("KIMI_MODEL") or os.environ.get("CLAUDE_MODEL") or _DEFAULT_MODEL
CLAUDE_VALUATION_TIMEOUT = 90  # seconds (Kimi thinking can be slower than Opus)

# Observability (opsiyonel)
try:
    import sys
    from pathlib import Path as _P
    _agent = _P(__file__).resolve().parent.parent
    if str(_agent) not in sys.path:
        sys.path.insert(0, str(_agent))
    from observability import log_claude_call
except ImportError:
    log_claude_call = lambda *a, **kw: None


SYSTEM_PROMPT = """You are Finzora's valuation expert — Zeynel's autonomous equity valuation assistant.

CONTEXT:
You will receive a stock's fundamentals plus the framework's mechanical valuation.
The framework uses mid-cycle methods (normalized PE, EV/EBITDA mid-cycle,
mean-reversion DCF). These rely on a return-to-historical-average assumption.

YOUR JOB:
1. Is there a structural regime change? (e.g. AI/HBM for semis, GLP-1 for pharma, EV for autos)
2. Cycle phase: early / mid / late / peak / bottom?
3. What do forward-looking metrics say (PEG, forward PE, growth-adjusted)?
4. Why does analyst consensus differ from the framework?
5. Bear / Base / Bull price targets?

OUTPUT: ONLY the JSON below — no other text. JSON keys MUST stay exactly as shown.
All free-text VALUES (thesis, aciklama, framework_kritik, konsensus_aciklama,
tavsiye) MUST be written in TURKISH (no Turkish-special characters: write
plain ASCII for these values to keep parsing safe — e.g. "satis" not "satış").

```json
{
  "claude_fair_value": 350.0,
  "confidence": 75,
  "scenarios": {
    "bear": {"price": 200.0, "thesis": "Turkish ASCII — bear thesis, single sentence"},
    "base": {"price": 350.0, "thesis": "Turkish ASCII — base thesis"},
    "bull": {"price": 550.0, "thesis": "Turkish ASCII — bull thesis"}
  },
  "rejim_degisikligi": {
    "var_mi": true,
    "tip": "ai_memory_yapisal",
    "aciklama": "Turkish ASCII — single sentence rationale"
  },
  "cycle_phase": "mid",
  "framework_kritik": "Turkish ASCII — single sentence",
  "konsensus_aciklama": "Turkish ASCII — single sentence",
  "tavsiye": "Turkish ASCII — recommendation prose",
  "tavsiye_etiket": "MANUEL_REVIEW"
}
```

RULES:
- claude_fair_value: single 12-month target.
- tavsiye_etiket: one of UCUZ / ADIL / PAHALI / MANUEL_REVIEW (no Turkish special chars).
- confidence: your own confidence (analyst clarity + framework + macro).
- thesis: short, single Turkish sentence, concrete catalyst, plain ASCII.
- No apostrophes (write Zeynelin not "Zeynel'in").
- ONLY return the JSON — no extra prose, no markdown fence outside the JSON."""


def _build_user_prompt(framework_result: dict) -> str:
    """Framework sonucundan Claude'a giden user mesajı."""
    ticker = framework_result.get("ticker", "?")
    fv = framework_result.get("fair_value", {})
    cls = framework_result.get("classification", {})
    conf = framework_result.get("confidence", {})
    methods = framework_result.get("methods_used", [])
    snap = framework_result.get("data_snapshot", {})
    analyst = framework_result.get("analyst_consensus") or {}
    regime = framework_result.get("market_regime") or {}

    method_lines = "\n".join(
        f"  - {m['name']}: ${m['fair_value']:.2f} (w={m['weight']:.0%})"
        for m in methods[:8]
    )

    pe = snap.get("pe_ttm", 0) or 0
    rev_g = (snap.get("rev_growth", 0) or 0) * 100
    op_m = (snap.get("op_margin", 0) or 0) * 100
    fcf_m = (snap.get("fcf_margin", 0) or 0) * 100
    roe = (snap.get("roe", 0) or 0) * 100
    roic = (snap.get("roic", 0) or 0) * 100

    return f"""VALUATION ANALYSIS — {ticker}

PRICE: ${fv.get('current_price', 0):.2f}
ARCHETYPE: {cls.get('archetype_label', '?')} ({cls.get('archetype', '?')})

═══ FRAMEWORK RESULT (mechanical) ═══
Fair value: ${fv.get('point', 0):.2f}
Range: ${fv.get('range_low', 0):.2f} - ${fv.get('range_high', 0):.2f}
Upside: {fv.get('upside_pct', 0):+.1f}%
Verdict: {fv.get('karar', '?')}
Confidence: {conf.get('score', 0)}/100

METHODS USED:
{method_lines}

RED FLAGS: {', '.join(conf.get('red_flags', []))}

═══ ANALYST CONSENSUS ═══
Median: ${analyst.get('median', 0):.2f}
High: ${analyst.get('high', 0):.2f}
Low: ${analyst.get('low', 0):.2f}
Framework gap: {analyst.get('framework_gap_pct', 0):+.1f}%

═══ FUNDAMENTALS ═══
Sector: {snap.get('sector', '?')} / {snap.get('industry', '?')}
Market cap: ${(snap.get('mcap', 0) or 0)/1e9:.1f}B
P/E (TTM): {pe:.1f}
Rev growth (TTM): {rev_g:+.1f}%
Op margin: {op_m:.1f}%
FCF margin: {fcf_m:.1f}%
ROE: {roe:.1f}%
ROIC: {roic:.1f}%

═══ MACRO REGIME ═══
{regime.get('detay', 'no regime data')}
Regime multiplier: {regime.get('multiplier', 1.0)}

═══ QUESTION ═══
Is there a structural regime change for this stock? Are the mid-cycle methods
unfairly lowballing it? In Bear/Base/Bull scenarios, what is the realistic target?
Do you agree with the framework or is a correction required?

Reply with JSON ONLY (free-text values in plain-ASCII Turkish)."""


def _parse_json_response(text: str) -> Optional[dict]:
    """Claude'un cevabından JSON çıkar."""
    # JSON code block varsa öncelikle dene
    block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if block_match:
        try:
            return json.loads(block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Direct JSON parse
    text = text.strip()
    # İlk { ile son } arasını bul
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def consult_claude(
    framework_result: dict,
    severity: float = 0.40,
    force: bool = False,
    verbose: bool = False
) -> Optional[dict]:
    """
    Claude'dan değerleme görüşü al.

    Args:
        framework_result: framework.valuate() çıktısı
        severity: 0.0-1.0, blend ağırlığını belirler (yüksek severity → Claude'a daha çok ağırlık)
        force: True ise tetikleyici olmasa bile çağır
        verbose: stdout log

    Returns:
        {
          "claude_fair_value": float,
          "confidence": int,
          "scenarios": {bear, base, bull},
          "rejim_degisikligi": {...},
          "cycle_phase": str,
          "framework_kritik": str,
          "tavsiye_etiket": str,
          "blended_fair_value": float,    # framework × (1-blend) + claude × blend
          "blend_weight": float,          # 0.30 - 0.50
          "raw_response": str,
          "model": str,
          "duration_ms": int,
        }
        veya None (API key yoksa veya hata)
    """
    if not _get_api_key():
        if verbose:
            print("[ai_consultant] OPENROUTER_API_KEY tanımsız, atlandı")
        return {"_error": "OPENROUTER_API_KEY (veya ANTHROPIC_API_KEY) env var tanımsız"}

    user_prompt = _build_user_prompt(framework_result)

    t0 = time.time()
    try:
        resp = _llm_chat(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            model=CLAUDE_MODEL,
            max_tokens=6000,  # Kimi K2 thinking spends most of the budget on reasoning;
                              # 2000 was empirically not enough to leave room for the JSON.
            temperature=0.3,
            timeout=CLAUDE_VALUATION_TIMEOUT,
            apply_language_policy=False,  # SYSTEM_PROMPT already pins output language explicitly
        )
        duration_ms = int((time.time() - t0) * 1000)
        raw = resp.text

        # Observability
        try:
            log_claude_call(
                mode="valuation_consult",
                model=CLAUDE_MODEL,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                duration_ms=duration_ms,
                metadata={"ticker": framework_result.get("ticker"), "severity": severity},
            )
        except Exception:
            pass

    except Exception as e:
        if verbose:
            print(f"[ai_consultant] LLM API hatası: {type(e).__name__}: {e}")
        return {
            "_error": f"LLM API çağrısı başarısız: {type(e).__name__}: {e}",
            "model_attempted": CLAUDE_MODEL,
            "duration_ms": int((time.time() - t0) * 1000),
        }

    parsed = _parse_json_response(raw)
    if not parsed:
        if verbose:
            print(f"[ai_consultant] JSON parse başarısız:\n{raw[:300]}")
        return {
            "_error": "Claude cevabı JSON formatında değil veya parse edilemedi",
            "raw_response_preview": raw[:500],
            "model": CLAUDE_MODEL,
            "duration_ms": duration_ms,
        }

    # Blend ağırlığı: severity'ye göre 0.30-0.50 arası
    blend = max(0.30, min(0.50, 0.30 + severity * 0.40))

    framework_fv = framework_result.get("fair_value", {}).get("point", 0)
    claude_fv = float(parsed.get("claude_fair_value", framework_fv))

    blended = framework_fv * (1 - blend) + claude_fv * blend

    parsed["blended_fair_value"] = round(blended, 2)
    parsed["blend_weight"] = round(blend, 3)
    parsed["framework_fair_value"] = round(framework_fv, 2)
    parsed["raw_response"] = raw
    parsed["model"] = CLAUDE_MODEL
    parsed["duration_ms"] = duration_ms

    if verbose:
        print(f"[ai_consultant] Claude FV: ${claude_fv:.2f}, "
              f"Framework FV: ${framework_fv:.2f}, "
              f"Blended (w={blend:.0%}): ${blended:.2f}")

    return parsed


def should_consult(framework_result: dict) -> tuple[bool, float, str]:
    """
    Framework sonucuna bakıp Claude'a danışmak gerekli mi karar ver.

    Returns: (should_consult, severity 0-1, reason)
    """
    fv = framework_result.get("fair_value", {})
    conf = framework_result.get("confidence", {})
    analyst = framework_result.get("analyst_consensus") or {}
    methods = framework_result.get("methods_used", [])

    score = conf.get("score", 100)
    gap_pct = abs(analyst.get("framework_gap_pct") or 0)

    # Method dispersion (CV)
    cv = 0.0
    if len(methods) >= 2:
        from statistics import median as _med
        vals = [m["fair_value"] for m in methods]
        med = _med(vals) or 0.01
        if med > 0:
            cv = sum(abs(v - med) for v in vals) / len(vals) / med

    severity = 0.0
    reasons = []

    # Konsensüs sapma severity (en güçlü tetik)
    if gap_pct >= 70:
        severity = max(severity, 0.95)
        reasons.append(f"konsensüs_sapma_{gap_pct:.0f}%")
    elif gap_pct >= 50:
        severity = max(severity, 0.70)
        reasons.append(f"konsensüs_sapma_{gap_pct:.0f}%")
    elif gap_pct >= 30:
        severity = max(severity, 0.40)
        reasons.append(f"konsensüs_sapma_{gap_pct:.0f}%")

    # Düşük güven
    if score < 40:
        severity = max(severity, 0.80)
        reasons.append(f"düşük_güven_{score}")
    elif score < 50:
        severity = max(severity, 0.50)
        reasons.append(f"düşük_güven_{score}")

    # Yüksek metod uyuşmazlığı
    if cv >= 0.50:
        severity = max(severity, 0.60)
        reasons.append(f"metod_dispersion_{cv:.0%}")
    elif cv >= 0.40:
        severity = max(severity, 0.35)
        reasons.append(f"metod_dispersion_{cv:.0%}")

    should = severity >= 0.30
    reason_str = ",".join(reasons) if reasons else "tetikleyici_yok"
    return should, severity, reason_str


if __name__ == "__main__":
    # Test
    fake_result = {
        "ticker": "MU",
        "fair_value": {"point": 167.30, "current_price": 496.72,
                       "range_low": 84.17, "range_high": 245.08,
                       "upside_pct": -66.3, "karar": "PAHALI"},
        "classification": {"archetype": "mature_semi", "archetype_label": "Olgun yarı iletken"},
        "confidence": {"score": 72, "red_flags": ["framework_bearish_vs_analysts"]},
        "methods_used": [
            {"name": "normalized_pe_midcycle", "fair_value": 75.15, "weight": 0.25},
            {"name": "dcf_2stage", "fair_value": 218.82, "weight": 0.20},
        ],
        "analyst_consensus": {"median": 429, "high": 550, "low": 310, "framework_gap_pct": -65},
        "data_snapshot": {
            "sector": "Technology", "industry": "Semiconductors",
            "mcap": 540e9, "pe_ttm": 23.4,
            "rev_growth": 0.57, "op_margin": 0.35,
            "fcf_margin": 0.20, "roe": 0.30, "roic": 0.20,
        },
        "market_regime": {"detay": "🐂 BOGA: SPY > SMA21", "multiplier": 1.12},
    }
    should, sev, reason = should_consult(fake_result)
    print(f"Should consult: {should}, severity: {sev:.2f}, reason: {reason}")
    if should:
        result = consult_claude(fake_result, severity=sev, verbose=True)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
