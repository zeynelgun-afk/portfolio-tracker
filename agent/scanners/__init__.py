"""Scanner paketi — Faz 2 (17 May 2026).

Mevcut 4 scanner buraya migrate ediliyor. Polymarket kalibratörü de bu pakette.
Tam tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md

Modüller (Faz 2 sürecinde eklenecek):
    base       — BaseScanner ABC + Candidate dataclass [ADIM 2, bu dosya ile birlikte]
    thematic   — ← scripts/thematic_discovery.py        [ADIM 5]
    fair_value — ← scripts/fair_value_panel.py          [ADIM 6]
    news       — ← scripts/news_radar.py                [ADIM 7]
    analyst_revisions  — ← agent/legacy/analist_takip/monitor.py [ADIM 8]
    calibrator — Polymarket kalibratör (yeni)          [ADIM 9]
"""
from agent.scanners.base import BaseScanner, Candidate

__all__ = ["BaseScanner", "Candidate"]
