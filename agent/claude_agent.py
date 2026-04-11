#!/usr/bin/env python3
"""
Finzora Agent — Claude Karar Motoru
=====================================
Anthropic API ile iletişim kurar.
Otonom karar verir, uygular, kaydeder.
"""

import os
import anthropic
from pathlib import Path

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
REPO_ROOT = Path(__file__).parent.parent

SYSTEM_PROMPT = """Sen Finzora Agent'sın — Zeynel'in otonom portföy yönetim asistanısın.

KİMLİĞİN:
- Türk yatırımcılar için ABD piyasasını takip ediyorsun
- Zeynel'in portföy yönetim kurallarını (K-kuralları) eksiksiz biliyorsun
- Dürüstsün: iyi haberi olduğu kadar kötü haberi de söylersin
- Spekülatif yorumları KESİN gibi sunmazsın

KONUŞMA TARZI:
- Türkçe, sade, profesyonel
- Gereksiz süsleme yok — dolgu cümle, "mükemmel", "kesinlikle" gibi ifadeler yasak
- Rakamlar somut, gerekçeler net
- Belirsizlik varsa açıkça söyle

OTONOM KARAR KURALI (SEN KARAR VER):
- Tüm aksiyonlar onay beklemeden uygulanır
- Stop-loss tetiklendiğinde: hemen çık, override yasak
- Swing giriş/çıkış: karar ver, JSON'a yaz, Telegram'a bildir
- Portföy rebalancing: K-12 aşımında küçült
- Onay istemek = kural ihlali

ETİKETLER (zorunlu):
- KESİN: FMP verisi, doğrulanmış rakam
- MUHTEMEL: güçlü kanıta dayalı çıkarım
- SPEKÜLATİF: yorum, tahmin, sezgi"""


def load_prompt_file(filename: str) -> str:
    """docs/prompts/ klasöründen prompt dosyasını okur."""
    path = REPO_ROOT / "docs" / "prompts" / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_claude_decision(
    user_prompt: str,
    mode: str = "monitor",
    system_override: str = None
) -> str:
    """
    Claude API'ye prompt gönderir, metin yanıt döner.
    system_override: Uzman agent sistemleri için özel sistem promptu.
    """
    if not ANTHROPIC_KEY:
        return "⚠️ ANTHROPIC_API_KEY bulunamadı."

    max_tokens = {
        "morning": 4000,
        "closing": 4000,
        "monitor": 800,
        "weekly":  4000,
    }.get(mode, 1000)

    system = system_override if system_override else SYSTEM_PROMPT

    try:
        client   = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model      = "claude-opus-4-5",
            max_tokens = max_tokens,
            system     = system,
            messages   = [{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    except anthropic.APIError as e:
        return f"⚠️ Claude API hatası: {e}"
    except Exception as e:
        return f"⚠️ Beklenmeyen hata: {e}"
