#!/usr/bin/env python3
"""
Finzora AI - Günlük Risk Paneli Üretici

8 varlık için teknik skor hesaplar, 1080x1920 PNG üretir.
Skor: SMA50, SMA200, RSI>50, 5-gün momentum (her biri +1, toplam 0-4)
Etiket: 3-4=RISK ON, 2=RISK TEST, 0-1=RISK OFF

Kullanım:
  python scripts/risk_panel_generator.py                # bugünün paneli
  python scripts/risk_panel_generator.py --date YYYY-MM-DD  # geçmiş tarih (henüz desteklenmiyor)

Çıktı: outputs/risk_panel/YYYY-MM-DD.png
"""

import urllib.request
import json
import os
import sys
import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FMP_KEY = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"

# 8 varlık — BIST ve doğalgaz çıkarıldı (kullanıcı kararı)
ASSETS = [
    ("SPY", "SPY", "S&P 500"),
    ("QQQ", "QQQ", "Nasdaq 100"),
    ("DIA", "DIA", "Dow Jones"),
    ("IWM", "IWM", "Russell 2000"),
    ("GLD", "ALTIN", "Gold"),
    ("BTCUSD", "BTC", "Bitcoin"),
    ("BNO", "BRENT", "Brent Petrol"),
    ("CPER", "BAKIR", "Bakır"),
]

# Finzora teması
BG_TOP = (15, 23, 42)        # #0f172a
BG_BOTTOM = (30, 41, 59)     # #1e293b
CARD_BG = (22, 32, 54)       # slight lighter for cards
CARD_BORDER = (51, 65, 85)   # #334155
TEXT_MAIN = (241, 245, 249)  # #f1f5f9
TEXT_MUTED = (148, 163, 184) # #94a3b8
TEAL = (20, 184, 166)        # #14b8a6
GREEN = (16, 185, 129)       # #10b981
AMBER = (245, 158, 11)       # #f59e0b
RED = (239, 68, 68)          # #ef4444

FONT_DIR = "/usr/share/fonts/truetype/google-fonts"
FONT_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
FONT_MEDIUM = os.path.join(FONT_DIR, "Poppins-Medium.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "Poppins-Regular.ttf")


def fmp(path: str):
    sep = "&" if "?" in path else "?"
    url = f"{FMP_BASE}/{path}{sep}apikey={FMP_KEY}"
    return json.loads(urllib.request.urlopen(url, timeout=30).read())


def calc_scores():
    """8 varlık için SMA21/SMA50 bazlı 3 seviyeli risk durumu hesapla."""
    symbols = [a[0] for a in ASSETS]
    quotes = {q["symbol"]: q for q in fmp(f"batch-quote?symbols={','.join(symbols)}")}

    # Son kapanış tarihi — SPY historical'dan al
    close_date = None
    try:
        spy_hist = fmp("historical-price-eod/full?symbol=SPY")
        if spy_hist:
            close_date = spy_hist[0]["date"]
    except Exception:
        pass

    results = []
    for sym, display, fullname in ASSETS:
        q = quotes.get(sym)
        if not q:
            print(f"WARN: {sym} veri yok")
            continue

        price = q.get("price", 0)
        sma50 = q.get("priceAvg50", 0)
        prev = q.get("previousClose", 0)
        day_chg = ((price - prev) / prev * 100) if prev else 0

        # SMA21 — historical'dan hesapla (FMP batch-quote'ta yok)
        sma21 = 0
        try:
            hist = fmp(f"historical-price-eod/full?symbol={sym}")[:21]
            if len(hist) >= 21:
                sma21 = sum(h["close"] for h in hist) / 21
        except Exception:
            pass

        # 3 seviyeli risk durumu (Yorum B: ikisi birden üstte = ON)
        p_gt_21 = bool(sma21 and price > sma21)
        p_gt_50 = bool(sma50 and price > sma50)

        if p_gt_21 and p_gt_50:
            label = "RISK ON"
            tier = 2
        elif p_gt_21 or p_gt_50:
            label = "RISK TEST"
            tier = 1
        else:
            label = "RISK OFF"
            tier = 0

        results.append({
            "symbol": sym,
            "display": display,
            "fullname": fullname,
            "price": price,
            "day_chg": day_chg,
            "sma21": sma21,
            "sma50": sma50,
            "label": label,
            "tier": tier,
            "p_gt_21": p_gt_21,
            "p_gt_50": p_gt_50,
        })
    return results, close_date


def gradient_bg(w, h):
    img = Image.new("RGB", (w, h), BG_TOP)
    px = img.load()
    for y in range(h):
        t = y / h
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_panel(results, out_path, date_str):
    W, H = 1080, 1920
    img = gradient_bg(W, H)
    d = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(FONT_BOLD, 64)
    f_subtitle = ImageFont.truetype(FONT_MEDIUM, 32)
    f_brand = ImageFont.truetype(FONT_BOLD, 28)
    f_card_label = ImageFont.truetype(FONT_BOLD, 44)
    f_card_name = ImageFont.truetype(FONT_MEDIUM, 30)
    f_card_meta = ImageFont.truetype(FONT_REGULAR, 24)
    f_status = ImageFont.truetype(FONT_BOLD, 28)
    f_footer = ImageFont.truetype(FONT_REGULAR, 22)
    f_footer_bold = ImageFont.truetype(FONT_BOLD, 24)

    # Header
    d.text((W // 2, 90), "GÜNLÜK RİSK PANELİ", font=f_title, fill=TEXT_MAIN, anchor="mm")
    d.text((W // 2, 155), date_str, font=f_subtitle, fill=TEXT_MUTED, anchor="mm")

    # Teal accent line
    d.rectangle([(W // 2 - 60, 195), (W // 2 + 60, 199)], fill=TEAL)

    # 8 cards in 2 columns, 4 rows
    card_w, card_h = 480, 290
    gap_x, gap_y = 40, 30
    start_x = (W - (card_w * 2 + gap_x)) // 2
    start_y = 250

    for i, r in enumerate(results):
        col = i % 2
        row = i // 2
        x1 = start_x + col * (card_w + gap_x)
        y1 = start_y + row * (card_h + gap_y)
        x2 = x1 + card_w
        y2 = y1 + card_h

        # label color
        if r["label"] == "RISK ON":
            lc = GREEN
        elif r["label"] == "RISK TEST":
            lc = AMBER
        else:
            lc = RED

        # Card background
        rounded_rect(d, (x1, y1, x2, y2), 24, fill=CARD_BG, outline=CARD_BORDER, width=2)

        # Left color bar
        rounded_rect(d, (x1, y1, x1 + 8, y2), 4, fill=lc)

        # Asset display name (big)
        d.text((x1 + 32, y1 + 30), r["display"], font=f_card_label, fill=TEXT_MAIN)
        d.text((x1 + 32, y1 + 85), r["fullname"], font=f_card_name, fill=TEXT_MUTED)

        # Daily change
        chg = r["day_chg"]
        chg_color = GREEN if chg >= 0 else RED
        chg_txt = f"{chg:+.2f}%"
        d.text((x2 - 32, y1 + 35), chg_txt, font=f_card_name, fill=chg_color, anchor="ra")

        # Price line
        d.text((x2 - 32, y1 + 78), f"${r['price']:,.2f}", font=f_card_meta, fill=TEXT_MUTED, anchor="ra")

        # SMA satırları (2 satır)
        metrics_y = y1 + 140
        row_h = 38

        def sma_row(yy, label, sma_val, price_val, ok):
            # Daire işareti
            rr = 9
            cy = yy + 16
            cx = x1 + 40
            if ok:
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=GREEN)
            else:
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=RED, width=3)
            # Label + değer
            d.text((x1 + 60, yy), label, font=f_card_meta, fill=TEXT_MAIN)
            d.text((x2 - 32, yy), f"${sma_val:,.2f}", font=f_card_meta, fill=TEXT_MUTED, anchor="ra")

        sma_row(metrics_y, "Fiyat > SMA21", r["sma21"], r["price"], r["p_gt_21"])
        sma_row(metrics_y + row_h, "Fiyat > SMA50", r["sma50"], r["price"], r["p_gt_50"])

        # Status badge (bottom right)
        badge_w = 170
        badge_h = 42
        bx1 = x2 - badge_w - 24
        by1 = y2 - badge_h - 24
        bx2 = x2 - 24
        by2 = y2 - 24
        rounded_rect(d, (bx1, by1, bx2, by2), 21, fill=lc)
        d.text(((bx1 + bx2) // 2, (by1 + by2) // 2), r["label"], font=f_status, fill=(15, 23, 42), anchor="mm")

    # Footer
    footer_y = 1740
    d.text((W // 2, footer_y), "finzora ai", font=f_brand, fill=TEAL, anchor="mm")
    d.text(
        (W // 2, footer_y + 45),
        "SMA21 + SMA50 ikisi de üstü = RISK ON | tek biri = RISK TEST | ikisi altı = RISK OFF",
        font=f_footer,
        fill=TEXT_MUTED,
        anchor="mm",
    )
    d.text(
        (W // 2, footer_y + 80),
        "portföy aksiyonları K kurallarına bağlıdır, bu panel sadece teknik durum gösterir",
        font=f_footer,
        fill=TEXT_MUTED,
        anchor="mm",
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None, help="output PNG path")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")

    print(f"FMP veri çekiliyor ({len(ASSETS)} varlık)...")
    results, close_date = calc_scores()
    print(f"Skorlar hesaplandı: {len(results)} varlık, kapanış tarihi: {close_date}")

    # Turkish date — kapanış tarihine göre
    tr_months = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran",
                 "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"]
    tr_days = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]
    if close_date:
        dt = datetime.strptime(close_date, "%Y-%m-%d")
    else:
        dt = datetime.now()
    date_str = f"{dt.day} {tr_months[dt.month-1]} {dt.year} {tr_days[dt.weekday()]} kapanışı"

    # Dosya adını kapanış tarihine göre yaz
    if not args.out:
        args.out = os.path.join(REPO_ROOT, "outputs", "risk_panel", f"{close_date or today}.png")

    print(f"PNG üretiliyor: {args.out}")
    draw_panel(results, args.out, date_str)
    print(f"Tamam: {args.out}")

    # Summary
    print("\n=== ÖZET ===")
    for r in results:
        print(f"  {r['display']:6s}  px ${r['price']:>10,.2f}  SMA21 ${r['sma21']:>10,.2f}  SMA50 ${r['sma50']:>10,.2f}  → {r['label']:10s}  ({r['day_chg']:+.2f}%)")


if __name__ == "__main__":
    main()
