# PORTFÖY YÖNETİM KURALLARI

> **son güncelleme**: 26 şubat 2026

---

## yapı

3 aktif portföy, toplam $600K simülasyon sermayesi.

| portföy | sermaye | ağırlık |
|---------|---------|---------|
| dengeli | $100K | %17 |
| agresif büyüme | $400K | %66 |
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

## 2. agresif büyüme ($400K) ⭐ ANA PORTFÖY

**ruh**: sektör-agnostik momentum + katalizör bazlı büyüme, yıllık %30+ hedef

| kural | değer |
|-------|-------|
| izin verilen | HERHANGİ bir sektörden güçlü momentum hisseler |
| sektör kısıtı | YOK — enerji, sağlık, finans, savunma, tech hepsi olabilir |
| giriş kriterleri | güçlü katalizör + teknik momentum + fundamental filtre |
| max pozisyon | 10 |
| min sektör dengesi | minimum 3 farklı sektör |
| pozisyon büyüklüğü | max %10 ($40K) |
| çıkış kriteri | stop-loss / hedef / momentum kaybı (sabit süre yok) |
| stop-loss | %8 (katı) |
| kar hedefi | minimum %10 |
| R:R minimum | 2:1 |
| hedef getiri | yıllık %30+ |

**katalizörler**: earnings beat >%10, teknik breakout, M&A duyurusu, contract win, jeopolitik tetikleyici

**kademeli çıkış**: +%5-7'de %33 sat → +%10-12'de %33 sat → kalan trailing stop

**yasak**: katalizör olmadan almak, tek sektöre >%40 exposure, stop-loss gevşetmek

detay: `docs/AGGRESSIVE_STRATEGY.md`

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
