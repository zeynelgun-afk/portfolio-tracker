#!/usr/bin/env python3
"""
K-14: Kayıp serisi yönetimi (drawdown fren)
TRADING_PLAYBOOK.md K-14 kuralı uygulaması.

Swing closed.json'daki ardışık zararları sayar:
- 2 ardışık zarar → boyut %25 küçült
- 3 ardışık zarar → boyut %50 küçült + sadece A-kalite
- 4+ ardışık zarar → TAMAMEN DUR, min 1 hafta swing yok
- Toplam swing drawdown %15+ (peak-to-trough) → DUR

Kullanım:
  python scripts/k14_drawdown_track.py            # son durum + alert
  python scripts/k14_drawdown_track.py --quiet    # sessiz mod
"""

import sys
import json
import argparse
from pathlib import Path
from k_rules_common import DATA_DIR, send_k_alert, set_quiet_mode


def load_closed_swing():
    """closed.json'daki tüm swing trade'leri çıkış tarihine göre sıralı döndürür."""
    path = DATA_DIR / "swing" / "closed.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    trades = data.get("kapatilan_pozisyonlar", [])
    # Çıkış tarihine göre sırala
    return sorted(trades, key=lambda t: t.get("cikis_tarihi", ""))


def count_consecutive_losses(trades):
    """Son trade'den geriye doğru ardışık zarar sayar."""
    consecutive = 0
    for t in reversed(trades):
        pnl = t.get("kar_zarar_yuzde", 0)
        if pnl < 0:
            consecutive += 1
        else:
            break
    return consecutive


def calculate_drawdown(trades, capital=10000):
    """
    Peak-to-trough drawdown hesaplar.
    capital: başlangıç sermayesi (varsayılan $10K, swing standart)
    Her trade'in PnL yüzdesini sermayeye uygular.
    """
    if not trades:
        return {"peak": capital, "trough": capital, "drawdown_pct": 0}

    equity = capital
    peak = capital
    max_dd_pct = 0

    for t in trades:
        pnl_pct = t.get("kar_zarar_yuzde", 0) / 100
        # Trade büyüklüğü swing standart $5-10K, ortalama $7.5K varsayalım
        # PnL$ = $7.5K * pnl_pct, sermaye uygulanır
        trade_size = 7500
        pnl_dollar = trade_size * pnl_pct
        equity += pnl_dollar
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd_pct:
            max_dd_pct = dd

    return {"peak": peak, "trough": equity, "drawdown_pct": max_dd_pct, "current_equity": equity}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--days", type=int, default=30, help="Son N gün")
    args = parser.parse_args()
    set_quiet_mode(getattr(args, "quiet", False))

    trades = load_closed_swing()
    if not trades:
        print("[K-14] closed.json'da swing trade yok")
        return

    consecutive = count_consecutive_losses(trades)
    dd = calculate_drawdown(trades[-30:] if len(trades) > 30 else trades)

    last_trade = trades[-1]
    last_info = f"{last_trade.get('sembol')} {last_trade.get('kar_zarar_yuzde'):+.2f}% ({last_trade.get('cikis_tarihi')})"

    print(f"[K-14] Toplam swing trade: {len(trades)}")
    print(f"[K-14] Son trade: {last_info}")
    print(f"[K-14] Ardışık zarar: {consecutive}")
    print(f"[K-14] Drawdown (son 30): %{dd['drawdown_pct']:.2f}")

    # Kademeli fren karar
    if consecutive >= 4:
        msg = (f"K-14 STOP: {consecutive} ardışık zarar! "
               f"Min 1 hafta swing yasak.\n"
               f"Son: {last_info}\n"
               f"Drawdown: %{dd['drawdown_pct']:.2f}\n"
               f"Yeniden başlama: 5 iş günü soğuma + neden analizi + ilk 3 trade yarım poz")
        send_k_alert("K-14 STOP", "SWING", msg, severity="critical")
    elif consecutive == 3:
        msg = (f"K-14 katman 2: {consecutive} ardışık zarar.\n"
               f"Boyut %50 küçült + SADECE A-kalite (ichimoku 4/4 + sektör lider + RS pozitif + K-13 + K-17 + K-18).\n"
               f"Standart $10K → $5K, $5K → $2.5K\n"
               f"Son: {last_info}")
        send_k_alert("K-14 KATMAN 2", "SWING", msg, severity="critical")
    elif consecutive == 2:
        msg = (f"K-14 katman 1: {consecutive} ardışık zarar.\n"
               f"Boyut %25 küçült.\n"
               f"Standart $10K → $7.5K, $5K → $3.75K\n"
               f"Son: {last_info}")
        send_k_alert("K-14 KATMAN 1", "SWING", msg, severity="warning")

    if dd["drawdown_pct"] >= 15:
        msg = (f"K-14 DRAWDOWN STOP: peak-to-trough %{dd['drawdown_pct']:.2f}\n"
               f"DUR, ortamı değerlendir. VIX/SPY trendi kontrol et.")
        send_k_alert("K-14 DRAWDOWN", "SWING", msg, severity="critical")


if __name__ == "__main__":
    main()
