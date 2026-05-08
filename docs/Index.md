---
title: Finzora Bilgi Tabanı — Index
description: Tüm dokümanların kategorize haritası. Obsidian graph view'i için ana giriş noktası. Yeni özellik geliştirirken önce buraya bak, ilgili dokümanlara wikilink üzerinden git.
tags:
  - index
  - architecture
  - finzora
created: 2026-05-03
---

# 🗺️ Finzora Bilgi Tabanı

> **Kullanım:** Obsidian'da `docs/` klasörünü vault olarak aç. Bu dosya ana harita. Her `[[link]]` ilgili dosyaya götürür. Graph view'da modüller arası ilişkileri görsel olarak izle.

---

## 🏛️ Mimari & Sistem

Sistem nasıl çalışır, hangi parça nereye bağlı.

- [[SYSTEM_MAP]] — Tam sistem haritası: entry point'ler, 4 mod, akış
- [[DECISION_ARCHITECTURE_V2]] — Karar verme mimarisi v2
- [[DECISION_FRAMEWORK]] — K-rule + LLM birleşim mantığı
- [[OBSERVABILITY]] — Event logging, JSONL/SQLite şeması
- [[GITHUB_ACTIONS_GUIDE]] — Workflow zamanlamaları, CI/CD
- [[RAILWAY_DEPLOY]] — Railway worker (Telegram bot) deploy
- [[SESSION_REFERENCE]] — FAZ 0/1/2/3 seans modeli

---

## 📊 Değerleme (Valuation)

- [[ADIL_DEGER_RAPOR_PROTOKOLU]] — **EMIR:** "TICKER adil değer hesapla" komutu için zorunlu rapor formatı, GitHub kayıt yolu, 11 bölüm şartı
- [[VALUATION_SYSTEM_v6]] — En güncel framework (v6 + v7 Hybrid Plus)
- [[VALUATION_FRAMEWORK_v5]] — v5 archetype-routed temeli
- [[FORWARD_VALUATION_METHOD]] — Forward EPS bazlı yöntem
- [[ADIL_DEGER_KULLANIM]] — `/deger` ve `/q` komutları, kullanım örnekleri

İlgili: [[K_RULES_QUICK_REF#K-13]] (VIX bazlı pozisyon)

---

## 🎯 Trade Sistemi & K-Kuralları

- [[K_RULES_QUICK_REF]] — Tüm K-rule'ların özeti (K-04...K-23)
- [[K_RULES_BACKTEST_DERSLER]] — Backtest sonuçları, ders çıkarımları
- [[STOP_MANAGEMENT_V2]] — Stop-loss yönetimi, trailing
- [[TRADING_PLAYBOOK]] — Genel oyun kitabı

---

## 📈 Portföy Tipleri

- [[AGGRESSIVE_V2_THESIS]] — Agresif portföy tezi
- [[DIVIDEND_SYSTEM]] — Temettü portföyü
- [[SWING_SYSTEM_V2]] — Swing trade sistemi (5-slot)
- [[PORTFOLIO_OPPORTUNITY_SYSTEM]] — Fırsat tespit sistemi
- [[PORTFOLIO_DATA_SKILL]] — Portföy veri yapısı

---

## 🌊 Tema & Sektör

- [[THEMATIC_SYSTEM]] — Tematik analiz mimarisi
- [[THEMATIC_INTEGRATION_GUIDE]] — Sisteme nasıl bağlanır
- [[THEMATIC_CATALYST_CALENDAR]] — Katalist takvimi
- [[THEMATIC_WATCHLIST_Q2_2026]] — Q2 2026 watchlist
- [[SECTOR_AGENTS]] — Sektör agent sistemi
- [[SEKTOR_DEEP_DIVE_SKILL]] — Derin sektör analizi
- [[MARKET_INTELLIGENCE]] — Piyasa zekası özet

---

## 🧠 Öğrenme & Hafıza

- [[EPISODIC_MEMORY]] — Episodic memory sistemi
- [[SELF_IMPROVEMENT_SYSTEM]] — Darwin evrim, prompt mutasyonu
- [[POST_TRADE_REVIEW]] — Trade kapanış sonrası analiz
- [[RAG_SYSTEM]] — Retrieval-augmented generation altyapısı

---

## 🔍 Tarama & Sinyal

- [[DYNAMIC_SCREENER_CRITERIA]] — Tarama kriterleri
- [[PREDICTION_MARKETS_GUIDE]] — Tahmin piyasaları rehberi
- [[FMP_SKILL]] — FMP API entegrasyon kılavuzu (master)

---

## 📝 Raporlama

- [[WEEKLY_REPORT_TEMPLATE]] — Haftalık rapor şablonu

---

## 🎨 Bot Komutları (Hızlı Referans)

| Komut | Amaç | Süre |
|---|---|---|
| `AAPL` veya `/deger AAPL` | Kimi v7 derin analiz | ~30-50sn |
| `/q AAPL` | Sadece framework | ~2sn |
| `/detay AAPL` | Uzun rapor | ~30-50sn |
| `/portfoy` | Pozisyon özeti | anlık |
| `/swing` | Aktif swing | anlık |
| `/tema` | Bugünün dominant temaları | anlık |
| `/havuz` | AI'nin son aday havuzu + kararları | anlık |
| `/vix` | VIX seviyesi | anlık |
| `/kriz` | K-13 aktif kriz matrisi | anlık |
| `/stats` | P&L istatistikleri | anlık |
| `/finzora_sor X` | Serbest AI sorusu | ~10-30sn |
| `/analiz AAPL` | Tam tez + risk + portföy uygunluğu | ~30-60sn |
| `/env` | Sistem env durumu | anlık |
| `/yardim` | Tüm komutlar | anlık |

---

## 🤖 AI Modeli

Aktif: **`moonshotai/kimi-k2-thinking`** (OpenRouter üzerinden)
Geçmiş: Anthropic Claude Opus 4.7 — `KIMI_VALUATION_BLEND` env'i ile blend ağırlığı, default `0.70` Kimi.

---

## 🔧 Geliştirici Notları

- Repo kökü: `/home/zeynel/Belgeler/portfolio-tracker`
- Production: Railway worker (`Procfile` → `scripts/telegram_bot.py`)
- Bot, Railway'de zamanı takip eder, GitHub Actions workflow'larını dispatch eder
- Tüm cron Railway'de — GitHub'da sadece `workflow_dispatch` + `push` trigger
- Kritik state: `data/portfolios/*.json`, `data/swing/*.json`, `data/session_state.json`, `agent/memory/*.json`, `logs/events.jsonl`

Daha derin teknik referans: [[SYSTEM_MAP]]
