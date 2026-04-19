#!/usr/bin/env python3
"""
Finzora RAG — Context'li Claude Çağrısı
=========================================
Kullanıcı sorgusu → RAG retrieve → Claude API → yanıt.

KULLANIM:
  python scripts/rag/claude_with_context.py "POWL için ne düşünüyorsun?"
  python scripts/rag/claude_with_context.py "Son kriz rallilerinde hangi dersler var?" --top-k 8
  python scripts/rag/claude_with_context.py "AI tedarik zinciri" --symbol COHR --top-k 5

MANTIK:
  1. Sorgu Voyage ile embed edilir
  2. ChromaDB'den top-k chunk çekilir
  3. Chunk'lar Claude'un system prompt'una "geçmiş kayıt" olarak inject edilir
  4. Claude yanıt verir — artık POWL geçmişini, LASR dersini, aktif pozisyonları bilir
"""

import os
import sys
import argparse
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "rag"))
sys.path.insert(0, str(_REPO_ROOT / "agent"))

from retriever import retrieve, format_context_for_claude  # noqa: E402


SYSTEM_PROMPT_WITH_RAG = """Sen Finzora AI'ın — Zeynel'in otonom portföy yönetim asistanısın.

Bu konuşmada sana "İlgili Geçmiş Kayıtlar (RAG)" bölümünde gerçek trade geçmişi,
kapatılmış swing dersleri ve kararlar veriliyor. Bu verileri dikkate al:

1. Tekrar eden pattern'lere bak: aynı sembolde birden çok kayıp varsa söyle
2. Geçmiş derslerle çelişmediğinden emin ol (örn. "kriz rallisini kovalama" gibi)
3. Pozitif/negatif örneklerin dengesine bak
4. Spekülatif olma — geçmiş veride olmayan iddialarda "geçmiş veri yok" de

Etiketler zorunlu:
- KESİN: RAG verisi, doğrulanmış rakam
- MUHTEMEL: güçlü kanıta dayalı çıkarım
- SPEKÜLATİF: yorum, tahmin

Türkçe, sade, profesyonel yanıt ver."""


def ask_with_context(
    query: str,
    top_k: int = 5,
    filter: dict = None,
    model: str = "claude-opus-4-7",
    max_tokens: int = 1500,
) -> dict:
    """
    Query + RAG + Claude → yanıt.

    Returns: {
        "query": str,
        "hits": list,        # retrieved chunks
        "context": str,      # format_context_for_claude output
        "response": str,     # Claude's answer
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

    # 2. Claude çağrısı
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        result["error"] = "ANTHROPIC_API_KEY tanımsız. Sadece retrieval yapıldı."
        return result

    try:
        import anthropic
    except ImportError:
        result["error"] = "anthropic paketi yok. pip install anthropic"
        return result

    # System prompt = ana kimlik + RAG context
    system = SYSTEM_PROMPT_WITH_RAG + "\n\n" + result["context"]

    try:
        client = anthropic.Anthropic(api_key=anthropic_key)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": query}],
        )
        result["response"] = resp.content[0].text
        # Observability logging (opsiyonel)
        try:
            from observability import log_claude_call  # noqa
            in_tok = getattr(resp.usage, "input_tokens", 0) if hasattr(resp, "usage") else 0
            out_tok = getattr(resp.usage, "output_tokens", 0) if hasattr(resp, "usage") else 0
            log_claude_call(
                mode="rag_query",
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                duration_ms=0,  # CLI'dan net ölçmedik
                success=True,
                context_chars=len(system) + len(query),
                decisions_count=0,
            )
        except Exception:
            pass
    except Exception as e:
        result["error"] = f"Claude hata: {e}"

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="Sorgu")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--symbol", help="Metadata filtresi: sembol")
    ap.add_argument("--type", help="event_type filtresi")
    ap.add_argument("--portfoy", help="portfoy filtresi")
    ap.add_argument("--show-context", action="store_true", help="RAG context'i bastır")
    ap.add_argument("--model", default="claude-opus-4-7")
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
        print("CLAUDE YANITI")
        print("=" * 60)
        print(result["response"])


if __name__ == "__main__":
    main()
