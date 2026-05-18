---
title: JSON Key Migration — Türkçe → İngilizce
description: data/*.json içindeki Türkçe field adlarının aşamalı İngilizce'ye geçişi
tags:
  - migration
  - refactor
  - data-schema
related:
  - "[[SYSTEM_MAP]]"
version: 1.0 (17 May 2026)
---

# JSON KEY MIGRATION — TÜRKÇE → İNGİLİZCE

> **Amaç**: data/ altındaki JSON dosyalarında kalan Türkçe field adlarını
> aşamalı olarak İngilizce'ye geçir. Konvansiyon: kod = İngilizce.

## TL;DR

```bash
# Mevcut durumu gör
python3 scripts/audit_json_keys.py

# Kapsam: 488 occurrence, 54 benzersiz key, 19 dosya
# Migration: 4 öncelik kategorisi, aşamalı (her seans 1-2 dosya)
```

## 1. Bağlam

userMemories konvansiyonu (May 13 2026):
> English = code (vars/funcs/JSON keys/classes), file/folder/doc names,
> GitHub report artifacts. Turkish = Telegram, chat, commits, reports
> presented to Zeynel, HTML pages/visualizations.

Yani: JSON key'ler İngilizce olmalı. Şu an birkaç eski dosyada Türkçe
kalan key'ler var — migration ile temizlenecek.

## 2. Mevcut durum (17 May 2026)

`scripts/audit_json_keys.py` çıktısı:

| Metrik | Değer |
|---|---|
| Toplam Türkçe key occurrence | 488 |
| Benzersiz key adı | 54 |
| Etkilenen dosya | 19 |
| Migrate edilmez (NLP data dumps) | 2 dosya (tfidf_vectors, sistem_icgoruleri) |

### En sık geçen 10 key

| Key | Sayı | Öneri | Migration karmaşıklığı |
|---|---:|---|---|
| `tarih` | ~100 | `date` | Trivial (sade dönüş) |
| `fiyat` | ~60 | `price` | Trivial |
| `g10_fiyat`, `g5_fiyat` vb. | ~46 | `price_10d`, `price_5d` | Easy |
| `yüksek_hacim` | 20+ | `high_volume` | Easy |
| `dominant_temalar` | 3 | `dominant_themes` | Medium (nested) |
| `öncelikli_alt_dal` | 3 | `priority_subsector` | Medium |
| `önerilen_hisseler` | 3 | `suggested_tickers` | Medium |
| `güç_skoru` | 3 | `strength_score` | Medium |
| `portföy` | 3 | `portfolio` | Hard (genel terim, çakışma riski) |
| `kacınılacak` | 1 | `avoid` | Easy |

## 3. Migration kategorileri

### A) TRIVIAL (1-2 saat per dosya)

Tek bir field adı değişiyor, hem yazan hem okuyan kod tek bir yerde.

**Hedef dosyalar**:
- `data/daily_full_scan.json` (`tarih`)
- `data/daily_scan_aggressive.json` (`tarih`)
- `data/daily_scan_balanced.json` (`tarih`)
- `data/daily_scan_dividend.json` (`tarih`)
- `data/summary.json` (`temettü` portfolio name'i)

Yöntem:
1. `grep -rn "['\"]tarih['\"]" --include="*.py"` ile yazan/okuyan tüm kodu bul
2. String replace (`'tarih'` → `'date'`)
3. JSON dosyasını da güncelle (manuel veya migration script ile)
4. Test çalıştır — tüm 544 test geçmeli

### B) EASY (yarım gün per dosya)

Aynı dosyada birden fazla key değişiyor, ama tek bir yazıcı modül var.

**Hedef dosyalar**:
- `data/backtest_summary.json` (5 key: `g10_fiyat`, `g1_fiyat`, `g20_fiyat`, `g5_fiyat`, `tarih`)
- `data/discovery_signals.json` (`fiyat`, `tarih`)
- `data/premarket_gaps.json` (`gaplar`, `yüksek_hacim` vb.)

### C) MEDIUM (1 gün per dosya)

Nested structure, birden fazla yazıcı/okuyucu.

**Hedef dosyalar**:
- `data/macro_intelligence.json` (`dominant_temalar`, `önerilen_hisseler`,
  `güç_skoru`, `öncelikli_alt_dal`, `kacınılacak`, `portföy`)
- `data/research/index.json` (`analizler`, `bülançö_tarihi`)

### D) HARD (kapsamlı planlama gerek)

Field adı widespread, schema migration script gerek.

**Hedef dosyalar**:
- `data/weekly_pre_check.json` (`sektor_dagilimi` — Türkçe SEKTÖR ADLARI value olarak da var)

Bu dosyada hem **key** (`sektor_dagilimi`) hem **value** (`"Tütün"`, `"Yarı İletken"`) Türkçe. Sadece key migrate etmek yetmez, sözlük gerekir.

## 4. Migration adımları (her dosya için)

### Adım 1 — Kod tarama

```bash
# Hedef key
KEY="tarih"
NEW_KEY="date"

# Yazan/okuyan kodu bul
grep -rn "['\"]$KEY['\"]" --include="*.py" agent/ scripts/ tests/
```

### Adım 2 — Geriye uyumluluk shim (opsiyonel)

Eğer dosya çok sık okunuyorsa, geçici olarak HEM ESKI HEM YENİ key'i destekle:

```python
# Geriye uyumluluk: eski Türkçe key + yeni İngilizce key birlikte okunur
date_value = item.get("date") or item.get("tarih")
```

Bir hafta sonra eski key silindiğinde bu shim de kalkar.

### Adım 3 — Yazan kodu güncelle

```python
# Eski:
output = {"tarih": "2026-05-18", ...}
# Yeni:
output = {"date": "2026-05-18", ...}
```

### Adım 4 — Mevcut JSON dosyasını migrate et

Manuel için küçük:
```bash
sed -i 's/"tarih":/"date":/g' data/daily_full_scan.json
```

Büyük migration için Python script (her dosya için).

### Adım 5 — Test

```bash
python -m pytest tests/ -q
# Tüm 544 test geçmeli
# Eğer JSON şema testleri varsa onlar da geçmeli
```

### Adım 6 — Commit

Her dosya için ayrı commit:
```
refactor(data): tarih → date migration in daily_full_scan.json

- Eski Türkçe key 'tarih' İngilizce 'date'a değiştirildi
- agent/scanners/X.py:N yazıcı kodu güncellendi
- Geriye uyumluluk shim 7 gün boyunca aktif (Y tarihinde silinecek)
- Test: 544 PASS
```

## 5. Önerilen sıralama

Kolaydan zora — her seans 1-2 dosya:

| # | Dosya | Kategori | Tahmini süre |
|---|---|---|---|
| 1 | `summary.json` (`temettü`) | Trivial | 30 dk |
| 2 | `daily_full_scan.json` (`tarih`) | Trivial | 30 dk |
| 3 | `daily_scan_aggressive/balanced/dividend.json` (`tarih`) | Trivial | 1 saat (3 dosya birlikte) |
| 4 | `discovery_signals.json` (`fiyat`, `tarih`) | Easy | 1 saat |
| 5 | `backtest_summary.json` (5 key) | Easy | 2 saat |
| 6 | `premarket_gaps.json` (`gaplar`, `yüksek_hacim`) | Easy | 2 saat |
| 7 | `episodic_memory/trade_index.json` | Easy | 1 saat |
| 8 | `episodic_memory/portfolio_history.json` | Easy | 1 saat |
| 9 | `research/index.json` (`analizler`, `bülançö_tarihi`) | Medium | 3 saat |
| 10 | `macro_intelligence.json` (6 key) | Medium | 4 saat |
| 11 | `weekly_pre_check.json` (sözlük migration) | Hard | 1 gün |

**Toplam tahmini efor**: ~3-4 seans (1-2 hafta).

## 6. Geriye uyumluluk stratejisi

Production'da çalışan kod kırılmasın diye **çift-okuma pattern'i**:

```python
def get_date_field(record: dict) -> str:
    """Hem eski 'tarih' hem yeni 'date' destekle."""
    return record.get("date") or record.get("tarih", "")
```

Migration tamamlanınca (bir hafta gözlem sonrası):
- Yazan kodda eski key kalmadıysa
- Tüm okuyucu yerlerde shim varsa
- Production'da hata yoksa
→ shim'leri sil, tek key destek.

## 7. Test stratejisi

Her migration adımı sonrası:

1. **Tüm mevcut testler geçmeli** — `pytest tests/ -q` → 544 PASS
2. **JSON dosyası okunabiliyor** — `python -c "import json; json.load(open('data/X.json'))"`
3. **Yazan kod test edilebiliyorsa** — yeni unit test yaz, dosya çıktı şemasını doğrula
4. **Production smoke test** (mümkünse) — script'i `--dry-run` modda çalıştır, output doğru mu

## 8. Migration NE DEĞİLDİR

Bu refactor **SADECE field adlarını** değiştirir. Şunları YAPMAZ:
- ❌ Schema redesign (örn. nested struct → flat)
- ❌ Yeni field ekleme
- ❌ Field silme
- ❌ Value type değiştirme (string → int vb.)
- ❌ İş mantığı değişikliği

Eğer schema redesign gerekirse: ayrı bir tasarım dokümanı + ayrı bir migration.

## 9. Hangi key'ler migrate EDİLMEZ

**TF-IDF tokens / NLP data dumps**:
- `data/episodic_memory/tfidf_vectors.json` — Türkçe metin işleme çıktısı, token'lar Türkçe değer olarak doğru
- `data/episodic_memory/sistem_icgoruleri.json` — narrative text dump

**Telegram/Türkçe rapor içerikleri** (eğer JSON'da saklanıyorsa):
- Eğer bir field'ın **değeri** Türkçe metin (kullanıcıya gösterilecek) ise migrate edilmez
- Sadece **key adı** İngilizce'ye geçer

Örnek: `{"telegram_message": "Bugün NVDA yükseldi"}` — key migrate edilebilir (`telegram_message`),
ama value Türkçe kalır.

## 10. İlk migration (örnek)

İlk somut migration için bir küçük dosya seçildi: **`data/summary.json`**.

Tek key: `portfolyolar.temettü` → `portfolios.dividend` (eğer "temettü" portfolio adı ise) veya
`portfolios.divided_portfolio` (eğer "temettü portföyü" kısaltma ise).

Bu migration ayrı bir commit olarak yapılacak — dokümanın 4. ve 5. bölümündeki adımları takip edip
geriye uyumluluk shim'i ekleyerek.

(Bu seansta plan dokümanı + audit script tamamlandı. Migration kendisi sonraki seansta yapılacak.)

## 11. Audit script kullanımı

```bash
# Tüm data/ tara
python3 scripts/audit_json_keys.py

# Tek dosya
python3 scripts/audit_json_keys.py --file data/summary.json

# JSON çıktı (otomasyon için)
python3 scripts/audit_json_keys.py --format json

# CSV çıktı (manuel sözlük doldurma için)
python3 scripts/audit_json_keys.py --format csv > migration_plan.csv
```

CSV çıktısı manuel doldurma için: her satıra önerilen yeni isim yaz.

## 12. Yapılan ve yapılacak

| Tarih | Eylem | Dosya | Commit |
|---|---|---|---|
| 17 May 2026 | Plan + audit script | (bu doküman + scripts/audit_json_keys.py) | `9a56ecd8` |
| 17 May 2026 | İlk migration: daily_scan_* dosyaları | 4 JSON + 1 Python | TBD bu commit |
| ? | summary.json (HARD — re-kategorize edildi) | 19 unique key | TBD |
| ... | ... | ... | ... |

### Migration log

**17 May 2026 — daily_scan_* dosyaları**:
- `scripts/legacy/full_universe_screener.py` yazıcı kod güncellendi (2 yer)
- 4 JSON dosyası migrate edildi:
  - `data/daily_full_scan.json`
  - `data/daily_scan_aggressive.json`
  - `data/daily_scan_balanced.json`
  - `data/daily_scan_dividend.json`
- Key dönüşümleri:
  - `tarih` → `date`
  - `son_guncelleme` → `last_updated`
- Okuyucu kod bulunmadı (sadece scan sonuçları okunuyor, metadata field'lara erişilmiyor) → geriye uyumluluk shim **gerek değil**
- Test: 561 PASS (kırılma yok)

**17 May 2026 — discovery_signals.json**:
- Re-kategorize: EASY → MEDIUM (dosyada 14 unique Türkçe key vardı, sadece 2 değil)
- `scripts/legacy/discovery_engine.py` yazıcı tamamen güncellendi:
  - Top-level (4 key): `tarih→date`, `toplam→total`, `min_skor→min_score`, `adaylar→candidates`
  - Candidate içi (10 key): `sembol→symbol`, `fiyat→price`, `hedef→target`,
    `kalite_skor→quality_score`, `kalite_karar→quality_decision`,
    `carpan→multiplier`, `rejim→regime`, `sektor_fark→sector_diff`,
    `volume_rasyo→volume_ratio`, `sinyaller→signals`
  - Telegram + print render bloklarında da key referansları güncellendi
- `agent/legacy/risk_engine.py` okuyucu — **geriye uyumluluk shim** eklendi:
  - Hem yeni `candidates` hem eski `adaylar` okunur (or fallback)
  - Aday içi field'lar için de or-fallback (`symbol or sembol`, vb.)
  - 1 hafta gözlem sonrası eski key fallback'i kaldırılacak
- Mevcut `data/discovery_signals.json` (42 candidate) migrate edildi
- Test: 561 PASS

### Re-kategorize edilen dosyalar (planda gözüktüğünden farklı)

İlk audit (17 May) sırasında ASCII Türkçe kelimeler eksik tespit edildi — `summary.json` "trivial" gözüküyordu ama gerçekte 19 unique key var. Yeniden değerlendirme:

| Dosya | Eski Kategori | Yeni Kategori | Sebep |
|---|---|---|---|
| `summary.json` | TRIVIAL | **HARD** | 19 unique key, tam dosya migration |
| `daily_full_scan.json` | TRIVIAL | TRIVIAL | ✅ 17 May tamamlandı |
| `daily_scan_*.json` | TRIVIAL | TRIVIAL | ✅ 17 May tamamlandı |
| `backtest_summary.json` | EASY | **MEDIUM** | 5 key'in her biri tracked, yazıcı tek ama okuyucular dağınık |

audit script ASCII Türkçe sözlüğü genişletildi — sonraki audit doğru kapsamı yansıtacak.
