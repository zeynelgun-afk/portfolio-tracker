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
  python scripts/telegram_notify.py --type winners               # kârdaki pozisyonlar vitrini
  python scripts/telegram_notify.py --type photo --image panel.png --caption "başlık"  # görsel gönder
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
    """Seans içi kısa özet. pozisyon detayı yok, sadece toplam + aksiyonlar + dikkat."""
    all_pos, bal, agg, div = get_all_positions()
    swing = load_swing()

    toplam = bal["toplam_deger"] + agg["toplam_deger"] + div["toplam_deger"]
    toplam_pnl = toplam - 600000
    toplam_pct = (toplam_pnl / 600000) * 100
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    msg = f"""<b>📊 FİNZORA SEANS RAPORU</b>
<i>{now}</i>

<b>💰 ${toplam:,.0f} ({toplam_pct:+.2f}%)</b>
  Dengeli {bal['toplam_getiri_yuzde']:+.1f}% | Agresif {agg['toplam_getiri_yuzde']:+.1f}% | Temettü {div['toplam_getiri_yuzde']:+.1f}%
"""
    if theme:
        msg += f"\n📌 {theme}\n"

    # günün en iyi/en kötü 3'er pozisyonu
    movers = sorted(all_pos, key=lambda x: x["gunluk_degisim_yuzde"], reverse=True)
    best3 = [p for p in movers[:3] if p["gunluk_degisim_yuzde"] > 0]
    worst3 = [p for p in movers[-3:] if p["gunluk_degisim_yuzde"] < 0]

    if best3 or worst3:
        msg += "\n<b>📈 Günün Öne Çıkanları</b>\n"
        for p in best3:
            msg += f"  🟢 {p['sembol']} {p['gunluk_degisim_yuzde']:+.1f}% (toplam {p['kar_zarar_yuzde']:+.1f}%)\n"
        for p in reversed(worst3):
            msg += f"  🔴 {p['sembol']} {p['gunluk_degisim_yuzde']:+.1f}% (toplam {p['kar_zarar_yuzde']:+.1f}%)\n"

    # günün işlemleri (summary.json)
    try:
        summary = load_json("data/summary.json")
        son_islemler = summary.get("son_islemler", [])
        trade_islemler = [i for i in son_islemler if any(
            t in i for t in ["SATIŞ", "ALIŞ", "SWING", "TRAILING", "STOP"]
        )]
        if trade_islemler:
            msg += "\n<b>📝 Aksiyonlar</b>\n"
            for islem in trade_islemler[:5]:
                msg += f"  • {islem}\n"
    except:
        pass

    # stop yakını uyarıları
    alerts = []
    for p in all_pos:
        sl = p.get("stop_loss")
        if sl and p["guncel_fiyat"] > 0:
            dist_pct = ((p["guncel_fiyat"] - sl) / p["guncel_fiyat"]) * 100
            if dist_pct < 3:
                alerts.append((p["sembol"], p["port"], p["guncel_fiyat"], sl, dist_pct))

    aktif = swing.get("aktif_pozisyonlar", [])
    for p in aktif:
        sl = p.get("stop_loss", 0)
        if sl and p["guncel_fiyat"] > 0:
            dist_pct = ((p["guncel_fiyat"] - sl) / p["guncel_fiyat"]) * 100
            if dist_pct < 3:
                alerts.append((p["sembol"], "SWG", p["guncel_fiyat"], sl, dist_pct))

    if alerts:
        msg += "\n<b>🚨 Stop Yakını</b>\n"
        for sym, port, price, sl, dist in sorted(alerts, key=lambda x: x[4]):
            msg += f"  {sym} ({port}) ${price:.2f} → SL ${sl:.2f} (%{dist:.1f})\n"

    # swing özet (tek satır)
    if aktif:
        sw_summary = ", ".join(f"{p['sembol']} {p['guncel_kar_zarar_yuzde']:+.1f}%" for p in aktif)
        msg += f"\n⚡ Swing ({len(aktif)}/8): {sw_summary}\n"

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
        sl = p.get("stop_loss")
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
        wl = load_json("data/watchlist.json")
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


def format_winners(theme=None):
    """Kârdaki pozisyonların vitrin gösterimi. reklam/showcase amaçlı."""
    all_pos, bal, agg, div = get_all_positions()
    swing = load_swing()

    toplam = bal["toplam_deger"] + agg["toplam_deger"] + div["toplam_deger"]
    toplam_pnl = toplam - 600000
    toplam_pct = (toplam_pnl / 600000) * 100
    today = datetime.now().strftime("%d.%m.%Y")

    # aktif kârdaki pozisyonlar (tüm portföyler)
    winners = [p for p in all_pos if p["kar_zarar_yuzde"] > 0]
    winners.sort(key=lambda x: x["kar_zarar_yuzde"], reverse=True)

    # swing aktif kârdakiler
    swing_aktif = swing.get("aktif_pozisyonlar", [])
    swing_winners = [p for p in swing_aktif if p["guncel_kar_zarar_yuzde"] > 0]
    swing_winners.sort(key=lambda x: x["guncel_kar_zarar_yuzde"], reverse=True)

    # kapanmış swing kazançları
    try:
        closed = load_json("data/swing/closed.json")
        closed_wins = [p for p in closed.get("kapatilan_pozisyonlar", []) if p["kar_zarar_yuzde"] > 0]
        closed_wins.sort(key=lambda x: x["kar_zarar_yuzde"], reverse=True)
        total_closed = len(closed.get("kapatilan_pozisyonlar", []))
        win_rate = (len(closed_wins) / total_closed * 100) if total_closed > 0 else 0
    except:
        closed_wins = []
        win_rate = 0
        total_closed = 0

    # portföy isim haritası
    port_names = {"DNG": "Dengeli", "AGR": "Agresif", "TMT": "Temettü"}

    # tutma süresi hesapla
    def hold_days(giris):
        try:
            d = datetime.strptime(giris, "%Y-%m-%d")
            return (datetime.now() - d).days
        except:
            return 0

    # toplam realize + unrealized
    unrealized_pnl = sum(p.get("kar_zarar", 0) for p in all_pos if p.get("kar_zarar", 0) > 0)

    msg = f"""<b>🏆 KAZANANLAR VİTRİNİ</b>
<i>{today}</i>
"""
    if theme:
        msg += f"\n<b>📌</b> {theme}\n"

    msg += f"""
<b>💰 Toplam Portföy: ${toplam:,.0f} ({toplam_pct:+.2f}%)</b>
"""

    # en iyi aktif pozisyonlar
    if winners:
        msg += f"\n<b>📈 Aktif Kazananlar ({len(winners)} pozisyon)</b>\n"
        for i, p in enumerate(winners):
            # medal emojisi ilk 3 için
            if i == 0:
                medal = "🥇"
            elif i == 1:
                medal = "🥈"
            elif i == 2:
                medal = "🥉"
            else:
                medal = "🟢"

            days = hold_days(p.get("giris_tarihi", ""))
            port_label = port_names.get(p["port"], p["port"])
            pnl_usd = p.get("kar_zarar", 0)
            msg += f"  {medal} <b>{p['sembol']}</b> <b>+%{p['kar_zarar_yuzde']:.1f}</b>"
            if pnl_usd > 0:
                msg += f" (+${pnl_usd:,.0f})"
            msg += f" | {days} gün | {port_label}\n"

    # swing aktif kazananlar
    if swing_winners:
        msg += f"\n<b>⚡ Swing Aktif Kazananlar</b>\n"
        for p in swing_winners:
            msg += f"  🟢 <b>{p['sembol']}</b> <b>+%{p['guncel_kar_zarar_yuzde']:.1f}</b> | {p['tutulan_gun']} gün\n"

    # kapanmış swing istatistikleri
    if closed_wins:
        avg_win = sum(p["kar_zarar_yuzde"] for p in closed_wins) / len(closed_wins)
        best = closed_wins[0]
        msg += f"\n<b>📊 Swing Geçmiş Performans</b>\n"
        msg += f"  Kazanç oranı: <b>%{win_rate:.0f}</b> ({len(closed_wins)}/{total_closed})\n"
        msg += f"  Ort. kazanç: <b>+%{avg_win:.1f}</b>\n"
        msg += f"  En iyi: <b>{best['sembol']} +%{best['kar_zarar_yuzde']:.1f}</b> ({best['tutulan_gun']} gün)\n"

        # son 5 kapanmış kazanç
        msg += "\n  Son kapanmış kazançlar:\n"
        recent = sorted(closed_wins, key=lambda x: x.get("cikis_tarihi", ""), reverse=True)[:5]
        for p in recent:
            msg += f"    ✅ {p['sembol']} +%{p['kar_zarar_yuzde']:.1f} | {p['tutulan_gun']} gün\n"

    # portföy bazında özet
    msg += f"\n{'─' * 25}\n"
    msg += "<b>📋 Portföy Bazında Getiri</b>\n"
    for label, port in [("Dengeli", bal), ("Agresif", agg), ("Temettü", div)]:
        pct = port["toplam_getiri_yuzde"]
        emoji = "📈" if pct >= 0 else "📉"
        msg += f"  {emoji} {label}: <b>{pct:+.2f}%</b>\n"

    msg += f"\n<i>17 şubat 2026'dan beri takip ediliyor</i>"
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
    parser.add_argument("--type", choices=["session", "action", "alert", "daily", "premarket", "closing", "report", "custom", "winners", "photo"], required=True)
    parser.add_argument("--msg", help="Özel mesaj (--type custom için)")
    parser.add_argument("--file", help="Markdown rapor dosyası (--type report için)")
    parser.add_argument("--image", help="Görsel dosyası (--type photo için)")
    parser.add_argument("--caption", help="Görsel altı açıklama (--type photo için)")
    parser.add_argument("--theme", help="Piyasa teması / günün özeti (session, premarket, closing için)")
    parser.add_argument("--symbol", help="Sembol (action/alert için)")
    parser.add_argument("--price", type=float, help="Fiyat")
    parser.add_argument("--action", help="Aksiyon tipi: ALIŞ, SATIŞ, STOP, KAR_AL, UYARI")
    parser.add_argument("--details", help="Detay açıklama")
    parser.add_argument("--stop", type=float, help="Stop fiyatı (alert için)")
    parser.add_argument("--private", "--dm", action="store_true", dest="private",
                        help="Gruba değil sadece Zeynel'e DM gönder (sistem bakım, bugfix, teknik rapor)")

    args = parser.parse_args()

    # Hedef kanal kuralları (memory #9):
    #   GRUP:  alım/satım aksiyonu, açılış/kapanış raporu, günlük özet
    #   DM:    sistem mesajları, hata/bakım, kural güncelleme, denetim özeti
    #
    # custom + alert gibi belirsiz tiplerde --dm açık belirtilmediyse grup'a değil
    # DM'e düşsün (yanlış yere gidip grubu kirletme riskini kesiyoruz).
    _DM_DEFAULT_TYPES = {"alert", "custom"}   # Açık --dm olmadıkça da DM'e
    _GROUP_SAFE_TYPES = {"action", "premarket", "closing", "daily", "report", "photo",
                         "session", "winners"}

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

    if args.type == "session":
        msg = format_session_report(theme=args.theme)
    elif args.type == "premarket":
        msg = format_premarket(theme=args.theme)
    elif args.type == "winners":
        msg = format_winners(theme=args.theme)
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
