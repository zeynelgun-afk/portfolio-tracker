#!/usr/bin/env python3
"""
Finzora AI — Sentiment Entegrasyon Sistemi (Katman 7)
======================================================
FMP haber akışı + Twitter (opsiyonel) → sektör sentiment skoru (1-10).
Her sabah çalışır, theme_scores.json günceller, sabah raporuna bağlam sağlar.

Kullanım:
  python3 scripts/sentiment_engine.py              # Tam tarama
  python3 scripts/sentiment_engine.py --inject     # Prompt enjeksiyonu
  python3 scripts/sentiment_engine.py --symbol NVDA # Tek hisse
  python3 scripts/sentiment_engine.py --twitter    # Twitter da dahil et
"""

import json
import re
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE         = Path(__file__).parent.parent
FMP_KEY      = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE     = "https://financialmodelingprep.com/stable"
RAPIDAPI_KEY = "fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7"

THEME_FILE   = BASE / "data" / "theme_scores.json"
SENTIMENT_FILE = BASE / "data" / "sentiment_scores.json"


# ══════════════════════════════════════════════════════════════════════════════
# 1. KELİME BAZLI SENTIMENT SINIFLANDIRICI
# ══════════════════════════════════════════════════════════════════════════════

POZITIF_KELIMELER = {
    # Güçlü pozitif (ağırlık 2)
    "güçlü": 2, "strong": 2, "beat": 2, "surge": 2, "rally": 2,
    "breakout": 2, "record": 2, "best": 2, "soar": 2, "boom": 2,
    "bullish": 2, "upgrade": 2, "buy": 1.5, "outperform": 2,
    "growth": 1.5, "profit": 1.5, "gain": 1.5, "rise": 1.5,
    "up": 1, "high": 1, "positive": 1.5, "optimistic": 1.5,
    "opportunity": 1.5, "recovery": 1.5, "momentum": 1.5,
    "demand": 1, "expansion": 1.5, "win": 1.5, "success": 1.5,
    "milestone": 1.5, "innovation": 1, "ai": 1, "artificial intelligence": 1,
    "undervalued": 1.5, "cheap": 1, "bargain": 1.5,
}

NEGATIF_KELIMELER = {
    # Güçlü negatif (ağırlık 2)
    "crash": 2, "collapse": 2, "plunge": 2, "fall": 1.5, "drop": 1.5,
    "bearish": 2, "downgrade": 2, "sell": 1.5, "underperform": 2,
    "loss": 1.5, "debt": 1, "concern": 1.5, "risk": 1, "warning": 2,
    "recession": 2, "inflation": 1.5, "tariff": 1.5, "war": 1.5,
    "geopolitical": 1, "volatile": 1, "uncertainty": 1.5,
    "miss": 2, "disappoint": 2, "weak": 2, "decline": 1.5,
    "cut": 1.5, "layoff": 2, "bankrupt": 2, "fraud": 2, "lawsuit": 1.5,
    "overvalued": 1.5, "bubble": 2, "short": 1, "puts": 1,
}

def metin_sentiment_skoru(baslik: str, icerik: str = "") -> float:
    """
    Başlık ve içerikten -1 ile +1 arası sentiment skoru üretir.
    +1 = çok pozitif, -1 = çok negatif, 0 = nötr
    """
    metin = (baslik + " " + icerik).lower()

    poz = sum(v for k, v in POZITIF_KELIMELER.items() if k in metin)
    neg = sum(v for k, v in NEGATIF_KELIMELER.items() if k in metin)

    toplam = poz + neg
    if toplam == 0:
        return 0.0

    ham_skor = (poz - neg) / toplam
    # Normalize: [-1, +1] → daha güvenilir aralık
    return round(max(-1.0, min(1.0, ham_skor)), 3)


def skor_to_1_10(skor: float) -> float:
    """[-1, +1] → [1, 10] dönüşümü."""
    return round(5.5 + skor * 4.5, 1)


# ══════════════════════════════════════════════════════════════════════════════
# 2. SEKTÖR ETF → SEMBOl HARİTASI
# ══════════════════════════════════════════════════════════════════════════════

SEKTOR_SEMBOLLERI = {
    "Teknoloji":     ["XLK", "NVDA", "AMD", "AMAT", "KLAC", "MSFT", "AAPL", "GOOGL"],
    "Enerji":        ["XLE", "XOM", "CVX", "SM", "KOS", "OXY", "HAL"],
    "Savunma":       ["LMT", "RTX", "NOC", "GD", "KTOS", "RKLB"],
    "Altın/Emtia":   ["GLD", "NEM", "GOLD", "RGLD", "FCX", "AEM"],
    "Finans":        ["XLF", "JPM", "GS", "BAC", "MS"],
    "Sanayi":        ["XLI", "CAT", "GE", "DE", "HON", "GEV"],
    "Sağlık":        ["XLV", "JNJ", "UNH", "LLY", "ABBV"],
    "TüketicD":      ["XLY", "AMZN", "TSLA", "HD", "NKE"],
    "TüketicS":      ["XLP", "WMT", "PG", "KO", "MO"],
    "Gayrimenkul":   ["XLRE", "AMT", "PLD", "O"],
}

# Portföy sembolleri — JSON dosyalarından dinamik olarak okunur
def _portfoy_sembollerini_oku() -> list[str]:
    """Tüm portföy JSON'larından aktif sembolleri döndür."""
    import json as _json
    _root = Path(__file__).parent.parent
    semboller = set()
    for fp in ["data/portfolios/balanced.json",
               "data/portfolios/aggressive.json",
               "data/portfolios/dividend.json"]:
        try:
            with open(_root / fp, encoding="utf-8") as f:
                d = _json.load(f)
            semboller.update(p["sembol"] for p in d.get("pozisyonlar", []))
        except Exception:
            pass
    # Fallback — dosya okunamazsa eski liste
    return list(semboller) or ["MO", "DUK", "CI", "NEE", "VZ", "T", "MRK", "OKE"]

PORTFOY_SEMBOLLERI = _portfoy_sembollerini_oku()


# ══════════════════════════════════════════════════════════════════════════════
# 3. FMP HABER ÇEKİMİ
# ══════════════════════════════════════════════════════════════════════════════

def fmp_haber_cek(semboller: list[str], limit: int = 50) -> list[dict]:
    """Verilen semboller için FMP'den son haberleri çeker."""
    sembol_str = ",".join(semboller[:15])  # Max 15 sembol per request
    params = urllib.parse.urlencode({
        "symbols": sembol_str,
        "limit":   limit,
        "apikey":  FMP_KEY,
    })
    url = f"{FMP_BASE}/news/stock?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FinzoraAI/7.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠️  FMP haber hatası: {e}")
        return []


def haberler_filtrele(haberler: list[dict], saat_sinir: int = 24) -> list[dict]:
    """Son N saatteki haberleri filtreler."""
    sinir = datetime.now() - timedelta(hours=saat_sinir)
    guncel = []
    for h in haberler:
        tarih_str = h.get("publishedDate", "")[:19]
        try:
            tarih = datetime.strptime(tarih_str, "%Y-%m-%d %H:%M:%S")
            if tarih >= sinir:
                guncel.append(h)
        except Exception:
            guncel.append(h)  # Tarih parse hatası → dahil et
    return guncel


# ══════════════════════════════════════════════════════════════════════════════
# 4. TWİTTER VERİSİ (OPSİYONEL)
# ══════════════════════════════════════════════════════════════════════════════

TAKIP_HESAPLARI = {
    "CheddarFlow":    "1507417589705633793",
    "Jake__Wujastyk": "887754279125221378",
    "RyanDetrick":    None,  # ID henüz çekilmedi
    "VolSignals":     None,
    "TrendSpider":    None,
}

def twitter_tweet_cek(user_id: str, count: int = 15) -> list[str]:
    """RapidAPI ile tweet'leri çeker."""
    try:
        url = f"https://twitter241.p.rapidapi.com/user-tweets?user={user_id}&count={count}"
        req = urllib.request.Request(url, headers={
            "x-rapidapi-host": "twitter241.p.rapidapi.com",
            "x-rapidapi-key":  RAPIDAPI_KEY,
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read())

        # Timeline'dan tweet metinlerini çıkar
        tweets = []
        def ara(obj, derinlik=0):
            if derinlik > 10 or len(tweets) >= count:
                return
            if isinstance(obj, dict):
                txt = obj.get("full_text", "")
                if txt and len(txt) > 20 and not txt.startswith("RT @"):
                    tweets.append(txt)
                for v in obj.values():
                    ara(v, derinlik + 1)
            elif isinstance(obj, list):
                for item in obj:
                    ara(item, derinlik + 1)

        ara(d)
        return tweets
    except Exception:
        return []


def twitter_sentiment_topla(hesap_sayisi: int = 3) -> dict:
    """Birden fazla hesabın tweet'lerinden genel market sentiment üretir."""
    tum_tweet = []
    for hesap, uid in list(TAKIP_HESAPLARI.items())[:hesap_sayisi]:
        if uid:
            tweets = twitter_tweet_cek(uid, 10)
            tum_tweet.extend(tweets)
            if tweets:
                print(f"  🐦 @{hesap}: {len(tweets)} tweet")

    if not tum_tweet:
        return {}

    # Tüm tweet'lerden sektör bazlı sentiment
    HISSE_SEKTÖR = {s: sektor for sektor, semblar in SEKTOR_SEMBOLLERI.items()
                    for s in semblar}
    sektor_skorlar = defaultdict(list)

    for tweet in tum_tweet:
        skor = metin_sentiment_skoru(tweet)
        # Hangi sektörlerden bahsediyor?
        tweet_upper = tweet.upper()
        for sembol, sektor in HISSE_SEKTÖR.items():
            if sembol in tweet_upper or f"${sembol}" in tweet_upper:
                sektor_skorlar[sektor].append(skor)

    return {sektor: sum(skorlar) / len(skorlar)
            for sektor, skorlar in sektor_skorlar.items() if skorlar}


# ══════════════════════════════════════════════════════════════════════════════
# 5. ANA SENTIMENT HESAPLAMA
# ══════════════════════════════════════════════════════════════════════════════

def sektor_sentiment_hesapla(twitter_dahil: bool = False) -> dict:
    """
    Her sektör için ağırlıklı sentiment skoru üretir (1-10).
    Ağırlık: Haber sayısı × güncellik × kaynak kalitesi
    """
    print("  📰 Haber verisi çekiliyor...")

    sektor_skorlari = {}
    sektor_haber_sayisi = {}
    sektor_ozet_haberler = {}

    for sektor, sembolar in SEKTOR_SEMBOLLERI.items():
        haberler = fmp_haber_cek(sembolar, limit=30)
        guncel   = haberler_filtrele(haberler, saat_sinir=48)

        if not guncel:
            sektor_skorlari[sektor] = 5.0  # Nötr — veri yok
            sektor_haber_sayisi[sektor] = 0
            continue

        # Her haber için ağırlıklı skor
        agirlikli_toplam = 0.0
        agirlik_toplam   = 0.0
        en_iyi_haberler  = []

        for h in guncel:
            skor    = metin_sentiment_skoru(h.get("title", ""), h.get("text", "")[:200])
            # Ağırlık: daha yeni haber daha önemli
            tarih_str = h.get("publishedDate", "")[:19]
            try:
                tarih   = datetime.strptime(tarih_str, "%Y-%m-%d %H:%M:%S")
                yas_saat = max(0, (datetime.now() - tarih).total_seconds() / 3600)
                agirlik = max(0.2, 1.0 - yas_saat / 48)  # 48 saatte 0.2'ye düşer
            except Exception:
                agirlik = 0.5

            agirlikli_toplam += skor * agirlik
            agirlik_toplam   += agirlik

            # En çarpıcı haberleri kaydet (pozitif veya negatif)
            if abs(skor) > 0.3:
                en_iyi_haberler.append({
                    "baslik": h.get("title", "")[:100],
                    "skor":   skor,
                    "sembol": h.get("symbol", ""),
                    "tarih":  tarih_str[:16],
                })

        ort_skor = agirlikli_toplam / agirlik_toplam if agirlik_toplam > 0 else 0
        sektor_skorlari[sektor] = skor_to_1_10(ort_skor)
        sektor_haber_sayisi[sektor] = len(guncel)
        sektor_ozet_haberler[sektor] = sorted(
            en_iyi_haberler, key=lambda x: abs(x["skor"]), reverse=True
        )[:3]

    # Twitter verisini karıştır (varsa)
    if twitter_dahil:
        print("  🐦 Twitter verisi ekleniyor...")
        twitter_skorlar = twitter_sentiment_topla()
        for sektor, twitter_skor in twitter_skorlar.items():
            if sektor in sektor_skorlari:
                # Twitter %30, FMP %70 ağırlık
                mevcut = (sektor_skorlari[sektor] - 5.5) / 4.5
                karisik = mevcut * 0.70 + twitter_skor * 0.30
                sektor_skorlari[sektor] = skor_to_1_10(karisik)

    return {
        "skorlar":     sektor_skorlari,
        "haber_sayisi": sektor_haber_sayisi,
        "onemli_haberler": sektor_ozet_haberler,
    }


def portfoy_sentiment_hesapla() -> dict:
    """Aktif portföy pozisyonları için bireysel sentiment."""
    haberler = fmp_haber_cek(PORTFOY_SEMBOLLERI, limit=40)
    guncel   = haberler_filtrele(haberler, saat_sinir=24)

    sembol_sentiment = {}
    for sembol in PORTFOY_SEMBOLLERI:
        ilgili = [h for h in guncel if h.get("symbol") == sembol]
        if ilgili:
            skorlar = [metin_sentiment_skoru(h.get("title", "")) for h in ilgili]
            ort = sum(skorlar) / len(skorlar)
            sembol_sentiment[sembol] = {
                "skor_110":   skor_to_1_10(ort),
                "ham_skor":   round(ort, 3),
                "haber_sayisi": len(ilgili),
                "son_baslik": ilgili[0].get("title", "")[:80] if ilgili else "",
            }
        else:
            sembol_sentiment[sembol] = {"skor_110": 5.0, "haber_sayisi": 0}

    return sembol_sentiment


# ══════════════════════════════════════════════════════════════════════════════
# 6. TEMA SKORLARINI GÜNCELLE
# ══════════════════════════════════════════════════════════════════════════════

def theme_scores_guncelle(sektor_data: dict):
    """Mevcut theme_scores.json'ı sentiment verileriyle günceller."""
    skorlar = sektor_data["skorlar"]
    simdi   = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Rotasyon alarmı: 3+ sektör 4'ün altında
    dusuk_sektorler = [s for s, v in skorlar.items() if v < 4.5]
    rotasyon_alarmi = len(dusuk_sektorler) >= 3

    # Aktif tema: En yüksek puanlı sektör
    aktif_tema = max(skorlar, key=skorlar.get) if skorlar else None

    tema_data = {
        "tarih":          simdi,
        "aktif_tema":     aktif_tema,
        "tema_puanlari":  {s: {"sentiment": v, "kaynak": "fmp_news"}
                           for s, v in skorlar.items()},
        "rotasyon_alarmi": rotasyon_alarmi,
        "dusuk_sektorler": dusuk_sektorler,
        "not": f"Sentiment motoru v1.0 | {simdi}"
    }

    with open(THEME_FILE, "w", encoding="utf-8") as f:
        json.dump(tema_data, f, ensure_ascii=False, indent=2)

    return tema_data


# ══════════════════════════════════════════════════════════════════════════════
# 7. SENTIMENT RAPORU
# ══════════════════════════════════════════════════════════════════════════════

def rapor_yazdir(sektor_data: dict, portfoy_data: dict, tema: dict):
    skorlar = sektor_data["skorlar"]
    print(f"\n{'='*62}")
    print(f"  📊 SENTIMENT RAPORU — {datetime.now().strftime('%d %B %Y %H:%M')}")
    print(f"{'='*62}")

    # Sektör sentiment tablosu
    print(f"\n  🏢 SEKTÖR SENTIMENT SKORU (1=Aşırı Negatif, 10=Aşırı Pozitif)\n")
    sirali = sorted(skorlar.items(), key=lambda x: -x[1])
    for sektor, skor in sirali:
        bar_len = int(skor)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        emoji = "🟢" if skor >= 6.5 else "🔴" if skor <= 4.0 else "🟡"
        haber_n = sektor_data["haber_sayisi"].get(sektor, 0)
        print(f"  {emoji} {sektor:<15} {bar} {skor:.1f}  ({haber_n} haber)")

    # Önemli haberler
    print(f"\n  📰 ÖNEMLI HABERLER:")
    for sektor, haberler in sektor_data.get("onemli_haberler", {}).items():
        if haberler:
            h = haberler[0]
            yon = "⬆️" if h["skor"] > 0 else "⬇️"
            print(f"     {yon} [{sektor}] {h['baslik'][:70]}")

    # Portföy sentiment
    if portfoy_data:
        print(f"\n  💼 PORTFöY POZİSYON SENTİMENT:")
        for sembol, data in portfoy_data.items():
            skor = data.get("skor_110", 5.0)
            emoji = "🟢" if skor >= 6.5 else "🔴" if skor <= 4.0 else "🟡"
            n = data.get("haber_sayisi", 0)
            baslik = data.get("son_baslik", "")
            print(f"     {emoji} {sembol:<6} {skor:.1f}/10  ({n} haber)")
            if baslik:
                print(f"        → {baslik[:70]}")

    # Sistem uyarıları
    if tema.get("rotasyon_alarmi"):
        print(f"\n  ⚠️  ROTASYON ALARMI: {', '.join(tema.get('dusuk_sektorler', []))} "
              f"sektörleri zayıf (< 4.5)")

    print(f"\n  🎯 AKTİF TEMA: {tema.get('aktif_tema', '—')}")
    print(f"{'='*62}\n")


def prompt_inject(sektor_data: dict, portfoy_data: dict) -> str:
    """Sabah promptuna enjekte edilecek özet metin."""
    skorlar = sektor_data["skorlar"]
    if not skorlar:
        return ""

    guclu  = [s for s, v in skorlar.items() if v >= 7.0]
    zayif  = [s for s, v in skorlar.items() if v <= 4.0]

    portfoy_alarm = [s for s, d in portfoy_data.items()
                     if d.get("skor_110", 5) <= 3.5]

    lines = [
        f"📊 SENTIMENT ÖZETİ ({datetime.now().strftime('%d.%m.%Y')}):",
        f"Güçlü sektörler: {', '.join(guclu) if guclu else '—'} | "
        f"Zayıf sektörler: {', '.join(zayif) if zayif else '—'}",
    ]
    if portfoy_alarm:
        lines.append(f"⚠️ Portföy alarmi: {', '.join(portfoy_alarm)} — negatif haber akışı")

    # En yüksek ve düşük sektör
    en_guclu = max(skorlar, key=skorlar.get)
    en_zayif = min(skorlar, key=skorlar.get)
    lines.append(f"En güçlü: {en_guclu} ({skorlar[en_guclu]:.1f}/10) | "
                 f"En zayıf: {en_zayif} ({skorlar[en_zayif]:.1f}/10)")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 8. CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — Sentiment Entegrasyon Sistemi"
    )
    parser.add_argument("--twitter", action="store_true",
                        help="Twitter verisi dahil et")
    parser.add_argument("--inject",  action="store_true",
                        help="Prompt enjeksiyonu üret")
    parser.add_argument("--symbol",  type=str,
                        help="Tek hisse sentiment")
    parser.add_argument("--no-save", action="store_true",
                        help="Dosyalara kaydetme")
    args = parser.parse_args()

    if args.symbol:
        sembol = args.symbol.upper()
        haberler = fmp_haber_cek([sembol], 20)
        guncel   = haberler_filtrele(haberler, 48)
        print(f"\n📰 {sembol} — {len(guncel)} güncel haber:\n")
        for h in guncel[:8]:
            skor  = metin_sentiment_skoru(h.get("title", ""))
            emoji = "⬆️ " if skor > 0.2 else "⬇️ " if skor < -0.2 else "➡️ "
            print(f"  {emoji} [{skor:+.2f}] {h['title'][:80]}")
            print(f"       {h['publishedDate'][:16]}")
        return

    # Ana tarama
    sektor_data  = sektor_sentiment_hesapla(args.twitter)
    portfoy_data = portfoy_sentiment_hesapla()

    if not args.no_save:
        tema = theme_scores_guncelle(sektor_data)
        # Tam sonuçları da kaydet
        with open(SENTIMENT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "tarih":       datetime.now().strftime("%Y-%m-%d %H:%M"),
                "sektor":      sektor_data,
                "portfoy":     portfoy_data,
            }, f, ensure_ascii=False, indent=2)
    else:
        tema = {}

    if args.inject:
        print(prompt_inject(sektor_data, portfoy_data))
    else:
        rapor_yazdir(sektor_data, portfoy_data, tema)
        print(f"✅ theme_scores.json ve sentiment_scores.json güncellendi.")


if __name__ == "__main__":
    main()
