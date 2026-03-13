# 1 HAFTALIK TEST PLANI — Otomatik Güncelleme Sistemi

> **Test başlangıcı**: 28 Şubat 2026  
> **Test süresi**: 7 gün (1 tam hafta)  
> **Hedef**: Otomatik fiyat güncelleme sisteminin stabilitesini doğrulamak

---

## 🎯 TEST HEDEFLERİ

### ana hedefler
1. ✅ Workflow her 30 dakikada düzenli çalışıyor mu?
2. ✅ Fiyat güncellemeleri doğru mu?
3. ✅ Git commit/push hatasız çalışıyor mu?
4. ✅ FMP API limiti aşılıyor mu?
5. ✅ Log dosyası düzgün tutuluyor mu?

### başarı kriterleri
- **workflow başarı oranı**: >95%
- **fiyat doğruluğu**: manuel kontrollerde %100 match
- **git hatası**: haftada max 2 geçici hata (retry ile düzelir)
- **api kullanımı**: günlük <100 call (limit: 2500)

---

## 📅 GÜNLÜK KONTROL (5 dakika)

### her gün yapılacaklar (tercihen akşam 23:00-00:00)

#### 1. github actions kontrol (2 dk)
**url**: https://github.com/zeynelgun-afk/portfolio-tracker/actions

**kontrol listesi**:
- [ ] Bugün kaç workflow çalışmış? (beklenen: 14)
- [ ] Kaç tanesi başarılı ✅? (hedef: 13+/14)
- [ ] Başarısız ❌ varsa nedeni ne?

**kayıt**:
```
[28 Şubat] 1/1 başarılı (manuel test)
[1 Mart] __/14 başarılı
[2 Mart] __/14 başarılı
...
```

---

#### 2. hızlı sağlık kontrolü (1 dk)
```bash
cd /path/to/portfolio-tracker
python3 scripts/weekly_health_check.py
```

**beklenen çıktı**:
```
✅ Başarılı güncelleme: 1
❌ Hata sayısı: 0
✅ Tüm dosyalar <1 saat önce güncellendi
✅ API kullanımı %0.6
```

---

#### 3. spot check - rastgele 1 hisse (30 sn)

**örnek**: dengeli portföy, SM energy
1. `data/portfolios/balanced.json` aç
2. SM'in `guncel_fiyat` değerine bak: `$24.50`
3. google'da "SM stock price" ara
4. karşılaştır → fiyat ±$0.50 içinde mi?

**kayıt**:
```
[28 Şubat] SM: $24.50 (json) vs $24.48 (google) ✅
[1 Mart] KOS: $__.__ (json) vs $__.__ (google) ✅/❌
...
```

---

#### 4. summary quick look (10 sn)

`data/summary.json`:
```json
{
  "toplam_deger": 621335.53,
  "toplam_kar_zarar_yuzde": 3.56
}
```

**kontrol**:
- Toplam değer önceki güne göre makul değişim mi? (±5% içinde)
- Büyük sapma varsa (>5%) → detaylı kontrol et

---

## 📊 HAFTALIK ÖZET (pazar akşamı - 30 dakika)

### 1. workflow istatistikleri

| gün | beklenen | gerçekleşen | başarı oranı | notlar |
|-----|----------|-------------|--------------|--------|
| pazartesi | 14 | __ | __% | |
| salı | 14 | __ | __% | |
| çarşamba | 14 | __ | __% | |
| perşembe | 14 | __ | __% | |
| cuma | 14 | __ | __% | |
| **toplam** | **70** | **__** | **__%** | |

**hedef**: >95% başarı oranı

---

### 2. hata analizi

tüm haftadaki hataları topla:

**hata kategorileri**:
- FMP API timeout/hata: __ adet
- Git push conflict: __ adet
- Network timeout: __ adet
- Diğer: __ adet

**aksiyon gereken hatalar**:
- [ ] tekrarlayan hata var mı? (aynı hata 3+ kez)
- [ ] kalıcı çözüm gerekiyor mu?

---

### 3. fiyat doğruluğu raporu

hafta boyunca yapılan spot check'ler:

| gün | sembol | json fiyat | gerçek fiyat | fark | durum |
|-----|--------|------------|--------------|------|-------|
| 28 şub | SM | $24.50 | $24.48 | $0.02 | ✅ |
| 1 mart | KOS | $__.__ | $__.__ | $__.__ | ✅/❌ |
| ... | ... | ... | ... | ... | ... |

**doğruluk**: __/7 ✅ (__%)

---

### 4. api kullanım analizi

**toplam call (tahmini)**:
- günlük ortalama: __ call
- haftalık toplam: __ call
- limit: 2,500 call/gün

**durum**:
- [ ] güvenli (<500/gün) ✅
- [ ] dikkatli (500-1000/gün) ⚠️
- [ ] tehlikeli (>1000/gün) ❌

---

### 5. sorun tespiti

**bu hafta yaşanan sorunlar**:
1. ________________________________
2. ________________________________
3. ________________________________

**çözüm önerileri**:
1. ________________________________
2. ________________________________
3. ________________________________

---

## 🔍 DETEYLİ KONTROLLER (gerekirse)

### senaryo 1: workflow sürekli başarısız
**tetikleyici**: başarı oranı <90%

**adımlar**:
1. GitHub actions → başarısız workflow'a tıkla
2. "Commit and push changes (with retry)" step'ini aç
3. hatayı oku ve not al
4. github issue oluştur veya manuel düzelt

---

### senaryo 2: fiyatlar yanlış
**tetikleyici**: spot check'te %5+ fark

**adımlar**:
1. FMP API'yi manuel test et:
   ```bash
   curl "https://financialmodelingprep.com/stable/quote?symbol=SM&apikey=..."
   ```
2. API yanıtı doğru mu kontrol et
3. script'te bug var mı kontrol et
4. gerekirse script düzelt

---

### senaryo 3: dosyalar güncellenmiyor
**tetikleyici**: dosya tarihi >24 saat eski

**adımlar**:
1. GitHub actions → son 24 saate bak
2. hiç çalışma yok mu?
   - cron schedule kontrolü
   - github actions enabled mi?
3. çalışma var ama başarısız mı?
   - log'u oku
   - hatayı çöz

---

## 📝 TEST SONUÇ RAPORU (7. gün)

### özet

**sistem performansı**:
- Workflow başarı oranı: __%
- Fiyat doğruluk oranı: __%
- API kullanımı: __/2500 call

**genel değerlendirme**:
- [ ] sistem stabil ve production-ready ✅
- [ ] küçük düzeltmeler gerekiyor ⚠️
- [ ] majör sorunlar var, ek geliştirme lazım ❌

---

### sonraki adımlar

**eğer başarılı (>95%)**:
- [ ] alert sistemi ekle (telegram/email)
- [ ] backtest engine geliştir
- [ ] risk analytics dashboard

**eğer sorunlu (<95%)**:
- [ ] sorunları çöz
- [ ] 1 hafta daha test et
- [ ] dokümantasyon güncelle

---

### öğrenilen dersler

**iyi çalışanlar**:
1. ________________________________
2. ________________________________
3. ________________________________

**iyileştirilebilirler**:
1. ________________________________
2. ________________________________
3. ________________________________

---

## 🛠️ ARAÇLAR

### hızlı komutlar

```bash
# haftalık health check
python3 scripts/weekly_health_check.py

# manuel güncelleme (test için)
python3 scripts/daily_update.py

# log'un son 100 satırını oku
tail -100 logs/daily_update.log

# bugünkü güncellemeleri filtrele
grep "2026-02-28" logs/daily_update.log
```

---

### github actions url
https://github.com/zeynelgun-afk/portfolio-tracker/actions

### log dosyası
`logs/daily_update.log`

### kontrol dosyaları
- `data/summary.json`
- `data/portfolios/*.json`
- `data/swing/active.json`

---

## 📞 SORUN GİDERME

### sık karşılaşılan sorunlar

#### 1. "workflow çalışmıyor"
**çözüm**: github repo settings → actions → "allow all actions"

#### 2. "git push failed"
**çözüm**: otomatik retry var, 3 deneme sonra başarısız oluyorsa manuel pull/push

#### 3. "fmp api error"
**çözüm**: api key kontrol, günlük limit kontrol (2500 call)

#### 4. "dosya tarihi eski"
**çözüm**: github actions son çalışmayı kontrol, başarısız mı?

---

## ✅ TEST TAMAMLANDI MÜ?

**7 gün sonunda şu sorulara cevap verebiliyorsan test başarılı**:

- [ ] sistem hafta boyunca stabil çalıştı mı?
- [ ] fiyatlar doğru güncellendi mi?
- [ ] api limiti sorun olmadı mı?
- [ ] manuel müdahale gerekmedi mi?

**EVET** → sonraki adıma geç (alert sistemi)  
**HAYIR** → sorunları çöz, 1 hafta daha test et

---

**test başarılar!** 🚀
