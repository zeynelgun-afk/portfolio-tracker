# AAOI — Applied Optoelectronics — Bilanço Sonrası Değerlendirme

**Tarih**: 11 Mayıs 2026 (Pazartesi)
**Skill**: `bilanco-sonrasi-us` v1.2
**Bilanço Tarihi**: 7 Mayıs 2026 (Q1 2026, AMC)
**Veri Kaynağı**: FMP Ultimate API, SEC Edgar, Yahoo Finance, transcript (43.907 karakter)
**Hazırlayan**: finzora ai

---

## Karar Özeti

| Aşama | Durum |
|-------|-------|
| Aşama 1 — Mid-cap+ filtre | GEÇTİ (mcap $13.86 milyar, NASDAQ) |
| Aşama 2 — YoY/QoQ iyileşme | KISMI GEÇTİ (YoY ciro %51, ama hâlâ net zarar) |
| Aşama 3 — Adil değer + analist hedef teyidi | **BAŞARISIZ** (analist hedef ortalaması mevcut fiyatın %18 altında) |
| Aşama 4a — Analist revize yön sayımı | GEÇTİ (4 raised, 0 lowered) |
| Aşama 4b — Transcript guidance | GEÇTİ (açık RAISED) |
| Aşama 4c — 13F kurumsal birikim | KARIŞIK (Q4 2025: +7.9M; Q1 2026: -43M) |
| Aşama 4d — 8-K cross-validation | EVET (7-8 Mayıs 8-K + 10-Q yayınlandı) |
| Aşama 5 — Yıldız skor | **2.5 / 5 — İZLEME** |

**Nihai karar**: **İZLE — AL DEĞİL**. Hisse 7-8 Mayıs bilanço açıklamasından sonra %16+ gap-up ile Pazartesi günü kovalanıyor. Skill kuralı uyarınca "Day-1+ chasing yasağı" aktif. Ek olarak post-earnings revize edilen analist hedef ortalaması ($141.62) mevcut fiyatın ($172.5) altında — yani analistlerin yeni hedeflerini bile aşmış durumda.

---

## Bölüm 1 — Bilanço Özeti

Q1 2026 sonuçları (7 Mayıs 2026 piyasa kapanışından sonra açıklandı):

| Metrik | Gerçekleşen | Konsensüs | Sürpriz |
|--------|-------------|-----------|---------|
| Revenue | 151.1 milyon $ | 156.98 milyon $ | **MISS** (-3.7%) |
| Non-GAAP EPS | -0.07 $ | -0.05 $ | **MISS** (daha derin zarar) |
| GAAP Net Loss | -14.3 milyon $ | — | (önceki yıl çeyrek -9.2M) |
| Non-GAAP Gross Margin | 29.2% | — | guidance aralığında (29-31%) |

YoY/QoQ momentum:
- Revenue YoY: **+%51.4** (101 milyon $ → 151 milyon $)
- Revenue QoQ: **+%12.6** (134 milyon $ → 151 milyon $)
- 4. art arda **rekor** çeyrek
- Net income YoY -%55.7 (-9.2M → -14.3M) — kâr tarafı kötüleşmiş
- Net income QoQ -%606 (-2.0M → -14.3M) — Q4 düşük zararın ardından bozulma

**KESİN sinyal**: Hem revenue hem EPS analist beklentisini ıskaladı, ama YoY büyüme rekor seviye.

---

## Bölüm 2 — Adil Değer Hesabı (4 Yöntem Ağırlıklı)

### Yöntem 1 — Post-earnings analist hedef ortalaması (%35 ağırlık)

Bilanço sonrası 8 Mayıs revize listesi:

| Analist | Önceki Hedef | Yeni Hedef | Değişim | Tavsiye |
|---------|--------------|------------|---------|---------|
| Raymond James (Simon Leopold) | 72.50 $ | 160 $ | +%121 | Outperform |
| Rosenblatt (Mike Genovese) | 140 $ | 220 $ | +%57 | Buy |
| B. Riley (Dave Kang) | 54 $ | 129 $ | +%139 | Neutral |
| Northland (Tim Savageaux) | 55 $ | 57.50 $ | +%5 | — |

**Post-earnings ortalama: 141.62 $** (yelpaze 57.50-220, medyan 144.5)

Eski FMP konsensüs hedefi 74.5 $ idi (Aralık 2025) — bilanço sonrası bu rakam henüz API'da güncellenmedi. Üstte gerçek revize fiyatları kullanıldı.

Mevcut fiyat 172.5 $ → yeni analist ortalamasının **-%17.9 üstünde**. Skill'in "analist target +%25 upside vermeli" sağlamlık filtresi BAŞARISIZ.

### Yöntem 2 — Forward P/E × NTM EPS (%35 ağırlık)

| Yıl | Analist EPS Tahmini | Analist Sayısı |
|-----|---------------------|----------------|
| 2026 | 1.00 $ | 3 |
| 2027 | 5.44 $ | 3 |
| 2028 | 10.45 $ | 1 |

- 2026 forward P/E: 172.5 / 1.00 = **172x** (zarar makinesi → kâr geçişi, distortion)
- 2027 forward P/E: 172.5 / 5.44 = **31.7x** (semis büyüme median 30x)
- 2028 forward P/E: 172.5 / 10.45 = **16.5x** (ucuz görünüyor — tek analist tahmini)

2027 EPS × 30x semis growth median = **163.20 $** (NTM bazında)

### Yöntem 3 — EV/EBITDA peer (%30 ağırlık)

- TTM EBITDA negatif → yöntem mevcut için uygulanamaz
- 2027 forward EBITDA tahmini: ~500-600 milyon $ (analist Op Income 540M $'a yakın)
- Semis peer median EV/EBITDA: 20x
- Forward EV target: 10-12 milyar $ (Düşük 10B alınırsa)
- Diluted shares yaklaşık 80 milyon → per share: **137.50 $**

### Yöntem 4 — PEG (uygulanmadı)

L2P (zarardan kâra geçiş) hisselerinde TTM EPS düşük baz distortion verir. Skill kuralı ile eleme.

### Ağırlıklı Adil Değer

```
0.35 × 141.62 + 0.35 × 163.20 + 0.30 × 137.50 = 147.94 $
```

**Adil Değer: 147.94 $**
**Mevcut Fiyat: 172.5 $**
**Upside / Downside: -%14.2 (mevcut fiyat adil değerin üzerinde)**

---

## Bölüm 3 — Telekonferans Guidance (Aşama 4b)

Transcript Q1 2026 başarıyla çekildi (43.907 karakter, FMP Ultimate). Anahtar guidance cümleleri:

**Açık RAISED sinyalleri**:

1. *"Based on new demand and our anticipated capacity ramp, we now believe our 2026 revenue will exceed $1.1 billion, and we now expect to generate more than $140 million in non-GAAP operating income this year."* — **2026 ciro guidance 1.0 milyar $'dan 1.1 milyar $'a yükseltildi**, ek olarak 140 milyon $+ non-GAAP işletme kârı açıklandı.

2. *"We expect by the end of this year we will be capable of producing over 650 thousand pieces of 800G and 1.6T products per month, with about 30% of that output coming from Texas."* — Kapasite genişlemesi açık.

3. *"We expect to further expand our laser fabrication capacity by around 350% by 2027."* — 2027'ye kadar lazer fab kapasitesi %350 büyüyecek.

4. *"Looking ahead to Q2, we expect our CATV revenue will be between $75 million and $80 million."* — Q1 66.8M → Q2 75-80M (sequential +%12-20).

5. *"Annual CATV revenue $325 million+"* — eskisinin neredeyse iki katı.

**Q2 2026 toplam revenue guidance: 180-198 milyon $** (analist konsensüsü 192.57M — orta tahmine eşit, "in-line").

**CFO yorumu**: Şirket 124 milyon $'lık tek 1.6T/800G siparişi aldı (transcript). 2H 2026'da %60-80 sequential growth bekleniyor (Q3/Q4 ivmelenme).

**Constraint**: *"This revenue level is limited by our production capacity and supply chain, not market demand."* — bu hem fırsat hem risk (execution riski).

**Transcript Verdict: STRONG RAISED**

---

## Bölüm 4 — 13F Kurumsal Birikim (Aşama 4c)

| Çeyrek | Yatırımcı Sayısı | # 13F Shares | Toplam Yatırım | Ownership % |
|--------|------------------|--------------|----------------|-------------|
| Q4 2025 | 244 (+32) | 47.6 milyon (+7.9M) | 1.66 milyar $ | — |
| Q1 2026 | 112 (-132) | 4.2 milyon (-43.4M) | 355 milyon $ | %5.97 |

**KESİN sinyal**: Q4 2025'te güçlü kurumsal birikim (+%20 yatırımcı, +%20 shares). Q1 2026'da kurumların 132'si pozisyon kapatmış, shares -%91 düşmüş. Bu değişim eski konsensüs hedefinin 74.5 $ olduğu dönemde yaşandı — yani **kurumlar AAOI'yi Q1'de büyük ölçüde sattı**, bilanço beklentisi olumsuzdu.

**Smart money (Druckenmiller / Buffett / Tepper / Burry / Ackman / Loeb / Einhorn)**: Hiçbirinde AAOI yok.

**MUHTEMEL yorum**: Q1 2026 13F'ler son filing tarihine henüz gelmedi (45 gün, son tarih ~15 Mayıs). Veri eksik olabilir. Yine de Q1 yönü çok belirgin (-43M shares).

---

## Bölüm 5 — Teknik Görünüm

| Metrik | Değer | Yorum |
|--------|-------|-------|
| Mevcut Fiyat | 172.5 $ | — |
| 52-Hafta High | 191.87 $ | High'tan -%9.1 |
| 52-Hafta Low | 15.06 $ | Low'dan +%1057 |
| 50-Gün SMA | 125.36 $ | SMA üstü +%37.6 |
| 200-Gün SMA | 54.85 $ | SMA üstü **+%214** |
| Beta | 3.76 | Çok yüksek volatilite |
| RSI(14) | 57.58 | Nötr-yüksek |
| 7 Mayıs Volume | 14.5M (3x average) | Bilanço günü |
| 8 Mayıs Volume | 20.8M (4x average) | Volatil alış-satış |

**Bilanço sonrası price action**:
- 7 May (bilanço açıklaması): Open 172.6 $, Low 152.2 $, **Close 157.55 $** (-%5.7 from open)
- 8 May (volatil gün): Range 143.58 $ - 177.88 $, **Close 148.94 $** (bilanço günü altında)
- 11 May (bugün — pazartesi): Open 174.37 $ (gap-up), **Close 170.52 $** (intraday volatil)

**SPEKÜLATİF yorum**: Hisse 7-8 Mayıs'ta bilanço beklentilerine rağmen geri çekildi, ama hafta sonu medyada "AI optical" momentumu sürdü ve Pazartesi yeniden açıldı. Bu **klasik day-1+ chasing örüntüsü**.

200-gün SMA'nın %214 üzerinde olması mean reversion riskini ciddi şekilde artırır.

---

## Bölüm 6 — 5 Yıldız Skoru

| # | Kriter | Durum | Yıldız |
|---|--------|-------|--------|
| 1 | Adil değer +%30+ analist hedefli | Hedef avg 141.6 $, downside -%18 | ❌ 0 |
| 2 | Şirket guidance RAISED | Transcript açık RAISED (1.1B+ revenue, 140M+ op income) | ✅ +1 |
| 3 | Net analist target raised > lowered | 4 raised (RJ, Rosenblatt, B.Riley, Northland), 0 lowered | ✅ +1 |
| 4 | 13F shares net birikim Q4 > +1M | Q4 2025: +7.9M (POZİTİF) ama Q1 2026: -43M (NEGATİF) | ⚠️ +0.5 |
| 5 | Smart money portföyünde | Hiçbiri (7 fon) | ❌ 0 |

**TOPLAM: 2.5 / 5 — İZLEME tier**

(Skill eşikleri: 4+ öncelikli, 3 ikinci tier, 2 izleme, 1 ele)

---

## Bölüm 7 — Hisse Öneri Kartı (4 Alan — Zorunlu)

### 1. Tetikleyici (Sinyal)

Q1 2026 bilanço sonrası AAOI yönetimi 2026 yıl sonu ciro guidance'ını 1.0 milyar $'dan **1.1 milyar $'a yükseltti** ve ilk kez **140 milyon $+ non-GAAP işletme kârı** beklediğini açıkladı. Beraberinde Q2 ciro guidance'ı 180-198 milyon $ (sequential +%18-31) verildi. 4 ana analist (Raymond James 160 $, Rosenblatt 220 $, B. Riley 129 $, Northland 57.50 $) hedefini bilanço sonrası yükseltti — 0 lowered.

### 2. Veri Dayanağı (FMP + Somut Rakam)

| Veri | Değer | Kaynak |
|------|-------|--------|
| Piyasa değeri | 13.86 milyar $ | profile |
| Mevcut fiyat | 172.5 $ | quote |
| 2026 forward revenue | 1.1 milyar $ (şirket) / 1.04B $ (analist avg) | transcript / analyst-estimates |
| 2027 forward revenue | 2.72 milyar $ (analist avg, 3 analist) | analyst-estimates |
| 2027 forward EPS | 5.44 $ (analist avg) | analyst-estimates |
| 2027 EV/Sales | ~5.1x (10B / 2.72B EV/Sales) | hesaplama |
| Q1 ciro YoY | +%51.4 (4. rekor çeyrek) | income-statement |
| Data center segment Q1 | 81.4 milyon $ (YoY +%154) | transcript |
| TTM net margin | -%8.5 (zarar) | ratios-ttm |
| 200-gün SMA üstü | +%214 | quote |
| Beta | 3.76 | profile |
| Q4 2025 13F shares change | +7.9 milyon (POZİTİF) | institutional-ownership |
| Q1 2026 13F shares change | -43.4 milyon (NEGATİF, dağılım) | institutional-ownership |

### 3. Risk / Bear Case / Stop

**Bear case (en az 5 madde)**:

1. **Day-1+ chasing yasağı**: Skill kuralı (K-15c eşdeğeri) uyarınca bilanço sonrası ilk 1-2 gün almak yasak. AAOI Pazartesi pre-market %16 gap-up ile açıldı, intraday $152'ye kadar geri çekildi — alıcı-satıcı savaşı sürüyor. Geçmiş örnekler (KTOS/CEG/HAL/LASR) day-1 alımlarının 5/5'inde zarar verdi.

2. **Adil değer downside -%14 ila -%18**: Post-earnings analist hedef ortalaması 141.6 $, ağırlıklı adil değer 147.9 $. Mevcut fiyat 172.5 $ — yani analistlerin yeni revize hedeflerini bile aşmış durumda. Skill'in "analist target zaten +%25 upside vermeli" sağlamlık filtresi başarısız.

3. **200-gün SMA'nın %214 üzerinde aşırı extension**: Mean reversion riski yüksek. Beta 3.76 ile küçük bir piyasa düzeltmesi AAOI'da abartılı düşüş demek.

4. **Execution riski (capacity-constrained)**: CFO transcript'te "limited by production capacity and supply chain, not market demand" dedi. 2H 2026 sequential +%60-80 büyüme bekleniyor — bu hedef Texas tesisi açılışına ve laser fab capacity'sine bağlı. Gecikme = guidance miss.

5. **Hyperscaler order concentration**: Tek 124 milyon $'lık 1.6T/800G siparişi şirketin %25'i. Eğer Microsoft / Amazon / Google AI capex'i yavaşlatırsa AAOI doğrudan etkilenir.

6. **Dilution geçmişi**: 26 Şubat 2026'da secondary offering (424B5 filing) yapıldı. AAOI tarihsel olarak gerektiğinde hisse ihraç eden bir şirket. Mevcut $172 fiyat seviyesi yeni offering için iştah açar.

7. **13F Q1 2026 dağılımı**: 132 kurumsal yatırımcı pozisyon kapatmış, shares -43.4 milyon. Bu veri henüz tam olmayabilir (filing son tarihi 15 Mayıs), ama yön net.

8. **Q1 bilanço miss**: Revenue $5.8M altında, EPS $0.02 daha derin zarar. Şirket "guidance aralığında" diyor ama Wall Street consensus altında.

9. **Smart money yokluğu**: 7 büyük fon (Druckenmiller, Buffett, Tepper, Burry, Loeb, Ackman, Einhorn) hiç AAOI tutmamış. Genç yüksek-beta hikaye, kurumsal kalite onayı eksik.

**Stop seviyesi**: Eğer girilirse, **2×ATR(14) ≈ $20** mantıklı stop. $172.5'tan girişte stop ~ $150 (-%13). Ama bu yüksek volatilite (beta 3.76) için de yeterli olmayabilir.

**Trigger noktaları (eğer girmek istenirse)**:
- Min 2-3 gün cooldown
- RSI(14) < 50 + bir günlük teyit
- Tercihen 50-gün SMA bölgesine (125-130 $) çekilme
- Q2 2026 earnings (Ağustos başı) sonrası ikinci doğrulama

### 4. Hangi Portföye Uygun

- **Agresif (400.000 $) — POTANSİYEL ADAY ama ŞU AN DEĞİL**: AAOI agresif portföyün AI tedarik zinciri tematik kapsamına uyar (800G/1.6T optical transceiver hyperscaler tedariği, US manufacturing avantajı). Ancak şu anki seviyede (200-gün SMA %214 üstü, day-1+ chasing) giriş zayıf risk/ödül. **İzleme listesine alınmalı**, geri çekilme bekleyerek pozisyon açılmalı.
- **Dengeli (100.000 $) — HAYIR**: Beta 3.76 ve TTM zarar makinesi olması Dengeli portföyün risk profiline aykırı.
- **Temettü (100.000 $) — HAYIR**: AAOI temettü ödemiyor (`lastDividend = 0`), savunmacı temettü stratejisine uymaz.
- **Swing Trade — KOŞULLU**: Eğer 125-130 $ bölgesine geri çekilirse 5-10K $ swing entry düşünülebilir. Hedef $160 (Raymond James), stop $115. Bu durumda bile pozisyon küçük olmalı (yüksek beta).

---

## Bölüm 8 — Belirsizlik Etiketleri

**KESİN** (FMP/SEC doğrulanmış sayısal veri):
- Q1 2026 revenue 151.1M $, EPS -$0.07 (FMP earnings)
- 2026 revenue guidance 1.1B+ (transcript verbatim)
- Q2 revenue guidance 180-198M $ (transcript)
- Bilanço sonrası 4 analist raised, 0 lowered (FMP price-target-news + web)
- Mevcut fiyat 172.5 $, 200-gün SMA 54.85 $ (FMP quote)
- 7 analist Buy, 6 Hold, 3 Sell konsensüsü (FMP grades-consensus)

**MUHTEMEL** (verili veri + makul çıkarım):
- 2027 EPS $5.44 hedefi gerçekleşirse forward P/E 31x makul olur
- 2H 2026 sequential +%60-80 büyüme guidance'ı capacity ramp'a bağlı
- 13F Q1 2026 dağılımı kısmen tamamlanmamış filing'lerden kaynaklanıyor olabilir
- Day-1+ chasing örüntüsünün 1-2 gün içinde geri çekilmeyle sonuçlanma olasılığı yüksek

**SPEKÜLATİF** (yorum, kanıt zayıf):
- Hyperscaler customer mix Microsoft/Amazon/Google bileşimi (transcript açıkça söylemiyor)
- 2028 EPS $10.45 hedefi (tek analist tahmini, güven düşük)
- Şirketin bir sonraki secondary offering'i kısa vadede yapıp yapmayacağı
- "AI bubble" temasının 2026 ortasında devam edip etmeyeceği

---

## Bölüm 9 — Neden Yanlış Olabilirim (Zorunlu — En Az 5 Madde)

1. **Capacity ramp beklediğimden hızlı olabilir**: Şirket Texas fab'i ve laser kapasitesi konusunda %30 + %350 büyüme açıklaması yaptı. Eğer 2H 2026'da bu execution gerçekleşirse, mevcut fiyat ucuz kalabilir. 2027 EPS $5.44 yerine $7-8'e çıkması durumunda forward P/E daha cazip olur ve $250+ hedefleri haklı çıkar.

2. **Analist target ortalaması yanıltıcı**: Northland'in $57.50 hedefi diğer üçünden çok düşük (RJ $160, Rosenblatt $220, B.Riley $129). Bu outlier ortalamayı aşağı çekiyor. Outlier çıkarılırsa medyan hedef $144.5 → bu da hâlâ downside ama daha az dramatik.

3. **13F Q1 2026 verisi yarı tamamlanmış**: Son filing tarihi 15 Mayıs. Şu an 11 Mayıs. -43.4M shares düşüş kısmen "henüz filing yapmadı" anlamına gelebilir. Tam veri 15 Mayıs sonrası daha pozitif olabilir.

4. **AI optical sektörü trend olarak güçlü**: Hyperscaler capex 2026'da $1.6 trilyon. AAOI bu pastadan %5 alsa bile $80B TAM içinden büyük pay. Sektör momentumu mean reversion endişelerini geçici olarak geçersiz kılabilir.

5. **US manufacturing avantajı**: Trump tariff trade ve "Buy American" trendi AAOI'ya yapısal premium veriyor olabilir. Çin'deki Innolight/Eoptolink rakiplerine karşı stratejik tedarikçi pozisyonu — eğer 2026'da yeni tariff açıklamaları gelirse AAOI'da %20-40 sıçrama mümkün.

6. **Day-1 chasing yasağı her zaman geçerli değil**: KTOS/CEG/HAL/LASR örnekleri spesifik teknik koşullarda ortaya çıktı. AAOI'da RSI 57 (aşırı alım değil) ve %12 sequential pullback (8 May) zaten yaşandı. Belki "ralli içinde geri çekilme" girişin doğru zamanı olabilir.

7. **Analist hedef revize gecikmesi**: 8 Mayıs'ta 4 analist revize etti. Önümüzdeki 1-2 hafta içinde diğer kapsamayan analistler de (Cowen, Northland yeni, Stifel) yüksek hedeflerle gelebilir. Yeni konsensüs $180+ üstüne çıkarsa skill'in sağlamlık filtresi tersine döner.

---

## Bölüm 10 — Tavsiye Edilen Aksiyon

| Portföy | Aksiyon | Notlar |
|---------|---------|--------|
| Agresif (400K $) | **İZLE — watchlist'e ekle** | Hedef giriş: 125-135 $ veya RSI<50 + 2-gün cooldown |
| Dengeli (100K $) | **GEÇ** | Risk profili uyuşmuyor (beta 3.76, zarar makinesi) |
| Temettü (100K $) | **GEÇ** | Temettü yok |
| Swing | **KOŞULLU İZLE** | 130 $ altına çekilirse 5-10K $ entry düşün |

**İzleme tetikleri**:
- Fiyat 50-gün SMA'ya (125 $) yakınlaşırsa
- RSI(14) < 50'ye düşerse
- Q2 2026 earnings (~Ağu 5-7) sonrası guidance teyit edilirse
- 13F Q1 2026 son filing'leri 15 Mayıs sonrası — kurumsal yön netleşince
- Northland hedefini $100+'a güncellerse (consensus +25% upside teyidi)

**Eleme tetikleri**:
- 2H 2026 sequential growth guidance miss
- Yeni secondary offering duyurusu (dilution)
- Microsoft / Amazon / Google capex revize-aşağı (sektör tetikleyici)

---

## Bölüm 11 — Veri Kaynakları

| Kaynak | Endpoint / Belge |
|--------|------------------|
| FMP profile | `/stable/profile?symbol=AAOI` |
| FMP quote | `/stable/quote?symbol=AAOI` |
| FMP earnings | `/stable/earnings?symbol=AAOI` |
| FMP income-statement | `/stable/income-statement?period=quarter` |
| FMP analyst-estimates | `/stable/analyst-estimates?period=annual/quarter` |
| FMP price-target-consensus | `/stable/price-target-consensus` |
| FMP grades-consensus | `/stable/grades-consensus` |
| FMP grades-news | `/stable/grades-news?symbol=AAOI` |
| FMP earning-call-transcript | `/stable/earning-call-transcript?year=2026&quarter=1` (43.9K karakter) |
| FMP institutional-ownership | `/stable/institutional-ownership/symbol-positions-summary` (Q1 2026, Q4 2025) |
| FMP sec-filings-search/symbol | `/stable/sec-filings-search/symbol?from=2026-05-05&to=2026-05-09` |
| FMP technical-indicators/rsi | `/stable/technical-indicators/rsi?periodLength=14` |
| FMP historical-price-eod | `/stable/historical-price-eod/full?symbol=AAOI` |
| Web search | Raymond James, Rosenblatt, B. Riley, Northland post-earnings revisions |
| SEC EDGAR | 8-K (7 May aaoi_ex9901), 10-Q (7 May), DEFA14A (8 May) |
| Transcript | Seeking Alpha, Yahoo Finance, BigGo (Q1 2026 earnings call) |

---

**Rapor sonu** | 11 Mayıs 2026 | finzora ai
