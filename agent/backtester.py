#!/usr/bin/env python3
"""
Finzora Agent — Backtesting Motoru
=====================================
Mevcut veya önerilen kural değişikliklerini geçmiş trade verisiyle test eder.

ÖNEMLİ SINIRLAR:
  - Sadece closed.json'daki gerçek trade geçmişi kullanılır
  - FMP historical data ile basit simülasyon
  - Karmaşık Monte Carlo değil, parametrik test
  - Sonuç "öneri" niteliğinde — otomatik uygulama için 14 gün dry-run zorunlu

Test Edilebilir Parametreler:
  - RSI eşikleri (K-11 katmanları)
  - Stop-loss yüzdesi
  - ATR katsayısı
  - Holding period limiti
  - VIX eşikleri (K-13)
"""

import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import pytz

REPO_ROOT = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ     = pytz.timezone("Europe/Istanbul")
FMP_KEY   = os.environ.get("FMP_API_KEY", "")
FMP_BASE  = "https://financialmodelingprep.com/stable"


def fmp_get(endpoint, params=None):
    p = params or {}
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=12)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return []


# ── 1. Mevcut Kural Performansı ───────────────────────────────────────────────

def test_current_rules() -> dict:
    """
    Mevcut K-kurallarını closed.json'daki trade'lerle değerlendirir.
    Hangi kural tetiklendi, sonuç ne oldu?
    """
    path = REPO_ROOT / "data" / "swing" / "closed.json"
    if not path.exists():
        return {"hata": "closed.json bulunamadı"}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    trades = data.get("kapali_pozisyonlar", data.get("closed_positions", []))
    if not trades:
        return {"hata": "Kapanmış trade yok"}

    # Kural bazlı analiz
    rule_results = defaultdict(lambda: {"tetik": 0, "kazan": 0, "kayip": 0, "pnl_toplam": 0.0})

    for t in trades:
        exit_reason = (t.get("cikis_nedeni") or t.get("exit_reason", "")).lower()
        pnl = float(t.get("pnl_yuzde") or t.get("pnl_pct") or 0)

        # Hangi kural tetikledi?
        rules_triggered = []
        if "stop" in exit_reason:
            rules_triggered.append("stop_loss")
        if "k-11" in exit_reason or "kar al" in exit_reason or "profit" in exit_reason:
            rules_triggered.append("K-11")
        if "k-05" in exit_reason or "earnings" in exit_reason:
            rules_triggered.append("K-05")
        if "k-13" in exit_reason or "vix" in exit_reason:
            rules_triggered.append("K-13")
        if not rules_triggered:
            rules_triggered.append("manuel")

        for rule in rules_triggered:
            rule_results[rule]["tetik"] += 1
            rule_results[rule]["pnl_toplam"] += pnl
            if pnl > 0:
                rule_results[rule]["kazan"] += 1
            else:
                rule_results[rule]["kayip"] += 1

    # Özet
    summary = {}
    for rule, data in rule_results.items():
        total = data["tetik"]
        summary[rule] = {
            "tetiklenme":  total,
            "win_rate":    round(data["kazan"] / total * 100, 1) if total > 0 else 0,
            "ort_pnl":     round(data["pnl_toplam"] / total, 2) if total > 0 else 0,
            "toplam_pnl":  round(data["pnl_toplam"], 2),
        }

    return {
        "toplam_trade": len(trades),
        "kural_performansi": summary,
        "test_tarihi": datetime.now(TR_TZ).strftime("%Y-%m-%d"),
    }


# ── 2. Parametre Değişikliği Testi ────────────────────────────────────────────

def test_rsi_threshold(
    closed_trades: list,
    current_threshold: int = 70,
    new_threshold: int = 75
) -> dict:
    """
    RSI eşiğini değiştirince P/L nasıl değişirdi?
    Basit simülasyon: Eşik değişince daha fazla/az trade tutulurdu.
    """
    if not closed_trades:
        return {"hata": "Trade verisi yok"}

    # Mevcut kuralda erken çıkılan trade'ler (RSI 70'te çıkıldı)
    early_exits = []
    normal_exits = []

    for t in closed_trades:
        exit_reason = (t.get("cikis_nedeni") or t.get("exit_reason", "")).lower()
        pnl = float(t.get("pnl_yuzde") or t.get("pnl_pct") or 0)
        hold_days = int(t.get("tutma_suresi") or t.get("hold_days") or 0)

        if "k-11" in exit_reason or "rsi" in exit_reason:
            early_exits.append({"pnl": pnl, "hold": hold_days})
        else:
            normal_exits.append({"pnl": pnl, "hold": hold_days})

    if not early_exits:
        return {
            "mesaj": f"K-11 ile çıkılan trade bulunamadı — RSI eşiği testi anlamlı değil",
            "tavsiye": "Yeterli trade geçmişi oluştuğunda tekrar test et"
        }

    current_avg = sum(t["pnl"] for t in early_exits) / len(early_exits)

    # Yeni eşikle tahmini: Eşik yükseldikçe daha az erken çıkılır
    # Trade'lerin ortalama %2 daha fazla tutulacağı varsayımı (sezgisel)
    estimate_improvement = (new_threshold - current_threshold) * 0.15
    estimated_new_avg    = current_avg + estimate_improvement

    return {
        "mevcut_esik":    current_threshold,
        "yeni_esik":      new_threshold,
        "k11_trade_sayisi": len(early_exits),
        "mevcut_ort_pnl": round(current_avg, 2),
        "tahmini_yeni_pnl": round(estimated_new_avg, 2),
        "tahmini_fark":   round(estimate_improvement, 2),
        "guven":          "DÜŞÜK — N=" + str(len(early_exits)) + ", sezgisel tahmin",
        "backtest_notu":  "Gerçek backtest için FMP historical data ile doğrula"
    }


def test_stop_threshold(
    closed_trades: list,
    current_stop: float = 8.0,
    new_stop: float = 6.0
) -> dict:
    """
    Stop-loss eşiğini değiştirince kaç trade kurtarılırdı?
    """
    if not closed_trades:
        return {"hata": "Trade verisi yok"}

    stop_trades = [
        t for t in closed_trades
        if "stop" in (t.get("cikis_nedeni") or t.get("exit_reason", "")).lower()
    ]

    if not stop_trades:
        return {"mesaj": "Stop ile kapanan trade yok"}

    # Daha sıkı stop: Bazı trade'ler daha erken kesilir
    # Daha geniş stop: Bazı trade'ler toparlar
    avg_stop_loss = sum(
        float(t.get("pnl_yuzde") or t.get("pnl_pct") or 0)
        for t in stop_trades
    ) / len(stop_trades)

    # Tahmin: Sıkı stop daha küçük kayıplar ama daha fazla erken çıkış
    estimated_avg = avg_stop_loss * (new_stop / current_stop)

    return {
        "mevcut_stop":    f"%{current_stop}",
        "yeni_stop":      f"%{new_stop}",
        "stop_trade_sayisi": len(stop_trades),
        "mevcut_ort_kayip": round(avg_stop_loss, 2),
        "tahmini_yeni_kayip": round(estimated_avg, 2),
        "guven":          "ORTA — gerçek stop seviyelerine bakılamadı",
        "backtest_notu":  "ATR bazlı dinamik stop daha anlamlı olabilir"
    }


# ── 3. Historical Validation ──────────────────────────────────────────────────

def validate_with_historical(
    symbol: str,
    entry_date: str,
    exit_date: str,
    entry_price: float,
    rule_change: str
) -> dict:
    """
    Belirli bir trade için alternatif kural senaryosunu test eder.
    FMP historical data kullanır.
    """
    try:
        hist = fmp_get(
            "historical-price-eod/full",
            {"symbol": symbol}
        )
        if not hist or not isinstance(hist, list):
            return {"hata": "Historical data alınamadı"}

        # Tarih aralığını filtrele
        price_map = {d["date"]: d for d in hist}

        entry  = price_map.get(entry_date)
        exit_p = price_map.get(exit_date)

        if not entry or not exit_p:
            return {"hata": f"Tarih bulunamadı: {entry_date} veya {exit_date}"}

        actual_return = (exit_p["close"] - entry["close"]) / entry["close"] * 100

        return {
            "sembol":       symbol,
            "giriş_fiyat":  entry["close"],
            "çıkış_fiyat":  exit_p["close"],
            "gerçek_getiri": round(actual_return, 2),
            "kural_degişikliği": rule_change,
        }

    except Exception as e:
        return {"hata": str(e)}


# ── 4. Backtest Özeti ─────────────────────────────────────────────────────────

def run_full_backtest() -> dict:
    """
    Tüm backtest analizini çalıştırır.
    Sonuç Claude'a gönderilir, öneri üretir.
    """
    print("[Backtest] Çalıştırılıyor...")

    path = REPO_ROOT / "data" / "swing" / "closed.json"
    if not path.exists():
        return {"hata": "closed.json bulunamadı"}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    trades = data.get("kapali_pozisyonlar", data.get("closed_positions", []))

    results = {
        "test_tarihi":      datetime.now(TR_TZ).strftime("%Y-%m-%d"),
        "toplam_trade":     len(trades),
        "kural_performansi": test_current_rules(),
        "rsi_testi":        test_rsi_threshold(trades, 70, 75),
        "stop_testi":       test_stop_threshold(trades, 8.0, 6.0),
    }

    # Sonucu kaydet
    out_path = MEMORY_DIR / "backtest_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[Backtest] Tamamlandı: {len(trades)} trade analiz edildi.")
    return results


def format_backtest_for_claude(results: dict) -> str:
    """Backtest sonuçlarını Claude context'i için formatlar."""
    lines = ["=== BACKTEST SONUÇLARI ===\n"]

    lines.append(f"Toplam trade: {results.get('toplam_trade', 0)}")
    lines.append(f"Test tarihi: {results.get('test_tarihi', '')}\n")

    kp = results.get("kural_performansi", {}).get("kural_performansi", {})
    if kp:
        lines.append("--- KURAL PERFORMANSI ---")
        for rule, data in kp.items():
            lines.append(
                f"  {rule}: {data['tetiklenme']} kez | "
                f"Win %{data['win_rate']} | Ort P/L %{data['ort_pnl']}"
            )
        lines.append("")

    rsi = results.get("rsi_testi", {})
    if "tahmini_fark" in rsi:
        lines.append("--- RSI EŞİĞİ TESTİ (70 → 75) ---")
        lines.append(f"  Mevcut ort P/L: %{rsi.get('mevcut_ort_pnl', 0)}")
        lines.append(f"  Tahmini yeni P/L: %{rsi.get('tahmini_yeni_pnl', 0)}")
        lines.append(f"  Güven: {rsi.get('guven', '')}")
        lines.append("")

    stop = results.get("stop_testi", {})
    if "tahmini_yeni_kayip" in stop:
        lines.append("--- STOP TESTİ (%8 → %6) ---")
        lines.append(f"  Mevcut ort kayıp: %{stop.get('mevcut_ort_kayip', 0)}")
        lines.append(f"  Tahmini yeni: %{stop.get('tahmini_yeni_kayip', 0)}")
        lines.append(f"  Güven: {stop.get('guven', '')}")

    return "\n".join(lines)
