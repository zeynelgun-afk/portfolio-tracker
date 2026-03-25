# PİYASA İSTİHBARAT VE TAHMİN SİSTEMİ

> **versiyon**: 1.0 | **tarih**: 25 mart 2026
> **amaç**: haberleri okuyarak, trendleri izleyerek geleceği tahmin etmek ve portföyleri ÖNCEDEN pozisyonlamak
> **felsefe**: reaktif değil proaktif. fiyat değişince tepki vermek değil, haberi okuyunca geleceği tahmin edip pozisyon almak.

---

## 1. SİSTEMİN MANTIĞI

```
DÜNYADA NE OLUYOR?           →  BUNUN ETKİSİ NE?           →  NE YAPMALIYIM?
(haber/veri/trend toplama)       (analiz/tahmin/senaryo)         (portföy aksiyonu)

örnek akış:
  "NVIDIA $1T Blackwell siparişi"
    → veri merkezi yapımı patlayacak
      → trafo talebi artacak (POWL, ETN)
      → soğutma talebi artacak (VRT, TT)
      → bakır talebi artacak (FCX)
      → enerji talebi artacak (COP, XOM)
    → bu katmanlara ŞİMDİ gir, haber fiyatlanmadan önce

  "İran Hürmüz Boğazı'nı tehdit etti"
    → petrol fiyatları yükselecek
      → E&P şirketleri kârlı (COP, XOM)
      → savunma harcamaları artacak (LMT, RTX)
      → taşımacılık maliyetleri yükselecek (havayolu/lojistik zararlı)
    → enerji/savunma ağırlığını artır, tüketim döngüsellerini azalt

  "Fed faiz indirimi olasılığı %70'e çıktı"
    → büyüme hisseleri güçlenecek
      → tech/AI rallisi gelecek
      → REIT'ler toparlanacak (DLR, EQIX)
      → bankalar marj baskısı (dikkatli)
    → büyüme ağırlığını artır, defansif azalt
```

---

## 2. HABER/VERİ TOPLAMA KATMANLARI

### 2a. makro ekonomi (haftalık/aylık etki)

| veri | sıklık | izleme yöntemi | etki |
|------|--------|----------------|------|
| FOMC faiz kararı | 6 hafta | kalshi + fed watch | tüm portföyler |
| CPI (enflasyon) | aylık | web arama + economic calendar | faiz beklentisi → sektör rotasyonu |
| NFP (istihdam) | aylık | web arama | piyasa yönü, resesyon riski |
| GDP | çeyreklik | web arama | büyüme/daralma sinyali |
| PMI (imalat/hizmet) | aylık | web arama | sektörel güç/zayıflık |
| treasury yield eğrisi | günlük | FMP treasury-rates | resesyon sinyali (tersine dönme) |
| VIX | günlük | FMP quote | risk ortamı, pozisyon boyutu |

**nasıl kullanılır**: her sabah raporunda makro takvimi kontrol et. kritik veri öncesi (1-2 gün):
- olası senaryoları yaz (pozitif/negatif/nötr)
- her senaryoda portföy etkisini belirle
- gerekirse hedge pozisyonu al veya nakit artır
- veri sonrası: senaryoyu gerçekleşmeyle karşılaştır, pozisyon ayarla

### 2b. jeopolitik gelişmeler (günlük/anlık etki)

| olay tipi | izleme | etkilenen sektörler |
|-----------|--------|---------------------|
| savaş/çatışma eskalasyonu | web arama + polymarket | savunma ↑, enerji ↑, tüketim ↓ |
| barış/ateşkes haberleri | web arama + polymarket | savunma ↓, enerji ↓, tüketim ↑ |
| ticaret savaşı/tarife | web arama + kalshi | etkilenen sektör ↓, yerel üretim ↑ |
| seçim/politika değişikliği | polymarket + kalshi | sektör bazlı (regülasyon riski) |
| doğal afet/pandemi | web arama | sigorta ↓, inşaat ↑ (sonra) |
| yaptırımlar | web arama | hedef ülke/sektör ↓, alternatifler ↑ |

**nasıl kullanılır**: seans öncesi ve seans içinde web aramasıyla güncel gelişmeleri tara. prediction markets (kalshi/polymarket) olasılık değişimlerini izle. >%10 olasılık değişimi = aksiyon sinyali.

### 2c. AI / teknoloji harcama trendleri (haftalık etki)

| sinyal | kaynak | etki |
|--------|--------|------|
| hyperscaler capex artışı (MSFT, GOOG, META, AMZN) | earnings calls, haber | tüm AI tedarik zinciri ↑ |
| yeni GPU/chip duyurusu | NVIDIA GTC, AMD events | ekipman + malzeme ↑ |
| veri merkezi inşaat haberleri | haber, gayrimenkul raporları | güç + soğutma + REIT ↑ |
| AI regülasyon haberleri | haber, politika | risk/fırsat analizi |
| chip export kısıtlamaları | haber, politika | ABD ekipman ↑, Çin alternatifleri |
| enerji darboğazı haberleri | haber, utilities raporları | güç altyapısı ↑ |

**nasıl kullanılır**: her sabah "AI data center" + "chip manufacturing" + "hyperscaler capex" araması yap. yeni bir kontrat/duyuru/darboğaz haberi varsa → hangi tedarik zinciri katmanı etkileniyor → o katmanı tara.

### 2d. sektörel earnings döngüsü (çeyreklik etki)

| dönem | odak sektör | neden |
|-------|-------------|-------|
| ocak-şubat | mega tech (AAPL, MSFT, GOOG, META) | Q4 earnings, yeni yıl capex planları |
| nisan-mayıs | endüstriyel + enerji | Q1 earnings, ilkbahar talep sinyalleri |
| temmuz-ağustos | yarı iletken (NVDA, AMD, MRVL) | Q2 earnings, AI demand update |
| ekim-kasım | tüketim + perakende | Q3 + tatil sezonu yönlendirme |

**nasıl kullanılır**: earnings sezonunda ilgili sektör hisselerini ÖNCEDEN pozisyonla. güçlü earnings beklenen şirketin tedarik zincirinde ol (örn: NVIDIA iyi raporlarsa → AMAT, ASML, ENTG da yükselir).

---

## 3. ANALİZ VE TAHMİN KATMANI

### 3a. neden-sonuç zinciri (her haber için)

her önemli haber veya gelişme için 3 adımlı düşün:

```
1. BİRİNCİ DERECE ETKİ (direkt):
   "NVIDIA rekor sipariş aldı" → NVIDIA hissesi yükselir

2. İKİNCİ DERECE ETKİ (tedarik zinciri):
   → NVIDIA daha fazla chip üretecek
   → TSMC'ye daha fazla sipariş verecek
   → ASML'den daha fazla EUV makinesi alınacak
   → ENTG'den daha fazla kimyasal kullanılacak
   → POWL'dan daha fazla trafo lazım olacak

3. ÜÇÜNCÜ DERECE ETKİ (yan etkiler):
   → veri merkezleri daha fazla elektrik tüketecek (COP, enerji)
   → daha fazla soğutma lazım (VRT, TT)
   → daha fazla bakır lazım (FCX)
   → daha fazla arazi/bina lazım (DLR, EQIX)
```

**kural**: birinci derece zaten fiyatlanmış olabilir. ikinci ve üçüncü derece etkilerde alfa var. oraya git.

### 3b. senaryo planlama (kritik olaylar için)

büyük olaylar öncesi (FOMC, earnings, jeopolitik) 3 senaryo yaz:

```
OLAY: [ne bekleniyor]

SENARYO A — POZİTİF (%XX olasılık):
  piyasa tepkisi: [ne olur]
  portföy etkisi: [hangi pozisyonlar etkilenir]
  aksiyon: [ne yapılır]

SENARYO B — NEGATİF (%XX olasılık):
  piyasa tepkisi: [ne olur]
  portföy etkisi: [hangi pozisyonlar etkilenir]
  aksiyon: [ne yapılır]

SENARYO C — SÜRPRİZ (%XX olasılık):
  piyasa tepkisi: [ne olur]
  portföy etkisi: [hangi pozisyonlar etkilenir]
  aksiyon: [ne yapılır]

EN ÇOK BEKLENTİ: [senaryo X]
PORTFÖY ÖNCEDEN POZİSYONLAMA: [ne yapılmalı]
```

### 3c. trend skorlama (haftalık güncelleme)

her aktif tema için güç skoru tut (1-10):

```
AI ALTYAPI HARCAMASI:     [8/10] — hyperscaler capex rekor, NVIDIA sipariş $1T
ENERJİ GÜVENLİĞİ:        [7/10] — iran savaşı devam, hürmüz riski
SAVUNMA HARCAMASI:        [7/10] — NATO bütçe artışı, drone/lazer
FAİZ İNDİRİMİ BEKLENTİSİ: [5/10] — fed temkinli, enflasyon yapışkan
RESESYON RİSKİ:           [3/10] — istihdam güçlü, PMI karışık
```

skor >7 olan temalara portföy ağırlığı artır. skor <4 olan temalardan ağırlık azalt.

---

## 4. AKSİYON KATMANI — PORTFÖY YÖNETİMİ

### 4a. mod geçişi

piyasa ortamına göre portföy modu değişir:

| mod | tetikleyici | portföy davranışı |
|-----|------------|-------------------|
| AGRESİF | VIX <20, trend yukarı, güçlü earnings | tam pozisyonlar, yeni girişler, trend takip |
| NORMAL | VIX 20-25, karışık sinyaller | yarım-tam pozisyonlar, seçici girişler |
| DİKKATLİ | VIX 25-30, makro belirsizlik | yarım pozisyonlar, nakit artır, stop sıkılaştır |
| DEFANSİF | VIX >30, resesyon riski, kriz | min pozisyon, max nakit, sadece hedge pozisyon |

### 4b. sektör rotasyonu

makro döngüye göre ağırlık kayması:

```
ERKEN TOPARLANMA (faiz indirim başlangıcı):
  ağırlık artır: tech, tüketim döngüsel, küçük şirket
  ağırlık azalt: savunmacı, utilities, altın

GEÇ DÖNGÜ (enflasyon yapışkan, faiz yüksek):
  ağırlık artır: enerji, emtia, savunmacı
  ağırlık azalt: büyüme, spekülasyon

RESESYON RİSKİ (yield eğrisi ters, PMI düşük):
  ağırlık artır: utilities, sağlık, temettü, altın
  ağırlık azalt: döngüsel, endüstriyel, tech
```

### 4c. pozisyon yönetimi sinyalleri

| sinyal | kaynak | aksiyon |
|--------|--------|---------|
| tema gücü arttı (skor +2) | haftalık değerlendirme | o temadaki mevcut pozisyonları yarımdan tama çıkar |
| tema gücü düştü (skor -2) | haftalık değerlendirme | o temadaki pozisyonları daralt, stop sıkılaştır |
| yeni mega trend tespit | haber/earnings analizi | yeni katman keşfet, aday araştır, giriş yap |
| earnings beat + guidance ↑ | earnings takvimi | tedarik zincirinde pozisyon al (2. derece etki) |
| earnings miss + guidance ↓ | earnings takvimi | tedarik zincirinde risk değerlendir |
| prediction market >%10 kayma | kalshi/polymarket | senaryo güncelle, portföy ayarla |

---

## 5. GÜNLÜK UYGULAMA

### sabah raporu eklemeleri

```
BÖLÜM 0: PIYASA İSTİHBARATI (yeni bölüm)

  aktif temalar ve güç skoru:
  - AI altyapı harcaması: [X/10] — [değişim nedeni]
  - enerji güvenliği: [X/10] — [değişim nedeni]
  - savunma: [X/10] — [değişim nedeni]

  dünden bu yana önemli haber/gelişme:
  1. [haber] → 1. derece etki → 2. derece etki → portföy aksiyonu
  2. [haber] → ...

  bu haftanın kritik olayları:
  - [olay] → senaryo A/B/C → önceden pozisyonlama

  tedarik zinciri katman durumu:
  - ekipman: [güçlü/zayıf/nötr] — [neden]
  - kimya: [güçlü/zayıf/nötr] — [neden]
  - güç: [güçlü/zayıf/nötr] — [neden]
  - optik: [güçlü/zayıf/nötr] — [neden]
```

### seans içi ekleme

```
her 2 saatte hızlı web taraması:
  - "stock market breaking news"
  - "AI chip semiconductor news today"
  - "energy oil gas news today"
  - prediction markets güncellemesi

yeni gelişme varsa:
  1. neden-sonuç zinciri yaz (1./2./3. derece)
  2. portföy etkisini değerlendir
  3. gerekirse aksiyon al (satış, alış, stop ayarla)
```

### haftalık ekleme (pazar raporu)

```
tema skorlarını güncelle
sektör rotasyonu değerlendirmesi
gelecek haftanın kritik olayları ve senaryolar
portföy mod değerlendirmesi (agresif/normal/dikkatli/defansif)
```

---

## 6. CLAUDE'UN SORUMLULUKLARI

claude sadece fiyat takip eden bir araç değil. claude:

1. **haberleri OKUR ve YORUMLAR** — her sabah ve seans içinde dünyada neler olduğunu araştırır
2. **geleceği TAHMİN EDER** — haberin 2. ve 3. derece etkilerini düşünür
3. **ÖNCEDEN POZİSYONLANIR** — tahmine göre portföyü ayarlar, fiyat hareketini beklemez
4. **SENARYO PLANLAR** — kritik olaylar öncesi senaryolar yazar, her senaryoda aksiyonu belirler
5. **TREND TARAR** — hangi sektör/tema güçleniyor, hangi katman fırsatlı, nereye para akıyor
6. **PROAKTİF KARAR VERİR** — zeynel'in söylemesini beklemez. düşünür, araştırır, karar verir, uygular

---

*finzora ai | piyasa istihbarat sistemi v1.0 | 25 mart 2026*
