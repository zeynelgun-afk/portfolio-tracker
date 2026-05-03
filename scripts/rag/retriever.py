#!/usr/bin/env python3
"""
Finzora RAG — Retriever
=========================
ChromaDB'den sorgu ile ilgili chunk'ları çeker.

KULLANIM (Python):
    from scripts.rag.retriever import retrieve

    hits = retrieve("stop tetiklendi earnings", top_k=5)
    for h in hits:
        print(h["score"], h["text"][:100])

METADATA FİLTRESİ:
    hits = retrieve("POWL", filter={"symbol": "POWL"})
    hits = retrieve("ders", filter={"event_type": "swing_lesson"})

KULLANIM (CLI):
    python scripts/rag/retriever.py "kriz rallisi" --top-k 5
    python scripts/rag/retriever.py "POWL" --symbol POWL
    python scripts/rag/retriever.py "ders" --type swing_lesson
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "rag"))
sys.path.insert(0, str(_REPO_ROOT / "agent"))

from embedder import embed_query  # noqa: E402

CHROMA_PATH = _REPO_ROOT / "data" / "rag" / "chroma"
COLLECTION_NAME = "finzora"

_collection = None


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def retrieve(
    query: str,
    top_k: int = 5,
    filter: Optional[dict] = None,
) -> list[dict]:
    """
    Sorguyu embed edip en yakın top_k chunk'ı döner.

    Args:
        query: Arama metni
        top_k: Kaç sonuç
        filter: ChromaDB metadata filtresi, örn {"symbol": "POWL"} veya
                {"$and": [{"symbol": "POWL"}, {"event_type": "trade"}]}

    Returns:
        [{score, text, metadata, id}, ...] — skor 0-1 arası, 1 en iyi
    """
    try:
        col = _get_collection()
    except Exception as e:
        print(f"[retriever] Koleksiyon yüklenemedi: {e}")
        print("İlk kurulum için: python scripts/rag/indexer.py --rebuild")
        return []

    qvec, _ = embed_query(query)

    result = col.query(
        query_embeddings=[qvec],
        n_results=top_k,
        where=filter,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    if not result["ids"] or not result["ids"][0]:
        return hits

    for i in range(len(result["ids"][0])):
        distance = result["distances"][0][i]
        # ChromaDB cosine distance (0 = ident, 2 = zıt) → benzerliğe çevir
        score = max(0.0, 1.0 - distance / 2.0)
        hits.append({
            "id": result["ids"][0][i],
            "score": round(score, 4),
            "text": result["documents"][0][i],
            "metadata": result["metadatas"][0][i],
        })

    return hits


def format_context_for_claude(hits: list[dict], max_chars: int = 4000) -> str:
    """
    Retrieved chunk'ları AI'ye inject edilebilir context string'e çevir.
    max_chars sınırını aşan chunk'lar atılır.
    """
    if not hits:
        return ""

    lines = ["## İlgili Geçmiş Kayıtlar (RAG)"]
    total = 0
    for h in hits:
        block = f"\n[{h['metadata'].get('date', '?')}] [{h['metadata'].get('event_type', '?')}] (skor: {h['score']})\n{h['text']}"
        if total + len(block) > max_chars:
            lines.append("\n[... daha fazla sonuç kesildi (max_chars)]")
            break
        lines.append(block)
        total += len(block)

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="Arama sorgusu")
    ap.add_argument("--top-k", type=int, default=5, help="Sonuç sayısı")
    ap.add_argument("--symbol", help="Sembol filtresi")
    ap.add_argument("--type", help="event_type filtresi (trade/decision/swing_lesson/doc)")
    ap.add_argument("--portfoy", help="portfoy filtresi")
    ap.add_argument("--claude-format", action="store_true",
                    help="LLM context formatında bastır")
    args = ap.parse_args()

    # Filtre oluştur
    filters = {}
    if args.symbol:
        filters["symbol"] = args.symbol
    if args.type:
        filters["event_type"] = args.type
    if args.portfoy:
        filters["portfoy"] = args.portfoy

    # ChromaDB filter formatı: tek alan {k: v}, çoklu {$and: [{k: v}, ...]}
    where = None
    if len(filters) == 1:
        where = filters
    elif len(filters) > 1:
        where = {"$and": [{k: v} for k, v in filters.items()]}

    hits = retrieve(args.query, top_k=args.top_k, filter=where)

    if args.claude_format:
        print(format_context_for_claude(hits))
    else:
        print(f"Query: {args.query}")
        if where:
            print(f"Filter: {where}")
        print(f"Sonuç: {len(hits)} chunk\n")
        for i, h in enumerate(hits, 1):
            print(f"--- #{i} skor={h['score']:.3f} ---")
            print(f"ID: {h['id']}")
            print(f"Meta: {h['metadata']}")
            print(f"Text: {h['text'][:300]}")
            print()


if __name__ == "__main__":
    main()
