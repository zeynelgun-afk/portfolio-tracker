# -*- coding: utf-8 -*-
"""
THEME TRACKER — aktif yatirim temalari ve performans takibi
=============================================================
Memory: 'Aktif tema skorlari (1-10) haftalik guncelle.'

10 ana tema, her birinin temsilci semboller listesi var. Her hafta:
1. Her temanin son 10g performansini hesapla (semboller ortalama)
2. SPY'a karsi RS hesapla
3. Tema skoru = base_score + RS bonus/ceza
4. Skor 8+ → guclu, hot tema (yatirima uygun)
5. Skor 4-7 → orta (mevcut pozisyonlari koru)
6. Skor <4 → zayif (rotasyon yapilmali)

Kullanim:
  python scripts/theme_tracker.py --update     # Skorlari guncelle
  python scripts/theme_tracker.py --report     # Markdown rapor
"""
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))

sys.path.insert(0, str(REPO_ROOT / "scripts"))

# 10 ana tema — temsilci semboller
TEMALAR = {
    "ai_yari_iletken": {
        "ad": "AI / Yari-iletken",
        "semboller": ["NVDA", "AMD", "AVGO", "MU", "MRVL", "ASML", "AMAT", "LRCX", "KLAC"],
        "kategori": "buyume",
    },
    "ai_yazilim": {
        "ad": "AI Yazilim / Bulut",
        "semboller": ["MSFT", "GOOGL", "META", "ORCL", "PLTR", "CRWD", "SNOW", "DDOG"],
        "kategori": "buyume",
    },
    "elektrik_altyapi": {
        "ad": "Elektrik / Sebeke / DC",
        "semboller": ["VRT", "PWR", "ETN", "GEV", "POWL", "DLR", "EQIX", "TT"],
        "kategori": "buyume",
    },
    "uranyum_nukleer": {
        "ad": "Uranyum / Nukleer",
        "semboller": ["UEC", "LEU", "DNN", "CCJ", "NNE", "OKLO", "VST", "BWXT"],
        "kategori": "agresif",
    },
    "savunma": {
        "ad": "Savunma / Defansif",
        "semboller": ["LMT", "RTX", "GD", "NOC", "HII", "KTOS", "AVAV"],
        "kategori": "defansif_buyume",
    },
    "saglik": {
        "ad": "Saglik (XLV)",
        "semboller": ["UNH", "JNJ", "ABBV", "MRK", "LLY", "PFE", "TMO"],
        "kategori": "defansif",
    },
    "tuketici_temel": {
        "ad": "Tuketici Temel (XLP)",
        "semboller": ["KO", "PG", "PEP", "WMT", "COST", "MO", "PM", "CL"],
        "kategori": "defansif",
    },
    "altin": {
        "ad": "Altin / Kıymetli Maden",
        "semboller": ["GLD", "GDX", "NEM", "GOLD", "AEM", "FNV"],
        "kategori": "guvenli_liman",
    },
    "kripto": {
        "ad": "Kripto / Ethereum",
        "semboller": ["MSTR", "COIN", "MARA", "RIOT", "GBTC", "ETHE"],
        "kategori": "yuksek_risk",
    },
    "petrol_enerji": {
        "ad": "Petrol / Enerji",
        "semboller": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD"],
        "kategori": "siklus",
    },
}


def get_history(symbol: str, days: int = 12) -> list:
    """FMP'den tarihi fiyat al"""
    import requests
    KEY = os.environ.get("FMP_API_KEY", "")
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/stable/historical-price-eod/full",
            params={"symbol": symbol, "apikey": KEY},
            timeout=10
        )
        if r.status_code == 200:
            d = r.json()
            if isinstance(d, list):
                return d[:days]
    except Exception:
        pass
    return []


def gun_basari(symbol: str, gun: int = 10) -> float:
    """Son N gun yuzde getiri"""
    h = get_history(symbol, gun + 2)
    if len(h) < gun + 1:
        return None
    # FMP yeni->eski sıralı
    son = h[0]["close"]
    onceki = h[gun]["close"]
    return (son - onceki) / onceki * 100


def tema_skor(tema_key: str, tema: dict, spy_perf: float) -> dict:
    """Tek tema icin skor hesabi"""
    semboller = tema["semboller"]
    perflar = []
    for s in semboller:
        p = gun_basari(s)
        if p is not None:
            perflar.append(p)
    if not perflar:
        return {"skor": 5, "perf": 0, "rs": 0, "veri_yok": True}
    
    avg_perf = sum(perflar) / len(perflar)
    rs = avg_perf - spy_perf
    
    # Base skor 5 + RS bonus
    if rs > 5:
        bonus = 4  # Çok güçlü
    elif rs > 2:
        bonus = 3
    elif rs > 0:
        bonus = 1
    elif rs > -2:
        bonus = -1
    elif rs > -5:
        bonus = -3
    else:
        bonus = -4
    
    skor = max(1, min(10, 5 + bonus))
    
    # Yorum
    if skor >= 8:
        seviye = "GUCLU"
    elif skor >= 5:
        seviye = "ORTA"
    elif skor >= 3:
        seviye = "ZAYIF"
    else:
        seviye = "TEHLIKELI"
    
    return {
        "skor": skor,
        "seviye": seviye,
        "perf_10g": round(avg_perf, 2),
        "rs_vs_spy": round(rs, 2),
        "sembol_sayisi": len(perflar),
    }


def hesapla_tum_temalar() -> dict:
    """Her tema için skor hesapla"""
    spy_perf = gun_basari("SPY")
    if spy_perf is None:
        spy_perf = 0
    print(f"[Theme] SPY 10g: {spy_perf:+.2f}%")
    
    sonuc = {
        "tarih": datetime.now(TR).isoformat(),
        "spy_10g_perf": round(spy_perf, 2),
        "temalar": {},
    }
    
    for k, t in TEMALAR.items():
        print(f"  {k}... ", end="", flush=True)
        skor_data = tema_skor(k, t, spy_perf)
        sonuc["temalar"][k] = {
            "ad": t["ad"],
            "kategori": t["kategori"],
            **skor_data,
        }
        print(f"skor:{skor_data['skor']} ({skor_data['seviye']})")
    
    return sonuc


def rapor_olustur(s: dict) -> str:
    """Markdown rapor"""
    lines = [
        f"# TEMA SKOR RAPORU — {s['tarih'][:10]}",
        f"",
        f"SPY 10 gun: {s['spy_10g_perf']:+.2f}%",
        f"",
        f"## Aktif Temalar (skor sirali)",
        f"",
        f"| Skor | Tema | Kategori | 10g Perf | RS vs SPY |",
        f"|------|------|----------|----------|-----------|",
    ]
    
    # Skor sırasına göre sırala
    sorted_temalar = sorted(s["temalar"].items(), key=lambda x: -x[1]["skor"])
    for k, t in sorted_temalar:
        seviye_icon = {"GUCLU": "🟢", "ORTA": "🟡", "ZAYIF": "🟠", "TEHLIKELI": "🔴"}.get(t["seviye"], "⚪")
        lines.append(
            f"| {seviye_icon} **{t['skor']}** | {t['ad']} | {t['kategori']} | "
            f"{t['perf_10g']:+.2f}% | {t['rs_vs_spy']:+.2f}% |"
        )
    
    lines.extend([
        f"",
        f"## Eylem Onerileri",
        f"",
        f"### Guclu Temalar (skor 8+) — Yatırıma Uygun",
    ])
    guclu = [t for t in s["temalar"].values() if t["skor"] >= 8]
    if guclu:
        for t in guclu:
            lines.append(f"- {t['ad']} (skor {t['skor']}, RS {t['rs_vs_spy']:+.1f}%)")
    else:
        lines.append("- Yok (tum temalar SPY altinda veya nott)")
    
    lines.extend([
        f"",
        f"### Zayıf Temalar (skor <4) — Rotasyon Adayı",
    ])
    zayif = [t for t in s["temalar"].values() if t["skor"] < 4]
    if zayif:
        for t in zayif:
            lines.append(f"- {t['ad']} (skor {t['skor']}, RS {t['rs_vs_spy']:+.1f}%) — pozisyon varsa azalt")
    else:
        lines.append("- Yok (tum temalar saglikli)")
    
    return "\n".join(lines)


def kayit_et(s: dict):
    out = REPO_ROOT / "data" / "theme_scores.json"
    with open(out, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    print(f"[Theme] Kaydedildi: {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="Skorlari guncelle ve kaydet")
    parser.add_argument("--report", action="store_true", help="Markdown rapor")
    args = parser.parse_args()
    
    if args.update or args.report:
        s = hesapla_tum_temalar()
        if args.update:
            kayit_et(s)
        if args.report:
            print()
            print(rapor_olustur(s))


if __name__ == "__main__":
    main()
