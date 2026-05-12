"""
Analist Takip — Performans İzleme

Sistem BUY/STRONG_BUY ürettiği her hisseyi bu listeye otomatik ekler.
Zaman içinde performans takip eder: ekleme fiyatı → mevcut fiyat → %.
Manuel ekleme/silme de mümkün.

Veri Dosyası:
    data/analist_takip/performance_watchlist.json

Şema:
    {
        "tickers": {
            "CEVA": {
                "symbol": "CEVA",
                "added_at": "2026-05-12T14:09:00Z",
                "added_price": 39.13,
                "added_decision": "STRONG_BUY",
                "added_rationale": "3 analist hedef yükseltti...",
                "biggest_raise": {"company": "...", "pct": 35, "old": 50, "new": 67},
                "market_cap_b": 0.85,
                "manual": false,           # auto-added by polling
                "tags": [],
                "notes": ""
            }
        },
        "archived": [...]     # 30 günden eski olanlar
    }
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .config import ANALIST_STATE_DIR


PERFORMANCE_WATCHLIST_PATH = f"{ANALIST_STATE_DIR}/performance_watchlist.json"
WATCHLIST_RETENTION_DAYS = 30


def _ensure_dirs():
    Path(ANALIST_STATE_DIR).mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    """Watchlist'i yükle, yoksa boş yapı döndür."""
    _ensure_dirs()
    p = Path(PERFORMANCE_WATCHLIST_PATH)
    if not p.exists():
        return {"tickers": {}, "archived": []}
    try:
        with open(p) as f:
            data = json.load(f)
        # Şema doğrulama
        if "tickers" not in data:
            data["tickers"] = {}
        if "archived" not in data:
            data["archived"] = []
        return data
    except Exception:
        return {"tickers": {}, "archived": []}


def _save(data: dict) -> None:
    _ensure_dirs()
    with open(PERFORMANCE_WATCHLIST_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_to_watchlist(
    ticker: str,
    decision: dict,
    current_price: Optional[float] = None,
    market_cap_b: Optional[float] = None,
    manual: bool = False,
    notes: str = "",
) -> dict:
    """
    Watchlist'e ticker ekle. Aynı ticker zaten varsa GÜNCELLEMEZ
    (orijinal ekleme tarihi/fiyatı korunur — performans referansı).

    Returns:
        {"added": True|False, "reason": "..."}
    """
    ticker = ticker.upper().strip()
    if not ticker:
        return {"added": False, "reason": "Boş ticker"}

    data = _load()
    if ticker in data["tickers"]:
        return {
            "added": False,
            "reason": "Zaten watchlist'te",
            "existing": data["tickers"][ticker],
        }

    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "symbol": ticker,
        "added_at": now,
        "added_price": current_price,
        "added_decision": decision.get("decision"),
        "added_confidence": decision.get("confidence"),
        "added_rationale": decision.get("rationale", ""),
        "biggest_raise": decision.get("biggest_raise"),
        "biggest_cut": decision.get("biggest_cut"),
        "raised_count": decision.get("raised_count_48h"),
        "lowered_count": decision.get("lowered_count_48h"),
        "avg_revision_pct": decision.get("avg_revision_pct"),
        "market_cap_b": market_cap_b,
        "manual": manual,
        "tags": [],
        "notes": notes,
    }

    data["tickers"][ticker] = entry
    _save(data)

    return {"added": True, "entry": entry}


def add_manual_ticker(ticker: str, notes: str = "", current_price: Optional[float] = None) -> dict:
    """
    /analist ekle komutu için. Sistem kararı olmadan manuel ekleme.
    """
    ticker = ticker.upper().strip()
    if not ticker:
        return {"added": False, "reason": "Boş ticker"}

    # Eğer fiyat verilmediyse FMP'den çek
    if current_price is None:
        try:
            from .revision_fetcher import get_current_price
            current_price = get_current_price(ticker)
        except Exception:
            pass

    fake_decision = {
        "decision": "MANUAL",
        "confidence": "manual",
        "rationale": notes or "Manuel eklendi",
    }
    return add_to_watchlist(
        ticker, fake_decision,
        current_price=current_price,
        manual=True,
        notes=notes,
    )


def remove_from_watchlist(ticker: str) -> dict:
    """Watchlist'ten ticker sil."""
    ticker = ticker.upper().strip()
    data = _load()
    if ticker not in data["tickers"]:
        return {"removed": False, "reason": "Watchlist'te yok"}
    entry = data["tickers"].pop(ticker)
    _save(data)
    return {"removed": True, "entry": entry}


def cleanup_old(retention_days: int = WATCHLIST_RETENTION_DAYS) -> dict:
    """30 günden eski watchlist girişlerini arşivle."""
    data = _load()
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()

    archived = []
    kept = {}
    for ticker, entry in data["tickers"].items():
        added_at = entry.get("added_at", "").replace("Z", "")
        if added_at < cutoff_iso and not entry.get("manual"):
            # Manuel olmayan ve 30 günden eski olanları arşivle
            archived.append(entry)
        else:
            kept[ticker] = entry

    if archived:
        data["tickers"] = kept
        data["archived"].extend(archived)
        # Arşivi 90 günde bir temizle (büyümesin)
        if len(data["archived"]) > 500:
            data["archived"] = data["archived"][-500:]
        _save(data)

    return {"archived_count": len(archived), "kept_count": len(kept)}


def get_watchlist() -> dict:
    """Mevcut performans watchlist'i (raw)."""
    return _load()


def get_watchlist_with_performance() -> list[dict]:
    """
    Watchlist + mevcut fiyat ile performans hesabı.

    Returns:
        [
            {
                "symbol", "added_at", "added_price",
                "current_price", "performance_pct", "hold_days",
                "added_decision", "added_rationale", "biggest_raise",
                "manual", ...
            }
        ]
    """
    from .revision_fetcher import _fmp_get

    data = _load()
    if not data["tickers"]:
        return []

    results = []
    now = datetime.utcnow()

    for ticker, entry in data["tickers"].items():
        # Mevcut fiyatı çek
        current_price = None
        try:
            q = _fmp_get("quote", symbol=ticker)
            if isinstance(q, list) and q:
                current_price = q[0].get("price")
        except Exception:
            pass

        # Performans
        added_price = entry.get("added_price")
        performance_pct = None
        if current_price and added_price and added_price > 0:
            # SELL kararıysa ters çevir (düşüş = isabet)
            if entry.get("added_decision") in ("SELL", "STRONG_SELL"):
                performance_pct = ((added_price / current_price) - 1) * 100
            else:
                performance_pct = ((current_price / added_price) - 1) * 100

        # Hold days
        added_at_str = entry.get("added_at", "").replace("Z", "")
        hold_days = None
        try:
            added_dt = datetime.fromisoformat(added_at_str)
            hold_days = (now - added_dt).days
        except Exception:
            pass

        result = dict(entry)
        result["current_price"] = current_price
        result["performance_pct"] = round(performance_pct, 2) if performance_pct is not None else None
        result["hold_days"] = hold_days
        results.append(result)

    # Performansa göre sırala (en iyi başta)
    results.sort(
        key=lambda x: (x["performance_pct"] is None, -(x.get("performance_pct") or 0))
    )
    return results


def get_statistics() -> dict:
    """Watchlist istatistikleri."""
    perf = get_watchlist_with_performance()
    if not perf:
        return {
            "total": 0, "positive": 0, "negative": 0, "neutral": 0,
            "avg_performance": None, "best": None, "worst": None,
        }

    with_perf = [p for p in perf if p["performance_pct"] is not None]
    positive = [p for p in with_perf if p["performance_pct"] > 1]
    negative = [p for p in with_perf if p["performance_pct"] < -1]
    neutral = [p for p in with_perf if -1 <= p["performance_pct"] <= 1]
    avg_perf = (
        sum(p["performance_pct"] for p in with_perf) / len(with_perf)
        if with_perf else None
    )

    return {
        "total": len(perf),
        "positive": len(positive),
        "negative": len(negative),
        "neutral": len(neutral),
        "avg_performance": round(avg_perf, 2) if avg_perf is not None else None,
        "best": with_perf[0] if with_perf else None,
        "worst": with_perf[-1] if with_perf else None,
        "hit_rate": (
            round(len(positive) / len(with_perf) * 100, 1)
            if with_perf else None
        ),
    }
