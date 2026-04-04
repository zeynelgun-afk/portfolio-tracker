# TWITTER API V2 SETUP - Finzora AI Otomasyon

## 1. Twitter Developer Portal'a Erişim

1. **https://developer.twitter.com/en/portal/dashboard** adresine git
2. Varsa X (eski Twitter) hesabınla giriş yap, yoksa yeni hesap oluştur
3. **Projects & Apps** → **Create App** → **Create New**
4. App ismi: `finzora-ai-trading` (veya preference'ına göre)
5. Use case: `Bot` seç (automated posting için)

## 2. API Keys & Tokens Oluşturma

Otomatik posting için **OAuth 2.0** gerekir (Elevated Access gerekebilir, free tier başında genellikle Basic):

### OAuth 2.0 Flow (En Basit)
1. App settings'e git
2. **Keys and Tokens** → **Generate** (Authentication Tokens)
3. Şunları al:
   - **API Key** (Consumer Key)
   - **API Secret** (Consumer Secret)
   - **Bearer Token** — direct posting için EN ÖNEMLI
   - **Access Token**
   - **Access Token Secret**

### Permissions
- **Read and Write** (at minimum)
- Eğer "Write" erişimi yoksa, App Settings → Permissions → **Read and Write** seç

## 3. BEARER TOKEN - GitHub Secrets'e Ekle

Bearer Token, otomatik posting için tek yeterli credential.

### GitHub Secrets'e Ekle:
1. Repo: `zeynelgun-afk/portfolio-tracker`
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**:
   - Name: `TWITTER_BEARER_TOKEN`
   - Value: `AAAA...` (Twitter'dan kopyalanan Bearer Token)

## 4. Elevated Access (İsteğe Bağlı, Free Tier Limit)

Free tier başında:
- Günde max 50 tweet
- 300K/15 min post endpoint call'ları

Eğer daha fazla tweet gerekirse, **Apply for Elevated** → Twitter'a form gönder (genellikle anında onay).

## 5. Test (Curl)

```bash
# Tek tweet test
curl -X POST https://api.twitter.com/2/tweets \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Test tweet from Finzora AI"}'
```

## 6. Quota Bilgileri

Free tier limits:
- Yazma: 50 tweets/day
- Başlık tweet reply'ı: 100/day
- Retweet: unlimited
- Rate limit: 300K tweets/15 minutes endpoint

## Alternatif: RapidAPI (Simpler ama Limited)

RapidAPI'deki Twitter240 endpoint'i posting için sınırlı. Preferred: Official Twitter API v2.

---

**Sonra:** Zeynel, bearer token'ı GitHub Secrets'e ekledikten sonra, otomatik script'leri push edebilirim.
