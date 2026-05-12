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

import os, sys, json, re, requests, time, threading
from datetime import datetime
from pathlib import Path
try:
    import pytz
except ImportError:
    pytz = None

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
    """
    Telegram GET. getUpdates long-poll (timeout=30) icin requests timeout 40s.
    Diğer endpointler icin 15s.
    """
    params = params or {}
    # Long-poll timeout > Telegram timeout
    poll_timeout = params.get("timeout", 0)
    req_timeout = max(15, poll_timeout + 10)
    try:
        r = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=req_timeout)
        return r.json()
    except requests.exceptions.ReadTimeout:
        # Long-poll'da read timeout normal — sessiz tut, scheduler'i bozmasin
        if poll_timeout > 0:
            return None
        print(f"[TG] GET {endpoint} timeout (req:{req_timeout}s)")
        return None
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

def adil_deger_hesapla(symbol: str, use_v5: bool = True, with_kimi: bool = True) -> dict | None:
    """
    Adil değer hesapla — v7 Hybrid Plus (framework + Kimi).

    Akış:
      1. valuation.framework.valuate() → mekanik fair value (sanity check)
      2. ai_consultant.consult_claude() → Kimi birincil karar (zenginleştirilmiş
         FMP context: forward estimates, stale-aware analyst targets, peer PE,
         earnings surprises, insider, price percentiles)
      3. Sonuç dict'inde HEM framework HEM Kimi alanları olur. Format'çı
         "kimi" alanı varsa zenginleştirilmiş çıktı verir.

    with_kimi=False → sadece framework (hızlı, ~2sn).
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
        if not res or res.get("error"):
            print(f"[Bot] v5 fail {symbol}: {res.get('error') if res else 'None'}")
            return None
        res["_version"] = "v5"

        # Kimi consult — Hybrid Plus
        if with_kimi:
            try:
                from valuation.ai_consultant import consult_claude
                kimi_result = consult_claude(res, verbose=False)
                if kimi_result and not kimi_result.get("_error"):
                    res["kimi"] = kimi_result  # alt anahtar olarak ekle
                    res["_version"] = "v7"
                else:
                    err = (kimi_result or {}).get("_error", "bilinmiyor")
                    print(f"[Bot] Kimi consult fail {symbol}: {err}")
                    res["kimi_error"] = err
            except Exception as e:
                print(f"[Bot] Kimi consult exception {symbol}: {e}")
                res["kimi_error"] = str(e)[:100]

        return res
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


def _format_kimi_block(kimi: dict) -> str:
    """v7 Kimi-led valuation çıktısını HTML blok olarak formatlar."""
    if not kimi or kimi.get("_error"):
        return ""

    fv = kimi.get("claude_fair_value")
    blended = kimi.get("blended_fair_value")
    blend_w = kimi.get("blend_weight", 0.70)
    conf = kimi.get("confidence", 0)
    cycle = kimi.get("cycle_phase", "?")
    etiket = kimi.get("tavsiye_etiket", "?")
    sanity = kimi.get("sanity_flag")

    rejim = kimi.get("rejim_degisikligi") or {}
    rejim_var = rejim.get("var_mi", False)
    rejim_aciklama = (rejim.get("aciklama") or "")[:140]

    senaryolar = kimi.get("scenarios") or {}

    fwd_y = (kimi.get("forward_pe_yorumu") or "")[:160]
    peer_y = (kimi.get("peer_yorumu") or "")[:160]
    stale_y = (kimi.get("stale_uyarisi") or "")[:160]
    insider_y = (kimi.get("insider_yorumu") or "")[:140]
    tavsiye = (kimi.get("tavsiye") or "")[:200]

    parts = ["", "<b>🤖 Kimi Değerlemesi (v7)</b>"]

    if fv is not None:
        parts.append(f"  Kimi FV: <b>${fv:.2f}</b> (güven {conf}/100)")
    if blended is not None:
        parts.append(
            f"  Karma FV: <b>${blended:.2f}</b>"
            f" (Kimi w={blend_w:.0%}, framework w={1-blend_w:.0%})"
        )
    if sanity:
        parts.append(f"  ⚠️ Sapma bayrağı: <code>{sanity}</code>")
    parts.append(f"  Cycle: <i>{cycle}</i> | Etiket: <b>{etiket}</b>")

    if rejim_var:
        parts.append(f"  🔄 Rejim değişikliği: {rejim.get('tip','?')} — {rejim_aciklama}")

    if senaryolar:
        parts.append("")
        parts.append("<b>Senaryolar:</b>")
        for k in ("bear", "base", "bull"):
            s = senaryolar.get(k, {})
            ic = {"bear": "🔴", "base": "🟡", "bull": "🟢"}[k]
            price = s.get("price", "?")
            thesis = (s.get("thesis", "") or "")[:140]
            try:
                price_str = f"${float(price):.2f}"
            except Exception:
                price_str = str(price)
            parts.append(f"  {ic} <b>{k.title()}</b> {price_str} — {thesis}")

    if fwd_y:    parts.append(f"\n📈 Forward: {fwd_y}")
    if peer_y:   parts.append(f"⚖️ Peer: {peer_y}")
    if stale_y:  parts.append(f"🗓 Stale: {stale_y}")
    if insider_y: parts.append(f"👤 Insider: {insider_y}")
    if tavsiye:  parts.append(f"\n💬 <i>{tavsiye}</i>")

    return "\n".join(parts)


def format_adil_deger(symbol: str, res: dict, analyst: dict, detay: bool = False) -> str:
    """Adil değer sonucu formatla. v5 (framework) ve v7 (framework+Kimi) destekler.
    detay=True → uzun versiyon (telegram_full), False → kısa (telegram)."""

    # ── v5/v7 framework result ise framework'ün kendi formatter'ını kullan ────
    if res.get("_version") in ("v5", "v7"):
        try:
            agent_dir = str(REPO_ROOT / "agent")
            if agent_dir not in sys.path:
                sys.path.insert(0, agent_dir)
            from valuation.framework import format_report
            style = "telegram_full" if detay else "telegram"
            base_report = format_report(res, style=style)
        except Exception:
            base_report = _format_v5_fallback(symbol, res)

        # v7 → Kimi blok'u ekle
        kimi = res.get("kimi") or {}
        kimi_block = _format_kimi_block(kimi) if kimi else ""

        if kimi_block:
            return base_report + "\n" + kimi_block
        if res.get("kimi_error"):
            return base_report + f"\n\n<i>⚠️ Kimi consult atlandı: {res['kimi_error'][:80]}</i>"
        return base_report

    # adil_deger_hesapla() artık her zaman v5/v7 döndürür.
    # Defensive: tanınmayan res şeması → kısa fallback.
    return f"<b>{symbol}</b> — beklenmedik veri formatı."


# ── ADİL DEĞER SKILL v5.0 ENTEGRASYONU (Etap 7) ─────────────────────────────

def run_adil_deger_skill_v5(ticker: str, full_mode: bool = False) -> dict | None:
    """
    Adil Değer Skill v5.0'ı subprocess ile çalıştırır.
    --commit flag ile çalışır: markdown + index.json + git push otomatik.
    
    Returns: skill çıktısı + index.json entry, ya da None (hata)
    """
    import subprocess
    
    repo_root = "/app" if os.path.exists("/app") else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    skill_path = os.path.join(repo_root, "skills", "adil-deger-9-yontem", "scripts", "adil_deger.py")
    
    if not os.path.exists(skill_path):
        return {"error": f"Skill bulunamadı: {skill_path}"}
    
    try:
        # Skill'i --commit ile çalıştır (180sn timeout - FMP yavaş olabilir)
        result = subprocess.run(
            ["python3", skill_path, ticker.upper(), "--commit"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=180,
        )
        
        if result.returncode != 0:
            return {"error": f"Skill hatası (exit {result.returncode}): {result.stderr[-500:] if result.stderr else result.stdout[-500:]}"}
        
        # index.json'dan son giriş oku
        today = datetime.now().strftime("%Y-%m-%d")
        index_path = os.path.join(repo_root, "data", "research", "index.json")
        
        if not os.path.exists(index_path):
            return {"error": "index.json oluşmadı"}
        
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        entry_id = f"{ticker.upper()}_ADIL_DEGER_{today}"
        entry = next((a for a in index_data.get("analizler", []) if a.get("id") == entry_id), None)
        
        if not entry:
            return {"error": f"Index'te giriş bulunamadı: {entry_id}"}
        
        # Markdown dosyasını da hazır oku (full mode için)
        md_path = os.path.join(repo_root, entry.get("dosya", ""))
        md_text = None
        if full_mode and os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                md_text = f.read()
        
        return {
            "entry": entry,
            "md_path": entry.get("dosya"),
            "md_text": md_text,
            "stdout_tail": result.stdout[-1000:] if result.stdout else "",
        }
    except subprocess.TimeoutExpired:
        return {"error": "Skill 180sn içinde tamamlanmadı (FMP yavaş veya analiz başarısız)"}
    except Exception as e:
        return {"error": f"Skill çalıştırma hatası: {type(e).__name__}: {e}"}


def format_v5_telegram_summary(entry: dict, github_url: str | None = None) -> str:
    """
    index.json entry'sinden Telegram için kısa HTML özet.
    """
    ticker = entry.get("ticker", "?")
    sirket = entry.get("sirket", "")
    karar = entry.get("karar", "—")
    karar_gerekce = entry.get("karar_gerekce", "")
    fiyat = entry.get("analiz_fiyati", 0)
    
    ad = entry.get("adil_deger", {})
    mod = ad.get("mod", "—")
    agirlikli = ad.get("agirlikli_adil_deger")
    confidence = ad.get("confidence", "ORTA")
    quality = ad.get("quality_premium", 1.0)
    ai_mega = ad.get("ai_mega_cap", False)
    
    on = entry.get("on_beklenti", {})
    bear = on.get("senaryo_ayi", {})
    base = on.get("senaryo_baz", {})
    bull = on.get("senaryo_boga", {})
    
    v5 = entry.get("v5_sinyaller", {})
    altman = v5.get("altman_z") or {}
    pio = v5.get("piotroski") or {}
    momentum = v5.get("upgrade_momentum") or {}
    cons_p = v5.get("konsantrasyon_urun") or {}
    fmp_dcf = v5.get("fmp_dcf_unlevered")
    live_pe = v5.get("canli_sektor_pe")
    wacc = v5.get("dinamik_wacc")
    
    proj = entry.get("projeksiyon") or {}
    norm_year = proj.get("normalizasyon_yili")
    profile_key = proj.get("profile_key")
    
    portfoy = entry.get("portfoy_onerisi", {})
    giris = entry.get("giris_plani", {})
    
    parts = []
    parts.append(f"<b>📊 {ticker} — Adil Değer v5.0</b>")
    if sirket:
        parts.append(f"<i>{sirket}</i>")
    parts.append("")
    parts.append(f"💰 <b>Fiyat:</b> ${fiyat:.2f}")
    if agirlikli:
        upside = (agirlikli - fiyat) / fiyat * 100 if fiyat else 0
        sign = "+" if upside >= 0 else ""
        parts.append(f"🎯 <b>Adil Değer:</b> ${agirlikli:.2f} ({sign}%{upside:.1f})")
    parts.append(f"🎲 <b>Mod:</b> {mod}  |  <b>Confidence:</b> {confidence}")
    if quality and quality > 1.05:
        parts.append(f"⭐ <b>Quality Premium:</b> {quality:.2f}x")
    if ai_mega:
        parts.append(f"🤖 <b>AI Mega-Cap aktif</b>")
    parts.append("")
    parts.append(f"<b>📈 Karar:</b> {karar}")
    if karar_gerekce:
        parts.append(f"<i>{karar_gerekce}</i>")
    parts.append("")
    
    # Senaryolar
    if bear and base and bull:
        parts.append("<b>🎭 Senaryolar:</b>")
        if bear.get("fiyat_hedef"):
            parts.append(f"  🐻 Bear:  ${bear['fiyat_hedef']:.2f} ({bear.get('getiri_pct', 0):+.1f}%)")
        if base.get("fiyat_hedef"):
            parts.append(f"  ⚖️ Baz:   ${base['fiyat_hedef']:.2f} ({base.get('getiri_pct', 0):+.1f}%)")
        if bull.get("fiyat_hedef"):
            parts.append(f"  🐂 Bull:  ${bull['fiyat_hedef']:.2f} ({bull.get('getiri_pct', 0):+.1f}%)")
        parts.append("")
    
    # v5 sinyaller
    parts.append("<b>🔍 v5 Sinyaller:</b>")
    if altman.get("value") is not None:
        parts.append(f"  🛡️ Altman Z: {altman['value']:.2f} {altman.get('emoji','')} {altman.get('label','')}")
    if pio.get("value") is not None:
        parts.append(f"  📋 Piotroski: {pio['value']}/9 {pio.get('emoji','')} {pio.get('label','')}")
    if momentum.get("label"):
        parts.append(f"  📊 Sentiment 6 ay: {momentum['label']}")
    if cons_p.get("label"):
        parts.append(f"  🎯 Ürün: {cons_p['label']}")
    if live_pe:
        parts.append(f"  🌐 Canlı sektör P/E: {live_pe:.1f}x")
    if wacc:
        parts.append(f"  💼 CAPM WACC: %{wacc:.2f}")
    if fmp_dcf is not None:
        parts.append(f"  📐 FMP DCF: ${fmp_dcf:.2f}")
    parts.append("")
    
    # Projeksiyon
    if norm_year and profile_key:
        years_to_wait = norm_year - datetime.now().year
        emoji = "🟢" if years_to_wait <= 2 else ("🟡" if years_to_wait <= 4 else "🟠")
        parts.append(f"<b>📅 Normalizasyon:</b> {emoji} {norm_year} ({years_to_wait} yıl)  |  Profil: <code>{profile_key}</code>")
        parts.append("")
    
    # Giriş planı
    if giris.get("stop_loss"):
        parts.append("<b>🚀 Giriş Planı:</b>")
        parts.append(f"  Stop: ${giris.get('stop_loss', 0):.2f}  |  H1: ${giris.get('hedef_1', 0):.2f}  |  H2: ${giris.get('hedef_2', 0):.2f}")
        parts.append("")
    
    # Portföy
    parts.append("<b>📁 Portföy Uygunluğu:</b>")
    parts.append(f"  Dengeli: {portfoy.get('dengeli', '—')}")
    parts.append(f"  Agresif: {portfoy.get('agresif', '—')}")
    parts.append(f"  Temettü: {portfoy.get('temettu', portfoy.get('temettü', '—'))}")
    parts.append("")
    
    # GitHub link
    if github_url:
        parts.append(f'<b>📄 Tam Rapor:</b> <a href="{github_url}">GitHub</a>')
    
    parts.append("")
    parts.append("<i>Tam rapor için: <code>/deger {} full</code></i>".format(ticker))
    parts.append("<i>finzora ai — Adil Değer Skill v5.0</i>")
    
    return "\n".join(parts)


def github_md_url(repo_path: str) -> str:
    """
    Repo içi göreceli markdown yolundan GitHub blob URL üret.
    """
    return f"https://github.com/zeynelgun-afk/portfolio-tracker/blob/main/{repo_path}"


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
  <code>/tema</code> — Bugünün dominant temaları (AI tespiti)
  <code>/havuz</code> — AI'nin son aday hisse havuzu + son kararlar
  <code>/risk</code> — Risk paneli (manuel üret + grup'a gönder)

<b>📡 Analist Takip:</b>
  <code>/analist TICKER</code> — Tek hissenin anlık analist sinyali
  <code>/analist watchlist</code> — İzlenen ticker'lar listesi
  <code>/analist status</code> — Son 24h sinyal özeti + sistem durumu
  <code>/analist tara</code> — Şimdi tüm watchlist için manuel tarama
  <code>/fiyat AAPL</code> — Canlı fiyat + değişim

<b>Adil Değer v5.0 (önerilen — 11 May 2026 sonrası):</b>
  <code>/deger AAPL</code> — Tam akış: 9 yöntem + v5 sinyaller + 5y projeksiyon → markdown + GitHub push (30-90sn)
  <code>/deger AAPL full</code> — Aynı + tam markdown raporu Telegram'a kopyalar
  → 12 bölümlü protokole uygun rapor: Bear/Bull/Wrong case otomatik, Altman+Piotroski, FMP DCF sanity, konsantrasyon, CAPM WACC, 5y P&amp;L+forward+normalizasyon yılı, portföy karar matrisi, giriş planı, izleme tetikleyicileri

<b>Hisse Analizi (eski v7/Kimi):</b>
  <code>AAPL</code> sadece — Framework + Kimi v7 (forward EPS, peer PE, senaryolar) ~30-50sn
  <code>/q AAPL</code> (alias: <code>/hizli</code>) — Sadece framework, ~2sn
  <code>/detay AAPL</code> — Uzun rapor + tüm metotlar
  <code>/beklenti AAPL</code> — Analist + EPS beklentileri

<b>Valuation v5 (archetype-routed):</b>
  <code>/vstats</code> — Son 30 gün kaydedilen değerleme özeti
  <code>/backtest</code> (<code>/bt</code>) — ≥14 gün eski tahminlerin hit rate'i
  <code>/sanity</code> [gün] — Kimi vs framework sapma raporu (default 30g)

<b>AI (Finzora):</b>
  <code>/finzora_sor &lt;soru&gt;</code> (alias: <code>/sor</code>, <code>/ask</code>) — Serbest soru (portföy bağlamında)
  <code>/analiz AAPL</code> — Tam tez + risk + portföy uygunluğu

<i>Yanıt süresi: statik 2-5sn, AI komutları 20-60sn</i>"""


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
            f"AI güveni: {guven}/10",
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


def format_tema() -> str:
    """Bugünün dominant temaları + aktif kriz tipi (Kimi tespiti)."""
    path = REPO_ROOT / "data" / "macro_intelligence.json"
    if not path.exists():
        return "🌊 Henüz tema tespiti yapılmadı (sabah 16:00'da çalışır)."
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return f"Tema verisi okunamadı: {e}"

    tarih = (d.get("tarih", "") or "")[:16]
    vix = d.get("vix", 0)
    mod = d.get("piyasa_modu", "?")
    temalar = d.get("dominant_temalar", []) or []
    kriz = d.get("aktif_kriz", {}) or {}
    kacin = d.get("kacınılacak", d.get("kaçınılacak", [])) or []
    yorum = (d.get("genel_yorum", "") or "")[:300]

    lines = [
        f"<b>🌊 Tema &amp; Piyasa Havası</b>",
        f"<i>Son güncelleme: {tarih}</i>",
        "",
        f"📊 Piyasa modu: <b>{mod}</b>",
        f"📉 VIX: <b>{vix:.1f}</b>",
        "",
    ]

    # Aktif kriz
    kriz_tip = kriz.get("tip", "yok")
    kriz_guven = kriz.get("guven", 0)
    if kriz_tip and kriz_tip not in ("yok", "belirsiz"):
        lines.append(f"⚠️ <b>Aktif kriz: {kriz_tip}</b> (güven: {kriz_guven}/10)")
        ben = kriz.get("beneficiary_sectors", [])
        sen = kriz.get("sensitive_sectors", [])
        if ben:
            lines.append(f"  ✅ Faydalanan: {', '.join(ben[:5])}")
        if sen:
            lines.append(f"  ❌ Zayıflayan: {', '.join(sen[:5])}")
        lines.append("")
    elif kriz_tip == "yok":
        lines.append("✅ Aktif kriz yok (normal risk-on)")
        lines.append("")
    else:
        lines.append(f"❓ Kriz: belirsiz (güven {kriz_guven}/10)")
        lines.append("")

    # Dominant temalar
    if temalar:
        lines.append("<b>🔥 Dominant temalar:</b>")
        for t in temalar[:5]:
            ad = t.get("tema_adi", "?")
            skor = t.get("güç_skoru", t.get("guc_skoru", "?"))
            neden = (t.get("neden", "") or "")[:80]
            hisse = t.get("önerilen_hisseler", t.get("onerilen_hisseler", [])) or []
            pf = t.get("portföy", t.get("portfoy", "?"))
            acil = t.get("aciliyet", "?")
            lines.append(f"  • <b>{ad}</b> ({skor}/10) [{pf}, {acil}]")
            if neden:
                lines.append(f"    💭 {neden}")
            if hisse:
                lines.append(f"    🎯 {' '.join('$'+h for h in hisse[:5])}")
        lines.append("")
    else:
        lines.append("ℹ️ Bugün için tema tespit edilmedi.")
        lines.append("")

    if kacin:
        lines.append(f"🚫 Kaçınılacak sektörler: {', '.join(kacin[:5])}")
        lines.append("")

    if yorum:
        lines.append(f"<i>💬 {yorum}</i>")

    return "\n".join(lines)


def format_sanity(gun: int = 30) -> str:
    """Son N gün Kimi-led valuation'lar — sanity_flag tetiklenenler.

    Çıktı: framework vs Kimi sapma listesi, her satırda gap %, etiket, tarih.
    """
    path = REPO_ROOT / "logs" / "kimi_valuations.jsonl"
    if not path.exists():
        return ("🔍 <b>Sanity Log</b>\n\nHenüz Kimi valuation kaydı yok.\n"
                "<i>İlk /deger TICKER çağrısında dolar.</i>")

    from datetime import datetime as _dt, timedelta as _td
    cutoff = _dt.utcnow() - _td(days=gun)

    kayitlar = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                ts = r.get("timestamp", "")
                try:
                    t = _dt.fromisoformat(ts.replace("Z", ""))
                    if t < cutoff:
                        continue
                except Exception:
                    continue
                kayitlar.append(r)
    except Exception as e:
        return f"Sanity log okunamadı: {e}"

    if not kayitlar:
        return f"🔍 <b>Sanity Log</b>\n\nSon {gun} günde kayıt yok."

    # Sapma % hesabı + sıralama (en büyük sapma üstte)
    for r in kayitlar:
        fw = r.get("framework_fv") or 0
        ki = r.get("kimi_fv") or 0
        if fw > 0:
            r["_gap_pct"] = abs(ki - fw) / fw * 100
        else:
            r["_gap_pct"] = 0
    kayitlar.sort(key=lambda x: x.get("_gap_pct", 0), reverse=True)

    flag_count = sum(1 for r in kayitlar if r.get("sanity_flag"))
    extreme = sum(1 for r in kayitlar
                  if (r.get("sanity_flag") or "").startswith("EXTREME"))
    large = sum(1 for r in kayitlar
                if (r.get("sanity_flag") or "").startswith("LARGE"))

    lines = [
        f"<b>🔍 Sanity Log — Son {gun} gün</b>",
        f"<i>Toplam Kimi consult: {len(kayitlar)}</i>",
        f"⚠️ Sapma bayrağı: <b>{flag_count}</b>"
        f" (🔴 EXTREME: {extreme}, 🟠 LARGE: {large})",
        "",
    ]

    # En büyük 12 sapma
    lines.append("<b>📊 En büyük sapmalar (framework vs Kimi):</b>")
    for r in kayitlar[:12]:
        sym = r.get("ticker", "?")
        gap = r.get("_gap_pct", 0)
        fw = r.get("framework_fv") or 0
        ki = r.get("kimi_fv") or 0
        bl = r.get("blended_fv") or 0
        flag = r.get("sanity_flag") or ""
        etiket = r.get("tavsiye_etiket", "?")
        ts = (r.get("timestamp", "") or "")[:10]
        rejim = "🔄" if r.get("rejim_var_mi") else "  "
        ico = "🔴" if flag.startswith("EXTREME") else (
            "🟠" if flag.startswith("LARGE") else "🟡")
        lines.append(
            f"{ico}{rejim}<b>{sym}</b> {gap:.0f}% sapma • "
            f"FV: fw=${fw:.0f} ki=${ki:.0f} → bl=${bl:.0f} • "
            f"<i>{etiket}</i> ({ts})"
        )

    if len(kayitlar) > 12:
        lines.append(f"<i>...{len(kayitlar)-12} kayıt daha</i>")

    # Etiket dağılımı
    from collections import Counter
    etiket_dag = Counter(r.get("tavsiye_etiket", "?") for r in kayitlar)
    lines.append("")
    lines.append("<b>🏷 Etiket dağılımı:</b>")
    for et, cnt in etiket_dag.most_common():
        lines.append(f"  {et}: {cnt}")

    # Rejim değişikliği tespit edilen tickerlar
    rejim_var = [r.get("ticker") for r in kayitlar if r.get("rejim_var_mi")]
    if rejim_var:
        lines.append("")
        lines.append(f"<b>🔄 Rejim değişikliği tespiti ({len(set(rejim_var))} hisse):</b>")
        lines.append("  " + ", ".join(sorted(set(rejim_var))[:15]))

    return "\n".join(lines)


def format_havuz() -> str:
    """Kimi'nin son seçtiği aday havuz + aktif kararlar."""
    ss_path = REPO_ROOT / "data" / "session_state.json"
    if not ss_path.exists():
        return "🎯 Henüz aday havuzu üretilmedi."
    try:
        d = json.load(open(ss_path, encoding="utf-8"))
    except Exception as e:
        return f"Aday havuz okunamadı: {e}"

    lines = ["<b>🎯 AI Aday Havuzu</b>", ""]

    # Buy list (sabah 16:00 morning'den)
    buy = d.get("buy_list", {}) or {}
    bl_tarih = (buy.get("tarih", "") or "")[:16]
    adaylar = buy.get("adaylar", []) or []
    bl_vix = buy.get("vix", 0)
    bl_mod = buy.get("piyasa_mod", buy.get("piyasa_modu", "?"))

    lines.append(f"<i>Sabah taraması: {bl_tarih}</i>")
    lines.append(f"VIX: {bl_vix:.1f} • Piyasa: {bl_mod}")
    lines.append("")

    if adaylar:
        lines.append(f"<b>📋 Aday hisseler ({len(adaylar)}):</b>")
        for a in adaylar[:15]:
            if isinstance(a, dict):
                sym = a.get("sembol", a.get("symbol", "?"))
                tema = a.get("tema", a.get("tema_adi", ""))
                pf = a.get("portfoy", a.get("portföy", ""))
                lines.append(f"  • ${sym}" + (f" [{tema}]" if tema else "") + (f" → {pf}" if pf else ""))
            else:
                lines.append(f"  • ${a}")
        lines.append("")
    else:
        lines.append("ℹ️ Bugün için aday hisse listesi boş.")
        lines.append("")

    # Son AI kararları (morning'in çıktısı)
    kararlar_blok = d.get("claude_kararlar", d.get("ai_kararlar", {})) or {}
    k_tarih = (kararlar_blok.get("tarih", "") or "")[:16]
    kararlar = kararlar_blok.get("kararlar", []) or []
    if kararlar:
        lines.append(f"<b>🤖 Son AI kararları ({k_tarih}):</b>")
        ico = {"EKLE": "🟢", "BÜYÜT": "🟢", "ÇIK": "🔴",
               "DÖNDÜR": "🔄", "STOP_GÜNCELLE": "⚙️", "İZLE": "👁"}
        for k in kararlar[:10]:
            tip = k.get("tip", "?")
            sym = k.get("sembol", "?")
            pf = k.get("portfoy", "?")
            pct = k.get("pct", 0) or 0
            neden = (k.get("neden", "") or "")[:80]
            lines.append(f"  {ico.get(tip,'•')} <b>{tip}</b> ${sym} ({pf}, %{pct})")
            if neden:
                lines.append(f"    💭 {neden}")
        lines.append("")

    # Zorunlu aksiyonlar (varsa)
    zorunlu = d.get("zorunlu_aksiyonlar", []) or []
    if zorunlu:
        lines.append(f"⚠️ <b>Bekleyen zorunlu aksiyon ({len(zorunlu)}):</b>")
        for z in zorunlu[:5]:
            if isinstance(z, dict):
                lines.append(f"  • {z.get('sembol','?')} → {z.get('aksiyon','?')}: {(z.get('neden','') or '')[:60]}")
            else:
                lines.append(f"  • {z}")

    return "\n".join(lines)


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


def format_takvim(hedef: str = "yarın") -> str:
    """Google Calendar iCal -> yarın/bugün etkinlikleri. RRULE (tekrarlayan) destekler."""
    from datetime import date as _d, timedelta as _td
    ical_urls_raw  = os.environ.get("GCAL_ICAL_URLS","")
    ical_names_raw = os.environ.get("GCAL_ICAL_NAMES","Ana Takvim")
    if not ical_urls_raw:
        return "⚠️ GCAL_ICAL_URLS tanımlanmamış. Railway env değişkenlerine ekle."
    try:
        from icalendar import Calendar as _Cal
        import recurring_ical_events as _rie
    except ImportError:
        return "⚠️ Eksik kütüphane: pip install icalendar recurring-ical-events"

    urls  = [u.strip() for u in ical_urls_raw.split(",") if u.strip()]
    names = [n.strip() for n in ical_names_raw.split(",") if n.strip()]
    while len(names) < len(urls):
        names.append(f"Takvim {len(names)+1}")

    bugun = _d.today()
    if hedef.lower().strip() in ("bugün","bugun","today"):
        hedef_tarih, etiket = bugun, "BUGÜN"
    else:
        hedef_tarih, etiket = bugun + _td(days=1), "YARIN"

    # recurring_ical_events naive datetime ister
    sorgu_bas = datetime(hedef_tarih.year, hedef_tarih.month, hedef_tarih.day, 0, 0, 0)
    sorgu_bit = datetime(hedef_tarih.year, hedef_tarih.month, hedef_tarih.day, 23, 59, 59)

    etkinlikler = []
    for takvim_adi, url in zip(names, urls):
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent":"FinzoraBot/1.0"})
            resp.raise_for_status()
            cal = _Cal.from_ical(resp.content)
            events = _rie.of(cal).between(sorgu_bas, sorgu_bit)
            for ev in events:
                summary = str(ev.get("SUMMARY","İsimsiz"))
                dtstart = ev.get("DTSTART")
                if dtstart is None: continue
                dt = dtstart.dt
                if hasattr(dt, "date"):
                    # datetime — timezone'u TR'ye çevir
                    try:
                        from datetime import timezone as _tz
                        if dt.tzinfo:
                            import pytz as _pytz2
                            tr = dt.astimezone(_pytz2.timezone("Europe/Istanbul"))
                            event_time = tr.strftime("%H:%M")
                        else:
                            event_time = dt.strftime("%H:%M")
                    except Exception:
                        event_time = "?"
                else:
                    event_time = "Tüm gün"
                etkinlikler.append({"baslik": summary, "saat": event_time, "takvim": takvim_adi})
        except Exception as e:
            etkinlikler.append({"baslik": f"⚠️ {takvim_adi}: {e}", "saat":"", "takvim":""})

    etkinlikler.sort(key=lambda x: x["saat"] if x["saat"] not in ("","Tüm gün") else "00:00")
    gun_adlari = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    aylar = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"]
    tarih_str = f"{gun_adlari[hedef_tarih.weekday()]} {hedef_tarih.day} {aylar[hedef_tarih.month-1]}"
    if not etkinlikler:
        return f"📅 <b>TAKVİM — {etiket}</b>\n<i>{tarih_str}</i>\n\n✅ Etkinlik yok."
    lines = [f"📅 <b>TAKVİM — {etiket}</b>",
             f"<i>{tarih_str} • {len(etkinlikler)} etkinlik</i>",""]
    for i, ev in enumerate(etkinlikler, 1):
        saat_str = f" {ev['saat']}" if ev["saat"] and ev["saat"] not in ("","Tüm gün") else " 📆"
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


def finzora_sor(soru: str) -> str:
    """Serbest AI sorgusu — portföy bağlamında. Kimi K2 (non-thinking) ile hızlı yanıt."""
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
        # Bot serbest sorular için ucuz/hızlı bir model. KIMI_MODEL_BOT env ile
        # override edilebilir; default Kimi K2 (thinking değil — cevap hızlı dönsün).
        import os
        os.environ['KIMI_MODEL'] = os.environ.get('KIMI_MODEL_BOT', 'moonshotai/kimi-k2-0905')

        yanit = get_claude_decision(prompt, mode="monitor", rag_enabled=False)
        # Telegram HTML — escape
        yanit = yanit.replace("<", "&lt;").replace(">", "&gt;")
        return f"🤖 <b>Finzora</b>\n\n{yanit[:3500]}"
    except Exception as e:
        return f"AI hatası: {e}"


# Geriye uyumluluk — eski isim hâlâ çağrılabilir (gerekirse harici scripts kullansın diye)
claude_sor = finzora_sor


def finzora_analiz(ticker: str) -> str:
    """Tam ticker analizi — Kimi K2 thinking ile derin analiz."""
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
        # /analiz için thinking modeli — derin analiz değer.
        os.environ['KIMI_MODEL'] = os.environ.get('KIMI_MODEL_BOT_ANALIZ', 'moonshotai/kimi-k2-thinking')

        yanit = get_claude_decision(prompt, mode="morning", rag_enabled=True)
        yanit = yanit.replace("<", "&lt;").replace(">", "&gt;")
        return f"🔬 <b>{ticker} Tam Analiz</b>\n\n{yanit[:3800]}"
    except Exception as e:
        return f"Analiz hatası: {e}"


# Geriye uyumluluk — eski fonksiyon adı
claude_analiz = finzora_analiz


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

    # ── /analist [TICKER|watchlist|status|tara|yardim] ─────────────
    # Analist Takip sistemi komutları (DM'lerin yanı sıra manuel sorgu)
    if text_lower.startswith("/analist"):
        arg = text_lower.replace("/analist", "").strip()
        try:
            from agent.analist_takip import (
                analyze_single_ticker_now,
                format_watchlist_summary,
                format_system_status,
                run_scan_now,
                format_analist_help,
            )
        except Exception as e:
            tg_send(chat_id, f"❌ Analist Takip modülü yüklenemedi: {e}", reply_to=msg_id)
            return

        if not arg or arg in ("yardim", "yardım", "help", "?"):
            tg_send(chat_id, format_analist_help(), reply_to=msg_id)
            return

        if arg in ("watchlist", "wl", "izleme"):
            tg_send(chat_id, "⏳ Watchlist alınıyor...", reply_to=msg_id)
            tg_send(chat_id, format_watchlist_summary(), reply_to=msg_id)
            return

        if arg in ("status", "durum", "sağlık", "saglik"):
            tg_send(chat_id, format_system_status(), reply_to=msg_id)
            return

        if arg in ("tara", "scan", "polling"):
            tg_send(chat_id, "⏳ Tarama başlatıldı (30-90sn)...", reply_to=msg_id)
            tg_send(chat_id, run_scan_now(), reply_to=msg_id)
            return

        # Aksi halde ticker olarak yorumla
        ticker = arg.upper().replace(" ", "").replace("$", "")
        if 1 <= len(ticker) <= 6 and (ticker.isalpha() or "." in ticker):
            tg_send(chat_id, f"⏳ <code>{ticker}</code> analist sinyali alınıyor...",
                    reply_to=msg_id)
            tg_send(chat_id, analyze_single_ticker_now(ticker), reply_to=msg_id)
        else:
            tg_send(chat_id, f"❌ Geçersiz argüman: <code>{arg}</code>\n\n"
                             f"<code>/analist yardim</code> ile komutları gör.",
                    reply_to=msg_id)
        return

    # ── /kriz ─────────────────────────────────────────────────────
    if text_lower in ("/kriz", "/crisis"):
        tg_send(chat_id, format_kriz(), reply_to=msg_id)
        return

    # ── /tema ─ AI'nin tespit ettiği bugünün dominant temaları ────
    if text_lower in ("/tema", "/themes", "/temalar"):
        tg_send(chat_id, format_tema(), reply_to=msg_id)
        return

    # ── /havuz ─ AI'nin son aday hisse havuzu + kararlar ──────────
    if text_lower in ("/havuz", "/aday", "/adaylar", "/buylist"):
        tg_send(chat_id, format_havuz(), reply_to=msg_id)
        return

    # ── /risk ─ Manuel risk panel üret + grup chat'e gönder ───────
    if text_lower in ("/risk", "/riskpanel", "/risk_panel"):
        tg_send(chat_id, "📊 Risk paneli üretiliyor (10-30sn)...", reply_to=msg_id)
        try:
            import subprocess as _sp
            from datetime import datetime as _dt
            gun = _dt.now().strftime("%Y-%m-%d")
            out_dir = REPO_ROOT / "outputs" / "risk_panel"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{gun}_manual.png"
            proc = _sp.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "risk_panel_generator.py"),
                 "--out", str(out_path)],
                capture_output=True, text=True, timeout=120,
                cwd=str(REPO_ROOT),
            )
            if proc.returncode == 0 and out_path.exists():
                with open(out_path, "rb") as f:
                    r = requests.post(
                        f"{API_BASE}/sendPhoto",
                        data={"chat_id": chat_id, "caption": f"📊 Risk Paneli (manuel) — {gun}"},
                        files={"photo": f},
                        timeout=60,
                    )
                if r.status_code != 200:
                    tg_send(chat_id, f"❌ Telegram gönderim hatası: HTTP {r.status_code}",
                            reply_to=msg_id)
            else:
                tg_send(chat_id,
                        f"❌ Üretim hatası (rc={proc.returncode}):\n<pre>{(proc.stderr or '')[:500]}</pre>",
                        reply_to=msg_id)
        except Exception as e:
            tg_send(chat_id, f"❌ Hata: {type(e).__name__}: {e}", reply_to=msg_id)
        return

    # ── /sanity ─ Kimi vs framework sapma raporu (son 30 gün) ─────
    if text_lower.startswith("/sanity"):
        # /sanity 7 → son 7 gün; default 30
        parts = text.split()
        gun = 30
        if len(parts) >= 2:
            try:
                gun = max(1, min(180, int(parts[1])))
            except ValueError:
                pass
        tg_send(chat_id, format_sanity(gun=gun), reply_to=msg_id)
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
        # Optional vars: env'de yoksa "default" gösterilir, ❌ değil
        OPTIONAL_VARS = {"KIMI_MODEL", "CLAUDE_MODEL"}
        # GH_TOKEN/PAT_TOKEN birincil/ikincil — biri yetiyor
        gh_primary = os.environ.get("GH_TOKEN", "")
        gh_secondary = os.environ.get("PAT_TOKEN", "")
        gh_present = bool(gh_primary or gh_secondary)

        for var in ["TELEGRAM_TOKEN", "TELEGRAM_PRIVATE_CHAT", "FMP_API_KEY",
                    "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
                    "GH_TOKEN", "PAT_TOKEN",
                    "KIMI_MODEL", "CLAUDE_MODEL", "RAILWAY",
                    "RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_NAME",
                    "RAILWAY_SERVICE_NAME"]:
            v = os.environ.get(var, "")
            if not v:
                if var in OPTIONAL_VARS:
                    # Default kullanılıyor — sorun değil
                    if var == "KIMI_MODEL":
                        status = "⚪ default (moonshotai/kimi-k2-thinking)"
                    elif var == "CLAUDE_MODEL":
                        status = "⚪ legacy (kullanılmıyor)"
                    else:
                        status = "⚪ default"
                elif var in ("GH_TOKEN", "PAT_TOKEN") and gh_present:
                    # Diğeri set ise OK
                    status = "⚪ diğeri set (yedek)"
                else:
                    status = "❌ MISSING"
            elif var in ("OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "FMP_API_KEY",
                         "TELEGRAM_TOKEN", "GH_TOKEN", "PAT_TOKEN"):
                # Maskeli göster (güvenlik)
                status = f"✅ SET ({v[:8]}...{v[-4:]}, len={len(v)})"
            else:
                status = f"✅ SET ({v[:50]})"
            env_check.append(f"<code>{var}</code>: {status}")
        # Workflow tetikleyici özet — kullanıcı kritik bilgi
        env_check.append("")
        if gh_present:
            env_check.append("🟢 <b>Workflow tetikleyici:</b> Aktif (cron'lar Railway'den GitHub'a gidiyor)")
        else:
            env_check.append("🔴 <b>Workflow tetikleyici:</b> KIRIK — GH_TOKEN/PAT_TOKEN yok!")
            env_check.append("   Sabah 14:00 tarama, 16:00 morning, monitor, closing → tetiklenmiyor.")
        env_check.append("")
        env_check.append(f"<b>Python:</b> {_sys.version.split()[0]}")
        env_check.append(f"<b>CWD:</b> <code>{os.getcwd()}</code>")
        env_check.append(f"<b>Bot zamanı:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # openai paketi yüklü mü (OpenRouter / Kimi için)
        try:
            import openai as _oa
            env_check.append(f"<b>openai pkg:</b> ✅ v{_oa.__version__}")
        except ImportError:
            env_check.append(f"<b>openai pkg:</b> ❌ KURULU DEĞİL")

        tg_send(chat_id, "\n".join(env_check), reply_to=msg_id)
        return

    # ── /finzora_sor | /sor | /ask (AI serbest soru) ──────────────
    if (text_lower.startswith("/finzora_sor ") or
        text_lower.startswith("/sor ") or
        text_lower.startswith("/ask ")):
        # Komut prefix'inin uzunlugu degisken — boslugun konumundan ayir
        soru = text.split(" ", 1)[1].strip() if " " in text else ""
        if len(soru) < 3:
            tg_send(chat_id,
                    "Soru kısa — örnek: <code>/finzora_sor bugün NVDA için ne dersin?</code>",
                    reply_to=msg_id)
            return
        tg_send(chat_id, "🤔 Düşünüyorum...", reply_to=msg_id)
        tg_send(chat_id, finzora_sor(soru), reply_to=msg_id)
        return

    # ── /analiz TICKER (AI tam analiz) ────────────────────────────
    if text_upper.startswith("/ANALIZ ") or text_upper.startswith("/ANALYZE "):
        parts = text.split()
        if len(parts) >= 2:
            tkr = parts[1].upper()
            tg_send(chat_id, f"🔍 <b>{tkr}</b> için tam analiz hazırlanıyor (30-60sn)...", reply_to=msg_id)
            tg_send(chat_id, finzora_analiz(tkr), reply_to=msg_id)
            return

    # ── Ticker tespiti ────────────────────────────────────────────
    ticker = None
    detay_modu = False   # /detay ise telegram_full style kullan
    hizli_modu = False   # /q veya /hizli → sadece framework, Kimi olmadan

    # "/detay AAPL" — uzun versiyon (Kimi dahil)
    if text.upper().startswith("/DETAY ") or text.upper().startswith("/DETAIL "):
        parts = text.split()
        if len(parts) >= 2:
            ticker = parts[1].upper()
            detay_modu = True

    # "/q AAPL" veya "/hizli AAPL" — sadece framework, Kimi yok (~2sn)
    elif text.upper().startswith("/Q ") or text.upper().startswith("/HIZLI ") or text.upper().startswith("/QUICK "):
        parts = text.split()
        if len(parts) >= 2:
            ticker = parts[1].upper()
            hizli_modu = True

    # "/deger AAPL" veya "/deger AAPL full" → v5.0 SKILL (Etap 7, 2026-05-11)
    # /commit ile rapor + index.json + git push otomatik
    elif text.upper().startswith("/DEGER ") or text.upper().startswith("/BEKLENTI "):
        parts = text.split()
        if len(parts) >= 2:
            tkr = parts[1].upper()
            full_mode = (len(parts) >= 3 and parts[2].lower() in ("full", "tam", "detay"))
            
            tg_send(chat_id,
                    f"⏳ <b>{tkr}</b> Adil Değer v5.0 hesaplanıyor...\n"
                    f"<i>FMP veri → 9 yöntem + v5 sinyaller + 5y projeksiyon → markdown rapor → GitHub push (30-90sn)</i>",
                    reply_to=msg_id)
            
            res = run_adil_deger_skill_v5(tkr, full_mode=full_mode)
            
            if not res or res.get("error"):
                tg_send(chat_id,
                        f"❌ <b>{tkr}</b> için skill çalıştırılamadı.\n"
                        f"<code>{(res or {}).get('error', 'bilinmeyen hata')}</code>",
                        reply_to=msg_id)
                return
            
            entry = res["entry"]
            md_path = res.get("md_path")
            url = github_md_url(md_path) if md_path else None
            
            # Kısa özet
            summary = format_v5_telegram_summary(entry, github_url=url)
            tg_send(chat_id, summary, reply_to=msg_id)
            
            # Full mode: tam markdown'ı parça parça da gönder (4000 karakter sınırı)
            if full_mode and res.get("md_text"):
                md = res["md_text"]
                # HTML escape değil, sadece markdown olarak Telegram'da düz metin yolla
                # Telegram 4096 karakter sınırı
                CHUNK = 3800
                tg_send(chat_id, f"📄 <b>{tkr} - Tam Markdown Rapor:</b>", reply_to=msg_id)
                for i in range(0, len(md), CHUNK):
                    chunk = md[i:i+CHUNK]
                    # Basit HTML escape
                    chunk_safe = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    tg_send(chat_id, f"<pre>{chunk_safe}</pre>", parse_mode="HTML")
            
            print(f"[Bot] /deger {tkr} v5.0 yanıtı gönderildi → {chat_id} (full={full_mode})")
            return  # Eski adil_deger_hesapla path'ini bypass

    # "/deger AAPL" eskiden — Kimi-led (~30-50sn) — ARTIK kullanılmıyor, v5'e taşındı
    # Aşağıdaki blok eski uyum için duruyor, tetiklenmez:

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
    if hizli_modu:
        tg_send(chat_id, f"⚡ <b>{ticker}</b> hızlı (sadece framework)...", reply_to=msg_id)
    else:
        tg_send(chat_id,
                f"⏳ <b>{ticker}</b> Kimi derin analiz (30-50sn)...\n"
                f"<i>Hızlı için: /q {ticker}</i>",
                reply_to=msg_id)

    res = adil_deger_hesapla(ticker, with_kimi=not hizli_modu)
    if not res:
        tg_send(chat_id,
                f"❌ <b>{ticker}</b> için veri bulunamadı.\nTicker doğru mu? (NYSE/NASDAQ sembolü girin)",
                reply_to=msg_id)
        return

    analyst = get_analyst_data(ticker)
    mesaj   = format_adil_deger(ticker, res, analyst, detay=detay_modu)
    tg_send(chat_id, mesaj, reply_to=msg_id)
    print(f"[Bot] {ticker} yanıtı gönderildi → {chat_id} (kimi={not hizli_modu})")


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
    # ── Environment sağlık kontrolü (LLM çağrıları için kritik) ──
    env_status = {
        "TELEGRAM_TOKEN": "SET" if os.environ.get("TELEGRAM_TOKEN") else "MISSING",
        "TELEGRAM_PRIVATE_CHAT": "SET" if os.environ.get("TELEGRAM_PRIVATE_CHAT") else "MISSING",
        "FMP_API_KEY": "SET" if os.environ.get("FMP_API_KEY") else "MISSING",
        "OPENROUTER_API_KEY": "SET" if os.environ.get("OPENROUTER_API_KEY") else "MISSING",
        "ANTHROPIC_API_KEY": "SET" if os.environ.get("ANTHROPIC_API_KEY") else "MISSING (legacy fallback)",
        "KIMI_MODEL": os.environ.get("KIMI_MODEL", "moonshotai/kimi-k2-thinking (default)"),
    }
    print(f"[Bot] === Environment kontrolü ===")
    for k, v in env_status.items():
        print(f"[Bot]   {k}: {v}")
    print(f"[Bot] ============================")

    # LLM ulaşılabilir mi: OPENROUTER veya legacy ANTHROPIC en az biri lazım
    if env_status["OPENROUTER_API_KEY"] == "MISSING" and \
       env_status["ANTHROPIC_API_KEY"].startswith("MISSING"):
        print(f"[Bot] ⚠️  OPENROUTER_API_KEY yok (ANTHROPIC fallback'i de yok) — "
              f"/sor, /analiz, v6 AI consultation çalışmayacak")

    railway_mode = os.environ.get("RAILWAY") or os.environ.get("RAILWAY_ENVIRONMENT")

    if railway_mode:
        # ── Railway: Sürekli polling ──────────────────────────────
        print(f"[Bot] Railway modu — sürekli polling başlıyor")
        print(f"[Bot] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # ── Dahili Günlük Zamanlayıcı ─────────────────────────────
        # GitHub Actions schedule güvenilmez — Railway 7/24 çalıştığı için
        # takvim bildirimini buradan gönderiyoruz. Hedef: 08:30 TR
        # pytz & threading üstte import edildi

        _TR_TZ = pytz.timezone("Europe/Istanbul")
        _zamanlayi_durum = {"son_tarih": None}  # aynı gün iki kez göndermesin

        def _gunluk_bildirim():
            """Her 60sn bir zamanı kontrol et, 08:30 TR olunca takvim bildirimini gönder."""
            while True:
                try:
                    simdi_tr = datetime.now(_TR_TZ)
                    bugun    = simdi_tr.date()
                    saat     = simdi_tr.hour
                    dakika   = simdi_tr.minute

                    # 08:30 - 08:34 arasında, bugün henüz gönderilmemişse
                    if (saat == 8 and 30 <= dakika <= 34
                            and _zamanlayi_durum["son_tarih"] != bugun):

                        _zamanlayi_durum["son_tarih"] = bugun
                        print(f"[Zamanlayıcı] Takvim bildirimi gönderiliyor — {simdi_tr.strftime('%H:%M TR')}")

                        try:
                            mesaj = format_takvim("yarın")
                            tg_send(PRIVATE_CHAT, mesaj)
                            print(f"[Zamanlayıcı] ✅ Gönderildi.")
                        except Exception as e:
                            print(f"[Zamanlayıcı] ❌ Hata: {e}")

                except Exception as e:
                    print(f"[Zamanlayıcı] Döngü hatası: {e}")

                time.sleep(60)  # Her dakika kontrol et

        _t = threading.Thread(target=_gunluk_bildirim, daemon=True, name="GunlukZamanlayici")
        _t.start()
        print(f"[Bot] Günlük zamanlayıcı başlatıldı — hedef 08:30 TR")

        # ── Aylık Makro Takvim Güncelleyici ───────────────────────
        def _aylik_makro():
            """Her ayın 1'inde 09:00 TR'de makro takvim ICS günceller."""
            import subprocess as _sp
            while True:
                try:
                    simdi_tr = datetime.now(_TR_TZ)
                    if (simdi_tr.day == 1 and simdi_tr.hour == 9
                            and 0 <= simdi_tr.minute <= 4
                            and _zamanlayi_durum.get("son_makro_ay") != simdi_tr.month):

                        _zamanlayi_durum["son_makro_ay"] = simdi_tr.month
                        print(f"[Makro] Aylık güncelleme başlıyor — {simdi_tr.strftime('%d.%m.%Y %H:%M')}")

                        # macro_calendar_updater.py'yi çalıştır
                        script = str(REPO_ROOT / "scripts" / "macro_calendar_updater.py")
                        env = {**__import__("os").environ, "FMP_API_KEY": FMP_KEY}
                        result = _sp.run(
                            ["python3", script, "--aylar", "3"],
                            capture_output=True, text=True, env=env, timeout=120
                        )
                        if result.returncode == 0:
                            print(f"[Makro] ✅ ICS üretildi")
                            # GitHub'a commit et (PAT token gerekli)
                            pat = __import__("os").environ.get("GH_TOKEN") or __import__("os").environ.get("PAT_TOKEN","")
                            if pat:
                                import base64 as _b64
                                ics_path = REPO_ROOT / "data" / "calendars" / "macro_events.ics"
                                if ics_path.exists():
                                    ics_content = ics_path.read_bytes()
                                    b64_content = _b64.b64encode(ics_content).decode()
                                    ay_str = simdi_tr.strftime("%Y-%m")
                                    # GitHub API ile dosyayı güncelle
                                    api_url = "https://api.github.com/repos/zeynelgun-afk/portfolio-tracker/contents/data/calendars/macro_events.ics"
                                    headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
                                    # Mevcut SHA'yı al
                                    import requests as _rq2
                                    r_get = _rq2.get(api_url, headers=headers, timeout=10)
                                    sha = r_get.json().get("sha","")
                                    payload = {
                                        "message": f"[DATA] Makro takvim güncellendi — {ay_str}",
                                        "content": b64_content,
                                        "sha": sha
                                    }
                                    r_put = _rq2.put(api_url, headers=headers, json=payload, timeout=15)
                                    if r_put.status_code in (200, 201):
                                        print("[Makro] ✅ GitHub'a commit edildi")
                                    else:
                                        print(f"[Makro] ⚠️ Commit hatası: {r_put.status_code}")
                            # Telegram bildirimi
                            tg_send(PRIVATE_CHAT,
                                f"📈 <b>Makro Takvim Güncellendi</b>\n"
                                f"<i>{simdi_tr.strftime('%B %Y')}</i>\n\n"
                                f"FOMC + CPI + NFP + PCE + Earnings tarihleri yenilendi.\n"
                                f"Google Calendar otomatik senkronize olacak.\n\n"
                                f"<i>finzora ai • makro takvim</i>")
                        else:
                            print(f"[Makro] ❌ Script hatası: {result.stderr[:200]}")
                except Exception as e:
                    print(f"[Makro] Döngü hatası: {e}")
                time.sleep(60)

        _tm = threading.Thread(target=_aylik_makro, daemon=True, name="AylikMakro")
        _tm.start()
        print(f"[Bot] Aylık makro zamanlayıcı başlatıldı — her ayın 1'i 09:00 TR")

        # ── GitHub Actions Workflow Tetikleyici ───────────────────
        # Railway zamanı takip eder, GitHub Actions işi yapar
        GH_PAT = os.environ.get("GH_TOKEN") or os.environ.get("PAT_TOKEN","")
        GH_REPO = "zeynelgun-afk/portfolio-tracker"
        GH_API  = "https://api.github.com"

        def _gh_dispatch(workflow_file: str, inputs: dict = None):
            """GitHub Actions workflow_dispatch tetikle."""
            if not GH_PAT:
                print(f"[GH] ⚠️ GH_TOKEN eksik — {workflow_file} tetiklenemiyor")
                return False
            url = f"{GH_API}/repos/{GH_REPO}/actions/workflows/{workflow_file}/dispatches"
            payload = {"ref": "main"}
            if inputs:
                payload["inputs"] = inputs
            try:
                r = requests.post(url, json=payload, timeout=10, headers={
                    "Authorization": f"Bearer {GH_PAT}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                })
                ok = r.status_code == 204
                print(f"[GH] {'✅' if ok else '❌'} {workflow_file} → HTTP {r.status_code}")
                return ok
            except Exception as e:
                print(f"[GH] ❌ {workflow_file} hata: {e}")
                return False

        # ── Zamanlama tablosu ─────────────────────────────────────
        # (saat, dakika, workflow_file, inputs, hafta_ici, pazar_mu, aciklama)
        # hafta_ici=True  → sadece Pzt-Cum
        # pazar_mu=True   → sadece Pazar
        # Her ikisi False → her gün
        _GH_ZAMANLAMALAR = [
            # Hafta içi sabit
            (9,   0, "news_radar.yml",       {},                    True,  False, "Haber Radarı"),
            (12, 30, "adil_deger_panel.yml", {},                    True,  False, "Adil Değer Paneli"),
            (14,  0, "morning_scan.yml",     {"mode":"all"},        True,  False, "Sabah Evren Taraması"),
            (16,  0, "agent.yml",            {"mode":"morning"},    True,  False, "Agent Sabah"),
            (23, 30, "result_tracker.yml",   {},                    True,  False, "Sonuç Takip"),
            (23, 35, "research_tracker.yml", {"mode":"daily"},      False, False, "Research Tracker Günlük"),  # v5.0 Etap 11 her gün 23:35
            # Kapanış: gece yarısı 00:30 TR (yeni güne geçmiş ama hafta içinde)
            # Pzt gecesi 00:30 = Salı sabahı, Cum gecesi 00:30 = Cmt sabahı
            # weekday(): Sal=1…Cmt=5 → 1-5 arası = gece öncesi hafta içiydi
            (0,  30, "agent.yml",            {"mode":"closing"},    False, False, "Agent Kapanış"),
            # Haftalık — Pazar
            (12,  0, "agent.yml",            {"mode":"weekly"},     False, True,  "Agent Haftalık"),
            (14,  0, "research_tracker.yml", {"mode":"weekly"},     False, True,  "Research Tracker Haftalık"),  # v5.0 Etap 11 Pazar 14:00
        ]

        # Monitor: seans saatlerinde her 30 dakika ayrı liste
        # 17:00-23:30 TR arası (14:00-20:30 UTC) Pzt-Cum
        _MONITOR_SAATLER = set()
        for _h in range(17, 24):
            _MONITOR_SAATLER.add((_h, 0))
            _MONITOR_SAATLER.add((_h, 30))

        _gh_tetiklendi = {}  # "key:YYYY-MM-DD:HH:MM" → True

        def _workflow_zamanlayici():
            """Her dakika kontrol — doğru saatte GitHub Actions workflow tetikle."""
            while True:
                try:
                    simdi      = datetime.now(_TR_TZ)
                    is_hft     = simdi.weekday() < 5   # Pzt(0)…Cum(4)
                    is_pazar   = simdi.weekday() == 6
                    is_gece_hft = 1 <= simdi.weekday() <= 5  # Sal-Cmt (gece öncesi hft)
                    saat, dakika = simdi.hour, simdi.minute
                    gun_str    = simdi.strftime("%Y-%m-%d")

                    # Sabit zamanlamalar
                    for s, d, wf, inputs, hft, pazar, aciklama in _GH_ZAMANLAMALAR:
                        if saat != s or dakika != d:
                            continue
                        if hft   and not is_hft:   continue
                        if pazar and not is_pazar:  continue
                        # Kapanış özel kontrolü (00:30 TR, önceki gün hft olmalı)
                        if wf == "agent.yml" and inputs.get("mode") == "closing":
                            if not is_gece_hft: continue

                        key = f"{wf}:{inputs.get('mode','')}:{gun_str}:{s:02d}{d:02d}"
                        if key not in _gh_tetiklendi:
                            _gh_tetiklendi[key] = True
                            print(f"[GH] {simdi.strftime('%H:%M')} → {aciklama}")
                            _gh_dispatch(wf, inputs or None)

                    # Monitor: seans içi her 30 dk
                    if is_hft and (saat, dakika) in _MONITOR_SAATLER:
                        key = f"agent_monitor:{gun_str}:{saat:02d}{dakika:02d}"
                        if key not in _gh_tetiklendi:
                            _gh_tetiklendi[key] = True
                            print(f"[GH] {simdi.strftime('%H:%M')} → Agent Monitor")
                            _gh_dispatch("agent.yml", {"mode": "monitor"})

                    # Bellek temizliği
                    if len(_gh_tetiklendi) > 200:
                        _gh_tetiklendi.clear()

                except Exception as e:
                    print(f"[GH-Zamanlayici] Hata: {e}")
                time.sleep(60)

        _tw = threading.Thread(target=_workflow_zamanlayici, daemon=True, name="WorkflowZamanlayici")
        _tw.start()
        print(f"[Bot] Workflow zamanlayıcı başlatıldı (tüm cron'lar Railway'de):")
        print(f"[Bot]   09:00 TR (Hft) → Haber Radarı")
        print(f"[Bot]   12:30 TR (Hft) → Adil Değer Paneli")
        print(f"[Bot]   14:00 TR (Hft) → Sabah Evren Taraması")
        print(f"[Bot]   16:00 TR (Hft) → Agent Sabah")
        print(f"[Bot]   17:00-23:30 TR (Hft/30dk) → Agent Monitor")
        print(f"[Bot]   23:30 TR (Hft) → Sonuç Takip")
        print(f"[Bot]   23:35 TR (Gün) → Research Tracker Günlük (v5.0)")
        print(f"[Bot]   00:30 TR (Hft) → Agent Kapanış")
        print(f"[Bot]   12:00 TR (Pzr) → Agent Haftalık")
        print(f"[Bot]   14:00 TR (Pzr) → Research Tracker Haftalık DM Özet (v5.0)")

        # ── Günlük Risk Panel (09:30 TR Hft, grup chat'e PNG) ─────
        def _send_risk_panel(date_str: str) -> bool:
            """Risk paneli üret + grup chat'e PNG olarak gönder."""
            try:
                import subprocess as _sp
                out_dir = REPO_ROOT / "outputs" / "risk_panel"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{date_str}.png"

                # 1. Script'i çalıştır
                proc = _sp.run(
                    [sys.executable, str(REPO_ROOT / "scripts" / "risk_panel_generator.py"),
                     "--out", str(out_path)],
                    capture_output=True, text=True, timeout=180,
                    cwd=str(REPO_ROOT),
                )
                if proc.returncode != 0 or not out_path.exists():
                    print(f"[RiskPanel] ❌ Script hata (rc={proc.returncode}): "
                          f"{proc.stderr[:300] if proc.stderr else 'no stderr'}")
                    return False

                # 2. Telegram grup chat'e gönder
                if not BOT_TOKEN:
                    print("[RiskPanel] ❌ BOT_TOKEN yok, gönderilemedi")
                    return False
                with open(out_path, "rb") as f:
                    r = requests.post(
                        f"{API_BASE}/sendPhoto",
                        data={"chat_id": GROUP_CHAT,
                              "caption": f"📊 Risk Paneli — {date_str}"},
                        files={"photo": f},
                        timeout=60,
                    )
                if r.status_code == 200:
                    print(f"[RiskPanel] ✅ Grup'a gönderildi: {date_str}")
                    return True
                print(f"[RiskPanel] ❌ Telegram hata: HTTP {r.status_code} — "
                      f"{r.text[:200]}")
                return False
            except Exception as e:
                print(f"[RiskPanel] Exception: {type(e).__name__}: {e}")
                return False

        _risk_panel_gunluk = {}  # gün başına 1 kez

        def _risk_panel_zamanlayici():
            """Her dakika kontrol — Hft 09:30 TR'de risk paneli grup chat'e."""
            while True:
                try:
                    simdi = datetime.now(_TR_TZ)
                    is_hft = simdi.weekday() < 5
                    saat, dakika = simdi.hour, simdi.minute
                    gun_str = simdi.strftime("%Y-%m-%d")

                    if is_hft and saat == 9 and dakika == 30:
                        if gun_str not in _risk_panel_gunluk:
                            _risk_panel_gunluk[gun_str] = True
                            print(f"[RiskPanel] {simdi.strftime('%H:%M')} → Günlük panel üretiliyor")
                            _send_risk_panel(gun_str)
                except Exception as e:
                    print(f"[RiskPanel-Zamanlayici] Hata: {e}")
                time.sleep(60)

        _trp = threading.Thread(target=_risk_panel_zamanlayici, daemon=True, name="RiskPanelZamanlayici")
        _trp.start()
        print(f"[Bot]   09:30 TR (Hft) → Günlük Risk Paneli (grup chat'e PNG)")
        # ─────────────────────────────────────────────────────────

        # ─────────────────────────────────────────────────────────
        # ANALİST TAKİP — Analyst revision monitoring (12 May 2026)
        # 13:00-16:30 (60dk), 16:30-23:30 (30dk), 23:30-01:30 (30dk),
        # Cmt 10:00 catchup. Tümü DM-only.
        try:
            from agent.analist_takip import analist_takip_tick

            def _analist_takip_zamanlayici():
                while True:
                    try:
                        analist_takip_tick()
                    except Exception as e:
                        print(f"[AnalistTakip-Zamanlayici] Hata: {e}")
                    time.sleep(60)

            _tat = threading.Thread(
                target=_analist_takip_zamanlayici,
                daemon=True,
                name="AnalistTakip",
            )
            _tat.start()
            print(f"[Bot]   13:00-01:30 TR → Analist Takip (revize polling, DM-only)")
        except Exception as e:
            print(f"[Bot] AnalistTakip başlatılamadı: {e}")
        # ─────────────────────────────────────────────────────────

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
