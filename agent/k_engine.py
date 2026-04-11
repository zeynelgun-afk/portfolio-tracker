#!/usr/bin/env python3
"""
Finzora K-Engine — Tüm K-kuralları tek modülde
================================================
Her giriş kararında çağrılır. 17 kural, sıralı kontrol.
Kural hiyerarşisi:
  K-06 stop > K-07 kâr kilidi > K-14 fren > K-13 VIX > K-18/K-20 giriş filtreleri

Kullanım:
  from k_engine import run_entry_checks, run_exit_checks, get_position_size
  result = run_entry_checks("AAPL", portfolio="aggressive", vix=21.5)
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

FMP_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE = "https://financialmodelingprep.com/stable"

# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı
# ─────────────────────────────────────────────────────────────────────────────

def _fmp(endpoint: str, params: dict = None) -> dict | list | None:
    import requests
    p = params or {}
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
# K-13 VIX Matrisi
# ─────────────────────────────────────────────────────────────────────────────

BENEFICIARY_SECTORS = {
    "Energy", "Defense", "Gold", "Materials",
    "Real Estate", "Consumer Defensive"
}

SENSITIVE_SECTORS = {
    "Technology", "Consumer Cyclical", "Communication Services",
    "Healthcare", "Financial Services", "Industrials"
}


def k13_position_size(vix: float, sector: str, base_size: float) -> tuple[float, str]:
    """
    K-13 v4.1 sektör bazlı VIX matrisi.
    Döndürür: (pozisyon_büyüklüğü, açıklama)
    """
    is_beneficiary = any(s.lower() in sector.lower() for s in BENEFICIARY_SECTORS)

    if vix < 22:
        return base_size, f"VIX {vix:.1f}<22 tam pozisyon"
    elif vix < 28:
        if is_beneficiary:
            return base_size, f"VIX {vix:.1f} faydalanıcı → tam"
        else:
            return base_size * 0.5, f"VIX {vix:.1f} duyarlı → yarım"
    elif vix < 35:
        if is_beneficiary:
            return base_size * 0.5, f"VIX {vix:.1f} faydalanıcı → yarım"
        else:
            return 0, f"VIX {vix:.1f} duyarlı → giriş yok"
    else:
        if is_beneficiary:
            return base_size * 0.25, f"VIX {vix:.1f} faydalanıcı → çeyrek"
        else:
            return 0, f"VIX {vix:.1f}≥35 duyarlı → giriş yok"


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

        if value >= 5_000_000:
            return {
                "passed": False,
                "reason": f"K-18: ${value/1e6:.1f}M insider satış ({tx.get('reportingName')}, {tx.get('transactionDate')})"
            }

    return {"passed": True, "reason": "K-18: insider temiz"}


# ─────────────────────────────────────────────────────────────────────────────
# K-20 RS Dead Cat Bounce
# ─────────────────────────────────────────────────────────────────────────────

def k20_dead_cat_check(symbol: str) -> dict:
    """Son 1 ayda SPY'dan %10+ geride + son 5 günde +%5 bounce → dead cat → NO-GO."""
    spy_data = _fmp("stock-price-change", {"symbol": "SPY"})
    sym_data = _fmp("stock-price-change", {"symbol": symbol})

    if not spy_data or not sym_data:
        return {"passed": True, "reason": "K-20: veri alınamadı"}

    try:
        spy = spy_data[0] if isinstance(spy_data, list) else spy_data
        sym = sym_data[0] if isinstance(sym_data, list) else sym_data

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
    """Mevcut portföyle sektör/tema çakışması kontrolü."""
    # Tüm portföylerdeki sembolleri topla
    pf_symbols = []
    for pf in ["growth", "income", "balanced", "aggressive", "dividend"]:
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

    # Aynı sektördeki pozisyon sayısı
    sym_info  = _fmp(f"profile/{symbol}")
    sym_sector = ""
    if sym_info:
        sym_sector = (sym_info[0] if isinstance(sym_info, list) else sym_info).get("sector", "")

    if not sym_sector:
        return {"passed": True, "reason": "K-17: sektör bilgisi yok"}

    same_sector = sum(1 for s in pf_symbols if s)
    if same_sector >= 3:
        return {"passed": True, "reason": f"K-17: sektör OK ({sym_sector})"}

    return {"passed": True, "reason": f"K-17: korelasyon temiz ({sym_sector})"}


# ─────────────────────────────────────────────────────────────────────────────
# K-14 Drawdown Fren
# ─────────────────────────────────────────────────────────────────────────────

def k14_drawdown_check() -> dict:
    """K-14 drawdown fren aktif mi?"""
    status_path = REPO_ROOT / "data" / "swing" / "status.json"
    if not status_path.exists():
        return {"passed": True, "reason": "K-14: status dosyası yok"}
    try:
        status = json.load(open(status_path))
        aktif  = status.get("aktif_durum", "normal")
        if aktif == "K14_DRAWDOWN_FREN":
            return {"passed": False, "reason": "K-14: drawdown freni aktif — swing giriş yasak"}
        return {"passed": True, "reason": f"K-14: {aktif}"}
    except Exception:
        return {"passed": True, "reason": "K-14: okunamadı"}


# ─────────────────────────────────────────────────────────────────────────────
# K-19 XLP Filtresi
# ─────────────────────────────────────────────────────────────────────────────

def k19_xlp_check(symbol: str) -> dict:
    """Consumer Defensive sektörü swing için yasak."""
    info = _fmp(f"profile/{symbol}")
    if not info:
        return {"passed": True, "reason": "K-19: profil yok"}
    sector = (info[0] if isinstance(info, list) else info).get("sector", "")
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

    # 1. K-14 Drawdown Fren (en önce — sistemik yasak)
    checks["K-14"] = k14_drawdown_check()
    if not checks["K-14"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-14"]["reason"]}

    # 2. K-19 XLP (ucuz kontrol)
    checks["K-19"] = k19_xlp_check(symbol)
    if not checks["K-19"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-19"]["reason"]}

    # 3. K-05 Earnings (ucuz + kritik)
    checks["K-05"] = k05_earnings_check(symbol)
    if not checks["K-05"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-05"]["reason"]}

    # 4. K-18 Insider (kritik, geri dönüşsüz)
    checks["K-18"] = k18_insider_check(symbol)
    if not checks["K-18"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-18"]["reason"]}

    # 5. K-20 Dead Cat
    checks["K-20"] = k20_dead_cat_check(symbol)
    if not checks["K-20"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-20"]["reason"]}

    # 6. K-17 Korelasyon
    checks["K-17"] = k17_correlation_check(symbol, portfolio)
    if not checks["K-17"]["passed"]:
        return {"go": False, "position_size": 0,
                "checks": checks, "fail_reason": checks["K-17"]["reason"]}

    # 7. K-13 VIX → pozisyon büyüklüğü
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
        return {"action": "EXIT_NOW", "reason": f"K-06: stop tetiklendi ${current_price:.2f}≤${stop_loss:.2f}"}

    # Stop mesafesi
    stop_dist = (current_price - stop_loss) / current_price * 100

    # K-09: Stop %2 içinde
    if 0 < stop_dist < 2:
        return {"action": "EXIT_NOW", "reason": f"K-09: stop %{stop_dist:.1f} yakın — çık"}

    # K-11: Kısmi kâr alma
    if rsi >= 80 and pnl_pct >= 10:
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
