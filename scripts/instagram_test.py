#!/usr/bin/env python3
"""
finzora ai - instagram baglanti testi
config dosyasindaki bilgilerle instagram api baglantisindan kontrol eder
"""

import json
import requests
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "instagram_config.json"

def main():
    # config oku
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    token = config["access_token"]
    ig_id = config["instagram_account_id"]
    page_id = config["facebook_page_id"]
    api_version = config.get("graph_api_version", "v25.0")
    base = f"https://graph.facebook.com/{api_version}"

    print("=" * 50)
    print("  finzora ai - instagram baglanti testi")
    print("=" * 50)

    # 1. token gecerlilik kontrolu
    print("\n1. token kontrolu...")
    r = requests.get(f"{base}/debug_token",
                    params={"input_token": token, "access_token": token}, timeout=30)
    if r.status_code == 200:
        data = r.json().get("data", {})
        is_valid = data.get("is_valid", False)
        expires = data.get("expires_at", 0)
        print(f"   gecerli: {is_valid}")
        if expires:
            from datetime import datetime
            exp_date = datetime.fromtimestamp(expires).strftime("%Y-%m-%d %H:%M")
            print(f"   son kullanim: {exp_date}")
        scopes = data.get("scopes", [])
        print(f"   izinler: {', '.join(scopes[:5])}...")
    else:
        print(f"   hata: {r.status_code} - {r.text[:200]}")

    # 2. page token al
    print("\n2. sayfa tokeni aliniyor...")
    r = requests.get(f"{base}/me/accounts",
                    params={"access_token": token}, timeout=30)
    page_token = None
    if r.status_code == 200:
        for page in r.json().get("data", []):
            if page["id"] == page_id:
                page_token = page.get("access_token")
                print(f"   sayfa: {page['name']} ({page['id']})")
                print(f"   page token: {'alindi' if page_token else 'yok'}")
    else:
        print(f"   hata: {r.status_code}")

    # 3. instagram hesap bilgileri
    print("\n3. instagram hesap bilgileri...")
    use_token = page_token or token
    r = requests.get(f"{base}/{ig_id}",
                    params={
                        "fields": "id,username,name,profile_picture_url,followers_count,media_count",
                        "access_token": use_token
                    }, timeout=30)
    if r.status_code == 200:
        ig = r.json()
        print(f"   id: {ig.get('id')}")
        print(f"   kullanici: @{ig.get('username', '?')}")
        print(f"   takipci: {ig.get('followers_count', '?')}")
        print(f"   paylasim: {ig.get('media_count', '?')}")
        print(f"\n   BASARILI! instagram api baglantisi calisiyor.")
    else:
        err = r.json().get("error", {})
        print(f"   hata: {err.get('message', r.text[:200])}")
        print(f"\n   BASARISIZ. yukaridaki hatayi kontrol et.")

    # 4. content publish testi (gorsel olmadan sadece izin kontrolu)
    print("\n4. paylasim izni kontrolu...")
    r = requests.get(f"{base}/debug_token",
                    params={"input_token": use_token, "access_token": use_token}, timeout=30)
    if r.status_code == 200:
        scopes = r.json().get("data", {}).get("scopes", [])
        has_publish = "instagram_content_publish" in scopes
        has_basic = "instagram_basic" in scopes or "instagram_business_basic" in scopes
        print(f"   instagram_basic: {'var' if has_basic else 'YOK'}")
        print(f"   instagram_content_publish: {'var' if has_publish else 'YOK'}")
        if has_publish:
            print(f"\n   PAYLASIM IZNI AKTIF! gorsel paylasimi yapilabilir.")
        else:
            print(f"\n   UYARI: paylasim izni yok. developers.facebook.com dan aktif et.")

    print("\n" + "=" * 50)
    print("  test tamamlandi")
    print("=" * 50)


if __name__ == "__main__":
    main()
