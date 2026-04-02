#!/usr/bin/env python3
"""
finzora ai - instagram api kurulum ve test scripti
bu scripti bilgisayarinda calistir, gerisini otomatik yapar

kullanim:
  python scripts/instagram_setup.py

adimlar:
  1. graph api explorer dan yeni token al (script sana url verecek)
  2. token'i yapistir
  3. script otomatik olarak:
     - tokeni uzun sureliye cevirir
     - facebook sayfani bulur
     - instagram business account id'ni ceker
     - config dosyasini olusturur
     - test paylasimi yapar (opsiyonel)
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent

# meta app bilgileri
APP_ID = "1521966196161302"
APP_SECRET = "3625b06d1fb69979fd882989a960a574"
GRAPH_API_VERSION = "v25.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# instagram app bilgileri (yedek)
IG_APP_ID = "1505058181223109"
IG_APP_SECRET = "1dd3ec249bcfed1b86458a0d3c1f35c0"

# threads bilgileri (ileride kullanilacak)
THREADS_APP_ID = "922552067315328"
THREADS_APP_SECRET = "76edf3ed4c0b406fbce333cb0b36c9f0"

CONFIG_PATH = REPO_ROOT / "config" / "instagram_config.json"


def print_header(text):
    print(f"\n{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}\n")


def print_step(num, text):
    print(f"\n--- adim {num}: {text} ---\n")


def exchange_token(short_token):
    """kisa sureli tokeni uzun sureliye cevir (60 gun)"""
    url = f"{GRAPH_API_BASE}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 200:
        data = r.json()
        return data.get("access_token"), data.get("expires_in")
    else:
        print(f"hata: token uzatma basarisiz - {r.status_code}")
        print(r.text)
        return None, None


def get_page_token(user_token):
    """kullanici tokenindan sayfa tokenini al"""
    url = f"{GRAPH_API_BASE}/me/accounts"
    params = {
        "fields": "id,name,access_token,instagram_business_account",
        "access_token": user_token,
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 200:
        data = r.json()
        pages = data.get("data", [])
        return pages
    else:
        print(f"hata: sayfa listesi alinamadi - {r.status_code}")
        print(r.text)
        return []


def get_ig_account_from_page(page_id, page_token):
    """sayfa tokenini kullanarak instagram business account id al"""
    url = f"{GRAPH_API_BASE}/{page_id}"
    params = {
        "fields": "instagram_business_account",
        "access_token": page_token,
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 200:
        data = r.json()
        ig_account = data.get("instagram_business_account", {})
        return ig_account.get("id")
    return None


def get_ig_account_info(ig_account_id, token):
    """instagram hesap bilgilerini al"""
    url = f"{GRAPH_API_BASE}/{ig_account_id}"
    params = {
        "fields": "id,name,username,profile_picture_url,followers_count,media_count",
        "access_token": token,
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 200:
        return r.json()
    return None


def test_post(ig_account_id, token):
    """test paylasimi yap (opsiyonel)"""
    # basit bir test goruntusu - finzora logolu placeholder
    test_image_url = "https://placehold.co/1080x1080/1a1a2e/e94560?text=FINZORA+AI%0ATest+Post&font=montserrat"
    test_caption = """🔧 finzora ai instagram entegrasyonu basariyla kuruldu

bu bir test paylasimidir, kisa surede silinecektir.

#finzora #test"""

    # adim 1: medya container olustur
    create_url = f"{GRAPH_API_BASE}/{ig_account_id}/media"
    create_params = {
        "image_url": test_image_url,
        "caption": test_caption,
        "access_token": token,
    }

    print("medya container olusturuluyor...")
    resp = requests.post(create_url, data=create_params, timeout=30)
    if resp.status_code != 200:
        print(f"hata: {resp.status_code}")
        print(resp.json())
        return False

    container_id = resp.json().get("id")
    print(f"container id: {container_id}")

    # adim 2: yayinla
    publish_url = f"{GRAPH_API_BASE}/{ig_account_id}/media_publish"
    publish_params = {
        "creation_id": container_id,
        "access_token": token,
    }

    print("yayinlaniyor...")
    pub_resp = requests.post(publish_url, data=publish_params, timeout=30)
    if pub_resp.status_code != 200:
        print(f"hata: {pub_resp.status_code}")
        print(pub_resp.json())
        return False

    media_id = pub_resp.json().get("id")
    print(f"basarili! media id: {media_id}")
    return True


def save_config(config):
    """config dosyasini kaydet"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"config kaydedildi: {CONFIG_PATH}")


def load_config():
    """mevcut config dosyasini yukle"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    print_header("finzora ai - instagram api kurulum")

    # mevcut config var mi kontrol et
    config = load_config()
    if config.get("instagram_account_id") and config.get("access_token"):
        print(f"mevcut config bulundu:")
        print(f"  instagram id: {config['instagram_account_id']}")
        print(f"  kullanici: @{config.get('username', '?')}")
        print(f"  token son kullanim: {config.get('token_expires', '?')}")
        choice = input("\nyeni token almak ister misin? (e/h): ").strip().lower()
        if choice != "e":
            print("mevcut config ile devam ediliyor.")
            return

    # adim 1: token al
    print_step(1, "access token al")
    print("graph api explorer dan yeni token olustur:")
    print(f"  1. su adrese git: https://developers.facebook.com/tools/explorer/")
    print(f"  2. meta app: claude")
    print(f"  3. user or page: User Token")
    print(f"  4. permissions ekle:")
    print(f"     - pages_show_list")
    print(f"     - pages_read_engagement")
    print(f"     - instagram_basic (veya instagram_business_basic)")
    print(f"     - instagram_content_publish (veya instagram_business_content_publish)")
    print(f"  5. generate access token tikla")
    print(f"  6. tokeni kopyala ve asagiya yapistir")

    short_token = input("\ntoken: ").strip()
    if not short_token:
        print("token girilmedi, cikiliyor.")
        sys.exit(1)

    # adim 2: tokeni uzat
    print_step(2, "token uzun sureliye cevriliyor")
    long_token, expires_in = exchange_token(short_token)
    if not long_token:
        print("token uzatma basarisiz. kisa sureli tokenla devam ediliyor.")
        long_token = short_token
        expires_in = 3600
    else:
        days = expires_in // 86400
        print(f"uzun sureli token alindi ({days} gun gecerli)")

    # adim 3: sayfa ve instagram hesabini bul
    print_step(3, "facebook sayfasi ve instagram hesabi araniyor")
    pages = get_page_token(long_token)

    if not pages:
        print("hic facebook sayfasi bulunamadi!")
        print("instagram hesabinin bir facebook sayfasina bagli oldugundan emin ol.")
        sys.exit(1)

    print(f"{len(pages)} sayfa bulundu:\n")

    ig_account_id = None
    page_token = None
    selected_page = None

    for i, page in enumerate(pages):
        ig = page.get("instagram_business_account", {})
        ig_id = ig.get("id", "bagli degil")
        print(f"  {i+1}. {page['name']} (sayfa id: {page['id']}, instagram: {ig_id})")

        if ig.get("id"):
            ig_account_id = ig["id"]
            page_token = page.get("access_token", long_token)
            selected_page = page

    if not ig_account_id:
        # sayfa tokeniyle tekrar dene
        print("\ninstagram baglantisi user token ile gorunmuyor, sayfa tokenleriyle deneniyor...")
        for page in pages:
            pt = page.get("access_token")
            if pt:
                ig_id = get_ig_account_from_page(page["id"], pt)
                if ig_id:
                    ig_account_id = ig_id
                    page_token = pt
                    selected_page = page
                    print(f"  bulundu! sayfa: {page['name']}, instagram id: {ig_id}")
                    break

    if not ig_account_id:
        print("\nhicbir sayfada instagram business account bulunamadi!")
        print("kontrol et:")
        print("  1. instagram hesabin profesyonel (business) mi?")
        print("  2. instagram, finzora facebook sayfasina bagli mi?")
        print("  3. token olusturulurken tum izinleri verdin mi?")
        print("\nmanuel id girisi:")
        manual_id = input("instagram business account id (bos birakirsan cikis): ").strip()
        if manual_id:
            ig_account_id = manual_id
            page_token = long_token
        else:
            sys.exit(1)

    # adim 4: instagram hesap bilgilerini al
    print_step(4, "instagram hesap bilgileri aliniyor")
    ig_info = get_ig_account_info(ig_account_id, page_token or long_token)
    if ig_info:
        print(f"  id: {ig_info.get('id')}")
        print(f"  kullanici: @{ig_info.get('username', '?')}")
        print(f"  takipci: {ig_info.get('followers_count', '?')}")
        print(f"  paylasim: {ig_info.get('media_count', '?')}")
    else:
        print("  hesap bilgileri alinamadi (token izinleri yetersiz olabilir)")

    # adim 5: config kaydet
    print_step(5, "config kaydediliyor")

    from datetime import timedelta
    expires_date = (datetime.now() + timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M")

    config = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
        "instagram_account_id": ig_account_id,
        "facebook_page_id": selected_page["id"] if selected_page else "",
        "facebook_page_name": selected_page["name"] if selected_page else "",
        "access_token": page_token or long_token,
        "user_access_token": long_token,
        "token_expires": expires_date,
        "username": ig_info.get("username", "zeynelgun01") if ig_info else "zeynelgun01",
        "ig_app_id": IG_APP_ID,
        "ig_app_secret": IG_APP_SECRET,
        "threads_app_id": THREADS_APP_ID,
        "threads_app_secret": THREADS_APP_SECRET,
        "graph_api_version": GRAPH_API_VERSION,
        "setup_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "imgbb_api_key": "",
        "notes": "token her 60 gunde yenilenmeli. imgbb_api_key gorsel hosting icin gerekli."
    }

    save_config(config)

    # adim 6: test paylasimi
    print_step(6, "test paylasimi (opsiyonel)")
    do_test = input("test paylasimi yapmak ister misin? (e/h): ").strip().lower()
    if do_test == "e":
        success = test_post(ig_account_id, page_token or long_token)
        if success:
            print("\ntest paylasimi basarili! instagram hesabini kontrol et.")
        else:
            print("\ntest paylasimi basarisiz. token izinlerini kontrol et.")
    else:
        print("test atlandi.")

    # ozet
    print_header("kurulum tamamlandi!")
    print(f"instagram account id : {ig_account_id}")
    print(f"facebook sayfasi     : {selected_page['name'] if selected_page else '?'}")
    print(f"token gecerlilik     : {expires_date}")
    print(f"config dosyasi       : {CONFIG_PATH}")
    print(f"\nkullanim:")
    print(f"  python scripts/instagram_publisher.py --type piyasa --dry-run")
    print(f"  python scripts/instagram_publisher.py --type performans")
    print(f"\nnot: token {expires_date} tarihinde sona erecek.")
    print(f"yenilemek icin bu scripti tekrar calistir.")


if __name__ == "__main__":
    main()
