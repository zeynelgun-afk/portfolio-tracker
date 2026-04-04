#!/usr/bin/env python3
"""7 Hata Eğitim Carousel — Instagram Yayınlama"""
import requests, json, time, sys, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "config", "instagram_config.json")) as f:
    config = json.load(f)

IG_ID = config["instagram_account_id"]
TOKEN = config["access_token"]
API = f"https://graph.facebook.com/{config['graph_api_version']}"
IMG_DIR = os.path.join(BASE_DIR, "outputs", "instagram", "7mistakes")

CAPTION = """⚠️ yeni başlayanların yaptığı 7 hata

borsada para kaybetmenin en yaygın nedenleri. yeni yatırımcıların %90 ı bu hataları yapıyor.

1. duyguyla işlem yapmak — panik ve FOMO düşmanın
2. stop-loss kullanmamak — küçük kayıp büyük felakete dönüşür
3. tek hisseye yüklemek — çeşitlendirme hayat kurtarır
4. başkasının tavsiyesiyle almak — kendi ödevini yap
5. düşeni kovalamak — ucuz ≠ değerli
6. kârı erken kesip zararı tutmak — tam tersini yap
7. araştırmadan girmek — 5 dakika araştırma 5000 dolar kurtarır

bu listeyi kaydet 🔖 her işlemden önce kontrol listesi olarak kullan.

yatırıma yeni başlayan bir arkadaşına gönder 📩

detaylı analiz ve $600K gerçek portföy takibi 👇
🔗 t.me/+nWm5M7VnxEEzNGQ0
🌐 finzora.ai

⚠️ yatırım tavsiyesi değildir, eğitim amaçlıdır.


#finzora #yatirim #borsa #borsaegitimi #yatirimegitimleri #stoploss #amerikanborsasi #finansokuryazarligi #yeniyatirimci #yatirimpsikolojisi #borsahatalari #portfoy #riskYonetimi #hisseSenedi #borsaanalizi"""

FIRST_COMMENT = "sen bu hatalardan hangisini yaptın? 👇 yorumlarda paylaş"

def upload(filepath):
    print(f"  📤 {os.path.basename(filepath)}...")
    r = requests.post("https://catbox.moe/user/api.php",
        files={"fileToUpload": open(filepath, "rb")},
        data={"reqtype": "fileupload"})
    url = r.text.strip()
    if url.startswith("http"):
        print(f"     ✓ {url}")
        return url
    print(f"     ✗ yükleme hatası")
    return None

def ig(endpoint, data):
    r = requests.post(f"{API}/{endpoint}", data={**data, "access_token": TOKEN})
    try: return r.json()
    except: return {}

def wait_ready(cid, timeout=120):
    for _ in range(timeout // 5):
        s = requests.get(f"{API}/{cid}", params={"fields": "status_code", "access_token": TOKEN}).json().get("status_code", "")
        if s == "FINISHED": return True
        if s == "ERROR": return False
        time.sleep(5)
    return False

def main():
    slides = sorted([f for f in os.listdir(IMG_DIR) if f.endswith('.png')])
    print(f"{'='*55}")
    print(f"  FINZORA AI — 7 Hata Eğitim Carousel")
    print(f"  {len(slides)} slide yayınlanıyor")
    print(f"{'='*55}")

    # Upload
    print(f"\n📤 Görseller yükleniyor...\n")
    urls = []
    for s in slides:
        url = upload(os.path.join(IMG_DIR, s))
        if not url:
            print("✗ Yükleme başarısız, çıkılıyor")
            sys.exit(1)
        urls.append(url)
        time.sleep(1)

    # Containers
    print(f"\n📸 Container'lar oluşturuluyor...\n")
    cids = []
    for i, url in enumerate(urls):
        print(f"  [{i+1}/{len(urls)}] container...")
        r = ig(f"{IG_ID}/media", {"image_url": url, "is_carousel_item": "true"})
        if "id" in r:
            cids.append(r["id"])
            print(f"     ✓ {r['id']}")
        else:
            print(f"     ✗ {r.get('error',{}).get('message',json.dumps(r))}")
            sys.exit(1)
        time.sleep(3)

    # Carousel
    print(f"\n  Carousel oluşturuluyor...")
    cr = ig(f"{IG_ID}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(cids),
        "caption": CAPTION
    })
    if "id" not in cr:
        print(f"  ✗ {cr.get('error',{}).get('message','')}")
        sys.exit(1)

    car_id = cr["id"]
    print(f"     ✓ {car_id}")
    print(f"     ⏳ işleniyor...")

    if not wait_ready(car_id):
        print(f"  ✗ zaman aşımı")
        sys.exit(1)

    # Publish
    pr = ig(f"{IG_ID}/media_publish", {"creation_id": car_id})
    if "id" not in pr:
        print(f"  ✗ {pr.get('error',{}).get('message','')}")
        sys.exit(1)

    post_id = pr["id"]
    print(f"\n  ✅ CAROUSEL YAYINLANDI! Post ID: {post_id}")

    # First comment (engagement)
    time.sleep(3)
    cmr = ig(f"{post_id}/comments", {"message": FIRST_COMMENT})
    if cmr.get("id"):
        print(f"  💬 İlk yorum eklendi")

    # Second comment (clickable link)
    time.sleep(2)
    LINK_COMMENT = "📱 telegram grubuna katıl: https://t.me/+nWm5M7VnxEEzNGQ0\n🌐 site: https://finzora.ai"
    cmr2 = ig(f"{post_id}/comments", {"message": LINK_COMMENT})
    if cmr2.get("id"):
        print(f"  🔗 Link yorumu eklendi (tıklanabilir)")

    print(f"\n{'='*55}")
    print(f"  ✅ TAMAMLANDI")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
