"""
agent/observability.py için unit testler.

Kapsam:
- log_event: JSONL append, UUID/timestamp atama, dönüş değeri
- log_fmp_call: status -> success eşleme, error alanı persist (silent failure regression)
- query_fmp_stats: SQLite aggregation
- Graceful degradation: SQLite hata olursa JSONL hâlâ yazılır

Çalıştırma:
    cd repo_root && python -m pytest tests/test_observability.py -v

Tasarım: gerçek SQLite ve JSONL'e yazılır ama monkeypatch ile tmp_path'a
yönlendirilir, repo'nun logs/events.jsonl ve data/finzora.db dosyalarına
DOKUNULMAZ.
"""

import json
import sys
from pathlib import Path

import pytest

# agent/ modülünü import path'e ekle
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "agent"))

import observability  # noqa: E402


# ── Fixture: her test kendi tmp_path'ini kullansın ────────────────────────────

@pytest.fixture
def tmp_obs(tmp_path, monkeypatch):
    """observability modülünü tmp_path'a yönlendir — yan etki yok."""
    jsonl_path = tmp_path / "logs" / "events.jsonl"
    db_path = tmp_path / "data" / "finzora.db"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(observability, "EVENTS_JSONL", jsonl_path)
    monkeypatch.setattr(observability, "DB_PATH", db_path)

    # SQLite şema init'i ilk yazımda gerçekleşir
    yield {"jsonl": jsonl_path, "db": db_path}


def _read_jsonl(path: Path) -> list[dict]:
    """JSONL dosyasını liste olarak oku."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ── Test grubu 1: log_event temel davranış ────────────────────────────────────

class TestLogEvent:
    """log_event ana JSONL writer."""

    def test_writes_to_jsonl(self, tmp_obs):
        """log_event çağrısı JSONL dosyasına satır ekler."""
        observability.log_event("test_event", {"foo": "bar"})
        events = _read_jsonl(tmp_obs["jsonl"])
        assert len(events) == 1
        assert events[0]["type"] == "test_event"
        assert events[0]["foo"] == "bar"

    def test_event_has_id_and_timestamp(self, tmp_obs):
        """Her event id ve ts (ISO 8601 UTC) alanlarına sahip."""
        observability.log_event("ping", {})
        events = _read_jsonl(tmp_obs["jsonl"])
        ev = events[0]
        assert "id" in ev
        assert len(ev["id"]) == 12  # _new_id kısa hex
        assert "ts" in ev
        assert ev["ts"].endswith("+00:00") or "Z" in ev["ts"]  # UTC marker

    def test_unique_ids(self, tmp_obs):
        """Ardışık event'ler farklı id alır."""
        ids = set()
        for i in range(20):
            event_id = observability.log_event("ping", {"i": i})
            ids.add(event_id)
        assert len(ids) == 20, "20 event'in 20 unique id'si olmalı"

    def test_returns_event_id(self, tmp_obs):
        """Başarılı yazım event_id döner."""
        event_id = observability.log_event("ping", {})
        assert event_id is not None
        assert len(event_id) == 12

    def test_multiple_events_append(self, tmp_obs):
        """Çoklu log_event çağrıları append olur, overwrite değil."""
        observability.log_event("e1", {})
        observability.log_event("e2", {})
        observability.log_event("e3", {})
        events = _read_jsonl(tmp_obs["jsonl"])
        assert len(events) == 3
        assert [e["type"] for e in events] == ["e1", "e2", "e3"]


# ── Test grubu 2: log_fmp_call status -> success eşleme ───────────────────────

class TestLogFmpCallSuccess:
    """log_fmp_call status code'a göre success doğru hesaplıyor mu."""

    def test_status_200_success_1(self, tmp_obs):
        """200 status -> success=1."""
        observability.log_fmp_call(
            endpoint="quote", status=200, duration_ms=50, response_size=100
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        assert ev["success"] == 1
        assert ev["status"] == 200

    def test_status_429_success_0(self, tmp_obs):
        """429 rate limit -> success=0."""
        observability.log_fmp_call(
            endpoint="quote", status=429, duration_ms=14000, retry_count=3
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        assert ev["success"] == 0
        assert ev["status"] == 429
        assert ev["retry_count"] == 3

    def test_status_404_success_0(self, tmp_obs):
        """404 endpoint not found -> success=0."""
        observability.log_fmp_call(
            endpoint="bad-endpoint", status=404, duration_ms=50
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        assert ev["success"] == 0

    def test_status_500_success_0(self, tmp_obs):
        """500 server error -> success=0."""
        observability.log_fmp_call(
            endpoint="quote", status=500, duration_ms=200
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        assert ev["success"] == 0


# ── Test grubu 3: error alanı persist (silent failure regression) ─────────────

class TestErrorFieldPersistence:
    """
    10 May 2026 silent failure bug'ı regression koruması.
    fmp_client'tan error mesajı geldiğinde JSONL'e doğru yazılmalı.
    """

    def test_error_message_persisted(self, tmp_obs):
        """error parametresi log'a doğru yazılır."""
        observability.log_fmp_call(
            endpoint="quote",
            status=429,
            duration_ms=14000,
            retry_count=3,
            error="429_rate_limit (attempt 3/3)",
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        assert ev["error"] == "429_rate_limit (attempt 3/3)", \
            "error mesajı persist edilmedi — silent failure regression"

    def test_body_limit_reach_error_persisted(self, tmp_obs):
        """body Limit Reach error mesajı log'a yazılır."""
        observability.log_fmp_call(
            endpoint="quote",
            status=200,  # body'de error olsa da HTTP 200
            duration_ms=14000,
            retry_count=3,
            error="body_limit_reach (attempt 3/3)",
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        assert ev["error"] == "body_limit_reach (attempt 3/3)"

    def test_error_none_is_explicit_null(self, tmp_obs):
        """error=None verilirse JSONL'de null olarak kalır (success path)."""
        observability.log_fmp_call(
            endpoint="quote", status=200, duration_ms=50
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        # error alanı None geçti, JSONL'de null olarak görünmeli
        assert ev["error"] is None

    def test_error_field_truncation_safe(self, tmp_obs):
        """Çok uzun error mesajı bile temiz yazılır (UTF-8)."""
        long_err = "x" * 500
        observability.log_fmp_call(
            endpoint="quote", status=500, duration_ms=100, error=long_err
        )
        ev = _read_jsonl(tmp_obs["jsonl"])[0]
        assert ev["error"] == long_err


# ── Test grubu 4: query_fmp_stats aggregation ────────────────────────────────

class TestQueryFmpStats:
    """SQLite üzerinden query_fmp_stats aggregation doğruluğu."""

    def test_aggregates_by_endpoint(self, tmp_obs):
        """Aynı endpoint'e çoklu çağrı tek satırda toplanır."""
        for _ in range(5):
            observability.log_fmp_call(
                endpoint="quote", status=200, duration_ms=10
            )
        for _ in range(3):
            observability.log_fmp_call(
                endpoint="profile", status=200, duration_ms=20
            )
        stats = observability.query_fmp_stats(since_days=1)
        endpoints = {s["endpoint"]: s for s in stats}
        assert "quote" in endpoints
        assert endpoints["quote"]["calls"] == 5
        assert "profile" in endpoints
        assert endpoints["profile"]["calls"] == 3

    def test_failure_count_correct(self, tmp_obs):
        """failure_count = status != 200 olan kayıt sayısı."""
        observability.log_fmp_call(endpoint="x", status=200, duration_ms=10)
        observability.log_fmp_call(endpoint="x", status=429, duration_ms=10)
        observability.log_fmp_call(endpoint="x", status=429, duration_ms=10)
        observability.log_fmp_call(endpoint="x", status=404, duration_ms=10)
        stats = observability.query_fmp_stats(since_days=1)
        x_stat = next(s for s in stats if s["endpoint"] == "x")
        assert x_stat["calls"] == 4
        assert x_stat["failures"] == 3


# ── Test grubu 5: Graceful degradation ────────────────────────────────────────

class TestGracefulDegradation:
    """Hata path'lerinde sistem çökmemeli."""

    def test_jsonl_write_failure_returns_none(self, tmp_obs, monkeypatch):
        """JSONL yazımı patlarsa log_event None döner, exception fırlatmaz."""
        def bad_open(*args, **kw):
            raise PermissionError("Test: yazılamıyor")

        # Path.open()'a patch
        monkeypatch.setattr(Path, "open", bad_open)
        result = observability.log_event("ping", {})
        assert result is None  # Hata path'i None döndürür, exception fırlatmaz

    def test_sqlite_failure_does_not_break_jsonl(self, tmp_obs, monkeypatch):
        """SQLite index patlasa bile JSONL hâlâ yazılır."""
        def bad_index(_):
            raise RuntimeError("Test: SQLite bozuk")

        monkeypatch.setattr(observability, "_index_to_sqlite", bad_index)
        event_id = observability.log_event("ping", {"foo": "bar"})
        # JSONL yine yazıldı
        events = _read_jsonl(tmp_obs["jsonl"])
        assert len(events) == 1
        assert events[0]["foo"] == "bar"
        # event_id de döndü
        assert event_id is not None
