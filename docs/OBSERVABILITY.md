---
title: Observability Altyapısı
description: Her LLM API çağrısı, FMP çağrısı, karar ve trade olayının kayıt sistemi. JSONL stream + SQLite index.
tags:
  - observability
  - logging
  - infrastructure
related:
  - "[[Index]]"
  - "[[SYSTEM_MAP]]"
  - "[[RAG_SYSTEM]]"
---

# Observability — Karar ve Çağrı Kayıt Altyapısı

Finzora AI sisteminin her LLM API çağrısı, FMP çağrısı, karar ve trade olayı otomatik olarak kaydedilir. Amaç: maliyet takibi, hata yakalama, pattern analizi ve ileride RAG için veri kaynağı.

## İki Depo

| Depo | Konum | Amaç | Git |
|------|-------|------|-----|
| JSONL event stream | `logs/events.jsonl` | Append-only, insan okuyabilir, RAG kaynak | gitignore |
| SQLite index | `data/finzora.db` | Sorgulanabilir, rapor | gitignore |

SQLite dosyası her zaman JSONL den yeniden inşa edilebilir (idempotent).

## Event Tipleri

### 1. `claude_call`
Her LLM API çağrısı.
```json
{
  "id": "a1b2c3d4",
  "ts": "2026-04-17T21:15:30.123Z",
  "type": "claude_call",
  "mode": "morning",
  "model": "claude-opus-4-6",
  "input_tokens": 1234,
  "output_tokens": 567,
  "cost_usd": 0.0612,
  "context_chars": 5678,
  "decisions_count": 3,
  "duration_ms": 4321,
  "success": 1,
  "error": null
}
```

### 2. `fmp_call`
Her FMP API çağrısı.
```json
{
  "id": "e5f6g7h8",
  "ts": "2026-04-17T21:15:31.456Z",
  "type": "fmp_call",
  "endpoint": "quote",
  "status": 200,
  "duration_ms": 120,
  "retry_count": 0,
  "response_size": 1500,
  "success": 1,
  "error": null
}
```

### 3. `decision`
AI dan çıkan her karar.
```json
{
  "id": "i9j0k1l2",
  "ts": "2026-04-17T21:15:33.789Z",
  "type": "decision",
  "claude_call_id": "a1b2c3d4",
  "mode": "morning",
  "tip": "EKLE",
  "portfoy": "balanced",
  "sembol": "AAPL",
  "pct": 100,
  "neden": "PE 18.5 tarihsel ortalamanın altında...",
  "hedef_fiyat": 220.0,
  "stop": 180.0,
  "aciliyet": "bugün",
  "executed": 0,
  "skipped_reason": null
}
```

### 4. `trade`
Gerçekleşmiş alım/satım.
```json
{
  "id": "m3n4o5p6",
  "ts": "2026-04-17T21:16:00.000Z",
  "type": "trade",
  "decision_id": "i9j0k1l2",
  "action": "BUY",
  "portfoy": "balanced",
  "sembol": "AAPL",
  "shares": 50,
  "price": 199.50,
  "total": 9975.00,
  "reason": "K-13 eşiği geçti, skor 9.2"
}
```

## Kullanım

### Kod içinde
```python
from observability import log_claude_call, log_fmp_call, log_decision, log_trade

# Genelde wrapper fonksiyonlar (claude_agent.py, fmp_client.py) bunu otomatik yapar.
# Yeni yerde loglama yapılacaksa:
log_decision(
    mode="monitor",
    tip="ÇIK",
    portfoy="aggressive",
    sembol="POWL",
    neden="Stop tetiklendi",
    executed=True,
)
```

### Komut satırı raporu
```bash
# Son 7 gün özet
python scripts/finzora_stats.py

# Son 30 gün
python scripts/finzora_stats.py --days 30

# Bugün
python scripts/finzora_stats.py --today

# Telegram a gönder
python scripts/finzora_stats.py --days 7 --telegram
```

### SQL ile direkt sorgu
```bash
sqlite3 data/finzora.db

# En pahalı AI günleri
SELECT
    date(ts) as gun,
    COUNT(*) as cagri_sayisi,
    SUM(cost_usd) as maliyet
FROM claude_calls
GROUP BY date(ts)
ORDER BY maliyet DESC
LIMIT 10;

# En yavaş FMP endpointleri
SELECT
    endpoint,
    AVG(duration_ms) as ort_ms,
    COUNT(*) as n
FROM fmp_calls
GROUP BY endpoint
HAVING n > 10
ORDER BY ort_ms DESC;

# EKLE kararlarının uygulanma oranı
SELECT
    portfoy,
    COUNT(*) as toplam,
    SUM(executed) as uygulanan,
    CAST(SUM(executed) AS REAL) / COUNT(*) * 100 as oran_pct
FROM decisions
WHERE tip = 'EKLE'
GROUP BY portfoy;
```

## Güvenlik ve Maliyet

- **JSONL ve SQLite gitignore da**. Git repo büyümez, sürekli commit oluşmaz.
- **Fail-safe**: Observability çökmesi asla ana sistemi etkilemez. Her log yazımı try/except içinde.
- **Maliyet tahmini**: AI Opus 4.6 için varsayılan \$15/M input, \$75/M output. Gerçek pricing'i [anthropic.com/pricing](https://www.anthropic.com/pricing) ile doğrula. Yanlışsa `observability.py` içinde `_CLAUDE_COST_PER_M_IN/OUT` güncelle.

## RAG için Kaynak

`logs/events.jsonl` formatı RAG indexleme için ideal:
- Her satır bağımsız bir olay
- Timestamp + semantik alanlar (sembol, mode, neden) arama için
- Append-only → incremental index güncellemesi kolay

RAG fazına geçince bu dosyayı direkt beslemek için `scripts/rag/indexer.py` bu yolu kullanacak.
