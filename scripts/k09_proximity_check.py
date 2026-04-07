#!/usr/bin/env python3
"""
K-09: Stop yakınlığı erken çıkış protokolü
TRADING_PLAYBOOK.md K-09 kuralı uygulaması.

Her açık pozisyon için stop'a mesafeyi hesaplar. Mesafe ≤%2 ise 4 kontrol uygular:
1) RSI yönü düşüyor + 40 altı → negatif
2) Hacim profili: satış > alış → negatif
3) SPY günlük negatif + VIX yükseliyor → negatif
4) Sektör ETF günlük negatif → negatif

Karar:
- 3+ negatif → stop beklemeden ÇIK alert
- 2 negatif → stop'u bekle
- 0-1 negatif + toparlanma → tut (kuvvetli)
- 0-1 negatif + sinyal yok → tut (zayıf)

Kullanım:
  python scripts/k09_proximity_check.py            # tüm aktif pozisyonlar + swing
  python scripts/k09_proximity_check.py --symbol AAPL  # tek hisse
"""

import sys
import argparse
from k_rules_common import (
    fmp_get, get_all_positions, get_swing_active, send_k_alert, get_sector, set_quiet_mode
)


def get_quote(symbol):
    """FMP batch-quote ile güncel fiyat ve değişim."""
    data = fmp_get("quote", {"symbol": symbol})
    if data and isinstance(data, list) and data:
        return data[0]
    return None


def get_rsi(symbol, period=14):
    """RSI 14g, son 2 değer (yön için)."""
    data = fmp_get("technical-indicators/rsi", {
        "symbol": symbol, "periodLength": period, "timeframe": "1day"
    })
    if data and isinstance(data, list) and len(data) >= 2:
        return {"current": data[0].get("rsi"), "previous": data[1].get("rsi")}
    return None


def evaluate_position(symbol, stop_loss, current_price):
    """Stop'a mesafe ve 4 kontrol değerlendirmesi."""
    if not stop_loss or not current_price:
        return None

    distance_pct = ((current_price - stop_loss) / current_price) * 100
    if distance_pct > 2.0 or distance_pct < 0:
        return {"distance_pct": distance_pct, "action": "no_check", "negatives": 0}

    negatives = 0
    details = []

    # 1) RSI yönü
    rsi = get_rsi(symbol)
    if rsi and rsi["current"] and rsi["previous"]:
        if rsi["current"] < 40 and rsi["current"] < rsi["previous"]:
            negatives += 1
            details.append(f"RSI {rsi['current']:.1f} düşüyor")
        else:
            details.append(f"RSI {rsi['current']:.1f} OK")

    # 2) Hacim profili (basitleştirilmiş: bugünkü hacim 20g ortalamadan yüksek + fiyat düşüş)
    quote = get_quote(symbol)
    if quote:
        volume = quote.get("volume", 0)
        avg_volume = quote.get("avgVolume", 1)
        change_pct = quote.get("changesPercentage", 0)
        if volume > avg_volume * 1.2 and change_pct < 0:
            negatives += 1
            details.append(f"Yüksek hacim + düşüş ({volume/avg_volume:.1f}x)")

    # 3) SPY günlük + VIX
    spy = get_quote("SPY")
    vixy = get_quote("VIXY")
    if spy and vixy:
        spy_neg = spy.get("changesPercentage", 0) < 0
        vix_pos = vixy.get("changesPercentage", 0) > 0
        if spy_neg and vix_pos:
            negatives += 1
            details.append(f"SPY {spy.get('changesPercentage'):.2f}% + VIX yükseliyor")

    # 4) Sektör ETF
    sector_etf = get_sector(symbol)
    if sector_etf and sector_etf != "UNKNOWN":
        sector_quote = get_quote(sector_etf)
        if sector_quote and sector_quote.get("changesPercentage", 0) < 0:
            negatives += 1
            details.append(f"Sektör {sector_etf} {sector_quote.get('changesPercentage'):.2f}%")

    # Karar
    if negatives >= 3:
        action = "EXIT_NOW"
    elif negatives == 2:
        action = "WAIT_STOP"
    else:
        action = "HOLD"

    return {
        "symbol": symbol,
        "distance_pct": distance_pct,
        "negatives": negatives,
        "details": details,
        "action": action,
        "stop_loss": stop_loss,
        "current_price": current_price,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", help="Tek hisse kontrolü")
    parser.add_argument("--quiet", action="store_true", help="Sadece uyarı verirse yazdır")
    args = parser.parse_args()
    set_quiet_mode(getattr(args, "quiet", False))

    positions = []
    if args.symbol:
        # Tek sembol — manuel test için stop'u kullanıcıdan iste
        print(f"Manuel test: {args.symbol} için stop_loss bekleniyor (--symbol modu sadece debug)")
        return

    # Tüm aktif pozisyonlar + swing
    for p in get_all_positions():
        positions.append({
            "sembol": p["sembol"],
            "stop_loss": p.get("stop_loss"),
            "current_price": p.get("guncel_fiyat"),
            "portfoy": p["portfoy"],
        })
    for s in get_swing_active():
        positions.append({
            "sembol": s.get("sembol"),
            "stop_loss": s.get("stop_loss"),
            "current_price": s.get("guncel_fiyat"),
            "portfoy": "swing",
        })

    if not positions:
        print("[K-09] Aktif pozisyon yok")
        return

    print(f"[K-09] {len(positions)} pozisyon kontrol ediliyor...")

    for pos in positions:
        result = evaluate_position(pos["sembol"], pos["stop_loss"], pos["current_price"])
        if not result:
            continue

        if result["action"] == "no_check":
            if not args.quiet:
                print(f"  {pos['sembol']:6} ({pos['portfoy']:9}) → mesafe %{result['distance_pct']:.2f} (kontrol gerekmez)")
            continue

        msg = (f"{pos['sembol']} ({pos['portfoy']}) stop'a %{result['distance_pct']:.2f} mesafe\n"
               f"Stop: ${pos['stop_loss']} | Fiyat: ${pos['current_price']}\n"
               f"Negatif sayısı: {result['negatives']}/4\n"
               f"Detaylar: {' | '.join(result['details'])}\n"
               f"Karar: {result['action']}")

        print(f"  {pos['sembol']:6} ({pos['portfoy']:9}) → mesafe %{result['distance_pct']:.2f}, neg {result['negatives']}/4 → {result['action']}")

        if result["action"] == "EXIT_NOW":
            send_k_alert("K-09 EXIT_NOW", pos["sembol"], msg, severity="critical")
        elif result["action"] == "WAIT_STOP":
            send_k_alert("K-09 WAIT", pos["sembol"], msg, severity="warning")


if __name__ == "__main__":
    main()
