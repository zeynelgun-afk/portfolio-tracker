---
name: fmp-integration
description: Comprehensive guide for integrating Financial Modeling Prep (FMP) API, covering stable endpoints, migration from legacy versions, and usage examples. Use this skill whenever AI needs to fetch real financial data from FMP API including stock quotes, financial statements, technical indicators, earnings data, analyst estimates, screener, news, insider trading, ETF holdings, economic calendar, and more. This is the master reference for ALL FMP API calls.
---

# FMP API Integration — Premium Plan Reference

> **Last verified**: 19 April 2026 | **Plan**: Premium | **Base URL**: `https://financialmodelingprep.com/stable/`

---

## Authentication

```
https://financialmodelingprep.com/stable/quote?symbol=AAPL&apikey=YOUR_API_KEY
```

API key always goes as `apikey` query parameter. Key is stored in user memory.

---

## Plan Limits (Premium)

| Item | Value |
|------|-------|
| Daily calls | Sınırsız |
| Calls per minute | 2,500 |
| Bandwidth (30-day) | 50GB |
| Historical data | 30+ years |
| Coverage | US, UK, Canada |

> **⚠️ CRITICAL**: Legacy `/api/v3/` and `/api/v4/` routes are **completely blocked** (403 "Legacy Endpoint" error). **Always use `/stable/` only.**

---

## ⚠️ KRİTİK: ALAN ADI TUZAKLARI (Field Name Gotchas)

> **19 Nisan 2026 — Doğrulanmış kritik hatalar.** Bu alan isimleri Python `.get(key, 0)` ile sessizce yanlış (0/None) döner, hiçbir hata fırlatmaz. FMP dokümanları bazen eski/yanlış adları gösterir.
>
> **⚠️ FMP kendi içinde tutarsızdır** — aynı konsept için farklı endpoint'lerde farklı alan adı kullanılır. Endpoint'e göre doğrulamak şart.

### Yüzde Değişim Alanı (endpoint'e göre değişiyor!)

| Endpoint | ✅ Doğru Alan | Not |
|----------|---------------|-----|
| `quote`, `batch-quote`, `profile` | **`changePercentage`** (TEKİL) | `changesPercentage` DEĞİL, `.get("changesPercentage",0)` sessiz 0 döner |
| `biggest-gainers`, `biggest-losers`, `most-actives` | **`changesPercentage`** (ÇOĞUL) | Burada çoğul doğru — FMP'nin kendi tutarsızlığı |
| `sector-performance-snapshot`, `industry-performance-snapshot` | **`averageChange`** | Ne "change" ne "changesPercentage" — tamamen farklı |
| `stock-price-change` | `1D`, `5D`, `1M`, `3M`, `6M`, `ytd`, `1Y`, ... | Alanlar dönem adı; `ytd` küçük harf |

### Diğer Alan Adı Tuzakları

| ❌ YANLIŞ Alan (yaygın hata) | ✅ DOĞRU Alan | Etkilenen Endpoint'ler |
|------------------------------|---------------|-----------------------|
| `estimatedEpsAvg` | **`epsAvg`** | analyst-estimates |
| `estimatedEpsHigh` | **`epsHigh`** | analyst-estimates |
| `estimatedEpsLow` | **`epsLow`** | analyst-estimates |
| `numberAnalystsEstimatedEps` | **`numAnalystsEps`** | analyst-estimates |
| `numberAnalystEstimatedRevenue` | **`numAnalystsRevenue`** | analyst-estimates |
| `actualEPS` / `estimatedEPS` | **`epsActual`** / **`epsEstimated`** | earnings |
| `actualRevenue` / `estimatedRevenue` | **`revenueActual`** / **`revenueEstimated`** | earnings |

**⚠️ NEDEN TEHLİKELİ**: `quote.get("changesPercentage", 0)` HER ZAMAN `0` döner çünkü quote endpoint'inde bu alan yok (asıl ad `changePercentage`, tekil). "Piyasa dışında 0 dönüyor, manuel hesaplayalım" diye yorumlanır ama aslında alan hep yoktur — kod sessiz sessiz yanlış çalışır.

**TEST YAKLAŞIMI**: Yeni bir endpoint kullanmadan önce `curl -s 'URL' | jq 'keys'` ile gerçek alan adlarını doğrula. Production kodunda doğrudan `dict["key"]` (KeyError fırlatır) kullan, `.get()` sadece varsayılan gerçekten makulse.

---

## Standard Python Pattern

```python
import requests

FMP_API_KEY = "YOUR_API_KEY"  # From user memory
FMP_BASE = "https://financialmodelingprep.com/stable"

def fmp_get(endpoint, params=None):
    if params is None:
        params = {}
    params['apikey'] = FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and 'Error Message' in data:
            print(f"FMP Error: {data['Error Message']}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
```

---

## ✅ VERIFIED ENDPOINTS (Tested Feb 2026)

### ⚠️ CRITICAL: Endpoint Name Traps

Many endpoints were renamed. Wrong names silently return `[]`. Always use these:

| ❌ Wrong Name (404) | ✅ Correct Name | Notes |
|---|---|---|
| `market-biggest-gainers` | `biggest-gainers` | |
| `market-biggest-losers` | `biggest-losers` | |
| `market-most-active` | `most-actives` | |
| `enterprise-value` | `enterprise-values` | plural |
| `sector-performance` | `sector-performance-snapshot` | + requires `date` param |
| `press-releases` | `news/press-releases` | under news/ prefix |
| `news/general` | `fmp-articles` | completely renamed |
| `rating` | `ratings-snapshot` | completely renamed |
| `financial-score` | `financial-scores` | plural |
| `earnings-surprises` / `earnings-surprise` | `earnings` | earnings endpoint'i hem geçmiş hem gelecek veriyor; surprise manuel hesaplanır |
| `historical-earnings` / `earnings-historical` | `earnings` | tek endpoint — limit param ile geçmiş tahmini dönüyor |

---

### 1. SEARCH & DIRECTORY

| Endpoint | Params | Description |
|----------|--------|-------------|
| `search-symbol` | `query` | Ticker search |
| `search-name` | `query` | Company name search |
| `company-screener` | see below | Multi-filter screener |
| `stock-list` | `limit` | 48,000+ symbols |
| `etf-list` | `limit` | 9,700+ ETFs |
| `actively-trading-list` | `limit` | Currently trading |
| `symbol-change` | `page`, `limit` | Ticker changes |
| `available-exchanges` | — | 73 exchanges |
| `available-sectors` | — | 11 sectors |
| `available-industries` | — | 159 industries |
| `available-countries` | — | 117 countries |

**Screener params**: `marketCapMoreThan`, `marketCapLowerThan`, `priceMoreThan`, `priceLowerThan`, `betaMoreThan`, `betaLowerThan`, `volumeMoreThan`, `volumeLowerThan`, `dividendMoreThan`, `dividendLowerThan`, `isEtf`, `isFund`, `isActivelyTrading`, `sector`, `industry`, `country`, `exchange`, `limit`

```python
screener = fmp_get("company-screener", {
    "marketCapMoreThan": 2000000000,
    "sector": "Energy",
    "exchange": "NYSE,NASDAQ",
    "isActivelyTrading": "true",
    "limit": 50
})
```

---

### 2. COMPANY PROFILE

| Endpoint | Params | Description |
|----------|--------|-------------|
| `profile` | `symbol` | Full profile (price, mktcap, sector, CEO, desc) |
| `stock-peers` | `symbol` | Same-sector peers |
| `market-capitalization` | `symbol` | Current market cap |
| `market-capitalization-batch` | `symbols` | Comma-sep batch |
| `historical-market-capitalization` | `symbol`, `from`, `to`, `limit` | Historical mktcap |
| `key-executives` | `symbol` | CEO, CFO, etc. |
| `governance-executive-compensation` | `symbol` | Compensation data |
| `employee-count` | `symbol` | Current headcount |
| `historical-employee-count` | `symbol` | Historical headcount |
| `shares-float` | `symbol` | Float & outstanding |
| `shares-float-all` | `page`, `limit` | All companies |
| `delisted-companies` | `page`, `limit` | Delisted stocks |
| `mergers-acquisitions-latest` | `page`, `limit` | Recent M&A |
| `mergers-acquisitions-search` | `name` | Search M&A |

---

### 3. QUOTES

| Endpoint | Params | Description |
|----------|--------|-------------|
| `quote` | `symbol` | Full quote — stocks, ETF, forex, crypto, commodity |
| `quote-short` | `symbol` | Price + volume only |
| `batch-quote` | `symbols` | Comma-sep multiple |
| `batch-quote-short` | `symbols` | Comma-sep condensed |
| `stock-price-change` | `symbol` | % change 1D/5D/1M/3M/6M/YTD/1Y/3Y/5Y/10Y/max |
| `aftermarket-quote` | `symbol` | Pre/post-market |
| `aftermarket-trade` | `symbol` | Post-market trades |

```python
# Portfolio batch quote
quotes = fmp_get("batch-quote", {"symbols": "SM,KOS,MO,XLE,RGLD,FCX"})
# Forex/Crypto/Commodity — same endpoint
eurusd = fmp_get("quote", {"symbol": "EURUSD"})
btc = fmp_get("quote", {"symbol": "BTCUSD"})
gold = fmp_get("quote", {"symbol": "GCUSD"})

# Index sembolleri — ÇALIŞIR (19 Nisan 2026 doğrulandı)
vix = fmp_get("quote", {"symbol": "^VIX"})    # CBOE Volatility Index
spx = fmp_get("quote", {"symbol": "^GSPC"})   # S&P 500 Index
ndx = fmp_get("quote", {"symbol": "^IXIC"})   # Nasdaq Composite
```

> **✅ quote alanları** (19 Nisan 2026 doğrulandı — stocks, ETF, forex, crypto, commodity, index hepsi aynı):
>
> `symbol, name, price, changePercentage, change, volume, dayLow, dayHigh, yearHigh, yearLow, marketCap, priceAvg50, priceAvg200, exchange, open, previousClose, timestamp`
>
> **KRİTİK**: Alan adı `changePercentage` (TEKİL) — `changesPercentage` DEĞİL. Bkz. "Alan Adı Tuzakları" bölümü.

> **✅ `^VIX` endpoint ÇALIŞIYOR** (19 Nisan 2026): Skill'de önceden "VIX için sadece web search" yazıyordu — bu bilgi artık eski. FMP `^VIX` stabil şekilde gerçek VIX değerini döndürüyor. VIXY proxy'ye (contango riski) gerek yok.

> **⚠️ aftermarket-quote farklı şema**: Alanlar `symbol, bidSize, bidPrice, askSize, askPrice, volume, timestamp`. `price` alanı **YOKTUR** — fiyat için `(bidPrice + askPrice) / 2` hesaplanmalı. Seans dışı son tick bid/ask değerini döner.

---

### 4. HISTORICAL PRICES

| Endpoint | Params | Description |
|----------|--------|-------------|
| `historical-price-eod/full` | `symbol`, `from`, `to`, `limit` | Full OHLCV daily |
| `historical-price-eod/light` | `symbol`, `from`, `to`, `limit` | Date + close only |
| `historical-chart/1min` | `symbol`, `from`, `to` | 1-min intraday |
| `historical-chart/5min` | `symbol`, `from`, `to` | 5-min intraday |
| `historical-chart/15min` | `symbol`, `from`, `to` | 15-min intraday |
| `historical-chart/30min` | `symbol`, `from`, `to` | 30-min intraday |
| `historical-chart/1hour` | `symbol`, `from`, `to` | 1-hour intraday |
| `historical-chart/4hour` | `symbol`, `from`, `to` | 4-hour intraday |

Works for stocks, ETFs, forex pairs, crypto, and commodities.

```python
prices = fmp_get("historical-price-eod/full", {
    "symbol": "AAPL", "from": "2025-01-01", "to": "2026-02-20"
})
intraday = fmp_get("historical-chart/1hour", {
    "symbol": "AAPL", "from": "2026-02-18", "to": "2026-02-20"
})
```

---

### 5. FINANCIAL STATEMENTS

| Endpoint | Params | Description |
|----------|--------|-------------|
| `income-statement` | `symbol`, `period`, `limit` | P&L |
| `balance-sheet-statement` | `symbol`, `period`, `limit` | Balance sheet |
| `cash-flow-statement` | `symbol`, `period`, `limit` | Cash flows |
| `income-statement-growth` | `symbol`, `period`, `limit` | Growth rates |
| `enterprise-values` | `symbol`, `period`, `limit` | EV (**plural, not singular**) |
| `revenue-product-segmentation` | `symbol` | Revenue by product |
| `revenue-geographic-segmentation` | `symbol` | Revenue by geography |

**period**: `annual` or `quarter`

```python
income = fmp_get("income-statement", {"symbol": "AAPL", "period": "quarter", "limit": 8})
ev = fmp_get("enterprise-values", {"symbol": "AAPL", "period": "annual", "limit": 5})
geo = fmp_get("revenue-geographic-segmentation", {"symbol": "AAPL"})
```

---

### 6. RATIOS, METRICS & SCORES

| Endpoint | Params | Description |
|----------|--------|-------------|
| `ratios` | `symbol`, `period`, `limit` | All financial ratios |
| `ratios-ttm` | `symbol` | TTM ratios (60+ alan) |
| `key-metrics` | `symbol`, `period`, `limit` | Key metrics |
| `key-metrics-ttm` | `symbol` | TTM key metrics (42+ alan) |
| `discounted-cash-flow` | `symbol` | DCF valuation |
| `owner-earnings` | `symbol` | Owner earnings |
| `ratings-snapshot` | `symbol` | Overall rating + sub-scores (**NOT `rating`**) |
| `financial-scores` | `symbol` | Altman Z-score, Piotroski score (**NOT `financial-score`**) |

> **✅ ratios-ttm önemli alanlar** (19 Nisan 2026 doğrulandı — TTM suffix'li):
> - Değerleme: `priceToEarningsRatioTTM`, `priceToBookRatioTTM`, `priceToSalesRatioTTM`, `priceToFreeCashFlowRatioTTM`, `priceToOperatingCashFlowRatioTTM`, `priceToEarningsGrowthRatioTTM`, `enterpriseValueMultipleTTM`, `priceToFairValueTTM`
> - Kârlılık: `grossProfitMarginTTM`, `operatingProfitMarginTTM`, `netProfitMarginTTM`, `ebitdaMarginTTM`, `ebitMarginTTM`
> - Borç: `debtToEquityRatioTTM`, `debtToAssetsRatioTTM`, `debtToCapitalRatioTTM`, `debtToMarketCapTTM`, `interestCoverageRatioTTM`, `financialLeverageRatioTTM`
> - Likidite: `currentRatioTTM`, `quickRatioTTM`, `cashRatioTTM`, `solvencyRatioTTM`
> - Temettü: `dividendYieldTTM`, `dividendPayoutRatioTTM`, `dividendPerShareTTM`
> - Diğer: `effectiveTaxRateTTM`, `enterpriseValueTTM`, `bookValuePerShareTTM`, `revenuePerShareTTM`, `freeCashFlowPerShareTTM`

> **✅ key-metrics-ttm önemli alanlar** (19 Nisan 2026 doğrulandı):
> - `marketCap`, `enterpriseValueTTM`, `evToSalesTTM`, `evToEBITDATTM`, `evToFreeCashFlowTTM`, `evToOperatingCashFlowTTM`, `netDebtToEBITDATTM`
> - `returnOnEquityTTM`, `returnOnAssetsTTM`, `returnOnInvestedCapitalTTM`, `returnOnCapitalEmployedTTM`, `returnOnTangibleAssetsTTM`
> - `earningsYieldTTM`, `freeCashFlowYieldTTM`, `incomeQualityTTM`, `grahamNumberTTM`, `grahamNetNetTTM`
> - `workingCapitalTTM`, `investedCapitalTTM`, `capexToRevenueTTM`, `capexToOperatingCashFlowTTM`, `researchAndDevelopementToRevenueTTM`

> **✅ ratings-snapshot alanları**: `symbol, rating, overallScore, discountedCashFlowScore, returnOnEquityScore, returnOnAssetsScore, debtToEquityScore, priceToEarningsScore, priceToBookScore` — rating A-F arası harf, skorlar 1-5 arası tam sayı.

> **✅ financial-scores alanları**: `symbol, reportedCurrency, altmanZScore, piotroskiScore, workingCapital, totalAssets, retainedEarnings, ebit, marketCap, totalLiabilities, revenue`

```python
rating = fmp_get("ratings-snapshot", {"symbol": "AAPL"})
# Returns: symbol, rating, overallScore, discountedCashFlowScore, etc.

scores = fmp_get("financial-scores", {"symbol": "AAPL"})
# Returns: altmanZScore, piotroskiScore, workingCapital, etc.
```

---

### 7. ANALYST & GRADES

| Endpoint | Params | Description |
|----------|--------|-------------|
| `analyst-estimates` | `symbol`, `period`, `limit` | EPS/revenue estimates |

> **⚠️ analyst-estimates Response Field Names** (10 Nisan 2026 doğrulandı):
> - `epsAvg` (NOT `estimatedEpsAvg`)
> - `epsHigh`, `epsLow`
> - `numAnalystsEps` (NOT `numberAnalystsEstimatedEps`)
> - `numAnalystsRevenue` (NOT `numberAnalystEstimatedRevenue`)
> - `date` formatı: fiscal year-end tarihi (örn. `"2027-01-25"`)
> - En yakın 2 tahmini almak için: tarih > bugün-180gün filtrele, ascending sırala

| `analyst-recommendations` | `symbol`, `limit` | Buy/sell recs |
| `price-target` | `symbol`, `limit` | Individual price targets |
| `price-target-summary` | `symbol` | Aggregated target stats |
| `upgrades-downgrades` | `symbol`, `limit` | Rating changes |
| `upgrades-downgrades-consensus` | `symbol` | Consensus rating |
| `grades` | `symbol`, `limit` | Analyst stock grades (all companies) |
| `grades-consensus` | `symbol` | StrongBuy/Buy/Hold/Sell/StrongSell counts |

```python
grades = fmp_get("grades", {"symbol": "AAPL", "limit": 20})
consensus = fmp_get("grades-consensus", {"symbol": "AAPL"})
# Returns: strongBuy, buy, hold, sell, strongSell counts
```

---

### 8. MARKET MOVERS ⚠️

```python
# ✅ CORRECT names
gainers = fmp_get("biggest-gainers", {"limit": 20})
losers = fmp_get("biggest-losers", {"limit": 20})
active = fmp_get("most-actives", {"limit": 20})

# ❌ WRONG — these return 404
# fmp_get("market-biggest-gainers")
# fmp_get("market-most-active")
```

---

### 9. MARKET PERFORMANCE ⚠️ Requires `date` param!

| Endpoint | Required Params | Description |
|----------|----------------|-------------|
| `sector-performance-snapshot` | `date=YYYY-MM-DD` | All sectors daily change |
| `industry-performance-snapshot` | `date=YYYY-MM-DD` | All industries daily change |
| `historical-sector-performance` | `sector=Technology` | Historical sector perf |
| `sector-pe-snapshot` | `date=YYYY-MM-DD` | Sector P/E ratios |
| `industry-pe-snapshot` | `date=YYYY-MM-DD` | Industry P/E ratios |
| `historical-sector-pe` | `sector=Technology` | Historical sector P/E |

```python
from datetime import datetime, timedelta
today = datetime.now().strftime("%Y-%m-%d")

# ✅ CORRECT — must include date
sectors = fmp_get("sector-performance-snapshot", {"date": today})
# Returns: date, sector, exchange, averageChange

# Get all sectors snapshot
industries = fmp_get("industry-performance-snapshot", {"date": today})

# Historical sector performance
tech_hist = fmp_get("historical-sector-performance", {
    "sector": "Technology",
    "from": "2026-01-01",
    "to": "2026-02-20"
})

# ❌ WRONG — returns 404
# fmp_get("sector-performance")
```

> **⚠️ Piyasa kapalı günü uyarısı** (19 Nisan 2026): Pazar/Cumartesi/tatil günlerinde bugünün tarihiyle `sector-performance-snapshot` **boş `[]` döner**. Son iş gününe düş:
> ```python
> from datetime import datetime, timedelta
> d = datetime.now()
> # Cumartesi(5)/Pazar(6) ise en son Cuma'ya in
> if d.weekday() >= 5:
>     d = d - timedelta(days=d.weekday() - 4)
> sectors = fmp_get("sector-performance-snapshot", {"date": d.strftime("%Y-%m-%d")})
> ```
> Tatil günleri için benzer şekilde bir önceki iş gününe düşmek gerekir. Aynı kural `industry-performance-snapshot`, `sector-pe-snapshot`, `industry-pe-snapshot` için de geçerli.

**Valid sector names**: `Technology`, `Healthcare`, `Financial Services`, `Energy`, `Consumer Cyclical`, `Industrials`, `Consumer Defensive`, `Basic Materials`, `Real Estate`, `Communication Services`, `Utilities`

---

### 10. INDEXES (Premium — Accessible)

```python
sp500 = fmp_get("sp500-constituent")       # 503 stocks
nasdaq = fmp_get("nasdaq-constituent")     # 101 stocks
dow = fmp_get("dowjones-constituent")      # 30 stocks
```

---

### 11. TECHNICAL INDICATORS

| Endpoint | Params | Timeframes |
|----------|--------|------------|
| `technical-indicators/sma` | `symbol`, `periodLength`, `timeframe` | 1min, 5min, 15min, 30min, 1hour, 4hour, 1day |
| `technical-indicators/ema` | same | same |
| `technical-indicators/rsi` | same | same |
| `technical-indicators/macd` | same | same |
| `technical-indicators/adx` | same | same |
| `technical-indicators/williams` | same | same |
| `technical-indicators/roc` | same | same |

```python
rsi = fmp_get("technical-indicators/rsi", {"symbol": "AAPL", "periodLength": 14, "timeframe": "1day"})
sma200 = fmp_get("technical-indicators/sma", {"symbol": "AAPL", "periodLength": 200, "timeframe": "1day"})
macd = fmp_get("technical-indicators/macd", {"symbol": "AAPL", "periodLength": 12, "timeframe": "1day"})
```

---

### 12. NEWS ⚠️ Correct endpoints!

| Endpoint | Params | Description |
|----------|--------|-------------|
| `news/stock` | `symbols` (comma-sep), `limit` | Stock news ✅ |
| `news/press-releases` | `symbol`, `limit` | Press releases ✅ (**NOT `press-releases`**) |
| `news/crypto` | `limit` | Crypto news ✅ |
| `news/forex` | `limit` | Forex news ✅ |
| `fmp-articles` | `limit` | FMP market articles ✅ (**NOT `news/general`**) |

```python
# Stock news
news = fmp_get("news/stock", {"symbols": "AAPL,MSFT", "limit": 20})
# Portfolio news
port_news = fmp_get("news/stock", {"symbols": "SM,KOS,MO,XLE,RGLD,FCX", "limit": 30})

# Press releases
pr = fmp_get("news/press-releases", {"symbol": "AAPL", "limit": 10})

# General market articles
articles = fmp_get("fmp-articles", {"limit": 20})

# ❌ WRONG — these return 404
# fmp_get("press-releases", {"symbol": "AAPL"})
# fmp_get("news/general")
```

---

### 13. EARNINGS & CALENDAR

| Endpoint | Params | Description |
|----------|--------|-------------|
| `earnings` | `symbol`, `limit` | **Past + future earnings birlikte** — epsActual, epsEstimated, revenueActual, revenueEstimated |
| `earnings-calendar` | `from`, `to` | Upcoming earnings (max 90 days) |
| `analyst-estimates` | `symbol`, `period`, `limit` | EPS/revenue estimates |
| `dividends` | `symbol`, `limit` | Dividend history |
| `stock-split-calendar` | `from`, `to` | Stock splits |
| `ipo-calendar` | `from`, `to` | IPO calendar |
| `economic-calendar` | `from`, `to` | Economic events |

> **✅ Earnings Surprise Hesaplama** (19 Nisan 2026 — doküman güncellemesi): Eski dokümanlar `earnings-surprises` endpoint'ine işaret ediyordu; **bu endpoint FMP'de mevcut değildir (404)**, Ultimate plan meselesi de değildir. Doğru endpoint: **`earnings`** (tekil, parametresiz isim).
>
> ```python
> earnings = fmp_get("earnings", {"symbol": "AAPL", "limit": 10})
> # Alanlar: symbol, date, epsActual, epsEstimated, revenueActual, revenueEstimated, lastUpdated
> # epsActual == None → gelecek earnings (henüz açıklanmadı)
> # epsActual != None → geçmiş earnings
> for e in earnings:
>     if e["epsActual"] is not None:
>         surprise_pct = ((e["epsActual"] - e["epsEstimated"]) / e["epsEstimated"]) * 100
>         print(f"{e['date']}: EPS surprise {surprise_pct:+.2f}%")
> ```

> **✅ dividends alanları** (19 Nisan 2026 doğrulandı):
> `symbol, date, recordDate, paymentDate, declarationDate, adjDividend, dividend, yield, frequency`
> `frequency` değerleri: `Quarterly`, `Semi-Annual`, `Annual`, `Monthly`.

---

### 14. INSIDER & INSTITUTIONAL

| Endpoint | Params | Description |
|----------|--------|-------------|
| `insider-trading` | `symbol`, `limit` | Insider transactions |
| `insider-trading-statistics` | `symbol` | Insider summary stats |
| `institutional-holders` | `symbol`, `limit` | Institutional ownership |
| `senate-trading` | `symbol`, `limit` | Congressional trades |
| `form-13f` | `cik`, `date` | 13F filing data |
| `form-13f-filing-dates` | `cik` | Available 13F dates |

---

### 15. ETF

| Endpoint | Params | Description |
|----------|--------|-------------|
| `etf/holdings` | `symbol`, `date` | ETF constituents |
| `etf/info` | `symbol` | ETF details |
| `etf/sector-weightings` | `symbol` | Sector breakdown |
| `etf/country-weightings` | `symbol` | Country breakdown |

---

### 16. ECONOMICS

| Endpoint | Params | Description |
|----------|--------|-------------|
| `treasury-rates` | `from`, `to` | US treasury yields |
| `economic-indicators` | `name`, `from`, `to` | GDP, CPI, unemployment, etc. |
| `market-risk-premium` | `date` | Country risk premiums |

---

### 17. FOREX / CRYPTO / COMMODITIES

Use standard `quote` and `historical-price-eod/full` with appropriate symbols:

```python
fmp_get("forex-list")           # All forex symbols
fmp_get("crypto-list")          # All crypto symbols
fmp_get("commodity-list")       # All commodity symbols

# Quotes work for all asset types
fmp_get("quote", {"symbol": "EURUSD"})   # Forex
fmp_get("quote", {"symbol": "BTCUSD"})   # Crypto
fmp_get("quote", {"symbol": "GCUSD"})    # Gold
fmp_get("quote", {"symbol": "CLUSD"})    # Crude Oil

# Historical works for all
fmp_get("historical-price-eod/full", {"symbol": "BTCUSD", "from": "2025-01-01"})
```

---

## 🔒 NOT Available on Premium (Requires Ultimate)

| Feature | Plan Needed |
|---------|-------------|
| Earnings Call Transcripts (`earnings-transcript-list`) | Ultimate (402) |
| ETF & Mutual Fund Holdings (full) | Ultimate |
| 13F Institutional Holdings (full analytics) | Ultimate |
| 1-Minute Intraday Charting | Ultimate |
| `income-statement-ttm` | Returns 402 |
| Bulk delivery endpoints | Ultimate |

---

## READY-TO-USE WORKFLOWS

### Portfolio Monitoring
```python
symbols = "SM,KOS,MO,XLE,RGLD,FCX"
quotes = fmp_get("batch-quote", {"symbols": symbols})
news = fmp_get("news/stock", {"symbols": symbols, "limit": 30})
for sym in symbols.split(","):
    change = fmp_get("stock-price-change", {"symbol": sym})
```

### Market Overview
```python
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")

gainers = fmp_get("biggest-gainers", {"limit": 20})
losers = fmp_get("biggest-losers", {"limit": 20})
active = fmp_get("most-actives", {"limit": 20})
sectors = fmp_get("sector-performance-snapshot", {"date": today})
articles = fmp_get("fmp-articles", {"limit": 10})
econ = fmp_get("economic-calendar", {"from": today, "to": "2026-02-28"})
```

### Fundamental Analysis
```python
symbol = "AAPL"
profile = fmp_get("profile", {"symbol": symbol})
income = fmp_get("income-statement", {"symbol": symbol, "period": "annual", "limit": 5})
balance = fmp_get("balance-sheet-statement", {"symbol": symbol, "period": "annual", "limit": 5})
cashflow = fmp_get("cash-flow-statement", {"symbol": symbol, "period": "annual", "limit": 5})
metrics = fmp_get("key-metrics-ttm", {"symbol": symbol})
ratios = fmp_get("ratios-ttm", {"symbol": symbol})
dcf = fmp_get("discounted-cash-flow", {"symbol": symbol})
ev = fmp_get("enterprise-values", {"symbol": symbol, "period": "annual", "limit": 5})
rating = fmp_get("ratings-snapshot", {"symbol": symbol})
scores = fmp_get("financial-scores", {"symbol": symbol})
geo_rev = fmp_get("revenue-geographic-segmentation", {"symbol": symbol})
peers = fmp_get("stock-peers", {"symbol": symbol})
```

### Technical Analysis
```python
symbol = "TSLA"
prices = fmp_get("historical-price-eod/full", {"symbol": symbol, "from": "2025-08-01"})
rsi = fmp_get("technical-indicators/rsi", {"symbol": symbol, "periodLength": 14, "timeframe": "1day"})
sma20 = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 20, "timeframe": "1day"})
sma50 = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 50, "timeframe": "1day"})
sma200 = fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 200, "timeframe": "1day"})
macd = fmp_get("technical-indicators/macd", {"symbol": symbol, "periodLength": 12, "timeframe": "1day"})
adx = fmp_get("technical-indicators/adx", {"symbol": symbol, "periodLength": 14, "timeframe": "1day"})
```

### Analyst & Sentiment
```python
symbol = "META"
estimates = fmp_get("analyst-estimates", {"symbol": symbol, "period": "quarter", "limit": 8})
targets = fmp_get("price-target-summary", {"symbol": symbol})
consensus = fmp_get("grades-consensus", {"symbol": symbol})
upgrades = fmp_get("upgrades-downgrades", {"symbol": symbol, "limit": 20})
insider = fmp_get("insider-trading", {"symbol": symbol, "limit": 50})
```

---

## ERROR HANDLING

| Status | Cause | Fix |
|--------|-------|-----|
| `404` + empty `[]` | Wrong endpoint name | Check correct name in this skill |
| `402` Restricted | Not in Premium plan | Requires Ultimate |
| `403` Legacy | Used v3/v4 route | Switch to `/stable/` |
| `400` Query Error | Missing required param | Add `date`, `sector`, etc. |
| `{"Error Message": "Limit Reach"}` | Per-minute limit hit (2500/dk) | Kısa bekle, retry |
| `{"Error Message": "Invalid API KEY"}` | Wrong key | Check memory |
| Empty `[]` with `200` | No data for params | Check symbol, date range |

```python
import time

def fmp_get_retry(endpoint, params=None, max_retries=3):
    for attempt in range(max_retries):
        result = fmp_get(endpoint, params)
        if result is not None and result != []:
            return result
        time.sleep(2 ** attempt)
    return None
```

---

## LEGACY ENDPOINT MAPPING

All v3/v4 routes are **blocked**. Use these stable equivalents:

| Legacy (BLOCKED) | Stable ✅ |
|------------------|-----------|
| `/api/v3/quote/AAPL` | `/stable/quote?symbol=AAPL` |
| `/api/v3/income-statement/AAPL` | `/stable/income-statement?symbol=AAPL` |
| `/api/v3/historical-price-full/AAPL` | `/stable/historical-price-eod/full?symbol=AAPL` |
| `/api/v3/technical_indicator/daily/AAPL?type=rsi&period=14` | `/stable/technical-indicators/rsi?symbol=AAPL&periodLength=14&timeframe=1day` |
| `/api/v3/earning_calendar` | `/stable/earnings-calendar` |
| `/api/v3/stock_news` | `/stable/news/stock` |
| `/api/v3/stock-screener` | `/stable/company-screener` |
| `/api/v3/discounted-cash-flow/AAPL` | `/stable/discounted-cash-flow?symbol=AAPL` |
| `/api/v3/biggest-gainers` | `/stable/biggest-gainers` |

**Key changes**:
- Symbols moved from path to query param: `/AAPL` → `?symbol=AAPL`
- Technical indicators: `type=rsi` → URL path `/rsi`; `period` → `periodLength`
- News reorganized under `/news/` prefix
- Screener: `stock-screener` → `company-screener`
- Market movers renamed (remove `market-` prefix)
- Enterprise value: singular → plural (`enterprise-values`)

---

## CHANGELOG

### 19 Nisan 2026 — Kritik alan adı düzeltmeleri
- **Alan Adı Tuzakları bölümü eklendi** — `changesPercentage` (YANLIŞ) → `changePercentage` (DOĞRU), `estimatedEpsAvg` → `epsAvg`, `actualEPS` → `epsActual`, vs. Python `.get(k, 0)` ile sessiz 0 dönüşünün kaynağı bu alanlardı.
- **`earnings` endpoint eklendi** — eski belgedeki "earnings-surprises Ultimate gerekir" bilgisi yanlıştı: endpoint hem Premium hem Ultimate'da mevcut değil, doğrusu `earnings` (tekil). Geçmiş + gelecek tahmin aynı yanıtta.
- **`^VIX` çalışıyor notu eklendi** — Eski notlarda "402 döner, web search gerekli" yazıyordu, bu artık geçerli değil. Tüm index sembolleri (^VIX, ^GSPC, ^IXIC) standart `quote` ile alınıyor.
- **`aftermarket-quote` şema uyarısı eklendi** — `price` alanı yok, sadece `bidPrice/askPrice`. Manual midpoint hesabı gerekir.
- **Pazar/tatil günü sector-performance boş dönüş uyarısı** — date parametresi piyasa kapalı günü için boş `[]` döner.
- **ratios-ttm (60+ alan) ve key-metrics-ttm (42+ alan) tam alan listeleri** eklendi — daha önce sadece "vs" olarak geçiyordu.
- **dividends alanları** netleştirildi — frequency değerleri dahil.

### 10 Nisan 2026
- Plan limitleri düzeltildi (2500/dakika, günlük sınırsız).
- `analyst-estimates` alan isimleri eklendi (`epsAvg`, `numAnalystsEps`).

### Şubat 2026
- İlk sürüm — stable endpoint referansı.
