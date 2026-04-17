#!/usr/bin/env python3
"""
Finzora Agent — Risk Motoru
=============================
Portföy risk metrikleri:
  1. Pozisyon korelasyon analizi (K-17 desteği)
  2. Volatilite bazlı pozisyon boyutu önerisi
  3. Senaryo testi ("yarın %5 düşerse ne olur?")
  4. Drawdown takibi (K-14 desteği)
  5. Konsantrasyon riski

Tüm hesaplamalar sadece okuma — veri dosyalarına yazmaz.
"""

import json
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import pytz

REPO_ROOT = Path(__file__).parent.parent
TR_TZ     = pytz.timezone("Europe/Istanbul")
FMP_KEY   = os.environ.get("FMP_API_KEY", "")
FMP_BASE  = "https://financialmodelingprep.com/stable"


def fmp_get(endpoint: str, params: dict = None) -> list | dict:
    p = params or {}
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=12)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Risk] FMP hatası ({endpoint}): {e}")
        return []


# ── 1. Korelasyon Analizi ─────────────────────────────────────────────────────

# Sektör haritası (temel)
SECTOR_MAP = {
    "COHR": "technology", "VRT": "technology", "ANET": "technology",
    "MU": "technology", "CAMT": "technology", "NVDA": "technology",
    "AMD": "technology", "QCOM": "technology", "INTC": "technology",
    "MO": "consumer_staples", "T": "communication", "VZ": "communication",
    "MRK": "healthcare", "DUK": "utilities", "NEE": "utilities",
    "CI": "healthcare", "XOM": "energy", "CVX": "energy",
    "OKE": "energy", "FCX": "materials", "RGLD": "materials",
    "GLD": "commodities", "SPY": "index", "QQQ": "index",
}


def analyze_portfolio_correlation(portfolios: dict) -> dict:
    """
    3 portföy genelinde sektör konsantrasyonu ve korelasyon riski.
    K-17: Aynı sektörde çok pozisyon uyarısı.
    """
    sector_positions  = defaultdict(list)
    total_value       = 0
    sector_value      = defaultdict(float)

    for pf_name, pf_data in portfolios.items():
        for pos in pf_data.get("pozisyonlar", []):
            sym      = pos.get("sembol") or pos.get("symbol", "?")
            price    = pos.get("guncel_fiyat") or pos.get("maliyet_baz") or pos.get("maliyet_bazis") or 0
            adet     = pos.get("adet") or pos.get("shares") or 0

            try:
                value = float(price) * float(adet)
            except (TypeError, ValueError):
                value = 0

            sector = SECTOR_MAP.get(sym, "diger")
            sector_positions[sector].append({
                "sembol":   sym,
                "portfoy":  pf_name,
                "deger":    round(value),
            })
            sector_value[sector] += value
            total_value += value

    # Konsantrasyon hesapla
    concentration = {}
    for sector, val in sector_value.items():
        pct = (val / total_value * 100) if total_value > 0 else 0
        positions = sector_positions[sector]
        uyari = ""
        if pct > 40:
            uyari = "🔴 YÜKSEK KONSANTRASYON"
        elif pct > 25:
            uyari = "🟡 ORTA KONSANTRASYON"
        if len(positions) >= 3:
            uyari += " — K-17 riski"

        concentration[sector] = {
            "deger":       round(val),
            "yuzde":       round(pct, 1),
            "pozisyonlar": [p["sembol"] for p in positions],
            "uyari":       uyari,
        }

    # Uyarıları öne al
    warnings = [
        f"{s}: %{d['yuzde']} {d['uyari']}"
        for s, d in concentration.items()
        if d.get("uyari")
    ]

    return {
        "toplam_deger":   round(total_value),
        "konsantrasyon":  concentration,
        "uyarilar":       warnings,
    }


# ── 2. Volatilite Bazlı Pozisyon Boyutu ──────────────────────────────────────

def calculate_position_size(
    symbol: str,
    portfolio_value: float,
    risk_pct: float = 0.02,
    stop_pct: float = 0.08
) -> dict:
    """
    ATR bazlı pozisyon boyutu hesaplar.
    risk_pct: portföyün kaç %'i bu trade'de riske atılacak (varsayılan %2)
    stop_pct: stop-loss yüzdesi (varsayılan %8)
    """
    # ATR çek
    try:
        hist = fmp_get(
            f"historical-price-eod/full",
            {"symbol": symbol, "serietype": "line"}
        )
        if not hist or not isinstance(hist, list):
            raise ValueError("Veri yok")

        # Son 14 günün fiyatları
        closes = [float(d["close"]) for d in hist[:15] if d.get("close")]
        if len(closes) < 2:
            raise ValueError("Yetersiz veri")

        current_price = closes[0]

        # Basit ATR proxy: son 14 günün gün içi hareket ortalaması
        daily_ranges  = [abs(closes[i] - closes[i+1]) for i in range(min(14, len(closes)-1))]
        atr14         = sum(daily_ranges) / len(daily_ranges) if daily_ranges else current_price * 0.02

    except Exception as e:
        print(f"[Risk] {symbol} ATR hesaplama hatası: {e}")
        return {"hata": str(e)}

    # Risk tutarı
    risk_amount  = portfolio_value * risk_pct
    stop_amount  = current_price * stop_pct

    # Pozisyon boyutu
    shares       = int(risk_amount / stop_amount)
    position_val = shares * current_price
    position_pct = position_val / portfolio_value * 100

    # ATR bazlı stop
    atr_stop     = current_price - (2 * atr14)

    return {
        "sembol":         symbol,
        "guncel_fiyat":   round(current_price, 2),
        "atr14":          round(atr14, 2),
        "onerilen_adet":  shares,
        "pozisyon_degeri": round(position_val),
        "portfoy_yuzdesi": round(position_pct, 1),
        "risk_tutari":    round(risk_amount),
        "atr_stop":       round(atr_stop, 2),
        "sabit_stop":     round(current_price * (1 - stop_pct), 2),
        "not":            "ATR stop tercih edilir (sabit %8 yerine)"
    }


# ── 3. Senaryo Testi ──────────────────────────────────────────────────────────

def run_scenario_test(portfolios: dict, drop_pct: float = 5.0) -> dict:
    """
    "Piyasa %X düşerse portföyler ne olur?" senaryosu.
    Beta olmadan basit korelasyon varsayımı kullanır.
    """
    # Sektör beta varsayımları (yaklaşık)
    SECTOR_BETA = {
        "technology":      1.4,
        "communication":   1.0,
        "healthcare":      0.7,
        "utilities":       0.5,
        "consumer_staples": 0.6,
        "energy":          1.1,
        "materials":       1.2,
        "commodities":     0.3,
        "diger":           1.0,
        "index":           1.0,
    }

    results = {}
    toplam_kayip = 0
    toplam_deger = 0

    for pf_name, pf_data in portfolios.items():
        pf_kayip = 0
        pf_deger = 0
        pos_results = []

        for pos in pf_data.get("pozisyonlar", []):
            sym   = pos.get("sembol") or pos.get("symbol", "?")
            price = pos.get("guncel_fiyat") or pos.get("maliyet_baz") or pos.get("maliyet_bazis") or 0
            adet  = pos.get("adet") or pos.get("shares") or 0

            try:
                value = float(price) * float(adet)
            except (TypeError, ValueError):
                value = 0

            sector      = SECTOR_MAP.get(sym, "diger")
            beta        = SECTOR_BETA.get(sector, 1.0)
            beklenen_dd = value * (drop_pct / 100) * beta
            stop        = pos.get("stop_loss")
            stop_tetik  = ""

            if stop and price:
                try:
                    yeni_fiyat = float(price) * (1 - drop_pct / 100 * beta)
                    if yeni_fiyat <= float(stop):
                        stop_tetik = f"⚠️ STOP TETİKLENİR ({yeni_fiyat:.2f} ≤ {stop})"
                except (TypeError, ValueError):
                    pass

            # Stop tetikleniyorsa detay bilgisi
            stop_tetiklendi = bool(stop_tetik)
            stop_seviye     = float(stop) if stop else 0
            cur_price       = float(price) if price else 0
            uzaklik         = round((cur_price - stop_seviye) / cur_price * 100, 1) if cur_price and stop_seviye else 0

            pos_results.append({
                "sembol":           sym,
                "fiyat":            round(cur_price, 2),
                "tahmini_kayip":    round(beklenen_dd),
                "tahmini_zarar":    -round(beklenen_dd),
                "beta":             beta,
                "stop":             stop_tetik if stop_tetiklendi else "",
                "stop_seviye":      stop_seviye,
                "stop_uzaklik_pct": uzaklik,
            })
            pf_kayip += beklenen_dd
            pf_deger += value

        results[pf_name] = {
            "mevcut_deger":  round(pf_deger),
            "tahmini_kayip": round(pf_kayip),
            "kayip_yuzde":   round(pf_kayip / pf_deger * 100, 1) if pf_deger > 0 else 0,
            "pozisyonlar":   pos_results,
        }
        toplam_kayip += pf_kayip
        toplam_deger += pf_deger

    return {
        "senaryo":          f"Piyasa %{drop_pct} düşer",
        "toplam_deger":     round(toplam_deger),
        "tahmini_toplam_kayip": round(toplam_kayip),
        "kayip_yuzde":      round(toplam_kayip / toplam_deger * 100, 1) if toplam_deger > 0 else 0,
        "portfoyler":       results,
    }


# ── 4. Drawdown Takibi ────────────────────────────────────────────────────────

def check_drawdown_status(portfolios: dict) -> dict:
    """
    K-14: Portföy drawdown durumunu kontrol eder.
    Peak değer tracking.
    """
    dd_path = REPO_ROOT / "data" / "swing" / "status.json"
    status  = {}
    if dd_path.exists():
        with open(dd_path, encoding="utf-8") as f:
            status = json.load(f)

    results = {}
    for pf_name, pf_data in portfolios.items():
        baslangic = pf_data.get("baslangic_sermaye", 0)
        mevcut    = pf_data.get("toplam_deger", 0)

        if not baslangic or not mevcut:
            continue

        try:
            baslangic = float(baslangic)
            mevcut    = float(mevcut)
        except (TypeError, ValueError):
            continue

        dd_pct = (mevcut - baslangic) / baslangic * 100

        uyari = ""
        if dd_pct <= -15:
            uyari = "🔴 KRİTİK drawdown >%15 — psikoloji testi: mevcut pozisyonları yarın tekrar değerlendir"
        elif dd_pct <= -10:
            uyari = "🟡 UYARI drawdown >%10 — yeni giriş öncesi psikoloji testi zorunlu"
        elif dd_pct <= -5:
            uyari = "ℹ️ Drawdown >%5 — normal, stop disiplini koru"

        results[pf_name] = {
            "baslangic":  round(baslangic),
            "mevcut":     round(mevcut),
            "getiri_pct": round(dd_pct, 2),
            "uyari":      uyari,
        }

    return results


# ── 5. Risk Özeti ─────────────────────────────────────────────────────────────

def build_risk_context(portfolios: dict) -> str:
    """
    Tüm risk metriklerini Claude context'i için formatlar.
    """
    print("[Risk] Risk analizi yapılıyor...")

    corr    = analyze_portfolio_correlation(portfolios)
    dd      = check_drawdown_status(portfolios)
    scenario = run_scenario_test(portfolios, drop_pct=5.0)

    lines = ["=== RİSK ANALİZİ ===\n"]

    # Drawdown
    lines.append("--- PORTFÖY DURUMU (Başlangıca Göre) ---")
    for pf, data in dd.items():
        uyari = f" {data['uyari']}" if data.get("uyari") else ""
        lines.append(
            f"  {pf}: {data['getiri_pct']:+.1f}%"
            f" (${data['mevcut']:,} / ${data['baslangic']:,}){uyari}"
        )
    lines.append("")

    # Korelasyon uyarıları
    if corr["uyarilar"]:
        lines.append("--- KONSANTRASYON UYARILARI ---")
        for w in corr["uyarilar"]:
            lines.append(f"  {w}")
        lines.append("")

    # Senaryo — her hisse stop seviyesi ve uzaklık detaylı
    s = scenario
    lines.append(f"--- SENARYO: {s['senaryo']} ---")
    lines.append(
        f"  Toplam tahmini kayıp: ${s['tahmini_toplam_kayip']:,} "
        f"(-%{s['kayip_yuzde']})"
    )
    lines.append("  Stop tetiklenecek pozisyonlar:")
    stop_tetik_sayisi = 0
    for pf_name, pf_data in s["portfoyler"].items():
        for p in pf_data.get("pozisyonlar", []):
            if p.get("stop"):
                cur  = p.get("fiyat", 0)
                stop = p.get("stop_seviye", 0)
                uzak = p.get("stop_uzaklik_pct", 0)
                zarar = p.get("tahmini_zarar", 0)
                lines.append(
                    f"  ❌ [{pf_name[:3].upper()}] {p['sembol']:6} "
                    f"${cur:,.2f} → stop ${stop:,.2f} "
                    f"(%{uzak:.1f} uzakta | ${zarar:+,.0f})"
                )
                stop_tetik_sayisi += 1
    if stop_tetik_sayisi == 0:
        lines.append("  ✅ Hiçbir stop tetiklenmez")
    lines.append("")

    print("[Risk] Analiz tamamlandı.")
    return "\n".join(lines)
