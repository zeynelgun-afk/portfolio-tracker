#!/usr/bin/env python3
"""
Portfolio Tracker - Daily Update Script
Uses FMP API to fetch current prices and update performance log.

Usage:
    python3 update_portfolio.py                    # Normal güncelleme
    python3 update_portfolio.py --report           # Detaylı rapor
    python3 update_portfolio.py --api-key YOUR_KEY # Farklı API key
"""

import json
import csv
import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system(f"{sys.executable} -m pip install requests --break-system-packages -q")
    import requests

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
REPORTS_DIR = PROJECT_DIR / "reports"

FMP_BASE_URL = "https://financialmodelingprep.com"
DEFAULT_API_KEY = os.environ.get("FMP_API_KEY", "")


def load_portfolio(path: Path = None) -> dict:
    """portfolio.json dosyasını yükle"""
    if path is None:
        path = DATA_DIR / "portfolio.json"
    with open(path, "r") as f:
        return json.load(f)


def fetch_quotes(symbols: list, api_key: str) -> dict:
    """FMP Stable API'den toplu fiyat çek"""
    result = {}
    for symbol in symbols:
        url = f"{FMP_BASE_URL}/stable/quote"
        try:
            resp = requests.get(url, params={"symbol": symbol, "apikey": api_key}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                item = data[0]
                # Field mapping: stable API uses slightly different names
                result[symbol] = {
                    "symbol": item.get("symbol", symbol),
                    "price": item.get("price", 0),
                    "changesPercentage": item.get("changePercentage", 0),
                    "change": item.get("change", 0),
                    "dayHigh": item.get("dayHigh", 0),
                    "dayLow": item.get("dayLow", 0),
                    "yearHigh": item.get("yearHigh", 0),
                    "yearLow": item.get("yearLow", 0),
                    "marketCap": item.get("marketCap", 0),
                    "volume": item.get("volume", 0),
                    "avgVolume": item.get("avgVolume", 0),
                    "pe": item.get("pe", 0),
                    "open": item.get("open", 0),
                    "previousClose": item.get("previousClose", 0),
                }
                print(f"  ✅ {symbol}: ${item.get('price', 0):.2f}")
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
    return result


def fetch_key_metrics(symbol: str, api_key: str) -> dict:
    """Temel metrikler çek (P/E, beta, vb.)"""
    url = f"{FMP_BASE_URL}/api/v3/quote/{symbol}"
    try:
        resp = requests.get(url, params={"apikey": api_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else {}
    except:
        return {}


def calculate_portfolio(portfolio: dict, quotes: dict) -> dict:
    """Portföy değerlerini hesapla"""
    positions = []
    total_invested = 0
    total_current = 0

    for pos in portfolio["positions"]:
        symbol = pos["symbol"]
        shares = pos["shares"]
        cost = pos["cost_basis"]
        invested = shares * cost

        quote = quotes.get(symbol, {})
        current_price = quote.get("price", cost)
        current_value = shares * current_price
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0
        weight = 0  # calculated after total

        total_invested += invested
        total_current += current_value

        positions.append({
            "symbol": symbol,
            "name": pos.get("name", ""),
            "sector": pos.get("sector", ""),
            "shares": shares,
            "cost_basis": cost,
            "current_price": current_price,
            "invested": invested,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "change_pct": quote.get("changesPercentage", 0),
            "day_high": quote.get("dayHigh", 0),
            "day_low": quote.get("dayLow", 0),
            "volume": quote.get("volume", 0),
            "avg_volume": quote.get("avgVolume", 0),
            "pe": quote.get("pe", 0),
            "market_cap": quote.get("marketCap", 0),
            "year_high": quote.get("yearHigh", 0),
            "year_low": quote.get("yearLow", 0),
        })

    cash = portfolio["cash"]["amount"]
    total_value = total_current + cash
    initial = portfolio["initial_capital"]

    # Ağırlıkları hesapla
    for p in positions:
        p["weight_pct"] = (p["current_value"] / total_value * 100) if total_value > 0 else 0

    # Sektör ağırlıkları
    sector_weights = {}
    for p in positions:
        s = p["sector"]
        sector_weights[s] = sector_weights.get(s, 0) + p["weight_pct"]

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "initial_capital": initial,
        "total_invested": total_invested,
        "total_current": total_current,
        "cash": cash,
        "total_value": total_value,
        "total_pnl": total_value - initial,
        "total_return_pct": (total_value - initial) / initial * 100,
        "positions": positions,
        "sector_weights": sector_weights,
        "cash_weight_pct": (cash / total_value * 100) if total_value > 0 else 0,
    }


def check_risk_alerts(result: dict, portfolio: dict) -> list:
    """Risk uyarılarını kontrol et"""
    alerts = []
    limits = portfolio.get("risk_limits", {})

    for p in result["positions"]:
        # Tek pozisyon limiti
        max_pos = limits.get("max_single_position_pct", 25)
        if p["weight_pct"] > max_pos:
            alerts.append(f"⚠️ {p['symbol']}: %{p['weight_pct']:.1f} > max %{max_pos} (pozisyon limiti aşıldı)")

        # Stop-loss kontrolü
        stop = limits.get("stop_loss_pct", -15)
        if p["pnl_pct"] < stop:
            alerts.append(f"🛑 {p['symbol']}: %{p['pnl_pct']:.1f} < %{stop} STOP-LOSS!")

    # Sektör limiti
    max_sector = limits.get("max_sector_weight_pct", 40)
    for sector, weight in result["sector_weights"].items():
        if weight > max_sector:
            alerts.append(f"⚠️ Sektör '{sector}': %{weight:.1f} > max %{max_sector}")

    # Nakit limiti
    min_cash = limits.get("min_cash_pct", 3)
    if result["cash_weight_pct"] < min_cash:
        alerts.append(f"⚠️ Nakit: %{result['cash_weight_pct']:.1f} < min %{min_cash}")

    return alerts


def append_performance_log(result: dict, quotes: dict):
    """performance_log.csv'ye yeni satır ekle"""
    log_path = DATA_DIR / "performance_log.csv"

    row = {
        "date": result["date"],
        "portfolio_value": f"{result['total_value']:.2f}",
        "daily_return_pct": "",  # Önceki günle karşılaştırma gerekir
        "cumulative_return_pct": f"{result['total_return_pct']:.2f}",
        "cash": f"{result['cash']:.2f}",
    }

    for p in result["positions"]:
        sym = p["symbol"].lower()
        row[f"{sym}_price"] = f"{p['current_price']:.2f}"
        row[f"{sym}_value"] = f"{p['current_value']:.2f}"

    row["notes"] = f"Auto-update {datetime.now().strftime('%H:%M')}"

    # Önceki günün değerini oku
    try:
        with open(log_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                prev_value = float(rows[-1]["portfolio_value"])
                daily_ret = (result["total_value"] - prev_value) / prev_value * 100
                row["daily_return_pct"] = f"{daily_ret:.2f}"
    except:
        pass

    # CSV'ye ekle
    fieldnames = list(row.keys())
    file_exists = log_path.exists()

    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"✅ Performance log güncellendi: {log_path}")


def generate_report(result: dict, alerts: list, detailed: bool = False) -> str:
    """Markdown rapor oluştur"""
    lines = []
    lines.append(f"# 📊 Portföy Raporu — {result['date']}")
    lines.append(f"")
    lines.append(f"**Güncelleme:** {result['timestamp']}")
    lines.append(f"")
    lines.append(f"## Özet")
    lines.append(f"")
    lines.append(f"| Metrik | Değer |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Başlangıç Sermayesi | ${result['initial_capital']:,.2f} |")
    lines.append(f"| Toplam Portföy Değeri | ${result['total_value']:,.2f} |")
    lines.append(f"| Nakit | ${result['cash']:,.2f} ({result['cash_weight_pct']:.1f}%) |")
    lines.append(f"| Toplam P/L | ${result['total_pnl']:,.2f} ({result['total_return_pct']:+.2f}%) |")
    lines.append(f"")

    # Pozisyonlar tablosu
    lines.append(f"## Pozisyonlar")
    lines.append(f"")
    lines.append(f"| Hisse | Sektör | Adet | Maliyet | Fiyat | Değer | P/L% | Ağırlık |")
    lines.append(f"|-------|--------|------|---------|-------|-------|------|---------|")

    for p in sorted(result["positions"], key=lambda x: x["current_value"], reverse=True):
        emoji = "🟢" if p["pnl_pct"] >= 0 else "🔴"
        lines.append(
            f"| {emoji} {p['symbol']} | {p['sector']} | {p['shares']:,} | "
            f"${p['cost_basis']:.2f} | ${p['current_price']:.2f} | "
            f"${p['current_value']:,.2f} | {p['pnl_pct']:+.1f}% | {p['weight_pct']:.1f}% |"
        )
    lines.append(f"")

    # Sektör dağılımı
    lines.append(f"## Sektör Dağılımı")
    lines.append(f"")
    for sector, weight in sorted(result["sector_weights"].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(weight / 2)
        lines.append(f"- **{sector}**: {weight:.1f}% {bar}")
    lines.append(f"- **Nakit**: {result['cash_weight_pct']:.1f}%")
    lines.append(f"")

    # Risk uyarıları
    if alerts:
        lines.append(f"## ⚠️ Risk Uyarıları")
        lines.append(f"")
        for a in alerts:
            lines.append(f"- {a}")
        lines.append(f"")
    else:
        lines.append(f"## ✅ Risk Durumu: Normal")
        lines.append(f"")

    if detailed:
        lines.append(f"## Detaylı Pozisyon Analizi")
        lines.append(f"")
        for p in result["positions"]:
            lines.append(f"### {p['symbol']} — {p['name']}")
            lines.append(f"- P/E: {p['pe']:.1f}" if p['pe'] else "- P/E: N/A")
            lines.append(f"- Gün Aralığı: ${p['day_low']:.2f} - ${p['day_high']:.2f}")
            lines.append(f"- 52H Aralığı: ${p['year_low']:.2f} - ${p['year_high']:.2f}")
            lines.append(f"- Hacim: {p['volume']:,} (Ort: {p['avg_volume']:,})")
            if p['year_high'] > 0:
                from_high = (p['current_price'] - p['year_high']) / p['year_high'] * 100
                lines.append(f"- 52H Yüksekten Uzaklık: {from_high:+.1f}%")
            lines.append(f"")

    lines.append(f"---")
    lines.append(f"*Bu rapor otomatik oluşturulmuştur. Yatırım tavsiyesi değildir.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Portfolio Tracker - Daily Update")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="FMP API key")
    parser.add_argument("--report", action="store_true", help="Detaylı rapor oluştur")
    parser.add_argument("--save-report", action="store_true", help="Raporu dosyaya kaydet")
    parser.add_argument("--no-log", action="store_true", help="Performance log'a ekleme")
    args = parser.parse_args()

    if not args.api_key:
        print("❌ FMP API key gerekli. --api-key ile belirtin veya FMP_API_KEY env var ayarlayın.")
        sys.exit(1)

    # Portföyü yükle
    print("📂 Portföy yükleniyor...")
    portfolio = load_portfolio()

    # Fiyatları çek
    symbols = [p["symbol"] for p in portfolio["positions"]]
    print(f"📡 Fiyatlar çekiliyor: {', '.join(symbols)}")
    quotes = fetch_quotes(symbols, args.api_key)

    if not quotes:
        print("❌ Fiyatlar alınamadı, çıkılıyor.")
        sys.exit(1)

    print(f"✅ {len(quotes)} hisse fiyatı alındı")

    # Portföy hesapla
    result = calculate_portfolio(portfolio, quotes)

    # Risk kontrol
    alerts = check_risk_alerts(result, portfolio)

    # Rapor
    report = generate_report(result, alerts, detailed=args.report)
    print("\n" + report)

    # Performance log
    if not args.no_log:
        append_performance_log(result, quotes)

    # Raporu dosyaya kaydet
    if args.save_report:
        REPORTS_DIR.mkdir(exist_ok=True)
        report_path = REPORTS_DIR / f"report_{result['date']}.md"
        with open(report_path, "w") as f:
            f.write(report)
        print(f"📄 Rapor kaydedildi: {report_path}")

    # Sonuç JSON
    result_path = DATA_DIR / "latest_snapshot.json"
    # Serialize-safe versiyon
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"💾 Snapshot kaydedildi: {result_path}")


if __name__ == "__main__":
    main()
