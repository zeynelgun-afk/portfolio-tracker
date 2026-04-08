# PORTFÖY FIRSAT TARAMA SİSTEMİ v1.0

> **amaç**: 3 portföy için sistematik, filtreli, karar matrisi tabanlı aday tarama ve watchlist yönetimi
> **referans prompt**: `docs/prompts/DAILY_PART1C_PORTFOY.md`
> **son güncelleme**: 8 nisan 2026
> **versiyon**: 1.0

bu dosya 3 portföyün (dengeli, agresif, temettü) fırsat tarama kriterlerini, filtrelerini ve karar matrisini tanımlar. PART 1C promptu bu dosyanın kurallarını uygular.

---

## 1. GENEL MANTIK

**portföy fırsat taraması 4 aşamalıdır**:

1. **ön koşullar** (her portföy için) — boş slot sayısı, nakit pozisyonu, sektör konsantrasyon kapasitesi, mevcut pozisyonların sağlığı
2. **tarama evreni + portföy spesifik filtre** — FMP screener'dan ilgili portföy için uygun hisseler çekilir
3. **ortak filtreler** — K-04, K-05, K-17, K-18 her aday için mekanik uygulanır
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

**skor sistemi** (1-10 arası, toplanır):
- ROIC >%15: +3, >%12: +2, >%10: +1
- 6M momentum >%20: +3, >%10: +2, >%0: +1
- RSI 40-60 (nötr bölge, aşırı alım değil): +2
- P/E <15: +2, <20: +1
- sektör mevcut portföyde değil: +2
- 5 yıllık EPS büyümesi >%10: +2
- **minimum skor 8** altı GEÇ, 8-11 İZLE, 12+ EKLE

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

**skor sistemi**:
- EPS surprise >%20: +4, >%15: +3, >%10: +2
- RS rank >90: +3, >85: +2, >80: +1
- hacim oranı >2x: +3, >1.5x: +2, >1.2x: +1
- AI tedarik zinciri katmanı: +3 (doğrudan), +1 (dolaylı)
- analyst consensus "Strong Buy": +2, "Buy": +1
- 6M getiri >%50: +3, >%30: +2, >%15: +1
- **minimum skor 10** altı GEÇ, 10-13 İZLE, 14+ EKLE

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

**skor sistemi**:
- yield %5-7: +3, %4-5: +2, %3-4: +1
- payout ratio <%50: +3, <%65: +2, <%75: +1
- 10+ yıl temettü artışı: +3, 5-10 yıl: +2
- P/E <12: +3, <15: +2, <18: +1
- FCF büyümesi son 3 yıl pozitif: +2
- sektör defensive (XLU/XLP/XLV/Tobacco): +2
- **minimum skor 9** altı GEÇ, 9-12 İZLE, 13+ EKLE

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

### K-18: insider trading
- son 30 gün içinde CEO/CFO/direktör satışı >$5M varsa → ❌ elenir
- script: `scripts/k18_insider_check.py SYMBOL`

### K-19: XLP dışlama (SWING için, portföy için DEĞİL)
- dengeli ve temettü portföyleri için bu filtre UYGULANMAZ (XLP defensive karakter portföyler için uygundur)
- agresif için XLP sektörü öncelikli değil ama otomatik eleme yok

### K-20: RS dead cat bounce filtresi
- hisse 1 aylık olarak SPY'yi %10+ geride bırakmışsa ve son 5 günde +%5 yukarı gelmişse → ❌ elenir (dead cat bounce)
- bu filtre agresif için zorunlu, dengeli ve temettü için öneri seviyesinde

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
      "neden": "K-18 insider satışı $12M (CEO)",
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
| `k_17_gecis` | bool | ✅ | K-17 korelasyon geçtí mi? |
| `k_18_gecis` | bool | ✅ | K-18 insider geçti mi? |
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
   a. ortak filtreler (K-04, K-05, K-17, K-18, K-20) uygulanır
   b. portföy spesifik skor hesaplanır
   c. karar matrisine göre aksiyon atanır
7. watchlist güncellemesi (seviyeye ulaşan, elenen, yeni eklenen)
8. rapor yazılır (aşağıda format)
9. data/watchlist.json güncellenir
10. git commit + push
```

---

## 9. ÖRNEK SKOR HESAPLAMA (QCOM için agresif portföy)

### ham veriler (7 nisan 2026 kapanış)
- fiyat: $124.07
- RSI: 32.2
- son çeyrek EPS surprise: +%14 (tahmin $2.60, gerçek $2.96)
- 6 aylık getiri: %12 (SPY aynı dönem +%3, RS mesafe +%9)
- RS rank: ~72 (eşik altı — kriter %80)
- hacim oranı: 1.3x
- 52W high: $142 → %12 mesafe
- sektör: teknoloji, alt tema: mobil/edge compute
- AVGO/google ASIC haberi dolaylı pozitif
- SMA50: $128 → fiyat altında ❌ (K-04 soru işareti, istisna değerlendir)
- SMA200: $135 → fiyat altında ❌

### skor
- EPS surprise %14: +3
- RS rank 72: +0 (eşik altı, puan yok — ama dead cat filtresi engellenmedi)
- hacim oranı 1.3x: +1 (marjinal)
- AI tedarik zinciri dolaylı: +1
- analyst consensus "Buy": +1 (FMP grades-consensus doğrulama gerek)
- 6M getiri %12: 0 (%15 altı)
- K-04 istisna (RSI 32 oversold): bonus +1
- **toplam: 7**

### karar
- agresif eşik EKLE = 14
- skor 7 < 14 → **EKLE değil**
- skor 7 < 10 (İZLE alt eşiği) → **GEÇ**

**ama**: CPU darboğazı tezi ve forward P/E cazipliği niteliksel katkı. skor düşük ama ticker manuel "CRITICAL" urgency ile watchlist'te. bu sistematik değerlendirme skorun 14'ü geçmediğini gösteriyor — iyimser tezi mekanik filtrenin önüne koymayalım uyarısı.

**ders**: mevcut watchlist'teki QCOM sübjektif tutuldu. yeni sistem bu tür durumları engelleyecek — ya skor geçer ya geçmez.

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
- [ ] filtreler mekanik uygulandı mı? (K-04, K-05, K-17, K-18 her aday için)
- [ ] watchlist güncel mi? (seviyeye ulaşanlar taşındı mı, 14 gün dolanlar elenlendi mi?)
- [ ] data/watchlist.json dosyası push edildi mi?
- [ ] mevcut pozisyonlar için BÜYÜT/DÖNDÜR değerlendirmesi yapıldı mı?
- [ ] skor hesaplamaları şeffaf mı? (her puan gerekçeli mi?)

---

*finzora ai — portföy fırsat tarama sistemi v1.0*
