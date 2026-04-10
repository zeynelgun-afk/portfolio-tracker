# GÜNLÜK RAPOR PART 2 — KAPANIŞ RAPORU v1.5

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt'taki her adım sırayla ve eksiksiz uygulanmalıdır. hiçbir adım atlanamaz, kısaltılamaz veya "sonra yaparım" diye ertelenmez. bir adımı tamamlamadan diğerine geçme.
>
> **zorunlu adımlar (teker teker kontrol et):**
> - [ ] ADIM 1 — git pull + hazırlık (JSON'ları oku, dünkü raporu kontrol et)
> - [ ] ADIM 1.5 — dün session_state.json okuma (faz1/faz2/faz3 aksiyon logları, K-rule etiketleri, trade tarihçesi)
> - [ ] ADIM 2 — FMP veri toplama (batch-quote, portföy: RSI+SMA, swing: ichimoku, emtia, treasury)
> - [ ] ADIM 3 — JSON güncelleme (fiyatlar, k/z, ağırlıklar, summary.json, git commit)
> - [ ] ADIM 3.5 — KAZANÇ AÇIKLAMALARI TARAMASI (earnings-calendar, portföy kesişimi, detaylı analiz)
> - [ ] ADIM 4 — rapor yaz (BÖLÜM 1-6 eksiksiz)
> - [ ] BÖLÜM 1 — günün özeti (piyasa tablosu, sektörler, trend)
> - [ ] BÖLÜM 2 — portföy takibi (3 portföy + genel özet + uyarılar)
> - [ ] BÖLÜM 3 — swing trade durumu (aktif pozisyonlar, ichimoku kontrol)
> - [ ] BÖLÜM 4 — kazanç açıklamaları (bugünkü bilançolar, portföy kesişimi analizi)
> - [ ] BÖLÜM 5 — günün değerlendirmesi (sabah planı vs gerçekleşme, seans içi aksiyon logu, dersler)
> - [ ] BÖLÜM 6 — sonuç + yarın aksiyonları
> - [ ] ADIM 5 — PLAYBOOK GÜNCELLE (derslerden yeni kural varsa `docs/TRADING_PLAYBOOK.md`'ye ekle)
> - [ ] GIT — rapor + playbook commit + push yapıldı mı?
>
> **geçmiş hatalar**: bölüm 4 (kazanç açıklamaları) atlandı → Oracle bilançosu ($17.2B gelir, bulut +%84, AH +%6.3) rapordan tamamen eksik kaldı. bölüm 5 ve 6 da eksik yazıldı. bu tür atlamalar portföy kararlarını olumsuz etkiler. her bölümü tamamla.

> **versiyon**: 1.5 | **son güncelleme**: 9 nisan 2026 (session_state.json okuma + K-kural referans bağlantısı)
> **çıktı dosyası**: `reports/daily/DAILY_KAPANIS_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~09:00 (NYSE dün gece 23:00'da kapandı, bugün 16:30 açılacak — yaz saati)
> **ön koşul**: bir önceki günün PART 1 sabah raporu çalıştırılmış olmalı (çünkü PART 2 dünün seansını değerlendirir, sabah planı ile gerçekleşmeyi karşılaştırır). aynı gün PART 1 bugün seansı için ayrı plan yapar, PART 2 ile doğrudan ilişkili değildir.
> **session state okuma**: `data/session_state.json` dün FAZ 1/2/3 bloklarını okur, trade kararlarını + K-rule uygulamalarını rapora yansıtır. kapanış raporu yazıldıktan sonra state dosyası yarın sabah PART 1 tarafından flag'ler okunana kadar korunur.
> **K-kural referansı**: `docs/K_RULES_QUICK_REF.md` — kural detayları için, prompt içinde tekrarlama
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit 1**: `[GÜNCELLEME] DD Ay - kapanış fiyatları`
> **git commit 2**: `[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~09:00'da yazılır — NYSE dün gece 23:00'da kapandı
- FMP fiyatları = dünün kapanışı (kesinleşmiş)
- after-hours: dün 23:00-01:00 TR (tamamlanmış)
- pre-market: bugün 12:00-16:30 TR (henüz başlamadı)
- bugünün seansı: 16:30-23:00 TR (yaz saati)
- sabah raporundaki plan dünün seansında uygulandı

---

## ÇALIŞMA AKIŞI

```
ADIM 1 — GIT PULL + HAZIRLIK
  → git pull (sabahtan bu yana değişiklik olabilir)
  → tüm JSON dosyalarını oku (balanced, aggressive, dividend, swing/active)
  → benzersiz sembol listesi çıkar (3 portföy + swing + SPY)
  → dünkü raporu oku (varsa), bölüm 5 aksiyon planını not al

ADIM 1.5 — DÜN SESSION_STATE OKUMA
  → data/session_state.json dosyasını oku (yoksa uyar, BÖLÜM 5 seans logu boş kalsın)
  → tarih kontrolü: state.tarih == dün olmalı (değilse uyar, eski state)
  → state.faz1 oku:
    - açılış piyasa verileri (SPY/QQQ/VIX snapshot)
    - gap raporu
    - k06/k09 tetikleri (acil aksiyonlar)
    - BMO earnings etkisi
    - twitter öne çıkanlar (rapora YAZILMAZ, sadece bağlam)
  → state.faz2 oku:
    - teknik durum snapshot'ı
    - sektör RS ve prediction markets delta'ları
    - karar matrisi çıktıları (alış/satış/tut/izle)
    - yeni aday değerlendirmeleri ve GO/NO-GO sonuçları
  → state.faz3 oku:
    - power hour aksiyonları (kâr alma, trailing güncelleme, final satış)
    - AMC earnings listesi
    - after-hours izleme listesi
    - yarin_flag_listesi (yarın PART 1 sabah raporu kullanacak)
  → state.seans_ozet oku: toplam trade, net k/z, aktif pozisyon, nakit oranı
  → CROSS-CHECK: bu veriyi data/transactions.csv ve portfolio JSON'ları ile karşılaştır
    - state'te yazan her trade CSV'de var mı?
    - CSV'de olup state'te olmayan trade var mı? (manuel müdahale flag'i)
    - tutarsızlık varsa rapor BÖLÜM 5'te belirt

⚠️ ÖNEMLİ: state dosyası silinmez, yarın sabah PART 1 bayrakları okuyacak.
    state tarihi eski olursa (bir gün atlama) PART 1 kendi durumu raporlar.

ADIM 2 — FMP VERİ TOPLAMA
  → batch-quote: tüm benzersiz semboller + SPY/QQQ/DIA/IWM/VIXY
  → teknik göstergeler (portföy hisseleri): her sembol için RSI(14), SMA(50), SMA(200)
  → portföy stopları:
    ⚠️ portföy pozisyonlarının stop_loss alanı JSON'da SABİTTİR (giriş anında belirlenmiş), kapanışta yeniden hesaplanmaz
    ⚠️ istisna: K-11 katman 1 tetiklendiyse (RSI ≥70 VE kâr ≥%15) kâr kilidi aktifleşir
      → ATR(14) hesapla, yeni kâr kilidi: max(2×ATR, 20SMA altı)
      → yeni stop eski stoptan BÜYÜKSE güncelle; ASLA aşağı çekme
      → tetiklenmediyse stop değişmez
  → swing pozisyonları için chandelier stop ADIM 3'te güncellenir (RSI/SMA swing için çekilmez, ichimoku scripti kapsar)
  → emtia/döviz: GCUSD, USO (petrol proxy), EURUSD
    ⚠️ CLUSD/WTIUSD güvenilmez → USO kullan. doğrudan ^VIX güvenilmez → VIXY kullan
  → treasury-rates

ADIM 3 — JSON GÜNCELLEME
  → her pozisyon: guncel_fiyat, gunluk_degisim_yuzde, guncel_deger, kar_zarar, kar_zarar_yuzde, agirlik_yuzde, son_guncelleme
  → portföy toplamları: toplam_deger, toplam_getiri_yuzde
  → swing: guncel_fiyat, guncel_kar_zarar_yuzde, tutulan_gun
  → swing pozisyonları: chandelier stop güncelle (highest_high, ATR yeniden hesapla)
    (çıkış sinyali kontrolü: chandelier tetiklendi mi, TK cross, kumo girişi)
  → kapanış raporunda ichimoku değişimi takibi (kijun hareket, sinyal durumu)
  → summary.json güncelle
  → doğrulama: yatirim = adet × maliyet_baz, toplam = sum(pozisyonlar) + nakit, ağırlık ≈ %100
  → GIT COMMIT + PUSH: "[GÜNCELLEME] DD Ay - kapanış fiyatları"

ADIM 3.5 — KAZANÇ AÇIKLAMALARI TARAMASI
  → FMP earnings-calendar: from=bugün, to=bugün → o günün açıklamalarını çek
  → market cap filtresi: sadece >$2B şirketler (küçük şirketler atla)
  → zamanlama filtresi: sadece "amc" (kapanış sonrası) veya tümü
  → KESİŞİM KONTROLÜ:
      - portföy sembolleriyle karşılaştır (3 portföy + swing)
      - data/watchlist.json sembolleriyle karşılaştır (merkezi watchlist)
  → KESİŞEN şirketler için FMP'den tam analiz çek:
      - income-statement (son 2 çeyrek — gerçek vs önceki dönem)
      - analyst-estimates (EPS ve gelir beklenti vs gerçek fark)
      - key-metrics-ttm + ratios-ttm
      - news/stock (limit=5, yönetim yorumu / yönlendirme)
  → KESİŞMEYEN şirketler için: sadece beklenti/gerçek özet tablosu (max 5 şirket)
  → SONUÇ: kazanç açıklamaları bölümü (bölüm 4) için veri hazır

ADIM 4 — RAPOR YAZ
  → bölüm 1-6'yı sırayla yaz (format aşağıda)
  → bölüm 4 kazanç açıklamaları (adım 3.5 verileriyle) ekle
  → sabah raporundaki planla karşılaştır (bölüm 5)
  → reports/daily/DAILY_KAPANIS_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet"
  → TELEGRAM GÖNDERİMİ (git push'tan SONRA):
    1. python scripts/telegram_notify.py --type closing --theme "[günün özeti]"
    2. python scripts/telegram_notify.py --type report --file reports/daily/DAILY_KAPANIS_YYYY-MM-DD.md

ADIM 5 — PLAYBOOK GÜNCELLE
  → docs/TRADING_PLAYBOOK.md dosyasını oku
  → bölüm 5'teki derslerden yeni kural çıkarılacak mı kontrol et:
    - yeni bir hata kalıbı tespit edildiyse → yeni K-XX kuralı ekle
    - mevcut bir kural teyit edildiyse → kanıt satırına ekle
    - hata tablosuna yeni satır ekle (tarih, hisse, hata, sonuç, kural)
    - çalışan strateji varsa → çalışan stratejiler tablosuna ekle
    - swing istatistiklerini güncelle (yeni kapanış varsa)
  → değişiklik yoksa "bugün yeni kural yok" notu düş ve atla
  → değişiklik varsa → GIT COMMIT + PUSH: "[PLAYBOOK] yeni kural/güncelleme açıklaması"
```

---

## RAPOR FORMATI

rapor 6 bölümden oluşur. github'a push edilir.

---

### BÖLÜM 1: GÜNÜN ÖZETİ

kısa, hızlı özet — bugün ne oldu.

```markdown
## 1. günün özeti

**tarih**: {tarih}, {gün} | **seans**: NYSE kapandı
### piyasa

| ticker | kapanış | değişim | RSI | SMA50 | SMA200 |
|--------|---------|---------|-----|-------|--------|
| SPY | $XXX.XX | +X.XX% | XX.X | ✅/❌ | ✅/❌ |
| QQQ | $XXX.XX | +X.XX% | | | |
| DIA | $XXX.XX | +X.XX% | | | |
| IWM | $XXX.XX | +X.XX% | | | |

**emtia + döviz**: altın $X,XXX (±%), WTI $XX (±%), 10Y %X.XX

**sektörler**: en güçlü [sektör +%], en zayıf [sektör -%]
**trend**: [boğa/nötr/ayı] — [1 cümle gerekçe]
```

---

### BÖLÜM 2: PORTFÖY TAKİBİ

3 portföyün detay tablosu, uyarılar, aksiyonlar.

**teknik uyarı kuralları** (playbook referansları ile):
- RSI > 70 → overbought uyarısı (K-11 katman 1 tetiği, RSI 70+ otomatik satış DEĞİL, momentum teyidi)
- RSI > 80 → K-11 katman 2 baskın tetik (kısmi satış %25-30 değerlendir)
- RSI < 35 → oversold bölgesi, mevcut pozisyon için tez gözden geçir; K-04 istisna kontrolü uygun mu? (K-15a sadece YENI giriş filtresi, mevcut pozisyon için uygulanmaz)
- fiyat > SMA50 → ✅ (K-04 trend filtresi), fiyat < SMA50 → ❌ (K-04 istisna kontrolü gerek)
- fiyat < SMA200 → uzun vadeli trend kırılması uyarısı
- k/z < -max(2×ATR, %5) → K-06 stop-loss tetikleyici (sabit eşik yok, hisse bazlı)
- K-12 konsantrasyon kontrolü (portföy bazlı):
  • Dengeli: tek hisse > %25 → uyarı
  • Agresif: tek hisse > %20 → uyarı
  • Temettü: tek hisse > %15 → uyarı
- günlük değişim < -%5 → sert düşüş kontrolü (K-09 stop yakınlık çalıştır)

```markdown
## 2. portföy takibi

### 2a. dengeli portföy ($100K başlangıç)

| sembol | fiyat | günlük | k/z | RSI | 50 | 200 | durum |
|--------|-------|--------|-----|-----|----|-----|-------|
| SM | $XX.XX | +X.X% | +X% | XX | ✅ | ✅ | [not] |

**toplam**: $XXX,XXX (+%X.XX) | **nakit**: $X,XXX | **pozisyon**: X

### 2b. agresif portföy ($400K başlangıç)

[aynı tablo formatı]

### 2c. temettü portföyü ($100K başlangıç)

[aynı tablo formatı]

### genel özet ($600K toplam)

**toplam değer**: $XXX,XXX | **k/z**: +$XX,XXX (+%X.XX) | **SPY**: +%X.XX | **alpha**: +%X.XX

### uyarı özeti

🔴 **acil**: [SEMBOL] — [neden]
⚠️ **izle**: [SEMBOL] — [neden]
🟢 **fırsat**: [SEMBOL] — [neden]
```

---

### BÖLÜM 3: SWING TRADE

aktif pozisyonlar, ichimoku çıkış kontrolü, aksiyonlar.

**durum belirleme (swing v2.3 chandelier)**:
- intraday low ≤ chandelier stop → 🔴 ÇIK (K-06 ana kural: stop tetiklendiğinde ÇIKIŞ, override yasak)
- kâr %7-15 bandında → chandelier sıkılaşır (2×ATR), K-07 kâr kilidi aktif
- kâr %15+ bandında → chandelier agresif (1.5×ATR)
- fiyat kumo üstü + tenkan > kijun → ✅ normal tutma
- hacim ayrışması (düşen hacim + yükselen fiyat) → ⚠️ DİKKAT, izleme artır
- NOT: kijun tabanlı çıkış v2.1'de kaldırıldı, sadece TK cross savunmacı kullanım (K-07 referansı)

```markdown
## 3. swing trade durumu

> swing v2.3: chandelier exit (3×ATR) + ichimoku durum kontrolü

| id | sembol | giriş | güncel | k/z | chandelier stop | highest high | ATR | gün | durum |
|----|--------|-------|--------|-----|-----------|------|--------------|-----|-------|

**aktif**: X/6 | **ortalama k/z**: +%X.XX

**ichimoku değişimi** (önceki seans ile karşılaştır):
- [SEMBOL]: chandelier $XX → $XX (stop güncellendi/korundu), çıkış sinyali: var/yok

**aksiyonlar**:
🔴 **hemen**: [SEMBOL] — [chandelier stop tetiklendi / TK cross aşağı → çık]
🟡 **izle**: [SEMBOL] koşul → aksiyon
✅ **sorunsuz**: [liste]

**istatistik**: toplam X trade | kazanç X (%XX) | kayıp X (%XX)
```

---

### BÖLÜM 4: KAZANÇ AÇIKLAMALARI

bugün kapanış sonrası (veya gün içi) açıklayan şirketlerin analizi.

**mantık**:
- o günün açıklamalarını tara, market cap >$2B filtrele
- portföy/watchlist kesişimi varsa → tam analiz
- kesişim yoksa → sadece öne çıkan 3-5 şirketi özet tablo

```markdown
## 4. kazanç açıklamaları — [tarih]

### bugün açıklayanlar (market cap >$2B)

| şirket | sembol | EPS beklenti | EPS gerçek | fark | gelir fark | yönlendirme | AH |
|--------|--------|-------------|------------|------|------------|-------------|-----|
| Marvell | MRVL | $0.62 | $0.68 | +9.7% | +4.2% | yükseltildi ✅ | +13.6% |

> toplam X şirket açıkladı, X tanesi beklenti üstü (%XX), X tanesi beklenti altı (%XX)

---

### portföy/izleme kesişimi — detaylı analiz

[kesişim varsa her şirket için ayrı başlık]

**SEMBOL — Şirket Adı** ✅ beklenti üstü / ❌ beklenti altı

- **EPS**: beklenti $X.XX → gerçek $X.XX (+%X.X)
- **gelir**: beklenti $XB → gerçek $XB (+%X.X)
- **yönlendirme**: [yükseltildi / düşürüldü / korundu / verilmedi]
- **yönlendirme detayı**: [Q1 gelir beklentisi vb]
- **karlılık trendi**: [son 3 çeyrek EPS: $X → $X → $X]
- **tez etkisi**: [portföy/watchlist pozisyonumuzu nasıl etkiliyor]
- **aksiyon önerisi**: [tez devam / pozisyon artır / kar al / izle]

---

### kesişim dışı öne çıkanlar

[günün en çarpıcı 2-3 açıklaması — portföy dışı ama piyasa etkisi olanlar]

**SEMBOL**: [1 cümle özet — EPS fark ve yönlendirme]

---

[kazanç açıklaması yoksa / $2B altındakilerse]: *bugün portföyle ilgili önemli kazanç açıklaması yok.*
```

**teknik notlar**:
- beklenti vs gerçek fark: `(gerçek - beklenti) / abs(beklenti) × 100`
- **gerçek EPS/gelir verisi**: FMP `earnings-calendar` endpoint'i `epsActual` ve `revenueActual` alanları (açıklama günü anlık güncellenir)
- beklenti verisi: FMP `earnings-calendar` `epsEstimated` / `revenueEstimated` (açıklama öncesi)
- detay kalem analizi: FMP `income-statement` (açıklama sonrası 1-3 gün içinde güncellenir, anlık değil)
- kazanç sezonu dışında (Ocak/Nisan/Temmuz/Ekim arası) açıklama sayısı az olabilir — normal
- AH hareketi: web araması ile kapanış sonrası fiyat değişimi (FMP aftermarket-quote seans dışında sıfır dönüyor, kullanma)

**K-16 SELL-THE-NEWS SKOR (portföy pozisyonları için, earnings 7 gün öncesi çalıştır)**:
- Script: `python scripts/k16_sell_the_news_score.py SYMBOL`
- 5 madde: 5g ralli %5+, EPS revizyon %10+, 52w zirve %5 mesafe, sektör 1ay %10+, short float %10+
- Skor 2-3: portföy pozisyonunda %25 kısmi kâr al + K-11 trailing aktif
- Skor 4-5: %50 kısmi çık, post-earnings bekle
- NOT: Swing pozisyonları için K-05 geçerli (earnings ≤2 gün kala TAM çık), K-16 portföy için

---

### BÖLÜM 5: GÜNÜN DEĞERLENDİRMESİ

sabah raporundaki plan tuttu mu, dersler.

**kapanan trade varsa** şu formatı kullan (detay: docs/POST_TRADE_REVIEW.md):

```
kapanan trade review:
  SEMBOL — kazanç ✅ / kayıp ❌ — %X.XX ($XXX)
  süreç skoru: X/5 (5=mükemmel, 3=ortalama, 1=kötü)
  matris: ✅ ideal / ⚠️ şans / 📊 normal / ❌ hata
  kök neden: hazırlık / uygulama / boyutlandırma / duygusal / harici
  önyargı: yok / anchoring / FOMO / disposition / overconfidence / sunk_cost
  düzeltici aksiyon: [somut davranış]
```

```markdown
## 5. günün değerlendirmesi

### seans içi aksiyon logu (session_state.json kaynağı)

> ADIM 1.5'te okunan session_state dosyasından üretilir.
> state yoksa bu alt bölüm yazılmaz, "state dosyası bulunamadı" notu düşülür.

**faz 1 (açılış, TR 16:30-17:30)**:
- risk ortamı: [RISK-ON/OFF]
- gap yapan pozisyonlar: [liste]
- K-06/K-09 tetikler: [liste]
- BMO earnings etkisi: [özet]
- faz 1 aksiyonlar: [liste]

**faz 2 (orta seans, TR 18:00-21:00)**:
- karar matrisi sonucu: [X alış, Y satış, Z tut]
- yeni aday değerlendirmesi: [kaç aday, kaç GO/NO-GO geçti]
- portföyler arası korelasyon: [durum]
- faz 2 aksiyonlar: [liste, her birine K-rule etiketi]

**faz 3 (power hour, TR 22:00-23:00)**:
- kapanış öncesi kâr alma: [liste]
- trailing stop final güncellemeleri: [liste]
- AMC earnings not edildi: [liste]

**state vs transactions cross-check**:
- state'teki tüm trade'ler CSV'de ✓/✗
- CSV'de olup state'te olmayan (manuel müdahale): [varsa liste]

### sabah planı vs gerçekleşme

| plan | sonuç | not |
|------|-------|-----|
| [sabahki aksiyon 1] | ✅/❌/⏳ | [açıklama] |
| [sabahki aksiyon 2] | ✅/❌/⏳ | [açıklama] |

### günün performansı

- portföy toplam: $XXX,XXX (±$X,XXX, ±%X.XX)
- SPY: +%X.XX → alpha: +%X.XX
- en iyi: SEMBOL (+%X.XX) — [neden]
- en kötü: SEMBOL (-%X.XX) — [neden]

### dersler

- ✅ doğru: [ne, neden doğru]
- ❌ yanlış: [ne, neden yanlış]
- 🔍 kaçırılan: [fırsat]
```

---

### BÖLÜM 6: YARIN + AKSİYON

özet ve yarın ne yapacağız.

```markdown
## 6. sonuç

### özet

[3-4 cümle — piyasa + portföy + kritik noktalar]

### yarının aksiyonları

🔴 **hemen** (seans açılışta):
1. [aksiyon] — [sebep]

🟡 **izle** (seans içinde):
2. [koşul] → [aksiyon]

🟢 **pasif** (seviye bekle):
3. [sembol] $XXX'e gelirse → [değerlendir]

### sonraki güncelleme

[yarın sabah raporu / cumartesi haftalık / ay sonu aylık]

---

*finzora ai | fmp api | new york kapalı*
```

---

## JSON GÜNCELLEME KURALLARI

bu prompt'ta JSON'lar güncellenir. kurallar:

**pozisyon güncelleme** (her pozisyon için):
- `guncel_fiyat` = FMP quote price
- `gunluk_degisim_yuzde` = FMP changesPercentage
    ⚠️ changesPercentage seans dışında 0 dönebilir → manuel hesapla: ((price - previousClose) / previousClose) × 100
- `guncel_deger` = adet × guncel_fiyat
- `kar_zarar` = guncel_deger - yatirim
- `kar_zarar_yuzde` = (kar_zarar / yatirim) × 100
- `agirlik_yuzde` = (guncel_deger / toplam_deger) × 100
- `son_guncelleme` = şu anın timestamp'i

**portföy toplamları**:
- `toplam_deger` = tüm pozisyonların guncel_deger toplamı + nakit
- `toplam_getiri_yuzde` = ((toplam_deger - baslangic_sermaye) / baslangic_sermaye) × 100

**swing güncelleme (v2.3 chandelier)**:
- `guncel_fiyat`, `guncel_kar_zarar_yuzde`, `tutulan_gun` güncelle
- ichimoku seviyeleri + ATR(14) yeniden hesapla (FMP historical data ile)
  → chandelier stop güncelle: highest_high - 3×ATR(14) (stop ASLA aşağı çekilmez)
  → highest_high yenilendi mi? ATR değişti mi? → stop yeniden hesapla
  → çıkış sinyali var mı? chandelier tetiklendi, TK cross aşağı, kumo'ya giriş
  → rapora chandelier değişimi yaz (önceki seansla karşılaştır)

**doğrulama**:
- yatirim = adet × maliyet_baz (sabit, değişmemeli)
- toplam_deger = sum(pozisyonlar) + nakit
- ağırlık toplamı ≈ %100
- summary.json = portföyler toplamı

**after-hours kontrol**:
- portföy/swing hissesinde >%3 AH hareket → raporda belirt

---

## KALİTE KONTROL

rapor tamamlandığında kontrol et:

- [ ] tüm bölümler (1, 2, 3, 4, 5, 6) yazıldı mı?
- [ ] JSON'lar güncellenip push edildi mi?
- [ ] tüm semboller güncel fiyatla güncellendi mi?
- [ ] k/z hesaplamaları tutarlı mı?
- [ ] sabah planı değerlendirildi mi?
- [ ] kazanç açıklamaları tarandı mı? (portföy/watchlist kesişimi kontrol edildi mi?)
- [ ] aksiyon planı net ve uygulanabilir mi?
- [ ] TRADING_PLAYBOOK.md güncellendi mi? (yeni ders varsa kural/hata tablosuna eklendi mi?)
- [ ] rapor dosyası push edildi mi?

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
