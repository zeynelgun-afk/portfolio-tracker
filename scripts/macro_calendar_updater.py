#!/usr/bin/env python3
"""
Finzora AI — Makro & Earnings Takvim Güncelleyici
===================================================
ABD makro ekonomik olayları + kazanç takvimi → ICS dosyası → Google Calendar

Her ayın 1'inde GitHub Actions tarafından otomatik çalıştırılır.
Üretilen ICS dosyasına Google Calendar'dan abone olunur.

Çalışma modları:
  python scripts/macro_calendar_updater.py              # gelecek ay
  python scripts/macro_calendar_updater.py --ay 2026-05 # belirli ay
  python scripts/macro_calendar_updater.py --aylar 3    # kaç ay ilerisi (varsayılan: 2)
  python scripts/macro_calendar_updater.py --test       # çıktı önizle, dosya yazma
"""

import os, sys, json, argparse, requests
from datetime import datetime, date, timedelta
from pathlib import Path
from uuid import uuid4
import pytz

try:
    from icalendar import Calendar, Event, vText, vDatetime
    from dateutil.relativedelta import relativedelta
except ImportError:
    print("[KURULUM] pip install icalendar python-dateutil pytz requests")
    sys.exit(1)

# ─── Config ──────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
FMP_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_URL = "https://financialmodelingprep.com/stable"
ET_TZ   = pytz.timezone("America/New_York")
TR_TZ   = pytz.timezone("Europe/Istanbul")
ICS_OUT = ROOT / "data" / "calendars" / "macro_events.ics"

# ─── FOMC Tarihleri (FED yıllık önceden açıklar) ─────────────────────────────
# Tuple: (başlangıç, karar_günü)
FOMC_DATES = {
    2026: [
        ("2026-01-28", "2026-01-29"),
        ("2026-03-18", "2026-03-19"),
        ("2026-05-06", "2026-05-07"),
        ("2026-06-17", "2026-06-18"),
        ("2026-07-28", "2026-07-29"),
        ("2026-09-16", "2026-09-17"),
        ("2026-11-04", "2026-11-05"),
        ("2026-12-15", "2026-12-16"),
    ],
    2027: [
        ("2027-01-27", "2027-01-28"),
        ("2027-03-17", "2027-03-18"),
        ("2027-05-05", "2027-05-06"),
        ("2027-06-16", "2027-06-17"),
        ("2027-07-27", "2027-07-28"),
        ("2027-09-15", "2027-09-16"),
        ("2027-11-03", "2027-11-04"),
        ("2027-12-14", "2027-12-15"),
    ],
}

# ─── İzleme Listeleri ─────────────────────────────────────────────────────────
# Portföy hisseleri (öncelik 1)
PORTFOLIO_TICKERS = {
    "MO", "JNJ", "T", "VZ", "PM",          # Temettü
    "SM", "KOS", "XLE", "RGLD", "FCX",     # Dengeli
}

# S&P 500 mega-cap (piyasayı etkiler)
MEGA_CAP_TICKERS = {
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA",
    "JPM", "V", "UNH", "XOM", "LLY", "MA", "AVGO", "HD", "PG",
    "MRK", "COST", "ABBV", "BAC", "KO", "WMT", "CVX", "CRM",
    "AMD", "NFLX", "TMO", "PLTR", "BKNG", "BX", "GS", "MS",
    "C", "WFC", "UBER", "DIS", "SBUX", "INTC", "QCOM", "TXN",
    "MU", "SNOW", "ORCL", "IBM", "COP", "SLB", "EOG", "RTX",
    "CAT", "DE", "BA", "HON", "GE",
}

ALL_TICKERS = PORTFOLIO_TICKERS | MEGA_CAP_TICKERS

# ─── Öncelikli Makro Olay Anahtar Kelimeleri ─────────────────────────────────
# Bu kelimeler event adında geçiyorsa dahil et
PRIORITY_HIGH = [
    "Nonfarm Payroll", "Non-Farm Payroll",
    "CPI", "Consumer Price Index",
    "Core CPI", "Core Consumer Price",
    "PCE Price", "Core PCE",
    "GDP", "Gross Domestic Product",
    "Federal Funds", "Interest Rate Decision", "FOMC",
    "Unemployment Rate", "Initial Jobless Claims",
    "PPI", "Producer Price",
    "Retail Sales",
    "ISM Manufacturing PMI", "ISM Services PMI",
    "ISM Non-Manufacturing PMI",
    "JOLTs Job Openings", "JOLTS",
    "Consumer Confidence",
    "Michigan Consumer",
    "ADP Employment",
    "Trade Balance",
    "Durable Goods",
]

# Medium etkili ama dahil edilecek (keyword içerirse)
PRIORITY_MEDIUM = [
    "Housing Starts", "Building Permits",
    "Existing Home Sales", "New Home Sales",
    "Industrial Production",
    "Factory Orders",
    "ISM Manufacturing Employment",
    "Pending Home Sales",
]

# Kesinlikle dahil etme (gürültü)
EXCLUDE_KEYWORDS = [
    "CFTC", "speculative net", "Baker Hughes",
    "Mortgage Application", "MBA ",
    "API Crude", "EIA Crude",
    "Cushing", "Natural Gas Storage",
    "Redbook", "Challenger",
]


# 10 May 2026 — canonical fmp_client'a migrasyon. Boş veride [] döner (geri uyum).
import sys as _sys_fmp
from pathlib import Path as _Path_fmp

_AGENT_DIR = _Path_fmp(__file__).resolve().parent.parent / "agent"
if str(_AGENT_DIR) not in _sys_fmp.path:
    _sys_fmp.path.insert(0, str(_AGENT_DIR))

try:
    from fmp_client import fmp_get as _canonical_fmp_get

    def fmp_get(endpoint: str, params: dict) -> list:
        """fmp_client wrapper. Boş/hata durumunda [] döner."""
        result = _canonical_fmp_get(endpoint, params)
        return result if isinstance(result, list) else []
except ImportError:
    def fmp_get(endpoint: str, params: dict) -> list:
        """FMP API çağrısı (fallback)."""
        params["apikey"] = FMP_KEY
        try:
            r = requests.get(f"{FMP_URL}/{endpoint}", params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"  [HATA] FMP {endpoint}: {e}")
            return []


def fetch_macro_events(baslangic: date, bitis: date) -> list[dict]:
    """FMP'den ABD makro olayları çek, filtrele ve düzenle."""
    raw = fmp_get("economic-calendar", {
        "from": baslangic.isoformat(),
        "to":   bitis.isoformat(),
    })

    events = []
    for e in raw:
        if e.get("country") != "US":
            continue
        name   = e.get("event", "")
        impact = e.get("impact", "Low")

        # Hariç tut
        if any(kw.lower() in name.lower() for kw in EXCLUDE_KEYWORDS):
            continue

        # Öncelik kontrol
        is_high   = any(kw.lower() in name.lower() for kw in PRIORITY_HIGH)
        is_medium = any(kw.lower() in name.lower() for kw in PRIORITY_MEDIUM)

        if not (is_high or (is_medium and impact in ("High", "Medium"))):
            continue
        if impact not in ("High", "Medium"):
            continue

        # Tarih / saat parse
        raw_date = e.get("date", "")
        try:
            dt_et = ET_TZ.localize(datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S"))
            dt_tr = dt_et.astimezone(TR_TZ)
            event_date = dt_tr.date()
            event_time = dt_tr.strftime("%H:%M")
        except Exception:
            try:
                event_date = date.fromisoformat(raw_date[:10])
                event_time = "?"
            except Exception:
                continue

        # Önceki/tahmin
        onceki  = e.get("previous")
        tahmin  = e.get("estimate")
        gercek  = e.get("actual")
        birim   = e.get("unit", "")

        def _fmt(val):
            if val is None: return "—"
            if birim and "%" in birim: return f"{val}%"
            return str(val)

        aciklama = f"Önceki: {_fmt(onceki)}"
        if tahmin is not None:
            aciklama += f" | Tahmin: {_fmt(tahmin)}"
        if gercek is not None:
            aciklama += f" | Gerçek: {_fmt(gercek)}"

        events.append({
            "tip":       "makro",
            "tarih":     event_date,
            "saat":      event_time,
            "baslik":    f"🇺🇸 {name}",
            "aciklama":  aciklama,
            "etki":      impact,
            "sembol":    None,
        })

    return events


def fetch_earnings(baslangic: date, bitis: date) -> list[dict]:
    """FMP'den kazanç takvimi çek, izleme listesiyle filtrele."""
    raw = fmp_get("earnings-calendar", {
        "from": baslangic.isoformat(),
        "to":   bitis.isoformat(),
    })

    events = []
    for e in raw:
        sym = e.get("symbol", "")
        if sym not in ALL_TICKERS:
            continue

        raw_date = e.get("date", "")
        try:
            event_date = date.fromisoformat(raw_date[:10])
        except Exception:
            continue

        eps_est = e.get("epsEstimated")
        rev_est = e.get("revenueEstimated")
        eps_act = e.get("epsActual")
        rev_act = e.get("revenueActual")

        def _m(v):
            if v is None: return "—"
            if abs(v) >= 1e9: return f"${v/1e9:.1f}B"
            if abs(v) >= 1e6: return f"${v/1e6:.0f}M"
            return f"${v:.2f}"

        is_portfolio = sym in PORTFOLIO_TICKERS
        emoji = "⭐" if is_portfolio else "📊"
        baslik = f"{emoji} {sym} Bilanço"

        aciklama_parts = []
        if eps_est is not None:
            aciklama_parts.append(f"EPS Tahmin: ${eps_est:.2f}")
        if eps_act is not None:
            aciklama_parts.append(f"EPS Gerçek: ${eps_act:.2f}")
        if rev_est is not None:
            aciklama_parts.append(f"Gelir Tahmin: {_m(rev_est)}")
        if rev_act is not None:
            aciklama_parts.append(f"Gelir Gerçek: {_m(rev_act)}")

        events.append({
            "tip":      "earnings",
            "tarih":    event_date,
            "saat":     "?",
            "baslik":   baslik,
            "aciklama": " | ".join(aciklama_parts) if aciklama_parts else "Tahmin henüz yok",
            "etki":     "High" if is_portfolio else "Medium",
            "sembol":   sym,
        })

    return events


def fetch_fomc(baslangic: date, bitis: date) -> list[dict]:
    """Sabit FOMC tarihlerinden aralığa düşenleri döndür."""
    events = []
    all_fomc = []
    for yil_dates in FOMC_DATES.values():
        all_fomc.extend(yil_dates)

    for basl_str, karar_str in all_fomc:
        try:
            basl_d  = date.fromisoformat(basl_str)
            karar_d = date.fromisoformat(karar_str)
        except Exception:
            continue

        # Karar günü aralıkta mı?
        if not (baslangic <= karar_d <= bitis):
            continue

        events.append({
            "tip":      "fomc",
            "tarih":    basl_d,
            "bitis":    karar_d + timedelta(days=1),   # ICS end (exclusive)
            "saat":     "tüm gün",
            "baslik":   "🏦 FOMC Toplantısı — FED Faiz Kararı",
            "aciklama": (
                f"Federal Reserve Para Politikası Toplantısı\n"
                f"Başlangıç: {basl_d.strftime('%d.%m.%Y')}\n"
                f"Karar Günü: {karar_d.strftime('%d.%m.%Y')}\n"
                "Saat: ~21:00 TR (16:00 ET)"
            ),
            "etki":     "High",
            "sembol":   None,
        })

    return events


def build_ics(events: list[dict], uretim_tarihi: date) -> Calendar:
    """ICS Calendar objesi oluştur."""
    cal = Calendar()
    cal.add("prodid",  "-//Finzora AI//Makro Takvim//TR")
    cal.add("version", "2.0")
    cal.add("calscale","GREGORIAN")
    cal.add("method",  "PUBLISH")
    cal.add("x-wr-calname",    "📈 Finzora — Makro & Earnings")
    cal.add("x-wr-caldesc",    "ABD Makro Olaylar + Kazanç Takvimi | finzora.ai")
    cal.add("x-wr-timezone",   "Europe/Istanbul")
    cal.add("x-published-ttl", "PT1H")

    for ev in events:
        ie = Event()
        ie.add("uid",     str(uuid4()) + "@finzora.ai")
        ie.add("summary", vText(ev["baslik"]))

        tarih = ev["tarih"]
        bitis = ev.get("bitis")

        if isinstance(tarih, date):
            if bitis:
                # Çok günlük etkinlik (FOMC)
                ie.add("dtstart", tarih)
                ie.add("dtend",   bitis)
            else:
                # Tek gün tüm gün
                ie.add("dtstart", tarih)
                ie.add("dtend",   tarih + timedelta(days=1))
        else:
            ie.add("dtstart", tarih)
            ie.add("dtend",   tarih + timedelta(hours=1))

        # Açıklama
        aciklama = ev.get("aciklama", "")
        if ev.get("saat") and ev["saat"] not in ("?", "tüm gün"):
            aciklama = f"Türkiye Saati: {ev['saat']}\n" + aciklama
        ie.add("description", vText(aciklama))

        # Renk kategorisi
        etki = ev.get("etki", "")
        tip  = ev.get("tip", "")
        if tip == "fomc":
            ie.add("categories", vText("FOMC"))
        elif etki == "High":
            ie.add("categories", vText("Yüksek Etki"))
        else:
            ie.add("categories", vText("Orta Etki"))

        # Dtstamp
        ie.add("dtstamp", datetime.utcnow().replace(tzinfo=pytz.utc))

        cal.add_component(ie)

    return cal


def yaz_ics(cal: Calendar):
    """ICS dosyasını kaydet."""
    ICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(ICS_OUT, "wb") as f:
        f.write(cal.to_ical())
    print(f"  ICS kaydedildi: {ICS_OUT}")
    print(f"  Boyut: {ICS_OUT.stat().st_size / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="Finzora Makro Takvim Güncelleyici")
    parser.add_argument("--ay",    help="YYYY-MM formatında ay (ör: 2026-05)")
    parser.add_argument("--aylar", type=int, default=2,
                        help="Kaç ay ilerisi (varsayılan: 2)")
    parser.add_argument("--test",  action="store_true",
                        help="Önizleme — dosya yazma")
    args = parser.parse_args()

    bugun = date.today()
    simdi = datetime.now(TR_TZ).strftime("%H:%M:%S")
    print(f"[{simdi}] Finzora Makro Takvim Güncelleyici başlatıldı")

    # Tarih aralığını belirle
    if args.ay:
        yil, ay = map(int, args.ay.split("-"))
        baslangic = date(yil, ay, 1)
    else:
        # Bu ay + sonraki N ay
        baslangic = bugun.replace(day=1)

    # Son gün: N ay sonrasının son günü
    bitis = (baslangic + relativedelta(months=args.aylar + 1)) - timedelta(days=1)
    print(f"  Kapsam   : {baslangic} → {bitis}")

    tum_events = []

    # 1. FOMC
    print("\n[1/3] FOMC tarihleri alınıyor...")
    fomc = fetch_fomc(baslangic, bitis)
    tum_events.extend(fomc)
    print(f"  → {len(fomc)} FOMC toplantısı")

    # 2. Makro olaylar
    print("\n[2/3] FMP Ekonomik takvim alınıyor...")
    makro = fetch_macro_events(baslangic, bitis)
    tum_events.extend(makro)
    print(f"  → {len(makro)} makro olay")

    # 3. Earnings
    print("\n[3/3] FMP Kazanç takvimi alınıyor...")
    earnings = fetch_earnings(baslangic, bitis)
    tum_events.extend(earnings)
    portfoy_sayisi = sum(1 for e in earnings if e["sembol"] in PORTFOLIO_TICKERS)
    megacap_sayisi = len(earnings) - portfoy_sayisi
    print(f"  → {len(earnings)} kazanç (portföy: {portfoy_sayisi}, mega-cap: {megacap_sayisi})")

    # Tarihe göre sırala
    tum_events.sort(key=lambda x: (x["tarih"], x.get("saat", "?") or "?"))

    print(f"\n{'─'*50}")
    print(f"Toplam etkinlik: {len(tum_events)}")
    print(f"{'─'*50}")

    # Özet önizleme
    ay_gruplari = {}
    for ev in tum_events:
        ay_key = ev["tarih"].strftime("%B %Y")
        ay_gruplari.setdefault(ay_key, []).append(ev)

    for ay, evler in ay_gruplari.items():
        fomc_c    = sum(1 for e in evler if e["tip"] == "fomc")
        makro_c   = sum(1 for e in evler if e["tip"] == "makro")
        earn_c    = sum(1 for e in evler if e["tip"] == "earnings")
        print(f"  {ay}: {len(evler)} etkinlik (FOMC:{fomc_c} Makro:{makro_c} Earnings:{earn_c})")

        if args.test:
            for ev in evler[:30]:
                saat = f" [{ev['saat']}]" if ev["saat"] not in ("?", "tüm gün") else ""
                print(f"    {ev['tarih'].strftime('%d.%m')}{saat} {ev['baslik']}")

    print(f"{'─'*50}")

    if args.test:
        print("\n[TEST MODU] ICS dosyası oluşturulmadı.")
        return

    # ICS oluştur ve kaydet
    print("\nICS dosyası oluşturuluyor...")
    cal = build_ics(tum_events, bugun)
    yaz_ics(cal)

    # Abonelik URL'si
    print()
    print("✅ Tamamlandı!")
    print()
    print("📎 Google Calendar Abonelik URL'si:")
    print("   https://raw.githubusercontent.com/zeynelgun-afk/portfolio-tracker/main/data/calendars/macro_events.ics")
    print()
    print("🔄 Abonelik nasıl yapılır:")
    print("   Google Calendar → Sol panel → + (Diğer takvimler)")
    print("   → URL'den → Yukarıdaki URL'yi yapıştır → Takvim Ekle")


if __name__ == "__main__":
    main()
