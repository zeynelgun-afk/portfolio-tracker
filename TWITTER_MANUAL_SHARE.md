# Twitter Automation - Manuel Paylaşım Akışı

## 🔄 Workflow

```
1. Portfolio güncellemesi
   └─ data/portfolios/*.json push'lenir

2. Rapor oluşturulur
   └─ DAILY_*.md veya reports/*.md push'lenir

3. GitHub Actions Trigger
   └─ .github/workflows/twitter_thread_publish.yml başlasın

4. Thread Oluştur (Otomatik)
   └─ scripts/generate_cpu_thread.py
   └─ data/twitter_threads/cpu_thread.json kaydedilir
   └─ GitHub'a commit + push

5. Telegram Bildirimi (Otomatik)
   └─ ✅ Thread hazır, paylaş komutu bekleniyor

6. MANUEL PAYLAŞ (Zeynel diğinde)
   └─ python3 scripts/twitter_thread_poster.py ...
   └─ 9-10 tweet sırayla atılır
   └─ Thread URL gönderilir

7. Telegram Success (Otomatik)
   └─ ✅ X tweet başarıyla atıldı + URL
```

---

## 🔐 Gerekli Setup (Tek Seferlik)

### GitHub Secrets (Zaten Eklendi mi?)
```
✓ TWITTER_BEARER_TOKEN
✓ TELEGRAM_BOT_TOKEN
✓ TELEGRAM_CHAT_ID
```

**Kontrol:** Repo → Settings → Secrets and variables → Actions

### Twitter API Permissions (Zaten Hazır mı?)
```
✓ App: finzora-twitter-bot
✓ Permissions: Read and Write
```

**Kontrol:** https://developer.twitter.com/ → App Settings

---

## 📝 Zeynel'in Yapacakları

### 1️⃣ Her Gün
```
- Portfolio update + push
- Rapor oluştur + push
→ Workflow otomatik başlasın
```

### 2️⃣ Tweet Atmak İstediğinde
```
Zeynel: "Twitter'a paylaş"
  ↓
Ben: python3 scripts/twitter_thread_poster.py ... çalıştırırım
  ↓
✅ 9-10 tweet atılır
```

### 3️⃣ Twitter Analytics
```
https://analytics.twitter.com
- Impressions
- Engagements
- Followers
```

---

## 📊 Thread'ler (JSON Format)

**Konum:** `data/twitter_threads/`

```
cpu_thread.json
├─ report: "CPU Arz Darbogazi"
├─ report_date: "2026-04-04"
├─ threads: [
│   "Tweet 1...",
│   "Tweet 2...",
│   ...
│   "Tweet 10..."
│ ]
└─ metadata
```

**Preview:**
```bash
cat data/twitter_threads/cpu_thread.json | python3 -m json.tool | head -50
```

---

## 🚀 Paylaş Komutu

### Option A: Dry-run (Preview Yap)
```bash
python3 scripts/twitter_thread_poster.py \
  --source data/twitter_threads/cpu_thread.json \
  --format json \
  --dry-run
```

**Çıktı:**
```
[1/10] (145 char)
Tweet 1 metni...

[2/10] (156 char)
Tweet 2 metni...

...

✓ Dry-run modunda. Tweet'ler atılmadı.
```

### Option B: Gerçekten Paylaş
```bash
python3 scripts/twitter_thread_poster.py \
  --source data/twitter_threads/cpu_thread.json \
  --format json

# Prompt çıkacak: "Thread'i Twitter'a atmak istediğine emin misin? (y/n): "
# "y" yaz
```

**Çıktı:**
```
[1/10] Atılıyor: 2026'nin en buyuk...
✓ Tweet atıldı (ID: 17549999...)

[2/10] Atılıyor: dunun GPU pazari...
✓ Tweet atıldı (ID: 17549999...)

...

✓ 10 tweet başarıyla atıldı!
🔗 Thread URL: https://twitter.com/zeynelgun01/status/17549999...
```

---

## 📱 Telegram Notification'ları

### Otomatik Bildirim 1: Thread Hazır
```
✅ CPU Arz Darbogazi Twitter thread'i oluşturuldu!

📊 10 tweet hazır
🔗 Repo: data/twitter_threads/cpu_thread.json

▶️ Paylaşmak için: python3 scripts/twitter_thread_poster.py ...
```

### Otomatik Bildirim 2: Tweet Paylaşıldı (Manual)
```
✅ 10 tweet başarıyla atıldı!
🔗 Thread URL: https://twitter.com/zeynelgun01/status/...

#Finzora #PortfolioManagement
```

---

## 🛠️ Troubleshooting

### ❌ Thread oluşturulmuyor
- Rapor dosyası push'lendi mi? (DAILY_*.md veya reports/*)
- Workflow trigger'ı çalıştı mı? (Repo → Actions)
- Python dependencies var mı? (workflow'da kurulur)

### ❌ Tweet atılmıyor
- Bearer token geçerli mi? (`TWITTER_BEARER_TOKEN`)
- Twitter API permissions "Read and Write" mi?
- Tweet'ler 280 char'ı aşmıyor mu?

### ❌ Telegram bildirimi gelmiyor
- Bot token geçerli mi? (`TELEGRAM_BOT_TOKEN`)
- Chat ID doğru mu? (`TELEGRAM_CHAT_ID`)
- Bot @finzora_ai_bot'a üye mi?

---

## 📈 İleri Automation'lar (Sonra)

Şu an: **Thread oluştur + manuel paylaş**

Gelecek:
- [ ] Weekly summary thread
- [ ] Market analysis thread
- [ ] Portfolio performance thread
- [ ] Instagram cross-post
- [ ] Scheduled tweets (saatleri seç)

---

## 📚 Files Reference

```
scripts/
├── twitter_thread_poster.py        — Tweet at (API v2)
├── generate_cpu_thread.py          — CPU raporu → thread
└── twitter_notifications.py        (opsiyonel)

.github/workflows/
└── twitter_thread_publish.yml      — Trigger + thread gen

data/twitter_threads/
└── cpu_thread.json                 — Oluşturulan thread

docs/
├── TWITTER_AUTOMATION.md           — Full guide
└── TWITTER_SETUP_CHECKLIST.md     — Setup steps
```

---

## ✅ Checklist

- [x] Workflow sadece "rapor push'lendiğinde" trigger
- [x] Thread otomatik oluşturulur
- [x] GitHub'a commit + push otomatik
- [x] Telegram bildirimi otomatik
- [x] Twitter posting manuel (Zeynel komutu)
- [x] Bearer token gerekli
- [x] Dry-run modu var (preview)

---

**Status: HAZIR** ✅

Zeynel rapor push'lerse → workflow trigger → thread hazır → "paylaş" komutu verirse → paylaşırız!
