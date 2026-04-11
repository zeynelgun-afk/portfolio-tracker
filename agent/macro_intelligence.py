#!/usr/bin/env python3
"""
Finzora — Makro Zeka Motoru
=============================
Her sabah şu soruyu yanıtlar:
  "Bugün para nereye gidiyor ve bu hikayeye ait hangi hisseler alınabilir?"

Akış:
  1. Web araması: küresel ekonomi, sektör rotasyonu, jeopolitik
  2. FMP: sektör performansı, en güçlü hisseler, analist revizyonları
  3. Claude analizi: 3-5 dominant tema tespit + alt dal hisseleri
  4. Çıktı: tema_listesi + hisse_adayları → opportunity_finder'a gider
"""

import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT = Path(__file__).parent.parent
TR_TZ     = pytz.timezone("Europe/Istanbul")
FMP_KEY   = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE  = "https://financialmodelingprep.com/stable"

# Bilinen tema→hisse evreni (statik başlangıç, Darwin evrimleştirir)
THEME_UNIVERSE = {
    "AI_altyapı": {
        "açıklama": "AI veri merkezi, çip ekipmanı, güç altyapısı harcamaları",
        "alt_dallar": {
            "çip_ekipman":    ["ASML","AMAT","LRCX","KLAC","CAMT","ONTO","TER"],
            "optik_bağlantı": ["COHR","LITE","AAOI","FN","ANET"],
            "güç_soğutma":    ["VRT","ETN","PWR","GNRC","HUBB"],
            "bellek":         ["MU","WDC","STX"],
            "veri_merkezi":   ["EQIX","DLR","IREN"],
        }
    },
    "savunma_uzay": {
        "açıklama": "Jeopolitik gerilim, NATO harcamaları, hipersonik/uzay yarışı",
        "alt_dallar": {
            "ana_savunma":    ["LMT","RTX","GD","NOC","LHX"],
            "drone_uzay":     ["KTOS","RKLB","AJRD","RDW"],
            "siber":          ["CRWD","PANW","S","ZS"],
        }
    },
    "enerji_geçiş": {
        "açıklama": "Temiz enerji, nükleer, AI güç talebi, enerji güvenliği",
        "alt_dallar": {
            "nükleer":        ["CEG","VST","NRG","CCJ"],
            "yenilenebilir":  ["NEE","FSLR","ENPH","RUN"],
            "enerji_altyapı": ["KMI","WMB","OKE","ET"],
        }
    },
    "sağlık_yenilik": {
        "açıklama": "GLP-1, onkoloji, AI destekli ilaç keşfi",
        "alt_dallar": {
            "glp1_obezite":   ["LLY","NVO","VKTX","ALT"],
            "onkoloji":       ["REGN","BMY","MRNA","GILD"],
            "medikal_cihaz":  ["ISRG","MDT","SYK","EW"],
        }
    },
    "finansal_döngüsel": {
        "açıklama": "Faiz ortamı, kredi döngüsü, fintech büyümesi",
        "alt_dallar": {
            "büyük_banka":    ["JPM","BAC","GS","MS"],
            "sigorta":        ["AIG","MET","PRU","CB"],
            "fintech":        ["V","MA","PYPL","AFRM"],
        }
    },
    "emtia_kaynak": {
        "açıklama": "Nadir toprak, bakır, altın — AI + yeşil geçiş talebi",
        "alt_dallar": {
            "bakır_maden":    ["FCX","SCCO","TECK","HBM"],
            "altın_gümüş":    ["NEM","GOLD","AEM","PAAS"],
            "nadir_toprak":   ["MP","NOVN","USA"],
        }
    },
}


def _fmp(endpoint, params=None):
    p = (params or {})
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
        return r.json()
    except Exception:
        return None


def get_sector_performance() -> dict:
    """Son 5 günlük sektör performansını çek."""
    for i in range(5):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        data = _fmp("sector-performance-snapshot", {"date": date})
        if data and isinstance(data, list) and len(data) > 5:
            return {s.get("sector", ""): float(s.get("changesPercentage", 0))
                    for s in data}
    return {}


def get_market_news() -> list:
    """Son 24 saatin önemli piyasa haberlerini çek."""
    data = _fmp("news/general-latest", {"limit": 15}) or []
    return [{"baslik": n.get("title",""), "kaynak": n.get("site",""),
             "tarih": n.get("publishedDate","")[:16]} for n in data[:10]]


def get_biggest_gainers() -> list:
    """Günün en güçlü hisselerini çek — momentum sinyali."""
    data = _fmp("biggest-gainers", {"limit": 20}) or []
    return [{"sembol": s.get("symbol",""), "degisim": float(s.get("changesPercentage",0)),
             "fiyat": float(s.get("price",0))} for s in data[:15]]


def analyze_themes_with_claude(
    sektor_perf: dict,
    haberler: list,
    güçlü_hisseler: list,
    vix: float
) -> dict:
    """Claude ile dominant temaları tespit et ve hisse adaylarını belirle."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from claude_agent import get_claude_decision

    # Context hazırla
    sektor_ozet = "\n".join(
        f"  {s}: {v:+.1f}%" for s, v in
        sorted(sektor_perf.items(), key=lambda x: -x[1])[:8]
    ) if sektor_perf else "  veri yok"

    haber_ozet = "\n".join(
        f"  [{n['tarih']}] {n['baslik'][:80]}" for n in haberler[:6]
    )

    guclu_ozet = ", ".join(
        f"{h['sembol']}({h['degisim']:+.1f}%)" for h in güçlü_hisseler[:10]
    )

    # Bilinen tema evreni
    tema_listesi = "\n".join(
        f"  {k}: {v['açıklama']}" for k, v in THEME_UNIVERSE.items()
    )

    prompt = f"""Sen Finzora AI trading sistemisin. Piyasa analizine dayalı tematik fırsat tespiti yapıyorsun.

SEKTÖR PERFORMANSI (bugün):
{sektor_ozet}

SON HABERLER:
{haber_ozet}

GÜNÜN EN GÜÇLÜ HİSSELERİ: {guclu_ozet}
VIX: {vix:.1f}

BİLİNEN TEMA EVRENİ:
{tema_listesi}

GÖREV: Bugün için en güçlü 2-3 temayı tespit et ve her tema için alım adayları belirle.

ÇIKTI FORMAT (SADECE JSON):
{{
  "dominant_temalar": [
    {{
      "tema_adi": "AI_altyapı",
      "güç_skoru": 8,
      "neden": "Büyük teknoloji şirketleri capex artışı, güç altyapısı talebi",
      "öncelikli_alt_dal": "güç_soğutma",
      "önerilen_hisseler": ["VRT","ETN","PWR"],
      "portföy": "growth",
      "aciliyet": "yüksek"
    }}
  ],
  "kaçınılacak_sektörler": ["Consumer Defensive", "Real Estate"],
  "piyasa_modu": "risk-on",
  "genel_yorum": "2-3 cümle"
}}"""

    response = get_claude_decision(prompt, mode="morning")

    try:
        import re
        m = re.search(r'\{.*\}', response, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass

    # Fallback: varsayılan tema
    return {
        "dominant_temalar": [],
        "piyasa_modu": "nötr",
        "genel_yorum": response[:200]
    }


def run_macro_intelligence(vix: float = 20.0) -> dict:
    """
    Ana makro zeka fonksiyonu.
    Döndürür: {dominant_temalar, hisse_adayları, sektor_güçlü, piyasa_modu}
    """
    print("[Makro] Sektör performansı çekiliyor...")
    sektor = get_sector_performance()

    print("[Makro] Haberler çekiliyor...")
    haberler = get_market_news()

    print("[Makro] En güçlü hisseler çekiliyor...")
    güçlü = get_biggest_gainers()

    print("[Makro] Claude tema analizi yapılıyor...")
    analiz = analyze_themes_with_claude(sektor, haberler, güçlü, vix)

    # Her tema için hisse evrenini ekle
    for tema in analiz.get("dominant_temalar", []):
        tema_adi = tema.get("tema_adi", "")
        alt_dal  = tema.get("öncelikli_alt_dal", "")

        if tema_adi in THEME_UNIVERSE:
            evren = THEME_UNIVERSE[tema_adi]
            if alt_dal in evren.get("alt_dallar", {}):
                tema["hisse_evreni"] = evren["alt_dallar"][alt_dal]
            else:
                # Tüm alt dalları birleştir
                tüm = []
                for hisseler in evren["alt_dallar"].values():
                    tüm.extend(hisseler)
                tema["hisse_evreni"] = list(set(tüm))

    # Sonucu kaydet
    output = {
        "tarih":            datetime.now(TR_TZ).isoformat(),
        "vix":              vix,
        "sektor_performans": sektor,
        "dominant_temalar": analiz.get("dominant_temalar", []),
        "kacınılacak":      analiz.get("kaçınılacak_sektörler", []),
        "piyasa_modu":      analiz.get("piyasa_modu", "nötr"),
        "genel_yorum":      analiz.get("genel_yorum", ""),
        "haberler":         haberler[:5],
    }

    out_path = REPO_ROOT / "data" / "macro_intelligence.json"
    json.dump(output, open(out_path, "w"), ensure_ascii=False, indent=2)
    print(f"[Makro] {len(output['dominant_temalar'])} tema tespit edildi → {out_path.name}")

    return output
