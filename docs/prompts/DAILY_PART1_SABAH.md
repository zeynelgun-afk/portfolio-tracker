# GÜNLÜK RAPOR PART 1 — SABAH RAPORU v2.0

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt'taki her adım sırayla ve eksiksiz uygulanmalıdır. hiçbir adım atlanamaz, kısaltılamaz veya "sonra yaparım" diye ertelenmez. bir adımı tamamlamadan diğerine geçme.
>
> **zorunlu adımlar (teker teker kontrol et):**
> - [ ] ADIM 0 — playbook oku (`docs/TRADING_PLAYBOOK.md` — aktif kuralları gözden geçir)
> - [ ] ADIM 1 — piyasa verisi (FMP batch-quote, teknik göstergeler, emtia, treasury)
> - [ ] ADIM 2 — haber toplama (web search, piyasa haberleri)
> - [ ] ADIM 2.5 — twitter takip listesi (RapidAPI ile hesap taraması)
> - [ ] ADIM 3 — earnings takvimi (FMP earnings-calendar, market cap filtresi)
> - [ ] ADIM 4 — otomatik swing tarama sonuçları (daily_scan.json oku)
> - [ ] ADIM 4.5 — ichimoku tarama (swing_ichimoku.py — adaylar + aktif pozisyonlar)
> - [ ] ADIM 5 — finviz tarama (teyit katmanı)
> - [ ] ADIM 6 — analiz, plan ve kayıt (playbook kurallarını planla çapraz kontrol et)
> - [ ] RAPOR — tüm bölümler (1-5) eksiksiz yazıldı mı?
> - [ ] GIT — commit + push yapıldı mı?
>
> **geçmiş hatalar**: adım atlama maliyetli oldu (örn: kazanç açıklaması taramasını atlama → Oracle bilançosu rapordan eksik kaldı). bu tür eksiklikler güvenilirliği zedeler. her adımı tamamla, sonra raporu yaz.

> **versiyon**: 2.2 | **son güncelleme**: 25 mart 2026
> **çıktı dosyası**: `reports/daily/DAILY_SABAH_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~14:00 (NYSE dün 23:00'da kapandı, bugün 16:30 açılacak — yaz saati)
> **amaç**: piyasa analizi + haberler + otomatik tarama sonuçları + günün planı
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[SABAH RAPORU] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~14:00'da yazılır — NYSE dün gece 23:00'da kapandı
- **yaz saati (mart-kasım)**: NYSE açılış 16:30 TR, kapanış 23:00 TR
- **kış saati (kasım-mart)**: NYSE açılış 17:30 TR, kapanış 00:00 TR
- FMP fiyatları = dünün kapanışı (kesinleşmiş)
- `data/daily_scan.json` = dün gece 00:30 TR'de otomatik çalışan tarama sonuçları

---

## ÇALIŞMA AKIŞI

bu prompt tek seferde çalışır. adımları sırayla takip et:

```
ADIM 0 — PLAYBOOK OKU
  → docs/TRADING_PLAYBOOK.md dosyasını oku
  → aktif kuralları gözden geçir (özellikle K-01 ile K-14)
  → swing istatistikleri bölümünü kontrol et (K-14: ardışık zarar → dur)
  → günün planında her karar playbook kurallarıyla çapraz kontrol edilecek

ADIM 1 — PİYASA VERİSİ (FMP + WEB)
  → batch-quote: SPY, QQQ, DIA, IWM, VIX (varsa), GCUSD, CLUSD
  → stock-price-change: tüm portföy sembolleri (1D, 5D, 1M güvenilir)
  → sector-performance-snapshot (date = dünün tarihi)
  → biggest-gainers, biggest-losers (limit 15)
  → treasury-rates (son 5 gün)

  ⚠️ ÖN PİYASA VERİSİ — WEB ARAMASI ZORUNLU:
  FMP aftermarket-quote endpoint'i NYSE seans dışında sıfır dönüyor.
  ön piyasa (pre-market) ve vadeli işlem (futures) verileri için:
  → websearch: "S&P 500 futures today" / "stock market premarket today"
  → kaynak önceliği: investing.com, cnbc.com, tradingeconomics.com, robinhood.com
  → endeks vadeli (ES, NQ, YM), petrol (Brent, WTI), altın, ORCL gibi AH hareketleri
  → raporda tablo formatında sun: ticker | dün kapanış | ön piyasa | fark% | not

ADIM 2 — HABER TOPLAMA
  → FMP: news/stock (tüm portföy + swing sembolleri), fmp-articles (limit 15)
  → FMP: upgrades-downgrades (portföy hisseleri, limit 20)
  → websearch: futures ve pre-market durumu
  → websearch: dün gece / bugün sabah önemli piyasa haberleri
  → websearch: portföy hisselerini etkileyen gelişmeler
  → websearch: Fed faiz olasılıkları (Kalshi/Polymarket)

ADIM 2.5 — TWİTTER TAKİP LİSTESİ (RapidAPI / twitter241)
  → aşağıdaki 9 hesabın son tweetlerini çek (her biri için 15-20 tweet)
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
    @RyanDetrick       → piyasa istatistikleri / mevsimsellik verileri

  ÖNEMLİ: tweet verileri SADECE claude'un bağlamına (context) girer,
  rapora yazılmaz. tweet bilgileri yorumlanarak piyasa değerlendirmelerine,
  sektör analizine veya pozisyon yorumlarına yedirilerek kullanılır.

ADIM 3 — EARNINGS
  → FMP: earnings-calendar (bugün + 7 gün)
  → websearch: dün gece açıklanan earnings sonuçları (portföy/swing/majör)
  → websearch: bugünkü ekonomik veri takvimi

ADIM 4 — OTOMATİK SWING TARAMA SONUÇLARI (daily_scan.json)
  ─────────────────────────────────────────────────────────
  → GitHub'dan data/daily_scan.json dosyasını oku
    URL: https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/data/daily_scan.json

  OKUMA AKIŞI:
  1. dosyayı oku
  2. piyasa_ozeti → vix_kritik veya vix_uyarisi varsa önce belirt
  3. ep_adaylari → skora göre sıralı, en yüksek 5'i al
  4. breakout_adaylari → skora göre sıralı, en yüksek 5'i al
  5. her aday için: seviyeler (giriş/stop/2R/3R), uyarılar, hacim katsayısı

  ELEME KRİTERLERİ (bu adımda yap):
  - VIX > 30 ise: EP adayları için "yarım pozisyon" notu ekle
  - uyarılar listesi 2'den fazla madde içeriyorsa: "ZAYIF SETUP" işaretle
  - sma200_uzerinde = false ise: uzun vadeli trend aşağı, yarım pozisyon veya geç
  - (v1 skor filtresi kaldırıldı — v2'de ichimoku sinyali belirleyici, skor eşiği yok)

  KONTROL: mevcut swing aktif pozisyonlarla (data/swing/active.json)
  sembol çakışması var mı? varsa listeden çıkar.

ADIM 4.5 — İCHİMOKU TARAMA (swing v2.1)
  → aktif swing pozisyonları için ichimoku seviyeleri güncelle:
    python scripts/swing_ichimoku.py --aktif
    → kijun trailing stop değişti mi? çıkış sinyali var mı?
  → ADIM 4'ten geçen adaylar için tam ichimoku tarama:
    python scripts/swing_ichimoku.py SEMBOL1,SEMBOL2,...
  → sonuçları rapora ekle:
    - "GİRİŞ ✅": kumo kırılımı/kijun bounce + hacim teyidi + SMA200 üstü
    - "GİRİŞ ⚠️": sinyal var ama hacim zayıf veya SMA200 altı
    - "TREND DEVAM": kumo üstü ama bugün giriş sinyali yok
    - "BEKLE": sinyal zayıf
    - "GİRME ❌": kumo altı + düşüş trendi
  → sinyal veren adaylar için claude temel değerlendirme yapacak (sabit rasyo filtresi yok)
  → mevcut aktif pozisyonların ichimoku durumunu raporla (kijun mesafe, çıkış sinyali)

ADIM 5 — FİNVİZ TARAMA (teyit katmanı)
  → websearch: finviz screener — ADIM 4'teki adayları teyit et
  → finviz.com/quote.ashx?t=SEMBOL → pattern, float, short float
  → ADIM 4 listesinde olmayan ama finviz'de öne çıkan varsa ekle
  → temettü portföy adayları: p/e <20, yield >%3
  → sektör heatmap kontrolü: hangi sektörler güçlü/zayıf

ADIM 6 — ANALİZ, PLAN VE KAYIT
  → tüm verileri sentezle
  → PLAYBOOK ÇAPRAZ KONTROL: günün planındaki her aksiyonu docs/TRADING_PLAYBOOK.md kurallarıyla kontrol et
    - yeni giriş planlıyorsan: K-01 (makro veri), K-02 (kriz rallisi), K-03 (VIX+small cap), K-13 (VIX ortam)
    - çıkış planlıyorsan: K-06 (stop override), K-07 (trailing stop), K-08 (momentum), K-09 (stop yakın)
    - swing planlıyorsan: K-14 (ardışık zarar → dur), ichimoku giriş sinyali zorunlu
    - temel analiz: claude hisse bazında değerlendirir, sabit rasyo filtresi yok
    - kural ihlali varsa raporda açıkça belirt ve gerekçelendir
  → raporu yaz (aşağıdaki format)
  → reports/daily/DAILY_SABAH_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[SABAH RAPORU] DD Ay YYYY - kısa özet"
  → TELEGRAM GÖNDERİMİ (git push'tan SONRA):
    1. python scripts/telegram_notify.py --type premarket --theme "[günün özeti]"
    2. python scripts/telegram_notify.py --type report --file reports/daily/DAILY_SABAH_YYYY-MM-DD.md
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

**vadeli işlemler / ön piyasa** ({bugün sabah}, web aramasından):

| ticker | dün kapanış | ön piyasa | fark | not |
|--------|------------|-----------|------|-----|
| S&P 500 vadeli | X,XXX | X,XXX | ±%X.XX | [kısa not] |
| NASDAQ vadeli | XX,XXX | XX,XXX | ±%X.XX | |
| Dow vadeli | XX,XXX | XX,XXX | ±%X.XX | |
| Brent | $XX.XX | $XX.XX | ±%X.XX | |
| [AH hareket eden hisse] | $XX.XX | $XX.XX | ±%X.XX | [neden] |

> kaynak: investing.com / cnbc / robinhood (FMP aftermarket seans dışında sıfır dönüyor)

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

| # | sembol | değişim | hacim | ep skoru | ichimoku | SMA200 | karar |
|---|--------|---------|-------|----------|----------|--------|-------|
| 1 | XXX | +X.X% | Xm | XX/100 | kumo üstü/içi/altı | ✅/❌ | GİRİŞ/BEKLE/RED |

**[SEMBOL] — detay:**
- setup: [ne tetikledi — earnings/ürün/sektör rotasyonu]
- ichimoku: fiyat $XX vs kumo $XX-$XX, tenkan/kijun, sinyal: [kumo kırılımı/kijun bounce/yok]
- hacim: X.Xx ortalama, OBV: [yükseliş/düşüş/nötr]
- stop: $XX (kijun), mesafe: -%X.X, ATR: X.Xx
- risk/ödül: kijun stop %X.X aşağıda
- claude temel değerlendirme: [sektör bağlamı, hikaye, katalizör]

### breakout (flag/base) adayları

| # | sembol | değişim | hacim katsayı | breakout skoru | ichimoku | SMA200 | karar |
|---|--------|---------|---------------|----------------|----------|--------|-------|
| 1 | XXX | +X.X% | X.Xx | XX/100 | kumo üstü/içi/altı | ✅/❌ | GİRİŞ/BEKLE/RED |

**[SEMBOL] — detay:**
- base: XX günlük konsolidasyon
- ichimoku: [sinyal tipi + hacim teyidi]
- claude temel değerlendirme: [hisse bazında]

### mevcut swing pozisyonları ichimoku durumu

| sembol | PnL | kijun stop | kumo | tenkan vs kijun | çıkış sinyali | durum |
|--------|-----|-----------|------|-----------------|----------------|-------|
| XXX | +X.X% | $XX.XX | üstü/içi/altı | ↑/↓ | var/yok | [kısa yorum] |

### tarama notu

[daily_scan.json'dan gelen ozet.tarama_notu]

### bugün izlenecek setup önceliği

1. [SEMBOL] — ichimoku sinyal: [kumo kırılımı/kijun bounce] — neden öncelikli
2. [SEMBOL] — ichimoku sinyal: [tip] — neden öncelikli
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
- stop: $XX.XX (kijun/kumo, -%X.X)
- ichimoku: [sinyal tipi, kumo/kijun seviyeleri]

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
- EP adaylarında "ilk 30 dakika bekle, konfirmasyon al" kuralı seans promptunda uygulanır — sabah planına yaz

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
**RAPIDAPI KEY**: fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7
**RAPIDAPI HOST**: twitter241.p.rapidapi.com
**DAILY SCAN**: https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/data/daily_scan.json
