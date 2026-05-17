#!/usr/bin/env python3
"""Scanner Dry-Run — kalibratör observability CLI.

Faz 2 — Adım 10b-iii-A (17 May 2026).

Bu script SADECE GÖZLEM amaçlıdır:
    - Belirtilen scanner'ı çalıştırır (scanner.scan())
    - Opsiyonel kalibrasyon uygular (CALIBRATOR_ENABLED veya --use-calibrator)
    - Sonuçları insan-okunabilir veya JSON formatında basar
    - HİÇBİR YAN ETKİ YAPMAZ:
        * watchlist'e yazmaz
        * Telegram DM göndermez
        * Tracker dosyasına event yazmaz (kalibratör fake_tracker kullanır)
        * Mevcut akıştan tamamen bağımsız

Kullanım örnekleri:
    # fair_value scanner çalıştır, kalibratör default (env var kontrol)
    python scripts/scanner_dry_run.py --scanner fair_value

    # thematic scanner, kalibratör zorla aktif
    python scripts/scanner_dry_run.py --scanner thematic --use-calibrator

    # JSON formatında çıktı, en üst 10 candidate
    python scripts/scanner_dry_run.py --scanner news --format json --limit 10

    # Tüm scanner'lardan candidate al
    python scripts/scanner_dry_run.py --scanner all

Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 10)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


SCANNER_REGISTRY = {
    "thematic": "agent.scanners.thematic:ThematicDiscoveryScanner",
    "fair_value": "agent.scanners.fair_value:FairValuePanelScanner",
    "news": "agent.scanners.news:NewsRadarScanner",
    "analyst_revisions": "agent.scanners.analyst_revisions:AnalystRevisionsScanner",
}


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [scanner-dry-run] {msg}", flush=True, file=sys.stderr)


def _load_scanner(name: str):
    """Scanner sınıfını lazy yükle ve instantiate et."""
    if name not in SCANNER_REGISTRY:
        raise ValueError(
            f"Bilinmeyen scanner: {name!r}. "
            f"Geçerli: {sorted(SCANNER_REGISTRY.keys())}"
        )
    module_path, class_name = SCANNER_REGISTRY[name].split(":")
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls()


def _make_observability_calibrator(use_calibrator: Optional[bool]):
    """Kalibratör instance'ı veya None döndür.

    Önemli: Tracker dosyasına yazmamak için performance_log_path geçici
    bir dosyaya yönlendirilir. Dry-run gerçek üretim tracker'ına
    dokunmamalı.
    """
    if use_calibrator is None:
        # env var kontrolü
        from agent.scanners.pipeline import is_calibrator_enabled
        if not is_calibrator_enabled():
            return None
    elif not use_calibrator:
        return None

    # Tracker'ı tmp'ye yönlendir — dry-run gerçek dosyaya yazmamalı
    from agent.scanners.calibrator import PolymarketCalibrator
    import tempfile
    tmp_tracker = Path(tempfile.gettempdir()) / "scanner_dry_run_tracker.json"
    log(f"Kalibratör AKTİF — tracker (geçici): {tmp_tracker}")
    return PolymarketCalibrator(performance_log_path=tmp_tracker)


def _format_text(candidates: list, scanner_name: str) -> str:
    """İnsan-okunabilir tablo formatı."""
    if not candidates:
        return f"\n=== {scanner_name} ===\nHiç candidate üretilmedi.\n"

    lines = [f"\n=== {scanner_name} ({len(candidates)} candidate) ==="]
    lines.append(
        f"{'#':<3}  {'Symbol':<8}  {'Score':>6}  {'Calib':>6}  "
        f"{'Mult':>5}  {'Flags':<25}  Reason"
    )
    lines.append("-" * 110)
    for i, c in enumerate(candidates, 1):
        flags_str = ",".join(c.calibration_flags) if c.calibration_flags else "—"
        mult_str = (
            f"{c.calibration_multiplier:.2f}"
            if c.has_calibration
            else "—"
        )
        calib_str = (
            f"{c.calibrated_score:.3f}"
            if c.has_calibration
            else "—"
        )
        reason = (c.reason or "")[:55]
        lines.append(
            f"{i:<3}  {c.symbol:<8}  {c.score:>6.3f}  {calib_str:>6}  "
            f"{mult_str:>5}  {flags_str:<25}  {reason}"
        )
    return "\n".join(lines)


def _format_json(candidates: list, scanner_name: str) -> str:
    """JSON dump (her satır bir candidate, jsonl-uyumlu output)."""
    out = {
        "scanner": scanner_name,
        "count": len(candidates),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "candidates": [
            {
                "symbol": c.symbol,
                "score": c.score,
                "calibrated_score": c.calibrated_score,
                "has_calibration": c.has_calibration,
                "calibration_multiplier": c.calibration_multiplier,
                "calibration_flags": c.calibration_flags,
                "source": c.source,
                "reason": c.reason,
                "metadata": c.metadata,
            }
            for c in candidates
        ],
    }
    return json.dumps(out, indent=2, ensure_ascii=False, default=str)


def run_scanner(
    name: str,
    calibrator,
    limit: Optional[int] = None,
) -> list:
    """Bir scanner çalıştır + opsiyonel kalibrasyon. Limit uygula."""
    from agent.scanners.pipeline import scan_and_calibrate

    log(f"Scanner '{name}' başlatılıyor…")
    scanner = _load_scanner(name)

    candidates = scan_and_calibrate(
        scanner,
        calibrator_enabled=(calibrator is not None),
        calibrator=calibrator,
    )

    log(f"Scanner '{name}' bitti: {len(candidates)} candidate")

    # Skora göre azalan sırala (yüksek skor önce)
    sort_key = lambda c: c.calibrated_score if c.has_calibration else c.score
    candidates = sorted(candidates, key=sort_key, reverse=True)

    if limit is not None and limit > 0:
        candidates = candidates[:limit]

    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scanner",
        choices=list(SCANNER_REGISTRY.keys()) + ["all"],
        required=True,
        help="Hangi scanner çalıştırılsın",
    )
    parser.add_argument(
        "--use-calibrator",
        action="store_true",
        default=None,
        help="Kalibratör'ü zorla aktif et (CALIBRATOR_ENABLED env var'ı override eder)",
    )
    parser.add_argument(
        "--no-calibrator",
        action="store_true",
        help="Kalibratör'ü zorla deaktif et (env var açık olsa bile)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output formatı (default: text)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="En üst N candidate göster (default: hepsi)",
    )
    args = parser.parse_args(argv)

    # Calibrator karar mantığı
    use_calibrator: Optional[bool] = None
    if args.no_calibrator:
        use_calibrator = False
    elif args.use_calibrator:
        use_calibrator = True

    try:
        calibrator = _make_observability_calibrator(use_calibrator)
    except Exception as e:
        log(f"HATA: kalibratör oluşturma başarısız: {e}")
        return 1

    # Scanner listesi
    scanner_names = (
        list(SCANNER_REGISTRY.keys())
        if args.scanner == "all"
        else [args.scanner]
    )

    exit_code = 0
    all_outputs: list[str] = []

    for name in scanner_names:
        try:
            candidates = run_scanner(name, calibrator, limit=args.limit)
        except Exception as e:
            log(f"HATA: '{name}' scanner çöktü: {e}")
            exit_code = 1
            continue

        if args.format == "json":
            all_outputs.append(_format_json(candidates, name))
        else:
            all_outputs.append(_format_text(candidates, name))

    # stdout'a output (stderr'a log)
    if args.format == "json" and len(all_outputs) > 1:
        # 'all' modunda JSON listesini birleştir
        print("[" + ",\n".join(all_outputs) + "]")
    else:
        print("\n".join(all_outputs))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
