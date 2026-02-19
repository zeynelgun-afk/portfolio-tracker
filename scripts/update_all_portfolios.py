#!/usr/bin/env python3
"""
Portfolio Tracker - TAM OTOMATİK GÜNCELLEYİCİ
- 4 Portföy güncelleme
- Swing Trade otomatik kontrol
- Stop-loss/Target otomatik kapama
- Timeframe disiplin kontrolü

Kullanım:
    python3 update_all_portfolios.py
    python3 update_all_portfolios.py --swing-only
    python3 update_all_portfolios.py --portfolios-only
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse

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
SWING_DIR = DATA_DIR / "swing"

FMP_API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE_URL = "https://financialmodelingprep.com"

PORTFOLIOS = {
    "balanced": "Dengeli Portföy",
    "aggressive": "Agresif Büyüme",
    "dividend": "Değer + Temettü",
    "rotation": "Sektör Rotasyonu"
}

# Swing trade kuralları
SWING_RULES = {
    "target_pct": 10,  # %10 hedef
    "stop_pct": 5,     # %5 stop
    "max_days": 10,    # 10 gün zaman çerçevesi
    "trailing_stop_trigger": 5  # %5 karlı olunca trailing stop aktive
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


def load_json(path: Path) -> dict:
    """JSON dosya yükle"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    """JSON dosya kaydet"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFÖY GÜNCELLEYİCİ
# ═══════════════════════════════════════════════════════════════════════════════

def update_portfolio(name: str, display_name: str) -> dict:
    """Portföyü güncelle ve hesapla"""
    print(f"\n{'='*70}")
    print(f"📊 {display_name} ({name}.json)")
    print(f"{'='*70}")
    
    portfolio = load_json(PORTFOLIOS_DIR / f"{name}.json")
    
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
    
    cash_info = portfolio.get("nakit", portfolio.get("cash", {}))
    cash = cash_info.get("miktar", cash_info.get("amount", 0))
    
    total_value = total_current + cash
    initial_capital = portfolio.get("baslangic_sermaye", portfolio.get("initial_capital", 100000))
    total_pnl = total_value - initial_capital
    total_return_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
    
    for pos in updated_positions:
        pos["agirlik_yuzde"] = (pos["guncel_deger"] / total_value * 100) if total_value > 0 else 0
    
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
    
    print(f"\n  💰 Toplam Değer: ${total_value:,.2f}")
    print(f"  📈 Getiri: ${total_pnl:,.2f} ({total_return_pct:+.2f}%)")
    print(f"  💵 Nakit: ${cash:,.2f} ({result['nakit_agirlik_yuzde']:.1f}%)")
    
    portfolio_updated = {
        "portfoy_adi": display_name,
        "baslangic_sermaye": initial_capital,
        "nakit": {"miktar": cash, "para_birimi": "USD"},
        "pozisyonlar": updated_positions,
        "son_guncelleme": datetime.now().isoformat(),
        "toplam_deger": total_value,
        "toplam_getiri_yuzde": total_return_pct
    }
    
    save_json(PORTFOLIOS_DIR / f"{name}.json", portfolio_updated)
    print(f"  ✅ Kaydedildi")
    
    return result


def generate_portfolio_summary(results: dict):
    """Tüm portföyler için özet rapor"""
    print(f"\n{'='*70}")
    print(f"📊 PORTFÖY ÖZET - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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
    
    sorted_results = sorted(results.items(), key=lambda x: x[1]["toplam_getiri_yuzde"], reverse=True)
    
    print("🏆 EN İYİ PERFORMANS:")
    best = sorted_results[0][1]
    print(f"   {best['portfoy_adi']}: {best['toplam_getiri_yuzde']:+.2f}%")
    
    print("\n📉 EN KÖTÜ PERFORMANS:")
    worst = sorted_results[-1][1]
    print(f"   {worst['portfoy_adi']}: {worst['toplam_getiri_yuzde']:+.2f}%")
    
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
    
    save_json(DATA_DIR / "portfolio_summary.json", summary)
    print(f"\n✅ Özet kaydedildi: portfolio_summary.json")


# ═══════════════════════════════════════════════════════════════════════════════
# SWING TRADE OTOMATİK KONTROL
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_days_held(entry_date_str: str) -> int:
    """Pozisyon tutma süresini hesapla"""
    try:
        entry_date = datetime.fromisoformat(entry_date_str.replace("Z", "+00:00"))
        return (datetime.now() - entry_date).days
    except:
        # Farklı format dene (YYYY-MM-DD)
        try:
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
            return (datetime.now() - entry_date).days
        except:
            return 0


def update_swing_positions():
    """Swing pozisyonlarını güncelle ve otomatik çıkışları kontrol et"""
    print(f"\n{'='*70}")
    print(f"🎯 SWING TRADE OTOMATİK KONTROL")
    print(f"{'='*70}\n")
    
    active_path = SWING_DIR / "active.json"
    closed_path = SWING_DIR / "closed.json"
    
    if not active_path.exists():
        print("❌ active.json bulunamadı")
        return
    
    active_data = load_json(active_path)
    closed_data = load_json(closed_path) if closed_path.exists() else {
        "son_guncelleme": datetime.now().strftime("%Y-%m-%d"),
        "kapatilan_pozisyonlar": [],
        "istatistikler": {}
    }
    
    positions = active_data.get("aktif_pozisyonlar", [])
    
    if not positions:
        print("✅ Aktif pozisyon yok")
        return
    
    print(f"📊 {len(positions)} aktif pozisyon kontrol ediliyor...\n")
    
    to_close = []
    updated_positions = []
    action_items = []
    
    for pos in positions:
        symbol = pos.get("sembol", pos.get("symbol"))
        entry_price = pos.get("giris_fiyati", pos.get("entry_price"))
        target_price = pos.get("hedef_fiyat", pos.get("target_price"))
        stop_loss = pos.get("stop_loss")
        entry_date = pos.get("giris_tarihi", pos.get("entry_date"))
        
        print(f"  🔄 {symbol}...", end=" ")
        
        # Fiyat çek
        quote = fetch_quote(symbol)
        current_price = quote.get("price", entry_price)
        
        # Hesaplamalar
        pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        days_held = calculate_days_held(entry_date)
        
        # Kontroller
        target_hit = current_price >= target_price
        stop_hit = current_price <= stop_loss
        timeframe_exceed = days_held > SWING_RULES["max_days"]
        
        # Güncelle
        pos["guncel_fiyat"] = current_price
        pos["guncel_kar_zarar_yuzde"] = pnl_pct
        pos["tutulan_gun"] = days_held
        pos["son_guncelleme"] = datetime.now().isoformat()
        
        # ÇIKIŞ KONTROL
        exit_reason = None
        
        if target_hit:
            exit_reason = f"Hedef vurdu (${target_price:.2f})"
            emoji = "🎯"
            print(f"{emoji} ${current_price:.2f} TARGET HIT! {pnl_pct:+.1f}%")
            
        elif stop_hit:
            exit_reason = f"Stop-loss vurdu (${stop_loss:.2f})"
            emoji = "🛑"
            print(f"{emoji} ${current_price:.2f} STOP HIT! {pnl_pct:+.1f}%")
            
        elif timeframe_exceed and pnl_pct > 0:
            exit_reason = f"Zaman çerçevesi aşıldı ({days_held} gün, hedef {SWING_RULES['max_days']} gündü), kar alındı"
            emoji = "⏰"
            print(f"{emoji} ${current_price:.2f} ZAMAN AŞIMI (karlı) {pnl_pct:+.1f}%")
            
        elif timeframe_exceed and pnl_pct < 0:
            exit_reason = f"Zaman çerçevesi aşıldı ({days_held} gün, hedef {SWING_RULES['max_days']} gündü), zarar kesildi"
            emoji = "⏰"
            print(f"{emoji} ${current_price:.2f} ZAMAN AŞIMI (zararlı) {pnl_pct:+.1f}%")
        
        if exit_reason:
            # Kapatılacaklar listesine ekle
            closed_pos = {
                "id": pos.get("id"),
                "sembol": symbol,
                "giris_tarihi": entry_date,
                "cikis_tarihi": datetime.now().strftime("%Y-%m-%d"),
                "giris_fiyati": entry_price,
                "cikis_fiyati": current_price,
                "kar_zarar_yuzde": pnl_pct,
                "tutulan_gun": days_held,
                "cikis_nedeni": exit_reason,
                "sonuc": "KAZANÇ" if pnl_pct >= 0 else "ZARAR",
                "ders": f"Otomatik kapatıldı. {exit_reason}",
                "giris_nedeni": pos.get("giris_nedeni", ""),
                "katalizor": pos.get("katalizor", ""),
                "tez": pos.get("tez", "")
            }
            to_close.append(closed_pos)
            action_items.append(f"🔴 KAPANDI: {symbol} {pnl_pct:+.1f}% - {exit_reason}")
            
        else:
            # Açık kalsın
            emoji = "🟢" if pnl_pct >= 0 else "🔴"
            
            # Trailing stop kontrol
            if pnl_pct >= SWING_RULES["trailing_stop_trigger"] and stop_loss < entry_price:
                pos["stop_loss"] = entry_price  # Break-even'e çek
                action_items.append(f"📈 TRAILING: {symbol} stop ${entry_price:.2f} (break-even)")
                print(f"{emoji} ${current_price:.2f} ({pnl_pct:+.1f}%) TRAILING AKTIVE")
            else:
                status = "Normal" if abs(pnl_pct) < 3 else ("Stop yakın!" if current_price < stop_loss * 1.02 else "İyi")
                print(f"{emoji} ${current_price:.2f} ({pnl_pct:+.1f}%) {status}")
            
            updated_positions.append(pos)
    
    # Kapatılanları closed.json'a taşı
    if to_close:
        print(f"\n{'='*70}")
        print(f"🔴 OTOMATİK KAPATILAN POZİSYONLAR: {len(to_close)}")
        print(f"{'='*70}")
        
        for closed_pos in to_close:
            sym = closed_pos["sembol"]
            pnl = closed_pos["kar_zarar_yuzde"]
            reason = closed_pos["cikis_nedeni"]
            print(f"  ✅ {sym}: {pnl:+.2f}% - {reason}")
            
            # Closed listesine ekle
            closed_data["kapatilan_pozisyonlar"].append(closed_pos)
        
        # İstatistikleri güncelle
        all_closed = closed_data["kapatilan_pozisyonlar"]
        winning = [p for p in all_closed if p.get("kar_zarar_yuzde", 0) >= 0]
        losing = [p for p in all_closed if p.get("kar_zarar_yuzde", 0) < 0]
        
        closed_data["istatistikler"] = {
            "toplam_islem": len(all_closed),
            "kazanan_islem": len(winning),
            "kaybeden_islem": len(losing),
            "kazanma_orani": (len(winning) / len(all_closed) * 100) if all_closed else 0,
            "toplam_kar_zarar_yuzde": sum(p.get("kar_zarar_yuzde", 0) for p in all_closed),
            "ortalama_kar_zarar_yuzde": (sum(p.get("kar_zarar_yuzde", 0) for p in all_closed) / len(all_closed)) if all_closed else 0,
            "en_iyi_islem": max(all_closed, key=lambda x: x.get("kar_zarar_yuzde", 0)) if all_closed else None,
            "en_kotu_islem": min(all_closed, key=lambda x: x.get("kar_zarar_yuzde", 0)) if all_closed else None
        }
        
        closed_data["son_guncelleme"] = datetime.now().strftime("%Y-%m-%d")
        save_json(closed_path, closed_data)
        print(f"\n  ✅ closed.json güncellendi")
    
    # Active güncellemelerini kaydet
    active_data["aktif_pozisyonlar"] = updated_positions
    active_data["son_guncelleme"] = datetime.now().isoformat()
    active_data["ozet"] = {
        "toplam_pozisyon": len(updated_positions),
        "bos_slot": 10 - len(updated_positions),
        "maksimum_pozisyon": 10,
        "ortalama_kar_zarar_yuzde": sum(p.get("guncel_kar_zarar_yuzde", 0) for p in updated_positions) / len(updated_positions) if updated_positions else 0
    }
    save_json(active_path, active_data)
    
    # Özet
    print(f"\n{'='*70}")
    print(f"📋 SWING ÖZET")
    print(f"{'='*70}")
    print(f"  Aktif Pozisyon: {len(updated_positions)}/10")
    print(f"  Kapatılan: {len(to_close)}")
    if updated_positions:
        avg_pnl = active_data["ozet"]["ortalama_kar_zarar_yuzde"]
        emoji = "🟢" if avg_pnl >= 0 else "🔴"
        print(f"  Ortalama P/L: {emoji} {avg_pnl:+.2f}%")
    
    if action_items:
        print(f"\n  📌 ACTION ITEMS:")
        for item in action_items:
            print(f"     {item}")
    
    # İstatistikler
    if closed_data.get("istatistikler"):
        stats = closed_data["istatistikler"]
        print(f"\n  📊 TOPLAM İSTATİSTİKLER:")
        print(f"     Toplam İşlem: {stats['toplam_islem']}")
        print(f"     Kazanma Oranı: {stats['kazanma_orani']:.1f}%")
        print(f"     Ortalama: {stats['ortalama_kar_zarar_yuzde']:+.2f}%")
    
    print(f"\n✅ active.json güncellendi")


# ═══════════════════════════════════════════════════════════════════════════════
# ANA PROGRAM
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Portfolio Tracker - Tam Otomatik")
    parser.add_argument("--swing-only", action="store_true", help="Sadece swing trade güncelle")
    parser.add_argument("--portfolios-only", action="store_true", help="Sadece portföyleri güncelle")
    args = parser.parse_args()
    
    print("=" * 70)
    print("🚀 TAM OTOMATİK GÜNCELLEME SİSTEMİ")
    print("=" * 70)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Portföy güncelleme
    if not args.swing_only:
        portfolio_results = {}
        for name, display_name in PORTFOLIOS.items():
            try:
                result = update_portfolio(name, display_name)
                portfolio_results[name] = result
            except Exception as e:
                print(f"\n❌ {display_name} güncellenirken hata: {e}")
        
        if portfolio_results:
            generate_portfolio_summary(portfolio_results)
    
    # Swing trade güncelleme
    if not args.portfolios_only:
        try:
            update_swing_positions()
        except Exception as e:
            print(f"\n❌ Swing trade güncellenirken hata: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print("✅ TÜM GÜNCELLEMELER TAMAMLANDI")
    print("=" * 70)


if __name__ == "__main__":
    main()
