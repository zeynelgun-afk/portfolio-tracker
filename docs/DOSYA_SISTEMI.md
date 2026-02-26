# PORTFOLIO TRACKER — DOSYA SİSTEMİ

> **son güncelleme**: 26 şubat 2026
> **repo**: https://github.com/zeynelgun-afk/portfolio-tracker

---

## klasör yapısı

```
portfolio-tracker/
│
├── data/
│   ├── portfolios/                    # 3 ana portföy ($600K toplam)
│   │   ├── balanced.json              # dengeli portföy ($100K)
│   │   ├── aggressive.json            # agresif momentum ($400K)
│   │   └── dividend.json              # değer + temettü ($100K)
│   │
│   ├── swing/                         # swing trade sistemi
│   │   ├── active.json                # aktif pozisyonlar (max 10)
│   │   ├── closed.json                # kapatılmış trade'ler + istatistikler
│   │   ├── watchlist.json             # swing trade izleme listesi
│   │   └── README.md                  # swing klasörü açıklaması
│   │
│   ├── archive/                       # kapatılmış portföyler
│   │   └── rotation_kapandi_2026-02-26.json
│   │
│   ├── logs/                          # tarihsel trade logları (arşiv)
│   │
│   ├── watchlist.json                 # merkezi izleme listesi (tüm portföyler + swing)
│   ├── summary.json                   # 3 portföy + swing genel özet
│   └── transactions.csv               # tüm işlemler — tek kaynak
│
├── docs/                              # dokümantasyon
│   ├── AGGRESSIVE_MOMENTUM_STRATEGY.md # ⭐ agresif momentum strateji detayları
│   ├── PORTFOLIO_DATA_SKILL.md        # ⭐ portföy JSON şemaları + hesaplama kuralları
│   ├── SWING_TRADE_RULES.md           # ⭐ swing trade kural seti v2.0 + JSON şemaları
│   ├── BALANCED_STRATEGY.md           # dengeli portföy stratejisi
│   ├── DIVIDEND_STRATEGY.md           # temettü portföy stratejisi
│   ├── DOSYA_SISTEMI.md               # bu dosya
│   ├── PREDICTION_MARKETS_GUIDE.md    # prediction markets rehberi
│   ├── SELF_VALIDATION.md             # 3 katmanlı doğrulama sistemi
│   └── prompts/
│       ├── DAILY_REPORT_PROMPT.md     # sabah raporu master prompt
│       └── SESSION_ACTION_PROMPT.md   # seans içi aksiyon prompt
│
├── reports/                           # oluşturulan raporlar
│   ├── daily/   → DAILY_REPORT_*.md
│   ├── weekly/  → WEEKLY_REPORT_*.md
│   └── monthly/ → MONTHLY_*.md
│
├── PORTFOY_KURALLARI.md               # portföy yönetim kuralları + risk limitleri
├── README.md                          # repo ana dokümantasyonu
└── .gitignore
```

---

## dokümantasyon haritası

her konu tek bir yerde yaşar, tekrar edilmez:

| konu | tek kaynak |
|------|-----------|
| agresif momentum strateji | `docs/AGGRESSIVE_MOMENTUM_STRATEGY.md` |
| portföy JSON şemaları | `docs/PORTFOLIO_DATA_SKILL.md` |
| swing trade her şey | `docs/SWING_TRADE_RULES.md` |
| portföy stratejileri | `PORTFOY_KURALLARI.md` |
| prediction markets | `docs/PREDICTION_MARKETS_GUIDE.md` |
| veri doğrulama | `docs/SELF_VALIDATION.md` |
| FMP API | `FMP_SKILL.md` (project file) |

---

## kritik dosyalar

### her gün güncellenen

| dosya | güncelleme zamanı |
|-------|-------------------|
| `data/portfolios/*.json` | kapanış sonrası |
| `data/swing/active.json` | günlük + trade anında |
| `data/swing/closed.json` | trade kapatıldığında |
| `data/swing/watchlist.json` | tarama sonrası |
| `data/summary.json` | günlük |
| `data/transactions.csv` | her trade'de |
| `reports/daily/DAILY_REPORT_*.md` | her iş günü |

### referans (ihtiyaç halinde güncellenen)

| dosya | içerik |
|-------|--------|
| `docs/AGGRESSIVE_MOMENTUM_STRATEGY.md` | aylık %5 strateji, sinyal tipleri, risk kuralları |
| `docs/PORTFOLIO_DATA_SKILL.md` | JSON şemaları, hesaplama kuralları |
| `docs/SWING_TRADE_RULES.md` | swing trade kural seti v2.0 |
| `docs/prompts/DAILY_REPORT_PROMPT.md` | günlük rapor prompt |
| `docs/prompts/SESSION_ACTION_PROMPT.md` | seans içi aksiyon prompt |

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
**pozisyon kapat**: JSON'dan kaldır → nakit artır → transactions[] ekle → CSV ekle → summary güncelle → git push

---

## git commit formatı

```
[ALIŞ] Portföy - SEMBOL @FİYAT - neden
[SATIŞ] Portföy - SEMBOL @FİYAT - neden
[GÜNCELLEME] tüm portföyler - tarih kapanış fiyatları
[SWING-GİRİŞ] SEMBOL @FİYAT - neden
[SWING-ÇIKIŞ] SEMBOL @FİYAT - sonuç +/-%X
[STRATEJİ] strateji değişikliği
[YAPISAL] yapısal değişiklik
[DOKÜMAN] açıklama
```

---

> son güncelleme: 26 şubat 2026 | finzora ai
