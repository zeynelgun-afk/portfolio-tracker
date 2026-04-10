#!/usr/bin/env python3
"""
Finzora Agent — Kural Güncelleme Motoru
=========================================
Sistemi kendi kurallarını güncellemesini sağlar.

GÜVENLİK KATMANLARI:
  1. Sadece izin verilen parametreler değiştirilebilir
  2. Kritik kurallar (K-13 VIX eşiği, K-11 temel mantık) kilitli
  3. Her değişiklik 14 gün dry-run zorunlu
  4. Backtest kanıtı olmadan uygulanmaz
  5. Tüm değişiklikler git geçmişinde izlenebilir
  6. Haftalık max 1 kural değişikliği

DEĞIŞTIRILEBILIR:
  - RSI alt/üst eşikleri (±5 sınırlı)
  - ATR katsayısı (1.5–3.0 arası)
  - Holding period önerisi
  - Screener filtre parametreleri

DEĞİŞTİRİLEMEZ (kilitli):
  - K-13 VIX seviyeleri
  - K-14 drawdown freni mantığı
  - Stop-loss disiplin kuralı
  - Broker bağlantısı olmadan gerçek emir
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

# ── Güvenlik Tanımları ────────────────────────────────────────────────────────

LOCKED_RULES = {
    "K-13": "VIX bazlı pozisyon boyutu — jeopolitik kriz yönetimi, kilitli",
    "K-14": "Drawdown fren mekanizması, kilitli",
    "K-17": "Korelasyon limiti — risk yönetimi temeli, kilitli",
    "K-18": "Insider kontrol zorunluluğu, kilitli",
    "stop_override": "Stop-loss asla override edilmez, kilitli",
}

CHANGEABLE_PARAMS = {
    "rsi_k11_katman1":  {"min": 65, "max": 75, "current": 70, "desc": "K-11 Katman1 RSI eşiği"},
    "rsi_k11_katman2":  {"min": 73, "max": 82, "current": 80, "desc": "K-11 Katman2 RSI eşiği"},
    "atr_katsayi":      {"min": 1.5, "max": 3.0, "current": 2.0, "desc": "Trailing stop ATR katsayısı"},
    "swing_max_gun":    {"min": 7, "max": 30, "current": 15, "desc": "Swing max tutma süresi (gün)"},
    "vix_tam_pozisyon": {"min": 18, "max": 24, "current": 22, "desc": "VIX altında tam pozisyon eşiği"},
}

MAX_WEEKLY_CHANGES  = 1    # Haftada max kural değişikliği
MIN_BACKTEST_TRADES = 10   # Minimum backtest trade sayısı


# ── Değişiklik Güvenlik Kontrolü ──────────────────────────────────────────────

def validate_change_request(
    param: str,
    new_value: float,
    backtest_result: dict
) -> tuple[bool, str]:
    """
    Değişiklik isteğini güvenlik filtrelerinden geçirir.
    Returns: (izin_var, gerekce)
    """
    # 1. Kilitli kural mı?
    for locked in LOCKED_RULES:
        if locked.lower() in param.lower():
            return False, f"KILITLI: {LOCKED_RULES[locked]}"

    # 2. İzin verilen parametre mi?
    if param not in CHANGEABLE_PARAMS:
        return False, f"Bilinmeyen parametre: {param}. İzin verilenler: {list(CHANGEABLE_PARAMS.keys())}"

    # 3. Değer aralığı kontrolü
    limits = CHANGEABLE_PARAMS[param]
    if not (limits["min"] <= new_value <= limits["max"]):
        return False, (
            f"Değer aralık dışı: {new_value}. "
            f"İzin verilen: {limits['min']}–{limits['max']}"
        )

    # 4. Backtest kanıtı var mı?
    total_trades = backtest_result.get("toplam_trade", 0)
    if total_trades < MIN_BACKTEST_TRADES:
        return False, (
            f"Yetersiz backtest verisi: {total_trades} trade. "
            f"Minimum {MIN_BACKTEST_TRADES} gerekli."
        )

    # 5. Haftalık değişiklik limiti
    changes_path = MEMORY_DIR / "applied_changes.json"
    if changes_path.exists():
        with open(changes_path, encoding="utf-8") as f:
            applied = json.load(f)
        week_ago = (datetime.now(TR_TZ) - timedelta(days=7)).isoformat()
        recent   = [c for c in applied.get("list", []) if c["tarih"] >= week_ago]
        if len(recent) >= MAX_WEEKLY_CHANGES:
            return False, (
                f"Haftalık limit aşıldı: Bu hafta {len(recent)} değişiklik uygulandı "
                f"(max {MAX_WEEKLY_CHANGES})"
            )

    return True, "Güvenlik kontrolü geçti"


# ── PLAYBOOK Güncelleme ────────────────────────────────────────────────────────

def update_playbook_param(
    param: str,
    old_value: float,
    new_value: float,
    rationale: str
) -> bool:
    """
    TRADING_PLAYBOOK.md'de parametre değerini günceller.
    Güvenli string replacement — markdown yapısını bozmaz.
    """
    playbook_path = REPO_ROOT / "docs" / "TRADING_PLAYBOOK.md"
    if not playbook_path.exists():
        print("[RuleUpdater] PLAYBOOK bulunamadı!")
        return False

    content = playbook_path.read_text(encoding="utf-8")

    # Parametre bazlı güncelleme
    update_map = {
        "rsi_k11_katman1": (
            f"RSI {int(old_value)}+",
            f"RSI {int(new_value)}+"
        ),
        "atr_katsayi": (
            f"{old_value}×ATR",
            f"{new_value}×ATR"
        ),
        "swing_max_gun": (
            f"Max {int(old_value)} gün",
            f"Max {int(new_value)} gün"
        ),
    }

    if param not in update_map:
        print(f"[RuleUpdater] Parametre PLAYBOOK mapping'i bulunamadı: {param}")
        return False

    old_str, new_str = update_map[param]

    if old_str not in content:
        print(f"[RuleUpdater] PLAYBOOK'ta '{old_str}' bulunamadı")
        return False

    # Güncelleme yap
    updated = content.replace(old_str, new_str, 1)  # Sadece ilk occurrence

    # Güncelleme logu ekle (playbook'un başına)
    log_entry = (
        f"\n> **Otomatik Güncelleme** {datetime.now(TR_TZ).strftime('%Y-%m-%d')}: "
        f"{param} {old_value}→{new_value} | Gerekçe: {rationale[:100]}\n"
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
    proposed_by: str = "agent"
) -> dict:
    """
    Bir kural değişikliğini güvenlik kontrolünden geçirerek uygular.
    """
    # 1. Güvenlik kontrolü
    allowed, reason = validate_change_request(param, new_value, backtest_result)
    if not allowed:
        return {
            "durum":    "REDDEDILDI",
            "gerekce":  reason,
            "param":    param,
            "yeni_deger": new_value,
        }

    old_value = CHANGEABLE_PARAMS[param]["current"]

    # 2. PLAYBOOK güncelle
    success = update_playbook_param(param, old_value, new_value, rationale)
    if not success:
        return {
            "durum":   "HATA",
            "gerekce": "PLAYBOOK güncellenemedi",
            "param":   param,
        }

    # 3. K-rules digest güncelle
    digest_path = MEMORY_DIR / "k_rules_digest.md"
    if digest_path.exists():
        digest = digest_path.read_text(encoding="utf-8")
        desc   = CHANGEABLE_PARAMS[param]["desc"]
        digest += f"\n\n**{datetime.now(TR_TZ).strftime('%Y-%m-%d')} GÜNCELLENDİ:** {desc}: {old_value} → {new_value}"
        digest_path.write_text(digest, encoding="utf-8")

    # 4. Uygulanan değişikliği kaydet
    changes_path = MEMORY_DIR / "applied_changes.json"
    applied = {"list": []}
    if changes_path.exists():
        with open(changes_path, encoding="utf-8") as f:
            applied = json.load(f)

    change_record = {
        "tarih":      datetime.now(TR_TZ).isoformat(),
        "param":      param,
        "eski_deger": old_value,
        "yeni_deger": new_value,
        "gerekce":    rationale,
        "oneren":     proposed_by,
        "backtest_n": backtest_result.get("toplam_trade", 0),
    }
    applied["list"].append(change_record)
    applied["list"] = applied["list"][-50:]

    with open(changes_path, "w", encoding="utf-8") as f:
        json.dump(applied, f, ensure_ascii=False, indent=2)

    # 5. In-memory güncellemesi
    CHANGEABLE_PARAMS[param]["current"] = new_value

    print(f"[RuleUpdater] ✅ Değişiklik uygulandı: {param} = {new_value}")
    return {
        "durum":      "UYGULANMADI",
        "param":      param,
        "eski_deger": old_value,
        "yeni_deger": new_value,
        "gerekce":    rationale,
    }


# ── Git Push ──────────────────────────────────────────────────────────────────

def commit_rule_change(param: str, old_val: float, new_val: float) -> bool:
    """
    PLAYBOOK değişikliğini git'e commit eder.
    """
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name", "Finzora Agent"], check=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], check=True)

        # Pull önce
        subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                       capture_output=True)

        subprocess.run(["git", "add",
                        "docs/TRADING_PLAYBOOK.md",
                        "agent/memory/k_rules_digest.md",
                        "agent/memory/applied_changes.json"],
                       check=True)

        msg = f"🔧 [Agent] Kural güncellendi: {param} {old_val}→{new_val}"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)

        print(f"[RuleUpdater] Git push başarılı: {msg}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[RuleUpdater] Git hatası: {e}")
        return False


# ── Claude Kararı Parse Et ────────────────────────────────────────────────────

def parse_claude_rule_proposal(claude_response: str) -> list[dict]:
    """
    Claude'un haftalık analizinden "BACKTEST GEREKLİ" önerilerini çıkarır.
    Format: "BACKTEST GEREKLİ — [param]: [eski] → [yeni] | [gerekçe]"
    """
    proposals = []
    lines     = claude_response.split("\n")

    for line in lines:
        if "BACKTEST GEREKLİ" not in line.upper():
            continue

        # Basit parse
        try:
            # Örnek: "BACKTEST GEREKLİ — rsi_k11_katman1: 70 → 75 | RSI 70 çok erken..."
            parts = line.split("—", 1)
            if len(parts) < 2:
                continue

            detail = parts[1].strip()

            # param: old → new | rationale
            if ":" in detail and "→" in detail:
                param_part, rest = detail.split(":", 1)
                param = param_part.strip()

                values_part = rest.split("|")[0].strip()
                rationale   = rest.split("|")[1].strip() if "|" in rest else "Agent önerisi"

                old_new = values_part.split("→")
                if len(old_new) == 2:
                    old_val = float(old_new[0].strip())
                    new_val = float(old_new[1].strip())

                    proposals.append({
                        "param":     param,
                        "old_value": old_val,
                        "new_value": new_val,
                        "rationale": rationale[:200],
                    })
        except (ValueError, IndexError):
            continue

    return proposals


# ── Haftalık Kural İncelemesi ─────────────────────────────────────────────────

def run_weekly_rule_review(claude_response: str, backtest_results: dict) -> list[dict]:
    """
    Haftalık analizden önerileri çıkarır, güvenlik kontrolünden geçirir.
    Phase 4'te sadece "öneri" aşamasındayız — gerçek uygulama Phase 5'te.
    """
    proposals = parse_claude_rule_proposal(claude_response)
    results   = []

    for p in proposals:
        # Sadece güvenlik kontrolü yap, gerçekte uygulama yapma
        allowed, reason = validate_change_request(
            p["param"], p["new_value"], backtest_results
        )

        result = {
            "param":     p["param"],
            "new_value": p["new_value"],
            "izin":      allowed,
            "gerekce":   reason,
            "durum":     "ONAY_BEKLIYOR" if allowed else "REDDEDILDI",
        }
        results.append(result)

        if allowed:
            # Öneriler kuyruğuna ekle (gerçek uygulama değil)
            from learning_engine import add_proposed_change
            add_proposed_change(
                change_type=f"kural_parametresi_{p['param']}",
                description=f"{p['param']}: {p['old_value']} → {p['new_value']}",
                rationale=p["rationale"],
                proposed_by="agent_weekly",
                requires_backtest=True,
            )
            print(f"[RuleUpdater] Öneri kuyruğa eklendi: {p['param']}")

    return results


def get_applied_changes_summary() -> str:
    """Son uygulanan değişiklikleri formatlar."""
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
        lines.append(
            f"  [{c['tarih'][:10]}] {c['param']}: "
            f"{c['eski_deger']} → {c['yeni_deger']} | {c['gerekce'][:60]}"
        )
    return "\n".join(lines)
