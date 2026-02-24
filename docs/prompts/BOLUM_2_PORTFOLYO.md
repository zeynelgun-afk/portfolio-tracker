# BÖLÜM 2: PORTFÖY TAKİBİ

> **amaç**: 4 portföyün güncel durumunu fiyat + teknik verilerle raporla, uyarıları işaretle
> **tahmini FMP call**: ~85-100 (benzersiz hisse sayısına bağlı)
> **tahmini websearch**: 0

---

## ADIM 1 — BENZERSİZ SEMBOL LİSTESİ ÇIKAR

aynı hisse birden fazla portföyde olabilir (MO, XLE, XLI gibi).
önce tüm portföylerden benzersiz sembol listesi çıkar, FMP call'ları tekrar etme.

```
mevcut benzersiz semboller (şubat 2026 itibarıyla):
dengeli:  SM, KOS, MO, XLE, RGLD, XLI
agresif:  GILT, BKSY, NNDM, PLTR, SHOP
temettü:  T, VZ, MO, PM, XOM, CVX, SCHD
rotasyon: XLE, XLV, XLI

benzersiz: SM, KOS, MO, XLE, RGLD, XLI, GILT, BKSY, NNDM, PLTR, SHOP,
           T, VZ, PM, XOM, CVX, SCHD, XLV
toplam: ~18 benzersiz sembol
```

⚠️ bu liste pozisyon açılıp kapandıkça değişir.
her çalıştırmada JSON dosyalarından dinamik olarak çıkar.

---

## ADIM 2 — VERİ TOPLAMA

her benzersiz sembol için 4 FMP call:

```python
for symbol in benzersiz_semboller:
    # 1. güncel fiyat (batch ile toplu çekilebilir → 1 call)
    # 2. RSI 14-günlük
    fmp_get("technical-indicators/rsi", {"symbol": symbol, "periodLength": 14, "timeframe": "1day"})
    # 3. SMA 50-günlük
    fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 50, "timeframe": "1day"})
    # 4. SMA 200-günlük
    fmp_get("technical-indicators/sma", {"symbol": symbol, "periodLength": 200, "timeframe": "1day"})
```

**optimizasyon:**
```python
# fiyatlar tek seferde (1 call)
batch-quote → symbols=SM,KOS,MO,XLE,RGLD,XLI,GILT,...

# haftalık değişim tek seferde (her biri 1 call ama batch yok)
# alternatif: batch-quote'taki previousClose'dan hesapla
# veya stock-price-change endpoint'i (sembol başı 1 call)
stock-price-change → symbol=SM   # 1D, 5D, 1M, 3M, ... hepsi döner
```

**call hesabı:**
- batch-quote: 1 call (tüm semboller)
- RSI: 18 call (sembol başı)
- SMA50: 18 call
- SMA200: 18 call
- stock-price-change: 18 call
- **toplam: ~73 call** (18 benzersiz sembol için)

---

## ADIM 3 — UYARI KURALLARI

her hisseyi şu kurallara göre işaretle:

```
GÜNLÜK HAREKET:
  günlük düşüş ≥ %3        → 🔴 SERT DÜŞÜŞ
  günlük düşüş %1.5-%3     → 🟡 düşüş
  günlük değişim -%1.5/+%1.5 arası → ⚪ nötr
  günlük yükseliş %1.5-%3  → 🟡 yükseliş
  günlük yükseliş ≥ %3     → 🟢 GÜÇLÜ YÜKSELİŞ

RSI:
  RSI > 70                  → ⚠️ AŞIRI ALIM — kar realizasyonu düşün
  RSI 60-70                 → dikkat, aşırı alıma yaklaşıyor
  RSI 40-60                 → nötr
  RSI 30-40                 → zayıf, izle
  RSI < 30                  → ⚠️ AŞIRI SATIM — fırsat olabilir

SMA POZİSYONU:
  fiyat > SMA50 > SMA200    → 📈 güçlü trend (tüm hareketli ortalamalar üzerinde)
  fiyat > SMA50, < SMA200   → 📊 toparlanma (kısa vade pozitif, uzun vade henüz değil)
  fiyat < SMA50, > SMA200   → 📉 kısa vadeli zayıflık (SMA50 altına düşmüş)
  fiyat < SMA50 < SMA200    → ⛔ düşüş trendi (her iki ortalama üzerinde)

ÖZEL DURUMLAR:
  fiyat SMA200'e %2'den yakın → 📌 KRİTİK SEVİYE — SMA200 test ediliyor
  SMA50 ile SMA200 arası %3'ten az → 📌 GOLDEN/DEATH CROSS yakın
  haftalık düşüş ≥ %5        → 🔴 HAFTALIK KAYIP uyarısı
```

---

## ADIM 4 — RAPOR ÇIKTI FORMATI

### her portföy için ayrı tablo + yorum

```markdown
## 2. portföy takibi

### genel özet

| portföy | değer | k/z $ | k/z % | nakit | nakit % | durum |
|---------|-------|-------|-------|-------|---------|-------|
| dengeli | $XXX,XXX | +$X,XXX | +%X.XX | $X,XXX | %XX | [emoji] |
| agresif | $XXX,XXX | -$X,XXX | -%X.XX | $XX,XXX | %XX | [emoji] |
| temettü | $XXX,XXX | +$XX,XXX | +%XX.XX | $XXX | %X | [emoji] 🏆 |
| rotasyon | $XXX,XXX | +$X,XXX | +%X.XX | $XXX | %X | [emoji] |
| **toplam** | **$XXX,XXX** | **+$XX,XXX** | **+%X.XX** | | | |

durum emojileri: 🟢 k/z > +%5 | 🟡 k/z %0-%5 | 🔴 k/z < %0

---

### 2a. dengeli portföy ($100K başlangıç)

| sembol | fiyat | günlük % | haftalık % | RSI | SMA50 | SMA200 | trend | k/z % | ağırlık | uyarı |
|--------|-------|----------|------------|-----|-------|--------|-------|-------|---------|-------|
| SM | $XX.XX | ▼ %X.XX | %X.XX | XX | $XX.XX | $XX.XX | 📈/📉 | +%X.XX | %XX | [varsa] |
| KOS | ... | | | | | | | | | |
| ... | | | | | | | | | | |

**portföy notu:** [2-3 cümle: bugün ne oldu, dikkat çeken hareket, varsa aksiyon önerisi]

**sektör dağılımı:** enerji %XX | temel tüketim %XX | emtia %XX | endüstriyel %XX | nakit %XX

---

### 2b. agresif büyüme ($100K başlangıç)

(aynı tablo formatı)

**portföy notu:** [2-3 cümle]
**nakit durumu:** $XX,XXX (%XX) — [yüksek nakit oranı değerlendirmesi]

---

### 2c. değer + temettü ($100K başlangıç) 🏆

(aynı tablo formatı)

**portföy notu:** [2-3 cümle]

---

### 2d. sektör rotasyonu ($100K başlangıç)

(aynı tablo formatı)

**portföy notu:** [2-3 cümle]
**sektör ağırlıkları:** XLE %XX | XLV %XX | XLI %XX | nakit %X

---

### uyarı özeti

tüm portföylerden uyarı gerektiren hisseleri topla:

🔴 **acil dikkat:**
- [SEMBOL] — [neden: stop yakın / sert düşüş / RSI aşırı / ...]

⚠️ **izlenmesi gereken:**
- [SEMBOL] — [neden]

🟢 **fırsat:**
- [SEMBOL] — [neden: RSI oversold / destek test / ...]
```

---

## ADIM 5 — AKSİYON ÖNERİLERİ

uyarılara göre somut aksiyon öner:

```
KURAL SETİ:

RSI > 75 + k/z > %20     → "kısmi kar realizasyonu düşünülebilir"
RSI < 30 + trend 📈      → "ek alım fırsatı olabilir (mevcut pozisyon varsa)"
RSI < 30 + trend ⛔      → "bıçak düşerken tutma, dip onayı bekle"
günlük -%5+              → "stop-loss kontrol et, panik satış yapma"
haftalık -%10+           → "tez bozuldu mu değerlendir, bozulduysa çık"
fiyat < SMA200 + RSI < 35 → "uzun vadeli destek kırılmış, dikkatli ol"
nakit > %50 (agresif)    → "piyasa netleşince kademeli giriş planla"
```

---

## ADIM 6 — KALİTE KONTROL

- [ ] tüm semboller güncel fiyatla güncellendi mi?
- [ ] k/z hesaplamaları tutarlı mı? (guncel_deger - yatirim)
- [ ] ağırlık yüzdeleri toplamı %100'e yakın mı? (nakit dahil)
- [ ] RSI ve SMA verileri bugüne ait mi?
- [ ] uyarı kuralları doğru uygulandı mı?
- [ ] her portföy notu spesifik mi? (genel laf değil, bugüne özel)
- [ ] JSON dosyaları güncellenip git push yapıldı mı?
