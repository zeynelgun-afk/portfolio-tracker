# FMP API Öğrenilen Dersler

> **Tarih:** 20 Şubat 2026  
> **Test Edilen:** Premium Plan, /stable/ endpoints  
> **API Key:** Çalışıyor ✅

---

## 🎯 ANA DERSLER

### 1. Screener Kullanma - YERİNE Direkt Endpoint Kullan

**❌ ÇALIŞMAYAN YÖNTEM:**
```python
# Screener çok agresif filtrelerle boş döner
screener = fmp_get("company-screener", {
    "marketCapMoreThan": 2000000000,
    "sector": "Energy",
    "volumeMoreThan": 1000000
})
# Sonuç: [] (boş)
```

**✅ DOĞRU YÖNTEM:**
```python
# Her hisse için quote + profile + price-change
for symbol in ["ABBV", "LLY", "TSM", "OXY"]:
    quote = fmp_get("quote", {"symbol": symbol})
    profile = fmp_get("profile", {"symbol": symbol})
    price_change = fmp_get("stock-price-change", {"symbol": symbol})
    
    # Filtrelemeyi Python'da yap
    if (quote[0]['marketCap'] > 2e9 and 
        profile[0]['sector'] == 'Energy' and
        price_change[0]['1M'] > 5.0):
        # Bu hisse kriterleri karşılıyor!
```

---

### 2. Volume Verisi - Quote Endpoint'inden Al

**❌ YANLIŞ:**
```python
gainers = fmp_get("biggest-gainers", {"limit": 20})
volume = gainers[0]['volume']  # KeyError! Field yok
```

**✅ DOĞRU:**
```python
gainers = fmp_get("biggest-gainers", {"limit": 20})
for stock in gainers:
    quote = fmp_get("quote", {"symbol": stock['symbol']})
    volume = quote[0]['volume']  # ✅ Çalışır
```

---

### 3. Market Cap - Quote Endpoint'i Güvenilir

**❌ GÜVENSİZ:**
```python
ratios = fmp_get("ratios-ttm", {"symbol": "DVA"})
market_cap = ratios[0].get('marketCapTTM', 0)  # Sıfır olabilir!
```

**✅ GÜVENİLİR:**
```python
quote = fmp_get("quote", {"symbol": "DVA"})
market_cap = quote[0]['marketCap']  # Her zaman dolu
```

---

### 4. P/E Oranı - Premium Plan'da Quote Kullan

**⚠️ DİKKAT:**
```python
ratios = fmp_get("ratios-ttm", {"symbol": "AAPL"})
pe = ratios[0].get('peRatioTTM', 0)  # Premium'da eksik olabilir
```

**✅ DAHA İYİ:**
```python
quote = fmp_get("quote", {"symbol": "AAPL"})
pe = quote[0]['pe']  # Daha güvenilir
```

---

## 📊 ÖNERİLEN WORKFLOW

### Hisse Araştırması İçin 3 Adım:

```python
def get_stock_data(symbol):
    """Her hisse için standart veri toplama"""
    
    # 1. Quote: Fiyat, volume, market cap
    quote = fmp_get("quote", {"symbol": symbol})
    
    # 2. Profile: Sektör, industry
    profile = fmp_get("profile", {"symbol": symbol})
    
    # 3. Price Change: Momentum metrikleri
    price_change = fmp_get("stock-price-change", {"symbol": symbol})
    
    if not all([quote, profile, price_change]):
        return None
    
    return {
        'symbol': symbol,
        'price': quote[0]['price'],
        'volume': quote[0]['volume'],
        'market_cap': quote[0]['marketCap'],
        'sector': profile[0]['sector'],
        'change_1m': price_change[0].get('1M', 0),
        'change_ytd': price_change[0].get('ytd', 0)
    }
```

---

## 💡 PERFORMANS İPUÇLARI

### Batch Call Kullan (Mümkünse):

**✅ İYİ:**
```python
quotes = fmp_get("batch-quote", {"symbols": "AAPL,MSFT,GOOGL"})
# 1 API call = 3 hisse
```

**❌ KÖTÜ:**
```python
for symbol in ["AAPL", "MSFT", "GOOGL"]:
    quote = fmp_get("quote", {"symbol": symbol})
# 3 API call = 3 hisse
```

### Ama Profile/Price-Change İçin Individual Gerekli:

```python
# Quote batch (1 call)
quotes = fmp_get("batch-quote", {"symbols": "AAPL,MSFT,GOOGL"})

# Profile/Price-change individual (6 call)
for symbol in ["AAPL", "MSFT", "GOOGL"]:
    profile = fmp_get("profile", {"symbol": symbol})
    price_change = fmp_get("stock-price-change", {"symbol": symbol})

# Toplam: 7 call (batch + individual)
# vs. 9 call (her şey individual)
```

---

## 🚨 YAPILMAMASI GEREKENLER

1. **Screener filtrelerinin SQL gibi çalıştığını varsayma**
2. **Boş response kontrolü yapmamak**
3. **Volume için yanlış endpoint kullanmak**
4. **ratios-ttm'ye körü körüne güvenmek**
5. **API limit takibi yapmamak**

---

## ✅ GERÇEK ÖRNEK: Stock Screening

**Görev:** Yüksek momentumlu healthcare hisseleri bul

**YANLIŞ:**
```python
screener = fmp_get("company-screener", {
    "sector": "Healthcare",
    "change_1m": ">10%"  # ❌ Bu parametre yok!
})
# Sonuç: []
```

**DOĞRU:**
```python
# Adım 1: Aday listesi
healthcare = ["ABBV", "LLY", "BMY", "UNH", "MRK"]

# Adım 2: Veri topla
results = []
for symbol in healthcare:
    quote = fmp_get("quote", {"symbol": symbol})
    pc = fmp_get("stock-price-change", {"symbol": symbol})
    
    if quote and pc:
        results.append({
            'symbol': symbol,
            'change_1m': pc[0].get('1M', 0),
            'market_cap': quote[0]['marketCap']
        })

# Adım 3: Python'da filtrele
high_momentum = [
    r for r in results 
    if r['change_1m'] > 10 and r['market_cap'] > 50e9
]

# Sonuç: BMY +11.32%, gerçek momentum var! ✅
```

---

## 🎯 ALTIN KURALLAR

1. **`quote` kullan:** price, volume, market cap, P/E
2. **`profile` kullan:** sector, industry, company
3. **`price-change` kullan:** 1D, 5D, 1M, YTD momentum
4. **Screener'a güvenme:** Karmaşık filtreler için Python kullan
5. **Her zaman kontrol et:** Boş/null response'ları
6. **Batch kullan:** Mümkün olduğunda
7. **API limiti takip et:** 2,500 call/gün

---

## 📝 TEST EDİLENLER (20 Şubat 2026)

| Test | Sonuç | Not |
|------|-------|-----|
| `quote` AAPL | ✅ | Price, volume, market cap - hepsi dolu |
| `profile` AAPL | ✅ | Sector, industry - doğru |
| `price-change` AAPL | ✅ | 1M, YTD - doğru |
| `batch-quote` 3 hisse | ✅ | Tek call, 3 sonuç |
| `biggest-gainers` | ✅ | Ama volume yok! |
| `stock-list` | ✅ | 48,497 hisse |
| Screener momentum | ❌ | Boş döner |
| `ratios-ttm` DVA | ⚠️ | PE=0 döndü (quote kullan) |

---

## 🔬 GERÇEK VERİ ÖRNEKLERİ

**OXY (Occidental Petroleum):**
- Quote: $50.67, Volume: 7.9M, MCap: $49.9B ✅
- Profile: Energy / Oil & Gas E&P ✅
- Price-change: 1M +19.97%, YTD +19.57% ✅

**BMY (Bristol Myers):**
- Quote: $60.35, Volume: 3.2M, MCap: $122.9B ✅
- Profile: Healthcare / Drug Manufacturers ✅
- Price-change: 1M +11.32%, YTD +12.90% ✅

**TSM (Taiwan Semi):**
- Quote: $370.41, Volume: 3.7M, MCap: $1,921B ✅
- Profile: Tech / Semiconductors ✅
- Price-change: 1M +13.22%, YTD +15.89% ✅

---

## 💾 KAYNAK

Bu dersler şu testlerden öğrenildi:
- 20 Şubat 2026, 19:45 TR
- Premium Plan API testi
- 7 hisse detaylı analiz (ABBV, LLY, TSM, OXY, BMY, CRWD, EXPE)
- 6 endpoint başarı testi
- Screener sorun tespiti

---

**Son Güncelleme:** 20 Şubat 2026  
**Doğrulanan Plan:** FMP Premium  
**Status:** ✅ API Mükemmel Çalışıyor
