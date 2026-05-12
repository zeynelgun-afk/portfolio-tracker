"""
Analist Takip — State Tracker

İşlenen revizyon ID'lerini takip eder, idempotency sağlar.
Aynı revizyon birden fazla DM bildirimine yol açmaz.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import PROCESSED_REVISIONS_PATH, SIGNAL_HISTORY_PATH


def _ensure_dirs():
    Path(PROCESSED_REVISIONS_PATH).parent.mkdir(parents=True, exist_ok=True)


def is_revision_seen(revision_id: str) -> bool:
    """Daha önce işlenmiş mi?"""
    _ensure_dirs()
    p = Path(PROCESSED_REVISIONS_PATH)
    if not p.exists():
        return False
    with open(p) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("revision_id") == revision_id:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def mark_revision_seen(revision: dict) -> None:
    """Revizyonu işlenmiş olarak kaydet."""
    _ensure_dirs()
    record = {
        "revision_id": revision["revision_id"],
        "ticker": revision["ticker"],
        "source": revision.get("source", "?"),
        "published_at": revision["published_at"].isoformat() if isinstance(
            revision["published_at"], datetime) else str(revision["published_at"]),
        "seen_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(PROCESSED_REVISIONS_PATH, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def filter_unseen(revisions: list[dict]) -> list[dict]:
    """Henüz işlenmemiş revizyonları döner."""
    return [r for r in revisions if not is_revision_seen(r["revision_id"])]


def record_signal(signal: dict) -> None:
    """
    Üretilen sinyali (DM gönderildi) history'e kaydet.
    Audit trail için.
    """
    _ensure_dirs()
    record = dict(signal)
    record["recorded_at"] = datetime.utcnow().isoformat() + "Z"
    # Datetime'ları str'e çevir
    def _clean(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(x) for x in obj]
        return obj
    with open(SIGNAL_HISTORY_PATH, "a") as f:
        f.write(json.dumps(_clean(record), ensure_ascii=False) + "\n")


def get_recent_signals(ticker: Optional[str] = None, n: int = 20) -> list[dict]:
    """Son n sinyali döner (audit/debug için)."""
    p = Path(SIGNAL_HISTORY_PATH)
    if not p.exists():
        return []
    results = []
    with open(p) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if ticker is None or rec.get("ticker") == ticker:
                    results.append(rec)
            except json.JSONDecodeError:
                continue
    return results[-n:]


def already_signaled_recently(
    ticker: str,
    decision: str,
    cooldown_hours: int = 4,
) -> bool:
    """
    Belirli ticker+decision için son cooldown_hours içinde DM atıldı mı?
    Aynı sinyal sürekli DM atmasın diye.
    """
    recent = get_recent_signals(ticker=ticker, n=20)
    if not recent:
        return False
    cutoff = datetime.utcnow() - timedelta(hours=cooldown_hours)
    for rec in reversed(recent):
        try:
            rec_dt = datetime.fromisoformat(rec.get("recorded_at", "").replace("Z", ""))
            if rec_dt < cutoff:
                return False
            if rec.get("decision") == decision:
                return True
        except Exception:
            continue
    return False


def rotate_logs(keep_days: int = 90) -> dict:
    """Eski kayıtları arşivle (90 günden eski)."""
    cutoff = datetime.utcnow() - timedelta(days=keep_days)
    cutoff_iso = cutoff.isoformat()

    results = {"revisions": 0, "signals": 0}

    for path_str, key in [(PROCESSED_REVISIONS_PATH, "revisions"),
                          (SIGNAL_HISTORY_PATH, "signals")]:
        p = Path(path_str)
        if not p.exists():
            continue
        kept = []
        archived = []
        with open(p) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    ts = rec.get("seen_at") or rec.get("recorded_at", "")
                    if ts < cutoff_iso:
                        archived.append(line)
                    else:
                        kept.append(line)
                except json.JSONDecodeError:
                    kept.append(line)
        if archived:
            arc_path = p.with_suffix(f".archive_{cutoff.year}_{cutoff.month:02d}.jsonl")
            with open(arc_path, "a") as f:
                f.writelines(archived)
            with open(p, "w") as f:
                f.writelines(kept)
            results[key] = len(archived)

    return results
