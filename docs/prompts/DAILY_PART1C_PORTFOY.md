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

> **versiyon**: 1.2 | **son güncelleme**: 9 nisan 2026 (K-kural referans `K_RULES_QUICK_REF.md`'ye bağlandı)
> **çıktı dosyası**: `reports/daily/DAILY_PORTFOY_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~09:00-14:00 (sabah raporundan SONRA, swing raporundan önce/sonra fark etmez)
> **amaç**: 3 portföy için fırsat taraması + karar matrisi + watchlist yönetimi
> **referans**: `docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md` (sistem detayı), `docs/K_RULES_QUICK_REF.md` (K-kural özet), `docs/TRADING_PLAYBOOK.md` (K-kural tam detay)
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
  script: scripts/portfolio_scan_balanced.py (portfolio_scan_common.py wrapper'ı)

  → aday evrenini belirle (3 kaynak birleştir):
    a. Mevcut watchlist.json'dan "dengeli" hedef portföylü adaylar
    b. FMP company-screener (geniş):
       marketCapMoreThan=5000000000, peRatioLessThan=25, peRatioMoreThan=5,
       betaLessThan=1.5, priceMoreThan=10, volumeMoreThan=500000, limit=100
    c. Mevcut dengeli pozisyonlarda olmayan sektörlerden 5-10 ticker (çeşitlilik)

  → tarama çalıştırma:
    python scripts/portfolio_scan_balanced.py SEMBOL1,SEMBOL2,...
    → wrapper otomatik mevcut sektörleri okur, çeşitlilik bonusu hesaplar
    → her aday için fundamentals + technical + skor + detay döner

  → skor kaynağı: scripts/portfolio_scan_common.py/score_dengeli
    P/E <15 +2, <25 +1
    ROIC >15% +3, >12% +2, >10% +1
    6M momentum >20% +3, >10% +2, >0% +1
    RSI 40-60 nötr +2
    SMA50 üstü +2
    Golden cross +1
    FCF yield >5% +2, >3% +1
    Yeni sektör (çeşitlilik) +2

  → eşik (8 nisan 2026 kalibre): skor <6 GEÇ, 6-8 İZLE, 9+ EKLE

  → NİTELİKSEL KATALİZÖR OVERRIDE (opsiyonel, sıkı kurallı):
    scripts/portfolio_scan_common.py apply_catalyst_override fonksiyonu
    kurallar: max +2 puan, gerekçe ≥20 karakter, kaynak (URL/SEC/haber) zorunlu,
    katalizör son 7 gün içinde. Geçersiz override sessizce reddedilir.
    kullanım: catalyst_override={'puan':2, 'gerekce':'...', 'kaynak':'Reuters 2026-04-07'}

ADIM 4 — AGRESİF PORTFÖY TARAMASI
  detay: docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 2b
  script: scripts/portfolio_scan_aggressive.py

  → aday evrenini belirle:
    a. Mevcut watchlist.json'dan "agresif" hedef portföylü adaylar
    b. AI tedarik zinciri öncelik listesi (her zaman tara):
       ekipman: ASML, AMAT, LRCX, KLAC, CAMT, ONTO, TER, UCTT
       kimya: ENTG, MKSI, PLAB, LIN, APD, MP, FCX
       optik: COHR, LITE, GLW, AAOI, FN, ANET
       güç: POWL, VRT, ETN, PWR, HUBB
       veri merkezi: DLR, EQIX
       mobil/edge: QCOM, AVGO, MRVL, CRDO
       memory: MU, SNDK, WDC, STX
       chip AI: NVDA, AMD, TSM, TXN
    c. FMP company-screener (geniş büyüme):
       marketCapMoreThan=10000000000, priceMoreThan=20,
       volumeMoreThan=1000000, betaMoreThan=0.8, limit=150

  → tarama çalıştırma:
    python scripts/portfolio_scan_aggressive.py SEMBOL1,SEMBOL2,...
    → wrapper otomatik skor + karar döner

  → skor kaynağı: score_agresif (portfolio_scan_common.py)
    1M momentum >20% +3, >10% +2, >0% +1
    6M momentum >50% +3, >30% +2, >15% +1
    P/E quality guard: <0 -3, >80 -3, >60 -2, >40 -1
    ROIC >25% +3, >15% +2, >10% +1, <0% -3, <8% -1
    RSI 50-70 güçlü +2, 40-50 nötr +1, >75 aşırı alım -1
    SMA50 üstü +2, golden cross +2
    3M >15% +2

  → eşik (8 nisan 2026 kalibre): skor <10 GEÇ, 10-13 İZLE, 14+ EKLE

ADIM 5 — TEMETTÜ PORTFÖY TARAMASI
  detay: docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 2c
  script: scripts/portfolio_scan_dividend.py

  → aday evrenini belirle:
    a. Mevcut watchlist.json'dan "temettü" hedef portföylü adaylar
    b. FMP company-screener:
       marketCapMoreThan=5000000000, peRatioLessThan=20, peRatioMoreThan=5,
       dividendMoreThan=0.03, betaLessThan=1.2, priceMoreThan=10, limit=150
    c. Mevcut temettü portföyünde olmayan sektörlerden 5-10 ticker (çeşitlilik)

  → tarama çalıştırma:
    python scripts/portfolio_scan_dividend.py SEMBOL1,SEMBOL2,...

  → skor kaynağı: score_temettü
    yield 5-7% +3, 4-5% +2, 3-4% +1, >8% -2 (yield trap uyarı)
    payout <50% +3, <65% +2, <75% +1, >100% -5 (YIELD TRAP)
    P/E <12 +3, <15 +2, <18 +1, <0 -3
    ROIC >15% +2, >10% +1
    FCF yield >5% +2, >0 +1, <0 -2
    SMA50 üstü +1, SMA200 üstü +1
    Yeni sektör (çeşitlilik) +2

  → eşik (8 nisan 2026 kalibre): skor <6 GEÇ, 6-8 İZLE, 9+ EKLE
  → KRİTİK: payout >100% yield trap = otomatik -5 puan, rapora "YIELD TRAP" notu ekle

ADIM 6 — ORTAK FİLTRELER (TÜM 3 PORTFÖY ADAYLARINA)
  her aday yukarıdaki portföy spesifik skoru aldıktan sonra ortak filtreler uygulanır.
  birini geçemeyen TAMAMEN ELENİR.

  1. K-04 SMA50 trend filtresi:
     - fiyat > SMA50 → ✅
     - fiyat < SMA50 ama RSI <30 oversold bounce → istisna, +1 gün teyit
     - fiyat < SMA50 ve RSI >30 → ❌

  2. K-05 earnings proximity:
     - 2+ işlem günü içinde earnings varsa → ❌ (binary gap riski, playbook ile uyumlu)
     - not: PART 1B swing ile aynı eşik (2 gün). PEAD (post-earnings drift) girişleri K-16 ile yönetilir

  3. K-17 korelasyon kontrolü:
     - sektör mevcut portföyde K-12 limitini aşıyorsa → ❌
       • dengeli: >%25 → ❌
       • agresif: >%20 → ❌
       • temettü: >%15 → ❌
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
  script: scripts/watchlist_manager.py (CRUD + cooldown + otomatik eleme)
  4 kontrol her gün uygulanır:

  8a. yeniden skorlama (refresh):
    python scripts/watchlist_manager.py refresh
    → tüm mevcut adaylar için fiyat + RSI + skor + karar yeniden hesaplanır
    → bekleme_gun +1, son_kontrol güncellenir
    → skor veya karar değişenler raporda vurgulanır

  8b. seviyeye ulaşma:
    - watchlist adayı için fiyat hedef_giris bandı içinde mi?
    - evetse → BÖLÜM 5 giriş planına taşı, urgency = "entry_active"
    - K-04 teyit (SMA50 üstü) gerekli

  8c. otomatik eleme (cleanup):
    python scripts/watchlist_manager.py cleanup
    → kural 1: bekleme_gun >14 + karar GEÇ → sil
    → kural 2: karar GEÇ + skor < İZLE eşiğinin %70'i → sil
    → kural 3: bekleme_gun >14 + momentum bozuk (RSI<40, SMA50 altı) → sil
    → son_kontrol >14g eski olanlar "eski" etiketi (elle kontrol gerekli)

  8d. cool-down kontrolü (yeni ekleme öncesi):
    python scripts/watchlist_manager.py cooldown
    → kapanmış swing trade'lerin satış tarihi üstünden kaç gün geçti?
    → 7 gün içinde tekrar ekleme YASAK (trade tekrar hatası önleme)

  8e. yeni aday ekleme:
    bu sabah taramadan çıkan EKLE/İZLE adayları → watchlist'e ekle:
    python scripts/watchlist_manager.py add SEMBOL --portfoy dengeli|agresif|temettü
    → otomatik cool-down kontrolü, duplicate kontrolü, mekanik skor hesaplama
    → skor düşükse reddeder (--force ile override mümkün)

  → data/watchlist.json otomatik güncellenir (manuel JSON dokunma YASAK)
  → detay şema: docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md bölüm 7

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
