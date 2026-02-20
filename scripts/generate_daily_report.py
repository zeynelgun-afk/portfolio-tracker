#!/usr/bin/env python3
"""
Günlük Rapor Oluşturucu
Her gün 14:00 TR (11:00 UTC) otomatik çalışır
"""

import os
import sys
import requests
from datetime import datetime, timedelta
import pytz

# API Key
FMP_API_KEY = os.environ.get('FMP_API_KEY', 'g1GFJZtV5rCP49UCir4WuP56VjhmA6F8')
BASE_URL = "https://financialmodelingprep.com/stable"

# Türkiye saati
TR_TZ = pytz.timezone('Europe/Istanbul')
now_tr = datetime.now(TR_TZ)

def fetch_news(endpoint, params=None):
    """FMP News API çağrısı"""
    if params is None:
        params = {}
    params['apikey'] = FMP_API_KEY
    
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {endpoint}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []

def generate_report():
    """Günlük raporu oluştur"""
    
    # Tarih aralığı (son 24 saat)
    yesterday = now_tr - timedelta(days=1)
    from_date = yesterday.strftime("%Y-%m-%d")
    to_date = now_tr.strftime("%Y-%m-%d")
    
    print(f"📊 Günlük Rapor Oluşturuluyor - {to_date}")
    print(f"Türkiye Saati: {now_tr.strftime('%H:%M:%S')}")
    
    # 1. Portföy haberleri
    print("\n1. Portföy haberlerini çekiyor...")
    portfolio_symbols = "SM,KOS,MO,RGLD,FCX,XLE"
    portfolio_news = fetch_news(
        f"news/stock",
        {"symbols": portfolio_symbols, "from": from_date, "to": to_date, "limit": 50}
    )
    
    # 2. Tech haberleri
    print("2. Tech haberlerini çekiyor...")
    tech_symbols = "AAPL,MSFT,GOOGL,AMZN,META,TSLA,NVDA"
    tech_news = fetch_news(
        f"news/stock",
        {"symbols": tech_symbols, "from": from_date, "to": to_date, "limit": 50}
    )
    
    # 3. Genel piyasa
    print("3. Genel piyasa haberlerini çekiyor...")
    general_news = fetch_news("news/general-latest", {"page": 0, "limit": 20})
    
    # 4. Rapor oluştur
    print("4. Rapor oluşturuluyor...")
    
    report_date = now_tr.strftime("%Y_%m_%d")
    report_filename = f"reports/daily/GUNLUK_RAPOR_{report_date}.md"
    
    # Rapor içeriği
    report = f"""# 📊 GÜNLÜK RAPOR - {now_tr.strftime('%d %B %Y').upper()}

*Hazırlandı: {now_tr.strftime('%H:%M')} TR ({now_tr.astimezone(pytz.UTC).strftime('%H:%M')} UTC)*

---

## 🔥 ÖZET

**Veri Kaynakları:**
- FMP News API: ✅ {len(portfolio_news) + len(tech_news)} şirket haberi
- FMP General News: ✅ {len(general_news)} genel haber
- Tarih Aralığı: {from_date} → {to_date}

---

## 📰 PORTFÖY HABERLERİ

"""
    
    # Portföy haberlerini sembol bazında grupla
    by_symbol = {}
    for news in portfolio_news:
        symbol = news.get('symbol', 'N/A')
        if symbol not in by_symbol:
            by_symbol[symbol] = []
        by_symbol[symbol].append(news)
    
    for symbol in ['SM', 'KOS', 'MO', 'RGLD', 'FCX', 'XLE']:
        if symbol in by_symbol and len(by_symbol[symbol]) > 0:
            report += f"\n### {symbol} ({len(by_symbol[symbol])} haber)\n\n"
            for news in by_symbol[symbol][:3]:  # İlk 3 haber
                report += f"**{news.get('title', 'N/A')}**\n"
                report += f"- Tarih: {news.get('publishedDate', 'N/A')}\n"
                report += f"- Kaynak: {news.get('site', 'N/A')}\n"
                report += f"- [Haberi Oku]({news.get('url', '#')})\n\n"
    
    # Tech haberleri
    report += "\n---\n\n## 💻 TECH GIANTS HABERLERİ\n\n"
    
    tech_by_symbol = {}
    for news in tech_news:
        symbol = news.get('symbol', 'N/A')
        if symbol not in tech_by_symbol:
            tech_by_symbol[symbol] = []
        tech_by_symbol[symbol].append(news)
    
    for symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA']:
        if symbol in tech_by_symbol and len(tech_by_symbol[symbol]) > 0:
            report += f"\n### {symbol} ({len(tech_by_symbol[symbol])} haber)\n\n"
            for news in tech_by_symbol[symbol][:2]:
                report += f"**{news.get('title', 'N/A')}**\n"
                report += f"- {news.get('publishedDate', 'N/A')} - [{news.get('site', 'N/A')}]({news.get('url', '#')})\n\n"
    
    # Genel haberler
    report += "\n---\n\n## 🌍 GENEL PİYASA HABERLERİ (Top 10)\n\n"
    for i, news in enumerate(general_news[:10], 1):
        report += f"{i}. **{news.get('title', 'N/A')}**\n"
        report += f"   - {news.get('publishedDate', 'N/A')} - [{news.get('site', 'N/A')}]({news.get('url', '#')})\n\n"
    
    # Footer
    report += f"""
---

## 📌 NOT

Bu rapor FMP Premium API kullanılarak otomatik oluşturulmuştur.

**Veri Kaynakları:**
- [FMP Stock News API](https://financialmodelingprep.com/stable/news/stock)
- [FMP General News API](https://financialmodelingprep.com/stable/news/general-latest)

**Oluşturulma Zamanı:** {now_tr.strftime('%d %B %Y %H:%M:%S')} TR

---

*Otomatik Rapor v1.0 - Portfolio Tracker*
"""
    
    # Dosyaya yaz
    os.makedirs("reports/daily", exist_ok=True)
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Rapor oluşturuldu: {report_filename}")
    print(f"   Portföy haberleri: {len(portfolio_news)}")
    print(f"   Tech haberleri: {len(tech_news)}")
    print(f"   Genel haberler: {len(general_news)}")
    
    return report_filename

if __name__ == "__main__":
    try:
        filename = generate_report()
        print(f"\n🎉 Başarılı! Rapor hazır: {filename}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
