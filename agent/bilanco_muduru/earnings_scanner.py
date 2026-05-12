"""
Bilanço Müdürü — Earnings Scanner

İki ana iş:
1. find_today_earnings_companies() — Bugün bilanço açıklayacak şirketleri
   FMP earnings calendar'dan al, market cap filtresi uygula
2. find_latest_earnings_8k() — Verilen ticker için son earnings 8-K'sını
   SEC EDGAR'dan bul (Items 2.02), Exhibit 99.1 link'ini döner
"""
from __future__ import annotations
import re
import requests
from datetime import date, datetime, timedelta
from typing import Optional

from bs4 import BeautifulSoup

from .config import (
    get_fmp_key,
    MIN_MARKET_CAP_B,
)


FMP_BASE = "https://financialmodelingprep.com/stable"
SEC_HEADERS_DATA = {
    "User-Agent": "Finzora AI Research zeynelgun@finzora.example.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}
SEC_HEADERS_WWW = {
    "User-Agent": "Finzora AI Research zeynelgun@finzora.example.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}


def find_today_earnings_companies(
    target_date: Optional[date] = None,
    window: str = "amc",  # "amc", "bmo", "all"
    min_market_cap_b: float = MIN_MARKET_CAP_B,
    fetch_market_cap: bool = False,
) -> list[dict]:
    """
    Belirli tarih için bilanço açıklayacak şirketleri döner.

    FMP earnings-calendar endpoint'i `time` veya `marketCap` field'ı DÖNDÜRMEZ.
    Bu yüzden:
    - `window` parametresi şu an effective değil (TODO: alternative source)
    - `fetch_market_cap=True` → her ticker için ayrı profile çağrısı (yavaş)
    - `fetch_market_cap=False` → tümünü döner, downstream filter

    Returns:
        [{"ticker": "NVDA", "date": "2026-02-25",
          "eps_estimated": 1.30, "revenue_estimated_b": 32.0,
          "market_cap_b": None (veya fetch_market_cap=True ise gerçek)}, ...]
    """
    if target_date is None:
        target_date = date.today()
    date_str = target_date.isoformat()

    fmp_key = get_fmp_key()

    # FMP earnings calendar
    r = requests.get(
        f"{FMP_BASE}/earnings-calendar",
        params={"from": date_str, "to": date_str, "apikey": fmp_key},
        timeout=30,
    )
    if not r.ok:
        return []

    raw = r.json()
    results = []
    for e in raw:
        ticker = e.get("symbol")
        if not ticker:
            continue

        results.append({
            "ticker": ticker,
            "date": e.get("date"),
            "eps_estimated": e.get("epsEstimated") or e.get("eps"),
            "revenue_estimated_b": (e.get("revenueEstimated") or e.get("revenue") or 0) / 1e9 or None,
            "market_cap_b": None,  # FMP earnings-calendar'da yok
        })

    # Opsiyonel: market cap fetch (yavaş, 2000+ ticker için pahalı)
    if fetch_market_cap:
        results = _hydrate_market_cap(results, fmp_key)
        results = [r for r in results if r["market_cap_b"] and r["market_cap_b"] >= min_market_cap_b]
        results.sort(key=lambda x: x["market_cap_b"], reverse=True)

    return results


def _hydrate_market_cap(companies: list[dict], fmp_key: str) -> list[dict]:
    """Her ticker için FMP profile çağrısı ile market cap hidrate et."""
    for c in companies:
        try:
            r = requests.get(
                f"{FMP_BASE}/profile",
                params={"symbol": c["ticker"], "apikey": fmp_key},
                timeout=10,
            )
            if r.ok:
                data = r.json()
                if data:
                    c["market_cap_b"] = round((data[0].get("mktCap") or 0) / 1e9, 2)
        except Exception:
            pass
    return companies


def get_market_cap_b(ticker: str) -> Optional[float]:
    """Tek bir ticker için market cap (USD billion). FMP quote endpoint'inden."""
    try:
        r = requests.get(
            f"{FMP_BASE}/quote",
            params={"symbol": ticker, "apikey": get_fmp_key()},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            if data:
                return round((data[0].get("marketCap") or 0) / 1e9, 2)
    except Exception:
        pass
    return None


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """
    SEC EDGAR'dan ticker → CIK mapping.
    İlk çağrıda cache'lenir.
    """
    # SEC company tickers JSON
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=SEC_HEADERS_WWW,
            timeout=30,
        )
        if not r.ok:
            return None
        data = r.json()
        for item in data.values():
            if isinstance(item, dict) and item.get("ticker", "").upper() == ticker.upper():
                cik = item.get("cik_str")
                return str(cik).zfill(10) if cik else None
    except Exception:
        return None
    return None


# Hard-coded CIK cache (sık kullanılanlar için hızlı erişim)
CIK_CACHE = {
    "NVDA": "1045810",
    "GOOGL": "1652044",
    "GOOG": "1652044",
    "MSFT": "789019",
    "AAPL": "320193",
    "AMZN": "1018724",
    "META": "1326801",
    "TSLA": "1318605",
    "NFLX": "1065280",
    "JPM": "19617",
    "BAC": "70858",
    "WMT": "104169",
    "JNJ": "200406",
    "PG": "80424",
    "ORCL": "1341439",
    "CRM": "1108524",
    "AVGO": "1730168",
    "AMD": "2488",
    "INTC": "50863",
    "TSM": "1046179",
    "ASML": "937966",
    "LLY": "59478",
    "UNH": "731766",
    "XOM": "34088",
    "CVX": "93410",
}


def find_latest_earnings_8k(
    ticker: str,
    since_date: Optional[date] = None,
    cik: Optional[str] = None,
) -> Optional[dict]:
    """
    Ticker için son earnings 8-K'sını (Items 2.02) bul.

    Args:
        ticker: Hisse sembolü
        since_date: Sadece bu tarih sonrasındaki 8-K'lar (None ise son 7 gün)
        cik: Önceden bilinen CIK (yoksa SEC'ten arar)

    Returns:
        {"accession": "0001045810-26-000019", "filing_date": "2026-02-25",
         "primary_doc": "nvda-20260225.htm", "exhibit_99_1_url": "https://...",
         "items": "2.02,9.01"}
        veya None (8-K yok)
    """
    if since_date is None:
        since_date = date.today() - timedelta(days=7)

    cik = cik or CIK_CACHE.get(ticker.upper()) or get_cik_for_ticker(ticker)
    if not cik:
        return None

    # Recent filings
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    try:
        r = requests.get(url, headers=SEC_HEADERS_DATA, timeout=30)
        if not r.ok:
            return None
        data = r.json()
    except Exception:
        return None

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    items = recent.get("items", [""] * len(forms))

    since_str = since_date.isoformat()

    for i, form in enumerate(forms):
        if form != "8-K":
            continue
        if dates[i] < since_str:
            continue
        item_codes = str(items[i] if i < len(items) else "")
        if "2.02" not in item_codes:
            continue

        # Bulduk — Exhibit 99.1'i bul
        acc = accessions[i].replace("-", "")
        filing_dir_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc}/"
        ex991_url = _find_exhibit_99_1(filing_dir_url)

        return {
            "accession": accessions[i],
            "filing_date": dates[i],
            "primary_doc": primary_docs[i] if i < len(primary_docs) else None,
            "exhibit_99_1_url": ex991_url,
            "items": item_codes,
            "filing_dir_url": filing_dir_url,
        }

    return None


def _find_exhibit_99_1(filing_dir_url: str) -> Optional[str]:
    """Filing dizininden Exhibit 99.1 dosyasını bul (press release)."""
    try:
        r = requests.get(filing_dir_url, headers=SEC_HEADERS_WWW, timeout=30)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, "html.parser")

        # Pattern öncelikleri:
        # 1. "ex991", "ex-991", "exhibit991", "exhibit-99-1"
        # 2. "pr.htm", "press", "release", "earnings"
        # 3. Ana primary doc (8-K'nın kendisi) DIŞINDA herhangi bir htm

        candidates = []
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if not href.endswith(".htm"):
                continue
            if "index" in href.lower():
                continue
            fname = href.split("/")[-1].lower()
            candidates.append((fname, href))

        # Priority 1: explicit ex991 patterns
        for fname, href in candidates:
            if re.search(r"ex.{0,2}99.{0,1}1", fname) or "exhibit991" in fname:
                return f"https://www.sec.gov{href}" if href.startswith("/") else href

        # Priority 2: pr/press/release/earnings keyword
        for fname, href in candidates:
            if any(kw in fname for kw in ["pr.htm", "press", "release", "earnings"]):
                return f"https://www.sec.gov{href}" if href.startswith("/") else href

        # Priority 3: ilk non-primary htm (8-K body'sini at)
        # Primary doc genelde ticker-tarih.htm formatında
        for fname, href in candidates:
            if not re.match(r"^[a-z]+-\d{8}\.htm$", fname):
                return f"https://www.sec.gov{href}" if href.startswith("/") else href

        return None
    except Exception:
        return None


def fetch_press_release_text(url: str) -> Optional[str]:
    """SEC.gov'dan press release'i fetch et + HTML temizle."""
    try:
        r = requests.get(url, headers=SEC_HEADERS_WWW, timeout=30)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "head", "meta"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        return text
    except Exception:
        return None
