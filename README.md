# 📊 $100K Simulated Portfolio Tracker

> **Başlangıç:** 17 Şubat 2026 | **Sermaye:** $100,000 | **Strateji:** Multi-sector value + momentum

Simüle edilmiş bir yatırım portföyünün günlük takibi. Gerçek piyasa verileri kullanılarak performans ölçülmektedir.

## 📈 Güncel Durum

| Metrik | Değer |
|--------|-------|
| Başlangıç Sermayesi | $100,000 |
| İlk Gün Performansı | -2.60% |
| Aktif Pozisyon | 6 hisse |
| Nakit | $5,130 (%5.1) |

## 🏗️ Portföy Dağılımı

| Hisse | Sektör | Ağırlık | Giriş Fiyatı | Tez |
|-------|--------|---------|--------------|-----|
| **SM** | Energy (E&P) | %22 | $21.14 | Güçlü FCF, değerli enerji |
| **KOS** | Energy (Offshore) | %20 | $1.67 | Deep value, Afrika açık deniz |
| **MO** | Consumer Staples | %18 | $67.29 | Yüksek temettü, defansif |
| **XLE** | Energy ETF | %15 | $54.13 | Geniş enerji sektörü maruziyeti |
| **RGLD** | Gold Royalty | %12 | $277.50 | Düşük riskli altın exposure |
| **FCX** | Copper Mining | %8 | $60.54 | Bakır talebi, EV/altyapı |
| 💵 **Nakit** | — | %5 | — | Fırsat fonu |

## 📁 Proje Yapısı

```
portfolio-tracker/
├── README.md                          # Bu dosya
├── data/
│   ├── portfolio.json                 # Portföy pozisyonları
│   ├── performance_log.csv            # Günlük performans kaydı
│   ├── transactions.csv               # İşlem geçmişi
│   └── latest_snapshot.json           # Son durum snapshot
├── scripts/
│   └── update_portfolio.py            # FMP API ile güncelleme scripti
├── reports/
│   └── report_YYYY-MM-DD.md           # Günlük/haftalık raporlar
├── docs/
│   └── strategy.md                    # Strateji açıklaması
└── .github/
    └── workflows/
        └── daily_update.yml           # Otomatik güncelleme (GitHub Actions)
```

## 🚀 Kullanım

### Manuel Güncelleme
```bash
# Temel güncelleme
python3 scripts/update_portfolio.py --api-key YOUR_FMP_KEY

# Detaylı rapor
python3 scripts/update_portfolio.py --api-key YOUR_FMP_KEY --report --save-report
```

### GitHub Actions (Otomatik)
Repo secrets'a `FMP_API_KEY` eklendikten sonra her iş günü otomatik güncellenir.

## ⚠️ Sorumluluk Reddi

Bu tamamen **simüle edilmiş** bir portföydür. Gerçek para kullanılmamaktadır. Yatırım tavsiyesi değildir. Eğitim ve strateji test amaçlıdır.

---

*FMP (Financial Modeling Prep) API ile güçlendirilmiştir.*
