#!/usr/bin/env python3
"""Generic Instagram carousel publisher — folder + caption + comment ile çalışır"""
import requests, json, time, sys, os, argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "config", "instagram_config.json")) as f:
    config = json.load(f)

IG_ID = config["instagram_account_id"]
TOKEN = config["access_token"]
API = f"https://graph.facebook.com/{config['graph_api_version']}"

LINK_COMMENT = "📱 telegram grubuna katıl: https://t.me/+nWm5M7VnxEEzNGQ0\n🌐 site: https://finzora.ai"

# ===== CAPTIONS =====
CAPTIONS = {
    "weekly": """📊 bu hafta ABD borsasında ne oldu?

31 Mart — 4 Nisan haftasının özeti 👇

endeksler:
→ S&P 500: +%3.43
→ NASDAQ: +%3.98 (haftanın lideri)
→ Dow Jones: +%3.03
→ Russell 2000: +%3.37

haftanın ana teması: CPU arz krizi
→ Intel +%16.8 (haftanın yıldızı — Fab 34 geri alımı)
→ AMD +%7.7 (sunucu CPU fiyatlama gücü)
→ ARM +%3.5 (kendi AI CPU lansmanı)

sektör lideri: teknoloji +%2.50

⚠️ gelecek hafta dikkat:
→ 6 Nisan İran müzakere deadline ı
→ büyük banka kazanç açıklamaları başlıyor
→ VIX hâlâ 25 üzeri = yüksek volatilite

detaylı analiz ve $600K gerçek portföy takibi 👇
🔗 t.me/+nWm5M7VnxEEzNGQ0
🌐 finzora.ai

⚠️ yatırım tavsiyesi değildir, eğitim amaçlıdır.


#finzora #yatirim #borsa #amerikanborsasi #sp500 #nasdaq #haftalikozet #borsaanalizi #cpu #semiconductor #intel #amd #wallstreet #piyasa #hisseSenedi""",

    "100dollar": """💰 $100 ile yatırıma nasıl başlanır?

büyük paraya gerek yok. önemli olan başlamak.

4 adım:
1️⃣ yatırım hesabı aç — düşük komisyonlu platform seç
2️⃣ ETF ile başla — SPY veya VTI ile risk dağıt
3️⃣ otomatik yatırım kur — her ay $100, DCA stratejisi
4️⃣ sabırla büyüt — 10 yıl düşün, panik satma

bileşik getiri mucizesi:
$100/ay × %10 getiri × 20 yıl = $75,937 💰

yaygın yanılgılar:
❌ yatırım için çok param yok → $100 ile başla
❌ borsayı anlamam lazım → ETF al, piyasa çalışsın
❌ başlamak için geç → en iyi zaman bugün
❌ borsa kumar → tarihsel ortalama %10/yıl getiri

bu postu kaydet 🔖 yatırıma başlamak isteyen arkadaşına gönder 📩

detaylı rehber ve portföy takibi 👇
🔗 t.me/+nWm5M7VnxEEzNGQ0
🌐 finzora.ai

⚠️ yatırım tavsiyesi değildir, eğitim amaçlıdır.


#finzora #yatirim #borsa #yeniyatirimci #borsaegitimi #etf #sp500 #yatirimegitimleri #finansokuryazarligi #pasifgelir #bilesikGetiri #amerikanborsasi #ilkyatirim #100dolar #portfoy"""
}

FIRST_COMMENTS = {
    "weekly": "gelecek hafta hangi sektör öne çıkar? 👇",
    "100dollar": "yatırıma başlamak isteyip de başlayamayan arkadaşını etiketle 👇"
}

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

def publish(post_type, folder):
    img_dir = os.path.join(BASE_DIR, "outputs", "instagram", folder)
    caption = CAPTIONS[post_type]
    first_comment = FIRST_COMMENTS[post_type]
    
    slides = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')])
    print(f"{'='*55}")
    print(f"  FINZORA AI — {post_type.upper()} CAROUSEL")
    print(f"  {len(slides)} slide | {folder}")
    print(f"{'='*55}")

    print(f"\n📤 Görseller yükleniyor...\n")
    urls = []
    for s in slides:
        url = upload(os.path.join(img_dir, s))
        if not url: sys.exit(1)
        urls.append(url)
        time.sleep(1)

    print(f"\n📸 Container'lar oluşturuluyor...\n")
    cids = []
    for i, url in enumerate(urls):
        r = ig(f"{IG_ID}/media", {"image_url": url, "is_carousel_item": "true"})
        if "id" in r:
            cids.append(r["id"])
            print(f"  [{i+1}/{len(urls)}] ✓ {r['id']}")
        else:
            print(f"  ✗ {r.get('error',{}).get('message','')}")
            sys.exit(1)
        time.sleep(3)

    print(f"\n  Carousel oluşturuluyor...")
    cr = ig(f"{IG_ID}/media", {"media_type": "CAROUSEL", "children": ",".join(cids), "caption": caption})
    if "id" not in cr:
        print(f"  ✗ {cr.get('error',{}).get('message','')}")
        sys.exit(1)
    
    car_id = cr["id"]
    print(f"  ✓ {car_id}\n  ⏳ işleniyor...")
    if not wait_ready(car_id): sys.exit(1)

    pr = ig(f"{IG_ID}/media_publish", {"creation_id": car_id})
    if "id" not in pr:
        print(f"  ✗ {pr.get('error',{}).get('message','')}")
        sys.exit(1)
    
    post_id = pr["id"]
    print(f"\n  ✅ YAYINLANDI! Post ID: {post_id}")

    # Comments
    time.sleep(3)
    ig(f"{post_id}/comments", {"message": first_comment})
    print(f"  💬 İlk yorum eklendi")
    time.sleep(2)
    ig(f"{post_id}/comments", {"message": LINK_COMMENT})
    print(f"  🔗 Link yorumu eklendi (tıklanabilir)")
    
    print(f"\n{'='*55}\n  ✅ TAMAMLANDI\n{'='*55}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["weekly", "100dollar"])
    args = parser.parse_args()
    
    folders = {"weekly": "weekly", "100dollar": "100dollar"}
    publish(args.type, folders[args.type])
