# portfolio tracker

> 4 portföy simülasyonu + swing trade sistemi
> başlangıç: 17 şubat 2026 | toplam sermaye: $400,000
> yönetim: finzora ai

---

## klasör yapısı

```
data/
├── portfolios/
│   ├── balanced.json        # dengeli ($100K) — multi-sector value + momentum
│   ├── aggressive.json      # agresif büyüme ($100K) — tech/AI momentum
│   ├── dividend.json        # değer + temettü ($100K) — düşük P/E, yüksek yield
│   └── rotation.json        # sektör rotasyonu ($100K) — makro döngü ETF
├── swing/
│   ├── active.json          # açık swing pozisyonları (max 10)
│   ├── closed.json          # kapatılmış trade'ler + dersler
│   └── watchlist.json       # swing trade izleme listesi
├── watchlist.json           # ⭐ merkezi izleme listesi (tüm portföyler + swing)
├── summary.json             # genel portföy özeti
└── transactions.csv         # tüm alış/satış işlemleri (tek kaynak)

docs/
├── PORTFOLIO_DATA_SKILL.md  # ⭐ portföy JSON şemaları + hesaplama kuralları
├── SWING_TRADE_RULES.md     # ⭐ swing trade kural seti v2.0 + JSON şemaları
├── DOSYA_SISTEMI.md         # dosya yapısı detayları
├── PREDICTION_MARKETS_GUIDE.md  # kalshi/polymarket rehberi
├── SELF_VALIDATION.md       # veri doğrulama sistemi
└── prompts/
    ├── DAILY_REPORT_PROMPT.md    # günlük rapor prompt
    └── SESSION_ACTION_PROMPT.md  # seans içi aksiyon prompt

reports/
├── daily/                   # DAILY_REPORT_YYYY-MM-DD.md (pzt-cuma kapanış sonrası)
├── weekly/                  # WEEKLY_REPORT_YYYY-MM-DD.md (pazar)
└── monthly/                 # MONTHLY_YYYY-MM.md (ay sonu)
```

---

## portföy stratejileri

| portföy | sermaye | strateji | hedef | max poz |
|---------|---------|----------|-------|---------|
| dengeli | $100K | multi-sector value + momentum | %15-20/yıl | 7 |
| agresif | $100K | tech/AI büyüme, earnings momentum | %30+/yıl | 10 |
| temettü | $100K | düşük P/E (<20), temettü >%3 | %8-12/yıl + temettü | 15 |
| rotasyon | $100K | sektör ETF makro rotasyonu | SPY + %5/yıl | 8 |

detaylı kurallar: `PORTFOY_KURALLARI.md`

---

## swing trade (v2.0)

| kural | değer |
|-------|-------|
| max eşzamanlı | 10 |
| stop-loss | ATR tabanlı dinamik (2.0 × ATR14) |
| kar hedefi | kademeli: %50 hedefte sat + %50 trailing stop |
| min R:R | 2:1 |
| hisse filtre | beta 1.0+, ATR% 2+, hacim 500K+, cap $2B+ |
| giriş | 5 yöntem, min 2 teyit zorunlu |
| yasak sektörler | utilities, REITs, beta < 0.8 |

detaylı kurallar + JSON şemaları: `docs/SWING_TRADE_RULES.md`

---

## dokümantasyon haritası

| konu | tek kaynak |
|------|-----------|
| portföy JSON şemaları, hesaplama kuralları | `docs/PORTFOLIO_DATA_SKILL.md` |
| swing trade kuralları + JSON şemaları | `docs/SWING_TRADE_RULES.md` |
| dosya yapısı | `docs/DOSYA_SISTEMI.md` |
| portföy stratejileri | `PORTFOY_KURALLARI.md` |
| prediction markets | `docs/PREDICTION_MARKETS_GUIDE.md` |
| veri doğrulama | `docs/SELF_VALIDATION.md` |
| FMP API | `FMP_SKILL.md` (project file) |

---

## günlük rutin

| zaman (TR) | aktivite | çıktı |
|------------|----------|-------|
| ~14:00 | günlük rapor (NYSE açılmadan) | `reports/daily/DAILY_REPORT_*.md` |
| 17:30+ | seans açılış kontrolü | JSON güncelleme + trade kararları |
| 19:00-22:00 | mid-session analiz | watchlist + fırsat tarama |
| 23:00-00:00 | kapanış öncesi final | trailing stop + son kontrol |

haftalık (pazar): `reports/weekly/WEEKLY_REPORT_*.md`
aylık (ay sonu): `reports/monthly/MONTHLY_*.md`

---

## veri kaynakları

- **FMP API** (premium): fiyat, temel veriler, teknik göstergeler, haberler
- **kalshi / polymarket**: prediction markets sentiment
- **web search**: makro haberler, earnings sonuçları

API referansı: `FMP_SKILL.md` (proje dosyası)

---

## git commit formatı

```
[ALIŞ] Portföy - SEMBOL @FİYAT - neden
[SATIŞ] Portföy - SEMBOL @FİYAT - neden
[GÜNCELLEME] tüm portföyler - tarih kapanış fiyatları
[SWING-GİRİŞ] SEMBOL @FİYAT - neden
[SWING-ÇIKIŞ] SEMBOL @FİYAT - sonuç +/-%X
[WATCHLIST] merkezi watchlist güncellendi - detay
[DOKÜMAN] açıklama
[REBALANCE] Portföy - rotasyon detayı
```

---

> son güncelleme: 25 şubat 2026 | finzora ai
