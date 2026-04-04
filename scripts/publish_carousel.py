#!/usr/bin/env python3
"""Genel carousel yayınlama — klasör + caption ile çalışır"""
import requests, json, time, sys, os, argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "config", "instagram_config.json")) as f:
    config = json.load(f)

IG_ID = config["instagram_account_id"]
TOKEN = config["access_token"]
API = f"https://graph.facebook.com/{config['graph_api_version']}"

CAPTIONS = {
    "weekly": """📊 bu hafta ABD borsasında ne oldu?

31 mart — 4 nisan 2026 haftasının özeti 👇

🔴 CPU arz krizi patladı
→ Intel %9+ ralli yaptı, Fab 34 geri alımı
→ ARM AGI CPU lansmanıyla %18 sıçradı
→ sunucu CPU fiyatları %10-15 arttı
→ DDR5 256GB modül $5,700'e çıktı

🌍 jeopolitik
→ İran savaşı 5. haftasında, enerji primi yüksek
→ 7 nisan müzakere deadline'ı yaklaşıyor
→ VIX 25+ bölgesinde, volatilite devam

📈 haftanın öne çıkanları: INTC, AMD, ARM, MU, QCOM

gelecek hafta kritik: İran deadline + CPI verisi + Fed konuşmaları

detaylı analiz ve portföy takibi 👇
👆 bio'daki linke tıkla veya telegram'da @finzora ara
🌐 finzora.ai

⚠️ yatırım tavsiyesi değildir, eğitim amaçlıdır.


#finzora #yatirim #borsa #amerikanborsasi #haftalikozet #sp500 #nasdaq #cpu #semiconductor #intel #amd #borsaanalizi #piyasa #wallstreet #hisseSenedi""",

    "100dollar": """💰 $100 ile yatırıma nasıl başlanır?

sıfırdan adım adım rehber 👇

1️⃣ hedefini belirle — neden yatırım yapıyorsun?
2️⃣ acil durum fonu ayır — 3-6 aylık gider
3️⃣ aracı kurum hesabı aç — 10 dakika yeter
4️⃣ ETF ile başla — SPY, QQQ veya VT
5️⃣ düzenli yatır — her ay aynı gün, aynı tutar

$100/ay × 20 yıl × %10 getiri = $76,000+

bileşik getiri dünyanın 8. harikası. zaman senin en büyük silahın.

bu rehberi kaydet 🔖 lazım olacak
yatırıma başlamak isteyen arkadaşına gönder 📩

daha fazlası için 👇
👆 bio'daki linke tıkla veya telegram'da @finzora ara
🌐 finzora.ai

⚠️ yatırım tavsiyesi değildir, eğitim amaçlıdır.


#finzora #yatirim #borsa #yatirimabasla #etf #sp500 #borsaegitimi #finansokuryazarligi #yeniyatirimci #100dolar #bilesikgetiri #portfoy #pasifgelir #yatirimegitimleri #amerikanborsasi""",
}

COMMENTS = {
    "weekly": "gelecek hafta hangi hisseyi takip ediyorsunuz? 👇",
    "100dollar": "yatırıma kaç yaşında başladın veya başlamayı düşünüyorsun? 👇",
}

def upload(fp):
    r = requests.post("https://catbox.moe/user/api.php", files={"fileToUpload": open(fp,"rb")}, data={"reqtype":"fileupload"})
    url = r.text.strip()
    return url if url.startswith("http") else None

def ig(ep, data):
    r = requests.post(f"{API}/{ep}", data={**data, "access_token": TOKEN})
    try: return r.json()
    except: return {}

def wait(cid, t=120):
    for _ in range(t//5):
        s = requests.get(f"{API}/{cid}", params={"fields":"status_code","access_token":TOKEN}).json().get("status_code","")
        if s=="FINISHED": return True
        if s=="ERROR": return False
        time.sleep(5)
    return False

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--folder", required=True)
    p.add_argument("--type", required=True, choices=["weekly","100dollar"])
    a = p.parse_args()
    
    img_dir = os.path.join(BASE_DIR, "outputs", "instagram", a.folder)
    slides = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')])
    caption = CAPTIONS[a.type]
    comment = COMMENTS[a.type]
    
    print(f"{'='*55}\n  FINZORA AI — {a.type} carousel\n  {len(slides)} slide\n{'='*55}")
    
    print(f"\n📤 Yükleniyor...")
    urls = []
    for s in slides:
        print(f"  {s}...", end=" ")
        u = upload(os.path.join(img_dir, s))
        print(f"{'✓' if u else '✗'}")
        if not u: sys.exit(1)
        urls.append(u); time.sleep(1)
    
    print(f"\n📸 Container'lar...")
    cids = []
    for i,u in enumerate(urls):
        r = ig(f"{IG_ID}/media", {"image_url":u, "is_carousel_item":"true"})
        if "id" in r: cids.append(r["id"]); print(f"  [{i+1}] ✓")
        else: print(f"  [{i+1}] ✗ {r}"); sys.exit(1)
        time.sleep(3)
    
    print(f"\n  Carousel...")
    cr = ig(f"{IG_ID}/media", {"media_type":"CAROUSEL","children":",".join(cids),"caption":caption})
    if "id" not in cr: print(f"✗ {cr}"); sys.exit(1)
    print(f"  ✓ {cr['id']}"); print("  ⏳ işleniyor...")
    if not wait(cr["id"]): print("✗ timeout"); sys.exit(1)
    
    pr = ig(f"{IG_ID}/media_publish", {"creation_id":cr["id"]})
    if "id" not in pr: print(f"✗ {pr}"); sys.exit(1)
    print(f"\n✅ YAYINLANDI! {pr['id']}")
    
    time.sleep(3)
    ig(f"{pr['id']}/comments", {"message":comment})
    print(f"💬 İlk yorum eklendi")

if __name__ == "__main__":
    main()
