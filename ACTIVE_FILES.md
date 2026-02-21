# ✅ AKTİF KULLANILAN DOSYALAR

> **Repo:** https://github.com/zeynelgun-afk/portfolio-tracker  
> **Güncelleme:** 21 Şubat 2026  
> **Toplam Aktif Dosya:** 20

---

## 📂 KÖK DİZİN

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `README.md` | Repo ana dokümantasyonu, kullanım kılavuzu |
| `PORTFOY_KURALLARI.md` | Portföy yönetim kuralları, risk limitleri, stratejik ilkeler |

---

## 📂 data/ — VERİ KLASÖRÜ

### Ana Veri Dosyaları

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `summary.json` | **4 portföyün toplu özeti** - toplam değer, kar/zarar, performans karşılaştırması |
| `transactions.csv` | **TÜM alış/satış işlemleri** - CSV format, tarih/sembol/fiyat/tutar/neden |

### 📁 data/portfolios/ — PORTFÖY JSON'LARI

| Dosya | Sermaye | Ne İşe Yarar |
|-------|---------|--------------|
| `balanced.json` | $100K | **Dengeli Portföy** - Multi-sector value + momentum, SM/KOS/MO/XLE/RGLD/FCX |
| `aggressive.json` | $100K | **Agresif Büyüme** - Micro-cap AI disruption, GILT/BKSY, yarım pozisyon stratejisi |
| `dividend.json` | $100K | **Değer + Temettü** - Düşük P/E, yüksek temettü yield, savunmacı pozisyonlar |
| `rotation.json` | $100K | **Sektör Rotasyonu** - Makro döngüye göre sektör ETF rotasyonu |

**Her portföy JSON içerir:**
- `pozisyonlar[]` - Açık pozisyonlar (sembol, adet, maliyet, güncel fiyat, kar/zarar)
- `nakit` - Kullanılabilir nakit
- `transactions[]` - Bu portföye özel işlemler
- `notes[]` - Portföy notları ve kararlar

### 📁 data/swing/ — SWING TRADE

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `active.json` | **Açık swing pozisyonları** - Max 10 pozisyon, giriş/hedef/stop, tutulan gün, kar/zarar tracking |
| `closed.json` | **Kapanmış trade'ler** - Geçmiş performans, kazanç/zarar oranları, tutulan gün istatistikleri, çıkarılan dersler |
| `watchlist.json` | **İzleme listesi** - Günlük tarama sonuçları, potansiyel swing adayları, urgency seviyeleri |
| `README.md` | Swing trade kuralları - %5 stop, %10 target, max 15 gün, tarama yöntemleri |
| `TECH_RECOVERY_PLAYBOOK.md` | Tech düzeltme stratejisi - Nasıl ve ne zaman giriş yapılır |
| `AI_DISRUPTION_REHBERI.md` | AI disruption fırsatları - Hangi sektörler/şirketler risk altında |
| `DERSLER_SABLON.md` | Trade kapanışında kullanılan ders şablonu |

### 📁 data/logs/ — TRADE LOGLARI

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `2026-02-10-18-FINAL.md` | **Final özet** - 10-18 Şubat dönemi trade özeti ve dersler |

---

## 📂 docs/ — DOKÜMANTASYON

### 🔴 Kritik Dokümantasyon

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `PORTFOLIO_DATA_SKILL.md` | **EN ÖNEMLİ** - JSON şema kuralları, zorunlu alanlar, hesaplama formülleri, her güncelleme öncesi kontrol edilmeli |

### Strateji Dokümantasyonu

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `strategy.md` | Genel portföy stratejisi - 4 portföy yaklaşımı, hedefler, risk yönetimi |
| `SWING_TRADE_RULES.md` | Swing trade kuralları - Sayısal limitler, stop/target kuralları, max pozisyon |
| `AGGRESSIVE_MICRO_CAP_STRATEGY.md` | Agresif portföy micro-cap stratejisi - LPTH-tarzı yaklaşım, yarım pozisyon kuralları |
| `BALANCED_PORTFOLIO_TECHNICAL_ANALYSIS.md` | Dengeli portföy teknik analiz notları |
| `TECHNICAL_ANALYSIS_MICRO_CAPS.md` | Micro-cap teknik analiz rehberi - Volume, momentum, risk analizi |
| `ENTRY_TIMING_DECISION.md` | Giriş zamanlaması kararları - Ne zaman bekle, ne zaman gir |

### Teknik Dokümantasyon

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `DOSYA_SISTEMI.md` | Repo dosya yapısı açıklaması |
| `FMP_API_LESSONS_LEARNED.md` | FMP API endpoint çözümlemeleri - Hangi endpoint'ler çalışıyor/çalışmıyor |

---

## 📂 reports/ — RAPORLAR

### 📁 reports/daily/ — GÜNLÜK RAPORLAR

| Format | Ne İşe Yarar |
|--------|--------------|
| `DAILY_REPORT_2026-02-20.md` | **Perşembe** - Piyasa kapanışı, portföy performansı, önemli haberler |
| `DAILY_REPORT_2026-02-21.md` | **Cumartesi** - Haber odaklı (tarife, jeopolitik, sektör), hafta sonu derinlemesine analiz |

**Format:** `DAILY_REPORT_YYYY-MM-DD.md`  
**Sıklık:** Pazartesi-Cumartesi (her gün)  
**Cumartesi özel:** Haber ağırlıklı, Supreme Court kararları, jeopolitik gelişmeler, sektör analizleri

### 📁 reports/weekly/ — HAFTALIK RAPORLAR

| Format | Ne İşe Yarar |
|--------|--------------|
| `WEEKLY_REPORT_YYYY-MM-DD.md` | **Pazar** - Haftalık özet, sektör rotasyonu değerlendirmesi, balon riski analizi, önümüzdeki hafta stratejisi |

**Format:** `WEEKLY_REPORT_YYYY-MM-DD.md`  
**Sıklık:** Sadece Pazar günleri

### 📁 reports/monthly/ — AYLIK RAPORLAR

| Format | Ne İşe Yarar |
|--------|--------------|
| `MONTHLY_*.md` | Aylık performans özeti (henüz başlamadı) |

### Diğer

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `README.md` | Rapor sistemi açıklaması - Günlük/haftalık/aylık rapor formatları |

---

## 📂 scripts/ — OTOMASYON

| Dosya | Ne İşe Yarar |
|-------|--------------|
| `update_portfolio.py` | **Tek portföy güncelleme** - Belirtilen portföyün fiyatlarını FMP API'den çekip günceller |
| `update_all_portfolios.py` | **Toplu güncelleme** - 4 portföyü + swing trade'leri bir komutla günceller |
| `README.md` | Script kullanım kılavuzu - Nasıl çalıştırılır, parametreler |

---

## 📋 GÜNLÜK KULLANIM AKIŞI

### 🔴 Her Gün (Piyasa Kapanışı Sonrası)

```
1. scripts/update_all_portfolios.py çalıştır
   → data/portfolios/*.json güncellenir
   → data/summary.json güncellenir
   → data/swing/active.json güncellenir

2. reports/daily/DAILY_REPORT_YYYY-MM-DD.md oluştur
   → Portföy performansı
   → Önemli haberler
   → Swing trade durumu
   
3. GitHub'a push
   → git commit -m "Günlük güncelleme: YYYY-MM-DD"
```

### 🟡 Pozisyon Açılışında

```
1. docs/PORTFOLIO_DATA_SKILL.md kontrol et
   → Zorunlu alanları gör
   
2. data/portfolios/[portföy].json güncelle
   → pozisyonlar[] dizisine ekle
   → nakit.miktar düşür
   → transactions[] ekle
   
3. data/transactions.csv güncelle
   → BUY satırı ekle
   
4. GitHub'a push
   → git commit -m "[ALIŞ] Portföy - SEMBOL @Fiyat"
```

### 🟢 Haftalık (Pazar)

```
1. reports/weekly/WEEKLY_REPORT_YYYY-MM-DD.md oluştur
   → Haftalık performans
   → Sektör rotasyonu değerlendirmesi
   → Önümüzdeki hafta stratejisi
   
2. data/swing/watchlist.json güncelle
   → Haftalık tarama sonuçları
```

---

## 🎯 KULLANIM PRİORİTESİ

### 🔴 HER GÜN KULLANILAN (Kritik)
1. ✅ `data/portfolios/*.json` - Fiyat güncellemeleri
2. ✅ `data/transactions.csv` - İşlem kayıtları  
3. ✅ `data/summary.json` - Toplu özet
4. ✅ `reports/daily/DAILY_REPORT_*.md` - Günlük rapor

### 🟡 HAFTALIK KULLANILAN
1. ✅ `data/swing/watchlist.json` - Tarama sonuçları
2. ✅ `reports/weekly/WEEKLY_REPORT_*.md` - Pazar raporu
3. ✅ `data/swing/active.json` - Swing tracking

### 🟢 REFERANS (Gerektiğinde)
1. ✅ `docs/PORTFOLIO_DATA_SKILL.md` - Her değişiklik öncesi kontrol
2. ✅ `docs/SWING_TRADE_RULES.md` - Her swing trade öncesi
3. ✅ `docs/strategy.md` - Strateji kararlarında
4. ✅ `docs/AGGRESSIVE_MICRO_CAP_STRATEGY.md` - Agresif portföy işlemlerinde

### ⚪ ARAÇ (Nadiren)
1. ✅ `scripts/update_all_portfolios.py` - Otomasyon
2. ✅ `docs/FMP_API_LESSONS_LEARNED.md` - API sorunlarında

---

## 📊 DOSYA İSTATİSTİKLERİ

| Kategori | Dosya Sayısı | Kullanım Sıklığı |
|----------|--------------|------------------|
| **Portföy JSON'ları** | 4 | Her gün |
| **Swing Trade** | 7 | Her gün + haftalık |
| **Raporlar** | 4 | Her gün + haftalık |
| **Dokümantasyon** | 8 | Referans |
| **Scriptler** | 3 | Otomasyon |
| **TOPLAM AKTİF** | **26** | - |

---

**Son Güncelleme:** 21 Şubat 2026  
**Durum:** ✅ Aktif kullanımda  
**Sonraki Revizyon:** Mart 2026
