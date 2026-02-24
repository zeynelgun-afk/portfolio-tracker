# GÜNLÜK RAPOR MASTER PROMPT — v2.3 (Kapanış Değerlendirmesi + Seans Öncesi Plan)

> **versiyon**: 2.3 | **son güncelleme**: 24 şubat 2026
> **çıktı dosyası**: `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
> **çalışma zamanı**: her iş günü TR ~14:00 (NYSE kapanışından ~14 saat sonra, açılıştan ~3.5 saat önce)
> **perspektif**: DÜNÜN KAPANIŞ DEĞERLENDİRMESİ + JSON FİNAL GÜNCELLEME + BUGÜN NE YAPACAĞIZ
> **fiyat verisi**: dünün kapanış fiyatları (FMP quote = son kapanış)
> **dil**: küçük harf türkçe, teknik terimler ingilizce kalabilir
> **kaynak atfı**: sadece "finzora ai" kullan
> **format kuralları**: em dash kullanma, doğal yazım hataları kabul edilir
> **git commit**: `[GÜNLÜK RAPOR] DD Ay YYYY - kısa özet`
>
> **⚠️ ZAMAN BİLİNCİ**:
> - rapor TR ~14:00'da yazılır — NYSE dün 00:00 TR'de kapandı, bugün 17:30 TR'de açılacak
> - FMP fiyatları = dünün kapanışı (kesinleşmiş final fiyatlar)
> - after-hours: dün 00:00-02:00 TR arası olmuş (AMC earnings sonuçları gelebilir)
> - pre-market: bugün 16:00-17:30 TR (rapor yazıldıktan ~2 saat sonra başlar)
> - bugünün seansı 17:30 TR'de açılır, 00:00 TR'de kapanır
>
> **BU PROMPT 3 İŞİ BİRDEN YAPAR**:
> 1. dünün kapanış değerlendirmesi (ne oldu, plan tuttu mu, dersler)
> 2. JSON final güncelleme (tüm dosyalar kapanış fiyatıyla, doğrulama)
> 3. bugünün seans planı (futures, haberler, aksiyon listesi)

---

## GENEL BAKIŞ

| bölüm | içerik | sıklık | FMP call | websearch |
|-------|--------|--------|----------|-----------|
| 0. kapanış değerlendirmesi | plan tuttu mu, dersler, JSON final güncelleme | günlük | 0* | 0-1 |
| 1. piyasa görünümü | dünün kapanışı, futures, sektörler, risk, gece haberleri | günlük | ~12 | 5-7 |
| 2. portföy takibi | 4 portföy detay, RSI, SMA, uyarılar | günlük | ~73 | 0 |
| 3. swing trade | stop/hedef kontrol, bugünün aksiyon kararları | günlük | 0* | 0 |
| 4. earnings takvimi | dün gece sonuçları, bugün BMO/AMC, haftalık takvim | günlük | 5-15 | 2-4 |
| 5. CANSLIM tarama | 7 kriterli büyüme hissesi taraması | **haftalık** | 80-100 | 1-2 |
| 6. sonuç + aksiyon | sentez, bugünün seansı için plan | günlük | 0 | 0 |
| **günlük toplam** | | | **~90-100** | **7-12** |
| **haftalık ek** | (CANSLIM dahil) | | **+80-100** | **+1-2** |

*bölüm 0 verileri bölüm 1-2'de çekilir, ekstra call gerekmez
*bölüm 3 verileri bölüm 2'de zaten çekilir, ekstra call gerekmez

**⚠️ API bütçesi**: günlük rapor ~100 + seans içi ~88 = ~190 / 2,500 limit = **%7.6** (güvenli)

---

## ÇALIŞTIRMA ADIM SIRASI

```
GÜNLÜK RAPOR (TR ~14:00):

FАZE 0 — KAPANIŞ DEĞERLENDİRMESİ
0a. repo'yu çek (git pull)
0b. dünkü raporu oku (reports/daily/DAILY_REPORT_DÜNÜN_TARİHİ.md)
0c. dünün aksiyonları uygulandı mı? plan tuttu mu?
0d. dünün dersleri: doğru/yanlış kararlar, kaçırılan fırsatlar

FАZE 1 — VERİ TOPLAMA + JSON FİNAL GÜNCELLEME
1a. tüm portföy + swing JSON dosyalarını oku
1b. benzersiz sembol listesi çıkar (portföy + swing birleşik)
1c. FMP'den toplu veri çek (dünün kapanış fiyatları + teknik göstergeler)
1d. JSON dosyalarını güncelle (kapanış fiyatıyla — final güncelleme)
1e. doğrulama kontrolleri yap (hesaplama tutarlılığı)
1f. summary.json güncelle

FАZE 2 — PİYASA ANALİZİ + YENİ GÜN PLANI
2a. websearch: pre-market futures, gece haberleri, after-hours sonuçları
2b. sektör performansı + RS analizi
2c. bölüm 1-6'yı sırayla yaz
2d. raporu kaydet → reports/daily/DAILY_REPORT_YYYY-MM-DD.md
2e. git commit + push (JSON güncellemeleri + rapor birlikte)

SEANS SIRASINDA (TR 17:30-00:00):
→ SESSION_ACTION_PROMPT.md kullan
→ rapordaki aksiyon planını uygula
```

---

## 3 PROMPT SİSTEMİ — BİR GÜNÜN AKIŞI

```
TR 14:00  →  GÜNLÜK RAPOR (bu prompt)
              kapanış değerlendirmesi + JSON final güncelleme + yeni gün planı

TR 18:00+ →  SEANS İÇİ AKSİYON (SESSION_ACTION_PROMPT.md)
              canlı fiyat, karar + uygulama

(ertesi gün TR 14:00 → tekrar bu prompt)
```

---

## BENZERSİZ SEMBOL LİSTESİ (tüm bölümler için ortak)

bölüm 2 ve 3 aynı sembol havuzunu kullanır. tekrar FMP call yapma.
her çalıştırmada JSON dosyalarından dinamik olarak oluştur:

```python
import json

semboller = set()

# 4 portföyden
for dosya in ["balanced.json", "aggressive.json", "dividend.json", "rotation.json"]:
    with open(f"data/portfolios/{dosya}") as f:
        port = json.load(f)
    for pos in port['pozisyonlar']:
        semboller.add(pos['sembol'])

# swing aktif pozisyonlardan
with open("data/swing/active.json") as f:
    swing = json.load(f)
for pos in swing['aktif_pozisyonlar']:
    semboller.add(pos['sembol'])

# benchmark
semboller.add("SPY")

benzersiz = sorted(semboller)
# bu liste bölüm 1 (SPY teknik), bölüm 2 (portföy), bölüm 3 (swing) için kullanılır
```



---
---

# BÖLÜM 0: KAPANIŞ DEĞERLENDİRMESİ + JSON FİNAL GÜNCELLEME

> **amaç**: dünkü seansı değerlendir, plan tuttu mu kontrol et, JSON'ları final güncelle
> **tahmini FMP call**: 0 (bölüm 1-2'de zaten çekilecek veriler kullanılır)
> **tahmini websearch**: 0-1 (after-hours sonuçları gerekirse)
> **not**: bu bölüm rapor dosyasına yazılır + JSON güncelleme yapılır

---

## ADIM 1 — DÜNKÜ RAPORU OKU

```
1. dünün raporunu aç: reports/daily/DAILY_REPORT_{DÜN_TARİH}.md
2. bölüm 6'daki aksiyon planını bul:
   - 🔴 acil aksiyonlar → hangisi uygulandı?
   - 🟡 izlenenler → tetiklendi mi?
   - 🟢 fırsatlar → değerlendirildi mi?
3. dün seans içi prompt (SESSION_ACTION) kullanıldıysa → yapılan trade'leri not et
```

eğer dünkü rapor yoksa veya ilk raporse → bu adımı atla, "önceki rapor yok" notu düş

---

## ADIM 2 — PLAN DEĞERLENDİRMESİ

```markdown
## 0. dünün değerlendirmesi

### plan gerçekleşme

| aksiyon | plan | sonuç | not |
|---------|------|-------|-----|
| [acil 1] | [planlanmış aksiyon] | ✅ yapıldı / ❌ yapılmadı / ⏳ devam ediyor | [kısa açıklama] |
| [acil 2] | ... | ... | ... |
| [izle 1] | ... | ... | ... |

(dün aksiyon planı yoksa veya ilk raporse → "ilk rapor, önceki plan yok" yaz)

### dünün performans özeti

- portföy toplam değişim: +/-$X,XXX (+/-%X.XX)
- SPY dün: +/-%X.XX → alpha: +/-%X.XX
- en iyi performans: SEMBOL (+%X.XX) — [neden]
- en kötü performans: SEMBOL (-%X.XX) — [neden]

### dersler

- ✅ doğru karar: [ne yapıldı, neden doğruydu]
- ❌ yanlış karar: [ne yapıldı, neden yanlıştı, bir dahaki sefere ne farklı]
- 🔍 kaçırılan fırsat: [ne oldu, fark edildi mi, neden girilmedi]
- (her gün ders olmak zorunda değil — sıradan günlerde "rutin gün, özel ders yok" yaz)
```

---

## ADIM 3 — JSON FİNAL GÜNCELLEME

bu adımda FMP'den çekilen kapanış fiyatlarıyla (bölüm 1-2'de zaten çekilecek) tüm JSON'ları güncelle:

### 3a. portföy JSON'ları

```python
for portfolio in [balanced, aggressive, dividend, rotation]:
    for pozisyon in portfolio['pozisyonlar']:
        pozisyon['guncel_fiyat'] = quote['price']
        pozisyon['gunluk_degisim_yuzde'] = quote['changesPercentage']
        pozisyon['guncel_deger'] = pozisyon['adet'] * pozisyon['guncel_fiyat']
        pozisyon['kar_zarar'] = pozisyon['guncel_deger'] - pozisyon['yatirim']
        pozisyon['kar_zarar_yuzde'] = (pozisyon['kar_zarar'] / pozisyon['yatirim']) * 100
        pozisyon['son_guncelleme'] = datetime.now().isoformat()
    
    toplam_deger = sum(p['guncel_deger'] for p in pozisyonlar) + nakit['miktar']
    portfolio['toplam_deger'] = toplam_deger
    portfolio['toplam_getiri_yuzde'] = ((toplam_deger - 100000) / 100000) * 100
    
    for pozisyon in portfolio['pozisyonlar']:
        pozisyon['agirlik_yuzde'] = (pozisyon['guncel_deger'] / toplam_deger) * 100
```

### 3b. swing active.json

```python
for pozisyon in aktif_pozisyonlar:
    pozisyon['guncel_fiyat'] = quote['price']
    pozisyon['guncel_kar_zarar_yuzde'] = ((guncel - giris) / giris) * 100
    pozisyon['tutulan_gun'] = (today - giris_tarihi).days
    
    # trailing stop güncelle (sadece yukarı)
    if guncel_fiyat > önceki_zirve:
        yeni_trailing = guncel_fiyat * 0.95
        if yeni_trailing > mevcut_trailing:
            trailing_stop = yeni_trailing
```

### 3c. summary.json

```python
summary['toplam_deger'] = dengeli + agresif + temettü + rotasyon
summary['toplam_kar_zarar'] = toplam_deger - 400000
summary['toplam_kar_zarar_yuzde'] = (toplam_kar_zarar / 400000) * 100
summary['benchmark_spy'] = SPY_baslangictan_beri
summary['alpha'] = toplam_kar_zarar_yuzde - benchmark_spy
```

### 3d. doğrulama kontrolleri

güncelleme sonrası şu kontrolleri yap — hata varsa düzelt:

```
✓ yatirim = adet × maliyet_baz (sabit, değişmemeli)
✓ guncel_deger = adet × guncel_fiyat
✓ kar_zarar = guncel_deger - yatirim
✓ nakit.miktar = doğru (trade olmadıysa değişmemeli)
✓ toplam_deger = sum(guncel_deger) + nakit
✓ agirlik toplamı + nakit ağırlığı ≈ %100
✓ summary toplam = 4 portföy toplamı
✓ swing trailing stop'lar sadece yukarı gitmiş
✓ tüm son_guncelleme bugünün tarihi
```

### 3e. after-hours kontrol (varsa)

```
- dün AMC earnings açıklayan portföy/swing hissesi var mı?
- after-hours'ta > %3 hareket eden portföy hissesi var mı?
- after-hours'ta > %5 hareket eden swing hissesi var mı?
→ varsa not düş, bölüm 2-3'te dikkat çek
→ after-hours fiyatı JSON'lara YAZILMAZ (sadece normal kapanış geçerli)
```

---

## ADIM 4 — KALİTE KONTROL

- [ ] dünkü rapordaki aksiyonlar değerlendirildi mi?
- [ ] dersler yazıldı mı? (sıradan günlerde "rutin" notu yeterli)
- [ ] tüm JSON dosyaları kapanış fiyatıyla güncellendi mi?
- [ ] doğrulama kontrolleri yapıldı mı?
- [ ] summary.json güncellendi mi?
- [ ] after-hours önemli hareket varsa not düşüldü mü?

---
---

# BÖLÜM 1: PİYASA GÖRÜNÜMÜ (dünün özeti + bugünün beklentisi)

> **amaç**: dünün kapanışını özetle, gece gelişmelerini ekle, bugünün seansı için beklenti oluştur
> **tahmini FMP call**: 12-16
> **tahmini websearch**: 5-7

---

## ADIM 1 — VERİ TOPLAMA

### 1a. FMP API çağrıları (dünün kapanış verileri)

```
# ⚠️ rapor seans öncesi yazıldığı için FMP verileri = DÜNün kapanışı
# bu normal ve beklenen durum

# --- endeksler (1 call) ---
batch-quote → symbols=SPY,QQQ,DIA
# SPY = S&P 500 proxy, QQQ = NASDAQ proxy, DIA = Dow proxy

# --- emtia (2 call) ---
quote → symbol=GCUSD          # altın
quote → symbol=CLUSD          # WTI ham petrol

# --- forex (2 call) ---
quote → symbol=EURUSD
quote → symbol=USDTRY

# --- tahvil (1 call) ---
treasury-rates → from={bugün}, to={bugün}
# dönen veriden 'month10' = 10 yıllık yield (ondalık, örn: 4.25 = %4.25)
# eğer boş dönerse → websearch yedek: "us 10 year treasury yield today"

# --- sektör performansı (1 call) ---
sector-performance-snapshot → date={bugün}
# 11 sektör tek call'da gelir
# ⚠️ date parametresi ZORUNLU, yoksa 404 döner

# --- SPY teknik (3 call) ---
technical-indicators/sma → symbol=SPY, periodLength=50, timeframe=1day
technical-indicators/sma → symbol=SPY, periodLength=200, timeframe=1day
technical-indicators/rsi → symbol=SPY, periodLength=14, timeframe=1day
# sadece son 1 değeri kullan (limit=1 yok ama ilk eleman en güncel)

# --- piyasa hareketi (2 call) ---
biggest-gainers → limit=5
biggest-losers → limit=5
# ⚠️ doğru isim: "biggest-gainers", "biggest-losers" (market- prefix'i YOK)
```

**toplam: ~12 FMP call**

### 1b. WebSearch aramaları (bugünün beklentisi için kritik)

```
# --- VIX + DXY (FMP'de doğrudan yok) ---
websearch → "VIX index close today {dünün tarihi}"
websearch → "US dollar index DXY today"

# --- pre-market + futures (SABAH RAPORU İÇİN KRİTİK) ---
websearch → "stock market futures today pre-market"
# S&P 500 futures, NASDAQ futures, Dow futures
# bu veri bugünün açılış yönünü gösterir

# --- gece gelişmeleri ---
websearch → "stock market news today {bugünün tarihi}"
websearch → "overnight market news asia europe"
# asya/avrupa piyasaları sabah kapanmış olur, bilgi mevcuttur

# opsiyonel (önemli olay varsa):
websearch → "fed news today" veya "earnings results after hours"
# dün kapanıştan sonra açıklanan earnings sonuçları
```

**toplam: 5-7 websearch**

### 1c. veri bulunamazsa yedek plan

| veri | birincil kaynak | yedek |
|------|-----------------|-------|
| VIX | websearch | FMP quote UVXY (ters proxy, ama yeterli gösterge) |
| DXY | websearch | FMP quote EURUSD (ters çevir: DXY güçlü = EUR/USD düşük) |
| 10Y yield | treasury-rates | websearch "10 year yield today" |
| sektör perf | sector-performance-snapshot | websearch "sector performance today" |

---

## ADIM 2 — ANALİZ KURALLARI

### risk duyarlılığı nasıl belirlenir

```
3 ANA GÖSTERGEYE BAK:

1. VIX:  < 18 → Risk-On  |  18-25 → Nötr  |  > 25 → Risk-Off
2. SEKTÖR: günün en iyi 3 sektörü döngüsel mi savunmacı mı?
   - döngüsel lider (tech, finans, tüketim) → Risk-On
   - savunmacı lider (utilities, staples, healthcare) → Risk-Off
3. ALTIN + HISSE: ikisi birlikte yükseliyorsa → Nötr
   - altın ↑ hisse ↓ → Risk-Off  |  altın ↓ hisse ↑ → Risk-On

SONUÇ: 3 göstergeden 2'si aynı yöne işaret ediyorsa o yönü seç, yoksa Nötr
```

### S&P 500 trend nasıl belirlenir

```
SPY fiyat > SMA50 > SMA200      → "güçlü yükseliş trendi"
SPY fiyat > SMA50, < SMA200     → "toparlanma aşaması"
SPY fiyat < SMA50, > SMA200     → "kısa vadeli zayıflık, ana trend sağlam"
SPY fiyat < SMA50 < SMA200      → "düşüş trendi"

RSI > 70   → "aşırı alım bölgesi, dikkat"
RSI < 30   → "aşırı satım bölgesi, fırsat olabilir"
RSI 40-60  → "nötr"
```

### sektör göreceli güç analizi (relative strength)

```
KURAL: piyasa düşerken düşmeyen/yükselen sektör = güçlü para akışı sinyali

HESAPLAMA:
  sektor_rs = sektor_degisim - SPY_degisim

  SPY düşerken (SPY < -%0.5):
    sektor_rs > +1.0%  → 🔥 GÜÇ SEKTÖR — "piyasa düşerken para buraya akıyor"
    sektor_rs > +0.5%  → 💪 dirençli — "piyasaya göre belirgin üstün performans"

  SPY yükselirken (SPY > +%0.5):
    sektor_rs < -1.0%  → ⚠️ ZAYIF SEKTÖR — "yükselişe katılamıyor, çıkış var"
    sektor_rs < -0.5%  → 📉 geride kalıyor

  ÖNEMLİ: bu sektörleri raporda özel olarak vurgula:
  - portföyümüzdeki pozisyonlarla eşleştir (enerji güçlüyse SM, KOS, XLE nasıl?)
  - swing watchlist için fırsat mı? (güçlü sektörden yeni aday?)
  - rotasyon portföyü için sinyal mi? (güçlü sektöre ağırlık artır?)
```

websearch'ten gelen haberleri şu filtreyle değerlendir:
1. **portföy etkisi** — haber bizim pozisyonlarımızı doğrudan etkiliyor mu?
2. **sektör etkisi** — enerji, savunma, tech, telecom, sağlık sektörlerimiz etkileniyor mu?
3. **makro etki** — faiz, enflasyon, istihdam, jeopolitik gibi geniş çaplı mı?
4. **sadece en önemli 3-5 haber** — kalabalık yapma, her habere 1-2 cümle etki analizi yaz

---

## ADIM 3 — RAPOR ÇIKTI FORMATI

```markdown
## 0. dünün değerlendirmesi

### plan gerçekleşme ({dünün tarihi})

| aksiyon | plan | sonuç | not |
|---------|------|-------|-----|
| [acil 1] | [ne planlanmıştı] | ✅/❌/⏳ | [kısa açıklama] |
| [izle 1] | ... | ... | ... |

(ilk raporse veya dün aksiyon yoksa → "önceki rapor yok / rutin gün" yaz)

### dünün performans özeti

- portföy toplam değişim: +/-$X,XXX (+/-%X.XX)
- SPY dün: +/-%X.XX → alpha: +/-%X.XX
- en iyi: SEMBOL (+%X.XX) — [neden]
- en kötü: SEMBOL (-%X.XX) — [neden]

### dersler

- ✅ doğru karar: [açıklama]
- ❌ yanlış karar: [açıklama + bir dahaki sefere ne farklı]
- (sıradan gün → "rutin gün, özel ders yok")

### JSON güncelleme durumu

✅ 4 portföy + swing active + summary güncellendi (kapanış fiyatlarıyla)
doğrulama: [sorun yok / şu düzeltildi: ...]
```

```markdown
## 1. piyasa görünümü

### dünün kapanışı ({dünün tarihi}, {gün adı})

| gösterge | kapanış | günlük değişim | sinyal |
|----------|---------|----------------|--------|
| S&P 500 (SPY) | $XXX.XX | ▲/▼ %X.XX | |
| NASDAQ (QQQ) | $XXX.XX | ▲/▼ %X.XX | |
| Dow Jones (DIA) | $XXX.XX | ▲/▼ %X.XX | |
| VIX | XX.XX | ▲/▼ X.XX | [düşük korku / orta / yüksek korku] |
| US 10Y yield | %X.XX | ▲/▼ X bp | |
| altın (XAU) | $X,XXX | ▲/▼ %X.XX | |
| WTI petrol | $XX.XX | ▲/▼ %X.XX | |
| EUR/USD | X.XXXX | ▲/▼ %X.XX | |
| USD/TRY | XX.XX | ▲/▼ %X.XX | |
| DXY | XXX.XX | ▲/▼ %X.XX | |

### bugünün öncü göstergeleri

| gösterge | değer | sinyal |
|----------|-------|--------|
| S&P 500 futures | ▲/▼ %X.XX | [pozitif/negatif/düz açılış beklentisi] |
| NASDAQ futures | ▲/▼ %X.XX | |
| asya piyasaları | [nikkei/hang seng durum] | [risk-on/off sinyali] |
| avrupa piyasaları | [dax/ftse durum] | |

### sektör performansı (dün)

| sektör | değişim % | RS (vs SPY) | | sektör | değişim % | RS (vs SPY) |
|--------|-----------|-------------|---|--------|-----------|-------------|
| [en iyi 1] | +%X.XX 🟢 | +%X.XX | | [en kötü 1] | -%X.XX 🔴 | -%X.XX |
| [en iyi 2] | +%X.XX 🟢 | +%X.XX | | [en kötü 2] | -%X.XX 🔴 | -%X.XX |
| [en iyi 3] | +%X.XX | +%X.XX | | [en kötü 3] | -%X.XX | -%X.XX |

(11 sektörü en iyi → en kötü sırayla listele, en iyi 3 ve en kötü 3'ü vurgula)
(RS = sektör değişimi - SPY değişimi. 🔥 işareti: piyasa düşerken RS > +1%)

### piyasa hareketi (dün)

**dünün kazananları** (biggest-gainers'dan top 5):
| ticker | değişim % | hacim |
(tabloya hacim de ekle, anormal hacim genellikle haberi olan hissedir)

**dünün kaybedenleri** (biggest-losers'dan top 5):
| ticker | değişim % | hacim |

### risk değerlendirmesi

- **risk duyarlılığı**: [RISK-ON 🟢 / RISK-OFF 🔴 / NÖTR ⚪]
  - gerekçe: [yukarıdaki skor tablosuna göre 2-3 cümle]
- **SPY teknik durum**: $XXX.XX | SMA50: $XXX | SMA200: $XXX | RSI: XX
  - trend: [güçlü yükseliş / kısa vadeli zayıflık / düşüş trendi / ...]
- **kritik seviyeler**: destek $XXX, direnç $XXX

### gece gelişmeleri + bugünün beklentisi

1. **[başlık]** — [1-2 cümle: ne oldu + portföyümüze etkisi]
2. **[başlık]** — [1-2 cümle]
3. **[başlık]** — [1-2 cümle]

(dün kapanıştan sonra + gece + sabah gelişmeleri: after-hours earnings, asya haberleri, makro veri)

### strateji notu (bugünün seansı için)

[2-3 cümle: futures'a ve gece haberlerine göre bugün nasıl bir açılış bekliyoruz?
savunmacı mı kalmalıyız, fırsat mı kollamalıyız?
hangi sektörler bugün güçlü/zayıf olabilir?
bugünkü seans için dikkat edilmesi gereken saatler (earnings açıklaması, makro veri gibi)]
```

---

## ADIM 4 — KALİTE KONTROL

raporu yazmadan önce şunları doğrula:
- [ ] tüm FMP verileri başarıyla geldi mi? (boş [] dönmediyse OK)
- [ ] FMP fiyatları dünün kapanışı mı? (piyasa şu an kapalı, bu beklenen)
- [ ] VIX ve DXY websearch'ten alındıysa değer mantıklı mı?
- [ ] sektör performansı tarihi dünün tarihi mi?
- [ ] pre-market futures bilgisi websearch'ten alındı mı?
- [ ] asya/avrupa piyasa bilgisi eklendi mi?
- [ ] risk skoru hesaplaması tutarlı mı?
- [ ] SPY trend açıklaması SMA50/SMA200/RSI verileriyle uyuşuyor mu?
- [ ] gece gelişmeleri gerçekten dün akşam/gece haberleri mi?
- [ ] strateji notu bugünün seansına yönelik mi? (dünü anlatmıyor, bugünü planlıyor)


---
---

# BÖLÜM 2: PORTFÖY TAKİBİ (dünün kapanışı ile güncel durum)

> **amaç**: 4 portföyün dünün kapanışına göre güncel durumunu raporla, bugün dikkat edilecek seviyeleri belirle
> **tahmini FMP call**: ~85-100 (benzersiz hisse sayısına bağlı)
> **tahmini websearch**: 0

---

## ADIM 1 — BENZERSİZ SEMBOL LİSTESİ ÇIKAR

aynı hisse birden fazla portföyde olabilir (MO, XLE, XLI gibi).
önce tüm portföylerden benzersiz sembol listesi çıkar, FMP call'ları tekrar etme.

```
mevcut benzersiz semboller (şubat 2026 itibarıyla):
dengeli:  SM, KOS, MO, XLE, RGLD, XLI
agresif:  GILT, BKSY, NNDM, PLTR, SHOP
temettü:  T, VZ, MO, PM, XOM, CVX, SCHD
rotasyon: XLE, XLV, XLI

benzersiz: SM, KOS, MO, XLE, RGLD, XLI, GILT, BKSY, NNDM, PLTR, SHOP,
           T, VZ, PM, XOM, CVX, SCHD, XLV
toplam: ~18 benzersiz sembol
```

⚠️ bu liste pozisyon açılıp kapandıkça değişir.
her çalıştırmada JSON dosyalarından dinamik olarak çıkar.

---

## ADIM 2 — VERİ TOPLAMA

her benzersiz sembol için 4 FMP call:

```python
for symbol in benzersiz_semboller:
    # 1. güncel fiyat (batch ile toplu çekilebilir → 1 call)
    # 2. RSI 14-günlük
    fmp_get("technical-indicators/rsi", {"symbol": symbol, "periodLength": 14, "timeframe": "1day"})
    # 3. SMA 50-günlük
    fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 50, "timeframe": "1day"})
    # 4. SMA 200-günlük
    fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 200, "timeframe": "1day"})
```

**optimizasyon:**
```python
# fiyatlar tek seferde (1 call)
batch-quote → symbols=SM,KOS,MO,XLE,RGLD,XLI,GILT,...

# haftalık değişim tek seferde (her biri 1 call ama batch yok)
# alternatif: batch-quote'taki previousClose'dan hesapla
# veya stock-price-change endpoint'i (sembol başı 1 call)
stock-price-change → symbol=SM   # 1D, 5D, 1M, 3M, ... hepsi döner
```

**call hesabı:**
- batch-quote: 1 call (tüm semboller)
- RSI: 18 call (sembol başı)
- SMA50: 18 call
- SMA200: 18 call
- stock-price-change: 18 call
- **toplam: ~73 call** (18 benzersiz sembol için)

---

## ADIM 3 — UYARI KURALLARI

her hisseyi şu kurallara göre işaretle:

```
GÜNLÜK HAREKET:
  günlük düşüş ≥ %3        → 🔴 SERT DÜŞÜŞ
  günlük düşüş %1.5-%3     → 🟡 düşüş
  günlük değişim -%1.5/+%1.5 arası → ⚪ nötr
  günlük yükseliş %1.5-%3  → 🟡 yükseliş
  günlük yükseliş ≥ %3     → 🟢 GÜÇLÜ YÜKSELİŞ

RSI:
  RSI > 70                  → ⚠️ AŞIRI ALIM — kar realizasyonu düşün
  RSI 60-70                 → dikkat, aşırı alıma yaklaşıyor
  RSI 40-60                 → nötr
  RSI 30-40                 → zayıf, izle
  RSI < 30                  → ⚠️ AŞIRI SATIM — fırsat olabilir

SMA POZİSYONU:
  fiyat > SMA50 > SMA200    → 📈 güçlü trend (tüm hareketli ortalamalar üzerinde)
  fiyat > SMA50, < SMA200   → 📊 toparlanma (kısa vade pozitif, uzun vade henüz değil)
  fiyat < SMA50, > SMA200   → 📉 kısa vadeli zayıflık (SMA50 altına düşmüş)
  fiyat < SMA50 < SMA200    → ⛔ düşüş trendi (her iki ortalama üzerinde)

ÖZEL DURUMLAR:
  fiyat SMA200'e %2'den yakın → 📌 KRİTİK SEVİYE — SMA200 test ediliyor
  SMA50 ile SMA200 arası %3'ten az → 📌 GOLDEN/DEATH CROSS yakın
  haftalık düşüş ≥ %5        → 🔴 HAFTALIK KAYIP uyarısı
```

---

## ADIM 4 — RAPOR ÇIKTI FORMATI

### her portföy için ayrı tablo + yorum

```markdown
## 2. portföy takibi

### genel özet

| portföy | değer | k/z $ | k/z % | nakit | nakit % | durum |
|---------|-------|-------|-------|-------|---------|-------|
| dengeli | $XXX,XXX | +$X,XXX | +%X.XX | $X,XXX | %XX | [emoji] |
| agresif | $XXX,XXX | -$X,XXX | -%X.XX | $XX,XXX | %XX | [emoji] |
| temettü | $XXX,XXX | +$XX,XXX | +%XX.XX | $XXX | %X | [emoji] 🏆 |
| rotasyon | $XXX,XXX | +$X,XXX | +%X.XX | $XXX | %X | [emoji] |
| **toplam** | **$XXX,XXX** | **+$XX,XXX** | **+%X.XX** | | | |

durum emojileri: 🟢 k/z > +%5 | 🟡 k/z %0-%5 | 🔴 k/z < %0

---

### 2a. dengeli portföy ($100K başlangıç)

| sembol | fiyat | günlük % | haftalık % | RSI | SMA50 | SMA200 | trend | k/z % | ağırlık | uyarı |
|--------|-------|----------|------------|-----|-------|--------|-------|-------|---------|-------|
| SM | $XX.XX | ▼ %X.XX | %X.XX | XX | $XX.XX | $XX.XX | 📈/📉 | +%X.XX | %XX | [varsa] |
| KOS | ... | | | | | | | | | |
| ... | | | | | | | | | | |

**portföy notu:** [2-3 cümle: bugün ne oldu, dikkat çeken hareket, varsa aksiyon önerisi]

**sektör dağılımı:** enerji %XX | temel tüketim %XX | emtia %XX | endüstriyel %XX | nakit %XX

---

### 2b. agresif büyüme ($100K başlangıç)

(aynı tablo formatı)

**portföy notu:** [2-3 cümle]
**nakit durumu:** $XX,XXX (%XX) — [yüksek nakit oranı değerlendirmesi]

---

### 2c. değer + temettü ($100K başlangıç) 🏆

(aynı tablo formatı)

**portföy notu:** [2-3 cümle]

---

### 2d. sektör rotasyonu ($100K başlangıç)

(aynı tablo formatı)

**portföy notu:** [2-3 cümle]
**sektör ağırlıkları:** XLE %XX | XLV %XX | XLI %XX | nakit %X

---

### uyarı özeti

tüm portföylerden uyarı gerektiren hisseleri topla:

🔴 **acil dikkat:**
- [SEMBOL] — [neden: stop yakın / sert düşüş / RSI aşırı / ...]

⚠️ **izlenmesi gereken:**
- [SEMBOL] — [neden]

🟢 **fırsat:**
- [SEMBOL] — [neden: RSI oversold / destek test / ...]
```

---

## ADIM 5 — AKSİYON ÖNERİLERİ

uyarılara göre somut aksiyon öner:

```
KURAL SETİ:

RSI > 75 + k/z > %20     → "kısmi kar realizasyonu düşünülebilir"
RSI < 30 + trend 📈      → "ek alım fırsatı olabilir (mevcut pozisyon varsa)"
RSI < 30 + trend ⛔      → "bıçak düşerken tutma, dip onayı bekle"
günlük -%5+              → "stop-loss kontrol et, panik satış yapma"
haftalık -%10+           → "tez bozuldu mu değerlendir, bozulduysa çık"
fiyat < SMA200 + RSI < 35 → "uzun vadeli destek kırılmış, dikkatli ol"
nakit > %50 (agresif)    → "piyasa netleşince kademeli giriş planla"
```

---

## ADIM 6 — KALİTE KONTROL

- [ ] tüm semboller güncel fiyatla güncellendi mi?
- [ ] k/z hesaplamaları tutarlı mı? (guncel_deger - yatirim)
- [ ] ağırlık yüzdeleri toplamı %100'e yakın mı? (nakit dahil)
- [ ] RSI ve SMA verileri bugüne ait mi?
- [ ] uyarı kuralları doğru uygulandı mı?
- [ ] her portföy notu spesifik mi? (genel laf değil, bugüne özel)
- [ ] JSON dosyaları güncellenip git push yapıldı mı?


---
---

# BÖLÜM 3: SWING TRADE DURUMU (bugünün seansında ne yapacağız?)

> **amaç**: aktif swing pozisyonların dünün kapanışına göre stop/hedef kontrolü, bugün alınacak aksiyonlar
> **tahmini FMP call**: ~15-20 (swing sembolleri bölüm 2'de zaten çekilmişse 0)
> **tahmini websearch**: 0-2 (sadece önemli haber varsa)

---

## ADIM 1 — VERİ TOPLAMA

swing sembollerinin çoğu bölüm 2'de zaten çekilmiş olacak.
eğer çekilmediyse (portföyde olmayan swing hisseleri):

```python
# swing'e özel semboller (portföylerde olmayan)
# mevcut: NEM, UNH, LMT, GE, DUK, DVA — hiçbiri 4 portföyde yok
# bu semboller bölüm 2'nin benzersiz listesine DAHİL EDİLMELİ
# böylece ekstra call gerekmez

# eğer bölüm 2'de dahil edilmediyse:
batch-quote → symbols=NEM,UNH,LMT,GE,DUK,DVA
# + RSI, SMA50, SMA200 (sembol başı 3 call)
```

**⚠️ optimizasyon**: bölüm 2'deki benzersiz sembol listesini oluştururken
swing aktif pozisyonlarını da dahil et. böylece bölüm 3 için ekstra call gerekmez.

---

## ADIM 2 — HER POZİSYON İÇİN KONTROL

```python
for pozisyon in aktif_pozisyonlar:
    # active.json'dan oku:
    giris_fiyati = pozisyon['giris_fiyati']
    stop_loss = pozisyon['stop_loss']
    hedef_fiyat = pozisyon['hedef_fiyat']
    giris_tarihi = pozisyon['giris_tarihi']
    
    # FMP'den gelen güncel veri:
    guncel_fiyat = fmp_quote[symbol]['price']
    rsi = fmp_rsi[symbol]
    
    # hesaplamalar:
    kar_zarar_pct = ((guncel_fiyat - giris_fiyati) / giris_fiyati) * 100
    stop_mesafe = guncel_fiyat - stop_loss
    stop_mesafe_pct = (stop_mesafe / guncel_fiyat) * 100
    hedef_mesafe = hedef_fiyat - guncel_fiyat
    hedef_mesafe_pct = (hedef_mesafe / guncel_fiyat) * 100
    tutulan_gun = (bugun - giris_tarihi).days
    # max süre sınırı yok, tavsiye 7-10 gün
```

---

## ADIM 3 — UYARI VE AKSİYON KURALLARI

```
STOP-LOSS KONTROL:
  fiyat ≤ stop_loss                    → 🔴 STOP TETİKLENDİ — pozisyonu kapat
  stop mesafe < %1 (veya < $1.50)      → 🔴 STOP ÇOK YAKIN — yarın açılışta karar ver
  stop mesafe %1-%3                    → 🟡 stop yakın, izle
  stop mesafe > %3                     → 🟢 güvenli

HEDEF KONTROL:
  fiyat ≥ hedef_fiyat                  → 🎯 HEDEFE ULAŞTI — partial exit planını uygula
  hedef mesafe < %2                    → 🟢 hedefe yakın, trailing stop sıkılaştır
  hedef mesafe %2-%5                   → normal, bekle

SÜRE TAKİBİ (zorunlu değil, bilgilendirme):
  tutulan_gun > 14                     → ℹ️ uzun süredir tutuluyor, tezi yeniden değerlendir
  tutulan_gun > 10                     → ℹ️ tavsiye süre aşıldı (7-10 gün)
  tutulan_gun ≤ 10                     → normal

RSI KONTROL (swing özel):
  RSI > 75 + kar > %5                  → momentum aşırı, kısmi kar al
  RSI < 30 + zarar > %3               → zayıflık devam, stop sıkılaştır

BİLEŞİK AKSİYON KARARLARI:
  stop yakın + zarar büyüyor           → "güçlü çıkış sinyali, yarın kapat"
  hedefe yakın + RSI > 65              → "partial exit: %50 sat, kalan trailing stop"
  zarar > %3 + tutulan > 10 gün       → "tez çalışmıyor, çıkış düşün"
  kar > %7 + süre < 5 gün             → "erken hedef, trailing stop ile kal"
```

---

## ADIM 4 — TRAİLİNG STOP GÜNCELLEME

```
trailing stop kuralı (her pozisyon için):

eğer pozisyon karda ve zirve yaptıysa:
  yeni_trailing_stop = zirve_fiyat × 0.95  (zirveden -%5)
  
  eğer yeni_trailing_stop > mevcut_stop_loss:
    stop_loss = yeni_trailing_stop  ← GÜNCELLE (active.json'da)
    durum notu ekle: "trailing stop yükseltildi: $XX.XX → $YY.YY"
  
  eğer yeni_trailing_stop ≤ mevcut_stop_loss:
    değişiklik yapma (stop sadece yukarı hareket eder)

zirve tespiti:
  son 5 günün en yüksek fiyatı (FMP historical-price-eod/light ile)
  veya batch-quote'taki dayHigh değerini izle
```

---

## ADIM 5 — RAPOR ÇIKTI FORMATI

```markdown
## 3. swing trade durumu

**aktif: X/10 slot | ortalama k/z: +%X.XX | boş slot: X**

### pozisyon tablosu

| id | sembol | giriş | güncel | k/z % | gün | stop | stop mesafe | hedef | hedef mesafe | RSI | durum |
|----|--------|-------|--------|-------|-----|------|-------------|-------|-------------|-----|-------|
| 010 | NEM | $118.12 | $124.25 | +5.19% | 12 | $122.50 | $1.75 (1.4%) | $129.93 | $5.68 (4.6%) | XX | 🔴/🟡/🟢 |
| ... | | | | | | | | | | | | |

### aksiyon gerektiren pozisyonlar

(sadece uyarı olan pozisyonları listele, her biri için somut öneri)

🔴 **acil aksiyon:**
- **[SEMBOL]** (SWING-XXX) — [durum açıklaması]
  - **öneri**: [somut aksiyon: kapat / trailing stop güncelle / partial exit]
  - **gerekçe**: [neden bu aksiyonu öneriyorsun]

🟡 **izlenmesi gereken:**
- **[SEMBOL]** (SWING-XXX) — [durum]
  - yarın dikkat: [ne olursa aksiyon alınır]

🟢 **iyi giden:**
- **[SEMBOL]** (SWING-XXX) — [kısa durum notu]

### trailing stop güncellemeleri

(bugün güncellenen stop'lar varsa listele)
| sembol | eski stop | yeni stop | sebep |
|--------|-----------|-----------|-------|

### watchlist'ten fırsat

(data/swing/watchlist.json'dan urgency="high" olanları kontrol et)
- **[SEMBOL]** — hedef giriş: $XX-XX, güncel: $XX.XX, [giriş koşulu sağlandı mı?]

### swing istatistik

| metrik | değer |
|--------|-------|
| aktif pozisyon | X/10 |
| ortalama k/z | +%X.XX |
| en iyi | SEMBOL +%X.XX |
| en kötü | SEMBOL -%X.XX |
| stop tetiklenen (bugün) | X adet |
| hedefe ulaşan (bugün) | X adet |
| ortalama tutma süresi | X gün |
```

---

## ADIM 6 — JSON GÜNCELLEME

rapor yazıldıktan sonra `data/swing/active.json` güncelle:
1. `guncel_fiyat` → FMP'den gelen fiyat
2. `guncel_kar_zarar_yuzde` → yeniden hesapla
3. `tutulan_gun` → bugüne göre güncelle
4. `stop_loss` → trailing stop değiştiyse güncelle
5. `durum` → güncel durum metni
6. `son_guncelleme` → datetime.now().isoformat()

eğer stop tetiklendiyse:
1. pozisyonu `active.json`'dan kaldır
2. `closed.json`'a taşı (tüm zorunlu alanlarla: cikis_tarihi, cikis_fiyati, sonuc, ders)
3. `data/transactions.csv`'ye SELL satırı ekle
4. git commit: `[SWING-ÇIKIŞ] SEMBOL @FİYAT - Stop tetiklendi / Hedefe ulaştı`

---

## ADIM 7 — KALİTE KONTROL

- [ ] tüm aktif pozisyonların fiyatı güncellendi mi?
- [ ] stop mesafe hesaplamaları doğru mu?
- [ ] trailing stop güncellenmesi gereken pozisyon var mı?
- [ ] trailing stop sadece yukarı mı hareket etti? (aşağı çekilmediyse OK)
- [ ] stop tetiklenen pozisyon closed.json'a taşındı mı?
- [ ] watchlist'teki high urgency adaylar kontrol edildi mi?
- [ ] swing istatistik (ortalama, en iyi, en kötü) doğru mu?


---
---

# BÖLÜM 4: EARNINGS TAKVİMİ (bugün + önümüzdeki 7 gün)

> **amaç**: bugün açıklanacak earnings'leri öne çıkar, dün after-hours sonuçlarını özetle, haftalık takvim
> **tahmini FMP call**: 5-15 (takvim + portföy hissesi tahminleri)
> **tahmini websearch**: 2-4

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

### 1d. haftanın önemli earnings'leri için bağlam (2-4 websearch)

```
# SABAH RAPORU İÇİN KRİTİK:
websearch → "earnings results after hours yesterday {dünün tarihi}"
# dün kapanıştan sonra (AMC) açıklanan sonuçlar — bugünün açılışını etkiler

websearch → "earnings today before market open {bugünün tarihi}"
# bugün piyasa açılmadan (BMO) açıklanacak sonuçlar

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
## 4. earnings takvimi

### ⚡ portföy hisselerimizin earnings'leri

(eğer bu hafta portföy/swing hissemiz raporluyorsa)

| tarih | şirket | ticker | portföy | EPS tahmini | gelir tahmini | zamanlama |
|-------|--------|--------|---------|-------------|---------------|-----------|
| XX/XX | [isim] | [SYM] | [hangi portföy] | $X.XX | $X.XXB | BMO/AMC |

**etki analizi**: [bu earnings portföyümüzü nasıl etkiler, ne yapmalıyız]
**senaryo**: beat → [portföy etkisi] | miss → [portföy etkisi]

(eğer bu hafta yoksa: "bu hafta portföy hisselerimizden raporlayan yok ✅")

---

### 🔔 dün gece açıklanan sonuçlar (after-hours)

(dün AMC açıklananlar — bugünün açılışını doğrudan etkiler)

| şirket | ticker | EPS gerçekleşen | EPS beklenti | sürpriz | after-hours hareket |
|--------|--------|-----------------|--------------|---------|---------------------|
| [isim] | [SYM] | $X.XX | $X.XX | beat/miss | ▲/▼ %X.XX |

**bugüne etkisi**: [bu sonuçlar bugünün seansında hangi sektörleri/hisseleri etkiler?]

(websearch'ten gelir, FMP'de after-hours sonuçlar gecikebilir)

---

### bugün açıklanacak earnings (BMO — piyasa açılışı öncesi)

| şirket | ticker | piyasa değeri | EPS tahmini | gelir tahmini | sektör |
|--------|--------|---------------|-------------|---------------|--------|

⚠️ **dikkat**: BMO sonuçları TR 15:00-17:00 arası açıklanır, seansı doğrudan etkiler

---

### bugün kapanış sonrası (AMC — yarını etkiler)

| şirket | ticker | piyasa değeri | EPS tahmini | gelir tahmini | sektör |
|--------|--------|---------------|-------------|---------------|--------|

---

### earnings takvimi (önümüzdeki 7 gün, piyasa değeri > $2B)

#### [gün adı], [tarih]

**BMO:**
| şirket | ticker | sektör |

**AMC:**
| şirket | ticker | sektör |

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
bugün BMO açıklanacak sonuçlar açılışı nasıl etkileyebilir?
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


---
---

# BÖLÜM 5: CANSLIM HİSSE TARAMASI

> **amaç**: William O'Neil'in CANSLIM metodolojisi ile büyüme hissesi taraması
> **çalışma sıklığı**: HAFTADA 1 KEZ (pazar raporu — WEEKLY_REPORT'a dahil)
> **günlük raporda**: sadece referans satırı → "CANSLIM taraması pazar raporunda güncellenir"
> **tahmini FMP call**: ~80-100 (haftada 1 kez)
> **tahmini websearch**: 1-2

---

## CANSLIM KRİTERLERİ ÖZETİ

| harf | kriter | açıklama | ağırlık |
|------|--------|----------|---------|
| **C** | Current Quarterly Earnings | son çeyrek EPS büyümesi | %20 |
| **A** | Annual Earnings Growth | yıllık EPS büyüme trendi | %20 |
| **N** | New (yenilik/zirve yakınlığı) | yeni ürün/yönetim/zirve | %15 |
| **S** | Supply & Demand | düşük float + yüksek hacim | %10 |
| **L** | Leader or Laggard | sektöründe lider mi? | %15 |
| **I** | Institutional Sponsorship | kurumsal sahiplik artıyor mu? | %10 |
| **M** | Market Direction | genel piyasa yönü | %10 |

---

## ADIM 1 — PİYASA YÖNÜ KONTROLÜ (M kriteri)

bölüm 1'den SPY teknik durumunu al:

```
SPY > SMA50 > SMA200  → M = 10/10 "onaylı yükseliş"
SPY > SMA200, < SMA50  → M = 6/10  "karışık, dikkatli ol"
SPY < SMA200           → M = 3/10  "düşüş trendi — CANSLIM girişleri riskli"
                         ⚠️ uyarı ekle: "piyasa yönü olumsuz, yeni alım için bekle"
```

---

## ADIM 2 — ADAY HAVUZU OLUŞTUR (2 aşamalı filtre)

### aşama 1: kaba filtre (1-2 FMP call)

```python
# company-screener ile temel filtre
# ⚠️ doğru endpoint: "company-screener" ("stock-screener" DEĞİL)
adaylar = fmp_get("company-screener", {
    "marketCapMoreThan": 2000000000,      # $2B+ piyasa değeri
    "marketCapLowerThan": 200000000000,   # $200B altı (mega-cap hariç, onlar zaten yavaş büyür)
    "priceMoreThan": 10,                  # penny stock hariç
    "volumeMoreThan": 500000,             # günlük 500K+ hacim (likidite)
    "isActivelyTrading": "true",
    "exchange": "NYSE,NASDAQ",
    "limit": 100                          # ilk 100 aday
})
```

### aşama 2: 52-hafta zirvesine yakınlık filtresi (0 ekstra call)

```python
# screener sonuçlarında yearHigh alanı varsa kullan
# yoksa batch-quote ile çek (1 call)
# sadece 52W zirvesinden ≤%15 uzakta olanları tut

filtreli = []
for aday in adaylar:
    if aday.get('price') and aday.get('yearHigh'):
        zirve_uzaklik = ((aday['yearHigh'] - aday['price']) / aday['yearHigh']) * 100
        if zirve_uzaklik <= 15:
            filtreli.append(aday)

# bu filtre genellikle 100 → 30-40 adaya düşürür
# sonra ilk 20'yi al (en yüksek piyasa değerine göre sırala)
en_iyi_20 = sorted(filtreli, key=lambda x: x.get('marketCap', 0), reverse=True)[:20]
```

---

## ADIM 3 — DETAYLI SKORLAMA (20 aday için)

her aday için aşağıdaki FMP call'ları yap:

```python
for aday in en_iyi_20:
    symbol = aday['symbol']
    
    # C + A kriterleri için (1 call)
    income_q = fmp_get("income-statement", {
        "symbol": symbol, "period": "quarter", "limit": 8
    })
    
    # A kriteri için yıllık (1 call)
    income_a = fmp_get("income-statement", {
        "symbol": symbol, "period": "annual", "limit": 5
    })
    
    # S kriteri için float (1 call)
    float_data = fmp_get("shares-float", {"symbol": symbol})
    
    # I kriteri için kurumsal sahiplik (1 call)
    institutional = fmp_get("institutional-holders", {
        "symbol": symbol, "limit": 10
    })

# 20 aday × 4 call = 80 call
# + screener 1-2 call + batch-quote 1 call
# TOPLAM: ~83 call
```

---

## ADIM 4 — HER KRİTER NASIL SKORLANIR

### C — Current Quarterly Earnings (max 20 puan)

```python
# income-statement quarter verilerinden:
son_ceyrek_eps = income_q[0]['eps']
onceki_yil_ayni_ceyrek_eps = income_q[4]['eps']  # 4 çeyrek öncesi = geçen yıl aynı çeyrek

eps_buyume = ((son_ceyrek_eps - onceki_yil_ayni_ceyrek_eps) / abs(onceki_yil_ayni_ceyrek_eps)) * 100

# SKORLAMA:
# eps_buyume > %50    → 20/20
# eps_buyume %25-%50  → 16/20
# eps_buyume %10-%25  → 12/20
# eps_buyume %0-%10   → 8/20
# eps_buyume < %0     → 0/20

# BONUS: son 2 çeyrek üst üste hızlanma (accelerating) → +2 puan (max 20)
# hızlanma = bu çeyrek büyüme > geçen çeyrek büyüme
```

### A — Annual Earnings Growth (max 20 puan)

```python
# income-statement annual verilerinden:
# 3 yıllık EPS büyüme trendi

yillik_eps = [income_a[i]['eps'] for i in range(min(5, len(income_a)))]
# yillik_eps[0] = en güncel yıl, yillik_eps[4] = 5 yıl önce

# 3 yıllık ortalama büyüme hesapla
if len(yillik_eps) >= 4 and yillik_eps[3] > 0:
    buyume_3y = ((yillik_eps[0] / yillik_eps[3]) ** (1/3) - 1) * 100  # CAGR
else:
    buyume_3y = 0

# ROE kontrolü (key-metrics-ttm'den veya hesaplayarak)
# basit yöntem: income-statement'tan net income / balance sheet equity
# ama ekstra call gerekir, alternatif: ratios-ttm (1 call daha eklenebilir)

# SKORLAMA:
# CAGR > %25 + her yıl artış  → 20/20
# CAGR > %25                   → 16/20
# CAGR %15-%25                 → 12/20
# CAGR %5-%15                  → 8/20
# CAGR < %5 veya düzensiz      → 4/20
# negatif büyüme               → 0/20
```

### N — New (yenilik + 52W zirve yakınlığı) (max 15 puan)

```python
# batch-quote veya screener verisinden:
fiyat = aday['price']
zirve_52w = aday['yearHigh']
zirve_uzaklik_pct = ((zirve_52w - fiyat) / zirve_52w) * 100

# SKORLAMA:
# zirve_uzaklik < %5 (zirveye çok yakın)   → 15/15
# zirve_uzaklik %5-%10                      → 12/15
# zirve_uzaklik %10-%15                     → 8/15
# zirve_uzaklik > %15                       → aday zaten filtrede elenmiş olmalı

# NOT: "yeni ürün/yönetim" bilgisi FMP'den alınamaz
# websearch ile teyit edilebilir ama her hisse için yapma, sadece final top 5 için
```

### S — Supply & Demand (max 10 puan)

```python
# shares-float verisinden:
float_shares = float_data[0].get('floatShares', 0)
outstanding = float_data[0].get('outstandingShares', 0)

# düşük float = arz kısıtlı = fiyat hareketi daha sert
# batch-quote'tan: ortalama hacim vs son gün hacim karşılaştırması

hacim_orani = aday.get('volume', 0) / aday.get('avgVolume', 1)  # avgVolume varsa

# SKORLAMA:
# float < 100M + hacim_orani > 1.5  → 10/10 (az arz + yüksek talep)
# float < 100M                       → 8/10
# float 100M-500M + hacim_orani > 1.3 → 7/10
# float 100M-500M                    → 5/10
# float > 500M                       → 3/10
# float > 1B                         → 1/10 (çok fazla arz)
```

### L — Leader or Laggard (max 15 puan)

```python
# hisse sektöründe lider mi laggard mı?
# stock-price-change ile 3 aylık performans karşılaştır

hisse_3ay = fmp_get("stock-price-change", {"symbol": symbol})
# dönen veri: 1M, 3M, 6M, 1Y gibi % değişimler

# sektör ETF'i ile karşılaştır:
# Technology → XLK, Energy → XLE, Healthcare → XLV, vb.
sektor_etf_3ay = ... # aynı endpoint ile sektör ETF'in 3 aylık değişimi

# relative strength = hisse 3M% - sektör ETF 3M%
rs = hisse_3ay['3M'] - sektor_etf_3ay['3M']

# SKORLAMA:
# rs > +15% (sektörden çok iyi)    → 15/15
# rs > +5%                          → 12/15
# rs %0 ile +5% arası               → 8/15
# rs < %0 (sektörden kötü)          → 4/15
# rs < -%10 (ciddi laggard)         → 0/15

# ⚠️ her hisse için stock-price-change zaten bölüm 2'de çekilmiş olabilir
# sektör ETF'leri için de çekmek lazım (max 11 sektör ETF → 11 call ekstra)
# OPTİMİZASYON: sektör ETF performanslarını bölüm 1'deki sector-performance-snapshot'tan türet
```

### I — Institutional Sponsorship (max 10 puan)

```python
# institutional-holders verisinden:
# son çeyrek vs önceki çeyrek karşılaştır
# holder sayısı artıyor mu? toplam sahiplik yüzdesi artıyor mu?

holders = fmp_get("institutional-holders", {"symbol": symbol, "limit": 10})

# FMP'de dönem karşılaştırması sınırlı olabilir
# basit yöntem: toplam kurumsal holder sayısı + bilinen büyük fonlar var mı?

# SKORLAMA:
# büyük fon girişi var (Vanguard, BlackRock, Fidelity artırıyor) → 10/10
# kurumsal sahiplik > %60                                         → 8/10
# kurumsal sahiplik %40-%60                                       → 6/10
# kurumsal sahiplik < %40                                         → 3/10
# veri yok veya çok düşük                                         → 1/10
```

### M — Market Direction (max 10 puan)

```
# adım 1'de zaten hesaplandı, tüm adaylar için aynı skor
# SPY > SMA50 > SMA200  → 10/10
# SPY > SMA200, < SMA50 → 6/10
# SPY < SMA200          → 3/10
```

---

## ADIM 5 — SIRALAMA VE FİNAL TOP 5

```python
# toplam skor hesapla (max 100 puan)
toplam = C + A + N + S + L + I + M

# sırala, en yüksek 5'i seç
final_top5 = sorted(adaylar_skorlu, key=lambda x: x['toplam'], reverse=True)[:5]

# skor bantları:
# 85+   → "olağanüstü" (exceptional)
# 70-84 → "güçlü" (strong)
# 55-69 → "ortanın üstü" (above average)
# 40-54 → "orta" (average)
# < 40  → "zayıf" (weak) — top 5'e girmemeli
```

---

## ADIM 6 — RAPOR ÇIKTI FORMATI (haftalık rapor için)

```markdown
## 5. CANSLIM hisse taraması

**tarama tarihi**: [tarih] | **piyasa yönü (M)**: [durum] [skor]/10
**aday havuzu**: [screener'dan X hisse] → [52W filtre sonrası Y hisse] → [detaylı analiz Z hisse] → **top 5**

### sonuç tablosu

| # | ticker | şirket | sektör | C | A | N | S | L | I | M | toplam | değerlendirme |
|---|--------|--------|--------|---|---|---|---|---|---|---|--------|---------------|
| 1 | [SYM] | [isim] | [sektör] | XX | XX | XX | XX | XX | XX | XX | XX/100 | [olağanüstü/güçlü/...] |
| 2 | | | | | | | | | | | | |
| 3 | | | | | | | | | | | | |
| 4 | | | | | | | | | | | | |
| 5 | | | | | | | | | | | | |

### hisse detayları

**1. [TICKER] — [ŞİRKET] ([SEKTÖR])** — toplam: XX/100 [değerlendirme]
- **C** (XX/20): son çeyrek EPS büyümesi +%XX (YoY), [hızlanma var/yok]
- **A** (XX/20): 3 yıllık CAGR +%XX, [her yıl artış / düzensiz]
- **N** (XX/15): 52W zirvesinden -%XX, [yakın/uzak]
- **S** (XX/10): float XXM hisse, hacim oranı X.Xx
- **L** (XX/15): 3 aylık RS +%XX (sektöre göre), [lider/laggard]
- **I** (XX/10): kurumsal sahiplik %XX, [büyük fon girişi var/yok]
- **yorum**: [2-3 cümle: neden bu hisse ilginç, risk ne, potansiyel portföy uyumu]

(her 5 hisse için aynı format)

### agresif portföy için uygunluk

[top 5'ten hangisi agresif büyüme portföyüne uygun? neden?
mevcut pozisyonlarla korelasyon kontrolü.
önerilen giriş stratejisi (kademeli mi, tek seferde mi)]
```

### günlük rapordaki referans satırı

```markdown
## 5. CANSLIM taraması

son tarama: [tarih] | top 5: [SYM1], [SYM2], [SYM3], [SYM4], [SYM5]
detaylar haftalık raporda → reports/weekly/WEEKLY_REPORT_YYYY-MM-DD.md
```

---

## ADIM 7 — API MALİYET ÖZETİ

| işlem | call sayısı |
|-------|-------------|
| company-screener | 1 |
| batch-quote (52W filtre) | 1 |
| income-statement quarterly (20 aday) | 20 |
| income-statement annual (20 aday) | 20 |
| shares-float (20 aday) | 20 |
| institutional-holders (20 aday) | 20 |
| stock-price-change (bölüm 2'de yoksa) | 0-20 |
| **toplam** | **82-102** |

haftada 1 kez = günlük ortalama ~14 call (7 güne böl)

---

## ADIM 8 — KALİTE KONTROL

- [ ] company-screener kullanıldı mı? (stock-screener DEĞİL)
- [ ] 52W zirve filtresi ≤%15 uygulandı mı?
- [ ] EPS büyümesi YoY (yıldan yıla aynı çeyrek) karşılaştırma mı? (QoQ değil)
- [ ] M kriteri tüm adaylar için aynı mı?
- [ ] L kriteri sektör ETF'e göre göreceli mi? (mutlak performans değil)
- [ ] skor toplamı 100'ü geçmiyor mu?
- [ ] top 5'in hepsi skor > 40 mı?
- [ ] agresif portföy uygunluk değerlendirmesi yapıldı mı?
- [ ] günlük raporda sadece referans satırı var mı? (tam tarama yok)


---
---

# BÖLÜM 6: SONUÇ VE AKSİYON PLANI (bugünün seansı için)

> **amaç**: tüm bölümleri sentezle, bugünün seansındaki öncelikleri belirle
> **tahmini FMP call**: 0 (tüm veri önceki bölümlerden geliyor)
> **tahmini websearch**: 0

---

## ADIM 1 — GÜNÜN ÖZETİ

önceki 5 bölümden çıkan bilgileri sentezle:

```
TOPLA:
- bölüm 1'den: risk duyarlılığı, SPY trend, en önemli haber
- bölüm 2'den: portföy toplam değer/k/z, en iyi/en kötü hisse, uyarılar
- bölüm 3'ten: swing aksiyon gerektiren pozisyonlar, stop durumları
- bölüm 4'ten: yarın/bu hafta önemli earnings
- bölüm 5'ten: (sadece pazar) CANSLIM top 5 referansı
```

---

## ADIM 2 — RAPOR ÇIKTI FORMATI

```markdown
## 6. sonuç ve aksiyon planı

### günün özeti

**tarih**: [gün adı], [bugünün tarihi] (seans öncesi rapor)
**toplam portföy** (dünün kapanışı): $XXX,XXX (+$XX,XXX / +%X.XX)
**dünkü değişim**: [+/-$X,XXX] | SPY dün: [+/-%X.XX]
**risk ortamı**: [Risk-On 🟢 / Risk-Off 🔴 / Nötr ⚪]
**futures**: S&P [+/-%X.XX] | NASDAQ [+/-%X.XX] → [pozitif/negatif/düz açılış beklentisi]

**bir cümlede durum**: [dünü + bugünün beklentisini özetleyen tek cümle.
örnek: "dün tech satışı agresif portföyü vurdu ama futures pozitif,
bugün toparlanma şansı var. temettü portföy +%16.6 ile lider."]

### portföy skor kartı

| portföy | değer | k/z % | günlük | trend | not |
|---------|-------|-------|--------|-------|-----|
| dengeli | $XXX,XXX | +%X.XX | ▲/▼ | [iyileşiyor/kötüleşiyor/stabil] | [1 kelime] |
| agresif | $XXX,XXX | -%X.XX | ▲/▼ | | |
| temettü | $XXX,XXX | +%XX.XX | ▲/▼ | | 🏆 |
| rotasyon | $XXX,XXX | +%X.XX | ▲/▼ | | |
| swing | X/10 aktif | +%X.XX ort | | | |

---

### 🔴 acil aksiyonlar (bugün/yarın yapılması gereken)

(bu bölüm boş olabilir — her gün acil aksiyon olmak zorunda değil)

1. **[AKSİYON]** — [SEMBOL] ([portföy/swing])
   - durum: [neden acil]
   - öneri: [somut aksiyon + fiyat seviyesi]
   - zamanlama: [yarın açılışta / kapanışa kadar / bu hafta]

2. ...

### 🟡 izlenmesi gerekenler (bu hafta)

1. **[SEMBOL]** — [kısa açıklama]
   - tetikleyici: [ne olursa aksiyon alınır]

2. ...

### 🟢 fırsatlar

1. **[SEMBOL]** — [kısa açıklama]
   - koşul: [hangi fiyat/RSI/olay gerçekleşirse giriş düşünülür]
   - hedef portföy: [agresif / swing / dengeli]

---

### bugünün seansı için plan

**pre-market** (TR 16:00-17:30):
- [ ] [kontrol 1: örn. BMO earnings sonuçları açıklandı mı?]
- [ ] [kontrol 2: örn. futures yönü rapordakiyle uyuşuyor mu?]
- [ ] [kontrol 3: örn. NEM pre-market fiyatı, stop seviyesine yakın mı?]

**seans açılışı** (TR 17:30 — ilk 30 dakika):
- [ ] [aksiyon 1: örn. açılış gap varsa panik satış YAPMA, 15 dk bekle]
- [ ] [aksiyon 2: örn. NEM stop $122.50 tetiklenirse kapat]
- [ ] [aksiyon 3: örn. SHOP $115 altına düşerse stop değerlendir]

**seans ortası** (TR 19:00-22:00):
- [ ] [aksiyon 1: örn. swing watchlist'teki SEMBOL hedefe yaklaştı mı?]
- [ ] [aksiyon 2: varsa yeni giriş planı — limit emir fiyatı: $XX.XX]

**kapanışa doğru** (TR 23:00-00:00):
- [ ] [bekleyen emir: örn. kapanışta kısmi kar al SEMBOL %50]
- [ ] [not: bugün AMC earnings açıklanacak hisseler, yarını etkiler]

**kapanış sonrası**:
- [ ] fiyat güncellemesi (JSON + git push)
- [ ] [varsa: AMC earnings sonuçlarını kontrol et]

---

### haftalık bakış (sadece cuma raporu)

(pazartesi-perşembe raporlarında bu bölüm olmaz, sadece cuma günü ekle)

- haftanın en iyi hissesi: [SEMBOL] +%XX
- haftanın en kötü hissesi: [SEMBOL] -%XX
- haftalık toplam portföy değişimi: +/-$XX,XXX (+/-%X.XX)
- haftanın dersi: [1 cümle]
- gelecek hafta dikkat: [earnings, makro olay, teknik seviye]
```

---

## ADIM 3 — AKSİYON ÖNCELİKLENDİRME KURALLARI

```
ÖNCELİK SIRASI (yukarıdan aşağıya):

1. STOP TETİKLENEN POZİSYON      → hemen kapat, tartışma yok
2. HEDEFE ULAŞAN POZİSYON        → partial exit planını uygula
3. STOP'A ÇOK YAKIN (<%1)        → yarın açılışta karar ver
4. SÜRE AŞIMI + ZARAR            → tezi değerlendir, çıkış düşün
5. EARNINGS ÖNCESİ POZİSYON      → hedge veya küçült
6. RSI AŞIRI ALIM + BÜYÜK KAR    → kısmi kar al
7. RSI AŞIRI SATIM + GÜÇLÜ TREND → fırsat, giriş planla
8. WATCHLIST GİRİŞ KOŞULU SAĞLANDI → giriş planla
9. REBALANCE İHTİYACI             → hesapla, planla
10. YENİ ARAŞTIRMA                → not al, acele etme

her aksiyon önerisinde:
- somut fiyat seviyesi ver (sadece "izle" deme)
- hangi portföy/swing olduğunu belirt
- risk/ödül oranını hatırlat
```

---

## ADIM 4 — RAPOR SONU

```markdown
---

> günlük rapor sonu | finzora ai | [bugünün tarihi] [saat]
> NYSE açılış: bugün 17:30 (TR) | kapanış: 00:00 (TR)
> sonraki: seans içi aksiyon (SESSION_ACTION_PROMPT) → TR 18:00+
> sonraki rapor: yarın ~14:00 TR
```

---

## ADIM 5 — KALİTE KONTROL

- [ ] günün özeti tüm bölümlerden bilgi içeriyor mu?
- [ ] futures bilgisi eklendi mi? (sabah raporu için kritik)
- [ ] "dünün kapanışı" ve "bugünün beklentisi" net ayrılmış mı?
- [ ] acil aksiyonlar gerçekten acil mi? (her gün acil aksiyon olmak zorunda değil)
- [ ] fırsatlar somut koşula bağlı mı? ("güzel hisse" değil, "$XX altına düşerse")
- [ ] bugünün planı seans saatlerine göre bölünmüş mü? (pre-market / açılış / orta / kapanış)
- [ ] aksiyon önerilerinde fiyat seviyesi var mı?
- [ ] cuma günü haftalık bakış eklendi mi?
- [ ] rapor sonu satırı var mı?
