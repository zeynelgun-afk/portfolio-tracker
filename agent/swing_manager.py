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

# Tek kaynak: max eşzamanlı swing pozisyon sayısı.
# daily_update.py, memory_manager, swing_manager hepsi buradan okur.
SWING_MAX_POSITIONS = 5

sys.path.insert(0, str(REPO_ROOT / "scripts"))


# ── Telegram Bildirim Yardımcısı (27 Nis 2026 eklendi) ───────────────────────
# Memory kuralı: GROUP (-1003827034395) ONLY buy/sell actions + open/close
# reports + daily summary. Swing alım-satımları ANA grubun gönderilmesi gereken
# ZORUNLU içerikler. Eskiden hiç bildirim gitmiyordu, sadece JSON+CSV
# güncelleniyordu.
def _swing_notify_group(action_type: str, symbol: str, price: float, details: str):
    """Swing aksiyon → Finzora grubuna gönder. Hata olursa sessiz geç.

    NOT: telegram_notify.send_message env eksikse sys.exit(1) çağırır
    (BaseException). Swing akışını kırmasın diye BaseException de yakalanır.
    """
    try:
        from telegram_notify import format_action, send_message
        msg = format_action(action_type, symbol, price, details)
        send_message(msg)  # default chat_id = GROUP
        print(f"[Swing→TG] {action_type} {symbol} grubuna gönderildi")
    except SystemExit as e:
        print(f"[Swing→TG] Bildirim atlandı (env eksik, SystemExit {e.code})")
    except Exception as e:
        print(f"[Swing→TG] Bildirim atlandı: {e}")


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
    if len(mevcut) >= SWING_MAX_POSITIONS:
        print(f"[Swing] Kapasite dolu ({SWING_MAX_POSITIONS}/{SWING_MAX_POSITIONS}) — {symbol} için yer yok")
        return {}

    # Aynı sembold zaten var mı?
    if any(p.get("sembol") == symbol for p in mevcut):
        print(f"[Swing] {symbol} zaten aktif pozisyonda")
        return {}

    poz_id = f"SWING-{datetime.now().strftime('%Y%m%d%H%M')}-{symbol}"

    # Gerçek ATR14 hesaplaması (önce execution_engine, FMP historical fallback).
    # Eski: atr = abs(price - stop) → bu ATR değil, stop'un büyüklüğüydü.
    # Chandelier/trailing hesaplarında yanlış sonuç veriyordu.
    atr = None
    try:
        import sys as _sys
        _sys.path.insert(0, str(REPO_ROOT / "agent"))
        from execution_engine import compute_atr_stop as _cas_sw
        _s, _t, _atr = _cas_sw(symbol, price)
        if _atr is not None:
            atr = float(_atr)
    except Exception as _e:
        print(f"[Swing] ATR14 hesaplanamadı ({_e}), fallback abs(price-stop)")

    if atr is None or atr <= 0:
        # Son çare: stop mesafesi / 2 (stop ~2×ATR konvansiyonu)
        atr = abs(price - stop) / 2.0 if stop and stop < price else price * 0.02

    # Chandelier stop: zirve - 3×ATR (başlangıçta giriş fiyatı = zirve)
    chandelier = round(price - 3 * atr, 2)

    yeni_poz = {
        "id":              poz_id,
        "sembol":          symbol,
        "adet":            shares,
        "giris_fiyati":    round(price, 2),   # CANONICAL (closed.json ile uyumlu)
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
        "kar_zarar_yuzde": 0.0,               # CANONICAL (pnl_pct yerine)
        "tutulan_gun":     0,                 # CANONICAL (hold_days yerine)
        "atr14":           round(atr, 4),     # Trailing hesap için şart
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

    # 27 Nis 2026: Gruba alış bildirimi (memory kuralı: alım/satım gruba gider)
    yontemler = ", ".join(s.get("tip","") for s in sinyaller) or "swing"
    detay = (
        f"<b>SWING GİRİŞ</b>\n"
        f"Adet: {shares}\n"
        f"Tutar: ${shares * price:,.0f}\n"
        f"Stop: ${stop:.2f} ({(stop-price)/price*100:+.1f}%)\n"
        f"Hedef: ${target:.2f} ({(target-price)/price*100:+.1f}%)\n"
        f"R:R: 1:{((target-price)/(price-stop)):.1f}\n"
        f"Yöntem: {yontemler}\n"
        f"Gerekçe: {(reasoning or yontemler)[:140]}"
    )
    _swing_notify_group("ALIŞ", symbol, price, detay)

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
        giris   = float(poz.get("giris_fiyati", poz.get("giris_fiyat", 0)) or 0)  # Backward compat
        stop    = poz["stop_loss"]
        hedef   = poz["hedef_fiyat"]
        adet    = poz["adet"]
        zirve   = max(poz.get("zirve_fiyat", giris), price)

        if not price or not giris:
            continue

        pnl_pct = (price - giris) / giris * 100
        # ATR14 — pozisyondan kaynaklanıyor (open'da kaydedildi); yoksa fallback stop-giris farkı
        atr     = float(poz.get("atr14") or abs(giris - stop))

        # Zirveyi güncelle
        poz["zirve_fiyat"]      = round(zirve, 2)
        poz["guncel_fiyat"]     = round(price, 2)
        poz["son_fiyat"]        = round(price, 2)
        poz["kar_zarar_yuzde"]  = round(pnl_pct, 2)   # CANONICAL
        poz["son_guncelleme"]   = datetime.now().strftime("%Y-%m-%d")
        # Backward compat: eski pnl_pct alanı da güncel tutulsun (diğer scriptler geçene kadar)
        poz["pnl_pct"]          = round(pnl_pct, 2)

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
    """Pozisyonu kapatır — active → closed (canonical şema ile).

    closed.json kanonik alanları:
      sembol, id, giris_fiyati, cikis_fiyati, giris_tarihi, cikis_tarihi,
      kar_zarar_yuzde, tutulan_gun, cikis_nedeni, sonuc, ders,
      giris_nedeni, tarama_yontemi, katalizor, partial_exits
    """
    sym   = poz["sembol"]
    giris = float(poz.get("giris_fiyati", poz.get("giris_fiyat", 0)) or 0)
    adet  = poz["adet"]
    pnl   = (cikis_fiyat - giris) / giris * 100 if giris else 0

    # Closed pozisyona taşı
    closed_path = REPO_ROOT / "data" / "swing" / "closed.json"
    with open(closed_path, encoding="utf-8") as f:
        closed = json.load(f)

    giris_dt    = datetime.strptime(poz["giris_tarihi"], "%Y-%m-%d")
    tutulan_gun = (datetime.now() - giris_dt).days

    sonuc = "KAZANC" if pnl > 0 else ("NOTR" if abs(pnl) < 0.1 else "ZARAR")

    # Canonical şema ile kaydet
    kapali_poz = {
        "id":              poz.get("id", f"SWING-{sym}-{datetime.now().strftime('%Y%m%d')}"),
        "sembol":          sym,
        "adet":            adet,
        "giris_fiyati":    round(giris, 2),        # CANONICAL
        "cikis_fiyati":    round(cikis_fiyat, 2),  # CANONICAL
        "giris_tarihi":    poz["giris_tarihi"],
        "cikis_tarihi":    datetime.now().strftime("%Y-%m-%d"),
        "cikis_nedeni":    neden,
        "kar_zarar_yuzde": round(pnl, 2),          # CANONICAL
        "tutulan_gun":     tutulan_gun,            # CANONICAL
        "sonuc":           sonuc,                  # KAZANC / ZARAR / NOTR
        "ders":            _auto_lesson(poz, neden, pnl),
        "giris_nedeni":    poz.get("giris_nedeni", ""),
        "tarama_yontemi":  poz.get("tarama_yontemi", ""),
        "katalizor":       poz.get("katalizor", ""),
        "stop_loss":       poz.get("stop_loss"),
        "hedef_fiyat":     poz.get("hedef_fiyat"),
        "zirve_fiyat":     poz.get("zirve_fiyat"),
        "partial_exits":   poz.get("partial_exits", []),
    }

    kapatilanlar = closed.get("kapatilan_pozisyonlar", [])  # CANONICAL KEY
    kapatilanlar.append(kapali_poz)
    closed["kapatilan_pozisyonlar"] = kapatilanlar
    closed["son_guncelleme"]        = datetime.now().isoformat()

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
        "reason": f"Swing çıkış — {neden}. P/L: {pnl:+.1f}% ({tutulan_gun} gün)",
    }

    with open(REPO_ROOT / "data" / "transactions.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","action","symbol","shares","price","total","reason"])
        writer.writerow(tx_row)

    # Observability kaydı — canonical alanlarla
    try:
        import sys as _s
        _s.path.insert(0, str(REPO_ROOT / "agent"))
        from observability import log_trade
        log_trade(
            action="SELL", portfoy="swing", sembol=sym,
            shares=float(adet), price=float(cikis_fiyat),
            total=float(adet * cikis_fiyat),
            reason=f"Swing çıkış — {neden}. P/L: {pnl:+.1f}%",
        )
    except Exception as _e:
        print(f"[swing_manager] observability log_trade atlandı: {_e}")

    icon = "✅" if pnl > 0 else "❌"
    print(f"[Swing] {icon} {sym} kapatıldı: {neden} | P/L: {pnl:+.1f}% | {tutulan_gun}g")

    # 27 Nis 2026: Gruba satış bildirimi (memory kuralı: alım/satım gruba gider)
    neden_aciklama = {
        "STOP": "Stop-loss tetiklendi",
        "HEDEF": "Hedef fiyat ulaşıldı",
        "SURE": f"Maksimum süre doldu ({tutulan_gun} gün)",
    }.get(neden, neden)
    pnl_isaret = "+" if pnl >= 0 else ""
    detay = (
        f"<b>SWING ÇIKIŞ</b>\n"
        f"Adet: {adet}\n"
        f"Giriş: ${giris:.2f} → Çıkış: ${cikis_fiyat:.2f}\n"
        f"P/L: <b>{pnl_isaret}{pnl:.2f}%</b> ({sonuc})\n"
        f"Tutulan: {tutulan_gun} gün\n"
        f"Sebep: {neden_aciklama}\n"
        f"Tahsil: ${adet * cikis_fiyat:,.0f}"
    )
    action_type = "STOP" if neden == "STOP" else ("KAR_AL" if neden == "HEDEF" else "SATIŞ")
    _swing_notify_group(action_type, sym, cikis_fiyat, detay)


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

    pozlar    = active.get("aktif_pozisyonlar", [])
    kapalilar = closed.get("kapatilan_pozisyonlar", [])  # CANONICAL

    lines = ["📊 SWING DURUMU\n"]

    # Aktif pozisyonlar
    if pozlar:
        lines.append(f"Aktif ({len(pozlar)}/{SWING_MAX_POSITIONS}):")
        for p in pozlar:
            sym   = p["sembol"]
            pnl   = p.get("kar_zarar_yuzde", p.get("pnl_pct", 0))  # canonical, fallback eski
            price = p.get("guncel_fiyat", 0)
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
        # canonical: kar_zarar_yuzde, fallback eski: pnl_pct
        kazanc = sum(1 for k in son5 if (k.get("kar_zarar_yuzde", k.get("pnl_pct", 0)) or 0) > 0)
        pnls   = [(k.get("kar_zarar_yuzde", k.get("pnl_pct", 0)) or 0) for k in son5]
        avg    = sum(pnls) / len(pnls) if pnls else 0
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
        "max_kapasite":  SWING_MAX_POSITIONS,
        "bos_slot":      SWING_MAX_POSITIONS - kapasite,
        "rapor":         get_swing_report(),
    }
