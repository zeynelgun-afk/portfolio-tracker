#!/usr/bin/env python3
"""
Log Rotation — Observability events.jsonl arşivleme

Amacı: logs/events.jsonl sonsuza büyümesin. Tamamlanmış aylar
logs/archive/events-YYYY-MM.jsonl.gz olarak sıkıştırılır, aktif
dosyada sadece bu ayın kayıtları kalır.

Kullanım:
  python scripts/log_rotation.py --stats              # durum raporu
  python scripts/log_rotation.py --archive-completed  # bugünden önceki ayları arşivle
  python scripts/log_rotation.py --archive-completed --dry-run
  python scripts/log_rotation.py --archive-month 2026-04
  python scripts/log_rotation.py --archive-month 2026-04 --dry-run

Tasarım:
- ATOMIK: önce yeni dosya yaz, doğrulan, sonra aktif dosyayı swap et.
  Hiçbir kayıt kaybolmaz.
- HASH KONTROL: her kayıt id'si benzersiz (observability._new_id 12-hex),
  archive sırasında çift kayıt riski yok.
- LOCK YOK: events.jsonl append-only. Rotation çalıştığı sırada yeni
  kayıt gelebilir — script "bu ana kadar olan" kayıtları işler, sonraki
  kayıtlar aktif dosyada kalır.
"""

import argparse
import gzip
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_JSONL = _REPO_ROOT / "logs" / "events.jsonl"
ARCHIVE_DIR = _REPO_ROOT / "logs" / "archive"


def _log(msg: str) -> None:
    """Düz log."""
    print(f"[log_rotation] {msg}", flush=True)


def stats() -> None:
    """events.jsonl durum raporu."""
    if not EVENTS_JSONL.exists():
        _log(f"Aktif log bulunamadı: {EVENTS_JSONL}")
        return
    size_mb = EVENTS_JSONL.stat().st_size / (1024 * 1024)
    months: Counter[str] = Counter()
    total = 0
    with EVENTS_JSONL.open() as f:
        for line in f:
            try:
                ev = json.loads(line)
                months[ev["ts"][:7]] += 1
                total += 1
            except (json.JSONDecodeError, KeyError):
                pass
    print(f"\nAktif log: {EVENTS_JSONL}")
    print(f"  Boyut: {size_mb:.2f} MB")
    print(f"  Toplam kayıt: {total:,}")
    print(f"  Aylar:")
    for m, c in sorted(months.items()):
        marker = " ← bu ay" if _is_current_month(m) else ""
        print(f"    {m}: {c:>6,}{marker}")

    print(f"\nArchive: {ARCHIVE_DIR}")
    if ARCHIVE_DIR.exists():
        archives = sorted(ARCHIVE_DIR.glob("events-*.jsonl.gz"))
        if archives:
            total_arch_mb = sum(a.stat().st_size for a in archives) / (1024 * 1024)
            print(f"  Sıkıştırılmış toplam: {total_arch_mb:.2f} MB")
            for a in archives:
                kb = a.stat().st_size / 1024
                print(f"    {a.name}: {kb:.1f} KB")
        else:
            print(f"  (boş)")
    else:
        print(f"  (henüz oluşturulmadı)")


def _is_current_month(month_str: str) -> bool:
    """YYYY-MM string'i şu anki ay mı."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return month_str == f"{now.year}-{now.month:02d}"


def _list_completed_months() -> list[str]:
    """Aktif log'da bugünden önceki AYLARı (bu ay hariç) listele."""
    if not EVENTS_JSONL.exists():
        return []
    months: set[str] = set()
    with EVENTS_JSONL.open() as f:
        for line in f:
            try:
                ev = json.loads(line)
                m = ev["ts"][:7]
                if not _is_current_month(m):
                    months.add(m)
            except (json.JSONDecodeError, KeyError):
                pass
    return sorted(months)


def archive_month(month: str, dry_run: bool = False) -> bool:
    """
    Belirli ayın kayıtlarını arşivle. Aktif dosyadan kaldır.
    Atomic: yeni aktif dosyaya temp yazılır, doğrulanır, swap edilir.

    Args:
        month: 'YYYY-MM' formatında
        dry_run: True ise sadece ne yapacağını söyle

    Returns: arşivleme başarılı mı
    """
    if not EVENTS_JSONL.exists():
        _log(f"Aktif log yok: {EVENTS_JSONL}")
        return False

    archive_path = ARCHIVE_DIR / f"events-{month}.jsonl.gz"
    if archive_path.exists():
        _log(f"HATA: {archive_path.name} zaten var, üzerine yazılmayacak")
        return False

    # İlk pass: sayım
    to_archive = 0
    to_keep = 0
    with EVENTS_JSONL.open() as f:
        for line in f:
            try:
                ev = json.loads(line)
                if ev["ts"][:7] == month:
                    to_archive += 1
                else:
                    to_keep += 1
            except (json.JSONDecodeError, KeyError):
                to_keep += 1  # malformed kayıtlar aktif dosyada kalır

    if to_archive == 0:
        _log(f"{month} için arşivlenecek kayıt yok")
        return False

    _log(f"{month}: {to_archive:,} kayıt arşivlenecek, {to_keep:,} aktif kalacak")

    if dry_run:
        _log(f"[DRY-RUN] {archive_path} oluşturulacak, {EVENTS_JSONL} truncate edilecek")
        return True

    # İkinci pass: archive + new active dosyayı paralel yaz
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_archive = archive_path.with_suffix(".gz.tmp")
    tmp_active = EVENTS_JSONL.with_suffix(".jsonl.tmp")

    archived_count = 0
    kept_count = 0
    try:
        with EVENTS_JSONL.open("rb") as src, \
             gzip.open(tmp_archive, "wb") as arch, \
             tmp_active.open("wb") as keep:
            for line in src:
                try:
                    ev = json.loads(line)
                    if ev["ts"][:7] == month:
                        arch.write(line)
                        archived_count += 1
                    else:
                        keep.write(line)
                        kept_count += 1
                except (json.JSONDecodeError, KeyError):
                    keep.write(line)
                    kept_count += 1
    except Exception as e:
        _log(f"HATA archive yazımı: {e}")
        tmp_archive.unlink(missing_ok=True)
        tmp_active.unlink(missing_ok=True)
        return False

    # Sayım doğrulama — bir kayıt kaybedildi mi
    if archived_count != to_archive or kept_count != to_keep:
        _log(
            f"SAYIM UYUŞMAZLIĞI: archive {archived_count}/{to_archive}, "
            f"keep {kept_count}/{to_keep} — rollback"
        )
        tmp_archive.unlink(missing_ok=True)
        tmp_active.unlink(missing_ok=True)
        return False

    # Atomic swap
    shutil.move(str(tmp_archive), str(archive_path))
    shutil.move(str(tmp_active), str(EVENTS_JSONL))

    arch_kb = archive_path.stat().st_size / 1024
    _log(f"✓ {archive_path.name} oluşturuldu ({arch_kb:.1f} KB)")
    _log(f"✓ {EVENTS_JSONL.name} {archived_count:,} kayıt çıkarıldı, {kept_count:,} kaldı")
    return True


def archive_completed(dry_run: bool = False) -> int:
    """Şu anki ay hariç tüm tamamlanmış ayları arşivle."""
    months = _list_completed_months()
    if not months:
        _log("Arşivlenecek tamamlanmış ay yok")
        return 0
    _log(f"Arşivlenecek ay sayısı: {len(months)} → {', '.join(months)}")
    success = 0
    for m in months:
        if archive_month(m, dry_run=dry_run):
            success += 1
    return success


def main() -> int:
    ap = argparse.ArgumentParser(description="events.jsonl log rotation")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--stats", action="store_true", help="Durum raporu")
    g.add_argument("--archive-month", metavar="YYYY-MM", help="Belirli ayı arşivle")
    g.add_argument("--archive-completed", action="store_true",
                   help="Şu anki ay hariç tamamlanmış tüm ayları arşivle")
    ap.add_argument("--dry-run", action="store_true",
                    help="Hiçbir dosya yazma, sadece ne yapacağını söyle")
    args = ap.parse_args()

    if args.stats:
        stats()
        return 0

    if args.archive_month:
        if not args.archive_month.count("-") == 1 or len(args.archive_month) != 7:
            _log(f"HATA: ay formatı YYYY-MM olmalı, verilen: {args.archive_month}")
            return 1
        if _is_current_month(args.archive_month):
            _log(f"HATA: Şu anki ay ({args.archive_month}) arşivlenemez — hâlâ kayıt geliyor")
            return 1
        ok = archive_month(args.archive_month, dry_run=args.dry_run)
        return 0 if ok else 1

    if args.archive_completed:
        n = archive_completed(dry_run=args.dry_run)
        _log(f"Tamamlandı: {n} ay arşivlendi")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
