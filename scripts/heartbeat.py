#!/usr/bin/env python3
"""
Finzora AI — Günlük Sistem Sağlık Özeti
========================================
Her gün piyasa kapanışından sonra çalışır.
Sistemin ne yaptığını, ne yapamadığını özetler.

Kullanım:
  python scripts/heartbeat.py
  python scripts/heartbeat.py --mode ozet   # kısa özet
  python scripts/heartbeat.py --mode tam    # tam rapor
"""

import os, sys, json, argparse, requests
from datetime import datetime, date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PRIVATE_ID = os.environ.get("TELEGRAM_PRIVATE_ID", "") or os.environ.get("TELEGRAM_PRIVATE_CHAT", "")
API        = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOG_FILE   = ROOT / "logs" / "event_log.jsonl"


def send(text: str):
    payload = {"chat_id": PRIVATE_ID, "text": text,
               "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=15)
        return r.json().get("ok", False)
    except Exception as e:
        print(f"Telegram hatası: {e}")
        return False


def _load(path: str) -> dict | list:
    full = ROOT / path
    if not full.exists():
        return {}
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def portfoy_ozeti() -> dict:
    """3 portföyün anlık durumu."""
    sonuclar = {}
    for isim, dosya in [("Dengeli","balanced"), ("Agresif","aggressive"), ("Temettü","dividend")]:
        try:
            d = _load(f"data/portfolios/{dosya}.json")
            nakit = d.get("nakit", {}).get("miktar", 0)
            pozlar = d.get("pozisyonlar", [])
            total  = nakit + sum(p.get("guncel_deger", 0) for p in pozlar)
            basla  = d.get("baslangic_sermaye", 0)
            pnl_pct = ((total - basla) / basla * 100) if basla else 0
            sonuclar[isim] = {
                "total": total, "pnl_pct": pnl_pct,
                "pozisyon": len(pozlar), "nakit": nakit,
                "semboller": [p["sembol"] for p in pozlar]
            }
        except Exception as e:
            sonuclar[isim] = {"hata": str(e)}
    return sonuclar


def swing_ozeti() -> dict:
    """Swing trade durumu."""
    try:
        d = _load("data/swing/active.json")
        pozlar = d.get("aktif_pozisyonlar", [])
        return {
            "aktif": len(pozlar),
            "semboller": [p["sembol"] for p in pozlar],
            "pozisyonlar": [
                {"sembol": p["sembol"],
                 "pnl": p.get("pnl_pct", 0),
                 "gun": p.get("tutulan_gun", 0)}
                for p in pozlar
            ]
        }
    except Exception as e:
        return {"hata": str(e)}


def bugunun_olaylari() -> dict:
    """event_log.jsonl'dan bugünün istatistikleri."""
    if not LOG_FILE.exists():
        return {"toplam": 0, "seviyeler": {}, "hatalar": []}

    bugun = date.today().isoformat()
    olaylar = []
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            for satir in f:
                try:
                    e = json.loads(satir)
                    if e.get("zaman", "").startswith(bugun):
                        olaylar.append(e)
                except:
                    pass
    except:
        pass

    seviyeler = {}
    hatalar   = []
    islemler  = []
    for e in olaylar:
        sev = e.get("seviye", "?")
        seviyeler[sev] = seviyeler.get(sev, 0) + 1
        if sev in ("hata", "kritik"):
            hatalar.append(f"{e.get('baslik','?')}: {e.get('detay','')[:80]}")
        if sev == "islem":
            islemler.append(e.get("baslik", "?"))

    return {
        "toplam": len(olaylar),
        "seviyeler": seviyeler,
        "hatalar": hatalar[:5],
        "islemler": islemler[:10],
    }


def workflow_durumu() -> dict:
    """Son workflow çalışmalarını kontrol et (log dosyasından)."""
    if not LOG_FILE.exists():
        return {}
    
    son_24saat = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    calistirmalar = []
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            for satir in f:
                try:
                    e = json.loads(satir)
                    if e.get("seviye") == "calistirma" and e.get("zaman","") > son_24saat:
                        calistirmalar.append({
                            "zaman": e["zaman"][11:16],
                            "baslik": e.get("baslik","?"),
                            "kaynak": e.get("kaynak","?")
                        })
                except:
                    pass
    except:
        pass
    return {"son_24saat": calistirmalar[-10:]}


def format_rapor(mod: str = "ozet") -> str:
    portfoy = portfoy_ozeti()
    swing   = swing_ozeti()
    olaylar = bugunun_olaylari()
    wf      = workflow_durumu()

    bugun   = datetime.now().strftime("%d.%m.%Y")
    simdi   = datetime.now().strftime("%H:%M")

    # Portföy toplam
    toplam_val  = sum(v.get("total", 0) for v in portfoy.values() if "hata" not in v)
    baslangic   = 600_000
    toplam_pnl  = ((toplam_val - baslangic) / baslangic * 100) if baslangic else 0
    pnl_emoji   = "📈" if toplam_pnl >= 0 else "📉"

    # Bugünün olayları özeti
    hata_sayisi = olaylar["seviyeler"].get("hata", 0) + olaylar["seviyeler"].get("kritik", 0)
    islem_sayisi = olaylar["seviyeler"].get("islem", 0)
    sistem_emoji = "✅" if hata_sayisi == 0 else ("⚠️" if hata_sayisi < 3 else "🚨")

    msg = f"""<b>📊 FİNZORA GÜNLÜK ÖZET</b>
<i>{bugun} {simdi}</i>
{'─' * 28}

{pnl_emoji} <b>Toplam: ${toplam_val:,.0f} ({toplam_pnl:+.2f}%)</b>
"""

    # Portföy satırları
    for isim, v in portfoy.items():
        if "hata" in v:
            msg += f"  ❌ {isim}: veri hatası\n"
        else:
            e = "🟢" if v["pnl_pct"] >= 0 else "🔴"
            msg += (f"  {e} {isim}: ${v['total']:,.0f} ({v['pnl_pct']:+.1f}%)"
                    f" | {v['pozisyon']} poz | ${v['nakit']:,.0f} nakit\n")

    # Swing
    if "hata" not in swing:
        sw_e = "⚡" if swing["aktif"] > 0 else "—"
        msg += f"\n{sw_e} <b>Swing</b>: {swing['aktif']}/8 aktif"
        if swing.get("pozisyonlar"):
            msg += "\n"
            for p in swing["pozisyonlar"]:
                e = "🟢" if p["pnl"] >= 0 else "🔴"
                msg += f"  {e} {p['sembol']} {p['pnl']:+.1f}% ({p['gun']}g)\n"

    msg += f"\n{'─' * 28}\n"
    msg += f"{sistem_emoji} <b>Sistem Durumu</b>\n"
    msg += f"  Bugünkü olaylar: {olaylar['toplam']} kayıt\n"
    msg += f"  İşlemler: {islem_sayisi} | Hatalar: {hata_sayisi}\n"

    # Hatalar varsa listele
    if olaylar["hatalar"]:
        msg += "\n<b>⚠️ Bugünkü Hatalar</b>\n"
        for h in olaylar["hatalar"]:
            msg += f"  • {h[:100]}\n"

    # Bugünkü işlemler
    if olaylar.get("islemler") and mod == "tam":
        msg += "\n<b>💱 Bugünkü İşlemler</b>\n"
        for i in olaylar["islemler"]:
            msg += f"  • {i}\n"

    # Son çalışmalar
    if wf.get("son_24saat") and mod == "tam":
        msg += "\n<b>🔄 Son Agent Çalışmaları</b>\n"
        for w in wf["son_24saat"][-5:]:
            msg += f"  {w['zaman']} {w['baslik']}\n"

    msg += f"\n<i>finzora ai • {simdi}</i>"
    return msg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["ozet","tam"], default="ozet")
    args = parser.parse_args()

    rapor = format_rapor(args.mode)
    print(rapor)
    ok = send(rapor)
    print(f"\n→ Telegram: {'✅ gönderildi' if ok else '❌ başarısız'}")


if __name__ == "__main__":
    main()
