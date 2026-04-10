#!/usr/bin/env python3
"""
Finzora AI — K-Kural Tutarsızlık Tarayıcısı
=============================================
TRADING_PLAYBOOK.md ile bağımlı dosyalar arasındaki uçurumları tespit eder.

Kontrol edilen çelişkiler:
  1. K-13 v4.1: Eski statik VIX>=25 eşiği scriptlerde/promptlarda var mı?
  2. K-11 v3:   Eski "kalanı sür" (Katman3) ifadesi kalmış mı?
  3. K-14 v2.2: Eski "yarım pozisyon sayacı / 2-3 kazanırsa" ifadesi var mı?
  4. K-Kaldırıldı: K-01/K-03/K-08 aktif kural gibi kullanılıyor mu?
  5. VIX kaynak: VIXY fiyatı VIX seviyesi olarak mı kullanılıyor?
  6. status.json: vix_level alanı eksik mi?

Kullanım:
  python scripts/consistency_check.py           # stdout rapor
  python scripts/consistency_check.py --notify  # sorun varsa Telegram
  python scripts/consistency_check.py --strict  # sorun varsa exit(1)
"""

import os, re, sys, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_PATHS = {'.git', '__pycache__', 'archive', 'node_modules'}
# Yoksayılacak dosyalar (backup, scriptin kendisi, vb.)
SKIP_FILES = {
    'scripts/consistency_check.py',        # scriptin kendisi — string literaller tetikler
    'docs/TRADING_PLAYBOOK_backup_20260401.md',  # eski backup
}
# Geçmiş raporları atla — o tarihe ait, doğru kayıt
SKIP_REPORTS_BEFORE = "2026-04-10"

# ── Dosya yükleyici ──────────────────────────────────────────────────────────
def load_files(extensions=('.md', '.py', '.json'), skip_old_reports=True):
    files = {}
    for root, dirs, fnames in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_PATHS]
        for fname in fnames:
            if not any(fname.endswith(e) for e in extensions):
                continue
            path = Path(root) / fname
            rel = str(path.relative_to(ROOT))

            # Eski rapor filtresi
            if skip_old_reports and 'reports/' in rel:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
                if date_match and date_match.group(1) < SKIP_REPORTS_BEFORE:
                    continue

            if rel in SKIP_FILES:
                continue
            try:
                files[rel] = path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                pass
    return files


# ── Kontrol fonksiyonları ────────────────────────────────────────────────────
def check_k13_static_vix(files):
    """K-13 v4.1: Eski statik VIX>=25 / VIX>25 eşiği."""
    issues = []
    skip = {'docs/TRADING_PLAYBOOK.md', 'docs/K_RULES_QUICK_REF.md',
            'scripts/consistency_check.py'}
    patterns = [
        r'vix\s*[>]=\s*25\b',               # Python: vix >= 25
        r'VIX\s*[>]\s*25\s*[→=→]',          # Metin: VIX > 25 →
        r'VIX\s*>\s*25\s*(=|→|giriş)',       # Metin: VIX>25=yarım
    ]
    for rel, content in files.items():
        if rel in skip:
            continue
        for pat in patterns:
            for m in re.finditer(pat, content, re.IGNORECASE):
                ctx = content[max(0, m.start()-40):m.end()+60].replace('\n', ' ').strip()
                issues.append(('K-13', 'HATA', rel,
                    f'Eski statik VIX=25 eşiği: "...{ctx}..."'))
    return issues


def check_k11_kalan_sur(files):
    """K-11 v3: Eski Katman3 'kalanı sür' ifadesi."""
    issues = []
    skip = {'docs/TRADING_PLAYBOOK.md'}
    for rel, content in files.items():
        if rel in skip:
            continue
        if 'kalanı sür' in content:
            for line in content.split('\n'):
                if 'kalanı sür' in line:
                    issues.append(('K-11', 'HATA', rel,
                        f'Eski Katman3 "kalanı sür": "{line.strip()}"'))
    return issues


def check_k14_old_counter(files):
    """K-14 v2.2: Eski yarım pozisyon sayacı."""
    issues = []
    skip = {'docs/TRADING_PLAYBOOK.md', 'data/swing/status.json',
            'scripts/consistency_check.py'}
    phrases = [
        '2/3 kazanırsa', '2/3 kazanirsa',
        'ilk 3 trade yarım', 'ilk 3 trade yarim',
        'trade sayacı: 0/3', 'yarım_pozisyon_protokolu',
    ]
    for rel, content in files.items():
        if rel in skip:
            continue
        for phrase in phrases:
            if phrase in content:
                idx = content.find(phrase)
                ctx = content[max(0,idx-30):idx+80].replace('\n',' ').strip()
                issues.append(('K-14', 'HATA', rel,
                    f'Eski v2.1 protokol: "...{ctx}..."'))
    return issues


def check_removed_rules(files):
    """K-01/K-03/K-08 KALDIRILDI — aktif kullanım var mı?"""
    issues = []
    skip = {'docs/TRADING_PLAYBOOK.md', 'docs/K_RULES_QUICK_REF.md',
            'scripts/consistency_check.py'}
    removed = ['K-01', 'K-03', 'K-08']
    # Kaldırıldı bağlamı var mı kontrol et
    for rel, content in files.items():
        if rel in skip:
            continue
        for rule in removed:
            for m in re.finditer(re.escape(rule), content):
                ctx = content[max(0,m.start()-60):m.end()+80]
                if 'kaldırıldı' not in ctx.lower() and 'kaldirildi' not in ctx.lower():
                    snippet = ctx.replace('\n',' ').strip()
                    issues.append((rule, 'UYARI', rel,
                        f'Kaldırılmış kural aktif gibi: "...{snippet[:100]}..."'))
    return issues


def check_vixy_as_vix_level(files):
    """VIXY fiyatı VIX seviyesi gibi kullanılıyor mu?"""
    issues = []
    skip = {'docs/TRADING_PLAYBOOK.md', 'scripts/k_rules_common.py',
            'scripts/consistency_check.py', 'docs/K_RULES_QUICK_REF.md'}
    # "VIXY = VIX proxy" ifadesi var mı? (güncel: sadece yön için izinli)
    phrases = ['VIXY = VIX proxy', 'VIXY proxy (doğrudan ^VIX güvenilmez)',
               'VIXY (VIX proxy)']
    for rel, content in files.items():
        if rel in skip:
            continue
        for phrase in phrases:
            if phrase in content:
                idx = content.find(phrase)
                ctx = content[max(0,idx-20):idx+len(phrase)+40].replace('\n',' ')
                issues.append(('VIX', 'HATA', rel,
                    f'VIXY fiyatı VIX seviyesi gibi sunuluyor: "{ctx.strip()}"'))
    return issues


def check_vix_level_in_state(files):
    """session_state.json ve summary.json'da vix_level alanı var mı?"""
    issues = []
    for rel in ['data/session_state.json', 'data/summary.json']:
        if rel not in files:
            continue
        try:
            d = json.loads(files[rel])
            content_str = json.dumps(d)
            if 'vixy' in content_str and 'vix_level' not in content_str and 'vix' not in content_str:
                issues.append(('VIX', 'UYARI', rel,
                    'vixy alanı var ama vix/vix_level alanı eksik'))
        except Exception:
            pass
    return issues


# ── Ana fonksiyon ────────────────────────────────────────────────────────────
def run_checks(notify=False, strict=False):
    files = load_files()

    all_issues = []
    all_issues += check_k13_static_vix(files)
    all_issues += check_k11_kalan_sur(files)
    all_issues += check_k14_old_counter(files)
    all_issues += check_vixy_as_vix_level(files)
    all_issues += check_vix_level_in_state(files)
    # K-01/03/08 kaldırıldı kontrolü çok gürültülü (geçmiş raporlar) → yalnızca scriptler
    script_files = {k: v for k, v in files.items() if k.startswith('scripts/')}
    all_issues += check_removed_rules(script_files)

    hatalar   = [i for i in all_issues if i[1] == 'HATA']
    uyarilar  = [i for i in all_issues if i[1] == 'UYARI']

    # ── Rapor ──
    if not all_issues:
        print("✅ Tutarsızlık bulunamadı — tüm K-kuralları senkron.")
        return 0

    print(f"\n{'='*60}")
    print(f"K-KURAL TUTARSIZLIK RAPORU — {len(hatalar)} HATA / {len(uyarilar)} UYARI")
    print(f"{'='*60}")

    by_rule = {}
    for rule, sev, path, msg in all_issues:
        by_rule.setdefault(rule, []).append((sev, path, msg))

    report_lines = []
    for rule in sorted(by_rule):
        items = by_rule[rule]
        print(f"\n[{rule}]")
        for sev, path, msg in items:
            icon = '🔴' if sev == 'HATA' else '🟡'
            line = f"  {icon} {path}\n     {msg[:120]}"
            print(line)
            report_lines.append(f"{icon} [{rule}] {path}: {msg[:80]}")

    # ── Telegram ──
    if notify and (hatalar or uyarilar):
        try:
            import subprocess
            summary = f"{len(hatalar)} hata, {len(uyarilar)} uyarı\n" + "\n".join(report_lines[:8])
            subprocess.run([
                'python', str(ROOT / 'scripts/telegram_notify.py'),
                '--type', 'alert',
                '--title', 'K-Kural Tutarsızlık Taraması',
                '--details', summary[:800],
                '--private',  # sistem uyarısı — gruba değil, sadece Zeynel'e
            ], check=False)
            print("\n📨 Telegram bildirimi gönderildi.")
        except Exception as e:
            print(f"\n⚠️  Telegram gönderilemedi: {e}")

    return len(hatalar)  # strict modda exit kodu


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='K-Kural tutarsızlık tarayıcısı')
    parser.add_argument('--notify', action='store_true', help='Sorun varsa Telegram gönder')
    parser.add_argument('--strict', action='store_true', help='Hata varsa exit(1)')
    args = parser.parse_args()

    hata_sayisi = run_checks(notify=args.notify, strict=args.strict)

    if args.strict and hata_sayisi > 0:
        sys.exit(1)
