# portfolio tracker

> 3 portföy simülasyonu + swing trade sistemi
> başlangıç: 17 şubat 2026 | toplam sermaye: $600,000
> yönetim: finzora ai

---

## portföy yapısı

| portföy | sermaye | strateji | hedef |
|---------|---------|----------|-------|
| **dengeli** | $100K | multi-sector value + momentum | %15-20/yıl |
| **agresif büyüme** | $400K | sektör-agnostik momentum + katalizör | %30+/yıl |
| **değer + temettü** | $100K | düşük P/E (<20), temettü >%3 | %8-12/yıl + temettü |

> sektör rotasyonu portföyü 26 şubat 2026'da kapatıldı → `data/archive/`

---

## klasör yapısı

```
data/
├── portfolios/
│   ├── balanced.json        # dengeli ($100K)
│   ├── aggressive.json      # agresif momentum ($400K)
│   └── dividend.json        # değer + temettü ($100K)
├── swing/
│   ├── active.json          # açık swing pozisyonları (max 10)
│   ├── closed.json          # kapatılmış trade'ler + dersler
│   └── watchlist.json       # swing trade izleme listesi
├── archive/                 # kapatılmış portföyler
│   └── rotation_kapandi_2026-02-26.json
├── watchlist.json           # merkezi izleme listesi
├── summary.json             # genel portföy özeti
└── transactions.csv         # tüm alış/satış işlemleri

docs/
├── AGGRESSIVE_MOMENTUM_STRATEGY.md  # ⭐ agresif momentum strateji detayları
├── PORTFOLIO_DATA_SKILL.md          # ⭐ portföy JSON şemaları + hesaplama kuralları
├── SWING_TRADE_RULES.md             # ⭐ swing trade kural seti v2.0
├── BALANCED_STRATEGY.md             # dengeli portföy stratejisi
├── DIVIDEND_STRATEGY.md             # temettü portföy stratejisi
├── DOSYA_SISTEMI.md                 # dosya yapısı detayları
├── PREDICTION_MARKETS_GUIDE.md      # kalshi/polymarket rehberi
├── SELF_VALIDATION.md               # veri doğrulama sistemi
└── prompts/
    ├── DAILY_REPORT_PROMPT.md       # günlük rapor prompt
    └── SESSION_ACTION_PROMPT.md     # seans içi aksiyon prompt

reports/
├── daily/                   # DAILY_REPORT_YYYY-MM-DD.md (pzt-cuma)
├── weekly/                  # WEEKLY_REPORT_YYYY-MM-DD.md (pazar)
└── monthly/                 # MONTHLY_YYYY-MM.md (ay sonu)
```

---

## agresif büyüme stratejisi ($400K)

ana portföy — toplam sermayenin %67'si.

| parametre | değer |
|-----------|-------|
| yıllık hedef | %30+ |
| max eşzamanlı pozisyon | 10 |
| pozisyon büyüklüğü | max %10 ($40K) |
| çıkış kriteri | stop-loss / hedef / momentum kaybı |
| stop-loss | %8 |
| kar hedefi | minimum %10 |
| R:R minimum | 2:1 |
| sektör kısıtı | YOK — herhangi bir sektör |
| min sektör dengesi | 3 farklı sektör |

**giriş kriterleri**: güçlü katalizör (earnings, M&A, contract, jeopolitik) + teknik momentum + risk-ödül dengesi

**sektörler**: enerji, sağlık, finans, savunma, tüketici, materials, industrial, teknoloji vs — önemli olan momentum!

detay: `docs/AGGRESSIVE_STRATEGY.md`

---

## swing trade

| kural | değer |
|-------|-------|
| max eşzamanlı | 10 |
| stop-loss | ATR tabanlı dinamik (2.0 × ATR14) |
| kar hedefi | kademeli: %50 hedefte sat + %50 trailing stop |
| min R:R | 2:1 |

detay: `docs/SWING_TRADE_RULES.md`

---

## dokümantasyon haritası

| konu | kaynak |
|------|--------|
| agresif büyüme strateji detayları | `docs/AGGRESSIVE_STRATEGY.md` |
| portföy JSON şemaları, hesaplama kuralları | `docs/PORTFOLIO_DATA_SKILL.md` |
| swing trade kuralları + JSON şemaları | `docs/SWING_TRADE_RULES.md` |
| portföy bazlı strateji kuralları | `PORTFOY_KURALLARI.md` |
| dosya yapısı | `docs/DOSYA_SISTEMI.md` |
| prediction markets | `docs/PREDICTION_MARKETS_GUIDE.md` |
| veri doğrulama | `docs/SELF_VALIDATION.md` |
| FMP API | `FMP_SKILL.md` (project file) |

---

## günlük rutin

| zaman (TR) | aktivite | çıktı |
|------------|----------|-------|
| ~14:00 | günlük rapor (NYSE kapanış sonrası) | `reports/daily/DAILY_REPORT_*.md` |
| 17:30+ | seans açılış | JSON güncelleme + trade kararları |
| 19:00-22:00 | mid-session | watchlist + fırsat tarama |
| 23:00-00:00 | kapanış öncesi | trailing stop + son kontrol |

---

## veri kaynakları

- **FMP API** (premium): fiyat, temel veriler, teknik göstergeler, haberler
- **kalshi / polymarket**: prediction markets sentiment
- **web search**: makro haberler, earnings sonuçları

---

## git commit formatı

```
[ALIŞ] Portföy - SEMBOL @FİYAT - neden
[SATIŞ] Portföy - SEMBOL @FİYAT - neden
[GÜNCELLEME] tüm portföyler - tarih kapanış fiyatları
[SWING-GİRİŞ] SEMBOL @FİYAT - neden
[SWING-ÇIKIŞ] SEMBOL @FİYAT - sonuç +/-%X
[STRATEJİ] strateji değişikliği açıklaması
[YAPISAL] yapısal değişiklik açıklaması
[DOKÜMAN] açıklama
```

---

> son güncelleme: 26 şubat 2026 | finzora ai
