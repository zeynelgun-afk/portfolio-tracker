#!/usr/bin/env python3
"""
Finzora Agent — Darwinian Prompt Evolution v2.0
================================================
Her 5 İŞ gününde en zayıf K-kuralının promptunu evrimleştirir.
Claude API'ye yeni versiyon yazdırır, 14 gün test eder.
İyileşirse git commit, kötüleşirse git revert.

Fitness fonksiyonu: Sharpe × win_rate
  (Sharpe = avg_pnl / std_dev  —  hem getiri hem tutarlılık)

Düzeltmeler (v2.0):
  1. Kilitli kural yok — tüm K-kuralları evrimleştirilebilir
  2. Çakışan test koruması — pending_test=True olan kural seçilmez
  3. İş günü kontrolü — hafta sonu tetiklenme engellendi
  4. Docstring ↔ kod uyumu sağlandı (fitness formülü)
  5. L3 digest her evrimden sonra anlık güncellenir
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

# ── Evrimleştirilebilir K-kuralları ──────────────────────────────────────────
# KILITLI KURAL YOK. Her kural evrimleştirilebilir.
# Kritik kurallar (K-13) Darwin'de de yer alır.
# Yüksek etki → daha fazla dikkat, daha fazla kanıt gerekir (rule_updater.py'de tier="critical").
# (K-14 drawdown freni 11 Nisan 2026'da tamamen kaldırıldı — genome'dan da çıkarıldı.)

INITIAL_GENOME = {
    "K-11_trailing_stop": {
        "version": 1, "description": "Trailing stop tetikleme koşulu",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "K-11 Trailing Stop:\n"
            "Pozisyon zirveden 2×ATR aşağı düşerse trailing stop tetiklenir.\n"
            "Makro şok istisnası: SPY ≥%3 düşüş + VIX ≥%20 spike aynı gün → 1 gün bekle."
        ),
        "fitness": None, "last_modified": None,
    },
    "K-11_partial_sell": {
        "version": 1, "description": "Kısmi kâr alma tetikleme koşulu",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "K-11 Kısmi Kâr Alma:\n"
            "Katman 1: RSI 70+ VE kâr %15+ → trailing stop aktif\n"
            "Katman 2: RSI 80+ VEYA (RSI 75+ + negatif div/20SMA altı) → %25-30 sat\n"
            "Katman 3: 50SMA altı kapanış VEYA chandelier trailing → TAM ÇIK"
        ),
        "fitness": None, "last_modified": None,
    },
    "K-13_vix_threshold": {
        "version": 1, "description": "VIX bazlı pozisyon boyutu (kritik)",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "K-13 VIX Kuralı:\n"
            "Faydalanıcı sektörler (savunma, enerji, altın): VIX 28'e kadar tam pozisyon\n"
            "Duyarlı sektörler (tech, growth): VIX 22'den itibaren yarım pozisyon\n"
            "VIX>35: tüm yeni girişler dur"
        ),
        "fitness": None, "last_modified": None,
        "min_trades_to_evolve": 30,   # Kritik kural → daha fazla kanıt
    },
    # K-14 KALDIRILDI (11 Nisan 2026) — genome'dan da çıkarıldı
    "K-04_entry_filter": {
        "version": 1, "description": "Giriş filtresi - SMA ve RSI",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "K-04 Giriş Filtresi:\n"
            "Standart: Giriş fiyatı SMA50 üstünde olmalı\n"
            "İstisna: RSI<30 + stabilizasyon + pozitif katalizör → çeyrek pozisyon\n"
            "Yasak: SMA50+SMA200 altı + insider satış yoğun → giriş yok"
        ),
        "fitness": None, "last_modified": None,
    },
    "session_faz1_gap": {
        "version": 1, "description": "FAZ 1 açılış gap eşikleri",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "FAZ 1 Gap Analizi:\n"
            "Gap < -%5 → GAP-DOWN uyarı, K-09 tetik\n"
            "Gap > +%5 → GAP-UP, ilk 15dk bekle\n"
            "Gap -3% ile -5% → negatif gap, stop yakınlık kontrol\n"
            "Gap +3% ile +5% → pozitif gap, giriş fırsatı izle"
        ),
        "fitness": None, "last_modified": None,
    },
    "session_faz2_entry": {
        "version": 1, "description": "FAZ 2 yeni giriş GO/NO-GO eşikleri",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "FAZ 2 Giriş Kriterleri:\n"
            "GO: Ichimoku 4/4 + R:R ≥2.5:1 + K-13 VIX uygun + K-18 temiz\n"
            "NO-GO: FAZ 1'in ilk 15dk içinde + VIX>28 + earnings ≤2 gün + stop>%12\n"
            "İlk 30dk yeni giriş yasak (gap stabilizasyonu)"
        ),
        "fitness": None, "last_modified": None,
    },
    "session_faz3_trailing": {
        "version": 1, "description": "FAZ 3 power hour trailing stop mantığı",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "FAZ 3 Trailing Stop:\n"
            "Kâr <%7: chandelier 3×ATR\n"
            "Kâr %7-15: chandelier 2×ATR (kâr kilidi)\n"
            "Kâr %15+: chandelier 1.5×ATR (agresif kilit)\n"
            "RSI 80+ kapanışa yakın: %25-30 kısmi satış değerlendir"
        ),
        "fitness": None, "last_modified": None,
    },
    "swing_rsi_range": {
        "version": 1, "description": "Swing giriş RSI aralığı",
        "weight": 1.0, "weight_history": [],
        "current_prompt": (
            "Swing Giriş RSI:\n"
            "RSI 40-65 arası giriş bölgesi\n"
            "RSI<40: oversold bounce için çeyrek pozisyon\n"
            "RSI>65: momentum trade sadece güçlü trend varlığında"
        ),
        "fitness": None, "last_modified": None,
    },
}

WEIGHT_MIN  = 0.3
WEIGHT_MAX  = 2.5
WEIGHT_UP   = 1.05
WEIGHT_DOWN = 0.95

try:
    from prompt_evolver import update_prompt_file as _update_prompt
except ImportError:
    _update_prompt = None


# ── İş Günü Kontrolü ─────────────────────────────────────────────────────────

def is_trading_day(dt: datetime = None) -> bool:
    """Piyasa açık günü mü? Hafta sonu Darwin çalışmaz."""
    if dt is None:
        dt = datetime.now(TR_TZ)
    return dt.weekday() < 5   # 0=Pazartesi, 4=Cuma


def count_trading_days_since(date_str: str) -> int:
    """Verilen tarihten bugüne kadar geçen iş günü sayısı."""
    try:
        start = datetime.strptime(date_str, "%Y-%m-%d")
        end   = datetime.now(TR_TZ).replace(tzinfo=None)
        count = 0
        cur   = start
        while cur < end:
            if cur.weekday() < 5:
                count += 1
            cur += timedelta(days=1)
        return count
    except (ValueError, TypeError):
        return 0


# ── Fitness Hesaplama ─────────────────────────────────────────────────────────

def load_all_transactions() -> list:
    import csv
    tx_path = REPO_ROOT / "data" / "transactions.csv"
    if not tx_path.exists():
        return []
    rows = []
    with open(tx_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    buy_history = {}
    trades = []
    for row in rows:
        action = row.get("action", "").upper()
        symbol = row.get("symbol", "")
        price  = float(row.get("price", 0) or 0)
        reason = row.get("reason", "")
        date   = row.get("date", "")
        if action == "BUY" and price > 0:
            buy_history.setdefault(symbol, []).append({"price": price, "date": date})
        elif action in ("SELL", "SATIŞ") and price > 0 and symbol in buy_history:
            buys    = buy_history[symbol]
            avg_buy = sum(b["price"] for b in buys) / len(buys)
            pnl_pct = (price - avg_buy) / avg_buy * 100
            # Gerçek çıkış tarihi → prediction scorer için eklendi
            trades.append({
                "symbol":    symbol,
                "action":    action,
                "price":     price,
                "reason":    reason,
                "pnl_pct":   round(pnl_pct, 2),
                "date":      date,
                "exit_date": date,
            })
    return trades


def calculate_fitness(rule_name: str, transactions: list, min_trades: int = 5) -> dict:
    """
    Fitness = Sharpe × win_rate
    Sharpe proxy = avg_pnl / std_dev  (risk-free rate = 0)

    Bu formül hem getiriyi (avg_pnl) hem tutarlılığı (düşük std_dev = iyi Sharpe)
    hem de kazanma oranını (win_rate) birlikte ölçer.
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
        # K-14 kaldırıldı — matcher da kaldırıldı
        elif rule_name == "K-04_entry_filter":
            matched = "k-04" in reason or ("sma" in reason and "giriş" in reason)
        elif rule_name == "swing_rsi_range":
            matched = "rsi" in reason and (
                "swing" in reason or "oversold" in reason or "aşırı satım" in reason
            )
        elif "faz" in rule_name or "session" in rule_name:
            matched = "faz" in reason or "gap" in reason or "power hour" in reason
        if matched:
            rule_trades.append(float(pnl))

    if len(rule_trades) < min_trades:
        return {"fitness": None, "n": len(rule_trades), "win_rate": None,
                "avg_pnl": None, "sharpe": None,
                "not": f"Yetersiz veri ({len(rule_trades)}/{min_trades})"}

    n        = len(rule_trades)
    wins     = sum(1 for p in rule_trades if p > 0)
    win_rate = wins / n
    avg_pnl  = sum(rule_trades) / n
    variance = sum((p - avg_pnl) ** 2 for p in rule_trades) / n if n > 1 else 1.0
    std_dev  = variance ** 0.5 if variance > 0 else 1.0
    sharpe   = avg_pnl / std_dev if std_dev > 0 else 0
    fitness  = sharpe * win_rate

    return {
        "fitness":  round(fitness, 4),
        "n":        n,
        "win_rate": round(win_rate * 100, 1),
        "avg_pnl":  round(avg_pnl, 2),
        "std_dev":  round(std_dev, 2),
        "sharpe":   round(sharpe, 3),
    }


# ── Genome Yönetimi ───────────────────────────────────────────────────────────

def load_genome() -> dict:
    path = MEMORY_DIR / "prompt_genome.json"
    if not path.exists():
        save_genome(INITIAL_GENOME)
        return INITIAL_GENOME.copy()
    with open(path, encoding="utf-8") as f:
        genome = json.load(f)
    # Yeni kurallar eklendiyse merge et
    for k, v in INITIAL_GENOME.items():
        if k not in genome:
            genome[k] = v
        else:
            # Eksik alanları INITIAL_GENOME'dan tamamla (özellikle current_prompt)
            for field in ('current_prompt', 'version', 'description', 'weight'):
                if field not in genome[k] and field in v:
                    genome[k][field] = v[field]
    # _ ile başlayan meta anahtarları ve dict olmayan değerleri temizle
    genome = {k: v for k, v in genome.items()
              if isinstance(v, dict) and not k.startswith('_')}
    return genome


def save_genome(genome: dict):
    with open(MEMORY_DIR / "prompt_genome.json", "w", encoding="utf-8") as f:
        json.dump(genome, f, ensure_ascii=False, indent=2)


def update_fitness_scores(genome: dict, transactions: list) -> dict:
    for rule_name, rule_data in genome.items():
        min_trades = rule_data.get("min_trades_to_evolve", 5)
        fitness_data = calculate_fitness(rule_name, transactions, min_trades=min_trades)
        genome[rule_name]["fitness"]        = fitness_data.get("fitness")
        genome[rule_name]["fitness_detail"] = fitness_data
    return genome


def update_darwin_weights(genome: dict) -> dict:
    """
    Üst çeyrek fitness → ağırlık ×1.05 | Alt çeyrek → ×0.95
    Min: 0.3 | Max: 2.5
    """
    scored = {
        name: data["fitness"]
        for name, data in genome.items()
        if data.get("fitness") is not None
    }
    if len(scored) < 2:
        return genome

    fitnesses = sorted(scored.values())
    n         = len(fitnesses)
    q1        = fitnesses[n // 4]
    q3        = fitnesses[3 * n // 4]
    today     = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    for name, data in genome.items():
        fitness = data.get("fitness")
        weight  = data.get("weight", 1.0)
        if fitness is None:
            continue
        if fitness >= q3:
            new_weight = min(weight * WEIGHT_UP, WEIGHT_MAX)
        elif fitness <= q1:
            new_weight = max(weight * WEIGHT_DOWN, WEIGHT_MIN)
        else:
            new_weight = weight
        genome[name]["weight"] = round(new_weight, 4)
        history = genome[name].get("weight_history", [])
        history.append({"date": today, "weight": new_weight, "fitness": fitness})
        genome[name]["weight_history"] = history[-30:]
    return genome


def find_weakest_rule(genome: dict) -> tuple[str, dict]:
    """
    En düşük fitness'e sahip, TEST ALTINDA OLMAYAN kuralı seçer.

    DÜZELTME (v2.0): pending_test=True olan kurallar bu seçimden dışlanır.
    Böylece aynı kural iki kez teste girmez, çakışan testler önlenir.
    """
    eligible = {
        name: data
        for name, data in genome.items()
        if not data.get("pending_test", False)   # ← Aktif test varsa atla
           and data.get("fitness") is not None
    }

    if not eligible:
        # Fitness verisi yoksa ya da hepsi test altındaysa rastgele seç
        no_pending = {
            name: data for name, data in genome.items()
            if not data.get("pending_test", False)
        }
        if not no_pending:
            return None, None   # Tüm kurallar test altında
        name = list(no_pending.keys())[0]
        return name, no_pending[name]

    weakest = min(eligible.items(), key=lambda x: x[1]["fitness"])
    return weakest[0], weakest[1]


def get_weighted_genome_context(genome: dict) -> str:
    """Orchestrator için ağırlıklı kural özeti."""
    lines = ["=== DARWIN AĞIRLIKLI K-KURALLARI ===\n"]
    # _meta ve _ ile başlayan anahtarları atla, dict olmayanları atla
    valid = {k: v for k, v in genome.items()
             if not k.startswith('_') and isinstance(v, dict)}
    sorted_rules = sorted(valid.items(), key=lambda x: x[1].get("weight", 1.0), reverse=True)
    for name, data in sorted_rules:
        w       = data.get("weight", 1.0)
        fitness = data.get("fitness")
        v       = data.get("version", 1)
        pending = " ⏳" if data.get("pending_test") else ""
        bar     = "█" * int(w * 4)
        f_str   = f"fitness:{fitness:.3f}" if fitness else "fitness:N/A"
        prefix  = "🔊 GÜÇLÜ" if w >= 2.0 else "📢 Normal" if w >= 1.5 else "🔇 ZAYIF" if w <= 0.5 else "📣 Orta"
        prompt_line = data.get('current_prompt', data.get('not', data.get('description', '')))
        lines.append(f"{prefix} | {name} v{v}{pending}")
        lines.append(f"  Ağırlık: {w:.2f} {bar} | {f_str}")
        if prompt_line:
            lines.append(f"  {str(prompt_line).split(chr(10))[0][:80]}")
        lines.append("")
    return "\n".join(lines)


# ── Claude ile Evrim ──────────────────────────────────────────────────────────

def evolve_rule_with_claude(
    rule_name: str,
    current_rule: dict,
    transactions: list,
    analysis_context: str,
) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from claude_agent import get_claude_decision

    fitness = current_rule.get("fitness_detail", {})
    prompt = f"""
You are Finzora Agent doing ATLAS-style Darwinian prompt evolution.

CURRENT RULE: {rule_name}
CURRENT PROMPT:
{current_rule['current_prompt']}

PERFORMANCE DATA (fitness = Sharpe × win_rate):
  Fitness: {current_rule.get('fitness', 'N/A')}
  Trade count: {fitness.get('n', 0)}
  Win rate: %{fitness.get('win_rate', 'N/A')}
  Avg P/L: %{fitness.get('avg_pnl', 'N/A')}
  Sharpe proxy: {fitness.get('sharpe', 'N/A')}
  Std dev: {fitness.get('std_dev', 'N/A')}

TRADE ANALYSIS CONTEXT:
{analysis_context[:1500]}

TASK:
1. Diagnose why this rule has low fitness.
2. Identify weak points in the current prompt.
3. Propose a NEW prompt version. The new prompt MUST itself be written in Turkish
   (because the rule is consumed by Turkish-output flows).

OUTPUT (JSON ONLY — keys stay exactly as shown):
{{
  "analiz": "Turkish — why the rule is weak",
  "degisiklik": "Turkish — what should change",
  "yeni_prompt": "Turkish — full text of the new rule prompt",
  "beklenen_etki": "Turkish — expected win-rate/P&L impact",
  "risk": "Turkish — risk of this change"
}}
"""
    response = get_claude_decision(prompt, mode="weekly")
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
    Her 5 İŞ gününde bir çalışır (takvim günü değil).
    DÜZELTMELER:
      - Hafta sonu kontrolü → force=False ise Cumartesi/Pazar çalışmaz
      - Çakışan test koruması → pending_test=True olan kurallar seçilmez
    """
    print("[Darwin] Evrim döngüsü başlatılıyor...")

    # Hafta sonu kontrolü
    if not force and not is_trading_day():
        print("[Darwin] Hafta sonu — Darwin çalışmaz.")
        return {"skipped": True, "reason": "Hafta sonu"}

    # Son çalışma zamanı
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
        is_gunler = count_trading_days_since(last_run)
        if is_gunler < 5:
            print(f"[Darwin] Son evrimden {is_gunler} iş günü geçti (min 5). Atlandı.")
            return {"skipped": True, "reason": f"{is_gunler} iş günü önce çalıştı"}

    transactions = load_all_transactions()
    print(f"[Darwin] {len(transactions)} işlem yüklendi.")

    genome = load_genome()
    genome = update_fitness_scores(genome, transactions)
    genome = update_darwin_weights(genome)
    save_genome(genome)

    # Aktif testleri raporla
    active_tests = [n for n, d in genome.items() if d.get("pending_test")]
    if active_tests:
        print(f"[Darwin] Aktif testler (seçim dışı): {active_tests}")

    # En zayıf test-dışı kuralı bul
    weakest_name, weakest_rule = find_weakest_rule(genome)

    if weakest_name is None:
        print("[Darwin] Tüm kurallar test altında, evrim ertelendi.")
        return {"skipped": True, "reason": "Tüm kurallar test altında"}

    fitness_val = weakest_rule.get("fitness")
    print(f"[Darwin] En zayıf kural: {weakest_name} (fitness: {fitness_val})")

    if fitness_val is not None and fitness_val > 5.0:
        print(f"[Darwin] Fitness yeterli ({fitness_val} > 5.0). Evrim gerekmez.")
        return {"skipped": True, "reason": "Fitness yeterli", "fitness": fitness_val}

    # Claude ile evrim
    from backtester import format_backtest_for_claude, run_full_backtest
    backtest     = run_full_backtest()
    analysis_ctx = format_backtest_for_claude(backtest)

    print(f"[Darwin] Claude'a {weakest_name} için yeni prompt isteniyor...")
    evolution = evolve_rule_with_claude(
        weakest_name, weakest_rule, transactions, analysis_ctx
    )
    new_prompt = evolution.get("yeni_prompt")
    if not new_prompt:
        print("[Darwin] Claude geçerli prompt üretemedi.")
        return {"error": "Prompt üretilemedi", "claude_response": evolution}

    old_version = genome[weakest_name]["version"]
    new_version = old_version + 1

    genome[weakest_name]["previous_prompt"] = genome[weakest_name]["current_prompt"]
    genome[weakest_name]["current_prompt"]  = new_prompt
    genome[weakest_name]["version"]         = new_version
    genome[weakest_name]["last_modified"]   = today
    genome[weakest_name]["pending_test"]    = True
    genome[weakest_name]["test_start_date"] = today
    genome[weakest_name]["test_end_date"]   = (
        datetime.now(TR_TZ) + timedelta(days=14)
    ).strftime("%Y-%m-%d")
    genome[weakest_name]["evolution_data"]  = evolution

    save_genome(genome)
    _update_session_prompt_file(weakest_name, new_prompt)
    if _update_prompt:
        _update_prompt(weakest_name, new_prompt, new_version)

    # L3 digest anlık güncelle
    _update_k_rules_digest(genome)

    log_entry = {
        "date":        today,
        "rule":        weakest_name,
        "old_version": old_version,
        "new_version": new_version,
        "old_fitness": fitness_val,
        "active_tests_bypassed": active_tests,
        "analiz":      evolution.get("analiz", "")[:200],
        "degisiklik":  evolution.get("degisiklik", "")[:200],
        "risk":        evolution.get("risk", "")[:100],
    }
    if "entries" not in evo_log:

        evo_log["entries"] = []

    evo_log["entries"].append(log_entry)
    evo_log["entries"] = evo_log["entries"][-50:]
    with open(evo_log_path, "w", encoding="utf-8") as f:
        json.dump(evo_log, f, ensure_ascii=False, indent=2)

    print(f"[Darwin] ✅ {weakest_name} v{old_version} → v{new_version}")
    return log_entry


# ── Evrim Sonuç Değerlendirmesi ───────────────────────────────────────────────

def evaluate_evolution_results() -> list:
    genome       = load_genome()
    transactions = load_all_transactions()
    today        = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    results      = []

    for rule_name, rule_data in genome.items():
        if not rule_data.get("pending_test"):
            continue
        test_end = rule_data.get("test_end_date", "")
        if test_end > today:
            days_left = (
                datetime.strptime(test_end, "%Y-%m-%d")
                - datetime.now(TR_TZ).replace(tzinfo=None)
            ).days
            print(f"[Darwin] {rule_name}: test devam ediyor ({days_left} gün kaldı)")
            continue

        min_trades   = rule_data.get("min_trades_to_evolve", 5)
        new_fd       = calculate_fitness(rule_name, transactions, min_trades=min_trades)
        new_fitness  = new_fd.get("fitness")
        old_fitness  = rule_data.get("fitness")

        print(f"[Darwin] {rule_name}: eski {old_fitness} → yeni {new_fitness}")

        if new_fitness is None or (old_fitness is not None and new_fitness <= old_fitness):
            genome[rule_name]["current_prompt"] = rule_data.get(
                "previous_prompt", rule_data["current_prompt"]
            )
            genome[rule_name]["version"]      -= 1
            genome[rule_name]["pending_test"]  = False
            genome[rule_name]["last_result"]   = "REVERTED"
            results.append({"rule": rule_name, "result": "REVERTED"})
        else:
            genome[rule_name]["fitness"]      = new_fitness
            genome[rule_name]["pending_test"] = False
            genome[rule_name]["last_result"]  = "COMMITTED"
            results.append({
                "rule":          rule_name,
                "result":        "COMMITTED",
                "fitness_change": round((new_fitness - (old_fitness or 0)), 3),
            })
            _git_commit_evolution(rule_name, rule_data["version"])

    save_genome(genome)
    _update_k_rules_digest(genome)
    return results


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────

def _update_k_rules_digest(genome: dict):
    """L3 digest'i anlık günceller — artık haftalık bekleme yok."""
    digest_path = MEMORY_DIR / "k_rules_digest.md"
    existing    = digest_path.read_text(encoding="utf-8") if digest_path.exists() else ""

    genome_section = f"\n\n## Evrimleştirilen Kural Versiyonları\n_Son güncelleme: {datetime.now(TR_TZ).strftime('%Y-%m-%d %H:%M')}_\n"
    for name, data in genome.items():
        v       = data.get("version", 1)
        fitness = data.get("fitness", "N/A")
        pending = " [TEST DEVAM EDİYOR]" if data.get("pending_test") else ""
        genome_section += f"\n### {name} (v{v}, fitness: {fitness}){pending}\n"
        genome_section += data["current_prompt"] + "\n"

    if "## Evrimleştirilen Kural Versiyonları" in existing:
        base    = existing.split("## Evrimleştirilen Kural Versiyonları")[0]
        updated = base + genome_section
    else:
        updated = existing + genome_section

    digest_path.write_text(updated, encoding="utf-8")


def _update_session_prompt_file(rule_name: str, new_prompt: str):
    """Session prompt dosyasını günceller."""
    if not rule_name.startswith("session_"):
        return
    prompts_dir = REPO_ROOT / "docs" / "prompts"
    for fname in ["SESSION_PART2_ORTA.md", "SESSION_PART3_POWER.md", "SESSION_PART1_ACILIS.md"]:
        fpath = prompts_dir / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            if rule_name in content:
                print(f"[Darwin] {fname} prompt dosyası güncellendi.")
                break


def _git_commit_evolution(rule_name: str, version: int):
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name",  "Finzora AI"],  check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], check=True, capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add",
                        "agent/memory/prompt_genome.json",
                        "agent/memory/evolution_log.json",
                        "agent/memory/k_rules_digest.md"], capture_output=True)
        msg = f"🧬 [Darwin] {rule_name} v{version} COMMIT — fitness iyileşti"
        subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print(f"[Darwin] Git commit: {msg}")
    except subprocess.CalledProcessError as e:
        print(f"[Darwin] Git hatası: {e}")


def get_evolution_summary() -> str:
    genome       = load_genome()
    evo_log_path = MEMORY_DIR / "evolution_log.json"
    lines = ["=== DARWIN EVRİM DURUMU ===\n"]
    lines.append("Kural Versiyonları:")
    for name, data in genome.items():
        v       = data.get("version", 1)
        fitness = data.get("fitness")
        pending = " ⏳ TEST" if data.get("pending_test") else ""
        result  = data.get("last_result", "")
        icon    = "🟢" if result == "COMMITTED" else "🔴" if result == "REVERTED" else "⚪"
        f_str   = f"fitness:{fitness:.2f}" if fitness else "fitness:N/A"
        lines.append(f"  {icon} {name}: v{v} | {f_str}{pending}")
    lines.append("")
    if evo_log_path.exists():
        with open(evo_log_path, encoding="utf-8") as f:
            log = json.load(f)
        entries = log.get("entries", [])[-3:]
        if entries:
            lines.append("Son evrimler:")
            for e in entries:
                bypassed = e.get("active_tests_bypassed", [])
                note     = f" (atlandı: {bypassed})" if bypassed else ""
                lines.append(f"  [{e['date']}] {e['rule']}: v{e['old_version']}→v{e['new_version']}{note}")
    return "\n".join(lines)
