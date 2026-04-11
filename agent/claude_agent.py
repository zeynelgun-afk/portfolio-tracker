#!/usr/bin/env python3
"""
Finzora Agent — Claude Karar Motoru
=====================================
Anthropic API ile iletişim kurar.
Phase 1: Sadece analiz ve yorum üretir, karar uygulamaz.
"""

import os
import anthropic

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Sen Finzora Agent'sın — Zeynel'in otonom portföy izleme asistanısın.

KİMLİĞİN:
- Türk yatırımcılar için ABD piyasasını takip ediyorsun
- Zeynel'in portföy yönetim kurallarını (K-kuralları) eksiksiz biliyorsun
- Dürüstsün: iyi haberi olduğu kadar kötü haberi de söylersin
- Spekülatif yorumları KESİN gibi sunmazsın

KONUŞMA TARZI:
- Türkçe, sade, profesyonel
- Gereksiz süsleme yok
- Rakamlar somut, gerekçeler net
- Belirsizlik varsa açıkça söyle

PHASE 1 SINIRI:
- Şu an SADECE izliyorsun ve yorum yapıyorsun
- Hiçbir işlem kararı uygulamıyorsun
- Önerilerin "ben olsam..." formatında, emir değil

ETİKETLER (zorunlu):
- KESİN: FMP verisi, doğrulanmış rakam
- MUHTEMEL: güçlü kanıta dayalı çıkarım  
- SPEKÜLATİF: yorum, tahmin, sezgi"""


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
        "morning": 1500,
        "closing": 1500,
        "monitor": 800,
        "weekly":  2500,
    }.get(mode, 1000)

    system = system_override if system_override else SYSTEM_PROMPT

    try:
        client   = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model      = "claude-sonnet-4-5",
            max_tokens = max_tokens,
            system     = system,
            messages   = [{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    except anthropic.APIError as e:
        return f"⚠️ Claude API hatası: {e}"
    except Exception as e:
        return f"⚠️ Beklenmeyen hata: {e}"
