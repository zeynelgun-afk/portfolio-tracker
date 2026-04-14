# Adil Değer Hesaplayıcı — Kullanım Kılavuzu

Pine Script v3.5.2'nin Python uyarlaması. FMP API ile gerçek zamanlı veri çeker.

## Temel Kullanım

```bash
python3 scripts/adil_deger_calculator.py AMD
```

## PE Modları

| Mod | Açıklama | Örnek |
|-----|----------|-------|
| `rate` | 10Y hazine faizine dayalı F/K (100/faiz) | `--pe-modu rate` |
| `average` | TTM P/E, max 50x ile sınırlı | `--pe-modu average` |
| `manuel` | Kullanıcı tanımlı F/K | `--pe-modu manuel --manuel-pe 25` |

## EV Çarpan Örnekleri (Sektöre Göre)

| Sektör | EV/EBIT | EV/EBITDA | EV/Ciro |
|--------|---------|-----------|---------|
| Teknoloji/Yarı iletken | 30-40x | 35-45x | 8-12x |
| Sanayi | 15-20x | 12-18x | 2-4x |
| Enerji | 10-15x | 8-12x | 1-3x |
| Sağlık | 18-25x | 15-20x | 3-6x |
| Genel | 15x | 20x | 3x (varsayılan) |

## Örnekler

```bash
# AMD — yarı iletken çarpanlarıyla
python3 scripts/adil_deger_calculator.py AMD \
  --pe-modu average --ev-ebit 35 --ev-ebitda 40 --ev-rev 10

# DUK (Dengeli portföyündeki kamu hizmeti)
python3 scripts/adil_deger_calculator.py DUK \
  --pe-modu rate --ev-ebit 14 --ev-ebitda 12 --ev-rev 2

# NVDA karşılaştırması
python3 scripts/adil_deger_calculator.py NVDA \
  --pe-modu average --ev-ebit 40 --ev-ebitda 50 --ev-rev 15
```

## 10 Değerleme Metodu

1. **Net Kazanç P/E** — TTM EPS × seçilen F/K
2. **ROE Bazlı** — ROE × Defter Değeri × F/K
3. **EV/EBIT** — Hedef EV/EBIT × TTM EBIT → hisse başı
4. **EV/EBITDA** — Hedef EV/EBITDA × TTM EBITDA → hisse başı
5. **EV/Ciro** — Hedef EV/Ciro × TTM Ciro → hisse başı
6. **Forward P/E** — Tahmini EPS (TTM + büyüme) × F/K
7. **Forward P/S** — Tahmini Ciro × P/S
8. **P/SNA (P/FCF)** — TTM FCF/Hisse × hedef çarpan
9. **Graham Sayısı** — √(22.5 × EPS × Defter Değeri)
10. **DCF** — 5 yıllık İndirgenmiş Nakit Akışı

Sonuç, sektöre özgü ağırlıklarla birleştirilir (tech, energy, financial vb.).

## Güven Skoru

Metotlar arasındaki varyasyon katsayısına (CV) dayanır.
- **60+** → Metotlar yakınsıyor, güvenilir tahmin
- **40-60** → Orta güven, ek araştırma önerilir
- **<40** → Metotlar ıraksıyor (büyüme hissesi veya kriz senaryosu)
