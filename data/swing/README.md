# 🎯 SWING TRADE SİSTEMİ

**Son Güncelleme:** 19 Şubat 2026  
**Versiyon:** 2.0 - Trailing Stop Aktif

---

## 📋 KURALLAR

### ✅ **YENİ SİSTEM:**

#### **1. ❌ ZAMAN KISITLAMASI YOK**
- 10 gün sınırı kaldırıldı
- Pozisyon trend devam ettikçe açık kalır
- Trailing stop ile yönetilir

#### **2. ✅ TRAİLİNG STOP AKTİF**
- **%5 kar** → Otomatik trailing aktive
- Stop break-even'e çekilir
- **Her yeni zirve** → Stop %3 aşağı güncellenir
- Stop **sadece yukarı** çekilir (aşağı inmez)

#### **3. ✅ GÜNLÜK KONTROL**
- Her gün script çalıştır
- Fiyatları güncelle
- Trailing stop'u güncelle

#### **4. ✅ ÇIKIŞ KURALLARI**
```
🎯 Target vurdu (%10)     → SAT
🛑 Stop-loss vurdu (%5)   → KES
📈 Trailing stop vurdu    → SAT (dinamik kar)
```

---

## 🔧 TRAİLİNG STOP MEKANİZMASI

### **Örnek Senaryo:**

```
Gün 1:  Giriş $100
Gün 3:  $105 (+5%) → Trailing aktive, stop $100 (break-even)
Gün 5:  $110 (+10%) → Stop güncellenir: $106.70 (+3% trailing)
Gün 7:  $108 (-1.8%) → Stop hala $106.70, pozisyon açık
Gün 8:  $106.50 → STOP VURDU! Kapatıldı, net kar: +6.5%
```

### **Formül:**
```python
if kar >= %5:
    trailing_aktive = True
    en_yuksek_fiyat = max(en_yuksek_fiyat, guncel_fiyat)
    trailing_stop = en_yuksek_fiyat * 0.97  # %3 aşağı
    
    if trailing_stop > mevcut_stop:
        stop = trailing_stop  # Sadece yukarı çek
```

---

## 📊 MAKSİMUM POZİSYON

- **Maksimum:** 10 eşzamanlı pozisyon
- **Miktar:** $5K-10K per trade
- **Risk:** Toplam portföyün %5'i

---

## 📁 DOSYALAR

### **active.json**
Aktif pozisyonlar ve güncel durumları

**Yeni Alanlar:**
- `en_yuksek_fiyat` → Trailing için peak tracking
- `tutulan_gun` → Kaç gün açık
- `durum` → Trailing aktif mi

### **closed.json**
Kapatılmış pozisyonlar ve istatistikler

**Otomatik İstatistikler:**
- Kazanma oranı
- Ortalama K/Z
- En iyi/kötü trade

### **watchlist.json**
Potansiyel adaylar

---

## 🤖 OTOMASYON

### **Günlük Rutin:**
```bash
python3 scripts/update_all_portfolios.py
```

**Ne yapar:**
1. Fiyatları günceller
2. Trailing stop kontrol eder
3. Stop/target vurdu mu kontrol eder
4. Otomatik kapatır
5. Action items raporlar

---

## 📈 AVANTAJLAR

### **Eski Sistem (Zaman Kısıtlaması):**
```
❌ 10 gün sonra zorla çık
❌ Kar devam ederken kes
❌ Trend takibi yok
❌ Fırsat kaybı
```

### **Yeni Sistem (Trailing Stop):**
```
✅ Trend devam ettikçe tut
✅ Kar sınırsız
✅ Zarar sınırlı (%5 max)
✅ Otomatik kar koruma
```

---

## 🎯 ÖRNEK TRADE

**NEM - 19 Şubat 2026:**
```
Giriş:   $118.12 (12 Şub)
Güncel:  $124.69 (+5.6%)
Stop:    $120.95 (trailing aktive)
Peak:    $124.69

✅ Kar garanti: +2.4% minimum
✅ Yukarı potansiyel: Sınırsız
✅ Aşağı risk: %3 (trailing)
```

---

## 💡 DİKKAT

- **Manuel müdahale:** İstediğin zaman çıkabilirsin
- **Fundamental bozulma:** Tez bozulursa bekle-me, çık
- **Günlük kontrol:** Script her gün çalıştır
- **Disiplin:** Sisteme güven, duygusal karar verme

---

**Yazar:** Zeynel  
**Versiyon:** 2.0  
**Tarih:** 19 Şubat 2026
