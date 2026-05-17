"""agent/reports/stats.py Polymarket kalibratör istatistikleri testleri.

Faz 2 — Adım 13: stats.py'a kalibratör event analizi.

KAPSAM:
    - _load_calibrator_tracker: missing / corrupt / valid
    - query_calibrator_stats:
        * tracker yok → error
        * boş events → 0 stats
        * filter cutoff doğru
        * by_flag dağılımı
        * by_multiplier dağılımı
        * by_source dağılımı
        * top_themes / top_symbols sıralı
        * outcome_status: pending_phase10
        * days_collected + phase10_progress
    - format_calibrator_section:
        * Error case → uyarı mesajı
        * 0 event → kısa not
        * Dolu stats → tüm tablolar
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.reports import stats


def _make_event(symbol: str, theme: str, flag: str, mult: float,
                ts: datetime, src: str = "thematic",
                outcome_7d: float | None = None) -> dict:
    return {
        "id": f"evt_{symbol}",
        "ts": ts.isoformat(),
        "candidate_symbol": symbol,
        "candidate_source": src,
        "candidate_original_score": 0.5,
        "applied_flag": flag,
        "applied_multiplier": mult,
        "matched_theme": theme,
        "matched_side": "negative" if flag.startswith("pm_conflict") else "positive",
        "market_slug": "test-slug",
        "market_delta_24h": 0.1,
        "outcome_7d": outcome_7d,
        "outcome_14d": None,
        "outcome_30d": None,
    }


def _write_tracker(tmp_path: Path, events: list[dict],
                    started_at: datetime | None = None) -> Path:
    path = tmp_path / "polymarket_calibrator_performance.json"
    data: dict = {"_version": "v1", "events": events}
    if started_at:
        data["_started_at"] = started_at.isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── _load_calibrator_tracker ───────────────────────────────────────────────────


class TestLoadTracker:
    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "missing.json")
        assert stats._load_calibrator_tracker() == {}

    def test_corrupt_json(self, tmp_path, monkeypatch):
        path = tmp_path / "bad.json"
        path.write_text("{not valid")
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)
        assert stats._load_calibrator_tracker() == {}

    def test_non_dict_root(self, tmp_path, monkeypatch):
        path = tmp_path / "list-root.json"
        path.write_text(json.dumps(["not-a-dict"]))
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)
        assert stats._load_calibrator_tracker() == {}

    def test_valid_tracker(self, tmp_path, monkeypatch):
        path = _write_tracker(tmp_path, [])
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)
        result = stats._load_calibrator_tracker()
        assert result.get("_version") == "v1"


# ── query_calibrator_stats ─────────────────────────────────────────────────────


class TestQueryStats:
    def test_missing_tracker_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "missing.json")
        result = stats.query_calibrator_stats(days=7)
        assert "error" in result
        assert result["total_events"] == 0

    def test_empty_events_returns_zero(self, tmp_path, monkeypatch):
        path = _write_tracker(tmp_path, [])
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)
        result = stats.query_calibrator_stats(days=7)
        assert result["total_events"] == 0
        assert result["by_flag"] == {}
        assert result["by_multiplier"] == {}

    def test_filter_cutoff(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        events = [
            _make_event("OLD", "t1", "pm_confirm", 1.20,
                        now - timedelta(days=10)),  # excluded (10g > 7g)
            _make_event("NEW", "t1", "pm_confirm", 1.20,
                        now - timedelta(hours=2)),  # included
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["total_events"] == 1
        assert result["by_flag"] == {"pm_confirm": 1}

    def test_by_flag_distribution(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        events = [
            _make_event("A", "t1", "pm_confirm", 1.20, now - timedelta(hours=1)),
            _make_event("B", "t1", "pm_confirm", 1.20, now - timedelta(hours=2)),
            _make_event("C", "t1", "pm_conflict", 0.75, now - timedelta(hours=3)),
            _make_event("D", "t1", "pm_confirm_weak", 1.10, now - timedelta(hours=4)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["by_flag"] == {
            "pm_confirm": 2,
            "pm_conflict": 1,
            "pm_confirm_weak": 1,
        }

    def test_by_multiplier(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        events = [
            _make_event("A", "t1", "pm_confirm", 1.20, now - timedelta(hours=1)),
            _make_event("B", "t1", "pm_conflict", 0.75, now - timedelta(hours=2)),
            _make_event("C", "t1", "pm_conflict", 0.75, now - timedelta(hours=3)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["by_multiplier"] == {"1.20x": 1, "0.75x": 2}

    def test_by_source(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        events = [
            _make_event("A", "t1", "pm_confirm", 1.20,
                        now - timedelta(hours=1), src="fair_value"),
            _make_event("B", "t1", "pm_confirm", 1.20,
                        now - timedelta(hours=2), src="thematic"),
            _make_event("C", "t1", "pm_confirm", 1.20,
                        now - timedelta(hours=3), src="thematic"),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["by_source"] == {"thematic": 2, "fair_value": 1}

    def test_top_themes_sorted(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        # theme_a: 3, theme_b: 1, theme_c: 2
        events = [
            _make_event(f"A{i}", "theme_a", "pm_confirm", 1.20,
                        now - timedelta(hours=i)) for i in range(3)
        ] + [
            _make_event("B", "theme_b", "pm_confirm", 1.20,
                        now - timedelta(hours=4))
        ] + [
            _make_event(f"C{i}", "theme_c", "pm_confirm", 1.20,
                        now - timedelta(hours=5+i)) for i in range(2)
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        themes = result["top_themes"]
        # En çok event olan tema önce
        assert themes[0] == ("theme_a", 3)
        assert themes[1] == ("theme_c", 2)
        assert themes[2] == ("theme_b", 1)

    def test_top_symbols_sorted(self, tmp_path, monkeypatch):
        now = datetime.now(timezone.utc)
        # LMT: 3 event, NVDA: 1
        events = [
            _make_event("LMT", "t1", "pm_confirm", 1.20,
                        now - timedelta(hours=i)) for i in range(3)
        ] + [
            _make_event("NVDA", "t1", "pm_confirm", 1.20,
                        now - timedelta(hours=4))
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["top_symbols"][0] == ("LMT", 3)
        assert result["top_symbols"][1] == ("NVDA", 1)

    def test_outcome_status_pending(self, tmp_path, monkeypatch):
        """outcome_*_d field'ları None → pending_phase10."""
        now = datetime.now(timezone.utc)
        events = [
            _make_event("A", "t1", "pm_confirm", 1.20, now - timedelta(hours=1)),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["outcome_status"] == "pending_phase10"

    def test_outcome_status_partial(self, tmp_path, monkeypatch):
        """En az 1 event'in outcome'u dolu → partial."""
        now = datetime.now(timezone.utc)
        events = [
            _make_event("A", "t1", "pm_confirm", 1.20,
                        now - timedelta(hours=1), outcome_7d=0.05),
        ]
        path = _write_tracker(tmp_path, events)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["outcome_status"] == "partial"

    def test_phase10_progress(self, tmp_path, monkeypatch):
        """30 günlük hedef için doğru progress yüzdesi."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=15)  # 50% progress
        path = _write_tracker(tmp_path, [
            _make_event("A", "t1", "pm_confirm", 1.20, now - timedelta(hours=1))
        ], started_at=start)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        # 15 gün / 30 gün = 50%
        assert 49 <= result["phase10_progress_pct"] <= 51
        assert 14.9 <= result["days_collected"] <= 15.1

    def test_phase10_progress_capped_100(self, tmp_path, monkeypatch):
        """30+ gün geçtiyse %100'de sabitlenmeli."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=45)
        path = _write_tracker(tmp_path, [
            _make_event("A", "t1", "pm_confirm", 1.20, now - timedelta(hours=1))
        ], started_at=start)
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH", path)

        result = stats.query_calibrator_stats(days=7)
        assert result["phase10_progress_pct"] == 100.0


# ── format_calibrator_section ──────────────────────────────────────────────────


class TestFormatSection:
    def test_error_case(self):
        section = stats.format_calibrator_section({"error": "Tracker yok"})
        text = "\n".join(section)
        assert "Polymarket Kalibratör" in text
        assert "Tracker yok" in text
        assert "CALIBRATOR_ENABLED=true" in text

    def test_zero_events(self):
        section = stats.format_calibrator_section({
            "total_events": 0,
            "by_flag": {},
            "by_multiplier": {},
            "by_source": {},
            "top_themes": [],
            "top_symbols": [],
            "days_collected": 5.0,
            "phase10_progress_pct": 16.7,
            "outcome_status": "no_data",
        })
        text = "\n".join(section)
        assert "0** (henüz yok)" in text
        assert "5.0 gün" in text
        assert "17%" in text or "16%" in text

    def test_full_stats(self):
        section = stats.format_calibrator_section({
            "total_events": 10,
            "by_flag": {"pm_confirm": 6, "pm_conflict": 4},
            "by_multiplier": {"1.20x": 6, "0.75x": 4},
            "by_source": {"thematic": 7, "fair_value": 3},
            "top_themes": [("china_taiwan", 4), ("ai_chips", 3)],
            "top_symbols": [("TSM", 3), ("NVDA", 2)],
            "days_collected": 10.0,
            "phase10_progress_pct": 33.3,
            "outcome_status": "pending_phase10",
        })
        text = "\n".join(section)

        # Genel
        assert "Toplam event: **10**" in text
        assert "10.0 gün" in text

        # Flag tablosu
        assert "Bayrak Dağılımı" in text
        assert "pm_confirm" in text
        assert "60.0%" in text  # 6/10

        # Çarpan tablosu (yüksek önce)
        assert "Çarpan Dağılımı" in text
        idx_120 = text.find("1.20x")
        idx_075 = text.find("0.75x")
        assert idx_120 < idx_075

        # Source
        assert "Kaynak Dağılımı" in text
        assert "thematic" in text

        # Top temalar
        assert "En Aktif Temalar" in text
        assert "china_taiwan" in text

        # Top semboller
        assert "En Çok Eşleşen Hisseler" in text
        assert "TSM" in text

        # Outcome note
        assert "Phase 10'da hesaplanacak" in text

    def test_partial_outcome_note(self):
        section = stats.format_calibrator_section({
            "total_events": 5,
            "by_flag": {"pm_confirm": 5},
            "by_multiplier": {"1.20x": 5},
            "by_source": {"thematic": 5},
            "top_themes": [],
            "top_symbols": [],
            "days_collected": 35.0,
            "phase10_progress_pct": 100.0,
            "outcome_status": "partial",
        })
        text = "\n".join(section)
        assert "kısmi veri" in text


# ── format_report entegrasyonu ─────────────────────────────────────────────────


class TestFormatReportIntegration:
    def test_calibrator_section_appears_in_full_report(self, tmp_path, monkeypatch):
        """format_report kalibratör bölümünü içeriyor."""
        # DB_PATH yok → erken çıkış olmasın diye monkey-patch
        # Aslında DB_PATH.exists() False olduğunda format_report tek satır döndürüyor
        # Kalibratör bölümünü görmek için DB_PATH var gibi yapmalıyız
        from agent.reports.stats import DB_PATH
        monkeypatch.setattr(stats, "_CALIBRATOR_LOG_PATH",
                            tmp_path / "missing.json")

        # DB_PATH yoksa erken çıkış — kalibratör bölümü görünmez
        if not DB_PATH.exists():
            # Boş bir SQLite dosyası oluştur ki erken çıkış olmasın
            import sqlite3
            db_tmp = tmp_path / "fake.db"
            conn = sqlite3.connect(db_tmp)
            conn.close()
            monkeypatch.setattr(stats, "DB_PATH", db_tmp)
            # query_* fonksiyonlar exception veya boş döndürebilir; tolere et
            monkeypatch.setattr(stats, "query_claude_cost",
                                lambda d: {"calls": 0, "failures": 0,
                                            "input_tokens": 0, "output_tokens": 0,
                                            "cost_usd": 0.0})
            monkeypatch.setattr(stats, "query_fmp_stats", lambda d: [])
            monkeypatch.setattr(stats, "query_decision_hitrate",
                                lambda d: {"by_type": []})

        report = stats.format_report(days=7)
        assert "Polymarket Kalibratör" in report
