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
# Sadece Zeynel DM (1403072107). Grup'ta komut alma yasak — grupta sadece alım/satım bildirimi.
IZINLI_CHATLER = {PRIVATE_CHAT, str(PRIVATE_CHAT), "1403072107"}

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
        result["fwd_eps_est"]   = next_yr.get("epsAvg")
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

def adil_deger_hesapla(symbol: str, use_v5: bool = True) -> dict | None:
    """
    Adil değer hesapla — v5 framework (archetype-routed).
    v5 fail olursa None döner (eskiden v2 fallback vardı ama
    adil_deger_calculator shim zaten v5'e yönlendiriyor — sahte fallback).
    """
    symbol = symbol.upper()

    if not use_v5:
        return None

    try:
        agent_dir = str(REPO_ROOT / "agent")
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        from valuation.framework import valuate
        res = valuate(symbol, verbose=False)
        if res and not res.get("error"):
            res["_version"] = "v5"
            return res
        print(f"[Bot] v5 fail {symbol}: {res.get('error') if res else 'None'}")
        return None
    except Exception as e:
        print(f"[Bot] v5 exception {symbol}: {e}")
        return None


# ── Mesaj Formatları ──────────────────────────────────────────────────────────

def _format_v5_fallback(symbol: str, res: dict) -> str:
    """v5 formatter crash ederse elle HTML."""
    cls = res.get("classification", {})
    fv = res.get("fair_value", {})
    conf = res.get("confidence", {})
    methods = res.get("methods_used", [])
    excluded = res.get("methods_excluded", [])

    price = fv.get("current_price", 0)
    fair = fv.get("point", 0)
    upside = fv.get("upside_pct", 0)
    ico = "🟢" if upside > 5 else "🔴" if upside < -5 else "🟡"

    lines = [
        f"<b>{symbol} — Adil Değer v5</b>",
        f"<i>{cls.get('archetype_label','?')} (güven %{cls.get('confidence',0)*100:.0f})</i>",
        "",
        f"{ico} <b>${price:.2f}</b> → hedef <b>${fair:.2f}</b> ({upside:+.1f}%)",
        f"Aralık: ${fv.get('range_low',0):.2f} — ${fv.get('range_high',0):.2f}",
        f"Karar: <b>{fv.get('karar','?')}</b>",
        f"Güven: <b>{conf.get('score',0)}/100</b>",
    ]
    if methods:
        lines.append("")
        lines.append("<b>Kullanılan metotlar:</b>")
        for m in methods[:6]:
            lines.append(f"  {m['name']:28} ${m['fair_value']:.2f} (w={m['weight']:.0%})")
    if excluded:
        lines.append("")
        lines.append(f"<b>Yasaklı ({len(excluded)}):</b> " + ", ".join(e['name'] for e in excluded[:4]))
    if conf.get("red_flags"):
        lines.append("")
        lines.append(f"⚠ {', '.join(conf['red_flags'][:3])}")
    return "\n".join(lines)


def format_adil_deger(symbol: str, res: dict, analyst: dict, detay: bool = False) -> str:
    """Adil değer sonucu formatla. v5 ve v2 result'ları farklı şemaya sahip.
    detay=True → uzun versiyon (telegram_full), False → kısa (telegram)."""

    # ── v5 result ise framework'ün kendi formatter'ını kullan ────────
    if res.get("_version") == "v5":
        try:
            agent_dir = str(REPO_ROOT / "agent")
            if agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
            from valuation.framework import format_report
            style = "telegram_full" if detay else "telegram"
            return format_report(res, style=style)
        except Exception as e:
            return _format_v5_fallback(symbol, res)

    # ── v2 legacy format (ÖLÜ KOD — adil_deger_hesapla artık sadece v5 döner) ───
    # Bu blok, v5 shim'inden önceki adil_deger_calculator doğrudan çağrıldığında
    # kullanılırdı. Artık shim her çağrıda v5 döndürür, bu blok gerçek trafik
    # almayacak. Defensive olarak korunuyor — manuel v2 res dict gelirse
    # çalışır.
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

<b>📅 Takvim &amp; Makro:</b>
  <code>/takvim</code> — Yarınki takvim etkinlikleri (Telegram bildirimi)
  <code>/takvim bugün</code> — Bugünkü etkinlikler
  <code>/makro</code> — Bu haftanın ABD makro olayları (CPI/NFP/PCE…)
  <code>/fomc</code> — Sonraki FOMC toplantısı + kaç gün kaldı
  <code>/kazanc</code> — Önümüzdeki 14 gün bilanço takvimi

<b>Portföy &amp; Pozisyon:</b>
  <code>/portfoy</code> (<code>/pf</code>) — Açık pozisyon özeti
  <code>/swing</code> (<code>/sw</code>) — Aktif swing pozisyonları
  <code>/stats</code> — Bu ay/hafta P&amp;L istatistikleri
  <code>/kapanan</code> (<code>/kp</code>) — Son 5 kapanan trade + dersler
  <code>/watchlist</code> (<code>/iz</code>) — Günlük tarama adayları

<b>Piyasa:</b>
  <code>/vix</code> — Güncel VIX + seviye
  <code>/kriz</code> — K-13 aktif kriz matrisi
  <code>/fiyat AAPL</code> — Canlı fiyat + değişim

<b>Hisse Analizi:</b>
  <code>AAPL</code> veya <code>/deger AAPL</code>
  → Adil değer, değerleme metotları, analist görüşü
  <code>/beklenti AAPL</code> — Analist + EPS beklentileri

<b>Valuation v5 (archetype-routed):</b>
  <code>/vstats</code> — Son 30 gün kaydedilen değerleme özeti
  <code>/backtest</code> (<code>/bt</code>) — ≥14 gün eski tahminlerin hit rate'i

<b>AI (Claude):</b>
  <code>/sor &lt;soru&gt;</code> — Serbest soru (portföy bağlamında)
  <code>/analiz AAPL</code> — Tam tez + risk + portföy uygunluğu

<i>Yanıt süresi: statik 2-5sn, Claude komutları 20-60sn</i>"""


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


def format_swing() -> str:
    """Aktif swing pozisyonları."""
    try:
        d = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
        pozlar = d.get("aktif_pozisyonlar", [])
        if not pozlar:
            return "📊 <b>Swing</b>\n\nAktif pozisyon yok — tarama devam ediyor."

        lines = [f"<b>📊 Swing Pozisyonları ({len(pozlar)}/5)</b>", ""]
        for p in pozlar:
            sym   = p.get("sembol", "?")
            giris = float(p.get("giris_fiyati", p.get("giris_fiyat", 0)) or 0)
            cur   = float(p.get("guncel_fiyat", 0) or 0)
            stop  = float(p.get("stop_loss", 0) or 0)
            hedef = float(p.get("hedef_fiyat", 0) or 0)
            pnl   = float(p.get("kar_zarar_yuzde", p.get("pnl_pct", 0)) or 0)
            gun   = int(p.get("tutulan_gun", 0) or 0)
            ico   = "🟢" if pnl >= 0 else "🔴"
            sd    = (cur - stop) / cur * 100 if cur and stop else 0
            lines.append(
                f"{ico} <b>{sym}</b>  {pnl:+.1f}%  ({gun}g)\n"
                f"   Giriş ${giris:.2f} → ${cur:.2f}\n"
                f"   Stop ${stop:.2f} (%{sd:.1f} uzak) | Hedef ${hedef:.2f}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"Swing verisi okunamadı: {e}"


def format_vix() -> str:
    """Güncel VIX."""
    try:
        import sys as _s
        _s.path.insert(0, str(REPO_ROOT / "agent"))
        from vix_fetcher import get_vix
        value, source = get_vix()
        if value < 18:
            seviye = "🟢 DÜŞÜK (Risk-On)"
        elif value < 25:
            seviye = "🟡 NORMAL"
        elif value < 30:
            seviye = "🟠 YÜKSEK (K-13 aktif)"
        else:
            seviye = "🔴 EKSTREM (giriş dur)"
        return f"<b>📉 VIX</b>\n\nSeviye: <b>{value:.2f}</b>\n{seviye}\n<i>Kaynak: {source}</i>"
    except Exception as e:
        return f"VIX okunamadı: {e}"


def format_kriz() -> str:
    """K-13 kriz matrisi özeti."""
    try:
        d = json.load(open(REPO_ROOT / "data" / "k13_crisis_matrix.json"))
        kriz  = d.get("aktif_kriz", "bilinmiyor")
        benef = d.get("beneficiary", [])
        sens  = d.get("sensitive", [])
        ardisik = d.get("ardisik_gun", 1)
        guven = d.get("son_guven", "?")
        last  = d.get("son_guncelleme", "?")

        lines = [
            f"<b>🌍 K-13 Kriz Matrisi</b>",
            "",
            f"Aktif kriz: <b>{kriz}</b> ({ardisik}. gün)",
            f"Claude güveni: {guven}/10",
            f"Son güncelleme: {last}",
        ]
        if benef:
            lines.append(f"\n<b>🟢 Faydalanıcı sektörler:</b>")
            lines.append("  " + ", ".join(benef))
        if sens:
            lines.append(f"\n<b>🔴 Duyarlı sektörler:</b>")
            lines.append("  " + ", ".join(sens))
        if not benef and not sens:
            lines.append("\n<i>Kriz yok — standart VIX eşikleri aktif</i>")
        return "\n".join(lines)
    except Exception as e:
        return f"Kriz matrisi okunamadı: {e}"


def format_stats() -> str:
    """Bu ay/hafta P&L istatistikleri."""
    try:
        d = json.load(open(REPO_ROOT / "data" / "swing" / "closed.json"))
        trades = d.get("kapatilan_pozisyonlar", d.get("kapali_pozisyonlar", []))

        if not trades:
            return "📈 İstatistik yok — henüz kapanan trade yok."

        from datetime import datetime, timedelta
        bugun = datetime.now()
        ay_onces = bugun - timedelta(days=30)
        hafta_onces = bugun - timedelta(days=7)

        son_30 = []
        son_7  = []
        for t in trades:
            try:
                cd = datetime.strptime(t.get("cikis_tarihi", ""), "%Y-%m-%d")
                if cd >= ay_onces:
                    son_30.append(t)
                if cd >= hafta_onces:
                    son_7.append(t)
            except ValueError:
                continue

        def _stats(batch):
            if not batch:
                return "0 trade"
            n = len(batch)
            pnls = [float(t.get("kar_zarar_yuzde", t.get("pnl_pct", 0)) or 0) for t in batch]
            wins = sum(1 for p in pnls if p > 0)
            avg = sum(pnls)/n
            best = max(pnls)
            worst = min(pnls)
            return f"{n} trade | %{wins/n*100:.0f} win | ort {avg:+.1f}% | en iyi {best:+.1f}% / en kötü {worst:+.1f}%"

        lines = [
            "<b>📈 Swing İstatistikleri</b>",
            "",
            f"Son 7 gün: {_stats(son_7)}",
            f"Son 30 gün: {_stats(son_30)}",
            f"Tüm zaman ({len(trades)} trade):",
        ]
        all_pnls = [float(t.get("kar_zarar_yuzde", t.get("pnl_pct", 0)) or 0) for t in trades]
        all_wins = sum(1 for p in all_pnls if p > 0)
        lines.append(f"  %{all_wins/len(trades)*100:.0f} win | ort {sum(all_pnls)/len(trades):+.2f}%")
        return "\n".join(lines)
    except Exception as e:
        return f"Stats okunamadı: {e}"


def format_watchlist() -> str:
    """Günlük tarama watchlist."""
    try:
        import html as _html
        p = REPO_ROOT / "data" / "watchlist.json"
        if not p.exists():
            return "📋 Watchlist henüz oluşturulmamış."
        d = json.load(open(p))
        # v3 şeması: izleme_listesi. Eski: adaylar/izlenenler (backward compat)
        adaylar = d.get("izleme_listesi", d.get("adaylar", d.get("izlenenler", [])))
        toplam = len(adaylar)
        if not adaylar:
            return "📋 Watchlist boş."

        # urgency + skor sıralaması: high/medium/low önce, sonra yüksek skor
        urg_rank = {"high": 0, "medium": 1, "low": 2}
        adaylar = sorted(
            adaylar,
            key=lambda x: (
                urg_rank.get(str(x.get("urgency", "")).lower(), 3),
                -float(x.get("skor", x.get("score", 0)) or 0),
            ),
        )[:10]

        lines = [f"<b>📋 Watchlist (top {len(adaylar)}/{toplam})</b>", ""]
        for a in adaylar:
            sym   = a.get("sembol", a.get("symbol", "?"))
            skor  = a.get("skor", a.get("score", "?"))
            port  = a.get("hedef_portfoy", a.get("portfoy", a.get("portföy", "-")))
            urg   = str(a.get("urgency", "")).lower()
            karar = a.get("karar", "")
            tez   = (a.get("tez", a.get("neden", a.get("reason", ""))) or "")[:90]
            hgir  = a.get("hedef_giris", "")
            rr    = a.get("r_r_orani", a.get("r_r", ""))

            ico = {"high": "🔥", "medium": "⚡", "low": "·"}.get(urg, "•")
            head = f"{ico} <b>{_html.escape(str(sym))}</b> ({_html.escape(str(port))}) skor {skor}"
            if karar:
                head += f" [{_html.escape(str(karar))}]"
            if hgir:
                head += f" · giriş {_html.escape(str(hgir))}"
            if rr:
                head += f" · R:R {rr}"
            lines.append(head)
            if tez:
                lines.append(f"   {_html.escape(tez)}")

        # Mekanik karar özeti (varsa)
        mk = d.get("mekanik_kararlar", {})
        if mk:
            ekle = len(mk.get("EKLE", []))
            izle = len(mk.get("IZLE", []))
            gec  = len(mk.get("GEC", []))
            lines.append("")
            lines.append(f"<i>Mekanik: EKLE {ekle} · İZLE {izle} · GEÇ {gec}</i>")

        return "\n".join(lines)
    except Exception as e:
        return f"Watchlist okunamadı: {e}"


def format_kapanan() -> str:
    """Son 5 kapanan swing trade."""
    try:
        d = json.load(open(REPO_ROOT / "data" / "swing" / "closed.json"))
        trades = d.get("kapatilan_pozisyonlar", d.get("kapali_pozisyonlar", []))
        if not trades:
            return "📕 Henüz kapanan trade yok."

        son5 = trades[-5:][::-1]
        lines = ["<b>📕 Son 5 Kapanan Swing</b>", ""]
        for t in son5:
            sym = t.get("sembol", "?")
            pnl = float(t.get("kar_zarar_yuzde", t.get("pnl_pct", 0)) or 0)
            gun = int(t.get("tutulan_gun", t.get("hold_days", 0)) or 0)
            neden = (t.get("cikis_nedeni", "") or "")[:50]
            tarih = t.get("cikis_tarihi", "?")
            ders = (t.get("ders", t.get("dersler", "")) or "")[:100]
            ico = "🟢" if pnl > 0 else "🔴"
            lines.append(f"{ico} <b>{sym}</b> {pnl:+.1f}% ({gun}g) — {tarih}")
            lines.append(f"   Çıkış: {neden}")
            if ders:
                lines.append(f"   💡 {ders}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Kapanan trade'ler okunamadı: {e}"


# ── TAKVİM & MAKRO FONKSİYONLARI ─────────────────────────────────────────────

# FOMC sabit tarihleri (FED yıllık önceden açıklar)
_FOMC_TARIHLERI = [
    ("2026-01-28", "2026-01-29"), ("2026-03-18", "2026-03-19"),
    ("2026-05-06", "2026-05-07"), ("2026-06-17", "2026-06-18"),
    ("2026-07-28", "2026-07-29"), ("2026-09-16", "2026-09-17"),
    ("2026-11-04", "2026-11-05"), ("2026-12-15", "2026-12-16"),
    ("2027-01-27", "2027-01-28"), ("2027-03-17", "2027-03-18"),
    ("2027-05-05", "2027-05-06"), ("2027-06-16", "2027-06-17"),
    ("2027-07-27", "2027-07-28"), ("2027-09-15", "2027-09-16"),
    ("2027-11-03", "2027-11-04"), ("2027-12-14", "2027-12-15"),
]

_PORTFOY_TICKERS = {"MO","JNJ","T","VZ","PM","SM","KOS","XLE","RGLD","FCX"}
_MEGACAP_TICKERS = {
    "AAPL","MSFT","NVDA","AMZN","GOOGL","GOOG","META","TSLA","JPM","V",
    "UNH","XOM","LLY","MA","AVGO","HD","PG","MRK","COST","ABBV","BAC",
    "KO","WMT","CVX","CRM","AMD","NFLX","TMO","PLTR","BKNG","BX","GS",
    "MS","C","WFC","UBER","DIS","SBUX","INTC","QCOM","TXN","MU","SNOW",
    "ORCL","IBM","COP","SLB","EOG","RTX","CAT","DE","BA","HON","GE",
}
_TUM_TICKERS = _PORTFOY_TICKERS | _MEGACAP_TICKERS

_MAKRO_ONCELIK = [
    "Nonfarm Payroll","Non-Farm Payroll","CPI","Consumer Price Index",
    "Core CPI","PCE Price","Core PCE","GDP","Gross Domestic Product",
    "Unemployment Rate","Initial Jobless","PPI","Producer Price",
    "Retail Sales","ISM Manufacturing PMI","ISM Services PMI",
    "ISM Non-Manufacturing PMI","JOLTs","JOLTS","Michigan Consumer",
    "ADP Employment","Federal Funds","Interest Rate Decision",
]
_MAKRO_DISI = ["CFTC","Baker Hughes","Mortgage","MBA ","API Crude",
               "EIA Crude","Natural Gas","Redbook","Challenger","speculative"]


def _parse_ical_date(value: str):
    from datetime import timezone as _tz, timedelta as _td
    value = value.strip()
    try:
        if len(value) == 8:
            return datetime(int(value[:4]),int(value[4:6]),int(value[6:8])).date()
        if value.endswith("Z"):
            dt = datetime.strptime(value,"%Y%m%dT%H%M%SZ")
            dt = dt.replace(tzinfo=_tz.utc)
            tr = dt + _td(hours=3)
            return tr
        if "T" in value:
            return datetime.strptime(value,"%Y%m%dT%H%M%S")
    except Exception:
        pass
    return None


def format_takvim(hedef: str = "yarın") -> str:
    """Google Calendar iCal -> yarın/bugün etkinlikleri."""
    import re as _re
    from datetime import date as _d, timedelta as _td
    ical_urls_raw  = os.environ.get("GCAL_ICAL_URLS","")
    ical_names_raw = os.environ.get("GCAL_ICAL_NAMES","Ana Takvim")
    if not ical_urls_raw:
        return "⚠️ GCAL_ICAL_URLS tanımlanmamış. Railway env değişkenlerine ekle."
    urls  = [u.strip() for u in ical_urls_raw.split(",") if u.strip()]
    names = [n.strip() for n in ical_names_raw.split(",") if n.strip()]
    while len(names) < len(urls):
        names.append(f"Takvim {len(names)+1}")
    bugun = _d.today()
    if hedef.lower().strip() in ("bugün","bugun","today"):
        hedef_tarih, etiket = bugun, "BUGÜN"
    else:
        hedef_tarih, etiket = bugun + _td(days=1), "YARIN"
    etkinlikler = []
    for takvim_adi, url in zip(names, urls):
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent":"FinzoraBot/1.0"})
            resp.raise_for_status()
            for block in resp.text.split("BEGIN:VEVENT")[1:]:
                end_idx = block.find("END:VEVENT")
                if end_idx > 0: block = block[:end_idx]
                m = _re.search(r"SUMMARY[^:]*:(.+)", block)
                summary = m.group(1).strip().replace("\\n"," ").replace("\\,",",") if m else "İsimsiz"
                m = _re.search(r"DTSTART(?:;[^:]*)?:(\S+)", block)
                if not m: continue
                dt_val = _parse_ical_date(m.group(1))
                if dt_val is None: continue
                if isinstance(dt_val, _d) and not isinstance(dt_val, datetime):
                    event_date, event_time = dt_val, "Tüm gün"
                elif isinstance(dt_val, datetime):
                    event_date, event_time = dt_val.date(), dt_val.strftime("%H:%M")
                else: continue
                if event_date != hedef_tarih: continue
                etkinlikler.append({"baslik":summary,"saat":event_time,"takvim":takvim_adi})
        except Exception as e:
            etkinlikler.append({"baslik":f"⚠️ {takvim_adi}: {e}","saat":"","takvim":""})
    etkinlikler.sort(key=lambda x: x["saat"] if x["saat"] not in ("","Tüm gün") else "00:00")
    gun_adlari = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    aylar = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"]
    tarih_str = f"{gun_adlari[hedef_tarih.weekday()]} {hedef_tarih.day} {aylar[hedef_tarih.month-1]}"
    if not etkinlikler:
        return f"📅 <b>TAKVİM — {etiket}</b>\n<i>{tarih_str}</i>\n\n✅ Etkinlik yok."
    lines = [f"📅 <b>TAKVİM — {etiket}</b>",f"<i>{tarih_str} • {len(etkinlikler)} etkinlik</i>",""]
    for i, ev in enumerate(etkinlikler, 1):
        saat_str = f" {ev['saat']}" if ev["saat"] and ev["saat"] != "Tüm gün" else " 📆"
        lines.append(f"<b>{i}. {ev['baslik']}</b>{saat_str}")
        if ev["takvim"]: lines.append(f"   📂 {ev['takvim']}")
    lines.append("\n<i>finzora ai • takvim</i>")
    return "\n".join(lines)


def format_makro(gun: int = 7) -> str:
    """FMP -> Bu haftanin ABD yuksek etkili makro olaylari."""
    from datetime import date as _d, timedelta as _td
    bugun = _d.today()
    bitis = bugun + _td(days=gun)
    try:
        r = requests.get(f"{FMP_BASE}/economic-calendar",
                         params={"from":bugun.isoformat(),"to":bitis.isoformat(),"apikey":FMP_KEY},
                         timeout=12)
        data = r.json()
    except Exception as e:
        return f"❌ FMP makro takvim hatası: {e}"
    events = []
    for ev in (data if isinstance(data,list) else []):
        if ev.get("country") != "US": continue
        name = ev.get("event","")
        if any(k.lower() in name.lower() for k in _MAKRO_DISI): continue
        if ev.get("impact") != "High": continue
        if not any(k.lower() in name.lower() for k in _MAKRO_ONCELIK): continue
        raw_date = ev.get("date","")
        try:
            dt_utc = datetime.strptime(raw_date,"%Y-%m-%d %H:%M:%S")
            tr_hour = (dt_utc.hour + 3) % 24
            saat_str = f"{tr_hour:02d}:{dt_utc.minute:02d}"
            event_date = dt_utc.date() if dt_utc.hour + 3 < 24 else (dt_utc + __import__("datetime").timedelta(days=1)).date()
        except Exception:
            try: event_date = _d.fromisoformat(raw_date[:10]); saat_str = ""
            except: continue
        onceki = ev.get("previous"); tahmin = ev.get("estimate"); gercek = ev.get("actual")
        def _v(val): return "—" if val is None else str(val)
        detay = f"Önceki: {_v(onceki)}"
        if tahmin is not None: detay += f" | Tahmin: {_v(tahmin)}"
        if gercek is not None: detay += f" | <b>Gerçek: {_v(gercek)}</b>"
        events.append({"tarih":event_date,"saat":saat_str,"baslik":name,"detay":detay})
    events.sort(key=lambda x: (x["tarih"],x["saat"]))
    if not events:
        return f"📊 <b>Makro Takvim ({gun} gün)</b>\n\nBu dönemde yüksek etkili ABD olayı bulunamadı."
    gun_adlari = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"]
    lines = [f"📊 <b>Makro Takvim — Sonraki {gun} Gün</b>","<i>ABD • Yüksek Etki • Türkiye saatiyle</i>",""]
    son_tarih = None
    for ev in events:
        if ev["tarih"] != son_tarih:
            son_tarih = ev["tarih"]
            lines.append(f"\n<b>📅 {gun_adlari[ev['tarih'].weekday()]} {ev['tarih'].strftime('%d.%m')}</b>")
        saat = f" <code>{ev['saat']}</code>" if ev["saat"] else ""
        lines.append(f"  • {ev['baslik']}{saat}")
        lines.append(f"    {ev['detay']}")
    lines.append("\n<i>finzora ai • makro takvim</i>")
    return "\n".join(lines)


def format_fomc() -> str:
    """Sonraki FOMC toplantisi."""
    from datetime import date as _d
    bugun = _d.today()
    sonraki = None
    for basl_str, karar_str in _FOMC_TARIHLERI:
        karar = _d.fromisoformat(karar_str)
        if karar >= bugun:
            sonraki = (_d.fromisoformat(basl_str), karar)
            break
    if not sonraki:
        return "🏦 <b>FOMC</b>\n\nBilinen tarih kalmadı."
    basl, karar = sonraki
    kalan = (basl - bugun).days
    aylar = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
    aciliyor = f"{basl.day} {aylar[basl.month-1]} {basl.year}"
    karar_str2 = f"{karar.day} {aylar[karar.month-1]} {karar.year}"
    if kalan == 0: durum = "🟢 Bugün başlıyor!"
    elif kalan < 0 and (karar - bugun).days >= 0: durum = "🔴 Devam ediyor — karar bugün!"
    else: durum = f"⏳ <b>{kalan} gün kaldı</b>"
    return (f"🏦 <b>Sonraki FOMC Toplantısı</b>\n\n"
            f"📅 Başlangıç  : <b>{aciliyor}</b>\n"
            f"⚖️ Karar günü : <b>{karar_str2}</b> — 21:00 TR\n\n"
            f"{durum}\n\n"
            f"<i>Kararlar karar günü 21:00 TR'de açıklanır.</i>\n"
            f"<i>finzora ai • FOMC takvimi</i>")


def format_kazanc(gun: int = 14) -> str:
    """Onumuzdeki 14 gunde portfoy + mega-cap bilancolar."""
    from datetime import date as _d, timedelta as _td
    bugun = _d.today()
    bitis = bugun + _td(days=gun)
    try:
        r = requests.get(f"{FMP_BASE}/earnings-calendar",
                         params={"from":bugun.isoformat(),"to":bitis.isoformat(),"apikey":FMP_KEY},
                         timeout=12)
        data = r.json()
    except Exception as e:
        return f"❌ FMP earnings hatası: {e}"
    events = []
    for ev in (data if isinstance(data,list) else []):
        sym = ev.get("symbol","")
        if sym not in _TUM_TICKERS: continue
        try: event_date = _d.fromisoformat(ev.get("date","")[:10])
        except: continue
        eps_e = ev.get("epsEstimated"); eps_a = ev.get("epsActual"); rev_e = ev.get("revenueEstimated")
        is_pf = sym in _PORTFOY_TICKERS
        detay_parts = []
        if eps_e is not None: detay_parts.append(f"EPS Tahmin: ${eps_e:.2f}")
        if eps_a is not None: detay_parts.append(f"EPS Gerçek: ${eps_a:.2f}")
        if rev_e and rev_e > 0:
            detay_parts.append(f"Gelir: ${'%.1fB' % (rev_e/1e9) if rev_e >= 1e9 else '%.0fM' % (rev_e/1e6)}")
        events.append({"tarih":event_date,"sembol":sym,"emoji":"⭐" if is_pf else "📊",
                       "is_pf":is_pf,"detay":" | ".join(detay_parts) or "Tahmin henüz yok"})
    events.sort(key=lambda x: (x["tarih"], not x["is_pf"], x["sembol"]))
    if not events:
        return f"📊 <b>Bilanço Takvimi</b>\n\nÖnümüzdeki {gun} günde izleme listesinde bilanço yok."
    gun_adlari = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"]
    lines = [f"📊 <b>Bilanço Takvimi — {gun} Gün</b>","<i>⭐ = Portföyde  📊 = İzleme listesi</i>",""]
    son_tarih = None
    for ev in events:
        if ev["tarih"] != son_tarih:
            son_tarih = ev["tarih"]
            lines.append(f"\n<b>📅 {gun_adlari[ev['tarih'].weekday()]} {ev['tarih'].strftime('%d.%m')}</b>")
        lines.append(f"  {ev['emoji']} <b>{ev['sembol']}</b> — {ev['detay']}")
    lines.append("\n<i>finzora ai • bilanço takvimi</i>")
    return "\n".join(lines)


def format_fiyat(ticker: str) -> str:
    """Canlı fiyat."""
    try:
        r = requests.get(f"{FMP_BASE}/quote",
                         params={"symbol": ticker, "apikey": FMP_KEY},
                         timeout=8).json()
        if not r or not isinstance(r, list):
            return f"❌ {ticker} bulunamadı"
        q = r[0]
        price = float(q.get("price", 0) or 0)
        prev  = float(q.get("previousClose", 0) or 0)
        chg   = ((price - prev) / prev * 100) if prev else 0
        ico   = "🟢" if chg >= 0 else "🔴"
        mcap  = float(q.get("marketCap", 0) or 0)
        vol   = float(q.get("volume", 0) or 0)
        return (
            f"{ico} <b>{ticker}</b>\n\n"
            f"Fiyat: <b>${price:.2f}</b> ({chg:+.2f}%)\n"
            f"Önceki kapanış: ${prev:.2f}\n"
            f"Mkt cap: ${mcap/1e9:.1f}B\n"
            f"Hacim: {vol/1e6:.1f}M"
        )
    except Exception as e:
        return f"Fiyat okunamadı: {e}"


def claude_sor(soru: str) -> str:
    """Serbest Claude sorgusu — portföy bağlamında."""
    try:
        import sys as _s
        _s.path.insert(0, str(REPO_ROOT / "agent"))

        # Portföy bağlamını oku
        ctx_parts = []
        for pf in ["aggressive", "balanced", "dividend"]:
            try:
                d = json.load(open(REPO_ROOT / "data" / "portfolios" / f"{pf}.json"))
                syms = [p.get("sembol","?") for p in d.get("pozisyonlar", [])]
                ctx_parts.append(f"{pf}: {', '.join(syms)}")
            except Exception:
                pass
        try:
            sw = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
            swing_syms = [p.get("sembol","?") for p in sw.get("aktif_pozisyonlar", [])]
            ctx_parts.append(f"swing: {', '.join(swing_syms)}")
        except Exception:
            pass
        try:
            v = json.load(open(REPO_ROOT / "data" / "vix_cache.json"))
            ctx_parts.append(f"VIX: {v.get('value','?')}")
        except Exception:
            pass
        try:
            k = json.load(open(REPO_ROOT / "data" / "k13_crisis_matrix.json"))
            ctx_parts.append(f"Aktif kriz: {k.get('aktif_kriz','?')}")
        except Exception:
            pass

        ctx = "\n".join(ctx_parts)

        prompt = f"""Mevcut Finzora portföy bağlamı:
{ctx}

Zeynel'in sorusu: {soru}

Kurallar:
- Türkçe cevap ver, cümleler büyük harfle başlasın
- Kısa ve öz ol (max 6 cümle veya 3 madde)
- Em dash yok, AI kokusu olmasın
- Spekülatif/muhtemel/kesin ayrımını belirt
- Risk tarafını atlama"""

        from claude_agent import get_claude_decision
        # Haiku tier için explicit model — ucuz serbest sorular
        import os
        os.environ['CLAUDE_MODEL'] = os.environ.get('CLAUDE_MODEL_BOT', 'claude-haiku-4-5-20251001')

        yanit = get_claude_decision(prompt, mode="monitor", rag_enabled=False)
        # Telegram HTML — escape
        yanit = yanit.replace("<", "&lt;").replace(">", "&gt;")
        return f"🤖 <b>Claude</b>\n\n{yanit[:3500]}"
    except Exception as e:
        return f"Claude hatası: {e}"


def claude_analiz(ticker: str) -> str:
    """Tam ticker analizi — Opus (daha detaylı)."""
    try:
        import sys as _s
        _s.path.insert(0, str(REPO_ROOT / "agent"))

        # FMP'den profil + metrikleri topla
        def fmp(ep, p=None):
            pp = (p or {}); pp["apikey"] = FMP_KEY
            try:
                r = requests.get(f"{FMP_BASE}/{ep}", params=pp, timeout=8)
                return r.json()
            except Exception:
                return None

        prof = fmp("profile", {"symbol": ticker}) or []
        prof = prof[0] if prof else {}
        quote = fmp("quote", {"symbol": ticker}) or []
        quote = quote[0] if quote else {}
        ratios = fmp("ratios-ttm", {"symbol": ticker}) or []
        ratios = ratios[0] if ratios else {}
        metrics = fmp("key-metrics-ttm", {"symbol": ticker}) or []
        metrics = metrics[0] if metrics else {}

        if not prof:
            return f"❌ {ticker} FMP'de bulunamadı"

        veri = f"""Sembol: {ticker}
Şirket: {prof.get('companyName','?')}
Sektör: {prof.get('sector','?')}
Mkt cap: ${float(quote.get('marketCap',0) or 0)/1e9:.1f}B
Fiyat: ${float(quote.get('price',0) or 0):.2f}
P/E: {ratios.get('priceToEarningsRatioTTM','?')}
P/B: {ratios.get('priceToBookRatioTTM','?')}
D/E: {ratios.get('debtToEquityRatioTTM','?')}
ROE: {ratios.get('returnOnEquityTTM','?')}
FCF yield: {metrics.get('freeCashFlowYieldTTM','?')}
Div yield: {ratios.get('dividendYieldTTM','?')}"""

        # Mevcut portföy
        portfoyde_mi = False
        for pf in ["aggressive", "balanced", "dividend"]:
            try:
                d = json.load(open(REPO_ROOT / "data" / "portfolios" / f"{pf}.json"))
                if any(p.get("sembol") == ticker for p in d.get("pozisyonlar", [])):
                    portfoyde_mi = pf
                    break
            except Exception:
                pass

        prompt = f"""{ticker} için kapsamlı analiz yap:

{veri}

{'Portföyde var: ' + portfoyde_mi if portfoyde_mi else 'Portföyde yok.'}

İstenen format (Türkçe, kısa):
1. NEDEN BAKIYORUZ? — Tetikleyen sinyal (1-2 cümle)
2. VERİ DAYANAĞI — P/E, büyüme, FCF, ROIC metrikleri yorumu (3-4 satır)
3. BULL CASE — Tez (2-3 cümle)
4. BEAR CASE — Risk senaryosu (2-3 cümle)
5. PORTFÖY UYGUNLUĞU — Dengeli/Agresif/Temettü/Swing hangisi?
6. KESİN KARAR — AL / BEKLE / PAS / ÇIK (portföyde varsa)

Kurallar: Em dash yok, cümleler büyük harfle, spekülatif/muhtemel/kesin ayrımı belirt."""

        from claude_agent import get_claude_decision
        import os
        os.environ['CLAUDE_MODEL'] = os.environ.get('CLAUDE_MODEL_BOT_ANALIZ', 'claude-opus-4-7')

        yanit = get_claude_decision(prompt, mode="morning", rag_enabled=True)
        yanit = yanit.replace("<", "&lt;").replace(">", "&gt;")
        return f"🔬 <b>{ticker} Tam Analiz</b>\n\n{yanit[:3800]}"
    except Exception as e:
        return f"Analiz hatası: {e}"


# ── Rate Limit (chat bazlı, dakika penceresi) ─────────────────────────────────

_RATE_LIMIT_STATE: dict = {}  # chat_id -> [ts1, ts2, ...]
_RATE_LIMIT_MAX = 15
_RATE_LIMIT_WINDOW = 60  # saniye


def _rate_limit_check(chat_id: str) -> bool:
    """True dönerse geçebilir, False ise limit aşıldı."""
    import time as _t
    now = _t.time()
    timestamps = _RATE_LIMIT_STATE.get(chat_id, [])
    # Eski timestampleri temizle
    timestamps = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(timestamps) >= _RATE_LIMIT_MAX:
        _RATE_LIMIT_STATE[chat_id] = timestamps
        return False
    timestamps.append(now)
    _RATE_LIMIT_STATE[chat_id] = timestamps
    return True


# ── Mesaj İşleyici ────────────────────────────────────────────────────────────

def isle_mesaj(msg: dict):
    chat_id  = str(msg.get("chat", {}).get("id", ""))
    msg_id   = msg.get("message_id")
    text     = (msg.get("text") or "").strip()
    user     = msg.get("from", {}).get("first_name", "?")

    if not text or chat_id not in IZINLI_CHATLER:
        return

    # Rate limit (dakikada max 15 komut, chat bazlı)
    if not _rate_limit_check(chat_id):
        tg_send(chat_id, "⚠️ Rate limit — dakikada max 15 komut. Biraz bekle.", reply_to=msg_id)
        return

    print(f"[Bot] Mesaj [{chat_id}] {user}: {text[:50]}")

    text_upper = text.upper().strip()
    text_lower = text.lower().strip()

    # ── /yardim ──────────────────────────────────────────────────
    if text_lower in ("/yardim", "/help", "/start"):
        tg_send(chat_id, format_yardim(), reply_to=msg_id)
        return

    # ── /portfoy ─────────────────────────────────────────────────
    if text_lower in ("/portfoy", "/portfolio", "/portföy", "/pf"):
        tg_send(chat_id, format_portfoy(), reply_to=msg_id)
        return

    # ── /swing ────────────────────────────────────────────────────
    if text_lower in ("/swing", "/sw"):
        tg_send(chat_id, format_swing(), reply_to=msg_id)
        return

    # ── /takvim [bugün|yarın] ─────────────────────────────────────
    if text_lower.startswith("/takvim"):
        arg = text_lower.replace("/takvim", "").strip() or "yarın"
        tg_send(chat_id, "⏳ Takvim alınıyor...", reply_to=msg_id)
        tg_send(chat_id, format_takvim(arg), reply_to=msg_id)
        return

    # ── /makro ────────────────────────────────────────────────────
    if text_lower in ("/makro", "/macro"):
        tg_send(chat_id, "⏳ Makro takvim yükleniyor...", reply_to=msg_id)
        tg_send(chat_id, format_makro(), reply_to=msg_id)
        return

    # ── /fomc ─────────────────────────────────────────────────────
    if text_lower in ("/fomc", "/fed"):
        tg_send(chat_id, format_fomc(), reply_to=msg_id)
        return

    # ── /kazanc ───────────────────────────────────────────────────
    if text_lower in ("/kazanc", "/kazanç", "/earnings", "/bilanco", "/bilanço"):
        tg_send(chat_id, "⏳ Bilanço takvimi alınıyor...", reply_to=msg_id)
        tg_send(chat_id, format_kazanc(), reply_to=msg_id)
        return

    # ── /vix ──────────────────────────────────────────────────────
    if text_lower in ("/vix",):
        tg_send(chat_id, format_vix(), reply_to=msg_id)
        return

    # ── /kriz ─────────────────────────────────────────────────────
    if text_lower in ("/kriz", "/crisis"):
        tg_send(chat_id, format_kriz(), reply_to=msg_id)
        return

    # ── /stats ────────────────────────────────────────────────────
    if text_lower in ("/stats", "/istatistik"):
        tg_send(chat_id, format_stats(), reply_to=msg_id)
        return

    # ── /watchlist ────────────────────────────────────────────────
    if text_lower in ("/watchlist", "/izleme", "/iz"):
        tg_send(chat_id, format_watchlist(), reply_to=msg_id)
        return

    # ── /vstats — v5 valuation log özeti ──────────────────────────
    if text_lower in ("/vstats", "/valstats"):
        try:
            import sys as _s
            from pathlib import Path as _P
            agent_dir = str(_P(__file__).parent.parent / "agent")
            if agent_dir not in _s.path:
                _s.path.insert(0, agent_dir)
            from valuation.prediction_log import summary_stats
            s = summary_stats(days_back=30)
            if s.get("total", 0) == 0:
                tg_send(chat_id, "<b>v5 Valuation Log</b>\n\nHenüz kayıt yok. Bot /deger veya sabah tarama sonrası birikir.", reply_to=msg_id)
                return
            lines = [f"<b>v5 Valuation Log — son 30 gün</b>", ""]
            lines.append(f"Toplam: <b>{s['total']}</b> kayıt, <b>{s['unique_tickers']}</b> eşsiz ticker")
            lines.append(f"Ortalama güven: <b>{s.get('avg_confidence','?')}/100</b>")
            lines.append(f"Tarih aralığı: {s.get('date_range','?')}")
            lines.append("")
            lines.append("<b>Archetype dağılımı:</b>")
            for k, v in sorted(s.get("archetypes", {}).items(), key=lambda x: -x[1]):
                lines.append(f"  {k}: {v}")
            lines.append("")
            lines.append("<b>Karar dağılımı:</b>")
            for k, v in sorted(s.get("kararlar", {}).items(), key=lambda x: -x[1]):
                lines.append(f"  {k}: {v}")
            tg_send(chat_id, "\n".join(lines), reply_to=msg_id)
        except Exception as e:
            tg_send(chat_id, f"vstats hatası: {e}", reply_to=msg_id)
        return

    # ── /backtest — v5 backtest analizi (14+ gün eski) ────────────
    if text_lower in ("/backtest", "/bt"):
        try:
            import sys as _s
            from pathlib import Path as _P
            agent_dir = str(_P(__file__).parent.parent / "agent")
            if agent_dir not in _s.path:
                _s.path.insert(0, agent_dir)
            from valuation.backtest import analyze
            r = analyze(min_age_days=14)
            if r.get("error"):
                tg_send(chat_id, f"<b>Backtest</b>\n\n{r['error']}\n\n<i>Toplam kayıt: {r.get('total_predictions',0)}</i>", reply_to=msg_id)
                return
            o = r["overall"]
            lines = [
                f"<b>v5 Backtest — ≥14 gün eski tahminler</b>", "",
                f"Değerlendirilen: <b>{r['unique_tickers']}</b> ticker ({r['eligible']} kayıt / toplam {r['total_predictions']})",
                f"HIT RATE: <b>{o['hit_rate_pct']}%</b>",
                "",
                f"  HIT: {o['HIT']} | MISS: {o['MISS']} | NEUTRAL: {o['NEUTRAL']} | NO_SIGNAL: {o['NO_SIGNAL']}",
                "",
                "<b>Archetype hit rate:</b>",
            ]
            for a, v in sorted(r["by_archetype"].items(), key=lambda x: -(x[1].get("hit_rate") or 0)):
                hr = v["hit_rate"] if v["hit_rate"] is not None else "—"
                lines.append(f"  {a}: {hr}% ({v['HIT']}/{v['HIT']+v['MISS']})")
            lines.append("")
            lines.append("<b>Güven bazında:</b>")
            for c in ["high (≥75)", "med (50-74)", "low (<50)"]:
                if c not in r["by_confidence"]: continue
                v = r["by_confidence"][c]
                hr = v["hit_rate"] if v["hit_rate"] is not None else "—"
                lines.append(f"  {c}: {hr}% ({v['HIT']}/{v['HIT']+v['MISS']})")
            tg_send(chat_id, "\n".join(lines), reply_to=msg_id)
        except Exception as e:
            tg_send(chat_id, f"backtest hatası: {e}", reply_to=msg_id)
        return

    # ── /kapanan ──────────────────────────────────────────────────
    if text_lower in ("/kapanan", "/closed", "/kp"):
        tg_send(chat_id, format_kapanan(), reply_to=msg_id)
        return

    # ── /fiyat TICKER ─────────────────────────────────────────────
    if text_upper.startswith("/FIYAT ") or text_upper.startswith("/PRICE "):
        parts = text.split()
        if len(parts) >= 2:
            tg_send(chat_id, format_fiyat(parts[1].upper()), reply_to=msg_id)
            return

    # ── /env (sistem env teşhis - debug) ──────────────────────────
    if text_lower in ("/env", "/durum", "/health"):
        import sys as _sys
        env_check = []
        env_check.append("<b>🔧 Sistem Env Durumu</b>")
        env_check.append("")
        for var in ["TELEGRAM_TOKEN", "TELEGRAM_PRIVATE_CHAT", "FMP_API_KEY",
                    "ANTHROPIC_API_KEY", "CLAUDE_MODEL", "RAILWAY",
                    "RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_NAME",
                    "RAILWAY_SERVICE_NAME"]:
            v = os.environ.get(var, "")
            if not v:
                status = "❌ MISSING"
            elif var in ("ANTHROPIC_API_KEY", "FMP_API_KEY", "TELEGRAM_TOKEN"):
                # Maskeli göster (güvenlik)
                status = f"✅ SET ({v[:8]}...{v[-4:]}, len={len(v)})"
            else:
                status = f"✅ SET ({v[:50]})"
            env_check.append(f"<code>{var}</code>: {status}")
        env_check.append("")
        env_check.append(f"<b>Python:</b> {_sys.version.split()[0]}")
        env_check.append(f"<b>CWD:</b> <code>{os.getcwd()}</code>")
        env_check.append(f"<b>Bot zamanı:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # anthropic paketi yüklü mü
        try:
            import anthropic as _an
            env_check.append(f"<b>anthropic pkg:</b> ✅ v{_an.__version__}")
        except ImportError:
            env_check.append(f"<b>anthropic pkg:</b> ❌ KURULU DEĞİL")

        tg_send(chat_id, "\n".join(env_check), reply_to=msg_id)
        return

    # ── /sor <soru> (Claude serbest) ──────────────────────────────
    if text_lower.startswith("/sor ") or text_lower.startswith("/ask "):
        soru = text[5:].strip()
        if len(soru) < 3:
            tg_send(chat_id, "Soru kısa — örnek: /sor bugün NVDA için ne dersin?", reply_to=msg_id)
            return
        tg_send(chat_id, "🤔 Düşünüyorum...", reply_to=msg_id)
        tg_send(chat_id, claude_sor(soru), reply_to=msg_id)
        return

    # ── /analiz TICKER (Claude tam analiz) ────────────────────────
    if text_upper.startswith("/ANALIZ ") or text_upper.startswith("/ANALYZE "):
        parts = text.split()
        if len(parts) >= 2:
            tkr = parts[1].upper()
            tg_send(chat_id, f"🔍 <b>{tkr}</b> için tam analiz hazırlanıyor (30-60sn)...", reply_to=msg_id)
            tg_send(chat_id, claude_analiz(tkr), reply_to=msg_id)
            return

    # ── Ticker tespiti ────────────────────────────────────────────
    ticker = None
    detay_modu = False  # /detay ise telegram_full style kullan

    # "/detay AAPL" — uzun versiyon
    if text.upper().startswith("/DETAY ") or text.upper().startswith("/DETAIL "):
        parts = text.split()
        if len(parts) >= 2:
            ticker = parts[1].upper()
            detay_modu = True

    # "/deger AAPL" veya "/beklenti AAPL" — kısa versiyon
    elif text.upper().startswith("/DEGER ") or text.upper().startswith("/BEKLENTI "):
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
    mesaj   = format_adil_deger(ticker, res, analyst, detay=detay_modu)
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
    # ── Environment sağlık kontrolü (v6 ai_consultant için kritik) ──
    env_status = {
        "TELEGRAM_TOKEN": "SET" if os.environ.get("TELEGRAM_TOKEN") else "MISSING",
        "TELEGRAM_PRIVATE_CHAT": "SET" if os.environ.get("TELEGRAM_PRIVATE_CHAT") else "MISSING",
        "FMP_API_KEY": "SET" if os.environ.get("FMP_API_KEY") else "MISSING",
        "ANTHROPIC_API_KEY": "SET" if os.environ.get("ANTHROPIC_API_KEY") else "MISSING",
        "CLAUDE_MODEL": os.environ.get("CLAUDE_MODEL", "claude-opus-4-7 (default)"),
    }
    print(f"[Bot] === Environment kontrolü ===")
    for k, v in env_status.items():
        print(f"[Bot]   {k}: {v}")
    print(f"[Bot] ============================")

    if env_status["ANTHROPIC_API_KEY"] == "MISSING":
        print(f"[Bot] ⚠️  ANTHROPIC_API_KEY yok — /sor, /analiz, v6 AI consultation çalışmayacak")

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
