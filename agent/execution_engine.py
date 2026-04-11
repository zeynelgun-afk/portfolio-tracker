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
from datetime import datetime
from pathlib import Path
import pytz

REPO_ROOT = Path(__file__).parent.parent
TR_TZ     = pytz.timezone("Europe/Istanbul")

PORTFOLIO_MAP = {
    "growth":     "data/portfolios/growth.json",
    "income":     "data/portfolios/income.json",
    "balanced":   "data/portfolios/balanced.json",
    "dividend":   "data/portfolios/dividend.json",
    "aggressive": "data/portfolios/aggressive.json",
}

# Portföy limitleri (K-12)
MAX_POSITIONS = {"growth": 6, "income": 8, "balanced": 6,
                 "dividend": 8, "aggressive": 6}
MAX_WEIGHT    = {"growth": 0.20, "income": 0.15, "balanced": 0.25,
                 "dividend": 0.15, "aggressive": 0.20}


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

        mevcut["adet"]        = int(yeni_adet)
        mevcut["maliyet_baz"] = yeni_maly
        mevcut["guncel_fiyat"] = round(price, 4)
        aksiyon = "BÜYÜT"
    else:
        # Yeni pozisyon
        if len(pozlar) >= max_poz:
            return {"ok": False, "hata": f"Portföy dolu ({max_poz}/{max_poz})"}

        yeni_poz = {
            "sembol":           symbol,
            "adet":             shares,
            "maliyet_baz":      round(price, 4),
            "guncel_fiyat":     round(price, 4),
            "giris_tarihi":     datetime.now(TR_TZ).strftime("%Y-%m-%d"),
            "stop_loss":        round(stop, 2),
            "hedef_fiyat":      round(target, 2),
            "tema":             tema,
            "giris_nedeni":     reason[:200],
            "k_checks":         k_checks or {},
            "kar_zarar":        0,
            "kar_zarar_yuzde":  0,
            "agirlik_yuzde":    round(gercek_tutar / toplam * 100, 2),
            "son_guncelleme":   datetime.now(TR_TZ).strftime("%Y-%m-%d"),
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
) -> list:
    """
    Boş nakiti fırsat listesine göre konuşlandır.
    candidates: opportunity_finder'dan gelen sıralı liste
    """
    status = get_portfolio_status(portfolio)
    nakit  = status["nakit"]
    slot   = status["slot"]

    if nakit < 1000 or slot <= 0:
        return []

    # Konuşlandırılacak max tutar
    deploy_budget = nakit * max_deploy
    slot_budget   = deploy_budget / max(slot, 1)
    slot_budget   = max(1000, min(slot_budget, 50000))  # $1K-$50K arası

    işlemler = []
    harcanan = 0

    for c in candidates:
        if harcanan >= deploy_budget or slot <= 0:
            break

        sym    = c.get("symbol","")
        price  = float(c.get("price", 0))
        stop   = float(c.get("stop", price*0.95))
        target = float(c.get("target", price*1.10))
        reason = c.get("reason","")
        tema   = c.get("tema","")
        k_res  = c.get("k_checks",{})

        if not sym or not price:
            continue

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
            status["semboller"].append(sym)

    return işlemler
