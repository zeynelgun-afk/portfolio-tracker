#!/usr/bin/env python3
"""
Aşama 1: Earnings Calendar Tarama + Mid-Cap+ Filtre

FMP earnings-calendar ile belirli tarih aralığında bilanço açıklayan ABD hisselerini çeker,
profile endpoint ile mid-cap+ filtre uygular.

Kullanım:
    python 01_earnings_calendar.py --from 2026-05-07 --to 2026-05-08

Çıktı: 01_filtered_midcap.json
"""
import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timedelta

API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
BASE = "https://financialmodelingprep.com/stable"


def fmp_get(endpoint, params=None, max_retries=3, retry_delay=1.5):
    """FMP API çağrısı. 429/503/network için retry, 4xx için kalıcı hata (None döner)."""
    if params is None:
        params = {}
    params["apikey"] = API_KEY
    for attempt in range(max_retries):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            elif r.status_code == 503:
                time.sleep(retry_delay)
                continue
            else:
                return None
        except (requests.ConnectionError, requests.Timeout):
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
        except Exception:
            break
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_date", required=True)
    ap.add_argument("--to", dest="to_date", required=True)
    ap.add_argument("--out", default="01_filtered_midcap.json")
    ap.add_argument("--min-mcap", type=float, default=2_000_000_000, help="Min market cap USD")
    ap.add_argument("--min-price", type=float, default=10.0, help="Min hisse fiyatı USD")
    args = ap.parse_args()

    print(f"[1/2] Earnings calendar {args.from_date} → {args.to_date}")
    cal = fmp_get("earnings-calendar", {"from": args.from_date, "to": args.to_date})
    if not cal:
        print("Earnings calendar boş, çıkıyor")
        return 1
    
    # Sadece US hisseleri (nokta veya tire içermeyen ticker = US listing genelde)
    us_only = [e for e in cal if e.get("symbol") and "." not in e["symbol"] and "-" not in e["symbol"]]
    print(f"  Total: {len(cal)}, US: {len(us_only)}")
    
    # Sadece actual data açıklamış olanlar
    reported = [e for e in us_only if e.get("epsActual") is not None or e.get("revenueActual") is not None]
    print(f"  Actual data açıkladı: {len(reported)}")

    print(f"[2/2] Profile çekiyor (mid-cap+ filtre için)...")
    filtered = []
    for i, e in enumerate(reported):
        sym = e["symbol"]
        prof = fmp_get("profile", {"symbol": sym})
        if not prof or not isinstance(prof, list) or len(prof) == 0:
            continue
        p = prof[0]
        
        mcap = p.get("marketCap") or 0
        price = p.get("price") or 0
        # KRİTİK: stable endpoint'inde 'exchange' alanı kullanılır, 'exchangeShortName' DEĞİL
        exch = p.get("exchange", "")
        is_etf = p.get("isEtf", False)
        is_fund = p.get("isFund", False)
        is_active = p.get("isActivelyTrading", False)
        
        if (mcap >= args.min_mcap and price >= args.min_price 
            and exch in ("NYSE", "NASDAQ", "AMEX") 
            and not is_etf and not is_fund and is_active):
            filtered.append({
                "symbol": sym,
                "name": p.get("companyName"),
                "sector": p.get("sector"),
                "industry": p.get("industry"),
                "mcap": mcap,
                "price": price,
                "exchange": exch,
                "earnings_date": e.get("date"),
                "epsActual": e.get("epsActual"),
                "epsEstimated": e.get("epsEstimated"),
                "revenueActual": e.get("revenueActual"),
                "revenueEstimated": e.get("revenueEstimated"),
            })
        
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(reported)} işlendi, {len(filtered)} mid-cap+ bulundu")
    
    filtered.sort(key=lambda x: x["mcap"], reverse=True)
    
    with open(args.out, "w") as f:
        json.dump(filtered, f, indent=2)
    print(f"\n=== Mid-cap+ ABD hisseler: {len(filtered)} ===")
    print(f"Top 10 (mcap'a göre):")
    for f in filtered[:10]:
        print(f"  {f['symbol']:8s} ${f['mcap']/1e9:>7.1f}B  {(f['sector'] or 'N/A')[:25]:25s}  {(f['name'] or '')[:35]}")
    print(f"\nKaydedildi: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
