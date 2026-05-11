# Env Değişkenleri — Kanonik Liste

**Yürürlük:** 10 Mayıs 2026 itibarıyla
**Kaynak:** finzora ai
**İlgili dosyalar:** `agent/_config.py`, `scripts/_config.py`

## 1. Standart Adlar (Tercih Edilen)

Bu adlar memory entry #29 ile uyumlu, Railway/GitHub Actions Secrets'ta standarttır.

| Env adı | Python sembolü | Tür | Açıklama |
|---------|----------------|-----|----------|
| `FMP_API_KEY` | `FMP_KEY` | Zorunlu | Financial Modeling Prep API anahtarı (Ultimate plan) |
| `TELEGRAM_BOT_TOKEN` | `TELEGRAM_TOKEN` / `TELEGRAM_BOT_TOKEN` | Zorunlu | Telegram bot token |
| `TELEGRAM_PRIVATE_ID` | `TELEGRAM_PRIVATE_CHAT` / `TELEGRAM_PRIVATE_ID` | Zorunlu | Zeynel DM chat_id (1403072107) |
| `TELEGRAM_CHAT_ID` | `TELEGRAM_GROUP_CHAT` / `TELEGRAM_CHAT_ID` | Opsiyonel | Grup chat_id (-1003827034395) |
| `ANTHROPIC_API_KEY` | `ANTHROPIC_KEY` | Opsiyonel | Claude API anahtarı |
| `VOYAGE_API_KEY` | `VOYAGE_API_KEY` | Opsiyonel | RAG embedder için |
| `GH_TOKEN` | `GH_TOKEN` | Opsiyonel | GitHub API token (commit/push) |
| `PAT_TOKEN` | `GH_TOKEN` (fallback) | Opsiyonel | GH_TOKEN alternatifi |
| `RAPIDAPI_KEY` | `RAPIDAPI_KEY` | Opsiyonel | RapidAPI rezerv |
| `GCAL_ICAL_URLS` | (direkt env) | Opsiyonel | Google Calendar iCal URL'leri |
| `GCAL_ICAL_NAMES` | (direkt env) | Opsiyonel | Google Calendar iCal isimleri |

## 2. Legacy Adlar (Hâlâ Destekleniyor)

Eski kod tabanı bazı env adlarını farklı yazıyordu. `agent/_config.py` her iki adı da kabul ediyor — standart ad öncelikli, legacy fallback.

| Standart | Legacy fallback |
|----------|-----------------|
| `TELEGRAM_BOT_TOKEN` | `TELEGRAM_TOKEN` |
| `TELEGRAM_PRIVATE_ID` | `TELEGRAM_PRIVATE_CHAT` |
| `TELEGRAM_CHAT_ID` | `TELEGRAM_GROUP_CHAT` |
| `GH_TOKEN` | `PAT_TOKEN` |

Yeni kod yazılırken **her zaman standart adlar tercih edilir**. Legacy adlar sadece geriye dönük uyum için tutulur, ileride kaldırılabilir.

## 3. 10 Mayıs 2026 Kritik Bug Fix

Önceki `agent/_config.py` `TELEGRAM_PRIVATE_CHAT` için fallback olarak yanlışlıkla `TELEGRAM_CHAT_ID`'yi (grup) gösteriyordu. Bu, Railway'de sadece grup chat_id set edilmiş bir senaryoda **sistem mesajlarının yanlışlıkla gruba sızması** riskini taşıyordu (memory kuralı ihlali: sistem mesajları sadece Zeynel DM'e).

Düzeltme:

```python
# ESKİ (BUGGY)
TELEGRAM_PRIVATE_CHAT = (
    os.environ.get("TELEGRAM_PRIVATE_CHAT", "").strip()
    or os.environ.get("TELEGRAM_CHAT_ID", "").strip()  # ← YANLIŞ! Grup kanalı
)

# YENİ
TELEGRAM_PRIVATE_CHAT = (
    os.environ.get("TELEGRAM_PRIVATE_ID", "").strip()      # standart (DM)
    or os.environ.get("TELEGRAM_PRIVATE_CHAT", "").strip()  # legacy (DM)
)
TELEGRAM_GROUP_CHAT = (
    os.environ.get("TELEGRAM_CHAT_ID", "").strip()       # standart (grup)
    or os.environ.get("TELEGRAM_GROUP_CHAT", "").strip()  # legacy (grup)
)
```

Artık `TELEGRAM_CHAT_ID` özel kanala (Zeynel DM) sızmıyor, sadece grup kanalını besliyor.

## 4. Uyarı Sistemi

`agent/_config.py` modülü yüklenirken kritik env eksikliklerini stderr'e yazar. Uyarı **Python sembolü bazlı** yapılır (env adı bazlı değil), böylece legacy ad ile set edilse bile fallback'ten sonra sembol doluysa yanlış uyarı çıkmaz.

Kritik sembol listesi:
- `FMP_KEY` (env: `FMP_API_KEY`)
- `TELEGRAM_TOKEN` (env: `TELEGRAM_BOT_TOKEN` veya legacy `TELEGRAM_TOKEN`)
- `TELEGRAM_PRIVATE_CHAT` (env: `TELEGRAM_PRIVATE_ID` veya legacy `TELEGRAM_PRIVATE_CHAT`)

Uyarıyı bastırmak için: `FINZORA_SUPPRESS_CONFIG_WARN=1`

## 5. Yeni Kod İçin Kullanım Örneği

```python
# Standart import (yeni kod) — memory adlandırması ile birebir
from _config import (
    FMP_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_PRIVATE_ID,
    TELEGRAM_CHAT_ID,
)

# Geriye dönük uyumlu import (eski kod, hâlâ çalışıyor)
from _config import (
    FMP_KEY,
    TELEGRAM_TOKEN,         # = TELEGRAM_BOT_TOKEN
    TELEGRAM_PRIVATE_CHAT,  # = TELEGRAM_PRIVATE_ID
    TELEGRAM_GROUP_CHAT,    # = TELEGRAM_CHAT_ID
)
```

## 6. Doğrulama

`agent/_config.py` 4 test senaryosu üzerinden doğrulandı:

1. **Standart adlar** (Railway production): Tüm sembol değerleri doğru atanıyor
2. **Legacy adlar**: Fallback üzerinden doğru sembol değerleri
3. **Sadece TELEGRAM_CHAT_ID set** (regression): `PRIVATE_CHAT` boş kalır, grup kanalı özel kanala SIZMAZ
4. **Eksik kritik env**: Uyarı standart adlarla yazdırılır, false positive yok

Smoke test komutu:

```bash
FMP_API_KEY=x \
TELEGRAM_BOT_TOKEN=y \
TELEGRAM_PRIVATE_ID=z \
python -c "import sys; sys.path.insert(0,'agent'); import _config; \
  print(_config.TELEGRAM_PRIVATE_CHAT, _config.TELEGRAM_PRIVATE_ID)"
```

---

**Son güncelleme:** 10 Mayıs 2026
**Kaynak:** finzora ai
