# Adil Değer Skill v5.0 — Etap 3 Notu

**Tarih**: 11 Mayıs 2026
**Durum**: Etap 3 tamamlandı

## Yapılan Değişiklikler

### A. Kalibrasyon Override Sistemi

v5 sinyalleri artık `calculate_methods()`'tan **ÖNCE** toplanıyor ve hesaplara override değer olarak besleniyor. Bu sayede 9 yöntem hesabı gerçek piyasa parametreleri ile yapılıyor.

#### 1. Net P/E + Forward P/E için Canlı Sektör P/E

```python
live_pe, source = fmp_layer.get_live_pe_for_sector_key(sector_key, static_fallback_pe=static_pe)
if source in ('industry', 'sector') and abs(deviation) > 0.5:
    # %50+ sapma varsa blend yap (orta nokta)
    data_pack['live_pe_override'] = (live_pe + static_pe) / 2
elif source in ('industry', 'sector'):
    # Normal sapma — canlı veriyi direkt kullan
    data_pack['live_pe_override'] = live_pe
```

calculate_methods içinde:
```python
pe_mult = data.get('live_pe_override') or sector_mults['pe']  # canlı öncelik
fwd_pe_mult = (data.get('live_pe_override') * 0.88) if override else sector_mults['fwd_pe']
```

#### 2. DCF için Dinamik WACC (CAPM)

```python
dyn_wacc, source = fmp_layer.calculate_dynamic_wacc(beta=profile_beta)
# CAPM = Rf + Beta × ERP (6%) + Country Risk
# Sınır 8-18% (otomatik clip)
if 'CAPM' in source and 0.08 <= dyn_wacc <= 0.18:
    data_pack['dynamic_wacc'] = dyn_wacc
```

calculate_methods içinde DCF:
```python
wacc = data.get('dynamic_wacc') or adj['wacc']
```

#### 3. DCF için Gerçek Revenue Growth

Statik `g_high` (sektör tablosu) çok düşük kalıyordu. Şimdi gerçek `revenue_yoy` ile karşılaştırılıyor:

```python
static_g_high = sector_mults['g_high'] + adj['g_high_adj']
actual_growth = data.get('revenue_growth_yoy')
if actual_growth and actual_growth > static_g_high:
    g_high_eff = min(actual_growth, 0.50)  # 50% cap
else:
    g_high_eff = static_g_high
```

### B. 5 Yıllık Projeksiyon Entegrasyonu

`analyze()` sonuna `projection_engine` çağrısı eklendi. **Default ON** — flag gerekmez.

Adımlar:
1. `detect_margin_profile()` — sektör + op margin + growth oranı bazlı otomatik profil
2. `project_revenue_5y()` — analist 2y forward + kademeli azalan büyüme
3. `project_pnl_5y()` — tam P&L (gelir → brüt → faaliyet → vergi → net → EPS)
4. `project_multiples_5y()` — Forward P/E, P/S, EV/Sales, EV/EBITDA (fiyat sabit varsayımıyla)
5. `detect_normalization_year()` — canlı sektör P/E'ye göre hangi yıl oturur

Çıktı: format_output sonuna **"📅 5 YILLIK FİNANSAL PROJEKSİYON"** bölümü.

### C. Pre-IPO Modu (Yeni)

FMP'de bulunmayan şirketler için manuel JSON input ile akış. Yöntem hesabı yok, sadece projeksiyon.

CLI:
```bash
python3 adil_deger.py --pre-ipo test_data/cbrs_pre_ipo.json
```

JSON şema:
```json
{
  "ticker": "CBRS",
  "company": "Cerebras Systems Inc.",
  "sector_key": "semicon_design",
  "revenue_ttm": 510000000,
  "revenue_yoy_growth": 0.76,
  "shares_basic": 224000000,
  "shares_diluted": 257000000,
  "ipo_price_mid": 155,
  "ipo_date": "2026-05-13",
  "custom_revenues": {"2026": 1200000000, "2027": 2700000000, ...},
  "interest_expense_annual": 60000000,
  "current_op_margin": -0.28,
  "current_cash": 4200000000,
  "current_debt": 1000000000,
  "notes": "OpenAI MRA + AWS Bedrock..."
}
```

Yeni fonksiyonlar:
- `analyze_pre_ipo(json_path)` — JSON oku, projeksiyon üret
- `format_pre_ipo_output(result)` — sade çıktı formatı

## Test Sonuçları

### NVDA (Halka Açık, AI Mega-Cap)

**Kalibrasyon öncesi (v5.0 Etap 2):**
- Net P/E (statik 28x): Traditional medyan $120 (bear normal)
- DCF: $59 (statik WACC %10, g_high %15)
- Forward Bandı: $137-$294
- FMP DCF karşılaştırması: %-76 fark 🔴

**Kalibrasyon sonrası (v5.0 Etap 3):**
- Net P/E (canlı 62x ile blend 45x): Traditional medyan $120 → $192 (genişledi)
- DCF: **$140** (dinamik WACC %17.84, gerçek growth %65)
- Forward Bandı: **$260-$498** (gerçekçi, analist konsensüsü $275 ile uyumlu)
- FMP DCF karşılaştırması: **%-43 fark** 🟠 (kabul edilebilir)
- 5Y projeksiyon: 2025 EPS $2.25 → 2030 $9.21
- Normalizasyon: **🟢 2026** (sektör medyanı 62x'e 0 yıl bekleme)

### KO (Olgun Defansif, Düşük Beta)

- Altman Z: 5.18 🟢, Piotroski: **8/9 🟢 ÇOK GÜÇLÜ**
- WACC dinamik: %8 (beta 0.36) — statik %10'dan düşük
- Canlı consumer-defensive P/E: 41.8x vs statik 20x → %+109 sapma
- 5Y projeksiyon: 2025 EPS $1.95 → 2030 $2.74
- Forward P/E 2030: 28.6x
- Normalizasyon: **🟢 2026** (sektör medyanı 42x'e 0 yıl bekleme)
- Karar: 🟡 İZLE / KÜÇÜK POZİSYON (BLENDED mode, Trad %80 / FwdGrowth %20)

### CBRS (Pre-IPO, AI Saf Oyuncu)

`--pre-ipo test_data/cbrs_pre_ipo.json` ile çalıştırıldı.

- Profil otomatik: `semicon_design_growth_ai` ✅
- Revenue 2025-2030: $510M → $1.2B → $2.7B → $5.5B → $7B → $9.5B
- Net Kâr 2026: **-$96M** (manuel hesap: -$96M — TAM uyum)
- Net Kâr 2027: +$162M (kâra geçiş yılı)
- Net Kâr 2028: +$660M
- 2028 Forward P/E: **52.6x** (manuel: 53x — TAM uyum)
- 2029 EPS: $5.00 (manuel: $4.79)
- 2030 EPS: $8.06 (manuel: $7.50)
- Normalizasyon: **🟢 2028** (sektör medyanı 62x — canlı veri ile)

## Mimari Kararlar

### 1. Override Stratejisi Sıralaması

İlk olarak kalibrasyon sinyalleri (canlı PE, dinamik WACC) toplanır. **Sonra** calculate_methods çağrılır. Diğer sinyaller (risk skorları, sentiment, FMP DCF, segmentation) hesap **sonrasında** toplanır çünkü FMP DCF ile bizim DCF'i karşılaştırmak için bizim DCF'in önce hesaplanmış olması gerekir.

### 2. Blend Mantığı (Sektör PE)

Canlı PE statik tablodan %50'den fazla saparsa, **ortalama** alınır. Sebep:
- Statik tablo eskimiş olabilir (yukarı sapma)
- Canlı veri geçici yüksek (multiple inflation) olabilir
- Orta nokta daha muhafazakar bir tahmin

%50 altı sapmada canlı veri direkt kullanılır.

### 3. WACC Sınır Kontrolü

CAPM %8-%18 dışına çıkarsa override yapılmaz, statik kullanılır. Sebep:
- %8 altı: Risk-free anormal düşük, makul değil
- %18 üstü: Aşırı yüksek beta (>2.5), aşırı volatil
- Bu sınırlar pratik hesap istikrarı için

### 4. DCF Growth Override

Sektör tablosu `g_high` (semicon %15) NVDA gibi gerçek %65 büyüyen şirketler için çok düşük. Override sınırı: gerçek growth varsa kullan, ama 50%'de cap'le (sürdürülebilir değil).

### 5. Pre-IPO için Ayrı Akış

`analyze_pre_ipo()` ayrı bir fonksiyon. Sebep:
- TTM bazlı 9 yöntem hesaplanamaz (TTM verisi yok)
- FMP'de profile, ratios, key-metrics yok
- Sadece projection_engine kullanılabilir
- Output formatı da farklı (`format_pre_ipo_output`)

## Test Karşılaştırma Tablosu

| Metrik | v4.1 | v5.0 Etap 1 | v5.0 Etap 2 | v5.0 Etap 3 |
|---|---|---|---|---|
| Yöntem sayısı | 13 | 13 | 9 | 9 |
| NVDA DCF | $59 | $59 | $26 | **$140** |
| NVDA FMP DCF fark | bilmiyorduk | bilmiyorduk | -76% | -43% |
| Sektör PE kaynağı | statik | statik | statik | **canlı + blend** |
| WACC kaynağı | statik %10 | statik %10 | statik %10 | **CAPM canlı** |
| Pre-IPO desteği | ❌ | ❌ | ❌ | **✅ JSON input** |
| 5Y projeksiyon | ❌ | engine var | engine var | **✅ entegre** |
| Risk skorları | ❌ | ❌ | ✅ | ✅ |
| Analist sentiment | ❌ | ❌ | ✅ | ✅ |
| Konsantrasyon riski | ❌ | ❌ | ✅ | ✅ |

## Kalan Çalışmalar (Etap 4'e)

### Yüksek Öncelik
- SKILL.md v5.0 olarak güncelle
- references/sektor-margin-profilleri.md (17 profil dokümentasyonu)
- references/fmp-endpoint-rehberi.md (Ultimate plan endpoint guide)
- references/9-yontem-formuller.md güncelle (4 yöntem kaldırıldı)
- notes/learnings.md (NVDA/KO/CBRS test bulguları)

### Orta Öncelik
- Markdown rapor üretici (`--md` flag) — 12 bölüm tam protokole uygun çıktı
- Geniş test: AMD, TEM, FLYW, SMCI, AVGO (5+ ticker)
- AnalistDCF sanity check threshold konfigürable (%30 → %50 arası)

### Düşük Öncelik
- analyst_estimates 1y/2y çoklu yıl projection için entegrasyon
- Tarihsel multiple bandı (enterprise-values 5y) projection'a entegre
- Pre-IPO modu için canlı IPO calendar bilgisi otomatik enrich

## Kod İstatistikleri

| Metrik | Önceki (Etap 2) | Şimdi (Etap 3) |
|---|---|---|
| adil_deger.py satır | 1341 | ~1750 |
| Toplam dosya (skill) | 5 | 6 (test_data/cbrs_pre_ipo.json) |
| FMP endpoint kullanımı | 20 | 20 |
| Override mekanizması | yok | 3 (live_pe, dynamic_wacc, actual_growth) |
| Modlar | standart | standart + pre-IPO |
| CLI flag | --json | --json, --pre-ipo |

**Kaynak**: finzora ai
