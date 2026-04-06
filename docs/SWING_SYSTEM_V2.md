# SWING TRADE SİSTEMİ v2.3 — ICHİMOKU + CHANDELİER EXİT + ÖN FİLTRE

> **versiyon**: 2.3
> **son güncelleme**: 6 nisan 2026
> **önceki sistem**: sabit %5 stop / %10 hedef / RSI+MACD+SMA skor kartı
> **neden değişti**: ichimoku kendi başına komple bir trend sistemi. sabit stop/hedef ile karıştırmak çelişki yaratıyordu. yeni sistem: stop dinamik (chandelier), hedef sabit (%10).
> **v2.1 değişiklik**: TK cross giriş sinyali kaldırıldı (sahte sinyaller), minimum %5 stop mesafesi zorunluluğu eklendi
> **v2.2 değişiklik**: VIX rejimine göre çift katmanlı ön filtre sistemi eklendi (A+B+E+F) — sonra v2.3'te kaldırıldı
> **v2.3 değişiklik**: SPY 21EMA master switch (konum + eğim). K-19 XLP dışlama. K-20 sektör RS dead cat bounce. ABEF kaldırıldı (184 sinyal, %0 iyileştirme). 4/4 ichimoku zorunlu. kijun trailing → chandelier exit (3×ATR) — 126 trade: +45% P/L iyileştirme. tarama evreni: sabit liste → FMP screener dinamik evren (~1,100 hisse, mcap >$2B). mcap eşiği $5B → $2B
>
> **61 dönem backtest özeti (2021-2026)**:
> - 184 ichimoku 3/4+ sinyal analiz edildi → 4/4 sinyal: %54 kâr, 3/4 sinyal: %49 kâr
> - ABEF filtreleri (A/B/E/F) hiçbiri anlamlı fark yaratmadı → kaldırıldı
> - yeni sistem: ichimoku 4/4 zorunlu + chandelier exit (3×ATR) + SPY > 21EMA + eğim ↗ + K-19 sektör dışlama + K-20 RS dead cat bounce filtresi
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
ichimoku sinyali (4/4 zorunlu, 3/4 → ATLA)
        │
        ├── K-13 v4.1: sektör faydalanıcı mı duyarlı mı?
        │
        ├── FAYDALANICI SEKTÖR (savunma, enerji, altın, sağlık, staples, telekom, utilities, siber güvenlik)
        │     │
        │     ├── VIX <28 → SPY > 21EMA + eğim ↗? (VIX <22 iken zorunlu, VIX 22-28 iken önerilir)
        │     │     │
        │     │     ├── evet → K-19 → K-20 → GİR (tam pozisyon)
        │     │     └── hayır + VIX <22 → ATLA | VIX 22-28 → ichimoku 4/4 yeterliyse yarım pozisyon
        │     │
        │     ├── VIX 28-35 → yarım pozisyon, stop 3xATR, SPY kontrol yok
        │     └── VIX 35+ → çeyrek pozisyon
        │
        ├── DUYARLI SEKTÖR (tech/AI, tüketim döngüsel, havacılık, küçük sermaye, spekülatif)
        │     │
        │     ├── VIX <22 → SPY > 21EMA + eğim ↗ → K-19 → K-20 → GİR (tam pozisyon)
        │     ├── VIX 22-28 → SPY > 21EMA + eğim ↗ → K-19 → K-20 → GİR (yarım pozisyon)
        │     ├── VIX 28-35 → giriş yok (istisna: K-13b 6 koşul sağlanırsa çeyrek pozisyon)
        │     └── VIX 35+ → ATLA (K-13b bile izin vermez)
        │
        └── PEAD GİRİŞİ (K-05 v3 Aşama 2 — ichimoku 4/4 gerekmez, kendi koşulları var)
              └── kazanç sürprizi ≥%10 + gap-up + hacim 2x + 2. gün trigger → yarım pozisyon
```

**tüm ichimoku bazlı swing girişleri 4/4 zorunlu.** 3/4 sinyaller (volume teyitsiz) swing'de değerlendirilmez.
**PEAD girişleri** (K-05 v3 Aşama 2) ichimoku 4/4 gerektirmez, kendi giriş koşulları vardır (bkz. aşağıda 1d).
portföy pozisyonlarında K-11 kademeli çıkış uygulanır, sabit hedef yoktur.

**hedef ve çıkış politikası (v2.3.1 — 6 nisan 2026):**
eski sistem sabit %10 hedef kullanıyordu. sorun: birçok trade %7-8'de zirve yapıp geri dönüyor, %10'u görmeden chandelier stop'ta düşük kârla veya zararda çıkıyordu. backtest'te başarı tanımı zaten "kârda kapanma" idi, "%10'a ulaşma" değil.
yeni sistem: sabit hedef kaldırıldı, chandelier trailing birincil çıkış mekanizması. ek olarak kâr kilidi mekanizması:
  - kâr <%7: chandelier 3×ATR trailing (normal)
  - kâr %7-15: chandelier 2×ATR'ye sıkılaştır (kâr kilidi — geri vermeyi önle)
  - kâr %15+: chandelier 1.5×ATR (agresif kâr koruma)
  - ichimoku çıkış sinyalleri (TK aşağı kesişim, kumo'ya giriş) hala geçerli
bu sayede %7-8 kârda olan trade korunurken, %15-20 trend devamı engellenmiyor.

> **neden ABEF kaldırıldı**: 184 ichimoku sinyali üzerinde yapılan analiz sonucu ABEF filtrelerinin (52W yakınlık, 5gün momentum, 20gün volatilite, RSI>60) hiçbiri anlamlı fark yaratmadı. baseline %49 kâr oranı, ABEF ile %49 — sıfır iyileştirme. tekil en iyi filtre +2p, toplu ABEF -1p. buna karşılık 4/4 vs 3/4 sinyal ayrımı +5p fark yarattı. ABEF yerine 4/4 zorunluluğu daha etkili ve daha basit.

### SPY 21EMA master switch (konum + eğim)

VIX <22 ortamında girişten ÖNCE iki koşul kontrol edilir (VIX 22-28'de faydalanıcı sektörlerde önerilir ama zorunlu değil):
1. SPY kapanış > 21EMA (konum)
2. 21EMA bugün > 21EMA 5 gün önce (eğim yükseliyor)

her iki koşul da sağlanmalı. SPY 21EMA altındaysa VEYA 21EMA düşüş eğimindeyse swing girişi yapılmaz.

- konum hesaplama: SPY kapanış > SPY 21 günlük üstel hareketli ortalama (EMA)
- eğim hesaplama: 21EMA(bugün) > 21EMA(5 gün önce). eğim = (21EMA_bugün - 21EMA_5gün_önce) / 21EMA_5gün_önce × 100. eğim > 0 ise ↗ yükseliyor
- gerekçe: SPY 21EMA üzerinde ama eğim düşüyorsa momentum kırılıyor. backtestinde:
  SPY ↗ yükseliyor: kâr oranı %67
  SPY ↘ düşüyor:    kâr oranı %25 (+42 puan fark)
- neden EMA: EMA son fiyatlara daha fazla ağırlık verir, rejim değişikliğini SMA'dan 1-2 gün önce yakalar. swing trade kısa vadeli zaman dilimiyle uyumlu. 50 ve 200 periyot için SMA kalır (endüstri standardı, kurumsal referans)
- neden 50SMA değil: 50SMA çok yavaş, ağu 2023'ü kaçırıyor, nis 2023 LLY'yi engelliyor. 21EMA swing trade zaman dilimiyle uyumlu
- FMP çağrısı: `technical-indicators/ema` (periodLength=21, timeframe=1day)
- K-13 v4.1: faydalanıcı sektörlerde VIX 22-28 arası SPY kontrolü önerilir ama zorunlu değil. VIX 28+ iken SPY kontrolü yapılmaz. duyarlı sektörlerde VIX 22-28 arası SPY kontrolü zorunlu

### sektör dışlaması (K-19)

- XLP (temel tüketim / defansif) sektöründen swing girişi YAPILMAZ
- kapsam: MO, PM, KO, PEP, WMT, COST ve XLP'ye dahil diğer hisseler
- gerekçe: backtestinde XLP'den 0 kâr, 2 zarar. defansif hisseler yapısal olarak düşük volatiliteye sahip, %10 hedefe ulaşamıyor
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
- K-13b istisnası pozisyonlarında bu filtre uygulanmaz (K-13b'nin kendi sektör ETF SMA filtresi var). diğer tüm VIX bantlarında uygulanır

### K-13b özet referans (sadece VIX-duyarlı sektörlerde, VIX 28-35 arası)

K-13 v4.1 ile K-13b artık sadece duyarlı sektörlere uygulanır. faydalanıcı sektörler K-13 v4.1 matrisiyle zaten izinli. duyarlı sektörlerde VIX 28-35 arası ichimoku 4/4 + 6 koşul sağlanırsa çeyrek pozisyon izni. giriş koşulları (tümü zorunlu):
1. ichimoku skoru tam 4/4 (kumo üstü + TK bull + tenkan üstü + volume 1.3x+)
2. hissenin sektör ETF'i (XLK/XLE/XLI/XLC/XLV/XLF/XLY/XLU/XLB) hem 9SMA hem 21EMA üzerinde (**not**: XLP hisseleri K-19 gereği swing'de alınmaz, ancak XLP ETF genel piyasa sağlık göstergesi olarak kontrol edilebilir)
3. mcap >$2B
4. RSI 40-70
5. K-18 insider temiz
6. K-17 korelasyon >%50
uygulama kuralları: max 2 eşzamanlı, sektör başına 1, kâr kilidi sistemi (<%7: 3×ATR, %7-15: 2×ATR, %15+: 1.5×ATR), stop: chandelier exit — normal modla aynı

detaylar: docs/TRADING_PLAYBOOK.md K-13 v4.1 bölümü

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

**stop notu**: kijun bounce'ta fiyat kijun'a çok yakın girişi olduğu için chandelier stop (giriş_fiyatı - 3×ATR) genellikle kijun'dan daha geniş alan tanır. bu yüzden kijun bounce girişleri chandelier ile daha iyi korunur. chandelier stop mesafesi yine de <%5 ise → giriş reddedilir.

### 1d. PEAD GİRİŞİ (kazanç sonrası sürüklenme — K-05 v3 Aşama 2)

kazanç açıklaması sonrası sürpriz yönünde devam eden fiyat hareketinden (post-earnings announcement drift) faydalanma. bu giriş tipi ichimoku 4/4 gerektirmez — kendi koşulları var.

**koşullar (TÜMÜ sağlanmalı):**
1. kazanç sürprizi ≥%10 (EPS actual vs estimate)
2. ilk gün tepkisi sürprizle aynı yönde: pozitif sürpriz → gap-up, negatif → gap-down
3. ilk gün hacim ≥ 20 günlük ortalama hacmin 2 katı (kurumsal ilgi teyidi)
4. 2. gün trigger candle: ilk gün yüksek/düşüğünü kırmadan konsolide + yeni mum aynı yönde kapanış
5. ilk güne GİRME (K-02 ile tutarlı)

**pozisyon:** yarım pozisyon (kazanç sonrası volatilite hala yüksek)
**stop:** ilk gün (açıklama günü) düşüğü altı (long) veya yükseği üstü (short)
**çıkış:** chandelier trailing ile kâr kilidi sistemi (<%7: 3×ATR, %7-15: 2×ATR, %15+: 1.5×ATR)
**süre:** 60 işlem günü drift veya stop tetiklenene kadar. K-08 zaman filtresi uygulanır ama tolerans 15 gün yerine 30 gün (PEAD drifti daha yavaş gelişir)

**akademik kanıt:** Ball & Brown (1968), Bernard & Thomas (1989). çeyreklik %2.6-9.37 anormal getiri. momentum hisselerde (küçük sermaye, düşük analist takibi) daha güçlü
**kendi kanıtımız:** henüz backtest edilmedi. gelecek kazanç sezonunda (nisan 2026 Q1 sonuçları) ilk 5-10 PEAD trade'i simülasyon olarak kaydedilecek

**güç**: orta-yüksek. ichimoku sinyalinden farklı bir alfa kaynağı — teknik değil temel veri bazlı. iki sistem birbirini tamamlıyor.

**ilişkili:** K-05 v3 Aşama 3 (tedarik zinciri yayılım) da PEAD benzeri giriş ama lider şirket yerine ortaklarına uygulanır

---

## 2. STOP-LOSS (CHANDELİER EXİT — 3×ATR)

> **v2.3 değişiklik**: kijun-sen trailing stop → chandelier exit (3×ATR) olarak değiştirildi.
> kanıt: 126 trade karşılaştırmasında chandelier +57.1% vs kijun +12.0% toplam P/L (+45.1% fark).
> kijun çok sıkı — normal volatiliteyi stop olarak algılıyordu (gün 2'de gereksiz çıkışlar).
> chandelier trende daha fazla nefes alanı tanıyor.
> çarpan testi: 2×(-52%), 2.5×(+24%), **3×(+57%)**, 3.5×(+66%), 4×(+71%). 3× seçildi: en çok trade'de kazanan (31/25), makul worst-case (-5.6%), standart literatür ayarı.

### chandelier exit formülü

```
ilk stop = giriş_fiyatı - 3 × ATR(14)
trailing: highest_high - 3 × ATR(14)
```

- highest_high: giriş gününden itibaren ulaşılan en yüksek fiyat (intraday high)
- ATR(14): son 14 günün true range ortalaması, her gün yeniden hesaplanır
- stop sadece YUKARI hareket eder (highest high artınca veya ATR düşünce stop yükselir)
- fiyat stop seviyesine dokunursa (intraday low ≤ stop) → çıkış

### minimum stop mesafesi

giriş fiyatından chandelier stop'a kadar mesafe <%5 ise → giriş reddedilir (whipsaw riski)

- kumo kırılımı: 3×ATR < fiyatın %5'i ise → ATR çok düşük, hisse yeterince hareketli değil
- kijun bounce: fiyat kijun'a yakın olduğu için mesafe zaten dar olabilir. bu durumda chandelier stop doğal olarak daha geniş alan tanır (kijundan bağımsız)

### ATR hesaplama

ATR(14) = son 14 günün true range ortalaması
true range = max(yüksek-düşük, abs(yüksek-önceki kapanış), abs(düşük-önceki kapanış))

### neden kijun değil chandelier

| metrik | kijun | chandelier 3×ATR |
|--------|:-----:|:----------------:|
| toplam P/L (126 trade) | +12.0% | **+57.1%** |
| kâr oranı | 45% | **49%** |
| trade başına beklenen değer | +0.10% | **+0.46%** |

kijun sorunu: 26 günlük en yüksek+en düşük ortalaması bazen giriş fiyatına çok yakın kalıyor. özellikle dar range sonrası breakout'larda kijun giriş fiyatının %1-2 altında olabiliyor → normal geri çekilmede gereksiz stop. chandelier entry high'dan 3×ATR mesafede durarak trende nefes alanı tanıyor.

---

## 3. ÇIKIŞ SİNYALLERİ

chandelier stop dışında ek çıkış sinyalleri:

### 3a. CHANDELİER STOP TETİKLENME (birincil çıkış)

intraday low ≤ chandelier stop seviyesi → çıkış. bu otomatik ve mekanik bir çıkış.

### 3b. TK CROSS AŞAĞI (trend dönüşü — ikincil teyit)

tenkan-sen kijun-sen'i aşağı keserse → potansiyel erken uyarı. chandelier henüz tetiklenmemiş olabilir.

filtre:
- fark > %1 VE hacim > 1.0x ortalama → güçlü sinyal, çık (chandelier bekleme)
- fark > %0.5 ama hacim düşük → uyarı, chandelier bekle
- fark < %0.5 → sahte sinyal olasılığı yüksek, chandelier'a güven

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
| min_stop_mesafesi | fiyatın %5'i | bunun altında giriş reddedilir |
| max_stop_mesafesi | chandelier: 3x ATR(14) | çarpan sabit (3×), ATR günlük güncellenir |
| max_pozisyon_tutari | hesabın %16.7'si | tek pozisyon max (6 slot / %100) |

### ATR hesaplama

bkz. bölüm 2 (chandelier exit) — ATR(14) formülü orada tanımlı.

### örnek

- hesap: $10,000 swing sermayesi
- risk: %1 = $100
- AROC giriş: $37.56, ATR(14): $1.20
- chandelier stop: $37.56 - 3 × $1.20 = $33.96
- stop mesafesi: $37.56 - $33.96 = $3.60 (fiyatın %9.6'sı, min %5 geçiyor ✅)
- pozisyon: $100 / $3.60 = 27 hisse
- pozisyon tutarı: 27 × $37.56 = $1,014 (hesabın %10.1'i, max %12.5 altında ✅)

### VIX düzeltmesi

| VIX | faydalanıcı sektör risk% | duyarlı sektör risk% | açıklama |
|-----|:------------------------:|:--------------------:|----------|
| <22 | %1.0 | %1.0 | her iki grup tam pozisyon |
| 22-28 | %1.0 | %0.50 | faydalanıcı tam, duyarlı yarım |
| 28-35 | %0.50 | K-13b: %0.25 veya girme | faydalanıcı yarım, duyarlı sadece K-13b istisnasıyla |
| 35+ | %0.25 | girme | faydalanıcı çeyrek, duyarlı tamamen kapalı |

not: sektör sınıflandırması aktif kriz tipine göre belirlenir (bkz. TRADING_PLAYBOOK.md K-13 v4.1)
aktif kriz: jeopolitik/savaş (İran, şubat 2026). kriz tipi değişirse bu tablo güncellenmeli

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
| sabit %5 stop | chandelier exit: highest_high - 3×ATR(14) trailing stop |
| sabit %10 hedef | kâr kilidi sistemi: <%7 chandelier 3×ATR, %7-15 chandelier 2×ATR, %15+ chandelier 1.5×ATR. sabit hedef yok |
| RSI oversold giriş | ichimoku kumo kırılımı / kijun bounce giriş |
| MACD teyidi | gereksiz (TK cross kaldırıldı, tek başına anlamlı değildi) |
| SMA20/50 pozisyon kontrolü | ichimoku kumo bunu zaten yapıyor |
| SMA200 filtresi | SMA200 referans bilgi olarak korundu (zorunlu filtre değil) |
| sabit %5 trailing | chandelier exit (3×ATR) doğal trailing |
| 7-14 gün tutma süresi | chandelier stop tetiklenene kadar tut. süre sınırı yok ama K-08 zaman filtresi uygulanır |
| skor kartı (7 puan) | ichimoku 4/4 + SPY master switch + K-19/K-20 filtreleri |
| sabit lot | ATR bazlı risk hesaplı lot |

---

## 8. JSON ŞEMA DEĞİŞİKLİKLERİ

### aktif pozisyon (data/swing/active.json)

eski alanlar kaldırılan:
- ~~hedef_fiyat~~ → giriş fiyatı x 1.10 sabit hedef
- ~~trailing_yuzde~~ → chandelier exit (3×ATR)
- ~~zaman_cercevesi~~ → süre sınırı yok
- ~~partial_exit_plan~~ → chandelier + ichimoku çıkış sinyalleri

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
  "stop_loss": 33.96,
  "stop_tipi": "chandelier_3xATR",
  "highest_high": 37.56,
  "chandelier_stop": 33.96,
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
  "cikis_sinyali": "chandelier_stop",
  "stop_tipi_cikis": "chandelier_3xATR",
  "atr_giris": 1.20,
  "atr_cikis": 1.35,
  "highest_high": 41.20,
  "max_kar_zarar_yuzde": 9.70
}
```

---

## 9. TARAMA EVRENİ

### FMP screener bazlı dinamik evren

tarama evreni sabit liste değil, her seans içinde FMP API'den çekilir:

```
FMP company-screener parametreleri:
  marketCapMoreThan: 2000000000 ($2B+)
  volumeMoreThan: 500000 (günlük 500K+ hacim)
  priceMoreThan: 10 ($10+ fiyat)
  isEtf: false
  isFund: false
  isActivelyTrading: true
  country: US
  limit: 5000 (sektör başına kısıtlama yok)
```

bu filtrelerle ~1,100 hisse gelir. sektör dağılımı otomatik ve dengeli.

### neden sabit liste değil

- hisseler mcap, hacim, fiyat değişimine göre evrene girip çıkar
- sabit liste güncellenmeyi unutma riski taşır
- FMP screener her zaman güncel veri verir
- API limiti sorun değil (~1,100 çağrı / seans)

### tarama akışı (seans içi, manuel)

1. FMP screener → ~1,100 sembol çek
2. K-19 filtresi: XLP (consumer defensive) hisselerini çıkar
3. her sembol için FMP historical data çek (son 120 gün)
4. ichimoku 4/4 hesapla (kumo üstü + TK bull + tenkan üstü + volume 1.3x)
5. K-13 v4.1 sektör bazlı VIX kontrol:
   - sektör faydalanıcı + VIX <28: SPY > 21EMA + eğim ↗ (VIX<22 zorunlu, 22-28 önerilir) → K-20 → GİR tam
   - sektör faydalanıcı + VIX 28-35: yarım pozisyon, SPY kontrol yok
   - sektör duyarlı + VIX <22: SPY > 21EMA + eğim ↗ → K-20 → GİR tam
   - sektör duyarlı + VIX 22-28: SPY > 21EMA + eğim ↗ → K-20 → GİR yarım
   - sektör duyarlı + VIX 28-35: K-13b 6 koşul → GİR çeyrek (veya ATLA)
   - VIX 35+: faydalanıcı çeyrek, duyarlı ATLA
6. chandelier stop hesapla: giriş_fiyatı - 3×ATR(14)
7. min stop mesafesi ≥%5 kontrol

### K-19 dışlama listesi (consumer defensive)

XLP sektörüne dahil tüm hisseler otomatik dışlanır. FMP screener'dan sector="Consumer Defensive" olarak gelir.

---

## 10. GÜNLÜK İŞ AKIŞI

### seans öncesi / FAZ1
1. aktif swing pozisyonları için ichimoku seviyeleri + ATR güncelle
2. chandelier stop güncelle: highest_high yenilendi mi, ATR değişti mi → stop yeniden hesapla (sadece yukarı)
3. kumo yakınında mı kontrol et → çıkış uyarısı

### seans içi / FAZ2-FAZ3
4. stop tetiklendi mi → çık
5. swing tarama çalıştır: FMP screener → ichimoku 4/4 filtre → karar akışı
6. aday varsa: temel kontrol (K-18 insider, earnings tarihi) → giriş kararı

### seans sonrası
7. JSON güncelle, git push

---

## 11. NOTLAR

- NEM ve AROC v1 sisteminden v2'ye geçiş (mart 2026) tamamlanmış, her iki pozisyon da kapatılmıştır
- v1 skor kartı sistemi (7 puan, sabit %5/%10) artık kullanılmıyor
- v2.1'de TK cross giriş sinyali kaldırıldı, v2.2'de ABEF eklendi, v2.3'te ABEF kaldırılıp 4/4 zorunlu yapıldı, kijun trailing → chandelier exit (3×ATR)
- tarama evreni: sabit liste → FMP screener bazlı dinamik evren (v2.3, nisan 2026)

---

*finzora ai | swing sistemi v2.3 | 6 nisan 2026*
