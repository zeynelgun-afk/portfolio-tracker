---
title: Değerleme Framework v5
description: Archetype-routed multi-method framework. v5 mekanik temel — v6/v7 üzerine inşa edildi.
tags:
  - valuation
  - framework
  - archetype
related:
  - "[[Index]]"
  - "[[VALUATION_SYSTEM_v6]]"
  - "[[FORWARD_VALUATION_METHOD]]"
---

# Valuation Framework v5 — Mimari ve Kullanım Rehberi

**Dosya tarihi**: 2026-04-19
**Commit**: 5100177

## Neden v5? v2'nin sorunları

Mevcut `adil_deger_calculator.py` (v2) tüm hisselere aynı 6 metodu (P/E, Forward P/E, EV/EBITDA, DCF, P/FCF, EV/Revenue) eşit ağırlıkla uyguluyordu. Sonuç:

**ALAB örneği** (hyper-growth AI semi):
- Trailing P/E: $248 (-30%)  — anlamsız, büyüme curve'ü yakalayamıyor
- Forward P/E: $68 (+156%)
- EV/EBITDA: $308 (-44%) — trailing EBITDA çok düşük
- DCF: $123 (+41%)
- P/FCF: $186 (-6%)
- EV/Revenue: $19 (+813%) — hyper-growth için doğru ama izole

→ **Ağırlıklı ortalama: $168, güven %26 (CHAOS).**

Problem şu ki: ALAB için trailing P/E ve EV/EBITDA **ekonomik olarak anlamsız**. ALAB henüz matured earnings'e sahip değil. Banka için EV/EBITDA **ekonomik olarak tanımsız**. REIT için GAAP net income depreciation yüzünden %40-60 distorted.

Eşit ağırlıklı 6 metot, **uygun olmayan metotları elimine etmek yerine ortalamaya karıştırıyor**, sahte güven skoru üretiyor.

## v5'in çözümü: archetype-routed method selection

**Tez**: Valuation doğruluğu, sınıflandırma doğruluğuyla sınırlıdır. Yanlış arketip → yanlış metot seti → kademeli hata.

### 32 arketip

Her şirket 32 arketipten birine sınıflanır. Her arketip için:
- **Primary metotlar** (60-70% ağırlık): Bu şirket tipine en uygun 2-3 metot
- **Secondary** (20-30%): Destek metotları
- **Sanity check** (5-15%): Çapraz doğrulama
- **Excluded** (hard exclusion): Yasaklı metotlar + gerekçeleri

Örnek yol ayrımları:

| Arketip | Primary | Excluded (gerekçe) |
|---------|---------|---------------------|
| hyper_growth_semi (ALAB, NVDA peak) | Forward P/E NY2 25% + EV/EBITDA forward 20% + DCF aggressive 20% | trailing_pe (cycle-distorted), dividend_discount (no div), price_to_book (asset-light) |
| money_center_bank (JPM) | Justified P/B 25% + Residual Income 25% + Forward P/E normalized 15% | **FCFF-DCF (undefined)**, **EV/EBITDA (undefined)**, EV/Revenue (meaningless) |
| reit_net_lease (O) | P/AFFO 30% + P/FFO 20% + DDM 20% | **Trailing P/E (GAAP distortion 40-60%)**, forward P/E NY1/NY2 (same reason) |
| biotech_preclinical (pre-revenue) | rNPV pipeline 40% + cash-adjusted cap 20% + real options 15% | Tüm earnings multiples, DCF, P/B (R&D not capitalized) |

## Mimari

```
agent/valuation/
├── archetypes.py          # 32 arketip + method routing table
├── classifier.py          # FMP verisi → archetype tespit
├── framework.py           # Ana aggregator (outlier + weight + confidence)
├── tuning.py              # v5.2: Archetype-specific parametreler (WACC, multipleları)
├── market_regime.py       # SPY SMA21 → BOGA/AYI multiplier
├── prediction_log.py      # v5.5: Her valuate() çağrısı kayıt (backtest için)
├── backtest.py            # v5.5: Geçmiş tahminleri gerçek fiyatlarla karşılaştır
└── methods/
    ├── __init__.py        # Data fetcher (9 FMP endpoint)
    └── registry.py        # 30+ valuation method fonksiyonu
```

### 6-aşamalı pipeline

1. **Classify** — `classifier.classify(ticker)` FMP profile/ratios/growth verilerine bakarak arketip belirler. REIT/Bank/Insurer öncelik (sektör-zorunlu), sonra growth/margin/SBC bazlı disambiguation.
2. **Fetch** — Tüm FMP verileri bir kez çeker (~9 endpoint), TTM türetmeleri yapar, FMP eksik alanları fallback ile doldurur (ROE = NI/Equity, tangible_bvps = BVPS*0.82).
3. **Compute** — Her applicable method'u bağımsız olarak çalıştırır. Veri yetersizse `None` döner (metod atlanır).
4. **Outlier filter** — 3× MAD (median absolute deviation) dışındaki metod sonuçlarını hariç tutar. Ortalamaya karıştırmaz.
5. **Weighted aggregation** — Kalan metotların ağırlıklı ortalaması (ağırlıklar yeniden normalize edilir).
6. **Confidence score** — Classification-fit + method coverage + dispersion:
   - `score = 0.35 × archetype_conf + 0.35 × weight_coverage + 0.30 × agreement`
   - Red flags: SBC > 10%, large deviation, outlier count, few methods

## Kullanım

### Python'dan

```python
from agent.valuation.framework import valuate, format_report

result = valuate("ALAB", verbose=True)
print(format_report(result, style="terminal"))
# veya
print(format_report(result, style="telegram"))

# Yapılandırılmış erişim:
print(result["classification"]["archetype"])      # "hyper_growth_semi"
print(result["fair_value"]["point"])              # 112.00
print(result["fair_value"]["upside_pct"])         # -35.7
print(result["confidence"]["score"])              # 82
print(result["methods_used"])                     # 5 metot detayı
print(result["methods_excluded"])                 # 4 yasaklı metot
```

### Entegrasyon noktaları (v5.3-v5.4)

v5 framework 3 farklı sistem tarafından kullanılıyor, hepsi aynı kaynaktan besleniyor:

1. **Telegram bot** (`scripts/telegram_bot.py`) — `/deger AAPL`, `AAPL` doğrudan komutlar
2. **Portfolio scan** (`scripts/portfolio_scan_common.py`) — `apply_valuation_signal()` helper, score bonus/penalty (+3/-3 skala)
3. **Agent opportunity finder** (`agent/opportunity_finder.py`) — `_score_valuation()` 0-10 ölçek, final score'un %20 ağırlığı

Her 3 noktada da **aynı guardrail'ler** çalışır:
- Güven <50 → sinyal yok / neutral
- Güven 50-70 → sinyal yarıya
- Analyst gap >30% → sinyal yarıya (framework ↔ consensus çelişkisi)

### Backtest altyapısı (v5.5)

Her `valuate()` çağrısı `logs/valuation_predictions.jsonl`'e kaydedilir. GitHub Actions workflow'ları (agent.yml, morning_scan.yml) bu dosyayı git'e commit eder (timestamp bazlı dedup + sort -u). 

Bot komutları:
- `/vstats` — son 30 gün log özeti (archetype dağılımı, karar dağılımı, ortalama güven)
- `/backtest` (veya `/bt`) — ≥14 gün eski tahminlerin hit rate analizi

CLI:
```bash
python3 agent/valuation/backtest.py --min-age 14
python3 agent/valuation/backtest.py --min-age 30 --json
```

Hit/miss mantığı:
- `UCUZ/ADİL-UCUZ` + real >+5% → HIT
- `UCUZ/ADİL-UCUZ` + real <-5% → MISS
- `PAHALI/ADİL-PAHALI` + real <-5% → HIT
- `PAHALI/ADİL-PAHALI` + real >+5% → MISS
- `ADİL` → NO_SIGNAL (değerlendirme dışı)

Beklenen birikim: ~1000-1200 log/hafta (agent workflow 8 run/gün × 25-30 v5 çağrı/run). 3 ay sonra backtest için anlamlı veri.

### Komut satırından

```bash
python3 agent/valuation/framework.py ALAB MSFT JPM O NVDA
```

### Telegram bot

`/deger AAPL` ve `AAPL` dogrudan ticker komutları v5'i kullanır. Output:

```
AAPL — v5 Adil Değer
Olgun mega-cap tech (güven %90)

🔴 $252.11 → hedef $248.50 (-1.4%)
Aralık: $220.00 — $290.00
Karar: ADİL
Güven: 88/100

Kullanılan metotlar:
  ⭐ dcf_2stage                    $252.00  (w=25%)
  ⭐ forward_pe_ny1                $245.00  (w=20%)
  ⭐ fcf_yield                     $248.50  (w=20%)
  ◽ ev_ebitda                     $252.00  (w=15%)
  ◽ pegy                          $250.00  (w=10%)

Yasaklı (3): price_to_book, reserves_nav, rnpv...
```

## Migration guide

v5 şu anda **v2 ile paralel** çalışıyor. Bot ve portföy scanner'ları önce v5'i dener, hata durumunda v2'ye düşer:

```python
def hesapla_sembol(sym):
    # 1. v5 dene
    try:
        from valuation.framework import valuate
        res = valuate(sym)
        if res and not res.get("error"):
            return {
                "symbol": sym, "price": res["fair_value"]["current_price"],
                "adil_deger": res["fair_value"]["point"],
                "fark_pct": res["fair_value"]["upside_pct"],
                "guven": res["confidence"]["score"],
                "_version": "v5",
                "_v5_full": res,
            }
    except Exception:
        pass

    # 2. v2 fallback
    from adil_deger_calculator import hesapla
    return hesapla(sym, sessiz=True)
```

v5 olgunlaştıkça v2 shim olarak kalacak.

## Test sonuçları (5 ticker)

| Ticker | Archetype | Current | Fair | Upside | Confidence | v2 güven |
|--------|-----------|---------|------|--------|------------|----------|
| ALAB | hyper_growth_semi | $174 | $112 | -35.7% PAHALI | 82/100 | **26/100** |
| MSFT | mature_megacap_tech | $423 | $252 | -40% PAHALI | 81/100 | ~60 |
| JPM | money_center_bank | $310 | $228 | -26% PAHALI | 71/100 | ~40 (FCFF çıktı) |
| O | reit_net_lease | $65 | $76 | +17% UCUZ | 84/100 | ~30 (trailing P/E çıktı) |
| NVDA | hyper_growth_semi | $202 | $368 | +83% UCUZ | 78/100 | ~50 |

**4x iyileşme** ALAB ve JPM için confidence skorunda.

## Bilinen limitasyonlar ve yol haritası

### v5.0 → v5.5 tamamlananlar
- v5.1: Analyst consensus reality check (FMP price-target-consensus entegre)
- v5.2: Archetype-specific tuning parametreleri (WACC, multipleları per archetype)
- v5.3: Portfolio scan skoruna valuation sinyali (apply_valuation_signal)
- v5.4: Agent opportunity finder valuation skoru (_score_valuation 0-10)
- v5.5: Prediction log + backtest altyapısı (14+ gün sonra çalışır)

### v5.6+ yol haritası

1. **Backtest kalibrasyonu** (4-8 hafta sonra): Framework hit rate'i <50% olan archetype'lar için tuning parametrelerini revize et. Örnek: `hyper_growth_semi` hit rate <40% ise forward_pe_ny2 multiplier'ı 45 → 35'e düşür.

2. **MSFT/AAPL/GOOGL mature tech DCF sorunu**: Framework -30 ile -45% bearish diyor, analyst +30 ile +45% bullish. Gerçek taraf backtest ile belirlenecek. Muhtemel neden: Azure/iPhone capex normalleştirmesi yapılmıyor.

3. **Reserves NAV / rNPV gerçek veri**: Oil/gas ve biotech için şu an proxy (BVPS×1.5). AI web research entegrasyonu — clinicaltrials.gov, SEC 10-K filings.

4. **Dinamik sektör peer median**: Tuning parametreleri hard-coded. FMP sector/industry filter ile canlı peer median → fair multiple auto-update.

5. **Multistage DDM, embedded value, Merton option pricing**: Utility ve insurer için şu an placeholder. Gerçek implementation.

6. **Confidence kalibrasyonu**: Backtest ile `conf >80` → gerçekten %X doğru mu? Bucket edge'ları (50, 70, 75) iteratif ayarlanır.

## Referanslar

- **Damodaran's lifecycle valuation** (NYU Stern): pages.stern.nyu.edu/~adamodar
- **McKinsey/Koller Valuation 7e**: ROIC fade + WACC consistency
- **CFA Institute Equity Asset Valuation** (Pinto/Henry/Robinson)
- **NAREIT FFO white paper**: REIT standardization
- **Araştırma dokümanı**: Archetype-Routed Valuation Framework (AI Extended Research, 2026-04-19)

## İlgili kod dosyaları

- `agent/valuation/archetypes.py` — 32 arketip taksonomi
- `agent/valuation/classifier.py` — Detection rules
- `agent/valuation/framework.py` — Aggregator + format_report
- `agent/valuation/methods/__init__.py` — Data fetcher
- `agent/valuation/methods/registry.py` — 30+ valuation method
- `scripts/telegram_bot.py` — Bot v5 dispatch
- `scripts/portfoy_adil_deger.py` — Portföy scan v5 dispatch
- `scripts/adil_deger_calculator.py` — v2 legacy (fallback)
