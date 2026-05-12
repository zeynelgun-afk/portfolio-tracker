"""
Analist Takip — Revision Fetcher

FMP'den 3 endpoint çağrısı:
1. price-target-news (sembol bazlı) — Hedef fiyat değişiklikleri
2. grades (sembol bazlı) — Upgrade/downgrade akışı
3. grades-latest-news — En son grade haberleri (global)

NOT: price-target-latest-news global (tüm semboller karışık) — sembol filter
yok, biz sembol bazlı price-target-news kullanıyoruz.
"""
from __future__ import annotations
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from .config import FMP_BASE, FMP_THROTTLE_MS, get_fmp_key


_last_call_time = 0.0


def _throttle() -> None:
    global _last_call_time
    elapsed_ms = (time.time() - _last_call_time) * 1000
    if elapsed_ms < FMP_THROTTLE_MS:
        time.sleep((FMP_THROTTLE_MS - elapsed_ms) / 1000)
    _last_call_time = time.time()


def _fmp_get(endpoint: str, **params) -> Optional[list | dict]:
    _throttle()
    params["apikey"] = get_fmp_key()
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=20)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def parse_old_target_from_title(title: str) -> Optional[float]:
    """
    "Applied Optoelectronics price target raised to $160 from $72.50 at Raymond James"
    → 72.50
    """
    m = re.search(r"from \$?([\d,]+\.?\d*)", title)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None


def fetch_price_target_revisions(
    ticker: str,
    since_dt: datetime,
    limit: int = 50,
) -> list[dict]:
    """
    Belirli ticker için since_dt sonrası hedef fiyat revizyonlarını döner.

    Returns:
        [
            {
                "ticker": "AAOI",
                "published_at": datetime (UTC),
                "analyst_company": "Raymond James",
                "analyst_name": "",
                "title": "Applied Optoelectronics price target raised to $160 from $72.50 ...",
                "direction": "raised" | "lowered" | "initiated" | "maintained",
                "new_target": 160.0,
                "old_target": 72.50,
                "change_pct": 120.69,
                "price_when_posted": 150.73,
                "news_url": "https://...",
                "revision_id": "<unique key>",
            },
            ...
        ]
    """
    data = _fmp_get("price-target-news", symbol=ticker, limit=limit)
    if not isinstance(data, list):
        return []

    results = []
    for rev in data:
        try:
            pub_str = rev.get("publishedDate", "")
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except Exception:
            continue

        if pub_dt < since_dt:
            continue

        title = rev.get("newsTitle", "")
        title_lower = title.lower()
        new_target = rev.get("priceTarget")

        # Direction parse
        direction = "unknown"
        if "raised" in title_lower or "increased" in title_lower or "upgrade" in title_lower:
            direction = "raised"
        elif "lowered" in title_lower or "cut" in title_lower or "downgrade" in title_lower or "reduce" in title_lower:
            direction = "lowered"
        elif "initiat" in title_lower:
            direction = "initiated"
        elif "maintain" in title_lower or "reiterat" in title_lower:
            direction = "maintained"

        old_target = parse_old_target_from_title(title)
        change_pct = None
        if old_target and old_target > 0 and new_target:
            change_pct = ((new_target / old_target) - 1) * 100

        # Idempotency için unique ID
        revision_id = f"pt_{ticker}_{pub_str}_{rev.get('analystCompany', 'unknown')}"

        results.append({
            "ticker": ticker,
            "source": "price-target-news",
            "published_at": pub_dt,
            "analyst_company": rev.get("analystCompany", ""),
            "analyst_name": rev.get("analystName", ""),
            "title": title,
            "direction": direction,
            "new_target": new_target,
            "old_target": old_target,
            "change_pct": change_pct,
            "price_when_posted": rev.get("priceWhenPosted"),
            "news_url": rev.get("newsURL", ""),
            "revision_id": revision_id,
        })

    return results


def fetch_grades(
    ticker: str,
    since_dt: datetime,
    limit: int = 50,
) -> list[dict]:
    """
    Belirli ticker için since_dt sonrası grade değişikliklerini döner.

    Returns:
        [
            {
                "ticker": "AAOI",
                "published_at": datetime,
                "grading_company": "Rosenblatt",
                "previous_grade": "Buy",
                "new_grade": "Buy",
                "action": "maintain" | "upgrade" | "downgrade" | "initiate",
                "revision_id": "<unique key>",
            },
            ...
        ]
    """
    data = _fmp_get("grades", symbol=ticker, limit=limit)
    if not isinstance(data, list):
        return []

    results = []
    for g in data:
        try:
            date_str = g.get("date", "")
            # FMP grades endpoint sadece tarih döner (saat yok)
            pub_dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if pub_dt < since_dt:
            continue

        action = g.get("action", "").lower()
        if action == "main" or action == "maintained":
            action = "maintain"

        revision_id = f"gr_{ticker}_{date_str}_{g.get('gradingCompany', 'unknown')}"

        results.append({
            "ticker": ticker,
            "source": "grades",
            "published_at": pub_dt,
            "grading_company": g.get("gradingCompany", ""),
            "previous_grade": g.get("previousGrade", ""),
            "new_grade": g.get("newGrade", ""),
            "action": action,
            "revision_id": revision_id,
        })

    return results


def fetch_grades_latest_news(
    ticker: str,
    since_dt: datetime,
    limit: int = 50,
) -> list[dict]:
    """
    Belirli ticker için grade-related haber akışı (price target + grade combined).

    Returns:
        [
            {
                "ticker": "MOS",
                "published_at": datetime,
                "grading_company": "UBS",
                "previous_grade": "Neutral",
                "new_grade": "Neutral",
                "action": "hold",
                "price_target": 23,  # haberle gelen yeni hedef
                "news_title": "Mosaic price target lowered to $23 from $27 at UBS",
                "old_target": 27.0,
                "change_pct": -14.81,
                "revision_id": "<unique key>",
            },
            ...
        ]
    """
    data = _fmp_get("grades-latest-news", symbol=ticker, limit=limit)
    if not isinstance(data, list):
        return []

    results = []
    for g in data:
        try:
            pub_str = g.get("publishedDate", "")
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except Exception:
            continue

        if pub_dt < since_dt:
            continue

        title = g.get("newsTitle", "")
        new_target = g.get("priceTarget")
        old_target = parse_old_target_from_title(title)
        change_pct = None
        if old_target and old_target > 0 and new_target:
            change_pct = ((new_target / old_target) - 1) * 100

        revision_id = f"gnews_{ticker}_{pub_str}_{g.get('gradingCompany', 'unknown')}"

        results.append({
            "ticker": ticker,
            "source": "grades-latest-news",
            "published_at": pub_dt,
            "grading_company": g.get("gradingCompany", ""),
            "previous_grade": g.get("previousGrade", ""),
            "new_grade": g.get("newGrade", ""),
            "action": g.get("action", "").lower(),
            "price_target": new_target,
            "old_target": old_target,
            "change_pct": change_pct,
            "price_when_posted": g.get("priceWhenPosted"),
            "news_title": title,
            "news_url": g.get("newsURL", ""),
            "revision_id": revision_id,
        })

    return results


def fetch_all_signals(ticker: str, since_dt: datetime) -> list[dict]:
    """
    3 endpoint'i birlikte çağırır, deduplicate eder, tarihe göre sıralar.
    """
    pt_revisions = fetch_price_target_revisions(ticker, since_dt)
    grades = fetch_grades(ticker, since_dt)
    grade_news = fetch_grades_latest_news(ticker, since_dt)

    # Birleştir + deduplicate (revision_id üzerinden)
    all_signals = {}
    for sig in pt_revisions + grades + grade_news:
        rid = sig["revision_id"]
        if rid not in all_signals:
            all_signals[rid] = sig
        else:
            # Aynı kayıt birden fazla endpoint'te varsa, en zengini al
            existing = all_signals[rid]
            for k, v in sig.items():
                if v and not existing.get(k):
                    existing[k] = v

    # Tarihe göre sırala (en yeni önce)
    sorted_signals = sorted(all_signals.values(),
                            key=lambda x: x["published_at"], reverse=True)
    return sorted_signals


def get_current_price(ticker: str) -> Optional[float]:
    """FMP quote endpoint'inden mevcut fiyat."""
    data = _fmp_get("quote", symbol=ticker)
    if isinstance(data, list) and data:
        return data[0].get("price")
    return None


def get_market_cap_b(ticker: str) -> Optional[float]:
    """FMP quote endpoint'inden market cap (USD billion)."""
    data = _fmp_get("quote", symbol=ticker)
    if isinstance(data, list) and data:
        mcap = data[0].get("marketCap", 0)
        return round(mcap / 1e9, 2) if mcap else None
    return None
