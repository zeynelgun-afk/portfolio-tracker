#!/usr/bin/env python3
"""
Finzora AI — Merkezi Olay Kaydı
================================
Sistemin yaptığı veya yapamadığı her işlemi Telegram'a bildirir.

Kullanım (kod içinden):
    from scripts.event_logger import log

    log.basarili("COHR alındı", "139 adet @ $285.75 | Agresif")
    log.hata("FMP API bağlantı hatası", "batch-quote endpoint 502 döndürdü")
    log.uyari("MU stop'a yakın", "%1.8 mesafe | stop $402.99")
    log.bilgi("Fiyat güncellendi", "5 portföy pozisyonu güncellendi")
    log.calistirma("agent/monitor başladı", "04:30 UTC")

Komut satırından:
    python scripts/event_logger.py --seviye basarili --baslik "test" --detay "detay"
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

# --- CONFIG ---
BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PRIVATE_ID = os.environ.get("TELEGRAM_PRIVATE_ID", "") or os.environ.get("TELEGRAM_PRIVATE_CHAT", "")   # sadece Zeynel görür
CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID",    "-1003827034395")
API        = f"https://api.telegram.org/bot{BOT_TOKEN}"
REPO_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE   = os.path.join(REPO_ROOT, "logs", "event_log.jsonl")

# Olay tipi → emoji + hedef
SEVIYE = {
    "basarili":   {"emoji": "✅", "hedef": "private"},  # işlem başarıyla tamamlandı
    "hata":       {"emoji": "❌", "hedef": "private"},  # hata / başarısız işlem
    "kritik":     {"emoji": "🚨", "hedef": "private"},  # stop tetiklendi, kritik kural
    "uyari":      {"emoji": "⚠️", "hedef": "private"},  # dikkat gerektiren durum
    "bilgi":      {"emoji": "ℹ️", "hedef": "private"},  # bilgilendirme
    "calistirma": {"emoji": "🔄", "hedef": "private"},  # agent başladı / bitti
    "islem":      {"emoji": "💱", "hedef": "private"},  # alım / satım işlemi
}

# Hangi seviyeler Telegram'a gider (bilgi = sadece log dosyasına)
TELEGRAM_GONDER = {"basarili", "hata", "kritik", "uyari", "calistirma", "islem"}


def _send(text: str, chat_id: str = None) -> bool:
    target = chat_id or PRIVATE_ID
    payload = {
        "chat_id": target,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=15)
        return r.json().get("ok", False)
    except Exception as e:
        # Telegram'a ulaşamazsak sadece konsola yaz
        print(f"[event_logger] Telegram bağlantı hatası: {e}", file=sys.stderr)
        return False


def _log_dosya(seviye: str, baslik: str, detay: str, kaynak: str):
    """Olayı JSONL log dosyasına yaz."""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        entry = {
            "zaman": datetime.utcnow().isoformat(),
            "seviye": seviye,
            "baslik": baslik,
            "detay": detay,
            "kaynak": kaynak,
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # log dosyası yazılamazsa sessizce devam et


def _format(seviye: str, baslik: str, detay: str, kaynak: str) -> str:
    cfg   = SEVIYE.get(seviye, {"emoji": "📌"})
    emoji = cfg["emoji"]
    zaman = datetime.now().strftime("%d.%m %H:%M")
    kaynak_str = f" <code>[{kaynak}]</code>" if kaynak else ""

    msg = f"{emoji} <b>{baslik}</b>{kaynak_str}\n"
    if detay:
        # Her satırı girintiyle göster
        satirlar = detay.strip().split("\n")
        for satir in satirlar:
            msg += f"  {satir}\n"
    msg += f"<i>{zaman} • finzora ai</i>"
    return msg


def kaydet(seviye: str, baslik: str, detay: str = "", kaynak: str = "", chat_id: str = None):
    """
    Ana giriş noktası. Her yerde bu fonksiyonu çağır.
    seviye: basarili | hata | kritik | uyari | bilgi | calistirma | islem
    """
    # Her zaman dosyaya yaz
    _log_dosya(seviye, baslik, detay, kaynak)

    # Sadece belirli seviyeleri Telegram'a gönder
    if seviye in TELEGRAM_GONDER:
        msg = _format(seviye, baslik, detay, kaynak)
        _send(msg, chat_id=chat_id)


class _Logger:
    """Kolaylık: log.basarili(...), log.hata(...) gibi kullanım."""

    def __init__(self, varsayilan_kaynak: str = ""):
        self.kaynak = varsayilan_kaynak

    def _kaynak(self, kaynak: str) -> str:
        return kaynak or self.kaynak

    def basarili(self, baslik: str, detay: str = "", kaynak: str = ""):
        kaydet("basarili", baslik, detay, self._kaynak(kaynak))

    def hata(self, baslik: str, detay: str = "", kaynak: str = ""):
        kaydet("hata", baslik, detay, self._kaynak(kaynak))

    def kritik(self, baslik: str, detay: str = "", kaynak: str = ""):
        kaydet("kritik", baslik, detay, self._kaynak(kaynak))

    def uyari(self, baslik: str, detay: str = "", kaynak: str = ""):
        kaydet("uyari", baslik, detay, self._kaynak(kaynak))

    def bilgi(self, baslik: str, detay: str = "", kaynak: str = ""):
        kaydet("bilgi", baslik, detay, self._kaynak(kaynak))

    def calistirma(self, baslik: str, detay: str = "", kaynak: str = ""):
        kaydet("calistirma", baslik, detay, self._kaynak(kaynak))

    def islem(self, baslik: str, detay: str = "", kaynak: str = ""):
        kaydet("islem", baslik, detay, self._kaynak(kaynak))


# Modül düzeyinde global logger (varsayılan kaynak boş)
log = _Logger()


# --- KOMUT SATIRI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finzora Olay Kaydı")
    parser.add_argument("--seviye",  required=True,
                        choices=list(SEVIYE.keys()),
                        help="Olay seviyesi")
    parser.add_argument("--baslik",  required=True, help="Kısa başlık")
    parser.add_argument("--detay",   default="",    help="Detay açıklama")
    parser.add_argument("--kaynak",  default="",    help="Kaynak script/modül")
    args = parser.parse_args()
    kaydet(args.seviye, args.baslik, args.detay, args.kaynak)
    print(f"[{args.seviye.upper()}] {args.baslik}")
