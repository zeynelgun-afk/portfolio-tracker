#!/usr/bin/env python3
"""
Finzora Agent — Tahmin Loglama Sistemi
========================================
ATLAS'ın en kritik özelliği: Her öneri gerçek sonuca karşı skorlanır.
Biz şu ana kadar bunu yapmıyorduk — kararlar havaya karışıyordu.

Akış:
  1. Agent bir öneri yapar (BUY/SELL/HOLD/ROTASYON)
  2. Öneri prediction_log.json'a kaydedilir
  3. 5, 10, 14 gün sonra FMP'den gerçek fiyat çekilir
  4. Skor hesaplanır: yön doğru mu? kazanç doğru mu?
  5. Bu skor Darwin fitness'a beslenir

Skor sistemi:
  +2.0: Yön ve büyüklük doğru (>%5 hareket, doğru yön)
  +1.0: Sadece yön doğru
   0.0: HOLD dedi, fiyat yatay kaldı
  -1.0: Yön yanlış
  -2.0: Yön ve büyüklük yanlış (>%5 hareket, ters yön)
"""

import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT   = Path(__file__).parent.parent
MEMORY_DIR  = Path(__file__).parent / "memory"
TR_TZ       = pytz.timezone("Europe/Istanbul")
FMP_KEY     = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE    = "https://financialmodelingprep.com/stable"
LOG_PATH    = MEMORY_DIR / "prediction_log.json"

SCORE_WINDOWS = [5, 10, 14]  # Gün sonra skorla


# ── Tahmin Kaydetme ───────────────────────────────────────────────────────────

def log_prediction(
    agent_name: str,
    prediction_type: str,       # BUY / SELL / HOLD / ROTASYON / REJIM
    symbol: str,                # Hisse kodu veya sektör (ör: "XLE")
    direction: str,             # UP / DOWN / NEUTRAL
    magnitude: str,             # HIGH (>%5) / MEDIUM (%2-5) / LOW (<%2)
    rationale: str,             # Gerekçe
    source_rule: str = "",      # Hangi K-kuralı tetikledi
    confidence: str = "MEDIUM"  # HIGH / MEDIUM / LOW
) -> str:
    """Bir tahmin kaydeder ve ID döner."""

    pred_id = f"pred_{datetime.now(TR_TZ).strftime('%Y%m%d_%H%M%S')}"

    # Mevcut fiyatı al
    current_price = None
    try:
        r = requests.get(
            f"{FMP_BASE}/batch-quote",
            params={"symbols": symbol, "apikey": FMP_KEY},
            timeout=8
        ).json()
        if r and isinstance(r, list):
            current_price = r[0].get("price")
    except Exception:
        pass

    prediction = {
        "id":              pred_id,
        "tarih":           datetime.now(TR_TZ).isoformat(),
        "agent":           agent_name,
        "tip":             prediction_type,
        "sembol":          symbol,
        "yon":             direction,      # UP / DOWN / NEUTRAL
        "buyukluk":        magnitude,      # HIGH / MEDIUM / LOW
        "guven":           confidence,
        "giris_fiyat":     current_price,
        "gerekce":         rationale[:200],
        "kaynak_kural":    source_rule,
        "durum":           "BEKLIYOR",     # BEKLIYOR / SKORLANDI
        "skorlar":         {},             # {5: 1.0, 10: -1.0, 14: 0.5}
        "gercek_fiyatlar": {},             # {5: 145.2, 10: 138.0, 14: 142.0}
        "son_skor":        None,           # Nihai ağırlıklı skor
    }

    # Kaydet
    log = _load_log()
    log["tahminler"].append(prediction)
    log["tahminler"] = log["tahminler"][-500:]  # Max 500 kayıt
    _save_log(log)

    print(f"[Tahmin] Kaydedildi: {pred_id} | {symbol} {direction} | {agent_name}")
    return pred_id


# ── Tahmin Skiplama ───────────────────────────────────────────────────────────

def score_pending_predictions() -> list[dict]:
    """
    Süresi gelen tahminleri skorlar.
    Her sabah çalıştırılır.
    """
    log   = _load_log()
    today = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    scored = []

    for pred in log["tahminler"]:
        if pred.get("durum") == "SKORLANDI":
            continue

        pred_date     = pred.get("tarih", "")[:10]
        entry_price   = pred.get("giris_fiyat")
        symbol        = pred.get("sembol", "")
        direction     = pred.get("yon", "")
        magnitude     = pred.get("buyukluk", "")

        if not entry_price or not symbol:
            continue

        pred_dt = datetime.strptime(pred_date, "%Y-%m-%d")
        all_scored = True

        for window in SCORE_WINDOWS:
            if str(window) in pred.get("skorlar", {}):
                continue  # Zaten skorlandı

            target_date = (pred_dt + timedelta(days=window)).strftime("%Y-%m-%d")
            if target_date > today:
                all_scored = False
                continue

            # Gerçek fiyatı çek
            real_price = _get_price_on_date(symbol, target_date)
            if real_price is None:
                all_scored = False
                continue

            # Skor hesapla
            pct_change = (real_price - float(entry_price)) / float(entry_price) * 100
            score      = _calculate_score(direction, magnitude, pct_change)

            pred["skorlar"][str(window)]          = score
            pred["gercek_fiyatlar"][str(window)]  = real_price

            print(f"[Tahmin] {pred['id']} | {symbol} | {window}g: {pct_change:+.1f}% → skor {score:+.1f}")

        # Tüm pencereler skorlandıysa nihai skoru hesapla
        if all_scored and len(pred["skorlar"]) == len(SCORE_WINDOWS):
            weights    = {5: 0.2, 10: 0.3, 14: 0.5}  # Uzun vade daha önemli
            final      = sum(
                pred["skorlar"].get(str(w), 0) * weights[w]
                for w in SCORE_WINDOWS
            )
            pred["son_skor"] = round(final, 3)
            pred["durum"]    = "SKORLANDI"
            scored.append(pred)

    _save_log(log)

    if scored:
        print(f"[Tahmin] {len(scored)} tahmin skorlandı")
    return scored


def _calculate_score(direction: str, magnitude: str, pct_change: float) -> float:
    """
    Tahmin vs gerçek karşılaştırması.
    Yön + büyüklük birlikte değerlendirilir.
    """
    threshold_high   = 5.0   # %>5 = HIGH
    threshold_medium = 2.0   # %>2 = MEDIUM

    actual_dir = "UP" if pct_change > 0.5 else "DOWN" if pct_change < -0.5 else "NEUTRAL"
    actual_mag = "HIGH" if abs(pct_change) >= threshold_high else \
                 "MEDIUM" if abs(pct_change) >= threshold_medium else "LOW"

    # Yön doğru mu?
    dir_correct = (direction == actual_dir) or \
                  (direction == "NEUTRAL" and actual_dir == "NEUTRAL")

    if direction == "NEUTRAL":
        return 0.5 if actual_dir == "NEUTRAL" else -0.5

    if not dir_correct:
        # Yön yanlış
        return -2.0 if actual_mag == "HIGH" else -1.0

    # Yön doğru
    if magnitude == actual_mag:
        return 2.0  # Hem yön hem büyüklük doğru
    elif magnitude == "HIGH" and actual_mag == "MEDIUM":
        return 0.8  # Biraz aşırı tahmin
    elif magnitude == "LOW" and actual_mag in ("MEDIUM", "HIGH"):
        return 1.2  # Muhafazakar tahmin ama doğru yön
    else:
        return 1.0  # Yön doğru, büyüklük yaklaşık


def _get_price_on_date(symbol: str, date_str: str) -> float | None:
    """FMP'den belirli bir tarihteki fiyatı çeker."""
    try:
        r = requests.get(
            f"{FMP_BASE}/historical-price-eod/full",
            params={"symbol": symbol, "apikey": FMP_KEY},
            timeout=10
        ).json()

        if not isinstance(r, list):
            return None

        price_map = {d["date"]: d["close"] for d in r}

        # Tam tarih yoksa en yakın iş gününü bul
        for offset in range(5):
            dt  = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=offset)
            key = dt.strftime("%Y-%m-%d")
            if key in price_map:
                return price_map[key]
        return None
    except Exception:
        return None


# ── Agent Performans Özeti ────────────────────────────────────────────────────

def get_agent_accuracy_summary() -> dict:
    """
    Her agent'ın tahmin doğruluğunu özetler.
    Darwin fitness'a beslenir.
    """
    log    = _load_log()
    agents = {}

    for pred in log["tahminler"]:
        if pred.get("durum") != "SKORLANDI":
            continue

        agent = pred.get("agent", "bilinmiyor")
        skor  = pred.get("son_skor", 0)

        if agent not in agents:
            agents[agent] = {"tahmin": 0, "toplam_skor": 0.0, "skorlar": []}

        agents[agent]["tahmin"]      += 1
        agents[agent]["toplam_skor"] += skor
        agents[agent]["skorlar"].append(skor)

    # Ortalama ve std dev hesapla
    summary = {}
    for agent, data in agents.items():
        n      = data["tahmin"]
        avg    = data["toplam_skor"] / n if n > 0 else 0
        skorlar = data["skorlar"]
        std    = (sum((s - avg) ** 2 for s in skorlar) / n) ** 0.5 if n > 1 else 1.0
        sharpe = avg / std if std > 0 else 0  # Basit Sharpe proxy

        summary[agent] = {
            "tahmin_sayisi": n,
            "ort_skor":      round(avg, 3),
            "std_dev":       round(std, 3),
            "sharpe_proxy":  round(sharpe, 3),
            "son_5_skor":    skorlar[-5:],
        }

    return dict(sorted(summary.items(), key=lambda x: -x[1]["sharpe_proxy"]))


def get_rule_accuracy_summary() -> dict:
    """K-kuralı bazında tahmin doğruluğu."""
    log   = _load_log()
    rules = {}

    for pred in log["tahminler"]:
        if pred.get("durum") != "SKORLANDI":
            continue

        rule = pred.get("kaynak_kural", "genel")
        skor = pred.get("son_skor", 0)

        if rule not in rules:
            rules[rule] = {"n": 0, "toplam": 0.0, "skorlar": []}

        rules[rule]["n"]       += 1
        rules[rule]["toplam"]  += skor
        rules[rule]["skorlar"].append(skor)

    result = {}
    for rule, data in rules.items():
        n      = data["n"]
        avg    = data["toplam"] / n if n > 0 else 0
        result[rule] = {"n": n, "ort_skor": round(avg, 3)}

    return dict(sorted(result.items(), key=lambda x: -x[1]["ort_skor"]))


def get_prediction_context() -> str:
    """Claude context'i için tahmin özeti."""
    log      = _load_log()
    bekleyen = [p for p in log["tahminler"] if p.get("durum") == "BEKLIYOR"]
    skorlanan = [p for p in log["tahminler"] if p.get("durum") == "SKORLANDI"]

    lines = ["=== TAHMİN LOGU ==="]
    lines.append(f"Bekleyen: {len(bekleyen)} | Skorlanan: {len(skorlanan)}")

    if skorlanan:
        son5 = [p["son_skor"] for p in skorlanan[-5:] if p.get("son_skor") is not None]
        avg  = sum(son5) / len(son5) if son5 else 0
        lines.append(f"Son 5 tahmin ort skoru: {avg:+.2f}")

    agent_acc = get_agent_accuracy_summary()
    if agent_acc:
        lines.append("\nAgent Doğruluğu:")
        for agent, data in list(agent_acc.items())[:5]:
            lines.append(
                f"  {agent}: Sharpe {data['sharpe_proxy']:+.2f} "
                f"({data['tahmin_sayisi']} tahmin)"
            )

    return "\n".join(lines)


# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _load_log() -> dict:
    if LOG_PATH.exists():
        with open(LOG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"tahminler": [], "olusturma": datetime.now(TR_TZ).isoformat()}


def _save_log(log: dict):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ── Gerçek Çıkış Kontrolü — v2 Düzeltmesi ─────────────────────────────────────
# SORUN: score_pending_predictions() 5/10/14 günlük fiyatı FMP'den çekiyor.
# Ama trade 3. günde stop-loss ile kapandıysa:
#   → Gerçek sonuç: zarar
#   → 5. günde fiyat iyileştiyse: sistem "başarılı tahmin" sayıyor
# Bu Darwin fitness'ını bozar çünkü "başarılı tahmin ≠ başarılı trade".
#
# ÇÖZÜM: score_pending_predictions() çağrılmadan önce bu fonksiyon kontrol eder.
# Eğer trade score_window'dan önce gerçek çıkış yaptıysa → exit P/L kullan.

def find_real_exit_before(symbol: str, entry_price: float, before_date: str) -> float | None:
    """
    transactions.csv'den before_date'ten önce gerçekleşen çıkış P/L'ını döner.
    Yoksa None.
    """
    import csv
    tx_path = REPO_ROOT / "data" / "transactions.csv"
    if not tx_path.exists() or float(entry_price or 0) <= 0:
        return None
    try:
        with open(tx_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            sym    = row.get("symbol", "").upper()
            action = row.get("action", "").upper()
            edate  = row.get("date", "")
            eprice = float(row.get("price", 0) or 0)
            if sym == symbol.upper() and action in ("SELL", "SATIŞ"):
                if edate and edate < before_date and eprice > 0:
                    return (eprice - float(entry_price)) / float(entry_price) * 100
    except Exception:
        pass
    return None


def score_pending_predictions_v2() -> list[dict]:
    """
    v2: Gerçek çıkış farkında tahmin skoru.
    Her score_window için önce transactions.csv'e bakar.
    Erken çıkış varsa → gerçek exit P/L ile skor.
    Yoksa → FMP'den o günkü fiyatı çek (orijinal davranış).
    """
    log    = _load_log()
    today  = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    scored = []

    for pred in log["tahminler"]:
        if pred.get("durum") == "SKORLANDI":
            continue

        pred_date   = pred.get("tarih", "")[:10]
        entry_price = pred.get("giris_fiyat")
        symbol      = pred.get("sembol", "")
        direction   = pred.get("yon", "")
        magnitude   = pred.get("buyukluk", "")

        if not entry_price or not symbol:
            continue

        pred_dt    = datetime.strptime(pred_date, "%Y-%m-%d")
        all_scored = True

        for window in SCORE_WINDOWS:
            if str(window) in pred.get("skorlar", {}):
                continue

            target_date = (pred_dt + timedelta(days=window)).strftime("%Y-%m-%d")
            if target_date > today:
                all_scored = False
                continue

            # Önce gerçek çıkışa bak (erken stop/hedef)
            real_exit_pnl = find_real_exit_before(symbol, entry_price, target_date)
            if real_exit_pnl is not None:
                score      = _calculate_score(direction, magnitude, real_exit_pnl)
                pct_change = real_exit_pnl
                method     = "gercek_exit"
                real_price = float(entry_price) * (1 + real_exit_pnl / 100)
            else:
                # Gerçek çıkış yok → FMP'den o günkü fiyat
                real_price = _get_price_on_date(symbol, target_date)
                if real_price is None:
                    all_scored = False
                    continue
                pct_change = (real_price - float(entry_price)) / float(entry_price) * 100
                score      = _calculate_score(direction, magnitude, pct_change)
                method     = "piyasa_fiyat"

            pred["skorlar"][str(window)]         = score
            pred["gercek_fiyatlar"][str(window)] = real_price
            pred.setdefault("skor_metod", {})[str(window)] = method

            print(f"[Tahmin v2] {pred.get('id','')} | {symbol} | "
                  f"{window}g | {method}: {pct_change:+.1f}% → skor {score:+.1f}")

        if all_scored and len(pred.get("skorlar", {})) == len(SCORE_WINDOWS):
            weights   = {5: 0.2, 10: 0.3, 14: 0.5}
            final     = sum(pred["skorlar"].get(str(w), 0) * weights[w] for w in SCORE_WINDOWS)
            pred["son_skor"] = round(final, 3)
            pred["durum"]    = "SKORLANDI"
            scored.append(pred)

    _save_log(log)
    if scored:
        print(f"[Tahmin v2] {len(scored)} tahmin skorlandı")
    return scored
