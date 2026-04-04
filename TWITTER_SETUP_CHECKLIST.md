# ✅ TWITTER AUTOMATION - SETUP CHECKLIST

## Phase 1: Twitter API Hazırlık ✓ (TAMAMLANDI)

- [x] Twitter Developer Portal'a app oluştur
- [x] Consumer Key (API Key): `WmMeMCHWIduV7Myr7X7dwBZFZ`
- [x] Secret Key: `l1pBqFOFxvyPvnHaE9t8HKqectsn1WycfEKdOwRptfElORAxx6`
- [x] Bearer Token: `AAAAAAAAAAAAAAAAAAAAAGwZ8wEAAAAAWQx5jfK4HGkvdSb9AlSz3CvIkaQ%3D0Qw3Zn1rtjlNUX3Z2cUdxnTaW9IgM16L67zzE7pvRTuw4GmE76`

**SONRAKİ:** Permissions'ı "Read and Write" olarak değiştir

---

## Phase 2: GitHub Secrets Ekleme (HEMEN YAP)

### Konum
`Repo → Settings → Secrets and variables → Actions`

### Eklenecek 3 Secret

```
Name: TWITTER_BEARER_TOKEN
Value: AAAAAAAAAAAAAAAAAAAAAGwZ8wEAAAAAWQx5jfK4HGkvdSb9AlSz3CvIkaQ%3D0Qw3Zn1rtjlNUX3Z2cUdxnTaW9IgM16L67zzE7pvRTuw4GmE76

---

Name: TELEGRAM_BOT_TOKEN
Value: 8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI

---

Name: TELEGRAM_CHAT_ID
Value: -1003827034395
```

**Talimat:**
1. Her Secret için "New repository secret" tıkla
2. Name + Value yapıştır
3. "Add secret" tıkla
4. Tekrarla (3 secreytin hepsi için)

---

## Phase 3: Scripts'i Repo'ya Ekle (HEMEN YAP)

Şu dosyalar **GitHub reposuna** push'lenecek:

```
portfolio-tracker/
├── scripts/
│   ├── twitter_thread_poster.py        ← Hazır
│   ├── generate_cpu_thread.py          ← Hazır
│   └── twitter_notifications.py        (opsiyonel)
├── .github/
│   └── workflows/
│       └── twitter_thread_publish.yml  ← Hazır
├── data/
│   └── twitter_threads/
│       └── (JSON dosyaları buraya)
└── TWITTER_AUTOMATION.md               ← Hazır
```

**Yapılacak:**
```bash
# Repo'ya indir (sana göndereceğim dosyaları)
git clone https://github.com/zeynelgun-afk/portfolio-tracker.git
cd portfolio-tracker

# Yeni klasör + dosyalar ekle
mkdir -p scripts .github/workflows data/twitter_threads

# scripts/ dosyalarını ekle (aşağıda verili)
# .github/workflows/twitter_thread_publish.yml ekle
# TWITTER_AUTOMATION.md ekle

# Commit + Push
git add -A
git commit -m "feat: twitter thread automation (cpu, market analysis)"
git push origin main
```

---

## Phase 4: Local Test (OPSIYONEL AMA ÖNERİLEN)

### Test 1: Thread Oluştur
```bash
cd portfolio-tracker
python3 scripts/generate_cpu_thread.py \
  --output data/twitter_threads/cpu_thread.json

# Beklenen çıktı:
# ✓ Tüm 10 tweet valide (280 char max)
# ✓ Thread'ler kaydedildi: data/twitter_threads/cpu_thread.json
```

### Test 2: Dry-run (Gerçekten atmadan preview)
```bash
export TWITTER_BEARER_TOKEN="AAAAAAAAAAAAAAAAAAAAAGwZ8..."

python3 scripts/twitter_thread_poster.py \
  --source data/twitter_threads/cpu_thread.json \
  --format json \
  --dry-run

# Beklenen: 10 tweet preview + "Dry-run modunda, tweets atılmadı"
```

### Test 3: Gerçek Tweet (İlk test)
```bash
python3 scripts/twitter_thread_poster.py \
  --source data/twitter_threads/cpu_thread.json \
  --format json

# Prompt: "Thread'i Twitter'a atmak istediğine emin misin? (y/n): "
# "y" yaz

# Beklenen:
# ✓ 10 tweet başarıyla atıldı!
# 🔗 Thread URL: https://twitter.com/zeynelgun01/status/XXXX
```

---

## Phase 5: GitHub Actions Test (HEMEN YAP)

### Manual Tetikleme

1. Repo → Actions Tab
2. "Twitter CPU Thread Publisher" workflow'u bul
3. "Run workflow" → "Run workflow" tıkla
4. Bir kaç saniye sonra job başlamalı

**Kontrol:**
- ✅ Job "publish-thread" başladı mı?
- ✅ Python kuruldu mu?
- ✅ Scripts çalıştı mı?
- ✅ Tweet'ler atıldı mı?
- ✅ Telegram bildirimi geldi mi?

**Hata varsa:**
- Actions → Latest run → Hata log'u oku
- Çoğunlukla: secrets yanlış veya permissions değil

---

## Phase 6: Zamanlanmış Otomasyon (AFTER TEST)

Workflow zaten konfigüre edilmiş:
```yaml
schedule:
  - cron: '0 7 * * *'  # Her gün 07:00 UTC = 10:00 TR
```

**Bunu devre dışı bırakmak için:**
```yaml
# schedule:
#   - cron: '0 7 * * *'
```

---

## 🎯 IMMEDIATE ACTION ITEMS

### ✅ HEMEN (Sonraki 5 dakika):

1. **GitHub Secrets'e 3 secret ekle**
   - TWITTER_BEARER_TOKEN
   - TELEGRAM_BOT_TOKEN (mevcut)
   - TELEGRAM_CHAT_ID (mevcut)

2. **Twitter Developer Portal'ında permissions kontrol**
   - Settings → "Read and Write" seçili mi?

### ✅ BUGÜN (Sonraki 1 saat):

3. **Scripts'i repo'ya push et**
   - `scripts/twitter_thread_poster.py`
   - `scripts/generate_cpu_thread.py`
   - `.github/workflows/twitter_thread_publish.yml`

4. **GitHub Actions'da manual test**
   - "Twitter CPU Thread Publisher" workflow'u çalıştır
   - Başarılı oldu mu kontrol et

### ✅ ONAY (Sonraki 24 saat):

5. **Production'a geç**
   - Zamanlanmış workflow'lar aktif olacak
   - Hergün 10:00 TR'de tweet'ler atılacak

---

## 📊 Workflow Özeti

```
Rapor Tamamlandı
    ↓
GitHub'a Push Et
    ↓
Actions: twitter_thread_publish.yml Başlat
    ↓
Script: generate_cpu_thread.py (Thread oluştur)
    ↓
Script: twitter_thread_poster.py (Twitter'a at)
    ↓
Telegram: Success/Error bildirimi gönder
    ↓
GitHub: Commit + Push (thread JSON'ı)
```

---

## ⚠️ Common Issues + Solutions

| Problem | Çözüm |
|---------|-------|
| `401 Unauthorized` | Bearer token yanlış. Twitter Portal → Keys & Tokens |
| `403 Forbidden` | "Read and Write" permission yok. Twitter Portal → Settings |
| `Tweet too long` | Kaynak script'te tweet'i 280 char altına kısalt |
| `Workflow not running` | Actions enabled mi? Settings → Actions → Enable |
| `Secrets not found` | Syntax kontrol: `TWITTER_BEARER_TOKEN` (exact match) |

---

## 🚀 Sonra

Kurulum tamamlandıktan sonra:
- Instagram automation'ı entegre et
- Weekly summary thread'i ekle
- Portfolio performance thread'i ekle
- Sector rotation analysis thread'i ekle

---

## 📞 Sorularınız?

Her adımda kafan karışırsa:
1. TWITTER_AUTOMATION.md oku
2. GitHub Actions log'larını kontrol et
3. Bana sor!

**Status:** Hazırlanıyor → Git Pushing → Testing → Live
