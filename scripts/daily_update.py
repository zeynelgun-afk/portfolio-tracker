#!/usr/bin/env python3
"""
OTOMATIK GÜNLÜK FİYAT GÜNCELLEMESİ
Her gün piyasa kapanışında çalıştırılmalı (NYSE kapanış: TR 23:00)
Tüm portföyleri, swing trade'leri, watchlist'i günceller
"""

import json
import os
import sys
import requests
from datetime import datetime, timedelta
import subprocess
from pathlib import Path

# ====== KONFIGURASYON ======
FMP_API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE = "https://financialmodelingprep.com/stable"
REPO_ROOT = Path(__file__).parent.parent  # portfolio-tracker kök dizini

# Dosya yolları
BALANCED_JSON = REPO_ROOT / "data/portfolios/balanced.json"
AGGRESSIVE_JSON = REPO_ROOT / "data/portfolios/growth.json  # aggressive→growth"
DIVIDEND_JSON = REPO_ROOT / "data/portfolios/dividend.json"
SWING_ACTIVE_JSON = REPO_ROOT / "data/swing/active.json"
WATCHLIST_JSON = REPO_ROOT / "data/watchlist.json"
SUMMARY_JSON = REPO_ROOT / "data/summary.json"
LOG_FILE = REPO_ROOT / "logs/daily_update.log"

# ====== YARDIMCI FONKSİYONLAR ======

def log(message):
    """Log mesajını hem konsola hem dosyaya yaz"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    # Log klasörünü oluştur
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def fmp_get(endpoint, params=None):
    """FMP API'den veri çek"""
    if params is None:
        params = {}
    params['apikey'] = FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict) and 'Error Message' in data:
            log(f"❌ FMP Error: {data['Error Message']}")
            return None
        
        return data
    except requests.exceptions.RequestException as e:
        log(f"❌ Request failed for {endpoint}: {e}")
        return None


def get_batch_quotes(symbols):
    """Birden fazla sembol için fiyat çek"""
    symbols_str = ','.join(symbols)
    log(f"📊 Batch quote çekiliyor: {len(symbols)} sembol")
    
    quotes = fmp_get("batch-quote", {"symbols": symbols_str})
    
    if not quotes:
        log("❌ Batch quote başarısız!")
        return {}
    
    # Dict'e dönüştür (sembol -> quote)
    quote_dict = {q['symbol']: q for q in quotes}
    log(f"✅ {len(quote_dict)} sembol fiyatı alındı")
    
    return quote_dict


def load_json(filepath):
    """JSON dosyasını yükle"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log(f"⚠️  Dosya bulunamadı: {filepath}")
        return None
    except json.JSONDecodeError as e:
        log(f"❌ JSON parse hatası {filepath}: {e}")
        return None


def save_json(filepath, data):
    """JSON dosyasını kaydet"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"💾 Kaydedildi: {filepath.name}")
        return True
    except Exception as e:
        log(f"❌ Kaydetme hatası {filepath}: {e}")
        return False


def update_portfolio(filepath, quote_dict):
    """Bir portföy dosyasını güncelle"""
    portfolio = load_json(filepath)
    if not portfolio:
        return False
    
    portfolio_name = portfolio.get('portfoy_adi', filepath.stem)
    log(f"\n📂 {portfolio_name} güncelleniyor...")
    
    now = datetime.now().isoformat()
    updated_count = 0
    
    for pos in portfolio.get('pozisyonlar', []):
        symbol = pos['sembol']
        
        if symbol not in quote_dict:
            log(f"  ⚠️  {symbol}: fiyat bulunamadı")
            continue
        
        quote = quote_dict[symbol]
        old_price = pos.get('guncel_fiyat', 0)
        new_price = quote['price']
        
        # Fiyatları güncelle
        pos['guncel_fiyat'] = new_price
        pos['gunluk_degisim_yuzde'] = quote.get('changesPercentage', 0)
        
        # Hesaplamaları güncelle
        pos['guncel_deger'] = pos['adet'] * new_price
        pos['kar_zarar'] = pos['guncel_deger'] - pos['yatirim']
        pos['kar_zarar_yuzde'] = round((pos['kar_zarar'] / pos['yatirim']) * 100, 2)
        pos['son_guncelleme'] = now
        
        change = ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
        log(f"  ✅ {symbol}: ${old_price:.2f} → ${new_price:.2f} ({change:+.2f}%)")
        updated_count += 1
    
    # Toplam değer hesapla
    total_position_value = sum(pos['guncel_deger'] for pos in portfolio['pozisyonlar'])
    cash = portfolio.get('nakit', {}).get('miktar', 0)
    portfolio['toplam_deger'] = round(total_position_value + cash, 2)
    
    # Toplam getiri hesapla
    starting_capital = portfolio.get('baslangic_sermaye', 100000)
    portfolio['toplam_getiri_yuzde'] = round(
        ((portfolio['toplam_deger'] - starting_capital) / starting_capital) * 100, 2
    )
    
    # Ağırlıkları yeniden hesapla
    for pos in portfolio['pozisyonlar']:
        pos['agirlik_yuzde'] = round(
            (pos['guncel_deger'] / portfolio['toplam_deger']) * 100, 2
        )
    
    portfolio['son_guncelleme'] = now
    
    log(f"  💰 Toplam değer: ${portfolio['toplam_deger']:,.2f} ({portfolio['toplam_getiri_yuzde']:+.2f}%)")
    log(f"  📊 {updated_count}/{len(portfolio['pozisyonlar'])} pozisyon güncellendi")
    
    return save_json(filepath, portfolio)


def update_swing_trades(quote_dict):
    """Swing trade pozisyonlarını güncelle"""
    swing = load_json(SWING_ACTIVE_JSON)
    if not swing:
        return False
    
    log(f"\n🎯 Swing Trade güncelleniyor...")
    
    now = datetime.now().isoformat()
    today = datetime.now().date()
    updated_count = 0
    
    for pos in swing.get('aktif_pozisyonlar', []):
        symbol = pos['sembol']
        
        if symbol not in quote_dict:
            log(f"  ⚠️  {symbol}: fiyat bulunamadı")
            continue
        
        quote = quote_dict[symbol]
        old_price = pos.get('guncel_fiyat', 0)
        new_price = quote['price']
        
        # Fiyat güncelle
        pos['guncel_fiyat'] = new_price
        
        # Kar/zarar hesapla
        entry_price = pos['giris_fiyati']
        pos['guncel_kar_zarar_yuzde'] = round(
            ((new_price - entry_price) / entry_price) * 100, 2
        )
        
        # Tutulan gün hesapla
        entry_date = datetime.strptime(pos['giris_tarihi'], '%Y-%m-%d').date()
        pos['tutulan_gun'] = (today - entry_date).days
        
        # Stop-loss / hedef kontrolü
        stop_distance = ((new_price - pos['stop_loss']) / pos['stop_loss']) * 100
        target_distance = ((pos['hedef_fiyat'] - new_price) / new_price) * 100
        
        # Durum güncelle
        if new_price <= pos['stop_loss']:
            pos['durum'] = "🔴 STOP-LOSS TETİKLENDİ!"
        elif new_price >= pos['hedef_fiyat']:
            pos['durum'] = "🎯 HEDEF ULAŞILDI!"
        elif stop_distance < 2:
            pos['durum'] = f"⚠️ Stop-loss yakın ({stop_distance:.1f}%)"
        elif target_distance < 5:
            pos['durum'] = f"🎯 Hedefe yakın ({target_distance:.1f}%)"
        else:
            pos['durum'] = "✅ Normal aralıkta"
        
        pos['son_guncelleme'] = now
        
        change = ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
        log(f"  ✅ {symbol}: ${old_price:.2f} → ${new_price:.2f} ({change:+.2f}%) | P&L: {pos['guncel_kar_zarar_yuzde']:+.2f}% | {pos['durum']}")
        updated_count += 1
    
    swing['son_guncelleme'] = now
    
    log(f"  📊 {updated_count}/{len(swing.get('aktif_pozisyonlar', []))} swing pozisyon güncellendi")
    
    return save_json(SWING_ACTIVE_JSON, swing)


def update_watchlist(quote_dict):
    """Watchlist'i güncelle"""
    watchlist = load_json(WATCHLIST_JSON)
    if not watchlist:
        return False
    
    log(f"\n👁️  Watchlist güncelleniyor...")
    
    now = datetime.now().isoformat()
    updated_count = 0
    
    for candidate in watchlist.get('izleme_listesi', []):
        symbol = candidate['sembol']
        
        if symbol not in quote_dict:
            log(f"  ⚠️  {symbol}: fiyat bulunamadı")
            continue
        
        quote = quote_dict[symbol]
        old_price = candidate.get('guncel_fiyat', 0)
        new_price = quote['price']
        
        candidate['guncel_fiyat'] = new_price
        
        # 5 günlük momentum hesapla
        candidate['momentum_5gun'] = quote.get('changesPercentage', 0)
        
        candidate['son_kontrol'] = datetime.now().strftime('%Y-%m-%d')
        
        change = ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
        log(f"  ✅ {symbol}: ${old_price:.2f} → ${new_price:.2f} ({change:+.2f}%)")
        updated_count += 1
    
    watchlist['son_guncelleme'] = now
    
    log(f"  📊 {updated_count}/{len(watchlist.get('izleme_listesi', []))} watchlist adayı güncellendi")
    
    return save_json(WATCHLIST_JSON, watchlist)


def update_summary():
    """Summary dosyasını güncelle"""
    log(f"\n📋 Summary güncelleniyor...")
    
    balanced = load_json(BALANCED_JSON)
    aggressive = load_json(AGGRESSIVE_JSON)
    dividend = load_json(DIVIDEND_JSON)
    swing = load_json(SWING_ACTIVE_JSON)
    
    if not all([balanced, aggressive, dividend]):
        log("❌ Portföy dosyaları yüklenemedi!")
        return False
    
    # Toplam değerleri hesapla
    total_capital = 600000  # $100K + $400K + $100K
    total_value = balanced['toplam_deger'] + aggressive['toplam_deger'] + dividend['toplam_deger']
    total_pnl = total_value - total_capital
    total_pnl_pct = (total_pnl / total_capital) * 100
    
    summary = {
        "son_guncelleme": datetime.now().strftime('%Y-%m-%d'),
        "toplam_sermaye": total_capital,
        "toplam_deger": round(total_value, 2),
        "toplam_kar_zarar": round(total_pnl, 2),
        "toplam_kar_zarar_yuzde": round(total_pnl_pct, 2),
        "portfolyolar": {
            "dengeli": {
                "isim": "Dengeli Portföy",
                "deger": balanced['toplam_deger'],
                "maliyet": balanced['baslangic_sermaye'],
                "kar_zarar": balanced['toplam_deger'] - balanced['baslangic_sermaye'],
                "kar_zarar_yuzde": balanced['toplam_getiri_yuzde'],
                "pozisyon_sayisi": len(balanced['pozisyonlar']),
                "nakit": balanced.get('nakit', {"miktar": 0})
            },
            "agresif": {
                "isim": "Agresif Büyüme Portföyü",
                "deger": aggressive['toplam_deger'],
                "maliyet": aggressive['baslangic_sermaye'],
                "kar_zarar": aggressive['toplam_deger'] - aggressive['baslangic_sermaye'],
                "kar_zarar_yuzde": aggressive['toplam_getiri_yuzde'],
                "pozisyon_sayisi": len(aggressive['pozisyonlar']),
                "nakit": aggressive.get('nakit', {"miktar": 0})
            },
            "temettü": {
                "isim": "Değer + Temettü Portföyü",
                "deger": dividend['toplam_deger'],
                "maliyet": dividend['baslangic_sermaye'],
                "kar_zarar": dividend['toplam_deger'] - dividend['baslangic_sermaye'],
                "kar_zarar_yuzde": dividend['toplam_getiri_yuzde'],
                "pozisyon_sayisi": len(dividend['pozisyonlar']),
                "nakit": dividend.get('nakit', {"miktar": 0})
            },
            "swing_trade": {
                "isim": "Swing Trade (Simülasyon)",
                "pozisyon_sayisi": len(swing.get('aktif_pozisyonlar', [])),
                "bos_slot": 10 - len(swing.get('aktif_pozisyonlar', [])),
                "durum": f"{len(swing.get('aktif_pozisyonlar', []))}/10 pozisyon aktif"
            }
        }
    }
    
    log(f"  💰 Toplam portföy değeri: ${total_value:,.2f} ({total_pnl_pct:+.2f}%)")
    
    return save_json(SUMMARY_JSON, summary)


def git_commit_and_push(message):
    """Git commit ve push yap"""
    log(f"\n🔄 Git commit yapılıyor...")
    
    try:
        os.chdir(REPO_ROOT)
        
        # Git add
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Git commit
        commit_result = subprocess.run(
            ['git', 'commit', '-m', message],
            capture_output=True,
            text=True
        )
        
        if commit_result.returncode == 0:
            log(f"  ✅ Commit başarılı: {message}")
            
            # Git push
            push_result = subprocess.run(
                ['git', 'push'],
                capture_output=True,
                text=True
            )
            
            if push_result.returncode == 0:
                log(f"  ✅ Push başarılı!")
                return True
            else:
                log(f"  ❌ Push hatası: {push_result.stderr}")
                return False
        else:
            # "nothing to commit" durumu
            if "nothing to commit" in commit_result.stdout:
                log(f"  ℹ️  Değişiklik yok, commit atlandı")
                return True
            else:
                log(f"  ❌ Commit hatası: {commit_result.stderr}")
                return False
    
    except subprocess.CalledProcessError as e:
        log(f"  ❌ Git işlemi başarısız: {e}")
        return False


# ====== ANA FONKSİYON ======

def main():
    """Ana güncelleme fonksiyonu"""
    log("\n" + "="*60)
    log("🚀 OTOMATIK FİYAT GÜNCELLEMESİ BAŞLATILIYOR")
    log("="*60)
    
    # Tüm sembolleri topla
    all_symbols = set()
    
    # Portföy sembolleri
    for filepath in [BALANCED_JSON, AGGRESSIVE_JSON, DIVIDEND_JSON]:
        portfolio = load_json(filepath)
        if portfolio:
            all_symbols.update(pos['sembol'] for pos in portfolio.get('pozisyonlar', []))
    
    # Swing trade sembolleri
    swing = load_json(SWING_ACTIVE_JSON)
    if swing:
        all_symbols.update(pos['sembol'] for pos in swing.get('aktif_pozisyonlar', []))
    
    # Watchlist sembolleri
    watchlist = load_json(WATCHLIST_JSON)
    if watchlist:
        all_symbols.update(c['sembol'] for c in watchlist.get('izleme_listesi', []))
    
    log(f"\n📊 Toplam {len(all_symbols)} sembol güncelleniyor:")
    log(f"   {', '.join(sorted(all_symbols))}")
    
    # Batch quote çek
    quote_dict = get_batch_quotes(list(all_symbols))
    
    if not quote_dict:
        log("\n❌ FMP API'den fiyat alınamadı! Güncelleme iptal edildi.")
        sys.exit(1)
    
    # Her şeyi güncelle
    success = True
    success &= update_portfolio(BALANCED_JSON, quote_dict)
    success &= update_portfolio(AGGRESSIVE_JSON, quote_dict)
    success &= update_portfolio(DIVIDEND_JSON, quote_dict)
    success &= update_swing_trades(quote_dict)
    success &= update_watchlist(quote_dict)
    success &= update_summary()
    
    if not success:
        log("\n⚠️  Bazı dosyalar güncellenemedi!")
    
    # Git commit + push
    commit_message = f"[GÜNCELLEME] Otomatik fiyat güncellemesi - {datetime.now().strftime('%d %b %Y %H:%M')}"
    git_commit_and_push(commit_message)
    
    log("\n" + "="*60)
    log("✅ GÜNCELLEME TAMAMLANDI")
    log("="*60 + "\n")


if __name__ == "__main__":
    main()
