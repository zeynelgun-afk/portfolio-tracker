#!/usr/bin/env python3
"""
Agresif portföy fırsat tarama wrapper'ı.
score_agresif'i uygular; sektör çeşitliliği bonusu YOK (agresif odaklı portföy).

Kullanım:
  python scripts/portfolio_scan_aggressive.py SEMBOL1,SEMBOL2,...
  python scripts/portfolio_scan_aggressive.py --mevcut
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_scan_common as psc

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT_PATH = REPO_ROOT / "data" / "portfolios" / "aggressive.json"
PORTFOY = "agresif"


def mevcut_pozisyonlar():
    if not PORT_PATH.exists():
        return []
    with open(PORT_PATH) as f:
        p = json.load(f)
    return [pos.get("sembol", "") for pos in p.get("pozisyonlar", [])
            if not str(pos.get("sembol", "")).startswith("_")]


def tara(sym, catalyst_override=None):
    data = psc.get_full_data(sym, with_valuation=True)
    if not data or not data.get("price"):
        return None
    score, detail = psc.score_agresif(data, catalyst_override=catalyst_override)
    karar = psc.get_decision(score, PORTFOY)
    return {"symbol": sym, "data": data, "score": score, "detail": detail, "karar": karar}


def basli_rapor(r):
    d = r["data"]
    print(f"\n=== {r['symbol']} — AGRESİF ===")
    print(f"  Fiyat: ${d.get('price',0):.2f}  |  P/E: {d.get('pe',0):.1f}  |  "
          f"ROIC: {d.get('roic_pct',0):.1f}%  |  RSI: {d.get('rsi_14',0):.0f}")
    print(f"  Momentum — 1M: {d.get('m1m',0):+.1f}%, 3M: {d.get('m3m',0):+.1f}%, 6M: {d.get('m6m',0):+.1f}%")
    print("  Skor detay:")
    for x in r["detail"]:
        print(f"    • {x}")
    eş = psc.THRESHOLDS[PORTFOY]
    print(f"  SKOR: {r['score']}  |  Eşik: EKLE≥{eş['ekle']}, İZLE≥{eş['izle']}  |  KARAR: {r['karar']}")


def main():
    sembols = mevcut_pozisyonlar()
    print(f"[AGRESİF] Mevcut {len(sembols)} pozisyon: {', '.join(sembols) if sembols else '(yok, %100 nakit)'}")

    if len(sys.argv) < 2 or sys.argv[1] == "--mevcut":
        return

    arg = sys.argv[1]
    tarananlar = [s.strip().upper() for s in arg.split(",") if s.strip()]
    print(f"\n[AGRESİF] {len(tarananlar)} sembol taranıyor: {', '.join(tarananlar)}")

    sonuc = []
    for s in tarananlar:
        r = tara(s)
        if r:
            basli_rapor(r)
            sonuc.append(r)

    if sonuc:
        print(f"\n{'='*60}")
        print(f"  AGRESİF TARAMA ÖZETİ")
        print(f"{'='*60}")
        print(f"  {'sembol':7s} | {'skor':>5s} | karar")
        print(f"  {'─'*7} | {'─'*5} | {'─'*6}")
        for r in sorted(sonuc, key=lambda x: -x["score"]):
            print(f"  {r['symbol']:7s} | {r['score']:>5d} | {r['karar']}")


if __name__ == "__main__":
    main()
