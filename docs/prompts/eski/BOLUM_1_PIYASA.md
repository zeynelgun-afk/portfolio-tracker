# BÖLÜM 1: PİYASA GÖRÜNÜMÜ

> **amaç**: günün makro resmini çiz, risk ortamını değerlendir, portföy kararlarını destekle
> **tahmini FMP call**: 12-16
> **tahmini websearch**: 3-5

---

## ADIM 1 — VERİ TOPLAMA

### 1a. FMP API çağrıları

```
# --- endeksler (1 call) ---
batch-quote → symbols=SPY,QQQ,DIA
# SPY = S&P 500 proxy, QQQ = NASDAQ proxy, DIA = Dow proxy

# --- emtia (2 call) ---
quote → symbol=GCUSD          # altın
quote → symbol=CLUSD          # WTI ham petrol

# --- forex (2 call) ---
quote → symbol=EURUSD
quote → symbol=USDTRY

# --- tahvil (1 call) ---
treasury-rates → from={bugün}, to={bugün}
# dönen veriden 'month10' = 10 yıllık yield (ondalık, örn: 4.25 = %4.25)
# eğer boş dönerse → websearch yedek: "us 10 year treasury yield today"

# --- sektör performansı (1 call) ---
sector-performance-snapshot → date={bugün}
# 11 sektör tek call'da gelir
# ⚠️ date parametresi ZORUNLU, yoksa 404 döner

# --- SPY teknik (3 call) ---
technical-indicators/sma → symbol=SPY, periodLength=50, timeframe=1day
technical-indicators/sma → symbol=SPY, periodLength=200, timeframe=1day
technical-indicators/rsi → symbol=SPY, periodLength=14, timeframe=1day
# sadece son 1 değeri kullan (limit=1 yok ama ilk eleman en güncel)

# --- piyasa hareketi (2 call) ---
biggest-gainers → limit=5
biggest-losers → limit=5
# ⚠️ doğru isim: "biggest-gainers", "biggest-losers" (market- prefix'i YOK)
```

**toplam: ~12 FMP call**

### 1b. WebSearch aramaları

```
# --- VIX + DXY (FMP'de doğrudan yok) ---
websearch → "VIX index close today {tarih}"
websearch → "US dollar index DXY today"

# --- günün haberleri ---
websearch → "stock market today {tarih} recap"
websearch → "market moving news today stocks"

# opsiyonel (önemli olay varsa):
websearch → "fed news today" veya "earnings news today"
```

**toplam: 3-5 websearch**

### 1c. veri bulunamazsa yedek plan

| veri | birincil kaynak | yedek |
|------|-----------------|-------|
| VIX | websearch | FMP quote UVXY (ters proxy, ama yeterli gösterge) |
| DXY | websearch | FMP quote EURUSD (ters çevir: DXY güçlü = EUR/USD düşük) |
| 10Y yield | treasury-rates | websearch "10 year yield today" |
| sektör perf | sector-performance-snapshot | websearch "sector performance today" |

---

## ADIM 2 — ANALİZ KURALLARI

### risk duyarlılığı nasıl belirlenir

```
3 ANA GÖSTERGEYE BAK:

1. VIX:  < 18 → Risk-On  |  18-25 → Nötr  |  > 25 → Risk-Off
2. SEKTÖR: günün en iyi 3 sektörü döngüsel mi savunmacı mı?
   - döngüsel lider (tech, finans, tüketim) → Risk-On
   - savunmacı lider (utilities, staples, healthcare) → Risk-Off
3. ALTIN + HISSE: ikisi birlikte yükseliyorsa → Nötr
   - altın ↑ hisse ↓ → Risk-Off  |  altın ↓ hisse ↑ → Risk-On

SONUÇ: 3 göstergeden 2'si aynı yöne işaret ediyorsa o yönü seç, yoksa Nötr
```

### S&P 500 trend nasıl belirlenir

```
SPY fiyat > SMA50 > SMA200      → "güçlü yükseliş trendi"
SPY fiyat > SMA50, < SMA200     → "toparlanma aşaması"
SPY fiyat < SMA50, > SMA200     → "kısa vadeli zayıflık, ana trend sağlam"
SPY fiyat < SMA50 < SMA200      → "düşüş trendi"

RSI > 70   → "aşırı alım bölgesi, dikkat"
RSI < 30   → "aşırı satım bölgesi, fırsat olabilir"
RSI 40-60  → "nötr"
```

### haber değerlendirme kuralları

websearch'ten gelen haberleri şu filtreyle değerlendir:
1. **portföy etkisi** — haber bizim pozisyonlarımızı doğrudan etkiliyor mu?
2. **sektör etkisi** — enerji, savunma, tech, telecom, sağlık sektörlerimiz etkileniyor mu?
3. **makro etki** — faiz, enflasyon, istihdam, jeopolitik gibi geniş çaplı mı?
4. **sadece en önemli 3-5 haber** — kalabalık yapma, her habere 1-2 cümle etki analizi yaz

---

## ADIM 3 — RAPOR ÇIKTI FORMATI

```markdown
## 1. piyasa görünümü

### makro tablo

| gösterge | değer | günlük değişim | sinyal |
|----------|-------|----------------|--------|
| S&P 500 (SPY) | $XXX.XX | ▲/▼ %X.XX | |
| NASDAQ (QQQ) | $XXX.XX | ▲/▼ %X.XX | |
| Dow Jones (DIA) | $XXX.XX | ▲/▼ %X.XX | |
| VIX | XX.XX | ▲/▼ X.XX | [düşük korku / orta / yüksek korku] |
| US 10Y yield | %X.XX | ▲/▼ X bp | |
| altın (XAU) | $X,XXX | ▲/▼ %X.XX | |
| WTI petrol | $XX.XX | ▲/▼ %X.XX | |
| EUR/USD | X.XXXX | ▲/▼ %X.XX | |
| USD/TRY | XX.XX | ▲/▼ %X.XX | |
| DXY | XXX.XX | ▲/▼ %X.XX | |

### sektör performansı

| sektör | değişim % | | sektör | değişim % |
|--------|-----------|---|--------|-----------|
| [en iyi 1] | +%X.XX 🟢 | | [en kötü 1] | -%X.XX 🔴 |
| [en iyi 2] | +%X.XX 🟢 | | [en kötü 2] | -%X.XX 🔴 |
| [en iyi 3] | +%X.XX | | [en kötü 3] | -%X.XX |

(11 sektörü en iyi → en kötü sırayla listele, en iyi 3 ve en kötü 3'ü vurgula)

### piyasa hareketi

**günün kazananları** (biggest-gainers'dan top 5):
| ticker | değişim % | hacim |
(tabloya hacim de ekle, anormal hacim genellikle haberi olan hissedir)

**günün kaybedenleri** (biggest-losers'dan top 5):
| ticker | değişim % | hacim |

### risk değerlendirmesi

- **risk duyarlılığı**: [RISK-ON 🟢 / RISK-OFF 🔴 / NÖTR ⚪]
  - gerekçe: [yukarıdaki skor tablosuna göre 2-3 cümle]
- **SPY teknik durum**: $XXX.XX | SMA50: $XXX | SMA200: $XXX | RSI: XX
  - trend: [güçlü yükseliş / kısa vadeli zayıflık / düşüş trendi / ...]
- **kritik seviyeler**: destek $XXX, direnç $XXX

### günün önemli haberleri

1. **[başlık]** — [1-2 cümle: ne oldu + portföyümüze etkisi]
2. **[başlık]** — [1-2 cümle]
3. **[başlık]** — [1-2 cümle]

### strateji notu

[2-3 cümle: bugünkü piyasa ortamına göre yarın ne dikkat etmeliyiz?
savunmacı mı kalmalıyız, fırsat mı kollamalıyız, hangi sektörler güçlü?]
```

---

## ADIM 4 — KALİTE KONTROL

raporu yazmadan önce şunları doğrula:
- [ ] tüm FMP verileri başarıyla geldi mi? (boş [] dönmediyse OK)
- [ ] VIX ve DXY websearch'ten alındıysa değer mantıklı mı?
- [ ] sektör performansı tarihi bugün mü?
- [ ] risk skoru hesaplaması tutarlı mı?
- [ ] SPY trend açıklaması SMA50/SMA200/RSI verileriyle uyuşuyor mu?
- [ ] haberler gerçekten bugüne ait mi? (eski haber ekleme)
- [ ] strateji notu portföyümüzle bağlantılı mı?
