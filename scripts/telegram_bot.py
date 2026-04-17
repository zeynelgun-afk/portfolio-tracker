#!/usr/bin/env python3
"""
Finzora Telegram Bot — Hisse Sorgu Yanıtlayıcı
=================================================
Kullanıcı Telegram'dan ticker gönderince:
  1. getUpdates ile yeni mesajları yakala
  2. Ticker pattern'ı tespit et (1-6 büyük harf/rakam)
  3. adil_deger_calculator ile analiz yap
  4. Aynı kanala formatlanmış yanıt gönder

Çalışma: GitHub Actions (5dk schedule) veya monitor run içinde

Komutlar:
  AAPL         → Adil değer analizi
  /deger AAPL  → Aynı
  /beklenti AAPL → Analist + forward beklentiler
  /portfoy     → Açık portföy durumu
  /yardim      → Komut listesi
"""

import os, sys, json, re, requests, time
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
PRIVATE_CHAT = os.environ.get("TELEGRAM_PRIVATE_CHAT", "")
GROUP_CHAT   = "-1003827034395"
API_BASE     = f"https://api.telegram.org/bot{BOT_TOKEN}"
REPO_ROOT    = Path(__file__).parent.parent
OFFSET_FILE  = REPO_ROOT / "data" / "telegram_offset.json"
FMP_KEY      = os.environ.get("FMP_API_KEY", "")
FMP_BASE     = "https://financialmodelingprep.com/stable"

# Yanıt gönderilebilecek chat ID'ler (güvenlik)
IZINLI_CHATLER = {PRIVATE_CHAT, GROUP_CHAT, str(PRIVATE_CHAT)}

# Ticker pattern: 1-6 büyük harf, opsiyonel rakam
TICKER_PATTERN = re.compile(r'^[A-Z]{1,6}[0-9]?$')


# ── Telegram API ──────────────────────────────────────────────────────────────

def tg_get(endpoint, params=None):
    try:
        r = requests.get(f"{API_BASE}/{endpoint}", params=params or {}, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[TG] GET {endpoint} hatası: {e}")
        return None


def tg_send(chat_id, text, parse_mode="HTML", reply_to=None):
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_to:
            payload["reply_to_message_id"] = reply_to
        r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
        d = r.json()
        if not d.get("ok"):
            print(f"[TG] Gönderim hatası: {d.get('description','?')}")
        return d.get("ok", False)
    except Exception as e:
        print(f"[TG] send hatası: {e}")
        return False


# ── Offset Yönetimi ───────────────────────────────────────────────────────────

def load_offset() -> int:
    try:
        if OFFSET_FILE.exists():
            d = json.load(open(OFFSET_FILE))
            return d.get("offset", 0)
    except Exception:
        pass
    return 0


def save_offset(offset: int):
    try:
        json.dump({"offset": offset, "ts": datetime.now().isoformat()},
                  open(OFFSET_FILE, "w"))
    except Exception as e:
        print(f"[Offset] Kayıt hatası: {e}")


# ── Analist + Beklentiler ─────────────────────────────────────────────────────

def get_analyst_data(symbol: str) -> dict:
    """Analist hedefleri ve EPS beklentileri."""
    fmp_key = FMP_KEY

    def fmp(ep, p=None):
        p = p or {}; p["apikey"] = fmp_key
        try:
            r = requests.get(f"{FMP_BASE}/{ep}", params=p, timeout=12)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    result = {}

    # Analist hedefi
    pt = fmp("price-target-summary", {"symbol": symbol})
    if pt:
        result["analist_hedef"]  = pt[0].get("lastQuarterAvgPriceTarget")
        result["analist_yuksek"] = pt[0].get("lastQuarterHighPriceTarget")
        result["analist_dusuk"]  = pt[0].get("lastQuarterLowPriceTarget")

    # Konsensus
    cons = fmp("grades-consensus", {"symbol": symbol})
    if cons:
        result["strong_buy"] = cons[0].get("strongBuy", 0)
        result["buy"]        = cons[0].get("buy", 0)
        result["hold"]       = cons[0].get("hold", 0)
        result["sell"]       = cons[0].get("sell", 0)
        result["strong_sell"]= cons[0].get("strongSell", 0)

    # Forward EPS tahmini (analyst-estimates)
    est = fmp("analyst-estimates", {"symbol": symbol, "period": "annual", "limit": 2})
    if est:
        next_yr = est[0] if est else {}
        result["fwd_eps_est"]   = next_yr.get("estimatedEpsAvg")
        result["fwd_rev_est"]   = next_yr.get("estimatedRevenueAvg")
        result["est_tarih"]     = next_yr.get("date", "")[:7]

    # Key metrics TTM
    mttm = fmp("key-metrics-ttm", {"symbol": symbol})
    if mttm:
        result["pe_ttm"]        = mttm[0].get("peRatioTTM")
        result["ev_ebitda"]     = mttm[0].get("evToEbitdaTTM") or mttm[0].get("enterpriseValueOverEBITDATTM")
        result["fcf_yield"]     = mttm[0].get("freeCashFlowYieldTTM")
        result["roe"]           = mttm[0].get("returnOnEquityTTM")
        result["net_margin"]    = mttm[0].get("netProfitMarginTTM")

    return result


# ── Adil Değer Hesaplama ──────────────────────────────────────────────────────

def adil_deger_hesapla(symbol: str) -> dict | None:
    """adil_deger_calculator.hesapla() çağır."""
    try:
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from adil_deger_calculator import hesapla
        return hesapla(symbol.upper(), sessiz=True)
    except Exception as e:
        print(f"[Bot] Hesaplama hatası {symbol}: {e}")
        return None


# ── Mesaj Formatları ──────────────────────────────────────────────────────────

def format_adil_deger(symbol: str, res: dict, analyst: dict) -> str:
    """Adil değer sonucu formatla."""
    price = res.get("price", 0)
    adil  = res.get("adil_deger", 0) or 0
    fark  = res.get("fark_pct", 0) or 0
    guven = res.get("guven", 0)
    tip   = res.get("hisse_tipi", "deger")
    sektor= res.get("sector", "")[:30]

    # Sinyal
    if fark < -20:
        sinyal = "🟢 <b>UCUZ</b>"
    elif fark > 20:
        sinyal = "🔴 <b>PAHALI</b>"
    else:
        sinyal = "🟡 <b>ADİL</b>"

    tip_emoji = {"buyume":"🚀","temettu":"💰","dongusel":"🔄","deger":"📊"}.get(tip,"📊")

    lines = [
        f"<b>📊 {symbol} — Adil Değer Analizi</b>",
        f"<i>{sektor} | {tip_emoji} {tip.upper()}</i>",
        "",
        f"💵 Güncel fiyat:   <b>${price:.2f}</b>",
        f"🎯 Adil değer:     <b>${adil:.2f}</b>",
        f"📏 Fark:          <b>{fark:+.1f}%</b>  →  {sinyal}",
        f"🔍 Güven skoru:   <b>{guven}/100</b>",
    ]

    # Metot tablosu (en önemli 5)
    metotlar = res.get("metotlar", {})
    sirala = ["Net Kazanç P/E","Forward P/E","EV/EBITDA","DCF (3 aşama)","P/FCF","EV/Ciro"]
    metot_satir = []
    for m in sirala:
        v = metotlar.get(m)
        if v and v > 0:
            diff = (price/v - 1)*100
            ico  = "↑" if diff > 10 else ("↓" if diff < -10 else "≈")
            metot_satir.append(f"  {m:<18} ${v:>7.2f} ({diff:>+.0f}%) {ico}")
    if metot_satir:
        lines += ["", "<b>Değerleme Metotları:</b>"] + metot_satir

    # Analist bölümü
    at = analyst.get("analist_hedef")
    if at:
        at_diff = (price/at - 1)*100
        at_ico  = "↑" if at_diff < -5 else ("↓" if at_diff > 5 else "≈")
        cons_str = ""
        sb = analyst.get("strong_buy", 0)
        b  = analyst.get("buy", 0)
        h  = analyst.get("hold", 0)
        s  = (analyst.get("sell", 0) or 0) + (analyst.get("strong_sell", 0) or 0)
        total_an = sb + b + h + s
        if total_an > 0:
            al_pct = (sb + b) / total_an * 100
            cons_str = f" | AL:%{al_pct:.0f} Tut:%{h/total_an*100:.0f}"
        lines += [
            "",
            "<b>📈 Analist Görüşü:</b>",
            f"  Hedef: ${at:.2f} ({at_diff:+.1f}%) {at_ico}{cons_str}",
        ]
        if analyst.get("fwd_eps_est"):
            fwd_pe = price / analyst["fwd_eps_est"]
            lines.append(f"  Fwd EPS ({analyst.get('est_tarih','?')}): ${analyst['fwd_eps_est']:.2f} → Fwd P/E: {fwd_pe:.1f}x")

    # Key metrics
    lines += ["", "<b>📐 Temel Metrikler:</b>"]
    pe = analyst.get("pe_ttm"); roe = analyst.get("roe"); fcfy = analyst.get("fcf_yield")
    evebitda = analyst.get("ev_ebitda")
    if pe:     lines.append(f"  P/E TTM:      {pe:.1f}x")
    if evebitda: lines.append(f"  EV/EBITDA:    {evebitda:.1f}x")
    if roe:    lines.append(f"  ROE:          {roe*100:.1f}%")
    if fcfy:   lines.append(f"  FCF Verimi:   {fcfy*100:.1f}%")

    # Bant
    lines += [
        "",
        f"📊 Bantlar: <b>${adil*0.8:.2f}</b> (-%20) ← ADİL → <b>${adil*1.2:.2f}</b> (+%20)",
        "",
        "<i>finzora.ai — yatırım tavsiyesi değildir</i>",
    ]

    return "\n".join(lines)


def format_yardim() -> str:
    return """<b>🤖 Finzora AI Bot — Komutlar</b>

<b>Hisse Analizi:</b>
  <code>AAPL</code> veya <code>/deger AAPL</code>
  → Adil değer, değerleme metotları, analist görüşü

<b>Diğer:</b>
  <code>/portfoy</code> — Açık pozisyon özeti
  <code>/yardim</code>  — Bu menü

<b>Örnek:</b>
  <code>MU</code> → Micron adil değer analizi
  <code>NVDA</code> → Nvidia analizi

<i>Yanıt süresi: ~1-2 dakika</i>"""


def format_portfoy() -> str:
    """Kısa portföy özeti."""
    lines = ["<b>📊 Portföy Özeti</b>", ""]
    try:
        LABELS = {"aggressive":"⚡Agresif","balanced":"⚖️Dengeli","dividend":"💰Temettü"}
        STARTS = {"aggressive":400000,"balanced":100000,"dividend":100000}
        for pf, label in LABELS.items():
            d = json.load(open(REPO_ROOT / "data" / "portfolios" / f"{pf}.json"))
            pozlar = d.get("pozisyonlar", [])
            nakit  = float(d.get("nakit", {}).get("miktar", 0))
            deger  = sum(p.get("adet",0)*float(p.get("guncel_fiyat") or p.get("maliyet_baz",0)) for p in pozlar) + nakit
            pnl    = (deger - STARTS[pf]) / STARTS[pf] * 100
            ico    = "🟢" if pnl >= 0 else "🔴"
            lines.append(f"{ico} {label}: ${deger:,.0f} ({pnl:+.1f}%)")
            for p in pozlar:
                sym  = p.get("sembol","")
                mal  = float(p.get("maliyet_baz",0))
                gun  = float(p.get("guncel_fiyat") or mal)
                ppnl = (gun-mal)/mal*100 if mal else 0
                pi   = "🟢" if ppnl>=0 else "🔴"
                lines.append(f"  {pi} {sym:5} {ppnl:+.1f}%")
            lines.append("")
    except Exception as e:
        lines.append(f"Hata: {e}")
    lines.append("<i>Detay: finzora.ai</i>")
    return "\n".join(lines)


# ── Mesaj İşleyici ────────────────────────────────────────────────────────────

def isle_mesaj(msg: dict):
    chat_id  = str(msg.get("chat", {}).get("id", ""))
    msg_id   = msg.get("message_id")
    text     = (msg.get("text") or "").strip()
    user     = msg.get("from", {}).get("first_name", "?")

    if not text or chat_id not in IZINLI_CHATLER:
        return

    print(f"[Bot] Mesaj [{chat_id}] {user}: {text[:50]}")

    text_upper = text.upper().strip()

    # ── /yardim ──────────────────────────────────────────────────
    if text.lower() in ("/yardim", "/help", "/start"):
        tg_send(chat_id, format_yardim(), reply_to=msg_id)
        return

    # ── /portfoy ─────────────────────────────────────────────────
    if text.lower() in ("/portfoy", "/portfolio", "/portföy"):
        tg_send(chat_id, format_portfoy(), reply_to=msg_id)
        return

    # ── Ticker tespiti ────────────────────────────────────────────
    ticker = None

    # "/deger AAPL" veya "/beklenti AAPL"
    if text.upper().startswith("/DEGER ") or text.upper().startswith("/BEKLENTI "):
        parts = text.split()
        if len(parts) >= 2:
            ticker = parts[1].upper()

    # Doğrudan ticker: "AAPL", "MU", "NVDA"
    elif TICKER_PATTERN.match(text_upper) and len(text_upper) >= 2:
        # Yaygın Türkçe kelimeleri/komutları dışla
        DISI = {
            "VE","DE","DA","BU","ŞU","BİR","IKI","UC","BES","ON",
            "YOK","VAR","GEL","GIT","AL","SAT","OKE","EKI","IYI",
            "TAMAM","EVET","HAYIR","MERHABA","SELAM","TEKRAR","ESKI",
            "YENI","ARTIK","ZATEN","HATTA","SADECE","VEYA","ANCAK",
            "BELKI","SANKI","KALAN","DIGER","BUNUN","ONUN","OLAN",
            # Yaygın İngilizce (kısa) kelimeler
            "THE","AND","FOR","ARE","BUT","NOT","YOU","ALL","CAN",
            "HER","WAS","ONE","OUR","OUT","DAY","GET","HAS","HIM",
            "HIS","HOW","ITS","WHO","OIL","NOW","OLD","SEE","TWO",
            "WAY","MAY","SET","SAY","PUT","NEW","MAN","END","ADD",
            "TOO","TOP","USE","ANY","AIR","EYE","FAR","FEW","LAW",
            "LET","LOW","OWN","PAY","RUN","SIX","TEN","YES","ACT",
            "AGO","AID","AIM","ART","ASK","BIG","BOX","BOY","CUT",
            "DID","DIG","DUE","EAR","EAT","ERA","FAD","FAN","FAR",
            "FAT","FED","FIT","FLY","FUN","GAP","GAY","GUN","GUT",
            "GUY","HAD","HAT","HIT","HOT","HUG","HUT","ICE","ILL",
            "INK","INN","ION","IRE","JAB","JAM","JAR","JAW","JET",
            "JOB","JOG","JOT","JOY","JUG","KIT","LAB","LAD","LAG",
            "LAP","LAW","LAX","LAY","LID","LIE","LIT","LOG","LOT",
            "MAP","MAR","MAT","MIX","MOB","MOD","MOP","MUD","MUG",
        }
        if text_upper not in DISI:
            ticker = text_upper

    if not ticker:
        return  # Tanımadık mesaj — sessiz geç

    # ── Analiz başlıyor ───────────────────────────────────────────
    tg_send(chat_id, f"⏳ <b>{ticker}</b> analiz ediliyor...", reply_to=msg_id)

    res = adil_deger_hesapla(ticker)
    if not res:
        tg_send(chat_id,
                f"❌ <b>{ticker}</b> için veri bulunamadı.\nTicker doğru mu? (NYSE/NASDAQ sembolü girin)",
                reply_to=msg_id)
        return

    analyst = get_analyst_data(ticker)
    mesaj   = format_adil_deger(ticker, res, analyst)
    tg_send(chat_id, mesaj, reply_to=msg_id)
    print(f"[Bot] {ticker} yanıtı gönderildi → {chat_id}")


# ── Ana Döngü ─────────────────────────────────────────────────────────────────

def _process_updates(offset: int) -> int:
    """Tek bir getUpdates turu — offset döndürür."""
    updates = tg_get("getUpdates", {"offset": offset, "timeout": 30, "limit": 20})
    if not updates or not updates.get("ok"):
        return offset

    new_offset = offset
    for upd in updates.get("result", []):
        new_offset = max(new_offset, upd["update_id"] + 1)
        msg = upd.get("message") or upd.get("edited_message")
        if msg:
            isle_mesaj(msg)

    if new_offset > offset:
        save_offset(new_offset)

    return new_offset


def main():
    """
    Mod seçimi:
    - RAILWAY=1 → Sürekli polling (7/24)
    - Aksi halde → GitHub Actions modu (tek çalışma)
    """
    railway_mode = os.environ.get("RAILWAY") or os.environ.get("RAILWAY_ENVIRONMENT")

    if railway_mode:
        # ── Railway: Sürekli polling ──────────────────────────────
        print(f"[Bot] Railway modu — sürekli polling başlıyor")
        print(f"[Bot] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        offset = load_offset()
        hata_sayisi = 0

        while True:
            try:
                offset = _process_updates(offset)
                hata_sayisi = 0
                time.sleep(1)   # 1sn bekleme — rate limit koruması
            except KeyboardInterrupt:
                print("[Bot] Durduruldu.")
                break
            except Exception as e:
                hata_sayisi += 1
                print(f"[Bot] Hata #{hata_sayisi}: {e}")
                if hata_sayisi > 5:
                    print("[Bot] Çok fazla hata — 60sn bekleniyor")
                    time.sleep(60)
                    hata_sayisi = 0
                else:
                    time.sleep(5)
    else:
        # ── GitHub Actions: Tek çalışma ───────────────────────────
        print(f"[Bot] GitHub Actions modu — {datetime.now().strftime('%H:%M:%S')}")
        offset = load_offset()
        new_offset = _process_updates(offset)
        if new_offset > offset:
            save_offset(new_offset)
            print(f"[Bot] Offset: {offset} → {new_offset}")
        print("[Bot] Tamamlandı.")


if __name__ == "__main__":
    main()
