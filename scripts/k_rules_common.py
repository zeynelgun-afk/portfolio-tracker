#!/usr/bin/env python3
"""
Finzora AI - K Kuralları Ortak Yardımcı Modülü
TRADING_PLAYBOOK.md K-09, K-14, K-15b, K-16, K-17, K-19, K-20 scriptleri için.
(K-18 kaldırıldı — 11 Nisan 2026, backtest sonucu)

Kullanım (diğer k* scriptlerinden):
  from k_rules_common import fmp_get, load_portfolios, get_all_positions, send_k_alert, get_sector
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# --- CONFIG ---
FMP_KEY = os.environ.get("FMP_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Telegram entegrasyonu için telegram_notify modülünü kullan
sys.path.insert(0, str(SCRIPTS_DIR))


def fmp_get(endpoint, params=None):
    """FMP stable API çağrısı. Hata durumunda None döner."""
    params = params or {}
    params["apikey"] = FMP_KEY
    url = f"{FMP_BASE}/{endpoint.lstrip('/')}"
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
        print(f"[FMP HATA] {endpoint} → HTTP {r.status_code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[FMP HATA] {endpoint} → {e}", file=sys.stderr)
        return None


def load_portfolios():
    """3 portföyü dict olarak döndürür: {'balanced': {...}, 'aggressive': {...}, 'dividend': {...}}"""
    out = {}
    for name in ["balanced", "aggressive", "dividend"]:
        path = DATA_DIR / "portfolios" / f"{name}.json"
        if path.exists():
            with open(path) as f:
                out[name] = json.load(f)
        else:
            out[name] = {"pozisyonlar": []}
    return out


def get_all_positions():
    """Tüm aktif pozisyonları liste olarak döndürür. Her pozisyon dict, 'portfoy' anahtarı eklenir."""
    portfolios = load_portfolios()
    positions = []
    for name, p in portfolios.items():
        for pos in p.get("pozisyonlar", []):
            pos_copy = dict(pos)
            pos_copy["portfoy"] = name
            positions.append(pos_copy)
    return positions


def get_swing_active():
    """Aktif swing trade'leri döndürür."""
    path = DATA_DIR / "swing" / "active.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get("aktif_pozisyonlar", [])


# Global quiet mode flag (geriye dönük uyumluluk için, artık varsayılan davranış True).
# YENİ DAVRANIŞ (8 nisan 2026): info severity'si varsayılan olarak telegram'a gitmez.
# --notify flag'i veya send_k_alert(..., force=True) ile opt-in mümkün.
_QUIET_MODE = True

def set_quiet_mode(enabled: bool):
    """Quiet mode set. Varsayılan True (info skip). Eski --quiet flag'i için geriye dönük uyumluluk."""
    global _QUIET_MODE
    _QUIET_MODE = enabled


def send_k_alert(rule, symbol, message, severity="info", force=False):
    """Telegram alert gönder. severity: info, warning, critical.
    Varsayılan: info severity telegram'a gitmez (spam önleme).
    force=True → info da gönderilir (kritik sistem bildirimleri için).
    warning/critical her durumda gider."""
    icons = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
    icon = icons.get(severity, "ℹ️")

    # Varsayılan: info severity skip. force=True ile override edilebilir.
    if severity == "info" and _QUIET_MODE and not force:
        print(f"[{rule} {symbol}] info (quiet default, telegram skip)")
        return True

    text = f"{icon} <b>{rule}</b> | {symbol}\n\n{message}"
    try:
        from telegram_notify import send_message
        send_message(text)
        print(f"[TELEGRAM] {rule} {symbol} → gönderildi")
        return True
    except Exception as e:
        print(f"[TELEGRAM HATA] {rule} {symbol} → {e}", file=sys.stderr)
        print(f"\n--- ALERT (telegram failed) ---\n{text}\n--- END ---")
        return False


# Sektör eşleştirme: hisse → SPDR sektör ETF
SECTOR_MAP = {
    # XLK technology
    "NVDA": "XLK", "MSFT": "XLK", "AAPL": "XLK", "GOOGL": "XLK", "GOOG": "XLK",
    "MRVL": "XLK", "COHR": "XLK", "CRDO": "XLK", "CAMT": "XLK", "AVGO": "XLK",
    "AMAT": "XLK", "KLAC": "XLK", "LRCX": "XLK", "ADBE": "XLK", "CRM": "XLK",
    "ORCL": "XLK", "INTC": "XLK", "AMD": "XLK", "QCOM": "XLK", "TXN": "XLK",
    "CTSH": "XLK", "ZS": "XLK", "PANW": "XLK", "CRWD": "XLK", "FTNT": "XLK",
    "TYL": "XLK", "SMCI": "XLK", "ALMU": "XLK",
    # XLC communication services
    "META": "XLC", "NFLX": "XLC", "T": "XLC", "VZ": "XLC", "TMUS": "XLC",
    "DIS": "XLC", "CMCSA": "XLC", "EA": "XLC", "TTWO": "XLC",
    # XLE energy
    "XOM": "XLE", "CVX": "XLE", "COP": "XLE", "EOG": "XLE", "SLB": "XLE",
    "HAL": "XLE", "FANG": "XLE", "OXY": "XLE", "DVN": "XLE", "VLO": "XLE",
    "MPC": "XLE", "PSX": "XLE", "AR": "XLE", "AROC": "XLE", "KOS": "XLE",
    "SM": "XLE",
    # XLI industrials
    "CAT": "XLI", "GE": "XLI", "LMT": "XLI", "RTX": "XLI", "NOC": "XLI",
    "GD": "XLI", "POWL": "XLI", "VRT": "XLI", "ETN": "XLI", "PWR": "XLI",
    "HII": "XLI", "TDG": "XLI", "TDY": "XLI", "BA": "XLI", "HON": "XLI",
    "UPS": "XLI", "FDX": "XLI", "DAL": "XLI", "UAL": "XLI", "AAL": "XLI",
    "LUV": "XLI",
    # XLV healthcare
    "JNJ": "XLV", "UNH": "XLV", "LLY": "XLV", "PFE": "XLV", "ABBV": "XLV",
    "MRK": "XLV", "MDT": "XLV", "DVA": "XLV", "TMO": "XLV", "ABT": "XLV",
    "CVS": "XLV", "AMGN": "XLV", "GILD": "XLV", "BMY": "XLV", "ISRG": "XLV",
    # XLF financials
    "JPM": "XLF", "BAC": "XLF", "GS": "XLF", "MS": "XLF", "BRK.B": "XLF",
    "V": "XLF", "MA": "XLF", "WFC": "XLF", "C": "XLF", "AXP": "XLF",
    "BLK": "XLF", "SOFI": "XLF", "PYPL": "XLF",
    # XLY consumer discretionary
    "AMZN": "XLY", "TSLA": "XLY", "HD": "XLY", "LOW": "XLY", "MCD": "XLY",
    "SBUX": "XLY", "NKE": "XLY", "TGT": "XLY", "BKNG": "XLY", "ABNB": "XLY",
    # XLP consumer staples (K-19 swing yasak!)
    "MO": "XLP", "PM": "XLP", "PEP": "XLP", "KO": "XLP", "WMT": "XLP",
    "COST": "XLP", "PG": "XLP", "CL": "XLP", "CLX": "XLP", "KMB": "XLP",
    "MDLZ": "XLP", "GIS": "XLP", "K": "XLP", "HSY": "XLP", "MNST": "XLP",
    "KHC": "XLP", "KDP": "XLP", "SYY": "XLP", "TSN": "XLP", "HRL": "XLP",
    # XLU utilities
    "NEE": "XLU", "DUK": "XLU", "SO": "XLU", "CEG": "XLU", "EXC": "XLU",
    "AEP": "XLU", "D": "XLU", "SRE": "XLU", "XEL": "XLU", "PCG": "XLU",
    # XLB materials
    "LIN": "XLB", "APD": "XLB", "FCX": "XLB", "NEM": "XLB", "RGLD": "XLB",
    "ECL": "XLB", "DD": "XLB", "DOW": "XLB", "GOLD": "XLB", "FNV": "XLB",
    "WPM": "XLB", "MP": "XLB",
    # XLRE real estate
    "AMT": "XLRE", "PLD": "XLRE", "EQIX": "XLRE", "CCI": "XLRE", "DLR": "XLRE",
    "WELL": "XLRE", "SPG": "XLRE", "O": "XLRE",
}



def get_vix_level():
    """
    Gercek VIX seviyesini merkezi vix_fetcher uzerinden ceker.
    Kaynak zinciri: data/vix_cache.json (15dk TTL) -> Yahoo q1 -> Yahoo q2 -> FMP.

    ONEMLI: FMP'de ^VIX cogu zaman 402 dondurur (plan sinirli).
    VIXY ETF fiyati VIX seviyesiyle ESIT DEGILDIR (contango).
    K-13 eslikleri (<22 / 22-35 / >35) icin bu fonksiyonu kullan.

    Donus: float (VIX seviyesi) veya None (tum kaynaklar patladi)
    """
    try:
        # agent/ klasoruna path ekle
        import sys
        from pathlib import Path
        _agent_dir = Path(__file__).resolve().parent.parent / "agent"
        if str(_agent_dir) not in sys.path:
            sys.path.insert(0, str(_agent_dir))
        from vix_fetcher import get_vix
        value, source = get_vix()
        if source == "default":
            # Hicbir kaynak calismadi, None don ki caller fallback yapsin
            print(f"[VIX] Tum kaynaklar basarisiz, None donuluyor", file=sys.stderr)
            return None
        return float(value)
    except Exception as e:
        print(f"[VIX HATA] vix_fetcher cekilemedi: {e}", file=sys.stderr)
        # Eski Yahoo fallback (vix_fetcher import patlarsa)
        import urllib.request as _ureq
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d"
        try:
            req = _ureq.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = _ureq.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(price)
        except Exception as e2:
            print(f"[VIX HATA] Yahoo fallback da basarisiz: {e2}", file=sys.stderr)
            return None


def get_vix_direction():
    """
    VIX'in yonunu dondurur (+1 yukseliyor, -1 dusuyor, 0 bilinmiyor).

    19 Nisan 2026 guncellenmesi: FMP ^VIX endpoint'i artik calisiyor,
    VIXY proxy'ye gerek kalmadi. ^VIX dogrudan gercek VIX degerini donuyor.
    VIXY fallback olarak kaliyor (^VIX 200 doner ama bazen gecici hata olabilir).

    NOT: batch-quote alan adi changePercentage (TEKIL), changesPercentage DEGIL.
    """
    # 1. Once ^VIX dene (dogrudan VIX)
    data = fmp_get("quote", {"symbol": "^VIX"})
    if data and isinstance(data, list) and data:
        chg = data[0].get("changePercentage", 0) or 0
        if chg != 0:
            return 1 if chg > 0 else -1

    # 2. VIXY fallback (sadece yon; contango nedeniyle seviye degil)
    data = fmp_get("batch-quote", {"symbols": "VIXY"})
    if data and isinstance(data, list) and data:
        chg = data[0].get("changePercentage", 0) or 0
        return 1 if chg > 0 else (-1 if chg < 0 else 0)
    return 0


def get_sector(symbol):
    """Hisse sembolü için SPDR sektör ETF döndürür. Bilinmiyorsa FMP'den profile çek."""
    sym = symbol.upper()
    if sym in SECTOR_MAP:
        return SECTOR_MAP[sym]
    # FMP fallback
    data = fmp_get("profile", {"symbol": sym})
    if data and isinstance(data, list) and data:
        gics = data[0].get("sector", "")
        gics_to_etf = {
            "Technology": "XLK", "Information Technology": "XLK",
            "Communication Services": "XLC",
            "Energy": "XLE",
            "Industrials": "XLI",
            "Health Care": "XLV", "Healthcare": "XLV",
            "Financial Services": "XLF", "Financials": "XLF",
            "Consumer Cyclical": "XLY", "Consumer Discretionary": "XLY",
            "Consumer Defensive": "XLP", "Consumer Staples": "XLP",
            "Utilities": "XLU",
            "Basic Materials": "XLB", "Materials": "XLB",
            "Real Estate": "XLRE",
        }
        return gics_to_etf.get(gics, "UNKNOWN")
    return "UNKNOWN"


# Tema eşleştirme: K-17 anlatı bazlı tema
THEME_MAP = {
    "AI_TEDARIK_ZINCIRI": ["NVDA", "MRVL", "COHR", "POWL", "CAMT", "VRT", "ANET", "CRDO",
                            "AVGO", "AMAT", "KLAC", "LRCX", "TSM", "MU", "SMCI", "DELL",
                            "ALMU", "CEG", "DUK", "ETN", "PWR", "MP", "ASML"],
    "ENERJI_PETROL": ["XOM", "CVX", "COP", "EOG", "SLB", "HAL", "FANG", "OXY", "DVN",
                       "VLO", "MPC", "PSX", "AR", "AROC", "KOS", "SM"],
    "SAVUNMA_JEOPOLITIK": ["LMT", "NOC", "RTX", "GD", "HII", "TDG", "TDY", "KTOS"],
    "ALTIN_DEFANSIF": ["NEM", "GOLD", "RGLD", "FNV", "WPM", "GLD", "GDX"],
    "REIT": ["AMT", "PLD", "EQIX", "CCI", "DLR", "WELL", "SPG", "O"],
    "MEGA_CAP_TECH": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "TSLA"],
    "SIBER_GUVENLIK": ["PANW", "CRWD", "FTNT", "ZS", "S", "OKTA"],
    "FINANS_BANKA": ["JPM", "BAC", "GS", "MS", "WFC", "C"],
    "TELEKOM": ["T", "VZ", "TMUS"],
    "TUTUN": ["MO", "PM", "BTI"],
}


def get_themes(symbol):
    """Hisse hangi temalara ait listesi döndürür."""
    sym = symbol.upper()
    return [theme for theme, syms in THEME_MAP.items() if sym in syms]


if __name__ == "__main__":
    # Test
    print("=== K Rules Common Helper Test ===")
    print(f"FMP_KEY: {FMP_KEY[:10]}...")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"\nNVDA sektör: {get_sector('NVDA')}")
    print(f"NVDA temalar: {get_themes('NVDA')}")
    print(f"POWL sektör: {get_sector('POWL')}")
    print(f"POWL temalar: {get_themes('POWL')}")
    print(f"\nAktif pozisyonlar: {len(get_all_positions())}")
    for p in get_all_positions()[:5]:
        print(f"  {p['portfoy']}/{p['sembol']}")
