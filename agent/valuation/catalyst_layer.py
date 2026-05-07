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
# KEYWORD SÖZLÜKLERİ (v7.1: 75 → 180 keyword + 30 regex pattern)
# ─────────────────────────────────────────────────────────────────────────────

# Pozitif maddi katalist anahtar kelimeleri
POSITIVE_KEYWORDS = {
    # Kontrat / ortaklık
    "partnership", "agreement", "contract awarded", "wins contract", "selected by",
    "strategic alliance", "joint venture", "expansion", "acquires", "acquisition of",
    "memorandum of understanding", "mou signed", "letter of intent", "loi signed",
    "supply agreement", "licensing deal", "distribution agreement", "exclusive license",
    "design win", "purchase order", "framework agreement", "master agreement",
    # Onaylar / regülasyon
    "fda approval", "fda clearance", "patent granted", "patent approved",
    "regulatory approval", "ema approval", "510(k) clearance", "ce mark",
    "breakthrough designation", "fast track designation", "orphan drug designation",
    "doe approval", "epa approval", "faa approval",
    # Operasyonel zaferler
    "record revenue", "beats estimates", "exceeds guidance", "raises guidance",
    "raises forecast", "milestone", "first commercial", "production ramp",
    "all-time high", "best quarter", "ahead of schedule", "ahead of plan",
    "successful trial", "positive results", "positive data", "phase 3 success",
    "topline results positive", "primary endpoint met", "successfully completed",
    # Finansman (pozitif)
    "secures funding", "strategic investment", "grant award", "department of defense award",
    "doe grant", "non-dilutive funding", "credit facility expanded",
    "investment grade upgrade", "rating upgrade",
    # İçeriden alış
    "insider buying", "insider purchase", "10b5-1 plan", "open market purchase",
    "ceo buys", "director buys",
    # Buyback / temettü artışı
    "buyback authorized", "share repurchase", "dividend increase", "special dividend",
    "accelerated buyback", "tender offer at premium",
    # Analist hareketi
    "upgraded to buy", "upgraded to outperform", "price target raised",
    "initiates with buy", "initiates with overweight",
    # Operasyonel
    "rules in favor", "court rules", "favorable ruling", "patent victory",
    "lawsuit dismissed", "favorable settlement",
}

# Negatif maddi katalist
NEGATIVE_KEYWORDS = {
    # Going concern / iflas
    "going concern", "bankruptcy", "chapter 11", "chapter 7", "delisting", "delisted",
    "liquidation", "winding down", "ceasing operations", "files for bankruptcy",
    "default on", "covenant breach", "loan default",
    # Soruşturma / dava
    "sec investigation", "doj investigation", "class action", "securities fraud",
    "subpoena", "criminal investigation", "fraud charges", "indictment",
    "ftc investigation", "antitrust probe",
    # Operasyonel kötü
    "misses estimates", "lowers guidance", "cuts forecast", "guidance cut",
    "earnings miss", "warns of", "profit warning", "revenue shortfall",
    "withdraws guidance", "suspends guidance", "preliminary results below",
    "weaker than expected", "softer than expected", "headwinds intensify",
    # CEO/CFO ayrılışı
    "ceo resigns", "cfo resigns", "ceo steps down", "cfo steps down",
    "ceo departs", "ceo terminated", "abrupt departure", "interim ceo",
    "fired", "ousted", "leadership change", "ceo replaced",
    # Sulandırma
    "dilutive offering", "secondary offering", "shelf registration", "atm offering",
    "at-the-market offering", "convertible notes offering", "warrants exercised",
    "dilutive financing", "death spiral",
    # Recall / clinical fail
    "product recall", "trial failure", "clinical trial failed", "fda rejection",
    "complete response letter", "crl", "phase 3 fail", "trial halted",
    "trial discontinued", "primary endpoint missed", "topline results negative",
    "safety issue", "fatal event", "serious adverse event",
    # Temettü kesme
    "dividend suspended", "dividend cut", "dividend eliminated", "dividend reduction",
    # Analist hareketi
    "downgraded to sell", "downgraded to underperform", "price target lowered",
    "initiates with sell", "rating downgrade",
    # Operasyonel
    "operations halted", "production halted", "facility closed", "layoffs",
    "workforce reduction", "restructuring charges", "impairment charge",
    "writedown", "write-down", "data breach", "cyber attack", "cyberattack",
    "ransomware", "supply chain disruption",
    # Vergi/yasal
    "tax fraud", "money laundering", "fcpa violation", "consent decree",
}

# Nötr veya rutin (skip)
NEUTRAL_KEYWORDS = {
    "earnings call transcript", "presentation slides", "analyst day",
    "investor conference", "to present at", "scheduled to report",
    "reschedules", "files annual report", "files quarterly report",
    "appoints to board", "elected to board", "annual meeting",
}

# v7.1: Regex pattern'lar — single-keyword check'inden daha güvenli
# (örn "wins major.*contract" → tek tek "wins contract" ararken kaçar)
import re as _re
POSITIVE_PATTERNS = [
    _re.compile(p, _re.IGNORECASE) for p in [
        r"wins?\s+(?:major\s+|new\s+|\$[\d.]+\s*[mb]illion\s+)?contract",
        r"awarded\s+(?:contract|grant)",
        r"raises?\s+(?:fy\s*\d{2,4}\s+)?guidance",
        r"raises?\s+(?:fy\s*\d{2,4}\s+)?(?:revenue|earnings)\s+forecast",
        r"beats?\s+(?:on\s+)?(?:eps|revenue|earnings|both)",
        r"(?:topped|exceeded|beat)\s+(?:wall\s+street\s+)?(?:expectations|estimates)",
        r"fda\s+(?:grants?|approves?|clears?)",
        r"(?:patent|trademark)\s+(?:granted|issued|approved)",
        r"phase\s+(?:i+|[23])\s+(?:trial\s+)?(?:success|met\s+primary)",
        r"strategic\s+(?:partnership|alliance|investment)\s+with",
        r"selected\s+(?:as|by)\s+(?:supplier|partner|vendor)",
        r"first\s+(?:commercial|production|delivery|sale)",
        r"insider\s+(?:purchase|buying|bought)",
        r"upgraded?\s+(?:to|from\s+\w+\s+to)\s+(?:buy|outperform|overweight)",
    ]
]
NEGATIVE_PATTERNS = [
    _re.compile(p, _re.IGNORECASE) for p in [
        r"misses?\s+(?:on\s+)?(?:eps|revenue|earnings|both|expectations)",
        r"(?:cuts?|lowers?|reduces?)\s+(?:fy\s*\d{2,4}\s+)?guidance",
        r"(?:cuts?|lowers?|reduces?)\s+(?:revenue|earnings)\s+forecast",
        r"(?:fell|missed)\s+(?:short\s+)?of\s+(?:wall\s+street\s+)?(?:expectations|estimates)",
        r"phase\s+(?:i+|[23])\s+(?:trial\s+)?(?:fail|missed\s+primary)",
        r"(?:files?|filed)\s+for\s+(?:chapter\s+11|bankruptcy)",
        r"(?:ceo|cfo|coo)\s+(?:resigns?|steps?\s+down|departs?|terminated|fired)",
        r"(?:secondary|public)\s+offering\s+of\s+\d+(?:[\.,]\d+)?\s*(?:million|m)\s+shares",
        r"shelf\s+registration\s+statement",
        r"sec\s+(?:investigation|probe|inquiry)",
        r"class\s+action\s+(?:lawsuit|complaint)",
        r"recall(?:s)?\s+(?:of|its|the)\s+\w+",
        r"downgraded?\s+(?:to|from\s+\w+\s+to)\s+(?:sell|underperform|underweight)",
        r"impairment\s+charge\s+of\s+\$",
        r"writedown\s+of\s+\$|write-down\s+of\s+\$",
    ]
]


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


# v7.1: 8-K Item kategorileri (SEC standartları)
# https://www.sec.gov/files/form8-k.pdf
EIGHT_K_ITEM_MAP = {
    # Section 1 — Business
    "1.01": ("pozitif", "maddi_anlaşma_yapımı", 12),
    "1.02": ("negatif", "maddi_anlaşma_feshi", -10),
    "1.03": ("negatif", "iflas_korumasına_giriş", -25),
    "1.04": ("negatif", "FCPA_ihlali", -20),
    # Section 2 — Financial
    "2.01": ("pozitif", "satın_alma_tamamlandı", 10),
    "2.02": ("notr", "kazanç_açıklaması", 0),  # sayılar haberlerden alınır
    "2.03": ("negatif", "yeni_borç_yükümlülüğü", -8),
    "2.04": ("negatif", "tetikleyici_olay_covenant", -15),
    "2.05": ("negatif", "elden_çıkarma_yeniden_yapılanma", -10),
    "2.06": ("negatif", "değer_düşüklüğü_yazılımı", -12),
    # Section 3 — Securities
    "3.01": ("negatif", "delisting_uyarısı", -18),
    "3.02": ("negatif", "tescilsiz_hisse_satışı", -10),
    "3.03": ("notr", "hak_değişikliği", 0),
    # Section 4 — Accountants
    "4.01": ("negatif", "denetçi_değişikliği", -15),
    "4.02": ("negatif", "geçmiş_finansal_geri_çekme", -25),
    # Section 5 — Corporate Governance
    "5.01": ("notr", "kontrol_değişikliği", 0),
    "5.02": ("karma", "yönetici_ayrılışı_atama", -3),  # yumuşak negatif
    "5.03": ("notr", "ana_sözleşme_değişikliği", 0),
    "5.04": ("notr", "trading_blackout", 0),
    "5.05": ("notr", "etik_kuralları", 0),
    "5.06": ("negatif", "shell_company_status", -15),
    "5.07": ("notr", "oylama_sonuçları", 0),
    "5.08": ("notr", "hissedar_önerileri", 0),
    # Section 6 — Asset-Backed Securities (atla)
    # Section 7 — Reg FD
    "7.01": ("notr", "reg_fd_açıklaması", 0),
    # Section 8 — Other Events
    "8.01": ("pozitif", "diğer_pozitif_duyuru", 6),  # genelde pozitif PR
    # Section 9 — Financial Statements
    "9.01": ("notr", "finansal_ekler", 0),
}


def _fetch_8k_items(url: str, timeout: int = 8) -> list:
    """
    SEC 8-K dosyasından Item numaralarını çıkar (v7.1: parent fallback).

    Strateji:
      1. Verilen URL'yi fetch et, "Item X.XX" pattern'i ara
      2. Bulamazsa: URL exhibit (`-ex*.htm`) olabilir → parent klasör listesini al,
         ana 8-K dosyasını (genelde `<ticker>-<YYYYMMDD>.htm`) bul, onu fetch et

    SEC fair-access politikası gereği User-Agent zorunlu.

    Returns: ['1.01', '8.01', ...] — bulunan item numaraları (boş olabilir)
    """
    if not url or not url.startswith("http"):
        return []

    headers = {
        "User-Agent": "Finzora-AI valuation-research admin@finzora.ai",
        "Accept": "text/html",
    }

    def _parse_html(html_text: str) -> list:
        import re as _r
        text = _r.sub(r"<[^>]+>", " ", html_text)
        text = _r.sub(r"&nbsp;|&amp;|&[a-z]+;", " ", text)
        text = _r.sub(r"\s+", " ", text)
        items = _r.findall(r"(?i)Item\s+(\d+\.\d{2})", text[:30000])
        seen = set()
        out = []
        for it in items:
            if it not in seen:
                seen.add(it)
                out.append(it)
        return out[:5]

    try:
        # 1. Verilen URL'yi dene
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            items = _parse_html(r.text[:50000])
            if items:
                return items

        # 2. Bulamadık — exhibit URL olabilir, parent klasöre git
        # /Archives/edgar/data/X/Y/airj-ex99_1.htm → /Archives/edgar/data/X/Y/
        if "/" in url:
            parent = url.rsplit("/", 1)[0] + "/"
            r2 = requests.get(parent, headers=headers, timeout=timeout)
            if r2.status_code != 200:
                return []
            # Klasör listesinden ana 8-K dosyasını bul
            import re as _r
            files = _r.findall(r'href="([^"]+\.htm)"', r2.text)
            # Ana 8-K kriterleri:
            #   - Aynı klasörde (parent'da geçiyor olmalı)
            #   - Exhibit değil (ex* içermesin)
            #   - Index değil
            base_path = url.split("/Archives/")[1].rsplit("/", 1)[0] if "/Archives/" in url else ""
            candidates = []
            for f in files:
                if base_path and base_path not in f:
                    continue
                fname = f.rsplit("/", 1)[-1].lower()
                if "-ex" in fname or "index" in fname:
                    continue
                if fname.endswith(".htm"):
                    candidates.append(f)
            for cand in candidates[:2]:  # En fazla 2 ana dosyayı dene
                full_url = cand if cand.startswith("http") else f"https://www.sec.gov{cand}"
                r3 = requests.get(full_url, headers=headers, timeout=timeout)
                if r3.status_code == 200:
                    items = _parse_html(r3.text[:50000])
                    if items:
                        return items
        return []
    except Exception:
        return []


def classify_8k_with_items(items: list) -> tuple[str, str, float]:
    """
    8-K içindeki item listesinden kategori + skor çıkar.

    Returns: (kategori, açıklama, skor) — skor pozitif veya negatif
    """
    if not items:
        return ("8k_event", "8-K (item belirsiz)", 0)

    scores = []
    descs = []
    cats = []
    for item in items:
        info = EIGHT_K_ITEM_MAP.get(item)
        if info is None:
            continue
        cat, desc, score = info
        scores.append(score)
        descs.append(f"{item}={desc}")
        cats.append(cat)

    if not scores:
        return ("8k_event", f"8-K (bilinmeyen item: {','.join(items)})", 0)

    total_score = sum(scores)
    # Genel kategori — en negatif/pozitif olan baskın
    if total_score > 5:
        cat = "pozitif"
    elif total_score < -5:
        cat = "negatif"
    else:
        cat = "karma"
    return (cat, "; ".join(descs[:3]), total_score)


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


def fetch_filings(ticker: str, days: int = 90, limit: int = 30,
                  parse_8k_items: bool = True) -> list:
    """
    FMP /sec-filings-search/symbol — SEC dosyaları.

    v7.1: 8-K'lar için item parsing (parse_8k_items=True). Bu SEC'ten
    her 8-K için ek bir HTTP fetch yapar (yavaş). Cache devreye girdiğinde
    sadece ilk çalıştırmada yavaş, sonra hızlı.
    """
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
        form_type = item.get("formType", "") or ""
        final_link = item.get("finalLink") or item.get("link", "")

        entry = {
            "date": d.isoformat(),
            "form": form_type,
            "link": final_link,
        }

        # v7.1: 8-K için item parsing
        if parse_8k_items and form_type == "8-K" and final_link:
            try:
                items = _fetch_8k_items(final_link)
                entry["items"] = items
                if items:
                    entry["form"] = f"8-K [{','.join(items)}]"
            except Exception:
                entry["items"] = []

        out.append(entry)
    return out


def classify_filing_item(item: dict) -> tuple[str, str]:
    """
    Tek SEC dosyasını sınıflandır (v7.1: 8-K item-aware).
    Return: (kategori, açıklama)
    """
    form = (item.get("form") or "").strip()
    raw_form = form.split(" ")[0] if " " in form else form
    items_8k = item.get("items", [])

    # 8-K item parsing varsa onu kullan
    if raw_form == "8-K" and items_8k:
        cat, desc, _score = classify_8k_with_items(items_8k)
        # cat: pozitif | negatif | karma | 8k_event
        return (cat, desc)

    if raw_form in {"S-1", "S-3", "S-3ASR", "424B5", "424B3"}:
        return ("negatif", f"sulandırma_riski ({raw_form})")
    if raw_form in {"NT"} or form in {"NT 10-K", "NT 10-Q"}:
        return ("negatif", f"geç_dosyalama ({form})")
    if raw_form in INSIDER_FORMS:
        return ("insider", f"içeriden_işlem ({raw_form})")
    if raw_form == "8-K":
        return ("8k_event", "8-K (item belirsiz)")
    if raw_form in {"10-K", "10-Q", "DEF", "DEFA14A", "ARS", "PRE"}:
        return ("rutin", form)
    return ("rutin", form)


def classify_news_item(item: dict) -> tuple[str, list]:
    """
    Tek haberi sınıflandır (v7.1: keyword + regex pattern).
    Return: (kategori, eşleşen_keywordler)
    Kategoriler: pozitif | negatif | notr
    """
    text = f"{item.get('title','')} {item.get('snippet','')}".lower()

    pos_hits = [k for k in POSITIVE_KEYWORDS if k in text]
    neg_hits = [k for k in NEGATIVE_KEYWORDS if k in text]
    neu_hits = [k for k in NEUTRAL_KEYWORDS if k in text]

    # v7.1: regex pattern'lar — daha esnek yakalama
    for pat in POSITIVE_PATTERNS:
        m = pat.search(text)
        if m:
            pos_hits.append(f"~{m.group(0)[:50]}")
    for pat in NEGATIVE_PATTERNS:
        m = pat.search(text)
        if m:
            neg_hits.append(f"~{m.group(0)[:50]}")

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


# ─────────────────────────────────────────────────────────────────────────────
# CLAUDE AI FALLBACK (v7.1) — keyword 0 hit verirse opsiyonel sınıflandırma
# ─────────────────────────────────────────────────────────────────────────────

def _classify_with_claude_ai(items: list, ticker: str = "") -> list:
    """
    Keyword + regex 0 hit veren haberleri Claude API ile sınıflandır.

    Maliyet kontrolü:
      - Sadece keyword hit YOK olan haberler gönderilir
      - Tek API çağrısında batch olarak (max 10 haber)
      - 0 haber varsa çağrı yapılmaz

    Returns: items listesi (yerinde mutate edilir, '_category' field'ı eklenir)

    Çevre değişkenleri:
      ANTHROPIC_API_KEY zorunlu
      Yoksa sessizce items'i değiştirmeden döner.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return items  # AI kapalı

    # Sadece keyword hit verilmemiş "notr" kategorideki haberler
    candidates = [
        i for i in items
        if i.get("_category") == "notr"
        and not i.get("_hits")
        and len(i.get("title", "")) >= 20  # çok kısa başlıklar nötr kalsın
    ]
    if not candidates:
        return items
    candidates = candidates[:10]  # Maliyet kontrolü

    # Prompt
    titles = "\n".join(f"{i+1}. {c.get('title','')[:160]}"
                       for i, c in enumerate(candidates))
    prompt = (
        f"Ticker: {ticker}\n"
        f"Aşağıda {len(candidates)} haber başlığı var. Her birini şirket için "
        f"finansal/operasyonel etki açısından sınıflandır:\n"
        f"  POZITIF — kontrat, onay, beklentileri aşma, ortaklık, içeriden alış\n"
        f"  NEGATIF — sulandırma, kayıp, ayrılış, soruşturma, başarısızlık, dava\n"
        f"  NOTR — rutin duyuru, sektör haberi, makale yorumu\n\n"
        f"Sadece JSON dön: [\"POZITIF\"|\"NEGATIF\"|\"NOTR\", ...] "
        f"({len(candidates)} eleman, sıraya uygun).\n\n"
        f"Başlıklar:\n{titles}"
    )

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",  # ucuz + hızlı
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        if r.status_code != 200:
            return items
        resp = r.json()
        text = "".join(b.get("text", "") for b in resp.get("content", [])
                      if b.get("type") == "text")
        # JSON parse — sadece array kısmını al
        m = re.search(r"\[.*?\]", text, re.DOTALL)
        if not m:
            return items
        labels = json.loads(m.group(0))
        if not isinstance(labels, list) or len(labels) != len(candidates):
            return items
        for cand, label in zip(candidates, labels):
            label = str(label).upper().strip()
            if label == "POZITIF":
                cand["_category"] = "pozitif"
                cand["_hits"] = ["~ai:pozitif"]
                cand["_ai_classified"] = True
            elif label == "NEGATIF":
                cand["_category"] = "negatif"
                cand["_hits"] = ["~ai:negatif"]
                cand["_ai_classified"] = True
            # NOTR ise zaten öyle
        return items
    except Exception:
        return items


def compute_catalyst_layer(ticker: str, archetype: str = "generic_equity",
                           use_cache: bool = True, verbose: bool = False,
                           use_ai_fallback: bool = False) -> dict:
    """
    Ana giriş noktası. Ticker → katalist katmanı raporu.

    Args:
        ticker: örn "AIRJ"
        archetype: framework'ten gelen archetype key (pre_revenue tespiti için)
        use_cache: 6 saatlik cache kullan
        verbose: stdout log
        use_ai_fallback: v7.1 — keyword 0 hit veren nötr haberleri Claude
                         API ile sınıflandır (ANTHROPIC_API_KEY gerek). Default
                         off — maliyet kontrolü.

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

    # ── Haber sınıflandırması (1. geçiş: keyword + regex) ────────────
    for item in news:
        cat, hits = classify_news_item(item)
        item["_category"] = cat
        item["_hits"] = hits

    # ── AI fallback (opsiyonel, v7.1) ────────────────────────────────
    # Keyword'ün yakalayamadığı nötr haberleri Claude'a sınıflandırması için ver
    if use_ai_fallback:
        try:
            news = _classify_with_claude_ai(news, ticker=ticker)
            if verbose:
                ai_count = sum(1 for n in news if n.get("_ai_classified"))
                if ai_count:
                    print(f"[Catalyst] {ticker} → AI {ai_count} haber sınıflandırdı")
        except Exception as e:
            if verbose:
                print(f"[Catalyst] AI fallback atlandı: {e}")

    # ── Skor + bucket'lara dağılım ───────────────────────────────────
    news_pos, news_neg, news_neutral = [], [], []
    score_news = 0.0
    for item in news:
        cat = item.get("_category", "notr")
        item["_weight"] = time_weight(item["date"], now)
        if cat == "pozitif":
            news_pos.append(item)
            score_news += 10 * item["_weight"]
        elif cat == "negatif":
            news_neg.append(item)
            score_news -= 15 * item["_weight"]  # negatif daha ağır
        else:
            news_neutral.append(item)

        item["_weight"] = time_weight(item["date"], now)
        if cat == "pozitif":
            news_pos.append(item)
            score_news += 10 * item["_weight"]
        elif cat == "negatif":
            news_neg.append(item)
            score_news -= 15 * item["_weight"]  # negatif daha ağır
        else:
            news_neutral.append(item)

    # ── Filing sınıflandırması (v7.1: 8-K item-aware) ────────────────
    score_filings = 0.0
    insider_buys, insider_sells = 0, 0
    shelf_count = 0
    eight_k_count = 0
    eight_k_negative = 0  # v7.1: negatif 8-K item sayısı
    eight_k_positive = 0  # v7.1: pozitif 8-K item sayısı
    auditor_change = False
    director_departure = False

    for f in filings:
        cat, desc = classify_filing_item(f)
        f["_category"] = cat
        f["_desc"] = desc
        f["_weight"] = time_weight(f["date"], now)
        form = f.get("form", "")
        # form "8-K [1.01,8.01]" gibi olabilir — raw form çıkar
        raw_form = form.split(" ")[0] if " " in form else form

        if raw_form in {"S-1", "S-3", "S-3ASR", "424B5", "424B3"}:
            shelf_count += 1
            score_filings -= 12 * f["_weight"]
        elif raw_form == "NT" or form in {"NT 10-K", "NT 10-Q"}:
            score_filings -= 15 * f["_weight"]
        elif raw_form in INSIDER_FORMS:
            if raw_form == "4" and f["_weight"] >= 0.5:
                insider_buys += 1
        elif raw_form == "8-K":
            eight_k_count += 1
            # v7.1: item-level skor uygula
            items = f.get("items", [])
            if items:
                _cat, _desc, _score = classify_8k_with_items(items)
                score_filings += _score * f["_weight"]
                if _score < -3:
                    eight_k_negative += 1
                elif _score > 3:
                    eight_k_positive += 1
                # Özel item kontrolleri
                if "4.01" in items or "4.02" in items:
                    auditor_change = True
                if "5.02" in items and f["_weight"] >= 0.5:
                    director_departure = True

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

    # v7.1: 8-K item-tabanlı bayraklar
    if auditor_change:
        flags.append("auditor_change")
        confidence_adj -= 12
    if director_departure:
        flags.append("director_departure")
        confidence_adj -= 5
    if eight_k_negative >= 2:
        flags.append("multiple_negative_8k")
        confidence_adj -= 8
    if eight_k_positive >= 1 and not eight_k_negative:
        flags.append("positive_8k_event")
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
    confidence_adj = max(-25, min(20, confidence_adj))  # v7.1: aralık genişledi

    result = {
        "ticker": ticker,
        "computed_at": now.isoformat(),
        "archetype": archetype,
        "framework_version": "v7.1-catalyst",
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
            "8k_positive": eight_k_positive,  # v7.1
            "8k_negative": eight_k_negative,  # v7.1
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
            {
                "date": f["date"][:10],
                "form": f.get("form", ""),
                "items": f.get("items", []),  # v7.1
                "category": f["_category"],
                "desc": f.get("_desc", ""),  # v7.1
            }
            for f in filings[:10]
        ],
    }

    if use_cache:
        _write_cache(ticker, result)

    # v7.1: Prediction logging — backtest için canlı veri biriktirme
    _log_prediction(ticker, result)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION LOGGING (backtest altyapısı)
# ─────────────────────────────────────────────────────────────────────────────

PREDICTION_LOG = (
    Path(__file__).parent.parent.parent / "logs" / "catalyst_predictions.jsonl"
)


def _log_prediction(ticker: str, result: dict) -> None:
    """
    Catalyst tahminini JSONL'e yaz. Forward return script'i sonra
    bu kayıtlara T+5/T+10/T+30 gün return'ünü ekler.

    Schema:
      {
        "ticker": "AIRJ",
        "logged_at": "2026-05-07T15:30:00",
        "archetype": "pre_revenue_hardtech",
        "score": 2.5,
        "flags": [...],
        "confidence_adjustment": -8,
        "max_signal_override": null,
        "news_pos": 1, "news_neg": 0, "8k_pos": 0, "8k_neg": 0,
        "shelf_count": 0,
        # Forward returns daha sonra eklenecek (compute_forward_returns.py):
        "fwd_5d_return": null, "fwd_10d_return": null, "fwd_30d_return": null,
        "logged_price": null
      }
    """
    try:
        # Sadece günde bir kez log (aynı ticker için tekrarları önle)
        today_key = datetime.now().strftime("%Y-%m-%d")
        if PREDICTION_LOG.exists():
            # Son 100 satırı kontrol et — bugün log atılmış mı?
            with open(PREDICTION_LOG) as f:
                lines = f.readlines()
            for line in lines[-100:]:
                try:
                    rec = json.loads(line)
                    if (rec.get("ticker") == ticker
                            and rec.get("logged_at", "")[:10] == today_key):
                        return  # Zaten loglanmış
                except Exception:
                    continue

        PREDICTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        # Fiyatı log için al — basit FMP quote
        price = 0
        try:
            q = _fmp_get("quote", {"symbol": ticker})
            if isinstance(q, list) and q:
                price = q[0].get("price", 0)
        except Exception:
            pass

        record = {
            "ticker": ticker,
            "logged_at": result.get("computed_at"),
            "archetype": result.get("archetype"),
            "score": result.get("score"),
            "flags": result.get("flags", []),
            "confidence_adjustment": result.get("confidence_adjustment"),
            "max_signal_override": result.get("max_signal_override"),
            "news_pos": result.get("news_summary", {}).get("pos", 0),
            "news_neg": result.get("news_summary", {}).get("neg", 0),
            "8k_pos": result.get("filing_summary", {}).get("8k_positive", 0),
            "8k_neg": result.get("filing_summary", {}).get("8k_negative", 0),
            "shelf_count": result.get("filing_summary", {}).get("shelf_count", 0),
            "logged_price": price,
            # Forward returns boş — compute_forward_returns.py dolduracak
            "fwd_5d_return": None,
            "fwd_10d_return": None,
            "fwd_30d_return": None,
        }
        with open(PREDICTION_LOG, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Logging hatasını sessizce yut — ana akışı bozma
        pass


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
