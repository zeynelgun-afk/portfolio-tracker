# Finzora Agent

Zeynel'in otonom portföy izleme asistanı.

## Phase 1 — Sadece İzler (Şu An)

Agent hiçbir dosyaya **yazmaz**. Sadece okur, analiz yapar, Zeynel'e özel Telegram'a yazar.

```
Finzora Kanalı (@finzora)  → mevcut sistem bildirimleri (değişmedi)
Zeynel private chat         → Agent yorumları (yeni)
```

## Çalışma Zamanları

| Zaman (TR) | Mod | Ne yapar |
|---|---|---|
| 16:00 (Pzt-Cuma) | morning | Sabah analizi, günün planı |
| 00:30 (Pzt-Cuma) | closing | Kapanış yorumu |
| Her 30dk (16:30-23:00) | monitor | Stop uyarısı, acil durum |
| Pazar 12:00 | weekly | Haftalık derin analiz |

## Kurulum

### 1. GitHub Secrets Ekle

`Settings → Secrets and variables → Actions → New repository secret`

```
ANTHROPIC_API_KEY     → Anthropic Console'dan al
TELEGRAM_PRIVATE_CHAT → @userinfobot'tan al (kişisel chat ID)
FMP_API_KEY           → Zaten var
TELEGRAM_TOKEN        → Zaten var
```

### 2. İlk Testi Çalıştır

GitHub Actions → Finzora Agent → Run workflow → mode: morning

### 3. Telegram'dan Takip Et

Agent yorumları sadece sana gelir. Finzora kanalı etkilenmez.

## Dosya Yapısı

```
agent/
├── orchestrator.py   → Ana döngü, mod yönetimi
├── claude_agent.py   → LLM API bağlantısı
├── tools.py          → FMP, Telegram, veri okuma
└── README.md         → Bu dosya

.github/workflows/
└── agent.yml         → Zamanlanmış çalışma
```

## Phase Yol Haritası

- **Phase 1** (Şu an): Sadece izle, yorum yap, Telegram'a yaz
- **Phase 2**: Karar ver, Telegram'da onay iste, onaylanınca uygula
- **Phase 3**: Tam otonom, broker bağlantısı

## Önemli

Agent şu an `contents: read` yetkisiyle çalışıyor.
Hiçbir portföy dosyasını, JSON'ı, CSV'yi değiştiremez.
Bu Phase 2'de değişecek.
