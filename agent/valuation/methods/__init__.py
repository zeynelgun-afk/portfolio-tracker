"""
Finzora Valuation Framework v5 — Data Fetcher
===============================================
Tüm valuation metotlarının ortak kullandığı FMP veri toplayıcı.
Bir ticker için GEREKLİ tüm veriyi bir kez çeker, methodlara geçirir.

Çağrı maliyeti (~9 FMP call/ticker):
- profile, ratios-ttm, key-metrics-ttm
- income-statement (annual 3 + quarter 8)
- balance-sheet-statement (quarter 4)
- cash-flow-statement (quarter 8)
- analyst-estimates (annual)
- earnings (surprises)
- treasury-rates
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
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


def _safe(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def fetch_all_data(ticker: str) -> dict:
    """
    Bir ticker için tüm valuation data'yı topla.
    Returns: büyük dict, methodlar burdan okuyacak.
    """
    d = {"ticker": ticker}

    # 1. Quote + profile
    q = fmp_get("quote", {"symbol": ticker}) or []
    q = q[0] if q else {}
    p = fmp_get("profile", {"symbol": ticker}) or []
    p = p[0] if p else {}
    d["price"]     = _safe(q.get("price"))
    d["prev_close"] = _safe(q.get("previousClose"))
    d["mcap"]      = _safe(q.get("marketCap"), _safe(p.get("marketCap") or p.get("mktCap")))
    d["shares"]    = _safe(q.get("sharesOutstanding"), d["mcap"] / d["price"] if d["price"] else 0)
    d["beta"]      = _safe(p.get("beta"), 1.0)
    d["sector"]    = (p.get("sector") or "").strip()
    d["industry"]  = (p.get("industry") or "").strip()

    # 2. Ratios-TTM (KRİTİK alan isimleri!)
    r = fmp_get("ratios-ttm", {"symbol": ticker}) or []
    r = r[0] if r else {}
    d["pe_ttm"]      = _safe(r.get("priceToEarningsRatioTTM"))
    d["pb"]          = _safe(r.get("priceToBookRatioTTM"))
    d["de"]          = _safe(r.get("debtToEquityRatioTTM"))
    d["div_yield"]   = _safe(r.get("dividendYieldTTM"))
    d["payout_ratio"] = _safe(r.get("dividendPayoutRatioTTM"))
    d["roe"]         = _safe(r.get("returnOnEquityTTM"))
    d["eps_ttm"]     = _safe(r.get("netIncomePerShareTTM"))
    d["bvps"]        = _safe(r.get("bookValuePerShareTTM"))
    d["fcf_ps"]      = _safe(r.get("freeCashFlowPerShareTTM"))
    d["peg_fmp"]     = _safe(r.get("priceToEarningsGrowthRatioTTM"))
    d["fwd_peg"]     = _safe(r.get("forwardPriceToEarningsGrowthRatioTTM"))

    # 3. Key metrics TTM
    m = fmp_get("key-metrics-ttm", {"symbol": ticker}) or []
    m = m[0] if m else {}
    d["ev"]         = _safe(m.get("enterpriseValueTTM"))
    d["roic"]       = _safe(m.get("returnOnInvestedCapitalTTM"))
    d["fcf_yield"]  = _safe(m.get("freeCashFlowYieldTTM"))
    d["tangible_bvps"] = _safe(m.get("tangibleBookValuePerShareTTM"))
    d["graham"]     = _safe(m.get("grahamNumberTTM"))

    # 4. Income statement (annual x3 + quarter x8)
    inc_ann = fmp_get("income-statement", {"symbol": ticker, "period": "annual", "limit": 3}) or []
    inc_q   = fmp_get("income-statement", {"symbol": ticker, "period": "quarter", "limit": 8}) or []

    # Annual series
    d["rev_annual"] = [_safe(x.get("revenue")) for x in inc_ann]
    d["ebit_annual"] = [_safe(x.get("operatingIncome")) for x in inc_ann]
    d["ebitda_annual"] = [_safe(x.get("ebitda")) for x in inc_ann]
    d["ni_annual"] = [_safe(x.get("netIncome")) for x in inc_ann]
    d["eps_annual"] = [_safe(x.get("eps")) for x in inc_ann]
    d["rd_annual"] = [_safe(x.get("researchAndDevelopmentExpenses")) for x in inc_ann]

    # TTM (quarterly sum)
    d["ttm_rev"]    = sum(_safe(x.get("revenue")) for x in inc_q[:4])
    d["ttm_ebit"]   = sum(_safe(x.get("operatingIncome")) for x in inc_q[:4])
    d["ttm_ebitda"] = sum(_safe(x.get("ebitda")) for x in inc_q[:4])
    d["ttm_ni"]     = sum(_safe(x.get("netIncome")) for x in inc_q[:4])
    d["ttm_rd"]     = sum(_safe(x.get("researchAndDevelopmentExpenses")) for x in inc_q[:4])

    # Previous TTM
    d["prev_ttm_rev"] = sum(_safe(x.get("revenue")) for x in inc_q[4:8])
    d["prev_ttm_ni"]  = sum(_safe(x.get("netIncome")) for x in inc_q[4:8])

    # Büyüme oranları
    d["rev_growth_ttm"] = ((d["ttm_rev"] / d["prev_ttm_rev"]) - 1.0) if d["prev_ttm_rev"] > 0 else 0
    d["eps_growth_ttm"] = ((d["ttm_ni"] / d["prev_ttm_ni"]) - 1.0) if d["prev_ttm_ni"] > 0 else 0

    # Marjlar
    d["op_margin"]  = (d["ttm_ebit"] / d["ttm_rev"]) if d["ttm_rev"] > 0 else 0
    d["net_margin"] = (d["ttm_ni"] / d["ttm_rev"]) if d["ttm_rev"] > 0 else 0
    d["rd_intensity"] = (d["ttm_rd"] / d["ttm_rev"]) if d["ttm_rev"] > 0 else 0

    # 5. Cash flow (quarter x8 TTM + previous)
    cf_q = fmp_get("cash-flow-statement", {"symbol": ticker, "period": "quarter", "limit": 8}) or []
    d["ttm_fcf"]    = sum(_safe(x.get("freeCashFlow")) for x in cf_q[:4])
    d["ttm_ocf"]    = sum(_safe(x.get("operatingCashFlow")) for x in cf_q[:4])
    d["ttm_capex"]  = sum(_safe(x.get("capitalExpenditure")) for x in cf_q[:4])
    d["ttm_sbc"]    = sum(_safe(x.get("stockBasedCompensation")) for x in cf_q[:4])
    d["ttm_depam"]  = sum(_safe(x.get("depreciationAndAmortization")) for x in cf_q[:4])
    d["prev_ttm_fcf"] = sum(_safe(x.get("freeCashFlow")) for x in cf_q[4:8])

    d["fcf_margin"]    = (d["ttm_fcf"] / d["ttm_rev"]) if d["ttm_rev"] > 0 else 0
    d["sbc_intensity"] = (d["ttm_sbc"] / d["ttm_rev"]) if d["ttm_rev"] > 0 else 0
    d["fcf_adjusted_sbc"] = d["ttm_fcf"] - d["ttm_sbc"]  # SBC cash expense olarak düş

    # 6. Balance sheet
    bal = fmp_get("balance-sheet-statement", {"symbol": ticker, "period": "quarter", "limit": 1}) or []
    b = bal[0] if bal else {}
    d["cash"]         = _safe(b.get("cashAndCashEquivalents")) + _safe(b.get("shortTermInvestments"))
    d["total_debt"]   = _safe(b.get("totalDebt"))
    d["net_debt"]     = d["total_debt"] - d["cash"]
    d["total_assets"] = _safe(b.get("totalAssets"))
    d["total_equity"] = _safe(b.get("totalStockholdersEquity"))
    d["tangible_equity"] = _safe(b.get("tangibleAssetValue")) or (
        _safe(b.get("totalStockholdersEquity")) -
        _safe(b.get("goodwillAndIntangibleAssets"))
    )

    # 7. Analyst estimates (forward EPS / revenue)
    est = fmp_get("analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 5}) or []
    # FMP "epsAvg" alanı (eski "estimatedEpsAvg" DEĞİL, yeni API'da epsAvg)
    d["est_annual"] = []
    for e in est:
        d["est_annual"].append({
            "date":    e.get("date"),
            "eps_avg": _safe(e.get("epsAvg") or e.get("estimatedEpsAvg")),
            "eps_high": _safe(e.get("epsHigh") or e.get("estimatedEpsHigh")),
            "eps_low":  _safe(e.get("epsLow") or e.get("estimatedEpsLow")),
            "rev_avg": _safe(e.get("revenueAvg") or e.get("estimatedRevenueAvg")),
            "num_analysts": int(_safe(e.get("numberAnalystsEstimatedEps"), 0)),
        })

    # 7b. Analyst price target consensus (reality check)
    pt = fmp_get("price-target-consensus", {"symbol": ticker}) or []
    pt = pt[0] if pt else {}
    d["analyst_target_high"]      = _safe(pt.get("targetHigh"))
    d["analyst_target_low"]       = _safe(pt.get("targetLow"))
    d["analyst_target_consensus"] = _safe(pt.get("targetConsensus"))
    d["analyst_target_median"]    = _safe(pt.get("targetMedian"))

    # Forward EPS 1Y, 2Y, 3Y (sırala, bugünden sonrakiler)
    from datetime import datetime
    today = datetime.now()
    future_est = [e for e in d["est_annual"] if e["date"] and e["date"] > today.strftime("%Y-%m-%d")]
    future_est.sort(key=lambda x: x["date"])
    d["fwd_eps_ny1"] = future_est[0]["eps_avg"] if len(future_est) >= 1 else 0
    d["fwd_eps_ny2"] = future_est[1]["eps_avg"] if len(future_est) >= 2 else 0
    d["fwd_eps_ny3"] = future_est[2]["eps_avg"] if len(future_est) >= 3 else 0
    d["fwd_rev_ny1"] = future_est[0]["rev_avg"] if len(future_est) >= 1 else 0
    d["fwd_rev_ny2"] = future_est[1]["rev_avg"] if len(future_est) >= 2 else 0
    d["analyst_count"] = future_est[0]["num_analysts"] if future_est else 0

    # 8. Treasury rate (10Y)
    from datetime import datetime, timedelta
    today_s = datetime.now().strftime("%Y-%m-%d")
    tr_from = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    tr = fmp_get("treasury-rates", {"from": tr_from, "to": today_s}) or []
    d["bond_y"] = _safe(tr[0].get("year10")) if tr else 4.5

    # 9. Türetilmiş alanlar
    d["ev_ebitda"]   = (d["ev"] / d["ttm_ebitda"]) if d["ttm_ebitda"] > 0 else 0
    d["ev_rev"]      = (d["ev"] / d["ttm_rev"]) if d["ttm_rev"] > 0 else 0
    d["fwd_pe_ny1"]  = (d["price"] / d["fwd_eps_ny1"]) if d["fwd_eps_ny1"] > 0 else 0
    d["fwd_pe_ny2"]  = (d["price"] / d["fwd_eps_ny2"]) if d["fwd_eps_ny2"] > 0 else 0
    d["net_income_margin"] = d["net_margin"]

    # 10. Fallback hesaplamalar — FMP boş dönebilir
    # ROE fallback: NI / Equity
    if d["roe"] <= 0 and d["ttm_ni"] > 0 and d["total_equity"] > 0:
        d["roe"] = d["ttm_ni"] / d["total_equity"]

    # Tangible BVPS fallback
    if d["tangible_bvps"] <= 0 and d["shares"] > 0:
        # Approximate: BVPS * 0.82 (bankalar için ~%18 goodwill avg)
        d["tangible_bvps"] = d["bvps"] * 0.82

    # ROIC fallback: NI / (Equity + Debt)
    if d["roic"] <= 0 and d["ttm_ni"] > 0:
        invested = d["total_equity"] + d["total_debt"]
        if invested > 0:
            d["roic"] = d["ttm_ni"] / invested

    # FCF yield fallback: FCF / MCap
    if d["fcf_yield"] <= 0 and d["ttm_fcf"] > 0 and d["mcap"] > 0:
        d["fcf_yield"] = d["ttm_fcf"] / d["mcap"]

    return d
