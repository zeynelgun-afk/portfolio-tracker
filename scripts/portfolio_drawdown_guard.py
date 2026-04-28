# -*- coding: utf-8 -*-
"""
PORTFOLIO DRAWDOWN GUARD — K-23
================================
Portföy düzeyinde drawdown koruması. Memory'de tek pozisyon stop'u var
(K-06) ama portföy bazlı korunma yok. Tüm pozisyonlar aynı anda kayba
geçerse sistem saldırı modunda kalıp daha çok kayıp yapar.

K-23 EŞIKLERI (peak'ten drawdown):
  ≤%5  → NORMAL (aksiyon yok)
  >%5  → UYARI (early warning, defansif düşün)
  >%10 → DEFANSIF (yeni saldırı pozisyonu YOK, K-22 nakit dağıtım defansife)
  >%15 → HEDGE (inverse ETF zorunlu, mevcut pozisyonlardan %25 azalt)
  >%20 → STOP TRADING (tüm yeni girişler durur, sadece mevcut yönetim)

Drawdown hesabı:
  Peak = max(performance_history.values) ya da baslangic_sermaye
  Drawdown = (peak - mevcut) / peak

Kullanim:
  python scripts/portfolio_drawdown_guard.py            # Konsola
  python scripts/portfolio_drawdown_guard.py --apply   # session_state'e kaydet
  python scripts/portfolio_drawdown_guard.py --telegram # DM uyarısı
"""
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))

# K-23 eşikleri
DRAWDOWN_LIMIT = {
    "uyari":     5.0,   # Erken uyarı
    "defansif": 10.0,   # Saldırı durdur, defansif geç
    "hedge":    15.0,   # Inverse ETF zorunlu, %25 azalt
    "stop":     20.0,   # Trading dur
}


def hesapla_drawdown(pf_data: dict, history: list = None) -> dict:
    """
    Drawdown hesapla.
    history: performance_history.jsonl'dan snapshot listesi
    """
    bas = pf_data.get("baslangic_sermaye", 0) or 0
    
    # Mevcut değer
    pos_deger = 0
    for poz in pf_data.get("pozisyonlar", []):
        sym = poz.get("sembol")
        if sym in (None, "_template"):
            continue
        adet = poz.get("adet", 0) or 0
        cf = poz.get("guncel_fiyat", 0) or 0
        pos_deger += adet * cf
    
    nakit_obj = pf_data.get("nakit", 0)
    if isinstance(nakit_obj, dict):
        nakit = nakit_obj.get("miktar", 0) or 0
    else:
        nakit = float(nakit_obj or 0)
    
    mevcut = pos_deger + nakit
    
    # Peak hesabı
    if history:
        # En yüksek snapshot değerini bul (performans tarihinden)
        peak_history = max(history) if history else 0
        peak = max(peak_history, bas, mevcut)
    else:
        peak = max(bas, mevcut)
    
    drawdown_pct = ((peak - mevcut) / peak * 100) if peak else 0
    
    return {
        "baslangic": bas,
        "mevcut": mevcut,
        "peak": peak,
        "drawdown_pct": round(drawdown_pct, 2),
        "drawdown_usd": round(peak - mevcut, 0) if peak > mevcut else 0,
    }


def k23_seviye(drawdown_pct: float) -> dict:
    """K-23 seviye karar"""
    if drawdown_pct >= DRAWDOWN_LIMIT["stop"]:
        return {"seviye": "STOP_TRADING", "renk": "🔴", "kod": 4,
                "aksiyon": "Tum yeni girisler DURDU. Sadece mevcut pozisyon yonetimi.",
                "kural": "K-23/4: %20+ drawdown = trading dur"}
    elif drawdown_pct >= DRAWDOWN_LIMIT["hedge"]:
        return {"seviye": "HEDGE_ZORUNLU", "renk": "🟠", "kod": 3,
                "aksiyon": "Inverse ETF zorunlu (SH/SQQQ). Mevcut pozisyonlardan %25 azalt.",
                "kural": "K-23/3: %15+ drawdown = hedge"}
    elif drawdown_pct >= DRAWDOWN_LIMIT["defansif"]:
        return {"seviye": "DEFANSIF", "renk": "🟡", "kod": 2,
                "aksiyon": "Yeni saldiri pozisyonu YOK. K-22 nakit defansife (XLP/XLV/GLD/TLT).",
                "kural": "K-23/2: %10+ drawdown = defansif"}
    elif drawdown_pct >= DRAWDOWN_LIMIT["uyari"]:
        return {"seviye": "UYARI", "renk": "🟢", "kod": 1,
                "aksiyon": "Defansif planı düşün. Yeni girişlerde dikkat.",
                "kural": "K-23/1: %5+ drawdown = uyari"}
    else:
        return {"seviye": "NORMAL", "renk": "✅", "kod": 0,
                "aksiyon": "Normal operasyon, aksiyon yok.",
                "kural": "K-23/0: NORMAL"}


def get_history(pf_name: str) -> list:
    """performance_history.jsonl'dan portföy degerlerini al"""
    h_path = REPO_ROOT / "data" / "performance_history.jsonl"
    if not h_path.exists():
        return []
    snapshots = []
    try:
        with open(h_path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    pf = d.get("portfoyler", {}).get(pf_name, {})
                    val = pf.get("mevcut_deger") or pf.get("toplam_deger")
                    if val:
                        snapshots.append(val)
                except Exception:
                    continue
    except Exception:
        pass
    return snapshots


def analiz_yap() -> dict:
    """Tüm portföyler için K-23 analiz"""
    sonuc = {
        "tarih": datetime.now(TR).isoformat(),
        "portfoyler": {},
        "toplam": {},
    }
    
    toplam_mevcut = 0
    toplam_peak = 0
    
    for pf in ["balanced", "aggressive", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if not path.exists():
            continue
        d = json.load(open(path))
        history = get_history(pf)
        dd = hesapla_drawdown(d, history)
        seviye = k23_seviye(dd["drawdown_pct"])
        sonuc["portfoyler"][pf] = {
            "drawdown": dd,
            "k23": seviye,
        }
        toplam_mevcut += dd["mevcut"]
        toplam_peak += dd["peak"]
    
    # Toplam $600K bazlı genel drawdown
    if toplam_peak:
        toplam_dd = ((toplam_peak - toplam_mevcut) / toplam_peak * 100)
    else:
        toplam_dd = 0
    sonuc["toplam"] = {
        "mevcut": round(toplam_mevcut, 0),
        "peak": round(toplam_peak, 0),
        "drawdown_pct": round(toplam_dd, 2),
        "k23": k23_seviye(toplam_dd),
    }
    
    return sonuc


def yazdir(s: dict):
    print("=" * 70)
    print(f"K-23 PORTFOLIO DRAWDOWN GUARD")
    print("=" * 70)
    
    for pf, data in s["portfoyler"].items():
        dd = data["drawdown"]
        k = data["k23"]
        print(f"\n>>> {pf.upper()}")
        print(f"  Mevcut: ${dd['mevcut']:>8,.0f} | Peak: ${dd['peak']:>8,.0f}")
        print(f"  Drawdown: {dd['drawdown_pct']:>5.2f}% (${dd['drawdown_usd']:,.0f})")
        print(f"  {k['renk']} {k['seviye']} — {k['kural']}")
        if k['kod'] >= 1:
            print(f"     Aksiyon: {k['aksiyon']}")
    
    # Toplam
    t = s["toplam"]
    k = t["k23"]
    print(f"\n>>> TOPLAM ($600K hedef)")
    print(f"  Mevcut: ${t['mevcut']:>8,.0f} | Peak: ${t['peak']:>8,.0f}")
    print(f"  Drawdown: {t['drawdown_pct']:>5.2f}%")
    print(f"  {k['renk']} {k['seviye']}")


def telegram_uyarisi(s: dict):
    """K-23 seviye 2+ icin DM uyarısı"""
    try:
        import requests
    except ImportError:
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    dm_id = os.environ.get("TELEGRAM_PRIVATE_ID", "")
    if not (token and dm_id):
        return
    
    # En kötü drawdown seviyesini bul
    en_kotu = 0
    en_kotu_pf = None
    for pf, data in s["portfoyler"].items():
        kod = data["k23"]["kod"]
        if kod > en_kotu:
            en_kotu = kod
            en_kotu_pf = pf
    
    # Toplam drawdown da
    toplam_kod = s["toplam"]["k23"]["kod"]
    if toplam_kod > en_kotu:
        en_kotu = toplam_kod
        en_kotu_pf = "TOPLAM"
    
    # Sadece UYARI ve üstü için bildirim
    if en_kotu < 1:
        return
    
    msg = "*🚨 K-23 DRAWDOWN GUARD UYARI*\n\n"
    for pf, data in s["portfoyler"].items():
        dd = data["drawdown"]
        k = data["k23"]
        if k["kod"] >= 1:
            msg += f"{k['renk']} *{pf.upper()}*: -%{dd['drawdown_pct']:.1f} (${dd['drawdown_usd']:,.0f})\n"
            msg += f"   {k['kural']}\n"
            msg += f"   {k['aksiyon']}\n\n"
    
    t = s["toplam"]
    if t["k23"]["kod"] >= 1:
        msg += f"*TOPLAM*: -%{t['drawdown_pct']:.1f}\n{t['k23']['aksiyon']}"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, data={
            "chat_id": dm_id, "text": msg, "parse_mode": "Markdown"
        }, timeout=10)
        if r.status_code == 200:
            print(f"[K-23] Telegram DM gonderildi (en kotu: {en_kotu_pf})")
    except Exception as e:
        print(f"[K-23] Telegram hata: {e}")


def session_state_kaydet(s: dict):
    ss_path = REPO_ROOT / "data" / "session_state.json"
    ss = json.load(open(ss_path)) if ss_path.exists() else {}
    ss["k23_drawdown_guard"] = s
    with open(ss_path, "w") as f:
        json.dump(ss, f, ensure_ascii=False, indent=2)
    print(f"\n[K-23] session_state.k23_drawdown_guard kaydedildi")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="session_state'e kaydet")
    parser.add_argument("--telegram", action="store_true", help="DM uyarısı yolla")
    args = parser.parse_args()
    
    s = analiz_yap()
    yazdir(s)
    
    if args.apply:
        session_state_kaydet(s)
    if args.telegram:
        telegram_uyarisi(s)


if __name__ == "__main__":
    main()
