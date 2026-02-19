# 📊 Portfolio Tracker - Zeynel'in Yatırım Takip Sistemi

Bu repo Zeynel'in profesyonel portföy yönetimi ve swing trade simülasyonunu takip eder.

## 🎯 Sistem Yapısı

### 4 Ana Portföy ($400K Toplam - Başlangıç: 17 Şubat 2026)

#### 1. Dengeli Portföy ($100K)
- **Dosya:** `data/portfolios/balanced.json`
- **Strateji:** Multi-sector value + momentum blend
- **Aktif:** SM, KOS, MO, XLE, RGLD, FCX
- **Orijinal veriler:** `data/portfolio.json`, `performance_log.csv`, `transactions.csv`

#### 2. Agresif Büyüme ($100K)
- **Dosya:** `data/portfolios/aggressive.json`
- **Strateji:** Momentum + earnings surprise, AI/tech ağırlıklı
- **Hedef:** Yıllık %30+
- **Risk:** Max 10 pozisyon, %8 stop-loss

#### 3. Değer + Temettü ($100K)
- **Dosya:** `data/portfolios/dividend.json`
- **Strateji:** Düşük P/E (<20), temettü yield >%3, güçlü FCF
- **Hedef:** Yıllık %8-12 + temettü
- **Risk:** Max 15 pozisyon, D/E < 1.5

#### 4. Sektör Rotasyonu ($100K)
- **Dosya:** `data/portfolios/rotation.json`
- **Strateji:** Makro döngüye göre sektör ETF rotasyonu
- **Hedef:** S&P 500'ü yıllık %5+ geçmek
- **Evren:** XLE, XLF, XLK, XLV, XLI, XLP, XLU, XLY, XLB, XLRE, XLC

### Swing Trade Sistemi
- **Klasör:** `data/swing/`
- **Max Pozisyon:** 10 eşzamanlı
- **Position Size:** $5K-10K per trade
- **Kurallar:** %10 target, %5 stop, 7-10 gün hedef
- **Yöntemler:** RSI oversold, earnings momentum, breakout, sektör liderliği

## 📁 Klasör Yapısı

```
portfolio-tracker/
├── data/
│   ├── portfolios/          # 4 ana portföy
│   │   ├── balanced.json
│   │   ├── aggressive.json
│   │   ├── dividend.json
│   │   └── rotation.json
│   ├── swing/               # Swing trade sistem
│   │   ├── active.json      # Açık pozisyonlar
│   │   ├── closed.json      # Kapatılmış trade'ler
│   │   ├── watchlist.json   # İzleme listesi
│   │   ├── OZET_*.md        # Özet raporlar
│   │   └── README.md        # Swing sistem dökümantasyonu
│   ├── logs/                # Günlük loglar
│   └── summary.json         # Genel özet
└── README.md                # Bu dosya
```

## 🎯 Veri Kayıt Kuralları

### Her Pozisyon Açıldığında ZORUNLU:
- `giris_tarihi`, `giris_fiyati`, `adet`
- `giris_nedeni`: Neden alındı (detaylı tez)
- `katalizor`: Tetikleyici olay
- `hedef_fiyat`, `stop_loss`

### Her Pozisyon Kapatıldığında ZORUNLU:
- `cikis_tarihi`, `cikis_fiyati`
- `cikis_nedeni`: Neden satıldı
- `kar_zarar`, `kar_zarar_yuzde`, `tutulan_gun`
- `dersler`: Bu trade'den çıkarılan dersler

## 🔄 Günlük Rutin

### Piyasa Öncesi:
- Swing tarama → watchlist güncelle

### Piyasa Saatleri:
- Stop-loss kontrol
- Fırsat takibi

### Kapanış Sonrası:
- Fiyat güncelle
- Günlük log yaz
- Summary güncelle
- Git commit + push

### Haftalık (Pazar):
- Strateji değerlendirmesi
- Sektör rotasyonu analizi
- Balon riski kontrol
- Portföy dengeleme
- İzleme listesi güncelleme

## 📊 API & Araçlar

- **FMP API:** Financial Modeling Prep
- **API Key:** `g1GFJZtV5rCP49UCir4WuP56VjhmA6F8`
- **GitHub:** https://github.com/zeynelgun-afk/portfolio-tracker
- **Token:** `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`

## 🎓 Genel Kurallar

1. ✅ Somut, veriye dayalı öneriler
2. ✅ Her öneride risk/ödül oranı belirt
3. ✅ Portföy değişikliklerinde korelasyon kontrol
4. ✅ Büyük kararları adımlara böl
5. ✅ Her değişiklikte Git commit + push

## 📈 Performans Takibi

Tüm performans metrikleri `data/summary.json` dosyasında takip edilir.

---

**Başlangıç:** 17 Şubat 2026  
**Son Güncelleme:** 18 Şubat 2026  
**Dil:** Türkçe
