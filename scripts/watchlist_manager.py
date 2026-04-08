#!/usr/bin/env python3
"""
Watchlist Manager — data/watchlist.json için CRUD işlemleri ve otomatik temizlik.

Kullanım:
  python scripts/watchlist_manager.py list                               # tüm adaylar
  python scripts/watchlist_manager.py list --portfoy dengeli             # portföye göre
  python scripts/watchlist_manager.py show SEMBOL                        # tek sembol detayı
  python scripts/watchlist_manager.py add SEMBOL --portfoy agresif       # mekanik skora göre ekle
  python scripts/watchlist_manager.py remove SEMBOL                      # elle çıkar
  python scripts/watchlist_manager.py refresh                            # tüm adayları yeniden skorla
  python scripts/watchlist_manager.py cleanup                            # kurallara göre otomatik eleme
  python scripts/watchlist_manager.py cooldown                           # cool-down durumunu göster

Eleme kuralları (cleanup):
  1) bekleme_gun > 10: soğutma süresi dolmuş, karar GEÇ ise sil
  2) karar "GEÇ" + skor eşiğin çok altında (İZLE eşiğinin %70'i): sil
  3) son_kontrol > 14 gün önce: "eski" etiketi (elle kontrol gerekli)

Cool-down mantığı:
  - Bir sembol bir kez satıldığında closed.json'a yazılır. O sembolü tekrar eklemek için
    satış tarihinden bu yana min 7 gün geçmesi gerekir (trade hatası tekrarını önlemek için).
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_scan_common as psc

REPO_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = REPO_ROOT / "data" / "watchlist.json"
SWING_CLOSED_PATH = REPO_ROOT / "data" / "swing" / "closed.json"
TODAY = datetime.now().date()

COOLDOWN_GUN = 7  # bir sembol kapandıktan sonra tekrar ekleme için bekleme süresi


# ============================================================
# I/O
# ============================================================

def load_watchlist():
    if not WATCHLIST_PATH.exists():
        return {"son_guncelleme": "", "izleme_listesi": []}
    with open(WATCHLIST_PATH) as f:
        return json.load(f)


def save_watchlist(wl):
    wl["son_guncelleme"] = datetime.now().isoformat()
    with open(WATCHLIST_PATH, "w") as f:
        json.dump(wl, f, indent=2, ensure_ascii=False)
    print(f"[WATCHLIST] Kaydedildi: {WATCHLIST_PATH}")


def load_closed_swing():
    """Kapatılmış swing trade'lerinden son satış tarihlerini döndürür."""
    if not SWING_CLOSED_PATH.exists():
        return {}
    with open(SWING_CLOSED_PATH) as f:
        data = json.load(f)
    last_exit = {}
    for t in data.get("kapatilan_pozisyonlar", []):
        sym = t.get("sembol", "")
        exit_date = t.get("cikis_tarihi", "")
        if sym and exit_date:
            try:
                dt = datetime.fromisoformat(exit_date).date()
                if sym not in last_exit or dt > last_exit[sym]:
                    last_exit[sym] = dt
            except Exception:
                pass
    return last_exit


# ============================================================
# CRUD
# ============================================================

def cmd_list(args):
    wl = load_watchlist()
    liste = wl.get("izleme_listesi", [])
    if args.portfoy:
        liste = [x for x in liste if x.get("hedef_portfoy") == args.portfoy]
    
    if not liste:
        print(f"(boş) — portföy filtresi: {args.portfoy or 'yok'}")
        return
    
    print(f"\n{'─'*70}")
    print(f"  {'sembol':7s} | {'portföy':9s} | {'skor':>4s} | {'RSI':>5s} | {'karar':8s} | urgency")
    print(f"  {'─'*7}-+-{'─'*9}-+-{'─'*4}-+-{'─'*5}-+-{'─'*8}-+-{'─'*7}")
    for x in sorted(liste, key=lambda z: -z.get("skor", 0)):
        sym = x.get("sembol", "?")
        port = x.get("hedef_portfoy", "?")
        skor = x.get("skor", 0)
        rsi = x.get("rsi", 0)
        karar = x.get("karar", "?")
        urg = x.get("urgency", "-")
        print(f"  {sym:7s} | {port:9s} | {skor:>4d} | {rsi:>5.1f} | {karar:8s} | {urg}")
    print(f"{'─'*70}")
    print(f"  Toplam: {len(liste)} aday")


def cmd_show(args):
    wl = load_watchlist()
    sym = args.symbol.upper()
    for x in wl.get("izleme_listesi", []):
        if x.get("sembol") == sym:
            print(json.dumps(x, indent=2, ensure_ascii=False))
            return
    print(f"[HATA] {sym} watchlist'te yok")
    sys.exit(1)


def cmd_add(args):
    sym = args.symbol.upper()
    portfoy = args.portfoy.lower()
    
    if portfoy not in ("dengeli", "agresif", "temettü"):
        print(f"[HATA] Portföy {portfoy} geçersiz. Seçenekler: dengeli, agresif, temettü")
        sys.exit(1)
    
    # Cool-down kontrolü
    last_exit = load_closed_swing()
    if sym in last_exit:
        gun = (TODAY - last_exit[sym]).days
        if gun < COOLDOWN_GUN:
            print(f"[COOL-DOWN] {sym} son satış {gun} gün önce, "
                  f"{COOLDOWN_GUN} gün bekleme süresi dolmadı. Ekleme iptal.")
            sys.exit(1)
    
    # Mevcut kontrol
    wl = load_watchlist()
    for x in wl.get("izleme_listesi", []):
        if x.get("sembol") == sym:
            print(f"[UYARI] {sym} zaten watchlist'te (skor {x.get('skor')}, "
                  f"portföy {x.get('hedef_portfoy')}, karar {x.get('karar')})")
            sys.exit(1)
    
    # Skor hesapla
    print(f"[ADD] {sym} için {portfoy} skor hesaplanıyor...")
    data = psc.get_full_data(sym)
    if not data or not data.get("price"):
        print(f"[HATA] {sym} için FMP verisi alınamadı")
        sys.exit(1)
    
    if portfoy == "dengeli":
        from portfolio_scan_balanced import mevcut_sektorler as msl
        _, existing = msl()
        score, detail = psc.score_dengeli(data, existing_sectors=existing)
    elif portfoy == "agresif":
        score, detail = psc.score_agresif(data)
    else:
        from portfolio_scan_dividend import mevcut_sektorler as msl
        _, existing = msl()
        score, detail = psc.score_temettü(data, existing_sectors=existing)
    
    karar = psc.get_decision(score, portfoy)
    eş = psc.THRESHOLDS[portfoy]
    
    if karar == "GEÇ":
        print(f"[UYARI] {sym} skor {score} < İZLE eşiği {eş['izle']}. "
              f"Yine de eklemek için --force kullan.")
        if not args.force:
            sys.exit(1)
    
    sector, _, tema = psc.get_sector_info(sym)
    yeni = {
        "sembol": sym,
        "hedef_portfoy": portfoy,
        "guncel_fiyat": round(data.get("price", 0), 2),
        "rsi": round(data.get("rsi_14", 0), 1),
        "skor": score,
        "skor_detay": " | ".join(detail),
        "sektor": sector,
        "tema": tema,
        "urgency": "high" if score >= eş["ekle"] else ("medium" if score >= eş["izle"] else "low"),
        "ekleme_tarihi": str(TODAY),
        "son_kontrol": str(TODAY),
        "bekleme_gun": 0,
        "karar": karar,
    }
    
    wl.setdefault("izleme_listesi", []).append(yeni)
    save_watchlist(wl)
    print(f"[ADD ✓] {sym} eklendi — skor {score}, karar {karar}, urgency {yeni['urgency']}")


def cmd_remove(args):
    sym = args.symbol.upper()
    wl = load_watchlist()
    liste = wl.get("izleme_listesi", [])
    yeni_liste = [x for x in liste if x.get("sembol") != sym]
    if len(yeni_liste) == len(liste):
        print(f"[UYARI] {sym} watchlist'te yok")
        sys.exit(1)
    wl["izleme_listesi"] = yeni_liste
    save_watchlist(wl)
    print(f"[REMOVE ✓] {sym} çıkarıldı. Kalan: {len(yeni_liste)} aday")


def cmd_refresh(args):
    """Tüm watchlist adaylarını yeniden skorla."""
    wl = load_watchlist()
    liste = wl.get("izleme_listesi", [])
    if not liste:
        print("(boş watchlist)")
        return
    
    from portfolio_scan_balanced import mevcut_sektorler as msl_d
    from portfolio_scan_dividend import mevcut_sektorler as msl_t
    _, denge_sek = msl_d()
    _, temet_sek = msl_t()
    
    print(f"[REFRESH] {len(liste)} aday yeniden skorlanıyor...")
    degisti = 0
    for x in liste:
        sym = x.get("sembol", "")
        port = x.get("hedef_portfoy", "")
        data = psc.get_full_data(sym)
        if not data or not data.get("price"):
            print(f"  {sym}: veri alınamadı, atlandı")
            continue
        
        if port == "dengeli":
            score, detail = psc.score_dengeli(data, existing_sectors=denge_sek)
        elif port == "agresif":
            score, detail = psc.score_agresif(data)
        elif port == "temettü":
            score, detail = psc.score_temettü(data, existing_sectors=temet_sek)
        else:
            continue
        
        eski_skor = x.get("skor", 0)
        eski_karar = x.get("karar", "?")
        yeni_karar = psc.get_decision(score, port)
        
        x["guncel_fiyat"] = round(data.get("price", 0), 2)
        x["rsi"] = round(data.get("rsi_14", 0), 1)
        x["skor"] = score
        x["skor_detay"] = " | ".join(detail)
        x["son_kontrol"] = str(TODAY)
        x["karar"] = yeni_karar
        x["bekleme_gun"] = x.get("bekleme_gun", 0) + 1
        
        if eski_skor != score or eski_karar != yeni_karar:
            degisti += 1
            print(f"  {sym}: {eski_skor}→{score} ({eski_karar}→{yeni_karar})")
        else:
            print(f"  {sym}: sabit skor {score}")
    
    save_watchlist(wl)
    print(f"[REFRESH ✓] {degisti}/{len(liste)} adayda skor/karar değişti")


def cmd_cleanup(args):
    """Otomatik eleme kurallarına göre watchlist'i temizler."""
    wl = load_watchlist()
    liste = wl.get("izleme_listesi", [])
    if not liste:
        print("(boş)")
        return
    
    silinenler = []
    kalan = []
    for x in liste:
        sym = x.get("sembol", "")
        port = x.get("hedef_portfoy", "")
        skor = x.get("skor", 0)
        karar = x.get("karar", "")
        bekleme = x.get("bekleme_gun", 0)
        
        eş = psc.THRESHOLDS.get(port, {"izle": 6})
        izle_esik_70pct = eş["izle"] * 0.7
        
        sil = False
        sebep = ""
        
        # Kural 1: bekleme >10 + karar GEÇ
        if bekleme > 10 and karar == "GEÇ":
            sil = True
            sebep = f"bekleme {bekleme}g + karar GEÇ"
        # Kural 2: skor çok altında
        elif karar == "GEÇ" and skor < izle_esik_70pct:
            sil = True
            sebep = f"skor {skor} < %70 izle eşiği ({izle_esik_70pct:.1f})"
        
        if sil:
            silinenler.append((sym, sebep))
        else:
            kalan.append(x)
    
    wl["izleme_listesi"] = kalan
    
    print(f"[CLEANUP] {len(silinenler)} aday eleme kurallarını tetikledi:")
    for sym, sebep in silinenler:
        print(f"  - {sym}: {sebep}")
    
    # Eski etiket (bilgi amaçlı)
    print(f"\n[CLEANUP] Son kontrolü 14 günden eski adaylar:")
    eski = 0
    for x in kalan:
        sk = x.get("son_kontrol", "")
        try:
            sk_dt = datetime.fromisoformat(sk).date()
            if (TODAY - sk_dt).days > 14:
                print(f"  - {x.get('sembol')}: {(TODAY - sk_dt).days} gün")
                eski += 1
        except Exception:
            pass
    if eski == 0:
        print("  (yok)")
    
    if silinenler:
        save_watchlist(wl)
    else:
        print("\n[CLEANUP] Değişiklik yok")


def cmd_cooldown(args):
    """Kapanmış trade'lerin cool-down durumunu göster."""
    last_exit = load_closed_swing()
    if not last_exit:
        print("(kapanmış swing trade yok)")
        return
    
    print(f"\n{'─'*55}")
    print(f"  {'sembol':7s} | {'satış tarihi':12s} | {'gün':>4s} | durum")
    print(f"  {'─'*7}-+-{'─'*12}-+-{'─'*4}-+-{'─'*15}")
    for sym in sorted(last_exit, key=lambda s: last_exit[s], reverse=True):
        dt = last_exit[sym]
        gun = (TODAY - dt).days
        if gun < COOLDOWN_GUN:
            durum = f"🔒 {COOLDOWN_GUN - gun}g kaldı"
        else:
            durum = "✅ eklenebilir"
        print(f"  {sym:7s} | {str(dt):12s} | {gun:>4d} | {durum}")
    print(f"{'─'*55}")
    print(f"  Cool-down süresi: {COOLDOWN_GUN} gün")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Watchlist Manager")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    p_list = sub.add_parser("list", help="Tüm adayları listele")
    p_list.add_argument("--portfoy", choices=["dengeli", "agresif", "temettü"])
    
    p_show = sub.add_parser("show", help="Tek sembol detayı")
    p_show.add_argument("symbol")
    
    p_add = sub.add_parser("add", help="Sembol ekle (mekanik skorla)")
    p_add.add_argument("symbol")
    p_add.add_argument("--portfoy", required=True, choices=["dengeli", "agresif", "temettü"])
    p_add.add_argument("--force", action="store_true", help="Skor düşük olsa bile ekle")
    
    p_rem = sub.add_parser("remove", help="Sembol çıkar")
    p_rem.add_argument("symbol")
    
    sub.add_parser("refresh", help="Tüm adayları yeniden skorla")
    sub.add_parser("cleanup", help="Otomatik eleme kurallarını uygula")
    sub.add_parser("cooldown", help="Kapanan trade'lerin cool-down durumu")
    
    args = parser.parse_args()
    
    {
        "list": cmd_list,
        "show": cmd_show,
        "add": cmd_add,
        "remove": cmd_remove,
        "refresh": cmd_refresh,
        "cleanup": cmd_cleanup,
        "cooldown": cmd_cooldown,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
