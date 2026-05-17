"""BaseScanner interface + Candidate dataclass.

Tasarım dokümanı: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 4)

Candidate, scanner çıktısının standart birimidir. AI Gate ve kalibratör
bu birim üzerinden çalışır. Kalibratör (Polymarket) `calibration_multiplier`
ve `calibration_flags` alanlarını doldurur; ham `score` asla değişmez —
böylece hangi sinyalin kalibrasyonsuz hangi puana ulaştığı her zaman izlenebilir.

Faz 2 ile başladı (17 May 2026).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


# Çarpan sabitleri — tasarım dokümanı Bölüm 8'deki tablodan
CALIBRATION_MIN: float = 0.75
CALIBRATION_MAX: float = 1.20
CALIBRATION_NEUTRAL: float = 1.0

# İzin verilen bayraklar (whitelist) — bilinmeyen bayrak hata fırlatır
ALLOWED_FLAGS: frozenset[str] = frozenset({
    "pm_confirm",
    "pm_confirm_weak",
    "pm_conflict_weak",
    "pm_conflict",
})

# İzin verilen scanner source isimleri — bilinmeyen source uyarı verir ama hata değil
KNOWN_SOURCES: frozenset[str] = frozenset({
    "thematic",
    "fair_value",
    "news",
    "analyst_revisions",
})


@dataclass
class Candidate:
    """Scanner çıktısı — AI Gate'in tükettiği standart birim.

    Attributes:
        symbol: Ticker (büyük harfle normalize edilir).
        score: Ham güven skoru, 0.0 — 1.0 aralığında.
        reason: Türkçe insan-okur açıklama. AI Gate prompt'una bu metin girer.
        source: Sinyali üreten scanner'ın adı (KNOWN_SOURCES'tan biri tercih edilir).
        metadata: Scanner-spesifik ek alanlar (örn. {"theme_id": "ai-supply-chain"}).
        calibration_multiplier: Kalibratör tarafından yazılır (0.75 — 1.20).
        calibration_flags: Kalibratör bayrakları (örn. ["pm_confirm"]).

    Properties:
        calibrated_score: score * multiplier, 1.0 ile sınırlandırılmış.
    """
    symbol: str
    score: float
    reason: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    calibration_multiplier: float = CALIBRATION_NEUTRAL
    calibration_flags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # symbol normalize
        self.symbol = (self.symbol or "").strip().upper()
        if not self.symbol:
            raise ValueError("Candidate.symbol boş olamaz")

        # score sınırlama
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"Candidate.score 0.0-1.0 aralığında olmalı, alındı: {self.score}"
            )

        # source uyarısı (hata değil — yeni scanner eklerken esneklik)
        if self.source not in KNOWN_SOURCES:
            # Sessiz devam — yeni scanner geliştirilirken bilinçli durum olabilir
            pass

        # multiplier aralık kontrolü
        if not CALIBRATION_MIN <= self.calibration_multiplier <= CALIBRATION_MAX:
            raise ValueError(
                f"calibration_multiplier {CALIBRATION_MIN}-{CALIBRATION_MAX} "
                f"aralığında olmalı, alındı: {self.calibration_multiplier}"
            )

        # bayrak whitelist kontrolü
        for flag in self.calibration_flags:
            if flag not in ALLOWED_FLAGS:
                raise ValueError(
                    f"Bilinmeyen calibration_flag: {flag!r}. "
                    f"İzin verilenler: {sorted(ALLOWED_FLAGS)}"
                )

    @property
    def calibrated_score(self) -> float:
        """Kalibrasyon uygulanmış skor. 1.0 ile sınırlı."""
        return min(1.0, self.score * self.calibration_multiplier)

    @property
    def has_calibration(self) -> bool:
        """Kalibratör bu candidate'e dokundu mu?"""
        return (
            self.calibration_multiplier != CALIBRATION_NEUTRAL
            or len(self.calibration_flags) > 0
        )

    def apply_calibration(
        self,
        multiplier: float,
        flags: list[str],
    ) -> None:
        """Kalibratör tarafından çağrılır. Çoklu eşleşmede tekrar çağrılabilir.

        Çoklu çağrı semantiği (tasarım dokümanı Bölüm 17):
        En aşırı çarpan kazanır — yani min(mevcut, yeni) eğer ikisi de <1.0,
        veya max(mevcut, yeni) eğer ikisi de >1.0. Karışık durumda (biri >1
        biri <1) çelişki kazanır (daha düşük çarpan).
        """
        if not CALIBRATION_MIN <= multiplier <= CALIBRATION_MAX:
            raise ValueError(
                f"multiplier {CALIBRATION_MIN}-{CALIBRATION_MAX} aralığında olmalı"
            )
        for flag in flags:
            if flag not in ALLOWED_FLAGS:
                raise ValueError(f"Bilinmeyen flag: {flag!r}")

        # En aşırı kazanır — çelişki önceliklidir (asimetrik downside protection)
        if self.calibration_multiplier == CALIBRATION_NEUTRAL:
            self.calibration_multiplier = multiplier
        elif multiplier < CALIBRATION_NEUTRAL and self.calibration_multiplier < CALIBRATION_NEUTRAL:
            # İkisi de çelişki — daha düşük (daha sert) olan kazanır
            self.calibration_multiplier = min(self.calibration_multiplier, multiplier)
        elif multiplier > CALIBRATION_NEUTRAL and self.calibration_multiplier > CALIBRATION_NEUTRAL:
            # İkisi de doğrulama — daha yüksek olan kazanır
            self.calibration_multiplier = max(self.calibration_multiplier, multiplier)
        else:
            # Karışık — çelişki kazanır (downside protection)
            self.calibration_multiplier = min(self.calibration_multiplier, multiplier)

        # Bayraklar birikir (duplicate'ler tekilleştirilir, sıra korunur)
        for flag in flags:
            if flag not in self.calibration_flags:
                self.calibration_flags.append(flag)

    def to_dict(self) -> dict[str, Any]:
        """JSON serialize için."""
        return {
            "symbol": self.symbol,
            "score": self.score,
            "calibrated_score": self.calibrated_score,
            "reason": self.reason,
            "source": self.source,
            "metadata": self.metadata,
            "calibration_multiplier": self.calibration_multiplier,
            "calibration_flags": list(self.calibration_flags),
        }


class BaseScanner(ABC):
    """4 mevcut scanner + ileride eklenecekler için ortak interface.

    Faz 2 migrasyon planı:
        ADIM 5: ThematicDiscoveryScanner
        ADIM 6: FairValuePanelScanner
        ADIM 7: NewsRadarScanner
        ADIM 8: AnalystRevisionsScanner (legacy adaptör)

    Kalibratör (Polymarket) bu sınıftan miras almaz — farklı imza
    (`calibrate()`), farklı rol. Sadece scanner paketinde duruyor.
    """

    name: ClassVar[str] = ""  # alt sınıf tanımlamalı

    @abstractmethod
    def scan(self) -> list[Candidate]:
        """Ticker adayları üret. Cron veya manuel tetikleme.

        Returns:
            Candidate listesi. Boş liste hata değil — sadece o turda sinyal yok.
            Hata durumunda exception fırlat (sessiz kalma).
        """
        ...

    def health_check(self) -> dict[str, Any]:
        """API kotaları, son başarılı çalışma, throttle durumu.

        Default: minimum sağlık raporu. Alt sınıflar override edebilir.
        """
        return {"name": self.name, "ok": True}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
