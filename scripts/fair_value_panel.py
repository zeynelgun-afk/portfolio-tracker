#!/usr/bin/env python3
"""
DEPRECATED — Bu dosya 17 Mayıs 2026 itibarıyla agent/scanners/fair_value.py'a taşındı.

Bu shim geriye dönük uyumluluk için tutuluyor; yeni kodda doğrudan
`agent.scanners.fair_value` modülünü kullanın:

    from agent.scanners.fair_value import FairValuePanelScanner
    scanner = FairValuePanelScanner(min_potential_pct=25.0)
    candidates = scanner.scan()

Workflow ve harici çağrılar için bu dosya hâlâ çalışır, çağrıyı yeni
konuma yönlendirir.

Faz 2 — Adım 6: Scanner konsolidasyonu (17 Mayıs 2026)
"""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/fair_value_panel.py taşındı: agent/scanners/fair_value.py kullanın "
    "(bu shim ileride kaldırılacak)",
    DeprecationWarning,
    stacklevel=2,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NEW_PATH = _REPO_ROOT / "agent" / "scanners" / "fair_value.py"

if not _NEW_PATH.exists():
    print(f"FATAL: yeni konum bulunamadı: {_NEW_PATH}", file=sys.stderr)
    sys.exit(2)

runpy.run_path(str(_NEW_PATH), run_name="__main__")
