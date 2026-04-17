#!/usr/bin/env python3
"""
Finzora Agent — Piyasa Rejimi Tespiti
=======================================
Growth portföyü için aktif makro rejimi belirler.
Sektör rotasyon kararlarına temel oluşturur.

Rejimler:
  - jeopolitik_kriz   : VIX spike + savunma/enerji liderliği
  - ai_boom           : Tech/semicon liderliği + AI haber akışı
  - faiz_dusus        : Fed pivot sinyali + growth outperform
  - tarife_gerilimi   : Hammadde + iç üretim öne çıkıyor
  - risk_on_genel     : Düşük VIX, momentum liderleri
  - risk_off          : VIX yüksek, defansif liderlik
"""

import requests
import json
from pathlib import Path
import pytz
from datetime import datetime

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
FMP_KEY    = os.environ.get("FMP_API_KEY", "")
TR_TZ      = pytz.timezone("Europe/Istanbul")

# Sektör ETF'leri
SEKTOR_ETFS = ["XLE","XLK","XLI","XLF","XLV","XLU","XLP","XLY","XLB","GLD","ITA"]

def get_sektor_performans() -> dict:
    """Son 1 aylık sektör performansları."""
    try:
        r = requests.get(
            "https://financialmodelingprep.com/stable/batch-quote",
            params={"symbols": ",".join(SEKTOR_ETFS), "apikey": FMP_KEY},
            timeout=12
        ).json()

        result = {}
        for q in r:
            sym   = q["symbol"]
            price = q.get("price", 0) or 0
            prev  = q.get("previousClose", 0) or 0
            chg   = ((price - prev) / prev * 100) if prev else 0
            result[sym] = {"price": price, "gunluk_chg": round(chg, 2)}
        return result
    except Exception as e:
        print(f"[Rejim] Sektör verisi hatası: {e}")
        return {}

def detect_regime(market: dict, sektor: dict, vix: float) -> dict:
    """
    Piyasa verilerine bakarak aktif rejimi tespit eder.
    """
    skorlar = {
        "jeopolitik_kriz":  0,
        "ai_boom":          0,
        "faiz_dusus":       0,
        "tarife_gerilimi":  0,
        "risk_on_genel":    0,
        "risk_off":         0,
    }

    # VIX değerlendirmesi
    if vix:
        if vix > 30:
            skorlar["risk_off"]         += 3
            skorlar["jeopolitik_kriz"]  += 2
        elif vix > 22:
            skorlar["risk_off"]         += 1
        elif vix < 15:
            skorlar["risk_on_genel"]    += 2
            skorlar["ai_boom"]          += 1

    # Sektör liderliği değerlendirmesi
    if sektor:
        ita_chg = sektor.get("ITA", {}).get("gunluk_chg", 0) or 0
        xle_chg = sektor.get("XLE", {}).get("gunluk_chg", 0) or 0
        xlk_chg = sektor.get("XLK", {}).get("gunluk_chg", 0) or 0
        gld_chg = sektor.get("GLD", {}).get("gunluk_chg", 0) or 0
        xlb_chg = sektor.get("XLB", {}).get("gunluk_chg", 0) or 0
        xlp_chg = sektor.get("XLP", {}).get("gunluk_chg", 0) or 0

        # Savunma + Enerji güçlü → jeopolitik
        if ita_chg > 1 and xle_chg > 0.5:
            skorlar["jeopolitik_kriz"] += 3
        elif ita_chg > 0.5 or xle_chg > 1:
            skorlar["jeopolitik_kriz"] += 1

        # Tech güçlü → AI boom
        if xlk_chg > 1:
            skorlar["ai_boom"] += 2
        elif xlk_chg > 0.3:
            skorlar["ai_boom"] += 1

        # Defansif liderlik → risk-off
        if xlp_chg > 0 and xlk_chg < 0:
            skorlar["risk_off"] += 2

        # Altın güçlü → jeopolitik veya risk-off
        if gld_chg > 1:
            skorlar["jeopolitik_kriz"] += 1
            skorlar["risk_off"]        += 1

        # Hammadde güçlü → tarife
        if xlb_chg > 1.5:
            skorlar["tarife_gerilimi"] += 2

    # SPY hareketi
    spy = market.get("SPY", {})
    spy_chg = spy.get("chg", 0) or 0
    if spy_chg > 1:
        skorlar["risk_on_genel"] += 2
        skorlar["ai_boom"]       += 1
    elif spy_chg < -2:
        skorlar["risk_off"]      += 2

    # Aktif rejim = en yüksek skorlu
    aktif = max(skorlar, key=lambda k: skorlar[k])
    guven = "YÜKSEK" if skorlar[aktif] >= 4 else "ORTA" if skorlar[aktif] >= 2 else "DÜŞÜK"

    # Growth portföy için aksiyon
    aksiyon_map = {
        "jeopolitik_kriz":  "Savunma (ITA, LMT, RTX) + Enerji (XLE, CVX) ağırlığını artır. AI tezini koru ama yeni giriş yapma.",
        "ai_boom":          "Mevcut AI pozisyonlar (COHR, VRT, ANET, MU, CAMT) tutulmaya devam. Yeni AI fırsatları ara.",
        "faiz_dusus":       "Büyüme hisseleri (PLTR, APP, SQ) radar'ına al. AI pozisyonlar korunur.",
        "tarife_gerilimi":  "İç üretim + hammadde (FCX, CLF, NUE) tara. Çin bağlantılı tech dikkatli.",
        "risk_on_genel":    "En güçlü RS hisselerine odaklan. Momentum liderleri.",
        "risk_off":         "YÖN DEĞİŞTİR: Savunma (ITA, LMT) + Altın (GLD, RGLD) + Enerji (XLE). Gerekirse inverse ETF (SH, PSQ). Para hep bir yere akıyor — o yeri bul.",
    }

    return {
        "aktif_rejim":    aktif,
        "skor":           skorlar[aktif],
        "guven":          guven,
        "tum_skorlar":    skorlar,
        "growth_aksiyon": aksiyon_map.get(aktif, "Rejim neti değil, bekle"),
        "tespit_zamani":  datetime.now(TR_TZ).isoformat(),
    }

def run_regime_detection(market: dict = None, vix: float = None) -> dict:
    """Ana fonksiyon — rejimi tespit eder ve memory'e kaydeder."""
    sektor = get_sektor_performans()

    if vix is None:
        vix = 20.0  # Varsayılan

    rejim = detect_regime(market or {}, sektor, vix)

    # Memory'e kaydet
    rejim_path = MEMORY_DIR / "market_regime.json"
    with open(rejim_path, "w", encoding="utf-8") as f:
        json.dump({
            "rejim":       rejim,
            "sektor_data": sektor,
        }, f, ensure_ascii=False, indent=2)

    print(f"[Rejim] Aktif: {rejim['aktif_rejim']} (güven: {rejim['guven']})")
    print(f"[Rejim] Growth aksiyonu: {rejim['growth_aksiyon']}")
    return rejim

def get_regime_context() -> str:
    """Claude context'i için rejim özeti."""
    rejim_path = MEMORY_DIR / "market_regime.json"
    if not rejim_path.exists():
        return "Rejim tespiti henüz yapılmadı."

    with open(rejim_path, encoding="utf-8") as f:
        data = json.load(f)

    r = data.get("rejim", {})
    sektor = data.get("sektor_data", {})

    # Sektör sıralaması
    sektor_sirali = sorted(
        [(s, d.get("gunluk_chg", 0)) for s, d in sektor.items()],
        key=lambda x: -x[1]
    )

    lines = [
        "=== AKTİF PİYASA REJİMİ ===",
        f"Rejim: {r.get('aktif_rejim','?').upper()} (güven: {r.get('guven','?')})",
        f"Growth Aksiyonu: {r.get('growth_aksiyon','')}",
        "",
        "Sektör Liderleri (günlük):",
    ]
    for sym, chg in sektor_sirali[:5]:
        icon = "🟢" if chg > 0 else "🔴"
        lines.append(f"  {icon} {sym}: {chg:+.2f}%")

    return "\n".join(lines)
