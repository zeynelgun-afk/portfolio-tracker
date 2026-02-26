# PORTFÖY YÖNETİM KURALLARI

> **son güncelleme**: 26 şubat 2026

---

## yapı

3 aktif portföy, toplam $600K simülasyon sermayesi.

| portföy | sermaye | ağırlık |
|---------|---------|---------|
| dengeli | $100K | %17 |
| agresif momentum | $400K | %66 |
| değer + temettü | $100K | %17 |

> rotasyon portföyü ($100K) 26 şubat 2026'da kapatıldı → arşiv: `data/archive/`

---

## 1. dengeli portföy ($100K)

**ruh**: dengeli, risk/ödül balanced, çeşitlendirilmiş, multi-sector value + momentum

| kural | değer |
|-------|-------|
| izin verilen | hisseler + sektör ETF |
| hedge | short ETF izin verilir (SQQQ, SH, SPXU) |
| max pozisyon | 7 |
| stop-loss | %8 |
| hedef getiri | yıllık %15-20 |

---

## 2. agresif momentum ($400K) ⭐ ANA PORTFÖY

**ruh**: yüksek frekanslı momentum trading, aylık %5 net getiri hedefi

| kural | değer |
|-------|-------|
| izin verilen | büyüme hisseleri (ETF yok) |
| sinyal tipleri | earnings momentum, breakout, mean reversion |
| max pozisyon | 8 |
| pozisyon büyüklüğü | $40K-$60K (%10-15) |
| tutma süresi | 3-7 gün (max 10) |
| stop-loss | %4 (sıkı) |
| kar hedefi | %8-12 (kademeli çıkış) |
| R:R minimum | 2:1 |
| aylık max drawdown | %8 |
| günlük max kayıp | %2 |
| hedef getiri | aylık %5 (yıllık ~%80) |

**kademeli çıkış**: +%4'te breakeven stop → +%6'da %33 sat → +%10'da %33 sat → kalan trailing

**yasak**: değer hisseleri, temettü aristokratları, defensive sektörler

detay: `docs/AGGRESSIVE_MOMENTUM_STRATEGY.md`

---

## 3. değer + temettü ($100K)

**ruh**: değer hisseleri, yüksek temettü, istikrar, güçlü FCF

| kural | değer |
|-------|-------|
| izin verilen | değer/temettü hisseleri + temettü ETF'leri (SCHD, VYM, DVY) |
| giriş kriterleri | P/E < 20, temettü yield > %3, D/E < 1.5, FCF pozitif |
| hedge | short ETF izin verilir |
| max pozisyon | 15 |
| hedef getiri | yıllık %8-12 + temettü |

**yasak**: sektör ETF'leri, büyüme hisseleri, temettü ödemeyen hisseler
**çıkış**: temettü kesintisi veya fundamentaller bozulursa

---

## hedge kuralları

tüm portföylerde izin verilen short ETF'ler: SQQQ, SPXU, SH, PSQ, QID, TZA
kullanım: piyasa düşüş beklentisinde, max 2 hafta

---

## özet

| portföy | long izin | ETF izin | hedge | max poz |
|---------|-----------|----------|-------|---------|
| dengeli | hisse + ETF | evet | short ETF | 7 |
| agresif | büyüme hisse | hayır | short ETF | 8 |
| temettü | değer/temettü hisse | temettü ETF | short ETF | 15 |

---

> son güncelleme: 26 şubat 2026 | finzora ai
