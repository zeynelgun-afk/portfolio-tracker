#!/usr/bin/env python3
"""
Finzora scripts/ için konfigürasyon shim.
agent/_config.py'yi import eder ve aynı arayüzü sunar.
"""

from pathlib import Path
import sys

# agent/ klasörünü path'e ekle
_AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

# Tüm sabitleri ve fonksiyonları yeniden export et
from _config import (  # noqa: E402
    FMP_KEY,
    FMP_BASE,
    TELEGRAM_TOKEN,
    TELEGRAM_PRIVATE_CHAT,
    TELEGRAM_GROUP_CHAT,
    ANTHROPIC_KEY,
    RAPIDAPI_KEY,
    REPO_ROOT,
    require,
    warn_if_missing,
    have_all,
)

__all__ = [
    "FMP_KEY",
    "FMP_BASE",
    "TELEGRAM_TOKEN",
    "TELEGRAM_PRIVATE_CHAT",
    "TELEGRAM_GROUP_CHAT",
    "ANTHROPIC_KEY",
    "RAPIDAPI_KEY",
    "REPO_ROOT",
    "require",
    "warn_if_missing",
    "have_all",
]
