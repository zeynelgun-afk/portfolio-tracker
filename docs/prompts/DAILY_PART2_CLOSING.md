# GÜNLÜK RAPOR PART 2 — KAPANIŞ RAPORU v1.0

> **versiyon**: 1.0 | **son güncelleme**: 3 mart 2026
> **çıktı dosyası**: `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~00:30-01:00 (NYSE az önce kapandı)
> **ön koşul**: part 1 (sabah briefing) aynı gün çalıştırılmış olmalı
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit 1**: `[GÜNCELLEME] DD Ay - kapanış fiyatları`
> **git commit 2**: `[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~00:30-01:00'da yazılır — NYSE az önce kapandı (00:00 TR)
- FMP fiyatları = bugünün kapanışı (kesinleşmiş)
- after-hours: 00:00-02:00 TR (şu an aktif olabilir)
- sabah briefingdeki plan bugünün seansında uygulandı

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
  → teknik göstergeler: her sembol için RSI(14), SMA(20), SMA(50), SMA(200)
  → emtia/döviz: GCUSD, CLUSD, EURUSD
  → treasury-rates

ADIM 3 — JSON GÜNCELLEME
  → her pozisyon: guncel_fiyat, gunluk_degisim_yuzde, guncel_deger, kar_zarar, kar_zarar_yuzde, agirlik_yuzde, son_guncelleme
  → portföy toplamları: toplam_deger, toplam_getiri_yuzde
  → swing: guncel_fiyat, guncel_kar_zarar_yuzde, tutulan_gun, stop/hedef kontrol
  → summary.json güncelle
  → doğrulama: yatirim = adet × maliyet_baz, toplam = sum(pozisyonlar) + nakit, ağırlık ≈ %100
  → GIT COMMIT + PUSH: "[GÜNCELLEME] DD Ay - kapanış fiyatları"

ADIM 4 — RAPOR YAZ
  → bölüm 1-5'i sırayla yaz (format aşağıda)
  → sabah briefingdeki planla karşılaştır (bölüm 4)
  → reports/daily/DAILY_REPORT_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet"
```

---

## RAPOR FORMATI

rapor 5 bölümden oluşur. github'a push edilir.

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

| sembol | fiyat | günlük | k/z | RSI | 20 | 50 | 200 | durum |
|--------|-------|--------|-----|-----|----|----|-----|-------|
| SM | $XX.XX | +X.X% | +X% | XX | ✅ | ✅ | ✅ | [not] |

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

aktif pozisyonlar, stop/hedef kontrolü, aksiyonlar.

**durum belirleme**:
- fiyat ≤ stop → 🔴 STOP TETİKLENDİ
- fiyat ≥ hedef → 🟢 HEDEF ULAŞILDI
- hedefe %5 kala → 🟡 HEDEFE YAKIN
- stop'a %2 kala → ⚠️ STOP YAKIN
- diğer → ✅ normal aralıkta

```markdown
## 3. swing trade durumu

| id | sembol | giriş | güncel | k/z | stop | hedef | gün | durum |
|----|--------|-------|--------|-----|------|-------|-----|-------|

**aktif**: X/10 | **ortalama k/z**: +%X.XX

**aksiyonlar**:
🔴 **hemen**: [SEMBOL] — [aksiyon + neden]
🟡 **izle**: [SEMBOL] koşul → aksiyon
✅ **sorunsuz**: [liste]

**istatistik**: toplam X trade | kazanç X (%XX) | kayıp X (%XX)
```

---

### BÖLÜM 4: DÜNÜN DEĞERLENDİRMESİ

sabah briefingdeki plan tuttu mu, dersler.

```markdown
## 4. günün değerlendirmesi

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

### BÖLÜM 5: YARIN + AKSİYON

özet ve yarın ne yapacağız.

```markdown
## 5. sonuç

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

[yarın sabah briefing / cumartesi haftalık / ay sonu aylık]

---

*finzora ai | fmp api | new york kapandı*
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

**swing güncelleme**:
- `guncel_fiyat`, `guncel_kar_zarar_yuzde`, `tutulan_gun` güncelle
- trailing stop sadece yukarı yönde güncellenir
- stop tetiklendi mi, hedef ulaşıldı mı kontrol et

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

- [ ] tüm bölümler (1-5) yazıldı mı?
- [ ] JSON'lar güncellenip push edildi mi?
- [ ] tüm semboller güncel fiyatla güncellendi mi?
- [ ] k/z hesaplamaları tutarlı mı?
- [ ] sabah planı değerlendirildi mi?
- [ ] aksiyon planı net ve uygulanabilir mi?
- [ ] rapor dosyası push edildi mi?

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
