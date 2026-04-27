# Sektör Deep Dive Raporu — Şablon Paketi

Bir sektör/tema için tedarik zincirini katman katman ayıran, hisseleri **değerleme × potansiyel** matrisinde konumlandıran ve 3 portföye (Dengeli / Agresif / Temettü) bağlayan editörel HTML rapor şablonu.

## Dosyalar

| Dosya | Amaç |
|---|---|
| `template.html` | Boş şablon. CSS + JS iskeleti hazır, içerik ve veri `{{...}}` placeholder'larıyla |
| `SCHEMA.md` | Tüm placeholder'ların ve JS veri yapılarının (LAYERS, STOCKS, PORTFOLIOS) açıklaması |
| `ornek_veri_merkezi_zinciri_2026-04-19.html` | 19 Nisan 2026 tarihli veri merkezi zinciri raporu — referans örnek (12 katman, 54 hisse, 3 portföy) |

## Kullanım

1. **Skill dokümantasyonunu oku:** `docs/SEKTOR_DEEP_DIVE_SKILL.md`
2. **Şemayı incele:** `SCHEMA.md` (alanların ne anlama geldiği)
3. **Örneğe bak:** `ornek_veri_merkezi_zinciri_2026-04-19.html`
4. **Template'i kopyala:** `cp template.html ../../reports/research/{TEMA_KOD}_CHAIN_{YYYY-MM-DD}.html`
5. **Placeholder'ları doldur** (30 unique placeholder)
6. **KQ checklist'i uygula** (SCHEMA.md son bölümü)
7. **Browser'da test et, commit + push**

## Hızlı kontrol

```bash
# Placeholder kalmamış mı?
grep -o "{{[A-Z_]*}}" reports/research/{DOSYAN}.html

# JS syntax doğru mu?
python3 -c "
import re
with open('reports/research/{DOSYAN}.html') as f:
    js = re.search(r'<script>(.*?)</script>', f.read(), re.DOTALL).group(1)
print('braces dengeli:', js.count('{') == js.count('}'))
print('brackets dengeli:', js.count('[') == js.count(']'))
"
```
