"""scripts/watchlist_health_check.py için testler.

Faz 2 — Adım 11: Pozisyon #3 cron entry-point.

KAPSAM:
    - State load/save: idempotency
    - _prune_old_state: 24h+ eski entry'ler temizlenir
    - _is_new_alert: aynı (symbol, theme, flag) → False
    - _format_dm: çoklu alert tek mesajda toplanır
    - run_check: boş watchlist graceful
    - run_check: alert yok → dm_sent=False
    - run_check: yeni alert → dm_sent=True, state güncellenir
    - run_check: aynı alert ikinci tur → DM yok (cooldown)
    - run_check: 24h+ eski alert tekrar DM (cooldown geçti)
    - run_check: calibrator init exception graceful
    - run_check: dry-run state güncellenir, DM atılmaz
"""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "watchlist_health_check.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "watchlist_health_check", _SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── State helpers ──────────────────────────────────────────────────────────────


class TestStateHelpers:
    def test_prune_old_state_removes_expired(self):
        wh = _load_script()
        now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
        state = {
            "alerts": [
                # 30h önce — temizlenir
                {"symbol": "OLD", "theme_id": "t1", "flag": "pm_conflict",
                 "ts": (now - timedelta(hours=30)).isoformat()},
                # 23h önce — kalır
                {"symbol": "RECENT", "theme_id": "t1", "flag": "pm_conflict",
                 "ts": (now - timedelta(hours=23)).isoformat()},
                # Bozuk
                {"symbol": "BAD", "ts": "not-a-date"},
            ]
        }
        result = wh._prune_old_state(state, now)
        symbols = [a["symbol"] for a in result["alerts"]]
        assert "OLD" not in symbols
        assert "RECENT" in symbols
        assert "BAD" not in symbols

    def test_is_new_alert(self):
        wh = _load_script()
        state = {"alerts": [
            {"symbol": "LMT", "theme_id": "ct", "flag": "pm_conflict"}
        ]}
        # Aynı tuple — yeni değil
        assert wh._is_new_alert(
            {"symbol": "LMT", "theme_id": "ct", "flag": "pm_conflict"},
            state,
        ) is False
        # Farklı flag — yeni
        assert wh._is_new_alert(
            {"symbol": "LMT", "theme_id": "ct", "flag": "pm_conflict_weak"},
            state,
        ) is True
        # Farklı symbol — yeni
        assert wh._is_new_alert(
            {"symbol": "TSM", "theme_id": "ct", "flag": "pm_conflict"},
            state,
        ) is True


# ── DM format ──────────────────────────────────────────────────────────────────


class TestFormatDm:
    def test_strong_alert_red_icon(self):
        wh = _load_script()
        alert = {
            "symbol": "TSM", "theme_id": "china_taiwan",
            "matched_side": "negative", "market_slug": "taiwan-2026",
            "delta_24h": 0.15, "flag": "pm_conflict", "severity": "strong",
        }
        text = wh._format_alert(alert)
        assert "🔴" in text
        assert "TSM" in text
        assert "+15.0pp" in text or "+15.0" in text

    def test_weak_alert_yellow_icon(self):
        wh = _load_script()
        alert = {
            "symbol": "TSM", "theme_id": "china_taiwan",
            "matched_side": "negative", "market_slug": "s1",
            "delta_24h": 0.05, "flag": "pm_conflict_weak", "severity": "weak",
        }
        text = wh._format_alert(alert)
        assert "🟡" in text

    def test_multi_alert_dm(self):
        wh = _load_script()
        alerts = [
            {"symbol": "TSM", "theme_id": "ct", "matched_side": "negative",
             "market_slug": "s1", "delta_24h": 0.15, "flag": "pm_conflict",
             "severity": "strong"},
            {"symbol": "NVDA", "theme_id": "ct", "matched_side": "negative",
             "market_slug": "s1", "delta_24h": 0.05, "flag": "pm_conflict_weak",
             "severity": "weak"},
        ]
        text = wh._format_dm(alerts)
        assert "TSM" in text
        assert "NVDA" in text
        assert "2" in text  # yeni alert sayısı
        assert "1 güçlü" in text
        assert "1 zayıf" in text


# ── run_check end-to-end ───────────────────────────────────────────────────────


class _MockCalibrator:
    """Test için stub kalibratör."""

    def __init__(self, alerts_to_return):
        self._alerts = alerts_to_return

    def watchlist_health_check(self, symbols):
        return list(self._alerts)


class TestRunCheck:
    def test_empty_watchlist(self, tmp_path, monkeypatch):
        wh = _load_script()
        monkeypatch.setattr(wh, "_STATE_PATH", tmp_path / "state.json")

        result = wh.run_check(
            symbols=[],
            calibrator=_MockCalibrator([]),
            dry_run=True,
        )
        assert result == {"total_alerts": 0, "new_alerts": 0, "dm_sent": False}

    def test_no_alerts(self, tmp_path, monkeypatch):
        wh = _load_script()
        monkeypatch.setattr(wh, "_STATE_PATH", tmp_path / "state.json")

        result = wh.run_check(
            symbols=["AAPL", "NVDA"],
            calibrator=_MockCalibrator([]),
            dry_run=True,
        )
        assert result["dm_sent"] is False

    def test_new_alert_dm_sent_state_updated(self, tmp_path, monkeypatch):
        wh = _load_script()
        state_path = tmp_path / "state.json"
        monkeypatch.setattr(wh, "_STATE_PATH", state_path)

        alerts = [
            {"symbol": "TSM", "theme_id": "ct", "theme_label": "Çin-Tayvan",
             "matched_side": "negative", "market_slug": "taiwan",
             "delta_24h": 0.15, "flag": "pm_conflict", "severity": "strong"},
        ]
        result = wh.run_check(
            symbols=["TSM"],
            calibrator=_MockCalibrator(alerts),
            dry_run=True,
        )
        assert result["total_alerts"] == 1
        assert result["new_alerts"] == 1
        # dry-run dm_sent True (gönderildi sayılır)
        assert result["dm_sent"] is True

        # State dosyası yazıldı
        assert state_path.exists()
        state = json.loads(state_path.read_text())
        assert len(state["alerts"]) == 1
        assert state["alerts"][0]["symbol"] == "TSM"

    def test_repeat_alert_cooldown_no_dm(self, tmp_path, monkeypatch):
        """Aynı alert 24h içinde tekrar → DM yok."""
        wh = _load_script()
        state_path = tmp_path / "state.json"
        monkeypatch.setattr(wh, "_STATE_PATH", state_path)

        now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
        # State'i önceden doldur — 2h önce raporlanmış
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({
            "alerts": [{
                "symbol": "TSM", "theme_id": "ct", "flag": "pm_conflict",
                "ts": (now - timedelta(hours=2)).isoformat(),
            }]
        }))

        alerts = [
            {"symbol": "TSM", "theme_id": "ct", "matched_side": "negative",
             "market_slug": "taiwan", "delta_24h": 0.15, "flag": "pm_conflict",
             "severity": "strong"},
        ]
        result = wh.run_check(
            symbols=["TSM"],
            calibrator=_MockCalibrator(alerts),
            now=now,
            dry_run=True,
        )
        # Alert var ama yeni değil
        assert result["total_alerts"] == 1
        assert result["new_alerts"] == 0
        assert result["dm_sent"] is False

    def test_old_alert_after_cooldown_dm_again(self, tmp_path, monkeypatch):
        """25h+ önceki alert tekrar DM atılır (cooldown geçti)."""
        wh = _load_script()
        state_path = tmp_path / "state.json"
        monkeypatch.setattr(wh, "_STATE_PATH", state_path)

        now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
        # State: 25h önce — cooldown geçti
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({
            "alerts": [{
                "symbol": "TSM", "theme_id": "ct", "flag": "pm_conflict",
                "ts": (now - timedelta(hours=25)).isoformat(),
            }]
        }))

        alerts = [
            {"symbol": "TSM", "theme_id": "ct", "matched_side": "negative",
             "market_slug": "taiwan", "delta_24h": 0.15, "flag": "pm_conflict",
             "severity": "strong"},
        ]
        result = wh.run_check(
            symbols=["TSM"],
            calibrator=_MockCalibrator(alerts),
            now=now,
            dry_run=True,
        )
        # 25h önceki alert prune edildi → yeni sayılır
        assert result["new_alerts"] == 1
        assert result["dm_sent"] is True

    def test_calibrator_init_exception_graceful(self, tmp_path, monkeypatch):
        """PolymarketCalibrator() exception → graceful exit, hiç DM yok."""
        wh = _load_script()
        monkeypatch.setattr(wh, "_STATE_PATH", tmp_path / "state.json")

        # Calibrator'ı patch'le
        from agent.scanners import calibrator as cal_module

        class _BrokenCal:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("init failed")

        monkeypatch.setattr(cal_module, "PolymarketCalibrator", _BrokenCal)

        result = wh.run_check(
            symbols=["AAPL"],
            calibrator=None,  # default → BrokenCal kullanılır
            dry_run=True,
        )
        assert result["total_alerts"] == 0
        assert result["dm_sent"] is False

    def test_calibrate_exception_graceful(self, tmp_path, monkeypatch):
        """calibrator.watchlist_health_check exception → graceful."""
        wh = _load_script()
        monkeypatch.setattr(wh, "_STATE_PATH", tmp_path / "state.json")

        class _ExceptionCal:
            def watchlist_health_check(self, symbols):
                raise RuntimeError("Polymarket cache corrupt")

        result = wh.run_check(
            symbols=["AAPL"],
            calibrator=_ExceptionCal(),
            dry_run=True,
        )
        assert result["total_alerts"] == 0
        assert result["dm_sent"] is False

    def test_mixed_new_and_repeat_alerts(self, tmp_path, monkeypatch):
        """Bir alert yeni, biri cooldown'da → sadece yeni DM'e gider."""
        wh = _load_script()
        state_path = tmp_path / "state.json"
        monkeypatch.setattr(wh, "_STATE_PATH", state_path)

        now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({
            "alerts": [{
                "symbol": "TSM", "theme_id": "ct", "flag": "pm_conflict",
                "ts": (now - timedelta(hours=5)).isoformat(),
            }]
        }))

        alerts = [
            # Tekrar — atlanır
            {"symbol": "TSM", "theme_id": "ct", "matched_side": "negative",
             "market_slug": "s1", "delta_24h": 0.15, "flag": "pm_conflict",
             "severity": "strong"},
            # Yeni
            {"symbol": "NVDA", "theme_id": "ct", "matched_side": "negative",
             "market_slug": "s1", "delta_24h": 0.05, "flag": "pm_conflict_weak",
             "severity": "weak"},
        ]
        result = wh.run_check(
            symbols=["TSM", "NVDA"],
            calibrator=_MockCalibrator(alerts),
            now=now,
            dry_run=True,
        )
        assert result["total_alerts"] == 2
        assert result["new_alerts"] == 1  # Sadece NVDA
        assert result["dm_sent"] is True


# ── main() ─────────────────────────────────────────────────────────────────────


class TestMain:
    def test_main_dry_run_returns_zero(self, tmp_path, monkeypatch, capsys):
        wh = _load_script()
        monkeypatch.setattr(wh, "_STATE_PATH", tmp_path / "state.json")

        # all_symbols boş döndür
        from agent import watchlist
        monkeypatch.setattr(watchlist, "all_symbols", lambda: [])

        rc = wh.main(["--dry-run"])
        assert rc == 0
