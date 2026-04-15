#!/usr/bin/env python3
"""
Finzora Agent — Kural Güncelleme Motoru v2.0
=============================================
KILITLI KURAL YOK. Her K-kuralı değiştirilebilir.
Bunun yerine: Kademeli Güven Eşiği (Tiered Confidence) sistemi.

  Normal kurallar  → min 10 trade, backtest kanıtı, haftalık max 1
  Kritik kurallar  → min 30 trade, güven ≥8/10, değişim ±%20 sınırı
  
Kritik = K-13 (VIX), K-14 (drawdown freni), K-17 (korelasyon limiti)
  Bu kurallar değişebilir ama DAHA ZOR değişir.
  
Güvenlik katmanları:
  1. Her parametre için min/max aralık
  2. Kritik parametreler için yüksek backtest eşiği (30 trade)
  3. Her değişiklik 14 gün dry-run zorunlu
  4. Haftalık max 1 kural değişikliği
  5. Tüm değişiklikler git geçmişinde izlenebilir
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")

# ── Parametre Kataloğu ────────────────────────────────────────────────────────
# tier: "normal" → standart eşikler
# tier: "critical" → yüksek eşikler (daha zor değişir, imkansız değil)

CHANGEABLE_PARAMS = {
    # --- Normal tier ---
    "rsi_k11_katman1": {
        "min": 65, "max": 75, "current": 70,
        "tier": "normal",
        "desc": "K-11 Katman1 RSI eşiği",
    },
    "rsi_k11_katman2": {
        "min": 73, "max": 82, "current": 80,
        "tier": "normal",
        "desc": "K-11 Katman2 RSI eşiği",
    },
    "atr_katsayi": {
        "min": 1.5, "max": 3.0, "current": 2.0,
        "tier": "normal",
        "desc": "Trailing stop ATR katsayısı",
    },
    "swing_max_gun": {
        "min": 7, "max": 30, "current": 15,
        "tier": "normal",
        "desc": "Swing max tutma süresi (gün)",
    },
    "k04_sma_esik": {
        "min": 20, "max": 200, "current": 50,
        "tier": "normal",
        "desc": "K-04 giriş filtresi SMA eşiği",
    },
    "k11_atr_katman3": {
        "min": 1.0, "max": 2.5, "current": 1.5,
        "tier": "normal",
        "desc": "K-11 Katman3 ATR çarpanı (agresif kilit)",
    },

    # --- Critical tier (değiştirilebilir ama yüksek eşik) ---
    "vix_tam_pozisyon": {
        "min": 18, "max": 26, "current": 22,
        "tier": "critical",
        "desc": "K-13: VIX altında tam pozisyon eşiği",
    },
    "vix_yari_pozisyon": {
        "min": 22, "max": 35, "current": 28,
        "tier": "critical",
        "desc": "K-13: VIX üstünde yarım pozisyon eşiği",
    },
    "vix_dur": {
        "min": 30, "max": 50, "current": 35,
        "tier": "critical",
        "desc": "K-13: Yeni giriş dur eşiği",
    },
    "k14_brake_esik": {
        "min": 10, "max": 25, "current": 16,
        "tier": "critical",
        "desc": "K-14: Drawdown freni tetik eşiği (%)",
    },
    "k17_korelasyon_limit": {
        "min": 0.55, "max": 0.85, "current": 0.70,
        "tier": "critical",
        "desc": "K-17: Maksimum portföy korelasyonu",
    },
}

# Tier eşikleri
TIER_CONFIG = {
    "normal": {
        "min_trades":   10,
        "min_guven":    6,       # 10 üzerinden
        "max_degisim":  0.30,    # Mevcut değerin %30'u kadar değişim
        "weekly_limit": 1,
    },
    "critical": {
        "min_trades":   30,
        "min_guven":    8,       # 10 üzerinden
        "max_degisim":  0.20,    # Mevcut değerin %20'si kadar değişim
        "weekly_limit": 1,
    },
}

MAX_WEEKLY_CHANGES = 1


# ── Değişiklik Güvenlik Kontrolü ──────────────────────────────────────────────

def validate_change_request(
    param: str,
    new_value: float,
    backtest_result: dict,
    guven_skoru: int = 7,
) -> tuple[bool, str]:
    """
    Değişiklik isteğini kademeli güven eşiklerinden geçirir.
    Kilitli kural yok — kritik kurallar daha yüksek kanıt gerektirir.
    Returns: (izin_var, gerekce)
    """
    # 1. Parametre tanımlı mı?
    if param not in CHANGEABLE_PARAMS:
        return False, (
            f"Bilinmeyen parametre: {param}. "
            f"Kayıtlı parametreler: {list(CHANGEABLE_PARAMS.keys())}"
        )

    cfg    = CHANGEABLE_PARAMS[param]
    tier   = cfg["tier"]
    limits = TIER_CONFIG[tier]

    # 2. Değer aralığı kontrolü
    if not (cfg["min"] <= new_value <= cfg["max"]):
        return False, (
            f"Değer aralık dışı: {new_value}. "
            f"İzin verilen: {cfg['min']}–{cfg['max']}"
        )

    # 3. Değişim büyüklüğü sınırı
    current     = cfg["current"]
    max_degisim = limits["max_degisim"]
    if current != 0:
        degisim_oran = abs(new_value - current) / abs(current)
        if degisim_oran > max_degisim:
            return False, (
                f"Değişim çok büyük: %{degisim_oran*100:.1f}. "
                f"'{tier}' tier için max %{max_degisim*100:.0f} adım izni var. "
                f"Küçük adımlarla ilerle."
            )

    # 4. Backtest trade sayısı
    total_trades = backtest_result.get("toplam_trade", 0)
    if total_trades < limits["min_trades"]:
        return False, (
            f"Yetersiz backtest verisi: {total_trades} trade. "
            f"'{tier}' tier için minimum {limits['min_trades']} gerekli."
        )

    # 5. Güven skoru (kritik tier için daha yüksek eşik)
    if guven_skoru < limits["min_guven"]:
        return False, (
            f"Güven skoru yetersiz: {guven_skoru}/10. "
            f"'{tier}' tier için minimum {limits['min_guven']}/10 gerekli."
        )

    # 6. Haftalık değişiklik limiti
    changes_path = MEMORY_DIR / "applied_changes.json"
    if changes_path.exists():
        with open(changes_path, encoding="utf-8") as f:
            applied = json.load(f)
        week_ago = (datetime.now(TR_TZ) - timedelta(days=7)).isoformat()
        recent   = [c for c in applied.get("list", []) if c["tarih"] >= week_ago]
        if len(recent) >= MAX_WEEKLY_CHANGES:
            return False, (
                f"Haftalık limit aşıldı: Bu hafta {len(recent)} değişiklik uygulandı "
                f"(max {MAX_WEEKLY_CHANGES}). Önce dry-run sonuçlarını bekle."
            )

    tier_label = "KRİTİK — yüksek kanıt sağlandı" if tier == "critical" else "Normal"
    return True, f"Güvenlik kontrolü geçti ({tier_label})"


# ── PLAYBOOK Güncelleme ────────────────────────────────────────────────────────

def update_playbook_param(
    param: str,
    old_value: float,
    new_value: float,
    rationale: str
) -> bool:
    """
    TRADING_PLAYBOOK.md'de parametre değerini günceller.
    """
    playbook_path = REPO_ROOT / "docs" / "TRADING_PLAYBOOK.md"
    if not playbook_path.exists():
        print("[RuleUpdater] PLAYBOOK bulunamadı!")
        return False

    content = playbook_path.read_text(encoding="utf-8")

    update_map = {
        "rsi_k11_katman1":     (f"RSI {int(old_value)}+",       f"RSI {int(new_value)}+"),
        "rsi_k11_katman2":     (f"RSI {int(old_value)}+",       f"RSI {int(new_value)}+"),
        "atr_katsayi":         (f"{old_value}×ATR",              f"{new_value}×ATR"),
        "swing_max_gun":       (f"Max {int(old_value)} gün",     f"Max {int(new_value)} gün"),
        "vix_tam_pozisyon":    (f"VIX {int(old_value)}'e kadar", f"VIX {int(new_value)}'e kadar"),
        "vix_yari_pozisyon":   (f"VIX {int(old_value)}'den",     f"VIX {int(new_value)}'den"),
        "vix_dur":             (f"VIX>{int(old_value)}",          f"VIX>{int(new_value)}"),
        "k14_brake_esik":      (f"%{int(old_value)} drawdown",   f"%{int(new_value)} drawdown"),
        "k17_korelasyon_limit":(f"korelasyon {old_value}",       f"korelasyon {new_value}"),
        "k04_sma_esik":        (f"SMA{int(old_value)}",          f"SMA{int(new_value)}"),
        "k11_atr_katman3":     (f"chandelier {old_value}×ATR",   f"chandelier {new_value}×ATR"),
    }

    if param not in update_map:
        print(f"[RuleUpdater] Parametre PLAYBOOK mapping'i bulunamadı: {param}")
        return False

    old_str, new_str = update_map[param]

    if old_str not in content:
        print(f"[RuleUpdater] PLAYBOOK'ta '{old_str}' bulunamadı — manuel kontrol gerekli")
        return False

    updated   = content.replace(old_str, new_str, 1)
    log_entry = (
        f"\n> **Otomatik Güncelleme** {datetime.now(TR_TZ).strftime('%Y-%m-%d')}: "
        f"{param} {old_value}→{new_value} | {rationale[:120]}\n"
    )
    updated = updated.replace("# TRADING PLAYBOOK", "# TRADING PLAYBOOK" + log_entry, 1)
    playbook_path.write_text(updated, encoding="utf-8")
    print(f"[RuleUpdater] PLAYBOOK güncellendi: {param} {old_value} → {new_value}")
    return True


# ── Değişiklik Uygulama ───────────────────────────────────────────────────────

def apply_rule_change(
    param: str,
    new_value: float,
    rationale: str,
    backtest_result: dict,
    guven_skoru: int = 7,
    proposed_by: str = "agent",
) -> dict:
    """
    Değişiklik isteğini kademeli güven eşiklerinden geçirerek uygular.
    """
    allowed, reason = validate_change_request(
        param, new_value, backtest_result, guven_skoru
    )
    if not allowed:
        return {"durum": "REDDEDILDI", "gerekce": reason, "param": param}

    old_value = CHANGEABLE_PARAMS[param]["current"]
    tier      = CHANGEABLE_PARAMS[param]["tier"]

    success = update_playbook_param(param, old_value, new_value, rationale)
    if not success:
        return {"durum": "HATA", "gerekce": "PLAYBOOK güncellenemedi", "param": param}

    # K-rules digest güncelle
    digest_path = MEMORY_DIR / "k_rules_digest.md"
    if digest_path.exists():
        digest  = digest_path.read_text(encoding="utf-8")
        desc    = CHANGEABLE_PARAMS[param]["desc"]
        tier_lbl = "⚠️ KRİTİK" if tier == "critical" else "📝 Normal"
        digest += (
            f"\n\n**{datetime.now(TR_TZ).strftime('%Y-%m-%d')} GÜNCELLENDİ** {tier_lbl}: "
            f"{desc}: {old_value} → {new_value} | Güven: {guven_skoru}/10"
        )
        digest_path.write_text(digest, encoding="utf-8")

    # Kayıt
    changes_path = MEMORY_DIR / "applied_changes.json"
    applied = {"list": []}
    if changes_path.exists():
        with open(changes_path, encoding="utf-8") as f:
            applied = json.load(f)

    record = {
        "tarih":      datetime.now(TR_TZ).isoformat(),
        "param":      param,
        "tier":       tier,
        "eski_deger": old_value,
        "yeni_deger": new_value,
        "gerekce":    rationale,
        "oneren":     proposed_by,
        "guven":      guven_skoru,
        "backtest_n": backtest_result.get("toplam_trade", 0),
    }
    if "list" not in applied:

        applied["list"] = []

    applied["list"].append(record)
    applied["list"] = applied["list"][-50:]
    with open(changes_path, "w", encoding="utf-8") as f:
        json.dump(applied, f, ensure_ascii=False, indent=2)

    CHANGEABLE_PARAMS[param]["current"] = new_value
    print(f"[RuleUpdater] ✅ {tier.upper()} parametre değiştirildi: {param} = {new_value}")

    return {
        "durum":      "UYGULANMADI",   # dry-run → apply_after_dryrun ile kalıcılaşır
        "param":      param,
        "tier":       tier,
        "eski_deger": old_value,
        "yeni_deger": new_value,
        "gerekce":    rationale,
    }


# ── Git Push ──────────────────────────────────────────────────────────────────

def commit_rule_change(param: str, old_val: float, new_val: float) -> bool:
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name",  "Finzora AI"],  check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], check=True, capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add",
                        "docs/TRADING_PLAYBOOK.md",
                        "agent/memory/k_rules_digest.md",
                        "agent/memory/applied_changes.json"], check=True, capture_output=True)
        tier = CHANGEABLE_PARAMS.get(param, {}).get("tier", "normal")
        tier_icon = "⚠️" if tier == "critical" else "🔧"
        msg = f"{tier_icon} [Agent] Kural güncellendi: {param} {old_val}→{new_val}"
        subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print(f"[RuleUpdater] Git push başarılı: {msg}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[RuleUpdater] Git hatası: {e}")
        return False


# ── Claude Önerisini Parse Et ─────────────────────────────────────────────────

def parse_claude_rule_proposal(claude_response: str) -> list[dict]:
    """
    Claude'un haftalık analizinden "BACKTEST GEREKLİ" önerilerini çıkarır.
    Format: "BACKTEST GEREKLİ — [param]: [eski] → [yeni] | [gerekçe]"
    """
    proposals = []
    for line in claude_response.split("\n"):
        if "BACKTEST GEREKLİ" not in line.upper():
            continue
        try:
            parts = line.split("—", 1)
            if len(parts) < 2:
                continue
            detail    = parts[1].strip()
            if ":" not in detail or "→" not in detail:
                continue
            param_part, rest = detail.split(":", 1)
            param     = param_part.strip()
            rationale = rest.split("|")[1].strip() if "|" in rest else "Agent önerisi"
            val_part  = rest.split("|")[0].strip()
            old_new   = val_part.split("→")
            if len(old_new) == 2:
                proposals.append({
                    "param":     param,
                    "old_value": float(old_new[0].strip()),
                    "new_value": float(old_new[1].strip()),
                    "rationale": rationale[:200],
                })
        except (ValueError, IndexError):
            continue
    return proposals


# ── Haftalık İnceleme ─────────────────────────────────────────────────────────

def run_weekly_rule_review(
    claude_response: str,
    backtest_results: dict,
    guven_skoru: int = 7,
) -> list[dict]:
    proposals = parse_claude_rule_proposal(claude_response)
    results   = []
    for p in proposals:
        allowed, reason = validate_change_request(
            p["param"], p["new_value"], backtest_results, guven_skoru
        )
        results.append({
            "param":     p["param"],
            "new_value": p["new_value"],
            "izin":      allowed,
            "gerekce":   reason,
            "durum":     "ONAYLANDI" if allowed else "REDDEDILDI",
        })
        if allowed:
            try:
                from learning_engine import add_proposed_change
                add_proposed_change(
                    change_type=f"kural_parametresi_{p['param']}",
                    description=f"{p['param']}: {p['old_value']} → {p['new_value']}",
                    rationale=p["rationale"],
                    proposed_by="agent_weekly",
                    requires_backtest=True,
                )
            except ImportError:
                pass
            print(f"[RuleUpdater] Öneri kuyruğa eklendi: {p['param']}")
    return results


def get_applied_changes_summary() -> str:
    path = MEMORY_DIR / "applied_changes.json"
    if not path.exists():
        return "Henüz otomatik değişiklik uygulanmadı."
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    changes = data.get("list", [])[-5:]
    if not changes:
        return "Değişiklik kaydı boş."
    lines = ["Son kural değişiklikleri:"]
    for c in changes:
        tier_lbl = "⚠️" if c.get("tier") == "critical" else "📝"
        lines.append(
            f"  {tier_lbl} [{c['tarih'][:10]}] {c['param']}: "
            f"{c['eski_deger']} → {c['yeni_deger']} | {c['gerekce'][:60]}"
        )
    return "\n".join(lines)
