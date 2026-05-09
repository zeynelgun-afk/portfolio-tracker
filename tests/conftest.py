"""
Pytest conftest — fmp_client testleri için ortak fixture'lar.

10 May 2026: _MIN_CALL_INTERVAL throttle (50ms) test'lerin sleep timing
ölçümlerini bozuyor. Test ortamında 0 set ediyoruz; throttle'a özel test
TestThrottle grubu içinde, gerektiğinde geçici set edilerek doğrulanıyor.
"""
import os
import sys

# Test ortamı için zorunlu env değişkenleri
os.environ.setdefault("FMP_API_KEY", "test_key_dummy")
os.environ.setdefault("TELEGRAM_TOKEN", "x")
os.environ.setdefault("TELEGRAM_PRIVATE_CHAT", "x")
os.environ.setdefault("ANTHROPIC_API_KEY", "x")
os.environ.setdefault("GH_TOKEN", "x")

# agent/ path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "agent"))

import pytest
import fmp_client


@pytest.fixture(autouse=True)
def disable_throttle():
    """Tüm testlerde throttle disable. Throttle test'i kendi fixture'ı ile
    geri açar (_MIN_CALL_INTERVAL doğrudan set ederek)."""
    original = fmp_client._MIN_CALL_INTERVAL
    fmp_client._MIN_CALL_INTERVAL = 0
    yield
    fmp_client._MIN_CALL_INTERVAL = original
