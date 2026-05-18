#!/usr/bin/env python3
"""JSON Key Audit — Türkçe → İngilizce migration kapsam taraması.

Faz 2 sonrası bakım. Tüm `data/` altındaki JSON dosyalarını tarar,
Türkçe karakter veya Türkçe kelime içeren key isimlerini raporlar.

Bu key'lerin migrate edilmesi planı: docs/JSON_KEY_MIGRATION.md

Çıktı modları:
    --format=text   İnsan okur (default)
    --format=json   Otomasyon/script okur
    --format=csv    Migration tablosu için

Filtre:
    --file=PATH     Sadece tek dosya tara
    --all           İçeriği de dökümle (key + values)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Türkçe-spesifik karakterler
_TURKISH_CHARS = set("çğıİöşüÇĞİÖŞÜ")

# Türkçe kelime sözlüğü — sık geçen field/value adları
# ASCII Türkçe (turkish characters yok) varyantları da dahil
_TURKISH_WORDS = {
    # NLP/value isimleri
    "tema", "temalar", "öncelikli", "önerilen", "portföy", "portfolyo",
    "güç", "skoru", "alt_dal", "kacınılacak", "kaçınılacak",
    "yüksek", "düşük", "orta", "hacim", "fiyat", "bilanço", "bülançö",
    "analiz", "analizler", "tarih", "saat", "dolar", "lira",
    "sektör", "dağılım", "dağılımı", "alım", "satım",
    "değerleme", "değerli", "ucuz", "pahalı",
    "yarı", "iletken", "ekipman", "tütün", "doğalgaz",
    "temettü", "büyüme", "değer", "agresif", "dengeli",
    "uyarı", "uyarılar", "hata", "başarılı", "başarısız",
    # ASCII Türkçe field adları (summary.json benzerleri)
    "son_guncelleme", "guncelleme", "guncel",
    "toplam_sermaye", "toplam_deger", "toplam_kar",
    "kar_zarar", "kar_zarar_yuzde", "yuzde",
    "portfolyolar", "portfolyo",  # ascii portföy
    "pozisyon", "pozisyon_sayisi",
    "deger", "maliyet", "miktar",
    "nakit", "para_birimi", "agirlik", "agirlik_yuzde",
    "isim", "dagilim", "sektor_dagilimi",
    "gaplar", "yuksek", "dusuk", "yuksek_hacim",
    "fiyat", "tarih", "saat",
    "analiz_edilen_trade", "trade_index",
    "bilanco", "bilanco_tarihi", "bulanco",
    "satim", "alim",
    "g1_fiyat", "g5_fiyat", "g10_fiyat", "g20_fiyat",  # backtest
}


def has_turkish(s: str) -> bool:
    """String Türkçe karakter veya bilinen Türkçe kelime içeriyor mu?"""
    if not isinstance(s, str):
        return False
    if any(ch in _TURKISH_CHARS for ch in s):
        return True
    lower = s.lower()
    return any(word in lower for word in _TURKISH_WORDS)


def scan_keys(obj, prefix: str = "", path: str = "") -> list[dict]:
    """Bir JSON objesi içinde Türkçe key'leri recursive tara."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = prefix + k
            if has_turkish(k):
                # Bu bir key — value tipini de kaydet
                vtype = type(v).__name__
                found.append({
                    "file": path,
                    "key_path": full_key,
                    "key_name": k,
                    "value_type": vtype,
                    "depth": prefix.count(".") + 1,
                })
            found.extend(scan_keys(v, full_key + ".", path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(scan_keys(item, prefix, path))
    return found


# Dosyalar — bu dosyalardaki key'ler "gerçek Türkçe metin verisi"
# olduğu için migrate edilmez (TF-IDF tokens, NLP embeddings, vb.)
_SKIP_FILES = {
    "data/episodic_memory/tfidf_vectors.json",
    "data/episodic_memory/sistem_icgoruleri.json",  # narrative text dump
}


def audit_file(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []

    rel = str(path.relative_to(_REPO_ROOT))
    if rel in _SKIP_FILES:
        return []  # NLP/data dump, migrate edilemez

    return scan_keys(data, path=rel)


def audit_all() -> list[dict]:
    """data/ altındaki tüm JSON dosyalarını tara."""
    data_dir = _REPO_ROOT / "data"
    if not data_dir.exists():
        return []

    findings = []
    for p in sorted(data_dir.rglob("*.json")):
        # Test/temp dosyaları atla
        if "archive" in p.parts or ".pytest_cache" in p.parts:
            continue
        findings.extend(audit_file(p))
    return findings


def format_text(findings: list[dict]) -> str:
    if not findings:
        return "✅ Türkçe key bulunamadı (data/ temiz)"

    lines = [f"⚠️  Türkçe key sayısı: {len(findings)}\n"]

    # Dosya bazında grupla
    by_file: dict[str, list[dict]] = {}
    for f in findings:
        by_file.setdefault(f["file"], []).append(f)

    # Unique key adlarını da say
    unique_keys = set(f["key_name"] for f in findings)
    lines.append(f"Benzersiz key adı: {len(unique_keys)}")
    lines.append(f"Etkilenen dosya: {len(by_file)}\n")

    # Dosya bazında detay
    for file_path, items in sorted(by_file.items()):
        unique_in_file = set(it["key_name"] for it in items)
        lines.append(f"\n📁 {file_path} ({len(items)} key, {len(unique_in_file)} benzersiz)")
        for k in sorted(unique_in_file):
            count = sum(1 for it in items if it["key_name"] == k)
            lines.append(f"   - {k!r:30}  ({count}× görünüm)")

    # Migration önerileri
    lines.append("\n" + "=" * 60)
    lines.append("MIGRATION ÖNERİSİ (Türkçe → İngilizce):")
    lines.append("=" * 60)
    suggested = {
        "temettü": "dividend",
        "portföy": "portfolio",
        "portfolyolar": "portfolios",
        "portfolyo": "portfolio",
        "tema": "theme",
        "temalar": "themes",
        "dominant_temalar": "dominant_themes",
        "öncelikli_alt_dal": "priority_subsector",
        "önerilen_hisseler": "suggested_tickers",
        "güç_skoru": "strength_score",
        "kacınılacak": "avoid",
        "kaçınılacak": "avoid",
        "yüksek_hacim": "high_volume",
        "düşük_hacim": "low_volume",
        "gaplar": "gaps",
        "bülançö_tarihi": "earnings_date",
        "bilanço_tarihi": "earnings_date",
        "analizler": "analyses",
        "sektor_dagilimi": "sector_distribution",
        "uyarı": "alert",
        "uyarılar": "alerts",
    }
    for k in sorted(unique_keys):
        sug = suggested.get(k.lower(), "(öneri yok)")
        lines.append(f"   {k:30} → {sug}")

    return "\n".join(lines)


def format_json(findings: list[dict]) -> str:
    return json.dumps({
        "total_findings": len(findings),
        "unique_keys": len(set(f["key_name"] for f in findings)),
        "files": len(set(f["file"] for f in findings)),
        "findings": findings,
    }, indent=2, ensure_ascii=False)


def format_csv(findings: list[dict]) -> str:
    """Migration tablosu için CSV. Manuel doldurma kolay."""
    lines = ["file,key_path,key_name,value_type,suggested_replacement"]
    suggested_map = {
        "temettü": "dividend", "portföy": "portfolio", "tema": "theme",
        "öncelikli_alt_dal": "priority_subsector", "güç_skoru": "strength_score",
        "yüksek_hacim": "high_volume", "kacınılacak": "avoid",
    }
    for f in findings:
        sug = suggested_map.get(f["key_name"].lower(), "")
        lines.append(f'"{f["file"]}","{f["key_path"]}","{f["key_name"]}","{f["value_type"]}","{sug}"')
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["text", "json", "csv"], default="text")
    parser.add_argument("--file", help="Sadece tek dosya tara")
    args = parser.parse_args(argv)

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = _REPO_ROOT / path
        findings = audit_file(path)
    else:
        findings = audit_all()

    if args.format == "json":
        print(format_json(findings))
    elif args.format == "csv":
        print(format_csv(findings))
    else:
        print(format_text(findings))

    return 0 if not findings else 0  # Non-fatal — sadece raporlama


if __name__ == "__main__":
    sys.exit(main())
