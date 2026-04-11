#!/usr/bin/env python3
"""
Finzora AI — Sabah Bağlam Toplayıcısı
Katman 1-7'nin tüm inject çıktılarını birleştirir.
Her sabah PART1_SABAH promptundan önce çalıştırılır.

Kullanım:
  python3 scripts/morning_context.py --vix 19.23
"""
import sys, os, argparse
from pathlib import Path
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vix", type=float, default=0.0)
    args = parser.parse_args()

    print("=" * 65)
    print("  🌅 FİNZORA AI — SABAH BAĞLAM RAPORU")
    print("=" * 65)

    # Katman 1: Episodik bellek
    try:
        from memory_update import sabah_bellegi_uret
        print(sabah_bellegi_uret())
    except Exception as e:
        print(f"  [Katman 1] ⚠️ {e}")

    # Katman 4: Piyasa rejimi
    try:
        import subprocess
        vix_arg = ["--vix", str(args.vix)] if args.vix > 0 else []
        r = subprocess.run(
            [sys.executable, "scripts/market_regime.py", "--inject"] + vix_arg,
            capture_output=True, text=True, cwd=BASE
        )
        print("\n" + r.stdout.strip())
    except Exception as e:
        print(f"  [Katman 4] ⚠️ {e}")

    # Katman 7: Sentiment
    try:
        r = subprocess.run(
            [sys.executable, "scripts/sentiment_engine.py", "--inject"],
            capture_output=True, text=True, cwd=BASE
        )
        # Sadece özet satırları
        lines = [l for l in r.stdout.splitlines() if l.strip() and "çekiliyor" not in l]
        print("\n" + "\n".join(lines))
    except Exception as e:
        print(f"  [Katman 7] ⚠️ {e}")

    print("\n" + "=" * 65)

if __name__ == "__main__":
    main()
