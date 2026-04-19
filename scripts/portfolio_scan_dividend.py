#!/usr/bin/env python3
"""
Temettü portföy fırsat tarama wrapper'ı.
Mevcut temettü portföyünün sektör dağılımını yükleyip çeşitlilik bonusunu uygular.

Kullanım:
  python scripts/portfolio_scan_dividend.py SEMBOL1,SEMBOL2,...
  python scripts/portfolio_scan_dividend.py --mevcut
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_scan_common as psc

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT_PATH = REPO_ROOT / "data" / "portfolios" / "dividend.json"
PORTFOY = "temettü"


def mevcut_sektorler():
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
    score, detail = psc.score_temettü(
        data,
        existing_sectors=existing_sectors,
        catalyst_override=catalyst_override,
    )
    karar = psc.get_decision(score, PORTFOY)
    return {"symbol": sym, "data": data, "score": score, "detail": detail, "karar": karar}


def basli_rapor(r):
    d = r["data"]
    print(f"\n=== {r['symbol']} — TEMETTÜ ===")
    print(f"  Fiyat: ${d.get('price',0):.2f}  |  P/E: {d.get('pe',0):.1f}  |  "
          f"Yield: {d.get('yield_pct',0):.2f}%  |  Payout: {d.get('payout_pct',0):.1f}%")
    print(f"  ROIC: {d.get('roic_pct',0):.1f}%  |  FCF yield: {d.get('fcf_yield_pct',0):.1f}%  |  "
          f"RSI: {d.get('rsi_14',0):.0f}")
    print("  Skor detay:")
    for x in r["detail"]:
        print(f"    • {x}")
    eş = psc.THRESHOLDS[PORTFOY]
    print(f"  SKOR: {r['score']}  |  Eşik: EKLE≥{eş['ekle']}, İZLE≥{eş['izle']}  |  KARAR: {r['karar']}")


def main():
    sembols, sectors = mevcut_sektorler()
    print(f"[TEMETTÜ] Mevcut {len(sembols)} pozisyon: {', '.join(sembols) if sembols else '(yok)'}")
    print(f"[TEMETTÜ] Temsil edilen sektörler: {', '.join(sorted(sectors)) if sectors else '(yok)'}")

    if len(sys.argv) < 2 or sys.argv[1] == "--mevcut":
        return

    arg = sys.argv[1]
    tarananlar = [s.strip().upper() for s in arg.split(",") if s.strip()]
    print(f"\n[TEMETTÜ] {len(tarananlar)} sembol taranıyor: {', '.join(tarananlar)}")

    sonuc = []
    for s in tarananlar:
        r = tara(s, sectors)
        if r:
            basli_rapor(r)
            sonuc.append(r)

    if sonuc:
        print(f"\n{'='*60}")
        print(f"  TEMETTÜ TARAMA ÖZETİ")
        print(f"{'='*60}")
        print(f"  {'sembol':7s} | {'skor':>5s} | karar")
        print(f"  {'─'*7} | {'─'*5} | {'─'*6}")
        for r in sorted(sonuc, key=lambda x: -x["score"]):
            print(f"  {r['symbol']:7s} | {r['score']:>5d} | {r['karar']}")


if __name__ == "__main__":
    main()
