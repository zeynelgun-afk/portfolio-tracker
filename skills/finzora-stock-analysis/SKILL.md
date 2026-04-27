---
name: finzora-stock-analysis
description: Finzora AI sistemi için ABD hisse senedi kapsamlı analiz skill'i. FMP API ile gerçek veri çeker. Görsel dashboard artifact üretir: 52 hafta çubuğu, finansal trend grafikleri, teknik sinyaller, bilanço takvimi, EPS sürpriz geçmişi, Boğa/Ayı tezleri, 3 senaryo analizi (Beat&Raise / In-Line / Miss), portföy uygunluk matrisi (Dengeli/Agresif/Temettü). Tetikleyiciler: "analiz et", "incele", "hisse raporu", "bilanço öncesi değerlendir", "al mı sat mı", "Finzora portföyüne uyar mı", tek ticker veya birden fazla ticker karşılaştırması. Her analizde mutlaka FMP API ile gerçek veri çek — hafızandan veri kullanma.
---

# Finzora Hisse Analiz Skill'i

## Genel Bakış

ABD hisse senetlerini Finzora AI sistemi için kapsamlı biçimde analiz eder. FMP API'dan gerçek veri çekip görsel, interaktif bir HTML artifact üretir. Her çalışmada sıfırdan veri çekimi zorunludur — hafızadaki eski veriler kullanılmaz.

## Analiz Akışı (Sırayla)

### Adım 1 — Konfigürasyon
```python
FMP_KEY  = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE = "https://financialmodelingprep.com/stable"
```
Her FMP çağrısında `sleep(2)` uygula — DNS rate limit önlemi.

### Adım 2 — Veri Çekimi (Bash ile)

Şu endpoint'leri sırayla çek:

```bash
# 1. Quote (fiyat, 52H yüksek/düşük, SMA'lar, hacim)
GET /stable/quote?symbol={TICKER}

# 2. Ratios TTM (P/E, P/B, P/S, P/FCF, D/E, marjlar, ROE, ROA)
GET /stable/ratios-ttm?symbol={TICKER}

# 3. Key Metrics TTM (FCF yield, earnings yield)
GET /stable/key-metrics-ttm?symbol={TICKER}

# 4. Income Statement - 3 yıllık (revenue, EPS, net income, EBITDA)
GET /stable/income-statement?symbol={TICKER}&period=annual&limit=3

# 5. Balance Sheet (cash, total debt, net debt, equity, total assets)
GET /stable/balance-sheet-statement?symbol={TICKER}&period=annual&limit=1

# 6. Cash Flow (FCF, operating CF, capex) - 3 yıllık
GET /stable/cash-flow-statement?symbol={TICKER}&period=annual&limit=3

# 7. Price Target Consensus
GET /stable/price-target-consensus?symbol={TICKER}

# 8. Earnings Calendar (bilanço tarihi, EPS est, gelir est)
GET /stable/earnings-calendar?from=BUGUN&to=60_GUN_SONRA

# 9. Analyst Estimates quarterly
GET /stable/analyst-estimates?symbol={TICKER}&period=quarter

# 10. Profile (sektör, sanayi, çalışan, CEO, açıklama)
GET /stable/profile?symbol={TICKER}
```

**DNS Overflow hatası:** 3 saniye bekle, tekrar dene. "DNS cache overflow" yanıtı boş döner — `"DNS" in raw` kontrolü yap.

### Adım 3 — Hesaplamalar

```python
# 52W konumu
pct_from_low  = (price - yearLow) / (yearHigh - yearLow) * 100
pct_from_high = (yearHigh - price) / yearHigh * 100

# SMA pozisyon
above_50sma  = price > priceAvg50
above_200sma = price > priceAvg200

# Net borç
net_debt = totalDebt - cash

# Net Leverage
net_leverage = net_debt / ebitda_ttm  # yaklaşık

# Sürpriz geçmişi
beat_pattern = [eps_actual vs eps_estimated, son 4 çeyrek]
```

### Adım 4 — Bilanço Analizi (Varsa)
Bilanço 0–60 gün içindeyse:
- EPS konsensüs vs şirket rehberi
- Gelir konsensüs vs şirket rehberi
- Son 4 çeyreğin beat/miss örüntüsü
- FX etkisi, tarife riski, mevsimsellik
- 3 senaryo (A/B/C) olasılıkları ve fiyat hedefleri

### Adım 5 — Portföy Uygunluk Matrisi

**Dengeli ($100K):** Multi-sector value+momentum. P/E<25, güçlü marjlar, 50SMA üzeri.
**Agresif ($400K):** Momentum+earnings surprise. Beat örüntüsü, RS yükseliş, yüksek büyüme.
**Temettü ($100K):** Yield >%3, P/E<20, FCF güçlü, D/E<1.5.

Her portföy için: ✅ Uygun / ⚠️ Dikkatli / ❌ Uygun Değil + 1 cümle gerekçe.

### Adım 6 — Belirsizlik Etiketleme
- **KESİN:** Doğrudan FMP verisinden gelen rakamlar
- **MUHTEMEL:** Hesaplanan/çıkarılan sonuçlar
- **SPEKÜLATİF:** Senaryo ve tez yorumları

## Artifact Yapısı

Dark theme HTML artifact üret (Finzora AI marka kimliği):

```
Renkler:
  --bg: #0d1117
  --surface: #161b22
  --border: #21262d
  --teal: #2dd4bf      (ana renk, pozitif)
  --gold: #f59e0b      (dikkat, nötr)
  --red: #f87171       (negatif, risk)
  --green: #4ade80     (pozitif)
  --blue: #60a5fa      (bilgi)
  --muted: #7d8590
Fontlar: 'Syne' (başlıklar/rakamlar), 'DM Mono' (metrikler/etiketler)
```

### Zorunlu Bölümler (bu sırayla):

1. **Header** — Ticker (büyük teal), şirket adı, anlık fiyat, değişim %, piyasa değeri, hacim, tarih
2. **52 Hafta Çubuğu** — Düşük/Yüksek arası progress bar, anlık fiyat noktası, 50SMA/200SMA notları
3. **8 Temel Metrik Kartı** — P/E, EV/EBITDA, P/FCF, P/B, Brüt Marj, EBITDA Marj, Net Marj, ROE (renk: yeşil/sarı/kırmızı)
4. **4 Sparkline Grafik** (Chart.js) — Gelir, EPS, FCF, Net Borç trendi (3 yıl)
5. **Bilanço & Değerleme Tablosu** — İki kolon: Bilanço + Değerleme
6. **Teknik Sinyal Tablosu** — 50SMA, 200SMA, 52H konum, RSI, trend, destek/direnç
7. **Bilanço Kutusu** (eğer yakın bilançosu varsa) — Tarih, EPS konsensüs, gelir konsensüs, YoY büyüme, beat geçmişi
8. **3 Senaryo Kartı** — A (Bullish), B (In-Line), C (Bearish) — her birinde EPS aralığı, fiyat hedefi, olasılık, açıklama
9. **Boğa & Ayı Tezleri** — 2 kolon, her birinde 5-6 madde
10. **Finzora Tavsiye Kutusu** — AL/SAT/BEKLE + hedef fiyat + stop seviyesi + R:R oranı
11. **Portföy Uygunluk Matrisi** — 3 kart (Dengeli/Agresif/Temettü)
12. **Footer** — Finzora AI branding, tarih, uyarı

## Renk Kodlaması (Metrik Kartlar)

```
Yeşil  → İyi:    P/E<18, EV/EBITDA<12, P/FCF<20, Marj>%15, ROE>%15
Sarı   → Dikkat: P/E 18-25, D/E 1-1.5x, marj %8-15
Kırmızı→ Kötü:  P/E>30, Negatif marj, D/E>1.5x, faiz karşılama <3x
```

## Teknik Sinyal Kuralı

```
Bullish badge: 50SMA üzeri, 200SMA üzeri, RSI 40-65, hacim artış
Bearish badge: SMA altı, RSI>75 ya da <30, hacim düşüş
Nötr badge:   Karma sinyal
```

## Senaryo Olasılıkları

Bilanço analizi için:
- Beat örüntüsü 3+/4: Senaryo A olasılığı ≥%35
- Rehber konsensüs üzerinde: Senaryo A %+5
- VIX >25: Olasılıkları aşağı revize et

## Çıktı Formatı

**Artifact + kısa metin özeti:**

Artifact: Tam görsel dashboard (yukarda tanımlanan)
Metin (artifact altında, maksimum 5 cümle):
- KESİN veri özeti
- MUHTEMEL çıkarım
- 30 Nisan sonrası için somut eylem

**GitHub'a kaydet:**
Analiz tamamlanınca:
```python
# reports/research/TICKER_YYYY-MM-DD.md oluştur
# data/research/index.json güncelle
# git commit + push
```

## FMP Hata Yönetimi

```python
def fmp(endpoint, params, retries=2):
    for i in range(retries):
        time.sleep(2 + i)
        r = requests.get(f"{BASE}/{endpoint}", params={**params,"apikey":KEY}, timeout=15)
        if r.status_code == 200 and r.text.strip() and "DNS" not in r.text:
            return r.json()
    return []  # Sessizce başarısız ol, devam et
```

## Karşılaştırma Modu

İki+ ticker verilirse:
1. Her biri için Adım 2 veri çekimi yap
2. Yan yana metrik tablosu üret (tek artifact içinde)
3. Her metrikte kim daha iyi? → Renk vurgusu
4. Sonuçta "X mi Y mi daha cazip?" önerisi

## Örnek Tetikleyici İfadeler

- "BDC'yi analiz et"
- "NVDA bilanço öncesi değerlendir"
- "CLF al mı satmalı mı?"
- "Agresif portföyüme ETN uyar mı?"
- "GEV vs ETN karşılaştır"
- "Bu hisseyi Finzora sistemine göre incele"

## Önemli Notlar

- FMP `changePercentage` live seansta 0 dönebilir → `((price-previousClose)/previousClose)*100` ile hesapla
- `historical-price-eod/full` liste döner (dict değil) → `isinstance(data, list)` kontrol et
- Analyst estimates `epsAvg` kullan (`estimatedEpsAvg` değil)
- Her analizde GitHub'a kayıt otomatik yapılır → kullanıcıdan onay isteme
