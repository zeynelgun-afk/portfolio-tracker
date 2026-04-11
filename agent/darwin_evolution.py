#!/usr/bin/env python3
"""
Finzora Agent — Darwinian Prompt Evolution (ATLAS tarzı)
==========================================================
Her 5 işlem gününde en zayıf performanslı K-kuralını tespit eder.
Claude'a yeni bir prompt (kural versiyonu) yazdırır.
14 gün test eder. İyileşirse git commit, kötüleşirse git revert.

ATLAS'tan farkımız:
  - Agent sayısı değil, K-kural promtlarını evrimleştiriyoruz
  - Fitness function: Sharpe oranı değil, win_rate × avg_pnl
  - Her kural kendi versiyonunu tutar (v1, v2, v3...)
  - Tüm değişiklikler git geçmişinde izlenebilir

Dosyalar:
  agent/memory/prompt_genome.json  → Her kuralın mevcut prompt versiyonu
  agent/memory/evolution_log.json  → Deneme geçmişi
  agent/memory/fitness_scores.json → Kural performans skorları
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")
MEMORY_DIR.mkdir(exist_ok=True)

# Evrimleştirilebilir K-kuralları ve başlangıç promptları
INITIAL_GENOME = {
    "K-11_trailing_stop": {
        "version": 1,
        "description": "Trailing stop tetikleme koşulu",
        "weight": 1.0,           # Darwinian ağırlık: 0.3 (min) → 2.5 (max)
        "weight_history": [],    # Günlük ağırlık geçmişi
        "current_prompt": """K-11 Trailing Stop: 
Pozisyon zirveden 2×ATR aşağı düşerse trailing stop tetiklenir.
Makro şok istisnası: SPY ≥%3 düşüş + VIX ≥%20 spike aynı gün → 1 gün bekle.""",
        "fitness": None,
        "last_modified": None,
    },
    "K-11_partial_sell": {
        "version": 1,
        "description": "Kısmi kâr alma tetikleme koşulu",
        "weight": 1.0,
        "weight_history": [],
        "current_prompt": """K-11 Kısmi Kâr Alma:
Katman 1: RSI 70+ VE kâr %15+ → trailing stop aktif
Katman 2: RSI 80+ VEYA (RSI 75+ + negatif div/20SMA altı) → %25-30 sat
Katman 3: 50SMA altı kapanış VEYA chandelier trailing → TAM ÇIK""",
        "fitness": None,
        "last_modified": None,
    },
    "K-13_vix_threshold": {
        "version": 1,
        "description": "VIX bazlı pozisyon boyutu",
        "weight": 1.0,
        "weight_history": [],
        "current_prompt": """K-13 VIX Kuralı:
Faydalanıcı sektörler (savunma, enerji, altın): VIX 28'e kadar tam pozisyon
Duyarlı sektörler (tech, growth): VIX 22'den itibaren yarım pozisyon
VIX>35: tüm yeni girişler dur""",
        "fitness": None,
        "last_modified": None,
    },
    "K-04_entry_filter": {
        "version": 1,
        "description": "Giriş filtresi - SMA ve RSI",
        "weight": 1.0,
        "weight_history": [],
        "current_prompt": """K-04 Giriş Filtresi:
Standart: Giriş fiyatı SMA50 üstünde olmalı
İstisna: RSI<30 + stabilizasyon + pozitif katalizör → çeyrek pozisyon
Yasak: SMA50+SMA200 altı + insider satış yoğun → giriş yok""",
        "fitness": None,
        "last_modified": None,
    },
    "swing_rsi_range": {
        "version": 1,
        "description": "Swing giriş RSI aralığı",
        "weight": 1.0,
        "weight_history": [],
        "current_prompt": """Swing Giriş RSI:
RSI 40-65 arası giriş bölgesi
RSI<40: oversold bounce için çeyrek pozisyon
RSI>65: momentum trade sadece güçlü trend varlığında""",
        "fitness": None,
        "last_modified": None,
    },
}

WEIGHT_MIN  = 0.3
WEIGHT_MAX  = 2.5
WEIGHT_UP   = 1.05   # Üst çeyrek: günlük ×1.05
WEIGHT_DOWN = 0.95   # Alt çeyrek: günlük ×0.95


# ── Fitness Hesaplama ─────────────────────────────────────────────────────────

def load_all_transactions() -> list:
    """
    transactions.csv'den tüm işlemleri yükler.
    Alış-satış eşleştirmesi yaparak P/L hesaplar.
    """
    import csv
    tx_path = REPO_ROOT / "data" / "transactions.csv"
    if not tx_path.exists():
        return []

    rows = []
    with open(tx_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Alış fiyatlarını sembol bazında tut
    buy_history = {}
    trades = []

    for row in rows:
        action = row.get("action", "").upper()
        symbol = row.get("symbol", "")
        price  = float(row.get("price", 0) or 0)
        reason = row.get("reason", "")

        if action == "BUY" and price > 0:
            if symbol not in buy_history:
                buy_history[symbol] = []
            buy_history[symbol].append(price)

        elif action in ("SELL", "SATIŞ") and price > 0 and symbol in buy_history:
            buy_prices = buy_history.get(symbol, [])
            if buy_prices:
                avg_buy = sum(buy_prices) / len(buy_prices)
                pnl_pct = (price - avg_buy) / avg_buy * 100
                trades.append({
                    "symbol":  symbol,
                    "action":  action,
                    "price":   price,
                    "reason":  reason,
                    "pnl_pct": round(pnl_pct, 2),
                    "date":    row.get("date", ""),
                })

    return trades


def calculate_fitness(rule_name: str, transactions: list) -> dict:
    """
    Bir K-kuralının fitness skorunu hesaplar.
    
    ATLAS yöntemi: Rolling Sharpe proxy
    Fitness = (avg_pnl / std_dev) × win_rate
    
    Neden bu daha iyi?
    - win_rate × avg_pnl: %100 win rate, +%0.1 avg = iyi görünür ama aslında kötü
    - Sharpe: Hem getiri hem tutarlılık (volatilite) ölçülür
    - Volatilitesi düşük, tutarlı getirili kural > yüksek volatilite
    """
    rule_trades = []

    for t in transactions:
        reason = (t.get("reason") or "").lower()
        pnl    = t.get("pnl_pct", 0) or 0

        matched = False
        if rule_name == "K-11_trailing_stop":
            matched = "trailing stop" in reason or "izleyen zarar kes" in reason
        elif rule_name == "K-11_partial_sell":
            matched = "k-11" in reason or (
                ("kısmi kâr" in reason or "kismi kar" in reason) and "rsi" in reason
            )
        elif rule_name == "K-13_vix_threshold":
            matched = "k-13" in reason or (
                "vix" in reason and ("pozisyon" in reason or "kriz" in reason)
            )
        elif rule_name == "K-04_entry_filter":
            matched = "k-04" in reason or (
                "sma" in reason and "giriş" in reason
            )
        elif rule_name == "swing_rsi_range":
            matched = "rsi" in reason and (
                "swing" in reason or "oversold" in reason or "aşırı satım" in reason
            )

        if matched:
            rule_trades.append(float(pnl))

    if not rule_trades:
        return {"fitness": None, "n": 0, "win_rate": None, "avg_pnl": None, "sharpe": None}

    n        = len(rule_trades)
    wins     = sum(1 for p in rule_trades if p > 0)
    win_rate = wins / n
    avg_pnl  = sum(rule_trades) / n

    # Standart sapma (volatilite)
    variance = sum((p - avg_pnl) ** 2 for p in rule_trades) / n if n > 1 else 1.0
    std_dev  = variance ** 0.5 if variance > 0 else 1.0

    # Sharpe proxy (risk-free rate = 0 varsayımı)
    sharpe = avg_pnl / std_dev if std_dev > 0 else 0

    # Nihai fitness: Sharpe × win_rate (hem kalite hem tutarlılık)
    fitness = sharpe * win_rate

    return {
        "fitness":   round(fitness, 4),
        "n":         n,
        "win_rate":  round(win_rate * 100, 1),
        "avg_pnl":   round(avg_pnl, 2),
        "std_dev":   round(std_dev, 2),
        "sharpe":    round(sharpe, 3),
    }


# ── Genome Yönetimi ───────────────────────────────────────────────────────────

def load_genome() -> dict:
    path = MEMORY_DIR / "prompt_genome.json"
    if not path.exists():
        save_genome(INITIAL_GENOME)
        return INITIAL_GENOME.copy()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_genome(genome: dict):
    path = MEMORY_DIR / "prompt_genome.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(genome, f, ensure_ascii=False, indent=2)


def update_fitness_scores(genome: dict, transactions: list) -> dict:
    """Tüm kuralların fitness skorlarını günceller."""
    for rule_name in genome:
        fitness_data = calculate_fitness(rule_name, transactions)
        genome[rule_name]["fitness"] = fitness_data.get("fitness")
        genome[rule_name]["fitness_detail"] = fitness_data
    return genome


def update_darwin_weights(genome: dict) -> dict:
    """
    ATLAS Darwinian ağırlık sistemi:
    - Üst çeyrek fitness → ağırlık ×1.05 (daha yüksek ses)
    - Alt çeyrek fitness → ağırlık ×0.95 (susturulur)
    - Min: 0.3, Max: 2.5
    
    İyi agentlar daha güçlü konuşur.
    Kötü agentlar susmaz ama fısıldar.
    """
    # Fitness skorlarını topla
    scored = {
        name: data["fitness"]
        for name, data in genome.items()
        if data.get("fitness") is not None
    }

    if len(scored) < 2:
        return genome  # Yeterli veri yok

    fitnesses  = list(scored.values())
    fitnesses.sort()
    n          = len(fitnesses)
    q1_thresh  = fitnesses[n // 4]       # Alt çeyrek eşiği
    q3_thresh  = fitnesses[3 * n // 4]   # Üst çeyrek eşiği

    today = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    for name, data in genome.items():
        fitness = data.get("fitness")
        weight  = data.get("weight", 1.0)

        if fitness is None:
            continue

        # Ağırlık güncelle
        if fitness >= q3_thresh:
            new_weight = min(weight * WEIGHT_UP, WEIGHT_MAX)
        elif fitness <= q1_thresh:
            new_weight = max(weight * WEIGHT_DOWN, WEIGHT_MIN)
        else:
            new_weight = weight  # Orta grupta değişiklik yok

        genome[name]["weight"] = round(new_weight, 4)

        # Geçmiş tut (son 30)
        history = genome[name].get("weight_history", [])
        history.append({"date": today, "weight": new_weight, "fitness": fitness})
        genome[name]["weight_history"] = history[-30:]

    return genome


def get_weighted_genome_context(genome: dict) -> str:
    """
    Orchestrator için ağırlıklı kural özetini formatlar.
    Yüksek ağırlıklı kurallar daha belirgin.
    """
    lines = ["=== DARWIN AĞIRLIKLI K-KURALLARI ===\n"]

    # Ağırlığa göre sırala
    sorted_rules = sorted(
        genome.items(),
        key=lambda x: x[1].get("weight", 1.0),
        reverse=True
    )

    for name, data in sorted_rules:
        w       = data.get("weight", 1.0)
        fitness = data.get("fitness")
        v       = data.get("version", 1)
        pending = " ⏳" if data.get("pending_test") else ""

        bar     = "█" * int(w * 4)  # Görsel bar
        f_str   = f"fitness:{fitness:.3f}" if fitness else "fitness:N/A"

        # Yüksek ağırlıklı kurallara dikkat çek
        if w >= 2.0:
            prefix = "🔊 GÜÇLÜ"
        elif w >= 1.5:
            prefix = "📢 Normal"
        elif w <= 0.5:
            prefix = "🔇 ZAYIF"
        else:
            prefix = "📣 Orta"

        lines.append(f"{prefix} | {name} v{v}{pending}")
        lines.append(f"  Ağırlık: {w:.2f} {bar} | {f_str}")
        lines.append(f"  {data['current_prompt'].split(chr(10))[0][:80]}")
        lines.append("")

    return "\n".join(lines)
    """En düşük fitness'e sahip kuralı bulur."""
    scored = {
        name: data for name, data in genome.items()
        if data.get("fitness") is not None
    }

    if not scored:
        # Fitness verisi yoksa rastgele seç
        name = list(genome.keys())[0]
        return name, genome[name]

    weakest = min(scored.items(), key=lambda x: x[1]["fitness"])
    return weakest[0], weakest[1]


# ── Claude ile Evrim ──────────────────────────────────────────────────────────

def evolve_rule_with_claude(
    rule_name: str,
    current_rule: dict,
    transactions: list,
    analysis_context: str
) -> str:
    """
    Claude'a mevcut kuralı + performans verisini gönderir.
    Claude yeni bir prompt versiyonu önerir.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from claude_agent import get_claude_decision

    fitness = current_rule.get("fitness_detail", {})

    prompt = f"""
Sen Finzora Agent'sın. ATLAS tarzı Darwinian prompt evolution yapıyorsun.

MEVCUT KURAL: {rule_name}
MEVCUT PROMPT:
{current_rule['current_prompt']}

PERFORMANS VERİSİ:
  Fitness: {current_rule.get('fitness', 'N/A')}
  Trade sayısı: {fitness.get('n', 0)}
  Win rate: %{fitness.get('win_rate', 'N/A')}
  Ortalama P/L: %{fitness.get('avg_pnl', 'N/A')}

TRADE ANALİZİ BAĞLAMI:
{analysis_context[:1500]}

GÖREV:
1. Bu kuralın neden düşük performans verdiğini analiz et
2. Mevcut promptun zayıf noktalarını tespit et
3. Yeni bir prompt versiyonu öner

ÇIKTI FORMAT (SADECE JSON):
{{
  "analiz": "Kuralın neden zayıf olduğu",
  "degisiklik": "Ne değiştirilmeli",
  "yeni_prompt": "Yeni kural promptu (tam metin, Türkçe)",
  "beklenen_etki": "Bu değişikliğin win rate/P/L üzerindeki beklenen etkisi",
  "risk": "Bu değişikliğin riski"
}}
"""
    response = get_claude_decision(prompt, mode="weekly")

    # JSON parse
    try:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    return {"yeni_prompt": None, "analiz": response[:300]}


# ── Ana Evrim Döngüsü ─────────────────────────────────────────────────────────

def run_evolution_cycle(force: bool = False) -> dict:
    """
    Her 5 işlem gününde bir çalışır.
    En zayıf kuralı tespit eder → Claude'a yeni prompt yazdırır.
    """
    print("[Darwin] Evrim döngüsü başlatılıyor...")

    # Son evrim ne zaman çalıştı?
    evo_log_path = MEMORY_DIR / "evolution_log.json"
    evo_log = {"entries": []}
    if evo_log_path.exists():
        with open(evo_log_path, encoding="utf-8") as f:
            evo_log = json.load(f)

    last_run = None
    if evo_log["entries"]:
        last_run = evo_log["entries"][-1].get("date")

    today = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    if not force and last_run:
        last_dt   = datetime.strptime(last_run, "%Y-%m-%d")
        days_diff = (datetime.now(TR_TZ).replace(tzinfo=None) - last_dt).days
        if days_diff < 5:
            print(f"[Darwin] Son evrimden {days_diff} gün geçti (min 5). Atlandı.")
            return {"skipped": True, "reason": f"{days_diff} gün önce çalıştı"}

    # 1. Tüm transaction'ları yükle
    transactions = load_all_transactions()
    print(f"[Darwin] {len(transactions)} işlem yüklendi.")

    # 2. Genome yükle ve fitness güncelle
    genome = load_genome()
    genome = update_fitness_scores(genome, transactions)

    # 2b. Darwinian ağırlıkları güncelle
    genome = update_darwin_weights(genome)
    save_genome(genome)

    # 3. En zayıf kuralı bul
    weakest_name, weakest_rule = find_weakest_rule(genome)
    fitness_val = weakest_rule.get("fitness")

    print(f"[Darwin] En zayıf kural: {weakest_name} (fitness: {fitness_val})")

    # Fitness çok iyi ise evrim gerekmez
    if fitness_val is not None and fitness_val > 5.0:
        print(f"[Darwin] Fitness yeterli ({fitness_val} > 5.0). Evrim gerekmez.")
        return {"skipped": True, "reason": "Fitness yeterli", "fitness": fitness_val}

    # 4. Trade analizi bağlamını oluştur
    from backtester import format_backtest_for_claude, run_full_backtest
    backtest = run_full_backtest()
    analysis_ctx = format_backtest_for_claude(backtest)

    # 5. Claude ile evrim
    print(f"[Darwin] Claude'a {weakest_name} için yeni prompt isteniyor...")
    evolution = evolve_rule_with_claude(
        weakest_name, weakest_rule, transactions, analysis_ctx
    )

    new_prompt = evolution.get("yeni_prompt")
    if not new_prompt:
        print("[Darwin] Claude geçerli prompt üretemedi.")
        return {"error": "Prompt üretilemedi", "claude_response": evolution}

    # 6. Yeni versiyonu genome'a kaydet (eski versiyonu tut)
    old_version = genome[weakest_name]["version"]
    new_version = old_version + 1

    genome[weakest_name]["previous_prompt"]  = genome[weakest_name]["current_prompt"]
    genome[weakest_name]["current_prompt"]   = new_prompt
    genome[weakest_name]["version"]          = new_version
    genome[weakest_name]["last_modified"]    = today
    genome[weakest_name]["pending_test"]     = True
    genome[weakest_name]["test_start_date"]  = today
    genome[weakest_name]["test_end_date"]    = (
        datetime.now(TR_TZ) + timedelta(days=14)
    ).strftime("%Y-%m-%d")
    genome[weakest_name]["evolution_data"]   = evolution

    save_genome(genome)

    # 7. K-rules digest güncelle
    _update_k_rules_digest(genome)

    # 8. Log'a yaz
    log_entry = {
        "date":        today,
        "rule":        weakest_name,
        "old_version": old_version,
        "new_version": new_version,
        "old_fitness": fitness_val,
        "analiz":      evolution.get("analiz", "")[:200],
        "degisiklik":  evolution.get("degisiklik", "")[:200],
        "risk":        evolution.get("risk", "")[:100],
    }
    evo_log["entries"].append(log_entry)
    evo_log["entries"] = evo_log["entries"][-50:]  # Max 50 kayıt

    with open(evo_log_path, "w", encoding="utf-8") as f:
        json.dump(evo_log, f, ensure_ascii=False, indent=2)

    print(f"[Darwin] ✅ {weakest_name} v{old_version} → v{new_version}")
    return log_entry


# ── Evrim Sonuç Değerlendirmesi ───────────────────────────────────────────────

def evaluate_evolution_results() -> list:
    """
    Test süresi biten promtları değerlendirir.
    Fitness iyileştiyse → commit (kalıcı)
    Kötüleştiyse → revert (eski versiyona dön)
    """
    genome       = load_genome()
    transactions = load_all_transactions()
    today        = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    results      = []

    for rule_name, rule_data in genome.items():
        if not rule_data.get("pending_test"):
            continue

        test_end = rule_data.get("test_end_date", "")
        if test_end > today:
            days_left = (datetime.strptime(test_end, "%Y-%m-%d")
                        - datetime.now(TR_TZ).replace(tzinfo=None)).days
            print(f"[Darwin] {rule_name}: test devam ediyor ({days_left} gün kaldı)")
            continue

        # Test bitti — fitness ölç
        new_fitness_data = calculate_fitness(rule_name, transactions)
        new_fitness      = new_fitness_data.get("fitness")
        old_fitness      = rule_data.get("fitness")

        print(f"[Darwin] {rule_name}: eski fitness {old_fitness} → yeni {new_fitness}")

        if new_fitness is None or (old_fitness is not None and new_fitness <= old_fitness):
            # REVERT — eski versiyona dön
            print(f"[Darwin] REVERT: {rule_name} eski versiyona dönüyor")
            genome[rule_name]["current_prompt"]  = rule_data.get("previous_prompt", rule_data["current_prompt"])
            genome[rule_name]["version"]         -= 1
            genome[rule_name]["pending_test"]    = False
            genome[rule_name]["last_result"]     = "REVERTED"
            results.append({"rule": rule_name, "result": "REVERTED", "fitness_change": None})
        else:
            # COMMIT — yeni versiyon kalıcı
            print(f"[Darwin] COMMIT: {rule_name} v{rule_data['version']} kalıcı")
            genome[rule_name]["fitness"]      = new_fitness
            genome[rule_name]["pending_test"] = False
            genome[rule_name]["last_result"]  = "COMMITTED"
            results.append({
                "rule":          rule_name,
                "result":        "COMMITTED",
                "fitness_change": round((new_fitness - (old_fitness or 0)), 3)
            })
            # Git commit
            _git_commit_evolution(rule_name, rule_data["version"])

    save_genome(genome)
    _update_k_rules_digest(genome)
    return results


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────

def _update_k_rules_digest(genome: dict):
    """K-rules digest'i genome'daki güncel promtlarla günceller."""
    digest_path = MEMORY_DIR / "k_rules_digest.md"
    existing    = digest_path.read_text(encoding="utf-8") if digest_path.exists() else ""

    # Genome bölümünü ekle/güncelle
    genome_section = "\n\n## Evrimleştirilen Kural Versiyonları\n"
    for name, data in genome.items():
        v       = data.get("version", 1)
        fitness = data.get("fitness", "N/A")
        pending = " [TEST DEVAM EDİYOR]" if data.get("pending_test") else ""
        genome_section += f"\n### {name} (v{v}, fitness: {fitness}){pending}\n"
        genome_section += data["current_prompt"] + "\n"

    # Mevcut digest'e ekle (genome bölümü varsa güncelle)
    if "## Evrimleştirilen Kural Versiyonları" in existing:
        base = existing.split("## Evrimleştirilen Kural Versiyonları")[0]
        updated = base + genome_section
    else:
        updated = existing + genome_section

    digest_path.write_text(updated, encoding="utf-8")


def _git_commit_evolution(rule_name: str, version: int):
    """Başarılı evrim sonucunu git'e commit eder."""
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name", "Finzora Agent"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], check=True, capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add",
                        "agent/memory/prompt_genome.json",
                        "agent/memory/evolution_log.json",
                        "agent/memory/k_rules_digest.md"], capture_output=True)
        msg = f"🧬 [Darwin] {rule_name} v{version} COMMIT — fitness iyileşti"
        subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print(f"[Darwin] Git commit başarılı: {msg}")
    except subprocess.CalledProcessError as e:
        print(f"[Darwin] Git hatası: {e}")


def get_evolution_summary() -> str:
    """Claude ve Telegram için evrim özeti."""
    genome      = load_genome()
    evo_log_path = MEMORY_DIR / "evolution_log.json"

    lines = ["=== DARWIN EVRİM DURUMU ===\n"]

    # Genome durumu
    lines.append("Kural Versiyonları:")
    for name, data in genome.items():
        v       = data.get("version", 1)
        fitness = data.get("fitness")
        pending = " ⏳ TEST" if data.get("pending_test") else ""
        result  = data.get("last_result", "")
        icon    = "🟢" if result == "COMMITTED" else "🔴" if result == "REVERTED" else "⚪"
        fitness_str = f"fitness:{fitness:.2f}" if fitness else "fitness:N/A"
        lines.append(f"  {icon} {name}: v{v} | {fitness_str}{pending}")

    lines.append("")

    # Son evrimler
    if evo_log_path.exists():
        with open(evo_log_path, encoding="utf-8") as f:
            log = json.load(f)
        entries = log.get("entries", [])[-3:]
        if entries:
            lines.append("Son evrimler:")
            for e in entries:
                lines.append(f"  [{e['date']}] {e['rule']}: v{e['old_version']}→v{e['new_version']}")

    return "\n".join(lines)
