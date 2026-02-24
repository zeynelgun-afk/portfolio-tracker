# 📊 Portfolio Tracker

> **4 Portföy Simülasyonu** - Dengeli, Agresif, Temettü, Rotasyon  
> **Başlangıç:** 17 Şubat 2026 | **Toplam Sermaye:** $400,000

---

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
│   ├── summary.json         # Genel özet
│   └── transactions.csv     # Tüm işlemler
├── reports/
│   ├── daily/               # Günlük raporlar (Pzt-Cmt)
│   │   └── DAILY_REPORT_YYYY-MM-DD.md
│   └── weekly/              # Haftalık raporlar (Pazar)
│       └── WEEKLY_REPORT_YYYY-MM-DD.md
├── docs/                    # Dokümantasyon
│   ├── PORTFOLIO_DATA_SKILL.md  # JSON şema (KRİTİK)
│   └── strategy.md
├── PORTFOY_KURALLARI.md     # Portföy yönetim kuralları
└── README.md                # Bu dosya
```

---

## 💼 4 Portföy Stratejisi

| Portföy | Sermaye | Strateji | Hedef |
|---------|---------|----------|-------|
| **Dengeli** | $100K | Multi-sector value + momentum | Yıllık %15-20 |
| **Agresif** | $100K | Micro-cap AI disruption | Yıllık %30+ |
| **Temettü** | $100K | Düşük P/E, yüksek temettü | Yıllık %8-12 + temettü |
| **Rotasyon** | $100K | Sektör ETF makro rotasyonu | S&P 500 + %5 |

---

## 🔄 Günlük Rutin

### Piyasa Kapanışı Sonrası
1. **Fiyat Güncelle** → FMP API ile manuel güncelleme
2. **Günlük Rapor** → `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
3. **GitHub Push** → Tüm değişiklikleri kaydet

### Pazar Günü
1. **Haftalık Rapor** → `reports/weekly/WEEKLY_REPORT_YYYY-MM-DD.md`
2. **Strateji Review** → Sektör rotasyonu, balon riski, portföy dengeleme
3. **Watchlist Güncelle** → `data/swing/watchlist.json`

---

## 📊 Veri Dosyaları

### Portföy JSON Yapısı
```json
{
  "portfoy_adi": "Dengeli Portföy",
  "baslangic_sermaye": 100000,
  "nakit": {"miktar": 12345.67, "para_birimi": "USD"},
  "pozisyonlar": [...],
  "transactions": [...],
  "son_guncelleme": "2026-02-21T19:41:06"
}
```

### Pozisyon Zorunlu Alanlar
- `sembol`, `isim`, `sektor`
- `adet`, `maliyet_baz`, `guncel_fiyat`
- `yatirim`, `guncel_deger`, `kar_zarar`
- `giris_tarihi`, `giris_fiyati`, `giris_nedeni`

**Detaylı şema:** `docs/PORTFOLIO_DATA_SKILL.md`

---

## 🎯 Swing Trade Kuralları

| Kural | Değer |
|-------|-------|
| Max eşzamanlı pozisyon | 10 |
| Stop-loss | %5 |
| Kar hedefi | %10 |
| Min R:R oranı | 2:1 |
| Tutma süresi | 7-10 gün tavsiye (trailing stop ile yönetilir) |

**Detaylı kurallar:** `data/swing/README.md`

---

## 📈 Raporlar

### Günlük Rapor (Pazartesi-Cumartesi)
- Format: `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
- İçerik: Portföy performansı, önemli haberler, swing durumu
- **Cumartesi özel:** Haber odaklı derinlemesine analiz

### Haftalık Rapor (Pazar)
- Format: `reports/weekly/WEEKLY_REPORT_YYYY-MM-DD.md`
- İçerik: Haftalık özet, sektör rotasyonu, önümüzdeki hafta stratejisi

---

## 📋 Git Commit Formatı

```
[TİP] PORTFÖY - SEMBOL @FİYAT - AÇIKLAMA

Örnekler:
[ALIŞ] Dengeli - SM @20.67 - Oil & gas başlangıç pozisyonu
[SATIŞ] Agresif - AMD @199.39 - Stop-loss tetiklendi
[GÜNCELLEME] Tüm portföyler - 21 Şubat kapanış fiyatları
[SWING-GİRİŞ] NEM @118.12 - Altın momentum breakout
```

---

## 🔗 API & Araçlar

- **FMP API:** Financial Modeling Prep (Premium plan)
- **Git:** Versiyon kontrolü ve yedekleme
- **Manuel güncelleme:** Direkt JSON düzenleme

---

## 📚 Dokümantasyon

| Dosya | Açıklama |
|-------|----------|
| `docs/PORTFOLIO_DATA_SKILL.md` | JSON şema ve güncelleme kuralları (KRİTİK) |
| `docs/strategy.md` | Genel portföy stratejisi |
| `docs/SWING_TRADE_RULES.md` | Swing trade detaylı kurallar |
| `PORTFOY_KURALLARI.md` | Yönetim kuralları ve ilkeler |
| `ACTIVE_FILES.md` | Aktif dosyalar listesi |

---

**Son Güncelleme:** 21 Şubat 2026  
**Durum:** ✅ Aktif  
**Simülasyon Dönemi:** 17 Şubat 2026 - Devam Ediyor
