# K-24 VCP Backtest Sonuçları (13 May 2026)

## Veri
- Kaynak: `data/swing/closed.json` — 34 kapanmış swing trade (2026-01-02 → 2026-05-12)
- Yöntem: Her trade'in giriş tarihinden **1 iş günü öncesi** VCP skoru hesaplandı (look-ahead bias yok)
- Script: `scripts/k24_backtest.py`
- Detay: `notes/k24_backtest_results.json`

## Sonuçlar — Özet Tablo

| Grup | N | Ortalama PnL | Medyan | Min | Max | Win% | StdDev |
|---|---|---|---|---|---|---|---|
| **BASELINE** (tüm) | 34 | +0.15% | +1.40% | -11.38% | +12.02% | 55.9% | 5.81 |
| **STRONG** (skor ≥70) | 9 | **+0.45%** | +1.36% | -5.54% | +8.85% | 55.6% | 5.65 |
| **WEAK** (skor 40-69) | 12 | **+1.28%** | +1.55% | -5.10% | +12.02% | 58.3% | 5.36 |
| **NONE** (skor <40) | 13 | **-1.09%** | +1.05% | -11.38% | +11.45% | 53.8% | 6.49 |

## Hipotez Testi

**Hipotez**: VCP ✅ olanlar baseline'a göre +%2+ avantaj sağlar.

- VCP ✅ (STRONG+WEAK, n=21): **+0.92%**
- VCP ❌ (NONE, n=13): **-1.09%**
- **Fark: +2.02%** — eşik tam sınırda geçildi

**Pearson r (skor vs pnl)**: +0.191 — ZAYIF korelasyon

## ❌ KRİTİK SORUN: STRONG-WEAK PARADOKSU

Eğer K-24 gerçek bir kalite filtresi olsaydı, beklenti:
```
STRONG > WEAK > NONE
```

Gerçek sonuç:
```
WEAK (+1.28%) > STRONG (+0.45%) > NONE (-1.09%)
```

**STRONG WEAK'ten daha kötü performans gösteriyor.** Bu hipotez için ciddi bir kırmızı bayrak.

### STRONG grubunun detayı (9 trade):
| Ticker | Skor | PnL | Notlar |
|---|---|---|---|
| AROC | 88 | -4.95% | Stop-loss tetiklendi |
| RTX | 85 | -5.16% | Stop-loss |
| CAT | 81 | +4.26% | ✅ |
| KLAC | 81 | +8.85% | ✅ |
| AMAT | 81 | +1.36% | ✅ |
| GEV | 81 | +7.70% | ✅ |
| DUK | 80 | +1.52% | Zaman doldu |
| TFC | 80 | -3.97% | Stop-loss |
| T | 70 | -5.54% | Stop-loss |

**4 kazançlı / 5 kaybetti** — coin flip'ten beter.

### WEAK grubu başarıları:
- CAT (skor 61): +%12.02 (en yüksek)
- XOM (skor 68): +%5.53
- GOOGL (skor 45): +%7.79

### NONE grubunun aksini gösteren örnekler:
- CAT (skor 38): +%11.45 — VCP olmadan da büyük kazanç
- NEM (skor 30): +%4.18
- NVDA (skor 35): +%2.88

## Olası Açıklamalar

1. **Örneklem küçük**: STRONG sadece 9 trade. İstatistiksel anlamlılık için yetersiz.
2. **STRONG'da Nisan 2026 kümesi**: 6 STRONG trade aynı dönemde (Nis 10-27) açıldı. Aynı makro koşullar, korele sonuçlar.
3. **Pivot kırılmasından sonra hızlı dönüş**: STRONG VCP'ler "pivot yakın" olduğu için kırıldığı anda girildi; ancak pivot kırılışları hâlâ fail edebilir.
4. **Çıkış kuralları VCP'yi nötrleştirebilir**: Sıkı stop-loss'lar düşük volatil VCP setup'larında daha sık tetiklenir (RTX, AROC örnekleri).

## ⚖️ Dürüst Karar

**K-24'ü mevcut hâliyle kalıcı kural yapmamak gerekir.** Hipotez tam sınırda geçti (+2.02% / eşik +2.0%) ama:

✅ **Güçlü bulgu**: VCP ❌ (NONE) grubu negatif beklenti taşıyor (-1.09%, win rate %53.8). "VCP yok ise girme" tek başına bir filtre olabilir.

❌ **Zayıf bulgu**: STRONG/WEAK ayrımı anlamsız. STRONG, WEAK'ten daha kötü.

## Önerilen Revizyonlar

### Seçenek A — Basitleştir (önerilen)
K-24'ü iki seviyeli yap:
- **VCP ✅** (skor ≥40): Normal pozisyon
- **VCP ❌** (skor <40): Giriş YOK

Mantık: Asıl güçlü sinyal "VCP olmamak" — bu negatif ekspekt yaratıyor. Var olduğu sürece STRONG/WEAK ayrımı gürültü.

### Seçenek B — Erteleme
- K-24'ü prototip statüsünde tut, kullanma
- Daha büyük örneklem birikene kadar (50+ trade) bekle
- Q3 2026'da yeniden test et

### Seçenek C — Reddetme
- Bulgular yeterince güçlü değil
- Mevcut Ichimoku 4/4 + K-19/K-20 zinciri zaten iyi çalışıyor (Baseline win rate %55.9)
- K-24 değer katmıyor, kuralları sadeleştir

## Onay Bekleyen
Hangi seçeneği uygulayalım? Şahsi tavsiyem **Seçenek A** — "VCP yok ise girme" basit ve veri destekli; STRONG/WEAK ayrımını şimdilik kullanma. Ama sen karar ver.

## Bilinen Sınırlamalar
- 34 trade istatistik için zayıf örneklem (50+ ideal)
- Aynı sektörde aynı gün açılan korele trade'ler bağımsız değil
- VCP skor eşikleri (40, 70) backtest öncesi keyfi seçildi — overfit riski
- Look-ahead bias kontrolü yapıldı (entry'den 1 gün önce), ama survival bias kontrol edilmedi (closed.json sadece kapanmış trade'leri içerir)
