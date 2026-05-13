#!/usr/bin/env python3
"""
Finzora Agent — Adversarial Debate Sistemi
============================================
TradingAgents'tan ilham: Boğa ve Ayı araştırmacıları tartışır,
CIO nihai kararı verir.

ATLAS bulgusu: Yapılandırılmış tartışma, tek taraflı analizden
çok daha güvenilir kararlar üretir. Körleşmeyi önler.

Akış:
  1. CIO'nun ilk kararını al (specialist_agents'tan)
  2. BULL_AGENT: Neden haklıyız? En güçlü argümanlar.
  3. BEAR_AGENT: Neden yanlışız? En zayıf noktalar, riskler.
  4. CIO_DEBATE: Her iki tarafı dinle, final karar ver.
  5. Tartışmayı logla — blind spot tespiti için.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from claude_agent import get_claude_decision
from prediction_logger import log_prediction

MEMORY_DIR   = Path(__file__).parent / "memory"
DEBATE_LOG   = MEMORY_DIR / "debate_log.json"


# ── Agent Sistem Promptları ───────────────────────────────────────────────────

BULL_PROMPT = """You are Finzora's Bull Researcher.
Task: produce the STRONGEST bull arguments for the given positions/decisions.
You are deliberately one-sided — defend the most optimistic scenario.
But stay data-driven, not emotional.

OUTPUT (JSON ONLY — keys MUST stay in Turkish exactly as shown):
{
  "argümanlar": [
    "strong argument 1 (with concrete data) — write content in Turkish",
    "strong argument 2 — Turkish",
    "strong argument 3 — Turkish"
  ],
  "katalizörler": ["upcoming positive catalyst 1 in Turkish", "catalyst 2"],
  "hedef_fiyat_gerekce": "why the price target is reachable — Turkish, single sentence",
  "boğa_skoru": 1-10,
  "en_güçlü_nokta": "single Turkish sentence — the most important argument"
}"""

BEAR_PROMPT = """You are Finzora's Bear Researcher.
Task: produce the STRONGEST bear arguments for the given positions/decisions.
You are deliberately one-sided — defend the most pessimistic scenario.
But stay data-driven, not emotional.

OUTPUT (JSON ONLY — keys MUST stay in Turkish exactly as shown):
{
  "argümanlar": [
    "risk factor 1 (with concrete data) — Turkish",
    "risk factor 2 — Turkish",
    "risk factor 3 — Turkish"
  ],
  "katalizörler": ["upcoming negative catalyst 1 in Turkish", "catalyst 2"],
  "stop_gerekce": "why a stop could trigger — Turkish, single sentence",
  "ayı_skoru": 1-10,
  "en_güçlü_nokta": "single Turkish sentence — the most important risk"
}"""

DEBATE_ARBITRATOR_PROMPT = """You are Finzora's CIO. You have heard the debate.
Task: weigh both sides and produce the FINAL decision.
Be neither blindly optimistic nor pessimistic — be realistic.

OUTPUT (JSON ONLY — keys MUST stay in Turkish exactly as shown):
{
  "nihai_karar": "AL | SAT | BEKLE | KISMI_CIK | KISMI_EKLE",
  "kazan_taraf": "BOĞA | AYI | BAĞLANTI",
  "karar_gerekce": "why this decision — Turkish, 2-3 sentences",
  "boğa_haklı_çünkü": "the strongest bull point you accept — Turkish",
  "ayı_haklı_çünkü": "the strongest bear point you accept — Turkish",
  "göz_ardı_edilen": "what the debate missed — Turkish",
  "güven": "HIGH | MEDIUM | LOW",
  "tahmin": {
    "yon": "UP | DOWN | NEUTRAL",
    "buyukluk": "HIGH | MEDIUM | LOW",
    "sembol": "SPY"
  }
}"""


# ── Tartışma Çalıştırıcı ─────────────────────────────────────────────────────

def run_debate(
    symbol: str,
    context: str,
    initial_decision: dict,
    portfolio_data: str = ""
) -> dict:
    """
    Boğa vs Ayı tartışması çalıştırır.
    
    Args:
        symbol: Tartışma konusu hisse/sektör
        context: Piyasa bağlamı
        initial_decision: CIO'nun ilk kararı
        portfolio_data: Portföy pozisyon detayları
    """
    print(f"[Debate] {symbol} için tartışma başlıyor...")

    debate_context = f"""
TARTIŞMA KONUSU: {symbol}
İLK CIO KARARI: {initial_decision.get('karar', '?')} 
(güven: {initial_decision.get('guven', '?')})

PİYASA BAĞLAMI:
{context[:800]}

{portfolio_data[:400]}
"""

    # Boğa argümanları
    bull_response = get_claude_decision(
        debate_context + "\nBoğa argümanlarını sun.",
        mode="monitor",
        system_override=BULL_PROMPT,
    )
    bull_data = _parse_json(bull_response)
    print(f"[Debate] Boğa skoru: {bull_data.get('boğa_skoru', '?')}/10")

    # Ayı argümanları
    bear_response = get_claude_decision(
        debate_context + "\nAyı argümanlarını sun.",
        mode="monitor",
        system_override=BEAR_PROMPT,
    )
    bear_data = _parse_json(bear_response)
    print(f"[Debate] Ayı skoru: {bear_data.get('ayı_skoru', '?')}/10")

    # CIO hakem kararı
    arbitrator_context = f"""
{debate_context}

BOĞA ARAŞTIRMACISI ({bull_data.get('boğa_skoru', 5)}/10):
Argümanlar: {json.dumps(bull_data.get('argümanlar', []), ensure_ascii=False)}
En güçlü: {bull_data.get('en_güçlü_nokta', '')}

AYI ARAŞTIRMACISI ({bear_data.get('ayı_skoru', 5)}/10):
Argümanlar: {json.dumps(bear_data.get('argümanlar', []), ensure_ascii=False)}
En güçlü: {bear_data.get('en_güçlü_nokta', '')}

Nihai kararı ver:"""

    arbitrator_response = get_claude_decision(
        arbitrator_context,
        mode="monitor",
        system_override=DEBATE_ARBITRATOR_PROMPT,
    )
    final_decision = _parse_json(arbitrator_response)
    print(f"[Debate] Nihai karar: {final_decision.get('nihai_karar', '?')}")

    result = {
        "symbol":           symbol,
        "tarih":            datetime.now().isoformat(),
        "ilk_karar":        initial_decision,
        "boğa":             bull_data,
        "ayı":              bear_data,
        "nihai":            final_decision,
        "karar_degisti_mi": (
            initial_decision.get("karar") != final_decision.get("nihai_karar")
        ),
    }

    # Tartışmayı logla
    _log_debate(result)

    # Tahmin logla
    tahmin = final_decision.get("tahmin", {})
    if tahmin.get("sembol") and tahmin.get("yon"):
        log_prediction(
            agent_name      = "DEBATE_CIO",
            prediction_type = "DEBATE_KARAR",
            symbol          = tahmin["sembol"],
            direction       = tahmin["yon"],
            magnitude       = tahmin.get("buyukluk", "MEDIUM"),
            rationale       = final_decision.get("karar_gerekce", ""),
            source_rule     = "adversarial_debate",
            confidence      = final_decision.get("güven", "MEDIUM"),
        )

    return result


def _parse_json(response: str) -> dict:
    """JSON parse, hata durumunda boş dict."""
    try:
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"_raw": response[:200], "_parse_hata": True}


def _log_debate(result: dict):
    """Tartışmayı logla — blind spot tespiti için."""
    log = {"tartismalar": []}
    if DEBATE_LOG.exists():
        with open(DEBATE_LOG, encoding="utf-8") as f:
            log = json.load(f)

    if "tartismalar" not in log:


        log["tartismalar"] = []


    log["tartismalar"].append(result)
    log["tartismalar"] = log["tartismalar"][-100:]

    with open(DEBATE_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def format_debate_for_telegram(result: dict) -> str:
    """Tartışma özetini Telegram için formatlar."""
    boğa  = result.get("boğa", {})
    ayı   = result.get("ayı", {})
    nihai = result.get("nihai", {})

    lines = [f"⚔️ Tartışma: {result.get('symbol', '?')}\n"]

    lines.append(
        f"🟢 Boğa ({boğa.get('boğa_skoru', '?')}/10): "
        f"{boğa.get('en_güçlü_nokta', '')[:80]}"
    )
    lines.append(
        f"🔴 Ayı ({ayı.get('ayı_skoru', '?')}/10): "
        f"{ayı.get('en_güçlü_nokta', '')[:80]}"
    )
    lines.append("")
    lines.append(
        f"🎯 Karar: {nihai.get('nihai_karar', '?')} "
        f"({nihai.get('kazan_taraf', '?')} kazandı)"
    )
    lines.append(f"   {nihai.get('karar_gerekce', '')[:120]}")

    if result.get("karar_degisti_mi"):
        lines.append("⚡ Tartışma ilk kararı DEĞİŞTİRDİ!")

    return "\n".join(lines)
