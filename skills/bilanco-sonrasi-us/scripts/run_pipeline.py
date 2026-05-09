#!/usr/bin/env python3
"""
Bilanço Sonrası ABD Fırsat Tarayıcısı — Pipeline Runner

5 aşamayı sırayla çalıştırır, ara JSON'ları workspace dizininde tutar.

Kullanım:
    python run_pipeline.py --from 2026-05-07 --to 2026-05-08 --year 2026 --quarter 1
    python run_pipeline.py --from 2026-08-01 --to 2026-08-02 --year 2026 --quarter 2 --top 5

Argümanlar:
    --from / --to          : Bilanço tarama dönemi (zorunlu)
    --year / --quarter     : Calendar yıl ve çeyrek (transcript çekme için, varsayılan: tarihten türetilir)
    --13f-year / --13f-quarter : 13F dönemi (varsayılan: bilanço çeyreğinin bir öncesi, SEC 45 gün gecikme)
    --top                  : Final shortlist boyutu (varsayılan: 10)
    --workspace            : Ara dosyaların kaydedileceği dizin (varsayılan: ./workspace_YYYYMMDD)
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def run_step(script_path, args, cwd):
    """Alt script'i çalıştır, hata varsa exit."""
    print(f"\n{'='*80}\nÇALIŞTIRILIYOR: {script_path.name}\n{'='*80}")
    cmd = [sys.executable, str(script_path)] + args
    print(f"$ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\nHATA: {script_path.name} exit code {result.returncode}")
        sys.exit(result.returncode)


def derive_year_quarter(date_str):
    """Tarihten calendar year ve quarter türetir."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    quarter = (d.month - 1) // 3 + 1
    return d.year, quarter


def derive_13f_period(year, quarter):
    """Bilanço çeyreğinin bir öncesi (SEC 45 gün gecikme nedeniyle)."""
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_date", required=True)
    ap.add_argument("--to", dest="to_date", required=True)
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--quarter", type=int, default=None)
    ap.add_argument("--13f-year", dest="thirteenf_year", type=int, default=None)
    ap.add_argument("--13f-quarter", dest="thirteenf_quarter", type=int, default=None)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--workspace", default=None)
    args = ap.parse_args()
    
    # Calendar year/quarter türet
    if args.year is None or args.quarter is None:
        y, q = derive_year_quarter(args.from_date)
        args.year = args.year or y
        args.quarter = args.quarter or q
    
    # 13F periyodu türet (bilanço çeyreğinin önceki çeyreği — SEC 45 gün gecikme)
    if args.thirteenf_year is None or args.thirteenf_quarter is None:
        ty, tq = derive_13f_period(args.year, args.quarter)
        args.thirteenf_year = args.thirteenf_year or ty
        args.thirteenf_quarter = args.thirteenf_quarter or tq
    
    # Workspace
    if args.workspace is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.workspace = f"workspace_{ts}"
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'#'*80}")
    print(f"# Bilanço Sonrası ABD Fırsat Tarayıcısı — Pipeline")
    print(f"{'#'*80}")
    print(f"# Bilanço dönemi: {args.from_date} → {args.to_date}")
    print(f"# Calendar year/quarter (transcript): Q{args.quarter} {args.year}")
    print(f"# 13F yılı/çeyreği: Q{args.thirteenf_quarter} {args.thirteenf_year}")
    print(f"# Workspace: {workspace}")
    print(f"# Top final: {args.top}")
    print(f"{'#'*80}")
    
    scripts_dir = Path(__file__).parent
    
    # Aşama 1: Earnings calendar + mid-cap+
    run_step(scripts_dir / "01_earnings_calendar.py",
             ["--from", args.from_date, "--to", args.to_date, "--out", "01_filtered_midcap.json"],
             cwd=workspace)
    
    # Aşama 2: Growth filter
    run_step(scripts_dir / "02_growth_filter.py",
             ["--in", "01_filtered_midcap.json", "--out", "02_growth_passed.json"],
             cwd=workspace)
    
    # Aşama 3: Adil değer + sağlamlık
    run_step(scripts_dir / "03_valuation.py",
             ["--in", "02_growth_passed.json", "--out", "03_solid_shortlist.json", "--top", "45"],
             cwd=workspace)
    
    # Aşama 4: Post-earnings sinyaller (transcript + 13F + analist revize)
    run_step(scripts_dir / "04_post_earnings_signals.py",
             ["--in", "03_solid_shortlist.json", "--out", "04_signals_enriched.json",
              "--earnings-from", args.from_date,
              "--year", str(args.year), "--quarter", str(args.quarter),
              "--13f-year", str(args.thirteenf_year),
              "--13f-quarter", str(args.thirteenf_quarter)],
             cwd=workspace)
    
    # Aşama 5: Final sıralama + yıldız
    run_step(scripts_dir / "05_finalize.py",
             ["--in", "04_signals_enriched.json", "--out", "05_final_ranked.json",
              "--top", str(args.top)],
             cwd=workspace)
    
    print(f"\n{'#'*80}")
    print(f"# PIPELINE TAMAMLANDI")
    print(f"# Final sonuçlar: {workspace}/05_final_ranked.json")
    print(f"# Ara çıktılar: {workspace}/01-04_*.json")
    print(f"{'#'*80}\n")
    print("Sonraki adım: 05_final_ranked.json içeriğini templates/rapor_template.md ile rapor olarak yaz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
