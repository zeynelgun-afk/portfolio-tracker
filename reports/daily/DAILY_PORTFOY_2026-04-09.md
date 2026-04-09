# GÜNLÜK PORTFÖY FIRSAT RAPORU — 9 NİSAN 2026, PERŞEMBE

> finzora ai | sabah raporu okundu (DAILY_SABAH_2026-04-09.md) | swing raporu okundu (K-14 kaldırıldı, yarım pozisyon protokolü) | VIX: 20.18 (K-13 sakin) | toplam nakit: $537K (%87.5)

---

## 1. mevcut pozisyon değerlendirmesi

### 1a. büyütme adayları (BÜYÜT)

mevcut 6 pozisyon değerlendirildi. skor + teknik + katalizör kombinasyonuna göre:

| portföy | sembol | mevcut k/z | RSI | SMA50 | mekanik skor | katalizör | öneri | miktar |
|---------|--------|-----------:|----:|:-----:|:--:|----------------|-------|--------|
| dengeli | MO | -0.95% | 55 | ✅ | 12 EKLE | defansif, K-12 aşım ⚠️ | **HAYIR** | — |
| dengeli | JNJ | -1.16% | 52 | ✅ | 12 EKLE | 14 nis earnings binary | **HAYIR** | — |
| temettü | T | +4.55% | 41 | ❌ | 11 EKLE ama K-04 başarısız | SpaceX baskısı | **HAYIR** | — |
| temettü | VZ | +20.61% | 37 | ❌ | 10 EKLE ama K-04 başarısız | DBS hold, SpaceX | **HAYIR** | — |
| temettü | MO | +16.56% | 55 | ✅ | 5 GEÇ (YIELD TRAP) | payout %100.2 | **HAYIR** | — |
| temettü | MRK | +2.67% | 64 | ✅ | 9 EKLE | sessiz güç | İZLE (RSI sınırda) | — |

**BÜYÜT kararı: YOK**. gerekçeler sırasıyla:
- MO (dengeli): mekanik skor EKLE ama K-12 tütün sektör limit aşımı (%49 vs %40 limit)
- JNJ: 5 iş günü içinde earnings (14 nisan), K-05 binary gap riski
- T: K-04 SMA50 altı filtresi başarısız (RSI 41, oversold istisna kapısı kapalı)
- VZ: K-04 SMA50 altı filtresi başarısız, DBS hold 1 gün önceydi
- MO (temettü): skor GEÇ (payout %100 yield trap cezası -5)
- MRK: RSI 64 üst sınır, K-11 tetik bölgesine girmek üzere

### 1b. döndürme adayları (DÖNDÜR)

**DÖNDÜR aday 1: MO (temettü portföy)**

| alan | detay |
|------|-------|
| satılacak | MO (temettü) — 218 pay, $14,562 |
| mevcut k/z | +%16.56 (tetikleyici hedef değil, rotasyon gerekçesi) |
| sebep 1 | **K-12 sektör limit aşımı**: MO iki portföyde (dengeli + temettü) → toplam tütün exposure $32,392, invested capital'ın %42'si, limit %40 |
| sebep 2 | **yield trap mekanik ceza**: payout ratio %100.2, dividend sürdürülebilirlik riski |
| sebep 3 | mekanik skor GEÇ (5, eşik İZLE≥6 altı) |
| yerine | **BMY** (Bristol-Myers) veya **KMB** (Kimberly-Clark) — temettü İZLE listesinde skor 8 |

**alternatif: tam satış yerine küçültme (trim)**
MO temettü pozisyonunu %50 küçült (109 pay → 109 pay sat $7,281 serbest bırak). tütün exposure toplam %42 → %34 iner. K-12 uyumu sağlanır. nakit bekler veya başka temettü adayına rotasyon yapar.

**karar**: **DÖNDÜR-TRİM önerisi** — bugün fiziki uygulama değil, session promptunda icra edilir. trim %50 (partial sell) + nakit tutma veya BMY/KMB rotasyon.

**neden DÖNDÜR değil TRIM?**
- MO teknik olarak sağlıklı (RSI 55, SMA50/200 üstü, trend up)
- "kayıpta" değil — +%16.56 kârda
- Tek sorun K-12 sektör konsantrasyonu + yield trap ceza
- Tamamen satmak fundamentaller haklı değil

**DÖNDÜR aday 2: T veya VZ (reddedildi)**

sabah raporunda "T/VZ tez zayıflıyor" notu vardı, ancak:

| kriter | T | VZ |
|--------|---|-----|
| mekanik skor | 11 EKLE | 10 EKLE |
| P/E | 9.0 (çok ucuz) | 11.8 (ucuz) |
| yield | 4.06% | 5.69% |
| payout | 37.4% (sağlıklı) | 66.9% (orta) |
| FCF yield | 10.2% (güçlü) | 9.8% (güçlü) |
| ROIC | 5.4% (düşük) | 6.2% (düşük) |
| k/z | +%4.55 | +%20.61 |
| RS 1M | -%0.6 | -%4.8 |
| SMA50 | altı ❌ | altı ❌ |
| SMA200 | üstü ✅ | üstü ✅ |
| katalizör | SpaceX direct-to-cell (-), DBS hold (-) | SpaceX (-), DBS hold (-) |

**DÖNDÜR kriter testi**:
- k/z <-5%? ❌ (ikisi de kârda)
- RSI<40 + SMA50 altı + RS rank <20 momentum bozulmuş? kısmi — T RSI 41 (sınır), VZ RSI 37 ✅; RS 1M -%4.8 (VZ) zayıf ama -%20 değil
- K-04 trend filtresini 3+ iş günü kaybetmiş? **evet** — her ikisi de SMA50 altında (kaç gündür olduğu belirsiz, veriye göre T son 1 haftadır, VZ 2 haftadır)
- tez bozuldu mu? **kısmi** — SpaceX yapısal ama tek haber, DBS hold 1 kurum, consensus değişmedi

**karar**: **DÖNDÜR edilmez** — hem mekanik skor EKLE seviyesinde hem de kâr pozisyonunda. onay yanlılığı önleme kuralı gereği tek haber (SpaceX) ile tez bozdurmak recency bias. **İZLE + yeni ekleme yok**. K-04 başarısız olduğu sürece yeni alım yapılmaz. SMA50 altında kalmaya devam ederse haftalık kontrolle DÖNDÜR yeniden değerlendirilir.

**ancak**: DÖNDÜR günde max 1 — MO trim ile bugünkü rotasyon kotası dolmuş oluyor.

### 1c. mevcut pozisyon özet (sağlık)

| portföy | toplam değer | getiri | pozisyon | sağlık |
|---------|-------:|----:|:---:|--------|
| dengeli | $112,514 | +%12.51 | 2/6 | **dikkat** (JNJ earnings 14 nis + MO sektör aşım) |
| agresif | $357,823 | -%10.54 | 0/10 | **underdeployed** (K-14 kalktı, deployment penceresi açık) |
| temettü | $143,888 | +%43.89* | 4/15 | **dikkat** (T/VZ K-04 başarısız, MO yield trap) |

*temettü %43.89 rakamı muhtemelen veri bütünlüğü sorunu, session promptunda doğrulanmalı.

**nakit durumu**: toplam $537,312 nakit / $614,225 toplam = **%87.5 cash**. uzun süren underdeployment. K-14 kalkışı + ceasefire rejim değişikliği + VIX<22 kombinasyonu re-deployment penceresini açıyor.

---

## 2. dengeli portföy fırsat taraması

### tarama özeti
- evren: 10 manuel seçim aday (CAT, DUK, NEE, GEV, ATMU, LMT, RSG, WM, ADP, BRK.B) + sektör çeşitlilik bonusu (Industrial mevcut portföyde yok)
- tarama kaynağı: `scripts/portfolio_scan_balanced.py`
- eşik: skor <6 GEÇ, 6-8 İZLE, 9+ EKLE

### nihai adaylar

| # | sembol | sektör | fiyat | RSI | P/E | ROIC | 6M | skor | karar |
|---|--------|--------|-------|----:|----:|-----:|----|-----:|-------|
| 1 | ATMU | Industrial | $63.13 | 62 | 24.8 | 23.0% | +42.4% | **12** | **EKLE** |
| 2 | LMT | Industrial | $628.50 | 50 | 28.9 | 17.4% | +23.8% | **12** | **EKLE** |
| 3 | DUK | Utility | $131.60 | 57 | — | — | — | **11** | **EKLE** |
| 4 | CAT | Industrial | $771.58 | 64 | — | — | — | **9** | **EKLE** |
| 5 | GEV | Industrial | $936.07 | 63 | — | — | — | 8 | İZLE |
| 6 | ADP | Technology | $200.78 | 37 | 19.1 | 24.0% | -29.8% | 8 | İZLE |
| 7 | NEE | Utility | $94.17 | 60 | — | — | — | 7 | İZLE |
| 8 | WM | Industrial | $231.43 | 48 | 34.4 | 8.9% | +6.4% | 7 | İZLE |
| 9 | RSG | Industrial | $216.51 | 42 | 31.3 | 8.8% | -2.3% | 5 | GEÇ |

### ortak filtre uygulaması (K-04, K-05, K-17, K-18, K-20)

| sembol | K-04 | K-05 | K-17 | K-18 | K-20 | day-2 chase | nihai karar |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|--------|
| ATMU | ✅ | ✅ | ✅ | ? | ✅ | ✅ (+%4.55 ölçülü) | **EKLE** |
| LMT | ✅ | ✅ | ✅ | ? | ✅ | ? | **EKLE** |
| DUK | ✅ | ✅ | ✅ | ? | ✅ | ✅ (-%0.17 sessiz) | **EKLE** |
| CAT | ✅ | ✅ | ✅ | ? | ✅ | ⚠️ (+%6.51 chase) | EKLE-koşullu |
| GEV | ✅ | ❌ 13g | ✅ | ? | ✅ | — | İZLE (earnings 22 nis) |

### tez ve karşıt argümanlar

**ATMU — atmus filtration** (skor 12 EKLE)
- **tez**: filter sektörü defansif-büyüme karışımı, ROIC %23 yüksek kalite, 6M +%42 güçlü momentum, RSI 62 sağlıklı. dengeli portföyde Industrial sektörü yok, çeşitlilik bonusu. day-1 chase düşük (+%4.55).
- **skor detay**: P/E <25 +1, ROIC 23% +3, 6M 42% +3, SMA50 üstü +2, golden cross +1, yeni sektör +2 = 12
- **karşıt argüman**: ATMU küçük-orta cap, likidite 500K volume sınırında, ani baskılarda geniş slippage riski. 6M +%42 sonrası pullback olasılığı var.
- **karar**: **EKLE** — dengeli portföy çeşitlilik için ideal. başlangıç pozisyonu $8-10K (toplam portföy %8-10).

**LMT — lockheed martin** (skor 12 EKLE)
- **tez**: defense prime, ROIC %17 kaliteli, FCF yield %4.8, 6M +%24 sağlıklı momentum. ceasefire savunma primini eritmiş olsa da LMT uzun vadeli sözleşmelere dayalı, kısa vadeli haber etkisi sınırlı. nadir P/E <30 defense.
- **karşıt argüman**: ceasefire uzun sürerse savunma harcaması teması soğur, 6-12 ay yavaş büyüme. yeni başlayan "defense rotation out" trendi başlangıç aşamasında.
- **day-2 chase durumu**: LMT verisi net değil ama defense sektörü genel olarak ceasefire günü zayıftı. giriş zamanlaması uygun olabilir.
- **karar**: **EKLE** — ancak day-1 gainer listesinde değil, seviye tetiği kullan. $620 altı giriş ideal. başlangıç $8-10K.

**DUK — duke energy** (skor 11 EKLE)
- **tez**: utility defansif, SMA50 üstü, rally gününde -%0.17 ile katılmadı (sakin konsolidasyon). AI veri merkezi elektrik talebi uzun vadeli tez (NEE ile birlikte).
- **karşıt argüman**: utility sektörü faiz hareketine hassas, 10Y düşüşü fayda ama daha düşük growth profile. dengeli portföy için de büyüme payı düşük.
- **day-2 chase**: yok, rally katılmadı, ideal giriş penceresi.
- **karar**: **EKLE** — dengeli portföy için defansif denge. $7-8K başlangıç.

**CAT — caterpillar** (skor 9 EKLE, koşullu)
- **tez**: global infrastructure, ceasefire sonrası civil spending recovery, dengeli portföy için industrial çekirdek.
- **karşıt argüman**: day-1 +%6.51 chase riski, 29 nis earnings 20 gün sonra (K-05 temiz ama yaklaşan).
- **karar**: **EKLE-koşullu** — $745-755 pullback'te. direkt giriş yapma.

### dengeli portföy nihai deployment planı

**slot durumu**: 2/6 dolu, **4 boş slot** var. mevcut nakit $82,613.

| sıra | sembol | miktar | karar | zamanlama |
|------|--------|--------|-------|-----------|
| 1 | ATMU | $9,000 (143 pay @$63) | **EKLE** | seans açılışı veya ilk pullback |
| 2 | DUK | $9,000 (68 pay @$131) | **EKLE** | seans açılışı (day-2 chase yok) |
| 3 | LMT | $9,000 (14 pay @$628) | EKLE | pullback $620 altı |
| 4 | CAT | $9,000 (11 pay @$770) | EKLE-koşullu | pullback $750 altı |

**toplam deployment**: $36,000 — dengeli nakit %44 düşer ($46,613 kalır). 2 pozisyon hemen, 2 koşullu → kademeli giriş.

---

## 3. agresif portföy fırsat taraması

### tarama özeti
- evren: 15 AI tedarik zinciri öncelik listesi (ASML, AMAT, LRCX, KLAC, COHR, WDC, AVGO, MU, MRVL, CRDO, NVDA, ANET, VRT, POWL, MP)
- tarama kaynağı: `scripts/portfolio_scan_aggressive.py`
- eşik: skor <10 GEÇ, 10-13 İZLE, 14+ EKLE

### nihai adaylar

| # | sembol | tema | fiyat | RSI | 1M | 3M | day-1 | skor | karar |
|---|--------|------|-------|----:|---:|---:|------:|-----:|-------|
| 1 | WDC | memory | $338.78 | 65 | +29.3% | +69.0% | +8.60% | **17** | **EKLE** |
| 2 | POWL | güç | $218.07 | — | +25.8% | +79.0% | +8.12% | **16** | **EKLE** |
| 3 | AMAT | semi equip | $385.72 | 63 | +13.8% | +28.1% | +8.87% | **15** | **EKLE** |
| 4 | KLAC | semi equip | $1672 | 66 | +17.0% | +19.5% | +7.97% | **15** | **EKLE** |
| 5 | MU | memory | $406.73 | — | +4.5% | +17.9% | +7.72% | **15** | **EKLE** |
| 6 | LRCX | semi equip | $246.49 | — | +16.7% | +12.9% | +9.87% | 13 | İZLE |
| 7 | ASML | semi equip | $1421 | — | +4.7% | +11.6% | +8.77% | 11 | İZLE |
| 8 | VRT | güç/sogutma | $281.03 | — | +6.3% | +71.8% | +7.14% | 11 | İZLE |
| 9 | ANET | connectivity | $145.07 | — | +5.8% | +18.0% | +8.55% | 10 | İZLE |
| 10 | COHR | optik | — | — | — | — | — | 9 | GEÇ |
| 11 | MRVL | chip | — | — | — | — | — | 9 | GEÇ |
| 12 | NVDA | chip AI | — | — | — | — | — | 7 | GEÇ |
| 13 | AVGO | chip AI | — | — | — | — | — | 5 | GEÇ |
| 14 | CRDO | optik | — | — | — | — | — | 3 | GEÇ |
| 15 | MP | rare earth | $54.44 | 51 | -9.7% | -12.2% | — | **-4** | GEÇ |

### ortak filtre + day-2 chase uygulaması

**kritik**: tüm EKLE adayları day-1 +%7-9 arası koştu. day-2 chase riski yüksek. 1M momentum sıralama + chase skoru:

| sembol | skor | 1M | day-1 | chase skoru | revize karar |
|--------|:---:|---:|------:|:---:|--------|
| MU | 15 | **+4.5%** | +7.72% | **düşük** | **EKLE (ilk deployment)** |
| VRT | 11 | +6.3% | +7.14% | orta-düşük | İZLE → EKLE koşullu |
| ANET | 10 | +5.8% | +8.55% | orta | İZLE |
| ASML | 11 | +4.7% | +8.77% | orta | İZLE |
| AMAT | 15 | +13.8% | +8.87% | yüksek | EKLE-koşullu (pullback) |
| KLAC | 15 | +17.0% | +7.97% | yüksek | EKLE-koşullu (pullback) |
| LRCX | 13 | +16.7% | +9.87% | yüksek | İZLE |
| WDC | 17 | +29.3% | +8.60% | **çok yüksek** | **İZLE** (RSI 65 sınırda, aşırı uzanmış) |
| POWL | 16 | +25.8% | +8.12% | **çok yüksek** | **İZLE** (aşırı uzanmış) |

**MU en ölçülü aday** — skor 15 EKLE + 1M sadece +%4.5 (diğerlerinden çok daha az uzanmış) + day-1 chase minimum. ilk deployment ideal.

### tez ve karşıt argümanlar

**MU — micron technology** (skor 15 EKLE, day-2 deployment en iyi aday)
- **tez**: HBM memory için AI data center talebi, TSMC/SK Hynix kapasitesi sıkışık, MU kazanç döngüsü yukarı. skor 15 + 1M sadece +%4.5 = chase riski düşük. schwab post-ceasefire notu MU'yu +%9 pre-market hareket olarak saydı (memory chip beneficiary).
- **karşıt argüman**: geçmiş "MU sell the news" kayıp dersi var (earnings beat → düşüş). ancak bu earnings olayı değil, ceasefire rally, farklı mekanizma. yine de memory fiyatı döngüsel, üst başlangıcında alım hatalı olabilir.
- **skor detay**: 1M momentum düşük bonus, 6M 17% +1, ROIC orta, golden cross, SMA50/200 üstü, RSI healthy zone
- **karar**: **EKLE** — agresif portföyün ilk deployment adayı. **çeyrek pozisyon** başlangıç ($17,891 = $357,823'ün %5), day-2 teyit sonrası kademeli ekleme.

**AMAT — applied materials** (skor 15 EKLE, koşullu)
- **tez**: ASML/LRCX/KLAC ile birlikte semiconductor capital equipment quartet, AI supply chain sol taraf çekirdek. ROIC güçlü, trend sağlam.
- **karşıt argüman**: 1M +%13.8 uzanmış, day-1 +%8.87 chase riski yüksek. RSI 62 henüz üst sınırda değil ama yaklaşıyor. pullback'e kadar beklemek rasyonel.
- **karar**: **EKLE-koşullu** — $360-365 pullback gelirse, çeyrek pozisyon $17,891.

**KLAC — kla corporation** (skor 15 EKLE, koşullu)
- **tez**: AMAT ile aynı cluster, semi equipment lideri, metrology/inspection niş.
- **karşıt argüman**: RSI 66.4 üst sınırın hemen üzerinde, fiyat $1672 yüksek, position sizing'de çeyrek pozisyon = 10-11 pay dar slipaj.
- **karar**: **EKLE-koşullu** — RSI 60 altına gelirse, AMAT ile K-17 korelasyon nedeniyle sadece BİRİNİ seç (AMAT öncelikli, daha iyi likidite).

**VRT — vertiv** (skor 11 İZLE, koşullu yükseltme)
- **tez**: veri merkezi güç + soğutma, AI infrastructure saf play, 3M +%71 güçlü trend ama 1M +%6.3 ölçülü.
- **karşıt argüman**: aggressive v1 failure listesinde vardı (POWL/CAMT/VRT cluster, 25 mart K-17 ihlali). aynı hataya düşmemek için dikkat.
- **karar**: **EKLE-koşullu** — MU deployment 1 hafta sonra işe yararsa ikinci adım olarak. pullback $265 altı.

### agresif portföy nihai deployment planı

**slot durumu**: 0/10 dolu, **10 boş slot** var. mevcut nakit $357,823.

**kademeli deployment stratejisi** (day-2 chase riskini yönetmek için):

| faz | zaman | sembol | miktar | koşul |
|-----|-------|--------|--------|-------|
| **FAZ 1** | bugün (9 nis) | MU | **$17,891** (44 pay @$407) çeyrek pozisyon | day-2 teyit: SPY $675 üstü kalırsa |
| FAZ 2 | yarın-pazartesi (10-13 nis) | AMAT | $17,891 (46 pay @$385) | pullback $360-365 |
| FAZ 3 | 13-14 nis | VRT veya ANET | $17,891 | K-17 korelasyon kontrolü |
| FAZ 4 | 15 nis sonrası | KLAC veya LRCX | $17,891 | ASML earnings teyit sonrası |
| FAZ 5 | 20+ nis | ek pozisyonlar | adım adım | her FAZ için ayrı değerlendirme |

**toplam FAZ 1-4 deployment**: $71,564 (agresif nakitin %20'si). eğer rally teyit olursa FAZ 5'te %40-50'ye çıkar. day-2 sonrası konservatif kalibre.

### neden "bugün hepsini deploy et" yapmıyorum?

1. **K-14 yeni kalktı**: swing tarafında yarım pozisyon protokolü aktif, aynı disiplin portföy tarafında da geçerli
2. **day-2 chase**: tüm adaylar dün +%7-9 koştu, iki gün üst üste devam olasılığı düşük
3. **aggressive v1 failure dersi**: over-concentration + fast deployment mart drawdown'u yarattı
4. **ceasefire fragile**: 2 hafta sonunda re-escalation riski %15-35 arası, tam deployment risk bütçesi aşar
5. **JNJ earnings 14 nis**: genel piyasa volatilite risk penceresi, bu hafta tam deployment zamanlaması kötü

---

## 4. temettü portföy fırsat taraması

### tarama özeti
- evren: 19 manuel seçim (energy midstream, tobacco, consumer staples, pharma)
- tarama kaynağı: `scripts/portfolio_scan_dividend.py`
- eşik: skor <6 GEÇ, 6-8 İZLE, 9+ EKLE

### nihai adaylar

| # | sembol | sektör | fiyat | yield | P/E | payout | skor | karar |
|---|--------|--------|-------|------:|----:|-------:|-----:|-------|
| 1 | OKE | energy midstream | — | 5.22% | 16.0 | — | 8 | İZLE |
| 2 | BTI | tobacco | — | — | — | — | 8 | İZLE |
| 3 | BMY | pharma | — | — | — | — | 8 | İZLE |
| 4 | KMB | staples | — | — | — | — | 8 | İZLE |
| 5 | XOM | energy | — | — | — | — | 7 | İZLE |
| 6 | LLY | pharma | — | — | — | — | 7 | İZLE |
| 7 | KMI | energy | — | — | — | — | 6 | İZLE |
| 8 | WMB, CL, PG | | | | | | 5 | GEÇ |
| 9 | PM, KO, PEP | | | | | | 4 | GEÇ |
| 10 | ENB, PFE, CVX | | | | | | 1-3 | GEÇ |
| 11 | MDLZ, ABBV, HSY | | | | | | <0 | GEÇ |

**önemli**: **hiçbir aday EKLE eşiği 9'u geçemedi**. hepsi İZLE veya GEÇ. bu özel bir şey — ceasefire rally sonrası yüksek P/E temettü hisselerinin skoru düştü, value-dividend kombinasyonu şu anda zor.

### ortak filtre uygulaması

İZLE seviyesindeki 7 aday için K-04 ve K-18 kontrolü:

| sembol | K-04 SMA50 | mekanik skor | day-1 chase | karar |
|--------|:---:|:---:|:---:|--------|
| OKE | ? | 8 | rally gününde yaklaşık sessiz | İZLE |
| BTI | ? | 8 | — | İZLE |
| BMY | ? | 8 | — | **İZLE** (MO trim rotasyonu için iyi aday) |
| KMB | ? | 8 | sessiz | **İZLE** (MO trim rotasyonu için iyi aday) |
| XOM | ? | 7 | **-%4.69** ceasefire kaybedeni | İZLE |

### tez ve karşıt argümanlar

**BMY — bristol-myers squibb** (skor 8 İZLE, trim rotasyonu için ana aday)
- **tez**: yüksek temettü + ucuz P/E pharma, sağlık sektörü çeşitlilik (MRK ile birlikte). momentum zayıf ama defansif.
- **karşıt argüman**: BMY uzun dönemdir momentum zayıf, patent cliff endişeleri devam ediyor. yield trap sinyalleri yok ama growth yok.
- **karar**: **İZLE** — MO trim serbest bırakılan $7K için rotasyon adayı.

**KMB — kimberly-clark** (skor 8 İZLE)
- **tez**: consumer staples defansif, stabil cash flow, temettü sürdürülebilirlik yüksek.
- **karşıt argüman**: growth yavaş, ceasefire sonrası risk-on ortamında underperformance olası.
- **karar**: **İZLE** — trim rotasyonu için ikincil aday.

**XOM — exxon mobil** (skor 7 İZLE, day-1 kaybeden)
- **tez**: oil price %16 düşüşle -%4.69 geldi. ucuzladı. mevcut temettü portföyünde enerji yok, çeşitlilik bonus.
- **karşıt argüman**: oil price belirsiz, WTI 90 altına düşerse ikinci satış dalgası, E&P analist downgrade dalgası devam ediyor (roth capital 6 isim indirdi).
- **karar**: **İZLE** — WTI $92+ üstünde stabilize olursa + XOM SMA50 üstü kalırsa değerlendir.

### temettü portföyü nihai deployment planı

**slot durumu**: 4/15 dolu, **11 boş slot** var. mevcut nakit $96,876.

**bu sabahki aksiyon**: **yeni EKLE yok** (hiçbir aday eşik geçmedi). sadece **MO trim rotasyonu** (bkz bölüm 1b). 

| sıra | aksiyon | miktar | karar |
|------|---------|--------|-------|
| 1 | MO trim (%50) | 109 pay sat → $7,281 | DÖNDÜR-TRİM |
| 2 | serbest $7,281 | nakit tut (haftaya tekrar tara) | beklemede |

**temettü portföy diagnozu**: şu an "alınacak çok şey yok" piyasası. ceasefire rally'si growth hisselerine kaydı, temettü tarafı geride kaldı. önümüzdeki 1-2 hafta temettü hisselerinde pullback fırsatı gelebilir. nakitte kalıp beklemek akıllıca.

---

## 5. watchlist güncellemesi

### 5a. seviyeye ulaşan adaylar (entry_active)

mevcut watchlist'teki 10 adayın hiçbiri "pullback bandı" seviyesinde değil — hepsi dün koştuğu için giriş seviyelerinden uzak.

| sembol | hedef_giris | son fiyat | durum |
|--------|-------------|-----------|-------|
| WDC | — | $338.78 | uzak (çok uzanmış) |
| AMAT | — | $385.72 | pullback bekleniyor |
| CAT | — | $771.58 | pullback bekleniyor |
| ATMU | — | $63.13 | **yakın — bugün giriş adayı** |
| DUK | — | $131.60 | **sakin — bugün giriş adayı** |

### 5b. yeni eklenen adaylar (bu sabah taramadan)

| sembol | portföy | sektör | skor | urgency | not |
|--------|---------|--------|------|---------|-----|
| MU | agresif | memory | 15 | high | day-2 deployment primary |
| LMT | dengeli | defense/industrial | 12 | high | pullback hedefi $620 |
| VRT | agresif | veri merkezi güç | 11 | medium | FAZ 3 adayı |
| ANET | agresif | connectivity | 10 | medium | K-17 korelasyon kontrol |
| BMY | temettü | pharma | 8 | medium | MO trim rotasyon adayı |
| KMB | temettü | staples | 8 | low | MO trim alternatif |
| OKE | temettü | energy midstream | 8 | low | enerji sektör çeşitlilik |

### 5c. elenen adaylar (K-12, K-18, day-2 chase)

| sembol | portföy | sebep | aksiyon |
|--------|---------|-------|---------|
| KLAC | agresif | RSI 66.4 üst sınırın üstü + AMAT ile K-17 korelasyon | izlemede kalır, AMAT alternatif |
| WDC | agresif | 1M +%29 aşırı uzanmış + RSI 65 sınır | izlemede kalır, pullback bekle |
| POWL | agresif | 1M +%25.8 aşırı uzanmış + v1 cluster dersi | izlemede kalır |

### 5d. watchlist toplam (güncel)

- dengeli: 4 (ATMU, DUK, CAT, LMT ⭐ yeni)
- agresif: 8 (WDC, KLAC, AMAT, MU ⭐ yeni, LRCX, ASML, VRT ⭐ yeni, ANET ⭐ yeni)
- temettü: 4 (MRK, BMY ⭐ yeni, KMB ⭐ yeni, OKE ⭐ yeni)
- **toplam aktif watchlist**: 16 aday
- **hariç tutulanlar**: 5 (QCOM, PFE, SNDK, UNH, SO — 30g cool-down)

---

## 6. bugün için aksiyon planı

### 🔴 hemen (seans açılışında, 16:30 TR)

1. **EKLE** — **ATMU** — $9,000 (143 pay @$63.13) — **dengeli portföy** — day-1 ölçülü +%4.55, çeşitlilik bonusu, defansif büyüme
2. **EKLE** — **DUK** — $9,000 (68 pay @$131.60) — **dengeli portföy** — rally'ye katılmadı, pullback riski düşük, utility defansif denge
3. **EKLE** — **MU** — $17,891 (44 pay @$406.73) — **agresif portföy** — FAZ 1 deployment, day-2 ölçülü chase (1M +%4.5), AI memory HBM tezi, çeyrek pozisyon

**bugünkü toplam deployment**: $35,891

### 🟡 izle (seans içinde — seviye tetikli)

4. **LMT** $620 altı → **EKLE** dengeli $9,000 (14 pay)
5. **CAT** $750 altı → **EKLE** dengeli $9,000 (11 pay)
6. **AMAT** $365 altı → **EKLE** agresif FAZ 2 $17,891 (48 pay)
7. **SPY** $674.92 (SMA50) altına geçerse → **tüm planları askıya al**, K-14 yeniden devreye girebilir
8. **VIX** 22 üstüne çıkarsa → **K-13 sakin bandı bozuldu**, yeni giriş yok

### 🟢 pasif (gün sonu / bu hafta)

9. **MO trim (temettü)** — 109 pay sat ~$7,281 serbest bırak — K-12 sektör limit aşımı çözümü, session promptunda icra
10. **T ve VZ** — izlemede, K-04 SMA50 altı devam ettiği sürece yeni alım yok. haftalık kontrol ile DÖNDÜR yeniden değerlendirme.
11. **VRT, ANET** — FAZ 3 adayları, pazartesi (13 nis) değerlendirme
12. **KLAC** — RSI 60 altına inerse AMAT alternatifi olarak değerlendir

---

## 7. karşıt argüman özeti

her EKLE/DÖNDÜR-TRİM kararı için "neden yanlış olabilirim":

- **ATMU EKLE**: 6M +%42 sonrası normal mean reversion beklenebilir, small-cap likidite riski baskılarda büyür. ama çeşitlilik bonusu + skor 12 + day-1 ölçülü giriş gerekçesi yeterli.
- **DUK EKLE**: utility sektörü faiz hareketine hassas, eğer 10Y %4.29'dan yukarı dönerse utility basınç altında. ama mevcut rate cut beklentisi güçlendi (Fed watch %45), tailwind devam.
- **MU EKLE**: "MU sell the news" geçmiş dersi var, memory döngüsel, DRAM spot fiyatları son 3 ayda zirve yapmış olabilir. ama bu earnings olayı değil ceasefire rally, mekanizma farklı. 1M +%4.5 düşük momentum chase riski minimize ediyor.
- **LMT EKLE-koşullu**: ceasefire süresi uzarsa defense rotation out devam eder, $620 seviyesinde bile geç alım olabilir. ama LMT uzun sözleşme modeli, kısa vadeli haber etkisi sınırlı.
- **CAT EKLE-koşullu**: day-1 +%6.5, pullback derin olmayabilir, $750 görmeyip direkt uçabilir. bekleme maliyeti var. ama R:R disiplini kritik.
- **MO trim**: MO teknik olarak sağlıklı ve kârda, satmak mekanik olarak "yanlış" gibi. ama K-12 sektör limit aşımı + yield trap cezası bir disiplin meselesi, fundamenta değil.
- **T/VZ DÖNDÜR değil İZLE**: ben mekanik skora karşı "SpaceX yapısal baskı" öne çıkarıyorum. bu onay yanlılığı olabilir, skor 10-11 EKLE seviyesi açık. DBS hold 1 kurum, consensus değişmedi. belki T/VZ yeniden EKLE'ye dönmeli. ancak K-04 filtresi başarısız olduğu için yeni alım yapılamıyor — bu disiplin çelişkisi değil, kural.

### genel fırsat kaçırma riski

eğer bugün deployment yapmaz/ertelersem ve rally devam ederse $35,891 yerine $200K+ deploy etmek gerekebilir, daha yüksek fiyatlardan. FOMO riski gerçek. ancak:
- FAZ 1-5 planı kademeli, FOMO'yu kontrollü hale getiriyor
- $35,891 bugün + 1-2 hafta içinde $71K'ya çıkabilir = yeterli katılım
- sıfır deployment DEĞİL — bugün 3 pozisyon açılıyor

---

*finzora ai | portfolio_opportunity_system v1.1 | 3 portföy scan tamam | watchlist 16 aday | bugün 3 EKLE aksiyon + 1 DÖNDÜR-TRİM*
