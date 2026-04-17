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
- Otomatik retry (429, 500, 503 için exponential backoff)
- 402 yakalama (Premium dışı endpoint)
- Telegram'a kritik hata bildirimi (opsiyonel)
- Timeout default 15s
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

            # 429: Rate limit — backoff ile bekle
            if r.status_code == 429:
                wait = _RETRY_BACKOFF ** (attempt + 1)
                print(f"[fmp_client] 429 rate limit, {wait:.1f}s bekliyor...")
                time.sleep(wait)
                continue

            r.raise_for_status()
            data = r.json()
            response_size = len(r.content) if r.content else 0

            # FMP bazen {"Error Message": "..."} döner
            if isinstance(data, dict) and "Error Message" in data:
                print(f"[fmp_client] FMP Error: {data['Error Message']}")
                log_fmp_call(
                    endpoint=endpoint,
                    status=r.status_code,
                    duration_ms=int((time.time() - t_total_start) * 1000),
                    retry_count=attempt,
                    response_size=response_size,
                    error=data["Error Message"][:200],
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

        # Backoff
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
