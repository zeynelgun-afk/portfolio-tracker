"""
Bilanço Müdürü — State Tracker

İşlenen bilançoları JSONL formatında log'lar. Pipeline çökmeye dayanıklı:
yeniden başlatıldığında aynı bilançoyu tekrar işlemez.

Dosya: data/earnings_state/processed.jsonl
Format (her satır bir JSON):
    {
        "ticker": "NVDA",
        "fiscal_period": "Q4 FY2026",
        "filing_date": "2026-02-25",
        "processed_at": "2026-02-25T23:15:00Z",
        "decision": "AL",
        "target_avg": 216.54,
        "current_price_at_decision": 138.0,
        "dry_run": true,
        "kimi_cost_usd": 0.0092
    }
"""
from __future__ import annotations
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .config import EARNINGS_STATE_DIR


def _state_path() -> Path:
    p = Path(EARNINGS_STATE_DIR) / "processed.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def is_processed(ticker: str, fiscal_period: str) -> bool:
    """
    Belirli bir ticker+çeyrek kombinasyonu daha önce işlendi mi?
    """
    p = _state_path()
    if not p.exists():
        return False
    with open(p) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("ticker") == ticker and rec.get("fiscal_period") == fiscal_period:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def mark_processed(
    ticker: str,
    fiscal_period: str,
    filing_date: str,
    decision: str,
    target_avg: Optional[float] = None,
    target_high: Optional[float] = None,
    current_price: Optional[float] = None,
    dry_run: bool = False,
    kimi_cost_usd: float = 0.0,
    error: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Bir bilançoyu işlenmiş olarak işaretler.
    """
    record = {
        "ticker": ticker,
        "fiscal_period": fiscal_period,
        "filing_date": filing_date,
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "decision": decision,
        "target_avg": target_avg,
        "target_high": target_high,
        "current_price_at_decision": current_price,
        "dry_run": dry_run,
        "kimi_cost_usd": round(kimi_cost_usd, 4),
        "error": error,
    }
    if extra:
        record.update(extra)

    p = _state_path()
    with open(p, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_today_kimi_call_count() -> int:
    """Bugün yapılan Kimi çağrı sayısını döner (maliyet koruması için)."""
    p = _state_path()
    if not p.exists():
        return 0
    today_str = date.today().isoformat()
    count = 0
    with open(p) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("processed_at", "").startswith(today_str):
                    count += 1
            except json.JSONDecodeError:
                continue
    return count


def get_recent_processed(n: int = 20) -> list[dict]:
    """Son n işlenmiş bilançoyu döner (DM raporları için)."""
    p = _state_path()
    if not p.exists():
        return []
    lines = []
    with open(p) as f:
        for line in f:
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return lines[-n:]


def rotate_log(keep_days: int = 60) -> int:
    """
    keep_days günden eski kayıtları arşive taşır.
    Dosya çok büyürse aylık rotate edilir.
    Returns: kaç kayıt arşivlendi.
    """
    p = _state_path()
    if not p.exists():
        return 0

    cutoff = datetime.utcnow().date()
    cutoff_str = (cutoff.replace(day=1)).isoformat()  # ay başı kes

    kept = []
    archived = []
    with open(p) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("processed_at", "")[:10] < cutoff_str:
                    archived.append(line)
                else:
                    kept.append(line)
            except json.JSONDecodeError:
                kept.append(line)

    if archived:
        archive_path = p.parent / f"processed_archive_{cutoff.year}_{cutoff.month:02d}.jsonl"
        with open(archive_path, "a") as f:
            f.writelines(archived)
        with open(p, "w") as f:
            f.writelines(kept)

    return len(archived)
