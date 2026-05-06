# Piyasa Rejimleri - Çarpan Ayarları

3 piyasa rejimi her sektör presetine uygulanır:

## Rejim Tespiti

### VIX + SPY 200 SMA Bazlı

```
def tespit_rejim(vix, spy_200ma_distance):
    # spy_200ma_distance = (SPY_current - SPY_200SMA) / SPY_200SMA
    
    if vix < 16 and spy_200ma_distance > 0.05:
        return "BOĞA"      # Risk-on
    
    if vix > 28 or spy_200ma_distance < -0.05:
        return "AYI"       # Risk-off
    
    if vix < 22 and spy_200ma_distance > -0.02:
        return "NORMAL"    # Yatay/sakin
    
    # Geçiş bölgeleri
    if vix > 22:
        return "AYI_HAFIF"
    
    return "NORMAL"
```

**Not:** Skill her durumda 3 senaryoyu da hesaplar. Tespit sadece "şu an hangisindeyiz" işaretlemesi için.

## Çarpan Düzeltme Faktörleri

Her yöntemin "Normal" çarpanına uygulanan multiplier:

| Yöntem | Ayı (×) | Normal (×) | Boğa (×) |
|---|---|---|---|
| P/E | 0.70 | 1.00 | 1.25 |
| Forward P/E | 0.72 | 1.00 | 1.22 |
| EV/EBIT | 0.72 | 1.00 | 1.22 |
| EV/EBITDA | 0.75 | 1.00 | 1.20 |
| EV/Revenue | 0.65 | 1.00 | 1.30 |
| P/FCF | 0.70 | 1.00 | 1.25 |
| Justified P-B | (k+%2, g-%1) | baseline | (k-%1, g+%1) |
| Graham | 18 katsayı | 22.5 | 28 |
| DCF | WACC %12, g düşük | WACC %10 | WACC %8, g yüksek |

## Mantık Açıklaması

### Ayı Piyasası (Risk-Off)
- Yatırımcılar risk primi talep eder, çarpanlar daralır
- Bilanço gücü ön plana çıkar (Graham, ROE/P-B)
- Multiple kontraksiyon tarihsel olarak %25-35 (S&P 500 dot-com 2002, GFC 2008-2009, COVID 2020 Mart, 2022 ayı)
- WACC artar (risk premium genişler)
- Büyüme beklentileri düşer

### Normal Piyasa
- Tarihsel medyan değerler
- VIX 15-22 aralığı
- SPY 200 SMA çevresinde

### Boğa Piyasası (Risk-On)
- Multiple ekspansiyonu, momentum primi
- Büyüme hisseleri lehine
- WACC düşer, FCF büyüme bekleyişi yüksek
- Tarihsel boğa rallileri %20-30 multiple expansion getirir
- Özellikle yüksek beta/secular tema hisseler için belirgin

## Uygulama Örneği

Şirket: Semicon Design (NVDA)
Normal P/E: 28

- Ayı eder: EPS × (28 × 0.70) = EPS × 19.6
- Normal eder: EPS × 28
- Boğa eder: EPS × (28 × 1.25) = EPS × 35

Buna göre 3 senaryo değer aralığı çıkar.

## Sektör-Spesifik Ayarlamalar

### Defansif Sektörler (Staples, Utilities, Healthcare-Pharma)
Boğa multiplier daha düşük (1.10-1.15), çünkü defansiflerin boğa piyasasında relatif performansı zayıf.

### Döngüsel Sektörler (Energy, Industrials, Consumer Cyclical)
Ayı multiplier daha sert (0.55-0.65), çünkü döngüsel düşüşte tepki büyük.

### Yüksek Beta / Secular Büyüme (Semicon Design, Tech Software, Biotech)
Boğa multiplier daha yüksek (1.30-1.40), çünkü momentum primi büyük. Ama ayıda da daha sert düşüş (0.55-0.65).

### Bankalar
P-B değişimi dominant. Ayıda 0.7-0.9, boğada 1.4-1.6 P-B.

## Tarihsel Referanslar (Kalibrasyon)

| Dönem | Rejim | S&P 500 P/E | Yorum |
|---|---|---|---|
| 2000 dot-com pik | Boğa zirvesi | 28-30 | Aşırı boğa |
| 2002 dip | Ayı | 17 | Multiple kontraksiyon |
| 2007 pik | Boğa | 17-18 | Standart boğa |
| 2009 dip | Ayı | 11-12 | Sert ayı |
| 2018 sonu | Ayı_hafif | 16 | Hafif düzeltme |
| 2020 Mart | Ayı | 14 | COVID şok |
| 2021 sonu | Boğa | 24-26 | Aşırı boğa |
| 2022 sonu | Ayı | 17 | Faiz şoku |
| 2024-2025 | Boğa | 22-24 | AI primli |
| 2026 Mayıs | Belirlenecek | - | Mevcut |

## Kişiselleştirme Notu

Bu çarpanlar başlangıç noktasıdır. Her şirkette aşağıdaki faktörler de düşünülmeli:
- Şirket-spesifik moat (büyük moat = boğada daha yüksek prim)
- Yönetim kalitesi
- Bilanço gücü
- Cash conversion (yüksek = ayıda daha az multiple kontraksiyon)
