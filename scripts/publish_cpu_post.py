#!/usr/bin/env python3
"""
CPU Arz Darboğazı - Instagram Carousel + Story Yayınlama
Finzora AI | 4 Nisan 2026

Kullanım: python3 scripts/publish_cpu_post.py
"""
import requests
import json
import time
import sys
import os

# Config
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "instagram_config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

IG_ID = config["instagram_account_id"]
TOKEN = config["access_token"]
BASE = f"https://graph.facebook.com/{config['graph_api_version']}"

# Görselleri catbox.moe'ye yükle
def upload_image(filepath):
    """Görseli catbox.moe'ye yükle, public URL döndür"""
    print(f"  Yükleniyor: {os.path.basename(filepath)}...")
    r = requests.post("https://catbox.moe/user/api.php", files={
        "fileToUpload": open(filepath, "rb")
    }, data={"reqtype": "fileupload"})
    url = r.text.strip()
    print(f"  ✓ {url}")
    return url

# Instagram API fonksiyonları
def create_container(image_url, is_carousel_item=True):
    """Tek görsel için container oluştur"""
    data = {
        "image_url": image_url,
        "access_token": TOKEN
    }
    if is_carousel_item:
        data["is_carousel_item"] = "true"
    
    r = requests.post(f"{BASE}/{IG_ID}/media", data=data)
    result = r.json()
    if "id" in result:
        return result["id"]
    else:
        print(f"  ✗ Hata: {result.get('error', {}).get('message', json.dumps(result))}")
        return None

def create_carousel(container_ids, caption):
    """Carousel container oluştur"""
    data = {
        "media_type": "CAROUSEL",
        "children": ",".join(container_ids),
        "caption": caption,
        "access_token": TOKEN
    }
    r = requests.post(f"{BASE}/{IG_ID}/media", data=data)
    result = r.json()
    if "id" in result:
        return result["id"]
    else:
        print(f"  ✗ Carousel hatası: {result.get('error', {}).get('message', json.dumps(result))}")
        return None

def create_story(image_url):
    """Story container oluştur"""
    data = {
        "image_url": image_url,
        "media_type": "STORIES",
        "access_token": TOKEN
    }
    r = requests.post(f"{BASE}/{IG_ID}/media", data=data)
    result = r.json()
    if "id" in result:
        return result["id"]
    else:
        print(f"  ✗ Story hatası: {result.get('error', {}).get('message', json.dumps(result))}")
        return None

def publish(creation_id):
    """Container'ı yayınla"""
    r = requests.post(f"{BASE}/{IG_ID}/media_publish", data={
        "creation_id": creation_id,
        "access_token": TOKEN
    })
    result = r.json()
    if "id" in result:
        return result["id"]
    else:
        print(f"  ✗ Yayınlama hatası: {result.get('error', {}).get('message', json.dumps(result))}")
        return None

def wait_for_processing(container_id, max_wait=60):
    """Container işlenene kadar bekle"""
    for i in range(max_wait // 5):
        r = requests.get(f"{BASE}/{container_id}", params={
            "fields": "status_code",
            "access_token": TOKEN
        })
        status = r.json().get("status_code", "")
        if status == "FINISHED":
            return True
        elif status == "ERROR":
            print(f"  ✗ İşleme hatası!")
            return False
        time.sleep(5)
    return False

# Caption
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

# İlk yorum
FIRST_COMMENT = "hangi hisseyi en cazip buluyorsunuz? 👇"

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    img_dir = os.path.join(base_dir, "outputs", "instagram")
    
    slides = [
        os.path.join(img_dir, "slide1_cover.png"),
        os.path.join(img_dir, "slide2_problem.png"),
        os.path.join(img_dir, "slide3_energy.png"),
        os.path.join(img_dir, "slide4_stocks.png"),
        os.path.join(img_dir, "slide5_cta.png"),
    ]
    story_path = os.path.join(img_dir, "story_cpu_krizi.png")
    
    # Dosyaları kontrol et
    for s in slides + [story_path]:
        if not os.path.exists(s):
            print(f"✗ Dosya bulunamadı: {s}")
            sys.exit(1)
    
    print("=" * 55)
    print("  FINZORA AI — Instagram Yayınlama")
    print("  CPU Arz Darboğazı Carousel + Story")
    print("=" * 55)
    
    # === ADIM 1: Görselleri yükle ===
    print("\n📤 ADIM 1: Görseller yükleniyor (catbox.moe)...\n")
    slide_urls = []
    for s in slides:
        url = upload_image(s)
        slide_urls.append(url)
        time.sleep(1)
    
    story_url = upload_image(story_path)
    
    # === ADIM 2: Carousel ===
    print("\n📸 ADIM 2: Carousel post oluşturuluyor...\n")
    container_ids = []
    for i, url in enumerate(slide_urls):
        print(f"  [{i+1}/5] Container oluşturuluyor...")
        cid = create_container(url, is_carousel_item=True)
        if cid:
            container_ids.append(cid)
            print(f"  ✓ ID: {cid}")
        time.sleep(3)
    
    if len(container_ids) != 5:
        print(f"\n✗ Sadece {len(container_ids)}/5 container oluşturuldu, devam edilemiyor.")
        sys.exit(1)
    
    print(f"\n  Carousel container oluşturuluyor...")
    carousel_id = create_carousel(container_ids, CAPTION)
    
    if carousel_id:
        print(f"  ✓ Carousel ID: {carousel_id}")
        print(f"  İşleniyor, bekleniyor...")
        
        if wait_for_processing(carousel_id):
            post_id = publish(carousel_id)
            if post_id:
                print(f"\n  ✅ CAROUSEL YAYINLANDI! Post ID: {post_id}")
                
                # İlk yorum ekle
                print(f"  İlk yorum ekleniyor...")
                time.sleep(3)
                cr = requests.post(f"{BASE}/{post_id}/comments", data={
                    "message": FIRST_COMMENT,
                    "access_token": TOKEN
                })
                if cr.json().get("id"):
                    print(f"  ✓ İlk yorum eklendi: \"{FIRST_COMMENT}\"")
            else:
                print(f"\n  ✗ Carousel yayınlanamadı")
        else:
            print(f"\n  ✗ Carousel işleme zaman aşımı")
    
    # === ADIM 3: Story ===
    print(f"\n📱 ADIM 3: Story yayınlanıyor...\n")
    story_cid = create_story(story_url)
    
    if story_cid:
        print(f"  ✓ Story container: {story_cid}")
        print(f"  İşleniyor...")
        
        if wait_for_processing(story_cid):
            story_post_id = publish(story_cid)
            if story_post_id:
                print(f"\n  ✅ STORY YAYINLANDI! Story ID: {story_post_id}")
            else:
                print(f"\n  ✗ Story yayınlanamadı")
        else:
            print(f"\n  ✗ Story işleme zaman aşımı")
    
    print(f"\n{'='*55}")
    print(f"  İŞLEM TAMAMLANDI")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
