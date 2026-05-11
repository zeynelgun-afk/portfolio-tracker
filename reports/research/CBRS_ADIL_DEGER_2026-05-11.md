# CBRS — Cerebras Systems Inc. Adil Değer Raporu (Pre-IPO)

| Alan | Değer |
|---|---|
| Şirket | Cerebras Systems Inc. |
| Ticker | CBRS (Nasdaq Global Select Market) |
| Sektör | Yarı İletken (Semiconductor) — AI Compute Pure-Play (Saf Oyuncu) |
| Analiz Tarihi | 11 Mayıs 2026 |
| Halka Arz (IPO) Pricing | 13 Mayıs 2026 |
| İşlem Başlangıcı | 14 Mayıs 2026 |
| IPO Talep | 20x+ oversubscribed (aşırı talep), 10 milyar dolar üzeri indication of interest |
| Son Fiyat Aralığı (10 Mayıs) | 150-160 dolar (orijinal 115-125'ten iki kez yukarı revize) |
| Önerilen Hisse Sayısı | 28 milyon Class A (+ 4,2 milyon greenshoe) |
| Üst Aralık Valuation | ~34,7 milyar dolar (potansiyel 40 milyar dolara doğru) |
| Rapor Versiyonu | v2.0 (sözleşmeler + iş bağlantıları entegre) |
| Kaynak | finzora ai |

> **NOT:** CBRS pre-IPO bir şirkettir. FMP API'de henüz veri yok. Tüm rakamlar S-1/A (4 Mayıs 2026), OpenAI Master Relationship Agreement (Ocak 2026), AWS partnership açıklaması (13 Mart 2026), IPO roadshow haberleri ve karşılaştırılabilir şirket analizinden manuel olarak hesaplanmıştır. Standart 9 Yöntem skill scripti pre-IPO için çalıştırılamaz; manuel olarak forward-zorlu metodoloji uygulandı.

---

## 1. Yönetici Özeti

Cerebras Systems Wafer Scale Engine (WSE) adı verilen wafer ölçeğinde tek parça AI işlemci üreten saf oyuncu yarı iletken şirketidir. 2016 kuruluşludur, merkezi Sunnyvale Kaliforniya. WSE-3 nesil çipi NVIDIA Blackwell B200 GPU'larına göre tek silikon kalıbında çok daha fazla compute, bellek ve bant genişliği barındırır; özellikle inference (çıkarım) decode aşamasında GPU'lara göre 10x'e kadar hızlı olduğu duyuruluyor. 2025'te 510 milyon dolar gelir kaydetti (yıllık +%76). Kâr kalitesi tartışmalı: GAAP 87,9 milyon dolar net kâr, ama bunun 363,3 milyon doları G42 ile bağlantılı forward sözleşme yükümlülüğünün kapatılmasından gelen nakit dışı (non-cash) kazanç. Operasyonel olarak şirket -145,9 milyon dolar GAAP operating loss, -75,7 milyon dolar non-GAAP net zarar verdi.

Ana büyüme tezi 24,6 milyar dolar performans yükümlülüğü (RPO, remaining performance obligations) ve son iki çeyrekte imzalanan iki kritik partnership üzerine kurulu. **Birincisi**, OpenAI ile Ocak 2026'da imzalanan Master Relationship Agreement (MRA): 750 megawatt (MW) compute kapasitesi 2028'e kadar, yılda 250 MW olarak 2026-2027-2028 boyunca devreye alınacak; sözleşme değeri 20+ milyar dolar. OpenAI buna ek olarak 2030'a kadar **1,25 gigawatt (GW) ek opsiyon** hakkı aldı (toplam 2 GW potansiyel), 1 milyar dolar tutarında 6% faizli borç verdi ve 33,4 milyon Class N (oysuz) hisse warrantı aldı (tam vesting ancak 2 GW alımında). Nisan 2026'da OpenAI 10 milyar dolar ek harcama taahhüdü ekledi. **İkincisi**, AWS ile 13 Mart 2026'da imzalanan çok yıllı sözleşme: CS-3 sistemleri AWS veri merkezlerine yerleştirilecek, "disaggregated inference" mimarisinde AWS Trainium prefill aşamasını, Cerebras CS-3 decode aşamasını çalıştıracak. Amazon Bedrock üzerinden açık kaynak LLM'ler ve Amazon Nova modelleri 2026 sonunda erişilebilir olacak.

Backlog dönüşüm takvimi (S-1 kanıtlı): 24,6 milyar doların **%15'i 2026-2027'de** (~3,7 milyar), **%43'ü 2028-2029'da** (~10,6 milyar), kalan **%42'si 2030 ve sonrası** (~10,3 milyar). Yani 2028-2029 patlamalı büyüme yılları olacak. Buna ek olarak AWS Bedrock geliri 2027'den başlayarak materyalize olmaya başlamalı.

Hisse başına ağırlıklı adil değer (GROWTH modu, forward 2026-2028 + DCF): **127 dolar**. IPO üst aralığı 160 dolar üzerinde olduğundan hisse base case'de yaklaşık **%26 pahalı** ama bull senaryosunda (185 dolar) içinde rahatlıkla erişilebilir. Yani fiyat aralığı agresif ama mantıksız değil. Asıl risk **müşteri konsantrasyonu (%86 top 2)**, **backlog dönüşüm hızı** ve **NVIDIA fiyat baskısı**.

| Senaryo | Adil Değer | IPO Üst Aralığı (160 $) Göre |
|---|---|---|
| Ayı | ~$75 | -%53 |
| Base | ~$127 | -%21 |
| Boğa | ~$185 | +%16 |
| **Beklenen Değer** | **~$123** | **-%23** |

**Confidence: ORTA.** Pre-IPO + 0 işlem geçmişi + müşteri konsantrasyonu olumsuz; OpenAI MRA + AWS partnership + detaylı backlog takvimi + bağımsız analist konsensüs olumlu. Yöntemler arası CV %32 (normal dağılım).

---

## 2. 9 Yöntem Bazlı Değerlendirme

CBRS 2025'te operasyonel zarar verdi. Net P/E, EV/EBIT, EV/EBITDA, P/FCF, ROE bazlı ve Graham Number yöntemleri **TTM bazlı KULLANILAMAZ**. Protokol gereği 4'ten fazla yöntem kullanılamadığında **Forward bazlı versiyonlar zorlanır**.

| # | Yöntem | Durum | Sonuç | Not |
|---|---|---|---|---|
| 1 | Net P/E TTM | KULLANILAMAZ | — | GAAP NI nakit dışı kazanç, normalleşmiş kâr negatif |
| 2 | Forward P/E (NTM 2026) | KULLANILAMAZ | — | 2026 net zarar bekleniyor |
| 3 | Forward P/E (2028 normalize) | KULLANILABİLİR (zorlandı) | $130 | 2028 EPS ~$1,30 varsayım (15% op margin, ~%10 net margin × 100 P/E) |
| 4 | EV/EBIT | KULLANILAMAZ | — | 2025 operating loss -$146M |
| 5 | EV/EBITDA | KULLANILAMAZ | — | Negatif EBITDA |
| 6 | EV/Revenue TTM | KULLANILABİLİR | $54 | $510M × 24x (sektör medyanı) ÷ 224M hisse |
| 7 | Forward EV/Rev (2026 ~$1,2B) | KULLANILABİLİR (zorlandı) | $79 | $1,2B × 15x ÷ 224M |
| 8 | Forward EV/Rev (2027 ~$2,7B) | KULLANILABİLİR (zorlandı) | $145 | $2,7B × 12x ÷ 224M |
| 9 | Forward EV/Rev (2028 ~$5,5B) | KULLANILABİLİR (zorlandı) | $196 | $5,5B × 8x ÷ 224M (büyüme yavaşladıkça multiple düşer) |
| 10 | P/FCF | KULLANILAMAZ | — | FCF negatif |
| 11 | ROE bazlı | KULLANILAMAZ | — | Birikmiş zarar $905M |
| 12 | Graham Number | KULLANILAMAZ | — | EPS ve BVPS anlamsız |
| 13 | DCF (10 yıl + Terminal) | KULLANILABİLİR | $108 | Backlog destekli, WACC %13, terminal büyüme %4 |
| 14 | EV/Backlog | KULLANILABİLİR (ek metrik) | $134 | $30B etkili backlog × 1,0x ÷ 224M |

### 2.1 Karşılaştırılabilir Şirket Multiple Verileri (FMP, 11 Mayıs 2026)

| Şirket | Fiyat | MCap (B$) | P/S TTM | Not |
|---|---|---|---|---|
| NVDA | $215,22 | 5.230 | 24,22x | AI lider, çeyreklik $34,2B GPU geliri |
| AMD | $455,19 | 742 | 19,82x | MI300, MI325 ramp |
| AVGO | $430,00 | 2.036 | 29,82x | Custom AI silicon, networking |
| ARM | $213,27 | 227 | 46,12x | Saf oyuncu IP, premium multiple |
| MRVL | $170,13 | 149 | 18,15x | Custom AI silicon, networking |
| **Medyan** | | | **24,22x** | |
| **Ortalama** | | | **27,63x** | |

CBRS için base multiple 24x (sektör medyanı), büyüme premium +%10, müşteri konsantrasyon iskonto -%15 net etki ~24x TTM. Ancak büyüme yavaşladıkça forward yıllar için multiple kademeli düşer: 2026 için 15x, 2027 için 12x, 2028 için 8x (büyüme oranı %50'nin altına düşer varsayımı).

### 2.2 DCF Varsayımları (Backlog Takvimi Destekli)

Backlog dönüşüm S-1 takvimine sadık kaldı, yeni iş varsayımı OpenAI 2 GW opsiyonunun %50'sinin yürürlüğe girmesi + AWS Bedrock ramp:

| Yıl | Gelir (M$) | Op Margin | Op Income (M$) | FCF (M$) |
|---|---|---|---|---|
| 2026 | 1.200 | -%3 | -36 | -50 |
| 2027 | 2.700 | %8 | 216 | 135 |
| 2028 | 5.500 | %15 | 825 | 660 |
| 2029 | 7.000 | %20 | 1.400 | 1.100 |
| 2030 | 9.500 | %23 | 2.185 | 1.700 |
| 2031 | 12.000 | %25 | 3.000 | 2.400 |
| 2032 | 14.000 | %26 | 3.640 | 2.900 |
| 2033 | 15.500 | %26 | 4.030 | 3.200 |
| 2034 | 16.500 | %25 | 4.125 | 3.400 |
| 2035 | 17.000 | %25 | 4.250 | 3.500 |
| Terminal | %4 büyüme | %25 | | |

WACC %13 (yüksek beta + IPO premium + müşteri konsantrasyon risk primi). Terminal value = $3,5B × 1,04 / (0,13 − 0,04) = $40,4B. Bu DCF 224M hisse üzerinden **hisse başına 108 dolar** verir.

**Hassasiyet analizi:**

| WACC | Terminal Büyüme | DCF / Hisse |
|---|---|---|
| %15 | %3 | $82 |
| %15 | %4 | $90 |
| %13 | %3 | $98 |
| %13 | %4 | $108 |
| %13 | %5 | $122 |
| %11 | %4 | $135 |
| %11 | %5 | $155 |

### 2.3 Backlog Dönüşüm Takvimi (S-1 Kanıtlı)

| Dönem | Tutar | % | Yıllık Ortalama |
|---|---|---|---|
| 2026-2027 (24 ay) | $3,7B | %15 | $1,85B |
| 2028-2029 (ay 25-48) | $10,6B | %43 | $5,3B |
| 2030+ (ay 49+) | $10,3B | %42 | Belirsiz |
| **Toplam** | **$24,6B** | **%100** | |

**Bu, 2028-2029'un patlamalı büyüme yılları olacağı anlamına gelir** — sadece backlog dönüşümü yıllık 5+ milyar dolara işaret ediyor, üzerine AWS Bedrock + OpenAI 2 GW opsiyonu + sovereign AI sözleşmeleri eklenirse 2028'de 6-7 milyar dolar gelir muhtemel.

---

## 3. Ağırlıklı Adil Değer Tablosu (GROWTH Modu)

CBRS hızla büyüyen, kâra geçmemiş, AI saf oyuncu olduğundan **GROWTH modu** uygulandı. Traditional yöntemler hesaba katılmadı. Ağırlık Forward + Growth yöntemlerinde toplandı.

| Yöntem | Adil Değer | Ağırlık | Katkı |
|---|---|---|---|
| EV/TTM Revenue (24x) | $54 | %5 | $2,70 |
| Forward EV/Rev 2026 (15x, $1,2B) | $79 | %15 | $11,85 |
| Forward EV/Rev 2027 (12x, $2,7B) | $145 | %20 | $29,00 |
| Forward EV/Rev 2028 (8x, $5,5B) | $196 | %15 | $29,40 |
| DCF (2 aşama, WACC %13) | $108 | %25 | $27,00 |
| EV/Backlog (1,0x × $30B etkili) | $134 | %15 | $20,10 |
| Forward P/E 2028 normalize | $130 | %5 | $6,50 |
| **Toplam** | | **%100** | **~$127** |

**Ağırlıklı Adil Değer: 127 dolar.**

Gerekçe: 2027 ve DCF en ağır iki yöntem (toplam %45) çünkü ikisi de backlog dönüşümünü doğrudan kullanır. 2028 forward EV/Rev (%15) backlog takviminin %43 dönüşüm aşamasını yakalar. 2026 forward (%15) yakın gelecek görünürlüğü için. EV/Backlog (%15) backlog değerlemesinin doğrulayıcısı. TTM (%5) sadece zemin. Forward P/E (%5) sembolik.

**CV (Coefficient of Variation): ~%32** — yöntemler normal dağılımda, makul tutarlılık. 🟡 normal.

---

## 4. Senaryo Matrisi

| Senaryo | Adil Değer | IPO Üst Aralığı (160 $) Göre | Olasılık | Gerekçe |
|---|---|---|---|---|
| Ayı | $75 | -%53 | %30 | UAE müşteri konsantrasyon krizi, CFIUS yeniden incelemesi, NVDA fiyat baskısı, brüt marj %30 altına iner, backlog dönüşümü gecikir, OpenAI ilişkisi soğur |
| Base | $127 | -%21 | %50 | Backlog S-1 takvimine sadık dönüşür, 2026 $1,2B → 2027 $2,7B → 2028 $5,5B, brüt marj %40-45'te tutar, AWS Bedrock 2026 sonunda canlı ama mega-cap değil |
| Boğa | $185 | +%16 | %20 | OpenAI 1,25 GW ek opsiyonu erken yürürlüğe girer, AWS Bedrock üretim ölçeğine geçer, brüt marj %50+, sovereign AI sözleşmeleri (Hindistan, Suudi Arabistan, AB) imzalanır, NVDA premium multiple'larını yakalar |
| **Beklenen Değer** | **$123** | **-%23** | %100 | (75 × 0,30 + 127 × 0,50 + 185 × 0,20) |

Olasılık gerekçeleri:
- **Ayı %30**: 86% müşteri konsantrasyonu + UAE jeopolitik gerçek bir tail risk (kuyruk riski); ABD merkezli gelir 2024-2025'te %34 düştü, bu trendin tersine dönmesi kanıt gerektirir.
- **Base %50**: Backlog kontratlı, OpenAI taahhütlü, AWS imzalı; en olası senaryo bu yöne işaret ediyor.
- **Boğa %20**: OpenAI 2 GW opsiyonu ve sovereign AI sözleşmeleri kanıtsız ama mümkün; AWS Bedrock üretim ölçeği ölçeklenebilir.

---

## 5. Bear Case (8 Madde, Detaylı)

### 5.1 Müşteri Konsantrasyonu (KRİTİK)
S-1'e göre 2025 gelirinin **%62'si Mohamed bin Zayed University of Artificial Intelligence (MBZUAI), %24'ü G42** kaynaklı. Top 2 müşteri = **%86 gelir**. ABD merkezli gelir 2024'te 282,7M dolardan 2025'te 187,6M dolara **%34 düştü** — büyümenin tamamı Abu Dabi tabanlı. CFIUS yeniden incelemesi, UAE-ABD diplomatik kriz veya G42-OpenAI iş birliği değişikliği geliri %60+ daraltabilir. OpenAI bağımlılığı ileride 86% konsantrasyonu sadece bir başka tek-müşteri-riski ile değiştirir.

### 5.2 Kâr Kalitesi Soru İşareti (KRİTİK)
2025 GAAP net kârı 87,9 milyon dolar görünse de **363,3 milyon dolar nakit dışı forward sözleşme yükümlülüğü kapatılma kazancından** geliyor. Bu kazancı çıkarınca GAAP operating loss -145,9 milyon dolar, non-GAAP net zarar -75,7 milyon dolar. Non-GAAP zarar 2024'teki 21,8 milyon dolardan **%247 kötüleşmiş**. Şirket büyüyor ama operasyonel olarak nakit yakıyor. Sürdürülebilir karlılık tezi için zayıf başlangıç.

### 5.3 NVIDIA Rekabet Baskısı
NVIDIA çeyreklik 34,2 milyar dolar GPU geliri kaydediyor — CBRS'in **yıllık gelirinin 67 katı çeyrekte**. CUDA ekosistemi, geliştirici tabanı, milyonlarca aktif GPU kurulu tabanı bir gecede aşılamaz. Blackwell Ultra ve Rubin nesli ile fiyat-performans hızla ilerliyor; CBRS WSE-3'ün inference avantajları 18-24 ay içinde kapanabilir. NVIDIA'nın 5,2 trilyon dolar piyasa değeri ve büyük müşterilere agresif fiyat ayrıcalığı sağlama kapasitesi var.

### 5.4 Backlog Konvertibilite Riski
24,6 milyar dolar RPO etkileyici ama dönüşüm güç altyapısına bağlı: Cerebras S-1'de **veri merkezi inşası, güç temini ve üretim kapasitesi** kısıtlarını risk faktörü olarak listeliyor. AI veri merkezleri için ABD'de gigawatt sınıfı güç bağlantısı 2026-2028'de büyük darboğaz; OpenAI bile 250 MW/yıl 2026 hedefini başaramayabilir. Backlog %15 dönüşüm hedefinin altında kalırsa 2026-2027 gelir tahminleri düşer ve forward multiple sıkışır.

### 5.5 OpenAI Borç-Müşteri Çatışması
OpenAI Cerebras'a 1 milyar dolar 6% faizli borç verdi ve 33,4 milyon hisse warrantı aldı. Bu çapraz finansal ilişki **bağımsız müşteri-tedarikçi ilişkisi olmadığını gösterir**. OpenAI baskı yapma ihtiyacı duyarsa fiyat indirimi, ödeme erteleme veya borç-hisse çevrim talebinde bulunabilir. Cerebras hisse fiyatı düşerse OpenAI warrantı içeride pahalı olur, alternatif çözüm aranır. Çapraz iliskiler **finansal mühendislik** olarak görülebilir, organic talep değil.

### 5.6 Forward Sözleşme Yükümlülüğü Geri Gelir Mi?
2025'te kapatılan 363,3M dolar forward sözleşme yükümlülüğü G42 ile bağlantılı. Eğer G42 ile yeni anlaşma yapılırsa benzer non-cash gain/loss gelecek mali tablolarda tekrar görünebilir. Bu **kazanç kalitesini sürekli sorgulanır** kılar, hisse multiple'ı bunu pahalı bulmaya devam eder.

### 5.7 Lock-up Süresi Sonrası Satış Baskısı (Kasım 2026)
IPO klasik 180 gün lockup ile çalışır. Kasım 2026'da insider, VC ve erken yatırımcı satışları gelir. Hisse o zamana kadar 200+ dolara çıkmışsa ciddi profit taking gelir, %20-30 düzeltme sıradan olur. Cerebras 2016'dan beri özel; içeride önemli birikim var.

### 5.8 IPO Hype Sonrası Çöküş (Tarihsel Örnekler)
ARM (Eylül 2023): IPO $51, 2 hafta sonra $66, 3 ay sonra $48 (-%27). SMR/Reddit (2024): IPO pop sonrası 6 ay içinde -%40-50. AI IPO'larında **2026-2027 küresel ekonomik yavaşlama** kombinasyonu fiyatı 100 doların altına çekebilir. 20x oversubscribed talep gerçek değil — short squeeze + retail FOMO da içerebilir.

---

## 6. Bull Case (8 Madde, Detaylı)

### 6.1 OpenAI 2 GW Opsiyonu Yürürlüğe Girer (KRİTİK)
Mevcut sözleşme: 750 MW = 20+ milyar dolar 2028'e kadar. Opsiyon: ek 1,25 GW = potansiyel ek 33+ milyar dolar 2030'a kadar. OpenAI Sam Altman'ın 1,4 trilyon dolar / 30 GW hedefi göz önüne alındığında 2 GW Cerebras alımı **çok mümkün**; OpenAI altyapı diversifikasyonuna ihtiyaç duyuyor (NVDA tek tedarikçi bağımlılığını azaltmak istiyor). 2 GW tamamen yürürlüğe girerse Cerebras tek bir müşteriden 50+ milyar dolar revenue elde eder.

### 6.2 AWS Bedrock Üretim Ölçeği (Mart 2026 Yeni)
13 Mart 2026 AWS partnership materyal: Trainium prefill + CS-3 decode "disaggregated inference" mimarisi GPU'ya göre **5x token kapasitesi, 10x hız**. AWS Bedrock 2026 sonunda açık kaynak LLM'ler (Llama, Mistral) ve Amazon Nova modellerini Cerebras üzerinden sunacak. Bedrock'un 1 milyon+ kurumsal kullanıcısına anında erişim, **organic müşteri diversifikasyonu**. 2027'den itibaren AWS revenue $500M-$1B/yıl katkıda bulunabilir.

### 6.3 Inference TAM Büyümesi (S-1 Verisi)
Bloomberg Intelligence: AI inference pazarı 2025'te 251 milyar dolardan 2029'da 672 milyar dolara çıkar — **%28 CAGR**. Inference **training'in 2 katı hızında** büyüyor. Cerebras "inference-first" mimari ile bu büyümenin saf oyuncusu. 672 milyar dolar pazarın %2'si bile Cerebras için 13 milyar dolar/yıl demek.

### 6.4 Disaggregated Inference Mimari Liderliği
AWS partnership'i ile birlikte Cerebras "disaggregated inference" mimarisinin lideri konumuna geçti. Bu mimari Microsoft Azure, Google Cloud ve Oracle Cloud için de cazip — hyperscaler diversifikasyonu mümkün. Bir 2027 Azure veya GCP partnership'i talep tabanını üçe katlar.

### 6.5 Sovereign AI Sözleşmeleri (Genişleme)
MBZUAI ve G42 mevcut UAE ilişkileri. Suudi Arabistan PIF (Public Investment Fund), Hindistan Hükümeti, AB AI Çağı projesi gibi devlet destekli AI compute alıcıları **çok yıllı milyar dolarlık sözleşmeler imzalama eğiliminde**. Cerebras'ın UAE'de kanıtlanmış teslimat geçmişi diğer devletler için referans noktası.

### 6.6 Brüt Marj Genişleme Potansiyeli
2025 brüt marj %39 (hardware ~%43, services/cloud daha düşük). Hyperscale ölçeğine geçtikçe TSMC ile fiyat müzakeresi, üretim verimi, R&D amortismanı **brüt marjı %50-55'e** çıkarabilir. NVIDIA brüt marj %75 — Cerebras'in oraya gitmesi gerekmiyor, %50'ye geçmesi bile DCF değerlemesini 1,5x artırır.

### 6.7 IPO Pop ve Momentum (Kısa Vadeli)
20x oversubscribed, 10 milyar dolar üzeri indication of interest, fiyat aralığı 2 kez yukarı revize → klasik **IPO day-1 pop sinyali**. ARM (+25%), SMR (+30%), ASTS gibi AI temalı IPO'lar 1. günde %30-50 pop yaptı. Day-1 fiyat 200-220 dolara çıkabilir. Bu, ilk hafta için arbitraj fırsatı (ama K-rules nedeniyle K-13 sonrası giriş yasak — aşağıda).

### 6.8 Yüksek Backlog/Revenue Çarpanı Tarihsel Olarak Karşılığını Buldu
Cerebras backlog/2025 revenue = 48x. NVIDIA 2022'de benzer bir backlog avantajına sahipti (data center backlog patladığında); 2 yıl içinde hisse 6x oldu. SNOW, DDOG ve UBER da yüksek RPO/Revenue oranlarını **2-3 yıl içinde gerçekleştirdi**. Cerebras backlog'unun %85'i yasal kontrat (RPO), tahmini bir tutar değil.

---

## 7. "Neden Yanlış Olabilirim" Notu (8 Madde)

### 7.1 Multiple Seçimi Sübjektifliği
Forward EV/Rev için 8x (2028), 12x (2027), 15x (2026) kullandım. Bu rakamlar **sektör medyanından gelir** ama Cerebras'in unique pozisyonu, UAE iskontosu, OpenAI premium'u bu rakamları ±%30 oynatabilir. NVIDIA premium-luxury multiple'lara (35-40x forward) çıktığında Cerebras "next NVIDIA" anlatısına kapılırsa multiple inflasyonu base case adil değeri 160-180 dolara çıkarabilir.

### 7.2 Analist Coverage Yokluğu
Pre-IPO. Resmi analyst price target yok, sadece roadshow indications + bağımsız investment memo'lar. Konsensüs 2026 $1,1B - 2027 $2,3B tahminleri **bağımsız analist konsensüsünden değil**, IPO underwriters (Morgan Stanley, Citi, Barclays, UBS) eğitilmiş rakamlardan geliyor. Underwriter rakamları **alıcıyı kandırmak için optimist eğilimli olabilir**.

### 7.3 Capex / FCF Varsayımları
DCF FCF marjlarını 2030'da %20'ye varsaydım. Ancak Cerebras OpenAI veri merkezlerini **inşa etme yükümlülüğünde** (S-1 dipnotu). 250 MW veri merkezi $5-10 milyar capex demek — bu Cerebras bilançosunda mı yoksa OpenAI'de mi göründüğü net değil. Eğer Cerebras'ın bilançosunda görünürse FCF marjları çok daha düşük olur, DCF değerlemesi 70-80 dolara çekilir.

### 7.4 Sektör Multiple Aralığının Geniş Olması
AI semicon'da P/S 18-46 arasında dağılmış (MRVL 18x → ARM 46x). CBRS hangi gruba yakın olacağı belirsiz. ARM-benzeri saf oyuncu profili premium çekerse multiple genişler, ama müşteri konsantrasyon iskontosu MRVL profiline çekerse multiple sıkışır.

### 7.5 OpenAI Sözleşmesinin Esnekliği
"Failure to deliver compute on time" maddesi ile OpenAI **tek taraflı çıkma hakkı** saklı tutuyor. Cerebras 250 MW/yıl teslim edemezse OpenAI sözleşmeyi kısmen veya tamamen iptal edebilir. Bu olasılık base case'de göz ardı edildi; ayı senaryosu için zayıf madde.

### 7.6 Pre-IPO TTM Verisinin Temsiliyeti
2025 gelirin %86'sı top 2 müşteriden geldi. 2026 gelir karışımı çok daha çeşitli olacak (OpenAI, AWS, sovereign), bu nedenle 2025 verisi 2026+ için **temsil edici değil**. Karşılaştırma multiple'ları uygularken yanlış zemin oluşturabilir.

### 7.7 Recency Bias (Yeni Sözleşmeler Etkisi)
13 Mart AWS, Ocak OpenAI sözleşmeleri 6 ay içinde imzalandı. Bu yoğun olumlu haber akışı **base case'i optimistik etkilemiş olabilir**. Tarihsel olarak yeni iş duyurusu bolluğunun ardından **yürütme zorluğu** evresi gelir (Snowflake 2021-2022 örneği). Adil değer hesabı bu psikolojik geri tepmeyi yansıtmıyor.

### 7.8 Dilüsyon Riski (Warrantlar + Lock-up)
33,4M OpenAI warrantı 2 GW tamamen alımında vest eder. Hisse sayısı 224M'den 257M'e çıkarsa **%15 dilüsyon**, hisse başına adil değer 127 dolardan **108 dolara düşer**. Bu sadece bir senaryo, ama olasılık düşük değil.

---

## 8. Belirsizlik Etiketleri

### KESİN (S-1 ve Resmi Kaynaklardan Doğrudan Veri)
- 2025 revenue: $510M (+%76 YoY)
- 2025 GAAP net income: $87,9M (içinde $363,3M non-cash gain)
- 2025 non-GAAP net loss: -$75,7M
- 2025 GAAP operating loss: -$145,9M
- 2025 gross margin: %39
- Cash and equivalents (Dec 31, 2025): $701,7M
- Backlog (RPO): $24,6B
- Backlog conversion: %15 in 2026-2027, %43 in 2028-2029, %42 in 2030+
- OpenAI MRA: 750 MW through 2028, $20B+ value, $1B loan @ 6%, 33,4M warrants
- OpenAI 2 GW opsiyonu: ek 1,25 GW through 2030
- AWS partnership: imzalandı 13 Mart 2026, Bedrock 2026 sonunda canlı
- IPO offering: 28M shares + 4,2M greenshoe
- Latest price range (10 Mayıs): $150-160 (per CNBC)
- Müşteri konsantrasyonu: MBZUAI %62 + G42 %24 = %86 (2025)
- ABD revenue %34 düşüş (2024-2025)
- Inference TAM (Bloomberg): $251B (2025) → $672B (2029), %28 CAGR
- 20x+ oversubscribed talep

### MUHTEMEL (Veriden Çıkarım, Makul Varsayım)
- 2026 revenue: $1,1-1,2B (underwriter konsensüs)
- 2027 revenue: $2,3-2,7B (backlog $1,85B/yıl avg + AWS rampup)
- 2028 revenue: $5,0-5,5B (backlog %43 dönüşümü)
- 2029 revenue: $6,5-7,5B
- 2026 net loss devam eder
- 2027 break-even, 2028 net profit
- Post-IPO toplam hisse sayısı: ~224M (basic), fully diluted ~257M (warrant dahil)
- 224M hisse × $155 mid IPO = $34,7B market cap
- Brüt marj 2027-2028 ramp: %42-45
- AWS Bedrock revenue başlangıcı: Q4 2026 / Q1 2027

### SPEKÜLATİF (Yorum, Marjinal Sapmaya Açık)
- IPO day-1 pop: %30-50 (200-220 dolar aralığı)
- 2030 sovereign AI sözleşmeleri: olası ama kanıtsız
- 2 GW OpenAI opsiyonunun %50+ yürürlüğe girme olasılığı
- NVIDIA fiyat baskısının 2027'de gerçekleşme olasılığı
- Lock-up sonrası (Kasım 2026) düşüş büyüklüğü
- Brüt marj %50+ erişimi 2028-2030 arasında
- Microsoft Azure veya Google Cloud sözleşmesi 2027'de
- CBRS'in "next NVIDIA" anlatısına oturma olasılığı

---

## 9. Portföy Karar Matrisi (3 Portföy)

| Portföy | Uygunluk | Gerekçe + Maks Ağırlık |
|---|---|---|
| **Dengeli ($100K)** | uygun_değil | Pre-IPO, 0 işlem geçmişi, müşteri konsantrasyon riski yüksek. Dengeli portföy max 6 pozisyon ve momentum/value blend felsefesi, IPO'ya açık değil. Day-1'de chase yasak (K-13 crisis rally kuralı). Lock-up sonrası (Kasım 2026+) hisse $100-120'ye geri çekilirse value tarafına geçebilir, o zaman tekrar değerlendirilir. |
| **Agresif Büyüme ($400K)** | uygun_koşullu | AI supply chain tezinin tam ortasında, momentum + earnings surprise profili uyuyor. Ancak **IPO day-1'de giriş YASAK** (K-rules gereği 1 gün cooldown + RSI confirmation). **İdeal giriş zonu: 2-4 hafta post-IPO consolidation aşamasında, $130-150 zonunda, eğer 50DMA oluşur ve teknik kırılım gelirse**. Maks ağırlık %4-5 ($16K-20K), tek pozisyon $20K üst sınır. Korelasyon: NVDA, AMD ile yüksek; bu pozisyonlar varsa CBRS pozisyon boyutu yarıya. |
| **Değer + Temettü ($100K)** | uygun_değil | Temettü ödemiyor, fundamentaller bozuk (net zarar), value metriği yok (P/S 50+). Hiçbir kriteri karşılamıyor. Geç. |

**Karar: AGRESİF PORTFÖY için AL_KADEMELİ (zonlama bekle), Dengeli ve Temettü için GEÇ.**

---

## 10. Giriş Planı (Agresif Portföy İçin)

| Parametre | Değer |
|---|---|
| Mevcut Fiyat | Pre-IPO, henüz işlem görmüyor |
| IPO Pricing Beklenen | $150-160 (13 Mayıs 2026 akşam) |
| İşlem Başlangıcı | 14 Mayıs 2026 |
| Beklenen Adil Değer | $127 (base), $185 (boğa), $75 (ayı) |
| Day-1 Pop Beklenen | %25-50 → $190-240 zonu |
| **İdeal Giriş Zonu** | **$130-150 (consolidation post-pop, 2-4 hafta sonra)** |
| **Stop Loss** | **$115** (-%14 ideal giriş zonundan, lifo-DMA20 altı) |
| Hedef 1 (Base) | $185 (12 ay, %42 getiri ideal girişten) |
| Hedef 2 (Bull) | $250+ (18-24 ay, AWS Bedrock + OpenAI ramp ile) |
| R/R Oranı | ~3,0 (R 15 dolar / R 45 dolar Base) |
| Pozisyon Boyutu | $16K-20K (Agresif %4-5) |
| **Bekle Koşulları (3 madde)** | 1) Day-1 ve Day-2 close gözlemlenir, K-13 1 gün cooldown uygulanır. 2) 5-7 gün post-IPO consolidation zonu oluşur, gün-içi volatilite %5'in altına iner. 3) NVDA + AMD + AVGO korelasyonu açılıştan sonra haftalık olarak izlenir; AI sektörü genel olarak düşüyorsa giriş ertelenir. |

**K-13 (Crisis Rally Day 1 Chasing) Uygulaması:**
- IPO day-1 ne kadar güçlü olursa olsun **CHASE YASAK**
- Day-1 ve Day-2 close izlenir
- En erken Day-5 sonrası, RSI 14 günde 60 altına dönmüşse, giriş düşünülebilir
- Şişme zonunda chase yapmak K-13'ü doğrudan ihlal eder

---

## 11. İzleme Tetikleyicileri (8 Madde)

1. **13 Mayıs 2026, ABD saati 20:00 sonrası**: IPO pricing açıklanır. Final fiyat $160 üzerinde ise base case multiple güncellenir. $145 altında pricing yapılırsa underwriter rakamı yumuşamıştır, base case adil değer 130 dolara çıkar.

2. **14 Mayıs 2026, NYSE açılış**: Day-1 open fiyatı izlenir. $200+ açılış = aşırı talep onayı, day-1 chase yasak. $170 altı = soğuk açılış, day-2 giriş zonu yakın olabilir.

3. **Q3 2026 Earnings (Ağustos sonu / Eylül başı 2026)**: İlk halka açık bilanço. **Kritik metrikler**: (a) Revenue $250M+ Q2/Q3 (yıllık $1B+ run rate), (b) Backlog raporu hala $24B+, (c) Müşteri sayısı 2'den 4-5'e çıkıyor mu, (d) Brüt marj %40+ tutuyor mu.

4. **Kasım 2026: Lock-up Expiration (180 gün)**: Insider, VC ve erken yatırımcı satış baskısı. Tarihsel ortalama: %15-25 düşüş 1 hafta içinde. Eğer hisse $130-140'a iner ve fundamentaller stabilse, **agresif portföy giriş zonu burada açılır**.

5. **Q4 2026 / Q1 2027: AWS Bedrock Cerebras Hardware Lansman**: AWS resmi olarak Cerebras CS-3 hardware'ı Amazon Bedrock'ta açılma duyurusu (Mart 2026 partnership açıklamasındaki "in the coming months" şartı). Lansman başarılı olursa **Bedrock revenue katkısı ölçülebilir**, base case Bull yöne kayar.

6. **2027 Q2 OpenAI 250 MW İlk Tranche Teslimat Doğrulaması**: Cerebras OpenAI'ye taahhüt ettiği ilk 250 MW kapasitesini 2026 sonu / 2027 başında teslim etmesi gerek. Teslimat gecikirse **OpenAI sözleşme iptal hakkı tetiklenebilir** — kritik tetik. Cerebras Q2 2027 earnings call'unda bu güncellemeyi ver.

7. **2027 Sonu: Backlog Dönüşüm Hızı Doğrulaması**: 2026-2027 toplam 24 ay sonunda kümülatif revenue $3,7B'a yakın mı? Bu rakamın %20'sinin altında kalırsa **backlog konvertibilite tezi çöker**, hisse $80-90'a düşer. %20'sinin üstünde geçerse **2028 patlamasına bilet** alınır.

8. **OpenAI 2 GW Ek Opsiyon Vesting**: Cerebras 8-K filing veya investor update ile 1,25 GW opsiyonunun yürürlüğe girdiğini bildirirse **bull case açılır**, 33,4M warrant tam vesting yolda, hisse $200+ hedeflenir.

---

## Ek: Karşılaştırma — IPO Fiyatlandırma Tablosu

| IPO Fiyatı | Market Cap (224M hisse) | P/S 2025 ($510M) | P/S 2026 ($1,2B) | P/S 2027 ($2,7B) |
|---|---|---|---|---|
| $115 | $25,8B | 50,5x | 21,5x | 9,5x |
| $125 | $28,0B | 54,9x | 23,3x | 10,4x |
| $135 | $30,2B | 59,2x | 25,2x | 11,2x |
| $145 | $32,5B | 63,7x | 27,1x | 12,0x |
| $155 | $34,7B | 68,0x | 28,9x | 12,9x |
| $160 | $35,8B | 70,2x | 29,8x | 13,3x |
| $180 (Day-1 pop) | $40,3B | 79,0x | 33,6x | 14,9x |
| $200 (Day-1 pop) | $44,8B | 87,8x | 37,3x | 16,6x |

**Yorum**: Day-1'de $180-200'ye fırlarsa 2027 P/S 16-17x olur — bu ARM (46x), AVGO (30x), NVDA (24x) bandında, agresif ama korkutucu değil. Ancak 2025 TTM P/S 79-87x **NVDA tarihsel zirvesinin (40x) iki katı**. Yani kısa vadeli aşırı, uzun vadeli savunulabilir.

---

## Kaynaklar

- Cerebras Systems Form S-1/A (4 Mayıs 2026, SEC filing)
- Cerebras Systems Form S-1 (17 Nisan 2026, SEC filing)
- CNBC (10 Mayıs 2026): IPO fiyat aralığı $150-160 revize
- CNBC (17 Nisan 2026): S-1 filing, OpenAI sözleşme detayları
- AWS Press Release (13 Mart 2026): Cerebras partnership announcement
- Cerebras Blog (26 Mart 2026): "Cerebras is coming to AWS"
- Renaissance Capital, Bloomberg, Reuters, Tom's Hardware, MarketWise
- Futurum Group S-1 teardown
- Yahoo Finance, SiliconANGLE, EBC Financial
- FMP karşılaştırılabilir multiple verileri (11 Mayıs 2026)

**Kaynak**: finzora ai
**Rapor Tarihi**: 11 Mayıs 2026, 10:30 (İstanbul saati)
**Versiyon**: v2.0 (sözleşme + iş bağlantıları entegre)
