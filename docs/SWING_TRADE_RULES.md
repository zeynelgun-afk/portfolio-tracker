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

### Hariç tutulacak sektörler (swing trade için uygunsuz):
- **Utilities** (kamu hizmetleri) — düşük volatilite, yavaş hareket
- **REITs** — faiz oranına duyarlı, dar range
- **Düşük beta defensive** hisseler (beta < 0.8)

### Tercih edilen sektörler:
- Teknoloji, Sağlık, Enerji, Tüketim Döngüsel, Endüstriyel
- Sektörde aktif momentum/rotasyon olan alanlar

---

## 2. GİRİŞ STRATEJİLERİ (5 Yöntem)

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

### 2d. Earnings Momentum (Kazanç İvmesi)
- **Tetik**: Earnings beat > %10, guidance yükseltme
- **Teyitler**: Gap-up + yüksek hacim, sektör desteği
- **Giriş**: Earnings sonrası ilk geri çekilme (gap fill kısmen veya tamamen)
- **UYARI**: Earnings günü girme. minimum 1 gün bekle

### 2e. Sektör Rotasyonu Lideri
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
- **Earnings öncesi kural**: Eğer açık pozisyonda 5 gün içinde earnings varsa, pozisyonun en az %50'sini kapat veya stop'u sıkılaştır
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
