#!/usr/bin/env python3
"""
Finzora AI — Bellek Güncelleyici & Prompt Entegrasyon Modülü
=============================================================
Her kapanan trade sonrası çağrılır. Bellekleri günceller,
sabah raporu ve seans promptlarına bağlam enjekte eder.

Kullanım:
  python3 scripts/memory_update.py                   # Güncelle + kontrol et
  python3 scripts/memory_update.py --morning         # Sabah bağlamı üret
  python3 scripts/memory_update.py --setup "NVDA breakout RSI 68"
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from trade_memory import (
    rebuild_index,
    get_memory_for_prompt,
    query_memory,
    load_index,
    MEMORY_DIR,
    INDEX_FILE
)

CLOSED_SWING = BASE / "data" / "swing" / "closed.json"


# ══════════════════════════════════════════════════════════════════════════════
# GÜNCELLİK KONTROLÜ
# ══════════════════════════════════════════════════════════════════════════════

def index_guncel_mi() -> bool:
    """İndeks dosyasının closed.json'dan daha yeni olup olmadığını kontrol eder."""
    if not INDEX_FILE.exists():
        return False
    index_mtime  = INDEX_FILE.stat().st_mtime
    closed_mtime = CLOSED_SWING.stat().st_mtime if CLOSED_SWING.exists() else 0
    return index_mtime >= closed_mtime


def guncelle_gerekirse():
    """Veri değiştiyse indeksi yeniden oluşturur."""
    if index_guncel_mi():
        print("✅ Bellek indeksi güncel.")
    else:
        print("🔄 Veri güncellendi, bellek yeniden oluşturuluyor...")
        rebuild_index()


# ══════════════════════════════════════════════════════════════════════════════
# SABAH BAĞLAM RAPORU
# ══════════════════════════════════════════════════════════════════════════════

def sabah_bellegi_uret() -> str:
    """
    Sabah raporuna enjekte edilecek bellek özetini üretir.
    Aktif portföy ve watchlist bazlı bağlam çeker.
    """
    try:
        index, idf, vectors = load_index()
        trades = index["trades"]
    except FileNotFoundError:
        return ""

    # Portföy dosyalarından aktif hisseleri oku
    aktif_semboller = set()
    for port in ["balanced", "aggressive", "dividend"]:
        port_file = BASE / "data" / "portfolios" / f"{port}.json"
        if port_file.exists():
            with open(port_file, encoding="utf-8") as f:
                data = json.load(f)
            for poz in data.get("pozisyonlar", []):
                aktif_semboller.add(poz.get("sembol", ""))

    # Watchlist'i oku
    watchlist_file = BASE / "data" / "watchlist.json"
    watchlist_semboller = []
    if watchlist_file.exists():
        with open(watchlist_file, encoding="utf-8") as f:
            wl = json.load(f)
        for item in wl.get("izleme_listesi", [])[:5]:
            watchlist_semboller.append(item.get("sembol", ""))

    lines = [
        "=" * 60,
        "  🧠 EPİSODİK BELLEK — SABAH BRİFİNGİ",
        f"  {datetime.now().strftime('%d %B %Y')}",
        "=" * 60,
        "",
    ]

    # Genel istatistik
    kazanc = [t for t in trades if t["sonuc"] == "KAZANÇ"]
    zarar  = [t for t in trades if t["sonuc"] == "ZARAR"]
    if trades:
        wr = len(kazanc) / len(trades) * 100
        lines.append(f"  📊 Bellek: {len(trades)} trade | WR: {wr:.0f}%")

    # Sektör uyarıları (kaybeden sektörler)
    sektor_zarar = {}
    for t in zarar:
        ana = t.get("sektor", "bilinmiyor").split()[0]
        sektor_zarar[ana] = sektor_zarar.get(ana, 0) + 1

    kotu_sektorler = [s for s, c in sektor_zarar.items() if c >= 2]
    if kotu_sektorler:
        lines.append(f"  ⚠️  Çok kayıp verilen sektörler: {', '.join(kotu_sektorler)}")

    # Aktif portföyde bulunan semboller için geçmiş kontrol
    if aktif_semboller:
        lines.append("")
        lines.append("  📁 AKTİF POZİSYONLAR — Geçmiş Deneyim:")
        for sembol in sorted(aktif_semboller):
            ilgili = [t for t in trades if t["sembol"] == sembol]
            if ilgili:
                avg_pnl = sum(t["pnl"] for t in ilgili) / len(ilgili)
                wr_s = sum(1 for t in ilgili if t["sonuc"] == "KAZANÇ") / len(ilgili) * 100
                lines.append(
                    f"     {sembol:<6}: {len(ilgili)} geçmiş trade | "
                    f"WR: {wr_s:.0f}% | Ort: {avg_pnl:+.1f}%"
                )

    # Watchlist adayları için ilgili geçmiş dersler
    if watchlist_semboller:
        lines.append("")
        lines.append("  👁️  WATCHLIST ADAYLARI — Geçmiş Benzer Durumlar:")
        for sembol in watchlist_semboller[:3]:
            context = get_memory_for_prompt(sembol, top_k=2)
            if context and "bulunamadı" not in context:
                ilgili_kisim = "\n".join(
                    l for l in context.split("\n") if "•" in l
                )
                if ilgili_kisim:
                    lines.append(f"     [{sembol}]: {ilgili_kisim.strip()[:200]}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# SETUP BAZLI BAĞLAM
# ══════════════════════════════════════════════════════════════════════════════

def setup_bellegi_uret(setup_aciklamasi: str) -> str:
    """
    Belirli bir trade setup'ı için geçmiş deneyimleri ve uyarıları döndürür.
    Swing tarama ve portföy kararlarında kullanılır.
    """
    guncelle_gerekirse()

    context = get_memory_for_prompt(setup_aciklamasi, top_k=5)
    if not context:
        return "📭 Bu setup için yeterli geçmiş veri yok."

    # Ek: En alakalı ders özeti
    results = query_memory(setup_aciklamasi, top_k=5)
    dersler = [r["ders"] for r in results if r.get("ders") and r["benzerlik_skoru"] > 0.05]

    if dersler:
        context += "\n\n📚 **Ana Dersler:**\n"
        for ders in dersler[:3]:
            context += f"  → {ders[:150]}\n"

    return context


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — Bellek Güncelleyici"
    )
    parser.add_argument("--morning", action="store_true",
                        help="Sabah brifing raporunu üret")
    parser.add_argument("--setup", type=str,
                        help="Setup için geçmiş bağlam üret")
    parser.add_argument("--force-rebuild", action="store_true",
                        help="Zorla yeniden oluştur")

    args = parser.parse_args()

    if args.force_rebuild:
        rebuild_index()
    else:
        guncelle_gerekirse()

    if args.morning:
        rapor = sabah_bellegi_uret()
        print(rapor)

    elif args.setup:
        context = setup_bellegi_uret(args.setup)
        print(context)

    else:
        print("💡 Kullanım: --morning | --setup 'açıklama' | --force-rebuild")


if __name__ == "__main__":
    main()
