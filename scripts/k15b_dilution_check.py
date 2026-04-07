#!/usr/bin/env python3
"""
K-15b: Momentum hisselerinde dilüsyon + arz riski
TRADING_PLAYBOOK.md K-15b kuralı uygulaması.

5 maddelik dilüsyon risk skoru:
1) Negatif FCF (son 4 çeyrek)
2) Borç/öz sermaye >1.5
3) Son 12 ay hisse arzı yapılmış (shares-float artışı)
4) Aktif shelf registration (manuel kontrol gerekli — alert)
5) Büyük CapEx + finansman belirsiz (manuel kontrol gerekli — alert)

Karar:
- Skor 0-1: normal
- Skor 2-3: max %2 portföy ağırlığı
- Skor 4-5: girme veya sadece opsiyon

Kullanım:
  python scripts/k15b_dilution_check.py SYMBOL
"""

import sys
import argparse
from k_rules_common import fmp_get, send_k_alert


def is_momentum_stock(symbol):
    """K-15b momentum tanımı: son 3 ay >%30 ralli VE (P/E negatif veya >50)."""
    quote = fmp_get("quote", {"symbol": symbol})
    if not quote or not isinstance(quote, list) or not quote:
        return False, "quote yok"

    q = quote[0]
    pe = q.get("pe")

    # Son 3 ay performansı için historical fiyat
    hist = fmp_get("historical-price-eod/full", {"symbol": symbol})
    if not hist or not isinstance(hist, list):
        return False, "historical yok"

    bars = hist
    if len(bars) < 65:
        return False, "yetersiz veri"

    today = bars[0]["close"]
    three_months_ago = bars[63]["close"]
    pct_3m = ((today - three_months_ago) / three_months_ago) * 100

    is_mom = pct_3m > 30 and (pe is None or pe < 0 or pe > 50)
    return is_mom, f"3ay %{pct_3m:.1f}, P/E {pe}"


def calc_dilution_score(symbol):
    """5 maddelik skor hesabı."""
    score = 0
    details = []

    # 1) Negatif FCF (son 4 çeyrek)
    cf = fmp_get("cash-flow-statement", {"symbol": symbol, "period": "quarter", "limit": 4})
    if cf and isinstance(cf, list) and len(cf) >= 4:
        fcf_values = [q.get("freeCashFlow", 0) for q in cf]
        negative_count = sum(1 for v in fcf_values if v < 0)
        if negative_count >= 3:  # 4 çeyreğin en az 3'ü negatif
            score += 1
            details.append(f"Negatif FCF: {negative_count}/4 çeyrek (toplam ${sum(fcf_values)/1e6:.0f}M)")
        else:
            details.append(f"FCF OK: {negative_count}/4 negatif")
    else:
        details.append("FCF: veri yok")

    # 2) Borç/Öz sermaye >1.5
    bs = fmp_get("balance-sheet-statement", {"symbol": symbol, "period": "quarter", "limit": 1})
    if bs and isinstance(bs, list) and bs:
        total_debt = bs[0].get("totalDebt", 0) or 0
        equity = bs[0].get("totalStockholdersEquity", 0) or 1
        if equity > 0:
            de_ratio = total_debt / equity
            if de_ratio > 1.5:
                score += 1
                details.append(f"D/E {de_ratio:.2f} > 1.5")
            else:
                details.append(f"D/E {de_ratio:.2f} OK")
        else:
            score += 1
            details.append(f"Negatif equity (D/E hesaplanamaz)")
    else:
        details.append("Balance sheet: veri yok")

    # 3) Son 12 ay hisse arzı (shares outstanding artışı)
    profile = fmp_get("profile", {"symbol": symbol})
    historical_bs = fmp_get("balance-sheet-statement", {"symbol": symbol, "period": "annual", "limit": 2})
    if historical_bs and isinstance(historical_bs, list) and len(historical_bs) >= 2:
        current_shares = historical_bs[0].get("commonStock") or historical_bs[0].get("totalStockholdersEquity", 0)
        prev_shares = historical_bs[1].get("commonStock") or historical_bs[1].get("totalStockholdersEquity", 1)
        # Daha doğru: sharesOutstanding alanını kullan (varsa)
        current_so = historical_bs[0].get("commonStockSharesOutstanding") or current_shares
        prev_so = historical_bs[1].get("commonStockSharesOutstanding") or prev_shares
        if prev_so and prev_so > 0:
            growth = ((current_so - prev_so) / prev_so) * 100
            if growth > 5:  # %5+ hisse artışı = arz işareti
                score += 1
                details.append(f"Hisse arzı: %{growth:.1f} yıllık artış")
            else:
                details.append(f"Hisse sabit: %{growth:.1f}")
    else:
        details.append("Shares: veri yok")

    # 4) Aktif shelf registration → manuel kontrol notu
    details.append("Shelf S-3: MANUEL KONTROL (SEC EDGAR / dilutiontracker.com)")

    # 5) CapEx + finansman → manuel kontrol notu
    details.append("CapEx/finansman: MANUEL KONTROL (10-K MD&A / earnings call)")

    return score, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", help="Hisse sembolü (örn: RKLB)")
    parser.add_argument("--force", action="store_true", help="Momentum check'i atla")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    print(f"[K-15b] {symbol} dilüsyon kontrolü...")

    if not args.force:
        is_mom, reason = is_momentum_stock(symbol)
        if not is_mom:
            print(f"[K-15b] {symbol} momentum hisse değil ({reason}). K-15b uygulanmaz.")
            print(f"  --force ile yine de skor hesaplayabilirsin.")
            return
        print(f"[K-15b] Momentum hisse onaylandı: {reason}")

    score, details = calc_dilution_score(symbol)

    print(f"\n[K-15b] {symbol} SKOR: {score}/5 (manuel olanlar dahil değil, otomatik 0-3)")
    for d in details:
        print(f"  • {d}")

    # Karar
    if score >= 4:
        decision = "GİRME veya sadece opsiyon (max $1K premium)"
        severity = "critical"
    elif score >= 2:
        decision = "MAX %2 portföy ağırlığı (Dengeli $2K, Agresif $8K)"
        severity = "warning"
    else:
        decision = "Normal pozisyon ($5K-$10K)"
        severity = "info"

    print(f"\n[K-15b] KARAR: {decision}")

    msg = (f"{symbol} K-15b skor: {score}/5\n"
           f"{chr(10).join('• '+d for d in details)}\n"
           f"\nKARAR: {decision}\n"
           f"⚠️ Manuel kontrol: shelf registration + CapEx finansman")
    send_k_alert(f"K-15b SCORE:{score}", symbol, msg, severity=severity)


if __name__ == "__main__":
    main()
