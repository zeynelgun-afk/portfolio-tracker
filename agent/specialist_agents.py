#!/usr/bin/env python3
"""
Finzora Agent — Uzman Agent Sistemi
=====================================
ATLAS'tan ilham: Her agent kendi alanında uzman.
Tek Claude yerine 4 uzman + 1 CIO.

Ajanlar:
  1. MACRO_AGENT   → Fed, VIX, jeopolitik, makro takvim
  2. SECTOR_AGENT  → Sektör liderliği, rotasyon, rejim
  3. SIGNAL_AGENT  → RSI, momentum, teknik giriş sinyalleri
  4. RISK_AGENT    → Stop seviyeleri, pozisyon boyutu, korelasyon
  5. CIO_AGENT     → Tüm sinyalleri Darwinian ağırlıkla sentezler

Her agent kendi genome'una sahip ve bağımsız skorlanır.
Yüksek doğruluklu agent → CIO'da daha yüksek ağırlık alır.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from claude_agent import get_claude_decision
from prediction_logger import log_prediction

MEMORY_DIR = Path(__file__).parent / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

SPECIALIST_GENOME_PATH = MEMORY_DIR / "specialist_genome.json"

# ── Uzman Agent Sistem Promptları ─────────────────────────────────────────────

SPECIALIST_PROMPTS = {
    "MACRO_AGENT": """Sen Finzora'nın Makro Analisti'sin.
SADECE makroekonomik faktörlere odaklan:
- Fed politikası, faiz beklentileri
- VIX seviyesi ve yönü
- Jeopolitik riskler (savaş, tarife, politika)
- Ekonomik takvim (CPI, NFP, GDP)
- Dolar endeksi, tahvil faizleri

ÇIKTI FORMAT (SADECE JSON):
{
  "sinyal": "RISK_ON | RISK_OFF | NEUTRAL",
  "guven": "HIGH | MEDIUM | LOW",
  "ana_tema": "tek cümle ana makro tema",
  "beklentiler": ["beklenti1", "beklenti2"],
  "risk_faktoru": "en kritik risk nedir",
  "tahmin": {
    "yon": "UP | DOWN | NEUTRAL",
    "buyukluk": "HIGH | MEDIUM | LOW",
    "sembol": "SPY"
  }
}""",

    "SECTOR_AGENT": """Sen Finzora'nın Sektör Analisti'sin.
SADECE sektör rotasyonu ve liderliğe odaklan:
- Hangi sektör ETF öne çıkıyor (XLE, XLK, ITA, GLD, XLI...)
- Aktif piyasa rejimi (jeopolitik, AI boom, faiz döngüsü, tarife)
- Sektörler arası para akışı
- Hangi sektörden çıkmalı, hangisine girmeli

ÇIKTI FORMAT (SADECE JSON):
{
  "aktif_rejim": "jeopolitik_kriz | ai_boom | faiz_dusus | tarife_gerilimi | risk_on | risk_off",
  "lider_sektor": "sektör adı ve ETF kodu",
  "zayif_sektor": "sektör adı ve ETF kodu",
  "rotasyon_onerisi": "hangi sektörden hangisine",
  "guven": "HIGH | MEDIUM | LOW",
  "tahmin": {
    "yon": "UP | DOWN | NEUTRAL",
    "buyukluk": "HIGH | MEDIUM | LOW",
    "sembol": "lider sektör ETF"
  }
}""",

    "SIGNAL_AGENT": """Sen Finzora'nın Teknik Sinyal Analisti'sin.
SADECE teknik giriş/çıkış sinyallerine odaklan:
- RSI seviyeleri (oversold/overbought)
- SMA50/SMA200 pozisyonları
- Hacim anormallikleri
- Momentum göstergeleri
- Portföydeki her pozisyon için teknik görüş

ÇIKTI FORMAT (SADECE JSON):
{
  "portfoy_sinyalleri": [
    {
      "sembol": "TICKER",
      "sinyal": "BUY | SELL | HOLD | WATCH",
      "rsi_yorumu": "oversold | normal | overbought",
      "sma_durumu": "ustunde | altinda",
      "aciklama": "tek cümle"
    }
  ],
  "en_guclu_setup": "en iyi teknik setup hisse",
  "en_zayif_setup": "en zayıf teknik pozisyon",
  "guven": "HIGH | MEDIUM | LOW"
}""",

    "RISK_AGENT": """Sen Finzora'nın Risk Yöneticisi'sin.
SADECE risk faktörlerine odaklan:
- Stop seviyelerine yakınlık
- Portföy konsantrasyonu ve korelasyon
- ATR bazlı pozisyon boyutlandırma
- Drawdown durumu
- "Yarın %5 düşerse ne olur?" senaryosu

ÇIKTI FORMAT (SADECE JSON):
{
  "risk_seviyesi": "LOW | MEDIUM | HIGH | CRITICAL",
  "stop_yakini": ["TICKER1 - %X uzakta", "TICKER2 - %Y uzakta"],
  "konsantrasyon_uyarisi": "varsa açıkla",
  "senaryo_5pct_dusus": "portföy tahmini kayıp",
  "onerileri": ["risk azaltma önerisi 1", "öneri 2"],
  "guven": "HIGH | MEDIUM | LOW"
}""",
}

# ── Uzman Agent Çağrısı ───────────────────────────────────────────────────────

def call_specialist(
    agent_name: str,
    context: str,
    extra_data: str = ""
) -> dict:
    """
    Bir uzman agent'ı çağırır ve JSON yanıt döner.
    """
    system_prompt = SPECIALIST_PROMPTS.get(agent_name, "")

    prompt = f"""
{context}

{extra_data}

Görevin: Yukarıdaki verileri değerlendir ve SADECE JSON formatında yanıt ver.
Başka metin ekleme. Markdown code fence kullanma. Doğrudan JSON ile başla {{
Yanıtın 13 pozisyon için fazla uzun olmamalı — her sembol için maksimum
3-4 alanlı kısa kayıt yeterli. Açıklamalar 1 cümle.
"""

    response = get_claude_decision(
        prompt,
        mode="specialist",  # 28 Nis 2026: monitor (1500) → specialist (3000)
        system_override=system_prompt,
        rag_enabled=False,   # Uzmanların portföy geçmişine erişimi gereksiz; prompt
                             # zaten compressed_ctx + market/risk/portfolio içeriyor.
    )

    # JSON parse (28 Nis 2026 sertlestirildi):
    # 1. Markdown code fence (```json ... ```) varsa cikar
    # 2. Greedy regex YERINE balanced brace matching
    # 3. Bozuk JSON'da en buyuk valid prefix'i bul
    try:
        import re
        # Markdown fence cikar
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        
        # Ilk { ile son } arasini bul (greedy)
        # Eger response truncated ise (max_tokens bitti), JSON tam degil — repair dene
        start_idx = cleaned.find("{")
        if start_idx == -1:
            raise ValueError("JSON baslangici bulunamadi")
        
        # Brace counting ile dengeli {} bul
        depth = 0
        end_idx = -1
        in_string = False
        escape = False
        for i in range(start_idx, len(cleaned)):
            c = cleaned[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            # Truncated JSON — repair: son TAM objenin sonunu bul
            # Stratejisi: en son '}' karakteri ya da '},' bul, sonra acik
            # array/object'leri kapat. Yarim obje (acik {) varsa ondan onceki
            # virgule kadar kes.
            partial = cleaned[start_idx:]
            
            # Brace counting yapip son denge noktasini bul
            depth = 0
            in_str = False
            esc = False
            son_denge_idx = -1
            for i, c in enumerate(partial):
                if esc:
                    esc = False
                    continue
                if c == "\\":
                    esc = True
                    continue
                if c == '"' and not esc:
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    # Bu noktada partial[0:i+1] tek bir tam JSON degil, ama
                    # bir alt objenin tam yeri. Eger ust seviye degilse, son
                    # tam alt obje sonu olarak isaretle (post-process'te kullanacagiz).
                    if depth >= 0:
                        son_denge_idx = i
            
            # Son tam alt obje sonundan sonra ne var? Gereksiz fragmenti at.
            if son_denge_idx > 0:
                truncated = partial[:son_denge_idx + 1]
                # Acik [ ve { say
                open_braces = truncated.count("{")
                close_braces = truncated.count("}")
                open_brackets = truncated.count("[")
                close_brackets = truncated.count("]")
                # Sadece kapatma eksigi varsa ekle
                ekstra_curly = max(0, open_braces - close_braces)
                ekstra_bracket = max(0, open_brackets - close_brackets)
                repaired = truncated + ("]" * ekstra_bracket) + ("}" * ekstra_curly)
                try:
                    result = json.loads(repaired)
                    result["_agent"] = agent_name
                    result["_timestamp"] = datetime.now().isoformat()
                    result["_partial_repaired"] = True
                    print(f"[ClaudeAgent {agent_name}] JSON truncated, repaired ({len(repaired)} bytes)")
                    return result
                except Exception:
                    pass
            raise ValueError("JSON tam degil (truncated)")
        
        json_str = cleaned[start_idx:end_idx + 1]
        result = json.loads(json_str)
        result["_agent"] = agent_name
        result["_timestamp"] = datetime.now().isoformat()
        return result
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        print(f"[ClaudeAgent {agent_name}] JSON parse hatasi: {type(e).__name__}: {str(e)[:80]}")

    return {
        "_agent":     agent_name,
        "_raw":       response[:300],
        "_parse_hata": True,
        "guven":      "LOW"
    }


def call_cio(
    macro_signal: dict,
    sector_signal: dict,
    signal_signal: dict,
    risk_signal: dict,
    agent_weights: dict,
    portfolio_context: str
) -> dict:
    """
    CIO Agent: 4 uzman sinyalini Darwinian ağırlıklarla sentezler.
    
    ATLAS bulgusu: CIO en önemli değil — sentez kalitesi önemli.
    Bu yüzden CIO sadece ağırlıklı toplama yapar, süslü analiz değil.
    """

    cio_prompt = f"""Sen Finzora'nın CIO'susun. 4 uzman analistten sinyal aldın.
Her analistin ağırlığı geçmiş doğruluğuna göre belirlenmiş (0.3-2.5 arası).

MAKRO ANALİST (ağırlık: {agent_weights.get('MACRO_AGENT', 1.0):.2f}):
{json.dumps(macro_signal, ensure_ascii=False)}

SEKTÖR ANALİST (ağırlık: {agent_weights.get('SECTOR_AGENT', 1.0):.2f}):
{json.dumps(sector_signal, ensure_ascii=False)}

TEKNİK SİNYAL ANALİST (ağırlık: {agent_weights.get('SIGNAL_AGENT', 1.0):.2f}):
{json.dumps(signal_signal, ensure_ascii=False)}

RİSK YÖNETİCİSİ (ağırlık: {agent_weights.get('RISK_AGENT', 1.0):.2f}):
{json.dumps(risk_signal, ensure_ascii=False)}

PORTFÖY:
{portfolio_context[:500]}

GÖREV:
1. Yüksek ağırlıklı analistlere daha fazla önem ver
2. Analistler çelişiyorsa: Risk > Makro > Sektör > Teknik önceliği
3. Net aksiyon öner: BEKLE / AL / SAT / DÖNDÜR / ACİL_CIK

ÇIKTI FORMAT (SADECE JSON):
{{
  "karar": "BEKLE | AL | SAT | DONDUR | ACIL_CIK",
  "hedef_sembol": "ticker veya sektör",
  "gerekce": "tek paragraf Türkçe gerekçe",
  "uyari": "varsa kritik uyarı",
  "guven": "HIGH | MEDIUM | LOW",
  "analist_uzlasma": "YUKSEK | ORTA | DUSUK",
  "tahmin": {{
    "yon": "UP | DOWN | NEUTRAL",
    "buyukluk": "HIGH | MEDIUM | LOW",
    "sembol": "SPY"
  }}
}}"""

    response = get_claude_decision(
        cio_prompt,
        mode="morning",
        rag_enabled=False,   # 4 uzman çıktısı + portfolio_context prompt'ta zaten;
                             # ek RAG inject tokensuz değer katmıyor.
    )

    try:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["_agent"]     = "CIO_AGENT"
            result["_timestamp"] = datetime.now().isoformat()
            return result
    except (json.JSONDecodeError, AttributeError):
        pass

    return {
        "_agent":      "CIO_AGENT",
        "_raw":        response[:300],
        "_parse_hata": True,
        "karar":       "BEKLE",
        "guven":       "LOW",
    }


# ── Uzman Genome ──────────────────────────────────────────────────────────────

def load_specialist_genome() -> dict:
    """Uzman agentların ağırlık ve fitness geçmişi."""
    if SPECIALIST_GENOME_PATH.exists():
        with open(SPECIALIST_GENOME_PATH, encoding="utf-8") as f:
            return json.load(f)

    # İlk kurulum — hepsi eşit ağırlık
    initial = {
        "MACRO_AGENT":  {"weight": 1.0, "n": 0, "avg_score": 0.0, "history": []},
        "SECTOR_AGENT": {"weight": 1.0, "n": 0, "avg_score": 0.0, "history": []},
        "SIGNAL_AGENT": {"weight": 1.0, "n": 0, "avg_score": 0.0, "history": []},
        "RISK_AGENT":   {"weight": 1.0, "n": 0, "avg_score": 0.0, "history": []},
        "CIO_AGENT":    {"weight": 1.0, "n": 0, "avg_score": 0.0, "history": []},
    }
    save_specialist_genome(initial)
    return initial


def save_specialist_genome(genome: dict):
    with open(SPECIALIST_GENOME_PATH, "w", encoding="utf-8") as f:
        json.dump(genome, f, ensure_ascii=False, indent=2)


def update_specialist_weights(genome: dict, scored_predictions: list) -> dict:
    """
    Skorlanan tahminlerden uzman ağırlıklarını günceller.
    prediction_logger ile entegre.
    """
    from prediction_logger import _load_log

    log         = _load_log()
    agent_scores = {}

    for pred in log.get("tahminler", []):
        if pred.get("durum") != "SKORLANDI":
            continue
        agent = pred.get("agent", "")
        skor  = pred.get("son_skor", 0)
        if agent in genome:
            if agent not in agent_scores:
                agent_scores[agent] = []
            agent_scores[agent].append(skor)

    # Ağırlıkları güncelle
    WEIGHT_MIN = 0.3
    WEIGHT_MAX = 2.5

    for agent, scores in agent_scores.items():
        if not scores or agent not in genome:
            continue

        avg = sum(scores) / len(scores)
        old_weight = genome[agent]["weight"]

        # Pozitif ortalama → ağırlık artır, negatif → azalt
        if avg > 0.5:
            new_weight = min(old_weight * 1.05, WEIGHT_MAX)
        elif avg < -0.5:
            new_weight = max(old_weight * 0.95, WEIGHT_MIN)
        else:
            new_weight = old_weight

        genome[agent]["weight"]    = round(new_weight, 4)
        genome[agent]["n"]         += len(scores)
        genome[agent]["avg_score"] = round(avg, 3)
        genome[agent]["history"].append({
            "date":       datetime.now().strftime("%Y-%m-%d"),
            "weight":     new_weight,
            "avg_score":  avg,
            "n_samples":  len(scores),
        })
        genome[agent]["history"] = genome[agent]["history"][-30:]

    save_specialist_genome(genome)
    return genome


def get_agent_weights(genome: dict) -> dict:
    """CIO için ağırlık sözlüğü."""
    return {name: data["weight"] for name, data in genome.items()}


# ── Ana Multi-Agent Analiz ────────────────────────────────────────────────────

def run_multi_agent_analysis(
    compressed_ctx: str,
    market_data: str,
    risk_data: str,
    portfolio_ctx: str,
) -> dict:
    """
    4 uzman agent'ı paralel çalıştır, CIO ile sentezle.
    """
    print("[MultiAgent] 4 uzman agent çalışıyor...")

    genome  = load_specialist_genome()
    weights = get_agent_weights(genome)

    # 4 uzman çağır (sıralı — maliyet kontrolü)
    macro_sig  = call_specialist("MACRO_AGENT",  compressed_ctx + "\n" + market_data)
    sector_sig = call_specialist("SECTOR_AGENT", compressed_ctx + "\n" + market_data)
    signal_sig = call_specialist("SIGNAL_AGENT", compressed_ctx + "\n" + portfolio_ctx)
    risk_sig   = call_specialist("RISK_AGENT",   compressed_ctx + "\n" + risk_data)

    print("[MultiAgent] CIO sentez yapıyor...")

    # CIO sentezi
    cio_decision = call_cio(
        macro_sig, sector_sig, signal_sig, risk_sig,
        weights, portfolio_ctx
    )

    # Tahminleri logla
    for agent_name, signal in [
        ("MACRO_AGENT",  macro_sig),
        ("SECTOR_AGENT", sector_sig),
        ("SIGNAL_AGENT", signal_sig),
        ("CIO_AGENT",    cio_decision),
    ]:
        tahmin = signal.get("tahmin", {})
        if tahmin.get("sembol") and tahmin.get("yon"):
            log_prediction(
                agent_name    = agent_name,
                prediction_type = "ANALIZ",
                symbol        = tahmin["sembol"],
                direction     = tahmin["yon"],
                magnitude     = tahmin.get("buyukluk", "MEDIUM"),
                rationale     = signal.get("gerekce") or signal.get("ana_tema") or "",
                source_rule   = agent_name,
                confidence    = signal.get("guven", "MEDIUM"),
            )

    result = {
        "macro":  macro_sig,
        "sector": sector_sig,
        "signal": signal_sig,
        "risk":   risk_sig,
        "cio":    cio_decision,
        "weights": weights,
    }

    # Kaydet
    output_path = MEMORY_DIR / "multi_agent_latest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[MultiAgent] Tamamlandı. CIO kararı: {cio_decision.get('karar','?')}")
    return result


def format_multi_agent_for_telegram(result: dict) -> str:
    """Telegram mesajı için multi-agent sonucunu formatlar."""
    macro  = result.get("macro", {})
    sector = result.get("sector", {})
    risk   = result.get("risk", {})
    cio    = result.get("cio", {})
    ws     = result.get("weights", {})

    lines = ["📊 Multi-Agent Analiz\n"]

    lines.append(f"🌍 MAKRO ({ws.get('MACRO_AGENT',1.0):.1f}x): "
                 f"{macro.get('sinyal','?')} | {macro.get('ana_tema','')[:60]}")

    lines.append(f"🔄 SEKTÖR ({ws.get('SECTOR_AGENT',1.0):.1f}x): "
                 f"{sector.get('aktif_rejim','?')} | Lider: {sector.get('lider_sektor','?')}")

    stop_yakini = risk.get("stop_yakini", [])
    if stop_yakini:
        lines.append(f"⚠️ RİSK ({ws.get('RISK_AGENT',1.0):.1f}x): "
                     f"Stop yakın: {', '.join(stop_yakini[:2])}")
    else:
        lines.append(f"✅ RİSK ({ws.get('RISK_AGENT',1.0):.1f}x): "
                     f"{risk.get('risk_seviyesi','?')}")

    lines.append("")
    lines.append(f"🎯 CIO KARARI: {cio.get('karar','?')} "
                 f"(güven: {cio.get('guven','?')}, uzlaşma: {cio.get('analist_uzlasma','?')})")

    if cio.get("gerekce"):
        lines.append(f"   {cio['gerekce'][:150]}")

    if cio.get("uyari"):
        lines.append(f"   ⚠️ {cio['uyari']}")

    return "\n".join(lines)
