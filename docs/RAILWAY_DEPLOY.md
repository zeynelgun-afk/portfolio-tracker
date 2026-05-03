---
title: Railway Deploy Rehberi
description: Railway worker (Telegram bot) konfigürasyonu, env, build & deploy.
tags:
  - infrastructure
  - deployment
  - railway
related:
  - "[[Index]]"
  - "[[SYSTEM_MAP]]"
  - "[[GITHUB_ACTIONS_GUIDE]]"
---

# Railway Deploy Rehberi — Telegram Bot

Finzora Telegram Bot'u Railway'de 7/24 çalıştırma.

## Neden Railway

- **Always-on** long polling → komut anında cevap (5dk GitHub Actions gecikmesi yerine)
- GitHub push otomatik deploy
- Ücretsiz tier $5 kredi/ay, bot için fazlasıyla yeterli (~$1-2 kullanır)

## Kurulum

### 1. Railway hesabı
- [railway.app](https://railway.app) → GitHub ile giriş
- "New Project" → "Deploy from GitHub repo"
- `zeynelgun-afk/portfolio-tracker` seç

### 2. Environment Variables (Project Settings → Variables)

Zorunlu:
```
TELEGRAM_TOKEN=<bot token — GitHub secret'tan aynısı>
TELEGRAM_PRIVATE_CHAT=1403072107
FMP_API_KEY=<FMP stable API key>
ANTHROPIC_API_KEY=<LLM API key — /sor, /analiz için>
RAILWAY=1
```

Opsiyonel (maliyet optimizasyonu):
```
CLAUDE_MODEL_BOT=claude-haiku-4-5-20251001      # /sor için (ucuz)
CLAUDE_MODEL_BOT_ANALIZ=claude-opus-4-7          # /analiz için (detaylı)
VOYAGE_API_KEY=<RAG için, opsiyonel>
```

### 3. Deploy ayarları

Railway otomatik `railway.json` veya `Procfile` okur. Start komutu:
```
python scripts/telegram_bot.py
```

### 4. Deploy sonrası doğrulama

Logs'ta görülmeli:
```
[Bot] Railway modu — sürekli polling başlıyor
[Bot] 2026-04-19 ...
```

Bot DM'ine `/yardim` yaz → anında cevap gelmeli.

## Komutlar

```
/portfoy        — 3 portföy özeti
/swing          — Aktif swing pozisyonlar
/stats          — Haftalık/aylık istatistik
/kapanan        — Son 5 kapanan trade + dersler
/watchlist      — Günlük tarama adayları
/vix            — Güncel VIX
/kriz           — K-13 aktif kriz matrisi
/fiyat AAPL     — Canlı fiyat
/deger AAPL     — Adil değer analizi
/beklenti AAPL  — Analist + EPS beklentileri
/sor <soru>     — AI serbest sorgusu (Haiku)
/analiz AAPL    — AI tam analiz (Opus)
```

## Maliyet Tahmini (aylık)

| Kullanım | Maliyet |
|---|---|
| Railway worker (~512MB, sürekli açık) | ~$1-2 |
| `/sor` Haiku 4.5 (günde 20 kullanım) | ~$2-3 |
| `/analiz` Opus 4.7 (günde 3 kullanım) | ~$15-20 |
| **Toplam** | **~$20-25** |

## Çakışma Önleme

GitHub Actions `telegram_bot.yml` workflow'u **devre dışı** bırakıldı (sadece manuel
trigger mümkün). Aynı anda iki instance getUpdates yaparsa mesajlar çift işlenir.

Railway deploy'u kapatırsan GitHub Actions'tan `workflow_dispatch` ile
manuel çalıştırabilirsin.

## Güvenlik

- `IZINLI_CHATLER` sadece Zeynel DM (1403072107) — grup komut almıyor
- Rate limit: dakikada max 15 komut (DDoS koruması)
- Komutlar sadece okuma — alım/satım komutu yok (kazara tek tuş riski)
- Sistem state değiştirmez, sadece raporlayıcı

## Güncelleme

GitHub main'e push attığında Railway otomatik redeploy yapar (~2 dakika).
Bot'u manuel restart etmek için: Railway dashboard → Service → Restart.
