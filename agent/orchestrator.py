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
from memory_manager import (
    build_portfolio_state,
    save_portfolio_state,
    save_daily_brief,
    build_context_for_claude,
    append_learning
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
    """
    Veri topla, memory'yi güncelle, sıkıştırılmış bağlam hazırla.
    Tam JSON yerine özet → ~1500 token, 10x ucuz.
    """
    print(f"[Orkestratör] Veri toplanıyor... (mod: {mode})")

    # Ham veri çek
    portfolios = get_portfolio_snapshot()
    market     = get_market_context()
    swing      = get_swing_status()

    # L1 belleği güncelle (her çağrıda)
    state = build_portfolio_state(portfolios, market)
    save_portfolio_state(state)

    # Sıkıştırılmış bağlamı derle
    compressed = build_context_for_claude(mode)

    return {
        "mode":       mode,
        "timestamp":  datetime.now(TR_TZ).isoformat(),
        "compressed": compressed,   # Claude'a bu gider (~1500 token)
        "raw": {                    # Monitor modunda anlık kontrol için
            "portfolios": portfolios,
            "market":     market,
            "swing":      swing,
        }
    }

# ── Mod çalıştırıcıları ───────────────────────────────────────────────────────

def run_morning(ctx: dict):
    """Sabah analizi — piyasa açılmadan önce."""
    print("[Orkestratör] Sabah modu çalışıyor...")

    prompt = f"""
{ctx['compressed']}

=== GÖREV: SABAH ANALİZİ ===
1. Stop'a yakın pozisyon var mı? (stop_pct <= 3 olanları işaretle)
2. Piyasa rejimi: RISK_ON / NEUTRAL / RISK_OFF? Neden?
3. Bugün dikkat edilmesi gereken 1-2 şey
4. Swing watchlist'te güçlü setup var mı?
5. Önerdiğim 1-2 aksiyon (uygulama değil, öneri)

Kısa ve net yaz. Sonda: "Bugün gözüm şunlarda: ..."
KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan.
"""

    print("[Orkestratör] Claude API çağrılıyor...")
    response = get_claude_decision(prompt, mode="morning")
    print(f"[Orkestratör] Claude yanıtı ({len(response)} karakter):\n{response[:200]}")
    save_daily_brief(response, "morning")

    msg = f"Finzora Agent - Sabah Analizi\n{ctx['timestamp'][:16]}\n\n{response}"
    result = send_private_telegram(msg)
    print(f"[Orkestratör] Telegram sonucu: {result}")

def run_closing(ctx: dict):
    """Kapanış yorumu — piyasa kapandıktan sonra."""
    print("[Orkestratör] Kapanış modu çalışıyor...")

    prompt = f"""
{ctx['compressed']}

=== GÖREV: KAPANIS YORUMU ===
1. Bugün portföyde en dikkat çeken hareket neydi?
2. Stop seviyelerine tehlikeli yaklaşan var mı?
3. Tezler hâlâ geçerli mi? Bozan bir gelişme var mı?
4. Yarın için en önemli 3 izleme noktası
5. Bu kapanıştan çıkan 1 ders (learning_log için)

Kısa ve net. KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan.
"""

    response = get_claude_decision(prompt, mode="closing")
    save_daily_brief(response, "closing")

    # Öğrenmeyi logla (son satırı yakala)
    lines = [l.strip() for l in response.split("\n") if l.strip()]
    if lines:
        append_learning(lines[-1], source="closing_analysis")

    msg = f"📊 *Finzora Agent — Kapanış*\n_{ctx['timestamp'][:16]}_\n\n{response}"
    send_private_telegram(msg)
    print("[Orkestratör] Kapanış yorumu gönderildi.")

def run_monitor(ctx: dict):
    """Seans içi izleme — sadece acil durumda mesaj atar."""
    print("[Orkestratör] İzleme modu çalışıyor...")

    portfolios = ctx["raw"]["portfolios"]
    market     = ctx["raw"]["market"]
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
{ctx['compressed']}

=== GÖREV: HAFTALIK DERİN ANALİZ ===
1. Bu haftanın portföy özeti: toplam getiri, en iyi/kötü pozisyon
2. Hangi K-kuralı bu hafta kritik rol oynadı?
3. Tezlerde değişen bir şey var mı? (AI supply chain, temettü, makro)
4. Gelecek hafta için 3 kritik izleme noktası
5. Bir kural veya filtre değişikliği öneriyor musun? (BACKTEST GEREKLİ etiketi ile)
6. Öğrenme özeti: Bu haftadan 2 somut ders

Detaylı Türkçe analiz. Spekülatif önerilere BACKTEST GEREKLİ işareti koy.
"""

    response = get_claude_decision(prompt, mode="weekly")
    save_daily_brief(response, "weekly")
    append_learning(f"Haftalık: {response[:200]}", source="weekly_analysis")

    msg = f"📅 *Finzora Agent — Haftalık*\n_{ctx['timestamp'][:16]}_\n\n{response}"
    send_private_telegram(msg)
    print("[Orkestratör] Haftalık analiz gönderildi.")

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
