# TRADING PLAYBOOK — KANIT BAZLI KURALLAR

> **son güncelleme**: 18 mart 2026
> **amaç**: gerçek trade deneyimlerinden çıkarılan, tekrar ihlal edilmemesi gereken kurallar
> **güncelleme sıklığı**: her kapanış raporunda yeni dersler eklenir
> **referans**: sabah raporu ve seans promptu bu dosyayı okur

---

## 1. KANITLANMIŞ KURALLAR

her kural en az bir gerçek trade deneyimiyle doğrulanmıştır. kural numarası değişmez, yeniler sona eklenir.

### giriş kuralları

**K-01: büyük makro veri öncesi giriş yapma**
- kanıt: AMKR 5 mart gece alındı, 6 mart NFP -92K şoku → bir gecede -%6 zarar
- kural: NFP, CPI, FOMC gibi kritik verilerden önce yeni pozisyon açma. veri sonrası en az 1 seans bekle
- ihlal maliyeti: AMKR -%6.12

**K-02: kriz rallisinin ilk gününe girme**
- kanıt: 2 mart iran savaşı rallisi — KTOS, CEG, HAL, LASR, BKSY hepsi ilk gün alındı → 5/5 zararda kapandı. CEG -%5.0, HAL -%5.1, KTOS stop
- kural: en az 1 gün soğuma bekle, RSI teyidi al. ilk günün momentumunu kovalama, ikinci gün genellikle kâr realizasyonu gelir
- ihlal maliyeti: CEG -%5.0, HAL -%5.1

**K-03: VIX >25 ortamında micro/small cap swing girişi yapma**
- kanıt: ALMU (small cap, düşük likidite) VIX 24'te 10 mart'ta alındı → 2 günde -%6.1 stop. hacim ~79K, gap riski yüksek
- kural: VIX >25 iken market cap <$5B ve günlük hacim <500K olan hisselere swing girişi yapma
- ihlal maliyeti: ALMU -%6.1

**K-04: SMA teyidi olmadan pozisyon açma**
- kanıt: CRDO 10 mart'ta alındı, tüm SMA'ların altındaydı → hâlâ -%2.4 zararda. SOFI de SMA50'nin %20 altında tutuldu → -%3.6
- kural: en az SMA50 veya SMA200 üzerinde olmalı. ikisinin de altındaysa giriş yapma, teyit bekle
- ihlal maliyeti: CRDO -%2.4 (devam), SOFI -%3.6

**K-05: earnings öncesi swing pozisyondan çık**
- kanıt: NVDA swing 23 şubat'ta +%2.9 kârla earnings öncesi satıldı → doğru karar, NVDA sonra düştü
- kural: swing pozisyonda kazanç varken earnings riskine girme. 2+ gün önceden çıkış planla
- kazanç: NVDA +%2.9 korundu

### çıkış kuralları

**K-06: stop-loss override en fazla 1 kez yapılır**
- kanıt: LASR 3 kez override ($65→$62→$60). ilk stop $65'te çıkılsaydı zarar -%3.8 olacaktı → sonunda -%7.3 (ve hâlâ açık)
- kural: override yapılırsa bir kez tolerans, ikincisi kesinlikle yok. ilk override'dan sonra hisse toparlanmazsa çık
- ihlal maliyeti: LASR -%3.8 → -%7.3 (ek -%3.5 kayıp)

**K-07: izleyen zarar kes (trailing stop) disiplini bozma**
- kanıt: SHOP trailing stop $130.20'de tetiklendi → +%8 kâr korundu. BKSY trailing stop → +%18.5 kâr korundu. NEM trailing stop → +%2.1 kâr
- kural: trailing stop tetiklendiğinde SORGULAMA, direkt çık. çalışan sistem
- kazanç: SHOP +%8, BKSY +%18.5, NEM +%2.1

**K-08: momentum yoksa uzun tutma (sektör ayrışma filtresi ekli)**
- kanıt: RKLB 3 hafta sonra sıfır getiri (giriş $68.44, güncel $68.37). T swing 22 gün tutuldu → -%5.5. LMT 18 gün → +%1.4 ama çok uzun
- kural: 10 gün sonra momentum gelmemişse aşağıdaki filtre uygula:
  - sektör düşerken hisse düşmüyorsa (pozitif ayrışma / relative strength) → ek 5-7 gün tolerans ver. birikim sinyali olabilir
  - pozitif ayrışma + hacim artışı → güçlü sinyal, toleransı uzat
  - pozitif ayrışma yok veya negatif ayrışma (sektör düşerken hisse daha çok düşüyor) → derhal çık
  - düşük hacimde yatay tutunma → zayıf sinyal, tolerans verme
- mantık: sektör baskısına rağmen tutunma, altta sessiz birikim olduğunu gösterir. satıcılar tükenmiş, alıcılar fiyatı savunuyor demek. ama her yatay hareket birikim değil, hacim teyidi şart
- ihlal maliyeti: T -%5.5 (ayrışma yoktu, sektör de zayıftı), RKLB zaman maliyeti (sektör zayıflarken tutundu, ayrışma pozitif)
- güncelleme: 13 mart 2026. RKLB havacılık/savunma sektörü düşerken $68.37-68.44 bandında tutundu, pozitif ayrışma mevcut

**K-09: stop'a %2 kala erken çıkışı değerlendir**
- kanıt: AMKR stop'a $0.17 kala çıkıldı → doğru karar, hisse aynı gün daha da düştü. GE stop'a yaklaşınca kârla çıkıldı
- kural: stop'a %2 veya altı mesafe kaldığında, momentum yoksa bekleme, erken disiplinli çıkış yap

### portföy yönetimi kuralları

**K-10: savunmacı/temettü pozisyonlar risk-off günlerinde portföyü koruyor**
- kanıt: 12 mart SPY -%1.52 düştü ama PM +%3.09, CVX +%2.70, MO +%2.08 ile portföy korundu
- kural: her zaman portföyün en az %30'u savunmacı/temettü hisselerinde olsun

**K-11: RSI 70+ karda kısmi kâr al**
- kanıt: SM RSI 74'te %40 satıldı → ertesi gün -%4.38 düşüş geldi. KOS RSI 68'de satıldı → doğru zamanlama
- kural: RSI 70 üstü + %20 kârda → en az %25-33 kısmi kâr al. tüm pozisyonu tutma

**K-12: tek pozisyon ağırlığı %15'i geçmesin**
- kanıt: SM ağırlık %24'e çıkmıştı → kısmi satış zorunlu oldu. aşırı konsantrasyon riski
- kural: tek pozisyon ağırlık %15 üstüne çıkarsa kısmi satış planla

### ortam kuralları

**K-13: VIX >30 ortamında varsayılan yarım pozisyon**
- kanıt: VIX 31+ ortamında 9 mart'ta yapılan satışlar hep doğruydu. VIX yüksekken tam pozisyon riski katlanır
- kural: VIX >30 → yeni girişler varsayılan yarım pozisyon. VIX >25 → dikkatli, normal pozisyon. VIX <20 → rahat giriş

**K-14: swing performansı kötüleşiyorsa dur**
- kanıt: son 5 swing kapanıştan 4'ü zarar (T -%5.5, ALMU -%6.1, SOFI -%3.6, CEG -%5.0). toplam kayıp ciddi
- kural: ardışık 3+ zarar gelince dur, ortamı değerlendir. piyasa koşulları uygun değilse slot boş bırak
- durum: 12 mart itibarıyla swing'e ara verilmeli

---

## 2. HATA KAYDI

her hata tarih, ne olduğu, neden yanlış olduğu ve çıkarılan kuralla kaydedilir.

| tarih | hisse | hata | sonuç | çıkarılan kural |
|-------|-------|------|-------|-----------------|
| 2 mart | KTOS, CEG, HAL | kriz rallisi ilk gün girişi | 5/5 zarar | K-02 |
| 5 mart | AMKR | NFP öncesi gece alım | -%6.12 | K-01 |
| 5-9 mart | LASR | 3x stop override | -%3.8→-%7.3 | K-06 |
| 27 şubat | LMT | swing'de süre aşımı ertelemesi | +%1.4 ama 18 gün | K-08 |
| 10 mart | ALMU | VIX 24'te small cap swing | 2 günde -%6.1 | K-03 |
| 10 mart | CRDO | SMA altında giriş | -%2.4 devam | K-04 |
| 24 şub-12 mart | SOFI | momentum gelmeden 16 gün tutma | -%3.6 | K-08 |
| 13 mart | SM/XLE | RSI 70+ uyarısı, kısmi kâr zamanlaması | izlenmeli | K-11 |
| 17 mart | CRDO | SMA altında giriş, insider satış baskısı | -%8.77 stop | K-04 (2. kanıt) |
| 18 mart | RKLB | momentum hissesinde arz riski değerlendirilmedi | -%11.59 (pozisyon küçük) | K-15 (yeni) |
| 18 mart | MU | canavar beat ama AH sınırlı tepki | +%1.27 (beklenti altı) | K-16 (yeni gözlem) |
| 17 şub-11 mart | T | 22 gün tutma, savunmacı tez çalışmadı | -%5.5 | K-08 |

---

## 3. ÇALIŞAN STRATEJİLER

neyin iyi çalıştığını da kaydet — tekrar et.

| strateji | kanıt | sonuç |
|----------|-------|-------|
| trailing stop disiplini | SHOP +%8, BKSY +%18.5, NEM +%2.1, TYL +%11.2 | kâr koruması mükemmel |
| kademeli kâr alma (RSI 70+) | SM %40 satış RSI 74, KOS parçalı ~+%65 | zamanlaması ideal |
| earnings öncesi çıkış | NVDA +%2.9 korundu | risk yönetimi doğru |
| savunmacı/temettü ağırlık | risk-off günlerinde portföy koruması | PM, CVX, MO sürekli güç |
| enerji/emtia rotasyonu | KOS +%65, SM +%23, CVX +%28 | savaş/kriz döneminde enerji kazandırır |
| erken disiplinli çıkış (stop yakın) | AMKR, GE | daha büyük zarardan korudu |
| kriz ortamında sağlık diversifikasyonu | JNJ eklendi, portföy dengesi | risk-off koruması güçleniyor |
| AI tedarik zinciri katalizör pozisyonlama | GTC 2026: MRVL +%4.2, RKLB +%4.2, COHR +%1.9, GLW +%2.3, ANET +%1.3 tek günde | katalizör öncesi yarim pozisyon, doğrulanınca artır stratejisi çalışıyor |

---

## 4. SEKTÖR GÖZLEMLERİ

piyasa ortamına göre hangi sektör nasıl davranıyor.

### risk-off / VIX >25 ortamı (şu an)
- **güçlü**: temel tüketim (MO, PM), utilities (DUK), enerji (CVX, XOM), temel malzeme (RGLD)
- **zayıf**: tech büyüme, endüstriyel (XLI), small cap (IWM), fintech (SOFI)
- **sonuç**: savunmacı rotasyonda tütün ve enerji portföyü koruyor

### savaş/kriz ortamı (iran krizi şubat-mart 2026)
- **güçlü**: enerji (KOS, SM, CVX, XOM), savunma (PLTR, RTX), altın (RGLD)
- **zayıf**: tech, döngüsel tüketim, endüstriyel
- **dikkat**: kriz rallileri kısa ömürlü (K-02), ilk gün girme

### nvidia "sell the news" etkisi
- kanıt: NVDA 26 şubat beat etti ama -%5 düştü. "mükemmel fiyatlanmış" hissede beat tek başına yetmiyor
- kural: consensus beklentisi çok yüksek olan mega cap'lerde earnings beat → sell the news riski

### altın rekor ama royalty hisseleri düşüyor (16 mart 2026)

### MU canavar kazanç ama AH sınırlı (18 mart 2026)
- gözlem: MU EPS +%31, gelir +%19, Q3 rehber +%38 sürpriz. AH sadece +%1.27. hisse kazanç öncesi 3 günde +%10 rally yapmıştı
- çıkarım: beklenti çok yüksek olan mega cap'lerde beat fiyatlanmış olabilir. bellek tedarik zinciri tezi doğrulandı ama hisse tepkisi zamanlamaya bağlı
- portföy etkisi: CRDO, MRVL, COHR, ANET için uzun vadeli pozitif ama kısa vadede "sell the news" riski
- gözlem: GCUSD $5,016 rekor ama RGLD -%8.79, RSI 34.8, SMA20 ve SMA50 altında
- olası nedenler: royalty modeli petrol/maden şirketleriyle farklı korelasyon gösteriyor, altın ETF (GLD) tercih ediliyor olabilir, sektör rotasyonu royalty modelinden uzaklaşıyor
- sonuç: altın yükseliyor diye royalty hissesi de yükselecek varsayımı hatalı olabilir. korelasyon bozulmasını izle, tez bozulursa çık

---

## 5. SWING TRADE İSTATİSTİKLERİ

### genel (17 şubat - 12 mart 2026)

| metrik | değer |
|--------|-------|
| toplam trade | 17 |
| kazanç | 10 (%58.8) |
| zarar | 7 (%41.2) |
| ortalama kazanç | +%4.13 |
| ortalama zarar | -%4.61 |
| en iyi | CAT +%12.0 (7 gün) |
| en kötü | ALMU -%6.1 (2 gün) |
| ortalama tutma (kazanç) | 10.4 gün |
| ortalama tutma (zarar) | 11.5 gün |

### yöntem bazlı
- **trailing stop çıkış**: 4/4 kârlı (SHOP, BKSY, NEM, TYL) — en güvenilir çıkış yöntemi
- **kriz rallisi girişi**: 0/5 başarılı — kesinlikle kaçınılmalı (K-02)
- **RSI oversold bounce**: karışık — teyit beklemek şart
- **breakout**: karışık — VIX yüksekken breakout güvenilmez

### son trend (mart 2026)
- son 5 kapanıştan 4'ü zarar → **ortam uygun değil, swing'e ara ver** (K-14)
- 16 mart itibarıyla 3 aktif pozisyon (DUK, DVA, RTX). DUK hedefe yakın, RTX yeni giriş
- genel: 10K/7Z (%58.8 win rate), ort kazanç +%4.13, ort kayıp -%4.61

---

## 6. GÜNCELLEME KURALLARI

1. her kapanış raporunda "dersler" bölümünden bu dosyaya yeni kural/hata eklenir
2. kural numaraları (K-XX) sabit kalır, yeniler sona eklenir
3. istatistikler her haftalık raporda güncellenir
4. sektör gözlemleri ortam değiştikçe güncellenir
5. sabah raporu ve seans promptu bu dosyayı referans alır — karar vermeden önce ilgili kuralı kontrol et

---

*finzora ai | son güncelleme: 18 mart 2026*

**K-15: aşırı satım bölgesinde (RSI <35) yeni alım yaparken dikkatli ol**
- kanıt: XLI RSI 34.5, 3 haftadır düşüşte. JNJ RSI 53'te alındı ama girişte SMA20 altındaydı. endüstriyel ve sağlık sektörleri savaş ortamında sürekli baskı altında
- kural: RSI <35 bölgesinde alım yapmadan önce en az 1 gün teyit bekle (gün içi dip test + toparlanma sinyali). düşen bıçağı tutma
- ilişkili: K-04 (SMA teyidi olmadan giriş yapma)

**K-15 (yeni): momentum hisselerinde hisse arzı (dilüsyon) riskini önceden değerlendir**
- kanıt: RKLB 18 mart'ta $1B hisse arzı açıkladı → -11.59% tek günde. bir gün önceki +%8 rallisini tamamen sildi
- kural: yüksek borç, negatif FCF veya büyük CapEx planları olan momentum hisselerinde hisse arzı riski mevcut. pozisyon büyütmeden önce şirketin sermaye ihtiyacını değerlendir. küçük pozisyon (%1 ağırlık) bu riski sınırlandırır
- ihlal maliyeti: RKLB -%11.59 (portföy etkisi sınırlı, %0.95 ağırlık sayesinde)

**K-16 (yeni): canavar kazanç bile "sell the news" tetikleyebilir**
- kanıt: MU 18 mart AMC devasa beat (EPS +%31, gelir +%19, rehber +%38 sürpriz) ama AH sadece +%1.27. hisse kazanç öncesi 3 günde +%10 rally yapmıştı
- kural: consensus beklentisi çok yüksek ve hisse kazanç öncesi büyük ralli yapmışsa, beat tek başına sert yukarı hareket getirmeyebilir. pozisyon girişinde zamanlama kazanç öncesi ralliden sonraya değil, geri çekilmeye bırak
- ilişkili: NVDA sell the news gözlemi (sektör gözlemleri bölümü)

**K-04 ek kanıt: CRDO 17 mart 2026**
- kanıt: CRDO 10 mart'ta $114.28'den alındı, tüm SMA'ların altındaydı (SMA50: $125.88, SMA200: $128.84). 17 mart'ta -%10.8 günlük düşüşle $104.26'da stop-loss ($108) tetiklendi. zarar: -%8.77
- ek faktörler: insider satışları yoğun (365 satış / 0 alış son 6 ayda), gross margin guidance compression (68.6%→64-66%), rosenblatt nötr notu
- sonuç: K-04 kuralı ikinci kez doğrulandı. SMA teyidi olmadan giriş = yüksek zarar riski. ilk kanıt SOFI -%3.6, ikinci kanıt CRDO -%8.77

**K-16 ek gözlem: sell the news hisseye özgü, sektöre yayılmayabilir (19 mart 2026)**
- kanıt: MU 18 mart'ta devasa beat etti (EPS +%31) ama kendi hissesi -%3.8 düştü (sell the news). ancak 19 mart'ta tedarik zinciri ortakları tam tersi tepki verdi: CRDO +%5.28, MRVL +%2.18, COHR +%7.14, GILT +%4.35
- çıkarım: sell the news etkisi o hisseye özgü kalabilir. tedarik zinciri ortakları temel verilere odaklanarak ralli yapabilir. "sempati baskısı" varsayımı her zaman doğru değil

**RGLD altın korelasyon bozulması ek kanıt (19 mart 2026)**
- kanıt: altın -%5 düştü, RGLD -%7.20 düştü (negatif beta, altından daha sert). RSI 27.9, 3 SMA altında, -%17.98 zararda
- sonuç: royalty modeli altınla asimetrik korelasyon gösteriyor -- yukarı sınırlı, aşağı sert. tez bozulma sınırı -%20 (RGLD $217 civarı)
- ilişkili: playbook sektör gözlemleri "altın yükseliyor diye royalty yükselecek varsayımı hatalı" notu

---

## 3. SWING TRADE TEKNİK GİRİŞ SİSTEMİ (K-17)

> ekleme: 24 mart 2026
> kanıt: NEM swing girişi (24 mart). RSI 31 + fundamental güçlü ama ichimoku 0/3, tüm SMA altında, MACD negatif. toplam skor 1.2/7 (%18). düşen bıçak riski.
> araç: scripts/swing_technical.py

### kural

swing trade girişlerinde temel analiz aday havuzunu oluşturur, teknik analiz giriş zamanlamasını belirler. **minimum %50 teknik skor** (3.5/7) gerekli.

### puanlama sistemi (7 puan üzerinden)

**ichimoku bulutu (3 puan)**
1. fiyat vs kumo: fiyat > kumo (+1), kumo icinde (+0.5), kumo altında (0)
2. tenkan-kijun kesisimi: tenkan > kijun (+1), yaklaşıyor (+0.5), tenkan < kijun (0)
3. chikou span: mevcut fiyat > 26 gün önceki fiyat (+1), altında (0)

**klasik göstergeler (4 puan)**
4. RSI donuş teyidi (+1): 30 altından 30 üzerine çıkış veya yükselen RSI trendi (+0.5)
5. MACD: bullish cross (+1), histogram yükseliyor (+0.5), toparlanma başlıyor (+0.25)
6. SMA pozisyonu: fiyat > SMA20 (+0.5) + fiyat > SMA50 (+0.5)
7. hacim: 1.5x ortalama + pozitif gün (+1), 1.2x + pozitif (+0.5)

### karar eşikleri

| skor | yüzde | karar |
|------|-------|-------|
| 5.0+ | %70+ | giris uygun |
| 3.5-4.9 | %50-69 | dikkatli giris (yakin izle, yarim pozisyon) |
| 2.0-3.4 | %28-49 | erken, bekle (donus teyidi yok) |
| 0-1.9 | %0-27 | girme (trend dusus) |

### özel durumlar

- ichimoku 0/3 = giris yapma, diger skor ne olursa olsun (trend kesinlikle dusus)
- ichimoku 3/3 + RSI > 70 = asiri alim, geri cekilme bekle
- VIX > 25 ise %70+ skor bile olsa yarim pozisyonla gir (K-13)
- fundamental cok guclu ama teknik zayifsa → watchlist'te tut, teknik donus bekle

### kullanim

```bash
python scripts/swing_technical.py NEM,ONTO,AROC     # belirli hisseler
python scripts/swing_technical.py --watchlist         # tum watchlist
```

her seans oncesi ve swing giris karari oncesi bu scripti calistir.

---

*finzora ai | son güncelleme: 24 mart 2026*
