---
name: adil-deger-9-yontem
description: ABD hisse senetleri için 9 yöntemli kapsamlı adil değer hesaplaması yapar (Net P/E, Forward P/E, EV/EBIT, EV/EBITDA, EV/Revenue, P/FCF, ROE/Justified P-B, Graham, DCF). Ayı/Normal/Boğa olmak üzere 3 piyasa rejiminde ayrı eder değer üretir. Dual-track raporlama (Traditional vs Forward), AI mega-cap özel preset, otomatik karar matrisi, analist konsensüs entegrasyonu içerir. Tetikleyiciler "X hissesini değerle", "adil değer hesapla", "X için fair value", "X kaç eder", "9 yöntem değerleme", "AMKR değerlemesi yap", "MSFT eder fiyatı". Finzora AI sisteminin Adil Değer v3.7.2 metodolojisini uygular. Her kullanımda notes klasörü güncellenir.
---

# Adil Değer 9 Yöntem (Finzora AI v3.7.2) - v2.0

## Versiyon Geçmişi

**v2.0 (6 Mayıs 2026)** — AMKR ve AMD analizlerinden çıkan iyileştirmeler
- Cost of Equity %15 cap (yüksek beta hisselerde formül abartısı düzeltildi)
- ROE < k_e durumunda Residual Income Model fallback (önceden $9.02 clipping bug'ı vardı)
- CV ≥ %50 kırmızı, ≥ %35 turuncu, ≥ %20 sarı uyarı sistemi
- Forward P/E outlier filtreleme (EPS_FWD/EPS_TTM > 2.5x ise işaret)
- AI mega-cap auto-detection ($300B+ market cap + 1y %100+ getiri + tech/semi)
- AI mega-cap için boğa primi 1.40-1.55x (NVDA, AMD gibi hisselerde)
- Analist konsensüs hedef fiyat entegrasyonu (FMP price-target-consensus)
- Dual-track raporlama: Traditional (TTM bazlı 7 yöntem) vs Forward (FWD bazlı 2 yöntem)
- Otomatik karar matrisi (GÜÇLÜ AL / AL / İZLE / PAHALI / GEÇ)

**v1.0 (6 Mayıs 2026)** — İlk sürüm

## Amaç

Bir ABD hissesi için 9 farklı yöntemle adil değer hesaplar ve 3 piyasa rejimi (Ayı/Normal/Boğa) için ayrı eder değer aralıkları üretir. Mevcut fiyatla karşılaştırır, otomatik karar matrisiyle GİR/İZLE/GEÇ önerisi sunar.

## Tetikleme

Kullanıcı şunları söylediğinde:
- "X hissesini değerle"
- "X için adil değer hesapla"
- "X kaç eder"
- "X fair value"
- "9 yöntem değerleme"

## Kullanım

```bash
python /mnt/skills/user/adil-deger-9-yontem/scripts/adil_deger.py TICKER
python /mnt/skills/user/adil-deger-9-yontem/scripts/adil_deger.py TICKER --json
```

Skill otomatik olarak:
1. FMP API'den tüm gerekli verileri çeker
2. VIX ve SPY 200SMA'dan piyasa rejimi tespit eder
3. Sektör auto-detection + AI mega-cap kontrolü yapar
4. 9 yöntemi 3 senaryoda hesaplar
5. CV uyarı seviyesi belirler
6. Analist konsensüsüyle karşılaştırır
7. Otomatik karar üretir
8. usage_log.csv ve learnings.md'ye kayıt atar

## Yöntemler

### Traditional (TTM Bazlı, 7 Yöntem)
- Net P/E: EPS TTM × hedef P/E
- EV/EBIT: EBIT × hedef → Equity → /share
- EV/EBITDA: EBITDA × hedef → Equity → /share
- EV/Revenue: Revenue × hedef → Equity → /share
- P/FCF: 4 yıl normalize FCF × hedef
- Justified P-B: Gordon büyüme veya Residual Income Model (ROE < k_e ise)
- Graham: sqrt(k × EPS × BVPS), k=18/22.5/28

### Forward (Beklenti Bazlı, 2 Yöntem)
- Forward P/E: EPS 2 yıl forward × hedef
- DCF: 10 yıl FCF projeksiyonu + Terminal Value

## Piyasa Rejimleri

| Rejim | Tespit | Çarpan Düzeltme |
|---|---|---|
| Ayı | VIX > 28 veya SPY < 200SMA -%5 | -%25-35 |
| Normal | VIX 15-22, baseline | %0 |
| Boğa | VIX < 16, SPY > 200SMA +%5 | +%20-30 |

AI Mega-Cap istisnası: Boğa multiplier 1.40-1.55x (semi/tech, $300B+, 1y +%100+)

## CV Uyarı Seviyeleri

| CV | Renk | Anlam |
|---|---|---|
| < %20 | Yeşil | Yöntemler hizalı, güvenilir |
| %20-35 | Sarı | Normal dağılım, kabul edilebilir |
| %35-50 | Turuncu | Yöntemler arası tutarsızlık var |
| ≥ %50 | Kırmızı | KRİTİK: Model güvenilir değil |

## Otomatik Karar Matrisi

| Mevcut Fiyat | Öneri |
|---|---|
| ≤ Ayı medyan | GÜÇLÜ AL |
| ≤ Normal medyan | AL |
| ≤ Normal P75 | İZLE / KÜÇÜK POZİSYON |
| ≤ Boğa medyan | İZLE |
| ≤ Boğa P75 | PAHALI / İZLE |
| ≤ Boğa P75 × 1.20 | ÇOK PAHALI |
| > Boğa P75 × 1.20 | GEÇ / KAÇIN |

## Veri Kaynakları (FMP Stable API)

- `/profile` - Şirket bilgileri
- `/quote` - Anlık fiyat, 50/200 SMA, 52H aralık
- `/income-statement` (annual + quarterly) - Gelir tablosu
- `/cash-flow-statement` (annual + quarterly) - Nakit akışı
- `/balance-sheet-statement` - Bilanço
- `/analyst-estimates` - Forward EPS tahminleri
- `/price-target-consensus` - Analist hedef fiyat (v2 yeni)
- `/quote` (^VIX, SPY) - Piyasa rejimi tespiti

## Justified P-B Çift Yol

```python
if ROE > k_e:
    # Klasik Gordon: P/B = (ROE-g)/(k_e-g)
else:
    # Residual Income Model fallback
    Value = BVPS + sum(RI_t / (1+k_e)^t) + Terminal_RI
```

## Forward Outlier Tespiti

```python
if EPS_FWD_2Y / EPS_TTM > 2.5:
    forward_outlier = True
    # Raporda uyarı ekle
```

## Doğrulanmış Test Vakaları

| Ticker | Sektör | Sonuç | Tarih |
|---|---|---|---|
| AMKR | semicon_osat | GEÇ (boğa medyan +%98 pahalı) | 2026-05-06 |
| AMD | semicon_design (AI mega-cap) | GEÇ Traditional, hafif pahalı Forward | 2026-05-06 |

## Önemli Kurallar (Memory'den)

- Tüm metinler Türkçe (rapor, log, notlar)
- Em dash yok
- Cümleler büyük harfle başlar
- Kaynak: "finzora ai"
- AI kokusu olmayan profesyonel ton
- Hesaplamada FMP "stable" endpoint kullan
- `epsAvg` (estimatedEpsAvg değil)
- `^VIX` ÇALIŞIYOR (VIXY proxy kullanma)
