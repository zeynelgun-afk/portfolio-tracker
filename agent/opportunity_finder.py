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

    closes  = [float(h.get("close") or 0) for h in hist]
    volumes = [float(h.get("volume") or 0) for h in hist[:20]]
    
    # Tüm close'lar 0 ise bozuk veri → skip
    if not any(c > 0 for c in closes[:50]):
        return 0, {}

    sma50  = sum(closes[:50]) / 50
    sma200 = sum(closes[:200]) / 200 if len(closes) >= 200 else sma50

    # RSI-14
    gains  = [max(0, closes[i]-closes[i+1]) for i in range(14)]
    losses = [max(0, closes[i+1]-closes[i]) for i in range(14)]
    ag, al = sum(gains)/14, sum(losses)/14
    rsi    = 100-(100/(1+ag/al)) if al else 100

    # Momentum (1M, 3M) — bozuk veriden kaçınmak için 0-check
    mom_1m = ((closes[0]-closes[21])/closes[21]*100) if len(closes)>21 and closes[21]>0 else 0
    mom_3m = ((closes[0]-closes[63])/closes[63]*100) if len(closes)>63 and closes[63]>0 else 0

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


def _score_valuation(symbol: str) -> tuple[float, dict]:
    """
    v5 framework fair value sonucunu 0-10 skora çevirir.
    
    Skor mantığı:
      UCUZ + yüksek güven (≥75) + analyst aligned  → 9-10
      UCUZ + güven ≥60                              → 7-8
      ADİL-UCUZ                                     → 6
      ADİL                                          → 5
      ADİL-PAHALI                                   → 3-4
      PAHALI                                        → 1-2
      PAHALI + yüksek güven                         → 0
    
    Veri yoksa 5.0 (neutral) döner. analyst_gap büyükse sınır skor uygulanır.
    """
    try:
        import sys as _s
        from pathlib import Path as _P
        agent_dir = str(_P(__file__).parent)
        if agent_dir not in _s.path:
            _s.path.insert(0, agent_dir)
        from valuation.framework import valuate
        r = valuate(symbol, verbose=False)
        if not r or r.get("error"):
            return 5.0, {"val": "veri yok"}
    except Exception:
        return 5.0, {"val": "hata"}

    fv = r["fair_value"]
    conf = r["confidence"]["score"]
    fark = fv["upside_pct"]
    karar = fv["karar"]
    ac = r.get("analyst_consensus") or {}
    has_analyst = bool(ac.get("consensus", 0) > 0)
    analyst_gap = abs(ac.get("framework_gap_pct") or 0)

    # Temel skor
    if fark > 25:      base = 9.5
    elif fark > 15:    base = 8.5
    elif fark > 8:     base = 7.5
    elif fark > 3:     base = 6.0
    elif fark > -3:    base = 5.0
    elif fark > -8:    base = 4.0
    elif fark > -15:   base = 3.0
    elif fark > -25:   base = 2.0
    else:              base = 1.0

    # Güven ayarı: neutral'a doğru çek
    if conf < 50:
        base = 5.0 + (base - 5.0) * 0.3
    elif conf < 70:
        base = 5.0 + (base - 5.0) * 0.6

    # Analyst verisi varsa gap büyükse neutral'a doğru çek
    if has_analyst:
        if analyst_gap > 40:
            base = 5.0 + (base - 5.0) * 0.3
        elif analyst_gap > 25:
            base = 5.0 + (base - 5.0) * 0.6
    else:
        # Analyst consensus yok → daha az iddialı
        # Framework tek başına, backup doğrulama yok → neutral'a %20 çek
        base = 5.0 + (base - 5.0) * 0.8

    skor = round(max(0, min(10, base)), 1)
    archetype = r["classification"]["archetype"]
    detay = {
        "val_karar":     karar,
        "val_fark":      f"{fark:+.1f}%",
        "val_guven":     conf,
        "val_archetype": archetype,
        "val_gap":       f"{ac.get('framework_gap_pct', 0):+.0f}%",
        "val_skor":      skor,
    }
    return skor, detay


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
        try:
            tema_skor = float(tema.get("güç_skoru", 5))
        except (ValueError, TypeError):
            tema_skor = 5.0  # Geçersiz skor → orta varsayılan
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

            # v5 valuation sinyali (0-10 ölçekli, analyst consensus ile doğrulanmış)
            val_skor, val_det = _score_valuation(sym)

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
            # Ağırlıklar: teknik %35 + fundamental %25 + tema %20 + valuation %20
            # Valuation yoksa 5.0 neutral kullanılır (val_skor 0 ise), ağırlık yine %20 kalır.
            _val = val_skor if val_skor > 0 else 5.0
            final = round(t_skor * 0.35 + f_skor * 0.25 + tema_skor * 0.20 + _val * 0.20, 2)

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
                "valuation":   val_skor,  # 0-10
                "atr":         atr_display,
                "k_checks":    k_res.get("checks", {}),
                "reason":      f"{tema_adi} teması — teknik:{t_skor}/10 fundamental:{f_skor}/10 valuation:{val_skor:.1f}/10",
                "detay":       {**t_det, **f_det, **val_det},
            }
            print(f"  ✅ {sym}: skor {final:.1f} (T:{t_skor} F:{f_skor} V:{val_skor:.1f} R:R {rr}:1)")

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
