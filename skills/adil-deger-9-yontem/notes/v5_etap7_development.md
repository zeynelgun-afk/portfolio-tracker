# Adil Değer Skill v5.0 — Etap 7: Telegram Bot Entegrasyonu

**Tarih**: 11 Mayıs 2026
**Durum**: Etap 7 tamamlandı

## Yapılan Değişiklikler

### A. `/deger TICKER` Komutu — v5.0 Skill'e Yönlendirildi

Eski Kimi-led handler (~30-50sn) tamamen v5.0 skill'e devrildi. Artık:

```
/deger NVDA       → Tam akış + kısa Telegram özet + GitHub link
/deger NVDA full  → Aynı + tam markdown raporu da Telegram'a kopyalar
```

**Tek komutla yapılan**:
1. `subprocess` ile `python3 skills/adil-deger-9-yontem/scripts/adil_deger.py TICKER --commit`
2. Skill: FMP veri + 9 yöntem + v5 sinyaller + 5y projeksiyon + 12 bölümlü markdown
3. Skill: `data/research/index.json` güncelle + git commit + pull rebase + push
4. Bot: `index.json`'dan son entry oku
5. Bot: `format_v5_telegram_summary()` ile kısa Telegram özeti üret
6. Bot: GROUP / DM'e gönder

### B. `run_adil_deger_skill_v5(ticker, full_mode)` Helper

`subprocess.run()` ile skill'i çağırır. 180sn timeout. Hata yönetimi:
- Skill bulunamadı
- Exit code ≠ 0
- index.json oluşmadı / entry yok
- Subprocess timeout

Returns: `{entry, md_path, md_text (full_mode), stdout_tail}` veya `{error}`.

### C. `format_v5_telegram_summary(entry, github_url)` Formatter

index.json entry'sinden HTML formatlı kısa özet üretir. İçerik:

```
📊 NVDA — Adil Değer v5.0
NVIDIA Corporation

💰 Fiyat: $215.22
🎯 Adil Değer: $259.25 (+%20.5)
🎲 Mod: GROWTH | Confidence: ORTA
⭐ Quality Premium: 1.40x

📈 Karar: 🟢 AL
Mevcut fiyat normal medyan altında. İyi giriş seviyesi.

🎭 Senaryolar:
  🐻 Bear:  $194.96 (-9.4%)
  ⚖️ Baz:   $259.25 (+20.5%)
  🐂 Bull:  $310.68 (+44.4%)

🔍 v5 Sinyaller:
  🛡️ Altman Z: 68.23 🟢 GÜVENLİ
  📋 Piotroski: 6/9 🟡 SAĞLAM
  📊 Sentiment 6 ay: 🔴 DOWNGRADE TRENDI (-6)
  🎯 Ürün: 🔴 KRİTİK: Data Center %90
  🌐 Canlı sektör P/E: 62.3x
  💼 CAPM WACC: %17.84
  📐 FMP DCF: $247.15

📅 Normalizasyon: 🟢 2026 (0 yıl) | Profil: semicon_design_mature

🚀 Giriş Planı:
  Stop: $187.24 | H1: $259.25 | H2: $310.68

📁 Portföy Uygunluğu:
  Dengeli: uygun_kosullu
  Agresif: uygun
  Temettü: uygun_degil

📄 Tam Rapor: GitHub

Tam rapor için: /deger NVDA full
finzora ai — Adil Değer Skill v5.0
```

Karakter sayısı: ~1100 (Telegram sınırı 4096, rahat sığar).

### D. Full Mode — Markdown'ı Telegram'a Kopyala

`/deger TICKER full` kullanıldığında:
1. Kısa özet gönderilir
2. Sonra markdown dosyası 3800 karakterlik parçalara bölünüp `<pre>` bloklarında gönderilir
3. HTML special karakterler escape edilir (`&`, `<`, `>`)

Tipik 12 bölümlü rapor 8-10KB → 3-4 Telegram mesajına böler.

### E. github_md_url(repo_path) Helper

```python
github_md_url("reports/research/NVDA_ADIL_DEGER_2026-05-11.md")
→ "https://github.com/zeynelgun-afk/portfolio-tracker/blob/main/reports/research/NVDA_ADIL_DEGER_2026-05-11.md"
```

### F. format_yardim() Güncellendi

Yardım metnine v5.0 bölümü eklendi (eski v7/Kimi de kalıyor — `AAPL` tek başına yazılırsa eski path kullanılır).

## Akış (Production Kullanım)

```
[Telegram] Zeynel: /deger NVDA
    ↓
[Bot] "⏳ NVDA Adil Değer v5.0 hesaplanıyor..."
    ↓
[Bot] subprocess.run skill --commit (30-90sn)
    ↓
[Skill] FMP veri → 9 yöntem + v5 + 5y projeksiyon
    ↓
[Skill] reports/research/NVDA_ADIL_DEGER_2026-05-11.md (201 satır)
    ↓
[Skill] data/research/index.json güncelle
    ↓
[Skill] git add + commit + pull --rebase + push
    ↓
[Bot] index.json'dan son NVDA entry oku
    ↓
[Bot] format_v5_telegram_summary → 1100 karakter özet
    ↓
[Telegram] Zeynel: Özet alındı + GitHub linki
```

## Railway Notları

Bot Railway'de çalışıyor. Skill subprocess olarak çağrılınca:
- `cwd` otomatik tespit: `/app` varsa (Railway), yoksa scripts/.. (lokal)
- `git push` Railway'de çalışıyorsa direkt push, çalışmıyorsa sadece commit kalır
- Skill `git_commit_and_push()` push fail durumunda exception fırlatmaz (False döner, stderr'a yazar)

Eğer Railway'de push fail olursa: commit lokal kalır, Zeynel sonradan manuel push'lar veya cron ile haftalık push yapılır.

## Test

format_v5_telegram_summary fonksiyonu mevcut NVDA index entry'siyle test edildi (commit `b4af3b3` üretmişti):
- ✅ 1124 karakter (sınır altında)
- ✅ HTML format doğru
- ✅ Tüm 8 alt bölüm dolu
- ✅ GitHub linki geçerli URL

## Yeni Bot CLI

```
[Telegram bot]
/deger NVDA          # v5.0 tam akış, kısa özet
/deger NVDA full     # + tam markdown rapor
AAPL                 # Eski v7/Kimi (geriye uyum)
/q AAPL              # Hızlı framework (eski)
/detay AAPL          # Eski v7 detay
```

## Etap 8'e Bırakılanlar

1. **Pre-IPO Telegram desteği** — `/deger pre-ipo PATH` ile JSON dosyasıyla pre-IPO modu çağrı
2. **HTML rapor üretici** — `--html` flag (frontend-design skill bridge)
3. **Multi-year analyst estimates** — 1y, 2y, 3y forward (şu an sadece 2y)
4. **Profile delta-based projection** — TTM gerçek üzerine delta (her şirket için doğru kalibre)
5. **Geçmiş analiz takip** — index.json "gerceklesen" alanı haftalık otomatik güncelleme
6. **Sektör multiple history tracking** — SECTOR_MULTIPLES'ı canlı veriden 3 aylık snapshot ile auto-update

Kaynak: finzora ai
