#!/usr/bin/env python3
"""
Finzora AI — Haber Radar Sistemi
Fiyatlanmamış veya yeni düşen piyasa hareketli haberleri tespit eder.
Claude API ile analiz eder, sadece önemli haberleri Telegram DM'e gönderir.

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
FMP_KEY          = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
ANTHROPIC_KEY    = os.environ.get("ANTHROPIC_API_KEY", "")
BOT_TOKEN        = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PRIVATE_CHAT_ID  = os.environ.get("TELEGRAM_PRIVATE_ID", "1403072107")
GH_TOKEN         = os.environ.get("GH_TOKEN", "")
GH_REPO          = "zeynelgun-afk/portfolio-tracker"

FMP_BASE         = "https://financialmodelingprep.com/stable"
ANTHROPIC_URL    = "https://api.anthropic.com/v1/messages"
TELEGRAM_API     = f"https://api.telegram.org/bot{BOT_TOKEN}"
GH_API           = "https://api.github.com"

REPO_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE         = os.path.join(REPO_ROOT, "data", "news_radar_log.json")

# Haber gecikmesi: kaç saat geriye bak
NEWS_LOOKBACK_HOURS = 16

# ── Yardımcı ────────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def fmp_get(endpoint, params=None):
    """FMP API çağrısı — rate limit için 2sn bekle."""
    p = params or {}
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=15)
        if r.status_code == 200 and r.text.strip():
            return r.json()
    except Exception as e:
        log(f"FMP hata ({endpoint}): {e}")
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

    # Sektör odaklı tickers - enerji, sanayi, savunma, çelik, malzeme
    sector_tickers = ["GEV","ETN","PWR","HUBB","CLF","NUE","STLD","X","VMC",
                      "MLM","LIN","DOW","FCX","ALB","MP","UUUU","DRS","KTOS",
                      "HII","LMT","GD","NOC","RTX","BA","CAT","DE","EMR","ROK"]

    time.sleep(2)
    ticker_str = ",".join(sector_tickers[:15])
    stock_news = fmp_get("news/stock", {"symbols": ticker_str, "limit": 30})
    if isinstance(stock_news, list):
        items.extend(stock_news)

    # Tekrar çek - ikinci grup
    time.sleep(2)
    ticker_str2 = ",".join(sector_tickers[15:])
    stock_news2 = fmp_get("news/stock", {"symbols": ticker_str2, "limit": 20})
    if isinstance(stock_news2, list):
        items.extend(stock_news2)

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

# ── Claude API Analizi ───────────────────────────────────────────────────────
CLAUDE_SYSTEM = """Sen bir hisse senedi araştırma uzmanısın. Türk yatırımcılar için ABD piyasalarını takip ediyorsun.

GÖREVİN: Verilen haber listesini analiz et. SADECE aşağıdaki kriterleri karşılayan haberleri işaretle:

ALACAĞIN HABERLER:
- Son 12 saatte yayımlanan ve piyasada henüz tam fiyatlanmamış (hisse %5'ten az tepki vermiş)
- Düzenleyici kararname / hükümet kararı → belirli şirketlere doğrudan fayda
- Beklenmedik M&A (birleşme/satın alma), kritik sözleşme, DOE/DOD finansmanı
- Hammadde/emtia kararı → belirli sektöre doğrudan etki
- Kritik teknoloji ortaklığı → şirket değeri değişecek

ALMAYACAĞIN HABERLER:
- Genel piyasa yorumları, makro tahminler, Fed söylemi (zaten fiyatlandı)
- Bilançolar, kâr açıklamaları (beklenen olaylar)
- Analist hedef fiyat güncellemeleri
- ETF/fon alım-satım haberleri
- Crypto/XRP/Bitcoin haberleri
- Genel ekonomi yorumları
- Eski haberler (12h+ önce)

ÇIKTI FORMAT (JSON dizisi):
[
  {
    "baslik": "kısa başlık Türkçe",
    "neden_onemli": "1 cümle - neden fiyatlanmadı",
    "etkilenen_hisseler": ["TICK1", "TICK2"],
    "yon": "bullish veya bearish",
    "sure": "kısa / orta / uzun vadeli",
    "aciliyet": "yüksek / orta / düşük",
    "kaynak_url": "url"
  }
]

Eğer kriterlerini karşılayan haber yoksa boş dizi döndür: []
SADECE JSON döndür, başka hiçbir şey yazma."""

def analyze_with_claude(news_items):
    """Claude API ile haberleri analiz et."""
    if not ANTHROPIC_KEY:
        log("HATA: ANTHROPIC_API_KEY eksik!")
        return []

    # Haber listesini formatla
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

    user_msg = f"Bugünün haberleri (şu an: {datetime.now().strftime('%d %b %Y %H:%M')} TR saati):\n{news_text}"

    log("Claude API'ye gönderiliyor...")
    try:
        r = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": CLAUDE_SYSTEM,
                "messages": [{"role": "user", "content": user_msg}],
            },
            timeout=45,
        )
        r.raise_for_status()
        data = r.json()
        raw = data["content"][0]["text"].strip()
        log(f"Claude yanıtı: {raw[:200]}")

        # JSON parse
        if raw.startswith("["):
            return json.loads(raw)
        # JSON bloğu içindeyse çıkar
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            return json.loads(raw.strip())
        return json.loads(raw)

    except json.JSONDecodeError as e:
        log(f"JSON parse hatası: {e} | Raw: {raw[:200]}")
        return []
    except Exception as e:
        log(f"Claude API hatası: {e}")
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

    # 3. Claude analizi
    results = analyze_with_claude(news_items)
    log(f"Claude önemli buldu: {len(results)} haber")

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
