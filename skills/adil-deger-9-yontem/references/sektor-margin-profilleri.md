# Sektör Marj Profilleri (v5.0 Projection Engine)

`scripts/projection_engine.py` içindeki `SECTOR_MARGIN_PROFILES` sözlüğünün dokümantasyonu.

## Mantık

Her profil 6 yıl × 5 metrik:
- `gross_margin_curve` — brüt marj eğrisi
- `op_margin_curve` — faaliyet marjı eğrisi
- `net_margin_curve` — net marj eğrisi
- `effective_tax_curve` — efektif vergi oranı
- `capex_pct_revenue` — CapEx / Revenue oranı

Yıl 0: TTM gerçek (geçen yıl tamamlanmış). Yıl 1-5: forward projeksiyon.

## Otomatik Profile Tespiti

```python
projection_engine.detect_margin_profile(
    sector_key='semicon_design',  # SECTOR_MULTIPLES anahtarından
    current_op_margin=-0.28,      # TTM faaliyet marjı
    revenue_yoy_growth=0.76,      # Son yıl büyüme
    is_pre_revenue=False,         # Revenue < $50M ise True
)
# → 'semicon_design_growth_ai' (negative op margin + high growth)
```

Tespit kuralları:

| Sektör + Durum | Profile |
|---|---|
| semicon_design + op<5% + growth>50% | semicon_design_growth_ai |
| semicon_design + op<20% | semicon_design_growth |
| semicon_design + op>20% | semicon_design_mature |
| semicon_equipment | semicon_equipment |
| semicon_osat | semicon_osat |
| software + op<10% + growth>30% | tech_software_growth |
| software + op>10% | tech_software_mature_saas |
| hardware | tech_hardware |
| biotech + pre_revenue | healthcare_biotech_pre_revenue |
| biotech + ticari | healthcare_biotech |
| pharma | healthcare_pharma |
| devices | healthcare_devices |
| consumer_staples | consumer_staples |
| industrials | industrials |
| energy | energy |
| bank | financials_bank |
| (diğer) | generic |

## 17 Profil Detay

### Yarı İletken

**semicon_design_growth_ai** — AI saf oyuncu, hızla büyüyen (CBRS, ARM erken yıllar, NVDA 2018-2020)
- Brüt marj: 39% → 54% (6 yılda)
- Faaliyet marjı: **-28% → 25%** (zarardan kâra geçiş)
- Net marj: -15% → 19%
- Vergi: %0 → %21
- CapEx: %8 → %6 of revenue

**semicon_design_growth** — Olgunlaşmaya doğru ilerleyen (AMD 2017-2020)
- Brüt marj: 45% → 54%
- Faaliyet marjı: 5% → 27%
- Net marj: 3% → 22%

**semicon_design_mature** — Olgun, güçlü marjlı (NVDA 2024, AVGO, MRVL)
- Brüt marj: 55% → 58%
- Faaliyet marjı: 32% → 35%
- Net marj: 26% → 29%

**semicon_equipment** — ASML, AMAT, LRCX, KLAC
- Brüt marj: 48% → 51%
- Faaliyet marjı: 28% → 32%
- Net marj: 23% → 26%

**semicon_osat** — Foundry, packaging (AMKR, ASE)
- Brüt marj: 15% → 18% (düşük marjlı capital-heavy)
- Faaliyet marjı: 5% → 9%
- CapEx: %18 → %13 (yüksek)

### Yazılım

**tech_software_growth** — Hızla büyüyen SaaS, kâra geçmemiş (SNOW, NET, DDOG 2020-2022)
- Brüt marj: 70% → 79%
- Faaliyet marjı: -20% → 20%
- Net marj: -15% → 16%

**tech_software_mature_saas** — Olgun SaaS (MSFT, ADBE, NOW, CRM)
- Brüt marj: 78% → 81%
- Faaliyet marjı: 30% → 35%
- Net marj: 24% → 28%

**tech_hardware** — DELL, HPE, SMCI
- Brüt marj: 20% → 23%
- Faaliyet marjı: 8% → 11%

### Sağlık

**healthcare_biotech_pre_revenue** — Klinik aşama
- Brüt marj: 85% (sabit, küçük revenue üzerinden)
- Faaliyet marjı: **-200% → +25%** (uzun yol)
- Net marj: -200% → 20%

**healthcare_biotech** — Ticari biotech (kâr veren)
- Brüt marj: 82% → 86%
- Faaliyet marjı: 25% → 32%
- Net marj: 20% → 25%

**healthcare_pharma** — PFE, JNJ, LLY
- Brüt marj: 75% → 78%
- Faaliyet marjı: 30% → 33%
- Net marj: 22% → 25%

**healthcare_devices** — ISRG, EW, BSX, MDT
- Brüt marj: 65% → 68%
- Faaliyet marjı: 22% → 25%
- Net marj: 17% → 20%

### Diğer

**consumer_staples** — KO, PG, PEP, COST
- Brüt marj: 45% → 47%
- Faaliyet marjı: 22% → 24%
- Net marj: 17% → 18%

**industrials** — CAT, HON, GE, RTX
- Brüt marj: 30% → 32%
- Faaliyet marjı: 13% → 15%
- Net marj: 9% → 11%

**energy** — XOM, CVX, OXY (döngüsel olduğu için sabit)
- Brüt marj: 30%
- Faaliyet marjı: 14%
- Net marj: 10%
- CapEx: %10 (yüksek)

**financials_bank** — JPM, BAC, WFC
- Brüt marj: 55% (NII margin proxy)
- Faaliyet marjı: 30%
- Net marj: 25%

**generic** — Sektör tespit edilemedi (fallback)
- Brüt marj: 40% → 43%
- Faaliyet marjı: 15% → 18%
- Net marj: 10% → 13%

## Veri Kaynakları

Profil eğrileri **gerçek tarihsel marj evrim**lerinden türetildi:
- NVDA 2018-2024 income statement (AI growth profili için baz)
- AMD 2017-2023 (büyüyen semicon profili için)
- AVGO, MRVL, KLAC olgun yıllar (mature için)
- MSFT, ADBE, NOW son 5 yıl (mature SaaS)
- SNOW, NET, DDOG 2019-2024 (SaaS growth)

## Override Mekanizması

`projection_engine.project_pnl_5y()` `override_curves` parametresi alır:

```python
projection_engine.project_pnl_5y(
    revenue_list=revenues,
    profile_key='semicon_design_growth_ai',
    shares_basic=224e6,
    override_curves={
        'op_margin_curve': [-0.28, -0.10, 0.05, 0.15, 0.20, 0.23],  # daha temkinli
    }
)
```

Pre-IPO modunda bu özellikle yararlıdır — analist tahminleri yoksa elle ayarlanır.

## Önemli Notlar

- Profiller **mutlak değer** olarak yorumlanır, **TTM gerçek üzerine delta değil**. CBRS testinde bu bir bug olarak fark edildi ve Yıl 0 = TTM gerçek alınarak düzeltildi.
- Vergi pre-tax pozitifse uygulanır, negatif pre-tax'ta vergi sıfır
- Net income için profile net_margin ile op_margin türetilen net_income arasında min alınır (muhafazakar)
- CapEx şu an P&L'de gösterilmiyor, sadece FCF projeksiyonunda kullanılabilir (Etap 5)

## İleride Eklenebilecekler

- **Profil delta'ya geçiş**: Mutlak yerine TTM üzerine değişim oranları (her şirkete kendi başlangıç noktasından)
- **Peer-tarihsel benchmark**: Şirket için gerçek peer'lerin tarihsel marj eğrisini çekip override
- **S-curve interpolation**: TTM gerçek → 5y hedef arasında nonlinear geçiş
- **Sektör listesi genişleme**: Real estate, utilities, communication services preset eksik

Kaynak: finzora ai
