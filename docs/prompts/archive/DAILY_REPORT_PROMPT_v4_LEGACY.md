# GÜNLÜK RAPOR PROMPT — v4.0

> **versiyon**: 4.0 | **son güncelleme**: 27 şubat 2026
> **çıktı dosyası**: `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~14:00 (NYSE dün 00:00'da kapandı, bugün 17:30 açılacak)
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~14:00'da yazılır — NYSE dün gece 00:00'da kapandı
- FMP fiyatları = dünün kapanışı (kesinleşmiş)
- after-hours: dün 00:00-02:00 TR
- pre-market: bugün 16:00-17:30 TR
- bugünün seansı: 17:30-00:00 TR

---

## ÇALIŞMA AKIŞI

bu prompt tek seferde çalışır. adımları sırayla takip et, araya durma:

```
ADIM 1 — HAZIRLIK
  → git pull
  → dünkü raporu oku (DAILY_REPORT_{DÜN}.md), bölüm 7 aksiyon planını not al
  → tüm JSON dosyalarını oku (balanced, aggressive, dividend, swing/active)
  → benzersiz sembol listesi çıkar (3 portföy + swing + SPY)

ADIM 2 — FMP VERİ TOPLAMA
  → batch-quote: tüm benzersiz semboller
  → teknik göstergeler: her sembol için RSI(14), SMA(20), SMA(50), SMA(200)
  → piyasa: SPY/QQQ/DIA/IWM quote, GCUSD, CLUSD, EURUSD, treasury-rates
  → sektör: sector-performance-snapshot (date parametresi zorunlu)
  → piyasa genişliği: biggest-gainers, biggest-losers
  → earnings: earnings-calendar (bugün + 7 gün), analyst-estimates (portföy/swing hisseleri)
  → haberler: news/stock (portföy sembolleri), fmp-articles, upgrades-downgrades (kritik hisseler)

ADIM 3 — JSON GÜNCELLEME
  → her pozisyon: guncel_fiyat, gunluk_degisim_yuzde, guncel_deger, kar_zarar, kar_zarar_yuzde, agirlik_yuzde, son_guncelleme
  → portföy toplamları: toplam_deger, toplam_getiri_yuzde
  → swing: guncel_fiyat, guncel_kar_zarar_yuzde, tutulan_gun
  → summary.json güncelle
  → doğrulama: yatirim = adet × maliyet_baz, toplam = sum(pozisyonlar) + nakit, ağırlık ≈ %100
  → GIT COMMIT + PUSH: "[GÜNCELLEME] DD ay - kapanış fiyatları"

ADIM 4 — WEBSEARCH
  → futures ve pre-market durumu
  → dün gece / bugün sabah önemli piyasa haberleri
  → portföy hisselerini etkileyen gelişmeler
  → dün gece açıklanan earnings sonuçları (portföy/swing/majör)
  → bugünkü ekonomik veri takvimi
  → Fed faiz olasılıkları (Kalshi/Polymarket)

ADIM 5 — RAPOR YAZ
  → bölüm 1-7'yi sırayla yaz (format aşağıda)
  → reports/daily/DAILY_REPORT_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet"
```

---

## RAPOR FORMATI

rapor 7 bölümden oluşur. her bölümün formatı aşağıda tanımlıdır.

---

### BÖLÜM 1: PİYASA GÖRÜNÜMÜ

dünün kapanışı + bugünün beklentisi.

```markdown
## 1. piyasa — dün + bugün

### dünün kapanışı ({tarih}, {gün})

| ticker | kapanış | değişim | RSI | SMA50 | SMA200 |
|--------|---------|---------|-----|-------|--------|
| SPY | $XXX.XX | +X.XX% | XX.X | ✅/❌ | ✅/❌ |
| QQQ | $XXX.XX | +X.XX% | | | |
| VIX | XX.XX | +X.XX% | | | |

**emtia + döviz**: altın $X,XXX (±%), WTI $XX (±%), DXY XX.X, 10Y %X.XX

**trend**: [boğa/nötr/ayı] — SPY {SMA durumu}

### bugünün öncü göstergeleri

**futures** ({bugün sabah}):
- S&P 500: ±%X.XX | NASDAQ: ±%X.XX
- [kısa yorum — neden yukarı/aşağı]

### sektör performansı (dün)

en güçlü 3: [sektör +%], [sektör +%], [sektör +%]
en zayıf 3: [sektör -%], [sektör -%], [sektör -%]
rotasyon sinyali: [risk-on / risk-off / karışık]

### risk değerlendirmesi

- VIX: XX.X → [risk-on/off/nötr]
- breadth: gainers/losers oranı → [güçlü/zayıf]
- prediction markets: Kalshi Fed faiz %XX, [diğer önemli]

### strateji notu

[2-3 cümle — bugünün seansı için yön]
```

---

### BÖLÜM 2: HABER VE YORUM ANALİZİ

piyasa haberleri, portföy haberleri, analist notları, makro yorum.

**veri kaynakları**: FMP news/stock, fmp-articles, upgrades-downgrades + websearch

**sınıflandırma**:
- 🔴 acil: portföy hissesini doğrudan etkileyen
- 🟠 yüksek: sektörümüzü etkileyen
- 🟡 orta: genel piyasa
- 🟢 düşük: dolaylı etki

**her 🔴/🟠 haber için etki analizi**:
ne oldu → kimi etkiliyor → nasıl etkiliyor → ne yapmalı → zaman çerçevesi

```markdown
## 2. haber ve yorum analizi

### 🔴 portföyü doğrudan etkileyen

**[SEMBOL] — [başlık]** ([kaynak])
etki: [✅/❌/➡️] | portföy: [hangisi]
[2-3 cümle analiz]
aksiyon: [ne yapılacak]

(yoksa: "portföy hisselerinde doğrudan etki yaratacak gelişme yok")

### 🟠 sektör ve makro gelişmeler

| gelişme | etki | ilgili portföy | yorum |
|---------|------|----------------|-------|
| [başlık] | ✅/❌/➡️ | [portföy/hisse] | [1 cümle] |

### 📊 analist notları ve grade değişiklikleri

| tarih | sembol | kurum | önceki | yeni | hedef fiyat | yorum |
|-------|--------|-------|--------|------|-------------|-------|

(yoksa: "son 24 saatte portföy hisselerinde grade değişikliği yok")

### 🌍 makro yorum

[2-4 cümle — genel atmosfer, risk algısı, ana temalar]

### bugünün veri takvimi

| saat (TR) | veri | beklenti | önceki | potansiyel etki |
|-----------|------|----------|--------|-----------------|

(yoksa: "bugün önemli veri açıklaması yok")

### haber özeti skoru

📊 **genel sentiment**: [pozitif / negatif / nötr / karışık]
portföy etkisi: [olumlu / olumsuz / nötr] — [1 cümle gerekçe]
```

---

### BÖLÜM 3: PORTFÖY TAKİBİ

3 portföyün detay tablosu, uyarılar, aksiyonlar.

**teknik uyarı kuralları**:
- RSI > 70 → overbought uyarısı
- RSI < 30 → oversold uyarısı
- fiyat > SMA → ✅, fiyat < SMA → ❌
- k/z > %20 + RSI > 75 → kar realizasyonu düşün
- k/z < -%8 → stop-loss değerlendir
- günlük değişim < -%5 → sert düşüş kontrolü

```markdown
## 3. portföy takibi

### 3a. dengeli portföy ($100K başlangıç)

| sembol | fiyat | k/z | RSI | 20 | 50 | 200 | durum |
|--------|-------|-----|-----|----|----|-----|-------|
| SM | $XX.XX | +X% | XX | ✅ | ✅ | ✅ | [not] |

**toplam**: $XXX,XXX (+%X.XX) | **nakit**: $X,XXX | **pozisyon**: X
**portföy notu**: [1-2 cümle]

### 3b. agresif portföy ($100K başlangıç)

[aynı tablo formatı]

### 3c. temettü portföyü ($100K başlangıç)

[aynı tablo formatı]

### genel özet ($400K toplam)

**toplam değer**: $XXX,XXX | **k/z**: +$XX,XXX (+%X.XX) | **SPY**: +%X.XX | **alpha**: +%X.XX

### uyarı özeti

🔴 **acil**: [SEMBOL] — [neden]
⚠️ **izle**: [SEMBOL] — [neden]
🟢 **fırsat**: [SEMBOL] — [neden]
```

---

### BÖLÜM 4: SWING TRADE

aktif pozisyonlar, stop/hedef kontrolü, aksiyonlar.

**durum belirleme**:
- fiyat ≤ stop → 🔴 STOP TETİKLENDİ
- fiyat ≥ hedef → 🟢 HEDEF ULAŞILDI
- hedefe %5 kala → 🟡 HEDEFE YAKIN
- stop'a %2 kala → ⚠️ STOP YAKIN
- diğer → ✅ normal aralıkta

```markdown
## 4. swing trade durumu

| id | sembol | giriş | güncel | k/z | stop | hedef | gün | durum |
|----|--------|-------|--------|-----|------|-------|-----|-------|

**aktif**: X/10 | **ortalama k/z**: +%X.XX

**aksiyonlar**:

🔴 **hemen**: [SEMBOL] — [aksiyon + neden]
🟡 **izle**: [SEMBOL] koşul → aksiyon
✅ **sorunsuz**: [liste]

**watchlist**: [kısa liste]

**istatistik**: kazanç X/X (%XX) | kayıp X/X (%XX) | win rate %XX
```

---

### BÖLÜM 5: EARNINGS TAKVİMİ

dün gece sonuçları + bugün + haftalık.

**earnings analiz çerçevesi**:

her earnings için şu soruları sor:
1. beat/miss oranı nedir? (EPS ve gelir ayrı ayrı)
2. guidance yükseltildi mi, korundu mu, düşürüldü mü?
3. beklenti çıtası ne kadar yüksekti? (son 90 gün revizyon yönü)
4. hisse bilanço öncesi 30 günde ne kadar hareket etti? (fiyatlanmış mı?)
5. AH ve pre-market tepkisi tutarlı mı?

**tepki kuralları**:
- beat + guidance yükseltildi = en güçlü sinyal
- beat + guidance korundu = nötr (piyasa daha fazlasını istiyordu olabilir)
- beat + guidance düşürüldü = tehlikeli (rakamlar iyi ama gelecek kötü)
- zayıf beat + yüksek çıta = "sell the news" riski
- düşürülen çıtayı aşmak = yanıltıcı beat

**pre-market > after-hours**: AH düşük hacimli ve abartılı olabilir. PM kurumsal oyuncular devrede, gece boyu analist notları sindirilmiş — daha güvenilir sinyal.

```markdown
## 5. earnings takvimi

### dün gece (AMC) — sonuçlar

SEMBOL — [şirket]
  EPS:       $X.XX vs beklenti $X.XX → beat/miss %X
  gelir:     $X.XXB vs beklenti $X.XXB → beat/miss %X
  guidance:  [yükseltildi / korundu / düşürüldü / verilmedi]
  çıta:      [yüksek / orta / düşük] | revizyon: [↑/→/↓]
  beat kalitesi: [güçlü / zayıf / yanıltıcı]
  AH: $XXX (±%X) | PM: $XXX (±%X)
  tepki: [pozitif / nötr / negatif — neden]
  portföy etkisi: [doğrudan/dolaylı — hangi hisse, aksiyon]

### bugün

**BMO** (16:30 TR öncesi): [SEMBOL] — EPS beklentisi $X.XX
**AMC** (23:00+ TR): [SEMBOL] — EPS beklentisi $X.XX

### haftalık kritik

| tarih | sembol | timing | portföy etkisi |
|-------|--------|--------|----------------|
```

---

### BÖLÜM 6: DÜNÜN DEĞERLENDİRMESİ

dünkü raporun aksiyon planı tuttu mu, dersler.

```markdown
## 6. dünün değerlendirmesi

### plan gerçekleşme

| aksiyon | plan | sonuç | not |
|---------|------|-------|-----|
| [ne] | [plan] | ✅/❌/⏳ | [açıklama] |

### dünün performansı

- toplam: $XXX,XXX (+%X.XX)
- SPY: +%X.XX → alpha: +%X.XX
- en iyi: SEMBOL (+%X.XX) — [neden]
- en kötü: SEMBOL (-%X.XX) — [neden]

### dersler

- ✅ doğru karar: [ne, neden doğru]
- ❌ yanlış karar: [ne, neden yanlış, sonraki sefere ne farklı]
- 🔍 kaçırılan: [ne oldu, neden girilmedi]
```

---

### BÖLÜM 7: SONUÇ + AKSİYON

özet ve bugün ne yapacağız.

```markdown
## 7. sonuç

### özet

[3-4 cümle — piyasa + portföy + kritik noktalar]

### bugünün aksiyonları

🔴 **hemen** (seans açılışta):
1. [aksiyon] — [sebep + hedef]

🟡 **izle** (seans içinde):
2. [koşul] → [aksiyon]

🟢 **pasif** (seviye bekle):
3. [sembol] $XXX'e gelirse → [değerlendir]

### sonraki güncelleme

[yarın günlük rapor / cumartesi haftalık / ay sonu aylık]

---

*finzora ai | fmp api | new york kapalı*
```

---

## JSON GÜNCELLEME KURALLARI

rapor yazılmadan önce JSON'lar güncellenir. kurallar:

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

**doğrulama**:
- yatirim = adet × maliyet_baz (sabit, değişmemeli)
- toplam_deger = sum(pozisyonlar) + nakit
- ağırlık toplamı ≈ %100
- summary.json = 3 portföy toplamı

**after-hours kontrol**:
- portföy/swing hissesinde >%3 AH hareket → raporda belirt
- dün gece earnings açıklayan portföy/swing hissesi → bölüm 5'te detaylandır

---

## KALİTE KONTROL

rapor tamamlandığında kontrol et:

- [ ] tüm bölümler (1-7) yazıldı mı?
- [ ] JSON'lar güncellenip push edildi mi?
- [ ] tüm semboller güncel fiyatla güncellendi mi?
- [ ] k/z hesaplamaları tutarlı mı?
- [ ] earnings formatı doğru ve eksiksiz mi?
- [ ] haber bölümü etki analizi veri destekli mi?
- [ ] aksiyon planı net ve uygulanabilir mi?
- [ ] rapor push edildi mi?

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
