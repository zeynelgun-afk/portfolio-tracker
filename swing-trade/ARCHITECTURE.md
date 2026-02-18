# 🧠 Swing Trade — Self-Learning System Architecture

## Temel Prensip

```
GitHub = BEYİN (Analiz + Karar + Öğrenme)
Finzora = ELLER (Sadece signals.json okur ve gösterir)
```

## Veri Akışı

```
┌─────────────────────────────────────────────────────────┐
│                    GITHUB (Beyin)                        │
│                                                         │
│  1. SCANNER ──→ Günlük tarama, aday hisseler            │
│       │                                                  │
│  2. SCORER ──→ Her adaya puan ver (teknik + fundamental) │
│       │                                                  │
│  3. SIGNALS.JSON ──→ Finzora bunu okur                  │
│       │                                                  │
│  4. TRACKER ──→ Açık sinyalleri takip et                │
│       │                                                  │
│  5. BACKTESTER ──→ Kapanan sinyalleri test et            │
│       │                                                  │
│  6. AUTOPSY ──→ Neden kazandı/kaybetti analiz et        │
│       │                                                  │
│  7. OPTIMIZER ──→ Parametreleri güncelle                 │
│       │                                                  │
│  └──→ 1'e dön (daha iyi parametrelerle)                 │
│                                                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼ (API / raw JSON)
              ┌────────────────┐
              │    FINZORA      │
              │  signals.json   │
              │  okur, gösterir │
              └────────────────┘
```

## Dosya Yapısı

```
swing-trade/
├── data/
│   ├── signals.json              ← FINZORA BUNU OKUR
│   ├── strategy_params.json      ← Evrimleşen parametreler
│   ├── signal_history.json       ← Tüm geçmiş sinyaller
│   ├── backtest_results.json     ← Geriye dönük test sonuçları
│   ├── lessons_learned.json      ← Öğrenilen dersler
│   ├── param_changelog.json      ← Parametre değişiklik tarihi
│   └── sector_scores.json        ← Güncel sektör puanları
│
├── scripts/
│   ├── scanner.py                ← Günlük hisse tarama
│   ├── signal_tracker.py         ← Açık sinyalleri takip et
│   ├── backtester.py             ← Kapanan sinyalleri test et
│   ├── autopsy.py                ← Sonuç analizi
│   ├── optimizer.py              ← Parametre optimizasyonu
│   └── fmp_client.py             ← FMP API wrapper
│
├── reports/
│   └── weekly_YYYY-MM-DD.md      ← Haftalık analiz raporu
│
└── .github/workflows/
    ├── daily_scan.yml            ← Her gün 11:30 UTC
    └── weekly_review.yml         ← Her Pazar
```

## signals.json Formatı (Finzora'nın Okuduğu)

```json
{
  "updated_at": "2026-02-18T11:30:00Z",
  "market_regime": "BULLISH",
  "active_signals": [
    {
      "id": "SIG-20260218-AVGO",
      "symbol": "AVGO",
      "strategy": "PULLBACK",
      "action": "BUY",
      "entry_price": 325.00,
      "stop_loss": 308.75,
      "target_1": 350.00,
      "target_2": 375.00,
      "trailing_stop_pct": 5.0,
      "confidence": 8,
      "max_hold_days": 15,
      "sector": "Technology",
      "thesis": "AI capex güçlü, EMA stack sağlam, RSI 45 pullback",
      "generated_at": "2026-02-18",
      "expires_at": "2026-02-20"
    }
  ],
  "watching": [...],
  "recently_closed": [...]
}
```

## Öğrenme Döngüsü Detayı

### Adım 1: Sinyal Üret (scanner.py)
- FMP API'den fiyat/hacim/teknik veri çek
- Pullback ve Breakout filtrelerini uygula
- Earnings takvimini kontrol et (7 gün içinde olanları ele)
- Sektör RS skorlarını hesapla
- Her adaya composite skor ver
- Top 3-5 sinyali signals.json'a yaz

### Adım 2: Takip Et (signal_tracker.py)
- Açık sinyallerin günlük fiyatını takip et
- Max favorable excursion (MFE) kaydet
- Max adverse excursion (MAE) kaydet
- Stop/target/timeout tetiklenirse kapat
- Kapanan sinyali backtest_results.json'a taşı

### Adım 3: Otopsi (autopsy.py)
Her kapanan sinyal için:
- Giriş kalitesi: RSI, hacim, sektör RS doğru muydu?
- Çıkış kalitesi: Erken mi, geç mi, optimal mi?
- Alternatif senaryolar: Stop %5 yerine %7 olsaydı?
- Benzer trade karşılaştırması

### Adım 4: Optimize Et (optimizer.py)
Minimum 20 kapanmış sinyal birikince:
- Win rate by strategy (pullback vs breakout)
- Win rate by sector
- Win rate by RSI range
- Win rate by market regime
- Optimal stop-loss (MFE/MAE analizi)
- Optimal hold period
→ strategy_params.json güncelle

### Adım 5: Geri Bildirim
Yeni parametrelerle scanner tekrar çalışır.
Parametreler her değiştiğinde param_changelog.json'a kayıt düşer.
```

## Finzora Entegrasyonu

Finzora sadece şu URL'yi okur:
```
https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/swing-trade/data/signals.json
```

Veya GitHub API:
```
GET https://api.github.com/repos/zeynelgun-afk/portfolio-tracker/contents/swing-trade/data/signals.json
```

Finzora'nın yapacağı tek şey:
1. signals.json'u periyodik oku
2. active_signals'ı dashboard'da göster
3. Kullanıcı onaylarsa pozisyon aç (entry, stop, target zaten hazır)
