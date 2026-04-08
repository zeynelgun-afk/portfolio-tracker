# GÜNLÜK RAPOR PART 1C — PORTFÖY FIRSAT TARAMASI v1.0

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt 3 portföy (dengeli, agresif, temettü) için sistematik fırsat tarama ve watchlist yönetimi yapar. her adım sırayla uygulanmalıdır.
>
> **ön koşul**: aynı gün içinde PART 1 çalıştırılmış ve `DAILY_SABAH_YYYY-MM-DD.md` üretilmiş olmalıdır. yoksa DUR ve kullanıcıya uyar.
>
> **referans**: `docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md` (sistem detayı, kriterler, skorlama, karar matrisi)
>
> **zorunlu adımlar (teker teker kontrol et):**
> - [ ] ADIM 0 — sabah raporunu oku (makro, VIX, trend, senaryolar)
> - [ ] ADIM 1 — mevcut portföyleri ve watchlist'i oku
> - [ ] ADIM 2 — mevcut pozisyonlar için BÜYÜT/DÖNDÜR değerlendirmesi
> - [ ] ADIM 3 — dengeli portföy taraması (FMP screener + filtreler + skor)
> - [ ] ADIM 4 — agresif portföy taraması
> - [ ] ADIM 5 — temettü portföy taraması
> - [ ] ADIM 6 — ortak filtreler (K-04, K-05, K-17, K-18, K-20) tüm adaylara
> - [ ] ADIM 7 — karar matrisi uygula (EKLE/BÜYÜT/DÖNDÜR/İZLE/GEÇ)
> - [ ] ADIM 8 — watchlist mekanik yönetimi (seviye, eleme, yeni ekleme)
> - [ ] ADIM 9 — rapor yaz + watchlist.json güncelle + git push
>
> **geçmiş hatalar**: 
> - portföy fırsatları "havada kalmış belirsiz" eleştirisi (8 nisan 2026) — sistematik karar matrisi olmaması
> - watchlist'te aday sübjektif tutuluyordu (örn. QCOM "CRITICAL" ama mekanik skor düşük)
> - mevcut pozisyonların büyütme/döndürme kararları hiç yapılmıyordu
> bu prompt bu eksikleri kapatır

> **versiyon**: 1.0 | **son güncelleme**: 8 nisan 2026
> **çıktı dosyası**: `reports/daily/DAILY_PORTFOY_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~09:00-14:00 (sabah raporundan SONRA, swing raporundan önce/sonra fark etmez)
> **amaç**: 3 portföy için fırsat taraması + karar matrisi + watchlist yönetimi
> **referans**: `docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md`
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[PORTFÖY RAPORU] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~09:00-14:00 arası yazılır, sabah raporundan sonra
- FMP fiyatları = dünün kapanışı
- watchlist seviye kontrolü için dünün kapanış fiyatları kullanılır

---

## ÇALIŞMA AKIŞI

```
ADIM 0 — SABAH RAPORUNU OKU
  → reports/daily/DAILY_SABAH_YYYY-MM-DD.md dosyasını ara
  → yoksa DUR: "sabah raporu (PART 1) çalıştırılmadan portföy taramasına geçilemez"
  → varsa oku ve şu bilgileri al:
    - VIX seviyesi ve K-13 aktif bandı
    - SPY/QQQ trend (SMA50 üstü/altı)
    - aktif tema listesi (AI tedarik zinciri katmanları, savunma, enerji vb.)
    - günün makro riski (binary olay, FOMC, earnings)
    - sabah raporunda işaretlenen "fırsat" notları
  → bu çerçeveyi akılda tutarak tarama kararını ayarla

ADIM 1 — MEVCUT PORTFÖYLERİ VE WATCHLİST'İ OKU
  → data/portfolios/balanced.json oku
  → data/portfolios/aggressive.json oku
  → data/portfolios/dividend.json oku
  → data/watchlist.json oku
  → her portföy için hesapla:
    - boş slot = limit - mevcut pozisyon
    - nakit miktarı + nakit oranı
    - sektör dağılımı (K-12 limit kontrolü için)
    - mevcut pozisyonların ortalama ağırlığı
  → watchlist'i kategorile:
    - "izleme_listesi": aktif izlenen adaylar
    - "haric_tutulanlar": elenmiş, 30 gün cool-down

ADIM 2 — MEVCUT POZİSYONLAR İÇİN BÜYÜT/DÖNDÜR DEĞERLENDİRMESİ
  her mevcut pozisyon için sırayla kontrol et:

  → BÜYÜT kontrolü:
    - kazançta mı? (k/z >%5)
    - SMA50 üstünde mi?
    - RSI 50-75 arası mı? (kâr al bölgesinde değil)
    - K-12 büyütme sonrası limit aşmıyor mu?
    - yeni pozitif katalizör var mı? (haber, earnings beat, sektör güç)
    - mevcut ağırlık hedef ağırlığın altında mı?
    → 5+ evet ise: BÜYÜT aday (rapora yaz, miktar belirt)

  → DÖNDÜR kontrolü:
    - k/z <%-5 (kayıpta) VEYA
    - RSI <40 + SMA50 altı + son 1 ay RS rank <20 (momentum bozulmuş) VEYA
    - K-04 trend filtresini 3+ iş günü kaybetmiş
    - tez bozuldu mu? (downgrade, miss, sektör zayıflığı)
    → koşulları karşılıyor ise: DÖNDÜR aday (yerine geçecek hisse aşağıda taranacak)

  ⚠️ DÖNDÜR günde max 1 defa uygulanır — overtrading koruması

ADIM 3 — DENGELİ PORTFÖY TARAMASI
  detay: docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 2a

  → FMP company-screener:
    marketCapMoreThan=5000000000
    priceMoreThan=10
    volumeMoreThan=500000
    country=US
    peRatioLessThan=25
    peRatioMoreThan=5
    betaLessThan=1.5
    limit=200

  → portföy spesifik filtre:
    1. ROIC >%10 (FMP key-metrics-ttm)
    2. 6 aylık fiyat momentum >%0
    3. SMA50 üstü
    4. EPS büyümesi son 3 yıl pozitif
    5. debt/equity <2
    6. sektör çeşitliliği (mevcut portföyde olmayan sektörler önce)

  → her geçen aday için skor hesapla (0-15+):
    ROIC >%15: +3, >%12: +2, >%10: +1
    6M momentum >%20: +3, >%10: +2, >%0: +1
    RSI 40-60 nötr: +2
    P/E <15: +2, <20: +1
    sektör mevcut portföyde değil: +2
    5Y EPS büyümesi >%10: +2

  → eşik: skor <8 GEÇ, 8-11 İZLE, 12+ EKLE

ADIM 4 — AGRESİF PORTFÖY TARAMASI
  detay: docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 2b

  → FMP company-screener:
    marketCapMoreThan=10000000000
    priceMoreThan=20
    volumeMoreThan=1000000
    country=US
    betaMoreThan=0.8
    limit=300

  → portföy spesifik filtre:
    1. son çeyrek EPS surprise >%10 (FMP earnings-surprises)
    2. RS rank >80 (6M getiri SPY'yi en az %15 geçmiş)
    3. ortalama hacim oranı >1.5x (10g / 50g hacim)
    4. SMA50 üstü
    5. RSI 40-75
    6. 52W high'a %15 mesafe içinde

  → AI tedarik zinciri öncelik listesi (önce bu listedekiler değerlendirilir):
    ekipman: ASML, AMAT, LRCX, KLAC, CAMT, ONTO, TER, UCTT, ACLS
    kimya: ENTG, MKSI, PLAB, LIN, APD, CCMP, MP, FCX
    optik: COHR, LITE, GLW, AAOI, FN, ANET
    güç: POWL, VRT, ETN, PWR, EME
    soğutma: VRT, TT, JCI
    veri merkezi: DLR, EQIX
    enerji destek: COP, XOM
    mobil/edge: QCOM, AVGO
    memory: MU, SNDK, WDC

  → skor (0-18+):
    EPS surprise >%20: +4, >%15: +3, >%10: +2
    RS rank >90: +3, >85: +2, >80: +1
    hacim oranı >2x: +3, >1.5x: +2, >1.2x: +1
    AI tedarik zinciri katmanı: +3 doğrudan, +1 dolaylı
    analyst "Strong Buy": +2, "Buy": +1
    6M getiri >%50: +3, >%30: +2, >%15: +1

  → eşik: skor <10 GEÇ, 10-13 İZLE, 14+ EKLE

ADIM 5 — TEMETTÜ PORTFÖY TARAMASI
  detay: docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 2c

  → FMP company-screener:
    marketCapMoreThan=5000000000
    priceMoreThan=10
    volumeMoreThan=300000
    country=US
    peRatioLessThan=20
    peRatioMoreThan=5
    dividendMoreThan=0.03
    betaLessThan=1.2
    limit=200

  → portföy spesifik filtre:
    1. yield %3-8 (yield trap üstünü ele)
    2. payout ratio <%75 (FMP ratios-ttm)
    3. debt/equity <1.5
    4. son 3 yıl operating cash flow pozitif (FMP cash-flow-statement)
    5. 5+ yıl temettü artış geçmişi (FMP stock-dividend)
    6. P/E <20
    7. SMA200 üstü VEYA RSI <40

  → skor (0-16+):
    yield %5-7: +3, %4-5: +2, %3-4: +1
    payout ratio <%50: +3, <%65: +2, <%75: +1
    10+ yıl temettü artışı: +3, 5-10 yıl: +2
    P/E <12: +3, <15: +2, <18: +1
    FCF büyümesi 3Y pozitif: +2
    sektör defensive (XLU/XLP/XLV/Tobacco): +2

  → eşik: skor <9 GEÇ, 9-12 İZLE, 13+ EKLE

ADIM 6 — ORTAK FİLTRELER (TÜM 3 PORTFÖY ADAYLARINA)
  her aday yukarıdaki portföy spesifik skoru aldıktan sonra ortak filtreler uygulanır.
  birini geçemeyen TAMAMEN ELENİR.

  1. K-04 SMA50 trend filtresi:
     - fiyat > SMA50 → ✅
     - fiyat < SMA50 ama RSI <30 oversold bounce → istisna, +1 gün teyit
     - fiyat < SMA50 ve RSI >30 → ❌

  2. K-05 earnings proximity:
     - 7 gün içinde earnings varsa → ❌ (binary gap riski)

  3. K-17 korelasyon kontrolü:
     - sektör mevcut portföyde >%25 ise → ❌
     - aynı tema 2+ pozisyon varsa yeni eleme
     - script: scripts/k17_correlation_check.py SYMBOL

  4. K-18 insider trading:
     - son 30 gün senior sell >$5M → ❌
     - script: scripts/k18_insider_check.py SYMBOL

  5. K-20 RS dead cat bounce (sadece agresif için zorunlu, dengeli/temettü için öneri):
     - 1 ay SPY'den %10+ geride + son 5 gün +%5 yukarı → ❌ (agresif)

ADIM 7 — KARAR MATRİSİ UYGULA
  her aday için 5 karardan biri verilir:

  EKLE: yeni pozisyon, watchlist'e + giriş planına
  BÜYÜT: mevcut pozisyonu artır (ADIM 2'den çıkan)
  DÖNDÜR: zayıf pozisyonu yeni adaya transfer (ADIM 2'den çıkan)
  İZLE: watchlist'te tut, urgency belirle
  GEÇ: ele, haric_tutulanlar listesine

  → karar matrisi detayı: docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 4

ADIM 8 — WATCHLİST MEKANİK YÖNETİMİ
  4 kontrol her gün uygulanır:

  8a. seviyeye ulaşma:
    - watchlist adayı için fiyat hedef_giris bandı içinde mi?
    - evetse → BÖLÜM 5 giriş planına taşı, urgency = "entry_active"
    - K-04 teyit (SMA50 üstü) gerekli

  8b. momentum bozulma:
    - aday son 5 gün SPY'den %5+ geride mi?
    - VE RSI <35 mi? → K-04 istisnası değerlendir
    - VE 14+ gün watchlist'te mi? → otomatik elenme

  8c. yeni aday ekleme:
    - bu sabah taramadan çıkan EKLE/İZLE adayları → watchlist'e ekle
    - duplicate kontrol: zaten varsa skoru güncelle

  8d. eleme (çöp toplama):
    - 14 gün hedef altında + momentum bozuk → elenme
    - fundamental katalist bozuldu (downgrade, miss, SEC) → elenme
    - portföyde zaten var → büyütme kararı ayrı yürütülür

  → data/watchlist.json güncelle (genişletilmiş şema, bkz. PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 7)

ADIM 9 — RAPOR YAZ + GIT PUSH
  → rapor yaz (aşağıdaki format)
  → reports/daily/DAILY_PORTFOY_YYYY-MM-DD.md olarak kaydet
  → data/watchlist.json güncelle ve commit'e dahil et
  → GIT COMMIT + PUSH: "[PORTFÖY RAPORU] DD Ay YYYY - kısa özet"
  → TELEGRAM (yeni EKLE/BÜYÜT/DÖNDÜR varsa):
    python scripts/telegram_notify.py --type alert --theme "portföy aday: ..."
```

---

## RAPOR FORMATI

```markdown
# günlük portföy fırsat raporu — {tarih}, {gün}

> finzora ai | sabah raporu okundu | VIX: XX.X | K-14: [aktif/pasif]

---

## 1. mevcut pozisyon değerlendirmesi

### 1a. büyütme adayları (BÜYÜT)

| portföy | sembol | mevcut k/z | RSI | SMA50 | yeni katalizör | öneri | miktar |
|---------|--------|-----------:|----:|:-----:|----------------|-------|--------|
| dengeli | XXX | +%X.X | XX | ✅ | [haber] | BÜYÜT | +$X,XXX |

### 1b. döndürme adayları (DÖNDÜR)

| portföy | satılacak | k/z | sebep | yerine | beklenen iyileşme |
|---------|-----------|----:|-------|--------|-------------------|
| agresif | YYY | -%X.X | RSI 32, SMA50 altı 5g | [yeni aday] | +%XX |

> DÖNDÜR günde max 1 uygulanır.

### 1c. mevcut pozisyon özet (sadece sağlık)

| portföy | toplam | k/z | pozisyon sayısı | sağlık |
|---------|-------:|----:|:---------------:|--------|
| dengeli | $XXX,XXX | ±%X.X | X/6 | [sağlıklı/dikkat/sorun] |
| agresif | $XXX,XXX | ±%X.X | X/10 | |
| temettü | $XXX,XXX | ±%X.X | X/15 | |

---

## 2. dengeli portföy fırsat taraması

### tarama sonuç özeti
- evren: ~XXX hisse (FMP screener filtresi sonrası)
- portföy spesifik filtre geçen: XX
- ortak filtreler (K-04/K-05/K-17/K-18) geçen: X
- minimum skor (8) geçen: X
- nihai aday: X

### nihai adaylar

| # | sembol | sektör | fiyat | RSI | P/E | ROIC | 6M | skor | hedef giriş | stop | hedef | R:R | karar |
|---|--------|--------|-------|-----|-----|------|----|------|-------------|------|-------|-----|-------|

**[SEMBOL]** — [kısa başlık]
- skor detay: [her puan kalemi]
- tez: [1-2 cümle]
- karşıt argüman: [1-2 cümle]
- karar: EKLE / BÜYÜT / İZLE / GEÇ

---

## 3. agresif portföy fırsat taraması

### tarama sonuç özeti
- evren: ~XXX hisse
- AI tedarik zinciri öncelik listesinden: X aday
- portföy spesifik filtre geçen: XX
- ortak filtreler geçen: X
- minimum skor (10) geçen: X
- nihai aday: X

### nihai adaylar

| # | sembol | sektör | tema | fiyat | RSI | EPS surprise | RS rank | hacim | skor | giriş | stop | hedef | R:R | karar |
|---|--------|--------|------|-------|-----|-------------:|--------:|-------|------|-------|------|-------|-----|-------|

**[SEMBOL]** — detay (yukarıdaki format)

---

## 4. temettü portföy fırsat taraması

### tarama sonuç özeti
- evren: ~XXX hisse
- portföy spesifik filtre geçen: XX
- ortak filtreler geçen: X
- minimum skor (9) geçen: X
- nihai aday: X

### nihai adaylar

| # | sembol | sektör | fiyat | yield | P/E | payout | D/E | temettü artış yıl | skor | karar |
|---|--------|--------|-------|------:|----:|-------:|----:|------------------:|------|-------|

**[SEMBOL]** — detay

---

## 5. watchlist güncellemesi

### 5a. seviyeye ulaşan adaylar (entry_active → giriş planı)

| sembol | portföy | aktif giriş bandı | son fiyat | aksiyon |
|--------|---------|-------------------|-----------|---------|

### 5b. yeni eklenen adaylar (bu sabah taramadan)

| sembol | portföy | sektör | skor | urgency | hedef giriş |
|--------|---------|--------|------|---------|-------------|

### 5c. elenen adaylar

| sembol | portföy | sebep | önceki bekleme gün |
|--------|---------|-------|--------------------|

### 5d. mevcut watchlist toplam

dengeli: X | agresif: X | temettü: X | toplam: XX adaylık watchlist
hariç tutulanlar: X (30 gün cool-down)

---

## 6. bugün için aksiyon planı

### 🔴 hemen (seans açılışında)

1. **BÜYÜT**: [SEMBOL] +$X,XXX — [neden] — [hangi portföy]
2. **DÖNDÜR**: [eski] → [yeni] — [neden]
3. **EKLE**: [SEMBOL] $X,XXX — [hangi portföy]

### 🟡 izle (seans içinde)

4. [SEMBOL] $XX.XX kırarsa → giriş onayı

### 🟢 pasif (seviye bekle)

5. [SEMBOL] $XX.XX'a düşerse → değerlendir

---

## 7. karşıt argüman özeti

her EKLE/BÜYÜT/DÖNDÜR kararı için "neden yanlış olabilirim":
- [SEMBOL]: [karşıt argüman]
- [SEMBOL]: [karşıt argüman]

---

*finzora ai | fmp screener + portfolio_opportunity_system v1.0 | sabah raporu bağlantılı*
```

---

## KURALLAR

- rapor github'a push edilir (`reports/daily/DAILY_PORTFOY_YYYY-MM-DD.md`)
- `data/watchlist.json` dosyası bu prompt tarafından güncellenir, başka prompt dokunmaz
- portföy JSON'larına bu prompt DOKUNMAZ — sadece okur (gerçek alım/satım PART 2 / SESSION promptunda)
- ön koşul: aynı gün sabah raporu (PART 1) üretilmiş olmalı
- karar matrisi mekanik uygulanır — sübjektif "feeling" yok
- her aday için 4 unsur zorunlu: tez, karşıt argüman, skor detayı, R:R
- DÖNDÜR günde max 1 uygulama (overtrading koruması)
- BÜYÜT için K-12 konsantrasyon limiti zorunlu
- 14 gün watchlist + momentum bozuk = otomatik eleme
- detay sistem: `docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md`

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
