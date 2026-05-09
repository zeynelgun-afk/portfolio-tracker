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
import argparse
import requests
from datetime import datetime, date

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
# Genişletilebilir, başlangıç seti:
NON_CALENDAR_FISCAL = {
    "BILL": {"fiscal_year_end_month": 6, "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2}},
    "HUBS": {"fiscal_year_end_month": 12, "calendar_to_fiscal_q": {1: 1, 2: 2, 3: 3, 4: 4}},  # actually calendar
    "CRM":  {"fiscal_year_end_month": 1, "calendar_to_fiscal_q": {1: 4, 2: 1, 3: 2, 4: 3}},
    "ORCL": {"fiscal_year_end_month": 5, "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2}},
    "ADBE": {"fiscal_year_end_month": 11, "calendar_to_fiscal_q": {1: 1, 2: 2, 3: 3, 4: 4}},  # close to calendar
    "NKE":  {"fiscal_year_end_month": 5, "calendar_to_fiscal_q": {1: 3, 2: 4, 3: 1, 4: 2}},
    "CSCO": {"fiscal_year_end_month": 7, "calendar_to_fiscal_q": {1: 2, 2: 4, 3: 1, 4: 2}},
    "WMT":  {"fiscal_year_end_month": 1, "calendar_to_fiscal_q": {1: 4, 2: 1, 3: 2, 4: 3}},
}


def fmp_get(endpoint, params=None):
    if params is None:
        params = {}
    params["apikey"] = API_KEY
    try:
        r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fiscal_quarter_for_calendar(symbol, calendar_quarter):
    """Verilen takvim çeyreğine karşılık gelen fiscal quarter."""
    fc = NON_CALENDAR_FISCAL.get(symbol)
    if fc:
        return fc["calendar_to_fiscal_q"].get(calendar_quarter, calendar_quarter)
    return calendar_quarter


# 4a) ANALİST REVİZE YÖN SAYIMI -------------------------------------------------

def analyst_revisions(symbol, earnings_date_str):
    """Bilanço sonrası analist hedef revize haberleri."""
    pt_news = fmp_get("price-target-news", {"symbol": symbol, "limit": 20})
    if not pt_news or not isinstance(pt_news, list):
        return {"raised": 0, "lowered": 0, "neutral": 0, "items": []}
    
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
        title = (n.get("newsTitle") or "").lower()
        new_pt = n.get("priceTarget") or n.get("adjPriceTarget") or 0
        old_pt = n.get("priceWhenPosted") or 0
        analyst = n.get("analystName") or n.get("analystCompany") or "N/A"
        
        if "raise" in title or "boost" in title or "upgrade" in title:
            direction = "RAISED"
            raised += 1
        elif "lower" in title or "cut" in title or "downgrade" in title or "reduce" in title:
            direction = "LOWERED"
            lowered += 1
        else:
            direction = "NEUTRAL"
            neutral += 1
        
        items.append({
            "date": pub,
            "analyst": analyst,
            "new_target": new_pt,
            "prior_price": old_pt,
            "direction": direction,
            "title": n.get("newsTitle"),
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

GUIDANCE_KEYWORDS = {
    'guidance': 3, 'outlook': 3, 'reaffirm': 3, 'raise': 3, 'midpoint': 3,
    'partnership': 3, 'anthropic': 5,
    'expect': 2, 'forecast': 2, 'project': 2, 'lower': 2,
    'fiscal year': 2, 'full year': 2, 'second quarter': 2, '2027': 2,
    'q2': 1, 'q3': 1, 'q4': 1, '2026': 1, 'range': 1,
}


def extract_guidance(content, max_n=12, min_score=4):
    """Transcript metninden guidance/forward-looking cümleleri extract et."""
    if not content:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', content)
    scored = []
    for s in sentences:
        s = s.strip()
        if len(s) < 30 or len(s) > 800:
            continue
        s_lower = s.lower()
        score = sum(weight for k, weight in GUIDANCE_KEYWORDS.items() if k in s_lower)
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
    fiscal_q = fiscal_quarter_for_calendar(symbol, calendar_quarter)
    t = fmp_get("earning-call-transcript", {"symbol": symbol, "year": year, "quarter": fiscal_q})
    if not t or not isinstance(t, list) or len(t) == 0:
        # Belki calendar_quarter de denenmeli
        if fiscal_q != calendar_quarter:
            t = fmp_get("earning-call-transcript", {"symbol": symbol, "year": year, "quarter": calendar_quarter})
            if not t or not isinstance(t, list) or len(t) == 0:
                return {"available": False, "reason": "transcript_yok"}
        else:
            return {"available": False, "reason": "transcript_yok"}
    
    item = t[0]
    content = item.get("content", "")
    date = item.get("date", "")
    
    if not content:
        return {"available": False, "reason": "icerik_bos"}
    
    guidance_sentences = extract_guidance(content, max_n=12)
    
    # Verdikt: cümlelerde anahtar kelimeler ara
    full_lower = content.lower()
    has_raise = "raising the midpoint" in full_lower or "raised our" in full_lower or "increasing the" in full_lower or "we are raising" in full_lower
    has_reaffirm = "reaffirm" in full_lower
    has_lower = "lowering our" in full_lower or "we are lowering" in full_lower
    
    if has_raise:
        verdict = "RAISED"
    elif has_lower:
        verdict = "LOWERED"
    elif has_reaffirm:
        verdict = "REAFFIRMED"
    else:
        verdict = "QUALITATIVE_ONLY"  # CELH örneği
    
    return {
        "available": True,
        "date": date,
        "fiscal_quarter": fiscal_q,
        "calendar_quarter": calendar_quarter,
        "content_length": len(content),
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
            print(f"  Transcript: {ts['verdict']} ({ts['content_length']} char, fiscal Q{ts['fiscal_quarter']})")
        else:
            print(f"  Transcript: {ts.get('reason', 'yok')}")
        
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
