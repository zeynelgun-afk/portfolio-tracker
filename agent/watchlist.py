"""
Finzora AI — Watchlist Helper Module
=====================================

Tek hisse havuzu (`data/watchlist.json` v2.0) için ortak CRUD API.
Tüm besleyiciler (analist_takip, fair_value_screener, tematik_keşif,
ai_orchestrator, manuel) bu modülü kullanır.

Kullanım:
    from agent.watchlist import add, remove, get, is_in_pool

    add(
        symbol="NVDA",
        source="analist_takip_strong_buy",
        rationale="3 analyst raise, avg +%8.5",
        tags=["AI", "semiconductor"],
        price=220.50,
    )

13 May 2026 — Aşama 3 (besleyiciler).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = REPO_ROOT / "data" / "watchlist.json"
PORTFOLIO_PATH = REPO_ROOT / "data" / "portfolio.json"

# Limit (yeni eklemeler buna takılır, eski tickerlar `_limit` aşılırsa
# `score` en düşük olanlardan arşivlenir — score yoksa eski tarihliden)
# 14 May 2026: 80 → 300 (tematik kaynaklar genişledi, daha geniş havuz)
DEFAULT_LIMIT = 300


# ────────────────────────────── I/O ──────────────────────────────


def load() -> dict:
    """watchlist.json'u yükle. Dosya yoksa default yapı döndür."""
    if not WATCHLIST_PATH.exists():
        return _empty_watchlist()
    try:
        return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_watchlist()


def save(data: dict) -> None:
    """watchlist.json'a yaz."""
    data["_son_guncelleme"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    WATCHLIST_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _empty_watchlist() -> dict:
    return {
        "_son_guncelleme": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "_aciklama": "Finzora AI tek hisse havuzu",
        "_limit": DEFAULT_LIMIT,
        "_schema_version": "2.0",
        "tickers": {},
        "archived": [],
        "excluded": [],
    }


# ────────────────────────────── Read ──────────────────────────────


def get(symbol: str) -> Optional[dict]:
    """Bir ticker'ı watchlist'ten oku. Yoksa None."""
    return load().get("tickers", {}).get(symbol.upper())


def all_symbols() -> list[str]:
    """Aktif watchlist'teki tüm sembolleri döndür."""
    return list(load().get("tickers", {}).keys())


def is_in_pool(symbol: str) -> bool:
    """Symbol watchlist'te (aktif) mi?"""
    return symbol.upper() in load().get("tickers", {})


def is_excluded(symbol: str) -> bool:
    """Symbol bilinçli olarak dışlanmış mı (excluded list)?"""
    return symbol.upper() in load().get("excluded", [])


def is_in_portfolio(symbol: str) -> bool:
    """Symbol açık pozisyonlarda mı (yani zaten elimizde, watchlist'e gerek yok)?"""
    if not PORTFOLIO_PATH.exists():
        return False
    try:
        d = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        return any(p.get("symbol", "").upper() == symbol.upper()
                   for p in d.get("positions", []))
    except (json.JSONDecodeError, OSError):
        return False


# ────────────────────────────── Write ──────────────────────────────


def add(
    symbol: str,
    source: str,
    rationale: str = "",
    tags: Optional[list[str]] = None,
    price: Optional[float] = None,
    score: Optional[float] = None,
    score_components: Optional[dict] = None,
) -> dict:
    """
    Watchlist'e bir ticker ekle veya günceller.

    - Symbol portföyde varsa: SKIP (zaten elde)
    - Symbol excluded'da varsa: SKIP (bilinçli dışlanmış)
    - Limit (_limit) doluysa: en düşük skorlu / en eski ticker arşivlenir
    - Symbol zaten watchlist'te varsa: rationale ve tags güncellenir,
      source ek olarak `sources` listesinde tutulur (multi-source destek)
    - `score` verilirse yeni eklemede direkt set edilir, mevcut girdide ise
      yüksek olan korunur (sinyal güçlenmesi).

    Returns:
        dict — {"action": "added"|"updated"|"skipped", "reason": "...", "symbol": "..."}
    """
    symbol = symbol.upper().strip()
    if not symbol:
        return {"action": "skipped", "reason": "empty symbol", "symbol": symbol}

    if is_in_portfolio(symbol):
        return {"action": "skipped", "reason": "already in portfolio", "symbol": symbol}
    if is_excluded(symbol):
        return {"action": "skipped", "reason": "in excluded list", "symbol": symbol}

    data = load()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Multi-source desteği: ticker zaten varsa source'u ekle
    if symbol in data["tickers"]:
        entry = data["tickers"][symbol]
        existing_sources = entry.get("sources", [entry.get("source", "")])
        if source not in existing_sources:
            existing_sources.append(source)
        entry["sources"] = existing_sources
        if rationale:
            existing_rats = entry.get("rationales", [entry.get("rationale", "")])
            if rationale not in existing_rats:
                existing_rats.append(rationale)
            entry["rationales"] = existing_rats
        if tags:
            entry["tags"] = list(set(entry.get("tags", []) + tags))
        if score_components:
            entry.setdefault("score_components", {}).update(score_components)
        # Score: yeni gelen >= mevcut ise güncelle (sinyal güçlenmesi)
        if score is not None:
            current_score = entry.get("score") or 0
            if score >= current_score:
                entry["score"] = score
                entry["score_updated_at"] = now_iso
        entry["last_updated"] = now_iso
        save(data)
        return {"action": "updated", "reason": "added source", "symbol": symbol,
                "sources": existing_sources}

    # Yeni ticker eklendiğinde limit kontrolü
    limit = data.get("_limit", DEFAULT_LIMIT)
    if len(data["tickers"]) >= limit:
        # En düşük skorlu / en eski ticker'ı arşivle (score yoksa added_at)
        candidates = list(data["tickers"].items())
        candidates.sort(
            key=lambda kv: (
                kv[1].get("score") if kv[1].get("score") is not None else -1,
                kv[1].get("added_at", ""),
            )
        )
        evict_sym, evict_entry = candidates[0]
        evict_entry["archived_at"] = now_iso
        evict_entry["archive_reason"] = "limit_eviction"
        data["archived"].append(evict_entry)
        del data["tickers"][evict_sym]

    # Yeni entry
    data["tickers"][symbol] = {
        "symbol": symbol,
        "added_at": now_iso,
        "added_price": price,
        "source": source,
        "sources": [source],
        "rationale": rationale,
        "rationales": [rationale] if rationale else [],
        "tags": tags or [],
        "score": score,
        "score_updated_at": now_iso if score is not None else None,
        "score_components": score_components or {},
        "last_news_check": None,
        "last_action_signal": None,
        "notes": "",
    }
    save(data)
    return {"action": "added", "reason": "new entry", "symbol": symbol}


def remove(symbol: str, reason: str = "manual") -> dict:
    """Watchlist'ten çıkar, archived'a taşı."""
    symbol = symbol.upper().strip()
    data = load()
    if symbol not in data["tickers"]:
        return {"action": "skipped", "reason": "not in watchlist", "symbol": symbol}
    entry = data["tickers"].pop(symbol)
    entry["archived_at"] = datetime.now(timezone.utc).isoformat()
    entry["archive_reason"] = reason
    data["archived"].append(entry)
    save(data)
    return {"action": "removed", "reason": reason, "symbol": symbol}


def exclude(symbol: str, reason: str = "manual") -> dict:
    """
    Symbol'u kalıcı olarak dışla — gelecekte besleyiciler eklemeye çalışsa
    da reddedilir. Eğer aktif watchlist'te varsa önce remove et.
    """
    symbol = symbol.upper().strip()
    data = load()
    if symbol in data["tickers"]:
        remove(symbol, reason=f"excluded ({reason})")
        data = load()
    if symbol not in data["excluded"]:
        data["excluded"].append(symbol)
        save(data)
    return {"action": "excluded", "reason": reason, "symbol": symbol}


def update_score(
    symbol: str,
    score: float,
    components: Optional[dict] = None,
) -> dict:
    """AI orchestrator scorla güncelle (0-100)."""
    symbol = symbol.upper().strip()
    data = load()
    if symbol not in data["tickers"]:
        return {"action": "skipped", "reason": "not in watchlist", "symbol": symbol}
    entry = data["tickers"][symbol]
    entry["score"] = score
    entry["score_updated_at"] = datetime.now(timezone.utc).isoformat()
    if components:
        entry.setdefault("score_components", {}).update(components)
    save(data)
    return {"action": "scored", "score": score, "symbol": symbol}


# ────────────────────────────── CLI ──────────────────────────────


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # Listele
        wl = load()
        print(f"Watchlist v{wl.get('_schema_version','?')}")
        print(f"Tickers: {len(wl['tickers'])} / {wl.get('_limit',DEFAULT_LIMIT)}")
        print(f"Archived: {len(wl['archived'])}")
        print(f"Excluded: {len(wl['excluded'])}")
        print()
        for sym, e in wl["tickers"].items():
            srcs = e.get("sources", [e.get("source", "?")])
            score = e.get("score")
            score_str = f"{score:>5.0f}" if score is not None else "  —  "
            print(f"  {sym:6} score={score_str} sources={','.join(srcs)} added={e.get('added_at','?')[:10]}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) >= 4:
        result = add(sys.argv[2], source="cli", rationale=" ".join(sys.argv[3:]))
        print(result)
    elif cmd == "remove" and len(sys.argv) >= 3:
        print(remove(sys.argv[2], reason="cli"))
    elif cmd == "exclude" and len(sys.argv) >= 3:
        print(exclude(sys.argv[2], reason="cli"))
    else:
        print(f"Kullanım: python -m agent.watchlist [add SYMBOL rationale | remove SYMBOL | exclude SYMBOL]")
