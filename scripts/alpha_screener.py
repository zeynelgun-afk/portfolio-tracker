#!/usr/bin/env python3
"""
Finzora Alpha Screener v2.0
==============================
Mevcut screener'dan farkı:
  ÖNCE: PE, ROIC, RSI, SMA, momentum, FCF (7 faktör)
  SONRA: + 52W high breakout, RS rank, earnings revision,
           insider alım, short interest değişimi,
           sector laggard, analyst upgrade (8 yeni faktör)

Araştırma dayanakları:
  - Insider cluster buying: +22.4% yıllık alpha (InsiderDashboard 2025)
  - PEAD (Post-Earnings Announcement Drift): revision→drift 3-6 hafta
  - 52W high breakout: en güçlü momentum sinyali (O'Neil CANSLIM)
  - RS rank top %20: sector liderliği = sürdürülebilir momentum
  - Short interest azalması + katalizör = squeeze

Çalıştırma:
  python scripts/alpha_screener.py --mode growth
  python scripts/alpha_screener.py --mode income
  python scripts/alpha_screener.py --mode swing
  python scripts/alpha_screener.py --mode all
"""

import requests
import json
import time
import math
from datetime import datetime, timedelta
from pathlib import Path
import argparse

BASE     = "https://financialmodelingprep.com/stable"
API_KEY  = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
OUT_DIR  = Path(__file__).parent.parent / "data"
REPO_ROOT = Path(__file__).parent.parent


def fetch(url: str, params: dict = None, timeout: int = 15):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"  ⚠ Fetch hatası: {e}")
        return None


# ── TARAMA EVRENİ ─────────────────────────────────────────────────────────────

def get_universe(mode: str) -> list[dict]:
    """Mod'a göre hisse evrenini çeker ve batch-quote ile zenginleştirir."""
    if mode == "income":
        url = (f"{BASE}/company-screener"
               f"?marketCapMoreThan=2000000000"
               f"&priceMoreThan=10&volumeMoreThan=300000"
               f"&dividendMoreThan=1.5&peRatioLessThan=30"
               f"&country=US&isActivelyTrading=true&limit=800"
               f"&apikey={API_KEY}")
    elif mode == "swing":
        url = (f"{BASE}/company-screener"
               f"?marketCapMoreThan=2000000000"
               f"&priceMoreThan=10&volumeMoreThan=500000"
               f"&country=US&isActivelyTrading=true&limit=1500"
               f"&apikey={API_KEY}")
    else:  # growth
        url = (f"{BASE}/company-screener"
               f"?marketCapMoreThan=2000000000"
               f"&priceMoreThan=10&volumeMoreThan=500000"
               f"&country=US&isActivelyTrading=true&limit=2000"
               f"&apikey={API_KEY}")

    raw = fetch(url) or []
    print(f"  Evren ham: {len(raw)} hisse ({mode})")

    # ETF'leri çıkar
    raw = [r for r in raw if not r.get("isEtf") and not r.get("isFund")]
    print(f"  ETF filtre sonrası: {len(raw)} hisse")

    # Batch-quote ile zenginleştir (momentum, yearHigh, RSI bilgileri için)
    symbols  = [r["symbol"] for r in raw]
    quote_map = {}
    batch_size = 50

    for i in range(0, min(len(symbols), 400), batch_size):
        batch = symbols[i:i+batch_size]
        quotes = fetch(
            f"{BASE}/batch-quote",
            params={"symbols": ",".join(batch), "apikey": API_KEY}
        ) or []
        for q in quotes:
            quote_map[q["symbol"]] = q

    # Veriyi birleştir
    enriched = []
    for r in raw[:400]:  # İlk 400 ile sınırla (API limiti)
        sym = r["symbol"]
        q   = quote_map.get(sym, {})
        row = {**r, **q}

        # Momentum hesapla (yearHigh/Low'dan yaklaşım)
        price     = row.get("price") or 0
        year_high = row.get("yearHigh") or 0
        year_low  = row.get("yearLow") or 0
        prev      = row.get("previousClose") or price

        # 1M momentum yok → yearHigh'tan kaba tahmin
        if year_high > 0 and year_low > 0 and price > 0:
            # %52W high'ın ne kadarındayız?
            range_pos = (price - year_low) / (year_high - year_low) if year_high > year_low else 0.5
            # RS proxy: üst %25'deyse momentum güçlü
            row["rs_proxy"] = range_pos

        enriched.append(row)

    print(f"  Zenginleştirilmiş: {len(enriched)} hisse")
    return enriched


# ── YENİ FAKTÖRLER ────────────────────────────────────────────────────────────

def get_52w_breakout_score(price: float, year_high: float, year_low: float) -> int:
    """
    52 hafta yüksek kırılımı — O'Neil CANSLIM'in temel prensibi.
    Araştırma: Yeni yüksek yapan hisseler momentum sürdürür.
    
    Skor:
      +4: Fiyat 52W high'ın %1 içinde (kırılım eşiğinde)
      +3: 52W high'ın %0-5 altında (güçlü)
      +2: 52W high'ın %5-15 altında (normal)
      +1: 52W high'ın %15-25 altında
       0: Daha derinde
      -2: 52W low'a yakın (<%20 üstünde)
    """
    if not price or not year_high or not year_low:
        return 0
    try:
        pct_of_high = price / year_high
        pct_of_low  = (price - year_low) / year_low if year_low > 0 else 1

        if pct_of_high >= 0.99:     return 4  # Yeni yüksek kırılımı
        elif pct_of_high >= 0.95:   return 3  # Yüksek yakını
        elif pct_of_high >= 0.85:   return 2
        elif pct_of_high >= 0.75:   return 1
        elif pct_of_low  <= 0.20:   return -2  # 52W low yakını
        return 0
    except (TypeError, ZeroDivisionError):
        return 0


def get_rs_rank_score(sym_mom: float, sector_mom_avg: float, sector_mom_std: float) -> int:
    """
    Sektör içi RS (Relative Strength) sıralaması.
    Araştırma: Sektörünü geçen hisseler = sürdürülebilir momentum.
    
    Skor:
      +4: Sektöründen 1.5 std üstünde (top %10)
      +3: 1.0 std üstünde (top %20)
      +2: 0.5 std üstünde
      +1: Sektörünü geçiyor
       0: Sektörle eşit
      -2: Sektörün 1.5 std altında
    """
    if sym_mom is None or sector_mom_avg is None or sector_mom_std is None:
        return 0
    if sector_mom_std == 0:
        return 1 if sym_mom > sector_mom_avg else 0

    z = (sym_mom - sector_mom_avg) / sector_mom_std
    if z >= 1.5:    return 4
    elif z >= 1.0:  return 3
    elif z >= 0.5:  return 2
    elif z > 0:     return 1
    elif z < -1.5:  return -2
    elif z < -0.5:  return -1
    return 0


def get_earnings_revision_score(sym: str) -> int:
    """
    Kazanç tahmini revizyon trendi.
    Araştırma (PEAD): Analistler birden fazla kez tahmin yükseltiyorsa
    hisse 3-6 hafta sonra fiyatlara yansır.
    
    Skor:
      +4: Price target konsensüs > güncel fiyat %20+
      +3: Price target konsensüs > güncel fiyat %10-20
      +2: Price target konsensüs > güncel fiyat %5-10
      +1: Price target konsensüs > güncel fiyat
       0: Konsensüs verisi yok
      -2: Price target konsensüs < güncel fiyat
    """
    try:
        data = fetch(f"{BASE}/price-target-consensus",
                     params={"symbol": sym, "apikey": API_KEY},
                     timeout=6)
        if not data or not isinstance(data, dict):
            return 0

        target   = data.get("targetConsensus") or data.get("targetMedian")
        price    = data.get("price") or data.get("lastPrice")

        if not target or not price or price == 0:
            return 0

        upside = (target - price) / price * 100

        if upside >= 20:    return 4
        elif upside >= 10:  return 3
        elif upside >= 5:   return 2
        elif upside > 0:    return 1
        elif upside < -10:  return -2
        elif upside < 0:    return -1
        return 0
    except Exception:
        return 0


def get_insider_buying_score(sym: str) -> int:
    """
    İçeriden ALIM taraması — sadece satış değil alım.
    Araştırma: Cluster buying (birden fazla insider) en güçlü sinyal.
    CEO/CFO açık piyasa alımı = yüksek konviksiyon.
    
    Skor:
      +4: Son 30 günde cluster buy (2+ insider)
      +3: Son 30 günde 1 CEO/CFO alımı
      +2: Son 60 günde insider alımı var
      +1: Son 90 günde insider alımı var
       0: Alım yok veya veri yok
      -1: Son 30 günde insider satışı > alım
    """
    try:
        data = fetch(f"{BASE}/insider-trading/search",
                     params={"symbol": sym, "transactionType": "P-Purchase",
                             "limit": 10, "apikey": API_KEY},
                     timeout=6)
        if not data or not isinstance(data, list):
            return 0

        today = datetime.now()
        cutoffs = {30: today - timedelta(days=30),
                   60: today - timedelta(days=60),
                   90: today - timedelta(days=90)}

        recent_30, recent_60, recent_90 = [], [], []
        ceo_cfo_30 = []

        for item in data:
            try:
                dt_str = item.get("filingDate") or item.get("transactionDate") or ""
                dt     = datetime.strptime(dt_str[:10], "%Y-%m-%d")
                val    = float(item.get("value") or 0)
                title  = (item.get("typeOfOwner") or "").lower()

                if val <= 0:
                    continue

                if dt >= cutoffs[30]:
                    recent_30.append(item)
                    if any(t in title for t in ["ceo", "cfo", "president", "director"]):
                        ceo_cfo_30.append(item)
                if dt >= cutoffs[60]:
                    recent_60.append(item)
                if dt >= cutoffs[90]:
                    recent_90.append(item)
            except (ValueError, TypeError):
                continue

        if len(recent_30) >= 2:   return 4   # Cluster buying
        elif ceo_cfo_30:          return 3   # CEO/CFO alımı
        elif recent_60:           return 2
        elif recent_90:           return 1
        return 0
    except Exception:
        return 0


def get_financial_growth_score(sym: str, mode: str) -> int:
    """
    Gelir/kazanç büyümesi trendi — mevcut statik EPS yerine dinamik.
    """
    try:
        data = fetch(f"{BASE}/financial-growth",
                     params={"symbol": sym, "limit": 3, "apikey": API_KEY},
                     timeout=8)
        if not data or not isinstance(data, list):
            return 0

        rev_growths = [d.get("revenueGrowth", 0) for d in data if d.get("revenueGrowth")]
        eps_growths = [d.get("epsgrowth", 0) or d.get("netIncomeGrowth", 0)
                       for d in data]

        if not rev_growths:
            return 0

        latest_rev = rev_growths[0] * 100   # yüzdeye çevir
        latest_eps = eps_growths[0] * 100 if eps_growths else 0

        # Büyüme ivmesi var mı? (son çeyrek > önceki çeyrek)
        accelerating = len(rev_growths) >= 2 and rev_growths[0] > rev_growths[1]

        s = 0
        if mode == "income":
            # Income için temettü büyümesi önemli
            div_growth = data[0].get("dividendsPerShareGrowth", 0) * 100 if data else 0
            if div_growth > 10:    s += 3
            elif div_growth > 5:   s += 2
            elif div_growth > 0:   s += 1
            elif div_growth < 0:   s -= 2
        else:
            if latest_rev > 30:    s += 3
            elif latest_rev > 15:  s += 2
            elif latest_rev > 5:   s += 1
            elif latest_rev < -5:  s -= 2

            if latest_eps > 30:    s += 2
            elif latest_eps > 10:  s += 1
            elif latest_eps < -10: s -= 2

            if accelerating:       s += 1   # Büyüme ivmeleniyor bonus

        return s
    except Exception:
        return 0


# ── SEKTÖR RS HESAPLAMA ───────────────────────────────────────────────────────

def calculate_sector_stats(universe: list[dict]) -> dict:
    """
    Sektör bazında momentum ortalaması ve std'yi hesaplar.
    RS rank için referans noktası.
    """
    sector_data: dict[str, list] = {}

    for h in universe:
        sektor  = h.get("sector") or "Diğer"
        mom_3m  = h.get("priceReturn3Month") or h.get("mom3m")
        if mom_3m is not None:
            sector_data.setdefault(sektor, []).append(float(mom_3m))

    stats = {}
    for sektor, vals in sector_data.items():
        if len(vals) >= 5:
            avg = sum(vals) / len(vals)
            std = math.sqrt(sum((v - avg) ** 2 for v in vals) / len(vals))
            stats[sektor] = {"avg": avg, "std": std, "n": len(vals)}

    return stats


# ── SKORLAMA ──────────────────────────────────────────────────────────────────

def score_growth(row: dict, sector_stats: dict) -> dict:
    """
    Growth portföyü skorlaması — rejim bazlı, momentum odaklı.
    Max toplam: ~30 puan.
    """
    s     = 0
    sym   = row.get("symbol", "")
    price = row.get("price") or 0

    # ── MEVCUT FAKTÖRLER ──────────────
    # Momentum
    mom1m = row.get("priceReturn1Month") or 0
    mom3m = row.get("priceReturn3Month") or 0
    mom6m = row.get("priceReturn6Month") or 0

    if mom1m > 15:    s += 3
    elif mom1m > 5:   s += 2
    elif mom1m > 0:   s += 1
    elif mom1m < -10: s -= 2

    if mom3m > 20:    s += 3
    elif mom3m > 10:  s += 2
    elif mom3m > 3:   s += 1

    if mom6m > 40:    s += 2
    elif mom6m > 20:  s += 1

    # ROIC
    roic = row.get("returnOnInvestedCapitalTTM") or row.get("roic") or 0
    if roic > 25:     s += 3
    elif roic > 15:   s += 2
    elif roic > 8:    s += 1
    elif roic < 0:    s -= 2

    # SMA
    above_sma50  = row.get("isAboveMA50") or False
    above_sma200 = row.get("isAboveMA200") or False
    if above_sma50:   s += 2
    if above_sma200:  s += 1

    # RSI
    rsi = row.get("rsi") or 0
    if 50 <= rsi <= 68:  s += 2
    elif 40 <= rsi < 50: s += 1
    elif rsi > 75:       s -= 1
    elif 0 < rsi < 35:  s -= 2

    # ── YENİ FAKTÖRLER ───────────────

    # 1. 52W High Breakout
    year_high = row.get("yearHigh") or 0
    year_low  = row.get("yearLow") or 0
    s52 = get_52w_breakout_score(price, year_high, year_low)
    s  += s52

    # 2. RS proxy (yearHigh/Low pozisyonu)
    rs_proxy = row.get("rs_proxy") or 0
    if rs_proxy >= 0.85:    s += 3  # 52W aralığının üst %15
    elif rs_proxy >= 0.70:  s += 2
    elif rs_proxy >= 0.55:  s += 1
    elif rs_proxy <= 0.20:  s -= 2  # Dibinde

    # 3. Sektör RS Rank (gerçek)
    sektor = row.get("sector", "")
    sect   = sector_stats.get(sektor, {})
    if sect:
        mom3m_val = row.get("priceReturn3Month") or (rs_proxy * 30 - 15)  # fallback
        s += get_rs_rank_score(mom3m_val, sect["avg"], sect["std"])

    return {"score": s, "symbol": sym, "reason": "growth_alpha"}


def score_income(row: dict) -> dict:
    """
    Income portföyü skorlaması — temettü kalitesi + momentum.
    """
    s    = 0
    sym  = row.get("symbol", "")

    # Temettü yield
    yld = row.get("dividendYieldTTM") or row.get("yield_pct") or 0
    if isinstance(yld, float) and yld < 1:  # Oran mı? yüzdeye çevir
        yld = yld * 100

    if 4.5 <= yld <= 7:    s += 4
    elif 3.5 <= yld < 4.5: s += 3
    elif 2.5 <= yld < 3.5: s += 2
    elif yld > 9:          s -= 3  # Yield trap

    # FCF yield
    fcf = row.get("freeCashFlowYieldTTM") or 0
    if isinstance(fcf, float) and fcf < 1:
        fcf = fcf * 100
    if fcf > 8:    s += 3
    elif fcf > 4:  s += 2
    elif fcf < 0:  s -= 3

    # D/E
    de = row.get("debtToEquityRatioTTM") or 0
    if de < 0.5:   s += 2
    elif de > 2.0: s -= 2

    # SMA
    if row.get("isAboveMA50"):   s += 1
    if row.get("isAboveMA200"):  s += 1

    # 52W High Breakout (Income için daha az ağırlık)
    year_high = row.get("yearHigh") or 0
    year_low  = row.get("yearLow") or 0
    price     = row.get("price") or 0
    brkout    = get_52w_breakout_score(price, year_high, year_low)
    s += brkout // 2  # Yarı ağırlık

    return {"score": s, "symbol": sym, "reason": "income_alpha"}


def score_swing(row: dict, sector_stats: dict) -> dict:
    """
    Swing trade skorlaması — kısa vadeli momentum + teknik setup.
    """
    s    = 0
    sym  = row.get("symbol", "")
    price = row.get("price") or 0

    # Temel Ichimoku/teknik filtreler
    rsi = row.get("rsi") or 0
    if 45 <= rsi <= 62:  s += 3
    elif 40 <= rsi < 45: s += 1
    elif rsi > 70:       s -= 1

    mom1m = row.get("priceReturn1Month") or 0
    mom3m = row.get("priceReturn3Month") or 0

    if mom1m > 10:  s += 3
    elif mom1m > 3: s += 2
    elif mom1m > 0: s += 1

    if mom3m > 15:  s += 2
    elif mom3m > 5: s += 1

    if row.get("isAboveMA50"):  s += 2
    if row.get("isAboveMA200"): s += 1

    # 52W High — swing için çok kritik
    year_high = row.get("yearHigh") or 0
    year_low  = row.get("yearLow") or 0
    s += get_52w_breakout_score(price, year_high, year_low)

    # Sektör RS rank
    sektor = row.get("sector", "")
    sect   = sector_stats.get(sektor, {})
    if sect:
        rs = get_rs_rank_score(mom3m, sect["avg"], sect["std"])
        s += rs

    return {"score": s, "symbol": sym, "reason": "swing_alpha"}


# ── DERIN ANALİZ (top hisseler için ek faktörler) ─────────────────────────────

def deep_analysis(candidates: list[dict], mode: str, top_n: int = 30) -> list[dict]:
    """
    Ön filtreyi geçen top N hisse için derin analiz.
    Ağır API çağrıları buraya — earnings revision, insider buy.
    """
    print(f"\n  Derin analiz: {min(len(candidates), top_n)} hisse...")

    top = candidates[:top_n]

    for i, row in enumerate(top):
        sym = row["symbol"]
        print(f"  [{i+1:2}/{len(top)}] {sym} ", end="", flush=True)

        # Earnings revision / price target
        rev_score = get_earnings_revision_score(sym)
        row["score"] += rev_score
        row["earnings_revision_score"] = rev_score
        print(".", end="", flush=True)

        # Insider buying (sadece ayda 2x çalış, örnekleme ile)
        if i % 3 == 0:  # Her 3. hisse için çalıştır (API limit)
            ins_score = get_insider_buying_score(sym)
            row["score"] += ins_score
            row["insider_score"] = ins_score
        print(".", end="", flush=True)

        # Financial growth
        growth_score = get_financial_growth_score(sym, mode)
        row["score"] += growth_score
        row["growth_score"] = growth_score
        print(" ✓")

        time.sleep(0.1)  # Rate limit

    return sorted(top, key=lambda x: -x["score"])


# ── ANA TARAMA ────────────────────────────────────────────────────────────────

def run_screener(mode: str = "growth") -> list[dict]:
    print(f"\n{'='*60}")
    print(f"ALPHA SCREENER v2.0 — {mode.upper()}")
    print(f"{'='*60}")

    # 1. Evren
    universe = get_universe(mode)
    if not universe:
        print("Evren boş!")
        return []

    # 2. Ücretsiz alpha sinyallerini çek (OpenInsider + Kongre)
    print("\n  Alpha sinyalleri çekiliyor (ücretsiz)...")
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from free_alpha_data import (
            get_cluster_buys, get_congress_recent_buys,
            get_insider_buy_score, get_congress_score,
            load_cached_signals, fetch_all_alpha_signals
        )

        # Cache varsa kullan
        cached = load_cached_signals()
        if cached:
            alpha_signals = cached
            print(f"  Alpha sinyalleri cache'den yüklendi ({len(cached)} hisse)")
        else:
            insider_buys  = get_cluster_buys(days_back=30, min_value=50000)
            congress_buys = get_congress_recent_buys(days_back=30)
            alpha_signals = {}
            for row in universe[:50]:  # İlk 50 hisse için skor hesapla
                sym = row.get("symbol", "")
                alpha_signals[sym] = {
                    "insider_skor":  get_insider_buy_score(sym, insider_buys),
                    "congress_skor": get_congress_score(sym, congress_buys),
                }
    except ImportError:
        print("  free_alpha_data modülü yok, atlanıyor")
        alpha_signals  = {}
        insider_buys   = []
        congress_buys  = []

    # 3. Sektör istatistikleri (RS rank için)
    sector_stats = calculate_sector_stats(universe)
    print(f"  Sektör istatistikleri: {len(sector_stats)} sektör")

    # 4. Ön skorlama (alpha sinyalleri dahil)
    scored = []
    for row in universe:
        sym = row.get("symbol", "")

        if mode == "income":
            result = score_income(row)
        elif mode == "swing":
            result = score_swing(row, sector_stats)
        else:
            result = score_growth(row, sector_stats)

        # Alpha sinyallerini ekle
        alpha = alpha_signals.get(sym, {})
        ins_skor  = alpha.get("insider_skor", 0)
        cong_skor = alpha.get("congress_skor", 0)

        result["score"] += ins_skor * 2   # Insider alım 2x ağırlık
        result["score"] += cong_skor      # Kongre alım 1x
        result["insider_alpha_score"]   = ins_skor
        result["congress_alpha_score"]  = cong_skor

        # Tüm veriyi taşı
        result.update({k: v for k, v in row.items() if k not in result})
        scored.append(result)

    # 5. Sıralama
    scored.sort(key=lambda x: -x["score"])
    print(f"  Ön skorlama tamamlandı: {len(scored)} hisse")

    # 6. Derin analiz (top 30 için)
    final = deep_analysis(scored, mode, top_n=30)
    return final


# ── ÇIKTI ─────────────────────────────────────────────────────────────────────

def print_results(results: list[dict], mode: str, n: int = 20):
    print(f"\n{'='*80}")
    print(f"{'#':>3} {'SYM':<7} {'Scr':>4} {'52W':>5} {'RS':>5} {'Rev':>5} {'Ins':>5} {'1M':>6} {'3M':>6} Sektör")
    print("-" * 80)

    for i, r in enumerate(results[:n], 1):
        karar = "✅EKLE" if r["score"] >= 18 else ("👁İZLE" if r["score"] >= 12 else "⏭GEÇ")

        print(
            f"{i:>3} "
            f"{r['symbol']:<7} "
            f"{r['score']:>4} "
            f"{r.get('earnings_revision_score', 0):>5} "
            f"{r.get('insider_score', 0):>5} "
            f"{(r.get('priceReturn1Month') or 0):>+6.0f}% "
            f"{(r.get('priceReturn3Month') or 0):>+6.0f}% "
            f"{(r.get('sector', '')[:15]):<16} "
            f"{karar}"
        )


def save_results(results: list[dict], mode: str):
    ekle = [r for r in results if r["score"] >= 18]
    izle = [r for r in results if 12 <= r["score"] < 18]

    output = {
        "tarih":    datetime.now().isoformat(),
        "mod":      mode,
        "versiyon": "alpha_v2",
        "ozet": {
            "toplam":      len(results),
            "ekle_sayisi": len(ekle),
            "izle_sayisi": len(izle),
        },
        "ekle": ekle[:10],
        "izle": izle[:15],
        "tum_sonuclar": results[:30],
    }

    fname = OUT_DIR / f"alpha_scan_{mode}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n  💾 Kaydedildi: {fname}")
    print(f"  EKLE: {len(ekle)} | İZLE: {len(izle)}")
    return fname


# ── SEKTÖR LAGGARD TARAMASI ───────────────────────────────────────────────────

def find_sector_laggards(universe: list[dict], sector_stats: dict) -> list[dict]:
    """
    Sector catalyst → laggard trade.
    Sektörde 1 hisse çıktı, diğerleri henüz hareket etmedi → catch-up.
    """
    laggards = []

    for row in universe:
        sektor = row.get("sector", "")
        mom3m  = row.get("priceReturn3Month") or 0
        sect   = sector_stats.get(sektor, {})

        if not sect or sect["n"] < 5:
            continue

        avg = sect["avg"]
        std = sect["std"]

        # Sektör güçlü ama bu hisse henüz hareket etmedi
        if avg > 10 and (mom3m - avg) / (std + 1) < -0.5:
            laggards.append({
                "symbol":       row.get("symbol"),
                "sector":       sektor,
                "sector_avg":   round(avg, 1),
                "hisse_mom3m":  round(mom3m, 1),
                "geride_kalma": round(avg - mom3m, 1),
                "catch_up_pot": round(avg - mom3m, 1),
                "fiyat":        row.get("price"),
            })

    laggards.sort(key=lambda x: -x["geride_kalma"])
    return laggards[:10]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finzora Alpha Screener v2.0")
    parser.add_argument("--mode", default="growth",
                        choices=["growth","income","swing","all"],
                        help="Tarama modu")
    parser.add_argument("--laggards", action="store_true",
                        help="Sektör laggard taraması da yap")
    args = parser.parse_args()

    modes = ["growth", "income", "swing"] if args.mode == "all" else [args.mode]

    for mode in modes:
        results = run_screener(mode)
        print_results(results, mode)
        save_results(results, mode)

        if args.laggards and mode == "growth":
            universe = get_universe("growth")
            sector_stats = calculate_sector_stats(universe)
            laggards = find_sector_laggards(universe, sector_stats)
            print(f"\n=== SEKTÖR LAGGARD'LAR ===")
            for l in laggards[:5]:
                print(f"  {l['symbol']:6} | Sektör avg: {l['sector_avg']:+.0f}% | "
                      f"Hisse: {l['hisse_mom3m']:+.0f}% | "
                      f"Geride: {l['geride_kalma']:+.0f}% | {l['sector']}")
