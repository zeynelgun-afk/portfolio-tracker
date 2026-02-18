# 📊 $100K Manual Portfolio Tracker

> **Başlangıç:** 17 Şubat 2026 | **Sermaye:** $100,000 | **Strateji:** Manuel portföy takibi - value & energy focus

Gerçek piyasa verileri kullanılarak manuel olarak yönetilen yatırım portföyünün takibi.

## 📈 Güncel Durum

| Metrik | Değer |
|--------|-------|
| Başlangıç Sermayesi | $100,000 |
| Güncel Değer | ~$101,700 |
| Net Kar | +$1,700 (+1.70%) |
| Aktif Pozisyon | 6 hisse |
| Nakit | $5,424 |
| Son Güncelleme | 18 Şubat 2026 |

## 🏗️ Portföy Dağılımı

| Hisse | Sektör | Adet | Maliyet | Notlar |
|-------|--------|------|---------|--------|
| **SM** | Energy (E&P) | 1,040 | $20.67 | 25 Şubat earnings öncesi sat |
| **KOS** | Energy (Offshore) | 15,276 | $1.617 | DCA ile büyütüldü |
| **MO** | Consumer Staples | 267 | $67.44 | Yüksek temettü, defansif |
| **XLE** | Energy ETF | 277 | $53.34 | Geniş enerji sektörü |
| **RGLD** | Gold Royalty | 22 | $274.40 | Earnings öncesi sat (21 adet satıldı) |
| **FCX** | Copper Mining | 132 | $59.53 | Bakır talebi, EV/altyapı |
| 💵 **Nakit** | — | — | — | Fırsat fonu |

## 📁 Proje Yapısı

```
portfolio-tracker/
├── README.md                          # Bu dosya
├── data/
│   ├── portfolio.json                 # Portföy pozisyonları (manuel güncellenir)
│   └── latest_snapshot.json           # Son durum snapshot
├── scripts/
│   └── update_portfolio.py            # FMP API ile güncel değer hesaplama
├── reports/
│   └── report_YYYY-MM-DD.md           # Günlük/haftalık raporlar
└── .github/
    └── workflows/
        └── daily_update.yml           # Otomatik değer güncelleme (opsiyonel)
```

## 🔄 İşlem Geçmişi

| Tarih | İşlem | Hisse | Adet | Fiyat | Tutar |
|-------|-------|-------|------|-------|-------|
| 2026-02-17 | AL | SM | 1,040 | $20.67 | $21,496.80 |
| 2026-02-17 | AL | KOS | 11,976 | $1.59 | $19,041.84 |
| 2026-02-17 | AL | MO | 267 | $67.44 | $18,006.48 |
| 2026-02-17 | AL | XLE | 277 | $53.34 | $14,775.18 |
| 2026-02-17 | AL | RGLD | 43 | $274.40 | $11,799.20 |
| 2026-02-17 | AL | FCX | 132 | $59.53 | $7,857.96 |
| 2026-02-18 | SAT | RGLD | 21 | $283.56 | $5,954.76 (+3.34%) |
| 2026-02-18 | AL | KOS | 3,300 | $1.715 | $5,659.50 (DCA) |

## 📋 Bekleyen İşlemler

- **19 Şubat:** RGLD kalan 22 hisse sat
- **22-23 Şubat:** SM 1,040 hisse sat (earnings öncesi)

## 🚀 Kullanım

### Manuel Güncelleme
```bash
# Portföy değerini güncelle
python3 scripts/update_portfolio.py --api-key YOUR_FMP_KEY --report
```

### GitHub Actions (Opsiyonel)
Repo secrets'a `FMP_API_KEY` eklendikten sonra her iş günü otomatik güncellenir.

## ⚠️ Sorumluluk Reddi

Bu tamamen **simüle edilmiş** bir portföydür. Gerçek para kullanılmamaktadır. Yatırım tavsiyesi değildir. Eğitim ve strateji test amaçlıdır.

---

*FMP (Financial Modeling Prep) API ile güçlendirilmiştir.*
