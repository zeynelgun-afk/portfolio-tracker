# 📰 FMP PREMIUM NEWS API - TAM REHBERİ

**Son Test:** 20 Şubat 2026  
**API Key:** Premium abonelik ✅  
**Base URL:** `https://financialmodelingprep.com/stable`

---

## ✅ **ÇALIŞAN ENDPOINT'LER**

### **1. STOCK NEWS (Hisse Haberleri)**

```
GET /stable/news/stock
```

**Parametreler:**
- `symbols` (zorunlu): Virgülle ayrılmış hisse sembolleri
- `limit` (opsiyonel): Varsayılan 5, max 100+
- `from` (opsiyonel): YYYY-MM-DD formatında başlangıç
- `to` (opsiyonel): YYYY-MM-DD formatında bitiş

**Örnek:**
```python
# Tek hisse
url = f"https://financialmodelingprep.com/stable/news/stock?symbols=AAPL&limit=10&apikey={api_key}"

# Çoklu hisse
url = f"https://financialmodelingprep.com/stable/news/stock?symbols=AAPL,MSFT,TSLA&limit=20&apikey={api_key}"

# Tarih aralığı
url = f"https://financialmodelingprep.com/stable/news/stock?symbols=NVDA&from=2026-02-19&to=2026-02-20&limit=50&apikey={api_key}"
```

**Response Format:**
```json
[
  {
    "symbol": "AAPL",
    "publishedDate": "2026-02-20 03:02:00",
    "publisher": "The Motley Fool",
    "title": "Apple Just Took a Page...",
    "image": "https://images.financialmodelingprep.com/...",
    "site": "fool.com",
    "text": "Full article text...",
    "url": "https://www.fool.com/..."
  }
]
```

---

### **2. GENERAL NEWS LATEST (Genel Piyasa Haberleri)**

```
GET /stable/news/general-latest
```

**Parametreler:**
- `page` (opsiyonel): Sayfa numarası (0'dan başlar)
- `limit` (opsiyonel): Sayfa başına kayıt

**Örnek:**
```python
# İlk sayfa
url = f"https://financialmodelingprep.com/stable/news/general-latest?page=0&limit=10&apikey={api_key}"

# İkinci sayfa
url = f"https://financialmodelingprep.com/stable/news/general-latest?page=1&limit=10&apikey={api_key}"
```

**Response Format:**
```json
[
  {
    "symbol": null,
    "publishedDate": "2026-02-20 03:00:26",
    "publisher": "Fox Business",
    "title": "Help is on the way at the Fed...",
    "image": "https://images.financialmodelingprep.com/...",
    "site": "youtube.com",
    "text": "Former deputy Treasury secretary...",
    "url": "https://www.youtube.com/..."
  }
]
```

**Not:** `symbol` field'ı null - genel piyasa haberleri

---

### **3. FOREX NEWS (Forex Haberleri)**

```
GET /stable/news/forex
```

**Parametreler:**
- `limit` (opsiyonel): Dönen haber sayısı

**Örnek:**
```python
url = f"https://financialmodelingprep.com/stable/news/forex?limit=10&apikey={api_key}"
```

**Response Format:**
```json
[
  {
    "symbol": "EURUSD",
    "publishedDate": "2026-02-20 03:08:29",
    "publisher": "FX Street",
    "title": "EUR/USD: Downside risk to 1.160...",
    "image": "https://...",
    "site": "fxstreet.com",
    "text": "EUR/USD: Downside risk...",
    "url": "https://www.fxstreet.com/..."
  }
]
```

---

### **4. CRYPTO NEWS (Kripto Haberleri)**

```
GET /stable/news/crypto
```

**Parametreler:**
- `limit` (opsiyonel): Dönen haber sayısı

**Örnek:**
```python
url = f"https://financialmodelingprep.com/stable/news/crypto?limit=10&apikey={api_key}"
```

**Response Format:**
```json
[
  {
    "symbol": "BTCUSD",
    "publishedDate": "2026-02-20 03:28:09",
    "publisher": "Coincu",
    "title": "Bitcoin steadies as Warren...",
    "image": "https://...",
    "site": "coincu.com",
    "text": "Sen. Elizabeth Warren urged...",
    "url": "https://coincu.com/..."
  }
]
```

---

## ❌ **ÇALIŞMAYAN ENDPOINT'LER**

### **1. Press Releases**
```
❌ GET /stable/press-releases?symbol=AAPL
❌ GET /stable/press-releases/search?name=Apple
Status: 404 - Endpoint bulunamadı
```

### **2. Social Sentiment**
```
❌ GET /stable/social-sentiment?symbol=AAPL
Status: 404 - Endpoint bulunamadı
```

### **3. Legacy Endpoints**
```
❌ GET /api/v3/stock_news
❌ GET /api/v4/general_news
❌ GET /api/v4/articles
Status: 403 - Legacy endpoints (31 Ağustos 2025 kapatıldı)
```

---

## 🎯 **GÜNLÜK RAPOR İÇİN KULLANIM**

### **Sabah 14:00 TR (06:00 EST) Raporu:**

```python
import requests
from datetime import datetime, timedelta

api_key = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
base_url = "https://financialmodelingprep.com/stable"

# Tarih aralığı (son 24 saat)
today = datetime.now()
yesterday = today - timedelta(days=1)
from_date = yesterday.strftime("%Y-%m-%d")
to_date = today.strftime("%Y-%m-%d")

# ========================================
# 1. PORTFÖY HABERLERİ
# ========================================
portfolio_symbols = "SM,KOS,MO,RGLD,FCX,XLE"
url = f"{base_url}/news/stock?symbols={portfolio_symbols}&from={from_date}&to={to_date}&limit=50&apikey={api_key}"
portfolio_news = requests.get(url, timeout=15).json()

# ========================================
# 2. TECH GIANTS HABERLERİ
# ========================================
tech_symbols = "AAPL,MSFT,GOOGL,AMZN,META,TSLA,NVDA"
url = f"{base_url}/news/stock?symbols={tech_symbols}&from={from_date}&to={to_date}&limit=50&apikey={api_key}"
tech_news = requests.get(url, timeout=15).json()

# ========================================
# 3. WATCHLIST HABERLERİ
# ========================================
watchlist_symbols = "AMD,NET,PANW"
url = f"{base_url}/news/stock?symbols={watchlist_symbols}&from={from_date}&to={to_date}&limit=30&apikey={api_key}"
watchlist_news = requests.get(url, timeout=15).json()

# ========================================
# 4. GENEL PİYASA HABERLERİ
# ========================================
url = f"{base_url}/news/general-latest?page=0&limit=20&apikey={api_key}"
general_news = requests.get(url, timeout=15).json()

# ========================================
# 5. FOREX HABERLERİ
# ========================================
url = f"{base_url}/news/forex?limit=10&apikey={api_key}"
forex_news = requests.get(url, timeout=15).json()

# ========================================
# 6. CRYPTO HABERLERİ
# ========================================
url = f"{base_url}/news/crypto?limit=10&apikey={api_key}"
crypto_news = requests.get(url, timeout=15).json()

# ========================================
# ANALİZ
# ========================================

# Portföy haberleri sembol bazında grupla
by_symbol = {}
for news in portfolio_news:
    symbol = news.get('symbol', 'N/A')
    if symbol not in by_symbol:
        by_symbol[symbol] = []
    by_symbol[symbol].append(news)

# Rapor çıktısı
print("=" * 80)
print("GÜNLÜK HABER RAPORU - 14:00 TR")
print("=" * 80)

print("\n1. PORTFÖY HABERLERİ:")
for symbol in ['SM', 'KOS', 'MO', 'RGLD', 'FCX', 'XLE']:
    if symbol in by_symbol and len(by_symbol[symbol]) > 0:
        print(f"\n  {symbol} ({len(by_symbol[symbol])} haber):")
        for news in by_symbol[symbol][:2]:  # İlk 2 haber
            print(f"    • {news['title'][:70]}")
            print(f"      {news['publishedDate']} - {news['site']}")

print("\n2. GENEL PİYASA (Top 5):")
for i, news in enumerate(general_news[:5], 1):
    print(f"  {i}. {news['title'][:75]}")
    print(f"     {news['publishedDate']} - {news['site']}")

print("\n3. TECH GIANTS (Top 3):")
for i, news in enumerate(tech_news[:3], 1):
    print(f"  {i}. [{news['symbol']}] {news['title'][:65]}")
    print(f"     {news['publishedDate']}")
```

---

## 📊 **VERİ KAYNAĞI STRATEJİSİ**

### **FMP API Kullan (✅ Çalışıyor):**
- Stock-specific haberler (AAPL, TSLA, SM, KOS, vb.)
- Genel piyasa haberleri (general-latest)
- Forex haberleri (EUR/USD, USD/TRY, vb.)
- Crypto haberleri (BTC, ETH, vb.)

### **Web Search Kullan (Ek olarak):**
- Jeopolitik gelişmeler (İran-ABD, Rusya, vb.)
- Fed/ECB/BOJ spesifik açıklamaları
- Makroekonomik veri yorumları
- Asya borsaları kapanış yorumları
- Sektör analizi raporları

---

## ⚙️ **TEKNİK DETAYLAR**

### **Rate Limits:**
```
Premium Plan: 50GB/30 gün bandwidth
Günlük kullanım tahmini:
  - 100 stock news × 50KB = 5MB
  - 20 general news × 50KB = 1MB
  - 10 forex/crypto × 50KB = 1MB
  - Toplam/gün: ~7MB
  - Aylık: ~210MB (Premium limiti içinde ✅)
```

### **Response Alanları (Tüm endpoint'lerde ortak):**
```json
{
  "symbol": "AAPL" (veya null genel haberler için),
  "publishedDate": "2026-02-20 03:02:00",
  "publisher": "The Motley Fool",
  "title": "Başlık...",
  "image": "https://images.financialmodelingprep.com/...",
  "site": "fool.com",
  "text": "Tam metin...",
  "url": "https://www.fool.com/..."
}
```

### **Tarih Formatı:**
- API sadece tarih alıyor: `YYYY-MM-DD`
- Saat parametresi yok
- Son 24 saat için: `from=dün&to=bugün`

### **Sembol Limiti:**
- Tek request'te çoklu sembol: ✅
- Virgülle ayrılmış: `AAPL,MSFT,GOOGL`
- Pratik limit: ~20-30 sembol/request

---

## 🚀 **OTOMASYON AKIŞI**

```
14:00 TR (06:00 EST) - Rapor Başla
│
├─ 1. FMP API: Portföy haberleri (stock)
│  └─ SM, KOS, MO, RGLD, FCX, XLE
│
├─ 2. FMP API: Tech giants (stock)
│  └─ AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA
│
├─ 3. FMP API: Watchlist (stock)
│  └─ AMD, NET, PANW
│
├─ 4. FMP API: Genel piyasa (general-latest)
│  └─ Top 20 genel haber
│
├─ 5. FMP API: Forex haberleri
│  └─ EUR/USD, GBP/USD, USD/JPY, vb.
│
├─ 6. FMP API: Crypto haberleri
│  └─ BTC, ETH, vb.
│
├─ 7. Web Search: Ek araştırma
│  ├─ "Asian markets close today"
│  ├─ "Iran oil tensions"
│  ├─ "Fed Powell speech" (varsa)
│  └─ "GDP PCE data release" (varsa)
│
└─ 8. Rapor Oluştur & GitHub Push
   ├─ Haberleri kategorize et
   ├─ Portföy etkisi değerlendir
   ├─ Bugün yapılacaklar
   └─ Git commit + push
```

---

## 📌 **BEST PRACTICES**

1. **Pagination Stratejisi:**
   - `general-latest` sayfa bazlı (page=0, 1, 2...)
   - Diğerleri limit bazlı
   - İlk sayfada genelde yeterli haber

2. **Error Handling:**
   ```python
   try:
       response = requests.get(url, timeout=15)
       if response.status_code == 200:
           data = response.json()
           if isinstance(data, list) and len(data) > 0:
               # İşle
           else:
               print("Haber bulunamadı")
       else:
           print(f"API Hatası: {response.status_code}")
   except Exception as e:
       print(f"Bağlantı hatası: {e}")
   ```

3. **Sembol Gruplandırma:**
   - Portföy, watchlist, tech ayrı ayrı çek
   - Sembol başına kategori daha kolay analiz

4. **Tarih Aralığı:**
   - Son 24 saat: dün + bugün
   - Haftalık özet: 7 gün geriye
   - Aylık özet: 30 gün geriye

---

## ✅ **ÖZET**

### **Çalışan Endpoint'ler (Premium):**
1. ✅ `/stable/news/stock` - Hisse haberleri
2. ✅ `/stable/news/general-latest` - Genel piyasa
3. ✅ `/stable/news/forex` - Forex haberleri
4. ✅ `/stable/news/crypto` - Crypto haberleri

### **Çalışmayan Endpoint'ler:**
- ❌ Press releases
- ❌ Social sentiment
- ❌ Legacy v3/v4 endpoints

### **Kombinasyon Stratejisi:**
- FMP API: Şirket + genel + forex + crypto
- Web Search: Jeopolitik + Fed + makro
- = **Tam kapsam** ✅

---

**Son Güncelleme:** 20 Şubat 2026  
**Test Durumu:** ✅ Tüm endpoint'ler test edildi  
**API Key:** Premium abonelik aktif
