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
    Adil değer hesapla. Öncelik: v5 framework (archetype-routed).
    Fallback: eski v2 (adil_deger_calculator).
    """
    symbol = symbol.upper()

    # ── v5 framework ──────────────────────────────────────────────────
    if use_v5:
        try:
            agent_dir = str(REPO_ROOT / "agent")
            if agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
            from valuation.framework import valuate
            res = valuate(symbol, verbose=False)
            if res and not res.get("error"):
                res["_version"] = "v5"
                return res
            print(f"[Bot] v5 fail {symbol}: {res.get('error') if res else 'None'} — v2'ye düşüyor")
        except Exception as e:
            print(f"[Bot] v5 exception {symbol}: {e} — v2'ye düşüyor")

    # ── v2 fallback ──────────────────────────────────────────────────
    try:
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from adil_deger_calculator import hesapla
        r = hesapla(symbol, sessiz=True)
        if r:
            r["_version"] = "v2"
        return r
    except Exception as e:
        print(f"[Bot] Hesaplama hatası {symbol}: {e}")
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


def format_adil_deger(symbol: str, res: dict, analyst: dict) -> str:
    """Adil değer sonucu formatla. v5 ve v2 result'ları farklı şemaya sahip."""

    # ── v5 result ise framework'ün kendi formatter'ını kullan ────────
    if res.get("_version") == "v5":
        try:
            agent_dir = str(REPO_ROOT / "agent")
            if agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
            from valuation.framework import format_report
            return format_report(res, style="telegram")
        except Exception as e:
            # Formatter fail → v5 ham çıktısını elle formatla
            return _format_v5_fallback(symbol, res)

    # ── v2 legacy format (aşağıdaki orijinal kod) ────────────────────
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

<b>Örnek:</b>
  <code>MU</code> → Micron adil değer
  <code>/sor bugün enerji sektörü risk-on mu?</code>
  <code>/analiz POWL</code> → POWL tam tez

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
        p = REPO_ROOT / "data" / "watchlist.json"
        if not p.exists():
            return "📋 Watchlist henüz oluşturulmamış."
        d = json.load(open(p))
        adaylar = d.get("adaylar", d.get("izlenenler", []))[:10]
        if not adaylar:
            return "📋 Watchlist boş."
        lines = [f"<b>📋 Watchlist ({len(adaylar)})</b>", ""]
        for a in adaylar:
            sym = a.get("sembol", a.get("symbol", "?"))
            skor = a.get("skor", a.get("score", "?"))
            port = a.get("portfoy", a.get("portföy", "-"))
            neden = (a.get("neden", a.get("reason", "")) or "")[:60]
            lines.append(f"• <b>{sym}</b> ({port}) skor {skor}\n  {neden}")
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
