#!/usr/bin/env python3
"""
Portföy şema standartlaştırma migration
========================================
3 portföy JSON dosyasındaki pozisyon alanlarını tek şemaya sabitler.

Şema (22 alan — pozisyon başına):
  ZORUNLU:
    sembol, isim, sektor, adet, maliyet_baz, giris_tarihi,
    giris_fiyati, giris_nedeni, stop_loss, hedef_fiyat, durum

  HESAPLANAN (otomatik güncellenir):
    guncel_fiyat, guncel_deger, yatirim, kar_zarar, kar_zarar_yuzde,
    gunluk_degisim_yuzde, agirlik_yuzde, son_guncelleme

  STOP YÖNETİMİ:
    zirve_fiyat, stop_faz, stop_mesafe_pct,
    stop_aciklama (aggressive'den eklendi),
    stop_guncelleme (aggressive'den eklendi)

  KAYNAK İZLEME:
    cb_kaynak (balanced/dividend'den geldi; "kayit-yok" default)

TEK SEFERLİK — bir kez çalıştır, sonra arşive kaldır.
"""

import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIOS_DIR = REPO_ROOT / "data" / "portfolios"

# Kanonik şema — tüm pozisyonlarda bulunacak 24 alan
CANONICAL_FIELDS = [
    # Kimlik
    "sembol",
    "isim",
    "sektor",
    # Pozisyon
    "adet",
    "maliyet_baz",
    "yatirim",
    # Canlı
    "guncel_fiyat",
    "guncel_deger",
    "kar_zarar",
    "kar_zarar_yuzde",
    "gunluk_degisim_yuzde",
    "agirlik_yuzde",
    "son_guncelleme",
    # Giriş
    "giris_tarihi",
    "giris_fiyati",
    "giris_nedeni",
    "cb_kaynak",
    # Hedef & Stop
    "hedef_fiyat",
    "stop_loss",
    "zirve_fiyat",
    "stop_faz",
    "stop_mesafe_pct",
    "stop_aciklama",
    "stop_guncelleme",
    # Durum
    "durum",
]

# Default değerler
FIELD_DEFAULTS = {
    "cb_kaynak": "kayit-yok",
    "stop_aciklama": "",
    "stop_guncelleme": "",
    "stop_faz": 1,
    "zirve_fiyat": None,
    "stop_mesafe_pct": None,
    "durum": "✅ Normal",
}


def normalize_position(pos: dict) -> dict:
    """
    Tek pozisyonu kanonik şemaya uyar.
    - Eksik alanları default ile doldur
    - Fazla alanları LOG'la ama koru (veri kaybı yasak)
    """
    out = {}

    # Kanonik alanları sırayla ekle
    for f in CANONICAL_FIELDS:
        if f in pos:
            out[f] = pos[f]
        elif f in FIELD_DEFAULTS:
            out[f] = FIELD_DEFAULTS[f]
        else:
            # Henüz hesaplanmamış canlı alan → None
            out[f] = None

    # zirve_fiyat None ise mevcut fiyat veya giris_fiyati
    if out["zirve_fiyat"] is None:
        out["zirve_fiyat"] = (
            pos.get("guncel_fiyat") or pos.get("giris_fiyati") or 0
        )

    # stop_mesafe_pct hesapla (None ise)
    if out["stop_mesafe_pct"] is None:
        price = out.get("guncel_fiyat") or out.get("giris_fiyati")
        stop = out.get("stop_loss")
        if price and stop and price > 0:
            out["stop_mesafe_pct"] = round((price - stop) / price * 100, 2)

    # Şema dışı ekstra alanları sonda tut
    extras = {k: v for k, v in pos.items() if k not in CANONICAL_FIELDS}
    if extras:
        out["_ek_alanlar"] = extras

    return out


def migrate(portfolio_path: Path) -> dict:
    """Tek portföy dosyasını göç ettir. Rapor dict'i döner."""
    data = json.loads(portfolio_path.read_text(encoding="utf-8"))
    positions = data.get("pozisyonlar", [])

    report = {
        "dosya": portfolio_path.name,
        "pozisyon_sayisi": len(positions),
        "once": {},
        "sonra": {},
        "eklenen_alanlar": set(),
    }

    # Önce durumu
    if positions:
        report["once"] = {
            "ilk_pos_alan_sayisi": len(positions[0]),
            "ilk_pos_alanlar": sorted(positions[0].keys()),
        }

    # Migrate
    new_positions = []
    for pos in positions:
        missing = [f for f in CANONICAL_FIELDS if f not in pos]
        report["eklenen_alanlar"].update(missing)
        new_positions.append(normalize_position(pos))

    data["pozisyonlar"] = new_positions

    # _sema_versiyonu meta alanı
    data["_sema_versiyonu"] = "2026-04-17"

    # Sonra durumu
    if new_positions:
        report["sonra"] = {
            "ilk_pos_alan_sayisi": len(new_positions[0]),
            "ilk_pos_alanlar": sorted(new_positions[0].keys()),
        }

    portfolio_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report["eklenen_alanlar"] = sorted(report["eklenen_alanlar"])
    return report


def main():
    files = ["aggressive.json", "balanced.json", "dividend.json"]
    print(f"Migration başlatılıyor: {datetime.now().isoformat()}")
    print("=" * 60)

    for name in files:
        path = PORTFOLIOS_DIR / name
        if not path.exists():
            print(f"ATLA: {path} yok")
            continue

        report = migrate(path)
        print(f"\n📂 {report['dosya']}")
        print(f"   Pozisyon sayısı: {report['pozisyon_sayisi']}")
        before = report["once"].get("ilk_pos_alan_sayisi", 0)
        after = report["sonra"].get("ilk_pos_alan_sayisi", 0)
        print(f"   Alan sayısı: {before} → {after}")
        if report["eklenen_alanlar"]:
            print(f"   Eklenen alanlar: {report['eklenen_alanlar']}")

    print("\n" + "=" * 60)
    print("Migration tamamlandı.")


if __name__ == "__main__":
    main()
