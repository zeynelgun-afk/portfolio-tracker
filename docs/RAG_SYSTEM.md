# RAG — Retrieval Augmented Generation

Finzora AI nın hafıza katmanı. Geçmiş trade leri, kararları, dersler ve dokümantasyonu vektör uzayında indexler; her yeni Claude çağrısı öncesi sorgu bazlı ilgili bağlamı çeker.

## Amaç

Claude API her çağrıldığında sıfırdan başlar. Önceki trade ler, LASR dersi, AI tedarik zinciri tezi, K-kuralları — hiçbirini bilmez. RAG bu boşluğu doldurur:

1. `logs/events.jsonl` ve `data/swing/closed.json` otomatik indexlenir
2. Claude çağrısı öncesi sorgu (örn. "POWL için stop kararı") retriever a gider
3. En ilgili 5 chunk Claude nin system prompt una eklenir
4. Claude artık "geçmişi bilen" bir karar verir

## Yapı

```
scripts/rag/
  embedder.py    # Voyage AI wrapper (retry + model fallback)
  indexer.py     # Kaynakları chunk a böl, embed, ChromaDB ye yaz
  retriever.py   # Sorgu → top-k chunk (metadata filter destekli)

data/rag/chroma/ # ChromaDB persistent store (gitignore)
```

## Kullanım

### İlk kurulum (tek seferlik)

```bash
# Local geliştirme
export VOYAGE_API_KEY="pa-..."
pip install voyageai chromadb

# Tüm event lerle index
python scripts/rag/indexer.py --rebuild

# Docs dahil etmek için
python scripts/rag/indexer.py --rebuild --include-docs
```

### Incremental güncelleme

Yeni event eklendiğinde (yeni trade, yeni karar):

```bash
python scripts/rag/indexer.py
# Sadece yeni id leri bulup embed eder, eskileri atlar
```

### Sorgulama (CLI)

```bash
# Basit arama
python scripts/rag/retriever.py "stop tetiklendi earnings"

# Sembol filtresi
python scripts/rag/retriever.py "yarım pozisyon" --symbol POWL

# Event tipi filtresi
python scripts/rag/retriever.py "ders" --type swing_lesson

# Portföy filtresi
python scripts/rag/retriever.py "AI tedarik" --portfoy aggressive

# Claude context formatı
python scripts/rag/retriever.py "POWL insider satışı" --claude-format --top-k 3
```

### Python API

```python
from scripts.rag.retriever import retrieve, format_context_for_claude

hits = retrieve("kriz rallisi erken alım", top_k=5)
for h in hits:
    print(h["score"], h["text"][:100])

# Claude'a inject için formatla
context = format_context_for_claude(hits)
# context bir string — system prompt'a veya user message'a ekle
```

## Event → Chunk dönüşümü

### Trade event
```json
{"id": "bf-abc", "type": "trade", "action": "SELL", "sembol": "POWL",
 "shares": 34, "price": 522.92, "reason": "stop tetiklendi...", "pnl_pct": -10.63}
```
↓
```
[TRADE] SELL POWL 34 adet @$522.92. Toplam: $17779.28.
Tarih: 2026-03-30. Neden: stop tetiklendi - 2xATR trailing stop $524.89 kirildi...
K/Z: -10.63%
```

### Swing lesson (closed.json dan)
closed.json daki her kapatılmış pozisyon AYRI chunk olarak indexlenir, çünkü `giris_nedeni + cikis_nedeni + dersler` birleşimi Claude için en değerli sinyaldir.

### Decision event
```
[KARAR] EKLE POWL 100%. Portfoy: aggressive. Mod: morning.
Neden: AI supply chain, EPS beat + insider cluster buying.
Hedef: $650. Stop: $580. Uygulandı: evet
```

### Claude call event
Observability için minimum info (cost, duration, success) — RAG değeri düşük ama dahil.

## Metadata filtreleri

ChromaDB where clause formatı:

```python
# Tek filtre
where = {"symbol": "POWL"}

# Çoklu AND
where = {"$and": [
    {"symbol": "POWL"},
    {"event_type": "trade"},
    {"date": {"$gte": "2026-03-01"}}
]}

# OR
where = {"$or": [
    {"action": "BUY"},
    {"action": "SELL"}
]}
```

Kullanılabilir metadata alanları (her chunk ta):
- `event_id`, `event_type`, `ts`, `date`
- `symbol` (semboller BÜYÜK harfle)
- `action` (BUY/SELL/LESSON)
- `portfoy` (balanced/aggressive/dividend/swing/"" — boşsa bilinmiyor)
- `source` (events.jsonl / swing/closed.json / docs/xxx.md)
- `has_lessons` (True/False)
- `backfill` (True = geçmiş veri, False = gerçek zamanlı kayıt)

## Embedding modeli

- Primary: `voyage-3` (1024 boyut, Anthropic önerisi, en iyi kalite)
- Fallback: `voyage-3-lite` (512 boyut, daha hızlı ve ucuz)
- Son çare: `voyage-2` (1024, yedek)

Embedder modül son kullanılan başarılı modeli hatırlar; sonraki çağrılarda önce onu dener. Hata → sıradaki model.

### Maliyet

- `voyage-3`: \$0.06/M token
- `voyage-3-lite`: \$0.02/M token

İlk index (231 chunk, ~19K token) maliyeti ~\$0.001. Aylık artış yaklaşık \$0.01 seviyesinde (günde ~30 yeni event, 300 token).

## Veri akışı

```
logs/events.jsonl ─┐
                   ├─→ indexer.py ─→ Voyage AI ─→ data/rag/chroma/
closed.json ───────┤                 (embed)
docs/*.md ─────────┘

Kullanıcı sorgusu ─→ retriever.py ─→ Voyage (query embed) ─→ Chroma search
                                                            ↓
                                                    top-k chunks
                                                            ↓
                                     format_context_for_claude()
                                                            ↓
                                   system_prompt + user_message → Claude API
```

## Rebuild stratejisi

ChromaDB binary dosyaları `data/rag/chroma/` altında. Gitignore da. İki senaryo:

1. **Lokal**: İlk kurulum sonrası commit etmeye gerek yok, indexer her run da incremental ekler.
2. **GitHub Actions**: Her workflow run ında koleksiyon YOK. İki seçenek:
   - **A**: Workflow başlangıcında `python scripts/rag/indexer.py --rebuild` — ama embedding çağrısı maliyeti doğar
   - **B**: ChromaDB yi artifact olarak cache le — 90 gün retention
   - **C**: Bu POC için şimdilik lokal kullan, production da karar ver

## Sonraki adımlar

- [ ] `scripts/rag/claude_with_context.py` — tam pipeline: soru → retrieve → Claude
- [ ] Orchestrator entegrasyonu — morning/closing raporu öncesi otomatik context inject
- [ ] Incremental reindex workflow — her gün yeni event leri indexle
- [ ] Metadata zenginleştirme — sektör, tema, özellik etiketleri
- [ ] Query expansion — Claude ye sorguyu genişlettirmek (HyDE benzeri)

## Sorun giderme

**"Koleksiyon yüklenemedi"** → İndexer henüz çalışmadı. `python scripts/rag/indexer.py --rebuild`

**"voyageai kurulu değil"** → `pip install voyageai chromadb`

**"VOYAGE_API_KEY tanımsız"** → `export VOYAGE_API_KEY="pa-..."` veya GitHub Secrets a ekle

**"voyage-3 overloaded"** → Normal, embedder fallback ile voyage-3-lite e geçer. Yine olmazsa retry artır.
