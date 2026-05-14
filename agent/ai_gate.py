"""
Finzora AI — AI Gate (Aşama 8)
==============================

Watchlist'in 4 besleyicisinden gelen her sinyal LLM (Kimi) ile değerlendirilir.

Kullanım:
    from agent.ai_gate import evaluate_signal

    decision = evaluate_signal(
        symbol="NVDA",
        signal_type="analist_revize",  # veya 'fair_value_iskonto', 'manuel'
        signal_data={"raised_count": 5, "avg_pct": 8.2, ...},
    )

    if decision["action"] == "EKLE":
        wl_add(symbol, score=decision["score"], rationale=decision["reason"], ...)
    elif decision["action"] == "RED":
        log(f"AI gate REDDETTİ: {symbol} — {decision['reason']}")

Action değerleri:
  - "EKLE": LLM hisseyi watchlist'e eklemeyi onayladı
  - "RED": LLM reddetti (zayıf sinyal, value trap, kötü tema bağlamı vb.)
  - "HATA": LLM çağrısı başarısız oldu (fallback: çağıran karar versin)

14 May 2026 — Aşama 8 (4 besleyici LLM gate).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "moonshotai/kimi-k2"

# Fallback davranışı: AI çağrısı başarısız ise besleyici eski mantığa düşer
FALLBACK_ON_ERROR = True


def _log(msg: str) -> None:
    print(f"[ai_gate] {msg}")


# ────────────────────────── Default Context ──────────────────────────


def _build_default_context() -> dict:
    """LLM'e geçilecek market bağlamını otomatik oluştur."""
    context = {
        "active_themes": [],
        "dying_themes": [],
        "portfolio_symbols": [],
        "watchlist_size": 0,
        "watchlist_max": 80,
    }
    try:
        from agent.themes import all_themes
        themes = all_themes()
        for tid, t in themes.items():
            stage = t.get("lifecycle_stage", "?")
            entry = {
                "id": tid,
                "name": t.get("name", tid),
                "stage": stage,
                "score": t.get("momentum_score", 0),
            }
            if stage == "sönüs":
                context["dying_themes"].append(entry)
            elif stage in ("dogus", "yukselis", "olgun"):
                context["active_themes"].append(entry)
    except Exception as e:
        _log(f"context theme yükleme hatası: {e}")

    try:
        from agent.watchlist import load as wl_load
        wl = wl_load()
        context["watchlist_size"] = len(wl.get("tickers", {}))
    except Exception:
        pass

    try:
        pf_path = REPO_ROOT / "data" / "portfolio.json"
        if pf_path.exists():
            pf = json.loads(pf_path.read_text(encoding="utf-8"))
            context["portfolio_symbols"] = [
                p.get("symbol", "").upper()
                for p in pf.get("positions", [])
                if p.get("symbol")
            ]
    except Exception:
        pass

    return context


# ────────────────────────── Prompt Builder ──────────────────────────


def _build_prompt(symbol: str, signal_type: str, signal_data: dict,
                   context: dict) -> str:
    """LLM prompt'u oluştur — kompakt ve odaklı."""
    lines = []
    lines.append(f"FİNZORA AI — WATCHLIST GATE DEĞERLENDİRMESİ")
    lines.append(f"Hisse: {symbol}")
    lines.append(f"Sinyal kaynağı: {signal_type}")
    lines.append(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Sinyal verileri
    lines.append("SİNYAL VERİSİ:")
    for k, v in signal_data.items():
        lines.append(f"  {k}: {v}")
    lines.append("")

    # Market bağlamı
    lines.append("MARKET BAĞLAMI:")
    lines.append(f"  Watchlist: {context['watchlist_size']}/{context['watchlist_max']} dolu")
    if context["portfolio_symbols"]:
        lines.append(f"  Portföy: {', '.join(context['portfolio_symbols'])}")

    if context["active_themes"]:
        lines.append("  Aktif temalar (skor sıralı):")
        for t in sorted(context["active_themes"],
                         key=lambda x: -x["score"])[:6]:
            lines.append(f"    [{t['stage']:8}] {t['name']}: score {t['score']}")

    if context["dying_themes"]:
        lines.append("  Sönüşte temalar:")
        for t in context["dying_themes"][:3]:
            lines.append(f"    [sönüs] {t['name']}: score {t['score']}")
    lines.append("")

    # Sinyal tipine göre özel rehber
    sig_guidance = _get_signal_guidance(signal_type)
    if sig_guidance:
        lines.append("BU SİNYAL TİPİ İÇİN REHBER:")
        lines.append(sig_guidance)
        lines.append("")

    # Görev
    lines.append("""GÖREV:
Bu hisseyi watchlist'e eklemeli misin? Aşağıdaki kriterleri değerlendir:

1. SİNYAL KALİTESİ: Sinyal verisi güçlü mü, gürültü mü?
2. TEMA BAĞLAMI: Aktif bir temaya bağlanıyor mu? Sönüş tema'sındaysa RED.
3. ÇAKIŞMA: Hisse zaten portföyde mi? (varsa RED)
4. KALİTE: Mikro-cap hisse mi (genelde RED), büyük cap mi (genelde EKLE)?
5. VALUE TRAP: Fair value sinyali varsa, "ucuz olduğu için ucuz" mu?

KARAR:
  - "EKLE": sinyal güçlü, tema uyumlu, kalite OK → watchlist'e ekle
  - "RED": zayıf sinyal, kötü bağlam, value trap, çakışma → ekleme

ÇIKTI (KESİNLİKLE JSON, başka metin yok):
{
  "action": "EKLE" | "RED",
  "score": 0-100 (sinyal gücü skoru),
  "reason": "1 cümle gerekçe (Türkçe)",
  "theme_match": "tema_id veya null (bağlanıyorsa)",
  "cautions": ["liste, varsa risk uyarıları", "yoksa boş []"]
}""")

    return "\n".join(lines)


def _get_signal_guidance(signal_type: str) -> str:
    """Sinyal tipine özel değerlendirme rehberi."""
    if signal_type == "analist_revize":
        return ("Analist hedef revizyonu güçlüyse (3+ raise, ort.>5%, 0 lower) "
                "ve hisse aktif tema'da ise EKLE. Tek raise veya consensus zayıfsa RED.")
    if signal_type == "fair_value_iskonto":
        return ("Analist target %25+ üstüyse fırsat olabilir, ama: "
                "(a) hisse value trap mı? (low margin, high debt, declining revenue), "
                "(b) sektör downtrend'de mi? "
                "Bunlar varsa RED. Kalite şirket + iskonto = EKLE.")
    if signal_type == "manuel":
        return ("Zeynel manuel ekledi. RED nadiren — sadece tehlikeli yönlere "
                "(spekülatif penny stock, sönüş tema) işaret ediyorsa. "
                "Genelde EKLE + tema önerisi.")
    if signal_type == "tematik":
        return "Tematik keşif sinyali. Tema aktifse (dogus/yukselis/olgun) EKLE."
    return ""


# ────────────────────────── LLM Call ──────────────────────────


def _call_llm(prompt: str) -> Optional[dict]:
    """OpenRouter Kimi'yi çağır."""
    if not OPENROUTER_API_KEY:
        _log("OPENROUTER_API_KEY yok — gate atlanıyor")
        return None
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system",
                     "content": "Sen ABD piyasası watchlist gatekeeper'ısın. "
                                "Sadece JSON döndür."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
                "temperature": 0.2,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            _log(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            lines_c = content.split("\n")
            content = "\n".join(
                lines_c[1:-1] if lines_c[-1].strip() == "```" else lines_c[1:]
            ).strip()
        return json.loads(content, strict=False)
    except json.JSONDecodeError as e:
        _log(f"JSON parse hata: {e}")
        return None
    except Exception as e:
        _log(f"LLM çağrı hata: {e}")
        return None


# ────────────────────────── Public API ──────────────────────────


def evaluate_signal(symbol: str, signal_type: str,
                    signal_data: dict,
                    market_context: Optional[dict] = None) -> dict:
    """
    Bir besleyici sinyalini LLM ile değerlendir.

    Args:
        symbol: Ticker (örn. 'NVDA')
        signal_type: 'analist_revize' | 'fair_value_iskonto' |
                     'manuel' | 'tematik'
        signal_data: kaynağa özgü ham veri (sözlük)
        market_context: opsiyonel, verilmezse otomatik oluşturulur

    Returns:
        {
          "action": "EKLE" | "RED" | "HATA",
          "score": int (0-100),
          "reason": str,
          "theme_match": str | None,
          "cautions": list[str],
        }
    """
    symbol = symbol.upper().strip()

    # 1. Çakışma ön-kontrolü (LLM'e gitmeden)
    try:
        from agent.watchlist import is_in_portfolio, is_excluded
        if is_in_portfolio(symbol):
            return {"action": "RED", "score": 0,
                    "reason": "Zaten portföyde", "theme_match": None,
                    "cautions": ["portfolio_skip"]}
        if is_excluded(symbol):
            return {"action": "RED", "score": 0,
                    "reason": "Excluded listesinde", "theme_match": None,
                    "cautions": ["excluded_skip"]}
    except Exception:
        pass

    # 2. Context'i hazırla
    if market_context is None:
        market_context = _build_default_context()

    # 3. Prompt + LLM çağrısı
    prompt = _build_prompt(symbol, signal_type, signal_data, market_context)
    result = _call_llm(prompt)

    if not result:
        # Fallback: AI çağrısı başarısız → çağıran karar versin
        if FALLBACK_ON_ERROR:
            _log(f"{symbol} gate başarısız — fallback EKLE (çağıranın eski mantığı)")
            return {"action": "EKLE", "score": 50,
                    "reason": "AI gate başarısız, fallback eski mantığa",
                    "theme_match": None, "cautions": ["gate_failed"]}
        return {"action": "HATA", "score": 0,
                "reason": "LLM çağrısı başarısız",
                "theme_match": None, "cautions": ["llm_error"]}

    # 4. Sonucu normalize et
    action = str(result.get("action", "RED")).upper()
    if action not in ("EKLE", "RED"):
        action = "RED"

    return {
        "action": action,
        "score": int(result.get("score", 50)),
        "reason": str(result.get("reason", "—"))[:200],
        "theme_match": result.get("theme_match"),
        "cautions": result.get("cautions", []) or [],
    }


# ────────────────────────── CLI (test) ──────────────────────────


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        symbol = sys.argv[1].upper()
        signal_type = sys.argv[2] if len(sys.argv) >= 3 else "manuel"
        signal_data = {"manual_test": True, "user": "cli"}
        result = evaluate_signal(symbol, signal_type, signal_data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Kullanım: python -m agent.ai_gate SYM [signal_type]")
        print("Örnek: python -m agent.ai_gate NVDA analist_revize")
