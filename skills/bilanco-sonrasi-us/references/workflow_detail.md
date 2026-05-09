# Workflow Detayları — Bilanço Sonrası ABD Tarayıcısı

Bu doküman 5 aşamalı pipeline'ın her adımının metodolojisini detaylıca açıklar.

## Aşama 1: Earnings Tarama + Mid-Cap+ Filtre

**Script**: `scripts/01_earnings_calendar.py`

### Veri Akışı

```
FMP earnings-calendar?from=X&to=Y
    ↓ (1.000-2.000 hisse, küresel)
US filter (ticker'da "." veya "-" yok)
    ↓ (~1.300)
actualEPS or actualRevenue dolu olanlar
    ↓ (~900)
Profile çek (mcap, price, exchange)
    ↓
Mid-cap+ filtre: mcap≥$2B, price≥$10, exchange in (NYSE, NASDAQ, AMEX),
                  not isEtf, not isFund, isActivelyTrading
    ↓ (~150-300)
01_filtered_midcap.json
```

### Parametre Ayarları

- `--min-mcap`: Daha küçük cap için $1B'ye indirilebilir, ancak likidite ve smart money sinyalleri zayıflar
- `--min-price`: $5'e indirilirse penny stock riski, $10 default mantıklı

### Bilinen Tuzaklar

- `exchange` alanı kullan, `exchangeShortName` DEĞİL (FMP stable endpoint tuzağı, bkz. `docs/FMP_SKILL.md`)
- ADR'ler bazen "TM" (Toyota), "SHEL" (Shell) gibi US ticker'a sahip ama foreign issuer — şu anda elenmiyor (US olarak işliyor), bu kabul edilebilir çünkü bunlar genelde NYSE'de işlem görüyor

## Aşama 2: YoY/QoQ İyileşme Filtresi

**Script**: `scripts/02_growth_filter.py`

### Veri Akışı

```
Her hisse için income-statement?period=quarter&limit=5
    ↓
q[0] = en son çeyrek (yeni biten, bilanço açıkladı bu)
q[1] = bir önceki çeyrek (QoQ karşılaştırma)
q[4] = 1 yıl önceki aynı çeyrek (YoY karşılaştırma)
    ↓
4 kriter:
  - YoY ciro: pass if q[0].rev / q[4].rev - 1 ≥ 8%
  - YoY net kâr: pass if (q[4].ni > 0 ve %15+) VEYA L2P (q[4].ni < 0 < q[0].ni)
  - QoQ ciro: pass if q[0].rev / q[1].rev - 1 ≥ 3%
  - QoQ net kâr: pass if (q[1].ni > 0 ve ≥ 0% delta) VEYA L2P
    ↓
Filter: YoY ciro ZORUNLU + en az 3/4 toplam
    ↓
Outlier: yoy_rev > 500% silinir (IPO/M&A artefaktı)
    ↓
~30-60 hisse → growth_score'la sırala → 02_growth_passed.json
```

### Skor Formülü

```python
score = min(yoy_rev_pct, 100)                          # ciro büyümesi (cap 100)
      + min(max(yoy_eps_pct, -50), 200) * 0.5          # EPS büyümesi (clamp -50, +200)
      + qoq_rev_pct * 2                                # QoQ momentum 2x ağırlık
      + (50 if loss_to_profit_yoy else 0)              # L2P bonusu
      + (30 if loss_to_profit_qoq else 0)              # QoQ L2P bonusu
```

Bu sıralama Aşama 3'e geçecek hangi hisselerin önce işleneceğini belirler. Aşama 3 default olarak ilk 45'i alır.

### Veri Eksikliği Durumu

5 çeyrek income-statement gelmezse (yeni IPO veya FMP coverage eksik) hisse atlanır. Bu durum normalde %1-2 hisseyi etkiler.

## Aşama 3: Adil Değer + Sağlamlık Filtresi

**Script**: `scripts/03_valuation.py`

### 4 Yöntem ve Ağırlıkları

| # | Yöntem | Endpoint | Ağırlık | Mantık |
|---|--------|----------|---------|--------|
| 1 | Analyst Target Consensus | `price-target-consensus` | 30% | Wall Street ortalama hedef |
| 2 | Forward P/E × NTM EPS | `analyst-estimates` × sektör çarpanı | 30% | Gelecek 12 ay kazanca göre |
| 3 | PEG = 1 fair value | TTM EPS × growth (cap 5-30%) | 20% | Büyümeye göre F/K hak ediş |
| 4 | EV/EBITDA peer median | `key-metrics-ttm` × sektör çarpanı − net debt | 20% | Operasyonel kâra göre |

Sektör çarpanları kod içinde sabit (`SECTOR_PE_FAIR`, `SECTOR_EVEBITDA_FAIR`). Gelecek versiyonda dinamik (FMP `sector-pe-snapshot` endpoint'i ile) yapılabilir.

### Sağlamlık Filtresi (CRITICAL)

İki kriter zorunlu:

1. **Analyst target ZATEN +25% upside** — En güvenilir tek metrik. Bu olmadan diğer 3 yöntem yanıltabilir (örn. FIS'te Forward P/E $215 hesaplandı ama analist hedef sadece $67 = +54%, bu daha gerçekçi).
2. **En az 1 fundamental teyit** — Forward P/E veya EV/EBITDA en az +20% upside göstermeli. Tek başına analyst target yetmez, çünkü analyst beklenti sıkışmış da olabilir.

Bu çift filtre **FIS'te %215 fair value gibi yöntem dispersion artefaktlarını** ya da **LYFT'te $99 PEG distortion'ını** eler.

### L2P Düzeltmesi

`loss_to_profit_yoy = True` olan hisselerde:
- PEG yöntemi ağırlığı 0'a indirilir
- Kalan 3 yöntem (analyst target, forward P/E, EV/EBITDA) ile yeniden ortalama alınır
- `fair_value_adj` ve `upside_pct_adj` alanları eklenir

Final sıralamada `upside_pct_adj` kullanılır.

### Confidence (CV)

Yöntem değerlerinin **coefficient of variation** (sd/mean) hesaplanır:
- CV < 0.20 → YÜKSEK güven (yöntemler birbirini onaylıyor)
- CV 0.20-0.40 → ORTA güven
- CV > 0.40 → DÜŞÜK güven (yöntemler dağınık, dikkatli yorumla)

Düşük güvenli hisseler skor düşmez ama raporta "CV yüksek" notu eklenir.

## Aşama 4: Bilanço Sonrası Sinyaller (CORE — Bu Skill'in Özgün Kısmı)

**Script**: `scripts/04_post_earnings_signals.py`

### 4a) Analist Revize Yön Sayımı

`price-target-news?symbol=X&limit=20`

Filtre: `publishedDate >= earnings_date`

Yön tespiti (newsTitle anahtar kelime):
- "raise", "boost", "upgrade" → RAISED
- "lower", "cut", "downgrade", "reduce" → LOWERED
- Diğer → NEUTRAL

**Verdict matrisi**:

| Raised | Lowered | Verdict | Yorum |
|--------|---------|---------|-------|
| ≥8 | 0 | VERY_STRONG_RAISE | CON+ (henüz örnek yok) |
| ≥1 | 0 | STRONG_RAISE | BILL örneği (MS+Opp) |
| ≥2× lowered | <yarısı | NET_RAISE | Hafif pozitif |
| Eşit | Eşit | MIXED | Nötr |
| <yarısı | ≥2× raised | NET_LOWER | Hafif negatif |
| 0 | ≥1 | STRONG_LOWER | TOST örneği |
| 0 | ≥8 | CAPITULATION | HUBS örneği (13/13) |
| 0 | 0 | NO_DATA | FIS örneği (henüz revize gelmedi) |

### 4b) Transcript Guidance Extract

`earning-call-transcript?symbol=X&year=Y&quarter=Q` (FMP Ultimate)

**Endpoint adı tuzağı**: `earning-call-transcript` (TEKİL "earning"). Çoğul `earnings-call-transcript` 404 verir.

**Fiscal year çevirisi**: `NON_CALENDAR_FISCAL` mapping (BILL, CRM, ORCL, NKE, CSCO, WMT). Calendar quarter → fiscal quarter dönüşümü.

**Anahtar kelime skor sistemi**: Cümle bazında, `GUIDANCE_KEYWORDS` ağırlıkları toplanır. Skor ≥4 olan top 12 cümle döndürülür.

**Verdict tespiti** (full content içinde regex):
- "raising the midpoint", "raised our", "increasing the", "we are raising" → RAISED
- "lowering our", "we are lowering" → LOWERED
- "reaffirm" → REAFFIRMED
- Hiçbiri yok ama transcript var → QUALITATIVE_ONLY (CELH örneği)

### 4c) 13F Kurumsal Birikim + Smart Money

`institutional-ownership/symbol-positions-summary?symbol=X&year=Y&quarter=Q`

**Verdict matrisi**:

| Shares Δ | Investors Δ | Verdict | Yorum |
|----------|-------------|---------|-------|
| >+1M | ≥0 | STRONG_ACCUMULATION | Büyük birikim |
| >0 | >0 | ACCUMULATION | Yeni isim girişi + birikim |
| >0 | <0 | CONSOLIDATION | Yatırımcı azaldı, kalanlar büyütüyor |
| <0 | >0 | ROTATION | Yeni isim giriyor, eski büyük çıktı |
| <0 | herhangi | DISTRIBUTION | Net çıkış |
| 0 | herhangi | STABLE | Hareketsiz |

**Smart money kontrolü**: 5 büyük yatırımcının (Druckenmiller, Buffett, Burry, Tepper, Ackman) Q-1 holdings'i çekilir, shortlist sembolleri var mı bak.

**Genişletilmiş smart money listesi**: `references/smart_money_ciks.md`

## Aşama 5: Final Sıralama + Yıldız Skor

**Script**: `scripts/05_finalize.py`

### Yıldız Sistemi (Maks 5)

```
+1 ★ : Adil değer +30%+ analist hedefli (ana metrik)
+1 ★ : Şirket guidance RAISED (transcript) VEYA REAFFIRMED + güçlü forward sinyal (VST gibi)
+1 ★ : Net analist target raised > lowered (post-earnings)
+1 ★ : 13F shares net birikim (>+1M Q-1) VEYA ACCUMULATION verdict
+1 ★ : Smart money portföyünde (Druckenmiller/Buffett/Burry/Tepper/Ackman)
```

### Eleme Kriterleri (Yıldıza Bakmadan Çıkar)

- Analist verdict CAPITULATION, STRONG_LOWER, NET_LOWER → ele
- Transcript verdict LOWERED → ele

Bu hisseler `eliminated` listesinde "fallen angel adayı" olarak takipte tutulur, 2-3 hafta sonra yeniden değerlendirilebilir.

### Sıralama

`(yıldız sayısı, analyst_target_upside)` ikili anahtar — yıldız yüksek olan önce, eşitlikte upside yüksek olan önce.

### Çıktı Yapısı

```json
{
  "date": "2026-05-09",
  "final_ranked": [...],     // Top N
  "eliminated": [...],        // Fallen angel adayları
  "watchlist": [...]          // Top sonrası ilk 5 (orta tier)
}
```

## Yıldız Yorumlaması

| Yıldız | Yorum | Aksiyon |
|--------|-------|---------|
| 5 ★★★★★ | Tüm sinyaller hizalı, "all green" | Yüksek-konfidens pozisyon adayı |
| 4 ★★★★☆ | Hemen hemen tüm sinyaller, 1 eksik | Standart pozisyon |
| 3 ★★★☆☆ | Yarısı sinyal | Watchlist + tetikleyici bekle |
| 2 ★★☆☆☆ | Az sinyal | Bekleme listesi |
| 0-1 ★ | Yetersiz | Genelde 03'ten geçemez |

## Pipeline Süresi Tahmini

FMP Ultimate plan'da 3000 calls/min:

- Aşama 1: ~1.000-2.000 calls (~1-2 dakika)
- Aşama 2: ~50-300 calls (~30 saniye)
- Aşama 3: ~200 calls × ilk 45 = ~250 calls (~30 saniye)
- Aşama 4: ~3-5 calls × shortlist (10-15) = ~50 calls (~10 saniye) + 5 smart money calls
- Aşama 5: tamamen lokal hesap (~1 saniye)

**Toplam**: ~3-5 dakika tüm pipeline (Premium plan'da 750 calls/min'de ~10-15 dakika sürerdi).

## İlgili Dökümanlar

- `references/smart_money_ciks.md` — Genişletilmiş yatırımcı CIK tablosu
- `references/known_traps.md` — Pipeline tasarımına yansıyan tuzaklar
- `templates/rapor_template.md` — Final rapor şablonu
- `docs/FMP_SKILL.md` — FMP endpoint referansı (özellikle Ultimate-only ve alan adı tuzakları)
- `skills/adil-deger-9-yontem/SKILL.md` — Top 3 için ayrıca çalıştırılan tam adil değer raporu
