#!/usr/bin/env python3
"""
Portfolio Tracker - 4 Portföy Güncelleyici
Tüm portföyleri (Balanced, Aggressive, Dividend, Rotation) günceller.

Kullanım:
    python3 update_all_portfolios.py
    python3 update_all_portfolios.py --detailed
    python3 update_all_portfolios.py --api-key YOUR_KEY
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests yükleniyor...")
    os.system(f"{sys.executable} -m pip install requests --break-system-packages -q")
    import requests

# ═══════════════════════════════════════════════════════════════════════════════
# YAPILANDIRMA
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
PORTFOLIOS_DIR = DATA_DIR / "portfolios"

FMP_API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE_URL = "https://financialmodelingprep.com"

PORTFOLIOS = {
    "balanced": "Dengeli Portföy",
    "aggressive": "Agresif Büyüme",
    "dividend": "Değer + Temettü",
    "rotation": "Sektör Rotasyonu"
}


def fetch_quote(symbol: str) -> dict:
    """Tek hisse için güncel fiyat"""
    url = f"{FMP_BASE_URL}/stable/quote"
    try:
        resp = requests.get(url, params={"symbol": symbol, "apikey": FMP_API_KEY}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and len(data) > 0:
            return data[0]
    except Exception as e:
        print(f"  ⚠️ {symbol}: {e}")
    return {}


def load_portfolio(name: str) -> dict:
    """Portföy dosyasını yükle"""
    path = PORTFOLIOS_DIR / f"{name}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_portfolio(name: str, display_name: str) -> dict:
    """Portföyü güncelle ve hesapla"""
    print(f"\n{'='*70}")
    print(f"📊 {display_name} ({name}.json)")
    print(f"{'='*70}")
    
    portfolio = load_portfolio(name)
    
    # Pozisyonları güncelle
    positions = portfolio.get("pozisyonlar", portfolio.get("positions", []))
    total_invested = 0
    total_current = 0
    
    updated_positions = []
    
    for pos in positions:
        symbol = pos.get("sembol", pos.get("symbol"))
        shares = pos.get("adet", pos.get("shares", 0))
        cost_basis = pos.get("maliyet_baz", pos.get("cost_basis", 0))
        
        print(f"  🔄 {symbol}...", end=" ")
        
        quote = fetch_quote(symbol)
        current_price = quote.get("price", cost_basis)
        
        invested = shares * cost_basis
        current_value = shares * current_price
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0
        
        total_invested += invested
        total_current += current_value
        
        # Güncel pozisyon
        updated_pos = {
            "sembol": symbol,
            "isim": pos.get("isim", pos.get("name", "")),
            "sektor": pos.get("sektor", pos.get("sector", "")),
            "adet": shares,
            "maliyet_baz": cost_basis,
            "guncel_fiyat": current_price,
            "yatirim": invested,
            "guncel_deger": current_value,
            "kar_zarar": pnl,
            "kar_zarar_yuzde": pnl_pct,
            "gunluk_degisim_yuzde": quote.get("changePercentage", 0),
            "son_guncelleme": datetime.now().isoformat()
        }
        
        updated_positions.append(updated_pos)
        
        emoji = "🟢" if pnl_pct >= 0 else "🔴"
        print(f"{emoji} ${current_price:.2f} ({pnl_pct:+.1f}%)")
    
    # Nakit
    cash_info = portfolio.get("nakit", portfolio.get("cash", {}))
    cash = cash_info.get("miktar", cash_info.get("amount", 0))
    
    # Toplam değer
    total_value = total_current + cash
    initial_capital = portfolio.get("baslangic_sermaye", portfolio.get("initial_capital", 100000))
    total_pnl = total_value - initial_capital
    total_return_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
    
    # Ağırlıkları hesapla
    for pos in updated_positions:
        pos["agirlik_yuzde"] = (pos["guncel_deger"] / total_value * 100) if total_value > 0 else 0
    
    # Sektör ağırlıkları
    sector_weights = {}
    for pos in updated_positions:
        sector = pos["sektor"]
        sector_weights[sector] = sector_weights.get(sector, 0) + pos["agirlik_yuzde"]
    
    result = {
        "tarih": datetime.now().strftime("%Y-%m-%d"),
        "zaman_damgasi": datetime.now().isoformat(),
        "portfoy_adi": display_name,
        "baslangic_sermaye": initial_capital,
        "toplam_yatirim": total_invested,
        "toplam_guncel": total_current,
        "nakit": cash,
        "toplam_deger": total_value,
        "toplam_kar_zarar": total_pnl,
        "toplam_getiri_yuzde": total_return_pct,
        "pozisyon_sayisi": len(updated_positions),
        "pozisyonlar": updated_positions,
        "sektor_agirliklari": sector_weights,
        "nakit_agirlik_yuzde": (cash / total_value * 100) if total_value > 0 else 0
    }
    
    # Özet yazdır
    print(f"\n  💰 Toplam Değer: ${total_value:,.2f}")
    print(f"  📈 Getiri: ${total_pnl:,.2f} ({total_return_pct:+.2f}%)")
    print(f"  💵 Nakit: ${cash:,.2f} ({result['nakit_agirlik_yuzde']:.1f}%)")
    
    # Güncellenmiş portföyü kaydet
    portfolio_updated = {
        "portfoy_adi": display_name,
        "baslangic_sermaye": initial_capital,
        "nakit": {"miktar": cash, "para_birimi": "USD"},
        "pozisyonlar": updated_positions,
        "son_guncelleme": datetime.now().isoformat(),
        "toplam_deger": total_value,
        "toplam_getiri_yuzde": total_return_pct
    }
    
    output_path = PORTFOLIOS_DIR / f"{name}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(portfolio_updated, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ Kaydedildi: {output_path}")
    
    return result


def generate_summary(results: dict):
    """Tüm portföyler için özet rapor"""
    print(f"\n{'='*70}")
    print(f"📊 GENEL ÖZET - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}\n")
    
    total_capital = 0
    total_value = 0
    
    print(f"{'Portföy':<20} {'Başlangıç':>15} {'Güncel':>15} {'K/Z %':>10} {'Durum':>10}")
    print(f"{'-'*70}")
    
    for name, result in results.items():
        capital = result["baslangic_sermaye"]
        value = result["toplam_deger"]
        ret_pct = result["toplam_getiri_yuzde"]
        
        total_capital += capital
        total_value += value
        
        emoji = "🟢" if ret_pct >= 0 else "🔴"
        status = "Başarılı" if ret_pct >= 0 else "Kayıpda"
        
        print(f"{result['portfoy_adi']:<20} ${capital:>13,.0f} ${value:>13,.2f} {ret_pct:>9.2f}% {emoji} {status:>8}")
    
    print(f"{'-'*70}")
    total_pnl = total_value - total_capital
    total_ret_pct = (total_pnl / total_capital * 100) if total_capital > 0 else 0
    
    emoji = "🟢" if total_ret_pct >= 0 else "🔴"
    print(f"{'TOPLAM':<20} ${total_capital:>13,.0f} ${total_value:>13,.2f} {total_ret_pct:>9.2f}% {emoji}")
    print()
    
    # En iyi/kötü performanslar
    sorted_results = sorted(results.items(), key=lambda x: x[1]["toplam_getiri_yuzde"], reverse=True)
    
    print("🏆 EN İYİ PERFORMANS:")
    best = sorted_results[0][1]
    print(f"   {best['portfoy_adi']}: {best['toplam_getiri_yuzde']:+.2f}%")
    
    print("\n📉 EN KÖTÜ PERFORMANS:")
    worst = sorted_results[-1][1]
    print(f"   {worst['portfoy_adi']}: {worst['toplam_getiri_yuzde']:+.2f}%")
    
    # Özeti kaydet
    summary = {
        "tarih": datetime.now().strftime("%Y-%m-%d"),
        "zaman_damgasi": datetime.now().isoformat(),
        "toplam_sermaye": total_capital,
        "toplam_deger": total_value,
        "toplam_kar_zarar": total_pnl,
        "toplam_getiri_yuzde": total_ret_pct,
        "portfolyolar": {name: {
            "deger": r["toplam_deger"],
            "getiri_yuzde": r["toplam_getiri_yuzde"],
            "nakit": r["nakit"],
            "pozisyon_sayisi": r["pozisyon_sayisi"]
        } for name, r in results.items()}
    }
    
    summary_path = DATA_DIR / "portfolio_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Özet kaydedildi: {summary_path}")


def main():
    print("=" * 70)
    print("🚀 4 PORTFÖY GÜNCELLEYİCİ")
    print("=" * 70)
    
    results = {}
    
    # Her portföyü güncelle
    for name, display_name in PORTFOLIOS.items():
        try:
            result = update_portfolio(name, display_name)
            results[name] = result
        except Exception as e:
            print(f"\n❌ {display_name} güncellenirken hata: {e}")
            import traceback
            traceback.print_exc()
    
    # Genel özet
    if results:
        generate_summary(results)
    
    print(f"\n{'='*70}")
    print("✅ TÜM PORTFÖYLER GÜNCELLENDİ")
    print("=" * 70)


if __name__ == "__main__":
    main()
