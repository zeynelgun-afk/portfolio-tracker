# -*- coding: utf-8 -*-
"""
JUDGEMENT REVIEW — LLM kararlarinin post-mortem analizi
==========================================================
logs/exit_judgement.jsonl'i okuyup:
1. Toplam karar sayisi
2. Layer kullanim dagilimi (kural / llm / fallback)
3. Celiski oran
4. LLM kararlari ile gerceklesen sonucu karsilastir (5g/10g sonra fiyat)

Kullanim:
  python scripts/judgement_review.py            # Konsola
  python scripts/judgement_review.py --markdown # MD rapor
"""
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter

REPO_ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))


def yukle_kararlar() -> list:
    log_path = REPO_ROOT / "logs" / "exit_judgement.jsonl"
    if not log_path.exists():
        return []
    kararlar = []
    with open(log_path) as f:
        for line in f:
            try:
                kararlar.append(json.loads(line))
            except Exception:
                continue
    return kararlar


def analiz(kararlar: list) -> dict:
    if not kararlar:
        return {"toplam": 0}
    
    layers = Counter(k.get("layer_used", "?") for k in kararlar)
    actions = Counter(k.get("final_action", "?") for k in kararlar)
    semboller = Counter(k.get("sembol", "?") for k in kararlar)
    portfoyler = Counter(k.get("portfoy", "?") for k in kararlar)
    
    celiski_var = sum(1 for k in kararlar if k.get("celiski"))
    
    # LLM kararlari icin: kural ne dedi vs LLM ne dedi
    llm_kararlar = [k for k in kararlar if k.get("layer_used") == "llm"]
    llm_aciklama = []
    for k in llm_kararlar:
        kural = k.get("kural_action")
        llm = k.get("final_action")
        if kural != llm:
            llm_aciklama.append({
                "sembol": k.get("sembol"),
                "kural": kural,
                "llm": llm,
                "tarih": k.get("tarih", "")[:10],
                "reasoning": k.get("reasoning", "")[:120],
            })
    
    return {
        "toplam": len(kararlar),
        "layer_dagilim": dict(layers),
        "action_dagilim": dict(actions),
        "celiski_orani": round(celiski_var / len(kararlar) * 100, 1),
        "en_cok_sembol": semboller.most_common(5),
        "portfoy_dagilim": dict(portfoyler),
        "llm_kural_farkli": len(llm_aciklama),
        "llm_kararlar_detay": llm_aciklama[:10],
    }


def rapor_yazdir(s: dict):
    if s["toplam"] == 0:
        print("Henuz judgement kaydi yok.")
        return
    
    print(f"=" * 60)
    print(f"JUDGEMENT REVIEW — {s['toplam']} kayit")
    print(f"=" * 60)
    print()
    print(f"Layer dagilim:")
    for k, v in s["layer_dagilim"].items():
        pct = v / s['toplam'] * 100
        print(f"  {k:18}: {v:>4} (%{pct:.1f})")
    print()
    print(f"Action dagilim:")
    for k, v in s["action_dagilim"].items():
        print(f"  {k:18}: {v:>4}")
    print()
    print(f"Celiski orani: %{s['celiski_orani']:.1f}")
    print()
    if s["llm_kural_farkli"]:
        print(f"LLM kuraldan farkli karar verdi: {s['llm_kural_farkli']} kez")
        print()
        print("Detay (ilk 10):")
        for d in s["llm_kararlar_detay"]:
            print(f"  {d['tarih']} {d['sembol']:6} | kural:{d['kural']} → llm:{d['llm']}")
            print(f"           {d['reasoning']}")
    print()
    print(f"En cok sembol: {s['en_cok_sembol']}")
    print(f"Portfoy: {s['portfoy_dagilim']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    
    kararlar = yukle_kararlar()
    s = analiz(kararlar)
    rapor_yazdir(s)


if __name__ == "__main__":
    main()
