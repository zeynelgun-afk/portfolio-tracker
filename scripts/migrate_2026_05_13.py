#!/usr/bin/env python3
"""
13 Mayıs 2026 — Portföy yapısı sadeleştirme migration script.

Yapılanlar:
1. data/portfolios/*.json + data/swing/*.json → data/portfolio.json (tek liste)
2. Eski dosyalar data/archive/2026-05-13_pre_simplification/ altına taşınacak (git mv, ayrıca)
3. docs/K_RULES_QUICK_REF.md arşive, yeni minimal versiyon yerleştirilecek (ayrıca)

Yeni şema — sadece kâtip alanları:
  symbol, sector, entry_date, entry_price, shares, entry_reason, stop_loss, target (opsiyonel)
Kapanışta eklenir:
  exit_date, exit_price, exit_reason
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def donustur_acik(eski: dict) -> dict:
    """Eski portföy pozisyonu → yeni minimal şema."""
    yeni = {
        "symbol": eski.get("sembol"),
        "sector": eski.get("sektor"),
        "entry_date": eski.get("giris_tarihi"),
        "entry_price": eski.get("giris_fiyati") or eski.get("maliyet_baz"),
        "shares": eski.get("adet"),
        "entry_reason": eski.get("giris_nedeni") or "Eski sistemden taşındı — gerekçe kayıp",
        "stop_loss": eski.get("stop_loss"),
        "target": eski.get("hedef_fiyat"),  # opsiyonel, null olabilir
    }
    # notlar varsa entry_reason'a ekle
    notlar = eski.get("notlar")
    if notlar:
        yeni["entry_reason"] = f"{yeni['entry_reason']} | {notlar}"
    return yeni


def donustur_kapali(eski: dict) -> dict:
    """Eski swing closed pozisyonu → yeni minimal kapalı şema."""
    return {
        "symbol": eski.get("sembol"),
        "sector": eski.get("sektor") or "—",
        "entry_date": eski.get("giris_tarihi"),
        "entry_price": eski.get("giris_fiyati"),
        "shares": eski.get("adet") or eski.get("hisse_adedi"),
        "entry_reason": eski.get("giris_nedeni") or "Eski swing — gerekçe kayıp",
        "stop_loss": eski.get("stop_loss"),
        "target": eski.get("hedef_fiyat"),
        "exit_date": eski.get("cikis_tarihi"),
        "exit_price": eski.get("cikis_fiyati"),
        "exit_reason": eski.get("cikis_nedeni") or eski.get("sonuc") or "—",
        "pnl_pct": eski.get("kar_zarar_yuzde"),
        "lessons": eski.get("ders") or "",
    }


def donustur_swing_acik(eski: dict) -> dict:
    """Eski swing aktif pozisyon → yeni minimal şema."""
    yontem = eski.get("tarama_yontemi") or ""
    katalizor = eski.get("katalizor") or ""
    orijinal_neden = eski.get("giris_nedeni") or ""
    # Swing kaydı olduğunu entry_reason'a not düş
    parcalar = [f"[SWING — {yontem}]" if yontem else "[SWING]"]
    if orijinal_neden:
        parcalar.append(orijinal_neden)
    if katalizor:
        parcalar.append(f"Katalizör: {katalizor}")
    return {
        "symbol": eski.get("sembol"),
        "sector": eski.get("sektor") or "—",
        "entry_date": eski.get("giris_tarihi"),
        "entry_price": eski.get("giris_fiyati") or eski.get("maliyet_baz"),
        "shares": eski.get("adet"),
        "entry_reason": " | ".join(parcalar),
        "stop_loss": eski.get("stop_loss"),
        "target": eski.get("hedef_fiyat"),
    }


def main():
    acik_pozisyonlar = []
    for f in ["data/portfolios/balanced.json",
              "data/portfolios/aggressive.json",
              "data/portfolios/dividend.json"]:
        d = json.loads((ROOT / f).read_text())
        for p in d.get("pozisyonlar", []):
            acik_pozisyonlar.append(donustur_acik(p))

    # Swing aktif pozisyonlar
    swing_active = json.loads((ROOT / "data/swing/active.json").read_text())
    for p in swing_active.get("aktif_pozisyonlar", []):
        acik_pozisyonlar.append(donustur_swing_acik(p))

    # ---- POST-PROCESSING ----
    # 1) Aynı sembolü ağırlıklı ortalama ile birleştir
    from collections import defaultdict
    gruplar = defaultdict(list)
    for p in acik_pozisyonlar:
        gruplar[p["symbol"]].append(p)

    birlesik = []
    for sembol, grup in gruplar.items():
        if len(grup) == 1:
            birlesik.append(grup[0])
            continue
        # Çakışma — birleştir
        toplam_hisse = sum(p["shares"] for p in grup)
        toplam_maliyet = sum(p["shares"] * p["entry_price"] for p in grup)
        ort_giris = round(toplam_maliyet / toplam_hisse, 2)
        en_eski = min(p["entry_date"] for p in grup if p["entry_date"])

        # Stop seçimi: entry'ye eşit OLMAYAN orijinal stop'lar arasında min
        # Eğer min stop yeni ortalama maliyetin üstünde ise → %5 altı yedek
        gercek_stoplar = [
            p["stop_loss"] for p in grup
            if p["stop_loss"] is not None
            and abs(p["stop_loss"] - p["entry_price"]) > 0.01
        ]
        if gercek_stoplar:
            stop = min(gercek_stoplar)
            if stop >= ort_giris:
                stop = round(ort_giris * 0.95, 2)
        else:
            stop = round(ort_giris * 0.95, 2)

        # Sektör — boş olmayanı tercih et
        sektor = next((p["sector"] for p in grup if p["sector"] and p["sector"] != "—"), "—")

        # entry_reason birleştir
        nedenler = [p["entry_reason"] for p in grup if p["entry_reason"]]
        birlesik_neden = f"[BİRLEŞTİRİLDİ — {len(grup)} giriş] " + " // ".join(nedenler)

        birlesik.append({
            "symbol": sembol,
            "sector": sektor,
            "entry_date": en_eski,
            "entry_price": ort_giris,
            "shares": toplam_hisse,
            "entry_reason": birlesik_neden,
            "stop_loss": stop,
            "target": None,
        })

    # 2) Stop = giriş eşit olan tekil pozisyonlarda %5 altı stop koy
    for p in birlesik:
        ep = p.get("entry_price")
        sl = p.get("stop_loss")
        if ep is not None and (sl is None or abs(sl - ep) < 0.01):
            yeni_stop = round(ep * 0.95, 2)
            p["stop_loss"] = yeni_stop
            mevcut = p.get("entry_reason", "") or ""
            if "[STOP %5 OTOMATİK]" not in mevcut:
                p["entry_reason"] = f"{mevcut} | [STOP %5 OTOMATİK]"

    acik_pozisyonlar = birlesik

    kapali_pozisyonlar = []
    swing_closed = json.loads((ROOT / "data/swing/closed.json").read_text())
    for p in swing_closed.get("kapatilan_pozisyonlar", []):
        kapali_pozisyonlar.append(donustur_kapali(p))

    yeni = {
        "_aciklama": "Tek portföy — 13 Mayıs 2026 sadeleştirmesi sonrası. "
                     "Sleeve/sektör ağırlığı yok. Pozisyon büyüklüğü kararı Zeynel'e ait.",
        "_son_guncelleme": datetime.now().isoformat(timespec="seconds"),
        "_template_acik": {
            "symbol": "TICKER",
            "sector": "Sektör adı (Türkçe veya İngilizce)",
            "entry_date": "YYYY-MM-DD",
            "entry_price": 0.00,
            "shares": 0,
            "entry_reason": "Detaylı giriş tezi — neden alındı, hangi katalizör, tez",
            "stop_loss": 0.00,
            "target": None,
        },
        "_template_kapali": {
            "symbol": "TICKER",
            "sector": "...",
            "entry_date": "YYYY-MM-DD",
            "entry_price": 0.00,
            "shares": 0,
            "entry_reason": "...",
            "stop_loss": 0.00,
            "target": None,
            "exit_date": "YYYY-MM-DD",
            "exit_price": 0.00,
            "exit_reason": "Stop-loss / hedef / tez bozulması / başka — kısa gerekçe",
            "pnl_pct": 0.00,
            "lessons": "Bu trade'den çıkarılan ders (opsiyonel)",
        },
        "positions": acik_pozisyonlar,
        "closed": kapali_pozisyonlar,
    }

    (ROOT / "data/portfolio.json").write_text(
        json.dumps(yeni, ensure_ascii=False, indent=2)
    )
    print(f"✅ data/portfolio.json yazıldı: "
          f"{len(acik_pozisyonlar)} açık, {len(kapali_pozisyonlar)} kapalı")


if __name__ == "__main__":
    main()
