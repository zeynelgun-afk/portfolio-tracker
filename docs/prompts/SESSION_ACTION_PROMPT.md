# SEANS İÇİ AKSİYON PROMPT — v2.2

> ⛔ **KRİTİK: AŞAMA ATLAMA YASAĞI**
>
> bu prompt'taki 5 aşama sırayla ve eksiksiz uygulanmalıdır. hiçbir aşama veya alt adım atlanamaz, kısaltılamaz veya "gerek yok" diye geçilemez. bir aşamayı tamamlamadan diğerine geçme.
>
> **zorunlu aşamalar (teker teker kontrol et):**
> - [ ] AŞAMA 1 — VERİ TOPLAMA (tümü zorunlu):
>   - [ ] 1a. piyasa genel durumu (SPY, QQQ, VIX, emtia)
>   - [ ] 1b. portföy hisseleri (canlı fiyat + RSI + SMA)
>   - [ ] 1c. piyasa istihbaratı + prediction markets + haber (neden-sonuç zinciri)
>   - [ ] 1d. twitter takip listesi (faz 1'de çek)
>   - [ ] 1e. sektör RS analizi
> - [ ] AŞAMA 2 — DURUM TESPİTİ:
>   - [ ] 2a. sabah raporu ile karşılaştırma
>   - [ ] 2b. her portföy pozisyonu durum tespiti
>   - [ ] 2c. swing pozisyonları durum tespiti
> - [ ] AŞAMA 3 — KARAR (playbook kurallarıyla çapraz kontrol):
>   - [ ] 3a. karar matrisi (portföyler)
>   - [ ] 3b. karar matrisi (swing)
>   - [ ] 3c. portföyler arası korelasyon kontrolü
>   - [ ] 3d. yeni pozisyon fırsatları (geniş havuz ichimoku tarama: screener → SMA filtre → ichimoku → claude temel değerlendirme)
>   - [ ] 3e. satış/çıkış değerlendirmesi (K-06 ile K-09 kontrol)
> - [ ] AŞAMA 4 — UYGULAMA:
>   - [ ] 4a. trade işlemleri (JSON + CSV güncelle)
>   - [ ] 4b. fiyat güncellemesi
>   - [ ] 4c. watchlist güncellemesi
>   - [ ] 4d. git commit + push
>   - [ ] 4e. telegram bildirimleri (aksiyon + seans özeti)
> - [ ] AŞAMA 5 — RAPOR (chat'te göster)
> - [ ] SELF-VALIDATION kontrolü yapıldı mı?
>
> **geçmiş hatalar**: adım atlama maliyetli oldu (örn: kazanç açıklaması taramasını atlama, bölüm eksik bırakma). prompttaki her madde bir sebepten var — atlamak portföy kararlarını olumsuz etkiler.

> **versiyon**: 2.2 | **son güncelleme**: 6 nisan 2026
> **çalışma zamanı**: NYSE açıldıktan sonra (TR 16:30+, yaz saati), tercihen açılıştan 30-60dk sonra
> **ön koşul**: o günün sabah raporu zaten yazılmış olmalı
> **perspektif**: PİYASA AÇIK — GERÇEK ZAMANLI KARAR VE AKSİYON
> **fiyat verisi**: canlı/güncel fiyatlar (FMP quote = bugünün verisi)
> **çıktı**: doğrudan JSON güncelleme + trade kararları + git push
> **dil**: küçük harf türkçe, teknik terimler ingilizce kalabilir
> **kaynak atfı**: sadece "finzora ai" kullan
> **format kuralları**: em dash kullanma

---

> ## ⛔ KRİTİK KURAL — SEANS İÇİNDE RAPOR YAZILMAZ
> 
> **seans içinde hiçbir rapor (.md) hazırlanmaz ve githuba gönderilmez.**
> 
> repoya gidecek raporlar yalnızca dört türdür:
> - `DAILY_SABAH_YYYY-MM-DD.md` → piyasa açılmadan önce (sabah raporu)
> - `DAILY_REPORT_YYYY-MM-DD.md` → piyasa kapanışı sonrası (kapanış raporu)
> - `WEEKLY_YYYY-MM-DD.md` → pazar günü
> - `MONTHLY_YYYY-MM.md` → ay sonu
> 
> seans içi analizler, kararlar ve gözlemler **sadece chat'te kalır.**
> json/csv değişiklikleri repoya gider ama rapor dosyası asla.

---

## SEANS ÖNCESİ vs SEANS İÇİ — FARK

| | günlük rapor (TR ~14:00) | seans içi aksiyon (bu prompt) |
|---|---|---|
| **ne zaman** | NYSE açılmadan ~2.5 saat önce | NYSE açıldıktan 30-60dk sonra |
| **fiyat** | dünün kapanışı (final) | bugünün canlı fiyatı |
| **amaç** | değerlendirme + JSON güncelleme + plan | karar + uygulama |
| **çıktı** | rapor dosyası (.md) + JSON güncelleme | trade emirleri + JSON |
| **ton** | "dün şu oldu, bugün şunu yapacağız" | "şu anda şunu yapıyoruz" |

---

## ÇALIŞTIRMA KOMUTU

kullanıcı şunlardan birini söylediğinde bu prompt devreye girer:
- "piyasa açıldı, kontrol et"
- "seans içi güncelleme"
- "piyasa nasıl, ne yapıyoruz?"
- "açılış sonrası analiz"
- veya doğrudan bu prompt dosyasını referans verdiğinde

---

## SEANS FAZLARİ — NE ZAMAN NE YAPILIR

bu prompt seans boyunca birden fazla kez çalıştırılabilir.
her faz farklı önceliklere sahip:

```
FAZ 1: AÇILIŞ (TR 16:30-17:30) — ilk 60 dakika
  öncelik: ACİL KONTROL
  - gap-up/gap-down kontrolü
  - stop-loss tetiklenen var mı?
  - BMO earnings sonuçları (açılış öncesi açıklananlar)
  - sabah raporundaki acil aksiyonları uygula
  - ilk 15dk aşırı volatil olabilir → büyük karar verme, izle
  - TWİTTER TAKİP LİSTESİ → her açılışta 10 hesabın son tweetlerini çek, portföyle ilgili olanları özetle
  
FAZ 2: MID-SESSION (TR 18:00-21:00) — ana seans
  öncelik: ANALİZ + KARAR
  - tam teknik analiz (RSI, SMA, sektör RS)
  - yeni pozisyon fırsatları değerlendir
  - watchlist tarama (tüm portföyler + swing)
  - portföy rebalance değerlendirmesi
  - prediction markets güncellemesi
  
FAZ 3: POWER HOUR (TR 22:00-23:00) — son saat
  öncelik: FİNAL AKSİYONLAR
  - kapanışa yakın kar alma/pozisyon ayarlama
  - bugün AMC earnings açıklayacak hisseleri not et
  - trailing stop'ları final güncelle
  - kapanış öncesi son fiyat kontrolü
  - yarının sabah raporu için not düş
  - TWİTTER TAKİP LİSTESİ → faz 1'den bu yana yeni tweet varsa çek, önemli güncelleme varsa bildir
```

## TEKRAR ÇALIŞTIRMA — API OPTİMİZASYONU

aynı seansta 2. veya 3. kez çalıştırıldığında tam veri toplama gereksiz:

```
İLK ÇALIŞTIRMA (FAZ 1):
  → tam veri toplama: ~67 FMP + 6-9 websearch
  
TEKRAR ÇALIŞTIRMA (FAZ 2/3):
  → sadece değişenleri çek:
    - batch-quote (1 call — tüm fiyatlar)
    - sector-performance-snapshot (1 call)
    - varsa tetiklenen pozisyon için RSI (1-5 call)
    - websearch sadece yeni haber/PM varsa (0-10)
  → toplam: ~3-10 FMP + 0-12 websearch (minimal)
  
```

---

## ANA AKIŞ (5 AŞAMA)

```
AŞAMA 1: VERİ TOPLAMA (canlı fiyatlar + piyasa durumu)
    │
AŞAMA 2: DURUM TESPİTİ (sabah raporuyla karşılaştır)
    │
AŞAMA 3: AKSİYON KARARLARI (al/sat/tut/izle)
    │
AŞAMA 4: UYGULAMA (JSON güncelle, trade yap, git push)
    │
AŞAMA 5: ÖZET RAPOR (kullanıcıya sun)
```

---

# AŞAMA 1 — VERİ TOPLAMA

## 1a. piyasa genel durumu (canlı)

**FMP çağrıları**:
```python
# endeksler
spy = fmp_get("quote", {"symbol": "SPY"})
qqq = fmp_get("quote", {"symbol": "QQQ"})
dia = fmp_get("quote", {"symbol": "DIA"})
iwm = fmp_get("quote", {"symbol": "IWM"})  # russell 2000

# emtia + forex
gold = fmp_get("quote", {"symbol": "GCUSD"})
oil = fmp_get("quote", {"symbol": "USO"})  # petrol proxy (CLUSD güvenilmez)
usdtry = fmp_get("quote", {"symbol": "USDTRY"})

# treasury
treasury = fmp_get("treasury-rates", {"from": TODAY, "to": TODAY})
```

**websearch** (2-3 arama):
```
- "stock market today {DATE} live"
- "VIX index today"
- varsa özel haber/olay araması (sabah raporunda bekleniyorsa)
```

**sektör performansı**:
```python
sectors = fmp_get("sector-performance-snapshot", {"date": TODAY})
```

**market movers** (açılışta neler olmuş):
```python
gainers = fmp_get("biggest-gainers", {"limit": 10})
losers = fmp_get("biggest-losers", {"limit": 10})
```

**toplam**: ~8-10 FMP call + 2-3 websearch

## 1b. portföy hisseleri (canlı fiyat + teknik)

**tüm portföy + swing sembollerini birleştir** (benzersiz liste):
```python
# 3 portföy JSON + swing active.json oku
# benzersiz sembol listesi çıkar
# batch quote çek
quotes = fmp_get("batch-quote", {"symbols": "COHR,MRVL,PLTR,POWL,CAMT,VRT,..."})
```

**her sembol için teknik göstergeler**:
```python
for symbol in unique_symbols:
    rsi = fmp_get("technical-indicators/rsi", {"symbol": symbol, "periodLength": 14, "timeframe": "1day"})
    sma50 = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 50, "timeframe": "1day"})
    sma200 = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 200, "timeframe": "1day"})
```

**toplam**: ~1 (batch) + 3×N (teknik) — N = benzersiz sembol sayısı (~18 = ~54 call)

## 1c. piyasa istihbaratı + prediction markets + haber

### piyasa istihbaratı (docs/MARKET_INTELLIGENCE.md)

her seansta dünyada ne değişti düşün:
```
1. web araması: "stock market news today", "AI chip semiconductor news", "energy market news"
2. her haberin neden-sonuç zinciri:
   - 1. derece (direkt): haber kimi etkiler?
   - 2. derece (tedarik zinciri): tedarikçileri/müşterileri ne olur?
   - 3. derece (yan etki): enerji, hammadde, lojistik?
3. portföy etkisi: hangi pozisyonlar etkileniyor? aksiyon gerekiyor mu?
4. fırsat: yeni bir katman/hisse ortaya çıkıyor mu?
```

### prediction markets (canlı sentiment)

```
websearch → "kalshi fed rate probability today"
websearch → "polymarket" + gündemdeki olay (tariff/iran/election vb.)

kontrol:
- sabah raporundaki PM verileriyle karşılaştır
- >%10 değişim varsa → önemli sinyal, strateji etkisini değerlendir
- volume spike var mı? (<$10K güvenilmez, $1M+ güvenilir)

aksiyon tetikleyicileri (docs/PREDICTION_MARKETS_GUIDE.md):
- fed rate cut odds > %30 → defensive azalt, cyclical ekle
- iran escalation > %50 → enerji pozisyonlarını koru/artır
- ani %10+ swing → whale manipulation olabilir, teyit bekle
```

### haber kontrolü

```python
# portföy hisselerinin haberleri
news = fmp_get("news/stock", {"symbols": ALL_SYMBOLS, "limit": 50})
# keyword filtresi:
#   negatif: lawsuit, downgrade, SEC, investigation, cut dividend, miss, warning, recall, resign
#   pozitif: beat, upgrade, raise, target, deal, contract, approval, partnership
# eşleşen → web search ile doğrula, dolgu haberler (zacks "is X undervalued" vb.) → atla
# ⚠️ press-releases endpoint'i bozuk — KULLANMA
```

**websearch**: sabah raporundaki beklenen olaylara özel arama
- earnings sonuçları (BMO olanlar açılışta gelmiş olabilir)
- makro veriler (consumer confidence, PMI vb.)
- geopolitik gelişmeler

**toplam**: 1 FMP call + 2-4 websearch

## 1d. twitter takip listesi (faz 1 — açılışta çek)

**API**: RapidAPI → twitter241.p.rapidapi.com
**key**: fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7
**endpoint**: GET /user-tweets?user={numeric_id}&count=20
**user id alma**: GET /user?username=xxx → id alanını base64 decode et

**takip listesi**:
```
@CheddarFlow       → kurumsal para akışı / opsiyon
@berkdemirkiran_   → türk finans yorumcusu
@yatirim           → türk finans yorumcusu (içsel analiz)
@onestoploss       → teknik analiz / trade fikirleri
@StockSavvyShay    → ivme hisse önerileri
@BerkUcmz          → türk finans yorumcusu
@TrendSpider       → teknik analiz araçları
@Jake__Wujastyk    → ivme trader / hisse önerileri
@RyanDetrick       → piyasa istatistikleri / mevsimsellik verileri
@VolSignals        → volatilite analizi / opsiyon stratejileri
```

**filtreleme**: portföy sembolleri + genel piyasa yorumlarını öne çıkar
**toplam**: ~20 RapidAPI çağrısı (her hesap için user id + tweet)

## 1e. sektör RS analizi (canlı)

sabah raporundaki RS analizini canlı verilerle güncelle:
```
sektor_rs = sektor_degisim - SPY_degisim

sinyaller:
- SPY düşerken RS > +1.0% → 🔥 GÜÇ SEKTÖR (para buraya akıyor)
- SPY düşerken RS > +0.5% → 💪 dirençli
- SPY yükselirken RS < -1.0% → ⚠️ ZAYIF SEKTÖR
```

## toplam API bütçesi (aşama 1)

| kaynak | çağrı sayısı |
|--------|-------------|
| endeks + emtia + forex | ~8 |
| sektör + movers | ~3 |
| portföy batch quote | ~1 |
| teknik göstergeler (18 sembol × 3) | ~54 |
| haberler | ~1 |
| **FMP toplam** | **~67** |
| **websearch** | **4-7** |

⚠️ sabah raporu ~80 call kullandıysa, günlük toplam ~150 — dakikalık 2,500 limitin çok altında (güvenli)

---

# AŞAMA 2 — DURUM TESPİTİ

## 2a. sabah raporu ile karşılaştırma

sabah raporunu oku (`reports/daily/DAILY_SABAH_{TODAY}.md`) ve şu soruları cevapla:

**piyasa beklentisi tuttu mu?**
- sabah: "futures +%0.3, hafif toparlanma bekleniyor" → gerçek: SPY ?
- beklenen/beklenmeyen gelişmeler neler?

**risk ortamı değişti mi?**
- sabah: RISK-OFF/RISK-ON → şu an: ?
- VIX yönü: yükseliyor mu düşüyor mu?

**sektör RS değişti mi?**
- sabah güçlü olan sektörler hala güçlü mü?
- yeni güçlenen/zayıflayan sektör var mı?

## 2b. her portföy pozisyonu durum tespiti

her pozisyon için tek satırda durum:

```
format: SEMBOL | fiyat | günlük % | RSI | SMA50 vs | SMA200 vs | durum

durum kodları:
✅ GÜÇLÜ — trend yukarı, RSI 50-70, SMA'lar üzerinde
⚠️ DİKKAT — SMA kırılımı yakın, RSI aşırı bölgede, stop yakın
🔴 ACİL — stop-loss tetiklendi/tetiklenecek, büyük kayıp
💰 KAR AL — hedefe ulaştı veya aşırı alım
🔄 NÖTR — bekle, sinyal yok
```

**otomatik uyarı tetikleyicileri**:
- günlük değişim > +%5 veya < -%5 → acil inceleme
- RSI > 75 → aşırı alım uyarısı
- RSI < 30 → aşırı satım (fırsat mı tehlike mi?)
- fiyat SMA50 altına düştü → trend zayıflama
- fiyat SMA200 altına düştü → uzun vadeli trend kırılması
- stop-loss'a mesafe < %2 → acil uyarı
- portföy ağırlığı > %25 → yoğunlaşma riski

## 2c. swing pozisyonları durum tespiti

her swing pozisyonu için:

```
format: ID | SEMBOL | giriş | güncel | k/z% | chandelier stop | highest high | ATR | gün | durum

durum kodları:
⚠️ STOP YAKIN — fiyat kijun'a yaklaşıyor (<%2)
🔴 ÇIKIŞ SİNYALİ — chandelier stop tetiklenme veya TK cross aşağı
📈 TREND GÜÇLÜ — kumo üstü, tenkan > kijun, OBV yükseliş
📉 ZAYIFLIYOR — hacim ayrışması veya OBV düşüş
🔄 NÖTR — sinyal yok, ichimoku yapı korunuyor
```

**chandelier trailing stop güncelleme kuralı (ichimoku v2)**:
```
FMP historical data ile ichimoku + chandelier stop hesapla
→ chandelier stop güncellendi mi (highest_high artınca)? evet → stop yukarı çek
→ stop ASLA aşağı çekilmez (en yüksek kijun korunur)
→ çıkış sinyali var mı? acil olanlar hemen uygulanır
```

---

# AŞAMA 3 — AKSİYON KARARLARI

> ⚠️ **PLAYBOOK KONTROLÜ**: her karar vermeden önce `docs/TRADING_PLAYBOOK.md` kurallarını kontrol et.
> ⚠️ **KARAR ÇERÇEVESİ**: yeni giriş kararlarında `docs/DECISION_FRAMEWORK.md` uygula (GO/NO-GO 10 soru, düşünce zinciri, kırmızı takım testi, önyargı kontrolü).
> - yeni giriş → K-01 (makro veri), K-02 (kriz rallisi), K-03 (VIX + small cap), K-13 v4.1 (sektör bazlı VIX), K-17/K-18 (insider check)
> - çıkış → K-06 (stop override), K-07 (trailing stop), K-08 (momentum yoksa çık), K-09 (stop yakın erken çık)
> - swing → K-14 (ardışık 3+ zarar → dur), K-19 (XLP hariç), K-20 (RS dead cat bounce)
> - ichimoku giriş: kumo kırılımı / kijun bounce + hacim teyidi + SMA200 filtre
> - temel analiz: claude hisse bazında değerlendirir, sabit rasyo filtresi yok
> - kural ihlali gerekiyorsa gerekçeyi açıkça yaz

## 3a. karar matrisi — portföyler

her pozisyon için şu ağaçtan geç:

```
1. STOP-LOSS TETİKLENDİ Mİ?
   evet → 🔴 HEMEN SAT (duygusal karar yok)
   hayır → devam

2. HEDEF FİYATA ULAŞTI MI?
   evet → 💰 kar al (kısmi/tam)
   hayır → devam

3. TEZ BOZULDU MU?
   - temel verilerde kötüleşme? (earnings miss, temettü kesintisi, guidance düşürme)
   - sektör yapısal zayıflama? (sadece günlük dalgalanma değil)
   - korelasyon riski? (aynı sektörde çok fazla yoğunlaşma)
   evet → ⚠️ pozisyon küçült veya kapat
   hayır → devam

4. PORTFÖY DENGESİ BOZULDU MU?
   - bir pozisyon > %25 ağırlık?
   - bir sektör > %40 ağırlık?
   evet → 🔄 rebalance düşün
   hayır → devam

5. TEKNİK DURUM?
   - RSI > 75 + SMA'lar üzerinde → kar alma düşünülebilir
   - RSI < 30 + SMA'lar üzerinde → dip alım fırsatı
   - SMA200 altına kırılım → trend dönüşü uyarısı

6. HİÇBİR TETİK YOK → ✅ TUT, bir sonraki güne bekle
```

## 3b. karar matrisi — swing trade

her swing pozisyonu için:

```
0. ICHİMOKU SEVİYE TAKİBİ
   FMP historical data ile ichimoku + chandelier stop hesapla
   → kijun değişti mi? (trailing stop güncelleme)
   → çıkış sinyali var mı? (chandelier stop tetiklenme, TK cross aşağı, kumo'ya giriş)
   → hacim uyarısı var mı? (düşen hacim + yükselen fiyat = zayıflama)

1. STOP-LOSS KESİLDİ Mİ?
   fiyat < stop_loss (kijun veya kumo) → 🔴 %100 SAT, closed.json'a kaydet
   hayır → devam

2. KİJUN ALTI KAPANIŞ?
   fiyat kijun altında kapandı → fark > %0.5 ise hemen çık, < %0.5 ise yarın teyit bekle
   hayır → devam

3. TK CROSS AŞAĞI? (filtreli — v2.1'de giriş sinyali olarak kaldırıldı, çıkışta savunmacı kullanım)
   tenkan kijun'u aşağı kesti:
   → fark > %1 VE hacim > 1.0x ortalama → çık (güçlü sinyal)
   → fark > %0.5 ama hacim düşük → yarın teyit bekle
   → fark < %0.5 → sahte sinyal olasılığı yüksek, hacim + OBV teyidi olmadan çıkma
   hayır → devam

4. TRAİLİNG STOP GÜNCELLE
   chandelier stop güncellendi mi (highest_high artınca) → stop yukarı çek (stop ASLA aşağı çekilmez)
   en yüksek kijun değeri korunur

5. HACİM DURUMU?
   - OBV yükseliyor + fiyat yükseliyor → sağlıklı, tut
   - OBV düşüyor + fiyat yükseliyor → ayrışma, dikkat
   - 3 gün düşen hacim + yükselen fiyat → uyarı, trailing sıkılaştır

6. HİÇBİR TETİK YOK → ✅ TUT
```

## 3c. portföyler arası korelasyon kontrolü

> **SEKTÖR EXPOSURE TABLOSU**: docs/DECISION_FRAMEWORK.md bölüm 5 formatında hesapla.

yeni pozisyon açmadan önce veya mevcut durumu değerlendirirken:

```
kontrol 1: aynı hisse birden fazla portföyde var mı?
- swing + portföy çakışması kabul edilebilir (farklı zaman ufku)
- iki portföyde aynı hisse → bilinçli karar mı yoksa hata mı?

kontrol 2: sektör yoğunlaşması
- 3 portföy toplamında bir sektörün toplam ağırlığı > %30 → uyar
- örnek: dengeli'de XLE + agresif'te tech hisseler + swing'de enerji hissesi = aşırı exposure

kontrol 3: yön korelasyonu
- tüm portföyler aynı yönde mi hareket ediyor? (çeşitlendirme çalışıyor mu?)
- temettü portföyü piyasa düşerken yükseliyorsa → hedge fonksiyonu çalışıyor ✅
- hepsi aynı anda düşüyorsa → korelasyon riski ⚠️
```

## 3d. yeni pozisyon fırsatları — PROAKTİF TEMATİK TARAMA

> **felsefe**: claude kendi başına düşünür. haberleri okur, sektörel trendleri analiz eder, hangi tema öne çıkıyor saptar, o temadaki tedarik zincirinin her katmanını araştırır. zeynel'in söylemesini beklemez. watchlist'e ekleyip beklemez, uygun setup'a giriş yapar.
>
> **temel prensip**: AI her sektörü etkiliyor. çip tasarımı (NVDA) herkesin bildiği katman. ama çipi üretmek için ekipman, kimyasal, gaz, wafer, soğutma, trafo, bakır, optik fiber, nadir toprak lazım. bu alt katmanlar daha az kalabalık, daha ucuz ve seküler büyümeden faydalanıyor.

### kaynak 0: TEMATİK TEDARİK ZİNCİRİ TARAMASI (her seansta zorunlu)

aktif temaları ve her temanın tedarik zinciri katmanlarını tara:

```
AI TEDARİK ZİNCİRİ KATMANLARI:
  çip tasarımı:     NVDA, AMD, MRVL, AVGO, CRDO
  çip ekipmanı:     ASML, AMAT, LRCX, KLAC, CAMT, ONTO
  kimyasal/malzeme: ENTG, MKSI, PLAB, CCMP, LIN, APD
  optik bağlantı:   COHR, LITE, GLW, AAOI
  güç altyapısı:    POWL, VRT, ETN, PWR, GNRC
  soğutma/termal:   VRT, TT, JCI
  veri merkezi:     DLR, EQIX
  enerji:           COP, XOM, CVX (hepsini besleyen yakıt)
  nadir toprak:     MP, FCX, BHP

SAVUNMA/UZAY:       LMT, RTX, GE, RKLB, KTOS
ENERJİ GEÇİŞİ:     FSLR, ENPH, NEE, VST
```

claude her seansta:
1. web aramasıyla güncel piyasa temalarını/haberlerini oku
2. hangi katman öne çıkıyor belirle (kazanç açıklamaları, yeni kontratlar, darboğazlar)
3. o katmandaki hisseleri ichimoku ile tara
4. güçlü setup'lara giriş yap (watchlist'e ekleme yerine)

### kaynak 1-5: (mevcut geniş ağ tarama)

5 kaynaktan aday topla, tekrar edenleri birleştir:

```python
# kaynak 1: FMP biggest-gainers (momentum)
gainers = fmp_get("biggest-gainers", {"limit": 30})
# filtre: price > $15, volume > 500K, market cap > $3B

# kaynak 2: FMP screener — güçlü sektörlerden
# sektör performans snapshot'tan en güçlü 3 sektörü al
for sektor in en_guclu_3_sektor:
    fmp_get("company-screener", {
        "sector": sektor,
        "marketCapMoreThan": 3000000000,
        "volumeMoreThan": 500000,
        "priceMoreThan": 15,
        "exchange": "NYSE,NASDAQ",
        "isActivelyTrading": "true",
        "limit": 15
    })

# kaynak 3: mevcut watchlist (data/watchlist.json)
# tetiklenen seviyeler, urgency=high olanlar

# kaynak 4: portföy temaları (AI altyapı, enerji, savunma vb.)
# temaya uygun bilinen hisseler

# kaynak 5: finviz websearch (52W high, unusual volume)
# websearch: "finviz screener 52 week high unusual volume mid cap"
```

**hedef**: 20-30 benzersiz aday. portföyde olanları çıkar.

### adım 2: hızlı ön filtre (SMA50 + SMA200)

her aday için SMA50 ve SMA200 çek. kumo üstü olma ihtimali yüksek olanları seç:

```python
for sym in adaylar:
    sma50 = fmp("technical-indicators/sma", symbol=sym, periodLength=50)
    sma200 = fmp("technical-indicators/sma", symbol=sym, periodLength=200)
    # fiyat > SMA50 VE fiyat > SMA200 → ichimoku taramasına gönder
    # fiyat < SMA50 → elenir (kumo altında olma ihtimali yüksek)
```

**hedef**: 20-30'dan 10-15 adaya düşür.

### adım 3: ichimoku tam tarama

```bash
FMP screener → ichimoku 4/4 tarama (bkz. SWING_SYSTEM_V2.md bölüm 9)
```

script her sembol için otomatik hesaplar:
- ichimoku seviyeleri (tenkan, kijun, kumo, chikou)
- giriş sinyalleri (kumo kırılımı, kijun bounce)
- çıkış sinyalleri (kijun altı, TK cross aşağı)
- hacim analizi (oran, OBV trend, teyit seviyesi)
- ATR ve dinamik stop seviyesi
- SMA200 uzun vadeli filtre

### adım 4: claude temel değerlendirme

script "GİRİŞ ✅" veya "GİRİŞ ⚠️" veren hisseler için claude hisse bazında değerlendirir:

- sektör bağlamı (utilities yüksek borç normaldir, enerji gelir döngüseldir)
- şirketin hikayesi ve katalizörü
- mevcut portföy ile korelasyon
- risk/ödül dengesi
- VIX ortamı (K-13)

**sabit rasyo filtresi yok.** D/E, FCF, marj gibi metrikler sektör ve şirkete göre yorumlanır.

### adım 5: giriş kararı

sinyal + temel değerlendirme + portföy dengesi → giriş/bekle/geç kararı.

```
giriş koşulları (birini sağlaması yeterli):

A) SİNYAL GİRİŞİ (ideal):
1. ichimoku giriş sinyali var (kumo kırılımı / kijun bounce)
2. hacim teyidi (en az 1.0x ortalama, ideal 1.2x+)
3. SMA200 üstünde
→ tam veya yarım pozisyon (VIX'e göre)

B) TREND DEVAM GİRİŞİ (güçlü trend varken):
1. ichimoku 4/4 güçlü yükseliş (kumo üstü + tenkan>kijun + chikou pozitif + yeşil kumo)
2. OBV yükseliş (alıcılar aktif)
3. stop mesafesi >%5 (2x ATR uygun)
4. SMA200 üstünde
→ yarım pozisyon (trend güçlü ama spesifik sinyal yok, dikkatli giriş)
→ trend devam ederse ve kijun bounce veya yeni kırılım gelirse tamamla

C) ORTAK KOŞULLAR (her giriş için):
5. claude temel değerlendirmesi olumlu
6. portföy korelasyonu uygun (aynı alt sektörde 3'ten fazla pozisyon yok)
7. K-13 v4.1: kriz tipine göre sektör bazlı VIX kuralı (faydalanıcı sektörlere VIX 28'e kadar tam, duyarlılara 22'den itibaren yarım)
8. 2x ATR bazlı stop ve pozisyon boyutlandırma
```

### portföy yeni ekleme fırsatları

**her portföy için ayrı filtre**:

**dengeli portföy** ($100K): multi-sector value + momentum
- güçlü sektör RS gösteren hisseler
- P/E makul (<25), momentum pozitif
- mevcut sektör dağılımıyla çakışmayan

**agresif portföy** ($400K): AI tedarik zinciri tematik, yıllık %30+ hedef
- tedarik zinciri katmanlarından (ekipman, kimya, güç, optik, soğutma) güçlü hisseler
- ichimoku 4/4 bullish veya sinyal bazlı giriş
- pozisyon büyüklüğü: $20K-$70K, max 6 eşzamanlı pozisyon
- stop: 2x ATR(14) trailing
- nakit oranı yüksekse ve kaliteli setup varsa → kademeli giriş
- zayıfı kes, kazananı büyüt prensibi

**değer + temettü portföyü** ($100K): tema + kalite + momentum puanlama sistemi
- detay: docs/DIVIDEND_SYSTEM.md
- 5 katman: tema (25p) + temettü kalitesi (25p) + büyüme (20p) + momentum (15p) + değerleme (15p)
- giriş eşiği: skor ≥65, max 6 pozisyon

## 3e. satış/çıkış değerlendirmesi

**portföy hissesi satış nedenleri**:
```
1. stop-loss tetiklendi (agresif: 2x ATR(14), dengeli %8, temettü: tema/kalite/skor bazlı çıkış — bkz. DIVIDEND_SYSTEM.md)
2. tez bozuldu (temel verilerde kötüleşme)
3. sektör RS sürekli zayıf (3+ gün negatif RS, trend dönüşü)
4. daha iyi fırsat var (aynı sektörde/temada daha güçlü alternatif)
5. portföy ağırlık dengesizliği
6. kar realizasyonu (özellikle RSI > 75 + hedef aşılmış)
```

**satış uygulama süreci** (SEN KARAR VER kuralı geçerli — onay istenmez):
```
- tüm satışlar (acil, stratejik, kar alma) doğrudan uygulanır
- playbook kurallarıyla çapraz kontrol yap, gerekçeyi chat'te açıkla
- JSON güncelle, CSV kaydet, git push, telegram bildirim gönder
- onay istemek = kural ihlali
```

---

# AŞAMA 4 — UYGULAMA

## 4a. trade işlemleri

**her satış için**:
1. portföy JSON'undan pozisyonu kaldır
2. `nakit.miktar += adet × satis_fiyati`
3. portföy `transactions[]` listesine SATIŞ kaydı ekle
4. `data/transactions.csv` dosyasına satır ekle
5. swing ise → `data/swing/closed.json`'a ekle (tüm zorunlu alanlar: cikis_tarihi, cikis_fiyati, kar_zarar_yuzde, cikis_nedeni, sonuc, ders)
     → docs/POST_TRADE_REVIEW.md uygula: process_score, root_cause, corrective_action, bias_detected alanlarını doldur
6. `data/summary.json` güncelle

**her alış için**:
1. portföy JSON'unda `pozisyonlar[]` dizisine ekle (tüm zorunlu alanlar)
2. `nakit.miktar -= adet × fiyat`
3. portföy `transactions[]` listesine ALIŞ kaydı ekle
4. `data/transactions.csv` dosyasına satır ekle
5. swing ise → `data/swing/active.json`'a ekle (zorunlu alanlar: id, giris_tarihi, giris_fiyati, giris_sinyali, stop_loss, stop_tipi, kijun_sen, kumo_ust, kumo_alt, tenkan_sen, atr_14, giris_nedeni, katalizor, tez, risk, tarama_yontemi)
6. `data/summary.json` güncelle

## 4b. fiyat güncellemesi

trade olmasa bile tüm JSON dosyalarını güncelle:
```python
for each portfolio JSON:
    for each position:
        guncel_fiyat = quote['price']
        gunluk_degisim_yuzde = quote['changesPercentage']  # seans açıkken güvenilir, kapalıyken 0 dönebilir → manuel: ((price-previousClose)/previousClose)*100
        guncel_deger = adet × guncel_fiyat
        kar_zarar = guncel_deger - yatirim
        kar_zarar_yuzde = (kar_zarar / yatirim) × 100
        agirlik_yuzde = (guncel_deger / toplam_deger) × 100
        son_guncelleme = datetime.now().isoformat()
    
    toplam_deger = sum(pozisyon.guncel_deger) + nakit.miktar
    toplam_getiri_yuzde = ((toplam_deger - baslangic_sermaye) / baslangic_sermaye) × 100

for swing active:
    for each position:
        guncel_fiyat = quote['price']
        guncel_kar_zarar_yuzde = ((guncel - giris) / giris) × 100
        tutulan_gun = (today - giris_tarihi).days
        trailing stop güncelle (sadece yukarı)
        son_guncelleme = datetime.now().isoformat()
```

## 4c. watchlist güncellemesi

`data/watchlist.json` güncelle (tek merkezi watchlist — tüm portföyler + swing):
```
- mevcut adayların fiyatlarını güncelle
- tetiklenen giriş seviyesi varsa → "urgency": "high" yap + ⚠️ WATCHLIST ALARMI ver
- her adayın hedef_portfoy alanını kontrol et (swing/agresif/dengeli/temettü)
- artık geçerli olmayan adayları haric_tutulanlar'a taşı (neden ile)
- yeni aday varsa ekle (zorunlu alanlar: sembol, guncel_fiyat, sektor, hedef_portfoy, hedef_giris, hedef_fiyat, stop_loss, urgency, ekleme_tarihi)
- portföy ve tedarik zinciri adayları da burada (AMAT, KLAC, LITE, COP, LMT vb.)

⚠️ ÖNEMLİ: data/swing/watchlist.json KALDIRILDI — artık tek watchlist data/watchlist.json
⚠️ ÖNEMLİ: portföy JSON'larında watchlist[] KULLANILMAZ — her şey merkezi dosyada
```

## 4d. git commit + push

```bash
# trade varsa:
git commit -m "[ALIŞ] Portföy - SEMBOL @FİYAT - neden"
git commit -m "[SATIŞ] Portföy - SEMBOL @FİYAT - neden"
git commit -m "[SWING-GİRİŞ] SEMBOL @FİYAT - neden"
git commit -m "[SWING-ÇIKIŞ] SEMBOL @FİYAT - sonuç +/-%X"

# trade yoksa:
git commit -m "[GÜNCELLEME] seans içi fiyat güncellemesi - {tarih}"

# watchlist güncellemesi:
git commit -m "[WATCHLIST] merkezi watchlist güncellendi - {yeni aday varsa belirt}"
```

## 4e. telegram bildirimleri (git push'tan SONRA)

```bash
# her alış/satış/stop aksiyonunda:
python scripts/telegram_notify.py --type action --symbol SEMBOL --price FIYAT --action ALIŞ/SATIŞ/STOP/KAR_AL --details "detay"

# stop'a %2'den yakın pozisyon tespit edildiğinde:
python scripts/telegram_notify.py --type alert --symbol SEMBOL --price FIYAT --stop STOP_FIYAT

# seans özeti (her faz sonunda):
python scripts/telegram_notify.py --type session --theme "günün teması özeti"

# NOT: iç sistem detayları (kural değişiklikleri, skor açıklamaları vb.) telegram'a GÖNDERİLMEZ
```

---

# AŞAMA 5 — KULLANICIYA ÖZET

## rapor formatı (chat'te göster, dosya oluşturmaya gerek yok)

```markdown
## 🔔 seans içi güncelleme — {tarih} {saat} TR

### twitter takip özeti (faz 1)

| hesap | tweet | sembol | yorum |
|-------|-------|--------|-------|
| @xxx | [özet] | $XXX | [kısa yorum] |

öne çıkan:
- @hesap: [önemli tweet özeti — portföy bağlantısı]

---

### piyasa durumu
SPY: $XXX (±%X) | QQQ: $XXX (±%X) | VIX: XX
risk ortamı: RISK-ON/OFF | sabahtan değişim: [aynı/değişti → neden]

güçlü sektörler (RS): ...
zayıf sektörler (RS): ...

### acil aksiyonlar (varsa)
🔴 SATIŞ: SEMBOL — neden (stop tetiklendi / tez bozuldu)
💰 KAR AL: SEMBOL — neden (hedefe ulaştı)

### portföy özeti
| portföy | değer | günlük % | durum |
|---------|-------|----------|-------|
| dengeli | $XXX | ±%X | ✅/⚠️/🔴 |
| agresif | $XXX | ±%X | ... |
| temettü | $XXX | ±%X | ... |
| **toplam** | **$XXX** | **±%X** | |

dikkat gerektiren pozisyonlar:
- SEMBOL: neden (RSI/SMA/stop yakın/aşırı alım)

### swing durumu
| ID | sembol | k/z% | stop mesafe | durum |
|----|--------|------|------------|-------|
| ... | ... | ... | ... | ... |

aksiyonlar:
- [yapılan trade'ler]
- [trailing stop güncellemeleri]
- [watchlist değişiklikleri]

### fırsatlar
📌 swing adayı: SEMBOL — neden, giriş seviyesi, R:R
📌 portföy adayı: SEMBOL — hangi portföye, neden

### prediction markets güncellemesi (sabahtan değişim)
- fed rate cut: %XX → %XX (↑↓%X) — [etkisi: ...]
- [gündemdeki olay]: %XX → %XX — [etkisi: ...]
(değişim < %5 ise → "PM stabil, önemli değişim yok")

### sonraki kontrol
- seans fazı: [şu an faz 1/2/3 — bir sonraki faz ne zaman]
- saat XX:XX'de kontrol edilecek: [neden — earnings AMC, makro veri, vb.]
- bugün AMC earnings: [hangi hisseler kapanıştan sonra raporlayacak — portföy/sektör etkisi]
- kapanış güncellemesi: [JSON fiyat güncelleme yarın 14:00 günlük raporda yapılacak]
```

---

# KARAR AĞACI — HIZLI REFERANS

```
SEANS AÇILDI (FAZ 1: TR 16:30-17:30)
│
├─ ACİL KONTROL (ilk 5 dk)
│  ├─ stop-loss tetiklenen var mı? → SAT
│  ├─ gap-down > %5 olan var mı? → değerlendir (ilk 15dk bekle)
│  └─ sabah BMO earnings sonuçları → etki analizi
│
├─ PİYASA DURUMU (ilk 15 dk)
│  ├─ SPY/QQQ yönü → risk ortamı belirle
│  ├─ sektör RS → güçlü/zayıf sektörler
│  └─ VIX yönü → volatilite beklentisi
│
├─ SABAH PLANI UYGULAMASI (30 dk)
│  └─ günlük rapordaki acil aksiyonları uygula
│
MID-SESSION (FAZ 2: TR 18:00-21:00)
│
├─ PORTFÖY TARAMA (30 dk)
│  ├─ her pozisyon: fiyat, RSI, SMA kontrol
│  ├─ uyarı tetikleyicileri kontrol
│  └─ korelasyon kontrolü (sektör yoğunlaşması)
│
├─ SWING TARAMA (30 dk)
│  ├─ FMP historical data ile ichimoku + chandelier stop hesapla (stop/çıkış/trailing güncelle)
│  ├─ GENİŞ HAVUZ TARAMA:
│  │  ├─ FMP biggest-gainers + screener (güçlü sektörlerden)
│  │  ├─ watchlist tetiklenen seviyeler
│  │  ├─ SMA50+SMA200 ön filtre → ichimoku taramasına gönder
│  │  └─ FMP historical data ile ichimoku hesapla ADAY1,ADAY2,...
│  ├─ sinyal veren adaylar için claude temel değerlendirme
│  └─ boş slot varsa → en iyi adayı giriş yap
│
├─ PREDİCTION MARKETS (5 dk)
│  ├─ kalshi fed rate → sabahtan değişim?
│  ├─ polymarket gündem → ani hareket?
│  └─ >%10 değişim → strateji etkisini değerlendir
│
├─ FIRSATLAR (15 dk)
│  ├─ güçlü RS sektörlerinden aday
│  ├─ earnings beat momentum
│  ├─ dip alım fırsatları (RSI < 30 + kaliteli hisse)
│  └─ portföy dengeleme ihtiyacı
│
POWER HOUR (FAZ 3: TR 22:00-23:00)
│
├─ FİNAL AKSİYONLAR
│  ├─ bekleyen kar alma / pozisyon ayarlama
│  ├─ trailing stop'ları final güncelle
│  └─ kapanış öncesi son fiyat kontrolü
│
├─ TWİTTER GÜNCELLEMESİ
│  └─ faz 1'den bu yana yeni tweet varsa çek → önemli gelişme varsa bildir
│
├─ YARIN HAZIRLIK
│  ├─ bugün AMC earnings açıklayacak hisseler → not et
│  ├─ yarının sabah raporu için flag'ler
│  └─ after-hours izlenecek hisseler
│
└─ GÜNCELLEME + COMMIT
   ├─ trade varsa → JSON güncelle + commit
   ├─ data/watchlist.json güncelle + commit
   └─ fiyat güncelleme (seans içi — final güncelleme yarın 14:00 raporda)
```

---

# ÖNEMLİ KURALLAR

## SEN KARAR VER kuralı (tüm seans aksiyonları)

seans içi TÜM aksiyonlarda (kısmi kâr alma, trailing stop, stop-loss satışı,
yeni giriş, fiyat güncellemesi, pozisyon kapatma, kural esnetme/uygulama)
Zeynel'den onay istenmez. soru sormadan doğrudan karar ver ve uygula.
playbook kurallarına (K-01 ile K-20, K-13 v4.1 sektör bazlı VIX) uygunluk kontrolü yapıldıktan sonra
son karar her zaman Claude'da. onay istemek = kural ihlali.

## otomatik yapılan işlemler (hepsi)
- yeni pozisyon açma/kapatma (playbook kurallarına uygunsa)
- kısmi kâr alma (K-11 tetiklenirse)
- stop-loss satışı
- trailing stop güncelleme (sadece yukarı)
- fiyat güncellemesi (tüm JSON'lar)
- watchlist güncellemesi
- portföy rebalance kararları
- tutulan_gun artırma, ağırlık yüzdesi hesaplama

## yapma!
- stop-loss'u aşağı çekme (ASLA)
- duygusal karar (panik satış, FOMO alış)
- sabah planında olmayan büyük pozisyon açma (önce analiz)
- aynı sektörde 3'ten fazla swing pozisyonu
- portföy ruhuyla uyuşmayan hisse ekleme (temettü portföyüne growth stock gibi)
- nakit oranını %5 altına düşürme (acil fırsat hariç)

---

## SELF-VALIDATION (seans içi)

detaylı kurallar: `docs/SELF_VALIDATION.md`

### her FMP çağrısından sonra (katman 1)
```
✓ yanıt boş değil mi?
✓ fiyatlar mantıklı mı? (> 0, < 100K, |değişim| < %50)
✓ |changesPercentage| > %20 → haber teyidi yap
```

### her karar önerisinde (katman 3)
```
✓ "SAT" diyorsan → somut neden var mı? (stop, tez, veri)
✓ "AL" diyorsan → RSI/SMA/momentum destekliyor mu?
✓ portföy kurallarıyla uyumlu mu?
✓ nakit yeterli mi?
✓ GO/NO-GO 10 soru geçti mi? (docs/DECISION_FRAMEWORK.md bölüm 1)
✓ düşünce zinciri yazıldı mı? (docs/DECISION_FRAMEWORK.md bölüm 2)
✓ bilişsel önyargı kontrolü yapıldı mı? (docs/DECISION_FRAMEWORK.md bölüm 4)
✓ dünkü hareket yüzünden aşırı tepki mi veriyorsun? (yakınlık yanılgısı)
✓ "herkes alıyor" mantığıyla mı öneriyorsun? (FOMO)
```

### JSON güncelleme sonrası (katman 2a)
```
✓ sayısal tutarlılık (yatirim, guncel_deger, kar_zarar, nakit)
✓ trailing stop sadece yukarı gitmiş
✓ ağırlık toplamı ≈ %100
```

---

> son güncelleme: 6 nisan 2026 v2.2 | finzora ai
