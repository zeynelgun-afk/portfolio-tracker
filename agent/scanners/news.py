#!/usr/bin/env python3
"""
Finzora AI — Haber Radar Sistemi
Fiyatlanmamış veya yeni düşen piyasa hareketli haberleri tespit eder.
LLM API ile analiz eder, sadece önemli haberleri Telegram DM'e gönderir.

Kullanım:
  python scripts/news_radar.py           # normal çalıştır
  python scripts/news_radar.py --dry-run # telegram göndermeden test
  python scripts/news_radar.py --debug   # ham haberleri göster
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timedelta, timezone

# ── Config ──────────────────────────────────────────────────────────────────
# 13 May 2026: hardcoded fallback'lar kaldırıldı (güvenlik). Env vars
# yoksa script çalışmaz — workflow secrets üzerinden set ediliyor.
FMP_KEY          = os.environ.get("FMP_API_KEY", "")
BOT_TOKEN        = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PRIVATE_CHAT_ID  = os.environ.get("TELEGRAM_DM_CHAT_ID") or os.environ.get("TELEGRAM_PRIVATE_ID", "")
GH_TOKEN         = os.environ.get("GH_TOKEN", "")
GH_REPO          = "zeynelgun-afk/portfolio-tracker"

FMP_BASE         = "https://financialmodelingprep.com/stable"
TELEGRAM_API     = f"https://api.telegram.org/bot{BOT_TOKEN}"
GH_API           = "https://api.github.com"

# 13 May 2026: agent reorganization sonrası import path düzeltildi.
# Eski: agent/fmp_client.py → Yeni: agent/fmp.py (sade v2 wrapper)
REPO_ROOT        = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

LOG_FILE         = os.path.join(REPO_ROOT, "data", "news_radar_log.json")

# Haber gecikmesi: kaç saat geriye bak
NEWS_LOOKBACK_HOURS = 16

# ── Yardımcı ────────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def fmp_get(endpoint, params=None, retries=3):
    """FMP API çağrısı — yeni agent/fmp.py'ye yönlendirilir."""
    try:
        from agent.fmp import fmp_get as _canonical
        return _canonical(endpoint, params=params, max_retries=retries)
    except ImportError:
        # Fallback: agent/ erişilemiyorsa basit fetch
        p = params or {}
        p["apikey"] = FMP_KEY
        try:
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=15)
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return json.load(f)
    return {"gonderilen_url": [], "son_guncelleme": ""}

def save_log(data):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_portfolio_tickers():
    """
    Açık pozisyon ticker'larını yeni tek-portföy yapısından çek.
    13 May 2026 sadeleştirme sonrası: data/portfolio.json (positions[]).
    """
    path = os.path.join(REPO_ROOT, "data", "portfolio.json")
    if not os.path.exists(path):
        log(f"Portföy dosyası yok: {path}")
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        tickers = set()
        for pos in data.get("positions", []):
            sym = pos.get("symbol")
            if sym and isinstance(sym, str):
                tickers.add(sym.upper().strip())
        return sorted(tickers)
    except Exception as e:
        log(f"Portföy okuma hatası: {e}")
        return []

# ── Haber Çekimi ────────────────────────────────────────────────────────────
def fetch_recent_news(lookback_hours=NEWS_LOOKBACK_HOURS):
    """FMP'den son N saatin genel haberlerini çek."""
    log(f"Haberler çekiliyor (son {lookback_hours}h)...")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    items = []

    # Genel piyasa haberleri
    time.sleep(1)
    news = fmp_get("news/general-latest", {"limit": 40})
    if isinstance(news, list):
        items.extend(news)

    # Sektör odaklı statik ticker'lar — enerji, sanayi, savunma, çelik, malzeme
    sector_tickers = ["GEV","ETN","PWR","HUBB","CLF","NUE","STLD","X","VMC",
                      "MLM","LIN","DOW","FCX","ALB","MP","UUUU","DRS","KTOS",
                      "HII","LMT","GD","NOC","RTX","BA","CAT","DE","EMR","ROK"]

    # Portföydeki aktif pozisyonlar — dinamik çek
    portfolio_tickers = load_portfolio_tickers()
    if portfolio_tickers:
        log(f"Portföy pozisyonları takibe ekleniyor: {portfolio_tickers}")
    else:
        log("Portföy ticker'ları bulunamadı — sadece sektör listesi kullanılacak.")

    # Watchlist (havuz) ticker'ları — Aşama 3 (13 May 2026 sonrası)
    watchlist_tickers = []
    try:
        from agent.watchlist import all_symbols as _wl_symbols
        watchlist_tickers = _wl_symbols()
        if watchlist_tickers:
            log(f"Watchlist takibe ekleniyor ({len(watchlist_tickers)} ticker): {watchlist_tickers[:10]}{'...' if len(watchlist_tickers) > 10 else ''}")
    except Exception as e:
        log(f"Watchlist okunamadı: {e}")

    # Birleştir + dedupe
    all_tickers = sorted(set(sector_tickers + portfolio_tickers + watchlist_tickers))
    log(f"Toplam takip edilen ticker sayısı: {len(all_tickers)}")

    # 15'erli gruplar halinde FMP'ye sor (URL uzunluk limiti için)
    batch_size = 15
    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i:i + batch_size]
        time.sleep(2)
        ticker_str = ",".join(batch)
        stock_news = fmp_get("news/stock", {"symbols": ticker_str, "limit": 30})
        if isinstance(stock_news, list):
            items.extend(stock_news)
            log(f"  Batch {i//batch_size + 1}: {len(stock_news)} haber ({len(batch)} ticker)")

    # Filtre: son N saat + URL bazlı deduplicate
    seen_urls = set()
    filtered = []
    for item in items:
        url = item.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        pub = item.get("publishedDate", "")
        if not pub:
            continue

        # Tarih parse
        try:
            # "2026-04-26 10:00:52" veya ISO formatı
            pub_clean = pub.replace(" ", "T")
            if "+" not in pub_clean and "Z" not in pub_clean:
                pub_clean += "Z"
            pub_dt = datetime.fromisoformat(pub_clean.replace("Z", "+00:00"))
            if pub_dt < cutoff:
                continue
        except Exception:
            continue

        filtered.append({
            "title":    item.get("title", ""),
            "text":     item.get("text", "")[:300],
            "url":      url,
            "pub":      pub[:16],
            "source":   item.get("site", item.get("publisher", "")),
            "symbol":   item.get("symbol", ""),
        })

    log(f"Toplam haber: {len(items)} | Filtrelenmiş (son {lookback_hours}h): {len(filtered)}")
    return filtered

# ── LLM API Analizi ───────────────────────────────────────────────────────
CLAUDE_SYSTEM = """You are an equity research analyst writing for Turkish retail investors who follow US markets.

JOB: scan the news list and tag ONLY items that meet these criteria.

INCLUDE:
- Published in the last 12 hours, not yet fully priced in (stock has moved <5%).
- Regulatory/government decision → direct benefit to specific companies.
- Unexpected M&A, critical contract, DOE/DOD funding (DOE = US Department of Energy, DOD = US Department of Defense).
- Commodity/raw-materials decision → direct sectoral impact.
- Critical tech partnership → company value will change.

EXCLUDE:
- General market commentary, macro forecasts, Fed speak (already priced in).
- Earnings releases, scheduled events.
- Analyst price-target updates.
- ETF/fund flow stories.
- Crypto/XRP/Bitcoin news.
- General economic commentary.
- Old news (12h+ ago).

LANGUAGE RULES (CRITICAL — strict):
All free-text values in the JSON output MUST be written in plain, readable
Turkish — at a level a high-school graduate easily understands. DO NOT use
English finance/tech jargon raw — apply this translation map:

  WRONG → RIGHT
  • overhang → "fiyat üzerindeki baskı" / "tedirginlik"
  • narrative → "anlatı" / "piyasa hikayesi"
  • thematic → "temaya dayalı"
  • momentum → "yükseliş ivmesi" / "düşüş ivmesi"
  • sentiment → "piyasa havası" / "yatırımcı ruh hali"
  • capex → "yatırım harcaması"
  • headwind → "olumsuz rüzgar" / "engel"
  • tailwind → "destekleyici rüzgar" / "olumlu etki"
  • catalyst → "tetikleyici"
  • consensus → "piyasa beklentisi"
  • bullish (in prose) → "yükseliş yönlü"
  • bearish (in prose) → "düşüş yönlü"
  • AI → "yapay zeka"
  • chip → "yarı iletken" or "çip"
  • rally → "yükseliş hareketi"
  • sell-off → "satış dalgası"
  • exposure → "maruziyet" / "etkilenme"
  • upside / downside → "yukarı potansiyel" / "aşağı risk"
  • disrupt → "alt üst etmek" / "sarsmak"

These may stay in English:
- Company names and tickers (NVDA, AAPL, etc.)
- Statement-line abbreviations (FCF, EPS, P/E, ROE)
- Institution/place names (Reuters, Wall Street, Hong Kong)
- The "yon" field's enum (bullish/bearish — these are JSON values, do NOT translate).

OUTPUT FORMAT (JSON array — keys MUST stay exactly as shown):
[
  {
    "baslik": "short headline in Turkish, ≤70 chars",
    "neden_onemli": "1-2 Turkish sentences — why not yet priced, who is directly affected, why it matters",
    "etkilenen_hisseler": ["TICK1", "TICK2"],
    "yon": "bullish | bearish",
    "sure": "kısa | orta | uzun vadeli",
    "aciliyet": "yüksek | orta | düşük",
    "kaynak_url": "url"
  }
]

EXAMPLES:
GOOD: "ABD Enerji Bakanlığı küçük modüler reaktörlere 2 milyar dolar fon açıkladı, henüz hiçbir şirket adı duyurulmadı"
BAD : "DOE SMR sektörüne fund commitment, bullish catalyst, sektörde tailwind oluşuyor"

If no items qualify, return an empty array: []
Return ONLY the JSON array — no extra prose."""

def analyze_with_claude(news_items):
    """Analyze news with Kimi (via OpenRouter). Function name kept for backward compatibility."""
    try:
        # 13 May 2026: llm_client şimdi agent/legacy/'de
        from agent.legacy.llm_client import chat as _llm_chat, get_api_key as _get_api_key
    except ImportError as e:
        log(f"HATA: llm_client import edilemedi: {e}")
        return []

    if not _get_api_key():
        log("HATA: OPENROUTER_API_KEY (veya ANTHROPIC_API_KEY) eksik!")
        return []

    news_text = ""
    for i, item in enumerate(news_items[:30], 1):
        news_text += f"\n---{i}---\n"
        news_text += f"Başlık: {item['title']}\n"
        news_text += f"Kaynak: {item['source']} | Tarih: {item['pub']}\n"
        news_text += f"Özet: {item['text']}\n"
        news_text += f"URL: {item['url']}\n"

    if not news_text.strip():
        log("Analiz edilecek haber yok.")
        return []

    user_msg = (f"Today's news (now: {datetime.now().strftime('%d %b %Y %H:%M')} TR time). "
                f"Apply the criteria from the system prompt and return ONLY the JSON array.\n{news_text}")

    log("Kimi API'ye gönderiliyor (OpenRouter)...")
    raw = ""
    try:
        resp = _llm_chat(
            system=CLAUDE_SYSTEM,
            user=user_msg,
            max_tokens=1500,
            temperature=0.2,
            timeout=45,
            apply_language_policy=False,  # CLAUDE_SYSTEM already pins language behavior
        )
        raw = resp.text.strip()
        log(f"LLM yanıtı: {raw[:200]}")

        if raw.startswith("["):
            return json.loads(raw)
        if "```" in raw:
            inside = raw.split("```")[1]
            if inside.startswith("json"):
                inside = inside[4:]
            return json.loads(inside.strip())
        return json.loads(raw)

    except json.JSONDecodeError as e:
        log(f"JSON parse hatası: {e} | Raw: {raw[:200]}")
        return []
    except Exception as e:
        log(f"LLM API hatası: {e}")
        return []

# ── Telegram Gönderim ───────────────────────────────────────────────────────
YON_EMOJI = {"bullish": "📈", "bearish": "📉"}
ACILIYET_EMOJI = {"yüksek": "🔴", "orta": "🟡", "düşük": "⚪"}
SURE_TR = {"kısa": "Kısa vade", "orta": "Orta vade", "uzun": "Uzun vade"}

def build_telegram_message(results):
    """Telegram mesajını oluştur."""
    now_tr = datetime.now().strftime("%d %b %Y, %H:%M")
    lines = [f"🔍 <b>Haber Radarı</b> — {now_tr}\n"]

    for r in results:
        yon   = r.get("yon", "bullish")
        acil  = r.get("aciliyet", "orta")
        sure  = r.get("sure", "kısa")
        hisse = r.get("etkilenen_hisseler", [])
        hisse_str = " ".join([f"${t}" for t in hisse]) if hisse else "—"

        lines.append(f"{ACILIYET_EMOJI.get(acil,'⚪')} <b>{r.get('baslik','')}</b>")
        lines.append(f"💡 {r.get('neden_onemli','')}")
        lines.append(f"{YON_EMOJI.get(yon,'📊')} {yon.capitalize()} | {SURE_TR.get(sure, sure)}")
        lines.append(f"🎯 {hisse_str}")
        url = r.get("kaynak_url", "")
        if url:
            lines.append(f'<a href="{url}">→ Kaynak</a>')
        lines.append("")

    return "\n".join(lines).strip()

def send_telegram(message, dry_run=False):
    """Telegram DM'e gönder."""
    if dry_run:
        print("\n── DRY RUN — Telegram mesajı ──")
        print(message)
        print("────────────────────────────────")
        return True

    if not BOT_TOKEN:
        log("HATA: TELEGRAM_BOT_TOKEN eksik!")
        return False

    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": PRIVATE_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if r.status_code == 200:
            log("Telegram DM gönderildi ✓")
            return True
        else:
            log(f"Telegram hata: {r.status_code} — {r.text[:200]}")
            return False
    except Exception as e:
        log(f"Telegram bağlantı hatası: {e}")
        return False

# ── GitHub Kayıt ────────────────────────────────────────────────────────────
def gh_get_file_sha(path):
    """GitHub'daki dosyanın SHA'sını al (güncelleme için gerekli)."""
    if not GH_TOKEN:
        return None
    r = requests.get(
        f"{GH_API}/repos/{GH_REPO}/contents/{path}",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    if r.status_code == 200:
        return r.json().get("sha")
    return None

def gh_put_file(path, content, message, sha=None):
    """GitHub'a dosya yaz (oluştur veya güncelle)."""
    if not GH_TOKEN:
        log("GH_TOKEN eksik — GitHub kaydı atlanıyor.")
        return False
    import base64
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "committer": {"name": "Finzora AI", "email": "zeynelgun@users.noreply.github.com"},
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(
        f"{GH_API}/repos/{GH_REPO}/contents/{path}",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        json=payload,
        timeout=15,
    )
    return r.status_code in [200, 201]

def build_research_md(result, tarih):
    """Tek bir haber için Markdown araştırma dosyası oluştur."""
    hisseler = result.get("etkilenen_hisseler", [])
    hisse_str = " / ".join([f"${t}" for t in hisseler]) if hisseler else "—"
    yon   = result.get("yon", "bullish").capitalize()
    sure  = result.get("sure", "kısa vade")
    acil  = result.get("aciliyet", "orta").capitalize()
    url   = result.get("kaynak_url", "")

    return f"""# {result.get('baslik', 'Haber Analizi')}

**Tarih:** {tarih}  
**Analist:** Finzora AI — Haber Radarı  
**Tür:** Otomatik Haber Tespiti  
**Durum:** Aktif İzlemede 👁️

---

## Haber Özeti

**Neden Önemli:** {result.get('neden_onemli', '')}

**Yön:** {yon}  
**Süre:** {sure}  
**Aciliyet:** {acil}  

---

## Etkilenen Hisseler

{hisse_str}

---

## Kaynak

{f'[Habere Git]({url})' if url else '—'}

---

## İzleme Notu

> *Fiyat tepkisi ve gelişmeler buraya eklenecek*

| Alan | Değer |
|---|---|
| Tespit Fiyatı | — |
| Fiyat Tepkisi | — |
| Tez Tuttu mu | — |
| Ders | — |

---

*Finzora AI Haber Radarı tarafından otomatik üretilmiştir. Yatırım tavsiyesi değildir.*
"""

def save_to_github(results, dry_run=False):
    """Bulunan haberleri reports/research/ ve index.json'a kaydet."""
    if not results:
        return

    tarih      = datetime.now().strftime("%Y-%m-%d")
    saat       = datetime.now().strftime("%H:%M")
    kaydedilenler = 0

    # ── index.json oku ──
    idx_path = "data/research/index.json"
    idx_sha  = gh_get_file_sha(idx_path)

    if idx_sha:
        r = requests.get(
            f"{GH_API}/repos/{GH_REPO}/contents/{idx_path}",
            headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        import base64
        raw = base64.b64decode(r.json()["content"]).decode()
        index = json.loads(raw)
    else:
        index = {"son_guncelleme": tarih, "toplam_analiz": 0, "beklemede": 0,
                 "aktif_izleme": 0, "dogru_tahmin_orani": None, "analizler": []}

    mevcut_idler = {a["id"] for a in index.get("analizler", [])}

    for result in results:
        hisseler = result.get("etkilenen_hisseler", [])
        # ID: ilk ticker + tarih
        ticker_id = hisseler[0] if hisseler else "RADAR"
        analiz_id = f"{ticker_id}_RADAR_{tarih}"

        # Aynı gün aynı haber tekrar eklenmesin
        if analiz_id in mevcut_idler:
            continue

        # ── Markdown dosyası ──
        md_path    = f"reports/research/{analiz_id}.md"
        md_content = build_research_md(result, f"{tarih} {saat}")

        if dry_run:
            log(f"  [DRY RUN] {md_path} oluşturulacaktı")
        else:
            ok = gh_put_file(
                md_path, md_content,
                f"[RADAR] {result.get('baslik', analiz_id)[:60]} — {tarih}"
            )
            if ok:
                log(f"  GitHub MD kaydedildi: {md_path}")
                kaydedilenler += 1
            else:
                log(f"  GitHub MD HATA: {md_path}")
                continue

        # ── index.json güncelle ──
        index["analizler"].append({
            "id":           analiz_id,
            "ticker":       ticker_id,
            "sirket":       ticker_id,
            "sektor":       "Haber Radarı",
            "analiz_tarihi": tarih,
            "bilanco_tarihi": None,
            "analiz_turu":  "haber_radar",
            "durum":        "aktif_izleme",
            "dosya":        md_path,
            "kataliz": {
                "olay":     result.get("baslik", ""),
                "tarih":    tarih,
                "aciklama": result.get("neden_onemli", ""),
            },
            "portfoy_onerisi": {"dengeli": "izle", "agresif": "izle", "temettü": "izle"},
            "gerceklesen": {"fiyat_tepkisi_pct": None, "tez_tuttu": None, "ders": None},
            "etiketler": ["haber_radar", result.get("yon", "bullish"),
                          result.get("sure", "kısa").replace(" ", "_")],
        })
        mevcut_idler.add(analiz_id)

    if kaydedilenler == 0 and not dry_run:
        return

    # ── index.json geri yaz ──
    index["son_guncelleme"] = tarih
    index["toplam_analiz"]  = len(index["analizler"])
    index["aktif_izleme"]   = sum(1 for a in index["analizler"] if a["durum"] == "aktif_izleme")

    if dry_run:
        log(f"  [DRY RUN] index.json güncellenecekti ({len(index['analizler'])} kayıt)")
        return

    ok = gh_put_file(
        idx_path,
        json.dumps(index, ensure_ascii=False, indent=2),
        f"[RADAR] index.json güncellendi — {tarih} {saat}",
        sha=idx_sha,
    )
    log(f"  index.json: {'OK' if ok else 'HATA'}")


# ────────────────────────── Scanner Adaptörü (Faz 2 Adım 7) ──────────────────────────

# aciliyet × sure → ham score tablosu
# Tasarım: yüksek aciliyet + kısa vade = en güçlü AL sinyali
# Phase 10 tuning'inde bu tablo ayarlanacak
_NEWS_SCORE_TABLE = {
    ("yüksek", "kısa"): 0.90,
    ("yüksek", "orta"): 0.85,
    ("yüksek", "uzun"): 0.75,
    ("orta",   "kısa"): 0.70,
    ("orta",   "orta"): 0.65,
    ("orta",   "uzun"): 0.55,
    ("düşük",  "kısa"): 0.45,
    ("düşük",  "orta"): 0.40,
    ("düşük",  "uzun"): 0.30,
}
_NEWS_DEFAULT_SCORE = 0.50


def _build_candidates_from_news_results(results: list) -> list:
    """LLM haber analiz çıktısından Candidate listesi üret. Pure transform.

    Mantık:
        - Sadece `yon == "bullish"` sonuçlar Candidate üretir
          (bearish haberler farklı kanaldan — tez bozulması uyarısı)
        - Her sonuç × her ticker = bir Candidate
        - Score: aciliyet + sure tablosundan (yüksek/kısa = 0.90 en yüksek)

    Args:
        results: analyze_with_claude() çıktısı. Beklenen şema her elemanda:
            baslik, neden_onemli, yon (bullish/bearish), aciliyet, sure,
            etkilenen_hisseler, kaynak_url

    Returns:
        list[Candidate]. Yan etki yok.

    Faz 2 — Adım 7 (17 May 2026).
    """
    from agent.scanners.base import Candidate

    candidates: list = []
    if not isinstance(results, list):
        return candidates

    for r in results:
        if not isinstance(r, dict):
            continue

        # Yön filtresi: sadece bullish Candidate üretir
        yon = (r.get("yon") or "").strip().lower()
        if yon != "bullish":
            continue

        tickers = r.get("etkilenen_hisseler", []) or []
        if not isinstance(tickers, list) or not tickers:
            continue

        # Score: aciliyet + sure tablosu
        aciliyet = (r.get("aciliyet") or "orta").strip().lower()
        sure = (r.get("sure") or "kısa").strip().lower()
        score = _NEWS_SCORE_TABLE.get((aciliyet, sure), _NEWS_DEFAULT_SCORE)

        baslik = r.get("baslik", "")
        neden = r.get("neden_onemli", "")
        url = r.get("kaynak_url", "")

        reason = f"Haber: {baslik}. Etki: {neden} ({aciliyet} aciliyet, {sure} vade)."

        for ticker in tickers:
            if not isinstance(ticker, str) or not ticker.strip():
                continue
            sym = ticker.strip().upper()
            try:
                candidates.append(Candidate(
                    symbol=sym,
                    score=score,
                    reason=reason,
                    source="news",
                    metadata={
                        "baslik": baslik,
                        "yon": yon,
                        "aciliyet": aciliyet,
                        "sure": sure,
                        "kaynak_url": url,
                        "neden_onemli": neden,
                    },
                ))
            except ValueError as e:
                log(f"  Candidate üretim hatası ({sym}): {e}")

    return candidates


class NewsRadarScanner:
    """BaseScanner adaptörü — Faz 2 Adım 7 (17 May 2026).

    Mevcut script mantığını (fetch_recent_news, analyze_with_claude) yeniden
    kullanır. scan() yan etki yapmaz — sadece Candidate listesi döndürür.
    Yan etkiler (GitHub'a research/*.md push, Telegram DM) CLI main() içinde
    save_to_github + send_telegram üzerinden devam eder.

    Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 5)
    """

    name = "news"

    def __init__(self, lookback_hours: int = NEWS_LOOKBACK_HOURS):
        if lookback_hours <= 0:
            raise ValueError(
                f"lookback_hours > 0 olmalı, alındı: {lookback_hours}"
            )
        self.lookback_hours = int(lookback_hours)

    def scan(self) -> list:
        """FMP'den haber çek → LLM analiz → Candidate listesi.

        Sadece bullish yön'lü sonuçlar Candidate üretir.
        FMP veya LLM API anahtarı yoksa boş liste döner.
        """
        try:
            news = fetch_recent_news(lookback_hours=self.lookback_hours)
        except Exception as e:
            log(f"[news scanner] fetch_recent_news hatası: {e}")
            return []

        if not news:
            return []

        try:
            results = analyze_with_claude(news)
        except Exception as e:
            log(f"[news scanner] LLM analiz hatası: {e}")
            return []

        return _build_candidates_from_news_results(results)

    def health_check(self) -> dict:
        return {
            "name": self.name,
            "ok": bool(FMP_KEY),
            "lookback_hours": self.lookback_hours,
        }


# ── Ana Akış ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Telegram'a gönderme")
    parser.add_argument("--debug",   action="store_true", help="Ham haberleri göster")
    args = parser.parse_args()

    log("=== Finzora Haber Radarı başlıyor ===")
    radar_log = load_log()

    # 1. Haberleri çek
    news_items = fetch_recent_news()
    if not news_items:
        log("Yeni haber yok, çıkılıyor.")
        return

    if args.debug:
        for item in news_items:
            print(f"\n[{item['pub']}] {item['title']}")
            print(f"  {item['text'][:120]}")

    # 2. Daha önce gönderilenleri filtrele
    prev_sent = set(radar_log.get("gonderilen_url", []))
    news_items = [n for n in news_items if n["url"] not in prev_sent]
    log(f"Daha önce gönderilmeyenler: {len(news_items)} haber")

    if not news_items:
        log("Tüm haberler zaten işlendi.")
        return

    # 3. AI analizi
    results = analyze_with_claude(news_items)
    log(f"AI önemli buldu: {len(results)} haber")

    if not results:
        log("Fiyatlanmamış önemli haber bulunamadı — Telegram gönderilmiyor.")
        return

    # 4. Telegram gönder
    message = build_telegram_message(results)
    success = send_telegram(message, dry_run=args.dry_run)

    # 5. GitHub'a kaydet
    if success or args.dry_run:
        log("GitHub'a kaydediliyor...")
        save_to_github(results, dry_run=args.dry_run)

    # 6. Log güncelle
    if success or args.dry_run:
        new_urls = [n["url"] for n in news_items]
        radar_log["gonderilen_url"] = list(prev_sent | set(new_urls))[-500:]  # son 500 tut
        radar_log["son_guncelleme"] = datetime.now().isoformat()
        radar_log["son_gonderim"] = {
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "haber_sayisi": len(results),
            "basliklar": [r.get("baslik","") for r in results],
        }
        if not args.dry_run:
            save_log(radar_log)
        log("Log güncellendi.")

    log("=== Tamamlandı ===")

if __name__ == "__main__":
    main()
