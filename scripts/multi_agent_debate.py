#!/usr/bin/env python3
"""
Finzora AI — Çoklu Ajan Tartışma Sistemi (Katman 5)
====================================================
Her swing trade adayı için 3 bağımsız ajan analizi üretir.
Boğa (Bull), Ayı (Bear) ve Risk ajanları bağımsız puanlar,
Moderatör ajan sentezi yaparak nihai karar verir.

Kullanım:
  python3 scripts/multi_agent_debate.py --symbol NVDA
  python3 scripts/multi_agent_debate.py --symbol CAT --setup "tenkan_bounce sma50_bounce"
  python3 scripts/multi_agent_debate.py --scan               # Tüm tarama adaylarını tartış
  python3 scripts/multi_agent_debate.py --symbol NVDA --json # JSON çıktı
"""

import os
import json
import sys
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, date

BASE      = Path(__file__).parent.parent
FMP_KEY   = os.environ.get("FMP_API_KEY", "")
FMP_BASE  = "https://financialmodelingprep.com/stable"

SCAN_FILE   = BASE / "data" / "swing_entry_signals.json"
REGIME_FILE = BASE / "data" / "market_regime.json"
OUTPUT_FILE = BASE / "data" / "agent_debate_results.json"


# ══════════════════════════════════════════════════════════════════════════════
# 1. VERİ ÇEKME
# ══════════════════════════════════════════════════════════════════════════════

def fmp(endpoint: str, params: dict = {}) -> dict | list | None:
    params["apikey"] = FMP_KEY
    url = f"{FMP_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FinzoraAI/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except Exception as e:
        return None


def hisse_veri_cek(sembol: str) -> dict:
    """Bir hisse için tüm gerekli teknik ve temel veriyi çeker."""
    sonuc = {"sembol": sembol, "hata": []}

    # Fiyat ve teknik veriler
    quote = fmp("batch-quote", {"symbols": sembol})
    if quote and isinstance(quote, list):
        q = quote[0]
        fiyat   = q.get("price", 0)
        prev    = q.get("previousClose", fiyat)
        sonuc.update({
            "fiyat":   fiyat,
            "gun_deg": (fiyat - prev) / prev * 100 if prev else 0,
            "hacim":   q.get("volume", 0),
            "avg_vol": q.get("avgVolume", 1),
            "market_cap": q.get("marketCap", 0),
            "beta":    q.get("beta", 1.0),
            "52w_high": q.get("yearHigh", 0),
            "52w_low":  q.get("yearLow", 0),
        })
    else:
        sonuc["hata"].append("quote verisi yok")

    # RSI (14 günlük)
    rsi_data = fmp(f"technical-indicators/rsi", {
        "symbol": sembol, "periodLength": 14, "timeframe": "1day"
    })
    if rsi_data and isinstance(rsi_data, list):
        sonuc["rsi"] = round(rsi_data[0].get("rsi", 50), 1)
    else:
        sonuc["rsi"] = 50
        sonuc["hata"].append("RSI verisi yok")

    # ATR (14 günlük) — stop hesabı için
    atr_data = fmp(f"technical-indicators/atr", {
        "symbol": sembol, "periodLength": 14, "timeframe": "1day"
    })
    if atr_data and isinstance(atr_data, list):
        sonuc["atr14"] = round(atr_data[0].get("atr", 0), 2)
    else:
        sonuc["atr14"] = 0

    # SMA 50 ve 200
    for period in [50, 200]:
        sma = fmp(f"technical-indicators/sma", {
            "symbol": sembol, "periodLength": period, "timeframe": "1day"
        })
        if sma and isinstance(sma, list):
            sonuc[f"sma{period}"] = round(sma[0].get("sma", 0), 2)
        else:
            sonuc[f"sma{period}"] = 0

    # Beta — profile endpoint'ten al (batch-quote'ta eksik olabiliyor)
    profile = fmp("profile", {"symbol": sembol})
    if profile and isinstance(profile, list) and profile:
        beta_val = profile[0].get("beta")
        if beta_val is not None:
            sonuc["beta"] = float(beta_val)

    # Temel veriler (F/K, P/B vb.)
    metrics = fmp("key-metrics-ttm", {"symbol": sembol})
    if metrics and isinstance(metrics, list) and metrics:
        m = metrics[0]
        sonuc["pe_ttm"]  = m.get("peRatioTTM", 0)
        sonuc["pb_ttm"]  = m.get("pbRatioTTM", 0)
        sonuc["roe"]     = m.get("roeTTM", 0)
        sonuc["debt_eq"] = m.get("debtToEquityTTM", 0)
    else:
        sonuc["pe_ttm"] = sonuc["pb_ttm"] = sonuc["roe"] = sonuc["debt_eq"] = 0

    # Hesaplanan göstergeler
    if sonuc.get("fiyat") and sonuc.get("sma50"):
        sonuc["sma50_uzeri"] = sonuc["fiyat"] > sonuc["sma50"]
        sonuc["sma200_uzeri"] = sonuc["fiyat"] > sonuc.get("sma200", 0)
        sonuc["atr_stop"] = round(sonuc["fiyat"] - 2 * sonuc.get("atr14", 0), 2)
        sonuc["hacim_oran"] = (sonuc.get("hacim", 0) /
                               max(sonuc.get("avg_vol", 1), 1))
        sonuc["52w_pct"] = ((sonuc["fiyat"] - sonuc.get("52w_low", sonuc["fiyat"])) /
                             max(sonuc.get("52w_high", 1) - sonuc.get("52w_low", 1), 1) * 100)

    return sonuc


def rejim_yukle() -> dict:
    if REGIME_FILE.exists():
        with open(REGIME_FILE) as f:
            return json.load(f).get("guncel_rejim", {})
    return {}


# ══════════════════════════════════════════════════════════════════════════════
# 2. ÜÇLÜ AJAN PUANLAMA
# ══════════════════════════════════════════════════════════════════════════════

def boga_ajan(veri: dict, sinyaller: list, rejim: dict) -> dict:
    """
    Boğa ajan: Neden ALMALIYIZ?
    Momentum, teknik kurulum, sektör gücü, katalizörü inceler.
    """
    puan = 0
    guclu = []
    zayif = []

    rsi = veri.get("rsi", 50)
    sma50_uzeri = veri.get("sma50_uzeri", False)
    sma200_uzeri = veri.get("sma200_uzeri", False)
    hacim_oran = veri.get("hacim_oran", 1)
    gun_deg = veri.get("gun_degisim", veri.get("gun_deg", 0))
    w52_pct = veri.get("52w_pct", 50)

    # RSI momentum (30-70 arası ideal swing girişi)
    if 40 <= rsi <= 65:
        puan += 20
        guclu.append(f"RSI {rsi} — ideal momentum bölgesi (40-65)")
    elif 65 < rsi <= 72:
        puan += 10
        guclu.append(f"RSI {rsi} — güçlü momentum, henüz aşırı alım değil")
    elif rsi < 40:
        puan += 5
        zayif.append(f"RSI {rsi} — düşük momentum, giriş için erken")
    else:
        zayif.append(f"RSI {rsi} — aşırı alım bölgesine yakın")

    # SMA üzeri (trend teyidi)
    if sma50_uzeri:
        puan += 20
        guclu.append("Fiyat SMA50 üzerinde — orta vadeli trend yukarı")
    else:
        zayif.append("Fiyat SMA50 altında — K-RSI engeli")

    if sma200_uzeri:
        puan += 10
        guclu.append("Fiyat SMA200 üzerinde — uzun vadeli bull trendi")

    # Hacim teyidi
    if hacim_oran >= 1.5:
        puan += 20
        guclu.append(f"Hacim {hacim_oran:.1f}x — güçlü alıcı ilgisi")
    elif hacim_oran >= 1.2:
        puan += 10
        guclu.append(f"Hacim {hacim_oran:.1f}x — ortalama üzeri")
    else:
        zayif.append(f"Hacim {hacim_oran:.1f}x — yetersiz alıcı katılımı")

    # Günlük hareket (giriş momentumu)
    if gun_deg >= 3:
        puan += 15
        guclu.append(f"Gün hareketi %{gun_deg:.1f} — güçlü momentum girişi")
    elif gun_deg >= 1:
        puan += 8
        guclu.append(f"Gün hareketi %{gun_deg:.1f} — pozitif")
    elif gun_deg < -2:
        zayif.append(f"Gün hareketi %{gun_deg:.1f} — zayıf gün")

    # Ichimoku/teknik sinyaller
    iyi_sinyaller = [s for s in sinyaller if s in
                     ("tenkan_bounce", "kijun_bounce_v2", "ichimoku_4of4",
                      "sma50_bounce", "golden_cross", "nr7_sikisma")]
    puan += len(iyi_sinyaller) * 5
    if iyi_sinyaller:
        guclu.append(f"Teknik sinyaller: {', '.join(iyi_sinyaller)}")

    # 52 haftalık konum
    if 40 <= w52_pct <= 80:
        puan += 5
        guclu.append(f"52h konumu %{w52_pct:.0f} — güçlü ama aşırı değil")
    elif w52_pct > 90:
        zayif.append(f"52h konumu %{w52_pct:.0f} — zirveye yakın")

    # Rejim çarpanı
    carpan = rejim.get("pozisyon_carpani", 0.75)
    if carpan >= 1.0:
        puan += 5
        guclu.append("Rejim TREND_BULL — ek destek")
    elif carpan < 0.5:
        puan = int(puan * 0.7)
        zayif.append(f"Rejim {rejim.get('rejim', '?')} — olumsuz ortam")

    return {
        "ajan": "🐂 BOĞA",
        "puan": min(puan, 100),
        "karar": "AL" if puan >= 55 else "GEÇ",
        "guclu_yanlar": guclu,
        "zayif_yanlar": zayif,
        "ozet": f"Puan {puan}/100 — {'Güçlü setup, giriş mantıklı' if puan >= 55 else 'Setup henüz yeterince güçlü değil'}",
    }


def ayi_ajan(veri: dict, sinyaller: list, rejim: dict) -> dict:
    """
    Ayı ajan: Neden ALMAMALIYI Z?
    Riskler, olumsuz sinyaller, makro tehditler, kural ihlalleri.
    """
    risk_puan = 0  # Yüksek = daha riskli
    riskler = []
    savunma = []

    rsi = veri.get("rsi", 50)
    sma50_uzeri = veri.get("sma50_uzeri", False)
    market_cap = veri.get("market_cap", 0)
    beta = veri.get("beta", 1.0)
    hacim_oran = veri.get("hacim_oran", 1)
    vix = rejim.get("vix_deger", 20)
    vix_band = rejim.get("vix_band", "NORMAL")
    gun_deg = veri.get("gun_degisim", veri.get("gun_deg", 0))
    sembol = veri.get("sembol", "")

    # K-EVR hard-coded yasak listesi (beta verisi gelmese bile)
    K_EVR_YASAK = {
        "VZ", "T", "TMUS",           # Telekom
        "DUK", "NEE", "SO", "EXC",   # Kamu hizmetleri
        "DVA", "HUM", "UHS",          # Defensif sağlık
        "WMT", "TGT", "COST",         # Büyük defensif perakende
        "AMT", "O", "VICI",           # Defensif REIT
        "KO", "PEP", "CL",            # Defensive staples
    }
    if sembol.upper() in K_EVR_YASAK:
        risk_puan += 50
        riskler.append(f"K-EVR İHLALİ: {sembol} swing yasak listesinde (düşük beta sektör)")

    # K-EVR: Beta < 0.7 → swing evreni dışı
    if beta < 0.7:
        risk_puan += 40
        riskler.append(f"K-EVR İHLALİ: Beta {beta:.2f} < 0.7 — swing evrenine girmez")
    elif beta > 2.5:
        risk_puan += 15
        riskler.append(f"Yüksek beta {beta:.1f} — volatilite riski")

    # K-EVR: Market cap < $2B
    if market_cap and market_cap < 2_000_000_000:
        risk_puan += 35
        riskler.append(f"K-EVR İHLALİ: Market cap ${market_cap/1e9:.1f}B < $2B — swing yasak")
    elif market_cap and market_cap < 5_000_000_000:
        risk_puan += 10
        riskler.append(f"Küçük/orta cap ${market_cap/1e9:.1f}B — likidite riski")

    # VIX ortam riski (K-13)
    if vix_band == "KRİZ" or vix_band == "PANIK":
        risk_puan += 50
        riskler.append(f"K-13 İHLALİ: VIX {vix:.0f} [{vix_band}] — duyarlı sektörde giriş yasak")
    elif vix_band == "YÜKSEK" and beta > 1.5:
        risk_puan += 25
        riskler.append(f"VIX {vix:.0f} + yüksek beta — K-13 yarı pozisyon")

    # SMA50 altı (K-RSI giriş şartı)
    if not sma50_uzeri:
        risk_puan += 25
        riskler.append("SMA50 altı — K-RSI/K-EVR giriş şartı karşılanmıyor")
    else:
        savunma.append("SMA50 üzerinde — trend teyidi var")

    # RSI aşırı alım
    if rsi > 72:
        risk_puan += 20
        riskler.append(f"RSI {rsi} — aşırı alım, K-11 profit lock devreye girebilir")
    elif rsi < 30:
        risk_puan += 15
        riskler.append(f"RSI {rsi} — aşırı satım, dip avlama riski")

    # Hacim onaysız hareket
    if hacim_oran < 0.8 and abs(gun_deg) > 2:
        risk_puan += 20
        riskler.append(f"Hareket %{gun_deg:.1f} ama hacim düşük {hacim_oran:.1f}x — sahte breakout riski")

    # Büyük günlük hareket sonrası giriş
    if gun_deg > 7:
        risk_puan += 25
        riskler.append(f"Günlük %{gun_deg:.1f} hareket — kriz rally kuralı, 1 gün cooling bekle")
    elif gun_deg < -5:
        risk_puan += 20
        riskler.append(f"Sert düşüş %{gun_deg:.1f} — dip avlama, momentum onayı yok")

    # Olumsuz sinyaller
    kotu = [s for s in sinyaller if "zarar" in s.lower() or "düşüş" in s.lower()
            or s in ("rsi_overbought", "sma_breakdown", "volume_weak")]
    if kotu:
        risk_puan += len(kotu) * 10
        riskler.append(f"Olumsuz sinyaller: {', '.join(kotu)}")

    # Savunma puanları
    if market_cap and market_cap > 50_000_000_000:
        savunma.append(f"Büyük cap ${market_cap/1e9:.0f}B — likidite sağlam")
    if hacim_oran >= 1.5:
        savunma.append(f"Hacim teyidi {hacim_oran:.1f}x — sahte breakout değil")

    risk_puan = min(risk_puan, 100)
    return {
        "ajan": "🐻 AYI",
        "risk_puan": risk_puan,
        "karar": "GEÇ" if risk_puan >= 40 else "AL",
        "riskler": riskler,
        "savunma": savunma,
        "ozet": (f"Risk skoru {risk_puan}/100 — "
                 f"{'Ciddi riskler var, geç' if risk_puan >= 60 else 'Orta risk' if risk_puan >= 40 else 'Kabul edilebilir risk'}"),
    }


def risk_ajan(veri: dict, sinyaller: list, rejim: dict,
              portfoy_nakit: float = 50000) -> dict:
    """
    Risk ajan: Pozisyon boyutu, stop mesafesi, max kayıp, R:R hesaplar.
    """
    sembol    = veri.get("sembol", "")
    fiyat     = veri.get("fiyat", 0)
    atr14     = veri.get("atr14", 0)
    beta      = veri.get("beta", 1.0)
    vix_band  = rejim.get("vix_band", "NORMAL")
    carpan    = rejim.get("pozisyon_carpani", 0.75)
    sorunlar  = []
    onaylar   = []

    # Temel pozisyon büyüklüğü
    baz_pozisyon = 10_000  # Swing başlangıç
    rejim_poz    = baz_pozisyon * carpan

    # Stop hesabı (K-ATR kuralı)
    if atr14 > 0:
        atr_stop_mesafe = 2 * atr14
        stop_fiyat      = round(fiyat - atr_stop_mesafe, 2)
        stop_pct        = atr_stop_mesafe / fiyat * 100
        atm_kontrol     = True
        onaylar.append(f"Stop: ${stop_fiyat} (2×ATR = %{stop_pct:.1f})")
    else:
        atr_stop_mesafe = fiyat * 0.05
        stop_fiyat      = round(fiyat * 0.95, 2)
        stop_pct        = 5.0
        atm_kontrol     = False
        sorunlar.append("ATR verisi yok — %5 sabit stop kullanıldı")

    # K-ATR kontrolü — mesafe yeterli mi?
    if atr_stop_mesafe < fiyat * 0.03:
        sorunlar.append(f"K-ATR UYARI: Stop mesafesi %{stop_pct:.1f} < %3 — pozisyon yarıya indir")
        rejim_poz = rejim_poz * 0.5

    # Hedef hesabı (min 2:1 R:R)
    hedef_min = round(fiyat + 2 * atr_stop_mesafe, 2)
    hedef_pct = (hedef_min - fiyat) / fiyat * 100

    # Hisse adedi
    if fiyat > 0:
        adet = max(1, int(rejim_poz / fiyat))
        gercek_poz = adet * fiyat
    else:
        adet = 0
        gercek_poz = 0
        sorunlar.append("Fiyat verisi yok")

    # Max kayıp hesabı
    max_kayip     = adet * atr_stop_mesafe
    max_kayip_pct = max_kayip / gercek_poz * 100 if gercek_poz else 0

    # Nakit kontrolü
    if gercek_poz > portfoy_nakit * 0.15:
        sorunlar.append(f"Pozisyon ${gercek_poz:,.0f} — nakit'in %{gercek_poz/portfoy_nakit*100:.0f}'i (limit %15)")

    # R:R oranı
    rr_oran = (hedef_min - fiyat) / atr_stop_mesafe if atr_stop_mesafe > 0 else 0
    if rr_oran >= 2.0:
        onaylar.append(f"R:R {rr_oran:.1f}:1 — minimum şart karşılanıyor")
    else:
        sorunlar.append(f"R:R {rr_oran:.1f}:1 — minimum 2:1 altında")

    # VIX stres testi
    if vix_band in ("YÜKSEK", "KRİZ", "PANIK"):
        stres_kayip = max_kayip * 1.5
        onaylar.append(f"VIX stres testi: {vix_band} ortamda max kayıp → ${stres_kayip:,.0f}")

    karar = "AL" if len(sorunlar) <= 1 and rr_oran >= 2.0 else "GEÇ"

    return {
        "ajan": "⚖️ RİSK",
        "karar": karar,
        "pozisyon": {
            "adet": adet,
            "buyukluk": round(gercek_poz, 0),
            "stop": stop_fiyat,
            "stop_pct": round(stop_pct, 1),
            "hedef_min": hedef_min,
            "hedef_pct": round(hedef_pct, 1),
            "rr_oran": round(rr_oran, 1),
            "max_kayip": round(max_kayip, 0),
        },
        "onaylar": onaylar,
        "sorunlar": sorunlar,
        "ozet": (f"R:R {rr_oran:.1f}:1 | Stop ${stop_fiyat} | "
                 f"Hedef ${hedef_min} | Max kayıp ${max_kayip:,.0f}"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. MODERATÖR SENTEZİ
# ══════════════════════════════════════════════════════════════════════════════

def moderator(boga: dict, ayi: dict, risk: dict, veri: dict) -> dict:
    """
    3 ajanın çıktısını ağırlıklı ortalama ile sentezler.
    Ağırlık: Boğa %40, Ayı %35, Risk %25
    """
    boga_puan = boga["puan"]
    ayi_puan  = 100 - ayi["risk_puan"]   # Risk→alet dönüşüm
    risk_ok   = 1.0 if risk["karar"] == "AL" else 0.5

    # Ağırlıklı skor
    skor = (boga_puan * 0.40 + ayi_puan * 0.35 + risk_ok * 100 * 0.25)
    skor = round(skor, 1)

    # Veto kontrolleri (her biri tek başına reddedebilir)
    veto = []
    beta = veri.get("beta", 1.0)
    mc   = veri.get("market_cap", 999e9)
    sma50 = veri.get("sma50_uzeri", True)

    if beta < 0.7:
        veto.append("K-EVR: Beta < 0.7 — swing yasak")
    if mc and mc < 2_000_000_000:
        veto.append("K-EVR: Market cap < $2B — swing yasak")
    if not sma50:
        veto.append("K-RSI: SMA50 altı — giriş şartı yok")
    if ayi["risk_puan"] >= 70:
        veto.append(f"AYI VETO: Risk skoru {ayi['risk_puan']}/100")
    if risk["pozisyon"]["rr_oran"] < 1.5:
        veto.append(f"RİSK VETO: R:R {risk['pozisyon']['rr_oran']:.1f} < 1.5")

    if veto:
        karar = "VETO ❌"
        konviksiyon = 0
    elif skor >= 70:
        karar = "GİRİŞ ✅"
        konviksiyon = min(int((skor - 70) * 3.3), 100)
    elif skor >= 55:
        karar = "İZLE 👁️"
        konviksiyon = int((skor - 55) * 6.6)
    else:
        karar = "GEÇ ❌"
        konviksiyon = 0

    return {
        "sentez_skoru": skor,
        "karar": karar,
        "konviksiyon": konviksiyon,
        "veto_listesi": veto,
        "boga_puan": boga_puan,
        "ayi_risk": ayi["risk_puan"],
        "risk_karar": risk["karar"],
        "onerilen_stop": risk["pozisyon"]["stop"],
        "onerilen_hedef": risk["pozisyon"]["hedef_min"],
        "onerilen_adet": risk["pozisyon"]["adet"],
        "rr": risk["pozisyon"]["rr_oran"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. TAM TARTIŞMA — TEK SEMBOL
# ══════════════════════════════════════════════════════════════════════════════

def tartis(sembol: str, sinyaller: list = None,
           portfoy_nakit: float = 50000, sessiz: bool = False) -> dict:
    """Ana tartışma fonksiyonu. Tüm ajanları çalıştırır."""
    if sinyaller is None:
        sinyaller = []

    print(f"  📡 {sembol} verisi çekiliyor...", flush=True)
    veri  = hisse_veri_cek(sembol)
    rejim = rejim_yukle()

    if not veri.get("fiyat"):
        return {"sembol": sembol, "hata": "Fiyat verisi alınamadı"}

    boga  = boga_ajan(veri, sinyaller, rejim)
    ayi   = ayi_ajan(veri, sinyaller, rejim)
    risk  = risk_ajan(veri, sinyaller, rejim, portfoy_nakit)
    mod   = moderator(boga, ayi, risk, veri)

    sonuc = {
        "sembol":    sembol,
        "tarih":     datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fiyat":     veri.get("fiyat", 0),
        "rsi":       veri.get("rsi", 0),
        "sinyaller": sinyaller,
        "boga":      boga,
        "ayi":       ayi,
        "risk":      risk,
        "moderator": mod,
    }

    if not sessiz:
        _yazdir(sonuc)

    return sonuc


def _yazdir(s: dict):
    """Tek hisse tartışma çıktısı."""
    m = s["moderator"]
    print(f"\n{'='*60}")
    print(f"  🎭 AJAN TARTIŞMASI — {s['sembol']} @ ${s['fiyat']:.2f}")
    print(f"  RSI: {s['rsi']} | Sinyaller: {', '.join(s['sinyaller']) or '—'}")
    print(f"{'='*60}")

    # Boğa
    b = s["boga"]
    print(f"\n  {b['ajan']} PUANI: {b['puan']}/100 → {b['karar']}")
    for g in b["guclu_yanlar"][:3]:
        print(f"    ✅ {g}")
    for z in b["zayif_yanlar"][:2]:
        print(f"    ⚠️  {z}")

    # Ayı
    a = s["ayi"]
    print(f"\n  {a['ajan']} RİSK: {a['risk_puan']}/100 → {a['karar']}")
    for r in a["riskler"][:3]:
        print(f"    ❌ {r}")
    for sv in a["savunma"][:1]:
        print(f"    🛡️  {sv}")

    # Risk
    r = s["risk"]
    p = r["pozisyon"]
    print(f"\n  {r['ajan']} KARAR: {r['karar']}")
    print(f"    Stop: ${p['stop']} (-%{p['stop_pct']}) | "
          f"Hedef: ${p['hedef_min']} (+%{p['hedef_pct']:.1f})")
    print(f"    R:R {p['rr_oran']}:1 | {p['adet']} hisse × ${s['fiyat']:.0f} = ${p['buyukluk']:,.0f}")
    print(f"    Max kayıp: ${p['max_kayip']:,.0f}")
    for o in r["onaylar"][:2]:
        print(f"    ✅ {o}")
    for sr in r["sorunlar"][:2]:
        print(f"    ⚠️  {sr}")

    # Moderatör karar
    print(f"\n{'─'*60}")
    print(f"  🎯 MODERATÖR KARARI: {m['karar']}")
    print(f"  Sentez skoru: {m['sentez_skoru']}/100")
    if m["konviksiyon"]:
        print(f"  Konviksiyon: %{m['konviksiyon']}")
    if m["veto_listesi"]:
        print(f"  VETO sebepleri:")
        for v in m["veto_listesi"]:
            print(f"    🚫 {v}")
    if m["karar"] == "GİRİŞ ✅":
        print(f"\n  📋 ÖNERİLEN GİRİŞ:")
        print(f"     {p['adet']} hisse | Stop: ${m['onerilen_stop']} | "
              f"Hedef: ${m['onerilen_hedef']} | R:R {m['rr']}:1")
    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 5. TARAMA ÇIKTISINI TARTIŞMAYA TABİ TUT
# ══════════════════════════════════════════════════════════════════════════════

def tarama_tartis(nakit: float = 50000):
    """Günlük swing tarama çıktısındaki tüm adayları tartışır."""
    if not SCAN_FILE.exists():
        print("❌ Tarama dosyası bulunamadı:", SCAN_FILE)
        return

    with open(SCAN_FILE) as f:
        tarama = json.load(f)

    adaylar = tarama.get("giris_sinyalleri", [])
    detaylar = {d["symbol"]: d for d in tarama.get("detay", [])}

    if not adaylar:
        print("Tarama sonucunda aday yok.")
        return

    print(f"\n🎭 {len(adaylar)} aday tartışmaya alınıyor...\n")

    sonuclar = []
    for sembol in adaylar:
        det = detaylar.get(sembol, {})
        sinyaller = det.get("sinyaller", [])
        s = tartis(sembol, sinyaller, nakit)
        sonuclar.append(s)

    # Özet tablo
    print(f"\n{'='*60}")
    print(f"  📊 TARTIŞMA ÖZETİ")
    print(f"{'='*60}")
    gir = [s for s in sonuclar if "GİRİŞ" in s.get("moderator", {}).get("karar", "")]
    izle = [s for s in sonuclar if "İZLE" in s.get("moderator", {}).get("karar", "")]
    veto = [s for s in sonuclar if "VETO" in s.get("moderator", {}).get("karar", "")]
    gec  = [s for s in sonuclar if "GEÇ" in s.get("moderator", {}).get("karar", "")]

    for grup, label in [(gir, "GİRİŞ ✅"), (izle, "İZLE 👁️"), (veto, "VETO ❌"), (gec, "GEÇ ❌")]:
        if grup:
            print(f"\n  {label} ({len(grup)}):")
            for s in grup:
                m = s.get("moderator", {})
                print(f"    {s['sembol']:<8} Skor:{m.get('sentez_skoru',0):.0f} | "
                      f"R:R {m.get('rr',0):.1f} | Stop ${m.get('onerilen_stop',0)}")
    print()

    # JSON kaydet
    output = {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "toplam_aday": len(adaylar),
        "giris": len(gir),
        "izle": len(izle),
        "veto_gec": len(veto) + len(gec),
        "sonuclar": sonuclar,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ Sonuçlar kaydedildi: {OUTPUT_FILE}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — Çoklu Ajan Tartışma Sistemi"
    )
    parser.add_argument("--symbol", type=str,  help="Tek hisse analiz et")
    parser.add_argument("--setup",  type=str,  help="Teknik sinyaller (virgülle)")
    parser.add_argument("--scan",   action="store_true", help="Tüm tarama adaylarını tartış")
    parser.add_argument("--nakit",  type=float, default=50000, help="Swing nakit miktarı")
    parser.add_argument("--json",   action="store_true", help="JSON çıktı")
    args = parser.parse_args()

    if args.symbol:
        sinyaller = [s.strip() for s in args.setup.split(",")] if args.setup else []
        sonuc = tartis(args.symbol.upper(), sinyaller, args.nakit)
        if args.json:
            print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    elif args.scan:
        tarama_tartis(args.nakit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
