# 🤖 GÜNLÜK RAPOR OTOMASYONU - KURULUM

3 farklı otomasyon seçeneği mevcut.

---

## ⚡ SEÇENEK 1: MANUEL (ÖNERİLEN - EN KOLAY)

**Nasıl Çalışır:**
Her gün saat 14:00'te Claude'a mesaj at:
```
Günlük rapor
```

**Artıları:**
- ✅ Kurulum yok
- ✅ Şimdi kullanıma hazır
- ✅ Esneklik (erken/geç yapabilirsin)
- ✅ Hata kontrolü yapabilirsin

**Eksileri:**
- ❌ Her gün mesaj atman gerekiyor

**Süreç:**
1. Sen: "Günlük rapor"
2. Claude: FMP API + Web Search → Rapor oluştur
3. Claude: `reports/daily/GUNLUK_RAPOR_2026_02_20.md`
4. Claude: Git commit + push
5. Bitti! (2-3 dakika)

---

## 🔘 SEÇENEK 2: GITHUB ACTIONS (MANUEL BUTON)

**Nasıl Çalışır:**
GitHub'da "Run workflow" butonuna bas, rapor oluşur.

**Artıları:**
- ✅ Claude'a mesaj atmana gerek yok
- ✅ GitHub'da tek tıkla
- ✅ Zaman esnekliği

**Eksileri:**
- ⚠️ GitHub'a FMP API Key eklemen gerekiyor
- ❌ Her gün butona basman gerekiyor

**Kurulum Adımları:**

### 1. GitHub Secrets'a API Key Ekle

a. GitHub reposuna git:  
   `https://github.com/zeynelgun-afk/portfolio-tracker`

b. Settings → Secrets and variables → Actions

c. "New repository secret" tıkla:
   - Name: `FMP_API_KEY`
   - Value: `g1GFJZtV5rCP49UCir4WuP56VjhmA6F8`

### 2. Workflow'u Aktif Et

Workflow'lar zaten GitHub'a yüklendi:
- `.github/workflows/manual-daily-report.yml`

### 3. Kullan

a. GitHub'da Actions sekmesine git

b. "📊 Günlük Rapor (Manuel)" workflow'unu seç

c. "Run workflow" butonuna tıkla

d. Rapor otomatik oluşur ve commit edilir

---

## 🤖 SEÇENEK 3: GITHUB ACTIONS (TAM OTOMATİK)

**Nasıl Çalışır:**
Her gün saat 14:00 TR'de otomatik çalışır.

**Artıları:**
- ✅ Tamamen otomatik
- ✅ Hiçbir şey yapman gerekmiyor
- ✅ Her gün düzenli rapor

**Eksileri:**
- ⚠️ GitHub Secrets kurulum gerekli
- ⚠️ Public repo'da ücretsiz, private'da GitHub Pro gerekli
- ⚠️ GitHub Actions bazen birkaç dakika gecikmeli çalışabilir

**Kurulum Adımları:**

### 1. API Key Ekle (Seçenek 2'deki gibi)

Settings → Secrets → `FMP_API_KEY`

### 2. Workflow Zaten Aktif

- `.github/workflows/scheduled-daily-report.yml`
- Cron: `0 11 * * *` (11:00 UTC = 14:00 TR)

### 3. İlk Çalışma

- Yarın saat 14:00'te otomatik çalışır
- Rapor: `reports/daily/GUNLUK_RAPOR_2026_02_21.md`
- Otomatik commit edilir

### 4. Kontrol Et

GitHub → Actions sekmesinde çalışmaları görebilirsin.

---

## 📊 KARŞILAŞTIRMA

| Özellik | Manuel | Buton | Otomatik |
|---------|--------|-------|----------|
| Kurulum | Yok | Orta | Orta |
| Günlük iş | Mesaj at | Buton bas | Hiçbir şey |
| Esneklik | Yüksek | Yüksek | Düşük |
| Güvenilirlik | Yüksek | Yüksek | Orta |
| Maliyet | Ücretsiz | Ücretsiz | Ücretsiz* |

*Private repo'da GitHub Pro gerekli

---

## ✅ ÖNERİ

**Başlangıç için:** SEÇENEK 1 (Manuel)
- En basit
- Şimdi kullanıma hazır
- Sistemi öğren

**Sonra:** SEÇENEK 3 (Otomatik)
- API Key ekle
- Tamamen hands-off
- Düzenli raporlar

---

## 🔧 SORUN GİDERME

### GitHub Actions çalışmıyor:

1. **Secrets kontrol et:**
   - Settings → Secrets → `FMP_API_KEY` var mı?

2. **Actions aktif mi:**
   - Settings → Actions → "Allow all actions" seçili mi?

3. **Workflow dosyaları doğru mu:**
   - `.github/workflows/` klasörü var mı?

4. **Log'lara bak:**
   - Actions sekmesinde başarısız çalışmanın logunu oku

### Python script hatası:

```bash
# Local test
cd portfolio-tracker
python3 scripts/generate_daily_report.py
```

Hata varsa log'u kontrol et.

---

**Son Güncelleme:** 20 Şubat 2026  
**Versiyon:** 1.0
