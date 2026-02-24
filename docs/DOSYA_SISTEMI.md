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
│   │   ├── 2026-01-02.md ... 2026-02-10-18-FINAL.md
│   │   └── DAILY_2026-02-23.md        # son günlük log
│   │
│   ├── summary.json                   # 4 portföy + swing genel özet
│   ├── transactions.csv               # TÜM işlemler (tek kaynak)
│   ├── performance_log.csv            # günlük performans geçmişi
│   ├── latest_snapshot.json           # son anlık görüntü
│   └── portfolio.json                 # eski tek portföy (legacy)
│
├── docs/                              # dokümantasyon
│   ├── PORTFOLIO_DATA_SKILL.md        # ⭐ ana veri yapısı referansı
│   ├── DOSYA_SISTEMI.md               # bu dosya
│   ├── SWING_TRADE_RULES.md           # swing kuralları
│   ├── PREDICTION_MARKETS_GUIDE.md    # prediction markets rehberi
│   ├── FMP_API_LESSONS_LEARNED.md     # FMP API dersleri
│   ├── strategy.md                    # genel strateji notu
│   ├── AGGRESSIVE_MICRO_CAP_STRATEGY.md    # tek seferlik analiz
│   ├── BALANCED_PORTFOLIO_TECHNICAL_ANALYSIS.md  # tek seferlik analiz
│   ├── ENTRY_TIMING_DECISION.md       # tek seferlik analiz
│   ├── TECHNICAL_ANALYSIS_MICRO_CAPS.md    # tek seferlik analiz
│   └── prompts/
│       ├── DAILY_REPORT_PROMPT.md     # ⭐ sabah raporu master prompt v2.2
│       └── eski/                      # eski bölüm dosyaları (arşiv)
│           └── BOLUM_1-6.md
│
├── reports/                           # oluşturulan raporlar
│   ├── daily/
│   │   ├── DAILY_REPORT_2026-02-20.md
│   │   ├── DAILY_REPORT_2026-02-21.md
│   │   ├── DAILY_REPORT_2026-02-23.md
│   │   ├── DAILY_REPORT_2026-02-24.md # son rapor
│   │   └── eski/                      # eski versiyon raporlar
│   ├── weekly/
│   │   └── WEEKLY_REPORT_2026-02-23.md
│   ├── monthly/
│   ├── report_2026-02-18.md           # eski format rapor
│   └── README.md
│
├── ACTIVE_FILES.md                    # aktif dosya listesi
├── AI_DISRUPTION_OZET.md              # AI disruption özet notu
├── PORTFOY_KURALLARI.md               # portföy kuralları özet
├── README.md                          # ana README
└── .gitignore
```

---

## kritik dosyalar — ne nerede?

### veri dosyaları (her gün güncellenen)

| dosya | içerik | güncelleme sıklığı |
|-------|--------|-------------------|
| `data/portfolios/*.json` | 4 portföy pozisyonları, fiyatlar, k/z | günlük (kapanış sonrası) |
| `data/swing/active.json` | açık swing pozisyonları (max 10) | günlük + trade anında |
| `data/swing/closed.json` | kapatılmış trade'ler + istatistikler | trade kapatıldığında |
| `data/swing/watchlist.json` | izleme listesi, adaylar, urgency | günlük tarama sonrası |
| `data/summary.json` | 4 portföy + swing genel özet | günlük |
| `data/transactions.csv` | ⚠️ TÜM işlemler — TEK KAYNAK | her alış/satışta |
| `data/performance_log.csv` | günlük toplam portföy değeri | günlük |

### referans dosyaları (ara sıra güncellenen)

| dosya | içerik | not |
|-------|--------|-----|
| `docs/PORTFOLIO_DATA_SKILL.md` | ⭐ JSON şemaları, hesaplama kuralları, sektör isimleri | ana referans — project file olarak da yüklü |
| `docs/SWING_TRADE_RULES.md` | swing giriş kriterleri, stop/target kuralları | aktif referans |
| `docs/PREDICTION_MARKETS_GUIDE.md` | kalshi/polymarket kullanım rehberi | aktif referans |
| `docs/prompts/DAILY_REPORT_PROMPT.md` | sabah raporu master prompt v2.2 | günlük rapor üretiminde kullanılır |
| `FMP_SKILL.md` (project file) | FMP API endpoint referansı | project file olarak yüklü, repoda değil |

### raporlar (otomatik üretilen)

| dosya | içerik | sıklık |
|-------|--------|--------|
| `reports/daily/DAILY_REPORT_*.md` | sabah raporu — piyasa + portföy + swing + earnings | her iş günü |
| `reports/weekly/WEEKLY_REPORT_*.md` | haftalık strateji değerlendirmesi | pazar günü |

---

## veri akışı

```
FMP API (fiyat verisi)
    │
    ▼
data/portfolios/*.json  ←→  data/transactions.csv
    │                              │
    ▼                              ▼
data/summary.json           data/performance_log.csv
    │
    ▼
reports/daily/DAILY_REPORT_*.md
```

### günlük rutin

1. **sabah** (seans öncesi): rapor oluştur → `reports/daily/`
2. **seans sırasında**: stop/target kontrol, trade kararları
3. **kapanış sonrası**: FMP'den fiyat çek → JSON güncelle → summary güncelle → git push

### trade akışı

**yeni pozisyon açılışı**:
1. portföy JSON'unda `pozisyonlar[]` dizisine ekle
2. `nakit.miktar` azalt
3. portföy `transactions[]` listesine ekle
4. `data/transactions.csv` satır ekle
5. `data/summary.json` güncelle
6. git commit: `[ALIŞ] PORTFÖY - SEMBOL @FİYAT - NEDEN`

**pozisyon kapatma**:
1. `pozisyonlar[]` listesinden kaldır
2. `nakit.miktar` artır
3. portföy `transactions[]` listesine ekle
4. `data/transactions.csv` satır ekle
5. swing ise → `data/swing/closed.json`'a ekle
6. `data/summary.json` güncelle
7. git commit: `[SATIŞ] PORTFÖY - SEMBOL @FİYAT - NEDEN`

---

## dosya durumları

### aktif — günlük kullanılan
- `data/portfolios/*.json` — 4 portföy
- `data/swing/active.json`, `closed.json`, `watchlist.json` — swing sistemi
- `data/summary.json` — genel özet
- `data/transactions.csv` — işlem kaydı
- `docs/PORTFOLIO_DATA_SKILL.md` — veri yapısı referansı
- `docs/prompts/DAILY_REPORT_PROMPT.md` — rapor prompt'u
- `reports/daily/` — günlük raporlar

### referans — ihtiyaç halinde
- `docs/SWING_TRADE_RULES.md` — swing kuralları
- `docs/PREDICTION_MARKETS_GUIDE.md` — prediction markets
- `docs/FMP_API_LESSONS_LEARNED.md` — API notları

### legacy / tek seferlik — taşınabilir
- `data/portfolio.json` — eski tek portföy dosyası
- `data/GUNLUK_RAPOR_STRATEJI.md`, `_v2.md` — eski rapor stratejileri (data klasöründe olmamalı)
- `data/FMP_NEWS_ENDPOINTS_PREMIUM.md` — eski FMP notu (data klasöründe olmamalı)
- `docs/AGGRESSIVE_MICRO_CAP_STRATEGY.md` — 20 şubat tek seferlik analiz
- `docs/BALANCED_PORTFOLIO_TECHNICAL_ANALYSIS.md` — 20 şubat tek seferlik analiz
- `docs/ENTRY_TIMING_DECISION.md` — 20 şubat tek seferlik analiz
- `docs/TECHNICAL_ANALYSIS_MICRO_CAPS.md` — 20 şubat tek seferlik analiz
- `docs/strategy.md` — eski 35 satırlık strateji notu
- `AI_DISRUPTION_OZET.md` — root'ta olmamalı
- `ACTIVE_FILES.md` — root'ta, eski olabilir
- `PORTFOY_KURALLARI.md` — root'ta, PORTFOLIO_DATA_SKILL ile çakışıyor olabilir
- `reports/report_2026-02-18.md` — eski format rapor

---

## git commit formatı

```
[TİP] PORTFÖY - SEMBOL @FİYAT - AÇIKLAMA

örnekler:
[ALIŞ] Dengeli - SM @20.67 - oil & gas başlangıç pozisyonu
[SATIŞ] Agresif - AMD @199.39 - stop-loss tetiklendi -%10.8
[GÜNCELLEME] tüm portföyler - 24 şubat kapanış fiyatları
[SWING-GİRİŞ] NEM @118.12 - altın momentum breakout
[SWING-ÇIKIŞ] CAT @775.00 - hedef tutturuldu +%12
[REBALANCE] rotasyon - tech'ten enerji+endüstriye rotasyon
[SABAH RAPORU] 24 şubat 2026 - risk-off, temettü güçlü
[HAFTALIK RAPOR] 23 şubat 2026 - hafta değerlendirmesi
[PROMPT] v2.2 - sektör RS analizi eklendi
```

---

> son güncelleme: 24 şubat 2026 | finzora ai
