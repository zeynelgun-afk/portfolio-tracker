"""Scanner orchestration — scan + opsiyonel kalibrasyon.

Faz 2 — Adım 10b-ii (17 May 2026).

Bu modül scanner'ların scan() metodlarına DOKUNMAZ. Pure transform
disiplini korunur. Üst seviye orchestration burada:

    pipeline.scan_and_calibrate(scanner) → Candidate listesi
        1. scanner.scan() çağır (her zaman çağrılır)
        2. Feature flag CALIBRATOR_ENABLED kontrol et
        3. Flag açıksa PolymarketCalibrator.calibrate() uygula
        4. Sonucu döndür

Feature flag yaklaşımı (CALIBRATOR_ENABLED env var):
    Üretim default: KAPALI. Adım 10b-iii'de AI Gate ve CLI entegrasyonu
    tamamlandığında flag açılır, kademeli rollout yapılır.

    Değerler (case-insensitive):
        true / 1 / yes  → kalibrator aktif
        false / 0 / no / boş / yok  → kalibrator pasif (default)

CLI entegrasyonu Adım 10b-iii kapsamında. Şu an hiçbir scanner script'i
bu helper'ı çağırmıyor — sadece test ve manuel kullanım için hazır.

Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 2, 10)
"""
from __future__ import annotations

import os
from typing import Any, Optional

from agent.scanners.base import BaseScanner, Candidate


_CALIBRATOR_ENV_VAR = "CALIBRATOR_ENABLED"
_TRUTHY_VALUES = {"true", "1", "yes"}


def is_calibrator_enabled() -> bool:
    """Feature flag kontrolü — CALIBRATOR_ENABLED env var.

    True değerleri: "true", "1", "yes" (case-insensitive, trim'li).
    Diğer her şey False (env var hiç yoksa veya boş ise default kapalı).
    """
    val = os.environ.get(_CALIBRATOR_ENV_VAR, "").strip().lower()
    return val in _TRUTHY_VALUES


def scan_and_calibrate(
    scanner: BaseScanner,
    calibrator_enabled: Optional[bool] = None,
    calibrator: Optional[Any] = None,
) -> list[Candidate]:
    """Scanner'ı çalıştır + flag açıksa kalibrasyon uygula.

    Args:
        scanner: scan() metodu sağlayan BaseScanner instance.
            scan() her zaman çağrılır — bu helper bypass etmez.
        calibrator_enabled: None ise CALIBRATOR_ENABLED env var'dan
            okunur. True/False ise env var'ı override eder (test için).
        calibrator: None ise PolymarketCalibrator() default oluşturulur.
            Instance verilirse o kullanılır (dependency injection).

    Returns:
        Candidate listesi. Flag kapalı → scan() çıktısı aynen.
        Flag açık + candidates dolu → kalibre edilmiş liste.
        Flag açık + candidates boş → boş liste (kalibratör hiç çağrılmaz).

    Yan etki:
        Kalibratör tracker'a event kaydeder (data/polymarket_calibrator_performance.json).
        scan() çağrısının kendi yan etkileri varsa onlar da çalışır (FMP fetch vs).
        Bu fonksiyon kendi başına state yazmaz.
    """
    candidates = scanner.scan()

    if calibrator_enabled is None:
        calibrator_enabled = is_calibrator_enabled()

    if not calibrator_enabled:
        return candidates

    if not candidates:
        # Boş listede kalibratör çağırmaya gerek yok — gereksiz I/O atlanır
        return candidates

    if calibrator is None:
        # Lazy import — flag kapalıysa hiç yüklenmez
        from agent.scanners.calibrator import PolymarketCalibrator
        calibrator = PolymarketCalibrator()

    return calibrator.calibrate(candidates)
