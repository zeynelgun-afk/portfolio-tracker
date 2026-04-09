# GÜNLÜK SWING RAPORU — 9 NİSAN 2026, PERŞEMBE

> finzora ai | sabah raporu okundu (DAILY_SABAH_2026-04-09.md) | VIX: 20.18 (K-13 sakin bandı) | K-14: **kalkıyor — teyit + half-position modu**

---

## 1. swing sistem durumu

### parametreler
- **VIX**: 20.18 (-%22 dünden) → K-13 v4.1 bandı: **sakin** (<22)
- **SPY trend**: $676.01 > SMA50 $674.92 (fark sadece +%0.16, sınırda), SMA200 üstü ✅, eğim ↗
- **SPY RSI14**: 58.4 (orta bant, overbought değil)
- **K-02 durumu**: kriz sonrası teyit şartları sağlandı (VIX zirveden -%22, SPX trough'tan +%3'den fazla toparlama)
- **K-14 drawdown freni**: **kaldırma kararı — half-position protokolü ile**
  - peak: $12,480 (3 mart 2026) | trough: $10,430 (26 mart 2026) | DD: %16.42
  - dün (8 nisan faz2 ortam testi) kriter özeti: "VIX<22 + SPY>SMA50 iki kriter de sağlandı"
  - dünkü karar: "aktif kalıyor — 1 gün teyit kuralı (kriz rally gün-1 kovalama yasağı)"
  - dünkü yarınki karar: "SPY SMA50 üstü + VIX<22 devam ederse VE yeni kriz flari yoksa K-14 kaldır"
  - bugünkü teyit durumu:
    1. VIX<22 devam ediyor ✅ (20.18, dün 21.02 → bugün kapanış verisi daha düşük)
    2. SPY>SMA50 devam ediyor ✅ ($676.01 > $674.92, sınırda ama aynı yönde)
    3. Yeni kriz flari yok ⚠️ (futures -%0.2 normal sindirim, kriz sinyali değil)
  - **karar**: K-14 formal olarak kalkar, ancak yeniden başlama protokolü (madde 3) gereği **ilk 3 trade yarım pozisyon** zorunlu, 2/3 kazanırsa tam pozisyona geçilir
- **aktif pozisyon**: 0/6 | slot: 6 boş

### mod kararı

K-14 formal olarak kalkıyor ama bu **"açılış zili çalınca giriş yap" anlamına gelmiyor**. iki ek disiplin katmanı devrede:

1. **day-2 chase kontrol**: dün A-kalite adaylar +%6-9 arası koştu (WDC +%8.60, AMAT +%8.87, KLAC +%7.97, CAT +%6.51). day-1 rally kovalama yasağı bittikten sonra da RSI 65 üst sınırı otomatik kendi eleme yapıyor. bu "iki gün üst üste dev rally" tipinde chase riski hala yüksek.

2. **yarım pozisyon protokolü**: sistem bu hafta içinde hiç açık pozisyon yok, K-14 soğuma zemini tam yerleşmedi (sadece 2 iş günü geçti, protokol 5 iş günü soğuma istiyor ama "yarinki_karar" bu sürenin üzerine çıkıyor). çelişkiyi çözmek için yarım pozisyon protokolü çalıştırılıyor — ilk 3 trade max $5K, 2/3 kazanırsa sonraki trade'ler $10K'ya çıkar.

**sonuç**: bugün tarama yapılıyor, A-kalite aday listesi oluşturuluyor, ancak **bugün yeni giriş yok**. seviye bazlı tetik emirleri hazırlanıyor, bir-iki işlem günü pullback veya yatay konsolidasyon teyidi aranıyor.

---

## 2. aktif pozisyonlar

**aktif swing pozisyonu yok** (0/6).

mart 2026 kayıp serisi sonrası 26 mart trough'undan beri sistem nakitte. bu rapor pozisyon yönetimi değil, restart hazırlık değerlendirmesi.

### mart 2026 kayıp analizi (dersler)

| tarih | sembol | pnl% | sebep sınıflandırması |
|-------|--------|------|----------------------|
| 9 mart | HAL | -%5.1 | kriz sonrası day-1 chase (K-02 ihlal) |
| 9 mart | CEG | -%5.05 | aynı gün korelasyon (K-17 ihlal) |
| 11 mart | T | -%5.54 | defansif rotasyon timing hatası |
| 12 mart | ALMU | -%6.11 | stop override (K-06 ihlal) |
| 12 mart | SOFI | -%3.62 | trend filtresi ihlal (K-04 ihlal) |
| 24 mart | RTX | -%5.16 | savunma primi unwinding |
| 26 mart | AROC | -%4.95 | enerji sektörü cluster |

**restart öncesi dersler** (status.json'dan):
1. 9-12 mart 5 zarar penceresi: K-14 zamanında uygulanmadı, boyut küçültülmedi
2. K-14 manuel izleme başarısız, otomatik script şart (7 nisan 2026'da eklendi)
3. POWL+CAMT+VRT 25 mart: K-17 ihlali aynı temada üçlük, K-14 drawdown'un büyük parçası
4. Mart 2026 genel ders: VIX dikkatli + sektör rotasyonu yavaş = swing ortamı zayıf

bu dersler bugünkü restart kararına doğrudan etki ediyor: chase yasağı + korelasyon + boyut küçültme hepsi aktif.

---

## 3. tarama sonuçları

### mod: hedefli evren (K-14 yeni kalktı, ilk gün tam evren tarama yerine mevcut watchlist değerlendirmesi)

K-14 resmen kalkmış olsa da protokol kurulumu henüz oturmadı. dünkü 10'lu watchlist (part 1C sistemi tarafından üretilmiş) zaten AI tedarik zinciri v2 tezinin kalbinde. tam evren tarama yerine bu liste değerlendiriliyor.

### dünkü watchlist.json (8 nisan 2026 güncellemesi)

| # | sembol | urgency | hedef port | fiyat | RSI | skor | sektör | not |
|---|--------|---------|------------|-------|-----|------|--------|-----|
| 1 | WDC | high | agresif | $338.78 | 65.1 | 17 | tech/storage | +%8.60 dün, RSI sınırda |
| 2 | KLAC | high | agresif | $1672.34 | 66.4 | 14 | semi ekipman | +%7.97 dün, **RSI 65 üstü** |
| 3 | AMAT | high | agresif | $385.72 | 62.7 | 14 | semi ekipman | +%8.87 dün |
| 4 | CAT | high | dengeli | $771.58 | 64.1 | 12 | endüstri | +%6.51 dün |
| 5 | MRK | high | temettü | $123.20 | 64.4 | 11 | sağlık | pozisyon portföyde, swing değil |
| 6 | UPS | medium | temettü | $100.43 | 40.4 | 11 | lojistik | SMA50 altı — swing için uygun değil |
| 7 | DUK | medium | dengeli | $131.60 | 57.4 | 11 | utility | -%0.17 dün, katılmadı |
| 8 | NEE | medium | dengeli | $94.17 | 61.6 | 9 | utility | +%0.53 sessiz |
| 9 | GEV | medium | dengeli | $936.07 | 63.0 | 10 | güç ekipman | **14g earnings (22 nis) K-05 marjinal** |
| 10 | ATMU | low | dengeli | $63.13 | 61.8 | 9 | endüstri | +%4.55 sessiz katılım |

### ichimoku 4/4 yaklaşık değerlendirme

ichimoku tam hesaplama yapılmadı (PART 1B script çalıştırılmadı), ama SMA/RSI vekil göstergeleriyle hızlı eleme:

| sembol | SMA50 üstü | SMA200 üstü | RSI 40-65 | day-1 chase | durum |
|--------|:---:|:---:|:---:|:---:|-------|
| WDC | ✅ | ✅ | ❌ (65.1) | ⚠️ +%8.60 | **RSI SINIRDA** — eşiği geçti |
| KLAC | ✅ | ✅ | ❌ (66.4) | ⚠️ +%7.97 | **ELENDİ** — RSI 65 üstü |
| AMAT | ✅ | ✅ | ✅ (62.7) | ⚠️ +%8.87 | chase risk yüksek |
| CAT | ✅ | ✅ | ✅ (64.1) | ⚠️ +%6.51 | chase risk orta |
| GEV | ✅ | ✅ | ✅ (63.0) | ⚠️ +%2.78 | K-05 earnings yakın |
| ATMU | ✅ | ✅ | ✅ (61.8) | ✅ +%4.55 | katılım ölçülü |
| MRK | ✅ | ✅ | ✅ (64.4) | ✅ +%3.29 | swing değil, temettü pozisyonu |
| DUK | ✅ | ✅ | ✅ (57.4) | ✅ -%0.17 | ralliye katılmadı |
| NEE | ✅ | ✅ | ✅ (61.6) | ✅ +%0.53 | ralliye katılmadı |
| UPS | ❌ | ✅ | ❌ (40.4) | — | SMA50 altı, eleme |

**eleme özeti**:
- KLAC: RSI 66.4 > 65 üst sınır (K-system v2 RSI 40-65 bandı ihlal) ❌
- WDC: RSI 65.1 sınır ihlal marjinal ❌
- UPS: SMA50 altı, trend filtresi ihlal ❌
- MRK: swing değil, zaten temettü portföyünde pozisyon ❌

**aday kalanlar**: AMAT, CAT, GEV, ATMU, DUK, NEE (6)

### K filtreleri sonrası

| # | sembol | K-19 XLP | K-20 dead cat | K-17 korelasyon | K-18 insider | K-05 earnings | K-13 VIX | sonuç |
|---|--------|:---:|:---:|:---:|:---:|:---:|:---:|-------|
| 1 | AMAT | ✅ | ✅ | ⚠️ | ? | ✅ (42g) | ✅ sakin | **ADAY** (korelasyon notu) |
| 2 | CAT | ✅ | ✅ | ✅ | ? | ✅ (20g) | ✅ sakin | **ADAY** |
| 3 | GEV | ✅ | ✅ | ✅ | ? | ⚠️ (13g, marjinal) | ✅ sakin | KOŞULLU (earnings riski) |
| 4 | ATMU | ✅ | ✅ | ✅ | ? | ✅ (22g) | ✅ sakin | **ADAY** |
| 5 | DUK | ✅ | ✅ | ✅ | ? | ✅ | ✅ sakin | **ADAY** (yavaş) |
| 6 | NEE | ✅ | ✅ | ✅ | ? | ✅ | ✅ sakin | **ADAY** (yavaş) |

**K-17 korelasyon notları**:
- AMAT + KLAC + WDC + TSM aynı semiconductor equipment / AI supply chain temasında → birden fazla giriş yapılırsa K-17 ihlal. sadece bir tane seçilebilir.
- CAT + GEV + ATMU endüstri/power ekipman teması → aynı kümede. birden fazla giriş K-17 ihlal.
- DUK + NEE utility sektörü → aynı sektör, sadece bir tane seçilebilir.

**K-05 GEV notu**: earnings 22 nisan = bugünden 13 iş günü sonra. swing tutma süresi tipik 7-10 gün, marjinal. giriş yaparsak kesin çıkış tarihi 17 nisan (2 iş günü önce). bu sıkışık zemin → skip daha güvenli.

**K-18 insider**: FMP insider-trading endpoint bugün veri döndürmedi, manuel finviz kontrolü trading seansı öncesi şart.

### nihai aday listesi (K filtreleri sonrası)

1. **AMAT** (semiconductor equipment, AI supply chain core) — day-2 chase warning
2. **CAT** (industrial, infrastructure hikayesi)
3. **ATMU** (ölçülü katılım, diversifiye endüstri)
4. **DUK** veya **NEE** (utility, savunma rotasyonu)

---

## 4. nihai aday detayları

> **önemli not**: bugün fiili giriş YOK. tüm girişler seviye bazlı tetik emirleri halinde hazırlanıyor, en erken 10 nisan (yarın) ya da 13 nisan (pazartesi) aktif olacak. amaç day-2 chase riskini yönetmek + yarım pozisyon protokolüne uymak.

### **AMAT** — applied materials, semiconductor ekipman

- **sektör**: technology / semiconductor capital equipment
- **tema**: AI tedarik zinciri v2, sol taraf ekipman katmanı (ASML, LRCX, KLAC ile aynı küme)
- **fiyat**: $385.72 | **RSI**: 62.7 | **ATR(14)**: $18.87 (günlük ~%4.9 range)
- **trend**: SMA50 $348.51 ✅ (+%10.7), SMA200 $251.77 ✅ (+%53)
- **katalizör**: iran ceasefire sonrası tech ralli, TD cowen ASML hedef artışı aynı tema paralelinde, AI infrastructure harcaması tezinin canlanması
- **giriş koşulu**: **day-1 chase yasağı gereği bugün giriş yok**. seviye tetiği: $380 altına pullback VEYA $390 üstüne bir sonraki kapanış teyidi
- **pozisyon büyüklüğü**: **yarım pozisyon $5,000** (K-14 restart protokol madde 3: ilk 3 trade yarım)
- **ilk stop (K-06)**: max(2×ATR, %5) = max($37.74, $19.29) = $37.74 → giriş $385'ten stop $347 (yaklaşık SMA50 seviyesi, -%9.8)
- **hedef 1**: $424 (+%10, K-07 kâr kilidi tetik noktası)
- **hedef 2**: chandelier trailing 3×ATR
- **R:R**: ($424-$385)/($385-$347) = $39/$38 = **1.03:1** ❌ **MIN 2:1 ŞARTI SAĞLANMIYOR**
- **sorun**: yüksek ATR + dar hedef = R:R yetersiz. bu seviyeden giriş anlamsız.
- **karşıt argüman**: "KLAC ve AMAT dün +%8 koştu, iki gün üst üste aynı sıçrama beklenmez, pullback olasılığı yüksek. sabırsız girmek ATR'yi kaldırmanın en kestirme yolu." pullback fırsatı bekle.
- **revize giriş tetiği**: $370 altına pullback → giriş $370, stop $345 (-%6.8), hedef 1 $407 (+%10), R:R ($37/$25) = **1.48:1** hala zayıf
- **revize 2**: $360 oversold bounce entry → giriş $360, stop $335 (-%6.9), hedef $396 (+%10), R:R ($36/$25) = **1.44:1**
- **karar**: AMAT R:R yeterli değil ATR çok yüksek → **GEÇ veya pullback daha derin olursa yeniden değerlendir**
- **filtreler**: K-19 ✅, K-20 ✅, K-17 ⚠️ (AI supply chain cluster), K-18 manuel kontrol, K-05 ✅, K-13 sakin

### **CAT** — caterpillar, endüstri

- **sektör**: industrial / construction machinery
- **tema**: infrastructure harcaması, dengeli portföy katalizörü (hedef_portfoy: dengeli)
- **fiyat**: $771.58 | **RSI**: 64.1 | **ATR(14)**: $27.52 (günlük ~%3.6 range)
- **trend**: SMA50 $717.40 ✅ (+%7.6), SMA200 $555.37 ✅ (+%39)
- **katalizör**: infrastructure + ceasefire civil recovery + tech unwinding ötesi rotasyon
- **giriş koşulu**: **bugün giriş yok**. tetik: $765 altına pullback VEYA $775 üstüne kapanış teyidi
- **pozisyon büyüklüğü**: **yarım pozisyon $5,000**
- **ilk stop**: max(2×ATR, %5) = max($55.04, $38.58) = $55.04 → giriş $771'den stop $716 (SMA50 seviyesi, -%7.1)
- **hedef 1**: $848 (+%10)
- **hedef 2**: chandelier trailing 3×ATR
- **R:R**: ($848-$771)/($771-$716) = $77/$55 = **1.40:1** ❌ (2:1 altı)
- **revize**: $760 altına pullback → giriş $760, stop $716, hedef $836, R:R $76/$44 = **1.73:1** hala zayıf
- **karşıt argüman**: "CAT dün +%6.5, ATR $27, bir pullback gelirse hızlı olur. endüstri rotasyonu tezi sağlam ama giriş seviyesi önemli."
- **karar**: CAT da R:R yeterli değil → **pullback daha derin olursa veya RSI geri çekilirse yeniden değerlendir**
- **filtreler**: K-19 ✅, K-20 ✅, K-17 ✅, K-18 manuel, K-05 ✅ (29 nisan earnings), K-13 sakin

### **ATMU** — atmus filtration, diversifiye endüstri

- **sektör**: industrial / filtration
- **tema**: endüstri küçük-orta cap, smallcap toparlanma
- **fiyat**: $63.13 | **RSI**: 61.8 | **ATR(14)**: $2.42 (günlük ~%3.8 range)
- **trend**: SMA50 $60.35 ✅ (+%4.6), SMA200 $49.52 ✅ (+%27)
- **katalizör**: smallcap rotasyon, IWM dün +%2.99, ölçülü +%4.55 katılım (chase marjı düşük)
- **giriş koşulu**: $62.50 üstüne intraday konfirmasyon (daha sakin adaydan giriş mümkün)
- **pozisyon büyüklüğü**: **yarım pozisyon $5,000** (74 adet @$63.13)
- **ilk stop**: max(2×ATR, %5) = max($4.84, $3.16) = $4.84 → stop $58.29 (-%7.7)
- **hedef 1**: $69.44 (+%10)
- **hedef 2**: chandelier trailing
- **R:R**: ($69.44-$63.13)/($63.13-$58.29) = $6.31/$4.84 = **1.30:1** ❌
- **revize**: $62.00 oversold entry → stop $57.16, hedef $68.20, R:R $6.20/$4.84 = **1.28:1**
- **karar**: ATMU da R:R yeterli değil → **izle, direkt giriş yok**
- **filtreler**: K-19 ✅, K-20 ✅, K-17 ✅, K-18 manuel, K-05 ✅, K-13 sakin

### **DUK / NEE** — utility, savunma rotasyonu

- **DUK** $131.60 RSI 57.4, **NEE** $94.17 RSI 61.6
- **tema**: ralliye katılmayan utility → ceasefire sonrası savunma rotasyonu unwinding'i, değer potansiyeli
- **ATR ve SMA** verileri sağlam ama **RSI 40-65 bandında ama trend momenti yavaş**. ichimoku 4/4 teyidi için tam script lazım
- **durum**: swing teması için marjinal, pozisyon trade olarak daha anlamlı
- **karar**: part 1C portföy fırsat promptuna devret, swing listesinde değil

---

## 5. giriş planı özet

### **bugün (9 nisan) için aksiyon**: **yeni swing girişi YOK**

gerekçe:
1. K-14 resmen kalkıyor ama ilk işlem günü yarım pozisyon + day-2 chase riski eşiğinde
2. tüm A-kalite adaylarda R:R oranı 2:1 altı (yüksek ATR + dar %10 hedef birleşimi)
3. day-1 chase yasağı teknik olarak bitti ama RSI 65 üst sınırı birçok adayı eledi
4. pullback beklemek rasyonel: futures -%0.2 sindirim, bir-iki gün bekle, daha iyi seviyeler gelebilir

### **koşullu tetik emirleri** (seviye bekle, otomatik değil — gün içinde manuel izleme):

| sembol | tetik seviyesi | koşul | giriş büyüklüğü | karar |
|--------|---------------|-------|-----------------|-------|
| AMAT | $360-365 pullback | hacim normal, RSI 55 altı gelirse | yarım $5K | değerlendir |
| CAT | $745-750 pullback | SMA50 testi ($717 yakın), RSI 55 altı | yarım $5K | değerlendir |
| ATMU | $61.50 pullback | sakin daralma + hacim | yarım $5K | değerlendir |
| IWM | $255 altı bounce | smallcap breadth teyidi | ETF değil, gözlem | gözlem |

### **izleme** (gün içinde)

1. **SPY** $674.92 (SMA50) seviyesi → altına gelirse K-14 yeniden riski var, her aday geri geri
2. **SPY** $680 üstüne kapanış → rally dayanıklı, yarın tam pozisyon protokolüne hazırlık
3. **VIX** 22 eşiğinin üstüne çıkarsa → K-13 sakin bandı kırılır, tüm planı askıya al
4. **WTI** $100 üstüne dönerse → ceasefire çöküyor sinyali, tüm rally risk altında

### **haftalık plan** (9-13 nisan)

- **9 nisan (bugün)**: gözlem + aday listesi hazırlığı, yeni giriş yok
- **10 nisan**: pullback teyidi için seans izle, uygun seviye gelirse **ilk yarım pozisyon** (max 1 aday)
- **13 nisan**: ikinci ve üçüncü yarım pozisyon pencereleri (max 2 aday). 14 nisan JNJ+JPM earnings öncesi sakin dur
- **14 nisan**: earnings sezonu başlıyor → yeni swing girişi askı (K-05 binary risk)
- **15 nisan sonrası**: 2/3 kazançta tam pozisyon protokolüne geçiş değerlendir

---

## 6. sistem notları ve karşıt argümanlar

### neden bugün giriş yapmıyorum?

1. **R:R matematik sorunu**: tüm adaylarda ATR elevated (ceasefire vol) + fiyat SMA50'den uzak + %10 hedef dar → R:R 2:1 altı. kurala uymaz.
2. **day-2 chase distorsiyonu**: adayların hepsi dün +%6-9 arası koştu, iki gün üst üste aynı sıçrama tarihsel olarak nadir. mean reversion olasılığı yüksek.
3. **protokol disiplini**: K-14 restart protokolü yarım pozisyon istiyor, ilk gün "herkesi doldur" mentalitesi protokolün ruhuna aykırı.
4. **JNJ/JPM earnings 14 nisan**: sadece 3 iş günü sonra. yeni swing açıp kapatmak bile stresli.

### neden yanlış olabilirim?

1. **rally momentumu gerçek olabilir**: tech liderliği + yardeni recession prob indirimi + AI supply chain v2 tezi aynı yönde. ben pullback beklerken piyasa dümdüz yukarı devam ederse fırsatı kaçırırım.
2. **day-2 "sell the ceasefire" olmayabilir**: 2025 "liberation day" tariffe benzetmesi yapıldı, o zaman hızlı toparlanma sürdü. belki aynı pattern.
3. **AI supply chain momentum teması**: ASML +%8.74 TD Cowen target artışı = kurumsal talep gerçek. AMAT/KLAC paralel fırsat, her gün gerileme bekleyip giriş yapamayabilirim.
4. **VIX 20 altına inerse** (olası): K-13 daha gevşer, tam pozisyon kapısı açılır, yarım pozisyon protokolü aşırı muhafazakar kalabilir.

### ikinci senaryoya hazırlık

eğer rally devam ederse + ben giriş yapmazsam → bu durumda hata yaptığımı kabul et, ancak disiplin gereği aynı yanlışı tekrar etme. pazartesi (13 nisan) veya ASML earnings sonrası (15 nisan) yeniden değerlendirme noktaları var. fırsat kaçırma duygusuna (FOMO) teslim olmak mart 2026 kayıp serisinin ana sebeplerinden biriydi. disiplin kısa vadede maliyetli, uzun vadede hayat kurtarır.

---

*finzora ai | swing sistem durumu: hazır ama bekliyor | K-14: kalkıyor (yarım pozisyon protokolü aktif) | bugün aksiyon: 0 giriş, 4 seviye bazlı tetik emri izleniyor*
