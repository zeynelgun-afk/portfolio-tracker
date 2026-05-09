"""
agent/fmp_client.py için kapsamlı test suite.

10 Mayıs 2026 audit Aksiyon 4 — pytest + responses (HTTP mock) ile çalışır.

ÇALIŞTIRMA:
    cd repo_root && python -m pytest tests/test_fmp_client.py -v
    veya: pytest tests/test_fmp_client.py::TestRateLimit -v

KAPSAM:
    - Normal başarı durumu (200 + valid JSON)
    - Boş [] yanıt retry'a girmemeli
    - 404/4xx kalıcı hata - retry yapılmamalı
    - 429 rate limit - 60s+30s*attempt wait ile retry
    - Body 'Limit Reach' - 429 ile aynı muamele
    - JSONDecodeError - kalıcı hata, retry yok
    - Timeout/ConnectionError - retry'a değer
    - Wrapper fonksiyonlar (quote, batch_quote, rsi, historical_eod)
    - Throttle (_MIN_CALL_INTERVAL) burst koruması
    - Test design prensibi: sessiz IGNORE'u yakalamak için low-noise mock

NOT: conftest.py tüm testlerde throttle'ı 0 set ediyor; sadece TestThrottle
     grubu doğrudan değer set ederek davranışı doğruluyor.
"""
import json
import time
import pytest
import responses
from unittest.mock import patch

import fmp_client
from fmp_client import fmp_get, quote, batch_quote, rsi, historical_eod

FMP_BASE = "https://financialmodelingprep.com/stable"


# ── Test grubu 1: Başarı durumları ─────────────────────────────────────────────

class TestSuccess:
    """200 + valid JSON dönüş senaryoları."""

    @responses.activate
    def test_simple_quote(self):
        """Tek sembol quote başarıyla list döner."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"symbol": "AAPL", "price": 293.32}],
            status=200,
        )
        res = fmp_get("quote", {"symbol": "AAPL"})
        assert isinstance(res, list)
        assert len(res) == 1
        assert res[0]["price"] == 293.32

    @responses.activate
    def test_dict_response(self):
        """Bazı endpoint'ler dict döner (örn quote-list summary)."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/some-endpoint",
            json={"key": "value"},
            status=200,
        )
        res = fmp_get("some-endpoint")
        assert res == {"key": "value"}

    @responses.activate
    def test_empty_list_no_retry(self):
        """KRİTİK: Boş [] geçerli yanıt, retry'a girmemeli.

        Eski kod result != [] kontrolüyle 3 kez retry yapıyordu.
        Yeni kod: tek call, anında döner.
        """
        responses.add(
            responses.GET,
            f"{FMP_BASE}/news/stock",
            json=[],
            status=200,
        )
        res = fmp_get("news/stock", {"symbols": "XYZ", "from": "2099-01-01"})
        assert res == []
        # SADECE 1 call yapılmış olmalı (retry yok)
        assert len(responses.calls) == 1


# ── Test grubu 2: Kalıcı hatalar (retry yapılmaması beklenir) ─────────────────

class TestPermanentErrors:
    """404, 400, 402, JSON decode - retry yapılmamalı."""

    @responses.activate
    def test_404_no_retry(self):
        """404 yanlış endpoint - retry anlamsız, anında dön."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/nonexistent-endpoint",
            json={"message": "not found"},
            status=404,
        )
        res = fmp_get("nonexistent-endpoint")
        assert res == []
        assert len(responses.calls) == 1, "404 retry yapılmamalı"

    @responses.activate
    def test_402_payment_required_no_retry(self):
        """402 Premium dışı endpoint - retry anlamsız."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/premium-only",
            status=402,
            body="Payment Required",
        )
        res = fmp_get("premium-only")
        assert res == []
        assert len(responses.calls) == 1

    @responses.activate
    def test_invalid_api_key_body(self):
        """Body'de 'Invalid API KEY' - kalıcı, retry edilmemeli."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json={"Error Message": "Invalid API KEY"},
            status=200,
        )
        res = fmp_get("quote", {"symbol": "AAPL"})
        assert res == []
        assert len(responses.calls) == 1

    @responses.activate
    def test_json_decode_error_no_retry(self):
        """HTML hata sayfası dönüyorsa JSON parse hatası, retry'a girmemeli."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            body="<html><body>Service Unavailable</body></html>",
            status=200,
            content_type="text/html",
        )
        res = fmp_get("quote", {"symbol": "AAPL"})
        assert res == []
        # HTML body için retry edilmemeli (kalıcı hata)
        assert len(responses.calls) == 1


# ── Test grubu 3: Rate limit (geçici, retry beklenir) ──────────────────────────

class TestRateLimit:
    """429 status ve body 'Limit Reach' - retry edilmeli, 60s+30s*attempt wait."""

    @responses.activate
    def test_429_then_success(self):
        """İlk call 429, ikincisi 200 - başarıyla döner."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            status=429,
        )
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"symbol": "AAPL", "price": 293.32}],
            status=200,
        )
        # time.sleep'i mock'la ki test hızlı çalışsın
        with patch("fmp_client.time.sleep") as mock_sleep:
            res = fmp_get("quote", {"symbol": "AAPL"})

        assert res == [{"symbol": "AAPL", "price": 293.32}]
        assert len(responses.calls) == 2
        # İlk retry beklemesi 60s olmalı (eski 2s değil)
        assert mock_sleep.called
        first_wait = mock_sleep.call_args_list[0][0][0]
        assert first_wait == 60, f"İlk rate limit beklemesi 60s olmalı, gerçek: {first_wait}s"

    @responses.activate
    def test_429_backoff_progression(self):
        """3 ardışık 429 sonra 200. Wait süreleri 60, 90, 120 olmalı."""
        for _ in range(3):
            responses.add(responses.GET, f"{FMP_BASE}/quote", status=429)
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"price": 100}],
            status=200,
        )
        with patch("fmp_client.time.sleep") as mock_sleep:
            res = fmp_get("quote", {"symbol": "X"}, max_retries=4)

        assert res == [{"price": 100}]
        # max_retries=4 olduğu için 3 retry mümkün, hepsinin wait'i kontrol et
        waits = [c[0][0] for c in mock_sleep.call_args_list]
        # 60+30*0=60, 60+30*1=90, 60+30*2=120
        assert waits[:3] == [60, 90, 120], f"Wait progression bozuk: {waits[:3]}"

    @responses.activate
    def test_body_limit_reach_treated_as_429(self):
        """Body'de 'Limit Reach' mesajı 429 ile aynı muamele görmeli (yeni davranış).

        Eski kod: sessizce [] döndürüyordu, retry yapmıyordu.
        Yeni kod: 60s wait ile retry.
        """
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json={"Error Message": "Limit Reach. Please upgrade your plan."},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"price": 100}],
            status=200,
        )
        with patch("fmp_client.time.sleep") as mock_sleep:
            res = fmp_get("quote", {"symbol": "AAPL"})

        assert res == [{"price": 100}]
        assert len(responses.calls) == 2, "Limit Reach retry edilmedi"
        # Wait 60s olmalı
        first_wait = mock_sleep.call_args_list[0][0][0]
        assert first_wait == 60

    @responses.activate
    def test_rate_limit_max_retries_exhausted(self):
        """Max retry sonrası başarısız - [] döner."""
        for _ in range(5):
            responses.add(responses.GET, f"{FMP_BASE}/quote", status=429)
        with patch("fmp_client.time.sleep"):
            res = fmp_get("quote", {"symbol": "X"}, max_retries=3)
        assert res == []
        # 3 deneme yapıldı
        assert len(responses.calls) == 3


# ── Test grubu 4: Geçici sunucu hataları (retry beklenir) ──────────────────────

class TestServerErrors:
    """5xx server errors - retry edilmeli."""

    @responses.activate
    def test_503_then_success(self):
        """503 Service Unavailable - retry, sonra 200."""
        responses.add(responses.GET, f"{FMP_BASE}/quote", status=503)
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"price": 100}],
            status=200,
        )
        with patch("fmp_client.time.sleep"):
            res = fmp_get("quote", {"symbol": "X"})
        assert res == [{"price": 100}]
        assert len(responses.calls) == 2

    @responses.activate
    def test_500_retry(self):
        """500 Internal Server Error - retry."""
        responses.add(responses.GET, f"{FMP_BASE}/quote", status=500)
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"price": 100}],
            status=200,
        )
        with patch("fmp_client.time.sleep"):
            res = fmp_get("quote", {"symbol": "X"})
        assert res == [{"price": 100}]
        assert len(responses.calls) == 2


# ── Test grubu 5: Network exception'ları ──────────────────────────────────────

class TestNetworkErrors:
    """Timeout, ConnectionError - retry edilmeli."""

    @responses.activate
    def test_timeout_retry(self):
        """Timeout sonrası başarı."""
        from requests.exceptions import Timeout

        responses.add(responses.GET, f"{FMP_BASE}/quote", body=Timeout("test"))
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"price": 100}],
            status=200,
        )
        with patch("fmp_client.time.sleep"):
            res = fmp_get("quote", {"symbol": "X"})
        assert res == [{"price": 100}]

    @responses.activate
    def test_connection_error_retry(self):
        """ConnectionError sonrası başarı."""
        from requests.exceptions import ConnectionError

        responses.add(responses.GET, f"{FMP_BASE}/quote", body=ConnectionError("DNS"))
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"price": 100}],
            status=200,
        )
        with patch("fmp_client.time.sleep"):
            res = fmp_get("quote", {"symbol": "X"})
        assert res == [{"price": 100}]


# ── Test grubu 6: API key handling ─────────────────────────────────────────────

class TestApiKeyHandling:

    @responses.activate
    def test_apikey_added_to_params(self):
        """API key her isteğe eklenmeli."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"price": 100}],
            status=200,
        )
        fmp_get("quote", {"symbol": "AAPL"})
        # responses.calls[0].request.url içinde apikey query param olmalı
        assert "apikey=test_key_dummy" in responses.calls[0].request.url
        assert "symbol=AAPL" in responses.calls[0].request.url

    def test_no_apikey_returns_empty(self):
        """FMP_KEY tanımsızsa boş [] dönmeli, exception fırlatılmamalı."""
        with patch("fmp_client.FMP_KEY", ""):
            res = fmp_get("quote", {"symbol": "AAPL"})
        assert res == []


# ── Test grubu 7: Wrapper fonksiyonlar ─────────────────────────────────────────

class TestWrappers:
    """quote(), batch_quote(), rsi(), historical_eod() davranışları."""

    @responses.activate
    def test_quote_wrapper_returns_dict(self):
        """quote() LIST'i dict'e normalize etmeli."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/quote",
            json=[{"symbol": "AAPL", "price": 293.32}],
            status=200,
        )
        res = quote("AAPL")
        assert isinstance(res, dict)
        assert res["price"] == 293.32

    @responses.activate
    def test_quote_wrapper_empty_returns_none(self):
        """Boş yanıt None dönmeli (dict normalize)."""
        responses.add(responses.GET, f"{FMP_BASE}/quote", json=[], status=200)
        res = quote("XYZ")
        assert res is None

    @responses.activate
    def test_batch_quote_returns_dict(self):
        """batch_quote() symbol -> dict mapping dönmeli."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/batch-quote",
            json=[
                {"symbol": "AAPL", "price": 293.32},
                {"symbol": "MSFT", "price": 415.12},
            ],
            status=200,
        )
        res = batch_quote(["AAPL", "MSFT"])
        assert "AAPL" in res
        assert "MSFT" in res
        assert res["MSFT"]["price"] == 415.12

    def test_batch_quote_empty_input(self):
        """Boş ticker listesi anında {} dönmeli (call yapılmamalı)."""
        res = batch_quote([])
        assert res == {}

    @responses.activate
    def test_rsi_wrapper(self):
        """rsi() float değer dönmeli."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/technical-indicators/rsi",
            json=[{"date": "2026-05-09", "rsi": 64.5}, {"date": "2026-05-08", "rsi": 62.3}],
            status=200,
        )
        res = rsi("AAPL")
        assert res == 64.5

    @responses.activate
    def test_historical_eod_wrapper(self):
        """historical_eod() liste dönmeli, OHLCV keys."""
        responses.add(
            responses.GET,
            f"{FMP_BASE}/historical-price-eod/full",
            json=[
                {"date": "2026-05-09", "open": 290, "high": 295, "low": 289, "close": 293, "volume": 1000000},
            ],
            status=200,
        )
        res = historical_eod("AAPL", "2026-05-01")
        assert isinstance(res, list)
        assert len(res) == 1
        assert res[0]["close"] == 293


# ── Test grubu 8: Audit raporundan öğrenilen test design rule ──────────────────

class TestDesignPrinciples:
    """10 May audit Aksiyon 3'te öğrenildi: sessiz IGNORE'u yakalamak için
    LOW-NOISE mock data kullan, AAPL gibi yüksek-haber yoğunluklu ticker'lar
    yanıltıcı pozitif sonuç verir."""

    @responses.activate
    def test_silent_param_ignore_caught(self):
        """Mock döner ne dönerse onu döner; gerçek tuzak (param ignore)
        AAPL ile değil, low-noise ticker (VST, COIN) ile yakalanır.

        Bu test integration testi DEĞİL (mock kullanıyor) ama prensip
        belgesi olarak burada: yeni endpoint testleri eklerken
        DOĞRU MOCK DATA tasarla, gerçek API'ye benzer.
        """
        # Mock: ?symbol=VST → server filtrelemiyor, AAPL döner (gerçek tuzak simülasyonu)
        responses.add(
            responses.GET,
            f"{FMP_BASE}/news/press-releases",
            json=[{"symbol": "AAPL", "title": "Apple News"}],  # filtre yok
            status=200,
        )
        res = fmp_get("news/press-releases", {"symbol": "VST"})
        # fmp_get tuzağı yakalama YETKİSİ YOK (server seviyesi)
        # Bu test sadece dökümante edici: testler çağırma kodunu değil
        # endpoint cevabını mock'lar. Gerçek sessiz IGNORE'u yakalayan
        # integration test ayrı yazılmalı (notes/2026-05-10_PRESS_RELEASE_EVAL.md).
        assert res[0]["symbol"] == "AAPL"


# ── Test grubu 9: Throttle (burst koruması) ────────────────────────────────────

class TestThrottle:
    """_MIN_CALL_INTERVAL ile burst koruması.

    10 May 2026 — agent/valuation/methods/__init__.py fetch_all_data() 11
    ardışık endpoint çağırıyor. 30 Nisan 16:31-34 burst dalgasının kaynağı.
    Throttle her call arası min 50ms zorlar (max 20 call/sn = 1200/dk,
    Ultimate 3000/dk altında güvenli).
    """

    @responses.activate
    def test_throttle_enforces_min_interval(self):
        """5 ardışık call arası min 50ms olmalı (default _MIN_CALL_INTERVAL)."""
        # conftest disable_throttle fixture'ını override et (50ms set)
        fmp_client._MIN_CALL_INTERVAL = 0.05
        fmp_client._last_call_ts = 0.0
        try:
            for _ in range(5):
                responses.add(
                    responses.GET,
                    f"{FMP_BASE}/quote",
                    json=[{"price": 100}],
                    status=200,
                )

            t0 = time.monotonic()
            for _ in range(5):
                fmp_get("quote", {"symbol": "X"})
            elapsed = time.monotonic() - t0

            # 5 call * 0.05s = 0.20s minimum (ilk call hemen, sonrakiler beklemeli)
            # En az 4 wait * 0.05s = 0.20s
            assert elapsed >= 0.20, f"Throttle yetersiz: {elapsed:.3f}s, 0.20s+ olmalı"
            # Üst sınır da makul olsun (test takılmasın)
            assert elapsed < 1.0, f"Throttle çok uzun: {elapsed:.3f}s"
        finally:
            # Diğer testler etkilenmesin
            fmp_client._MIN_CALL_INTERVAL = 0

    @responses.activate
    def test_throttle_zero_disables(self):
        """_MIN_CALL_INTERVAL=0 throttle'ı disable eder, çağrılar hızlı."""
        fmp_client._MIN_CALL_INTERVAL = 0
        for _ in range(3):
            responses.add(
                responses.GET,
                f"{FMP_BASE}/quote",
                json=[{"price": 100}],
                status=200,
            )

        t0 = time.monotonic()
        for _ in range(3):
            fmp_get("quote", {"symbol": "X"})
        elapsed = time.monotonic() - t0

        # 3 call mock'lu, throttle yok → çok hızlı (10ms altı)
        assert elapsed < 0.10, f"Throttle disable olmalı: {elapsed:.3f}s"

    @responses.activate
    def test_throttle_does_not_double_count(self):
        """Önceki call'ın kendi süresi yeterliyse extra wait olmamalı."""
        fmp_client._MIN_CALL_INTERVAL = 0.05
        fmp_client._last_call_ts = 0.0
        try:
            responses.add(
                responses.GET,
                f"{FMP_BASE}/quote",
                json=[{"price": 100}],
                status=200,
            )
            responses.add(
                responses.GET,
                f"{FMP_BASE}/quote",
                json=[{"price": 100}],
                status=200,
            )

            # İlk call
            fmp_get("quote", {"symbol": "X"})
            # 100ms bekle (throttle aralığından uzun)
            time.sleep(0.1)
            t0 = time.monotonic()
            fmp_get("quote", {"symbol": "X"})
            elapsed = time.monotonic() - t0

            # Throttle bekleme yapmamalı çünkü 100ms zaten geçti
            assert elapsed < 0.04, f"Gereksiz throttle: {elapsed:.3f}s"
        finally:
            fmp_client._MIN_CALL_INTERVAL = 0
