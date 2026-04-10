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
from web_researcher import build_research_context
from twitter_monitor import build_twitter_context
from learning_engine import (
    build_weekly_learning_context,
    auto_extract_lessons,
    analyze_closed_trades,
    update_k_rule_stats,
)
from risk_engine import build_risk_context

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
    Sabah/kapanış: web + twitter da eklenir.
    İzleme: sadece portföy + piyasa (hızlı, ucuz).
    """
    print(f"[Orkestratör] Veri toplanıyor... (mod: {mode})")

    portfolios = get_portfolio_snapshot()
    market     = get_market_context()
    swing      = get_swing_status()

    # Portföydeki semboller
    symbols = []
    for pf in portfolios.values():
        for pos in pf.get("pozisyonlar", []):
            sym = pos.get("sembol") or pos.get("symbol")
            if sym:
                symbols.append(sym)

    # L1 belleği güncelle
    state = build_portfolio_state(portfolios, market)
    save_portfolio_state(state)

    # Sıkıştırılmış temel bağlam
    compressed = build_context_for_claude(mode)

    # Sabah ve kapanış: web + twitter + risk ekle
    research = ""
    twitter  = ""
    risk     = ""
    if mode in ("morning", "closing", "weekly"):
        research = build_research_context(symbols)
        try:
            twitter = build_twitter_context(symbols)
        except Exception as e:
            print(f"[Twitter] Hata: {e}")
            twitter = ""
        risk = build_risk_context(portfolios)

    return {
        "mode":       mode,
        "timestamp":  datetime.now(TR_TZ).isoformat(),
        "compressed": compressed,
        "research":   research,
        "twitter":    twitter,
        "risk":       risk,
        "raw": {
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

{ctx['research']}

{ctx['twitter']}

{ctx['risk']}

=== GÖREV: SABAH ANALİZİ ===
Yukarıdaki verileri değerlendirerek:
1. Stop'a yakın pozisyon var mı? Risk analizindeki stop uyarılarına bak
2. Earnings yaklaşan hisse var mı? K-05 uyarısı gerekiyor mu?
3. Makro takvimde bugün/bu hafta kritik olay var mı?
4. Konsantrasyon/korelasyon riski var mı? K-17 uyarısı?
5. Twitter'da portföyle ilgili önemli sinyal var mı? (SPEKÜLATİF etiketle)
6. Piyasa rejimi: RISK_ON / NEUTRAL / RISK_OFF?
7. Önerdiğim 1-2 aksiyon (uygulama değil, öneri)

Kısa ve net. KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan.
Sonda: "Bugün gözüm şunlarda: ..."
"""

    response = get_claude_decision(prompt, mode="morning")
    save_daily_brief(response, "morning")

    msg = f"Finzora Agent — Sabah Analizi\n{ctx['timestamp'][:16]}\n\n{response}"
    result = send_private_telegram(msg)
    print(f"[Orkestratör] Telegram sonucu: {result}")

def run_closing(ctx: dict):
    """Kapanış yorumu — piyasa kapandıktan sonra."""
    print("[Orkestratör] Kapanış modu çalışıyor...")

    prompt = f"""
{ctx['compressed']}

{ctx['research']}

{ctx['twitter']}

=== GÖREV: KAPANIS YORUMU ===
1. Bugün portföyde en dikkat çeken hareket neydi?
2. Stop seviyelerine tehlikeli yaklaşan var mı?
3. Tezler hâlâ geçerli mi? Bugünkü haberler bir şeyi değiştiriyor mu?
4. Twitter'da önemli bir sinyal gördün mü? (SPEKÜLATİF etiketle)
5. Yarın için en önemli 3 izleme noktası
6. Bu günden 1 somut ders

Kısa ve net. KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan.
"""

    response = get_claude_decision(prompt, mode="closing")
    save_daily_brief(response, "closing")
    lines = [l.strip() for l in response.split("\n") if l.strip()]
    if lines:
        append_learning(lines[-1], source="closing_analysis")

    msg = f"Finzora Agent — Kapanış\n{ctx['timestamp'][:16]}\n\n{response}"
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

    # VIX yüksekse uyar (gerçek CBOE VIX)
    vix_data  = market.get("VIX", {})
    vix_price = vix_data.get("price")
    vix_seviye = vix_data.get("seviye", "")
    if vix_price and float(vix_price) > 25:
        alerts.append(
            f"🔴 VIX YÜKSEK: {vix_price} — {vix_seviye}"
        )

    # Sadece alert varsa mesaj gönder (Claude'u meşgul etme)
    if alerts:
        msg = "🔔 *Finzora Agent — Seans Uyarısı*\n\n" + "\n\n".join(alerts)
        send_private_telegram(msg)
        print(f"[Orkestratör] {len(alerts)} uyarı gönderildi.")
    else:
        print("[Orkestratör] İzleme tamamlandı, uyarı yok.")

def run_weekly(ctx: dict):
    """Pazar günü haftalık derin analiz + öğrenme döngüsü."""
    print("[Orkestratör] Haftalık mod çalışıyor...")

    learning_ctx = build_weekly_learning_context()
    trade_stats  = analyze_closed_trades(days_back=7)
    update_k_rule_stats(trade_stats)

    prompt = f"""
{ctx['compressed']}

{ctx['research']}

{ctx['risk']}

{learning_ctx}

=== GÖREV: HAFTALIK DERİN ANALİZ + ÖĞRENME ===
1. Bu haftanın portföy özeti: en iyi/kötü pozisyon, genel performans
2. Risk analizi: konsantrasyon, korelasyon, drawdown durumu
3. Hangi K-kuralı bu hafta kritik rol oynadı?
4. Trade istatistiklerine göre: win rate, ort P/L, hangi yöntem daha iyi?
5. Tezlerde değişen bir şey var mı?
6. Gelecek hafta için 3 kritik izleme noktası
7. Kural/filtre değişikliği önerisi varsa: BACKTEST GEREKLİ — [değişiklik]
8. Bu haftadan 2 somut ders

Detaylı Türkçe analiz. Spekülatif önerilere BACKTEST GEREKLİ işareti koy.
"""

    response = get_claude_decision(prompt, mode="weekly")
    save_daily_brief(response, "weekly")
    auto_extract_lessons(response, "weekly")

    msg = f"Finzora Agent — Haftalık Analiz\n{ctx['timestamp'][:16]}\n\n{response}"
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
