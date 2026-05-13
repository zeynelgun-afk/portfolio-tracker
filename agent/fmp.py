"""
FMP (Financial Modeling Prep) Stable API client.

Self-contained wrapper around the FMP /stable endpoints. Includes:
  - Rate-limit aware throttling (50ms min interval)
  - Retry on 429 / 5xx / "Limit Reach" body responses
  - 402 (Premium endpoint) caught without retry
  - JSONDecodeError caught as permanent failure (CDN HTML error page case)

Replaces the legacy agent/legacy/fmp_client.py module. The legacy version
imports `from _config import FMP_KEY, FMP_BASE` which broke during the
13 May 2026 reorganization. This module bakes the configuration in directly.

Usage:
    from agent.fmp import fmp_get, quote, batch_quote

    q = quote("AAPL")
    quotes = batch_quote(["AAPL", "MSFT", "NVDA"])
    rsi = fmp_get("technical-indicators/rsi",
                  {"symbol": "AAPL", "periodLength": 14, "timeframe": "1day"})

FMP Ultimate plan: 3000 calls/min.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

import requests

# ---------- Configuration ----------

FMP_KEY = os.environ.get(
    "FMP_API_KEY",
    "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8",  # fallback from memory
)
FMP_BASE = "https://financialmodelingprep.com/stable"

_DEFAULT_TIMEOUT  = 15
_MAX_RETRIES      = 3
_RETRY_BACKOFF    = 2.0
_MIN_CALL_INTERVAL = 0.05   # 50 ms — burst protection, 1200/min ceiling
_last_call_ts: float = 0.0


# ---------- Throttle ----------

def _throttle() -> None:
    """Enforce minimum interval between consecutive calls."""
    global _last_call_ts
    if _MIN_CALL_INTERVAL <= 0:
        return
    now = time.monotonic()
    elapsed = now - _last_call_ts
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)
    _last_call_ts = time.monotonic()


# ---------- Core GET ----------

def fmp_get(
    endpoint: str,
    params: Optional[dict] = None,
    timeout: int = _DEFAULT_TIMEOUT,
    max_retries: int = _MAX_RETRIES,
):
    """
    GET request to FMP /stable/<endpoint>.

    Returns the parsed JSON response (list or dict). Returns [] on hard
    failure (no API key, permanent error, all retries exhausted).
    """
    if not FMP_KEY:
        print(f"[fmp] FMP_API_KEY not set. endpoint={endpoint}")
        return []

    p = dict(params or {})
    p["apikey"] = FMP_KEY
    url = f"{FMP_BASE}/{endpoint.lstrip('/')}"

    last_err: Optional[str] = None
    for attempt in range(max_retries + 1):
        _throttle()
        try:
            r = requests.get(url, params=p, timeout=timeout)
        except requests.RequestException as e:
            last_err = f"network: {e}"
            if attempt < max_retries:
                time.sleep(_RETRY_BACKOFF ** attempt)
                continue
            break

        # 402 — premium endpoint, do not retry
        if r.status_code == 402:
            print(f"[fmp] 402 premium-only endpoint={endpoint}")
            return []

        # 429 or 5xx — retry with backoff
        body = (r.text or "")[:200].lower()
        if r.status_code == 429 or r.status_code >= 500 or "limit reach" in body:
            wait = 60 + 30 * attempt  # 60s, 90s, 120s — aligned with FMP min reset
            last_err = f"status={r.status_code}, body={body[:80]!r}"
            if attempt < max_retries:
                print(f"[fmp] retry in {wait}s ({last_err})")
                time.sleep(wait)
                continue
            break

        if not r.ok:
            last_err = f"status={r.status_code}, body={body[:80]!r}"
            break

        # Parse JSON
        try:
            return r.json()
        except json.JSONDecodeError as e:
            # Often a CDN HTML error page — permanent failure for this call
            last_err = f"json_decode: {e}"
            break

    print(f"[fmp] fmp_get failed endpoint={endpoint} err={last_err}")
    return []


# ---------- Convenience helpers ----------

def quote(symbol: str) -> Optional[dict]:
    """Single quote. Returns the first element of the list, or None."""
    result = fmp_get("quote", {"symbol": symbol})
    if isinstance(result, list) and result:
        return result[0]
    return None


def batch_quote(symbols: list[str]) -> dict[str, dict]:
    """
    Batch quote for multiple symbols. Returns {symbol: quote_dict}.

    FMP `batch-quote` accepts comma-separated symbols and returns a list.
    """
    if not symbols:
        return {}
    syms = ",".join(sorted(set(symbols)))
    result = fmp_get("batch-quote", {"symbols": syms})
    if not isinstance(result, list):
        return {}
    return {q.get("symbol"): q for q in result if isinstance(q, dict) and q.get("symbol")}


def historical_eod(symbol: str, limit: int = 30) -> list[dict]:
    """
    Historical EOD bars (newest first per FMP convention).
    Endpoint: /stable/historical-price-eod/full
    Returns a list of {symbol, date, open, high, low, close, volume, ...}.
    """
    result = fmp_get("historical-price-eod/full", {"symbol": symbol, "limit": limit})
    return result if isinstance(result, list) else []


def vix_quote() -> Optional[dict]:
    """Current VIX quote (FMP ^VIX confirmed working since Apr 19 2026)."""
    return quote("^VIX")


# ---------- CLI for sanity checks ----------

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="FMP stable client quick test")
    p.add_argument("--symbol", default="AAPL")
    args = p.parse_args()

    q = quote(args.symbol)
    if q:
        print(f"{args.symbol}: price=${q.get('price')} "
              f"chg={q.get('changePercentage')}% "
              f"prev=${q.get('previousClose')}")
    else:
        print(f"No quote returned for {args.symbol}")

    vix = vix_quote()
    if vix:
        print(f"^VIX: {vix.get('price')}")
