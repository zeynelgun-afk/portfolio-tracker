#!/usr/bin/env python3
"""
Savaşta Borsa: Panik mi Fırsat mı? - Instagram Carousel + Video Story Yayınlama
Finzora AI | 4 Nisan 2026

Kullanım:
  python3 scripts/publish_savas_post.py                         # her ikisini yayınla
  python3 scripts/publish_savas_post.py --type carousel_only    # sadece carousel
  python3 scripts/publish_savas_post.py --type story_only       # sadece story
  python3 scripts/publish_savas_post.py --type carousel_and_story
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

CAPTION = """⚡ savas zamaninda borsa: panik mi yoksa firsat mi?

iran savasi 5. haftasinda. petrol $110 ustu. s&p 500 son 4 yilin en kotu ceyregini kapatti.

ama tarih net bir sey soyluyor: korfez savasi, afganistan, ukrayna, israel-iran... her seferinde piyasalar 12 ay icinde toparlanmis.

panik satan her zaman kaybetmis. stratejik hareket eden kazanmis.

kaydir, veriyi gor, stratejini kur.

detayli analiz ve gercek portfoy takibi icin telegram kanalimiza katil 👇

🔗 t.me/+nWm5M7VnxEEzNGQ0
🌐 finzora.ai

⚠️ yatirim tavsiyesi degildir, egitim amaclidir.


#finzora #yatirim #borsa #amerikanborsasi #sp500 #nasdaq #piyasa #borsaanalizi #wallstreet #petrol #kriz #yatirimegitimleri #borsaegitimi #finansokuryazarligi #portfoy"""

FIRST_COMMENT = "sizce savas sonrasi en cok hangi sektor toparlanir? 👇"

CAROUSEL_FILES = [
    "slide_1_cover.png",
    "slide_2_tarih.png",
    "slide_3_durum.png",
    "slide_4_strateji.png",
    "slide_5_cta.png",
]

STORY_FILE = "story_savas_borsa.mp4"

def upload_file(filepath):
    print(f"  📤 {os.path.basename(filepath)}...")
    r = requests.post("https://catbox.moe/user/api.php",
        files={"fileToUpload": open(filepath, "rb")},
        data={"reqtype": "fileupload"})
    url = r.text.strip()
    if url.startswith("http"):
        print(f"     ✓ {url}")
        return url
    print(f"     ✗ yukleme hatasi: {url}")
    return None

def ig_post(endpoint, data):
    r = requests.post(f"{API}/{endpoint}", data={**data, "access_token": TOKEN})
    try:
        return r.json()
    except:
        print(f"     ✗ API yanit hatasi: {r.status_code} {r.text[:200]}")
        return {}

def ig_get(endpoint, params={}):
    r = requests.get(f"{API}/{endpoint}", params={**params, "access_token": TOKEN})
    try:
        return r.json()
    except:
        return {}

def wait_ready(container_id, timeout=120):
    for _ in range(timeout // 5):
        s = ig_get(container_id, {"fields": "status_code"}).get("status_code", "")
        if s == "FINISHED": return True
        if s == "ERROR": return False
        time.sleep(5)
    return False

def publish_carousel():
    print("\n" + "="*55)
    print("  📸 CAROUSEL POST - Savas Zamaninda Borsa")
    print("="*55)

    # Upload
    print("\n  adim 1: gorseller yukleniyor...\n")
    urls = []
    for s in CAROUSEL_FILES:
        path = os.path.join(IMG_DIR, s)
        if not os.path.exists(path):
            print(f"  ✗ dosya yok: {path}")
            return False
        url = upload_file(path)
        if not url: return False
        urls.append(url)
        time.sleep(1)

    # Containers
    print(f"\n  adim 2: container lar olusturuluyor...\n")
    cids = []
    for i, url in enumerate(urls):
        print(f"  [{i+1}/{len(urls)}] container...")
        success = False
        for attempt in range(3):
            r = ig_post(f"{IG_ID}/media", {"image_url": url, "is_carousel_item": "true"})
            if "id" in r:
                cids.append(r["id"])
                print(f"     ✓ {r['id']}")
                success = True
                break
            else:
                err = r.get("error", {}).get("message", json.dumps(r))
                print(f"     ✗ deneme {attempt+1}/3: {err}")
                time.sleep(10)
        if not success:
            return False
        time.sleep(6)

    # Carousel
    time.sleep(5)
    print(f"\n  adim 3: carousel olusturuluyor...")
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
    print(f"     ⏳ isleniyor...")

    if not wait_ready(car_id):
        print(f"  ✗ isleme basarisiz veya zaman asimi")
        return False

    # Publish
    print(f"  adim 4: yayinlaniyor...")
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

def publish_video_story():
    print("\n" + "="*55)
    print("  📱 VIDEO STORY - Savas Zamaninda Borsa")
    print("="*55)

    path = os.path.join(IMG_DIR, STORY_FILE)
    if not os.path.exists(path):
        print(f"  ✗ dosya yok: {path}")
        return False

    print("\n  adim 1: video yukleniyor...\n")
    url = upload_file(path)
    if not url: return False

    print(f"\n  adim 2: story container (video)...")
    sr = ig_post(f"{IG_ID}/media", {
        "video_url": url,
        "media_type": "STORIES"
    })
    if "id" not in sr:
        print(f"  ✗ {sr.get('error', {}).get('message', json.dumps(sr))}")
        return False

    sid = sr["id"]
    print(f"     ✓ {sid}")
    print(f"     ⏳ video isleniyor (bu biraz surebilir)...")

    if not wait_ready(sid, timeout=180):
        print(f"  ✗ isleme basarisiz")
        return False

    print(f"  adim 3: yayinlaniyor...")
    pr = ig_post(f"{IG_ID}/media_publish", {"creation_id": sid})
    if "id" not in pr:
        print(f"  ✗ {pr.get('error', {}).get('message', json.dumps(pr))}")
        return False

    print(f"\n  ✅ VIDEO STORY YAYINLANDI!")
    print(f"     Story ID: {pr['id']}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", default="carousel_and_story",
        choices=["carousel_and_story", "carousel_only", "story_only"])
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  🔥 FINZORA AI - SAVAS ZAMANINDA BORSA")
    print(f"  Mod: {args.type}")
    print("="*55)

    ok = True
    if args.type in ("carousel_and_story", "carousel_only"):
        ok = publish_carousel() and ok

    if args.type in ("carousel_and_story", "story_only"):
        ok = publish_video_story() and ok

    print("\n" + "="*55)
    if ok:
        print("  🎉 TUM YAYINLAR BASARILI!")
    else:
        print("  ⚠️ BAZI YAYINLARDA HATA OLUSTU")
    print("="*55 + "\n")
    sys.exit(0 if ok else 1)
