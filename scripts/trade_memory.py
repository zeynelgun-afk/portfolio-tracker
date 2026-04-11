#!/usr/bin/env python3
"""
Finzora AI — Episodik Bellek Sistemi (Katman 1)
================================================
Kapanmış trade'leri vektör uzayında saklar ve benzer geçmiş
durumları yeni analizlere bağlam olarak enjekte eder.

Kullanım:
  python3 scripts/trade_memory.py --rebuild          # Bellekleri yeniden oluştur
  python3 scripts/trade_memory.py --query "NVDA momentum breakout RSI 70"
  python3 scripts/trade_memory.py --query-trade SWING-020
  python3 scripts/trade_memory.py --stats
"""

import json
import os
import sys
import math
import argparse
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── Yollar ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
CLOSED_SWING  = BASE / "data" / "swing"    / "closed.json"
CLOSED_PORT   = BASE / "data" / "transactions.csv"
MEMORY_DIR    = BASE / "data" / "episodic_memory"
INDEX_FILE    = MEMORY_DIR / "trade_index.json"
TFIDF_FILE    = MEMORY_DIR / "tfidf_vectors.json"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# 1. TRADE → METİN DÖNÜŞÜMÜ
# ══════════════════════════════════════════════════════════════════════════════

SEKTÖR_MAP = {
    # Teknoloji
    "NVDA": "teknoloji yarı_iletken AI",
    "AMD":  "teknoloji yarı_iletken AI",
    "AMAT": "teknoloji yarı_iletken ekipman",
    "GOOGL":"teknoloji büyük_teknoloji AI bulut",
    "META": "teknoloji sosyal_medya AI",
    "MSFT": "teknoloji büyük_teknoloji bulut",
    "AAPL": "teknoloji donanım tüketici",
    "ZS":   "teknoloji siber_güvenlik bulut",
    "CRWD": "teknoloji siber_güvenlik",
    "NET":  "teknoloji ağ bulut",
    # Savunma / Uzay
    "KTOS": "savunma uzay teknoloji",
    "LASR": "savunma lazer yüksek_riskli",
    "RKLB": "savunma uzay fırlatma",
    "LMT":  "savunma havacılık",
    "RTX":  "savunma havacılık",
    # Enerji
    "XOM":  "enerji petrol büyük_şirket",
    "SM":   "enerji petrol_gaz küçük_cap",
    "KOS":  "enerji petrol açık_deniz deep_value",
    "XLE":  "enerji sektör_ETF",
    "CEG":  "enerji nükleer kamu",
    "HAL":  "enerji petrol_hizmet",
    # Sanayi
    "CAT":  "sanayi ağır_makine döngüsel",
    "GE":   "sanayi havacılık güç",
    "DE":   "sanayi tarım_makinesi döngüsel",
    # Finans
    "JPM":  "finans büyük_banka",
    "GS":   "finans yatırım_bankası",
    # Tüketici
    "WMT":  "tüketici defansif perakende",
    "MO":   "tüketici sigara temettü defansif",
    # Gayrimenkul
    "AMT":  "gayrımenkul kule REIT temettü",
    # Telekom
    "VZ":   "telekom temettü defansif",
    # Maden/Emtia
    "FCX":  "emtia bakır maden döngüsel",
    "RGLD": "emtia altın royalty",
    "GLD":  "emtia altın ETF",
}

def sembol_sektor(sembol: str) -> str:
    return SEKTÖR_MAP.get(sembol.upper(), "bilinmiyor")


def trade_to_text(trade: dict) -> str:
    """Bir trade kaydını aranabilir metin belgesine çevirir."""
    sembol = trade.get("sembol", "")
    giris  = trade.get("giris_fiyati", trade.get("giris", 0))
    cikis  = trade.get("cikis_fiyati", trade.get("cikis", 0))
    pnl    = trade.get("kar_zarar_yuzde", trade.get("pnl_yuzde", 0))
    gun    = trade.get("tutulan_gun", trade.get("gun", 0))
    sonuc  = trade.get("sonuc", "BILINMIYOR")
    sektor = sembol_sektor(sembol)

    giris_sebebi = trade.get("giris_nedeni",
                   trade.get("entry_reason",
                   trade.get("tez", "")))

    cikis_sebebi = trade.get("cikis_nedeni",
                   trade.get("exit_reason", ""))

    ders = trade.get("ders",
           trade.get("lessons", ""))

    tarama = trade.get("tarama_yontemi",
             trade.get("scan_method", ""))

    kataliz = trade.get("katalizor",
              trade.get("catalyst", ""))

    pnl_sinif = "büyük_kazanç" if pnl >= 10 else \
                "orta_kazanç"  if pnl >= 5  else \
                "küçük_kazanç" if pnl > 0   else \
                "küçük_zarar"  if pnl >= -5 else \
                "büyük_zarar"

    gun_sinif = "çok_kısa" if gun <= 3 else \
                "kısa"      if gun <= 7 else \
                "orta"      if gun <= 12 else \
                "uzun"

    parts = [
        f"hisse:{sembol}",
        f"sektör:{sektor}",
        f"sonuç:{sonuc}",
        f"pnl_sınıf:{pnl_sinif}",
        f"pnl:{pnl:+.1f}%",
        f"süre:{gun_sinif} {gun}gün",
    ]

    if tarama:
        parts.append(f"tarama:{tarama}")
    if kataliz:
        parts.append(f"katalizör:{kataliz}")
    if giris_sebebi:
        parts.append(f"giriş_tezi:{giris_sebebi}")
    if cikis_sebebi:
        parts.append(f"çıkış:{cikis_sebebi}")
    if ders:
        parts.append(f"ders:{ders}")

    return " ".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# 2. TF-IDF VEKTÖRLEŞTİRME
# ══════════════════════════════════════════════════════════════════════════════

def tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w%+\-öüşığçÖÜŞIĞÇ:]", " ", text)
    tokens = text.split()
    # Fazla kısa tokenleri çıkar
    return [t for t in tokens if len(t) > 1]


def build_tfidf(documents: list[str]) -> tuple[list[dict], dict]:
    """Basit TF-IDF vektörleri hesaplar."""
    N = len(documents)
    tokenized = [tokenize(doc) for doc in documents]

    # IDF hesapla
    df = defaultdict(int)
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1

    idf = {}
    for term, freq in df.items():
        idf[term] = math.log((N + 1) / (freq + 1)) + 1.0

    # TF-IDF vektörleri
    vectors = []
    for tokens in tokenized:
        tf = defaultdict(float)
        for t in tokens:
            tf[t] += 1.0
        # Normalize TF
        total = len(tokens) if tokens else 1
        vec = {}
        for term, cnt in tf.items():
            vec[term] = (cnt / total) * idf.get(term, 1.0)
        vectors.append(vec)

    return vectors, idf


def cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot = sum(vec_a[t] * vec_b[t] for t in common)
    norm_a = math.sqrt(sum(v*v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v*v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def query_vector(query: str, idf: dict) -> dict:
    """Sorgu metnini TF-IDF vektörüne çevirir."""
    tokens = tokenize(query)
    tf = defaultdict(float)
    for t in tokens:
        tf[t] += 1.0
    total = len(tokens) if tokens else 1
    vec = {}
    for term, cnt in tf.items():
        vec[term] = (cnt / total) * idf.get(term, 1.0)
    return vec


# ══════════════════════════════════════════════════════════════════════════════
# 3. VERİ YÜKLEME
# ══════════════════════════════════════════════════════════════════════════════

def load_swing_trades() -> list[dict]:
    """Kapanmış swing trade'leri yükler."""
    if not CLOSED_SWING.exists():
        return []
    with open(CLOSED_SWING, encoding="utf-8") as f:
        data = json.load(f)
    trades = data.get("kapatilan_pozisyonlar", [])
    for t in trades:
        t["_kaynak"] = "swing"
        if "id" not in t:
            t["id"] = f"SWING-{t.get('sembol','')}_{t.get('giris_tarihi','')}"
    return trades


def load_all_trades() -> list[dict]:
    """Tüm kaynaklardan trade'leri birleştirir."""
    trades = []
    trades.extend(load_swing_trades())
    # İleride portföy trade'leri de eklenecek
    return trades


# ══════════════════════════════════════════════════════════════════════════════
# 4. İNDEKS OLUŞTURMA / YÜKLEME
# ══════════════════════════════════════════════════════════════════════════════

def rebuild_index():
    """Tüm trade'lerden sıfırdan indeks oluşturur."""
    print("🔄 Episodik bellek yeniden oluşturuluyor...")

    trades = load_all_trades()
    if not trades:
        print("⚠️  Hiç kapanmış trade bulunamadı.")
        return

    documents = [trade_to_text(t) for t in trades]
    vectors, idf = build_tfidf(documents)

    # İndeks kaydet
    index = {
        "son_guncelleme": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "trade_sayisi": len(trades),
        "trades": []
    }

    for trade, doc, vec in zip(trades, documents, vectors):
        index["trades"].append({
            "id":      trade.get("id", ""),
            "sembol":  trade.get("sembol", ""),
            "sonuc":   trade.get("sonuc", ""),
            "pnl":     trade.get("kar_zarar_yuzde", 0),
            "gun":     trade.get("tutulan_gun", 0),
            "tarih":   trade.get("cikis_tarihi", trade.get("giris_tarihi", "")),
            "metin":   doc,
            "ders":    trade.get("ders", ""),
            "sektor":  sembol_sektor(trade.get("sembol", "")),
            "kaynak":  trade.get("_kaynak", ""),
        })

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    tfidf_data = {
        "idf":     idf,
        "vectors": vectors
    }
    with open(TFIDF_FILE, "w", encoding="utf-8") as f:
        json.dump(tfidf_data, f, ensure_ascii=False)

    print(f"✅ {len(trades)} trade bellekte indekslendi.")
    print(f"   📁 {INDEX_FILE}")
    print(f"   📊 Kelime hazinesi: {len(idf)} terim")

    # Hızlı istatistik
    kazanc = [t for t in trades if t.get("sonuc") == "KAZANÇ"]
    zarar  = [t for t in trades if t.get("sonuc") == "ZARAR"]
    print(f"\n   📈 Kazanç: {len(kazanc)} | 📉 Zarar: {len(zarar)}")
    if kazanc:
        avg_k = sum(t["kar_zarar_yuzde"] for t in kazanc) / len(kazanc)
        print(f"   Ort. kazanç: +{avg_k:.1f}%")
    if zarar:
        avg_z = sum(t["kar_zarar_yuzde"] for t in zarar) / len(zarar)
        print(f"   Ort. zarar: {avg_z:.1f}%")


def load_index() -> tuple[dict, dict, list[dict]]:
    """Kaydedilmiş indeksi yükler."""
    if not INDEX_FILE.exists() or not TFIDF_FILE.exists():
        raise FileNotFoundError(
            "Bellek indeksi bulunamadı. Önce --rebuild çalıştırın."
        )
    with open(INDEX_FILE, encoding="utf-8") as f:
        index = json.load(f)
    with open(TFIDF_FILE, encoding="utf-8") as f:
        tfidf = json.load(f)
    return index, tfidf["idf"], tfidf["vectors"]


# ══════════════════════════════════════════════════════════════════════════════
# 5. SORGULAMA — ANA FONKSİYON
# ══════════════════════════════════════════════════════════════════════════════

def query_memory(query_text: str, top_k: int = 5,
                 filtre_sonuc: str = None) -> list[dict]:
    """
    Sorguya en benzer geçmiş trade'leri döndürür.

    Parametreler:
        query_text   : Arama metni (ör. "NVDA breakout momentum RSI 70")
        top_k        : Döndürülecek trade sayısı
        filtre_sonuc : "KAZANÇ" veya "ZARAR" ile filtrele (opsiyonel)

    Döndürür:
        [{"id", "sembol", "sonuc", "pnl", "ders", "skor", ...}, ...]
    """
    index, idf, vectors = load_index()
    q_vec = query_vector(query_text, idf)
    trades = index["trades"]

    scores = []
    for i, (trade, vec) in enumerate(zip(trades, vectors)):
        if filtre_sonuc and trade["sonuc"] != filtre_sonuc:
            continue
        sim = cosine_similarity(q_vec, vec)
        scores.append((sim, i, trade))

    scores.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sim, idx, trade in scores[:top_k]:
        result = dict(trade)
        result["benzerlik_skoru"] = round(sim, 4)
        results.append(result)

    return results


def format_memory_context(results: list[dict], baslik: str = "") -> str:
    """
    Sorgu sonuçlarını Claude için okunabilir bağlam metnine çevirir.
    Bu metin doğrudan prompt'a enjekte edilebilir.
    """
    if not results:
        return "📭 Benzer geçmiş trade bulunamadı."

    lines = [f"## 🧠 Episodik Bellek — {baslik}", ""]
    for i, t in enumerate(results, 1):
        pnl_emoji = "📈" if t["pnl"] >= 0 else "📉"
        lines.append(
            f"**{i}. {t['sembol']}** [{t['sonuc']}] "
            f"{pnl_emoji} {t['pnl']:+.1f}% | "
            f"{t['gun']} gün | "
            f"Benzerlik: {t['benzerlik_skoru']:.0%}"
        )
        if t.get("ders"):
            lines.append(f"   💡 *{t['ders'][:200]}*")
        lines.append("")

    return "\n".join(lines)


def query_similar_to_trade(trade_id: str, top_k: int = 5) -> list[dict]:
    """Belirli bir trade'e benzer diğer trade'leri bulur."""
    index, idf, vectors = load_index()
    trades = index["trades"]

    source_trade = next(
        (t for t in trades if t["id"] == trade_id), None
    )
    if not source_trade:
        raise ValueError(f"Trade bulunamadı: {trade_id}")

    q_vec = query_vector(source_trade["metin"], idf)
    scores = []
    for i, (trade, vec) in enumerate(zip(trades, vectors)):
        if trade["id"] == trade_id:
            continue
        sim = cosine_similarity(q_vec, vec)
        scores.append((sim, i, trade))

    scores.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sim, idx, trade in scores[:top_k]:
        result = dict(trade)
        result["benzerlik_skoru"] = round(sim, 4)
        results.append(result)

    return results


# ══════════════════════════════════════════════════════════════════════════════
# 6. İSTATİSTİKLER
# ══════════════════════════════════════════════════════════════════════════════

def print_stats():
    """Bellek istatistiklerini gösterir."""
    index, idf, vectors = load_index()
    trades = index["trades"]

    print(f"\n{'='*55}")
    print(f"  📊 FİNZORA EPİSODİK BELLEK — İSTATİSTİKLER")
    print(f"{'='*55}")
    print(f"  Son güncelleme : {index['son_guncelleme']}")
    print(f"  Toplam trade   : {len(trades)}")
    print(f"  Kelime hazinesi: {len(idf)} terim")
    print()

    kazanc = [t for t in trades if t["sonuc"] == "KAZANÇ"]
    zarar  = [t for t in trades if t["sonuc"] == "ZARAR"]

    print(f"  📈 KAZANÇ: {len(kazanc)} trade")
    if kazanc:
        avg_k = sum(t["pnl"] for t in kazanc) / len(kazanc)
        max_k = max(t["pnl"] for t in kazanc)
        print(f"     Ortalama: +{avg_k:.1f}%  Max: +{max_k:.1f}%")

    print(f"\n  📉 ZARAR: {len(zarar)} trade")
    if zarar:
        avg_z = sum(t["pnl"] for t in zarar) / len(zarar)
        min_z = min(t["pnl"] for t in zarar)
        print(f"     Ortalama: {avg_z:.1f}%  Max: {min_z:.1f}%")

    # Sektör bazlı başarı
    print(f"\n  🏢 SEKTÖR BAZLI PERFORMANS:")
    sektor_sonuc = defaultdict(lambda: {"k": 0, "z": 0, "pnl": []})
    for t in trades:
        ana_sektor = t.get("sektor", "bilinmiyor").split()[0]
        if t["sonuc"] == "KAZANÇ":
            sektor_sonuc[ana_sektor]["k"] += 1
        else:
            sektor_sonuc[ana_sektor]["z"] += 1
        sektor_sonuc[ana_sektor]["pnl"].append(t["pnl"])

    for sektor, data in sorted(sektor_sonuc.items()):
        total = data["k"] + data["z"]
        wr = data["k"] / total * 100
        avg_pnl = sum(data["pnl"]) / len(data["pnl"])
        print(f"     {sektor:<15} {total:>2} trade | "
              f"WR: {wr:.0f}% | Ort. PnL: {avg_pnl:+.1f}%")

    # En iyi ve en kötü
    sorted_trades = sorted(trades, key=lambda x: x["pnl"], reverse=True)
    print(f"\n  🏆 EN İYİ 3:")
    for t in sorted_trades[:3]:
        print(f"     {t['sembol']:<6} +{t['pnl']:.1f}% ({t['gun']} gün)")
    print(f"\n  💀 EN KÖTÜ 3:")
    for t in sorted_trades[-3:]:
        print(f"     {t['sembol']:<6} {t['pnl']:.1f}% ({t['gun']} gün)")

    print(f"{'='*55}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 7. PROMPT ENJEKSİYON FONKSİYONU (Ana entegrasyon noktası)
# ══════════════════════════════════════════════════════════════════════════════

def get_memory_for_prompt(setup_description: str, top_k: int = 4) -> str:
    """
    Yeni bir trade setup'ı için ilgili geçmiş deneyimleri döndürür.
    Bu fonksiyon sabah prompta, seans promptlarına ve swing taramaya enjekte edilir.

    Kullanım:
        context = get_memory_for_prompt("NVDA breakout RSI 68 AI momentum")
        # context'i Claude promptuna ekle
    """
    try:
        results = query_memory(setup_description, top_k=top_k)
        if not results:
            return ""

        # Ayır: benzer kazananlar ve benzer kaybedenler
        kazananlar = [r for r in results if r["sonuc"] == "KAZANÇ"]
        kaybedenler = [r for r in results if r["sonuc"] == "ZARAR"]

        lines = ["---", "🧠 **EPİSODİK BELLEK — Benzer Geçmiş Durumlar:**", ""]

        if kazananlar:
            lines.append("✅ Benzer başarılı setup'lar:")
            for r in kazananlar[:2]:
                lines.append(
                    f"  • {r['sembol']} → +{r['pnl']:.1f}% ({r['gun']} gün) | "
                    f"{r.get('ders', '')[:120]}"
                )

        if kaybedenler:
            lines.append("")
            lines.append("⚠️ Benzer başarısız setup'lar — UYARI:")
            for r in kaybedenler[:2]:
                lines.append(
                    f"  • {r['sembol']} → {r['pnl']:.1f}% ({r['gun']} gün) | "
                    f"{r.get('ders', '')[:120]}"
                )

        lines.append("---")
        return "\n".join(lines)

    except FileNotFoundError:
        return ""  # İndeks yoksa sessizce atla


# ══════════════════════════════════════════════════════════════════════════════
# 8. CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — Episodik Bellek Sistemi"
    )
    parser.add_argument("--rebuild", action="store_true",
                        help="Bellekleri sıfırdan yeniden oluştur")
    parser.add_argument("--query", type=str,
                        help="Benzer trade'leri sorgula")
    parser.add_argument("--query-trade", type=str,
                        help="Belirli bir trade'e benzer olanları bul")
    parser.add_argument("--top", type=int, default=5,
                        help="Döndürülecek sonuç sayısı")
    parser.add_argument("--stats", action="store_true",
                        help="Bellek istatistiklerini göster")
    parser.add_argument("--prompt-inject", type=str,
                        help="Prompt enjeksiyonu için bağlam üret")

    args = parser.parse_args()

    if args.rebuild:
        rebuild_index()

    elif args.query:
        results = query_memory(args.query, top_k=args.top)
        print(f"\n🔍 Sorgu: '{args.query}'")
        print(f"📊 {len(results)} benzer trade bulundu:\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['benzerlik_skoru']:.0%}] "
                  f"{r['sembol']} {r['sonuc']} "
                  f"{r['pnl']:+.1f}% | {r['gun']} gün")
            if r.get("ders"):
                print(f"   💡 {r['ders'][:200]}")
            print()

    elif args.query_trade:
        results = query_similar_to_trade(args.query_trade, top_k=args.top)
        print(f"\n🔗 '{args.query_trade}' trade'ine benzer diğerleri:\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['benzerlik_skoru']:.0%}] "
                  f"{r['sembol']} {r['sonuc']} {r['pnl']:+.1f}%")
            if r.get("ders"):
                print(f"   💡 {r['ders'][:200]}")
            print()

    elif args.stats:
        print_stats()

    elif args.prompt_inject:
        context = get_memory_for_prompt(args.prompt_inject)
        print(context if context else "(Yeterli bellek verisi yok)")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
