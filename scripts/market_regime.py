#!/usr/bin/env python3
"""
Finzora AI — Piyasa Rejimi Tespit Sistemi (Katman 4)
=====================================================
Her sabah çalışır. SPY, VIX ve sektör verilerinden
piyasa rejimini belirler. Tüm pozisyon ve tarama
kararlarına rejim bağlamı sağlar.

Rejimler:
  TREND_BULL   → SPY>21EMA + VIX<18  | Full size, momentum ön
  VOLATILE_BULL→ SPY>21EMA + VIX18-25| Normal size, dikkatli
  KRİZ_RALLİ  → VIX düşüyor + rotasyon| Beneficiary sektörler
  CHOP         → SPY ±1% bant içinde  | Boyutu küçült, bekle
  BEAR         → SPY<21EMA            | Yarı size, defansif
  KRİZ         → VIX>28              | K-14 benzeri önlem

Kullanım:
  python3 scripts/market_regime.py              # Anlık rejim
  python3 scripts/market_regime.py --full       # Detaylı rapor
  python3 scripts/market_regime.py --json       # JSON çıktı
  python3 scripts/market_regime.py --history    # Son 30 gün trend
"""

import json
import sys
import os
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque

BASE       = Path(__file__).parent.parent
REGIME_FILE = BASE / "data" / "market_regime.json"
FMP_KEY    = os.environ.get("FMP_API_KEY", "")
FMP_BASE   = "https://financialmodelingprep.com/stable"


# ══════════════════════════════════════════════════════════════════════════════
# 1. FMP VERİ ÇEKME
# ══════════════════════════════════════════════════════════════════════════════

def fmp_get(endpoint: str, params: dict = {}) -> dict | list | None:
    params["apikey"] = FMP_KEY
    qs  = urllib.parse.urlencode(params)
    url = f"{FMP_BASE}/{endpoint}?{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FinzoraAI/4.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠️  FMP hata [{endpoint}]: {e}")
        return None


def spy_fiyat_ve_ema() -> dict:
    """SPY fiyatı, 21EMA, 50SMA hesaplar."""
    # Son 60 günlük kapanış
    data = fmp_get("historical-price-eod/full", {"symbol": "SPY", "limit": 60})
    if not data:
        return {}

    fiyatlar = [d["close"] for d in data]  # En yeni önde
    guncel   = fiyatlar[0]
    onceki   = fiyatlar[1] if len(fiyatlar) > 1 else guncel

    # 21 EMA (hesaplama)
    k = 2 / (21 + 1)
    ema21 = fiyatlar[-1]
    for p in reversed(fiyatlar[:-1]):
        ema21 = p * k + ema21 * (1 - k)

    # 50 SMA
    sma50 = sum(fiyatlar[:50]) / 50 if len(fiyatlar) >= 50 else sum(fiyatlar) / len(fiyatlar)

    # 5 günlük trend eğimi
    egim5 = (fiyatlar[0] - fiyatlar[4]) / fiyatlar[4] * 100 if len(fiyatlar) >= 5 else 0

    return {
        "guncel": guncel,
        "onceki": onceki,
        "gun_degisim": (guncel - onceki) / onceki * 100,
        "ema21": round(ema21, 2),
        "sma50": round(sma50, 2),
        "ema21_uzeri": guncel > ema21,
        "sma50_uzeri": guncel > sma50,
        "egim5g": round(egim5, 2),
    }


def vix_oku() -> float:
    """
    VIX değerini okur.
    VIXY/UVXY güvenilmez (memory not: VIXY 29.71 → gerçek VIX 21.04).
    FMP ^VIX 402 dönüyor.
    En güvenilir yol: web_search "VIX today" — bu script dışında yapılır.
    Yedek: son kaydedilen rejim dosyasından oku.
    """
    # Son rejim dosyasından önceki VIX'i al (insan doğrulamalı)
    if REGIME_FILE.exists():
        try:
            with open(REGIME_FILE) as f:
                prev = json.load(f)
            prev_vix = prev.get("guncel_rejim", {}).get("vix_deger", 0)
            if 10 < prev_vix < 80:  # Makul aralık
                print(f"  ℹ️  VIX: önceki kayıttan {prev_vix} kullanılıyor")
                print(f"       (Güncel VIX için: web_search 'VIX today')")
                return prev_vix
        except Exception:
            pass

    # İlk çalıştırma — varsayılan olarak belirsiz döndür
    print("  ⚠️  VIX verisi yok — web_search ile manuel gir veya --vix parametresi kullan")
    return 0.0


def sektor_performans() -> dict:
    """9 ana sektör ETF'inin son 5 günlük performansını ölçer."""
    SEKTORLER = {
        "XLK": "Teknoloji",    "XLF": "Finans",
        "XLV": "Sağlık",       "XLE": "Enerji",
        "XLI": "Sanayi",       "XLY": "Tüketici-D",
        "XLP": "Tüketici-S",   "XLU": "Kamu",
        "GLD": "Altın",        "IWM": "Küçük Cap",
    }
    semboller = ",".join(SEKTORLER.keys())
    data = fmp_get("batch-quote", {"symbols": semboller})
    if not data:
        return {}

    sonuc = {}
    for item in data:
        sym  = item.get("symbol", "")
        isim = SEKTORLER.get(sym, sym)
        pct  = item.get("changesPercentage", 0)
        fiy  = item.get("price", 0)
        prev = item.get("previousClose", fiy)
        # changesPercentage piyasa dışında 0 döner, manuel hesapla
        if prev and prev > 0:
            pct = (fiy - prev) / prev * 100
        sonuc[sym] = {"isim": isim, "gunluk": round(pct, 2), "fiyat": fiy}

    return sonuc


# ══════════════════════════════════════════════════════════════════════════════
# 2. REJİM SINIFLANDIRMASI
# ══════════════════════════════════════════════════════════════════════════════

def rejim_siniflandir(spy: dict, vix: float, sektorler: dict) -> dict:
    """
    Tüm göstergeleri birleştirip rejim üretir.

    Döndürür:
        {
          "rejim": str,
          "alt_rejim": str,
          "guven": int(1-100),
          "pozisyon_carpani": float,
          "tarama_modu": str,
          "uyarilar": list[str],
          "aciklama": str,
        }
    """
    uyarilar   = []
    sinyaller  = []

    ema21_uzeri = spy.get("ema21_uzeri", False)
    sma50_uzeri = spy.get("sma50_uzeri", False)
    egim5       = spy.get("egim5g", 0)
    gun_deg     = spy.get("gun_degisim", 0)

    # ── VIX bandı ──────────────────────────────────────────────
    if vix == 0:
        vix_band = "BİLİNMİYOR"
        uyarilar.append("VIX verisi alınamadı — web search ile kontrol et")
    elif vix < 18:
        vix_band = "DÜŞÜK"
    elif vix < 22:
        vix_band = "NORMAL"
    elif vix < 28:
        vix_band = "YÜKSEK"
    elif vix < 35:
        vix_band = "KRİZ"
    else:
        vix_band = "PANIK"

    # ── Sektör rotasyon analizi ─────────────────────────────────
    if sektorler:
        # Risk-on sinyali: XLK, XLY, IWM güçlü
        risk_on_etf = ["XLK", "XLY", "IWM"]
        risk_off_etf = ["XLP", "XLU", "GLD"]

        risk_on_avg  = sum(sektorler.get(s, {}).get("gunluk", 0) for s in risk_on_etf) / 3
        risk_off_avg = sum(sektorler.get(s, {}).get("gunluk", 0) for s in risk_off_etf) / 3

        rotasyon = "RISK_ON" if risk_on_avg > risk_off_avg else "RISK_OFF"
        rot_fark = risk_on_avg - risk_off_avg
    else:
        rotasyon = "BİLİNMİYOR"
        rot_fark = 0

    # ── Ana rejim belirleme ─────────────────────────────────────
    if vix_band in ("KRİZ", "PANIK"):
        rejim     = "KRİZ"
        alt_rejim = "VIX>28 — K-14 tipi önlem"
        carpan    = 0.0   # Yeni swing girişi yok
        tarama    = "KAPAL"
        guven     = 90
        uyarilar.append(f"VIX {vix:.1f} — yeni swing girişi engellendi (K-13)")
        if not ema21_uzeri:
            uyarilar.append("SPY 21EMA altı — çifte kırmızı bayrak")

    elif not ema21_uzeri:
        rejim     = "BEAR"
        alt_rejim = "SPY 21EMA altı"
        carpan    = 0.5
        tarama    = "DEFANS"
        guven     = 80
        uyarilar.append("SPY 21EMA altında — yarı pozisyon büyüklüğü")
        if not sma50_uzeri:
            uyarilar.append("SPY 50SMA da altında — iyimserlik için iki teyit gerekli")

    elif ema21_uzeri and vix_band == "DÜŞÜK" and rotasyon == "RISK_ON":
        rejim     = "TREND_BULL"
        alt_rejim = "Güçlü yükseliş trendi"
        carpan    = 1.0
        tarama    = "MOMENTUM"
        guven     = 85

    elif ema21_uzeri and vix_band in ("NORMAL", "DÜŞÜK") and rotasyon == "RISK_OFF":
        rejim     = "VOLATILE_BULL"
        alt_rejim = "Yükseliş ama rotasyon karışık"
        carpan    = 0.75
        tarama    = "SEÇİCİ"
        guven     = 65
        uyarilar.append("Risk-off rotasyon — sektor seçimine dikkat")

    elif ema21_uzeri and vix_band == "YÜKSEK":
        rejim     = "VOLATILE_BULL"
        alt_rejim = f"VIX {vix:.0f} — K-13 yarı pozisyon"
        carpan    = 0.5
        tarama    = "SEÇİCİ"
        guven     = 70
        uyarilar.append(f"VIX {vix:.0f} — duyarlı sektörlerde yarı pozisyon (K-13)")

    elif abs(egim5) < 1.0 and abs(gun_deg) < 0.3:
        rejim     = "CHOP"
        alt_rejim = "Yatay konsolidasyon"
        carpan    = 0.5
        tarama    = "BEKLE"
        guven     = 60
        uyarilar.append("Bant içi hareket — momentum sinyali bekleniyor")

    else:
        rejim     = "VOLATILE_BULL"
        alt_rejim = "Karma sinyal"
        carpan    = 0.75
        tarama    = "SEÇİCİ"
        guven     = 55

    # ── Kriz rallisi tespiti (VIX düşerken SPY yukarı) ─────────
    if rejim in ("VOLATILE_BULL", "TREND_BULL") and vix_band == "YÜKSEK" and egim5 > 1.5:
        alt_rejim = "Kriz rallisi — beneficiary sektörler ön planda"
        uyarilar.append("Kriz rally sinyali — enerji/savunma/altın pozisyon büyütülebilir")

    return {
        "rejim":            rejim,
        "alt_rejim":        alt_rejim,
        "guven":            guven,
        "pozisyon_carpani": carpan,
        "tarama_modu":      tarama,
        "vix_band":         vix_band,
        "vix_deger":        vix,
        "spy_ema21_uzeri":  ema21_uzeri,
        "spy_sma50_uzeri":  sma50_uzeri,
        "rotasyon":         rotasyon,
        "rotasyon_farki":   round(rot_fark, 2),
        "uyarilar":         uyarilar,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. REJİM BAZLI AKSİYONLAR
# ══════════════════════════════════════════════════════════════════════════════

REJIM_AKSIYONLARI = {
    "TREND_BULL": {
        "swing":      "Tam büyüklük. Momentum hisseler öncelikli.",
        "portfoy":    "Agresif portföy tam gas. Dengeli büyüt.",
        "stop":       "Normal chandelier. K-07 standart.",
        "sektör":     "Teknoloji, Sanayi, Finans lider.",
        "emoji":      "🟢",
    },
    "VOLATILE_BULL": {
        "swing":      "Pozisyonu %75'e indir. Daha seçici ol.",
        "portfoy":    "Mevcut pozisyonları koru, yeni girişlerde dikkat.",
        "stop":       "Stopları sıkıştır. K-ATR kontrolü.",
        "sektör":     "Defansif + momentum karışık. Sektör ETF >9EMA şart.",
        "emoji":      "🟡",
    },
    "KRİZ_RALLİ": {
        "swing":      "Beneficiary sektörler tam, duyarlılar yarı.",
        "portfoy":    "Enerji/savunma/altın büyüt. Tech küçült.",
        "stop":       "Chandelier 3×ATR (K-13b).",
        "sektör":     "Enerji, Savunma, Altın — K-13 matrisi.",
        "emoji":      "🟠",
    },
    "CHOP": {
        "swing":      "Pozisyonu %50'ye indir. Momentum sinyali bekle.",
        "portfoy":    "Stop'ları gevşet. Kazananları koru.",
        "stop":       "Chandelier gevşet (bant içi fiyatlama).",
        "sektör":     "Sektör liderliği belli değil, genişlik kontrolü.",
        "emoji":      "⚪",
    },
    "BEAR": {
        "swing":      "Yarı büyüklük. Sadece net setup'lar.",
        "portfoy":    "Defansif rotasyon. Kazananları kes, nakit artır.",
        "stop":       "Stopları sıkıştır. K-09 sık kontrol.",
        "sektör":     "XLP, XLU, GLD, sağlık sektörü.",
        "emoji":      "🔴",
    },
    "KRİZ": {
        "swing":      "YENİ GİRİŞ YOK. Mevcut pozisyonlar K-09 ile.",
        "portfoy":    "Nakit artır. Zayıfları kes. K-14 protokolü.",
        "stop":       "Stop override YASAK. K-06 çalışsın.",
        "sektör":     "Tüm girişler durduruldu.",
        "emoji":      "🚨",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# 4. KAYIT VE GEÇMİŞ TAKİBİ
# ══════════════════════════════════════════════════════════════════════════════

def rejim_kaydet(rejim_data: dict, spy: dict, sektorler: dict):
    """Rejimi JSON'a kaydeder, 30 günlük geçmiş tutar."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Mevcut dosyayı oku
    if REGIME_FILE.exists():
        with open(REGIME_FILE, encoding="utf-8") as f:
            mevcut = json.load(f)
    else:
        mevcut = {"gecmis": []}

    gecmis = mevcut.get("gecmis", [])

    kayit = {
        "tarih":            now,
        "rejim":            rejim_data["rejim"],
        "alt_rejim":        rejim_data["alt_rejim"],
        "vix":              rejim_data["vix_deger"],
        "spy_fiyat":        spy.get("guncel", 0),
        "spy_ema21_uzeri":  rejim_data["spy_ema21_uzeri"],
        "rotasyon":         rejim_data["rotasyon"],
        "carpan":           rejim_data["pozisyon_carpani"],
    }

    gecmis.insert(0, kayit)
    gecmis = gecmis[:30]  # Son 30 kayıt

    output = {
        "son_guncelleme":    now,
        "guncel_rejim":      rejim_data,
        "spy":               spy,
        "sektorler":         sektorler,
        "gecmis":            gecmis,
        "aksiyonlar":        REJIM_AKSIYONLARI.get(rejim_data["rejim"], {}),
    }

    with open(REGIME_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


# ══════════════════════════════════════════════════════════════════════════════
# 5. ÇIKTI FORMATLAMA
# ══════════════════════════════════════════════════════════════════════════════

def rapor_yazdir(rejim: dict, spy: dict, sektorler: dict, tam: bool = False):
    aks = REJIM_AKSIYONLARI.get(rejim["rejim"], {})
    emoji = aks.get("emoji", "⚪")

    print(f"\n{'='*60}")
    print(f"  {emoji} PİYASA REJİMİ — {datetime.now().strftime('%d %B %Y %H:%M')}")
    print(f"{'='*60}")
    print(f"\n  Rejim    : {rejim['rejim']} ({rejim['alt_rejim']})")
    print(f"  Güven    : %{rejim['guven']}")
    print(f"  Pos. çarp: ×{rejim['pozisyon_carpani']}")
    print(f"  Tarama   : {rejim['tarama_modu']}")

    print(f"\n  📊 GÖSTERGELER")
    if spy:
        ema_ok = "✅" if rejim["spy_ema21_uzeri"] else "❌"
        sma_ok = "✅" if rejim["spy_sma50_uzeri"] else "❌"
        print(f"  SPY     : ${spy.get('guncel', 0):.2f} "
              f"({spy.get('gun_degisim', 0):+.2f}%)")
        print(f"  21EMA   : ${spy.get('ema21', 0):.2f} {ema_ok}")
        print(f"  50SMA   : ${spy.get('sma50', 0):.2f} {sma_ok}")
        print(f"  5g eğim : {spy.get('egim5g', 0):+.2f}%")

    vix = rejim["vix_deger"]
    print(f"  VIX     : {vix:.1f} [{rejim['vix_band']}]")
    print(f"  Rotasyon: {rejim['rotasyon']} "
          f"(fark: {rejim['rotasyon_farki']:+.2f}%)")

    if rejim["uyarilar"]:
        print(f"\n  ⚠️  UYARILAR:")
        for u in rejim["uyarilar"]:
            print(f"     • {u}")

    print(f"\n  🎯 AKSİYONLAR ({rejim['rejim']}):")
    print(f"  Swing   : {aks.get('swing', '—')}")
    print(f"  Portföy : {aks.get('portfoy', '—')}")
    print(f"  Stop    : {aks.get('stop', '—')}")
    print(f"  Sektör  : {aks.get('sektör', '—')}")

    if tam and sektorler:
        print(f"\n  🏢 SEKTÖR PERFORMANSI (günlük):")
        sirali = sorted(sektorler.items(), key=lambda x: -x[1].get("gunluk", 0))
        for sym, d in sirali:
            bar = "▲" if d["gunluk"] > 0 else "▼"
            print(f"  {bar} {d['isim']:<15} {d['gunluk']:+.2f}%")

    print(f"\n{'='*60}\n")


def prompt_inject_metni(rejim_file: str = None) -> str:
    """
    Sabah promptuna enjekte edilecek rejim bağlamı.
    session_state.json veya doğrudan çağrı ile kullanılır.
    """
    try:
        path = Path(rejim_file) if rejim_file else REGIME_FILE
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        r  = data["guncel_rejim"]
        ak = data.get("aksiyonlar", {})
        emoji = ak.get("emoji", "⚪")
        uyari = "\n".join(f"  ⚠️ {u}" for u in r.get("uyarilar", []))
        return f"""{emoji} PİYASA REJİMİ: {r['rejim']} — {r['alt_rejim']}
VIX: {r['vix_deger']:.1f} [{r['vix_band']}] | SPY 21EMA: {'✅' if r['spy_ema21_uzeri'] else '❌'} | Rotasyon: {r['rotasyon']}
Pozisyon çarpanı: ×{r['pozisyon_carpani']} | Tarama modu: {r['tarama_modu']}
Swing aksiyonu: {ak.get('swing', '—')}
{uyari}"""
    except Exception:
        return "⚪ Rejim verisi yok — önce market_regime.py çalıştır"


# ══════════════════════════════════════════════════════════════════════════════
# 6. CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — Piyasa Rejimi Tespiti"
    )
    parser.add_argument("--full",    action="store_true", help="Sektör tablosu dahil tam rapor")
    parser.add_argument("--json",    action="store_true", help="JSON çıktı (prompt için)")
    parser.add_argument("--history", action="store_true", help="Son 30 gün rejim geçmişi")
    parser.add_argument("--inject",  action="store_true", help="Prompt enjeksiyon metni")
    parser.add_argument("--no-save", action="store_true", help="JSON'a kaydetme")
    parser.add_argument("--vix", type=float, default=0.0, help="VIX degerini manuel gir")
    args = parser.parse_args()

    # Geçmiş modu — sadece dosyayı oku
    if args.history:
        if REGIME_FILE.exists():
            with open(REGIME_FILE) as f:
                data = json.load(f)
            gecmis = data.get("gecmis", [])
            print(f"\n📅 SON {len(gecmis)} REJİM KAYDI:\n")
            for g in gecmis[:15]:
                emoji = REJIM_AKSIYONLARI.get(g["rejim"], {}).get("emoji", "⚪")
                print(f"  {emoji} {g['tarih'][:10]} | {g['rejim']:<14} | "
                      f"VIX:{g['vix']:4.1f} | SPY ${g['spy_fiyat']:.0f} | ×{g['carpan']}")
        else:
            print("Henüz geçmiş kayıt yok.")
        return

    if args.inject:
        print(prompt_inject_metni())
        return

    # Veri çek
    print("📡 Veri çekiliyor...", flush=True)
    spy      = spy_fiyat_ve_ema()
    vix      = args.vix if args.vix > 0 else vix_oku()
    sektorler = sektor_performans()

    if not spy:
        print("❌ SPY verisi alınamadı.")
        sys.exit(1)

    # Rejim belirle
    rejim = rejim_siniflandir(spy, vix, sektorler)

    # Kaydet
    if not args.no_save:
        rejim_kaydet(rejim, spy, sektorler)

    # Çıktı
    if args.json:
        print(json.dumps({"rejim": rejim, "spy": spy}, ensure_ascii=False, indent=2))
    else:
        rapor_yazdir(rejim, spy, sektorler, tam=args.full)


if __name__ == "__main__":
    main()
