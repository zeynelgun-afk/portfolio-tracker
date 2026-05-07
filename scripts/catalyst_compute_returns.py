#!/usr/bin/env python3
"""
Catalyst Forward Returns Computation
=====================================
logs/catalyst_predictions.jsonl içindeki tahminleri açar, T+5/T+10/T+30 gün
forward return'lerini FMP'den çekip kayıtlara ekler.

Bu script Railway'de günlük çalıştırılır (veya manuel) — forward return
süresi dolmuş kayıtları işaretler. 30+ gün canlı kullanım sonrası gerçek
backtest yapılabilir hale gelir.

Kullanım:
    python3 scripts/catalyst_compute_returns.py
    python3 scripts/catalyst_compute_returns.py --analyze    # özet rapor
"""

from __future__ import annotations
import os
import json
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).parent.parent
PRED_LOG = REPO_ROOT / "logs" / "catalyst_predictions.jsonl"
FMP_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")


def _fmp_history(ticker: str, from_date: str, to_date: str) -> list:
    """FMP historical-price-eod/full — son N gün."""
    try:
        url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
        r = requests.get(url, params={
            "symbol": ticker,
            "from": from_date,
            "to": to_date,
            "apikey": FMP_KEY,
        }, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        if isinstance(data, dict) and "historical" in data:
            return data["historical"]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _price_at_or_after(history: list, target_date: str) -> tuple[float, str] | None:
    """
    history newest-first sıralı. target_date ve sonrası ilk close'u bul.
    Returns: (close_price, actual_date) | None
    """
    target = datetime.strptime(target_date[:10], "%Y-%m-%d").date()
    # Eski → yeni sıralı liste
    by_date = sorted(history, key=lambda x: x.get("date", ""))
    for row in by_date:
        try:
            d = datetime.strptime(row["date"][:10], "%Y-%m-%d").date()
            if d >= target:
                return (float(row.get("close", 0)), row["date"][:10])
        except Exception:
            continue
    return None


def compute_returns(verbose: bool = False) -> dict:
    """
    Tüm kayıtları gez, forward return'leri eksik olanları doldur.
    Returns: {'updated': N, 'skipped': N, 'errors': N}
    """
    if not PRED_LOG.exists():
        print(f"Prediction log yok: {PRED_LOG}")
        return {"updated": 0, "skipped": 0, "errors": 0}

    with open(PRED_LOG) as f:
        records = [json.loads(line) for line in f if line.strip()]

    # Ticker bazında gruplandır (FMP çağrılarını azalt)
    by_ticker = defaultdict(list)
    for i, rec in enumerate(records):
        # Sadece eksik forward return olanları al
        needs_update = (
            rec.get("fwd_5d_return") is None or
            rec.get("fwd_10d_return") is None or
            rec.get("fwd_30d_return") is None
        )
        if needs_update and rec.get("logged_price", 0) > 0:
            by_ticker[rec["ticker"]].append((i, rec))

    updated, skipped, errors = 0, 0, 0
    today = datetime.now().date()

    for ticker, recs in by_ticker.items():
        # En eski kayıt + 35 gün arası history çek
        oldest = min(datetime.strptime(r[1]["logged_at"][:10], "%Y-%m-%d").date()
                     for r in recs)
        from_date = oldest.strftime("%Y-%m-%d")
        to_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")

        history = _fmp_history(ticker, from_date, to_date)
        if not history:
            errors += len(recs)
            if verbose:
                print(f"[{ticker}] history alınamadı, {len(recs)} kayıt atlandı")
            continue

        for idx, rec in recs:
            logged_at = rec["logged_at"][:10]
            logged_price = rec.get("logged_price", 0)
            if logged_price <= 0:
                skipped += 1
                continue

            log_date = datetime.strptime(logged_at, "%Y-%m-%d").date()

            # T+5
            if rec.get("fwd_5d_return") is None:
                target = (log_date + timedelta(days=7)).strftime("%Y-%m-%d")  # ~5 trading day = 7 cal day
                if datetime.strptime(target, "%Y-%m-%d").date() <= today:
                    found = _price_at_or_after(history, target)
                    if found:
                        ret = ((found[0] - logged_price) / logged_price) * 100
                        records[idx]["fwd_5d_return"] = round(ret, 2)
                        records[idx]["fwd_5d_date"] = found[1]
                        records[idx]["fwd_5d_price"] = found[0]
                        updated += 1
            # T+10
            if rec.get("fwd_10d_return") is None:
                target = (log_date + timedelta(days=14)).strftime("%Y-%m-%d")
                if datetime.strptime(target, "%Y-%m-%d").date() <= today:
                    found = _price_at_or_after(history, target)
                    if found:
                        ret = ((found[0] - logged_price) / logged_price) * 100
                        records[idx]["fwd_10d_return"] = round(ret, 2)
                        records[idx]["fwd_10d_date"] = found[1]
                        records[idx]["fwd_10d_price"] = found[0]
                        updated += 1
            # T+30
            if rec.get("fwd_30d_return") is None:
                target = (log_date + timedelta(days=42)).strftime("%Y-%m-%d")
                if datetime.strptime(target, "%Y-%m-%d").date() <= today:
                    found = _price_at_or_after(history, target)
                    if found:
                        ret = ((found[0] - logged_price) / logged_price) * 100
                        records[idx]["fwd_30d_return"] = round(ret, 2)
                        records[idx]["fwd_30d_date"] = found[1]
                        records[idx]["fwd_30d_price"] = found[0]
                        updated += 1

    # Geri yaz
    if updated > 0:
        with open(PRED_LOG, "w") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {"updated": updated, "skipped": skipped, "errors": errors,
            "total_records": len(records)}


def analyze_predictions() -> None:
    """Bayrak bazında forward return ortalaması — basit alpha analizi."""
    if not PRED_LOG.exists():
        print(f"Prediction log yok: {PRED_LOG}")
        return

    with open(PRED_LOG) as f:
        records = [json.loads(line) for line in f if line.strip()]

    # Bayrak bazında grup
    flag_returns = defaultdict(lambda: {"5d": [], "10d": [], "30d": []})
    no_flag_returns = {"5d": [], "10d": [], "30d": []}
    score_buckets = defaultdict(lambda: {"5d": [], "10d": [], "30d": []})

    for rec in records:
        flags = rec.get("flags", [])
        for horizon in ["5d", "10d", "30d"]:
            ret = rec.get(f"fwd_{horizon}_return")
            if ret is None:
                continue
            if not flags:
                no_flag_returns[horizon].append(ret)
            for flag in flags:
                # "catalyst:" prefix'ini kaldır
                clean_flag = flag.split(":")[-1].strip()
                flag_returns[clean_flag][horizon].append(ret)

            # Skor bucket
            score = rec.get("score", 0)
            if score > 30:
                bucket = "score>+30"
            elif score > 10:
                bucket = "score +10..+30"
            elif score > -10:
                bucket = "score -10..+10"
            elif score > -30:
                bucket = "score -30..-10"
            else:
                bucket = "score<-30"
            score_buckets[bucket][horizon].append(ret)

    print(f"\n{'='*70}")
    print(f"  Catalyst Backtest Özeti — {len(records)} toplam kayıt")
    print(f"{'='*70}")

    def _stats(arr):
        if not arr:
            return "n/a"
        avg = sum(arr) / len(arr)
        return f"avg {avg:+.2f}% (n={len(arr)})"

    print("\n📊 Bayraklar (forward return ortalaması):")
    print(f"  {'BAYRAK':<35} {'T+5':<22} {'T+10':<22} {'T+30':<22}")
    for flag, h in sorted(flag_returns.items()):
        if sum(len(v) for v in h.values()) < 3:
            continue  # n<3 skip
        print(f"  {flag:<35} {_stats(h['5d']):<22} {_stats(h['10d']):<22} {_stats(h['30d']):<22}")

    print(f"\n  {'(bayraksız)':<35} {_stats(no_flag_returns['5d']):<22} "
          f"{_stats(no_flag_returns['10d']):<22} {_stats(no_flag_returns['30d']):<22}")

    print("\n📈 Skor Bucket'ları:")
    print(f"  {'BUCKET':<25} {'T+5':<22} {'T+10':<22} {'T+30':<22}")
    for bucket, h in sorted(score_buckets.items()):
        if sum(len(v) for v in h.values()) < 3:
            continue
        print(f"  {bucket:<25} {_stats(h['5d']):<22} {_stats(h['10d']):<22} {_stats(h['30d']):<22}")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true",
                        help="Backtest özet raporu")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        analyze_predictions()
    else:
        result = compute_returns(verbose=args.verbose)
        print(f"Catalyst forward returns güncellendi:")
        print(f"  Toplam kayıt: {result['total_records']}")
        print(f"  Güncellenen alan: {result['updated']}")
        print(f"  Atlanan: {result['skipped']}")
        print(f"  Hata: {result['errors']}")
