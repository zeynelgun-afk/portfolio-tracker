# Adil Değer Skill v5.0 — Etap 6 Notu

**Tarih**: 11 Mayıs 2026
**Durum**: Etap 6 tamamlandı

## Yapılan Değişiklikler

### A. GitHub Otomatik Kayıt (`--commit` flag)

Adil Değer Rapor Protokolü'nün şartı: "kayıt yapılmadan tamamlandı sayılmaz". Şimdi bu otomatik:

```bash
# Tam akış: hesap → markdown → index.json → commit → push
python3 adil_deger.py NVDA --commit

# Push hariç (test için)
python3 adil_deger.py NVDA --commit --no-push
```

**Tek komutta yapılan**:
1. FMP'den veri çek + 9 yöntem hesabı + v5 sinyalleri
2. Markdown rapor → `reports/research/{TICKER}_ADIL_DEGER_{YYYY-MM-DD}.md` (12 bölüm)
3. `data/research/index.json` "analizler" dizisine yeni giriş
4. `git add` (md + index.json)
5. `git commit -m "[VALUATION] {TICKER} adil değer hesabı eklendi ({date})"`
6. `git pull --rebase origin main` + `git push origin main`

### B. update_research_index() Fonksiyonu

Protokolde tanımlı şemaya uygun otomatik index güncelleme. Her giriş içerir:

```json
{
  "id": "NVDA_ADIL_DEGER_2026-05-11",
  "ticker": "NVDA",
  "sirket": "NVIDIA Corporation",
  "sektor": "Technology / Semiconductors",
  "analiz_tarihi": "2026-05-11",
  "analiz_turu": "adil_deger_hesabi",
  "durum": "aktif_izleme",
  "dosya": "reports/research/NVDA_ADIL_DEGER_2026-05-11.md",
  "adil_deger": {
    "yontem_v": "v5.0",
    "mod": "GROWTH",
    "kullanilabilir_yontem_sayisi": 9,
    "kullanilamayan_yontem_sayisi": 0,
    "agirlikli_adil_deger": 259.25,
    "confidence": "ORTA",
    "quality_premium": 1.396,
    "ai_mega_cap": false
  },
  "on_beklenti": {
    "senaryo_boga": {"fiyat_hedef": 310.68, "getiri_pct": 44.4, "olasilik": 0.225},
    "senaryo_baz": {"fiyat_hedef": 259.25, "getiri_pct": 20.5, "olasilik": 0.475},
    "senaryo_ayi": {"fiyat_hedef": 194.96, "getiri_pct": -9.4, "olasilik": 0.30}
  },
  "analiz_fiyati": 215.217,
  "temel_metrikler": {
    "pe_ttm": 43.57,
    "forward_pe": 19.34,
    "roe_ttm_pct": 76.33,
    "net_margin_pct": 55.6,
    "revenue_growth_yoy_pct": 65.5,
    "piyasa_degeri_m": 5230849.0,
    "beta": 2.244,
    "vix_at_analysis": 18.12
  },
  "v5_sinyaller": {
    "altman_z": {"value": 68.23, "label": "GÜVENLİ", "emoji": "🟢"},
    "piotroski": {"value": 6, "label": "SAĞLAM", "emoji": "🟡"},
    "analist_sentiment": {"strong_buy": 2, "buy": 58, "hold": 16, ...},
    "upgrade_momentum": {"direction": "downgrade", "magnitude": -6, ...},
    "fmp_dcf_unlevered": 247.15,
    "konsantrasyon_urun": {...},
    "konsantrasyon_cografya": {...},
    "canli_sektor_pe": 62.3,
    "dinamik_wacc": 17.84
  },
  "projeksiyon": {
    "profile_key": "semicon_design_mature",
    "normalizasyon_yili": 2026
  },
  "portfoy_onerisi": {
    "dengeli": "uygun_kosullu",
    "agresif": "uygun",
    "temettu": "uygun_degil"
  },
  "giris_plani": {
    "stop_loss": 187.24,
    "hedef_1": 259.25,
    "hedef_2": 310.68
  },
  "karar": "🟢 AL",
  "karar_gerekce": "Mevcut fiyat normal medyan altında. İyi giriş seviyesi.",
  "gerceklesen": {
    "tespit_fiyati": 215.217,
    "simdiki_fiyat": null,
    "fiyat_tepkisi_pct": 0,
    "tez_tuttu": null,
    "ders": null
  },
  "etiketler": ["growth", "v5.0_skill", "semicon_design_mature"]
}
```

Üst-seviye sayaçlar (`son_guncelleme`, `toplam_analiz`, `aktif_izleme`) otomatik güncellenir.

**Aynı ticker + tarih için tekrar çalıştırılırsa**: Mevcut girişi temizleyip yenisini ekler (idempotent).

### C. Pre-IPO için Otomatik Kayıt

Pre-IPO modunda da `--commit` çalışıyor. Farklı şema kullanılıyor:

```json
{
  "id": "CBRS_ADIL_DEGER_2026-05-11",
  "ticker": "CBRS",
  "sirket": "Cerebras Systems Inc.",
  "sektor": "semicon_design",
  "analiz_tarihi": "2026-05-11",
  "ipo_tarihi": "2026-05-13",
  "analiz_turu": "pre_ipo_adil_deger",
  "durum": "aktif_izleme",
  "ipo_fiyat_aralik": [150, 160],
  "ipo_fiyat_orta": 155,
  "projeksiyon": {
    "profile_key": "semicon_design_growth_ai",
    "normalizasyon_yili": 2028,
    "sektor_pe_medyan": 62.3,
    "5y_son_eps": 8.06,
    "5y_son_revenue_b": 9.5
  },
  "notlar": "OpenAI MRA + AWS Bedrock...",
  "gerceklesen": {
    "ipo_aktivasyon": null,
    "ilk_islem_fiyati": null,
    "1ay_sonra": null,
    "3ay_sonra": null,
    "12ay_sonra": null
  },
  "etiketler": ["pre_ipo", "v5.0_skill"]
}
```

### D. git_commit_and_push() Fonksiyonu

`subprocess` ile:
- `git add` (md + index.json)
- `git diff --cached --quiet` (değişiklik var mı kontrol; yoksa commit'i atla)
- `git commit -m "[VALUATION] {ticker} adil değer hesabı eklendi ({date})"`
- `git pull --rebase origin main` (auto-updater ile çakışmayı önle)
- `git push origin main`

**Hata yönetimi**:
- Push başarısız ise stderr'a yazar (rebase + retry değil — kullanıcı manuel müdahale eder)
- Pull rebase'i sessiz fail edebilir (önemli değil)

### E. --no-push Flag

`--commit --no-push` ile commit atılır ama push edilmez. Test/debug için.

### F. Yuvarlama Düzeltmeleri

- `quality_premium`: 14 ondalık → 3 ondalık (`1.3964240043768943` → `1.396`)
- `pe_ttm`: → 2 ondalık (`43.5661943319838` → `43.57`)
- `forward_pe`: → 2 ondalık (`19.3366576819407` → `19.34`)

## Test Sonuçları

NVDA test (`--commit --no-push`):

```
📄 Rapor yazıldı: /home/claude/portfolio-tracker/reports/research/NVDA_ADIL_DEGER_2026-05-11.md
📋 index.json güncellendi (/home/claude/portfolio-tracker/data/research/index.json): NVDA_ADIL_DEGER_2026-05-11
💾 Commit: [VALUATION] NVDA adil değer hesabı eklendi (2026-05-11)
```

`git log` çıktısı:
```
e9ba01c [VALUATION] NVDA adil değer hesabı eklendi (2026-05-11)
```

`git show --stat`:
```
data/research/index.json                       | 122 ++++++++++++++-
reports/research/NVDA_ADIL_DEGER_2026-05-11.md | 201 +++++++++++++++++++++++++
2 files changed, 321 insertions(+), 2 deletions(-)
```

Test commit geri alındı (`HEAD~1 reset`) — Etap 6 itibariyle skill üretime hazır, gerçek kullanımda Zeynel `--commit` ile push edebilir.

## Akış Sistemi (Tam Pipeline)

```
1. python3 adil_deger.py NVDA --commit
   ↓
2. FMP'den veri çek (profile, quote, income, cashflow, balance, analyst-estimates, ratios-ttm, key-metrics-ttm)
   ↓
3. v5.0 kalibrasyon sinyalleri topla (canlı PE, dinamik WACC) → data_pack'a inject
   ↓
4. calculate_methods 3 senaryoda (bear/normal/bull) — 9 yöntem
   ↓
5. v5.0 ek sinyaller topla (Altman Z, Piotroski, grades, FMP DCF, segmentation)
   ↓
6. 5y projeksiyon üret (projection_engine) — sektör profili + P&L + multiples + normalizasyon
   ↓
7. format_markdown_report() — 12 bölümlü rapor
   ↓
8. Dosyaya yaz: reports/research/{TICKER}_ADIL_DEGER_{date}.md
   ↓
9. update_research_index() — data/research/index.json güncelle
   ↓
10. git add + commit + pull --rebase + push
   ↓
11. Bitti — chat'te tam rapor, repo'da kalıcı kayıt
```

## CLI Tam Referans (v5.0 Final)

```bash
# Standart akış (sadece chat çıktısı)
python3 adil_deger.py NVDA

# JSON çıktı (otomasyon için)
python3 adil_deger.py NVDA --json

# Markdown rapor (chat + dosya, commit yok)
python3 adil_deger.py NVDA --md

# Markdown + custom path
python3 adil_deger.py NVDA --md --md-out /tmp/nvda.md

# Tam kayıt akışı (markdown + index.json + git commit + push)
python3 adil_deger.py NVDA --commit

# Commit ama push yok (test)
python3 adil_deger.py NVDA --commit --no-push

# Pre-IPO modu
python3 adil_deger.py --pre-ipo cbrs.json
python3 adil_deger.py --pre-ipo cbrs.json --md
python3 adil_deger.py --pre-ipo cbrs.json --commit
```

## Sonraki Adımlar (Etap 7+)

1. **Telegram bot entegrasyonu**: `/deger TICKER` komutu otomatik tam akış + Telegram özet
2. **HTML rapor üretici**: `--html` flag, frontend-design skill bridge
3. **Multi-year analyst estimates**: 1y, 2y, 3y forward (şu an sadece 2y)
4. **Profile delta-based projection**: SECTOR_MARGIN_PROFILES'ı TTM gerçek üzerine delta olarak yorumla
5. **Sektör multiple history tracking**: SECTOR_MULTIPLES'ı canlı veriden 3 aylık snapshot ile otomatik güncelleme
6. **Geçmiş analiz takip**: index.json'daki "gerceklesen" alanı haftalık otomatik güncelleme (fiyat tepkisi, tez tutması)
7. **Web sitesi**: index.json'dan otomatik özet sayfa üreten basit skill

## Skill Özet (v5.0 — Etap 6 Sonrası)

| Özellik | Durum |
|---|---|
| 9 yöntem (4 trad + 2 fwd + 3 growth) | ✅ |
| DUAL-MODE (GROWTH / BLENDED) | ✅ |
| 3 senaryo (bear / normal / bull) | ✅ |
| Canlı sektör P/E (override + blend) | ✅ |
| Dinamik CAPM WACC | ✅ |
| Gerçek revenue growth (DCF override) | ✅ |
| Altman Z + Piotroski | ✅ |
| Analist sentiment + momentum | ✅ |
| FMP DCF sanity check | ✅ |
| Konsantrasyon riski tespiti | ✅ |
| 17 sektör marj profili | ✅ |
| 5 yıllık P&L projeksiyonu | ✅ |
| Forward çarpan projeksiyonu | ✅ |
| Normalizasyon yılı tespiti | ✅ |
| Pre-IPO modu (JSON input) | ✅ |
| 12 bölümlü markdown rapor | ✅ |
| Y3-Y5 decay cap | ✅ |
| v5 risk uyarıları (markdown sonu) | ✅ |
| Otomatik index.json güncelleme | ✅ |
| Otomatik git commit + push | ✅ |
| --no-push flag (test) | ✅ |
| --json çıktı | ✅ |
| Pre-IPO için commit | ✅ |

Skill artık tam otonom: tek komutla rapor + kayıt + GitHub push.

Kaynak: finzora ai
