# -*- coding: utf-8 -*-
"""
K-12 v2 — DINAMIK SEKTOR LIMITI
==================================
Mevcut K-12: sabit %40 sektor+tema limit.
Sorun: Cok guclu temalar varken (AI 9/10) %40 catisi firsat kaybi.
Druckenmiller felsefesi: 'convicted bet — when you have strong
conviction, bet big.'

K-12 v2 (Dinamik):
  Base: sektor+tema toplam %40 (eski)
  
  YUMUSAMA (artirir):
  - Tema skor 9-10 + RS vs SPY > +5%  → +%20 (max %60)
  - Tema skor 8     + RS > +2%        → +%10 (max %50)
  - Tema skor 7     + RS > 0          → +%5  (max %45)
  
  IPTAL (yumuşama uygulanmaz):
  - VIX > 28 → standart %40
  - K-23 drawdown >= DEFANSIF → standart %40 (yada azalt)
  - Tema skoru ardisik 2 hafta dustuyse → standart %40
  
  ZORUNLU AZALT (mevcut pozisyondan):
  - Tema skoru 9 → 6 dustuyse → %25 azalt
  - Tema skoru 9 → 4 dustuyse → %50 azalt
  - Tema skoru 9 → 2 dustuyse → tam cikis

Kullanim:
  python scripts/k12_dynamic_limits.py            # Konsola
  python scripts/k12_dynamic_limits.py --apply   # session_state'e kaydet
"""
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))

sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Tema → semboller (theme_tracker.TEMALAR)
def _tema_haritasi() -> dict:
    """Sembol → tema_key haritasi"""
    try:
        from theme_tracker import TEMALAR
    except ImportError:
        return {}
    out = {}
    for k, t in TEMALAR.items():
        for s in t.get("semboller", []):
            out[s] = k
    return out


def _tema_skoru(tema_key: str) -> dict:
    """theme_scores.json'dan tek tema bilgisi"""
    th_path = REPO_ROOT / "data" / "theme_scores.json"
    if not th_path.exists():
        return {}
    th = json.load(open(th_path))
    return th.get("temalar", {}).get(tema_key, {})


def get_vix() -> float:
    import requests
    try:
        KEY = os.environ.get("FMP_API_KEY", "")
        r = requests.get(
            f"https://financialmodelingprep.com/stable/quote?symbol=^VIX&apikey={KEY}",
            timeout=8
        )
        if r.status_code == 200:
            d = r.json()
            if isinstance(d, list) and d:
                return float(d[0].get("price") or 20)
    except Exception:
        pass
    return 20.0


def hesapla_dinamik_limit(tema_skor: dict, vix: float, k23_kod: int = 0) -> dict:
    """
    Tema/VIX/K-23 durumuna gore yumusatilmis limiti hesapla.
    Donus: {limit_pct, yumusama, gerekce}
    """
    base = 40
    skor = tema_skor.get("skor", 5)
    rs = tema_skor.get("rs_vs_spy", 0)
    
    # Iptal kosullari
    if vix > 28:
        return {"limit_pct": base, "yumusama": 0, 
                "gerekce": f"VIX {vix:.1f}>28, yumusama yok"}
    if k23_kod >= 2:
        return {"limit_pct": base, "yumusama": 0,
                "gerekce": f"K-23 kod {k23_kod} (DEFANSIF+), yumusama yok"}
    
    # Yumusama
    bonus = 0
    gerekce_parts = []
    if skor >= 9 and rs > 5:
        bonus = 20
        gerekce_parts.append(f"tema skor {skor} GUCLU + RS +{rs:.1f}%")
    elif skor >= 8 and rs > 2:
        bonus = 10
        gerekce_parts.append(f"tema skor {skor} GUCLU + RS +{rs:.1f}%")
    elif skor >= 7 and rs > 0:
        bonus = 5
        gerekce_parts.append(f"tema skor {skor} ORTA-yukari + RS +{rs:.1f}%")
    
    return {
        "limit_pct": base + bonus,
        "yumusama": bonus,
        "gerekce": "; ".join(gerekce_parts) if gerekce_parts else "Standart limit",
    }


def portfoy_sektor_dagilimi(pf_data: dict) -> dict:
    """Portfoyun sektor (tema) bazli dagilimini hesapla"""
    haritasi = _tema_haritasi()
    
    # Toplam değer
    pos_deger = 0
    tema_deger = defaultdict(float)
    sektor_deger = defaultdict(float)
    
    for poz in pf_data.get("pozisyonlar", []):
        sym = poz.get("sembol")
        if sym in (None, "_template"):
            continue
        adet = poz.get("adet", 0) or 0
        cf = poz.get("guncel_fiyat", 0) or 0
        deger = adet * cf
        pos_deger += deger
        
        # Tema atama
        tema_key = haritasi.get(sym)
        if tema_key:
            tema_deger[tema_key] += deger
        
        # Sektor atama
        sek = poz.get("sektor", "")
        if sek:
            sektor_deger[sek] += deger
    
    nakit_obj = pf_data.get("nakit", 0)
    if isinstance(nakit_obj, dict):
        nakit = nakit_obj.get("miktar", 0) or 0
    else:
        nakit = float(nakit_obj or 0)
    
    toplam = pos_deger + nakit
    
    # Yuzdeler
    tema_pct = {k: round(v / toplam * 100, 1) for k, v in tema_deger.items()} if toplam else {}
    sektor_pct = {k: round(v / toplam * 100, 1) for k, v in sektor_deger.items()} if toplam else {}
    
    return {
        "toplam": toplam,
        "pozisyon_deger": pos_deger,
        "nakit": nakit,
        "tema_pct": tema_pct,
        "sektor_pct": sektor_pct,
    }


def k12_v2_analiz(pf_name: str, pf_data: dict, vix: float, k23_kod: int = 0) -> dict:
    """
    Tek portfoy icin K-12 v2 analizi.
    Her tema/sektor icin: mevcut % vs dinamik limit
    """
    dagilim = portfoy_sektor_dagilimi(pf_data)
    
    # Her temanin icin durum
    tema_durum = []
    for tema_key, mevcut_pct in dagilim["tema_pct"].items():
        skor_data = _tema_skoru(tema_key)
        limit = hesapla_dinamik_limit(skor_data, vix, k23_kod)
        durum = "NORMAL"
        aksiyon = None
        if mevcut_pct > limit["limit_pct"]:
            durum = "ASILDI"
            aksiyon = f"K-12 ihlal: %{mevcut_pct} > %{limit['limit_pct']}, kucult"
        elif mevcut_pct > limit["limit_pct"] * 0.85:
            durum = "YAKIN"
            aksiyon = f"Limite yakin (%{mevcut_pct} / %{limit['limit_pct']}), yeni alim sınırlı"
        
        tema_durum.append({
            "tema": tema_key,
            "ad": skor_data.get("ad", tema_key),
            "mevcut_pct": mevcut_pct,
            "tema_skor": skor_data.get("skor"),
            "tema_seviye": skor_data.get("seviye"),
            "rs_vs_spy": skor_data.get("rs_vs_spy"),
            "dinamik_limit_pct": limit["limit_pct"],
            "yumusama": limit["yumusama"],
            "gerekce": limit["gerekce"],
            "durum": durum,
            "aksiyon": aksiyon,
        })
    
    # En riskli sektor
    en_yuksek_sektor = None
    en_yuksek_pct = 0
    for sek, pct in dagilim["sektor_pct"].items():
        if pct > en_yuksek_pct:
            en_yuksek_pct = pct
            en_yuksek_sektor = sek
    
    return {
        "portfoy": pf_name,
        "toplam_deger": dagilim["toplam"],
        "tema_durum": sorted(tema_durum, key=lambda x: -x["mevcut_pct"]),
        "en_yuksek_sektor": {"ad": en_yuksek_sektor, "pct": en_yuksek_pct} if en_yuksek_sektor else None,
        "tema_dagilim": dagilim["tema_pct"],
        "sektor_dagilim": dagilim["sektor_pct"],
    }


def tum_portfoyler() -> dict:
    vix = get_vix()
    
    # K-23 al
    k23_kod = 0
    try:
        from portfolio_drawdown_guard import analiz_yap as _k23_a
        k23_s = _k23_a()
        k23_kod = k23_s["toplam"]["k23"]["kod"]
    except Exception:
        pass
    
    sonuc = {
        "tarih": datetime.now(TR).isoformat(),
        "vix": vix,
        "k23_kod": k23_kod,
        "portfoyler": {},
    }
    
    for pf in ["balanced", "aggressive", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if not path.exists():
            continue
        d = json.load(open(path))
        sonuc["portfoyler"][pf] = k12_v2_analiz(pf, d, vix, k23_kod)
    
    return sonuc


def yazdir(s: dict):
    print("=" * 75)
    print(f"K-12 v2 DINAMIK SEKTOR LIMITI — VIX {s['vix']:.1f} | K-23 kod {s['k23_kod']}")
    print("=" * 75)
    
    for pf, data in s["portfoyler"].items():
        print(f"\n>>> {pf.upper()} (${data['toplam_deger']:,.0f})")
        if not data["tema_durum"]:
            print("  Tematik tasinma yok")
        for t in data["tema_durum"]:
            durum_icon = {"NORMAL": "✅", "YAKIN": "🟡", "ASILDI": "🔴"}.get(t["durum"], "?")
            limit_str = f"%{t['dinamik_limit_pct']}"
            if t["yumusama"]:
                limit_str += f" (+%{t['yumusama']} yumusama)"
            print(f"  {durum_icon} {t['ad']:25} %{t['mevcut_pct']:>5.1f} / {limit_str:20} | tema skor {t.get('tema_skor', '?')}")
            if t["aksiyon"]:
                print(f"     ⚠️ {t['aksiyon']}")
            if t["gerekce"] and t["yumusama"]:
                print(f"     💡 Yumusama: {t['gerekce']}")
        
        # En yuksek sektor
        if data.get("en_yuksek_sektor"):
            es = data["en_yuksek_sektor"]
            print(f"  En yuksek sektor: {es['ad']} %{es['pct']:.1f}")


def session_state_kaydet(s: dict):
    ss_path = REPO_ROOT / "data" / "session_state.json"
    ss = json.load(open(ss_path)) if ss_path.exists() else {}
    ss["k12_v2_durum"] = s
    with open(ss_path, "w") as f:
        json.dump(ss, f, ensure_ascii=False, indent=2)
    print(f"\n[K-12 v2] session_state kaydedildi")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="session_state'e kaydet")
    parser.add_argument("--vix", type=float, help="Manuel VIX")
    args = parser.parse_args()
    
    s = tum_portfoyler()
    if args.vix:
        s["vix"] = args.vix
    yazdir(s)
    
    if args.apply:
        session_state_kaydet(s)


if __name__ == "__main__":
    main()


def tema_skor_history() -> Path:
    """Tema skor history dosyası — her hafta append edilir"""
    return REPO_ROOT / "data" / "theme_scores_history.jsonl"


def history_append():
    """Bu haftanin tema skorlarini history'e ekle"""
    th_path = REPO_ROOT / "data" / "theme_scores.json"
    if not th_path.exists():
        return
    th = json.load(open(th_path))
    
    h_path = tema_skor_history()
    h_path.parent.mkdir(exist_ok=True)
    
    with open(h_path, "a") as f:
        f.write(json.dumps({
            "tarih": th.get("tarih", datetime.now(TR).isoformat()),
            "spy_perf": th.get("spy_10g_perf"),
            "skorlar": {k: t["skor"] for k, t in th.get("temalar", {}).items()},
        }, ensure_ascii=False) + "\n")
    print(f"[K-12 v2] Tema history'e eklendi")


def tema_dusus_tespit(tema_key: str) -> dict | None:
    """
    Tema skorunda dusus oldu mu? (Otomatik azaltma trigger)
    Donus: None yada {eski_skor, yeni_skor, dusus, aksiyon}
    """
    h_path = tema_skor_history()
    if not h_path.exists():
        return None
    
    # Son 2 hafta
    kayitlar = []
    with open(h_path) as f:
        for line in f:
            try:
                kayitlar.append(json.loads(line))
            except Exception:
                continue
    
    if len(kayitlar) < 2:
        return None
    
    # Bugun ve onceki
    son = kayitlar[-1].get("skorlar", {}).get(tema_key)
    onceki = kayitlar[-2].get("skorlar", {}).get(tema_key)
    
    if son is None or onceki is None:
        return None
    
    dusus = onceki - son
    if dusus < 2:
        return None
    
    # Aksiyon belirleme
    if dusus >= 7:
        aksiyon = "TAM_CIKIS"
        oran = 100
    elif dusus >= 5:
        aksiyon = "AZALT_50"
        oran = 50
    elif dusus >= 3:
        aksiyon = "AZALT_25"
        oran = 25
    else:
        aksiyon = "UYARI"
        oran = 0
    
    return {
        "eski_skor": onceki,
        "yeni_skor": son,
        "dusus": dusus,
        "aksiyon": aksiyon,
        "azalt_oran": oran,
    }
