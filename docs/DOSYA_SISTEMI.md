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
│   │   └── closed.json                # kapatılmış trade'ler + istatistikler
│   │
│   ├── logs/                          # tarihsel trade logları (arşiv)
│   │
│   ├── watchlist.json                 # ⭐ MERKEZİ İZLEME LİSTESİ (tüm portföyler + swing)
│   ├── summary.json                   # 4 portföy + swing genel özet
│   └── transactions.csv               # ⚠️ TÜM işlemler — TEK KAYNAK
│
├── docs/                              # dokümantasyon
│   ├── PORTFOLIO_DATA_SKILL.md        # ⭐ ana veri yapısı referansı
│   ├── DOSYA_SISTEMI.md               # bu dosya
│   ├── SWING_TRADE_RULES.md           # swing kuralları
│   ├── PREDICTION_MARKETS_GUIDE.md    # prediction markets rehberi
│   ├── SELF_VALIDATION.md             # 3 katmanlı doğrulama sistemi
│   └── prompts/
│       ├── DAILY_REPORT_PROMPT.md     # ⭐ sabah raporu master prompt
│       └── SESSION_ACTION_PROMPT.md   # ⭐ seans içi aksiyon prompt
│
├── reports/                           # oluşturulan raporlar
│   ├── daily/
│   │   └── DAILY_REPORT_*.md          # günlük raporlar (pzt-cuma kapanış sonrası)
│   ├── weekly/
│   │   └── WEEKLY_REPORT_*.md         # haftalık raporlar (pazar)
│   └── monthly/
│       └── MONTHLY_*.md               # aylık raporlar (ay sonu)
│
├── PORTFOY_KURALLARI.md               # portföy yönetim kuralları + risk limitleri
├── README.md                          # repo ana dokümantasyonu
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
| `data/watchlist.json` | **merkezi** izleme listesi (tüm portföyler + swing) | tarama sonrası |
| `data/summary.json` | 4 portföy + swing genel özet | günlük |
| `data/transactions.csv` | TÜM alış/satış işlemleri | her trade'de |
| `reports/daily/DAILY_REPORT_*.md` | günlük rapor | her iş günü kapanış sonrası |

### referans (ihtiyaç halinde)

| dosya | içerik |
|-------|--------|
| `docs/PORTFOLIO_DATA_SKILL.md` | ⭐ JSON şemaları, hesaplama kuralları, sektör isimleri |
| `docs/prompts/DAILY_REPORT_PROMPT.md` | ⭐ günlük rapor prompt |
| `docs/prompts/SESSION_ACTION_PROMPT.md` | ⭐ seans içi aksiyon prompt |
| `docs/SWING_TRADE_RULES.md` | swing giriş/çıkış kuralları |
| `docs/PREDICTION_MARKETS_GUIDE.md` | kalshi/polymarket rehberi |
| `docs/SELF_VALIDATION.md` | veri/analiz/karar doğrulama kuralları |
| `PORTFOY_KURALLARI.md` | portföy bazlı strateji kuralları |
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

### watchlist akışı

**tek merkezi dosya**: `data/watchlist.json`
- her adayda `hedef_portfoy` alanı: swing / agresif / dengeli / temettü / rotasyon
- portföy JSON'larında watchlist tutulmaz
- seans prompt'u ve günlük rapor bu dosyadan okur

---

## git commit formatı

```
[ALIŞ] Dengeli - SM @20.67 - oil & gas başlangıç pozisyonu
[SATIŞ] Agresif - SHOP @117.28 - stop-loss tetiklendi
[GÜNCELLEME] tüm portföyler - 24 şubat kapanış fiyatları
[SWING-GİRİŞ] NEM @118.12 - altın momentum breakout
[SWING-ÇIKIŞ] CAT @775.00 - hedef tutturuldu +%12
[WATCHLIST] merkezi watchlist güncellendi - IREN eklendi
[REFACTOR] yapısal düzenleme - açıklama
```

---

> son güncelleme: 24 şubat 2026 | finzora ai
