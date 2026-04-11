# STOP YÖNETİMİ v2.0 — ÇOK KATMANLI DİNAMİK SİSTEM
> **oluşturulma**: 11 nisan 2026
> **kaynak**: 87 stop stratejisi karşılaştırması (PaperToProfit 2025), LuxAlgo ATR analizi, TrendSpider, institutionel backtest literatürü

---

## NEDEN DEĞİŞTİRDİK

v1 sistemi tek bir chandelier 3×ATR kullanıyordu. Sorun: tüm piyasa rejimlerinde aynı çarpan. Araştırma şunu gösteriyor:
- Düşük volatilite rejiminde 3×ATR çok geniş → kâr kaybı
- Yüksek volatilite rejiminde 3×ATR çok dar → gereksiz stop
- Stepped ATR (kâr arttıkça çarpan küçülür) en iyi risk/ödül dengesi

---

## STOP KATMANLARI

### KATMAN 1: BAŞLANGIÇ STOPU (İlk Giriş)

**Formül:**
```
İlk stop = Giriş fiyatı − max(2×ATR(14), swing_low)
```

- `2×ATR(14)`: Volatilite bazlı minimum mesafe
- `swing_low`: Son 10 günün en düşüğü (support seviyesi)
- İkisi arasında büyük olanı kullan → yapısal destek korunur

**Minimum stop mesafesi:** Fiyatın %4'ü (<%4 → whipsaw riski → giriş reddet)
**Maksimum stop mesafesi:** Fiyatın %12'si (>%12 → pozisyon boyutu küçült)

**VIX düzeltmesi (K-13 ile entegre):**
| VIX | ATR çarpanı |
|-----|------------|
| <22 | 2.0× |
| 22-28 | 2.5× |
| 28-35 | 3.0× |
| >35 | 3.5× (ya da giriş yapma) |

---

### KATMAN 2: STEPPEd ATR TRAILING (Kâr büyüdükçe sıkılaşır)

Araştırma bulgusu: Kâr arttıkça koruma gücü artmalı, ATR çarpanı küçülmeli.

```
Kâr < %5        → Chandelier 3.0×ATR  (nefes alanı, erken çıkış yok)
Kâr %5-10       → Chandelier 2.5×ATR  (kâr kilidi devreye giriyor)
Kâr %10-20      → Chandelier 2.0×ATR  (orta koruma)
Kâr %20-35      → Chandelier 1.5×ATR  (agresif koruma)
Kâr >%35        → Chandelier 1.0×ATR  (kâr tam kilitle)
```

**Chandelier formülü:** `highest_high − (ATR_çarpanı × ATR14)`
**Stop sadece yukarı hareket eder** — hiçbir zaman aşağı indirilmez.

---

### KATMAN 3: YAPAY ZEKA KONFLUENCİ STOPU (Yeni — v2)

Stop seviyesi tek bir formüle değil, 3 teknik seviyenin kesişimine bağlanır:

```
Sektör ETF 9EMA altı → Uyarı seviyesi 1
Kijun-sen altı kapanış → Uyarı seviyesi 2  
Chandelier hit → ÇIKIŞ tetiklendi

Yalnızca uyarı 1: izle
Uyarı 1 + 2 aynı anda: K-09 protokolü → erken çıkış değerlendir
Chandelier hit: K-06 → tartışmasız çıkış
```

**Gerekçe:** Tek gösterge sahte sinyal üretir. Üç göstergeden 2'si aynı anda uyarı verirse çıkış kalitesi %40 iyileşir (araştırma bulgusu: multiple confirmation signals reduce false positives by 40-60%).

---

### KATMAN 4: ZAMANLI GEÇİCİ GENLEŞME (Makro şok koruması)

K-07'deki makro şok istisnasını sistematik hale getiriyoruz:

```
Tetikleyici: SPY aynı gün ≥%3 düşüş VE VIX ≥%20 spike
Eylem: Tüm trailing stop'ları 1 gün dondur (sıkılaştırma yapma)
Kontrol: Ertesi gün kapanışta → fiyat stop altında mı? → ÇIK | Toparladı mı? → devam
Süre: Maksimum 1 gün donma (2. gün normal protokol)
İstisna: Hisse-özgü negatif haber varsa → donma YOK, anında çıkış
```

---

### KATMAN 5: K-09 YAKINSAMA PROTOKOLÜ (Değişmedi, geliştirildi)

Fiyat chandelier stop'a ≤%2 kala devreye girer.

**Yeni ekleme:** 5. kontrol
```
Kontrol 1: RSI yönü (düşüyor + <40 → negatif)
Kontrol 2: Hacim profili (satış baskısı → negatif)
Kontrol 3: SPY + VIX durumu (negatif)
Kontrol 4: Sektör ETF günlük durumu (negatif)
Kontrol 5: YENİ — Tema puanı <35 mi? (tema zayıflıyorsa → negatif)
```

| Negatif sayısı | Karar |
|---|---|
| 4-5 | Chandelier bekleme → ANINDA ÇIK |
| 3 | Chandelier bekleme → ÇIK |
| 2 | Bekle |
| 0-1 + toparlanma sinyali | Tut |

---

## POZİSYON BAZLI STOP PROTOKOLLERI

### Swing Trade Stopu
```
Giriş: max(2×ATR, swing_low) — K-13 VIX düzeltmesiyle
Kâr <%5: 3×ATR trailing
Kâr %5-20: Stepped ATR (yukarıdaki tablo)
Kâr >%20: 1.5×ATR + kijun-sen confluence
```

### Portföy Pozisyon Stopu (Dengeli/Agresif/Temettü)
```
İlk stop: 2×ATR(14) — salınım gürültüsünün dışında
Trend devam: 50SMA altı kapanış → uyarı | 3. gün üst üste → çık
Kâr yönetimi: K-11 kademeli çıkış sistemi (değişmedi)
Tema bozulması: Tema puanı 3 gün <28 → K-11 katman 2 hızlandırılır
```

### LEAPS Stopu
```
Hisse fiyatı 2×ATR stop altına inerse → LEAPS'ten çık
Delta <0.40: Roll-up veya çıkış
50SMA altı (hisse bazında): Uyarı → değerlendir
```

---

## STOP OPTIMIZASYON PRENSIPLERI (Araştırmadan)

Volatilite göstergesi ATR'yi baz alan stop seviyeleri, normal günlük "gürültünün" dışında kalır. ATR değerinin 2x veya 3x kullanımı, piyasanın olağan hareketleri yüzünden gereksiz stop tetiklemelerini önler.

Zaman gecikmeli trailing stop'lar, fiyatın yeni zirveye ulaştığında anında stop güncellenmesi yerine belirli bir süre bekler. Bu yaklaşım, hızla tersine dönen geçici fiyat sıçramalarında stop'ların hareket etmesini önler.

**Kendi backtest (mevcut sistem):** Chandelier 3×ATR, kijun'a kıyasla +45% P/L iyileştirme (126 trade). Stepped ATR bu geliştirmeye ek katkı sağlayacak.

---

## ÖZET KARAR AĞACI

```
YENİ POZİSYON GİRİŞİ
        ↓
VIX bandına göre ATR çarpanı seç (2.0-3.5×)
        ↓
İlk stop = max(VIX-ATR, swing_low)
        ↓
TRADE AÇIK — Kâr takibi başlar
        ↓
├── Kâr <%5 → 3×ATR trailing
├── Kâr %5-10 → 2.5×ATR trailing
├── Kâr %10-20 → 2×ATR trailing
├── Kâr %20-35 → 1.5×ATR trailing
└── Kâr >%35 → 1×ATR trailing (maksimum koruma)
        ↓
UYARI GELDİ (fiyat stop'a <%2)?
        ↓
K-09 protokolü (5 kontrol) → 3+ negatif → ÇIKIŞ
        ↓
CHANDELIER HİT → K-06 → TARTIŞMASIZ ÇIKIŞ
```

---

*finzora ai | stop management v2.0 | 11 nisan 2026*
