#!/usr/bin/env python3
"""
Dengeli portföy fırsat tarama wrapper'ı.
scripts/portfolio_scan_common.py'yi sarar, mevcut dengeli portföyün sektör
dağılımını otomatik yükleyip çeşitlilik bonusunu hesaba katar.

Kullanım:
  python scripts/portfolio_scan_balanced.py SEMBOL1,SEMBOL2,...
  python scripts/portfolio_scan_balanced.py --mevcut    # sadece mevcut portföy özeti
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_scan_common as psc

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT_PATH = REPO_ROOT / "data" / "portfolios" / "balanced.json"
PORTFOY = "dengeli"


def mevcut_sektorler():
    """Mevcut dengeli portföydeki sembolleri ve sektörlerini döndürür."""
    if not PORT_PATH.exists():
        return [], set()
    with open(PORT_PATH) as f:
        p = json.load(f)
    sembols = [pos.get("sembol", "") for pos in p.get("pozisyonlar", [])
               if not str(pos.get("sembol", "")).startswith("_")]
    sectors = set()
    for s in sembols:
        sec, _, _ = psc.get_sector_info(s)
        if sec != "UNKNOWN":
            sectors.add(sec)
    return sembols, sectors


def tara(sym, existing_sectors, catalyst_override=None):
    data = psc.get_full_data(sym, with_valuation=True)
    if not data or not data.get("price"):
        return None
    score, detail = psc.score_dengeli(
        data,
        existing_sectors=existing_sectors,
        catalyst_override=catalyst_override,
    )
    karar = psc.get_decision(score, PORTFOY)
    return {"symbol": sym, "data": data, "score": score, "detail": detail, "karar": karar}


def basli_rapor(r):
    d = r["data"]
    print(f"\n=== {r['symbol']} — DENGELİ ===")
    print(f"  Fiyat: ${d.get('price',0):.2f}  |  P/E: {d.get('pe',0):.1f}  |  "
          f"ROIC: {d.get('roic_pct',0):.1f}%  |  RSI: {d.get('rsi_14',0):.0f}  |  "
          f"6M: {d.get('m6m',0):+.1f}%")
    print("  Skor detay:")
    for x in r["detail"]:
        print(f"    • {x}")
    eş = psc.THRESHOLDS[PORTFOY]
    print(f"  SKOR: {r['score']}  |  Eşik: EKLE≥{eş['ekle']}, İZLE≥{eş['izle']}  |  KARAR: {r['karar']}")


def main():
    sembols, sectors = mevcut_sektorler()
    print(f"[DENGELİ] Mevcut {len(sembols)} pozisyon: {', '.join(sembols) if sembols else '(yok)'}")
    print(f"[DENGELİ] Temsil edilen sektörler: {', '.join(sorted(sectors)) if sectors else '(yok)'}")

    if len(sys.argv) < 2 or sys.argv[1] == "--mevcut":
        return

    arg = sys.argv[1]
    tarananlar = [s.strip().upper() for s in arg.split(",") if s.strip()]
    print(f"\n[DENGELİ] {len(tarananlar)} sembol taranıyor: {', '.join(tarananlar)}")

    sonuc = []
    for s in tarananlar:
        r = tara(s, sectors)
        if r:
            basli_rapor(r)
            sonuc.append(r)

    # Özet tablo
    if sonuc:
        print(f"\n{'='*60}")
        print(f"  DENGELİ TARAMA ÖZETİ")
        print(f"{'='*60}")
        print(f"  {'sembol':7s} | {'skor':>5s} | karar")
        print(f"  {'─'*7} | {'─'*5} | {'─'*6}")
        for r in sorted(sonuc, key=lambda x: -x["score"]):
            print(f"  {r['symbol']:7s} | {r['score']:>5d} | {r['karar']}")


if __name__ == "__main__":
    main()
