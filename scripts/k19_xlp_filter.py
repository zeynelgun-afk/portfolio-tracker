#!/usr/bin/env python3
"""
K-19: XLP swing dışlama
TRADING_PLAYBOOK.md K-19 kuralı uygulaması.

XLP sektöründeki hisseler swing trade'den otomatik elenir.
- Tütün: MO, PM
- Gıda/içecek: PEP, KO, KDP, MDLZ, GIS, K, HSY, MNST, CAG, CPB, KHC
- Perakende: WMT, COST
- Ev ürünleri: PG, CL, CLX, KMB, CHD, EL, NWL
- Diğer: SYY, ADM, BG, TSN, HRL

Kullanım:
  python scripts/k19_xlp_filter.py SCAN_RESULTS.json   # JSON tarama dosyası
  python scripts/k19_xlp_filter.py --check SYMBOL       # tek sembol kontrol
"""

import sys
import json
import argparse
from k_rules_common import send_k_alert, get_sector


XLP_HISSELERI = {
    # Tütün
    "MO", "PM",
    # Gıda/içecek
    "PEP", "KO", "KDP", "MDLZ", "GIS", "K", "HSY", "MNST", "CAG", "CPB", "KHC",
    # Perakende
    "WMT", "COST",
    # Ev ürünleri
    "PG", "CL", "CLX", "KMB", "CHD", "EL", "NWL",
    # Diğer
    "SYY", "ADM", "BG", "TSN", "HRL",
}


def is_xlp(symbol):
    """K-19 XLP listesi VEYA SECTOR_MAP/profile kontrolü."""
    sym = symbol.upper()
    if sym in XLP_HISSELERI:
        return True
    if get_sector(sym) == "XLP":
        return True
    return False


def filter_scan_results(scan_data):
    """Tarama sonuçlarından XLP hisseleri eler. List veya dict struct'ı destekler."""
    if isinstance(scan_data, dict):
        # Dict struct: candidates / sonuclar / izleme_listesi vb.
        for key in ["sonuclar", "candidates", "izleme_listesi", "results", "swing"]:
            if key in scan_data and isinstance(scan_data[key], list):
                original = len(scan_data[key])
                filtered = [item for item in scan_data[key] if not is_xlp(item.get("sembol") or item.get("symbol", ""))]
                removed = [item.get("sembol") or item.get("symbol", "") for item in scan_data[key] if is_xlp(item.get("sembol") or item.get("symbol", ""))]
                scan_data[key] = filtered
                return scan_data, original - len(filtered), removed
        return scan_data, 0, []
    elif isinstance(scan_data, list):
        original = len(scan_data)
        filtered = [item for item in scan_data if not is_xlp(item if isinstance(item, str) else (item.get("sembol") or item.get("symbol", "")))]
        removed = [item if isinstance(item, str) else (item.get("sembol") or item.get("symbol", "")) for item in scan_data if is_xlp(item if isinstance(item, str) else (item.get("sembol") or item.get("symbol", "")))]
        return filtered, original - len(filtered), removed
    return scan_data, 0, []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scan_file", nargs="?", help="JSON tarama dosyası yolu")
    parser.add_argument("--check", help="Tek sembol kontrol")
    parser.add_argument("--write", action="store_true", help="Dosyayı güncelle")
    args = parser.parse_args()

    if args.check:
        sym = args.check.upper()
        result = is_xlp(sym)
        print(f"[K-19] {sym} → {'YASAK (XLP)' if result else 'OK (XLP değil)'}")
        if result:
            send_k_alert("K-19 XLP YASAK", sym, f"{sym} XLP sektörü, swing girişi yasak. Portföy pozisyonu olarak izinli.", severity="warning")
        sys.exit(1 if result else 0)

    if not args.scan_file:
        print("Kullanım: python k19_xlp_filter.py SCAN_FILE.json veya --check SYMBOL")
        print(f"\nK-19 XLP listesi ({len(XLP_HISSELERI)} hisse):")
        print(f"  {sorted(XLP_HISSELERI)}")
        return

    # Dosya işleme
    try:
        with open(args.scan_file) as f:
            scan_data = json.load(f)
    except FileNotFoundError:
        print(f"[K-19] Dosya bulunamadı: {args.scan_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[K-19] JSON hatası: {e}")
        sys.exit(1)

    filtered_data, removed_count, removed_symbols = filter_scan_results(scan_data)

    print(f"[K-19] {args.scan_file}")
    print(f"  Eleyen: {removed_count} hisse")
    if removed_symbols:
        print(f"  XLP listesinden çıkarılan: {removed_symbols}")
        msg = f"Tarama K-19 filtre: {removed_count} XLP hissesi elendi: {', '.join(removed_symbols)}"
        send_k_alert("K-19 FILTER", "SCAN", msg, severity="info")

    if args.write:
        with open(args.scan_file, "w") as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Dosya güncellendi")
    else:
        print(f"  (--write ile dosyayı kalıcı yap)")


if __name__ == "__main__":
    main()
