# günlük portföy fırsat raporu güncelleme — 8 nisan 2026 tr 15:38

> finzora ai | ana rapor: `DAILY_PORTFOY_2026-04-08_FINAL.md` (tr 12:44) | bu güncelleme: tr 15:38 | seans açılışına 52 dk
>
> **amaç**: part 1c yeniden çalıştırıldı, ön piyasa gap-up sonrası yeni adaylar tarandı. bu rapor final planı ile birlikte **okunmalıdır**, FINAL planı geçersiz kılmaz, **üzerine ek adaylar** ekler.

---

## 1. yeniden tarama gerekçesi

tr 09:39 (08:44 UTC) FINAL raporu yazıldığında ön piyasa durumu belirsizdi. şimdi:
- vix 24.17 → **20.29** (-%21.31)
- s&p vadeli +%2.1 → **+%2.81**
- **4 FINAL EKLE adayı kovalama kapsamında** (amat, klac, wdc, cat marjinal)
- ateşkes rally'si bazı sektörlerde kayıp yarattı (savunma, defansif sağlık) — yeni fırsat pencereleri
- ay aktif yeni temalar: utility (düşük beta rally-dışı), nükleer güç (gev), memory chip (samsung beat sonrası)

part 1c scripts (scripts/portfolio_scan_*.py) yeniden çalıştırıldı, genişletilmiş evrenle skor hesaplandı, K-04 (SMA50) ve K-18 (insider) filtreleri tüm adaylara uygulandı.

---

## 2. yeniden tarama — yeni bulgular

### dengeli portföy — yeni EKLE adayları (9+ skor, K-04 ✅, K-18 ✅)

| sembol | skor | fiyat | rsi | sma50 | sma200 | not |
|--------|:----:|:-----:|:---:|:-----:|:------:|-----|
| **MU** | 14 | $377.58 | 47.3 | ❌ $402.67 | ✅ | K-04 ihlali → **GEÇ** (skor yüksek ama trend bozuk) |
| MRK | 13 | - | - | - | - | zaten temettü planında |
| **CAT** | 12 | $724.44 | 54.4 | ✅ | ✅ | FINAL planında, ön piyasa marjinal üst — **koşullu** |
| **LMT** | 12 | $627.70 | 49.6 | ❌ $636.09 | ✅ | ateşkes kayıp, yakın ama sma50 altı → **İZLE** |
| **ASML** | 11 | $1306.45 | 44.8 | ❌ $1391.46 | ✅ | K-04 ihlali + chip ekipman gap — **GEÇ** |
| **DUK** | 11 | $131.82 | 58.4 | ✅ | ✅ | **🆕 YENİ EKLE** — utility, düşük beta, rally-dışı |
| **GEV** | 10 | $910.75 | 59.6 | ✅ | ✅ | **🆕 YENİ EKLE** — nükleer/AI güç, sma50 üstü |
| **HON** | 9 | $223.84 | 41.0 | ❌ $233.80 | ✅ | K-04 ihlali → **GEÇ** |
| **GD** | 9 | $348.43 | 47.4 | ❌ $352.93 | ✅ | ateşkes kayıp, sma50 altı → **İZLE** |
| **NEE** | 9 | $93.67 | 59.6 | ✅ | ✅ | **🆕 YENİ EKLE** — utility, AI güç talebi |
| **UBER** | 9 | $71.73 | 44.9 | ❌ $74.34 | ❌ $86.80 | K-04 + K-04b ihlali → **GEÇ** |

**dengeli sonuç**: FINAL planındaki CAT korunur (koşullu). **3 yeni aday eklendi**: DUK, NEE, GEV (hepsi K-04+K-18 temiz, rally-dışı veya rally-bağımsız).

### agresif portföy — yeni bulgular

| sembol | skor | fiyat | rsi | sma50 | sma200 | durum |
|--------|:----:|:-----:|:---:|:-----:|:------:|-------|
| **POWL** | **17** | $201.70 | 63.0 | ✅ | ✅ | **🚫 K-18 ELENDİ**: son 30g **$27.3M senior insider satış** (METCALF EXEC VP) |
| **WDC** | 17 | $311.96 | 59.1 | ✅ | ✅ | FINAL'da, ön piyasa kovalama — **bugün YOK** |
| **KLAC** | 14 | $1,548.85 | 57.2 | ✅ | ✅ | FINAL'da, kovalama — **bugün YOK** |
| **AMAT** | 14 | $354.31 | 52.4 | ✅ | ✅ | FINAL'da, kovalama canlı $378.30 — **bugün YOK** |
| **MU** | 12 | $377.58 | 47.3 | ❌ | ✅ | K-04 ihlali → **İZLE** devam |
| **VRT** | 12 | - | - | - | - | cooling → **İZLE** |
| **GEV** | 10 | $910.75 | 59.6 | ✅ | ✅ | dengeli için alındı |

**agresif sonuç**: **POWL 17 skor ama K-18 elemesi kritik**. mart 2026 kayıp serisi POWL ile başlamıştı ("POWL → K-13b + K-18 ihlali (insider $25M satış kontrol edilmedi)"). K-18 otomatik script bu sefer yakaladı — disiplin çalışıyor. POWL 30 gün cool-down'a alındı.

**yeni aday yok** agresif için (POWL elendi, diğer 3 zaten FINAL'da ve kovalama).

### temettü portföyü — yeni bulgular

| sembol | skor | fiyat | rsi | sma50 | durum |
|--------|:----:|:-----:|:---:|:-----:|-------|
| **MRK** | 11 | $119.36 | - | ✅ | FINAL'da, ✅ **HÂLÂ GEÇERLİ**, plana göre al |
| **UPS** | 11 | $97.58 | 40.4 | ❌ $106.7 | FINAL'da koşullu, **SMA50 çok uzak**, koşul karşılanmıyor |
| **T** | 11 | $28.03 | 48.3 | ✅ | zaten portföyde → **BÜYÜT değerlendirme** |
| **VZ** | 11 | $48.62 | 41.0 | ✅ | zaten portföyde → **BÜYÜT değerlendirme** |
| **BMY** | 10 | $57.67 | 42.7 | ❌ $59.32 | K-04 marjinal ihlal → **İZLE** |
| **GIS** | 10 | $36.80 | **30.8** | ❌ $42.63 | RSI oversold + K-04 ihlal + K-04b (sma200 altı) → **GEÇ** (tez bozulma sinyali) |
| **COP** | 8 | - | - | - | enerji ateşkes kaybı → **İZLE** |

**temettü sonuç**: FINAL planındaki MRK ve UPS (koşullu) korunur. **T ve VZ için BÜYÜT değerlendirmesi** yeni bulgu.

### BÜYÜT değerlendirmesi — T ve VZ

**T (AT&T)** — skor 11, zaten portföyde:
- mevcut: 773 hisse @ $26.17 maliyet, k/z **+%7.11**
- fiyat $28.03 | ağırlık %15.0 (temettü portföy)
- RSI 48.3 (nötr), SMA50 ✅, SMA200 ✅
- katalizör: 7 nisan goldman sachs hedef +%11
- K-12 limit: %40 telekom — alan var (şu an %15 + VZ %3.6 = %18.6)
- **BÜYÜT uygun** — koşul: seans içi sağlıklı trend, k/z devam etmesi

**VZ (Verizon)** — skor 11, zaten portföyde:
- mevcut: 107 hisse @ $39.83 maliyet, k/z **+%22.07**
- fiyat $48.62 | ağırlık %3.6 (temettü portföy)
- RSI **41.0 (düşük)** ⚠️ — kâr alma baskısı sinyali olabilir
- SMA50 ✅ ($48.54), SMA200 ✅
- katalizör: iki küçük kurum alımı haberi
- **BÜYÜT marjinal** — RSI 41 kâr al bölgesine yaklaşıyor. kâr kilidi tercihi: kâr koru, büyütme

**karar**: T büyüt (mevcut plandaki MO büyütmesine ek olarak değerlendir, ama K-12 ve K-17 sınırları kontrol et), VZ mevcut kâr pozisyonunu koru, büyütme yok.

---

## 3. güncel nihai EKLE listesi (ön piyasa gap overlay)

### ✅ bugün giriş uygun (kesin)

| # | portföy | sembol | aksiyon | fiyat aralığı | tutar | gerekçe |
|---|---------|--------|---------|---------------|------:|---------|
| 1 | temettü | **MRK** | AL | $118-122 | $6,000 | defansif sağlık, minimal gap, plan içinde |
| 2 | temettü | **PM** | SAT | $160 altı ilk 30 dk | -$12,127 | k-04 ihlal, rsi 34.6, fda pouch endişesi, tez bozulma |
| 3 | dengeli | **DUK** | 🆕 AL | $129-133 | $13,182 | utility, düşük beta, rally-bağımsız, k-04+k-18 temiz |

### 🟡 koşullu (ilk 30 dk teyit)

| # | portföy | sembol | aksiyon | koşul | tutar |
|---|---------|--------|---------|-------|------:|
| 4 | dengeli | **CAT** | AL | pullback $715-735 aralığına | $16,675 |
| 5 | temettü | **MO** | BÜYÜT | sma50 ($66.06) üstü kapanış | +$5,000 |
| 6 | dengeli | **NEE** | 🆕 AL | $91-95 aralığı içinde kalırsa | $9,367 |
| 7 | dengeli | **GEV** | 🆕 AL | pullback $895-925 aralığına | $9,108 |
| 8 | temettü | **T** | BÜYÜT | sağlıklı trend devam, rsi>45 | +$8,000 |

### ⛔ bugün yok (kovalama veya koşul karşılanmıyor)

| sembol | portföy | sebep |
|--------|---------|-------|
| **WDC** | agresif | ön piyasa +%6-7 kovalama, hedef aralık üstü |
| **KLAC** | agresif | ön piyasa +%5-7 kovalama, hedef aralık üstü |
| **AMAT** | agresif | canlı $378.30 teyit (+%6.77), hedef $360 üstü |
| **UPS** | temettü | sma50 $106.7 %9 uzak, koşul karşılanmıyor |
| **POWL** | agresif | **K-18 $27.3M insider satış ELENDİ**, 30g cool-down |

---

## 4. senaryo bazlı toplam hareket tahmini

### senaryo A (%40): açılış gap-up kalıcı, pullback yok

- MRK al (+$6,000) ✅
- PM sat (-$12,127) koşul met
- **DUK al (+$13,182)** 🆕 — geçerli, rally-dışı
- CAT, NEE, GEV, MO büyüt, T büyüt → pullback gelmediği için **geç**
- **net**: +$6K + (-$12.1K) + $13.2K = **+$7.1K alım, $5K nakit azaltma**, plan edilen $78.8K'nın %9'u

### senaryo B (%40): açılış gap, ilk 30 dk %1-2 pullback

- senaryo A + **CAT ($16.7K), NEE ($9.4K), GEV ($9.1K), MO +$5K, T +$8K** koşullu alımlar açılır
- **net**: +$68K alım, plan edilenin %86'sı
- bu senaryo FINAL planın en yakın uygulaması

### senaryo C (%20): ikinci dalga rally, pullback gelmez

- senaryo A uygulanır, koşullular kaçar
- yarın sabah raporu (9 nisan) kritik: k-14 kriter 2/3 yeşil ise agresif ikinci pencere (WDC/KLAC/AMAT yarım pozisyon) + dengeli pullback bekleyen adaylar
- **net**: senaryo A ile aynı (~$7K)

### kümülatif risk değerlendirmesi

- **maksimum alım** (senaryo B): $68K (FINAL plandan daha fazla, çünkü DUK/NEE/GEV yeni eklendi ama $45K agresif chip'ler geçti — net daha az risk yoğunlaşması)
- **K-12 sektör limitleri**:
  - dengeli utility (DUK+NEE): $22.5K = %20 — limit %25 altı ✅
  - dengeli sanayi (CAT+GEV): $25.8K = %23 — limit %25 sınır ⚠️ (GEV güç altyapı, CAT global capex, kısmen korelasyon)
  - temettü telekom (T büyüt sonrası): %15 + %8 = %23 — limit %40 altı ✅
  - temettü sağlık (MRK): %5 — limit %15 altı ✅
- **K-17 korelasyon riski**: dengeli utility (DUK+NEE) aynı katman, 2 pozisyon limit max 3 altı ✅. sanayi (CAT+GEV) farklı alt-katman (endüstriyel capex vs güç altyapı) — kabul edilebilir
- **maksimum zarar** (tüm stoplar tetiklenirse): ~$4,500-5,500 (FINAL plan ile benzer, %0.8 portföy toplamı)

---

## 5. FINAL plana göre ana farklar

| alan | FINAL (09:39) | GÜNCEL (15:38) | fark |
|------|--------------|----------------|------|
| agresif yeni giriş | WDC + KLAC + AMAT ($45.4K) | **hiçbiri (kovalama)** | -$45.4K |
| dengeli yeni giriş | CAT tek ($16.7K) | CAT + **DUK + NEE + GEV** ($48.3K) | +$31.6K |
| temettü yeni giriş | MRK + UPS koşullu ($11.8K) | MRK kesin + UPS koşul karşılanmıyor | -$5.8K |
| büyüt | MO sadece ($5K) | MO + **T** koşullu ($13K) | +$8K |
| toplam yeni alım | $78.8K | **senaryo A: $19K \| B: $68K** | -$11K ila -$60K |
| POWL | yok | **K-18 ile elendi, watchlist'ten çıktı** | yeni bilgi |
| kovalama yasağı | yok (bilinmiyordu) | aktif, 4 pozisyon | disiplin |

**temel yeniden yönlenme**: ateşkes rally'si agresif chip tedarik zinciri adaylarını kovalama kapsamına aldı (AMAT canlı +%6.77 teyit). karşılığında rally-dışı defansif kalite (DUK, NEE utility) ve AI güç altyapı (GEV) dengeli portföye yeni EKLE olarak açıldı. risk-on ortamında defansifleri almak kontra-intuitive görünebilir, ancak (1) K-04 filtresi uyguluyor, (2) ön piyasada gap yok veya minimal, (3) hedef aralık içinde. rally devam ederse underperform, bozulursa outperform — asimetrik risk lehine.

---

## 6. karşıt argüman — neden yanlış olabilirim

1. **DUK/NEE utility trade dezavantajı**: risk-on rally ciddi devam ederse utilities underperform eder (2023 örneği: SPY +%24, XLU +%1). bu alım "rally katılım" değil, "rally hedge" gibi olur.

2. **GEV ateşkes etkisi**: güç altyapısı petrol düşüşünden dolaylı etkilenebilir (doğalgaz fiyatları petrolü takip eder, gaz türbin talebi marjı zayıflayabilir). ancak AI veri merkezi talep temeli sağlam.

3. **Chip kovalama fırsat maliyeti**: AMAT/KLAC/WDC gap-up kapanmazsa yarın +%2-3 daha yüksekten girmek zorunda kalırım. fırsat maliyeti tahminim ~$1.5-2K (yarın + ufuk) vs kovalama kayıp riski ~$2.5-3.5K. R:R disiplin lehine ama marjinal.

4. **DUK K-04 geçişi sıkı**: fiyat $131.82, sma50 $127.70 — sadece +%3.2 yukarıda. seans içi sma50 dokunuşu gelirse giriş tetiklenebilir ama aynı gün +%2 düşüş de mümkün. stop disiplini kritik.

5. **POWL K-18 elemesi doğru ama skor sinyal kaybı**: POWL 17 skor, agresif sistemin en yüksek sinyali. K-18 eleme doğru disiplin (mart 2026 dersi) ama 17 skor bilgisini ARAMAK için POWL'a benzer insider temiz alternatifler aranmalı. bugünlük evrende bulunmadı.

---

*finzora ai | portfolio_scan_common.py v3 + ön piyasa gap overlay | K-18 POWL elemesi + DUK/NEE/GEV yeni EKLE | FINAL rapora ek güncelleme*
