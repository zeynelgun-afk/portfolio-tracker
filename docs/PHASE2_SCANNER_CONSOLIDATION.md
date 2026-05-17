---
title: Faz 2 — Scanner Konsolidasyonu ve Polymarket Kalibratörü
description: 4 mevcut scanner'ı BaseScanner paketine taşıma + Polymarket kalibratör katmanı tasarım kararları.
tags:
  - architecture
  - scanners
  - polymarket
  - refactor
  - phase-2
related:
  - "[[SYSTEM_MAP]]"
  - "[[PREDICTION_MARKETS_GUIDE]]"
  - "[[OBSERVABILITY]]"
  - "[[DECISION_FRAMEWORK]]"
updated: 2026-05-17
status: draft (kararlar netleşti, kod yazımı bekliyor)
---

# FAZ 2 — SCANNER KONSOLİDASYONU + POLYMARKET KALİBRATÖRÜ

> **Durum:** Tasarım kararları kesinleşti — kod yazımı sonraki turlarda.
> **Bağlam:** Faz 1 (Reports konsolidasyonu) `a3156ab5` ile tamamlandı. Bu doküman Faz 2'nin navigasyon haritası — sonraki turlarda hangi karar verildiğini yeniden tartışmamak için referans.
> **Faz 3 ön şartı:** Phase 10 (adaptive learning) bu paketin üstüne inşa edilecek.

---

## 1. AMAÇ

İki paralel hedef:

1. **Konsolidasyon:** Mevcut 4 scanner (`thematic_discovery.py`, `fair_value_panel.py`, `news_radar.py`, `analist_takip/monitor.py`) farklı yerlerde, farklı imzalarla yaşıyor. Aralarında ortak `Candidate` interface'i yok. Yeni scanner eklemek (Polymarket) için önce bu dağınıklığı temizlemek gerek.

2. **Polymarket entegrasyonu:** Mevcut `PREDICTION_MARKETS_GUIDE.md` manuel okuma rutini olarak yaşıyor (Kalshi Fed odds, Polymarket Iran/tarife). Bunu otomatize edip diğer scanner çıktılarını **doğrulayan/çelişki bayrağı koyan** bir kalibratör katmanına dönüştür.

---

## 2. KARARLAR (Özet Tablo)

Bu kararlar 17 May 2026 brainstorm turlarında netleşti, referans için burada tek bakışta:

| Karar | Seçim | Gerekçe |
|---|---|---|
| Polymarket rolü | **Kalibratör** (üretici değil) | Veri tipi olay olasılığı, ticker değil; mevcut "supplement not replace" disiplini |
| Mimari yer | **Pozisyon #2 + #3** (gate sonrası + watchlist sağlık) | İzlenebilir, deterministik; LLM yorumuna ikinci yorum sokmaz |
| Veto hakkı | **YOK** — çarpan + bayrak | Polymarket %67 güvenirlik, scanner sinyalini iptal etme yetkisi riskli |
| Çarpan aralığı | **0.75 — 1.20** | Tam çelişki ×0.75, tam doğrulama ×1.20; başlangıç tahmini, 30g sonra tune |
| Mapping yöntemi | **Hibrit** (statik tablo + LLM köprüsü + insan onayı) | Hız + denetlenebilirlik + yeni tema esnekliği |
| v1 whitelist | **Fed, China-Taiwan, Iran, Tariff, Recession** | Likit + portföye anlamlı + mapping güvenirliği yüksek |
| Observability | **Aynı events.jsonl** (`type: "polymarket_call"`) | Tek stream, FMP pattern'iyle simetrik |
| Weekly Pulse | **Otomatize**, `agent/reports/weekly.py` parçası | Manuel rutin = unutma riski; standart format |
| Tracker zamanlama | **Faz 2 ilk gün** | 30g veri olmadan çarpan tuning körlemedir |
| Cache TTL | **1 saat** | Marketler saatlik değişir, swing horizon günlük |
| Fetch sıklığı | **3/gün** (09:00 / 12:30 / 23:00) | Mevcut scanner schedule'ına senkron |

---

## 3. YAPI HARİTASI

```
agent/
├── scanners/                            # YENİ paket
│   ├── __init__.py
│   ├── base.py                          # BaseScanner ABC + Candidate dataclass
│   ├── thematic.py                      # ← scripts/thematic_discovery.py
│   ├── fair_value.py                    # ← scripts/fair_value_panel.py
│   ├── news.py                          # ← scripts/news_radar.py
│   ├── analyst_revisions.py             # ← agent/legacy/analist_takip/monitor.py
│   └── calibrator.py                    # YENİ — Polymarket kalibratör
│
├── polymarket.py                        # YENİ — Gamma API client (FMP pattern)
│
└── reports/
    └── weekly.py                        # Mevcut, "Prediction Markets Pulse" bölümü eklenir

data/
├── polymarket_themes.json               # YENİ — whitelist tablosu (insan-onaylı)
├── polymarket_cache.json                # YENİ — 1h TTL market snapshot
├── polymarket_calibrator_performance.json  # YENİ — kalibratör hit rate tracker
└── watchlist.json                       # Mevcut, kalibratör bayrakları metadata olarak eklenir

scripts/
├── thematic_discovery.py                # → SHIM (Faz 2)
├── fair_value_panel.py                  # → SHIM (Faz 2)
└── news_radar.py                        # → SHIM (Faz 2)

agent/legacy/analist_takip/monitor.py    # → SHIM, agent/scanners/analyst_revisions.py'ye yönlendirir
```

**Faz 1 disiplini korunuyor:** Eski path'ler `runpy.run_path` shim'leriyle çalışmaya devam eder. Workflow'lar yeni path'i kullanır.

---

## 4. BaseScanner INTERFACE

```python
# agent/scanners/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Candidate:
    """Scanner çıktısı — AI Gate'in tükettiği standart birim."""
    symbol: str
    score: float                          # 0.0 - 1.0 ham güven
    reason: str                           # Türkçe insan-okur açıklama
    source: str                           # 'thematic' | 'fair_value' | 'news' | 'analyst_revisions'
    metadata: dict = field(default_factory=dict)

    # Kalibratör tarafından doldurulur (Faz 2):
    calibration_multiplier: float = 1.0   # 0.75 - 1.20
    calibration_flags: list[str] = field(default_factory=list)  # ['pm_confirm', 'pm_conflict_weak'] vb.

    @property
    def calibrated_score(self) -> float:
        return min(1.0, self.score * self.calibration_multiplier)


class BaseScanner(ABC):
    """4 mevcut scanner + ileride eklenecekler için ortak interface."""

    name: str  # alt sınıf tanımlar

    @abstractmethod
    def scan(self) -> list[Candidate]:
        """Ticker adayları üret. Cron veya manuel tetikleme."""
        ...

    def health_check(self) -> dict:
        """API kotaları, son başarılı çalışma, throttle durumu. Opsiyonel override."""
        return {"name": self.name, "ok": True}
```

**Önemli:** Kalibratör `BaseScanner`'dan miras almaz. O ayrı bir kategori — `scan()` değil `calibrate(candidates) → candidates` imzasıyla çalışır. Aynı pakette duruyor ama farklı rol.

---

## 5. MEVCUT 4 SCANNER — MİGRASYON PLANI

Her biri için aynı pattern:

1. Mevcut dosyadaki ana mantığı bir sınıf altına topla (örn. `ThematicDiscoveryScanner(BaseScanner)`)
2. `scan() → list[Candidate]` metodu, mevcut çıktıyı `Candidate` formatına dönüştürür
3. Eski CLI entry-point'i (`if __name__ == "__main__":`) yeni dosyada korunur — geriye dönük uyumluluk
4. Eski path'te shim bırakılır
5. Workflow YAML'ları yeni path'e güncellenir

### Scanner-spesifik notlar

| Scanner | Karmaşıklık | Dikkat noktaları |
|---|---|---|
| `thematic_discovery.py` → `agent/scanners/thematic.py` | Orta | LLM (Kimi via OpenRouter) bağımlılığı; `themes.json` CRUD'ı agent/themes modülüne ait, taşıma — sadece sinyal üretimi |
| `fair_value_panel.py` → `agent/scanners/fair_value.py` | Orta-yüksek | `update_watchlist_fair_values()` yan etki var; bunu `scan()`'in dışına çıkar, ayrı bir public method olarak kalsın |
| `news_radar.py` → `agent/scanners/news.py` | Yüksek | GitHub API çağrıları (`gh_put_file`) — bunlar scanner sorumluluğu değil, ayrı util'e çıkar; LLM analizi Claude tarafında, dikkat |
| `analist_takip/monitor.py` → `agent/scanners/analyst_revisions.py` | Yüksek | Alt-sistem (8 dosya), sadece `monitor.py` taşınıyor; diğerleri (`revision_fetcher`, `signal_analyzer`, vs.) `agent/legacy/analist_takip/` altında kalıyor şimdilik — Faz 4'te düşünülür |

**`analist_takip` neden tam taşınmıyor?** 8 dosyalık entegre alt-sistem. Şu an çalışıyor. Tam migrasyon kapsam patlamasıdır. `monitor.py` BaseScanner adaptörü olarak çalışır, içte hâlâ legacy modülleri çağırır. Geride kalan dosyaların migrasyonu Faz 4 (Position Manager + Trade Execution konsolidasyonu) ile birlikte değerlendirilir.

---

## 6. POLYMARKET MODÜLÜ — `agent/polymarket.py`

`agent/fmp.py` ile aynı pattern:

```python
# agent/polymarket.py — temel iskele

BASE_URL = "https://gamma-api.polymarket.com"
THROTTLE_MS = 100  # konservatif, public API
USER_AGENT = "Finzora AI Research zeynelgun@finzora.example.com"

def fetch_markets(slugs: list[str] = None, active_only: bool = True) -> list[dict]:
    """Gamma API /markets endpoint. Whitelist slug'larıyla filtrele."""
    ...

def fetch_market_history(market_id: str, lookback_hours: int = 24) -> list[dict]:
    """Olasılık delta'sı hesaplamak için tarihsel veri."""
    ...

def compute_delta(market: dict, lookback_hours: int = 24) -> float:
    """Son N saatte olasılık değişimi (yüzde puan)."""
    ...

def is_liquid(market: dict, min_volume_usd: float = 100_000) -> bool:
    """Likidite filtresi — manipulation guard."""
    ...
```

Her çağrı `events.jsonl`'a `type: "polymarket_call"` etiketiyle yazılır (FMP pattern). `agent/reports/stats.py` genişletilerek Polymarket istatistiği eklenir.

**Önemli teknik notlar:**

- Gamma API public, auth gerekmez (read-only)
- CLOB API (`clob.polymarket.com`) emir defteri için, biz kullanmıyoruz
- Rate limit belirsiz; 100ms throttle konservatif
- Bazı marketlerin `outcomes` alanı binary değil multi (3+ choice); şimdilik sadece binary destekle (`Yes/No`)
- Market kapanmış (`closed: true`) ama henüz `resolved` değilse veri kullanılabilir; resolved olduktan sonra atla

---

## 7. WHITELIST İLK SEED (v1)

`data/polymarket_themes.json` — başlangıç tablosu. **5 tema**, sıralama portföy alakası önceliğine göre:

```json
{
  "_version": "v1",
  "_updated": "2026-05-17",
  "_note": "v1 seed — yeni tema eklemek için ai_orchestrator LLM köprüsü insan onayı ister",
  "themes": {
    "fed_rate_cut": {
      "label": "Fed faiz indirimi",
      "polymarket_slugs": ["fed-rate-decision-june-2026", "fed-rate-cut-by-q3-2026"],
      "min_volume_usd": 1000000,
      "positive_tickers": ["IWM", "TLT", "VNQ", "XLRE", "XLU"],
      "negative_tickers": ["XLF", "USD", "KRE"],
      "confidence": 0.85,
      "applies_to_themes": ["rate-sensitive", "small-cap", "reits"]
    },
    "china_taiwan_tension": {
      "label": "Çin-Tayvan gerilimi",
      "polymarket_slugs": ["taiwan-invasion-2026", "china-taiwan-blockade-2026"],
      "min_volume_usd": 500000,
      "positive_tickers": ["LMT", "RTX", "NOC", "ITA"],
      "negative_tickers": ["TSM", "ASML", "NVDA", "AAPL", "AMAT", "LRCX", "KLAC"],
      "confidence": 0.90,
      "applies_to_themes": ["ai-supply-chain", "semi-equipment", "semi-foundry"],
      "_note": "Portföyün omurgası — yüksek dikkat"
    },
    "iran_escalation": {
      "label": "İran/Orta Doğu eskalasyonu",
      "polymarket_slugs": ["iran-israel-strike-2026", "iran-nuclear-escalation"],
      "min_volume_usd": 500000,
      "positive_tickers": ["XLE", "OIH", "LMT", "RTX", "XOP"],
      "negative_tickers": ["XAL", "LUV", "DAL", "UAL"],
      "confidence": 0.85,
      "applies_to_themes": ["energy", "defense"]
    },
    "trump_tariff_action": {
      "label": "Trump tarife kararı",
      "polymarket_slugs": ["trump-tariff-china-2026", "tariff-mexico-2026"],
      "min_volume_usd": 500000,
      "positive_tickers": ["X", "NUE", "STLD"],
      "negative_tickers": ["AAPL", "NKE", "WMT", "TGT", "BBY", "TSLA"],
      "confidence": 0.70,
      "applies_to_themes": ["import-heavy-retail", "semi-import"],
      "_note": "Mapping güvenirliği orta — etki geniş, sektör seçimi kaba"
    },
    "us_recession_2026": {
      "label": "ABD resesyon 2026",
      "polymarket_slugs": ["us-recession-2026", "nber-recession-2026"],
      "min_volume_usd": 1000000,
      "positive_tickers": ["TLT", "GLD", "XLP", "XLU"],
      "negative_tickers": ["XLY", "XLI", "IYT", "KRE"],
      "confidence": 0.75,
      "applies_to_themes": ["defensive", "cyclical"]
    }
  }
}
```

**Slug isimleri tahmini** — Polymarket'ta gerçek market açıldıkça `agent/polymarket.py`'nin `fetch_markets()` çağrısı ile listelenir, doğru slug'lar tabloya işlenir. Bu seed sadece yapı örneği.

---

## 8. KALİBRATÖR AKIŞI

### Pozisyon #2 — Gate sonrası kalibrasyon

```
Scanner.scan() → [Candidate(score=0.7, source='thematic')]
                              ↓
              AI Gate (LLM bayrağı: AL/SAT/BEKLE)
                              ↓
                  Calibrator.calibrate()  ← Polymarket cache
                              ↓
              [Candidate(score=0.7, calibration_multiplier=1.15,
                         calibration_flags=['pm_confirm'])]
                              ↓
              Watchlist.add() ← kalibrasyon metadata dahil
```

### Eşleştirme mantığı

Kalibratör her Candidate için:

1. Candidate'in `metadata` ve `reason` alanlarındaki tema/ticker bilgisini çıkar
2. `polymarket_themes.json` whitelist'inde eşleşme ara (ticker veya tema bazlı)
3. Eşleşme bulunursa, ilgili Polymarket market(ler)inin son 24h delta'sını al
4. Yön karşılaştır:
   - Candidate "AL" yönlü + market olumlu yönde hareket etti → **doğrulama**
   - Candidate "AL" yönlü + market olumsuz yönde hareket etti → **çelişki**
5. Delta büyüklüğüne göre çarpan ve bayrak ata:

| Delta (24h) | Yön | Çarpan | Bayrak |
|---|---|---|---|
| > +%10 | Aynı | 1.20 | `pm_confirm` |
| %3 — +%10 | Aynı | 1.10 | `pm_confirm_weak` |
| —%3 — +%3 | — | 1.00 | (bayrak yok) |
| —%10 — —%3 | Zıt | 0.90 | `pm_conflict_weak` |
| < —%10 | Zıt | 0.75 | `pm_conflict` |

### Pozisyon #3 — Watchlist sağlık taraması

Günlük cron (örn. 23:00, mevcut scanner'lardan sonra):
- `watchlist.json` içindeki tüm ticker'lar için Polymarket eşleşmesi var mı kontrol et
- Eşleşme varsa ve son 24h'te `pm_conflict` veya `pm_conflict_weak` çıktıysa Zeynel DM'ine uyarı:
  > "⚠️ TSM watchlist'inde. China-Taiwan tension market 24h içinde %42 → %58 (+%16). Pozisyon tezi gözden geçirilsin."

---

## 9. VERİ FORMATLARI

### `data/polymarket_cache.json`

```json
{
  "_fetched_at": "2026-05-17T15:30:00Z",
  "_ttl_seconds": 3600,
  "markets": {
    "fed-rate-decision-june-2026": {
      "id": "0x123abc",
      "question": "Will the Fed cut rates at the June 2026 FOMC?",
      "current_probability": 0.72,
      "probability_24h_ago": 0.65,
      "delta_24h": 0.07,
      "volume_usd": 4250000,
      "is_liquid": true,
      "outcomes": {"Yes": 0.72, "No": 0.28},
      "end_date": "2026-06-12T18:00:00Z"
    }
  }
}
```

### `data/polymarket_calibrator_performance.json`

```json
{
  "_version": "v1",
  "_started_at": "2026-05-17T00:00:00Z",
  "events": [
    {
      "id": "cal_evt_001",
      "ts": "2026-05-17T16:00:00Z",
      "candidate_symbol": "TSM",
      "candidate_source": "thematic",
      "candidate_original_score": 0.75,
      "applied_flag": "pm_conflict",
      "applied_multiplier": 0.75,
      "matched_theme": "china_taiwan_tension",
      "market_slug": "taiwan-invasion-2026",
      "market_delta_24h": -0.12,
      "outcome_7d": null,
      "outcome_14d": null,
      "outcome_30d": null
    }
  ],
  "stats": {
    "total_events": 0,
    "confirms": 0,
    "conflicts": 0,
    "confirm_hit_rate_7d": null,
    "conflict_hit_rate_7d": null
  }
}
```

`signal_tracker.py`'ye benzer geri-doldurma mantığı: 7g/14g/30g sonra `outcome_*` alanları FMP fiyat checkpoint'iyle güncellenir. Çarpan tuning Phase 10'a kadar bekler.

---

## 10. PERFORMANS TRACKER

`agent/scanners/calibrator.py` her bayrak koyduğunda:
1. `polymarket_calibrator_performance.json`'a event yazar (yukarıdaki şema)
2. `events.jsonl`'a `type: "calibrator_flag"` ekler

Geri-doldurma cron'u (Railway, mevcut `signal_tracker`'a paralel veya birleşik):
- Her gün 23:50 — 7g/14g/30g hedefli event'leri tara, FMP'den fiyat çek, `outcome_*` güncelle
- Pazar 19:30 — haftalık DM özeti

**Tuning kuralı:** İlk 30 gün veri sadece toplanır, çarpan değiştirilmez. Veri yeterince birikince (en az 20 confirm + 20 conflict event) çarpan ayarlanabilir:
- Confirm hit rate %70+ → çarpan tavanını 1.25'e çıkar
- Conflict hit rate %70+ → çarpan tabanını 0.65'e indir
- Confirm hit rate %50-altı → kalibratör veto edilebilir (bu temayı whitelist'ten çıkar)

---

## 11. OBSERVABILITY — events.jsonl entegrasyonu

Yeni event tipleri:

| Type | Tetikleyici | Anahtar alanlar |
|---|---|---|
| `polymarket_call` | `agent/polymarket.py` HTTP isteği | endpoint, status, duration_ms, market_count |
| `calibrator_flag` | Kalibratör bayrak koyduğunda | candidate_symbol, applied_flag, multiplier, market_slug |
| `calibrator_watchlist_alert` | Pozisyon #3 uyarısı | symbol, theme, delta_24h |

`agent/reports/stats.py` (Faz 1'de taşındı) genişletilir: Polymarket çağrı sayısı, kalibratör bayrak dağılımı, hit rate (30g sonra).

---

## 12. WEEKLY PULSE — `agent/reports/weekly.py`

Yeni bölüm formatı (manuel rehberinden uyarlandı):

```markdown
## 🎲 Prediction Markets Pulse (Polymarket)

### Whitelist Tema Snapshot — 2026-05-17

| Tema | Mevcut Olasılık | 7g Δ | 7g Volume | Bayrak Sayısı | Net Etki |
|---|---|---|---|---|---|
| Fed Rate Cut June | 72% | +7pp | $12.3M | 3 confirm | +0.18 ortalama portföy skor |
| China-Taiwan | 8% | -2pp | $1.8M | 1 conflict | -0.05 ortalama AI supply chain |
| Iran Escalation | 35% | 0pp | $0.9M | (eşleşme yok) | — |
| Trump Tariff | 45% | +5pp | $2.1M | 2 conflict (AAPL, TSLA) | uyarı: tarife pozisyonları |
| US Recession 2026 | 22% | -3pp | $3.5M | 1 confirm (TLT) | hafif defensif teyit |

### Bu Hafta Kalibratör Aktivitesi
- Toplam bayrak: 7
- Doğrulama: 4 (3 confirm, 1 confirm_weak)
- Çelişki: 3 (2 conflict, 1 conflict_weak)
- En çok etkilenen scanner: thematic_discovery (5 bayrak)

### 30 Günlük Hit Rate (yeterli veri varsa)
- Confirm hit rate: 73% (16/22)
- Conflict hit rate: 64% (9/14)
```

---

## 13. SCHEDULING

Mevcut scanner schedule'ı korunur. Polymarket fetch hook'ları **scanner çalışmasından hemen önce** tetiklenir:

```
09:00 TR  → polymarket fetch → news_radar çalışır
12:30 TR  → polymarket fetch (cache hit ihtimali yüksek) → fair_value_panel çalışır
23:00 TR  → polymarket fetch → thematic_discovery çalışır
23:00 TR  → Pozisyon #3 watchlist sağlık taraması (paralel)

Pzr 11:00 TR  → polymarket weekly snapshot
Pzr 12:00 TR  → weekly raporu üretilir (Pulse bölümü dahil)

Hft 23:50 TR  → calibrator_performance.json geri-doldurma (FMP fiyat checkpoint)
Pzr 19:30 TR  → weekly kalibratör DM özeti
```

3 fetch/gün × 1h TTL → maksimum 3 unique API isteği/gün. Konservatif.

---

## 14. TEST STRATEJİSİ

### Birim testleri (mevcut `tests/` altında)

- `tests/test_scanners_base.py` — BaseScanner ABC + Candidate dataclass
- `tests/test_polymarket.py` — Gamma API client (mocked HTTP, `responses` lib mevcut)
- `tests/test_calibrator.py` — eşleştirme mantığı + çarpan tablosu
- `tests/test_calibrator_performance.py` — geri-doldurma + hit rate hesaplama

Hedef: Mevcut 79 testi koru, **en az 25 yeni test** ekle. Phase 2 sonrası ~104 test.

### Entegrasyon testleri

- 4 mevcut scanner'ın shim'leri yeni paketle aynı çıktıyı veriyor mu? — Faz 1 disiplini
- Kalibratör boş Polymarket cache ile çağrıldığında graceful degradation (çarpan 1.0, bayrak yok)
- Whitelist'te olmayan tema için kalibratör no-op

### Smoke testleri

Her scanner taşındıktan sonra:
- Lokal `python -m agent.scanners.thematic --dry-run` çalışıyor
- Eski `python scripts/thematic_discovery.py --dry-run` (shim üzerinden) aynı çıktıyı veriyor

---

## 15. MİGRASYON ADIMLARI (Commit sırası)

Risk en düşükten en yükseğe sıralı, her adım ayrı commit:

| # | Adım | Risk | Mevcut sistemi etkiler mi? |
|---|---|---|---|
| 1 | `docs/PHASE2_SCANNER_CONSOLIDATION.md` (bu dosya) | Sıfır | Hayır |
| 2 | `agent/scanners/base.py` (sadece interface, kullanan yok) | Sıfır | Hayır |
| 3 | `agent/polymarket.py` + `data/polymarket_themes.json` seed | Düşük | Hayır (modül izole) |
| 4 | `tests/test_polymarket.py` — modül doğrulama | Sıfır | Hayır |
| 5 | `agent/scanners/thematic.py` + shim + workflow güncelle | Orta | Evet — smoke test zorunlu |
| 6 | `agent/scanners/fair_value.py` + shim + workflow | Orta | Evet |
| 7 | `agent/scanners/news.py` + shim + workflow | Yüksek | Evet (GitHub API yan etkileri) |
| 8 | `agent/scanners/analyst_revisions.py` adaptör + shim | Yüksek | Evet (legacy alt-sistem) |
| 9 | `agent/scanners/calibrator.py` + tracker JSON seed | Orta | Hayır (henüz hook bağlı değil) |
| 10 | Kalibratör hook'larını scanner'lara bağla (Pozisyon #2) | Yüksek | Evet — tüm pipeline |
| 11 | Pozisyon #3 watchlist sağlık cron'u | Düşük | Sadece DM uyarısı ekler |
| 12 | `agent/reports/weekly.py` Pulse bölümü | Düşük | Pazar raporu genişler |
| 13 | `agent/reports/stats.py` Polymarket bölümü | Düşük | Haftalık stats genişler |
| 14 | `docs/SYSTEM_MAP.md` + `docs/system_map.json` güncelle | Sıfır | Dashboard güncellenir |

**Adım 1-4 tek PR**, izole değişiklik. **Adım 5-8 scanner-başına ayrı PR**, kademeli güven. **Adım 9-13 tek PR** kalibratör paketi.

---

## 16. RİSKLER VE GERİ ALMA

### Riskler

| Risk | Olasılık | Etki | Mitigation |
|---|---|---|---|
| Polymarket API down/değişim | Orta | Orta | Cache'den eski veri kullan; 6h+ stale ise kalibratör no-op |
| Whitelist mapping yanlış | Yüksek | Düşük | Çarpan dar aralık (0.75-1.20), veto yok |
| LLM köprüsü halüsinasyon | Yüksek | Orta | İnsan onayı zorunlu, statik tabloya işlenmeden kalibratör çalışmaz |
| Whale manipulation (low volume market) | Orta | Düşük | `min_volume_usd` filtresi (her temada tanımlı) |
| Scanner shim'leri farklı çıktı | Düşük | Yüksek | Faz 1 disiplini: shim öncesi/sonrası smoke test |
| Phase 10 erken başlatma | Düşük | Yüksek | Tracker `_started_at` tarih kontrolü, 30g öncesi tuning blokla |

### Geri alma planı

Her adım ayrı commit + her PR'da etiketli commit hash. Acil geri alma:
- Kalibratör tek başına devre dışı: `data/polymarket_themes.json` boş themes dict → kalibratör tüm Candidate'leri unchanged geri döndürür
- Scanner migrasyonu geri alma: shim hâlâ var, workflow YAML'ları eski path'e döndür → `git revert <commit>` yeterli
- Tam Faz 2 geri alma: branch sıralı revert, 14 commit (her adım için)

---

## 17. KALAN AÇIK SORULAR

Tasarım netleşti ama kod yazımında karar gerektirecek noktalar (Claude tarafından otonom karar verilecek, burada listeleniyor ki şeffaf olsun):

- **AI Gate'in `calibration_flags` ile etkileşimi:** LLM gate'in prompt'unda flag'leri nasıl sunalım? Adım 10'da netleşir.
- **Çoklu tema eşleşmesi:** Bir Candidate birden fazla tema ile eşleşirse (örn. TSM hem `china_taiwan_tension` hem `trump_tariff_action`) çarpanlar nasıl birleşir? **Karar:** En aşırı olan kazanır (max conflict veya max confirm), birden fazla bayrak listede tutulur.
- **Kalibratör no-op koşulları:** Polymarket cache 6h+ stale, whitelist tema yok, market volume eşiğin altı → hangi durumlarda warning, hangilerinde silent skip? Adım 9'da kod-içi karar.
- **Test verisi:** `tests/fixtures/polymarket_sample.json` ile mocked market verisi. Gerçek API'dan bir kez snapshot alıp commit edilir, deterministik test için.

---

## ZAMAN ÇİZELGESİ

| Hafta | Hedef adımlar |
|---|---|
| Hafta 1 (17-24 May) | Adım 1-4 (doc + base + polymarket modülü + testler) |
| Hafta 2 (24-31 May) | Adım 5-8 (4 scanner migrasyonu, kademeli) |
| Hafta 3 (31 May - 7 Haz) | Adım 9-13 (kalibratör + Pulse + stats) |
| Hafta 4 (7-14 Haz) | Adım 14 + 30g performans tracker veri toplama başlar |
| 14 Haz sonrası | Veri birikimi (Phase 10 ön şartı) |

---

## SONRAKİ ADIMLAR (Bu doküman onaylandıktan sonra)

Sonraki tur "devam et" derse:
- Adım 2: `agent/scanners/base.py` ve `Candidate` dataclass yazımı
- Adım 3: `agent/polymarket.py` Gamma API client iskeleti
- Adım 4: `tests/test_polymarket.py` mocked testler

Bu üç adım tek branch'te birlikte (`refactor/phase2-foundations`), izole, mevcut sistemi etkilemez.
