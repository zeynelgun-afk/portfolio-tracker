"""
Tests — Price-Target Gap Gate (15 May 2026)

VIK gozleminden dogan gate:
  - Analist hareketi pozitif olsa bile fiyat hedef bandinin ustunde/yakinindaysa
    AL kararlari WATCH'a dusurulur.
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from agent.legacy.analist_takip.signal_analyzer import (
    analyze_signals,
    price_target_gap_gate,
    _apply_gate_cap,
)


# === Gate fonksiyonu unit testleri ===

def test_gate_no_data_returns_disabled():
    """Fiyat yoksa gate atlanir (UNKNOWN/STRONG_BUY)."""
    r = price_target_gap_gate(None, None)
    assert r["enabled"] is False
    assert r["max_decision"] == "STRONG_BUY"


def test_gate_vik_scenario_skip():
    """VIK gozlemi: fiyat 86.72, avg 81.60 (-6%), high 95 (+10%), low 59 (-32%)."""
    r = price_target_gap_gate(
        86.72,
        {"avg": 81.60, "high": 95.00, "low": 59.00, "num_analysts": 5},
    )
    assert r["enabled"] is True
    assert r["gap_quality"] == "SKIP"
    assert r["max_decision"] == "WATCH"
    assert r["upside_avg_pct"] < 0
    assert r["upside_max_pct"] < 15
    assert r["risk_reward"] < 0  # negatif upside, negatif R/R


def test_gate_strong_quality():
    """Fiyat 100, avg 130 (+30%), high 150 (+50%), low 90 (-10%) → STRONG."""
    r = price_target_gap_gate(
        100.0,
        {"avg": 130.0, "high": 150.0, "low": 90.0, "num_analysts": 10},
    )
    assert r["gap_quality"] == "STRONG"
    assert r["max_decision"] == "STRONG_BUY"
    assert r["risk_reward"] == 3.0  # 30/10


def test_gate_medium_quality():
    """Fiyat 100, avg 110 (+10%), high 125 (+25%), low 94 (-6%) → MEDIUM."""
    r = price_target_gap_gate(
        100.0,
        {"avg": 110.0, "high": 125.0, "low": 94.0, "num_analysts": 8},
    )
    assert r["gap_quality"] == "MEDIUM"
    assert r["max_decision"] == "BUY"


def test_gate_watch_quality():
    """Fiyat 100, avg 106 (+6%), high 118 (+18%), low 95 (-5%) → WATCH."""
    r = price_target_gap_gate(
        100.0,
        {"avg": 106.0, "high": 118.0, "low": 95.0, "num_analysts": 7},
    )
    assert r["gap_quality"] == "WATCH"
    assert r["max_decision"] == "WATCH"


def test_gate_skip_when_max_below_high_floor():
    """Fiyat 100, avg 108, high 112 (+12% — WATCH floor altinda) → SKIP."""
    r = price_target_gap_gate(
        100.0,
        {"avg": 108.0, "high": 112.0, "low": 90.0, "num_analysts": 5},
    )
    assert r["gap_quality"] == "SKIP"


def test_gate_handles_missing_low():
    """Low yoksa R/R hesaplanmaz ama avg/max'a gore karar verilir."""
    r = price_target_gap_gate(
        100.0,
        {"avg": 130.0, "high": 150.0, "low": None, "num_analysts": 3},
    )
    # R/R yok ama avg/max STRONG threshold gecti
    assert r["gap_quality"] == "STRONG"
    assert r["risk_reward"] is None


# === Cap helper ===

def test_cap_strong_buy_to_buy_on_medium():
    assert _apply_gate_cap("STRONG_BUY", "BUY") == "BUY"


def test_cap_buy_unchanged_on_strong_buy_max():
    assert _apply_gate_cap("BUY", "STRONG_BUY") == "BUY"


def test_cap_sells_untouched():
    assert _apply_gate_cap("SELL", "WATCH") == "SELL"
    assert _apply_gate_cap("STRONG_SELL", "WATCH") == "STRONG_SELL"


def test_cap_buy_to_watch_on_skip():
    assert _apply_gate_cap("BUY", "WATCH") == "WATCH"


# === Entegrasyon: analyze_signals + gate ===

def _make_raise(date, company, old_t, new_t, change_pct):
    """Test icin sahte raise sinyali."""
    return {
        "published_at": date,
        "direction": "raised",
        "action": "raised",
        "old_target": old_t,
        "new_target": new_t,
        "price_target": new_t,
        "change_pct": change_pct,
        "analyst_company": company,
        "grading_company": company,
    }


def test_analyze_vik_scenario_buy_downgraded_to_watch():
    """
    VIK orijinal kararı: BUY (4 raise + 1 downgrade tolere edildi).
    Gate fiyat-hedef boslugu kotu oldugu icin BUY → WATCH dusurmeli.
    """
    now = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
    earnings = (now - timedelta(days=3)).date()

    raises = [
        _make_raise(now - timedelta(hours=2), "Barclays", 76, 88, 15.8),
        _make_raise(now - timedelta(hours=3), "Goldman Sachs", 84, 95, 13.1),
        _make_raise(now - timedelta(hours=4), "Mizuho", 69, 75, 8.7),
        _make_raise(now - timedelta(hours=5), "Susquehanna", 100, 105, 5.0),
    ]
    downgrade = {
        "published_at": now - timedelta(hours=6),
        "direction": "downgrade",
        "action": "downgrade",
        "previous_grade": "Buy",
        "new_grade": "Hold",
        "analyst_company": "BTIG",
        "grading_company": "BTIG",
    }
    signals = raises + [downgrade]

    result = analyze_signals(
        "VIK", signals,
        now=now,
        last_earnings_date=earnings,
        require_post_earnings=True,
        current_price=86.72,
        target_consensus={
            "avg": 81.60, "high": 95.00, "low": 59.00, "num_analysts": 5,
        },
    )

    assert result["original_decision"] == "BUY", \
        f"Orijinal karar BUY beklendi, geldi: {result['original_decision']}"
    assert result["decision"] == "WATCH", \
        f"Gate sonrasi WATCH beklendi, geldi: {result['decision']}"
    assert result["gate_applied"] is True
    assert result["gap_quality"] == "SKIP"


def test_analyze_strong_quality_passes_through():
    """Iyi gap (STRONG) durumunda STRONG_BUY/BUY kararlari degismez."""
    now = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
    earnings = (now - timedelta(days=2)).date()

    # 1 raise +25% → STRONG_BUY tetiklenir (avg %25 > %20 esigi)
    raises = [
        _make_raise(now - timedelta(hours=2), "Goldman", 80, 100, 25.0),
    ]

    result = analyze_signals(
        "TEST", raises,
        now=now,
        last_earnings_date=earnings,
        require_post_earnings=True,
        current_price=100.0,
        target_consensus={"avg": 130.0, "high": 150.0, "low": 90.0},
    )

    assert result["decision"] == "STRONG_BUY", \
        f"STRONG_BUY beklendi, geldi: {result['decision']}"
    assert result["gate_applied"] is False
    assert result["gap_quality"] == "STRONG"


def test_analyze_strong_buy_capped_to_buy_on_medium_gap():
    """STRONG_BUY (3 raise + 0 dnowngrade + avg %20+) ama gap MEDIUM → BUY."""
    now = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
    earnings = (now - timedelta(days=2)).date()

    # 3 raise, avg %25 → STRONG_BUY
    raises = [
        _make_raise(now - timedelta(hours=2), "GS", 80, 100, 25.0),
        _make_raise(now - timedelta(hours=3), "MS", 80, 100, 25.0),
        _make_raise(now - timedelta(hours=4), "Citi", 80, 100, 25.0),
    ]

    result = analyze_signals(
        "TEST", raises,
        now=now,
        last_earnings_date=earnings,
        require_post_earnings=True,
        current_price=100.0,
        # Gap MEDIUM: avg +10% (>=8), high +25% (>=20), low -6% → R/R 1.67 (>=1.5)
        target_consensus={"avg": 110.0, "high": 125.0, "low": 94.0},
    )

    assert result["original_decision"] == "STRONG_BUY"
    assert result["decision"] == "BUY"
    assert result["gate_applied"] is True
    assert result["gap_quality"] == "MEDIUM"


def test_analyze_no_price_data_skips_gate():
    """Fiyat/hedef yoksa gate atlanir, orijinal karar gecer."""
    now = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
    earnings = (now - timedelta(days=2)).date()

    raises = [
        _make_raise(now - timedelta(hours=2), "GS", 80, 100, 25.0),
    ]

    result = analyze_signals(
        "TEST", raises,
        now=now,
        last_earnings_date=earnings,
        require_post_earnings=True,
        current_price=None,
        target_consensus=None,
    )

    # 1 raise +25% → STRONG_BUY (avg ≥ 20%, raised ≥ 1, 0 downgrade)
    assert result["decision"] == "STRONG_BUY"
    assert result["gate_applied"] is False
    assert result["gap_quality"] == "UNKNOWN"


def test_analyze_sell_unaffected_by_gate():
    """SELL kararlarina gate dokunmaz."""
    now = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
    earnings = (now - timedelta(days=2)).date()

    lowereds = [
        {
            "published_at": now - timedelta(hours=2),
            "direction": "lowered",
            "action": "lowered",
            "old_target": 100,
            "new_target": 70,
            "change_pct": -30.0,
            "analyst_company": "GS",
            "grading_company": "GS",
        },
        {
            "published_at": now - timedelta(hours=3),
            "direction": "lowered",
            "action": "lowered",
            "old_target": 100,
            "new_target": 75,
            "change_pct": -25.0,
            "analyst_company": "MS",
            "grading_company": "MS",
        },
    ]

    result = analyze_signals(
        "TEST", lowereds,
        now=now,
        last_earnings_date=earnings,
        require_post_earnings=True,
        # Suni iyimserce gap (low cok asagi, R/R yuksek) — yine de SELL kalmali
        current_price=50.0,
        target_consensus={"avg": 80.0, "high": 100.0, "low": 45.0},
    )

    assert result["decision"] in ("SELL", "STRONG_SELL")
    # Gate hesaplandi ama uygulanmadi (SELL'lere dokunulmuyor)
    assert result["gate_applied"] is False


if __name__ == "__main__":
    import traceback
    tests = [
        test_gate_no_data_returns_disabled,
        test_gate_vik_scenario_skip,
        test_gate_strong_quality,
        test_gate_medium_quality,
        test_gate_watch_quality,
        test_gate_skip_when_max_below_high_floor,
        test_gate_handles_missing_low,
        test_cap_strong_buy_to_buy_on_medium,
        test_cap_buy_unchanged_on_strong_buy_max,
        test_cap_sells_untouched,
        test_cap_buy_to_watch_on_skip,
        test_analyze_vik_scenario_buy_downgraded_to_watch,
        test_analyze_strong_quality_passes_through,
        test_analyze_strong_buy_capped_to_buy_on_medium_gap,
        test_analyze_no_price_data_skips_gate,
        test_analyze_sell_unaffected_by_gate,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
    sys.exit(0 if failed == 0 else 1)
