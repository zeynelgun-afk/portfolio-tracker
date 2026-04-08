#!/usr/bin/env python3
"""
K-16: Sell the news riski değerlendirmesi
TRADING_PLAYBOOK.md K-16 kuralı uygulaması.

KAPSAM: SADECE portföy pozisyonları (Dengeli, Agresif, Temettü).
Swing trade için K-05 geçerli (earnings 2g öncesi tam çıkış).

5 maddelik skor:
1) Hisse kazanç öncesi 5 günde %5+ ralli
2) Consensus EPS son 3 ay %10+ yükseltilmiş
3) 52w zirveye %5 mesafe
4) Sektör son 1 ay %10+ ralli
5) Short interest %10+ float

Karar:
- 0-1: normal tut
- 2-3: %25 kısmi al + trailing sıkılaştır (K-11 aktif)
- 4-5: %50 kısmi çık, post-earnings bekle

Kullanım:
  python scripts/k16_sell_the_news_score.py SYMBOL
"""

import sys
import argparse
from datetime import datetime, timedelta
from k_rules_common import fmp_get, send_k_alert, get_sector, set_quiet_mode


def calc_score(symbol):
    score = 0
    details = []

    # 1) Son 5 gün ralli
    hist = fmp_get("historical-price-eod/full", {"symbol": symbol})
    if hist and isinstance(hist, list) and len(hist) >= 6:
        bars = hist
        today = bars[0]["close"]
        five_days = bars[5]["close"]
        pct_5d = ((today - five_days) / five_days) * 100
        if pct_5d >= 5:
            score += 1
            details.append(f"Son 5g ralli: %{pct_5d:.1f} (>%5)")
        else:
            details.append(f"Son 5g: %{pct_5d:.1f}")
    else:
        details.append("Historical: veri yok")

    # 2) Consensus EPS revizyonu (FMP analyst-estimates)
    estimates = fmp_get("analyst-estimates", {"symbol": symbol, "period": "quarter", "limit": 4})
    if estimates and isinstance(estimates, list) and len(estimates) >= 2:
        # En yakın dönem + 3 ay önceki estimate karşılaştırması zor — basitleştirme:
        # Mevcut estimate'i 3 ay öncekiyle kıyasla yerine, son 4 dönem ortalama trend kullan
        recent_eps = [e.get("estimatedEpsAvg", 0) for e in estimates[:2]]
        if len(recent_eps) >= 2 and recent_eps[1] != 0:
            change = ((recent_eps[0] - recent_eps[1]) / abs(recent_eps[1])) * 100
            if change >= 10:
                score += 1
                details.append(f"EPS estimate yükseliş: %{change:.1f}")
            else:
                details.append(f"EPS estimate: %{change:.1f}")
        else:
            details.append("EPS estimate: yetersiz veri")
    else:
        details.append("Analyst estimates: veri yok")

    # 3) 52w zirveye mesafe
    quote = fmp_get("quote", {"symbol": symbol})
    if quote and isinstance(quote, list) and quote:
        q = quote[0]
        current = q.get("price", 0)
        high_52w = q.get("yearHigh", current)
        if high_52w > 0:
            distance = ((high_52w - current) / high_52w) * 100
            if distance <= 5:
                score += 1
                details.append(f"52w zirveye %{distance:.1f} mesafe (<%5)")
            else:
                details.append(f"52w zirveye %{distance:.1f}")

    # 4) Sektör son 1 ay rallisi
    sector_etf = get_sector(symbol)
    if sector_etf and sector_etf != "UNKNOWN":
        sec_hist = fmp_get("historical-price-eod/full", {"symbol": sector_etf})
        if sec_hist and "historical" in sec_hist and len(sec_hist) >= 22:
            sec_bars = sec_hist
            sec_today = sec_bars[0]["close"]
            sec_month = sec_bars[21]["close"]
            sec_pct = ((sec_today - sec_month) / sec_month) * 100
            if sec_pct >= 10:
                score += 1
                details.append(f"Sektör {sector_etf} %{sec_pct:.1f} (>%10)")
            else:
                details.append(f"Sektör {sector_etf} %{sec_pct:.1f}")

    # 5) Short interest
    if quote and isinstance(quote, list) and quote:
        # FMP key-metrics shortFloat
        km = fmp_get("key-metrics-ttm", {"symbol": symbol})
        if km and isinstance(km, list) and km:
            short_ratio = km[0].get("shortRatio") or km[0].get("shortInterestPercent", 0) or 0
            if short_ratio > 10:
                score += 1
                details.append(f"Short interest %{short_ratio:.1f} (>%10)")
            else:
                details.append(f"Short interest %{short_ratio:.1f}")
        else:
            details.append("Short interest: veri yok")

    return score, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action="store_true", help="Info seviyeli bildirimleri de telegrama gönder (varsayılan: kapalı)")
    parser.add_argument("symbol")
    args = parser.parse_args()
    set_quiet_mode(not args.notify)

    symbol = args.symbol.upper()
    print(f"[K-16] {symbol} sell-the-news skor hesaplanıyor...")

    score, details = calc_score(symbol)

    print(f"\n[K-16] SKOR: {score}/5")
    for d in details:
        print(f"  • {d}")

    if score >= 4:
        decision = "Kazanç öncesi %50 kısmi çık, post-earnings bekle"
        severity = "critical"
    elif score >= 2:
        decision = "Kazanç öncesi %25 kısmi al + trailing sıkılaştır (K-11 aktif et)"
        severity = "warning"
    else:
        decision = "Normal tut, kazanç sonrası izle"
        severity = "info"

    print(f"\n[K-16] KARAR: {decision}")
    print(f"\n⚠️ NOT: K-16 SADECE portföy pozisyonları için. Swing'de K-05 geçerli (2g öncesi TAM çık).")

    msg = (f"{symbol} K-16 skor: {score}/5\n"
           f"{chr(10).join('• '+d for d in details)}\n"
           f"\nKARAR: {decision}\n"
           f"⚠️ Sadece portföy pozisyonları, swing K-05'e tabi")
    send_k_alert(f"K-16 SCORE:{score}", symbol, msg, severity=severity)


if __name__ == "__main__":
    main()
