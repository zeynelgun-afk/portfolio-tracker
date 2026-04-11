#!/usr/bin/env python3
# DEVRE DIŞI — 12 Nisan 2026
raise SystemExit("consolidate_portfolios.py ghost portfoy olusturur, kullanilamaz")
"""
Finzora — Portföy Konsolidasyonu
==================================
3 portföy → 2 portföy

MEVCUT:
  Aggressive  → AI supply chain, -9.5%
  Balanced    → Karışık, +12.3%  ← KAPATILACAK
  Dividend    → Temettü odaklı, +42.9%

HEDEF:
  Growth (Büyüme) ← Aggressive + CI (Balanced'dan)
  Income (Gelir)  ← Dividend + MO/DUK/NEE (Balanced'dan)

TAŞIMA KURALLARI:
  CI  → Growth (momentum/sağlık, temettü yok)
  MO  → Income (zaten Dividend'de var → hisseleri birleştir)
  DUK → Income (utility, temettü %3.8)
  NEE → Income (utility, temettü %2.7)
  Balanced nakit → Growth'a

DRY-RUN: --dry-run flag ile gerçek değişiklik yapmadan kontrol et
UYGULA:  --apply flag ile kalıcı yap
"""

import json
import shutil
import argparse
import subprocess
import os
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

def load_pf(name):
    path = REPO_ROOT / "data" / "portfolios" / f"{name}.json"
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def save_pf(name, data):
    path = REPO_ROOT / "data" / "portfolios" / f"{name}.json"
    # Yedek al (sadece dosya varsa)
    if path.exists():
        backup = REPO_ROOT / "data" / "portfolios" / f"{name}_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        shutil.copy(path, backup)
        print(f"  ✅ {name}.json güncellendi (yedek: {backup.name})")
    else:
        print(f"  ✅ {name}.json oluşturuldu (yeni)")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run_consolidation(dry_run=True):
    print(f"\n{'='*60}")
    print(f"PORTFÖY KONSOLİDASYONU {'(DRY-RUN)' if dry_run else '(GERÇEK)'}")
    print(f"{'='*60}\n")

    # Mevcut portföyleri yükle
    aggressive = load_pf('aggressive')
    balanced   = load_pf('balanced')
    dividend   = load_pf('dividend')

    # ── GROWTH (Büyüme) = eski Aggressive ────────────────────────────
    print("📊 GROWTH PORTFÖYÜ OLUŞTURULUYOR...")
    growth = {
        "portfoy_adi":          "Büyüme Portföyü",
        "strateji":             aggressive.get('strateji', {}),
        "baslangic_sermaye":    aggressive.get('baslangic_sermaye', 400000),
        "nakit":                aggressive.get('nakit', {}),
        "pozisyonlar":          list(aggressive.get('pozisyonlar', [])),
        "son_guncelleme":       datetime.now().isoformat(),
        "toplam_deger":         aggressive.get('toplam_deger', 0),
        "toplam_getiri_yuzde":  aggressive.get('toplam_getiri_yuzde', 0),
        "notes":                aggressive.get('notes', []),
        "transactions":         aggressive.get('transactions', []),
    }

    # Balanced'dan CI → Growth
    bal_pozlar = balanced.get('pozisyonlar', [])
    ci_pos = next((p for p in bal_pozlar if p.get('sembol') == 'CI'), None)
    if ci_pos:
        ci_pos['portfoy'] = 'growth'
        growth['pozisyonlar'].append(ci_pos)
        growth['toplam_deger'] = (growth.get('toplam_deger', 0) or 0) + (
            (ci_pos.get('adet', 0) or 0) * (ci_pos.get('guncel_fiyat') or ci_pos.get('maliyet_bazis') or 271)
        )
        print(f"  CI ({ci_pos.get('adet')} adet) Balanced → Growth eklendi")
    else:
        print("  CI: Balanced'da bulunamadı")

    # Balanced nakitini Growth'a ekle
    bal_nakit = balanced.get('nakit', {}).get('tutar', 0) or 0
    mevcut_nakit = growth.get('nakit', {}).get('tutar', 0) or 0
    growth['nakit']['tutar'] = round(float(mevcut_nakit) + float(bal_nakit), 2)
    print(f"  Balanced nakit ${bal_nakit:,.0f} → Growth nakite eklendi")

    growth_pozlar = [p.get('sembol') for p in growth['pozisyonlar']]
    print(f"\n  Growth pozisyonlar ({len(growth['pozisyonlar'])}): {growth_pozlar}")

    # ── INCOME (Gelir) = eski Dividend + Balanced defensive ──────────
    print("\n📊 INCOME PORTFÖYÜ OLUŞTURULUYOR...")
    income = {
        "portfoy_adi":          "Gelir Portföyü",
        "baslangic_sermaye":    dividend.get('baslangic_sermaye', 100000),
        "nakit":                dividend.get('nakit', {}),
        "pozisyonlar":          list(dividend.get('pozisyonlar', [])),
        "son_guncelleme":       datetime.now().isoformat(),
        "toplam_deger":         dividend.get('toplam_deger', 0),
        "toplam_getiri_yuzde":  dividend.get('toplam_getiri_yuzde', 0),
        "notes":                dividend.get('notes', []),
        "transactions":         dividend.get('transactions', []),
    }

    # MO zaten Dividend'de var — Balanced MO'sunu hisse adedi olarak birleştir
    mo_income = next((p for p in income['pozisyonlar'] if p.get('sembol') == 'MO'), None)
    mo_balanced = next((p for p in bal_pozlar if p.get('sembol') == 'MO'), None)

    if mo_income and mo_balanced:
        bal_mo_adet = mo_balanced.get('adet', 0) or 0
        bal_mo_maliyet = mo_balanced.get('maliyet_bazis', 0) or 0
        inc_mo_adet = mo_income.get('adet', 0) or 0
        inc_mo_maliyet = mo_income.get('maliyet_bazis', 0) or 0

        # Ağırlıklı ortalama maliyet
        toplam_adet = bal_mo_adet + inc_mo_adet
        if toplam_adet > 0 and bal_mo_maliyet and inc_mo_maliyet:
            yeni_maliyet = (bal_mo_adet * bal_mo_maliyet + inc_mo_adet * inc_mo_maliyet) / toplam_adet
            mo_income['maliyet_bazis'] = round(yeni_maliyet, 4)

        mo_income['adet'] = toplam_adet
        print(f"  MO: Balanced {bal_mo_adet} + Income {inc_mo_adet} = {toplam_adet} adet (birleştirildi)")

    # Balanced'dan DUK ve NEE → Income
    for sym in ['DUK', 'NEE']:
        pos = next((p for p in bal_pozlar if p.get('sembol') == sym), None)
        if pos:
            pos['portfoy'] = 'income'
            income['pozisyonlar'].append(pos)
            pos_deger = (pos.get('adet', 0) or 0) * (
                pos.get('guncel_fiyat') or pos.get('maliyet_bazis') or 100
            )
            income['toplam_deger'] = (income.get('toplam_deger', 0) or 0) + pos_deger
            print(f"  {sym} ({pos.get('adet')} adet) Balanced → Income eklendi")
        else:
            print(f"  {sym}: Balanced'da bulunamadı")

    income_pozlar = [p.get('sembol') for p in income['pozisyonlar']]
    print(f"\n  Income pozisyonlar ({len(income['pozisyonlar'])}): {income_pozlar}")

    # ── ÖZET ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("ÖZET:")
    print(f"  Growth: {len(growth['pozisyonlar'])} pozisyon | ~${growth.get('toplam_deger',0):,.0f}")
    print(f"  Income: {len(income['pozisyonlar'])} pozisyon | ~${income.get('toplam_deger',0):,.0f}")
    print(f"  Balanced: KAPATILACAK (tüm pozisyonlar dağıtıldı)")

    # Transaction log
    transfer_log = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "type": "PORTFOLIO_CONSOLIDATION",
        "description": "3 portföy → 2 portföy (Balanced kapatıldı)",
        "transfers": [
            {"from": "balanced", "to": "growth", "symbol": "CI", "reason": "Momentum/sağlık, büyüme portföyüne uygun"},
            {"from": "balanced", "to": "income", "symbol": "MO", "reason": "Temettü, gelir portföyüne eklendi (birleştirildi)"},
            {"from": "balanced", "to": "income", "symbol": "DUK", "reason": "Utility temettü, gelir portföyüne uygun"},
            {"from": "balanced", "to": "income", "symbol": "NEE", "reason": "Utility temettü, gelir portföyüne uygun"},
        ]
    }

    if dry_run:
        print(f"\n⚠️  DRY-RUN: Değişiklik yapılmadı.")
        print("   Onaylamak için: python scripts/consolidate_portfolios.py --apply")
        return

    # ── GERÇEK UYGULAMA ───────────────────────────────────────────────
    print("\n📝 UYGULANIYIOR...")

    # Yeni JSON dosyaları oluştur (growth.json, income.json)
    save_pf('growth', growth)
    save_pf('income', income)

    # Balanced'ı arşivle (silme)
    bal_archive = REPO_ROOT / "data" / "portfolios" / f"balanced_archived_{datetime.now().strftime('%Y%m%d')}.json"
    shutil.copy(REPO_ROOT / "data" / "portfolios" / "balanced.json", bal_archive)
    print(f"  Balanced arşivlendi: {bal_archive.name}")

    # Transfer log kaydet
    log_path = REPO_ROOT / "data" / "portfolios" / "consolidation_log.json"
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(transfer_log, f, ensure_ascii=False, indent=2)

    # Git commit
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name", "Finzora AI"], capture_output=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add", "data/portfolios/", "docs/TRADING_PLAYBOOK.md"], capture_output=True)
        subprocess.run(["git", "commit", "-m",
            "♻️ Portföy konsolidasyonu: 3→2 (Balanced kapatıldı, Growth+Income)"], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print("  ✅ Git push başarılı")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ Git hatası: {e}")

    print("\n✅ KONSOLİDASYON TAMAMLANDI")
    print(f"   Growth: {[p.get('sembol') for p in growth['pozisyonlar']]}")
    print(f"   Income: {[p.get('sembol') for p in income['pozisyonlar']]}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Portföy konsolidasyonu')
    parser.add_argument('--apply', action='store_true', help='Gerçekten uygula (dry-run değil)')
    args = parser.parse_args()
    run_consolidation(dry_run=not args.apply)
