# Twitter Automation - Finzora AI

## 📋 Genel Bakış

Bu sistem Finzora AI portföy raporlarını otomatik olarak Twitter'da uzun thread'ler (9-10 tweet) halinde paylaşır.

**Bileşenler:**
- `scripts/twitter_thread_poster.py` — Twitter API v2 ile tweet at
- `scripts/generate_cpu_thread.py` — CPU raporu → Twitter thread
- `.github/workflows/twitter_thread_publish.yml` — GitHub Actions workflow
- `data/twitter_threads/` — Oluşturulan thread'ler (JSON)

---

## 🔐 Gerekli Credentials

### 1. Twitter API v2 Credentials

**Nereden:** https://developer.twitter.com/

```
TWITTER_BEARER_TOKEN
TWITTER_API_KEY (opsiyonel)
TWITTER_API_SECRET (opsiyonel)
```

### 2. GitHub Secrets'e Ekle

**Repo → Settings → Secrets and variables → Actions**

```
TWITTER_BEARER_TOKEN = "AAA...xxx"
TELEGRAM_BOT_TOKEN = "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI"
TELEGRAM_CHAT_ID = "-1003827034395"
```

---

## 🚀 Kullanım

### Option A: Manuel Tetikleme (CLI)

```bash
# 1. Thread oluştur (JSON'a)
python3 scripts/generate_cpu_thread.py \
  --output data/twitter_threads/cpu_thread.json

# 2. Preview göster
cat data/twitter_threads/cpu_thread.json | python3 -m json.tool

# 3. Twitter'a at (interaktif)
TWITTER_BEARER_TOKEN="YOUR_TOKEN" \
python3 scripts/twitter_thread_poster.py \
  --source data/twitter_threads/cpu_thread.json \
  --format json \
  --dry-run  # İlk önce preview

# 4. Gerçekten at
TWITTER_BEARER_TOKEN="YOUR_TOKEN" \
python3 scripts/twitter_thread_poster.py \
  --source data/twitter_threads/cpu_thread.json \
  --format json
```

### Option B: GitHub Actions (Otomatik)

**Manuel tetikleme:**
- Repo → Actions → "Twitter CPU Thread Publisher" → Run workflow

**Zamanlanmış:**
- Her gün 10:00 TR (07:00 UTC) otomatik çalışır
- Rapor push'lendiğinde trigger olur

---

## 📊 Desteklenen Report Tipleri

Şu an: **CPU Arz Darbogazi** (`scripts/generate_cpu_thread.py`)

Gelecekte eklenebilir:
- Market Analysis Thread
- Weekly Summary Thread
- Portfolio Performance Thread
- Sector Rotation Analysis

Yeni thread oluşturmak için:
```python
# scripts/generate_YENI_thread.py
def generate_yeni_thread() -> dict:
    threads = [
        "Tweet 1...",
        "Tweet 2...",
        # ...
    ]
    return {"threads": threads, ...}
```

---

## ⚙️ Configuration

### Tweet Uzunluğu
- Max: 280 karakter
- Script otomatik kontrol eder

### Rate Limiting
- Twitter limit: 50 tweet / 15 dakika
- Script: 1 saniye bekleme
- Thread 9 tweet = ~9 saniye

### Hata Yönetimi
- Bearer token hatalı → 401 error
- Permissions yok → 403 error
- Tweet çok uzun → 400 error
- Rate limit aşıldı → 429 error

---

## 📈 Monitoring

### Twitter Analytics
- https://analytics.twitter.com
- Impressions, Engagements, Followers

### GitHub Actions Log'ları
- Repo → Actions → Workflow → Run

### Telegram Notifications
- Success: ✅ Thread paylaşıldı
- Error: ❌ Workflow başarısız

---

## 🛠️ Troubleshooting

### ❌ "TWITTER_BEARER_TOKEN not found"
→ GitHub Secrets'e ekle: `TWITTER_BEARER_TOKEN = "AAA..."`

### ❌ "401 Unauthorized"
→ Bearer Token geçersiz veya expired

### ❌ "403 Forbidden"
→ App'in "Read and Write" permissions yok
→ Twitter Developer Portal → App Settings → Değiştir

### ❌ "Tweet too long"
→ Bir tweet > 280 char
→ Kaynak script'te edit et

### ❌ Workflow hiç başlamıyor
→ GitHub Actions enabled mi? (Settings → Actions)
→ `.github/workflows/` dosyaları mı var?

---

## 📝 Yeni Thread Ekleme (Örnek)

```python
# scripts/generate_weekly_summary.py
import json
from datetime import datetime

def generate_weekly_summary() -> dict:
    threads = [
        "Bu hafta portfolio: %X gain, Y loss...",
        "Top performer: TICKER %X...",
        # ... 9-10 tweet
    ]
    return {
        "report": "Weekly Summary",
        "report_date": datetime.now().isoformat(),
        "threads": threads,
    }

if __name__ == "__main__":
    data = generate_weekly_summary()
    with open("data/twitter_threads/weekly_summary.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

Ardından workflow'a ekle:
```yaml
- name: Weekly summary thread
  run: python3 scripts/generate_weekly_summary.py
```

---

## ✅ Checklist

- [ ] Twitter API credentials aldım
- [ ] GitHub Secrets'e `TWITTER_BEARER_TOKEN` ekledim
- [ ] `scripts/twitter_thread_poster.py` yüklendi
- [ ] `scripts/generate_cpu_thread.py` yüklendi
- [ ] `.github/workflows/twitter_thread_publish.yml` yüklendi
- [ ] `data/twitter_threads/` klasörü var
- [ ] Local test: `python3 scripts/generate_cpu_thread.py` başarılı
- [ ] Local test: `--dry-run` ile preview çalışıyor
- [ ] GitHub Actions manual trigger'ı çalışıyor
- [ ] Telegram notifications aktif (opsiyonel)

---

## 📚 Kaynaklar

- Twitter API v2 Docs: https://developer.twitter.com/en/docs/twitter-api
- Rate Limits: https://developer.twitter.com/en/docs/projects/overview#rate-limits
- GitHub Actions: https://docs.github.com/en/actions

---

**Finzora AI | Otomatik Portföy Yönetim Sistemi**
