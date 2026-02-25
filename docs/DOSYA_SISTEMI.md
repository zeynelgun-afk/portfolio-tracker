# PORTFOLIO TRACKER — DOSYA SİSTEMİ

> **son güncelleme**: 25 şubat 2026
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
│   │   ├── watchlist.json             # swing trade izleme listesi
│   │   └── README.md                  # swing klasörü açıklaması
│   │
│   ├── logs/                          # tarihsel trade logları (arşiv)
│   │
│   ├── watchlist.json                 # ⭐ MERKEZİ İZLEME LİSTESİ (tüm portföyler + swing)
│   ├── summary.json                   # 4 portföy + swing genel özet
│   └── transactions.csv               # ⚠️ TÜM işlemler — TEK KAYNAK
│
├── docs/                              # dokümantasyon
│   ├── PORTFOLIO_DATA_SKILL.md        # ⭐ portföy JSON şemaları + hesaplama kuralları
│   ├── SWING_TRADE_RULES.md           # ⭐ swing trade kural seti v2.0 + JSON şemaları
│   ├── DOSYA_SISTEMI.md               # bu dosya
│   ├── PREDICTION_MARKETS_GUIDE.md    # prediction markets rehberi
│   ├── SELF_VALIDATION.md             # 3 katmanlı doğrulama sistemi
│   └── prompts/
│       ├── DAILY_REPORT_PROMPT.md     # sabah raporu master prompt
│       └── SESSION_ACTION_PROMPT.md   # seans içi aksiyon prompt
│
├── reports/                           # oluşturulan raporlar
│   ├── daily/
│   │   └── DAILY_REPORT_*.md          # günlük raporlar (pzt-cuma kapanış sonrası)
│   ├── weekly/
│   │   └── WEEKLY_REPORT_*.md         # haftalık raporlar (pazar)
│   └── monthly/
│       └── MONTHLY_*.md               # aylık raporlar (ay sonu)
│
├── backups/                           # veritabanı yedekleri
│   └── db/
│
├── PORTFOY_KURALLARI.md               # portföy yönetim kuralları + risk limitleri
├── README.md                          # repo ana dokümantasyonu
└── .gitignore
```

---

## dokümantasyon haritası

her konu tek bir yerde yaşar, tekrar edilmez:

| konu | tek kaynak | içerik |
|------|-----------|--------|
| portföy JSON şemaları | `docs/PORTFOLIO_DATA_SKILL.md` | pozisyon alanları, hesaplama kuralları, sektör isimleri, günlük akış, git format |
| swing trade her şey | `docs/SWING_TRADE_RULES.md` | hisse seçimi, 5 giriş stratejisi, ATR stop-loss, kademeli çıkış, active/closed/watchlist JSON şemaları |
| portföy stratejileri | `PORTFOY_KURALLARI.md` | 4 portföy hedefleri, risk limitleri |
| prediction markets | `docs/PREDICTION_MARKETS_GUIDE.md` | kalshi/polymarket kullanımı |
| veri doğrulama | `docs/SELF_VALIDATION.md` | 3 katmanlı doğrulama sistemi |
| FMP API | `FMP_SKILL.md` (project file) | endpoint referansı, python şablonları |

---

## kritik dosyalar

### her gün güncellenen

| dosya | içerik | güncelleme zamanı |
|-------|--------|-------------------|
| `data/portfolios/*.json` | 4 portföy pozisyonları, fiyatlar, k/z | kapanış sonrası |
| `data/swing/active.json` | açık swing pozisyonları (max 10) | günlük + trade anında |
| `data/swing/closed.json` | kapatılmış trade'ler + istatistikler | trade kapatıldığında |
| `data/swing/watchlist.json` | swing trade adayları | tarama sonrası |
| `data/watchlist.json` | merkezi izleme listesi (tüm portföyler) | tarama sonrası |
| `data/summary.json` | 4 portföy + swing genel özet | günlük |
| `data/transactions.csv` | TÜM alış/satış işlemleri | her trade'de |
| `reports/daily/DAILY_REPORT_*.md` | günlük rapor | her iş günü kapanış sonrası |

### referans (ihtiyaç halinde güncellenen)

| dosya | içerik |
|-------|--------|
| `docs/PORTFOLIO_DATA_SKILL.md` | portföy JSON şemaları, hesaplama kuralları, sektör isimleri |
| `docs/SWING_TRADE_RULES.md` | swing trade kural seti v2.0 + tüm JSON şemaları |
| `docs/prompts/DAILY_REPORT_PROMPT.md` | günlük rapor prompt |
| `docs/prompts/SESSION_ACTION_PROMPT.md` | seans içi aksiyon prompt |
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

### swing trade akışı

**tarama**: FMP API → beta/ATR/hacim filtre → watchlist.json → min 2 teyit → giriş kararı
**giriş**: active.json'a ekle (tüm zorunlu alanlar: atr_giris, risk_tutar, rr_orani, tarama_yontemi) → CSV ekle → git push
**çıkış**: active.json'dan kaldır → closed.json'a ekle (cikis_yontemi, gercek_rr, ders) → CSV ekle → git push

### watchlist akışı

**merkezi dosya**: `data/watchlist.json` — tüm portföy adayları tek dosyada
- her adayda `hedef_portfoy` alanı: swing / agresif / dengeli / temettü / rotasyon
- portföy JSON'larında ayrı watchlist tutulmaz

**swing watchlist**: `data/swing/watchlist.json` — sadece swing trade adayları
- beta 1.0+, ATR% 2+, hacim 500K+ filtreli
- tarama_yontemi ve tahmini_rr zorunlu

---

## git commit formatı

```
[ALIŞ] Dengeli - SM @20.67 - oil & gas başlangıç pozisyonu
[SATIŞ] Agresif - SHOP @117.28 - stop-loss tetiklendi
[GÜNCELLEME] tüm portföyler - 25 şubat kapanış fiyatları
[SWING-GİRİŞ] NEM @118.12 - altın momentum breakout
[SWING-ÇIKIŞ] CAT @775.00 - hedef tutturuldu +%12
[WATCHLIST] merkezi watchlist güncellendi - IREN eklendi
[DOKÜMAN] açıklama
[REBALANCE] Rotasyon - tech'ten enerji+endüstriye rotasyon
```

---

> son güncelleme: 25 şubat 2026 | finzora ai
