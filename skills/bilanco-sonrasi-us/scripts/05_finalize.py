#!/usr/bin/env python3
"""
Aşama 5: Final Sıralama ve Yıldız Skor

Her shortlist hissesi için 5 yıldızlı skorlama:
  +1: Adil değer +30%+ analist hedefli
  +1: Şirket guidance RAISED (transcript veya 8-K)
  +1: Net analist target raised > lowered (post-earnings)
  +1: 13F shares net birikim Q-1 (>+1M)
  +1: Smart money portföyünde

Kullanım:
    python 05_finalize.py --in 04_signals_enriched.json --out 05_final_ranked.json --top 10

Çıktı: 05_final_ranked.json
"""
import sys
import json
import argparse


def calculate_stars(stock):
    """Hisse için 5 yıldızlı kompozit skor."""
    sigs = stock.get("post_earnings_signals", {})
    stars = 0
    reasons = []
    
    # ★ 1: Analist hedef +30%+ upside (analyst_target_upside zaten en az +25 sağlamlık filtresinde)
    upside = stock.get("analyst_target_upside", 0)
    if upside >= 30:
        stars += 1
        reasons.append(f"Analist hedef +{upside:.0f}% upside")
    
    # ★ 2: Şirket guidance — transcript VEYA 8-K press release RAISED
    # (transcript yayınlanmadan önce 8-K kullanılır, ikisi de varsa transcript öncelikli)
    ts = sigs.get("transcript", {})
    pr = sigs.get("press_release", {})
    
    raised_in_transcript = ts.get("verdict") == "RAISED"
    raised_in_press_release = pr.get("verdict") == "RAISED"
    reaffirmed_with_hint = False
    
    if ts.get("verdict") == "REAFFIRMED":
        sentences = ts.get("guidance_sentences", [])
        upside_hint_phrases = [
            "below many third-party", "below most analyst", "conservatively",
            "expect to update", "plan to update", "following the closing",
            "incremental upside", "additional opportunity", "midpoint opportunity",
            "visible upside", "above the midpoint", "trending toward the high end",
        ]
        reaffirmed_with_hint = any(
            any(p in s.get("text", "").lower() for p in upside_hint_phrases)
            for s in sentences
        )
    
    if raised_in_transcript:
        stars += 1
        reasons.append("CFO/CEO 'raising guidance' söyledi (transcript)")
    elif raised_in_press_release and not raised_in_transcript:
        # Transcript yok ama 8-K'da RAISED varsa
        stars += 1
        reasons.append(f"8-K {pr.get('form_type', '8-K')} press release: 'raising guidance' (transcript henüz yok)")
    elif reaffirmed_with_hint:
        stars += 1
        reasons.append("Reaffirmed guidance + upside hint (yönetim conservative)")
    # LOWERED veya QUALITATIVE_ONLY için yıldız yok
    
    # ★ 3: Net analyst target raised > lowered (post-earnings)
    rev = sigs.get("analyst_revisions", {})
    raised = rev.get("raised", 0)
    lowered = rev.get("lowered", 0)
    if raised > 0 and (lowered == 0 or raised >= 2 * lowered):
        stars += 1
        reasons.append(f"Analist net raise: {raised}↑ vs {lowered}↓")
    
    # ★ 4: 13F shares net birikim — mcap'a göre normalize
    inst = sigs.get("institutional", {})
    shares_change = inst.get("numberOf13FsharesChange", 0) or 0
    mcap = stock.get("mcap", 0) or 0
    price = stock.get("price", 0) or 0
    
    # Threshold: total shares outstanding'in en az %0.3'ü kadar birikim
    # (mcap büyüdükçe absolute threshold da büyür, küçük caps korunur)
    shares_outstanding = (mcap / price) if price > 0 else 0
    threshold_pct = 0.003  # %0.3
    threshold_shares = max(shares_outstanding * threshold_pct, 500_000)  # min 500K
    
    if shares_change >= threshold_shares:
        stars += 1
        pct = (shares_change / shares_outstanding * 100) if shares_outstanding > 0 else 0
        reasons.append(f"13F birikim +{shares_change/1e6:.1f}M shares ({pct:.2f}% of outstanding)")
    elif inst.get("verdict") == "ACCUMULATION" and shares_change > 0:
        # Yeni isim girişi + birikim, küçük olsa bile pozitif sinyal
        stars += 1
        reasons.append(f"13F: yeni yatırımcı girişi (+{inst.get('investorsHoldingChange', 0)} isim) + birikim")
    
    # ★ 5: Smart money portföyünde
    sm = sigs.get("smart_money_owners") or []
    if sm:
        stars += 1
        reasons.append(f"Smart money: {', '.join(sm)}")
    
    return stars, reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="04_signals_enriched.json")
    ap.add_argument("--out", default="05_final_ranked.json")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    
    with open(args.inp) as f:
        enriched = json.load(f)
    
    # Yıldız hesapla
    for s in enriched:
        stars, reasons = calculate_stars(s)
        s["stars"] = stars
        s["star_reasons"] = reasons
    
    # Şartı sağlamayanları ele: STRONG_LOWER veya CAPITULATION → yıldıza bakma, çıkar
    survivors = []
    eliminated = []
    for s in enriched:
        sigs = s.get("post_earnings_signals", {})
        rev_verdict = sigs.get("analyst_revisions", {}).get("verdict", "")
        ts_verdict = sigs.get("transcript", {}).get("verdict") if sigs.get("transcript", {}).get("available") else None
        pr_verdict = sigs.get("press_release", {}).get("verdict") if sigs.get("press_release", {}).get("available") else None
        
        if rev_verdict in ("CAPITULATION", "STRONG_LOWER", "NET_LOWER"):
            s["elimination_reason"] = f"Analist {rev_verdict}"
            eliminated.append(s)
        elif ts_verdict == "LOWERED":
            s["elimination_reason"] = "Transcript LOWERED guidance"
            eliminated.append(s)
        elif pr_verdict == "LOWERED" and ts_verdict not in ("RAISED", "REAFFIRMED"):
            # Press release LOWERED + transcript pozitif değilse ele
            # (transcript RAISED/REAFFIRMED ise press release lowered çelişkili olabilir, transcript öncelikli)
            s["elimination_reason"] = "8-K press release LOWERED guidance"
            eliminated.append(s)
        else:
            survivors.append(s)
    
    # Sırala: yıldız → upside
    survivors.sort(key=lambda x: (-x["stars"], -x.get("analyst_target_upside", 0)))
    final = survivors[:args.top]
    
    # Kaydet
    out = {
        "date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
        "final_ranked": final,
        "eliminated": eliminated,
        "watchlist": survivors[args.top:args.top+5],  # top sonrası ilk 5 izlemeye
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, default=str)
    
    # Konsol çıktısı
    print(f"\n{'='*80}")
    print(f"FİNAL SIRALAMA — Top {len(final)} (yıldız + upside'a göre)")
    print(f"{'='*80}\n")
    print(f"{'#':>3s} {'Sym':6s} {'★':>5s} {'Sektör':22s} {'Fiyat':>8s} {'Hedef':>8s} {'Üst%':>6s}")
    print("-" * 80)
    for i, s in enumerate(final, 1):
        stars_str = "★" * s["stars"] + "☆" * (5 - s["stars"])
        sector = (s.get("sector") or "")[:22]
        mv = s.get("method_values", {})
        target = mv.get("analyst_target", 0)
        print(f"{i:>3d} {s['symbol']:6s} {stars_str:>5s} {sector:22s} ${s['price']:>7.2f} ${target:>7.2f} {s.get('analyst_target_upside', 0):>5.1f}%")
        for reason in s["star_reasons"]:
            print(f"     • {reason}")
        print()
    
    if eliminated:
        print(f"\n--- ELENDI ({len(eliminated)}) ---")
        for s in eliminated:
            print(f"  {s['symbol']:6s} — {s['elimination_reason']}")
    
    print(f"\nKaydedildi: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
