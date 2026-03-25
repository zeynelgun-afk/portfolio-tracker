# GÜNLÜK RAPOR PART 2 — KAPANIŞ RAPORU v1.0

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt'taki her adım sırayla ve eksiksiz uygulanmalıdır. hiçbir adım atlanamaz, kısaltılamaz veya "sonra yaparım" diye ertelenmez. bir adımı tamamlamadan diğerine geçme.
>
> **zorunlu adımlar (teker teker kontrol et):**
> - [ ] ADIM 1 — git pull + hazırlık (JSON'ları oku, dünkü raporu kontrol et)
> - [ ] ADIM 2 — FMP veri toplama (batch-quote, portföy: RSI+SMA, swing: ichimoku, emtia, treasury)
> - [ ] ADIM 3 — JSON güncelleme (fiyatlar, k/z, ağırlıklar, summary.json, git commit)
> - [ ] ADIM 3.5 — KAZANÇ AÇIKLAMALARI TARAMASI (earnings-calendar, portföy kesişimi, detaylı analiz)
> - [ ] ADIM 4 — rapor yaz (BÖLÜM 1-6 eksiksiz)
> - [ ] BÖLÜM 1 — günün özeti (piyasa tablosu, sektörler, trend)
> - [ ] BÖLÜM 2 — portföy takibi (3 portföy + genel özet + uyarılar)
> - [ ] BÖLÜM 3 — swing trade durumu (aktif pozisyonlar, ichimoku kontrol)
> - [ ] BÖLÜM 4 — kazanç açıklamaları (bugünkü bilançolar, portföy kesişimi analizi)
> - [ ] BÖLÜM 5 — günün değerlendirmesi (sabah planı vs gerçekleşme, dersler)
> - [ ] BÖLÜM 6 — sonuç + yarın aksiyonları
> - [ ] ADIM 5 — PLAYBOOK GÜNCELLE (derslerden yeni kural varsa `docs/TRADING_PLAYBOOK.md`'ye ekle)
> - [ ] GIT — rapor + playbook commit + push yapıldı mı?
>
> **geçmiş hatalar**: bölüm 4 (kazanç açıklamaları) atlandı → Oracle bilançosu ($17.2B gelir, bulut +%84, AH +%6.3) rapordan tamamen eksik kaldı. bölüm 5 ve 6 da eksik yazıldı. bu tür atlamalar portföy kararlarını olumsuz etkiler. her bölümü tamamla.

> **versiyon**: 1.2 | **son güncelleme**: 25 mart 2026
> **çıktı dosyası**: `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~09:00 (NYSE dün gece 23:00'da kapandı, bugün 16:30 açılacak — yaz saati)
> **ön koşul**: part 1 (sabah raporu) aynı gün veya bir önceki gün çalıştırılmış olmalı
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

ADIM 2 — FMP VERİ TOPLAMA
  → batch-quote: tüm benzersiz semboller + SPY/QQQ/DIA/IWM
  → teknik göstergeler (portföy hisseleri): her sembol için RSI(14), SMA(50), SMA(200)
  → agresif portföy stopları: 2x ATR(14) trailing (FMP historical-price ile ATR hesapla)
  → swing pozisyonları için RSI/SMA çekilmez — ichimoku scripti (adım 3) bunu kapsar
  → emtia/döviz: GCUSD, CLUSD, EURUSD
  → treasury-rates

ADIM 3 — JSON GÜNCELLEME
  → her pozisyon: guncel_fiyat, gunluk_degisim_yuzde, guncel_deger, kar_zarar, kar_zarar_yuzde, agirlik_yuzde, son_guncelleme
  → portföy toplamları: toplam_deger, toplam_getiri_yuzde
  → swing: guncel_fiyat, guncel_kar_zarar_yuzde, tutulan_gun
  → swing ichimoku güncelleme: python scripts/swing_ichimoku.py --aktif
    (kijun trailing stop güncelleme, çıkış sinyali kontrolü, ichimoku seviyeleri)
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
      - watchlist.json sembolleriyle karşılaştır
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
  → reports/daily/DAILY_REPORT_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet"
  → TELEGRAM GÖNDERİMİ (git push'tan SONRA):
    1. python scripts/telegram_notify.py --type closing --theme "[günün özeti]"
    2. python scripts/telegram_notify.py --type report --file reports/daily/DAILY_REPORT_YYYY-MM-DD.md

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

**teknik uyarı kuralları**:
- RSI > 70 → overbought uyarısı
- RSI < 30 → oversold uyarısı
- fiyat > SMA → ✅, fiyat < SMA → ❌
- k/z > %20 + RSI > 75 → kar realizasyonu düşün
- k/z < -%8 → stop-loss değerlendir
- günlük değişim < -%5 → sert düşüş kontrolü

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

**durum belirleme (ichimoku v2)**:
- fiyat < kijun (%0.5+ fark) → 🔴 ÇIKIŞ SİNYALİ
- fiyat < kijun (<%0.5 fark) → ⚠️ YAKIN, yarın teyit
- tenkan < kijun (bearish TK cross) → 🔴 TREND DÖNÜŞÜ
- fiyat kumo'ya girdi → 🟡 KISMI ÇIKIŞ DÜŞÜN
- fiyat kumo üstü + tenkan > kijun → ✅ normal
- hacim ayrışması (düşen hacim + yükselen fiyat) → ⚠️ DİKKAT

```markdown
## 3. swing trade durumu

> ichimoku güncelleme: python scripts/swing_ichimoku.py --aktif

| id | sembol | giriş | güncel | k/z | kijun stop | kumo | tenkan/kijun | gün | durum |
|----|--------|-------|--------|-----|-----------|------|--------------|-----|-------|

**aktif**: X/8 | **ortalama k/z**: +%X.XX

**ichimoku değişimi** (önceki seans ile karşılaştır):
- [SEMBOL]: kijun $XX → $XX (stop güncellendi/korundu), çıkış sinyali: var/yok

**aksiyonlar**:
🔴 **hemen**: [SEMBOL] — [kijun altı kapanış / TK cross aşağı → çık]
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
- beklenti verisi: FMP `analyst-estimates` (en son çeyrek tahmini)
- gerçek veri: FMP `income-statement` (son çeyrek)
- kazanç sezonu dışında (Ocak/Nisan/Temmuz/Ekim arası) açıklama sayısı az olabilir — normal
- AH hareketi: web araması ile kapanış sonrası fiyat değişimi (FMP aftermarket-quote seans dışında sıfır dönüyor, kullanma)

---

### BÖLÜM 5: GÜNÜN DEĞERLENDİRMESİ

sabah raporundaki plan tuttu mu, dersler.

```markdown
## 5. günün değerlendirmesi

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
- `guncel_deger` = adet × guncel_fiyat
- `kar_zarar` = guncel_deger - yatirim
- `kar_zarar_yuzde` = (kar_zarar / yatirim) × 100
- `agirlik_yuzde` = (guncel_deger / toplam_deger) × 100
- `son_guncelleme` = şu anın timestamp'i

**portföy toplamları**:
- `toplam_deger` = tüm pozisyonların guncel_deger toplamı + nakit
- `toplam_getiri_yuzde` = ((toplam_deger - baslangic_sermaye) / baslangic_sermaye) × 100

**swing güncelleme (ichimoku v2)**:
- `guncel_fiyat`, `guncel_kar_zarar_yuzde`, `tutulan_gun` güncelle
- `python scripts/swing_ichimoku.py --aktif` çalıştır
  → kijun_sen, tenkan_sen, kumo_ust, kumo_alt, atr_14, hacim_oran, obv_trend güncelle
  → kijun yükseldi mi? evet → stop_loss yukarı çek (stop ASLA aşağı çekilmez)
  → çıkış sinyali var mı? kijun altı kapanış, TK cross aşağı, kumo'ya giriş
  → rapora ichimoku değişimi yaz (önceki seansla karşılaştır)

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
