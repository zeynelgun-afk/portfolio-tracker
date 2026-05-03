#!/usr/bin/env python3
"""
Finzora Agent — Kimi K2 Thinking Decision Engine (via OpenRouter)
==================================================================
File name kept as `claude_agent.py` for backward compatibility — many other
modules import `from claude_agent import get_claude_decision` etc.

Public API (stable):
  - get_claude_decision(...)              → str
  - get_claude_decision_with_actions(...)  → (str, list[dict])
  - SYSTEM_PROMPT, DECISION_SCHEMA         (re-used by other modules)
  - load_prompt_file(...)
"""

import os
import sys
import json
import re
import time
from pathlib import Path

# Observability (optional)
try:
    from observability import log_claude_call, log_decision
except ImportError:
    log_claude_call = lambda *a, **kw: None
    log_decision = lambda *a, **kw: None

# RAG retrieval (optional)
_RAG_AVAILABLE = False
try:
    _rag_dir = Path(__file__).resolve().parent.parent / "scripts" / "rag"
    if str(_rag_dir) not in sys.path:
        sys.path.insert(0, str(_rag_dir))
    from retriever import retrieve as _rag_retrieve, format_context_for_claude as _rag_format
    _RAG_AVAILABLE = True
except Exception:
    _rag_retrieve = None
    _rag_format = None

# LLM client (OpenRouter / Kimi)
from llm_client import chat as _llm_chat, DEFAULT_MODEL as _DEFAULT_MODEL, get_api_key as _get_api_key

REPO_ROOT = Path(__file__).parent.parent

# Public model name — kept under CLAUDE_MODEL var name for env compatibility
# (also accepts KIMI_MODEL via llm_client.DEFAULT_MODEL).
CLAUDE_MODEL = os.environ.get("KIMI_MODEL") or os.environ.get("CLAUDE_MODEL") or _DEFAULT_MODEL

# Mode-keyed default RAG queries
DEFAULT_RAG_QUERIES = {
    "morning": "portföy pozisyon durumu stop seviyesi açılış öncesi karar",
    "closing": "gün sonu trade sonuç kapanış performans ders",
    "monitor": "aktif pozisyon stop yakınlık fırsat izleme",
    "weekly": "sektör rotasyon tema performans haftalık değerlendirme pattern",
}


def _build_rag_context(mode: str, user_prompt: str, top_k: int = 5) -> str:
    if not _RAG_AVAILABLE or _rag_retrieve is None:
        return ""
    try:
        base = DEFAULT_RAG_QUERIES.get(mode, "")
        query = f"{base} {user_prompt[:400]}".strip()
        hits = _rag_retrieve(query, top_k=top_k)
        if not hits:
            return ""
        return _rag_format(hits, max_chars=3000)
    except Exception as e:
        print(f"[claude_agent] RAG context unavailable (ignored): {e}")
        return ""


# ── System prompt (English reasoning, Turkish output) ────────────────────────
SYSTEM_PROMPT = """You are Finzora Agent — Zeynel's autonomous portfolio management assistant.

IDENTITY:
- You track the US equity market on behalf of a Turkish investor.
- You know Zeynel's portfolio rules (the "K-rules") in full.
- You are honest: you state bad news as plainly as good news.
- You never present speculation as if it were fact.

VOICE:
- Output language is Turkish — plain, professional, no fluff.
- Numbers are concrete. Rationales are explicit.

AUTONOMY (you decide, no approvals required):
- All actions execute without confirmation.
- When a stop-loss triggers: exit immediately. Overrides are forbidden.
- Asking for approval is a rule violation.

EVIDENCE TAGS (mandatory — write them in Turkish in your output):
- KESİN: FMP-verified data, confirmed numbers.
- MUHTEMEL: strong inferential evidence.
- SPEKÜLATİF: opinion, guess, intuition."""

DECISION_SCHEMA = """

---
DECISION BLOCK (MANDATORY — append at the very end of the report):

```json
{
  "kararlar": [
    {
      "tip":         "EKLE | BÜYÜT | ÇIK | DÖNDÜR | STOP_GÜNCELLE | İZLE",
      "portfoy":     "balanced | aggressive | dividend | swing",
      "sembol":      "TICKER",
      "pct":         100,
      "neden":       "single-sentence rationale, max 120 chars, in Turkish",
      "hedef_fiyat": 0.0,
      "stop":        0.0,
      "tutar":       0,
      "aciliyet":    "hemen | bugün | bu_hafta",
      "dondur_al":   null
    }
  ]
}
```

Field semantics:
- DÖNDÜR: sell current position + buy a new one. dondur_al = ticker string of the new buy.
- ÇIK: pct=100 full exit, pct=50 half exit.
- EKLE: open a new position from cash. tutar=0 means "use available cash limit".
- BÜYÜT: scale into an existing position.
- İZLE: no trade, watch only.
- If no actions: "kararlar": []

CRITICAL: keep JSON keys EXACTLY as shown (Turkish), do NOT translate keys.
The values like "tip" enum stay in Turkish too — they are matched by downstream code."""


def load_prompt_file(filename):
    path = REPO_ROOT / "docs" / "prompts" / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# Token budgets per mode.
# Kimi K2 thinking emits a sizable internal reasoning trace that counts toward
# output tokens. Empirically ~50-70% of the budget is consumed by reasoning, so
# we ~doubled the previous Claude-tuned values to keep the post-reasoning report
# untruncated.
_MAX_TOKENS = {
    "morning":         16000,  # was 8000 — large multi-section report
    "closing":         16000,  # was 8000
    "weekly":          16000,  # was 8000
    "monitor":          4000,  # was 1500
    "specialist":       6000,  # was 3000
    "exit_judgement":   2500,  # was 800
}


def get_claude_decision(user_prompt, mode="monitor", system_override=None, rag_enabled=True):
    """Plain text reply (legacy API — preserved for backward compatibility)."""
    if not _get_api_key():
        return "⚠️ OPENROUTER_API_KEY (veya ANTHROPIC_API_KEY) bulunamadı."

    max_tokens = _MAX_TOKENS.get(mode, 4000)
    base_system = system_override or SYSTEM_PROMPT

    rag_ctx = _build_rag_context(mode, user_prompt, top_k=5) if rag_enabled else ""
    system = base_system + ("\n\n" + rag_ctx if rag_ctx else "")

    _t0 = time.time()
    _in, _out = 0, 0
    _success = False
    _error = None

    try:
        resp = _llm_chat(
            system=system,
            user=user_prompt,
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        _in, _out = resp.input_tokens, resp.output_tokens
        if resp.finish_reason == "length":
            print(f"[ClaudeAgent/legacy] ⚠️ max_tokens={max_tokens} doldu, "
                  f"yanıt kesik. output_tokens={_out}")
        _success = True
        return resp.text
    except Exception as e:
        _error = f"{type(e).__name__}: {str(e)[:200]}"
        return f"⚠️ LLM API hatası: {e}"
    finally:
        log_claude_call(
            mode=mode,
            model=CLAUDE_MODEL,
            input_tokens=_in,
            output_tokens=_out,
            duration_ms=int((time.time() - _t0) * 1000),
            success=_success,
            context_chars=len(system) + len(user_prompt),
            decisions_count=0,
            error=_error,
        )


# Alias under new name — preferred for new callers
get_kimi_decision = get_claude_decision


def get_claude_decision_with_actions(user_prompt, mode="morning", system_override=None, rag_enabled=True):
    """
    Returns (report_text, decisions_list).
    """
    if not _get_api_key():
        return "⚠️ OPENROUTER_API_KEY (veya ANTHROPIC_API_KEY) bulunamadı.", []

    enhanced = user_prompt + DECISION_SCHEMA
    max_tokens = _MAX_TOKENS.get(mode, 4000)
    base_system = system_override or SYSTEM_PROMPT

    rag_ctx = _build_rag_context(mode, user_prompt, top_k=5) if rag_enabled else ""
    system = base_system + ("\n\n" + rag_ctx if rag_ctx else "")

    _t0 = time.time()
    _in, _out = 0, 0
    _success = False
    _error = None
    kararlar = []
    rapor = ""

    try:
        resp = _llm_chat(
            system=system,
            user=enhanced,
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        _in, _out = resp.input_tokens, resp.output_tokens
        full_text = resp.text

        if resp.finish_reason == "length":
            print(f"[ClaudeAgent] ⚠️ UYARI: max_tokens={max_tokens} sınırı dolmuş! "
                  f"Rapor kesilmiş olabilir, JSON karar bloğu kayıp olabilir. "
                  f"output_tokens={_out}")
            try:
                from event_logger import kaydet as _le
                _le(seviye="uyari",
                    baslik=f"LLM max_tokens sınırı doldu ({mode})",
                    detay=f"max_tokens={max_tokens}, output={_out}, "
                          f"rapor son 200 karakter: …{full_text[-200:]}",
                    kaynak="claude_agent")
            except Exception:
                pass

        rapor = full_text

        # Closed JSON block first
        match = re.search(r"```json\s*(\{.*?\})\s*```", full_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                kararlar = parsed.get("kararlar", [])
                rapor = full_text[:match.start()].rstrip()
            except json.JSONDecodeError as e:
                print(f"[ClaudeAgent] JSON parse hatası: {e}")
        else:
            # Truncated JSON recovery (max_tokens edge case)
            open_match = re.search(r"```json\s*(\{.*)", full_text, re.DOTALL)
            if open_match:
                kismi = open_match.group(1).rstrip().rstrip("`").rstrip()
                try:
                    karar_match = re.search(r'"kararlar"\s*:\s*\[(.*)', kismi, re.DOTALL)
                    if karar_match:
                        ic = karar_match.group(1)
                        depth = 0
                        son_kapali = -1
                        for i, ch in enumerate(ic):
                            if ch == "{":
                                depth += 1
                            elif ch == "}":
                                depth -= 1
                                if depth == 0:
                                    son_kapali = i
                        if son_kapali > 0:
                            blok = "[" + ic[:son_kapali+1] + "]"
                            try:
                                arr = json.loads(blok)
                                kararlar = arr if isinstance(arr, list) else []
                                print(f"[ClaudeAgent] ⚠️ Kesik JSON kurtarıldı: "
                                      f"{len(kararlar)} karar geri alındı")
                                rapor = full_text[:open_match.start()].rstrip()
                            except json.JSONDecodeError as e2:
                                print(f"[ClaudeAgent] Kesik JSON onarım da başarısız: {e2}")
                except Exception as ex:
                    print(f"[ClaudeAgent] Kesik JSON onarım hatası: {ex}")
            else:
                print("[ClaudeAgent] JSON bloğu bulunamadı.")

        print(f"[ClaudeAgent] {len(kararlar)} karar üretildi.")
        for k in kararlar:
            print(f"  {k.get('tip','?'):12} {k.get('portfoy','?'):12} "
                  f"{k.get('sembol','?'):6} — {k.get('neden','')[:60]}")

        _success = True
        return rapor, kararlar

    except Exception as e:
        _error = f"{type(e).__name__}: {str(e)[:200]}"
        return f"⚠️ LLM API hatası: {e}", []
    finally:
        claude_call_id = log_claude_call(
            mode=mode,
            model=CLAUDE_MODEL,
            input_tokens=_in,
            output_tokens=_out,
            duration_ms=int((time.time() - _t0) * 1000),
            success=_success,
            context_chars=len(system) + len(enhanced),
            decisions_count=len(kararlar),
            error=_error,
        )
        for k in kararlar:
            decision_id = log_decision(
                mode=mode,
                tip=k.get("tip", "?"),
                portfoy=k.get("portfoy", "?"),
                sembol=k.get("sembol", "?"),
                neden=k.get("neden", ""),
                pct=k.get("pct", 0) or 0,
                hedef_fiyat=k.get("hedef_fiyat"),
                stop=k.get("stop"),
                aciliyet=k.get("aciliyet", "bugün"),
                claude_call_id=claude_call_id,
                executed=False,
            )
            if decision_id:
                k["_decision_id"] = decision_id


# Alias under new name — preferred for new callers
get_kimi_decision_with_actions = get_claude_decision_with_actions
