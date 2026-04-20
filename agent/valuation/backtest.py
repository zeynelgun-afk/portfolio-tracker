"""
Finzora Valuation Framework v5 — Backtest Analyzer
=====================================================
Geçmiş v5 tahminlerini bugünkü fiyatlarla karşılaştırıp hit rate hesaplar.

Mantık:
  1. prediction_log'dan ≥N gün önce yapılan tahminleri al
  2. Her ticker için FMP'den bugünkü fiyatı al
  3. Başlangıç fiyatı → bugünkü fiyat getirisi hesapla
  4. Framework karar/upside ile gerçek performans karşılaştır

Başarı metriği:
  - "UCUZ" dedi + hisse %5+ yükseldi → HIT
  - "UCUZ" dedi + hisse %5+ düştü → MISS
  - "PAHALI" dedi + hisse %5+ düştü → HIT
  - "PAHALI" dedi + hisse %5+ yükseldi → MISS
  - "ADİL" → sinyal yok (NO_SIGNAL)
  - Aradaki bölge (±5% içinde) → NEUTRAL

(Eşikler HIT_THRESHOLD_PCT ve MISS_THRESHOLD_PCT ile ayarlanabilir.)

Archetype bazında, confidence bazında, karar bazında kırılım üretir.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# fmp_client için path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fmp_client import fmp_get
except ImportError:
    import requests
    FMP_KEY = os.environ.get("FMP_API_KEY", "")
    FMP_BASE = "https://financialmodelingprep.com/stable"

    def fmp_get(endpoint, params=None):
        p = (params or {}); p["apikey"] = FMP_KEY
        try:
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
            return r.json()
        except Exception:
            return None


from valuation.prediction_log import read_predictions


# Hit/miss eşikleri (performans yüzdesi)
HIT_THRESHOLD_PCT   = 5.0   # bu kadar doğru yönde hareket = HIT
MISS_THRESHOLD_PCT  = 5.0   # bu kadar yanlış yönde hareket = MISS


def _get_current_price(ticker: str) -> float:
    """Güncel fiyat."""
    q = fmp_get("quote", {"symbol": ticker}) or []
    if not q:
        return 0.0
    q = q[0] if isinstance(q, list) else q
    if not q or not isinstance(q, dict):
        return 0.0
    try:
        return float(q.get("price") or 0)
    except (ValueError, TypeError, AttributeError):
        return 0.0


def _classify_outcome(karar: str, realized_pct: float) -> str:
    """
    Framework kararı vs gerçek getiri → HIT/MISS/NEUTRAL.
    """
    is_bullish = karar in ("UCUZ", "ADİL-UCUZ", "UCUZ (düşük güven)")
    is_bearish = karar in ("PAHALI", "ADİL-PAHALI", "PAHALI (düşük güven)")

    if is_bullish:
        if realized_pct >= HIT_THRESHOLD_PCT:
            return "HIT"
        elif realized_pct <= -MISS_THRESHOLD_PCT:
            return "MISS"
        else:
            return "NEUTRAL"
    elif is_bearish:
        if realized_pct <= -HIT_THRESHOLD_PCT:
            return "HIT"
        elif realized_pct >= MISS_THRESHOLD_PCT:
            return "MISS"
        else:
            return "NEUTRAL"
    else:
        # ADİL, YETERSİZ
        return "NO_SIGNAL"


def analyze(min_age_days: int = 14, verbose: bool = False) -> dict:
    """
    Ana analiz fonksiyonu.

    Args:
        min_age_days: Tahmin en az bu kadar eski olmalı (volatilite ile beraber
                      anlamlı değerlendirme için). Default 14 gün.

    Returns:
        {
            "overall": {hit, miss, neutral, no_signal, hit_rate},
            "by_archetype": {archetype: {hit, miss, ...}},
            "by_confidence": {"high"/"med"/"low": {...}},
            "by_karar": {karar: {...}},
            "samples": [{ticker, karar, conf, realized_pct, outcome, ...}],
        }
    """
    # Tüm geçmiş tahminleri al (uzak geçmiş)
    all_preds = read_predictions(days_back=365)

    # Min_age filtresi
    cutoff = datetime.now() - timedelta(days=min_age_days)
    eligible = []
    for p in all_preds:
        try:
            ts = datetime.fromisoformat(p.get("timestamp", ""))
            if ts <= cutoff:
                eligible.append(p)
        except Exception:
            continue

    if not eligible:
        return {
            "error": f"{min_age_days}+ gün eski tahmin yok",
            "total_predictions": len(all_preds),
        }

    # Her kayıt ayrı bir test case (daha çok veri noktası).
    # Aynı ticker için 20 gün önce UCUZ, 10 gün önce UCUZ 2 ayrı sample.
    # Eğer sadece ticker başına 1 kayıt istenirse aşağıdaki "first_by_ticker"
    # yaklaşımı kullanılabilir — şu an her kayıt değerlendiriliyor.

    # Güncel fiyatları batch'le (ticker bazında dedup)
    unique_tickers = list({p.get("ticker") for p in eligible if p.get("ticker")})
    current_prices = {}
    for t in unique_tickers:
        current_prices[t] = _get_current_price(t)

    # Her kayıt için realized getiri
    samples = []
    for pred in eligible:
        ticker = pred.get("ticker")
        if not ticker:
            continue
        current = current_prices.get(ticker, 0)
        if current <= 0:
            if verbose:
                print(f"  [skip] {ticker}: fiyat alınamadı")
            continue

        start_price = pred.get("current_price") or 0
        if start_price <= 0:
            continue

        realized_pct = ((current / start_price) - 1.0) * 100
        outcome = _classify_outcome(pred.get("karar", ""), realized_pct)

        # Kayıt yaşını da ekle (analiz için faydalı)
        try:
            pred_ts = datetime.fromisoformat(pred.get("timestamp", ""))
            age_days = (datetime.now() - pred_ts).days
        except Exception:
            age_days = None

        samples.append({
            "ticker":         ticker,
            "pred_date":      pred.get("timestamp"),
            "age_days":       age_days,
            "archetype":      pred.get("archetype"),
            "karar":          pred.get("karar"),
            "upside_pred":    pred.get("upside_pct"),
            "confidence":     pred.get("confidence_score"),
            "analyst_gap":    pred.get("analyst_gap_pct"),
            "start_price":    start_price,
            "current_price":  current,
            "realized_pct":   round(realized_pct, 2),
            "outcome":        outcome,
        })

    if not samples:
        return {"error": "hiçbir örnek değerlendirilemedi"}

    # Overall
    totals = {"HIT": 0, "MISS": 0, "NEUTRAL": 0, "NO_SIGNAL": 0}
    for s in samples:
        totals[s["outcome"]] += 1
    signaled = totals["HIT"] + totals["MISS"]
    hit_rate = (totals["HIT"] / signaled * 100) if signaled else 0

    # Kırılımlar
    by_archetype = defaultdict(lambda: {"HIT": 0, "MISS": 0, "NEUTRAL": 0, "NO_SIGNAL": 0})
    by_confidence = defaultdict(lambda: {"HIT": 0, "MISS": 0, "NEUTRAL": 0, "NO_SIGNAL": 0})
    by_karar = defaultdict(lambda: {"HIT": 0, "MISS": 0, "NEUTRAL": 0, "NO_SIGNAL": 0})

    for s in samples:
        by_archetype[s["archetype"] or "unknown"][s["outcome"]] += 1
        conf = s.get("confidence") or 0
        conf_bucket = "high (≥75)" if conf >= 75 else "med (50-74)" if conf >= 50 else "low (<50)"
        by_confidence[conf_bucket][s["outcome"]] += 1
        by_karar[s["karar"] or "?"][s["outcome"]] += 1

    # Hit rate'leri ekle
    def _add_hit_rate(d):
        for k, v in d.items():
            signaled = v["HIT"] + v["MISS"]
            v["hit_rate"] = round(v["HIT"] / signaled * 100, 1) if signaled else None
            v["total"] = sum([v["HIT"], v["MISS"], v["NEUTRAL"], v["NO_SIGNAL"]])
        return d

    return {
        "min_age_days":       min_age_days,
        "analyzed":           datetime.now().isoformat(timespec="seconds"),
        "total_predictions":  len(all_preds),
        "eligible":           len(eligible),
        "unique_tickers":     len({s["ticker"] for s in samples}),
        "total_samples":      len(samples),
        "overall":            {**totals, "hit_rate_pct": round(hit_rate, 1)},
        "by_archetype":       _add_hit_rate(dict(by_archetype)),
        "by_confidence":      _add_hit_rate(dict(by_confidence)),
        "by_karar":           _add_hit_rate(dict(by_karar)),
        "samples":            sorted(samples, key=lambda x: -x["realized_pct"]),
    }


def format_report(result: dict) -> str:
    """Terminal için rapor."""
    if result.get("error"):
        return f"❌ {result['error']}"

    out = [
        "=" * 70,
        f"  VALUATION BACKTEST — ≥{result['min_age_days']}-gün eski tahminler",
        "=" * 70,
        f"  Toplam log kaydı:    {result['total_predictions']}",
        f"  Değerlendirilebilir: {result['eligible']} kayıt → {result.get('total_samples', result.get('unique_tickers', 0))} sample ({result['unique_tickers']} ticker)",
        "",
        "  GENEL:",
    ]
    o = result["overall"]
    out.append(f"    HIT:       {o['HIT']}")
    out.append(f"    MISS:      {o['MISS']}")
    out.append(f"    NEUTRAL:   {o['NEUTRAL']} (hareket eşiği altı)")
    out.append(f"    NO_SIGNAL: {o['NO_SIGNAL']} (ADİL kararları)")
    out.append(f"    HIT RATE:  {o['hit_rate_pct']}%")
    out.append("")
    out.append("  ARCHETYPE BAZINDA:")
    for a, v in sorted(result["by_archetype"].items(), key=lambda x: -(x[1].get("hit_rate") or 0)):
        hr = v["hit_rate"] if v["hit_rate"] is not None else "—"
        out.append(f"    {a:35} hit_rate={hr}% ({v['HIT']}H/{v['MISS']}M/{v['NEUTRAL']}N)  toplam={v['total']}")
    out.append("")
    out.append("  GÜVEN BAZINDA:")
    for c in ["high (≥75)", "med (50-74)", "low (<50)"]:
        if c not in result["by_confidence"]:
            continue
        v = result["by_confidence"][c]
        hr = v["hit_rate"] if v["hit_rate"] is not None else "—"
        out.append(f"    {c:15} hit_rate={hr}% ({v['HIT']}H/{v['MISS']}M)  toplam={v['total']}")
    out.append("")
    out.append("  EN İYİ / EN KÖTÜ (realized %):")
    for s in result["samples"][:3]:
        out.append(f"    ✓ {s['ticker']:6} {s['karar']:20} pred={s['upside_pred']:+.0f}% real={s['realized_pct']:+.1f}% [{s['outcome']}]")
    out.append("    ...")
    for s in result["samples"][-3:]:
        out.append(f"    ✗ {s['ticker']:6} {s['karar']:20} pred={s['upside_pred']:+.0f}% real={s['realized_pct']:+.1f}% [{s['outcome']}]")

    return "\n".join(out)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="v5 Valuation Backtest")
    ap.add_argument("--min-age", type=int, default=14,
                    help="Tahmin en az bu kadar gün eski olmalı (default 14)")
    ap.add_argument("--json", action="store_true", help="JSON çıktı")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    result = analyze(min_age_days=args.min_age, verbose=args.verbose)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_report(result))
