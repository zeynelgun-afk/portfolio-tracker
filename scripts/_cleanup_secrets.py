#!/usr/bin/env python3
"""
Hardcoded secret temizlik script'i.
TEK SEFERLİK kullanılır — repo kök dizininden çalıştırılır.

Yaptıkları:
1. Tüm .py dosyalarındaki hardcoded FMP key ve Telegram token'ı
   os.environ.get(..., "") haline çevirir.
2. Fallback değerleri boşaltır.
3. Değişen dosya sayısını raporlar.
"""

import os
import re
from pathlib import Path


FMP_HARDCODED = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
TELEGRAM_HARDCODED = "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI"
CHAT_HARDCODED = "1403072107"


def clean_file(path: Path) -> int:
    """Tek dosyayı temizle, değişen satır sayısını dön."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return 0

    original = text

    # FMP key: "g1GFJZtV..." fallback'lerini "" yap
    # Pattern 1: os.environ.get("FMP_API_KEY", "g1GFJZtV...")
    text = re.sub(
        rf'os\.environ\.get\(\s*"(FMP_API_KEY|FMP_KEY)"\s*,\s*"{FMP_HARDCODED}"\s*\)',
        r'os.environ.get("\1", "")',
        text,
    )
    # Pattern 2: FMP_KEY = "g1GFJZtV..."
    text = re.sub(
        rf'^(\s*_?FMP_KEY\s*=\s*)"{FMP_HARDCODED}"',
        r'\1os.environ.get("FMP_API_KEY", "")',
        text,
        flags=re.MULTILINE,
    )
    # Pattern 3: "apikey": "g1GFJZtV..."
    text = re.sub(
        rf'"apikey"\s*:\s*"{FMP_HARDCODED}"',
        r'"apikey": os.environ.get("FMP_API_KEY", "")',
        text,
    )

    # Telegram BOT_TOKEN
    text = re.sub(
        rf'os\.environ\.get\(\s*"(TELEGRAM_TOKEN|TELEGRAM_BOT_TOKEN)"\s*,\s*""\s*\)\s*or\s*"{TELEGRAM_HARDCODED}"',
        r'os.environ.get("\1", "")',
        text,
    )
    text = re.sub(
        rf'os\.environ\.get\(\s*"(TELEGRAM_TOKEN|TELEGRAM_BOT_TOKEN)"\s*,\s*"{TELEGRAM_HARDCODED}"\s*\)',
        r'os.environ.get("\1", "")',
        text,
    )
    # TG_TOKEN = "8749..."  (adil_deger_calculator gibi)
    text = re.sub(
        rf'^(\s*TG?_TOKEN\s*=\s*)"{TELEGRAM_HARDCODED}"',
        r'\1os.environ.get("TELEGRAM_TOKEN", "")',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        rf'^(\s*BOT_TOKEN\s*=\s*)"{TELEGRAM_HARDCODED}"',
        r'\1os.environ.get("TELEGRAM_TOKEN", "")',
        text,
        flags=re.MULTILINE,
    )

    # PRIVATE_CHAT
    text = re.sub(
        rf'os\.environ\.get\(\s*"TELEGRAM_PRIVATE_CHAT"\s*,\s*""\s*\)\s*or\s*"{CHAT_HARDCODED}"',
        r'os.environ.get("TELEGRAM_PRIVATE_CHAT", "")',
        text,
    )
    text = re.sub(
        rf'os\.environ\.get\(\s*"TELEGRAM_PRIVATE_CHAT"\s*,\s*"{CHAT_HARDCODED}"\s*\)',
        r'os.environ.get("TELEGRAM_PRIVATE_CHAT", "")',
        text,
    )

    # JS dosyası (finzora-bot.js) için basit fallback temizleme
    if path.suffix == ".js":
        text = re.sub(
            rf"process\.env\.(TELEGRAM_TOKEN|BOT_TOKEN)\s*\|\|\s*'{TELEGRAM_HARDCODED}'",
            r"process.env.\1 || ''",
            text,
        )
        text = re.sub(
            rf"process\.env\.(FMP_API_KEY|FMP_KEY)\s*\|\|\s*'{FMP_HARDCODED}'",
            r"process.env.\1 || ''",
            text,
        )

    if text != original:
        path.write_text(text, encoding="utf-8")
        # Değişen satır sayısı
        orig_lines = original.count("\n")
        new_lines = text.count("\n")
        return 1
    return 0


def main():
    repo = Path(__file__).resolve().parent.parent
    if not (repo / "agent").exists() or not (repo / "scripts").exists():
        print(f"ERROR: Repo kök dizininden çalıştırılmalı. Aranan: {repo}")
        return 1

    changed_files = []
    for ext in ("*.py", "*.js"):
        for path in sorted(
            list(repo.glob(f"agent/**/{ext}")) + list(repo.glob(f"scripts/**/{ext}"))
        ):
            if clean_file(path):
                changed_files.append(path.relative_to(repo))

    print(f"Temizlenen dosya sayısı: {len(changed_files)}")
    for p in changed_files:
        print(f"  - {p}")

    # Doğrulama
    print("\n=== Kalan hardcoded pattern kontrolü ===")
    import subprocess
    for pattern in [FMP_HARDCODED, TELEGRAM_HARDCODED, CHAT_HARDCODED]:
        result = subprocess.run(
            ["grep", "-rln", pattern, "agent/", "scripts/"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        remaining = [ln for ln in result.stdout.strip().split("\n") if ln]
        if remaining:
            print(f"  {pattern[:15]}...: {len(remaining)} dosyada kaldı:")
            for r in remaining[:5]:
                print(f"    - {r}")
        else:
            print(f"  {pattern[:15]}...: TEMİZ")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
