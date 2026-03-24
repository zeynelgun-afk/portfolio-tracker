#!/usr/bin/env python3
"""
Finzora AI - Telegram Bildirim Sistemi
Seans raporlarını ve aksiyonları Telegram kanalına gönderir.

Kullanım:
  python scripts/telegram_notify.py --type session       # seans içi özet
  python scripts/telegram_notify.py --type action        # tek aksiyon bildirimi
  python scripts/telegram_notify.py --type alert         # acil uyarı (stop yakın vb.)
  python scripts/telegram_notify.py --type daily         # günlük kapanış raporu
  python scripts/telegram_notify.py --type premarket     # seans öncesi rapor
  python scripts/telegram_notify.py --type closing       # detaylı kapanış raporu
  python scripts/telegram_notify.py --type report --file rapor.md  # markdown rapor gönder
  python scripts/telegram_notify.py --type custom --msg "mesaj"    # özel mesaj
"""

import requests
import json
import argparse
import os
import sys
import re
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

    chunks = split_message(text, 4000)

    for i, chunk in enumerate(chunks):
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
                desc = data.get("description", "bilinmeyen hata")
                print(f"Telegram hata: {desc}")
                if "can't parse" in desc.lower():
                    payload["parse_mode"] = None
                    r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=30)
                    data = r.json()
                    if data.get("ok"):
                        print(f"Mesaj gönderildi (düz metin, {len(chunk)} karakter) [{i+1}/{len(chunks)}]")
                    else:
                        print(f"Düz metin de başarısız: {data.get('description')}")
            else:
                print(f"Mesaj gönderildi ({len(chunk)} karakter) [{i+1}/{len(chunks)}]")
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
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks


# --- MARKDOWN → TELEGRAM HTML ---
def md_to_telegram(md_text):
    """Markdown'ı Telegram HTML formatına çevirir."""
    # Önce HTML özel karakterleri escape et
    md_text = md_text.replace("&", "&amp;")
    md_text = md_text.replace("<", "&lt;")
    md_text = md_text.replace(">", "&gt;")

    lines = md_text.split("\n")
    result = []

    for line in lines:
        if line.startswith("#### "):
            line = f"<b>{line[5:].strip()}</b>"
        elif line.startswith("### "):
            line = f"<b>{line[4:].strip()}</b>"
        elif line.startswith("## "):
            line = f"\n<b>{line[3:].strip()}</b>"
        elif line.startswith("# "):
            line = f"\n{'─' * 25}\n<b>{line[2:].strip()}</b>"
        elif line.strip() in ("---", "***", "___"):
            line = "─" * 25
        elif line.strip().startswith("|") and line.strip().endswith("|"):
            if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            line = "  ".join(cells)
        elif line.strip().startswith("- "):
            indent = len(line) - len(line.lstrip())
            prefix = "  " * (indent // 2) + "•"
            line = f"{prefix} {line.strip()[2:]}"

        line = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"\*(.+?)\*", r"<i>\1</i>", line)
        line = re.sub(r"`(.+?)`", r"<code>\1</code>", line)

        result.append(line)

    text = "\n".join(result)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def get_all_positions():
    bal, agg, div = load_portfolios()
    all_pos = []
    for tag, port in [("DNG", bal), ("AGR", agg), ("TMT", div)]:
        for p in port["pozisyonlar"]:
            all_pos.append({**p, "port": tag})
    return all_pos, bal, agg, div


# --- MESAJ FORMATLARI ---

def format_session_report(theme=None):
    """Seans içi özet raporu."""
    all_pos, bal, agg, div = get_all_positions()
    swing = load_swing()

    toplam = bal["toplam_deger"] + agg["toplam_deger"] + div["toplam_deger"]
    toplam_pnl = toplam - 600000
    toplam_pct = (toplam_pnl / 600000) * 100
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    msg = f"""<b>📊 FİNZORA SEANS RAPORU</b>
<i>{now}</i>

<b>💰 TOPLAM: ${toplam:,.0f} ({toplam_pct:+.2f}%)</b>
"""
    if theme:
        msg += f"\n<b>📌 Günün teması:</b> {theme}\n"

    msg += f"""
<b>▸ Dengeli</b> ${bal['toplam_deger']:,.0f} ({bal['toplam_getiri_yuzde']:+.2f}%)
"""
    for p in bal["pozisyonlar"]:
        e = "🟢" if p["kar_zarar_yuzde"] >= 0 else "🔴"
        msg += f"  {e} {p['sembol']} ${p['guncel_fiyat']:.2f} ({p['gunluk_degisim_yuzde']:+.1f}%) | PnL: {p['kar_zarar_yuzde']:+.1f}%\n"

    msg += f"\n<b>▸ Agresif</b> ${agg['toplam_deger']:,.0f} ({agg['toplam_getiri_yuzde']:+.2f}%)\n"
    for p in agg["pozisyonlar"]:
        e = "🟢" if p["kar_zarar_yuzde"] >= 0 else "🔴"
        msg += f"  {e} {p['sembol']} ${p['guncel_fiyat']:.2f} ({p['gunluk_degisim_yuzde']:+.1f}%) | PnL: {p['kar_zarar_yuzde']:+.1f}%\n"
    nakit_pct = (agg["nakit"]["miktar"] / agg["toplam_deger"]) * 100
    msg += f"  💵 Nakit: ${agg['nakit']['miktar']:,.0f} ({nakit_pct:.0f}%)\n"

    msg += f"\n<b>▸ Temettü</b> ${div['toplam_deger']:,.0f} ({div['toplam_getiri_yuzde']:+.2f}%)\n"
    for p in div["pozisyonlar"]:
        e = "🟢" if p["kar_zarar_yuzde"] >= 0 else "🔴"
        msg += f"  {e} {p['sembol']} ${p['guncel_fiyat']:.2f} ({p['gunluk_degisim_yuzde']:+.1f}%) | PnL: {p['kar_zarar_yuzde']:+.1f}%\n"

    aktif = swing.get("aktif_pozisyonlar", [])
    if aktif:
        msg += f"\n<b>▸ Swing ({len(aktif)} aktif)</b>\n"
        for p in aktif:
            e = "🟢" if p["guncel_kar_zarar_yuzde"] >= 0 else "🔴"
            msg += f"  {e} {p['sembol']} ${p['guncel_fiyat']:.2f} | PnL: {p['guncel_kar_zarar_yuzde']:+.1f}% | SL: ${p['stop_loss']}\n"

    msg += "\n<i>finzora ai</i>"
    return msg


def format_action(action_type, symbol, price, details):
    """Tek aksiyon bildirimi."""
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


def format_premarket(theme=None):
    """Seans öncesi rapor."""
    all_pos, bal, agg, div = get_all_positions()
    swing = load_swing()

    toplam = bal["toplam_deger"] + agg["toplam_deger"] + div["toplam_deger"]
    toplam_pct = ((toplam - 600000) / 600000) * 100
    today = datetime.now().strftime("%d.%m.%Y")

    msg = f"""<b>🌅 SEANS ÖNCESİ RAPOR</b>
<i>{today}</i>
"""
    if theme:
        msg += f"\n<b>📌 Piyasa notu:</b> {theme}\n"

    msg += f"""
<b>💼 Portföy Durumu</b>
  Toplam: ${toplam:,.0f} ({toplam_pct:+.2f}%)
  Dengeli: ${bal['toplam_deger']:,.0f} ({bal['toplam_getiri_yuzde']:+.2f}%)
  Agresif: ${agg['toplam_deger']:,.0f} ({agg['toplam_getiri_yuzde']:+.2f}%)
  Temettü: ${div['toplam_deger']:,.0f} ({div['toplam_getiri_yuzde']:+.2f}%)

<b>🎯 Günün İzleme Listesi</b>
"""
    # Stop'a yakın
    alerts = []
    for p in all_pos:
        sl = p.get("stop_loss") or p.get("zarar_kes")
        if sl and p["guncel_fiyat"] > 0:
            dist_pct = ((p["guncel_fiyat"] - sl) / p["guncel_fiyat"]) * 100
            if dist_pct < 3:
                alerts.append((p["sembol"], p["port"], p["guncel_fiyat"], sl, dist_pct))

    swing_aktif = swing.get("aktif_pozisyonlar", [])
    for p in swing_aktif:
        sl = p.get("stop_loss", 0)
        if sl and p["guncel_fiyat"] > 0:
            dist_pct = ((p["guncel_fiyat"] - sl) / p["guncel_fiyat"]) * 100
            if dist_pct < 3:
                alerts.append((p["sembol"], "SWG", p["guncel_fiyat"], sl, dist_pct))

    if alerts:
        msg += "<b>  🚨 Stop Yakını</b>\n"
        for sym, port, price, sl, dist in sorted(alerts, key=lambda x: x[4]):
            msg += f"    {sym} ({port}) ${price:.2f} → SL ${sl:.2f} (%{dist:.1f})\n"
    else:
        msg += "  ✅ Stop'a yakın pozisyon yok\n"

    # K-11 adayları
    k11 = [p for p in all_pos if p["kar_zarar_yuzde"] >= 20]
    if k11:
        msg += "\n<b>  📊 K-11 Takip (%20+ kazanç)</b>\n"
        for p in sorted(k11, key=lambda x: x["kar_zarar_yuzde"], reverse=True):
            msg += f"    {p['sembol']} ({p['port']}) +%{p['kar_zarar_yuzde']:.1f} → RSI kontrol\n"

    # Agresif durum
    agg_nakit_pct = (agg["nakit"]["miktar"] / agg["toplam_deger"]) * 100
    agg_slots = 10 - len(agg["pozisyonlar"])
    msg += f"""
<b>📋 Agresif</b>
  Nakit: ${agg['nakit']['miktar']:,.0f} ({agg_nakit_pct:.0f}%) | Boş slot: {agg_slots}/10
"""

    # Swing
    swing_slots = 8 - len(swing_aktif)
    msg += f"""<b>📋 Swing</b>
  Aktif: {len(swing_aktif)}/8 | Boş slot: {swing_slots}
"""
    for p in swing_aktif:
        e = "🟢" if p["guncel_kar_zarar_yuzde"] >= 0 else "🔴"
        msg += f"  {e} {p['sembol']} {p['guncel_kar_zarar_yuzde']:+.1f}% (gün {p['tutulan_gun']})\n"

    # Watchlist
    try:
        wl = load_json("data/swing/watchlist.json")
        izleme = wl.get("izleme_listesi", [])
        high = [w for w in izleme if w.get("urgency") == "high"]
        if high:
            msg += "\n<b>🔥 Yüksek Öncelik</b>\n"
            for w in high[:5]:
                msg += f"  {w['sembol']} ${w.get('guncel_fiyat', 0):.2f} → giriş: {w.get('hedef_giris', 'N/A')}\n"
    except:
        pass

    msg += "\n<i>finzora ai</i>"
    return msg


def format_closing(theme=None):
    """Detaylı kapanış raporu."""
    all_pos, bal, agg, div = get_all_positions()
    swing = load_swing()

    toplam = bal["toplam_deger"] + agg["toplam_deger"] + div["toplam_deger"]
    toplam_pnl = toplam - 600000
    toplam_pct = (toplam_pnl / 600000) * 100
    today = datetime.now().strftime("%d.%m.%Y")

    best = sorted(all_pos, key=lambda x: x["gunluk_degisim_yuzde"], reverse=True)[:3]
    worst = sorted(all_pos, key=lambda x: x["gunluk_degisim_yuzde"])[:3]

    msg = f"""<b>📋 KAPANIŞ RAPORU</b>
<i>{today}</i>

{'─' * 25}
"""
    if theme:
        msg += f"\n<b>📌 Günün teması:</b> {theme}\n\n"

    msg += f"""<b>💰 TOPLAM: ${toplam:,.0f} ({toplam_pct:+.2f}%)</b>
  Dengeli: ${bal['toplam_deger']:,.0f} ({bal['toplam_getiri_yuzde']:+.2f}%)
  Agresif: ${agg['toplam_deger']:,.0f} ({agg['toplam_getiri_yuzde']:+.2f}%)
  Temettü: ${div['toplam_deger']:,.0f} ({div['toplam_getiri_yuzde']:+.2f}%)

<b>📈 Günün En İyileri</b>
"""
    for p in best:
        msg += f"  🟢 {p['sembol']} ({p['port']}) {p['gunluk_degisim_yuzde']:+.2f}%\n"

    msg += "\n<b>📉 Günün En Kötüleri</b>\n"
    for p in worst:
        msg += f"  🔴 {p['sembol']} ({p['port']}) {p['gunluk_degisim_yuzde']:+.2f}%\n"

    msg += f"\n{'─' * 25}\n"
    msg += "\n<b>▸ Dengeli Portföy</b>\n"
    for p in bal["pozisyonlar"]:
        e = "🟢" if p["gunluk_degisim_yuzde"] >= 0 else "🔴"
        msg += f"  {e} {p['sembol']:5} ${p['guncel_fiyat']:>8.2f} | gün:{p['gunluk_degisim_yuzde']:+5.1f}% | toplam:{p['kar_zarar_yuzde']:+6.1f}% | w:{p['agirlik_yuzde']:.1f}%\n"
    msg += f"  💵 Nakit: ${bal['nakit']['miktar']:,.0f}\n"

    msg += "\n<b>▸ Agresif Portföy</b>\n"
    for p in agg["pozisyonlar"]:
        e = "🟢" if p["gunluk_degisim_yuzde"] >= 0 else "🔴"
        msg += f"  {e} {p['sembol']:5} ${p['guncel_fiyat']:>8.2f} | gün:{p['gunluk_degisim_yuzde']:+5.1f}% | toplam:{p['kar_zarar_yuzde']:+6.1f}% | w:{p['agirlik_yuzde']:.1f}%\n"
    agg_nakit_pct = (agg["nakit"]["miktar"] / agg["toplam_deger"]) * 100
    msg += f"  💵 Nakit: ${agg['nakit']['miktar']:,.0f} ({agg_nakit_pct:.0f}%)\n"

    msg += "\n<b>▸ Temettü Portföy</b>\n"
    for p in div["pozisyonlar"]:
        e = "🟢" if p["gunluk_degisim_yuzde"] >= 0 else "🔴"
        msg += f"  {e} {p['sembol']:5} ${p['guncel_fiyat']:>8.2f} | gün:{p['gunluk_degisim_yuzde']:+5.1f}% | toplam:{p['kar_zarar_yuzde']:+6.1f}% | w:{p['agirlik_yuzde']:.1f}%\n"
    msg += f"  💵 Nakit: ${div['nakit']['miktar']:,.0f}\n"

    aktif = swing.get("aktif_pozisyonlar", [])
    if aktif:
        msg += "\n<b>▸ Swing Trade</b>\n"
        for p in aktif:
            e = "🟢" if p["guncel_kar_zarar_yuzde"] >= 0 else "🔴"
            msg += f"  {e} {p['sembol']} ${p['guncel_fiyat']:.2f} | PnL:{p['guncel_kar_zarar_yuzde']:+.1f}% | SL:${p['stop_loss']} | gün:{p['tutulan_gun']}\n"

    try:
        summary = load_json("data/summary.json")
        son_islemler = summary.get("son_islemler", [])
        if son_islemler:
            msg += f"\n{'─' * 25}\n"
            msg += "\n<b>📝 Günün İşlemleri</b>\n"
            for islem in son_islemler[:5]:
                msg += f"  • {islem}\n"
    except:
        pass

    msg += f"\n{'─' * 25}\n"
    msg += "<i>finzora ai</i>"
    return msg


def format_report_from_file(filepath):
    """Markdown rapor dosyasını oku ve telegram formatına çevir."""
    full_path = filepath
    if not os.path.isabs(filepath):
        full_path = os.path.join(REPO_ROOT, filepath)

    if not os.path.exists(full_path):
        print(f"Dosya bulunamadı: {full_path}")
        sys.exit(1)

    with open(full_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    return md_to_telegram(md_content)


# --- ANA FONKSİYON ---
def main():
    parser = argparse.ArgumentParser(description="Finzora AI Telegram Bildirim")
    parser.add_argument("--type", choices=["session", "action", "alert", "daily", "premarket", "closing", "report", "custom"], required=True)
    parser.add_argument("--msg", help="Özel mesaj (--type custom için)")
    parser.add_argument("--file", help="Markdown rapor dosyası (--type report için)")
    parser.add_argument("--theme", help="Piyasa teması / günün özeti (session, premarket, closing için)")
    parser.add_argument("--symbol", help="Sembol (action/alert için)")
    parser.add_argument("--price", type=float, help="Fiyat")
    parser.add_argument("--action", help="Aksiyon tipi: ALIŞ, SATIŞ, STOP, KAR_AL, UYARI")
    parser.add_argument("--details", help="Detay açıklama")
    parser.add_argument("--stop", type=float, help="Stop fiyatı (alert için)")

    args = parser.parse_args()

    if args.type == "session":
        msg = format_session_report(theme=args.theme)
    elif args.type == "premarket":
        msg = format_premarket(theme=args.theme)
    elif args.type in ("daily", "closing"):
        msg = format_closing(theme=args.theme)
    elif args.type == "report":
        if not args.file:
            print("report için --file gerekli")
            sys.exit(1)
        msg = format_report_from_file(args.file)
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
