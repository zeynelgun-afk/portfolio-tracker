# GÜNLÜK RAPOR PART 1 — SABAH RAPORU v2.0

> **versiyon**: 2.0 | **son güncelleme**: 10 mart 2026
> **çıktı dosyası**: `reports/daily/DAILY_SABAH_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~14:00 (NYSE dün 00:00'da kapandı, bugün 16:30 açılacak — yaz saati)
> **amaç**: piyasa analizi + haberler + otomatik tarama sonuçları + günün planı
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[SABAH RAPORU] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~14:00'da yazılır — NYSE dün gece 00:00'da kapandı
- **yaz saati (mart-kasım)**: NYSE açılış 16:30 TR, kapanış 23:00 TR
- **kış saati (kasım-mart)**: NYSE açılış 17:30 TR, kapanış 00:00 TR
- FMP fiyatları = dünün kapanışı (kesinleşmiş)
- `data/swing/daily_scan.json` = dün gece 00:30 TR'de otomatik çalışan tarama sonuçları

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

ADIM 2.5 — TWİTTER TAKİP LİSTESİ (RapidAPI / twitter241)
  → aşağıdaki 8 hesabın son tweetlerini çek (her biri için 15-20 tweet)
  → portföy sembolleriyle örtüşenleri öne çıkar
  → yorum/fikir içerenleri özetle
  → kaynak: RapidAPI twitter241.p.rapidapi.com
    key: fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7
    endpoint: GET /user-tweets?user={numeric_user_id}&count=20
    user id alma: GET /user?username={username} → id alanını base64 decode et

  TAKİP LİSTESİ:
    @CheddarFlow       → opsiyon akışı / kurumsal para hareketleri
    @berkdemirkiran_   → türk finans yorumcusu
    @yatirim           → türk finans yorumcusu (içsel analiz)
    @onestoploss       → teknik analiz / trade fikirleri
    @StockSavvyShay    → momentum hisse önerileri
    @BerkUcmz          → türk finans yorumcusu
    @TrendSpider       → teknik analiz araçları / piyasa gözlemleri
    @Jake__Wujastyk    → momentum trader / hisse önerileri

  ÖNEMLİ: tweet verileri SADECE claude'un bağlamına (context) girer,
  rapora yazılmaz. tweet bilgileri yorumlanarak piyasa değerlendirmelerine,
  sektör analizine veya pozisyon yorumlarına yedirilerek kullanılır.

ADIM 3 — EARNINGS
  → FMP: earnings-calendar (bugün + 7 gün)
  → websearch: dün gece açıklanan earnings sonuçları (portföy/swing/majör)
  → websearch: bugünkü ekonomik veri takvimi

ADIM 4 — OTOMATİK SWING TARAMA SONUÇLARI (daily_scan.json)
  ─────────────────────────────────────────────────────────
  → GitHub'dan data/swing/daily_scan.json dosyasını oku
    URL: https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/data/swing/daily_scan.json

  OKUMA AKIŞI:
  1. dosyayı oku
  2. piyasa_ozeti → vix_kritik veya vix_uyarisi varsa önce belirt
  3. ep_adaylari → skora göre sıralı, en yüksek 5'i al
  4. breakout_adaylari → skora göre sıralı, en yüksek 5'i al
  5. her aday için: seviyeler (giriş/stop/2R/3R), uyarılar, hacim katsayısı

  ELEME KRİTERLERİ (bu adımda yap):
  - VIX > 30 ise: EP adayları için "yarım pozisyon" notu ekle
  - uyarılar listesi 2'den fazla madde içeriyorsa: "ZAYIF SETUP" işaretle
  - sma50_uzerinde = false ise: agresif portföy için uyarı ekle
  - ep_skoru < 50 veya breakout_skoru < 40 ise: listeye alma

  KONTROL: mevcut swing aktif pozisyonlarla (data/swing/active.json)
  sembol çakışması var mı? varsa listeden çıkar.

ADIM 5 — FİNVİZ TARAMA (teyit katmanı)
  → websearch: finviz screener — ADIM 4'teki adayları teyit et
  → finviz.com/quote.ashx?t=SEMBOL → RSI, pattern, float, short float
  → ADIM 4 listesinde olmayan ama finviz'de öne çıkan varsa ekle
  → temettü portföy adayları: p/e <20, yield >%3
  → sektör heatmap kontrolü: hangi sektörler güçlü/zayıf

ADIM 6 — ANALİZ, PLAN VE KAYIT
  → tüm verileri sentezle
  → raporu yaz (aşağıdaki format)
  → reports/daily/DAILY_SABAH_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[SABAH RAPORU] DD Ay YYYY - kısa özet"
```

---

## RAPOR FORMATI (GITHUB'A GÖNDERİLİR)

rapor 5 bölümden oluşur.

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

### BÖLÜM 2: HABER VE ANALİZ

```markdown
## 2. haber ve analiz

### portföyü doğrudan etkileyen

**[SEMBOL] — [başlık]**
etki: [✅/❌/➡️] | portföy: [hangisi]
[2-3 cümle analiz]
aksiyon: [ne yapılacak]

### sektör ve makro gelişmeler

| gelişme | etki | ilgili hisse | yorum |
|---------|------|--------------|-------|

### analist notları

| tarih | sembol | kurum | önceki → yeni | hedef fiyat |
|-------|--------|-------|---------------|-------------|

### makro yorum

[2-4 cümle]

### bugünün veri takvimi

| saat (TR) | veri | beklenti | önceki |
|-----------|------|----------|--------|

**genel sentiment**: [pozitif / negatif / nötr / karışık]
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

### bugün ve haftalık kritik

| tarih | sembol | timing | beklenti | portföy etkisi |
|-------|--------|--------|----------|----------------|
```

---

### BÖLÜM 4: OTOMATİK SWING TARAMA SONUÇLARI

```markdown
## 4. swing tarama — {tarih} ({ep_sayisi} EP + {breakout_sayisi} breakout)

> tarama zamanı: dün gece 00:30 TR | vix: XX.X | piyasa: [risk-on/off]
> [vix_mesaj — varsa]

### EP (episodic pivot) adayları

| # | sembol | değişim | hacim | dolar hacim | close>dünkü high | ep skoru | giriş | stop | 2R hedef |
|---|--------|---------|-------|-------------|------------------|----------|-------|------|----------|
| 1 | XXX | +X.X% | Xm | $XXXm | ✅/❌ | XX/100 | $XX.XX | $XX.XX | $XX.XX |

**[SEMBOL] — detay:**
- setup: [ne tetikledi — earnings/ürün/sektör rotasyonu]
- risk/ödül: stop %X.X aşağıda, 2R hedef %X.X yukarıda
- uyarılar: [varsa]
- piyasa uyumu: [sektörü bugün güçlü mü]

### breakout (flag/base) adayları

| # | sembol | değişim | hacim katsayı | base genişlik | trend | breakout skoru | giriş | stop | 2R hedef |
|---|--------|---------|---------------|---------------|-------|----------------|-------|------|----------|
| 1 | XXX | +X.X% | X.Xx | %X | ✅/❌ | XX/100 | $XX.XX | $XX.XX | $XX.XX |

**[SEMBOL] — detay:**
- base: XX günlük konsolidasyon, %X.X genişlik
- kırılım: XX günlük high olan $XX.XX seviyesini kırdı
- uyarılar: [varsa]

### tarama notu

[daily_scan.json'dan gelen ozet.tarama_notu]

### bugün izlenecek setup önceliği

1. [SEMBOL] — EP / Breakout — neden öncelikli
2. [SEMBOL] — EP / Breakout — neden öncelikli
```

---

### BÖLÜM 5: GÜNÜN PLANI

```markdown
## 5. günün planı

### strateji notu

[2-3 cümle — bugünün seansı için yön ve yaklaşım]

### aksiyonlar

**hemen** (seans açılışında):
1. [aksiyon] — [sebep]

**izle** (seans içinde):
2. [koşul] → [aksiyon]

**pasif** (seviye bekle):
3. [sembol] $XXX'e gelirse → [değerlendir]

### swing giriş planı (varsa)

**[SEMBOL]** — EP / Breakout
- giriş koşulu: [ilk 30dk bekle, $XX.XX üzerinde konfirmasyon]
- pozisyon büyüklüğü: [tam / yarım — VIX'e göre]
- stop: $XX.XX (-%X.X)
- hedef: $XX.XX (+%X.X, 2R)

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
- amaç: sabah bilgilendirme + günün planını oluşturma + otomatik tarama okuma
- `daily_scan.json` her gece 00:30 TR'de otomatik güncellenir — fresh data garantili
- VIX > 30 durumunda swing girişlerinde "yarım pozisyon" varsayılan öneri olsun
- EP adaylarında "ilk 30 dakika bekle, konfirmasyon al" kuralı her zaman geçerli

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
**RAPIDAPI KEY**: fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7
**RAPIDAPI HOST**: twitter241.p.rapidapi.com
**DAILY SCAN**: https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/data/swing/daily_scan.json
