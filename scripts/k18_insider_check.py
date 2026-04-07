#!/usr/bin/env python3
"""
K-18: Giriş öncesi insider kontrolü
TRADING_PLAYBOOK.md K-18 kuralı uygulaması.

3 katmanlı kontrol:
- Katman 1: İnsider satış analizi (FMP insider-trading)
  • CEO/CFO/Chairman 30g satışı varsa → girme/çeyrek
  • Toplam 30g satış >$5M → yarım pozisyon
  • Kelly nüansı: zararda satış (downtrend) → özellikle kaçın
  • Insider alışı varsa → pozitif sinyal
- Katman 2: Kısa vadeli baskı
  • Analist downgrade'leri (FMP analyst-stock-recommendations)
  • Margin compression (interestCoverage <2x)
- Katman 3: Dilüsyon → K-15b'ye yönlendir

Kullanım:
  python scripts/k18_insider_check.py SYMBOL
"""

import sys
import argparse
from datetime import datetime, timedelta
from k_rules_common import fmp_get, send_k_alert, set_quiet_mode


def check_insider_layer1(symbol):
    """Katman 1: İnsider satış analizi."""
    # FMP insider-trading endpoint (stable: insider-trading/search)
    data = fmp_get("insider-trading/search", {"symbol": symbol, "page": 0})
    if not data or not isinstance(data, list):
        return {"status": "veri yok", "score": 0, "details": ["FMP insider-trading: veri yok"]}

    # Son 30 gün filtresi
    cutoff = datetime.now() - timedelta(days=30)
    recent = []
    for tx in data:
        date_str = tx.get("transactionDate") or tx.get("filingDate", "")
        try:
            tx_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if tx_date >= cutoff:
                recent.append(tx)
        except (ValueError, TypeError):
            continue

    if not recent:
        return {"status": "temiz", "score": 0, "details": [f"Son 30g insider hareketi yok ({len(data)} eski kayıt)"]}

    details = []
    score_modifier = 0
    decision_flags = []

    # CEO/CFO/Chairman satış
    senior_titles = ["CEO", "CHIEF EXECUTIVE", "CFO", "CHIEF FINANCIAL", "CHAIRMAN", "PRESIDENT"]
    senior_sells = []
    total_sell_value = 0
    total_buy_value = 0

    for tx in recent:
        title = (tx.get("typeOfOwner", "") or "").upper()
        type_code = (tx.get("transactionType", "") or "").upper()
        shares = tx.get("securitiesTransacted", 0) or 0
        price = tx.get("price", 0) or 0
        value = shares * price

        is_sell = "S-Sale" in tx.get("transactionType", "") or "Sale" in (tx.get("acquistionOrDisposition") or "") or "D" == tx.get("acquistionOrDisposition")
        is_buy = "P-Purchase" in tx.get("transactionType", "") or "A" == tx.get("acquistionOrDisposition")

        is_senior = any(t in title for t in senior_titles)

        if is_sell:
            total_sell_value += value
            if is_senior:
                senior_sells.append({
                    "name": tx.get("reportingName", ""),
                    "title": title,
                    "value": value,
                    "date": tx.get("transactionDate", "")
                })
        elif is_buy:
            total_buy_value += value

    if senior_sells:
        names = ", ".join(f"{s['name']} ({s['title'][:15]}) ${s['value']/1e6:.1f}M" for s in senior_sells[:3])
        details.append(f"⚠️ Senior insider satışı: {names}")
        decision_flags.append("SENIOR_SELL")

    if total_sell_value >= 5_000_000:
        details.append(f"Toplam satış 30g: ${total_sell_value/1e6:.1f}M (>$5M eşiği)")
        decision_flags.append("HIGH_SELL_VALUE")
    elif total_sell_value > 0:
        details.append(f"Toplam satış 30g: ${total_sell_value/1e6:.1f}M")

    if total_buy_value > 0:
        details.append(f"Insider alış 30g: ${total_buy_value/1e6:.1f}M (pozitif sinyal)")

    return {
        "status": "kontrol",
        "score": len(decision_flags),
        "details": details,
        "flags": decision_flags,
        "senior_sells": senior_sells,
        "total_sell_value": total_sell_value,
        "total_buy_value": total_buy_value,
    }


def check_insider_layer2(symbol):
    """Katman 2: Analist downgrade ve margin compression."""
    details = []
    flags = []

    # Analist downgrade'leri
    grades = fmp_get("grades-historical", {"symbol": symbol, "limit": 10})
    if not grades:
        grades = fmp_get("upgrades-downgrades", {"symbol": symbol, "limit": 10})

    if grades and isinstance(grades, list):
        cutoff = datetime.now() - timedelta(days=14)
        recent_downs = 0
        for g in grades:
            date_str = g.get("publishedDate", "") or g.get("date", "")
            try:
                g_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                if g_date >= cutoff:
                    action = (g.get("action", "") or g.get("newGrade", "")).lower()
                    if "down" in action or "lowered" in action or "sell" in action:
                        recent_downs += 1
            except (ValueError, TypeError):
                continue
        if recent_downs >= 2:
            details.append(f"⚠️ {recent_downs} analist downgrade (son 2 hafta)")
            flags.append("ANALYST_DOWNGRADE")
        elif recent_downs > 0:
            details.append(f"{recent_downs} analist downgrade (son 2 hafta)")

    # Margin compression (interestCoverage <2x)
    km = fmp_get("key-metrics-ttm", {"symbol": symbol})
    if km and isinstance(km, list) and km:
        interest_coverage = km[0].get("interestCoverageTTM") or km[0].get("interestCoverage", 0)
        if interest_coverage and interest_coverage < 2:
            details.append(f"⚠️ Interest coverage {interest_coverage:.2f} (<2x = margin compression riski)")
            flags.append("MARGIN_COMPRESSION")

    return {"details": details, "flags": flags}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true", help="Sadece warning/critical alerts telegrama gider")
    parser.add_argument("symbol")
    args = parser.parse_args()
    set_quiet_mode(getattr(args, "quiet", False))

    symbol = args.symbol.upper()
    print(f"[K-18] {symbol} insider kontrolü başlıyor...")

    # KATMAN 1
    print("\n=== KATMAN 1: İNSİDER SATIŞ ===")
    l1 = check_insider_layer1(symbol)
    for d in l1["details"]:
        print(f"  {d}")

    # KATMAN 2
    print("\n=== KATMAN 2: KISA VADELİ BASKI ===")
    l2 = check_insider_layer2(symbol)
    if l2["details"]:
        for d in l2["details"]:
            print(f"  {d}")
    else:
        print("  ✓ Temiz")

    # KATMAN 3
    print("\n=== KATMAN 3: DİLÜSYON ===")
    print(f"  → scripts/k15b_dilution_check.py {symbol} ile kontrol et")

    # KARAR
    all_flags = l1.get("flags", []) + l2.get("flags", [])
    print(f"\n=== KARAR ===")
    print(f"Toplam flag: {len(all_flags)}: {all_flags}")

    if "SENIOR_SELL" in all_flags:
        decision = "GIRME veya çeyrek pozisyon (CEO/CFO satışı var)"
        severity = "critical"
    elif "HIGH_SELL_VALUE" in all_flags or "MARGIN_COMPRESSION" in all_flags:
        decision = "YARIM pozisyon (yüksek satış veya margin riski)"
        severity = "warning"
    elif "ANALYST_DOWNGRADE" in all_flags:
        decision = "YARIM pozisyon veya skip (analist downgrade)"
        severity = "warning"
    elif l1.get("total_buy_value", 0) > 0:
        decision = "Normal pozisyon + POZİTİF SİNYAL (insider alış)"
        severity = "info"
    else:
        decision = "Normal pozisyon (insider temiz)"
        severity = "info"

    print(f"KARAR: {decision}")

    msg_lines = [f"{symbol} K-18 sonuç:"]
    msg_lines.extend(l1["details"])
    msg_lines.extend(l2["details"])
    msg_lines.append(f"\nKARAR: {decision}")
    msg = "\n".join(msg_lines)

    send_k_alert("K-18", symbol, msg, severity=severity)


if __name__ == "__main__":
    main()
