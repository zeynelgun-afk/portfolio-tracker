# 📊 Zeynel's Portfolio Tracker

4 ayrı portföy + swing trade sistemi için günlük takip reposu.  
Başlangıç: **17 Şubat 2026** | Toplam sermaye: **$400,000**

## Portföyler

| # | Ad | Strateji | Sermaye | Hedef | Durum |
|---|-----|----------|---------|-------|-------|
| 1 | **Dengeli** | Multi-sector value + momentum blend | $100,000 | Stabil büyüme | ✅ Aktif |
| 2 | **Agresif Büyüme** | Momentum, AI/tech, earnings surprise | $100,000 | Yıllık %30+ | ⏳ Pozisyon bekleniyor |
| 3 | **Değer + Temettü** | Düşük P/E, yüksek yield, güçlü FCF | $100,000 | Yıllık %8-12 + temettü | ⏳ Pozisyon bekleniyor |
| 4 | **Sektör Rotasyonu** | Makro döngüye göre sektör ETF rotasyonu | $100,000 | S&P 500 + %5 | ⏳ Pozisyon bekleniyor |

## Swing Trade Sistemi

Ayrı nakit havuzu, günlük tarama:
- RSI oversold pullback
- Earnings surprise / momentum
- Breakout (volume + fiyat)
- Sektör liderliği rotasyonu

## Repo Yapısı

```
portfolio-tracker/
├── data/
│   ├── portfolios/
│   │   ├── balanced.json        # Portföy 1: Dengeli (mevcut)
│   │   ├── aggressive.json      # Portföy 2: Agresif Büyüme
│   │   ├── dividend.json        # Portföy 3: Değer + Temettü
│   │   └── rotation.json        # Portföy 4: Sektör Rotasyonu
│   ├── swing/
│   │   ├── active.json          # Aktif swing pozisyonlar
│   │   ├── watchlist.json       # Günlük tarama sonuçları
│   │   └── closed.json          # Kapatılmış swing trade'ler
│   ├── daily-logs/
│   │   └── YYYY-MM-DD.json      # Günlük tüm portföy snapshot'ları
│   ├── latest_snapshot.json     # Son fiyat snapshot'ı (Dengeli)
│   ├── portfolio.json           # Legacy - Dengeli portföy orijinal
│   ├── performance_log.csv      # Dengeli portföy performans geçmişi
│   └── transactions.csv         # Dengeli portföy işlem geçmişi
├── scripts/
│   └── update_portfolio.py      # FMP API ile fiyat güncelleme
├── reports/
│   └── report_YYYY-MM-DD.md     # Günlük/haftalık raporlar
├── docs/
│   └── strategy.md              # Trading kuralları
├── summary.json                 # Genel özet (4 portföy + swing)
└── README.md
```

## Günlük Rutin

1. **Sabah (piyasa açılmadan)**: Swing tarama, watchlist güncelleme
2. **Piyasa saatlerinde**: Aktif pozisyon takibi, stop-loss kontrol
3. **Kapanış sonrası**: Fiyat güncelleme, günlük log, P&L hesaplama
4. **Pazar günleri**: Haftalık strateji değerlendirmesi

## API
- Financial Modeling Prep (FMP)
