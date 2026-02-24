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
│   └── closed.json          # kapatılmış trade'ler + dersler
├── watchlist.json           # ⭐ merkezi izleme listesi (tüm portföyler + swing)
├── summary.json             # genel portföy özeti
└── transactions.csv         # tüm alış/satış işlemleri (tek kaynak)

docs/
├── PORTFOLIO_DATA_SKILL.md  # ⭐ JSON şema kuralları (KRİTİK — her güncelleme öncesi oku)
├── DOSYA_SISTEMI.md         # dosya yapısı detayları
├── SWING_TRADE_RULES.md     # swing trade kuralları
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

## swing trade

| kural | değer |
|-------|-------|
| max eşzamanlı | 10 |
| stop-loss | %5 |
| kar hedefi | %10 |
| min R:R | 2:1 |
| çıkış | hedefe ulaşınca %50 sat + kalan trailing stop (-%5) |

detaylı kurallar: `docs/SWING_TRADE_RULES.md`

---

## merkezi watchlist

`data/watchlist.json` — tüm portföy ve swing adayları tek dosyada.
her adayda `hedef_portfoy` alanı hangi stratejiye ait olduğunu belirtir.
portföy JSON'larında ayrı watchlist tutulmaz.

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
```

---

> son güncelleme: 24 şubat 2026 | finzora ai
