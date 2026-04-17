#!/usr/bin/env python3
"""
Finzora RAG — Indexer
=======================
events.jsonl + docs/ → ChromaDB.

Neyi indexler:
  1. logs/events.jsonl
     - trade event → doğal dil: "BUY POWL 50 @$22.50, portfoy=aggressive, neden=..."
     - Lessons içeren event'ler AYRI chunk olarak (daha zengin retrieval için)
  2. docs/*.md (opsiyonel, --include-docs flag ile)
     - TRADING_PLAYBOOK, K_RULES_QUICK_REF, SWING_SYSTEM_V2 vb.
     - Her başlık bölümü ayrı chunk

ÇIKTI:
  data/rag/chroma/  — ChromaDB persistent store

KULLANIM:
  python scripts/rag/indexer.py                    # Sadece events
  python scripts/rag/indexer.py --include-docs     # Events + docs
  python scripts/rag/indexer.py --rebuild          # Sıfırdan yeniden
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "rag"))
sys.path.insert(0, str(_REPO_ROOT / "agent"))

from embedder import embed_documents  # noqa: E402

EVENTS_JSONL = _REPO_ROOT / "logs" / "events.jsonl"
DOCS_DIR = _REPO_ROOT / "docs"
CHROMA_PATH = _REPO_ROOT / "data" / "rag" / "chroma"
CLOSED_JSON = _REPO_ROOT / "data" / "swing" / "closed.json"

COLLECTION_NAME = "finzora"


# ── Event → doğal dil metin ───────────────────────────────────────────────────

def event_to_text(event: dict) -> tuple[str, dict]:
    """
    Bir event'i embedding için uygun doğal dil metne çevir.
    Returns: (text, metadata)
    """
    etype = event.get("type", "?")
    ts = event.get("ts", "")

    meta = {
        "event_id": event.get("id", ""),
        "event_type": etype,
        "ts": ts,
        "date": ts[:10] if ts else "",
        "source": "events.jsonl",
        "backfill": bool(event.get("backfill", False)),
    }

    if etype == "trade":
        action = event.get("action", "?")
        sembol = event.get("sembol", "?")
        shares = event.get("shares", 0)
        price = event.get("price", 0)
        total = event.get("total", 0)
        portfoy = event.get("portfoy", "")
        reason = event.get("reason", "")
        pnl_pct = event.get("pnl_pct")
        lessons = event.get("lessons", "")

        parts = [
            f"[TRADE] {action} {sembol} {shares} adet @${price}",
            f"Toplam: ${total:.2f}" if total else "",
            f"Portfoy: {portfoy}" if portfoy else "",
            f"Tarih: {ts[:10]}" if ts else "",
            f"Neden: {reason}" if reason else "",
        ]
        if pnl_pct is not None:
            parts.append(f"K/Z: {pnl_pct}%")
        if lessons:
            parts.append(f"Ders: {lessons}")

        text = ". ".join(p for p in parts if p)
        meta.update({
            "symbol": sembol,
            "action": action,
            "portfoy": portfoy or "",
            "has_lessons": bool(lessons),
        })
        return text, meta

    elif etype == "decision":
        tip = event.get("tip", "?")
        sembol = event.get("sembol", "?")
        portfoy = event.get("portfoy", "")
        mode = event.get("mode", "")
        neden = event.get("neden", "")
        pct = event.get("pct", 0)
        hedef = event.get("hedef_fiyat")
        stop = event.get("stop")
        executed = event.get("executed", 0)

        parts = [
            f"[KARAR] {tip} {sembol} {pct}%",
            f"Portfoy: {portfoy}",
            f"Mod: {mode}" if mode else "",
            f"Neden: {neden}" if neden else "",
        ]
        if hedef:
            parts.append(f"Hedef: ${hedef}")
        if stop:
            parts.append(f"Stop: ${stop}")
        parts.append(f"Uygulandı: {'evet' if executed else 'hayır'}")

        text = ". ".join(p for p in parts if p)
        meta.update({
            "symbol": sembol,
            "tip": tip,
            "portfoy": portfoy or "",
            "executed": bool(executed),
        })
        return text, meta

    elif etype == "claude_call":
        mode = event.get("mode", "")
        in_tok = event.get("input_tokens", 0)
        out_tok = event.get("output_tokens", 0)
        cost = event.get("cost_usd", 0)
        dur = event.get("duration_ms", 0)
        dec = event.get("decisions_count", 0)
        success = event.get("success", 0)

        text = (
            f"[CLAUDE] Mod: {mode}, süre: {dur}ms, "
            f"input={in_tok} output={out_tok} token, "
            f"maliyet=${cost}, karar_sayısı={dec}, "
            f"başarılı: {'evet' if success else 'hayır'}"
        )
        meta.update({"mode": mode, "success": bool(success)})
        return text, meta

    elif etype == "fmp_call":
        endpoint = event.get("endpoint", "")
        status = event.get("status", 0)
        dur = event.get("duration_ms", 0)
        text = f"[FMP] {endpoint} status={status} süre={dur}ms"
        meta.update({"endpoint": endpoint, "status": status})
        return text, meta

    # Bilinmeyen tip
    return f"[{etype}] {json.dumps(event, ensure_ascii=False)[:300]}", meta


# ── swing/closed.json → ayrı lesson chunk'ları ────────────────────────────────

def closed_swings_as_lesson_chunks() -> list[tuple[str, dict]]:
    """
    data/swing/closed.json içindeki her kapatılmış pozisyon için
    AYRI bir "lesson" chunk üretir — retrieval daha iyi olsun.
    """
    chunks = []
    if not CLOSED_JSON.exists():
        return chunks

    try:
        data = json.loads(CLOSED_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"closed.json okunamadı: {e}")
        return chunks

    for p in data.get("kapatilan_pozisyonlar", []):
        sembol = p.get("sembol", "?")
        entry_date = p.get("giris_tarihi", "")
        exit_date = p.get("cikis_tarihi", "")
        entry_price = p.get("giris_fiyati", 0)
        exit_price = p.get("cikis_fiyati", 0)
        pnl_pct = p.get("kar_zarar_yuzde", 0)
        giris_nedeni = p.get("giris_nedeni", "")
        cikis_nedeni = p.get("cikis_nedeni", "")
        dersler = p.get("dersler") or p.get("lessons", "")
        scan_method = p.get("scan_method", "")

        parts = [
            f"[SWING DERS] {sembol}",
            f"Giriş: {entry_date} @ ${entry_price}",
            f"Çıkış: {exit_date} @ ${exit_price}",
            f"K/Z: {pnl_pct}%",
            f"Tarama: {scan_method}" if scan_method else "",
            f"Giriş tezi: {giris_nedeni}" if giris_nedeni else "",
            f"Çıkış nedeni: {cikis_nedeni}" if cikis_nedeni else "",
        ]
        if dersler:
            if isinstance(dersler, list):
                dersler = " | ".join(str(d) for d in dersler)
            parts.append(f"Ders: {dersler}")

        text = ". ".join(p for p in parts if p)
        meta = {
            "event_id": f"swing_lesson_{sembol}_{exit_date}",
            "event_type": "swing_lesson",
            "ts": exit_date + "T00:00:00Z" if exit_date else "",
            "date": exit_date,
            "source": "swing/closed.json",
            "symbol": sembol,
            "action": "LESSON",
            "portfoy": "swing",
            "pnl_pct": pnl_pct,
            "has_lessons": bool(dersler),
            "backfill": True,
        }
        chunks.append((text, meta))

    return chunks


# ── docs/*.md → başlık bazlı chunk'lar ────────────────────────────────────────

def docs_as_chunks(max_chunk_chars: int = 1500) -> list[tuple[str, dict]]:
    """
    docs/ içindeki .md dosyalarını `## ` başlıklarına göre böler.
    """
    chunks = []
    if not DOCS_DIR.exists():
        return chunks

    for md_path in sorted(DOCS_DIR.glob("*.md")):
        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # ## veya ### başlıklarında böl
        import re
        sections = re.split(r"\n(#{2,3} .+)\n", text)
        # [pre-heading text, heading, body, heading, body, ...]

        # İlk bölüm başlıksız olabilir
        doc_title = md_path.stem
        current_heading = doc_title
        current_body = sections[0] if sections else ""

        def flush(heading, body):
            body = body.strip()
            if len(body) < 50:  # çok kısaysa atla
                return
            # Çok uzunsa böl
            for i in range(0, len(body), max_chunk_chars):
                chunk_text = body[i : i + max_chunk_chars]
                text_with_title = f"[DOC: {doc_title} / {heading}]\n{chunk_text}"
                meta = {
                    "event_id": f"doc_{doc_title}_{heading[:30]}_{i // max_chunk_chars}",
                    "event_type": "doc",
                    "source": f"docs/{md_path.name}",
                    "doc_title": doc_title,
                    "heading": heading[:100],
                    "date": "",
                    "ts": "",
                }
                chunks.append((text_with_title, meta))

        flush(current_heading, current_body)

        i = 1
        while i < len(sections) - 1:
            heading = sections[i].lstrip("# ").strip()
            body = sections[i + 1] if i + 1 < len(sections) else ""
            flush(heading, body)
            i += 2

    return chunks


# ── Ana indexer ───────────────────────────────────────────────────────────────

def load_events(jsonl_path: Path) -> list[dict]:
    events = []
    if not jsonl_path.exists():
        return events
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events


def run_index(
    include_docs: bool = False,
    rebuild: bool = False,
    include_swing_lessons: bool = True,
) -> None:
    import chromadb

    # Koleksiyonu kur
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Eski koleksiyon silindi: {COLLECTION_NAME}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Finzora trade/karar geçmişi + docs"},
    )

    existing_ids = set()
    try:
        # Mevcut id'leri çek (incremental için)
        res = collection.get(limit=100000, include=[])
        existing_ids = set(res["ids"])
        print(f"Mevcut chunk sayısı: {len(existing_ids)}")
    except Exception as e:
        print(f"Mevcut id okunamadı: {e}")

    # Kaynak topla
    pending: list[tuple[str, dict]] = []

    # 1. events.jsonl
    events = load_events(EVENTS_JSONL)
    print(f"events.jsonl: {len(events)} event yüklendi")
    for e in events:
        text, meta = event_to_text(e)
        pending.append((text, meta))

    # 2. swing lessons (ayrı chunk olarak — daha zengin arama)
    if include_swing_lessons:
        swing_chunks = closed_swings_as_lesson_chunks()
        print(f"swing lessons: {len(swing_chunks)} chunk")
        pending.extend(swing_chunks)

    # 3. docs (opsiyonel)
    if include_docs:
        doc_chunks = docs_as_chunks()
        print(f"docs: {len(doc_chunks)} chunk")
        pending.extend(doc_chunks)

    print(f"\nToplam chunk (ham): {len(pending)}")

    # Incremental: zaten indexlenmiş id'leri atla
    new_items = [
        (text, meta) for text, meta in pending
        if meta.get("event_id") and meta["event_id"] not in existing_ids
    ]
    print(f"Yeni chunk (indexlenecek): {len(new_items)}")

    if not new_items:
        print("Yapılacak iş yok, çık.")
        return

    # Embed
    texts = [t for t, _ in new_items]
    metas = [m for _, m in new_items]
    ids = [m["event_id"] for m in metas]

    print(f"\nEmbedding üretiliyor... ({len(texts)} chunk)")
    embeddings, stats = embed_documents(texts, show_progress=True)
    print(f"Embed stats: {stats}")

    # ChromaDB'ye ekle (batch'ler halinde)
    ADD_BATCH = 500
    for i in range(0, len(ids), ADD_BATCH):
        j = min(i + ADD_BATCH, len(ids))
        collection.add(
            ids=ids[i:j],
            embeddings=embeddings[i:j],
            documents=texts[i:j],
            metadatas=metas[i:j],
        )
        print(f"ChromaDB: {j}/{len(ids)} eklendi")

    print(f"\n✓ Index tamam. Koleksiyon: {collection.count()} chunk")
    print(f"Voyage token harcaması: ~{stats['total_tokens']} token")
    # voyage-3-lite: $0.02/M token
    cost = stats["total_tokens"] / 1_000_000 * 0.02
    print(f"Tahmini maliyet: ~${cost:.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-docs", action="store_true", help="docs/*.md dahil et")
    ap.add_argument("--rebuild", action="store_true", help="Koleksiyonu sıfırdan kur")
    ap.add_argument("--no-swing-lessons", action="store_true", help="Swing dersleri ekleme")
    args = ap.parse_args()

    run_index(
        include_docs=args.include_docs,
        rebuild=args.rebuild,
        include_swing_lessons=not args.no_swing_lessons,
    )


if __name__ == "__main__":
    main()
