# instagram otomatik paylasim kurulum rehberi

## genel bakis

bu rehber @zeynelgun01 instagram isletme hesabina meta graph api uzerinden otomatik paylasim yapmak icin gereken adimlari aciklar.

sistem iki scriptten olusur:
- `scripts/instagram_post_generator.py` — gorsel uretir (pillow)
- `scripts/instagram_publisher.py` — instagram a paylas (meta api)

---

## on kosullar

1. instagram isletme hesabi (business account) — zaten var
2. facebook sayfasi — instagram hesabina bagli olmali
3. meta developer hesabi — developers.facebook.com

---

## adim 1: facebook sayfasi olustur ve bagla

instagram isletme hesabini bir facebook sayfasina baglamak zorunlu:

1. facebook.com/pages/create adresinden sayfa olustur
2. instagram uygulamasinda ayarlar > hesap > bagli hesaplar > facebook > sayfani sec
3. bu baglanti olmadan api calismaz

---

## adim 2: meta developer uygulamasi olustur

1. developers.facebook.com adresine git
2. "uygulamalarim" > "uygulama olustur"
3. uygulama turu: "isletme" sec
4. uygulama adini gir: "finzora instagram"
5. uygulama kimligini not al (app id)

---

## adim 3: izinleri yapilandir

uygulama panelinde asagidaki izinleri ekle:
- `instagram_basic`
- `instagram_content_publish`
- `pages_show_list`
- `pages_read_engagement`

bu izinler icin meta incelemesinden gecmen gerekebilir (genellikle 1-3 gun).

---

## adim 4: erisim tokeni al

### kisa sureli token (test icin)
1. graph api explorer: developers.facebook.com/tools/explorer
2. uygulamani sec
3. izinleri ekle (yukardaki listeden)
4. "erisim tokeni olustur" tikla
5. bu token 1 saat gecerli

### uzun sureli token (uretim icin)
kisa sureli tokeni uzun sureliye cevir:

```
GET https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &fb_exchange_token={KISA_SURELI_TOKEN}
```

bu token 60 gun gecerli. otomatik yenileme icin cron job kurulabilir.

### sayfa tokeni (kalici)
uzun sureli kullanici tokeninle:

```
GET https://graph.facebook.com/v19.0/me/accounts
  ?access_token={UZUN_SURELI_TOKEN}
```

donusen sayfa tokeni kalicidir (sureleri dolmaz).

---

## adim 5: instagram hesap id sini bul

```
GET https://graph.facebook.com/v19.0/{SAYFA_ID}
  ?fields=instagram_business_account
  &access_token={SAYFA_TOKENI}
```

donusen `instagram_business_account.id` degerini not al.

---

## adim 6: ortam degiskenlerini ayarla

repo kok dizininde `.env` dosyasi olustur:

```env
# instagram api
INSTAGRAM_ACCOUNT_ID=17841400000000000
META_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx

# gorsel hosting (birini sec)
IMGBB_API_KEY=abc123def456  # imgbb.com dan ucretsiz api key
# veya
IMAGE_HOST_BASE=https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/outputs/instagram
```

github actions icin bu degerleri repo settings > secrets > actions kismina ekle.

---

## adim 7: gorsel hosting

instagram api gorsel url si ister (yerel dosya kabul etmez). secenekler:

### secenek a: imgbb (onerilen)
1. imgbb.com da hesap ac
2. api.imgbb.com dan api key al
3. `.env` ye `IMGBB_API_KEY` ekle
4. script otomatik olarak goruntuyu yukler

### secenek b: github raw url
1. goruntuyu repo ya pushla
2. `IMAGE_HOST_BASE` i github raw url olarak ayarla
3. api goruntuyu bu url den ceker

### secenek c: cloudinary
1. cloudinary.com da ucretsiz hesap ac
2. upload api kullan
3. publisher scripti buna gore guncelle

---

## kullanim

### tek seferlik post
```bash
# gorsel uret
python scripts/instagram_post_generator.py --type piyasa

# instagram a paylas
python scripts/instagram_publisher.py --type piyasa

# veya hazir gorsel + ozel caption
python scripts/instagram_publisher.py --image outputs/instagram/piyasa_20260331.png --caption "piyasa ozeti..."

# test modu (api cagrisi yapmaz)
python scripts/instagram_publisher.py --type performans --dry-run
```

### otomatik gunluk post (github actions)
`.github/workflows/instagram_daily.yml` dosyasi ile her gun otomatik paylasim:

```yaml
name: instagram gunluk post
on:
  schedule:
    - cron: '0 21 * * 1-5'  # pazartesi-cuma 00:00 TR (UTC+3)
  workflow_dispatch:

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install Pillow requests
      - name: piyasa postu uret ve paylas
        env:
          INSTAGRAM_ACCOUNT_ID: ${{ secrets.INSTAGRAM_ACCOUNT_ID }}
          META_ACCESS_TOKEN: ${{ secrets.META_ACCESS_TOKEN }}
          IMGBB_API_KEY: ${{ secrets.IMGBB_API_KEY }}
        run: python scripts/instagram_publisher.py --type piyasa
```

---

## sorun giderme

| sorun | cozum |
|-------|-------|
| "invalid access token" | token suresi dolmus, yenile |
| "instagram account not found" | facebook sayfasi baglantisini kontrol et |
| "(#9004) image url is not accessible" | gorsel hosting yapilandirmasini kontrol et |
| "you do not have permission" | izinlerin onaylandigini kontrol et |
| "rate limit exceeded" | 25 post/gun limiti var, bekle |

---

## limitler

- gunluk 25 post (container olusturma)
- gorsel: jpeg veya png, max 8mb
- caption: max 2200 karakter
- hashtag: max 30 (ama 5-10 arasi onerilen)
- carousel (coklu gorsel): ayri api endpoint i gerekir
- video/reels: ayri endpoint, farkli akis

---

## sonraki adimlar

1. meta developer hesabi olustur
2. facebook sayfasi bagla
3. izinleri al
4. tokenlari `.env` ye ekle
5. `--dry-run` ile test et
6. calisiyorsa github actions yapilandir
