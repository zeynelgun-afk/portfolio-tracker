#!/usr/bin/env python3
"""
Finzora — Fırsat Bulucu
=========================
Makro temalardan → puanlanmış alım adayları üretir.

Her aday için:
  1. Teknik skor: RSI + SMA50/200 + momentum + ichimoku
  2. Fundamental skor: ROIC + P/E + FCF yield + EPS büyüme
  3. Tema uyumu: tema gücü × alt dal puanı
  4. K-engine filtresi: tüm giriş kuralları
  5. Final skor: teknik×0.4 + fundamental×0.35 + tema×0.25

Çıktı: data/buy_candidates.json (her sabah yenilenir)
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

FMP_KEY  = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"


def _fmp(endpoint, params=None):
    p = params or {}
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
        return r.json()
    except Exception:
        return None


def score_technical(symbol: str, price: float) -> tuple[float, dict]:
    """Teknik skor 0-10. Döndürür: (skor, detay)"""
    hist = _fmp(f"historical-price-eod/full", {"symbol": symbol, "limit": 210})
    if not hist or not isinstance(hist, list) or len(hist) < 50:
        return 0, {}

    closes  = [float(h["close"]) for h in hist]
    volumes = [float(h.get("volume",0)) for h in hist[:20]]

    sma50  = sum(closes[:50]) / 50
    sma200 = sum(closes[:200]) / 200 if len(closes) >= 200 else sma50

    # RSI-14
    gains  = [max(0, closes[i]-closes[i+1]) for i in range(14)]
    losses = [max(0, closes[i+1]-closes[i]) for i in range(14)]
    ag, al = sum(gains)/14, sum(losses)/14
    rsi    = 100-(100/(1+ag/al)) if al else 100

    # Momentum (1M, 3M)
    mom_1m = (closes[0]-closes[21])/closes[21]*100 if len(closes)>21 else 0
    mom_3m = (closes[0]-closes[63])/closes[63]*100 if len(closes)>63 else 0

    # Hacim
    avg_vol = sum(volumes[5:])/max(len(volumes[5:]),1)
    vol_ratio = volumes[0]/avg_vol if avg_vol else 1

    skor = 0
    detay = {}

    # SMA pozisyonu
    if price > sma200:
        skor += 2; detay["sma200"] = "✅"
    if price > sma50:
        skor += 1; detay["sma50"] = "✅"

    # RSI: 40-65 ideal giriş bölgesi
    if 40 <= rsi <= 65:
        skor += 2; detay["rsi"] = f"✅ {rsi:.0f}"
    elif 35 <= rsi < 40:
        skor += 1; detay["rsi"] = f"⚠️ {rsi:.0f}"
    elif rsi > 75:
        skor -= 1; detay["rsi"] = f"⚠️ aşırı alım {rsi:.0f}"

    # Momentum
    if mom_1m > 5:  skor += 2; detay["mom_1m"] = f"✅ +{mom_1m:.1f}%"
    elif mom_1m > 0: skor += 1
    if mom_3m > 15: skor += 1; detay["mom_3m"] = f"✅ +{mom_3m:.1f}%"

    # Hacim
    if vol_ratio > 1.5: skor += 1; detay["hacim"] = f"✅ {vol_ratio:.1f}x"

    detay["skor"] = min(10, max(0, skor))
    return min(10, max(0, skor)), detay


def score_fundamental(symbol: str) -> tuple[float, dict]:
    """Fundamental skor 0-10."""
    # Doğru format: ?symbol= query param (/symbol path param değil — 404 döner)
    ratios = _fmp("ratios-ttm", {"symbol": symbol}) or {}
    if isinstance(ratios, list):
        ratios = ratios[0] if ratios else {}

    metrics = _fmp("key-metrics-ttm", {"symbol": symbol}) or {}
    if isinstance(metrics, list):
        metrics = metrics[0] if metrics else {}

    # Doğru alan adları (FMP stable API)
    pe    = float(ratios.get("priceToEarningsRatioTTM") or 0)
    roic  = float(metrics.get("returnOnInvestedCapitalTTM") or 0) * 100
    fcf_y = float(metrics.get("freeCashFlowYieldTTM") or 0) * 100
    roe   = float(metrics.get("returnOnEquityTTM") or 0) * 100   # büyüme proxy

    skor = 0
    detay = {}

    # ROIC
    if roic > 20:   skor += 3; detay["roic"] = f"✅ {roic:.1f}%"
    elif roic > 12: skor += 2; detay["roic"] = f"✅ {roic:.1f}%"
    elif roic > 8:  skor += 1
    elif roic < 0:  skor -= 2; detay["roic"] = f"❌ {roic:.1f}%"

    # P/E
    if 0 < pe < 15:  skor += 2; detay["pe"] = f"✅ {pe:.1f}"
    elif 0 < pe < 25: skor += 1; detay["pe"] = f"→ {pe:.1f}"
    elif pe > 50 or pe < 0: skor -= 1; detay["pe"] = f"⚠️ {pe:.1f}"

    # FCF yield
    if fcf_y > 5: skor += 2; detay["fcf"] = f"✅ {fcf_y:.1f}%"
    elif fcf_y > 2: skor += 1

    # Büyüme
    if roe > 20: skor += 2; detay["büyüme"] = f"✅ ROE {roe:.1f}%"
    elif roe > 10: skor += 1

    detay["skor"] = min(10, max(0, skor))
    return min(10, max(0, skor)), detay


def find_candidates(
    tema_listesi: list,
    vix: float = 20.0,
    mevcut_pozisyonlar: list = None,
) -> list:
    """
    Tema listesinden puanlanmış alım adayları üretir.
    Döndürür: [{"symbol","score","portfolio","stop","target","reason",...}]
    """
    mevcut = set(mevcut_pozisyonlar or [])
    tüm_adaylar = {}

    for tema in tema_listesi:
        tema_adi  = tema.get("tema_adi", "")
        tema_skor = float(tema.get("güç_skoru", 5))
        _pf_alias = {"agresif":"aggressive","aggressive":"aggressive","büyüme":"aggressive",
                      "temettü":"dividend","temettu":"dividend","gelir":"dividend","dengeli":"balanced"}
        portföy = tema.get("portföy", "aggressive").lower()
        portföy = _pf_alias.get(portföy, portföy)
        if portföy not in ("aggressive","balanced","dividend"):
            portföy = "aggressive"  # fallback
        evren     = tema.get("hisse_evreni", tema.get("önerilen_hisseler", []))

        print(f"[Finder] {tema_adi} ({len(evren)} hisse)...")

        for sym in evren[:10]:  # Tema başına max 10 hisse
            if sym in tüm_adaylar:
                continue

            # Fiyat
            q = _fmp("quote", {"symbol": sym})
            if not q:
                continue
            q = q[0] if isinstance(q, list) else q
            price = float(q.get("price") or 0)
            if not price:
                continue

            time.sleep(0.1)

            # K-engine kontrolü
            try:
                from k_engine import run_entry_checks
                # tema_adi'nı sector proxy olarak geç (K-13 VIX matrisi için)
                _sector_proxy = tema_adi.replace("_", " ").title()
                k_res = run_entry_checks(sym, vix=vix, sector=_sector_proxy, base_size=5000, portfolio=portföy)
                if not k_res["go"]:
                    print(f"  ❌ {sym}: {k_res['fail_reason']}")
                    continue
            except Exception:
                k_res = {"go": True, "checks": {}, "position_size": 5000}

            # Teknik skor
            t_skor, t_det = score_technical(sym, price)
            if t_skor < 3:  # Minimum teknik eşik
                print(f"  ↓ {sym}: teknik zayıf ({t_skor}/10)")
                continue

            time.sleep(0.1)

            # Fundamental skor
            f_skor, f_det = score_fundamental(sym)

            # ATR14 + SMA50 bazlı stop (ortak helper) — kör %7 fallback yerine
            try:
                from execution_engine import compute_atr_stop as _cas_of
                stop, target, atr = _cas_of(sym, price)
            except Exception:
                stop   = round(price * 0.92, 2)
                target = round(price * 1.12, 2)
                atr    = None
            # compute_atr_stop FMP patlarsa atr=None dönüyor — None'a round() TypeError atar
            atr_display = round(atr, 2) if atr is not None else None
            rr     = round((target-price)/(price-stop), 2) if price > stop else 0

            if rr < 2:  # R:R minimum 2:1
                continue

            # Final skor (0-10 ölçekli, ağırlıklı ortalama)
            # t_skor, f_skor, tema_skor hepsi 0-10 — doğrudan ağırlıklı ortalama al.
            # Eski: (tema_skor/10)*10*0.25 = tema_skor*0.25 (pleonasm; normalize→denormalize)
            final = round(t_skor * 0.4 + f_skor * 0.35 + tema_skor * 0.25, 2)

            tüm_adaylar[sym] = {
                "symbol":      sym,
                "tema":        tema_adi,
                "portföy":     portföy,
                "price":       round(price, 2),
                "stop":        stop,
                "target":      target,
                "rr":          rr,
                "score":       final,
                "teknik":      t_skor,
                "fundamental": f_skor,
                "tema_güç":    tema_skor,
                "atr":         atr_display,
                "k_checks":    k_res.get("checks", {}),
                "reason":      f"{tema_adi} teması — teknik:{t_skor}/10 fundamental:{f_skor}/10",
                "detay":       {**t_det, **f_det},
            }
            print(f"  ✅ {sym}: skor {final:.1f} (T:{t_skor} F:{f_skor} R:R {rr}:1)")

    # Skora göre sırala
    sonuç = sorted(tüm_adaylar.values(), key=lambda x: -x["score"])

    # Kaydet
    out = {
        "tarih":    datetime.now().isoformat(),
        "vix":      vix,
        "adaylar":  sonuç,
        "özet":     {
            "toplam":     len(sonuç),
            "portföy_dağılım": {},
        }
    }
    for a in sonuç:
        pf = a["portföy"]
        out["özet"]["portföy_dağılım"][pf] = out["özet"]["portföy_dağılım"].get(pf,0)+1

    json.dump(out, open(REPO_ROOT/"data"/"buy_candidates.json","w"),
              ensure_ascii=False, indent=2)

    print(f"\n[Finder] {len(sonuç)} aday bulundu → data/buy_candidates.json")
    return sonuç
