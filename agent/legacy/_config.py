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

# Telegram env standartı (memory entry #9, #29):
#   TELEGRAM_BOT_TOKEN  → bot token (standart)
#   TELEGRAM_PRIVATE_ID → Zeynel DM (standart) — chat_id 1403072107
#   TELEGRAM_CHAT_ID    → Grup (standart) — chat_id -1003827034395
# Legacy adlar (geriye dönük uyum için fallback):
#   TELEGRAM_TOKEN, TELEGRAM_PRIVATE_CHAT, TELEGRAM_GROUP_CHAT
TELEGRAM_TOKEN = (
    os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()  # standart
    or os.environ.get("TELEGRAM_TOKEN", "").strip()    # legacy
)
TELEGRAM_PRIVATE_CHAT = (
    os.environ.get("TELEGRAM_PRIVATE_ID", "").strip()      # standart (memory)
    or os.environ.get("TELEGRAM_PRIVATE_CHAT", "").strip()  # legacy
)
TELEGRAM_GROUP_CHAT = (
    os.environ.get("TELEGRAM_CHAT_ID", "").strip()       # standart (memory: grup)
    or os.environ.get("TELEGRAM_GROUP_CHAT", "").strip()  # legacy
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# ── Opsiyonel anahtarlar ──────────────────────────────────────────────────────
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "").strip()
GH_TOKEN = os.environ.get("GH_TOKEN", "").strip() or os.environ.get("PAT_TOKEN", "").strip()

# ── Standart ad alias'ları (yeni kodun kullanması için) ──────────────────────
# Bu alias'lar geriye dönük uyumu kırmadan yeni kodun memory standart adlarını
# import etmesine izin verir. Eski kod TELEGRAM_TOKEN/PRIVATE_CHAT/GROUP_CHAT'i,
# yeni kod TELEGRAM_BOT_TOKEN/PRIVATE_ID/CHAT_ID'yi kullanabilir.
TELEGRAM_BOT_TOKEN = TELEGRAM_TOKEN
TELEGRAM_PRIVATE_ID = TELEGRAM_PRIVATE_CHAT
TELEGRAM_CHAT_ID = TELEGRAM_GROUP_CHAT

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
# Python sembolü bazlı kontrol — env adı tutarsızlığını kapsar.
# Standart adın yerine legacy ad set edilmiş olsa bile fallback çalıştıktan
# sonra sembol dolu olur, yanlış uyarı çıkmaz (önceki bug: env adına bakıyordu).
_CRITICAL_SYMBOLS = {
    "FMP_API_KEY": FMP_KEY,
    "TELEGRAM_BOT_TOKEN": TELEGRAM_TOKEN,
    "TELEGRAM_PRIVATE_ID": TELEGRAM_PRIVATE_CHAT,
}
_missing_at_load = [name for name, value in _CRITICAL_SYMBOLS.items() if not value]
if _missing_at_load and os.environ.get("FINZORA_SUPPRESS_CONFIG_WARN") != "1":
    print(
        f"[_config] Eksik kritik env: {_missing_at_load}. "
        f"Bu modülü kullanan script'ler çalışmayacak.",
        file=sys.stderr,
    )
