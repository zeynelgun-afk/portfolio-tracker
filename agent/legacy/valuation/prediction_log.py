"""
Finzora Valuation Framework v5 — Prediction Log
=================================================
Her v5 valuate() çağrısı burada kaydedilir, gelecekte backtest için.

Kayıt mantığı: JSONL (append-only), her satır bir valuation snapshot.
Ileride 3/6/12 ay sonra aynı ticker için tekrar bakılırsa, mevcut
fiyatla karşılaştırılıp framework'ün doğruluk oranı hesaplanır.

Schema per line:
{
  "timestamp": "2026-04-19T21:30:00",
  "ticker": "NVDA",
  "archetype": "hyper_growth_semi",
  "archetype_confidence": 0.90,
  "current_price": 201.68,
  "fair_value": 334.61,
  "upside_pct": 65.9,
  "karar": "UCUZ",
  "confidence_score": 78,
  "analyst_consensus": 277.82,
  "analyst_gap_pct": 20.4,
  "market_regime": "BOGA",
  "regime_multiplier": 1.12,
  "method_count": 5,
  "excluded_count": 4,
  "outlier_count": 1,
  "red_flags": ["large_deviation_from_market", "1_outliers_removed"],
  "red_flag_count": 2
}

Dosya: logs/valuation_predictions.jsonl (git-tracked)
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime


LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "valuation_predictions.jsonl"


def log_valuation(result: dict) -> None:
    """
    v5 valuate() sonucunu JSONL'e ekle.
    Hata durumunda sessizce geçer (log sistemi ana akışı bloklamasın).
    
    Railway ortamında (ephemeral filesystem) log yazılmaz — dosya
    restart'ta kaybolur ve git'e commit edilemez. Sadece GitHub
    Actions workflow'lari ve yerel kullanim icin anlamli.
    """
    if not result or result.get("error"):
        return

    # Railway ephemeral fs — log yazma (restart'ta kaybolur)
    if os.environ.get("RAILWAY") or os.environ.get("RAILWAY_ENVIRONMENT"):
        return

    try:
        fv = result.get("fair_value", {})
        cls = result.get("classification", {})
        conf = result.get("confidence", {})
        regime = result.get("market_regime") or {}
        analyst = result.get("analyst_consensus") or {}

        entry = {
            "timestamp":             datetime.now().isoformat(timespec="seconds"),
            "ticker":                result.get("ticker"),
            "framework_version":     result.get("framework_version", "v5"),
            "archetype":             cls.get("archetype"),
            "archetype_confidence":  cls.get("confidence"),
            "current_price":         fv.get("current_price"),
            "fair_value":            fv.get("point"),
            "range_low":             fv.get("range_low"),
            "range_high":            fv.get("range_high"),
            "upside_pct":            fv.get("upside_pct"),
            "karar":                 fv.get("karar"),
            "confidence_score":      conf.get("score"),
            "analyst_consensus":     analyst.get("consensus"),
            "analyst_gap_pct":       analyst.get("framework_gap_pct"),
            "market_regime":         regime.get("rejim"),
            "regime_multiplier":     regime.get("multiplier"),
            "method_count":          len(result.get("methods_used", [])),
            "excluded_count":        len(result.get("methods_excluded", [])),
            "outlier_count":         len(result.get("methods_outliers", [])),
            "red_flag_count":        len(conf.get("red_flags", [])),
        }

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Logging hatasi kritik degil — sessizce gec
        if os.environ.get("VALUATION_LOG_DEBUG"):
            print(f"[valuation log] hata: {e}")


def read_predictions(ticker: str | None = None, days_back: int = 30) -> list[dict]:
    """
    Eski prediction'ları oku. ticker=None ise hepsi.
    days_back: son N gün.
    """
    if not LOG_FILE.exists():
        return []

    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days_back)

    out = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                    ts = datetime.fromisoformat(e.get("timestamp", ""))
                    if ts < cutoff:
                        continue
                    if ticker and e.get("ticker") != ticker.upper():
                        continue
                    out.append(e)
                except Exception:
                    continue
    except Exception:
        return []

    return out


def summary_stats(days_back: int = 30) -> dict:
    """
    Özet istatistikler: kaç ticker, archetype dağılımı, ortalama güven, vs.
    """
    preds = read_predictions(days_back=days_back)
    if not preds:
        return {"total": 0}

    archetypes = {}
    kararlar = {}
    confs = []
    for p in preds:
        a = p.get("archetype", "unknown")
        archetypes[a] = archetypes.get(a, 0) + 1
        k = p.get("karar", "?")
        kararlar[k] = kararlar.get(k, 0) + 1
        if p.get("confidence_score"):
            confs.append(p["confidence_score"])

    return {
        "total":            len(preds),
        "unique_tickers":   len({p.get("ticker") for p in preds}),
        "archetypes":       archetypes,
        "kararlar":         kararlar,
        "avg_confidence":   round(sum(confs) / len(confs), 1) if confs else None,
        "date_range":       f"{preds[0].get('timestamp')} → {preds[-1].get('timestamp')}",
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        import pprint
        pprint.pprint(summary_stats(days_back=30))
    else:
        preds = read_predictions(days_back=30)
        print(f"Toplam prediction: {len(preds)}")
        if preds:
            print(f"İlk: {preds[0].get('timestamp')} — {preds[0].get('ticker')}")
            print(f"Son: {preds[-1].get('timestamp')} — {preds[-1].get('ticker')}")
