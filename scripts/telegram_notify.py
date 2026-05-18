#!/usr/bin/env python3
"""
Finzora AI - Telegram Bildirim Sistemi
Aksiyonları, uyarıları ve markdown raporları Telegram'a gönderir.

Kullanım:
  python scripts/telegram_notify.py --type action        # tek aksiyon bildirimi
  python scripts/telegram_notify.py --type alert         # acil uyarı (stop yakın vb.)
  python scripts/telegram_notify.py --type report --file rapor.md  # markdown rapor gönder
  python scripts/telegram_notify.py --type custom --msg "mesaj"    # özel mesaj
  python scripts/telegram_notify.py --type photo --image panel.png --caption "başlık"  # görsel gönder

NOT (17 May 2026): session/premarket/winners/daily/closing tipleri kaldırıldı
(13 May 2026 single portfolio.json simplification sonrası bu fonksiyonlar
data/portfolios/* yok olan dizine bakıyordu, production'da kullanılmıyorlardı).
Eşdeğer raporlar `--type report --file <md>` ile gönderilir.
"""

import requests
import json
import argparse
import os
import sys
import re
from datetime import datetime

# --- CONFIG ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID",    "-1003827034395")  # Finzora grubu
# Zeynel özel DM (chat_id 1403072107, @Zeynelgun) — sistem bakım, denetim, bugfix, teknik rapor buraya.
# Grubu bu mesajlarla kirletme kuralı: memory #9
TELEGRAM_PRIVATE_ID = os.environ.get("TELEGRAM_PRIVATE_ID", "") or \
                      os.environ.get("TELEGRAM_PRIVATE_CHAT", "") or \
                      "1403072107"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- TELEGRAM GÖNDERME ---
def send_photo(image_path, caption=None, parse_mode="HTML", chat_id=None):
    """Telegram'a fotoğraf gönder. Caption max 1024 karakter."""
    target = chat_id or TELEGRAM_CHAT_ID
    if not target:
        print("HATA: TELEGRAM_CHAT_ID ayarlanmamış!")
        sys.exit(1)

    if not os.path.exists(image_path):
        print(f"HATA: görsel bulunamadı: {image_path}")
        sys.exit(1)

    url = f"{TELEGRAM_API}/sendPhoto"
    data = {"chat_id": target}
    if caption:
        # Telegram caption limit 1024 karakter
        data["caption"] = caption[:1024]
        data["parse_mode"] = parse_mode

    try:
        with open(image_path, "rb") as f:
            files = {"photo": f}
            r = requests.post(url, data=data, files=files, timeout=60)
            resp = r.json()
            if resp.get("ok"):
                print(f"Görsel gönderildi: {os.path.basename(image_path)}")
                return True
            else:
                desc = resp.get("description", "bilinmeyen hata")
                print(f"Telegram sendPhoto hatası: {desc}")
                # parse_mode hatalıysa plain text ile tekrar dene
                if "can't parse" in desc.lower() and caption:
                    data.pop("parse_mode", None)
                    with open(image_path, "rb") as f2:
                        files = {"photo": f2}
                        r = requests.post(url, data=data, files=files, timeout=60)
                        if r.json().get("ok"):
                            print(f"Görsel gönderildi (düz metin caption)")
                            return True
                return False
    except Exception as e:
        print(f"sendPhoto exception: {e}")
        return False


def send_message(text, parse_mode="HTML", disable_preview=True, chat_id=None):
    """Telegram'a mesaj gönder. Uzun mesajları otomatik böler.

    Returns:
        bool: Tüm chunk'lar başarılı gittiyse True, herhangi biri başarısızsa False.
        4 May 2026: 'Not Found' / token bozuk durumunda yanıltıcı 'gönderildi'
        log'unu önlemek için return değeri eklendi (önceden None döndürüyordu).
    """
    target = chat_id or TELEGRAM_CHAT_ID
    if not target:
        print("HATA: TELEGRAM_CHAT_ID ayarlanmamış!")
        sys.exit(1)

    chunks = split_message(text, 4000)
    all_ok = True

    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": target,
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
                        all_ok = False
                else:
                    all_ok = False
            else:
                print(f"Mesaj gönderildi ({len(chunk)} karakter) [{i+1}/{len(chunks)}]")
        except Exception as e:
            print(f"Gönderim hatası: {e}")
            all_ok = False

    return all_ok


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


# --- MESAJ FORMATLARI ---

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
    parser.add_argument("--type",
                        choices=["action", "alert", "report", "custom", "photo"],
                        required=True)
    parser.add_argument("--msg", help="Özel mesaj (--type custom için)")
    parser.add_argument("--file", help="Markdown rapor dosyası (--type report için)")
    parser.add_argument("--image", help="Görsel dosyası (--type photo için)")
    parser.add_argument("--caption", help="Görsel altı açıklama (--type photo için)")
    parser.add_argument("--symbol", help="Sembol (action/alert için)")
    parser.add_argument("--price", type=float, help="Fiyat")
    parser.add_argument("--action", help="Aksiyon tipi: ALIŞ, SATIŞ, STOP, KAR_AL, UYARI")
    parser.add_argument("--details", help="Detay açıklama")
    parser.add_argument("--stop", type=float, help="Stop fiyatı (alert için)")
    parser.add_argument("--private", "--dm", action="store_true", dest="private",
                        help="Gruba değil sadece Zeynel'e DM gönder (sistem bakım, bugfix, teknik rapor)")

    args = parser.parse_args()

    # Hedef kanal kuralları:
    #   GRUP:  alım/satım aksiyonu (--type action), markdown rapor (--type report), foto
    #   DM:    sistem mesajları, alert, custom
    #
    # custom + alert gibi belirsiz tiplerde --dm açık belirtilmediyse grup'a değil
    # DM'e düşsün (yanlış yere gidip grubu kirletme riskini kesiyoruz).
    _DM_DEFAULT_TYPES = {"alert", "custom"}   # Açık --dm olmadıkça da DM'e

    if args.private:
        target_chat = TELEGRAM_PRIVATE_ID
    elif args.type in _DM_DEFAULT_TYPES:
        target_chat = TELEGRAM_PRIVATE_ID
        print(f"[telegram_notify] {args.type} default olarak DM'e yönlendirildi "
              f"(--private açıkça belirtilmedi ama sistem mesajı kabul edildi)")
    else:
        target_chat = TELEGRAM_CHAT_ID

    # DM hedefi boşsa gruba düşmek yerine HATA ver (yanlış kanala göndermek yok)
    if args.private and not TELEGRAM_PRIVATE_ID:
        print("HATA: --private belirtildi ama TELEGRAM_PRIVATE_ID ayarlı değil.")
        sys.exit(1)

    if args.type == "report":
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
    elif args.type == "photo":
        if not args.image:
            print("photo için --image gerekli")
            sys.exit(1)
        success = send_photo(args.image, caption=args.caption, chat_id=target_chat)
        sys.exit(0 if success else 1)
    else:
        print("Geçersiz tip")
        sys.exit(1)

    send_message(msg, chat_id=target_chat)


if __name__ == "__main__":
    main()
