#!/usr/bin/env python3
"""
Finzora RAG — Embedder
========================
Voyage AI embedding wrapper.

Özellikler:
- Model fallback: voyage-3 → voyage-3-lite → voyage-2
- Batch processing (max 128 text per call, Voyage sınırı)
- Retry: service overloaded durumlarında bekle + dene
- Token sayımı

KULLANIM:
    from scripts.rag.embedder import embed_documents, embed_query

    embeddings = embed_documents(["metin 1", "metin 2"])
    query_vec = embed_query("arama sorgusu")
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

# agent/ klasörüne path ekle (scripts/_config değil, direkt agent/_config kullan)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AGENT_DIR = _REPO_ROOT / "agent"
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

from _config import VOYAGE_API_KEY  # noqa: E402

try:
    import voyageai
    _voyage_available = True
except ImportError:
    voyageai = None
    _voyage_available = False

# Tercih sırasıyla modeller (ilki yoksa sonrakiler dene)
_MODEL_FALLBACK = ["voyage-3", "voyage-3-lite", "voyage-2"]
_BATCH_SIZE = 128  # Voyage API sınırı
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0

# Client lazy init
_client: Optional["voyageai.Client"] = None
_last_successful_model: Optional[str] = None


def _get_client() -> "voyageai.Client":
    """Voyage client'ı lazy olarak oluştur."""
    global _client
    if not _voyage_available:
        raise RuntimeError(
            "voyageai kurulu değil. `pip install voyageai` veya "
            "requirements.txt'i güncelle."
        )
    if not VOYAGE_API_KEY:
        raise RuntimeError(
            "VOYAGE_API_KEY tanımsız. GitHub Secrets'a ekle veya "
            "local'de `export VOYAGE_API_KEY=...` yap."
        )
    if _client is None:
        _client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _client


def _embed_batch(
    texts: list[str],
    input_type: str,
    preferred_model: Optional[str] = None,
) -> tuple[list[list[float]], str, int]:
    """
    Tek bir batch'i embed et. Model fallback ve retry içerir.

    Returns: (embeddings, used_model, tokens)
    """
    global _last_successful_model
    client = _get_client()

    # Başarılı model varsa onu tercih et, yoksa tam fallback listesi
    if _last_successful_model and not preferred_model:
        models = [_last_successful_model] + [
            m for m in _MODEL_FALLBACK if m != _last_successful_model
        ]
    elif preferred_model:
        models = [preferred_model] + [m for m in _MODEL_FALLBACK if m != preferred_model]
    else:
        models = _MODEL_FALLBACK

    last_err = None
    for model in models:
        for attempt in range(_MAX_RETRIES):
            try:
                result = client.embed(texts, model=model, input_type=input_type)
                _last_successful_model = model
                return result.embeddings, model, result.total_tokens
            except Exception as e:
                last_err = e
                err_str = str(e)[:100]
                # Service overloaded → beklenen, retry
                if "overloaded" in err_str.lower() or "not ready" in err_str.lower():
                    wait = _RETRY_BACKOFF ** (attempt + 1)
                    print(f"[embedder] {model} meşgul, {wait:.1f}s bekle (deneme {attempt+1})")
                    time.sleep(wait)
                    continue
                # Başka hata → sonraki modele geç
                print(f"[embedder] {model} hata: {err_str}")
                break
    raise RuntimeError(f"Tüm modeller başarısız. Son hata: {last_err}")


def embed_documents(
    texts: list[str],
    preferred_model: Optional[str] = None,
    show_progress: bool = True,
) -> tuple[list[list[float]], dict]:
    """
    Belge gibi metinleri embed et (input_type='document').

    Returns: (embeddings, stats_dict)
    stats_dict: {model, batches, total_tokens, duration_sec}
    """
    if not texts:
        return [], {"model": None, "batches": 0, "total_tokens": 0, "duration_sec": 0}

    t0 = time.time()
    all_embeds: list[list[float]] = []
    total_tokens = 0
    used_model = None
    batch_count = 0

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        embs, model, tokens = _embed_batch(batch, "document", preferred_model)
        all_embeds.extend(embs)
        total_tokens += tokens
        used_model = model
        batch_count += 1

        if show_progress:
            print(
                f"[embedder] Batch {batch_count}: {len(batch)} text, "
                f"{tokens} token, model={model}, kümül={len(all_embeds)}/{len(texts)}"
            )

    return all_embeds, {
        "model": used_model,
        "batches": batch_count,
        "total_tokens": total_tokens,
        "duration_sec": round(time.time() - t0, 2),
    }


def embed_query(
    text: str,
    preferred_model: Optional[str] = None,
) -> tuple[list[float], dict]:
    """
    Tek sorgu embed et (input_type='query').

    Returns: (embedding, stats_dict)
    """
    t0 = time.time()
    embs, model, tokens = _embed_batch([text], "query", preferred_model)
    return embs[0], {
        "model": model,
        "total_tokens": tokens,
        "duration_sec": round(time.time() - t0, 3),
    }


if __name__ == "__main__":
    # Self-test
    print("Voyage embedder self-test")
    print("=" * 50)

    test_docs = [
        "Stop tetiklendi, aynı gün alınıp satıldı",
        "Kriz rallisinde ilk günü kovalama, soğuma bekle",
        "Earnings beat olmasına rağmen sell the news oldu",
    ]

    embs, stats = embed_documents(test_docs)
    print(f"\nDoc embed: {len(embs)} vektör, boyut={len(embs[0])}")
    print(f"Stats: {stats}")

    query = "aşırı satım RSI stop"
    qvec, qstats = embed_query(query)
    print(f"\nQuery embed: boyut={len(qvec)}")
    print(f"Stats: {qstats}")

    # Cosine similarity
    import math

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0

    print("\nQuery'ye en yakın belge:")
    scores = [(cosine(qvec, e), d) for e, d in zip(embs, test_docs)]
    scores.sort(reverse=True)
    for score, doc in scores:
        print(f"  {score:.3f} — {doc}")
