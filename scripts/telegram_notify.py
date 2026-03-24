#!/usr/bin/env python3
"""
Finzora AI - Telegram Bildirim Sistemi
Seans raporlarını ve aksiyonları Telegram kanalına gönderir.

Kullanım:
  python scripts/telegram_notify.py --type session     # seans özeti
  python scripts/telegram_notify.py --type action      # tek aksiyon bildirimi
  python scripts/telegram_notify.py --type alert       # acil uyarı (stop yakın vb.)
  python scripts/telegram_notify.py --type daily        # günlük kapanış raporu
  python scripts/telegram_notify.py --type custom --msg "mesaj"  # özel mesaj
"""

import requests
import json
import argparse
import os
import sys
from datetime import datetime

# --- CONFIG ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003827034395")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- TELEGRAM GÖNDERME ---
def send_message(text, parse_mode="HTML", disable_preview=True):
    """Telegram'a mesaj gönder. Uzun mesajları otomatik böler."""
    if not TELEGRAM_CHAT_ID:
        print("HATA: TELEGRAM_CHAT_ID ayarlanmamış!")
        sys.exit(1)

    # telegram max 4096 karakter, uzunsa böl
    chunks = split_message(text, 4000)

    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }
        try:
            r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=30)
            data = r.json()
            if not data.get("ok"):
                print(f"Telegram hata: {data.get('description', 'bilinmeyen hata')}")
                # HTML parse hatası olursa düz metin dene
                if "can't parse" in data.get("description", "").lower():
                    payload["parse_mode"] = None
                    r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=30)
            else:
                print(f"Mesaj gönderildi ({len(chunk)} karakter)")
        except Exception as e:
            print(f"Gönderim hatası: {e}")
            sys.exit(1)


def split_message(text, max_len=4000):
    """Uzun mesajları satır bazında böl."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks


# --- VERİ OKUMA ---
def load_json(path):
    full = os.path.join(REPO_ROOT, path)
    with open(full, "r") as f:
        return json.load(f)


def load_portfolios():
    bal = load_json("data/portfolios/balanced.json")
    agg = load_json("data/portfolios/aggressive.json")
    div = load_json("data/portfolios/dividend.json")
    return bal, agg, div


def load_swing():
    return load_json("data/swing/active.json")


# --- MESAJ FORMATLARI ---
def format_session_report():
    """Seans içi özet raporu."""
    bal, agg, div = load_portfolios()
    swing = load_swing()

    toplam = bal["toplam_deger"] + agg["toplam_deger"] + div["toplam_deger"]
    toplam_pnl = toplam - 600000
    toplam_pct = (toplam_pnl / 600000) * 100

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    msg = f"""<b>📊 FİNZORA SEANS RAPORU</b>
<i>{now}</i>

<b>💰 TOPLAM: ${toplam:,.0f} ({toplam_pct:+.2f}%)</b>

<b>▸ Dengeli</b> ${bal['toplam_deger']:,.0f} ({bal['toplam_getiri_yuzde']:+.2f}%)
"""
    for p in bal["pozisyonlar"]:
        emoji = "🟢" if p["kar_zarar_yuzde"] >= 0 else "🔴"
        msg += f"  {emoji} {p['sembol']} ${p['guncel_fiyat']:.2f} ({p['gunluk_degisim_yuzde']:+.1f}%) | PnL: {p['kar_zarar_yuzde']:+.1f}%\n"

    msg += f"\n<b>▸ Agresif</b> ${agg['toplam_deger']:,.0f} ({agg['toplam_getiri_yuzde']:+.2f}%)\n"
    for p in agg["pozisyonlar"]:
        emoji = "🟢" if p["kar_zarar_yuzde"] >= 0 else "🔴"
        msg += f"  {emoji} {p['sembol']} ${p['guncel_fiyat']:.2f} ({p['gunluk_degisim_yuzde']:+.1f}%) | PnL: {p['kar_zarar_yuzde']:+.1f}%\n"
    nakit_pct = (agg["nakit"]["miktar"] / agg["toplam_deger"]) * 100
    msg += f"  💵 Nakit: ${agg['nakit']['miktar']:,.0f} ({nakit_pct:.0f}%)\n"

    msg += f"\n<b>▸ Temettü</b> ${div['toplam_deger']:,.0f} ({div['toplam_getiri_yuzde']:+.2f}%)\n"
    for p in div["pozisyonlar"]:
        emoji = "🟢" if p["kar_zarar_yuzde"] >= 0 else "🔴"
        msg += f"  {emoji} {p['sembol']} ${p['guncel_fiyat']:.2f} ({p['gunluk_degisim_yuzde']:+.1f}%) | PnL: {p['kar_zarar_yuzde']:+.1f}%\n"

    # Swing
    aktif = swing.get("aktif_pozisyonlar", [])
    if aktif:
        msg += f"\n<b>▸ Swing ({len(aktif)} aktif)</b>\n"
        for p in aktif:
            emoji = "🟢" if p["guncel_kar_zarar_yuzde"] >= 0 else "🔴"
            msg += f"  {emoji} {p['sembol']} ${p['guncel_fiyat']:.2f} | PnL: {p['guncel_kar_zarar_yuzde']:+.1f}% | SL: ${p['stop_loss']}\n"

    msg += "\n<i>finzora ai</i>"
    return msg


def format_action(action_type, symbol, price, details):
    """Tek aksiyon bildirimi (alış/satış/stop)."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    emoji_map = {
        "ALIŞ": "🟢 ALIŞ",
        "SATIŞ": "🔴 SATIŞ",
        "STOP": "🛑 STOP-LOSS",
        "KAR_AL": "💰 KAR ALMA",
        "UYARI": "⚠️ UYARI",
    }
    header = emoji_map.get(action_type, f"📌 {action_type}")

    msg = f"""<b>{header}</b>
<i>{now}</i>

<b>{symbol}</b> @ ${price:.2f}
{details}

<i>finzora ai</i>"""
    return msg


def format_alert(symbol, price, stop_loss, distance):
    """Stop yakınlık uyarısı."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    pct = (distance / price) * 100

    msg = f"""<b>🚨 STOP UYARISI</b>
<i>{now}</i>

<b>{symbol}</b> ${price:.2f}
Stop: ${stop_loss:.2f}
Mesafe: ${distance:.2f} (%{pct:.1f})

<i>finzora ai</i>"""
    return msg


def format_daily_close():
    """Günlük kapanış raporu."""
    bal, agg, div = load_portfolios()
    swing = load_swing()

    toplam = bal["toplam_deger"] + agg["toplam_deger"] + div["toplam_deger"]
    toplam_pnl = toplam - 600000
    toplam_pct = (toplam_pnl / 600000) * 100

    today = datetime.now().strftime("%d.%m.%Y")

    # en iyi ve en kotu performanslar
    all_positions = []
    for port_name, port in [("DNG", bal), ("AGR", agg), ("TMT", div)]:
        for p in port["pozisyonlar"]:
            all_positions.append({**p, "port": port_name})

    best = sorted(all_positions, key=lambda x: x["gunluk_degisim_yuzde"], reverse=True)[:3]
    worst = sorted(all_positions, key=lambda x: x["gunluk_degisim_yuzde"])[:3]

    msg = f"""<b>📋 GÜNLÜK KAPANIŞ RAPORU</b>
<i>{today}</i>

<b>💰 TOPLAM: ${toplam:,.0f} ({toplam_pct:+.2f}%)</b>
  Dengeli: ${bal['toplam_deger']:,.0f} ({bal['toplam_getiri_yuzde']:+.2f}%)
  Agresif: ${agg['toplam_deger']:,.0f} ({agg['toplam_getiri_yuzde']:+.2f}%)
  Temettü: ${div['toplam_deger']:,.0f} ({div['toplam_getiri_yuzde']:+.2f}%)

<b>📈 En İyi 3</b>
"""
    for p in best:
        msg += f"  🟢 {p['sembol']} ({p['port']}) {p['gunluk_degisim_yuzde']:+.1f}%\n"

    msg += "\n<b>📉 En Kötü 3</b>\n"
    for p in worst:
        msg += f"  🔴 {p['sembol']} ({p['port']}) {p['gunluk_degisim_yuzde']:+.1f}%\n"

    # Son işlemler
    try:
        summary = load_json("data/summary.json")
        son_islemler = summary.get("son_islemler", [])
        if son_islemler:
            msg += "\n<b>📝 Son İşlemler</b>\n"
            for islem in son_islemler[:5]:
                msg += f"  • {islem}\n"
    except:
        pass

    msg += "\n<i>finzora ai</i>"
    return msg


# --- ANA FONKSİYON ---
def main():
    parser = argparse.ArgumentParser(description="Finzora AI Telegram Bildirim")
    parser.add_argument("--type", choices=["session", "action", "alert", "daily", "custom"], required=True)
    parser.add_argument("--msg", help="Özel mesaj (--type custom için)")
    parser.add_argument("--symbol", help="Sembol (action/alert için)")
    parser.add_argument("--price", type=float, help="Fiyat")
    parser.add_argument("--action", help="Aksiyon tipi: ALIŞ, SATIŞ, STOP, KAR_AL, UYARI")
    parser.add_argument("--details", help="Detay açıklama")
    parser.add_argument("--stop", type=float, help="Stop fiyatı (alert için)")

    args = parser.parse_args()

    if args.type == "session":
        msg = format_session_report()
    elif args.type == "daily":
        msg = format_daily_close()
    elif args.type == "action":
        if not all([args.symbol, args.price, args.action]):
            print("action için --symbol, --price, --action gerekli")
            sys.exit(1)
        msg = format_action(args.action, args.symbol, args.price, args.details or "")
    elif args.type == "alert":
        if not all([args.symbol, args.price, args.stop]):
            print("alert için --symbol, --price, --stop gerekli")
            sys.exit(1)
        distance = args.price - args.stop
        msg = format_alert(args.symbol, args.price, args.stop, distance)
    elif args.type == "custom":
        if not args.msg:
            print("custom için --msg gerekli")
            sys.exit(1)
        msg = args.msg
    else:
        print("Geçersiz tip")
        sys.exit(1)

    send_message(msg)


if __name__ == "__main__":
    main()
