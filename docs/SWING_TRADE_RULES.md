# SWING TRADE KURAL SETİ v2.0

> **Son güncelleme**: 25 Şubat 2026  
> **Amaç**: Sistematik, tekrarlanabilir ve ölçülebilir swing trade süreci  
> **Felsefe**: Sabit yüzde stop yerine volatiliteye dayalı (ATR-based) dinamik risk yönetimi

---

## 1. HİSSE SEÇİM KRİTERLERİ (Evren Filtresi)

Swing trade adayı olabilmek için bir hissenin aşağıdaki **tüm** kriterleri karşılaması gerekir:

| Kriter | Minimum | Açıklama |
|--------|---------|---------|
| Market cap | $2B+ | Micro-cap gürültüsünü engelle |
| Fiyat | $10 - $300 | Penny stock ve aşırı pahalı hisselerden kaçın |
| Günlük ortalama hacim (20 gün) | 500K+ hisse | Likidite, slippage riski azaltma |
| Beta | 1.0+ | Yeterli hareket potansiyeli (volatilite) |
| ATR% (14 gün ATR / fiyat × 100) | %2+ | Günlük yeterli fiyat hareketi |

### Temel analiz minimum filtresi (çöp eleme)

Swing trade teknik ağırlıklıdır ama **temelden bozuk hisselere teknik sinyal üzerine girmek** en büyük tuzaktır. aşağıdaki filtreler "en iyiyi bulmak" için değil, **en kötüleri elemek** içindir. FMP API'den tek seferde çekilir, taramaya 10 saniye ekler.

| filtre | kriter | FMP endpoint | neden |
|--------|--------|-------------|-------|
| gelir trendi | son çeyrek revenue YoY > %0 | `income-statement` (quarter) | küçülen şirkete swing girme |
| kârlılık | EBITDA > 0 (son çeyrek) | `income-statement` (quarter) | para yakan şirkete girme |
| borç kontrolü | D/E < 3.0 | `ratios-ttm` | aşırı kaldıraçlı şirket batma riski |
| analist görüşü | consensus "strongSell" DEĞİL | `grades-consensus` | herkesin sattığı hisseye karşı gitme |

> **NOT**: bu filtreler eleme amaçlıdır, geçmesi yeterli şart değildir. teknik giriş sinyali + teyitler hala zorunludur.

### Hariç tutulacak sektörler (swing trade için uygunsuz):
- **Utilities** (kamu hizmetleri) — düşük volatilite, yavaş hareket
- **REITs** — faiz oranına duyarlı, dar range
- **Düşük beta defensive** hisseler (beta < 0.8)

### Tercih edilen sektörler:
- Teknoloji, Sağlık, Enerji, Tüketim Döngüsel, Endüstriyel
- Sektörde aktif momentum/rotasyon olan alanlar

---

## 2. GİRİŞ STRATEJİLERİ (6 Yöntem)

Her giriş için minimum **2 teyit** gerekir. Tek gösterge ile giriş yapılmaz.

### 2a. RSI Oversold Bounce
- **Tetik**: RSI(14) < 30
- **Teyitler**: Hacim artışı (1.5x+ 20 gün ortalaması), destek seviyesinde tutunma
- **Giriş**: RSI 30'u yukarı kırdığında (dönüş teyidi)
- **NOT**: RSI < 30 tek başına giriş sinyali DEĞİLDİR. dönüş teyidi bekle

### 2b. Breakout (Kırılım)
- **Tetik**: Fiyat 50 günlük SMA'yı veya kilit direnç seviyesini yukarı kırdığında
- **Teyitler**: Hacim 1.5x+ ortalama, ADX > 25 (trend gücü)
- **Giriş**: Kırılım mumu kapanışında veya sonraki geri çekilme testinde

### 2c. Pullback (Geri Çekilme)
- **Tetik**: Güçlü yükseliş trendinde fiyat 20 günlük EMA'ya geri çekilme
- **Teyitler**: RSI 40-60 aralığında (sağlıklı geri çekilme), trend bozulmamış
- **Giriş**: EMA'dan seken ilk yeşil mum kapanışında

### 2d. Earnings Momentum (Kazanç İvmesi — Earnings Sonrası)
- **Tetik**: Earnings beat > %10, guidance yükseltme
- **Teyitler**: Gap-up + yüksek hacim, sektör desteği
- **Giriş**: Earnings sonrası ilk geri çekilme (gap fill kısmen veya tamamen)
- **UYARI**: Earnings günü girme. minimum 1 gün bekle

### 2e. Earnings Catalyst (Earnings Öncesi Giriş)
- **Tetik**: 3-7 gün içinde earnings açıklaması var
- **Ön koşullar** (hepsi gerekli):
  - Son 4 çeyrek beat oranı ≥ %75 (4'te en az 3'ü beat etmiş) — `analyst-estimates` ile kontrol
  - Sektör momentum'u pozitif (sektördeki diğer earnings'ler iyi gelmiş)
  - Whisper number / Street consensus'tan yüksek beklenti sinyalleri
  - Hisse earnings öncesi aşırı rally yapmamış (son 5 günde < %5 yükseliş)
- **Teyitler**: RSI 40-65 aralığında (aşırı alım değil), hacim normale yakın
- **Giriş**: Earnings'ten 2-3 gün önce, teknik destek yakınında
- **Risk yönetimi**:
  - Gap-down riski var, stop-loss gap'te tetiklenmeyebilir — bunu kabul ederek giriyorsun
  - Earnings sonrası ilk 30 dakika işlem yapma, volatilite oturmasını bekle
  - Beat gelirse: kademeli çıkış planı uygula (bölüm 4)
  - Miss gelirse: açılışta değerlendir, panik satma ama tezi tekrar kontrol et
- **UYARI**: Bu en riskli stratejidir. diğer 5 yöntemden farklı olarak binary sonuç (beat/miss) var. sadece güçlü tarihsel beat oranı olan şirketlerde kullan

### 2f. Sektör Rotasyonu Lideri
- **Tetik**: Sektör ETF'i 5 günlük > %3 performans
- **Teyitler**: Hisse sektör ETF'inden daha güçlü (relative strength), hacim artışı
- **Giriş**: Sektördeki en güçlü 2-3 hisseden seç

---

## 3. STOP-LOSS YÖNETİMİ (ATR Tabanlı)

### Sabit yüzde stop KULLANMA. Bunun yerine:

### İlk Stop-Loss (Initial Stop)
```
LONG pozisyon: Giriş fiyatı - (2.0 × ATR14)
SHORT pozisyon: Giriş fiyatı + (2.0 × ATR14)
```

| Piyasa Durumu | ATR Çarpanı | Açıklama |
|---------------|-------------|---------|
| Düşük volatilite | 1.5x ATR | Dar stop, sıkı risk |
| Normal volatilite | 2.0x ATR | Standart |
| Yüksek volatilite | 2.5-3.0x ATR | Geniş stop, nefes alanı ver |

### Neden ATR tabanlı?
- Sabit %5 stop bir $10 hisse için mantıklı olabilir ama $500 hisse için anlamsız
- ATR hissenin gerçek volatilitesine göre ayarlanır
- DUK gibi düşük volatilite hisselerde dar, TSLA gibi yükseklerde geniş stop verir

### Stop seviyesi kontrol:
- Stop, en yakın destek seviyesinin **altında** olmalı
- Stop giriş fiyatından ATR'den daha yakınsa → trade alma, R:R bozulur

---

## 4. KAR ALMA STRATEJİSİ (Kademeli Çıkış)

### 3 Aşamalı Çıkış Planı:

#### Aşama 1: İlk Kar (pozisyonun %50'si)
- **Hedef**: 2.0 × risk mesafesi (giriş - stop arası)
- Yani stop 2 ATR uzaksa, hedef de 4 ATR uzak → R:R = 2:1
- Hedefe ulaşınca pozisyonun yarısını sat

#### Aşama 2: Trailing Stop (kalan %50)
- İlk %50 satıldıktan sonra stop'u breakeven'e (giriş fiyatına) çek
- Trailing stop: Zirve fiyattan 2.0 × ATR14 uzaklıkta takip et
- Fiyat yeni zirve yaptıkça trailing stop da yukarı gelir

#### Aşama 3: Final Çıkış
- Trailing stop tetiklendiğinde kalan %50'yi sat
- VEYA fiyat 50 günlük SMA'nın altına kapanırsa çık
- VEYA giriş tezini bozan bir haber gelirse hemen çık

### R:R Hedefleri
| Minimum | Tercih edilen | İdeal |
|---------|---------------|-------|
| 2:1 | 3:1 | 5:1+ (trend devam ederse) |

**2:1'in altında R:R olan hiçbir trade açılmaz.**

---

## 5. POZİSYON BOYUTLANDIRMA

### %1 Risk Kuralı
Her trade'de toplam portföy değerinin maksimum **%1-2**'si risklendirilir.

```
Pozisyon büyüklüğü = (Portföy × Risk%) / (Giriş fiyatı - Stop fiyatı)

Örnek:
- Portföy: $100,000
- Risk: %1 = $1,000
- Giriş: $50.00
- Stop: $47.00 (2x ATR = $3.00)
- Pozisyon: $1,000 / $3.00 = 333 hisse
- Yatırım tutarı: 333 × $50 = $16,650
```

### Eşzamanlı pozisyon limitleri
| Kural | Değer |
|-------|-------|
| Max eşzamanlı pozisyon | 10 |
| Max tek sektör ağırlık | 3 pozisyon |
| Max portföy riski (tüm açık pozisyonlar) | %6 |

---

## 6. TRADE YÖNETİMİ

### Giriş sonrası günlük kontrol listesi:
1. Stop-loss seviyesi hala geçerli mi? (destek kırılmadı mı?)
2. ATR değişti mi? trailing stop güncelle
3. Giriş tezi hala geçerli mi?
4. Sektör momentumu devam ediyor mu?
5. Yaklaşan earnings/haber var mı?

### Önemli kurallar:
- **Mevcut pozisyon + yaklaşan earnings**: Eğer açık pozisyonda 5 gün içinde earnings varsa:
  - Kârdaysan: giriş tezi güçlüyse tut (earnings catalyst gibi değerlendir), değilse %50 kapat
  - Zarardaysan: ya tamamen kapat ya da tez hala geçerliyse stop sıkılaştırıp tut
  - Her durumda earnings tarihini `durum` alanına yaz
- **Korelasyon kontrolü**: Aynı sektörden 3'ten fazla pozisyon açma
- **Kayıp serisi kuralı**: 3 ardışık kayıp sonrası 2 gün trade'e ara ver, stratejiyi gözden geçir
- **Momentum bozulması**: Hisse giriş tezini kaybederse (sektör zayıfladı, haber geldi) bekleme, stop'u sıkılaştır

---

## 7. TARAMA YÖNTEMLERİ VE KAYIT

Her trade açılırken `tarama_yontemi` alanı ZORUNLU doldurulur:

| Yöntem Kodu | Açıklama | Temel Göstergeler |
|-------------|---------|-------------------|
| `RSI oversold` | RSI < 30 bounce | RSI(14), hacim, destek |
| `breakout` | Direnç/SMA kırılımı | 50SMA, hacim 1.5x+, ADX |
| `pullback` | Trend içi geri çekilme | 20EMA, RSI 40-60, trend |
| `earnings momentum` | Earnings beat sonrası | EPS surprise, guidance, gap |
| `earnings catalyst` | Earnings öncesi giriş | Son 4Q beat oranı ≥%75, sektör momentum, whisper |
| `sektor rotasyonu` | Sektör liderliği | Sektör ETF RS, hacim |

### Yöntem bazlı performans takibi
Her ay sonunda yöntem bazlı analiz yap:
```
Yöntem | Trade sayısı | Win rate | Ort kazanç | Ort kayıp | Expectancy
-------|-------------|----------|-----------|----------|----------
RSI    |     X       |   XX%    |   +X.X%   |  -X.X%   |   $XXX
```
Expectancy negatif olan yöntemi 1 ay askıya al veya revize et.

---

## 8. TRADE GÜNLÜĞÜ GEREKSİNİMLERİ

### Giriş kaydı (active.json — zorunlu alanlar):
- `id`, `sembol`, `giris_tarihi`, `giris_fiyati`
- `hedef_fiyat`: hesaplama göster (örn: "giriş + 2×risk")
- `stop_loss`: ATR tabanlı hesaplama göster
- `giris_nedeni`: detaylı türkçe tez
- `katalizor`: tetikleyici olay
- `tarama_yontemi`: yukarıdaki 5 yöntemden biri
- `atr_giris`: giriş anındaki ATR(14) değeri (yeni alan)
- `risk_tutar`: dolar cinsinden risk (yeni alan)
- `rr_orani`: hedeflenen reward:risk (yeni alan)

### Çıkış kaydı (closed.json — zorunlu alanlar):
- Mevcut tüm alanlar +
- `cikis_yontemi`: "hedef", "trailing_stop", "tez_bozuldu", "zaman" veya "earnings_oncesi"
- `gercek_rr`: gerçekleşen reward:risk oranı

---

## 9. YAPILMAYACAKLAR LİSTESİ

| # | Kural | Neden |
|---|-------|-------|
| 1 | +%30 rally sonrası momentum chasing yapma | Geç giriş, kâr realizasyonu riski |
| 2 | Utility/REIT hisselerinde swing trade açma | Düşük volatilite, ATR yetersiz |
| 3 | Beta < 0.8 hissede swing trade açma | Hareket potansiyeli düşük |
| 4 | Tek gösterge ile giriş yapma | Minimum 2 teyit gerekli |
| 5 | Stop-loss'suz pozisyon açma | Her pozisyonun tanımlı stop'u olmalı |
| 6 | Kayıp pozisyona ekleme (averaging down) yapma | Batık maliyet yanılgısı |
| 7 | Aynı sektörden 3+ pozisyon açma | Korelasyon riski |
| 8 | Gün içi duygusal karar verme | Plana sadık kal |
| 9 | Stop'u geriye çekme (genişletme) | İlk plan en objektif plan |
| 10 | Sabit yüzde stop kullanma | ATR tabanlı dinamik stop kullan |

---

## 10. HAFTALIK DEĞERLENDİRME

Her pazar günü (weekly rapor içinde) swing trade bölümü:
1. Haftalık P&L ve win rate
2. Yöntem bazlı performans
3. Açık pozisyon durumları ve stop seviyeleri
4. Watchlist güncelleme
5. Hatalar ve dersler
6. Bir sonraki hafta planı

---

## 11. FMP API İLE TARAMA ŞABLONU

```python
# ATR hesaplama
atr_data = fmp_get("technical-indicators/sma", {
    "symbol": ticker,
    "periodLength": 14,
    "timeframe": "1day"
})

# RSI kontrolü
rsi_data = fmp_get("technical-indicators/rsi", {
    "symbol": ticker,
    "periodLength": 14,
    "timeframe": "1day"
})

# Profil (beta, market cap, volume)
profile = fmp_get("profile", {"symbol": ticker})

# Filtrele
if (profile['beta'] >= 1.0 and
    profile['mktCap'] >= 2e9 and
    profile['volAvg'] >= 500000 and
    profile['price'] >= 10 and
    profile['price'] <= 300):
    # Aday listesine ekle
    pass
```

---

## SÖZLÜK

| Terim | Açıklama |
|-------|---------|
| ATR (Average True Range) | 14 günlük ortalama gerçek aralık — volatilite ölçüsü |
| R:R (Reward:Risk) | Kar hedefi / stop mesafesi oranı |
| Trailing stop | Fiyat yükseldikçe yukarı çekilen dinamik stop |
| Breakeven stop | Stop'u giriş fiyatına çekme (sıfır risk) |
| Relative Strength | Hissenin sektör/endeks karşısındaki göreceli gücü |
| ATR% | (ATR / fiyat) × 100 — fiyata göre normalize volatilite |
| Expectancy | (Win% × Ort kazanç) - (Loss% × Ort kayıp) — sistemin beklenen değeri |

---

## 12. DOSYA ŞEMALARI (JSON Yapıları)

> Bu bölüm swing trade JSON dosyalarının veri yapısını tanımlar.

### 12a. `data/swing/active.json` — Açık Pozisyonlar

```json
{
  "son_guncelleme": "2026-02-20T16:36:55.511599",
  "not": "SWING TRADE SADECE SİMÜLASYON - Sadece % kazanç/kayıp takibi (MAX: 10 pozisyon)",
  "aktif_pozisyonlar": [
    {
      "id": "SWING-001",
      "sembol": "NEM",
      "giris_tarihi": "2026-02-12",
      "giris_fiyati": 118.12,
      "guncel_fiyat": 124.97,
      "guncel_kar_zarar_yuzde": 5.80,
      "hedef_fiyat": 129.93,
      "stop_loss": 112.21,
      "tutulan_gun": 7,
      "giris_nedeni": "Güçlü momentum, altın madenciliği lideri, güvenli liman talebi",
      "katalizor": "Altın fiyat gücü, malzeme sektörü rotasyonu",
      "tez": "Dünyanın en büyük altın üreticisi, emtia gücü",
      "zaman_cercevesi": "7-10 gün",
      "risk": "Altın fiyat dönüşü, dolar güçlenmesi",
      "durum": "Normal aralıkta",
      "tarama_yontemi": "breakout",
      "atr_giris": 3.45,
      "risk_tutar": 690,
      "rr_orani": "2.5:1",
      "son_guncelleme": "2026-02-20T19:41:14.015574",
      "partial_exit_plan": {
        "hedef_ulasildiginda": {
          "aksiyon": "%50 POZİSYONU SAT",
          "satis_fiyati": 129.93,
          "sebep": "Kar garantiye al"
        },
        "kalan_50_icin": {
          "aksiyon": "TRAİLİNG STOP AKTİF",
          "baslangic_trailing_stop": 123.43,
          "trailing_yuzde": 5,
          "aciklama": "Zirveden 2xATR düşünce sat"
        },
        "durum": "Hedef bekleniyor"
      }
    }
  ]
}
```

#### Aktif Pozisyon — Zorunlu Alanlar

| Alan | Türü | Açıklama |
|------|------|---------|
| `id` | string | `"SWING-NNN"` formatında sıralı ID |
| `sembol` | string | Büyük harf ticker |
| `giris_tarihi` | date | `"YYYY-MM-DD"` |
| `giris_fiyati` | float | Giriş fiyatı |
| `guncel_fiyat` | float | Güncel kapanış fiyatı |
| `guncel_kar_zarar_yuzde` | float | `((guncel - giris) / giris) × 100` |
| `hedef_fiyat` | float | Giriş + (2 × risk mesafesi) minimum |
| `stop_loss` | float | Giriş - (2 × ATR14) |
| `tutulan_gun` | int | Giriş tarihinden itibaren geçen gün |
| `giris_nedeni` | string | Türkçe, detaylı neden |
| `katalizor` | string | Türkçe, tetikleyici olay |
| `tez` | string | Türkçe, yatırım tezi |
| `zaman_cercevesi` | string | Örn: `"7-10 gün"` |
| `risk` | string | Türkçe, ana riskler |
| `durum` | string | Güncel durum açıklaması |
| `tarama_yontemi` | string | **ZORUNLU** — 5 yöntemden biri (bkz. Bölüm 2) |
| `atr_giris` | float | **ZORUNLU** — giriş anındaki ATR(14) değeri |
| `risk_tutar` | float | **ZORUNLU** — dolar cinsinden risk miktarı |
| `rr_orani` | string | **ZORUNLU** — hedeflenen R:R oranı |
| `son_guncelleme` | datetime | Her güncellemede yenile |

#### Tarama Yöntemleri (`tarama_yontemi` değerleri)
- `"RSI oversold"` — RSI < 30, dönüş teyidi + hacim artışı
- `"earnings momentum"` — Kazanç sürprizi >%10 sonrası geri çekilme girişi
- `"earnings catalyst"` — Earnings öncesi giriş, son 4Q beat oranı ≥%75
- `"breakout"` — 50SMA/direnç kırılımı + hacim 1.5x+ + ADX > 25
- `"pullback"` — Trend içi 20EMA'ya geri çekilme, RSI 40-60
- `"sektor rotasyonu"` — Sektör ETF'i 5g >%3, hisse RS güçlü

---

### 12b. `data/swing/closed.json` — Kapanmış Pozisyonlar

```json
{
  "son_guncelleme": "2026-02-20",
  "kapatilan_pozisyonlar": [
    {
      "id": "SWING-001",
      "sembol": "GOOGL",
      "giris_tarihi": "2026-01-02",
      "cikis_tarihi": "2026-02-03",
      "giris_fiyati": 315.15,
      "cikis_fiyati": 339.71,
      "kar_zarar_yuzde": 7.79,
      "tutulan_gun": 23,
      "cikis_nedeni": "Hedefe yakın, kar realize edildi",
      "cikis_yontemi": "hedef",
      "tarama_yontemi": "breakout",
      "gercek_rr": "2.3:1",
      "sonuc": "KAZANÇ",
      "ders": "Momentum devam stratejisi çalıştı."
    }
  ]
}
```

#### Kapanmış Pozisyon — Zorunlu Alanlar

| Alan | Türü | Açıklama |
|------|------|---------|
| `id` | string | Orijinal SWING ID |
| `sembol` | string | Ticker |
| `giris_tarihi` | date | `"YYYY-MM-DD"` |
| `cikis_tarihi` | date | `"YYYY-MM-DD"` |
| `giris_fiyati` | float | Giriş fiyatı |
| `cikis_fiyati` | float | Çıkış fiyatı |
| `kar_zarar_yuzde` | float | `((cikis - giris) / giris) × 100` |
| `tutulan_gun` | int | Giriş → çıkış arası gün |
| `cikis_nedeni` | string | Türkçe, neden çıkıldı |
| `cikis_yontemi` | string | **ZORUNLU** — `"hedef"`, `"trailing_stop"`, `"tez_bozuldu"`, `"earnings_oncesi"` |
| `tarama_yontemi` | string | **ZORUNLU** — girişte kullanılan yöntem |
| `gercek_rr` | string | **ZORUNLU** — gerçekleşen R:R oranı |
| `sonuc` | string | `"KAZANÇ"` veya `"ZARAR"` |
| `ders` | string | Türkçe, bu trade'den çıkarılan ders |

---

### 12c. `data/swing/watchlist.json` — İzleme Listesi

```json
{
  "son_guncelleme": "2026-02-20T16:48:07.288589",
  "not": "Bir sonraki işlemler için potansiyel swing adayları",
  "izleme_listesi": [
    {
      "sembol": "SPG",
      "guncel_fiyat": 202.01,
      "beta": 1.45,
      "atr_yuzde": 2.8,
      "sektor": "Tüketim Döngüsel",
      "notlar": "Breakout setup oluşuyor, 50SMA üzeri kapanış bekleniyor",
      "tarama_yontemi": "breakout",
      "urgency": "medium",
      "ekleme_tarihi": "2026-02-20",
      "son_kontrol": null,
      "hedef_giris": "195-200",
      "hedef_fiyat": 220.0,
      "stop_loss": 190.0,
      "tahmini_rr": "2.5:1"
    }
  ],
  "haric_tutulanlar": [
    {
      "sembol": "DUK",
      "neden": "Utility sektörü - swing trade evreni dışı (beta < 1.0, ATR% < 2)"
    }
  ]
}
```

#### Watchlist Aday — Alanlar

| Alan | Türü | Açıklama |
|------|------|---------|
| `sembol` | string | Ticker |
| `guncel_fiyat` | float | Güncel fiyat |
| `beta` | float | **ZORUNLU** — 1.0+ olmalı |
| `atr_yuzde` | float | **ZORUNLU** — %2+ olmalı |
| `sektor` | string | Türkçe sektör |
| `notlar` | string | Türkçe gözlemler |
| `tarama_yontemi` | string | Hangi yöntemle tarandı |
| `urgency` | string | `"high"` / `"medium"` / `"low"` |
| `ekleme_tarihi` | date | Watchlist'e eklenme tarihi |
| `son_kontrol` | date/null | Son kontrol tarihi |
| `hedef_giris` | string | Fiyat aralığı (örn. `"195-200"`) |
| `hedef_fiyat` | float | Hedef çıkış fiyatı |
| `stop_loss` | float | ATR tabanlı stop seviyesi |
| `tahmini_rr` | string | Tahmini R:R oranı |
