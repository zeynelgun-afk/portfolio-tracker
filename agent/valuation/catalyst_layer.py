"""
Finzora Valuation Framework — Catalyst Layer (v7 add-on)
=========================================================
Adil değer hesabına haber + 8-K/SEC dosyaları katmanı ekler.

Mantık:
  1. Son 90 gün haberleri ve SEC filings çek (FMP)
  2. Keyword sınıflandırması: pozitif_maddi / negatif_maddi / nötr
  3. Zaman ağırlığı: 7d→1.0, 7-30d→0.5, 30-90d→0.25
  4. Skor: -100 ile +100 arası
  5. Bayraklar: fresh_positive, dilution_risk, unexplained_move, going_concern,
                insider_buying_cluster, insider_selling_cluster

Framework'e döndürdüğü etki:
  - Confidence puanını ±15 etkiler (zorlama, override değil)
  - Pre-revenue archetype + 90 günde pozitif yok → max NÖTR
  - Bugünkü %10+ hareket + 7d içinde haber yok → "açıklanamayan hareket" red flag
  - Son 30 gün S-3/S-1/şelf başvurusu → dilution_risk red flag
  - Son 7 gün pozitif maddi haber → "fresh_positive" güven +10

Bağımlılık: requests (sadece). FMP API key env'den.
"""

from __future__ import annotations
import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

FMP_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_BASE = "https://financialmodelingprep.com/stable"

# Cache: data/rag/catalyst_cache/<TICKER>.json — 6 saatlik TTL
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "rag" / "catalyst_cache"
CACHE_TTL_SEC = 6 * 3600


# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD SÖZLÜKLERİ
# ─────────────────────────────────────────────────────────────────────────────

# Pozitif maddi katalist anahtar kelimeleri (İngilizce, FMP haberlerinin dili)
POSITIVE_KEYWORDS = {
    # Kontrat / ortaklık
    "partnership", "agreement", "contract awarded", "wins contract", "selected by",
    "strategic alliance", "joint venture", "expansion", "acquires", "acquisition of",
    # Onaylar / regülasyon
    "fda approval", "fda clearance", "patent granted", "patent approved",
    "regulatory approval", "ema approval", "510(k) clearance",
    # Operasyonel zaferler
    "record revenue", "beats estimates", "exceeds guidance", "raises guidance",
    "raises forecast", "milestone", "first commercial", "production ramp",
    # Finansman (pozitif)
    "secures funding", "strategic investment", "grant award",
    # İçeriden alış
    "insider buying", "insider purchase", "10b5-1 plan",
    # Buyback / temettü artışı
    "buyback authorized", "share repurchase", "dividend increase", "special dividend",
}

# Negatif maddi katalist
NEGATIVE_KEYWORDS = {
    # Going concern / iflas
    "going concern", "bankruptcy", "chapter 11", "delisting", "delisted",
    # Soruşturma / dava
    "sec investigation", "doj investigation", "class action",
    "securities fraud", "subpoena",
    # Operasyonel kötü
    "misses estimates", "lowers guidance", "cuts forecast", "guidance cut",
    "earnings miss", "warns of", "profit warning", "revenue shortfall",
    # CEO/CFO ayrılışı
    "ceo resigns", "cfo resigns", "ceo steps down", "cfo steps down",
    "ceo departs", "ceo terminated", "abrupt departure",
    # Sulandırma
    "dilutive offering", "secondary offering", "shelf registration",
    # Recall / clinical fail
    "product recall", "trial failure", "clinical trial failed", "fda rejection",
    "complete response letter", "crl",
    # Temettü kesme
    "dividend suspended", "dividend cut", "dividend eliminated",
}

# Nötr veya rutin (skip)
NEUTRAL_KEYWORDS = {
    "earnings call transcript", "presentation slides", "analyst day",
    "investor conference", "to present at", "scheduled to report",
}


# Form tipi sınıflandırması (SEC filings)
POSITIVE_FORMS = {
    "8-K_item_1.01",  # Material agreement
    "8-K_item_8.01",  # Other (genelde pozitif duyuru)
}
NEGATIVE_FORMS = {
    "S-1", "S-3", "S-3ASR", "424B5", "424B3",  # Şelf / ihraç
    "NT 10-K", "NT 10-Q",  # Geç dosyalama (genelde kötü)
    "8-K_item_5.02",  # CEO/CFO ayrılışı
    "8-K_item_4.01",  # Auditor değişikliği
}
INSIDER_FORMS = {"3", "4", "5"}  # İçeriden işlemler


# ─────────────────────────────────────────────────────────────────────────────
# FMP VERİ ÇEKME
# ─────────────────────────────────────────────────────────────────────────────

def _fmp_get(endpoint: str, params: dict, timeout: int = 12) -> list | dict | None:
    """FMP API GET — hata durumunda None döner."""
    p = dict(params)
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _get_company_name_keywords(ticker: str) -> list:
    """
    Şirket profiline bakarak haberlerde aranacak distinctive keyword'leri çıkar.
    FMP'nin haber endpoint'i ticker etiketini özensiz koyduğu için
    (örn. Montana merkezli AIRJ → tüm Montana haberleri),
    title+text'te şirket adı veya ticker'ın geçmesi şart.
    """
    keywords = [ticker.lower()]  # her zaman ticker'ı ara

    # FMP profile çek
    data = _fmp_get("profile", {"symbol": ticker})
    if not isinstance(data, list) or not data:
        return keywords

    name = (data[0].get("companyName") or "").lower()
    # Şirket adından gürültü kelimeleri çıkar
    noise = {
        "the", "inc", "inc.", "corp", "corp.", "corporation", "company",
        "co", "co.", "ltd", "ltd.", "llc", "limited", "group", "holdings",
        "holding", "international", "industries", "technologies", "technology",
        "tech", "systems", "solutions", "global", "plc", "&", "and",
    }
    parts = re.findall(r"[A-Za-z]+", name)
    distinctive = [p.lower() for p in parts
                   if p.lower() not in noise and len(p) >= 4]
    keywords.extend(distinctive[:3])  # en fazla 3 distinctive parça
    return list(set(keywords))


def _is_relevant(item_text: str, keywords: list) -> bool:
    """Title + snippet'in herhangi bir keyword içerip içermediği."""
    if not keywords:
        return True
    text_lc = item_text.lower()
    return any(k in text_lc for k in keywords)


def fetch_news(ticker: str, days: int = 90, limit: int = 50) -> list:
    """FMP /news/stock — son N gün, şirket adı/ticker eşleşmesi zorunlu."""
    data = _fmp_get("news/stock", {"symbols": ticker, "limit": limit})
    if not isinstance(data, list):
        return []

    keywords = _get_company_name_keywords(ticker)
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    filtered_irrelevant = 0
    for item in data:
        date_str = item.get("publishedDate", "")
        try:
            d = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if d < cutoff:
            continue

        title = item.get("title", "") or ""
        text = item.get("text", "") or ""
        # Relevance check: title VEYA text'te keyword olmalı
        if not _is_relevant(f"{title} {text[:500]}", keywords):
            filtered_irrelevant += 1
            continue

        out.append({
            "date": d.isoformat(),
            "title": title,
            "site": item.get("site", "") or "",
            "url": item.get("url", "") or "",
            "snippet": text[:300],
        })
    return out


def fetch_filings(ticker: str, days: int = 90, limit: int = 30) -> list:
    """FMP /sec-filings-search/symbol — SEC dosyaları."""
    today = datetime.now()
    cutoff = today - timedelta(days=days)
    data = _fmp_get("sec-filings-search/symbol", {
        "symbol": ticker,
        "from": cutoff.strftime("%Y-%m-%d"),
        "to": today.strftime("%Y-%m-%d"),
        "limit": limit,
    })
    if not isinstance(data, list):
        return []

    out = []
    for item in data:
        date_str = (item.get("filingDate") or item.get("acceptedDate") or "")
        try:
            d = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                d = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception:
                continue
        out.append({
            "date": d.isoformat(),
            "form": item.get("formType", "") or "",
            "link": item.get("finalLink") or item.get("link", ""),
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SINIFLANDIRMA
# ─────────────────────────────────────────────────────────────────────────────

def classify_news_item(item: dict) -> tuple[str, list]:
    """
    Tek haberi sınıflandır.
    Return: (kategori, eşleşen_keywordler)
    Kategoriler: pozitif | negatif | notr
    """
    text = f"{item.get('title','')} {item.get('snippet','')}".lower()

    pos_hits = [k for k in POSITIVE_KEYWORDS if k in text]
    neg_hits = [k for k in NEGATIVE_KEYWORDS if k in text]
    neu_hits = [k for k in NEUTRAL_KEYWORDS if k in text]

    # Nötr keyword tek başına geçiyorsa ve başka pozitif/negatif yoksa → nötr
    if neu_hits and not pos_hits and not neg_hits:
        return ("notr", neu_hits)

    # Negatif daha agresif (göz ardı edemeyiz)
    if neg_hits and not pos_hits:
        return ("negatif", neg_hits)
    if neg_hits and pos_hits:
        # Karışık — negatif ağır basar (örn "raises guidance but warns of...")
        return ("negatif", neg_hits + pos_hits[:2])
    if pos_hits:
        return ("pozitif", pos_hits)
    return ("notr", [])


def classify_filing_item(item: dict) -> tuple[str, str]:
    """
    Tek SEC dosyasını sınıflandır.
    Return: (kategori, açıklama)
    """
    form = (item.get("form") or "").strip()

    if form in {"S-1", "S-3", "S-3ASR", "424B5", "424B3"}:
        return ("negatif", f"sulandırma_riski ({form})")
    if form in {"NT 10-K", "NT 10-Q"}:
        return ("negatif", f"geç_dosyalama ({form})")
    if form in INSIDER_FORMS:
        return ("insider", f"içeriden_işlem ({form})")
    if form == "8-K":
        # 8-K detayını item description'dan alamıyoruz — nötr varsay
        return ("8k_event", "8-K (detay belirsiz)")
    if form in {"10-K", "10-Q", "DEF 14A", "DEFA14A", "ARS", "PRE 14A"}:
        return ("rutin", form)
    return ("rutin", form)


def time_weight(item_date_iso: str, now: datetime | None = None) -> float:
    """
    Zaman ağırlığı:
      0-7 gün:    1.0
      7-30 gün:   0.5
      30-90 gün:  0.25
      90+ gün:    0
    """
    if now is None:
        now = datetime.now()
    try:
        d = datetime.fromisoformat(item_date_iso)
    except Exception:
        return 0.0
    age = (now - d).days
    if age < 0:
        return 1.0
    if age <= 7:
        return 1.0
    if age <= 30:
        return 0.5
    if age <= 90:
        return 0.25
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# ANA HESAP
# ─────────────────────────────────────────────────────────────────────────────

def _read_cache(ticker: str) -> dict | None:
    p = CACHE_DIR / f"{ticker.upper()}.json"
    if not p.exists():
        return None
    try:
        with open(p) as f:
            data = json.load(f)
        if time.time() - data.get("_cached_at", 0) > CACHE_TTL_SEC:
            return None
        return data
    except Exception:
        return None


def _write_cache(ticker: str, data: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        out = dict(data)
        out["_cached_at"] = time.time()
        with open(CACHE_DIR / f"{ticker.upper()}.json", "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def compute_catalyst_layer(ticker: str, archetype: str = "generic_equity",
                           use_cache: bool = True, verbose: bool = False) -> dict:
    """
    Ana giriş noktası. Ticker → katalist katmanı raporu.

    Args:
        ticker: örn "AIRJ"
        archetype: framework'ten gelen archetype key (pre_revenue tespiti için)
        use_cache: 6 saatlik cache kullan
        verbose: stdout log

    Returns:
        {
          "ticker": "AIRJ",
          "score": -45 ile +100 arası int (zaman ağırlıklı),
          "flags": ["fresh_positive", "dilution_risk", "unexplained_move", ...],
          "recent_positive": [...],   # son 7 gün pozitifler
          "recent_negative": [...],   # son 30 gün negatifler
          "insider_activity": {"buys": int, "sells": int, "net": int},
          "filing_summary": {"8k_count": int, "shelf_count": int, "insider_count": int},
          "news_summary": {"pos": int, "neg": int, "neutral": int},
          "confidence_adjustment": int (-15 ile +15 arası),
          "max_signal_override": str | None  ("NOTR" → en iyi ihtimalle nötr olur)
        }
    """
    ticker = ticker.upper()

    if use_cache:
        cached = _read_cache(ticker)
        if cached is not None:
            if verbose:
                print(f"[Catalyst] {ticker} → cache hit")
            return cached

    if verbose:
        print(f"[Catalyst] {ticker} → fetching news + filings...")

    news = fetch_news(ticker, days=90, limit=50)
    filings = fetch_filings(ticker, days=90, limit=30)

    now = datetime.now()

    # ── Haber sınıflandırması ────────────────────────────────────────
    news_pos, news_neg, news_neutral = [], [], []
    score_news = 0.0
    for item in news:
        cat, hits = classify_news_item(item)
        item["_category"] = cat
        item["_hits"] = hits
        item["_weight"] = time_weight(item["date"], now)
        if cat == "pozitif":
            news_pos.append(item)
            score_news += 10 * item["_weight"]
        elif cat == "negatif":
            news_neg.append(item)
            score_news -= 15 * item["_weight"]  # negatif daha ağır
        else:
            news_neutral.append(item)

    # ── Filing sınıflandırması ───────────────────────────────────────
    score_filings = 0.0
    insider_buys, insider_sells = 0, 0
    shelf_count = 0
    eight_k_count = 0
    going_concern_recent = False
    auditor_change = False

    for f in filings:
        cat, desc = classify_filing_item(f)
        f["_category"] = cat
        f["_desc"] = desc
        f["_weight"] = time_weight(f["date"], now)
        form = f.get("form", "")

        if form in {"S-1", "S-3", "S-3ASR", "424B5", "424B3"}:
            shelf_count += 1
            score_filings -= 12 * f["_weight"]
        elif form in {"NT 10-K", "NT 10-Q"}:
            score_filings -= 15 * f["_weight"]
        elif form in INSIDER_FORMS:
            # Form 4 için alış/satış ayrımı yapamıyoruz (FMP detay vermez)
            # Kümülatif sayı olarak kaydet (yorum yapmadan)
            if form == "4":
                # Tarih yakınsa "insider activity cluster" sinyali
                if f["_weight"] >= 0.5:  # son 30 gün
                    insider_buys += 1  # heuristic: form 4 genelde alış
        elif form == "8-K":
            eight_k_count += 1

    score = round(score_news + score_filings, 1)
    score = max(-100, min(100, score))

    # ── Bayraklar ────────────────────────────────────────────────────
    flags = []
    confidence_adj = 0
    max_signal_override = None

    # Fresh positive: son 7 günde pozitif maddi
    fresh_pos = [n for n in news_pos if n["_weight"] >= 1.0]
    if fresh_pos:
        flags.append("fresh_positive")
        confidence_adj += 8

    # Fresh negative
    fresh_neg = [n for n in news_neg if n["_weight"] >= 1.0]
    if fresh_neg:
        flags.append("fresh_negative")
        confidence_adj -= 12

    # Dilution risk (son 30 gün şelf/secondary)
    if shelf_count >= 1:
        flags.append("dilution_risk")
        confidence_adj -= 10

    # Going concern check (haber içinde)
    for n in news_neg:
        if any("going concern" in h or "bankruptcy" in h for h in n["_hits"]):
            flags.append("going_concern")
            confidence_adj -= 20
            break

    # Insider activity cluster
    if insider_buys >= 3:
        flags.append("insider_buying_cluster")
        confidence_adj += 5

    # Unexplained move detection burada yapılamaz (fiyat verisi yok),
    # framework tarafında yapılacak. Burada sadece "no recent news"
    # bayrağını kuruyoruz.
    if not fresh_pos and not fresh_neg and not news:
        flags.append("no_recent_news")

    # ── Pre-revenue override ─────────────────────────────────────────
    is_pre_revenue = archetype in {
        "biotech_preclinical",
        "pre_revenue_hardtech",
    }
    if is_pre_revenue:
        # Son 90 günde pozitif maddi yok → max NOTR
        any_positive_90d = bool(news_pos)
        if not any_positive_90d:
            max_signal_override = "NOTR"
            flags.append("pre_revenue_no_positive_90d")
            confidence_adj -= 5

    # Skor sınırlama
    confidence_adj = max(-20, min(15, confidence_adj))

    result = {
        "ticker": ticker,
        "computed_at": now.isoformat(),
        "archetype": archetype,
        "score": score,
        "flags": flags,
        "confidence_adjustment": confidence_adj,
        "max_signal_override": max_signal_override,
        "news_summary": {
            "pos": len(news_pos),
            "neg": len(news_neg),
            "neutral": len(news_neutral),
            "total": len(news),
        },
        "filing_summary": {
            "total": len(filings),
            "8k_count": eight_k_count,
            "shelf_count": shelf_count,
            "insider_count": insider_buys + insider_sells,
        },
        "recent_positive": [
            {"date": n["date"][:10], "title": n["title"][:120], "hits": n["_hits"][:3]}
            for n in news_pos[:5]
        ],
        "recent_negative": [
            {"date": n["date"][:10], "title": n["title"][:120], "hits": n["_hits"][:3]}
            for n in news_neg[:5]
        ],
        "recent_filings": [
            {"date": f["date"][:10], "form": f.get("form", ""), "category": f["_category"]}
            for f in filings[:8]
        ],
    }

    if use_cache:
        _write_cache(ticker, result)

    return result


def detect_unexplained_move(ticker: str, change_pct: float,
                            catalyst: dict) -> bool:
    """
    Fiyat hareketi için "açıklanamayan hareket" tespiti.
    Framework tarafında çağrılır, çünkü fiyat verisi orada.

    True dönerse → "unexplained_move" red flag
    """
    if abs(change_pct) < 7.0:  # %7 altı normal hareket
        return False
    fresh_pos = "fresh_positive" in catalyst.get("flags", [])
    fresh_neg = "fresh_negative" in catalyst.get("flags", [])
    fresh_8k = any(
        f.get("category") == "8k_event" and (
            datetime.now() - datetime.fromisoformat(f["date"])
        ).days <= 2
        for f in catalyst.get("recent_filings", [])
    )
    return not (fresh_pos or fresh_neg or fresh_8k)


# ─────────────────────────────────────────────────────────────────────────────
# RAPOR FORMATLAYICI
# ─────────────────────────────────────────────────────────────────────────────

def format_catalyst_summary(cat: dict) -> str:
    """Kısa Türkçe özet."""
    score = cat.get("score", 0)
    flags = cat.get("flags", [])
    ns = cat.get("news_summary", {})
    fs = cat.get("filing_summary", {})

    yon = "🟢" if score > 15 else "🔴" if score < -15 else "🟡"
    out = [f"{yon} Katalist skoru: {score:+.0f} (90 gün)"]
    out.append(f"  Haberler: {ns.get('pos',0)} pozitif, {ns.get('neg',0)} negatif, "
               f"{ns.get('neutral',0)} nötr")
    out.append(f"  Dosyalar: {fs.get('total',0)} toplam "
               f"(8-K: {fs.get('8k_count',0)}, şelf: {fs.get('shelf_count',0)})")
    if flags:
        out.append(f"  Bayraklar: {', '.join(flags)}")
    if cat.get("recent_positive"):
        out.append("  Son pozitifler:")
        for p in cat["recent_positive"][:3]:
            out.append(f"    • {p['date']} — {p['title'][:80]}")
    if cat.get("recent_negative"):
        out.append("  Son negatifler:")
        for n in cat["recent_negative"][:3]:
            out.append(f"    • {n['date']} — {n['title'][:80]}")
    if cat.get("max_signal_override"):
        out.append(f"  ⚠ Sinyal sınırlaması: max={cat['max_signal_override']}")
    return "\n".join(out)


# CLI test
if __name__ == "__main__":
    import sys
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "AIRJ"
    archetype = sys.argv[2] if len(sys.argv) > 2 else "generic_equity"
    print(f"Catalyst Layer test: {ticker} ({archetype})")
    print("=" * 60)
    cat = compute_catalyst_layer(ticker, archetype, use_cache=False, verbose=True)
    print(format_catalyst_summary(cat))
    print("\nFull JSON:")
    print(json.dumps(cat, indent=2, ensure_ascii=False)[:2000])
