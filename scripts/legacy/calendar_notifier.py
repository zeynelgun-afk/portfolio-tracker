#!/usr/bin/env python3
"""
Finzora AI — Google Takvim → Telegram Bildirim Sistemi
=======================================================
Her gün sabah 09:00 TR'de çalışır.
Yarınki tüm etkinlikleri bulur ve Telegram DM'e gönderir.

Kullanım:
  python scripts/calendar_notifier.py
  python scripts/calendar_notifier.py --test   # Bugünkü etkinlikleri test et
"""

import os
import sys
import argparse
import requests
from datetime import datetime, timedelta, date
from pathlib import Path

try:
    from icalendar import Calendar, vDatetime
    import pytz
except ImportError:
    print("[KURULUM] Gerekli kütüphaneler: pip install icalendar pytz requests")
    sys.exit(1)

# ─── Konfigurasyon ───────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PRIVATE_ID  = os.environ.get("TELEGRAM_PRIVATE_ID", "1403072107")
TR_TZ       = pytz.timezone("Europe/Istanbul")
API         = f"https://api.telegram.org/bot{BOT_TOKEN}"

# iCal URL'leri — GitHub Secrets'dan gelir (virgülle ayrılmış liste)
# GCAL_ICAL_URLS = "https://calendar.google.com/calendar/ical/.../basic.ics,https://..."
# GCAL_ICAL_NAMES = "Ana Takvim,Finansal Tablolar"   ← sıra eşleşmeli
ICAL_URLS_RAW   = os.environ.get("GCAL_ICAL_URLS", "")
ICAL_NAMES_RAW  = os.environ.get("GCAL_ICAL_NAMES", "")


def _build_calendar_map() -> dict[str, str]:
    """Env değişkenlerinden takvim adı → URL eşlemesi oluştur."""
    urls  = [u.strip() for u in ICAL_URLS_RAW.split(",") if u.strip()]
    names = [n.strip() for n in ICAL_NAMES_RAW.split(",") if n.strip()]

    # İsimler eksikse otomatik adlandır
    while len(names) < len(urls):
        names.append(f"Takvim {len(names) + 1}")

    return {names[i]: urls[i] for i in range(len(urls))}


def send_telegram(message: str) -> bool:
    """Telegram DM gönder."""
    if not BOT_TOKEN:
        print("[HATA] TELEGRAM_BOT_TOKEN eksik!")
        return False
    payload = {
        "chat_id":               PRIVATE_ID,
        "text":                  message,
        "parse_mode":            "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=15)
        ok = r.json().get("ok", False)
        if not ok:
            print(f"[HATA] Telegram yanıtı: {r.text[:200]}")
        return ok
    except Exception as e:
        print(f"[HATA] Telegram bağlantısı: {e}")
        return False


def _parse_dt(component) -> tuple[date | None, str]:
    """iCal bileşeninden tarih ve saat string'i döndür."""
    dtstart = component.get("dtstart")
    if not dtstart:
        return None, "?"
    dt = dtstart.dt

    if isinstance(dt, datetime):
        # Timezone'u Türkiye saatine çevir
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        dt_tr = dt.astimezone(TR_TZ)
        return dt_tr.date(), dt_tr.strftime("%H:%M")
    else:
        # Tüm gün etkinlik (date objesi)
        return dt, "Tüm gün"


def fetch_events(target_date: date) -> list[dict]:
    """Tüm takvimlerde belirtilen tarihteki etkinlikleri topla."""
    takvimler = _build_calendar_map()

    if not takvimler:
        print("[UYARI] Hiç iCal URL'si tanımlanmamış. GCAL_ICAL_URLS secret'ını kontrol et.")
        return []

    tum_etkinlikler = []

    for takvim_adi, url in takvimler.items():
        print(f"  [{takvim_adi}] İndiriliyor...")
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "FinzoraAI/1.0"})
            resp.raise_for_status()
            cal = Calendar.from_ical(resp.content)

            for component in cal.walk():
                if component.name != "VEVENT":
                    continue

                event_date, event_time = _parse_dt(component)
                if event_date != target_date:
                    continue

                summary     = str(component.get("summary",     "İsimsiz Etkinlik"))
                description = str(component.get("description", ""))
                location    = str(component.get("location",    ""))

                # Tekrarlayan etkinlikler için RRULE kontrolü (basit)
                rrule = component.get("rrule")

                tum_etkinlikler.append({
                    "takvim":      takvim_adi,
                    "baslik":      summary,
                    "saat":        event_time,
                    "aciklama":    description[:300] if description and description != "None" else "",
                    "konum":       location if location and location != "None" else "",
                    "tekrar":      bool(rrule),
                    "tarih":       event_date,
                })

        except requests.HTTPError as e:
            print(f"  [{takvim_adi}] HTTP HATASI {e.response.status_code}: {url[:60]}...")
        except Exception as e:
            print(f"  [{takvim_adi}] HATA: {e}")

    # Saat sıralaması (tüm gün etkinlikler en önce)
    tum_etkinlikler.sort(key=lambda x: x["saat"] if x["saat"] != "Tüm gün" else "00:00")
    return tum_etkinlikler


def _gun_adi(d: date) -> str:
    """Türkçe gün adı."""
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return gunler[d.weekday()]


def _aylar():
    return ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
            "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]


def _tarih_str(d: date) -> str:
    return f"{_gun_adi(d)}, {d.day} {_aylar()[d.month - 1]} {d.year}"


def format_mesaj(etkinlikler: list[dict], hedef_tarih: date, test_modu: bool = False) -> str:
    """Telegram mesajı oluştur."""
    etiket = "BUGÜN" if test_modu else "YARIN"
    tarih  = _tarih_str(hedef_tarih)

    if not etkinlikler:
        return (
            f"📅 <b>TAKVİM — {etiket}</b>\n"
            f"<i>{tarih}</i>\n\n"
            f"✅ {etiket.lower()} için herhangi bir etkinlik bulunamadı.\n\n"
            f"<i>finzora ai • takvim bildirimi</i>"
        )

    msg  = f"📅 <b>TAKVİM BİLDİRİMİ — {etiket}</b>\n"
    msg += f"<i>{tarih}</i>\n"
    msg += f"🔔 <b>{len(etkinlikler)}</b> etkinlik var\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"

    for i, ev in enumerate(etkinlikler, 1):
        # Saat ikonu
        saat_ikon = "🕐" if ev["saat"] != "Tüm gün" else "📆"
        # Tekrar ikonu
        tekrar_ikon = "🔁 " if ev["tekrar"] else ""

        msg += f"\n<b>{i}. {ev['baslik']}</b> {tekrar_ikon}\n"
        msg += f"{saat_ikon} {ev['saat']}"

        if ev["konum"]:
            msg += f"  📍 {ev['konum']}"
        msg += "\n"

        msg += f"📂 {ev['takvim']}\n"

        if ev["aciklama"]:
            aciklama = ev["aciklama"]
            if len(aciklama) > 150:
                aciklama = aciklama[:150] + "..."
            msg += f"📝 <i>{aciklama}</i>\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━"
    msg += f"\n<i>finzora ai • takvim bildirimi</i>"
    return msg


def main():
    parser = argparse.ArgumentParser(description="Finzora Takvim Bildirici")
    parser.add_argument("--test", action="store_true",
                        help="Bugünkü etkinlikleri test et (yarın yerine)")
    args = parser.parse_args()

    simdi      = datetime.now(TR_TZ)
    test_modu  = args.test
    hedef      = simdi.date() if test_modu else (simdi + timedelta(days=1)).date()
    etiket     = "BUGÜN (TEST)" if test_modu else "YARIN"

    print(f"[{simdi.strftime('%H:%M:%S')}] Finzora Takvim Bildirici başlatıldı")
    print(f"  Hedef tarih : {hedef} ({etiket})")
    print(f"  Telegram ID : {PRIVATE_ID}")

    etkinlikler = fetch_events(hedef)
    print(f"  Sonuç       : {len(etkinlikler)} etkinlik bulundu")

    mesaj = format_mesaj(etkinlikler, hedef, test_modu)
    print(f"\n{'─'*50}")
    print(mesaj)
    print(f"{'─'*50}\n")

    ok = send_telegram(mesaj)
    print(f"  Telegram    : {'✅ gönderildi' if ok else '❌ GÖNDERİLEMEDİ'}")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
