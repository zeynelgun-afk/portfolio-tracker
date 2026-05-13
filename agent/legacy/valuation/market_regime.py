"""
Finzora Valuation Framework v5 — Market Regime Detector
=========================================================
SPY SMA21 tabanlı boğa/ayı piyasası rejim tespiti.
Rejim, fair value hesabına carpan olarak uygulanabilir
(aynı şirket için boğa/ayı piyasasında farklı fair value).

BOĞA multiplier:  1.12 (çarpan genişlemesi, +%12 premi)
AYI multiplier:   0.87 (çarpan sıkışması, %13 iskonto)

Orijinal: scripts/adil_deger_calculator.py (v2)
Taşındı:  v5 framework, 2026-04-19
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

try:
    from fmp_client import fmp_get
except ImportError:
    import requests
    FMP_KEY = os.environ.get("FMP_API_KEY", "")
    FMP_BASE = "https://financialmodelingprep.com/stable"

    def fmp_get(endpoint, params=None):
        p = (params or {}); p["apikey"] = FMP_KEY
        try:
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
            return r.json()
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# SABITLER
# ─────────────────────────────────────────────────────────────────────────────

BOGA_REJIM_MULT = 1.12  # Boğa: çarpan genişlemesi (+%12 premi)
AYI_REJIM_MULT  = 0.87  # Ayı: çarpan sıkışması (%13 iskonto)
NOTR_REJIM_MULT = 1.00  # Nötr

_CACHE = None  # (rejim, spy_p, sma21, detay)
_CACHE_TS: float = 0  # Son fetch zamanı
_CACHE_TTL_SECONDS = 3600  # 1 saat — SPY/SMA21 bu süre içinde anlamlı değişmez


def _safe(v, default=None):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def get_market_regime() -> tuple[str, float | None, float | None, str]:
    """
    SPY SMA21 bazlı boğa/ayı piyasası rejim tespiti.

    BOGA: SPY fiyatı > 21 günlük hareketli ortalama
    AYI:  SPY fiyatı < 21 günlık hareketli ortalama

    1-saat TTL cache (önceden process-lifetime cache vardı — bu
    Railway 7/24 bot'ta günler sonra stale veri sorunu yaratıyordu).
    Returns: (rejim: 'BOGA'|'AYI', spy_price, sma21, detay_str)
    """
    global _CACHE, _CACHE_TS
    import time as _t

    # Cache hit?
    if _CACHE is not None and (_t.time() - _CACHE_TS) < _CACHE_TTL_SECONDS:
        return _CACHE

    try:
        spy_q   = fmp_get("quote", {"symbol": "SPY"})
        spy_sma = fmp_get("technical-indicators/sma",
                          {"symbol": "SPY", "periodLength": 21, "timeframe": "1day"})
        spy_p   = _safe(spy_q[0].get("price")) if spy_q else None
        sma21   = _safe(spy_sma[0].get("sma")) if spy_sma else None

        if spy_p and sma21:
            fark_pct = (spy_p / sma21 - 1) * 100
            rejim = "BOGA" if spy_p >= sma21 else "AYI"
            emoji = "🐂" if rejim == "BOGA" else "🐻"
            yon = ">" if rejim == "BOGA" else "<"
            detay = (f"{emoji} {rejim} PİYASASI: "
                     f"SPY ${spy_p:.2f} {yon} SMA21 ${sma21:.2f} ({fark_pct:+.1f}%)")
        else:
            rejim = "BOGA"
            detay = "🐂 BOGA (SPY verisi alınamadı — varsayılan)"
            spy_p = sma21 = None

        _CACHE = (rejim, spy_p, sma21, detay)
        _CACHE_TS = _t.time()

    except Exception as e:
        _CACHE = ("BOGA", None, None, f"🐂 BOGA (hata: {e} — varsayılan)")
        _CACHE_TS = _t.time()

    return _CACHE


def get_regime_multiplier() -> float:
    """Aktif rejim için multiplier. Fair value'yu bununla çarpmak mümkün."""
    rejim, _, _, _ = get_market_regime()
    if rejim == "BOGA":
        return BOGA_REJIM_MULT
    elif rejim == "AYI":
        return AYI_REJIM_MULT
    return NOTR_REJIM_MULT


def reset_cache():
    """Test/force-refresh için cache temizle."""
    global _CACHE, _CACHE_TS
    _CACHE = None
    _CACHE_TS = 0


if __name__ == "__main__":
    rejim, spy, sma, detay = get_market_regime()
    print(detay)
    print(f"Multiplier: {get_regime_multiplier()}")
