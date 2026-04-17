#!/usr/bin/env python3
"""
Finzora Agent — Tema Yönetim Motoru
=====================================
Her Pazar haftalık tema incelemesi yapar:
  1. Mevcut 7 temanın geçen hafta performansını ölçer
  2. Yeni tema adaylarını web'den araştırır (web_search via Claude API)
  3. Düşük performanslı temayı uyarı listesine alır
  4. Onay gerektirmeden değil — Claude API'ye karar aldırır
  5. Karar verilirse THEMATIC_SYSTEM.md'yi günceller + git push

ÖNEMLI: Bu script Claude API'yi çağırır (claude-sonnet-4-6).
Tema ekleme/çıkarma kararını Claude verir — insan onayı beklenmez.
"""

import json
import os
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")
FMP_KEY    = os.environ.get("FMP_API_KEY", "")
FMP_BASE   = "https://financialmodelingprep.com/stable"

MEMORY_DIR.mkdir(exist_ok=True)

# Tema → ETF eşleştirmesi (performans ölçümü için)
# ── Tema → ETF Sepeti ────────────────────────────────────────────────────────
# DÜZELTME (v2): Tek ETF yerine ağırlıklı ETF sepeti (composite basket)
# Neden? Tek ETF (ör: SMH) temayı eksik temsil eder.
#   AI_ALTYAPI yalnızca yarı iletken değil; güç, soğutma, optik, veri merkezi de içerir.
#   Sepet ağırlıkları Agresif portföy v2 thesis'ine göre ayarlandı.
# Öncelik: Gerçek trade P/L varsa (tema_portfolio_tracker) → ETF sepeti ikincil.

THEME_BASKETS = {
    "AI_ALTYAPI": {
        "SMH":  0.25,   # Yarı iletken (semiconductor)
        "GRID": 0.20,   # Güç şebekesi (power grid)
        "BOTZ": 0.20,   # Yapay zeka & robotik
        "SOXX": 0.15,   # Geniş yar. iletken
        "PAVE": 0.10,   # Altyapı (veri merkezi inşaat)
        "FAN":  0.10,   # Soğutma (fan/cooling — yakın proxy)
    },
    "SAVUNMA_JEOPOLITIK": {
        "ITA":  0.40,   # iShares Defense
        "XAR":  0.30,   # SPDR Aerospace & Defense
        "PPA":  0.30,   # Invesco Defense
    },
    "ENERJI_HAMMADDE": {
        "XLE":  0.40,   # Geniş enerji
        "XOP":  0.30,   # Petrol üreticileri
        "GLD":  0.20,   # Altın
        "COPX": 0.10,   # Bakır madenciliği
    },
    "SAGLIK_BIOTEK": {
        "IBB":  0.40,   # Biotech
        "XLV":  0.35,   # Geniş sağlık
        "ARKG": 0.25,   # Genomik/yenilikçi sağlık
    },
    "FINANS_BANKALAR": {
        "XLF":  0.50,   # Geniş finansal
        "KBE":  0.30,   # Banka ETF
        "IAI":  0.20,   # Yatırım bankacılığı
    },
    "INSAAT_ALTYAPI": {
        "PAVE": 0.50,   # Altyapı
        "ITB":  0.30,   # Konut inşaat
        "XHB":  0.20,   # Ev inşaatçıları
    },
    "TUKETICI_TICARET": {
        "XLY":  0.50,   # Tüketici takdiri
        "XRT":  0.30,   # Perakende
        "MCHI": 0.20,   # Çin tüketimi (global)
    },
}

# Geriye dönük uyumluluk — tek ETF isteyenler için (ilk ETF'i kullan)
THEME_ETFS = {tema: list(sepet.keys())[0] for tema, sepet in THEME_BASKETS.items()}

# Performans eşikleri
WEAK_THEME_THRESHOLD      = -3.0   # 4 hafta RS ortalaması bu altındaysa uyarı
STRONG_CANDIDATE_THRESHOLD = 5.0   # Yeni tema adayı için min RS

def fmp_get(endpoint, params=None):
    if params is None:
        params = {}
    params['apikey'] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ThemeManager] FMP hata: {endpoint} — {e}")
        return None


def _get_etf_return(symbol: str, from_date: str, to_date: str) -> float | None:
    """Tek ETF için tarih aralığı getirisi (%)."""
    data = fmp_get("historical-price-eod/light", {"symbol": symbol, "from": from_date, "to": to_date})
    if not data or len(data) < 5:
        return None
    srt   = sorted(data, key=lambda x: x["date"])
    start = srt[0]["price"]
    end   = srt[-1]["price"]
    return (end - start) / start * 100 if start > 0 else None


def _get_real_trade_rs(theme: str, spy_return: float) -> float | None:
    """
    Gerçek trade P/L'ından tema RS hesaplar.
    tema_portfolio_tracker.py entegrasyonu — veri yoksa None döner.
    """
    try:
        matrix_path = Path(__file__).parent / "memory" / "tema_portfolio_matrix.json"
        if not matrix_path.exists():
            return None
        with open(matrix_path, encoding="utf-8") as f:
            matrix = json.load(f)
        if theme not in matrix:
            return None
        # Tüm portföylerdeki tema ortalama P/L
        all_pnl = []
        for portfoy, stats in matrix[theme].items():
            n   = stats.get("trade_sayisi", 0)
            pnl = stats.get("ortalama_pnl", None)
            if n >= 3 and pnl is not None:   # En az 3 trade → güvenilir
                all_pnl.extend([pnl] * n)
        if len(all_pnl) < 3:
            return None
        avg_pnl = sum(all_pnl) / len(all_pnl)
        return round(avg_pnl - spy_return, 2)
    except Exception:
        return None


def measure_theme_performance(weeks_back: int = 4) -> dict:
    """
    Her temanın son N haftadaki performansını SPY'a göre ölçer.
    RS = tema_getiri - SPY_getiri

    DÜZELTME (v2): İki katmanlı ölçüm:
      1. Gerçek trade P/L (tema_portfolio_tracker) → güvenilir, öncelikli
      2. ETF sepeti (composite basket) → veri yoksa yedek
    Tek ETF proxy yerine ağırlıklı sepet kullanılır.
    """
    from_date = (datetime.now(TR_TZ) - timedelta(weeks=weeks_back)).strftime("%Y-%m-%d")
    to_date   = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    # SPY referans
    spy_return_val = _get_etf_return("SPY", from_date, to_date)
    if spy_return_val is None:
        return {}
    spy_return = spy_return_val

    results = {}
    for theme, basket in THEME_BASKETS.items():
        # Katman 1: Gerçek trade P/L
        real_rs = _get_real_trade_rs(theme, spy_return)
        if real_rs is not None:
            results[theme] = {
                "olcum_yontemi": "gercek_trade",
                "etf_sepeti":    list(basket.keys()),
                "rs":            real_rs,
                "spy_getiri":    round(spy_return, 2),
                "durum":         "ZAYIF" if real_rs < WEAK_THEME_THRESHOLD else "NORMAL",
            }
            continue

        # Katman 2: ETF sepeti composite RS
        weighted_return = 0.0
        total_weight    = 0.0
        etf_details     = {}
        for etf_sym, weight in basket.items():
            etf_ret = _get_etf_return(etf_sym, from_date, to_date)
            if etf_ret is not None:
                weighted_return += etf_ret * weight
                total_weight    += weight
                etf_details[etf_sym] = round(etf_ret, 2)

        if total_weight < 0.4:   # En az %40 veri gelmediyse güvenilmez
            results[theme] = {
                "olcum_yontemi": "etf_sepeti",
                "rs":            None,
                "hata":          f"Yetersiz ETF verisi (ağırlık: {total_weight:.2f})",
            }
            continue

        # Eksik ETF varsa ağırlığı normalize et
        composite_return = weighted_return / total_weight
        rs               = round(composite_return - spy_return, 2)

        results[theme] = {
            "olcum_yontemi": "etf_sepeti",
            "etf_sepeti":    etf_details,
            "tema_getiri":   round(composite_return, 2),
            "spy_getiri":    round(spy_return, 2),
            "rs":            rs,
            "agirlik_kapsamı": round(total_weight, 2),
            "durum":         "ZAYIF" if rs < WEAK_THEME_THRESHOLD else "NORMAL",
        }

    return results


def call_claude_for_theme_decision(performance_data: dict, current_themes: list) -> dict:
    """
    Claude API'ye tema güncelleme kararı aldırır.
    'Yeni tema ekle mi?', 'Zayıf temayı çıkar mı?' sorularını Claude yanıtlar.
    """
    # Performans özetini metin olarak hazırla
    perf_text = "\n".join([
        f"  {tema}: RS={data.get('rs', 'N/A')}% ({data.get('durum', '?')}) — ETF: {data.get('etf', '?')}"
        for tema, data in performance_data.items()
    ])

    weak_themes = [t for t, d in performance_data.items() if d.get('durum') == 'ZAYIF']

    system_prompt = """Sen Finzora AI sistem ajansın. Portföy yönetim sisteminin tema listesini haftalık olarak güncellemekle sorumlusun.

KURALLAR:
1. Zayıf tema (RS < -3%, 4 hafta): Uyarı listesine al. 8. haftada da zayıfsa öner kaldır.
2. Yeni tema: Makro/jeopolitik/teknolojik bir megatrend varsa ve mevcut listede yoksa öneri yap.
3. Her hafta max 1 tema değişikliği (ekle VEYA çıkar — ikisi aynı anda değil).
4. Öneri formatı JSON.

YANIT FORMATI (sadece JSON, başka bir şey yazma):
{
  "karar": "DEGISIKLIK_YOK" | "YENİ_TEMA_OÖNERİ" | "TEMA_CIKARI_ONERISÍ" | "UYARI",
  "tema_adi": "YENİ_TEMA veya CIKARILACAK_TEMA veya null",
  "tema_etf": "ETF sembolü veya null",
  "tema_hisseleri": ["SEM1", "SEM2", ...] veya [],
  "gerekce": "Neden bu karar?",
  "rs_kaniti": "Varsa RS verisi veya haber kanıtı",
  "guven_skoru": 1-10
}"""

    user_prompt = f"""Haftalık tema performans analizi:

MEVCUT TEMALAR ({len(current_themes)}):
{chr(10).join(f'  - {t}' for t in current_themes)}

SON 4 HAFTA PERFORMANSI:
{perf_text}

ZAYIF TEMALAR: {', '.join(weak_themes) if weak_themes else 'Yok'}

Mevcut küresel trendler, jeopolitik durum ve piyasa yapısını değerlendirerek:
1. Zayıf temalar için ne yapmalıyız?
2. Mevcut listede olmayan ama eklenmesi gereken yeni bir megatrend var mı?
3. Kararını JSON formatında ver."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        text = data['content'][0]['text'].strip()

        # JSON parse
        if text.startswith('{'):
            return json.loads(text)
        else:
            # JSON bloğunu çıkar
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())

    except Exception as e:
        print(f"[ThemeManager] Claude API hatası: {e}")

    return {"karar": "HATA", "gerekce": "Claude API yanıt vermedi"}


def load_current_themes() -> list:
    """THEMATIC_SYSTEM.md'den mevcut tema listesini okur."""
    path = REPO_ROOT / "docs" / "THEMATIC_SYSTEM.md"
    if not path.exists():
        return list(THEME_ETFS.keys())

    content = path.read_text(encoding="utf-8")
    themes = []
    for line in content.split("\n"):
        for theme_key in THEME_ETFS.keys():
            if theme_key in line:
                themes.append(theme_key)
                break
    return list(set(themes)) if themes else list(THEME_ETFS.keys())


def apply_theme_change(decision: dict) -> bool:
    """
    Claude'un tema kararını THEMATIC_SYSTEM.md'ye uygular.
    Git commit + push atar.
    """
    karar = decision.get("karar", "DEGISIKLIK_YOK")

    if karar in ("DEGISIKLIK_YOK", "HATA", "UYARI"):
        print(f"[ThemeManager] Değişiklik yok: {karar} — {decision.get('gerekce', '')}")
        return False

    path = REPO_ROOT / "docs" / "THEMATIC_SYSTEM.md"
    content = path.read_text(encoding="utf-8")
    today = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    if karar == "YENİ_TEMA_OÖNERİ":
        tema_adi    = decision.get("tema_adi", "BILINMIYOR")
        tema_etf    = decision.get("tema_etf", "?")
        hisseler    = ", ".join(decision.get("tema_hisseleri", []))
        gerekce     = decision.get("gerekce", "")

        # THEME_ETFS global'i güncelle (runtime)
        THEME_ETFS[tema_adi] = tema_etf

        # Dosyaya yeni tema ekle
        yeni_satir = f"TEMA-N: {tema_adi:<20} → {hisseler}"
        # "TEMA-7:" satırının arkasına ekle
        content = content.replace(
            "```\n\n---",
            f"TEMA-N: {tema_adi:<20} → {hisseler}\n```\n\n---"
        )

        # Güncelleme logu
        log = f"\n\n> **[{today}] AJAN TEMA EKLEDİ:** {tema_adi} (ETF: {tema_etf})\n> Gerekçe: {gerekce}\n"
        content = content.replace("*finzora ai | thematic system", log + "*finzora ai | thematic system")

    elif karar == "TEMA_CIKARI_ONERISÍ":
        tema_adi = decision.get("tema_adi", "")
        gerekce  = decision.get("gerekce", "")

        # Temayı "KALDIRILAN TEMALAR" bölümüne taşı
        log = f"\n\n> **[{today}] AJAN TEMA KALDIRDI:** {tema_adi}\n> Gerekçe: {gerekce}\n"
        content = content.replace("*finzora ai | thematic system", log + "*finzora ai | thematic system")

        if tema_adi in THEME_ETFS:
            del THEME_ETFS[tema_adi]

    path.write_text(content, encoding="utf-8")

    # Git push
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name", "Finzora Agent"], check=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add", "docs/THEMATIC_SYSTEM.md", "agent/memory/theme_scores.json"], check=True)
        subprocess.run(["git", "commit", "-m", f"🎯 [Agent] Tema güncellendi: {karar} — {decision.get('tema_adi', '')} | {decision.get('gerekce', '')[:80]}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"[ThemeManager] ✅ Git push başarılı: {karar}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ThemeManager] Git hatası: {e}")
        return False


def save_weekly_review(performance: dict, decision: dict):
    """Haftalık inceleme sonucunu kaydet."""
    path = MEMORY_DIR / "theme_weekly_reviews.json"
    reviews = {"incelemeler": []}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            reviews = json.load(f)

    if "incelemeler" not in reviews:


        reviews["incelemeler"] = []


    reviews["incelemeler"].append({
        "tarih":       datetime.now(TR_TZ).strftime("%Y-%m-%d"),
        "performans":  performance,
        "karar":       decision,
    })
    reviews["incelemeler"] = reviews["incelemeler"][-52:]  # Son 52 hafta

    with open(path, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)


def run_weekly_theme_review():
    """
    Ana haftalık tema incelemesi.
    Her Pazar otomatik çalışır (GitHub Actions veya manuel tetikleme).
    """
    print(f"\n{'='*50}")
    print(f"[ThemeManager] HAFTALIK TEMA İNCELEMESİ — {datetime.now(TR_TZ).strftime('%Y-%m-%d')}")
    print('='*50)

    # 1. Performans ölç
    print("[ThemeManager] Tema ETF performansları ölçülüyor...")
    performance = measure_theme_performance(weeks_back=4)

    if not performance:
        print("[ThemeManager] FMP verisi alınamadı, inceleme iptal")
        return

    print("\n--- TEMA PERFORMANSLARI (son 4 hafta, SPY'a göre RS) ---")
    for tema, data in sorted(performance.items(), key=lambda x: x[1].get('rs', 0), reverse=True):
        rs     = data.get('rs', 'N/A')
        durum  = data.get('durum', '?')
        emoji  = "✅" if durum == "NORMAL" else "⚠️"
        print(f"  {emoji} {tema:<25}: RS={rs:+.1f}% | ETF: {data.get('etf', '?')}")

    # 2. Mevcut temaları yükle
    current_themes = load_current_themes()

    # 3. Claude'a karar aldır
    print("\n[ThemeManager] Claude API'ye tema kararı soruluyor...")
    decision = call_claude_for_theme_decision(performance, current_themes)

    print(f"\n--- CLAUDE KARARI ---")
    print(f"  Karar: {decision.get('karar')}")
    print(f"  Tema: {decision.get('tema_adi')}")
    print(f"  Gerekçe: {decision.get('gerekce', '')[:120]}")
    print(f"  Güven: {decision.get('guven_skoru', 0)}/10")

    # 4. Kaydet
    save_weekly_review(performance, decision)

    # 5. Değişiklik varsa uygula
    if decision.get("karar") not in ("DEGISIKLIK_YOK", "UYARI", "HATA"):
        guven = decision.get("guven_skoru", 0)
        if guven >= 7:  # Yüksek güven gerektiriyor
            print(f"\n[ThemeManager] Değişiklik uygulanıyor (güven: {guven}/10)...")
            apply_theme_change(decision)
        else:
            print(f"\n[ThemeManager] Güven düşük ({guven}/10), değişiklik önerisi kuyruğa alındı")
            # Öneriler kuyruğuna ekle
            from learning_engine import add_proposed_change
            add_proposed_change(
                change_type="tema_degisiklik",
                description=f"{decision.get('karar')}: {decision.get('tema_adi', '')}",
                rationale=decision.get("gerekce", ""),
                proposed_by="theme_manager_agent",
                requires_backtest=False,
            )

    print(f"\n[ThemeManager] İnceleme tamamlandı.")
    return {"performans": performance, "karar": decision}


if __name__ == "__main__":
    run_weekly_theme_review()
