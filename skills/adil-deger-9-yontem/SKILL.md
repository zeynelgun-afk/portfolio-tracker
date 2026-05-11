---
name: adil-deger-9-yontem
description: ABD hisse senetleri için kapsamlı adil değer hesaplaması v5.0. 9 YÖNTEM (4 Traditional + 2 Forward + 3 Growth), DUAL-MODE sistem (GROWTH vs BLENDED), 3 piyasa rejimi (Ayı/Normal/Boğa). FMP Ultimate plan ile canlı sektör P/E, dinamik CAPM WACC, Altman Z + Piotroski risk skorları, analist sentiment momentum, FMP DCF sanity check, konsantrasyon riski tespiti. 5 YILLIK FİNANSAL PROJEKSİYON (gelir, brüt, faaliyet, net, EPS yıl yıl + Forward çarpanlar + normalizasyon yılı). PRE-IPO MODU (manuel JSON input, FMP'de olmayan şirketler için). 17 sektör marj profili. Tetikleyiciler "X hissesini değerle", "adil değer hesapla", "X için fair value", "X kaç eder", "9 yöntem değerleme", "pre-IPO analiz". Finzora AI Adil Değer v3.7.2 metodolojisi. Her kullanımda notes klasörü güncellenir.
---

# Adil Değer 9 Yöntem (Finzora AI v3.7.2) — v5.0

## Versiyon Geçmişi

**v5.0 (11 Mayıs 2026)** — Büyük Yükseltme
- 🟢 SADELEŞTIRME: 4 yöntem kaldırıldı (Graham Number, EV/EBIT, Justified P-B, Rule of 40). Skill ismi ile uyumlu **9 yöntem**.
- 🟢 FMP ULTIMATE ENTEGRASYONU: 20 endpoint kullanımı, yeni `fmp_layer.py` modülü ile sarmalandı.
- 🟢 CANLI SEKTÖR P/E: `sector-pe-snapshot` + `industry-pe-snapshot` endpoint'leri ile statik tabloyu override eder (>%50 sapmada blend).
- 🟢 DİNAMİK CAPM WACC: 10y treasury + beta ile yıllık güncel WACC, DCF hesabına injekte (8-18% sınır).
- 🟢 DCF GROWTH FIX: Sektör tablosu `g_high` yerine gerçek revenue YoY büyüme kullanılır (50% cap).
- 🟢 RİSK SKORLARI: Altman Z (iflas riski) + Piotroski (fundamental kalite) otomatik tespiti.
- 🟢 ANALİST SENTIMENT: StrongBuy/Buy/Hold/Sell/StrongSell dağılımı + son 6 ay upgrade momentum.
- 🟢 FMP DCF SANITY CHECK: FMP'nin kendi DCF'i (unlevered + levered) ile bizim DCF karşılaştırması.
- 🟢 KONSANTRASYON RİSKİ: Ürün/segment + coğrafya bazlı %50+ tek müşteri konsantrasyonu otomatik tespiti.
- 🟢 5 YILLIK PROJEKSİYON: Yeni `projection_engine.py` modülü ile yıl yıl P&L + Forward çarpan + normalizasyon yılı analizi.
- 🟢 17 SEKTÖR MARJ PROFİLİ: AI growth (CBRS, NVDA 2018), büyüyen semicon (AMD 2017-2020), olgun (NVDA 2024), SaaS growth/mature, biotech pre-revenue/commercial, pharma, devices, consumer staples, industrials.
- 🟢 PRE-IPO MODU: `--pre-ipo input.json` ile FMP'de olmayan şirketler için manuel JSON akışı.

**v4.1 (9 Mayıs 2026)** — Mantık denetimi sonrası 8 hata düzeltildi (weighted_summary None × float, PEG eps_fwd_1y, hard-coded 2027, reverse_dcf None, forward_outlier ELİMİNE, fetch retry, shares fallback)

**v4.0 (6 Mayıs 2026)** — Quality/Moat Premium (1.0-1.50x ROE+margin bazlı)
**v3.0 (6 Mayıs 2026)** — DUAL-MODE GROWTH vs BLENDED ayrımı
**v2.0 (6 Mayıs 2026)** — k_e cap, RIM fallback, CV uyarı, AI mega-cap
**v1.0 (6 Mayıs 2026)** — İlk sürüm

## Amaç

Hisse senetleri için 9 yöntem × 3 piyasa rejimi (27 değerleme noktası) + canlı sektör çarpanları + dinamik CAPM WACC + 5 yıllık projeksiyon ile adil değer hesaplar.

## Tetikleme

- "X hissesini değerle"
- "X için adil değer hesapla"
- "X kaç eder"
- "X fair value"
- "X'i 9 yöntem ile değerle"
- "X pre-IPO analiz" → `--pre-ipo` modu

## Kullanım

```bash
# Standart akış (halka açık şirketler)
python3 skills/adil-deger-9-yontem/scripts/adil_deger.py NVDA
python3 skills/adil-deger-9-yontem/scripts/adil_deger.py NVDA --json

# Pre-IPO modu (FMP'de olmayan şirketler)
python3 skills/adil-deger-9-yontem/scripts/adil_deger.py --pre-ipo input.json
python3 skills/adil-deger-9-yontem/scripts/adil_deger.py --pre-ipo input.json --json
```

## 9 Yöntem (v5.0)

### Traditional (TTM Bazlı, 4 Yöntem)
1. **Net P/E** — `EPS_TTM × sector_PE × regime_adj × ai_mult × quality_mult` (canlı sektör PE öncelikli)
2. **EV/EBITDA** — `EBITDA × sector_EV_EBITDA × ...` + cash - debt
3. **EV/Revenue** — `Revenue × sector_EV_Rev × ...` + cash - debt
4. **P/FCF** — `(FCF_4y_normalized / shares) × sector_P_FCF × ...`

### Forward (Beklenti Bazlı, 2 Yöntem)
5. **Forward P/E** — `EPS_FWD_2Y × (canlı_PE × 0.88) × regime_adj × ai_mult × quality_mult`
6. **DCF** — 10 yıl + Terminal, dinamik CAPM WACC, gerçek growth rate override

### Growth (Yeni v3, 3 Yöntem)
7. **PEG Ratio** — `EPS_FWD_1Y × growth × PEG_target` (forward outlier'da elenir)
8. **EV/Forward Revenue** — `Revenue_FWD × sector_EV_Rev × adj × qm` + cash - debt
9. **EV/Forward EBITDA** — `EBITDA_FWD × sector_EV_EBITDA × adj × qm` + cash - debt

### Bonus
- **Reverse DCF** — Mevcut fiyatın implied büyüme oranı (sadece bilgi notu, hesaba katılmaz)

## DUAL-MODE Sistemi

### 🚀 GROWTH MODU (≥3/5 kriter)
1. Forward growth ratio > 2.0
2. Revenue 3y CAGR > %20
3. Sektör Growth-friendly (semicon_design, tech_software, healthcare_biotech, communication)
4. AI mega-cap aktif
5. 1y fiyat performansı > %50

**Yöntem**: Sadece Forward + Growth (5 yöntem). Traditional sadece zemin.

### ⚖️ BLENDED MODU (kriter <3)

| Forward Growth | Traditional | Forward+Growth |
|---|---|---|
| > 1.5x | %50 | %50 |
| 1.2-1.5x | %65 | %35 |
| < 1.2x | %80 | %20 |

Tüm 9 yöntem ağırlıklandırılır.

## v5.0 Yeni Sinyaller (Ek Çıktı)

### Risk Skorları
- **Altman Z-Score** (iflas riski): >2.99 GÜVENLİ 🟢 / 1.81-2.99 BELİRSİZ 🟡 / <1.81 İFLAS RİSKİ 🔴
- **Piotroski F-Score** (fundamental kalite, 0-9): 8-9 ÇOK GÜÇLÜ 🟢 / 5-7 SAĞLAM 🟡 / 3-4 ZAYIF 🟠 / 0-2 ÇOK ZAYIF 🔴

### Analist Sentiment + Momentum
- StrongBuy / Buy / Hold / Sell / StrongSell sayıları
- Son 6 ay momentum: UPGRADE +5 ve üstü 🟢 / Stabil ⚪ / DOWNGRADE -5 ve altı 🔴

### DCF Sanity Check
- FMP DCF (unlevered + levered) vs bizim DCF normal medyan karşılaştırma
- %30+ sapmada "varsayımlar farklı, gözden geçir" uyarısı

### Konsantrasyon Riski (Otomatik)
- Ürün/segment: %70+ KRİTİK 🔴 / %50-70 YÜKSEK 🟠 / Top 2 %75+ ORTA 🟡
- Coğrafya: aynı eşikler

### Canlı Sektör P/E (Statik Tabloyu Override)
- Industry-PE öncelikli (hassas), Sector-PE fallback (geniş), statik tablo last fallback
- >%50 sapmada blend (orta nokta)

### Dinamik CAPM WACC
- WACC = Rf (canlı 10y treasury) + Beta × ERP (%6)
- Sınır: %8-%18
- Statik %10 fallback

## 5 Yıllık Finansal Projeksiyon (v5.0 Yeni)

### Otomatik Profile Tespiti
- AI saf oyuncu (CBRS, NVDA 2018-2020) — TTM op margin <%5, growth >%50
- Büyüyen yarı iletken (AMD 2017-2020) — TTM op margin %5-20
- Olgun yarı iletken (NVDA 2024, AVGO) — TTM op margin >%20
- SaaS growth (SNOW, NET, DDOG) — TTM op margin <%10, growth >%30
- SaaS mature (MSFT, ADBE, NOW) — TTM op margin >%30
- Biotech pre-revenue / commercial
- Pharma, Medical Devices, Consumer Staples, Industrials, Energy, Banks

### P&L Tablosu (6 Yıl: TTM + 5 Forward)
- Gelir + Büyüme oranı
- Brüt marj + Brüt kâr
- Faaliyet marjı + Faaliyet kârı
- Faiz gideri (manuel veya FMP)
- Vergi öncesi + Vergi (efektif oran)
- Net Marj + Net Kâr
- EPS (basic + diluted)
- CapEx (sektör profil bazlı %)

### Forward Çarpanlar (Fiyat Sabit Varsayımı)
- Forward P/E, P/S, EV/Sales, EV/EBITDA, EV/EBIT
- Hangi yılda sektör medyanına oturuyor? otomatik tespit
- Bekleme süresine göre yorum: 🟢 ≤2 yıl, 🟡 3-4 yıl, 🟠 5+ yıl

## Pre-IPO Modu (v5.0 Yeni)

FMP'de olmayan şirketler için manuel JSON input. Test örneği: `scripts/test_data/cbrs_pre_ipo.json`.

### JSON Şema
```json
{
  "ticker": "CBRS",
  "company": "Cerebras Systems Inc.",
  "sector_key": "semicon_design",
  "revenue_ttm": 510000000,
  "revenue_yoy_growth": 0.76,
  "shares_basic": 224000000,
  "shares_diluted": 257000000,
  "ipo_price_low": 150,
  "ipo_price_high": 160,
  "ipo_price_mid": 155,
  "ipo_date": "2026-05-13",
  "custom_revenues": {"2026": 1.2e9, "2027": 2.7e9},
  "interest_expense_annual": 60000000,
  "current_op_margin": -0.28,
  "is_pre_revenue": false,
  "current_cash": 4200000000,
  "current_debt": 1000000000,
  "notes": "S-1 belgesi, OpenAI MRA, AWS Bedrock vs"
}
```

Pre-IPO modunda 9 yöntem **atlanır** (TTM verisi yok), sadece projection_engine çalıştırılır.

## Premium Sistemi (3 Katmanlı)

### 1. Piyasa Rejimi Çarpanı
- Ayı: -%25-35, Normal: %0, Boğa: +%20-30

### 2. AI Mega-Cap Premium (sadece boğada)
- Tetikleme: market cap > $300B + 1y +%100+ + (semi/tech)
- Boğa multiplier: 1.40-1.55x

### 3. Quality/Moat Premium (her senaryoda)
- ROE > sektör hedef VEYA Net Margin > sektör hedef → 1.0-1.50x
- Geometrik ortalama: (ROE ratio × Margin ratio) ^ 0.5

## Piyasa Rejimleri

| Rejim | Tespit | Çarpan Düzeltme |
|---|---|---|
| Ayı | VIX > 28 veya SPY < 200SMA -%5 | -%25-35 |
| Normal | VIX 15-22, baseline | %0 |
| Boğa | VIX < 16, SPY > 200SMA +%5 | +%20-30 |

## CV Uyarı Seviyeleri

| CV | Renk | Anlam |
|---|---|---|
| < %20 | 🟢 | Yöntemler hizalı, güvenilir |
| %20-35 | 🟡 | Normal dağılım |
| %35-50 | 🟠 | Tutarsızlık var |
| ≥ %50 | 🔴 | KRİTİK: Model güvenilir değil |

## Otomatik Karar Matrisi

| Mevcut Fiyat | Öneri |
|---|---|
| ≤ Ayı medyan | 🟢 GÜÇLÜ AL |
| ≤ Normal medyan | 🟢 AL |
| ≤ Normal P75 | 🟡 İZLE / KÜÇÜK POZİSYON |
| ≤ Boğa medyan | 🟡 İZLE |
| ≤ Boğa P75 | 🟠 PAHALI / İZLE |
| ≤ Boğa P75 × 1.20 | 🟠 ÇOK PAHALI |
| > Boğa P75 × 1.20 | 🔴 GEÇ / KAÇIN |

## Veri Kaynakları (FMP Ultimate Plan — 20 Endpoint)

### Tier 1 — Manuel hesap yerine canlı
- `/profile`, `/quote`, `/income-statement`, `/cash-flow-statement`, `/balance-sheet-statement` (klasik)
- `/ratios-ttm`, `/key-metrics-ttm` (TTM oranlar hazır)
- `/sector-pe-snapshot`, `/industry-pe-snapshot` (canlı sektör P/E)
- `/historical-price-eod` (5y OHLCV)
- `/stock-peers` (dinamik peer)
- `/analyst-estimates`, `/price-target-consensus` (mevcut)
- `^VIX`, SPY (piyasa rejimi)

### Tier 2 — Yeni değerleme sinyalleri
- `/financial-scores` (Altman Z + Piotroski)
- `/grades-consensus`, `/grades-historical` (analist sentiment + momentum)
- `/discounted-cash-flow`, `/levered-discounted-cash-flow` (FMP DCF)
- `/revenue-product-segmentation`, `/revenue-geographic-segmentation` (konsantrasyon)
- `/enterprise-values` (5y tarihsel EV)

### Tier 3 — Akıllı varsayımlar
- `/treasury-rates` (canlı 10y → CAPM)
- `/ipos-calendar` (pre-IPO tespit)
- `/financial-growth` (5y tarihsel büyüme)

## Doğrulanmış Test Vakaları (v5.0)

| Ticker | Mod | Karar v5.0 | Notlar |
|---|---|---|---|
| NVDA | 🚀 GROWTH (4/5) | 🟢 AL | DCF $140 (FMP $247, -43% fark), Forward bandı $260-$498 |
| KO | ⚖️ BLENDED %80/%20 | 🟡 İZLE/KÜÇÜK | Piotroski 8/9 ÇOK GÜÇLÜ, WACC dinamik %8 |
| CBRS | Pre-IPO | 5y projeksiyon | Profile auto: AI growth, 2027 kâra geçiş, 2028 P/E 52.6x |

## Yerleşim

```
skills/adil-deger-9-yontem/
├── SKILL.md (bu dosya)
├── scripts/
│   ├── adil_deger.py (~1750 satır, ana skill)
│   ├── fmp_layer.py (12KB, Ultimate plan endpoint wrapper)
│   ├── projection_engine.py (19KB, 17 sektör profili + projeksiyon)
│   └── test_data/
│       └── cbrs_pre_ipo.json (pre-IPO örnek input)
├── tests/
│   ├── test_cbrs_pre_ipo.py
│   └── test_nvda_live.py
├── notes/
│   ├── v5_etap1_development.md
│   ├── v5_etap2_development.md
│   └── v5_etap3_development.md
└── references/
    ├── 9-yontem-formuller.md
    ├── sektor-margin-profilleri.md
    └── fmp-endpoint-rehberi.md
```

## Önemli Kurallar

- Tüm metinler Türkçe (rapor, log, notlar)
- Em dash yok, cümleler büyük harfle başlar
- Kaynak: "finzora ai"
- FMP "stable" endpoint, `epsAvg` kullan
- `^VIX` doğrudan kullanılır (VIXY proxy yasak)
- Pre-IPO mod manuel JSON gerektirir, FMP otomatik veri çekmez
- Canlı PE >%50 sapmışsa blend yap (statik + canlı ortalama)
- DCF WACC sınırı %8-%18 (CAPM dışında kalırsa statik fallback)
- Quality Premium çift sayım önleme: P/E, EV/X, P/FCF, EV/FWD x'e uygulanır
- v5.0 modülleri yüklü değilse v4.1 mode'a düşer (backward compat)

## Akış (Halka Açık Şirket)

1. FMP'den veri çek (profile, quote, income, cashflow, balance, analyst-estimates)
2. v5 kalibrasyon sinyalleri topla (canlı PE, dinamik WACC)
3. Bunları data_pack'a inject et (override değerleri)
4. calculate_methods 3 senaryoda çalıştır (bear/normal/bull)
5. v5 ek sinyaller topla (Altman Z, Piotroski, grades, FMP DCF, segmentation)
6. 5 yıllık projeksiyon üret (projection_engine)
7. format_output: temel + v5 ek sinyaller + 5y projeksiyon
8. Karar matrisi uygula

## Akış (Pre-IPO)

1. JSON dosyasını oku
2. detect_margin_profile (sektör + op margin + growth)
3. project_revenue_5y (custom_revenues veya analist)
4. project_pnl_5y (tam P&L)
5. project_multiples_5y (Forward P/E, P/S vs)
6. detect_normalization_year (canlı sektör PE varsa öncelikli)
7. format_pre_ipo_output

Kaynak: finzora ai
