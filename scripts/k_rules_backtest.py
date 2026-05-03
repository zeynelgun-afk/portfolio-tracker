# -*- coding: utf-8 -*-
"""
K-Kurallari Backtest Modulu
==========================
189 islemlik gercek transaction.csv'yi kullanarak her K-kuralinin
gercek getirisini, FIRSAT KACIRMASINI ve hata oranini olcer.

Kullanim:
  python scripts/k_rules_backtest.py            # Tum kurallari analiz et
  python scripts/k_rules_backtest.py --rule K-06 # Tek kural detay

Cikti: reports/backtest/k_rules_YYYY-MM-DD.md
"""
import csv
import os
import sys
import json
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[1]
KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")

def get_history(sym: str, from_date: str, to_date: str) -> list:
    """FMP historical-price-eod/full ile tarih araliginda fiyat verisi"""
    url = (f"https://financialmodelingprep.com/stable/historical-price-eod/full"
           f"?symbol={sym}&from={from_date}&to={to_date}&apikey={KEY}")
    try:
        r = requests.get(url, timeout=12)
        if r.status_code != 200:
            return []
        d = r.json()
        return d if isinstance(d, list) else []
    except Exception:
        return []


def kategori_belirle(reason: str) -> str:
    """Reason metnindenkategori cikar"""
    r = (reason or "").lower()
    if "k-06" in r or "stop tetik" in r:
        return "K-06"
    if "k-05" in r or "earnings oncesi" in r or "bilanco oncesi" in r or "earnings öncesi" in r:
        return "K-05"
    if "k-07" in r or "kar kilidi" in r or "kâr kilidi" in r:
        return "K-07"
    if "k-09" in r or "trailing" in r:
        return "K-09"
    if "k-11" in r or "rsi" in r:
        return "K-11"
    if "k-13" in r or "vix" in r:
        return "K-13"
    # Swing entry: ichimoku, tenkan_bounce, kijun_bounce, sma50_bounce, swing giris
    if ("ichimoku" in r or "tenkan_bounce" in r or "kijun_bounce" in r 
        or "sma50_bounce" in r or "nr7_sikisma" in r or "swing giriş" in r 
        or "swing giris" in r or "oversold bounce" in r):
        return "Swing-Giris"
    if "swing exit" in r or "swing cikis" in r or "swing çıkış" in r:
        return "Swing-Cikis"
    if "tema" in r or "opportunity" in r or "agresif v2" in r:
        return "Tema"
    if "claude" in r or "manuel" in r or "tez" in r:
        return "AI"
    return "Diger"


def what_if_satis(satis_tarihi: str, sembol: str, satis_fiyati: float, 
                   shares: float, gunler: list = [1, 5, 10, 20]) -> dict:
    """Bir SELL islemi icin: gun-N sonra fiyat ne olurdu?"""
    sat_dt = datetime.strptime(satis_tarihi, "%Y-%m-%d")
    end = (sat_dt + timedelta(days=max(gunler) + 15)).strftime("%Y-%m-%d")
    start = (sat_dt - timedelta(days=2)).strftime("%Y-%m-%d")
    
    hist = get_history(sembol, start, end)
    if not hist:
        return {"hata": "veri yok"}
    
    hist_asc = sorted(hist, key=lambda x: x.get("date", ""))
    after = [h for h in hist_asc if h.get("date", "") > satis_tarihi]
    
    sonuc = {"sembol": sembol, "tarih": satis_tarihi, "satis": satis_fiyati}
    for g in gunler:
        if len(after) >= g:
            fiyat = after[g - 1].get("close")
            if fiyat:
                pct = (fiyat - satis_fiyati) / satis_fiyati * 100
                kac_kazan = (fiyat - satis_fiyati) * shares
                sonuc[f"g{g}_pct"] = round(pct, 2)
                sonuc[f"g{g}_kazan"] = round(kac_kazan, 2)
                sonuc[f"g{g}_fiyat"] = round(fiyat, 2)
    return sonuc


def what_if_alis(alis_tarihi: str, sembol: str, alis_fiyati: float, 
                  shares: float, gunler: list = [1, 5, 10, 20]) -> dict:
    """Bir BUY islemi icin: gun-N sonra fiyat ne olurdu? (Pozitif = iyi alim)"""
    al_dt = datetime.strptime(alis_tarihi, "%Y-%m-%d")
    end = (al_dt + timedelta(days=max(gunler) + 15)).strftime("%Y-%m-%d")
    start = (al_dt - timedelta(days=2)).strftime("%Y-%m-%d")
    
    hist = get_history(sembol, start, end)
    if not hist:
        return {"hata": "veri yok"}
    
    hist_asc = sorted(hist, key=lambda x: x.get("date", ""))
    after = [h for h in hist_asc if h.get("date", "") > alis_tarihi]
    
    sonuc = {"sembol": sembol, "tarih": alis_tarihi, "alis": alis_fiyati}
    for g in gunler:
        if len(after) >= g:
            fiyat = after[g - 1].get("close")
            if fiyat:
                pct = (fiyat - alis_fiyati) / alis_fiyati * 100
                kazan = (fiyat - alis_fiyati) * shares
                sonuc[f"g{g}_pct"] = round(pct, 2)
                sonuc[f"g{g}_kazan"] = round(kazan, 2)
    return sonuc


def kategori_analiz(rows: list, kategori: str, action_filter: str = "SELL") -> dict:
    """Bir kategori icin tum islemleri analiz et."""
    iliskili = []
    for r in rows:
        if r["action"] != action_filter:
            continue
        if kategori_belirle(r.get("reason", "")) != kategori:
            continue
        iliskili.append(r)
    
    if not iliskili:
        return {"kategori": kategori, "sayi": 0}
    
    sonuclar = []
    for r in iliskili:
        try:
            if action_filter == "SELL":
                w = what_if_satis(r["date"], r["symbol"], 
                                   float(r["price"]), float(r["shares"]))
            else:
                w = what_if_alis(r["date"], r["symbol"],
                                  float(r["price"]), float(r["shares"]))
            if "hata" not in w:
                sonuclar.append(w)
        except Exception as e:
            print(f"  Hata {r['symbol']} {r['date']}: {e}")
    
    if not sonuclar:
        return {"kategori": kategori, "sayi": len(iliskili), "veri": 0}
    
    # Istatistikler
    def safe_avg(key):
        vals = [s[key] for s in sonuclar if key in s]
        return round(sum(vals) / len(vals), 2) if vals else None
    
    def safe_sum(key):
        return round(sum(s.get(key, 0) for s in sonuclar), 2)
    
    def yuksek_say(key):
        return sum(1 for s in sonuclar if s.get(key, 0) > 0)
    
    return {
        "kategori": kategori,
        "action": action_filter,
        "sayi": len(iliskili),
        "veri": len(sonuclar),
        "g1_avg_pct": safe_avg("g1_pct"),
        "g5_avg_pct": safe_avg("g5_pct"),
        "g10_avg_pct": safe_avg("g10_pct"),
        "g20_avg_pct": safe_avg("g20_pct"),
        "g5_yukselen": yuksek_say("g5_pct"),
        "g5_dusen": len(sonuclar) - yuksek_say("g5_pct"),
        "g5_toplam_kazan": safe_sum("g5_kazan"),
        "g20_toplam_kazan": safe_sum("g20_kazan"),
        "ornek": sonuclar[:3],
    }


def yorumla(stat: dict) -> str:
    """Istatistiklere bakip kuraldan ne ders cikiyor?"""
    if stat["sayi"] == 0:
        return "Yeterli veri yok."
    
    k = stat["kategori"]
    g5 = stat.get("g5_avg_pct")
    g20 = stat.get("g20_avg_pct")
    
    if stat["action"] == "SELL":
        if g5 is None:
            return "Veri eksik."
        # Stop kurallari icin
        if k in ("K-06", "K-05", "K-09", "Swing-Cikis"):
            if g5 < -2:
                yorum = f"GUCLU KURAL: 5g sonra ort {g5}% (kotu yon) — satis dogruydu, kayip onlendi."
            elif g5 < 0:
                yorum = f"NOTR: 5g sonra ort {g5}% (hafif kotu yon) — satis marjinal dogru."
            elif g5 < 5:
                yorum = f"ZAYIF: 5g sonra ort {g5}% (hafif kac) — bazi stoplar erken olabilir."
            else:
                yorum = f"BAGIMSIZ INCELEN: 5g sonra ort {g5}% (yuksek kac) — kural cok agresif olabilir."
            
            if g20 and g20 > 10:
                yorum += f" 20g sonra ort {g20}% — uzun vadede ciddi toparlanma var."
            return yorum
        
        # Kar al kurallari icin
        if k in ("K-07", "K-11"):
            if g5 < -3:
                yorum = f"GUCLU TIMING: 5g sonra ort {g5}% (zirve sonrasi dustu) — kar dogru zamanda alindi."
            elif g5 < 2:
                yorum = f"NOTR: 5g sonra ort {g5}% (yatay) — kar al timing'i orta."
            elif g5 < 8:
                yorum = f"ZAYIF: 5g sonra ort {g5}% (devam etti) — kar al biraz erken."
            else:
                yorum = f"YANLIS TIMING: 5g sonra ort {g5}% (gucle devam etti) — momentum kacirildi."
            return yorum
    
    # Alim kurallari icin
    else:
        if g5 is None:
            return "Veri eksik."
        if g5 > 5:
            return f"GUCLU GIRIS: 5g sonra ort +{g5}% — alim timing'i mukemmel."
        elif g5 > 0:
            return f"NOTR: 5g sonra ort +{g5}% — alim biraz iyi."
        elif g5 > -3:
            return f"ZAYIF: 5g sonra ort {g5}% — bazi alimlar erken."
        else:
            return f"YANLIS GIRIS: 5g sonra ort {g5}% — alim filtresi sikilastirmali."
    
    return "Yorum yok."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rule", help="Tek kural analizi (K-06, K-09, K-05, K-11, vb.)")
    parser.add_argument("--save", action="store_true", help="Sonucu reports/backtest'a kaydet")
    args = parser.parse_args()
    
    # Transactions oku
    csv_path = REPO_ROOT / "data" / "transactions.csv"
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    
    print(f"K-Kurallari Backtest — {len(rows)} islem analiz ediliyor")
    print("=" * 70)
    
    # Hangi kategoriler icin SELL ve BUY analiz edilecek
    sell_kategoriler = ["K-06", "K-05", "K-09", "K-11", "K-07"]
    buy_kategoriler = ["Swing-Giris", "Tema"]
    
    if args.rule:
        sell_kategoriler = [args.rule] if args.rule in sell_kategoriler else []
        buy_kategoriler = [args.rule] if args.rule in buy_kategoriler else []
    
    raporlar = []
    
    # SELL analizleri
    for k in sell_kategoriler:
        print(f"\n>>> {k} (SATIS analizi)")
        s = kategori_analiz(rows, k, "SELL")
        raporlar.append(s)
        if s["sayi"] == 0:
            print(f"  Yeterli veri yok.")
            continue
        print(f"  Toplam {k} satisi: {s['sayi']} | analiz edildi: {s['veri']}")
        if s.get("g5_avg_pct") is not None:
            print(f"  Satis sonrasi ort %:")
            print(f"    1 gun:  {s['g1_avg_pct']:+6.2f}%")
            print(f"    5 gun:  {s['g5_avg_pct']:+6.2f}%")
            print(f"    10 gun: {s['g10_avg_pct']:+6.2f}%" if s.get('g10_avg_pct') else "")
            print(f"    20 gun: {s['g20_avg_pct']:+6.2f}%" if s.get('g20_avg_pct') else "")
            print(f"  5g sonra YUKSELDI: {s['g5_yukselen']}/{s['veri']} ({s['g5_yukselen']/s['veri']*100:.0f}%)")
            print(f"  5g sonra DUSTU: {s['g5_dusen']}/{s['veri']} ({s['g5_dusen']/s['veri']*100:.0f}%)")
            print(f"  Yorum: {yorumla(s)}")
    
    # BUY analizleri
    for k in buy_kategoriler:
        print(f"\n>>> {k} (ALIM analizi)")
        s = kategori_analiz(rows, k, "BUY")
        raporlar.append(s)
        if s["sayi"] == 0:
            continue
        print(f"  Toplam {k} alimi: {s['sayi']} | analiz edildi: {s['veri']}")
        if s.get("g5_avg_pct") is not None:
            print(f"  Alim sonrasi ort %:")
            print(f"    1 gun:  {s['g1_avg_pct']:+6.2f}%")
            print(f"    5 gun:  {s['g5_avg_pct']:+6.2f}%")
            print(f"    10 gun: {s['g10_avg_pct']:+6.2f}%" if s.get('g10_avg_pct') else "")
            print(f"    20 gun: {s['g20_avg_pct']:+6.2f}%" if s.get('g20_avg_pct') else "")
            print(f"  Yorum: {yorumla(s)}")
    
    # Genel ozet
    print(f"\n{'='*70}")
    print("GENEL OZET")
    print(f"{'='*70}")
    print(f"{'Kural':12} {'Sayi':>6} {'5g %':>10} {'20g %':>10} {'Karar':30}")
    print("-" * 70)
    for s in raporlar:
        if s["sayi"] == 0:
            continue
        karar = ""
        g5 = s.get("g5_avg_pct")
        if s.get("action") == "SELL" and g5 is not None:
            if g5 < -2: karar = "DOGRU"
            elif g5 < 5: karar = "MARJINAL"
            else: karar = "AGRESIF (gevsetilmeli?)"
        elif s.get("action") == "BUY" and g5 is not None:
            if g5 > 5: karar = "MUKEMMEL"
            elif g5 > 0: karar = "IYI"
            else: karar = "ZAYIF"
        
        g5_str = f"{g5:+.2f}%" if g5 is not None else "—"
        g20 = s.get("g20_avg_pct")
        g20_str = f"{g20:+.2f}%" if g20 is not None else "—"
        print(f"{s['kategori']:12} {s['sayi']:>6} {g5_str:>10} {g20_str:>10} {karar:30}")
    
    # Markdown rapor olustur
    if args.save:
        bugun = datetime.now().strftime("%Y-%m-%d")
        out_dir = REPO_ROOT / "reports" / "backtest"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"k_rules_{bugun}.md"
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# K-Kurallari Backtest Raporu — {bugun}\n\n")
            f.write(f"**Analiz edilen islem sayisi:** {len(rows)}\n")
            f.write(f"**Tarih araligi:** {rows[0]['date']} → {rows[-1]['date']}\n\n")
            f.write("## Ozet Tablo\n\n")
            f.write("| Kural | Islem Sayisi | 5g Sonra Ort % | 20g Sonra Ort % | Karar |\n")
            f.write("|-------|---|---|---|---|\n")
            for s in raporlar:
                if s["sayi"] == 0:
                    continue
                g5 = s.get("g5_avg_pct")
                g20 = s.get("g20_avg_pct")
                karar = "—"
                if s.get("action") == "SELL" and g5 is not None:
                    if g5 < -2: karar = "✅ Dogru"
                    elif g5 < 5: karar = "⚠️ Marjinal"
                    else: karar = "🔴 Cok agresif"
                elif s.get("action") == "BUY" and g5 is not None:
                    if g5 > 5: karar = "✅ Mukemmel"
                    elif g5 > 0: karar = "⚠️ Iyi"
                    else: karar = "🔴 Zayif"
                f.write(f"| {s['kategori']} | {s['sayi']} | {g5:+.2f}% | {g20:+.2f}% | {karar} |\n" 
                        if g5 is not None and g20 is not None else
                        f"| {s['kategori']} | {s['sayi']} | — | — | — |\n")
            
            f.write("\n## Detayli Yorumlar\n\n")
            for s in raporlar:
                if s["sayi"] == 0:
                    continue
                f.write(f"### {s['kategori']} ({s['sayi']} islem)\n\n")
                f.write(f"**Yorum:** {yorumla(s)}\n\n")
        
        print(f"\nRapor kaydedildi: {out_path}")
    
    # JSON ozet
    out_json = REPO_ROOT / "data" / "backtest_summary.json"
    with open(out_json, "w") as f:
        json.dump({"tarih": datetime.now().isoformat(), "raporlar": raporlar}, f, indent=2)
    print(f"\nJSON ozet: {out_json}")


if __name__ == "__main__":
    main()
