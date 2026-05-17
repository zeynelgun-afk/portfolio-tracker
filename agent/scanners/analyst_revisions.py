"""Analyst Revisions Scanner adaptörü.

Faz 2 — Adım 8 (17 May 2026).

Bu scanner DİĞERLERİNDEN FARKLI:
    - Adım 5-7 dosya TAŞIDI; bu dosya yeni bir ADAPTÖR
    - Kaynak (agent/legacy/analist_takip/monitor.py) YERİNDE KALIYOR
    - Mevcut Railway scheduler analist_takip_tick() çağırmaya devam ediyor
    - Bu scanner paralel bir kanal: kalibratör (Adım 9-10) tüketecek

Mevcut akış vs yeni akış:
    Eski (CLI/Railway, devam ediyor):
        telegram_bot → analist_takip_tick → _run_polling_cycle → DM
    Yeni (Scanner, henüz tüketici yok):
        kalibratör → AnalystRevisionsScanner.scan() → list[Candidate]

Yan etki disiplini:
    monitor.py'ın _run_polling_cycle'ı DM atar, state günceller. Scanner
    bu yan etkili katmanı atlatır ve doğrudan alt katmana iner:
        fetch_all_signals() + analyze_signals()
    Bunlar read-only (FMP çağrıları + saf hesaplama).

Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 5)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

# Score tablosu — Phase 10 tuning'inde ayarlanacak
# Sadece bullish decision'lar (STRONG_BUY/BUY/WATCH) Candidate üretir
# NEUTRAL/SELL/STRONG_SELL → Candidate yok (mevcut tez korumalı, ayrı kanal)
_DECISION_BASE_SCORE = {
    "STRONG_BUY": 0.95,
    "BUY":        0.70,
    "WATCH":      0.40,
}
_CONFIDENCE_MULTIPLIER = {
    "high":   1.0,
    "medium": 0.9,
    "low":    0.8,
}


def _build_candidate_from_decision(decision: dict):
    """Tek bir analyze_signals çıktısından Candidate üret veya None.

    Args:
        decision: analyze_signals() çıktısı — bir dict, "decision" + "confidence" +
                  diğer metadata alanları.

    Returns:
        Candidate veya None (NEUTRAL/SELL durumları, eksik veri).

    Pure function. Yan etki yok.
    """
    from agent.scanners.base import Candidate

    if not isinstance(decision, dict):
        return None

    ticker = decision.get("ticker")
    if not isinstance(ticker, str) or not ticker.strip():
        return None

    dec_type = (decision.get("decision") or "").strip().upper()
    base = _DECISION_BASE_SCORE.get(dec_type)
    if base is None:
        # NEUTRAL, SELL, STRONG_SELL → Candidate yok
        return None

    confidence = (decision.get("confidence") or "medium").strip().lower()
    multiplier = _CONFIDENCE_MULTIPLIER.get(confidence, _CONFIDENCE_MULTIPLIER["medium"])

    score = max(0.0, min(1.0, base * multiplier))

    rationale = decision.get("rationale") or ""
    raised = decision.get("raised_count_48h", 0)
    lowered = decision.get("lowered_count_48h", 0)
    avg_pct = decision.get("avg_revision_pct")
    avg_str = f"%{avg_pct:.1f}" if isinstance(avg_pct, (int, float)) else "—"

    reason = (
        f"Analist revize: {dec_type} ({confidence}). "
        f"48h: +{raised} raised / {lowered} lowered, ortalama {avg_str}. "
        f"{rationale}"
    )

    try:
        return Candidate(
            symbol=ticker,
            score=score,
            reason=reason.strip(),
            source="analyst_revisions",
            metadata={
                "decision": dec_type,
                "confidence": confidence,
                "raised_count_48h": raised,
                "lowered_count_48h": lowered,
                "raised_count_24h": decision.get("raised_count_24h", 0),
                "lowered_count_24h": decision.get("lowered_count_24h", 0),
                "avg_revision_pct": avg_pct,
                "biggest_raise": decision.get("biggest_raise"),
                "biggest_cut": decision.get("biggest_cut"),
                "drift_status": decision.get("drift_status"),
                "days_since_earnings": decision.get("days_since_earnings"),
                "gap_quality": decision.get("gap_quality"),
                "upside_avg_pct": decision.get("upside_avg_pct"),
                "risk_reward": decision.get("risk_reward"),
            },
        )
    except ValueError:
        # Boş ticker vs.
        return None


class AnalystRevisionsScanner:
    """BaseScanner adaptörü — Faz 2 Adım 8 (17 May 2026).

    Legacy alt-sistem (agent/legacy/analist_takip) üzerine paralel scanner.
    monitor.py'ın yan etkili _run_polling_cycle'ını ATLATIR ve doğrudan
    fetch_all_signals + analyze_signals çağırır.

    scan() pure: DM atmaz, state'i değiştirmez, watchlist'e yazmaz.
    """

    name = "analyst_revisions"

    def __init__(
        self,
        signal_window_hours: int = 48,
        universe: Optional[list[str]] = None,
        require_post_earnings: bool = True,
    ):
        if signal_window_hours <= 0:
            raise ValueError(
                f"signal_window_hours > 0 olmalı, alındı: {signal_window_hours}"
            )
        self.signal_window_hours = int(signal_window_hours)
        self.universe = universe
        self.require_post_earnings = require_post_earnings

    def _resolve_universe(self) -> list[str]:
        """Constructor universe varsa onu, yoksa analist_takip evreni."""
        if self.universe is not None:
            return list(self.universe)

        try:
            from agent.legacy.analist_takip.watchlist import build_watchlist
        except ImportError as e:
            print(f"[analyst_revisions scanner] watchlist import hatası: {e}")
            return []

        try:
            u = build_watchlist()
            if isinstance(u, dict):
                return list(u.keys())
            return list(u or [])
        except Exception as e:
            print(f"[analyst_revisions scanner] universe oluşturma hatası: {e}")
            return []

    def scan(self) -> list:
        """Universe tara → her ticker için analyze_signals → Candidate listesi.

        Yan etki yok:
            - mark_revision_seen() çağrılmaz (state korunur)
            - notify_signal() çağrılmaz (DM atılmaz)
            - cooldown kontrol yapılmaz (CLI tarafında)

        FMP veya legacy import hatası → boş liste (graceful degradation).
        """
        # Lazy imports — modül yüklenirken legacy bağımlılığı zorunlu olmasın
        try:
            from agent.legacy.analist_takip.revision_fetcher import (
                fetch_all_signals,
                get_last_actual_earnings_date,
                get_target_consensus,
                _fmp_get,
            )
            from agent.legacy.analist_takip.signal_analyzer import analyze_signals
        except ImportError as e:
            print(f"[analyst_revisions scanner] legacy import hatası: {e}")
            return []

        tickers = self._resolve_universe()
        if not tickers:
            return []

        now_utc = datetime.now(timezone.utc)
        since = now_utc - timedelta(hours=self.signal_window_hours)

        candidates: list = []
        for ticker in tickers:
            try:
                signals = fetch_all_signals(ticker, since)
                if not signals:
                    continue

                # Fiyat + target consensus (gate için)
                current_price = None
                target_consensus = None
                try:
                    q_data = _fmp_get("quote", symbol=ticker)
                    if isinstance(q_data, list) and q_data:
                        current_price = q_data[0].get("price")
                    target_consensus = get_target_consensus(ticker)
                except Exception:
                    pass

                last_earnings = get_last_actual_earnings_date(ticker)

                decision = analyze_signals(
                    ticker, signals,
                    now=now_utc,
                    last_earnings_date=last_earnings,
                    require_post_earnings=self.require_post_earnings,
                    current_price=current_price,
                    target_consensus=target_consensus,
                )

                cand = _build_candidate_from_decision(decision)
                if cand is not None:
                    candidates.append(cand)

            except Exception as e:
                # Tek ticker hatası tüm scan'i kırmamalı
                print(f"[analyst_revisions scanner] {ticker} hata: {e}")
                continue

        return candidates

    def health_check(self) -> dict:
        import os as _os
        return {
            "name": self.name,
            "ok": bool(_os.environ.get("FMP_API_KEY")),
            "signal_window_hours": self.signal_window_hours,
            "universe_size": len(self.universe) if self.universe is not None else None,
            "require_post_earnings": self.require_post_earnings,
        }
