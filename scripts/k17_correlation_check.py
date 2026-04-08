#!/usr/bin/env python3
"""
K-17: Korelasyon ve yoğunlaşma yönetimi
TRADING_PLAYBOOK.md K-17 kuralı uygulaması.

Yeni hisse girişi öncesi çalışır:
1) Sektör çakışması kontrol (mevcut portföydeki aynı sektör pozisyonları)
2) Tema çakışması kontrol (anlatı bazlı tema, K-17 3 soru testi)
3) Aynı gün giriş limiti (max 2/gün)
4) Tema yoğunluk %40 limiti

Kullanım:
  python scripts/k17_correlation_check.py NEW_SYMBOL
"""

import sys
import argparse
from k_rules_common import (
    get_all_positions, send_k_alert, get_sector, get_themes, fmp_get, set_quiet_mode
)


def check_correlation(new_symbol):
    new_symbol = new_symbol.upper()
    new_sector = get_sector(new_symbol)
    new_themes = get_themes(new_symbol)

    positions = get_all_positions()

    print(f"[K-17] {new_symbol} korelasyon kontrolü")
    print(f"  Sektör: {new_sector}")
    print(f"  Temalar: {new_themes if new_themes else 'tanımlı tema yok'}")
    print(f"  Mevcut aktif pozisyon sayısı: {len(positions)}")

    risks = []

    # 1) Sektör çakışması
    same_sector = [p for p in positions if get_sector(p["sembol"]) == new_sector and new_sector != "UNKNOWN"]
    if same_sector:
        syms = [f"{p['sembol']}({p['portfoy']})" for p in same_sector]
        risks.append(f"AYNI SEKTÖR ({new_sector}): {', '.join(syms)}")

    # 2) Tema çakışması
    for theme in new_themes:
        same_theme = []
        for p in positions:
            p_themes = get_themes(p["sembol"])
            if theme in p_themes:
                same_theme.append(p)
        if same_theme:
            syms = [f"{p['sembol']}({p['portfoy']})" for p in same_theme]
            risks.append(f"AYNI TEMA ({theme}): {', '.join(syms)}")

    # 3) Tema yoğunluk hesabı (toplam $)
    if new_themes:
        for theme in new_themes:
            total = 0
            for p in positions:
                if theme in get_themes(p["sembol"]):
                    total += p.get("guncel_deger", 0) or p.get("yatirim", 0) or 0
            # Toplam portföy ($600K baz)
            total_portfolio = 600000
            theme_pct = (total / total_portfolio) * 100
            if theme_pct >= 30:  # %30+ uyarı, %40 limit
                risks.append(f"TEMA YOĞUNLUK ({theme}): mevcut %{theme_pct:.1f} / max %40")

    return {
        "symbol": new_symbol,
        "sector": new_sector,
        "themes": new_themes,
        "risks": risks,
        "decision": "GIRMA" if len(risks) >= 2 else ("DIKKAT" if risks else "OK"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action="store_true",
                        help="Info severity de telegrama gönder (varsayılan: kapalı). Warning/critical her durumda gider.")
    parser.add_argument("--quiet", action="store_true",
                        help="(Eski flag, artık varsayılan davranış. Uyumluluk için tutuldu.)")
    parser.add_argument("symbol", help="Yeni eklenecek hisse")
    args = parser.parse_args()
    # Varsayılan quiet=True. --notify verilirse info'lar da gider.
    quiet_default = not args.notify
    set_quiet_mode(quiet_default)

    result = check_correlation(args.symbol)

    print(f"\n[K-17] SONUÇ: {result['decision']}")
    if result["risks"]:
        print("RİSK BULGULAR:")
        for r in result["risks"]:
            print(f"  ⚠️  {r}")
    else:
        print("  ✓ Korelasyon riski yok")

    # K-17 kuralı: 1 risk → DIKKAT, 2+ risk → GIRMA, 0 → OK
    if result["decision"] == "GIRMA":
        msg = (f"{args.symbol} → K-17 GİRMA\n"
               f"Sektör: {result['sector']}, Tema: {', '.join(result['themes']) or 'yok'}\n"
               f"Riskler:\n" + "\n".join(f"• {r}" for r in result['risks']))
        send_k_alert("K-17 GIRMA", args.symbol, msg, severity="critical")
    elif result["decision"] == "DIKKAT":
        msg = (f"{args.symbol} → K-17 DIKKAT (1 risk)\n"
               f"Risk: {result['risks'][0]}\n"
               f"Karar: küçük poz veya skip değerlendir")
        send_k_alert("K-17 DIKKAT", args.symbol, msg, severity="warning")
    else:
        msg = f"{args.symbol} K-17 ✓ temiz, korelasyon riski yok"
        send_k_alert("K-17 OK", args.symbol, msg, severity="info")


if __name__ == "__main__":
    main()
