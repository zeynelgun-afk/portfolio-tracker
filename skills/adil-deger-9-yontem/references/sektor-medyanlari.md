# Sektör Medyan Çarpanları (10 Yıllık)

> **v5.0 NOT (11 Mayıs 2026)**: Bu dosyadaki **statik** sektör tabloları v5.0'da **fallback** olarak korunur. Skill öncelikle FMP `sector-pe-snapshot` ve `industry-pe-snapshot` ile **canlı veri** çekiyor. Canlı veri statik tablodan %50+ saparsa blend yapılır (orta nokta). NVDA testinde canlı semicon industry P/E 62.3x iken statik tablo 28x'ti — %+123 sapma. Bkz `fmp-endpoint-rehberi.md`.

Tüm değerler **Normal Piyasa** baseline'dır. Ayı/Boğa ayarlamaları için `piyasa-rejimleri.md` ile çarpılır.

## Auto-Detection Kuralları

```python
def detect_sector(profile):
    sector = profile.get('sector', '').lower()
    industry = profile.get('industry', '').lower()
    
    # Semiconductors özel preset
    if 'semiconduct' in industry:
        # OSAT (Amkor, ASE) düşük marjlı
        if any(k in profile.get('description', '').lower() 
               for k in ['osat', 'packaging', 'assembly and test', 'foundry']):
            return 'semicon_osat'
        return 'semicon_design'  # Fabless / IDM
    
    if sector == 'technology':
        if 'software' in industry:
            return 'tech_software'
        return 'tech_hardware'
    
    if sector == 'financial services':
        if 'bank' in industry:
            return 'financials_bank'
        if 'insurance' in industry:
            return 'financials_insurance'
        return 'financials_other'
    
    if sector == 'healthcare':
        if any(k in industry for k in ['biotech', 'drug']):
            return 'healthcare_biotech'
        if 'pharma' in industry:
            return 'healthcare_pharma'
        return 'healthcare_devices'
    
    if sector in ['consumer cyclical', 'consumer defensive']:
        if sector == 'consumer defensive':
            return 'consumer_staples'
        return 'consumer_discretionary'
    
    if sector == 'industrials':
        return 'industrials'
    
    if sector == 'energy':
        return 'energy'
    
    if sector == 'real estate':
        return 'reits'
    
    if sector == 'utilities':
        return 'utilities'
    
    if sector == 'communication services':
        return 'communication'
    
    return 'generic'
```

## Sektör Preset Tablosu (Normal Piyasa)

### Technology

#### tech_software
- P/E: 28
- Forward P/E: 24
- EV/EBIT: 22
- EV/EBITDA: 18
- EV/Revenue: 6.0
- P/FCF: 28
- ROE hedefi: %20
- DCF g_high: %12

#### tech_hardware
- P/E: 22
- Forward P/E: 20
- EV/EBIT: 17
- EV/EBITDA: 13
- EV/Revenue: 3.5
- P/FCF: 22
- ROE hedefi: %18
- DCF g_high: %8

### Semiconductors

#### semicon_design (NVDA, AMD, AVGO, MRVL, QCOM)
- P/E: 28
- Forward P/E: 24
- EV/EBIT: 22
- EV/EBITDA: 18
- EV/Revenue: 7.0
- P/FCF: 30
- ROE hedefi: %25
- DCF g_high: %15

#### semicon_osat (AMKR, ASX)
- P/E: 18
- Forward P/E: 16
- EV/EBIT: 14
- EV/EBITDA: 11
- EV/Revenue: 2.0
- P/FCF: 22
- ROE hedefi: %15
- DCF g_high: %8
- **Not:** OSAT'lar capital-intensive, FCF zayıf, marjlar düşük

#### semicon_equipment (ASML, AMAT, LRCX, KLAC)
- P/E: 26
- Forward P/E: 22
- EV/EBIT: 20
- EV/EBITDA: 16
- EV/Revenue: 6.0
- P/FCF: 26
- ROE hedefi: %22
- DCF g_high: %12

### Financials

#### financials_bank
- P/E: 11
- Forward P/E: 10
- EV/EBIT: 9 (limited use)
- EV/EBITDA: 8 (limited use)
- EV/Revenue: 3.0
- P/FCF: 12 (limited)
- ROE hedefi: %12
- Justified P-B çok önemli (1.2-1.5)
- DCF g_high: %5
- **Not:** Bankalarda P-B ve ROE-driven yaklaşım dominant

#### financials_insurance
- P/E: 12
- Forward P/E: 11
- ROE hedefi: %12
- Justified P-B: 1.3
- DCF g_high: %5

### Healthcare

#### healthcare_pharma
- P/E: 18
- Forward P/E: 16
- EV/EBIT: 15
- EV/EBITDA: 12
- EV/Revenue: 4.0
- P/FCF: 20
- ROE hedefi: %18
- DCF g_high: %6

#### healthcare_biotech
- P/E: 25 (kazanç istikrarsızsa N/A)
- Forward P/E: 22
- EV/EBIT: 20
- EV/EBITDA: 16
- EV/Revenue: 6.0
- P/FCF: 25
- ROE hedefi: %15
- DCF g_high: %12

#### healthcare_devices
- P/E: 24
- Forward P/E: 20
- EV/EBIT: 18
- EV/EBITDA: 15
- EV/Revenue: 5.0
- P/FCF: 24
- ROE hedefi: %18
- DCF g_high: %8

### Consumer

#### consumer_staples
- P/E: 20
- Forward P/E: 18
- EV/EBIT: 16
- EV/EBITDA: 13
- EV/Revenue: 2.5
- P/FCF: 22
- ROE hedefi: %18
- DCF g_high: %5

#### consumer_discretionary
- P/E: 18
- Forward P/E: 16
- EV/EBIT: 14
- EV/EBITDA: 11
- EV/Revenue: 2.0
- P/FCF: 20
- ROE hedefi: %15
- DCF g_high: %7

### Industrials & Energy

#### industrials
- P/E: 18
- Forward P/E: 16
- EV/EBIT: 14
- EV/EBITDA: 11
- EV/Revenue: 2.0
- P/FCF: 20
- ROE hedefi: %15
- DCF g_high: %6

#### energy
- P/E: 12
- Forward P/E: 10
- EV/EBIT: 8
- EV/EBITDA: 6
- EV/Revenue: 1.5
- P/FCF: 12
- ROE hedefi: %12
- DCF g_high: %3
- **Not:** Petrol fiyatına çok bağımlı, normalize edilmiş kazanç kullan

### Diğer

#### reits
- P/E: 18 (FFO bazlı tercih edilir, P/FFO hedef 16)
- Forward P/E: 16
- EV/EBITDA: 16
- EV/Revenue: 7.0
- P/FCF: 18 (P/AFFO daha doğru)
- ROE hedefi: %10
- DCF g_high: %4

#### utilities
- P/E: 18
- Forward P/E: 16
- EV/EBIT: 14
- EV/EBITDA: 11
- EV/Revenue: 3.0
- P/FCF: 18
- ROE hedefi: %10
- DCF g_high: %4

#### communication
- P/E: 20
- Forward P/E: 18
- EV/EBIT: 15
- EV/EBITDA: 10
- EV/Revenue: 3.0
- P/FCF: 20
- ROE hedefi: %15
- DCF g_high: %6

#### generic (fallback)
- P/E: 20
- Forward P/E: 17
- EV/EBIT: 15
- EV/EBITDA: 12
- EV/Revenue: 2.5
- P/FCF: 22
- ROE hedefi: %15
- DCF g_high: %7

## Sektör Medyanları Güncelleme Politikası

Bu medyanlar tarihsel ortalamalardır. Her 10 kullanımda usage_log.csv incelenir, gerekirse güncellenir.

**Veri kaynağı:** S&P Capital IQ, Bloomberg, FactSet 10 yıl medyanları (manuel doğrulama gerekli her 6 ayda bir).

**Son güncelleme:** 6 Mayıs 2026 (ilk versiyon)
