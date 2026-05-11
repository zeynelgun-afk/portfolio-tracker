# Adil Değer Skill v5.0 — Etap 12 Notu (Forward Veri Kalitesi)

**Tarih**: 11 Mayıs 2026
**Tetikleyici**: AAOI raporu — skill 🟢 GÜÇLÜ AL dedi ama gerçekte değerleme şişkindi.

## Bulunan 3 Bug

### Bug 1: FMP Alan Adı Yanlışlığı 🔴 KRİTİK

Skill `numAnalystsEstimatedRevenue` / `numAnalystsEstimatedEps` arıyordu — bu alanlar FMP'de **YOK**.

FMP'nin gerçek alan adları: `numAnalystsRevenue` / `numAnalystsEps`

Bu nedenle skill **her zaman 0 analyst** olarak görüyordu (NVDA dahil 40+ analyst'li mega-cap'ler bile). Tüm `data_quality` mantığı ALGORITHMIC'e düşüyordu.

### Bug 2: 3 Yıl Forward EPS Alıyordu (Adı 2y idi)

`adil_deger.py` satır 909: `target_year_2y = str(this_year + 2)`

Mayıs 2026'da:
- `this_year + 2 = 2028` → FMP fiscal year 2028-12-31 EPS'i alınıyor → **2.5 yıl forward**
- Sektör standardı Forward P/E: **NTM (1y) veya FY1 (next fiscal year)**

AAOI etkisi: 2028 EPS $10.45 (tek analyst bull case) yerine 2027 EPS $5.44 (3 analyst gerçek konsensüs) alınmalıydı.

NVDA'da bu bug daha az hasarlıydı çünkü Y1-Y2-Y3 arası büyüme yumuşak. AAOI gibi **pozitife geçen** şirketlerde Y1→Y2 üstel sıçradığı için bug %200 hata yaratıyordu.

Düzeltme: `target_year_2y = str(this_year + 1)` (FY+1, sektör standart)

### Bug 3: Forward Veri Kalitesi Sınıflandırması Yoktu

Eski mantık: numAnalysts > 0 → kullan, sıfır → atla (tüm verisi atılırdı).

AAOI gibi durumlarda bu çok katı: 1 analyst veya FMP algorithmic veri **bilgi taşır** — tamamen atmamak gerekir.

Yeni sınıflar (`data_quality`):

| Sınıf | Koşul | Anlam | Karar Etkisi |
|---|---|---|---|
| **CONSENSUS** | numAnalysts ≥ 2 | Gerçek analyst konsensüsü | Tam güven |
| **SINGLE** | numAnalysts = 1 | Tek analyst görüşü | Confidence max ORTA |
| **ALGORITHMIC** | numAnalysts = 0 | FMP extrapolation (yönetim guidance/capacity) | Confidence max ORTA, "bull case görünümlü" uyarısı |
| **UNKNOWN** | Hiç veri yok | Forward yöntem kullanılamaz | Confidence DÜŞÜK zorla |

## Değişiklikler

### `fmp_layer.py`

```python
def get_analyst_estimates_multi_year(symbol, years=5, min_analysts=0):
    # min_analysts=0 default → ALGORITHMIC veri de dahil
    # ... data_quality flag ataması ...
    if analyst_count >= 2: data_quality = 'CONSENSUS'
    elif analyst_count == 1: data_quality = 'SINGLE'
    else: data_quality = 'ALGORITHMIC'
```

### `adil_deger.py`

Yeni return alanları:
- `analyst_count_fwd` — kullanılan forward yıldaki analyst sayısı
- `forward_data_quality` — CONSENSUS/SINGLE/ALGORITHMIC/UNKNOWN

Confidence override mantığı:
```python
if forward_data_quality == 'UNKNOWN':
    confidence = "DÜŞÜK"  # Hiç forward yok
elif forward_data_quality in ('ALGORITHMIC', 'SINGLE') and confidence == "YÜKSEK":
    confidence = "ORTA"  # En fazla ORTA
if piotroski <= 4 and confidence == "YÜKSEK":
    confidence = "ORTA"
```

Yeni markdown bölümleri:
- Snapshot tablosu: `Forward Veri Kalitesi | ✅/⚠️/🟡/🔴 X analyst (...)`
- Risk uyarıları: ALGORITHMIC / SINGLE / UNKNOWN için ayrı uyarılar
- Kalite tuzağı tespiti: Piotroski ≤3 + FMP DCF negatif → 🚨 uyarı

## Karşılaştırma — AAOI

| Metrik | Etap 11 (buggy) | Etap 12 (düzeltilmiş) | Değişim |
|---|---|---|---|
| Forward EPS yıl | 2028 (Y2/3y forward) | 2027 (Y1/1y forward) | Doğru yıl |
| EPS değeri | $10.45 (1 analyst bull) | $5.44 (3 analyst konsensüs) | Gerçekçi |
| Forward P/E | $417.28 | $217.35 | -%48 |
| EV/FWD Revenue | $350.59 | $237.69 | -%32 |
| **Adil Değer** | **$350.59** | **$217.35** | **-%38** |
| Karar | 🟢 GÜÇLÜ AL | 🟢 AL | Daha temkinli |
| Confidence | DÜŞÜK | DÜŞÜK | Aynı (Piotroski 2/9) |
| Risk uyarısı sayısı | 2 | 5+ | Detaylı |

Web'deki gerçek analyst price targets:
- Rosenblatt: $220 (en bull) — Skill'in adil değeri $217.35 ile **%1 fark**
- Simply Wall St 12-month avg: $151 — Skill'in adil değerinden %30 düşük (skill bull tarafta ama makul)
- TipRanks ortalama: $82.25 — Bear case

Skill'in $217 adil değeri Rosenblatt'la **neredeyse aynı** — kalibre.

## Karşılaştırma — NVDA

| Metrik | Etap 11 | Etap 12 | Değişim |
|---|---|---|---|
| Forward EPS yıl | 2028 (FY3) | 2027 (FY1) | Doğru yıl |
| EPS değeri | $10.59 | $8.02 | Doğru konsensüs |
| Forward P/E | (sektör + AI premium ile $677) | $620.77 | -%8 |
| Forward Veri Kalitesi | (gizli) | ✅ 40 analyst | Görünür |
| Adil Değer | $259 | $259 | Aynı (NVDA için bug etkisi küçüktü) |

## Faydası

1. **Algorithmic veri kaybedilmiyor**: AAOI gibi pozitife geçen şirketler için FMP'nin guidance bazlı tahminleri **kullanılır ama flag'lenir**.
2. **Bug görünür**: Analyst sayısı snapshot'ta belirgin — kullanıcı ham veri kalitesini görür.
3. **Confidence kalibre**: ALGORITHMIC + Piotroski zayıf → otomatik confidence düşer.
4. **Karar override yok**: Skill yine matematiğine göre karar verir, ama **risk uyarıları detaylı**.
5. **Sektör standardı**: Forward P/E artık FY1 (NTM ile uyumlu), Wall Street convention.

## Sonraki Adımlar

- **Analyst price target consensus** ekle — bizim adil değer / analyst avg target karşılaştırması → "izole tahmin" uyarısı
- **Forward outlier kontrolü** — negatif TTM + pozitif Forward durumunda spread kontrolü (örn EPS_FWD/EPS_TTM oranı negatif olduğunda absolute spread kullan)
- **EPS_TTM negatif durumda Forward zorla outlier mantığı** — şu an çalışmıyor (eps_ttm > 0 şartı var)

Kaynak: finzora ai
