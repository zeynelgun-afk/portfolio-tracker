# TRADING PLAYBOOK — KANIT BAZLI KURALLAR

> **son güncelleme**: 2 nisan 2026
> **amaç**: gerçek trade deneyimlerinden çıkarılan, tekrar ihlal edilmemesi gereken kurallar
> **güncelleme sıklığı**: her kapanış raporunda yeni dersler eklenir
> **referans**: sabah raporu ve seans promptu bu dosyayı okur

---

## 1. KANITLANMIŞ KURALLAR

her kural en az bir gerçek trade deneyimiyle doğrulanmıştır. kural numarası değişmez, yeniler sona eklenir.

### giriş kuralları

**K-01: büyük makro veri öncesi giriş yapma (v2 — 1 nisan 2026)**
- kanıt: AMKR 5 mart gece alındı, 6 mart NFP -92K şoku → bir gecede -%6 zarar
- araştırma: quantifiedstrategies backtestleri makro veri etrafında tutarlı edge bulamadı. NFP/CPI ilk spike'ı genellikle tuzak, profesyoneller ilk tepkiyi fade ediyor. veri öncesi likidite düşer, spreadler genişler
- kural (genişletildi):
  - NFP, CPI, FOMC, GDP verilerinden 24 saat önce yeni swing pozisyon açma
  - mevcut pozisyonlarda: kazanç açıklaması+makro veri aynı haftada çakışıyorsa pozisyon boyutunu %50 küçült
  - veri sonrası: ilk 30 dakika tepki genellikle aşırı. en az 1 saat (tercihen 1 seans) bekle, trendin yönünü teyit et
  - pozisyon trade/LEAPS: makro veri genellikle kısa vadeli gürültü, pozisyonu tut ama yeni ekleme yapma
- istisna: eğer veri beklentiyle uyumluysa (sürpriz yok) ve mevcut trend güçlüyse, mevcut pozisyonlara dokunma
- ihlal maliyeti: AMKR -%6.12

**K-02: kriz rallisinin ilk gününe girme (v2 — 1 nisan 2026)**
- kanıt: 2 mart iran savaşı rallisi — KTOS, CEG, HAL, LASR, BKSY hepsi ilk gün alındı → 5/5 zararda. 25 mart POWL/CAMT/VRT aynı hata → -%8 ile -%10 kayıp
- araştırma: LPL research 2. dünya savaşından bu yana jeopolitik şokları inceledi → S&P 500 ortalama -%5 düşüş, genellikle 3 haftada dip bulunur, 1-2 ayda toparlanır. ilk gün tepkisi genellikle aşırı, ertesi gün düzeltme gelir. enerji bağlantılı çatışmalarda ilk spike sonra reverse eğilimi güçlü
- kural (genişletildi):
  - kriz/savaş/jeopolitik olayda ilk günün rallisine/satışına girme
  - en az 2 tam işlem günü bekle (1 değil 2 — çünkü 2. gün de genellikle volatil)
  - giriş teyitleri: RSI 50 üzeri stabilizasyon + hacim normalleşmesi + VIX zirve yapıp geri çekilme başlaması
  - sektör bazlı: enerji/savunma kriz rallileri genellikle kısa ömürlü. kalıcı tedarik kesintisi kanıtlanana kadar tam pozisyon açma
  - dip alım stratejisi: kriz dip alımı yapmak istiyorsan, 3 hafta sonrası hedefle (tarihsel dip zamanlaması). kademeli giriş: %33 ilk giriş → %33 teyit sonrası → %34 trend doğrulanınca
- ihlal maliyeti: 2 mart 5/5 zarar, 25 mart 3/3 zarar

**K-03: VIX bazlı pozisyon boyutlandırma matrisi (v2 — 1 nisan 2026)**
- kanıt: ALMU (small cap, düşük likidite) VIX 24'te 10 mart'ta alındı → 2 günde -%6.1 stop. AROC VIX 27+'da swing girişi → -%4.95
- araştırma: kurumsal masalarda VIX eşik sistemi standart: düşük VIX=normal risk, orta=yarım, yüksek=sadece A-kalite veya dur. ATR bazlı pozisyon boyutlandırma oynaklıkla ters orantılı olmalı. small cap'ler jeopolitik streste large cap'lerden çok daha sert düşer (springer araştırması)
- kural (matris):
  VIX <18: tam pozisyon, tüm cap seviyeleri uygun
  VIX 18-25: normal pozisyon, micro/small cap dikkatli (mcap <$2B + hacim <300K → girme)
  VIX 25-30: yarım pozisyon, sadece large cap ($10B+) swing girişi. small/mid cap yeni giriş yok
  VIX 30-35: çeyrek pozisyon veya sadece A-kalite kurulum. yeni swing girişi yok, mevcut pozisyonlarda trailing stop sıkılaştır. (istisna: K-13b ichimoku 4/4 koşulları sağlanırsa yarım pozisyon izni — bkz. K-13 v3)
  VIX >35: tüm yeni girişleri durdur, sadece mevcut pozisyon yönetimi. dip alım için nakit biriktir. (istisna: K-13b sağlanırsa çeyrek pozisyon izni)
- pozisyon boyutu formülü: standart pozisyon × (20 / mevcut VIX). örnek: VIX 30'da standart $10K pozisyon → $10K × (20/30) = $6.7K
- ihlal maliyeti: ALMU -%6.1, AROC -%4.95

**K-04: trend teyidi olmadan pozisyon açma (v2 — 1 nisan 2026)**
- kanıt: CRDO 10 mart'ta alındı, tüm SMA'ların altındaydı → -%8.77 stop. SOFI SMA50'nin %20 altında → -%3.6. CRDO 2. deneme 17 mart → yine -%8.77
- araştırma: 200 günlük SMA trend filtresi olarak kullanıldığında backtest performansı %15-25 iyileşir. SMA200 üstü trend güçlü, altı zayıf. ichimoku kumo da eşdeğer trend filtresi
- kural (katmanlı):
  katman A (en güçlü giriş): fiyat SMA50 + SMA200 üstünde + ichimoku kumo üstünde → tam pozisyon
  katman B (normal giriş): fiyat SMA200 üstünde ama SMA50 altında → SMA50'yi yukarı kırılma bekleniyor, yarım pozisyonla gir
  katman C (riskli — genellikle kaçın): fiyat SMA200 altında → yalnızca güçlü katalizörle (kazanç sürprizi, sektör rotasyonu) ve çeyrek pozisyonla gir
  katman D (yasak): fiyat hem SMA50 hem SMA200 altında + ichimoku kumo altında → kesinlikle girme, düşen bıçağı tutma
- ek filtre: insider satışı yoğunsa (K-18) + SMA altındaysa → çifte kırmızı bayrak, kesinlikle giriş yok
- ihlal maliyeti: CRDO -%8.77 (2 kez), SOFI -%3.6

**K-05: kazanç açıklaması risk yönetimi (v2 — 1 nisan 2026)**
- kanıt: NVDA swing 23 şubat'ta +%2.9 kârla earnings öncesi satıldı → doğru karar, NVDA sonra düştü. MU canavar beat ama +%1.27 sınırlı tepki (K-16)
- araştırma: kazanç açıklamaları yıllık fiyat hareketinin %30-70'ini oluşturur. IV crush etkisi opsiyon pozisyonlarını sert vurur. post-earnings gap trade en etkili ilk 30 dakikada ve gap %3+'teyken. kazanç sezonu risk yönetimi: pozisyon boyutunu %1-2'ye düşür, toplam portföy maruziyetini %15 ile sınırla
- kural (pozisyon tipine göre):
  swing trade: kazanç açıklamasından 2+ gün önce çık (kârda veya zararda). açıklama riskine maruz kalma
  pozisyon trade (portföy hissesi): pozisyonda kal ama şunları yap:
  a) mevcut kâr %15+ ise → kazanç öncesi %25 kısmi kâr al (riski küçült)
  b) mevcut kâr %5 altı veya zararda ise → tam pozisyon tut, stop sıkılaştır (2×ATR yerine 1.5×ATR)
  c) hisse kazanç öncesi 5 günde %10+ ralli yaptıysa → "sell the news" riski yüksek (K-16), kısmi çıkış yap
  LEAPS opsiyon: vade 6+ ay ise tut (zaman değeri yeterli). vade 3 ay altıysa ve kârdaysan → kısmi çık (IV crush LEAPS'i de etkiler)
  post-earnings giriş: açıklama sonrası giriş açıklamadan öncekinden daha sürdürülebilir. ilk gün tepkisini bekle, 2. gün trigger candle ile gir
- kazanç: NVDA +%2.9 korundu

### çıkış kuralları

**K-06: stop-loss override protokolü (v2 — 1 nisan 2026)**
- kanıt: LASR 3 kez override ($65→$62→$60). ilk stop $65'te çıkılsaydı zarar -%3.8 → sonunda -%7.3. RTX -%5.16 stop tetiklendi, K-06'ya uyuldu → kontrollü zarar
- araştırma: sabit yüzde stop volatiliteyi hesaba katmaz, ATR bazlı stop daha etkili. stop'lar disiplin aracı ama kesinlik aracı değil (schwab). volatil hisselerde dar stop whipsaw yaratır. gap riski stop'u geçersiz kılabilir, bu yüzden pozisyon boyutlandırma asıl koruma
- kural (kesinleştirildi):
  - stop tetiklendiğinde ÇIKIŞ. tartışma yok, sorgulama yok
  - override istisnası (sadece 1 kez, şu koşulların TÜMÜ sağlanmalı):
    a) hisse teknik destek seviyesinde (SMA200, önemli pivot, kumo desteği)
    b) piyasa geneli düşük (SPY -%2+ gün) ve hisse nispeten dirençli (pozitif ayrışma)
    c) orijinal tez hala geçerli (katalizör bozulmamış)
    d) override sonrası yeni stop en fazla %2 daha aşağıda (orijinal stop'un %2 altı)
  - 3 koşuldan biri bile sağlanmazsa → override yok, direkt çık
  - override sonrası 3 iş günü içinde toparlanma yoksa → kesin çıkış, 2. override yok
- ATR bazlı stop önerisi: sabit %5 yerine 2×ATR(14) kullan. hisse volatilitesine göre otomatik ayarlanır
- ihlal maliyeti: LASR -%3.8 → -%7.3 (ek -%3.5 kayıp)

**K-07: izleyen zarar kes (trailing stop) disiplini (v2 — 1 nisan 2026)**
- kanıt: SHOP +%8, BKSY +%18.5, NEM +%2.1, TYL +%11.2 — hepsi trailing stop ile korundu. %100 başarı oranı
- araştırma: ATR bazlı trailing stop volatiliteye adapte olur, sabit yüzde trailing'den üstündür. kısa vadeli trend: 20SMA veya 2×ATR trail. orta vadeli: 50SMA veya 3×ATR trail. trailing çok sıkıysa normal geri çekilmelerde çıkarsın, çok gevşekse kârın büyük kısmını geri verirsin. ideal trailing: son swing düşük/yüksek seviyesi
- kural (yöntem bazlı trailing seçimi):
  swing trade: kijun-sen trailing VEYA 2×ATR(14) — hangisi daha geniş
  pozisyon trade: 20SMA altı günlük kapanış VEYA 50SMA altı haftalık kapanış
  momentum trade: 10EMA altı kapanış (daha sıkı, hızlı çıkış)
  - trailing tetiklendiğinde SORGULAMA, direkt çık. bu kural ASLA bozulmaz
  - çıkış sonrası: hisse toparlanırsa ve yeni sinyal verirse tekrar girilebilir (yeni trade olarak)
  - trailing'i sıkılaştırma zamanı: VIX yükselirken, kazanç açıklaması yaklaşırken, sektör zayıflarken
- kazanç: SHOP +%8, BKSY +%18.5, NEM +%2.1, TYL +%11.2 — portföydeki en güvenilir strateji

**K-08: zaman bazlı çıkış + sektör ayrışma filtresi (v2 — 1 nisan 2026)**
- kanıt: T 22 gün tutma → -%5.5. LMT 18 gün → +%1.4 (zaman maliyeti yüksek). RKLB 3 hafta yatay → sıfır getiri
- araştırma: swing trade'de en karlı işlemler genellikle ilk 5-7 günde hareket eder. 10+ gün momentum gelmezse fırsat maliyeti artar. sektör ayrışması (relative strength) birikim sinyali olabilir ama hacim teyidi şart
- kural (3 aşamalı zaman filtresi):
  gün 1-7: normal izleme, teze sadık kal
  gün 8-10: momentum kontrolü — fiyat giriş fiyatından %3+ yukarı mı? hacim artıyor mu? cevap evet → devam et. cevap hayır → ayrışma filtresi uygula:
    - pozitif ayrışma + hacim artışı → ek 5 gün tolerans
    - pozitif ayrışma ama düşük hacim → max 3 gün daha, sonra çık
    - ayrışma yok veya negatif → derhal çık
  gün 15+: kazanç açıklaması yaklaşmıyorsa veya güçlü katalizör yoksa → çık. zaman maliyeti çok yüksek. sermayeyi daha iyi fırsata aktar
  - ichimoku entegrasyonu: kijun-sen düz ve fiyat kijun etrafında sıkışıyorsa → momentum yok sinyali. kumo daraldıysa → yakında büyük hareket gelecek, sabret. kumo genişliyor + trend belirsiz → çık
- istisna: agresif portföy pozisyon trade'lerinde bu zaman sınırı uygulanmaz (tez bazlı çıkış)
- ihlal maliyeti: T -%5.5, LMT zaman maliyeti

**K-09: stop yakınlığı erken çıkış protokolü (v2 — 1 nisan 2026)**
- kanıt: AMKR stop'a $0.17 kala çıkıldı → doğru karar, hisse daha düştü. GE stop yakınında kârla çıkıldı
- araştırma: stop seviyelerinin etrafında likidite avcılığı (stop hunting) yaygın. fiyat stop'a çok yaklaşıp geri dönebilir. ama momentum kaybı + stop yakınlığı birleştiğinde erken çıkış genellikle doğru
- kural (karar ağacı):
  fiyat stop'a %2 veya altı mesafede mi? → evet ise şu kontrolleri yap:
  1) RSI yönü: RSI düşüyor + 40 altında → momentum yok, erken çık
  2) hacim: satış hacmi alış hacminden yüksek → baskı devam ediyor, erken çık
  3) piyasa geneli: SPY o gün negatif + VIX yükseliyor → ortam kötü, erken çık
  4) sektör: ilgili sektör ETF'si düşüyor → sektörel baskı, erken çık
  - 4 kontolden 3+ negatifse → stop beklemeden çık
  - 4 kontrolden 2 negatif, 2 nötr/pozitif → stop'u bekle (destek tutabilir)
  - stop yakınında ama hisse toparlanma sinyali veriyorsa (hammer mum, hacim artışı) → stop'u tut
- telegram alert: stop'a %2 kala otomatik alert gönder (--type alert)

### portföy yönetimi kuralları

**K-10: savunmacı/temettü allokasyon kuralı (v2 — 1 nisan 2026)**
- kanıt: 12 mart SPY -%1.52 ama PM +%3.09, CVX +%2.70, MO +%2.08 → portföy korundu. iran krizi süresince enerji sektörü +%12.5 (mart 2026)
- araştırma: goldman sachs önerisi: %33 inovasyon, %33 enflasyon koruması, %33 güvenli liman. jeopolitik streste large cap'ler small cap'lerden iyi performans gösterir. altın ve emtia enflasyon koruması sağlar
- kural (VIX bazlı dinamik allokasyon):
  VIX <18 (sakin piyasa): min %20 savunmacı/temettü (düşük koruma yeterli)
  VIX 18-25 (normal): min %30 savunmacı/temettü (mevcut kural)
  VIX 25-30 (gergin): min %40 savunmacı/temettü, agresif pozisyonları küçült
  VIX >30 (kriz): min %50 savunmacı/temettü, agresif'te sadece mevcut pozisyonları yönet
  - savunmacı tanımı: temettü yield >%2.5, beta <1.0, veya utilities/tüketim/sağlık sektörü
  - enerji: çatışma dönemlerinde savunmacıdan çok saldırgana dönüşür, ayrı değerlendir
  - dengeli portföy doğası gereği savunmacı ağırlıklı, agresif portföyde bu oran düşük olabilir ama toplam portföyde min %30 korunmalı

**K-11: kademeli kâr alma sistemi (v2 — 1 nisan 2026 güncelleme)**
- **kapsam**: sadece portföy pozisyonları (dengeli/agresif/temettü). swing trade'lerde uygulanmaz, swing sabit %10 hedef kullanır
- eski kural: RSI 70+ ve %20+ kâr → %25-33 kısmi sat. sorun: güçlü trendlerde kazananlar erken kesiliyordu
- araştırma bulgusu: güçlü yükseliş trendlerinde RSI 70+ uzun süre kalabilir, fiyat yükselmeye devam edebilir. RSI 70 otomatik satış sinyali DEĞİL, güçlü momentumu teyit eder. yükseliş trendinde RSI 40-80+ aralığında hareket eder (investtech, stockcharts araştırması)
- kanıt: SM RSI 74'te %40 satıldı → ertesi gün -%4.38 düşüş geldi (doğru). KOS parçalı satış → ideal zamanlama. ama trend devam eden hisselerde erken çıkış kâr kaçırır

- yeni kural — 3 katmanlı çıkış:

  katman 1 — UYARI (izle, henüz satma):
  RSI 70+ ve %15+ kâr → pozisyonu sıkı izlemeye al. izleyen zarar kes (trailing stop) aktif et: 2×ATR(14) veya 20SMA altı kapanış (hangisi daha geniş). henüz satış yok, sadece koruma

  katman 2 — KISMİ KÂR AL (tetikleyici gerekli):
  aşağıdakilerden BİRİ gerçekleşirse pozisyonun %25-30'unu sat:
  a) RSI ayı uyumsuzluğu (bearish divergence): fiyat yeni zirve yapar ama RSI yapmaz
  b) RSI 75+ ve sonra 70 altına düşer (momentum kırılması)
  c) fiyat 20SMA altına kapanır
  d) RSI 80+ (aşırı gerilim, uyumsuzluk aramadan kısmi çık)

  katman 3 — KALAN POZİSYON YÖNETİMİ:
  kalan %70-75 pozisyon izleyen zarar kesle devam eder:
  - pozisyon trade: 50SMA altı kapanış veya 3×ATR(14)
  trend devam ettiği sürece tut, izleyen stop tetiklenene kadar çıkma

- istisnalar:
  - kazanç açıklaması (earnings) yaklaşıyorsa (5 gün içinde): katman 2'yi RSI 70+'ta uygula, açıklama riskini alma
  - VIX >28 ortamında: katman 2'yi RSI 72+'ta uygula (daha erken çık)
  - LEAPS opsiyonlarda: zaman değeri avantajı var, katman 2 eşiğini RSI 80+ yap

- amaç: kazananları erken kesme hatasını önle, ama kontrolsüz de bırakma. "kazananı büyüt" felsefesini disiplinle uygula

**K-12: pozisyon konsantrasyon limitleri (v2 — 1 nisan 2026)**
- kanıt: SM ağırlık %24'e çıkmıştı → kısmi satış zorunlu oldu. IBKR portföyde NVDA (hisse+call) toplam %19.4 ağırlık → yoğunluk riski
- araştırma: kurumsal risk yönetiminde tek pozisyon limiti genellikle %5-10. bireysel yatırımcıda %15 makul üst sınır. tematik yoğunluk (aynı sektör/tema) toplam %40'ı geçmemeli. LEAPS opsiyonlar delta-ayarlanmış ağırlıkla hesaplanmalı
- kural (katmanlı limitler):
  tek hisse pozisyonu: max %15 portföy ağırlığı
  tek hisse + opsiyonları toplam: max %20 (NVDA hisse + NVDA call birlikte hesaplanır)
  tek sektör/tema: max %40 (örn: tüm AI/yarıiletken pozisyonları toplam)
  LEAPS hesaplama: kontrat değeri × delta = efektif maruziyet. 6 MU call × $87.93 × 100 × 0.55 delta = ~$29K efektif maruziyet
  - %15 aşılırsa: otomatik olarak kısmi satış planla (1 hafta içinde dengeleme)
  - %20 aşılırsa (hisse+opsiyon): aynı gün veya ertesi gün kısmi satış yap
  - sektör %40 aşılırsa: en zayıf pozisyonu küçült veya kapat
- haftalık kontrol: her pazar portföy ağırlıklarını kontrol et, dengeyi sağla

### ortam kuralları

**K-13: VIX rejim bazlı risk yönetimi (v3 — 2 nisan 2026)**
- kanıt v2: VIX 31+ ortamında 9 mart haber bazlı satışlar doğruydu (5/5 zarar). VIX 27+ AROC swing girişi → -%4.95
- kanıt v3 (backtest 2 nisan 2026): 9 mart VIX ~30 ortamında ichimoku 4/4 sinyalleri 6/6 kazandı (VLO +10% 3 günde, OXY +10% 9 günde, MPC +12.6%, DVN +11.2%, COP +9.7%, FANG +6.5%). aynı gün 3/4 sinyal savunma hisseleri 2/2 stop yedi (NOC -3.1%, LMT -3.1%). volume teyidi (4. sinyal) kazananları kaybedenlerden ayıran kritik filtre. 20 mart VIX ~27 ortamında ichimoku 4/4 HAL +10% 5 günde. K-13 bu fırsatları tamamen engelledi ama haber bazlı kötü girişleri de engelledi
- araştırma: VIX kurumsal masalarda rejim göstergesi olarak kullanılır. VIX >30'da ATR genişler, stop'lar daha sık tetiklenir. profesyoneller VIX eşik sistemi ile pozisyon boyutunu otomatik ayarlar. ancak sistematik sinyal (ichimoku 4/4 + volume) haber bazlı impulsif girişten temelden farklıdır: backtest'te 4/4 sinyaller VIX rejiminden bağımsız çalıştı
- kural (K-03 ile entegre — VIX rejim matrisi):
  VIX <18 — SAKİN: tam pozisyon, tüm stratejiler aktif, swing agresif olabilir
  VIX 18-22 — NORMAL: normal pozisyon, standart risk parametreleri
  VIX 22-25 — DİKKATLİ: normal pozisyon ama yeni girişlerde seçici ol. sadece A-kalite kurulumlar
  VIX 25-30 — GERGİN: yarım pozisyon varsayılan. yeni swing girişi sadece large cap. trailing stop sıkılaştır (2xATR → 1.5xATR). portföy modunu "dikkatli" yap
  VIX 30-35 — KRİZ: çeyrek pozisyon veya dur. mevcut pozisyonlarda kısmi kâr al. nakit oranını %30+'a çıkar
  VIX >35 — PANİK: yeni giriş yok. mevcut pozisyonları yönet. dip alım listesi hazırla (VIX düşünce kullanılacak)
  - VIX spike sonrası normalleşme: VIX zirvesinden %20+ düştüğünde kademeli geri dönüş başlat
  - VIX <20'ye dönüşte: tam kapasite geri dön, swing aktif et

- **K-13b: ichimoku 4/4 istisnası (yeni — 2 nisan 2026)**
  - gerekçe: backtest kanıtı ichimoku 4/4 + volume teyitli sinyallerin VIX 30+ ortamında bile %100 başarı gösterdiğini kanıtladı. haber bazlı impulsif girişler ile sistematik ichimoku sinyalleri ayrıştırılmalı
  - istisna koşulları (TÜMÜ eşzamanlı sağlanmalı):
    1) ichimoku skoru tam 4/4: kumo üstü + TK bull cross + fiyat tenkan üstü + volume teyit (5 gün ort / 20 gün ort > 1.3x)
    2) sektör trendi aktif (sayısal tanım — v2, 2 nisan 2026): hissenin ait olduğu sektör ETF'i hem 9SMA hem 21SMA üzerinde olmalı. ETF eşleştirmesi: XLK (tech), XLE (enerji), XLI (endüstriyel), XLC (iletişim), XLV (sağlık), XLF (finans), XLP (temel tüketim), XLY (tüketim döngüsel), XLU (utilities), XLB (malzeme). backtest kanıtı: 9 mart XLE ✅✅ → 6/6 enerji kazandı, XLI ❌❌ → 2/2 savunma kaybetti. 20 mart aynı sonuç. contrarian sektör oyunlarına (ETF SMA altında) istisna uygulanmaz
    3) mcap >$5B (large cap zorunlu)
    4) RSI 40-70 arasında (aşırı alım/satım bölgesinde değil)
    5) K-18 insider kontrolü temiz (son 30 gün CEO/CFO satışı yok)
    6) K-17 korelasyon skoru >%50
  - istisna durumunda pozisyon boyutu:
    VIX 25-30: yarım pozisyon ($5K) → değişiklik yok, zaten izin var
    VIX 30-35: yarım pozisyon ($5K) izni açılır (normalde çeyrek veya dur)
    VIX >35: çeyrek pozisyon ($2.5K) izni açılır (normalde tamamen dur)
  - ek güvenlik katmanları (istisna kullanıldığında zorunlu):
    a) stop sıkılaştırma: kijun-sen trailing + max %5 (hangisi daha sıkıysa)
    b) max 2 eşzamanlı istisna pozisyonu (toplam risk sınırı)
    c) aynı sektörden max 1 istisna pozisyonu (K-17 korelasyon koruması)
    d) hedef %10 sabittir, K-11 kademeli çıkış uygulanmaz (hızlı kâr al ve çık)
    e) giriş günü hisse o gün >%3 yükselmişse girme (kovalama yasağı)
  - iptal koşulları: VIX bir gün içinde >%15 yükselirse istisna pozisyonları yarıya indirilir
  - izleme: her istisna girişi trade log'da "K-13b istisnası" olarak etiketlenir. 10 trade sonra başarı oranı değerlendirilir, <%60 ise istisna kaldırılır
- mevcut durum notu: VIX 25.77, "gergin" rejimde. K-13b istisnası şartları sağlanırsa yarım pozisyon izni var

**K-18: giriş öncesi insider + arz riski kontrolü (v2 — 1 nisan 2026)**
- kanıt: POWL 25 mart'ta giriş, 23 mart'ta insider $25M satış → -%10.29. CRDO insider 365 satış/0 alış → -%8.77. RKLB $1B hisse arzı → -%11.59
- araştırma: insider satışları tek başına her zaman negatif sinyal değil (vergi planlaması, çeşitlendirme). ama CEO/CFO satışı + SMA altında fiyat birleştiğinde çok güçlü negatif sinyal. hisse arzı (dilüsyon) riski yüksek borç + negatif FCF şirketlerinde yaygın
- kural (3 katmanlı kontrol — giriş öncesi zorunlu):
  1) insider kontrolü (FMP insider-trading endpoint):
     - son 30 günde CEO/CFO satışı → girme veya çeyrek pozisyon
     - son 30 günde toplam insider satışı >$5M → yarım pozisyon
     - insider alışı mevcut → pozitif sinyal, normal giriş
     - insider alış/satış dengeli → nötr, diğer faktörlere bak
  2) arz riski kontrolü (özellikle momentum/büyüme hisseleri):
     - negatif FCF + yüksek borç + büyük CapEx planı → hisse arzı riski yüksek
     - son 12 ayda hisse arzı yapılmış mı? yapılmışsa tekrar risk var
     - shelf registration (raf kayıt) aktif mi? (SEC filings kontrol)
     - risk varsa: pozisyon boyutunu %1 portföy ile sınırla (K-15b ile uyumlu)
  3) kısa vadeli satış baskısı kontrolü:
     - dark pool/büyük blok satış aktivitesi (varsa)
     - analist not düşürmeleri son 2 haftada
  - tüm kontroller girişten ÖNCE yapılır, sonradan yapılan kontrol kabul edilmez
- ihlal maliyeti: POWL -%10.38, CRDO -%8.77, RKLB -%11.59

**K-14: kayıp serisi yönetimi — drawdown fren sistemi (v2 — 1 nisan 2026)**
- kanıt: son 5 swing kapanıştan 4'ü zarar (T -%5.5, ALMU -%6.1, SOFI -%3.6, CEG -%5.0). POWL/CAMT/VRT 25 mart → 3/3 zarar
- araştırma: kurumsal risk yönetiminde standart: %10-15 drawdown'da riski azalt, ardışık zarar serisinde dur ve equity toparlanana kadar bekle. küçük boyutla yeniden başla. bu duygusal değil matematiksel bir kural
- kural (kademeli fren sistemi):
  ardışık 2 zarar: boyutu %25 küçült (standart $10K → $7.5K)
  ardışık 3 zarar: boyutu %50 küçült ($10K → $5K) + sadece A-kalite kurulumlar
  ardışık 4+ zarar: TAMAMEN DUR. en az 1 hafta swing girişi yok
  toplam swing drawdown %15+ (başlangıç sermayesine göre): dur, ortamı değerlendir
  - yeniden başlama protokolü:
    1) en az 5 iş günü bekleme (soğuma dönemi)
    2) neden kaybettiğini analiz et (ortam mı, sistem mi, psikoloji mi?)
    3) ilk 3 trade yarım pozisyonla başla (güven inşası)
    4) 2/3 kazanç gelirse normal boyuta dön
  - ortam testi: VIX <25 + SPY SMA50 üstünde + sektör rotasyonu pozitif → swing'e geri dön. herhangi biri sağlanmıyorsa → beklemeye devam
- ihlal maliyeti: 4/5 zarar serisi mart 2026

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
| 24 mart | NEM | K-17 skor %18 (min %50 gerekli) ile giriş, ichimoku 0/3 | devam izleniyor | K-17 ihlali |
| 25 mart | POWL, CAMT, VRT | toparlanma günü (çarşamba +%0.5) tam pozisyon girişi, ertesi gün -%8 ile -%10 kayıp | POWL -%10.3, CAMT -%8.3, VRT -%9.4 | K-02 varyasyonu |
| 25 mart | POWL | insider $25M satışı kontrol edilmedi, giriş yapıldı | -%10.38 (1 gün) | K-18 (yeni) |
| 24 mart | AROC | VIX 27+ ortamında swing girişi, enerji hizmet tezi ama petrol doğrudan E&P taşıdı | -%4.95 (2 gün) | K-13 |
| 2 nis (backtest) | VLO, OXY, MPC, DVN, COP, FANG | 9 mart VIX ~30 ortamında ichimoku 4/4 sinyaller tarandı (backtest). 6/6 kârda, VLO +%10 3 günde, OXY +%10 9 günde. aynı gün 3/4 sinyal savunma (NOC, LMT) 2/2 stop. volume teyidi kritik filtre | K-13 fırsat kaçırdı ama haber bazlı girişleri engelledi | K-13b istisnası eklendi |
| 2 nis (backtest) | HAL, DVN, VLO | 20 mart VIX ~27 ortamında ichimoku 4/4 sinyaller. HAL +%10 5 günde, DVN +%8.3 | 4/4 sinyaller %100 başarı | K-13b kanıtı |

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
| stop-loss disiplini (override yok) | RTX -%5.16 stop tetiklendi, K-06'ya uyuldu (24 mart) | kontrollü zarar, daha büyük kayıp önlendi |
| ichimoku 4/4 + volume teyit (backtest) | 9 mart: VLO, OXY, MPC, DVN, COP, FANG = 6/6 kazanan. 20 mart: HAL, DVN, VLO = 3/3 kazanan. 3/4 sinyal (volume eksik) savunma hisseleri 2/2 stop | %100 başarı oranı, volume teyidi kritik filtre. K-13b istisnası bu kanıta dayanır |

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
| toplam trade | 20 |
| kazanç | 10 (%50.0) |
| zarar | 10 (%50.0) |
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
- 26 mart AROC stop ihlali ile kapatıldı (-%4.95, 2 gün). 0/8 aktif pozisyon
- genel: 10K/10Z (%50 win rate), ort kazanç +%4.13, ort kayıp -%4.61
- agresif portföyde 25 mart girişleri (POWL, CAMT, VRT) ilk gününde -%8 ile -%10 arasında. K-02 varyasyonu

---

## 6. GÜNCELLEME KURALLARI

1. her kapanış raporunda "dersler" bölümünden bu dosyaya yeni kural/hata eklenir
2. kural numaraları (K-XX) sabit kalır, yeniler sona eklenir
3. istatistikler her haftalık raporda güncellenir
4. sektör gözlemleri ortam değiştikçe güncellenir
5. sabah raporu ve seans promptu bu dosyayı referans alır — karar vermeden önce ilgili kuralı kontrol et

---

*finzora ai | son güncelleme: 2 nisan 2026*

**K-15a: aşırı satım bölgesinde (RSI <35) yeni alım yaparken dikkatli ol**
- kanıt: XLI RSI 34.5, 3 haftadır düşüşte. JNJ RSI 53'te alındı ama girişte SMA20 altındaydı. endüstriyel ve sağlık sektörleri savaş ortamında sürekli baskı altında
- kural: RSI <35 bölgesinde alım yapmadan önce en az 1 gün teyit bekle (gün içi dip test + toparlanma sinyali). düşen bıçağı tutma
- ilişkili: K-04 (SMA teyidi olmadan giriş yapma)

**K-15b: momentum hisselerinde dilüsyon + arz riski (v2 — 1 nisan 2026)**
- kanıt: RKLB 18 mart $1B hisse arzı → -%11.59. bir önceki +%8 rallisi tamamen silindi
- araştırma: hisse arzı riski en yüksek olan profil: negatif FCF + yüksek büyüme + yüksek borç + aktif shelf registration. SEC S-3 dosyalaması shelf registration'ı gösterir. momentum hisselerinde ralli sonrası arz riski artar (şirketler yüksek fiyattan sermaye toplamak ister)
- kural (v2):
  - giriş öncesi dilüsyon risk skoru hesapla:
    +1: negatif FCF (son 4 çeyrek)
    +1: borç/öz sermaye >1.5
    +1: son 12 ayda hisse arzı yapılmış
    +1: aktif shelf registration (SEC filings)
    +1: büyük CapEx planı açıklanmış ama finansman belirsiz
  - skor 0-1: normal pozisyon
  - skor 2-3: max %2 portföy ağırlığı (küçük pozisyon)
  - skor 4-5: girme veya sadece opsiyon ile sınırlı risk al
  - momentum hissesi tanımı: son 3 ayda %30+ yükselmiş, P/E negatif veya >50, profitability düşük
- ihlal maliyeti: RKLB -%11.59 (portföy etkisi %0.95 ağırlık sayesinde sınırlıydı — küçük pozisyon kuralı çalıştı)

**K-16: sell the news riski değerlendirmesi (v2 — 1 nisan 2026)**
- kanıt: MU 18 mart devasa beat (EPS +%31) ama AH +%1.27, sonra -%3.8. NVDA 26 şubat beat ama -%5. ama MU tedarik zinciri ortakları (CRDO +%5.28, MRVL +%2.18, COHR +%7.14) ertesi gün ralli yaptı
- araştırma: beklentileri %10+ aşan hisseler %72 olasılıkla 5 gün pozitif momentum sürdürür. AMA hisse kazanç öncesi büyük ralli yapmışsa, beat fiyatlanmış olabilir ("buy the rumor, sell the news"). IV crush opsiyon pozisyonlarını sert vurur
- kural (sell the news risk skoru):
  +1: hisse kazanç öncesi 5 günde %5+ ralli yapmış (beklenti fiyatlanmış)
  +1: consensus EPS tahmini son 3 ayda %10+ yükseltilmiş (çıta çok yüksek)
  +1: hisse 52 haftalık zirveye %5 içinde (yukarı alan sınırlı)
  +1: sektör geneli son 1 ayda %10+ yükselmiş (sektörel beklenti yüksek)
  +1: yüksek short interest (%10+ float) → short squeeze olmazsa hayal kırıklığı büyük
  - skor 0-1: normal tutma, kazanç riski düşük
  - skor 2-3: kazanç öncesi %25 kısmi kâr al + kalan pozisyonda trailing stop sıkılaştır
  - skor 4-5: kazanç öncesi %50 kısmi çıkış. post-earnings tepkiyi bekle, gerekirse tekrar gir
  - önemli: sell the news etkisi genellikle hisseye özgü, tedarik zinciri ortaklarına yayılmayabilir (MU/CRDO örneği). tedarik zinciri ortaklarında geri çekilmeyi alım fırsatı olarak değerlendir
- ihlal maliyeti: MU -%3.8 (sınırlı), NVDA -%5

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

## 7. SWING TRADE SİSTEMİ

### v2.2 — ichimoku + hacim + ATR + ön filtre (2 nisan 2026~)

> **tam doküman**: `docs/SWING_SYSTEM_V2.md`
> **araç**: `scripts/swing_ichimoku.py`
> **neden değişti**: v1'de ichimoku'yu sabit %5 stop / %10 hedef ile karıştırıyorduk. ichimoku kendi başına komple bir trend sistemi. sabit kurallarla karıştırmak çelişki yaratıyordu (NEM örneği: ichimoku 0/3 "girme" diyor, RSI oversold tezi "gir" diyordu).

**v2.2 özeti**:
- giriş: kumo kırılımı / TK cross / kijun bounce (ichimoku sinyalleri)
- stop: kijun-sen dinamik (sabit %5 yok)
- hedef: tüm swing girişleri ön filtreden geçtiği için sabit %10 hedef. portföy pozisyonlarında K-11 kademeli çıkış uygulanır
- trailing: kijun-sen doğal trailing (sabit % yok)
- süre: %10 hedefe veya stop'a kadar tut. süre sınırı yok ama K-08 zaman filtresi uygulanır
- hacim: giriş teyidi + OBV trendi
- ATR: pozisyon boyutlandırma + stop mesafesi doğrulama
- RSI/MACD/SMA: kullanılmıyor (ichimoku zaten hepsini kapsıyor)

### v1 (eski, 24 mart 2026'ya kadar)

> v1 artık kullanılmıyor. skor kartı sistemi (7 puan, sabit %5/%10) ichimoku ile çelişiyordu.
> eski script `scripts/swing_technical.py` referans olarak saklanıyor.
> v1 detayları: git log'dan 24 mart 2026 öncesi commitlerde mevcut.

---

*finzora ai | son güncelleme: 2 nisan 2026*

**K-17: korelasyon ve yoğunlaşma risk yönetimi (v2 — 1 nisan 2026)**
- kanıt: 25 mart POWL, CAMT, VRT aynı gün girildi, üçü AI altyapısı → üçü de -%8 ile -%10. IBKR portföyde AI/yarıiletken %63 yoğunluk → büyük düzeltmede toplu zarar riski
- araştırma: kurumsal portföylerde tek faktör maruziyeti VAR'ın (value at risk) büyük kısmını belirler. korelasyon riski düşüşlerde artar (korelasyonlar krızde 1'e yaklaşır). pozisyon çeşitlendirmesi tek başına yetmez, tema/sektör çeşitlendirmesi de gerekli
- kural (v2 — genişletildi):
  aynı gün giriş limitleri:
  - max 2 yeni pozisyon aynı gün (hepsi farklı sektör/tema olsa bile)
  - aynı tema/sektörden max 1 yeni giriş per gün
  - VIX >25'te aynı gün max 1 yeni giriş (tema fark etmez)
  tema yoğunluk limitleri (K-12 ile entegre):
  - tek tema max %40 toplam portföy (AI/yarıiletken, enerji, savunma vb.)
  - %40 aşılırsa: en zayıf pozisyonu küçült veya yeni giriş yapma
  - IBKR notu: mevcut AI/yarıiletken yoğunluğu %63 → sınır çok aşılmış. yeni AI girişi yapmadan önce mevcut pozisyonlardan biri küçültülmeli
  korelasyon kontrol listesi (giriş öncesi):
  - yeni hissenin mevcut portföyle korelasyonu yüksek mi? (aynı sektör ETF'ine bak)
  - aynı makro faktöre duyarlı mı? (faiz, petrol, dolar, çip talebi)
  - aynı katalizöre mi tepki veriyor? (kazanç açıklaması, FOMC, sektör haberi)
- ihlal maliyeti: POWL/CAMT/VRT toplam -%28.0

**RGLD çıkış teyidi (25 mart 2026)**
- kanıt: RGLD -%16 zararla satıldı @$232. altın korelasyon bozulması tezi doğrulandı. sermaye SM'ye aktarıldı (güçlüye aktar prensibi)
- sonuç: sektör gözlemlerindeki "altın yükseliyor diye royalty yükselecek varsayımı hatalı" notu kesin olarak doğrulandı. RGLD çıkışı K-08 (momentum yoksa çık) ve tez bozulma prensibiyle tutarlı

**NEM ichimoku çıkış (25 mart 2026)**
- kanıt: NEM SWING-026, +4.18% kârdayken ichimoku 0/4 (kumo altı, düşüş trendi) nedeniyle çıkıldı. disiplinli çıkış
- sonuç: ichimoku v2 sisteminin ilk başarılı çıkış sinyali. kârdayken bile teknik bozulma sinyaline saygı göstermek doğru
- ilişkili: K-07 (trailing stop disiplini)
