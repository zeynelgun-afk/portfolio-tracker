"""Polymarket Calibrator — Faz 2 Adım 9 (17 May 2026).

Scanner DEĞIL, post-processor. BaseScanner'dan miras almaz.

Görev:
    Pozisyon #2 (gate sonrası kalibrasyon):
        scanner.scan() → AI Gate → calibrator.calibrate(candidates) → watchlist

    Pozisyon #3 (watchlist sağlık taraması):
        günlük cron → watchlist'teki ticker'lar için yeni çelişki kontrolü → DM

Tasarım:
    docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 2, 8)

Çarpan tablosu (Bölüm 8):
    side='positive', delta > +%10  → 1.20 (pm_confirm)
    side='positive', delta +%3-+%10 → 1.10 (pm_confirm_weak)
    side='positive', |delta| < %3  → no-op
    side='positive', delta -%3--%10 → 0.90 (pm_conflict_weak)
    side='positive', delta < -%10  → 0.75 (pm_conflict)
    side='negative': aynı tablo, delta -1 ile çarpılır (effective delta)

Veto YOK. Çarpan aralığı 0.75-1.20 (Candidate.apply_calibration enforce eder).
Çoklu eşleşme: en aşırı kazanır + downside protection (Candidate.apply_calibration).

Performance tracker (Phase 10 ön şartı):
    Her kalibrasyon bayrağı → data/polymarket_calibrator_performance.json
    7/14/30g sonra outcome geri-doldurma signal_tracker paralelinde.
    İlk 30 gün tuning kilidi: çarpan tablosu hardcoded.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ── Çarpan tablosu — Phase 10'a kadar HARDCODED ────────────────────────────────

# Effective delta eşikleri (pp = percentage point, ondalık olarak)
# Tasarım Bölüm 8 — değiştirme: Phase 10 + 30g veri sonrası
_STRONG_THRESHOLD = 0.10
_WEAK_THRESHOLD = 0.03

_MULTIPLIER_FLAG_TABLE = {
    "strong_confirm":  (1.20, "pm_confirm"),
    "weak_confirm":    (1.10, "pm_confirm_weak"),
    "neutral":         (None, None),  # no-op
    "weak_conflict":   (0.90, "pm_conflict_weak"),
    "strong_conflict": (0.75, "pm_conflict"),
}


def _classify_delta(delta: float, side: str) -> str:
    """Delta + side → bayrak kategori adı.

    Args:
        delta: market'in 24h Yes-prob delta'sı (örn. +0.07 = +7pp)
        side: 'positive' (market yükselişi olumlu, candidate AL teyit eder)
              veya 'negative' (market yükselişi olumsuz)

    Returns:
        Kategori string'i: strong_confirm | weak_confirm | neutral |
        weak_conflict | strong_conflict
    """
    if side not in ("positive", "negative"):
        raise ValueError(f"side 'positive' veya 'negative' olmalı, alındı: {side!r}")

    # Negative side için delta'yı ters çevir → tek tablo
    eff = delta if side == "positive" else -delta

    if eff >= _STRONG_THRESHOLD:
        return "strong_confirm"
    if eff >= _WEAK_THRESHOLD:
        return "weak_confirm"
    if eff > -_WEAK_THRESHOLD:
        return "neutral"
    if eff > -_STRONG_THRESHOLD:
        return "weak_conflict"
    return "strong_conflict"


def _delta_to_multiplier_flag(
    delta: float, side: str
) -> tuple[Optional[float], Optional[str]]:
    """Delta + side → (multiplier, flag). Neutral durumda (None, None).

    Hata fırlatmaz — _classify_delta ValueError fırlatır eğer side hatalı.
    """
    category = _classify_delta(delta, side)
    return _MULTIPLIER_FLAG_TABLE[category]


# ── Theme matching ─────────────────────────────────────────────────────────────


def _find_theme_matches(
    symbol: str, themes_config: dict
) -> list[tuple[str, str, dict]]:
    """Ticker → (theme_id, side, theme_dict) eşleşmeleri.

    Args:
        symbol: Candidate.symbol (uppercase olarak gelir)
        themes_config: load_themes() çıktısı, "themes" altında dict

    Returns:
        Liste tuple'lar. Bir ticker birden fazla temada olabilir (örn. TSM hem
        china_taiwan_tension hem trump_tariff_action).
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return []

    themes = themes_config.get("themes", {}) if isinstance(themes_config, dict) else {}

    matches: list[tuple[str, str, dict]] = []
    for theme_id, cfg in themes.items():
        if not isinstance(cfg, dict):
            continue
        positives = [t.strip().upper() for t in cfg.get("positive_tickers", []) if isinstance(t, str)]
        negatives = [t.strip().upper() for t in cfg.get("negative_tickers", []) if isinstance(t, str)]

        if sym in positives:
            matches.append((theme_id, "positive", cfg))
        elif sym in negatives:
            matches.append((theme_id, "negative", cfg))
        # Hem positive hem negative listede olursa → positive kazanır (yukarıdaki elif)
    return matches


# ── PolymarketCalibrator class ─────────────────────────────────────────────────


class PolymarketCalibrator:
    """Diğer scanner'ların çıktısını Polymarket cache'iyle kalibre eder.

    Lifecycle:
        kalibratör = PolymarketCalibrator()
        kalibrated = kalibratör.calibrate(candidates)
        # candidates listesi yerinde mutate edilir, ayrıca döndürülür
    """

    def __init__(
        self,
        themes_loader=None,
        cache_loader=None,
        performance_log_path: Optional[Path] = None,
    ):
        """
        Args:
            themes_loader: () → dict. None ise polymarket.load_themes kullanılır.
            cache_loader: () → dict. None ise polymarket.load_cache kullanılır.
            performance_log_path: Tracker JSON yolu. None ise default
                data/polymarket_calibrator_performance.json
        """
        # Lazy import — test'ler bu fonksiyonları mock'layabilsin
        from agent import polymarket as _pm

        self._themes_loader = themes_loader or _pm.load_themes
        self._cache_loader = cache_loader or _pm.load_cache

        if performance_log_path is None:
            repo_root = Path(__file__).resolve().parents[2]
            performance_log_path = (
                repo_root / "data" / "polymarket_calibrator_performance.json"
            )
        self.performance_log_path = Path(performance_log_path)

    # ── Ana kalibrasyon ────────────────────────────────────────────────────────

    def calibrate(self, candidates: list) -> list:
        """Candidate listesini kalibre et.

        Her Candidate için:
            1. Whitelist temalarında ticker eşleşmesi ara
            2. Eşleşen temanın market'leri için Polymarket cache'inde delta bak
            3. Likidite + delta → çarpan/bayrak
            4. Candidate.apply_calibration() çağır (çoklu eşleşme orada yönetilir)
            5. Performance tracker'a event yaz

        Args:
            candidates: list[Candidate] — yerinde mutate edilir

        Returns:
            Aynı liste, kalibrasyon uygulanmış olarak. Boş liste hata değil.
        """
        if not candidates:
            return candidates

        try:
            themes = self._themes_loader() or {}
            cache = self._cache_loader() or {}
        except Exception as e:
            print(f"[calibrator] data yükleme hatası: {e}")
            return candidates

        markets = cache.get("markets", {}) if isinstance(cache, dict) else {}

        events_to_record: list[dict] = []

        for cand in candidates:
            try:
                applied = self._apply_to_candidate(cand, themes, markets)
                events_to_record.extend(applied)
            except Exception as e:
                # Tek candidate hatası tüm kalibrasyonu kırmamalı
                print(f"[calibrator] {getattr(cand, 'symbol', '?')} hata: {e}")
                continue

        # Tracker yazımı (graceful — hata varsa silent skip)
        if events_to_record:
            try:
                self._append_events(events_to_record)
            except Exception as e:
                print(f"[calibrator] tracker yazım hatası: {e}")

        return candidates

    def _apply_to_candidate(
        self, cand, themes: dict, markets: dict
    ) -> list[dict]:
        """Tek candidate için kalibrasyon uygula. Mutasyonu yapan iç metod.

        Returns:
            Bu candidate için kayıt edilecek event listesi (boş olabilir).
        """
        matches = _find_theme_matches(cand.symbol, themes)
        if not matches:
            return []

        events: list[dict] = []
        original_score = cand.score

        for theme_id, side, theme_cfg in matches:
            min_volume = float(theme_cfg.get("min_volume_usd", 0))
            slugs = theme_cfg.get("polymarket_slugs", []) or []

            for slug in slugs:
                if not isinstance(slug, str) or not slug:
                    continue

                market = markets.get(slug)
                if not isinstance(market, dict):
                    continue

                # Likidite filtresi (manipulation guard)
                volume = market.get("volume", market.get("volumeNum", 0))
                try:
                    if float(volume or 0) < min_volume:
                        continue
                except (TypeError, ValueError):
                    continue

                delta = market.get("delta_24h")
                if delta is None:
                    continue
                try:
                    delta_f = float(delta)
                except (TypeError, ValueError):
                    continue

                mult, flag = _delta_to_multiplier_flag(delta_f, side)
                if mult is None or flag is None:
                    continue  # neutral zone, no-op

                # Candidate'a uygula — çoklu eşleşme yönetimi Candidate'da
                cand.apply_calibration(mult, [flag])

                events.append({
                    "id": _new_event_id(),
                    "ts": _now_iso(),
                    "candidate_symbol": cand.symbol,
                    "candidate_source": cand.source,
                    "candidate_original_score": original_score,
                    "applied_flag": flag,
                    "applied_multiplier": mult,
                    "matched_theme": theme_id,
                    "matched_side": side,
                    "market_slug": slug,
                    "market_delta_24h": delta_f,
                    "outcome_7d": None,
                    "outcome_14d": None,
                    "outcome_30d": None,
                })

        return events

    # ── Pozisyon #3: Watchlist sağlık taraması ────────────────────────────────

    def watchlist_health_check(
        self, watchlist_symbols: list[str]
    ) -> list[dict]:
        """Watchlist'teki ticker'lar için Polymarket çelişki kontrolü.

        Her ticker için tema eşleşmesi bul, market delta'sını kontrol et.
        Sadece çelişki (`pm_conflict` veya `pm_conflict_weak`) durumlarında
        alert üretir — DM uyarısı için kullanılır.

        Args:
            watchlist_symbols: data/watchlist.json'dan toplanan ticker'lar

        Returns:
            list[dict]: alertler. Her biri:
                {symbol, theme_id, market_slug, delta_24h, flag, severity}
        """
        if not watchlist_symbols:
            return []

        try:
            themes = self._themes_loader() or {}
            cache = self._cache_loader() or {}
        except Exception as e:
            print(f"[calibrator/health] data yükleme hatası: {e}")
            return []

        markets = cache.get("markets", {}) if isinstance(cache, dict) else {}
        alerts: list[dict] = []

        for symbol in watchlist_symbols:
            if not isinstance(symbol, str) or not symbol.strip():
                continue
            sym = symbol.strip().upper()

            matches = _find_theme_matches(sym, themes)
            for theme_id, side, theme_cfg in matches:
                min_volume = float(theme_cfg.get("min_volume_usd", 0))
                for slug in theme_cfg.get("polymarket_slugs", []) or []:
                    market = markets.get(slug)
                    if not isinstance(market, dict):
                        continue

                    volume = market.get("volume", market.get("volumeNum", 0))
                    try:
                        if float(volume or 0) < min_volume:
                            continue
                    except (TypeError, ValueError):
                        continue

                    delta = market.get("delta_24h")
                    if delta is None:
                        continue
                    try:
                        delta_f = float(delta)
                    except (TypeError, ValueError):
                        continue

                    mult, flag = _delta_to_multiplier_flag(delta_f, side)
                    if flag not in ("pm_conflict", "pm_conflict_weak"):
                        continue  # sadece çelişki alert üretir

                    alerts.append({
                        "symbol": sym,
                        "theme_id": theme_id,
                        "theme_label": theme_cfg.get("label", theme_id),
                        "matched_side": side,
                        "market_slug": slug,
                        "delta_24h": delta_f,
                        "flag": flag,
                        "severity": "strong" if flag == "pm_conflict" else "weak",
                    })

        return alerts

    # ── Performance tracker ───────────────────────────────────────────────────

    def initialize_tracker(self) -> None:
        """Tracker JSON yoksa boş şema ile oluştur. Idempotent."""
        if self.performance_log_path.exists():
            return
        self.performance_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "_version": "v1",
            "_started_at": _now_iso(),
            "_note": (
                "Faz 2 Adım 9 (17 May 2026). 30g sonra çarpan tuning'i için "
                "yeterli veri biriksin diye Phase 10'da bu dosya tüketilecek."
            ),
            "events": [],
            "stats": {
                "total_events": 0,
                "confirms": 0,
                "conflicts": 0,
                "confirm_hit_rate_7d": None,
                "conflict_hit_rate_7d": None,
            },
        }
        with self.performance_log_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _append_events(self, events: list[dict]) -> None:
        """Performance log'a event'leri ekle. Stats güncelle."""
        if not events:
            return

        self.initialize_tracker()

        with self.performance_log_path.open(encoding="utf-8") as f:
            log = json.load(f)

        log.setdefault("events", []).extend(events)
        stats = log.setdefault("stats", {})
        stats["total_events"] = len(log["events"])
        stats["confirms"] = sum(
            1 for e in log["events"]
            if e.get("applied_flag", "").startswith("pm_confirm")
        )
        stats["conflicts"] = sum(
            1 for e in log["events"]
            if e.get("applied_flag", "").startswith("pm_conflict")
        )

        with self.performance_log_path.open("w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

    def load_performance_log(self) -> dict:
        """Mevcut tracker dosyasını oku. Yoksa initialize edip oku."""
        self.initialize_tracker()
        with self.performance_log_path.open(encoding="utf-8") as f:
            return json.load(f)


# ── Helper'lar ─────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_event_id() -> str:
    """16-hex char unique ID — saatlik kalibrasyon ölçeğinde yeterli."""
    return secrets.token_hex(6)  # 12 hex chars
