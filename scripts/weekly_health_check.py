#!/usr/bin/env python3
"""
HAFTALIK TEST KONTROL SCRIPTI
Otomatik güncelleme sisteminin sağlığını kontrol eder
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SUMMARY = REPO_ROOT / "data/summary.json"
LOG_FILE = REPO_ROOT / "logs/daily_update.log"

def check_summary():
    """Summary dosyasını kontrol et"""
    print("\n📊 SUMMARY KONTROLÜ")
    print("=" * 50)
    
    with open(SUMMARY, 'r') as f:
        data = json.load(f)
    
    print(f"Son güncelleme: {data['son_guncelleme']}")
    print(f"Toplam değer: ${data['toplam_deger']:,.2f}")
    print(f"Getiri: {data['toplam_kar_zarar_yuzde']:+.2f}%")
    print(f"\nPortföy detayları:")
    
    for key, portfolio in data['portfolyolar'].items():
        if key != 'swing_trade':
            print(f"  • {portfolio['isim']}: ${portfolio['deger']:,.2f} ({portfolio['kar_zarar_yuzde']:+.2f}%)")

def check_logs():
    """Log dosyasını kontrol et"""
    print("\n📝 LOG KONTROLÜ")
    print("=" * 50)
    
    if not LOG_FILE.exists():
        print("⚠️  Log dosyası bulunamadı!")
        return
    
    # Son 50 satır
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()[-50:]
    
    # Hata sayısı
    errors = [l for l in lines if '❌' in l or 'Error' in l or 'Failed' in l]
    successes = [l for l in lines if '✅ GÜNCELLEME TAMAMLANDI' in l]
    
    print(f"Son 50 satırda:")
    print(f"  ✅ Başarılı güncelleme: {len(successes)}")
    print(f"  ❌ Hata sayısı: {len(errors)}")
    
    if errors:
        print(f"\n⚠️  Hatalar:")
        for err in errors[-5:]:  # son 5 hata
            print(f"    {err.strip()}")

def check_file_dates():
    """Dosyaların son güncellenme tarihlerini kontrol et"""
    print("\n📅 DOSYA TARİHLERİ")
    print("=" * 50)
    
    files_to_check = [
        REPO_ROOT / "data/portfolios/balanced.json",
        REPO_ROOT / "data/portfolios/aggressive.json",
        REPO_ROOT / "data/portfolios/dividend.json",
        REPO_ROOT / "data/swing/active.json",
        REPO_ROOT / "data/watchlist.json",
        REPO_ROOT / "data/summary.json",
    ]
    
    now = datetime.now()
    
    for filepath in files_to_check:
        if filepath.exists():
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age = now - mtime
            
            status = "✅" if age < timedelta(hours=1) else "⚠️" if age < timedelta(days=1) else "❌"
            print(f"  {status} {filepath.name}: {age.seconds // 60} dakika önce")
        else:
            print(f"  ❌ {filepath.name}: BULUNAMADI")

def check_api_usage():
    """Tahmini API kullanımını hesapla"""
    print("\n📡 API KULLANIMI TAHMİNİ")
    print("=" * 50)
    
    # Her güncelleme 1 batch-quote call = 1 API call
    # Günde 14 güncelleme
    daily_calls = 14
    weekly_calls = daily_calls * 5  # pazartesi-cuma
    
    print(f"Günlük: ~{daily_calls} API call")
    print(f"Haftalık: ~{weekly_calls} API call")
    print(f"Limit: 2,500 call/gün")
    print(f"Kullanım: {(daily_calls/2500)*100:.1f}%")
    
    if daily_calls < 2500:
        print("✅ Limit içinde!")
    else:
        print("❌ Limit aşımı riski!")

def main():
    print("\n" + "=" * 50)
    print("🔍 OTOMATIK GÜNCELLEME SİSTEMİ - HAFTALIK KONTROL")
    print("=" * 50)
    
    try:
        check_summary()
        check_logs()
        check_file_dates()
        check_api_usage()
        
        print("\n" + "=" * 50)
        print("✅ KONTROL TAMAMLANDI")
        print("=" * 50)
        print("\nSONRAKİ ADIM:")
        print("1. GitHub Actions sayfasını kontrol et:")
        print("   https://github.com/zeynelgun-afk/portfolio-tracker/actions")
        print("2. Bugün yeşil ✅ çalışmalar var mı?")
        print("3. Kırmızı ❌ varsa log'u oku")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")

if __name__ == "__main__":
    main()
