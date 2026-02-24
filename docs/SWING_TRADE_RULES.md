# SWING TRADE KURALLARI

> son güncelleme: 24 şubat 2026

## giriş kriterleri

- güçlü momentum: son 5 gün +%3 üzeri
- volume artışı: ortalama volume'ün 1.2x+ üzeri
- market cap: minimum $2B
- maksimum eşzamanlı pozisyon: 10
- tavsiye tutma süresi: 7-10 gün (kesin üst limit yok — trailing stop ile yönetilir)

## çıkış stratejisi (hibrit yaklaşım)

### 1. hedef fiyata ulaşınca (+%10)

**%50 pozisyonu sat** — kar garantiye al, risk/reward iyileşir

**kalan %50 → trailing stop** — zirveden -%5, momentum devam ederse ekstra kazanç

### 2. stop-loss kırılırsa (-%5)

**%100 pozisyonu sat** — hemen çık, beklemeden. kayıp -%5 ile sınırlı

### 3. trailing stop nasıl çalışır?

trailing stop = fiyatı takip eden yükselen stop. fiyat yükseldikçe stop da yükselir, asla düşmez.

```
örnek: DVA
giriş: $149.73
hedef: $164.70 (+%10)
initial stop: $142.24 (-%5)

ADIM 1: hedef $164.70'e ulaştı
→ %50 sat: $164.70 (kar garantilendi)
→ trailing stop kur: $156.47 (hedeften -%5)

ADIM 2: fiyat yükselmeye devam ediyor
$170 → trailing stop: $161.50
$175 → trailing stop: $166.25
$180 → trailing stop: $171.00

ADIM 3: geri düşüş başladı
$180 → $177 → $174 → $171 → STOP TETİKLENDİ
→ kalan %50'yi $171'de sat

SONUÇ:
- ilk %50: $164.70'de (+%10)
- ikinci %50: $171'de (+%14.2)
- toplam ortalama: +%12.1 ✅
```

**önemli**: trailing stop sadece yukarı hareket eder, asla aşağı çekilmez. fiyat yeni zirve yaptıkça stop otomatik yükselir. bu yüzden kesin gün sınırı gerekmiyor — pozisyon kazandırdığı sürece trailing stop ile tutulur.

### 4. trailing stop aktifleşme kuralı

- +%5 kar → trailing stop aktifleşir (zirveden -%5)
- hedefe ulaşmamış ama karlı → trailing stop ile korunur
- hedefe ulaşmış → %50 sat + kalan trailing

## risk yönetimi

### pozisyon büyüklüğü
- her pozisyon: $5,000 - $10,000
- maksimum kayıp risk: $250-500 per trade
- total exposure: $50K-80K (8-10 pozisyon)

### stop-loss kuralları
- initial stop: girişten -%5
- ASLA stop-loss'u aşağı çekme
- yukarı çekmek serbest (trailing)
- stop kırılırsa: HEMEN SAT (duygusal karar yok)

### kar realizasyonu
- hedef +%10: %50 sat, %50 trail
- hızlı +%15: %75 sat, %25 trail
- +%20: %100 sat

## günlük checklist

sabah:
- [ ] stop-loss'ları kontrol et
- [ ] trailing stop'ları güncelle (dünün zirvesine göre)
- [ ] hedef fiyata yakın olanları işaretle

gün içi:
- [ ] stop/hedef alarmları aktif
- [ ] %50 sat/trail kararları hazır

akşam:
- [ ] güncel fiyatları kaydet
- [ ] trailing stop'ları ayarla
- [ ] yarın için plan yap

## prensipler

1. **kar garantiye al, sonra risk al** — hedefte %50 sat = garanti, kalan %50 trail = bonus
2. **kayıpları hızlı kes, kazananları sürdür** — stop -%5 acımadan kes, trailing ile momentum sürsün
3. **plan yap, plana uy** — giriş öncesi hedef/stop belirle, duygusal karar yok
4. **sermayeyi koru** — kayıp trade'leri kabul et, fırsat her zaman var

---

> tüm kurallar simülasyon amaçlıdır
