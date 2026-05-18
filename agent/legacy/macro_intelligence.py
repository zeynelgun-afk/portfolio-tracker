#!/usr/bin/env python3
"""
Finzora — Makro Zeka Motoru
=============================
Her sabah şu soruyu yanıtlar:
  "Bugün para nereye gidiyor ve bu hikayeye ait hangi hisseler alınabilir?"

Akış:
  1. Web araması: küresel ekonomi, sektör rotasyonu, jeopolitik
  2. FMP: sektör performansı, en güçlü hisseler, analist revizyonları
  3. AI analizi: 3-5 dominant tema tespit + alt dal hisseleri
  4. Çıktı: tema_listesi + hisse_adayları → opportunity_finder'a gider
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT = Path(__file__).parent.parent
TR_TZ     = pytz.timezone("Europe/Istanbul")
FMP_KEY   = os.environ.get("FMP_API_KEY", "")
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
    """FMP çağrısı — merkezi fmp_client (observability loglanır)."""
    try:
        from fmp_client import fmp_get as _centralized_fmp_get
        return _centralized_fmp_get(endpoint, params or {})
    except ImportError:
        # Fallback: manuel requests
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
            # sector-performance-snapshot alanı: averageChange (changesPercentage DEĞİL, changePercentage de DEĞİL)
            return {s.get("sector", ""): float(s.get("averageChange", 0))
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
    """AI ile dominant temaları tespit et ve hisse adaylarını belirle."""
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

    prompt = f"""You are the Finzora AI trading system. Detect dominant themes
from market data and identify the active crisis type for the K-13 crisis matrix.

SECTOR PERFORMANCE (today):
{sektor_ozet}

RECENT NEWS:
{haber_ozet}

STRONGEST STOCKS TODAY: {guclu_ozet}
VIX: {vix:.1f}

KNOWN THEME UNIVERSE:
{tema_listesi}

TASK 1: identify the 2-3 strongest themes for today and propose buy candidates.

TASK 2 (K-13 CRISIS MATRIX): is there market stress/crisis? Identify type:
- yok: VIX<20, mixed sectors, calm headlines → no crisis (normal risk-on)
- jeopolitik: war/tension headlines, defense sector strong, gold up
- pandemi: health alarms, healthcare up, travel/energy down
- finansal: banking stress, volatile yields, gold up
- ticaret: tariff/embargo headlines, domestic sectors favored, exporters under pressure
- enflasyon: energy + materials up, consumer pressured, hawkish Fed talk

Per crisis type:
- beneficiary sectors: those STRENGTHENING in this crisis (full position)
- sensitive sectors: those WEAKENING in this crisis (half position or stop)

Valid sector names: Technology, Healthcare, Financial Services, Energy,
Consumer Cyclical, Industrials, Consumer Defensive, Basic Materials,
Real Estate, Communication Services, Utilities, Defense, Gold

OUTPUT (JSON ONLY — keys MUST stay in Turkish exactly as shown, free-text values in Turkish):
{{
  "dominant_temalar": [
    {{
      "tema_adi": "AI_altyapı",
      "güç_skoru": 8,
      "neden": "Turkish, single sentence — concrete reason",
      "öncelikli_alt_dal": "güç_soğutma",
      "önerilen_hisseler": ["VRT","ETN","PWR"],
      "portföy": "aggressive",
      "aciliyet": "yüksek"
    }}
  ],
  "kaçınılacak_sektörler": ["Consumer Defensive", "Real Estate"],
  "piyasa_modu": "risk-on",
  "aktif_kriz": {{
    "tip": "jeopolitik",
    "guven": 7,
    "kanit": "2-3 Turkish sentences — concrete evidence: which news, which sector moves",
    "beneficiary_sectors": ["Energy","Defense","Gold","Materials","Real Estate","Consumer Defensive"],
    "sensitive_sectors": ["Technology","Consumer Cyclical","Communication Services","Healthcare","Financial Services","Industrials"]
  }},
  "genel_yorum": "2-3 Turkish sentences"
}}

CRITICAL: aktif_kriz.tip allowed values: "yok", "jeopolitik", "pandemi", "finansal", "ticaret", "enflasyon".
If no crisis: tip="yok", beneficiary_sectors=[], sensitive_sectors=[] (K-13 then runs standard VIX-based).
guven: 1-10 (evidence strength; low values mean no change will be applied)."""

    response = get_claude_decision(prompt, mode="morning")

    try:
        import re
        m = re.search(r'\{.*\}', response, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
            # aktif_kriz alanı yoksa ekle (kriz değişikliği yapma default)
            if "aktif_kriz" not in parsed:
                parsed["aktif_kriz"] = {"tip": "belirsiz", "guven": 0}
            return parsed
    except Exception as e:
        print(f"[Makro] AI JSON parse hatası: {e}")

    # Fallback: varsayılan tema + kriz belirsiz
    return {
        "dominant_temalar": [],
        "piyasa_modu": "nötr",
        "aktif_kriz": {"tip": "belirsiz", "guven": 0},  # Kriz tespiti başarısız
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

    print("[Makro] AI tema analizi yapılıyor...")
    analiz = analyze_themes_with_claude(sektor, haberler, güçlü, vix)

    # Her tema için hisse evrenini ekle (analiz Türkçe key'lerle gelir LLM'den)
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

    # LLM çıktısı Türkçe key'ler — İngilizce'ye dönüştür (17 May 2026 migration)
    # LLM prompt'unda Türkçe key zorunluluğu var, kod tarafında EN'ye çeviriyoruz.
    def _theme_tr_to_en(t: dict) -> dict:
        """Tema dict'i: Türkçe LLM çıktısı → İngilizce JSON şema."""
        return {
            "theme_name":         t.get("tema_adi", ""),
            "strength_score":     t.get("güç_skoru"),
            "reason":             t.get("neden", ""),
            "priority_subsector": t.get("öncelikli_alt_dal", ""),
            "suggested_tickers":  t.get("önerilen_hisseler", []),
            "portfolio":          t.get("portföy", ""),
            "urgency":             t.get("aciliyet", ""),
            "stock_universe":     t.get("hisse_evreni", []),
        }

    def _crisis_tr_to_en(c: dict) -> dict:
        """aktif_kriz dict: TR → EN."""
        if not isinstance(c, dict):
            return {"type": "unknown", "confidence": 0}
        return {
            "type":                c.get("tip", "unknown"),
            "confidence":          c.get("guven", 0),
            "evidence":            c.get("kanit", ""),
            "beneficiary_sectors": c.get("beneficiary_sectors", []),
            "sensitive_sectors":   c.get("sensitive_sectors", []),
        }

    def _news_tr_to_en(n: dict) -> dict:
        """Haber dict: TR → EN."""
        return {
            "date":   n.get("tarih", ""),
            "title":  n.get("baslik", ""),
            "source": n.get("kaynak", ""),
        }

    # Sonucu kaydet — İngilizce key'lerle
    output = {
        "date":               datetime.now(TR_TZ).isoformat(),
        "vix":                vix,
        "sector_performance": sektor,
        "dominant_themes":    [_theme_tr_to_en(t) for t in analiz.get("dominant_temalar", [])],
        "avoid_sectors":      analiz.get("kaçınılacak_sektörler", []),
        "market_mode":        analiz.get("piyasa_modu", "nötr"),
        "active_crisis":      _crisis_tr_to_en(analiz.get("aktif_kriz", {})),
        "overview":           analiz.get("genel_yorum", ""),
        "news":               [_news_tr_to_en(n) for n in haberler[:5]],
    }

    out_path = REPO_ROOT / "data" / "macro_intelligence.json"
    json.dump(output, open(out_path, "w"), ensure_ascii=False, indent=2)
    print(f"[Makro] {len(output['dominant_themes'])} tema tespit edildi → {out_path.name}")

    # K-13 kriz matrisini otomatik güncelle (guven ≥ 6 ise)
    _update_k13_matrix_if_changed(analiz.get("aktif_kriz", {}), vix=vix)

    return output


def _update_k13_matrix_if_changed(kriz: dict, vix: float = 0) -> None:
    """AI'nin tespit ettiği kriz matrisini data/k13_crisis_matrix.json'a yazar.

    Şartlar:
    - Yeni kriz tipi mevcuttan farklı olmalı
    - Güven skoru ≥ 6 (düşük güvenle matris değiştirme)
    - beneficiary + sensitive sektör listeleri boş olmamalı (kriz "yok" hariç)
    - Histerezis: aynı kriz 2 gün üst üste tespit edilmiş olmalı (tek gün flip-flop önle)
    """
    new_tip = (kriz.get("tip") or "").lower().strip()
    guven   = int(kriz.get("guven", 0) or 0)

    # Güven düşükse dokunma
    if guven < 6:
        print(f"[K-13] Kriz tespit güveni düşük ({guven}/10), matris dokunulmadı (mevcut: {new_tip or 'belirsiz'})")
        return

    # Geçerli tip mi
    VALID_TYPES = {"yok", "jeopolitik", "pandemi", "finansal", "ticaret", "enflasyon"}
    if new_tip not in VALID_TYPES:
        print(f"[K-13] Geçersiz kriz tipi '{new_tip}', matris dokunulmadı")
        return

    matrix_path = REPO_ROOT / "data" / "k13_crisis_matrix.json"

    # Mevcut matris
    current = {}
    if matrix_path.exists():
        try:
            current = json.load(open(matrix_path))
        except Exception:
            current = {}

    current_tip = (current.get("aktif_kriz") or "").lower().strip()

    # Aynıysa sadece son_guncelleme + gun_sayisi artır
    if new_tip == current_tip:
        gun = int(current.get("ardisik_gun", 1)) + 1
        current["ardisik_gun"]    = gun
        current["son_guncelleme"] = datetime.now(TR_TZ).strftime("%Y-%m-%d")
        current["son_guven"]      = guven
        json.dump(current, open(matrix_path, "w"), ensure_ascii=False, indent=2)
        print(f"[K-13] Aynı kriz ({new_tip}) {gun}. gün, güven {guven}/10")
        return

    # Değişiklik: "kriz yok" hariç, sektör listesi gerekli
    benef_new = kriz.get("beneficiary_sectors") or []
    sens_new  = kriz.get("sensitive_sectors") or []

    if new_tip != "yok" and (not benef_new or not sens_new):
        print(f"[K-13] Yeni kriz tipi '{new_tip}' için sektör listeleri boş, matris dokunulmadı")
        return

    # Histerezis: tek gün flip etmeyi engellemek için state dosyası
    pending_path = REPO_ROOT / "data" / "k13_pending_change.json"
    pending = {}
    if pending_path.exists():
        try:
            pending = json.load(open(pending_path))
        except Exception:
            pending = {}

    pending_tip = (pending.get("tip") or "").lower().strip()
    bugun = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    if pending_tip == new_tip:
        # İkinci gün aynı — artık uygulayabiliriz
        pending_days = pending.get("days", []) + [bugun]
        if len(set(pending_days)) >= 2:
            # Uygula
            yeni_matris = {
                "aktif_kriz":     new_tip,
                "baslangic":      bugun,
                "son_guncelleme": bugun,
                "ardisik_gun":    1,
                "son_guven":      guven,
                "kanit":          kriz.get("kanit", ""),
                "vix_anlik":      vix,
                "aciklama":       f"AI otomatik tespit (güven {guven}/10, 2 gün üst üste)",
                "beneficiary":    benef_new if new_tip != "yok" else [],
                "sensitive":      sens_new  if new_tip != "yok" else [],
                "matris_versiyon": "v4.2_claude_auto",
                "notlar": current.get("notlar", {}),  # Kriz tipi rehber notları koru
            }
            json.dump(yeni_matris, open(matrix_path, "w"), ensure_ascii=False, indent=2)
            pending_path.unlink(missing_ok=True)
            print(f"[K-13] MATRİS GÜNCELLENDİ: {current_tip or 'yok'} → {new_tip} (güven {guven}/10, 2 gün üst üste)")
            return
        else:
            pending["days"] = pending_days
            json.dump(pending, open(pending_path, "w"), ensure_ascii=False, indent=2)
            print(f"[K-13] Kriz değişim adayı '{new_tip}' bekliyor (2. gün onayı gerekiyor)")
            return
    else:
        # Yeni aday — ilk gün, bekleme başlat
        pending = {
            "tip": new_tip,
            "days": [bugun],
            "guven": guven,
            "onceki_tip": current_tip,
        }
        json.dump(pending, open(pending_path, "w"), ensure_ascii=False, indent=2)
        print(f"[K-13] Kriz değişim adayı: {current_tip or 'yok'} → {new_tip} (1. gün, 2. gün onayı bekleniyor)")
