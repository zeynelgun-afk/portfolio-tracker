#!/usr/bin/env python3
"""
Finzora — Ortak FMP İstemci
============================
Repo'da 15 yerde kopyalanmış `fmp_get` fonksiyonunu tek yere topladı.

KULLANIM:
    from agent.fmp_client import fmp_get

    quote = fmp_get("quote", {"symbol": "AAPL"})
    rsi   = fmp_get("technical-indicators/rsi", {"symbol": "AAPL", "periodLength": 14, "timeframe": "1day"})

ÖZELLİKLER:
- Otomatik retry (429, 500, 502, 503, 504 ve body'deki "Limit Reach" için)
- Rate limit beklemesi 60s'ten başlar, +30s artar (FMP dakikalık reset uyumlu)
- 402 yakalama (Premium dışı endpoint, retry yok)
- JSONDecodeError ayrı yakalanır (CDN HTML hata sayfası vakası, kalıcı hata)
- Body'de "Limit Reach" mesajı 429 ile aynı muamele görür
- Telegram'a kritik hata bildirimi (opsiyonel)
- Timeout default 15s

10 May 2026 GÜNCELLEMESİ — Bkz. docs/FMP_SKILL.md CHANGELOG.
"""

import time
import requests
from typing import Optional

from _config import FMP_KEY, FMP_BASE

# Observability (opsiyonel — eksikse sessizce geç)
try:
    from observability import log_fmp_call
except ImportError:
    log_fmp_call = lambda *a, **kw: None

_DEFAULT_TIMEOUT = 15
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0  # exponential base

# 10 May 2026 — burst koruması (30 Nis 11 ardışık 429 dalgası ampirik bulgusu)
# Min interval: ardışık fmp_get çağrıları arası saniye cinsinden minimum bekleme.
# 0.05s = 20 call/sn = 1200 call/dk. Ultimate limit 3000/dk altında, yine güvenli marj.
# fetch_all_data 11 endpoint × 0.05s = 0.55s ek bekleme per ticker, kabul edilebilir.
# Test ortamında 0 set edilebilir: import fmp_client; fmp_client._MIN_CALL_INTERVAL = 0
_MIN_CALL_INTERVAL = 0.05
_last_call_ts = 0.0


def _throttle():
    """Ardışık fmp_get çağrıları arası min interval enforcer."""
    global _last_call_ts
    if _MIN_CALL_INTERVAL <= 0:
        return
    now = time.monotonic()
    elapsed = now - _last_call_ts
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)
    _last_call_ts = time.monotonic()


def fmp_get(
    endpoint: str,
    params: Optional[dict] = None,
    timeout: int = _DEFAULT_TIMEOUT,
    max_retries: int = _MAX_RETRIES,
    notify_on_error: bool = False,
):
    """
    FMP stable API'ye GET isteği atar.

    Args:
        endpoint: "quote", "ratios-ttm" gibi. Başında / olmasın.
        params: Query parametreleri (apikey otomatik eklenir).
        timeout: Saniye cinsinden.
        max_retries: Geçici hatalar için yeniden deneme sayısı.
        notify_on_error: True ise kritik hatalar Telegram'a düşer.

    Returns:
        list | dict: JSON yanıt.
        None: Tüm denemeler başarısız olduğunda (beklenen dönüş tipleri
              kullanıcı koddan liste ise, `None` gelince bozulabilir;
              riski azaltmak için boş liste dönüyor).
    """
    if not FMP_KEY:
        print(f"[fmp_client] FMP_API_KEY tanımsız. endpoint={endpoint}")
        log_fmp_call(endpoint=endpoint, status=0, duration_ms=0, error="no_api_key")
        return []

    p = dict(params or {})
    p["apikey"] = FMP_KEY
    url = f"{FMP_BASE}/{endpoint}"

    last_err: Optional[str] = None
    last_status: int = 0
    response_size: Optional[int] = None
    t_total_start = time.time()

    for attempt in range(max_retries):
        try:
            _throttle()  # 10 May 2026: burst koruması
            r = requests.get(url, params=p, timeout=timeout)
            last_status = r.status_code

            # 402: Premium dışı endpoint — retry'ın anlamı yok
            if r.status_code == 402:
                print(f"[fmp_client] 402 Payment Required: {endpoint}")
                log_fmp_call(
                    endpoint=endpoint,
                    status=402,
                    duration_ms=int((time.time() - t_total_start) * 1000),
                    retry_count=attempt,
                    error="402_payment_required",
                )
                return []

            # 429: Rate limit — 60s'ten başla, sonra +30s artır (FMP dakikalık reset)
            if r.status_code == 429:
                wait = 60 + 30 * attempt  # 60s, 90s, 120s
                last_err = f"429_rate_limit (attempt {attempt + 1}/{max_retries})"
                print(f"[fmp_client] 429 rate limit, {wait}s bekliyor (deneme {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue

            r.raise_for_status()

            # JSON parse — FMP arada CDN HTML hata sayfası dönebilir
            try:
                data = r.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as e:
                last_err = f"JSON parse failed: {str(e)[:100]}"
                # JSON decode kalıcı hata — retry anlamsız
                break

            response_size = len(r.content) if r.content else 0

            # FMP bazen {"Error Message": "..."} döner — "Limit Reach" rate limit, kalanı kalıcı
            if isinstance(data, dict) and "Error Message" in data:
                err_msg = data["Error Message"]
                if "Limit Reach" in err_msg:
                    # Body'de rate limit — 429 ile aynı muamele
                    wait = 60 + 30 * attempt
                    last_err = f"body_limit_reach (attempt {attempt + 1}/{max_retries})"
                    print(f"[fmp_client] Body Limit Reach, {wait}s bekliyor (deneme {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
                # Diğer body error'ları kalıcı (Invalid API KEY, vs.)
                print(f"[fmp_client] FMP Error: {err_msg}")
                log_fmp_call(
                    endpoint=endpoint,
                    status=r.status_code,
                    duration_ms=int((time.time() - t_total_start) * 1000),
                    retry_count=attempt,
                    response_size=response_size,
                    error=err_msg[:200],
                )
                return []

            log_fmp_call(
                endpoint=endpoint,
                status=200,
                duration_ms=int((time.time() - t_total_start) * 1000),
                retry_count=attempt,
                response_size=response_size,
            )
            return data

        except requests.exceptions.Timeout:
            last_err = f"Timeout (attempt {attempt + 1})"
        except requests.exceptions.ConnectionError as e:
            last_err = f"ConnectionError: {str(e)[:100]}"
        except requests.exceptions.HTTPError as e:
            last_err = f"HTTPError {e.response.status_code}"
            last_status = e.response.status_code
            if e.response.status_code in (500, 502, 503, 504):
                # Geçici sunucu hatası, retry'a değer
                time.sleep(_RETRY_BACKOFF ** (attempt + 1))
                continue
            # Diğer HTTP hataları için tekrar deneme
            break
        except Exception as e:
            last_err = f"Unexpected: {type(e).__name__}: {str(e)[:100]}"
            # Beklenmeyen hata — retry edilebilir ama kontrollü
            if attempt >= max_retries - 1:
                break

        # Geçici hatalar için backoff (ConnectionError, Timeout)
        if attempt < max_retries - 1:
            time.sleep(_RETRY_BACKOFF ** (attempt + 1))

    print(f"[fmp_client] Başarısız ({endpoint}): {last_err}")

    log_fmp_call(
        endpoint=endpoint,
        status=last_status,
        duration_ms=int((time.time() - t_total_start) * 1000),
        retry_count=max_retries,
        error=last_err,
    )

    if notify_on_error:
        _notify_telegram(endpoint, last_err or "Bilinmeyen hata")

    return []


def _notify_telegram(endpoint: str, err: str) -> None:
    """Kritik FMP hatasını Telegram'a bildir (opsiyonel)."""
    try:
        from _config import TELEGRAM_TOKEN, TELEGRAM_PRIVATE_CHAT
        if not TELEGRAM_TOKEN or not TELEGRAM_PRIVATE_CHAT:
            return
        msg = f"⚠️ FMP hatası: {endpoint}\n{err[:200]}"
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_PRIVATE_CHAT, "text": msg},
            timeout=10,
        )
    except Exception:
        pass  # Bildirim hatası sistemi durdurmasın


# ── Sık kullanılan kolay sarmalayıcılar ───────────────────────────────────────

def quote(symbol: str) -> Optional[dict]:
    """Tek sembol için quote döner."""
    res = fmp_get("quote", {"symbol": symbol})
    if isinstance(res, list) and res:
        return res[0]
    return None


def batch_quote(symbols: list[str]) -> dict[str, dict]:
    """Çoklu sembol → {symbol: quote_dict}."""
    if not symbols:
        return {}
    res = fmp_get("batch-quote", {"symbols": ",".join(symbols)})
    if not isinstance(res, list):
        return {}
    return {q["symbol"]: q for q in res if "symbol" in q}


def rsi(symbol: str, period: int = 14, timeframe: str = "1day") -> Optional[float]:
    """Tek sembol için son RSI değeri."""
    res = fmp_get(
        "technical-indicators/rsi",
        {"symbol": symbol, "periodLength": period, "timeframe": timeframe},
    )
    if isinstance(res, list) and res:
        return res[0].get("rsi")
    return None


def historical_eod(symbol: str, from_date: str, to_date: Optional[str] = None) -> list:
    """Günlük OHLCV döner."""
    params = {"symbol": symbol, "from": from_date}
    if to_date:
        params["to"] = to_date
    res = fmp_get("historical-price-eod/full", params)
    if isinstance(res, list):
        return res
    return []
