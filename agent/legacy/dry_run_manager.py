#!/usr/bin/env python3
"""
Finzora Agent — Dry-Run Yöneticisi
=====================================
Öneri kuyruğundaki değişiklikleri izler.
14 gün dry-run sonunda kanıtlanmışsa PLAYBOOK'a uygular.

Akış:
  1. Her Pazar: proposed_changes.json kontrol et
  2. dry_run_bitis geçmiş öneriler → değerlendir
  3. Yeterli backtest verisi + pozitif sonuç → PLAYBOOK güncelle + git push
  4. Yetersiz kanıt → öneriye "REDDEDILDI" yaz, neden açıkla
  5. Telegram'a özet gönder
"""

import json
import subprocess
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")

MIN_TRADES_FOR_APPLY = 10   # Uygulamak için minimum trade sayısı
MIN_WIN_RATE         = 52.0  # Uygulamak için minimum win rate (mevcut + yeni)


# ── Dry-Run Değerlendirme ─────────────────────────────────────────────────────

def evaluate_pending_proposals(backtest_results: dict) -> list[dict]:
    """
    Süresi dolmuş önerileri değerlendirir.
    Kanıtlanmışsa APPLY, değilse REJECT.
    """
    path = MEMORY_DIR / "proposed_changes.json"
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    proposals  = data.get("kuyruk", [])
    today      = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    evaluated  = []

    for p in proposals:
        if p.get("durum") != "BEKLIYOR":
            continue

        dry_run_bitis = p.get("dry_run_bitis", "")
        if dry_run_bitis > today:
            # Henüz bitmemiş
            days_left = (datetime.strptime(dry_run_bitis, "%Y-%m-%d")
                        - datetime.now(TR_TZ).replace(tzinfo=None)).days
            p["kalan_gun"] = days_left
            evaluated.append({"oneri": p, "karar": "BEKLIYOR", "kalan_gun": days_left})
            continue

        # Süre doldu — değerlendir
        total_trades  = backtest_results.get("toplam_trade", 0)
        kural_perf    = backtest_results.get("kural_performansi", {})
        win_rate_data = kural_perf.get("kural_performansi", {})

        # Yeterli veri var mı?
        if total_trades < MIN_TRADES_FOR_APPLY:
            p["durum"]       = "REDDEDILDI"
            p["ret_gerekce"] = f"Yetersiz trade verisi: {total_trades} < {MIN_TRADES_FOR_APPLY}"
            evaluated.append({"oneri": p, "karar": "REDDEDILDI", "gerekce": p["ret_gerekce"]})
            continue

        # Pozitif etki gösteriyor mu?
        # Basit heuristik: stop_loss win rate'i kontrol et
        stop_wr = win_rate_data.get("stop_loss", {}).get("win_rate", 0)
        overall_wr = sum(
            v.get("win_rate", 0) for v in win_rate_data.values()
        ) / max(len(win_rate_data), 1)

        if overall_wr >= MIN_WIN_RATE:
            p["durum"]        = "ONAYLANDI"
            p["onay_gerekce"] = f"Win rate %{overall_wr:.1f} ≥ min %{MIN_WIN_RATE}"
            evaluated.append({"oneri": p, "karar": "ONAYLANDI"})
        else:
            p["durum"]       = "REDDEDILDI"
            p["ret_gerekce"] = f"Win rate %{overall_wr:.1f} < min %{MIN_WIN_RATE} — kanıt yetersiz"
            evaluated.append({"oneri": p, "karar": "REDDEDILDI", "gerekce": p["ret_gerekce"]})

    # Güncellenmiş listeyi kaydet
    data["kuyruk"]       = proposals
    data["son_degerlendirme"] = today
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return evaluated


# ── Onaylananları Uygula ──────────────────────────────────────────────────────

def apply_approved_proposals(evaluated: list[dict]) -> list[dict]:
    """
    ONAYLANDI durumundaki önerileri PLAYBOOK'a uygular.
    """
    from rule_updater import apply_rule_change, commit_rule_change, CHANGEABLE_PARAMS
    from backtester import run_full_backtest

    applied = []
    backtest = run_full_backtest()

    for item in evaluated:
        if item["karar"] != "ONAYLANDI":
            continue

        oneri = item["oneri"]
        param = oneri.get("aciklama", "").split(":")[0].strip()

        # Parametre adını çıkar
        for key in CHANGEABLE_PARAMS:
            if key in oneri.get("aciklama", ""):
                param = key
                break

        if not param or param not in CHANGEABLE_PARAMS:
            print(f"[DryRun] Parametre bulunamadı: {oneri.get('aciklama')}")
            continue

        # Yeni değeri çıkar
        try:
            desc   = oneri.get("aciklama", "")
            values = desc.split("→")
            if len(values) < 2:
                continue
            new_val = float(values[1].strip().split()[0])
        except (ValueError, IndexError):
            continue

        result = apply_rule_change(
            param        = param,
            new_value    = new_val,
            rationale    = oneri.get("gerekce", "Dry-run onayı"),
            backtest_result = backtest,
            proposed_by  = "dry_run_manager",
        )

        if result["durum"] != "REDDEDILDI":
            # Git push
            old_val = CHANGEABLE_PARAMS[param].get("current", 0)
            commit_rule_change(param, old_val, new_val)

        applied.append(result)

    return applied


# ── Haftalık Dry-Run Raporu ───────────────────────────────────────────────────

def run_dry_run_check(backtest_results: dict) -> str:
    """
    Haftalık dry-run kontrolünü çalıştırır.
    Özet raporu döner (Telegram'a gider).
    """
    print("[DryRun] Öneri kuyruğu kontrol ediliyor...")

    evaluated = evaluate_pending_proposals(backtest_results)

    if not evaluated:
        return "Öneri kuyruğu boş — bu hafta değerlendirilecek öneri yok."

    # Onaylananları uygula
    approved = [e for e in evaluated if e["karar"] == "ONAYLANDI"]
    rejected = [e for e in evaluated if e["karar"] == "REDDEDILDI"]
    waiting  = [e for e in evaluated if e["karar"] == "BEKLIYOR"]

    applied_results = apply_approved_proposals(evaluated)

    # Özet metin
    lines = ["--- DRY-RUN DEĞERLENDIRME ---"]

    if approved:
        lines.append(f"\nONAYLANDI ({len(approved)} öneri PLAYBOOK'a uygulandı):")
        for a in approved:
            lines.append(f"  ✅ {a['oneri']['aciklama'][:80]}")

    if rejected:
        lines.append(f"\nREDDEDILDI ({len(rejected)} öneri):")
        for r in rejected:
            lines.append(f"  ❌ {r['oneri']['aciklama'][:60]} | {r.get('gerekce','')[:60]}")

    if waiting:
        lines.append(f"\nBEKLIYOR ({len(waiting)} öneri):")
        for w in waiting:
            lines.append(f"  ⏳ {w['oneri']['aciklama'][:60]} | {w.get('kalan_gun','?')} gün kaldı")

    return "\n".join(lines)
