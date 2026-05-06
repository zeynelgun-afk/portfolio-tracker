# 9 Yöntem - Detaylı Formüller

Tüm yöntemler 3 senaryoda hesaplanır: Ayı / Normal / Boğa.
Çarpanlar `sektor-medyanlari.md` ve `piyasa-rejimleri.md`'den gelir.

## Ortak Tanımlar

```
P             = Mevcut hisse fiyatı
S             = Outstanding shares (market_cap / price)
EPS_TTM       = Net Income TTM / S
BVPS          = Stockholders' Equity / S
EBIT          = Operating Income (TTM)
EBITDA        = EBITDA (TTM)
Revenue       = Revenue (TTM)
NI            = Net Income (TTM)
FCF           = Operating CF - CapEx
Net_Debt      = Total Debt - Cash & ST Investments
EV            = Market Cap + Total Debt - Cash
ROE           = NI / Stockholders' Equity
EPS_FWD_2Y    = Analyst EPS estimate ~2 years out
```

## 1. Net P/E (TTM)

```
Adil_Değer_PE = EPS_TTM × Hedef_PE
```
- Hedef_PE: Sektörden gelir (her senaryo için ayrı)
- Negatif EPS varsa atla, "N/A" yaz

## 2. Forward P/E (2 yıl ileri)

```
Adil_Değer_FWD = EPS_FWD_2Y × Hedef_FWD_PE
```
- Hedef_FWD_PE genellikle TTM P/E'den biraz düşük (büyüme primli)
- Eğer 2 yıl forward yoksa 1 yıl forward al, başlığa not düş

## 3. EV/EBIT

```
EV_Hedef    = EBIT × Hedef_EVEBIT
Equity      = EV_Hedef + Cash - Total_Debt
Adil_Değer  = Equity / S
```

## 4. EV/EBITDA

```
EV_Hedef    = EBITDA × Hedef_EVEBITDA
Equity      = EV_Hedef + Cash - Total_Debt
Adil_Değer  = Equity / S
```

## 5. EV/Revenue

```
EV_Hedef    = Revenue × Hedef_EVS
Equity      = EV_Hedef + Cash - Total_Debt
Adil_Değer  = Equity / S
```

## 6. P/FCF (Normalize 4 yıl)

```
FCF_Norm    = ortalama(son 4 yıl FCF) [outlier'lar varsa median]
FCFPS_Norm  = FCF_Norm / S
Adil_Değer  = FCFPS_Norm × Hedef_PFCF
```

**Capex normalize uyarısı:** Eğer şirket büyük yatırım dönemindeyse (capex/revenue > %15), bu yöntem geçici olarak baskılı sonuç verir. Senaryo notu olarak ekle.

## 7. ROE / Justified P-B (Gordon büyüme modeli)

```
k_e         = Cost of Equity = Rf + Beta × ERP
              Rf = 4.5% (10Y UST), ERP = 5.5% varsayım
g           = Sürdürülebilir büyüme
              g = ROE × (1 - payout_ratio)  veya max %5

Justified_PB = (ROE - g) / (k_e - g)
Adil_Değer   = Justified_PB × BVPS
```

**Senaryolarda farklılık:**
- Ayı: k_e + %2, g - %1
- Normal: baseline
- Boğa: k_e - %1, g + %1

**Sınır kontrolleri:**
- ROE < %5 → yöntem güvenilmez, "N/A (ROE düşük)"
- ROE > k_e olmalı (yoksa Justified_PB negatif çıkar)
- Justified_PB minimum 0.5, maksimum 6.0 ile sınırla (extreme'i kes)

## 8. Graham Number

```
Adil_Değer = sqrt(22.5 × EPS_TTM × BVPS)
```
- EPS_TTM negatifse N/A
- BVPS negatifse N/A
- Graham 22.5 = 15 (max P/E) × 1.5 (max P/B)
- Senaryolarda farklılık:
  - Ayı: 18 katsayısı (sqrt(18 × ...))
  - Normal: 22.5 (klasik)
  - Boğa: 28 katsayısı

## 9. DCF (10 yıl + Terminal)

### Adımlar

1. **Başlangıç FCF:** Son yıl FCF veya 4 yıl ortalaması (hangisi daha temsili)
2. **Büyüme aşamaları:**
   - Yıl 1-5: yüksek büyüme (g_high)
   - Yıl 6-10: orta büyüme (g_mid)
3. **Terminal:** g_term ile sonsuz büyüme
4. **Discount:** WACC ile

### Formül

```
PV(FCF_t) = FCF_t / (1 + WACC)^t

Terminal_Value = FCF_11 × (1 + g_term) / (WACC - g_term)
PV(TV) = Terminal_Value / (1 + WACC)^10

EV_DCF = sum(PV(FCF_1..10)) + PV(TV)
Equity = EV_DCF + Cash - Total_Debt
Adil_Değer = Equity / S
```

### Senaryo Varsayımları

| Parametre | Ayı | Normal | Boğa |
|---|---|---|---|
| g_high (Yıl 1-5) | %5 | %10 | %15 |
| g_mid (Yıl 6-10) | %3 | %6 | %9 |
| g_term | %2 | %3 | %3 |
| WACC | %12 | %10 | %8 |

**Negatif FCF düzeltmesi:** Eğer mevcut FCF negatifse, yıl 1-3 için OCF×0.3 minimum kabul edilir, sonra normalize edilir.

## CV (Coefficient of Variation) Kontrolü

Her senaryo için 9 yöntemin standart sapması / ortalama oranı:
```
CV = std_dev(values) / mean(values)
```

- CV < %20: Çok güvenilir, yöntemler hizalı
- CV %20-30: Normal, dağılım kabul edilebilir
- CV ≥ %30: **TURUNCU UYARI**, yöntemler arası tutarsızlık var. Hangi yöntemin neden saptığını incele, raporda belirt.

## Pure Forward Auto-Trigger

Aşağıdaki koşullardan biri sağlanırsa hesaplamada TTM yerine forward kullan:
- Net Income TTM negatif
- Net margin TTM < %3
- EBITDA TTM, son 3 yıl ortalamasının %70'i altında (geçici düşüş işareti)

Bu durumda yöntem 1, 4, 6 forward verilerle hesaplanır ve raporda "(Forward modu aktif)" notu eklenir.

## Asimetrik Bilanço Düzeltmesi

Eğer Net Debt > Market Cap × %50 ise (yüksek kaldıraçlı şirket):
- EV/EBIT, EV/EBITDA, EV/Revenue yöntemlerinde Equity hesabı kritik.
- Ek olarak `interest_coverage < 3` kontrolü, eğer riskli ise raporda not.

## Sonuç Birleştirme

Her senaryo için:
```
ortalama = mean(geçerli_9_yontem_sonucu)
median = median(geçerli_9_yontem_sonucu)
adil_değer_alt = persentil_25
adil_değer_üst = persentil_75
```

Final raporda her senaryo için **median ± IQR/2** olarak sun.
