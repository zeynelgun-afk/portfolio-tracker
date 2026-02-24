# BÖLÜM 4: EARNINGS TAKVİMİ

> **amaç**: önümüzdeki 7 günün önemli earnings açıklamalarını listele, portföy etkisini değerlendir
> **tahmini FMP call**: 5-15 (takvim + portföy hissesi tahminleri)
> **tahmini websearch**: 1-2

---

## ADIM 1 — VERİ TOPLAMA

### 1a. earnings takvimi (1 call)

```python
from datetime import datetime, timedelta

bugun = datetime.now().strftime("%Y-%m-%d")
yedi_gun_sonra = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

earnings = fmp_get("earnings-calendar", {
    "from": bugun,
    "to": yedi_gun_sonra
})
# dönen veri: date, symbol, eps, epsEstimated, revenue, revenueEstimated, time (bmo/amc)
```

### 1b. filtreleme

```python
# sadece piyasa değeri > $2B şirketleri al
# earnings-calendar'da marketCap alanı yoksa → profile endpoint ile kontrol et
# ama bu çok call harcar, alternatif:

# YÖNTEİM 1 (verimli): bilinen büyük şirketleri websearch ile teyit et
# YÖNTEM 2 (kesin): her earnings hissesi için profile çek — ÇOK PAHALI, yapma

# PRATİK ÇÖZÜM: earnings-calendar zaten büyük şirketleri döner
# elle filtrele: tanınmayan/micro-cap isimleri çıkar
# mega-cap (FAANG, top 50) ve sektörümüzle ilgili olanları öne çıkar
```

### 1c. portföy hisselerinin earnings kontrolü (opsiyonel, 0-5 call)

```python
# portföy + swing hisselerimizin earnings'i bu hafta mı?
portfoy_semboller = ["SM","KOS","MO","XLE","RGLD","XLI","GILT","BKSY",
                      "NNDM","PLTR","SHOP","T","VZ","PM","XOM","CVX",
                      "SCHD","XLV","NEM","UNH","LMT","GE","DUK","DVA"]

# earnings takviminden bu sembolleri filtrele
portfoy_earnings = [e for e in earnings if e['symbol'] in portfoy_semboller]

# eğer varsa, analyst-estimates ile EPS tahmini çek
for e in portfoy_earnings:
    estimates = fmp_get("analyst-estimates", {
        "symbol": e['symbol'], "period": "quarter", "limit": 1
    })
```

### 1d. haftanın önemli earnings'leri için bağlam (1-2 websearch)

```
websearch → "earnings this week {tarih} most important"
websearch → "earnings preview week {tarih}"
```

---

## ADIM 2 — ÖNEMLİ EARNINGS SEÇME KRİTERLERİ

tüm earnings listesinden "haftanın en kritik 5-7 earnings"ini seç:

```
ÖNCELİK SIRASI:

1. PORTFÖY HİSSELERİMİZ (en yüksek öncelik)
   - bizim portföy veya swing'deki herhangi bir hisse raporluyorsa → mutlaka dahil et

2. SEKTÖR ETKİSİ
   - enerji sektörü earnings (portföyümüzde enerji ağırlığı yüksek)
   - savunma sektörü (BKSY, LMT bağlantısı)
   - telecom (T, VZ bağlantısı)
   - tech mega-cap (PLTR, SHOP için yön gösterici)

3. PİYASA ETKİSİ
   - mega-cap earnings (AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA)
   - bu şirketler tüm piyasayı etkiler

4. MACRO BELİRLEYİCİLER
   - banka earnings → finans sektörü sağlığı
   - perakende earnings → tüketici harcaması
   - endüstriyel earnings → ekonomik aktivite
```

---

## ADIM 3 — SÜRPRİZ BEKLENTİSİ DEĞERLENDİRME

`earnings-surprises` endpoint'i Premium'da yok. alternatif yöntem:

```
SÜRPRİZ OLASILIK DEĞERLENDİRME KRİTERLERİ:

POZİTİF SÜRPRİZ BEKLENTİSİ (beat):
- hisse son 3 ayda piyasadan iyi performans gösterdi (insider bilgi sızıntısı olabilir)
- şirket son 4 çeyrekte üst üste beat etti (geçmiş pattern)
- sektör rüzgarı arkasından esiyor (örn: enerji fiyatları yükseldi → enerji şirketleri beat eder)
- analist tahminleri son 30 günde yukarı revize edildi
- yönetim son earnings call'da iyimser guidance verdi
- websearch'te "whisper number" veya "beat expectations" beklentisi var mı?

NEGATİF SÜRPRİZ BEKLENTİSİ (miss):
- hisse son 3 ayda piyasadan kötü performans gösterdi
- sektörde ters rüzgar var (örn: tech harcamaları düşüyor)
- analist tahminleri son 30 günde aşağı revize edildi
- makro ortam şirkete olumsuz (faiz ↑ → borçlu şirketler, dolar ↑ → ihracatçılar)

DEĞERLENDİRME ÖLÇEĞİ:
  "yüksek beat olasılığı"  — 3+ pozitif kriter karşılanıyor
  "olası beat"             — 1-2 pozitif kriter
  "belirsiz"               — karışık sinyaller
  "olası miss"             — 1-2 negatif kriter
  "yüksek miss riski"      — 3+ negatif kriter

⚠️ BU TAHMİN DEĞİL, OLASI SENARYO: kesinlik iddia etme,
"bu kriterlere bakarak X olasılığı yüksek görünüyor" şeklinde yaz
```

---

## ADIM 4 — RAPOR ÇIKTI FORMATI

```markdown
## 4. earnings takvimi (önümüzdeki 7 gün)

### ⚡ portföy hisselerimizin earnings'leri

(eğer bu hafta portföy/swing hissemiz raporluyorsa)

| tarih | şirket | ticker | portföy | EPS tahmini | gelir tahmini | zamanlama |
|-------|--------|--------|---------|-------------|---------------|-----------|
| XX/XX | [isim] | [SYM] | [hangi portföy] | $X.XX | $X.XXB | BMO/AMC |

**etki analizi**: [bu earnings portföyümüzü nasıl etkiler, ne yapmalıyız]
**senaryo**: beat → [portföy etkisi] | miss → [portföy etkisi]

(eğer bu hafta yoksa: "bu hafta portföy hisselerimizden raporlayan yok ✅")

---

### earnings takvimi (piyasa değeri > $2B)

#### [gün adı], [tarih]

**piyasa açılışı öncesi (BMO):**
| şirket | ticker | piyasa değeri | EPS tahmini | gelir tahmini | sektör |
|--------|--------|---------------|-------------|---------------|--------|

**piyasa kapanışı sonrası (AMC):**
| şirket | ticker | piyasa değeri | EPS tahmini | gelir tahmini | sektör |
|--------|--------|---------------|-------------|---------------|--------|

(her gün için ayrı tablo, sadece önemli şirketler)

---

### haftanın en kritik 5-7 earnings

1. **[ŞİRKET] ([TICKER])** — [tarih] [BMO/AMC]
   - **neden önemli**: [portföy bağlantısı veya piyasa etkisi]
   - **beklenti**: [EPS tahmini, gelir tahmini]
   - **sürpriz değerlendirmesi**: [yüksek beat olasılığı / belirsiz / miss riski]
   - **dikkat**: [bu earningsten sonra ne izlemeliyiz]

2. **[ŞİRKET] ([TICKER])** — ...

...

### portföy için earnings riski

[1-3 cümle: bu haftaki earnings portföyümüzü nasıl etkiler?
pozisyon almadan önce earnings tarihini kontrol et.
earnings öncesi yeni swing girişi riskli olabilir.]
```

---

## ADIM 5 — KALİTE KONTROL

- [ ] earnings-calendar verisi bu haftanın tarihlerini kapsıyor mu?
- [ ] portföy hisselerimizin earnings'i kontrol edildi mi?
- [ ] mega-cap earnings'ler listede mi? (FAANG varsa kaçırılmamalı)
- [ ] sektörümüzle ilgili earnings'ler vurgulandı mı?
- [ ] sürpriz değerlendirmesi somut kriterlere dayalı mı? (subjektif tahmin değil)
- [ ] BMO/AMC ayrımı doğru mu?
- [ ] "portföy için earnings riski" bölümü spesifik mi?
