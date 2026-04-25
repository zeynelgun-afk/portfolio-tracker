"""
Finzora Valuation Framework v6 — Cycle Phase Detector
=======================================================
Siklik sektörlerde (yarı iletken, enerji, otomotiv, materials) cycle aşamasını
tespit eder. Mid-cycle metodları için ağırlık ayarlaması üretir.

Phase sınıflandırması:
  - bottom: Sektör momentum -, multiple sıkışmış, EPS dip
  - early:  Sektör momentum yeni +, multiple normalize, EPS toparlanma
  - mid:    Sektör momentum +, multiple ortalama, EPS büyümede
  - late:   Sektör momentum +++, multiple yüksek, EPS peak yaklaşımı
  - peak:   Sektör momentum yavaşlama, multiple aşırı, EPS peak
  - reset:  Geçiş — yapısal rejim değişikliği (mid-cycle metod ağırlığı düşürülmeli)

Sinyaller:
  1. Sektör SPDR ETF / SPY oranı (6 ay momentum)
  2. TTM EPS growth (yüksek growth = late, negatif = bottom)
  3. Forward EPS revision direction (yukarı = early/mid, aşağı = late/peak)
  4. Capex intensity trend (yükseliyor = mid → late)

Output:
  - phase: str
  - confidence: 0-1
  - mid_cycle_weight_modifier: -0.50 ile +0.30 arası
    (negatif = mid-cycle metodlarının ağırlığını düşür)
  - growth_weight_modifier: -0.30 ile +0.50 arası
    (pozitif = growth-adjusted metodların ağırlığını artır)

Tasarım: 2026-04-25 — v6 framework eklenti
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

try:
    from fmp_client import fmp_get
except ImportError:
    import requests
    FMP_KEY = os.environ.get("FMP_API_KEY", "")
    FMP_BASE = "https://financialmodelingprep.com/stable"

    def fmp_get(endpoint, params=None):
        p = (params or {}); p["apikey"] = FMP_KEY
        try:
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
            return r.json()
        except Exception:
            return None


# Sektör → SPDR ETF eşlemesi
SECTOR_ETF = {
    "Technology": "XLK",
    "Energy": "XLE",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Consumer Cyclical": "XLY",
    "Consumer Discretionary": "XLY",
    "Consumer Defensive": "XLP",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Materials": "XLB",
    "Communication Services": "XLC",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
}

# Industry → daha spesifik ETF (semiconductor için SOXX, vs.)
INDUSTRY_ETF = {
    "Semiconductors": "SOXX",
    "Semiconductor Equipment & Materials": "SOXX",
    "Oil & Gas E&P": "XOP",
    "Oil & Gas Refining & Marketing": "XOP",
    "Banks - Diversified": "KBE",
    "Banks - Regional": "KRE",
    "Biotechnology": "XBI",
    "Pharmaceutical Retailers": "XPH",
}

# Cycle = True olan sektörler (mid-cycle ayarı uygulanır)
CYCLICAL_SECTORS = {
    "Energy", "Basic Materials", "Materials",
    "Industrials", "Consumer Cyclical", "Consumer Discretionary",
    "Financials", "Real Estate",
}

CYCLICAL_INDUSTRIES = {
    "Semiconductors", "Semiconductor Equipment & Materials",
    "Auto Manufacturers", "Auto Parts",
    "Steel", "Copper", "Aluminum", "Gold", "Silver",
    "Oil & Gas E&P", "Oil & Gas Integrated", "Oil & Gas Drilling",
    "Memory", "Storage Hardware",  # MU/STX için
}

# Yapısal rejim olası sektör+industry kombinasyonları
# (mid-cycle metodları lowball yapma riski yüksek)
STRUCTURAL_REGIME_CANDIDATES = {
    # AI/HBM yarı iletken — 2023-2026+
    ("Technology", "Semiconductors"): "ai_memory_or_compute",
    # GLP-1 ilaç — 2023-2026+
    ("Health Care", "Drug Manufacturers - General"): "glp1_or_specialty",
    # EV/battery — 2020-2026
    ("Consumer Cyclical", "Auto Manufacturers"): "ev_transition",
    # Cloud infrastructure
    ("Technology", "Software - Infrastructure"): "ai_infrastructure",
}


def _safe(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _get_etf_for_ticker(sector: str, industry: str) -> str | None:
    """Sektör/industry'ye göre en uygun benchmark ETF."""
    if industry and industry in INDUSTRY_ETF:
        return INDUSTRY_ETF[industry]
    if sector in SECTOR_ETF:
        return SECTOR_ETF[sector]
    return None


def _sector_momentum_6m(etf_symbol: str) -> tuple[float, float]:
    """
    Son 6 ay sektör ETF / SPY relatif performans.
    Returns: (etf_return_pct, relative_pct)
    """
    try:
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        from_d = (datetime.now() - timedelta(days=190)).strftime("%Y-%m-%d")

        # ETF
        etf_hist = fmp_get("historical-price-eod/full",
                           {"symbol": etf_symbol, "from": from_d, "to": today}) or []
        spy_hist = fmp_get("historical-price-eod/full",
                           {"symbol": "SPY", "from": from_d, "to": today}) or []

        if not etf_hist or not spy_hist:
            return 0.0, 0.0

        # FMP plain list döner (eski "historical" key yok)
        etf_curr = _safe(etf_hist[0].get("close")) if etf_hist else 0
        etf_old = _safe(etf_hist[-1].get("close")) if len(etf_hist) > 100 else 0
        spy_curr = _safe(spy_hist[0].get("close")) if spy_hist else 0
        spy_old = _safe(spy_hist[-1].get("close")) if len(spy_hist) > 100 else 0

        if etf_old > 0 and spy_old > 0:
            etf_ret = (etf_curr / etf_old - 1) * 100
            spy_ret = (spy_curr / spy_old - 1) * 100
            return etf_ret, etf_ret - spy_ret
    except Exception:
        pass
    return 0.0, 0.0


def detect_cycle_phase(data: dict, archetype: str = "") -> dict:
    """
    Bir hisse için cycle phase tespiti yap.

    Args:
        data: methods.fetch_all_data() çıktısı
        archetype: classifier sonucu

    Returns:
        {
          "is_cyclical": bool,
          "phase": str,                    # bottom/early/mid/late/peak/reset/n/a
          "confidence": float,             # 0-1
          "structural_regime_suspect": bool,
          "structural_regime_type": str | None,
          "mid_cycle_weight_modifier": float,   # -0.50 to +0.30
          "growth_weight_modifier": float,      # -0.30 to +0.50
          "signals": dict,
          "rationale": str,
        }
    """
    sector = data.get("sector", "")
    industry = data.get("industry", "")

    is_cyclical = (
        sector in CYCLICAL_SECTORS or
        industry in CYCLICAL_INDUSTRIES or
        "cyclical" in archetype.lower() or
        "semi" in archetype.lower() or
        "energy" in archetype.lower()
    )

    if not is_cyclical:
        return {
            "is_cyclical": False,
            "phase": "n/a",
            "confidence": 1.0,
            "structural_regime_suspect": False,
            "structural_regime_type": None,
            "mid_cycle_weight_modifier": 0.0,
            "growth_weight_modifier": 0.0,
            "signals": {},
            "rationale": "non-cyclical sector, cycle ayarı uygulanmaz",
        }

    # Sinyaller
    rev_g = (data.get("rev_growth_ttm") or 0) * 100
    eps_g = (data.get("eps_growth_ttm") or 0) * 100
    op_margin = (data.get("op_margin") or 0) * 100
    fcf_margin = (data.get("fcf_margin") or 0) * 100
    pe_ttm = data.get("pe_ttm") or 0
    fwd_pe = data.get("fwd_pe_ny1") or 0

    # Forward EPS revision: ny2 / ny1 ratio
    fwd_eps_1 = data.get("fwd_eps_ny1") or 0
    fwd_eps_2 = data.get("fwd_eps_ny2") or 0
    eps_growth_fwd = ((fwd_eps_2 / fwd_eps_1) - 1) * 100 if fwd_eps_1 > 0 else 0

    # Sektör momentum
    etf = _get_etf_for_ticker(sector, industry)
    sector_ret, rel_perf = _sector_momentum_6m(etf) if etf else (0, 0)

    signals = {
        "rev_growth_ttm_pct": round(rev_g, 1),
        "eps_growth_ttm_pct": round(eps_g, 1),
        "op_margin_pct": round(op_margin, 1),
        "fcf_margin_pct": round(fcf_margin, 1),
        "pe_ttm": round(pe_ttm, 1),
        "fwd_pe": round(fwd_pe, 1),
        "fwd_eps_growth_pct": round(eps_growth_fwd, 1),
        "sector_etf": etf,
        "sector_6m_return_pct": round(sector_ret, 1),
        "sector_relative_to_spy_pct": round(rel_perf, 1),
    }

    # Yapısal rejim adayı mı?
    structural_key = (sector, industry)
    structural_suspect = False
    structural_type = None

    if structural_key in STRUCTURAL_REGIME_CANDIDATES:
        # Yapısal aday — ek olarak büyüme + marj seviyesine bak
        if rev_g > 25 and op_margin > 25:
            structural_suspect = True
            structural_type = STRUCTURAL_REGIME_CANDIDATES[structural_key]

    # Phase tespiti — basit kural seti
    phase = "mid"
    confidence = 0.5

    # Bottom: rev/eps growth negatif, sektör underperform
    if rev_g < -10 and eps_g < -25 and rel_perf < -10:
        phase = "bottom"
        confidence = 0.7
    # Early: rev henüz toparlıyor, sektör rotation yeni başlamış
    elif rev_g > 0 and rev_g < 15 and rel_perf > 0 and rel_perf < 10 and eps_g > -15:
        phase = "early"
        confidence = 0.6
    # Late: yüksek growth + sektör overperform + multiple aşırı
    elif rev_g > 30 and rel_perf > 15 and pe_ttm > 30:
        phase = "late"
        confidence = 0.65
    # Peak: çok yüksek growth + sektör çok overperform + forward revision yavaşlıyor
    elif rev_g > 40 and rel_perf > 20 and eps_growth_fwd < 5:
        phase = "peak"
        confidence = 0.7
    # Mid: normal aralık
    elif 5 < rev_g < 30 and -5 < rel_perf < 15:
        phase = "mid"
        confidence = 0.7

    # Reset durumu: yapısal rejim adayı + güçlü growth + güçlü margin
    # Mid-cycle metodları artık geçerli değil
    if structural_suspect and rev_g > 30 and op_margin > 30:
        phase = "reset"
        confidence = 0.55  # belirsizlik var

    # Ağırlık modifierları
    if phase == "bottom":
        # Mid-cycle metodları doğal kullanılır (cycle bottom'dayız, normalize değer ortaya çıkıyor)
        mid_mod = +0.10
        growth_mod = -0.10
    elif phase == "early":
        # Early stage: mid-cycle hala makul
        mid_mod = 0.0
        growth_mod = +0.10
    elif phase == "mid":
        # Mid: framework default
        mid_mod = 0.0
        growth_mod = 0.0
    elif phase == "late":
        # Late: mid-cycle hala önemli (mean reversion bekleyen aşama)
        mid_mod = +0.15
        growth_mod = -0.10
    elif phase == "peak":
        # Peak: mid-cycle ağırlığı maksimuma yakın, mean reversion bekleniyor
        mid_mod = +0.30
        growth_mod = -0.30
    elif phase == "reset":
        # Yapısal değişiklik şüphesi — mid-cycle ağırlığını ÇOK DÜŞÜR
        mid_mod = -0.50
        growth_mod = +0.50
    else:
        mid_mod = 0.0
        growth_mod = 0.0

    rationale_parts = [
        f"Sektör: {sector}/{industry}",
        f"Cycle phase: {phase} (güven {confidence:.0%})",
        f"Rev growth TTM: {rev_g:+.1f}%, Op margin: {op_margin:.1f}%",
        f"Sektör 6m: {sector_ret:+.1f}% (vs SPY {rel_perf:+.1f}%)",
    ]
    if structural_suspect:
        rationale_parts.append(f"⚠️ Yapısal rejim şüphesi: {structural_type}")

    return {
        "is_cyclical": True,
        "phase": phase,
        "confidence": round(confidence, 2),
        "structural_regime_suspect": structural_suspect,
        "structural_regime_type": structural_type,
        "mid_cycle_weight_modifier": mid_mod,
        "growth_weight_modifier": growth_mod,
        "signals": signals,
        "rationale": " | ".join(rationale_parts),
    }


# Mid-cycle metodlarını tanımlamak için — ağırlık modifier uygulanır
MID_CYCLE_METHODS = {
    "normalized_pe_midcycle",
    "normalized_pe_cyclical",
    "ev_ebitda_midcycle",
    "fcf_yield_midcycle",
    "price_to_book_capital_intensive",
}

# Growth-adjusted metodlar — pozitif modifier uygulanır
GROWTH_METHODS = {
    "peg_forward",
    "pegy",
    "forward_pe_ny1",
    "forward_pe_ny2",
    "ev_rev_growth_adjusted",
    "rule_of_40_multiple",
    "dcf_multi_stage_aggressive",
}


def adjust_method_weights(
    methods_used: list,
    cycle_info: dict
) -> tuple[list, dict]:
    """
    Cycle phase'e göre kullanılan metodların ağırlıklarını yeniden ayarla.

    Args:
        methods_used: framework'un kullandığı metodların listesi
        cycle_info: detect_cycle_phase() çıktısı

    Returns:
        (adjusted_methods, adjustment_log)
    """
    if not cycle_info.get("is_cyclical"):
        return methods_used, {"applied": False, "reason": "non-cyclical"}

    mid_mod = cycle_info.get("mid_cycle_weight_modifier", 0.0)
    growth_mod = cycle_info.get("growth_weight_modifier", 0.0)

    if abs(mid_mod) < 0.01 and abs(growth_mod) < 0.01:
        return methods_used, {"applied": False, "reason": "zero modifier"}

    adjusted = []
    log = {"applied": True, "phase": cycle_info["phase"], "changes": []}

    for m in methods_used:
        m_copy = dict(m)
        original_w = m_copy["weight"]
        new_w = original_w

        if m["name"] in MID_CYCLE_METHODS:
            # mid_mod > 0 → ağırlık artar, < 0 → azalır
            new_w = max(0.01, original_w * (1.0 + mid_mod))
        elif m["name"] in GROWTH_METHODS:
            new_w = max(0.01, original_w * (1.0 + growth_mod))

        m_copy["weight"] = new_w
        m_copy["original_weight"] = original_w

        if abs(new_w - original_w) > 0.001:
            log["changes"].append({
                "method": m["name"],
                "weight_before": round(original_w, 3),
                "weight_after": round(new_w, 3),
            })

        adjusted.append(m_copy)

    return adjusted, log


if __name__ == "__main__":
    # Test - MU varsayımı
    fake_data = {
        "sector": "Technology",
        "industry": "Semiconductors",
        "rev_growth_ttm": 0.57,
        "eps_growth_ttm": 1.20,
        "op_margin": 0.35,
        "fcf_margin": 0.20,
        "pe_ttm": 23.4,
        "fwd_pe_ny1": 12.0,
        "fwd_eps_ny1": 41.4,
        "fwd_eps_ny2": 50.0,
    }
    result = detect_cycle_phase(fake_data, archetype="mature_semi")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
