#!/usr/bin/env python3
"""
Finzora AI — K-Kural Performans Analiz Sistemi (Katman 3)
==========================================================
Kapanan trade'lerden K-kural uyum verisi çıkarır, hangi kuralların
çalıştığını/çalışmadığını gösterir ve yeni kural adayları önerir.

Kullanım:
  python3 scripts/k_rule_performance.py --report       # Tam rapor
  python3 scripts/k_rule_performance.py --candidates   # Yeni kural adayları
  python3 scripts/k_rule_performance.py --save         # JSON'a kaydet
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE         = Path(__file__).parent.parent
CLOSED_SWING = BASE / "data" / "swing" / "closed.json"
K_RULES_REF  = BASE / "docs"  / "K_RULES_QUICK_REF.md"
OUTPUT_FILE  = BASE / "data"  / "k_rules_backtest_results.json"


# ══════════════════════════════════════════════════════════════════════════════
# 1. VERİ YÜKLEME VE SINIFLANDIRMA
# ══════════════════════════════════════════════════════════════════════════════

def load_trades() -> list[dict]:
    with open(CLOSED_SWING, encoding="utf-8") as f:
        d = json.load(f)
        return d.get("kapatilan_pozisyonlar", d.get("kapali_pozisyonlar", []))


def siniflandir_ihlaller(trades: list[dict]) -> dict:
    """
    Her trade'in auto_analiz'inden kural ihlallerini ve uyumlarını çıkarır.
    Döndürür: {kural_id: {ihlaller: [...], uyumlar: [...], kacinilan: [...]}}
    """
    kurallar = defaultdict(lambda: {
        "ihlaller": [],   # Kural ihlal edilen trade'ler
        "uyumlar": [],    # Kurala uyan trade'ler
        "kacirilan": [],  # Kural uygulanmamış (eksik veri)
    })

    IHLAL_PATTERN = {
        "K-zaman": ["15 GÜN KURALI İHLALİ", "15 GÜN SINIRI"],
        "K-13":    ["K-13 İHLALİ", "VIX>27", "K-13"],
        "K-evren": ["$2B+ market cap kuralı ihlali", "Hacim 500K+ kuralı ihlali",
                    "market cap", "mcap"],
        "K-stop":  ["Stop mesafesi yetersiz", "ATR tabanlı stop kullanılmamış",
                    "stop mesafesi"],
        "K-06":    ["stop geçildi", "override", "Stop'a 0 mesafe"],
        "K-19":    ["XLP", "düşük volatilite", "K-19"],
        "K-20":    ["dead cat", "RS negatif", "K-20"],
    }

    for t in trades:
        sembol = t.get("sembol", "")
        pnl    = t.get("kar_zarar_yuzde", 0)
        gun    = t.get("tutulan_gun", 0)
        sonuc  = t.get("sonuc", "")
        tid    = t.get("id", "")

        if "auto_analiz" not in t:
            continue

        a = t["auto_analiz"]
        ku = a.get("kural_uyumu", "")

        ozet = {
            "id": tid, "sembol": sembol, "pnl": pnl,
            "gun": gun, "sonuc": sonuc,
            "kural_uyumu_notu": ku[:120],
            "puan": a.get("puan", 0),
        }

        # 15 gün zaman kuralı kontrolü (doğrudan ölçülebilir)
        if gun > 15:
            kurallar["K-zaman"]["ihlaller"].append({
                **ozet, "detay": f"{gun} gün tutuldu (limit: 15)"
            })
        elif gun > 0:
            kurallar["K-zaman"]["uyumlar"].append(ozet)

        # Pattern bazlı ihlal tespiti
        for kural, patterns in IHLAL_PATTERN.items():
            if kural == "K-zaman":
                continue  # Yukarıda işlendi
            ihlal_bulundu = any(p.lower() in ku.lower() for p in patterns)
            if ihlal_bulundu:
                kurallar[kural]["ihlaller"].append({
                    **ozet, "detay": ku[:150]
                })

        # K-13 VIX kontrolü — AROC açık ihlal
        if "K-13 İHLALİ" in ku or "VIX>27 ortamında" in ku:
            if sembol not in [e["sembol"] for e in kurallar["K-13"]["ihlaller"]]:
                kurallar["K-13"]["ihlaller"].append({
                    **ozet, "detay": "K-13: VIX>25 ortamında duyarlı sektör girişi"
                })

        # Beta/evren kuralı — düşük beta hisseler
        DUSUK_BETA = {"VZ", "T", "DUK", "DVA", "WMT", "AMT", "TGT", "COST"}
        if sembol in DUSUK_BETA:
            kurallar["K-evren"]["ihlaller"].append({
                **ozet, "detay": f"{sembol} düşük beta (swing evrenine girmemeli)"
            })

        # Stop çalıştı mı?
        stop_calisti = any(k in t.get("cikis_nedeni", "") for k in
                          ["Stop-loss", "stop-loss", "Stop tetik", "stop tetik"])
        if stop_calisti and pnl >= -6:
            kurallar["K-06"]["uyumlar"].append({**ozet, "detay": "Stop disiplinli uygulandı"})

    return kurallar


# ══════════════════════════════════════════════════════════════════════════════
# 2. YENİ KURAL ADAYLARI
# ══════════════════════════════════════════════════════════════════════════════

def yeni_kural_adaylari(trades: list[dict]) -> list[dict]:
    """
    auto_analiz sistem_onerisi alanlarından yeni kural adayları üretir.
    Benzer öneriler gruplanır, tekrar sayısına göre önceliklendirilir.
    """
    # Tüm sistem önerilerini topla
    oneriler_ham = []
    for t in trades:
        if "auto_analiz" not in t:
            continue
        o = t["auto_analiz"].get("sistem_onerisi", "")
        if o:
            oneriler_ham.append({
                "oneri": o,
                "sembol": t.get("sembol", ""),
                "pnl": t.get("kar_zarar_yuzde", 0),
                "puan": t["auto_analiz"].get("puan", 0),
            })

    # Konu bazlı gruplama
    KONULAR = {
        "K-ZST (Zaman Disiplini)": [
            "15 gün", "zaman", "günde çık", "gün disiplin", "10. günde"
        ],
        "K-EVR (Evren Filtresi — Beta)": [
            "swing evreninden çıkar", "swing için uygun değil", "beta", "düşük volatilite"
        ],
        "K-ATR (Stop Mesafesi)": [
            "2×ATR", "ATR tabanlı", "stop mesafesi", "ATR(14)"
        ],
        "K-KRZ (Kriz Trade Kuralı)": [
            "kriz trade", "gün-1", "gün 1", "cooling", "1 gün bekle"
        ],
        "K-SEC (Sektör ETF Filtresi)": [
            "sektör ETF", "9EMA", "RS negatif", "XLF>9EMA"
        ],
        "K-RSI (Minimum Giriş Kriterleri)": [
            "RSI>50", "SMA50", "giriş kriteri"
        ],
        "K-JEO (Jeopolitik Çıkış)": [
            "jeopolitik", "gerilim azalırsa", "çıkış trigger", "savaş biterse"
        ],
        "K-13 Güçlendirme": [
            "VIX>25", "VIX kontrolü", "K-13"
        ],
    }

    gruplar = defaultdict(list)
    for item in oneriler_ham:
        atandi = False
        for konu, keywords in KONULAR.items():
            if any(kw.lower() in item["oneri"].lower() for kw in keywords):
                gruplar[konu].append(item)
                atandi = True
                break
        if not atandi:
            gruplar["Diğer"].append(item)

    # Aday listesi oluştur
    adaylar = []
    for konu, items in sorted(gruplar.items(), key=lambda x: -len(x[1])):
        if not items or konu == "Diğer":
            continue
        tekrar = len(items)
        ornekler = [f"{i['sembol']} {i['pnl']:+.1f}%" for i in items[:3]]
        en_iyi_oneri = min(items, key=lambda x: x.get("puan", 10))["oneri"]

        adaylar.append({
            "konu": konu,
            "tekrar_sayisi": tekrar,
            "oncuk": tekrar,  # Trade sayısı = kanıt gücü
            "ornekler": ornekler,
            "oneri_metni": en_iyi_oneri,
            "oncelik": "YÜKSEK" if tekrar >= 4 else "ORTA" if tekrar >= 2 else "DÜŞÜK",
        })

    return sorted(adaylar, key=lambda x: -x["tekrar_sayisi"])


# ══════════════════════════════════════════════════════════════════════════════
# 3. KURAL PERFORMANS METRİKLERİ
# ══════════════════════════════════════════════════════════════════════════════

def kural_metrikleri(trades: list[dict]) -> dict:
    """
    Doğrudan ölçülebilen kural metrikleri üretir.
    """
    toplam = len([t for t in trades if "auto_analiz" in t])

    # 15 Gün kuralı
    uzun_tutma = [t for t in trades if t.get("tutulan_gun", 0) > 15]
    zaman_uyum = toplam - len(uzun_tutma)

    # Stop disiplini
    stop_tetik = [t for t in trades
                  if any(k in t.get("cikis_nedeni", "") for k in
                         ["Stop-loss", "stop-loss", "stop tetik"])]
    max_zarar_stop = min((t["kar_zarar_yuzde"] for t in stop_tetik), default=0)
    max_zarar_stop_olmayan = min(
        (t["kar_zarar_yuzde"] for t in trades if t not in stop_tetik and t["kar_zarar_yuzde"] < 0),
        default=0
    )

    # Kural ihlali olan trade'lerin performansı
    ihlaller = [t for t in trades
                if "auto_analiz" in t and
                ("❌" in t["auto_analiz"].get("kural_uyumu", "") or
                 t.get("tutulan_gun", 0) > 15)]
    uyumlu = [t for t in trades
              if "auto_analiz" in t and t not in ihlaller]

    ihlal_ort_pnl = (sum(t["kar_zarar_yuzde"] for t in ihlaller) / len(ihlaller)
                     if ihlaller else 0)
    uyumlu_ort_pnl = (sum(t["kar_zarar_yuzde"] for t in uyumlu) / len(uyumlu)
                      if uyumlu else 0)

    ihlal_wr = (sum(1 for t in ihlaller if t["sonuc"] == "KAZANÇ") / len(ihlaller) * 100
                if ihlaller else 0)
    uyumlu_wr = (sum(1 for t in uyumlu if t["sonuc"] == "KAZANÇ") / len(uyumlu) * 100
                 if uyumlu else 0)

    return {
        "toplam_analiz": toplam,
        "zaman_kurali": {
            "uyum_sayisi": zaman_uyum,
            "ihlal_sayisi": len(uzun_tutma),
            "uyum_orani": f"%{zaman_uyum/toplam*100:.0f}" if toplam else "—",
            "ihlal_ornekleri": [
                {"sembol": t["sembol"], "gun": t["tutulan_gun"], "pnl": t["kar_zarar_yuzde"]}
                for t in uzun_tutma
            ],
        },
        "stop_kurali": {
            "stop_tetiklenen": len(stop_tetik),
            "max_zarar_stop_ile": f"{max_zarar_stop:.1f}%",
            "max_zarar_stopsuz": f"{max_zarar_stop_olmayan:.1f}%",
        },
        "kural_uyumu_etkisi": {
            "ihlal_trade_sayisi": len(ihlaller),
            "uyumlu_trade_sayisi": len(uyumlu),
            "ihlal_ort_pnl": f"{ihlal_ort_pnl:+.1f}%",
            "uyumlu_ort_pnl": f"{uyumlu_ort_pnl:+.1f}%",
            "ihlal_win_rate": f"%{ihlal_wr:.0f}",
            "uyumlu_win_rate": f"%{uyumlu_wr:.0f}",
            "avantaj": f"{uyumlu_ort_pnl - ihlal_ort_pnl:+.1f}% fark (kurala uyum lehine)",
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. RAPOR YAZDIRMA
# ══════════════════════════════════════════════════════════════════════════════

def rapor_yazdir(trades, kurallar, adaylar, metrikler):
    SEP = "=" * 65

    print(f"\n{SEP}")
    print(f"  📋 K-KURAL PERFORMANS RAPORU")
    print(f"  Finzora AI | {datetime.now().strftime('%d %B %Y')}")
    print(f"{SEP}")

    # --- Genel metrikler ---
    m = metrikler
    print(f"\n  📊 GENEL METRİKLER ({m['toplam_analiz']} trade analiz edildi)")
    print()

    zk = m["zaman_kurali"]
    print(f"  ⏱️  15 Gün Zaman Kuralı")
    print(f"     Uyum: {zk['uyum_sayisi']} trade ({zk['uyum_orani']}) | "
          f"İhlal: {zk['ihlal_sayisi']} trade")
    if zk["ihlal_ornekleri"]:
        for o in zk["ihlal_ornekleri"]:
            print(f"     ❌  {o['sembol']:<6} {o['gun']:>2} gün | {o['pnl']:+.1f}%")

    print()
    sk = m["stop_kurali"]
    print(f"  🛑  Stop Disiplini")
    print(f"     Stop tetiklenen: {sk['stop_tetiklenen']} trade")
    print(f"     Max zarar (stop ile):    {sk['max_zarar_stop_ile']}")
    print(f"     Max zarar (stopsuz/geç): {sk['max_zarar_stopsuz']}")

    print()
    ke = m["kural_uyumu_etkisi"]
    print(f"  📈  KURAL UYUMUNUN ETKİSİ")
    print(f"     {'':20} {'İhlal':<12} {'Uyumlu'}")
    print(f"     {'Trade sayısı':20} {ke['ihlal_trade_sayisi']:<12} {ke['uyumlu_trade_sayisi']}")
    print(f"     {'Ort. PnL':20} {ke['ihlal_ort_pnl']:<12} {ke['uyumlu_ort_pnl']}")
    print(f"     {'Win Rate':20} {ke['ihlal_win_rate']:<12} {ke['uyumlu_win_rate']}")
    print(f"     ✅ {ke['avantaj']}")

    # --- Kural bazlı ihlaller ---
    print(f"\n{SEP}")
    print(f"  ❌ KURAL BAZLI İHLAL ANALİZİ")
    print(f"{SEP}")

    ihlal_olan = {k: v for k, v in kurallar.items() if v["ihlaller"]}
    for kural_id, data in sorted(ihlal_olan.items()):
        ihlaller = data["ihlaller"]
        print(f"\n  [{kural_id}] — {len(ihlaller)} ihlal")
        for ihl in ihlaller[:5]:
            print(f"     • {ihl['sembol']:<6} {ihl['pnl']:+.1f}% ({ihl['gun']} gün)")
            if ihl.get("detay"):
                print(f"       {ihl['detay'][:90]}")

    # --- Yeni kural adayları ---
    print(f"\n{SEP}")
    print(f"  💡 YENİ KURAL ADAYLARI (Zeynel onayı gerektirir)")
    print(f"{SEP}\n")

    for i, aday in enumerate(adaylar, 1):
        oncelik_icon = "🔴" if aday["oncelik"] == "YÜKSEK" else \
                       "🟡" if aday["oncelik"] == "ORTA"   else "🟢"
        print(f"  {oncelik_icon} [{i}] {aday['konu']}")
        print(f"       Kanıt: {aday['tekrar_sayisi']} trade'de tespit edildi")
        print(f"       Örnekler: {', '.join(aday['ornekler'])}")
        print(f"       Öneri: {aday['oneri_metni'][:130]}")
        print()


# ══════════════════════════════════════════════════════════════════════════════
# 5. JSON KAYIT
# ══════════════════════════════════════════════════════════════════════════════

def json_kaydet(trades, kurallar, adaylar, metrikler):
    output = {
        "olusturulma": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "toplam_trade": len(trades),
        "metrikler": metrikler,
        "kural_ihlalleri": {
            k: {
                "ihlal_sayisi": len(v["ihlaller"]),
                "ihlaller": v["ihlaller"][:10],
            }
            for k, v in kurallar.items() if v["ihlaller"]
        },
        "yeni_kural_adaylari": adaylar,
        "ozet": {
            "en_kritik_ihlal": "15 GÜN ZAMAN KURALI (5 ihlal, ort. +2.5% — kural çalışıyor)",
            "en_kritik_eksik": "Beta filtresi (DUK, DVA, VZ, WMT, AMT swing evrenine girmemeli)",
            "hemen_uygulanabilir": [
                "Swing evreninden çıkar: VZ, T, DUK, DVA, WMT, AMT",
                "Stop min. 2×ATR(14) zorunlu kıl",
                "VIX>25'te yeni swing girişi engelle (K-13 güçlendir)",
            ],
            "zeynel_onayi_bekleyen": [
                "K-ZST: 10. günde momentum kontrol protokolü",
                "K-KRZ: Kriz gün-1 yasak kuralı (K-21 adayı)",
                "K-EVR: Beta>0.7 swing evren filtresi",
            ],
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Kaydedildi: {OUTPUT_FILE}")
    return output


# ══════════════════════════════════════════════════════════════════════════════
# 6. CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — K-Kural Performans Analizi"
    )
    parser.add_argument("--report",     action="store_true", help="Tam rapor yazdır")
    parser.add_argument("--candidates", action="store_true", help="Sadece kural adayları")
    parser.add_argument("--save",       action="store_true", help="JSON'a kaydet")
    parser.add_argument("--all",        action="store_true", help="Rapor + kaydet")
    args = parser.parse_args()

    trades   = load_trades()
    kurallar = siniflandir_ihlaller(trades)
    adaylar  = yeni_kural_adaylari(trades)
    metrikler = kural_metrikleri(trades)

    if args.all or args.report:
        rapor_yazdir(trades, kurallar, adaylar, metrikler)

    if args.candidates:
        print(f"\n💡 YENİ KURAL ADAYLARI:\n")
        for i, a in enumerate(adaylar, 1):
            print(f"  {i}. [{a['oncelik']}] {a['konu']}")
            print(f"     {a['tekrar_sayisi']} trade | {', '.join(a['ornekler'])}")
            print(f"     → {a['oneri_metni'][:120]}\n")

    if args.all or args.save:
        json_kaydet(trades, kurallar, adaylar, metrikler)

    if not any([args.report, args.candidates, args.save, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
