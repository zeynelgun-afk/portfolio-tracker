#!/usr/bin/env python3
"""
Finzora Agent — Otomatik Conviction Scorer
============================================
Her hisse adayı için 0-100 güven puanı hesaplar.
Tamamen FMP API verisiyle — manuel hesaplama yok.

Skor bileşenleri:
  Teknik güç      (0-25): Ichimoku proxy + RSI + hacim + SMA
  Tema uyumu      (0-25): Tema puanı × katman ağırlığı
  Momentum        (0-20): RS20 + fiyat momentum + earnings revizyon
  Temel kalite    (0-15): FCF + borç + ROIC
  Risk faktörü    (0-15): K-15b skoru + earnings yakınlık + korelasyon
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

FMP_KEY  = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"
MEMORY_DIR = Path(__file__).parent / "memory"


def fmp(endpoint, params=None):
    p = (params or {}); p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── 1. TEKNİK GÜÇ (0-25) ─────────────────────────────────────────────────────

def score_technical(symbol: str) -> tuple[float, dict]:
    hist = fmp("historical-price-eod/full", {"symbol": symbol, "limit": 60})
    if not hist or not isinstance(hist, list) or len(hist) < 30:
        return 0, {"hata": "Yetersiz tarihsel veri"}

    closes  = [float(h["close"]) for h in hist]
    volumes = [float(h.get("volume", 0)) for h in hist]
    highs   = [float(h["high"]) for h in hist]
    lows    = [float(h["low"])  for h in hist]
    price   = closes[0]

    # SMA50 kontrolü
    sma50  = sum(closes[:50]) / 50 if len(closes) >= 50 else sum(closes) / len(closes)
    above_sma50 = price > sma50

    # RSI-14
    gains  = [max(0, closes[i] - closes[i+1]) for i in range(14)]
    losses = [max(0, closes[i+1] - closes[i]) for i in range(14)]
    ag = sum(gains)/14; al = sum(losses)/14
    rsi = 100 - (100 / (1 + ag/al)) if al > 0 else 100

    # Hacim oranı (son 5g / son 20g ortalama)
    vol_5  = sum(volumes[:5]) / 5  if volumes else 0
    vol_20 = sum(volumes[:20]) / 20 if len(volumes) >= 20 else vol_5
    vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 0

    # Ichimoku proxy: tenkan (9) > kijun (26)
    tenkan = (max(highs[:9]) + min(lows[:9])) / 2 if len(highs) >= 9 else price
    kijun  = (max(highs[:26]) + min(lows[:26])) / 2 if len(highs) >= 26 else price
    tk_bull = tenkan > kijun

    # Puanlama
    skor = 0
    if above_sma50:  skor += 8
    if 40 <= rsi <= 65: skor += 8
    elif 35 <= rsi < 40 or 65 < rsi <= 72: skor += 4
    if vol_ratio >= 1.5:  skor += 5
    elif vol_ratio >= 1.2: skor += 3
    if tk_bull: skor += 4

    return min(skor, 25), {
        "rsi": round(rsi, 1), "sma50_ustu": above_sma50,
        "vol_ratio": round(vol_ratio, 2), "tk_bull": tk_bull,
        "teknik_skor": skor
    }


# ── 2. TEMA UYUMU (0-25) ──────────────────────────────────────────────────────

TIER_WEIGHTS = {"tier_0": 25, "tier_1": 22, "tier_2": 15, "tier_3": 8}

def score_tema_uyumu(symbol: str, tema_puani: float, tier: str = "tier_1") -> tuple[float, dict]:
    """
    Tema puanı (0-70) × katman ağırlığı → normalize edilmiş 0-25 puan.
    Tema puanı ≤ 0 ise theme_scores.json'dan ORTALAMA puan kullanılır
    (eskiden max alınıyordu → her sembol aynı skoru alıyordu → sıralama bozuluyordu).
    """
    # Güncel tema puanı
    scores_path = REPO_ROOT / "data" / "theme_scores.json"
    if tema_puani <= 0 and scores_path.exists():
        try:
            with open(scores_path, encoding="utf-8") as f:
                data = json.load(f)
            puanlar = list(data.get("tema_puanlari", {}).values() or [])
            # Max yerine ortalama — her sembole sabit max atanmasını önler
            tema_puani = sum(puanlar) / len(puanlar) if puanlar else 0
        except Exception:
            tema_puani = 0

    # Normalize: 70 puan → max puan
    tema_normalized = min(tema_puani / 70, 1.0) if tema_puani > 0 else 0
    tier_weight     = TIER_WEIGHTS.get(tier, 15)

    skor = round(tema_normalized * (tier_weight / 25) * 25, 1)
    return min(skor, 25), {
        "tema_puani": tema_puani, "tier": tier,
        "tier_weight": tier_weight, "tema_skor": skor
    }


# ── 3. MOMENTUM (0-20) ────────────────────────────────────────────────────────

def score_momentum(symbol: str) -> tuple[float, dict]:
    # Fiyat değişimi (20g, 5g)
    change = fmp("stock-price-change", {"symbol": symbol})
    mom_20g = 0; mom_5g = 0
    if change and isinstance(change, list) and change:
        c = change[0]
        mom_20g = float(c.get("1M", 0))
        mom_5g  = float(c.get("5D", 0))

    # SPY ile RS20 (relative strength)
    spy_change = fmp("stock-price-change", {"symbol": "SPY"})
    spy_20g = 0
    if spy_change and isinstance(spy_change, list) and spy_change:
        spy_20g = float(spy_change[0].get("1M", 0))

    rs20 = mom_20g - spy_20g  # Sektör - SPY

    # Analyst estimates revisions
    estimates = fmp("analyst-estimates", {"symbol": symbol, "period": "quarter", "limit": 2})
    eps_revizyon = 0
    if estimates and isinstance(estimates, list) and len(estimates) >= 2:
        eps_new = float(estimates[0].get("estimatedEpsAvg", 0) or 0)
        eps_old = float(estimates[1].get("estimatedEpsAvg", 0) or 0)
        if eps_old and eps_old != 0:
            eps_revizyon = (eps_new - eps_old) / abs(eps_old) * 100

    # Puanlama
    skor = 0
    if rs20 > 5:  skor += 8
    elif rs20 > 2: skor += 5
    elif rs20 > 0: skor += 3
    elif rs20 < -3: skor -= 2

    if mom_5g > 3:  skor += 6
    elif mom_5g > 1: skor += 3

    if eps_revizyon > 5:  skor += 6
    elif eps_revizyon > 0: skor += 3

    return max(0, min(skor, 20)), {
        "mom_20g": round(mom_20g, 1), "rs20": round(rs20, 1),
        "mom_5g": round(mom_5g, 1), "eps_revizyon": round(eps_revizyon, 1),
        "momentum_skor": skor
    }


# ── 4. TEMEL KALİTE (0-15) ────────────────────────────────────────────────────

def score_fundamental(symbol: str) -> tuple[float, dict]:
    metrics = fmp("key-metrics-ttm", {"symbol": symbol})
    ratios  = fmp("ratios-ttm", {"symbol": symbol})

    skor   = 5  # Başlangıç nötr
    detay  = {}

    if metrics and isinstance(metrics, list) and metrics:
        m = metrics[0]
        roe  = float(m.get("returnOnEquityTTM", 0) or 0) * 100
        roic = float(m.get("returnOnInvestedCapitalTTM", 0) or 0) * 100
        fcf_yield = float(m.get("freeCashFlowYieldTTM", 0) or 0) * 100

        if roic > 15:  skor += 4
        elif roic > 8: skor += 2

        if fcf_yield > 4:  skor += 4
        elif fcf_yield > 2: skor += 2
        elif fcf_yield < 0: skor -= 3  # Negatif FCF

        detay = {"roe": round(roe,1), "roic": round(roic,1), "fcf_yield": round(fcf_yield,1)}

    if ratios and isinstance(ratios, list) and ratios:
        r = ratios[0]
        de = float(r.get("debtToEquityRatioTTM", 0) or 0)
        if de < 0.5:   skor += 2
        elif de > 1.5: skor -= 2
        detay["de_ratio"] = round(de, 2)

    return max(0, min(skor, 15)), {**detay, "temel_skor": skor}


# ── 5. RİSK FAKTÖRÜ (0-15) ───────────────────────────────────────────────────

def score_risk(symbol: str) -> tuple[float, dict]:
    """Düşük risk → yüksek puan. Yüksek risk → düşük puan."""
    skor = 10  # Başlangıç: nötr
    detay = {}

    # K-15b: FCF negatif mi?
    cf = fmp("cash-flow-statement", {"symbol": symbol, "period": "quarter", "limit": 4})
    if cf and isinstance(cf, list) and cf:
        fcf_values = [float(q.get("freeCashFlow", 0) or 0) for q in cf]
        neg_fcf_count = sum(1 for f in fcf_values if f < 0)
        if neg_fcf_count >= 3: skor -= 5  # Çoğunlukla negatif FCF
        elif neg_fcf_count >= 2: skor -= 2
        detay["neg_fcf_quarters"] = neg_fcf_count

    # Earnings yakınlığı — k_engine K-05 ile uyumlu (2 iş günü içinde = NO-GO)
    # 8 gün penceresi k_engine ile çakışıyordu: k_engine pozisyonu reddediyor,
    # conviction aynı sembol için hâlâ -4 puan veriyor → çifte ceza.
    # Şimdi: 2 gün içinde earnings varsa -4, 3-7 gün arası -1 (hafif).
    today = datetime.now()
    earn_cal = fmp("earnings-calendar", {
        "from": today.strftime("%Y-%m-%d"),
        "to": (today + timedelta(days=8)).strftime("%Y-%m-%d")
    })
    if earn_cal and isinstance(earn_cal, list):
        sym_earnings = [e for e in earn_cal if e.get("symbol") == symbol]
        if sym_earnings:
            try:
                e_date = datetime.strptime(sym_earnings[0].get("date", ""), "%Y-%m-%d")
                delta = (e_date - today).days
                if 0 <= delta <= 2:
                    skor -= 4       # k_engine zaten NO-GO verecek, bu yedek ceza
                    detay["yakın_earnings"] = f"{sym_earnings[0].get('date','?')} ({delta}g, K-05 NO-GO)"
                elif 3 <= delta <= 7:
                    skor -= 1       # Hafif ceza — giriş yasak değil ama risk
                    detay["yakın_earnings"] = f"{sym_earnings[0].get('date','?')} ({delta}g)"
            except ValueError:
                pass

    # Beta yüksekliği
    profile = fmp("profile", {"symbol": symbol})
    if profile and isinstance(profile, list) and profile:
        beta = float(profile[0].get("beta", 1.0) or 1.0)
        if beta > 2.0:  skor -= 3
        elif beta > 1.5: skor -= 1
        elif beta < 0.8: skor += 2
        detay["beta"] = round(beta, 2)

    return max(0, min(skor, 15)), {**detay, "risk_skor": skor}


# ── ANA FONKSIYON ─────────────────────────────────────────────────────────────

def calculate_conviction(
    symbol: str,
    tema_puani: float = 0,
    tier: str = "tier_1"
) -> dict:
    """
    Tek hisse için tam conviction hesabı.
    Tüm FMP verileri çekilir, 0-100 toplam skor hesaplanır.
    """
    print(f"[ConvictionScorer] {symbol} hesaplanıyor...")

    t_skor, t_det = score_technical(symbol);  time.sleep(0.15)
    m_skor, m_det = score_tema_uyumu(symbol, tema_puani, tier)
    mo_skor, mo_det = score_momentum(symbol); time.sleep(0.15)
    f_skor, f_det = score_fundamental(symbol); time.sleep(0.15)
    r_skor, r_det = score_risk(symbol);        time.sleep(0.15)

    toplam = t_skor + m_skor + mo_skor + f_skor + r_skor

    karar = (
        "GÜÇLÜ — Tam pozisyon"   if toplam >= 80 else
        "İYİ — Yarım-tam pozisyon" if toplam >= 60 else
        "ZAYIF — Sadece Temettü"  if toplam >= 40 else
        "GEÇ"
    )

    result = {
        "sembol":   symbol,
        "tarih":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "skor":     round(toplam, 1),
        "karar":    karar,
        "bilesenler": {
            "teknik":   {"puan": round(t_skor,1),  "max": 25, "detay": t_det},
            "tema":     {"puan": round(m_skor,1),  "max": 25, "detay": m_det},
            "momentum": {"puan": round(mo_skor,1), "max": 20, "detay": mo_det},
            "temel":    {"puan": round(f_skor,1),  "max": 15, "detay": f_det},
            "risk":     {"puan": round(r_skor,1),  "max": 15, "detay": r_det},
        }
    }

    print(f"[ConvictionScorer] {symbol}: {toplam:.0f}/100 — {karar}")
    return result


def batch_score(symbols: list, tema_puani: float = 50, tier: str = "tier_1") -> list:
    """Birden fazla hisse için toplu conviction hesabı."""
    results = []
    for sym in symbols:
        try:
            r = calculate_conviction(sym, tema_puani, tier)
            results.append(r)
        except Exception as e:
            print(f"[ConvictionScorer] {sym} hata: {e}")
        time.sleep(0.3)

    results.sort(key=lambda x: x["skor"], reverse=True)

    # Sonucu kaydet
    out_path = REPO_ROOT / "data" / "conviction_scores.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tema_puani": tema_puani,
            "sonuclar": results
        }, f, ensure_ascii=False, indent=2)

    return results


if __name__ == "__main__":
    import sys
    syms = sys.argv[1:] if len(sys.argv) > 1 else ["NVDA", "LMT", "XOM"]
    results = batch_score(syms)
    print("\n=== CONVİCTİON SKORLARI ===")
    for r in results:
        print(f"  {r['sembol']:6s}: {r['skor']:5.1f}/100 — {r['karar']}")
