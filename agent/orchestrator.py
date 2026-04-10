#!/usr/bin/env python3
"""
Finzora Agent — Orkestratör (Phase 1)
======================================
SADECE İZLER. Hiçbir veri dosyasına yazmaz.
Tüm yorumlar Zeynel'e özel Telegram'a gider.

Çalışma zamanları (GitHub Actions):
  - Sabah: 13:00 UTC (16:00 TR) — piyasa öncesi analiz
  - Kapanış: 21:30 UTC (00:30 TR) — kapanış yorumu
  - İzleme: her 30dk piyasa saatlerinde — stop/fırsat uyarısı
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import pytz

# Agent modülleri
sys.path.insert(0, str(Path(__file__).parent))
from claude_agent import get_claude_decision
from tools import (
    get_portfolio_snapshot,
    get_market_context,
    get_swing_status,
    get_watchlist,
    send_private_telegram
)

REPO_ROOT = Path(__file__).parent.parent
TR_TZ     = pytz.timezone("Europe/Istanbul")

# ── Zaman dilimi tespiti ──────────────────────────────────────────────────────

def get_run_mode() -> str:
    """
    Hangi modda çalışıyoruz?
    GitHub Actions'tan MODE env değişkeni gelir.
    Yoksa saate göre otomatik tespit.
    """
    mode = os.environ.get("AGENT_MODE", "").lower()
    if mode in ("morning", "closing", "monitor", "weekly"):
        return mode

    now = datetime.now(TR_TZ)
    h   = now.hour + now.minute / 60

    if 15.0 <= h <= 16.5:
        return "morning"
    elif 23.0 <= h or h <= 1.0:
        return "closing"
    elif 16.5 <= h <= 23.0:
        return "monitor"
    else:
        return "morning"  # default

# ── Veri toplama ─────────────────────────────────────────────────────────────

def collect_context(mode: str) -> dict:
    """Tüm bağlamı topla, Claude'a hazırla."""
    print(f"[Orkestratör] Veri toplanıyor... (mod: {mode})")

    ctx = {
        "mode":      mode,
        "timestamp": datetime.now(TR_TZ).isoformat(),
        "portfolios": get_portfolio_snapshot(),
        "market":     get_market_context(),
        "swing":      get_swing_status(),
        "watchlist":  get_watchlist(),
    }

    # K-kuralları playbook'u oku (Claude'un hafızası)
    playbook_path = REPO_ROOT / "docs" / "TRADING_PLAYBOOK.md"
    if playbook_path.exists():
        ctx["playbook"] = playbook_path.read_text(encoding="utf-8")[:8000]  # İlk 8K token

    # Son kapanış raporunu oku (bağlam için)
    reports_dir = REPO_ROOT / "reports" / "daily"
    if reports_dir.exists():
        reports = sorted(reports_dir.glob("*KAPANIS*.md"), reverse=True)
        if reports:
            ctx["last_report"] = reports[0].read_text(encoding="utf-8")[:3000]

    return ctx

# ── Mod çalıştırıcıları ───────────────────────────────────────────────────────

def run_morning(ctx: dict):
    """Sabah analizi — piyasa açılmadan önce."""
    print("[Orkestratör] Sabah modu çalışıyor...")

    prompt = f"""
Sen Finzora Agent'sın. Zeynel'in portföy asistanısın.
Bugün {ctx['timestamp']} — piyasa açılmadan önce sabah analizi yapıyorsun.

PORTFÖY DURUMU:
{json.dumps(ctx['portfolios'], ensure_ascii=False, indent=2)[:3000]}

PİYASA BAĞLAMI:
{json.dumps(ctx['market'], ensure_ascii=False, indent=2)}

SWING DURUMU:
{json.dumps(ctx['swing'], ensure_ascii=False, indent=2)}

K-KURALLARI (özet):
{ctx.get('playbook','')[:2000]}

Görevin:
1. Portföylerdeki pozisyonları tara — stop'a yakın olan var mı? (K-09)
2. Bugün dikkat edilmesi gereken makro/earnings var mı?
3. Swing watchlist'te güçlü setup var mı?
4. Genel piyasa rejimi: RISK_ON / NEUTRAL / RISK_OFF?
5. Önerdiğin 1-2 aksiyon (henüz UYGULAMA, sadece öneri)

Format: Doğal Türkçe, kısa ve net. Madde madde yaz.
Belirsiz şeyleri SPEKÜLATİF olarak işaretle.
Sonda: "Bugün gözüm şunlarda olacak: ..."
"""

    response = get_claude_decision(prompt, mode="morning")
    
    msg = f"🌅 *Finzora Agent — Sabah Analizi*\n_{ctx['timestamp'][:16]}_\n\n{response}"
    send_private_telegram(msg)
    print("[Orkestratör] Sabah analizi Telegram'a gönderildi.")

def run_closing(ctx: dict):
    """Kapanış yorumu — piyasa kapandıktan sonra."""
    print("[Orkestratör] Kapanış modu çalışıyor...")

    prompt = f"""
Sen Finzora Agent'sın.
Bugün {ctx['timestamp']} — piyasa kapandı, kapanış analizi yapıyorsun.

PORTFÖY DURUMU:
{json.dumps(ctx['portfolios'], ensure_ascii=False, indent=2)[:3000]}

PİYASA BAĞLAMI:
{json.dumps(ctx['market'], ensure_ascii=False, indent=2)}

SON RAPOR (varsa):
{ctx.get('last_report','Yok')[:1500]}

Görevin:
1. Bugün portföylerde ne değişti? Hangi pozisyon en çok etkilendi?
2. Stop seviyelerine yaklaşan var mı? (kritik olanları vurgula)
3. Tezler hâlâ geçerli mi? Bozan bir gelişme var mı?
4. Yarın için izleme listesi: En önemli 3 şey.
5. Hafta genelinde bir pattern görüyor musun?

Format: Doğal Türkçe, kısa ve net.
KESİN / MUHTEMEL / SPEKÜLATİF etiketlerini kullan.
"""

    response = get_claude_decision(prompt, mode="closing")

    msg = f"📊 *Finzora Agent — Kapanış Yorumu*\n_{ctx['timestamp'][:16]}_\n\n{response}"
    send_private_telegram(msg)
    print("[Orkestratör] Kapanış yorumu Telegram'a gönderildi.")

def run_monitor(ctx: dict):
    """Seans içi izleme — sadece acil durumda mesaj atar."""
    print("[Orkestratör] İzleme modu çalışıyor...")

    portfolios = ctx["portfolios"]
    market     = ctx["market"]
    alerts     = []

    # Stop yakınlık kontrolü (basit, Claude'suz — ucuz)
    for pf_name, pf_data in portfolios.items():
        for pos in pf_data.get("pozisyonlar", []):
            symbol   = pos.get("sembol", "?")
            stop     = pos.get("stop_loss")
            cur_price = pos.get("guncel_fiyat") or pos.get("son_fiyat")

            if not stop or not cur_price:
                continue

            try:
                stop      = float(stop)
                cur_price = float(cur_price)
                pct       = (cur_price - stop) / stop * 100

                if pct <= 2.0:
                    alerts.append(
                        f"⚠️ *STOP YAKINI* [{pf_name.upper()}]\n"
                        f"{symbol}: ${cur_price:.2f} — Stop ${stop:.2f} "
                        f"(%{pct:.1f} uzakta)"
                    )
            except (ValueError, TypeError):
                continue

    # VIX yüksekse uyar
    vixy = market.get("VIXY", {})
    vixy_price = vixy.get("price", 0)
    if vixy_price and float(vixy_price) > 18:
        alerts.append(
            f"🔴 *VIX YÜKSEK* VIXY: ${vixy_price} — K-13 aktif, yeni giriş kısıtlı"
        )

    # Sadece alert varsa mesaj gönder (Claude'u meşgul etme)
    if alerts:
        msg = "🔔 *Finzora Agent — Seans Uyarısı*\n\n" + "\n\n".join(alerts)
        send_private_telegram(msg)
        print(f"[Orkestratör] {len(alerts)} uyarı gönderildi.")
    else:
        print("[Orkestratör] İzleme tamamlandı, uyarı yok.")

def run_weekly(ctx: dict):
    """Pazar günü haftalık derin analiz."""
    print("[Orkestratör] Haftalık mod çalışıyor...")

    prompt = f"""
Sen Finzora Agent'sın. Haftalık derin analiz yapıyorsun.
Tarih: {ctx['timestamp']}

PORTFÖY DURUMU:
{json.dumps(ctx['portfolios'], ensure_ascii=False, indent=2)[:4000]}

K-KURALLARI:
{ctx.get('playbook','')[:3000]}

Görevin:
1. Bu haftanın özeti: Portföyler toplamda nasıl performans gösterdi?
2. En iyi / en kötü pozisyon ve neden?
3. Hangi K-kuralı bu hafta en çok devreye girdi?
4. Tezlerde değişen bir şey var mı? (AI supply chain, temettü, makro)
5. Gelecek hafta için 3 kritik izleme noktası
6. Bir şeyi değiştirmemi öneriyor musun? (Kural, filtre, pozisyon)

Format: Daha uzun olabilir, detaylı Türkçe analiz.
Spekülatif öneriler için "BACKTEST GEREKLİ" işareti koy.
"""

    response = get_claude_decision(prompt, mode="weekly")

    msg = f"📅 *Finzora Agent — Haftalık Analiz*\n_{ctx['timestamp'][:16]}_\n\n{response}"
    send_private_telegram(msg)
    print("[Orkestratör] Haftalık analiz Telegram'a gönderildi.")

# ── Ana giriş ─────────────────────────────────────────────────────────────────

def main():
    print(f"[Finzora Agent] Başlatılıyor — {datetime.now(TR_TZ).strftime('%Y-%m-%d %H:%M TR')}")

    mode = get_run_mode()
    print(f"[Finzora Agent] Mod: {mode.upper()}")

    ctx = collect_context(mode)

    if mode == "morning":
        run_morning(ctx)
    elif mode == "closing":
        run_closing(ctx)
    elif mode == "monitor":
        run_monitor(ctx)
    elif mode == "weekly":
        run_weekly(ctx)
    else:
        print(f"[Finzora Agent] Bilinmeyen mod: {mode}")
        sys.exit(1)

    print("[Finzora Agent] Tamamlandı.")

if __name__ == "__main__":
    main()
