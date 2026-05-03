#!/usr/bin/env python3
"""
Finzora — Prompt Evolver
=========================
Darwin evolution sonuçlarını docs/K_RULES_QUICK_REF.md ve
agent/memory/prompt_genome.json'a geri yazar.
Prompt dosyaları kaldırıldı — kurallar genome'da yaşar.
"""
import json
import re
from datetime import datetime
from pathlib import Path
import pytz

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")


def sync_genome_to_kref(genome: dict):
    """
    Evrimleşen kuralları docs/K_RULES_QUICK_REF.md'e yazar.
    Sadece v2+ kurallar (değişmiş olanlar) güncellenir.
    """
    kref = REPO_ROOT / "docs" / "K_RULES_QUICK_REF.md"
    if not kref.exists():
        return

    content = kref.read_text(encoding="utf-8")
    updated = 0

    for rule_name, data in genome.items():
        if data.get("version", 1) <= 1:
            continue  # Hiç evrimleşmemiş, atla

        # K-XX formatını çıkar
        match = re.search(r"K[-_](\d+)", rule_name)
        if not match:
            continue

        k_num = match.group(1)
        prompt_first_line = data["current_prompt"].split("\n")[0].strip()
        tarih = data.get("last_modified", "?")

        # QUICK_REF'te ilgili satırı bul ve güncelle
        pattern = rf"(\*\*K-{k_num}\*\*.*?\|)(.*?)(\|)"
        new_line = rf"\1 {prompt_first_line[:60]} [Darwin v{data['version']} {tarih}] \3"
        new_content = re.sub(pattern, new_line, content, count=1)

        if new_content != content:
            content = new_content
            updated += 1

    if updated:
        kref.write_text(content, encoding="utf-8")
        print(f"[PromptEvolver] K_RULES_QUICK_REF güncellendi: {updated} kural")


def propose_improvement(rule_name: str, failure_summary: str) -> str:
    """
    Bir kural başarısız olduğunda Claude'dan iyileştirme iste.
    Learning engine tarafından çağrılır.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from claude_agent import get_claude_decision

    genome_path = MEMORY_DIR / "prompt_genome.json"
    genome = json.load(open(genome_path)) if genome_path.exists() else {}
    mevcut = genome.get(rule_name, {}).get("current_prompt", "Kural bulunamadı")

    prompt = f"""A rule in the Finzora trading system is underperforming.

RULE: {rule_name}
CURRENT DEFINITION:
{mevcut}

FAILURE/PERFORMANCE SUMMARY:
{failure_summary}

TASK: propose a better rule definition.
Return ONLY this JSON (keys exactly as shown):
{{"yeni_prompt": "Turkish — new rule text, 2-4 lines", "gerekce": "Turkish — why it is better"}}"""

    response = get_claude_decision(prompt, mode="weekly")
    try:
        m = re.search(r'\{.*\}', response, re.DOTALL)
        if m:
            return json.loads(m.group()).get("yeni_prompt", "")
    except Exception:
        pass
    return ""


def update_genome_rule(rule_name: str, new_prompt: str):
    """
    Genome'da bir kuralı güncelle. Darwin'den veya learning engine'den çağrılır.
    """
    genome_path = MEMORY_DIR / "prompt_genome.json"
    if not genome_path.exists():
        return

    genome = json.load(open(genome_path))
    if rule_name not in genome:
        return

    genome[rule_name]["previous_prompt"] = genome[rule_name]["current_prompt"]
    genome[rule_name]["current_prompt"]  = new_prompt
    genome[rule_name]["version"]         = genome[rule_name].get("version", 1) + 1
    genome[rule_name]["last_modified"]   = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    json.dump(genome, open(genome_path, "w"), ensure_ascii=False, indent=2)

    # K_RULES_QUICK_REF'e de yaz
    sync_genome_to_kref(genome)
    print(f"[PromptEvolver] {rule_name} güncellendi v{genome[rule_name]['version']}")


if __name__ == "__main__":
    # Mevcut genome'u K_RULES ile senkronize et
    genome_path = MEMORY_DIR / "prompt_genome.json"
    if genome_path.exists():
        genome = json.load(open(genome_path))
        sync_genome_to_kref(genome)
        print(f"Senkronize edildi: {len(genome)} kural")
