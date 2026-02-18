#!/usr/bin/env python3
"""FMP API Client - Stable Endpoints Only (tested & working)"""

import requests
import time
import os
from typing import Optional, List, Dict

FMP_BASE = "https://financialmodelingprep.com"

class FMPClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("FMP_API_KEY", "")
        self.call_count = 0
        self._last_call = 0

    def _get(self, endpoint: str, params: dict = None) -> Optional[any]:
        elapsed = time.time() - self._last_call
        if elapsed < 0.35:
            time.sleep(0.35 - elapsed)
        self._last_call = time.time()
        if params is None:
            params = {}
        params["apikey"] = self.api_key
        try:
            resp = requests.get(f"{FMP_BASE}{endpoint}", params=params, timeout=15)
            self.call_count += 1
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) == 0:
                    return None
                if isinstance(data, dict) and "Error" in str(data):
                    return None
                return data
            return None
        except Exception as e:
            print(f"  ❌ API Error: {e}")
            return None

    def quote(self, symbol: str) -> Optional[Dict]:
        data = self._get("/stable/quote", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None

    def profile(self, symbol: str) -> Optional[Dict]:
        data = self._get("/stable/profile", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None

    def income_statement(self, symbol: str, period="quarter", limit=8) -> Optional[List]:
        return self._get("/stable/income-statement", {
            "symbol": symbol, "period": period, "limit": limit
        })

    def financial_growth(self, symbol: str, period="quarter", limit=4) -> Optional[List]:
        return self._get("/stable/financial-growth", {
            "symbol": symbol, "period": period, "limit": limit
        })

    def ratios_ttm(self, symbol: str) -> Optional[Dict]:
        data = self._get("/stable/ratios-ttm", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None

    def key_metrics_ttm(self, symbol: str) -> Optional[Dict]:
        data = self._get("/stable/key-metrics-ttm", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None

    def analyst_estimates(self, symbol: str, limit=4) -> Optional[List]:
        return self._get("/stable/analyst-estimates", {
            "symbol": symbol, "period": "quarter", "limit": limit
        })
