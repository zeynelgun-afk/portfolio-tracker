---
title: Sistem Haritası
description: Tüm Finzora AI bileşenlerinin tam haritası — entry point, 4 mod, akış, modüller arası bağlantı.
tags:
  - architecture
  - system
  - reference
related:
  - "[[Index]]"
  - "[[DECISION_FRAMEWORK]]"
  - "[[OBSERVABILITY]]"
  - "[[RAILWAY_DEPLOY]]"
  - "[[GITHUB_ACTIONS_GUIDE]]"
updated: 2026-05-03
---

# FINZORA AI — SİSTEM HARİTASI

> Oluşturulma: 20 Nisan 2026
> Amaç: Tüm scriptler, workflowlar, data akışı ve tetikleyicilerin tek bakışta görünümü.

---

## 1. TETİKLEYİCİLER VE WORKFLOW'LAR

```
┌─ GITHUB ACTIONS CRON (TR saati, hafta içi) ──────────────────────────────┐
│                                                                          │
│  16:00 ── agent.yml (morning)        → orchestrator.py sabah modu       │
│                                        + macro_intelligence_notify.py   │
│                                                                          │
│  14:00 ── morning_scan.yml           → full_universe_screener.py        │
│                                      → swing_entry_engine.py --watchlist│
│                                      → parse_swing_entry.py             │
│                                      → scan_summary.py                  │
│                                                                          │
│  17:00-23:30 ── agent.yml (monitor, her 30dk)                           │
│                                      → orchestrator.py izleme modu      │
│                                                                          │
│  00:30 ── agent.yml (closing)        → orchestrator.py kapanış modu     │
│                                      → daily_update.py (alt süreç)      │
│                                      → heartbeat.py --mode ozet         │
│                                                                          │
│  12:30 ── adil_deger_panel.yml       → adil_deger_calculator.py         │
│  xx:xx ── swing_adil_deger.yml       → portfoy_adil_deger.py            │
│  xx:xx ── consistency_check.yml      → consistency_check.py --strict    │
│  Sürekli ── telegram_bot.yml         → telegram_bot.py (Railway'de)     │
│  Her commit ── notify-transactions.yml                                  │
│                                                                          │
│  Pazar 12:00 ── agent.yml (weekly)   → orchestrator.py haftalık mod     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. SABAH AKIŞI (morning mode, TR 16:00)

```
agent.yml tetiklenir
   │
   ├─► RAG index güncelle (scripts/rag/indexer.py)
   │      Voyage AI → ChromaDB chroma/
   │
   ├─► orchestrator.py collect_context("morning")
   │      │
   │      ├─ run_regime_detection()            → agent/memory/market_regime.json
   │      ├─ run_macro_intelligence(vix)       → data/macro_intelligence.json
   │      │     └─ _update_k13_matrix_if_changed() → data/k13_crisis_matrix.json
   │      │        (histerezis: 2 gün üst üste)
   │      ├─ find_candidates() (opportunity_finder) → buy_list
   │      ├─ build_research_context()          (FMP news + macro + earnings + insider)
   │      ├─ build_twitter_context()           (9 hesap RapidAPI)
   │      ├─ build_risk_context()              (portföy ağırlık, pozisyon sayısı)
   │      ├─ get_portfolio_news(24h)           → LLM context
   │      ├─ build_thematic_context()          (thematic_calendar)
   │      ├─ scan_premarket_gaps()             → data/premarket_gaps.json
   │      └─ run_swing_morning_check()
   │
   ├─► AI Opus 4.6 (claude_agent) sabah analizi
   │      → reports/daily/DAILY_SABAH_YYYY-MM-DD.md
   │
   └─► macro_intelligence_notify.py
          → Zeynel DM: dominant tema + kriz + önerilen hisseler
```

---

## 3. SEANS İÇİ İZLEME (monitor mode, her 30 dk)

```
agent.yml tetiklenir
   │
   ├─► orchestrator.py collect_context("monitor")
   │      ├─ Portföy pozisyon kontrolü
   │      ├─ Stop-loss yakınlık (k09_proximity_check)
   │      ├─ get_portfolio_news(4h) (hızlı bağlam)
   │      └─ Session state oku → buy_list
   │
   └─► AI değişiklik tespit ederse:
          → execution_engine → data/transactions.csv
          → telegram_notify.py --type action (GRUP)
```

---

## 4. KAPANIŞ AKIŞI (closing mode, TR 00:30)

```
agent.yml tetiklenir
   │
   ├─► orchestrator.py collect_context("closing")
   │      ├─ daily_update.py alt süreç (fiyat + ATR stop güncelle)
   │      ├─ run_auto_feedback() → trade_feedback.py
   │      │     Kapanan trade'leri AI ile analiz, closed.json lessons
   │      ├─ score_pending_predictions() → prediction_log.json
   │      └─ Darwin evrim kontrolü (5 işlem gününde 1)
   │
   ├─► AI Opus 4.6 kapanış raporu
   │      → reports/daily/DAILY_KAPANIS_YYYY-MM-DD.md
   │
   └─► heartbeat.py --mode ozet (gün özeti DM)
```

---

## 5. VERİ DOSYALARI VE SAHİPLİKLERİ

### Portföy (CANONICAL — tek kaynak)
```
data/portfolios/aggressive.json    ← execution_engine, orchestrator
data/portfolios/balanced.json      ← execution_engine, orchestrator
data/portfolios/dividend.json      ← execution_engine, orchestrator
data/transactions.csv              ← TEK işlem kaynağı
data/swing/active.json             ← swing_manager
data/swing/closed.json             ← swing_manager + trade_feedback
data/swing/watchlist.json          ← swing_entry_engine
```

### Runtime state
```
data/macro_intelligence.json       WRITE: macro_intelligence.py (sabah)
                                   READ: tema_portfolio_tracker, notify script
data/k13_crisis_matrix.json        WRITE: macro_intelligence._update_k13
                                   READ: k_rules_common, k_engine
data/k13_pending_change.json       WRITE: macro_intelligence (histerezis state)
data/vix_cache.json                WRITE/READ: agent/vix_fetcher.py
agent/memory/market_regime.json    WRITE: regime_detector.py
                                   READ: conviction_scorer, vb.
data/premarket_gaps.json           WRITE: premarket_gap_scanner
                                   READ: orchestrator
data/swing_entry_signals.json      WRITE: parse_swing_entry.py
                                   READ: swing_manager, orchestrator
data/buy_candidates.json           WRITE: opportunity_finder
                                   READ: orchestrator session state
data/watchlist.json                WRITE: watchlist_manager (7g cooldown)
                                   READ: session_state, daily_scan
data/daily_full_scan.json          WRITE: full_universe_screener
data/daily_scan_{aggr,bal,div}.json WRITE: full_universe_screener, scan_summary
data/summary.json                  WRITE: daily_update (günlük)
```

### Gözlemlenebilirlik
```
logs/events.jsonl                  WRITE: agent/observability.py (git-tracked)
data/finzora.db                    WRITE: observability (gitignored)
data/rag/chroma/                   WRITE: scripts/rag/indexer.py (gitignored)
```

---

## 6. AGENT MODÜL HARİTASI (agent/)

```
orchestrator.py ────────────────────── Ana orkestratör (entry point)
   │
   ├─ claude_agent.py                 Anthropic API wrapper
   ├─ tools.py                        Yardımcı fonksiyonlar (portföy oku, haber)
   ├─ memory_manager.py               Kapsam bağlamı üret
   ├─ fmp_client.py                   FMP API çağrıları (observability loglar)
   │
   ├─ macro_intelligence.py           ⭐ TEK TEMA KAYNAĞI (AI tespit)
   ├─ regime_detector.py              Piyasa rejimi (BOGA/AYI/KRIZ/CHOP/TREND)
   ├─ vix_fetcher.py                  VIX cache + fallback zinciri
   │
   ├─ opportunity_finder.py           Tema → hisse arama
   ├─ swing_manager.py                Swing pozisyon yönetimi
   ├─ execution_engine.py             Alım/satım kararını uygula, CSV'ye yaz
   ├─ risk_engine.py                  Risk context (pozisyon, ağırlık)
   │
   ├─ conviction_scorer.py            5 bileşen 0-100 güven skoru
   ├─ tema_portfolio_tracker.py       Tema × portföy P&L matrisi
   ├─ thematic_calendar.py            Tematik katalist takvim
   │
   ├─ web_researcher.py               FMP haber + earnings + insider
   ├─ twitter_monitor.py              9 hesap tweet sinyali (RapidAPI)
   ├─ sector_cache.py                 Sektör haritası cache
   │
   ├─ learning_engine.py              Trade ders çıkarım, K-kural istatistik
   ├─ trade_feedback.py               Post-trade otomatik analiz
   ├─ prediction_logger.py            Tahmin doğruluk takibi
   ├─ backtester.py                   Strateji backtest motor
   │
   ├─ darwin_evolution.py             Kural evrim (5 gün test)
   ├─ prompt_evolver.py               Prompt versiyon evrimi
   ├─ rule_updater.py                 PLAYBOOK parametre güncelleme
   ├─ screener_optimizer.py           Screener eşik optimizasyon
   │
   ├─ adversarial_debate.py           Bull/Bear/Risk 3 ajan tartışma
   ├─ specialist_agents.py            Uzman ajan yönlendirme
   ├─ multi_cohort.py                 Çoklu kohort test
   │
   ├─ observability.py                Event log + metrics
   ├─ dry_run_manager.py              Gerçek para kullanmadan test
   └─ k_engine.py                     K-kural motoru
```

---

## 7. SCRIPT HARİTASI (scripts/)

### Aktif (workflow + import bağlı)
```
orchestrator entry:
  full_universe_screener.py          morning_scan.yml
  swing_entry_engine.py              morning_scan.yml
  parse_swing_entry.py               morning_scan.yml
  scan_summary.py                    morning_scan.yml
  daily_update.py                    orchestrator closing subprocess
  macro_intelligence_notify.py       agent.yml morning post-step
  heartbeat.py                       agent.yml closing post-step
  consistency_check.py               consistency_check.yml
  event_logger.py                    agent.yml failure handler
  adil_deger_calculator.py           adil_deger_panel.yml
  portfoy_adil_deger.py              swing_adil_deger.yml
  telegram_notify.py                 çok yerden çağrılıyor
  telegram_bot.py                    Railway daemon
```

### Portföy ve swing tarama (aktif)
```
portfolio_scan_aggressive.py + common + balanced + dividend
swing_full_universe.py
swing_ichimoku.py + swing_technical.py
watchlist_manager.py
premarket_gap_scanner.py
risk_panel_generator.py
```

### K-kural yardımcıları (aktif, k_rules_common üzerinden)
```
k09_proximity_check.py               Stop yakınlık
k15b_dilution_check.py               Hisse seyreltme
k16_sell_the_news_score.py           Sell-the-news skoru
k17_correlation_check.py             Korelasyon
k19_xlp_filter.py                    XLP swing yasağı
k20_rs_filter.py                     RS dead cat bounce
k_rule_performance.py                K-kural başarı ölçümü
k_rules_common.py                    Ortak yardımcı (merkezi)
```

### Gözlem ve istatistik (aktif, manuel)
```
finzora_stats.py                     CLI istatistik
trade_memory.py                      TF-IDF trade belleği
```

### Arşiv (tek seferlik migrasyonlar)
```
_backfill_observability.py           Yapıldı, saklı
_cleanup_secrets.py                  Yapıldı, saklı
_migrate_portfolio_schema.py         Yapıldı, saklı
_migrate_swing_schema.py             Yapıldı, saklı
_merge_events_jsonl.py               agent.yml artifact merge için aktif
```

### Konfigürasyon
```
_config.py                           Script-seviyesinde env_key + path
```

### RAG
```
scripts/rag/indexer.py               Voyage AI → ChromaDB
scripts/rag/embedder.py              Embed yardımcı
```

---

## 8. TELEGRAM YÖNLENDİRME

```
GRUP (chat_id -1003827034395):
  • Alım/satım aksiyonları (telegram_notify --type action)
  • Açılış/kapanış raporu (type premarket/closing)
  • Günlük özet (type daily)
  • Winners vitrini (type winners)
  • Risk paneli görseli (type photo)

ZEYNEL DM (chat_id 1403072107):
  • Sistem bakım/bugfix/denetim (type custom, default DM)
  • Acil uyarı (type alert, default DM)
  • K-script critical/warning (send_k_alert)
  • Macro intelligence günlük özet (macro_intelligence_notify.py)
  • Commit bildirimleri (notify-transactions.yml)
  • Heartbeat ozet (heartbeat.py)
```

---

## 9. DIŞ BAĞIMLILIKLAR

```
FMP API            financialmodelingprep.com/stable (2,500 req/min unlimited)
Anthropic API      claude-opus-4-6 (orchestrator, macro_intelligence)
Voyage AI          voyage-3-lite (RAG embedding, TEK model — dim 512)
ChromaDB           data/rag/chroma (local, rebuildable)
RapidAPI           twitter241 (twitter_monitor.py)
Twitter OAuth      finzora2 (içerik paylaşımı, pay-per-use)
Telegram Bot API   finzora AI bot (token env)
Meta Graph API     Instagram publish (account 17841444988981487)
```

---

## 10. 20 NİSAN 2026 TEMİZLİĞİ (ref)

```
SILINDI (toplam ~5,500 satır):
  scripts/sentiment_engine.py        Ölü sistem, orchestrator okumuyordu
  scripts/intraday_morning_scan.py   morning_scan.yml ile değiştirilmiş
  scripts/multi_agent_debate.py      agent/adversarial_debate.py ile değiştirilmiş
  scripts/market_regime.py           agent/regime_detector.py ile değiştirilmiş
  scripts/weekly_health_check.py     Şubat'tan beri dokunulmamış
  scripts/memory_update.py           trade_memory + memory_manager karşılıyor
  scripts/alpha_screener.py          portfolio_scan_* ile değiştirilmiş
  scripts/free_alpha_data.py         alpha_screener bağımlısıydı
  scripts/auto_trade_review.py       agent/trade_feedback.py ile değiştirilmiş
  scripts/walk_forward_backtest.py   agent/backtester.py ile değiştirilmiş
  scripts/session_watchlist_scan.py  Kullanılmıyordu
  agent/theme_manager.py             macro_intelligence tek kaynak olduğu için

DATA:
  data/sentiment_scores.json, data/theme_scores.json
  data/agent_debate_results.json, data/theme_stock_candidates.json
  data/alpha_scan_aggressive.json
  agent/memory/theme_scores.json, agent/memory/theme_weekly_reviews.json

WORKFLOW:
  .github/workflows/weekly_theme_review.yml

BUG DÜZELTMELERİ:
  orchestrator _load_alpha_scan_context() kaldırıldı — AI 9 gündür stale
  EKLE listesi görüyordu, kapandı.
  tema_portfolio_tracker repoint edildi → data/macro_intelligence.json
  conviction_scorer fallback dead kodu temizlendi

YENİ:
  scripts/macro_intelligence_notify.py (her sabah DM)
  agent.yml morning post-step bağlantısı
```
