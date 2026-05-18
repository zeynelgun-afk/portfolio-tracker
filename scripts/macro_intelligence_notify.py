#!/usr/bin/env python3
"""
Finzora AI — Macro Intelligence Telegram Bildirim
====================================================
data/macro_intelligence.json'ı okur, Zeynel DM'ine günlük özet gönderir.

Kullanım:
  python scripts/macro_intelligence_notify.py

Çalışma zamanı: agent.yml sabah modunda "Agent calistir" adımından sonra.
Grup değil, ZEYNEL DM'e gider (macro özeti sistem içeriği).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent
MACRO_FILE   = REPO_ROOT / "data" / "macro_intelligence.json"
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DM_CHAT_ID   = os.environ.get("TELEGRAM_PRIVATE_ID", "") or \
               os.environ.get("TELEGRAM_PRIVATE_CHAT", "") or "1403072107"

TR_AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}


def _tarih_format(iso_str: str) -> str:
    """ISO 8601 → '20 Nisan 2026' formatı."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return f"{dt.day} {TR_AYLAR.get(dt.month, '?')} {dt.year}"
    except Exception:
        return iso_str[:10]


def _truncate(text: str, n: int) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0] + "…"


def _kriz_aciklama(kriz: dict) -> str:
    tip = kriz.get("type") or kriz.get("tip", "belirsiz")
    guven = kriz.get("confidence") or kriz.get("guven", 0)
    if tip == "yok" or not tip:
        return f"yok (güven {guven}/10)"
    return f"{tip} (güven {guven}/10)"


def format_message(data: dict) -> str:
    tarih = _tarih_format(data.get("date") or data.get("tarih", ""))
    vix = data.get("vix", 0)
    mod = data.get("market_mode") or data.get("piyasa_modu", "nötr")
    kriz = data.get("active_crisis") or data.get("aktif_kriz", {}) or {}
    temalar = data.get("dominant_themes") or data.get("dominant_temalar", []) or []
    kacin = (data.get("avoid_sectors") or data.get("kacınılacak", [])
             or data.get("kaçınılacak_sektörler", []) or [])
    yorum = data.get("overview") or data.get("genel_yorum", "")

    lines = []
    lines.append(f"🧠 *MAKRO ZEKA — {tarih}*")
    lines.append("")
    lines.append(f"VIX: {vix} · Piyasa: {mod}")
    lines.append(f"Aktif kriz: {_kriz_aciklama(kriz)}")
    lines.append("")

    if temalar:
        lines.append("*🎯 DOMİNANT TEMALAR*")
        lines.append("")
        for i, t in enumerate(temalar[:4], 1):
            tema_adi = (t.get("theme_name") or t.get("tema_adi", "?")).replace("_", " ")
            skor = t.get("strength_score") or t.get("güç_skoru") or t.get("guc_skoru", "?")
            portfoy = t.get("portfolio") or t.get("portföy") or t.get("portfoy", "?")
            aciliyet = t.get("urgency") or t.get("aciliyet", "?")
            tickers = t.get("suggested_tickers") or t.get("önerilen_hisseler") or t.get("onerilen_hisseler", [])
            hisseler = ", ".join(tickers[:5])
            alt = t.get("priority_subsector") or t.get("öncelikli_alt_dal") or t.get("oncelikli_alt_dal", "")
            alt_dal = alt.replace("_", " ")
            neden = _truncate(t.get("reason") or t.get("neden", ""), 240)

            lines.append(f"{i}. *{tema_adi}* ({skor}/10) · {portfoy} · {aciliyet}")
            if hisseler:
                alt_kismi = f" ({alt_dal})" if alt_dal else ""
                lines.append(f"   → {hisseler}{alt_kismi}")
            if neden:
                lines.append(f"   {neden}")
            lines.append("")
    else:
        lines.append("_Bugün dominant tema tespit edilemedi._")
        lines.append("")

    if kacin:
        lines.append(f"⚠️ Kaçınılacak: {', '.join(kacin[:6])}")
        lines.append("")

    if yorum:
        lines.append(f"💬 {_truncate(yorum, 320)}")

    msg = "\n".join(lines)
    # Telegram limit 4096 — güvenli tarafta kal
    return msg[:3900]


def send(msg: str) -> bool:
    if not BOT_TOKEN:
        print("[MacroNotify] TELEGRAM_BOT_TOKEN yok, gönderilmedi")
        return False

    import requests
    try:
        r = requests.post(
            TELEGRAM_API.format(token=BOT_TOKEN),
            data={
                "chat_id": DM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        resp = r.json()
        if resp.get("ok"):
            print(f"[MacroNotify] DM gönderildi (chat_id={DM_CHAT_ID})")
            return True
        # Markdown parse hatası olursa düz metin tekrar dene
        desc = resp.get("description", "")
        if "can't parse" in desc.lower() or "parse" in desc.lower():
            plain = msg.replace("*", "").replace("_", "")
            r2 = requests.post(
                TELEGRAM_API.format(token=BOT_TOKEN),
                data={"chat_id": DM_CHAT_ID, "text": plain,
                      "disable_web_page_preview": True},
                timeout=15,
            )
            if r2.json().get("ok"):
                print("[MacroNotify] DM gönderildi (düz metin fallback)")
                return True
        print(f"[MacroNotify] Hata: {desc}")
        return False
    except Exception as e:
        print(f"[MacroNotify] İstisna: {e}")
        return False


def main():
    if not MACRO_FILE.exists():
        print(f"[MacroNotify] {MACRO_FILE} bulunamadı, atlandı")
        return 0

    try:
        data = json.loads(MACRO_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[MacroNotify] JSON okunamadı: {e}")
        return 1

    # Tazelik kontrolü: 24 saatten eski veri gönderme
    try:
        tarih = datetime.fromisoformat(data.get("date") or data.get("tarih", ""))
        yas_saat = (datetime.now(tarih.tzinfo) - tarih).total_seconds() / 3600
        if yas_saat > 36:
            print(f"[MacroNotify] Veri {yas_saat:.0f}s eski, gönderilmedi "
                  f"(macro_intelligence.py bugün çalıştı mı?)")
            return 0
    except Exception:
        pass  # tarih parse edilemezse yine de gönder

    msg = format_message(data)
    return 0 if send(msg) else 1


if __name__ == "__main__":
    sys.exit(main())
