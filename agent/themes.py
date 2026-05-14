"""
Finzora AI — Themes Helper Module
==================================

AI türeyen tema kataloğu (`data/themes.json` v1.0) için ortak CRUD API.

Tema yaşam döngüsü:
    dogus → yukselis → olgun → sönüs → archived

Kullanım:
    from agent.themes import add_theme, update_score, get_active_themes

    add_theme(
        theme_id="AI_supply_chain",
        name="AI Tedarik Zinciri",
        description="AI training/inference için chip + ekipman + optik...",
        related_tickers=["AMAT", "KLAC", "ASML"],
        lifecycle_stage="olgun",
        momentum_score=75,
    )

14 May 2026 — Aşama 4a (tematik keşif altyapısı).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
THEMES_PATH = REPO_ROOT / "data" / "themes.json"
PORTFOLIO_PATH = REPO_ROOT / "data" / "portfolio.json"

LIFECYCLE_STAGES = ["dogus", "yukselis", "olgun", "sönüs"]
DEFAULT_MOMENTUM_THRESHOLD_DYING = 30  # 30 altı = sönüş eşiği


# ────────────────────────────── I/O ──────────────────────────────


def load() -> dict:
    """themes.json'u yükle. Dosya yoksa default yapı döndür."""
    if not THEMES_PATH.exists():
        return _empty_themes()
    try:
        return json.loads(THEMES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_themes()


def save(data: dict) -> None:
    """themes.json'a yaz."""
    data["_son_guncelleme"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    THEMES_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _empty_themes() -> dict:
    return {
        "_son_guncelleme": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "_aciklama": "Finzora AI — AI türeyen aktif tema kataloğu",
        "_schema_version": "1.0",
        "_lifecycle_stages": LIFECYCLE_STAGES,
        "themes": {},
        "archived_themes": [],
    }


def _normalize_id(s: str) -> str:
    """'AI Tedarik Zinciri' → 'ai_tedarik_zinciri'."""
    s = s.lower().strip()
    # Türkçe karakterleri normalize et
    repl = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c", "İ": "i"}
    for tr, ascii_ in repl.items():
        s = s.replace(tr, ascii_)
    # Boşluk → underscore, alfanumerik dışı kaldır
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


# ────────────────────────────── Read ──────────────────────────────


def get_theme(theme_id: str) -> Optional[dict]:
    """Bir temayı oku. Yoksa None."""
    return load().get("themes", {}).get(theme_id)


def all_themes(stage_filter: Optional[list[str]] = None) -> dict:
    """Tüm aktif temaları döndür. stage_filter verilirse filtreler."""
    data = load()
    themes = data.get("themes", {})
    if stage_filter:
        return {tid: t for tid, t in themes.items()
                if t.get("lifecycle_stage") in stage_filter}
    return themes


def get_active_themes() -> dict:
    """Aktif temalar (dogus/yukselis/olgun, sönüs hariç)."""
    return all_themes(stage_filter=["dogus", "yukselis", "olgun"])


def get_dying_themes() -> dict:
    """Sönüş aşamasındaki temalar."""
    return all_themes(stage_filter=["sönüs"])


def get_tickers_by_theme(theme_id: str) -> list[str]:
    """Bir temaya ait ticker'lar."""
    t = get_theme(theme_id)
    return t.get("related_tickers", []) if t else []


def get_themes_for_ticker(symbol: str) -> list[str]:
    """Bir ticker'ın bağlı olduğu tema id'lerini döndür."""
    symbol = symbol.upper()
    themes_dict = load().get("themes", {})
    return [tid for tid, t in themes_dict.items()
            if symbol in [s.upper() for s in t.get("related_tickers", [])]]


def get_portfolio_theme_map() -> dict:
    """Portföydeki her hisse için bağlı temaları döndür: {sym: [theme_id, ...]}."""
    if not PORTFOLIO_PATH.exists():
        return {}
    try:
        d = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        result = {}
        for p in d.get("positions", []):
            sym = p.get("symbol", "").upper()
            if sym:
                result[sym] = get_themes_for_ticker(sym)
        return result
    except (json.JSONDecodeError, OSError):
        return {}


# ────────────────────────────── Write ──────────────────────────────


def add_theme(
    theme_id: Optional[str] = None,
    name: str = "",
    description: str = "",
    related_tickers: Optional[list[str]] = None,
    lifecycle_stage: str = "yukselis",
    momentum_score: float = 50,
    signals: Optional[dict] = None,
    evidence: Optional[list[dict]] = None,
    source: str = "ai_thematic_discovery",
) -> dict:
    """
    Tema ekle veya güncelle. theme_id verilmezse name'den türetilir.

    - Tema zaten varsa: related_tickers'a yeni eklemeler birleşir,
      momentum_score güncellenir (history'e eklenir), evidence eklenir.
    - Yeni temaysa: yeni entry oluşturulur.
    """
    if not theme_id and name:
        theme_id = _normalize_id(name)
    if not theme_id:
        return {"action": "skipped", "reason": "empty theme_id and name"}

    if lifecycle_stage not in LIFECYCLE_STAGES:
        lifecycle_stage = "yukselis"

    data = load()
    now_iso = datetime.now(timezone.utc).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")

    if theme_id in data["themes"]:
        # Update mode
        t = data["themes"][theme_id]
        if name and not t.get("name"):
            t["name"] = name
        if description and not t.get("description"):
            t["description"] = description
        if related_tickers:
            existing = set(t.get("related_tickers", []))
            t["related_tickers"] = sorted(existing | set(s.upper() for s in related_tickers))
        # Lifecycle değişimi varsa kaydet
        if lifecycle_stage and lifecycle_stage != t.get("lifecycle_stage"):
            t["lifecycle_stage"] = lifecycle_stage
        # Score history
        t["momentum_score"] = momentum_score
        history = t.setdefault("score_history", [])
        history.append({"date": today, "score": momentum_score, "stage": lifecycle_stage})
        # En son 30 günlük tarih bırak (overflow'u önle)
        t["score_history"] = history[-30:]
        if signals:
            t.setdefault("signals", {}).update(signals)
        if evidence:
            ev_list = t.setdefault("evidence", [])
            ev_list.extend(evidence)
            t["evidence"] = ev_list[-20:]  # son 20 evidence
        t["updated_at"] = now_iso
        save(data)
        return {"action": "updated", "theme_id": theme_id}

    # New theme
    data["themes"][theme_id] = {
        "id": theme_id,
        "name": name or theme_id,
        "description": description,
        "created_at": now_iso,
        "updated_at": now_iso,
        "lifecycle_stage": lifecycle_stage,
        "momentum_score": momentum_score,
        "score_history": [{"date": today, "score": momentum_score, "stage": lifecycle_stage}],
        "signals": signals or {},
        "related_tickers": sorted(set(s.upper() for s in (related_tickers or []))),
        "evidence": evidence or [],
        "source": source,
    }
    save(data)
    return {"action": "added", "theme_id": theme_id}


def update_score(theme_id: str, score: float, stage: Optional[str] = None,
                 signals: Optional[dict] = None) -> dict:
    """Momentum skoru güncelle. Stage verilirse lifecycle da değişir."""
    data = load()
    if theme_id not in data["themes"]:
        return {"action": "skipped", "reason": "theme not found"}
    t = data["themes"][theme_id]
    t["momentum_score"] = score
    if stage and stage in LIFECYCLE_STAGES:
        t["lifecycle_stage"] = stage
    today = datetime.now().strftime("%Y-%m-%d")
    history = t.setdefault("score_history", [])
    history.append({
        "date": today, "score": score,
        "stage": stage or t.get("lifecycle_stage", "yukselis"),
    })
    t["score_history"] = history[-30:]
    if signals:
        t.setdefault("signals", {}).update(signals)
    t["updated_at"] = datetime.now(timezone.utc).isoformat()
    save(data)
    return {"action": "scored", "theme_id": theme_id, "score": score}


def update_lifecycle(theme_id: str, stage: str, reason: str = "") -> dict:
    """Lifecycle aşamasını değiştir."""
    if stage not in LIFECYCLE_STAGES:
        return {"action": "skipped", "reason": f"invalid stage: {stage}"}
    data = load()
    if theme_id not in data["themes"]:
        return {"action": "skipped", "reason": "theme not found"}
    t = data["themes"][theme_id]
    old_stage = t.get("lifecycle_stage")
    t["lifecycle_stage"] = stage
    t["updated_at"] = datetime.now(timezone.utc).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    history = t.setdefault("score_history", [])
    history.append({
        "date": today, "score": t.get("momentum_score", 0),
        "stage": stage, "transition_reason": reason,
    })
    t["score_history"] = history[-30:]
    save(data)
    return {"action": "lifecycle_changed", "theme_id": theme_id,
            "from": old_stage, "to": stage}


def archive_theme(theme_id: str, reason: str = "ended") -> dict:
    """Temayı archive et — themes'tan çıkar, archived_themes'a taşı."""
    data = load()
    if theme_id not in data["themes"]:
        return {"action": "skipped", "reason": "theme not found"}
    t = data["themes"].pop(theme_id)
    t["archived_at"] = datetime.now(timezone.utc).isoformat()
    t["archive_reason"] = reason
    data["archived_themes"].append(t)
    save(data)
    return {"action": "archived", "theme_id": theme_id}


# ────────────────────────────── CLI ──────────────────────────────


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        # Listele
        d = load()
        print(f"Themes v{d.get('_schema_version','?')}")
        print(f"Active themes: {len(d['themes'])}")
        print(f"Archived: {len(d['archived_themes'])}")
        print()
        for tid, t in sorted(d["themes"].items(),
                              key=lambda kv: -kv[1].get("momentum_score", 0)):
            stage = t.get("lifecycle_stage", "?")
            score = t.get("momentum_score", 0)
            tickers = t.get("related_tickers", [])
            print(f"  [{stage:9}] {tid:30} score={score:>5.0f} ({len(tickers)} ticker)")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "show" and len(sys.argv) >= 3:
        t = get_theme(sys.argv[2])
        print(json.dumps(t, indent=2, ensure_ascii=False) if t else "Tema bulunamadı")
    elif cmd == "active":
        for tid, t in get_active_themes().items():
            print(f"  [{t.get('lifecycle_stage','?')}] {tid}: score={t.get('momentum_score',0)}")
    elif cmd == "dying":
        d = get_dying_themes()
        if not d:
            print("Sönüş aşamasında tema yok.")
        for tid, t in d.items():
            print(f"  [sönüs] {tid}: score={t.get('momentum_score',0)} tickers={t.get('related_tickers',[])}")
    elif cmd == "ticker" and len(sys.argv) >= 3:
        themes = get_themes_for_ticker(sys.argv[2])
        print(f"{sys.argv[2].upper()} → temalar: {themes}")
    elif cmd == "portfolio":
        m = get_portfolio_theme_map()
        for sym, themes in sorted(m.items()):
            print(f"  {sym:6} → {themes}")
    else:
        print("Kullanım: python -m agent.themes [list | active | dying | show ID | ticker SYM | portfolio]")
