# GÜNLÜK RAPOR PART 1 — SABAH RAPORU v1.0

> **versiyon**: 1.0 | **son güncelleme**: 3 mart 2026
> **çıktı dosyası**: `reports/daily/DAILY_SABAH_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~14:00 (NYSE dün 00:00'da kapandı, bugün 17:30 açılacak)
> **amaç**: piyasa analizi + haberler + tarama + günün planı
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[SABAH RAPORU] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~14:00'da yazılır — NYSE dün gece 00:00'da kapandı
- FMP fiyatları = dünün kapanışı (kesinleşmiş)
- after-hours: dün 00:00-02:00 TR
- pre-market: bugün 16:00-17:30 TR
- bugünün seansı: 17:30-00:00 TR

---

## ÇALIŞMA AKIŞI

bu prompt tek seferde çalışır. adımları sırayla takip et:

```
ADIM 1 — PİYASA VERİSİ (FMP)
  → batch-quote: SPY, QQQ, DIA, IWM, VIX (varsa), GCUSD, CLUSD
  → sector-performance-snapshot (date = dünün tarihi)
  → biggest-gainers, biggest-losers (limit 15)
  → treasury-rates (son 5 gün)

ADIM 2 — HABER TOPLAMA
  → FMP: news/stock (tüm portföy + swing sembolleri), fmp-articles (limit 15)
  → FMP: upgrades-downgrades (portföy hisseleri, limit 20)
  → websearch: futures ve pre-market durumu
  → websearch: dün gece / bugün sabah önemli piyasa haberleri
  → websearch: portföy hisselerini etkileyen gelişmeler
  → websearch: Fed faiz olasılıkları (Kalshi/Polymarket)

ADIM 3 — EARNINGS
  → FMP: earnings-calendar (bugün + 7 gün)
  → websearch: dün gece açıklanan earnings sonuçları (portföy/swing/majör)
  → websearch: bugünkü ekonomik veri takvimi

ADIM 4 — FİNVİZ TARAMA (ücretsiz)
  → websearch: finviz.com screener sonuçları
  → swing adayları: RSI < 35, market cap > 500M, change > -5%
  → momentum tarama: RSI 50-70, SMA20 üzeri, volume > avg
  → sektör heatmap kontrolü: hangi sektörler güçlü/zayıf
  → agresif portföy adayları: earnings beat > %10, RS yükselen
  → sonuçları mevcut watchlist ile karşılaştır

ADIM 5 — ANALİZ, PLAN VE KAYIT
  → tüm verileri sentezle
  → raporu yaz (aşağıdaki format)
  → reports/daily/DAILY_SABAH_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[SABAH RAPORU] DD Ay YYYY - kısa özet"
```

---

## RAPOR FORMATI (CHAT'TE)

rapor 5 bölümden oluşur. github'a push edilmez, sadece chat'te paylaşılır.

---

### BÖLÜM 1: PİYASA GÖRÜNÜMÜ

```markdown
## 1. piyasa — dün + bugün

### dünün kapanışı ({tarih}, {gün})

| ticker | kapanış | değişim | not |
|--------|---------|---------|-----|
| SPY | $XXX.XX | +X.XX% | [kısa not] |
| QQQ | $XXX.XX | +X.XX% | |
| DIA | $XXX.XX | +X.XX% | |
| IWM | $XXX.XX | +X.XX% | |

**emtia + döviz**: altın $X,XXX (±%), WTI $XX (±%), DXY XX.X, 10Y %X.XX

### bugünün öncü göstergeleri

**futures** ({bugün sabah}):
- S&P 500: ±%X.XX | NASDAQ: ±%X.XX
- [kısa yorum]

### sektör performansı (dün)

en güçlü 3: [sektör +%], [sektör +%], [sektör +%]
en zayıf 3: [sektör -%], [sektör -%], [sektör -%]
rotasyon sinyali: [risk-on / risk-off / karışık]

### risk değerlendirmesi

- VIX: XX.X → [risk-on/off/nötr]
- breadth: gainers/losers oranı
- prediction markets: Kalshi Fed faiz %XX
```

---

### BÖLÜM 2: HABER VE YORUM ANALİZİ

```markdown
## 2. haber ve yorum analizi

### 🔴 portföyü doğrudan etkileyen

**[SEMBOL] — [başlık]**
etki: [✅/❌/➡️] | portföy: [hangisi]
[2-3 cümle analiz]
aksiyon: [ne yapılacak]

### 🟠 sektör ve makro gelişmeler

| gelişme | etki | ilgili hisse | yorum |
|---------|------|--------------|-------|

### 📊 analist notları ve grade değişiklikleri

| tarih | sembol | kurum | önceki → yeni | hedef fiyat |
|-------|--------|-------|---------------|-------------|

### 🌍 makro yorum

[2-4 cümle]

### bugünün veri takvimi

| saat (TR) | veri | beklenti | önceki |
|-----------|------|----------|--------|

### haber özeti skoru

📊 **genel sentiment**: [pozitif / negatif / nötr / karışık]
```

---

### BÖLÜM 3: EARNINGS TAKVİMİ

```markdown
## 3. earnings takvimi

### dün gece (AMC) — sonuçlar

SEMBOL — [şirket]
  EPS: $X.XX vs beklenti $X.XX → beat/miss %X
  gelir: $X.XXB vs beklenti $X.XXB → beat/miss %X
  guidance: [yükseltildi / korundu / düşürüldü]
  AH/PM tepki: $XXX (±%X)
  portföy etkisi: [doğrudan/dolaylı — aksiyon]

### bugün

**BMO**: [SEMBOL] — EPS beklentisi $X.XX
**AMC**: [SEMBOL] — EPS beklentisi $X.XX

### haftalık kritik

| tarih | sembol | timing | portföy etkisi |
|-------|--------|--------|----------------|
```

---

### BÖLÜM 4: FİNVİZ TARAMA SONUÇLARI

```markdown
## 4. finviz tarama sonuçları

### swing adayları (RSI oversold + momentum)

| sembol | fiyat | RSI | sektör | market cap | sinyal |
|--------|-------|-----|--------|------------|--------|

### agresif portföy adayları

kriter: earnings beat >%10, RS yükselen, beta >1.2, market cap 00M-0B, 50MA üzeri, hacim 1.5x+

| sembol | fiyat | neden | sektör | earnings |
|--------|-------|-------|--------|----------|

### dengeli portföy adayları

kriter: multi-sector value + momentum blend, makul değerleme, güçlü momentum, mevcut pozisyonlarla düşük korelasyon

| sembol | fiyat | neden | sektör | p/e | momentum |
|--------|-------|-------|--------|-----|----------|

### temettü portföy adayları

kriter: p/e <20, temettü yield >%3, güçlü FCF, D/E <1.5, temettü büyüme geçmişi

| sembol | fiyat | yield | p/e | sektör | neden |
|--------|-------|-------|-----|--------|-------|

### sektör heatmap özeti

[hangi sektörler yeşil/kırmızı — rotasyon sinyali]

### watchlist güncellemesi

eklenmeli: [sembol — neden]
çıkarılmalı: [sembol — neden]
urgency değişmeli: [sembol — eski → yeni]
```

---

### BÖLÜM 5: GÜNÜN PLANI

```markdown
## 5. günün planı

### strateji notu

[2-3 cümle — bugünün seansı için yön ve yaklaşım]

### aksiyonlar

🔴 **hemen** (seans açılışta):
1. [aksiyon] — [sebep]

🟡 **izle** (seans içinde):
2. [koşul] → [aksiyon]

🟢 **pasif** (seviye bekle):
3. [sembol] $XXX'e gelirse → [değerlendir]

### dikkat edilecekler

- [risk 1]
- [fırsat 1]

---

*finzora ai | fmp api | new york kapalı*
```

---

## KURALLAR

- rapor github'a push edilir (`reports/daily/DAILY_SABAH_YYYY-MM-DD.md`)
- JSON dosyalarına dokunma (veri güncellemesi part 2'de yapılacak)
- amacı: sabah bilgilendirme + günün planını oluşturma + Finviz tarama
- finviz taramasını websearch ile yap (ücretsiz versiyon)

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
