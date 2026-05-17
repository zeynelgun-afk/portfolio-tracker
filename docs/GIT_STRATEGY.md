# Git Stratejisi — Bot vs Manuel Commit Ayrımı

**Yürürlük:** 10 Mayıs 2026 itibarıyla
**Kaynak:** finzora ai

## 1. Amaç

Repo'da bot tarafından otomatik atılan commit'lerin (workflow ve schedule kaynaklı) manuel commit'lerden net şekilde ayırt edilebilmesi. Önceki durumda hepsi aynı author email ile atılıyordu, bu yüzden istatistik raporları, audit ve git log filtreleri bot'u manuel'den ayıramıyordu.

## 2. Konvansiyon

### 2.1 Bot commit'leri

| Alan | Değer |
|------|-------|
| `user.name` | `Finzora Bot` |
| `user.email` | `finzora-bot@users.noreply.github.com` |
| Commit mesaj prefix | `[bot/CATEGORY] ...` |

CATEGORY listesi (workflow'a göre):

| Workflow dosyası | Prefix |
|------------------|--------|
| `agent.yml` | `[bot/agent-MODE]` (MODE = morning/monitor/closing) |
| `morning_scan.yml` | `[bot/scan]`, `[bot/scan-retry]`, `[bot/swing-entry]` |
| `news_radar.yml` | `[bot/radar]` |
| `adil_deger_panel.yml` | `[bot/panel]` |
| `adil_deger_weekly.yml` | `[bot/panel-weekly]` |
| `macro_calendar.yml` | `[bot/macro]` |
| `telegram_bot.yml` | `[bot/telegram-offset]` |

### 2.2 Manuel commit'ler

| Alan | Değer |
|------|-------|
| `user.name` | `Finzora AI` (mevcut, korunuyor) |
| `user.email` | `zeynelgun@users.noreply.github.com` (mevcut, korunuyor) |
| Commit mesaj formatı | Conventional commit (`fmp:`, `fix:`, `ops:`, `notes:`, `docs:`, vs) — prefix'siz olabilir |

Manuel commit'lerde `[bot/...]` prefix kullanılmaz. Bot prefix'leri rezervedir.

## 3. Filtre Komutları

Sadece bot commit'leri:

```bash
git log --author='finzora-bot@' --oneline
# veya prefix ile
git log --grep='^\[bot/' --oneline
```

Sadece manuel commit'ler:

```bash
git log --author='zeynelgun@users' --oneline
```

Belirli kategorideki bot commit'leri:

```bash
git log --grep='^\[bot/scan' --oneline       # scan + scan-retry
git log --grep='^\[bot/agent-morning' --oneline
```

Haftalık bot etkinliği:

```bash
git log --author='finzora-bot@' --since='7 days ago' \
  --pretty=format:'%h %ad %s' --date=short
```

Manuel commit ile bot commit oranı:

```bash
echo "Bot:    $(git log --author='finzora-bot@' --since='30 days ago' --oneline | wc -l)"
echo "Manuel: $(git log --author='zeynelgun@users' --since='30 days ago' --oneline | wc -l)"
```

## 4. Geriye Dönük Uyumluluk

10 Mayıs 2026 öncesi tüm bot commit'leri eski standartla atılmış (`zeynelgun@users` email + karışık prefix). Bunlar tarih kayıtlarında öyle kalır, geriye dönük rewrite YAPILMAYACAK (force-push riski yüksek, paylaşımlı branch). Yeni standart sadece bu tarihten sonraki commit'lere uygulanır.

İstatistik script'leri (örnek `agent/reports/stats.py` — eski path `scripts/finzora_stats.py` shim olarak çalışır) bu kesim noktasını dikkate almalı: 10 May 2026 öncesi bot/manuel ayrımı hatalı sonuç verecektir.

## 5. Onay ve İstisna

Yeni bir workflow eklenirken bu konvansiyona uyulmalı:
- Git config blok'u standart user.name + user.email kullanır
- Commit mesaj prefix'i `[bot/CATEGORY]` formatında, kategori listede yoksa eklenmeli (PR'da bu doc da güncellenmeli)

İstisna: Kullanıcı (Zeynel) lokal'den manuel commit attığında elle `git config` setlemez, mevcut global config kullanır. Global config `Finzora AI <zeynelgun@users.noreply.github.com>` olduğu için doğal olarak manuel kategoriye düşer.

---

**Son güncelleme:** 10 Mayıs 2026
**Kaynak:** finzora ai
