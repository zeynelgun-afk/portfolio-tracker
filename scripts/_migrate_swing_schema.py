#!/usr/bin/env python3
"""
Swing Şema Migration — TEK SEFERLİK
======================================
active.json içindeki alan isimlerini canonical şemaya hizalar.
closed.json canonical şemasıyla uyumlu hale getirir.

Canonical alan isimleri (closed.json'da olduğu gibi):
  giris_fiyati   (giris_fiyat değil)
  cikis_fiyati   (cikis_fiyat değil)
  kar_zarar_yuzde (pnl_pct değil)
  tutulan_gun    (hold_days değil)
  ders           (dersler değil, tekil)
  sonuc          (KAZANÇ/ZARAR/NOTR)

active.json: mevcut 5 pozisyon migrate edilir
closed.json: dokunulmaz (zaten canonical)
"""

import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE = REPO_ROOT / "data" / "swing" / "active.json"
BACKUP = REPO_ROOT / "data" / "swing" / f"active.json.bak-{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def migrate_active():
    with open(ACTIVE, encoding="utf-8") as f:
        data = json.load(f)

    # Backup
    with open(BACKUP, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Backup: {BACKUP}")

    pozlar = data.get("aktif_pozisyonlar", [])
    migrated = 0

    # Alan eşleştirmesi: eski → yeni canonical
    FIELD_MAP = {
        "giris_fiyat": "giris_fiyati",
        "pnl_pct": "kar_zarar_yuzde",  # Active'te mevcut anlık P/L
        # tutulan_gun zaten doğru
    }

    for p in pozlar:
        changed = False
        for old_key, new_key in FIELD_MAP.items():
            if old_key in p and new_key not in p:
                p[new_key] = p.pop(old_key)
                changed = True
            elif old_key in p and new_key in p:
                # İkisi de varsa: yeni'yi koru, eski'yi sil
                p.pop(old_key)
                changed = True
        if changed:
            migrated += 1

    data["aktif_pozisyonlar"] = pozlar
    data["son_guncelleme"] = datetime.now().isoformat()
    data["_schema_version"] = 2  # Canonical schema

    with open(ACTIVE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Migrated {migrated}/{len(pozlar)} aktif pozisyon")
    for p in pozlar:
        print(f"  {p.get('sembol')}: giris_fiyati={p.get('giris_fiyati')}, kar_zarar_yuzde={p.get('kar_zarar_yuzde')}")


if __name__ == "__main__":
    migrate_active()
    print("\n✅ Migration tamam. active.json canonical şemaya hizalandı.")
