#!/usr/bin/env python3
"""
Finzora — VCP (Volatility Contraction Pattern) Detector
========================================================
Mark Minervini'nin VCP setup'ını algoritmik olarak tespit eder.

KULLANIM:
    from agent.vcp_detector import detect_vcp

    result = detect_vcp("NVDA")
    # {
    #   "symbol": "NVDA",
    #   "vcp_status": "STRONG" | "WEAK" | "NONE",
    #   "vcp_score": 0-100,
    #   "contractions": [{"depth_pct": ..., "length_days": ..., "avg_volume": ...}, ...],
    #   "pivot_price": float,
    #   "pivot_distance_pct": float,   # mevcut fiyatın pivot'a uzaklığı (% olarak, negatif = altında)
    #   "volume_dry_up": bool,         # son kontraksiyonda hacim öncekilerden düşük mü
    #   "trend_ok": bool,              # SMA50 > SMA200 (Stage 2 ön koşul)
    #   "reason": "..." (insan-okunur açıklama)
    # }

ALGORITMA (Minervini metodolojisi):
1. Son 60-120 trading günü al (historical-price-eod/full)
2. Zigzag pivot tespiti: %3+ swing'leri yakala (high-low arası)
3. Ardışık pullback'ler (peak → trough → peak): her biri öncekinden küçük olmalı
4. Hacim kuruması: her kontraksiyonun ortalama hacmi öncekinden düşük olmalı
5. Pivot noktası: son ve en yüksek peak; mevcut fiyat buna < %3 uzaklıkta olmalı
6. Trend filtresi: SMA50 > SMA200 zorunlu (Stage 2)

KARAR EŞİKLERİ:
- STRONG VCP (skor 70+): 3+ kontraksyon + hacim kuruyor + pivot net + trend ok
- WEAK VCP (skor 40-69): 2 kontraksyon veya hacim karışık
- NONE (skor <40): VCP paterni yok
"""

import sys
from pathlib import Path
from typing import Optional

# agent/ klasörünü sys.path'e ekle ki "agent.fmp_client" yerine doğrudan "fmp_client" import edilsin
_AGENT_DIR = Path(__file__).resolve().parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

from fmp_client import fmp_get  # noqa: E402


# ============================================================================
# YAPILANDIRMA
# ============================================================================
MIN_SWING_PCT = 3.0          # %3 altı hareketler gürültü kabul edilir
MIN_CONTRACTIONS = 2          # En az 2 ardışık daralan kontraksiyon
IDEAL_CONTRACTIONS = 3        # 3+ kontraksyon ideal
PIVOT_MAX_DISTANCE_PCT = 3.0  # Pivot'a max %3 uzaklık (yakınlık şartı)
LOOKBACK_DAYS = 120           # Son 6 ay civarı


# ============================================================================
# YARDIMCILAR
# ============================================================================

def _sma(values: list, period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _detect_pivots(highs: list, lows: list, min_swing_pct: float = MIN_SWING_PCT) -> list:
    """
    Zigzag pivot tespiti.

    Her bar için: önceki pivot'a göre min_swing_pct'lik bir hareket olduğunda
    yeni pivot oluştur.

    Returns:
        list of dicts: [{"idx": int, "price": float, "type": "H"|"L"}, ...]
        Kronolojik sırada (eski → yeni).
    """
    if len(highs) < 5:
        return []

    pivots = []
    # İlk pivot: bilinmeyen yön. Açılış barını L kabul edip ilerle.
    # Yön bulunca düzeltilir.
    last_pivot_price = highs[0]
    last_pivot_idx = 0
    last_pivot_type = None  # belirsiz başla
    direction = None        # "up" | "down" | None

    for i in range(1, len(highs)):
        h, l = highs[i], lows[i]

        if direction is None:
            # Yön henüz belli değil; ilk %min_swing kırılmasını bul
            up_move = (h - last_pivot_price) / last_pivot_price * 100 if last_pivot_price > 0 else 0
            down_move = (last_pivot_price - l) / last_pivot_price * 100 if last_pivot_price > 0 else 0

            if up_move >= min_swing_pct:
                # Yukarı kırıldı → ilk pivot L'di
                pivots.append({"idx": last_pivot_idx, "price": lows[last_pivot_idx], "type": "L"})
                last_pivot_price = h
                last_pivot_idx = i
                last_pivot_type = "H"
                direction = "up"
            elif down_move >= min_swing_pct:
                # Aşağı kırıldı → ilk pivot H'di
                pivots.append({"idx": last_pivot_idx, "price": highs[last_pivot_idx], "type": "H"})
                last_pivot_price = l
                last_pivot_idx = i
                last_pivot_type = "L"
                direction = "down"

        elif direction == "up":
            # Yukarı trend: yeni high'lar pivot'u güncelle; min_swing aşağı düşüş yön değiştirir
            if h > last_pivot_price:
                last_pivot_price = h
                last_pivot_idx = i
            else:
                down_from_peak = (last_pivot_price - l) / last_pivot_price * 100 if last_pivot_price > 0 else 0
                if down_from_peak >= min_swing_pct:
                    pivots.append({"idx": last_pivot_idx, "price": last_pivot_price, "type": "H"})
                    last_pivot_price = l
                    last_pivot_idx = i
                    last_pivot_type = "L"
                    direction = "down"

        elif direction == "down":
            if l < last_pivot_price:
                last_pivot_price = l
                last_pivot_idx = i
            else:
                up_from_trough = (h - last_pivot_price) / last_pivot_price * 100 if last_pivot_price > 0 else 0
                if up_from_trough >= min_swing_pct:
                    pivots.append({"idx": last_pivot_idx, "price": last_pivot_price, "type": "L"})
                    last_pivot_price = h
                    last_pivot_idx = i
                    last_pivot_type = "H"
                    direction = "up"

    # Son pivot'u da ekle
    if last_pivot_type is not None:
        pivots.append({"idx": last_pivot_idx, "price": last_pivot_price, "type": last_pivot_type})

    return pivots


def _extract_contractions(pivots: list, volumes: list) -> list:
    """
    Pivot listesinden kontraksiyonları çıkar.
    Bir kontraksiyon = peak (H) → trough (L) → peak (H) üçlüsünden trough'a inen düşüş.

    Her kontraksyon için:
      - depth_pct: peak'ten trough'a düşüş yüzdesi
      - length_days: bar sayısı (idx farkı)
      - avg_volume: kontraksyon süresince ortalama hacim
      - peak_idx, trough_idx
    """
    contractions = []
    for i in range(len(pivots) - 1):
        p_now = pivots[i]
        p_next = pivots[i + 1]
        if p_now["type"] == "H" and p_next["type"] == "L":
            peak_price = p_now["price"]
            trough_price = p_next["price"]
            if peak_price <= 0:
                continue
            depth = (peak_price - trough_price) / peak_price * 100
            length = p_next["idx"] - p_now["idx"]
            seg_volumes = volumes[p_now["idx"]:p_next["idx"] + 1]
            avg_vol = sum(seg_volumes) / len(seg_volumes) if seg_volumes else 0
            contractions.append({
                "peak_idx": p_now["idx"],
                "trough_idx": p_next["idx"],
                "peak_price": peak_price,
                "trough_price": trough_price,
                "depth_pct": round(depth, 2),
                "length_days": length,
                "avg_volume": int(avg_vol),
            })
    return contractions


def _evaluate_vcp(contractions: list, current_price: float, trend_ok: bool) -> dict:
    """
    Kontraksiyon listesini değerlendirip VCP skorunu hesapla.

    Skor bileşenleri (toplam 100):
      - Kontraksyon sayısı (30 puan)
      - Daralma sırası (her biri öncekinden küçük) (25 puan)
      - Hacim kuruması (20 puan)
      - Pivot yakınlığı (15 puan)
      - Trend (SMA50>SMA200) (10 puan)
    """
    n = len(contractions)
    score = 0
    reasons = []

    # 1) Kontraksyon sayısı
    if n >= IDEAL_CONTRACTIONS:
        score += 30
        reasons.append(f"{n} kontraksyon (ideal)")
    elif n >= MIN_CONTRACTIONS:
        score += 18
        reasons.append(f"{n} kontraksyon (minimum)")
    else:
        reasons.append(f"sadece {n} kontraksyon (yetersiz)")
        return {
            "vcp_status": "NONE",
            "vcp_score": score,
            "pivot_price": None,
            "pivot_distance_pct": None,
            "volume_dry_up": False,
            "trend_ok": trend_ok,
            "reason": "; ".join(reasons),
        }

    # KRİTİK: VCP, SON kontraksyondan geriye doğru ARDIŞIK DARALAN diziye bakar.
    # Sondan başla, derinlik artmaya başlayana kadar geri git → bu "VCP zinciri".
    shrinking_chain = [contractions[-1]]
    for i in range(len(contractions) - 2, -1, -1):
        if contractions[i]["depth_pct"] > shrinking_chain[0]["depth_pct"]:
            shrinking_chain.insert(0, contractions[i])
        else:
            break  # zincir bozuldu, daha geriye gitmek yanlış sinyal verir

    chain_len = len(shrinking_chain)
    last_n = shrinking_chain

    # Yukarıda toplam kontraksyon için verilen 30/18 puanı geri al;
    # gerçek puan zincir uzunluğuna dayanmalı.
    if n >= IDEAL_CONTRACTIONS:
        score -= 30
    elif n >= MIN_CONTRACTIONS:
        score -= 18

    # Zincir uzunluğuna göre yeni puan
    if chain_len >= IDEAL_CONTRACTIONS:
        score += 30
        reasons.append(f"VCP zinciri güçlü: {chain_len} ardışık daralan kontraksyon")
    elif chain_len >= MIN_CONTRACTIONS:
        score += 18
        reasons.append(f"VCP zinciri minimum: {chain_len} ardışık daralan kontraksyon")
    else:
        reasons.append(f"VCP zinciri yok (son daralma izole)")

    # 2) Daralma sırası — zincir tanımı gereği monoton, ama bilgiyi yaz
    depths = [c["depth_pct"] for c in last_n]
    if chain_len >= MIN_CONTRACTIONS:
        score += 25
        reasons.append(f"daralma sırası: {'→'.join(f'%{d:.1f}' for d in depths)}")
    else:
        reasons.append(f"daralma sırası: {'→'.join(f'%{d:.1f}' for d in depths)} (yetersiz)")

    # 3) Hacim kuruması
    vols = [c["avg_volume"] for c in last_n]
    volume_drying = all(vols[i] < vols[i-1] for i in range(1, len(vols)))
    if volume_drying:
        score += 20
        reasons.append("hacim her kontraksyonda azalıyor")
    elif len(vols) >= 2 and vols[-1] < vols[-2]:
        score += 10
        reasons.append("son kontraksyon hacmi düşük")
    else:
        reasons.append("hacim kuruması net değil")

    # 4) Pivot yakınlığı
    # Pivot = VCP zincirindeki en yüksek peak.
    pivot_price = max(c["peak_price"] for c in last_n)
    pivot_dist = (current_price - pivot_price) / pivot_price * 100 if pivot_price > 0 else 0

    pivot_broken_down = False  # bayrak: setup tamamen bozuldu mu

    if abs(pivot_dist) <= PIVOT_MAX_DISTANCE_PCT:
        score += 15
        reasons.append(f"pivot ${pivot_price:.2f} yakınında ({pivot_dist:+.2f}%)")
    elif pivot_dist > PIVOT_MAX_DISTANCE_PCT:
        # Yukarı kırılmış — breakout zaten gerçekleşmiş; kovalama riski
        if pivot_dist > 10:
            reasons.append(f"pivot çok yukarıda kırılmış (+{pivot_dist:.1f}%) — kovalama riski")
        else:
            score += 8
            reasons.append(f"pivot kırıldı (+{pivot_dist:.1f}%) — breakout teyidi gerek")
    else:
        # Pivot'un altında — setup ne kadar bozuldu?
        if pivot_dist < -5:
            pivot_broken_down = True
            reasons.append(f"⚠️ pivot'tan uzak ({pivot_dist:.1f}%) — setup BOZULDU")
        else:
            reasons.append(f"pivot'a yaklaşıyor ({pivot_dist:.1f}%)")

    # 5) Trend
    if trend_ok:
        score += 10
        reasons.append("SMA50>SMA200 (Stage 2)")
    else:
        reasons.append("trend zayıf (SMA50<=SMA200)")

    # Karar — setup bozulduysa max WEAK
    if pivot_broken_down:
        if score >= 40:
            status = "WEAK"  # zincir güçlü olsa bile, pivot bozulduysa STRONG yok
        else:
            status = "NONE"
    elif score >= 70:
        status = "STRONG"
    elif score >= 40:
        status = "WEAK"
    else:
        status = "NONE"

    return {
        "vcp_status": status,
        "vcp_score": score,
        "pivot_price": round(pivot_price, 2),
        "pivot_distance_pct": round(pivot_dist, 2),
        "volume_dry_up": volume_drying,
        "trend_ok": trend_ok,
        "reason": "; ".join(reasons),
    }


# ============================================================================
# ANA FONKSIYON
# ============================================================================

def detect_vcp(symbol: str, lookback_days: int = LOOKBACK_DAYS, as_of_date: Optional[str] = None) -> dict:
    """
    Bir sembol için VCP tespiti yapar.

    Args:
        symbol: Ticker
        lookback_days: Geriye bakılacak gün sayısı
        as_of_date: "YYYY-MM-DD" formatında. Verilirse, sanki o tarihteymişiz gibi
                    sadece o tarihe kadar olan veri kullanılır (backtest için).
    """
    params = {"symbol": symbol, "limit": lookback_days + 60}
    if as_of_date:
        # "to" parametresi ile o tarihe kadar olan veriyi al
        params["to"] = as_of_date
        # "from" da gerekli olabilir — limit her zaman çalışmıyor "to" ile
        from datetime import datetime, timedelta
        to_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
        # lookback + 60 takvim günü (haftasonu/tatil için ek marj × 1.5)
        from_dt = to_dt - timedelta(days=int((lookback_days + 60) * 1.5))
        params["from"] = from_dt.strftime("%Y-%m-%d")

    hist = fmp_get("historical-price-eod/full", params)
    if not hist or not isinstance(hist, list) or len(hist) < 50:
        return {
            "symbol": symbol,
            "as_of_date": as_of_date,
            "vcp_status": "ERROR",
            "vcp_score": 0,
            "reason": "yeterli geçmiş veri yok",
        }

    # FMP newest-first → reverse to chronological
    hist = list(reversed(hist))
    # Sadece son lookback_days günü al
    hist = hist[-lookback_days:]

    highs = [float(h.get("high") or 0) for h in hist]
    lows = [float(h.get("low") or 0) for h in hist]
    closes = [float(h.get("close") or 0) for h in hist]
    volumes = [float(h.get("volume") or 0) for h in hist]

    current_price = closes[-1] if closes else 0
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200) if len(closes) >= 200 else None
    # SMA200 alamadıysak, mevcut veriyle daha kısa pencere kullan (lookback 120 olduğunda)
    if sma200 is None and len(closes) >= 100:
        sma200 = _sma(closes, len(closes) - 10)  # mevcut uzun pencere

    trend_ok = (sma50 is not None and sma200 is not None and sma50 > sma200)

    pivots = _detect_pivots(highs, lows, MIN_SWING_PCT)
    contractions = _extract_contractions(pivots, volumes)

    evaluation = _evaluate_vcp(contractions, current_price, trend_ok)

    return {
        "symbol": symbol,
        "as_of_date": as_of_date,
        "current_price": round(current_price, 2),
        "sma50": round(sma50, 2) if sma50 else None,
        "sma200": round(sma200, 2) if sma200 else None,
        "contractions": contractions[-5:],  # son 5 kontraksyon
        "pivot_count": len(pivots),
        **evaluation,
    }


# ============================================================================
# CLI / TEST
# ============================================================================
if __name__ == "__main__":
    import json

    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["NVDA", "AAPL", "PLTR"]

    for sym in symbols:
        print(f"\n{'='*60}")
        print(f"VCP TESPİT: {sym}")
        print('='*60)
        result = detect_vcp(sym)
        print(json.dumps(result, indent=2, ensure_ascii=False))
