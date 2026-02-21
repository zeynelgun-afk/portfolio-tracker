# 📊 Portfolio Tracker - Zeynel'in Yatırım Takip Sistemi

Bu repo Zeynel'in profesyonel portföy yönetimi ve swing trade simülasyonunu takip eder.

## 🎯 Sistem Yapısı

### 4 Ana Portföy ($400K Toplam - Başlangıç: 17 Şubat 2026)

#### 1. Dengeli Portföy ($100K)
- **Dosya:** `data/portfolios/balanced.json`
- **Ruh:** Dengeli, risk/ödül balanced, çeşitlendirilmiş
- **Strateji:** **SADECE HİSSE** - Multi-sector value + momentum blend
- **Alım Kuralları:**
  - ✅ Çeşitli sektörlerden hisseler
  - ✅ Değer + Büyüme karışımı
  - ✅ Temettü ödemeyenler de olabilir
  - ❌ Long yönlü ETF YASAK
  - ✅ Hedge için satış yönlü ETF (SQQQ, SPXU, SH)
- **Aktif:** SM, KOS, MO, RGLD, FCX
- **Hedef:** Yıllık %60+ getiri
- **Risk:** Max 7 pozisyon, %8 stop-loss
- **Orijinal veriler:** `data/portfolio.json`, `performance_log.csv`, `transactions.csv`

#### 2. Agresif Büyüme ($100K)
- **Dosya:** `data/portfolios/aggressive.json`
- **Ruh:** Büyüme hisseleri, momentum, yüksek risk/yüksek ödül
- **Strateji:** **SADECE BÜYÜME HİSSELERİ** - Momentum + earnings surprise, AI/tech ağırlıklı
- **Alım Kuralları:**
  - ✅ Momentum hisseleri (50MA üzeri, RS yükseliş)
  - ✅ Earnings surprise (>%10)
  - ✅ AI, tech, innovation odaklı
  - ❌ Long yönlü ETF, değer hisseleri, defensive hisseler YASAK
  - ✅ Hedge için satış yönlü ETF
- **Aktif:** NVDA, META, GOOGL, AVGO
- **Hedef:** Yıllık %100+ getiri
- **Risk:** Max 8 pozisyon, %8 stop-loss

#### 3. Değer + Temettü ($100K)
- **Dosya:** `data/portfolios/dividend.json`
- **Ruh:** Değer hisseleri, yüksek temettü, istikrar
- **Strateji:** **SADECE DEĞER/TEMETTÜ HİSSELERİ** - Düşük P/E, yüksek temettü, güçlü FCF
- **Alım Kuralları:**
  - ✅ P/E < 20, temettü yield > %3, güçlü FCF, D/E < 1.5
  - ✅ **İSTİSNA:** Temettü ETF'leri İZİN VERİLİR (SCHD, VYM, DVY)
  - ❌ Sektör ETF'leri, büyüme hisseleri YASAK
  - ✅ Hedge için satış yönlü ETF
- **Aktif:** SCHD, XOM, VZ, CVX, MO, T, PM
- **Hedef:** Yıllık %35+ getiri + temettü
- **Risk:** Max 10 pozisyon

#### 4. Sektör Rotasyonu ($100K)
- **Dosya:** `data/portfolios/rotation.json`
- **Ruh:** Sektör ETF'leriyle makro döngü takibi
- **Strateji:** **SADECE SEKTÖR ETF'LERİ** - Makro döngüye göre rotasyon
- **Alım Kuralları:**
  - ✅ SADECE sektör ETF'leri (XLE, XLF, XLK, XLV, XLI, XLP, XLU, XLY, XLB, XLRE, XLC)
  - ✅ Çeyreklik rebalance
  - ❌ Bireysel hisseler, kaldıraçlı ETF'ler YASAK
  - ✅ Hedge için satış yönlü ETF
- **Aktif:** XLE, XLI, XLV
- **Hedef:** S&P 500'ü yıllık %20+ geçmek
- **Risk:** Max 8 pozisyon

### 🛡️ Hedge Kuralları (Tüm Portföyler)

**İzin Verilen Satış Yönlü ETF'ler:**
- SQQQ (Nasdaq 3x Short)
- SPXU (S&P 500 3x Short)
- SH (S&P 500 Short)
- PSQ (Nasdaq Short)
- QID (Nasdaq 2x Short)
- TZA (Russell 2000 3x Short)

**Kullanım:** Piyasa düşüş beklentisinde portföy hedge'i için, kısa vadeli (max 2 hafta)

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
├── reports/
│   ├── daily/               # Günlük raporlar (Pzt-Cmt)
│   │   └── DAILY_REPORT_YYYY-MM-DD.md
│   └── weekly/              # Haftalık raporlar (Pazar)
│       └── WEEKLY_REPORT_YYYY-MM-DD.md
├── PORTFOY_KURALLARI.md     # Portföy yönetim kuralları
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

### Piyasa Öncesi (09:00-09:30):
- Swing tarama → watchlist güncelle
- Portföy kurallarına uygunluk kontrolü
- Gece haberleri ve makro takip

### Piyasa Saatleri (09:30-16:00):
- Stop-loss kontrol
- Fırsat takibi (portföy ruhuna uygun)
- Pozisyon yönetimi

### 🕑 **Saat 14:00 - Günlük Rapor (ZORUNLU)**
- **Dosya:** `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
- **İçerik:**
  - Günün piyasa özeti
  - Portföy performansları (4 portföy)
  - Açılan/kapatılan pozisyonlar
  - Önemli haberler ve katalizörler
  - Yarına dönük plan
- **Not:** Hafta sonu cumartesi günleri haber odaklı rapor yazılır

### Kapanış Sonrası (16:00-17:00):
- Fiyat güncelle
- Günlük log yaz
- Summary güncelle
- Git commit + push

### Haftalık (Pazar):
- **Dosya:** `reports/weekly/WEEKLY_REPORT_YYYY-MM-DD.md`
- Strateji değerlendirmesi
- Sektör rotasyonu analizi
- Balon riski kontrol
- Portföy dengeleme (kurallara uygun)
- İzleme listesi güncelleme
- Haftalık performans özeti

## 📊 API & Araçlar

- **FMP API:** Financial Modeling Prep
- **API Key:** `g1GFJZtV5rCP49UCir4WuP56VjhmA6F8`
- **GitHub:** https://github.com/zeynelgun-afk/portfolio-tracker
- **Token:** `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`

## 🎓 Genel Kurallar

1. ✅ **PORTFÖY RUHUNA SADAKAT** - Tüm işlemler portföy kurallarına uygun yapılmalıdır
2. ✅ Somut, veriye dayalı öneriler
3. ✅ Her öneride risk/ödül oranı belirt
4. ✅ Portföy değişikliklerinde korelasyon kontrol
5. ✅ Büyük kararları adımlara böl
6. ✅ Her değişiklikte Git commit + push
7. ✅ **Saat 14:00'de günlük rapor yaz (reports/daily/)**

## 📋 Portföy Özet Tablosu

| Portföy | Long İzin | ETF İzin | Hedge İzin | Max Pozisyon | Hedef Getiri |
|---------|-----------|----------|------------|--------------|--------------|
| Dengeli | Hisse | ❌ | Short ETF ✅ | 7 | %60+ |
| Agresif Büyüme | Büyüme Hisse | ❌ | Short ETF ✅ | 8 | %100+ |
| Değer + Temettü | Değer/Temettü Hisse | Sadece Temettü ETF ✅ | Short ETF ✅ | 10 | %35+ |
| Sektör Rotasyonu | ❌ | Sektör ETF ✅ | Short ETF ✅ | 8 | S&P+20% |

## 📈 Performans Takibi

Tüm performans metrikleri `data/summary.json` dosyasında takip edilir.

## 📝 Rapor Sistemi

### Günlük Raporlar (Pazartesi-Cumartesi)
- **Klasör:** `reports/daily/`
- **Format:** `DAILY_REPORT_YYYY-MM-DD.md`
- **Zaman:** Her gün saat 14:00
- **Hafta Sonu:** Cumartesi günleri haber odaklı rapor

### Haftalık Raporlar (Pazar)
- **Klasör:** `reports/weekly/`
- **Format:** `WEEKLY_REPORT_YYYY-MM-DD.md`
- **İçerik:** Haftalık performans, strateji değerlendirmesi, önümüzdeki hafta planı

## ⚠️ Geçiş Dönemi Notu

Mevcut ETF pozisyonları (Dengeli ve Agresif'teki XLE, XLI) tutulabilir, ancak:
- ✅ Yeni alımlarda KURALLARA UYULMALIDIR
- ✅ ETF'ler satılırsa, yerine KURAL UYGUN pozisyonlar alınmalıdır
- ✅ Rebalance'da kurallara uygun pozisyonlara geçilmelidir

***

**Kurallar Güncelleme:** 19 Şubat 2026  
**README Güncelleme:** 21 Şubat 2026  
**Dil:** Türkçe

***
