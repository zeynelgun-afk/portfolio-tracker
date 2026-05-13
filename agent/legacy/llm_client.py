#!/usr/bin/env python3
"""
Finzora — Kimi K2 Thinking client (OpenRouter)
================================================
Centralized OpenAI-compatible client targeting OpenRouter.

Default model: moonshotai/kimi-k2-thinking
Override:      KIMI_MODEL env var

API key precedence:
  1. OPENROUTER_API_KEY  (primary)
  2. ANTHROPIC_API_KEY   (legacy fallback — keeps deploys alive during migration)
"""

from __future__ import annotations
import os
import time
from typing import Optional

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.environ.get("KIMI_MODEL", "moonshotai/kimi-k2-thinking")
DEFAULT_TIMEOUT = int(os.environ.get("KIMI_TIMEOUT", "120"))

# Standardized output-language directive appended to every system prompt.
# Reasoning instructions stay English (more stable for the model);
# user-facing output stays Turkish; JSON keys stay verbatim.
LANGUAGE_POLICY = """

LANGUAGE POLICY (strict):
- All instructions above are in English for stability.
- Final user-facing report MUST be written in Turkish (professional, plain).
- JSON output keys MUST remain exactly as specified (do NOT translate keys).
- Do NOT translate ticker symbols, numeric values, or proper nouns.
- Use Turkish for prose, comments, rationales; keep tickers/units/keys verbatim."""


class LLMResponse:
    """Lightweight container — mimics what callers used from anthropic SDK."""
    __slots__ = ("text", "input_tokens", "output_tokens", "finish_reason", "model", "raw")

    def __init__(self, text: str, input_tokens: int, output_tokens: int,
                 finish_reason: str, model: str, raw=None):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.finish_reason = finish_reason  # "stop" | "length" | "content_filter" | ...
        self.model = model
        self.raw = raw


def get_api_key() -> str:
    """OPENROUTER_API_KEY first, fall back to ANTHROPIC_API_KEY for legacy compat."""
    return (os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or "")


def get_client(timeout: Optional[int] = None):
    """Lazy-import OpenAI SDK; returns a configured client or raises."""
    from openai import OpenAI  # local import → import-time errors don't break callers
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "No OPENROUTER_API_KEY (nor legacy ANTHROPIC_API_KEY) found in environment."
        )
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        timeout=timeout or DEFAULT_TIMEOUT,
    )


def chat(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    timeout: Optional[int] = None,
    apply_language_policy: bool = True,
    extra_messages: Optional[list] = None,
) -> LLMResponse:
    """
    One-shot chat completion against OpenRouter / Kimi.

    `apply_language_policy=True` automatically appends the LANGUAGE_POLICY block
    so reports stay Turkish while reasoning stays English.

    `extra_messages` lets callers inject prior assistant/user turns if needed.
    """
    client = get_client(timeout=timeout)
    used_model = model or DEFAULT_MODEL

    sys_msg = system + (LANGUAGE_POLICY if apply_language_policy else "")
    messages = [{"role": "system", "content": sys_msg}]
    if extra_messages:
        messages.extend(extra_messages)
    messages.append({"role": "user", "content": user})

    resp = client.chat.completions.create(
        model=used_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    choice = resp.choices[0]
    text = choice.message.content or ""
    finish = choice.finish_reason or "unknown"

    usage = getattr(resp, "usage", None)
    in_tok = getattr(usage, "prompt_tokens", 0) or 0
    out_tok = getattr(usage, "completion_tokens", 0) or 0

    return LLMResponse(
        text=text,
        input_tokens=in_tok,
        output_tokens=out_tok,
        finish_reason=finish,
        model=used_model,
        raw=resp,
    )


def is_available() -> bool:
    """Cheap check for callers that want to gracefully skip when no key is set."""
    return bool(get_api_key())
