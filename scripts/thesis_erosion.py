# -*- coding: utf-8 -*-
"""
TEZ BOZULMA ALARMI (Thesis Erosion Detector)
==============================================
Memory: "tez bozulması olunca pozisyon kapat" manuel kural.
Bu modul otomatik takip yapar.

Her pozisyon icin tez saglamlik skoru hesaplar (0-100):
  0   = tez tamamen saglam
  100 = tez tamamen bozuldu

Sinyaller:
  - Tema skoru ZAYIF (<5)        → +30
  - Tema guc dususu (9→6 vb)     → +25
  - Sektor RS underperform (<-3%) → +20
  - Fiyat 50SMA alti              → +15
  - VIX risk-off (>25)            → +10
  - Earnings miss son 30g         → +20

Karar matrisi:
  >=70 TEZ_TAMAMEN_BOZULDU → kapat
  50-69 TEZ_AGIR_HASAR    → %50 azalt
  30-49 TEZ_HAFIF_HASAR   → izle, siki stop
  <30  TEZ_SAGLAM         → tut

Kullanim:
  python scripts/thesis_erosion.py            # tum pozisyonlar
  python scripts/thesis_erosion.py --apply    # session_state kaydet
  python scripts/thesis_erosion.py --notify   # uyari Telegram
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


def get_50sma(sym: str) -> float:
    """FMP technical indicator 50SMA"""
    import requests
    try:
        KEY = os.environ.get("FMP_API_KEY", "")
        # SMA 50 stable endpoint
        r = requests.get(
            "https://financialmodelingprep.com/stable/technical-indicators/sma",
            params={"symbol": sym, "periodLength": 50, "timeframe": "1day", "apikey": KEY},
            timeout=8
        )
        if r.status_code == 200:
            d = r.json()
            if isinstance(d, list) and d:
                return float(d[0].get("sma") or 0)
    except Exception:
        pass
    return 0


def get_son_earnings(sym: str) -> dict | None:
    """Son 60g icinde earnings var mi, miss mi beat mi"""
    import requests
    try:
        KEY = os.environ.get("FMP_API_KEY", "")
        r = requests.get(
            "https://financialmodelingprep.com/stable/earnings",
            params={"symbol": sym, "limit": 4, "apikey": KEY},
            timeout=8
        )
        if r.status_code == 200:
            d = r.json()
            if isinstance(d, list) and d:
                bugun = datetime.now(TR).date()
                for e in d:
                    try:
                        tarih_str = e.get("date") or e.get("fiscalDate")
                        if not tarih_str:
                            continue
                        tarih = datetime.strptime(tarih_str[:10], "%Y-%m-%d").date()
                        gun_fark = (bugun - tarih).days
                        # Son 60g icinde
                        if 0 <= gun_fark <= 60:
                            est = e.get("epsEstimated") or 0
                            act = e.get("epsActual")
                            if est and act is not None:
                                surprise_pct = ((act - est) / abs(est)) * 100 if est != 0 else 0
                                return {
                                    "tarih": tarih_str[:10],
                                    "gun_kala": gun_fark,
                                    "estimated": est,
                                    "actual": act,
                                    "surprise_pct": round(surprise_pct, 1),
                                    "miss": surprise_pct < -3,  # %3+ miss
                                    "beat": surprise_pct > 3,   # %3+ beat
                                }
                    except Exception:
                        continue
    except Exception:
        pass
    return None


def evaluate_thesis(pos: dict, pf_name: str, vix: float, market_ctx: dict = None) -> dict:
    """
    Tek pozisyon icin tez saglamlik skoru hesapla.
    market_ctx: önceden hesaplanmış sektor/tema bilgileri (cache)
    """
    sym = pos.get("sembol")
    if not sym or sym == "_template":
        return None
    
    skor = 0  # 0 saglam, 100 bozuldu
    sebepler = []
    metrikler = {}
    
    # 1. Tema gucu
    try:
        from k12_dynamic_limits import _tema_haritasi, _tema_skoru
        tema_map = _tema_haritasi()
        tema_key = tema_map.get(sym)
        if tema_key:
            t_data = _tema_skoru(tema_key)
            t_skor = t_data.get("skor", 5)
            metrikler["tema"] = {"ad": t_data.get("ad"), "skor": t_skor, "rs": t_data.get("rs_vs_spy")}
            if t_skor < 5:
                skor += 30
                sebepler.append(f"Tema {t_data.get('ad')} skor {t_skor}/10 ZAYIF (+30)")
            elif t_skor < 7:
                skor += 15
                sebepler.append(f"Tema {t_data.get('ad')} skor {t_skor}/10 ORTA (+15)")
        else:
            metrikler["tema"] = None
    except Exception as _te:
        print(f"[ThesisErosion] {sym} tema hata: {_te}")
    
    # 2. Tema guc dususu (history)
    try:
        from k12_dynamic_limits import tema_dusus_tespit
        if tema_key:
            dusus = tema_dusus_tespit(tema_key)
            if dusus:
                metrikler["tema_dusus"] = dusus
                d = dusus["dusus"]
                if d >= 5:
                    skor += 25
                    sebepler.append(f"Tema skor dususu {dusus['eski_skor']}→{dusus['yeni_skor']} (-{d}) AGIR (+25)")
                elif d >= 3:
                    skor += 15
                    sebepler.append(f"Tema skor dususu {dusus['eski_skor']}→{dusus['yeni_skor']} (-{d}) (+15)")
    except Exception:
        pass
    
    # 3. Sektor RS
    try:
        from swing_entry_engine import check_sector_strength
        ss = check_sector_strength(sym)
        if ss:
            sek_rs = ss.get("fark", 0)
            metrikler["sektor"] = {"ad": ss.get("sektor"), "rs": sek_rs}
            if sek_rs < -5:
                skor += 25
                sebepler.append(f"Sektor {ss.get('sektor')} RS {sek_rs:+.1f}% AGIR underperform (+25)")
            elif sek_rs < -3:
                skor += 20
                sebepler.append(f"Sektor {ss.get('sektor')} RS {sek_rs:+.1f}% underperform (+20)")
    except Exception as _se:
        print(f"[ThesisErosion] {sym} sektor hata: {_se}")
    
    # 4. Fiyat 50SMA alti
    cur_p = pos.get("guncel_fiyat") or pos.get("son_fiyat") or 0
    if cur_p:
        sma50 = get_50sma(sym)
        if sma50 > 0:
            metrikler["sma50"] = {"sma": sma50, "fiyat": cur_p, "alti_mi": cur_p < sma50}
            if cur_p < sma50:
                fark_pct = (sma50 - cur_p) / sma50 * 100
                if fark_pct > 5:
                    skor += 20
                    sebepler.append(f"Fiyat ${cur_p:.2f} 50SMA ${sma50:.2f} %{fark_pct:.1f} ALTINDA (+20)")
                else:
                    skor += 15
                    sebepler.append(f"Fiyat ${cur_p:.2f} 50SMA ${sma50:.2f} altinda (+15)")
    
    # 5. VIX risk-off
    metrikler["vix"] = vix
    if vix > 30:
        skor += 15
        sebepler.append(f"VIX {vix:.1f} CRISIS (+15)")
    elif vix > 25:
        skor += 10
        sebepler.append(f"VIX {vix:.1f} risk-off (+10)")
    
    # 6. Earnings miss
    earnings = get_son_earnings(sym)
    if earnings:
        metrikler["earnings"] = earnings
        if earnings.get("miss"):
            skor += 20
            sebepler.append(f"Earnings MISS {earnings['surprise_pct']:+.1f}% ({earnings['gun_kala']}g once) (+20)")
        elif earnings.get("beat"):
            # Beat — tez gucleniyor, eksi puan
            skor -= 5
            sebepler.append(f"Earnings BEAT {earnings['surprise_pct']:+.1f}% — tez gucleniyor (-5)")
    
    # Skor 0-100 sinirla
    skor = max(0, min(100, skor))
    
    # Karar
    if skor >= 70:
        karar = "TEZ_TAMAMEN_BOZULDU"
        aksiyon = f"Pozisyonu KAPAT — tez gecerliligini yitirdi"
        seviye = "🔴"
    elif skor >= 50:
        karar = "TEZ_AGIR_HASAR"
        aksiyon = f"Pozisyonu %50 AZALT — risk yonetimi"
        seviye = "🟠"
    elif skor >= 30:
        karar = "TEZ_HAFIF_HASAR"
        aksiyon = f"IZLE — siki stop koy"
        seviye = "🟡"
    else:
        karar = "TEZ_SAGLAM"
        aksiyon = f"TUT — tez gecerli"
        seviye = "✅"
    
    # Pozisyon detay
    yas = 0
    pnl_pct = 0
    try:
        gd_str = pos.get("giris_tarihi", "")
        if gd_str:
            gd = datetime.strptime(gd_str[:10], "%Y-%m-%d")
            yas = (datetime.now() - gd).days
        mb = pos.get("maliyet_baz", 0) or 0
        if mb and cur_p:
            pnl_pct = (cur_p - mb) / mb * 100
    except Exception:
        pass
    
    return {
        "sembol": sym,
        "portfoy": pf_name,
        "skor": skor,
        "karar": karar,
        "aksiyon": aksiyon,
        "seviye": seviye,
        "sebepler": sebepler,
        "metrikler": metrikler,
        "yas_gun": yas,
        "pnl_pct": round(pnl_pct, 2),
    }


def tum_portfoyler() -> dict:
    # VIX al
    try:
        from k12_dynamic_limits import get_vix
        vix = get_vix()
    except Exception:
        vix = 20.0
    
    sonuclar = {
        "tarih": datetime.now(TR).isoformat(),
        "vix": vix,
        "pozisyonlar": [],
        "ozet": {"saglam": 0, "hafif": 0, "agir": 0, "bozuldu": 0},
    }
    
    # Portfolios
    for pf in ["balanced", "aggressive", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if not path.exists():
            continue
        d = json.load(open(path))
        for poz in d.get("pozisyonlar", []):
            r = evaluate_thesis(poz, pf, vix)
            if r:
                sonuclar["pozisyonlar"].append(r)
                if r["skor"] >= 70:
                    sonuclar["ozet"]["bozuldu"] += 1
                elif r["skor"] >= 50:
                    sonuclar["ozet"]["agir"] += 1
                elif r["skor"] >= 30:
                    sonuclar["ozet"]["hafif"] += 1
                else:
                    sonuclar["ozet"]["saglam"] += 1
    
    # Swing
    sw_path = REPO_ROOT / "data" / "swing" / "active.json"
    if sw_path.exists():
        sw = json.load(open(sw_path))
        for poz in sw.get("aktif_pozisyonlar", []):
            r = evaluate_thesis(poz, "swing", vix)
            if r:
                sonuclar["pozisyonlar"].append(r)
                if r["skor"] >= 70:
                    sonuclar["ozet"]["bozuldu"] += 1
                elif r["skor"] >= 50:
                    sonuclar["ozet"]["agir"] += 1
                elif r["skor"] >= 30:
                    sonuclar["ozet"]["hafif"] += 1
                else:
                    sonuclar["ozet"]["saglam"] += 1
    
    return sonuclar


def yazdir(s: dict):
    print("=" * 80)
    print(f"TEZ BOZULMA ALARMI — VIX {s['vix']:.1f}")
    print("=" * 80)
    print()
    print(f"OZET: ✅saglam:{s['ozet']['saglam']} 🟡hafif:{s['ozet']['hafif']} "
          f"🟠agir:{s['ozet']['agir']} 🔴bozuldu:{s['ozet']['bozuldu']}")
    print()
    
    # En riskli pozisyonlardan basla
    sirali = sorted(s["pozisyonlar"], key=lambda x: -x["skor"])
    
    for p in sirali:
        print(f"{p['seviye']} [{p['portfoy']:10}] {p['sembol']:6} "
              f"skor:{p['skor']:>3} | {p['karar']:25} | "
              f"yas:{p['yas_gun']:>3}g | P/L: {p['pnl_pct']:+.1f}%")
        if p["skor"] >= 30:
            for s_str in p["sebepler"]:
                print(f"     • {s_str}")
            print(f"     → {p['aksiyon']}")
            print()


def session_state_kaydet(sonuc: dict):
    ss_path = REPO_ROOT / "data" / "session_state.json"
    ss = json.load(open(ss_path)) if ss_path.exists() else {}
    ss["thesis_erosion"] = sonuc
    with open(ss_path, "w") as f:
        json.dump(ss, f, ensure_ascii=False, indent=2)
    print(f"\n[ThesisErosion] session_state kaydedildi")


def telegram_uyari(sonuc: dict):
    """Skor >= 50 olan pozisyonlar için DM uyarı"""
    riskli = [p for p in sonuc["pozisyonlar"] if p["skor"] >= 50]
    if not riskli:
        print("[ThesisErosion] Kritik pozisyon yok, Telegram'a gitmiyor")
        return
    
    msg = f"🚨 *TEZ BOZULMA ALARMI* — {len(riskli)} pozisyon\n\n"
    msg += f"VIX: {sonuc['vix']:.1f}\n\n"
    for p in riskli:
        msg += f"{p['seviye']} *{p['sembol']}* ({p['portfoy']}) skor:{p['skor']}\n"
        msg += f"   {p['karar']}\n"
        msg += f"   → {p['aksiyon']}\n"
        for s_str in p["sebepler"][:3]:
            msg += f"   • {s_str}\n"
        msg += "\n"
    
    # DM gonder (sistem mesaji)
    try:
        import subprocess
        subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "telegram_notify.py"), 
             "--text", msg, "--dm"],
            cwd=str(REPO_ROOT), check=False, timeout=15
        )
        print(f"[ThesisErosion] Telegram DM gonderildi: {len(riskli)} pozisyon")
    except Exception as _te:
        print(f"[ThesisErosion] Telegram hata: {_te}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()
    
    s = tum_portfoyler()
    yazdir(s)
    
    if args.apply:
        session_state_kaydet(s)
    if args.notify:
        telegram_uyari(s)


if __name__ == "__main__":
    main()
