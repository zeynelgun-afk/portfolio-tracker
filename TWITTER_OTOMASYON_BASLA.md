# ✅ TWITTER THREAD OTOMASYON - TAM REHBER

## 🎯 HEDEF
Rapor yazarken → otomatik Twitter thread oluşturma → posting

```
Rapor push → GitHub Actions tetikle → Claude API thread oluştur → Twitter post
```

---

## 📋 ADIM 1: Twitter API Hazırlanması (5 dakika)

### 1.1 Twitter Developer Portal
1. **https://developer.twitter.com/en/portal/dashboard** git
2. X/Twitter hesabınla giriş yap (yoksa oluştur)
3. **Create App** → `finzora-ai-trading`
4. **Keys and Tokens** → Oluştur

### 1.2 Bearer Token Al
- App Settings → **Authentication Tokens**
- **Bearer Token** kopyala (AAAA... ile başlayan uzun string)
- **Not et:** Sonra GitHub'a yapıştırılacak

### 1.3 Permissions Kontrol
- App Settings → **Permissions**
- **Read and Write** seçili mi?
- Eğer yoksa → seç → Save

✅ **Bearer token hazır mı?** Devam et.

---

## 📋 ADIM 2: GitHub Setup (10 dakika)

### 2.1 GitHub Secrets Ekle
1. **https://github.com/zeynelgun-afk/portfolio-tracker** git
2. **Settings** (sağ üst saat gibi icon) → **Secrets and variables** → **Actions**

### 2.2 Secret 1: TWITTER_BEARER_TOKEN
- **New repository secret** tıkla
- **Name:** `TWITTER_BEARER_TOKEN`
- **Value:** `AAAA...` (Twitter'dan kopyaladığın bearer token)
- **Add secret**

### 2.3 Secret 2: ANTHROPIC_API_KEY
- Tekrar **New repository secret**
- **Name:** `ANTHROPIC_API_KEY`
- **Value:** `sk-ant-...` (Claude API key'in)
- **Add secret**

✅ **Kontrol:** Settings → Secrets'te 2 secret görülüyor mu?

---

## 📋 ADIM 3: Script + Workflow Dosyalarını GitHub'a Ekle (5 dakika)

### 3.1 Local Repo'da Terminal Aç
```bash
cd ~/portfolio-tracker
```

### 3.2 Workflow Klasörü Oluştur
```bash
mkdir -p .github/workflows
```

### 3.3 Script Dosyalarını Kopyala
İndirin ve yükle:

**Script 1:** `scripts/twitter_thread_auto.py`
- `/home/claude/scripts_twitter_thread_auto.py` → `scripts/twitter_thread_auto.py` kopyala

**Script 2:** Workflow `.github/workflows/twitter_thread_auto.yml`
- `/home/claude/.github_workflows_twitter_thread_auto.yml` → `.github/workflows/twitter_thread_auto.yml` kopyala

### 3.4 Git'e Ekle ve Push Et
```bash
git add scripts/twitter_thread_auto.py
git add .github/workflows/twitter_thread_auto.yml
git commit -m "feat: add twitter thread auto-generation from reports"
git push origin main
```

✅ **Push başarılı mı?** GitHub'a bakmadan devam etme, confirm et.

---

## 📋 ADIM 4: Test (Dry Run) - 5 dakika

### 4.1 GitHub Actions'a Git
1. Repo: https://github.com/zeynelgun-afk/portfolio-tracker
2. **Actions** tabı → **📱 Twitter Thread Auto-Post**
3. **Run workflow** düğmesine tıkla (sağ taraf)

### 4.2 Test Formu Doldur
- **report_file:** `reports/cpu_darbogazi_raporu.pdf`
- **theme:** `CPU Supply Chain & Investment Opportunities`
- **dry_run:** `true` ← ÖNEMLI! (gerçek tweet atmaz, test et)

3. **Run workflow** butonuna tıkla

### 4.3 Logs'a Bak
- **Actions** → iş açılsın
- **generate-and-post** tıkla
- Adım adım çalışma görülecek:
  - ✅ Dependencies install
  - ✅ Report oku
  - ✅ Claude API'ye sor
  - ✅ Thread preview

### 4.4 Output Kontrol
- **Artifacts** tab'ında `.github/twitter_thread_output.json` indir
- İçinde tweets array'ı göreceksin

✅ **Thread preview güzel mi? Tweet sayısı doğru mu?** Devam et.

---

## 📋 ADIM 5: LIVE (Gerçek Post) - Test

### 5.1 Tekrar Run Workflow
1. **Run workflow** → Aynı form
2. **dry_run:** `false` ← LIVE MODE
3. **Run workflow**

### 5.2 Twitter'a Git
- @zeynelgun01 hesabını aç
- Profilde yeni thread'i göreceksin
- İlk tweet linkini kopyala: `https://x.com/zeynelgun01/status/XXXXX`

✅ **Tweet'ler başarıyla posted mi?** Tamamdır!

---

## 📋 ADIM 6: Otomatik Tetikleme (Günlük Raporlar)

Bundan sonra:

```bash
# Sabah raporu yaz
nano reports/daily/DAILY_2026_04_06_SABAH.md

# Push et
git add reports/daily/DAILY_2026_04_06_SABAH.md
git commit -m "daily: market open analysis"
git push

# ✨ Workflow OTOMATIK tetiklenir
# (push'tan 30 saniye sonra Actions'ta görülür)
# Thread oluşturulur → posted!
```

Haftalık (Pazar):
```bash
nano reports/weekly/WEEKLY_2026_04_06.md
git add reports/weekly/WEEKLY_2026_04_06.md
git commit -m "weekly: sector rotation & portfolio review"
git push

# ✨ Otomatik thread
```

---

## 🔧 Önemli Noktalar

### ⚠️ BACKUP PLAN: Manuel Post

Eğer otomasyonun bir gün fail'i olursa:
```bash
# Local'de test et
export ANTHROPIC_API_KEY="sk-..."
export TWITTER_BEARER_TOKEN="AAAA..."

python3 scripts/twitter_thread_auto.py \
  --file reports/cpu_darbogazi_raporu.pdf \
  --dry-run  # test

# Sonra --dry-run kaldır ve live at
python3 scripts/twitter_thread_auto.py \
  --file reports/cpu_darbogazi_raporu.pdf
```

### 📊 Monitoring
Her post sonra:
- Actions → Son job → Logs (çalışma kontrol)
- Artifacts → JSON output (tweet details)
- Twitter → @zeynelgun01 (published thread kontrol)

### 💰 Quota Attention
- **Twitter:** 50 tweet/day (free tier)
- **Claude:** Creditler biterse otomasyonun fail'i olur

---

## ✅ CHECKLIST - BAŞLAMA ÖNCESİ

- [ ] Twitter API Bearer Token aldı
- [ ] GitHub Secrets 2 tanesini ekledim (TWITTER_BEARER_TOKEN + ANTHROPIC_API_KEY)
- [ ] Script dosyalarını push ettim
- [ ] Workflow dosyasını push ettim
- [ ] Dry run test'ini yaptım (logs kontrol)
- [ ] LIVE run test'ini yaptım (tweet post)
- [ ] @zeynelgun01'de thread görünüyor mu?

---

## 🚀 READY!

Bundan sonra:
1. Rapor yaz (`reports/daily/` veya `reports/weekly/`)
2. Git push
3. ✨ Otomatik thread + post!

Sorular? Logs'a bak, screenshoot yolla → debug edelim 🎯
