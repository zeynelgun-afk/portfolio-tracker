# 📊 RAPORLAR

Portfolio tracker için otomatik oluşturulan raporlar.

---

## 📁 KLASÖR YAPISI

### `/daily` - Günlük Raporlar
**Zamanlama:** Her gün Türkiye saati 14:00 (06:00 EST)

**Dosya Formatı:** `GUNLUK_RAPOR_YYYY_MM_DD.md`

**Örnek:** `GUNLUK_RAPOR_2026_02_20.md`

**İçerik:**
- 🌏 Asya borsaları (gece kapanış)
- 📈 ABD pre-market (şu an)
- 💰 Commodities & Forex
- 📰 Gece haberleri (son 24 saat)
  - Portföy pozisyonları (SM, KOS, MO, RGLD, FCX, XLE)
  - Tech giants (AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA)
  - Watchlist (AMD, NET, PANW)
  - Genel piyasa
- 📅 Bugün beklenenler
- 💼 Portföy durumu
- ✅ Bugün yapılacaklar
- 🎯 Stratejik tavsiyeler

**Amaç:** 17:30 TR (09:30 EST) ABD açılışına hazır olmak

---

### `/weekly` - Haftalık Raporlar
**Zamanlama:** Her Pazar 20:00 TR

**Dosya Formatı:** `HAFTALIK_RAPOR_YYYY_WW.md`

**Örnek:** `HAFTALIK_RAPOR_2026_W08.md`

**İçerik:**
- Haftalık performans analizi
- Sektör rotasyonu değerlendirmesi
- Balon risk ölçümü
- Portföy dengeleme önerileri
- Gelecek hafta takvimi

---

### `/monthly` - Aylık Raporlar
**Zamanlama:** Her ay 1. günü

**Dosya Formatı:** `AYLIK_RAPOR_YYYY_MM.md`

**Örnek:** `AYLIK_RAPOR_2026_02.md`

**İçerik:**
- Aylık portföy performansı
- Swing trade özeti
- Stratejik pozisyon değişiklikleri
- Risk/ödül analizi
- Gelecek ay hedefleri

---

## 📌 ARŞİV POLİTİKASI

### Günlük Raporlar:
- Son 30 gün: `reports/daily/`
- 30+ gün: Silinir (gerekirse arşive alınır)

### Haftalık/Aylık:
- Tüm raporlar kalıcı
- Yıl bazlı alt klasörlere taşınabilir

---

## 🔄 OTOMASYON

Raporlar otomatik oluşturulur:

1. **14:00 TR:** Günlük rapor
   - FMP News API
   - FMP Price API
   - Web Search
   - GitHub portfolios

2. **Pazar 20:00 TR:** Haftalık rapor
   - Haftalık analiz
   - Sektör performansı
   - Balon risk

3. **Ay başı:** Aylık rapor
   - Aylık özet
   - Performans değerlendirmesi

---



### Web Search:
- Asya borsaları
- Jeopolitik gelişmeler
- Fed/ECB/BOJ açıklamaları
- Makro veriler

### GitHub Data:
- 4 portföy (Dengeli, Agresif, Değer+Temettü, Sektör Rotasyonu)
- Swing trade pozisyonları
- Performance logs
- Transaction history

---

**Son Güncelleme:** 20 Şubat 2026  
**Versiyon:** 1.0  
**Durum:** 🚀 Production Ready
