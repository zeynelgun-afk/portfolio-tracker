
## 🆕 4 Portföy Güncelleyici

### `update_all_portfolios.py`

Tüm 4 portföyü (Dengeli, Agresif, Temettü, Rotasyon) tek seferde günceller.

**Kullanım:**
```bash
# Tüm portföyleri güncelle
python3 scripts/update_all_portfolios.py

# Detaylı çıktı
python3 scripts/update_all_portfolios.py --detailed
```

**Ne yapar:**
- Her portföy için güncel fiyatları çeker
- Pozisyonları günceller
- Kar/zarar hesaplar
- Portföy dosyalarını kaydeder
- Karşılaştırmalı özet rapor üretir

**Çıktı:**
- `data/portfolios/balanced.json` → Güncellenir
- `data/portfolios/aggressive.json` → Güncellenir
- `data/portfolios/dividend.json` → Güncellenir
- `data/portfolios/rotation.json` → Güncellenir
- `data/portfolio_summary.json` → Özet rapor

---

**Son Güncelleme:** 19 Şubat 2026
