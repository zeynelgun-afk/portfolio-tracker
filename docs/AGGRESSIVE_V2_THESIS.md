# agresif portfoy v2 — AI deger zinciri tezi

> versiyon: 2.2 | tarih: 12 nisan 2026
> sermaye: ~$358K (Nisan 2026 güncel)
> baslangic sermayesi: $400,000
> v1 kaybi: -$42,177 (-%10.54)
> durum: AKTİF — nakit pozisyon AÇILMALIDIR
>
> ⚠️ HİSSE LİSTESİ BU DOSYADA BULUNMAZ.
> Claude her seansta FMP company-screener ile o anki koşullara uyan hisseleri
> kendisi bulur. Screener kriterleri: docs/DYNAMIC_SCREENER_CRITERIA.md

---

## v1'den cikarilan dersler

v1 portfoyu (17 subat - 30 mart 2026) sadece AI tedarik zincirinin sol tarafina (donanim, ekipman, altyapi) yogunlasmisti. bu katman capex donguselligi nedeniyle risk-off ortaminda ilk satilan segment oldu.

**v1 hatalari:**
- tek katman riski: 6/6 pozisyon donanim+altyapi katmaninda
- korelasyon hatasi: ayni seansta ayni segmentte coklu pozisyon acma
- dongusal risk: capex harcamasi yavaslarsa tum pozisyonlar ayni yonde hareket eder
- insider kontrol eksikligi

**v1 dogru yapilan:**
- stop disiplini calisti (2xATR trailing)
- zarar buyumeden kesildi
- nakit koruma onceligi dogru zamanda uygulandi

---

## AI deger zinciri mimarisi (6 katman)

```
katman 1    katman 2    katman 3      katman 4   katman 5     katman 6
temel       donanim     altyapi       veri       temel        uygulamalar
girdiler    (cipler)    (veri mrk.)              modeller     ve hizmetler
$50B        $90B        $400B         $90B       $300B        $1.5T
```

### katman 1: temel girdiler — enerji, hammadde

AI veri merkezleri devasa enerji tuketiyor. bu katman altyapinin fiziksel temelini olusturur.

**FMP screener kriterleri:**
```python
{
    "sector": "Energy,Basic Materials",
    "marketCapMoreThan": 5_000_000_000,
    "volumeMoreThan": 500_000,
    "limit": 20
}
# ek filtre: "data center", "nuclear", "copper", "rare earth" temaları
# FMP profile -> description içinde AI/enerji bağlantısı ara
```

risk profili: orta. enerji fiyatlarina bagli ama uzun vadeli sozlesmeler istikrar saglar.

---

### katman 2: donanim / cipler — hesaplama gucu

AI'nin beyni. GPU, ASIC, HBM, ileri paketleme.

**FMP screener kriterleri:**
```python
{
    "sector": "Technology",
    "industry": "Semiconductors,Semiconductor Equipment & Materials",
    "marketCapMoreThan": 10_000_000_000,
    "betaMoreThan": 1.0,
    "volumeMoreThan": 1_000_000,
    "limit": 20
}
# teknik filtre: RSI 45-70, SMA50 üstü, 1M momentum > %0
```

risk profili: yuksek. capex dongusune bagli.
v2 kurali: max 2 pozisyon bu katmandan, toplam agirlik <%30.

---

### katman 3a: ekipman ve uretim

**FMP screener kriterleri:**
```python
{
    "sector": "Technology",
    "industry": "Semiconductor Equipment & Materials",
    "marketCapMoreThan": 5_000_000_000,
    "volumeMoreThan": 500_000,
    "limit": 15
}
```

### katman 3b: guc ve sogutma

**FMP screener kriterleri:**
```python
{
    "sector": "Industrials",
    "industry": "Electrical Equipment & Parts,Building Products & Equipment",
    "marketCapMoreThan": 3_000_000_000,
    "volumeMoreThan": 500_000,
    "limit": 15
}
# ek filtre: "data center", "cooling", "power management" temalı
```

### katman 3c: optik ve ag

**FMP screener kriterleri:**
```python
{
    "sector": "Technology",
    "industry": "Communication Equipment,Electronic Components",
    "marketCapMoreThan": 2_000_000_000,
    "volumeMoreThan": 500_000,
    "limit": 15
}
# ek filtre: "optical", "fiber", "transceiver" temalı
```

### katman 3d: veri merkezi REIT

**FMP screener kriterleri:**
```python
{
    "sector": "Real Estate",
    "industry": "REIT - Specialty",
    "marketCapMoreThan": 10_000_000_000,
    "dividendMoreThan": 1.0,
    "limit": 10
}
# ek filtre: "data center" içeren şirketler
```

risk profili: orta-yuksek.
v2 kurali: max 2 pozisyon (3a/3b/3c/3d karisik), toplam agirlik <%25.

---

### katman 4: veri — AI'nin yakiti

model egitimi ve cikarsama icin veri toplama, isleme, depolama.

**FMP screener kriterleri:**
```python
{
    "sector": "Technology",
    "industry": "Software - Application,Software - Infrastructure",
    "marketCapMoreThan": 5_000_000_000,
    "betaMoreThan": 0.9,
    "volumeMoreThan": 1_000_000,
    "limit": 20
}
# ek filtre: "data platform", "analytics", "database", "observability" temalı
```

risk profili: orta. yazilim segmenti, faiz hassasiyeti var.
v2 kurali: max 1-2 pozisyon, toplam agirlik <%20.

---

### katman 5: temel modeller — AI'nin zekasi

buyuk dil modelleri, cikarsama, bulut AI hizmetleri.

**FMP screener kriterleri:**
```python
{
    "sector": "Technology,Communication Services",
    "marketCapMoreThan": 200_000_000_000,   # mega-cap zorunlu
    "betaMoreThan": 0.8,
    "volumeMoreThan": 5_000_000,
    "limit": 10
}
# ek filtre: "artificial intelligence", "cloud", "AI" temalı
# + FMP key-metrics-ttm: FCF yield > %2, ROIC > %15
```

risk profili: dusuk-orta. mega-cap kalesi, nakit akisi guclu.
v2 kurali: max 2 pozisyon, toplam agirlik <%30. bu katman portfoyun cekirdegi.

---

### katman 6: uygulamalar ve hizmetler — deger yakalama

AI'yi is sureclerine gomup gelir ureten katman. EN BUYUK PASTA.

**FMP screener kriterleri:**
```python
{
    "sector": "Technology,Communication Services,Healthcare",
    "marketCapMoreThan": 10_000_000_000,
    "betaMoreThan": 1.0,
    "volumeMoreThan": 1_000_000,
    "limit": 25
}
# ek filtre: "automation", "AI", "SaaS", "platform" temalı
# + revenue growth > %15 (FMP income-statement-growth ile kontrol)
```

risk profili: orta. buyume hisseleri, faiz hassasiyeti var.
v2 kurali: max 2-3 pozisyon, toplam agirlik <%30.

---

## v2 portfoy kurallari

### ⚠️ NAKİT HEDEF KURALI — AGRESİF PORTFÖY İÇİN ZORUNLU

bu portföy AGRESIF büyüme portföyüdür. nakit tutmak bu portföyün göreviyle çelişir.

| durum | hedef nakit | eylem |
|-------|-------------|-------|
| 0-2 açık pozisyon | max %20 (≈$80K) | ACELE GİRİŞ — fırsat ara, bu an en yüksek öncelik |
| 3-4 açık pozisyon | max %30 (≈$120K) | aktif giriş — varlık ara |
| 5-6 açık pozisyon | max %40 (≈$160K) | normal, yeni fırsat beklentisi |
| 6 pozisyon (dolu) | kalan nakit OK | tam dolu, yönet |

**KURAL: her seansta açık pozisyon sayısı <4 ise, nakit çalıştırma birinci önceliktir. "bekleyeyim" kararı verilemez.**

### pozisyon limitleri

| kural | deger |
|-------|-------|
| max pozisyon | 6 |
| min katman cesitliligi | 3 farkli katman |
| max tek katman agirligi | %30 |
| max tek pozisyon agirligi | %20 |
| stop | 2xATR(14) trailing |
| giris kosulu | ichimoku 4/4 VEYA kumo kirilimi + hacim teyidi VEYA RSI <40 oversold bounce |
| VIX >28 | yarim pozisyon (K-13) |
| VIX >35 | yeni giris yok |

---

## piyasa rejimi → giriş taktikleri

**temel ilke: agresif portföy her piyasa rejiminde çalışır. cevap her zaman "hangi hisseyi alırım"dır. screener kriterleri DYNAMIC_SCREENER_CRITERIA.md'den al.**

| piyasa rejimi | öncelikli screener | VIX referansı |
|---------------|-------------------|---------------|
| TREND_BULL | Katman 5-6 screener | <22 |
| VOLATILE_BULL | Katman 5 + kriz faydalananları screener | 22-28 |
| KRİZ_RALLİ | DYNAMIC_SCREENER_CRITERIA.md kriz screener'ı | 22-28 |
| KRİZ aktif | DYNAMIC_SCREENER_CRITERIA.md kriz screener'ı, yarım poz | 28-35 |
| BEAR | Defansif büyüme + kriz faydalananları screener | 22-30 |

**"koşullar yok" kararı sadece VIX>35 veya K-02 aktifken verilebilir.**

---

## giriş tetikleyicileri

### giriş koşulları (hepsi birden şart DEĞİL — herhangi 2'si yeterli):

1. VIX < 28
2. NASDAQ 20 günlük SMA üzerinde veya yakınında
3. hedef isim ichimoku 4/4 sinyali
4. hedef isim RSI 40-60 momentum sinyali
5. pozitif sektör rotasyonu var

### nakit çalıştırma kuralı:

$358K'nın %70'i (≈$250K) en geç 30 işlem günü içinde pozisyonlara taşınmalıdır.
son tarih: 23 Mayıs 2026.
her seans en az 1 giriş ARAŞTIRMASI zorunludur.

---

## risk yonetimi

- insider trading kontrolu: CEO/CFO büyük satış + K-15b skoru kötüyse manuel değerlendirme
- korelasyon kontrolu: ayni seansta ayni katmandan 2+ pozisyon acma
- senaryo planlamasi: fed/kazanc sezonu oncesi A/B/C senaryolari hazirla
- kismi kar alma: K-11 (RSI 70+ ve %15+ kar) tetiklenince kademe

---

## v1 vs v2

| ozellik | v1 | v2 |
|---------|----|-----|
| katman dagılimi | tek katman | 3+ katman zorunlu |
| hisse seçimi | sabit liste | dinamik screener (DYNAMIC_SCREENER_CRITERIA.md) |
| mega-cap orani | %0 | %30-50 (cekirdek) |
| kriz ortamı | bekle | kriz screener'ı uygula |
| capex dongusune bagimlilik | %100 | <%30 |

---

*finzora ai | 12 nisan 2026 | agresif portfoy v2.2 tez belgesi*
