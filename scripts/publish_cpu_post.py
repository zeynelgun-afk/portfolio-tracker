#!/usr/bin/env python3
"""
CPU Arz Darboğazı - Instagram Carousel + Story Yayınlama
Finzora AI | 4 Nisan 2026

Kullanım:
  python3 scripts/publish_cpu_post.py                         # her ikisini yayınla
  python3 scripts/publish_cpu_post.py --type carousel_only    # sadece carousel
  python3 scripts/publish_cpu_post.py --type story_only       # sadece story
  python3 scripts/publish_cpu_post.py --type carousel_and_story
"""
import requests, json, time, sys, os, argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "instagram_config.json")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

IG_ID = config["instagram_account_id"]
TOKEN = config["access_token"]
API = f"https://graph.facebook.com/{config['graph_api_version']}"
IMG_DIR = os.path.join(BASE_DIR, "outputs", "instagram")

CAPTION = """🔴 CPU arz krizi: AI nin yeni darboğazı

herkes GPU darboğazı konuşuyor ama asıl sorun başka yerde.

AI artık sadece soru-cevap değil. otonom ajanlar planlama yapıyor, kod yazıyor, veritabanı sorguluyor. tüm bu işler CPU üzerinde dönüyor.

sonuç?
→ intel teslimat süresi 6 aya uzadı
→ AMD 8-10 hafta bekleme süresi
→ sunucu CPU fiyatları %10-15 arttı
→ 2026 kapasitesi neredeyse tamamen tükendi

enerji tarafı daha da korkutucu. ABD veri merkezleri ülke elektriğinin %4 ünü tüketiyor.

izlenecek 5 hisse: QCOM, AMD, INTC, MU, MRVL

detaylı analiz ve $600K gerçek portföy takibi için telegram grubuna katıl 👇

🔗 t.me/+nWm5M7VnxEEzNGQ0
🌐 finzora.ai

⚠️ yatırım tavsiyesi değildir, eğitim amaçlıdır.


#finzora #yatirim #borsa #amerikanborsasi #cpu #semiconductor #yarileiletken #qualcomm #amd #intel #nvidia #borsaanalizi #hisseyatirimi #yapayzekaYatirim"""

FIRST_COMMENT = "hangi hisseyi en cazip buluyorsunuz? 👇"

def upload_image(filepath):
    print(f"  📤 {os.path.basename(filepath)}...")
    r = requests.post("https://catbox.moe/user/api.php", 
        files={"fileToUpload": open(filepath, "rb")},
        data={"reqtype": "fileupload"})
    url = r.text.strip()
    if url.startswith("http"):
        print(f"     ✓ {url}")
        return url
    print(f"     ✗ yükleme hatası: {url}")
    return None

def ig_post(endpoint, data):
    r = requests.post(f"{API}/{endpoint}", data={**data, "access_token": TOKEN})
    try:
        return r.json()
    except:
        print(f"     ✗ API yanıt hatası: {r.status_code} {r.text[:200]}")
        return {}

def ig_get(endpoint, params={}):
    r = requests.get(f"{API}/{endpoint}", params={**params, "access_token": TOKEN})
    try:
        return r.json()
    except:
        return {}

def wait_ready(container_id, timeout=90):
    for _ in range(timeout // 5):
        s = ig_get(container_id, {"fields": "status_code"}).get("status_code", "")
        if s == "FINISHED": return True
        if s == "ERROR": return False
        time.sleep(5)
    return False

def publish_carousel():
    print("\n" + "="*55)
    print("  📸 CAROUSEL POST")
    print("="*55)
    
    slides = [f"slide{i}_{'cover' if i==1 else 'problem' if i==2 else 'energy' if i==3 else 'stocks' if i==4 else 'cta'}.png" for i in range(1,6)]
    
    # Upload
    print("\n  adım 1: görseller yükleniyor...\n")
    urls = []
    for s in slides:
        path = os.path.join(IMG_DIR, s)
        if not os.path.exists(path):
            print(f"  ✗ dosya yok: {path}")
            return False
        url = upload_image(path)
        if not url: return False
        urls.append(url)
        time.sleep(1)
    
    # Containers
    print("\n  adım 2: container'lar oluşturuluyor...\n")
    cids = []
    for i, url in enumerate(urls):
        print(f"  [{i+1}/5] container...")
        r = ig_post(f"{IG_ID}/media", {"image_url": url, "is_carousel_item": "true"})
        if "id" in r:
            cids.append(r["id"])
            print(f"     ✓ {r['id']}")
        else:
            err = r.get("error", {}).get("message", json.dumps(r))
            print(f"     ✗ {err}")
            return False
        time.sleep(3)
    
    # Carousel
    print(f"\n  adım 3: carousel oluşturuluyor...")
    cr = ig_post(f"{IG_ID}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(cids),
        "caption": CAPTION
    })
    if "id" not in cr:
        print(f"  ✗ {cr.get('error', {}).get('message', json.dumps(cr))}")
        return False
    
    car_id = cr["id"]
    print(f"     ✓ carousel: {car_id}")
    print(f"     ⏳ işleniyor...")
    
    if not wait_ready(car_id):
        print(f"  ✗ işleme başarısız veya zaman aşımı")
        return False
    
    # Publish
    print(f"  adım 4: yayınlanıyor...")
    pr = ig_post(f"{IG_ID}/media_publish", {"creation_id": car_id})
    if "id" not in pr:
        print(f"  ✗ {pr.get('error', {}).get('message', json.dumps(pr))}")
        return False
    
    post_id = pr["id"]
    print(f"\n  ✅ CAROUSEL YAYINLANDI!")
    print(f"     Post ID: {post_id}")
    
    # First comment
    time.sleep(3)
    print(f"  💬 ilk yorum ekleniyor...")
    cmr = ig_post(f"{post_id}/comments", {"message": FIRST_COMMENT})
    if cmr.get("id"):
        print(f"     ✓ yorum eklendi")
    
    return True

def publish_story():
    print("\n" + "="*55)
    print("  📱 STORY")
    print("="*55)
    
    path = os.path.join(IMG_DIR, "story_cpu_krizi.png")
    if not os.path.exists(path):
        print(f"  ✗ dosya yok: {path}")
        return False
    
    print("\n  adım 1: görsel yükleniyor...\n")
    url = upload_image(path)
    if not url: return False
    
    print(f"\n  adım 2: story container...")
    sr = ig_post(f"{IG_ID}/media", {"image_url": url, "media_type": "STORIES"})
    if "id" not in sr:
        print(f"  ✗ {sr.get('error', {}).get('message', json.dumps(sr))}")
        return False
    
    sid = sr["id"]
    print(f"     ✓ {sid}")
    print(f"     ⏳ işleniyor...")
    
    if not wait_ready(sid):
        print(f"  ✗ işleme başarısız")
        return False
    
    print(f"  adım 3: yayınlanıyor...")
    pr = ig_post(f"{IG_ID}/media_publish", {"creation_id": sid})
    if "id" not in pr:
        print(f"  ✗ {pr.get('error', {}).get('message', json.dumps(pr))}")
        return False
    
    print(f"\n  ✅ STORY YAYINLANDI!")
    print(f"     Story ID: {pr['id']}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", default="carousel_and_story",
        choices=["carousel_and_story", "carousel_only", "story_only"])
    args = parser.parse_args()
    
    print("="*55)
    print("  FINZORA AI — Instagram Yayınlama")
    print("  CPU Arz Darboğazı | 4 Nisan 2026")
    print("="*55)
    
    ok = True
    if args.type in ("carousel_and_story", "carousel_only"):
        ok = publish_carousel() and ok
    if args.type in ("carousel_and_story", "story_only"):
        ok = publish_story() and ok
    
    print(f"\n{'='*55}")
    print(f"  {'✅ TAMAMLANDI' if ok else '⚠️ BAZI HATALAR OLUŞTU'}")
    print(f"{'='*55}")
    
    sys.exit(0 if ok else 1)
