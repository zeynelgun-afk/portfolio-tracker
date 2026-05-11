"""
FMP Endpoint Layer — Adil Değer Skill v5.0
================================================

Ultimate plan endpoint'lerini saran wrapper modülü.

Özellikler:
- TTL cache (5 dakika) — aynı çağrı tekrarlanmaz
- 3 deneme retry + exponential backoff
- Statik fallback verisi (API down ise)
- Tüm yanıtlar normalize edilmiş tek bir format

v5.0 — 11 Mayıs 2026
finzora ai
"""

import os
import time
import json
import requests
import sys
from datetime import datetime, timedelta

API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
BASE = "https://financialmodelingprep.com/stable"

# TTL Cache — endpoint adı + parametre hash → (data, timestamp)
_CACHE = {}
_CACHE_TTL_SECONDS = 300  # 5 dakika


def _fetch(endpoint, params=None, timeout=30, max_retries=3, retry_delay=1.5):
    """
    Düşük seviye fetch — retry + cache.
    """
    cache_key = f"{endpoint}::{json.dumps(params or {}, sort_keys=True)}"
    now = time.time()
    
    # Cache hit?
    if cache_key in _CACHE:
        data, ts = _CACHE[cache_key]
        if now - ts < _CACHE_TTL_SECONDS:
            return data
    
    p = {"apikey": API_KEY}
    if params:
        p.update(params)
    
    last_error = None
    for attempt in range(max_retries):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params=p, timeout=timeout)
            if r.status_code == 200:
                try:
                    data = r.json()
                    _CACHE[cache_key] = (data, now)
                    return data
                except json.JSONDecodeError:
                    return None
            elif r.status_code == 429:
                wait = retry_delay * (2 ** attempt)
                print(f"  [retry] {endpoint} 429, {wait}s bekleniyor", file=sys.stderr)
                time.sleep(wait)
                continue
            elif r.status_code == 503:
                time.sleep(retry_delay)
                continue
            else:
                return None
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
        except Exception as e:
            last_error = e
            break
    
    if last_error:
        print(f"FMP hata {endpoint}: {last_error}", file=sys.stderr)
    return None


# =============================================================================
# TIER 1 — TTM HAZIR ORANLAR (manuel hesap yerine)
# =============================================================================

def get_ratios_ttm(symbol):
    """
    P/E TTM, P/B TTM, ROE TTM, margin'leri hazır verir.
    Skill artık quarterly toplama yapmak zorunda değil.
    
    Returns: dict | None
    """
    data = _fetch("ratios-ttm", {"symbol": symbol})
    if isinstance(data, list) and data:
        return data[0]
    return None


def get_key_metrics_ttm(symbol):
    """
    Enterprise Value, EV/Sales, EV/EBITDA, EV/FCF, ROIC TTM hazır.
    
    Returns: dict | None
    """
    data = _fetch("key-metrics-ttm", {"symbol": symbol})
    if isinstance(data, list) and data:
        return data[0]
    return None


# =============================================================================
# TIER 1 — CANLI SEKTÖR / INDUSTRY P/E (statik tablo yerine)
# =============================================================================

# FMP sector-pe-snapshot endpoint'i FMP'nin kendi sector adlandırmasını kullanır.
# Bizim 'semicon_design' gibi internal key'lerimizden FMP sector adına mapping.
SECTOR_KEY_TO_FMP = {
    'tech_software':        'Technology',
    'tech_hardware':        'Technology',
    'semicon_design':       'Technology',
    'semicon_osat':         'Technology',
    'semicon_equipment':    'Technology',
    'financials_bank':      'Financial Services',
    'financials_insurance': 'Financial Services',
    'financials_other':     'Financial Services',
    'healthcare_pharma':    'Healthcare',
    'healthcare_biotech':   'Healthcare',
    'healthcare_devices':   'Healthcare',
    'consumer_staples':     'Consumer Defensive',
    'consumer_discretionary': 'Consumer Cyclical',
    'industrials':          'Industrials',
    'energy':               'Energy',
    'reits':                'Real Estate',
    'utilities':            'Utilities',
    'communication':        'Communication Services',
    'generic':              None,
}

INDUSTRY_KEY_TO_FMP = {
    'semicon_design':       'Semiconductors',
    'semicon_osat':         'Semiconductors',
    'semicon_equipment':    'Semiconductor Equipment & Materials',
    'tech_software':        'Software - Application',
    'tech_hardware':        'Computer Hardware',
    'healthcare_biotech':   'Biotechnology',
    'healthcare_pharma':    'Drug Manufacturers - General',
    'healthcare_devices':   'Medical Devices',
    'financials_bank':      'Banks - Regional',
    'financials_insurance': 'Insurance - Diversified',
    'communication':        'Internet Content & Information',
}


def get_sector_pe(sector_name, date=None):
    """
    Canlı sektör P/E ortalaması.
    
    Returns: float | None
    """
    if not sector_name:
        return None
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    data = _fetch("sector-pe-snapshot", {"date": date, "sector": sector_name})
    if isinstance(data, list) and data:
        pe = data[0].get("pe")
        try:
            return float(pe) if pe else None
        except (ValueError, TypeError):
            return None
    return None


def get_industry_pe(industry_name, date=None):
    """
    Canlı industry P/E ortalaması (sector'dan daha hassas).
    
    Returns: float | None
    """
    if not industry_name:
        return None
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    data = _fetch("industry-pe-snapshot", {"date": date, "industry": industry_name})
    if isinstance(data, list) and data:
        pe = data[0].get("pe")
        try:
            return float(pe) if pe else None
        except (ValueError, TypeError):
            return None
    return None


def get_live_pe_for_sector_key(sector_key, static_fallback_pe):
    """
    Önce industry P/E dener (hassas), sonra sector P/E (geniş), sonra statik fallback.
    
    sector_key: 'semicon_design' gibi internal key
    static_fallback_pe: SECTOR_MULTIPLES tablosundaki P/E (API down ise)
    
    Returns: (pe, source) — source: 'industry' | 'sector' | 'static'
    """
    industry_name = INDUSTRY_KEY_TO_FMP.get(sector_key)
    if industry_name:
        pe = get_industry_pe(industry_name)
        if pe and 5 <= pe <= 100:  # makul aralık kontrol
            return (pe, 'industry')
    
    sector_name = SECTOR_KEY_TO_FMP.get(sector_key)
    if sector_name:
        pe = get_sector_pe(sector_name)
        if pe and 5 <= pe <= 100:
            return (pe, 'sector')
    
    return (static_fallback_pe, 'static')


# =============================================================================
# TIER 1 — TARİHSEL FİYAT & MARJ (peer rampup analizi için)
# =============================================================================

def get_historical_price_eod(symbol, full=False):
    """
    5 yıllık günlük OHLCV verisi.
    
    full=True: open, high, low, close, vwap, volume, change, changePercent
    full=False: sadece date, price, volume (light)
    
    Returns: list | None
    """
    endpoint = "historical-price-eod/full" if full else "historical-price-eod/light"
    data = _fetch(endpoint, {"symbol": symbol})
    if isinstance(data, list):
        return data
    return None


# =============================================================================
# TIER 1 — STOK PEERS (dinamik karşılaştırma şirketleri)
# =============================================================================

def get_stock_peers(symbol):
    """
    FMP'nin dinamik peer listesi.
    
    Returns: list of dicts [{symbol, companyName, price, mktCap}] | None
    """
    data = _fetch("stock-peers", {"symbol": symbol})
    if isinstance(data, list):
        return data
    return None


# =============================================================================
# TIER 2 — RİSK SKORLARI (Altman Z + Piotroski)
# =============================================================================

def get_financial_scores(symbol):
    """
    Altman Z-Score (iflas riski) + Piotroski Score (fundamental kalitesi).
    
    Returns: dict {altmanZScore, piotroskiScore, ...} | None
    """
    data = _fetch("financial-scores", {"symbol": symbol})
    if isinstance(data, list) and data:
        return data[0]
    return None


def interpret_altman_z(z_score):
    """
    Altman Z-Score yorumu (manufacturing şirketler için).
    
    >2.99: Safe Zone (güvenli)
    1.81-2.99: Grey Zone (belirsiz)
    <1.81: Distress Zone (iflas riski yüksek)
    """
    if z_score is None:
        return None, None, None
    try:
        z = float(z_score)
    except (ValueError, TypeError):
        return None, None, None
    
    if z >= 2.99:
        return (z, "GÜVENLİ", "🟢")
    elif z >= 1.81:
        return (z, "BELİRSİZ", "🟡")
    else:
        return (z, "İFLAS RİSKİ", "🔴")


def interpret_piotroski(score):
    """
    Piotroski F-Score (0-9 arası).
    
    8-9: Çok güçlü fundamental
    5-7: Sağlam
    3-4: Zayıf
    0-2: Çok zayıf
    """
    if score is None:
        return None, None, None
    try:
        s = int(score)
    except (ValueError, TypeError):
        return None, None, None
    
    if s >= 8:
        return (s, "ÇOK GÜÇLÜ", "🟢")
    elif s >= 5:
        return (s, "SAĞLAM", "🟡")
    elif s >= 3:
        return (s, "ZAYIF", "🟠")
    else:
        return (s, "ÇOK ZAYIF", "🔴")


# =============================================================================
# TIER 2 — ANALİST SENTIMENT (Buy/Hold/Sell sayıları + trend)
# =============================================================================

def get_grades_consensus(symbol):
    """
    Mevcut analist sentiment dağılımı.
    
    Returns: dict {strongBuy, buy, hold, sell, strongSell, consensus} | None
    """
    data = _fetch("grades-consensus", {"symbol": symbol})
    if isinstance(data, list) and data:
        return data[0]
    return None


def get_grades_historical(symbol):
    """
    Tarihsel analist rating dağılımı (son ~87 nokta).
    Upgrade momentum tespiti için.
    
    Returns: list of dicts | None
    """
    data = _fetch("grades-historical", {"symbol": symbol})
    if isinstance(data, list):
        return data
    return None


def detect_upgrade_momentum(grades_historical, lookback_months=6):
    """
    Son N ay içinde analist sentiment'ı buy yönünde mi hareket etti?
    
    Returns: dict {direction, magnitude, label} | None
    """
    if not grades_historical or len(grades_historical) < 2:
        return None
    
    # Tarihe göre sırala (yeni → eski)
    sorted_grades = sorted(grades_historical, key=lambda x: x.get('date', ''), reverse=True)
    
    now_date = datetime.now()
    cutoff = now_date - timedelta(days=lookback_months * 30)
    
    recent = None
    past = None
    for g in sorted_grades:
        try:
            d = datetime.strptime(g.get('date', ''), "%Y-%m-%d")
        except ValueError:
            continue
        if recent is None:
            recent = g
        if d <= cutoff and past is None:
            past = g
            break
    
    if not recent or not past:
        return None
    
    def buy_score(g):
        return (g.get('analystRatingsStrongBuy', 0) or 0) * 2 + (g.get('analystRatingsBuy', 0) or 0)
    
    def hold_score(g):
        return g.get('analystRatingsHold', 0) or 0
    
    def sell_score(g):
        return (g.get('analystRatingsStrongSell', 0) or 0) * 2 + (g.get('analystRatingsSell', 0) or 0)
    
    recent_net = buy_score(recent) - sell_score(recent)
    past_net = buy_score(past) - sell_score(past)
    delta = recent_net - past_net
    
    if delta > 3:
        return {"direction": "upgrade", "magnitude": delta, "label": f"🟢 UPGRADE MOMENTUM (+{delta})"}
    elif delta < -3:
        return {"direction": "downgrade", "magnitude": delta, "label": f"🔴 DOWNGRADE TRENDI ({delta})"}
    else:
        return {"direction": "stable", "magnitude": delta, "label": f"⚪ Stabil ({delta:+d})"}


# =============================================================================
# TIER 2 — FMP'NIN KENDİ DCF HESABI (bizim DCF ile karşılaştırma)
# =============================================================================

def get_fmp_dcf(symbol, levered=False):
    """
    FMP'nin kendi DCF hesabı (bizim DCF'le sanity check).
    
    levered=True: levered DCF (borç dahil)
    
    Returns: dict {dcf, stockPrice} | None
    """
    endpoint = "levered-discounted-cash-flow" if levered else "discounted-cash-flow"
    data = _fetch(endpoint, {"symbol": symbol})
    if isinstance(data, list) and data:
        return data[0]
    return None


# =============================================================================
# TIER 2 — REVENUE SEGMENTATION (müşteri/coğrafya konsantrasyon)
# =============================================================================

def get_revenue_product_segmentation(symbol):
    """
    Ürün/segment bazlı gelir kırılımı (NVDA: Data Center %88, Gaming %8, ...).
    
    Returns: list | None
    """
    data = _fetch("revenue-product-segmentation", {"symbol": symbol})
    if isinstance(data, list):
        return data
    return None


def get_revenue_geographic_segmentation(symbol):
    """
    Coğrafya bazlı gelir kırılımı.
    
    Returns: list | None
    """
    data = _fetch("revenue-geographic-segmentation", {"symbol": symbol})
    if isinstance(data, list):
        return data
    return None


def detect_concentration_risk(segmentation_list):
    """
    Bir segment %50+ ise konsantrasyon riski.
    
    Returns: dict {top_segment, top_share, label} | None
    """
    if not segmentation_list:
        return None
    
    # En son fiscal year'ı al
    latest = sorted(segmentation_list, key=lambda x: x.get('date', ''), reverse=True)[0]
    data = latest.get('data', {})
    if not data or not isinstance(data, dict):
        return None
    
    total = sum(v for v in data.values() if isinstance(v, (int, float)) and v > 0)
    if total <= 0:
        return None
    
    sorted_segs = sorted(
        [(k, v) for k, v in data.items() if isinstance(v, (int, float)) and v > 0],
        key=lambda x: x[1], reverse=True
    )
    
    if not sorted_segs:
        return None
    
    top_seg, top_val = sorted_segs[0]
    top_share = top_val / total
    
    top2_share = sum(v for _, v in sorted_segs[:2]) / total if len(sorted_segs) >= 2 else top_share
    
    if top_share >= 0.70:
        label = f"🔴 KRİTİK: {top_seg} %{top_share*100:.0f}"
    elif top_share >= 0.50:
        label = f"🟠 YÜKSEK: {top_seg} %{top_share*100:.0f}"
    elif top2_share >= 0.75:
        label = f"🟡 ORTA: Top 2 segment %{top2_share*100:.0f}"
    else:
        label = f"🟢 DAĞINIK: En büyük segment %{top_share*100:.0f}"
    
    return {
        "top_segment": top_seg,
        "top_share_pct": round(top_share * 100, 1),
        "top2_share_pct": round(top2_share * 100, 1),
        "label": label,
        "fiscal_year": latest.get('fiscalYear', latest.get('date', 'N/A'))
    }


# =============================================================================
# TIER 2 — TARİHSEL EV (5 yıllık multiple bandı)
# =============================================================================

def get_enterprise_values(symbol):
    """
    5 yıllık tarihsel Enterprise Value.
    
    Returns: list of dicts | None
    """
    data = _fetch("enterprise-values", {"symbol": symbol})
    if isinstance(data, list):
        return data
    return None


# =============================================================================
# TIER 3 — TREASURY RATES (DCF WACC için)
# =============================================================================

def get_10y_treasury_rate():
    """
    10 yıllık ABD hazine bonosu faizi (DCF WACC risk-free rate olarak).
    
    Returns: float (%) | None
    """
    data = _fetch("treasury-rates")
    if isinstance(data, list) and data:
        # En son tarih
        sorted_data = sorted(data, key=lambda x: x.get('date', ''), reverse=True)
        for d in sorted_data:
            y10 = d.get('year10')
            try:
                rate = float(y10)
                if rate > 0:
                    # year10 = 4.38 anlam %4.38 — direkt kullan
                    return rate / 100
            except (ValueError, TypeError):
                continue
    return None


def calculate_dynamic_wacc(beta, equity_risk_premium=0.06, country_risk_premium=0.0):
    """
    CAPM ile dinamik WACC hesabı.
    
    WACC = Rf + Beta × ERP + Country Risk
    
    Rf: 10y treasury (canlı)
    ERP: %6 (ABD piyasa standart)
    Country Risk: 0 (ABD)
    
    Beta yoksa veya treasury alınamazsa fallback %12.
    """
    rf = get_10y_treasury_rate()
    if rf is None:
        return 0.12, "fallback (rf alınamadı)"
    
    if beta is None or beta <= 0:
        beta = 1.2  # tech default
    
    wacc = rf + beta * equity_risk_premium + country_risk_premium
    
    # Sınır kontrol
    wacc = max(0.08, min(0.18, wacc))
    
    return wacc, f"CAPM (Rf %{rf*100:.2f} + Beta {beta} × ERP %{equity_risk_premium*100:.0f})"


# =============================================================================
# TIER 3 — IPO TAKVİMİ (Pre-IPO otomatik tespit)
# =============================================================================

def get_ipos_calendar(from_date=None, to_date=None):
    """
    Yakın dönem IPO takvimi.
    
    Returns: list of dicts | None
    """
    if not from_date:
        from_date = datetime.now().strftime("%Y-%m-%d")
    if not to_date:
        to_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    
    data = _fetch("ipos-calendar", {"from": from_date, "to": to_date})
    if isinstance(data, list):
        return data
    return None


def is_ticker_pre_ipo(symbol):
    """
    Ticker önümüzdeki 60 gün içinde IPO oluyor mu?
    
    Returns: dict {is_pre_ipo, ipo_date, price_range, ...} | None
    """
    calendar = get_ipos_calendar()
    if not calendar:
        return None
    
    for ipo in calendar:
        if ipo.get('symbol', '').upper() == symbol.upper():
            return {
                "is_pre_ipo": True,
                "ipo_date": ipo.get('date'),
                "company": ipo.get('company'),
                "exchange": ipo.get('exchange'),
                "price_range": ipo.get('priceRange'),
                "shares": ipo.get('shares'),
                "market_cap": ipo.get('marketCap'),
                "actions": ipo.get('actions'),
            }
    
    return None


# =============================================================================
# TIER 3 — FİNANSAL BÜYÜME ORANLARI (5 yıllık)
# =============================================================================

def get_financial_growth(symbol):
    """
    5 yıllık büyüme oranları (revenueGrowth, ebitGrowth, freeCashFlowGrowth vs).
    
    Returns: list of dicts | None
    """
    data = _fetch("financial-growth", {"symbol": symbol})
    if isinstance(data, list):
        return data
    return None


# =============================================================================
# CACHE YARDIMCI
# =============================================================================

def clear_cache():
    """Test/debug için cache temizle."""
    global _CACHE
    _CACHE = {}


def cache_stats():
    """Cache durumu."""
    return {"entries": len(_CACHE), "ttl_seconds": _CACHE_TTL_SECONDS}
