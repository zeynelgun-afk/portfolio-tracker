---
title: Portföy Veri Yapısı
description: data/portfolios/*.json şeması, transactions.csv formatı, alanların anlamı.
tags:
  - portfolio
  - data
  - schema
related:
  - "[[Index]]"
  - "[[SYSTEM_MAP]]"
  - "[[OBSERVABILITY]]"
---

# PORTFOLIO TRACKER — VERİ YAPISI VE SİSTEM REFERANSI

> **Repo**: https://github.com/zeynelgun-afk/portfolio-tracker
> **Son güncelleme**: 10 Nisan 2026
> **Amaç**: Tüm JSON/CSV dosyalarının güncel şeması, script envanteri ve sistem kuralları

> ⚠️ **DEPRECATED — 13 Mayıs 2026 öncesi yapı.** Bu doküman eski 3-portföy
> (`data/portfolios/{balanced,aggressive,dividend}.json`) + swing
> (`data/swing/active.json`) + `data/transactions.csv` yapısını anlatır.
> 13 May 2026 simplification ile tek `data/portfolio.json` (positions+closed)
> kullanılıyor; transactions.csv `data/archive/2026-05-13_pre_simplification/`
> altına taşındı. Güncel mimari için `docs/SYSTEM_MAP.md` (14 May 2026).

---

## KRİTİK KURALLAR

1. **İşlemler `data/portfolio.json`'a** — `positions[]` (açık) + `closed[]` (kapanmış). Eski `transactions.csv` artık ARŞİVDE (`data/archive/2026-05-13_pre_simplification/`), 17 Şubat–12 Mayıs 2026 dönemini kapsar; yeni işlem yazılmıyor.
2. **Türkçe zorunlu** — commit mesajları, alan açıklamaları, tezler Türkçe
3. **Her değişiklikten sonra** git commit + push
4. **Hesaplama tutarlılığı**: `yatirim = adet × maliyet_baz`, `kar_zarar = guncel_deger - yatirim`
5. **Tarih formatı**: `"2026-04-10"` (tarih) / `"2026-04-10T14:30:00.000000"` (timestamp)

---

## 1. PORTFÖY DOSYALARI

### Dosya Yolları

| Portföy | Dosya | Başlangıç |
|---------|-------|-----------|
| Dengeli | `data/portfolios/balanced.json` | $100K |
| Agresif | `data/portfolios/aggressive.json` | $400K |
| Temettü | `data/portfolios/dividend.json` | $100K |

### Portföy JSON Şeması

```json
{
  "portfoy_adi": "Dengeli Portföy",
  "baslangic_sermaye": 100000,
  "nakit": {
    "miktar": 69669.30,
    "para_birimi": "USD",
    "agirlik_yuzde": 61.86
  },
  "pozisyonlar": [...],
  "son_guncelleme": "2026-04-09T19:01:30.732241",
  "toplam_deger": 112580.00,
  "toplam_getiri": 12580.00,
  "toplam_getiri_yuzde": 12.58,
  "transactions": [],
  "notes": []
}
```

### Pozisyon Şeması — Tam Alan Listesi

```json
{
  "sembol": "MO",
  "isim": "Altria Group Inc",
  "sektor": "Temel Tüketim",
  "adet": 267,
  "maliyet_baz": 67.44,
  "guncel_fiyat": 67.45,
  "yatirim": 18006.48,
  "guncel_deger": 18009.15,
  "kar_zarar": 2.67,
  "kar_zarar_yuzde": 0.24,
  "gunluk_degisim_yuzde": 0.47,
  "son_guncelleme": "2026-04-09T19:01:30.732241",
  "giris_tarihi": "2026-02-17",
  "giris_fiyati": 67.44,
  "giris_nedeni": "Başlangıç pozisyonu - Temettü savunmacı",
  "agirlik_yuzde": 15.86,
  "stop_loss": 64.89,
  "cb_kaynak": "transactions-2026-02-17"
}
```

| Alan | Hesaplama / Kural |
|------|-------------------|
| `maliyet_baz` | Ortalama alış fiyatı (CSV'den hesaplanır) |
| `stop_loss` | Stop-loss fiyatı (K-kurallarına göre, ATR14 tabanlı) |
| `cb_kaynak` | Maliyet bazının kaynağı (CSV kayıt tarihi) |
| `yatirim` | `adet × maliyet_baz` |
| `guncel_deger` | `adet × guncel_fiyat` |
| `kar_zarar` | `guncel_deger - yatirim` |
| `kar_zarar_yuzde` | `(kar_zarar / yatirim) × 100` |
| `agirlik_yuzde` | `(guncel_deger / toplam_deger) × 100` |

### Portföy Hesaplamaları

```
toplam_deger = sum(pozisyon.guncel_deger) + nakit.miktar
toplam_getiri = toplam_deger - baslangic_sermaye
toplam_getiri_yuzde = (toplam_getiri / baslangic_sermaye) × 100
nakit.agirlik_yuzde = (nakit.miktar / toplam_deger) × 100
```

---

## 2. TRANSACTIONS CSV — TEK İŞLEM KAYDI YERİ

**`data/transactions.csv`** — tüm alış/satışların tek kaydı. Portföy JSON'larına işlem yazılmaz.

```csv
date,action,symbol,shares,price,total,reason
2026-02-17,BUY,MO,267,67.44,18006.48,Başlangıç pozisyonu - Dengeli portföy - Temettü savunmacı
2026-03-15,SELL,FCX,100,58.20,5820.00,Stop-loss tetiklendi - Çin talebi zayıflığı
```

| Sütun | Değerler | Kural |
|-------|---------|-------|
| `action` | `BUY` / `SELL` | İngilizce (CSV standardı) |
| `total` | float | `shares × price` |
| `reason` | string | Türkçe, portföy adı + neden |

---

## 3. TARAMA DOSYALARI

Her sabah 06:15 UTC (09:15 TR) otomatik çalışır. 3 mod.

| Dosya | Mod | İçerik |
|-------|-----|--------|
| `data/daily_scan_balanced.json` | Dengeli | PEG≤2.5, EKLE≥9, İZLE≥6 |
| `data/daily_scan_dividend.json` | Temettü | Yield≥%2.5, EKLE≥9, İZLE≥6 |
| `data/daily_scan_aggressive.json` | Agresif | EPS≥%10 veya AI evreni, EKLE≥16, İZLE≥12 |
| `data/daily_full_scan.json` | Geriye dönük uyum | Dengeli sonuçları (eski format) |

### Tarama JSON Şeması

```json
{
  "tarih": "2026-04-10",
  "son_guncelleme": "2026-04-10T10:12:41",
  "mod": "aggressive",
  "toplam_taranan": 1543,
  "filtre_gecen": 617,
  "skorlanan": 617,
  "ekle_adaylari": 26,
  "izle_adaylari": 97,
  "esikler": {"ekle": 16, "izle": 12},
  "sonuclar": [
    {
      "symbol": "STX",
      "company": "Seagate Technology Holdings",
      "sector": "Technology",
      "price": 125.40,
      "mcap_b": 28.5,
      "fwd_pe": 18.2,
      "eps_growth_2y": 54.0,
      "peg": 0.34,
      "declining_eps": false,
      "n_analysts": 18,
      "yield_pct": 0.0,
      "k13_category": "duyarli",
      "payout_pct": 0.0,
      "de_ratio": 1.2,
      "roic": 39.0,
      "fcf_yield": 1.7,
      "npm": 12.4,
      "rsi": 68.3,
      "mom1m": 30.3,
      "mom3m": 45.1,
      "mom6m": 122.6,
      "above_sma50": true,
      "above_sma200": true,
      "golden_cross": true,
      "score": 23,
      "mode": "aggressive",
      "yield_trap": false
    }
  ]
}
```

---

## 4. WATCHLIST — `data/watchlist.json`

PART 1C ve `scripts/watchlist_manager.py` tarafından yönetilir. Manuel dokunma yapılmaz.

```json
{
  "son_guncelleme": "2026-04-09T12:00:00",
  "not": "...",
  "sistem_referans": "docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md",
  "script": "scripts/watchlist_manager.py",
  "izleme_listesi": [
    {
      "sembol": "QCOM",
      "hedef_portfoy": "agresif",
      "guncel_fiyat": 124.50,
      "rsi": 52.0,
      "skor": 18,
      "skor_detay": "...",
      "sektor": "Technology",
      "tema": "CPU darboğazı",
      "urgency": "high",
      "ekleme_tarihi": "2026-04-07",
      "son_kontrol": "2026-04-09",
      "hedef_giris": "120-128",
      "hedef_fiyat_1": 139.0,
      "hedef_fiyat_2": 160.0,
      "stop_loss": 118.0,
      "r_r_orani": 3.8,
      "tez": "CPU darboğazı teması, snapdragon liderliği...",
      "karsit_argumani": "Çin riski, NVIDIA ile rekabet...",
      "k_04_gecis": true,
      "k_05_gecis": true,
      "k_17_gecis": true,
      "k_18_gecis": true,
      "bekleme_gun": 3,
      "karar": "İZLE",
      "momentum_5gun": 2.1
    }
  ],
  "haric_tutulanlar": [
    {
      "sembol": "LASR",
      "neden": "Stop-loss tetiklendi, 7 gün cool-down",
      "tarih": "2026-03-20"
    }
  ]
}
```

**Watchlist script komutları:**
```bash
python scripts/watchlist_manager.py list
python scripts/watchlist_manager.py add QCOM --portfoy agresif
python scripts/watchlist_manager.py remove QCOM
python scripts/watchlist_manager.py refresh
python scripts/watchlist_manager.py cleanup
python scripts/watchlist_manager.py cooldown
```

---

## 5. SWING TRADE DOSYALARI

### `data/swing/active.json`

```json
{
  "son_guncelleme": "2026-04-09T21:37:40",
  "not": "SWING TRADE SADECE SİMÜLASYON - MAX: 8 pozisyon",
  "aktif_pozisyonlar": [
    {
      "id": "SWING-042",
      "sembol": "NEM",
      "giris_tarihi": "2026-04-01",
      "giris_fiyat": 58.40,
      "guncel_fiyat": 62.10,
      "pnl_pct": 6.34,
      "hedef_fiyat": 65.00,
      "stop_loss": 55.50,
      "tutulan_gun": 9,
      "giris_nedeni": "Ichimoku 4/4 sinyal, altın güçlü, SMA200 üstü",
      "katalizor": "Altın fiyat kırılımı",
      "tez": "Altın madenciliği lideri, güvenli liman talebi arttı",
      "risk": "Altın fiyat dönüşü, dolar güçlenmesi",
      "tarama_yontemi": "swing_full_universe.py / ichimoku-4/4",
      "k13_kategori": "faydalanici",
      "pozisyon_buyuklugu": 5000,
      "chandelier_stop": 59.20,
      "son_guncelleme": "2026-04-09T19:01:00"
    }
  ],
  "ozet": {
    "toplam_pozisyon": 1,
    "bos_slot": 4,
    "maksimum_pozisyon": 5,
    "ortalama_kar_zarar_yuzde": 6.34
  }
}
```

### `data/swing/closed.json`

```json
{
  "son_guncelleme": "2026-04-09",
  "istatistikler": {
    "toplam_trade": 42,
    "kazanc": 24,
    "zarar": 18,
    "kazanc_orani": 57.1,
    "ortalama_kar_yuzde": 8.4,
    "ortalama_zarar_yuzde": -4.2
  },
  "kapatilan_pozisyonlar": [
    {
      "id": "SWING-041",
      "sembol": "LASR",
      "giris_tarihi": "2026-03-18",
      "cikis_tarihi": "2026-03-20",
      "giris_fiyati": 18.40,
      "cikis_fiyati": 17.48,
      "kar_zarar_yuzde": -5.0,
      "tutulan_gun": 2,
      "cikis_nedeni": "Stop-loss tetiklendi -%5",
      "sonuc": "ZARAR",
      "ders": "Kriz rallisi kovalama hatası — K-13 kural ihlali"
    }
  ]
}
```

### `data/swing/status.json` — K-14 Drawdown Takibi

```json
{
  "k14_aktif": false,
  "peak_deger": 12480,
  "trough_deger": 10430,
  "mevcut_drawdown_yuzde": 16.42,
  "son_guncelleme": "2026-04-09",
  "yeniden_baslama_kosullari": {
    "vix_alti": 22,
    "spy_sma50_ustu": true,
    "sektor_rotasyonu_pozitif": false
  }
}
```

---

## 6. SUMMARY — `data/summary.json`

```json
{
  "son_guncelleme": "2026-04-09",
  "toplam_sermaye": 600000,
  "toplam_deger": 618450.00,
  "toplam_getiri": 18450.00,
  "toplam_getiri_yuzde": 3.08,
  "benchmark_spy_yuzde": -2.1,
  "alpha": 5.18,
  "portfolyolar": {
    "dengeli": {
      "deger": 112580.00,
      "getiri_yuzde": 12.58,
      "pozisyon_sayisi": 4,
      "nakit": 69669.30
    },
    "agresif": {
      "deger": 405870.00,
      "getiri_yuzde": 1.47,
      "pozisyon_sayisi": 0,
      "nakit": 405870.00
    },
    "temettü": {
      "deger": 100000.00,
      "getiri_yuzde": 0.0,
      "pozisyon_sayisi": 4,
      "nakit": 30000.00
    }
  }
}
```

---

## 7. SESSION STATE — `data/session_state.json`

Günlük seans sırasında otomatik update scripti tarafından yazılır.

```json
{
  "tarih": "2026-04-09",
  "faz": "KAPALI",
  "vix": 24.3,
  "spy_fiyat": 548.20,
  "spy_sma50": 562.40,
  "spy_sma50_ustu": false,
  "k13_aktif": true,
  "k13_mod": "yari_pozisyon",
  "k14_aktif": false,
  "son_guncelleme": "2026-04-09T21:41:00"
}
```

---

## 8. SCRIPT ENVANTERİ

| Script | Amaç |
|--------|------|
| `daily_update.py` | Fiyat güncelleme, seans snapshot (GitHub Actions) |
| `full_universe_screener.py` | 3 modlu sabah taraması (balanced/dividend/aggressive) |
| `portfolio_scan_balanced.py` | Dengeli portföy fırsat taraması (PART 1C) |
| `portfolio_scan_aggressive.py` | Agresif portföy taraması (PART 1C) |
| `portfolio_scan_dividend.py` | Temettü portföy taraması (PART 1C) |
| `portfolio_scan_common.py` | Ortak skorlama fonksiyonları |
| `swing_full_universe.py` | Swing evren taraması (ichimoku 4/4) |
| `swing_ichimoku.py` | Ichimoku hesaplamaları |
| `swing_technical.py` | Teknik analiz yardımcı fonksiyonlar |
| `watchlist_manager.py` | Watchlist CRUD + cooldown yönetimi |
| `risk_panel_generator.py` | Günlük risk paneli PNG (1080×1920) |
| `telegram_notify.py` | Telegram bildirim gönderimi |
| `macro_intelligence_notify.py` | Günlük dominant tema + kriz özeti DM |
| `k09_proximity_check.py` | Stop yakınlık kontrolü |
| `k14_drawdown_track.py` | Drawdown takibi |
| `k15b_dilution_check.py` | Hisse seyreltme kontrolü |
| `k16_sell_the_news_score.py` | Sell-the-news riski skoru |
| `k17_correlation_check.py` | Korelasyon / tema çakışma kontrolü |
| `k18_insider_check.py` | İçeriden satış kontrolü |
| `k19_xlp_filter.py` | XLP sektör filtresi |
| `k20_rs_filter.py` | RS dead cat bounce filtresi |
| `k_rules_common.py` | Ortak K-kural altyapısı |

---

## 9. GITHUB ACTIONS WORKFLOWS

| Workflow | Zamanlama | Amaç |
|----------|-----------|------|
| `morning_scan.yml` | 06:15 UTC haftaiçi | 3 modlu evren taraması |
| `daily_update.yml` | Seans saatleri | Fiyat güncelleme (her ~45 dk) |
| `notify-transactions.yml` | Push tetikli | Yeni işlem Telegram bildirimi |

---

## 10. GİT COMMIT FORMAT

```
[ALIŞ] Dengeli - MO @67.44 - Temettü savunmacı başlangıç
[SATIŞ] Agresif - AMD @199.39 - Stop-loss tetiklendi -%8
[GÜNCELLEME] Tüm portföyler - 09 Nisan kapanış fiyatları
[SWING-GİRİŞ] NEM @58.40 - Ichimoku 4/4 + altın momentum
[SWING-ÇIKIŞ] LASR @17.48 - Stop-loss -%5
[AUTO-SCAN] 10 Nisan 2026 | balanced:62ekle | dividend:42ekle | aggressive:26ekle
[PORTFÖY RAPORU] 10 Nisan 2026 - 3 EKLE kararı
[SWING RAPORU] 10 Nisan 2026 - 2 yeni aday
```

---

## 11. BELGE REFERANSLARI

| Belge | Konu |
|-------|------|
| `docs/TRADING_PLAYBOOK.md` | Tüm K-kuralları detaylı (K-01→K-20) |
| `docs/K_RULES_QUICK_REF.md` | K-kural özet referansı |
| `docs/SWING_SYSTEM_V2.md` | Swing sistemi v2.3 (ichimoku 4/4, chandelier) |
| `docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md` | PART 1C sistem detayı |
| `docs/AGGRESSIVE_V2_THESIS.md` | AI tedarik zinciri tezi |
| `docs/MARKET_INTELLIGENCE.md` | Makro zeka sistemi |
| `docs/THEMATIC_WATCHLIST_Q2_2026.md` | Q2-Q3 2026 tematik liste |
| `docs/prompts/DAILY_PART1_SABAH.md` | Sabah raporu promptu |
| `docs/prompts/DAILY_PART1B_SWING.md` | Swing tarama promptu |
| `docs/prompts/DAILY_PART1C_PORTFOY.md` | Portföy tarama promptu |
| `docs/prompts/DAILY_PART2_CLOSING.md` | Kapanış raporu promptu |
| `docs/prompts/SESSION_ACTION_PROMPT.md` | Seans aksiyon promptu |

---

*Finzora AI | 10 Nisan 2026 | v2.0*
