# agresif portfoy v2 — AI deger zinciri tezi

> versiyon: 2.1 | tarih: 12 nisan 2026
> sermaye: ~$358K (Nisan 2026 güncel)
> baslangic sermayesi: $400,000
> v1 kaybi: -$42,177 (-%10.54)
> durum: AKTİF — piyasa normale dönüyor, nakit pozisyon AÇILMALIDIR

---

## v1'den cikarilan dersler

v1 portfoyu (17 subat - 30 mart 2026) sadece AI tedarik zincirinin sol tarafina (donanim, ekipman, altyapi) yogunlasmisti. bu katman capex donguselligi nedeniyle risk-off ortaminda ilk satilan segment oldu.

**v1 hatalari:**
- tek katman riski: 6/6 pozisyon donanim+altyapi katmaninda (MRVL, COHR, CAMT, POWL, VRT, PLTR)
- korelasyon hatasi: ayni seansta ayni segmentte coklu pozisyon acma
- dongusal risk: capex harcamasi yavaslarsa tum pozisyonlar ayni yonde hareket eder
- insider kontrol eksikligi: POWL $25M insider satisi kacti

**v1 dogru yapilan:**
- stop disiplini calisti (2xATR trailing)
- zarar buyumeden kesildi
- nakit koruma onceligi dogru zamanda uygulandi

---

## AI deger zinciri mimarisi (6 katman)

kaynak: Kaya Finance yapay zeka ekosistem mimarisi

```
katman 1    katman 2    katman 3      katman 4   katman 5     katman 6
temel       donanim     altyapi       veri       temel        uygulamalar
girdiler    (cipler)    (veri mrk.)              modeller     ve hizmetler
$50B        $90B        $400B         $90B       $300B        $1.5T
```

### katman 1: temel girdiler ($50B) — enerji, arazi, hammadde

AI veri merkezleri devasa enerji tuketiyor. bu katman altyapinin fiziksel temelini olusturur.

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| COP | ConocoPhillips | enerji (E&P) | veri merkezi enerji talebi, petrol + dogalgaz |
| CEG | Constellation Energy | nukleer enerji | veri merkezi icin uzun vadeli nukleer PPA'lar |
| VST | Vistra Energy | nukleer + dogalgaz | Microsoft nukleer anlasma, baz yuk saglar |
| NRG | NRG Energy | baz yuk enerji | veri merkezi enerji tedarik sozlesmeleri |
| MP | MP Materials | nadir toprak | AI cip uretimi icin kritik malzeme |
| FCX | Freeport-McMoRan | bakir | elektrik altyapisi, veri merkezi kablolama |

risk profili: orta. enerji fiyatlarina bagli ama uzun vadeli sozlesmeler istikrar saglar.

### katman 2: donanim / cipler ($90B) — hesaplama gucu

AI'nin beyni. GPU, ASIC, HBM, ileri paketleme.

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| NVDA | NVIDIA | GPU / AI hizlandirici | pazar lideri, veri merkezi gelirinin %80+ |
| AMD | AMD | GPU + CPU | MI300X ile NVDA'ya alternatif, MI400 beklentisi |
| AVGO | Broadcom | custom ASIC + ag | Google TPU, Meta MTIA tasarimi + VMware |
| ARM | ARM Holdings | cip mimarisi lisansi | tum AI ciplerinin altindaki mimari |
| MRVL | Marvell | custom ASIC + optik | Amazon Trainium, Microsoft Maia tasarimi |
| ALAB | Astera Labs | baglanti cipleri | GPU kume arabaglanti, PCIe/CXL |

risk profili: yuksek. capex dongusune bagli, v1'de en cok zarar veren katman.
v2 kurali: max 2 pozisyon bu katmandan, toplam agirlik <%30.

### katman 3: altyapi / veri merkezleri ($400B) — fiziksel omurga

ciplerin calistigi bina, sogutma, guc, ag altyapisi.

**3a. ekipman ve uretim**

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| ASML | ASML | EUV litografi | cip uretiminin darboazi, tekel |
| AMAT | Applied Materials | yarileetken ekipman | CVD, etch, metroloji |
| LRCX | Lam Research | etch + depolama | NAND/HBM uretimi icin kritik |
| KLAC | KLA Corp | proses kontrol | verim optimizasyonu, kalite |

**3b. guc ve sogutma**

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| ETN | Eaton | guc yonetimi | veri merkezi guc dagilimi |
| PWR | Quanta Services | elektrik altyapi | veri merkezi baglanti + grid |
| VRT | Vertiv | sogutma + UPS | sivi sogutma trendi, veri merkezi termal |
| TT | Trane Tech | HVAC + sogutma | veri merkezi iklimlendirme |

**3c. optik ve ag**

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| COHR | Coherent | optik transceiver | 800G/1.6T gecis, GPU arabaglanti |
| LITE | Lumentum | lazer + optik | fiber optik + 3D algilama |
| GLW | Corning | fiber optik kablo | veri merkezi ag altyapisi |

**3d. veri merkezi REIT**

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| DLR | Digital Realty | veri merkezi | kapasite genislemesi, kira artisi |
| EQIX | Equinix | veri merkezi | premium baglanti, hibrit bulut |

risk profili: orta-yuksek. capex dongusune bagli ama daha genis musteriye yayilmis.
v2 kurali: max 2 pozisyon (ekipman/guc/optik/REIT karisik), toplam agirlik <%25.

### katman 4: veri ($90B) — AI'nin yakiti

model egitimi ve cikarsama icin veri toplama, isleme, depolama.

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| SNOW | Snowflake | veri platformu | bulut veri ambari, AI/ML entegrasyonu |
| MDB | MongoDB | NoSQL veritabani | yapilandirilmamis veri, AI uygulama katmani |
| DDOG | Datadog | gozlemlenebilirlik | AI altyapi izleme, log analizi |
| PLTR | Palantir | veri analitiği | devlet + kurumsal AI veri platformu |

risk profili: orta. yazilim segmenti, faiz hassasiyeti var ama recurring gelir modeli.
v2 kurali: max 1-2 pozisyon, toplam agirlik <%20.

### katman 5: temel modeller ($300B) — AI'nin zekasi

buyuk dil modelleri, cikarsama, bulut AI hizmetleri.

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| MSFT | Microsoft | OpenAI ortakligi + Copilot | kurumsal AI dagitiminda lider |
| GOOGL | Alphabet | Gemini + bulut AI | arama AI donusumu, GCP buyumesi |
| AMZN | Amazon | Bedrock + AWS | bulut AI platformu, Anthropic yatirimi |
| META | Meta | LLaMA acik kaynak | reklam AI + acik kaynak model lideri |

risk profili: dusuk-orta. mega-cap kalesi, nakit akisi guclu, coklu gelir kaynagi.
v2 kurali: max 2 pozisyon, toplam agirlik <%30. bu katman portfoyun cekirdegi olacak.

### katman 6: uygulamalar ve hizmetler ($1.5T) — deger yakalama

AI'yi is sureclerine gomup gelir ureten katman. EN BUYUK PASTA.

| sembol | sirket | alt segment | neden |
|--------|--------|-------------|-------|
| NOW | ServiceNow | kurumsal is akisi AI | IT otomasyon + AI agent platformu |
| CRM | Salesforce | CRM + AI (Einstein) | satis/pazarlama AI otomasyonu |
| WDAY | Workday | IK + finans AI | kurumsal kaynak yonetimi AI |
| CRWD | CrowdStrike | siber guvenlik AI | AI destekli tehdit tespiti |
| UBER | Uber | ulasim + teslimat AI | otonom surusten once bile AI optimizasyon |
| HIMS | Hims & Hers | saglik AI | telesaglik + AI tani, yuksek buyume |

risk profili: orta. buyume hisseleri, faiz hassasiyeti var ama AI gelir donusumu somut.
v2 kurali: max 2-3 pozisyon, toplam agirlik <%30. uzun vadede en buyuk alfa potansiyeli.

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

### giris onceligi (piyasa normale dondugunde)

oncelik 1 (cekirdek): katman 5 (temel modeller) — 2 pozisyon
- MSFT veya GOOGL + AMZN veya META
- neden: en genis hendek, en guclu nakit akisi, AI donusumunun temelini olusturur

oncelik 2 (buyume): katman 6 (uygulamalar) — 2 pozisyon
- NOW + CRWD veya CRM
- neden: AI gelir donusumu en somut bu katmanda, $1.5T adreslenebilir pazar

oncelik 3 (dongusal/taktik): katman 2-3 (donanim/altyapi) — 1-2 pozisyon
- NVDA veya AVGO + secici ekipman/optik (COHR, ASML)
- neden: capex dongusune bagimli, sadece guclu trend ortaminda

oncelik 4 (opsiyonel): katman 1 veya 4 — enerji veya veri
- sadece ozel katalist varsa (nukleer PPA, veri platformu kazanc surprizi)

### v1 vs v2 karsilastirma

| ozellik | v1 | v2 |
|---------|----|----|
| katman dagılimi | tek katman (donanim+altyapi) | 3+ katman zorunlu |
| mega-cap orani | %0 | %30-50 (cekirdek) |
| capex dongusune bagimlilik | %100 | <%30 |
| en buyuk risk | tek sektore yogunlasma | hala buyume hissesi agirlikli |
| alfa kaynagi | tedarik darboazi | deger zinciri genisliginde alfa |

---

## giriş tetikleyicileri (NİSAN 2026 GÜNCELLEMESİ)

### giriş koşulları (hepsi birden şart DEĞİL — herhangi 2'si yeterli):

1. VIX < 28 ✅ (Nisan 2026 itibarıyla sağlanıyor)
2. NASDAQ 20 günlük SMA üzerinde veya yakınında
3. hedef isim ichimoku 4/4 sinyali
4. hedef isim RSI 40-60 arası momentum sinyali
5. pozitif sektör rotasyonu var

### aktif giriş sıralaması (piyasa açıkken bu sırayla tara):

öncelik 1 (çekirdek — en az 2 pozisyon): katman 5 temel modeller
- MSFT, GOOGL, AMZN, META

öncelik 2 (büyüme — en az 2 pozisyon): katman 6 uygulamalar
- NOW, CRWD, CRM, WDAY

öncelik 3 (taktik — 1-2 pozisyon): katman 2-3 donanım/altyapı
- NVDA, AVGO, COHR, ETN, VRT

### nakit çalıştırma kuralı:

$358K'nın %70'i (≈$250K) en geç 30 işlem günü içinde pozisyonlara taşınmalıdır.
bu süre: 12 Nisan — 23 Mayıs 2026.
her seans en az 1 giriş ARAŞTIRMASI zorunludur.
"koşullar yok" kararı sadece VIX>35 veya K-02 kriz protokolü aktifken verilebilir.

~~tetikleyici oluşana kadar $358K nakit korunur. acele yok.~~ → **BU KURAL GEÇERSİZDİR.**

---

## risk yonetimi

- insider trading kontrolu: CEO/CFO düşüş trendinde büyük satış yapıyorsa + K-15b skoru kötüyse manuel değerlendirme (K-18 kaldırıldı — 11 Nisan 2026, backtest negatif kanıt)
- korelasyon kontrolu: ayni seansta ayni katmandan 2+ pozisyon acma
- senaryo planlamasi: iran/fed/kazanc sezonu oncesi A/B/C senaryolari hazirla
- kismi kar alma: K-11 (RSI 70+ ve %20+ kar) tetiklenince %50 sat

---

*finzora ai | 31 mart 2026 | agresif portfoy v2 tez belgesi*
