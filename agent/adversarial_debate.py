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

BULL_PROMPT = """Sen Finzora'nın Boğa Araştırmacısısın.
Görevin: Mevcut pozisyonlar ve kararlar için EN GÜÇLÜ boğa argümanlarını sun.
Taraflısın — en iyimser senaryoyu savun.
Ama veriye dayalı ol, duygusal değil.

ÇIKTI FORMAT (SADECE JSON):
{
  "argümanlar": [
    "güçlü argüman 1 (somut veri ile)",
    "güçlü argüman 2",
    "güçlü argüman 3"
  ],
  "katalizörler": ["yaklaşan pozitif katalizör 1", "katalizör 2"],
  "hedef_fiyat_gerekce": "neden hedef fiyata ulaşılır",
  "boğa_skoru": 1-10,
  "en_güçlü_nokta": "tek cümle en önemli argüman"
}"""

BEAR_PROMPT = """Sen Finzora'nın Ayı Araştırmacısısın.
Görevin: Mevcut pozisyonlar ve kararlar için EN GÜÇLÜ ayı argümanlarını sun.
Taraflısın — en kötümser senaryoyu savun.
Ama veriye dayalı ol, duygusal değil.

ÇIKTI FORMAT (SADECE JSON):
{
  "argümanlar": [
    "risk faktörü 1 (somut veri ile)",
    "risk faktörü 2",
    "risk faktörü 3"
  ],
  "katalizörler": ["yaklaşan negatif katalizör 1", "katalizör 2"],
  "stop_gerekce": "neden stop tetiklenebilir",
  "ayı_skoru": 1-10,
  "en_güçlü_nokta": "tek cümle en önemli risk"
}"""

DEBATE_ARBITRATOR_PROMPT = """Sen Finzora'nın CIO'susun. Tartışmayı dinledin.
Görevin: Boğa ve ayı argümanlarını değerlendirip NIHAI karar ver.
Ne saf iyimser ne saf kötümser ol — gerçekçi ol.

ÇIKTI FORMAT (SADECE JSON):
{
  "nihai_karar": "AL | SAT | BEKLE | KISMI_CIK | KISMI_EKLE",
  "kazan_taraf": "BOĞA | AYI | BAĞLANTI",
  "karar_gerekce": "neden bu karar (Türkçe, 2-3 cümle)",
  "boğa_haklı_çünkü": "en güçlü boğa noktası kabul edildi",
  "ayı_haklı_çünkü": "en güçlü ayı noktası kabul edildi",
  "göz_ardı_edilen": "tartışmada eksik kalan konu",
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
