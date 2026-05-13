#!/usr/bin/env python3
"""
K-24 VCP Detector — Backtest

Mevcut kapanmış swing trade'lerin entry_date'inde geriye dönük VCP skorunu
hesaplar ve VCP grubunun ortalama getirisini karşılaştırır.

K-24 hipotezi: VCP STRONG ✅ olanlar baseline'a göre +%2+ avantaj sağlar.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from statistics import mean, median, stdev

# agent/ klasörünü path'e ekle (vcp_detector kendi içinde fmp_client'ı yükleyecek)
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "agent"))

from vcp_detector import detect_vcp  # noqa: E402


def get_day_before(date_str: str) -> str:
    """2026-02-04 → 2026-02-03 (entry günü öncesi)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Pazartesi girişse Cuma'ya geri al
    prev = dt - timedelta(days=1)
    while prev.weekday() >= 5:  # 5=Cmt, 6=Pz
        prev -= timedelta(days=1)
    return prev.strftime("%Y-%m-%d")


def run_backtest():
    closed = json.load(open("data/swing/closed.json"))
    trades = closed["kapatilan_pozisyonlar"]

    print(f"Toplam closed trade: {len(trades)}")
    print(f"Backtest başlıyor...\n")

    results = []
    for i, t in enumerate(trades, 1):
        symbol = t["sembol"]
        entry_date = t["giris_tarihi"]
        pnl = t["kar_zarar_yuzde"]
        days = t["tutulan_gun"]

        # Entry günü öncesi VCP skoru (look-ahead bias yok)
        as_of = get_day_before(entry_date)

        try:
            vcp = detect_vcp(symbol, as_of_date=as_of)
            status = vcp.get("vcp_status", "ERROR")
            score = vcp.get("vcp_score", 0)
            pivot_dist = vcp.get("pivot_distance_pct")
        except Exception as e:
            status = "ERROR"
            score = 0
            pivot_dist = None
            print(f"  ⚠️ {symbol} hata: {e}")

        results.append({
            "symbol": symbol,
            "entry_date": entry_date,
            "as_of": as_of,
            "pnl_pct": pnl,
            "hold_days": days,
            "vcp_status": status,
            "vcp_score": score,
            "pivot_dist": pivot_dist,
        })

        print(f"[{i:2}/{len(trades)}] {symbol:6} {entry_date} → {status:7} skor:{score:3} | sonuç: {pnl:+6.2f}% ({days}g)")
        time.sleep(0.1)  # FMP throttle güvencesi

    return results


def analyze(results):
    print("\n" + "="*70)
    print("VCP BACKTEST ANALİZİ")
    print("="*70)

    by_status = {"STRONG": [], "WEAK": [], "NONE": [], "ERROR": []}
    for r in results:
        by_status.setdefault(r["vcp_status"], []).append(r["pnl_pct"])

    print(f"\n{'Grup':10} {'N':>3} {'Ort':>8} {'Med':>8} {'Min':>8} {'Max':>8} {'Win%':>6} {'StdDev':>8}")
    print("-"*70)

    baseline_returns = [r["pnl_pct"] for r in results if r["vcp_status"] != "ERROR"]
    if baseline_returns:
        bm = mean(baseline_returns)
        bmd = median(baseline_returns)
        bwin = sum(1 for x in baseline_returns if x > 0) / len(baseline_returns) * 100
        bstd = stdev(baseline_returns) if len(baseline_returns) > 1 else 0
        print(f"{'BASELINE':10} {len(baseline_returns):>3} {bm:>7.2f}% {bmd:>7.2f}% {min(baseline_returns):>7.2f}% {max(baseline_returns):>7.2f}% {bwin:>5.1f}% {bstd:>7.2f}")

    for status in ["STRONG", "WEAK", "NONE", "ERROR"]:
        returns = by_status[status]
        if not returns:
            print(f"{status:10} {0:>3}    (örnek yok)")
            continue
        n = len(returns)
        m = mean(returns)
        med = median(returns)
        win = sum(1 for x in returns if x > 0) / n * 100
        std = stdev(returns) if n > 1 else 0
        marker = ""
        if status in ("STRONG", "WEAK") and baseline_returns:
            diff = m - bm
            marker = f"  Δ baseline: {diff:+.2f}%"
        print(f"{status:10} {n:>3} {m:>7.2f}% {med:>7.2f}% {min(returns):>7.2f}% {max(returns):>7.2f}% {win:>5.1f}% {std:>7.2f}{marker}")

    print("\nK-24 HİPOTEZ TESTİ:")
    print("-" * 70)
    strong = by_status["STRONG"]
    weak = by_status["WEAK"]
    none_ = by_status["NONE"]
    vcp_yes = strong + weak  # K-24 ✅ (STRONG + WEAK)
    vcp_no = none_           # K-24 ❌

    if vcp_yes and vcp_no:
        adv = mean(vcp_yes) - mean(vcp_no)
        print(f"VCP ✅ (STRONG+WEAK, n={len(vcp_yes)}): ort {mean(vcp_yes):+.2f}%")
        print(f"VCP ❌ (NONE, n={len(vcp_no)}): ort {mean(vcp_no):+.2f}%")
        print(f"AVANTAJ: {adv:+.2f}% {'✅ HİPOTEZ DOĞRULANDI (≥+2%)' if adv >= 2 else '⚠️ HİPOTEZ ZAYIF' if adv >= 0 else '❌ HİPOTEZ REDDEDİLDİ'}")
    else:
        print("Yetersiz örnek")

    # Detay: VCP score vs pnl scatter
    print("\nVCP SKOR — PNL KORELASYON:")
    print("-" * 70)
    valid = [(r["vcp_score"], r["pnl_pct"]) for r in results if r["vcp_status"] != "ERROR"]
    if len(valid) >= 5:
        n = len(valid)
        sx = sum(x for x,y in valid)
        sy = sum(y for x,y in valid)
        sxy = sum(x*y for x,y in valid)
        sxx = sum(x*x for x,y in valid)
        syy = sum(y*y for x,y in valid)
        try:
            r = (n*sxy - sx*sy) / (((n*sxx - sx*sx) * (n*syy - sy*sy)) ** 0.5)
            print(f"Pearson r = {r:+.3f}  (n={n})")
            if abs(r) < 0.2: interp = "ZAYIF korelasyon"
            elif abs(r) < 0.4: interp = "ORTA korelasyon"
            else: interp = "GÜÇLÜ korelasyon"
            print(f"Yorum: {interp} ({'pozitif' if r>0 else 'negatif'})")
        except (ZeroDivisionError, ValueError):
            print("Korelasyon hesaplanamadı")

    # Detay tablo
    print("\nTÜM TRADE'LER (skor sırasıyla):")
    print("-" * 70)
    print(f"{'SEMBOL':7} {'TARIH':11} {'STATUS':7} {'SKOR':>4} {'PNL%':>7} {'GUN':>4}")
    for r in sorted(results, key=lambda x: -x["vcp_score"]):
        if r["vcp_status"] == "ERROR":
            continue
        print(f"{r['symbol']:7} {r['entry_date']:11} {r['vcp_status']:7} {r['vcp_score']:>4} {r['pnl_pct']:>+7.2f} {r['hold_days']:>4}")


if __name__ == "__main__":
    results = run_backtest()
    Path("notes/k24_backtest_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    analyze(results)
    print("\nDetay: notes/k24_backtest_results.json")
