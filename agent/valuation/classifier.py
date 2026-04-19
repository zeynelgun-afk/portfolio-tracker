"""
Finzora Valuation Framework v5 — Classifier
============================================
Bir ticker için FMP profile + ratios-ttm + growth verilerine bakarak
hangi arketipe ait olduğunu belirler. Detection precedence:
1. Sektör-zorunlu (REIT/Bank/Insurance) — FMP industry name
2. Growth + margin + market cap bantlarıyla disambiguation
3. Fallback: generic_equity
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


def _safe(v, default=0):
    try:
        f = float(v) if v is not None else default
        return f
    except (ValueError, TypeError):
        return default


def classify(ticker: str, verbose: bool = False) -> dict:
    """
    Bir ticker'ı arketipine sınıflandır.

    Returns:
        {
            "ticker": str,
            "archetype": str,           # örn "hyper_growth_semi"
            "confidence": float,        # 0-1, sınıflandırma güveni
            "signals": dict,            # hangi sinyal neyi tetikledi
            "fmp_raw": dict,            # FMP'den çekilen ham veri
            "fallback_used": bool
        }
    """
    signals = {}
    fmp_raw = {}

    # ── 1. Profile (sektör, industry, mcap, beta) ────────────────────
    profile = fmp_get("profile", {"symbol": ticker}) or []
    if not profile:
        return {
            "ticker": ticker,
            "archetype": "generic_equity",
            "confidence": 0.1,
            "signals": {"error": "profile not found"},
            "fmp_raw": {},
            "fallback_used": True,
        }
    p = profile[0]
    sector   = (p.get("sector") or "").strip()
    industry = (p.get("industry") or "").strip()
    mcap     = _safe(p.get("marketCap") or p.get("mktCap"))
    beta     = _safe(p.get("beta"))
    fmp_raw["profile"] = {
        "sector": sector, "industry": industry, "marketCap": mcap, "beta": beta,
    }

    # ── 2. Ratios TTM ────────────────────────────────────────────────
    ratios = fmp_get("ratios-ttm", {"symbol": ticker}) or []
    r = ratios[0] if ratios else {}
    fmp_raw["ratios"] = {
        "pe":     _safe(r.get("priceToEarningsRatioTTM")),
        "pb":     _safe(r.get("priceToBookRatioTTM")),
        "de":     _safe(r.get("debtToEquityRatioTTM")),
        "div_y":  _safe(r.get("dividendYieldTTM")),
        "roe":    _safe(r.get("returnOnEquityTTM")),
    }

    # ── 3. Key Metrics TTM ───────────────────────────────────────────
    metrics = fmp_get("key-metrics-ttm", {"symbol": ticker}) or []
    m = metrics[0] if metrics else {}
    fmp_raw["metrics"] = {
        "roic":       _safe(m.get("returnOnInvestedCapitalTTM")),
        "fcf_yield":  _safe(m.get("freeCashFlowYieldTTM")),
    }

    # ── 4. Income statement (revenue, op margin, R&D, SBC) ───────────
    inc4q = fmp_get("income-statement", {"symbol": ticker, "period": "quarter", "limit": 4}) or []
    inc_ann2 = fmp_get("income-statement", {"symbol": ticker, "period": "annual", "limit": 2}) or []

    ttm_rev = sum(_safe(q.get("revenue")) for q in inc4q)
    ttm_ebit = sum(_safe(q.get("operatingIncome")) for q in inc4q)
    ttm_rd = sum(_safe(q.get("researchAndDevelopmentExpenses")) for q in inc4q)
    ttm_ni = sum(_safe(q.get("netIncome")) for q in inc4q)

    op_margin   = (ttm_ebit / ttm_rev) if ttm_rev > 0 else 0
    rd_intensity = (ttm_rd / ttm_rev) if ttm_rev > 0 else 0

    # Revenue growth: last 2 annual
    rev_growth = 0
    if len(inc_ann2) >= 2:
        curr_rev = _safe(inc_ann2[0].get("revenue"))
        prev_rev = _safe(inc_ann2[1].get("revenue"))
        if prev_rev > 0:
            rev_growth = (curr_rev / prev_rev) - 1.0

    fmp_raw["income"] = {
        "ttm_revenue":   ttm_rev,
        "op_margin":     op_margin,
        "rd_intensity":  rd_intensity,
        "rev_growth":    rev_growth,
        "ttm_ni":        ttm_ni,
    }

    # ── 5. Cash flow (FCF, SBC) ──────────────────────────────────────
    cf4q = fmp_get("cash-flow-statement", {"symbol": ticker, "period": "quarter", "limit": 4}) or []
    ttm_fcf = sum(_safe(q.get("freeCashFlow")) for q in cf4q)
    ttm_sbc = sum(_safe(q.get("stockBasedCompensation")) for q in cf4q)

    fcf_margin = (ttm_fcf / ttm_rev) if ttm_rev > 0 else 0
    sbc_intensity = (ttm_sbc / ttm_rev) if ttm_rev > 0 else 0
    fmp_raw["cashflow"] = {
        "ttm_fcf": ttm_fcf, "fcf_margin": fcf_margin,
        "sbc_intensity": sbc_intensity,
    }

    # ── 6. Balance sheet (total assets, tangible equity) ─────────────
    bal = fmp_get("balance-sheet-statement", {"symbol": ticker, "period": "quarter", "limit": 1}) or []
    b = bal[0] if bal else {}
    total_assets = _safe(b.get("totalAssets"))
    fmp_raw["balance"] = {"totalAssets": total_assets}

    # ═════════════════════════════════════════════════════════════════
    # DETECTION LOGIC (öncelik sırasıyla)
    # ═════════════════════════════════════════════════════════════════

    signals["industry"] = industry
    signals["sector"] = sector

    industry_lc = industry.lower()
    sector_lc = sector.lower()

    # ── PRIORITY 1: REIT / Bank / Insurance (sektör-zorunlu) ─────────

    if "reit" in industry_lc or "reit" in sector_lc:
        # REIT alt türleri
        if "mortgage" in industry_lc:
            signals["trigger"] = "industry contains REIT + Mortgage"
            return _result(ticker, "reit_mortgage", 0.95, signals, fmp_raw)

        if any(x in industry_lc for x in ["retail", "net lease", "triple net"]):
            signals["trigger"] = "industry = REIT retail/net-lease"
            return _result(ticker, "reit_net_lease", 0.90, signals, fmp_raw)

        signals["trigger"] = f"REIT (equity) — industry: {industry}"
        return _result(ticker, "reit_equity", 0.90, signals, fmp_raw)

    if "bank" in industry_lc or sector_lc in ("financial services",) and "bank" in industry_lc:
        # Büyüklük ile money-center vs regional
        if total_assets > 500_000_000_000:
            signals["trigger"] = f"Bank + total assets >$500B ({total_assets/1e9:.0f}B)"
            return _result(ticker, "money_center_bank", 0.95, signals, fmp_raw)
        elif total_assets > 10_000_000_000:
            signals["trigger"] = f"Bank + regional ({total_assets/1e9:.0f}B)"
            return _result(ticker, "regional_bank", 0.90, signals, fmp_raw)
        else:
            signals["trigger"] = "Bank, small"
            return _result(ticker, "regional_bank", 0.75, signals, fmp_raw)

    if "insurance" in industry_lc:
        if "life" in industry_lc:
            signals["trigger"] = "Insurance Life"
            return _result(ticker, "insurer_life", 0.90, signals, fmp_raw)
        signals["trigger"] = f"Insurance P&C: {industry}"
        return _result(ticker, "insurer_pc", 0.85, signals, fmp_raw)

    if any(x in industry_lc for x in ["asset management", "capital markets"]):
        signals["trigger"] = f"Asset mgmt / capital markets: {industry}"
        return _result(ticker, "asset_manager", 0.85, signals, fmp_raw)

    # ── PRIORITY 2: Utility / Energy / Pharma (sektör-zorunlu) ──────

    if "utilit" in sector_lc or "utilit" in industry_lc:
        signals["trigger"] = "Utility sector"
        return _result(ticker, "utility_regulated", 0.85, signals, fmp_raw)

    if sector_lc == "energy" or "oil" in industry_lc or "gas" in industry_lc:
        if "integrated" in industry_lc or "major" in industry_lc:
            signals["trigger"] = "Energy integrated (XOM-type)"
            return _result(ticker, "energy_integrated", 0.90, signals, fmp_raw)
        if any(x in industry_lc for x in ["pipeline", "midstream", "storage"]):
            signals["trigger"] = "Energy midstream"
            return _result(ticker, "energy_midstream", 0.90, signals, fmp_raw)
        if any(x in industry_lc for x in ["e&p", "exploration", "upstream"]):
            signals["trigger"] = "Energy E&P upstream"
            return _result(ticker, "energy_upstream_ep", 0.90, signals, fmp_raw)
        signals["trigger"] = f"Energy default: {industry}"
        return _result(ticker, "energy_integrated", 0.70, signals, fmp_raw)

    if "biotech" in industry_lc or "pharmac" in industry_lc or "drug" in industry_lc:
        # Ciro/mcap oranı ve karlılık ile ayır
        rev_mcap = (ttm_rev / mcap) if mcap > 0 else 0
        if ttm_rev < 100_000_000 or rev_mcap < 0.05:
            signals["trigger"] = f"Biotech preclinical (rev/mcap={rev_mcap:.3f})"
            return _result(ticker, "biotech_preclinical", 0.85, signals, fmp_raw)
        if op_margin > 0.15 and mcap > 10_000_000_000:
            signals["trigger"] = "Pharma big / commercial biotech profitable"
            if "biotech" in industry_lc:
                return _result(ticker, "biotech_commercial", 0.80, signals, fmp_raw)
            return _result(ticker, "pharma_big", 0.85, signals, fmp_raw)
        signals["trigger"] = f"Biotech/pharma generic: {industry}"
        return _result(ticker, "biotech_commercial", 0.70, signals, fmp_raw)

    # ── PRIORITY 3: Semiconductor ────────────────────────────────────

    if "semiconductor" in industry_lc or "semi" in industry_lc:
        if rev_growth > 0.60 and op_margin > 0.15:
            signals["trigger"] = f"Semi hyper-growth (rev_gr={rev_growth:.0%})"
            return _result(ticker, "hyper_growth_semi", 0.90, signals, fmp_raw)
        signals["trigger"] = f"Semi mature (rev_gr={rev_growth:.0%})"
        return _result(ticker, "mature_semi", 0.80, signals, fmp_raw)

    # ── PRIORITY 4: Software / Tech (growth + margin) ────────────────

    is_software = any(x in industry_lc for x in ["software", "internet", "cloud"]) or \
                  "technology" in sector_lc

    if is_software:
        # Dual-channel: PLTR gibi gov+commercial karışımı — yüksek SBC + yüksek büyüme
        if sbc_intensity > 0.15 and rev_growth > 0.30:
            signals["trigger"] = f"Dual-channel software (SBC={sbc_intensity:.0%}, gr={rev_growth:.0%})"
            return _result(ticker, "software_dual_channel", 0.75, signals, fmp_raw)

        # Hyper-growth: rev growth >40%, FCF margin <5% veya negatif
        if rev_growth > 0.40 and fcf_margin < 0.10 and rd_intensity > 0.15:
            signals["trigger"] = f"Hyper-growth software (gr={rev_growth:.0%}, fcf_m={fcf_margin:.0%})"
            return _result(ticker, "hyper_growth_software", 0.85, signals, fmp_raw)

        # Profitable growth: rev_gr 20-40%, FCF margin >15%
        if rev_growth > 0.20 and fcf_margin > 0.15 and op_margin > 0.20:
            signals["trigger"] = f"Profitable growth SW (gr={rev_growth:.0%}, fcf_m={fcf_margin:.0%})"
            return _result(ticker, "profitable_growth_software", 0.85, signals, fmp_raw)

        # Mature mega-cap tech: mcap >$500B, olgun
        if mcap > 500_000_000_000 and fcf_margin > 0.15:
            signals["trigger"] = f"Mega-cap mature tech (mcap=${mcap/1e9:.0f}B)"
            return _result(ticker, "mature_megacap_tech", 0.90, signals, fmp_raw)

        # Gaming (eğer industry gaming ise)
        if "gaming" in industry_lc or "entertainment" in industry_lc:
            signals["trigger"] = "Gaming interactive"
            return _result(ticker, "gaming_interactive", 0.80, signals, fmp_raw)

        # Fallback: profitable growth
        signals["trigger"] = "Software profitable growth fallback"
        return _result(ticker, "profitable_growth_software", 0.60, signals, fmp_raw)

    # ── PRIORITY 5: Auto (TSLA optionality check) ────────────────────

    if "auto" in industry_lc or "vehicle" in industry_lc:
        # Tesla benzeri — yüksek R&D veya yüksek P/S (narrative premium)
        ps = (mcap / ttm_rev) if ttm_rev > 0 else 0
        is_optionality = (
            (rd_intensity > 0.08 and mcap > 100_000_000_000) or
            (ps > 5.0 and mcap > 200_000_000_000)  # TSLA ~15x P/S vs peers ~0.5x
        )
        if is_optionality:
            signals["trigger"] = f"Auto + optionality (P/S={ps:.1f}, R&D={rd_intensity:.0%})"
            return _result(ticker, "auto_oem_plus_optionality", 0.80, signals, fmp_raw)
        signals["trigger"] = f"Auto OEM traditional (P/S={ps:.1f})"
        return _result(ticker, "auto_oem_traditional", 0.85, signals, fmp_raw)

    # ── PRIORITY 6: Consumer / Industrial / Materials ────────────────

    if "consumer defensive" in sector_lc or "staples" in industry_lc:
        signals["trigger"] = "Consumer staples"
        return _result(ticker, "consumer_staples_aristocrat", 0.80, signals, fmp_raw)

    if "consumer cyclical" in sector_lc or "consumer discretionary" in sector_lc:
        signals["trigger"] = "Consumer cyclical"
        return _result(ticker, "consumer_cyclical", 0.80, signals, fmp_raw)

    if "industrial" in sector_lc:
        signals["trigger"] = "Industrial cyclical"
        return _result(ticker, "industrial_cyclical", 0.75, signals, fmp_raw)

    if "basic materials" in sector_lc or "materials" in sector_lc:
        if any(x in industry_lc for x in ["gold", "silver", "copper", "metals", "mining"]):
            signals["trigger"] = "Mining commodity"
            return _result(ticker, "mining_commodity", 0.85, signals, fmp_raw)
        if "chemical" in industry_lc:
            signals["trigger"] = "Chemicals commodity"
            return _result(ticker, "chemicals_commodity", 0.80, signals, fmp_raw)
        signals["trigger"] = "Materials generic"
        return _result(ticker, "mining_commodity", 0.65, signals, fmp_raw)

    # ── PRIORITY 7: Telecom / Media ──────────────────────────────────

    if "telecom" in sector_lc or "telecom" in industry_lc:
        signals["trigger"] = "Telecom"
        return _result(ticker, "telecom", 0.85, signals, fmp_raw)

    if "media" in industry_lc or "entertainment" in industry_lc:
        signals["trigger"] = "Media traditional"
        return _result(ticker, "media_traditional", 0.75, signals, fmp_raw)

    # ── PRIORITY 8: Distressed / Decliner (final signals) ────────────

    if op_margin < -0.10 and rev_growth < 0:
        signals["trigger"] = f"Distressed (op={op_margin:.0%}, gr={rev_growth:.0%})"
        return _result(ticker, "turnaround_distressed", 0.70, signals, fmp_raw)

    if rev_growth < -0.05 and fmp_raw["ratios"]["div_y"] > 0.04:
        signals["trigger"] = f"Structural decliner (gr={rev_growth:.0%}, div={fmp_raw['ratios']['div_y']:.0%})"
        return _result(ticker, "structural_decliner", 0.65, signals, fmp_raw)

    # ── FALLBACK ─────────────────────────────────────────────────────

    signals["trigger"] = f"Fallback — sector={sector}, industry={industry}"
    return _result(ticker, "generic_equity", 0.40, signals, fmp_raw, fallback=True)


def _result(ticker: str, archetype: str, confidence: float,
            signals: dict, fmp_raw: dict, fallback: bool = False) -> dict:
    return {
        "ticker":         ticker,
        "archetype":      archetype,
        "confidence":     round(confidence, 2),
        "signals":        signals,
        "fmp_raw":        fmp_raw,
        "fallback_used":  fallback,
    }


if __name__ == "__main__":
    # Smoke test
    import json
    for t in ["ALAB", "MSFT", "JPM", "O", "XOM", "KO", "TSLA", "PLTR", "NVDA"]:
        r = classify(t)
        print(f"{t:6} → {r['archetype']:30} ({r['confidence']:.0%})")
        print(f"        {r['signals'].get('trigger', '?')}")
