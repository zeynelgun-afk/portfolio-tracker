#!/usr/bin/env python3
"""
Finzora AI — Otomatik Post-Trade Analiz Motoru (Katman 2)
==========================================================
Kapanan her trade'i Claude API ile otomatik analiz eder.
Sonuçları closed.json'a yazar, episodik belleği günceller.

Kullanım:
  python3 scripts/auto_trade_review.py --all          # Tüm analiz eksik trade'leri analiz et
  python3 scripts/auto_trade_review.py --id SWING-020 # Tek trade analiz et
  python3 scripts/auto_trade_review.py --report       # Özet rapor göster
  python3 scripts/auto_trade_review.py --insights     # Sistem geneli dersler
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
CLOSED_SWING = BASE / "data" / "swing" / "closed.json"
REPORT_DIR   = BASE / "data" / "episodic_memory"

# Anthropic API — model ve anahtar
CLAUDE_MODEL = "claude-sonnet-4-6"
API_URL      = "https://api.anthropic.com/v1/messages"

# Bu scriptin kendi API anahtarını kullanmaması lazım —
# Claude artifacts ortamında inject edilmiş olur.
# Finzora'da FMP anahtarından farklı olarak bu sistem anahtarı
# environment variable'dan okunur.
import os
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ══════════════════════════════════════════════════════════════════════════════
# 1. CLAUDE API ÇAĞRISI
# ══════════════════════════════════════════════════════════════════════════════

def claude_analiz_et(trade: dict, sistem_ozeti: str = "") -> dict:
    """
    Tek bir trade kaydını Claude ile analiz eder.
    Döndürür: Yapılandırılmış analiz dict'i
    """
    sembol      = trade.get("sembol", "")
    pnl         = trade.get("kar_zarar_yuzde", 0)
    gun         = trade.get("tutulan_gun", 0)
    sonuc       = trade.get("sonuc", "")
    giris_neden = trade.get("giris_nedeni",
                  trade.get("entry_reason",
                  trade.get("tez", "—")))
    cikis_neden = trade.get("cikis_nedeni",
                  trade.get("exit_reason", "—"))
    ders        = trade.get("ders", "—")
    giris_f     = trade.get("giris_fiyati", 0)
    cikis_f     = trade.get("cikis_fiyati", 0)
    kataliz     = trade.get("katalizor",
                  trade.get("catalyst", "—"))
    tarama      = trade.get("tarama_yontemi",
                  trade.get("scan_method", "—"))

    partial = ""
    if trade.get("partial_exits"):
        kısmi = trade["partial_exits"]
        partial = f"\nKısmi çıkışlar: {json.dumps(kısmi, ensure_ascii=False)}"

    sistem_kontekst = ""
    if sistem_ozeti:
        sistem_kontekst = f"\n\nSistem geneli bağlam:\n{sistem_ozeti}"

    prompt = f"""Sen Finzora AI'ın post-trade analiz motorusun.
Kapanan bir swing trade'i analiz edeceksin ve yapılandırılmış bir değerlendirme sunacaksın.

## Trade Bilgileri
- Sembol: {sembol}
- Giriş: {giris_f} | Çıkış: {cikis_f}
- PnL: {pnl:+.2f}%
- Süre: {gun} gün
- Sonuç: {sonuc}
- Giriş nedeni/tezi: {giris_neden}
- Çıkış nedeni: {cikis_neden}
- Katalizör: {kataliz}
- Tarama yöntemi: {tarama}{partial}
- Mevcut ders notu: {ders}{sistem_kontekst}

## Swing Sistemi Kuralları (referans)
- Max 15 gün tutma
- Stop: %5 | Hedef: %10 | Min R:R 2:1
- Giriş: Ichimoku 4/4 + SPY>21EMA + hacim 1.5x+
- K-20: RS dead cat bounce filtresi
- K-19: XLP hariç tut
- Küçük cap (<$2B) trades için ekstra dikkat

## Görevin
Aşağıdaki JSON formatında SADECE JSON döndür, başka hiçbir şey yazma:

{{
  "tez_dogru": true/false,
  "tez_degerlendirme": "Giriş tezinin doğru/yanlış olup olmadığı ve neden (2-3 cümle)",
  "timing_hatasi": true/false,
  "timing_detay": "Timing doğru muydu? Daha iyi giriş/çıkış noktası var mıydı?",
  "stop_uygun": true/false,
  "hedef_uygun": true/false,
  "risk_yonetimi_notu": "Stop ve hedef seçiminin değerlendirmesi",
  "kural_uyumu": "Swing kurallarına uyuldu mu? Hangi kural ihlal edildi varsa?",
  "tekrar_yapilir_mi": true/false,
  "tekrar_sartlari": "Bu setup'ı tekrar almak için hangi koşullar gerekli?",
  "guclu_yanlar": "Trade'de doğru yapılan şeyler (varsa)",
  "zayif_yanlar": "Trade'de yanlış yapılan şeyler",
  "sistem_onerisi": "Bu trade'den sistemin öğrenmesi gereken 1 şey (çok somut, kural önerisi formatında)",
  "ders_guncel": "Güncellenmiş/zenginleştirilmiş ders notu (mevcut dersi geliştir)",
  "puan": 1-10
}}

Puan kriterleri:
- 8-10: Kural uyumlu, iyi timing, doğru risk yönetimi
- 5-7: Kabul edilebilir, küçük hatalar
- 1-4: Kural ihlali, kötü timing, zayıf risk yönetimi
"""

    payload = json.dumps({
        "model": CLAUDE_MODEL,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        raw = data["content"][0]["text"].strip()

        # JSON temizle
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        analiz = json.loads(raw)
        analiz["analiz_tarihi"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        analiz["model"] = CLAUDE_MODEL
        return analiz

    except urllib.error.HTTPError as e:
        hata = e.read().decode()
        return {"hata": f"API hatası {e.code}: {hata[:200]}",
                "analiz_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M")}
    except json.JSONDecodeError as e:
        return {"hata": f"JSON parse hatası: {str(e)}",
                "ham_cevap": raw[:500],
                "analiz_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M")}
    except Exception as e:
        return {"hata": str(e),
                "analiz_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M")}


# ══════════════════════════════════════════════════════════════════════════════
# 2. SİSTEM GENELİ ÖZET (bağlam için)
# ══════════════════════════════════════════════════════════════════════════════

def sistem_ozeti_olustur(trades: list) -> str:
    """Analiz öncesi bağlam için genel sistem durumunu özetler."""
    kazanc = [t for t in trades if t.get("sonuc") == "KAZANÇ"]
    zarar  = [t for t in trades if t.get("sonuc") == "ZARAR"]
    toplam = len(trades)
    if toplam == 0:
        return ""
    wr = len(kazanc) / toplam * 100
    avg_k = sum(t["kar_zarar_yuzde"] for t in kazanc) / len(kazanc) if kazanc else 0
    avg_z = sum(t["kar_zarar_yuzde"] for t in zarar) / len(zarar) if zarar else 0
    return (
        f"Sistem: {toplam} trade, WR %{wr:.0f}, "
        f"Ort kazanç +{avg_k:.1f}%, Ort zarar {avg_z:.1f}%"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. CLOSED.JSON GÜNCELLEME
# ══════════════════════════════════════════════════════════════════════════════

def closed_json_yukle() -> dict:
    with open(CLOSED_SWING, encoding="utf-8") as f:
        return json.load(f)


def closed_json_kaydet(data: dict):
    data["son_guncelleme"] = datetime.now().strftime("%Y-%m-%d")
    with open(CLOSED_SWING, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def tek_trade_analiz_et(trade_id: str, force: bool = False) -> bool:
    """Tek bir trade'i analiz eder, closed.json'u günceller."""
    data   = closed_json_yukle()
    trades = data["kapatilan_pozisyonlar"]
    ozet   = sistem_ozeti_olustur(trades)

    hedef = next((t for t in trades if t.get("id") == trade_id), None)
    if hedef is None:
        print(f"❌ Trade bulunamadı: {trade_id}")
        return False

    if "auto_analiz" in hedef and not force:
        print(f"⏭️  {trade_id} zaten analiz edilmiş (--force ile yeniden yap)")
        return True

    print(f"🔍 Analiz ediliyor: {hedef['sembol']} ({trade_id}) "
          f"{hedef['kar_zarar_yuzde']:+.1f}% | {hedef['tutulan_gun']} gün")

    analiz = claude_analiz_et(hedef, ozet)

    if "hata" in analiz:
        print(f"   ❌ Hata: {analiz['hata']}")
        return False

    # Güncellenmiş dersi de ana alana yaz
    if analiz.get("ders_guncel"):
        hedef["ders"] = analiz["ders_guncel"]

    hedef["auto_analiz"] = analiz

    # JSON güncelle
    closed_json_kaydet(data)

    puan = analiz.get("puan", "—")
    tekrar = "✅" if analiz.get("tekrar_yapilir_mi") else "❌"
    print(f"   ✅ Tamamlandı | Puan: {puan}/10 | Tekrar alınır mı: {tekrar}")
    if analiz.get("sistem_onerisi"):
        print(f"   💡 Sistem önerisi: {analiz['sistem_onerisi'][:100]}")

    return True


def tum_analiz_eksikleri_tamamla(force: bool = False, aralik: float = 2.0):
    """Analiz eksik tüm trade'leri işler."""
    data   = closed_json_yukle()
    trades = data["kapatilan_pozisyonlar"]

    if force:
        bekleyenler = trades
    else:
        bekleyenler = [t for t in trades if "auto_analiz" not in t]

    if not bekleyenler:
        print("✅ Tüm trade'ler zaten analiz edilmiş.")
        return

    print(f"📋 {len(bekleyenler)} trade analiz edilecek...\n")
    basarili = 0
    for i, trade in enumerate(bekleyenler, 1):
        trade_id = trade.get("id", f"IDX-{i}")
        print(f"[{i}/{len(bekleyenler)}] ", end="", flush=True)
        if tek_trade_analiz_et(trade_id, force=force):
            basarili += 1
        if i < len(bekleyenler):
            time.sleep(aralik)  # Rate limit için bekle

    print(f"\n✅ Tamamlandı: {basarili}/{len(bekleyenler)} trade analiz edildi.")

    # Episodik belleği güncelle
    try:
        sys.path.insert(0, str(BASE / "scripts"))
        from trade_memory import rebuild_index
        print("\n🔄 Episodik bellek güncelleniyor...")
        rebuild_index()
    except Exception as e:
        print(f"⚠️  Bellek güncellenemedi: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. RAPOR VE İÇGÖRÜLER
# ══════════════════════════════════════════════════════════════════════════════

def rapor_goster():
    """Analiz edilmiş trade'lerin özet raporunu gösterir."""
    data   = closed_json_yukle()
    trades = data["kapatilan_pozisyonlar"]
    analyzed = [t for t in trades if "auto_analiz" in t]

    if not analyzed:
        print("⚠️  Henüz analiz edilmiş trade yok. --all ile başlat.")
        return

    print(f"\n{'='*62}")
    print(f"  📊 POST-TRADE ANALİZ RAPORU — {len(analyzed)} trade")
    print(f"{'='*62}")

    # Puan dağılımı
    puanlar = [t["auto_analiz"].get("puan", 0) for t in analyzed if "auto_analiz" in t]
    if puanlar:
        avg_p = sum(puanlar) / len(puanlar)
        print(f"\n  ⭐ Ortalama Kalite Puanı: {avg_p:.1f}/10")
        iyi  = len([p for p in puanlar if p >= 8])
        orta = len([p for p in puanlar if 5 <= p < 8])
        kotu = len([p for p in puanlar if p < 5])
        print(f"     Yüksek (8+): {iyi} | Orta (5-7): {orta} | Düşük (<5): {kotu}")

    # Tez doğruluğu
    tez_dogru = [t for t in analyzed if t["auto_analiz"].get("tez_dogru")]
    print(f"\n  🎯 Tez Doğruluğu: {len(tez_dogru)}/{len(analyzed)} "
          f"(%{len(tez_dogru)/len(analyzed)*100:.0f})")

    # Timing hatası
    timing_hata = [t for t in analyzed if t["auto_analiz"].get("timing_hatasi")]
    print(f"  ⏱️  Timing Hatası: {len(timing_hata)}/{len(analyzed)}")

    # Tekrar alınır
    tekrar = [t for t in analyzed if t["auto_analiz"].get("tekrar_yapilir_mi")]
    print(f"  🔄 Tekrar Alınır: {len(tekrar)}/{len(analyzed)}")

    # En düşük puanlı trade'ler
    sorted_trades = sorted(analyzed,
                           key=lambda t: t["auto_analiz"].get("puan", 10))
    print(f"\n  📉 EN ÇIKARILACAK DERS (Düşük Puanlılar):")
    for t in sorted_trades[:3]:
        a = t["auto_analiz"]
        print(f"     {t['sembol']:<6} Puan:{a.get('puan','?')}/10 | "
              f"{t['kar_zarar_yuzde']:+.1f}%")
        if a.get("sistem_onerisi"):
            print(f"            → {a['sistem_onerisi'][:100]}")

    # En iyi trade'ler
    sorted_best = sorted(analyzed,
                         key=lambda t: t["auto_analiz"].get("puan", 0),
                         reverse=True)
    print(f"\n  🏆 EN İYİ TRADE'LER:")
    for t in sorted_best[:3]:
        a = t["auto_analiz"]
        print(f"     {t['sembol']:<6} Puan:{a.get('puan','?')}/10 | "
              f"{t['kar_zarar_yuzde']:+.1f}%")
        if a.get("guclu_yanlar"):
            print(f"            → {a['guclu_yanlar'][:100]}")

    print(f"\n{'='*62}\n")


def sistem_icgoruleri():
    """
    Tüm analizlerden sistem geneli içgörüler çıkarır.
    Bunlar K-kuralı önerileri ve sistem iyileştirmeleri için kullanılır.
    """
    data     = closed_json_yukle()
    trades   = data["kapatilan_pozisyonlar"]
    analyzed = [t for t in trades if "auto_analiz" in t]

    if not analyzed:
        print("⚠️  Analiz edilmiş trade bulunamadı.")
        return

    # Tüm sistem önerilerini topla
    oneriler = []
    for t in analyzed:
        o = t["auto_analiz"].get("sistem_onerisi", "")
        if o and o != "—":
            oneriler.append(f"[{t['sembol']} {t['kar_zarar_yuzde']:+.1f}%] {o}")

    # Zayıf yanları topla
    zayiflar = []
    for t in analyzed:
        z = t["auto_analiz"].get("zayif_yanlar", "")
        if z:
            zayiflar.append(f"[{t['sembol']}] {z[:150]}")

    print(f"\n{'='*62}")
    print(f"  🔬 SİSTEM GENELİ İÇGÖRÜLER")
    print(f"{'='*62}")

    print(f"\n  💡 SİSTEM ÖNERİLERİ ({len(oneriler)}):")
    for o in oneriler:
        print(f"     • {o}")

    print(f"\n  ⚠️  TEKRARLAYAN ZAYIFLIKLAR:")
    for z in zayiflar[:5]:
        print(f"     • {z}")

    # Özet dosyaya yaz
    icgoru_dosyasi = REPORT_DIR / "sistem_icgoruleri.json"
    icgoru_data = {
        "olusturulma": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "analiz_edilen_trade": len(analyzed),
        "sistem_onerileri": oneriler,
        "tekrarlayan_zayifliklar": zayiflar,
    }
    with open(icgoru_dosyasi, "w", encoding="utf-8") as f:
        json.dump(icgoru_data, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 Kaydedildi: {icgoru_dosyasi}")
    print(f"{'='*62}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 5. CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Finzora AI — Otomatik Post-Trade Analiz Motoru"
    )
    parser.add_argument("--all", action="store_true",
                        help="Analiz eksik tüm trade'leri işle")
    parser.add_argument("--id", type=str,
                        help="Belirli bir trade'i analiz et (ör. SWING-020)")
    parser.add_argument("--force", action="store_true",
                        help="Zaten analiz edilmişleri de yeniden analiz et")
    parser.add_argument("--report", action="store_true",
                        help="Analiz özet raporunu göster")
    parser.add_argument("--insights", action="store_true",
                        help="Sistem geneli içgörüleri çıkar")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="API çağrıları arası bekleme (saniye, default: 2)")

    args = parser.parse_args()

    if not ANTHROPIC_KEY and (args.all or args.id):
        print("❌ ANTHROPIC_API_KEY environment variable bulunamadı.")
        print("   export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    if args.all:
        tum_analiz_eksikleri_tamamla(force=args.force, aralik=args.delay)

    elif args.id:
        tek_trade_analiz_et(args.id, force=args.force)

    elif args.report:
        rapor_goster()

    elif args.insights:
        sistem_icgoruleri()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
