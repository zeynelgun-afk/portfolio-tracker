#!/usr/bin/env python3
"""
Finzora Agent — Claude Karar Motoru
"""

import os
import json
import re
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
- Gereksiz süsleme yok
- Rakamlar somut, gerekçeler net

OTONOM KARAR KURALI (SEN KARAR VER):
- Tüm aksiyonlar onay beklemeden uygulanır
- Stop-loss tetiklendiğinde: hemen çık, override yasak
- Onay istemek = kural ihlali

ETİKETLER (zorunlu):
- KESİN: FMP verisi, doğrulanmış rakam
- MUHTEMEL: güçlü kanıta dayalı çıkarım
- SPEKÜLATİF: yorum, tahmin, sezgi"""

DECISION_SCHEMA = """

---
KARAR BLOĞU (zorunlu — raporun en sonuna ekle):

```json
{
  "kararlar": [
    {
      "tip":         "EKLE | BÜYÜT | ÇIK | DÖNDÜR | STOP_GÜNCELLE | İZLE",
      "portfoy":     "balanced | aggressive | dividend | swing",
      "sembol":      "TICKER",
      "pct":         100,
      "neden":       "tek cümle gerekçe max 120 karakter",
      "hedef_fiyat": 0.0,
      "stop":        0.0,
      "tutar":       0,
      "aciliyet":    "hemen | bugün | bu_hafta",
      "dondur_al":   null
    }
  ]
}
```

Açıklamalar:
- DÖNDÜR: mevcut pozisyonu sat + yeni al. dondur_al = alınacak sembol string.
- ÇIK: pct=100 tam çıkış, pct=50 yarısı.
- EKLE: nakit kullanarak yeni pozisyon. tutar=0 nakit sınırı kadar.
- BÜYÜT: mevcut pozisyona ekle.
- İZLE: işlem yok sadece takip.
- Karar yoksa: "kararlar": []"""


def load_prompt_file(filename):
    path = REPO_ROOT / "docs" / "prompts" / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_claude_decision(user_prompt, mode="monitor", system_override=None):
    """Metin yanıt döner (eski API — geriye uyumluluk)."""
    if not ANTHROPIC_KEY:
        return "⚠️ ANTHROPIC_API_KEY bulunamadı."

    max_tokens = {"morning": 4000, "closing": 4000, "monitor": 800, "weekly": 4000}.get(mode, 1000)
    system = system_override or SYSTEM_PROMPT

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        resp = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return resp.content[0].text
    except anthropic.APIError as e:
        return f"⚠️ Claude API hatası: {e}"
    except Exception as e:
        return f"⚠️ Beklenmeyen hata: {e}"


def get_claude_decision_with_actions(user_prompt, mode="morning", system_override=None):
    """
    Rapor metni + yapılandırılmış kararlar döner.
    Returns: (rapor_str, kararlar_list)
    """
    if not ANTHROPIC_KEY:
        return "⚠️ ANTHROPIC_API_KEY bulunamadı.", []

    enhanced = user_prompt + DECISION_SCHEMA
    max_tokens = {"morning": 5000, "closing": 5000, "monitor": 1500, "weekly": 5000}.get(mode, 2000)
    system = system_override or SYSTEM_PROMPT

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        resp = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": enhanced}],
        )
        full_text = resp.content[0].text

        kararlar = []
        rapor = full_text
        match = re.search(r"```json\s*(\{.*?\})\s*```", full_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                kararlar = parsed.get("kararlar", [])
                rapor = full_text[:match.start()].rstrip()
            except json.JSONDecodeError as e:
                print(f"[ClaudeAgent] JSON parse hatası: {e}")
        else:
            print("[ClaudeAgent] JSON bloğu bulunamadı.")

        print(f"[ClaudeAgent] {len(kararlar)} karar üretildi.")
        for k in kararlar:
            print(f"  {k.get('tip','?'):12} {k.get('portfoy','?'):12} {k.get('sembol','?'):6} — {k.get('neden','')[:60]}")

        return rapor, kararlar

    except anthropic.APIError as e:
        return f"⚠️ Claude API hatası: {e}", []
    except Exception as e:
        return f"⚠️ Beklenmeyen hata: {e}", []
