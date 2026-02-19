# 📊 Portfolio Tracker Scripts

## 🚀 TAM OTOMATİK GÜNCELLEYİCİ

### `update_all_portfolios.py` ⭐ YENİ!

**4 Portföy + Swing Trade otomasyonu tek scriptte!**

```bash
# HER ŞEYİ GÜNCELLE (önerilen)
python3 scripts/update_all_portfolios.py

# Sadece swing trade kontrol et
python3 scripts/update_all_portfolios.py --swing-only

# Sadece portföyleri güncelle
python3 scripts/update_all_portfolios.py --portfolios-only
```

---

## 📋 ÖZELLİKLER

### 1️⃣ **4 Portföy Güncelleme**
- Balanced (Dengeli)
- Aggressive (Agresif Büyüme)
- Dividend (Değer + Temettü)
- Rotation (Sektör Rotasyonu)

**Ne yapar:**
- FMP API'den güncel fiyatları çeker
- Her pozisyon için K/Z hesaplar
- Portföy dosyalarını günceller
- Karşılaştırmalı özet rapor üretir

### 2️⃣ **Swing Trade Otomasyonu** 🔥 YENİ!

**OTOMATİK KONTROLLER:**
- ✅ Stop-loss vurdu mu? → Otomatik kapat
- ✅ Target vurdu mu? → Otomatik kapat
- ✅ 10 gün aşıldı mı? → Otomatik kapat
- ✅ +5% karlı mı? → Trailing stop aktive et

**Ne yapar:**
- `active.json`'daki tüm pozisyonları kontrol eder
- Güncel fiyatları çeker
- Exit koşullarını kontrol eder
- Otomatik olarak `closed.json`'a taşır
- İstatistikleri günceller
- Action items rapor eder

**EXIT KURALLARI:**
```
🎯 Target Hit:      %10 hedefe ulaştı → SAT
🛑 Stop Hit:        %5 stop'a düştü → KES
⏰ Timeframe Aşımı: 10 gün geçti → DEĞERLENDIR
📈 Trailing Stop:   %5 karlı → Break-even'e çek
```

---

## 📊 ÖRNEK ÇIKTI

### Portföy Özeti:
```
Portföy               Başlangıç     Güncel      K/Z %    Durum
────────────────────────────────────────────────────────────
Dengeli Portföy      $100,000  $103,096.25   +3.10%  🟢 Başarılı
Agresif Büyüme       $100,000  $ 91,345.24   -8.65%  🔴 Kayıpda
Değer + Temettü      $100,000  $112,351.42  +12.35%  🟢 Başarılı
Sektör Rotasyonu     $100,000  $105,105.40   +5.11%  🟢 Başarılı
────────────────────────────────────────────────────────────
TOPLAM               $400,000  $411,898.31   +2.97%  🟢
```

### Swing Trade Özeti:
```
🎯 SWING TRADE OTOMATİK KONTROL
──────────────────────────────────────────────
  🔄 NEM... 🟢 $124.69 (+5.6%) İyi
  🔄 NVDA... 🟢 $187.98 (+0.6%) Normal
  🔄 AMT... 🔴 $186.62 (-3.4%) Stop yakın!
  🔄 GE... 🟢 $329.58 (+0.0%) Normal

🔴 OTOMATİK KAPATILAN POZİSYONLAR: 2
  ✅ XOM: +5.53% - Zaman çerçevesi aşıldı
  ✅ VZ: +3.89% - Zaman çerçevesi aşıldı

📋 SWING ÖZET
  Aktif Pozisyon: 7/10
  Kapatılan: 2
  Ortalama P/L: 🔴 -0.31%

  📊 TOPLAM İSTATİSTİKLER:
     Toplam İşlem: 8
     Kazanma Oranı: 75.0%
     Ortalama: +3.45%
```

---

## 🔄 GÜNLÜK RUTIN

**Önerilen kullanım: Her gün bir kez**

```bash
# Sabah piyasa açılışında
python3 scripts/update_all_portfolios.py

# Veya cron ile otomatik
0 16 * * 1-5 cd /path/to/repo && python3 scripts/update_all_portfolios.py
```

**Ne zaman çalıştırmalı:**
- 📊 Piyasa kapanışından sonra (güncel fiyatlar için)
- 🎯 Hafta içi her gün (otomatik exit kontrolü)
- 📈 Önemli piyasa hareketlerinde

---

## 📁 GÜNCELLENEN DOSYALAR

### Portföy Güncelleme:
- `data/portfolios/balanced.json`
- `data/portfolios/aggressive.json`
- `data/portfolios/dividend.json`
- `data/portfolios/rotation.json`
- `data/portfolio_summary.json`

### Swing Trade Güncelleme:
- `data/swing/active.json` → Fiyatlar, P/L, trailing stops
- `data/swing/closed.json` → Otomatik kapatılanlar
- İstatistikler otomatik güncellenir

---

## ⚙️ YAPILANDIRMA

Script içinde değiştirilebilir:

```python
SWING_RULES = {
    "target_pct": 10,              # %10 hedef
    "stop_pct": 5,                 # %5 stop
    "max_days": 10,                # 10 gün max
    "trailing_stop_trigger": 5     # %5'te trailing aktive
}
```

---

## 🎯 AVANTAJLAR

### Manuel Sistem:
- ❌ Her gün elle kontrol
- ❌ Stop-loss'u kaçırma riski
- ❌ Zaman disiplini ihlali
- ❌ İnsan hatası

### Otomatik Sistem:
- ✅ Otomatik günlük kontrol
- ✅ Stop-loss asla kaçırılmaz
- ✅ Zaman disiplini garanti
- ✅ İstatistik tracking
- ✅ Trailing stop otomatik
- ✅ Disiplinsizlik yok

---

## 🐛 SORUN GİDERME

### "requests module not found"
```bash
pip install requests --break-system-packages
```

### "FMP API hatası"
- API key kontrolü: `g1GFJZtV5rCP49UCir4WuP56VjhmA6F8`
- Rate limit: Dakikada 300 request

### "active.json bulunamadı"
```bash
# Dosya yolu kontrolü
ls -la data/swing/
```

---

## 📚 DAHA FAZLA BİLGİ

- Swing Trade Sistemi: `data/swing/README.md`
- Portfolio Yapısı: Ana `README.md`

---

**Son Güncelleme:** 19 Şubat 2026  
**Versiyon:** 2.0 - Swing Otomasyon  
**Dil:** Türkçe
