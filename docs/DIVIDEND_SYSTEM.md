# TEMETTÜ PORTFÖYÜ SİSTEMİ v1.0 — TEMA + KALİTE + MOMENTUM

> **versiyon**: 1.0
> **son güncelleme**: 3 nisan 2026
> **portföy**: data/portfolios/dividend.json
> **başlangıç**: $100K (17 şubat 2026)
> **hedef**: yıllık %8-12 sermaye artışı + temettü geliri
> **max pozisyon**: 6 hisse, tek hisse max %20

---

## FELSEFESİ

temettü portföyü sadece "yüksek yield" avlamak değil. güçlü bir tema/hikâye içinde, kaliteli temettü ödeyen, büyüyen ve teknik olarak güçlü hisseleri almak.

üç tuzaktan kaçınma:
1. **yield tuzağı**: %8 yield veren ama fiyatı eriyen hisse → toplam getiri negatif
2. **ölü sektör tuzağı**: iyi temettü ama sektör hikâyesi yok → sermaye büyümesi sıfır
3. **düşen bıçak tuzağı**: "ucuzladı, yield arttı" diye almak → tez bozulmuş olabilir

---

## 1. TEMA / HİKÂYE FİLTRESİ (25 puan)

her dönemin çalışan hikâyeleri var. temettü portföyü de bu hikâyelerin içinden hisse seçer.

### dönemsel tema örnekleri

- faiz düşüşü → REITs, utilities, yüksek borçlu temettü hisseleri
- enerji krizi / savaş → XOM, CVX, COP, enerji altyapısı
- savunma harcamaları artışı → RTX, LMT, NOC, GD
- AI altyapısı → veri merkezi REITs (DLR, EQIX), enerji (VST, CEG)
- tüketim toparlanması → perakende, tüketici markaları
- banka karlılığı artışı → JPM, BAC, WFC

### puanlama

| puan | durum |
|:----:|-------|
| 25 | aktif tema, güçlü rüzgâr, sektör outperform ediyor |
| 20 | tema var ama henüz fiyatlara tam yansımamış |
| 15 | nötr tema, sektör endeksle uyumlu |
| 10 | tema zayıflıyor, rüzgâr azalıyor |
| 5 | ters rüzgâr var, sektör underperform |
| 0 | tema tamamen bozulmuş |

### kural

- sadece aktif temaya giren sektör ve hisseler izleme listesine alınır
- temalar haftalık değerlendirilir (pazar günü raporu)
- bir tema bozulduğunda o temadaki pozisyonlar gözden geçirilir (hemen satma, tez bozulduysa sat)

---

## 2. TEMETTÜ KALİTESİ FİLTRESİ (25 puan)

### kriterler

| kriter | ideal | kabul edilebilir | red |
|--------|:-----:|:----------------:|:---:|
| temettü yield | %2.5-5 | %1.5-7 | <%1 veya >%8 (tuzak riski) |
| temettü geçmişi | 10+ yıl kesintisiz | 5+ yıl kesintisiz | kesinti var |
| temettü büyüme (5y CAGR) | >%8 | >%3 | <%0 (düşüyor) |
| payout ratio | <%60 | <%75 | >%90 (sürdürülemez) |
| FCF payout ratio | <%70 | <%85 | >%100 (FCF'den fazla ödüyor) |

### puanlama

| puan | durum |
|:----:|-------|
| 25 | 5 kriterin hepsi ideal aralıkta |
| 20 | 4 kriter ideal, 1 kabul edilebilir |
| 15 | çoğu kabul edilebilir, hiçbiri red bölgesinde değil |
| 10 | 1 kriter red bölgesine yakın |
| 5 | 2+ kriter zayıf |
| 0 | temettü kesintisi riski yüksek |

### temettü büyüme oranı önemli notu

mevcut yield'den daha önemli olan temettü büyüme oranıdır:
- %2 yield + %15 yıllık büyüme → 5 yılda yield on cost: %4
- %5 yield + %0 büyüme → 5 yılda yield on cost: %5
- birincisi ikincisini 7-8 yılda geçer ve fiyat artışı da eklenince toplam getiri çok daha yüksek

büyüme oranı yüksekse düşük başlangıç yield'i kabul edilir.

---

## 3. FİNANSAL BÜYÜME (20 puan)

### kriterler

| kriter | ideal | kabul edilebilir | red |
|--------|:-----:|:----------------:|:---:|
| gelir büyümesi (YoY) | >%5 | >%0 | negatif ve kötüleşen |
| FAVÖK marjı trendi | yükseliyor | stabil | düşüyor |
| EPS büyümesi (YoY) | >%8 | >%0 | negatif |
| D/E oranı | <1.0 | <1.5 | >2.0 (sektöre göre, utilities/REITs hariç) |
| serbest nakit akışı (FCF) | büyüyor | stabil pozitif | negatif |

### puanlama

| puan | durum |
|:----:|-------|
| 20 | tüm kriterler ideal, büyüme hikâyesi güçlü |
| 15 | çoğu olumlu, 1-2 nötr |
| 10 | karışık, büyüme yavaşlıyor ama kırılmamış |
| 5 | büyüme duraklamış, marjlar baskı altında |
| 0 | küçülme, tez bozulmuş |

### analist tahmin kontrolü

- son 90 günde EPS tahmin revizyonu: yukarı mı aşağı mı?
- şirket guidance: yükseltildi / korundu / düşürüldü?
- son çeyrek sonuçları hikâyeyi destekliyor mu?
- analist revizyonu aşağıysa büyüme puanından -5

---

## 4. MOMENTUM / TEKNİK (15 puan)

### kriterler

| kriter | puan |
|--------|:----:|
| fiyat > 200SMA | 4 |
| fiyat > 50SMA | 3 |
| 50SMA > 200SMA (golden cross) | 3 |
| 6 aylık performans > SPY | 3 |
| hacim trendi artıyor veya stabil | 2 |

toplam: 15 puan

### kural

- fiyat 200SMA altındaysa maksimum momentum puanı 5 (diğer kriterler olsa bile sınırlanır)
- "iyi temettü ama ölü grafik" hisseler bu filtre ile ayıklanır
- düşen bıçak koruması: fiyat 50SMA altında + 200SMA altındaysa momentum puanı 0

---

## 5. DEĞERLEME (15 puan)

### kriterler

| kriter | ideal | kabul edilebilir | red |
|--------|:-----:|:----------------:|:---:|
| forward P/E | <15 | <20 | >25 |
| P/FCF | <15 | <20 | >25 |
| EV/EBITDA | <10 | <14 | >18 |
| yield on cost potansiyeli (5y) | >%5 | >%3 | <%2 |

### puanlama

| puan | durum |
|:----:|-------|
| 15 | açıkça ucuz, yield on cost potansiyeli yüksek |
| 12 | makul değerleme, endekse göre iskontolu |
| 9 | adil değerlenmiş |
| 6 | biraz pahalı ama büyüme ile haklı |
| 3 | pahalı, yield düşük |
| 0 | aşırı pahalı, temettü yatırımı olarak anlamsız |

### yield on cost hesaplama

```
yield_on_cost_5y = mevcut_yield × (1 + temettü_büyüme_oranı) ^ 5
```

bu metrik mevcut yield'den daha önemli: düşük yield + yüksek büyüme > yüksek yield + sıfır büyüme

---

## 6. TOPLAM SKOR VE GİRİŞ KARARI

### skor eşikleri

| skor | karar |
|:----:|-------|
| 80-100 | güçlü aday — giriş yapılabilir |
| 65-79 | iyi aday — tetikleyici bekle |
| 50-64 | izleme listesinde tut, henüz alma |
| <50 | değerlendirme dışı |

### giriş kuralı

- skor ≥65 olan hisselerde net bir tetikleyici bekle:
  - yatay kırılım (direnç aşımı + hacim)
  - bilanço sonrası güç (beat + guidance korundu)
  - destek seviyesinden sıçrama
  - temettü artışı açıklaması
- "ucuzladı" diye değil, "hikâye + kalite + fiyat gücü birlikte var" diye al
- hisseyi tek seferde değil 2-3 parçada al (ortalama maliyet riski azalır)

### pozisyon büyüklüğü

| skor | max ağırlık |
|:----:|:-----------:|
| 80-100 | %20 |
| 65-79 | %12 |

---

## 7. PORTFÖY YÖNETİMİ

### ağırlık kuralları

- max 6 pozisyon (tüm portföylerde aynı kural)
- tek hisse max %20
- tek sektör max %40 (6 hisseden max 2 aynı sektör)
- aynı temadan max 3 hisse (tema bozulma riski sınırlanır)

### sektör korelasyonu

yeni ekleme yapılırken mevcut portföyle korelasyon kontrol edilir:
- aynı sektörden zaten 2 hisse varsa → ekleme yapılmaz (max 2/sektör)
- farklı sektörden ekleme öncelikli (diversifikasyon)
- tema değişiminde sektör rotasyonu yapılır

### çıkış kuralları

| durum | aksiyon |
|-------|--------|
| tema bozuldu | yeniden değerlendir, tez yoksa sat |
| temettü kesildi veya donduruldu | hemen sat (birincil çıkış sinyali) |
| payout ratio >%90'a çıktı | uyarı, 1 çeyrek izle, düzelmezse sat |
| fiyat 200SMA altına düştü + 30 gün kaldı | momentum kırılmış, yeniden değerlendir |
| skor <50'ye düştü | sat |
| daha iyi alternatif var (skor farkı >15) | swap değerlendir |

### temettü kesilmezse düşüşte ne yapılır

- fiyat düşüyor ama temettü artıyor/koruyor → hold (yield on cost artıyor)
- fiyat düşüyor + tema sağlam + skor >65 → ekleme fırsatı (2. veya 3. parça)
- fiyat düşüyor + tema bozulmuş → sat (fiyat düşüşü haklı)

---

## 8. HAFTALIK GÖZDEN GEÇİRME

her pazar günü raporunda:

1. **aktif temalar**: skor 1-10, değişim yönü
2. **mevcut pozisyonlar**: skor güncellemesi, çıkış sinyali var mı
3. **izleme listesi**: yeni adaylar, tetikleyici yaklaşanlar
4. **sektör dengesi**: yoğunlaşma riski kontrolü
5. **temettü takvimi**: yaklaşan ex-dividend tarihleri

---

## 9. VERİ KAYNAKLARI

### FMP API endpointleri

- `company-screener`: evren oluşturma (mcap, yield, sektör filtresi)
- `ratios`: P/E, P/FCF, EV/EBITDA, payout ratio, D/E
- `income-statement`: gelir, FAVÖK, EPS trendi
- `cash-flow-statement`: FCF
- `historical-price-eod`: teknik analiz (SMA, momentum)
- `analyst-estimates`: tahmin revizyonları
- `stock-dividend-calendar`: temettü geçmişi ve takvim
- `insider-trading`: K-18 insider kontrol

### tarama akışı (seans içi)

1. FMP screener → temaya uyan sektör hisseleri çek
2. temettü kalite filtresi uygula (yield, geçmiş, payout)
3. finansal büyüme kontrol (gelir, EPS, FCF)
4. momentum kontrol (SMA200, SMA50, RS)
5. değerleme kontrol (P/E, yield on cost)
6. toplam skor hesapla → ≥65 → aday listesine al

---

*finzora ai | temettü portföyü sistemi v1.0 | 3 nisan 2026*
