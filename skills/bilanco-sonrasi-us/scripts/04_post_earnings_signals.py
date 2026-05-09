#!/usr/bin/env python3
"""
Aşama 4: Bilanço Sonrası Sinyaller (BU SKILL'İN ÖZGÜN KISMI)

3 alt katman:
  4a) Analist hedef revize yön sayımı (raised vs lowered) — price-target-news
  4b) Telekonferans transcript guidance extract — earning-call-transcript (Ultimate)
  4c) 13F kurumsal birikim + smart money kontrolü — institutional-ownership/*

Kullanım:
    python 04_post_earnings_signals.py --in 03_solid_shortlist.json --out 04_signals_enriched.json \\
        --earnings-from 2026-05-07 --year 2026 --quarter 1

Çıktı: 04_signals_enriched.json
"""
import os
import sys
import json
import re
import time
import argparse
import requests
from datetime import datetime, date, timedelta

API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
BASE = "https://financialmodelingprep.com/stable"

# Smart money CIK referans tablosu (genişletilmiş tablo references/smart_money_ciks.md'de)
SMART_MONEY = {
    "Druckenmiller": "0001536411",
    "Buffett": "0001067983",
    "Burry": "0001649339",
    "Tepper": "0001656456",
    "Ackman": "0001336528",
}

# Fiscal year tuzakları — calendar Q1 != fiscal Q1 olan şirketler
# year_offset: calendar quarter → fiscal year offset (BILL FY2026 = Tem 2025-Haz 2026,
#              dolayısıyla calendar Q3 (Tem-Eyl) ve Q4 (Eki-Ara) BILL FY2026 Q1/Q2 olur, year+1)
# Genişletilebilir, başlangıç seti:
NON_CALENDAR_FISCAL = {
    "BILL": {
        "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2},
        "year_offset":          {1: 0, 2: 0, 3: 1, 4: 1},  # Tem-Haz fiscal year
    },
    "CRM":  {  # Salesforce, Şubat biten fiscal year (FY26 = Şub 2025 - Oca 2026)
        "calendar_to_fiscal_q": {1: 4, 2: 1, 3: 2, 4: 3},
        "year_offset":          {1: 0, 2: 1, 3: 1, 4: 1},
    },
    "ORCL": {  # Oracle, Haziran biten fiscal year (FY26 = Haz 2025 - May 2026)
        "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2},
        "year_offset":          {1: 0, 2: 0, 3: 1, 4: 1},
    },
    "NKE":  {  # Nike, Mayıs biten fiscal year (FY26 = Haz 2025 - May 2026)
        "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2},
        "year_offset":          {1: 0, 2: 0, 3: 1, 4: 1},
    },
    "CSCO": {  # Cisco, Temmuz biten fiscal year
        "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2},
        "year_offset":          {1: 0, 2: 0, 3: 1, 4: 1},
    },
    "WMT":  {  # Walmart, Ocak biten fiscal year (FY27 = Şub 2026 - Oca 2027)
        "calendar_to_fiscal_q": {1: 4, 2: 1, 3: 2, 4: 3},
        "year_offset":          {1: 0, 2: 1, 3: 1, 4: 1},
    },
    "HD":   {  # Home Depot, Ocak biten fiscal year
        "calendar_to_fiscal_q": {1: 4, 2: 1, 3: 2, 4: 3},
        "year_offset":          {1: 0, 2: 1, 3: 1, 4: 1},
    },
    "TGT":  {  # Target, Ocak biten fiscal year
        "calendar_to_fiscal_q": {1: 4, 2: 1, 3: 2, 4: 3},
        "year_offset":          {1: 0, 2: 1, 3: 1, 4: 1},
    },
    "MU":   {  # Micron, Ağustos biten fiscal year (FY26 = Eyl 2025 - Ağu 2026)
        "calendar_to_fiscal_q": {1: 2, 2: 3, 3: 4, 4: 1},
        "year_offset":          {1: 0, 2: 0, 3: 0, 4: 1},
    },
    "ADBE": {  # Adobe, Kasım sonu biten fiscal year (FY26 = Ara 2025 - Kas 2026)
        "calendar_to_fiscal_q": {1: 1, 2: 2, 3: 3, 4: 4},
        "year_offset":          {1: 0, 2: 0, 3: 0, 4: 0},  # neredeyse calendar
    },
    "AVGO": {  # Broadcom, Ekim biten fiscal year (FY26 = Kas 2025 - Eki 2026)
        "calendar_to_fiscal_q": {1: 1, 2: 2, 3: 3, 4: 4},
        "year_offset":          {1: 0, 2: 0, 3: 0, 4: 1},
    },
    "FDX":  {  # FedEx, Mayıs biten fiscal year
        "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2},
        "year_offset":          {1: 0, 2: 0, 3: 1, 4: 1},
    },
}


# 10 May 2026 — canonical fmp_client'a migrasyon (None preservation wrapper)
import sys as _sys_fmp
from pathlib import Path as _Path_fmp

_AGENT_DIR = _Path_fmp(__file__).resolve().parent.parent.parent.parent / "agent"
if str(_AGENT_DIR) not in _sys_fmp.path:
    _sys_fmp.path.insert(0, str(_AGENT_DIR))

try:
    from fmp_client import fmp_get as _canonical_fmp_get

    def fmp_get(endpoint, params=None, max_retries=3, retry_delay=1.5):
        """fmp_client wrapper. Hata/boş veride None döner.
        Canonical sürüm 60+30s*attempt rate limit backoff kullanır."""
        result = _canonical_fmp_get(endpoint, params)
        return result if result else None
except ImportError:
    def fmp_get(endpoint, params=None, max_retries=3, retry_delay=1.5):
        """
        FMP API çağrısı (fallback).

        Retry stratejisi:
          - 200: başarılı, JSON döner
          - 429 (rate limit): retry_delay × 2 ile bekle, max_retries kadar dene
          - 503 (transient overload): retry_delay ile bekle, max_retries kadar dene
          - Network exception (ConnectionError, Timeout): retry_delay ile bekle, max_retries kadar dene
          - Diğer 4xx (400, 401, 403, 404): hata, None dön (retry yok)

        Tüm denemeler başarısızsa None döner.
        """
        if params is None:
            params = {}
        params["apikey"] = API_KEY

        last_error = None
        for attempt in range(max_retries):
            try:
                r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=20)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 429:
                    # Rate limit — exponential backoff
                    wait = retry_delay * (2 ** attempt)
                    print(f"  [retry] {endpoint} rate limit (429), {wait}s bekleniyor (deneme {attempt+1}/{max_retries})", file=sys.stderr)
                    time.sleep(wait)
                    continue
                elif r.status_code == 503:
                    # Transient overload
                    wait = retry_delay
                    print(f"  [retry] {endpoint} server overload (503), {wait}s bekleniyor (deneme {attempt+1}/{max_retries})", file=sys.stderr)
                    time.sleep(wait)
                    continue
                else:
                    # 4xx errors — kalıcı, retry yok
                    return None
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"  [retry] {endpoint} network error, {retry_delay}s bekleniyor (deneme {attempt+1}/{max_retries}): {e}", file=sys.stderr)
                    time.sleep(retry_delay)
                    continue
            except Exception as e:
                last_error = e
                break

        if last_error:
            print(f"  [error] {endpoint} tüm denemeler başarısız: {last_error}", file=sys.stderr)
        return None


def fiscal_period_for_calendar(symbol, calendar_year, calendar_quarter):
    """
    Verilen takvim çeyreğine karşılık gelen fiscal (year, quarter) tuple'ını döndürür.
    
    Calendar Q4 2025 BILL bilançosu için:
      - calendar_to_fiscal_q[4] = 2  (BILL FY Q2)
      - year_offset[4] = 1           (calendar Q4 -> fiscal year+1)
      - Sonuç: (2026, 2) — BILL FY26 Q2 = Eki-Ara 2025
    
    Calendar Q1 2026 BILL bilançosu için:
      - calendar_to_fiscal_q[1] = 3  (BILL FY Q3)
      - year_offset[1] = 0           (calendar Q1 -> aynı fiscal year)
      - Sonuç: (2026, 3) — BILL FY26 Q3 = Oca-Mar 2026
    
    Standart calendar şirketler için (fiscal year = calendar year):
      - Sonuç: (calendar_year, calendar_quarter) — değişiklik yok
    """
    fc = NON_CALENDAR_FISCAL.get(symbol)
    if not fc:
        return calendar_year, calendar_quarter  # standart calendar şirket
    
    fiscal_q = fc["calendar_to_fiscal_q"].get(calendar_quarter, calendar_quarter)
    year_off = fc["year_offset"].get(calendar_quarter, 0)
    return calendar_year + year_off, fiscal_q


# 4a) ANALİST REVİZE YÖN SAYIMI -------------------------------------------------

# Title pattern'leri — false positive'i azaltmak için "price target" bağlamı şart
# (örn. "Concerns are raised over X" RAISED olarak işaretlenmez çünkü "price target" geçmez)
RAISE_PATTERNS = [
    r"raise[ds]?\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target|outlook)",
    r"lift[seding]*\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"increas[eding]*\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"boost[seding]*\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"hike[ds]?\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"price\s+target\s+(?:raised|increased|lifted|boosted|hiked|upgraded)",
    r"new\s+street\s+high",
    # Rating upgrades (şirket adı arada olabilir, lazy match)
    r"upgrad[eds]+\s+\S+\s+(?:from\s+\w+\s+)?to\s+(?:buy|outperform|overweight|strong\s+buy)",
    r"upgrad[eds]+\s+(?:to|its\s+rating)\s+(?:buy|outperform|overweight)",
]

LOWER_PATTERNS = [
    r"lower[seding]*\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target|outlook)",
    r"reduc[eding]*\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"cut[s]?\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"slash[eding]*\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"trim[meding]*\s+(?:its\s+|the\s+|their\s+)?(?:price\s+target|pt|target)",
    r"price\s+target\s+(?:lowered|reduced|cut|slashed|trimmed|downgraded)",
    # Rating downgrades (şirket adı arada olabilir)
    r"downgrad[eds]+\s+\S+\s+(?:from\s+\w+\s+)?to\s+(?:hold|underperform|underweight|sell|neutral)",
    r"downgrad[eds]+\s+(?:to|its\s+rating)\s+(?:hold|underperform|underweight|sell)",
]


def classify_revision_title(title):
    """Analist haber başlığını RAISED/LOWERED/NEUTRAL olarak sınıflandır.
    Tek kelime tabanlı eşleşme yerine 'price target' bağlamına bağlı pattern."""
    if not title:
        return "NEUTRAL"
    t = title.lower()
    
    for p in RAISE_PATTERNS:
        if re.search(p, t):
            return "RAISED"
    for p in LOWER_PATTERNS:
        if re.search(p, t):
            return "LOWERED"
    
    # Fallback: pattern'ler eşleşmediyse ama "PT" veya "target" + (raise/lower variant) varsa
    if "target" in t or "pt" in t or "price" in t:
        if any(w in t for w in ["raise", "lift", "boost", "hike", "increase", "upgrade"]):
            return "RAISED"
        if any(w in t for w in ["lower", "cut", "slash", "trim", "reduce", "downgrade"]):
            return "LOWERED"
    
    return "NEUTRAL"


def analyst_revisions(symbol, earnings_date_str):
    """Bilanço sonrası analist hedef revize haberleri."""
    pt_news = fmp_get("price-target-news", {"symbol": symbol, "limit": 50})  # 20 → 50, mega-cap'ler için
    if not pt_news or not isinstance(pt_news, list):
        return {"raised": 0, "lowered": 0, "neutral": 0, "verdict": "NO_DATA", "items": []}
    
    earn_d = datetime.strptime(earnings_date_str, "%Y-%m-%d").date()
    raised = lowered = neutral = 0
    items = []
    for n in pt_news:
        pub = (n.get("publishedDate") or "")[:10]
        if not pub:
            continue
        try:
            pub_d = datetime.strptime(pub, "%Y-%m-%d").date()
        except ValueError:
            continue
        if pub_d < earn_d:
            continue  # Bilanço öncesi
        title = n.get("newsTitle") or ""
        new_pt = n.get("priceTarget") or n.get("adjPriceTarget") or 0
        old_pt = n.get("priceWhenPosted") or 0
        analyst = n.get("analystName") or n.get("analystCompany") or "N/A"
        
        direction = classify_revision_title(title)
        if direction == "RAISED":
            raised += 1
        elif direction == "LOWERED":
            lowered += 1
        else:
            neutral += 1
        
        items.append({
            "date": pub,
            "analyst": analyst,
            "new_target": new_pt,
            "prior_price": old_pt,
            "direction": direction,
            "title": title,
        })
    
    # Yorum
    total_directional = raised + lowered
    if total_directional == 0:
        verdict = "NO_DATA"
    elif raised >= 8 and lowered == 0:
        verdict = "VERY_STRONG_RAISE"  # CON+
    elif raised > 0 and lowered == 0:
        verdict = "STRONG_RAISE"  # BILL örneği
    elif raised >= 2 * lowered:
        verdict = "NET_RAISE"
    elif lowered >= 8 and raised == 0:
        verdict = "CAPITULATION"  # HUBS örneği (13/13 lowered)
    elif lowered > 0 and raised == 0:
        verdict = "STRONG_LOWER"  # TOST örneği
    elif lowered >= 2 * raised:
        verdict = "NET_LOWER"
    else:
        verdict = "MIXED"
    
    return {
        "raised": raised,
        "lowered": lowered,
        "neutral": neutral,
        "verdict": verdict,
        "items": items,
    }


# 4b) TRANSCRIPT GUIDANCE EXTRACT ----------------------------------------------

# Phrase-tabanlı skor sistemi — tek kelime tabanlı yerine bağlam-aware
# (örn. "lower bound" pozitif olabilir, "raises a question" guidance ile ilgisiz)
GUIDANCE_PHRASES = {
    # YÜKSEK SİNYAL (skor 5)
    "raising the midpoint": 5, "raised our guidance": 5, "raise our guidance": 5,
    "raising guidance": 5, "raised guidance": 5,
    "lifting our guidance": 5, "lifted our guidance": 5,
    "increasing our guidance": 5, "increased our guidance": 5,
    "lowering our guidance": 5, "lowered our guidance": 5,
    "reducing our guidance": 5, "cutting our guidance": 5,
    
    # ORTA SİNYAL (skor 4)
    "reaffirming": 4, "reaffirmed": 4, "we reaffirm": 4,
    "raising our outlook": 4, "lowered our outlook": 4,
    "updating our guidance": 4, "revised guidance": 4,
    "fiscal year guidance": 4, "full year guidance": 4, "full-year guidance": 4,
    "second quarter guidance": 4, "third quarter guidance": 4, "fourth quarter guidance": 4,
    "next quarter guidance": 4,
    
    # FORWARD-LOOKING SİNYAL (skor 3)
    "we expect": 3, "we anticipate": 3, "we project": 3, "we forecast": 3,
    "looking ahead": 3, "going forward": 3,
    "for the full year": 3, "for fiscal year": 3, "for the second quarter": 3,
    "midpoint of our": 3, "range of our": 3,
    "outlook for": 3,
    
    # KATALİST/PARTNERSHIP (skor 4-5)
    "strategic partnership": 4, "anthropic": 5, "openai": 4,
    "acquisition close": 4, "deal close": 4, "merger close": 4,
    
    # 2027/uzun vadeli sinyal (skor 3)
    "2027": 3, "2028": 3, "long-term": 3, "long term": 3,
    "multi-year": 3, "multiyear": 3,
}


def extract_guidance(content, max_n=12, min_score=3):
    """
    Transcript metninden guidance/forward-looking cümleleri extract et.
    Phrase-tabanlı skor — tek kelime false positive'lerini azaltır.
    """
    if not content:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', content)
    scored = []
    for s in sentences:
        s = s.strip()
        if len(s) < 30 or len(s) > 800:
            continue
        s_lower = s.lower()
        # Phrase eşleşmesi (tek kelime değil)
        score = sum(weight for phrase, weight in GUIDANCE_PHRASES.items() if phrase in s_lower)
        if score >= min_score:
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    
    seen = set()
    out = []
    for sc, s in scored:
        key = s[:100].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"score": sc, "text": s})
        if len(out) >= max_n:
            break
    return out


def transcript_signal(symbol, year, calendar_quarter):
    """Transcript çek + guidance extract + RAISED/REAFFIRMED/LOWERED tespit."""
    fiscal_year, fiscal_q = fiscal_period_for_calendar(symbol, year, calendar_quarter)
    t = fmp_get("earning-call-transcript", {"symbol": symbol, "year": fiscal_year, "quarter": fiscal_q})
    if not t or not isinstance(t, list) or len(t) == 0:
        # Fallback: calendar year/quarter de denenmeli (mapping yanlış olabilir)
        if (fiscal_year, fiscal_q) != (year, calendar_quarter):
            t = fmp_get("earning-call-transcript", {"symbol": symbol, "year": year, "quarter": calendar_quarter})
            if not t or not isinstance(t, list) or len(t) == 0:
                return {"available": False, "reason": "transcript_yok",
                        "tried": [f"fiscal:Y{fiscal_year}Q{fiscal_q}", f"calendar:Y{year}Q{calendar_quarter}"]}
        else:
            return {"available": False, "reason": "transcript_yok",
                    "tried": [f"Y{year}Q{calendar_quarter}"]}
    
    item = t[0]
    content = item.get("content", "")
    date = item.get("date", "")
    
    if not content:
        return {"available": False, "reason": "icerik_bos"}
    
    guidance_sentences = extract_guidance(content, max_n=12)
    
    # PHRASE-BASED VERDIKT (tek kelime tabanlı tespit yerine, false positive azaltılır)
    full_lower = content.lower()
    
    # RAISED phrases — geniş set
    raise_phrases = [
        "raising the midpoint", "raised our", "we are raising", "we have raised",
        "raising guidance", "raised guidance", "raise guidance",
        "raising our outlook", "raised our outlook", "raise our outlook",
        "raising our full year", "raised our full year",
        "lifting our guidance", "lifted our guidance",
        "increasing our guidance", "increased our guidance",
        "boosting our guidance", "boosted our guidance",
        "revised guidance higher", "revising guidance higher",
        "raising the lower end", "raising the upper end",
        "raising the low end", "raising the high end",
        "increasing our outlook", "increased our outlook",
    ]
    has_raise = any(p in full_lower for p in raise_phrases)
    
    # LOWERED phrases — geniş set
    lower_phrases = [
        "lowering our guidance", "lowered our guidance", "lower our guidance",
        "lowering our outlook", "lowered our outlook",
        "we are lowering", "we have lowered",
        "reducing our guidance", "reduced our guidance",
        "cutting our guidance", "cut our guidance",
        "revising guidance lower", "revising guidance downward",
        "trimming our outlook", "trimmed our outlook",
    ]
    has_lower = any(p in full_lower for p in lower_phrases)
    
    # REAFFIRMED phrases
    reaffirm_phrases = [
        "reaffirming", "reaffirmed", "we reaffirm",
        "maintaining our guidance", "maintain our guidance",
        "unchanged guidance", "guidance unchanged",
    ]
    has_reaffirm = any(p in full_lower for p in reaffirm_phrases)
    
    # Verdict önceliği: RAISED > LOWERED > REAFFIRMED > QUALITATIVE
    if has_raise:
        verdict = "RAISED"
    elif has_lower:
        verdict = "LOWERED"
    elif has_reaffirm:
        verdict = "REAFFIRMED"
    else:
        verdict = "QUALITATIVE_ONLY"  # CELH örneği — niteliksel ifadeler var ama RAISED/LOWERED phrase yok
    
    return {
        "available": True,
        "date": date,
        "fiscal_year_used": fiscal_year,
        "fiscal_quarter_used": fiscal_q,
        "calendar_quarter": calendar_quarter,
        "calendar_year": year,
        "content_length": len(content),
        "verdict": verdict,
        "has_raise": has_raise,
        "has_reaffirm": has_reaffirm,
        "has_lower": has_lower,
        "guidance_sentences": guidance_sentences,
    }


# 4d) 8-K PRESS RELEASE (SEC direct fetch) -------------------------------------
# Transcript yayınlanmadan önce (12-48 saat gecikme) bile bilanço sonrası şirket
# açıklamasını yakalamak için. SEC.gov fair-access için identifying User-Agent şart.

# SEC EDGAR resmi şartı: "Sample Company Name AdminContact@samplecompany.com"
SEC_USER_AGENT = "Finzora AI Research zeynelgun@finzora.example.com"


def strip_html(html_text):
    """Basit HTML tag temizleme (bs4 yerine standalone)."""
    if not html_text:
        return ""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    # HTML entity decode (basit)
    text = text.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&#160;', ' ')
    text = text.replace('&#x201c;', '"').replace('&#x201d;', '"')
    text = text.replace('&#x2019;', "'").replace('&#149;', '•').replace('&#8212;', '—')
    text = re.sub(r'&[#\w]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_sec_url(url, max_retries=2):
    """SEC.gov'dan dosya çek. Doğru User-Agent ile fair-access kuralına uy."""
    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov",
    }
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                return r.text
            elif r.status_code in (429, 503):
                time.sleep(1.0 * (2 ** attempt))
                continue
            else:
                return None
        except (requests.ConnectionError, requests.Timeout):
            if attempt < max_retries - 1:
                time.sleep(1.0)
                continue
        except Exception:
            break
    return None


def has_earnings_press_release(symbol, earnings_date_str, window_days=2):
    """
    Hızlı triage: news/press-releases ile bilanço dönemi PR yayınlanmış mı kontrol et.
    
    8-K SEC.gov fetch'ten ÖNCE çağrılır. Eğer bilanço dönemi penceresinde
    "earnings/quarter/results" başlıklı PR yoksa, mevcut SEC fetch akışı atlanır
    ve hatalı sec-filings-search sorgusu yapılmaz (rate limit dostu).
    
    KRİTİK: news/press-releases parametresi `?symbols=` (ÇOĞUL) olmalı.
    `?symbol=` (tekil) sessizce IGNORE edilir, generic latest döner.
    Bkz: notes/2026-05-10_PRESS_RELEASE_EVAL.md
    
    Returns:
        bool: True = bilanço PR var (SEC fetch'e devam et)
              False = bilanço PR yok (SEC fetch'i atla)
    """
    prs = fmp_get("news/press-releases", {"symbols": symbol, "limit": 20})
    if not prs or not isinstance(prs, list):
        # API hatası veya boş — ihtiyatlı: True dön (SEC fetch yine denenir)
        return True
    
    earn_d = datetime.strptime(earnings_date_str, "%Y-%m-%d").date()
    earnings_keywords = (
        "first quarter", "second quarter", "third quarter", "fourth quarter",
        "1q", "2q", "3q", "4q", "q1", "q2", "q3", "q4",
        "fiscal", "earnings", "quarterly", "reports", "results",
    )
    
    for pr in prs:
        try:
            pr_date_str = pr.get("publishedDate", "")[:10]
            if not pr_date_str:
                continue
            pr_d = datetime.strptime(pr_date_str, "%Y-%m-%d").date()
            if abs((pr_d - earn_d).days) > window_days:
                continue
            title_lower = (pr.get("title") or "").lower()
            if any(k in title_lower for k in earnings_keywords):
                return True
        except (ValueError, TypeError):
            continue
    
    return False


def press_release_signal(symbol, earnings_date_str):
    """
    Bilanço sonrası 8-K press release çek + guidance phrase analizi.
    
    Workflow:
      0. (10 May 2026 ek) news/press-releases ile hızlı triage:
         bilanço dönemi PR yayınlanmamışsa SEC fetch atlanır
      1. FMP sec-filings-search/symbol ile bilanço tarihinden ±2 gün 8-K bul
      2. finalLink (genelde Exhibit 99.1 = press release) ile SEC.gov direkt fetch
      3. HTML strip → phrase verdict (transcript ile aynı RAISED/LOWERED/REAFFIRMED)
    
    Avantaj: Transcript yayınlanmadan önce (12-48 saat gecikme) bile
             bilanço sonrası ilk gün şirket açıklamasını yakalar.
    """
    # 0. Hızlı triage — bilanço PR yayınlanmış mı?
    if not has_earnings_press_release(symbol, earnings_date_str):
        return {"available": False, "reason": "bilanco_PR_yok_triage"}
    
    earn_d = datetime.strptime(earnings_date_str, "%Y-%m-%d").date()
    from_date = (earn_d - timedelta(days=1)).strftime("%Y-%m-%d")
    to_date = (earn_d + timedelta(days=2)).strftime("%Y-%m-%d")
    
    filings = fmp_get("sec-filings-search/symbol",
                      {"symbol": symbol, "from": from_date, "to": to_date})
    if not filings or not isinstance(filings, list):
        return {"available": False, "reason": "filings_yok"}
    
    # 8-K (US) veya 6-K (foreign issuer) bul
    eight_k = next((f for f in filings if f.get("formType") in ("8-K", "6-K")), None)
    if not eight_k:
        return {"available": False, "reason": "8-K/6-K_yok"}
    
    final_link = eight_k.get("finalLink") or eight_k.get("link")
    if not final_link:
        return {"available": False, "reason": "link_yok"}
    
    # SEC.gov direkt fetch
    html = fetch_sec_url(final_link)
    if not html:
        return {"available": False, "reason": "sec_fetch_basarisiz"}
    
    text = strip_html(html)
    if len(text) < 500:
        return {"available": False, "reason": "icerik_cok_kisa", "length": len(text)}
    
    # Transcript ile aynı phrase listeleri (verdict tutarlılığı için)
    full_lower = text.lower()
    
    raise_phrases = [
        "raising the midpoint", "raised our", "we are raising", "we have raised",
        "raising guidance", "raised guidance", "raise guidance",
        "raising our outlook", "raised our outlook",
        "raising our full year", "raised our full year",
        "lifting our guidance", "lifted our guidance",
        "increasing our guidance", "increased our guidance",
        "increasing revenue guidance", "increasing our revenue",  # 8-K specific
        "boosting our guidance", "boosted our guidance",
        "revised guidance higher", "revising guidance higher",
        "raising the lower end", "raising the upper end",
        "raising the low end", "raising the high end",
        "increasing our outlook", "increased our outlook",
    ]
    has_raise = any(p in full_lower for p in raise_phrases)
    
    lower_phrases = [
        "lowering our guidance", "lowered our guidance",
        "lowering our outlook", "lowered our outlook",
        "we are lowering", "we have lowered",
        "reducing our guidance", "reduced our guidance",
        "cutting our guidance", "cut our guidance",
        "revising guidance lower", "revising guidance downward",
        "trimming our outlook", "trimmed our outlook",
        "reducing revenue guidance", "lowered revenue guidance",  # 8-K specific
    ]
    has_lower = any(p in full_lower for p in lower_phrases)
    
    reaffirm_phrases = [
        "reaffirming", "reaffirmed", "we reaffirm",
        "maintaining our guidance", "maintain our guidance",
        "unchanged guidance", "guidance unchanged",
    ]
    has_reaffirm = any(p in full_lower for p in reaffirm_phrases)
    
    if has_raise:
        verdict = "RAISED"
    elif has_lower:
        verdict = "LOWERED"
    elif has_reaffirm:
        verdict = "REAFFIRMED"
    else:
        verdict = "QUALITATIVE_ONLY"
    
    # Top guidance cümleleri extract
    guidance_sentences = extract_guidance(text, max_n=10, min_score=3)
    
    return {
        "available": True,
        "form_type": eight_k.get("formType"),
        "filing_date": eight_k.get("filingDate"),
        "url": final_link,
        "content_length": len(text),
        "verdict": verdict,
        "has_raise": has_raise,
        "has_reaffirm": has_reaffirm,
        "has_lower": has_lower,
        "guidance_sentences": guidance_sentences,
    }


# 4c) 13F KURUMSAL BİRİKİM + SMART MONEY ---------------------------------------

def institutional_signal(symbol, year, quarter):
    """Hisse-bazlı 13F özet."""
    s = fmp_get("institutional-ownership/symbol-positions-summary",
                {"symbol": symbol, "year": str(year), "quarter": str(quarter)})
    if not s or not isinstance(s, list) or len(s) == 0:
        return {"available": False}
    d = s[0]
    inv_change = d.get("investorsHoldingChange") or 0
    shares_change = d.get("numberOf13FsharesChange") or 0
    
    # Yorum
    if shares_change > 1_000_000 and inv_change >= 0:
        verdict = "STRONG_ACCUMULATION"
    elif shares_change > 0 and inv_change > 0:
        verdict = "ACCUMULATION"  # Yeni isim girişi + birikim (CON örneği +10 yatırımcı)
    elif shares_change > 0 and inv_change < 0:
        verdict = "CONSOLIDATION"  # Yatırımcı azaldı, kalanlar büyütüyor (CELH örneği)
    elif shares_change < 0 and inv_change > 0:
        verdict = "ROTATION"  # Yeni isim giriyor, eski büyük çıktı (CON daha hafif örnek)
    elif shares_change < 0:
        verdict = "DISTRIBUTION"
    else:
        verdict = "STABLE"
    
    return {
        "available": True,
        "investorsHolding": d.get("investorsHolding"),
        "investorsHoldingChange": inv_change,
        "numberOf13Fshares": d.get("numberOf13Fshares"),
        "numberOf13FsharesChange": shares_change,
        "totalInvested": d.get("totalInvested"),
        "verdict": verdict,
    }


def smart_money_check(symbols, year, quarter):
    """Smart money portföylerini çek, her birinde shortlist hisseleri var mı bak."""
    portfolios = {}
    for name, cik in SMART_MONEY.items():
        h = fmp_get("institutional-ownership/extract",
                    {"cik": cik, "year": str(year), "quarter": str(quarter)})
        if not h or not isinstance(h, list):
            portfolios[name] = []
            continue
        # Sembol setine göre filtrele
        matches = [d for d in h if d.get("symbol") in symbols]
        portfolios[name] = matches
    return portfolios


# ANA FONKSİYON ----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="03_solid_shortlist.json")
    ap.add_argument("--out", default="04_signals_enriched.json")
    ap.add_argument("--earnings-from", required=True, help="Bilanço dönemi başlangıç tarihi (YYYY-MM-DD)")
    ap.add_argument("--year", type=int, default=2026, help="Calendar yıl transcript çekme için")
    ap.add_argument("--quarter", type=int, default=1, help="Calendar quarter (1-4)")
    ap.add_argument("--13f-year", dest="thirteenf_year", type=int, default=2025, help="13F yılı (45 gün gecikme)")
    ap.add_argument("--13f-quarter", dest="thirteenf_quarter", type=int, default=4, help="13F çeyreği")
    args = ap.parse_args()
    
    with open(args.inp) as f:
        shortlist = json.load(f)
    print(f"Giriş: {len(shortlist)} hisse")
    
    # Smart money'i tek seferde çek (her hisse için tekrar etmemek için)
    print(f"\nSmart money portföyleri çekiliyor (Q{args.thirteenf_quarter} {args.thirteenf_year})...")
    symbols_set = set(s["symbol"] for s in shortlist)
    sm_portfolios = smart_money_check(symbols_set, args.thirteenf_year, args.thirteenf_quarter)
    for name, matches in sm_portfolios.items():
        if matches:
            print(f"  {name}: {[m['symbol'] for m in matches]}")
        else:
            print(f"  {name}: shortlist'imizden hiçbiri yok")
    
    enriched = []
    for i, stock in enumerate(shortlist):
        sym = stock["symbol"]
        earn_date = stock.get("earnings_date") or args.earnings_from
        print(f"\n[{i+1}/{len(shortlist)}] {sym}")
        
        # 4a) Analist revize
        rev = analyst_revisions(sym, earn_date)
        print(f"  Analist: {rev['verdict']} (raised={rev['raised']}, lowered={rev['lowered']})")
        
        # 4b) Transcript
        ts = transcript_signal(sym, args.year, args.quarter)
        if ts.get("available"):
            print(f"  Transcript: {ts['verdict']} ({ts['content_length']} char, fiscal Q{ts.get('fiscal_quarter_used')})")
        else:
            print(f"  Transcript: {ts.get('reason', 'yok')}")
        
        # 4d) 8-K Press Release (transcript yayınlanmadan önce de çalışır)
        pr = press_release_signal(sym, earn_date)
        if pr.get("available"):
            print(f"  Press release ({pr['form_type']}): {pr['verdict']} ({pr['content_length']} char)")
        else:
            print(f"  Press release: {pr.get('reason', 'yok')}")
        
        # 4c) 13F kurumsal
        inst = institutional_signal(sym, args.thirteenf_year, args.thirteenf_quarter)
        if inst.get("available"):
            print(f"  13F: {inst['verdict']} (shares Δ={inst['numberOf13FsharesChange']/1e6:+.1f}M, inv Δ={inst['investorsHoldingChange']:+d})")
        
        # Smart money sahipliği
        sm_owned_by = [name for name, matches in sm_portfolios.items() 
                       if any(m.get("symbol") == sym for m in matches)]
        if sm_owned_by:
            print(f"  Smart money: {sm_owned_by}")
        
        enriched.append({
            **stock,
            "post_earnings_signals": {
                "analyst_revisions": rev,
                "transcript": ts,
                "press_release": pr,
                "institutional": inst,
                "smart_money_owners": sm_owned_by,
            },
        })
    
    with open(args.out, "w") as f:
        json.dump(enriched, f, indent=2, default=str)
    print(f"\nKaydedildi: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
