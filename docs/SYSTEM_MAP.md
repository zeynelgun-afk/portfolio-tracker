---
title: Sistem Haritası
description: Finzora AI'nın tüm bileşenleri — Railway scheduler, modüller, veri akışı, dosya organizasyonu.
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
updated: 2026-05-17
---

# FINZORA AI — SİSTEM HARİTASI

> Son güncelleme: 17 Mayıs 2026 (Faz 1 ✅ + Faz 2 Adım 5-9 ✅ + Adım 10a-b-i ✅ + whitelist v2 gerçek slug ✅)
> **Devam ediyor:** [[PHASE2_SCANNER_CONSOLIDATION]] — Faz 2 Adım 10b-ii (scanner pipeline hook), 10b-iii (AI Gate prompt), 11-13 beklemede
> Amaç: Tüm scriptler, scheduler thread'leri, veri akışları ve dosya organizasyonunun tek bakışta görünümü.
>
> **Kritik dönüşüm:** 13 Mayıs 2026 — eski 3-portföy + sleeve + thematic + swing sistemi (`data/portfolios/*.json`, `data/swing/active.json`) `data/archive/2026-05-13_pre_simplification/` altına taşındı. Bunun yerine **tek `data/portfolio.json`** (positions[] + closed[]) ve `agent/` v2 modern paketi geldi.

---

## 1. ZAMANLAYICI MİMARİSİ

Finzora AI'nın iki tetikleyici mekanizması vardır:

### 1.1 Railway scheduler (`scripts/telegram_bot.py`)

`telegram_bot.py` 7/24 Railway'de çalışır. Ana iş polling (kullanıcı komutları) + arka planda 4 daemon thread:

| Thread | Görev | Frekans |
|--------|-------|---------|
| `AylikMakro` | `macro_calendar_updater.py` çağırır | Her ayın 1'i, 09:00 TR |
| `WorkflowZamanlayici` | `_GH_ZAMANLAMALAR` listesindeki workflow'ları doğru saatte GitHub Actions API üzerinden tetikler. DST-aware (`nyse_relative=True` olanlar kışın +1 saat ötelenir) | Dakika başı kontrol |
| `RiskPanelZamanlayici` | `risk_panel_generator.py` ile günlük PNG üretir + Telegram grubuna gönderir | Hft 09:30 TR |
| `AnalistTakipZamanlayici` | `agent/legacy/analist_takip/monitor.py` çağırır (revize polling + drift filter) | Dakika başı (modülün kendi saat kontrolü) |

### 1.2 GitHub Actions workflow'ları

`.github/workflows/` altında — Workflow Zamanlayıcı thread'i tarafından `workflow_dispatch` ile tetiklenir.

**Aktif workflow'lar (`.yml`):**
- `news_radar.yml`, `adil_deger_panel.yml`, `agent.yml`, `thematic_discovery.yml`, `research_tracker.yml`, `signal_tracker.yml`, `ai_orchestrator.yml`, `consistency_check.yml`, `signal_broadcaster.yml`, `macro_calendar.yml`, `log_rotation.yml`, `weekly_fmp_stats.yml`, `notify-transactions.yml`, `manual_telegram.yml`, `telegram_bot.yml`

**Arşivlenmiş workflow'lar (`.yml.legacy`):**
- `morning_scan.yml.legacy`, `result_tracker.yml.legacy`, `swing_adil_deger.yml.legacy`, `adil_deger_weekly.yml.legacy`, `calendar_notifier.yml.legacy`, `agent.yml.legacy`

### 1.3 Workflow zamanlama tablosu

NYSE DST aktif (Mart-Kasım, YAZ) varsayımıyla:

| Saat TR | Gün | Workflow | Mod | Açıklama |
|---------|-----|----------|-----|----------|
| 09:00 | Hft | news_radar.yml | — | Haber Radarı |
| 09:30 | Hft | (Railway thread) | — | Günlük Risk Paneli (PNG → grup) |
| 12:30 | Hft | adil_deger_panel.yml | — | Adil Değer Paneli (portföy + watchlist + %25+ keşif) |
| 16:00 | Hft | agent.yml | morning | Sabah raporu |
| 17:00–23:30 | Hft | agent.yml | monitor | Her 30 dk pozisyon izleme |
| 23:00 | Hft | thematic_discovery.yml | daily | Tematik tarama |
| 23:35 | Her gün | research_tracker.yml | daily | v5.0 Etap 11 — gün sonu araştırma takibi |
| 23:45 | Hft | signal_tracker.yml | — | Sinyal performans takibi (7g/14g/30g checkpoint) |
| 00:30 | Sal-Cmt | agent.yml | closing | Kapanış raporu (önceki gün hft idiyse) |
| 02:00 | Sal-Cmt | ai_orchestrator.yml | daily | AI orchestrator gün sonu sentezi |
| 11:00 | Pzr | thematic_discovery.yml | weekly | Haftalık tematik tarama |
| 12:00 | Pzr | agent.yml | weekly | Haftalık rapor |
| 13:00 | Pzr | ai_orchestrator.yml | weekly | Haftalık derin AI analizi |
| 14:00 | Pzr | research_tracker.yml | weekly | Haftalık araştırma özeti |
| 19:00 | Pzr | signal_tracker.yml | sunday | Haftalık sinyal DM raporu |
| Ay 1'i 09:00 | — | (Railway thread) | — | Makro takvim ICS güncelle |

DST geçişinde `nyse_relative=True` olan satırlar (Agent Sabah, Agent Kapanış, AI Orchestrator Günlük, Research Tracker Günlük) kışın +1 saat ötelenir.

---

## 2. KLASÖR HARİTASI

```
portfolio-tracker/
├── agent/                   # v2 modern Python paketi (13 May 2026 sonrası)
│   ├── __init__.py
│   ├── ai_gate.py           # LLM tabanlı watchlist sinyal değerlendirici (Aşama 8)
│   ├── fmp.py               # FMP stable endpoint client (canonical, self-contained)
│   ├── monitor.py           # Pozisyon + risk monitor (K-13, K-23, STOP, MOVE alertleri)
│   ├── portfolio.py         # data/portfolio.json CRUD + FMP fiyat zenginleştirme + metrics
│   ├── telegram.py          # Türkçe Telegram mesajları (grup + DM)
│   ├── themes.py            # Tema kataloğu CRUD (data/themes.json)
│   ├── watchlist.py         # Watchlist CRUD (data/watchlist.json, limit 300)
│   │
│   ├── reports/             # Rapor üreticileri
│   │   ├── morning.py       # Sabah raporu (16:00 TR)
│   │   ├── closing.py       # Kapanış raporu (00:30 TR)
│   │   ├── weekly.py        # Haftalık rapor (Pzr 12:00)
│   │   ├── research.py      # Adil Değer takibi (23:35 daily / Pzr 14:00 weekly) [Faz 1, 17 May 2026]
│   │   └── stats.py         # Observability/FMP istatistik raporu [Faz 1, 17 May 2026]
│   │
│   ├── scanners/            # Scanner paketi [Faz 2, 17 May 2026]
│   │   ├── base.py          # BaseScanner ABC + Candidate dataclass
│   │   ├── thematic.py      # ← scripts/thematic_discovery.py [Adım 5 ✅]
│   │   ├── fair_value.py    # ← scripts/fair_value_panel.py [Adım 6 ✅]
│   │   ├── news.py          # ← scripts/news_radar.py [Adım 7 ✅]
│   │   ├── analyst_revisions.py  # ← legacy/analist_takip/monitor.py [Adım 8 ✅ — adaptör, kaynak yerinde]
│   │   └── calibrator.py    # Polymarket kalibratör [Adım 9 ✅]
│   │
│   ├── polymarket.py        # Gamma API client [Faz 2, 17 May 2026]
│   │
│   └── legacy/              # Eski sistemin arşivi (~50 dosya)
│       ├── analist_takip/   # AKTIF — analist revize polling alt sistemi
│       │   ├── config.py            # PORTFOLIO_FILES, threshold'lar, FMP_BASE
│       │   ├── monitor.py           # Ana tick fonksiyonu
│       │   ├── revision_fetcher.py  # FMP 3 endpoint polling
│       │   ├── signal_analyzer.py   # STRONG_BUY/BUY/SELL skorlayıcı
│       │   ├── state_tracker.py     # Drift filter, processed_revisions.jsonl
│       │   ├── watchlist.py         # ~150-300 ticker (portföy + son 14g bilanço)
│       │   ├── telegram_helpers.py  # DM formatlayıcı
│       │   ├── dm_notifier.py       # DM gönderici
│       │   ├── dm_settings.py       # /sessizmod, /sinyal preset ayarları
│       │   └── performance_tracker.py # Sinyal performans takibi
│       │
│       ├── llm_client.py    # AKTIF — news_radar.py kullanır (Kimi via OpenRouter)
│       │
│       ├── k_engine.py            # ARŞIV — eski K-kural motoru
│       ├── claude_agent.py        # ARŞIV — eski Claude orchestrator
│       ├── swing_manager.py       # ARŞIV — eski swing trade yöneticisi
│       ├── opportunity_finder.py  # ARŞIV
│       ├── execution_engine.py    # ARŞIV — transactions.csv yazıcı
│       ├── memory_manager.py      # ARŞIV
│       ├── observability.py       # ARŞIV — events.jsonl yazıcı
│       ├── exit_judgement.py      # ARŞIV
│       ├── conviction_scorer.py   # ARŞIV
│       ├── fmp_client.py          # ARŞIV — agent/fmp.py'nin öncülü
│       ├── vix_fetcher.py         # ARŞIV
│       ├── web_researcher.py      # ARŞIV
│       ├── darwin_evolution.py    # ARŞIV
│       ├── valuation/             # ARŞIV — eski adil değer modülü
│       │   └── methods/           # 9 yöntem implementasyonları (skill'e taşındı)
│       └── ... (diğer arşiv dosyaları)
│
├── scripts/                 # Çalıştırılabilir görev scriptleri
│   ├── telegram_bot.py      # ANA — Railway scheduler + bot polling + 4 thread
│   ├── news_radar.py        # → SHIM (Faz 2 Adım 7): agent/scanners/news.py'ya yönlendiriyor
│   ├── fair_value_panel.py  # → SHIM (Faz 2 Adım 6): agent/scanners/fair_value.py'ya yönlendiriyor
│   ├── research_tracker.py  # → SHIM (Faz 1, 17 May 2026): agent/reports/research.py'ya yönlendiriyor
│   ├── signal_tracker.py    # 23:45 / Pzr 19:00 — sinyal performans (7/14/30 gün checkpoint)
│   ├── thematic_discovery.py # → SHIM (Faz 2 Adım 5): agent/scanners/thematic.py'ya yönlendiriyor
│   ├── ai_orchestrator.py   # 02:00 / Pzr 13:00 — gün sonu / haftalık AI sentez (Aşama 5)
│   ├── signal_broadcaster.py # Aşama 6 — sinyalleri grup/DM'e yayma
│   ├── risk_panel_generator.py # Günlük PNG (8 varlık, 1080×1920) → grup
│   ├── macro_calendar_updater.py # Ayın 1'i — ICS üretip GitHub'a push
│   ├── telegram_notify.py   # Genel Telegram bildirim aracı
│   ├── thesis_erosion.py    # Tez bozulması alarmı
│   ├── weekly_pre_check.py  # Haftalık rapor öncesi doğrulama
│   ├── consistency_check.py # K-kural tutarsızlık tarayıcı
│   ├── heartbeat.py         # Günlük sistem sağlık özeti
│   ├── event_logger.py      # Merkezi olay kaydı
│   ├── log_rotation.py      # events.jsonl arşivleme
│   ├── swing_ichimoku.py    # Ichimoku swing tarayıcı (ad-hoc)
│   ├── thematic_discovery.py # Tema keşfi
│   ├── theme_tracker.py     # Tema durum takibi
│   ├── portfolio_drawdown_guard.py # K-23 drawdown koruma
│   ├── portfolio_pacing.py  # Yıllık hedef vs gerçek getiri kıyaslama
│   ├── cash_deployment_engine.py # K-22 nakit kullanım (legacy ref'li, kullanım sınırlı)
│   ├── catalyst_compute_returns.py # Catalyst sonrası getiri hesaplama
│   ├── daily_update.py      # Eski günlük güncelleyici (legacy bağlam)
│   ├── finzora_stats.py     # → SHIM (Faz 1, 17 May 2026): agent/reports/stats.py'ya yönlendiriyor
│   ├── k12_dynamic_limits.py # K-12 dinamik limitler (legacy)
│   ├── k_rules_backtest.py  # K-kural backtest aracı
│   ├── k_rules_common.py    # K-kural ortak fonksiyonları
│   ├── macro_intelligence_notify.py # Makro intel DM
│   ├── migrate_2026_05_13.py # Simplification migration scripti
│   ├── split_sabah_report.py # Sabah rapor bölme aracı
│   ├── watchlist_manager.py # Watchlist yönetim CLI (eski; modern: `python -m agent.watchlist`)
│   ├── _config.py           # Ortak config
│   ├── _cleanup_secrets.py  # Secrets temizleme
│   ├── _merge_events_jsonl.py # events.jsonl birleştirici
│   │
│   ├── rag/                 # RAG (Voyage AI + ChromaDB) alt sistemi
│   │   ├── embedder.py      # Voyage AI embedding
│   │   ├── indexer.py       # ChromaDB indeksleyici
│   │   ├── retriever.py     # RAG sorgu
│   │   └── claude_with_context.py # Claude'a context enjekte
│   │
│   ├── _archive/            # Arşivlenmiş scriptler
│   └── legacy/              # Legacy scriptler (workflow'lardan çıkarıldı)
│
├── data/                    # Veri katmanı (JSON + CSV)
│   ├── portfolio.json       # ★ AKTİF TEKİL — positions[] + closed[]
│   ├── watchlist.json       # ★ Watchlist (limit 300, tematik kaynaklar)
│   ├── transactions.csv     # ⚠️ AUDIT LOG — sadece legacy modüller yazar/okur (bkz. §5)
│   ├── themes.json          # Tema kataloğu (agent/themes.py)
│   ├── theme_scores.json    # Tema skorları
│   ├── signal_performance.json # Sinyal tracker çıktısı
│   ├── monitor_state.json   # Monitor alert state (rate-limiting)
│   ├── vix_cache.json       # VIX cache
│   ├── sector_cache.json    # Sektör verisi cache
│   ├── k13_crisis_matrix.json # K-13 kriz matrisi
│   ├── macro_intelligence.json # Makro intelligence verisi
│   ├── news_radar_log.json  # Haber radar log
│   ├── premarket_gaps.json  # Pre-market gap'ler
│   ├── session_state.json   # Seans durumu
│   ├── summary.json         # Genel özet
│   ├── discovery_signals.json # Keşif sinyalleri
│   ├── daily_full_scan.json # Günlük full scan sonuçları
│   ├── daily_scan_aggressive.json  # ARŞIV — eski 3-portföy taraması
│   ├── daily_scan_balanced.json    # ARŞIV
│   ├── daily_scan_dividend.json    # ARŞIV
│   ├── swing_entry_signals.json    # ARŞIV — eski swing girdileri
│   ├── walkforward_results.json    # Walkforward backtest çıktısı
│   ├── backtest_summary.json       # Backtest özetleri
│   ├── k_rules_backtest_results.json # K-kural backtest
│   ├── pacing_summary.json  # Pacing özeti
│   ├── weekly_pre_check.json # Haftalık pre-check çıktısı
│   │
│   ├── analist_takip/       # AnalistTakip durum dosyaları
│   │   ├── signals.jsonl    # Üretilen sinyaller (STRONG_BUY/BUY/SELL)
│   │   ├── processed_revisions.jsonl # İşlenmiş revize ID'leri (drift filter)
│   │   └── dm_settings.json # Kullanıcı DM tercihleri
│   │
│   ├── calendars/           # Makro takvim ICS dosyaları
│   ├── episodic_memory/     # Episodic memory (eski)
│   ├── research/            # Araştırma index
│   │   └── index.json
│   │
│   ├── swing/               # ARŞIV — boş klasör (eski active.json arşive taşındı)
│   │
│   └── archive/             # 13 May 2026 arşivleri
│       ├── 2026-05-13_pre_simplification/
│       │   ├── portfolios/  # Eski balanced/aggressive/dividend.json
│       │   └── swing/       # Eski swing active.json
│       └── 2026-05-13_watchlist_reset/
│
├── docs/                    # Markdown belgeler
│   ├── dashboard.html       # GitHub Pages — Cytoscape.js sistem haritası
│   ├── system_map.json      # Dashboard veri kaynağı
│   ├── SYSTEM_MAP.md        # ★ Bu dosya
│   ├── Index.md             # Doküman indeksi
│   ├── README* / *_SKILL.md / docs/*.md ... (60+ md belge)
│   │
│   ├── archive/             # Arşivlenmiş eski belgeler
│   └── research/            # Araştırma çıktıları
│
├── logs/
│   └── events.jsonl         # Merkezi olay log (gözlemlenebilirlik)
│
├── outputs/
│   └── risk_panel/          # Günlük risk panel PNG'leri (1080×1920)
│
├── reports/                 # Üretilen raporlar
│   ├── daily/               # DAILY_*_SEANS_ONCESI.md / DAILY_*_KAPANIS.md
│   ├── weekly/              # WEEKLY_YYYY-MM-DD.md
│   ├── monthly/             # Aylık raporlar
│   ├── backtest/            # Backtest raporları
│   ├── pacing/              # Pacing raporları
│   └── research/            # Araştırma raporları
│
├── notes/                   # Tarihli geçici notlar
│   ├── 2026-05-13_SIMPLIFICATION.md
│   ├── 2026-05-10_FMP_FOLLOWUP_COMPLETE.md
│   └── ...
│
├── skills/                  # (boş — skill'ler Claude/Anthropic tarafında host'lanır)
├── templates/               # Rapor şablonları (sektor_deep_dive vb.)
├── tests/                   # Test dosyaları (63/63 PASS)
├── valuations/              # Adil değer çıktıları
├── assets/                  # Statik varlıklar (fonts/)
│
├── .github/workflows/       # GitHub Actions workflow YAML'ları (bkz. §1.2)
│
├── README.md
├── Procfile                 # Railway için (web: python scripts/telegram_bot.py)
└── requirements.txt
```

---

## 3. MODERN v2 SİSTEMİ (`agent/`)

`agent/` paketi 13 Mayıs 2026 sonrası yazılmış sade Python katmanıdır. Eski `agent/legacy/` 50+ dosyalı karmaşıklıktan vazgeçildi.

### 3.1 Modüller ve sorumlulukları

| Modül | Sorumluluk |
|-------|-----------|
| `agent.portfolio` | `data/portfolio.json` CRUD; load_portfolio, get_positions, add_position, close_position, portfolio_metrics |
| `agent.fmp` | FMP `/stable/` endpoint client (self-contained, no legacy/_config dependency, 50ms throttle) |
| `agent.monitor` | 30 dakikada bir çağrılır; K-13 (VIX), K-23 (drawdown), STOP (stop yakını), MOVE (anormal hareket) DM alertleri |
| `agent.watchlist` | `data/watchlist.json` CRUD; add/remove/exclude/score, multi-source merge, limit 300 |
| `agent.themes` | `data/themes.json` tema kataloğu; lifecycle (dogus→yukselis→olgun→sönüs→archived) |
| `agent.ai_gate` | Aşama 8 — Watchlist sinyallerini LLM (Kimi) ile değerlendir; EKLE / RED / HATA |
| `agent.telegram` | Türkçe Telegram mesajları (grup -1003827034395 + DM 1403072107) |
| `agent.reports.morning` | Sabah raporu (16:00 TR) |
| `agent.reports.closing` | Kapanış raporu (00:30 TR) |
| `agent.reports.weekly` | Haftalık rapor (Pzr 12:00) |

### 3.2 Hala aktif olan legacy modüller

| Modül | Neden hala aktif |
|-------|-----------------|
| `agent.legacy.analist_takip` (komple submodule) | Analist revize takip sistemi — modern v2'ye taşınmadı. AnalistTakip thread'i bu modülü çağırır. |
| `agent.legacy.llm_client` | `news_radar.py` Kimi LLM çağrısı için kullanıyor (modern alternatif yok) |

Geri kalan `agent/legacy/*.py` (k_engine, claude_agent, swing_manager, opportunity_finder, execution_engine, vb.) **şu an aktif sisteme bağlı değil** — arşiv niteliğinde duruyor.

---

## 4. ANA VERİ AKIŞLARI

### 4.1 Sabah raporu (Hft 16:00 TR)

```
WorkflowZamanlayici thread (telegram_bot.py)
    └→ agent.yml workflow tetikle (mode=morning)
        └→ agent/reports/morning.py
            ├→ agent.portfolio.load_portfolio() ← data/portfolio.json
            ├→ agent.fmp (canlı fiyat enrichment)
            ├→ agent.monitor (alert kontrolü)
            ├→ data/macro_intelligence.json oku
            ├→ data/themes.json + theme_scores.json oku
            └→ reports/daily/DAILY_*_SEANS_ONCESI.md yaz
                + Telegram grubuna gönder
                + GitHub commit + push
```

### 4.2 Kapanış raporu (Sal-Cmt 00:30 TR)

```
WorkflowZamanlayici → agent.yml (mode=closing)
    └→ agent/reports/closing.py
        ├→ FMP quote (gün kapanış fiyatları)
        ├→ Pozisyon P/L hesapla
        ├→ data/portfolio.json güncelle (gerekiyorsa)
        ├→ logs/events.jsonl event yaz
        └→ reports/daily/DAILY_*_KAPANIS.md yaz + Telegram + git push
```

### 4.3 Risk paneli (Hft 09:30 TR)

```
RiskPanelZamanlayici thread (telegram_bot.py)
    └→ scripts/risk_panel_generator.py
        ├→ FMP quote x8 varlık (SPY/QQQ/DIA/IWM + GLD/BTC/BNO/CPER)
        ├→ SMA21 + SMA50 hesapla, 3-level rejim
        └→ outputs/risk_panel/YYYY-MM-DD.png üret
            └→ Telegram grubuna sendPhoto
```

### 4.4 Analist revize takibi (Hft 13:00–01:30 TR)

```
AnalistTakipZamanlayici thread (telegram_bot.py)
    └→ agent.legacy.analist_takip.monitor.analist_takip_tick()
        ├→ watchlist.build_watchlist() — portföy + son 14g bilanço (~150-343 ticker)
        ├→ revision_fetcher (FMP 3 endpoint)
        ├→ signal_analyzer (STRONG_BUY / BUY / SELL threshold)
        ├→ state_tracker (drift filter, processed_revisions.jsonl)
        └→ DM gönder (Zeynel'e) + signals.jsonl yaz
```

### 4.5 Watchlist beslemesi

```
4 besleyici → AI gate (Aşama 8) → data/watchlist.json
─────────────────────────────────────────────────────────
1. analist_takip STRONG_BUY  ┐
2. fair_value_panel %25+     ├→ agent.ai_gate.evaluate_signal()
   analyst target iskonto    │   ├→ LLM (Kimi) kararı: EKLE / RED
3. thematic_discovery        │   └→ data/watchlist.json (limit 300)
4. /ekle manuel komut        ┘

news_radar SADECE OKUR (beslemez).
```

### 4.6 Sinyal performansı (23:45 / Pzr 19:00)

```
WorkflowZamanlayici → signal_tracker.yml
    └→ scripts/signal_tracker.py
        ├→ logs/events.jsonl içinden signal_sent event'leri oku
        ├→ FMP'den 7g/14g/30g sonrası kapanış fiyatları çek
        ├→ data/signal_performance.json güncelle
        └→ Pazar 19:00 → haftalık DM raporu
```

### 4.7 Tematik keşif (23:00 / Pzr 11:00)

```
WorkflowZamanlayici → thematic_discovery.yml
    └→ scripts/thematic_discovery.py
        ├→ Aktif temalar oku (data/themes.json, momentum_score≥70)
        ├→ LLM ile sektör/ticker fırsatları üret
        ├→ AI gate → uygun olanları watchlist'e ekle
        └→ data/discovery_signals.json güncelle
```

---

## 5. `transactions.csv` ARŞİVLENDİ (14 May 2026)

`data/transactions.csv` 17 Şub–12 May 2026 dönemini kapsayan eski tek-işlem-kaydı dosyasıydı (sütunlar: `date, action, symbol, shares, price, total, reason`). 13 Mayıs 2026 simplification ile rolü duplicate hale geldi: `data/portfolio.json` zaten `positions[]` (entry_date/price/shares/reason) ve `closed[]` (+ exit_date/price/reason/pnl) ile tam işlem tarihçesini tutuyor.

**14 May 2026 kararı:** Dosya `data/archive/2026-05-13_pre_simplification/transactions.csv` altına taşındı; dashboard'dan node silindi (44 node, 71 edge). Yeni işlem yazımı YOK — modern v2 sistemi `data/portfolio.json` üzerinden çalışır.

**Geçmiş verisinin durumu:** 290 satır, 36 KB, 17 Şubat 2026 başlangıcından 12 Mayıs 2026'ya kadar tüm alım-satımlar arşivde sağlam korunuyor. K-kural backtest, geçmiş performans analizi gerektiğinde `data/archive/2026-05-13_pre_simplification/transactions.csv` okunabilir.

**Hala arşivde transactions.csv okuyan modüller** (legacy klasöründe, aktif sisteme bağlı değil): `agent/legacy/closing_enrichment.py`, `trade_feedback.py`, `prediction_logger.py`, `darwin_evolution.py`, `tema_portfolio_tracker.py`, `orchestrator.py`, `execution_engine.py`, `swing_manager.py`; `scripts/k_rules_backtest.py` (backtest yapılırsa yol güncellenmeli).

---

## 6. GÖZLEMLENEBİLİRLİK (`logs/events.jsonl`)

Tüm sistemde merkezi olay kaydı. JSONL format, her satır bir event. Tipler:

| Tip | Anlam |
|-----|-------|
| `signal_sent` | Bir sinyal Telegram'a gönderildi |
| `trade` | Gerçekleşmiş alım/satım |
| `alert` | Monitor alert (K-13, K-23, STOP, MOVE) |
| `report` | Rapor üretildi |
| `error` | Hata oluştu |
| `fmp_call` | FMP API çağrısı |
| `workflow_triggered` | GitHub workflow tetiklendi |

`scripts/log_rotation.py` her ayın bitimi tamamlanmış ayları arşivler. RAG sistemi (`scripts/rag/`) bu dosyayı kaynak olarak indeksler.

---

## 7. RAG SİSTEMİ (`scripts/rag/`)

- **Embedding:** Voyage AI (`voyage-3` primary, `voyage-3-lite` fallback, 512 dim, fallback yok dimension mismatch için)
- **Veri tabanı:** ChromaDB local (`data/rag/chroma/`, gitignored)
- **Kaynaklar:** `logs/events.jsonl` + swing closed.json lessons + `docs/*.md`
- **Metadata filter:** symbol / event_type / portfolio
- **Sorgu:** `scripts/rag/claude_with_context.py` Claude API çağrılarına context enjekte eder
- İlk indeks: 231 chunk, ~$0.0004 cost

---

## 8. DASHBOARD (`docs/dashboard.html`)

GitHub Pages'te host'lu, Cytoscape.js ile interaktif sistem grafiği. Veri kaynağı: `docs/system_map.json`.

- 41 node, 65 edge (14 May 2026 itibarıyla)
- Kategoriler: AI Agent (#bc8cff), Data, Script, External API, Workflow
- ID konvansiyonu: dış API'ler `ext.fmp`, `ext.openrouter`, `ext.telegram` (kısa ad değil)
- Yeni edge eklerken target ID node listesinde olmalı, yoksa Cytoscape hata verir

---

## 9. ÖNEMLİ KONVANSİYONLAR

- **Tek `data/portfolio.json`** — 13 May 2026 sonrası tek aktif portföy dosyası
- **Watchlist limit 300** — `data/watchlist.json._limit` (14 May 2026, eski 80)
- **Dil:** Kod ve dosya adları İngilizce, Telegram/chat/commit mesajları Türkçe, ticker İngilizce
- **Telegram routing:** GROUP sadece buy/sell + rapor; DM sistem/maintenance/bugfix
- **K-rules:** Yalnızca K-13 + K-23 otomatik alert; diğer K kuralları (K-19, K-20, K-21, K-ZST) personal discipline (otomatik tetiklenmez)
- **Saat dilimi:** Tüm scheduler'lar TR (Europe/Istanbul); `_TR_TZ` global tanımlı (`scripts/telegram_bot.py`)
- **DST:** `nyse_relative=True` olan zamanlamalar kışın NYSE'ye göre +1 saat ötelenir
- **Bot:** @finzora_ai_bot (token Secrets'ta); kişisel asistan ayrı repo (`zeynelgun-afk/asistan`, @asistan_01_bot)
