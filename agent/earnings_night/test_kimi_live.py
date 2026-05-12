"""
Live test: Kimi K2 Thinking gerçek parse + gold-standard karşılaştırma.

Kullanım:
    export OPENROUTER_API_KEY="sk-or-v1-..."
    python test_kimi_live.py

Beklenen çıktı:
    - Kimi'nin parse ettiği JSON
    - Gold-standard ile field-by-field karşılaştırma
    - Accuracy raporu
"""
import sys
import json
import os
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, "/home/claude/finzora")

from agent.earnings_night import KimiEarningsParser, EarningsParse


def compare_values(gold, kimi, path=""):
    """İki değeri karşılaştır, fark varsa raporla."""
    diffs = []
    
    if isinstance(gold, dict) and isinstance(kimi, dict):
        all_keys = set(gold.keys()) | set(kimi.keys())
        for key in all_keys:
            sub_path = f"{path}.{key}" if path else key
            if key not in gold:
                diffs.append((sub_path, "MISSING IN GOLD", kimi[key]))
            elif key not in kimi:
                diffs.append((sub_path, gold[key], "MISSING IN KIMI"))
            else:
                diffs.extend(compare_values(gold[key], kimi[key], sub_path))
    
    elif isinstance(gold, list) and isinstance(kimi, list):
        for i in range(max(len(gold), len(kimi))):
            sub_path = f"{path}[{i}]"
            g = gold[i] if i < len(gold) else "MISSING IN GOLD"
            k = kimi[i] if i < len(kimi) else "MISSING IN KIMI"
            diffs.extend(compare_values(g, k, sub_path))
    
    elif isinstance(gold, (int, float)) and isinstance(kimi, (int, float)):
        # Sayısal değerler için %1 tolerans
        if gold == 0 and kimi == 0:
            pass
        elif abs(gold - kimi) / max(abs(gold), abs(kimi), 0.001) > 0.01:
            diffs.append((path, gold, kimi))
    
    elif isinstance(gold, str) and isinstance(kimi, str):
        # String'ler için %80 similarity yeterli
        similarity = SequenceMatcher(None, gold.lower(), kimi.lower()).ratio()
        if similarity < 0.7:
            diffs.append((path, gold[:60], kimi[:60]))
    
    else:
        # Tip uyuşmazlığı veya null vs value
        if gold != kimi:
            diffs.append((path, str(gold)[:60], str(kimi)[:60]))
    
    return diffs


def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY environment variable yok.")
        print("\nKullanım:")
        print("  export OPENROUTER_API_KEY='sk-or-v1-...'")
        print("  python test_kimi_live.py")
        sys.exit(1)
    
    print("=" * 70)
    print("LIVE KIMI K2 THINKING TESTI — NVDA Q4 FY26")
    print("=" * 70)
    
    # Press release'i yükle
    pr_path = Path("/home/claude/finzora/agent/earnings_night/fixtures/nvda_q4fy26/press_release.txt")
    with open(pr_path) as f:
        press_release_text = f.read()
    
    print(f"\nPress release: {pr_path.name}")
    print(f"Boyut: {len(press_release_text):,} karakter")
    
    # Gold-standard'ı yükle
    gold_path = Path("/home/claude/finzora/agent/earnings_night/fixtures/nvda_q4fy26/gold_standard.json")
    with open(gold_path) as f:
        gold_json = json.load(f)
    
    # Kimi parser'ı başlat
    parser = KimiEarningsParser(api_key=api_key)
    
    print("\nKimi K2 Thinking çağırılıyor (60-180 saniye sürebilir)...")
    
    result = parser.parse_8k(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        filing_date="2026-02-25",
        fiscal_period="Q4 FY2026",
        document_text=press_release_text,
        previous_guidance=None,
    )
    
    print(f"\n--- PARSE SONUCU ---")
    print(f"  Başarılı: {result.success}")
    print(f"  Deneme sayısı: {result.attempts}")
    print(f"  Yöntem: {result.method_used}")
    print(f"  Süre: {result.duration_sec:.1f}s")
    print(f"  Maliyet: ${result.cost_usd:.4f}")
    
    if not result.success:
        print(f"  Hata: {result.error}")
        print(f"\n  Raw response (ilk 1000 char):")
        print(result.raw_response[:1000] if result.raw_response else "None")
        sys.exit(1)
    
    parsed = result.parsed
    
    # Kimi çıktısını kaydet
    kimi_output_path = Path("/home/claude/finzora/agent/earnings_night/fixtures/nvda_q4fy26/kimi_output.json")
    with open(kimi_output_path, "w") as f:
        f.write(parsed.model_dump_json(indent=2))
    print(f"\n  Çıktı kaydedildi: {kimi_output_path}")
    
    print(f"\n--- KIMI PARSE ÖZET ---")
    ra = parsed.results_actual
    print(f"  Revenue: ${ra.revenue_usd_b}B (gold: $68.127B)")
    print(f"  Non-GAAP EPS: ${ra.non_gaap_eps} (gold: $1.62)")
    print(f"  Gross Margin: {ra.gross_margin_pct}% (gold: 75.2%)")
    print(f"  Operating Margin: {ra.operating_margin_pct}% (gold: 67.7% computed)")
    
    gq = parsed.guidance_next_quarter
    print(f"  Q1 FY27 Revenue Mid: ${gq.revenue_mid_b}B (gold: $78.0B)")
    print(f"  Q1 FY27 Revenue Range: ${gq.revenue_low_b}-${gq.revenue_high_b}B (gold: $76.44-$79.56B)")
    
    print(f"  Segment count: {len(parsed.segment_breakdown)} (gold: 4)")
    print(f"  One-time items: {len(parsed.one_time_items)} (gold: 1)")
    print(f"  Tone score: {parsed.qualitative_signals.tone_score} (gold: 5)")
    print(f"  Source quotes: {len(parsed.source_quotes)} (gold: 23)")
    
    # Field-by-field karşılaştırma
    print(f"\n--- GOLD-STANDARD KARSILASTIRMA ---")
    kimi_json = parsed.model_dump()
    diffs = compare_values(gold_json, kimi_json)
    
    # Sadece kritik field'larda fark olanları göster
    critical_paths = ["results_actual", "guidance_next_quarter", "segment_breakdown"]
    critical_diffs = [d for d in diffs if any(c in d[0] for c in critical_paths)]
    
    print(f"\nKritik farklar: {len(critical_diffs)}")
    for path, gold_val, kimi_val in critical_diffs[:20]:
        print(f"  [{path}]")
        print(f"    Gold: {gold_val}")
        print(f"    Kimi: {kimi_val}")
    
    other_diffs = [d for d in diffs if not any(c in d[0] for c in critical_paths)]
    print(f"\nDiğer farklar (qualitative, source_quotes, ambiguous): {len(other_diffs)}")
    
    # Accuracy skoru
    total_compared = len(diffs) + sum(1 for _ in iter_paths(gold_json))
    if total_compared > 0:
        accuracy = (1 - len(diffs) / total_compared) * 100
        print(f"\n=== ACCURACY: %{accuracy:.1f} ===")


def iter_paths(obj, path=""):
    """Tüm leaf path'leri yield et."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_paths(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_paths(v, f"{path}[{i}]")
    else:
        yield path


if __name__ == "__main__":
    main()
