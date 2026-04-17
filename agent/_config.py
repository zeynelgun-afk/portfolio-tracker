#!/usr/bin/env python3
"""
Finzora — Merkezi Konfigürasyon
================================
Tüm API anahtarları ve ortam değişkenleri TEK kaynaktan okunur.

KULLANIM:
    from agent._config import FMP_KEY, TELEGRAM_TOKEN, ANTHROPIC_KEY

KURAL:
- Hardcoded fallback YASAK. Eksik env → fail fast.
- Local geliştirme için: .env dosyası kullan veya export et.
"""

import os
import sys
from pathlib import Path

# ── Zorunlu anahtarlar ────────────────────────────────────────────────────────
FMP_KEY = os.environ.get("FMP_API_KEY", "").strip()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_PRIVATE_CHAT = os.environ.get("TELEGRAM_PRIVATE_CHAT", "").strip()
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# ── Opsiyonel anahtarlar ──────────────────────────────────────────────────────
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
TELEGRAM_GROUP_CHAT = os.environ.get("TELEGRAM_GROUP_CHAT", "").strip()

# ── Sabitler ──────────────────────────────────────────────────────────────────
FMP_BASE = "https://financialmodelingprep.com/stable"
REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Doğrulama yardımcıları ────────────────────────────────────────────────────

def require(name: str) -> str:
    """
    İsimlendirilmiş zorunlu ortam değişkenini döner.
    Eksikse RuntimeError fırlatır (geriye uyumluluk için hard fail).
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} ortam değişkeni boş. "
            f"GitHub Secrets'a ekle veya local'de export et."
        )
    return value


def warn_if_missing(required_keys: list[str]) -> list[str]:
    """
    Eksik anahtarları uyarır ama crash etmez.
    Dönen liste: Eksik anahtar isimleri.
    """
    missing = []
    for key in required_keys:
        if not os.environ.get(key, "").strip():
            missing.append(key)
    if missing:
        print(
            f"[_config] UYARI: Eksik ortam değişkenleri: {', '.join(missing)}",
            file=sys.stderr,
        )
    return missing


def have_all(required_keys: list[str]) -> bool:
    """Tüm anahtarlar mevcut mu?"""
    return all(os.environ.get(k, "").strip() for k in required_keys)


# ── Modül yüklendiğinde erken uyarı ──────────────────────────────────────────
# Kritik eksikleri sessizce bırakmak yerine stderr'e yaz.
_CRITICAL = ["FMP_API_KEY", "TELEGRAM_TOKEN", "TELEGRAM_PRIVATE_CHAT"]
_missing_at_load = [k for k in _CRITICAL if not os.environ.get(k, "").strip()]
if _missing_at_load and os.environ.get("FINZORA_SUPPRESS_CONFIG_WARN") != "1":
    print(
        f"[_config] Eksik kritik env: {_missing_at_load}. "
        f"Bu modülü kullanan script'ler çalışmayacak.",
        file=sys.stderr,
    )
