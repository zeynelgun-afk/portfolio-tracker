#!/usr/bin/env bash
# Finzora AI — lokal pre-commit hook
#
# JSON migration sağlık check + (opsiyonel) hızlı pytest çalıştırır.
# Commit'i bloke etmek için exit kodu 1. Bypass: `git commit --no-verify`.
#
# Kurulum:
#   bash scripts/install_pre_commit_hook.sh
# veya manuel:
#   ln -s ../../scripts/pre_commit_hook.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit

set -e

# Repo root'u git'ten al (symlink-safe — hook .git/hooks/'tan çalıştırıldığında
# BASH_SOURCE relative resolve yanlış path verir)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    echo "[pre-commit] HATA: git repo root bulunamadı" >&2
    exit 1
fi
cd "$REPO_ROOT"

# Renkler
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${YELLOW}[pre-commit] Migration sağlık check başlıyor...${RESET}"

# Hızlı tarama: değişen dosyalar arasında kod/data var mı?
CHANGED=$(git diff --cached --name-only 2>/dev/null)

# Sadece kod (scripts, agent, tests) veya migrate edilmiş JSON değişti mi?
SHOULD_RUN=false
for f in $CHANGED; do
    case "$f" in
        agent/*|scripts/*|tests/*)
            SHOULD_RUN=true
            break
            ;;
        data/macro_intelligence.json|data/backtest_summary.json|\
data/discovery_signals.json|data/premarket_gaps.json|data/summary.json|\
data/research/index.json|data/weekly_pre_check.json|\
data/episodic_memory/trade_index.json)
            SHOULD_RUN=true
            break
            ;;
    esac
done

if [ "$SHOULD_RUN" != "true" ]; then
    echo -e "${GREEN}[pre-commit] İlgili değişiklik yok, atlandı${RESET}"
    exit 0
fi

# Migration health check (5-10 saniye)
export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/agent:$REPO_ROOT/agent/legacy:${PYTHONPATH:-}"
# Stub env — production'da gerçek değerler vardır, hook ortamında bunlar olmazsa
# config modülü import'unda ImportError. test_key_dummy seçildi çünkü
# tests/conftest.py:12 os.environ.setdefault aynı değeri set ediyor — testlerle
# çakışma yaratmaz (bkz. test_apikey_added_to_params).
export FMP_API_KEY="${FMP_API_KEY:-test_key_dummy}"
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-test_token_dummy}"
export TELEGRAM_PRIVATE_ID="${TELEGRAM_PRIVATE_ID:-0}"

if python3 scripts/migration_health_check.py > /tmp/health_check.log 2>&1; then
    PASS_LINE=$(grep -oE '[0-9]+/[0-9]+ test PASS' /tmp/health_check.log | head -1)
    echo -e "${GREEN}[pre-commit] ✅ Health check ${PASS_LINE:-PASS}${RESET}"
else
    echo -e "${RED}[pre-commit] ❌ Health check BAŞARISIZ${RESET}"
    echo "Detay (son 20 satır):"
    tail -20 /tmp/health_check.log
    echo ""
    echo -e "${YELLOW}Bypass için: git commit --no-verify${RESET}"
    exit 1
fi

# Opsiyonel: pytest (eğer --with-tests env varsa)
if [ "${PRE_COMMIT_RUN_TESTS:-0}" = "1" ]; then
    echo -e "${YELLOW}[pre-commit] pytest çalıştırılıyor (PRE_COMMIT_RUN_TESTS=1)...${RESET}"
    if python3 -m pytest tests/ -q --tb=no > /tmp/pytest.log 2>&1; then
        TEST_LINE=$(tail -3 /tmp/pytest.log | grep -oE '[0-9]+ passed' | head -1)
        echo -e "${GREEN}[pre-commit] ✅ ${TEST_LINE:-tests PASS}${RESET}"
    else
        echo -e "${RED}[pre-commit] ❌ pytest BAŞARISIZ${RESET}"
        tail -10 /tmp/pytest.log
        exit 1
    fi
fi

echo -e "${GREEN}[pre-commit] Tüm check'ler geçti, commit'e devam${RESET}"
exit 0
