#!/usr/bin/env python3
"""
Finzora AI — Walk-Forward Backtest Otomasyonu (Katman 6)
=========================================================
K-kural parametre değişikliklerini geçmiş trade'lere uygular.
In-sample optimizasyon → out-of-sample validasyon döngüsü.
Overfitting'i önlemek için rolling window + LOOCV kullanır.

Kullanım:
  python3 scripts/walk_forward_backtest.py --rule K-ZAMAN --param zaman_limiti
  python3 scripts/walk_forward_backtest.py --rule K-STOP  --param stop_pct
  python3 scripts/walk_forward_backtest.py --full          # Tüm kurallar
  python3 scripts/walk_forward_backtest.py --report        # Son sonuçlar
"""

import json
import math
import argparse
import itertools
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE        = Path(__file__).parent.parent
CLOSED_FILE = BASE / "data" / "swing" / "closed.json"
RESULTS_FILE = BASE / "data" / "walkforward_results.json"


# ══════════════════════════════════════════════════════════════════════════════
# 1. VERİ YÜKLEME VE HAZIRLAMA
# ══════════════════════════════════════════════════════════════════════════════

def trades_yukle() -> list[dict]:
    with open(CLOSED_FILE, encoding="utf-8") as f:
        d = json.load(f)
    trades = d["kapatilan_pozisyonlar"]
    # Zaman sırasına göre sırala
    return sorted(trades, key=lambda t: t.get("giris_tarihi", ""))


def performans_hesapla(trades: list[dict]) -> dict:
    """Bir trade listesinin temel performans metriklerini hesaplar."""
    if not trades:
        return {"toplam": 0, "win_rate": 0, "ort_pnl": 0,
                "sharpe": 0, "max_drawdown": 0, "beklenti": 0}

    pnl_listesi = [t["kar_zarar_yuzde"] for t in trades]
    kazananlar  = [p for p in pnl_listesi if p > 0]
    kaybedenler = [p for p in pnl_listesi if p <= 0]

    ort_pnl = sum(pnl_listesi) / len(pnl_listesi)
    win_rate = len(kazananlar) / len(pnl_listesi)

    # Sharpe oranı (basit versiyon, risk-free=0)
    std = math.sqrt(sum((p - ort_pnl)**2 for p in pnl_listesi) / len(pnl_listesi)) if len(pnl_listesi) > 1 else 1
    sharpe = ort_pnl / std if std > 0 else 0

    # Max Drawdown
    kumulatif = 0
    zirve = 0
    max_dd = 0
    for p in pnl_listesi:
        kumulatif += p
        zirve = max(zirve, kumulatif)
        max_dd = min(max_dd, kumulatif - zirve)

    # Beklenti (Kelly benzeri)
    avg_kazanc = sum(kazananlar) / len(kazananlar) if kazananlar else 0
    avg_kayip  = abs(sum(kaybedenler) / len(kaybedenler)) if kaybedenler else 1
    beklenti   = (win_rate * avg_kazanc) - ((1 - win_rate) * avg_kayip)

    return {
        "toplam":       len(trades),
        "win_rate":     round(win_rate * 100, 1),
        "ort_pnl":      round(ort_pnl, 2),
        "sharpe":       round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "beklenti":     round(beklenti, 2),
        "toplam_pnl":   round(sum(pnl_listesi), 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. KURAL SİMÜLATÖRLERİ
# ══════════════════════════════════════════════════════════════════════════════

def simule_zaman_kurali(trades: list[dict], limit_gun: int) -> list[dict]:
    """
    Farklı zaman sınırlarında trade'lerin nasıl çıkacağını simüle eder.
    Limit günde zorla çıkış yapılır. Çıkış PnL'i o günkü fiyata göre
    tahmin edilir (lineer interpolasyon — gerçek fiyat olmadığında).
    """
    simule = []
    for t in trades:
        gun = t.get("tutulan_gun", 0)
        pnl = t.get("kar_zarar_yuzde", 0)

        if gun <= limit_gun:
            # Kural içinde — aynı çıkış
            simule.append({**t, "_simule": False})
        else:
            # Zorla limit_gun'da çıkış — lineer interpolasyon
            # Gerçek fiyat hareketini bilmediğimiz için muhafazakâr tahmin:
            # PnL = gerçek_pnl × (limit_gun / tutulan_gun)
            # Bu conservative (erken çıkış genelde daha az kazanır)
            tahmin_pnl = pnl * (limit_gun / gun) if gun > 0 else pnl
            simule_t = {
                **t,
                "kar_zarar_yuzde": round(tahmin_pnl, 2),
                "tutulan_gun":     limit_gun,
                "cikis_nedeni":    f"[SIM] {limit_gun}g zaman kuralı",
                "_simule": True,
                "_gercek_pnl": pnl,
            }
            simule.append(simule_t)
    return simule


def simule_stop_kurali(trades: list[dict], stop_pct: float) -> list[dict]:
    """
    Farklı stop yüzdelerinde çıkışları simüle eder.
    Gerçek stop tetiklenme noktasını bilmediğimiz için:
    - Mevcut çıkış < stop_pct ise → stop zaten çalıştı, değişmez
    - Mevcut çıkış > -stop_pct ise → stop çalışmadı, değişmez
    - Yeni stop daha sıkı ise → bazı trade'ler daha erken kesilir
    """
    simule = []
    for t in trades:
        pnl = t.get("kar_zarar_yuzde", 0)
        gercek_stop = -5.0  # Mevcut sistem %5 stop

        if pnl < 0 and pnl > -stop_pct:
            # Bu trade stop olmadı; yeni daha sıkı stop alsaydık?
            if stop_pct < abs(gercek_stop):
                # Daha sıkı stop → bu trade stop olurdu
                simule.append({
                    **t,
                    "kar_zarar_yuzde": -stop_pct,
                    "cikis_nedeni":    f"[SIM] {stop_pct}% sıkı stop",
                    "_simule": True,
                    "_gercek_pnl": pnl,
                })
                continue

        if pnl < -stop_pct:
            # Mevcut stop bu seviyeyi aşmış — yeni stop daha gevşek
            if stop_pct > abs(gercek_stop):
                # Daha gevşek stop → daha büyük zarar
                simule.append({
                    **t,
                    "kar_zarar_yuzde": -stop_pct,
                    "_simule": True,
                    "_gercek_pnl": pnl,
                })
                continue

        simule.append({**t, "_simule": False})
    return simule


def simule_evren_filtresi(trades: list[dict],
                           yasak_liste: list[str]) -> list[dict]:
    """
    Belirli hisselerin swing evreninde olmadığı durumu simüle eder.
    Bu trade'ler hiç yapılmasaydı ne olurdu?
    """
    yapilan    = [t for t in trades if t["sembol"] not in yasak_liste]
    yapilmayan = [t for t in trades if t["sembol"] in yasak_liste]
    return yapilan, yapilmayan


def simule_k_atr(trades: list[dict], atr_carpan: float = 2.0) -> list[dict]:
    """
    Stop mesafesi ATR bazlı olsaydı nasıl olurdu?
    Yeterli ATR verisi olmadığı için makul bir tahmin kullanır:
    ATR ≈ fiyatın %2-3'ü (tipik swing hissesi için)
    """
    simule = []
    for t in trades:
        pnl = t.get("kar_zarar_yuzde", 0)
        gun = t.get("tutulan_gun", 0)

        # ATR stop mesafesi ≈ fiyatın %{atr_carpan*1.5}%'i (konservatif)
        atr_stop_pct = atr_carpan * 1.5

        if pnl < -atr_stop_pct:
            # ATR stop bu trade'i daha erken keserdi
            simule.append({
                **t,
                "kar_zarar_yuzde": -atr_stop_pct,
                "_simule": True,
                "_gercek_pnl": pnl,
            })
        else:
            simule.append({**t, "_simule": False})
    return simule


# ══════════════════════════════════════════════════════════════════════════════
# 3. WALK-FORWARD DÖNGÜSÜ
# ══════════════════════════════════════════════════════════════════════════════

def walk_forward(trades: list[dict], simule_fn, parametreler: list,
                 pencere: int = 8, adim: int = 3) -> dict:
    """
    Rolling walk-forward analizi.

    Döngü:
      1. İlk `pencere` trade → in-sample (optimizasyon)
      2. Sonraki `adim` trade → out-of-sample (test)
      3. Pencereyi `adim` kadar ilerlet
      4. Tekrarla

    Parametreler: Test edilecek değerler listesi
    """
    toplam = len(trades)
    sonuclar = []

    pos = 0
    pencere_no = 0

    while pos + pencere + adim <= toplam:
        pencere_no += 1
        train = trades[pos: pos + pencere]
        test  = trades[pos + pencere: pos + pencere + adim]

        # In-sample: En iyi parametreyi bul
        en_iyi_param  = None
        en_iyi_sharpe = -999
        in_sample_sonuclar = {}

        for param in parametreler:
            simule_train = simule_fn(train, param)
            perf = performans_hesapla(simule_train)
            in_sample_sonuclar[param] = perf
            if perf["sharpe"] > en_iyi_sharpe:
                en_iyi_sharpe = perf["sharpe"]
                en_iyi_param  = param

        # Out-of-sample: En iyi parametreyi test et
        simule_test = simule_fn(test, en_iyi_param)
        oos_perf    = performans_hesapla(simule_test)

        # Baz (mevcut kural) ile karşılaştır
        baz_test = performans_hesapla(test)

        sonuclar.append({
            "pencere":          pencere_no,
            "train_aralik":     f"{train[0]['giris_tarihi']} → {train[-1]['giris_tarihi']}",
            "test_aralik":      f"{test[0]['giris_tarihi']} → {test[-1]['giris_tarihi']}",
            "en_iyi_param":     en_iyi_param,
            "in_sample_sharpe": round(en_iyi_sharpe, 2),
            "oos_sharpe":       oos_perf["sharpe"],
            "oos_win_rate":     oos_perf["win_rate"],
            "oos_ort_pnl":      oos_perf["ort_pnl"],
            "baz_sharpe":       baz_test["sharpe"],
            "baz_win_rate":     baz_test["win_rate"],
            "baz_ort_pnl":      baz_test["ort_pnl"],
            "gelisme":          round(oos_perf["ort_pnl"] - baz_test["ort_pnl"], 2),
        })

        pos += adim

    return {
        "pencere_sayisi": pencere_no,
        "pencereler":     sonuclar,
        "ortalama_gelisme": round(
            sum(s["gelisme"] for s in sonuclar) / len(sonuclar), 2
        ) if sonuclar else 0,
        "oos_tutarlilik": sum(1 for s in sonuclar if s["oos_sharpe"] > s["baz_sharpe"]) / len(sonuclar) * 100 if sonuclar else 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. LOOCV (Küçük Dataset için)
# ══════════════════════════════════════════════════════════════════════════════

def loocv_test(trades: list[dict], simule_fn, parametreler: list) -> dict:
    """
    Leave-One-Out Cross Validation.
    22 trade gibi küçük dataset'lerde walk-forward yetersiz kalır.
    Her seferinde 1 trade dışarı bırakılır, geri kalanıyla optimize edilir,
    dışarıdaki trade'e uygulanır.
    """
    tum_sonuclar = defaultdict(list)
    oos_sonuclar = []

    for i, test_trade in enumerate(trades):
        train = [t for j, t in enumerate(trades) if j != i]

        # En iyi parametreyi bul (train üzerinde)
        en_iyi_param  = None
        en_iyi_sharpe = -999
        for param in parametreler:
            simule_train = simule_fn(train, param)
            perf = performans_hesapla(simule_train)
            if perf["sharpe"] > en_iyi_sharpe:
                en_iyi_sharpe = perf["sharpe"]
                en_iyi_param  = param

        # Test trade'e uygula
        simule_test = simule_fn([test_trade], en_iyi_param)
        gercek_pnl  = test_trade["kar_zarar_yuzde"]
        simule_pnl  = simule_test[0]["kar_zarar_yuzde"]

        oos_sonuclar.append({
            "trade":       test_trade.get("id", ""),
            "sembol":      test_trade["sembol"],
            "gercek_pnl":  gercek_pnl,
            "simule_pnl":  simule_pnl,
            "en_iyi_param": en_iyi_param,
            "fark":        round(simule_pnl - gercek_pnl, 2),
        })

    # Genel istatistik
    iyilesen = [s for s in oos_sonuclar if s["fark"] > 0]
    kotulesen = [s for s in oos_sonuclar if s["fark"] < 0]
    ort_fark = sum(s["fark"] for s in oos_sonuclar) / len(oos_sonuclar)

    # En sık seçilen parametreyi bul
    param_sayisi = defaultdict(int)
    for s in oos_sonuclar:
        param_sayisi[s["en_iyi_param"]] += 1
    en_cok_secilen = max(param_sayisi, key=param_sayisi.get)

    return {
        "yontem":          "LOOCV",
        "toplam_fold":     len(trades),
        "iyilesen_trade":  len(iyilesen),
        "kotulesen_trade": len(kotulesen),
        "ort_fark":        round(ort_fark, 2),
        "en_cok_param":    en_cok_secilen,
        "param_frekans":   dict(param_sayisi),
        "detay":           oos_sonuclar,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. KURAL BAZLI TEST SETLERİ
# ══════════════════════════════════════════════════════════════════════════════

def test_zaman_kurali(trades: list[dict]) -> dict:
    """K-ZAMAN: Farklı gün limitlerini test eder."""
    print("  ⏱️  K-ZAMAN parametresi test ediliyor...")
    parametreler = [7, 10, 12, 15, 18, 21]

    # Baz performans (mevcut sistem)
    baz = performans_hesapla(trades)

    # Her parametre için tam simülasyon
    param_sonuclari = {}
    for p in parametreler:
        simule = simule_zaman_kurali(trades, p)
        param_sonuclari[p] = performans_hesapla(simule)

    # En iyi parametre (Sharpe'a göre)
    en_iyi = max(param_sonuclari, key=lambda p: param_sonuclari[p]["sharpe"])

    # LOOCV validasyonu
    loocv = loocv_test(trades, simule_zaman_kurali, parametreler)

    # Walk-forward (küçük dataset için 5+3 pencere)
    wf = walk_forward(trades, simule_zaman_kurali, parametreler,
                      pencere=10, adim=3)

    return {
        "kural":         "K-ZAMAN",
        "aciklama":      "Maksimum tutma süresi (gün)",
        "mevcut_deger":  15,
        "test_degerleri": parametreler,
        "baz_performans": baz,
        "param_sonuclari": {str(k): v for k, v in param_sonuclari.items()},
        "in_sample_en_iyi": en_iyi,
        "loocv":          loocv,
        "walk_forward":   wf,
        "oneri":          _oneri_olustur(
            mevcut=15, en_iyi=en_iyi,
            loocv_param=loocv["en_cok_param"],
            baz=baz, iyilesen=param_sonuclari[en_iyi]
        ),
    }


def test_stop_kurali(trades: list[dict]) -> dict:
    """K-STOP: Farklı stop yüzdelerini test eder."""
    print("  🛑  K-STOP parametresi test ediliyor...")
    parametreler = [3.5, 4.0, 5.0, 6.0, 7.0]

    baz = performans_hesapla(trades)
    param_sonuclari = {}
    for p in parametreler:
        simule = simule_stop_kurali(trades, p)
        param_sonuclari[p] = performans_hesapla(simule)

    en_iyi = max(param_sonuclari, key=lambda p: param_sonuclari[p]["sharpe"])
    loocv  = loocv_test(trades, simule_stop_kurali, parametreler)
    wf     = walk_forward(trades, simule_stop_kurali, parametreler,
                          pencere=10, adim=3)

    return {
        "kural":          "K-STOP",
        "aciklama":       "Maksimum stop yüzdesi",
        "mevcut_deger":   5.0,
        "test_degerleri": parametreler,
        "baz_performans": baz,
        "param_sonuclari": {str(k): v for k, v in param_sonuclari.items()},
        "in_sample_en_iyi": en_iyi,
        "loocv":           loocv,
        "walk_forward":    wf,
        "oneri":           _oneri_olustur(
            mevcut=5.0, en_iyi=en_iyi,
            loocv_param=loocv["en_cok_param"],
            baz=baz, iyilesen=param_sonuclari[en_iyi]
        ),
    }


def test_evren_filtresi(trades: list[dict]) -> dict:
    """K-EVR: Yasak liste değişikliklerinin etkisini test eder."""
    print("  🏢  K-EVR yasak listesi test ediliyor...")

    MEVCUT_YASAK = {
        "VZ", "T", "TMUS", "DUK", "NEE", "SO",
        "DVA", "WMT", "TGT", "COST", "AMT"
    }

    yasak_trade = [t for t in trades if t["sembol"] in MEVCUT_YASAK]
    temiz_trade = [t for t in trades if t["sembol"] not in MEVCUT_YASAK]

    baz_tum    = performans_hesapla(trades)
    baz_temiz  = performans_hesapla(temiz_trade)
    yasak_perf = performans_hesapla(yasak_trade)

    gelisme = {
        "win_rate_farki": round(baz_temiz["win_rate"] - baz_tum["win_rate"], 1),
        "ort_pnl_farki":  round(baz_temiz["ort_pnl"] - baz_tum["ort_pnl"], 2),
        "sharpe_farki":   round(baz_temiz["sharpe"]   - baz_tum["sharpe"], 2),
    }

    return {
        "kural":           "K-EVR",
        "aciklama":        "Swing evreninden çıkarılan düşük beta hisseler",
        "yasaklanan_hisse_sayisi": len(MEVCUT_YASAK),
        "etkilenen_trade": len(yasak_trade),
        "tum_trade_perf":  baz_tum,
        "yasak_trade_perf": yasak_perf,
        "temiz_trade_perf": baz_temiz,
        "gelisme":         gelisme,
        "yasak_trade_listesi": [
            {"sembol": t["sembol"], "pnl": t["kar_zarar_yuzde"],
             "gun": t["tutulan_gun"], "sonuc": t["sonuc"]}
            for t in yasak_trade
        ],
        "oneri": (
            f"K-EVR etkili: Yasak liste uygulanırsa ort. PnL "
            f"{baz_temiz['ort_pnl']:+.1f}% (mevcut: {baz_tum['ort_pnl']:+.1f}%), "
            f"win rate %{baz_temiz['win_rate']:.0f} (mevcut: %{baz_tum['win_rate']:.0f}). "
            f"{'✅ Devam et' if gelisme['ort_pnl_farki'] > 0 else '⚠️ İncele'}."
        ),
    }


def _oneri_olustur(mevcut, en_iyi, loocv_param, baz, iyilesen) -> str:
    """Backtest bulgularına göre öneri metni üretir."""
    pnl_farki   = iyilesen["ort_pnl"] - baz["ort_pnl"]
    sharpe_farki = iyilesen["sharpe"] - baz["sharpe"]

    # İki yöntem aynı parametreye işaret ediyor mu?
    tutarli = (en_iyi == loocv_param)

    if abs(pnl_farki) < 0.5 and abs(sharpe_farki) < 0.1:
        karar = "Fark istatistiksel olarak önemsiz — MEVCUT değeri koru"
    elif not tutarli:
        karar = (f"IS en iyi={en_iyi}, LOOCV={loocv_param} — "
                 f"Yöntemler çelişiyor, MEVCUT değeri koru (overfitting riski)")
    elif pnl_farki > 1.0 and sharpe_farki > 0.2 and tutarli:
        karar = (f"Güçlü öneri: {en_iyi} kullan "
                 f"(PnL +{pnl_farki:.1f}%, Sharpe +{sharpe_farki:.2f}). "
                 f"Zeynel onayı gerektirir.")
    elif pnl_farki > 0:
        karar = (f"Zayıf öneri: {en_iyi} biraz daha iyi "
                 f"(PnL +{pnl_farki:.1f}%) ama fark küçük — izle")
    else:
        karar = f"Mevcut {mevcut} değeri optimal görünüyor"

    return karar


# ══════════════════════════════════════════════════════════════════════════════
# 6. ÖZET RAPOR
# ══════════════════════════════════════════════════════════════════════════════

def rapor_yazdir(sonuclar: dict):
    print(f"\n{'='*65}")
    print(f"  📊 WALK-FORWARD BACKTEST RAPORU")
    print(f"  {datetime.now().strftime('%d %B %Y')} | {sonuclar['toplam_trade']} trade")
    print(f"{'='*65}\n")

    # Baz performans
    baz = sonuclar.get("baz_performans", {})
    print(f"  🎯 BAZ PERFORMANS (mevcut sistem):")
    print(f"     Win Rate: %{baz.get('win_rate',0)} | "
          f"Ort. PnL: {baz.get('ort_pnl',0):+.1f}% | "
          f"Sharpe: {baz.get('sharpe',0):.2f} | "
          f"Max DD: {baz.get('max_drawdown',0):.1f}%")
    print(f"     Beklenti per trade: {baz.get('beklenti',0):+.2f}%\n")

    for kural_adi, kural_sonuc in sonuclar.get("kural_sonuclari", {}).items():
        print(f"  {'─'*60}")
        print(f"  📋 {kural_sonuc['kural']} — {kural_sonuc['aciklama']}")
        print(f"     Mevcut: {kural_sonuc.get('mevcut_deger', '—')}")

        # K-EVR özel format
        if kural_adi == "K-EVR":
            g = kural_sonuc.get("gelisme", {})
            temiz = kural_sonuc.get("temiz_trade_perf", {})
            yasak = kural_sonuc.get("yasak_trade_perf", {})
            print(f"\n     Yasak liste trade performansı:")
            print(f"       Win Rate: %{yasak.get('win_rate',0)} | "
                  f"Ort. PnL: {yasak.get('ort_pnl',0):+.1f}%")
            print(f"     Yasak liste çıkarılırsa:")
            print(f"       Win Rate: %{temiz.get('win_rate',0)} | "
                  f"Ort. PnL: {temiz.get('ort_pnl',0):+.1f}% | "
                  f"Sharpe: {temiz.get('sharpe',0):.2f}")
            print(f"     Gelişme: PnL {g.get('ort_pnl_farki',0):+.2f}% | "
                  f"WR {g.get('win_rate_farki',0):+.1f}% | "
                  f"Sharpe {g.get('sharpe_farki',0):+.2f}")
        else:
            # Walk-forward parametreler
            print(f"\n     In-Sample en iyi parametre: {kural_sonuc.get('in_sample_en_iyi')}")
            loocv = kural_sonuc.get("loocv", {})
            print(f"     LOOCV en çok seçilen:       {loocv.get('en_cok_param')}")
            print(f"     LOOCV iyileşen fold: "
                  f"{loocv.get('iyilesen_trade',0)}/{loocv.get('toplam_fold',0)}")
            wf = kural_sonuc.get("walk_forward", {})
            if wf.get("pencere_sayisi", 0) > 0:
                print(f"     Walk-forward tutarlılık: "
                      f"%{wf.get('oos_tutarlilik',0):.0f}")
                print(f"     Walk-forward ort. gelişme: "
                      f"{wf.get('ortalama_gelisme',0):+.2f}%/trade")

        print(f"\n     💡 ÖNERİ: {kural_sonuc.get('oneri', '—')}")

    print(f"\n{'='*65}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 7. CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — Walk-Forward Backtest"
    )
    parser.add_argument("--full",   action="store_true",
                        help="Tüm kuralları test et")
    parser.add_argument("--rule",   type=str,
                        help="Belirli kural: K-ZAMAN / K-STOP / K-EVR")
    parser.add_argument("--report", action="store_true",
                        help="Son sonuçları göster")
    args = parser.parse_args()

    if args.report:
        if RESULTS_FILE.exists():
            with open(RESULTS_FILE) as f:
                rapor_yazdir(json.load(f))
        else:
            print("Sonuç dosyası yok — önce --full çalıştır")
        return

    trades = trades_yukle()
    baz    = performans_hesapla(trades)

    kural_sonuclari = {}

    if args.full or args.rule in ("K-ZAMAN", None):
        kural_sonuclari["K-ZAMAN"] = test_zaman_kurali(trades)

    if args.full or args.rule == "K-STOP":
        kural_sonuclari["K-STOP"] = test_stop_kurali(trades)

    if args.full or args.rule == "K-EVR":
        kural_sonuclari["K-EVR"] = test_evren_filtresi(trades)

    output = {
        "olusturulma":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "toplam_trade":   len(trades),
        "baz_performans": baz,
        "kural_sonuclari": kural_sonuclari,
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    rapor_yazdir(output)
    print(f"✅ Sonuçlar kaydedildi: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
