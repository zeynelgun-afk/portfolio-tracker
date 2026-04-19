#!/usr/bin/env python3
"""
Swing Tam Evren Taraması — İki Aşamalı

Amaç: FMP company-screener ile ~1,100+ hisseden oluşan tam evreni tarayıp
A-kalite swing setup'larını bulmak. K-14 kalktıktan sonra sabah rutinin ana taraması.

Aşama 1: Momentum Pre-filter (1-2 FMP çağrısı, ~1,100 hisse)
  - Market cap > $2B, fiyat > $10, vol > 500K
  - 1M getiri > 0, 3M getiri > %5 (trend yukarı)
  - Sonuç: ~100-200 aday

Aşama 2: RSI + Ichimoku Derin Analiz (her survivor için 3-4 FMP çağrısı)
  - RSI 40-65 (oversold veya güçlü trend)
  - Swing_ichimoku.py full_analysis (4/4 bullish + hacim + SMA200)
  - K-19 XLP filtre (swing giriş yasak)
  - Sonuç: 5-15 A-kalite aday

Kullanım:
  python scripts/swing_full_universe.py                   # tam çalışma
  python scripts/swing_full_universe.py --max-candidates 50
  python scripts/swing_full_universe.py --skip-stage2     # sadece aşama 1
  python scripts/swing_full_universe.py --json            # JSON çıktı

NOT: Aşama 2'de her survivor için ~3 FMP çağrısı yapılır. 100 survivor = 300 çağrı.
Tam evren taraması uzun sürer (2-5 dakika). Hedef: K-14 kalktıktan sonra günlük 1 defa.
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_scan_common as psc

REPO_ROOT = Path(__file__).resolve().parent.parent
FMP_KEY = psc.FMP_API_KEY
FMP_BASE = psc.FMP_BASE

# Filtreler
STAGE1_MIN_MCAP = 2_000_000_000  # $2B
STAGE1_MIN_PRICE = 10
STAGE1_MIN_VOL = 500_000
STAGE1_MIN_1M = 0     # 1M getiri pozitif olmalı
STAGE1_MIN_3M = 5     # 3M getiri > %5
STAGE2_RSI_MIN = 40
STAGE2_RSI_MAX = 65
XLP_YASAK = {"XLP", "ConsumerDef"}  # K-19


# ============================================================
# AŞAMA 1: Momentum Pre-filter
# ============================================================

def stage1_momentum_prefilter(max_candidates=None):
    """
    FMP company-screener ile geniş momentum evreni çek.
    Temel filtre: mcap, price, volume.
    Sonra stock-price-change endpoint'iyle momentum teyidi.
    """
    print(f"\n{'='*65}")
    print(f"  AŞAMA 1: MOMENTUM PRE-FILTER")
    print(f"{'='*65}")
    print(f"  Filtreler: mcap>${STAGE1_MIN_MCAP/1e9:.0f}B, price>${STAGE1_MIN_PRICE}, "
          f"vol>{STAGE1_MIN_VOL//1000}K, 1M>{STAGE1_MIN_1M}%, 3M>{STAGE1_MIN_3M}%")
    
    # Screener ile tüm evren
    params = {
        "marketCapMoreThan": STAGE1_MIN_MCAP,
        "priceMoreThan": STAGE1_MIN_PRICE,
        "volumeMoreThan": STAGE1_MIN_VOL,
        "exchange": "NYSE,NASDAQ",
        "isActivelyTrading": "true",
        "limit": 2000,
    }
    
    print(f"\n  → FMP company-screener çağrısı...")
    screener = psc.fmp_get("company-screener", params)
    if not screener or not isinstance(screener, list):
        print(f"  [HATA] company-screener boş döndü")
        return []
    
    print(f"  → {len(screener)} hisse evrende")
    
    # K-19 XLP filtreleme (ön eleme)
    filtered = []
    for item in screener:
        sym = item.get("symbol", "")
        sector = item.get("sector", "")
        if sector == "Consumer Defensive" or sector == "Consumer Staples":
            continue  # K-19: XLP swing yasak
        filtered.append(item)
    
    print(f"  → K-19 sonrası: {len(filtered)} (XLP hariç)")
    
    # Momentum teyidi — batch-quote ile 1M/3M getiri
    # FMP batch-quote tek çağrıda 500+ sembol alır
    symbols = [x.get("symbol", "") for x in filtered if x.get("symbol")]
    if not symbols:
        return []
    
    # Batch quote büyük çağrı — 500'lük bloklar
    print(f"  → Momentum verisi çekiliyor (batch)...")
    all_quotes = {}
    for i in range(0, len(symbols), 500):
        batch = symbols[i:i+500]
        q = psc.fmp_get("batch-quote", {"symbols": ",".join(batch)})
        if q and isinstance(q, list):
            for item in q:
                all_quotes[item.get("symbol", "")] = item
        time.sleep(0.1)
    
    # stock-price-change ile 1M/3M (tek tek; FMP bunu batch desteklemez)
    # Bu çok API çağrısı demek. Alternatif: değişim%'yi batch-quote'tan al
    # batch-quote dönüşü: price, previousClose, changePercentage (günlük), price
    # 1M/3M için ayrı çağrı gerekir — maliyetli, o yüzden YAKLAŞIK filtre kullanıyoruz:
    # Günlük değişim pozitif + price > SMA50 yaklaşımıyla
    
    # Ancak ideal: historical-price ile 1M/3M hesaplaması. Bu pahalı.
    # Pragmatik çözüm: stock-price-change endpoint (tek tek), ama sadece filtered listedeki semboller için
    # ve batch-quote'ın changePercentage'i pozitif olanları ön eleyelim.
    
    pre_filtered = []
    for s in symbols:
        q = all_quotes.get(s, {})
        price = q.get("price", 0) or 0
        prev = q.get("previousClose", 0) or 0
        if not price or not prev:
            continue
        # günlük pozitif ve fiyat > önceki kapanış (momentum işareti)
        if price > prev:
            pre_filtered.append(s)
    
    print(f"  → Günlük momentum pozitif: {len(pre_filtered)}")
    
    # Aşama 1 son: stock-price-change ile gerçek 1M/3M teyidi
    # Performans için max_candidates varsa kes
    limit = max_candidates if max_candidates else 300
    pre_filtered = pre_filtered[:limit]
    
    survivors = []
    print(f"  → 1M/3M momentum teyidi ({len(pre_filtered)} hisse, bu uzun sürebilir)...")
    for i, s in enumerate(pre_filtered):
        if i > 0 and i % 25 == 0:
            print(f"     ... {i}/{len(pre_filtered)}")
        pc = psc.fmp_get("stock-price-change", {"symbol": s})
        if not pc or not isinstance(pc, list) or not pc:
            continue
        p = pc[0]
        m1m = p.get("1M", 0) or 0
        m3m = p.get("3M", 0) or 0
        if m1m >= STAGE1_MIN_1M and m3m >= STAGE1_MIN_3M:
            survivors.append({
                "symbol": s,
                "m1m": m1m,
                "m3m": m3m,
                "m6m": p.get("6M", 0) or 0,
                "price": all_quotes.get(s, {}).get("price", 0),
            })
        time.sleep(0.02)
    
    print(f"\n  ✅ Aşama 1 survivor: {len(survivors)} hisse")
    return sorted(survivors, key=lambda x: -x["m3m"])


# ============================================================
# AŞAMA 2: RSI + Ichimoku Derin Analiz
# ============================================================

def stage2_deep_analysis(survivors, max_analyze=100):
    """
    Her survivor için RSI + Ichimoku full analiz.
    swing_ichimoku.py'nin full_analysis fonksiyonunu kullan.
    """
    print(f"\n{'='*65}")
    print(f"  AŞAMA 2: RSI + ICHIMOKU DERİN ANALİZ")
    print(f"{'='*65}")
    print(f"  Filtreler: RSI {STAGE2_RSI_MIN}-{STAGE2_RSI_MAX}, ichimoku 4/4, SMA200 üstü")
    
    if not survivors:
        print("  (survivor yok)")
        return []
    
    # swing_ichimoku importu
    try:
        from swing_ichimoku import full_analysis as sw_full
    except Exception as e:
        print(f"  [HATA] swing_ichimoku import: {e}")
        return []
    
    analyze = survivors[:max_analyze]
    print(f"\n  → {len(analyze)} hisse derin analiz ediliyor...")
    
    kaliteli = []
    for i, s in enumerate(analyze):
        sym = s["symbol"]
        if i > 0 and i % 10 == 0:
            print(f"     ... {i}/{len(analyze)}")
        
        try:
            r = sw_full(sym, detay=False)
        except Exception as e:
            print(f"     {sym}: analiz hatası {e}")
            continue
        
        if not r:
            continue
        
        # RSI filter
        rsi = r.get("ichimoku", {}).get("rsi", 0) or 0
        if not (STAGE2_RSI_MIN <= rsi <= STAGE2_RSI_MAX):
            continue
        
        # SMA200 üstü şart
        s200 = r.get("sma200", {}).get("above", False)
        if not s200:
            continue
        
        # Ichimoku 4/4 bullish şart
        pos = r.get("position", {})
        if pos.get("skor", 0) < 4:
            continue
        
        kaliteli.append({
            **s,
            "rsi": rsi,
            "position": pos,
            "stop": r.get("stop", {}).get("stop", 0),
            "volume_confirm": r.get("volume", {}).get("teyit") if r.get("volume") else "?",
            "signals": len(r.get("entry_signals", [])),
            "karar": r.get("karar", ""),
        })
        time.sleep(0.05)
    
    print(f"\n  ✅ Aşama 2 A-kalite: {len(kaliteli)} hisse")
    return kaliteli


# ============================================================
# RAPOR
# ============================================================

def print_report(stage2_results):
    if not stage2_results:
        print("\n  (A-kalite aday bulunamadı)")
        return
    
    print(f"\n{'='*75}")
    print(f"  A-KALİTE SWING ADAYLARI")
    print(f"{'='*75}")
    print(f"  {'sembol':7s} | {'fiyat':>8s} | {'RSI':>4s} | {'1M':>6s} | {'3M':>6s} | "
          f"{'6M':>6s} | {'trend':8s} | karar")
    print(f"  {'─'*7} | {'─'*8} | {'─'*4} | {'─'*6} | {'─'*6} | {'─'*6} | {'─'*8} | ─────")
    for r in sorted(stage2_results, key=lambda x: -x["m3m"]):
        pos = r.get("position", {})
        print(f"  {r['symbol']:7s} | ${r.get('price', 0):>7.2f} | "
              f"{r.get('rsi', 0):>4.0f} | {r.get('m1m', 0):>+5.1f}% | "
              f"{r.get('m3m', 0):>+5.1f}% | {r.get('m6m', 0):>+5.1f}% | "
              f"{pos.get('trend', '?'):8s} | {r.get('karar', '?')}")
    print(f"{'='*75}")


def save_results(stage1, stage2):
    """Sonuçları data/daily_full_scan.json'a yaz."""
    out = {
        "son_guncelleme": datetime.now().isoformat(),
        "stage1_survivors": len(stage1),
        "stage2_a_kalite": len(stage2),
        "stage2_adaylar": stage2,
    }
    out_path = REPO_ROOT / "data" / "daily_full_scan.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  💾 Sonuçlar kaydedildi: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Swing Full Universe Scanner (iki aşamalı)")
    parser.add_argument("--max-candidates", type=int, default=200,
                        help="Aşama 1'den kaç hisseyi aşama 2'ye geçireceksin (default 200)")
    parser.add_argument("--skip-stage2", action="store_true", help="Sadece aşama 1 çalıştır")
    parser.add_argument("--json", action="store_true", help="JSON çıktı (stdout'a)")
    parser.add_argument("--no-save", action="store_true", help="Dosyaya kaydetme")
    args = parser.parse_args()
    
    start = time.time()
    
    # Aşama 1
    stage1 = stage1_momentum_prefilter(max_candidates=args.max_candidates)
    
    if args.skip_stage2:
        print(f"\n[--skip-stage2] Aşama 1 sonuçları:")
        for r in stage1[:20]:
            print(f"  {r['symbol']}: 1M {r['m1m']:+.1f}%, 3M {r['m3m']:+.1f}%, 6M {r['m6m']:+.1f}%")
        if len(stage1) > 20:
            print(f"  ... ve {len(stage1)-20} daha")
        if not args.no_save:
            save_results(stage1, [])
        print(f"\n  ⏱  Süre: {time.time()-start:.1f}s")
        return
    
    # Aşama 2
    stage2 = stage2_deep_analysis(stage1, max_analyze=args.max_candidates)
    
    # Rapor
    if args.json:
        print(json.dumps({"stage1": stage1, "stage2": stage2}, indent=2, default=str))
    else:
        print_report(stage2)
    
    if not args.no_save:
        save_results(stage1, stage2)
    
    print(f"\n  ⏱  Toplam süre: {time.time()-start:.1f}s")


if __name__ == "__main__":
    main()
