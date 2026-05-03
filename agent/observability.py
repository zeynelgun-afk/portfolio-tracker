#!/usr/bin/env python3
"""
Finzora — Observability
========================
Agent sisteminin çağrı ve karar akışını kayıt altına alır.

İKİ DEPO:
  1. JSONL event stream (logs/events.jsonl)
     - Append-only, insan okuyabilir, RAG için kaynak
     - Her satır bir olay
     - Gitignore'da — büyüyecek, git'te olmayacak
  2. SQLite index (data/finzora.db)
     - Sorgulanabilir
     - Günlük/haftalık/aylık raporlar için
     - Gitignore'da — JSONL'den her zaman yeniden kurulabilir

EVENT TİPLERİ:
  claude_call  — Her Claude API çağrısı
  fmp_call     — Her FMP API çağrısı
  decision     — Claude'dan çıkan her karar (EKLE/ÇIK/DÖNDÜR vb.)
  trade        — Gerçekleşmiş alım/satım (transactions.csv mirror'u)

KULLANIM:
    from agent.observability import log_event, log_claude_call, log_fmp_call

    log_claude_call(
        mode="morning",
        input_tokens=1234, output_tokens=567,
        success=True,
        context_chars=5678,
        decisions_count=3,
        duration_ms=4321,
    )

TASARIM:
  - Her yazım try/except içinde — observability çökmesi ana sistemi etkilemez
  - Timestamp ISO 8601 UTC
  - UUID4 ile her olaya benzersiz id → JSONL ve SQLite arasında eşleşme
"""

import os
import json
import sqlite3
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

# ── Yollar ────────────────────────────────────────────────────────────────────
# agent/ içindeyiz, repo kökü bir üst
_AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _AGENT_DIR.parent
EVENTS_JSONL = REPO_ROOT / "logs" / "events.jsonl"
DB_PATH = REPO_ROOT / "data" / "finzora.db"

EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Yardımcı ──────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    """ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _new_id() -> str:
    """Kısa UUID (ilk 12 karakter yeter)."""
    return uuid.uuid4().hex[:12]


# ── JSONL yazım ────────────────────────────────────────────────────────────────

def log_event(event_type: str, payload: dict) -> Optional[str]:
    """
    Her yazım bu fonksiyondan geçer. JSONL'e append eder.
    SQLite index'e de yazmaya çalışır (başarısız olursa sessizce geçer).

    Returns: event_id, başarısızsa None.
    """
    event_id = _new_id()
    event = {
        "id": event_id,
        "ts": _now_utc(),
        "type": event_type,
        **payload,
    }

    # JSONL yazımı — en önemli garanti, bu çalışmalı
    try:
        with EVENTS_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        # Son çare: stderr
        print(f"[observability] JSONL yazım hatası: {e}")
        return None

    # SQLite index — başarısız olursa aşağıdan devam
    try:
        _index_to_sqlite(event)
    except Exception as e:
        print(f"[observability] SQLite index uyarısı: {e}")

    return event_id


# ── SQLite şema ────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    mode TEXT,
    symbol TEXT,
    portfoy TEXT,
    success INTEGER,
    duration_ms INTEGER,
    raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol);

CREATE TABLE IF NOT EXISTS claude_calls (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    mode TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    context_chars INTEGER,
    decisions_count INTEGER,
    duration_ms INTEGER,
    success INTEGER,
    error TEXT
);

CREATE TABLE IF NOT EXISTS fmp_calls (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    endpoint TEXT,
    status INTEGER,
    duration_ms INTEGER,
    retry_count INTEGER,
    response_size INTEGER,
    error TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    claude_call_id TEXT,
    mode TEXT,
    tip TEXT,
    portfoy TEXT,
    sembol TEXT,
    pct INTEGER,
    neden TEXT,
    hedef_fiyat REAL,
    stop REAL,
    aciliyet TEXT,
    executed INTEGER,
    skipped_reason TEXT,
    FOREIGN KEY (claude_call_id) REFERENCES claude_calls(id)
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    decision_id TEXT,
    action TEXT NOT NULL,
    portfoy TEXT,
    sembol TEXT NOT NULL,
    shares REAL,
    price REAL,
    total REAL,
    reason TEXT,
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);
"""


def _get_conn() -> sqlite3.Connection:
    """Bağlantıyı döner, şemayı kurar."""
    conn = sqlite3.connect(str(DB_PATH), isolation_level=None)  # autocommit
    conn.executescript(_SCHEMA)
    return conn


def _index_to_sqlite(event: dict) -> None:
    """JSONL olayını SQLite'a da yazar."""
    conn = _get_conn()
    try:
        # Ana events tablosu (her event buraya)
        conn.execute(
            """
            INSERT OR REPLACE INTO events
            (id, ts, type, mode, symbol, portfoy, success, duration_ms, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["id"],
                event["ts"],
                event["type"],
                event.get("mode"),
                event.get("symbol") or event.get("sembol"),
                event.get("portfoy"),
                int(event["success"]) if "success" in event else None,
                event.get("duration_ms"),
                json.dumps(event, ensure_ascii=False),
            ),
        )

        # Event tipine özel tablolar
        t = event["type"]
        if t == "claude_call":
            conn.execute(
                """
                INSERT OR REPLACE INTO claude_calls
                (id, ts, mode, model, input_tokens, output_tokens, cost_usd,
                 context_chars, decisions_count, duration_ms, success, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["ts"],
                    event.get("mode"),
                    event.get("model"),
                    event.get("input_tokens"),
                    event.get("output_tokens"),
                    event.get("cost_usd"),
                    event.get("context_chars"),
                    event.get("decisions_count"),
                    event.get("duration_ms"),
                    int(event.get("success", 0)),
                    event.get("error"),
                ),
            )
        elif t == "fmp_call":
            conn.execute(
                """
                INSERT OR REPLACE INTO fmp_calls
                (id, ts, endpoint, status, duration_ms, retry_count, response_size, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["ts"],
                    event.get("endpoint"),
                    event.get("status"),
                    event.get("duration_ms"),
                    event.get("retry_count", 0),
                    event.get("response_size"),
                    event.get("error"),
                ),
            )
        elif t == "decision":
            conn.execute(
                """
                INSERT OR REPLACE INTO decisions
                (id, ts, claude_call_id, mode, tip, portfoy, sembol, pct, neden,
                 hedef_fiyat, stop, aciliyet, executed, skipped_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["ts"],
                    event.get("claude_call_id"),
                    event.get("mode"),
                    event.get("tip"),
                    event.get("portfoy"),
                    event.get("sembol"),
                    event.get("pct"),
                    event.get("neden"),
                    event.get("hedef_fiyat"),
                    event.get("stop"),
                    event.get("aciliyet"),
                    int(event.get("executed", 0)),
                    event.get("skipped_reason"),
                ),
            )
        elif t == "trade":
            conn.execute(
                """
                INSERT OR REPLACE INTO trades
                (id, ts, decision_id, action, portfoy, sembol, shares, price, total, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["ts"],
                    event.get("decision_id"),
                    event.get("action"),
                    event.get("portfoy"),
                    event.get("sembol"),
                    event.get("shares"),
                    event.get("price"),
                    event.get("total"),
                    event.get("reason"),
                ),
            )
    finally:
        conn.close()


# ── Yüksek seviye yardımcılar ────────────────────────────────────────────────

# Model bazlı fiyat tablosu ($/M token)
# Notlar:
#   - Kimi K2 thinking fiyatları OpenRouter listesinden alınmıştır (yaklaşık).
#   - Anthropic Claude tier'ları geriye uyumluluk için bırakıldı (ANTHROPIC_API_KEY
#     fallback'i kullanılırsa veya eski log kayıtları okunursa lazım).
#   - SPEKÜLATİF — faturalandırma için değil, içsel maliyet izleme içindir.
_LLM_PRICING = {
    "kimi_thinking": {"in":  0.60, "out":  2.50},   # moonshotai/kimi-k2-thinking ~$/M
    "kimi":          {"in":  0.30, "out":  1.20},   # moonshotai/kimi-k2 (non-thinking)
    "opus":          {"in": 15.00, "out": 75.00},
    "sonnet":        {"in":  3.00, "out": 15.00},
    "haiku":         {"in":  0.80, "out":  4.00},
}
_DEFAULT_TIER = "kimi_thinking"  # post-migration default


def _model_tier(model: str) -> str:
    """Map model id to a pricing tier."""
    if not model:
        return _DEFAULT_TIER
    m = model.lower()
    if "kimi" in m and "thinking" in m:
        return "kimi_thinking"
    if "kimi" in m:
        return "kimi"
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return _DEFAULT_TIER


def estimate_claude_cost(in_tokens: int, out_tokens: int, model: str = "") -> float:
    """
    Approximate USD cost. Function name kept for backward compatibility — now
    handles Kimi (default) and legacy Claude tiers.
    """
    tier = _model_tier(model)
    rates = _LLM_PRICING.get(tier, _LLM_PRICING[_DEFAULT_TIER])
    cost_in = (in_tokens or 0) / 1_000_000 * rates["in"]
    cost_out = (out_tokens or 0) / 1_000_000 * rates["out"]
    return round(cost_in + cost_out, 4)


def log_claude_call(
    mode: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    success: bool,
    context_chars: Optional[int] = None,
    decisions_count: int = 0,
    error: Optional[str] = None,
) -> Optional[str]:
    """Claude API çağrısı için kullanışlı wrapper."""
    return log_event(
        "claude_call",
        {
            "mode": mode,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": estimate_claude_cost(input_tokens, output_tokens, model=model),
            "context_chars": context_chars,
            "decisions_count": decisions_count,
            "duration_ms": duration_ms,
            "success": 1 if success else 0,
            "error": error,
        },
    )


def log_fmp_call(
    endpoint: str,
    status: int,
    duration_ms: int,
    retry_count: int = 0,
    response_size: Optional[int] = None,
    error: Optional[str] = None,
) -> Optional[str]:
    """FMP API çağrısı için."""
    return log_event(
        "fmp_call",
        {
            "endpoint": endpoint,
            "status": status,
            "duration_ms": duration_ms,
            "retry_count": retry_count,
            "response_size": response_size,
            "success": 1 if status == 200 else 0,
            "error": error,
        },
    )


def log_decision(
    mode: str,
    tip: str,
    portfoy: str,
    sembol: str,
    neden: str,
    pct: int = 0,
    hedef_fiyat: Optional[float] = None,
    stop: Optional[float] = None,
    aciliyet: str = "bugün",
    claude_call_id: Optional[str] = None,
    executed: bool = False,
    skipped_reason: Optional[str] = None,
) -> Optional[str]:
    """Claude'dan çıkan karar için."""
    return log_event(
        "decision",
        {
            "mode": mode,
            "tip": tip,
            "portfoy": portfoy,
            "sembol": sembol,
            "pct": pct,
            "neden": neden,
            "hedef_fiyat": hedef_fiyat,
            "stop": stop,
            "aciliyet": aciliyet,
            "claude_call_id": claude_call_id,
            "executed": 1 if executed else 0,
            "skipped_reason": skipped_reason,
        },
    )


def update_decision_executed(
    decision_id: str,
    executed: bool = True,
    skipped_reason: Optional[str] = None,
    trade_id: Optional[str] = None,
) -> bool:
    """
    Daha önce log_decision ile kaydedilmiş kararın executed alanını günceller.
    Decision → trade loop'unu kapar, query_decision_hitrate anlamlı olur.

    NOT: JSONL append-only. SQLite index'te UPDATE + JSONL'e "decision_update" event
    kaydı (audit trail). Yeniden indexleme durumunda JSONL'den SQLite rebuild
    update kaydını görüp SQL'de güncelleyebilir.
    """
    if not decision_id:
        return False

    # JSONL'e audit event
    try:
        log_event("decision_update", {
            "decision_id": decision_id,
            "executed": 1 if executed else 0,
            "skipped_reason": skipped_reason,
            "trade_id": trade_id,
        })
    except Exception as e:
        print(f"[observability] decision_update audit yazımı atlandı: {e}")

    # SQLite update
    try:
        conn = _get_conn()
        conn.execute(
            """
            UPDATE decisions
            SET executed = ?, skipped_reason = COALESCE(?, skipped_reason)
            WHERE id = ?
            """,
            (1 if executed else 0, skipped_reason, decision_id),
        )
        conn.close()
        return True
    except Exception as e:
        print(f"[observability] update_decision_executed hata: {e}")
        return False


def log_trade(
    action: str,
    portfoy: str,
    sembol: str,
    shares: float,
    price: float,
    total: float,
    reason: str,
    decision_id: Optional[str] = None,
) -> Optional[str]:
    """Gerçekleşmiş alım/satım için."""
    return log_event(
        "trade",
        {
            "action": action,
            "portfoy": portfoy,
            "sembol": sembol,
            "shares": shares,
            "price": price,
            "total": total,
            "reason": reason,
            "decision_id": decision_id,
            "success": 1,
        },
    )


# ── Sorgu yardımcıları ────────────────────────────────────────────────────────

def query_claude_cost(since_days: int = 7) -> dict:
    """Son N gündeki Claude maliyet özeti."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*) AS n_calls,
                SUM(input_tokens) AS total_in,
                SUM(output_tokens) AS total_out,
                SUM(cost_usd) AS total_cost,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failures
            FROM claude_calls
            WHERE ts >= datetime('now', ?)
            """,
            (f"-{since_days} days",),
        )
        row = cur.fetchone()
        conn.close()
        return {
            "since_days": since_days,
            "calls": row[0] or 0,
            "input_tokens": row[1] or 0,
            "output_tokens": row[2] or 0,
            "cost_usd": round(row[3] or 0, 4),
            "failures": row[4] or 0,
        }
    except Exception as e:
        return {"error": str(e)}


def query_fmp_stats(since_days: int = 7) -> list[dict]:
    """Endpoint bazlı FMP kullanım istatistiği."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                endpoint,
                COUNT(*) AS n,
                AVG(duration_ms) AS avg_ms,
                SUM(CASE WHEN status != 200 THEN 1 ELSE 0 END) AS failures
            FROM fmp_calls
            WHERE ts >= datetime('now', ?)
            GROUP BY endpoint
            ORDER BY n DESC
            """,
            (f"-{since_days} days",),
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {"endpoint": r[0], "calls": r[1], "avg_ms": round(r[2] or 0, 1), "failures": r[3]}
            for r in rows
        ]
    except Exception as e:
        return [{"error": str(e)}]


def query_decision_hitrate(since_days: int = 30) -> dict:
    """Decision execution oranı."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                tip,
                COUNT(*) AS n,
                SUM(executed) AS executed_n
            FROM decisions
            WHERE ts >= datetime('now', ?)
            GROUP BY tip
            """,
            (f"-{since_days} days",),
        )
        rows = cur.fetchall()
        conn.close()
        return {
            "since_days": since_days,
            "by_type": [
                {
                    "tip": r[0],
                    "count": r[1],
                    "executed": r[2],
                    "rate_pct": round((r[2] / r[1] * 100) if r[1] else 0, 1),
                }
                for r in rows
            ],
        }
    except Exception as e:
        return {"error": str(e)}


# ── Self-test (modül çalıştırılınca) ─────────────────────────────────────────

if __name__ == "__main__":
    print(f"EVENTS_JSONL: {EVENTS_JSONL}")
    print(f"DB_PATH: {DB_PATH}")

    # Test kayıtlar
    eid = log_claude_call(
        mode="test",
        model="claude-opus-4-7",
        input_tokens=1000,
        output_tokens=500,
        duration_ms=3500,
        success=True,
        context_chars=5000,
        decisions_count=2,
    )
    print(f"Test claude_call logged: {eid}")

    eid = log_fmp_call(
        endpoint="quote",
        status=200,
        duration_ms=120,
        response_size=1500,
    )
    print(f"Test fmp_call logged: {eid}")

    eid = log_decision(
        mode="morning",
        tip="EKLE",
        portfoy="balanced",
        sembol="AAPL",
        neden="Test kaydı",
        pct=100,
    )
    print(f"Test decision logged: {eid}")

    # Sorgu testi
    print("\nSon 7 günlük Claude maliyet:")
    print(json.dumps(query_claude_cost(7), indent=2, ensure_ascii=False))

    print("\nSon 7 günlük FMP stats:")
    print(json.dumps(query_fmp_stats(7), indent=2, ensure_ascii=False))

    print("\nSon 30 günlük decision hitrate:")
    print(json.dumps(query_decision_hitrate(30), indent=2, ensure_ascii=False))
