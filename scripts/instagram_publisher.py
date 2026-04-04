#!/usr/bin/env python3
"""
finzora ai - instagram otomatik paylasim
meta graph api kullanarak instagram isletme hesabina post atar

kurulum:
  1. developers.facebook.com dan uygulama olustur
  2. instagram graph api izni al
  3. .env dosyasina tokenlari ekle

kullanim:
  python scripts/instagram_publisher.py --image outputs/instagram/piyasa_20260331.png --caption "gunluk piyasa ozeti..."
  python scripts/instagram_publisher.py --type piyasa   (otomatik gorsel + caption)
  python scripts/instagram_publisher.py --type performans
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# --- YAPILANDIRMA ---
# config/instagram_config.json dosyasindan oku, yoksa ortam degiskenlerinden
CONFIG_PATH = REPO_ROOT / "config" / "instagram_config.json"

def load_ig_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_page_access_token(user_token, page_id, api_base):
    """user tokendan page token al (page token suresiz gecerli)"""
    try:
        r = requests.get(f"{api_base}/me/accounts",
                        params={"access_token": user_token}, timeout=30)
        if r.status_code == 200:
            for page in r.json().get("data", []):
                if page["id"] == page_id:
                    return page.get("access_token")
    except Exception as e:
        print(f"page token alinamadi: {e}")
    return None

_config = load_ig_config()
INSTAGRAM_ACCOUNT_ID = _config.get("instagram_account_id") or os.getenv("INSTAGRAM_ACCOUNT_ID", "")
META_ACCESS_TOKEN = _config.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
GRAPH_API_VERSION = _config.get("graph_api_version", "v25.0")
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
IMGBB_API_KEY = _config.get("imgbb_api_key") or os.getenv("IMGBB_API_KEY", "")
FB_PAGE_ID = _config.get("facebook_page_id", "758837067309184")

# page token al (suresiz gecerli, her calistirmada yenilenir)
_page_token = get_page_access_token(META_ACCESS_TOKEN, FB_PAGE_ID, GRAPH_API_BASE)
if _page_token:
    META_ACCESS_TOKEN = _page_token

# gorsel sunucu - instagram api gorseli url uzerinden ceker
# github raw url veya imgbb/cloudinary gibi bir servis kullanilabilir
IMAGE_HOST_BASE = os.getenv("IMAGE_HOST_BASE", "")


# --- HAZIR CAPTIONLAR ---

def get_caption_piyasa():
    return """📊 gunluk piyasa ozeti

amerikan borsasinda bugun neler oldu? iste ozet 👇

detayli analiz ve portfoy guncellemeleri icin telegram kanalimiza katil

⚡ telegram: @finzora (link bio da)

#borsayatirimi #amerikanborsasi #yatirim #sp500 #piyasa #borsa #finzora #hisseyatirimi"""


def get_caption_performans():
    try:
        with open(REPO_ROOT / "data" / "summary.json", "r", encoding="utf-8") as f:
            s = json.load(f)
        total_ret = s.get("toplam_kar_zarar_yuzde", 0)
        spy = s.get("benchmark_spy", 0)
        alpha = s.get("alpha", 0)
        return f"""💰 haftalik portfoy performansi

3 portfoy, $600K sermaye, gercek sonuclar 📈

spy: {spy:+.1f}% | finzora: {total_ret:+.1f}%
alfa: {alpha:+.1f} puan

gercek portfoy, gercek sonuclar. detaylar telegram kanalimizda 👇
@finzora

#portfoy #yatirim #borsa #performans #alfa #sp500 #finzora #amerikanborsasi"""
    except Exception:
        return "💰 portfoy performansi icin telegram: @finzora\n\n#finzora #yatirim #borsa"


def get_caption_egitim():
    return """📚 amerikan borsasina yatirim yapmak istiyorsan bu 4 adimi takip et

turkiyeden amerikan borsasina yatirim yapmak artik cok kolay. dogru stratejiyle baslamak onemli 👇

1️⃣ guvenilir bir araci kurumda hesap ac
2️⃣ yatirim yapacagin sirketi arastir
3️⃣ kucuk miktarlarla basla
4️⃣ stop-loss kullan, disiplinli ol

kaydet, lazim olacak 🔖

#borsayatirimi #amerikanborsasi #yatirim #sp500 #hisseyatirimi #yatirimegitimleri #finzora"""


def get_caption_telegram():
    return """📢 ucretsiz piyasa analizi kanali

her gun amerikan borsasi hakkinda detayli analiz, portfoy guncellemeleri ve yatirim egitim icerikleri paylasiyorum

ne bulacaksin 👇
📊 gunluk piyasa ozeti
🎯 gercek portfoy performansi ($600K)
📚 yatirim egitim icerikleri
⚡ anlik piyasa uyarilari

tamamen ucretsiz, reklamsiz

telegram: @finzora
link bio da 👆

#telegram #yatirim #borsa #amerikanborsasi #piyasa #finzora"""


CAPTION_MAP = {
    "piyasa": get_caption_piyasa,
    "performans": get_caption_performans,
    "egitim": get_caption_egitim,
    "telegram": get_caption_telegram,
}


# --- INSTAGRAM API ---

def upload_to_instagram(image_url, caption):
    """
    instagram isletme hesabina gorsel paylas
    iki adimli surec:
      1. medya container olustur (gorsel url + caption)
      2. container i yayinla
    """
    if not INSTAGRAM_ACCOUNT_ID or not META_ACCESS_TOKEN:
        print("hata: INSTAGRAM_ACCOUNT_ID ve META_ACCESS_TOKEN ortam degiskenleri tanimli degil")
        print("kurulum icin docs/INSTAGRAM_SETUP.md dosyasini oku")
        return None

    # adim 1: medya container olustur
    create_url = f"{GRAPH_API_BASE}/{INSTAGRAM_ACCOUNT_ID}/media"
    create_params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": META_ACCESS_TOKEN,
    }

    print(f"medya container olusturuluyor...")
    resp = requests.post(create_url, data=create_params)

    if resp.status_code != 200:
        print(f"hata: medya olusturulamadi - {resp.status_code}")
        print(resp.json())
        return None

    container_id = resp.json().get("id")
    print(f"container olusturuldu: {container_id}")

    # adim 2: yayinla
    publish_url = f"{GRAPH_API_BASE}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    publish_params = {
        "creation_id": container_id,
        "access_token": META_ACCESS_TOKEN,
    }

    print(f"paylasim yapiliyor...")
    pub_resp = requests.post(publish_url, data=publish_params)

    if pub_resp.status_code != 200:
        print(f"hata: paylasim yapilamadi - {pub_resp.status_code}")
        print(pub_resp.json())
        return None

    media_id = pub_resp.json().get("id")
    print(f"basarili! media id: {media_id}")
    return media_id


def upload_image_to_host(local_path):
    """
    goruntuyu imgbb ye yukle ve url dondur
    imgbb ucretsiz api: https://api.imgbb.com/1/upload
    alternatif: github raw url kullanilabilir
    """
    imgbb_key = IMGBB_API_KEY or os.getenv("IMGBB_API_KEY", "")

    if imgbb_key:
        import base64
        with open(local_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()

        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": imgbb_key, "image": img_data}
        )
        if resp.status_code == 200:
            url = resp.json()["data"]["url"]
            print(f"gorsel yuklendi: {url}")
            return url

    # imgbb yoksa github raw url dene
    if IMAGE_HOST_BASE:
        filename = os.path.basename(local_path)
        return f"{IMAGE_HOST_BASE}/{filename}"

    print("uyari: gorsel hosting yapilandirilmamis")
    print("imgbb api key veya IMAGE_HOST_BASE ortam degiskeni gerekli")
    return None


def main():
    parser = argparse.ArgumentParser(description="finzora ai instagram otomatik paylasim")
    parser.add_argument("--type", choices=["piyasa", "performans", "egitim", "telegram"],
                        help="post turu (otomatik gorsel + caption)")
    parser.add_argument("--image", help="gorsel dosya yolu")
    parser.add_argument("--caption", help="paylasim metni")
    parser.add_argument("--dry-run", action="store_true", help="api cagrisi yapmadan test et")

    args = parser.parse_args()

    # gorsel ve caption belirle
    if args.type:
        # otomatik gorsel uret
        from instagram_post_generator import (
            generate_piyasa_post, generate_performans_post,
            generate_egitim_post, generate_telegram_post
        )

        generators = {
            "piyasa": generate_piyasa_post,
            "performans": generate_performans_post,
            "egitim": generate_egitim_post,
            "telegram": generate_telegram_post,
        }

        img = generators[args.type]()
        output_dir = REPO_ROOT / "outputs" / "instagram"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        img_path = output_dir / f"{args.type}_{timestamp}.png"
        img.save(str(img_path), "PNG", quality=95)
        print(f"gorsel uretildi: {img_path}")

        caption = args.caption or CAPTION_MAP[args.type]()
    elif args.image:
        img_path = args.image
        caption = args.caption or "finzora ai\n\n#finzora #yatirim #borsa"
    else:
        print("hata: --type veya --image belirtilmeli")
        sys.exit(1)

    print(f"\n--- PAYLASIM ONIZLEME ---")
    print(f"gorsel: {img_path}")
    print(f"caption:\n{caption}")
    print(f"-------------------------\n")

    if args.dry_run:
        print("dry-run modu: api cagrisi yapilmadi")
        return

    # goruntuyu internete yukle
    image_url = upload_image_to_host(str(img_path))
    if not image_url:
        print("hata: gorsel yuklenemedi, paylasim iptal")
        sys.exit(1)

    # instagram a paylas
    result = upload_to_instagram(image_url, caption)
    if result:
        print(f"\npaylasim basarili! instagram a git ve kontrol et.")
    else:
        print(f"\npaylasim basarisiz.")


if __name__ == "__main__":
    main()
