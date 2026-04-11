#!/usr/bin/env python3
"""
Finzora — Ücretsiz Alpha Veri Kaynakları
=========================================
Ücret ödemeden çekebileceğimiz kaliteli sinyaller:

1. OpenInsider       → SEC Form 4 alımları (gerçek zamanlı, ücretsiz)
2. SEC EDGAR         → Resmi Form 4 CIK bazlı (data.sec.gov, ücretsiz)
3. Yahoo Finance     → Short interest, put/call ratio (yfinance, ücretsiz)
4. FINRA Short Data  → 2 haftada bir, exchange bazlı (ücretsiz)
5. Congress Trades   → Senatör/Temsilci stock trades (ücretsiz)
6. Stocksera/FINVIZ  → Bazı ücretsiz filtreler

Kaynaklar ve güvenilirlik:
  OpenInsider: Yüksek (SEC'den)
  EDGAR Form 4: En yüksek (resmi)
  yfinance shortRatio: Orta (biraz gecikmeli)
  Congress trades: Yüksek (düzenleme zorunluluğu)
"""

import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

MEMORY_DIR = Path(__file__).parent.parent / "data"
EDGAR_HEADERS = {"User-Agent": "Finzora zeynelgun@gmail.com"}
OPENINSIDER_BASE = "http://openinsider.com"


# ── 1. OPENİNSİDER — CEO/CFO ALIMLARI ────────────────────────────────────────

def get_cluster_buys(days_back: int = 30, min_value: int = 50000) -> list[dict]:
    """
    OpenInsider'dan son N günün insider ALIMLARINI çeker.
    Cluster buy = aynı hissede birden fazla insider → güçlü sinyal.
    
    Araştırma: CEO/CFO açık piyasa alımı = +22.4% yıllık alpha.
    """
    from datetime import datetime, timedelta
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    try:
        r = requests.get(
            f"{OPENINSIDER_BASE}/screener",
            params={
                "tt":  "P",          # Purchase (alım)
                "num": "100",        # Max 100 sonuç
                "order": "fd",       # Filing date'e göre sırala
                "sd":  start,        # Başlangıç tarihi
                "lmi": str(min_value // 1000),  # Min işlem ($K)
            },
            timeout=15
        )

        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})

        if not table:
            return []

        results = []
        rows    = table.find_all('tr')[1:]

        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all('td')]
            if len(cols) < 10:
                continue

            # Değeri parse et
            val_str = cols[9].replace(',', '').replace('+', '').replace('$', '')
            try:
                val = float(val_str) * 1000  # K'dan dollar'a
            except (ValueError, IndexError):
                val = 0

            if val < min_value:
                continue

            results.append({
                "tarih":   cols[1][:10] if len(cols) > 1 else "",
                "sembol":  cols[3] if len(cols) > 3 else "",
                "isim":    cols[4] if len(cols) > 4 else "",
                "unvan":   cols[5] if len(cols) > 5 else "",
                "tip":     cols[6] if len(cols) > 6 else "",
                "fiyat":   cols[7] if len(cols) > 7 else "",
                "adet":    cols[8] if len(cols) > 8 else "",
                "deger":   val,
                "kaynak":  "openinsider",
            })

        # Cluster buy tespiti (aynı hissede 2+ insider)
        from collections import Counter
        sembol_sayisi = Counter(r["sembol"] for r in results)
        for r2 in results:
            r2["cluster_buy"] = sembol_sayisi[r2["sembol"]] >= 2
            r2["cxo_alim"]    = any(t in r2["unvan"].lower()
                                    for t in ["ceo","cfo","president","coo","founder"])

        print(f"[AlphaVeri] OpenInsider: {len(results)} alım, "
              f"{sum(1 for r2 in results if r2['cluster_buy'])} cluster")
        return results

    except Exception as e:
        print(f"[AlphaVeri] OpenInsider hatası: {e}")
        return []


def get_insider_buy_score(symbol: str, buys: list[dict]) -> int:
    """
    Bir hisse için insider alım skoru.
    Buys listesi get_cluster_buys'dan gelir (API call'u tekrar etmez).
    """
    sym_buys = [b for b in buys if b.get("sembol") == symbol]

    if not sym_buys:
        return 0

    cluster   = any(b.get("cluster_buy") for b in sym_buys)
    cxo       = any(b.get("cxo_alim") for b in sym_buys)
    max_val   = max(b.get("deger", 0) for b in sym_buys)

    if cluster and cxo:    return 5   # Cluster + CEO/CFO → en güçlü
    elif cluster:          return 4   # Birden fazla insider
    elif cxo:              return 3   # CEO/CFO tek alım
    elif len(sym_buys) >= 1 and max_val > 500000:  return 2  # Büyük alım
    elif sym_buys:         return 1
    return 0


# ── 2. YAHOO FİNANS — SHORT İNTEREST ─────────────────────────────────────────

def get_short_interest_batch(symbols: list[str]) -> dict[str, dict]:
    """
    Yahoo Finance üzerinden short interest verileri.
    yfinance ile ücretsiz: shortPercentOfFloat, shortRatio.
    
    Yorum:
    - shortPercentOfFloat > %20 + azalıyorsa → squeeze potansiyeli
    - shortRatio (days-to-cover) > 10 → yüksek squeeze riski
    """
    try:
        import yfinance as yf
    except ImportError:
        print("[AlphaVeri] yfinance kurulu değil. pip install yfinance")
        return {}

    results = {}
    batch_size = 10

    for i in range(0, min(len(symbols), 50), batch_size):
        batch = symbols[i:i+batch_size]
        try:
            tickers = yf.Tickers(" ".join(batch))
            for sym in batch:
                try:
                    info  = tickers.tickers[sym].info
                    float_short = info.get("shortPercentOfFloat") or 0
                    short_ratio = info.get("shortRatio") or 0

                    results[sym] = {
                        "short_float_pct":  round(float_short * 100, 1) if float_short < 1 else float_short,
                        "short_ratio":       short_ratio,
                        "squeeze_score":     _calc_squeeze_score(float_short, short_ratio),
                    }
                except Exception:
                    results[sym] = {"short_float_pct": 0, "short_ratio": 0, "squeeze_score": 0}
            time.sleep(0.5)
        except Exception as e:
            print(f"[AlphaVeri] yfinance batch hatası: {e}")

    return results


def _calc_squeeze_score(float_short: float, short_ratio: float) -> int:
    """Short squeeze potansiyel skoru."""
    # float_short < 1 ise oran formatında gelmiş → yüzdeye çevir
    if float_short and float_short < 1:
        float_short *= 100

    s = 0
    if float_short > 30:    s += 3  # %30+ kısa pozisyon
    elif float_short > 20:  s += 2
    elif float_short > 10:  s += 1

    if short_ratio > 15:    s += 2  # 15+ gün kapanış süresi
    elif short_ratio > 8:   s += 1

    return s


# ── 3. CONGRESS TRADES ────────────────────────────────────────────────────────

def get_congress_recent_buys(days_back: int = 30) -> list[dict]:
    """
    Kongre üyelerinin son alımları (senatestockwatcher.com ücretsiz API).
    Kongre üyelerinin içeriden bilgi avantajı olduğu bilinir.
    
    Araştırma: Kongre hisse alımları SPY'ı %11-17 outperform eder (Harvard 2023).
    """
    try:
        # Senate Stock Watcher - ücretsiz JSON
        r = requests.get(
            "https://senate-stock-watcher-data.s3-us-gov-west-1.amazonaws.com/aggregate/all_transactions.json",
            timeout=15
        )
        if r.status_code != 200:
            # Alternatif kaynak
            return _get_house_trades(days_back)

        all_trades = r.json()
        cutoff     = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        buys = []
        for trade in all_trades:
            td = trade.get("transaction_date", "")
            if td < cutoff:
                continue
            tt = trade.get("type", "").lower()
            if "purchase" not in tt:
                continue

            ticker = trade.get("ticker", "").strip()
            if not ticker or ticker in ("--", "N/A"):
                continue

            buys.append({
                "tarih":   td,
                "sembol":  ticker,
                "senator": trade.get("senator", ""),
                "tutar":   trade.get("amount", ""),
                "kaynak":  "senate_stock_watcher",
            })

        print(f"[AlphaVeri] Kongre alımları: {len(buys)} işlem")
        return buys[:50]

    except Exception as e:
        print(f"[AlphaVeri] Kongre verisi hatası: {e}")
        return []


def _get_house_trades(days_back: int) -> list[dict]:
    """Temsilciler Meclisi ticaret verisi (yedek kaynak)."""
    try:
        r = requests.get(
            "https://house-stock-watcher-data.s3-us-gov-west-1.amazonaws.com/data/all_transactions.json",
            timeout=15
        )
        if r.status_code != 200:
            return []

        all_trades = r.json()
        cutoff     = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        buys = []
        for trade in all_trades:
            td = trade.get("transaction_date", "")
            if td < cutoff:
                continue
            tt = trade.get("type", "").lower()
            if "purchase" not in tt:
                continue

            ticker = trade.get("ticker", "").strip()
            if not ticker or ticker in ("--", "N/A", ""):
                continue

            buys.append({
                "tarih":  td,
                "sembol": ticker,
                "isim":   trade.get("representative", ""),
                "tutar":  trade.get("amount", ""),
                "kaynak": "house_stock_watcher",
            })

        print(f"[AlphaVeri] Meclis alımları: {len(buys)} işlem")
        return buys[:50]

    except Exception as e:
        print(f"[AlphaVeri] Meclis verisi hatası: {e}")
        return []


def get_congress_score(symbol: str, congress_buys: list[dict]) -> int:
    """Bir hisse için kongre alım skoru."""
    sym_buys = [b for b in congress_buys if b.get("sembol") == symbol]

    if not sym_buys:
        return 0

    if len(sym_buys) >= 3:   return 3   # 3+ kongre üyesi aldı
    elif len(sym_buys) >= 2: return 2
    elif sym_buys:           return 1
    return 0


# ── 4. FINRA SHORT VOLUME (Günlük) ───────────────────────────────────────────

def get_finra_short_volume(symbol: str) -> dict:
    """
    FINRA'nın ücretsiz short volume verisi.
    Günlük short volume / total volume oranı.
    Azalan trend + katalizör = squeeze setup.
    """
    try:
        # FINRA OTCE short interest sayfası
        r = requests.get(
            "https://api.finra.org/data/group/OTCMarket/name/EQShortsales",
            params={"limit": 1, "offset": 0,
                    "fields": "issueName,securityId,shortParQuantity,totalParQuantity"},
            headers={"Accept": "application/json"},
            timeout=10
        )
        # FINRA API genellikle OTC için çalışır, exchange listeds için
        # doğrudan short interest dosyaları daha iyi
        if r.status_code == 200:
            return r.json()
        return {}
    except Exception:
        return {}


# ── 5. ANA ALPHA VERİ TOPLAMA ─────────────────────────────────────────────────

def fetch_all_alpha_signals(symbols: list[str], days_back: int = 30) -> dict:
    """
    Tüm ücretsiz alpha sinyallerini topla.
    Alpha screener'a entegre edilir.
    """
    print(f"[AlphaVeri] {len(symbols)} sembol için alpha sinyalleri çekiliyor...")

    # 1. Insider alımları (tek çağrı, tüm semboller için)
    insider_buys = get_cluster_buys(days_back=days_back, min_value=50000)

    # 2. Kongre alımları (tek çağrı)
    congress_buys = get_congress_recent_buys(days_back=days_back)

    # 3. Short interest (batch)
    short_data = get_short_interest_batch(symbols[:30])  # İlk 30 ile sınırla

    # Sembol bazında skorları birleştir
    combined = {}
    for sym in symbols:
        combined[sym] = {
            "insider_skor":   get_insider_buy_score(sym, insider_buys),
            "congress_skor":  get_congress_score(sym, congress_buys),
            "short_squeeze":  short_data.get(sym, {}).get("squeeze_score", 0),
            "short_float":    short_data.get(sym, {}).get("short_float_pct", 0),
        }
        # Cluster buy ekstra bonus
        sym_buys = [b for b in insider_buys if b.get("sembol") == sym]
        if any(b.get("cluster_buy") for b in sym_buys):
            combined[sym]["cluster_buy"] = True

    # Cache'e kaydet
    cache_path = MEMORY_DIR / "alpha_signals_cache.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({
            "tarih":         datetime.now().isoformat(),
            "insider_buys":  insider_buys,
            "congress_buys": congress_buys,
            "signals":       combined,
        }, f, ensure_ascii=False, indent=2, default=str)

    print(f"[AlphaVeri] Tamamlandı: {len(insider_buys)} insider alım, "
          f"{len(congress_buys)} kongre alım")
    return combined


def load_cached_signals() -> dict:
    """Cache'den alpha sinyallerini yükle (aynı günse yeniden çekme)."""
    cache_path = MEMORY_DIR / "alpha_signals_cache.json"
    if not cache_path.exists():
        return {}

    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)

    # 4 saatten eskiyse geçersiz
    tarih  = cache.get("tarih", "")
    if tarih:
        cache_dt = datetime.fromisoformat(tarih)
        if (datetime.now() - cache_dt).total_seconds() > 4 * 3600:
            return {}

    return cache.get("signals", {})


def get_alpha_summary_for_screener(symbol: str, signals: dict) -> dict:
    """Alpha screener'a verilecek özet skor."""
    sig = signals.get(symbol, {})
    return {
        "insider_skor":  sig.get("insider_skor", 0),
        "congress_skor": sig.get("congress_skor", 0),
        "squeeze_skor":  sig.get("short_squeeze", 0),
        "cluster_buy":   sig.get("cluster_buy", False),
        "toplam_alpha":  (
            sig.get("insider_skor", 0) * 2 +     # Insider en önemli
            sig.get("congress_skor", 0) * 1.5 +  # Kongre ikinci
            sig.get("short_squeeze", 0) * 1      # Squeeze ek sinyal
        ),
    }


# ── TEST ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Ücretsiz Alpha Veri Test ===\n")

    # OpenInsider test
    buys = get_cluster_buys(days_back=14, min_value=100000)
    print(f"\nSon 14 günde $100K+ insider alımı: {len(buys)} adet")
    cluster = [b for b in buys if b.get("cluster_buy")]
    print(f"Cluster alımlar: {len(cluster)}")
    for b in cluster[:3]:
        print(f"  {b['sembol']:6} {b['unvan']:25} ${b['deger']:,.0f}")

    # Kongre test
    print("\nKongre alımları test ediliyor...")
    congress = get_congress_recent_buys(days_back=30)
    print(f"Son 30 günde kongre alımları: {len(congress)}")

    from collections import Counter
    top_stocks = Counter(b["sembol"] for b in congress).most_common(5)
    print("En çok alınan:", top_stocks)
