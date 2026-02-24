# SEANS İÇİ AKSİYON PROMPT — v1.0

> **versiyon**: 1.0 | **oluşturma**: 24 şubat 2026
> **çalışma zamanı**: NYSE açıldıktan sonra (TR 17:30+), tercihen açılıştan 30-60dk sonra
> **ön koşul**: o günün sabah raporu zaten yazılmış olmalı
> **perspektif**: PİYASA AÇIK — GERÇEK ZAMANLI KARAR VE AKSİYON
> **fiyat verisi**: canlı/güncel fiyatlar (FMP quote = bugünün verisi)
> **çıktı**: doğrudan JSON güncelleme + trade kararları + git push
> **dil**: küçük harf türkçe, teknik terimler ingilizce kalabilir
> **kaynak atfı**: sadece "finzora ai" kullan
> **format kuralları**: em dash kullanma

---

## SEANS ÖNCESİ vs SEANS İÇİ — FARK

| | sabah raporu (seans öncesi) | seans içi aksiyon (bu prompt) |
|---|---|---|
| **ne zaman** | NYSE açılmadan önce | NYSE açıldıktan 30-60dk sonra |
| **fiyat** | dünün kapanışı | bugünün canlı fiyatı |
| **amaç** | analiz + plan | karar + uygulama |
| **çıktı** | rapor dosyası (.md) | JSON güncelleme + trade emirleri |
| **ton** | "bugün şunu izleyeceğiz" | "şu anda şunu yapıyoruz" |

---

## ÇALIŞTIRMA KOMUTU

kullanıcı şunlardan birini söylediğinde bu prompt devreye girer:
- "piyasa açıldı, kontrol et"
- "seans içi güncelleme"
- "piyasa nasıl, ne yapıyoruz?"
- "açılış sonrası analiz"
- veya doğrudan bu prompt dosyasını referans verdiğinde

---

## ANA AKIŞ (5 AŞAMA)

```
AŞAMA 1: VERİ TOPLAMA (canlı fiyatlar + piyasa durumu)
    │
AŞAMA 2: DURUM TESPİTİ (sabah raporuyla karşılaştır)
    │
AŞAMA 3: AKSİYON KARARLARI (al/sat/tut/izle)
    │
AŞAMA 4: UYGULAMA (JSON güncelle, trade yap, git push)
    │
AŞAMA 5: ÖZET RAPOR (kullanıcıya sun)
```

---

# AŞAMA 1 — VERİ TOPLAMA

## 1a. piyasa genel durumu (canlı)

**FMP çağrıları**:
```python
# endeksler
spy = fmp_get("quote", {"symbol": "SPY"})
qqq = fmp_get("quote", {"symbol": "QQQ"})
dia = fmp_get("quote", {"symbol": "DIA"})
iwm = fmp_get("quote", {"symbol": "IWM"})  # russell 2000

# emtia + forex
gold = fmp_get("quote", {"symbol": "GCUSD"})
oil = fmp_get("quote", {"symbol": "CLUSD"})
usdtry = fmp_get("quote", {"symbol": "USDTRY"})

# treasury
treasury = fmp_get("treasury-rates", {"from": TODAY, "to": TODAY})
```

**websearch** (2-3 arama):
```
- "stock market today {DATE} live"
- "VIX index today"
- varsa özel haber/olay araması (sabah raporunda bekleniyorsa)
```

**sektör performansı**:
```python
sectors = fmp_get("sector-performance-snapshot", {"date": TODAY})
```

**market movers** (açılışta neler olmuş):
```python
gainers = fmp_get("biggest-gainers", {"limit": 10})
losers = fmp_get("biggest-losers", {"limit": 10})
```

**toplam**: ~8-10 FMP call + 2-3 websearch

## 1b. portföy hisseleri (canlı fiyat + teknik)

**tüm portföy + swing sembollerini birleştir** (benzersiz liste):
```python
# 4 portföy JSON + swing active.json oku
# benzersiz sembol listesi çıkar
# batch quote çek
quotes = fmp_get("batch-quote", {"symbols": "SM,KOS,MO,XLE,RGLD,..."})
```

**her sembol için teknik göstergeler**:
```python
for symbol in unique_symbols:
    rsi = fmp_get("technical-indicators/rsi", {"symbol": symbol, "periodLength": 14, "timeframe": "1day"})
    sma50 = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 50, "timeframe": "1day"})
    sma200 = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 200, "timeframe": "1day"})
```

**toplam**: ~1 (batch) + 3×N (teknik) — N = benzersiz sembol sayısı (~25 = ~76 call)

## 1c. haber kontrolü (portföy hisseleri)

```python
# portföy hisselerinin haberleri
news = fmp_get("news/stock", {"symbols": ALL_SYMBOLS, "limit": 30})
```

**websearch**: sabah raporundaki beklenen olaylara özel arama
- earnings sonuçları (BMO olanlar açılışta gelmiş olabilir)
- makro veriler (consumer confidence, PMI vb.)
- geopolitik gelişmeler

**toplam**: 1 FMP call + 2-4 websearch

## 1d. sektör RS analizi (canlı)

sabah raporundaki RS analizini canlı verilerle güncelle:
```
sektor_rs = sektor_degisim - SPY_degisim

sinyaller:
- SPY düşerken RS > +1.0% → 🔥 GÜÇ SEKTÖR (para buraya akıyor)
- SPY düşerken RS > +0.5% → 💪 dirençli
- SPY yükselirken RS < -1.0% → ⚠️ ZAYIF SEKTÖR
```

## toplam API bütçesi (aşama 1)

| kaynak | çağrı sayısı |
|--------|-------------|
| endeks + emtia + forex | ~8 |
| sektör + movers | ~3 |
| portföy batch quote | ~1 |
| teknik göstergeler (25 sembol × 3) | ~75 |
| haberler | ~1 |
| **FMP toplam** | **~88** |
| **websearch** | **4-7** |

⚠️ sabah raporu ~100 call kullandıysa, günlük toplam ~190 / 2,500 limit = **%7.6** (güvenli)

---

# AŞAMA 2 — DURUM TESPİTİ

## 2a. sabah raporu ile karşılaştırma

sabah raporunu oku (`reports/daily/DAILY_REPORT_{TODAY}.md`) ve şu soruları cevapla:

**piyasa beklentisi tuttu mu?**
- sabah: "futures +%0.3, hafif toparlanma bekleniyor" → gerçek: SPY ?
- beklenen/beklenmeyen gelişmeler neler?

**risk ortamı değişti mi?**
- sabah: RISK-OFF/RISK-ON → şu an: ?
- VIX yönü: yükseliyor mu düşüyor mu?

**sektör RS değişti mi?**
- sabah güçlü olan sektörler hala güçlü mü?
- yeni güçlenen/zayıflayan sektör var mı?

## 2b. her portföy pozisyonu durum tespiti

her pozisyon için tek satırda durum:

```
format: SEMBOL | fiyat | günlük % | RSI | SMA50 vs | SMA200 vs | durum

durum kodları:
✅ GÜÇLÜ — trend yukarı, RSI 50-70, SMA'lar üzerinde
⚠️ DİKKAT — SMA kırılımı yakın, RSI aşırı bölgede, stop yakın
🔴 ACİL — stop-loss tetiklendi/tetiklenecek, büyük kayıp
💰 KAR AL — hedefe ulaştı veya aşırı alım
🔄 NÖTR — bekle, sinyal yok
```

**otomatik uyarı tetikleyicileri**:
- günlük değişim > +%5 veya < -%5 → acil inceleme
- RSI > 75 → aşırı alım uyarısı
- RSI < 30 → aşırı satım (fırsat mı tehlike mi?)
- fiyat SMA50 altına düştü → trend zayıflama
- fiyat SMA200 altına düştü → uzun vadeli trend kırılması
- stop-loss'a mesafe < %2 → acil uyarı
- portföy ağırlığı > %25 → yoğunlaşma riski

## 2c. swing pozisyonları durum tespiti

her swing pozisyonu için:

```
format: ID | SEMBOL | giriş | güncel | k/z% | stop | hedefe mesafe | trailing | durum

durum kodları:
🎯 HEDEF YAKLAŞTI — hedef fiyata %2 içinde
⚠️ STOP YAKIN — stop'a %2 içinde
📈 TREND GÜÇLÜ — momentum devam ediyor
📉 ZAYIFLIYOR — momentum kaybediyor
🔄 trailing aktif — zirveden -%5 takip ediyor
```

**trailing stop güncelleme kuralı**:
```
eğer güncel_fiyat > önceki_zirve:
    yeni_trailing_stop = güncel_fiyat × 0.95
    eğer yeni_trailing_stop > mevcut_trailing_stop:
        trailing_stop = yeni_trailing_stop  # sadece yukarı güncelle
```

---

# AŞAMA 3 — AKSİYON KARARLARI

## 3a. karar matrisi — portföyler

her pozisyon için şu ağaçtan geç:

```
1. STOP-LOSS TETİKLENDİ Mİ?
   evet → 🔴 HEMEN SAT (duygusal karar yok)
   hayır → devam

2. HEDEF FİYATA ULAŞTI MI?
   evet → 💰 kar al (kısmi/tam)
   hayır → devam

3. TEZ BOZULDU MU?
   - temel verilerde kötüleşme? (earnings miss, temettü kesintisi, guidance düşürme)
   - sektör yapısal zayıflama? (sadece günlük dalgalanma değil)
   - korelasyon riski? (aynı sektörde çok fazla yoğunlaşma)
   evet → ⚠️ pozisyon küçült veya kapat
   hayır → devam

4. PORTFÖY DENGESİ BOZULDU MU?
   - bir pozisyon > %25 ağırlık?
   - bir sektör > %40 ağırlık?
   evet → 🔄 rebalance düşün
   hayır → devam

5. TEKNİK DURUM?
   - RSI > 75 + SMA'lar üzerinde → kar alma düşünülebilir
   - RSI < 30 + SMA'lar üzerinde → dip alım fırsatı
   - SMA200 altına kırılım → trend dönüşü uyarısı

6. HİÇBİR TETİK YOK → ✅ TUT, bir sonraki güne bekle
```

## 3b. karar matrisi — swing trade

her swing pozisyonu için:

```
1. STOP-LOSS KESİLDİ Mİ?
   fiyat < stop_loss → 🔴 %100 SAT, closed.json'a kaydet
   hayır → devam

2. HEDEF FIYATA ULAŞTI MI?
   fiyat >= hedef_fiyat → 💰 partial exit planını uygula:
     - %50 sat (kar garantile)
     - kalan %50 trailing stop kur (hedeften -%5)
   hayır → devam

3. TRAİLİNG STOP TETİKLENDİ Mİ?
   trailing aktif VE fiyat < trailing_stop → 🔴 kalan pozisyonu sat
   hayır → devam

4. TRAİLİNG STOP GÜNCELLE
   fiyat > önceki zirve → trailing stop yukarı çek
   (trailing stop ASLA aşağı çekilmez)

5. MOMENTUM DURUMU?
   - RSI yükseliyor + hacim artıyor → 📈 momentum güçlü, tut
   - RSI düşüyor + hacim azalıyor → 📉 zayıflıyor, trailing sıkılaştır
   - sektör RS zayıflıyor → dikkat, sektör rotasyonu başlamış olabilir

6. HİÇBİR TETİK YOK → ✅ TUT, trailing kontrol et
```

## 3c. yeni pozisyon fırsatları

### swing watchlist tarama

**aday kaynakları**:
1. sabah raporundaki güçlü sektörlerden (RS > +1.0%)
2. biggest-gainers listesinden (momentum)
3. earnings beat eden hisselerden (BMO sonuçları açılışta gelir)
4. mevcut watchlist'ten tetiklenen seviyeler

**filtre kriterleri**:
```
- market cap > $2B
- günlük hacim > ortalama 1.2x
- RSI 30-65 arası (aşırı alımda değil)
- fiyat SMA50 üzerinde (veya SMA50'ye yaklaşan RSI < 35 dip alım)
- 5 günlük momentum > +%3
- mevcut açık slot var mı? (max 10 - aktif sayı = boş slot)
```

**her aday için zorunlu analiz**:
```
1. teknik: RSI, SMA50, SMA200, 5 günlük momentum, hacim
2. temel: son earnings, P/E, sektör durumu
3. risk: stop seviyesi, R:R oranı (min 2:1)
4. hedef: +%10 hedef fiyat gerçekçi mi?
5. katalizör: neden şimdi? yaklaşan earnings, sektör rotasyonu, momentum...
6. portföy korelasyonu: mevcut pozisyonlarla çakışma var mı?
```

### portföy yeni ekleme fırsatları

**her portföy için ayrı filtre**:

**dengeli portföy**: multi-sector value + momentum
- güçlü sektör RS gösteren hisseler
- P/E makul (<25), momentum pozitif
- mevcut sektör dağılımıyla çakışmayan

**agresif büyüme**: tech/AI momentum, earnings surprise
- earnings beat > %10
- RS yükseliş trendi
- fiyat SMA50 üzerinde, volume 1.5x+
- ⚠️ mevcut nakit oranı yüksekse (%50+) ve piyasa toparlanıyorsa → kademeli giriş fırsatı

**değer + temettü**: düşük P/E, yüksek temettü, güçlü FCF
- P/E < 20, temettü yield > %3
- D/E < 1.5, FCF pozitif
- temettü artış geçmişi
- güçlü sektör RS (özellikle consumer defensive, utilities, healthcare)

**sektör rotasyonu**: makro döngüye göre ETF
- RS analizi en güçlü sektör ETF'leri
- mevcut pozisyonlarda zayıf sektör varsa → rotasyon düşün
- çeyreklik rebalance zamanı yaklaşıyor mu?

## 3d. satış/çıkış değerlendirmesi

**portföy hissesi satış nedenleri**:
```
1. stop-loss tetiklendi (portföy tipine göre: agresif %8, diğerleri %10-15)
2. tez bozuldu (temel verilerde kötüleşme)
3. sektör RS sürekli zayıf (3+ gün negatif RS, trend dönüşü)
4. daha iyi fırsat var (aynı sektörde/temada daha güçlü alternatif)
5. portföy ağırlık dengesizliği
6. kar realizasyonu (özellikle RSI > 75 + hedef aşılmış)
```

**satış kararı onay süreci**:
```
- acil satışlar (stop tetiklendi): kullanıcıya bilgi ver, JSON güncelle
- stratejik satışlar (tez bozulması, rotasyon): kullanıcıya neden+alternatif sun, onay bekle
- kar alma: kullanıcıya öner, karar kullanıcıda
```

---

# AŞAMA 4 — UYGULAMA

## 4a. trade işlemleri

**her satış için**:
1. portföy JSON'undan pozisyonu kaldır
2. `nakit.miktar += adet × satis_fiyati`
3. portföy `transactions[]` listesine SATIŞ kaydı ekle
4. `data/transactions.csv` dosyasına satır ekle
5. swing ise → `data/swing/closed.json`'a ekle (tüm zorunlu alanlar: cikis_tarihi, cikis_fiyati, kar_zarar_yuzde, cikis_nedeni, sonuc, ders)
6. `data/summary.json` güncelle

**her alış için**:
1. portföy JSON'unda `pozisyonlar[]` dizisine ekle (tüm zorunlu alanlar)
2. `nakit.miktar -= adet × fiyat`
3. portföy `transactions[]` listesine ALIŞ kaydı ekle
4. `data/transactions.csv` dosyasına satır ekle
5. swing ise → `data/swing/active.json`'a ekle (tüm zorunlu alanlar: id, giris_tarihi, giris_fiyati, hedef_fiyat, stop_loss, giris_nedeni, katalizor, tez, zaman_cercevesi, risk, tarama_yontemi, partial_exit_plan)
6. `data/summary.json` güncelle

## 4b. fiyat güncellemesi

trade olmasa bile tüm JSON dosyalarını güncelle:
```python
for each portfolio JSON:
    for each position:
        guncel_fiyat = quote['price']
        gunluk_degisim_yuzde = quote['changesPercentage']
        guncel_deger = adet × guncel_fiyat
        kar_zarar = guncel_deger - yatirim
        kar_zarar_yuzde = (kar_zarar / yatirim) × 100
        agirlik_yuzde = (guncel_deger / toplam_deger) × 100
        son_guncelleme = datetime.now().isoformat()
    
    toplam_deger = sum(pozisyon.guncel_deger) + nakit.miktar
    toplam_getiri_yuzde = ((toplam_deger - baslangic_sermaye) / baslangic_sermaye) × 100

for swing active:
    for each position:
        guncel_fiyat = quote['price']
        guncel_kar_zarar_yuzde = ((guncel - giris) / giris) × 100
        tutulan_gun = (today - giris_tarihi).days
        trailing stop güncelle (sadece yukarı)
        son_guncelleme = datetime.now().isoformat()
```

## 4c. watchlist güncellemesi

`data/swing/watchlist.json` güncelle:
```
- mevcut adayların fiyatlarını güncelle
- tetiklenen giriş seviyesi varsa → "urgency": "high" yap
- artık geçerli olmayan adayları haric_tutulanlar'a taşı (neden ile)
- yeni aday varsa ekle (tüm alanlar: sembol, guncel_fiyat, momentum_5gun, sektor, notlar, urgency, hedef_giris, hedef_fiyat, stop_loss)
```

## 4d. git commit + push

```bash
# trade varsa:
git commit -m "[ALIŞ] Portföy - SEMBOL @FİYAT - neden"
git commit -m "[SATIŞ] Portföy - SEMBOL @FİYAT - neden"
git commit -m "[SWING-GİRİŞ] SEMBOL @FİYAT - neden"
git commit -m "[SWING-ÇIKIŞ] SEMBOL @FİYAT - sonuç +/-%X"

# trade yoksa:
git commit -m "[GÜNCELLEME] seans içi fiyat güncellemesi - {tarih}"

# watchlist güncellemesi:
git commit -m "[WATCHLIST] swing tarama güncellendi - {yeni aday varsa belirt}"
```

---

# AŞAMA 5 — KULLANICIYA ÖZET

## rapor formatı (chat'te göster, dosya oluşturmaya gerek yok)

```markdown
## 🔔 seans içi güncelleme — {tarih} {saat} TR

### piyasa durumu
SPY: $XXX (±%X) | QQQ: $XXX (±%X) | VIX: XX
risk ortamı: RISK-ON/OFF | sabahtan değişim: [aynı/değişti → neden]

güçlü sektörler (RS): ...
zayıf sektörler (RS): ...

### acil aksiyonlar (varsa)
🔴 SATIŞ: SEMBOL — neden (stop tetiklendi / tez bozuldu)
💰 KAR AL: SEMBOL — neden (hedefe ulaştı)

### portföy özeti
| portföy | değer | günlük % | durum |
|---------|-------|----------|-------|
| dengeli | $XXX | ±%X | ✅/⚠️/🔴 |
| agresif | $XXX | ±%X | ... |
| temettü | $XXX | ±%X | ... |
| rotasyon | $XXX | ±%X | ... |
| **toplam** | **$XXX** | **±%X** | |

dikkat gerektiren pozisyonlar:
- SEMBOL: neden (RSI/SMA/stop yakın/aşırı alım)

### swing durumu
| ID | sembol | k/z% | stop mesafe | durum |
|----|--------|------|------------|-------|
| ... | ... | ... | ... | ... |

aksiyonlar:
- [yapılan trade'ler]
- [trailing stop güncellemeleri]
- [watchlist değişiklikleri]

### fırsatlar
📌 swing adayı: SEMBOL — neden, giriş seviyesi, R:R
📌 portföy adayı: SEMBOL — hangi portföye, neden

### sonraki kontrol
- saat XX:XX'de kontrol edilecek: [neden — earnings AMC, makro veri, vb.]
- kapanış güncellemesi: [JSON fiyat güncelleme planı]
```

---

# KARAR AĞACI — HIZLI REFERANS

```
SEANS AÇILDI
│
├─ ACİL KONTROL (ilk 5 dk)
│  ├─ stop-loss tetiklenen var mı? → SAT
│  ├─ gap-down > %5 olan var mı? → değerlendir
│  └─ sabah BMO earnings sonuçları → etki analizi
│
├─ PİYASA DURUMU (ilk 15 dk)
│  ├─ SPY/QQQ yönü → risk ortamı belirle
│  ├─ sektör RS → güçlü/zayıf sektörler
│  └─ VIX yönü → volatilite beklentisi
│
├─ PORTFÖY TARAMA (30 dk)
│  ├─ her pozisyon: fiyat, RSI, SMA kontrol
│  ├─ uyarı tetikleyicileri kontrol
│  └─ sabah planındaki aksiyonları uygula
│
├─ SWING TARAMA (30 dk)
│  ├─ stop/hedef/trailing güncelle
│  ├─ watchlist fiyat kontrol
│  ├─ yeni aday tarama (güçlü sektörlerden)
│  └─ boş slot varsa → en iyi adayı değerlendir
│
├─ FIRSATLAR (15 dk)
│  ├─ güçlü RS sektörlerinden aday
│  ├─ earnings beat momentum
│  ├─ dip alım fırsatları (RSI < 30 + kaliteli hisse)
│  └─ portföy dengeleme ihtiyacı
│
└─ GÜNCELLEME + COMMIT
   ├─ trade varsa → JSON güncelle + commit
   ├─ watchlist güncelle + commit
   └─ fiyat güncelleme + commit
```

---

# ÖNEMLİ KURALLAR

## kullanıcı onayı gerektiren kararlar
- yeni pozisyon açma (portföy veya swing)
- mevcut pozisyonu kapatma (stop-loss hariç — o otomatik)
- portföy rebalance
- büyük strateji değişikliği

## otomatik yapılabilecek işlemler (onay gerekmez)
- fiyat güncellemesi (tüm JSON'lar)
- trailing stop yukarı güncelleme
- watchlist fiyat güncellemesi
- tutulan_gun artırma
- ağırlık yüzdesi yeniden hesaplama

## yapma!
- stop-loss'u aşağı çekme (ASLA)
- duygusal karar (panik satış, FOMO alış)
- sabah planında olmayan büyük pozisyon açma (önce analiz)
- aynı sektörde 3'ten fazla swing pozisyonu
- portföy ruhuyla uyuşmayan hisse ekleme (temettü portföyüne growth stock gibi)
- nakit oranını %5 altına düşürme (acil fırsat hariç)

---

> son güncelleme: 24 şubat 2026 | finzora ai
