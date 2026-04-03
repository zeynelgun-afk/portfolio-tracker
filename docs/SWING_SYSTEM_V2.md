# SWING TRADE SİSTEMİ v2.3 — ICHİMOKU + HACİM + ATR + ÖN FİLTRE

> **versiyon**: 2.3
> **son güncelleme**: 3 nisan 2026
> **önceki sistem**: sabit %5 stop / %10 hedef / RSI+MACD+SMA skor kartı
> **neden değişti**: ichimoku kendi başına komple bir trend sistemi. sabit stop/hedef ile karıştırmak çelişki yaratıyordu. yeni sistem tamamen dinamik.
> **v2.1 değişiklik**: TK cross giriş sinyali kaldırıldı (sahte sinyaller), minimum %5 stop mesafesi zorunluluğu eklendi
> **v2.2 değişiklik**: VIX rejimine göre çift katmanlı ön filtre sistemi eklendi (A+B+E+F) — sonra v2.3'te kaldırıldı
> **v2.3 değişiklik**: SPY 21SMA master switch (konum + eğim) eklendi. K-19 XLP dışlama. K-20 sektör RS dead cat bounce filtresi. ABEF kaldırıldı (184 sinyal analizinde %0 iyileştirme). 4/4 ichimoku zorunlu yapıldı (3/4 kaldırıldı)
>
> **61 dönem backtest özeti (2021-2026)**:
> - 184 ichimoku 3/4+ sinyal analiz edildi → 4/4 sinyal: %54 kâr, 3/4 sinyal: %49 kâr
> - ABEF filtreleri (A/B/E/F) hiçbiri anlamlı fark yaratmadı → kaldırıldı
> - yeni sistem: ichimoku 4/4 zorunlu + SPY > 21SMA + eğim ↗ + K-19 sektör dışlama + K-20 RS dead cat bounce filtresi
> - K-13b kriz modu: %85 kâr oranı (en güvenilir bileşen)
> - yıl bazlı: 2024 %100, 2025 %74, 2026 %85, 2023 %30, 2022 %40, 2021 %50
> - başarı tanımı: kârda kapanan trade = başarılı (sadece %10 hedef değil)

---

## FELSEFESİ

ichimoku kinko hyo zaten tek başına trend, momentum, destek ve direnç veriyor. ama iki eksiği var:

1. **hacim**: ichimoku tamamen fiyat bazlı. sinyalin arkasında gerçek alıcı/satıcı baskısı var mı bilmiyoruz. hacim teyidi sahte kırılımları filtreler
2. **ATR**: ichimoku dinamik seviyeler verir ama pozisyon boyutunu belirleyemiyor. ATR volatiliteyi ölçer, bununla risk bazlı lot hesaplarız

RSI ve MACD eklenmez. tenkan/kijun kesişimi zaten MACD'nin yaptığını yapıyor, chikou span momentum veriyor. üst üste yığmak karmaşıklık, çelişki ve analiz felci yaratır.

**SMA200 uzun vadeli referans olarak kullanılır.** ichimoku en uzun periyodu senkou span B (52 gün). SMA200 uzun vadeli trend perspektifi sağlar:

- fiyat > SMA200 → uzun vadeli trend yukarı, normal giriş
- fiyat < SMA200 → dikkat. ichimoku 4/4 sinyali yine de geçerli ama riskli. karar akışındaki filtreler (SPY master switch, K-19, K-20) zaten çoğu zayıf ortamı engelliyor. SMA200 ek bilgi olarak değerlendirilir, giriş engelleyen zorunlu filtre değildir
- SMA20 ve SMA50 eklenmez, bunların rolünü tenkan (9) ve kijun (26) zaten yapıyor

---

## 0. ÖN FİLTRE SİSTEMİ (v2.3 — GİRİŞ ÖNCESİ ZORUNLU)

> **61 dönem, 184 sinyal analizi (ocak 2021 — mart 2026)**:
>
> ABEF filtreleri (A: 52W yakınlık, B: 5gün momentum, E: volatilite, F: RSI>60) 184 ichimoku sinyali üzerinde test edildi. hiçbiri anlamlı fark yaratmadı:
> - filtre yok: %49 kâr oranı
> - ABEF toplu: %49 kâr oranı (sıfır iyileştirme)
> - tekil en iyi filtre (E): +2 puan (istatistiksel olarak anlamsız)
> - A filtresi (52W): -2 puan (zararlı)
>
> **gerçek ayrıştırıcı: ichimoku 4/4 vs 3/4**:
> - 4/4 sinyal (volume teyitli): %54 kâr
> - 3/4 sinyal (volume teyitsiz): %49 kâr
> - fark: +5 puan → ABEF'in tamamından daha etkili
>
> **karar**: ABEF kaldırıldı, 4/4 ichimoku zorunlu yapıldı
>
> K-13b kriz modu: %85 kâr oranı (en güvenilir bileşen)
> SPY eğim filtresi: ↗ yükselirken %67, ↘ düşerken %25 kâr (+42 puan fark)

### karar akışı (swing trade)

> **önemli**: bu akış sadece swing trade girişleri içindir. portföy pozisyonları (dengeli/agresif/temettü) farklı çıkış kuralları kullanır (K-11 kademeli çıkış).

```
ichimoku sinyali
        │
        ├── VIX <22 (normal)
        │     │
        │     ├── sinyal 4/4 mü? (volume teyit zorunlu)
        │     │     │
        │     │     ├── evet (4/4) → SPY > 21SMA + eğim ↗?
        │     │     │                  │
        │     │     │                  ├── evet → K-19 sektör kontrol
        │     │     │                  │           │
        │     │     │                  │           ├── XLP → ATLA
        │     │     │                  │           │
        │     │     │                  │           └── geçti → K-20 RS kontrol
        │     │     │                  │                        │
        │     │     │                  │                        ├── dead cat bounce → ATLA
        │     │     │                  │                        └── geçti → GİR (%10 hedef)
        │     │     │                  │
        │     │     │                  └── hayır → ATLA
        │     │     │
        │     │     └── hayır (3/4) → ATLA
        │
        ├── VIX 22-35 (kriz)
        │     └── ichimoku 4/4 + K-13b koşulları → GİR (yarım pozisyon, %10 hedef)
        │
        └── VIX >35 → ATLA
```

**tüm swing girişleri 4/4 ichimoku zorunlu.** 3/4 sinyaller (volume teyitsiz) swing'de değerlendirilmez.
portföy pozisyonlarında K-11 kademeli çıkış uygulanır, sabit hedef yoktur.

> **neden ABEF kaldırıldı**: 184 ichimoku sinyali üzerinde yapılan analiz sonucu ABEF filtrelerinin (52W yakınlık, 5gün momentum, 20gün volatilite, RSI>60) hiçbiri anlamlı fark yaratmadı. baseline %49 kâr oranı, ABEF ile %49 — sıfır iyileştirme. tekil en iyi filtre +2p, toplu ABEF -1p. buna karşılık 4/4 vs 3/4 sinyal ayrımı +5p fark yarattı. ABEF yerine 4/4 zorunluluğu daha etkili ve daha basit.

### SPY 21SMA master switch (konum + eğim)

VIX <22 ortamında girişten ÖNCE iki koşul kontrol edilir:
1. SPY kapanış > 21SMA (konum)
2. 21SMA bugün > 21SMA 5 gün önce (eğim yükseliyor)

her iki koşul da sağlanmalı. SPY 21SMA altındaysa VEYA 21SMA düşüş eğimindeyse swing girişi yapılmaz.

- konum hesaplama: SPY kapanış > SPY 21 günlük basit hareketli ortalama
- eğim hesaplama: 21SMA(bugün) > 21SMA(5 gün önce). eğim = (21SMA_bugün - 21SMA_5gün_önce) / 21SMA_5gün_önce × 100. eğim > 0 ise ↗ yükseliyor
- gerekçe: SPY 21SMA üzerinde ama eğim düşüyorsa momentum kırılıyor. 51 dönem backtestinde:
  SPY ↗ yükseliyor: kâr oranı %67
  SPY ↘ düşüyor:    kâr oranı %25 (+42 puan fark)
- neden 50SMA değil: 50SMA çok yavaş, ağu 2023'ü kaçırıyor, nis 2023 LLY'yi engelliyor. 21SMA swing trade zaman dilimiyle uyumlu
- K-13b yolunda (VIX >25) SPY kontrolü YAPILMAZ

### sektör dışlaması (K-19)

- XLP (temel tüketim / defansif) sektöründen swing girişi YAPILMAZ
- kapsam: MO, PM, KO, PEP, WMT, COST ve XLP'ye dahil diğer hisseler
- gerekçe: 51 dönem backtestinde XLP'den 0 kâr, 2 zarar. defansif hisseler yapısal olarak düşük volatiliteye sahip, %10 hedefe ulaşamıyor
- bu kural sadece swing trade için geçerli. portföy pozisyonu olarak XLP alınabilir
- K-13b kriz modunda da XLP'den swing girişi yapılmaz

### sektör RS dead cat bounce filtresi (K-20)

sektör ETF'inin SPY'a göre relative strength'i kontrol edilir. orta vadede zayıflayan ama kısa vadede sıçrayan sektördeki trade'ler engellenir.

- hesaplama:
  RS oranı = sektörETF(bugün) / SPY(bugün)
  RS20 = (RS_bugün - RS_20gün_önce) / RS_20gün_önce × 100
  RS10 = (RS_bugün - RS_10gün_önce) / RS_10gün_önce × 100
- kural: RS20 < 0 VE RS10 > 0 ise → GİRME (dead cat bounce riski)
- sektör ETF eşleştirme: XLK (tech), XLC (iletişim), XLE (enerji), XLI (sanayi), XLV (sağlık), XLF (finans), XLY (tüketici isteğe bağlı)
- gerekçe: 76 trade backtestinde bu kombinasyon %80 zarar oranı gösterdi (3 kâr / 12 zarar). sektör orta vadede zayıflamış ama kısa vadede sıçramış → sahte toparlanma, trend devam ediyor
- filtre etkisi: filtresiz %47 kâr → filtre ile %54 kâr (+7 puan). 12 zarar önlendi, 3 küçük kâr kaçırıldı
- K-13b kriz modunda bu filtre UYGULANMAZ (kriz modunun kendi sektör ETF SMA filtresi var)

### K-13b özet referans (VIX >25 ortamında)

VIX >25'te ichimoku 4/4 + volume teyit + sektör ETF SMA filtresi. giriş koşulları (tümü zorunlu):
1. ichimoku skoru tam 4/4 (kumo üstü + TK bull + tenkan üstü + volume 1.3x+)
2. hissenin sektör ETF'i (XLK/XLE/XLI/XLC/XLV/XLF/XLY/XLU/XLB) hem 9SMA hem 21SMA üzerinde (**not**: XLP hisseleri K-19 gereği swing'de alınmaz, ancak XLP ETF genel piyasa sağlık göstergesi olarak kontrol edilebilir)
3. mcap >$5B
4. RSI 40-70
5. K-18 insider temiz
6. K-17 korelasyon >%50
uygulama kuralları: max 2 eşzamanlı, sektör başına 1, hedef sabit %10

detaylar: docs/TRADING_PLAYBOOK.md K-13 v3 bölümü

---

## 1. GİRİŞ SİNYALLERİ

iki giriş tipi var. ikisi de ichimoku bazlı, hacim teyidi zorunlu.

### 1a. KUMO KIRILIMI (en güçlü sinyal)

fiyat kumo'nun üst kenarını (senkou span A veya B, hangisi üstteyse) yukarı doğru kırar ve o seviyenin üstünde kapanır.

**koşullar**:
- fiyat dünkü kapanışta kumo içinde veya altındaydı
- bugün kumo üst kenarının üstünde kapandı
- tenkan > kijun (veya en azından eşit)
- kumo rengi yeşil (senkou A > senkou B) tercih edilir. kırmızı kumo'dan çıkış daha zayıf sinyal
- **hacim teyidi**: kırılım günü hacim > 20 günlük ortalama hacmin 1.2 katı

**güç**: yüksek. kumo kalın ise direnç güçlüydü demek, kırılım anlamlı. kumo ince ise dikkatli ol, sahte kırılım olabilir.

### ~~1b. TK CROSS~~ (v2.1'de kaldırıldı)

tek başına anlamlı giriş sinyali üretmiyordu. sahte sinyaller çok fazlaydı, özellikle yatay piyasalarda sürekli tetikleniyordu. TK cross aşağı yönlü kesişim çıkış sinyali olarak korunuyor (bölüm 3b).

### 1c. KİJUN BOUNCE (geri çekilme girişi)

fiyat yükseliş trendinde kijun-sen'e geri çekilir ve oradan seker.

**koşullar**:
- fiyat kumo üzerinde
- tenkan > kijun (trend yukarı)
- fiyat kijun'a dokundu veya çok yaklaştı (fark < %1)
- kijun'dan sekerek yukarı döndü (bugün kapanış > kijun)
- **hacim teyidi**: sekme günü hacim > 20 günlük ortalama hacmin 0.8 katı (düşük hacimde bile olabilir, çünkü düşüşte hacim azalması normal)

**güç**: trend devamı sinyali. ilk girişi kaçırınca veya ekleme (piramitleme) için kullanılır.

**stop notu**: kijun bounce'ta fiyat kijun'a çok yakın olduğu için kijun bazlı stop mesafesi <%5 çıkar. bu durumda stop otomatik olarak kumo alt kenarına genişletilir (daha geniş stop mesafesi, daha küçük pozisyon boyutu).

---

## 2. STOP-LOSS (DİNAMİK)

sabit yüzde yok. stop seviyeleri ichimoku bileşenlerinden türetilir ve ATR ile doğrulanır.

### stop belirleme hiyerarşisi

**minimum %5 stop mesafesi kuralı** (v2.1 ile eklendi): giriş fiyatından %5'ten küçük stop mesafesi olan adaylar elenir. ancak bu kural giriş tipine göre farklı uygulanır:

- **kumo kırılımı**: kijun bazlı stop <%5 ise → giriş reddedilir (whipsaw riski)
- **kijun bounce**: doğası gereği kijun'a çok yakın olacağı için stop otomatik olarak kumo alt kenarına genişletilir. kumo alt ile bile <%2 kalıyorsa o zaman reddedilir
- **sinyal yokken**: <%5 stop mesafesi olan hisseler genel olarak reddedilir

fiyat kumo üzerindeyse:

| öncelik | stop seviyesi | ne zaman kullanılır |
|---------|---------------|---------------------|
| 1 | kijun-sen | varsayılan stop. fiyat kijun altında kapanırsa çık |
| 2 | kumo üst kenarı | kijun çok yakınsa (<%1) kumo'ya genişlet |
| 3 | kumo alt kenarı | güçlü trend, geniş stop istiyorsan. kumo altına kapanış = trend bitti |

fiyat kumo içindeyse (kumo kırılımı bekleniyor):
- stop = kumo alt kenarı. kumo altına kapanış = tez bozuldu

### ATR doğrulaması

stop mesafesi çok dar veya çok geniş olmamalı. ATR(14) ile kontrol:

- stop mesafesi < 0.5x ATR → stop çok dar, whipsaw riski yüksek. kijun yerine kumo'ya genişlet
- stop mesafesi > 3x ATR → stop çok geniş, pozisyon çok küçük olacak. girişi ertele veya farklı zaman dilimi kullan
- ideal: stop mesafesi 1x-2.5x ATR arasında

### stop güncelleme (trailing)

sabit yüzde trailing yok. kijun-sen doğal trailing stop olarak çalışır:

- kijun-sen her gün yeniden hesaplanır (26 günlük en yüksek + en düşük / 2)
- trend güçlüyken kijun yukarı hareket eder, stop otomatik yükselir
- fiyat kijun altında kapanırsa → çıkış
- kijun düz seyrediyorsa (konsolidasyon) → mevcut stop koru, acele etme

**önemli**: kijun aşağı hareket ederse stop aşağı çekilmez. stop sadece yukarı yönde güncellenir (en yüksek kijun değeri korunur).

---

## 3. ÇIKIŞ SİNYALLERİ

stop dışında üç çıkış sinyali var:

### 3a. KİJUN ALTI KAPANIŞ (birincil çıkış)

fiyat kijun-sen altında kapanırsa → ertesi gün aç, çık.

tek günlük ihlal sahte olabilir. doğrulama: kapanış kijun'un %0.5'inden fazla altındaysa → hemen çık. kijun'a çok yakın kapanışta (<%0.5) → bir gün daha bekle.

### 3b. TK CROSS AŞAĞI (trend dönüşü — filtreli)

tenkan-sen kijun-sen'i aşağı keserse → potansiyel çıkış sinyali. ama v2.1'de giriş sinyali olarak kaldırıldığı gibi, çıkışta da sahte sinyal üretebilir (özellikle yatay piyasalarda).

filtre:
- fark > %1 VE hacim > 1.0x ortalama → güçlü sinyal, çık
- fark > %0.5 ama hacim düşük → yarın teyit bekle (bir gün daha ver)
- fark < %0.5 → sahte sinyal olasılığı yüksek, hacim + OBV teyidi olmadan çıkma

bu sinyal genellikle kijun altı kapanıştan sonra gelir ama bazen önce gelir. kijun altı kapanış daha güvenilir birincil sinyal, TK cross ikincil teyit olarak kullanılır.

### 3c. KUMO'YA GİRİŞ (trend zayıflama)

fiyat yukarıdan kumo'nun içine girerse → kısmi çıkış (%50). kumo altına inerse → tam çıkış.

### 3d. HACİM UYARISI

yükselişte hacim sürekli azalıyorsa (3 ardışık gün düşen hacim + yükselen fiyat) → uyarı. satıcı baskısı yaklaşıyor olabilir. pozisyon daralt veya stop sıkılaştır.

---

## 4. POZİSYON BOYUTLANDIRMA (ATR BAZLI)

sabit lot veya sabit tutar yok. risk bazlı hesaplama:

### formül

```
risk_tutari = hesap_buyuklugu * risk_yuzdesi
stop_mesafesi = giris_fiyati - stop_seviyesi
pozisyon_buyuklugu = risk_tutari / stop_mesafesi
```

### parametreler

| parametre | değer | açıklama |
|-----------|-------|----------|
| risk_yuzdesi | %1 | tek trade'de kaybedilecek max tutar (hesabın %1'i) |
| min_stop_mesafesi | 0.5x ATR(14) | bunun altında stop çok dar |
| max_stop_mesafesi | 3x ATR(14) | bunun üstünde giriş ertele |
| max_pozisyon_tutari | hesabın %12.5'i | tek pozisyon max (8 slot / %100) |

### ATR hesaplama

ATR(14) = son 14 günün true range ortalaması
true range = max(yüksek-düşük, abs(yüksek-önceki kapanış), abs(düşük-önceki kapanış))

### örnek

- hesap: $10,000 swing sermayesi
- risk: %1 = $100
- AROC giriş: $37.56, kijun: $34.98, stop: $34.98
- stop mesafesi: $37.56 - $34.98 = $2.58
- ATR(14): $1.20, stop mesafesi = 2.15x ATR (ideal aralıkta)
- pozisyon: $100 / $2.58 = 38 hisse
- pozisyon tutarı: 38 * $37.56 = $1,427 (hesabın %14.3'ü, max %12.5 aşıyor → 33 hisseye düşür)

### VIX düzeltmesi

| VIX | risk_yuzdesi | açıklama |
|-----|--------------|----------|
| <22 | %1.0 | normal mod — karar akışında tam pozisyon |
| 22-35 | %0.50 | K-13b kriz modu — yarım pozisyon |
| >35 | girme | hiç giriş yapılmaz |

---

## 5. HACİM ANALİZİ

### OBV (on-balance volume) trendi

OBV = kümülatif hacim. fiyat yükseldiği günlerde hacim eklenir, düştüğü günlerde çıkarılır.

**kullanım**:
- OBV yükseliyor + fiyat yükseliyor → trend sağlıklı, teyit
- OBV yükseliyor + fiyat yatay → birikim, kırılım yakın (pozitif)
- OBV düşüyor + fiyat yükseliyor → ayrışma, trend zayıflıyor (uyarı)
- OBV düşüyor + fiyat düşüyor → dağıtım, uzak dur

### hacim profili (giriş teyidi)

- kırılım günü hacim > 1.2x ortalama → teyit
- kırılım günü hacim < ortalama → sahte kırılım riski, yarım pozisyonla gir veya bekle
- ardışık 3+ gün artan hacim + yükselen fiyat → momentum güçlü

---

## 6. TEMEL ANALİZ (claude değerlendirir)

script temel analiz yapmaz. her taramada claude hisse bazında bağlamsal değerlendirme yapar:

- sektör normları (utilities/REIT yüksek borç normaldir, büyüme şirketlerinde FCF negatif olabilir)
- döngüsel etki (enerji gelir küçülmesi petrol fiyatına bağlı, sabit kural ile filtrelenmez)
- katalizör ve tez uyumu (şirketin hikayesi teknik sinyalle tutarlı mı)
- risk/ödül dengesi (pozisyon büyüklüğüne yansıtılır)

sabit rasyolarla otomatik red yok. karar claude'da.

---

## 7. SİNYAL TABLOSU (eski sistemle karşılaştırma)

| eski sistem | yeni sistem |
|-------------|-------------|
| sabit %5 stop | kijun-sen dinamik stop (min %5 mesafe zorunlu) |
| sabit %10 hedef | sabit %10 hedef (tüm swing girişleri ön filtreden geçer, hedefe ulaşınca veya stop tetiklenince çıkış) |
| RSI oversold giriş | ichimoku kumo kırılımı / kijun bounce giriş |
| MACD teyidi | gereksiz (TK cross kaldırıldı, tek başına anlamlı değildi) |
| SMA20/50 pozisyon kontrolü | ichimoku kumo bunu zaten yapıyor |
| SMA200 filtresi | SMA200 referans bilgi olarak korundu (zorunlu filtre değil) |
| sabit %5 trailing | kijun-sen doğal trailing |
| 7-14 gün tutma süresi | %10 hedefe veya stop'a kadar tut. süre sınırı yok ama K-08 zaman filtresi uygulanır |
| skor kartı (7 puan) | ichimoku 4/4 + SPY master switch + K-19/K-20 filtreleri |
| sabit lot | ATR bazlı risk hesaplı lot |

---

## 8. JSON ŞEMA DEĞİŞİKLİKLERİ

### aktif pozisyon (data/swing/active.json)

eski alanlar kaldırılan:
- ~~hedef_fiyat~~ → giriş fiyatı x 1.10 sabit hedef (tüm swing girişleri filtreden geçtiği için %10 hedef zorunlu)
- ~~trailing_yuzde~~ → kijun trailing
- ~~zaman_cercevesi~~ → süre sınırı yok
- ~~partial_exit_plan~~ → ichimoku çıkış sinyalleri

yeni/değişen alanlar:

```json
{
  "id": "SWING-028",
  "sembol": "AROC",
  "giris_tarihi": "2026-03-24",
  "giris_fiyati": 37.56,
  "giris_sinyali": "kumo_kirilimi",
  "guncel_fiyat": 37.02,
  "guncel_kar_zarar_yuzde": -1.44,
  "stop_loss": 34.98,
  "stop_tipi": "kijun",
  "stop_en_yuksek": 34.98,
  "kijun_sen": 34.98,
  "kumo_ust": 35.54,
  "kumo_alt": 31.45,
  "tenkan_sen": 36.09,
  "atr_14": 1.20,
  "hacim_oran": 1.3,
  "obv_trend": "yukselis",
  "tutulan_gun": 0,
  "giris_nedeni": "ichimoku: kumo kırılımı + hacim teyidi 1.3x",
  "katalizor": "enerji sektörü güçlü, doğalgaz sıkıştırma talebi artışta",
  "tez": "ichimoku tam yükseliş: kumo üstü + trend yukarı. düşük beta enerji hizmet şirketi.",
  "risk": "enerji fiyatlarında sert düşüş",
  "durum": "✅ normal",
  "son_guncelleme": "2026-03-25T09:00:00"
}
```

### çıkış kaydı ek alanlar (data/swing/closed.json)

```json
{
  "cikis_sinyali": "kijun_alti_kapanis",
  "stop_tipi_cikis": "kijun",
  "atr_giris": 1.20,
  "atr_cikis": 1.35,
  "max_fiyat": 41.20,
  "max_kar_zarar_yuzde": 9.70
}
```

---

## 9. GÜNLÜK İŞ AKIŞI

### seans öncesi
1. `python scripts/swing_ichimoku.py --aktif` → tüm aktif pozisyonlar için ichimoku seviyeleri güncelle
2. kijun değişti mi kontrol et → stop güncelle (sadece yukarı)
3. kumo yakınında mı kontrol et → çıkış uyarısı

### seans içi
4. stop tetiklendi mi → çık
5. yeni kumo kırılımı veya kijun bounce var mı → giriş değerlendir

### seans sonrası
6. `python scripts/swing_ichimoku.py SEMBOL1,SEMBOL2` → aday tarama
7. hacim teyidi kontrolü
8. JSON güncelle, git push

---

## 10. NOTLAR

- NEM ve AROC v1 sisteminden v2'ye geçiş (mart 2026) tamamlanmış, her iki pozisyon da kapatılmıştır
- v1 skor kartı sistemi (7 puan, sabit %5/%10) artık kullanılmıyor
- v2.1'de TK cross giriş sinyali kaldırıldı, v2.2'de ABEF eklendi, v2.3'te ABEF kaldırılıp 4/4 zorunlu yapıldı

---

*finzora ai | swing sistemi v2.3 | 3 nisan 2026*
