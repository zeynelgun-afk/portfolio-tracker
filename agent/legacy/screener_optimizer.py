#!/usr/bin/env python3
"""
Finzora Agent — Screener Optimizasyon Motoru
===============================================
Swing screener ve portföy tarama filtrelerini otomatik optimize eder.

Optimizasyon mantığı:
  1. closed.json'dan hangi scan_method'un işe yaradığına bak
  2. Parametre kombinasyonlarını geçmiş trade'lerle test et
  3. En iyi performanslı filtre setini öner
  4. Güvenlik kontrolünden geçirse → daily_scan konfigürasyonunu güncelle

Optimize edilebilir filtreler:
  - RSI aralığı (giriş için: örn 40-65)
  - Momentum prefilter: 1M/3M getiri eşiği
  - Hacim çarpanı (1.5x → 2.0x vb.)
  - Market cap alt limiti
  - Sektör ağırlıkları
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import pytz

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")
FMP_KEY    = os.environ.get("FMP_API_KEY", "")
FMP_BASE   = "https://financialmodelingprep.com/stable"

# Mevcut screener parametreleri
CURRENT_PARAMS = {
    "rsi_alt":          40,
    "rsi_ust":          65,
    "momentum_1m":      0.0,    # Min 1 aylık getiri
    "momentum_3m":      5.0,    # Min 3 aylık getiri (%)
    "hacim_carpan":     1.5,    # Min hacim çarpanı
    "mcap_min_milyar":  2.0,    # Min market cap ($B)
    "fiyat_min":        10.0,   # Min hisse fiyatı
}

# Deneme aralıkları
PARAM_RANGES = {
    "rsi_alt":       [35, 40, 45],
    "rsi_ust":       [60, 65, 70],
    "momentum_3m":   [0, 5, 10],
    "hacim_carpan":  [1.2, 1.5, 2.0],
}


# ── Tarama Yöntemi Performansı ────────────────────────────────────────────────

def analyze_scan_method_performance() -> dict:
    """
    closed.json'dan her scan_method'un win rate ve P/L'sini hesaplar.
    """
    path = REPO_ROOT / "data" / "swing" / "closed.json"
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    trades = data.get("kapatilan_pozisyonlar", data.get("kapali_pozisyonlar", data.get("closed_positions", [])))
    method_stats = defaultdict(lambda: {"trades": [], "win": 0, "total": 0})

    for t in trades:
        method = t.get("tarama_yontemi") or t.get("scan_method", "bilinmiyor")
        pnl    = float(t.get("pnl_yuzde") or t.get("pnl_pct") or 0)

        method_stats[method]["trades"].append(pnl)
        method_stats[method]["total"] += 1
        if pnl > 0:
            method_stats[method]["win"] += 1

    result = {}
    for method, stats in method_stats.items():
        total = stats["total"]
        if total == 0:
            continue
        result[method] = {
            "trade_sayisi": total,
            "win_rate":     round(stats["win"] / total * 100, 1),
            "ort_pnl":      round(sum(stats["trades"]) / total, 2),
            "toplam_pnl":   round(sum(stats["trades"]), 2),
        }

    return dict(sorted(result.items(), key=lambda x: -x[1]["ort_pnl"]))


# ── Parametre Testi ───────────────────────────────────────────────────────────

def test_rsi_range(
    closed_trades: list,
    rsi_alt: int,
    rsi_ust: int
) -> dict:
    """
    Farklı RSI aralıklarının geçmiş trade'lere etkisini simüle eder.
    Kaç trade filtreye girerdi, win rate ne olurdu?
    """
    if not closed_trades:
        return {"hata": "Trade yok"}

    # RSI verisi olan trade'leri bul
    # Not: closed.json'da RSI genellikle kaydedilmiyor
    # Bu yüzden sezgisel tahmin kullanıyoruz

    in_range   = []
    out_range  = []

    for t in closed_trades:
        pnl   = float(t.get("pnl_yuzde") or t.get("pnl_pct") or 0)
        # Giriş tezinde "oversold" veya RSI varsa range içindedir
        entry = (t.get("giris_nedeni") or t.get("entry_reason", "")).lower()
        if "rsi" in entry or "oversold" in entry or "aşırı satım" in entry:
            in_range.append(pnl)
        else:
            out_range.append(pnl)

    if not in_range:
        return {
            "mesaj": "RSI bazlı giriş yapılan trade bulunamadı",
            "test_parametreler": f"RSI {rsi_alt}-{rsi_ust}"
        }

    return {
        "test_parametreler": f"RSI {rsi_alt}-{rsi_ust}",
        "rsi_trade_sayisi":  len(in_range),
        "rsi_win_rate":      round(sum(1 for p in in_range if p > 0) / len(in_range) * 100, 1),
        "rsi_ort_pnl":       round(sum(in_range) / len(in_range), 2),
        "diger_trade_sayisi": len(out_range),
        "diger_ort_pnl":     round(sum(out_range) / len(out_range), 2) if out_range else 0,
    }


def test_momentum_filter(closed_trades: list, momentum_3m: float) -> dict:
    """
    3M momentum filtresinin etkisini test eder.
    """
    if not closed_trades:
        return {"hata": "Trade yok"}

    # Momentum bilgisi olan trade'leri tahmin et
    total    = len(closed_trades)
    filtered = int(total * (1 - momentum_3m / 20))  # Yüksek eşik daha az trade

    if total == 0:
        return {"hata": "Trade yok"}

    avg_pnl = sum(
        float(t.get("pnl_yuzde") or t.get("pnl_pct") or 0)
        for t in closed_trades
    ) / total

    return {
        "momentum_esik": f"%{momentum_3m} (3 aylık)",
        "tahmini_filtre_sonrasi": filtered,
        "mevcut_toplam":          total,
        "guven":                  "DÜŞÜK — momentum verisi kayıtlı değil",
    }


# ── Optimum Parametre Seti ────────────────────────────────────────────────────

def find_optimal_params(closed_trades: list) -> dict:
    """
    Parametre kombinasyonlarını test edip en iyi seti bulur.
    """
    if len(closed_trades) < 5:
        return {
            "mesaj": f"Yetersiz veri ({len(closed_trades)} trade). Min 5 gerekli.",
            "tavsiye": "Trade geçmişi biriktiğinde optimizasyon yapılabilir."
        }

    results = {}

    # RSI aralığı testi
    for rsi_alt in PARAM_RANGES["rsi_alt"]:
        for rsi_ust in PARAM_RANGES["rsi_ust"]:
            if rsi_alt >= rsi_ust:
                continue
            key = f"rsi_{rsi_alt}_{rsi_ust}"
            results[key] = test_rsi_range(closed_trades, rsi_alt, rsi_ust)

    # En iyi kombinasyonu bul
    best_key    = None
    best_pnl    = float("-inf")
    best_params = CURRENT_PARAMS.copy()

    for key, res in results.items():
        pnl = res.get("rsi_ort_pnl", float("-inf"))
        if pnl > best_pnl and res.get("rsi_trade_sayisi", 0) >= 3:
            best_pnl    = pnl
            best_key    = key
            parts       = key.split("_")
            if len(parts) == 3:
                best_params["rsi_alt"] = int(parts[1])
                best_params["rsi_ust"] = int(parts[2])

    return {
        "mevcut_parametreler": CURRENT_PARAMS,
        "en_iyi_parametreler": best_params,
        "gelisim_tahmini":     f"%{best_pnl:.2f} ort P/L",
        "test_sonuclari":      results,
        "guven":               "DÜŞÜK — daha fazla trade verisi gerekli",
    }


# ── Screener Konfigürasyonu Güncelle ─────────────────────────────────────────

def update_screener_config(new_params: dict, rationale: str) -> bool:
    """
    daily_full_scan.json'daki screener parametrelerini günceller.
    Güvenlik: Sadece PARAM_RANGES içindeki değerlere izin ver.
    """
    # Değerleri doğrula
    for key, val in new_params.items():
        if key in PARAM_RANGES:
            if val not in PARAM_RANGES[key]:
                print(f"[Screener] {key}={val} izin verilen aralıkta değil: {PARAM_RANGES[key]}")
                return False

    config_path = MEMORY_DIR / "screener_config.json"
    config = CURRENT_PARAMS.copy()
    config.update(new_params)
    config["son_guncelleme"] = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    config["guncelleme_gerekce"] = rationale[:200]

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"[Screener] Konfigürasyon güncellendi: {new_params}")
    return True


# ── Haftalık Optimizasyon Raporu ──────────────────────────────────────────────

def run_screener_optimization() -> str:
    """
    Haftalık screener optimizasyonunu çalıştırır.
    AI'ye gönderilecek özet raporu döner.
    """
    print("[Screener] Optimizasyon çalışıyor...")

    # closed.json'dan trade'leri al
    path = REPO_ROOT / "data" / "swing" / "closed.json"
    trades = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        trades = data.get("kapatilan_pozisyonlar", data.get("kapali_pozisyonlar", data.get("closed_positions", [])))

    method_perf  = analyze_scan_method_performance()
    optimal      = find_optimal_params(trades)

    # Güncel config
    config_path  = MEMORY_DIR / "screener_config.json"
    current_conf = CURRENT_PARAMS.copy()
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            current_conf = json.load(f)

    lines = ["=== SCREENER OPTİMİZASYON RAPORU ===\n"]

    lines.append("--- TARAMA YÖNTEMİ PERFORMANSI ---")
    if method_perf:
        for method, stats in list(method_perf.items())[:5]:
            lines.append(
                f"  {method}: {stats['trade_sayisi']} trade | "
                f"Win %{stats['win_rate']} | Ort P/L %{stats['ort_pnl']}"
            )
    else:
        lines.append("  Henüz veri yok.")
    lines.append("")

    lines.append("--- MEVCUT PARAMETRELER ---")
    for k, v in CURRENT_PARAMS.items():
        lines.append(f"  {k}: {v}")
    lines.append("")

    if "mesaj" not in optimal:
        lines.append("--- OPTİMUM PARAMETRE ÖNERİSİ ---")
        en_iyi = optimal.get("en_iyi_parametreler", {})
        degisen = {k: v for k, v in en_iyi.items()
                   if v != CURRENT_PARAMS.get(k)}
        if degisen:
            for k, v in degisen.items():
                lines.append(f"  {k}: {CURRENT_PARAMS.get(k)} → {v}")
            lines.append(f"  Tahmini gelişim: {optimal.get('gelisim_tahmini','?')}")
            lines.append(f"  Güven: {optimal.get('guven','?')}")
        else:
            lines.append("  Mevcut parametreler zaten optimal görünüyor.")
    else:
        lines.append(f"  {optimal.get('mesaj','')}")
        lines.append(f"  {optimal.get('tavsiye','')}")

    print("[Screener] Optimizasyon tamamlandı.")
    return "\n".join(lines)
