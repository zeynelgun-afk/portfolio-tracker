# TRADING PLAYBOOK — KANIT BAZLI KURALLAR

> **son güncelleme**: 7 nisan 2026
> **amaç**: gerçek trade deneyimlerinden çıkarılan, tekrar ihlal edilmemesi gereken kurallar
> **güncelleme sıklığı**: her kapanış raporunda yeni dersler eklenir
> **referans**: sabah raporu ve seans promptu bu dosyayı okur

---

## 1. KANITLANMIŞ KURALLAR

her kural en az bir gerçek trade deneyimiyle doğrulanmıştır. kural numarası değişmez, yeniler sona eklenir.

### giriş kuralları

**K-01: büyük makro veri öncesi giriş yapma**
- NFP, CPI, FOMC, GDP verilerinden 24 saat önce yeni swing pozisyon açma
- mevcut pozisyonlarda: kazanç+makro aynı haftada çakışıyorsa pozisyonu %50 küçült
- veri sonrası: ilk 1 saat (tercihen 1 seans) bekle, trend yönünü teyit et
- pozisyon trade/LEAPS: pozisyonu tut ama yeni ekleme yapma
- istisna: veri beklentiyle uyumlu (sürpriz yok) + mevcut trend güçlü → mevcut pozisyonlara dokunma
- kanıt: AMKR -%6.12

**K-02: kriz rallisinin ilk gününe girme**
- kriz/savaş/jeopolitik olayda ilk gün rallisine/satışına girme. en az 2 tam işlem günü bekle
- giriş teyitleri: RSI 50 üstü stabilizasyon + hacim normalleşmesi + VIX zirve sonrası geri çekilme
- enerji/savunma kriz rallileri kısa ömürlü olabilir. kalıcı tedarik kesintisi kanıtlanana kadar tam pozisyon yok
- dip alım: 3 hafta sonrası hedefle. kademeli giriş %33 → %33 → %34
- kanıt: 2 mart 5/5 zarar (KTOS, CEG, HAL, LASR, BKSY), 25 mart 3/3 zarar (POWL, CAMT, VRT)

**K-03: KALDIRILDI** — içeriği K-13 v4.1 ile örtüşüyordu. tüm VIX bazlı pozisyon boyutlandırma artık K-13'te

**K-04: trend teyidi olmadan pozisyon açma**
- katman A (en güçlü): SMA50 + SMA200 + ichimoku kumo üstü → tam pozisyon
- katman B (normal): SMA200 üstü, SMA50 altı → SMA50 kırılma bekleniyor, yarım pozisyon
- katman C (riskli): SMA200 altı + güçlü katalizör → çeyrek pozisyon. RSI <35 ise K-15a teyidi de zorunlu
- katman D (yasak): SMA50 + SMA200 + kumo altı → düşen bıçağı tutma
- ek filtre: insider satışı yoğunsa (K-18) + SMA altıysa → çifte kırmızı bayrak, giriş yok
- kanıt: CRDO -%8.77 (2 kez), SOFI -%3.6

**K-05: kazanç açıklaması 3 aşamalı strateji**
- kanıt: NVDA swing +%2.9 (önce çıkıldı, sonra düştü). MU EPS +%31 ama AH +%1.27 sonra -%3.8 (sell the news). MU tedarik zinciri ortakları ertesi gün ralli: CRDO +%5.28, MRVL +%2.18, COHR +%7.14
- prensip: kazanç öncesi straddle/giriş negatif beklenti (IV crush). PEAD (post-earnings drift) sürpriz yönünde sürdürülebilir getiri sağlar. sell-the-news hisseye özgü, tedarik zinciri ortaklarına yayılmayabilir

  **AŞAMA 1 — AÇIKLAMA ÖNCESİ (çıkış/koruma)**
  - swing trade: 2+ gün önce çık (kâr/zarar fark etmez). binary gap riski yok
  - pozisyon trade: K-16 skoruna göre
    • K-16 0-2: pozisyonda kal, trailing 2×ATR → 1.5×ATR sıkılaştır
    • K-16 3: %25 kısmi kâr al, kalan trailing
    • K-16 4-5: %50 kısmi çık, post-earnings bekle
    • mevcut kâr %15+ ise K-16'dan bağımsız min %25 kısmi al
  - LEAPS: vade 6+ ay tut, vade 3 ay altı + kâr → kısmi çık

  **AŞAMA 2 — AÇIKLAMA SONRASI GİRİŞ (PEAD)**
  giriş koşulları (TÜMÜ):
    1) EPS sürpriz ≥%10
    2) ilk gün gap aynı yönde
    3) ilk gün hacim ≥ 20g ortalama × 2
    4) 2. gün trigger candle (1. gün range içinde konsolide + aynı yönde kapanış)
    5) ilk güne GİRME (K-02)
  - boyut: yarım pozisyon
  - stop: ilk gün düşüğü altı (long)
  - hedef: 60 gün drift veya chandelier 3×ATR
  - filtre: küçük/orta cap'te güçlü, mega-cap'te zayıf

  **AŞAMA 3 — TEDARİK ZİNCİRİ YAYILIM**
  koşullar:
    1) lider beat (EPS sürpriz ≥%5 veya gelir ≥%3)
    2) lider guidance güçlü (yıl beklentisi yükseltildi)
    3) beat metrikleri ortağı doğrudan etkiliyor
    4) ortak teknik uygun (SMA200 üstü, kumo üstü, RSI 40-65)
  - giriş: lider açıklamasından 1-2 gün sonra
  - boyut: yarım pozisyon, stop chandelier 3×ATR
  - max 1 ortak/açıklama (K-17 korelasyon riski)
  - tedarik zinciri haritası: docs/AGGRESSIVE_V2_THESIS.md

### çıkış kuralları

**K-06: stop-loss override protokolü**
- stop tetiklendiğinde ÇIKIŞ. tartışma yok
- override istisnası (sadece 1 kez, 4 koşul TÜMÜ sağlanmalı):
  a) hisse teknik destek seviyesinde (SMA200, pivot, kumo)
  b) piyasa geneli kötü (SPY -%2+) ve hisse pozitif ayrışıyor
  c) orijinal tez sağlam
  d) yeni stop max %2 daha aşağıda
- 4 koşuldan biri eksikse → direkt çık
- override sonrası 3 iş günü toparlanma yoksa → kesin çıkış, 2. override yok
- ATR önerisi: sabit %5 yerine 2×ATR(14)
- kanıt: LASR -%3.8 → -%7.3 (ihlal), RTX -%5.16 (uyuldu)

**K-07: izleyen zarar kes (trailing stop) disiplini**
- swing trade: chandelier exit — highest_high − 3×ATR(14)
- pozisyon trade: 20SMA günlük kapanış altı VEYA 50SMA haftalık altı
- momentum trade: 10EMA altı kapanış (daha sıkı)
- trailing tetiklendiğinde sorgulama yok, çık. ASLA bozulmaz
- çıkış sonrası yeni sinyal verirse tekrar girilebilir (yeni trade olarak)
- sıkılaştırma zamanı: VIX yükselirken, kazanç yaklaşırken, sektör zayıflarken
- kazanç: SHOP +%8, BKSY +%18.5, NEM +%2.1, TYL +%11.2 (4/4)

**K-08: zaman bazlı çıkış + sektör ayrışma filtresi**
- kapsam:
  • Swing v2.3 (aktif): sert 15g limit YOK, chandelier yönetir. sadece "momentum yok + ayrışma yok" durumunda manuel inceleme
  • Swing v1 / sabit hedefli: 3 aşamalı zaman filtresi (aşağıda)
  • Agresif portföy pozisyon trade'leri: zaman sınırı yok, tez bazlı
- 3 aşamalı filtre (sadece v1 / sabit hedefli):
  • gün 1-7: normal izleme
  • gün 8-10: momentum kontrol — fiyat giriş +%3 ve hacim artıyor mu?
    - evet → devam
    - hayır + pozitif ayrışma + hacim → +5 gün tolerans
    - hayır + pozitif ayrışma + düşük hacim → +3 gün, sonra çık
    - hayır + ayrışma yok → derhal çık
  • gün 15+: katalizör yoksa çık
- ichimoku entegrasyonu: kijun düz + fiyat sıkışıyor → momentum yok. kumo daraldı → sabırlı ol. kumo geniş + trend belirsiz → çık
- kanıt: T -%5.5, LMT zaman maliyeti

**K-09: stop yakınlığı erken çıkış protokolü**
- fiyat stop'a %2 mesafede ise 4 kontrol:
  1) RSI yönü: düşüyor + 40 altı → erken çık
  2) hacim: satış > alış → erken çık
  3) piyasa: SPY negatif + VIX yükseliyor → erken çık
  4) sektör: ETF düşüyor → erken çık
- 4'ten 3+ negatif → stop beklemeden çık
- 4'ten 2 negatif → stop'u bekle
- toparlanma sinyali (hammer mum, hacim artışı) → stop'u tut
- telegram alert: stop'a %2 kala otomatik (--type alert)
- kanıt: AMKR, GE doğru çıkışlar

### portföy yönetimi kuralları

**K-10: savunmacı/temettü allokasyon kuralı (K-13 ile hizalı)**
- VIX <22 (sakin/normal): min %25 savunmacı
- VIX 22-28 (dikkatli): min %35 savunmacı
- VIX 28-35 (gergin): min %45 savunmacı, agresif pozisyonları küçült
- VIX 35+ (panik): min %55 savunmacı, agresif'te sadece mevcudu yönet
- savunmacı tanımı: temettü yield >%2.5, beta <1.0, veya utilities/tüketim/sağlık
- enerji: çatışma dönemlerinde saldırgan, K-13 v4.1 faydalanıcı listesinde değerlendir
- toplam portföyde min %35 savunmacı korunmalı (mevcut "dikkatli" rejimde)

**K-11: kademeli kâr alma sistemi**
- kapsam: sadece portföy pozisyonları. swing'de uygulanmaz (kâr kilidi sistemi: <%7 chandelier 3×ATR, %7-15 2×ATR, %15+ 1.5×ATR)
- prensip: güçlü trendlerde RSI 70+ uzun süre kalabilir. RSI 70 otomatik satış değil, momentum teyidi. kazananı erken kesme

  katman 1 — UYARI (izle, satma):
  RSI 70+ ve %15+ kâr → trailing aktif (2×ATR(14) veya 20SMA altı kapanış, hangisi geniş). koruma modu

  katman 2 — KISMİ KÂR AL (%25-30, tetikleyici BİRİ):
  a) RSI bearish divergence (fiyat yeni zirve, RSI yapmaz)
  b) RSI 75+ sonra 70 altı (momentum kırılması)
  c) fiyat 20SMA altı kapanış
  d) RSI 80+ (uyumsuzluk aramadan)

  katman 3 — KALAN (trailing ile devam):
  pozisyon trade: 50SMA altı kapanış veya 3×ATR(14). trend bitene kadar tut

- istisnalar:
  • earnings 5 gün içinde: katman 2'yi RSI 70+'ta uygula
  • VIX >28: katman 2'yi RSI 72+'ta uygula
  • LEAPS: katman 2 eşiği RSI 80+
- kanıt: SM RSI 74 → ertesi gün -%4.38 (doğru). KOS parçalı ideal

**K-12: pozisyon konsantrasyon limitleri**
- tek hisse: max %15 portföy ağırlığı
- tek hisse + opsiyonları: max %20 (delta ayarlanmış)
- tek sektör/tema: max %40
- LEAPS efektif maruziyet: kontrat × 100 × delta. örnek: 6 MU call × $87.93 × 100 × 0.55 ≈ $29K
- aşımda:
  • %15 aşıldı → 1 hafta içinde kısmi satış
  • %20 aşıldı → aynı/ertesi gün kısmi satış
  • sektör %40 aşıldı → en zayıf pozisyonu küçült veya kapat
- haftalık kontrol pazar günleri zorunlu

### ortam kuralları

**K-13: VIX dinamik sektör bazlı risk yönetimi — MASTER VIX KURALI**
- temel: VIX tüm sektörleri eşit vurmaz. blanket VIX engeli fırsat maliyeti yaratır (mart 2026: agresif portföy %100 nakitte kalıp -$42K, ama enerji+savunma rallisini kaçırdı)
- kanıt: 9 mart VIX ~30, ichimoku 4/4 6/6 enerji kazandı (VLO/OXY/MPC/DVN/COP/FANG), aynı gün 3/4 sinyal savunma 2/2 stop. volume teyidi (4. sinyal) kritik filtre

  **ADIM 1: kriz tipini belirle** (sektör listesi kriz tipine göre değişir)

  | kriz tipi | faydalanıcı | duyarlı | tarihsel örnek |
  |-----------|-------------|---------|----------------|
  | jeopolitik/savaş (petrol şoku) | enerji, savunma, altın, staples, telekom | tech, döngüsel, havacılık | İran 2026, RU-UA 2022 |
  | pandemi/sağlık | tech, sağlık, e-ticaret, cloud | enerji, havacılık, otel, restoran | COVID 2020 |
  | finansal/sistemik | HİÇBİRİ (her şey duyarlı) | HER ŞEY | 2008 GFC, 1998 LTCM |
  | ticaret savaşı/tarife | domestik, küçük cap, hizmet | ihracatçılar, tedarik bağımlı tech, otomotiv | 2018-19, 2025 |
  | enflasyon/faiz şoku | enerji, emtia, bankalar | yüksek P/E büyüme, REIT, utilities, tech | 2022 Fed |

  **ADIM 2: aktif kriz listesi** (kriz değişirse güncellenir)

  ⚠️ AKTİF: jeopolitik/savaş (İran, şubat 2026'dan beri)

  Faydalanıcı sektörler:
  - savunma: RTX, NOC, LMT, GD, HII, TDG, TDY
  - enerji E&P/rafineri: XOM, CVX, COP, DVN, EOG, VLO, MPC, FANG, OXY, AR
  - altın: NEM, GOLD, RGLD, FNV, WPM
  - sağlık: JNJ, MRK, PFE, UNH, LLY, ABBV
  - staples/tütün: MO, PM, PG, KO, PEP, CL
  - telekom: T, VZ
  - utilities: NEE, DUK, SO, D
  - siber güvenlik: PANW, CRWD, FTNT

  Duyarlı sektörler:
  - tech/AI yarıiletken: NVDA, MRVL, COHR, AVGO, AMAT, KLAC, LRCX
  - tüketim döngüsel: TSLA, AMZN, NKE, SBUX
  - havacılık: DAL, UAL, AAL, LUV
  - küçük cap (mcap <$5B), spekülatif/IPO/SPAC, REIT, kripto

  **ADIM 3: kriz tipi geçişi**
  - kriz değişirse sektör listesi aynı gün güncellenir
  - kesişim dönemi (2 kriz aynı anda): iki tablonun kesişimi faydalanıcı
  - belirsiz dönemde: tüm sektörler "duyarlı" sayılır

  **VIX bant matrisi:**
  | VIX | faydalanıcı | duyarlı |
  |-----|-------------|---------|
  | <22 (sakin) | tam | tam |
  | 22-28 (dikkatli) | tam | yarım |
  | 28-35 (gergin) | yarım | giriş yok |
  | 35+ (panik) | çeyrek | giriş yok |

  ⚠️ sistemik finansal krizde sektör ayrımı uygulanmaz, tüm sektörler duyarlı

  **VIX 28+ ek kuralları (tüm sektörler):**
  - stop: 2×ATR → 3×ATR
  - max risk: %3 portföy (normal %5 yerine)
  - pozisyon formülü (sadece VIX 28+): standart × (22/VIX). örn VIX 30'da $10K → $7.3K
  - VIX 1 günde >%15 yükselirse yeni girişler 1 gün ertelenir
  - VIX zirvesinden %20 düştüğünde duyarlı sektörlere kademeli geri dönüş

- **K-13b: ichimoku 4/4 istisnası (sadece duyarlı sektörler için)**
  - amaç: K-13 duyarlı sektörlere VIX 28+ giriş yasaklıyor. K-13b sistematik 4/4 sinyalle çeyrek pozisyon istisnası
  - backtest: 51 dönem kriz modunda 11 kâr / 2 zarar = %85 başarı
  - kapsam: SADECE duyarlı sektörler (faydalanıcılar K-13 ile zaten izinli)
  - boyut: VIX 28-35 → çeyrek pozisyon ($2.5K). VIX 35+ → giriş yok
  - 6 koşul TÜMÜ:
    1) ichimoku tam 4/4 (kumo üstü + TK bull cross + tenkan üstü + volume 5g/20g >1.3x)
    2) sektör ETF 9EMA + 21EMA üstü (XLK, XLE, XLI, XLC, XLV, XLF, XLP, XLY, XLU, XLB)
    3) mcap >$2B
    4) RSI 40-70
    5) K-18 temiz (30g CEO/CFO satışı yok)
    6) K-17 korelasyon >%50
  - güvenlik:
    a) stop: chandelier (highest_high − 3×ATR(14)). sabit %5 cap YOK
    b) çıkış: Swing v2.3 kâr kilidi (<%7: 3×ATR, %7-15: 2×ATR, %15+: 1.5×ATR). sabit hedef YOK
    c) max 2 eşzamanlı, sektör başına max 1
    d) o gün >%3 yükselmişse girme (kovalama yasağı)
  - iptal: VIX 1 günde >%15 yükselirse istisna pozisyonları yarıya
  - izleme: trade log'da "K-13b istisnası" etiketi. 10 trade sonra <%60 ise istisna kaldırılır
- mevcut durum: VIX 24.83, "dikkatli" rejim. faydalanıcılarda tam, duyarlılarda yarım pozisyon

- **K-13b: ichimoku 4/4 istisnası (sadece duyarlı sektörler için)**
  - amaç: K-13 duyarlı sektörlere VIX 28+ giriş yasaklıyor. K-13b sistematik 4/4 sinyalle çeyrek pozisyon istisnası
  - backtest: 51 dönem kriz modunda 11 kâr / 2 zarar = %85 başarı
  - kapsam: SADECE duyarlı sektörler (faydalanıcılar K-13 ile zaten izinli)
  - boyut: VIX 28-35 → çeyrek pozisyon ($2.5K). VIX 35+ → giriş yok
  - 6 koşul TÜMÜ:
    1) ichimoku tam 4/4 (kumo üstü + TK bull cross + tenkan üstü + volume 5g/20g >1.3x)
    2) sektör ETF 9EMA + 21EMA üstü (XLK, XLE, XLI, XLC, XLV, XLF, XLP, XLY, XLU, XLB)
    3) mcap >$2B
    4) RSI 40-70
    5) K-18 temiz (30g CEO/CFO satışı yok)
    6) K-17 korelasyon >%50
  - güvenlik:
    a) stop: chandelier (highest_high − 3×ATR(14)). sabit %5 cap YOK
    b) çıkış: Swing v2.3 kâr kilidi (<%7: 3×ATR, %7-15: 2×ATR, %15+: 1.5×ATR). sabit hedef YOK
    c) max 2 eşzamanlı, sektör başına max 1
    d) o gün >%3 yükselmişse girme (kovalama yasağı)
  - iptal: VIX 1 günde >%15 yükselirse istisna pozisyonları yarıya
  - izleme: trade log'da "K-13b istisnası" etiketi. 10 trade sonra <%60 ise istisna kaldırılır
- mevcut durum: VIX 24.83, "dikkatli" rejim. faydalanıcılarda tam, duyarlılarda yarım pozisyon


**K-14: kayıp serisi yönetimi (drawdown fren)**
- kademeli fren:
  • 2 ardışık zarar: boyut %25 küçült ($10K → $7.5K)
  • 3 ardışık zarar: boyut %50 küçült ($10K → $5K) + sadece A-kalite
  • 4+ ardışık zarar: TAMAMEN DUR, min 1 hafta swing yok
  • toplam swing drawdown %15+ (başlangıca göre): dur, ortamı değerlendir
- yeniden başlama protokolü:
  1) min 5 iş günü soğuma
  2) neden kaybettiğini analiz et (ortam/sistem/psikoloji)
  3) ilk 3 trade yarım pozisyon
  4) 2/3 kazanırsa normal boyuta dön
- ortam testi: K-13'e göre. faydalanıcı sektörlerde VIX <28, duyarlı sektörlerde VIX <22 + SPY SMA50 üstü + sektör rotasyonu pozitif → swing'e dön
- kanıt: mart 2026 4/5 zarar serisi

### giriş öncesi filtreler

**K-15a: RSI <35 oversold girişinde dikkat**
- RSI <35 bölgesinde alım öncesi en az 1 gün teyit bekle (gün içi dip-test + toparlanma sinyali). düşen bıçağı tutma
- ilişkili: K-04 (SMA teyidi)

**K-15b: momentum hisselerinde dilüsyon + arz riski**
- giriş öncesi dilüsyon risk skoru:
  • +1: negatif FCF (son 4 çeyrek)
  • +1: borç/öz sermaye >1.5
  • +1: son 12 ay içinde hisse arzı yapılmış
  • +1: aktif shelf registration (SEC S-3)
  • +1: büyük CapEx planı + finansman belirsiz
- skor 0-1: normal pozisyon
- skor 2-3: max %2 portföy ağırlığı
- skor 4-5: girme veya sadece opsiyon ile sınırlı risk
- momentum hissesi tanımı: son 3 ayda %30+ ralli, P/E negatif veya >50
- kanıt: RKLB -%11.59 (küçük pozisyon kuralı sayesinde portföy etkisi sınırlı)

**K-16: sell the news riski değerlendirmesi**
- skor (her madde +1):
  • hisse kazanç öncesi 5 günde %5+ ralli (beklenti fiyatlanmış)
  • consensus EPS son 3 ay %10+ yükseltilmiş (çıta yüksek)
  • 52w zirveye %5 mesafe (yukarı alan dar)
  • sektör son 1 ay %10+ ralli
  • short interest %10+ float
- skor 0-1: normal tut
- skor 2-3: kazanç öncesi %25 kısmi al + trailing sıkılaştır
- skor 4-5: kazanç öncesi %50 kısmi çık, post-earnings bekle
- **önemli**: sell-the-news hisseye özgü, tedarik zinciri ortaklarına yayılmayabilir (MU→CRDO/MRVL/COHR örneği). ortaktaki geri çekilme alım fırsatı olabilir
- kanıt: MU -%3.8, NVDA -%5

**K-17: korelasyon ve yoğunlaşma yönetimi**
- aynı gün giriş limitleri:
  • max 2 yeni pozisyon/gün (farklı sektör olsa bile)
  • aynı tema/sektörden max 1
  • VIX 22-28 ("dikkatli"): max 1 duyarlı sektör girişi (faydalanıcılarda 2'ye izin)
  • VIX 28+: max 1 yeni giriş toplam (K-13 duyarlıları zaten yasaklıyor)
- tema yoğunluk (K-12 ile entegre): tek tema max %40
  • aşılırsa en zayıfı küçült, yeni giriş yok
  • IBKR notu: AI/yarıiletken %63 → sınır aşıldı, yeni AI öncesi azaltma şart
- korelasyon checklist (giriş öncesi):
  • yeni hisse mevcut portföyle aynı sektör ETF'inde mi?
  • aynı makro faktör (faiz, petrol, dolar, çip talebi)?
  • aynı katalizöre mi tepki veriyor (earnings, FOMC, sektör haberi)?
- kanıt: POWL+CAMT+VRT toplam -%28

**K-18: giriş öncesi insider kontrolü**
- 1) insider (FMP insider-trading endpoint):
  • 30 gün CEO/CFO satışı → girme veya çeyrek pozisyon
  • 30 gün toplam satış >$5M → yarım pozisyon
  • insider alışı → pozitif sinyal, normal giriş
  • dengeli → nötr, diğer faktörlere bak
- 2) kısa vadeli baskı:
  • dark pool / blok satışları
  • son 2 hafta analist downgrade'leri
- 3) arz/dilüsyon riski → K-15b'ye bak (negatif FCF, shelf, hisse arzı geçmişi)
- tüm kontroller girişten ÖNCE
- kanıt: POWL -%10.38, CRDO -%8.77

**K-19: XLP swing dışlama**
- XLP hisselerinden (MO, PM, PEP, WMT, COST, KO) swing trade sinyali değerlendirilmez. ichimoku 4/4 veya K-13b sinyal verse bile girme
- gerekçe: defansif hisseler yapısal düşük volatiliteye sahip — günlük %0.5-1 hareket eden hisseden 10 günde %10 beklemek gerçekçi değil
- kapsam: sadece swing. portföy pozisyonu (dengeli/temettü) olarak XLP alınabilir
- backtest: 51 dönem 0 hedef, 2 stop, 4 düz

**K-20: sektör RS dead cat bounce filtresi**
- kural: sektör ETF/SPY oranı 20g değişim <0 VE 10g değişim >0 ise swing girişi yok
- hesaplama: RS = sektörETF/SPY. RS20 = (RS_bugün − RS_20gün_önce)/RS_20gün_önce ×100. RS10 aynı formül
- gerekçe: sektör orta vadede SPY'a karşı zayıf ama kısa vadede sıçramış → dead cat bounce. sektörel zayıflık devam ediyor
- kapsam: tüm VIX bantları. K-13b istisna pozisyonlarında uygulanmaz (kendi sektör ETF filtresi var)
- sektör ETF: XLK, XLC, XLE, XLI, XLV, XLF, XLY
- backtest: bu kombinasyonda 3 kâr / 12 zarar (%80 zarar). filtre ile kâr oranı %47 → %54

### ek kanıtlar

**K-04 ek kanıt: CRDO 17 mart 2026** — CRDO 10 mart $114.28'den alındı (tüm SMA'ların altında: SMA50 $125.88, SMA200 $128.84). 17 mart -%10.8 günlük düşüşle stop tetiklendi (-%8.77). insider 365 sat / 0 al, gross margin guidance compression. K-04 ikinci kez doğrulandı

**RGLD altın korelasyon bozulması** — altın -%5 düştüğünde RGLD -%7.20 (negatif beta, daha sert). royalty modeli altınla asimetrik korelasyon: yukarı sınırlı, aşağı sert. tez bozulma sınırı -%20 ($217 civarı). "altın yükseliyor diye royalty yükselecek" varsayımı yanlış


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

---

## 6. GÜNCELLEME KURALLARI

1. her kapanış raporunda "dersler" bölümünden bu dosyaya yeni kural/hata eklenir
2. kural numaraları (K-XX) sabit kalır, yeniler sona eklenir
3. istatistikler her haftalık raporda güncellenir
4. sektör gözlemleri ortam değiştikçe güncellenir
5. sabah raporu ve seans promptu bu dosyayı referans alır — karar vermeden önce ilgili kuralı kontrol et

---

## 7. SWING TRADE SİSTEMİ

### v2.3 — ichimoku + hacim + ATR + ön filtre + SPY master switch (2 nisan 2026~)

> **tam doküman**: `docs/SWING_SYSTEM_V2.md`
> **araç**: `scripts/swing_ichimoku.py`
> **neden değişti**: v1'de ichimoku'yu sabit %5 stop / %10 hedef ile karıştırıyorduk. ichimoku kendi başına komple bir trend sistemi. sabit kurallarla karıştırmak çelişki yaratıyordu (NEM örneği: ichimoku 0/3 "girme" diyor, RSI oversold tezi "gir" diyordu).

**v2.3 özeti**:
- ön filtre: ichimoku 4/4 zorunlu → K-13 v4.1 sektör bazlı VIX matrisi uygula (faydalanıcı sektör VIX 28'e kadar tam, duyarlı VIX 22'den itibaren yarım) → SPY > 21EMA + eğim ↗ → K-19 → K-20. duyarlı sektörlerde VIX >28 → K-13b istisnası gerekli
- giriş: ichimoku 4/4 (kumo üstü + TK bull + tenkan üstü + volume 1.3x) zorunlu. 3/4 sinyal swing'de değerlendirilmez
- stop: chandelier exit — highest_high - 3×ATR(14) trailing stop
- çıkış: kâr kilidi sistemi (<%7: chandelier 3×ATR, %7-15: 2×ATR, %15+: 1.5×ATR). sabit hedef yok. portföy pozisyonlarında K-11 kademeli çıkış uygulanır
- trailing: chandelier exit doğal trailing (highest high artınca veya ATR düşünce stop yükselir)
- süre: %10 hedefe veya stop'a kadar tut. K-08 zaman filtresi uygulanır
- K-19: XLP (defansif) sektöründen swing girişi yapılmaz
- K-20: sektör RS dead cat bounce → sektör 20g RS↘ + 10g RS↗ ise girme (76 trade: %80 zarar)
- chandelier kanıtı: 126 trade karşılaştırmasında kijun +12% vs chandelier 3×ATR +57% toplam P/L
- ABEF kaldırıldı: 184 sinyal analizinde %0 iyileştirme. 4/4 ichimoku zorunluluğu +5p daha etkili
- K-13b her dönemde %85+ kâr oranı (en güvenilir bileşen)
- tarama evreni: FMP screener dinamik (~1,100 hisse, mcap >$2B, vol >500K, price >$10). seans içinde çekilir, sabit liste yok

### v1 (eski, 24 mart 2026'ya kadar)

> v1 artık kullanılmıyor. skor kartı sistemi (7 puan, sabit %5/%10) ichimoku ile çelişiyordu.
> eski script `scripts/swing_technical.py` referans olarak saklanıyor.
> v1 detayları: git log'dan 24 mart 2026 öncesi commitlerde mevcut.

---

*finzora ai | son güncelleme: 7 nisan 2026*
