# GÜNLÜK RAPOR PART 1 — SABAH RAPORU v2.3

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt'taki her adım sırayla ve eksiksiz uygulanmalıdır. hiçbir adım atlanamaz, kısaltılamaz veya "sonra yaparım" diye ertelenmez. bir adımı tamamlamadan diğerine geçme.
>
> **zorunlu adımlar (teker teker kontrol et):**
> - [ ] ADIM 0 — playbook + piyasa istihbaratı (`TRADING_PLAYBOOK.md` + `MARKET_INTELLIGENCE.md` + web arama)
> - [ ] ADIM 1 — piyasa verisi (FMP batch-quote, teknik göstergeler, emtia, treasury)
> - [ ] ADIM 2 — haber toplama (FMP news/stock keyword filtresi, web search, piyasa haberleri)
> - [ ] ADIM 2.5 — twitter takip listesi (RapidAPI ile hesap taraması)
> - [ ] ADIM 3 — earnings takvimi (FMP earnings-calendar, market cap filtresi)
> - [ ] ADIM 4 — swing tarama (FMP screener → ichimoku 4/4 → v2.3 filtreleri)
> - [ ] ADIM 5 — finviz tarama (teyit katmanı)
> - [ ] ADIM 6 — analiz, plan ve kayıt (playbook kurallarını planla çapraz kontrol et)
> - [ ] RAPOR — tüm bölümler (0-5) eksiksiz yazıldı mı?
> - [ ] GIT — commit + push yapıldı mı?
>
> **geçmiş hatalar**: adım atlama maliyetli oldu (örn: kazanç açıklaması taramasını atlama → Oracle bilançosu rapordan eksik kaldı). bu tür eksiklikler güvenilirliği zedeler. her adımı tamamla, sonra raporu yaz.

> **versiyon**: 2.3 | **son güncelleme**: 6 nisan 2026
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
- swing tarama: seans içinde FMP screener'dan ~1,100 hisse çekilip ichimoku 4/4 taranır

---

## ÇALIŞMA AKIŞI

bu prompt tek seferde çalışır. adımları sırayla takip et:

```
ADIM 0 — PLAYBOOK + PİYASA İSTİHBARATI
  → docs/TRADING_PLAYBOOK.md dosyasını oku
  → aktif kuralları gözden geçir (özellikle K-01 ile K-20, K-13 v4.1 sektör bazlı VIX kuralı)
  → docs/MARKET_INTELLIGENCE.md okuyarak istihbarat çerçevesini hatırla
  → web aramasıyla güncel piyasa istihbaratı topla:
    - dünden bu yana kritik haberler (makro, jeopolitik, sektörel)
    - her haberin neden-sonuç zinciri (1./2./3. derece etki)
    - bu haftanın kritik olayları ve senaryolar (FOMC, earnings, veri)
    - aktif tema güç skorları (AI altyapı, enerji, savunma vb.)
    - prediction markets değişimleri (kalshi, polymarket)
    - AI tedarik zinciri katmanlarının durumu (ekipman, kimya, güç, optik)
  → PORTFÖY ÖNCEDEN POZİSYONLAMA kararı:
    - hangi temaya ağırlık artır/azalt?
    - hangi katmanda fırsat var?
    - mod değişikliği gerekiyor mu? (agresif/normal/dikkatli/defansif)

ADIM 1 — PİYASA VERİSİ (FMP + WEB)
  → batch-quote: SPY, QQQ, DIA, IWM, VIXY (VIX proxy), GCUSD, USO (petrol proxy)
    ⚠️ doğrudan ^VIX ve CLUSD/WTIUSD güvenilmez — VIXY ve USO kullan
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
  → FMP news/stock: tüm portföy + swing + watchlist sembollerini virgülle birleştir, TEK çağrıda çek (limit 50)
    - negatif sinyal taraması: lawsuit, downgrade, SEC, investigation, cut dividend, miss, warning, recall, resign
    - pozitif sinyal taraması: beat, upgrade, raise, target, deal, contract, approval, partnership
    - eşleşen haberler → web search ile doğrula ve derinleştir
    - eşleşmeyen dolgu haberler (zacks "is X undervalued" vb.) → atla
    ⚠️ press-releases endpoint'i symbol filtresini düzgün uygulamıyor — KULLANMA
  → FMP: upgrades-downgrades (portföy hisseleri, limit 20)
  → websearch: futures ve pre-market durumu
  → websearch: dün gece / bugün sabah önemli piyasa haberleri
  → websearch: portföy hisselerini etkileyen gelişmeler
  → websearch: Fed faiz olasılıkları (Kalshi/Polymarket)

ADIM 2.5 — TWİTTER TAKİP LİSTESİ (RapidAPI / twitter241)
  → aşağıdaki 10 hesabın son tweetlerini çek (her biri için 15-20 tweet)
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
    @VolSignals        → volatilite analizi / opsiyon stratejileri

  ÖNEMLİ: tweet verileri SADECE claude'un bağlamına (context) girer,
  rapora yazılmaz. tweet bilgileri yorumlanarak piyasa değerlendirmelerine,
  sektör analizine veya pozisyon yorumlarına yedirilerek kullanılır.

ADIM 3 — EARNINGS
  → FMP: earnings-calendar (bugün + 7 gün)
  → websearch: dün gece açıklanan earnings sonuçları (portföy/swing/majör)
  → websearch: bugünkü ekonomik veri takvimi

ADIM 4 — SWİNG TARAMA (FMP screener → ichimoku 4/4 → v2.3 filtreleri)
  ─────────────────────────────────────────────────────────
  → swing tarama seans içinde yapılır, otomatik script yok
  → detay: docs/SWING_SYSTEM_V2.md bölüm 9 (tarama evreni)

  TARAMA AKIŞI:
  1. FMP company-screener → ~1,100 hisse çek (mcap >$2B, vol >500K, price >$10, US)
  2. K-19: consumer defensive sektör hisselerini çıkar
  3. VIX kontrol:
     - VIX <22: normal mod → SPY > 21SMA + eğim ↗ kontrol → K-20 RS kontrol
     - VIX 22-35: K-13b kriz modu → sektör ETF 9+21 SMA kontrol
     - VIX >35: hiç giriş yapılmaz
  4. ichimoku 4/4 hesapla (kumo üstü + TK bull + tenkan üstü + volume 1.3x)
  5. 4/4 sinyal verenler için chandelier stop hesapla: giriş_fiyatı - 3×ATR(14)
  6. min stop mesafesi ≥%5 kontrol
  7. aday varsa: K-18 insider check, earnings tarihi check

  MEVCUT AKTİF POZİSYONLAR:
  → data/swing/active.json oku
  → her pozisyon için: chandelier stop güncelle (highest_high, ATR yeniden hesapla)
  → çıkış sinyali var mı? (chandelier stop tetiklendi, TK cross aşağı, kumo'ya giriş)

ADIM 5 — FİNVİZ TARAMA (teyit katmanı)
  → websearch: finviz screener — ADIM 4'teki adayları teyit et
  → finviz.com/quote.ashx?t=SEMBOL → pattern, float, short float
  → ADIM 4 listesinde olmayan ama finviz'de öne çıkan varsa ekle
  → temettü portföy adayları: docs/DIVIDEND_SYSTEM.md kriterlerine göre
  → sektör heatmap kontrolü: hangi sektörler güçlü/zayıf

ADIM 6 — ANALİZ, PLAN VE KAYIT
  → tüm verileri sentezle
  → SEKTÖR EXPOSURE TABLOSU: 3 portföy + swing toplam sektör dağılımı hesapla (docs/DECISION_FRAMEWORK.md bölüm 5)
  → PLAYBOOK ÇAPRAZ KONTROL: günün planındaki her aksiyonu docs/TRADING_PLAYBOOK.md kurallarıyla kontrol et
    - yeni giriş planlıyorsan: K-01 (makro veri), K-02 (kriz rallisi), K-03 (VIX+small cap), K-13 v4.1 (sektör bazlı VIX), K-17/K-18 (insider check)
    - çıkış planlıyorsan: K-06 (stop override), K-07 (trailing stop), K-08 (momentum), K-09 (stop yakın)
    - swing planlıyorsan: K-14 (ardışık zarar → dur), K-19 (XLP hariç), K-20 (RS dead cat bounce), ichimoku giriş sinyali veya trend devam girişi (4/4 bullish)
    - temel analiz: claude hisse bazında değerlendirir, sabit rasyo filtresi yok
    - kural ihlali varsa raporda açıkça belirt ve gerekçelendir
  → KARAR ÇERÇEVESİ: giriş planlarında GO/NO-GO 10 soru kontrol et (sinyal, stop, R:R, VIX, insider, earnings, korelasyon, nakit, plan, karşıt argüman)
    her giriş planı için düşünce zinciri yaz: (1) VERİ — somut veri (2) KURAL — hangi K/sistem sinyali (3) KARŞIT — neden yanlış olabilir
    detay: docs/DECISION_FRAMEWORK.md
  → SENTIMENT: CBOE put/call ratio (web search) + FMP grades-consensus (portföy hisseleri)
    put/call <0.7 = aşırı iyimser uyarı, >1.0 = aşırı kötümser (contrarian boğa), >1.2 = panik
  → raporu yaz (aşağıdaki format)
  → reports/daily/DAILY_SABAH_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[SABAH RAPORU] DD Ay YYYY - kısa özet"
  → TELEGRAM GÖNDERİMİ (git push'tan SONRA):
    1. python scripts/telegram_notify.py --type premarket --theme "[günün özeti]"
    2. python scripts/telegram_notify.py --type report --file reports/daily/DAILY_SABAH_YYYY-MM-DD.md
```

---

## RAPOR FORMATI (GITHUB'A GÖNDERİLİR)

rapor 6 bölümden oluşur.

---

### BÖLÜM 0: PİYASA İSTİHBARATI

```markdown
## 0. piyasa istihbaratı

### aktif temalar

| tema | güç skoru | değişim | neden |
|------|-----------|---------|-------|
| AI altyapı harcaması | X/10 | ↑/↓/→ | [kısa açıklama] |
| enerji güvenliği | X/10 | ↑/↓/→ | |
| savunma harcaması | X/10 | ↑/↓/→ | |
| faiz indirimi beklentisi | X/10 | ↑/↓/→ | |

### kritik haber → etki zinciri

1. **[haber başlığı]**
   - 1. derece: [direkt etki]
   - 2. derece: [tedarik zinciri etkisi]
   - 3. derece: [yan etkiler]
   - portföy aksiyonu: [ne yapılmalı]

### bu haftanın senaryoları

**[olay]** — olasılıklar:
- senaryo A (%XX): [sonuç → aksiyon]
- senaryo B (%XX): [sonuç → aksiyon]
- önceden pozisyonlama: [ne yapılmalı]

### tedarik zinciri katman durumu

ekipman: [güçlü/zayıf/nötr] | kimya: [...] | güç: [...] | optik: [...] | soğutma: [...]
```

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

### BÖLÜM 4: SWING TARAMA SONUÇLARI

```markdown
## 4. swing tarama — {tarih}

> VIX: XX.X | mod: [normal / K-13b / dur] | SPY: 21SMA [üstü/altı], eğim [↗/↘]
> tarama evreni: ~X,XXX hisse (FMP screener, mcap >$2B)

### ichimoku 4/4 sinyal verenler

| # | sembol | sektör | fiyat | ichimoku | volume | RSI | chandelier stop | mesafe | karar |
|---|--------|--------|-------|----------|--------|-----|-----------------|--------|-------|
| 1 | XXX | XLX | $XX.XX | 4/4 | X.Xx | XX | $XX.XX | X.X% | GİR/K-13b/ATLA |

**[SEMBOL] — detay:**
- sinyal: [kumo kırılımı / kijun bounce]
- ichimoku: fiyat $XX vs kumo $XX-$XX, tenkan/kijun
- chandelier stop: $XX.XX (highest_high - 3×ATR), mesafe: %X.X
- filtreler: K-19 [geçti/XLP], K-20 [geçti/dead cat bounce], SPY [üstü/altı]
- temel değerlendirme: [sektör bağlamı, hikaye, katalizör]

### mevcut swing pozisyonları

| sembol | PnL | chandelier stop | highest high | ATR | çıkış sinyali | durum |
|--------|-----|----------------|--------------|-----|----------------|-------|
| XXX | +X.X% | $XX.XX | $XX.XX | $X.XX | var/yok | [kısa yorum] |

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
- stop: $XX.XX (chandelier 3×ATR, -%X.X)
- ichimoku: [sinyal tipi, 4/4 detay]

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
- swing tarama seans içinde FMP screener'dan çekilir — docs/SWING_SYSTEM_V2.md bölüm 9
- VIX kuralı: K-13 v4.1 sektör bazlı — kriz tipine göre faydalanıcı sektörlere VIX 28'e kadar tam pozisyon, duyarlı sektörlere 22'den itibaren yarım. aktif kriz: jeopolitik/savaş. detay: docs/TRADING_PLAYBOOK.md
- EP adaylarında "ilk 30 dakika bekle, konfirmasyon al" kuralı seans promptunda uygulanır — sabah planına yaz

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
**RAPIDAPI KEY**: fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7
**RAPIDAPI HOST**: twitter241.p.rapidapi.com
