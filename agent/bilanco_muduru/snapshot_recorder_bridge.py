"""
Bilanço Müdürü — Snapshot Recorder Bridge

earnings_night.snapshot_recorder'a hata-toleranslı wrapper.
"""
from __future__ import annotations
from typing import Optional


def snapshot_to_valuation_inputs(snapshot: dict) -> dict:
    """earnings_night modülünden import et."""
    from agent.earnings_night.snapshot_recorder import snapshot_to_valuation_inputs as _impl
    return _impl(snapshot)


def record_snapshot_safe(ticker: str) -> bool:
    """
    Snapshot kaydet, hata durumunda False döner (raise etmez).
    """
    try:
        from agent.earnings_night.snapshot_recorder import record_snapshot
        record_snapshot(ticker)
        return True
    except Exception as e:
        print(f"[BilancoMuduru] {ticker} snapshot hatası: {e}")
        return False
