# -*- coding: utf-8 -*-
"""
PORTFOY HIZLANDIRMA ANALIZI
============================
Her portfoyun gercek getirisi vs yıllık hedef (+%50-80) karsilastirmasi.

Kullanim:
  python scripts/portfolio_pacing.py            # Konsola yaz
  python scripts/portfolio_pacing.py --save     # reports/pacing/'a md kaydet
  python scripts/portfolio_pacing.py --json     # JSON ozet (data/pacing_summary.json)

Output:
- Gerçek vs hedef yıllık getiri
- Portföy bazinda detay
- Düzeltme önerileri
"""
import json, csv, sys, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))

# Hedef parametreler
HEDEF_DUSUK = 50  # Yıllık %50
HEDEF_YUKSEK = 80  # Yıllık %80
NAKIT_MAX = 10  # %10 (memory rule)


def portfoy_hesabi(pf_data: dict) -> dict:
    """Tek portfoyun mevcut/baslangic/getiri hesabi"""
    bas = pf_data.get("baslangic_sermaye", 0) or pf_data.get("baslangic_deger", 0) or 0
    
    # Pozisyon değeri
    pos_deger = 0
    for poz in pf_data.get("pozisyonlar", []):
        sym = poz.get("sembol")
        if sym in (None, "_template"):
            continue
        adet = poz.get("adet", 0) or 0
        cf = poz.get("guncel_fiyat", 0) or 0
        pos_deger += adet * cf
    
    # Nakit
    nakit_obj = pf_data.get("nakit", 0)
    if isinstance(nakit_obj, dict):
        nakit = nakit_obj.get("miktar", 0) or 0
    else:
        nakit = float(nakit_obj or 0)
    
    mevcut = pos_deger + nakit
    getiri_pct = ((mevcut - bas) / bas * 100) if bas else 0
    nakit_pct = (nakit / mevcut * 100) if mevcut else 0
    
    # Pozisyon sayısı
    poz_say = sum(1 for p in pf_data.get("pozisyonlar", []) 
                   if p.get("sembol") not in (None, "_template"))
    
    return {
        "baslangic": bas,
        "mevcut": mevcut,
        "pozisyon_deger": pos_deger,
        "nakit": nakit,
        "nakit_pct": nakit_pct,
        "pozisyon_sayi": poz_say,
        "getiri_pct": getiri_pct,
    }


def analiz_yap(start_date: str = "2026-02-17") -> dict:
    today = datetime.now(TR).strftime("%Y-%m-%d")
    days = (datetime.strptime(today, "%Y-%m-%d") - 
            datetime.strptime(start_date, "%Y-%m-%d")).days
    year_pct = days / 365.0
    
    portfoyler = {}
    toplam_bas = 0
    toplam_mev = 0
    
    for p in ["balanced", "aggressive", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{p}.json"
        if not path.exists():
            continue
        d = json.load(open(path))
        h = portfoy_hesabi(d)
        h["yillik_proj"] = h["getiri_pct"] / year_pct if year_pct > 0 else 0
        portfoyler[p] = h
        toplam_bas += h["baslangic"]
        toplam_mev += h["mevcut"]
    
    top_getiri = ((toplam_mev - toplam_bas) / toplam_bas * 100) if toplam_bas else 0
    top_yillik = top_getiri / year_pct if year_pct > 0 else 0
    
    # Düzeltme önerileri
    oneriler = []
    for p, h in portfoyler.items():
        if h["nakit_pct"] > NAKIT_MAX:
            oneriler.append(
                f"🔴 {p}: %{h['nakit_pct']:.0f} nakit — kural ihlali (>%{NAKIT_MAX}). "
                f"${h['nakit']:,.0f} nakit kullanilmali"
            )
        if h["yillik_proj"] < 0:
            oneriler.append(
                f"🔴 {p}: Negatif yillik proj (%{h['yillik_proj']:.1f}) — strateji gozden gecirilmeli"
            )
        elif h["yillik_proj"] < HEDEF_DUSUK:
            oneriler.append(
                f"🟡 {p}: Yillik proj %{h['yillik_proj']:.1f} — alt hedef altinda (%{HEDEF_DUSUK})"
            )
    
    if top_yillik < HEDEF_DUSUK:
        oneriler.append(
            f"⚠️ Toplam yillik proj %{top_yillik:.1f} — alt hedef %{HEDEF_DUSUK}'in {HEDEF_DUSUK-top_yillik:.1f} puan altinda"
        )
    
    return {
        "tarih": today,
        "baslangic_tarihi": start_date,
        "gun_sayisi": days,
        "yil_oran": year_pct,
        "toplam_baslangic": toplam_bas,
        "toplam_mevcut": toplam_mev,
        "toplam_getiri_pct": top_getiri,
        "toplam_yillik_proj": top_yillik,
        "hedef_dusuk": HEDEF_DUSUK,
        "hedef_yuksek": HEDEF_YUKSEK,
        "portfoyler": portfoyler,
        "oneriler": oneriler,
    }


def yazdir_konsol(a: dict):
    print("=" * 70)
    print(f"PORTFOY HIZLANDIRMA ANALIZI — {a['tarih']}")
    print("=" * 70)
    print()
    print(f"Sistem yasi: {a['gun_sayisi']} gun ({a['yil_oran']*100:.1f}% yil)")
    print()
    print(f"{'Portfoy':12} {'Baslangic':>12} {'Mevcut':>12} {'Getiri':>10} {'Yillik':>10} {'Nakit%':>7}")
    print("-" * 70)
    for p, h in a["portfoyler"].items():
        print(f"{p:12} ${h['baslangic']:>11,.0f} ${h['mevcut']:>11,.0f} "
              f"{h['getiri_pct']:>+9.2f}% {h['yillik_proj']:>+9.1f}% {h['nakit_pct']:>5.1f}%")
    print("-" * 70)
    print(f"{'TOPLAM':12} ${a['toplam_baslangic']:>11,.0f} ${a['toplam_mevcut']:>11,.0f} "
          f"{a['toplam_getiri_pct']:>+9.2f}% {a['toplam_yillik_proj']:>+9.1f}%")
    print()
    print(f"HEDEF: Yıllık +%{a['hedef_dusuk']} - +%{a['hedef_yuksek']}")
    print(f"GERCEK: Yıllık +%{a['toplam_yillik_proj']:.1f}")
    if a["toplam_yillik_proj"] >= a["hedef_dusuk"]:
        print(f"DURUM: ✅ Alt hedef tutuldu")
    else:
        fark = a["hedef_dusuk"] - a["toplam_yillik_proj"]
        print(f"DURUM: ⚠️ Alt hedefin {fark:.1f} puan altinda")
    
    if a["oneriler"]:
        print()
        print("=== ONERILER ===")
        for o in a["oneriler"]:
            print(f"  {o}")


def md_rapor(a: dict) -> str:
    lines = [
        f"# Portfoy Hizlandirma Raporu — {a['tarih']}",
        "",
        f"**Sistem yasi:** {a['gun_sayisi']} gun ({a['yil_oran']*100:.1f}% yıl)",
        f"**Hedef:** Yıllık +%{a['hedef_dusuk']} - +%{a['hedef_yuksek']}",
        f"**Gercek:** Yıllık +%{a['toplam_yillik_proj']:.1f}",
        "",
        "## Portfoy Detay",
        "",
        "| Portfoy | Başlangıç | Mevcut | Getiri | Yıllık | Nakit% | Pozisyon |",
        "|---------|-----------|--------|--------|--------|--------|---|",
    ]
    for p, h in a["portfoyler"].items():
        lines.append(
            f"| {p} | ${h['baslangic']:,.0f} | ${h['mevcut']:,.0f} | "
            f"{h['getiri_pct']:+.2f}% | {h['yillik_proj']:+.1f}% | "
            f"{h['nakit_pct']:.1f}% | {h['pozisyon_sayi']} |"
        )
    lines.append(
        f"| **TOPLAM** | **${a['toplam_baslangic']:,.0f}** | **${a['toplam_mevcut']:,.0f}** | "
        f"**{a['toplam_getiri_pct']:+.2f}%** | **{a['toplam_yillik_proj']:+.1f}%** | — | — |"
    )
    
    if a["oneriler"]:
        lines.append("")
        lines.append("## Oneriler")
        for o in a["oneriler"]:
            lines.append(f"- {o}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="Md rapor kaydet")
    parser.add_argument("--json", action="store_true", help="JSON ozet kaydet")
    parser.add_argument("--start", default="2026-02-17", help="Başlangıç tarihi")
    args = parser.parse_args()
    
    a = analiz_yap(args.start)
    yazdir_konsol(a)
    
    if args.json:
        out = REPO_ROOT / "data" / "pacing_summary.json"
        with open(out, "w") as f:
            json.dump(a, f, ensure_ascii=False, indent=2)
        print(f"\nJSON: {out}")
    
    if args.save:
        out_dir = REPO_ROOT / "reports" / "pacing"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"pacing_{a['tarih']}.md"
        with open(out, "w") as f:
            f.write(md_rapor(a))
        print(f"\nMD: {out}")


if __name__ == "__main__":
    main()
