"""
Bilanço Müdürü — Konfigürasyon

Tüm sabitler, saat pencereleri, eşikler burada.
"""
from __future__ import annotations
import os

# === Operasyon Modu ===
# İlk hafta DRY_RUN=True — DM'lere [DRY-RUN] prefix'i, gerçek karar değil
DRY_RUN = os.environ.get("BILANCO_MUDURU_DRY_RUN", "1") == "1"

# === Saat Pencereleri (TR saat) ===
# Tick fonksiyonu her 60 saniyede çağrılır. İçerideki saat kontrolü hangi
# pencerede olduğumuzu belirler.

# AMC erken pencere — ana yoğunluk (~%70 bilanço)
AMC_EARLY_START_HOUR = 22       # TR 22:00
AMC_EARLY_END_HOUR = 25         # TR 01:00 ertesi gün (24+1 = 25 mod 24)
AMC_EARLY_INTERVAL_MIN = 15     # 15 dakikada bir tarama

# BMO pencere — sabah açıklamalar (JPM, JNJ gibi)
BMO_START_HOUR = 13             # TR 13:00
BMO_END_HOUR = 17               # TR 16:30 + buffer
BMO_INTERVAL_MIN = 15

# Tekil zaman noktaları
T_MINUS_1_SNAPSHOT_HOUR = 17    # 17:00 — bugün/yarın bilanço için snapshot
T_MINUS_1_SNAPSHOT_MINUTE = 0

CATCHUP_MORNING_HOUR = 8        # 08:30 — gece+haftasonu catchup
CATCHUP_MORNING_MINUTE = 30

CATCHUP_LATE_HOUR = 2           # 02:00 — AMC geç catchup
CATCHUP_LATE_MINUTE = 0

# === Eşikler ===
# Sadece market cap > $5B şirketleri işle (mikrocap'leri at, gürültü çok)
MIN_MARKET_CAP_B = 5.0

# Pre-earnings snapshot zorunluluğu yok ama varsa daha iyi
REQUIRE_PRE_EARNINGS_SNAPSHOT = False

# Maliyet koruması: günde max 50 Kimi çağrısı (~$0.50)
MAX_DAILY_KIMI_CALLS = 50

# === Dosya Yolları ===
EARNINGS_STATE_DIR = "data/earnings_state"
EARNINGS_SNAPSHOTS_DIR = "data/earnings_snapshots"
EARNINGS_RESULTS_DIR = "data/earnings_results"
BILANCO_MUDURU_LOG = "logs/bilanco_muduru.log"

# === Telegram ===
# Memory satır 9: DM 1403072107, GRUP -1003827034395 YASAK
TELEGRAM_DM_CHAT_ID = 1403072107  # @Zeynelgun
TELEGRAM_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
TELEGRAM_BOT_TOKEN_FALLBACK = "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI"

# === Karar Eşikleri (implied_multiple_valuation default'larını override etmez) ===
# Sadece info olarak burada — kod logic'i kimi_parser.py içinde
DECISION_BUY_UPSIDE_PCT = 20
DECISION_WATCH_LOWER_PCT = -5

# === Anahtarlar (env'den oku) ===
def get_fmp_key() -> str:
    return os.environ.get("FMP_API_KEY") or "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"

def get_openrouter_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY") or ""
