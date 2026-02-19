# 📂 PORTFOLIO TRACKER - DOSYA SİSTEMİ DOKÜMANTASYONU

**Son Güncelleme:** 19 Şubat 2026  
**Versiyon:** 2.0  
**Durum:** Tam Türkçe

---

## 🗂️ KLASÖR YAPISI

```
portfolio-tracker/
├── data/                          # Tüm veri dosyaları
│   ├── portfolios/               # 4 ana portföy
│   │   ├── balanced.json         # Dengeli Portföy
│   │   ├── aggressive.json       # Agresif Büyüme
│   │   ├── dividend.json         # Değer + Temettü
│   │   └── rotation.json         # Sektör Rotasyonu
│   │
│   ├── swing/                    # Swing trade sistemi
│   │   ├── active.json           # Aktif pozisyonlar
│   │   ├── closed.json           # Kapatılmış trade'ler
│   │   ├── watchlist.json        # İzleme listesi
│   │   ├── OZET_*.md            # Periyodik özet raporlar
│   │   ├── DERSLER_SABLON.md    # Ders çıkarma şablonu
│   │   └── README.md            # Swing sistem dökümantasyonu
│   │
│   ├── logs/                     # Günlük loglar
│   │   └── *.md                 # Tarih bazlı log dosyaları
│   │
│   ├── portfolio.json            # ESKİ tek portföy (legacy)
│   ├── portfolio_summary.json    # Güncel 4 portföy özeti
│   ├── summary.json              # Genel özet
│   ├── latest_snapshot.json      # Son anlık görüntü
│   ├── transactions.csv          # İşlem geçmişi
│   └── performance_log.csv       # Performans logu
│
├── scripts/                      # Otomasyon scriptleri
│   ├── update_all_portfolios.py # Ana güncelleme scripti
│   ├── update_portfolio.py       # ESKİ script (legacy)
│   └── README.md                # Script dökümantasyonu
│
├── docs/                         # Dokümantasyon
│   ├── DOSYA_SISTEMI.md         # Bu dosya
│   └── strategy.md              # Strateji dokümantasyonu
│
├── reports/                      # Oluşturulan raporlar
│   └── report_*.md              # Tarihli raporlar
│
└── README.md                     # Ana README
```

---

## 📊 4 PORTFÖY SİSTEMİ

### 📁 `data/portfolios/`

Her portföy ayrı bir JSON dosyasında tutulur.

#### **Portföy Dosya Yapısı:**

```json
{
  "portfoy_adi": "Dengeli Portföy",
  "baslangic_sermaye": 100000,
  "nakit": {
    "miktar": 5424.50,
    "para_birimi": "USD"
  },
  "pozisyonlar": [
    {
      "sembol": "SM",
      "isim": "SM Energy Company",
      "sektor": "Enerji",
      "giris_tarihi": "2026-02-17",
      "giris_fiyati": 21.14,
      "giris_nedeni": "Initial position - Oil & gas E&P",
      "adet": 1040,
      "maliyet_baz": 20.67,
      "guncel_fiyat": 23.40,
      "yatirim": 21496.80,
      "guncel_deger": 24336.00,
      "kar_zarar": 2839.20,
      "kar_zarar_yuzde": 13.21,
      "gunluk_degisim_yuzde": 7.93,
      "son_guncelleme": "2026-02-19T12:21:07",
      "agirlik_yuzde": 23.61
    }
  ],
  "son_guncelleme": "2026-02-19T12:21:07",
  "toplam_deger": 103096.25,
  "toplam_getiri_yuzde": 3.10
}
```

#### **Pozisyon Alanları:**

| Alan | Tip | Açıklama |
|------|-----|----------|
| `sembol` | string | Ticker symbol (AAPL, GOOGL) |
| `isim` | string | Şirket adı |
| `sektor` | string | Sektör (TÜRKÇE) |
| `giris_tarihi` | string | Ne zaman alındı (YYYY-MM-DD) |
| `giris_fiyati` | number | Kaç dolardan alındı |
| `giris_nedeni` | string | Neden alındı (tez) |
| `adet` | number | Kaç hisse |
| `maliyet_baz` | number | Ortalama maliyet |
| `guncel_fiyat` | number | Şu anki fiyat |
| `yatirim` | number | Toplam yatırım (adet × maliyet) |
| `guncel_deger` | number | Şu anki değer (adet × fiyat) |
| `kar_zarar` | number | Dolar bazında K/Z |
| `kar_zarar_yuzde` | number | Yüzde bazında K/Z |
| `gunluk_degisim_yuzde` | number | Bugünkü değişim % |
| `son_guncelleme` | string | Son güncelleme zamanı |
| `agirlik_yuzde` | number | Portföy içinde ağırlık % |

#### **4 Portföy:**

| Dosya | Portföy | Başlangıç | Strateji |
|-------|---------|-----------|----------|
| `balanced.json` | Dengeli | $100K | Multi-sector value + momentum |
| `aggressive.json` | Agresif Büyüme | $100K | Tech/AI ağırlıklı momentum |
| `dividend.json` | Değer + Temettü | $100K | Yüksek temettü + değer |
| `rotation.json` | Sektör Rotasyonu | $100K | Sektör ETF rotasyonu |

**TOPLAM:** $400K başlangıç sermayesi

---

## 🎯 SWING TRADE SİSTEMİ

### 📁 `data/swing/`

Kısa vadeli (7-10 gün) trade'ler için sistem.

#### **1. active.json - Aktif Pozisyonlar**

```json
{
  "son_guncelleme": "2026-02-19T12:24:32Z",
  "not": "SWING TRADE SADECE SİMÜLASYON",
  "aktif_pozisyonlar": [
    {
      "id": "SWING-010",
      "sembol": "NEM",
      "giris_tarihi": "2026-02-12",
      "giris_fiyati": 118.12,
      "guncel_fiyat": 124.69,
      "guncel_kar_zarar_yuzde": 5.56,
      "hedef_fiyat": 129.93,
      "stop_loss": 118.12,
      "tutulan_gun": 6,
      "giris_nedeni": "Güçlü momentum +8.8%",
      "katalizor": "Altın fiyat gücü",
      "tez": "Dünyanın en büyük altın üreticisi",
      "zaman_cercevesi": "7-10 gün",
      "risk": "Altın fiyat dönüşü",
      "durum": "Trailing stop aktif"
    }
  ],
  "ozet": {
    "toplam_pozisyon": 7,
    "bos_slot": 3,
    "maksimum_pozisyon": 10,
    "ortalama_kar_zarar_yuzde": -0.30
  }
}
```

**Maksimum:** 10 eşzamanlı pozisyon  
**Otomatik Kontrol:** Stop-loss, target, timeframe

#### **2. closed.json - Kapatılmış Trade'ler**

```json
{
  "son_guncelleme": "2026-02-18",
  "kapatilan_pozisyonlar": [
    {
      "id": "SWING-007",
      "sembol": "CAT",
      "giris_tarihi": "2026-02-04",
      "cikis_tarihi": "2026-02-11",
      "giris_fiyati": 691.82,
      "cikis_fiyati": 775.00,
      "kar_zarar_yuzde": 12.02,
      "tutulan_gun": 7,
      "cikis_nedeni": "Hedef vurdu",
      "sonuc": "KAZANÇ",
      "ders": "Endüstriyel momentum mükemmel çalıştı"
    }
  ],
  "istatistikler": {
    "toplam_islem": 6,
    "kazanan_islem": 4,
    "kaybeden_islem": 2,
    "kazanma_orani": 66.7,
    "toplam_kar_zarar_yuzde": 17.66,
    "ortalama_kar_zarar_yuzde": 2.94,
    "en_iyi_islem": {"sembol": "CAT", "kar_yuzde": 12.02},
    "en_kotu_islem": {"sembol": "BAC", "kayip_yuzde": -7.09}
  }
}
```

**Otomatik:** İstatistikler güncellenir

#### **3. watchlist.json - İzleme Listesi**

```json
{
  "son_guncelleme": "2026-02-18T16:00:00Z",
  "not": "Potansiyel swing adayları",
  "izleme_listesi": [
    {
      "sembol": "DUK",
      "guncel_fiyat": 126.71,
      "momentum_5gun": 3.4,
      "sektor": "Utilities - Elektrik",
      "notlar": "Savunmacı kamu hizmeti"
    }
  ],
  "haric_tutulanlar": [
    {
      "sembol": "GOOGL",
      "neden": "Negatif momentum -6.7%"
    }
  ]
}
```

**Kullanım:** Günlük tarama sonuçları

---

## 📈 PERFORMANS TAKİP

### **performance_log.csv**

Günlük portföy performansı.

```csv
date,portfolio_value,daily_return_pct,cumulative_return_pct,cash,notes
2026-02-17,403500.00,,0.88,12000,Initial setup
2026-02-18,405120.50,0.40,1.28,12000,Market up
2026-02-19,411898.31,1.65,2.97,12000,Strong day
```

### **transactions.csv**

Tüm alım/satım işlemleri.

```csv
date,action,symbol,shares,price,total,reason
2026-02-17,BUY,SM,1040,21.14,21985.60,"Initial position - Oil & gas"
2026-02-18,SELL,AMD,50,200.12,10006.00,"Stop-loss hit"
```

---

## 🤖 OTOMASYON SCRİPTLERİ

### 📁 `scripts/`

#### **update_all_portfolios.py** ⭐ ANA SCRİPT

**Çalıştırma:**
```bash
python3 scripts/update_all_portfolios.py
```

**Ne yapar:**
1. **4 Portföyü Günceller:**
   - FMP API'den fiyatları çeker
   - K/Z hesaplar
   - Ağırlıkları günceller
   - Dosyaları kaydeder

2. **Swing Trade Otomasyonu:**
   - Aktif pozisyonları kontrol eder
   - Stop-loss/target kontrol
   - Timeframe disiplin (10 gün)
   - Trailing stop aktive
   - Otomatik kapatma

3. **Raporlama:**
   - Portföy özeti
   - Swing özeti
   - Action items

**Seçenekler:**
```bash
# Sadece portföyler
python3 scripts/update_all_portfolios.py --portfolios-only

# Sadece swing
python3 scripts/update_all_portfolios.py --swing-only
```

---

## 📁 ÖZET DOSYALARI

### **portfolio_summary.json**

4 portföyün özet durumu.

```json
{
  "tarih": "2026-02-19",
  "toplam_sermaye": 400000,
  "toplam_deger": 411898.31,
  "toplam_kar_zarar": 11898.31,
  "toplam_getiri_yuzde": 2.97,
  "portfolyolar": {
    "balanced": {"deger": 103096.25, "getiri_yuzde": 3.10},
    "aggressive": {"deger": 91345.24, "getiri_yuzde": -8.65},
    "dividend": {"deger": 112351.42, "getiri_yuzde": 12.35},
    "rotation": {"deger": 105105.40, "getiri_yuzde": 5.11}
  }
}
```

---

## ❌ OLMAYAN SİSTEMLER

### **1. Alert Sistemi**
```
📁 data/alerts.json
```
**Eksik:** Fiyat/teknik alertler.

**Kullanım Senaryoları:**
- RSI 30'un altına düştü
- 50MA kesişmesi
- Hacim spike
- Haber alertleri

### **2. Detaylı Watchlist Tracking**
```
📁 data/watchlist_detailed.json
```
**Eksik:** Adayların detaylı takibi.

**İçermeli:**
- Teknik seviyeler
- Momentum tracking
- Katalızör takibi
- Scoring sistemi

### **3. Backtest Sonuçları**
```
📁 data/backtests/
```
**Eksik:** Stratejilerin backtest sonuçları.

### **4. Risk Metrikleri**
```
📁 data/risk_metrics.json
```
**Eksik:** VaR, Sharpe ratio, beta vb.

---

## 🔧 YAPILACAKLAR

### **Öncelik 1 - YÜKSEK:**
- [ ] Alert sistemi
- [ ] Risk metrikleri
- [ ] Detaylı watchlist tracking

### **Öncelik 2 - ORTA:**
- [ ] Detaylı watchlist
- [ ] Backtest kayıtları
- [ ] Sektör analizi

### **Öncelik 3 - DÜŞÜK:**
- [ ] Grafik verisi
- [ ] Benchmark karşılaştırma
- [ ] Dividend tracking

---

## 📊 DOSYA BOYUTLARI

| Dosya | Boyut | Açıklama |
|-------|-------|----------|
| `active.json` | ~5KB | 7-10 pozisyon |
| `closed.json` | ~3KB | Tüm geçmiş |
| `aggressive.json` | ~5KB | 8 pozisyon |
| `balanced.json` | ~4KB | 6 pozisyon |
| `dividend.json` | ~5KB | 8 pozisyon |
| `rotation.json` | ~3KB | 5 ETF |

**TOPLAM VERİ:** ~50KB (çok küçük, hızlı)

---

## 🔄 GÜNCELLEME SIKLIĞI

| Dosya | Güncelleme | Yöntem |
|-------|-----------|--------|
| Portföyler | Günlük | Script |
| Swing active | Her run | Script |
| Swing closed | Trade sonrası | Script |
| Watchlist | Haftalık | Manuel/Script |
| Logs | Olay bazlı | Manuel |

---

## 💾 YEDEKLEME

**Git:** Tüm dosyalar GitHub'da  
**Sıklık:** Her commit (otomatik)  
**Geçmiş:** Tam commit history

---

**Son Güncelleme:** 19 Şubat 2026  
**Yazar:** Portfolio Tracker System  
**Versiyon:** 2.0 - Tam Türkçe
