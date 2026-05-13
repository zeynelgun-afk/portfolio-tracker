# -*- coding: utf-8 -*-
"""
DISCOVERY ENGINE
=================
Mevcut watchlist'in disinda taze kaliteli adaylar bulur.

Akis:
1. data/daily_full_scan.json'dan PEG-filtreli 476 hisseyi al
2. Her birini swing_entry_engine.enhanced_entry_analysis ile tara
3. Kalite skoru >=55 olanlari (ORTA+) yeni adaylar olarak kaydet
4. Sonuc data/discovery_signals.json'a yaz
5. En iyi 10'u Telegram'a yolla (DM)

Kullanim:
  python scripts/discovery_engine.py            # Konsola yaz
  python scripts/discovery_engine.py --save     # JSON kaydet
  python scripts/discovery_engine.py --limit 30 # Sadece ilk 30 hisseyi tara
"""
import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))

sys.path.insert(0, str(REPO_ROOT / "scripts"))


def discover_from_universe(limit: int = None, min_skor: int = 55, 
                           min_mcap_b: float = 5.0, verbose: bool = False) -> list:
    """
    daily_full_scan'den PEG-filtreli hisseleri al,
    her birini kalite skoruyla degerlendir.
    """
    scan_path = REPO_ROOT / "data" / "daily_full_scan.json"
    if not scan_path.exists():
        print(f"[Discovery] {scan_path} yok — once full_universe_screener calistir")
        return []
    
    with open(scan_path) as f:
        scan = json.load(f)
    
    # PEG-filtreli sonuclar (uzaylsa marketCap >5B, RSI hesapli)
    sonuclar = scan.get("sonuclar", [])
    print(f"[Discovery] {len(sonuclar)} PEG-filtreli hisse, marketCap>={min_mcap_b}B filtresi uygulaniyor")
    
    # Marketcap filtresi
    aday_listesi = [s for s in sonuclar if (s.get("mcap_b") or 0) >= min_mcap_b]
    print(f"[Discovery] {len(aday_listesi)} hisse marketCap filtresinden gecti")
    
    # Aktif portföyde olanları cikar
    aktif_semboller = set()
    for pf in ["balanced", "aggressive", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if path.exists():
            d = json.load(open(path))
            for poz in d.get("pozisyonlar", []):
                sym = poz.get("sembol")
                if sym and sym != "_template":
                    aktif_semboller.add(sym)
    # Active swing
    sw = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
    for poz in sw.get("aktif_pozisyonlar", []):
        sym = poz.get("sembol")
        if sym:
            aktif_semboller.add(sym)
    
    aday_listesi = [s for s in aday_listesi if s.get("symbol") not in aktif_semboller]
    print(f"[Discovery] Aktif pozisyon dususu: {len(aday_listesi)}")
    
    if limit:
        aday_listesi = aday_listesi[:limit]
    
    print(f"[Discovery] {len(aday_listesi)} hisse swing engine'e gonderiliyor...")
    
    # Her birini analiz et
    from swing_entry_engine import enhanced_entry_analysis
    
    bulunan = []
    for i, s in enumerate(aday_listesi, 1):
        sym = s.get("symbol")
        if not sym:
            continue
        try:
            r = enhanced_entry_analysis(sym)
        except Exception as e:
            if verbose:
                print(f"  [{i:3}/{len(aday_listesi)}] {sym} hata: {e}")
            continue
        
        karar = r.get("karar", "")
        skor = r.get("kalite_skor", 0)
        
        if "GİRİŞ ✅" in karar and skor >= min_skor:
            bulunan.append({
                "sembol": sym,
                "fiyat": r.get("price"),
                "stop": r.get("stop"),
                "hedef": r.get("target"),
                "stop_pct": r.get("stop_dist"),
                "rsi": r.get("rsi"),
                "kalite_skor": skor,
                "kalite_karar": r.get("kalite_karar"),
                "carpan": r.get("carpan"),
                "shares": r.get("shares"),
                "rejim": r.get("rejim"),
                "sektor_fark": r.get("sektor_fark"),
                "volume_rasyo": r.get("volume_rasyo"),
                "sinyaller": [s.get("tip") for s in r.get("sinyaller", [])],
                # Daily scan'den
                "company": s.get("company"),
                "sector": s.get("sector"),
                "mcap_b": s.get("mcap_b"),
                "fwd_pe": s.get("fwd_pe"),
                "peg": s.get("peg"),
                "eps_growth_2y": s.get("eps_growth_2y"),
            })
            if verbose:
                print(f"  [{i:3}/{len(aday_listesi)}] {sym} ✅ skor:{skor}")
        elif verbose and i % 20 == 0:
            print(f"  [{i:3}/{len(aday_listesi)}] taranan...")
    
    # Skor sırasına göre sırala
    bulunan.sort(key=lambda x: -x["kalite_skor"])
    return bulunan


def kayit_et(bulunan: list):
    out = REPO_ROOT / "data" / "discovery_signals.json"
    payload = {
        "tarih": datetime.now(TR).isoformat(),
        "toplam": len(bulunan),
        "min_skor": 55,
        "adaylar": bulunan,
    }
    with open(out, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[Discovery] {len(bulunan)} aday kaydedildi: {out}")


def telegram_oneri(bulunan: list, max_say: int = 10):
    """En iyi 10'u Telegram DM'e gonder"""
    if not bulunan:
        return
    try:
        import requests
    except ImportError:
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    dm_id = os.environ.get("TELEGRAM_PRIVATE_ID", "")
    if not (token and dm_id):
        return
    
    msg = f"🔍 *DISCOVERY* — {len(bulunan)} kaliteli aday bulundu\n\n"
    msg += "TOP {} (skor sirali):\n".format(min(max_say, len(bulunan)))
    msg += "```\n"
    msg += f"{'Sembol':6} {'Skor':>4} {'Cpn':>4} {'Sec':6} {'PEG':>5}\n"
    for b in bulunan[:max_say]:
        sek = (b.get("sector") or "")[:6]
        peg = b.get("peg")
        peg_str = f"{peg:.2f}" if isinstance(peg, (int,float)) else "—"
        msg += f"{b['sembol']:6} {b['kalite_skor']:>4} {b['carpan']:.1f}x {sek:6} {peg_str:>5}\n"
    msg += "```"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, data={
            "chat_id": dm_id, "text": msg, "parse_mode": "Markdown"
        }, timeout=10)
        if r.status_code == 200:
            print(f"[Discovery] Telegram DM gonderildi")
    except Exception as e:
        print(f"[Discovery] Telegram hata: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="JSON kaydet")
    parser.add_argument("--telegram", action="store_true", help="Telegram'a yolla")
    parser.add_argument("--limit", type=int, help="Sadece ilk N hisseyi tara")
    parser.add_argument("--min-skor", type=int, default=55, help="Min kalite skoru (default 55)")
    parser.add_argument("--min-mcap", type=float, default=5.0, help="Min market cap B$ (default 5)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    
    print(f"[Discovery] Baslangic: {datetime.now(TR).isoformat()}")
    bulunan = discover_from_universe(
        limit=args.limit, 
        min_skor=args.min_skor, 
        min_mcap_b=args.min_mcap,
        verbose=args.verbose
    )
    
    print(f"\n{'='*70}")
    print(f"BULUNAN ADAYLAR ({len(bulunan)}) — skor>=  {args.min_skor}")
    print(f"{'='*70}")
    print(f"{'Sembol':6} {'Skor':>5} {'Karar':6} {'Cpn':>5} {'Fiyat':>8} {'PEG':>5} {'Sektör':15}")
    print("-" * 70)
    for b in bulunan[:20]:
        sek = (b.get("sector") or "?")[:15]
        peg = b.get("peg")
        peg_str = f"{peg:.2f}" if isinstance(peg, (int,float)) else "—"
        print(f"{b['sembol']:6} {b['kalite_skor']:>5} {b['kalite_karar']:6} "
              f"{b['carpan']:>4.2f}x ${b['fiyat']:>7.2f} {peg_str:>5} {sek:15}")
    
    if args.save:
        kayit_et(bulunan)
    
    if args.telegram:
        telegram_oneri(bulunan)


if __name__ == "__main__":
    main()
