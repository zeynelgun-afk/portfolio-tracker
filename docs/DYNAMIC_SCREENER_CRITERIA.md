# dinamik hisse seçim kriterleri

> versiyon: 1.0 | tarih: 12 nisan 2026
> amaç: agresif portföy için piyasa rejimine göre FMP screener kriterleri
>
> ⚠️ TEMEL KURAL: bu dosyada hisse ismi YAZILMAZ.
> AI her seansta FMP company-screener ile o anki koşullara uyan
> hisseleri bizzat bulur. Sabit liste = eski liste = kaçırılan fırsat.

---

## nasıl kullanılır

1. Piyasa rejimini belirle (`data/market_regime.json`)
2. İlgili rejimin screener parametrelerini al
3. FMP `company-screener` endpoint'ini çağır
4. Çıkan listeyi teknik filtrelerden geçir (RSI, SMA, ichimoku)
5. En yüksek skorlu 2-3 adayı portföye ekle

```python
# standart çağrı
results = fmp_get("company-screener", {
    **kriter_dict,
    "isActivelyTrading": "true",
    "exchange": "NYSE,NASDAQ",
    "limit": 30
})
# ardından: RSI 40-75, SMA50 üstü, hacim >1.5x filtrele
```

---

## rejim bazlı kriterler

### 1. TREND_BULL / sakin yükseliş (VIX <22)

**hedef profil**: yüksek büyüme, AI dönüşümü, güçlü momentum

```python
{
    "sector": "Technology,Communication Services",
    "marketCapMoreThan": 10_000_000_000,       # >$10B
    "betaMoreThan": 1.0,                        # momentum karakteri
    "volumeMoreThan": 1_000_000,
    "priceMoreThan": 20,
    "limit": 30
}
```

**teknik filtreler** (FMP technical-indicators ile):
- RSI(14) 45–70 arası
- SMA50 üstünde
- 1M momentum > %5
- 6M momentum > %15

**temaslar** (screener sonrası tema eşleştir):
- AI altyapı ve yazılım
- bulut platformları
- siber güvenlik
- kurumsal otomasyon

---

### 2. VOLATILE_BULL / oynaklıklı yükseliş (VIX 22-28)

**hedef profil**: kaliteli büyüme + yüksek nakit akışı, VIX dayanıklı

```python
{
    "sector": "Technology,Communication Services,Energy",
    "marketCapMoreThan": 50_000_000_000,        # >$50B mega-cap öncelikli
    "betaMoreThan": 0.8,
    "volumeMoreThan": 2_000_000,
    "priceMoreThan": 30,
    "limit": 30
}
```

**teknik filtreler**:
- RSI(14) 40–65
- SMA200 üstünde (trend kırılmamış)
- FCF yield > %3 (FMP key-metrics-ttm ile kontrol)

---

### 3. KRİZ aktif — JEOPOLİTİK/SAVAŞ (VIX 28-35)

**hedef profil**: kriz faydalananları — savaş/enerji/risk-off

#### 3a. savunma
```python
{
    "sector": "Industrials",
    "industry": "Aerospace & Defense",
    "marketCapMoreThan": 5_000_000_000,
    "volumeMoreThan": 500_000,
    "limit": 20
}
```

#### 3b. enerji (E&P ve rafineri)
```python
{
    "sector": "Energy",
    "marketCapMoreThan": 5_000_000_000,
    "volumeMoreThan": 1_000_000,
    "limit": 20
}
```

**teknik filtreler**:
- 5G momentum > %0 (düşmüyor)
- SMA50 üstünde VEYA SMA50'ye geri dönen (oversold bounce)
- RSI 35–70

#### 3c. altın / değerli maden
```python
{
    "sector": "Basic Materials",
    "industry": "Gold,Silver,Precious Metals",
    "marketCapMoreThan": 2_000_000_000,
    "volumeMoreThan": 500_000,
    "limit": 15
}
```

#### 3d. siber güvenlik (her kriz tipinde geçerli)
```python
{
    "sector": "Technology",
    "industry": "Software - Infrastructure",
    "marketCapMoreThan": 10_000_000_000,
    "betaMoreThan": 0.8,
    "volumeMoreThan": 1_000_000,
    "limit": 15
}
# ardından: "cyber", "security", "threat" içeren şirketleri filtrele
# veya FMP profile -> description içinde "cybersecurity" ara
```

#### 3e. nükleer / baz yük enerji
```python
{
    "sector": "Utilities",
    "marketCapMoreThan": 5_000_000_000,
    "volumeMoreThan": 500_000,
    "limit": 15
}
# ardından: FMP profile -> description içinde "nuclear" ara
```

---

### 4. KRİZ aktif — ENFLASYON/FAİZ ŞOKU

**hedef profil**: emtia, bankalar, gerçek varlıklar

```python
# emtia üreticileri
{
    "sector": "Basic Materials,Energy",
    "marketCapMoreThan": 5_000_000_000,
    "dividendMoreThan": 1.0,               # temettü ödeyen emtia şirketi
    "volumeMoreThan": 1_000_000,
    "limit": 20
}

# bankalar
{
    "sector": "Financial Services",
    "industry": "Banks - Regional,Banks - Diversified",
    "marketCapMoreThan": 10_000_000_000,
    "betaMoreThan": 0.8,
    "limit": 15
}
```

---

### 5. KRİZ aktif — TİCARET SAVAŞI/TARİFE

**hedef profil**: domestik gelir, küçük-orta cap, hizmet sektörü

```python
{
    "sector": "Industrials,Consumer Defensive,Healthcare",
    "marketCapMoreThan": 2_000_000_000,
    "marketCapLowerThan": 50_000_000_000,  # mega-cap değil, domestik
    "country": "US",
    "volumeMoreThan": 500_000,
    "limit": 25
}
```

**ek filtre**: FMP profile -> `revenueByGeography` → US geliri >%80

---

### 6. BEAR / düşüş trendi (SPY SMA200 altında)

**hedef profil**: defansif büyüme — düşüşe dirençli ama büyüyen

```python
# defansif büyüme (düşük beta, yüksek kalite)
{
    "sector": "Technology,Healthcare,Consumer Defensive",
    "marketCapMoreThan": 20_000_000_000,
    "betaLowerThan": 1.2,
    "dividendMoreThan": 0.5,               # temettü ödeyen tercih
    "volumeMoreThan": 1_000_000,
    "limit": 20
}
```

**teknik filtreler**:
- SMA200 üstünde (piyasa bear olsa da hisse dirençli)
- RS rank: son 6 ayda SPY'yi geçmiş

---

## skor ve seçim protokolü

screener sonuçlarına şu metrikler uygulanır:

```python
def dinamik_skor(ticker, rejim):
    skor = 0

    # momentum (rejim bağımsız)
    if momentum_1m > 10:  skor += 3
    elif momentum_1m > 0: skor += 1

    if momentum_6m > 30:  skor += 3
    elif momentum_6m > 15: skor += 2
    elif momentum_6m > 0:  skor += 1

    # teknik
    if rsi between 45 and 70: skor += 2
    if sma50_ustu: skor += 2
    if golden_cross: skor += 2

    # kalite
    if roic > 15: skor += 3
    elif roic > 10: skor += 1
    if pe_ratio > 0 and pe_ratio < 40: skor += 1

    # kriz rejiminde ek puan
    if rejim in ["KRİZ", "KRİZ_RALLİ"]:
        if sektor in KRIZ_FAYDALANICILAR[aktif_kriz_tipi]:
            skor += 3

    return skor

# seçim: skor >= 10 → EKLE, 7-9 → İZLE, <7 → GEÇ
```

---

## kriz tipi → hedef sektör eşlemesi

bu tablo K-13 v4.1 ile senkronize tutulur (TRADING_PLAYBOOK.md master):

| kriz tipi | birinci öncelik sektör | ikinci öncelik sektör |
|-----------|------------------------|----------------------|
| jeopolitik/savaş | savunma + enerji E&P | altın + siber güvenlik |
| pandemi/sağlık | sağlık + tech | e-ticaret + cloud |
| enflasyon/faiz | emtia + bankalar | enerji + REIT (dikkatli) |
| ticaret savaşı | domestik hizmet + sağlık | küçük cap US gelirli |
| finansal/sistemik | GIRIŞ YOK | nakit + altın ETF |

---

## güncelleme kuralı

bu dosyadaki kriterler piyasa koşulları değişince güncellenir.
hisse isimleri asla eklenmez — kriterler eklenir.

*finzora ai | 12 nisan 2026 | dinamik hisse seçim kriterleri*
