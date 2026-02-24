# PORTFOLIO TRACKER — DOSYA SİSTEMİ

> **son güncelleme**: 24 şubat 2026
> **repo**: https://github.com/zeynelgun-afk/portfolio-tracker

---

## klasör yapısı

```
portfolio-tracker/
│
├── data/
│   ├── portfolios/                    # 4 ana portföy ($400K toplam)
│   │   ├── balanced.json              # dengeli portföy ($100K)
│   │   ├── aggressive.json            # agresif büyüme ($100K)
│   │   ├── dividend.json              # değer + temettü ($100K)
│   │   └── rotation.json              # sektör rotasyonu ($100K)
│   │
│   ├── swing/                         # swing trade sistemi
│   │   ├── active.json                # aktif pozisyonlar (max 10)
│   │   ├── closed.json                # kapatılmış trade'ler + istatistikler
│   │   ├── watchlist.json             # izleme listesi + adaylar
│   │   ├── README.md                  # swing sistem açıklaması
│   │   ├── DERSLER_SABLON.md          # ders çıkarma şablonu
│   │   ├── AI_DISRUPTION_REHBERI.md   # AI disruption analizi
│   │   ├── TECH_RECOVERY_PLAYBOOK.md  # tech toparlanma planı
│   │   └── OZET_18_SUBAT.md           # periyodik özet
│   │
│   ├── logs/                          # günlük loglar (tarih bazlı)
│   │   └── DAILY_*.md, 2026-*.md
│   │
│   ├── summary.json                   # 4 portföy + swing genel özet
│   ├── transactions.csv               # ⚠️ TÜM işlemler — TEK KAYNAK
│   ├── performance_log.csv            # günlük performans geçmişi
│   ├── latest_snapshot.json           # son anlık görüntü
│   └── portfolio.json                 # eski tek portföy (legacy)
│
├── docs/                              # dokümantasyon
│   ├── PORTFOLIO_DATA_SKILL.md        # ⭐ ana veri yapısı referansı
│   ├── DOSYA_SISTEMI.md               # bu dosya
│   ├── SWING_TRADE_RULES.md           # swing kuralları
│   ├── PREDICTION_MARKETS_GUIDE.md    # prediction markets rehberi
│   └── prompts/
│       └── DAILY_REPORT_PROMPT.md     # ⭐ sabah raporu master prompt v2.2
│
├── reports/                           # oluşturulan raporlar
│   ├── daily/
│   │   └── DAILY_REPORT_*.md          # sabah raporları
│   ├── weekly/
│   │   └── WEEKLY_REPORT_*.md         # haftalık raporlar
│   └── monthly/
│
├── README.md
├── ACTIVE_FILES.md
├── AI_DISRUPTION_OZET.md
├── PORTFOY_KURALLARI.md
└── .gitignore
```

---

## kritik dosyalar

### her gün güncellenen

| dosya | içerik | güncelleme |
|-------|--------|-----------|
| `data/portfolios/*.json` | 4 portföy pozisyonları, fiyatlar, k/z | kapanış sonrası |
| `data/swing/active.json` | açık swing pozisyonları (max 10) | günlük + trade anında |
| `data/swing/closed.json` | kapatılmış trade'ler + istatistikler | trade kapatıldığında |
| `data/swing/watchlist.json` | izleme listesi, urgency | tarama sonrası |
| `data/summary.json` | 4 portföy + swing genel özet | günlük |
| `data/transactions.csv` | TÜM alış/satış işlemleri | her trade'de |
| `reports/daily/DAILY_REPORT_*.md` | sabah raporu | her iş günü |

### referans (ihtiyaç halinde)

| dosya | içerik |
|-------|--------|
| `docs/PORTFOLIO_DATA_SKILL.md` | ⭐ JSON şemaları, hesaplama kuralları, sektör isimleri |
| `docs/prompts/DAILY_REPORT_PROMPT.md` | ⭐ sabah raporu prompt v2.2 |
| `docs/SWING_TRADE_RULES.md` | swing giriş/çıkış kuralları |
| `docs/PREDICTION_MARKETS_GUIDE.md` | kalshi/polymarket rehberi |
| `FMP_SKILL.md` (project file) | FMP API endpoint referansı |

---

## veri akışı

```
FMP API (fiyat verisi)
    │
    ▼
data/portfolios/*.json  ←→  data/transactions.csv
    │
    ▼
data/summary.json
    │
    ▼
reports/daily/DAILY_REPORT_*.md
```

### trade akışı

**yeni pozisyon**: JSON'a ekle → nakit azalt → transactions[] ekle → CSV ekle → summary güncelle → git push
**pozisyon kapat**: JSON'dan kaldır → nakit artır → transactions[] ekle → CSV ekle → (swing ise closed.json) → summary güncelle → git push

---

## git commit formatı

```
[ALIŞ] Dengeli - SM @20.67 - oil & gas başlangıç pozisyonu
[SATIŞ] Agresif - SHOP @117.28 - stop-loss tetiklendi
[GÜNCELLEME] tüm portföyler - 24 şubat kapanış fiyatları
[SWING-GİRİŞ] NEM @118.12 - altın momentum breakout
[SWING-ÇIKIŞ] CAT @775.00 - hedef tutturuldu +%12
[SABAH RAPORU] 24 şubat 2026 - risk-off, temettü güçlü
[HAFTALIK RAPOR] 23 şubat 2026 - hafta değerlendirmesi
```

---

## legacy — temizlenebilir

| dosya | durum |
|-------|-------|
| `data/portfolio.json` | eski tek portföy, artık kullanılmıyor |
| `data/GUNLUK_RAPOR_STRATEJI.md`, `_v2.md` | data klasöründe olmamalı |
| `data/FMP_NEWS_ENDPOINTS_PREMIUM.md` | data klasöründe olmamalı |
| `AI_DISRUPTION_OZET.md` | root'ta, taşınabilir |
| `ACTIVE_FILES.md` | root'ta, eski olabilir |
| `PORTFOY_KURALLARI.md` | PORTFOLIO_DATA_SKILL ile çakışıyor olabilir |

---

> son güncelleme: 24 şubat 2026 | finzora ai
