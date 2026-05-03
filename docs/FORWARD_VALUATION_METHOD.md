---
title: Forward Valuation Yöntemi
description: Forward EPS bazlı değerleme metodu. Mid-cycle ile birleştirme.
tags:
  - valuation
  - forward
  - method
related:
  - "[[Index]]"
  - "[[VALUATION_SYSTEM_v6]]"
  - "[[VALUATION_FRAMEWORK_v5]]"
  - "[[ADIL_DEGER_KULLANIM]]"
---

# Forward Değerleme Metodolojisi — Finzora AI

> Son güncelleme: 9 Nisan 2026 | KESİN (FMP stable endpoint test edildi)

## 1. Doğru Endpoint

```
GET https://financialmodelingprep.com/stable/analyst-estimates
  ?symbol={SYM}&period=annual&page=0&limit=10&apikey={KEY}
```

### Alan adları (stable endpoint):
| Alan | Açıklama |
|---|---|
| `date` | Tahmin dönemi sonu (YYYY-12-31) |
| `epsAvg` | Analist konsensüs EPS tahmini |
| `epsHigh` / `epsLow` | Üst / alt tahmin aralığı |
| `revenueAvg` | Analist konsensüs gelir tahmini |
| `numAnalystsEps` | Tahmine katkıda bulunan analist sayısı |

**NOT:** `estimatedEpsAvg` DEĞİL, `epsAvg` kullan. (8 Nisan 2026 doğrulandı)

## 2. Forward P/E Hesabı

```python
# NTM (next twelve months) = mevcut takvim yılı tahmini
ntm_year = str(current_year)  # 2026
ntm_eps  = estimates[ntm_year]['epsAvg']

forward_pe = current_price / ntm_eps
```

## 3. EPS Büyüme Oranı

```python
import math
# 2 yıllık CAGR: NTM yılından +2 yıl ileriye
fwd2_eps   = estimates[str(current_year + 2)]['epsAvg']
eps_growth = (math.pow(fwd2_eps / ntm_eps, 0.5) - 1) * 100  # %
```

**Dikkat:** `eps_growth < 0` ise declining earnings — PEG anlamlı değil, değer tuzağı riski!

## 4. PEG Oranı

```python
peg = forward_pe / eps_growth  # eps_growth > 0 olmalı
```

| PEG | Yorum |
|---|---|
| < 1.0 | Ucuz (büyüme fiyata göre ucuz) |
| 1.0 – 1.5 | Adil değer |
| 1.5 – 2.5 | Biraz pahalı ama kaliteli olabilir |
| > 2.5 | Pahalı |
| EPS düşüyor | Değer tuzağı riski — PEG kullanma |

## 5. Falling Earnings Tuzağı (BMY Vakası)

BMY örneği (9 Nisan 2026):
- Trailing P/E: 17x → "ucuz görünüyor"
- Forward P/E: 9.4x → "çok ucuz görünüyor"  
- Ama: 2026E $6.26 → 2028E $5.45 = -%6.7/yıl düşüş
- Sonuç: Patent kayıpları (Eliquis 2027) fiyatlanmış. Değer tuzağı.

**Kural:** TTM P/E veya tek yıl forward P/E tek başına anlamsız.  
Her zaman 2-3 yıllık EPS trendini kontrol et.

## 6. MCO/Sağlık Sigortası Sektörü Özel Notu

Medicare Advantage rate riski (Ocak 2026): CMS %0.09 artış teklifi (beklenti %4-6).
Etkilenen: UNH (%20 düşüş), ELV (%31 düşüş), CVS (%14 düşüş)
Etkilenmeyen: CI (Medicare Advantage dışında çıkmış)

Önce Medicare Advantage exposure kontrol et:
- CI: Yok → düşük MCO riski  
- ELV: Var ama CMS uyum süreci + 2026 dip yıl
- UNH: Büyük exposure + gelir düşüşü → yüksek risk
- CVS: Aetna üzerinden var ama diversifiye

## 7. Script Referansı

```
scripts/portfolio_scan_balanced.py    → forward P/E + PEG + K-04 + K-13 filtresi
scripts/portfolio_scan_aggressive.py  → büyüme odaklı (LLY, REGN tipi)
scripts/portfolio_scan_dividend.py    → yield + PEG + payout + FCF yield
```

> Kaynak atfı: finzora ai | FMP stable API
