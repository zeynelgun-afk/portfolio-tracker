#!/usr/bin/env python3
"""
K-20: Sektör RS dead cat bounce filtresi
TRADING_PLAYBOOK.md K-20 kuralı uygulaması.

Hisse'nin sektör ETF'i SPY'a karşı RS20 < 0 VE RS10 > 0 ise → swing girişi YOK.
Yorum: sektör orta vade zayıf + kısa vade sıçramış = dead cat bounce.

Hesaplama:
- RS = sektörETF_kapanış(bugün) / SPY_kapanış(bugün)
- RS20 = (RS_bugün - RS_20iş_önce) / RS_20iş_önce × 100
- RS10 = (RS_bugün - RS_10iş_önce) / RS_10iş_önce × 100

Kullanım:
  python scripts/k20_rs_filter.py SCAN_RESULTS.json
  python scripts/k20_rs_filter.py --check SYMBOL
  python scripts/k20_rs_filter.py --status        # 10 sektör RS durumu
"""

import sys
import json
import argparse
from k_rules_common import fmp_get, send_k_alert, get_sector


SEKTOR_ETFS = ["XLK", "XLC", "XLE", "XLI", "XLV", "XLF", "XLY", "XLU", "XLB", "XLRE"]


def get_close_history(symbol, days=30):
    """FMP historical-price-eod ile son N gün kapanış fiyatları."""
    data = fmp_get("historical-price-eod/full", {"symbol": symbol})
    if not data or not isinstance(data, list):
        return None
    bars = data[:days]
    return [b["close"] for b in bars]


def calc_rs(sektor_etf):
    """RS20 ve RS10 hesaplar. Negatif/None döndürürse hata."""
    sec_prices = get_close_history(sektor_etf, 25)
    spy_prices = get_close_history("SPY", 25)

    if not sec_prices or not spy_prices or len(sec_prices) < 21 or len(spy_prices) < 21:
        return None

    # Index 0 = en yeni
    rs_today = sec_prices[0] / spy_prices[0]
    rs_10 = sec_prices[10] / spy_prices[10]
    rs_20 = sec_prices[20] / spy_prices[20]

    rs10_pct = ((rs_today - rs_10) / rs_10) * 100
    rs20_pct = ((rs_today - rs_20) / rs_20) * 100

    return {
        "etf": sektor_etf,
        "rs10_pct": rs10_pct,
        "rs20_pct": rs20_pct,
        "is_dead_cat": rs20_pct < 0 and rs10_pct > 0,
    }


def get_all_sector_rs():
    """10 sektör için RS önbellek."""
    cache = {}
    for etf in SEKTOR_ETFS:
        rs = calc_rs(etf)
        if rs:
            cache[etf] = rs
    return cache


def filter_scan(scan_data, rs_cache):
    """Tarama sonuçlarından K-20 dead cat bounce hisselerini eler."""
    if isinstance(scan_data, dict):
        for key in ["sonuclar", "candidates", "izleme_listesi", "results", "swing"]:
            if key in scan_data and isinstance(scan_data[key], list):
                original = len(scan_data[key])
                kept = []
                removed = []
                for item in scan_data[key]:
                    sym = item.get("sembol") or item.get("symbol", "")
                    sector = get_sector(sym)
                    if sector in rs_cache and rs_cache[sector]["is_dead_cat"]:
                        removed.append((sym, sector, rs_cache[sector]))
                    else:
                        kept.append(item)
                scan_data[key] = kept
                return scan_data, original - len(kept), removed
    return scan_data, 0, []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scan_file", nargs="?")
    parser.add_argument("--check", help="Tek sembol kontrol")
    parser.add_argument("--status", action="store_true", help="10 sektör RS durumu")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.status:
        print("[K-20] 10 SEKTÖR RS DURUMU")
        print(f"{'ETF':6} {'RS20%':>8} {'RS10%':>8}  {'Durum':<25}")
        print("-" * 55)
        for etf in SEKTOR_ETFS:
            rs = calc_rs(etf)
            if rs:
                status = "⚠️ DEAD CAT" if rs["is_dead_cat"] else "OK"
                print(f"{etf:6} {rs['rs20_pct']:>+7.2f}% {rs['rs10_pct']:>+7.2f}%  {status}")
            else:
                print(f"{etf:6} veri yok")
        return

    if args.check:
        sym = args.check.upper()
        sector = get_sector(sym)
        if sector == "UNKNOWN":
            print(f"[K-20] {sym} sektörü bilinmiyor")
            return
        rs = calc_rs(sector)
        if not rs:
            print(f"[K-20] {sector} RS hesaplanamadı")
            return
        print(f"[K-20] {sym} ({sector}): RS20 %{rs['rs20_pct']:+.2f}, RS10 %{rs['rs10_pct']:+.2f}")
        if rs["is_dead_cat"]:
            msg = (f"{sym} ({sector}) → DEAD CAT BOUNCE\n"
                   f"RS20: {rs['rs20_pct']:+.2f}% (orta vade zayıflık)\n"
                   f"RS10: {rs['rs10_pct']:+.2f}% (kısa vade sıçrama)\n"
                   f"Karar: swing girişi YOK")
            send_k_alert("K-20 DEAD CAT", sym, msg, severity="warning")
            print(f"  ⚠️ DEAD CAT BOUNCE → swing girişi YOK")
            sys.exit(1)
        else:
            print(f"  ✓ OK, K-20 dead cat paterni yok")
        return

    if not args.scan_file:
        print("Kullanım: python k20_rs_filter.py SCAN_FILE.json | --check SYMBOL | --status")
        return

    # Dosya işleme
    try:
        with open(args.scan_file) as f:
            scan_data = json.load(f)
    except FileNotFoundError:
        print(f"[K-20] Dosya bulunamadı: {args.scan_file}")
        sys.exit(1)

    print("[K-20] Sektör RS önbelleği yükleniyor (10 sektör × FMP API)...")
    rs_cache = get_all_sector_rs()
    print(f"  ✓ {len(rs_cache)} sektör yüklendi")

    dead_cat_sectors = [k for k, v in rs_cache.items() if v["is_dead_cat"]]
    if dead_cat_sectors:
        print(f"  ⚠️ Dead cat sektörler: {dead_cat_sectors}")

    filtered_data, removed_count, removed_list = filter_scan(scan_data, rs_cache)

    print(f"\n[K-20] {args.scan_file}")
    print(f"  Eleyen: {removed_count} hisse")
    for sym, sector, rs in removed_list:
        print(f"    {sym} ({sector}) RS20={rs['rs20_pct']:+.2f}% RS10={rs['rs10_pct']:+.2f}%")

    if removed_count > 0:
        msg = f"Tarama K-20 filtre: {removed_count} hisse elendi (dead cat sektörler: {', '.join(dead_cat_sectors)})"
        send_k_alert("K-20 FILTER", "SCAN", msg, severity="info")

    if args.write:
        with open(args.scan_file, "w") as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)
        print("  ✓ Dosya güncellendi")
    else:
        print("  (--write ile dosyayı kalıcı yap)")


if __name__ == "__main__":
    main()
