# -*- coding: utf-8 -*-
"""
Theme Filter — gunun aktif tema-ici hisseleri (whitelist).

Iki kaynagi birlestirir:
- data/macro_intelligence.json: gunluk LLM tabanli dominant_temalar (guc_skoru >= macro_min_score)
- data/theme_scores.json: haftalik performans skoru (skor >= weekly_min_score)

Cikti: tema-ici hisse seti + ticker -> [tema_etiket] meta. swing_entry_engine
bunu okuyup once tema havuzunu tarar, ardindan alpha_scan ile tamamlar; ayrica
tema-ici hisselere kalite skoru bonusu uygular.

Public API:
    load_active_theme_universe(macro_min_score=5, weekly_min_score=6, max_age_hours=36) -> dict
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MACRO_PATH = REPO_ROOT / "data" / "macro_intelligence.json"
TRACKER_SCORES_PATH = REPO_ROOT / "data" / "theme_scores.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _load_tracker_themes() -> dict:
    try:
        from theme_tracker import TEMALAR  # type: ignore
        return TEMALAR
    except Exception:
        return {}


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _add(meta: dict, ticker: str, etiket: str) -> None:
    sym = (ticker or "").strip().upper()
    if not sym:
        return
    bucket = meta.setdefault(sym, [])
    if etiket and etiket not in bucket:
        bucket.append(etiket)


def _read_macro(min_score: int, max_age_hours: int, meta: dict) -> tuple[bool, float | None]:
    if not MACRO_PATH.exists():
        return False, None
    try:
        data = json.load(open(MACRO_PATH, encoding="utf-8"))
    except Exception:
        return False, None

    yas_saat: float | None = None
    ts = _parse_iso(data.get("date") or data.get("tarih", ""))
    if ts is not None:
        now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
        yas_saat = (now - ts).total_seconds() / 3600.0
        if yas_saat > max_age_hours:
            return False, yas_saat

    temalar = data.get("dominant_themes") or data.get("dominant_temalar") or []
    eklendi = False
    for tema in temalar:
        try:
            score = tema.get("strength_score") or tema.get("güç_skoru") or tema.get("guc_skoru", 0)
            if int(score) < min_score:
                continue
        except (TypeError, ValueError):
            continue
        etiket = tema.get("theme_name") or tema.get("tema_adi") or "tema"
        evren = (tema.get("stock_universe") or tema.get("hisse_evreni")
                 or tema.get("suggested_tickers") or tema.get("önerilen_hisseler")
                 or tema.get("onerilen_hisseler") or [])
        for sym in evren:
            _add(meta, sym, etiket)
            eklendi = True
    return eklendi, yas_saat


def _read_tracker(min_score: int, meta: dict) -> bool:
    if not TRACKER_SCORES_PATH.exists():
        return False
    try:
        data = json.load(open(TRACKER_SCORES_PATH, encoding="utf-8"))
    except Exception:
        return False

    skorlar = data.get("temalar") or {}
    if not skorlar:
        return False

    tema_def = _load_tracker_themes()
    eklendi = False
    for key, info in skorlar.items():
        try:
            if int(info.get("skor", 0)) < min_score:
                continue
        except (TypeError, ValueError):
            continue
        etiket = info.get("ad") or key
        semboller = (tema_def.get(key) or {}).get("semboller") or []
        for sym in semboller:
            _add(meta, sym, etiket)
            eklendi = True
    return eklendi


def load_active_theme_universe(
    macro_min_score: int = 5,
    weekly_min_score: int = 6,
    max_age_hours: int = 36,
) -> dict:
    """Tema-ici hisseleri ve etiket meta'sini birlestirip dondurur.

    Bos kaynak/parse hatasi durumunda sessizce gecer; sistem alpha_scan fallback
    ile cagrildigi yerde calismaya devam etmelidir.
    """
    meta: dict[str, list[str]] = {}
    macro_kullanildi, yas_saat = _read_macro(macro_min_score, max_age_hours, meta)
    tracker_kullanildi = _read_tracker(weekly_min_score, meta)

    return {
        "tema_hisseleri": set(meta.keys()),
        "tema_meta": meta,
        "kaynak_durumu": {
            "macro_kullanildi": macro_kullanildi,
            "tracker_kullanildi": tracker_kullanildi,
            "macro_yas_saat": yas_saat,
        },
    }


if __name__ == "__main__":
    r = load_active_theme_universe()
    print(f"Tema hisseleri ({len(r['tema_hisseleri'])}): {sorted(r['tema_hisseleri'])[:20]}")
    coklu = [(t, m) for t, m in r["tema_meta"].items() if len(m) >= 2]
    print(f"Coklu etiketli ({len(coklu)}): {coklu[:5]}")
    print(f"Kaynak durumu: {r['kaynak_durumu']}")
