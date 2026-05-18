#!/usr/bin/env python3
"""
Finzora — Pre-market Gap Scanner
===================================
Piyasa açılmadan önce (TR 16:00-16:30 arası) çalışır.
Gap up + haber + hacim üçlüsünü tespit eder.

Gap türleri:
  Continuation Gap : Trend yönünde gap → tüm pozisyon giriş
  Exhaustion Gap   : Aşırı hareket sonrası gap → dikkat, reversal yakın
  Breakout Gap     : Konsolidasyondan çıkış → güçlü sinyal
  Common Gap       : Anlamsız, genellikle doldurulur → giriş yok

Veri kaynakları (ücretsiz):
  - FMP premarket: batch-quote (aftermarket ve premarket fiyat bilgisi)
  - Yahoo Finance: Pre-market fiyat (yfinance)
  - Web araştırma: Haber teyidi
"""

import os
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
FMP_BASE  = "https://financialmodelingprep.com/stable"
FMP_KEY   = os.environ.get("FMP_API_KEY", "")


def get_premarket_quotes(symbols: list[str]) -> dict:
    """
    FMP'den premarket fiyatları çeker.
    aftermarket-quote endpoint'i premarket de döndürür.
    """
    if not symbols:
        return {}

    results = {}
    batch_size = 30

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        try:
            # Önce normal batch-quote dene
            r = requests.get(
                f"{FMP_BASE}/batch-quote",
                params={"symbols": ",".join(batch), "apikey": FMP_KEY},
                timeout=10
            ).json()

            for q in r:
                sym          = q.get("symbol", "")
                price        = q.get("price", 0)
                prev_close   = q.get("previousClose", 0)
                pre_price    = q.get("preMarketPrice") or q.get("postMarketPrice") or 0

                if not price or not prev_close:
                    continue

                # Pre-market fiyat varsa kullan, yoksa normal fiyat
                ref_price = pre_price if pre_price else price
                gap_pct   = ((ref_price - prev_close) / prev_close * 100) if prev_close else 0

                results[sym] = {
                    "price":      price,
                    "prev_close": prev_close,
                    "pre_price":  ref_price,
                    "gap_pct":    round(gap_pct, 2),
                    "year_high":  q.get("yearHigh", 0),
                    "year_low":   q.get("yearLow", 0),
                    "volume":     q.get("volume", 0),
                    "avg_volume": q.get("avgVolume", 0),
                }
        except Exception as e:
            print(f"  ⚠ FMP batch hatası: {e}")

    return results


def classify_gap(gap_pct: float, trend_dir: str, context: str = "") -> dict:
    """
    Gap türünü sınıflandır.
    trend_dir: "UP" veya "DOWN" (son 20 günlük trend)
    """
    abs_gap = abs(gap_pct)

    if abs_gap < 1.5:
        return {"tip": "common", "aksiyon": "GEÇ", "aciklama": "Küçük gap, anlamsız"}

    # Büyük gap (>%8) — Exhaustion riski
    if abs_gap > 8:
        tip = "exhaustion" if gap_pct > 0 and trend_dir == "UP" else "breakout"
        return {
            "tip": tip,
            "aksiyon": "DİKKAT" if tip == "exhaustion" else "İZLE",
            "aciklama": f"%{abs_gap:.1f} gap — {tip}. {'Reversal riski var' if tip=='exhaustion' else 'Güçlü breakout'}",
        }

    # Normal gap
    if gap_pct > 0:
        if trend_dir == "UP":
            return {
                "tip":     "continuation",
                "aksiyon": "OLASI_GİRİŞ",
                "aciklama": f"%{gap_pct:.1f} yukarı gap, trend devamı. Piyasa açılışında teyit et.",
            }
        else:
            return {
                "tip":     "reversal_gap",
                "aksiyon": "İZLE",
                "aciklama": f"%{gap_pct:.1f} yukarı gap, aşağı trend tersine dönüyor olabilir.",
            }
    else:
        return {
            "tip":     "down_gap",
            "aksiyon": "SAT_KONTROL",
            "aciklama": f"%{gap_pct:.1f} aşağı gap. Aktif pozisyon varsa stop kontrol et.",
        }


def scan_premarket_gaps(
    symbols: list[str] = None,
    min_gap_pct: float = 2.5,
    include_watchlist: bool = True,
) -> list[dict]:
    """
    Pre-market gap taraması.
    
    Args:
        symbols: Taranacak semboller (None → watchlist + aktif pozisyonlar)
        min_gap_pct: Minimum gap büyüklüğü
        include_watchlist: Watchlist'i dahil et
    """
    # Sembol listesini oluştur
    tarama_syms = set(symbols or [])

    if include_watchlist:
        wl_path = REPO_ROOT / "data" / "watchlist.json"
        if wl_path.exists():
            wl = json.load(open(wl_path))
            tarama_syms.update(h.get("sembol", "") for h in wl.get("izleme_listesi", []))

    # Aktif swing pozisyonları
    active_path = REPO_ROOT / "data" / "swing" / "active.json"
    if active_path.exists():
        active = json.load(open(active_path))
        for p in active.get("aktif_pozisyonlar", []):
            tarama_syms.add(p.get("sembol", ""))

    # Portföy pozisyonları
    for pf in ["aggressive", "balanced", "dividend"]:
        pf_path = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if pf_path.exists():
            pf_data = json.load(open(pf_path))
            for p in pf_data.get("pozisyonlar", []):
                tarama_syms.add(p.get("sembol", ""))

    tarama_syms = [s for s in tarama_syms if s and len(s) <= 5]
    print(f"[PreMarket] {len(tarama_syms)} hisse taranıyor...")

    # Fiyatları çek
    quotes = get_premarket_quotes(tarama_syms)

    # Trend bilgisi için basit hesap (son 20 günlük)
    trend_cache = {}

    gaps = []
    for sym, q in quotes.items():
        gap_pct = q["gap_pct"]

        if abs(gap_pct) < min_gap_pct:
            continue

        # 20 günlük trend
        if sym not in trend_cache:
            try:
                hist = requests.get(
                    f"{FMP_BASE}/historical-price-eod/full",
                    params={"symbol": sym, "limit": 22, "apikey": FMP_KEY},
                    timeout=8
                ).json()
                if isinstance(hist, list) and len(hist) >= 20:
                    closes = [d["close"] for d in hist[:20]]
                    trend_cache[sym] = "UP" if closes[0] > closes[-1] else "DOWN"
                else:
                    trend_cache[sym] = "UNKNOWN"
            except Exception:
                trend_cache[sym] = "UNKNOWN"

        trend   = trend_cache.get(sym, "UNKNOWN")
        gap_cls = classify_gap(gap_pct, trend)

        # Hacim kontrolü
        vol_ratio = (q["volume"] / q["avg_volume"]) if q.get("avg_volume") else 0

        gap_entry = {
            "symbol":     sym,
            "gap_pct":    gap_pct,
            "pre_price":  q["pre_price"],
            "prev_close": q["prev_close"],
            "gap_type":   gap_cls["tip"],
            "action":     gap_cls["aksiyon"],
            "description":gap_cls["aciklama"],
            "trend":      trend,
            "vol_ratio":  round(vol_ratio, 2),
            "high_volume":vol_ratio >= 1.5,
        }

        gaps.append(gap_entry)

    # Büyükten küçüğe sırala
    gaps.sort(key=lambda x: -abs(x["gap_pct"]))

    # Kaydet
    output = {
        "date":   datetime.now().isoformat(),
        "total":  len(gaps),
        "gaps":   gaps,
    }
    out_path = REPO_ROOT / "data" / "premarket_gaps.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[PreMarket] {len(gaps)} gap tespit edildi (min %{min_gap_pct})")
    return gaps


def format_gaps_for_telegram(gaps: list[dict]) -> str:
    """Telegram için gap özeti."""
    if not gaps:
        return "📊 Pre-market: Önemli gap yok (<%2.5)"

    lines = [f"📊 Pre-market Gap Taraması\n"]

    yukarı = [g for g in gaps if g["gap_pct"] > 0]
    asagi  = [g for g in gaps if g["gap_pct"] < 0]

    if yukarı:
        lines.append("🟢 Yukarı Gap:")
        for g in yukarı[:5]:
            # Shim: hem yeni "high_volume" hem eski "yüksek_hacim"
            high_vol = g.get("high_volume", g.get("yüksek_hacim", False))
            action = g.get("action") or g.get("aksiyon", "")
            desc = g.get("description") or g.get("aciklama", "")
            hacim_tag = " 📊VOL" if high_vol else ""
            lines.append(
                f"  {g['symbol']:6} {g['gap_pct']:+.1f}% "
                f"→ ${g['pre_price']:.2f} | {action}{hacim_tag}"
            )
            lines.append(f"     {desc[:70]}")

    if asagi:
        lines.append("\n🔴 Aşağı Gap:")
        for g in asagi[:3]:
            action = g.get("action") or g.get("aksiyon", "")
            lines.append(
                f"  {g['symbol']:6} {g['gap_pct']:+.1f}% "
                f"→ ${g['pre_price']:.2f} | {action}"
            )

    return "\n".join(lines)


def get_premarket_context() -> str:
    """Sabah analizine eklenecek pre-market özeti."""
    path = REPO_ROOT / "data" / "premarket_gaps.json"
    if not path.exists():
        return ""

    data = json.load(open(path))
    # Shim: hem yeni hem eski top-level keyler
    tarih = (data.get("date") or data.get("tarih", ""))[:16]
    gaplar = data.get("gaps") or data.get("gaplar", [])

    if not gaplar:
        return f"Pre-market ({tarih}): Gap yok"

    lines = [f"PRE-MARKET GAPLAR ({tarih}):"]
    for g in gaplar[:5]:
        action = g.get("action") or g.get("aksiyon", "")
        desc = g.get("description") or g.get("aciklama", "")
        lines.append(
            f"  {g['symbol']:6} {g['gap_pct']:+.1f}% | "
            f"{action} | {desc[:50]}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pre-market Gap Scanner")
    parser.add_argument("--symbols", default="",
                        help="Virgülle ayrılmış semboller")
    parser.add_argument("--min-gap", type=float, default=2.5)
    args = parser.parse_args()

    extra_syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    gaps = scan_premarket_gaps(extra_syms, min_gap_pct=args.min_gap)

    print(format_gaps_for_telegram(gaps))
