"""Polymarket Gamma API client.

Self-contained wrapper around https://gamma-api.polymarket.com.
agent/fmp.py pattern'ine paralel: throttle, retry, observability hook.

Public API (read-only, auth gerekmez):
    fetch_markets(slugs=None, active_only=True) -> list[dict]
    fetch_market_by_slug(slug: str) -> Optional[dict]
    compute_delta(market, lookback_hours=24) -> Optional[float]
    is_liquid(market, min_volume_usd=100000) -> bool

Cache wrapper (1h TTL):
    load_cache() -> dict
    save_cache(payload: dict) -> None
    cache_is_fresh(cache: dict, max_age_hours=1) -> bool

Tasarım dokümanı: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 6)
Faz 2 ile başladı (17 May 2026).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# ---------- Configuration ----------

BASE_URL = "https://gamma-api.polymarket.com"
USER_AGENT = "Finzora AI Research zeynelgun@finzora.example.com"

_DEFAULT_TIMEOUT = 15
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0
_MIN_CALL_INTERVAL = 0.10  # 100 ms — konservatif, public API rate limit belirsiz
_last_call_ts: float = 0.0

# Repo köküne göre cache yolu — agent/polymarket.py konumundan parent.parent
_REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = _REPO_ROOT / "data" / "polymarket_cache.json"
THEMES_PATH = _REPO_ROOT / "data" / "polymarket_themes.json"


# ---------- Observability hook (opsiyonel) ----------

def _log_call(
    endpoint: str,
    status: int,
    duration_ms: int,
    response_size: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Olay logla — observability modülü yoksa sessizce geç.

    log_event'i lazy import — modül legacy'de, test ortamlarında olmayabilir.
    """
    try:
        # Lazy import — observability legacy'de ve PYTHONPATH'e bağlı
        from observability import log_event  # type: ignore
    except ImportError:
        return

    try:
        log_event(
            "polymarket_call",
            {
                "endpoint": endpoint,
                "status": status,
                "duration_ms": duration_ms,
                "response_size": response_size,
                "success": 1 if 200 <= status < 300 else 0,
                "error": error,
            },
        )
    except Exception as e:
        # Observability hatası asla ana akışı kırmasın
        print(f"[polymarket] log uyarısı: {e}")


# ---------- Throttle ----------

def _throttle() -> None:
    """Çağrılar arası minimum aralık (100ms)."""
    global _last_call_ts
    if _MIN_CALL_INTERVAL <= 0:
        return
    now = time.monotonic()
    elapsed = now - _last_call_ts
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)
    _last_call_ts = time.monotonic()


# ---------- Core GET ----------

def _gamma_get(
    endpoint: str,
    params: Optional[dict] = None,
    timeout: int = _DEFAULT_TIMEOUT,
    max_retries: int = _MAX_RETRIES,
) -> Any:
    """GET request to Gamma API.

    Returns parsed JSON. Hata durumunda boş liste/dict döner (FMP pattern).
    Auth header yok — Gamma API public read-only.
    """
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    last_err: Optional[str] = None
    last_status: int = 0

    for attempt in range(max_retries + 1):
        _throttle()
        t_start = time.monotonic()
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            last_err = f"network: {e}"
            last_status = 0
            if attempt < max_retries:
                time.sleep(_RETRY_BACKOFF ** attempt)
                continue
            break

        last_status = r.status_code
        duration_ms = int((time.monotonic() - t_start) * 1000)

        # 429 / 5xx → retry
        if r.status_code == 429 or r.status_code >= 500:
            last_err = f"status={r.status_code}"
            if attempt < max_retries:
                wait = 5 * (attempt + 1)  # 5s, 10s, 15s — public API, daha agresif değil
                time.sleep(wait)
                continue
            _log_call(endpoint, r.status_code, duration_ms, error=last_err)
            break

        if not r.ok:
            last_err = f"status={r.status_code}, body={(r.text or '')[:80]!r}"
            _log_call(endpoint, r.status_code, duration_ms, error=last_err)
            break

        # Başarılı — parse et
        try:
            payload = r.json()
            _log_call(
                endpoint,
                r.status_code,
                duration_ms,
                response_size=len(r.content) if r.content else 0,
            )
            return payload
        except json.JSONDecodeError as e:
            last_err = f"json_decode: {e}"
            _log_call(endpoint, r.status_code, duration_ms, error=last_err)
            break

    print(f"[polymarket] gamma_get failed endpoint={endpoint} err={last_err}")
    return [] if endpoint.endswith("markets") else {}


# ---------- Public API ----------

def fetch_markets(
    slugs: Optional[list[str]] = None,
    active_only: bool = True,
    limit: int = 100,
) -> list[dict]:
    """Polymarket'ten market listesi çek.

    Args:
        slugs: Eğer verilirse sadece bu slug'lara filtrelenir (whitelist).
        active_only: closed=false & archived=false marketler.
        limit: Sayfa başı limit (Gamma default 100).

    Returns:
        Liste dict'ler. Her dict en az: id, slug, question, outcomes, outcomePrices,
        volume, liquidity, endDate, active, closed alanlarını içerir (Gamma şema).

    NOTE: Gerçek Gamma şeması integration testte doğrulanır. Bu istemci
    'active' / 'closed' bayrakları üzerinden filtre yapar; alan isimleri
    değişirse adapter buradan güncellenir.
    """
    params: dict[str, Any] = {"limit": limit}
    if active_only:
        params["active"] = "true"
        params["closed"] = "false"

    result = _gamma_get("markets", params)
    if not isinstance(result, list):
        return []

    if slugs is None:
        return result

    slug_set = set(slugs)
    return [m for m in result if isinstance(m, dict) and m.get("slug") in slug_set]


def fetch_market_by_slug(slug: str) -> Optional[dict]:
    """Tek bir market detayı, slug ile."""
    if not slug:
        return None
    result = _gamma_get("markets", {"slug": slug, "limit": 1})
    if isinstance(result, list) and result:
        return result[0]
    return None


# ---------- Likidite ve delta hesabı ----------

def is_liquid(market: dict, min_volume_usd: float = 100_000) -> bool:
    """Likidite filtresi — manipulation guard.

    `volume` alanı USD cinsinden total volume (Gamma şema).
    """
    if not isinstance(market, dict):
        return False
    vol = market.get("volume") or market.get("volumeNum") or 0
    try:
        return float(vol) >= float(min_volume_usd)
    except (TypeError, ValueError):
        return False


def get_yes_probability(market: dict) -> Optional[float]:
    """Binary market için 'Yes' outcome'ının olasılığını döndür (0.0 — 1.0).

    Gamma şeması: outcomes ve outcomePrices paralel array'ler.
    Non-binary marketler için None döner.
    """
    if not isinstance(market, dict):
        return None

    outcomes = market.get("outcomes")
    prices = market.get("outcomePrices")

    # Gamma bazen string olarak JSON döndürür — defansif parse
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except json.JSONDecodeError:
            return None
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            return None

    if not isinstance(outcomes, list) or not isinstance(prices, list):
        return None
    if len(outcomes) != 2 or len(prices) != 2:
        return None  # binary değil

    try:
        idx_yes = next(
            i for i, o in enumerate(outcomes)
            if isinstance(o, str) and o.strip().lower() == "yes"
        )
    except StopIteration:
        return None

    try:
        return float(prices[idx_yes])
    except (TypeError, ValueError):
        return None


def compute_delta(
    market: dict,
    previous_probability: Optional[float],
) -> Optional[float]:
    """Mevcut Yes olasılığı ile önceki snapshot arasındaki delta.

    Cache mantığı: cache 24h öncesinin snapshot'ını tutar; bu fonksiyon
    iki noktayı karşılaştırır. Eğer önceki snapshot yoksa None.

    Returns:
        Delta yüzde puan olarak (-1.0 — +1.0). Örn. +0.07 = +7pp.
    """
    current = get_yes_probability(market)
    if current is None or previous_probability is None:
        return None
    return current - previous_probability


# ---------- Cache I/O ----------

def load_cache() -> dict:
    """polymarket_cache.json'u oku. Yoksa veya bozuksa boş şema döner."""
    if not CACHE_PATH.exists():
        return _empty_cache()
    try:
        with CACHE_PATH.open(encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return _empty_cache()
        return payload
    except (json.JSONDecodeError, OSError) as e:
        print(f"[polymarket] cache okuma hatası: {e}")
        return _empty_cache()


def save_cache(payload: dict) -> None:
    """polymarket_cache.json'a yaz. _fetched_at otomatik güncellenir."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["_fetched_at"] = datetime.now(timezone.utc).isoformat()
    payload.setdefault("_ttl_seconds", 3600)
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def cache_is_fresh(cache: dict, max_age_hours: float = 1.0) -> bool:
    """Cache TTL kontrolü. Eksik/bozuk timestamp → stale (False)."""
    ts = cache.get("_fetched_at")
    if not isinstance(ts, str):
        return False
    try:
        fetched = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    age_s = (datetime.now(timezone.utc) - fetched).total_seconds()
    return age_s < max_age_hours * 3600


def _empty_cache() -> dict:
    return {
        "_fetched_at": None,
        "_ttl_seconds": 3600,
        "markets": {},
    }


# ---------- Snapshot rotation + delta hesabı (Adım 10a) ----------

# Snapshot retention: sliding window 48h
# Cache her saatte refresh ediliyor → ~48 snapshot/market tutulur
_SNAPSHOT_WINDOW_HOURS = 48
_DELTA_TARGET_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str) -> Optional[datetime]:
    """Tolerant ISO parse — "Z" suffix kabul, bozuksa None."""
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def add_snapshot(
    cache: dict,
    slug: str,
    probability: float,
    market_data: Optional[dict] = None,
    now: Optional[datetime] = None,
    window_hours: int = _SNAPSHOT_WINDOW_HOURS,
) -> dict:
    """Cache'e yeni bir snapshot ekle. 48h+ eski snapshot'ları temizler.

    Args:
        cache: load_cache() çıktısı (yerinde mutate edilir).
        slug: market slug
        probability: mevcut Yes olasılığı (0.0-1.0)
        market_data: opsiyonel market detayları (volume, question, vs).
            Mevcut alanları korurken yenilerini günceller.
        now: test için tarih injection; None → datetime.now(UTC)
        window_hours: retention süresi (default 48)

    Returns:
        Mutate edilmiş cache (zincirlemek için).
    """
    if now is None:
        now = _utc_now()
    if not isinstance(cache, dict):
        cache = _empty_cache()

    markets = cache.setdefault("markets", {})
    entry = markets.setdefault(slug, {"slug": slug})

    # Market metadata güncelle (volume, question, vs)
    if isinstance(market_data, dict):
        for k, v in market_data.items():
            if k == "snapshots":
                continue  # snapshot'ları explicit yönetiyoruz
            entry[k] = v

    # Snapshot'ları al — varsa veya boş liste başlat
    snapshots = entry.setdefault("snapshots", [])
    if not isinstance(snapshots, list):
        snapshots = []
        entry["snapshots"] = snapshots

    # Yeni snapshot
    new_snap = {"ts": now.isoformat(), "probability": float(probability)}
    snapshots.append(new_snap)

    # 48h+ eski snapshot'ları temizle (sliding window)
    cutoff = now - timedelta(hours=window_hours)
    snapshots[:] = [
        s for s in snapshots
        if (parsed := _parse_iso(s.get("ts", "")))
        and parsed >= cutoff
    ]

    # Sort by ts (defansif — out-of-order yazımları normalize)
    snapshots.sort(key=lambda s: s.get("ts", ""))

    # current_probability ve delta_24h hesapla, üst seviyeye yaz
    entry["current_probability"] = float(probability)
    delta_info = compute_24h_delta_from_snapshots(snapshots, now=now)
    if delta_info is not None:
        entry["probability_24h_ago"] = delta_info["probability_24h_ago"]
        entry["delta_24h"] = delta_info["delta_24h"]
    else:
        # 24h önceki snapshot yok — alanları temizle (kalibratör no-op yapar)
        entry.pop("probability_24h_ago", None)
        entry.pop("delta_24h", None)

    return cache


def compute_24h_delta_from_snapshots(
    snapshots: list,
    now: Optional[datetime] = None,
    target_hours: int = _DELTA_TARGET_HOURS,
    tolerance_hours: float = 2.0,
) -> Optional[dict]:
    """Snapshot listesinden ~24h önceki en yakın snapshot'ı bulup delta hesapla.

    Args:
        snapshots: list[{ts, probability}]
        now: test için tarih injection
        target_hours: hedef geçmiş süre (default 24h)
        tolerance_hours: target ± tolerans (default 2h). 22-26h arası snapshot kabul.

    Returns:
        {"probability_24h_ago": float, "delta_24h": float,
         "matched_ts": str, "matched_hours_ago": float}
        veya None (uygun snapshot yok).
    """
    if not isinstance(snapshots, list) or len(snapshots) < 2:
        return None
    if now is None:
        now = _utc_now()

    # En yeni snapshot (current)
    parsed_snaps: list[tuple[datetime, float]] = []
    for s in snapshots:
        if not isinstance(s, dict):
            continue
        ts = _parse_iso(s.get("ts", ""))
        prob = s.get("probability")
        if ts is None or prob is None:
            continue
        try:
            parsed_snaps.append((ts, float(prob)))
        except (TypeError, ValueError):
            continue

    if len(parsed_snaps) < 2:
        return None

    parsed_snaps.sort(key=lambda x: x[0])
    current_ts, current_prob = parsed_snaps[-1]

    # 24h önceki hedef
    target_ts = now - timedelta(hours=target_hours)
    tolerance = timedelta(hours=tolerance_hours)
    earliest_acceptable = target_ts - tolerance
    latest_acceptable = target_ts + tolerance

    # Tolerans penceresindeki en yakın snapshot
    candidates = [
        (ts, p) for ts, p in parsed_snaps[:-1]  # current hariç
        if earliest_acceptable <= ts <= latest_acceptable
    ]

    if not candidates:
        return None

    # En target'a yakın olanı seç
    best_ts, best_prob = min(candidates, key=lambda x: abs((x[0] - target_ts).total_seconds()))

    hours_ago = (current_ts - best_ts).total_seconds() / 3600
    return {
        "probability_24h_ago": best_prob,
        "delta_24h": current_prob - best_prob,
        "matched_ts": best_ts.isoformat(),
        "matched_hours_ago": round(hours_ago, 2),
    }


def refresh_cache_for_themes(
    themes_config: Optional[dict] = None,
    cache: Optional[dict] = None,
    now: Optional[datetime] = None,
    save: bool = True,
) -> dict:
    """Whitelist'teki tüm tema slug'ları için Gamma'dan fetch + snapshot kaydet.

    Bu fonksiyon:
        1. Whitelist tema slug'larını topla (themes_config veya load_themes)
        2. Gamma API'den fetch_markets(slugs=...) ile mevcut olasılıkları çek
        3. Her market için snapshot ekle (add_snapshot)
        4. Cache'i save_cache ile dosyaya yaz (save=True)

    Args:
        themes_config: opsiyonel themes dict. None → load_themes()
        cache: opsiyonel mevcut cache. None → load_cache()
        now: test injection
        save: True ise disk'e yaz; False ise sadece in-memory mutate (test için)

    Returns:
        Güncellenmiş cache dict.
    """
    if themes_config is None:
        themes_config = load_themes()
    if cache is None:
        cache = load_cache()
    if now is None:
        now = _utc_now()

    # Whitelist slug'ları topla
    slugs: set[str] = set()
    for theme in (themes_config.get("themes", {}) if isinstance(themes_config, dict) else {}).values():
        if not isinstance(theme, dict):
            continue
        for slug in theme.get("polymarket_slugs", []):
            if isinstance(slug, str) and slug.strip():
                slugs.add(slug.strip())

    if not slugs:
        if save:
            save_cache(cache)
        return cache

    # Gamma'dan fetch (whitelist filtre)
    markets = fetch_markets(slugs=list(slugs), active_only=True)

    for m in markets:
        if not isinstance(m, dict):
            continue
        slug = m.get("slug")
        if not slug:
            continue

        prob = get_yes_probability(m)
        if prob is None:
            continue  # binary olmayan veya bozuk market — atla

        # Snapshot için tutulacak metadata
        market_data = {
            "id": m.get("id"),
            "slug": slug,
            "question": m.get("question"),
            "volume": m.get("volume") or m.get("volumeNum"),
            "endDate": m.get("endDate"),
            "active": m.get("active"),
            "closed": m.get("closed"),
        }
        add_snapshot(cache, slug, prob, market_data=market_data, now=now)

    cache["_fetched_at"] = now.isoformat()
    cache.setdefault("_ttl_seconds", 3600)

    if save:
        save_cache(cache)
    return cache


# ---------- Themes whitelist I/O ----------

def load_themes() -> dict:
    """polymarket_themes.json'u oku. Insan-onaylı whitelist."""
    if not THEMES_PATH.exists():
        return {"themes": {}}
    try:
        with THEMES_PATH.open(encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return {"themes": {}}
        return payload
    except (json.JSONDecodeError, OSError) as e:
        print(f"[polymarket] themes okuma hatası: {e}")
        return {"themes": {}}


def get_theme_slugs() -> set[str]:
    """Tüm whitelist temalardaki tüm market slug'larını topla."""
    themes = load_themes().get("themes", {})
    slugs: set[str] = set()
    for theme in themes.values():
        if not isinstance(theme, dict):
            continue
        for slug in theme.get("polymarket_slugs", []):
            if isinstance(slug, str) and slug.strip():
                slugs.add(slug.strip())
    return slugs
