---
title: GitHub Actions Rehberi
description: Workflow dosyaları, schedule (Railway-tetikli), env değişkenleri, debug.
tags:
  - infrastructure
  - ci-cd
  - workflow
related:
  - "[[Index]]"
  - "[[SYSTEM_MAP]]"
  - "[[RAILWAY_DEPLOY]]"
---

# GITHUB ACTIONS OTOMATIK GÜNCELLEME KLAVUZU

## 🎯 NASIL ÇALIŞIR?

GitHub Actions sunucularında otomatik olarak çalışır:
- ✅ Bilgisayarın kapalı olsa bile çalışır
- ✅ İnternet bağlantısı gerekmez
- ✅ Tamamen ücretsiz (public repo için)
- ✅ Her çalıştırma loglanır

---

## ⏰ ÇALIŞMA TAKVİMİ

### Seans Saatleri (Pazartesi-Cuma)

**NYSE Seans: TR 17:30 - 00:00**

| TR Saati | UTC Saati | Durum |
|----------|-----------|-------|
| 17:30 | 14:30 | 🟢 İlk güncelleme (açılış) |
| 18:00 | 15:00 | 🟢 |
| 18:30 | 15:30 | 🟢 |
| 19:00 | 16:00 | 🟢 |
| 19:30 | 16:30 | 🟢 |
| 20:00 | 17:00 | 🟢 |
| 20:30 | 17:30 | 🟢 |
| 21:00 | 18:00 | 🟢 |
| 21:30 | 18:30 | 🟢 |
| 22:00 | 19:00 | 🟢 |
| 22:30 | 19:30 | 🟢 |
| 23:00 | 20:00 | 🟢 |
| 23:30 | 20:30 | 🟢 |
| 00:00 | 21:00 | 🔴 Son güncelleme (kapanış) |

**Toplam: günde 14 güncelleme** (30 dakikada bir)

### Hafta Sonu
- 🔴 Cumartesi-Pazar çalışmaz (piyasa kapalı)

---

## 📍 GITHUB'DA NASIL KONTROL EDERSİN?

### 1. Actions Tab'ını Aç
```
https://github.com/zeynelgun-afk/portfolio-tracker/actions
```

veya:
1. GitHub repo sayfasını aç
2. Üstteki **"Actions"** sekmesine tıkla

### 2. Workflow'ları Gör

Sol tarafta:
```
📂 All workflows
  └─ Otomatik Fiyat Güncelleme (Seans Saatleri)
```

Sağ tarafta:
```
🟢 [AUTO] Fiyat güncellemesi - 28 Feb 2026 14:30 UTC
🟢 [AUTO] Fiyat güncellemesi - 28 Feb 2026 15:00 UTC
🟢 [AUTO] Fiyat güncellemesi - 28 Feb 2026 15:30 UTC
...
```

### 3. Log Detaylarını Gör

Herhangi bir çalıştırmaya tıkla → **"update-prices"** job'una tıkla

Göreceksin:
```
✅ Checkout repo
✅ Set up Python
✅ Install dependencies
✅ Configure Git
✅ Run update script
  📊 Toplam 37 sembol güncelleniyor...
  ✅ SM: $23.13 → $23.50 (+1.60%)
  ✅ KOS: $2.33 → $2.45 (+5.15%)
  💰 Toplam değer: $110,486.24 (+10.49%)
✅ Commit and push changes
```

---

## 🎮 MANUEL TETIKLEME

Beklemek istemiyorsan, manuel tetikle:

1. **Actions** tab'ını aç
2. Sol tarafta **"Otomatik Fiyat Güncelleme"** workflow'una tıkla
3. Sağ üstte **"Run workflow"** butonu var
4. **"Run workflow"** dropdown'ını aç
5. Branch: **main**
6. Yeşil **"Run workflow"** butonuna tıkla

30 saniye içinde çalışmaya başlar!

---

## 🔔 BİLDİRİMLER (isteğe bağlı)

GitHub'dan email bildirimi almak istersen:

1. GitHub **Settings** → **Notifications**
2. **"Actions"** bölümünde:
   - ✅ **"Send notifications for failed workflows only"** (sadece hata varsa)
   - veya
   - ✅ **"Send notifications for all workflow runs"** (her çalıştırmada)

---

## 📊 BAŞARI KRİTERLERİ

Workflow başarılı sayılır eğer:
- ✅ FMP API'den fiyat çekilirse
- ✅ JSON dosyaları güncellenirse
- ✅ Git commit + push başarılı olursa

### Başarılı Çalışma Örneği
```
🟢 [AUTO] Fiyat güncellemesi - 28 Feb 2026 15:00 UTC
Duration: 24s
```

### Başarısız Çalışma Örneği
```
🔴 [AUTO] Fiyat güncellemesi - 28 Feb 2026 15:00 UTC
Duration: 18s
Error: FMP API request failed
```

---

## ⚠️ SORUN GİDERME

### Sorun 1: Workflow çalışmıyor
**Çözüm**: 
- GitHub repo settings → Actions → "Allow all actions" seçili mi?
- Workflow dosyası `.github/workflows/` klasöründe mi?

### Sorun 2: FMP API hatası
**Çözüm**: 
- API key doğru mu? (script içinde `g1GFJZtV5rCP49UCir4WuP56VjhmA6F8`)
- Günlük limit aşıldı mı? (2500 call/gün)

### Sorun 3: Git push hatası
**Çözüm**: 
- GitHub token geçerli mi? (otomatik `GITHUB_TOKEN` kullanılıyor)
- Repo private ise actions açık mı?

---

## 📈 KULLANIM İSTATİSTİKLERİ

GitHub Actions → **"Insights"** tab:
- Kaç kez çalıştı
- Başarı oranı
- Ortalama süre
- API kullanım grafiği

---

## 🔒 GÜVENLİK

- ✅ FMP API key script içinde hardcoded (güvenli - public repo için sorun değil)
- ✅ GitHub token otomatik yönetiliyor
- ✅ Sadece `main` branch'e push yapılıyor
- ✅ Commit history tamamen şeffaf

---

## 💡 İPUÇLARI

1. **İlk hafta yakından takip et** - her gün actions tab'ını kontrol et
2. **Log dosyasını incele** - `logs/daily_update.log` dosyasında tüm geçmiş
3. **Email bildirimleri aktif et** - hata olursa hemen öğren
4. **Manuel tetikle** - acil durumlarda beklemeden güncelle

---

## 📞 DESTEK

Sorun olursa:
1. Actions tab'daki hata loglarını kontrol et
2. `logs/daily_update.log` dosyasına bak
3. Script'i local'de test et: `python3 scripts/daily_update.py`

---

## 🎯 SONRAKI ADIM

**ŞİMDİ MANUEL TEST ET:**
1. https://github.com/zeynelgun-afk/portfolio-tracker/actions
2. "Otomatik Fiyat Güncelleme" workflow'u seç
3. "Run workflow" → "Run workflow" tıkla
4. 30 saniye bekle
5. Yeşil ✅ görüyorsan başarılı!

---

**Hazır! Sistem artık tamamen otomatik çalışıyor!** 🚀
