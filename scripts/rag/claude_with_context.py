#!/usr/bin/env python3
"""
Finzora RAG — Context-Augmented Kimi Call (via OpenRouter)
============================================================
User query → RAG retrieve → Kimi K2 thinking → response.

USAGE:
  python scripts/rag/claude_with_context.py "POWL için ne düşünüyorsun?"
  python scripts/rag/claude_with_context.py "Son kriz rallilerinde hangi dersler var?" --top-k 8
  python scripts/rag/claude_with_context.py "AI tedarik zinciri" --symbol COHR --top-k 5

FLOW:
  1. Query is embedded with Voyage.
  2. Top-k chunks fetched from ChromaDB.
  3. Chunks injected into the system prompt as "past records".
  4. Kimi answers — now aware of POWL history, LASR lessons, active positions.
"""

import os
import sys
import argparse
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "rag"))
sys.path.insert(0, str(_REPO_ROOT / "agent"))

from retriever import retrieve, format_context_for_claude  # noqa: E402
from llm_client import chat as _llm_chat, get_api_key as _get_api_key, DEFAULT_MODEL as _DEFAULT_MODEL  # noqa: E402


SYSTEM_PROMPT_WITH_RAG = """You are Finzora AI — Zeynel's autonomous portfolio management assistant.

In this conversation, the section "İlgili Geçmiş Kayıtlar (RAG)" supplies real
past trades, closed swing lessons, and prior decisions. Use that data:

1. Look for repeating patterns: if the same ticker has had multiple losses, say so.
2. Stay consistent with prior lessons (e.g. "do not chase crisis rallies").
3. Watch the balance of positive vs negative examples.
4. Don't speculate — if a claim isn't supported by the RAG, say "geçmiş veri yok".

Mandatory evidence tags (write them in Turkish, verbatim):
- KESİN: from RAG data, verified number.
- MUHTEMEL: strong inferential evidence.
- SPEKÜLATİF: opinion or guess.

Final answer MUST be in Turkish — plain, professional, no fluff."""


def ask_with_context(
    query: str,
    top_k: int = 5,
    filter: dict = None,
    model: str = None,
    max_tokens: int = 1500,
) -> dict:
    """
    Query + RAG + AI → yanıt.

    Returns: {
        "query": str,
        "hits": list,        # retrieved chunks
        "context": str,      # format_context_for_claude output
        "response": str,     # AI's answer
        "error": str or None
    }
    """
    result = {
        "query": query,
        "hits": [],
        "context": "",
        "response": "",
        "error": None,
    }

    # 1. RAG retrieval
    try:
        hits = retrieve(query, top_k=top_k, filter=filter)
        result["hits"] = hits
    except Exception as e:
        result["error"] = f"RAG hata: {e}"
        return result

    if not hits:
        result["context"] = "(Geçmiş kayıt bulunamadı)"
    else:
        result["context"] = format_context_for_claude(hits, max_chars=4000)

    # 2. LLM call (Kimi via OpenRouter)
    if not _get_api_key():
        result["error"] = "OPENROUTER_API_KEY (ya da ANTHROPIC_API_KEY) tanımsız. Sadece retrieval yapıldı."
        return result

    used_model = model or _DEFAULT_MODEL

    # System prompt = main identity + RAG context
    system = SYSTEM_PROMPT_WITH_RAG + "\n\n" + result["context"]

    try:
        resp = _llm_chat(
            system=system,
            user=query,
            model=used_model,
            max_tokens=max_tokens,
            temperature=0.3,
            apply_language_policy=False,  # SYSTEM_PROMPT already enforces Turkish output
        )
        result["response"] = resp.text
        try:
            from observability import log_claude_call  # noqa
            log_claude_call(
                mode="rag_query",
                model=used_model,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                duration_ms=0,
                success=True,
                context_chars=len(system) + len(query),
                decisions_count=0,
            )
        except Exception:
            pass
    except Exception as e:
        result["error"] = f"LLM hata: {e}"

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="Sorgu")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--symbol", help="Metadata filtresi: sembol")
    ap.add_argument("--type", help="event_type filtresi")
    ap.add_argument("--portfoy", help="portfoy filtresi")
    ap.add_argument("--show-context", action="store_true", help="RAG context'i bastır")
    ap.add_argument("--model", default=None, help="Default: KIMI_MODEL env or moonshotai/kimi-k2-thinking")
    ap.add_argument("--max-tokens", type=int, default=1500)
    args = ap.parse_args()

    # Filter
    filters = {}
    if args.symbol:
        filters["symbol"] = args.symbol
    if args.type:
        filters["event_type"] = args.type
    if args.portfoy:
        filters["portfoy"] = args.portfoy
    where = None
    if len(filters) == 1:
        where = filters
    elif len(filters) > 1:
        where = {"$and": [{k: v} for k, v in filters.items()]}

    result = ask_with_context(
        query=args.query,
        top_k=args.top_k,
        filter=where,
        model=args.model,
        max_tokens=args.max_tokens,
    )

    print("=" * 60)
    print(f"SORU: {result['query']}")
    if where:
        print(f"FİLTRE: {where}")
    print("=" * 60)

    if args.show_context:
        print("\n### RAG CONTEXT ###")
        print(result["context"])
        print("\n### /CONTEXT ###\n")

    print(f"\nRAG sonuçları: {len(result['hits'])} chunk")
    for i, h in enumerate(result["hits"][:3], 1):
        print(f"  #{i} skor={h['score']:.3f} [{h['metadata'].get('event_type')}] "
              f"{h['metadata'].get('symbol', '')}")

    if result["error"]:
        print(f"\n⚠️ {result['error']}")
    else:
        print("\n" + "=" * 60)
        print("LLM YANITI")
        print("=" * 60)
        print(result["response"])


if __name__ == "__main__":
    main()
