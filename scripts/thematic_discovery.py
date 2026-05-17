#!/usr/bin/env python3
"""
DEPRECATED — Bu dosya 17 Mayıs 2026 itibarıyla agent/scanners/thematic.py'a taşındı.

Bu shim geriye dönük uyumluluk için tutuluyor; yeni kodda doğrudan
`agent.scanners.thematic` modülünü kullanın:

    from agent.scanners.thematic import ThematicDiscoveryScanner
    scanner = ThematicDiscoveryScanner(mode="daily")
    candidates = scanner.scan()

Workflow ve harici çağrılar için bu dosya hâlâ çalışır, çağrıyı yeni
konuma yönlendirir.

Faz 2 — Adım 5: Scanner konsolidasyonu (17 Mayıs 2026)
"""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/thematic_discovery.py taşındı: agent/scanners/thematic.py kullanın "
    "(bu shim ileride kaldırılacak)",
    DeprecationWarning,
    stacklevel=2,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NEW_PATH = _REPO_ROOT / "agent" / "scanners" / "thematic.py"

if not _NEW_PATH.exists():
    print(f"FATAL: yeni konum bulunamadı: {_NEW_PATH}", file=sys.stderr)
    sys.exit(2)

runpy.run_path(str(_NEW_PATH), run_name="__main__")
