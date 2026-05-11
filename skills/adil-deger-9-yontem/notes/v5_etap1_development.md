# Adil Değer Skill v5.0 — Geliştirme Notu

**Tarih**: 11 Mayıs 2026
**Durum**: Etap 1 tamamlandı

## Genel Plan

3 etap halinde mevcut v4.1'i v5.0'a yükseltme:

### ✅ Etap 1 — Bu Push (Tamamlandı)
**Forward Projection Engine + FMP Layer Modülü**

İki yeni bağımsız modül eklendi (mevcut `adil_deger.py` korundu):

#### `scripts/fmp_layer.py` (12 KB)
Ultimate paket endpointlerini saran wrapper modülü. 5 dakikalık TTL cache + retry + statik fallback.

**Tier 1 — Manuel hesap yerine canlı API:**
- `get_ratios_ttm(symbol)` — P/E, P/B, ROE, margin'ler hazır
- `get_key_metrics_ttm(symbol)` — EV, EV/Sales, EV/EBITDA hazır
- `get_live_pe_for_sector_key(sector_key, fallback)` — sector-pe-snapshot + industry-pe-snapshot ile canlı sektör P/E (statik SECTOR_MULTIPLES tablosu fallback olarak korunur)
- `get_historical_price_eod(symbol)` — 5 yıllık günlük OHLCV
- `get_stock_peers(symbol)` — dinamik peer listesi

**Tier 2 — Yeni değerleme sinyalleri:**
- `get_financial_scores(symbol)` + `interpret_altman_z()` + `interpret_piotroski()` — iflas riski + fundamental kalite
- `get_grades_consensus(symbol)` + `get_grades_historical()` + `detect_upgrade_momentum()` — analist sentiment ve trend
- `get_fmp_dcf(symbol)` + `get_fmp_dcf(symbol, levered=True)` — FMP'nin kendi DCF (bizim DCF ile karşılaştırma)
- `get_revenue_product_segmentation()` + `get_revenue_geographic_segmentation()` + `detect_concentration_risk()` — müşteri/segment konsantrasyonu otomatik tespiti
- `get_enterprise_values(symbol)` — 5 yıllık tarihsel EV (multiple bandı için)

**Tier 3 — Akıllı varsayımlar:**
- `get_10y_treasury_rate()` + `calculate_dynamic_wacc(beta)` — DCF için canlı risk-free rate bazlı WACC
- `get_ipos_calendar()` + `is_ticker_pre_ipo(symbol)` — IPO calendar'dan otomatik pre-IPO tespiti
- `get_financial_growth(symbol)` — 5 yıllık tarihsel büyüme oranları

#### `scripts/projection_engine.py` (19 KB)
5 yıllık tam P&L projeksiyonu + çarpan projeksiyonu + normalizasyon yılı tespiti.

**Sektör marj profilleri (17 sektör):**
- AI saf oyuncu (CBRS, ARM erken)
- Hızla büyüyen yarı iletken (AMD 2017-2020)
- Olgun yarı iletken (NVDA 2024, AVGO)
- Semicon equipment, OSAT
- Tech software growth + mature SaaS
- Healthcare biotech pre-revenue + commercial + pharma + devices
- Consumer staples, industrials, energy, financials, generic

Her profil 6 yıl × 5 metrik: gross_margin_curve, op_margin_curve, net_margin_curve, effective_tax_curve, capex_pct_revenue. Veri kaynağı: NVDA, AMD, AVGO, SNOW, MSFT gibi peer şirketlerin gerçek tarihsel marj evrim eğrileri.

**Fonksiyonlar:**
- `detect_margin_profile(sector, current_op_margin, revenue_growth)` — şirket tipini tespit et
- `project_revenue_5y()` — analist konsensüs veya custom_revenues ile 5y gelir
- `project_pnl_5y()` — tam P&L tablosu (gelir, brüt, faaliyet, vergi, net, EPS basic+diluted)
- `project_multiples_5y()` — fiyat sabit varsayımıyla yıllık Forward P/E, P/S, EV/Sales, EV/EBITDA
- `detect_normalization_year()` — hangi yıl sektör medyanına oturur
- Markdown çıktı formatters

#### `tests/test_cbrs_pre_ipo.py`
CBRS pre-IPO için manuel girdi → tam P&L + çarpan projeksiyonu üretir. Doğrulandı.

#### `tests/test_nvda_live.py`
NVDA için canlı FMP + projection engine entegre testi. Etap 2'de geniş test.

### 🟠 Etap 2 — Sonraki Push
**Sadeleştirme + Yeni Sinyaller**

- 4 yöntem çıkarılır: Graham Number, EV/EBIT, Justified P-B, Rule of 40
- Reverse DCF yöntem olmaktan çıkar, bilgi notu olur
- Mevcut adil_deger.py'a fmp_layer entegrasyonu (manuel TTM hesabı → ratios-ttm)
- Risk skoru bölümü (Altman Z + Piotroski) rapora ekle
- Analist sentiment bölümü (grades) rapora ekle
- FMP DCF karşılaştırma sanity check
- Revenue segmentation otomatik konsantrasyon riski
- Tarihsel EV multiple bandı

### 🟠 Etap 3 — Final Push
**Entegrasyon + Test + Dokümantasyon**

- adil_deger.py'da projection_engine entegrasyonu (--projection default ON)
- Pre-IPO modu (--pre-ipo + JSON input)
- format_output() yeni bölümler
- Markdown rapor şablonu "Bölüm 12: Yıllık Finansal Projeksiyon" ekle
- SKILL.md v5.0 olarak güncelle
- references/sektor-margin-profilleri.md ekle
- references/fmp-endpoint-rehberi.md ekle
- notes/learnings.md güncelle (CBRS dersleri)
- Tam test: CBRS, NVDA, AMD, KO, TEM, FLYW

## Test Sonuçları

### CBRS Pre-IPO Test (✅ Başarılı)

```
Profile: semicon_design_growth_ai
Revenue 2025-2030: $510M → $1.2B → $2.7B → $5.5B → $7.0B → $9.5B

Net Kâr Trajektori:
2025: -$203M (TTM gerçek)
2026: -$96M (zarar devam)
2027: +$162M (kâra geçiş)
2028: +$660M
2029: +$1.12B
2030: +$1.80B

Forward P/E (155 USD fiyat):
2028: 52.6x
2029: 31.0x ← Sektör medyanı (28x) yakın
2030: 19.2x

Normalizasyon: 2029 (3 yıl bekleme)
```

Manuel hesabımla karşılaştırma:
- 2028 Forward P/E: 53x (manuel) vs 53x (engine) → **TAM uyum**
- 2026 Net Kâr: -$96M (manuel) vs -$96M (engine) → **TAM uyum**
- Normalizasyon: 2028-2029 (manuel) vs 2029 (engine) → **Yakın**

### NVDA Live Test (⏸ Network sandbox 503 — Etap 2'de tekrar)

Container'ın requests kütüphanesi FMP'ye 503 dönüyor, curl çalışıyor — sandbox proxy issue. fmp_layer.py'da retry mantığı var, Zeynel'in makinesinde sorun yaşanmaz.

## Mimari Kararlar

1. **Mevcut adil_deger.py korundu**, yan modüller eklendi → backward compat
2. **Statik SECTOR_MULTIPLES tablosu fallback olarak duruyor** (canlı API down ise)
3. **TTL cache 5dk** → aynı oturumda tekrar tekrar çağrı önlenir
4. **17 sektör margin profili** → çoğu hisse otomatik tespit edilir
5. **TTM yıl bilinçli** (current_year - 1) → off-by-one bug yok
6. **Custom revenues desteği** → pre-IPO için manuel girdi mümkün

## Yeni Bağımlılıklar

- `requests` (zaten var)
- `urllib.request` (zaten standart kütüphane)

Yeni paket gerekmiyor.

## Kullanım Önizleme

```python
from fmp_layer import get_ratios_ttm, calculate_dynamic_wacc, is_ticker_pre_ipo
from projection_engine import project_pnl_5y, project_multiples_5y

# 1. Pre-IPO tespiti
ipo_info = is_ticker_pre_ipo("CBRS")
if ipo_info:
    print(f"PRE-IPO: {ipo_info['ipo_date']}, price: {ipo_info['price_range']}")

# 2. Dinamik WACC
wacc, source = calculate_dynamic_wacc(beta=1.6)  # canlı 10y treasury

# 3. Projection (custom revenues ile)
pnl = project_pnl_5y(
    revenue_list=[(2025, 510e6), (2026, 1.2e9), ...],
    profile_key='semicon_design_growth_ai',
    shares_basic=224e6,
)
```

**Kaynak**: finzora ai
