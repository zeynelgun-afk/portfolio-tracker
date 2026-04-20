"""
split_sabah_report.py — DAILY_SABAH_*.md raporunu parse edip
DAILY_SWING_*.md ve DAILY_PORTFOY_*.md dosyalarina ayiran post-processor.

Amac: Tek Claude cagrisi ile yazilan sabah raporunu, ek token maliyeti
olmadan gorsel olarak 3 ayri dosyaya ayirmak (memory'deki v3.0 uclu
yapinin maliyetsiz esdegeri).

Kullanim:
    python3 scripts/split_sabah_report.py [YYYY-MM-DD]

Parametre verilmezse bugunun tarihini kullanir (TR timezone).
Kaynak: reports/daily/DAILY_SABAH_YYYY-MM-DD.md
Hedef:  reports/daily/DAILY_SWING_YYYY-MM-DD.md
        reports/daily/DAILY_PORTFOY_YYYY-MM-DD.md

Bolum haritasi (SABAH raporunun mevcut yapisi):
  0.   Piyasa Istihbarati    -> ikisine de (contekt)
  0.5. Dun seans sonu        -> ikisine de (kisa)
  0.7. Tematik katalist      -> SWING'e (tema tetikli giris/cikis)
  1.   Piyasa gorunumu       -> SWING'e (VIX/endeks swing icin kritik)
  2.   Haber ve analiz       -> PORTFOY'a (hisse bazli haberler)
  3.   Portfoy saglik durumu -> PORTFOY'a (Swing alt-basligi haric)
       3.x Swing altbasligi  -> SWING'e
  4.   Gunun plani           -> ikisine de (HEMEN/IZLE/PASIF hepsinde)
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import pytz
    TR_TZ = pytz.timezone("Europe/Istanbul")
except ImportError:
    TR_TZ = None

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = REPO_ROOT / "reports" / "daily"


def _bugun_tr() -> str:
    """TR timezone'una gore bugunun tarihi (YYYY-MM-DD)."""
    if TR_TZ:
        return datetime.now(TR_TZ).strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d")


def _parse_sections(md_text: str) -> dict:
    """
    SABAH raporunu bolumlere ayirir.
    Return: {
        "header": str,           # ilk ## oncesi (baslik + meta)
        "sections": {
            "0": str,            # "## 0. ..." tum icerigi
            "0.5": str,
            "0.7": str,
            "1": str,
            "2": str,
            "3": str,
            "4": str,
        },
        "swing_subsection": str, # bolum 3 icindeki "### Swing" alt basligi
    }
    """
    lines = md_text.split("\n")

    # Header = ilk "## 0" satirina kadar
    header_lines = []
    idx = 0
    sec_pattern = re.compile(r"^##\s+([0-9]+(?:\.[0-9]+)?)\.\s+", re.IGNORECASE)
    for i, line in enumerate(lines):
        if sec_pattern.match(line):
            idx = i
            break
        header_lines.append(line)
    else:
        # Hic bolum bulunamadi
        return {"header": md_text, "sections": {}, "swing_subsection": ""}

    header = "\n".join(header_lines).rstrip()

    # Bolumleri topla
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in lines[idx:]:
        m = sec_pattern.match(line)
        if m:
            # Onceki bolumu kaydet
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).rstrip()
            current_key = m.group(1)
            current_lines = [line]
        else:
            if current_key is not None:
                current_lines.append(line)

    # Son bolumu kaydet
    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).rstrip()

    # Bolum 3'un icindeki "### Swing" alt basligini ayir
    swing_subsection = ""
    bolum_3 = sections.get("3", "")
    if bolum_3:
        sub_pattern = re.compile(r"^###\s+(.+)$", re.MULTILINE)
        sub_starts = [(m.start(), m.group(1)) for m in sub_pattern.finditer(bolum_3)]
        for i, (start, title) in enumerate(sub_starts):
            if "swing" in title.lower():
                end = sub_starts[i + 1][0] if i + 1 < len(sub_starts) else len(bolum_3)
                swing_subsection = bolum_3[start:end].rstrip()
                break

    return {
        "header": header,
        "sections": sections,
        "swing_subsection": swing_subsection,
    }


def _strip_swing_from_bolum3(bolum_3: str, swing_subsection: str) -> str:
    """Bolum 3'ten swing alt basligini cikarip temiz portfoy halini dondurur."""
    if not swing_subsection or swing_subsection not in bolum_3:
        return bolum_3
    return bolum_3.replace(swing_subsection, "").rstrip()


def _build_swing_rapor(parsed: dict, tarih: str) -> str:
    """SWING dosyasinin icerigini olustur."""
    parts = [
        f"# swing raporu — {tarih}",
        "",
        "> finzora ai | sabah raporundan otomatik ayristirildi",
        "> kaynak: DAILY_SABAH_{0}.md — 3-rapor gorsel ayristirma, token maliyeti yok".format(tarih),
        "",
    ]

    secs = parsed["sections"]

    # Piyasa istihbarati (tema & rejim baglami)
    if "0" in secs:
        parts.append(secs["0"])
        parts.append("")

    # Tematik katalist — swing'e en kritik
    if "0.7" in secs:
        parts.append(secs["0.7"])
        parts.append("")

    # Piyasa gorunumu (VIX, endeks, sektor)
    if "1" in secs:
        parts.append(secs["1"])
        parts.append("")

    # Swing alt basligi (portfoy saglik durumundan)
    if parsed["swing_subsection"]:
        parts.append("## 3. SWING DURUMU")
        parts.append("")
        parts.append(parsed["swing_subsection"])
        parts.append("")

    # Gunun plani (swing giris sinyalleri burada)
    if "4" in secs:
        parts.append(secs["4"])
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _build_portfoy_rapor(parsed: dict, tarih: str) -> str:
    """PORTFOY dosyasinin icerigini olustur."""
    parts = [
        f"# portföy raporu — {tarih}",
        "",
        "> finzora ai | sabah raporundan otomatik ayristirildi",
        "> kaynak: DAILY_SABAH_{0}.md — 3-rapor gorsel ayristirma, token maliyeti yok".format(tarih),
        "",
    ]

    secs = parsed["sections"]

    # Piyasa istihbarati (kisa baglam)
    if "0" in secs:
        parts.append(secs["0"])
        parts.append("")

    # Dun seans sonu notlari (portfoy acisindan kritik)
    if "0.5" in secs:
        parts.append(secs["0.5"])
        parts.append("")

    # Haber ve analiz (portfoye etki)
    if "2" in secs:
        parts.append(secs["2"])
        parts.append("")

    # Portfoy saglik durumu (swing hariç)
    if "3" in secs:
        bolum_3_temiz = _strip_swing_from_bolum3(secs["3"], parsed["swing_subsection"])
        parts.append(bolum_3_temiz)
        parts.append("")

    # Gunun plani (EKLE/BÜYÜT/DÖNDÜR/İZLE portfoyu da kapsar)
    if "4" in secs:
        parts.append(secs["4"])
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def split(tarih: str | None = None) -> dict:
    """
    Ana fonksiyon. tarih=None ise bugun (TR).
    Return: {"swing": Path, "portfoy": Path, "skipped": bool, "reason": str}
    """
    tarih = tarih or _bugun_tr()
    kaynak = DAILY_DIR / f"DAILY_SABAH_{tarih}.md"

    if not kaynak.exists():
        return {
            "swing": None,
            "portfoy": None,
            "skipped": True,
            "reason": f"Kaynak yok: {kaynak.name}",
        }

    md_text = kaynak.read_text(encoding="utf-8")
    parsed = _parse_sections(md_text)

    if not parsed["sections"]:
        return {
            "swing": None,
            "portfoy": None,
            "skipped": True,
            "reason": "Bolumlenmemis rapor (## 0./0.5./... bulunamadi)",
        }

    swing_path = DAILY_DIR / f"DAILY_SWING_{tarih}.md"
    portfoy_path = DAILY_DIR / f"DAILY_PORTFOY_{tarih}.md"

    swing_path.write_text(_build_swing_rapor(parsed, tarih), encoding="utf-8")
    portfoy_path.write_text(_build_portfoy_rapor(parsed, tarih), encoding="utf-8")

    return {
        "swing": swing_path,
        "portfoy": portfoy_path,
        "skipped": False,
        "reason": "",
    }


def main() -> int:
    tarih = sys.argv[1] if len(sys.argv) > 1 else None
    result = split(tarih)
    if result["skipped"]:
        print(f"[split_sabah] Atlandi: {result['reason']}")
        return 0
    print(f"[split_sabah] Yazildi: {result['swing'].name}")
    print(f"[split_sabah] Yazildi: {result['portfoy'].name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
