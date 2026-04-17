#!/usr/bin/env python3
"""
Finzora — Swing Trade Yönetim Modülü
=======================================
Agent'ın swing kararlarını yürütür:
  1. Giriş → signal tespit → BUY kararı → JSON + CSV güncelle
  2. Takip → chandelier stop hesapla → her gün güncelle
  3. Çıkış → stop/hedef tetiklenince SELL → kapalı pozisyona taşı
  4. Raporlama → Telegram'a günlük durum
"""

import os
import json
import csv
import requests
import sys as _sys
_sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "scripts"))
try:
    from event_logger import log as _log
    _log.kaynak = "swing_manager"
except ImportError:
    class _FB:
        def __getattr__(self, n): return lambda *a, **kw: None
    _log = _FB()

import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
FMP_BASE  = "https://financialmodelingprep.com/stable"
FMP_KEY   = os.environ.get("FMP_API_KEY", "")

sys.path.insert(0, str(REPO_ROOT / "scripts"))


# ── Pozisyon Açma ─────────────────────────────────────────────────────────────

def open_swing_position(
    symbol:    str,
    shares:    int,
    price:     float,
    stop:      float,
    target:    float,
    sinyaller: list,
    reasoning: str = "",
) -> dict:
    """
    Swing pozisyon açar.
    active.json + transactions.csv günceller.
    Git commit/push agent orchestrator üstlenir.
    """
    active_path = REPO_ROOT / "data" / "swing" / "active.json"
    tx_path     = REPO_ROOT / "data" / "transactions.csv"

    with open(active_path, encoding="utf-8") as f:
        active = json.load(f)

    # Kapasite kontrolü
    mevcut = active.get("aktif_pozisyonlar", [])
    if len(mevcut) >= 5:
        print(f"[Swing] Kapasite dolu (5/5) — {symbol} için yer yok")
        return {}

    # Aynı sembold zaten var mı?
    if any(p.get("sembol") == symbol for p in mevcut):
        print(f"[Swing] {symbol} zaten aktif pozisyonda")
        return {}

    poz_id = f"SWING-{datetime.now().strftime('%Y%m%d%H%M')}-{symbol}"
    atr    = abs(price - stop)

    # Chandelier stop: zirve - 3×ATR (başlangıçta giriş fiyatı = zirve)
    chandelier = round(price - 3 * atr, 2)

    yeni_poz = {
        "id":              poz_id,
        "sembol":          symbol,
        "adet":            shares,
        "giris_fiyat":     round(price, 2),
        "maliyet_baz":     round(price, 2),
        "giris_tarihi":    datetime.now().strftime("%Y-%m-%d"),
        "stop_loss":       round(stop, 2),
        "hedef_fiyat":     round(target, 2),
        "rr_oran":         2.5,
        "tarama_yontemi":  ", ".join(s.get("tip", "") for s in sinyaller),
        "giris_nedeni":    reasoning or f"Swing entry: {', '.join(s.get('tip','') for s in sinyaller)}",
        "katalizor":       "",
        "max_sure_gun":    15,
        "durum":           "AKTIF",
        "guncel_fiyat":    round(price, 2),
        "son_fiyat":       round(price, 2),
        "zirve_fiyat":     round(price, 2),
        "chandelier_stop": chandelier,
        "k11_aktif":       False,
        "k11_profit_lock": None,
        "son_guncelleme":  datetime.now().strftime("%Y-%m-%d"),
        "notlar":          [],
        "pnl_pct":         0.0,
    }

    mevcut.append(yeni_poz)
    active["aktif_pozisyonlar"] = mevcut
    active["son_guncelleme"]    = datetime.now().isoformat()

    with open(active_path, "w", encoding="utf-8") as f:
        json.dump(active, f, ensure_ascii=False, indent=2)

    # Transaction CSV
    tx_row = {
        "date":   datetime.now().strftime("%Y-%m-%d"),
        "action": "BUY",
        "symbol": symbol,
        "shares": str(shares),
        "price":  str(round(price, 2)),
        "total":  str(round(shares * price, 2)),
        "reason": (f"Swing giriş — {', '.join(s.get('tip','') for s in sinyaller)}. "
                   f"Stop: ${stop:.2f}, Hedef: ${target:.2f}"),
    }

    with open(tx_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","action","symbol","shares","price","total","reason"])
        writer.writerow(tx_row)

    print(f"[Swing] ✅ {symbol} açıldı: {shares} adet @ ${price:.2f} | stop: ${stop:.2f} | hedef: ${target:.2f}")
    return yeni_poz


# ── Pozisyon Güncelleme (Her Gün) ────────────────────────────────────────────

def update_swing_positions() -> list[dict]:
    """
    Tüm aktif swing pozisyonlarını günceller:
    - Güncel fiyat çek
    - Chandelier stop güncelle
    - K-11 kısmi kâr kontrolü
    - Stop/hedef tetiklendi mi kontrol et
    """
    active_path = REPO_ROOT / "data" / "swing" / "active.json"
    with open(active_path, encoding="utf-8") as f:
        active = json.load(f)

    pozlar  = active.get("aktif_pozisyonlar", [])
    if not pozlar:
        return []

    # Batch quote
    syms = [p["sembol"] for p in pozlar]
    try:
        r      = requests.get(f"{FMP_BASE}/batch-quote",
                              params={"symbols": ",".join(syms), "apikey": FMP_KEY},
                              timeout=10).json()
        prices = {q["symbol"]: q.get("price", 0) for q in r}
    except Exception:
        prices = {}

    uyarilar  = []
    kapanacak = []

    for poz in pozlar:
        sym     = poz["sembol"]
        price   = prices.get(sym, poz.get("guncel_fiyat", 0))
        giris   = poz["giris_fiyat"]
        stop    = poz["stop_loss"]
        hedef   = poz["hedef_fiyat"]
        adet    = poz["adet"]
        zirve   = max(poz.get("zirve_fiyat", giris), price)

        if not price:
            continue

        pnl_pct = (price - giris) / giris * 100
        atr     = abs(giris - stop)

        # Zirveyi güncelle
        poz["zirve_fiyat"]  = round(zirve, 2)
        poz["guncel_fiyat"] = round(price, 2)
        poz["son_fiyat"]    = round(price, 2)
        poz["pnl_pct"]      = round(pnl_pct, 2)
        poz["son_guncelleme"] = datetime.now().strftime("%Y-%m-%d")

        # Chandelier stop güncelle (3×ATR trailing)
        new_chandelier = round(zirve - 3 * atr, 2)
        old_chandelier = poz.get("chandelier_stop", stop)
        if new_chandelier > old_chandelier:
            poz["chandelier_stop"] = new_chandelier

        eff_stop = max(stop, poz.get("chandelier_stop", stop))

        # K-11: Kısmi kâr alma teyidi
        if pnl_pct >= 15 and not poz.get("k11_aktif"):
            poz["k11_aktif"]     = True
            poz["k11_profit_lock"] = round(max(2 * atr, price * 0.97), 2)
            uyarilar.append({
                "sembol": sym, "tip": "K11_AKTIF",
                "mesaj":  f"{sym} K-11 aktif: +{pnl_pct:.1f}% kâr kilidi devreye girdi",
            })

        # Stop tetiklendi mi?
        stop_hit = price <= eff_stop
        tgt_hit  = price >= hedef

        # Maksimum süre doldu mu?
        giris_dt  = datetime.strptime(poz["giris_tarihi"], "%Y-%m-%d")
        gun_sayisi = (datetime.now() - giris_dt).days
        sure_doldu = gun_sayisi >= poz.get("max_sure_gun", 15)

        if stop_hit:
            kapanacak.append({"poz": poz, "neden": "STOP", "fiyat": price})
        elif tgt_hit:
            kapanacak.append({"poz": poz, "neden": "HEDEF", "fiyat": price})
        elif sure_doldu:
            kapanacak.append({"poz": poz, "neden": "SURE", "fiyat": price})
        else:
            # Uyarı: Stop'a yakın (%5 içinde)
            stop_mesafe = (price - eff_stop) / price * 100
            if stop_mesafe < 4:
                uyarilar.append({
                    "sembol": sym, "tip": "STOP_YAKIN",
                    "mesaj":  f"{sym} stop'a {stop_mesafe:.1f}% yakın (${price:.2f} vs ${eff_stop:.2f})",
                })

    # Kapanacak pozisyonları işle
    for item in kapanacak:
        _close_position(item["poz"], item["neden"], item["fiyat"], active)

    active["son_guncelleme"] = datetime.now().isoformat()
    with open(active_path, "w", encoding="utf-8") as f:
        json.dump(active, f, ensure_ascii=False, indent=2)

    return uyarilar


def _close_position(poz: dict, neden: str, cikis_fiyat: float, active: dict):
    """Pozisyonu kapatır — active → closed."""
    sym   = poz["sembol"]
    giris = poz["giris_fiyat"]
    adet  = poz["adet"]
    pnl   = (cikis_fiyat - giris) / giris * 100

    # Closed pozisyona taşı
    closed_path = REPO_ROOT / "data" / "swing" / "closed.json"
    with open(closed_path, encoding="utf-8") as f:
        closed = json.load(f)

    giris_dt   = datetime.strptime(poz["giris_tarihi"], "%Y-%m-%d")
    hold_days  = (datetime.now() - giris_dt).days

    kapali_poz = {
        **poz,
        "cikis_fiyat":  round(cikis_fiyat, 2),
        "cikis_tarihi": datetime.now().strftime("%Y-%m-%d"),
        "cikis_nedeni": neden,
        "pnl":          round((cikis_fiyat - giris) * adet, 2),
        "pnl_pct":      round(pnl, 2),
        "hold_days":    hold_days,
        "durum":        "KAPALI",
        "dersler":      _auto_lesson(poz, neden, pnl),
    }

    kapalilar = closed.get("kapali_pozisyonlar", [])
    kapalilar.append(kapali_poz)
    closed["kapali_pozisyonlar"] = kapalilar
    closed["son_guncelleme"]     = datetime.now().isoformat()

    with open(closed_path, "w", encoding="utf-8") as f:
        json.dump(closed, f, ensure_ascii=False, indent=2)

    # Active'den çıkar
    active["aktif_pozisyonlar"] = [
        p for p in active.get("aktif_pozisyonlar", [])
        if p.get("sembol") != sym
    ]

    # Transaction CSV
    tx_row = {
        "date":   datetime.now().strftime("%Y-%m-%d"),
        "action": "SELL",
        "symbol": sym,
        "shares": str(adet),
        "price":  str(round(cikis_fiyat, 2)),
        "total":  str(round(adet * cikis_fiyat, 2)),
        "reason": f"Swing çıkış — {neden}. P/L: {pnl:+.1f}% ({hold_days} gün)",
    }

    with open(REPO_ROOT / "data" / "transactions.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","action","symbol","shares","price","total","reason"])
        writer.writerow(tx_row)

    icon = "✅" if pnl > 0 else "❌"
    print(f"[Swing] {icon} {sym} kapatıldı: {neden} | P/L: {pnl:+.1f}% | {hold_days}g")


def _auto_lesson(poz: dict, neden: str, pnl: float) -> str:
    """Kapanan trade için otomatik ders."""
    yontem = poz.get("tarama_yontemi", "")
    if neden == "HEDEF" and pnl > 0:
        return f"✅ Hedef tuttu. {yontem} sinyali çalıştı. R:R planlandığı gibi."
    elif neden == "STOP" and pnl < 0:
        return f"Stop tetiklendi. Giriş tezi bozuldu. {yontem} sinyali bu piyasada yetersiz kaldı."
    elif neden == "SURE":
        return f"Süre doldu ({poz.get('max_sure_gun',15)}g). Momentum beklediğimiz kadar güçlü değildi."
    elif pnl > 5:
        return f"İyi çıkış. {yontem} sinyali momentum sağladı."
    return f"Nötr sonuç. {yontem} → {neden}."


# ── Swing Durum Raporu ────────────────────────────────────────────────────────

def get_swing_report() -> str:
    """Telegram/Claude için swing durumu."""
    active_path = REPO_ROOT / "data" / "swing" / "active.json"
    closed_path = REPO_ROOT / "data" / "swing" / "closed.json"

    with open(active_path, encoding="utf-8") as f:
        active = json.load(f)
    with open(closed_path, encoding="utf-8") as f:
        closed = json.load(f)

    pozlar   = active.get("aktif_pozisyonlar", [])
    kapalilar = closed.get("kapali_pozisyonlar", [])

    lines = ["📊 SWING DURUMU\n"]

    # Aktif pozisyonlar
    if pozlar:
        lines.append(f"Aktif ({len(pozlar)}/5):")
        for p in pozlar:
            sym   = p["sembol"]
            pnl   = p.get("pnl_pct", 0)
            price = p.get("guncel_fiyat", 0)
            # stop: chandelier varsa max(chandelier, stop_loss), yoksa stop_loss
            stop_loss_val = float(p.get("stop_loss", 0) or 0)
            chandelier_val = float(p.get("chandelier_stop", 0) or 0)
            stop = max(stop_loss_val, chandelier_val) if chandelier_val else stop_loss_val
            icon  = "📈" if pnl > 0 else "📉"
            stop_dist = (price - stop) / price * 100 if price and stop else 0
            lines.append(f"  {icon} {sym}: {pnl:+.1f}% | stop %{stop_dist:.1f} uzak")
    else:
        lines.append("Aktif pozisyon yok — tarama devam ediyor")

    # Son 5 kapalı trade
    if kapalilar:
        son5   = kapalilar[-5:]
        kazanc = sum(1 for k in son5 if k.get("pnl_pct", 0) > 0)
        avg    = sum(k.get("pnl_pct", 0) for k in son5) / len(son5)
        lines.append(f"\nSon {len(son5)} trade: {kazanc}/{len(son5)} kâr | ort {avg:+.1f}%")

    # Entry sinyalleri varsa
    sig_path = REPO_ROOT / "data" / "swing_entry_signals.json"
    if sig_path.exists():
        import json as _j
        sigs = _j.load(open(sig_path))
        giris_list = sigs.get("giris_sinyalleri", [])
        if giris_list:
            lines.append(f"\n🎯 Bugün {len(giris_list)} giriş sinyali: {', '.join(giris_list[:5])}")

    return "\n".join(lines)


# ── Agent Entegrasyon Fonksiyonu ──────────────────────────────────────────────

def run_swing_morning_check() -> dict:
    """
    Her sabah çalışır:
    1. Aktif pozisyonları fiyatla güncelle
    2. Stop/hedef kontrol
    3. Entry sinyallerini yükle
    4. Agent için bağlam hazırla
    """
    # 1. Mevcut pozisyonları güncelle
    uyarilar = update_swing_positions()

    # 2. Entry sinyallerini yükle
    sig_path = REPO_ROOT / "data" / "swing_entry_signals.json"
    entry_signals = []
    if sig_path.exists():
        import json as _j
        data = _j.load(open(sig_path))
        entry_signals = data.get("giris_sinyalleri", [])

    # 3. Kapasite kontrol
    active = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
    kapasite = len(active.get("aktif_pozisyonlar", []))

    return {
        "uyarilar":      uyarilar,
        "entry_signals": entry_signals,
        "kapasite":      kapasite,
        "max_kapasite":  5,
        "bos_slot":      5 - kapasite,
        "rapor":         get_swing_report(),
    }
