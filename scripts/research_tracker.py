#!/usr/bin/env python3
"""
DEPRECATED — Bu dosya 17 Mayıs 2026 itibarıyla agent/reports/research.py'a taşındı.

Bu shim geriye dönük uyumluluk için tutuluyor; yeni kodda doğrudan
`agent.reports.research` modülünü kullanın.

Workflow ve harici çağrılar için bu dosya hâlâ çalışır, çağrıyı yeni
konuma yönlendirir.

Faz 1 — Reports konsolidasyonu (17 Mayıs 2026)
"""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/research_tracker.py taşındı: agent/reports/research.py kullanın "
    "(bu shim ileride kaldırılacak)",
    DeprecationWarning,
    stacklevel=2,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NEW_PATH = _REPO_ROOT / "agent" / "reports" / "research.py"

if not _NEW_PATH.exists():
    print(f"FATAL: yeni konum bulunamadı: {_NEW_PATH}", file=sys.stderr)
    sys.exit(2)

# Yeni modülü `__main__` olarak çalıştır — orijinal CLI davranışı korunur
runpy.run_path(str(_NEW_PATH), run_name="__main__")
