#!/usr/bin/env python3
"""
Finzora — Portföy Execution Engine
=====================================
Portföylere otomatik alım/satım yapar.
Swing_manager'ın portföy karşılığı.

Kurallar:
  - Her işlem transactions.csv'ye yazılır
  - Nakit güncellemesi JSON'a yansır
  - Git commit orchestrator üstlenir
  - Telegram bildirimi execution'dan sonra gönderilir
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
import pytz

# Olay kaydı
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
try:
    from event_logger import log as _log
    _log.kaynak = "execution_engine"
except ImportError:
    class _FallbackLog:
        kaynak = "execution_engine"
        def __getattr__(self, name):
            return lambda *a, **kw: None
    _log = _FallbackLog()

REPO_ROOT = Path(__file__).parent.parent
TR_TZ     = pytz.timezone("Europe/Istanbul")

PORTFOLIO_MAP = {
    "aggressive": "data/portfolios/aggressive.json",
    "balanced":   "data/portfolios/balanced.json",
    "dividend":   "data/portfolios/dividend.json",
}

# Portföy limitleri (K-12)
MAX_POSITIONS = {"aggressive": 6, "balanced": 6, "dividend": 6}
MAX_WEIGHT    = {"aggressive": 0.20, "balanced": 0.25, "dividend": 0.15}

_FMP_KEY = os.environ.get("FMP_API_KEY", "")


def compute_atr_stop(symbol: str, price: float, fallback_pct: float = 0.08):
    """
    ATR14 + SMA50 confluence bazlı stop hesaplar.
    Min %5 max %10 bandında tutulur.
    Hedef = price + 4×ATR.
    FMP'den veri çekilemezse fallback_pct altı stop döner (target = +fallback_pct×1.5).

    Returns: (stop, target, atr14)  — atr14 None ise fallback kullanıldı demektir.
    """
    import requests as _req
    try:
        r = _req.get(
            "https://financialmodelingprep.com/stable/historical-price-eod/full",
            params={"symbol": symbol, "apikey": _FMP_KEY}, timeout=10
        )
        if r.status_code != 200:
            raise RuntimeError(f"FMP {r.status_code}")
        d = r.json()
        if not (isinstance(d, list) and len(d) >= 15):
            raise RuntimeError("yetersiz historical")
        trs = []
        for i in range(14):
            h = d[i]["high"]; l = d[i]["low"]; pc = d[i+1]["close"]
            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        atr = sum(trs) / len(trs)
        stop = price - 2.0 * atr
        # SMA50 confluence: stop SMA50 yakınındaysa SMA50×0.99'a hizala
        if len(d) >= 50:
            sma50 = sum(x["close"] for x in d[:50]) / 50
            if abs(stop - sma50) / price < 0.015 and price > sma50:
                stop = sma50 * 0.99
        # Min %5, max %10 band
        pct = (price - stop) / price
        if pct < 0.05:
            stop = price * 0.95
        elif pct > 0.10:
            stop = price * 0.92
        target = price + 4.0 * atr
        return round(stop, 2), round(target, 2), round(atr, 2)
    except Exception:
        return (round(price * (1 - fallback_pct), 2),
                round(price * (1 + fallback_pct * 1.5), 2),
                None)


def fetch_live_price(symbol: str):
    """
    FMP'den anlık canlı fiyat + previousClose döner.
    previousClose fallback YASAKTIR — eğer canlı fiyat yoksa None döner.
    Returns: (price, previousClose) veya (None, None)
    """
    import requests as _req
    try:
        r = _req.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": symbol, "apikey": _FMP_KEY}, timeout=8
        )
        if r.status_code != 200:
            return None, None
        d = r.json()
        if not (isinstance(d, list) and d):
            return None, None
        price = float(d[0].get("price", 0) or 0)
        prev  = float(d[0].get("previousClose", 0) or 0)
        if not price or not prev:
            return None, None
        return price, prev
    except Exception:
        return None, None


def _load(portfolio: str) -> dict:
    path = REPO_ROOT / PORTFOLIO_MAP[portfolio]
    return json.load(open(path, encoding="utf-8"))


def _save(portfolio: str, data: dict):
    path = REPO_ROOT / PORTFOLIO_MAP[portfolio]
    data["son_guncelleme"] = datetime.now(TR_TZ).isoformat()
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _append_transaction(row: dict):
    """transactions.csv'ye satır ekle."""
    tx_path = REPO_ROOT / "data" / "transactions.csv"
    fieldnames = ["date","action","symbol","shares","price","total","reason"]
    file_exists = tx_path.exists()
    with open(tx_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        w.writerow({k: row.get(k,"") for k in fieldnames})


def get_portfolio_status(portfolio: str) -> dict:
    """Portföy kapasitesini ve nakit durumunu döndür."""
    data  = _load(portfolio)
    pozlar = data.get("pozisyonlar", [])
    nakit  = float(data.get("nakit", {}).get("miktar", 0))
    toplam = float(data.get("toplam_deger", 0) or nakit)
    max_poz = MAX_POSITIONS.get(portfolio, 6)
    return {
        "mevcut_poz": len(pozlar),
        "max_poz":    max_poz,
        "slot":       max_poz - len(pozlar),
        "nakit":      nakit,
        "nakit_pct":  nakit / toplam * 100 if toplam else 0,
        "toplam":     toplam,
        "semboller":  [p["sembol"] for p in pozlar],
    }


def buy_position(
    symbol:    str,
    portfolio: str,
    amount:    float,      # TL değil $ — alınacak tutar
    price:     float,
    stop:      float,
    target:    float,
    reason:    str,
    tema:      str = "",
    k_checks:  dict = None,
) -> dict:
    """
    Portföye yeni pozisyon açar veya mevcutu büyütür.
    amount: kaç dolarlık alım yapılacak
    """
    # Portföy adı normalize et
    _ALIAS = {
        "agresif":   "aggressive", "aggressive": "aggressive", "büyüme": "aggressive",
        "temettü":   "dividend",   "temettu":    "dividend",   "gelir":  "dividend",
        "dengeli":   "balanced",
    }
    portfolio = _ALIAS.get(portfolio.lower(), portfolio.lower())

    if portfolio not in PORTFOLIO_MAP:
        return {"ok": False, "hata": f"Bilinmeyen portföy: {portfolio}"}

    data   = _load(portfolio)
    pozlar = data.get("pozisyonlar", [])
    nakit  = float(data.get("nakit", {}).get("miktar", 0))
    toplam = float(data.get("toplam_deger", nakit))
    max_poz = MAX_POSITIONS.get(portfolio, 6)

    # Nakit yeterli mi?
    if amount > nakit:
        amount = min(nakit * 0.95, amount)  # Max nakitin %95'i
        if amount < 500:
            _log.hata(f"ALIŞ BAŞARISIZ: {symbol}", f"Yetersiz nakit: ${nakit:.0f} | {portfolio}", kaynak="execution_engine.buy")
            return {"ok": False, "hata": f"Yetersiz nakit: ${nakit:.0f}"}

    # K-12 ağırlık kontrolü
    max_w = MAX_WEIGHT.get(portfolio, 0.20)
    if amount / toplam > max_w:
        amount = toplam * max_w * 0.95

    shares = int(amount / price)
    if shares < 1:
        return {"ok": False, "hata": "Yetersiz lot"}

    gercek_tutar = round(shares * price, 2)

    # Mevcut pozisyon var mı?
    mevcut = next((p for p in pozlar if p["sembol"] == symbol), None)

    if mevcut:
        # Büyüt — ortalama maliyet hesapla
        eski_adet  = float(mevcut["adet"])
        eski_maly  = float(mevcut["maliyet_baz"])
        yeni_adet  = eski_adet + shares
        yeni_maly  = round((eski_adet*eski_maly + gercek_tutar) / yeni_adet, 4)

        mevcut["adet"]              = int(yeni_adet)
        mevcut["maliyet_baz"]       = yeni_maly
        mevcut["guncel_fiyat"]      = round(price, 4)
        mevcut["yatirim"]           = round(yeni_adet * yeni_maly, 2)
        mevcut["guncel_deger"]      = round(yeni_adet * price, 2)
        mevcut["giris_tarihi"]      = mevcut.get("giris_tarihi", datetime.now(TR_TZ).strftime("%Y-%m-%d"))
        aksiyon = "BÜYÜT"
    else:
        # Yeni pozisyon
        if len(pozlar) >= max_poz:
            _log.hata(f"ALIŞ BAŞARISIZ: {symbol}", f"Portföy dolu {max_poz}/{max_poz} | {portfolio}", kaynak="execution_engine")
            return {"ok": False, "hata": f"Portföy dolu ({len(pozlar)}/{max_poz})"}

        # Sembol bilgisi çek
        try:
            import requests as _req
            pf_info = _req.get(
                f"https://financialmodelingprep.com/stable/profile",
                params={"symbol": symbol, "apikey": os.environ.get("FMP_API_KEY", "")},
                timeout=6
            ).json()
            pf_info = pf_info[0] if isinstance(pf_info, list) and pf_info else {}
        except Exception:
            pf_info = {}

        yeni_poz = {
            "sembol":               symbol,
            "isim":                 pf_info.get("companyName", symbol),
            "sektor":               pf_info.get("sector", ""),
            "adet":                 shares,
            "maliyet_baz":          round(price, 4),
            "giris_fiyati":         round(price, 4),
            "guncel_fiyat":         round(price, 4),
            "yatirim":              round(gercek_tutar, 2),
            "guncel_deger":         round(gercek_tutar, 2),
            "kar_zarar":            0.0,
            "kar_zarar_yuzde":      0.0,
            "gunluk_degisim_yuzde": 0.0,
            "agirlik_yuzde":        round(gercek_tutar / toplam * 100, 2),
            "giris_tarihi":         datetime.now(TR_TZ).strftime("%Y-%m-%d"),
            "stop_loss":            round(stop, 2),
            "hedef_fiyat":          round(target, 2),
            "tema":                 tema,
            "giris_nedeni":         reason[:200],
            "son_guncelleme":       datetime.now(TR_TZ).strftime("%Y-%m-%d"),
            "cb_kaynak":            f"transactions-{datetime.now(TR_TZ).strftime('%Y-%m-%d')}",
            "stop_faz":             1,
            "zirve_fiyat":          round(price, 2),
            "stop_mesafe_pct":      round((price - stop) / price * 100, 2),
            "durum":                "✅ Normal",
        }
        pozlar.append(yeni_poz)
        aksiyon = "YENİ POZİSYON"

    # Nakit güncelle
    data["nakit"]["miktar"] = round(nakit - gercek_tutar, 2)
    data["pozisyonlar"] = pozlar
    _save(portfolio, data)

    # Transaction kaydet
    _append_transaction({
        "date":   datetime.now(TR_TZ).strftime("%Y-%m-%d"),
        "action": "BUY",
        "symbol": symbol,
        "shares": shares,
        "price":  round(price, 2),
        "total":  gercek_tutar,
        "reason": reason[:100],
    })

    print(f"[Execution] {aksiyon} {portfolio.upper()} — {symbol} "
          f"{shares} adet @${price:.2f} = ${gercek_tutar:,.0f}")

    _log.islem(
        f"ALIŞ: {symbol}",
        f"{shares} adet @ ${price:.2f} | {portfolio.upper()} | ${gercek_tutar:,.0f}\n"
        f"Stop: ${stop:.2f} | Hedef: ${target:.2f}\n"
        f"Neden: {reason[:120]}",
        kaynak="execution_engine"
    )
    return {
        "ok":      True,
        "aksiyon": aksiyon,
        "sembol":  symbol,
        "portföy": portfolio,
        "adet":    shares,
        "fiyat":   round(price, 2),
        "tutar":   gercek_tutar,
        "stop":    round(stop, 2),
        "hedef":   round(target, 2),
    }


def sell_position(
    symbol:    str,
    portfolio: str,
    reason:    str,
    pct:       float = 100.0,   # Kaçta kaçı satılacak (100 = tamamı)
    price:     float = None,
) -> dict:
    """
    Portföyden pozisyon satar.
    pct=100 → tam çıkış, pct=25 → kısmi satış
    """
    if portfolio not in PORTFOLIO_MAP:
        return {"ok": False, "hata": f"Bilinmeyen portföy: {portfolio}"}

    data   = _load(portfolio)
    pozlar = data.get("pozisyonlar", [])

    poz = next((p for p in pozlar if p["sembol"] == symbol), None)
    if not poz:
        return {"ok": False, "hata": f"{symbol} portföyde yok"}

    mevcut_adet = int(poz.get("adet", 0))
    satis_fiyat = price or float(poz.get("guncel_fiyat", poz.get("maliyet_baz", 0)))
    satis_adet  = max(1, int(mevcut_adet * pct / 100))
    tutar       = round(satis_adet * satis_fiyat, 2)

    maliyet_baz = float(poz.get("maliyet_baz", satis_fiyat))
    pnl_pct     = round((satis_fiyat - maliyet_baz) / maliyet_baz * 100, 2)

    if satis_adet >= mevcut_adet or pct >= 99:
        # Tam çıkış
        pozlar = [p for p in pozlar if p["sembol"] != symbol]
        print(f"[Execution] TAM ÇIKIŞ {portfolio.upper()} — {symbol} "
              f"{satis_adet} adet @${satis_fiyat:.2f} P/L:{pnl_pct:+.1f}%")
    else:
        # Kısmi satış
        poz["adet"] = mevcut_adet - satis_adet
        print(f"[Execution] KISMİ SATIŞ {portfolio.upper()} — {symbol} "
              f"{satis_adet}/{mevcut_adet} adet @${satis_fiyat:.2f} P/L:{pnl_pct:+.1f}%")

    # Nakit güncelle
    nakit = float(data.get("nakit", {}).get("miktar", 0))
    data["nakit"]["miktar"] = round(nakit + tutar, 2)
    data["pozisyonlar"] = pozlar
    _save(portfolio, data)

    # Transaction kaydet
    _append_transaction({
        "date":   datetime.now(TR_TZ).strftime("%Y-%m-%d"),
        "action": "SELL",
        "symbol": symbol,
        "shares": satis_adet,
        "price":  round(satis_fiyat, 2),
        "total":  tutar,
        "reason": reason[:100],
    })

    _log.islem(
        f"SATIŞ: {symbol} {pnl_pct:+.1f}%",
        f"{satis_adet} adet @ ${satis_fiyat:.2f} | {portfolio.upper()} | ${tutar:,.0f}\n"
        f"P&L: {pnl_pct:+.1f}%\n"
        f"Neden: {reason[:120]}",
        kaynak="execution_engine"
    )
    return {
        "ok":      True,
        "sembol":  symbol,
        "portföy": portfolio,
        "adet":    satis_adet,
        "fiyat":   round(satis_fiyat, 2),
        "tutar":   tutar,
        "pnl_pct": pnl_pct,
    }


def deploy_cash(
    portfolio:   str,
    candidates:  list,     # [{"symbol","price","stop","target","reason","tema","score"}]
    max_deploy:  float = 0.8,  # Nakitin en fazla %80'i bir seferde konuşlandır
    add_only:    bool  = False, # True = sadece mevcut pozisyonları büyüt (slot=0)
) -> list:
    """
    Boş nakiti fırsat listesine göre konuşlandır.
    candidates: opportunity_finder'dan gelen sıralı liste
    """
    status = get_portfolio_status(portfolio)
    nakit  = status["nakit"]
    slot   = status["slot"]

    if nakit < 1000:
        return []

    # Slot yoksa sadece mevcut pozisyonları büyütebiliriz
    if slot <= 0:
        add_only = True
        if nakit < 2000:
            return []

    # Konuşlandırılacak max tutar
    deploy_budget = nakit * max_deploy
    slot_budget   = deploy_budget / max(slot, 1)
    slot_budget   = max(1000, min(slot_budget, 50000))  # $1K-$50K arası

    işlemler = []
    harcanan = 0

    for c in candidates:
        if harcanan >= deploy_budget:
            break
        if add_only and slot <= 0 and c.get("symbol","") not in status["semboller"]:
            continue  # add_only modunda yeni sembol alma

        sym    = c.get("symbol","")
        price  = float(c.get("price", 0))
        reason = c.get("reason","")
        tema   = c.get("tema","")
        k_res  = c.get("k_checks",{})

        if not sym or not price:
            continue

        # Stop/target ATR14 bazlı (aday dict'te yoksa veya 0 ise)
        cand_stop   = float(c.get("stop", 0) or 0)
        cand_target = float(c.get("target", 0) or 0)
        if cand_stop and cand_target and cand_stop < price < cand_target:
            stop, target = cand_stop, cand_target
        else:
            stop, target, _atr = compute_atr_stop(sym, price)

        # Mevcut pozisyonda var mı?
        if sym in status["semboller"]:
            tutar = min(slot_budget * 0.5, deploy_budget - harcanan)
        else:
            tutar = min(slot_budget, deploy_budget - harcanan)

        result = buy_position(sym, portfolio, tutar, price, stop, target,
                              reason, tema, k_res)
        if result["ok"]:
            işlemler.append(result)
            harcanan += result["tutar"]
            if sym not in status["semboller"]:
                slot -= 1
            if "semboller" not in status:
                status["semboller"] = []
            status["semboller"].append(sym)

    return işlemler
