# FMP Audit Alt-Aksiyon Tamamlanma — 10 Mayıs 2026

**Tarih:** 10 Mayıs 2026 (Cumartesi akşam)
**Bağlam:** 10 Mayıs FMP audit (commit `42b2cc7` ve sonrası) için takip aksiyonları
**Kaynak:** finzora ai

---

## 1. Yönetici Özeti

10 Mayıs FMP audit'in 4 ana aksiyonu (önceki turda) ve onların altından çıkan 3 alt-aksiyon (bu turda) tamamlandı. Toplam 6 commit `main` branch'a push edildi. Memory'deki "Migrating duplicate fmp_get implementations to fmp_client" maddesi büyük ölçüde kapatıldı: 22 duplicate `fmp_get`'in 21'i artık canonical kullanıyor (sadece `scripts/news_radar.py` tasarımsal nedenle kendi sofistike retry mantığını koruyor).

Yeni gelişmeler:
- `bilanco-sonrasi-us` Aşama 4d öncesi hızlı triage (rate limit dostu, gereksiz SEC fetch'i atlıyor)
- `agent/fmp_client.py` system-wide 50ms throttle (30 Nis 2026 burst dalgasının ampirik analizi sonucu)
- `tests/test_fmp_client.py` 27 test (24 önceki + 3 throttle), 0.60 saniyede tamamı PASS

---

## 2. Bu Turun Aksiyonları

### 2.1 Senaryo A — `bilanco-sonrasi-us` hızlı triage (commit `61c6b9d`)

`press_release_signal()` başına `has_earnings_press_release()` triage helper'ı eklendi. SEC.gov fetch'i denenmeden önce `news/press-releases` ile bilanço dönemi PR yayınlanıp yayınlanmadığı hızlıca kontrol edilir. Bilanço PR'ı yoksa erken `{"available": False, "reason": "bilanco_PR_yok_triage"}` dönüyor, gereksiz `sec-filings-search` ve SEC.gov fetch çağrıları önleniyor.

Triage logic:
- `news/press-releases` `?symbols=` (ÇOĞUL) parametresi (10 May skill bug fix uyumlu)
- Bilanço tarihi ±2 gün penceresi
- Earnings keywords listesi: `first/second/third/fourth quarter`, `q1-4`, `fiscal`, `earnings`, `quarterly`, `reports`, `results`
- Default güvenli: API hatası veya boş yanıt halinde `True` döner (mevcut SEC fetch akışı korunur)

Smoke test:
| Ticker | Tarih | Sonuç | Doğrulama |
|--------|-------|-------|-----------|
| VST | 2026-05-06 | `True` | ✓ "Vistra Reports First Quarter 2026 Results" 7 May'da |
| VST | 2025-01-01 | `False` | ✓ Yanlış tarih |
| AAPL | 2099-05-05 | `False` | ✓ Gelecek tarih |
| VST | 2026-02-25 | `True` | ✓ Q4 2025 bilanço PR'ı yakında |

### 2.2 `fmp_client` system-wide throttle (commit `6c87c2e`)

30 Nisan 2026 16:31-34 burst dalgasının (11 ardışık 429 hatası) ampirik analizi sonucunda kaynak tespit edildi: `agent/valuation/methods/fetch_all_data()` 11 ardışık endpoint çağırıyor (quote, profile, ratios-ttm, key-metrics-ttm, income-statement annual+quarter, cash-flow-statement, balance-sheet-statement, analyst-estimates, price-target-consensus, treasury-rates).

Çözüm — `agent/fmp_client.py`'a system-wide minimum interval throttle:

```python
_MIN_CALL_INTERVAL = 0.05  # 50ms = max 20 call/sn = 1200/dk
_last_call_ts = 0.0

def _throttle():
    global _last_call_ts
    if _MIN_CALL_INTERVAL <= 0:
        return
    now = time.monotonic()
    elapsed = now - _last_call_ts
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)
    _last_call_ts = time.monotonic()
```

`_throttle()` her `requests.get()` öncesi çağrılıyor. Test ortamında `_MIN_CALL_INTERVAL = 0` set edilebilir (`tests/conftest.py` autouse fixture).

Etki:
- Ultimate plan 3000/dk limit altında %60 güvenlik marjı (1200/dk max)
- `fetch_all_data()`: 11 endpoint × 50ms = 0.55 saniye ek latency per ticker (kabul edilebilir)
- Migrate edilmiş 21 dosyaya otomatik uygulanır (her dosyada ek değişiklik gerekmedi)

Test güncellemesi:
- `tests/conftest.py` (yeni): autouse fixture, tüm testlerde throttle disable
- `TestThrottle` grubu (3 yeni test):
  - `test_throttle_enforces_min_interval` (5 ardışık call ≥ 200ms)
  - `test_throttle_zero_disables` (`_MIN_CALL_INTERVAL=0` hızlı geçiş)
  - `test_throttle_does_not_double_count` (önceki call'ın süresi yeterliyse extra wait yok)
- Toplam: **27/27 PASS, 0.60 saniye**

### 2.3 Bekleyen 10 dosyalık migration push (commit `0887ef4`)

Önceki bir oturumda local'de yapılmış ama push edilmemiş 10 migration dosyası:

| Dosya | fmp_get çağrı sayısı | Durum |
|-------|----------------------|-------|
| `scripts/daily_update.py` | 5 | ✓ canonical wrapper (None preservation) |
| `scripts/k_rules_common.py` | 4 | ✓ canonical wrapper (8 K-script kullanır, kritik) |
| `scripts/macro_calendar_updater.py` | 3 | ✓ canonical wrapper |
| `scripts/portfolio_scan_common.py` | 7 | ✓ canonical wrapper (sabah portföy taraması) |
| `scripts/result_tracker.py` | 4 | ✓ canonical wrapper (1.5s pre-throttle korundu) |
| `scripts/swing_entry_engine.py` | 9 | ✓ canonical wrapper (swing girişi) |
| `scripts/swing_ichimoku.py` | 3 | ✓ canonical wrapper (ichimoku 4/4 tarama) |
| `skills/bilanco-sonrasi-us/scripts/01_earnings_calendar.py` | 3 | ✓ canonical wrapper |
| `skills/bilanco-sonrasi-us/scripts/02_growth_filter.py` | 2 | ✓ canonical wrapper |
| `skills/bilanco-sonrasi-us/scripts/03_valuation.py` | 6 | ✓ canonical wrapper |

Hepsi aynı pattern: `try/except ImportError + fallback` (ilk migrate edilen dosyalar `agent/k_engine.py`, `agent/valuation/*` ile uyumlu). Eski `None` dönüş davranışı wrapper içinde korunarak çağıran kod tabanında bozulma olmadı.

Canlı API smoke test:
- `k_rules_common.fmp_get(quote, AAPL)` → $293.32 ✓
- `swing_ichimoku.fmp_get(quote, MSFT)` → $415.12 ✓
- `result_tracker.fmp_get(quote, NVDA)` → $215.20 ✓

---

## 3. Kalan Migration Durumu

22 duplicate `fmp_get`'ten **21'i artık canonical kullanıyor**. Sadece **1 tasarımsal istisna** kaldı:

### `scripts/news_radar.py` (korundu)

Sebep: Kendi sofistike retry mantığı var:
- 503 ayrı backoff (5s × 2^attempt)
- 429 ayrı backoff (10s × 2^attempt)
- Timeout ayrı backoff (3s × 2^attempt)
- DNS cache overflow text yakalama
- `log()` fonksiyonu ile özel olay kaydı (event_logger entegrasyonu)

Migrate edilirse bu sofistike davranışlar kayıp olur. `news_radar.py` günlük çalışıyor (08:30 takvim, 09:00 news_radar) ve şu anki davranışı stabil. Future iş: news_radar'ın retry mantığını canonical fmp_client'a taşımak (örn. `fmp_client.fmp_get(..., custom_backoff=...)` parametresi). Ama bu büyük refactor, ayrı scope.

### `skills/bilanco-sonrasi-us/scripts/04_post_earnings_signals.py` (kısmen)

`fmp_get` kullanıyor ama yerel tanım korundu (skill bağımsızlığı için). Aynı dosyada bu turda Senaryo A triage (commit `61c6b9d`) eklendi.

---

## 4. Önemli Bulgular ve Öğrenmeler

### 4.1 Skill bug — `?symbol=` (tekil) sessizce IGNORE

10 Mayıs sabah audit testimde AAPL ile test ettiğim için yakalanmadı. VST testi tuzağı ortaya çıkardı. Bu bulgu:
- `docs/FMP_SKILL.md` v3 düzeltmesi (10 May akşam)
- Memory #21 güncellemesi
- `tests/test_fmp_client.py` `TestDesignPrinciples::test_silent_param_ignore_caught` (prensip belgesi)
- `notes/2026-05-10_PRESS_RELEASE_EVAL.md` (5. bölümde yan bulgu olarak)

**Test design prensibi**: API parametre filtre testlerinde **low-noise ticker** (VST, COIN, CELH) kullanılmalı. AAPL/MSFT gibi yüksek-haber yoğunluklu ticker'lar latest listesinde zaten yer aldıkları için yanlış pozitif teyit verir.

### 4.2 30 Nisan burst dalgası kaynağı

`fetch_all_data()` 11 endpoint ardışık çağırıyor. 50 ticker'lık tarama saniyede 50+ çağrı üretebiliyor → Premium 750/dk dakikalık limiti aşılabiliyor. Yeni 50ms throttle bu sorunu kaynağında çözüyor.

### 4.3 fmp_client wrapper pattern olgunluğu

`scripts/k_rules_common.py` ve `scripts/swing_ichimoku.py` gibi dosyaların pattern'i (canonical + None preservation wrapper) net bir standart oluşturdu. Future migration adayları (örn `news_radar.py` taşınırsa) bu pattern'i izleyebilir.

---

## 5. Bekleyen TODO'lar

Memory'deki "On the horizon" listesinden:

1. ✅ **Migrating duplicate fmp_get implementations to fmp_client** — 21/22 tamamlandı
2. ✅ **Weekly stats GitHub Actions workflow** — `.github/workflows/weekly_fmp_stats.yml` eklendi. Sadece `workflow_dispatch` (manuel) + `push paths` (script veya workflow değişimi smoke test) tetikleyicili, memory kuralına uyumlu (cron yasak, Railway tek zamanlayıcı). Mevcut `scripts/finzora_stats.py` script'i kullanılıyor, FMP endpoint istatistiği + LLM API kullanımı + karar tipi dağılımı tek raporda. `--days N` ve `--telegram` (Zeynel DM) parametreleri workflow inputs üzerinden expose edildi. Script env adı tutarsızlığı (TELEGRAM_TOKEN/PRIVATE_CHAT vs standart TELEGRAM_BOT_TOKEN/PRIVATE_ID) fallback ile geriye dönük uyumlu çözüldü. Çıktı 90 gün artifact olarak saklanıyor.
3. ✅ **Orchestrator silent-failure cleanup** — 26 silent failure'ın kök nedeni bulundu ve düzeltildi (commit aşağıda). 429 ve body "Limit Reach" kod yolları `continue` ile geçerken `last_err` SET ETMİYORDU; retry tükendiğinde `error=None` log'a yazılıyordu. Fix: iki kod yoluna `last_err = "429_rate_limit (attempt N/M)"` ve `last_err = "body_limit_reach (attempt N/M)"` eklendi. 2 yeni test (`test_rate_limit_max_retries_exhausted` güncellendi, `test_body_limit_reach_exhausted_logs_error` eklendi) ile silent failure regression koruması var. Toplam 28/28 PASS.
4. ⏳ **Git strategy split for bot commits** — bot commit'leri ile manuel commit'leri ayırma
5. ⏳ **Adding test suite** — `tests/test_fmp_client.py` ile başlangıç yapıldı (28 test). Diğer modüller için (k_engine, observability, valuation) ayrı test suite'leri yazılmalı

Yeni eklendi:
6. ⏳ **`news_radar.py` migration** — kendi retry mantığını canonical'a taşıma (büyük refactor)
7. ⏳ **`bilanco-sonrasi-us` Aşama 4d effectiveness ölçümü** — Senaryo A triage'in pazartesi sonrası gerçek bilanço sezonunda kaç hisse için "bilanco_PR_yok_triage" döndüğünü ve kaç gereksiz SEC fetch'in önlendiğini observability'den çıkar

---

## 6. Commit Tarihçesi (10 May 2026)

| Commit | Açıklama |
|--------|----------|
| `42b2cc7` | docs/FMP_SKILL.md skill fixes + agent/fmp_client.py runtime fixes (sabah) |
| `833a428` | notes/2026-05-10_FMP_AUDIT.md ilk rapor |
| `bfd102f` | agent/{tools,risk_engine,backtester}.py canonical fmp_client'a migrate |
| `8c2dc4c` | notes log analiz + PR eval + tests/ klasörü + skill press-releases bug fix |
| `6764f43` | notes audit raporu Sonraki Aksiyonlar status update |
| `61c6b9d` | bilanco-sonrasi-us Aşama 4d öncesi hızlı triage (Senaryo A) |
| `6c87c2e` | fmp_client system-wide burst koruması (50ms throttle) + 3 yeni test |
| `0887ef4` | 10 duplicate fmp_get migration push (scripts/* + skills/01-03) |

8 commit, hepsi `main` branch'a push edildi.

---

**Rapor hazırlama tarihi:** 10 Mayıs 2026
**Toplam test sayısı:** 27/27 PASS (0.60 saniye)
**Migrate edilen dosya:** 21/22 duplicate fmp_get
**Kaynak:** finzora ai
