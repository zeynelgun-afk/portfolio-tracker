#!/usr/bin/env python3
"""
Finzora Agent — Öğrenme Motoru
================================
Sistem kendi kendini geliştirir:
  1. Kapanan trade'lerden ders çıkarır
  2. K-kuralı performansını ölçer
  3. Twitter/web kaynak güvenilirlik skoru tutar
  4. Haftalık: PLAYBOOK güncelleme önerileri üretir
  5. Screener filtresi değişikliği önerir (backtest zorunlu)

Çıktı:
  - agent/memory/learning_log.json   → birikimli dersler
  - agent/memory/k_rule_stats.json   → K-kuralı istatistikleri
  - agent/memory/source_scores.json  → kaynak güvenilirlik
  - agent/memory/proposed_changes.json → öneri kuyruğu
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import pytz

REPO_ROOT  = Path(__file__).parent.parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")

MEMORY_DIR.mkdir(exist_ok=True)


# ── 1. Trade Analizi ──────────────────────────────────────────────────────────

def analyze_closed_trades(days_back: int = 30) -> dict:
    """
    closed.json'daki kapanmış trade'leri analiz eder.
    Son N günün performans özeti + ders çıkarımı.
    """
    path = REPO_ROOT / "data" / "swing" / "closed.json"
    if not path.exists():
        return {"hata": "closed.json bulunamadı"}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    trades    = data.get("kapatilan_pozisyonlar", data.get("kapali_pozisyonlar", data.get("closed_positions", [])))
    cutoff    = (datetime.now(TR_TZ) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    recent    = []
    for t in trades:
        exit_date = t.get("cikis_tarihi") or t.get("exit_date", "")
        if exit_date >= cutoff:
            recent.append(t)

    if not recent:
        return {"mesaj": f"Son {days_back} günde kapanmış trade yok"}

    # İstatistikler
    pnl_values   = []
    winners      = 0
    losers       = 0
    scan_methods = defaultdict(list)
    k_rules_hit  = defaultdict(int)
    lessons      = []

    for t in recent:
        # Canonical alan: kar_zarar_yuzde. Fallback'ler: pnl_yuzde, pnl_pct.
        pnl = t.get("kar_zarar_yuzde")
        if pnl is None:
            pnl = t.get("pnl_yuzde") or t.get("pnl_pct") or 0
        try:
            pnl = float(pnl)
        except (ValueError, TypeError):
            pnl = 0

        pnl_values.append(pnl)
        if pnl > 0:
            winners += 1
        else:
            losers += 1

        method = t.get("tarama_yontemi") or t.get("scan_method", "bilinmiyor")
        scan_methods[method].append(pnl)

        exit_reason = t.get("cikis_nedeni") or t.get("exit_reason", "")
        if "stop" in exit_reason.lower():
            k_rules_hit["stop_loss"] += 1
        if "K-11" in exit_reason or "kar_al" in exit_reason.lower():
            k_rules_hit["K-11_kar_alma"] += 1
        if "K-05" in exit_reason or "earnings" in exit_reason.lower():
            k_rules_hit["K-05_earnings"] += 1

        # Canonical alan: 'ders' (tekil). Fallback: 'dersler', 'lessons'.
        lesson = t.get("ders") or t.get("dersler") or t.get("lessons", "")
        if lesson:
            lessons.append(f"{t.get('sembol','?')}: {lesson[:150]}")

    avg_pnl    = sum(pnl_values) / len(pnl_values) if pnl_values else 0
    win_rate   = winners / len(recent) * 100 if recent else 0

    # Tarama yöntemi performansı
    method_perf = {}
    for method, pnls in scan_methods.items():
        method_perf[method] = {
            "trade_sayisi": len(pnls),
            "ort_pnl":      round(sum(pnls) / len(pnls), 2),
            "win_rate":     round(sum(1 for p in pnls if p > 0) / len(pnls) * 100, 1),
        }

    return {
        "analiz_tarihi":  datetime.now(TR_TZ).strftime("%Y-%m-%d"),
        "donem":          f"Son {days_back} gün",
        "trade_sayisi":   len(recent),
        "win_rate":       round(win_rate, 1),
        "ort_pnl":        round(avg_pnl, 2),
        "kazanan":        winners,
        "kaybeden":       losers,
        "method_perf":    method_perf,
        "k_rule_tetik":   dict(k_rules_hit),
        "son_dersler":    lessons[-5:],
    }


# ── 2. K-Kuralı İstatistikleri ────────────────────────────────────────────────

def update_k_rule_stats(trade_analysis: dict):
    """
    K-kuralı tetiklenme istatistiklerini günceller.
    Hangi kural en çok koruma sağladı, hangisi çok erken sattı?
    """
    path = MEMORY_DIR / "k_rule_stats.json"

    stats = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            stats = json.load(f)

    today = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    stats["son_guncelleme"] = today

    # Tetiklenme sayıları
    for rule, count in trade_analysis.get("k_rule_tetik", {}).items():
        if rule not in stats:
            stats[rule] = {"toplam_tetik": 0, "tarihler": []}
        stats[rule]["toplam_tetik"] += count
        stats[rule]["tarihler"].append(today)
        stats[rule]["tarihler"] = stats[rule]["tarihler"][-30:]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats


# ── 3. Kaynak Güvenilirlik Skoru ──────────────────────────────────────────────

def update_source_scores(
    twitter_account: str,
    prediction: str,
    outcome: str,
    correct: bool
):
    """
    Twitter/web kaynağının tahmin doğruluğunu takip eder.
    Yüksek skor → AI daha fazla ağırlık verir.
    """
    path = MEMORY_DIR / "source_scores.json"

    scores = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            scores = json.load(f)

    if twitter_account not in scores:
        scores[twitter_account] = {
            "toplam": 0, "dogru": 0, "skor": 50.0,
            "gecmis": []
        }

    scores[twitter_account]["toplam"] += 1
    if correct:
        scores[twitter_account]["dogru"] += 1

    # Basit skor: dogru/toplam * 100
    s = scores[twitter_account]
    s["skor"] = round(s["dogru"] / s["toplam"] * 100, 1)
    s["gecmis"].append({
        "tarih":   datetime.now(TR_TZ).strftime("%Y-%m-%d"),
        "tahmin":  prediction[:100],
        "sonuc":   outcome[:100],
        "dogru":   correct,
    })
    s["gecmis"] = s["gecmis"][-20:]  # Son 20 kayıt

    with open(path, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)


def get_source_scores_summary() -> str:
    """Kaynak skorlarını LLM context'i için formatlar."""
    path = MEMORY_DIR / "source_scores.json"
    if not path.exists():
        return "Kaynak skoru henüz yok."

    with open(path, encoding="utf-8") as f:
        scores = json.load(f)

    lines = ["Kaynak Güvenilirlik Skorları:"]
    for account, data in sorted(scores.items(), key=lambda x: -x[1]["skor"]):
        if data["toplam"] >= 3:
            lines.append(
                f"  @{account}: %{data['skor']} doğru "
                f"({data['dogru']}/{data['toplam']} tahmin)"
            )
    return "\n".join(lines) if len(lines) > 1 else "Henüz yeterli veri yok (min 3 tahmin)."


# ── 4. Öneri Kuyruğu ──────────────────────────────────────────────────────────

def add_proposed_change(
    change_type: str,
    description: str,
    rationale: str,
    proposed_by: str = "agent",
    requires_backtest: bool = True
):
    """
    Kural/filtre değişikliği önerisini kuyruğa ekler.
    14 gün dry-run sonrası uygulanır.
    """
    path = MEMORY_DIR / "proposed_changes.json"

    changes = {"kuyruk": []}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            changes = json.load(f)

    proposal = {
        "id":               f"prop_{datetime.now(TR_TZ).strftime('%Y%m%d_%H%M')}",
        "tur":              change_type,
        "aciklama":         description,
        "gerekce":          rationale,
        "oneren":           proposed_by,
        "backtest_gerekli": requires_backtest,
        "olusturma_tarihi": datetime.now(TR_TZ).isoformat(),
        "durum":            "BEKLIYOR",
        "dry_run_bitis":    (datetime.now(TR_TZ) + timedelta(days=14)).strftime("%Y-%m-%d"),
        "dry_run_sonuc":    None,
    }

    changes["kuyruk"].append(proposal)
    changes["kuyruk"] = changes["kuyruk"][-20:]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

    print(f"[Learning] Öneri eklendi: {change_type} — {description[:60]}")
    return proposal


def get_pending_proposals() -> list:
    """Bekleyen önerileri döner."""
    path = MEMORY_DIR / "proposed_changes.json"
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return [p for p in data.get("kuyruk", []) if p.get("durum") == "BEKLIYOR"]


# ── 5. Haftalık Öğrenme Raporu ────────────────────────────────────────────────

def build_weekly_learning_context() -> str:
    """
    Haftalık derin analiz için öğrenme bağlamını derler.
    AI bu bağlamla PLAYBOOK güncelleme önerisi üretir.
    """
    trade_stats  = analyze_closed_trades(days_back=7)
    month_stats  = analyze_closed_trades(days_back=30)
    k_stats_path = MEMORY_DIR / "k_rule_stats.json"
    proposals    = get_pending_proposals()
    src_scores   = get_source_scores_summary()

    k_stats = {}
    if k_stats_path.exists():
        with open(k_stats_path, encoding="utf-8") as f:
            k_stats = json.load(f)

    lines = ["=== HAFTALIK ÖĞRENME BAĞLAMI ===\n"]

    lines.append("--- HAFTALIK TRADE İSTATİSTİKLERİ ---")
    lines.append(json.dumps(trade_stats, ensure_ascii=False, indent=2))
    lines.append("")

    lines.append("--- AYLIK TRADE İSTATİSTİKLERİ ---")
    lines.append(f"Trade sayısı: {month_stats.get('trade_sayisi', 0)}")
    lines.append(f"Win rate: %{month_stats.get('win_rate', 0)}")
    lines.append(f"Ort P/L: %{month_stats.get('ort_pnl', 0)}")
    lines.append("")

    lines.append("--- K-KURALI TETİKLENME GEÇMİŞİ ---")
    # Not: k_stats üst seviyesinde meta alanlar da var (son_guncelleme, analiz_donemi,
    # toplam_trade vb.). Gerçek K-kural verileri "k_kural_istatistikleri" alt dict'inde.
    k_rule_istatistikleri = k_stats.get("k_kural_istatistikleri", {})
    if isinstance(k_rule_istatistikleri, dict):
        for rule, data in k_rule_istatistikleri.items():
            if isinstance(data, dict):
                tetik = data.get("tetiklenme", data.get("toplam_tetik", 0))
                lines.append(f"  {rule}: {tetik} kez")
    lines.append("")

    lines.append("--- BEKLEYEN ÖNERİLER ---")
    if proposals:
        for p in proposals[:3]:
            lines.append(f"  [{p['id']}] {p['tur']}: {p['aciklama'][:80]}")
            lines.append(f"  Dry-run bitiş: {p['dry_run_bitis']}")
    else:
        lines.append("  Bekleyen öneri yok.")
    lines.append("")

    lines.append("--- KAYNAK SKORLARI ---")
    lines.append(src_scores)

    return "\n".join(lines)


# ── 6. Otomatik Ders Çıkarımı ─────────────────────────────────────────────────

def auto_extract_lessons(claude_response: str, mode: str):
    """
    AI'nin kapanış/haftalık analizinden otomatik ders çıkarır.
    'ders', 'öğrendim', 'dikkat', 'hata' içeren satırları yakalar.
    """
    keywords = ["ders", "öğren", "dikkat", "hata", "fark ettim", "sonuç",
                "backtest", "öneri", "değiştir", "K-", "kural"]

    lines = claude_response.split("\n")
    lessons_found = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(kw.lower() in line.lower() for kw in keywords):
            lessons_found.append(line[:200])

    if lessons_found:
        from memory_manager import append_learning
        for lesson in lessons_found[:3]:
            append_learning(lesson, source=f"auto_{mode}")
        print(f"[Learning] {len(lessons_found)} ders otomatik çıkarıldı.")

        # Hata içeren dersleri prompt evolver'a ilet
        hata_dersleri = [l for l in lessons_found if any(
            kw in l.lower() for kw in ["hata", "yanlış", "kaçır", "kural ihlal"]
        )]
        if hata_dersleri and mode in ("closing", "weekly"):
            try:
                from prompt_evolver import propose_prompt_improvement
                for ders in hata_dersleri[:1]:  # Günde max 1 öneri
                    # K-XX kural adını tespit et
                    import re
                    k_match = re.search(r"K-\d+", ders)
                    rule_name = k_match.group(0).replace("-", "_").lower() if k_match else None
                    if rule_name:
                        print(f"[Learning] {rule_name} için prompt iyileştirme önerisi isteniyor...")
                        propose_prompt_improvement(rule_name, ders)
            except Exception as e:
                print(f"[Learning] Prompt evolver hatası: {e}")
