# GÜNLÜK RAPOR MASTER PROMPT — v3.2

> ⚠️ **ÇALIŞMA MODU**: Bu prompt FAZ FAZ işlenir. Tüm fazları tek seferde yapmaya ÇALIŞMA.
>
> **FAZ SIRASI**:
> 1. FAZ 0 → repo oku, dünkü raporu değerlendir (commit yok)
> 2. FAZ 1 → FMP veri çek + JSON güncelle + git push  
> 3. FAZ 2 → piyasa analizi + raporu yaz + git push

---

> **versiyon**: 3.4 | **son güncelleme**: 27 şubat 2026
> **çıktı dosyası**: `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~14:00 (NYSE dün kapandı, bugün 17:30 açılacak)
> **dil**: küçük harf türkçe ama **dilbilgisi kurallarına uygun** (cümle başı büyük, cümle sonu nokta, şirket/ticker tutarlı)
> **kaynak**: sadece "finzora ai"
> **git commit**: `[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet`

**⚠️ ZAMAN BİLİNCİ**:
- rapor TR ~14:00'da yazılır — NYSE dün 00:00'da kapandı, bugün 17:30'da açılacak
- FMP fiyatları = dünün kapanışı (kesinleşmiş)
- after-hours: dün 00:00-02:00 TR arası
- pre-market: bugün 16:00-17:30 TR
- bugünün seansı 17:30-00:00 TR

**BU PROMPT 3 İŞİ YAPAR**:
1. dünün değerlendirmesi (plan tuttu mu, dersler)
2. JSON final güncelleme (kapanış fiyatı)
3. bugünün plan (futures, haberler, aksiyonlar)

---

## GENEL BAKIŞ

| bölüm | içerik | FMP | websearch |
|-------|--------|-----|-----------|
| 0. değerlendirme | plan tuttu mu, dersler, JSON | 0* | 0-1 |
| 1. piyasa | kapanış, futures, sektör, risk | ~12 | 5-7 |
| 2. portföy | 3 portföy detay, RSI, SMA | ~73 | 0 |
| 3. swing | stop/hedef, aksiyonlar | 0* | 0 |
| 4. earnings | dün gece, bugün, haftalık | 5-15 | 3-6 |
| 5. sonuç | özet + aksiyon planı | 0 | 0 |
| **toplam** | | **~20-30** | **8-14** |

*bölüm 0 ve 3 verileri bölüm 1-2'de zaten çekilir

**API bütçesi**: ~190 / 2,500 = %7.6 (güvenli)

---

## ÇALIŞTIRMA ADIM SIRASI

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAZ 0 — OKUMA (commit yok)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ git pull
→ dünkü raporu oku (DAILY_REPORT_{DÜN}.md)
→ plan tuttu mu değerlendir
→ sohbette özet ver, "faz 1'e geç" de

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAZ 1 — VERİ + JSON GÜNCELLEME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ JSON dosyalarını oku
→ benzersiz sembol listesi çıkar
→ FMP batch-quote + teknik göstergeler
→ JSON güncelle + doğrula
→ summary.json güncelle
→ GIT COMMIT + PUSH: "[GÜNCELLEME] DD ay - kapanış"
→ "faz 2'ye geç" de

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAZ 2 — RAPOR YAZMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ websearch: futures, sektör, haberler
→ bölüm 0-5'i yaz
→ raporu kaydet
→ GIT COMMIT + PUSH: "[GÜNLÜK RAPOR] DD ay - özet"
```

---

## BENZERSİZ SEMBOL LİSTESİ

```python
import json

semboller = set()

# 3 portföyden
for dosya in ["balanced.json", "aggressive.json", "dividend.json"]:
    with open(f"data/portfolios/{dosya}") as f:
        for pos in json.load(f)['pozisyonlar']:
            semboller.add(pos['sembol'])

# swing aktif
with open("data/swing/active.json") as f:
    for pos in json.load(f)['aktif_pozisyonlar']:
        semboller.add(pos['sembol'])

semboller.add("SPY")
benzersiz = sorted(semboller)
```

---
---

# BÖLÜM 0: KAPANIŞ DEĞERLENDİRMESİ

> **amaç**: dünkü seans değerlendirmesi, plan kontrolü, JSON güncelleme

## ADIM 1 — DÜNKÜ RAPORU OKU

```
1. reports/daily/DAILY_REPORT_{DÜN}.md'yi aç
2. bölüm 5'teki aksiyon planını bul
3. uygulandı mı kontrol et
```

## ADIM 2 — PLAN DEĞERLENDİRMESİ

```markdown
## 0. dünün değerlendirmesi

### plan gerçekleşme

| aksiyon | plan | sonuç | not |
|---------|------|-------|-----|
| [acil] | [ne planlandı] | ✅/❌/⏳ | [açıklama] |

### dünün performans

- toplam: $XXX,XXX (+%X.XX)
- SPY: +%X.XX → alpha: +%X.XX  
- en iyi: SEMBOL (+%X.XX) — [neden]
- en kötü: SEMBOL (-%X.XX) — [neden]

### dersler

- ✅ doğru karar: [ne yapıldı, neden doğru]
- ❌ yanlış karar: [ne yapıldı, neden yanlış, sonraki sefere ne farklı]
- 🔍 kaçırılan: [ne oldu, neden girilmedi]
```

## ADIM 3 — JSON GÜNCELLEME

### 3a. portföy JSON

```python
for pozisyon in portfolio['pozisyonlar']:
    pozisyon['guncel_fiyat'] = quote['price']
    pozisyon['gunluk_degisim_yuzde'] = quote['changesPercentage']
    pozisyon['guncel_deger'] = pozisyon['adet'] * pozisyon['guncel_fiyat']
    pozisyon['kar_zarar'] = pozisyon['guncel_deger'] - pozisyon['yatirim']
    pozisyon['kar_zarar_yuzde'] = (pozisyon['kar_zarar'] / pozisyon['yatirim']) * 100
    pozisyon['son_guncelleme'] = datetime.now().isoformat()

toplam = sum(p['guncel_deger'] for p in pozisyonlar) + nakit
portfolio['toplam_deger'] = toplam
portfolio['toplam_getiri_yuzde'] = ((toplam - 100000) / 100000) * 100

for pozisyon in portfolio['pozisyonlar']:
    pozisyon['agirlik_yuzde'] = (pozisyon['guncel_deger'] / toplam) * 100
```

### 3b. swing active.json

```python
for pozisyon in aktif_pozisyonlar:
    pozisyon['guncel_fiyat'] = quote['price']
    pozisyon['guncel_kar_zarar_yuzde'] = ((guncel - giris) / giris) * 100
    pozisyon['tutulan_gun'] = (today - giris_tarihi).days
    
    # trailing stop (sadece yukarı)
    if guncel > önceki_zirve:
        yeni_trailing = guncel * 0.95
        if yeni_trailing > mevcut_trailing:
            trailing_stop = yeni_trailing
```

### 3c. summary.json

```python
summary['toplam_deger'] = dengeli + agresif + temettü
summary['toplam_kar_zarar_yuzde'] = ((toplam_deger - 400000) / 400000) * 100
summary['alpha'] = toplam_kar_zarar_yuzde - benchmark_spy
```

### 3d. doğrulama

```
KATMAN 1 — VERİ:
✓ batch-quote yanıtları dolu mu?
✓ fiyatlar > 0 ve mantıklı mı?
✓ |change%| > %20 → haber kontrolü
✓ tarih dünün tarihi mi?

KATMAN 2 — TUTARLILIK:
✓ yatirim = adet × maliyet_baz
✓ guncel_deger = adet × guncel_fiyat
✓ kar_zarar = guncel_deger - yatirim
✓ toplam_deger = sum(guncel) + nakit
✓ ağırlık toplamı ≈ %100
✓ summary = 3 portföy toplamı
✓ son_guncelleme bugün
```

### 3e. after-hours

```
- dün AMC earnings portföy/swing hissesi?
- after-hours > %3 portföy hissesi?
- after-hours > %5 swing hissesi?
→ not düş, bölüm 2-3'te belirt
```

## ADIM 4 — DÜN GECE EARNINGS

### 4a. hangi earnings

```
- portföy hisselerinden dün AMC açıklayan
- swing hisselerinden dün AMC açıklayan
- majör tech (NVDA, GOOGL, MSFT, META, AMZN)
- finans liderleri (JPM, GS, BAC)
```

### 4b. veri toplama

```python
# FMP earnings calendar
earnings = fmp_get("earnings-calendar", {"from": dün, "to": dün})
AMC_earnings = [e for e in earnings if e['time'] == 'amc']

# her sembol için estimates
for sym in AMC_earnings:
    estimates = fmp_get("analyst-estimates", {"symbol": sym, "period": "quarter", "limit": 1})
```

### 4c. earnings formatı

```markdown
SEMBOL — [şirket adı]
  EPS:       $X.XX vs beklenti $X.XX → beat/miss %X
  gelir:     $X.XXB vs beklenti $X.XXB → beat/miss %X
  guidance:  yükseltildi / korundu / düşürüldü / verilmedi
  
  beklenti kalitesi:
  - konsensüs çıtası: yüksek / orta / düşük
  - son 90 gün revizyon: yukarı ↑ / sabit → / aşağı ↓
  - whisper: konsensüsün üstünde/altında (varsa)
  - beat kalitesi: [güçlü / zayıf / yanıltıcı]
  
  piyasa tepkisi:
  - AH fiyat: $XXX (±%X)
  - pre-market: $XXX (±%X) [ertesi sabah]
  - tepki yorumu: [pozitif / nötr / negatif — neden]
  
  etki:
  - portföy: [doğrudan/dolaylı — hangi hisse]
  - sektör: [pozitif/negatif/nötr — neden]
  - aksiyon: [tut/ekle/azalt/izle]
```

**⚠️ BEKLENTİ KALİTESİ ANALİZİ — KURALLAR**:

piyasa sadece "beat mi miss mi" sorusuna cevap aramaz. asıl soru şudur:
**"beklentiler ne kadar yüksekti ve beat gerçekten kaliteli mi?"**

| durum | beat | beklenti çıtası | piyasa tepkisi | örnek |
|-------|------|-----------------|----------------|-------|
| güçlü beat | evet (%5+) | düşük-orta | 🟢 güçlü yükseliş | düşük beklentiyi aşan sürpriz |
| zayıf beat | evet (<%3) | zaten yüksek | 🔴 satış ("sell the news") | NVDA Şub 2026 |
| yanıltıcı beat | evet | aşağı revize edilmiş | 🔴 satış | düşürülen çıtayı aşmak kolay |
| kaliteli miss | hayır | çok yüksek | 🟡 sınırlı düşüş | beklentiler şişmişti |
| gerçek miss | hayır | orta-düşük | 🔴 sert satış | gerçek sorun var |

**kontrol adımları**:

```
1. son 90 günde analist tahminleri yukarı mı aşağı mı revize edildi?
   → yukarı: çıta yüksek, beat zor → beat gelse bile "priced in" riski
   → aşağı: çıta düşük, beat kolay → beat gelse bile "düşürülen çıtayı aşmak" riski
   → sabit: normal beklenti → beat/miss gerçek sinyal

2. hisse bilanço öncesi son 30 günde ne kadar yükseldi?
   → %10+ yükseliş: piyasa zaten fiyatladı → beat = "sell the news"
   → düz/düşüş: beklenti düşük → beat = gerçek sürpriz potansiyeli

3. guidance kalitesi:
   → beat + guidance yükseltildi = en güçlü sinyal
   → beat + guidance korundu = nötr (piyasa daha fazlasını istiyordu)
   → beat + guidance düşürüldü = 🔴 en tehlikeli (rakamlar iyi ama gelecek kötü)

4. whisper number (piyasanın gerçek beklentisi):
   → konsensüs vs whisper farkı büyükse, whisper'ı baz al
   → websearch ile "SEMBOL earnings whisper" kontrol et
```

**⚠️ PRE-MARKET FİYATLAMA — KURALLAR**:

after-hours tepkisi ile pre-market tepkisi farklı olabilir. her ikisi de raporlanmalı:

```
1. AH tepkisi (dün gece 00:00-02:00 TR):
   → ilk refleks, düşük hacim, manipülasyona açık
   → genelde abartılı (hem yukarı hem aşağı)

2. pre-market tepkisi (bugün 16:00-17:30 TR):
   → kurumsal oyuncular devrede, daha güvenilir sinyal
   → gece boyu analist notları hazırlanmış, piyasa sindirmiş
   → AH ile PM arasındaki fark önemli:
     - AH +%5 → PM +%2 = "ilk heyecan soğudu, temkinli ol"
     - AH -%3 → PM +%1 = "piyasa abarttı, toparlanma sinyali"
     - AH +%2 → PM +%5 = "analist yükseltmeleri geldi, momentum güçlü"

3. hacim kontrolü:
   → PM hacmi normalin 2x+ ise → güçlü sinyal
   → PM hacmi düşükse → güvenilirliği düşük, seans açılışını bekle
```

**örnek — "beat ama sat" senaryosu (NVDA Şub 2026)**:
```
NVDA — NVIDIA
  EPS:       $1.62 vs beklenti $1.53 → beat %5.9
  gelir:     $68.1B vs beklenti $66.2B → beat %2.9
  guidance:  Q1 $78B — güçlü
  
  beklenti kalitesi:
  - konsensüs çıtası: çok yüksek (son 90g sürekli yukarı revizyon ↑)
  - hisse bilanço öncesi 30g: +%12 yükselmiş (fiyatlanmış)
  - whisper: $1.65+ (konsensüs $1.53'ün çok üstünde)
  - beat kalitesi: zayıf — konsensüsü aştı ama whisper'ı tutturamadı

  piyasa tepkisi:
  - AH fiyat: +%0.5 (soğuk karşılandı)
  - pre-market: -%2 (analist notları: "peak margins" endişesi)
  - tepki yorumu: negatif — "sell the news", çıta zaten çok yüksekti

  etki:
  - portföy: dolaylı — PLTR, ANET basınç altında
  - sektör: AI/chip "priced in" sinyali, yazılıma rotasyon başlayabilir
  - aksiyon: tech pozisyonlarında savunmacı kal
```

**örnek — "beat ve uç" senaryosu (DELL Şub 2026)**:
```
DELL — Dell Technologies
  EPS:       $3.89 vs beklenti $3.53 → beat %10.2
  gelir:     $33.4B vs beklenti $31.7B → beat %5.4
  guidance:  FY27 $138-142B (konsensüsün çok üstünde)

  beklenti kalitesi:
  - konsensüs çıtası: orta (son 90g hafif yukarı revizyon ↑)
  - hisse bilanço öncesi 30g: -%5 düşmüş (beklenti düşük)
  - beat kalitesi: güçlü — hem konsensüsü hem whisper'ı aştı

  piyasa tepkisi:
  - AH fiyat: +%8
  - pre-market: +%12 (analist yükseltmeleri peş peşe)
  - tepki yorumu: pozitif — düşük beklenti + güçlü beat = gerçek sürpriz

  etki:
  - portföy: dolaylı — AI altyapı tezi güçlendi (ANET destekler)
  - sektör: sunucu/altyapı güçlü, yazılım AI harcaması devam
  - aksiyon: ANET tut, altyapı teması izle
```

### 4d. derinlemesine analiz

**yapılır** (kazanç çağrısı takip et):
- portföy hissesi ise
- > %5 AH hareket varsa
- sektör katalizörü ise (NVDA gibi)

**yapılmaz**:
- minör beat/miss <%3
- low-volume AH
- portföyümüzle ilgisiz

---
---

# BÖLÜM 1: PİYASA GÖRÜNÜMÜ

> **amaç**: dün kapanış + bugün beklentisi

## ADIM 1 — VERİ TOPLAMA

### 1a. FMP API (~12 call)

```python
API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
BASE = "https://financialmodelingprep.com/stable"

# endeks (1)
batch = fmp_get("batch-quote", {"symbols": "SPY,QQQ,DIA,IWM"})

# emtia (2)
gold = fmp_get("quote", {"symbol": "GCUSD"})
oil = fmp_get("quote", {"symbol": "CLUSD"})

# forex (2)
dxy = fmp_get("quote", {"symbol": "DX-Y.NYB"})
eurusd = fmp_get("quote", {"symbol": "EURUSD"})

# tahvil (1)
treasury = fmp_get("treasury-rates", {"from": dün, "to": dün})

# sektör (1)
from datetime import datetime
dün_tarih = (datetime.now() - timedelta(1)).strftime("%Y-%m-%d")
sectors = fmp_get("sector-performance-snapshot", {"date": dün_tarih})

# SPY teknik (3)
spy_rsi = fmp_get("technical-indicators/rsi", {"symbol": "SPY", "periodLength": 14, "timeframe": "1day"})
spy_sma50 = fmp_get("technical-indicators/sma", {"symbol": "SPY", "periodLength": 50, "timeframe": "1day"})
spy_sma200 = fmp_get("technical-indicators/sma", {"symbol": "SPY", "periodLength": 200, "timeframe": "1day"})

# piyasa genişliği (2) 
gainers = fmp_get("biggest-gainers", {"limit": 20})
losers = fmp_get("biggest-losers", {"limit": 20})
```

### 1b. WebSearch (5-7 call)

```
1. "S&P 500 futures pre-market [BUGÜN]"
2. "NASDAQ futures [BUGÜN]"
3. "stock market news [BUGÜN]"
4. "sector performance [DÜN]"
5. "Fed rate cut probability [BUGÜN]" (Kalshi/Polymarket)
6. [kritik hisse] earnings [DÜN gece] (gerekirse)
7. geopolitical risk [BUGÜN] (gerekirse)
```

### 1c. prediction markets

```
- Kalshi: Fed faiz indirimi olasılığı
- Polymarket: resesyon, seçim, kripto
→ piyasa duyarlılığı için kullan
```

## ADIM 2 — ANALİZ KURALLARI

### risk duyarlılığı

```python
if VIX < 15:
    risk = "risk-on"
elif VIX < 20:
    risk = "nötr"
elif VIX < 30:
    risk = "risk-off"
else:
    risk = "panik"
```

### S&P 500 trend

```python
SPY_price = quote['price']
if SPY_price > SMA200:
    trend = "boğa 📈"
elif SPY_price > SMA50:
    trend = "nötr ➡️"
else:
    trend = "ayı ⛔"
```

### sektör göreceli güç

```python
sectors_sorted = sorted(sectors, key=lambda x: x['change'], reverse=True)
strongest_3 = sectors_sorted[:3]
weakest_3 = sectors_sorted[-3:]

# sektör rotasyon sinyali
if "Technology" in strongest_3 and "Utilities" in weakest_3:
    rotation = "risk-on / büyüme"
elif "Utilities" in strongest_3 and "Technology" in weakest_3:
    rotation = "risk-off / savunma"
```

## ADIM 3 — RAPOR FORMATI

```markdown
## 1. piyasa — dün + bugün

### dünün kapanışı ({dün tarihi}, {gün})

| ticker | kapanış | değişim | RSI | SMA50 | SMA200 |
|--------|---------|---------|-----|-------|--------|
| SPY | $XXX.XX | +X.XX% | XX.X | ✅/❌ | ✅/❌ |
| QQQ | $XXX.XX | +X.XX% | - | - | - |
| VIX | XX.XX | +X.XX% | - | - | - |

**trend**: [boğa/nötr/ayı] — SPY {SMA50/200 üzeri/altı}

### bugünün öncü göstergeleri

**pre-market futures** ({bugün sabah}):
- S&P 500: [+%X.XX / -%X.XX]
- NASDAQ: [+%X.XX / -%X.XX]
- [websearch sonuçları]

### sektör performansı (dün)

**en güçlü**:
1. [Sektör] +X.XX%
2. [Sektör] +X.XX%
3. [Sektör] +X.XX%

**en zayıf**:
1. [Sektör] -X.XX%
2. [Sektör] -X.XX%
3. [Sektör] -X.XX%

**sektör rotasyon sinyali**: [risk-on/risk-off/karışık]

### piyasa hareketi

- gainers/losers oranı: XX / XX
- breadth: [güçlü/zayıf]

### risk değerlendirmesi

- VIX: XX.X → [risk-on/off/nötr]
- DXY: XX.X → [dolar güçlü/zayıf]
- 10Y: X.XX% → [tahvil akışı var/yok]

### gece gelişmeleri + bugünün beklentisi

[websearch sonuçları — 3-4 madde]

### prediction markets sinyalleri

**Kalshi**:
- Fed faiz indirimi (mart): %XX
- resesyon (6 ay): %XX

**Polymarket**:
- [önemli olay]: %XX

### strateji notu

[bugünün seansı için 2-3 cümle yön]
```

---
---

# BÖLÜM 2: PORTFÖY TAKİBİ

> **amaç**: 3 portföy detay, uyarılar, aksiyonlar

## ADIM 1 — SEMBOL LİSTESİ

benzersiz sembol listesi (yukarıda tanımlı) kullanılır

## ADIM 2 — VERİ TOPLAMA

```python
# batch quote (1 call)
quotes = fmp_get("batch-quote", {"symbols": ",".join(benzersiz)})

# her sembol için RSI + SMA (her sembol 4 call)
for sym in benzersiz:
    rsi14 = fmp_get("technical-indicators/rsi", {"symbol": sym, "periodLength": 14, "timeframe": "1day"})
    sma20 = fmp_get("technical-indicators/sma", {"symbol": sym, "periodLength": 20, "timeframe": "1day"})
    sma50 = fmp_get("technical-indicators/sma", {"symbol": sym, "periodLength": 50, "timeframe": "1day"})
    sma200 = fmp_get("technical-indicators/sma", {"symbol": sym, "periodLength": 200, "timeframe": "1day"})
```

**tahmini call**: benzersiz sembol sayısı × 4 + 1 (batch)
- örnek: 18 sembol → 18×4+1 = 73 call

## ADIM 3 — UYARI KURALLARI

```python
# RSI
if rsi < 30: rsi_durum = "oversold ⚠️"
elif rsi > 70: rsi_durum = "overbought ⚠️"
else: rsi_durum = str(round(rsi, 1))

# SMA
sma20_ok = "✅" if guncel > sma20 else "❌"
sma50_ok = "✅" if guncel > sma50 else "❌"
sma200_ok = "✅" if guncel > sma200 else "❌"

# kar/zarar
if kar_zarar_pct > 20 and rsi > 75:
    uyari = "🟡 kar realizasyonu düşünülebilir"
elif kar_zarar_pct < -8:
    uyari = "🔴 stop-loss yakın, değerlendir"
elif gunluk_degisim < -5:
    uyari = "🔴 sert düşüş, kontrol et"
```

## ADIM 4 — RAPOR FORMATI

### her portföy için tablo

```markdown
## 2. portföy takibi

### 2a. dengeli portföy ($100K başlangıç)

| sembol | fiyat | k/z | RSI | 20 | 50 | 200 | durum |
|--------|-------|-----|-----|----|----|-----|-------|
| SM | $XX.XX | +X% | XX | ✅ | ✅ | ✅ | [not] |
| KOS | $XX.XX | +X% | XX | ✅ | ❌ | ❌ | [not] |

**toplam**: $XXX,XXX (+%X.XX) | **nakit**: $X,XXX | **pozisyon**: X

**portföy notu**: [bugüne özel 1-2 cümle yorum]

**sektör dağılımı**:
- Enerji: XX% (SM, XLE)
- [diğerleri]

**uyarılar**:
- 🔴 [kritik — hemen aksiyon]
- 🟡 [izlenmeli]
- ✅ [sorunsuz]
```

*[agresif, temettü için tekrar]*

### genel özet

```markdown
### uyarı özeti

🔴 **acil**:
- [SEMBOL] — [neden]

⚠️ **izle**:
- [SEMBOL] — [neden]

🟢 **fırsat**:
- [SEMBOL] — [neden]
```

## ADIM 5 — AKSİYON

```
RSI > 75 + k/z > %20  → kısmi kar düşün
RSI < 30 + trend ✅   → ek alım fırsatı
RSI < 30 + trend ⛔   → bıçak düşerken tutma
günlük -%5+           → stop kontrol
haftalık -%10+        → tez değerlendir
fiyat < SMA200 + RSI < 35 → destek kırılmış
nakit > %50 (agresif) → kademeli giriş planla
```

---
---

# BÖLÜM 3: SWING TRADE

> **amaç**: aktif pozisyonlar stop/hedef, aksiyonlar

## ADIM 1 — VERİ

swing sembolleri bölüm 2'de zaten çekildi (ekstra call yok)

## ADIM 2 — KONTROL

```python
for pozisyon in aktif_pozisyonlar:
    kar_zarar_pct = ((guncel - giris) / giris) * 100
    stop_mesafe_pct = ((guncel - stop) / guncel) * 100
    hedef_mesafe_pct = ((hedef - guncel) / guncel) * 100
    tutulan_gun = (bugun - giris_tarihi).days
    
    # durum
    if guncel <= stop: durum = "🔴 STOP TETİKLENDİ"
    elif guncel >= hedef: durum = "🟢 HEDEF ULAŞILDI"
    elif guncel >= hedef * 0.95: durum = "🟡 HEDEFE YAKIN"
    elif stop_mesafe_pct < 2: durum = "⚠️ STOP YAKIN"
    elif tutulan_gun > 10: durum = "⏰ SÜRE AŞIMI YAKLAŞIYOR"
    else: durum = "✅ normal aralıkta"
```

## ADIM 3 — RAPOR FORMATI

```markdown
## 3. swing trade durumu

| id | sembol | giriş | güncel | k/z | stop | hedef | gün | durum |
|----|--------|-------|--------|-----|------|-------|-----|-------|
| 001 | NEM | $118 | $125 | +5.9% | $112 | $130 | 7 | ✅ |
| 002 | T | $28.5 | $27.8 | -2.5% | $27 | $31.5 | 8 | ⚠️ stop yakın |

**aktif**: X/10 | **ortalama**: +%X.XX

**aksiyonlar**:

🔴 **hemen**:
- [SEMBOL] — [aksiyon + neden]

🟡 **izle**:
- [SEMBOL] koşul → aksiyon

✅ **sorunsuz**:
- [liste]

**watchlist**:
- [sembol] — [giriş seviyesi]

**istatistik**:
- kazanç: X/X (%XX)
- kayıp: X/X (%XX)
- win rate: %XX
```

---
---

# BÖLÜM 4: EARNINGS TAKVİMİ

> **amaç**: dün gece + bugün + haftalık

## ADIM 1 — VERİ

```python
# earnings calendar (3 call)
bugün = datetime.now().strftime("%Y-%m-%d")
earnings_bugün = fmp_get("earnings-calendar", {"from": bugün, "to": bugün})
BMO = [e for e in earnings_bugün if e['time'] == 'bmo']
AMC = [e for e in earnings_bugün if e['time'] == 'amc']

# haftalık (1 call)
hafta_sonu = (datetime.now() + timedelta(7)).strftime("%Y-%m-%d")
earnings_hafta = fmp_get("earnings-calendar", {"from": bugün, "to": hafta_sonu})

# her sembol estimate (portföy/swing için 2-10 call)
for sym in [portföy + swing earnings]:
    est = fmp_get("analyst-estimates", {"symbol": sym, "period": "quarter", "limit": 1})
```

## ADIM 2 — WebSearch (3-6 call)

```
1. "[critical stock] earnings results [dün gece]"
2. "[critical stock] pre-market price today" (pre-market fiyatlaması)
3. "[critical stock] earnings whisper expectations" (beklenti kalitesi)
4. "earnings calendar today [bugün]"
5. "[portföy hissesi] guidance analyst reaction [dün]" (gerekirse)
6. "tech earnings [bu hafta]" (gerekirse)
```

**⚠️ pre-market araması zorunlu** — AH tepkisi tek başına yetmez.
analist notları gece boyunca yayınlanır, PM fiyatı daha güvenilir sinyaldir.

## ADIM 3 — RAPOR FORMATI

```markdown
## 4. earnings takvimi

### dün gece (AMC) — sonuçlar

[earnings formatı — her hisse için]

SEMBOL — [şirket]
  EPS:       $X.XX vs beklenti $X.XX → beat/miss %X
  gelir:     $X.XXB vs beklenti $X.XXB → beat/miss %X
  guidance:  [durum]

  beklenti kalitesi:
  - konsensüs çıtası: [yüksek/orta/düşük]
  - son 90g revizyon: [↑/→/↓]
  - beat kalitesi: [güçlü/zayıf/yanıltıcı]

  piyasa tepkisi:
  - AH: $XXX (±%X)
  - pre-market: $XXX (±%X)
  - tepki yorumu: [pozitif/nötr/negatif — neden]

  etki:
  - portföy: [doğrudan/dolaylı]
  - sektör: [etki]
  - aksiyon: [ne yapılacak]

### bugün

**BMO** (09:30 TR öncesi):
- [SEMBOL] — [şirket] | EPS beklentisi: $X.XX

**AMC** (23:00+ TR):
- [SEMBOL] — [şirket] | EPS beklentisi: $X.XX

### haftalık kritik

| tarih | sembol | timing | etki |
|-------|--------|--------|------|
| XX Şub | NVDA | AMC | portföy: PLTR, SHOP |
| XX Şub | WMT | BMO | sektör: perakende |
```

---
---

# BÖLÜM 5: SONUÇ + AKSİYON

> **amaç**: özet, bugün ne yapacağız

```markdown
## 5. sonuç

### özet

[3-4 cümle — piyasa + portföy + kritik noktalar]

### bugünün aksiyonları

**🔴 hemen** (seans açılışta):
1. [aksiyon] — [sebep + hedef]

**🟡 izle** (seans içinde):
2. [koşul] → [yapılacak aksiyon]
3. [koşul] → [yapılacak aksiyon]

**🟢 pasif** (seviye bekle):
4. [sembol] $XXX'e gelirse → [değerlendir]

### sonraki güncelleme

[yarın günlük rapor / cumartesi haftalık / ay sonu aylık]

---

*finzora ai | fmp api | new york kapalı*
```

---
---

# KALİTE KONTROL

**her faz sonrası**:
- [ ] faz 0: dünkü rapor okundu mu?
- [ ] faz 1: JSON güncellenip push edildi mi?
- [ ] faz 2: rapor yazılıp push edildi mi?

**JSON kontrol**:
- [ ] tüm semboller güncel fiyatla güncellendi?
- [ ] k/z hesaplamaları tutarlı?
- [ ] ağırlık toplamı ≈ %100?
- [ ] summary = 3 portföy toplamı?

**rapor kontrol**:
- [ ] tüm bölümler (0-5) yazıldı?
- [ ] earnings formatı doğru?
- [ ] aksiyon planı net?
- [ ] websearch sonuçları dahil?

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
