# Finzora AI — Otonom Portföy Yönetim Sistemi

> **Başlangıç:** 17 Şubat 2026 | **Sermaye:** $600,000 | **Yönetim:** Finzora AI (otonom)

Finzora AI, ABD borsasında üç portföyü ve bir swing trade hesabını otonom olarak yöneten Claude tabanlı yapay zeka sistemidir. GitHub Actions üzerinde her 30 dakikada bir çalışır; fiyat takibi, stop-loss izleme, sinyal tarama ve işlem kararlarını insan müdahalesi olmadan gerçekleştirir.

---

## Portföy Yapısı

| Portföy | Sermaye | Güncel Değer | Pozisyonlar | Strateji |
|---------|---------|-------------|-------------|----------|
| **Dengeli** | $100K | ~$112K | MO*, DUK, CI, NEE | Multi-sector value + defansif |
| **Agresif** | $400K | ~$362K | COHR, VRT, ANET, MU, CAMT | AI tedarik zinciri tematik |
| **Temettü** | $100K | ~$143K | T, VZ, MO, MRK, OKE | Yüksek temettü + değer |
| **Swing** | — | — | CAT, KLAC, AMAT | Ichimoku 4/4 momentum |

*MO Dengeli'den satılacak — Pazartesi açılışı*  
**Toplam sistem değeri:** ~$617,542

---

## Dosya Yapısı

```
finzora-ai/
│
├── agent/                          # Otonom karar motoru
│   ├── orchestrator.py             # Ana orkestratör — sabah/seans/kapanış/haftalık
│   ├── execution_engine.py         # Portföy alım/satım executor
│   ├── claude_agent.py             # Anthropic API bağlantısı
│   ├── swing_manager.py            # Swing trade yönetimi
│   ├── k_engine.py                 # K-kuralları otomatik kontrolcü
│   ├── opportunity_finder.py       # Portföy fırsat tarayıcı
│   ├── risk_engine.py              # Risk hesaplama
│   ├── regime_detector.py          # Piyasa rejim tespiti
│   ├── learning_engine.py          # Geçmiş trade'den öğrenme
│   ├── specialist_agents.py        # Çok-ajan analiz (Makro/Sektör/Sinyal/Risk)
│   ├── adversarial_debate.py       # Bull vs Bear otomatik tartışma
│   ├── darwin_evolution.py         # Prompt/strateji evrim motoru
│   ├── backtester.py               # Geriye dönük test
│   ├── tools.py                    # FMP + Telegram + veri araçları
│   ├── memory_manager.py           # Token tasarruflu bağlam yönetimi
│   └── memory/                     # Kalıcı agent hafızası
│       ├── market_regime.json      # Aktif piyasa rejimi
│       ├── theme_scores.json       # Tema skorları (1-10, haftalık)
│       ├── k_rules_digest.md       # K-kuralları özeti (agent için)
│       ├── prediction_log.json     # Tahmin kaydı ve doğruluk skoru
│       ├── prompt_genome.json      # Evrimleşen prompt genomi
│       └── specialist_genome.json  # Uzman agent ağırlıkları
│
├── scripts/                        # Yardımcı scriptler
│   ├── daily_update.py             # Saatlik fiyat güncellemesi
│   ├── swing_ichimoku.py           # Ichimoku hesaplama + chandelier trailing
│   ├── swing_entry_engine.py       # Swing sinyal üretici
│   ├── swing_full_universe.py      # ~1100 hisse tam tarama
│   ├── portfolio_scan_aggressive.py
│   ├── portfolio_scan_balanced.py
│   ├── portfolio_scan_dividend.py
│   ├── risk_panel_generator.py     # Günlük risk paneli PNG → Telegram
│   ├── telegram_notify.py          # Telegram bildirimleri
│   ├── watchlist_manager.py        # İzleme listesi (7 gün cool-down)
│   ├── k09_proximity_check.py      # Stop yakınlık 4-kontrol
│   ├── k15b_dilution_check.py      # Momentum hisse dilüsyon skoru
│   ├── k16_sell_the_news_score.py  # Earnings öncesi skor
│   ├── k17_correlation_check.py    # Korelasyon + tema çakışma
│   ├── k19_xlp_filter.py           # XLP swing girişi yasağı
│   ├── k20_rs_filter.py            # RS dead cat bounce filtresi
│   ├── alpha_screener.py           # FMP hisse tarayıcı (aggressive/dividend/swing)
│   ├── consistency_check.py        # Veri tutarlılık kontrolü
│   ├── sentiment_engine.py         # Haber duygu analizi
│   ├── premarket_gap_scanner.py    # Pre-market gap fırsatları
│   ├── auto_trade_review.py        # Trade sonrası otomatik analiz
│   ├── walk_forward_backtest.py    # Walk-forward backtest
│   └── consolidate_portfolios.py   # DEVRE DIŞI — ghost portföy oluşturur
│
├── data/                           # Canlı veri
│   ├── portfolios/
│   │   ├── aggressive.json         # ← CANONICAL
│   │   ├── balanced.json           # ← CANONICAL
│   │   └── dividend.json           # ← CANONICAL
│   ├── swing/
│   │   ├── active.json             # Açık swing pozisyonları (max 8)
│   │   ├── closed.json             # Kapanan trade'ler + dersler
│   │   ├── status.json             # Sistem durumu
│   │   └── watchlist.json          # Swing izleme listesi
│   ├── transactions.csv            # Tüm işlem geçmişi (TEK KAYNAK)
│   ├── watchlist.json              # Portföy izleme listesi
│   ├── daily_full_scan.json        # ~1100 hisse tarama sonuçları
│   ├── daily_scan_{aggressive,balanced,dividend}.json
│   ├── alpha_scan_aggressive.json
│   ├── summary.json
│   └── episodic_memory/            # Agent uzun dönem hafıza
│
├── docs/                           # Strateji belgeleri
│   ├── K_RULES_QUICK_REF.md        # ⭐ K-kuralları tek kaynak
│   ├── TRADING_PLAYBOOK.md         # ⭐ Tam strateji kitabı
│   ├── SWING_SYSTEM_V2.md          # Swing sistem v2.3
│   ├── AGGRESSIVE_V2_THESIS.md     # AI tedarik zinciri tezi
│   └── prompts/                    # Seans prompt şablonları
│
├── reports/
│   ├── daily/                      # SABAH / SWING / PORTFOY / KAPANIS
│   └── weekly/                     # WEEKLY_YYYY-MM-DD
│
├── outputs/risk_panel/             # Günlük risk paneli PNG
│
└── .github/workflows/
    ├── agent.yml                   # ⭐ Ana agent (her 30dk, piyasa saatlerinde)
    ├── daily_update.yml            # Saatlik fiyat güncellemesi
    ├── morning_scan.yml            # Sabah tarama
    ├── consistency_check.yml       # Veri tutarlılık
    ├── weekly_theme_review.yml     # Haftalık tema gözden geçirme
    └── notify-transactions.yml     # İşlem bildirimi
```

---

## Otomasyon Mimarisi

```
GitHub Actions (zamanlanmış)
        │
        ▼
agent/orchestrator.py
        │
        ├── Sabah  (16:00 TR)   → Makro analiz + fırsat tarama + günün planı
        ├── Seans  (her 30 dk)  → Stop izleme + sinyal tarama + execution
        ├── Kapanış (00:30 TR)  → P&L raporu + dersler + veri güncelleme
        └── Haftalık (Pazar)    → Tema skoru + rejim + kural gözden geçirme
                │
                ├── execution_engine.py → portfolios/*.json günceller
                ├── swing_manager.py    → swing/active.json günceller
                ├── k_engine.py         → K-kuralları + Telegram uyarı
                └── telegram_notify.py  → Zeynel'e bildirim
```

---

## Canonical Veri Kaynakları

| Veri | Dosya | Yazar |
|------|-------|-------|
| Portföy pozisyonları | `data/portfolios/{aggressive,balanced,dividend}.json` | Agent + Manuel |
| Tüm işlemler | `data/transactions.csv` — 7 sütun: `date,action,symbol,shares,price,total,reason` | Agent + Manuel |
| Swing pozisyonlar | `data/swing/active.json` | Agent (otomatik) |
| Swing geçmişi | `data/swing/closed.json` | Agent (otomatik) |
| Agent hafızası | `agent/memory/*.json` | Agent (otomatik) |

> `data/session_state.json` geçici, `.gitignore`'da — commit'lenmez.

---

## K-Kural Sistemi

Aktif 17 kural. Tam referans: `docs/K_RULES_QUICK_REF.md`

| Kategori | Kurallar |
|----------|----------|
| Giriş filtreleri | K-02, K-04, K-05, K-13 v4.1, K-13b, K-15a, K-15b, K-17, K-19, K-20 |
| Çıkış disiplini | K-06, K-07, K-09, K-ZST, K-EVR, K-ATR |
| Portföy yönetimi | K-10, K-11 v3, K-12, K-16 |

Kaldırılan: K-01, K-03, K-08, K-14 (psikoloji testi ile değiştirildi), K-18 (backtest ters sonuç)

---

## Ortam Değişkenleri (GitHub Secrets)

| Secret | Kullanım |
|--------|----------|
| `ANTHROPIC_API_KEY` | Claude API — karar motoru |
| `FMP_API_KEY` | Financial Modeling Prep — fiyat ve temel veri |
| `TELEGRAM_TOKEN` | Finzora AI bot bildirimleri |
| `TELEGRAM_PRIVATE_CHAT` | Zeynel'e özel chat ID |
| `RAPIDAPI_KEY` | Twitter monitoring |

---

## Önemli Teknik Notlar

- **VIX proxy:** VIXY/UVXY kullanılmaz. VIX için web_search ("CBOE VIX current").
- **Stop alanı:** `stop_loss` canonical. `zarar_kes` tüm JSON'lardan kaldırıldı (12 Nisan 2026).
- **Maliyet alanı:** `maliyet_baz` canonical. `maliyet_bazis` kaldırıldı (12 Nisan 2026).
- **Ghost portföyler:** `growth.json` ve `income.json` archived (12 Nisan 2026). Canonical: aggressive / balanced / dividend.
- **Psikoloji testi:** Her swing girişi öncesi — "Bu girişi yarın tekrar inceleseydim, tüm kuralları tam uyguladım mı?"
- **FMP limit:** 2,500 çağrı/gün. Sadece `/stable/` endpoint (v3/v4 kapalı).
- **Chandelier stop:** 3×ATR(14) trailing, sadece yukarı çekilir. `stop_loss` > `chandelier_stop` ise `stop_loss` aktif seviyedir.

---

*Son güncelleme: 12 Nisan 2026 | Finzora AI*
