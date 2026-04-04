---
name: instagram-content-creator
description: Finzora AI markası için Instagram içerik üretimi (görsel + video + caption). ABD borsası analizi, hisse önerileri, eğitim içerikleri ve marka tanıtımı postları oluşturur. Canva API ile profesyonel tasarım, Python Pillow ile veri bazlı görseller, Meta Graph API ile otomatik paylaşım. Tetikleyiciler: "instagram postu yap", "instagram içerik üret", "sosyal medya görseli", "post hazırla", "reel yap", "story yap", "instagram paylaş", "günlük post", "haftalık post", "hisse postu", "piyasa özeti görseli", "eğitim postu".
---

# Finzora AI — Instagram İçerik Üretim Sistemi

## 1. MARKA KİMLİĞİ

### Renk Paleti
| Renk | HEX | Kullanım |
|------|-----|----------|
| Koyu lacivert (bg) | `#0a0a0f` | Ana arka plan |
| Koyu kart | `#12121a` | Kart arka planları |
| Surface | `#16161f` | İkincil yüzeyler |
| Neon yeşil (accent) | `#00d4aa` | Pozitif değerler, CTA, logo |
| Kırmızı | `#ff4757` | Negatif değerler, düşüşler |
| Altın | `#ffd700` | Vurgular, eğitim serisi |
| Mavi | `#4a9eff` | Piyasa verileri, bilgi |
| Telegram mavisi | `#0088cc` | Telegram CTA |
| Metin | `#e8e8f0` | Ana metin |
| Soluk metin | `#6b6b80` | İkincil metin, tarih |

### Ton ve Dil
- Dil: Türkçe (teknik terimler İngilizce parantezle)
- Üslup: profesyonel ama samimi, jargonsuz, anlaşılır
- Kaynak: sadece "finzora ai" olarak atıf
- Emoji: ölçülü kullan (başlıkta 1, alt bilgide 1-2)
- Küçük harf: türkçe kesme işareti KULLANMA (Jensen'ın → Jensen in)
- CTA: her postta @finzora telegram yönlendirmesi

### Format Boyutları
| Tip | Boyut | Oran |
|-----|-------|------|
| Post (kare) | 1080×1080 | 1:1 |
| Post (dikey) | 1080×1350 | 4:5 |
| Story / Reel kapak | 1080×1920 | 9:16 |
| Carousel (her sayfa) | 1080×1080 | 1:1 |

---

## 2. İÇERİK TİPLERİ VE CANVA PROMPTLARI

### Tip 1: Günlük Piyasa Özeti
**Ne zaman:** Her işlem günü kapanış sonrası
**Veri kaynağı:** FMP API (batch-quote, sector-performance-snapshot)
**Canva prompt şablonu:**
```
Professional dark theme Instagram post for "FINZORA AI" brand. 
Title: "GÜNLÜK PİYASA ÖZETİ" 
Date: [TARİH]
Dark navy background (#0a0a0f) with emerald green (#00d4aa) and blue (#4a9eff) accents.
Show stock market data cards:
- S&P 500: [DEĞER] ([DEĞİŞİM]%)
- NASDAQ: [DEĞER] ([DEĞİŞİM]%)  
- VIX: [DEĞER]
- USD/TRY: [DEĞER]
Key insight box: "[GÜNÜN ÖNEMLİ GELİŞMESİ]"
Bottom: "@finzora" and "telegram: @finzora"
Clean fintech aesthetic, no photos of people.
```

### Tip 2: Hisse Analizi / Haftanın Hissesi
**Ne zaman:** Haftada 1-2 kez
**Veri kaynağı:** FMP API (profile, ratios-ttm, price-target-summary, technical-indicators)
**Canva prompt şablonu:**
```
Dark premium Instagram post for stock analysis. "FINZORA AI" brand.
Title: "HİSSE ANALİZİ" or "HAFTANIN HİSSESİ"
Stock: [SEMBOL] - [ŞİRKET ADI]
Key metrics in clean card layout:
- Fiyat: $[FIYAT] ([DEĞİŞİM]%)
- F/K: [PE]
- Hedef fiyat: $[HEDEF]
- RSI: [RSI]
- Sektör: [SEKTÖR]
Brief thesis: "[TEZ - 1 cümle]"
Dark background with neon green for bullish, red for bearish signals.
Bottom: "@finzora" branding. No photos.
```

### Tip 3: Eğitim Serisi
**Ne zaman:** Haftada 1-2 kez
**Konular:** Stop-loss, RSI, F/K oranı, temettü yatırımı, portföy çeşitlendirme, teknik analiz temelleri
**Canva prompt şablonu:**
```
Educational Instagram infographic for "FINZORA AI" brand.
Title: "[KONU BAŞLIĞI]"
Subtitle: "YATIRIM EĞİTİM SERİSİ"
Dark premium theme, NOT too dark - slightly lighter navy (#1a1a2e).
Infographic style with 3-4 key points, each with icons.
Points:
1. [MADDE 1]
2. [MADDE 2]
3. [MADDE 3]
4. [MADDE 4]
Gold (#ffd700) accent for education content.
Bottom: "kaydet, lazim olacak 🔖" and "@finzora"
Clean, readable typography. No photos.
```

### Tip 4: Portföy Performansı
**Ne zaman:** Haftalık (pazar günü)
**Veri kaynağı:** data/summary.json
**Araç:** Python Pillow (scripts/instagram_post_generator.py --type performans)
**Not:** Bu tip veri yoğun olduğu için Python ile otomatik üretim daha uygun

### Tip 5: Telegram Tanıtımı / CTA
**Ne zaman:** Haftada 1 kez
**Canva prompt şablonu:**
```
Instagram post promoting Telegram channel for "FINZORA AI" brand.
Title: "ÜCRETSİZ PİYASA ANALİZİ KANALI"
Telegram icon/branding with blue (#0088cc) accent.
Dark background.
Features list:
- 📊 Günlük piyasa analizi
- 🎯 Gerçek portföy performansı ($600K)
- 📚 Yatırım eğitim içerikleri
- ⚡ Anlık piyasa uyarıları
CTA: "@finzora - telegram da ara"
```

### Tip 6: Story / Reel Kapak
**Ne zaman:** Her gün
**Canva prompt şablonu:**
```
Instagram Story for "FINZORA AI" brand.
[story design_type: your_story]
Title: "[GÜNCEL BAŞLIK]"
Dynamic vertical layout with [KONU] visual elements.
Dark theme with [RENK] accents.
"@finzora" branding at bottom.
```

### Tip 7: Carousel (Çoklu Sayfa)
**Ne zaman:** Detaylı analizler, eğitim serileri
**Yöntem:** Canva'da birden fazla post oluşturup düzenle
**Sayfa yapısı:**
1. Kapak: başlık + konu
2-4. İçerik: her sayfada 1 ana fikir
5. CTA: telegram yönlendirmesi

---

## 3. CANVA KULLANIM KURALLARI

### Tasarım Oluşturma
```
Canva:generate-design
  design_type: "instagram_post" | "your_story"
  query: "[Yukarıdaki şablonlardan birini doldur]"
```

### Beğenilen Tasarımı Kaydetme
```
Canva:create-design-from-candidate
  job_id: "[generate-design'dan gelen job id]"
  candidate_id: "[beğenilen tasarımın candidate_id'si]"
```

### Tasarımı Düzenleme
1. `Canva:start-editing-transaction` → transaction_id al
2. `Canva:perform-editing-operations` → metin/görsel değiştir
3. `Canva:commit-editing-transaction` → kaydet

### Tasarımı Dışa Aktarma (Instagram'a yüklemek için)
```
Canva:export-design
  design_id: "[design id]"
  format: "png" | "jpg"
```

### Önemli Notlar
- Her zaman 4 alternatif tasarım üretilir, kullanıcıya seçtir
- Kullanıcı "3. sü güzel" derse → o candidate_id ile kaydet
- Tasarımda Türkçe karakter sorunları olabilir, düzenleme ile düzelt
- Koyu tema tercih ediliyor ama "çok koyu değil" → #1a1a2e kullan #0a0a0f yerine

---

## 4. PYTHON İLE VERİ BAZLI GÖRSEL ÜRETİMİ

### Mevcut Script
```bash
python scripts/instagram_post_generator.py --type piyasa
python scripts/instagram_post_generator.py --type performans
python scripts/instagram_post_generator.py --type egitim --konu "stop-loss nedir"
python scripts/instagram_post_generator.py --type telegram
```

### FMP API ile Canlı Veri Çekme
```python
import requests
FMP_API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE = "https://financialmodelingprep.com/stable"

# piyasa verileri
quotes = requests.get(f"{FMP_BASE}/batch-quote", 
    params={"symbols": "SPY,QQQ,VIXY,USO,GLD", "apikey": FMP_API_KEY}).json()

# sektör performansı
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
sectors = requests.get(f"{FMP_BASE}/sector-performance-snapshot",
    params={"date": today, "apikey": FMP_API_KEY}).json()
```

### Görsel GitHub'a Yükleyip URL Alma
Instagram API görseli URL üzerinden çeker. GitHub raw URL kullan:
```
https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/outputs/instagram/[dosya_adi].png
```

Workflow:
1. Görseli `outputs/instagram/` klasörüne kaydet
2. Git commit + push
3. Raw URL'yi Instagram API'ye ver

---

## 5. INSTAGRAM YAYINLAMA

### Config Dosyası
Tüm API bilgileri: `config/instagram_config.json`
- Instagram Business Account ID: `17841444988981487`
- Facebook Page ID: `758837067309184`
- Token: 60 günlük, haziran 2026'da yenilenmeli

### Yayınlama Scripti
```bash
# otomatik görsel + caption
python scripts/instagram_publisher.py --type piyasa

# özel görsel + caption
python scripts/instagram_publisher.py --image outputs/instagram/gorsel.png --caption "metin"

# önizleme (API çağrısı yapmadan test)
python scripts/instagram_publisher.py --type piyasa --dry-run
```

### Meta Graph API ile Manuel Yayınlama
```python
IG_ID = "17841444988981487"
TOKEN = "[config'den oku]"
BASE = "https://graph.facebook.com/v25.0"

# 1. medya container oluştur
resp = requests.post(f"{BASE}/{IG_ID}/media", data={
    "image_url": "https://raw.githubusercontent.com/...",
    "caption": "caption metni\n\n#hashtag1 #hashtag2",
    "access_token": TOKEN
})
container_id = resp.json()["id"]

# 2. yayınla
pub = requests.post(f"{BASE}/{IG_ID}/media_publish", data={
    "creation_id": container_id,
    "access_token": TOKEN
})
```

---

## 6. HASHTAG STRATEJİSİ

### Sabit Hashtagler (her postta)
```
#finzora #yatirim #borsa #amerikanborsasi
```

### Konu Bazlı Hashtagler
| Konu | Hashtagler |
|------|-----------|
| Piyasa özeti | `#sp500 #nasdaq #piyasa #borsaanalizi #wallstreet` |
| Hisse analizi | `#hisseyatirimi #hisseanalizi #temelanaliz #teknikanaliz` |
| Eğitim | `#yatirimegitimleri #borsaegitimi #finansokuryazarligi` |
| Temettü | `#temettu #pasifgelir #dividendyatirimi` |
| Performans | `#portfoy #performans #alfa #getiri` |

### Kurallar
- Maksimum 15 hashtag per post (Instagram algoritması için optimal)
- Sabit 4 + konu bazlı 5-8 + niche 2-3
- Hashtag'ler caption'ın en altında, 2 satır boşluktan sonra

---

## 7. CAPTION ŞABLONLARI

### Piyasa Özeti Caption
```
📊 günlük piyasa özeti | [TARİH]

amerikan borsasında bugün neler oldu? işte özet 👇

s&p 500: [DEĞER] ([DEĞİŞİM]%)
nasdaq: [DEĞER] ([DEĞİŞİM]%)
vix: [DEĞER]

[1-2 cümle günün özeti]

detaylı analiz ve portföy güncellemeleri için telegram kanalımıza katıl ⚡

telegram: @finzora (link bio da)

#finzora #yatirim #borsa #amerikanborsasi #sp500 #piyasa #borsaanalizi
```

### Hisse Analizi Caption
```
🎯 [SEMBOL] - [ŞİRKET ADI] analizi

fiyat: $[FIYAT] | f/k: [PE] | hedef: $[HEDEF]

[2-3 cümle neden ilginç / tez]

⚠️ bu yatırım tavsiyesi değildir, eğitim amaçlıdır.

detaylar telegram kanalımızda 👇
@finzora

#finzora #hisseyatirimi #[sembol küçük harf] #amerikanborsasi #borsaanalizi
```

### Eğitim Caption
```
📚 [KONU BAŞLIĞI]

[3-4 cümle açıklama, kolay anlaşılır dil]

kaydet, lazım olacak 🔖

daha fazla yatırım bilgisi için:
telegram: @finzora

#finzora #yatirim #borsaegitimi #finansokuryazarligi #yatirimegitimleri
```

---

## 8. HAFTALIK İÇERİK TAKVİMİ

| Gün | İçerik Tipi | Araç | Öncelik |
|-----|-------------|------|---------|
| Pazartesi | Haftalık piyasa beklentisi | Canva | Yüksek |
| Salı | Eğitim serisi | Canva | Orta |
| Çarşamba | Hisse analizi | Canva + FMP | Yüksek |
| Perşembe | Portföy performansı | Python otomatik | Orta |
| Cuma | Kapanış özeti / hafta değerlendirmesi | Canva | Yüksek |
| Cumartesi | Reel: hafta özeti (video) | Canva video editör | Düşük |
| Pazar | Telegram tanıtımı / CTA | Canva | Orta |

### Story Planı (her gün)
- Piyasa açılışı: "bugün piyasada ne bekliyoruz?"
- Gün içi: önemli gelişme varsa
- Kapanış: günün özeti

---

## 9. VİDEO / REEL STRATEJİSİ

### Video Tipleri
1. **Piyasa özeti reeli** (15-30 sn): hızlı veri gösterimi, metin overlay
2. **Hisse analizi reeli** (30-60 sn): grafik + temel veriler + tez
3. **Eğitim reeli** (30-60 sn): tek konu, adım adım açıklama
4. **Portföy update** (15-30 sn): haftalık performans animasyonu

### Video Oluşturma Yöntemleri
1. **Canva Video Editör** (önerilen): Canva'da video template seç, düzenle, indir
2. **Python moviepy** (otomatik): veri bazlı animasyonlu grafikler
   ```bash
   pip install moviepy Pillow numpy
   ```
3. **FFmpeg** (ileri seviye): image sequence → video dönüşümü

### Reel İpuçları
- İlk 3 saniye kancası: merak uyandıran soru veya şaşırtıcı veri
- Altyazı zorunlu (sesli izlenmeyebilir)
- Dikey format (9:16)
- Trending ses kullan (Canva editöründen)
- CTA: son karede "@finzora telegram"

---

## 10. WORKFLOW ÖZETİ

### Hızlı Post (Claude'a söyle)
```
"bugün için piyasa özeti instagram postu yap"
→ Claude FMP'den veri çeker
→ Canva ile 4 tasarım üretir
→ Kullanıcı seçer
→ Canva hesabına kaydedilir
→ Caption hazırlanır
→ Yayınlanır
```

### Otomatik Post (Script)
```bash
cd portfolio-tracker
python scripts/instagram_post_generator.py --type performans
python scripts/instagram_publisher.py --type performans
```

### Dosya Yapısı
```
config/instagram_config.json     ← API bilgileri
scripts/instagram_publisher.py   ← yayınlama
scripts/instagram_post_generator.py  ← Pillow ile görsel
scripts/instagram_setup.py       ← kurulum / token yenileme
scripts/instagram_test.py        ← bağlantı testi
outputs/instagram/               ← üretilen görseller
```
