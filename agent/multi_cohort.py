#!/usr/bin/env python3
"""
Finzora Agent — Multi-Cohort + Blind Spot Sistemi
===================================================
ATLAS'ın en ilginç keşfi:
  "Rejim dedektörünü biz inşa etmedik — hangisi kazandığını takip ettik."

Multi-cohort:
  - SHORT_COHORT: Son 30 günlük tahmin geçmişine göre ağırlıklı kararlar
  - LONG_COHORT: Son 6 aylık tahmin geçmişine göre ağırlıklı kararlar
  - JANUS: İkisi arasındaki farktan rejim değişimi tespiti
  
  Mantık: Kısa pencere kazanıyorsa → YENİ REJİM (tarihi pattern işe yaramaz)
          Uzun pencere kazanıyorsa → TARİHİ REJİM (geçmiş pattern çalışır)

Blind Spot Tespiti:
  - ATLAS'ın gerçek hayat keşfi: Sistem kendi CIO'sunun zayıf olduğunu
    otomatik tespit etti ve ağırlığını minimum'a çekti.
  - Aynı hata 3+ kez → Yeni uzman agent açılır
  - Bilgi boşluğu tespiti: Debate'de tekrarlayan "göz ardı edilen" konular
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from claude_agent import get_claude_decision

MEMORY_DIR        = Path(__file__).parent / "memory"
COHORT_STATE_PATH = MEMORY_DIR / "cohort_state.json"
BLIND_SPOT_PATH   = MEMORY_DIR / "blind_spots.json"
DEBATE_LOG        = MEMORY_DIR / "debate_log.json"


# ── Multi-Cohort Sistemi ──────────────────────────────────────────────────────

def calculate_cohort_accuracy(window_days: int) -> dict:
    """
    Belirli bir zaman penceresindeki tahmin doğruluğunu hesaplar.
    """
    from prediction_logger import _load_log

    log   = _load_log()
    preds = log.get("tahminler", [])
    cutoff = (datetime.now() - timedelta(days=window_days)).isoformat()

    # Penceredeki skorlanmış tahminler
    window_preds = [
        p for p in preds
        if p.get("tarih", "") >= cutoff
        and p.get("durum") == "SKORLANDI"
    ]

    if not window_preds:
        return {"n": 0, "avg_score": None, "sharpe": None}

    scores = [p.get("son_skor", 0) for p in window_preds]
    n      = len(scores)
    avg    = sum(scores) / n
    std    = (sum((s - avg) ** 2 for s in scores) / n) ** 0.5 if n > 1 else 1.0
    sharpe = avg / std if std > 0 else 0

    return {
        "n":         n,
        "avg_score": round(avg, 3),
        "sharpe":    round(sharpe, 3),
        "pencere":   window_days,
    }


def run_janus_detection() -> dict:
    """
    JANUS: Kısa vs uzun pencere karşılaştırması → rejim tespiti.
    
    ATLAS'ın bulgusu: "Biz rejim dedektörü yazmadık, o kendiliğinden ortaya çıktı."
    """
    short_acc = calculate_cohort_accuracy(30)   # Son 30 gün
    long_acc  = calculate_cohort_accuracy(180)  # Son 6 ay

    short_sharpe = short_acc.get("sharpe")
    long_sharpe  = long_acc.get("sharpe")

    # Yeterli veri yoksa
    if short_sharpe is None or long_sharpe is None:
        return {
            "rejim":        "BELIRSIZ",
            "short_sharpe": short_sharpe,
            "long_sharpe":  long_sharpe,
            "yeterli_veri": False,
            "mesaj":        f"Yeterli veri yok (kısa: {short_acc['n']}, uzun: {long_acc['n']})",
        }

    diff = short_sharpe - long_sharpe

    # Rejim tespiti
    if diff > 0.5:
        rejim = "YENİ_REJİM"
        aciklama = "Kısa pencere kazanıyor → Tarihi pattern işe yaramıyor. Yeni rejim!"
    elif diff < -0.5:
        rejim = "TARİHİ_REJİM"
        aciklama = "Uzun pencere kazanıyor → Tarihi pattern çalışıyor."
    else:
        rejim = "GEÇİŞ"
        aciklama = "İkisi yakın → Belirsiz, geçiş dönemi."

    result = {
        "rejim":        rejim,
        "aciklama":     aciklama,
        "short_sharpe": short_sharpe,
        "long_sharpe":  long_sharpe,
        "fark":         round(diff, 3),
        "yeterli_veri": True,
        "tarih":        datetime.now().isoformat(),
    }

    # Kaydet
    _save_cohort_state(result)
    print(f"[JANUS] {rejim}: kısa={short_sharpe}, uzun={long_sharpe}, fark={diff:.3f}")
    return result


def _save_cohort_state(state: dict):
    with open(COHORT_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_cohort_state() -> dict:
    if COHORT_STATE_PATH.exists():
        with open(COHORT_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"rejim": "BELIRSIZ", "yeterli_veri": False}


# ── Blind Spot Tespiti ────────────────────────────────────────────────────────

def detect_blind_spots() -> list[dict]:
    """
    Tekrarlayan hataları tespit eder.
    ATLAS'ın keşfi: Aynı konu 3+ debate'de "göz ardı edildi" olarak çıkarsa
    yeni uzman agent açılır.
    """
    if not DEBATE_LOG.exists():
        return []

    with open(DEBATE_LOG, encoding="utf-8") as f:
        log = json.load(f)

    debates = log.get("tartismalar", [])

    # "göz ardı edilen" konuları topla
    goz_ardi = []
    for d in debates[-30:]:  # Son 30 tartışma
        nihai = d.get("nihai", {})
        konu  = nihai.get("göz_ardı_edilen", "").strip().lower()
        if konu and len(konu) > 10:
            goz_ardi.append(konu)

    # 3+ kez tekrar eden konular
    blind_spots = []
    counter     = Counter(goz_ardi)
    for konu, count in counter.most_common():
        if count >= 3:
            blind_spots.append({
                "konu":    konu,
                "frekans": count,
                "oneri":   f"Yeni uzman agent önerisi: '{konu}' için",
            })

    # Ayrıca tahmin hatalarını incele
    error_patterns = _analyze_prediction_errors()
    blind_spots.extend(error_patterns)

    if blind_spots:
        _save_blind_spots(blind_spots)
        print(f"[BlindSpot] {len(blind_spots)} blind spot tespit edildi.")

    return blind_spots


def _analyze_prediction_errors() -> list[dict]:
    """Tahmin hatalarından pattern çıkarır."""
    from prediction_logger import _load_log

    log   = _load_log()
    preds = log.get("tahminler", [])

    # Skorlanan ve yanlış olan tahminler
    yanlis = [
        p for p in preds
        if p.get("durum") == "SKORLANDI" and (p.get("son_skor") or 0) < -0.5
    ]

    if not yanlis:
        return []

    # Hangi agent en çok yanılıyor?
    agent_hatalar = Counter(p.get("agent", "") for p in yanlis)
    patterns = []

    for agent, count in agent_hatalar.most_common(2):
        if count >= 3:
            # Bu agent hangi yönde yanılıyor?
            agent_preds = [p for p in yanlis if p.get("agent") == agent]
            yon_hatalar = Counter(p.get("yon", "") for p in agent_preds)
            en_cok_hata = yon_hatalar.most_common(1)[0][0] if yon_hatalar else "?"

            patterns.append({
                "konu":    f"{agent} {en_cok_hata} yönünde sistematik hata yapıyor",
                "frekans": count,
                "oneri":   f"{agent} prompt'u revize edilmeli — {en_cok_hata} bias var",
            })

    return patterns


def _save_blind_spots(spots: list):
    existing = []
    if BLIND_SPOT_PATH.exists():
        with open(BLIND_SPOT_PATH, encoding="utf-8") as f:
            existing = json.load(f).get("spots", [])

    data = {
        "son_guncelleme": datetime.now().isoformat(),
        "spots":          spots + existing,
    }
    data["spots"] = data["spots"][:50]

    with open(BLIND_SPOT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Yeni Uzman Agent Önerisi ──────────────────────────────────────────────────

def propose_new_specialist(blind_spot: dict) -> dict:
    """
    Tespit edilen blind spot için yeni uzman agent önerir.
    ATLAS'ta olduğu gibi: Sistem bilmediği alanı tespit edince yeni agent açar.
    """
    konu = blind_spot.get("konu", "")

    prompt = f"""
Finzora trading sisteminde şu blind spot tespit edildi:
"{konu}" (frekans: {blind_spot.get('frekans', 0)} kez)

Bu blind spot için yeni bir uzman agent tasarla:

ÇIKTI FORMAT (SADECE JSON):
{{
  "agent_adi": "YENI_AGENT_ADI",
  "uzmanlik_alani": "Ne konuda uzman?",
  "sistem_promptu": "Bu agent'ın sistem promptu (Türkçe, 100-200 kelime)",
  "fitness_metrigi": "Bu agent nasıl skorlanır?",
  "ilk_agirlik": 1.0
}}
"""

    response = get_claude_decision(prompt, mode="monitor")

    try:
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            proposal = json.loads(match.group())
            proposal["blind_spot"] = blind_spot
            proposal["olusturma"]  = datetime.now().isoformat()
            proposal["durum"]      = "ONAY_BEKLIYOR"

            # Öneri kuyruğuna ekle
            _queue_new_agent(proposal)
            print(f"[BlindSpot] Yeni agent önerildi: {proposal.get('agent_adi', '?')}")
            return proposal
    except (json.JSONDecodeError, AttributeError):
        pass

    return {}


def _queue_new_agent(proposal: dict):
    """Yeni agent önerisini kuyruğa ekle."""
    from learning_engine import add_proposed_change

    add_proposed_change(
        change_type   = f"yeni_agent_{proposal.get('agent_adi', 'bilinmiyor')}",
        description   = proposal.get("uzmanlik_alani", ""),
        rationale     = f"Blind spot: {proposal.get('blind_spot', {}).get('konu', '')}",
        proposed_by   = "blind_spot_detector",
        requires_backtest = False,
    )


# ── Haftalık Blind Spot Raporu ────────────────────────────────────────────────

def run_weekly_blind_spot_analysis() -> str:
    """
    Haftalık blind spot analizi + JANUS rejim raporu.
    """
    janus   = run_janus_detection()
    spots   = detect_blind_spots()

    lines = ["=== COHORT + BLIND SPOT ANALİZİ ===\n"]

    # JANUS
    lines.append(f"JANUS Rejim: {janus.get('rejim', '?')}")
    if janus.get("yeterli_veri"):
        lines.append(f"  Kısa Sharpe: {janus['short_sharpe']} | Uzun Sharpe: {janus['long_sharpe']}")
        lines.append(f"  → {janus.get('aciklama', '')}")
    else:
        lines.append(f"  → {janus.get('mesaj', 'Veri bekleniyor')}")
    lines.append("")

    # Blind spots
    if spots:
        lines.append(f"Tespit Edilen Blind Spot'lar ({len(spots)}):")
        for s in spots[:3]:
            lines.append(f"  [{s['frekans']}x] {s['konu'][:80]}")
            lines.append(f"  → {s['oneri'][:80]}")
    else:
        lines.append("Blind spot tespit edilmedi.")

    return "\n".join(lines)


def get_cohort_context() -> str:
    """Sabah analizi için cohort durumu."""
    state = load_cohort_state()

    if not state.get("yeterli_veri"):
        return "JANUS: Henüz yeterli tahmin verisi yok (min 5 skorlanan tahmin gerekli)."

    return (
        f"JANUS Rejim Durumu: {state.get('rejim', '?')} | "
        f"Kısa Sharpe: {state.get('short_sharpe', '?')} | "
        f"Uzun Sharpe: {state.get('long_sharpe', '?')}\n"
        f"→ {state.get('aciklama', '')}"
    )
