#!/usr/bin/env python3
"""
Finzora AI — Günlük Çoklu Portföy Tarama Scripti v2.0
-------------------------------------------------------
Çalışma: Her iş günü piyasa kapanışı sonrası (21:30 UTC / 00:30 TR)
Çıktı  : data/daily_scan.json (4 portföy bölümü)

Portföyler:
  1. agresif   — momentum + hacim + earnings beat
  2. dengeli   — value + sektör gücü + RSI kurtarma
  3. temettü   — düşük P/E + yüksek yield + güçlü FCF
  4. swing     — ichimoku sinyalleri (kumo kırılımı, TK cross, kijun bounce)
"""

import requests
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

# ─── Yapılandırma ────────────────────────────────────────────────────────────
FMP_API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_BASE    = "https://financialmodelingprep.com/stable"

MIN_FIYAT        = 10
MIN_HACIM        = 300_000
MAX_ADAY         = 10

VIX_UYARI_ESIGI  = 25
VIX_KRITIK_ESIGI = 30

AGR_MIN_MCAP     = 3e9
AGR_MIN_HACIM    = 1_000_000
AGR_MIN_5D_CHG   = 3.0

DNG_MIN_MCAP     = 5e9

TMT_MIN_MCAP     = 5e9
TMT_MAX_PE       = 20
TMT_MIN_YIELD    = 3.0

SWG_MIN_MCAP     = 2e9
SWG_MIN_HACIM    = 500_000


def mevcut_pozisyonlari_al():
    semboller = set()
    dosyalar = [
        "data/portfolios/aggressive.json",
        "data/portfolios/balanced.json",
        "data/portfolios/dividend.json",
        "data/swing/active.json",
    ]
    for dosya in dosyalar:
        yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), dosya)
        if os.path.exists(yol):
            try:
                with open(yol) as f:
                    d = json.load(f)
                if "pozisyonlar" in d:
                    for p in d["pozisyonlar"]:
                        semboller.add(p.get("sembol", ""))
                if "aktif_pozisyonlar" in d:
                    for p in d["aktif_pozisyonlar"]:
                        semboller.add(p.get("sembol", ""))
            except:
                pass
    semboller.discard("")
    return semboller


# ─── FMP Yardımcılar ────────────────────────────────────────────────────────
def fmp_get(endpoint, params=None):
    if params is None:
        params = {}
    params["apikey"] = FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "Error Message" in data:
            print(f"  ⚠ FMP hata [{endpoint}]: {data['Error Message']}")
            return None
        return data
    except Exception as e:
        print(f"  ✗ İstek hatası [{endpoint}]: {e}")
        return None


def sf(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except:
        return default


# ─── Piyasa Bağlamı ─────────────────────────────────────────────────────────
def piyasa_baglamini_al():
    print("→ Piyasa bağlamı alınıyor...")
    endeks_quotes = fmp_get("batch-quote", {"symbols": "SPY,QQQ,IWM,DIA"})
    vix_quote     = fmp_get("quote", {"symbol": "^VIX"})

    endeks = {}
    if endeks_quotes:
        for q in endeks_quotes:
            endeks[q.get("symbol", "")] = {
                "fiyat": sf(q.get("price")),
                "degisim": sf(q.get("changesPercentage")),
            }

    vix = 0.0
    if vix_quote:
        v = vix_quote[0] if isinstance(vix_quote, list) else vix_quote
        vix = sf(v.get("price"))

    dun = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    sektor_perf = fmp_get("sector-performance-snapshot", {"date": dun})
    if not sektor_perf:
        sektor_perf = fmp_get("sector-performance-snapshot",
                              {"date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")})

    sektorler = {}
    if sektor_perf:
        for s in sektor_perf:
            sektorler[s["sector"]] = sf(s.get("averageChange"))

    vix_mesaj = ""
    if vix >= VIX_KRITIK_ESIGI:
        vix_mesaj = f"🔴 VIX {vix:.1f} — KRİTİK. Yeni giriş tehlikeli, yarım pozisyon bile dikkatli."
    elif vix >= VIX_UYARI_ESIGI:
        vix_mesaj = f"⚠ VIX {vix:.1f} — YÜKSEK OYNAKLIK. Stop seviyeleri geniş tut, yarım pozisyon düşün."

    return {
        "tarih": datetime.now().strftime("%Y-%m-%d"),
        "spy_fiyat": endeks.get("SPY", {}).get("fiyat", 0),
        "spy_degisim": endeks.get("SPY", {}).get("degisim", 0),
        "qqq_degisim": endeks.get("QQQ", {}).get("degisim", 0),
        "iwm_degisim": endeks.get("IWM", {}).get("degisim", 0),
        "vix": vix,
        "vix_uyarisi": vix >= VIX_UYARI_ESIGI,
        "vix_kritik": vix >= VIX_KRITIK_ESIGI,
        "vix_mesaj": vix_mesaj,
        "sektorler": sektorler,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  1. AGRESİF TARAMA
# ═══════════════════════════════════════════════════════════════════════════
def agresif_tara(haric):
    print("\n→ Agresif tarama başlıyor...")
    goruldu = set()

    # biggest-gainers
    gainers = fmp_get("biggest-gainers", {"limit": 50})
    if gainers:
        for g in gainers:
            sym = g.get("symbol", "")
            mc = sf(g.get("marketCap"))
            price = sf(g.get("price"))
            vol = sf(g.get("volume"))
            if (sym not in haric and mc >= AGR_MIN_MCAP
                    and price >= MIN_FIYAT and vol >= AGR_MIN_HACIM):
                goruldu.add(sym)

    # screener (çoklu sektör)
    for sector in ["Technology", "Industrials", "Energy", "Healthcare"]:
        scr = fmp_get("company-screener", {
            "marketCapMoreThan": int(AGR_MIN_MCAP),
            "sector": sector,
            "exchange": "NYSE,NASDAQ",
            "isActivelyTrading": "true",
            "volumeMoreThan": AGR_MIN_HACIM,
            "priceMoreThan": MIN_FIYAT,
            "limit": 20,
        })
        if scr:
            for s in scr:
                if s["symbol"] not in haric:
                    goruldu.add(s["symbol"])

    # momentum filtresi
    print(f"  → {len(goruldu)} aday için momentum kontrolü...")
    sonuc = []
    for sym in list(goruldu)[:60]:
        d = fmp_get("stock-price-change", {"symbol": sym})
        if not d or len(d) == 0:
            continue
        c = d[0]
        d1 = sf(c.get("1D"))
        d5 = sf(c.get("5D"))
        d1m = sf(c.get("1M"))
        if d5 >= AGR_MIN_5D_CHG and d1 >= 0:
            profil = fmp_get("profile", {"symbol": sym})
            isim, sektor = sym, ""
            if profil and len(profil) > 0:
                isim = profil[0].get("companyName", sym)
                sektor = profil[0].get("sector", "")
            sonuc.append({
                "sembol": sym, "isim": isim, "sektor": sektor,
                "degisim_1d": round(d1, 2), "degisim_5d": round(d5, 2),
                "degisim_1m": round(d1m, 2),
                "neden": f"5 günlük momentum +%{d5:.1f}, dün +%{d1:.1f}",
            })

    sonuc.sort(key=lambda x: x["degisim_5d"], reverse=True)
    print(f"  ✓ Agresif: {len(sonuc[:MAX_ADAY])} aday")
    return sonuc[:MAX_ADAY]


# ═══════════════════════════════════════════════════════════════════════════
#  2. DENGELİ TARAMA
# ═══════════════════════════════════════════════════════════════════════════
def dengeli_tara(haric, guclu_sektorler):
    print("\n→ Dengeli tarama başlıyor...")
    goruldu = set()

    for sector in guclu_sektorler[:4]:
        scr = fmp_get("company-screener", {
            "marketCapMoreThan": int(DNG_MIN_MCAP),
            "sector": sector,
            "exchange": "NYSE,NASDAQ",
            "isActivelyTrading": "true",
            "volumeMoreThan": MIN_HACIM,
            "priceMoreThan": MIN_FIYAT,
            "limit": 20,
        })
        if scr:
            for s in scr:
                if s["symbol"] not in haric:
                    goruldu.add(s["symbol"])

    print(f"  → {len(goruldu)} aday için RSI kontrolü...")
    sonuc = []
    for sym in list(goruldu)[:40]:
        rsi_data = fmp_get("technical-indicators/rsi",
                           {"symbol": sym, "periodLength": 14, "timeframe": "1day"})
        if not rsi_data or len(rsi_data) < 2:
            continue
        rsi_now = sf(rsi_data[0].get("rsi"))
        rsi_prev = sf(rsi_data[1].get("rsi"))

        if 30 <= rsi_now <= 55 and rsi_now > rsi_prev:
            chg = fmp_get("stock-price-change", {"symbol": sym})
            d1 = sf(chg[0].get("1D")) if chg and len(chg) > 0 else 0
            d5 = sf(chg[0].get("5D")) if chg and len(chg) > 0 else 0
            d1m = sf(chg[0].get("1M")) if chg and len(chg) > 0 else 0

            profil = fmp_get("profile", {"symbol": sym})
            isim, sektor = sym, ""
            if profil and len(profil) > 0:
                isim = profil[0].get("companyName", sym)
                sektor = profil[0].get("sector", "")

            sonuc.append({
                "sembol": sym, "isim": isim, "sektor": sektor,
                "rsi": round(rsi_now, 1), "rsi_onceki": round(rsi_prev, 1),
                "degisim_1d": round(d1, 2), "degisim_5d": round(d5, 2),
                "degisim_1m": round(d1m, 2),
                "neden": f"RSI {rsi_now:.0f} kurtarma (önceki {rsi_prev:.0f}), güçlü sektör",
            })

    sonuc.sort(key=lambda x: x["rsi"])
    print(f"  ✓ Dengeli: {len(sonuc[:MAX_ADAY])} aday")
    return sonuc[:MAX_ADAY]


# ═══════════════════════════════════════════════════════════════════════════
#  3. TEMETTÜ TARAMA
# ═══════════════════════════════════════════════════════════════════════════
def temettu_tara(haric):
    print("\n→ Temettü tarama başlıyor...")

    scr = fmp_get("company-screener", {
        "marketCapMoreThan": int(TMT_MIN_MCAP),
        "dividendMoreThan": TMT_MIN_YIELD,
        "exchange": "NYSE,NASDAQ",
        "isActivelyTrading": "true",
        "priceMoreThan": MIN_FIYAT,
        "limit": 50,
    })

    semboller = []
    if scr:
        for s in scr:
            if s["symbol"] not in haric:
                semboller.append(s["symbol"])

    print(f"  → {len(semboller)} aday için temel analiz...")
    sonuc = []
    for sym in semboller[:30]:
        ratios = fmp_get("ratios-ttm", {"symbol": sym})
        if not ratios or len(ratios) == 0:
            continue
        r = ratios[0]
        pe = sf(r.get("peRatioTTM"))
        div_yield = sf(r.get("dividendYielTTM")) * 100
        payout = sf(r.get("payoutRatioTTM"))

        if pe <= 0 or pe > TMT_MAX_PE or div_yield < TMT_MIN_YIELD or payout > 1.0:
            continue

        km = fmp_get("key-metrics-ttm", {"symbol": sym})
        fcf_yield = 0
        if km and len(km) > 0:
            fcf_yield = sf(km[0].get("freeCashFlowYieldTTM")) * 100

        profil = fmp_get("profile", {"symbol": sym})
        isim, sektor, fiyat = sym, "", 0
        if profil and len(profil) > 0:
            isim = profil[0].get("companyName", sym)
            sektor = profil[0].get("sector", "")
            fiyat = sf(profil[0].get("price"))

        sonuc.append({
            "sembol": sym, "isim": isim, "sektor": sektor, "fiyat": fiyat,
            "pe": round(pe, 1), "temettu_yuzde": round(div_yield, 2),
            "payout_orani": round(payout * 100, 1),
            "fcf_yield_yuzde": round(fcf_yield, 2),
            "neden": f"P/E {pe:.1f}, temettü %{div_yield:.1f}, FCF yield %{fcf_yield:.1f}",
        })

    sonuc.sort(key=lambda x: x["temettu_yuzde"], reverse=True)
    print(f"  ✓ Temettü: {len(sonuc[:MAX_ADAY])} aday")
    return sonuc[:MAX_ADAY]


# ═══════════════════════════════════════════════════════════════════════════
#  4. SWING TARAMA (ichimoku)
# ═══════════════════════════════════════════════════════════════════════════
def ichimoku_hesapla(fiyatlar):
    if len(fiyatlar) < 52:
        return None

    def orta(veri, n):
        dilim = veri[:n]
        h = [sf(d.get("high")) for d in dilim]
        l = [sf(d.get("low")) for d in dilim]
        return (max(h) + min(l)) / 2

    tenkan = orta(fiyatlar, 9)
    kijun  = orta(fiyatlar, 26)
    senkou_a = (tenkan + kijun) / 2
    senkou_b = orta(fiyatlar, 52)
    kumo_ust = max(senkou_a, senkou_b)
    kumo_alt = min(senkou_a, senkou_b)

    fiyat = sf(fiyatlar[0].get("close"))
    fiyat_26 = sf(fiyatlar[25].get("close")) if len(fiyatlar) > 25 else fiyat
    fiyat_dun = sf(fiyatlar[1].get("close")) if len(fiyatlar) > 1 else fiyat
    tenkan_dun = orta(fiyatlar[1:], 9) if len(fiyatlar) > 10 else tenkan
    kijun_dun = orta(fiyatlar[1:], 26) if len(fiyatlar) > 27 else kijun

    return {
        "fiyat": fiyat, "tenkan": round(tenkan, 2), "kijun": round(kijun, 2),
        "kumo_ust": round(kumo_ust, 2), "kumo_alt": round(kumo_alt, 2),
        "kumo_renk": "yesil" if senkou_a > senkou_b else "kirmizi",
        "chikou_pozitif": fiyat > fiyat_26,
        "tenkan_gt_kijun": tenkan > kijun,
        "fiyat_dun": fiyat_dun, "tenkan_dun": round(tenkan_dun, 2),
        "kijun_dun": round(kijun_dun, 2),
    }


def swing_tara(haric, baglam):
    print("\n→ Swing ichimoku tarama başlıyor...")
    goruldu = set()

    gainers = fmp_get("biggest-gainers", {"limit": 40})
    if gainers:
        for g in gainers:
            sym = g.get("symbol", "")
            mc = sf(g.get("marketCap"))
            price = sf(g.get("price"))
            vol = sf(g.get("volume"))
            if sym not in haric and mc >= SWG_MIN_MCAP and price >= MIN_FIYAT and vol >= SWG_MIN_HACIM:
                goruldu.add(sym)

    for sector in ["Technology", "Energy", "Industrials", "Healthcare", "Basic Materials"]:
        scr = fmp_get("company-screener", {
            "marketCapMoreThan": int(SWG_MIN_MCAP), "sector": sector,
            "exchange": "NYSE,NASDAQ", "isActivelyTrading": "true",
            "volumeMoreThan": SWG_MIN_HACIM, "priceMoreThan": MIN_FIYAT, "limit": 15,
        })
        if scr:
            for s in scr:
                if s["symbol"] not in haric:
                    goruldu.add(s["symbol"])

    # 5D pozitif filtre
    momentum = []
    for sym in list(goruldu)[:50]:
        d = fmp_get("stock-price-change", {"symbol": sym})
        if d and len(d) > 0:
            d5 = sf(d[0].get("5D"))
            d1 = sf(d[0].get("1D"))
            if d5 > 0 and d1 >= 0:
                momentum.append(sym)

    print(f"  → {len(momentum)} aday için ichimoku kontrol...")
    sonuc = []
    for sym in momentum[:30]:
        fiyatlar = fmp_get("historical-price-eod/full", {"symbol": sym, "limit": 60})
        if not fiyatlar or len(fiyatlar) < 52:
            continue

        ich = ichimoku_hesapla(fiyatlar)
        if not ich:
            continue

        fiyat = ich["fiyat"]
        # konum
        if fiyat > ich["kumo_ust"]:
            konum = "kumo_ustu"
        elif fiyat > ich["kumo_alt"]:
            konum = "kumo_ici"
        else:
            konum = "kumo_alti"

        # sinyaller
        sinyaller = []
        if fiyat > ich["kumo_ust"] and ich["fiyat_dun"] <= ich["kumo_ust"]:
            sinyaller.append("kumo_kirilimi")
        if ich["tenkan_gt_kijun"] and ich["tenkan_dun"] <= ich["kijun_dun"]:
            sinyaller.append("tk_cross")
        kijun = ich["kijun"]
        if kijun > 0 and abs(fiyat - kijun) / kijun < 0.02 and fiyat > ich["fiyat_dun"]:
            sinyaller.append("kijun_bounce")

        guc = sum([
            konum == "kumo_ustu",
            ich["tenkan_gt_kijun"],
            ich["chikou_pozitif"],
            ich["kumo_renk"] == "yesil",
        ])

        # hacim
        hacimler = [sf(d.get("volume")) for d in fiyatlar[:20]]
        ort_hacim = sum(hacimler) / len(hacimler) if hacimler else 1
        hacim_kat = hacimler[0] / ort_hacim if ort_hacim > 0 else 0

        if len(sinyaller) > 0 or guc >= 3:
            karar = "BEKLE"
            if sinyaller and guc >= 3 and hacim_kat >= 1.0:
                karar = "GİRİŞ ✅"
            elif sinyaller and guc >= 2:
                karar = "GİRİŞ ⚠️"
            elif guc >= 3:
                karar = "TREND DEVAM"

            profil = fmp_get("profile", {"symbol": sym})
            isim, sektor = sym, ""
            if profil and len(profil) > 0:
                isim = profil[0].get("companyName", sym)
                sektor = profil[0].get("sector", "")

            sonuc.append({
                "sembol": sym, "isim": isim, "sektor": sektor,
                "fiyat": fiyat,
                "ichimoku": {
                    "konum": konum, "guc": guc, "sinyaller": sinyaller,
                    "tenkan": ich["tenkan"], "kijun": ich["kijun"],
                    "kumo_ust": ich["kumo_ust"], "kumo_alt": ich["kumo_alt"],
                    "kumo_renk": ich["kumo_renk"],
                },
                "hacim_katsayisi": round(hacim_kat, 1),
                "stop_kijun": ich["kijun"],
                "karar": karar,
                "neden": f"ichimoku {guc}/4, {', '.join(sinyaller) or 'trend devam'}",
            })

    sonuc.sort(key=lambda x: (
        0 if "GİRİŞ ✅" in x["karar"] else 1 if "GİRİŞ ⚠️" in x["karar"] else 2,
        -x["ichimoku"]["guc"]
    ))
    print(f"  ✓ Swing: {len(sonuc[:MAX_ADAY])} aday")
    return sonuc[:MAX_ADAY]


# ─── Kaydet + Git ────────────────────────────────────────────────────────
def sonuclari_kaydet(baglam, agresif, dengeli, temettu, swing):
    dosya = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "daily_scan.json")
    veri = {
        "tarama_tarihi": baglam["tarih"],
        "tarama_zamani": datetime.now(timezone.utc).isoformat(),
        "versiyon": "2.0",
        "piyasa_ozeti": baglam,
        "agresif_adaylari": agresif,
        "dengeli_adaylari": dengeli,
        "temettu_adaylari": temettu,
        "swing_adaylari": swing,
        "ozet": {
            "agresif_sayi": len(agresif),
            "dengeli_sayi": len(dengeli),
            "temettu_sayi": len(temettu),
            "swing_sayi": len(swing),
            "toplam": len(agresif) + len(dengeli) + len(temettu) + len(swing),
        }
    }
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Sonuçlar kaydedildi: {dosya}")


def git_commit_push(tarih_str):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "Finzora AI",
           "GIT_AUTHOR_EMAIL": "zeynelgun@users.noreply.github.com",
           "GIT_COMMITTER_NAME": "Finzora AI",
           "GIT_COMMITTER_EMAIL": "zeynelgun@users.noreply.github.com"}
    try:
        subprocess.run(["git", "add", "data/daily_scan.json"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"[TARAMA] {tarih_str} - günlük çoklu portföy taraması"],
                       cwd=repo, check=True, capture_output=True, env=env)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo, check=True, capture_output=True)
        print("✓ Git commit + push tamamlandı")
    except subprocess.CalledProcessError as e:
        print(f"✗ Git hatası: {e}")


def main():
    print("=" * 60)
    print("  FİNZORA AI — GÜNLÜK ÇOKLU PORTFÖY TARAMASI v2.0")
    print("=" * 60)

    haric = mevcut_pozisyonlari_al()
    print(f"  Mevcut pozisyonlar ({len(haric)}): {', '.join(sorted(haric))}")

    baglam = piyasa_baglamini_al()
    sektorler = baglam.get("sektorler", {})
    guclu = sorted(sektorler.keys(), key=lambda x: sektorler[x], reverse=True)

    agresif = agresif_tara(haric)
    dengeli = dengeli_tara(haric, guclu)
    temettu = temettu_tara(haric)
    swing   = swing_tara(haric, baglam)

    sonuclari_kaydet(baglam, agresif, dengeli, temettu, swing)
    git_commit_push(datetime.now().strftime("%d %B %Y"))

    print("\n" + "=" * 60)
    print("  TARAMA TAMAMLANDI")
    print(f"  Toplam: {len(agresif)} agresif + {len(dengeli)} dengeli + "
          f"{len(temettu)} temettü + {len(swing)} swing")
    print("=" * 60)


if __name__ == "__main__":
    main()
