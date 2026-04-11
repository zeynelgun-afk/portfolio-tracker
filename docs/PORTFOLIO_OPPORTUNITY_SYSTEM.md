# PORTFÖY FIRSAT TARAMA SİSTEMİ v1.0

> **amaç**: 3 portföy için sistematik, filtreli, karar matrisi tabanlı aday tarama ve watchlist yönetimi
> **referans prompt**: `docs/prompts/DAILY_PART1C_PORTFOY.md`
> **son güncelleme**: 9 nisan 2026 (skor sistemi kod ile senkronize edildi, eski EPS surprise/RS rank/analyst consensus puanları kaldırıldı)
> **versiyon**: 1.1

bu dosya 3 portföyün (dengeli, agresif, temettü) fırsat tarama kriterlerini, filtrelerini ve karar matrisini tanımlar. PART 1C promptu bu dosyanın kurallarını uygular.

---

## 1. GENEL MANTIK

**portföy fırsat taraması 4 aşamalıdır**:

1. **ön koşullar** (her portföy için) — boş slot sayısı, nakit pozisyonu, sektör konsantrasyon kapasitesi, mevcut pozisyonların sağlığı
2. **tarama evreni + portföy spesifik filtre** — FMP screener'dan ilgili portföy için uygun hisseler çekilir
3. **ortak filtreler** — K-04, K-05, K-17 her aday için mekanik uygulanır
4. **karar matrisi** — her aday için 5 aksiyondan biri: EKLE / BÜYÜT / DÖNDÜR / İZLE / GEÇ

**prensipler**:
- her gün tam tarama yapılır (hafif mod yok) — gürültülü olursa sonra ayarlanır
- mevcut pozisyonların ekleme/büyütme kararları yeni aday kararlarından ÖNCE değerlendirilir (zaten sahip olunan güçlü pozisyonları büyütmek yeni pozisyona girmekten daha az risklidir)
- watchlist sadece seviyeye ulaşmamış adayları tutar, ulaşanlar giriş planına geçer
- 14 gün watchlist'te kalıp momentum bozulan adaylar otomatik elenir

---

## 2. PORTFÖY SPESİFİK TARAMA KRİTERLERİ

### 2a. Dengeli Portföy ($100K, max 6 pozisyon)

**karakter**: multi-sector value + momentum blend. güvenlik ağırlıklı ama stagnasyon istemeyen. her sektörden en iyi 1-2 hisse. amaç %8-15 yıllık getiri + sermaye koruma.

**FMP screener parametreleri**:
```
marketCapMoreThan=5000000000          (mcap >$5B)
priceMoreThan=10
volumeMoreThan=500000
country=US
peRatioLessThan=25                    (değerleme disiplini)
peRatioMoreThan=5                     (kayıp eden şirket değil)
betaLessThan=1.5                      (aşırı volatil istemiyoruz)
```

**portföy spesifik filtreler** (sırayla uygulanır):
1. **ROIC >%10** — sermaye verimliliği (FMP key-metrics-ttm `returnOnInvestedCapital`)
2. **6 aylık fiyat momentum >%0** — pozitif trend (FMP stock-price-change `6M`)
3. **SMA50 üstü** — K-04 trend filtresi
4. **EPS büyümesi son 3 yıl pozitif** — FMP income-statement-growth (3Y CAGR)
5. **debt/equity <2** — finansal sağlık
6. **sektör çeşitliliği zorunluluğu** — mevcut portföyde olmayan sektörler öncelikli

**skor sistemi** (max ~18, kod: `scripts/portfolio_scan_common.py::score_dengeli`):
- P/E <15: +2, <25: +1
- ROIC >%15: +3, >%12: +2, >%10: +1
- 6M momentum >%20: +3, >%10: +2, >%0: +1
- RSI 40-60 (nötr bölge): +2
- SMA50 üstü: +2
- Golden cross (50>200): +1
- FCF yield >%5: +2, >%3: +1
- Yeni sektör (mevcut portföyde yok): +2
- (opsiyonel) katalizör override max +2 — `apply_catalyst_override()` sıkı kuralları
- **eşik**: skor <6 GEÇ, 6-8 İZLE, 9+ EKLE (8 nisan 2026 kalibrasyonu)

### 2b. Agresif Büyüme Portföyü ($400K, max 10 pozisyon)

**karakter**: momentum + earnings surprise + AI tedarik zinciri v2 tezi. Yüksek beta, yüksek büyüme, yüksek risk. %30+ yıllık hedef. %8 stop, teknik disiplin zorunlu. AI tedarik zinciri 6 katmanı (ekipman, kimya, optik, güç, soğutma, DC) + enerji + rare earth önceliği.

**FMP screener parametreleri**:
```
marketCapMoreThan=10000000000         (mcap >$10B)
priceMoreThan=20
volumeMoreThan=1000000                (likidite zorunlu, momentum trade için)
country=US
betaMoreThan=0.8                      (momentum karakteri)
```

**portföy spesifik filtreler** (sırayla uygulanır):
1. **son çeyrek EPS surprise >%10** — FMP earnings-surprises (actualEPS vs estimatedEPS)
2. **RS rank >80** — 6 aylık getiri SPY'yi en az %15 geride bırakmış (FMP stock-price-change `6M` SPY ile karşılaştır)
3. **ortalama hacim oranı >1.5x** — son 10 gün ortalama hacim / 50 gün ortalama hacim
4. **SMA50 üstü** — trend teyidi
5. **RSI 40-75** — ne aşırı oversold ne aşırı overbought (75+ ise K-11 katman 1 alarmı)
6. **52W high'a yakın** — %15 mesafe içinde (FMP quote `yearHigh`)
7. **AI tedarik zinciri temaları öncelikli** — aşağıdaki sembol listesi önce değerlendirilir:
   - ekipman: ASML, AMAT, LRCX, KLAC, CAMT, ONTO, TER, UCTT, ACLS
   - kimya/materyaller: ENTG, MKSI, PLAB, LIN, APD, CCMP, MP (rare earth), FCX
   - optik: COHR, LITE, GLW, AAOI, FN, ANET (networking/optik)
   - güç: POWL, VRT, ETN, PWR, EME
   - soğutma: VRT, TT, JCI
   - veri merkezi: DLR, EQIX
   - enerji destek: COP, XOM (AI+enerji geçiş)
   - mobil/edge compute: QCOM, AVGO
   - memory: MU, SNDK, WDC (samsung tezi sonrası)

**skor sistemi** (max ~18, kod: `scripts/portfolio_scan_common.py::score_agresif`, quality guard rails dahil):
- 1M momentum >%20: +3, >%10: +2, >%0: +1
- 6M momentum >%50: +3, >%30: +2, >%15: +1
- P/E quality guard: <0 (negatif) -3, >80 -3, >60 -2, >40 -1
- ROIC >%25: +3, >%15: +2, >%10: +1, <0 -3, <%8 -1
- RSI 50-70 (güçlü): +2, 40-50 (nötr-zayıf): +1, >75 (aşırı alım): -1
- SMA50 üstü: +2
- Golden cross: +2
- 3M momentum >%15: +2
- (opsiyonel) katalizör override max +2
- **eşik**: skor <10 GEÇ, 10-13 İZLE, 14+ EKLE (8 nisan 2026 kalibrasyonu)

**not**: EPS surprise, RS rank, hacim oranı, 52W high mesafesi ve analyst consensus gibi eski puan kalemleri kodda yok. Bu metrikler portföy spesifik filtrelerde (yukarıda) ön koşul olarak kontrol edilir ama skora girmez. Momentum (1M/3M/6M) + kalite (ROIC/P/E guards) + teknik (RSI/SMA/GC) üçgeni daha az gürültülü sinyal veriyor.

### 2c. Değer + Temettü Portföyü ($100K, max 15 pozisyon)

**karakter**: yüksek kaliteli temettü ödeyicileri. istikrarlı nakit akışı, düşük değerleme, uzun vadeli tut. %8-12 yıllık getiri + %3-5 temettü. düşük volatilite, defensive ağırlıklı.

**FMP screener parametreleri**:
```
marketCapMoreThan=5000000000          (mcap >$5B)
priceMoreThan=10
volumeMoreThan=300000
country=US
peRatioLessThan=20                    (değer disiplini)
peRatioMoreThan=5                     (kayıp eden şirket değil)
dividendMoreThan=0.03                 (yield >%3)
betaLessThan=1.2                      (defensive)
```

**portföy spesifik filtreler** (sırayla uygulanır):
1. **temettü yield %3-8 arası** — çok yüksek yield (>%8) yield trap sinyali olabilir
2. **payout ratio <%75** — temettü sürdürülebilirliği (FMP ratios-ttm `payoutRatioTTM`)
3. **debt/equity <1.5** — finansal disiplin
4. **FCF pozitif ve stabil** — son 3 yıl pozitif operating cash flow (FMP cash-flow-statement)
5. **temettü artış geçmişi 5+ yıl** — FMP stock-dividend son 5 yıl yıllık ödemeler artış trendinde
6. **P/E <20** — aşırı değerleme filtresi
7. **SMA200 üstü VEYA RSI <40** — trend içinde ya da aşırı satım (değer + dönüş)

**skor sistemi** (max ~18, kod: `scripts/portfolio_scan_common.py::score_temettü`, yield trap koruması dahil):
- Yield %5-7: +3, %4-5: +2, %3-4: +1, **>%8: -2** (yield trap uyarı)
- Payout ratio <%50: +3, <%65: +2, <%75: +1, **>100%: -5** (YIELD TRAP — otomatik eleme)
- P/E <12: +3, <15: +2, <18: +1, <0 (negatif): -3
- ROIC >%15: +2, >%10: +1
- FCF yield >%5: +2, >0: +1, <0: -2
- SMA50 üstü: +1
- SMA200 üstü: +1
- Yeni sektör (mevcut portföyde yok): +2
- (opsiyonel) katalizör override max +2
- **eşik**: skor <6 GEÇ, 6-8 İZLE, 9+ EKLE (8 nisan 2026 kalibrasyonu)
- **KRİTİK**: payout >100% tetiklenirse rapora "YIELD TRAP" notu ve -5 cezasıyla otomatik GEÇ kararı verilir, aday EKLE eşiğini geçemez

---

## 3. ORTAK FİLTRELER (3 PORTFÖYE DE UYGULANIR)

her aday için sırayla çalıştırılır. birini geçemeyen aday TAMAMEN ELENİR.

### K-04: SMA50 trend filtresi
- fiyat > SMA50 → ✅ geçer
- fiyat < SMA50 ama RSI <30 ve oversold bounce sinyali → K-04 istisnası uygulanır, +1 gün teyit bekle
- fiyat < SMA50 ve RSI >30 → ❌ elenir

### K-05: earnings proximity
- sonraki 7 gün içinde earnings varsa → dengeli/temettü için ❌ elenir, agresif için ❌ elenir
- NOT: sadece swing için 2+ gün önceden tam çıkış gerekli. portföy pozisyonları için de yeni giriş yapma kuralı aynı şekilde geçerli (binary gap riski)

### K-17: korelasyon kontrolü
- adayın sektörü mevcut portföyde %25'ten fazla temsil ediliyorsa → ❌ elenir (konsantrasyon limiti K-12)
- aday aynı temadan 2+ pozisyon içeriyorsa (örn. AI tedarik zinciri 3 hisse zaten var) → yeni aynı katmandan olanlar elenir
- script: `scripts/k17_correlation_check.py SYMBOL`

### ~~K-18: insider trading~~ (KALDIRILDI — 11 Nisan 2026)
- Backtest sonucu: $5M+ insider satışı sonrası hisseler +2.1% kazandı (n=55). Kural ters çalışıyordu.
- `scripts/k18_insider_check.py` devre dışı. Detay: `reports/k_rules_backtest_2026-04-11.md`

### K-19: XLP dışlama (SWING için, portföy için DEĞİL)
- dengeli ve temettü portföyleri için bu filtre UYGULANMAZ (XLP defensive karakter portföyler için uygundur)
- agresif için XLP sektörü öncelikli değil ama otomatik eleme yok

### K-20: RS dead cat bounce filtresi
- hesaplama: RS oranı = sektörETF / SPY. RS20 = 20 iş günü RS değişimi, RS10 = 10 iş günü RS değişimi
- RS20 < 0 VE RS10 > 0 ise → ❌ elenir (sektör orta vadede zayıf ama kısa vadede sıçramış = dead cat)
- bu filtre agresif için zorunlu, dengeli ve temettü için öneri seviyesinde
- script: `scripts/k20_rs_filter.py SCAN_FILE`

---

## 4. KARAR MATRİSİ

her aday yukarıdaki filtreleri ve portföy spesifik skoru geçtikten sonra 5 karardan birine atanır:

### 4a. EKLE (yeni pozisyon)

**koşullar**:
- aday yeni (portföyde yok, watchlist'te yok)
- tüm ortak filtreler geçti
- portföy spesifik skor EKLE eşiğini geçti
- boş slot var (mevcut pozisyon sayısı < limit)
- sektör konsantrasyon K-12 limiti içinde
- nakit yeterli (min pozisyon büyüklüğü dengeli $15K, agresif $30K, temettü $8K)

**çıktı**:
- watchlist'e ekle (hedef giriş bandı, stop, hedef fiyat)
- aday "seviye bekliyor" statüsünde
- eğer mevcut fiyat hedef bandı içindeyse → BÖLÜM 4 giriş planına direkt taşı

### 4b. BÜYÜT (mevcut pozisyonu artır)

**koşullar**:
- aday zaten portföyde var
- mevcut pozisyon kazançta VE teknik trend devam ediyor (SMA50 üstü + RSI 50-75)
- K-12 konsantrasyon limiti büyütme sonrası AŞILMAZ
- tez teyit edildi (yeni pozitif katalist var)
- mevcut pozisyon ağırlığı hedef ağırlığın altında

**çıktı**:
- mevcut pozisyona +%20-50 eklenir (pozisyon boyutuna göre)
- stop seviyesi ağırlıklı ortalama maliyete göre yeniden hesaplanır (K-11 uyumlu)

### 4c. DÖNDÜR (zayıf pozisyonu iyi adaya çevir)

**koşullar (çift taraflı)**:
- mevcut bir pozisyon ZAYIF kriterini karşılıyor:
  - k/z <%-5 (kayıpta) VEYA
  - RSI <40 + SMA50 altı + son 1 ay RS rank <20 (momentum bozulmuş) VEYA
  - K-04 trend filtresini 3+ iş günü kaybetmiş
- aday güçlü kriteri karşılıyor (EKLE eşiğini geçmiş, aynı veya daha iyi beklenen getiri, DAHA İYİ teknik setup)
- sermaye transfer mantıklı (aday getiri beklentisi zayıf pozisyondan en az +%10 daha yüksek)

**çıktı**:
- zayıf pozisyon satılır (stop yerine manuel eksik çıkış)
- sermaye yeni adaya aktarılır
- transactions.csv'ye "DÖNDÜR: XXX → YYY" notu
- BÖLÜM 5 aksiyon planına taşı

**ÖNEMLI**: DÖNDÜR kararı günde maksimum 1 defa uygulanabilir. çok DÖNDÜR = overtrading.

### 4d. İZLE (watchlist'te tut)

**koşullar**:
- aday filtreleri geçiyor AMA skor EKLE eşiğinin altında (orta bölge)
- VEYA aday teknik olarak henüz hedef giriş bandı içinde değil (fiyat çok yüksek)
- VEYA makro koşullar engelleyici (VIX yüksek, ateşkes belirsizliği, earnings yakın)

**çıktı**:
- watchlist'e eklenir (veya mevcutsa güncellenir)
- urgency belirlenir: HIGH (hedef bantta, skor yüksek), MEDIUM (hedef yakın), LOW (uzak)
- `son_kontrol` tarihi güncellenir

### 4e. GEÇ (eleme)

**koşullar**:
- ortak filtrelerden birini geçemedi
- VEYA portföy spesifik minimum skoru tutturamadı
- VEYA daha önce bu sembol watchlist'te 14+ gün bekledi ve hala seviyeye ulaşmadı

**çıktı**:
- watchlist'te varsa çıkar, `haric_tutulanlar` listesine ekle
- sebep not düş
- 30 gün boyunca yeniden değerlendirilmez (çöp liste)

---

## 5. WATCHLIST MEKANİK YÖNETİMİ

her sabah PART 1C çalıştığında watchlist 4 kontrol geçirir:

### 5a. seviyeye ulaşma kontrolü
- her watchlist adayı için: fiyat `hedef_giris` bandı içinde mi?
- evetse → BÖLÜM 4 giriş planına taşı, urgency = ENTRY_ACTIVE
- K-04 teyit var mı? SMA50 üstünde mi? Evet → gerçek giriş planına taşı, onay al

### 5b. momentum bozulma kontrolü
- watchlist'teki aday son 5 gün SPY'yi %5+ geride bıraktıysa → momentum bozuldu
- ve RSI <35 ise → K-04 istisnası değerlendir, değilse elenme
- ve 14+ gün watchlist'te kaldıysa → otomatik elenme

### 5c. yeni aday ekleme
- bu sabah tarama sonuçlarından gelen yeni adaylar watchlist'e eklenir
- duplicate kontrolü: zaten varsa güncelle, yoksa yeni kayıt

### 5d. eleme (çöp toplama)
- 14 gün hedef altında + momentum bozuk → elenme
- fundamental katalist bozuldu (downgrade, earnings miss, SEC) → elenme
- portföyde zaten var olan sembol → elenme (büyütme kararı ayrı)

---

## 6. HEDEF POZİSYON BÜYÜKLÜKLERİ

### dengeli portföy
- min pozisyon: $15,000 (%15 porteöy)
- max pozisyon: $25,000 (%25 — K-12 limit)
- hedef pozisyon: $16,600 (%16.66 — eşit dağılım 6 pozisyon için)

### agresif portföy
- min pozisyon: $30,000 (%7.5)
- max pozisyon: $80,000 (%20 — K-12 limit)
- hedef pozisyon: $40,000 (%10 — eşit dağılım 10 pozisyon için)
- AI tedarik zinciri tek katman max 3 pozisyon

### temettü portföyü
- min pozisyon: $6,500 (%6.5)
- max pozisyon: $15,000 (%15 — K-12 limit)
- hedef pozisyon: $6,666 (%6.66 — eşit dağılım 15 pozisyon için)

---

## 7. WATCHLIST DOSYA YAPISI

dosya: `data/watchlist.json`

### mevcut şema (genişletilmiş)

```json
{
  "son_guncelleme": "2026-04-08T14:00:00",
  "not": "3 portföy için aday havuzu",
  "izleme_listesi": [
    {
      "sembol": "QCOM",
      "hedef_portfoy": "agresif",
      "guncel_fiyat": 124.07,
      "rsi": 32.2,
      "skor": 14,
      "sektor": "Teknoloji",
      "tema": "AI tedarik zinciri — mobil/edge compute",
      "urgency": "high",
      "ekleme_tarihi": "2026-04-07",
      "son_kontrol": "2026-04-08",
      "hedef_giris": "120-128",
      "hedef_fiyat_1": 139,
      "hedef_fiyat_2": 160,
      "stop_loss": 118,
      "r_r_orani": 3.8,
      "tez": "CPU darboğaz teması + ucuz forward P/E + AI mobile edge",
      "karsit_argumani": "momentum zayıf, tech sektör iran riski altında",
      "k_17_gecis": true,
      "k_18_gecis": true,
      "bekleme_gun": 1,
      "filtre_skoru": {
        "eps_surprise": "+%14",
        "rs_rank": 72,
        "volume_oran": 1.3,
        "52w_mesafe": "%6"
      }
    }
  ],
  "haric_tutulanlar": [
    {
      "sembol": "TSLA",
      "hedef_portfoy": "agresif",
      "cikarma_tarihi": "2026-04-02",
      "neden": "K-17 korelasyon: AI tedarik zinciri tema dolu",
      "yeniden_degerlendirme": "2026-05-02"
    }
  ]
}
```

### alan açıklamaları

| alan | tür | zorunlu | açıklama |
|------|-----|:-------:|----------|
| `sembol` | string | ✅ | ticker |
| `hedef_portfoy` | string | ✅ | "dengeli" / "agresif" / "temettü" |
| `guncel_fiyat` | float | ✅ | son kapanış |
| `rsi` | float | ✅ | RSI(14) |
| `skor` | int | ✅ | portföy spesifik skor |
| `sektor` | string | ✅ | türkçe sektör |
| `tema` | string | ❌ | alt tema (AI tedarik zinciri katmanı vb.) |
| `urgency` | string | ✅ | "high" / "medium" / "low" / "entry_active" |
| `hedef_giris` | string | ✅ | fiyat aralığı "120-128" |
| `hedef_fiyat_1` | float | ✅ | ilk hedef (kısmi kâr) |
| `hedef_fiyat_2` | float | ❌ | ikinci hedef |
| `stop_loss` | float | ✅ | stop seviyesi |
| `r_r_orani` | float | ✅ | risk/ödül oranı |
| `tez` | string | ✅ | 1 cümle yatırım tezi |
| `karsit_argumani` | string | ✅ | 1 cümle karşıt argüman |
| `k_17_gecis` | bool | ✅ | K-17 korelasyon geçti mi? |
| `bekleme_gun` | int | ✅ | watchlist'te kaç gündür (eleme kontrolü için) |
| `filtre_skoru` | object | ❌ | portföy spesifik metriklerin detayı |

---

## 8. TARAMA AKIŞI (PART 1C PROMPT İÇİN)

```
1. sabah raporunu oku (reports/daily/DAILY_SABAH_YYYY-MM-DD.md) — makro çerçeve al
2. mevcut portföyleri oku (data/portfolios/*.json)
3. mevcut watchlist oku (data/watchlist.json)
4. mevcut pozisyonlar için BÜYÜT/DÖNDÜR değerlendirmesi yap
5. FMP screener 3 kez çağrılır:
   a. dengeli için value+momentum filtre
   b. agresif için momentum+earnings filtre
   c. temettü için yield+value filtre
6. her 3 tarama sonucu için:
   a. ortak filtreler (K-04, K-05, K-17, K-20) uygulanır
   b. portföy spesifik skor hesaplanır
   c. karar matrisine göre aksiyon atanır
7. watchlist güncellemesi (seviyeye ulaşan, elenen, yeni eklenen)
8. rapor yazılır (aşağıda format)
9. data/watchlist.json güncellenir
10. git commit + push
```

---

## 9. ÖRNEK SKOR HESAPLAMA (QCOM için agresif portföy, yeni skor sistemi)

### ham veriler (7 nisan 2026 kapanış)
- fiyat: $124.07
- RSI 14: 32.2
- 1M momentum: ~-%8 (düşen)
- 3M momentum: ~+%3
- 6M momentum: ~+%12 (SPY +%3 → RS pozitif ama mutlak düşük)
- P/E: ~14 (tech için düşük, quality guard pozitif tarafta)
- ROIC: ~%28 (yüksek kalite)
- SMA50: $128 → fiyat altında ❌ (K-04 istisna kontrolü gerek)
- SMA200: $135 → fiyat altında ❌
- Golden cross: yok (fiyat her iki SMA altında)

### skor (score_agresif)
- 1M momentum -%8: +0 (pozitif bracket altında)
- 6M momentum %12: +0 (%15 altı)
- 3M momentum %3: +0 (%15 altı)
- P/E ~14: +0 (cezası yok, bonus da yok)
- ROIC %28: +3
- RSI 32: +0 (hiçbir aralığa girmiyor, aşırı satım cezası yok çünkü >75 değil)
- SMA50 üstü: +0 (altında)
- Golden cross: +0
- **toplam: 3**

### karar
- agresif eşik EKLE = 14, İZLE = 10
- skor 3 < 10 → **GEÇ**

### niteliksel katalizör override değerlendirmesi
CPU darboğazı tezi ve AVGO/Google ASIC haberi niteliksel katalizör olarak değerlendirilebilir. `apply_catalyst_override` kurallarına göre:
- max +2 puan → toplam skor 5 olur
- 5 hala 10'un altında → yine **GEÇ**
- override bu durumda skoru kurtaramaz

### ders
QCOM'un teknik durumu (fiyat her iki SMA altında, 1M/3M/6M momentum zayıf) sistematik tarama için hazır değil. Tez güçlü olabilir ama sistematik giriş için fiyatın SMA50 üstüne çıkıp momentum teyidi vermesi bekleniyor. Watchlist'te "izle" statüsünde tutulur, skoru 10+ olunca otomatik yükselir. Bu sübjektif "CRITICAL urgency" atamalarının yerine mekanik eşiği koyuyor — iyimser tezi filtrenin önüne geçirmiyor.

---

## 10. KOD İMPLEMENTASYONU (GELECEK)

şu an skill + prompt ile manuel uygulanıyor. gelecek adımlar:

- `scripts/portfolio_scan_balanced.py` — FMP screener + dengeli filtre + skor
- `scripts/portfolio_scan_aggressive.py` — FMP screener + agresif filtre + skor
- `scripts/portfolio_scan_dividend.py` — FMP screener + temettü filtre + skor
- `scripts/watchlist_manager.py` — eleme + yeni ekleme + seviye kontrolü

her biri json çıktı verir, PART 1C promptu bunları okur, karar matrisine göre aksiyon yazar.

---

## 11. KALİTE KONTROL

PART 1C raporu yazıldıktan sonra kontrol edilir:

- [ ] her portföy için tarama sonucu var mı?
- [ ] karar matrisi uygulandı mı? (her aday EKLE/BÜYÜT/DÖNDÜR/İZLE/GEÇ etiketli mi?)
- [ ] filtreler mekanik uygulandı mı? (K-04, K-05, K-17 her aday için)
- [ ] watchlist güncel mi? (seviyeye ulaşanlar taşındı mı, 14 gün dolanlar elenlendi mi?)
- [ ] data/watchlist.json dosyası push edildi mi?
- [ ] mevcut pozisyonlar için BÜYÜT/DÖNDÜR değerlendirmesi yapıldı mı?
- [ ] skor hesaplamaları şeffaf mı? (her puan gerekçeli mi?)

---

*finzora ai — portföy fırsat tarama sistemi v1.0*
