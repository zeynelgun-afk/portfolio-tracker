#!/usr/bin/env python3
"""
Finzora AI — Günlük İntraday Tarama Scripti
Strateji: EMA21 filtreli, sektör pozitif, hacim patlamalı küçük/orta cap açılış oyunu
Çalıştırma zamanı: Sabah 09:00-09:25 ET (TR: 16:00-16:25)
Kullanım: python3 intraday_morning_scan.py
"""

import requests
from datetime import datetime, timedelta
import json
import sys

# ─── KONFİGÜRASYON ────────────────────────────────────────────
FMP_KEY  = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"

CAPITAL          = 5_000      # İşlem başı sermaye ($)
TARGET_PCT       = 7.5        # Hedef kâr %  (5-10 arası, ortalama)
STOP_PCT         = 3.0        # Stop-loss %
MIN_VOLUME_RATIO = 2.0        # Bugün / 10g ort hacim minimum çarpan
PRICE_MIN        = 5          # Minimum hisse fiyatı
PRICE_MAX        = 60         # Maksimum hisse fiyatı
MCAP_MIN_M       = 300        # Minimum piyasa değeri (milyon $)
MCAP_MAX_M       = 6_000      # Maksimum piyasa değeri (milyon $)
VOL_MIN          = 300_000    # Minimum günlük hacim
SECTOR_COUNT     = 4          # Kaç pozitif sektörden tarama yapılsın
# ──────────────────────────────────────────────────────────────

def fmp(ep, p=None):
    if p is None:
        p = {}
    p['apikey'] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{ep}", params=p, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠️  FMP hatası [{ep}]: {e}")
        return None

def renk(val, good_if_pos=True):
    """Terminal renklendirme"""
    if val > 0:
        return f"\033[92m{val:+.2f}%\033[0m" if good_if_pos else f"\033[91m{val:+.2f}%\033[0m"
    return f"\033[91m{val:+.2f}%\033[0m" if good_if_pos else f"\033[92m{val:+.2f}%\033[0m"

# ═══════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  FİNZORA AI — İNTRADAY SABAH TARAMASI")
print(f"  {datetime.now().strftime('%d %B %Y, %H:%M')}")
print("═"*60)

# ─── ADIM 1: PAZAR FİLTRESİ (SPY / 21 EMA) ────────────────
print("\n📊 ADIM 1 — PAZAR FİLTRESİ (SPY / 21 EMA)")
print("-"*45)

spy_quote = fmp("quote", {"symbol": "SPY"})
spy_ema21 = fmp("technical-indicators/ema", {"symbol": "SPY", "periodLength": 21, "timeframe": "1day"})

if not spy_quote or not spy_ema21:
    print("  ❌ SPY verisi alınamadı, çıkılıyor.")
    sys.exit(1)

spy_price = spy_quote[0]['price']
spy_prev  = spy_quote[0].get('previousClose', spy_price)
spy_chg   = (spy_price - spy_prev) / spy_prev * 100
ema21_val = spy_ema21[0]['ema']
spy_above = spy_price > ema21_val
gap_from_ema = (spy_price - ema21_val) / ema21_val * 100

print(f"  SPY       : ${spy_price:.2f} ({renk(spy_chg)})")
print(f"  EMA21     : ${ema21_val:.2f}")
print(f"  Fark      : {gap_from_ema:+.2f}%")

if spy_above:
    print("  ✅ FİLTRE GEÇTİ — SPY EMA21 üzerinde")
    market_ok = True
else:
    print("  ❌ FİLTRE BAŞARISIZ — SPY EMA21 altında → İntraday tarama durduruldu")
    market_ok = False

if not market_ok:
    print("\n  Pazar filtresi geçilemedi. Bugün bu strateji uygulanmaz.")
    sys.exit(0)

# ─── ADIM 2: SEKTÖR ANALİZİ ───────────────────────────────
print(f"\n📊 ADIM 2 — SEKTÖR PERFORMANSI")
print("-"*45)

today = datetime.now().strftime("%Y-%m-%d")
sectors_data = fmp("sector-performance-snapshot", {"date": today})

if not sectors_data:
    print("  ⚠️  Sektör verisi alınamadı")
    sys.exit(1)

sorted_sectors = sorted(sectors_data, key=lambda x: x.get('averageChange', 0), reverse=True)
positive_sectors = [s for s in sorted_sectors if s.get('averageChange', 0) > 0]
top_sectors = [s['sector'] for s in positive_sectors[:SECTOR_COUNT]]

for s in sorted_sectors:
    chg = s.get('averageChange', 0)
    marker = "🎯" if s['sector'] in top_sectors else ("✅" if chg > 0 else "❌")
    print(f"  {marker} {s['sector']:28} {renk(chg)}")

print(f"\n  Hedef sektörler ({SECTOR_COUNT} en güçlü pozitif): {', '.join(top_sectors)}")

if not top_sectors:
    print("  ❌ Pozitif sektör yok. Tarama durduruldu.")
    sys.exit(0)

# ─── ADIM 3: HİSSE TARAMASI ───────────────────────────────
print(f"\n📊 ADIM 3 — HİSSE TARAMASI ({PRICE_MIN}-${PRICE_MAX}, ${MCAP_MIN_M}M-${MCAP_MAX_M}M mcap)")
print("-"*45)

all_candidates = []
for sector in top_sectors:
    results = fmp("company-screener", {
        "sector": sector,
        "marketCapMoreThan": MCAP_MIN_M * 1_000_000,
        "marketCapLowerThan": MCAP_MAX_M * 1_000_000,
        "priceMoreThan": PRICE_MIN,
        "priceLowerThan": PRICE_MAX,
        "volumeMoreThan": VOL_MIN,
        "exchange": "NYSE,NASDAQ",
        "isActivelyTrading": "true",
        "limit": 60
    })
    if results and isinstance(results, list):
        for s in results:
            s['_sector'] = sector
        all_candidates.extend(results)

print(f"  {len(all_candidates)} hisse bulundu, hacim analizi yapılıyor...")

# ─── ADIM 4: HACİM PATLAMASI FİLTRESİ ────────────────────
print(f"\n📊 ADIM 4 — HACİM PATLAMASI FİLTRESİ (min {MIN_VOLUME_RATIO}x)")
print("-"*45)

qualified = []
for c in all_candidates:
    sym       = c['symbol']
    today_vol = c.get('volume', 0)
    price     = c.get('price', 0)
    mcap      = c.get('marketCap', 0)

    if not today_vol or today_vol < VOL_MIN:
        continue

    hist = fmp("historical-price-eod/full", {"symbol": sym, "limit": 12})
    if not hist or not isinstance(hist, list) or len(hist) < 5:
        continue

    # İlk kayıt bugün (seans açık ise), aksi halde dünkü
    base_idx  = 1  # bugünü atla
    past_vols = [d.get('volume', 0) for d in hist[base_idx:base_idx+10] if d.get('volume', 0) > 0]
    if not past_vols:
        continue

    avg_vol   = sum(past_vols) / len(past_vols)
    vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0

    prev_close = hist[base_idx].get('close', 0)
    chg_pct    = ((price - prev_close) / prev_close * 100) if prev_close else 0

    # RSI filtresi
    rsi_data = fmp("technical-indicators/rsi", {"symbol": sym, "periodLength": 14, "timeframe": "1day"})
    rsi_val  = rsi_data[0]['rsi'] if rsi_data and isinstance(rsi_data, list) else 0

    # EMA21 filtresi
    ema_data  = fmp("technical-indicators/ema", {"symbol": sym, "periodLength": 21, "timeframe": "1day"})
    ema21_sym = ema_data[0]['ema'] if ema_data and isinstance(ema_data, list) else 0
    above_ema21 = price > ema21_sym

    # KRİTERLER:
    # 1. Hacim 2x+ artış
    # 2. Bugün pozitif kapanış
    # 3. EMA21 üzerinde
    # 4. RSI 80 altı (aşırı alım değil)
    if vol_ratio >= MIN_VOLUME_RATIO and chg_pct > 0 and above_ema21 and rsi_val < 80:
        qualified.append({
            "symbol"   : sym,
            "price"    : price,
            "chg"      : chg_pct,
            "vol"      : today_vol,
            "avg_vol"  : avg_vol,
            "ratio"    : vol_ratio,
            "rsi"      : rsi_val,
            "ema21"    : ema21_sym,
            "sector"   : c['_sector'],
            "mcap_m"   : mcap / 1e6,
        })

qualified.sort(key=lambda x: x['ratio'], reverse=True)

# ─── ADIM 5: SONUÇLAR VE SENARYO ─────────────────────────
print(f"\n🎯 SONUÇ: {len(qualified)} KALİFİYE ADAY\n")

if not qualified:
    print("  Bugün kriterleri karşılayan hisse bulunamadı.")
    sys.exit(0)

print(f"{'#':>2} {'Sembol':7} {'Fiyat':>7} {'Değişim':>8} {'Vol Oran':>8} {'RSI':>5} {'EMA21':>7} {'MCap':>8} | Sektör")
print("-"*85)

for i, s in enumerate(qualified[:10], 1):
    chg_str = renk(s['chg'])
    print(f"{i:>2} {s['symbol']:7} ${s['price']:>6.2f} {chg_str:>16} {s['ratio']:>7.1f}x {s['rsi']:>5.1f} ${s['ema21']:>6.2f} ${s['mcap_m']:>6.0f}M | {s['sector']}")

# ─── ADIM 6: EN İYİ ADAY İÇİN SENARYO ───────────────────
if qualified:
    best = qualified[0]
    sym    = best['symbol']
    price  = best['price']
    shares = int(CAPITAL / price)
    cost   = shares * price

    print(f"\n{'═'*60}")
    print(f"  1. ADAY: {sym}  —  ${price:.2f}")
    print(f"{'═'*60}")
    print(f"  Sektör    : {best['sector']}")
    print(f"  RSI(14)   : {best['rsi']:.1f}")
    print(f"  EMA21     : ${best['ema21']:.2f} ({'✅ üstü' if price > best['ema21'] else '❌ altı'})")
    print(f"  Vol Oran  : {best['ratio']:.1f}x ({best['vol']:,.0f} vs {best['avg_vol']:,.0f} ort)")
    print(f"\n  💰 POZİSYON: {shares} hisse × ${price:.2f} = ${cost:,.2f}")
    print(f"\n  {'Senaryo':15} {'Hedef':>8} {'Kâr $':>8} {'Stop':>8} {'Zarar $':>8} {'R:R':>6}")
    print(f"  {'-'*60}")
    for t, s_pct in [(5, -2.5), (7.5, -3), (10, -4)]:
        t_price = price * (1 + t/100)
        s_price = price * (1 - s_pct/100)
        profit  = shares * (t_price - price)
        loss    = shares * (s_price - price)
        rr      = profit / abs(loss)
        print(f"  Hedef %{t:>2}      ${t_price:>7.2f} ${profit:>7.0f}  ${s_price:>7.2f} ${loss:>7.0f} {rr:>5.1f}:1")

    print(f"\n  ⚠️  GİRİŞ KURALI: İlk 5-10 dk. bekle, yönü teyitle, sonra al.")
    print(f"  ⚠️  ÇIKIŞ KURALI: %5+ kâra ulaşırsa partial sat, %7.5'te tam çık.")
    print(f"  ⚠️  STOP KURALI : ${price * 0.97:.2f} altında beklemeden sat.")

print("\n" + "═"*60 + "\n")
