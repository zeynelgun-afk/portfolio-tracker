#!/usr/bin/env python3
"""
Finzora Agent — Tema × Portföy Başarı Matrisi
===============================================
"AI teması aktifken Agresif portföy ne kazandı?" sorusunu cevaplar.

Her trade açılışında:
  → Aktif temayı kaydet (agent/memory/theme_scores.json'dan)
  → Trade kapandığında P&L hangi temaya ait olduğunu bil

Çıktı: agent/memory/tema_portfolio_matrix.json
Format:
{
  "AI_ALTYAPI": {
    "agresif": {"toplam_pnl": 12.4, "win_rate": 67, "trade_sayisi": 9},
    "dengeli":  {"toplam_pnl": 4.2,  "win_rate": 60, "trade_sayisi": 5},
    "temettü":  {"toplam_pnl": 2.1,  "win_rate": 75, "trade_sayisi": 4},
    "swing":    {"toplam_pnl": 8.3,  "win_rate": 55, "trade_sayisi": 20}
  },
  "SAVUNMA_JEOPOLITIK": {...}
}
"""

import json
from datetime import datetime
from pathlib import Path
import sys

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
MATRIX_PATH = MEMORY_DIR / "tema_portfolio_matrix.json"
MEMORY_DIR.mkdir(exist_ok=True)


# ── Tema Tespit ────────────────────────────────────────────────────────────────

def get_active_theme_on_date(date_str: str) -> str:
    """
    Belirli bir tarihte aktif temanın ne olduğunu bul.
    Önce theme_weekly_reviews.json'a bak, yoksa agent/memory/theme_scores.json'a.
    Not: Eski data/theme_scores.json (sentiment_engine output) kaldırıldı (20 Nisan 2026).
    """
    # Haftalık review geçmişinden bul
    reviews_path = MEMORY_DIR / "theme_weekly_reviews.json"
    if reviews_path.exists():
        with open(reviews_path, encoding="utf-8") as f:
            data = json.load(f)
        reviews = sorted(data.get("incelemeler", []), key=lambda x: x.get("tarih", ""))
        # Date'ten önceki son review
        for r in reversed(reviews):
            if r.get("tarih", "9999") <= date_str:
                # O review'daki en yüksek puanlı tema
                puanlar = r.get("performans", {})
                if puanlar:
                    best = max(puanlar.items(), key=lambda x: x[1].get("rs", 0) if isinstance(x[1], dict) else x[1])
                    return best[0]

    # Anlık fallback: theme_manager.py'nin yazdığı authoritative dosya
    scores_path = MEMORY_DIR / "theme_scores.json"
    if scores_path.exists():
        try:
            with open(scores_path, encoding="utf-8") as f:
                data = json.load(f)
            temalar = data.get("temalar", {})
            if temalar:
                # Aktif (aktif=True) ve en yüksek skorlu temayı al
                aktif = {k: v for k, v in temalar.items() if v.get("aktif")}
                kaynak = aktif if aktif else temalar
                best = max(kaynak.items(), key=lambda x: x[1].get("skor", 0))
                return best[0]
        except Exception:
            pass

    return "BILINMIYOR"


# ── Trade Analizi ─────────────────────────────────────────────────────────────

def analyze_trades_by_theme() -> dict:
    """
    Tüm kapanmış trade'leri (swing + portföy) tema × portföy matrisine dönüştür.
    """
    matrix = {}  # {tema: {portföy: {pnl_list, win_count, total}}}

    # 1. SWING trade'leri
    swing_path = REPO_ROOT / "data" / "swing" / "closed.json"
    if swing_path.exists():
        with open(swing_path, encoding="utf-8") as f:
            data = json.load(f)
        trades = data.get("kapatilan_pozisyonlar", data.get("kapali_pozisyonlar", data.get("closed_positions", [])))

        for t in trades:
            entry_date = t.get("giris_tarihi") or t.get("entry_date", "")
            pnl = float(t.get("pnl_yuzde") or t.get("pnl_pct") or 0)
            tema = t.get("aktif_tema") or get_active_theme_on_date(entry_date[:10] if entry_date else "")

            if tema not in matrix:
                matrix[tema] = {}
            if "swing" not in matrix[tema]:
                matrix[tema]["swing"] = {"pnl_list": [], "toplam": 0}

            matrix[tema]["swing"]["pnl_list"].append(pnl)
            matrix[tema]["swing"]["toplam"] += 1

    # 2. Portföy işlemleri (transactions.csv)
    tx_path = REPO_ROOT / "data" / "transactions.csv"
    if tx_path.exists():
        import csv
        buy_trades = {}  # {(portföy, sembol): {date, price}}

        with open(tx_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tx_type  = row.get("type", "").upper()
                portföy  = row.get("portfolio", row.get("portfoy", "agresif")).lower()
                sembol   = row.get("symbol", row.get("sembol", ""))
                date_str = row.get("date", "")
                price    = float(row.get("price", 0) or 0)

                key = (portföy, sembol)

                if tx_type == "BUY":
                    tema = get_active_theme_on_date(date_str[:10] if date_str else "")
                    buy_trades[key] = {"date": date_str, "price": price, "tema": tema}

                elif tx_type == "SELL" and key in buy_trades:
                    buy_info = buy_trades[key]
                    buy_price = buy_info["price"]
                    tema = buy_info["tema"]
                    pnl = (price - buy_price) / buy_price * 100 if buy_price > 0 else 0

                    if tema not in matrix:
                        matrix[tema] = {}
                    if portföy not in matrix[tema]:
                        matrix[tema][portföy] = {"pnl_list": [], "toplam": 0}

                    matrix[tema][portföy]["pnl_list"].append(pnl)
                    matrix[tema][portföy]["toplam"] += 1
                    del buy_trades[key]

    # 3. İstatistik hesapla
    result = {}
    for tema, portfolyolar in matrix.items():
        result[tema] = {}
        for portföy, data in portfolyolar.items():
            pnl_list = data["pnl_list"]
            if not pnl_list:
                continue
            winners = [p for p in pnl_list if p > 0]
            result[tema][portföy] = {
                "trade_sayisi": len(pnl_list),
                "toplam_pnl":   round(sum(pnl_list), 2),
                "ortalama_pnl": round(sum(pnl_list) / len(pnl_list), 2),
                "win_rate":     round(len(winners) / len(pnl_list) * 100, 1),
                "en_iyi":       round(max(pnl_list), 2),
                "en_kotu":      round(min(pnl_list), 2),
            }

    return result


# ── Matrisi Kaydet ve Raporla ─────────────────────────────────────────────────

def save_matrix(matrix: dict):
    output = {
        "guncelleme": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "matris":     matrix,
        "ozet":       build_summary(matrix)
    }
    with open(MATRIX_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[TemaMatrix] Matris kaydedildi: {MATRIX_PATH}")


def build_summary(matrix: dict) -> dict:
    """En karlı tema, en kötü tema, portföy bazında en başarılı tema."""
    tema_pnl   = {}
    portfoy_best = {"agresif": None, "dengeli": None, "temettü": None, "swing": None}

    for tema, portföyler in matrix.items():
        toplam_tema_pnl = sum(p["toplam_pnl"] for p in portföyler.values())
        tema_pnl[tema] = toplam_tema_pnl

        for portföy, stats in portföyler.items():
            if portföy in portfoy_best:
                if (portfoy_best[portföy] is None or
                        stats["ortalama_pnl"] > matrix.get(portfoy_best[portföy], {}).get(portföy, {}).get("ortalama_pnl", -999)):
                    portfoy_best[portföy] = tema

    return {
        "en_karli_tema":  max(tema_pnl, key=tema_pnl.get) if tema_pnl else "Veri yok",
        "en_kotu_tema":   min(tema_pnl, key=tema_pnl.get) if tema_pnl else "Veri yok",
        "tema_pnl_sirali": dict(sorted(tema_pnl.items(), key=lambda x: x[1], reverse=True)),
        "portfoy_en_iyi_tema": portfoy_best,
    }


def print_matrix_report(matrix: dict):
    """Konsol raporu."""
    print("\n" + "="*65)
    print("📊 TEMA × PORTFÖY BAŞARI MATRİSİ")
    print("="*65)

    for tema, portföyler in sorted(matrix.items()):
        print(f"\n🎯 {tema}")
        for portföy, stats in sorted(portföyler.items()):
            n   = stats["trade_sayisi"]
            avg = stats["ortalama_pnl"]
            wr  = stats["win_rate"]
            tot = stats["toplam_pnl"]
            bar = "█" * int(max(0, avg) / 2) if avg > 0 else "▒" * int(abs(avg) / 2)
            print(f"   {portföy:8s}: {avg:+6.1f}% ort | {wr:5.1f}% win | n={n:3d} | toplam={tot:+7.1f}% {bar}")

    ozet = build_summary(matrix)
    print(f"\n{'='*65}")
    print(f"🏆 En karlı tema: {ozet['en_karli_tema']}")
    print(f"💀 En kötü tema:  {ozet['en_kotu_tema']}")
    print(f"\nPortföy × En İyi Tema:")
    for p, t in ozet["portfoy_en_iyi_tema"].items():
        print(f"   {p:8s}: {t or 'Veri yok'}")


# ── Trade Açılışında Tema Etiketi Ekle ────────────────────────────────────────

def tag_trade_with_theme(trade_data: dict) -> dict:
    """
    Yeni trade açılırken çağrılır.
    trade_data'ya 'aktif_tema' alanı ekler.
    """
    entry_date = trade_data.get("giris_tarihi", datetime.now().strftime("%Y-%m-%d"))
    tema = get_active_theme_on_date(entry_date[:10])
    trade_data["aktif_tema"] = tema
    return trade_data


# ── Ana Çalışma ───────────────────────────────────────────────────────────────

def run():
    print("[TemaMatrix] Analiz başlıyor...")
    matrix = analyze_trades_by_theme()

    if not matrix:
        print("[TemaMatrix] Henüz yeterli trade verisi yok.")
        # Boş matris yaz
        save_matrix({})
        return

    print_matrix_report(matrix)
    save_matrix(matrix)


if __name__ == "__main__":
    run()
