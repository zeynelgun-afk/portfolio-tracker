"""
Analist Takip — Konfigürasyon

Sistem bilanço sonrası analist hedef revizyonlarını ve grade
değişikliklerini takip eder, threshold-based kararlar üretir,
DM'ye bildirim gönderir.
"""
from __future__ import annotations
import os

# === Operasyon Modu ===
DRY_RUN = os.environ.get("ANALIST_TAKIP_DRY_RUN", "1") == "1"

# === Saat Pencereleri (TR) ===
# Pre-NYSE: 13:00-16:30 — 60dk (analist sabah haberleri)
PRE_NYSE_START_HOUR = 13
PRE_NYSE_END_HOUR = 17  # 16:30 + buffer
PRE_NYSE_INTERVAL_MIN = 60

# NYSE açık: 16:30-23:30 — 30dk (asıl revizyon penceresi)
NYSE_OPEN_START_HOUR = 16
NYSE_OPEN_END_HOUR = 24
NYSE_OPEN_INTERVAL_MIN = 30

# After-hours: 23:30-01:30 — 30dk (bilanço sonrası dalga)
AFTER_HOURS_START_HOUR = 23
AFTER_HOURS_END_HOUR = 26  # 02:00 ertesi gün (24+2)
AFTER_HOURS_INTERVAL_MIN = 30

# Cumartesi catchup
SATURDAY_CATCHUP_HOUR = 10
SATURDAY_CATCHUP_MINUTE = 0

# === Watchlist ===
# Otomatik watchlist süresi: Bilanço açıklayan şirket kaç gün izlenir
POST_EARNINGS_WATCH_DAYS = 14
# Portföy ticker'ları sürekli watchlist'te (çıkış yok)
PORTFOLIO_ALWAYS_WATCH = True

# === Karar Eşikleri ===
# Sinyal pencereleri (saat)
SIGNAL_WINDOW_RECENT_HOURS = 24    # "Son X saat" pencere
SIGNAL_WINDOW_TOTAL_HOURS = 48     # Toplam pencere

# AL eşikleri
# 14 May 2026 (Zeynel kararı): nicelikten niteliğe — 3 analist x %5 yerine
# 1 analist x %20+ konvik. Az tetiklenir ama daha güçlü sinyal.
STRONG_BUY_MIN_RAISED = 1
STRONG_BUY_MIN_AVG_PCT = 20.0
STRONG_BUY_MAX_LOWERED = 0

BUY_BIG_RAISE_PCT = 25.0           # Tek bir analistin >%25 hedef artışı
BUY_MIN_NET_RAISED = 2

# SAT eşikleri
SELL_MIN_LOWERED = 2
SELL_BIG_CUT_PCT = -15.0
STRONG_SELL_MIN_LOWERED = 3
STRONG_SELL_DOWNGRADE_REQUIRED = True

# === Dosya Yolları ===
ANALIST_STATE_DIR = "data/analist_takip"
WATCHLIST_PATH = "data/analist_takip/watchlist.json"
PROCESSED_REVISIONS_PATH = "data/analist_takip/processed_revisions.jsonl"
SIGNAL_HISTORY_PATH = "data/analist_takip/signals.jsonl"
ANALIST_LOG = "logs/analist_takip.log"

# === Portfolio Dosyaları ===
PORTFOLIO_FILES = [
    "data/portfolios/balanced.json",
    "data/portfolios/aggressive.json",
    "data/portfolios/dividend.json",
]
SWING_ACTIVE_FILE = "data/swing/active.json"

# === Telegram ===
TELEGRAM_DM_CHAT_ID = 1403072107  # @Zeynelgun
TELEGRAM_BOT_TOKEN_FALLBACK = "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI"

# === FMP ===
def get_fmp_key() -> str:
    return os.environ.get("FMP_API_KEY") or "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"

FMP_BASE = "https://financialmodelingprep.com/stable"

# Rate limiting: Ultimate plan 3000/dk
FMP_THROTTLE_MS = 50

# === Mid-cap eşik ===
MIN_MARKET_CAP_B = 2.0  # AAOI gibi mid-cap dahil
