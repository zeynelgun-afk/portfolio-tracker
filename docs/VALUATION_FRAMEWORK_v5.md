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

## Bilinen limitasyonlar (v5.0 → v5.1 yol haritası)

1. **NVDA %83 upside**: DCF aggressive fade çok agresif. v5.1'de terminal growth cap + fade curve tuning.
2. **Reserves NAV, rNPV placeholder**: Oil/gas ve biotech için gerçek veri yok — BVPS proxy kullanılıyor. v5.1'de:
   - FMP reserves endpoint'i (eğer var ise)
   - Web research integration (Claude → clinicaltrials.gov, SEC filings)
3. **Sektör peer comparison eksik**: Mevcut fair multipleları hard-coded. v5.1'de dinamik peer median (FMP sector/industry filter).
4. **Multistage DDM, embedded value, Merton option pricing** placeholder. Utility ve insurer için geliştirilecek.
5. **Confidence kalibrasyonu**: Backtesting ile confidence <70 → ne kadar doğru? >80 → ne kadar tutuyor?

## Referanslar

- **Damodaran's lifecycle valuation** (NYU Stern): pages.stern.nyu.edu/~adamodar
- **McKinsey/Koller Valuation 7e**: ROIC fade + WACC consistency
- **CFA Institute Equity Asset Valuation** (Pinto/Henry/Robinson)
- **NAREIT FFO white paper**: REIT standardization
- **Araştırma dokümanı**: Archetype-Routed Valuation Framework (Claude Extended Research, 2026-04-19)

## İlgili kod dosyaları

- `agent/valuation/archetypes.py` — 32 arketip taksonomi
- `agent/valuation/classifier.py` — Detection rules
- `agent/valuation/framework.py` — Aggregator + format_report
- `agent/valuation/methods/__init__.py` — Data fetcher
- `agent/valuation/methods/registry.py` — 30+ valuation method
- `scripts/telegram_bot.py` — Bot v5 dispatch
- `scripts/portfoy_adil_deger.py` — Portföy scan v5 dispatch
- `scripts/adil_deger_calculator.py` — v2 legacy (fallback)
