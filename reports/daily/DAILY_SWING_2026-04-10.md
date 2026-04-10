# günlük swing raporu — 10 nisan 2026, cuma

> finzora ai | sabah raporu okundu | vix: 19.90 (k-13 sakin) | k-14: kaldırıldı (9 nisan), yarım pozisyon protokolü aktif

---

## 1. swing sistem durumu

### parametreler

- **vix**: 19.90 → k-13 v4.1 bandı: sakin (< 22) — tam pozisyon teknik izni mevcut
- **spy trend**: $679.91, sma50 üstü (+%0.7), rsi 60.3 ↗
- **k-14 drawdown freni**: kaldırıldı (9 nisan 2026)
  - peak: $12,480 (3 mart 2026) | trough: $10,430 (26 mart) | dd: %16.42
  - yeniden başlama kriterleri: vix<22 ✅ + spy>sma50 ✅ + yeni kriz flare yok ✅
  - **yarım pozisyon protokolü aktif**: ilk 3 trade $5K max (trade sayacı: 0/3)
- **aktif pozisyon**: 0/6 slot | 6 boş slot

### mod kararı

k-14 resmen kaldırıldı, sistem sakin bant. ancak 7 günlük rally sonrası ichimoku 4/4 sinyal konfigürasyonu bozulmuş — tüm evren taraması 0 a-kalite aday döndürdü. bugün yeni giriş yok; earnings temizliği ve rsi normalleşmesi bekleniyor.

---

## 2. aktif pozisyonlar

**aktif swing pozisyon yok.**

| durum | değer |
|-------|-------|
| aktif pozisyon | 0 |
| boş slot | 6 |
| max slot | 6 |
| trade sayacı (yeniden başlama) | 0/3 |

---

## 3. tarama sonuçları

### evren

- fmp screener filtresi: mcap>$2B, fiyat>$10, vol>500K, nyse+nasdaq
- k-19 (xlp dışlama): consumer defensive otomatik hariç
- aşama 1 hayatta: **94 hisse**
- aşama 2 a-kalite (ichimoku 4/4): **0 hisse**

### aşama 2 neden sıfır döndü

yedi günlük rally sonrası (s&p +%3.7 bu hafta) ichimoku bileşenlerinde yapısal bozulma var:

1. **kumo rengi kırmızı**: 7-günlük fiyat artışı önceki döneme baktığında kumo kırmızı/geri dönemde → sinyal 4 başarısız
2. **RSI 65+**: aşama 1'den hayatta kalan güçlü hisseler çoğunlukla rsi 65 üstünde → aşama 2 rsi 40-65 filtresi eliyor
3. **TK cross nötr**: hızlı yükseliş tenkan-kijun aralarını daraltıyor, net bull cross oluşmuyor

bu durum anormal değil. büyük rally sonrası ichimoku 4/4 aday sayısı genellikle 2-5 gün gecikmeli oluşur.

### k-05 earnings durumu (kritik): bu hafta büyük kümeler var

| grup | hisseler | earnings tarihi | iş günü mesafe | k-05 karar |
|------|----------|----------------|-----------------|-----------|
| grup 1 | LRCX, KLAC, COHR, ONTO, VST, GEV, ETN, MRVL | 14 nisan (salı) | 2 iş günü | 🔴 giriş yok |
| grup 2 | META, NVDA, AMD, PWR, NOC, LMT, EMR | 17 nisan (cuma) | 5 iş günü | ✅ temiz |

**kritik not**: çip/ai altyapı sektörünün güçlü hisselerinin büyük çoğunluğu 14 nisan'da earnings açıklıyor. bu hafta içinde giriş = 2 iş günü = k-05 blokajı.

### dünkü takip listesi güncelleme

dün status.json'da watchlist pullback seviyeleri belirlenmişti:

| sembol | dünkü hedef | bugünkü fiyat | sonuç | not |
|--------|------------|--------------|-------|-----|
| amat | $360-365 pullback | **$397.81 (+3.1%)** | kaçırıldı | pullback olmadı, daha da yüksek |
| cat | $745-750 pullback | **$787.07 (+2.0%)** | kaçırıldı | pullback olmadı |
| atmu | $61.50 pullback | **$63.51 (+0.6%)** | kaçırıldı | pullback olmadı |

bu durum 7. gün rally momentumunun gücünü gösteriyor. "dip bekleme" disiplini doğru ama piyasa dip vermedi.

### özel inceleme: axon (rsi aşırı satım)

axon bugün -%10.27 ile $351.33 seviyesinde. son 2 haftada $450'den -%22 düşüş.

| parametre | değer | yorum |
|-----------|-------|-------|
| fiyat | $351.33 | |
| rsi | **26.4** | aşırı satım — swing sistemi 40-65 bandı dışında |
| k-05 | earnings 1 mayıs | ✅ temiz |
| k-18 | $0.2M insider satış | ✅ temiz |
| ichimoku | taranmadı | rsi < 40 filtresinde elenecek |
| karar | **izleme modu** | rsi 40'a dönünce ichimoku değerlendir |

axon aşırı satım bölgesinde. k-18 ve k-05 temiz. ancak sistemin rsi 40-65 bandı aşağıdan kırılıyor. rsi 40'a döndüğünde (2-3 gün) ve ichimoku teyit gelirse güçlü aday olabilir. şu an girmek disiplinsizlik olur.

---

## 4. nihai aday detayları

**bugün için geçerli swing girişi yok.**

tüm güçlü adaylar ya ichimoku 4/4 koşulunu karşılamıyor (rsi>65 veya kumo kırmızı) ya da k-05 earnings blokajı altında.

---

## 5. giriş planı özet

**bugün giriş yok** — gerekçe:

1. aşama 2: 94 aşama 1 adayından 0 ichimoku 4/4 geçidi → sistem "giriş yok" sinyali veriyor
2. k-05: 14 nisan büyük chip earnings kümesi → 2 iş günü mesafe = giriş yapılamaz
3. rsi yapısı: 7 günlük rally sonrası güçlü hisseler rsi 65-75 bandında → swing 40-65 bandı koşulu sağlanmıyor
4. yarım pozisyon protokolü aktif: zaten $5K lot büyüklüğü — setup olmadan zorlamak anlamı yok

### gelecek hafta için watchlist (14 nisan sonrası)

earnings açıklamasından sonra tepki bazlı setup değerlendirilecek hisseler:

| sembol | fiyat | rsi | sektör | earnings | neden izle |
|--------|-------|-----|--------|----------|------------|
| cohr | $284.17 | 60.5 | ai optik | 14 nis | rsi bölge ✅, güçlü ai tema |
| lrcx | $258.76 | 65.4 | semi ekipman | 14 nis | rsi sınırda, güçlü momentum |
| klac | $1,727 | 69.6 | semi ekipman | 14 nis | rsi yüksek ama sektör lideri |
| onto | $246.96 | 67.1 | semi ekipman | 14 nis | rsi biraz yüksek |
| axon | $351.33 | 26.4 | teknoloji | 1 mayıs | rsi 40'a dönünce değerlendir |

**pead stratejisi**: earnings sonrası güçlü tepki + rsi normalleşmesi = a-kalite setup. pre-earnings giriş yapılmaz (k-05).

---

## 6. istatistik

**not**: swing sistemi yeniden başlatma protokolünde (k-14 kaldırıldı 9 nisan). yeni trade sayacı: 0. geçmiş closed.json kayıtları ayrı tutulmaktadır. sistematik swing istatistik birikmesi bu haftadan başlıyor.

---

## 7. sistem durumu özeti

| bileşen | durum |
|---------|-------|
| k-14 drawdown freni | kaldırıldı (9 nisan) |
| yarım pozisyon protokolü | aktif (trade sayacı 0/3) |
| k-13 bandı | sakin (vix 19.90) |
| aktif swing pozisyon | 0/6 |
| ichimoku 4/4 aday | 0 (rally sonrası geçici) |
| k-05 durumu | 14 nisan büyük earnings kümesi aktif |
| gelecek giriş penceresi | 14-15 nisan (chip earnings sonrası) |

---

*finzora ai | fmp api + web search | nyse açılışına ~2 saat | tr 11:25*
