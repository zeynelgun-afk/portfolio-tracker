#!/usr/bin/env python3
"""
Finzora K-Engine — Tüm K-kuralları tek modülde
================================================
Her giriş kararında çağrılır. 17 kural, sıralı kontrol.
Kural hiyerarşisi:
  K-06 stop > K-07 kâr kilidi > K-13 VIX > K-18/K-20 giriş filtreleri
(K-14 drawdown freni 11 Nisan 2026'da kaldırıldı — normal pozisyon boyutlandırma kullanılır)

Kullanım:
  from k_engine import run_entry_checks, run_exit_checks, get_position_size
  result = run_entry_checks("AAPL", portfolio="aggressive", vix=21.5)
"""

import os
# --- olay kaydı ---
import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / 'scripts'))
try:
    from event_logger import log as _log
    _log.kaynak = 'k_engine'
except ImportError:
    class _FB:
        kaynak='k_engine'
        def __getattr__(self, n): return lambda *a, **kw: None
    _log = _FB()
# --- /olay kaydı ---

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "agent"))

FMP_KEY = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"

# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı — merkezi fmp_client üzerinden (observability entegrasyonu için).
# Eski `_fmp` manuel requests kullanıyordu → FMP çağrıları finzora_stats'ta görünmüyordu.
# ─────────────────────────────────────────────────────────────────────────────

def _fmp(endpoint: str, params: dict = None) -> dict | list | None:
    """FMP çağrısı — merkezi fmp_client (observability loglanır)."""
    try:
        from fmp_client import fmp_get as _centralized_fmp_get
        result = _centralized_fmp_get(endpoint, params or {})
        # Merkezi client [] veya None dönebilir; k_engine None bekler.
        return result if result else None
    except ImportError:
        # Fallback: eski manuel requests (fmp_client modülü yoksa)
        import requests
        p = dict(params or {})
        p["apikey"] = FMP_KEY
        try:
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
            return r.json()
        except Exception:
            return None


def _run_script(script: str, symbol: str) -> dict:
    """K-kural script'ini çalıştır, JSON çıktısını parse et."""
    script_path = REPO_ROOT / "scripts" / script
    if not script_path.exists():
        return {"passed": True, "reason": f"{script} bulunamadı"}
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), symbol, "--quiet", "--json"],
            capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except Exception:
                pass
        # Script JSON döndürmediyse exit code'a bak
        return {"passed": result.returncode == 0, "raw": result.stdout[:200]}
    except Exception as e:
        return {"passed": True, "reason": f"script hatası: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# K-13 VIX Matrisi (v4.1 — kriz tipine göre sektör matrisi)
# ─────────────────────────────────────────────────────────────────────────────
#
# Matris data/k13_crisis_matrix.json'dan yüklenir. Örnek:
# {
#   "aktif_kriz": "jeopolitik",
#   "beneficiary": ["Energy","Defense","Gold","Materials","Real Estate","Consumer Defensive"],
#   "sensitive":   ["Technology","Consumer Cyclical","Communication Services",...]
# }
#
# Kriz değişince sadece bu dosyayı güncelle (pandemi → sağlık/tech benef, finansal → altın+bonds, vs).

_DEFAULT_BENEFICIARY = {
    "Energy", "Defense", "Gold", "Materials",
    "Real Estate", "Consumer Defensive"
}
_DEFAULT_SENSITIVE = {
    "Technology", "Consumer Cyclical", "Communication Services",
    "Healthcare", "Financial Services", "Industrials"
}


def _load_crisis_matrix() -> tuple[set, set, str]:
    """data/k13_crisis_matrix.json → (beneficiary, sensitive, kriz_adi).

    Kriz 'yok' durumunda beneficiary+sensitive boş olabilir (K-13 sade VIX'e düşer).
    Dosya hiç yoksa default (jeopolitik) matris döner.
    """
    p = REPO_ROOT / "data" / "k13_crisis_matrix.json"
    if not p.exists():
        return _DEFAULT_BENEFICIARY, _DEFAULT_SENSITIVE, "jeopolitik (default)"
    try:
        d = json.load(open(p))
        # Önemli: boş liste kriz='yok' durumunda geçerli. sadece 'beneficiary' anahtarı
        # hiç yoksa default kullan.
        kriz = d.get("aktif_kriz", "bilinmeyen")
        if "beneficiary" in d:
            benef = set(d["beneficiary"])
        else:
            benef = _DEFAULT_BENEFICIARY
        if "sensitive" in d:
            sens = set(d["sensitive"])
        else:
            sens = _DEFAULT_SENSITIVE
        return benef, sens, kriz
    except Exception as e:
        print(f"[K-13] matrix okuma hatası: {e}, default kullanılıyor")
        return _DEFAULT_BENEFICIARY, _DEFAULT_SENSITIVE, "default_fallback"


BENEFICIARY_SECTORS, SENSITIVE_SECTORS, _K13_AKTIF_KRIZ = _load_crisis_matrix()


def k13_position_size(vix: float, sector: str, base_size: float) -> tuple[float, str]:
    """
    K-13 v4.2 sektör bazlı VIX matrisi.
    Matrisi HER çağrıda taze okur — Claude kriz tespitini macro_intelligence run'ında
    güncelleyebiliyor, bu değişikliğin aynı gün içinde yansıması için.
    Döndürür: (pozisyon_büyüklüğü, açıklama)
    """
    # Matrisi her çağrıda yeniden yükle (dosya cache OS seviyesinde hızlı)
    benef, sens, kriz = _load_crisis_matrix()

    is_beneficiary = any(s.lower() in sector.lower() for s in benef)

    if vix < 22:
        return base_size, f"VIX {vix:.1f}<22 tam pozisyon [{kriz}]"
    elif vix < 28:
        if is_beneficiary:
            return base_size, f"VIX {vix:.1f} [{kriz}] faydalanıcı → tam"
        else:
            return base_size * 0.5, f"VIX {vix:.1f} [{kriz}] duyarlı → yarım"
    elif vix < 35:
        if is_beneficiary:
            return base_size * 0.5, f"VIX {vix:.1f} [{kriz}] faydalanıcı → yarım"
        else:
            return 0, f"VIX {vix:.1f} [{kriz}] duyarlı → giriş yok"
    else:
        if is_beneficiary:
            return base_size * 0.25, f"VIX {vix:.1f} [{kriz}] faydalanıcı → çeyrek"
        else:
            return 0, f"VIX {vix:.1f}≥35 [{kriz}] duyarlı → giriş yok"


# ─────────────────────────────────────────────────────────────────────────────
# K-05 Earnings Proximity
# ─────────────────────────────────────────────────────────────────────────────

def k05_earnings_check(symbol: str) -> dict:
    """Earnings ≤2 iş günü içinde → NO-GO."""
    today = datetime.now()
    end   = (today + timedelta(days=5)).strftime("%Y-%m-%d")
    data  = _fmp("earnings-calendar", {"symbol": symbol,
                                        "from": today.strftime("%Y-%m-%d"),
                                        "to": end})
    if not data:
        return {"passed": True, "reason": "earnings verisi alınamadı"}

    for event in data:
        # FMP earnings-calendar endpoint symbol filtresini görmezden geliyor
        # — tüm şirketlerin takvimini döndürüyor. Manuel filtre zorunlu.
        if event.get("symbol", "").upper() != symbol.upper():
            continue
        e_date = event.get("date", "")
        try:
            d = datetime.strptime(e_date, "%Y-%m-%d")
            delta = (d - today).days
            if 0 <= delta <= 2:
                return {
                    "passed": False,
                    "reason": f"K-05: earnings {e_date} ({delta} gün) — giriş yasak"
                }
        except ValueError:
            continue

    return {"passed": True, "reason": "K-05: earnings uzak"}


# ─────────────────────────────────────────────────────────────────────────────
# K-18 Insider Check
# ─────────────────────────────────────────────────────────────────────────────

def k18_insider_check(symbol: str) -> dict:
    """Son 30 günde CEO/CFO/Direktör $5M+ satışı → NO-GO."""
    data = _fmp("insider-trading/search", {"symbol": symbol, "limit": 30})
    if not data:
        return {"passed": True, "reason": "insider veri yok"}

    cutoff = datetime.now() - timedelta(days=30)
    SENIOR = {"ceo", "cfo", "president", "director", "chief", "officer"}

    for tx in data:
        tx_type = tx.get("transactionType", "").lower()
        if "sale" not in tx_type and "sell" not in tx_type:
            continue

        title = tx.get("reportingName", "").lower() + " " + tx.get("typeOfOwner", "").lower()
        if not any(s in title for s in SENIOR):
            continue

        try:
            tx_date = datetime.strptime(tx.get("transactionDate", ""), "%Y-%m-%d")
            if tx_date < cutoff:
                continue
        except ValueError:
            continue

        shares = float(tx.get("securitiesTransacted", 0) or 0)
        price  = float(tx.get("price", 0) or 0)
        value  = shares * price

        # Market cap bazlı eşik (split sonrası fiyat yanıltıcı olabilir)
        # Büyük şirket (>$50B): $25M eşiği — üst düzey satışlar yaygın
        # Orta şirket ($5B-50B): $10M eşiği
        # Küçük şirket (<$5B): $3M eşiği
        mcap_data = _fmp("profile", {"symbol": symbol}) or []
        mcap_item = mcap_data[0] if isinstance(mcap_data, list) and mcap_data else {}
        mcap = float(mcap_item.get("marketCap") or mcap_item.get("mktCap") or 0)
        if mcap >= 50_000_000_000:      # $50B+
            threshold = 25_000_000
        elif mcap >= 5_000_000_000:     # $5B-50B
            threshold = 10_000_000
        else:                            # <$5B
            threshold = 3_000_000

        if value >= threshold:
            return {
                "passed": False,
                "reason": f"K-18: ${value/1e6:.1f}M insider satış ({tx.get('reportingName')}, {tx.get('transactionDate')}) eşik:${threshold/1e6:.0f}M"
            }

    return {"passed": True, "reason": "K-18: insider temiz"}


# ─────────────────────────────────────────────────────────────────────────────
# K-20 RS Dead Cat Bounce
# ─────────────────────────────────────────────────────────────────────────────

def k20_dead_cat_check(symbol: str) -> dict:
    """Son 1 ayda SPY'dan %10+ geride + son 5 günde +%5 bounce → dead cat → NO-GO."""
    spy_data = _fmp("stock-price-change", {"symbol": "SPY"}) or []
    sym_data = _fmp("stock-price-change", {"symbol": symbol}) or []

    if not spy_data or not sym_data:
        return {"passed": True, "reason": "K-20: veri alınamadı"}

    try:
        spy = spy_data[0] if isinstance(spy_data, list) and spy_data else {}
        sym = sym_data[0] if isinstance(sym_data, list) and sym_data else {}

        spy_1m = float(spy.get("1M", 0) or 0)
        sym_1m = float(sym.get("1M", 0) or 0)
        sym_5d = float(sym.get("5D", 0) or 0)

        rs_1m = sym_1m - spy_1m

        if rs_1m <= -10 and sym_5d >= 5:
            return {
                "passed": False,
                "reason": f"K-20: dead cat — RS 1M {rs_1m:+.1f}% vs SPY, son 5G +{sym_5d:.1f}%"
            }

        return {"passed": True, "reason": f"K-20: RS temiz (1M: {rs_1m:+.1f}%)"}

    except (ValueError, TypeError, IndexError):
        return {"passed": True, "reason": "K-20: hesaplanamadı"}


# ─────────────────────────────────────────────────────────────────────────────
# K-17 Korelasyon / Tema Çakışması
# ─────────────────────────────────────────────────────────────────────────────

def k17_correlation_check(symbol: str, portfolio: str = "all") -> dict:
    """Mevcut portföyle sektör/tema çakışması kontrolü.

    Sektör lookup sector_cache üzerinden yapılır — her çağrıda N×FMP profile
    çağrısı yerine 7 gün TTL'li cache. Rate limit koruması + hızlı."""
    # Tüm portföylerdeki sembolleri topla
    pf_symbols = []
    for pf in ["aggressive", "balanced", "dividend"]:
        p = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
        if p.exists():
            try:
                data = json.load(open(p))
                for pos in data.get("pozisyonlar", []):
                    pf_symbols.append(pos.get("sembol", ""))
            except Exception:
                pass

    if symbol in pf_symbols:
        return {"passed": False, "reason": f"K-17: {symbol} zaten portföyde"}

    # Sektör lookup (merkezi cache — FMP profile sadece ilk çağrıda)
    try:
        from sector_cache import get_sector as _get_sector
    except ImportError:
        def _get_sector(s):
            r = _fmp("profile", {"symbol": s}) or []
            item = r[0] if isinstance(r, list) and r else {}
            return (item.get("sector", "") or "").strip().lower().replace(" ", "_")

    sym_sector = _get_sector(symbol)
    if not sym_sector or sym_sector == "diger":
        return {"passed": True, "reason": "K-17: sektör bilgisi yok"}

    # Aynı sektördeki pozisyon sayısı
    same_sector_count = 0
    for s in pf_symbols:
        if not s:
            continue
        s_sector = _get_sector(s)
        if s_sector and s_sector == sym_sector:
            same_sector_count += 1

    # Aynı sektörden 2+ pozisyon varsa uyar, 3+ ise reddet
    if same_sector_count >= 3:
        return {
            "passed": False,
            "reason": f"K-17: {sym_sector} sektöründe {same_sector_count} pozisyon var — yoğunlaşma riski"
        }

    return {"passed": True, "reason": f"K-17: korelasyon temiz ({sym_sector}, aynı sektör: {same_sector_count})"}


# ─────────────────────────────────────────────────────────────────────────────
# K-14 KALDIRILDI (11 Nisan 2026) — no-op stub
# ─────────────────────────────────────────────────────────────────────────────
# K-14 drawdown freni tamamen kaldırıldı. Normal pozisyon boyutlandırma yapılır,
# psikoloji pre-entry test'i devrede (conviction_scorer'daki risk bileşeni).
# Bu stub sadece eski çağrı yerlerinin kırılmaması için var.

def k14_drawdown_check() -> dict:
    """K-14 KALDIRILDI — her zaman geçer. Geriye uyumluluk için stub."""
    return {"passed": True, "reason": "K-14 kaldırıldı (11 Nisan 2026)"}


# ─────────────────────────────────────────────────────────────────────────────
# K-19 XLP Filtresi
# ─────────────────────────────────────────────────────────────────────────────

def k19_xlp_check(symbol: str, portfolio: str = "swing") -> dict:
    """Consumer Defensive sektörü swing için yasak. Portföy alımlarına uygulanmaz."""
    # Portföy alımlarında K-19 geçerli değil — sadece swing için
    if portfolio in ("balanced", "dividend", "aggressive"):
        return {"passed": True, "reason": f"K-19: portföy alımı ({portfolio}) — atlandı"}
    info = _fmp("profile", {"symbol": symbol}) or []
    if not info:
        return {"passed": True, "reason": "K-19: profil yok"}
    item = info[0] if isinstance(info, list) and info else info
    sector = item.get("sector", "") if isinstance(item, dict) else ""
    if "defensive" in sector.lower() or "staples" in sector.lower():
        return {"passed": False, "reason": f"K-19: {sector} swing girişi yasak"}
    return {"passed": True, "reason": f"K-19: {sector} uygun"}


# ─────────────────────────────────────────────────────────────────────────────
# Ana Giriş Kontrol Fonksiyonu
# ─────────────────────────────────────────────────────────────────────────────

def run_entry_checks(
    symbol: str,
    vix: float = 20.0,
    sector: str = "",
    base_size: float = 5000,
    portfolio: str = "swing"
) -> dict:
    """
    Tüm K-kurallarını sırayla uygular.
    Döndürür: {
        "go": True/False,
        "position_size": float,
        "checks": {kural: sonuç},
        "fail_reason": str | None
    }
    """
    checks = {}

    # Not: K-14 drawdown freni 11 Nisan 2026'da kaldırıldı.
    # Doğrudan K-19 ile başlıyoruz.

    # 1. K-19 XLP (ucuz kontrol — sadece swing)
    checks["K-19"] = k19_xlp_check(symbol, portfolio)
    if not checks["K-19"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-19"]["reason"]}

    # 2. K-05 Earnings (ucuz + kritik)
    checks["K-05"] = k05_earnings_check(symbol)
    if not checks["K-05"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-05"]["reason"]}

    # 3. K-18 Insider (kritik, geri dönüşsüz)
    checks["K-18"] = k18_insider_check(symbol)
    if not checks["K-18"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-18"]["reason"]}

    # 4. K-20 Dead Cat
    checks["K-20"] = k20_dead_cat_check(symbol)
    if not checks["K-20"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-20"]["reason"]}

    # 5. K-17 Korelasyon
    checks["K-17"] = k17_correlation_check(symbol, portfolio)
    if not checks["K-17"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-17"]["reason"]}

    # 6. K-13 VIX → pozisyon büyüklüğü
    pos_size, k13_note = k13_position_size(vix, sector, base_size)
    checks["K-13"] = {"passed": pos_size > 0, "reason": k13_note, "size": pos_size}
    if pos_size == 0:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-13"]["reason"]}

    passed = [f"{k}: ✅" for k, v in checks.items() if v["passed"]]
    return {
        "go": True,
        "position_size": pos_size,
        "checks": checks,
        "fail_reason": None,
        "summary": " | ".join(passed)
    }


# ─────────────────────────────────────────────────────────────────────────────
# Çıkış Kontrol Fonksiyonu
# ─────────────────────────────────────────────────────────────────────────────

def run_exit_checks(
    symbol: str,
    current_price: float,
    stop_loss: float,
    entry_price: float,
    rsi: float = 50,
    highest_high: float = None,
    atr: float = None
) -> dict:
    """
    K-06, K-07, K-09, K-11 çıkış kontrolü.
    Döndürür: {action: "EXIT_NOW"/"PARTIAL"/"TIGHTEN"/"HOLD", reason: str}
    """
    pnl_pct = (current_price - entry_price) / entry_price * 100

    # K-06: Stop tetiklendi
    if current_price <= stop_loss:
        _log.kritik(
            f"K-06 STOP TETİKLENDİ: {symbol}",
            f"Fiyat: ${current_price:.2f} ≤ Stop: ${stop_loss:.2f}\n"
            f"P&L: {((current_price - entry_price) / entry_price * 100):+.1f}% | ÇIKIŞ GEREKLİ",
            kaynak="k_engine"
        )
        return {"action": "EXIT_NOW", "reason": f"K-06: stop tetiklendi ${current_price:.2f}≤${stop_loss:.2f}"}

    # Stop mesafesi
    stop_dist = (current_price - stop_loss) / current_price * 100

    # K-09: Stop %2 içinde
    if 0 < stop_dist < 2:
        _log.uyari(
            f"K-09 STOP YAKINI: {symbol}",
            f"Fiyat: ${current_price:.2f} | Stop: ${stop_loss:.2f}\n"
            f"Mesafe: %{stop_dist:.1f} (eşik: %2) — EXIT_NOW",
            kaynak="k_engine"
        )
        return {"action": "EXIT_NOW", "reason": f"K-09: stop %{stop_dist:.1f} yakın — çık"}

    # K-11: Kısmi kâr alma
    if rsi >= 80 and pnl_pct >= 15:  # K-11: orchestrator ile tutarlı eşik
        _log.uyari(
            f"K-11 KISMİ KAR ALMA: {symbol}",
            f"RSI: {rsi:.0f} | P&L: %{pnl_pct:.1f}\n%25 satış önerildi",
            kaynak="k_engine"
        )
        return {"action": "PARTIAL", "pct": 25,
                "reason": f"K-11 katman 2: RSI {rsi:.0f} + kâr %{pnl_pct:.1f}"}

    # K-07: Trailing stop sıkılaştırma
    if atr and highest_high:
        if pnl_pct >= 15:
            new_stop = highest_high - 1.5 * atr
        elif pnl_pct >= 7:
            new_stop = highest_high - 2.0 * atr
        else:
            new_stop = highest_high - 3.0 * atr

        if new_stop > stop_loss:
            _log.bilgi(
                f"K-07 trailing güncellendi: {symbol}",
                f"Stop: ${stop_loss:.2f} → ${new_stop:.2f} | P&L: %{pnl_pct:.1f}",
                kaynak="k_engine"
            )
            return {"action": "TIGHTEN",
                    "new_stop": round(new_stop, 2),
                    "reason": f"K-07: trailing güncelle ${stop_loss:.2f}→${new_stop:.2f}"}

    return {"action": "HOLD", "reason": f"Tüm kontroller OK — kâr %{pnl_pct:.1f}"}


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    r = run_entry_checks(sym, vix=21.0, sector="Technology", base_size=5000)
    print(f"\n{'✅ GO' if r['go'] else '❌ NO-GO'}: {sym}")
    for k, v in r["checks"].items():
        icon = "✅" if v["passed"] else "❌"
        print(f"  {icon} {k}: {v['reason']}")
    if not r["go"]:
        print(f"\nNeden: {r['fail_reason']}")
    else:
        print(f"\nPozisyon: ${r['position_size']:,.0f}")
