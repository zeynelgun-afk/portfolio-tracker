# 🤖 GitHub Actions Workflows

## 📊 daily-update.yml

**Ne yapar:**
- Her hafta içi (Pazartesi-Cuma) saat 13:00 UTC (16:00 Türkiye) otomatik çalışır
- 4 portföyü günceller
- Swing trade pozisyonlarını kontrol eder
- Trailing stop'ları günceller
- Değişiklikleri otomatik commit + push eder

**Manuel tetikleme:**
- GitHub → Actions → "Günlük Portföy Güncellemesi" → Run workflow

**Gereksinimler:**
- `FMP_API_KEY` secret'ı tanımlı olmalı

---

**Son Güncelleme:** 19 Şubat 2026
