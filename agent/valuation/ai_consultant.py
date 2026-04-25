"""
Finzora Valuation Framework v6 — Claude AI Consultant
======================================================
Tek başına framework karar veremediğinde (büyük konsensüs sapması, düşük güven,
yüksek metod uyuşmazlığı) Claude'dan ikinci görüş alır.

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

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
CLAUDE_VALUATION_TIMEOUT = 60  # saniye

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


SYSTEM_PROMPT = """Sen Finzora değerleme uzmanısın — Zeynel'in otonom hisse değerleme asistanı.

GÖREV:
Sana bir hissenin temel verileri ve framework'un mekanik değerleme sonucu verilecek.
Framework mid-cycle metodları (normalize edilmiş PE, EV/EBITDA mid-cycle, mean-reversion DCF)
kullanıyor. Bu metodlar tarihsel ortalamaya geri dönüş varsayımına dayanır.

SENİN GÖREVİN:
1. Yapısal rejim değişikliği var mı? (örn: AI/HBM yarı iletkenler için, GLP-1 ilaç için, EV otomotiv için)
2. Cycle aşaması: early/mid/late/peak/bottom?
3. Forward looking metrikler (PEG, forward PE, growth-adjusted) ne diyor?
4. Analist konsensüsü ile framework neden farklı?
5. Bear/Base/Bull senaryolarda hedef fiyat?

ÇIKTI: SADECE aşağıdaki JSON formatında, başka hiçbir şey yazma.

```json
{
  "claude_fair_value": 350.0,
  "confidence": 75,
  "scenarios": {
    "bear": {"price": 200.0, "thesis": "AI capex yavaşlar, memory cycle peak"},
    "base": {"price": 350.0, "thesis": "HBM yapısal rejim devam, growth normalize"},
    "bull": {"price": 550.0, "thesis": "AI memory supercycle, multiple expansion"}
  },
  "rejim_degisikligi": {
    "var_mi": true,
    "tip": "ai_memory_yapisal",
    "aciklama": "HBM marjlari historicallden yapisal yuksek, mean-reversion gecmiyor"
  },
  "cycle_phase": "mid",
  "framework_kritik": "Mid-cycle PE metodu HBM rejim degisikligini yakalamiyor, %40 lowball",
  "konsensus_aciklama": "Analist $429 buyume normalize forward PE bazli, framework $167 mean-reversion bazli",
  "tavsiye": "PAHALI ama satma tezi sadece cycle peak hipotezi dogruysa gecerli, MANUEL REVIEW",
  "tavsiye_etiket": "MANUEL_REVIEW"
}
```

KURALLAR:
- claude_fair_value: tek nokta hedef (12-ay)
- tavsiye_etiket: UCUZ / ADIL / PAHALI / MANUEL_REVIEW (Turkce karakter yok)
- confidence: kendi guvenin (analist + framework + makro netligi)
- thesis: kisa, tek cumle, somut katalist
- Turkce yaz, kesme isareti kullanma, profesyonel ton
- SADECE JSON, baska aciklama yok"""


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

    return f"""DEGERLEME ANALIZI — {ticker}

FIYAT: ${fv.get('current_price', 0):.2f}
ARCHETYPE: {cls.get('archetype_label', '?')} ({cls.get('archetype', '?')})

═══ FRAMEWORK SONUCU (mekanik) ═══
Adil deger: ${fv.get('point', 0):.2f}
Aralik: ${fv.get('range_low', 0):.2f} - ${fv.get('range_high', 0):.2f}
Upside: {fv.get('upside_pct', 0):+.1f}%
Karar: {fv.get('karar', '?')}
Guven: {conf.get('score', 0)}/100

KULLANILAN METODLAR:
{method_lines}

KIRMIZI BAYRAKLAR: {', '.join(conf.get('red_flags', []))}

═══ ANALIST KONSENSUSU ═══
Median: ${analyst.get('median', 0):.2f}
High: ${analyst.get('high', 0):.2f}
Low: ${analyst.get('low', 0):.2f}
Framework gap: {analyst.get('framework_gap_pct', 0):+.1f}%

═══ TEMEL VERILER ═══
Sektor: {snap.get('sector', '?')} / {snap.get('industry', '?')}
Market cap: ${(snap.get('mcap', 0) or 0)/1e9:.1f}B
F/K (TTM): {pe:.1f}
Rev growth (TTM): {rev_g:+.1f}%
Op margin: {op_m:.1f}%
FCF margin: {fcf_m:.1f}%
ROE: {roe:.1f}%
ROIC: {roic:.1f}%

═══ MAKRO REJIM ═══
{regime.get('detay', 'rejim verisi yok')}
Regime carpani: {regime.get('multiplier', 1.0)}

═══ SORU ═══
Bu hissede yapisal rejim degisikligi var mi? Mid-cycle metodlari haksiz lowball
yapiyor mu? Bear/Base/Bull senaryolarda gercek hedef fiyat ne olur?
Framework'a katiliyor musun yoksa duzeltme gerekli mi?

Cevabini SADECE JSON formatinda ver."""


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
    if not ANTHROPIC_KEY:
        if verbose:
            print("[ai_consultant] ANTHROPIC_API_KEY tanımsız, atlandı")
        return None

    try:
        import anthropic
    except ImportError:
        if verbose:
            print("[ai_consultant] anthropic paketi yok, atlandı")
        return None

    user_prompt = _build_user_prompt(framework_result)

    t0 = time.time()
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY, timeout=CLAUDE_VALUATION_TIMEOUT)
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        duration_ms = int((time.time() - t0) * 1000)
        raw = "".join(b.text for b in msg.content if hasattr(b, "text"))

        # Observability
        try:
            log_claude_call(
                mode="valuation_consult",
                model=CLAUDE_MODEL,
                input_tokens=msg.usage.input_tokens if hasattr(msg, "usage") else 0,
                output_tokens=msg.usage.output_tokens if hasattr(msg, "usage") else 0,
                duration_ms=duration_ms,
                metadata={"ticker": framework_result.get("ticker"), "severity": severity},
            )
        except Exception:
            pass

    except Exception as e:
        if verbose:
            print(f"[ai_consultant] Claude API hatası: {e}")
        return None

    parsed = _parse_json_response(raw)
    if not parsed:
        if verbose:
            print(f"[ai_consultant] JSON parse başarısız:\n{raw[:300]}")
        return None

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
