# Adil Değer Skill v5.0 — Etap 13 Fix-2 Notu (Hibrit Forward Normalize)

**Tarih**: 11 Mayıs 2026
**Tetikleyici**: APLD raporu — Adil değer $3.16 (%-93), Stop $39.96 / Hedef $3.16 (ters mantık).
**Önceki düzeltme**: Fix-1 (3 modlu giriş planı). Bu Fix-2 valuation methodolojisini yenidan kurguluyor.

## Felsefi Soru

Skill TTM revenue + sektör multiple ile APLD gibi pivot şirketleri **dramatik yanlış** fiyatlıyor:
- TTM revenue $216M × 4x EV/Sales = $864M EV → fair price $3
- Gerçek: APLD AI/HPC pivot ortasında, FY2028 revenue $1.58B, hyperscaler $7.5B lease

Beyin fırtınası sonucu: **TTM yöntemleri bazı durumlarda yanıltıcı**, **analyst forward EPS daha güvenilir**.

## Karar: Forward-First Hibrit

Skill'in 9 yönteminin medyanı (TTM ağırlıklı) yerine **analyst raw EPS bazlı hibrit hesap** ana adil değer olur.

Seçilen Hibrit yaklaşım:
- **Seçenek 4** (Normalizasyon Yılı) + **Seçenek 2** (2 Yıl Ortalama)
- Akıllı yıl seçimi + outlier'dan kaçınma

## Hibrit Hesap Mantığı

```python
def calculate_forward_normalized_value(analyst_eps_dict, sector_pe, wacc, sub_premium):
    # 1. İlk pozitif EPS yılını bul (norm_year)
    # 2. Y_norm + Y_norm+1 EPS ortalaması (2 yıl)
    # 3. × sektör forward P/E × sub-industry premium
    # 4. Bugüne diskonto (WACC ile)
```

### Sektör P/E Seçimi (Sub-Industry'e Göre)

| Sub-Industry | Sektör P/E | Premium | Mantık |
|---|---|---|---|
| AI_INFRASTRUCTURE | **Canlı** (örn 49x) | 1.0 | Canlı PE growth zaten dahil |
| CLOUD_NATIVE_SAAS | **Canlı** | 1.0 | Aynı |
| AI_MEGACAP | **Statik** (NVDA = 24x) | 1.25 | Yerleşik mega-cap |
| GROWTH_DEFAULT | **Statik** | 1.0 | Mature/value şirketler |

### Pivot Tespiti

```python
PIVOT_DETECTED = (
    revenue_yoy > 0.50           # Dramatic büyüme
    AND ttm_op_margin < 0         # Eski iş kolu zayıf
    AND analyst_rev_fy1 / ttm_revenue > 2.0  # Forward sıçraması
    AND forward_data_quality in ('CONSENSUS', 'SINGLE')
)
```

Pivot tespit edilirse markdown'a 🔄 rozet, karar değişmez (sadece bilgi).

### Sub-Industry Premium Tespiti

3 keyword grubu:
- compute: 'high-performance computing', 'hpc hosting', 'gpu computing'
- infra: 'data center', 'ai factory', 'ai infrastructure'
- demand: 'hyperscaler', 'ai workloads', 'foundational ai'

En az 2 grup eşleşmesi + revenue YoY > %30 + sektör IT/Software/RE → AI_INFRASTRUCTURE

## Forward-First Karar Override

```python
if forward_normalized exists AND eps_source == 'analyst_raw' AND data_quality in ('CONSENSUS', 'SINGLE'):
    primary_adil_deger = forward_normalized_value
    karar = decide_by_ratio(price / forward_normalized_value)
    heritage_median saklanır (transparency için referans)
```

Ratio bantları:
- ≤ 0.70 → 🟢 GÜÇLÜ AL (derin değer)
- 0.70-0.90 → 🟢 AL
- 0.90-1.10 → 🟡 İZLE (adil değer civarı)
- 1.10-1.30 → 🟠 PAHALI / İZLE
- > 1.30 → 🔴 GEÇ / KAÇIN

## Test Sonuçları (5 Hisse)

| Hisse | Heritage | Hibrit | Mevcut | Analyst | Karar | Değerlendirme |
|---|---|---|---|---|---|---|
| **APLD** | $3.16 | **$48.96** | $45.44 | $44-50 | 🟡 İZLE | ✅ TAM UYUM |
| **NVDA** | $259 | $197.64 | $220.86 | $235-280 | 🟠 PAHALI | Hafif altta (AI_MEGACAP premium beklenirdi) |
| **KO** | $59 | $60.69 | $78.40 | $70-75 | 🟠 PAHALI | ✅ Mature için doğru |
| **AAOI** | $217 | $77.37 | $181 | $63-220 | 🔴 GEÇ | Hibrit daha temkinli |
| **AVGO** | $125 | $351.68 | $429.66 | ? | 🟠 PAHALI | Heritage çok düşüktü, Hibrit daha doğru |

## Bilinen İyileştirme Alanları

1. **AAOI bull case**: Hibrit $77 — Rosenblatt $220 hedef ile büyük makas. AAOI için CONSENSUS data (3 analyst) ama 2y ort ($1+$5.44)/2=$3.22 stagger oluyor. AI_INFRASTRUCTURE tetiklenmiyor (description AI/HPC keyword'leri eksik).
2. **NVDA AI_MEGACAP premium**: 1.25x devreye girmesi gerekirdi (Hibrit $197 yerine $246 olmalı). `is_ai_megacap` flag'i kontrol edilmeli.
3. **Pivot detection eşiği**: APLD için 2.0x sınırda (FY+1/TTM ≈ 2.0). 1.5-1.7x'e düşürmek daha fazla pivot yakalar.
4. **Eski yıllarda eps_basic yanlış**: PNL projection'ı sektör profile'a bağlı. APLD'nin tüm EPS'leri negatif çıkıyor (-$0.31 → -$3.64). Yine de **analyst raw EPS kullandığımız için Hibrit doğru çalışıyor**.

## Markdown Değişiklikleri

Snapshot tablosuna yeni satırlar:
- `| Mod | **Forward-First Hibrit** (analyst raw EPS bazlı) |`
- `| Normalize Yıl | YYYY (ilk pozitif EPS) |`
- `| Normalize EPS (2y ort) | $X.XX |`
- `| Sub-Industry Premium | 1.5x (AI_INFRASTRUCTURE) |` (varsa)
- `| Pivot Mode | 🔄 EVET — Dramatic dönüşüm |` (varsa)

Ana adil değer satırı (Forward-First aktifse):
```
**Adil Değer (Hibrit Forward Normalize)**: $48.96
**9 Yöntem Medyanı (referans)**: $3.16
**Potansiyel**: %7.7 yukarı (mevcut $45.44)
```

Giriş Planı bölümünde de Hibrit değeri Hedef 1 olarak kullanılır.

## Sonraki Düzeltmeler (Etap 13 Fix-3 adayları)

- AI_MEGACAP detection NVDA için çalışmıyor (is_ai_megacap flag kontrolü)
- AAOI AI_INFRASTRUCTURE tetiklenmiyor (description keyword'leri zenginleştirilmeli)
- Pivot eşiği 2.0 → 1.5-1.7 (daha fazla pivot şirketi yakalanır)
- analyst_eps_dict boşsa veya tüm yıllar negatifse fallback davranış (şu an None döner)

Kaynak: finzora ai
