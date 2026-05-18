#!/usr/bin/env bash
# Finzora AI — lokal pre-commit hook kurulum script'i
#
# Kullanım:
#   bash scripts/install_pre_commit_hook.sh
#
# Kaldırma:
#   rm .git/hooks/pre-commit

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HOOK_TARGET=".git/hooks/pre-commit"
HOOK_SOURCE="../../scripts/pre_commit_hook.sh"

# Mevcut hook var mı?
if [ -e "$HOOK_TARGET" ] || [ -L "$HOOK_TARGET" ]; then
    echo "⚠️  $HOOK_TARGET zaten mevcut."
    read -p "Üzerine yaz? [e/H] " yn
    case "$yn" in
        [eE]) rm -f "$HOOK_TARGET" ;;
        *) echo "İptal edildi"; exit 0 ;;
    esac
fi

# Symlink oluştur (relative path — repo taşıması güvenli)
ln -s "$HOOK_SOURCE" "$HOOK_TARGET"
chmod +x "scripts/pre_commit_hook.sh"

echo "✅ Pre-commit hook kuruldu: $HOOK_TARGET → $HOOK_SOURCE"
echo ""
echo "Davranış:"
echo "  - agent/scripts/tests veya 8 migrate edilmiş JSON dosyası değişirse"
echo "    commit öncesi migration health check (17 dual-schema test) çalışır."
echo "  - Hata varsa commit bloke olur."
echo ""
echo "Bypass: git commit --no-verify"
echo ""
echo "Pytest dahil et: PRE_COMMIT_RUN_TESTS=1 git commit ..."
