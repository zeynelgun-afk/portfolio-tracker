#!/usr/bin/env python3
"""Video story yayınlama — tek seferlik veya tekrar kullanılabilir"""
import requests, json, time, sys, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "config", "instagram_config.json")) as f:
    config = json.load(f)

IG_ID = config["instagram_account_id"]
TOKEN = config["access_token"]
API = f"https://graph.facebook.com/{config['graph_api_version']}"

VIDEO_URL = sys.argv[1] if len(sys.argv) > 1 else "https://files.catbox.moe/deljsw.mp4"

print("="*50)
print("  FINZORA AI — Video Story Yayınlama")
print("="*50)

# Step 1: Create video story container
print(f"\n📱 Video container oluşturuluyor...")
print(f"   URL: {VIDEO_URL}")
r = requests.post(f"{API}/{IG_ID}/media", data={
    "video_url": VIDEO_URL,
    "media_type": "STORIES",
    "access_token": TOKEN
})
result = r.json()
print(f"   Response: {json.dumps(result)}")

if "id" not in result:
    print(f"✗ Hata: {result.get('error', {}).get('message', 'bilinmeyen')}")
    sys.exit(1)

container_id = result["id"]
print(f"   ✓ Container: {container_id}")

# Step 2: Wait for video processing
print(f"\n⏳ Video işleniyor...")
for i in range(30):
    r2 = requests.get(f"{API}/{container_id}", params={
        "fields": "status_code,status",
        "access_token": TOKEN
    })
    status = r2.json()
    code = status.get("status_code", "")
    print(f"   [{i+1}/30] Durum: {code}")
    if code == "FINISHED":
        break
    elif code == "ERROR":
        print(f"   ✗ İşleme hatası: {json.dumps(status)}")
        sys.exit(1)
    time.sleep(5)

# Step 3: Publish
print(f"\n🚀 Yayınlanıyor...")
r3 = requests.post(f"{API}/{IG_ID}/media_publish", data={
    "creation_id": container_id,
    "access_token": TOKEN
})
pub = r3.json()
print(f"   Response: {json.dumps(pub)}")

if "id" in pub:
    print(f"\n✅ VIDEO STORY YAYINLANDI!")
    print(f"   Story ID: {pub['id']}")
else:
    print(f"\n✗ Yayınlama hatası: {pub.get('error', {}).get('message', '')}")
    sys.exit(1)
