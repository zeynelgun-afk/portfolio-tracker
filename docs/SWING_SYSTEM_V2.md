# SWING TRADE SİSTEMİ v2.2 — ICHİMOKU + HACİM + ATR + ÖN FİLTRE

> **versiyon**: 2.2
> **son güncelleme**: 2 nisan 2026
> **önceki sistem**: sabit %5 stop / %10 hedef / RSI+MACD+SMA skor kartı
> **neden değişti**: ichimoku kendi başına komple bir trend sistemi. sabit stop/hedef ile karıştırmak çelişki yaratıyordu. yeni sistem tamamen dinamik.
> **v2.1 değişiklik**: TK cross giriş sinyali kaldırıldı (sahte sinyaller), minimum %5 stop mesafesi zorunluluğu eklendi
> **v2.2 değişiklik**: VIX rejimine göre çift katmanlı ön filtre sistemi eklendi (A+B+E+F). 5 dönem backtesti ile doğrulandı (15/15 kazanan, 0 kayıp)

---

## FELSEFESİ

ichimoku kinko hyo zaten tek başına trend, momentum, destek ve direnç veriyor. ama iki eksiği var:

1. **hacim**: ichimoku tamamen fiyat bazlı. sinyalin arkasında gerçek alıcı/satıcı baskısı var mı bilmiyoruz. hacim teyidi sahte kırılımları filtreler
2. **ATR**: ichimoku dinamik seviyeler verir ama pozisyon boyutunu belirleyemiyor. ATR volatiliteyi ölçer, bununla risk bazlı lot hesaplarız

RSI ve MACD eklenmez. tenkan/kijun kesişimi zaten MACD'nin yaptığını yapıyor, chikou span momentum veriyor. üst üste yığmak karmaşıklık, çelişki ve analiz felci yaratır.

**SMA200 uzun vadeli filtre olarak eklenir.** ichimoku en uzun periyodu senkou span B (52 gün). bu, 200 günlük kurumsal trend perspektifini kapsamıyor. SMA200 tek başına uzun vadeli trend filtresi olarak çalışır:

- fiyat > SMA200 → uzun vadeli trend yukarı, giriş yapılabilir (normal akış)
- fiyat < SMA200 → uzun vadeli trend aşağı, sadece çok güçlü kumo kırılımı + hacim teyidi ile yarım pozisyon
- SMA20 ve SMA50 eklenmez, bunların rolünü tenkan (9) ve kijun (26) zaten yapıyor

---

## 0. ÖN FİLTRE SİSTEMİ (v2.2 — GİRİŞ ÖNCESİ ZORUNLU)

> **neden eklendi**: ichimoku 4/4 sinyal normal piyasada (VIX <22) tek başına %33 başarı gösterdi (kasım 2025, şubat 2026). A+B+E+F filtresi eklendikten sonra normal piyasada %100'e çıktı. kriz döneminde (VIX >25) ichimoku 4/4 zaten %100 çalıştığı için ek filtre gereksiz ve hatta zararlı (tüm kazananları engelliyor). bu yüzden çift katmanlı sistem: VIX rejimine göre farklı filtre.
>
> **backtest kanıtı (5 dönem, 27 hisse, 15 giriş)**:
> - mart 2025 (VIX ~30, tarife krizi): 0 giriş → doğru bloke, hiçbir şey çalışmadı
> - kasım 2025 (VIX ~21): A+B+E+F 2 giriş → 2 kazanan, AMZN -7.6% engellendi
> - şubat 2026 (VIX ~18): A+B+E+F 3 giriş → 3 kazanan (VZ, CAT, DVN), META/GOOGL engellendi
> - 9 mart 2026 (VIX ~30): K-13b 4/4 → 6/6 kazanan, A+B+E+F hepsini engellerdi
> - 20 mart 2026 (VIX ~27): K-13b 4/4 → 4/4 kazanan
> - **toplam: 15 giriş, 15 kazanan, 0 kayıp**

### karar akışı

```
ichimoku sinyali (3/4 veya 4/4)
        │
        ├── VIX <22 (normal/dikkatli)
        │     └── A+B+E+F filtresi uygula
        │           ├── 4/4 geçti → GİR (tam pozisyon)
        │           └── geçmedi → ATLA
        │
        ├── VIX 22-35 (gergin/kriz)
        │     └── ichimoku skoru 4/4 mü?
        │           ├── evet + K-13b koşulları sağlanıyor → GİR (yarım pozisyon)
        │           └── hayır (3/4 veya K-13b koşulları eksik) → ATLA
        │
        └── VIX >35 veya net sektör trendi yok → ATLA (hiç girme)
```

### A+B+E+F filtresi (VIX <22 ortamında zorunlu)

ichimoku sinyali aldıktan sonra, giriş öncesinde bu 4 koşulun **tümü** sağlanmalı:

| filtre | koşul | hesaplama | gerekçe |
|--------|-------|-----------|---------|
| **A** | 52 haftalık zirveye yakınlık | (fiyat - 52W high) / 52W high > -3% | düşüş trendindeki değil, yükseliş trendindeki hisseleri seçer |
| **B** | 5 günlük momentum | (fiyat - 5 gün önceki kapanış) / 5 gün önceki > +3% | son 1 haftada aktif alıcı baskısı olan hisseleri seçer |
| **E** | 20 günlük volatilite | std_dev(son 20 kapanış) / ortalama(son 20 kapanış) > 2.5% | yeterli hareket alanı olan hisseleri seçer, çok dar range'deki hisselerin kijun stop'u sıkı olur ve whipsaw ile tetiklenir |
| **F** | RSI(14) | RSI > 60 | momentum bölgesindeki hisseleri seçer. RSI <60 olan 4/4 sinyal volume spike'ının satış baskısından geldiğine işaret edebilir |

**ne zaman uygulanmaz**:
- VIX >22 ortamında A+B+E+F uygulanMAZ (kriz döneminde 52W ve Mom5 yapısal olarak farklı davranır, tüm kazananları engeller)
- bu durumda K-13b kuralları devreye girer (bkz. TRADING_PLAYBOOK.md K-13 v3)

### K-13b özet referans (VIX >25 ortamında)

VIX >25'te ichimoku 4/4 + volume teyit yeterli, A+B+E+F aranmaz. giriş koşulları (tümü zorunlu):
1. ichimoku skoru tam 4/4 (kumo üstü + TK bull + tenkan üstü + volume 1.3x+)
2. sektör ETF (XLK/XLE/XLI/XLC/XLV/XLF/XLP/XLY/XLU/XLB) hem 9SMA hem 21SMA üzerinde
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
| <20 | %1.0 | normal ortam |
| 20-25 | %0.75 | dikkatli |
| 25-30 | %0.50 | yarım risk |
| 30+ | %0.25 | minimum risk veya girme (K-13b istisnası: ichimoku 4/4 + ön filtre koşulları sağlanırsa %0.50) |

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
| sabit %10 hedef | ön filtreli girişlerde (A+B+E+F veya K-13b) sabit %10 hedef. filtresiz kumo kırılımlarında hedef yok, kijun trailing ile trend takip |
| RSI oversold giriş | ichimoku kumo kırılımı / kijun bounce giriş |
| MACD teyidi | gereksiz (TK cross kaldırıldı, tek başına anlamlı değildi) |
| SMA20/50 pozisyon kontrolü | ichimoku kumo bunu zaten yapıyor |
| SMA200 filtresi | SMA200 uzun vadeli trend filtresi olarak korundu |
| sabit %5 trailing | kijun-sen doğal trailing |
| 7-14 gün tutma süresi | süre sınırı yok, trend devam ettiği sürece tut |
| skor kartı (7 puan) | giriş sinyali var/yok + hacim teyidi |
| sabit lot | ATR bazlı risk hesaplı lot |

---

## 8. JSON ŞEMA DEĞİŞİKLİKLERİ

### aktif pozisyon (data/swing/active.json)

eski alanlar kaldırılan:
- ~~hedef_fiyat~~ → ön filtreli girişlerde (A+B+E+F / K-13b) giriş fiyatı × 1.10 sabit hedef. filtresiz girişlerde hedef yok, kijun trailing
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

## 10. MEVCUT POZİSYONLARA GEÇİŞ

NEM ve AROC v1 sistemiyle açıldı. geçiş:

**NEM**: eski stop $93.55 (sabit %5). yeni sistemde kijun $113.16, kumo alt $109.43. fiyat ($99.02) kumo'nun altında, kijun'un altında. ichimoku'ya göre bu pozisyon zaten "girme" sinyali veriyor. giriş tezi (altın rekor + RSI oversold) ichimoku dışı bir tezdi. yeni sistemde bu tür kontra-trend girişler yapılmaz. pozisyon v1 kurallarıyla yönetilmeye devam eder veya erken kapatılır.

**AROC**: eski stop $35.68 (sabit %5). yeni sistemde kijun $34.98. fiyat ($37.02) kumo üstünde, tenkan > kijun. ichimoku tam yükseliş sinyali. bu pozisyon yeni sisteme uyumlu. stop kijun $34.98'e güncellenir (eski $35.68'den daha geniş ama ichimoku bazlı).

---

*finzora ai | swing sistemi v2.2 | 2 nisan 2026*
