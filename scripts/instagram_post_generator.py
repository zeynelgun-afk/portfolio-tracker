#!/usr/bin/env python3
"""
finzora ai - instagram post gorsel uretici
kullanim:
  python scripts/instagram_post_generator.py --type piyasa
  python scripts/instagram_post_generator.py --type performans
  python scripts/instagram_post_generator.py --type egitim --konu "stop-loss nedir"
  python scripts/instagram_post_generator.py --type telegram

gorsel ciktisi: outputs/instagram/ klasorune kaydedilir
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("pillow yuklu degil: pip install Pillow")
    sys.exit(1)

# --- RENK PALETI ---
COLORS = {
    "bg": (10, 10, 15),
    "card": (18, 18, 26),
    "surface": (22, 22, 31),
    "accent": (0, 212, 170),       # yesil
    "accent_dim": (0, 212, 170, 40),
    "red": (255, 71, 87),
    "gold": (255, 215, 0),
    "blue": (74, 158, 255),
    "telegram": (0, 136, 204),
    "text": (232, 232, 240),
    "muted": (107, 107, 128),
    "border": (30, 30, 46),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}

# instagram kare post boyutu
POST_SIZE = (1080, 1080)
STORY_SIZE = (1080, 1920)

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = REPO_ROOT / "outputs" / "instagram"
DATA_DIR = REPO_ROOT / "data"


def get_font(size, bold=False):
    """sistem fontlari arasinda uygun olanini bul"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def load_summary():
    """summary.json oku"""
    with open(DATA_DIR / "summary.json", "r", encoding="utf-8") as f:
        return json.load(f)


def draw_header(draw, y, tag_text, tag_color):
    """finzora ai logo + etiket ciz"""
    # logo daire
    draw.ellipse([40, y, 80, y + 40], fill=COLORS["accent"])
    font_logo = get_font(18, bold=True)
    draw.text((52, y + 8), "F", fill=COLORS["black"], font=font_logo)

    # marka ismi
    font_brand = get_font(14)
    draw.text((92, y + 12), "FINZORA AI", fill=COLORS["muted"], font=font_brand)

    # etiket
    font_tag = get_font(12)
    tag_w = draw.textlength(tag_text, font=font_tag) + 16
    draw.rounded_rectangle([POST_SIZE[0] - 40 - tag_w, y + 6, POST_SIZE[0] - 40, y + 30], radius=4, fill=(*tag_color, 35))
    draw.text((POST_SIZE[0] - 40 - tag_w + 8, y + 10), tag_text, fill=tag_color, font=font_tag)

    return y + 60


def draw_footer(draw, y):
    """alt bilgi ciz"""
    draw.line([(40, y), (POST_SIZE[0] - 40, y)], fill=COLORS["border"], width=1)
    font = get_font(13)
    draw.text((40, y + 12), "@zeynelgun01", fill=COLORS["muted"], font=font)
    draw.text((POST_SIZE[0] - 40 - draw.textlength("telegram: @finzora", font=font), y + 12),
              "telegram: @finzora", fill=COLORS["accent"], font=font)


def draw_rounded_rect(draw, coords, radius, fill):
    """yuvarlak koseli dikdortgen"""
    x1, y1, x2, y2 = coords
    draw.rounded_rectangle(coords, radius=radius, fill=fill)


# ==========================================
# POST TURLERI
# ==========================================

def generate_piyasa_post(market_data=None):
    """gunluk piyasa ozeti postu"""
    img = Image.new("RGB", POST_SIZE, COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # gradient efekti (ust kisim)
    for i in range(200):
        alpha = int(15 * (1 - i / 200))
        draw.line([(0, i), (POST_SIZE[0], i)], fill=(10, 20, 35))

    y = 30
    y = draw_header(draw, y, "PIYASA OZETI", COLORS["blue"])

    # tarih
    font_date = get_font(14)
    today = datetime.now().strftime("%d %B %Y").lower()
    gunler = {"monday": "pazartesi", "tuesday": "sali", "wednesday": "carsamba",
              "thursday": "persembe", "friday": "cuma", "saturday": "cumartesi", "sunday": "pazar"}
    gun = gunler.get(datetime.now().strftime("%A").lower(), "")
    draw.text((40, y), f"{today} · {gun}", fill=COLORS["muted"], font=font_date)
    y += 25

    # baslik
    font_title = get_font(36, bold=True)
    draw.text((40, y), "gunluk piyasa ozeti", fill=COLORS["text"], font=font_title)
    y += 50

    # ayirici cizgi
    draw.rectangle([40, y, 80, y + 3], fill=COLORS["blue"])
    y += 25

    # varsayilan piyasa verileri (gercek veri parametre olarak gelir)
    if not market_data:
        market_data = [
            {"name": "S&P 500", "val": "5,712", "chg": "+0.84%", "up": True},
            {"name": "NASDAQ", "val": "17,899", "chg": "-0.32%", "up": False},
            {"name": "VIX", "val": "26.4", "chg": "+8.2%", "up": False},
            {"name": "USD/TRY", "val": "38.42", "chg": "+0.15%", "up": False},
            {"name": "ALTIN", "val": "$3,085", "chg": "+1.2%", "up": True},
            {"name": "PETROL", "val": "$71.8", "chg": "-0.9%", "up": False},
        ]

    font_name = get_font(16, bold=True)
    font_val = get_font(18, bold=True)
    font_chg = get_font(14, bold=True)

    for item in market_data:
        color = COLORS["accent"] if item["up"] else COLORS["red"]
        bg_color = (0, 212, 170, 12) if item["up"] else (255, 71, 87, 12)

        # satir arka plan
        draw_rounded_rect(draw, [40, y, POST_SIZE[0] - 40, y + 65], radius=10, fill=COLORS["surface"])
        # sol kenar
        draw.rectangle([40, y + 8, 44, y + 57], fill=color)

        draw.text((60, y + 20), item["name"], fill=COLORS["text"], font=font_name)
        val_text = item["val"]
        chg_text = item["chg"]
        draw.text((POST_SIZE[0] - 60 - draw.textlength(val_text, font=font_val), y + 12), val_text, fill=COLORS["text"], font=font_val)
        draw.text((POST_SIZE[0] - 60 - draw.textlength(chg_text, font=font_chg), y + 38), chg_text, fill=color, font=font_chg)

        y += 75

    # onemli gelisme kutusu
    y += 10
    draw_rounded_rect(draw, [40, y, POST_SIZE[0] - 40, y + 100], radius=10, fill=(74, 158, 255, 15))
    draw.rounded_rectangle([40, y, POST_SIZE[0] - 40, y + 100], radius=10, outline=(74, 158, 255, 50))

    font_label = get_font(12, bold=True)
    font_insight = get_font(14)
    draw.text((60, y + 12), "ONEMLI GELISME", fill=COLORS["blue"], font=font_label)
    # insight text - sabit ornek, gercekte parametre olarak gelir
    draw.text((60, y + 35), "vix 25 ustunde, dikkatli pozisyonlanma", fill=COLORS["text"], font=font_insight)
    draw.text((60, y + 58), "donemi devam ediyor.", fill=COLORS["text"], font=font_insight)
    y += 120

    draw_footer(draw, y)

    return img


def generate_performans_post():
    """portfoy performans postu - summary.json dan veri ceker"""
    summary = load_summary()

    img = Image.new("RGB", POST_SIZE, COLORS["bg"])
    draw = ImageDraw.Draw(img)

    y = 30
    y = draw_header(draw, y, "HAFTALIK PERFORMANS", COLORS["gold"])

    # baslik
    font_title = get_font(34, bold=True)
    draw.text((40, y), "portfoy performansi", fill=COLORS["text"], font=font_title)
    y += 45

    font_sub = get_font(13)
    draw.text((40, y), summary.get("simulasyon_donemi", ""), fill=COLORS["muted"], font=font_sub)
    y += 25

    draw.rectangle([40, y, 80, y + 3], fill=COLORS["gold"])
    y += 30

    # toplam performans kutusu
    draw_rounded_rect(draw, [40, y, POST_SIZE[0] - 40, y + 170], radius=14, fill=(0, 212, 170, 10))
    draw.rounded_rectangle([40, y, POST_SIZE[0] - 40, y + 170], radius=14, outline=(0, 212, 170, 40))

    font_label_sm = get_font(14)
    font_big = get_font(48, bold=True)
    font_medium = get_font(20, bold=True)
    font_small_accent = get_font(14)

    center_x = POST_SIZE[0] // 2
    draw.text((center_x - draw.textlength("TOPLAM PORTFOY", font=font_label_sm) // 2, y + 15),
              "TOPLAM PORTFOY", fill=COLORS["accent"], font=font_label_sm)

    total_val = f"${summary['toplam_deger']:,.0f}"
    draw.text((center_x - draw.textlength(total_val, font=font_big) // 2, y + 40),
              total_val, fill=COLORS["accent"], font=font_big)

    spy_text = f"spy: {summary['benchmark_spy']:+.1f}% | biz: {summary['toplam_kar_zarar_yuzde']:+.1f}%"
    draw.text((center_x - draw.textlength(spy_text, font=font_medium) // 2, y + 100),
              spy_text, fill=COLORS["text"], font=font_medium)

    alpha_text = f"alfa: {summary['alpha']:+.1f} puan"
    draw.text((center_x - draw.textlength(alpha_text, font=font_small_accent) // 2, y + 135),
              alpha_text, fill=COLORS["accent"], font=font_small_accent)

    y += 195

    # portfoy satirlari
    port_colors = {
        "dengeli": COLORS["blue"],
        "agresif": COLORS["accent"],
        "temettü": COLORS["gold"],
    }

    font_port_name = get_font(16)
    font_port_val = get_font(18, bold=True)

    for key in ["dengeli", "agresif", "temettü"]:
        if key not in summary["portfolyolar"]:
            continue
        p = summary["portfolyolar"][key]
        color = port_colors.get(key, COLORS["text"])

        draw_rounded_rect(draw, [40, y, POST_SIZE[0] - 40, y + 55], radius=8, fill=COLORS["surface"])
        # sol kenar renk
        draw.rectangle([40, y + 10, 46, y + 45], fill=color)

        draw.text((60, y + 16), p["isim"].lower(), fill=COLORS["text"], font=font_port_name)

        ret_text = f"{p['kar_zarar_yuzde']:+.1f}%"
        ret_color = COLORS["accent"] if p["kar_zarar_yuzde"] >= 0 else COLORS["red"]
        draw.text((POST_SIZE[0] - 60 - draw.textlength(ret_text, font=font_port_val), y + 14),
                  ret_text, fill=ret_color, font=font_port_val)

        y += 65

    # swing trade bilgisi
    y += 10
    swing = summary["portfolyolar"].get("swing_trade", {})
    font_swing = get_font(13)
    draw.text((40, y), f"swing trade: {swing.get('durum', 'bilgi yok')}", fill=COLORS["muted"], font=font_swing)
    y += 30

    # islem gunleri
    draw.text((40, y), f"islem gunleri: {summary.get('islem_gunleri', 0)} gun", fill=COLORS["muted"], font=font_swing)
    y += 50

    draw_footer(draw, y)

    return img


def generate_egitim_post(konu="amerikan borsasina nasil yatirim yapilir"):
    """egitim serisi postu"""
    img = Image.new("RGB", POST_SIZE, COLORS["bg"])
    draw = ImageDraw.Draw(img)

    y = 30
    y = draw_header(draw, y, "EGITIM SERISI", COLORS["gold"])

    # ust etiket
    font_tag = get_font(13, bold=True)
    draw.text((40, y), "YENI BASLAYANLAR ICIN", fill=COLORS["gold"], font=font_tag)
    y += 30

    # baslik
    font_title = get_font(32, bold=True)
    # baslik satirlara bol (max 20 karakter per satir)
    words = konu.split()
    lines = []
    current = ""
    for w in words:
        if len(current + " " + w) > 22:
            lines.append(current.strip())
            current = w
        else:
            current += " " + w
    if current.strip():
        lines.append(current.strip())

    for line in lines[:3]:
        draw.text((40, y), line, fill=COLORS["text"], font=font_title)
        y += 42
    y += 5

    draw.rectangle([40, y, 80, y + 3], fill=COLORS["accent"])
    y += 30

    # egitim konulari (varsayilan)
    topics = [
        {"n": "01", "t": "hesap ac", "d": "interactive brokers veya midas ile amerikan borsasina erisim"},
        {"n": "02", "t": "arastirma yap", "d": "sirketi tanimadan yatirim yapma, temel analiz ogren"},
        {"n": "03", "t": "kucuk basla", "d": "ilk yatirimda buyuk risk alma, portfoyunu yavas buyut"},
        {"n": "04", "t": "disiplinli ol", "d": "stop-loss kullan, duygusal karar verme"},
    ]

    font_num = get_font(15, bold=True)
    font_topic = get_font(18, bold=True)
    font_desc = get_font(13)

    for i, t in enumerate(topics):
        # numara kutusu
        box_color = COLORS["accent"] if i == 0 else COLORS["surface"]
        text_color = COLORS["black"] if i == 0 else COLORS["accent"]
        draw_rounded_rect(draw, [40, y, 80, y + 40], radius=8, fill=box_color)
        draw.text((52, y + 10), t["n"], fill=text_color, font=font_num)

        # baslik ve aciklama
        draw.text((95, y + 2), t["t"], fill=COLORS["text"], font=font_topic)
        draw.text((95, y + 26), t["d"], fill=COLORS["muted"], font=font_desc)

        y += 60

    y += 30
    draw_footer(draw, y)

    return img


def generate_telegram_post():
    """telegram kanal tanitim postu"""
    img = Image.new("RGB", POST_SIZE, COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # arka plan glow efekti
    for r in range(200, 0, -1):
        alpha_val = int(8 * (r / 200))
        cx, cy = POST_SIZE[0] // 2, 320
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 136, 204, alpha_val))

    y = 30
    y = draw_header(draw, y, "TELEGRAM", COLORS["telegram"])

    # telegram ikonu (daire)
    center_x = POST_SIZE[0] // 2
    icon_y = 180
    draw.ellipse([center_x - 50, icon_y, center_x + 50, icon_y + 100], fill=COLORS["telegram"])
    font_icon = get_font(44, bold=True)
    draw.text((center_x - 15, icon_y + 22), "T", fill=COLORS["white"], font=font_icon)

    y = icon_y + 130

    # baslik
    font_title = get_font(34, bold=True)
    title1 = "ucretsiz piyasa"
    title2 = "analizi kanali"
    draw.text((center_x - draw.textlength(title1, font=font_title) // 2, y), title1, fill=COLORS["text"], font=font_title)
    y += 42
    draw.text((center_x - draw.textlength(title2, font=font_title) // 2, y), title2, fill=COLORS["text"], font=font_title)
    y += 50

    draw.rectangle([center_x - 25, y, center_x + 25, y + 3], fill=COLORS["telegram"])
    y += 25

    font_desc = get_font(16)
    desc1 = "her gun amerikan borsasi analizi,"
    desc2 = "portfoy guncellemeleri ve yatirim fikirleri"
    draw.text((center_x - draw.textlength(desc1, font=font_desc) // 2, y), desc1, fill=COLORS["muted"], font=font_desc)
    y += 22
    draw.text((center_x - draw.textlength(desc2, font=font_desc) // 2, y), desc2, fill=COLORS["muted"], font=font_desc)
    y += 50

    # ozellikler
    features = [
        ("gunluk piyasa analizi ve ozet", "📊"),
        ("gercek portfoy performansi", "🎯"),
        ("yatirim egitim icerikleri", "📚"),
        ("anlik piyasa uyarilari", "⚡"),
    ]

    font_feat = get_font(16)
    for text, emoji in features:
        draw.text((center_x - 150, y), f"{emoji}  {text}", fill=COLORS["text"], font=font_feat)
        y += 35

    y += 20

    # cta kutusu
    draw_rounded_rect(draw, [80, y, POST_SIZE[0] - 80, y + 80], radius=14, fill=(0, 136, 204, 20))
    draw.rounded_rectangle([80, y, POST_SIZE[0] - 80, y + 80], radius=14, outline=(0, 136, 204, 60))

    font_cta = get_font(24, bold=True)
    font_cta_sub = get_font(13)
    cta = "@finzora"
    draw.text((center_x - draw.textlength(cta, font=font_cta) // 2, y + 15), cta, fill=COLORS["telegram"], font=font_cta)
    cta_sub = "telegram da ara veya bio daki linkten katil"
    draw.text((center_x - draw.textlength(cta_sub, font=font_cta_sub) // 2, y + 50), cta_sub, fill=COLORS["muted"], font=font_cta_sub)

    y += 110
    draw_footer(draw, y)

    return img


def main():
    parser = argparse.ArgumentParser(description="finzora ai instagram post uretici")
    parser.add_argument("--type", required=True, choices=["piyasa", "performans", "egitim", "telegram"],
                        help="post turu: piyasa, performans, egitim, telegram")
    parser.add_argument("--konu", default="amerikan borsasina nasil yatirim yapilir",
                        help="egitim postu konusu")
    parser.add_argument("--output", default=None, help="cikti dosya yolu (varsayilan: outputs/instagram/)")

    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")

    if args.type == "piyasa":
        img = generate_piyasa_post()
        filename = f"piyasa_{timestamp}.png"
    elif args.type == "performans":
        img = generate_performans_post()
        filename = f"performans_{timestamp}.png"
    elif args.type == "egitim":
        img = generate_egitim_post(args.konu)
        filename = f"egitim_{timestamp}.png"
    elif args.type == "telegram":
        img = generate_telegram_post()
        filename = f"telegram_{timestamp}.png"

    output_path = args.output or str(OUTPUT_DIR / filename)
    img.save(output_path, "PNG", quality=95)
    print(f"gorsel olusturuldu: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
