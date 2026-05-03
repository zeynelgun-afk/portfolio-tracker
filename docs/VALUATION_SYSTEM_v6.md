---
title: Değerleme Sistemi v6 + v7 Hybrid Plus
description: Multi-method mekanik framework + Kimi K2 thinking entegrasyonu. v7'de Kimi birincil karar verici, framework sanity check.
tags:
  - valuation
  - framework
  - kimi
  - hybrid-plus
related:
  - "[[Index]]"
  - "[[VALUATION_FRAMEWORK_v5]]"
  - "[[FORWARD_VALUATION_METHOD]]"
  - "[[ADIL_DEGER_KULLANIM]]"
  - "[[K_RULES_QUICK_REF]]"
updated: 2026-05-03
---

# Adil Değer Sistemi v6

**Sürüm:** 6.0 (mekanik) → **v7 Hybrid Plus** (Kimi-led, Mayıs 2026)
**Tarih:** 25 Nisan 2026
**Önceki sürüm:** v5.0 (geri uyumlu)

## Sorun (v5'te ne yanlıştı)

MU $497 fiyatında v5 mekanik framework "PAHALI, hedef $167 (-66%)" verdi. Aynı anda analist konsensüsü $429, range $310-$550. Sistem konsensüsten **-65% sapma** raporladı ama bu sadece bir red flag olarak kaldı, kararı etkilemedi. Güven skoru hâlâ 72/100 idi yani sistem yanılma ihtimalini doğru yansıtmıyordu.

Kök neden: MU "olgun yarı iletken" archetype'ında ve mid-cycle metodları (`normalized_pe_midcycle`, `ev_ebitda_midcycle`, `price_to_book_capital_intensive`) toplam ağırlığın %55'ini oluşturuyor. Bu metodların hepsi **mean-reversion** (ortalamaya dönüş) varsayımına dayanır. Memory tarihsel olarak siklik bir iştir, yani varsayım mantıklı görünür. Ama AI/HBM (High Bandwidth Memory) yarı iletken sektöründe **yapısal rejim değişikliği** olabilir; eski cycle ortalaması artık geçerli olmayabilir. Sistem bu olasılığı modellemiyordu, sadece tek bir cycle peak hipotezini kabul ediyordu.

## v6 Düzeltmeleri

### 1. Cycle Phase Detector (`agent/valuation/cycle_detector.py`)

Cyclical sektörlerde (yarı iletken, enerji, otomotiv, materials, financials) cycle aşamasını tespit eder.

**6 phase:**
- `bottom`: rev/eps growth negatif, sektör underperform → mid-cycle metodları doğal
- `early`: rev henüz toparlıyor, sektör rotation yeni başlamış
- `mid`: normal aralık, framework default
- `late`: yüksek growth + sektör overperform + multiple aşırı
- `peak`: çok yüksek growth + forward revision yavaşlıyor → mean reversion bekleniyor
- `reset`: yapısal rejim adayı + güçlü growth + güçlü margin → mid-cycle metodları geçersiz

**Yapısal rejim adayları (sektör + industry):**
- AI/memory/compute: Technology + Semiconductors
- GLP-1 / specialty pharma: Health Care + Drug Manufacturers - General
- EV transition: Consumer Cyclical + Auto Manufacturers
- AI infrastructure: Technology + Software - Infrastructure

**Sinyaller:**
- Sektör SPDR ETF / SPY 6-aylık relatif performans
- TTM revenue/EPS growth
- Forward EPS revision direction
- Operating margin seviyesi

**Çıktı:**
- `phase`: str
- `structural_regime_suspect`: bool
- `mid_cycle_weight_modifier`: -0.50 ile +0.30 (peak'te +0.30, reset'te -0.50)
- `growth_weight_modifier`: -0.30 ile +0.50 (peak'te -0.30, reset'te +0.50)

Mid-cycle metodları: `normalized_pe_midcycle`, `normalized_pe_cyclical`, `ev_ebitda_midcycle`, `fcf_yield_midcycle`, `price_to_book_capital_intensive`

Growth metodları: `peg_forward`, `pegy`, `forward_pe_ny1`, `forward_pe_ny2`, `ev_rev_growth_adjusted`, `rule_of_40_multiple`, `dcf_multi_stage_aggressive`

### 2. Konsensüs Sapma Cezası (framework.py)

Eskiden sapma sadece red flag idi. Artık güven skorunu doğrudan etkiliyor:

| Sapma | Aksiyon |
|-------|---------|
| < 15% | confidence +5 (analyst aligned bonus) |
| 15-30% | red flag, ceza yok |
| 30-50% | confidence -10 |
| 50-70% | confidence -25, **`manuel_review_required = True`** |
| ≥ 70% | confidence -40, **`manuel_review_required = True`** |

`manuel_review_required = True` olduğunda karar etiketi otomatik olarak `MANUEL_REVIEW` olur. Sistem mekanik PAHALI/UCUZ yargıya kilitlenmek yerine "ben emin değilim, sen incele" der.

### 3. AI AI Consultation (`agent/valuation/ai_consultant.py`)

Framework tek başına karar veremediğinde AI Opus 4.7'den ikinci görüş alır.

**Tetikleyiciler (otomatik mod):**
- `abs(framework_vs_analyst) >= 50%` → severity 0.70+
- `confidence < 50` → severity 0.50+
- Method dispersion `CV >= 0.40` → severity 0.35+
- Severity ≥ 0.30 ise tetiklenir

**Çağrı modları (`valuate(consult_ai=...)`):**
- `"auto"` (default): Tetikleyici varsa çağır
- `"always"`: Her değerlemede çağır (yavaş, API maliyeti)
- `"never"`: Hiç çağırma

**AI'ye gönderilen prompt:**
- Ticker, fiyat, archetype
- Framework sonucu (fair value, range, karar, güven)
- Kullanılan metodlar ve ağırlıkları
- Red flags
- Analist konsensüs detayı (median, high, low, gap)
- Temel veriler (P/E, growth, marjlar, ROE, ROIC, market cap)
- Makro rejim
- Soru: "Yapısal rejim değişikliği var mı? Mid-cycle metodları haksız lowball yapıyor mu? Bear/Base/Bull senaryolar?"

**AI'den beklenen JSON çıktı:**
```json
{
  "claude_fair_value": 350.0,
  "confidence": 75,
  "scenarios": {
    "bear": {"price": 200, "thesis": "AI capex yavaşlar, memory cycle peak"},
    "base": {"price": 350, "thesis": "HBM yapısal rejim devam"},
    "bull": {"price": 550, "thesis": "AI memory supercycle"}
  },
  "rejim_degisikligi": {
    "var_mi": true,
    "tip": "ai_memory_yapisal",
    "aciklama": "..."
  },
  "cycle_phase": "mid",
  "framework_kritik": "Mid-cycle PE metodu HBM rejim değişikliğini yakalamıyor",
  "tavsiye_etiket": "MANUEL_REVIEW"
}
```

**Blend:**
```
final_fair_value = framework_fv × (1 - blend) + claude_fv × blend
blend = max(0.30, min(0.50, 0.30 + severity × 0.40))
```

Severity 0.80 → blend 0.50 (AI ağırlığı maksimum). Severity 0.30 → blend 0.30 (framework ağırlığı baskın).

### 4. Senaryolu Çıktı (Bear/Base/Bull)

Her değerleme artık tek nokta tahmin yerine 3 senaryo verir:
- **Bear**: range_low veya AI bear (cycle peak / mean reversion)
- **Base**: weighted avg veya AI base
- **Bull**: analyst high veya AI bull (yapısal rejim devam)

## Output Schema (v6)

```python
{
  "ticker": "MU",
  "framework_version": "v6.0",
  "timestamp": "...",

  "classification": {...},   # v5 ile aynı

  "fair_value": {
    "point": 184.17,
    "range_low": 84.17,
    "range_high": 245.08,
    "current_price": 496.72,
    "upside_pct": -62.9,
    "karar": "MANUEL_REVIEW (framework PAHALI, konsensüs ≠)"
  },

  "fair_value_v6_blended": {   # v6 yeni — sadece AI consultation yapıldıysa
    "point": 280.0,            # framework × (1-w) + claude × w
    "framework_fv": 184.17,
    "claude_fv": 350.0,
    "blend_weight": 0.50,
    "upside_pct_blended": -43.6,
    "karar_blended": "PAHALI (AI: MANUEL_REVIEW)"
  },

  "confidence": {
    "score": 28,
    "factors": [...],
    "red_flags": [...],
    "consensus_penalty": 25,           # v6 yeni
    "manuel_review_required": true     # v6 yeni
  },

  "cycle_phase": {                     # v6 yeni
    "is_cyclical": true,
    "phase": "reset",
    "confidence": 0.55,
    "structural_regime_suspect": true,
    "structural_regime_type": "ai_memory_or_compute",
    "mid_cycle_weight_modifier": -0.50,
    "growth_weight_modifier": +0.50,
    "signals": {...},
    "rationale": "..."
  },

  "cycle_weight_adjustment": {         # v6 yeni
    "applied": true,
    "phase": "reset",
    "changes": [
      {"method": "normalized_pe_midcycle", "weight_before": 0.25, "weight_after": 0.125},
      ...
    ]
  },

  "scenarios": {                       # v6 yeni
    "bear": {"price": 84.17, "thesis": "..."},
    "base": {"price": 184.17, "thesis": "..."},
    "bull": {"price": 550.0, "thesis": "..."}
  },

  "ai_consultation": {                 # v6 yeni — sadece consult yapıldıysa
    "scenarios": {...},
    "rejim_degisikligi": {...},
    "cycle_phase": "mid",
    "framework_kritik": "...",
    "konsensus_aciklama": "...",
    "tavsiye": "...",
    "tavsiye_etiket": "MANUEL_REVIEW",
    "claude_confidence": 75,
    "model": "claude-opus-4-7"
  },

  "consultation": {                    # v6 yeni — meta
    "consulted": true,
    "should_consult": true,
    "severity": 0.80,
    "reason": "konsensüs_sapma_62%,düşük_güven_28",
    "model": "claude-opus-4-7",
    "duration_ms": 8500
  },

  "methods_used": [...],               # v6: original_weight alanı eklendi
  "methods_outliers": [...],
  "methods_excluded": [...],
  "methods_failed": [...],
  "market_regime": {...},
  "analyst_consensus": {...},
  "data_snapshot": {                   # v6: fwd_pe, peg_fmp, eps_growth eklendi
    ...
  }
}
```

## MU Testi (v5 vs v6)

| Metrik | v5 | v6 |
|--------|----|----|
| Karar | PAHALI | **MANUEL_REVIEW** (framework PAHALI, konsensüs ≠) |
| Güven | 72/100 | **28/100** |
| Fair value | $167 | $184 (mid-cycle ağırlıkları azaldı) |
| Cycle phase | yok | **reset** (yapısal rejim şüphesi) |
| `normalized_pe_midcycle` | w=25% | w=12% |
| `ev_ebitda_midcycle` | w=20% | w=10% |
| `price_to_book_capital_intensive` | w=10% | w=5% |
| Senaryolar | yok | Bear $84 / Base $184 / Bull $550 |
| AI consultation | yok | severity 0.80, blend %50 |

## Geri Uyumluluk

- `valuate()` fonksiyon imzası v5 ile uyumlu (yeni `consult_ai` parametresi opsiyonel default `"auto"`)
- Eski scriptler değişiklik gerektirmez:
  - `scripts/adil_deger_calculator.py`
  - `scripts/portfoy_adil_deger.py`
  - `scripts/telegram_bot.py`
  - `scripts/portfolio_scan_*.py`
- Çıktı dict'inde v5 alanları aynen var, v6 alanları yanlarına eklendi
- Cache key v5 ile uyumlu (`consult_ai="always"` modu cache atlar)

## Çevre Değişkenleri

```bash
# Zorunlu
FMP_API_KEY=g1GFJZtV5rCP49UCir4WuP56VjhmA6F8

# AI consultation için (Railway'da set edilmiş)
ANTHROPIC_API_KEY=...
CLAUDE_MODEL=claude-opus-4-7   # opsiyonel, default budur
```

`ANTHROPIC_API_KEY` yoksa AI consultation sessizce atlanır, framework v6 mekanik düzeltmeler (cycle phase, konsensüs cezası, senaryolar) yine de çalışır.

## Çağrı Örnekleri

```python
from valuation.framework import valuate, format_report

# Otomatik mod (default) — tetikleyici varsa AI'ye danışır
result = valuate("MU")
print(format_report(result, style="terminal"))

# Her zaman AI'ye danış (yavaş, API maliyeti)
result = valuate("MU", consult_ai="always")

# Sadece mekanik framework, AI yok
result = valuate("MU", consult_ai="never")
```

## Bilinen Sınırlamalar

1. **Cycle detection cyclical olmayan sektörler için bypass.** Tech (genel), Healthcare (genel), Communication Services tipik olarak non-cyclical kabul edilir. Sadece spesifik industry'ler (semiconductors, biotech vs.) cyclical override alır.
2. **Yapısal rejim aday listesi sabit.** Yeni rejim değişiklikleri (örn. uzay sektörü, nükleer rönesans) `STRUCTURAL_REGIME_CANDIDATES` dict'ine elle eklenmeli.
3. **AI consultation her tetikleyicide ~$0.05-0.15 maliyet** (Opus 4.7, ~3K input + ~1K output token). Günde 50 değerleme = ~$5/gün.
4. **Cache 5 dk TTL.** Aynı ticker için 5 dk içinde tekrar valuate çağrılırsa AI consultation tekrar yapılmaz. `consult_ai="always"` cache'i atlar.

## Sonraki İyileştirmeler (v7 düşünülen)

- Forward PE / PEG metodları için yeni archetype: `growth_at_reasonable_price`
- Yapısal rejim adayları için AI'ye "var mı?" sorusu (sabit liste yerine dinamik)
- Backtest: v5 tahminleri vs v6 tahminleri vs gerçek 90-gün fiyatları
- Sektör peer comparison metodu (önemli — peer'lerin median F/K'sı reference)
- Earnings revision momentum (forward EPS yukarı/aşağı revize trendi)
