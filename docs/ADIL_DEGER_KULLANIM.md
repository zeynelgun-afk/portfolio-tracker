---
title: Adil Değer Kullanım Kılavuzu
description: /deger AAPL, /q AAPL, /detay AAPL komutları. v7 Hybrid Plus (framework + Kimi) çıktı yapısı.
tags:
  - valuation
  - command
  - usage
  - bot
related:
  - "[[Index]]"
  - "[[VALUATION_SYSTEM_v6]]"
  - "[[VALUATION_FRAMEWORK_v5]]"
  - "[[FORWARD_VALUATION_METHOD]]"
---

# Adil Değer Hesaplayıcı — Kullanım Kılavuzu

Pine Script v3.5.2'nin Python uyarlaması. FMP API ile **252 günlük tarihsel
ortalamalar otomatik hesaplanır** — EV/EBIT, EV/EBITDA, EV/Ciro, P/E, P/S,
P/FCF hepsi Pine Script `historicalLookback=252` mantığıyla.

## Temel Kullanım

```bash
# Varsayılan: 252g dinamik ortalama (Pine Script birebir)
python3 scripts/adil_deger_calculator.py AMD

# Forward EPS analist konsensüsü ile (önerilir)
python3 scripts/adil_deger_calculator.py AMD --fwd-eps 5.00

# Faize dayalı F/K modu
python3 scripts/adil_deger_calculator.py DUK --pe-modu rate

# Manuel F/K
python3 scripts/adil_deger_calculator.py MSFT --pe-modu manuel --manuel-pe 28
```

## PE Modları

| Mod | Açıklama |
|-----|----------|
| `average` | 252g dinamik TTM P/E (varsayılan, Pine Script birebir) |
| `rate` | 10Y hazine faizine dayalı F/K (100/faiz) |
| `manuel` | Kullanıcı tanımlı F/K — `--manuel-pe` ile |

## Forward EPS Notu

FMP Premium forward EPS vermiyor. `--fwd-eps` girilmezse TTM×büyüme kullanılır.
Analist konsensüsünü manuel girmek için:
- Kaynak: TradingView, Seeking Alpha, Yahoo Finance → "EPS Estimate"

```bash
# AMD: 2026 analist konsensüsü ~$5.00
python3 scripts/adil_deger_calculator.py AMD --fwd-eps 5.00
```

## 10 Değerleme Metodu

| # | Metot | Çarpan Kaynağı |
|---|-------|----------------|
| 1 | Net Kazanç P/E | 252g tarihsel TTM P/E |
| 2 | ROE Bazlı | 252g tarihsel TTM P/E |
| 3 | EV/EBIT | 252g tarihsel EV/EBIT ortalaması (otomatik) |
| 4 | EV/EBITDA | 252g tarihsel EV/EBITDA ortalaması (otomatik) |
| 5 | EV/Ciro | 252g tarihsel EV/Ciro ortalaması (otomatik) |
| 6 | Forward P/E | Fwd EPS × mevcut piyasa fwd P/E (--fwd-eps ile) |
| 7 | Forward P/S | Fwd Ciro/Hisse × 252g P/S ortalaması |
| 8 | P/FCF | TTM FCF/Hisse × 252g P/FCF ortalaması |
| 9 | Graham Sayısı | √(22.5 × EPS × BVPS) — sadece değer hisseleri için |
| 10 | DCF | 5 yıllık İndirgenmiş Nakit Akışı |

## AMD Kalibrasyon Sonuçları

| Hesaplama | Sonuç |
|-----------|-------|
| Python (252g + `--fwd-eps 5.00`) | **$231** |
| TradingView Pine Script (average) | $218 |
| TradingView + analist beklentisi | $290 |
| FMP analist fiyat hedefi | $279 |

**~$13 fark** = FMP forward EPS kaynağı vs TradingView `request.earnings()`.
Kalan fark ihmal edilebilir; her iki araç da AMD'yi "adil değere yakın" gösteriyor.

## Güven Skoru

Metotlar arasındaki varyasyon katsayısına (CV) dayanır.
- **60+** → Metotlar yakınsıyor, güvenilir tahmin
- **40-60** → Orta güven, ek araştırma önerilir
- **<40** → Metotlar ıraksıyor (yüksek büyüme hissesi veya kriz senaryosu)
