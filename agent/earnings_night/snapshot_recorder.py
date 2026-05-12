"""
Pre-Earnings Snapshot Recorder

Bilanço öncesi (T-1) gün FMP'den çekilen veri:
- Analist hedef fiyatları (avg, high, low, median)
- Forward EPS / Revenue konsensüsü (FY+1)
- TTM diluted share count
- Pre-earnings YoY büyüme beklentisi
- Mevcut fiyat (snapshot anı)
- Sektör momentum skoru (manuel veya FMP sector-performance bazlı)

Çıktı: data/earnings_snapshots/{ticker}_{date}.json
Bilanço gecesi orchestrator bunu okuyup implied_multiple_valuation'a feed eder.

Kullanım:
    from agent.earnings_night.snapshot_recorder import record_snapshot
    snapshot = record_snapshot(ticker="GOOGL", fmp_key=FMP_KEY)
    # Otomatik kaydeder: data/earnings_snapshots/GOOGL_2026-04-28.json
"""
from __future__ import annotations
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests


FMP_BASE = "https://financialmodelingprep.com/stable"

# Sektör momentum manuel mapping (gelecekte FMP sector-performance bazlı otomatik)
SECTOR_MOMENTUM_MAP = {
    "Technology": 0.05,
    "Communication Services": 0.05,
    "Consumer Cyclical": 0.0,
    "Healthcare": 0.0,
    "Financial Services": 0.0,
    "Industrial": 0.0,
    "Consumer Defensive": -0.03,
    "Energy": -0.05,
    "Utilities": -0.05,
    "Real Estate": -0.05,
    "Basic Materials": -0.03,
}

# Tema bazlı override (AI/semis hot)
AI_TICKERS = {"NVDA", "AVGO", "AMD", "TSM", "ASML", "ANET", "ARM", "MRVL", "MU"}
AI_CLOUD_TICKERS = {"GOOGL", "GOOG", "MSFT", "AMZN", "META", "ORCL"}


def fmp_get(endpoint: str, fmp_key: str, **params) -> dict | list:
    """FMP API çağrısı (50ms throttle, basit retry)."""
    params["apikey"] = fmp_key
    r = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def estimate_sector_momentum(ticker: str, sector: str) -> float:
    """Ticker + sektör bazlı momentum tahmini (basit kural, gelecekte ML)."""
    if ticker in AI_TICKERS:
        return 0.10  # AI/semis hot
    if ticker in AI_CLOUD_TICKERS:
        return 0.10  # AI cloud da hot
    return SECTOR_MOMENTUM_MAP.get(sector, 0.0)


def record_snapshot(
    ticker: str,
    fmp_key: Optional[str] = None,
    output_dir: str = "data/earnings_snapshots",
    save: bool = True,
) -> dict:
    """
    T-1 günü pre-earnings snapshot kaydı.

    Args:
        ticker: Hisse sembolü
        fmp_key: FMP API key (yoksa env'den okur)
        output_dir: Çıktı klasörü
        save: True ise dosyaya yaz

    Returns:
        Snapshot dict (implied_multiple_valuation'a feed edilebilir)
    """
    fmp_key = fmp_key or os.environ.get("FMP_API_KEY") or "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"

    today = date.today().isoformat()

    # 1. Mevcut fiyat + market data
    quote_list = fmp_get("quote", fmp_key, symbol=ticker)
    if not quote_list:
        raise ValueError(f"FMP quote {ticker} için boş döndü")
    quote = quote_list[0]
    current_price = quote["price"]
    market_cap_b = round(quote.get("marketCap", 0) / 1e9, 2)

    # 2. Profile (sektör için)
    profile_list = fmp_get("profile", fmp_key, symbol=ticker)
    if not profile_list:
        raise ValueError(f"FMP profile {ticker} için boş döndü")
    profile = profile_list[0]
    sector = profile.get("sector", "Unknown")
    industry = profile.get("industry", "Unknown")

    # 3. Analist hedef fiyatları
    target_consensus = fmp_get("price-target-consensus", fmp_key, symbol=ticker)
    if isinstance(target_consensus, list) and target_consensus:
        target_consensus = target_consensus[0]
    elif isinstance(target_consensus, dict):
        pass
    else:
        target_consensus = {}

    target_avg = target_consensus.get("targetConsensus")
    target_high = target_consensus.get("targetHigh")
    target_low = target_consensus.get("targetLow")
    target_median = target_consensus.get("targetMedian")

    # 4. Analist estimates - FY+1 forward
    estimates = fmp_get("analyst-estimates", fmp_key, symbol=ticker, period="annual")
    current_year = datetime.now().year
    next_fy = str(current_year + 1)
    fy1_est = next((e for e in estimates if str(e.get("date", "")).startswith(next_fy)), None)
    if not fy1_est and estimates:
        # Fallback: ilk gelecek yıl
        fy1_est = next((e for e in estimates if e.get("date", "0000") > today), estimates[0])

    forward_eps = fy1_est.get("epsAvg") if fy1_est else None
    forward_revenue_b = (fy1_est.get("revenueAvg", 0) / 1e9) if fy1_est else None
    num_analysts = fy1_est.get("numAnalystsEps") if fy1_est else None

    # 5. Diluted shares (key-metrics-ttm + income-statement fallback)
    diluted_shares_m = None
    try:
        metrics = fmp_get("key-metrics-ttm", fmp_key, symbol=ticker)
        if isinstance(metrics, list) and metrics:
            metrics = metrics[0]
        else:
            metrics = {}
        for key in ["weightedAverageShsOutDilTTM", "dilutedSharesOutstandingTTM", "shareOutstandingDiluted"]:
            if key in metrics and metrics[key]:
                diluted_shares_m = metrics[key] / 1e6
                break
    except Exception:
        pass

    # Fallback: son çeyrek income-statement'ten diluted shares al
    if not diluted_shares_m:
        try:
            inc_q = fmp_get("income-statement", fmp_key, symbol=ticker, period="quarter", limit=1)
            if inc_q:
                # FMP'de "weightedAverageShsOutDil" raw sayı (Milyon değil, tam)
                for key in ["weightedAverageShsOutDil", "weightedAverageShsOutDiluted"]:
                    if key in inc_q[0] and inc_q[0][key]:
                        val = inc_q[0][key]
                        diluted_shares_m = val / 1e6 if val > 1e8 else val  # raw mi milyon mu otomatik tespit
                        break
        except Exception:
            pass

    forward_revenue_per_share = None
    if forward_revenue_b is not None and diluted_shares_m and diluted_shares_m > 0:
        forward_revenue_per_share = (forward_revenue_b * 1000) / diluted_shares_m

    # 6. Pre-earnings YoY büyüme beklentisi (FY+1 estimate vs FY actual)
    # Önceki yıl FY actual'ını al
    income = fmp_get("income-statement", fmp_key, symbol=ticker, period="annual", limit=2)
    expected_yoy = None
    if income and len(income) >= 1 and forward_revenue_b:
        last_fy_rev_b = income[0].get("revenue", 0) / 1e9
        if last_fy_rev_b > 0:
            expected_yoy = round((forward_revenue_b / last_fy_rev_b - 1) * 100, 2)

    # 7. Sektör momentum
    sector_momentum = estimate_sector_momentum(ticker, sector)

    # 8. Historical beat rate (son 4 çeyrek surprise ortalaması)
    earnings_calendar = fmp_get("earnings", fmp_key, symbol=ticker, limit=5)
    historical_beat = 5.0  # default
    if isinstance(earnings_calendar, list) and len(earnings_calendar) >= 1:
        surprises = []
        for e in earnings_calendar[:4]:
            actual = e.get("epsActual")
            estimated = e.get("epsEstimated")
            if actual and estimated and estimated > 0:
                surprises.append((actual - estimated) / abs(estimated) * 100)
        if surprises:
            historical_beat = round(sum(surprises) / len(surprises), 2)

    snapshot = {
        "ticker": ticker,
        "snapshot_date": today,
        "fiscal_period_next_report": "TBD",  # orchestrator dolduracak
        "company": {
            "name": profile.get("companyName"),
            "sector": sector,
            "industry": industry,
            "market_cap_b": market_cap_b,
        },
        "current_price": current_price,
        "analyst_targets": {
            "target_avg_pre": target_avg,
            "target_high_pre": target_high,
            "target_low_pre": target_low,
            "target_median_pre": target_median,
        },
        "forward_estimates": {
            "fiscal_year": fy1_est.get("date") if fy1_est else None,
            "forward_eps_pre": forward_eps,
            "forward_revenue_b_pre": forward_revenue_b,
            "forward_revenue_per_share_pre": (
                round(forward_revenue_per_share, 2) if forward_revenue_per_share else None
            ),
            "num_analysts": num_analysts,
            "expected_yoy_revenue_growth_pct": expected_yoy,
        },
        "share_count": {
            "diluted_shares_m": round(diluted_shares_m, 2) if diluted_shares_m else None,
        },
        "historical_beat_rate_pct": historical_beat,
        "sector_momentum_factor": sector_momentum,
        "_recorded_at": datetime.now().isoformat(),
    }

    if save:
        output_path = Path(output_dir) / f"{ticker}_{today}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

    return snapshot


def snapshot_to_valuation_inputs(snapshot: dict) -> dict:
    """
    Snapshot'ı implied_multiple_valuation()'a feed edilebilir format'a çevirir.
    """
    return {
        "pre_earnings_snapshot": {
            "target_avg_pre": snapshot["analyst_targets"]["target_avg_pre"],
            "target_high_pre": snapshot["analyst_targets"]["target_high_pre"],
            "forward_eps_pre": snapshot["forward_estimates"]["forward_eps_pre"],
            "forward_revenue_per_share_pre": snapshot["forward_estimates"]["forward_revenue_per_share_pre"],
            "expected_yoy_revenue_growth_pct": snapshot["forward_estimates"]["expected_yoy_revenue_growth_pct"],
        },
        "current_price": snapshot["current_price"],
        "analyst_fwd_eps_fy1": snapshot["forward_estimates"]["forward_eps_pre"],
        "analyst_fwd_revenue_fy1_b": snapshot["forward_estimates"]["forward_revenue_b_pre"],
        "sector_momentum_factor": snapshot["sector_momentum_factor"],
        "historical_beat_rate_pct": snapshot["historical_beat_rate_pct"],
    }


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "GOOGL"
    snap = record_snapshot(ticker)
    print(json.dumps(snap, indent=2, ensure_ascii=False))
