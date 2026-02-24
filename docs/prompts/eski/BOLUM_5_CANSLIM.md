# BÖLÜM 5: CANSLIM HİSSE TARAMASI

> **amaç**: William O'Neil'in CANSLIM metodolojisi ile büyüme hissesi taraması
> **çalışma sıklığı**: HAFTADA 1 KEZ (pazar raporu — WEEKLY_REPORT'a dahil)
> **günlük raporda**: sadece referans satırı → "CANSLIM taraması pazar raporunda güncellenir"
> **tahmini FMP call**: ~80-100 (haftada 1 kez)
> **tahmini websearch**: 1-2

---

## CANSLIM KRİTERLERİ ÖZETİ

| harf | kriter | açıklama | ağırlık |
|------|--------|----------|---------|
| **C** | Current Quarterly Earnings | son çeyrek EPS büyümesi | %20 |
| **A** | Annual Earnings Growth | yıllık EPS büyüme trendi | %20 |
| **N** | New (yenilik/zirve yakınlığı) | yeni ürün/yönetim/zirve | %15 |
| **S** | Supply & Demand | düşük float + yüksek hacim | %10 |
| **L** | Leader or Laggard | sektöründe lider mi? | %15 |
| **I** | Institutional Sponsorship | kurumsal sahiplik artıyor mu? | %10 |
| **M** | Market Direction | genel piyasa yönü | %10 |

---

## ADIM 1 — PİYASA YÖNÜ KONTROLÜ (M kriteri)

bölüm 1'den SPY teknik durumunu al:

```
SPY > SMA50 > SMA200  → M = 10/10 "onaylı yükseliş"
SPY > SMA200, < SMA50  → M = 6/10  "karışık, dikkatli ol"
SPY < SMA200           → M = 3/10  "düşüş trendi — CANSLIM girişleri riskli"
                         ⚠️ uyarı ekle: "piyasa yönü olumsuz, yeni alım için bekle"
```

---

## ADIM 2 — ADAY HAVUZU OLUŞTUR (2 aşamalı filtre)

### aşama 1: kaba filtre (1-2 FMP call)

```python
# company-screener ile temel filtre
# ⚠️ doğru endpoint: "company-screener" ("stock-screener" DEĞİL)
adaylar = fmp_get("company-screener", {
    "marketCapMoreThan": 2000000000,      # $2B+ piyasa değeri
    "marketCapLowerThan": 200000000000,   # $200B altı (mega-cap hariç, onlar zaten yavaş büyür)
    "priceMoreThan": 10,                  # penny stock hariç
    "volumeMoreThan": 500000,             # günlük 500K+ hacim (likidite)
    "isActivelyTrading": "true",
    "exchange": "NYSE,NASDAQ",
    "limit": 100                          # ilk 100 aday
})
```

### aşama 2: 52-hafta zirvesine yakınlık filtresi (0 ekstra call)

```python
# screener sonuçlarında yearHigh alanı varsa kullan
# yoksa batch-quote ile çek (1 call)
# sadece 52W zirvesinden ≤%15 uzakta olanları tut

filtreli = []
for aday in adaylar:
    if aday.get('price') and aday.get('yearHigh'):
        zirve_uzaklik = ((aday['yearHigh'] - aday['price']) / aday['yearHigh']) * 100
        if zirve_uzaklik <= 15:
            filtreli.append(aday)

# bu filtre genellikle 100 → 30-40 adaya düşürür
# sonra ilk 20'yi al (en yüksek piyasa değerine göre sırala)
en_iyi_20 = sorted(filtreli, key=lambda x: x.get('marketCap', 0), reverse=True)[:20]
```

---

## ADIM 3 — DETAYLI SKORLAMA (20 aday için)

her aday için aşağıdaki FMP call'ları yap:

```python
for aday in en_iyi_20:
    symbol = aday['symbol']
    
    # C + A kriterleri için (1 call)
    income_q = fmp_get("income-statement", {
        "symbol": symbol, "period": "quarter", "limit": 8
    })
    
    # A kriteri için yıllık (1 call)
    income_a = fmp_get("income-statement", {
        "symbol": symbol, "period": "annual", "limit": 5
    })
    
    # S kriteri için float (1 call)
    float_data = fmp_get("shares-float", {"symbol": symbol})
    
    # I kriteri için kurumsal sahiplik (1 call)
    institutional = fmp_get("institutional-holders", {
        "symbol": symbol, "limit": 10
    })

# 20 aday × 4 call = 80 call
# + screener 1-2 call + batch-quote 1 call
# TOPLAM: ~83 call
```

---

## ADIM 4 — HER KRİTER NASIL SKORLANIR

### C — Current Quarterly Earnings (max 20 puan)

```python
# income-statement quarter verilerinden:
son_ceyrek_eps = income_q[0]['eps']
onceki_yil_ayni_ceyrek_eps = income_q[4]['eps']  # 4 çeyrek öncesi = geçen yıl aynı çeyrek

eps_buyume = ((son_ceyrek_eps - onceki_yil_ayni_ceyrek_eps) / abs(onceki_yil_ayni_ceyrek_eps)) * 100

# SKORLAMA:
# eps_buyume > %50    → 20/20
# eps_buyume %25-%50  → 16/20
# eps_buyume %10-%25  → 12/20
# eps_buyume %0-%10   → 8/20
# eps_buyume < %0     → 0/20

# BONUS: son 2 çeyrek üst üste hızlanma (accelerating) → +2 puan (max 20)
# hızlanma = bu çeyrek büyüme > geçen çeyrek büyüme
```

### A — Annual Earnings Growth (max 20 puan)

```python
# income-statement annual verilerinden:
# 3 yıllık EPS büyüme trendi

yillik_eps = [income_a[i]['eps'] for i in range(min(5, len(income_a)))]
# yillik_eps[0] = en güncel yıl, yillik_eps[4] = 5 yıl önce

# 3 yıllık ortalama büyüme hesapla
if len(yillik_eps) >= 4 and yillik_eps[3] > 0:
    buyume_3y = ((yillik_eps[0] / yillik_eps[3]) ** (1/3) - 1) * 100  # CAGR
else:
    buyume_3y = 0

# ROE kontrolü (key-metrics-ttm'den veya hesaplayarak)
# basit yöntem: income-statement'tan net income / balance sheet equity
# ama ekstra call gerekir, alternatif: ratios-ttm (1 call daha eklenebilir)

# SKORLAMA:
# CAGR > %25 + her yıl artış  → 20/20
# CAGR > %25                   → 16/20
# CAGR %15-%25                 → 12/20
# CAGR %5-%15                  → 8/20
# CAGR < %5 veya düzensiz      → 4/20
# negatif büyüme               → 0/20
```

### N — New (yenilik + 52W zirve yakınlığı) (max 15 puan)

```python
# batch-quote veya screener verisinden:
fiyat = aday['price']
zirve_52w = aday['yearHigh']
zirve_uzaklik_pct = ((zirve_52w - fiyat) / zirve_52w) * 100

# SKORLAMA:
# zirve_uzaklik < %5 (zirveye çok yakın)   → 15/15
# zirve_uzaklik %5-%10                      → 12/15
# zirve_uzaklik %10-%15                     → 8/15
# zirve_uzaklik > %15                       → aday zaten filtrede elenmiş olmalı

# NOT: "yeni ürün/yönetim" bilgisi FMP'den alınamaz
# websearch ile teyit edilebilir ama her hisse için yapma, sadece final top 5 için
```

### S — Supply & Demand (max 10 puan)

```python
# shares-float verisinden:
float_shares = float_data[0].get('floatShares', 0)
outstanding = float_data[0].get('outstandingShares', 0)

# düşük float = arz kısıtlı = fiyat hareketi daha sert
# batch-quote'tan: ortalama hacim vs son gün hacim karşılaştırması

hacim_orani = aday.get('volume', 0) / aday.get('avgVolume', 1)  # avgVolume varsa

# SKORLAMA:
# float < 100M + hacim_orani > 1.5  → 10/10 (az arz + yüksek talep)
# float < 100M                       → 8/10
# float 100M-500M + hacim_orani > 1.3 → 7/10
# float 100M-500M                    → 5/10
# float > 500M                       → 3/10
# float > 1B                         → 1/10 (çok fazla arz)
```

### L — Leader or Laggard (max 15 puan)

```python
# hisse sektöründe lider mi laggard mı?
# stock-price-change ile 3 aylık performans karşılaştır

hisse_3ay = fmp_get("stock-price-change", {"symbol": symbol})
# dönen veri: 1M, 3M, 6M, 1Y gibi % değişimler

# sektör ETF'i ile karşılaştır:
# Technology → XLK, Energy → XLE, Healthcare → XLV, vb.
sektor_etf_3ay = ... # aynı endpoint ile sektör ETF'in 3 aylık değişimi

# relative strength = hisse 3M% - sektör ETF 3M%
rs = hisse_3ay['3M'] - sektor_etf_3ay['3M']

# SKORLAMA:
# rs > +15% (sektörden çok iyi)    → 15/15
# rs > +5%                          → 12/15
# rs %0 ile +5% arası               → 8/15
# rs < %0 (sektörden kötü)          → 4/15
# rs < -%10 (ciddi laggard)         → 0/15

# ⚠️ her hisse için stock-price-change zaten bölüm 2'de çekilmiş olabilir
# sektör ETF'leri için de çekmek lazım (max 11 sektör ETF → 11 call ekstra)
# OPTİMİZASYON: sektör ETF performanslarını bölüm 1'deki sector-performance-snapshot'tan türet
```

### I — Institutional Sponsorship (max 10 puan)

```python
# institutional-holders verisinden:
# son çeyrek vs önceki çeyrek karşılaştır
# holder sayısı artıyor mu? toplam sahiplik yüzdesi artıyor mu?

holders = fmp_get("institutional-holders", {"symbol": symbol, "limit": 10})

# FMP'de dönem karşılaştırması sınırlı olabilir
# basit yöntem: toplam kurumsal holder sayısı + bilinen büyük fonlar var mı?

# SKORLAMA:
# büyük fon girişi var (Vanguard, BlackRock, Fidelity artırıyor) → 10/10
# kurumsal sahiplik > %60                                         → 8/10
# kurumsal sahiplik %40-%60                                       → 6/10
# kurumsal sahiplik < %40                                         → 3/10
# veri yok veya çok düşük                                         → 1/10
```

### M — Market Direction (max 10 puan)

```
# adım 1'de zaten hesaplandı, tüm adaylar için aynı skor
# SPY > SMA50 > SMA200  → 10/10
# SPY > SMA200, < SMA50 → 6/10
# SPY < SMA200          → 3/10
```

---

## ADIM 5 — SIRALAMA VE FİNAL TOP 5

```python
# toplam skor hesapla (max 100 puan)
toplam = C + A + N + S + L + I + M

# sırala, en yüksek 5'i seç
final_top5 = sorted(adaylar_skorlu, key=lambda x: x['toplam'], reverse=True)[:5]

# skor bantları:
# 85+   → "olağanüstü" (exceptional)
# 70-84 → "güçlü" (strong)
# 55-69 → "ortanın üstü" (above average)
# 40-54 → "orta" (average)
# < 40  → "zayıf" (weak) — top 5'e girmemeli
```

---

## ADIM 6 — RAPOR ÇIKTI FORMATI (haftalık rapor için)

```markdown
## 5. CANSLIM hisse taraması

**tarama tarihi**: [tarih] | **piyasa yönü (M)**: [durum] [skor]/10
**aday havuzu**: [screener'dan X hisse] → [52W filtre sonrası Y hisse] → [detaylı analiz Z hisse] → **top 5**

### sonuç tablosu

| # | ticker | şirket | sektör | C | A | N | S | L | I | M | toplam | değerlendirme |
|---|--------|--------|--------|---|---|---|---|---|---|---|--------|---------------|
| 1 | [SYM] | [isim] | [sektör] | XX | XX | XX | XX | XX | XX | XX | XX/100 | [olağanüstü/güçlü/...] |
| 2 | | | | | | | | | | | | |
| 3 | | | | | | | | | | | | |
| 4 | | | | | | | | | | | | |
| 5 | | | | | | | | | | | | |

### hisse detayları

**1. [TICKER] — [ŞİRKET] ([SEKTÖR])** — toplam: XX/100 [değerlendirme]
- **C** (XX/20): son çeyrek EPS büyümesi +%XX (YoY), [hızlanma var/yok]
- **A** (XX/20): 3 yıllık CAGR +%XX, [her yıl artış / düzensiz]
- **N** (XX/15): 52W zirvesinden -%XX, [yakın/uzak]
- **S** (XX/10): float XXM hisse, hacim oranı X.Xx
- **L** (XX/15): 3 aylık RS +%XX (sektöre göre), [lider/laggard]
- **I** (XX/10): kurumsal sahiplik %XX, [büyük fon girişi var/yok]
- **yorum**: [2-3 cümle: neden bu hisse ilginç, risk ne, potansiyel portföy uyumu]

(her 5 hisse için aynı format)

### agresif portföy için uygunluk

[top 5'ten hangisi agresif büyüme portföyüne uygun? neden?
mevcut pozisyonlarla korelasyon kontrolü.
önerilen giriş stratejisi (kademeli mi, tek seferde mi)]
```

### günlük rapordaki referans satırı

```markdown
## 5. CANSLIM taraması

son tarama: [tarih] | top 5: [SYM1], [SYM2], [SYM3], [SYM4], [SYM5]
detaylar haftalık raporda → reports/weekly/WEEKLY_REPORT_YYYY-MM-DD.md
```

---

## ADIM 7 — API MALİYET ÖZETİ

| işlem | call sayısı |
|-------|-------------|
| company-screener | 1 |
| batch-quote (52W filtre) | 1 |
| income-statement quarterly (20 aday) | 20 |
| income-statement annual (20 aday) | 20 |
| shares-float (20 aday) | 20 |
| institutional-holders (20 aday) | 20 |
| stock-price-change (bölüm 2'de yoksa) | 0-20 |
| **toplam** | **82-102** |

haftada 1 kez = günlük ortalama ~14 call (7 güne böl)

---

## ADIM 8 — KALİTE KONTROL

- [ ] company-screener kullanıldı mı? (stock-screener DEĞİL)
- [ ] 52W zirve filtresi ≤%15 uygulandı mı?
- [ ] EPS büyümesi YoY (yıldan yıla aynı çeyrek) karşılaştırma mı? (QoQ değil)
- [ ] M kriteri tüm adaylar için aynı mı?
- [ ] L kriteri sektör ETF'e göre göreceli mi? (mutlak performans değil)
- [ ] skor toplamı 100'ü geçmiyor mu?
- [ ] top 5'in hepsi skor > 40 mı?
- [ ] agresif portföy uygunluk değerlendirmesi yapıldı mı?
- [ ] günlük raporda sadece referans satırı var mı? (tam tarama yok)
