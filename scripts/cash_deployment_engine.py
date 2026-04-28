# -*- coding: utf-8 -*-
"""
K-22 NAKIT KULLANIM ENGINE
============================
Memory: '3 portföyde nakit oranı %10'u GEÇMESİN. Claude otomatik yönetiyor.'

Bu modül:
1. Her portföyün gerçek nakit oranını hesaplar
2. >%10 ise dağıtım stratejisi önerir
3. Portföy tipine göre farklı yaklaşım:
   - AGGRESSIVE: swing sinyalleri + uranyum/AI tema + inverse ETF (volatil günler)
   - BALANCED: defansif rotasyon (XLP/XLV/GLD/TLT) veya inverse ETF max %10
   - DIVIDEND: SADECE temettü hisseleri (KO/PG/JNJ/VZ/KMB/MO/MCD/CL)
4. session_state.json'a oneriler yazar — Claude FAZ_2'de uygular

Kullanim:
  python scripts/cash_deployment_engine.py            # Konsola onerileri yaz
  python scripts/cash_deployment_engine.py --apply   # session_state'e kaydet
  python scripts/cash_deployment_engine.py --vix 18   # VIX manuel
"""
import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))

# Memory'den parametreler
NAKIT_LIMIT_PCT = 10  # %10 üzeri = aksiyon gerek
NAKIT_KRITIK_PCT = 30  # %30 üzeri = kritik
HEDEF_NAKIT_PCT = 5  # Aksiyon sonrası hedef nakit oranı

# Defansif sektör ETF listesi (memory: BALANCED)
DEFANSIF_ETF = ["XLP", "XLV", "GLD", "TLT"]

# Dividend portfoy uygun semboller (memory)
DIVIDEND_UYGUN = ["KO", "PG", "JNJ", "VZ", "KMB", "MO", "MCD", "CL"]

# Inverse ETF (memory: AGGRESSIVE serbest, BALANCED max %10 sadece düşük kaldıraçlı)
INVERSE_DUSUK_KALDIRAC = ["SH", "SDOW"]  # 1x veya düşük
INVERSE_YUKSEK_KALDIRAC = ["SQQQ", "SDOW3X"]  # 3x — sadece AGGRESSIVE

# K-12 limitleri (memory: Balanced 25%/Aggressive 20%/Dividend 15%)
K12_TEK_POZISYON_MAX = {"balanced": 25, "aggressive": 20, "dividend": 15}


def get_vix() -> float:
    """FMP'den canlı VIX, başarısız olursa 20 (nötr)"""
    import requests
    KEY = os.environ.get("FMP_API_KEY", "")
    if not KEY:
        return 20.0
    try:
        r = requests.get(f"https://financialmodelingprep.com/stable/quote?symbol=^VIX&apikey={KEY}", timeout=8)
        if r.status_code == 200:
            d = r.json()
            if isinstance(d, list) and d:
                return float(d[0].get("price") or 20)
    except Exception:
        pass
    return 20.0


def portfoy_durumu(pf_data: dict) -> dict:
    """Portföyün nakit, pozisyon, slot durumu"""
    bas = pf_data.get("baslangic_sermaye", 0) or 0
    
    pos_deger = 0
    aktif_semboller = []
    aktif_sektorler = {}
    for poz in pf_data.get("pozisyonlar", []):
        sym = poz.get("sembol")
        if sym in (None, "_template"):
            continue
        adet = poz.get("adet", 0) or 0
        cf = poz.get("guncel_fiyat", 0) or 0
        deger = adet * cf
        pos_deger += deger
        aktif_semboller.append(sym)
        sek = poz.get("sektor", "Bilinmiyor")
        aktif_sektorler[sek] = aktif_sektorler.get(sek, 0) + deger

    nakit_obj = pf_data.get("nakit", 0)
    if isinstance(nakit_obj, dict):
        nakit = nakit_obj.get("miktar", 0) or 0
    else:
        nakit = float(nakit_obj or 0)

    mevcut = pos_deger + nakit
    nakit_pct = (nakit / mevcut * 100) if mevcut else 0
    
    # Max pozisyon (memory: max 6)
    max_pos = pf_data.get("maksimum_pozisyon", 6) or 6
    bos_slot = max_pos - len(aktif_semboller)

    return {
        "baslangic": bas,
        "mevcut_deger": mevcut,
        "pozisyon_deger": pos_deger,
        "nakit": nakit,
        "nakit_pct": nakit_pct,
        "aktif_semboller": aktif_semboller,
        "aktif_sektorler": aktif_sektorler,
        "bos_slot": bos_slot,
        "max_pozisyon": max_pos,
    }


def hedef_nakit_kullanim(durum: dict) -> float:
    """Ne kadar nakitin kullanılması gerek (USD)"""
    nakit_pct = durum["nakit_pct"]
    if nakit_pct <= NAKIT_LIMIT_PCT:
        return 0
    fazla_pct = nakit_pct - HEDEF_NAKIT_PCT
    fazla_usd = (fazla_pct / 100) * durum["mevcut_deger"]
    return round(fazla_usd, 0)


def _bekleyen_cikis_semboller() -> set:
    """session_state.claude_kararlar'da ÇIK/SAT bekleyen semboller"""
    ss_path = REPO_ROOT / "data" / "session_state.json"
    if not ss_path.exists():
        return set()
    try:
        ss = json.load(open(ss_path))
        ck = ss.get("claude_kararlar", {})
        if ck.get("executed"):
            return set()  # Eski karar, geçerli değil
        kararlar = ck.get("kararlar", [])
        return {k["sembol"] for k in kararlar 
                if k.get("tip") in ("ÇIK", "SAT", "BUYUT-AZALT")}
    except Exception:
        return set()


def aggressive_strateji(durum: dict, vix: float) -> dict:
    """
    Memory: AGGRESSIVE — inverse ETF + put serbest, swing sinyalleri uygun.
    Backtest: tenkan_bounce/ichimoku +%8 (10g) — bu sinyaller tercih edilmeli.
    
    K-23 entegrasyon (28 Nis 2026): drawdown DEFANSIF/HEDGE/STOP ise saldiri yok.
    """
    kullanilacak = hedef_nakit_kullanim(durum)
    if kullanilacak <= 0:
        return {"oneriler": [], "kullanilacak_nakit": 0}
    
    # K-23 drawdown guard (yeni)
    k23_kod = 0
    k23_seviye = "NORMAL"
    try:
        from portfolio_drawdown_guard import analiz_yap as _k23_a
        s = _k23_a()
        agg = s["portfoyler"].get("aggressive", {}).get("k23", {})
        toplam = s["toplam"]["k23"]
        k23_kod = max(agg.get("kod", 0), toplam.get("kod", 0))
        k23_seviye = max([(agg.get("kod",0), agg.get("seviye","NORMAL")), 
                          (toplam.get("kod",0), toplam.get("seviye","NORMAL"))], 
                         key=lambda x: x[0])[1]
    except Exception:
        pass
    
    # Bekleyen ÇIKIŞ kararları olan semboller → öneri YASAK
    cikis_bekleyen = _bekleyen_cikis_semboller()
    
    # K-23 STOP_TRADING ise hicbir aksiyon yok
    if k23_kod >= 4:
        return {
            "oneriler": [],
            "kullanilacak_nakit": kullanilacak,
            "vix": vix,
            "k23_durdurma": f"K-23/{k23_kod}: {k23_seviye} — saldiri YOK",
        }
    
    # K-23 HEDGE seviyesi: hedge ETF zorunlu, swing yok
    if k23_kod >= 3:
        return {
            "oneriler": [{
                "sembol": "SQQQ",
                "tip": "AL (HEDGE-K23)",
                "kaynak": "k23-hedge",
                "tutar": kullanilacak * 0.5,
                "neden": f"K-23/{k23_kod}: {k23_seviye} — inverse ETF zorunlu",
                "oncelik": "yuksek",
            }],
            "kullanilacak_nakit": kullanilacak,
            "vix": vix,
            "k23_durdurma": k23_seviye,
        }
    
    # K-23 DEFANSIF: swing/saldiri yok, defansif ETF
    if k23_kod >= 2:
        defansif_oneriler = []
        for etf in DEFANSIF_ETF[:3]:
            if etf in durum["aktif_semboller"]:
                continue
            defansif_oneriler.append({
                "sembol": etf,
                "tip": "AL (DEFANSIF-K23)",
                "kaynak": "k23-defansif-rotasyon",
                "tutar": kullanilacak / 3,
                "neden": f"K-23/{k23_kod}: {k23_seviye} — defansif ETF (saldiri yasak)",
                "oncelik": "yuksek",
            })
        return {
            "oneriler": defansif_oneriler,
            "kullanilacak_nakit": kullanilacak,
            "vix": vix,
            "k23_seviye": k23_seviye,
        }
    
    # K-23 NORMAL/UYARI: standart akış (swing sinyalleri + tema)
    
    # K-12 v2 dinamik limit (28 Nis 2026): tema skorlu sektör için yumuşama
    # AI tema 9 GUCLU + RS +%7.5 → aggressive sektör limiti %40 → %60
    try:
        from k12_dynamic_limits import k12_v2_analiz
        # Aggressive icin
        path = REPO_ROOT / "data" / "portfolios" / "aggressive.json"
        d_pf = json.load(open(path))
        k12_durum = k12_v2_analiz("aggressive", d_pf, vix, 0)  # K-23 NORMAL bu blokta
    except Exception:
        k12_durum = {}
    
    # Mevcut swing sinyallerini oku
    sig_path = REPO_ROOT / "data" / "swing_entry_signals.json"
    sinyaller = []
    if sig_path.exists():
        sd = json.load(open(sig_path))
        sinyaller = sd.get("detaylar", [])
    
    # Tema adaylar (buy_candidates.json)
    cand_path = REPO_ROOT / "data" / "buy_candidates.json"
    adaylar = []
    if cand_path.exists():
        cd = json.load(open(cand_path))
        adaylar = [a for a in cd.get("adaylar", []) if a.get("portföy") == "aggressive"]
    
    oneriler = []
    
    # 1. Önce swing sinyallerinden tenkan_bounce / ichimoku olanlar (backtest +%8)
    # 28 Nis 2026: Sadece kalite skoru >=55 (ORTA+) sinyalleri kullan
    # ZAYIF (40-55) ve GECERSIZ (<40) sinyalleri gec — K-22'nin amacı
    # sermayeyi kaliteli pozisyonlara kanalize etmek
    iyi_sinyaller = []
    for s in sinyaller:
        sym = s.get("sembol")
        if sym in durum["aktif_semboller"] or sym in cikis_bekleyen:
            continue
        # Yeni alanlar (parse_swing_entry'den geliyor)
        skor = s.get("kalite_skor")
        karar = s.get("kalite_karar")
        # Eski formatla uyumluluk: skor yoksa default geçir (eskiden hep geçiyordu)
        if skor is not None and skor < 55:
            continue  # ZAYIF/GECERSIZ — K-22'ye dahil etme
        iyi_sinyaller.append(s)
    
    bos_slot = durum["bos_slot"]
    pozisyon_basina = kullanilacak / max(bos_slot, 1)
    # K-12 sınırı (tek pozisyon)
    k12_max = (K12_TEK_POZISYON_MAX["aggressive"] / 100) * durum["mevcut_deger"]
    pozisyon_basina = min(pozisyon_basina, k12_max)
    
    # K-12 v2 — sembol → tema haritasi, tema bazli mevcut yüzdeler
    try:
        from k12_dynamic_limits import _tema_haritasi
        tema_map = _tema_haritasi()
    except Exception:
        tema_map = {}
    
    # Mevcut tema yuzdeleri (K-12 v2 durum)
    mevcut_tema_pct = {}
    dinamik_limit_pct = {}
    if k12_durum and k12_durum.get("tema_durum"):
        for t in k12_durum["tema_durum"]:
            mevcut_tema_pct[t["tema"]] = t["mevcut_pct"]
            dinamik_limit_pct[t["tema"]] = t["dinamik_limit_pct"]
    
    for s in iyi_sinyaller[:bos_slot]:
        sym = s.get("sembol")
        fiyat = s.get("fiyat", 0)
        rsi = s.get("rsi", 0)
        skor = s.get("kalite_skor")
        if not fiyat:
            continue
        # Carpan varsa onu kullan (yeni system), yoksa standart hesap
        carpan = s.get("carpan", 1.0) or 1.0
        
        # K-12 v2 CONVICTED BET BONUS (28 Nis 2026):
        # Tema 9+ GUCLU + sektor RS +%5+ ise carpan +0.3 ek (max 2.5x)
        # Memory: 'Druckenmiller convicted bet — when conviction is high, bet big'
        sym_tema = tema_map.get(sym)
        sym_tema_skor = 5
        sym_tema_rs = 0
        if sym_tema:
            from k12_dynamic_limits import _tema_skoru
            ts_data = _tema_skoru(sym_tema)
            sym_tema_skor = ts_data.get("skor", 5)
            sym_tema_rs = ts_data.get("rs_vs_spy", 0)
            if sym_tema_skor >= 9 and sym_tema_rs > 5:
                old_carpan = carpan
                carpan = min(carpan + 0.3, 2.5)
                if carpan > old_carpan:
                    print(f"[K-12 v2] {sym} convicted bet bonus: carpan {old_carpan:.2f}x → {carpan:.2f}x (tema {sym_tema} skor {sym_tema_skor})")
        
        # Carpan'a göre pozisyon büyüt
        ayarlanmis_tutar = pozisyon_basina * carpan
        
        # K-12 v2: tek pozisyon limit yumusamasi (tema 9 + RS +%5)
        # Aggressive: %20 → %25 (tema skor 9'da)
        tek_poz_max_pct = K12_TEK_POZISYON_MAX["aggressive"]
        if sym_tema_skor >= 9 and sym_tema_rs > 5:
            tek_poz_max_pct = 25  # %20 → %25 yumusama
        k12_max_dyn = (tek_poz_max_pct / 100) * durum["mevcut_deger"]
        ayarlanmis_tutar = min(ayarlanmis_tutar, k12_max_dyn)
        
        # K-12 v2: tema toplam limit kontrolü
        sym_tema = tema_map.get(sym)
        if sym_tema and sym_tema in mevcut_tema_pct:
            mevcut = mevcut_tema_pct[sym_tema]
            limit = dinamik_limit_pct.get(sym_tema, 40)
            yeni_pct = (ayarlanmis_tutar / durum["mevcut_deger"]) * 100
            toplam = mevcut + yeni_pct
            if toplam > limit:
                # Limit asilacak — tutarı kıs
                kalan_alan = max(0, limit - mevcut)
                ayarlanmis_tutar = (kalan_alan / 100) * durum["mevcut_deger"]
                if ayarlanmis_tutar < 1000:
                    continue  # Kalan alan az, atla
        
        adet = int(ayarlanmis_tutar / fiyat)
        if adet < 1:
            continue
        skor_str = f" skor:{skor}" if skor else ""
        carpan_str = f" carpan:{carpan:.2f}x" if carpan != 1.0 else ""
        tema_str = f" tema:{sym_tema}" if sym_tema else ""
        oneriler.append({
            "sembol": sym,
            "tip": "AL",
            "kaynak": "swing-sinyal-kaliteli",
            "fiyat": fiyat,
            "adet": adet,
            "tutar": adet * fiyat,
            "stop": s.get("stop"),
            "hedef": s.get("hedef"),
            "rsi": rsi,
            "kalite_skor": skor,
            "carpan": carpan,
            "neden": f"K-22 kaliteli swing sinyal (RSI {rsi}{skor_str}{carpan_str}{tema_str})",
            "oncelik": "yuksek",
        })
    
    # 2. Tema adayları (aggressive için)
    if not oneriler and adaylar:
        for a in adaylar[:bos_slot]:
            sym = a.get("symbol")
            if sym in durum["aktif_semboller"]:
                continue
            fiyat = a.get("price", 0)
            if not fiyat:
                continue
            adet = int(pozisyon_basina / fiyat)
            if adet < 1:
                continue
            oneriler.append({
                "sembol": sym,
                "tip": "AL",
                "kaynak": "tema-tarama",
                "fiyat": fiyat,
                "adet": adet,
                "tutar": adet * fiyat,
                "stop": a.get("stop"),
                "hedef": a.get("target"),
                "neden": f"K-22 nakit kullanim — tema {a.get('tema')} skor {a.get('score')}",
                "oncelik": "orta",
            })
    
    # 3. VIX yüksekse hedge önerisi
    if vix > 22 and not oneriler:
        # Inverse ETF — agresif için 3x serbest
        hedge_tutar = min(kullanilacak * 0.3, k12_max)  # max %30 inverse
        oneriler.append({
            "sembol": "SQQQ",
            "tip": "AL (HEDGE)",
            "kaynak": "vix-hedge",
            "tutar": hedge_tutar,
            "neden": f"K-22 — VIX {vix:.1f}>22, agresife inverse ETF hedge serbest",
            "oncelik": "yuksek",
        })
    
    return {
        "oneriler": oneriler,
        "kullanilacak_nakit": kullanilacak,
        "vix": vix,
    }


def balanced_strateji(durum: dict, vix: float) -> dict:
    """
    Memory: BALANCED — önce defansif rotasyon (XLP/XLV/GLD/TLT),
    inverse ETF max %10 ve SADECE düşük kaldıraçlı.
    """
    kullanilacak = hedef_nakit_kullanim(durum)
    if kullanilacak <= 0:
        return {"oneriler": [], "kullanilacak_nakit": 0}
    
    oneriler = []
    bos_slot = durum["bos_slot"]
    
    # Tema adaylar
    cand_path = REPO_ROOT / "data" / "buy_candidates.json"
    adaylar = []
    if cand_path.exists():
        cd = json.load(open(cand_path))
        adaylar = [a for a in cd.get("adaylar", []) if a.get("portföy") == "balanced"]
    
    pozisyon_basina = kullanilacak / max(bos_slot, 1)
    k12_max = (K12_TEK_POZISYON_MAX["balanced"] / 100) * durum["mevcut_deger"]
    pozisyon_basina = min(pozisyon_basina, k12_max)
    
    # 1. Önce tema adayları (US-only)
    for a in adaylar[:bos_slot]:
        sym = a.get("symbol")
        if sym in durum["aktif_semboller"]:
            continue
        fiyat = a.get("price", 0)
        if not fiyat:
            continue
        adet = int(pozisyon_basina / fiyat)
        if adet < 1:
            continue
        oneriler.append({
            "sembol": sym,
            "tip": "AL",
            "kaynak": "tema-tarama",
            "fiyat": fiyat,
            "adet": adet,
            "tutar": adet * fiyat,
            "stop": a.get("stop"),
            "hedef": a.get("target"),
            "neden": f"K-22 — balanced tema {a.get('tema')} skor {a.get('score')}",
            "oncelik": "yuksek",
        })
    
    # 2. VIX yüksekse defansif rotasyon
    if vix > 22 and len(oneriler) < bos_slot:
        kalan_slot = bos_slot - len(oneriler)
        for etf in DEFANSIF_ETF[:kalan_slot]:
            if etf in durum["aktif_semboller"]:
                continue
            oneriler.append({
                "sembol": etf,
                "tip": "AL (DEFANSIF)",
                "kaynak": "vix-defansif-rotasyon",
                "tutar": pozisyon_basina,
                "neden": f"K-22 — VIX {vix:.1f}>22, balanced defansif rotasyon",
                "oncelik": "orta",
            })

    # 3. VIX normal (<22) ama tema adayı yoksa: geniş piyasa ETF (SPY/VTI/QQQ)
    # Memory: 'Yükseliş bekleniyorsa fırsat sektörlerinden alım'
    if vix <= 22 and not oneriler and bos_slot > 0:
        kalan = bos_slot
        # Mevcut portföyde geniş piyasa ETF var mı kontrol et
        broad_uygun = [e for e in ["SPY", "QQQ", "VTI"] if e not in durum["aktif_semboller"]]
        for etf in broad_uygun[:kalan]:
            oneriler.append({
                "sembol": etf,
                "tip": "AL (GENIS PIYASA)",
                "kaynak": "tema-bos-fallback",
                "tutar": pozisyon_basina,
                "neden": f"K-22 — VIX {vix:.1f} normal, tema aday yok, geniş piyasa ETF beta=1",
                "oncelik": "dusuk",
            })

    # 4. VIX çok yüksekse SH (1x inverse, balanced'a izin)
    if vix > 28 and len(oneriler) < bos_slot:
        max_inverse = durum["mevcut_deger"] * 0.10  # max %10 (memory)
        oneriler.append({
            "sembol": "SH",
            "tip": "AL (HEDGE)",
            "kaynak": "vix-extreme-hedge",
            "tutar": min(kullanilacak * 0.2, max_inverse),
            "neden": f"K-22 — VIX {vix:.1f}>28, balanced 1x inverse ETF max %10",
            "oncelik": "yuksek",
        })
    
    return {
        "oneriler": oneriler,
        "kullanilacak_nakit": kullanilacak,
        "vix": vix,
    }


def dividend_strateji(durum: dict, vix: float) -> dict:
    """
    Memory: DIVIDEND — hedge ve inverse ETF YASAK, 
    sadece defansif temettü hisseleri (KO/PG/JNJ/VZ/KMB/MO/MCD/CL).
    """
    kullanilacak = hedef_nakit_kullanim(durum)
    if kullanilacak <= 0:
        return {"oneriler": [], "kullanilacak_nakit": 0}

    oneriler = []
    bos_slot = durum["bos_slot"]
    
    # Eger slot dolu ise: mevcut en iyi performans gösteren pozisyonu büyüt
    # Memory: 'Cut losers, grow winners'
    if bos_slot == 0 and durum["aktif_semboller"]:
        # ÇIKIŞ bekleyen sembolleri exclude et
        cikis_bekleyen = _bekleyen_cikis_semboller()
        # En iyi performansli pozisyonu bul (kar_zarar_yuzde en yüksek)
        path = REPO_ROOT / "data" / "portfolios" / "dividend.json"
        d = json.load(open(path))
        en_iyi = None
        en_iyi_kz = -999
        for poz in d.get("pozisyonlar", []):
            sym = poz.get("sembol")
            if sym in (None, "_template"):
                continue
            if sym in cikis_bekleyen:
                continue  # Çıkış bekleyen pozisyonu büyütme
            kz = poz.get("kar_zarar_yuzde", 0) or 0
            cf = poz.get("guncel_fiyat", 0) or 0
            adet = poz.get("adet", 0) or 0
            mevcut_tutar = adet * cf
            # K-12 sınırına yakın değilse büyütülebilir
            limit_tutar = (K12_TEK_POZISYON_MAX["dividend"] / 100) * durum["mevcut_deger"]
            if kz > en_iyi_kz and mevcut_tutar < limit_tutar * 0.85:
                en_iyi_kz = kz
                en_iyi = (sym, cf, mevcut_tutar, limit_tutar)
        
        if en_iyi:
            sym, cf, mevcut_tutar, limit_tutar = en_iyi
            buyutme_tutar = min(kullanilacak * 0.5, limit_tutar - mevcut_tutar)
            adet_ek = int(buyutme_tutar / cf) if cf else 0
            if adet_ek > 0:
                oneriler.append({
                    "sembol": sym,
                    "tip": "BUYUT",
                    "kaynak": "best-performer",
                    "fiyat": cf,
                    "adet": adet_ek,
                    "tutar": adet_ek * cf,
                    "neden": f"K-22 — slot dolu, en iyi performansli pozisyon büyütüldü (+{en_iyi_kz:.1f}% K/Z)",
                    "oncelik": "orta",
                })
        return {"oneriler": oneriler, "kullanilacak_nakit": kullanilacak, "vix": vix}
    
    # Tema adaylar (dividend)
    cand_path = REPO_ROOT / "data" / "buy_candidates.json"
    adaylar = []
    if cand_path.exists():
        cd = json.load(open(cand_path))
        adaylar = [a for a in cd.get("adaylar", []) if a.get("portföy") == "dividend"]
    
    pozisyon_basina = kullanilacak / max(bos_slot, 1)
    k12_max = (K12_TEK_POZISYON_MAX["dividend"] / 100) * durum["mevcut_deger"]
    pozisyon_basina = min(pozisyon_basina, k12_max)
    
    # 1. Tema adayları
    for a in adaylar[:bos_slot]:
        sym = a.get("symbol")
        if sym in durum["aktif_semboller"]:
            continue
        fiyat = a.get("price", 0)
        if not fiyat:
            continue
        adet = int(pozisyon_basina / fiyat)
        if adet < 1:
            continue
        oneriler.append({
            "sembol": sym,
            "tip": "AL",
            "kaynak": "tema-tarama",
            "fiyat": fiyat,
            "adet": adet,
            "tutar": adet * fiyat,
            "stop": a.get("stop"),
            "hedef": a.get("target"),
            "neden": f"K-22 — dividend tema {a.get('tema')} skor {a.get('score')}",
            "oncelik": "yuksek",
        })
    
    # 2. Memory uygun listesinden ekle (eksik kalırsa)
    if len(oneriler) < bos_slot:
        kalan = bos_slot - len(oneriler)
        for sym in DIVIDEND_UYGUN:
            if sym in durum["aktif_semboller"]:
                continue
            if any(o["sembol"] == sym for o in oneriler):
                continue
            oneriler.append({
                "sembol": sym,
                "tip": "AL",
                "kaynak": "dividend-uygun-liste",
                "tutar": pozisyon_basina,
                "neden": f"K-22 — defansif temettü hissesi (memory uygun liste)",
                "oncelik": "orta",
            })
            if len([o for o in oneriler if o.get("kaynak") == "dividend-uygun-liste"]) >= kalan:
                break
    
    return {
        "oneriler": oneriler,
        "kullanilacak_nakit": kullanilacak,
        "vix": vix,
    }


def analiz_yap(vix: float = None) -> dict:
    """Tüm portföyler için K-22 analiz"""
    if vix is None:
        vix = get_vix()
    
    sonuc = {
        "tarih": datetime.now(TR).isoformat(),
        "vix": vix,
        "portfoyler": {},
    }
    
    strateji_fn = {
        "aggressive": aggressive_strateji,
        "balanced": balanced_strateji,
        "dividend": dividend_strateji,
    }
    
    for pf in ["balanced", "aggressive", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if not path.exists():
            continue
        d = json.load(open(path))
        durum = portfoy_durumu(d)
        strateji = strateji_fn[pf](durum, vix)
        sonuc["portfoyler"][pf] = {
            "durum": durum,
            "strateji": strateji,
            "aksiyon_gerek": durum["nakit_pct"] > NAKIT_LIMIT_PCT,
        }
    
    return sonuc


def yazdir(s: dict):
    print("=" * 70)
    print(f"K-22 NAKIT KULLANIM — VIX {s['vix']:.1f}")
    print("=" * 70)
    for pf, data in s["portfoyler"].items():
        d = data["durum"]
        st = data["strateji"]
        print(f"\n>>> {pf.upper()}")
        print(f"  Mevcut: ${d['mevcut_deger']:,.0f} | Nakit: ${d['nakit']:,.0f} (%{d['nakit_pct']:.1f})")
        print(f"  Aktif: {len(d['aktif_semboller'])}/{d['max_pozisyon']} | Bos slot: {d['bos_slot']}")
        if not data["aksiyon_gerek"]:
            print(f"  ✅ Nakit oranı kuralı altında, aksiyon yok")
            continue
        print(f"  🔴 Kullanilacak nakit: ${st['kullanilacak_nakit']:,.0f}")
        if st["oneriler"]:
            print(f"  Oneriler ({len(st['oneriler'])}):")
            for o in st["oneriler"]:
                print(f"    - {o['tip']:14} {o['sembol']:6} | ${o.get('tutar', 0):>9,.0f} | {o.get('neden','')[:60]}")
        else:
            print(f"  ⚠️ Aday bulunamadi (boş swing/tema)")


def session_state_kaydet(s: dict):
    """K-22 önerilerini session_state'e ekle"""
    ss_path = REPO_ROOT / "data" / "session_state.json"
    ss = json.load(open(ss_path)) if ss_path.exists() else {}
    
    # Mevcut k22 anahtarını güncelle
    ss["k22_nakit_dagitim"] = {
        "tarih": s["tarih"],
        "vix": s["vix"],
        "portfoyler": {pf: {
            "nakit_pct": d["durum"]["nakit_pct"],
            "kullanilacak_usd": d["strateji"]["kullanilacak_nakit"],
            "oneriler": d["strateji"]["oneriler"],
        } for pf, d in s["portfoyler"].items()},
    }
    
    with open(ss_path, "w") as f:
        json.dump(ss, f, ensure_ascii=False, indent=2)
    print(f"\nsession_state.k22_nakit_dagitim güncellendi")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="session_state'e kaydet")
    parser.add_argument("--vix", type=float, help="Manuel VIX")
    args = parser.parse_args()
    
    s = analiz_yap(args.vix)
    yazdir(s)
    
    if args.apply:
        session_state_kaydet(s)


if __name__ == "__main__":
    main()
