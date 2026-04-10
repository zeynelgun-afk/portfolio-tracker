# TRADING PLAYBOOK — KANIT BAZLI KURALLAR

> **son güncelleme**: 7 nisan 2026
> **amaç**: gerçek trade deneyimlerinden çıkarılan, tekrar ihlal edilmemesi gereken kurallar
> **güncelleme sıklığı**: her kapanış raporunda yeni dersler eklenir
> **referans**: sabah raporu ve seans promptu bu dosyayı okur

---

## 1. KANITLANMIŞ KURALLAR

her kural en az bir gerçek trade deneyimiyle doğrulanmıştır. kural numarası değişmez, yeniler sona eklenir.

### giriş kuralları

**K-01: KALDIRILDI** — 7 nisan 2026 değerlendirmesinde geri çekildi. gerekçeler:
- repo verisi (n=22 swing) destek sağlamadı: makro penceresinde win rate %75, ortalama P/L makro dışı grupla birebir aynı (+%0.26)
- FOMC pre-drift literatürü (Lucca-Moench 2015, Quantseeker 2024) FOMC öncesi dönemde POZİTİF drift gösteriyor, "giriş yapma" yönünde değil
- tek somut kanıt (AMKR -%6.12) N=1, AMKR closed.json'da swing kapanışı olarak da bulunmuyor
- "earnings + makro çakışması %50 küçült" maddesi K-05 ile çakışıyordu
- "sürpriz yok ise dokunma" istisnası giriş anında bilgi olmadığı için mantıken hatalı
- NFP/CPI/PCE binary risk koruması gerekirse ileride ayrı ve dar bir kural olarak yeniden ele alınacak

**K-02: kriz/şok başlangıcında momentum sektörlerine yeni giriş yapılmaz**
- tetik: VIX 1 günde >%20 sıçradığında VEYA SPX 1 günde >%2 düştüğünde + jeopolitik/finansal şok haberi
- yasak: 3 işlem günü boyunca AI tedarik zinciri, semiconductor, growth tech, momentum hisselerine yeni giriş yok
- muaf sektörler: defansif (XLU, XLP, XLV), enerji (XLE), gold (GLD, GDX) — yeni giriş açık
- mevcut pozisyonlar: K-13 v4.1 (sektör bazlı VIX) ve K-07 (trailing stop) tarafından yönetilir, K-02 burada müdahale etmez
- geri dönüş teyidi (3 günden önce de açılabilir, en az 1 tanesi gerekli): VIX zirveden %20 düştü VEYA sektör ETF SMA20 üstüne döndü VEYA SPX en düşüğünden +%3 toparladı
- gerekçe: MSCI çoklu varlık çalışması (5 jeopolitik şok, 2006-2026) momentum + value faktörlerinin kriz sonrası her bölgede en kötü performansı verdiğini gösteriyor; ABD piyasası genelde direniyor ama momentum hisselerinde unwinding sert
- kanıt: 2-9 mart 2026 dönemi (HAL -%5.10, CEG -%5.05, KTOS stop). aynı dönemde BKSY +%18 kâr, LASR breakeven — yani "tüm kriz girişleri zarar" iddiası geçerli değil, sadece momentum/AI tema riski geçerli
- 25 mart POWL/CAMT/VRT trade'leri tarihsel olarak K-02 referansı altında listelenmişti ama AI tedarik zinciri tezi ile girilmişti, bunlar K-13 alanına aittir

**K-03: KALDIRILDI** — içeriği K-13 v4.1 ile örtüşüyordu. tüm VIX bazlı pozisyon boyutlandırma artık K-13'te

**K-04: SMA trend filtresi (basitleştirilmiş 7 nisan 2026)**

standart kural:
- giriş fiyatı SMA50 üstünde olmalı (en az "yakın trend")
- bu sağlanıyorsa K-13 v4.1 sektör bazlı boyut sınırlarına göre tam pozisyon

istisna (SMA50 altında giriş — sadece oversold bounce için):
- koşul: RSI <30 + son 5 günde stabilizasyon (daha düşük dip yok) + pozitif sektör katalizörü
- boyut: çeyrek pozisyon (max $2.5K swing'de)
- stop: yakın swing low altı (sıkı, geniş değil)
- süre: 3-5 gün max, hızlı çıkış. bounce gelmezse stop ya da süre ile çık
- ilişkili: K-15a (RSI <35 oversold girişleri)

çift kırmızı bayrak (giriş kesin yasak):
- SMA50 + SMA200 altı + insider 30g satış yoğun (K-18 ile birlikte)
- bu durumda hiçbir koşulda giriş yapma — K-04 ve K-18 kesişimi
- kanıt: CRDO 10-17 mart 2026 (-%8.77, SMA altı + 365 insider satış)

repo verisi (n=22 swing test, 7 nisan 2026):
- SMA50+200 üstü (n=16): win rate %62, ort P/L +%0.67
- SMA50+200 altı (n=4): win rate %50, ort P/L -%1.43
- ortalama getiri belirgin biçimde negatif ama "yasak" değil, koşullu istisna açık
- kanıt 1: CRDO 10-17 mart -%8.77 (insider + SMA altı çifte bayrak)
- kanıt 2: SOFI -%3.62 (momentum kaybı + SMA altı)

**K-05: kazanç açıklaması koruma (basitleştirilmiş 7 nisan 2026)**

TEK KURAL: swing pozisyonu, kazanç açıklamasından 2+ işlem günü önce çıkılır. kâr/zarar fark etmez. binary gap riski alınmaz.

uygulama detayı:
- swing trade: 2+ gün önce kapanış, exception yok
- pozisyon trade (uzun vadeli): K-16 sell-the-news skoruna göre yönetilir, K-05 burada müdahale etmez
- LEAPS: bu dosyada "LEAPS YÖNETİM KURALLARI" bağımsız bölümünde ayrıntılı (7 nisan 2026'da eklendi)

PEAD GİRİŞİ (eski Aşama 2): KALDIRILDI
- gerekçe 1: Subrahmanyam (UCLA, ocak 2026) 2001-2024 ABD verisinde drift faktörü microcap dışlandığında t-istatistiği 1.43 ile anlamsız. PEAD ABD'de sadece NYSE alt %20 microcap'te var. portföy evrenimiz mid/large-cap → uygulanamaz
- gerekçe 2: SWING_SYSTEM_V2.md PEAD bölümü açıkça "henüz backtest edilmedi" notu taşıyor. hiç test edilmemiş bir kural ölü kuraldır
- gerekçe 3: closed.json'da hiç PEAD girişi yok, kanıt yok
- gerekçe 4: Martineau (2022) decimal trading + 2005 HFT regülasyonu sonrası PEAD'in çoğu hisse için "öldüğünü" gösterdi. CFA Institute (mayıs 2025) generatif AI'nın drift'i daha da sıkıştıracağını öngörüyor

TEDARİK ZİNCİRİ YAYILIM (eski Aşama 3): KALDIRILDI
- gerekçe 1: formal akademik literatürde "supply chain spillover" anomalisi yok. sezgisel gözleme dayalı bir kuraldı
- gerekçe 2: repo verisi karşı — 3 trade alındı, 1 küçük kâr (COHR +%4.93) + 2 zarar (CRDO -%8.77, MRVL -%3.80), ortalama -%2.55
- gerekçe 3: 3 hisse aynı sektörden aynı haftada → kendi K-17 korelasyon kuralını ihlal ediyordu
- gerekçe 4: gerçek sebep yayılım değil hisseye özgü olaylar (CRDO insider, MRVL Microsoft-AVGO geçişi, COHR Bain blok satış)

kanıt: NVDA swing +%2.88 (12-23 şubat 2026) — earnings öncesi kâr realizasyonu doğru strateji uygulaması. swing'de kazanç açıklamasına maruz kalmamak +%3.4 potansiyel kâr koruması sağladı. bu Aşama 1'in tek ve yeterli kanıtı

### çıkış kuralları

**K-06: stop disiplini (sertleştirilmiş 7 nisan 2026)**

ANA KURAL: stop tetiklendiğinde ÇIKIŞ. tartışma, istisna, koşul yok.

stop hesaplama (zorunlu):
- ilk giriş stop'u: max(2×ATR(14), %5) — sabit %5 tek başına yetersiz
- chandelier exit (3×ATR trailing) açıldıktan sonra K-07 devralır
- ATR hesaplaması zorunlu, "öneri" değil

OVERRIDE: yasak. istisnasız.
- "tez sağlam, biraz daha bekleyeyim" trader'ın en pahalı 4 kelimesidir
- önceki 4 koşullu istisna (teknik destek + ayrışma + tez + %2 alt stop) kaldırıldı
  - 4 koşulun 3'ü öznel, "tez sağlam" confirmation bias için açık kapıydı
  - "1 kez izin" sınırı LASR vakasında 3 kez ihlal edildi, pratikte çalışmadı

K-09 İLE İLİŞKİ: K-09 stop tetiklenmeden önceki hareketi yönetir (yakınlık erken çıkışı), K-06 tetik anında çalışır. çakışma yok, sıralı tamamlayıcı.

REPO KANITI (closed.json swing testi 7 nisan 2026):
- disipline uyulan 8 trade: RTX -%5.16, CEG -%5.05, T -%5.54, AMT -%3.35, GE +%1.68 (kâr koruma), ALMU -%6.11, SOFI -%3.62, AROC -%4.95
- hard zarar yok, hepsi -%6 ve altında, düzgün boyutlandırılmış stop
- ihlal vakası (aggressive portföy): LASR 3-16 mart, 3x override, breakeven dönüş (şans eseri kurtuluş, gelecek için garanti değil)

LİTERATÜR DESTEĞİ:
- TradeFundrr (2025): stop'u taşıyan trader'ların ortalama kaybı taşımayanlardan %40 daha büyük
- TradingMetrics: "stop'u taşımak risk yönetimi değil, risk kaçınmasıdır; risk kaçınması her zaman daha büyük kayıplara yol açar"
- mental stop yerine her zaman gerçek stop emri kullan (override fırsatını ortadan kaldır)

**K-07: trailing stop disiplini (sadeleştirilmiş 7 nisan 2026)**

ANA KURAL: trailing stop tetiklendiğinde ÇIKIŞ. sorgulama yok, ASLA bozulmaz. K-06 ile aynı disiplin felsefesi.

SWING TRADE: chandelier exit + kâr kilidi sistemi (matematiksel sıkılaştırma)
- kâr <%7: chandelier 3×ATR(14)
- kâr %7-15: chandelier 2×ATR (kâr kilidi devreye girer)
- kâr %15+: chandelier 1.5×ATR (agresif kilit)
- detaylar: docs/SWING_SYSTEM_V2.md

POZİSYON TRADE (uzun vadeli portföy): 50SMA günlük kapanış altı VEYA ichimoku kumo altı kapanış

YENİ GİRİŞ: trailing tetiklenen pozisyon yeni bir sinyal verirse tekrar girilebilir. "intikam trade'i" değil, yeni trade olarak değerlendirilir ve kendi K-04/K-13/K-17/K-18 kontrollerinden geçer.

ÇAKIŞMA AÇIKLAMASI:
- "VIX yükselince sıkılaştır" → K-13 v4.1 yönetir (sektör bazlı VIX)
- "Earnings yaklaşınca sıkılaştır" → K-05 yönetir (2+ gün önce çık)
- "Sektör zayıflayınca sıkılaştır" → K-20 yönetir
- K-07 ek manuel sıkılaştırma kuralı içermez. kâr kilidi zaten matematiksel sıkılaştırma yapıyor

REPO KANITI (n=10 trailing exit, 8 bilinen sonuç, 7 nisan 2026):
- Kazanç (5): TYL +%11.19, COHR +%4.93, KOS +%39 kısmi, NEM +%2.13, ZS +%2.55
- Zarar (3): RKLB -%11.59, VRT -%9.7, POWL -%10.63
- Win rate %62 (5/8)
- ÖNEMLİ NÜANS: 3 zararın hepsi K-07 başarısızlığı değil, giriş zamanlama ihlali sonucu:
  • RKLB → K-15b (momentum hisselerinde arz/dilüsyon riski)
  • VRT  → K-13b ihlali (VIX 29+ ortamında AI tema tam pozisyon)
  • POWL → K-13b + K-18 ihlali (insider $25M satış kontrol edilmedi)
- Bu trade'lerde trailing stop "kâr kilidi" değil "kayıp limiti" görevi yaptı, beklendiği gibi çalıştı

LİTERATÜR: Charles Le Beau chandelier exit standardı (22 periyot, 3×ATR varsayılan). choppy/range piyasada whipsaw riski var, kâr kilidi sistemi bu durumda devreye girer. tech-ağırlıklı portföylerde 3×ATR yeterince esnek (StockCharts: tech için 3-5x aralığı önerilir)

**K-08: KALDIRILDI** — 7 nisan 2026 değerlendirmesinde geri çekildi. gerekçeler:
- repo verisi tezi çürüttü: 15+ gün tutulan 8 trade win rate %75 / ort P/L +%1.51, 8-14 gün tutulan 7 trade win rate %57 / ort P/L -%0.80. "15g fazla" iddiası yanlıştı, kazananları uzun tutmak daha iyi sonuç veriyor
- ölü kod: 3 aşamalı v1 filtresi "sadece v1 için" notuyla pratikte hiç çalışmıyordu, Swing v2.3'te chandelier zaten momentumu yönetiyor
- K-07 ile çakışma: chandelier stop momentum kaybında zaten çıkış sağlıyor, K-08'in "momentum kontrol" maddesi gereksiz ikinci katman
- kanıt zayıf: T (-%5.5) zaman değil tez sorunu (savunmacı tez yanlıştı), LMT (+%1.43) "süre aşımı" diye etiketlenmişti ama trade KÂR etti
- akademik destek sınırlı: time stop ana çıkış değil, hibrit yedek olarak işe yarar (QuantifiedStrategies ocak 2026)
- fırsat maliyeti kaygısı haklıydı (DUK 28g +%1.52 = günde %0.054) ama bunun için ayrı kural gerekmez, manuel gözden geçirme yeterli

**K-09: stop yakınlığı erken çıkış protokolü (güncellenmiş 7 nisan 2026)**

TETİK: fiyat stop'a ≤%2 mesafede ise 4 kontrol değerlendirilir

4 KONTROL (her biri "negatif" veya "nötr" işaretlenir):
1) RSI yönü: düşüyor + 40 altı → negatif
2) Hacim profili: satış baskısı > alış baskısı → negatif
3) Piyasa: SPY günlük negatif + VIX yükseliyor → negatif
4) Sektör: ilgili ETF günlük negatif → negatif

KARAR EŞİKLERİ:
- 3+ negatif → stop beklemeden ÇIKIŞ
- 2 negatif → stop'u bekle (otomatik çıkış yok)
- 0-1 negatif + toparlanma sinyali (hammer mum, hacim sıçraması) → tut (kuvvetli)
- 0-1 negatif + toparlanma sinyali YOK → tut (zayıf), izlemeye devam

ESNEKLİK NOTU: %2 mesafe katı bir eşik değil, "stop bölgesi" yaklaşımı. Pratik uygulamada %0.06 (AROC) ile %1.7 (AMT) arası tetikleme yapılmış. Kural: ne kadar yakınsa karar o kadar acil.

OTOMASYON:
- Script: scripts/k09_proximity_check.py (her seans canlı izleme)
- Telegram alert: stop'a ≤%2 kala otomatik (--type alert)
- Manuel karar gerekli, alert otomatik çıkış değildir

K-06 İLE İLİŞKİ: K-09 tetik öncesi, K-06 tetik anında. çakışma yok, sıralı tamamlayıcı.
K-07 İLE İLİŞKİ: K-07 trailing seviyesini matematiksel ayarlar, K-09 stop yaklaştığında durum değerlendirir.

REPO KANITI (n=6 K-09 uygulaması, closed.json swing testi 7 nisan 2026):

KÂR KORUMA (en önemli katma değer):
- GE +%1.68 (13g sonra -%3 günlük düşüş, kâr korunarak çıkış)
- CTSH +%1.45 (RSI 33, momentum hiç gelmedi, stop beklemeden çıkış)

ZARAR KÜÇÜLTME:
- AMT -%3.35 (%1.7 mesafe, zarar limiti)
- SOFI -%3.62 (%1.3 mesafe, RSI 34.2, downtrend devam)
- AROC -%4.95 (%0.06 mesafe, gün içi ihlal)
- ALMU -%6.11 (sert düşüş, hard stop beklemeden)

KARŞILAŞTIRMA (K-09 vs normal stop tetik):
- K-09 erken çıkış (n=6): 2 kâr koruma + 4 zarar küçültme, ort -%2.48
- Normal stop tetik (n=3): CEG -%5.05, T -%5.54, RTX -%5.16, ort -%5.25
- K-09'un ASIL katma değeri: kazanan trade'leri (GE, CTSH) zarara dönmeden korumak
- İkincil katma değer: zarar büyüklüğünü ortalama %0.74 azaltmak

### portföy yönetimi kuralları

**K-10: VIX bazlı savunmacı allokasyon kuralı (netleştirilmiş 7 nisan 2026)**

KAPSAM: 3 ana portföyün TOPLAM değeri ($600K bazlı) üzerinden hesaplanır. swing trade hariç (kısa vadeli, ayrı bütçe).

EŞİKLER (K-13 v4.1 ile aynı VIX bantları):
- VIX <22 (sakin/normal): min %25 savunmacı + nakit
- VIX 22-28 (dikkatli): min %35 savunmacı + nakit
- VIX 28-35 (gergin): min %45 savunmacı + nakit, agresif pozisyonları küçült
- VIX 35+ (panik): min %55 savunmacı + nakit, agresif'te sadece mevcudu yönet

SAVUNMACI TANIMI (3 koşuldan EN AZ 1 sağlanmalı):
1) Temettü yield >%2.5
2) Beta <1.0
3) Defansif sektör (utilities/temel tüketim/sağlık/telekom)

NAKİT MUAMELESİ: nakit "savunmacı + nakit" toplamına dahildir. nakit kayıp riski olmayan en savunmacı varlıktır, savunmacı oranına sayılır.

ENERJİ İSTİSNASI: çatışma dönemlerinde enerji sektörü saldırgan olabilir. K-13 v4.1 faydalanıcı listesinde değerlendirilir, K-10 savunmacısı sayılmaz ama K-13 boyut izinleri korunur.

K-13 v4.1 İLE İLİŞKİ:
- K-10 PORTFÖY SEVİYESİ yüzde yönetir (statik koruma alt sınırı)
- K-13 v4.1 SEKTÖR SEVİYESİ giriş/boyut yönetir (dinamik tepki)
- iki kural çakışmaz, paraleldir: K-10 alt sınır koyar, K-13 sektör seçer

ÖLÇÜM PROTOKOLÜ:
- her seans öncesi summary.json'dan toplam değer ve nakit oranı çekilir
- yatırılı pozisyonların savunmacı tanımına göre sınıflandırılması yapılır
- VIX rejimine göre minimum karşılaştırılır
- eksikse: yeni agresif giriş yasak, savunmacı/nakit artırılır

ÖLÇÜM ÖRNEĞİ (mevcut durum 7 nisan 2026):
- toplam portföy: $615K (Dengeli + Agresif + Temettü)
- nakit: $516K (~%86)
- yatırılı savunmacı: T, VZ, MO, PM, JNJ ≈ $50-55K (~%9)
- toplam savunmacı + nakit: ~%94
- VIX 24.83 → "dikkatli" rejim → min %35 gerekli
- durum: ✓ FAZLASIYLA SAĞLANIYOR

LİTERATÜR KANITI:
- HL Hunt institutional research (2025): VIX bazlı dinamik koruma hedging maliyetlerini %40-60 azaltırken eşdeğer korumayı sağlıyor
- Nature 2025 ML çalışması: yüksek vol rejiminde (VIX≥25) defansif allokasyon Sharpe oranını %187 artırıyor, max drawdown'u %45.5 azaltıyor
- ScienceDirect VIX-managed portfolios: önceki ay VIX yüksekken risk azalt basit kuralı istikrarlı performans veriyor
- International Trading Institute (2025): VIX eşikleri pozisyon sizing'de endüstri standardı (sakin altı normal, ortada yarım, üstünde sadece A-setup)

**K-11: kademeli kâr alma sistemi (sadeleştirilmiş 7 nisan 2026)**

KAPSAM: portföy pozisyonları (Dengeli, Agresif, Temettü). swing'de uygulanmaz (swing'de K-07 kâr kilidi: <%7 chandelier 3×ATR, %7-15 2×ATR, %15+ 1.5×ATR)

PRENSİP: RSI 70 OTOMATİK SATIŞ DEĞİL, momentum teyididir. güçlü trendlerde RSI 70+ uzun süre kalabilir. kazananı erken kesme.

3 KATMANLI YAPI:

KATMAN 1 — UYARI MODU (izle, satma):
- Tetik: RSI 70+ VE +%15 kâr
- Aksiyon: KÂR KİLİDİ trailing aktif → max(2×ATR(14), 20SMA altı kapanış)
- Amaç: kâr koruma, çıkış DEĞİL
- K-07 İLE HİYERARŞİ: K-11 katman 1 KÂR KİLİDİ (sıkı 20SMA) önceliklidir. K-07 portföy stop (gevşek 50SMA) sadece K-11 katman 1 inaktif olduğunda (kâr <%15 veya RSI <70) devreye girer. Kazançlı pozisyonda K-11 sıkı, kazançsız pozisyonda K-07 gevşek.

KATMAN 2 — KISMİ KÂR AL (%25-30 dilim):
Tetikler (BİRİ yeterli, basitleştirilmiş — 2 ana tetik):
- (a) RSI 80+ → kısmi sat (en sık kullanılan, baskın tetik)
- (b) RSI 75+ VE bir teyit (negatif divergence YA DA 20SMA altı kapanış)
- Tek dilim kuralı: bir günde max 1 kısmi satış (transaction yığılmasını önle)

KATMAN 3 — KALAN POZİSYON (trend bitene kadar):
- Tetik: 50SMA altı kapanış VEYA 3×ATR(14) trailing kırılım
- Amaç: trend bitişinde tam çıkış

İSTİSNALAR:
- Earnings 5 gün içinde: katman 2 RSI 70+'a düşürülür
- VIX >28: katman 2 RSI 72+'a düşürülür
- LEAPS: katman 2 eşiği RSI 80+ (zaten baskın tetik ile aynı)

POZİSYON BÜYÜTME (yeni eklendi 7 nisan 2026):
- Katman 1 aktif + RSI <80 + 20SMA üstünde + güçlü hacim → "kazananı büyüt" pozisyon büyütme yapılabilir (max %10 ek)
- Örnek: SM 25 mart +160 hisse @ $31.14 (RSI 75, trend devam)

REPO KANITI (n=15+ K-11 uygulaması, closed.json + transactions.csv testi 7 nisan 2026):

SM (Dengeli) — K-11'in en yoğun uygulandığı trade:
- Giriş 17 şubat $21.14 (1040 hisse)
- 9 farklı K-11 kısmi satış: 9-25 mart arası, fiyat $26.50-$30.84
- Tetikler: RSI 72-80 aralığı (baskın olarak (a) RSI 80+ tetiği)
- 25 mart pozisyon büyütme +160 @ $31.14 (kazananı büyüt uygulaması)
- 1 nisan tam çıkış: iran ateşkes (tez bazlı, K-11 dışı)
- Sonuç: ortalama çıkış ~$28-29, %30-40 kâr boyunca yönetildi
- Ders: kademeli çıkış sayesinde tam tepe yakalanamadı ama trend kaçırılmadı

KOS (Dengeli) — parçalı ideal:
- Giriş $1.67, 27 şubat-9 mart arası 5 kısmi satış
- Çıkış aralığı $2.25-$2.58, ~%35-%55 kâr

VZ (Temettü) — kısmi kâr:
- 25 şubat 156 hisse @ $49.51, RSI 73, +%24 kâr realize

CELH, TYL, COHR, CRDO, MU (Agresif) — earnings rally + katalist tabanlı kademeli çıkışlar. K-11 kuralı doğru uygulandı.

KANIT DÜZELTMESİ (önemli): Önceki kanıt iddiası "SM RSI 74 → ertesi gün -%4.38" YANLIŞTI. SM gerçekte RSI 74 sonrası yükselmeye devam etti ($27.36 → $30.84). K-11'in asıl başarısı "RSI 70'te tamamen sat" hatasını önlemek, kademeli çıkışla trendi kaçırmamaktı.

LİTERATÜR:
- Capital.com / NusaTrader / Goat Funded Trader: RSI güçlü trendlerde 70+ uzun süre kalabilir, her 70'i aştığında satmak kaçırılmış fırsat yaratır
- Kraken: hidden bullish divergence (price higher low, RSI lower low) trend devam sinyali
- LuxAlgo: ATR bazlı çoklu hedef + ilk hedef sonra trail endüstri standardı

**K-12: pozisyon konsantrasyon limitleri (netleştirilmiş 7 nisan 2026)**

KAPSAM AYRIMI: hisse limitleri PORTFÖY BAZLI, sektör limiti TOPLAM bazlı

HİSSE LİMİTLERİ (her portföy kendi değeri içinde):
- Dengeli (max 6 pozisyon, $100K): tek hisse max %25 portföy ağırlığı
- Agresif (max 10 pozisyon, $400K): tek hisse max %20 portföy ağırlığı
- Temettü (max 15 pozisyon, $100K): tek hisse max %15 portföy ağırlığı

GEREKÇE (pozisyon sayısı × eşit ağırlık matematiği):
- Dengeli 6 pozisyon eşit ağırlık = %16.67 → %25 limit (eşit + esneklik)
- Agresif 10 pozisyon eşit ağırlık = %10 → %20 limit (eşit + esneklik)
- Temettü 15 pozisyon eşit ağırlık = %6.67 → %15 limit (eşit + esneklik)
NOT: Önceki K-12 metnindeki sabit %15 limiti Dengeli portföy ile mantıken çelişiyordu (6 eşit pozisyon zaten %16.67). Bu tutarsızlık 7 nisan 2026'da düzeltildi.

OPSİYONLU HİSSE: hisse + opsiyon (delta ayarlanmış efektif maruziyet) → yukarıdaki limitler +%5 toleransla uygulanır (Dengeli %30, Agresif %25, Temettü %20)

LEAPS EFEKTİF MARUZİYET HESABI:
- formül: kontrat sayısı × 100 × delta × strike
- örnek: 6 MU call × 100 × 0.55 × $87.93 ≈ $29K
- LEAPS pozisyonu portföy bazında "hisse" gibi sayılır

SEKTÖR LİMİTLERİ (TOPLAM $600K bazlı) — netleştirildi 7 nisan 2026:

İKİ AYRI LİMİT, AYRI AYRI UYGULANIR:

a) GICS SEKTÖR LİMİTİ: tek GICS sektörü max %40
   • Örnek: XLK (tüm tech) toplam max %40
   • Veri: SPY sektör sınıflaması (11 sektör)

b) ANLATI BAZLI TEMA LİMİTİ: tek anlatı teması max %40
   • Örnek: AI tedarik zinciri (NVDA + MRVL + COHR + POWL + CAMT + VRT) toplam max %40
   • Tema tanımı: K-17'deki 3 soru testi (makro hikaye / katalist / senaryo)
   • Bir hisse hem GICS hem tema sayımına girer (çift sayım kasıtlı, korelasyon yönetimi)

K-17 İLE ENTEGRASYON: K-17 anlatı bazlı tema tanımını sağlar, K-12 limit eşiğini sağlar (%40 ortak).

CROSS-PORTFÖY: aynı sektör/tema birden fazla portföyde varsa toplanır.

CROSS-PORTFÖY HİSSE TAKİBİ:
- aynı hisse birden fazla portföyde varsa her portföy kendi limitini ayrı kontrol eder
- AMA toplam $600K bazında ek bilgi olarak takip edilir
- Toplam >%10 → bilinçli karar (şirkete özgü risk: kazanç miss, regülatör eylemi iki portföyü birden vurur)
- Mevcut örnek: MO hem Dengeli ($17.8K) hem Temettü ($14.5K), toplam $32.3K = %5.25 → izleme altında

AŞIM YÖNETİMİ:
- portföy %25/%20/%15 aşıldı → 1 hafta içinde kısmi satış
- portföy +%5 üstü (yani %30/%25/%20) aşıldı → aynı/ertesi gün kısmi satış
- sektör %40 aşıldı → en zayıf pozisyonu küçült veya kapat
- haftalık kontrol pazar günleri zorunlu (summary.json + portföy ağırlıkları)

MEVCUT DURUM (7 nisan 2026):
- T (Temettü): $24.3K / $144.8K = %16.80 → ⚠️ %15 limiti +1.80 aşıldı, 1 hafta içinde kısmi satış GEREKLİ
- MO (Dengeli): $17.8K / $112K ≈ %15.9 → %25 limitin altında ✓
- Diğer hisseler tüm portföylerde limit altında
- Sektör bazlı toplam: hiçbir sektör %40'ı aşmıyor (telekom %4.81, tütün %4.37, tüm sektörler düşük çünkü %86 nakit)

LİTERATÜR KALIBRASYONu:
- Guardfolio (2026 ocak): retail için tek hisse %5-10 öneriliyor, sektör %25-30
- Charles Schwab: tek hisse %10-20 üstü "aşırı konsantrasyon riski"
- JP Morgan Private Bank: %10-20 yaygın eşik ama esnek yorumlanır
- Darrow Wealth Management: tek hisse %10 üstü "muhtemelen çok fazla"
- K-12'nin %15-25 portföy bazlı limiti retail'in orta gevşek tarafında, pozisyon sayısı limitleri ile birlikte mantıklı kalibrasyon

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
  - staples/tütün: MO, PM, PG, KO, PEP, CL (NOT: K-19 nedeniyle SADECE portföy pozisyonu olarak alınabilir, swing yasak)
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
  - K-13b SPESİFİK BACKTEST: kriz modunda 11 kâr / 2 zarar = %85 başarı (n=13, mart 2026 dönemi)
  - SWING SİSTEM GENEL BACKTEST (61 dönem 2021-2026, K-13b dahil tüm 4/4 sinyaller): 2024 %100, 2026 %85, 2025 %74, 2021 %50, 2022 %40, 2023 %30
  - İKİ FARKLI SAMPLE: %85 K-13b kriz modu (n=13), yıl bazlı dağılım swing genel (n=184)
  - K-13b piyasa rejimine duyarlı: sakin yıllarda az kullanılır, kriz modu en güvenilir
  - kapsam: SADECE duyarlı sektörler (faydalanıcılar K-13 ile zaten izinli)
  - boyut: VIX 28-35 → çeyrek pozisyon ($2.5K). VIX 35+ → giriş yok
  - 6 koşul TÜMÜ:
    1) ichimoku tam 4/4 (kumo üstü + TK bull cross + tenkan üstü + volume 5g/20g >1.3x)
    2) sektör ETF 9EMA + 21EMA üstü (XLK, XLE, XLI, XLC, XLV, XLF, XLY, XLU, XLB, XLRE) — XLP kaldırıldı (K-19 önceliği), XLRE eklendi (K-20 ile tutarlılık)
    3) mcap >$2B
    4) RSI 40-70
    5) K-18 temiz (30g CEO/CFO satışı yok)
    6) K-17 korelasyon >%50
  - güvenlik:
    a) stop: chandelier (highest_high − 3×ATR(14)). sabit %5 cap YOK (K-06 ANA KURALDAN FARKI: K-06 normal swing'de min %5 garanti eder, K-13b kriz modu istisnası daha geniş chandelier kullanır çünkü VIX 28+'da volatilite zaten yüksek)
    b) çıkış: Swing v2.3 kâr kilidi (<%7: 3×ATR, %7-15: 2×ATR, %15+: 1.5×ATR). sabit hedef YOK
    c) max 2 eşzamanlı, sektör başına max 1
    d) o gün >%3 yükselmişse girme (kovalama yasağı)
  - iptal: VIX 1 günde >%15 yükselirse istisna pozisyonları yarıya
  - izleme: trade log'da "K-13b istisnası" etiketi. 10 trade sonra <%60 ise istisna kaldırılır
- mevcut durum (7 nisan 2026): VIX 24.83, "dikkatli" rejim. faydalanıcılarda tam, duyarlılarda yarım pozisyon. K-13b inaktif (VIX <28).
- NİSAN 2026 ATEŞKES GEÇİŞİ: 6 nisan ateşkes haberleri, savunma sektörü "sell on the news" düzeltmesi başladı (LMT, NOC, RTX). K-13'ün "VIX zirvesinden %20 düştü → duyarlı sektörlere kademeli geri dönüş" kuralı aktivasyon eşiğine yaklaşıyor. İran krizi tezi zayıflıyor, jeopolitik kriz tablosu güncellemesi yakında gerekebilir.

K-12 İLE BOYUT ÇAKIŞMASI ÇÖZÜMÜ:
- "Tam pozisyon" = K-12 portföy bazlı limit (Dengeli %25, Agresif %20, Temettü %15)
- "Yarım pozisyon" = K-12 limitin yarısı (Dengeli %12.5, Agresif %10, Temettü %7.5)
- "Çeyrek pozisyon" = K-12 limitin çeyreği (Dengeli %6.25, Agresif %5, Temettü %3.75)
- K-13b istisna pozisyonu boyut: VIX 28-35'te çeyrek (yukarıdaki çeyrek seviyelerinde)

K-10 İLE İLİŞKİ (çift yönlü):
- K-10 PORTFÖY SEVİYESİ savunmacı/nakit alt sınır koyar (statik, VIX bandlı)
- K-13 SEKTÖR SEVİYESİ giriş/boyut yönetir (dinamik, kriz tipine bağlı)
- İki kural çakışmaz, paraleldir: K-10 alt sınır + K-13 sektör seçimi

LİTERATÜR DESTEĞİ (7 nisan 2026 araştırması):
- MSCI Multi-Asset Playbook (mart 2026): jeopolitik krizde defansif sektörler (enerji, staples, sağlık, utilities) outperformance, enerji en yüksek aktif getiri → K-13 jeopolitik tablosu doğrulandı
- PMC Geopolitical risk contagion (2025): savunma + siber defansif varlık, enerji + raw materials sensitive → K-13 sektör listesi doğrulandı
- FinancialContent (6 nisan 2026, 1 gün önce): savunma "sell on the news" düzeltmesi → K-13b geri dönüş kuralı şu an aktif olabilir
- Ecconomi (mart 2026): retail en büyük hata "şok aşamasında savunma/enerji kovalamak" → K-13b "o gün >%3 yükseldi → girme" kuralı bunu yansıtıyor
- JP Morgan / BlackRock Geopolitical Risk Dashboard: VIX-Geopolitical Risk Index zayıf korelasyon, sektör bazlı yönetim gerekli → K-13 "blanket VIX engeli yanlış" mantığı doğrulandı

**K-14: kayıp serisi yönetimi (drawdown fren) — netleştirilmiş 7 nisan 2026**

KAPSAM: swing trade (sadece). portföy pozisyonları için ayrı drawdown fren yok — K-10 (allokasyon alt sınır) + K-11 (kademeli kâr) + K-13 (sektör boyut) + K-12 (konsantrasyon limit) birlikte yönetir. K-14 specifik olarak swing kayıp serisi içindir.

TANIMLAR (netleştirildi):
- Ardışık zarar: takvim bazlı değil, swing trade ÇIKIŞ SIRASINA göre
- Drawdown ölçümü: peak-to-trough (literatür standardı), başlangıç sermayeye değil
- Standart swing boyutu: $5K-$10K (mevcut aralık)
- A-kalite trade tanımı (yeni eklendi):
  • İchimoku 4/4 (kumo+TK+tenkan+volume)
  • Sektör ETF lider (XLK/XLE vb. 9EMA+21EMA üstü)
  • RS pozitif (sektör/SPY 20g+ trend)
  • K-13 faydalanıcı sektör VEYA K-13b 6 koşulları
  • K-17 korelasyon ihlali yok
  • K-18 insider temiz

KADEMELİ FREN:
- 2 ardışık zarar → boyut %25 küçült
  • Standart $10K → $7.5K
  • Standart $5K → $3.75K
- 3 ardışık zarar → boyut %50 küçült + SADECE A-kalite
  • Standart $10K → $5K
  • Standart $5K → $2.5K
- 4+ ardışık zarar → TAMAMEN DUR, min 1 hafta swing yok
- Toplam swing drawdown %15+ (peak-to-trough) → DUR, ortamı değerlendir

YENİDEN BAŞLAMA PROTOKOLÜ (v2.1 — 10 nisan 2026):

1) Min 1 iş günü soğuma

2) Zorunlu kayıp analizi — her kayıp trade için 3 kategori (soğuma sonrası da yapılabilir):
   - ORTAM: Giriş anında VIX ve SPY SMA50 durumu neydi? K-13 uyumlu muydu?
   - SİSTEM: İchimoku 4/4 tam mıydı? Hangi katman eksikti?
   - PSİKOLOJİ: Kovalama, revenge veya kural dışı giriş var mıydı?

3) Normal boyutla devam ($5K-$10K) — SADECE A-kalite setup

GİRİŞ ÖNCESİ PSİKOLOJİ TESTİ (her trade için, tek soru):
"Bu girişi yarın tekrar inceleseydim, tüm kuralları tam uyguladım mı?"
→ Cevap net değilse veya tereddüt varsa: giriş yapma.

ORTAM TESTİ (K-13'e göre):
- Faydalanıcı sektörlerde VIX <28 + SPY SMA50 üstü
- Duyarlı sektörlerde VIX <22 + SPY SMA50 üstü + sektör rotasyonu pozitif
- Bu koşullar sağlanmadan swing'e dönülmez

OTOMATİK TAKİP (yeni eklendi):
- Script: scripts/k14_drawdown_track.py (her swing kapanışında otomatik çalışır)
- 2 ardışık zarar → telegram alert ("K-14 katman 1: boyut %25 küçült")
- 3 ardışık zarar → telegram alert ("K-14 katman 2: boyut %50 + A-kalite")
- 4 ardışık zarar → telegram alert ("K-14 STOP: 1 hafta swing yok")
- swing drawdown %15 → telegram alert ("K-14 drawdown stop")

REPO KANITI VE KRİTİK DERS (mart 2026):

DOĞRU SAYIM (closed.json testi 7 nisan 2026):
- 9 mart HAL -%5.10
- 9 mart CEG -%5.05
- 11 mart T -%5.54  ← 3 ardışık zarar TAMAM
- 11 mart CTSH +%1.45 (seriyi kırdı, 4 ardışık olmadı)
- 12 mart ALMU -%6.11 (yeni başlangıç, ama K-14 hâlâ aktif olmalıydı)
- 12 mart SOFI -%3.62 (24 şubat girişi, 12 mart çıkışı)
- 9-12 mart penceresi: 5 zarar / 6 trade

KRİTİK DERS:
- K-14 UYGULANMADI! 3 ardışık zarardan sonra (HAL/CEG/T 9-11 mart) boyut %50 küçültülmeliydi
- ALMU (12 mart girişi) standart boyutta açıldı → K-14 katman 2 ihlali
- closed.json'da K-14 etiketi yok → kayıt yetersiz
- Memory iddiası "4/5 zarar serisi" yanlış formülasyon — gerçek 3 ardışık + 2 ek
- BU OLAY OTOMATİK TAKİP VE TELEGRAM ALERT İHTİYACININ KANITI

LİTERATÜR DESTEĞİ:
- Quant.fish: drawdown bazlı kademeli kesim (5%/10%/15% → 10/25/50)
- Edgeful (matematik): %60 win rate'te 3 ardışık zarar olasılığı %100, normal varyans
- Atmos Funded: 2 zarar sonrası mola + sadece A-setup, K-14 ile uyumlu
- Quantvps: 3-5 ardışık zarar sonrası mola endüstri standardı
- TradingMetrics: psikolojik kırılma matematiksel kırılmadan önce gelir
- K-14 literatür orta sıkılığında, makul kalibrasyon

### giriş öncesi filtreler

**K-15a: RSI <35 oversold girişinde dikkat — netleştirilmiş 7 nisan 2026**

KAPSAM: swing ve agresif portföy (giriş öncesi filtre)

KURAL:
- RSI 14 günlük < 35 olan hisselerde anlık giriş YASAK
- Min 1 gün teyit bekle, teyit sinyalleri (BİRİ yeterli):
  • RSI dönüş: dün RSI <35, bugün RSI yukarı dönüyor (artıyor)
  • Hammer mum + yükselen hacim (>20g ortalama 1.3x+)
  • Gün içi düşük teste rağmen kapanış üstünde
- "Düşen bıçağı tutma" prensibi: yön belirsizken alma

İSTİSNALAR:
- K-04'TEN AYRI: K-15a SMA50 ÜSTÜ için (mean reversion trend içinde), K-04 SMA50 ALTI için (oversold bounce). İki kural ters senaryolar, RSI eşikleri farklı (K-04: <30 daha sıkı çünkü trend bozuk, K-15a: <35 daha gevşek çünkü trend sağlam).
- K-15a SMA50 üstü senaryosu: çeyrek pozisyon ile giriş izinli, 1 gün teyit gerekli
- K-13 faydalanıcı sektör + RSI <35 → güçlü alım sinyali (teyit ile)

REPO KANITI (n=4 closed.json testi 7 nisan 2026):
- CTSH RSI 22.5 (24 şubat) → +%1.45 ✓ KAZANÇ
- ZS RSI 26.7 (24 şubat) → +%2.55 ✓ KAZANÇ
- NEM RSI 31.4 (24 mart) → +%4.18 ✓ KAZANÇ
- SOFI RSI 27.8 (24 şubat) → -%3.62 ✗ ZARAR (K-04 ihlali, SMA50 altı)
- Win rate: 3/4 = %75. Çekirdek kural çalışıyor.

KRİTİK DERS: 24 şubat'ta CTSH/ZS/SOFI 3 hisse AYNI GÜN girildi. K-15a "1 gün teyit" uygulanmadı. SOFI tek zararı oldu - 1 gün teyit muhtemelen engellerdi. Bu olay K-15a + K-04 birlikte uygulanmasının önemini gösteriyor.

**K-15b: momentum hisselerinde dilüsyon + arz riski — netleştirilmiş 7 nisan 2026**

KAPSAM: swing ve agresif portföy. momentum hisse girişi öncesi zorunlu skor.

MOMENTUM HİSSE TANIMI (net):
- Son 3 ay >%30 ralli VE
- (P/E negatif VEYA P/E >50)
- Tipik örnek: RKLB, PLTR, BKSY, NNDM, GILT, AI/quantum/space sektör hisseleri

DİLÜSYON RİSK SKORU (her madde +1):
1) Negatif FCF (son 4 çeyrek)
   • Veri: FMP cash-flow-statement, "freeCashFlow" alanı
2) Borç/Öz sermaye >1.5
   • Veri: FMP balance-sheet, totalDebt / totalStockholdersEquity
3) Son 12 ay hisse arzı yapılmış
   • Veri: FMP shares-float değişimi VEYA SEC EDGAR S-1/S-3
4) Aktif shelf registration (SEC S-3)
   • Veri: SEC EDGAR full-text arama VEYA dilutiontracker.com
5) Büyük CapEx planı + finansman belirsiz
   • Veri: 10-K MD&A VEYA earnings call transkript

KARAR EŞİKLERİ:
- Skor 0-1: normal pozisyon (standart $5K-$10K)
- Skor 2-3: max %2 portföy ağırlığı (Dengeli $2K, Agresif $8K)
- Skor 4-5: girme YA DA sadece opsiyon ile sınırlı risk (max $1K premium)

OTOMATİK KONTROL (yeni eklendi):
- Giriş öncesi script çalışır: scripts/k15b_dilution_check.py SYMBOL
- Skor + telegram alert ("K-15b SCORE:3 SYMBOL → max %2 ağırlık")
- Manuel skor hesaplama riski (memory yanlış olabilir, RKLB örneği)

REPO KANITI (REVİZE 7 nisan 2026):
- ESKİ İDDIA: "RKLB -%11.59" → YANLIŞ
- GERÇEK RKLB: $68.44 giriş × 146 hisse, 17 mart kısmi kâr 96 hisse @ $77.53 (+%13) + 20 mart trailing stop 50 hisse @ $67.61 (-%1) = NET +%8 portföy. RKLB KÂR ETTİ.
- closed.json'da K-15b etiketli swing trade YOK
- K-15b başka momentum hisselerinde (PLTR, BKSY, NNDM, GILT) uygulanma KAYDI YOK
- Bu durum otomatik script ihtiyacının kanıtı

K-15a İLE İLİŞKİSİ:
- K-15a TIMING riski (kısa vade, RSI bazlı)
- K-15b YAPISAL risk (uzun vade, bilanço bazlı)
- İkisi birlikte: oversold momentum hisse + dilüsyon = ÇİFT KIRMIZI BAYRAK
- Örnek: hipotetik RKLB RSI 30 + shelf registration → K-15a 1g teyit + K-15b skor 4-5 = girme

LİTERATÜR DESTEĞİ:
- DilutionTracker: shelf registration küçük cap + nakit yakım + adil değer üstü → ek hisse ihraç olasılığı yüksek, fiyat üzerinde aşağı baskı
- HeyGotrade: %5-10 yıllık hisse artışı bile anlamlı dilüsyon, EPS basıncı
- Lord Abbett: value trap kavramı, quality + value + momentum kombinasyonu daha etkili, ROIC ana dayanıklılık göstergesi
- Quant Investing (12 yıl Avrupa çalışması): yüksek FCF + momentum kombinasyonu sadece FCF'ye göre %506 iyileşme - K-15b "negative FCF momentum" doğru kırmızı bayrak

**K-16: sell the news riski değerlendirmesi — netleştirilmiş 7 nisan 2026**

KAPSAM: SADECE portföy pozisyonları (Dengeli, Agresif, Temettü). swing trade için K-05 geçerli (kazançtan 2+ gün önce TAM çıkış).

NEDEN PORTFÖY: portföy pozisyonları uzun vadeli, kademeli çıkış mantıklı. swing kısa vadeli, tam çıkış zaman tasarrufu sağlar.

5 MADDELİK SKOR (her madde +1):
1) Hisse kazanç öncesi 5 günde %5+ ralli (beklenti fiyatlanmış)
   • Veri: FMP historical-price-eod son 5 gün
2) Consensus EPS son 3 ay %10+ yükseltilmiş (çıta yüksek)
   • Veri: FMP analyst-estimates revisions
3) 52w zirveye %5 mesafe (yukarı alan dar)
   • Veri: FMP historical-price-eod 52w high
4) Sektör son 1 ay %10+ ralli
   • Veri: FMP sector-performance-snapshot
5) Short interest %10+ float
   • Veri: FMP key-metrics shortFloat

KARAR EŞİKLERİ:
- Skor 0-1: normal tut, kazanç sonrası izle
- Skor 2-3: kazanç öncesi %25 kısmi al + trailing sıkılaştır (K-11 aktif et)
- Skor 4-5: kazanç öncesi %50 kısmi çık, post-earnings bekle

TEDARİK ZİNCİRİ ORTAKLARI NÜANSI (önemli):
- Sell-the-news hisseye özgüdür, tedarik zinciri ortaklarına yayılmayabilir
- Örnek: MU sell-the-news → CRDO/MRVL/COHR doğrudan etkilenmez
- Ortaktaki geri çekilme ALIM FIRSATI olabilir (sektör tezi sağlamsa)
- Uygulama: ana hisse skor 4-5 ise ortakları izle, sertçe düşerse K-15a 1g teyit ile alım değerlendir

OTOMATİK SKOR HESAPLAMA (yeni eklendi):
- Earnings tarihi 7 gün öncesi script çalışır: scripts/k16_sell_the_news_score.py SYMBOL
- Skor + telegram alert ("K-16 SCORE:3 AAPL → %25 kısmi al + trailing")
- Manuel hesaplama atlama riski (NVDA örneği — script olsaydı kayıt olurdu)

K-05 İLE İLİŞKİ:
- K-05: swing earnings 2+ gün öncesi TAM çıkış (binary risk yönetimi)
- K-16: portföy earnings öncesi KADEMELİ çıkış (uzun vadeli pozisyon koruma)
- Çakışma yok, farklı kapsam: swing K-05, portföy K-16

REPO KANITI (REVİZE 7 nisan 2026):

ESKİ İDDIA: "MU -%3.8, NVDA -%5" → KISMEN YANLIŞ

GERÇEK NVDA (closed.json SWING-011):
- 12 şubat - 23 şubat 2026
- +%2.88 KAZANÇ (zarar değil!)
- Çıkış nedeni: K-05 (earnings öncesi tam çıkış), K-16 değil
- "26 şubat NVDA earnings riski, +%3.4 kâr güvenceye alındı, gap-down riski (%10-15 olası) alınmadı"
- NVDA earnings sonrası belki gerçekten -%5 düştü ama Zeynel'e zarar yaratmadı
- Bu örnek K-05'in başarısı, K-16 ile karıştırılmış

GERÇEK MU: transactions.csv'de MU referansı yok (ALMU farklı hisse). Aggressive portföyde MU pozisyonu olabilir ama kayıt eksik.

KRİTİK DERS: closed.json'da K-16 etiketi 0 trade. K-16 hiç sistemli uygulanmadı. Otomatik script + telegram alert şart.

LİTERATÜR DESTEĞİ:
- AInvest (4 gün önce, en güncel): büyüme hisseleri sell the news riski, beat-and-raise gerekli, subtle guidance reset bile catalyst
- HeyGotrade: pre-earnings buyer profit-taking baskısı, guidance historical performance'tan ağır basar, markets forward-looking
- CMC Markets: buy the rumour sell the news klasik pattern, prices drift up before, selling even when numbers meet expectations
- US News Money: guidance ile eşleşen earnings = priced in = sell on news
- UCLA Anderson akademik: SUE + EAR earnings reaction patterns gerçek fenomen, abnormal returns sürekli görülüyor

**K-17: korelasyon ve yoğunlaşma yönetimi — netleştirilmiş 7 nisan 2026**

KAPSAM: tüm portföyler (Dengeli, Agresif, Temettü, Swing). hem bireysel pozisyon hem küme seviyesi risk yönetimi.

AYNI GÜN GİRİŞ LİMİTLERİ:
- Max 2 yeni pozisyon/gün (farklı sektör olsa bile)
- Aynı tema/sektör/anlatıdan max 1
- VIX 22-28 ("dikkatli"): max 1 duyarlı sektör girişi (faydalanıcılarda 2'ye izin)
- VIX 28+: max 1 yeni giriş toplam (K-13 duyarlıları zaten yasaklıyor)

TEMA TANIMI (yeni eklendi - kritik):
GICS sektör değil, ANLATI bazlı tema. Üç soru testi:
1) Aynı makro hikayeye mi bağlı? (örn: AI sermaye harcaması, petrol arzı, faiz)
2) Aynı katalize mi tepki veriyor? (örn: NVDA earnings, OPEC kararı, FOMC)
3) Aynı senaryo bozulursa hepsi düşer mi?
ÜÇ SORUDAN BİR EVET → AYNI TEMA

ÖRNEK TEMALAR:
- AI tedarik zinciri TEMASI: NVDA, MRVL, COHR, POWL, CAMT, VRT, ANET, CRDO (farklı GICS sektörler ama AYNI ANLATI)
- Enerji petrol TEMASI: XOM, CVX, COP, EOG, SLB, HAL, FANG
- Savunma jeopolitik TEMASI: LMT, NOC, RTX, GD, HII

TEMA YOĞUNLUK (K-12 ile entegre):
- Tek tema max %40 toplam $600K bazlı (K-12 sektör limiti ile aynı)
- Aşılırsa en zayıfı küçült, yeni tema girişi yok
- HAFTALIK kontrol pazar günleri zorunlu

KORELASYON CHECKLIST (giriş öncesi zorunlu):
1) Yeni hisse mevcut portföyle aynı sektör ETF'inde mi? (XLK, XLE, XLF...)
2) Aynı makro faktör? (faiz, petrol, dolar, çip talebi, AI capex)
3) Aynı katalizöre mi tepki veriyor? (earnings, FOMC, sektör haberi)
4) Aynı küme/anlatıya mı bağlı? (yukarıdaki tema testi)
- 2+ EVET → korelasyon riski yüksek, küçült veya skip

OTOMATİK KONTROL (yeni eklendi):
- Her giriş öncesi script çalışır: scripts/k17_correlation_check.py NEW_SYMBOL
- Mevcut portföy ile sektör/tema/makro çakışması raporlanır
- Telegram alert ("K-17 RISK: NEW_SYMBOL same theme as POWL/CAMT")

REPO KANITI - belgelendi 7 nisan 2026:

OLAY 1 - POWL+CAMT+VRT (en pahalı K-17 ihlali):
- 25 mart 2026, Aggressive portföy
- POWL $19,894 (AI veri merkezi güç altyapısı)
- CAMT $19,876 (HBM yarıiletken denetimi)
- VRT $19,775 (AI sıvı soğutma)
- Toplam yatırım: $59,544
- Tema: HEPSİ AI TEDARİK ZİNCİRİ (farklı GICS sektör ama aynı anlatı)
- K-17 ihlali: "aynı tema max 1" kuralının açık ihlali (3 hisse aynı gün)
- Sonuç (27-30 mart, 5 gün içinde hepsi stop):
  • CAMT 27 mart -%9.5 (~-$1,892)
  • VRT 27 mart -%9.7 (~-$1,925)
  • POWL 30 mart -%10.63 (~-$2,115) [+ K-18 ihlali insider satış]
- TOPLAM ZARAR: ~$5,932 (-%9.98 yatırım üzerinden)
- Memory iddiası "-%28": yüzdelerin matematik toplamı (-10.63 -9.5 -9.7 = -%29.83), YANILTICI metrik. Gerçek portföy etkisi -%9.98
- BONUS ZARAR: MRVL aynı tema/pencere -%3.80 (~-$1,354)
- TOPLAM AI TEDARİK ZİNCİRİ KAYBI: ~$7,286
- KRİTİK DERS: 5 gün içinde küme seviyesi başarısızlık. K-17 doğru uygulansaydı 3 hisse yerine 1 hisse açılırdı, kayıp 1/3'e inerdi

OLAY 2 - 24 şubat 3 swing pozisyon (nicel ihlal):
- ZS (cybersec) +%2.55 ✓
- HAL (oil services) -%5.10 ✗
- SOFI (fintech) -%3.62 ✗
- Sektörler farklı (tema ihlali yok)
- AMA max 2/gün limiti açık ihlal (3 pozisyon)
- Sonuç: 1 kazanç + 2 zarar = mixed
- DERS: nicel kontrolün önemi, otomasyon olmadan unutulur

LİTERATÜR DESTEĞİ:
- Black Swan Lab (3 hafta önce): konsantrasyon riski "çoklu pozisyonlar aynı altta yatan sürücü", 3 tech hisse + tech ETF + growth fund "diversified hissedilebilir, tech selloff'ta değil"
- Hereward Vaudry / Medium (ocak 2026): pozisyon listesi enstrüman listesi, risk listesi değil; küme seviyesi düşünme şart, "her pozisyon tek başına zararsız görünür, gerçek risk toplamdadır"
- Guardfolio (aralık 2025): 50 holding 5 gibi işleyebilir korelasyon yüksekse
- HeyGotrade (ocak 2026): konsantrasyon farkında olmadan birikir, sayı değil korelasyon önemli
- BIS akademik: sektör konsantrasyonu ekonomik sermayeyi %20-40 artırır
- Predictive Investor: korelasyon 0.80+ "diversified portföyü konsantre kumar haline getirir"
- K-17 mantığı endüstri standardı

ESKİ "IBKR notu" KALDIRILDI: "AI/yarıiletken %63 → sınır aşıldı, yeni AI öncesi azaltma şart" notu eski bir durumla ilgiliydi. Mevcut portföy %86 nakit, AI exposure ~%0. Mevcut durum kontrolü için günlük summary.json kullanılır.

**K-18: giriş öncesi insider kontrolü — netleştirilmiş 7 nisan 2026**

KAPSAM: tüm portföyler (Dengeli, Agresif, Temettü, Swing). giriş ÖNCESİ zorunlu kontrol, atlama yasak.

KATMAN 1: İNSİDER SATIŞ ANALİZİ (FMP insider-trading endpoint)

a) CEO/CFO/Chairman satışı son 30 gün:
   • VAR → girme veya çeyrek pozisyon (eşiğe bakılmaksızın)
   • YOK → diğer kontrollere geç

b) Toplam insider satış son 30 gün:
   • >$5M → yarım pozisyon
   • $1-5M → tam pozisyon ama dikkat (diğer faktörler)
   • <$1M → normal

c) Satış konteksti (Kelly nüansı - YENİ):
   • Satış son 6 ay düşüş trendinde (zarar gerçekleştirme) → ÖZELLİKLE KAÇIN
     (Notre Dame Kelly: zararda satış 188bp negatif tahmin)
   • Satış yükseliş trendinde (kâr gerçekleştirme) → daha az endişe verici
     (Kelly: kârda satış öngörü gücü yok)

d) İnsider alışı son 30 gün:
   • CEO/CFO alışı VAR → güçlü pozitif sinyal, normal giriş
   • Net alış pozitif → nötr-pozitif

e) Dengeli (alış+satış var) → nötr, diğer faktörlere bak

KATMAN 2: KISA VADELİ BASKI (yeni netleştirildi)

a) Dark pool / blok satış:
   • Veri kaynağı: cheddarflow.com (twitter izleme listesinde @CheddarFlow)
   • Son 5 gün $50M+ blok satış → yarım pozisyon

b) Analist downgrade'leri son 2 hafta:
   • Veri kaynağı: FMP analyst-stock-recommendations
   • 2+ downgrade → girme veya yarım pozisyon

c) Margin compression / debt warning:
   • Veri kaynağı: FMP key-metrics interestCoverage
   • <2x → ek dikkat

KATMAN 3: ARZ/DİLÜSYON RİSKİ
→ K-15b'ye bak (negatif FCF, shelf, hisse arzı geçmişi)

OTOMATİK KONTROL (kritik - yeni eklendi):
- Her giriş öncesi script çalışır: scripts/k18_insider_check.py SYMBOL
- 3 katman tek seferde sorgulanır
- Telegram alert ("K-18 RISK: SYMBOL CEO sold $25M last 30d → çeyrek poz")
- Manuel kontrol unutkanlığa açık (POWL kanıtı)

REPO KANITI - belgelendi 7 nisan 2026:

OLAY 1 - POWL (K-18 başarısızlığı, en pahalı):
- 25 mart 2026 giriş, $19,894 yatırım (Aggressive portföy)
- $585.12 fiyattan 34 hisse alındı
- K-18 GİRİŞ ÖNCESİ KONTROL EDİLMEDİ
- 30 mart stop kaydı: "$25M insider satışı (Thomas W. Powell - CEO) + kâr realizasyonu"
- PnL: -%10.63 (~-$2,115)
- 5 gün içinde stop yedi
- Eğer K-18 çalışsaydı: CEO satışı son 30g VAR → girme veya çeyrek poz
  • Çeyrek poz olsa kayıp ~-$528 (4x daha az)
  • Hiç girilmese kayıp $0
- POWL ayrıca K-17 ihlalinin parçası (POWL+CAMT+VRT AI tedarik zinciri kümesi)
- DERS: K-18 KURALI VARDI ama UYGULANMADI. Otomatik script şart.

OLAY 2 - CRDO (K-18 başarısızlığı):
- 17 mart 2026 stop kaydı: "Stop-loss tetiklendi - insider + margin compression - Agresif portföy"
- Aggressive portföyde, kayıp ~-%8.77
- closed.json'da yok (swing değil)
- Aynı pattern: K-18 giriş öncesi kontrol edilmedi
- Hem insider (K-18) hem margin compression (K-15b) → ÇİFT KIRMIZI BAYRAK
- DERS: K-18 + K-15b birlikte çalışsaydı bu pozisyon hiç açılmazdı

KRİTİK İSTATİSTİK:
- closed.json'da K-18 etiketi: 0 trade
- Yani K-18 hiç sistemli giriş öncesi uygulanmadı (mart 2026'ya kadar)
- POWL ve CRDO sadece "çıkış sonrası fark edildi"
- Bu kuralın ÖLÜ KURAL olduğunun kanıtı
- Otomasyon olmadan K-18 yine ölü kalır

LİTERATÜR DESTEĞİ (6 referans):
- Notre Dame Peter Kelly (Review of Financial Studies 2018, en titiz akademik):
  • Zararda insider satış → 6 ay sonra 188 baz puan daha düşük getiri
  • Kârda insider satış → öngörü gücü yok
  • "Loss-sold short, gain-sold long" stratejisi 67bp/ay alpha
- Springer Quantitative Finance: insider satışları gelecek crash risk ile pozitif ilişkili, senior insider (CEO/CFO/Chairman) en bilgilendirici, ortalama 15 ay önceden öngörü
- ScienceDirect 2019: CEO satışları tahminleri özellikle güçlü, opportunistik işlemler rutin işlemlerden daha bilgi içerir, "insider sales can be informative for investors"
- AEAweb 2019: insider price impact hızlı oluşuyor, kontrol giriş öncesi şart, market maker reaksiyonları zayıf
- MDPI 2024: earnings öncesi insider satış güçlü kötü haber sinyali, 10-40 gün pencerelerde negatif getiri
- ScienceDirect 2024: tüm insider satışları eşit değil, narsist CEO işlemleri daha az bilgilendirici, opportunistic vs routine ayrımı önemli

K-15b İLE İLİŞKİ:
- K-18 katman 1+2: insider davranışı ve kısa vadeli baskı (kısa-orta vade sinyaller)
- K-15b: yapısal dilüsyon (uzun vade bilanço, FCF, shelf)
- İkisi birlikte: insider satış + dilüsyon = ÇİFT KIRMIZI BAYRAK
- CRDO örneği: hem insider hem margin compression (K-18 + K-15b çift bayrak)
- POWL örneği: K-17 + K-18 çift ihlal (kümeleme + insider)

**K-19: XLP swing dışlama — netleştirilmiş 7 nisan 2026**

KAPSAM: SADECE swing trade. portföy pozisyonları izinli (Temettü'deki MO/PM örnekleri).

KURAL: XLP sektöründeki hisselerden swing trade sinyali değerlendirilmez. ichimoku 4/4, K-13b sinyali, RSI oversold gibi sinyaller verse bile GİRİLMEZ.

XLP HİSSELERİ (genişletilmiş, 25+ hisse):
- Tütün: MO, PM
- Gıda/içecek: PEP, KO, KDP, MDLZ, GIS, K, HSY, MNST, CAG, CPB, KHC
- Perakende: WMT, COST
- Ev ürünleri: PG, CL, CLX, KMB, CHD, EL, NWL
- Diğer: SYY, ADM, BG, TSN, HRL

ALTERNATİF FORMÜL: SPY sektör sınıflamasında "Consumer Staples" altındaki tüm hisseler. Şüphe varsa: spdr.com/etfs/XLP holdings sayfası kontrol edilir.

GEREKÇE: Defansif hisseler yapısal düşük volatiliteye sahip
- Beta ortalaması 0.6-0.8 (S&P 500 = 1.0)
- Günlük hareket %0.5-1
- 10 günde %10 swing hedef matematik olarak zor (literatür onayı)

K-13b İLE ÖNCELİK (yeni netleştirildi - kritik):
- K-13b "savunma sektör tam pozisyon" der, kapsam: XLU + XLV + XLP + XLC
- K-19 K-13b'den DAHA ÖNCELİKLİ sadece XLP için
- K-13b VIX 22-35'te:
  • XLU swing → izinli (orta volatilite, rate sensitive)
  • XLV swing → izinli (clinical katalist, M&A)
  • XLC swing → izinli (META/GOOGL/NFLX yüksek beta)
  • XLP swing → YASAK (K-19 önceliği)
- Bu hiyerarşi net: K-19 sadece XLP için ÖZELDİR, K-13b genel kuralı geçer

OTOMATİK KONTROL (yeni eklendi):
- Tarama sırasında script çalışır: scripts/k19_xlp_filter.py SCAN_RESULTS.json
- XLP hisseleri tarama sonuçlarından otomatik elenir
- Telegram alert ("K-19: WMT removed from scan, XLP exclusion")

REPO KANITI - belgelendi 7 nisan 2026:

CLOSED.JSON (1 vaka):
- WMT 6-18 şubat 2026: -%3.48 ZARAR
- 12 gün tutuldu, hedef 10 gündü
- Çıkış nedeni: "zaman çerçevesi aşıldı, hedef 10 gündü, zarar kesildi"
- Klasik düşük volatilite örneği — fiyat hedefe yetişemedi

SWING_SYSTEM_V2 BACKTEST (2 vaka):
- 0 kâr, 2 zarar
- 61 dönem 2021-2026 backtest evreninde
- "Defansif hisseler %10 hedefe ulaşamıyor"

TOPLAM: 3 trade, 3 zarar (%100 zarar oranı, küçük sample uyarısı)
- Sample küçük ama yön net
- Bull market'te (mart 2026 öncesi) bile staples zayıf

MEMORY HATA KONTROLÜ: T (AT&T) listede DEĞİL, doğru. T = XLC (Communication Services), XLP değil.

LİTERATÜR DESTEĞİ (7 referans):
- Quantified Strategies (en doğrudan akademik onay): "low volatility stocks may not appeal to day traders and SWING TRADERS because in short run may not provide the price movement needed for short-term gains" — K-19'un tam akademik onayı
- AlphaExCapital: consumer staples beta 0.6-0.8 vs S&P 500 = 1.0, daha az fiyat dalgalanması, daha düşük drawdown ama daha düşük getiri potansiyeli
- AQR Funds: low-vol stratejiler defansif sektörleri tercih eder, bull market'te underperform
- Motley Fool 2026: staples bull marketleri yönetmez, growth tökezlediğinde smooth eder, soda/tütün baskısı son yıllarda underperformance
- Interactive Brokers: yıllık %2.5 büyüme, broader market'tan düşük
- JP Morgan (5 gün önce): defensive playbook 2026 - staples yerine utilities ve healthcare öneriyor
- Fidelity 2026: staples 2025'te belirgin underperform, AI-growth tercih
- K-19 mantığı endüstri ve akademik konsensüs ile uyumlu

EKSILER (gelecek genişleme için not):
- XLP alt-sektör ayrımı yok (tütün vs gıda vs perakende farklı dinamikler)
- Tek tek istisna izin yok (örn: özel katalist)
- Mevcut form: bütün-veya-hiç (whole-or-none)
- Bu kabul edilebilir çünkü swing'de hassasiyet > esneklik

**K-20: sektör RS dead cat bounce filtresi — netleştirilmiş 7 nisan 2026**

KAPSAM: tüm swing girişler. K-13b istisna pozisyonlarında uygulanmaz.

KURAL: Hisse'nin sektör ETF'i SPY'a karşı RS20 < 0 VE RS10 > 0 ise → swing girişi YOK.
Yorum: sektör orta vadede zayıflıyor (RS20<0) ama kısa vadede sıçramış (RS10>0) → dead cat bounce, sektörel zayıflık devam ediyor.

HESAPLAMA (netleştirildi):
- Veri: FMP historical-price-eod, GÜNLÜK KAPANIŞ fiyatları
- RS oranı = sektörETF_kapanış(bugün) / SPY_kapanış(bugün)
- RS20 = (RS_bugün - RS_20_iş_günü_önce) / RS_20_iş_günü_önce × 100
- RS10 = (RS_bugün - RS_10_iş_günü_önce) / RS_10_iş_günü_önce × 100
- 20 ve 10 = takvim günü değil, İŞ GÜNÜ (trading day)

SEKTÖR ETF EŞLEŞTİRME (genişletildi 7 → 10):
- XLK: technology (NVDA, MSFT, AAPL, GOOGL, MRVL, COHR, CRDO, CAMT)
- XLC: communication services (META, NFLX, T, VZ, GOOGL)
- XLE: energy (XOM, CVX, COP, EOG, SLB, HAL, FANG, AROC)
- XLI: industrials (CAT, GE, LMT, RTX, NOC, GD, POWL, VRT)
- XLV: healthcare (JNJ, UNH, LLY, PFE, ABBV, MRK, DVA, MDT)
- XLF: financials (JPM, BAC, GS, MS, BRK.B, V, MA, SOFI)
- XLY: consumer discretionary (AMZN, TSLA, HD, LOW, MCD, SBUX)
- XLU: utilities (NEE, DUK, SO, CEG, EXC, AEP) — YENİ EKLENDİ
- XLB: materials (LIN, APD, FCX, NEM, RGLD, ECL) — YENİ EKLENDİ
- XLRE: real estate (AMT, PLD, EQIX, CCI, DLR) — YENİ EKLENDİ
- XLP: NOT — K-19 zaten swing yasak, K-20 uygulanmaz

K-19 İLE İLİŞKİ (sıralı uygulama):
- K-19 (XLP) ÖNCE çalışır: XLP hisseleri tarama dışı
- K-20 SONRA çalışır: K-19'dan geçen hisselerin sektör RS'i hesaplanır
- Çakışma yok

K-13b İSTİSNA POZİSYONLARI:
- K-13b "VIX 28-35'te 6 koşul sağlanırsa çeyrek pozisyon" istisnası verir
- Bu istisna pozisyonlarda K-20 uygulanmaz
- Gerekçe: K-13b zaten kendi sektör filtresi (faydalanıcı sektör — savunma, enerji, altın) uyguluyor, çift filtre over-restrictive olur

OTOMATİK SCRIPT (kritik - yeni eklendi):
- Tarama sırasında her hisse için sektör tespit + RS hesabı:
  python scripts/k20_rs_filter.py SCAN_RESULTS.json
- 10 sektör ETF için günlük RS önbelleğe alınır (FMP API quota tasarrufu)
- Telegram alert ("K-20: HAL filtered (XLE RS20=-2.1%, RS10=+0.8% → dead cat)")
- Manuel hesaplama imkansız (10 sektör × her hisse × her tarama)

REPO KANITI (revize 7 nisan 2026):

SWING_SYSTEM_V2 BACKTEST:
- 76 trade backtest evreninde (2021-2026)
- 15 vaka K-20 RS pattern'inde (RS20<0 + RS10>0)
- 3 kâr / 12 zarar (%80 zarar)
- Filtre olmadan: %47 win rate
- Filtre ile: %54 win rate (+%7 puan iyileşme)
- Mütevazı ama tutarlı iyileşme, sample küçük uyarısı

CLOSED.JSON SEKTÖR DAĞILIMI (referans, K-20 doğrudan test değil):
- XLK 5 trade %80 win, XLI 4 trade %75 win — güçlü sektörler
- XLE 3 trade %33 win, XLF 1 trade %0 win, XLRE 1 trade %0 win — zayıf
- XLU 2 trade %50, XLB 2 trade %100 (NEM altın), XLV 1 trade %100 (DVA)
- Bu dağılım K-20'nin sektör ayırt etme mantığını dolaylı destekliyor

KRİTİK DERS: closed.json'da K-20 etiketi 0 trade. K-20 muhtemelen otomasyon eksikliğinden hiç uygulanmadı (manuel hesaplama imkansız: 10 sektör × her hisse). Otomatik script + telegram alert şart.

LİTERATÜR DESTEĞİ (8 referans, hepsi aynı yönde):
- Wikipedia: dead cat bounce continuation pattern, kısa pozisyon kapama + temporary demand sürer
- Kraken: bearish continuation chart pattern, sadece oluştuktan sonra teyit
- Strike.money: continuation pattern, trend tersine dönüş değil, fundamental destek yok
- XS Trading: çok erken alım zarar, davranışsal önyargılar (confirmation bias, FOMO)
- EBC Financial: rallileri reversal ile karıştırmak anlamlı zararlar, gerçek reversal artan hacim
- FXOpen: her sıçrama toparlanma sinyali değil, broader market teyit gerekli
- Investing.com: bankacılık sektör tarihsel örneği — kısa toparlanma sonra yeniden düşüş
- Tealstreet: continuation pattern, market hala bearish, broader market analiz şart

HEPSİ aynı sonucu veriyor: kısa süreli sıçrama + uzun vade zayıflık = bearish continuation, swing alımı kayıp riski yüksek.

EKSILER (gelecek genişleme):
- Backtest sample küçük (15 vaka)
- Filtre etkisi mütevazı (%7 puan)
- Hisse seviyesi dead cat bounce kontrolü yok (sadece sektör seviyesi)
- Sektör seviyesi tek başına yetmez, hisse seviyesinde RSI overbought ek değerlendirilebilir

### LEAPS YÖNETİM KURALLARI (bağımsız bölüm, 7 nisan 2026)

**KAPSAM**: 1+ yıl vadeli opsiyon pozisyonları (agresif portföyde kaldıraç aracı). Normal hisse kurallarından bazı farklarla yönetilir.

**TANIM**:
- LEAPS = Long-term Equity Anticipation Securities
- Minimum vade: 12 ay (daha kısası "uzun vadeli opsiyon" sayılır, LEAPS değil)
- Genellikle in-the-money (ITM) veya yakın ITM call opsiyon
- Delta hedefi: 0.55-0.80 (senkronize hisse hareketi için)

**EFEKTİF MARUZİYET HESABI (K-12 entegrasyonu)**:
- formül: kontrat sayısı × 100 × delta × strike
- örnek: 6 MU call × 100 × 0.55 × $87.93 ≈ $29K
- K-12 limitlerine hisse gibi dahil edilir (Dengeli %25, Agresif %20, Temettü %15)
- K-17 korelasyon kontrolü aynen uygulanır (LEAPS hisseyi kapsam dışına çıkarmaz)

**GİRİŞ FİLTRELERİ (normal swing/portföy kurallarından farkları)**:
- K-04: SMA50 trend filtresi aynen uygulanır (LEAPS için trend kritik)
- K-13 v4.1: VIX bandı aynen uygulanır (faydalanıcı/duyarlı sektör)
- K-18 insider check: ZORUNLU (CEO/CFO senior sell = LEAPS için daha da kritik, 12+ ay horizon)
- K-15b dilüsyon: momentum LEAPS için zorunlu (shelf registration LEAPS'i öldürür)
- Theta decay: giriş anında hesaplanmalı, 1 yıl horizonda beklenen kayıp
- Implied volatility: IV percentile <50 olmalı (yüksek IV'de LEAPS pahalı, theta riski yüksek)

**ÇIKIŞ KURALLARI (normal stop'tan farkları)**:
- K-06: stop tetiği ÇIKIŞ, ama LEAPS için stop HİSSE fiyatı üzerinden hesaplanır
- Hisse fiyatı stop'u kırarsa → LEAPS tam çık (premium kaybı kabul edilir)
- K-07 trailing: LEAPS için 50SMA kullanılır (20SMA çok dar, gereksiz early exit)
- K-05 earnings: LEAPS'te earnings öncesi TAM çık ZORUNLU DEĞİL (binary risk yok, vega oynar)
  - AMA: IV crush riski var, pozisyon %50'ye indirilebilir
- K-11 kademeli kâr alma: LEAPS için RSI 80+ baskın tetik (RSI 70 çok erken, LEAPS trend'i yakalar)
- Delta <0.40'a düşerse → pozisyonu ayarla (roll up veya çık, ITM değeri kaybolmakta)

**POZİSYON BÜYÜKLÜĞÜ**:
- Max premium riski: portföyün %3'ü (hisse %25'ten farklı)
- Örnek: Agresif portföyde $400K × %3 = $12K premium max tek LEAPS'e
- Strike seçimi: 0.60-0.70 delta (ITM), at-the-money tercih edilmez (theta yüksek)
- Vade: min 12 ay, ideal 18-24 ay (theta decay yavaş aşama)

**ROLL YÖNETİMİ**:
- Vade <6 ay kalıpsa: roll forward (daha uzun vade) değerlendir
- Delta <0.40: roll down (daha düşük strike, ITM'e dön)
- Her roll K-12 limit kontrolü gerektirir
- Roll kâr/zarar: closed.json'a kaydet, yeni pozisyon active'de

**REPO KANITI (7 nisan 2026)**:
- Aggressive portföyünde geçmişte MU LEAPS pozisyonu vardı
- Bu bölüm formal olarak henüz uygulanmadı (MU trade'leri K-11/K-12 kurallarıyla yönetildi)
- Gelecek LEAPS trade'leri bu bölümü takip edecek

**LİTERATÜR REFERANSI**:
- CBOE LEAPS Educational Guide: ITM 0.7+ delta tercih edilir
- OptionGenius (2026): LEAPS için IV percentile altında giriş ana başarı faktörü
- TastyTrade: 45-60 DTE değil, 365+ DTE tercih edilmesi LEAPS'in temel prensibi

---

### ek kanıtlar

**K-04 + K-18 çifte bayrak kanıtı: CRDO 10-17 mart 2026** — CRDO 10 mart $114.28'den alındı (tüm SMA'ların altında: SMA50 $125.88, SMA200 $128.84). insider 365 sat / 0 al ile çift kırmızı bayrak oluşmuştu. 17 mart -%10.8 günlük düşüşle stop tetiklendi (-%8.77). gross margin guidance compression. NOT: 18 mart 2. CRDO girişi $101.56'dan yapıldı (FOMC sonrası ve insider tablosu değişmedi) ama portföy daraltma ile 25 mart $102.60'ta küçük kârla (+%1.02) çıkıldı — 2. trade K-04 doğrulaması değildir, sadece ilki kuralı doğruluyor

**RGLD altın korelasyon bozulması** — altın -%5 düştüğünde RGLD -%7.20 (negatif beta, daha sert). royalty modeli altınla asimetrik korelasyon: yukarı sınırlı, aşağı sert. tez bozulma sınırı -%20 ($217 civarı). "altın yükseliyor diye royalty yükselecek" varsayımı yanlış


---

## 2. HATA KAYDI

her hata tarih, ne olduğu, neden yanlış olduğu ve çıkarılan kuralla kaydedilir.

| tarih | hisse | hata | sonuç | çıkarılan kural |
|-------|-------|------|-------|-----------------|
| 2-9 mart | KTOS, CEG, HAL, LASR, BKSY | momentum/savunma kriz girişleri | 3 zarar (HAL -%5.10, CEG -%5.05, KTOS stop), 1 breakeven (LASR), 1 kâr (BKSY +%18) | K-02 (kısmi) |
| 5 mart | AMKR | NFP öncesi gece alım | -%6.12 | (K-01 kaldırıldı) |
| 5-9 mart | LASR | 3x stop override (override istisnası 'şanslı' breakeven dönüş ile maskelendi) | -%3.8→-%7.3, BE çıkış | K-06 ihlal kanıtı |
| 27 şubat | LMT | swing'de fırsat maliyeti gözlemi | +%1.43 (18g, kâr ama yavaş) | (K-08 kaldırıldı) |
| 10 mart | ALMU | VIX 24'te small cap swing | 2 günde -%6.1 | K-03 |
| 24 şub-12 mart | SOFI | momentum kaybı, SMA50 altı giriş | -%3.62 | K-04 (mean reversion ihlali) |
| 13 mart | SM/XLE | RSI 70+ uyarısı, kısmi kâr zamanlaması | izlenmeli | K-11 |
| 10-17 mart | CRDO | SMA50+200 altı + insider yoğun satış (çifte bayrak) | -%8.77 stop | K-04 + K-18 |
| 18 mart | RKLB | momentum hissesinde arz riski değerlendirilmedi | -%11.59 (pozisyon küçük) | K-15 (yeni) |
| 18 mart | MU | canavar beat ama AH sınırlı tepki | +%1.27 (beklenti altı) | K-16 (yeni gözlem) |
| 17 şub-11 mart | T | savunmacı tez yüksek VIX'te çalışmadı, sektör liderliği yok | -%5.54 | tez bazlı kayıp (K kategori dışı) |
| 24 mart | NEM | K-17 skor %18 (min %50 gerekli) ile giriş, ichimoku 0/3 | devam izleniyor | K-17 ihlali |
| 25 mart | POWL, CAMT, VRT | VIX 29+ ortamında AI tedarik zinciri tam pozisyon girişi (kriz rallisi değil, AI capex tezi) | POWL -%10.3, CAMT -%8.3, VRT -%9.4 | K-13 v4.1 (yüksek VIX'te momentum tema riski) |
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
| stop-loss disiplini (override yasak, K-06) | n=8 swing, hepsi -%6 altında: RTX -%5.16, CEG -%5.05, T -%5.54, AMT -%3.35, GE +%1.68, ALMU -%6.11, SOFI -%3.62, AROC -%4.95 | hard zarar yok, kontrollü kayıplar |
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
- **dikkat**: kriz başlangıcında momentum/AI tema yeni girişleri 3 gün ertelenir (K-02). enerji ve savunma defansif sayılır, K-02 muafiyetinde

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
- **kriz rallisi girişi**: 5 trade (KTOS, HAL, CEG, LASR, BKSY) → 3 zarar, 1 breakeven, 1 büyük kâr (BKSY +%18). momentum/AI girişlerinde dikkat, defansif/enerji görece dirençli (K-02)
- **RSI oversold bounce**: karışık — teyit beklemek şart
- **breakout**: karışık — VIX yüksekken breakout güvenilmez

### son trend (mart 2026)
- son 5 kapanıştan 4'ü zarar → **ortam uygun değil, swing'e ara ver** (K-14)
- 26 mart AROC stop ihlali ile kapatıldı (-%4.95, 2 gün). 0/8 aktif pozisyon
- genel: 10K/10Z (%50 win rate), ort kazanç +%4.13, ort kayıp -%4.61
- agresif portföyde 25 mart girişleri (POWL, CAMT, VRT) ilk gününde -%8 ile -%10 arasında. K-13 v4.1 ihlali (VIX 29+ ortamında momentum tam pozisyon)

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
- süre: %10 hedefe veya stop'a kadar tut. zaman sınırı yok, chandelier yönetir
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
