# AGRESİF MOMENTUM STRATEJİSİ — AYLIK %5 HEDEFLİ

> **Oluşturma**: 26 Şubat 2026  
> **Portföy**: Agresif Büyüme ($100K)  
> **Hedef**: Aylık %5 ortalama getiri (yıllık ~%80 bileşik)

---

## 1. STRATEJİ ÖZETİ

Bu strateji, yüksek frekanslı momentum trading ile aylık %5 net getiri hedefler.  
Temel prensip: **küçük ama sık kazançlar > büyük ama nadir kazançlar**

### Matematik
- Aylık hedef: %5 ($5,000 @ $100K sermaye)
- Haftalık hedef: ~%1.2
- Ortalama trade başına hedef: %6-8 kazanç, %3-4 kayıp
- Gerekli aylık başarılı trade: 6-8 (kayıplar dahil net %5)

---

## 2. TEMEL PARAMETRELER

| Parametre | Değer |
|-----------|-------|
| Sermaye | $100,000 |
| Aylık getiri hedefi | %5 ($5,000) |
| Max eşzamanlı pozisyon | 8 |
| Pozisyon büyüklüğü | Sermayenin %10-15 ($10K-$15K) |
| Tipik tutma süresi | 3-10 gün (momentum devam ettiği sürece uzayabilir) |
| Çıkış kriteri | Fiyat aksiyonu bazlı (sabit süre limiti yok) |
| Stop-loss | %4 (sıkı) |
| Kar hedefi | %8-12 (kademeli çıkış) |
| Min R:R oranı | 2:1 |
| Min win rate hedefi | %55 |
| Aylık max drawdown limiti | %8 |

---

## 3. SİNYAL TİPLERİ (3 ANA KATEGORİ)

### 3a. Earnings Momentum (Kazanç İvmesi) — Hedef Hit Rate: %62

**Giriş Koşulları:**
- EPS beat >%15 VE/VEYA revenue beat >%5
- Guidance yükseltme veya olumlu yorum
- Volume earnings günü ortalamanın 2x+
- Giriş: earnings sonrası ilk pullback (1-3 gün)

**Çıkış:**
- Hedef: %8-12 (post-earnings drift yakalama)
- Stop: %4 giriş fiyatından

**FMP Tarama:**
```
earnings-calendar → son 7 gün
analyst-estimates → beat kontrolü
batch-quote → volume + fiyat kontrolü
```

### 3b. Technical Breakout (Kırılım) — Hedef R:R: 3:1

**Giriş Koşulları:**
- 52 hafta high'ın %5 altında, dar range konsolidasyon (>2 hafta)
- Volume breakout günü ortalamanın 1.5x+
- RSI 50-70 aralığında (aşırı alımda DEĞİL)
- SMA20 > SMA50 (trend onayı)

**Çıkış:**
- Hedef: %10-15
- Stop: konsolidasyon low'unun %1 altı (max %4)

**FMP Tarama:**
```
company-screener → volume + price filtre
technical-indicators/rsi → RSI 50-70
technical-indicators/sma → SMA20 > SMA50 kontrol
historical-price-eod/full → range analizi
```

### 3c. Mean Reversion (Ortalamaya Dönüş) — En Hızlı

**Giriş Koşulları:**
- RSI <30 (aşırı satım)
- Hisse SMA200 üzerinde (uzun vadeli trend sağlam)
- Düşüş nedeni: sektör satışı veya genel piyasa korkusu (hisse bazlı sorun DEĞİL)
- Son 5 günde %8+ düşüş

**Çıkış:**
- Hedef: %5-8 (2-4 gün)
- Stop: %3 (çok sıkı, hızlı çık)

**FMP Tarama:**
```
technical-indicators/rsi → RSI <30
technical-indicators/sma → SMA200 üzeri kontrol
stock-price-change → 5 günlük düşüş kontrolü
biggest-losers → aday listesi
```

---

## 4. KADEMELİ ÇIKIŞ SİSTEMİ

```
Pozisyon +%4'te  → stop-loss'u breakeven'a çek (sıfır risk)
Pozisyon +%6'da  → %33 sat, trailing stop %3 aktif
Pozisyon +%10'da → %33 daha sat, trailing stop %4'e genişlet
Kalan %34        → trailing stop ile koştur (max profit)
```

### Momentum Bazlı Çıkış Değerlendirmesi
- Momentum devam ettiği sürece pozisyonu taşı (RSI 40+, SMA50 üzeri, hacim stabil)
- Kademeli çıkış otomatik olarak sermaye verimliliğini sağlar (%66 erken realize)
- Momentum kaybı sinyalleri: RSI düşüşe geçti + hacim azalıyor + SMA50'ye yaklaşıyor → çık
- Sideways giden pozisyonda süre değil fırsat maliyeti değerlendir → daha iyi sinyal varsa rotasyon yap

---

## 5. RİSK YÖNETİMİ KURALLARI (KESİN — İHLAL YOK)

### Günlük Limitler
| Kural | Limit | Aksiyon |
|-------|-------|---------|
| Günlük max kayıp | %2 ($2,000) | O gün yeni trade yok |
| Haftalık max kayıp | %4 ($4,000) | Pozisyon boyutunu %50 küçült |
| Aylık max kayıp | %8 ($8,000) | Stratejiye ARA, tam değerlendirme |

### Korelasyon Limitleri
- Aynı sektörden max 2 pozisyon
- Aynı tema'dan max 3 pozisyon (örn: AI, savunma, enerji)
- Beta >2.0 pozisyonlar toplam portföyün %20'sini geçemez

### Zamanlama Kuralları
- **Earnings öncesi**: Mevcut pozisyon varsa trailing stop ile koru, yeni giriş YOK
- **FOMC/CPI öncesi**: Yeni pozisyon açma, mevcut stop'ları sıkılaştır
- **Cuma 20:00+ (TR)**: Yeni pozisyon açma (hafta sonu gap riski)
- **Pazartesi ilk 30dk**: Gözlem yap, acele etme

### Position Sizing Formülü
```
max_kayıp_usd = sermaye × 0.02 = $2,000 (günlük)
pozisyon_büyüklüğü = max_kayıp_usd / stop_yüzde
Örnek: $2,000 / 0.04 = $50,000 max (ama %15 sermaye limiti = $15,000)
→ Efektif pozisyon: $10,000-$15,000
```

---

## 6. GÜNLÜK TARAMA RUTİNİ

### Piyasa Öncesi (16:00-17:30 TR)
1. **Earnings tarama**: Son 24 saat earnings beat'ler
2. **RSI tarama**: RSI <30 olan kaliteli hisseler
3. **Volume spike**: Olağandışı hacim artışı olanlar
4. **Sektör momentum**: Güçlü sektörleri belirle
5. **Watchlist kontrol**: Mevcut adayların fiyat seviyelerini kontrol

### Seans İçi (17:30-00:00 TR)
1. Açık pozisyonların stop/hedef kontrolü
2. Breakout taraması (real-time volume)
3. Gün içi RSI aşırı satım fırsatları

### Kapanış Sonrası (00:00-01:00 TR)
1. Tüm pozisyonları güncelle
2. After-hours earnings kontrol
3. Ertesi gün planı oluştur

---

## 7. AYLIK PERFORMANS DEĞERLENDİRME

Her ay sonu aşağıdaki metrikler raporlanır:

| Metrik | Hedef |
|--------|-------|
| Net getiri | %5+ |
| Toplam trade sayısı | 10-15 |
| Win rate | %55+ |
| Avg kazanç / Avg kayıp | 2:1+ |
| Max drawdown | <%8 |
| Profit factor | >1.5 |
| Sinyal tipi bazında başarı | Raporla |

### Strateji Ayarlama Tetikleyicileri
- 2 ardışık ay hedef tutturulamazsa → parametre gözden geçir
- Win rate <%45 düşerse → sinyal kalitesini sıkılaştır
- Max drawdown %8'i aşarsa → 1 hafta ara + tam analiz
- Belirli sinyal tipi sürekli başarısızsa → o sinyali devre dışı bırak

---

## 8. MEVCUT PORTFÖY GEÇİŞ PLANI

### Mevcut Durumu (26 Şubat 2026)
- 9 pozisyon aktif, $19.9K nakit
- Toplam değer: ~$93.3K (-%6.68)
- Pozitif P&L pozisyonlar: GILT, BKSY, PLTR, SHOP, ANET, RKLB, CELH, TYL
- Negatif: NNDM

### Geçiş Stratejisi
1. **Hemen**: Tüm pozisyonlara %4 stop-loss ve hedef fiyat ata
2. **Bu hafta**: Zayıf pozisyonları değerlendir (NNDM: -%1.5, zaman ver veya kes)
3. **Gelecek hafta**: Yeni sinyal sistemiyle ilk taramalar
4. **1 ay içinde**: Portföy tamamen yeni stratejiye geçmiş olacak
5. **Takip**: Momentum bazlı çıkış kriterleri uygulanmaya başlayacak (sabit süre limiti yok)

---

## 9. JSON KAYIT FORMATI (Agresif Portföy Ek Alanlar)

Her pozisyona ek olarak:
```json
{
  "sinyal_tipi": "earnings_momentum | breakout | mean_reversion",
  "hedef_fiyat": 140.00,
  "stop_loss": 123.28,
  "trailing_stop": null,
  "max_tutma_gun": 10,
  "partial_exit": {
    "seviye_1": {"fiyat": 134.50, "oran": 33, "durum": "bekliyor"},
    "seviye_2": {"fiyat": 141.25, "oran": 33, "durum": "bekliyor"},
    "seviye_3": {"tur": "trailing", "yuzde": 4, "durum": "bekliyor"}
  }
}
```

---

## 10. ÖNEMLİ UYARILAR

1. Bu strateji YÜK yüksek risk taşır — aylık %5 hedefi agresiftir
2. Disiplin HER ŞEYDEN önemli — stop-loss'a sadık kal
3. FOMO en büyük düşman — sinyal yoksa trade yok
4. Overtrading'den kaçın — kalite > miktar
5. Kayıp günlerinde intikam trade'i yapma
6. Her trade'i kaydet, her dersi not et
7. Piyasa koşulları kötüleşirse (VIX >30) pozisyon boyutunu %50 küçült
