# PHASE 10 — Adaptive Multiplier Tuning

> Yazıldı: 17 Mayıs 2026 (Faz 2 sonrası, implementasyon: ~30 gün veri biriktiğinde)
> Önceki: [[PHASE2_SCANNER_CONSOLIDATION]] — Faz 2 + C-serisi (TAMAMLANDI)
> Sonraki: Phase 11 — per-theme tuning (gelecek, opsiyonel)

## TL;DR

Faz 2 sonu kalibratör 4 bayrağa sabit çarpan uyguluyor (`1.20/1.10/0.90/0.75`).
Phase 10'da bu sabit tablo **veri-tabanlı adaptive tablo** ile değiştirilecek.
Çarpanlar `adaptive_suggestions` (C-3'te yazıldı) çıktısından runtime'da okunacak.
Sabit tabloya düşüş **fallback** olarak korunacak.

## 1. Bağlam — Faz 2 nereye geldi

Faz 2 sonunda kalibratör pipeline'ı **tamamen kapalı bir devre**:

```
[Scanner] → [Candidate] → [Calibrator] → [AI Gate / watchlist]
                              ↓
                  [Performance Tracker]
                              ↓ (C-1, C-2, C-3)
                  [Stats raporu — adaptive_suggestions]
                              ↓
                      [Phase 10 — BURADA AÇIK]
```

Açık kalan tek bağlantı: **adaptive_suggestions → calibrator runtime**.

## 2. Phase 10 önkoşulları

Implementasyona başlamadan önce **3 koşul** gerek:

### 2.1 Veri olgunluğu

`scripts/finzora_stats.py --days 30` çıktısında:
- `outcome_status: phase10_ready` ✅
- Tracker `_started_at` ≥ 30 gün önce ✅
- `confidence: high` (≥50 sample) olan en az 1 bayrak ✅

Eğer `medium` confidence ile yetinilecekse: kurallı bir karar ver, dokümanla.

### 2.2 Production etkinleştirme

- `CALIBRATOR_ENABLED=true` (GitHub Actions + Railway env)
- `polymarket_refresh.yml` cron AÇIK (manuel değil, otomatik)
- `fill_calibrator_outcomes.yml` cron çalışıyor (zaten açık)

### 2.3 Tasarım kararları

Şu üç soru cevaplı olmadan implementasyon başlamamalı:
1. Adaptive tablo nasıl saklanır?
2. Güncelleme sıklığı ne olmalı?
3. Hangi confidence eşiği ile öneri uygulanır?

Aşağıda her birine cevap.

## 3. Mimari kararlar

### 3.1 Tablo storage

**Karar**: `data/adaptive_multipliers.json` dosyası — yeni bir state dosyası.

```json
{
  "_version": "v1",
  "_updated_at": "2026-06-17T06:00:00Z",
  "_source": "phase10_adaptive_tuning",
  "multipliers": {
    "pm_confirm":       1.27,
    "pm_confirm_weak":  1.13,
    "pm_conflict_weak": 0.88,
    "pm_conflict":      0.68
  },
  "_metadata": {
    "pm_confirm":       {"hit_rate_pct": 78.5, "sample": 67, "confidence": "high"},
    "pm_confirm_weak":  {"hit_rate_pct": null, "sample": 8, "confidence": "insufficient"},
    "pm_conflict_weak": {"hit_rate_pct": null, "sample": 5, "confidence": "insufficient"},
    "pm_conflict":      {"hit_rate_pct": 82.0, "sample": 52, "confidence": "high"}
  },
  "_fallback_used_for": ["pm_confirm_weak", "pm_conflict_weak"]
}
```

**Neden bu format:**
- `multipliers`: runtime'da calibrator bunu okur, tek-seviye lookup
- `_metadata`: niye bu sayı? Şeffaflık + audit
- `_fallback_used_for`: hangi bayraklarda sabit tablo'ya düşülmüş

**Alternatif** (reddedildi): Calibrator kod içinde sabit + override config. Sebep: dosya bazlı daha şeffaf, git'te izlenir, manuel düzenlenebilir.

### 3.2 Calibrator runtime davranışı

`agent/scanners/calibrator.py:_MULTIPLIER_FLAG_TABLE` artık **fallback**:

```python
# Yeni mantık (Phase 10):
_FALLBACK_MULTIPLIER_FLAG_TABLE = {  # rename — vurgu fallback
    "strong_confirm":  (1.20, "pm_confirm"),
    "weak_confirm":    (1.10, "pm_confirm_weak"),
    "neutral":         (None, None),
    "weak_conflict":   (0.90, "pm_conflict_weak"),
    "strong_conflict": (0.75, "pm_conflict"),
}

_ADAPTIVE_PATH = REPO_ROOT / "data" / "adaptive_multipliers.json"


def _load_adaptive_multipliers() -> dict[str, float]:
    """Adaptive dosyadan {flag: mult} yükle. Yoksa {} → fallback kullanılır."""
    if not _ADAPTIVE_PATH.exists():
        return {}
    try:
        with _ADAPTIVE_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        m = data.get("multipliers", {})
        if not isinstance(m, dict):
            return {}
        # Sadece bilinen bayrakları al, type kontrol
        return {
            flag: float(val) for flag, val in m.items()
            if flag in {"pm_confirm", "pm_confirm_weak",
                        "pm_conflict_weak", "pm_conflict"}
            and isinstance(val, (int, float))
        }
    except Exception:
        return {}


def _resolve_multiplier(category: str) -> tuple[Optional[float], Optional[str]]:
    """Adaptive'i tercih et, yoksa fallback.

    Returns:
        (multiplier, flag) — neutral için (None, None).
    """
    mult, flag = _FALLBACK_MULTIPLIER_FLAG_TABLE[category]
    if mult is None or flag is None:
        return None, None  # neutral

    adaptive = _load_adaptive_multipliers()
    return (adaptive.get(flag, mult), flag)
```

**Performans**: `_load_adaptive_multipliers()` her `calibrate()` çağrısında değil, **sınıf init'inde** veya per-batch okunmalı (cache). Aşağıda Pattern 3.4'te.

### 3.3 Güncelleme cron

**Karar**: Haftalık. Pazartesi UTC 03:00 (TR 06:00, hafta başlamadan önce).

```yaml
# .github/workflows/update_adaptive_multipliers.yml
on:
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * 1'  # Pazartesi UTC 03:00
```

**Neden haftalık değil günlük:**
- Çarpan oscillation'ı önler — bir gün hit %75, ertesi gün %65 → tablo titremesi kötü
- Veri 7 günde anlamlı bir şekilde değişir
- Manuel review için fırsat — Zeynel Pazar raporunda adaptive_suggestions'ı görür, Pazartesi tabloyu update eder

**Alternatif** (reddedildi): Aylık. Çok yavaş — çelişki açıklarsa 3-4 hafta yanlış çarpan uygulamak istemiyoruz.

### 3.4 Güncelleme mantığı

`scripts/update_adaptive_multipliers.py` (yeni):

```
1. query_calibrator_stats(days=30) çağır
2. adaptive_suggestions al
3. Her bayrak için:
   - confidence == "high" → suggested uygula
   - confidence == "medium" + delta < 0.05 → suggested uygula (küçük adım)
   - confidence == "medium" + delta >= 0.05 → fallback kullan (büyük adım için high gerek)
   - confidence == "low" veya "insufficient" → fallback kullan
4. Yeni multipliers dict oluştur, _metadata + _fallback_used_for ekle
5. data/adaptive_multipliers.json'a yaz
6. Telegram DM: özet rapor (hangi bayraklar değişti, delta'lar)
```

**Conservative approach** kasıtlı: high confidence olmadan büyük adım atma. Phase 11'de bu eşik gevşetilebilir.

### 3.5 İlk Phase 10 çalıştırması

İlk çalıştırma özel — `data/adaptive_multipliers.json` henüz yok. Senaryo:

- Tracker'da 30+ gün veri
- ≥1 bayrak high confidence
- Cron Pazartesi tetikleniyor
- Script dosyayı **ilk kez yaratıyor**
- Calibrator sonraki çağrıda dosyayı okuyup adaptive değerleri kullanıyor
- Fallback bayraklar için (insufficient confidence) sabit tablo değerleri

Bu doğal, ekstra "first run" mantığı gerek değil — script idempotent.

## 4. Implementation adımları (Phase 10'da yapılacak)

**Sıra önemli — her adım test'li**:

### Adım 10.1 — Adaptive multiplier loader (calibrator'a)
- `agent/scanners/calibrator.py`'a `_load_adaptive_multipliers()`, `_resolve_multiplier()` ekle
- `_delta_to_multiplier_flag` fonksiyonunu `_resolve_multiplier` kullanacak şekilde refactor et
- Test: dosya yoksa fallback, dosya varsa override, bozuk dosya fallback
- ~10 test, ~50 satır kod

### Adım 10.2 — Updater script
- `scripts/update_adaptive_multipliers.py` yaz
- `_choose_multiplier(suggestion)` helper: confidence eşiğine göre adaptive vs fallback
- `_write_adaptive_table(suggestions)` helper
- Telegram özet DM
- Test: confidence kombinasyonları, dry-run, mevcut tablo yoksa
- ~15 test, ~150 satır kod

### Adım 10.3 — Workflow cron
- `.github/workflows/update_adaptive_multipliers.yml`
- Pazartesi UTC 03:00 + workflow_dispatch
- Tablo değiştiyse otomatik commit
- Manuel dry-run input

### Adım 10.4 — Stats raporu genişletme
- `format_calibrator_section`'a yeni "Aktif Tablo" bölümü
- `data/adaptive_multipliers.json` varsa: hangi bayraklar adaptive, hangileri fallback
- "Son güncelleme: X gün önce" bilgisi

### Adım 10.5 — Geriye dönük test
- Mevcut Faz 2 testlerinin %100'ü hâlâ geçmeli
- 7 günlük test çalıştırma: tablo değişiminin candidate skor dağılımına etkisi anormal mi?

## 5. Test stratejisi

### 5.1 Unit testler (Adım 10.1-10.3 için)

Standart yaklaşım: mock dosya, mock tracker, mock telegram.

```python
def test_calibrator_uses_adaptive_when_available(tmp_path, monkeypatch):
    adaptive_path = tmp_path / "adaptive.json"
    adaptive_path.write_text(json.dumps({
        "multipliers": {"pm_confirm": 1.35},
    }))
    monkeypatch.setattr(calibrator, "_ADAPTIVE_PATH", adaptive_path)

    cal = PolymarketCalibrator()
    candidates = [Candidate(symbol="LMT", score=0.5, ...)]
    cal.calibrate(candidates)

    # pm_confirm match olduysa: multiplier 1.35 (adaptive, fallback 1.20 değil)
    assert candidates[0].calibration_multiplier == 1.35
```

### 5.2 Shadow test (Adım 10.5)

İlk gerçek tablo değişikliğinden ÖNCE: shadow mode 1 hafta.

```python
# Shadow: hem fallback hem adaptive hesapla, ikisini de tracker'a yaz
# (yeni field: applied_multiplier_shadow). Production'da fallback aktif kalır.
# Sonuçlar 1 hafta sonra karşılaştırılır: önemli bir fark var mı?
```

Bu **opsiyonel** — eğer Phase 10 implementasyonu çok sert geçişse shadow test atlanabilir. Ama önerilir.

### 5.3 Smoke testler

```bash
# Adaptive dosyası yok → fallback davranış
rm data/adaptive_multipliers.json
python -m agent.scanners.calibrator  # mevcut testler geçer

# Adaptive dosyası bozuk → fallback davranış
echo "{not json" > data/adaptive_multipliers.json
python -m agent.scanners.calibrator

# Adaptive yarım dolu → eksik bayraklar fallback
echo '{"multipliers": {"pm_confirm": 1.30}}' > data/adaptive_multipliers.json
# pm_confirm 1.30, diğerleri 1.10/0.90/0.75 (fallback)
```

## 6. Risk yönetimi

### 6.1 Risk: yanlış adaptive tablo

**Senaryo**: Hit rate hesaplamasında bug → suggested fazla agresif → kalibratör kötü kararlar.

**Mitigation**:
- Clamp [0.50, 1.50] zaten C-3'te var
- `_fallback_used_for` listesinden hangi bayrakların adaptive olduğunu görürüz
- Acil kapanma: `rm data/adaptive_multipliers.json` → fallback'e döner
- Tracker'da `applied_multiplier` field zaten kayıtlı → backtrack mümkün

### 6.2 Risk: aşırı oscillation

**Senaryo**: Adaptive tablo her hafta delta ≥ 0.05 ile değişiyor → kalibratör tutarsız.

**Mitigation**:
- Conservative confidence eşiği (high tercih, medium küçük delta için)
- Smoothing eklenebilir: `new_mult = 0.7 * adaptive + 0.3 * previous`
- Phase 11'e ertelendi (gerekirse)

### 6.3 Risk: cold start (yetersiz veri)

**Senaryo**: 30 gün geçti ama sadece 12 event birikti. Tüm bayraklar insufficient/low.

**Mitigation**:
- Bu durumda `update_adaptive_multipliers.py` no-op olmalı (dosya yazmaz)
- Telegram DM: "yetersiz veri, Phase 10 ertelendi"
- Zeynel sebebini bilir: scanner çalıştırma sıklığı az, watchlist büyütülmeli?

### 6.4 Risk: Calibrator runtime cache stale

**Senaryo**: Updater Pazartesi tabloyu yazdı ama calibrator hâlâ eski cache'i kullanıyor.

**Mitigation**:
- Calibrator her `calibrate(candidates)` çağrısında dosyayı yeniden okur (her sefer disk I/O — yavaş)
- VEYA: cache + dosya `mtime` kontrolü (akıllı invalidation)
- Performans testi ile karar verilecek. Phase 10 ilk versiyon: **her batch'te bir kez oku**, batch içinde cache'li.

## 7. Rollout planı

Aşamalı 3 hafta:

| Hafta | Adım | Tablo |
|---|---|---|
| 0 | Phase 10 implementasyon + test | data/adaptive_multipliers.json YOK |
| 0 | İlk cron çalıştırması | Dosya yazılır (tüm bayraklar high ise) veya hiç yazılmaz |
| 1 | Shadow test (opsiyonel) | Adaptive hesaplanır ama uygulanmaz |
| 2 | Tablo aktif | Adaptive değerler kullanılır |
| 3 | İlk haftalık update | Tablo otomatik güncellenir |
| 4+ | Phase 10 olgunlaştı | Normal operasyon |

## 8. Phase 11 ipuçları (gelecek)

Phase 10 başardı diyelim. Sonraki olası iyileştirmeler:

- **Per-theme tuning**: `defense + pm_confirm` ile `china_taiwan + pm_confirm` ayrı çarpanlar
- **Per-source tuning**: `thematic.pm_confirm` vs `fair_value.pm_confirm` farklı
- **Time-weighted hit rate**: Son hafta daha ağır basar (recent reliability > old reliability)
- **Outcome threshold tuning**: `_HIT_THRESHOLD` 0 yerine veri-tabanlı (örn. avg market volatility)
- **Confidence intervals**: Hit rate %75 ± %3 vs %75 ± %10 farklı kararlar

Bunlar Phase 10'un başarısına bağlı. İlk önce sabit tabloyu adaptive yapmak yeter.

## 9. Tasarım dışı bırakılanlar

Phase 10'da YAPMIYORUZ:
- ❌ Continuous learning / online updates (haftalık batch yeter)
- ❌ Multi-armed bandit / exploration vs exploitation (formül-tabanlı yeter)
- ❌ Çarpan dışı parametreler (_REFERENCE_HIT_RATE sabit kalır)
- ❌ ML model (regression / gradient boosting). Linear formül zaten yeterli, ML overkill.

Phase 11+'de bunlar gündeme alınabilir.

## 10. Çıktı dosyaları

Phase 10 implementasyonu sonrası eklenecek dosyalar:

```
data/adaptive_multipliers.json          (yeni — state)
scripts/update_adaptive_multipliers.py  (yeni — cron entry)
.github/workflows/update_adaptive_multipliers.yml (yeni — cron)
tests/test_calibrator_adaptive.py       (yeni — runtime testleri)
tests/test_update_adaptive_multipliers.py (yeni — updater testleri)
```

Değişen dosyalar:

```
agent/scanners/calibrator.py — _load_adaptive_multipliers + _resolve_multiplier
agent/reports/stats.py        — "Aktif Tablo" bölümü
```

Tahmini boyut: **+25-30 test, +400 satır kod, 1-2 oturum implementasyon**.

## 11. Karar günlüğü (yapılırken doldurulacak)

```
Tarih    | Karar                                    | Sebep
---------|------------------------------------------|----------------
?? ??    | İlk Phase 10 implementasyon başlangıcı   | Veri yeterli mi?
?? ??    | Confidence eşiği seçimi (high vs medium) | Şu ana kadar gözlem
?? ??    | İlk adaptive tablo değişikliği uygulandı | Δ değerleri
```

Bu tablo Phase 10 yaşar — her önemli karar buraya not edilir.

---

## Hızlı başlangıç (gelecek bir oturum için)

```bash
# 1. Veri olgunluğunu kontrol et
python -m agent.reports.stats --days 30
# Ara: outcome_status: phase10_ready ✓

# 2. Bu dokümana göre yeni branch
git checkout -b feat/phase10-adaptive-multipliers

# 3. Adım 10.1'den başla (calibrator'a loader)

# 4. Her adım sonrası tüm testler geçmeli (mevcut + yeni)
python -m pytest tests/ -q
```
