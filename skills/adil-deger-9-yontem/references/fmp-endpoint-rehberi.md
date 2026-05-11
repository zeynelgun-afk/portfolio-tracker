# FMP Ultimate Plan Endpoint Rehberi (v5.0)

`scripts/fmp_layer.py` modülünün kullanım dokümantasyonu.

## Genel Yapı

```python
import fmp_layer

# Tüm fonksiyonlar 5dk TTL cache + 3 retry + statik fallback ile
data = fmp_layer.get_ratios_ttm("NVDA")
# data dict olarak gelir, retrieving döner None ise endpoint hatası
```

Cache temizlemek için:
```python
fmp_layer.clear_cache()
print(fmp_layer.cache_stats())  # {'entries': 12, 'ttl_seconds': 300}
```

## TIER 1 — TTM Bazlı Manuel Hesap Yerine

### `/ratios-ttm`
TTM finansal oranlar (P/E, P/B, ROE, marj'lar) HAZIR. Manuel hesap silindi.

```python
ratios = fmp_layer.get_ratios_ttm("NVDA")
# ratios['priceToEarningsRatioTTM']    # P/E TTM
# ratios['returnOnEquityTTM']          # ROE TTM (decimal)
# ratios['netProfitMarginTTM']         # net marj
# ratios['operatingProfitMarginTTM']   # faaliyet marjı
# ratios['grossProfitMarginTTM']       # brüt marj
```

### `/key-metrics-ttm`
EV, EV/Sales, EV/EBITDA, ROIC HAZIR.

```python
km = fmp_layer.get_key_metrics_ttm("NVDA")
# km['enterpriseValueTTM']
# km['evToSalesTTM']
# km['evToEBITDATTM']
```

### `/sector-pe-snapshot` + `/industry-pe-snapshot`
Canlı sektör/industry P/E. Statik tablonun yerini alır.

```python
pe, source = fmp_layer.get_live_pe_for_sector_key('semicon_design', static_fallback_pe=28)
# pe = 62.3 (canlı industry-pe-snapshot)
# source = 'industry' | 'sector' | 'static'
```

Sektör/industry adlandırması `SECTOR_KEY_TO_FMP` ve `INDUSTRY_KEY_TO_FMP` mapping'lerinde.

### `/historical-price-eod`
5 yıllık günlük OHLCV.

```python
prices = fmp_layer.get_historical_price_eod("NVDA", full=True)
# prices = [{'date': '2026-05-09', 'open': ..., 'close': ..., ...}]
```

### `/stock-peers`
Dinamik peer listesi.

```python
peers = fmp_layer.get_stock_peers("NVDA")
# peers = [{'symbol': 'AMD', 'companyName': 'Advanced Micro Devices', ...}]
```

## TIER 2 — Yeni Değerleme Sinyalleri

### `/financial-scores` (Altman Z + Piotroski)
İflas riski + fundamental kalite.

```python
scores = fmp_layer.get_financial_scores("NVDA")
# scores['altmanZScore']        # 68.23
# scores['piotroskiScore']      # 6

z, lbl, emoji = fmp_layer.interpret_altman_z(68.23)
# z = 68.23, lbl = 'GÜVENLİ', emoji = '🟢'

p, lbl, emoji = fmp_layer.interpret_piotroski(6)
# p = 6, lbl = 'SAĞLAM', emoji = '🟡'
```

Altman Z eşikleri (manufacturing standart):
- > 2.99: GÜVENLİ 🟢
- 1.81 - 2.99: BELİRSİZ 🟡
- < 1.81: İFLAS RİSKİ 🔴

Piotroski (0-9):
- 8-9: ÇOK GÜÇLÜ 🟢
- 5-7: SAĞLAM 🟡
- 3-4: ZAYIF 🟠
- 0-2: ÇOK ZAYIF 🔴

### `/grades-consensus` + `/grades-historical`
Analist sentiment + 6 ay momentum.

```python
gc = fmp_layer.get_grades_consensus("NVDA")
# gc['strongBuy'], gc['buy'], gc['hold'], gc['sell'], gc['strongSell']
# gc['consensus']  # 'Buy', 'Strong Buy', vs

gh = fmp_layer.get_grades_historical("NVDA")
momentum = fmp_layer.detect_upgrade_momentum(gh, lookback_months=6)
# momentum['direction']: 'upgrade' | 'downgrade' | 'stable'
# momentum['magnitude']: net delta (örn +5, -3)
# momentum['label']: '🟢 UPGRADE MOMENTUM (+5)' veya '🔴 DOWNGRADE TRENDI (-6)'
```

### `/discounted-cash-flow` + `/levered-discounted-cash-flow`
FMP'nin kendi DCF'i. Bizim DCF ile karşılaştırma için sanity check.

```python
dcf = fmp_layer.get_fmp_dcf("NVDA")
# dcf['dcf']: 247.15
# dcf['Stock Price']: 215.22

dcf_lev = fmp_layer.get_fmp_dcf("NVDA", levered=True)
# dcf_lev['dcf']: 257.86
```

%30+ sapmada uyarı verilmesi gerekir (varsayım farklılığı).

### `/revenue-product-segmentation` + `/revenue-geographic-segmentation`
Konsantrasyon riski tespiti.

```python
segs = fmp_layer.get_revenue_product_segmentation("NVDA")
risk = fmp_layer.detect_concentration_risk(segs)
# risk['top_segment']: 'Data Center'
# risk['top_share_pct']: 89.7
# risk['top2_share_pct']: 97.1
# risk['label']: '🔴 KRİTİK: Data Center %90'
# risk['fiscal_year']: '2026'
```

Eşikler:
- Top %70+: KRİTİK 🔴
- Top %50-70: YÜKSEK 🟠
- Top 2 %75+: ORTA 🟡
- Dağınık: 🟢

### `/enterprise-values`
5y tarihsel EV (multiple bandı için).

```python
ev = fmp_layer.get_enterprise_values("NVDA")
# ev = [{'date': '2026-01-26', 'enterpriseValue': ..., 'marketCap': ...}, ...]
```

## TIER 3 — Akıllı Varsayımlar

### `/treasury-rates` + CAPM
Canlı 10y treasury → dinamik WACC.

```python
rf = fmp_layer.get_10y_treasury_rate()
# rf = 0.0438 (decimal, %4.38)

wacc, source = fmp_layer.calculate_dynamic_wacc(beta=2.24)
# wacc = 0.1784 (decimal, %17.84)
# source = 'CAPM (Rf %4.38 + Beta 2.24 × ERP %6)'
```

CAPM formülü: `WACC = Rf + Beta × ERP (%6) + Country Risk (%0 ABD)`

Sınırlar:
- %8 altı: alt sınıra clip
- %18 üstü: üst sınıra clip
- %8-18 arası: CAPM kullanılır (override geçerli)
- Diğer: statik %10-12 fallback

### `/ipos-calendar`
Pre-IPO tespiti.

```python
pre_ipo = fmp_layer.is_ticker_pre_ipo("CBRS")
# pre_ipo['is_pre_ipo']: True
# pre_ipo['ipo_date']: '2026-05-13'
# pre_ipo['price_range']: '$150-$160'
# pre_ipo['exchange']: 'Nasdaq'
```

Önümüzdeki 60 gün içinde IPO oluyorsa True.

### `/financial-growth`
5y tarihsel büyüme oranları.

```python
growth = fmp_layer.get_financial_growth("NVDA")
# growth = [{'date': '2026-01-26', 'revenueGrowth': 0.655, 'ebitGrowth': ...}, ...]
```

## Hata Yönetimi

Tüm fonksiyonlar başarısızlıkta `None` döner. Skill bunu kontrol etmeli:

```python
ratios = fmp_layer.get_ratios_ttm("CBRS")  # FMP'de yok
if ratios is None:
    # FMP veri yok, fallback akış (pre-IPO modu vb)
```

Cache TTL: 5 dakika. Aynı oturumda tekrar çağrı cache'ten döner (FMP'ye yeniden istek atılmaz).

## Rate Limit

FMP Ultimate plan: 3000 calls/min. fmp_layer fonksiyonları otomatik retry yapıyor (429/503 için exponential backoff). Aynı oturumda 20+ endpoint çağırılırsa hız sınırına takılabilir.

## Statik Fallback Stratejisi

Canlı API down ise statik tablolardan fallback yapılır:
- SECTOR_MULTIPLES (skill içi) — sektör P/E, EV/Sales vs için
- REGIME_ADJ (skill içi) — WACC, k_e adj, peg_target için
- AI_MEGACAP_BULL_PREMIUM (skill içi) — boğa multiplier'ları

Kaynak: finzora ai
