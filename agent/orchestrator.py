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
from backtester import run_full_backtest, format_backtest_for_claude
from rule_updater import run_weekly_rule_review, get_applied_changes_summary
from dry_run_manager import run_dry_run_check
from trade_feedback import run_auto_feedback
from screener_optimizer import run_screener_optimization
from darwin_evolution import (
    run_evolution_cycle,
    evaluate_evolution_results,
    get_evolution_summary,
    get_weighted_genome_context,
    load_genome,
)
from regime_detector import run_regime_detection, get_regime_context
from prediction_logger import (
    log_prediction,
    score_pending_predictions,
    get_prediction_context,
)
from specialist_agents import (
    run_multi_agent_analysis,
    format_multi_agent_for_telegram,
    load_specialist_genome,
    update_specialist_weights,
)
from adversarial_debate import run_debate, format_debate_for_telegram
from multi_cohort import (
    run_janus_detection,
    detect_blind_spots,
    run_weekly_blind_spot_analysis,
    get_cohort_context,
    propose_new_specialist,
)
from swing_manager import run_swing_morning_check, get_swing_report
from premarket_gap_scanner import scan_premarket_gaps, get_premarket_context

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

# ── Alpha Scan Bağlamı ────────────────────────────────────────────────────────

def _load_alpha_scan_context() -> str:
    """
    Alpha screener sonuçlarını okur ve Claude için özet hazırlar.
    data/alpha_scan_growth.json → sabah analizine girer.
    """
    import json
    from pathlib import Path

    scan_path = Path(__file__).parent.parent / "data" / "alpha_scan_growth.json"
    if not scan_path.exists():
        return ""

    try:
        with open(scan_path, encoding="utf-8") as f:
            scan = json.load(f)

        tarih  = scan.get("tarih", "")[:10]
        ekle   = scan.get("ekle", [])
        izle   = scan.get("izle", [])[:5]

        lines = [f"=== ALPHA SCREENER ({tarih}) ==="]

        if ekle:
            lines.append(f"EKLE ({len(ekle)}):")
            for h in ekle[:5]:
                sym    = h.get("symbol", "")
                sc     = h.get("score", 0)
                ins    = h.get("insider_alpha_score", 0) or h.get("insider_score", 0)
                sektor = h.get("sector", "")[:18]
                ins_tag = " 🔑INS" if ins > 0 else ""
                lines.append(f"  {sym:6} skor:{sc:3} {sektor}{ins_tag}")

        if izle:
            lines.append(f"İZLE ({len(izle)}):")
            for h in izle[:5]:
                sym    = h.get("symbol", "")
                sc     = h.get("score", 0)
                sektor = h.get("sector", "")[:18]
                lines.append(f"  {sym:6} skor:{sc:3} {sektor}")

        return "\n".join(lines)
    except Exception:
        return ""


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

    # Rejim tespiti (VIX'ten al)
    vix_price = market.get("VIX", {}).get("price")
    regime    = run_regime_detection(market=market, vix=vix_price)

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

    # Bekleyen tahminleri skorla (her sabah)
    scored = score_pending_predictions()
    if scored:
        print(f"[Orkestratör] {len(scored)} tahmin skorlandı.")

    # Gece kapanan trade'leri kontrol et
    run_auto_feedback(ctx["raw"]["portfolios"])

    tahmin_ctx  = get_prediction_context()
    agirlik_ctx = get_weighted_genome_context(load_genome())

    # Alpha screener sonuçları (dünkü tarama)
    alpha_ctx = _load_alpha_scan_context()

    # Swing sabah kontrolü
    swing_check = run_swing_morning_check()
    swing_ctx   = swing_check["rapor"]

    # Pre-market gap taraması
    try:
        scan_premarket_gaps(min_gap_pct=2.5)
    except Exception as e:
        print(f"[Orkestratör] Pre-market scan hatası: {e}")
    premarket_ctx = get_premarket_context()
    swing_ctx   = swing_check["rapor"]
    swing_uyari = ""
    if swing_check["uyarilar"]:
        swing_uyari = "⚠️ SWING UYARI:\n" + "\n".join(u["mesaj"] for u in swing_check["uyarilar"])
    if swing_check["entry_signals"] and swing_check["bos_slot"] > 0:
        sigs = ", ".join(swing_check["entry_signals"][:3])
        swing_uyari += f"\n🎯 Swing giriş sinyali ({swing_check['bos_slot']} boş slot): {sigs}"

    # Multi-agent analiz çalıştır
    print("[Orkestratör] Multi-agent analiz başlıyor...")
    multi_result = run_multi_agent_analysis(
        compressed_ctx = ctx['compressed'],
        market_data    = ctx['research'],
        risk_data      = ctx['risk'],
        portfolio_ctx  = get_regime_context(),
    )
    multi_summary = format_multi_agent_for_telegram(multi_result)

    # Adversarial Debate — CIO kararı tartışmalıysa
    cio_karar   = multi_result.get("cio", {})
    debate_msg  = ""
    if cio_karar.get("guven") in ("LOW", "MEDIUM") or cio_karar.get("karar") in ("ACIL_CIK", "SAT"):
        print("[Orkestratör] Tartışmalı karar — debate başlıyor...")
        debate_result = run_debate(
            symbol     = cio_karar.get("hedef_sembol", "SPY"),
            context    = ctx['compressed'],
            initial_decision = cio_karar,
            portfolio_data   = ctx['risk'],
        )
        debate_msg = "\n\n" + format_debate_for_telegram(debate_result)

    # JANUS cohort güncelle
    janus_ctx = get_cohort_context()

    # Uzman ağırlıklarını güncelle
    s_genome = load_specialist_genome()
    update_specialist_weights(s_genome, [])

    prompt = f"""
{ctx['compressed']}

{get_regime_context()}

{janus_ctx}

{agirlik_ctx}

{tahmin_ctx}

{alpha_ctx}

{premarket_ctx}

{swing_ctx}
{swing_uyari}

{ctx['research']}

{ctx['twitter']}

{ctx['risk']}

=== GÖREV: SABAH ANALİZİ ===
Multi-agent ve debate sonuçları Telegram'a ayrıca gönderildi.

1. Pre-market gap'lerde portfolyo pozisyonları var mı? Aksiyon gerekiyor mu?
2. Stop'a yakın pozisyon? (portföy + swing)
3. Swing giriş sinyali + boş slot → GİRİŞ KARARI (SEN KARAR VER)
   Format: SWING_GİRİŞ: [SEMBOL] [ADET] adet @ ~$[FİYAT] stop:$[STOP] hedef:$[HEDEF]
4. Alpha screener fırsatı?
5. Bu haftanın 3 önceliği

Kısa ve net. KESİN / MUHTEMEL / SPEKÜLATİF.
"""

    response = get_claude_decision(prompt, mode="morning")
    save_daily_brief(response, "morning")

    # Telegram'a 3 mesaj: multi-agent + debate (varsa) + genel analiz
    send_private_telegram(multi_summary + debate_msg)
    msg    = f"Finzora Agent — Sabah Analizi\n{ctx['timestamp'][:16]}\n\n{response}"
    result = send_private_telegram(msg)
    print(f"[Orkestratör] Telegram sonucu: {result}")

def run_closing(ctx: dict):
    """Kapanış yorumu — piyasa kapandıktan sonra."""
    print("[Orkestratör] Kapanış modu çalışıyor...")

    # Swing değişikliği varsa git'e kaydet
    flag = REPO_ROOT / "data" / ".swing_updated"
    if flag.exists():
        _commit_swing_changes()
        flag.unlink()

    # Swing günlük özeti
    from swing_manager import get_swing_report
    swing_ozet = get_swing_report()

    prompt = f"""
{ctx['compressed']}

{swing_ozet}

{ctx['research']}

{ctx['twitter']}

=== GÖREV: KAPANIS YORUMU ===
1. Bugünkü swing aksiyonları (varsa) doğru muydu? Neden?
2. Portföyde en dikkat çeken hareket neydi?
3. Stop seviyelerine tehlikeli yaklaşan var mı?
4. Tezler hâlâ geçerli mi?
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


def _commit_swing_changes():
    """Swing JSON değişikliklerini git'e commit eder."""
    import subprocess
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name", "Finzora Agent"], capture_output=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add",
                        "data/swing/active.json",
                        "data/swing/closed.json",
                        "data/transactions.csv"], capture_output=True)
        msg = f"🔄 [Swing] Otomatik işlem kaydı — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        result = subprocess.run(["git", "commit", "-m", msg], capture_output=True)
        if result.returncode == 0:
            subprocess.run(["git", "push"], capture_output=True)
            print("[Swing] Git commit başarılı")
    except Exception as e:
        print(f"[Swing] Git commit hatası: {e}")

def run_monitor(ctx: dict):
    """
    Seans içi otonom yönetim — her 30 dakikada çalışır.
    
    KARAR VERİR VE KAYDEDERIn:
    1. Swing giriş: sinyal + uygun fiyat → JSON yaz + Telegram'a "ALIN"
    2. Swing çıkış: stop/hedef tetiklendi → JSON yaz + Telegram'a "SATIN"
    3. Portföy stop: yakın ise uyarı, tetiklenince karar
    4. VIX spike: acil koruma
    
    SEN KARAR VER kuralı — onay beklemez.
    """
    print("[Orkestratör] Seans içi otonom yönetim çalışıyor...")

    portfolios = ctx["raw"]["portfolios"]
    market     = ctx["raw"]["market"]
    now_tr     = datetime.now(pytz.timezone("Europe/Istanbul"))
    saat       = now_tr.strftime("%H:%M")

    aksiyonlar = []  # Bu sefer yapılan işlemler
    uyarilar   = []  # Acil bildirimler

    # ── 1. SWING ÇIKIŞ KONTROL (Önce çıkışlar) ───────────────────────────────
    swing_exits = _check_swing_exits(market)
    aksiyonlar.extend(swing_exits)

    # ── 2. SWING GİRİŞ KONTROL (Boş slot varsa) ──────────────────────────────
    swing_entries = _check_swing_entries()
    aksiyonlar.extend(swing_entries)

    # ── 3. PORTFÖY STOP KONTROL ───────────────────────────────────────────────
    for pf_name, pf_data in portfolios.items():
        for pos in pf_data.get("pozisyonlar", []):
            symbol    = pos.get("sembol", "?")
            stop      = pos.get("stop_loss")
            cur_price = pos.get("guncel_fiyat") or pos.get("son_fiyat")

            if not stop or not cur_price:
                continue

            try:
                stop      = float(stop)
                cur_price = float(cur_price)
                pct       = (cur_price - stop) / stop * 100

                if cur_price <= stop:
                    # STOP TETİKLENDİ
                    uyarilar.append(
                        f"🔴 *STOP TETİKLENDİ* [{pf_name.upper()}]\n"
                        f"{symbol}: ${cur_price:.2f} ≤ Stop ${stop:.2f}\n"
                        f"→ SATIN — K-07 gereği"
                    )
                elif pct <= 2.0:
                    uyarilar.append(
                        f"⚠️ *STOP YAKINI* [{pf_name.upper()}]\n"
                        f"{symbol}: ${cur_price:.2f} — Stop ${stop:.2f} (%{pct:.1f} uzakta)"
                    )
            except (ValueError, TypeError):
                continue

    # ── 4. VIX SPIKE ──────────────────────────────────────────────────────────
    vix_price = market.get("VIX", {}).get("price")
    if vix_price and float(vix_price) > 28:
        uyarilar.append(
            f"🔴 VIX YÜKSEK: {vix_price} — K-13 aktif, yeni giriş yapma"
        )

    # ── 5. TELEGRAMIn ─────────────────────────────────────────────────────────
    # Aksiyonlar (yapılan işlemler)
    if aksiyonlar:
        msg = f"🤖 *Finzora Agent — Seans Aksiyonu* ({saat})\n\n"
        msg += "\n\n".join(aksiyonlar)
        send_private_telegram(msg)
        print(f"[Orkestratör] {len(aksiyonlar)} aksiyon alındı.")

    # Uyarılar (acil bildirimler)
    if uyarilar:
        msg = f"🔔 *Finzora Agent — Uyarı* ({saat})\n\n"
        msg += "\n\n".join(uyarilar)
        send_private_telegram(msg)
        print(f"[Orkestratör] {len(uyarilar)} uyarı gönderildi.")

    if not aksiyonlar and not uyarilar:
        print("[Orkestratör] İzleme tamamlandı, aksiyon yok.")


def _check_swing_exits(market: dict) -> list[str]:
    """
    Aktif swing pozisyonlarında çıkış koşullarını kontrol et.
    Stop veya hedef tetiklendiyse JSON'a yaz + aksiyon mesajı döndür.
    """
    import sys as _sys
    _sys.path.insert(0, str(REPO_ROOT / "agent"))

    from swing_manager import update_swing_positions

    aksiyonlar = []

    # Swing manager çalıştır — stop/hedef kontrolü yapar
    uyarilar = update_swing_positions()

    for u in uyarilar:
        tip = u.get("tip", "")
        if tip == "STOP_YAKIN":
            aksiyonlar.append(
                f"⚠️ {u['mesaj']}\n→ Stop seviyesini takip et"
            )
        elif tip == "K11_AKTIF":
            aksiyonlar.append(
                f"💰 {u['mesaj']}\n→ K-11: %25-30 kısmi satış düşün"
            )

    # Kapatılan pozisyonlar (swing_manager kapattı, biz bildirelim)
    closed_path = REPO_ROOT / "data" / "swing" / "closed.json"
    if closed_path.exists():
        closed = json.load(open(closed_path))
        kapalilar = closed.get("kapali_pozisyonlar", [])
        # Bugün kapananları bul
        bugun = datetime.now().strftime("%Y-%m-%d")
        bugun_kapali = [k for k in kapalilar if k.get("cikis_tarihi") == bugun]
        for k in bugun_kapali[-3:]:  # Son 3
            pnl  = k.get("pnl_pct", 0)
            icon = "✅" if pnl > 0 else "❌"
            aksiyonlar.append(
                f"{icon} *SWING KAPANDI*: {k['sembol']}\n"
                f"Neden: {k.get('cikis_nedeni','?')} | P/L: {pnl:+.1f}%\n"
                f"→ {k.get('adet','?')} adet SATIN"
            )

    return aksiyonlar


def _check_swing_entries() -> list[str]:
    """
    Swing giriş sinyallerini kontrol et.
    Uygun koşul varsa JSON'a yaz + aksiyon mesajı döndür.
    """
    import sys as _sys
    _sys.path.insert(0, str(REPO_ROOT / "scripts"))

    aksiyonlar = []

    # Kapasite kontrol
    active = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
    mevcut_poz = len(active.get("aktif_pozisyonlar", []))
    if mevcut_poz >= 5:
        return []  # Dolu

    # Dün kaydedilen entry sinyallerini yükle
    sig_path = REPO_ROOT / "data" / "swing_entry_signals.json"
    if not sig_path.exists():
        return []

    sig_data = json.load(open(sig_path))
    giris_syms = sig_data.get("giris_sinyalleri", [])

    if not giris_syms:
        return []

    # Her sinyal için canlı analiz yap
    try:
        from swing_entry_engine import enhanced_entry_analysis
        from swing_manager import open_swing_position
    except ImportError:
        return []

    for sym in giris_syms[:3]:  # Max 3 kontrol
        # Kapasite yeterliyse devam
        if mevcut_poz >= 5:
            break

        # Zaten açık mı?
        if any(p.get("sembol") == sym for p in active.get("aktif_pozisyonlar", [])):
            continue

        # Canlı analiz
        try:
            r = enhanced_entry_analysis(sym)
        except Exception:
            continue

        if "GİRİŞ ✅" not in r.get("karar", ""):
            continue

        # GİRİŞ KARARI — Kaydedelim
        sinyaller = r.get("sinyaller", [])
        shares    = r.get("shares", 0)
        price     = r.get("price", 0)
        stop      = r.get("stop", 0)
        target    = r.get("target", 0)
        sinyal_str = ", ".join(s.get("tip","") for s in sinyaller)

        if not shares or not price or not stop:
            continue

        # JSON'a yaz
        result = open_swing_position(
            symbol    = sym,
            shares    = shares,
            price     = price,
            stop      = stop,
            target    = target,
            sinyaller = sinyaller,
            reasoning = f"Seans içi otomatik giriş — {sinyal_str}",
        )

        if result:
            mevcut_poz += 1
            aksiyonlar.append(
                f"🟢 *SWING GİRİŞ KAYIT*: {sym}\n"
                f"Sinyal: {sinyal_str}\n"
                f"→ *ALIN: {shares} adet @ ~${price:.2f}*\n"
                f"Stop: ${stop:.2f} | Hedef: ${target:.2f} | R:R 2.5:1"
            )

            # Git commit için işaret bırak
            _flag_for_commit()

    return aksiyonlar


def _flag_for_commit():
    """Swing değişikliği oldu — kapanışta commit edilecek."""
    flag = REPO_ROOT / "data" / ".swing_updated"
    flag.write_text(datetime.now().isoformat())

def run_weekly(ctx: dict):
    """Pazar günü haftalık derin analiz + öğrenme + Darwin evrimi."""
    print("[Orkestratör] Haftalık mod çalışıyor...")

    learning_ctx  = build_weekly_learning_context()
    trade_stats   = analyze_closed_trades(days_back=7)
    update_k_rule_stats(trade_stats)
    backtest      = run_full_backtest()
    backtest_ctx  = format_backtest_for_claude(backtest)
    applied_log   = get_applied_changes_summary()
    screener_rpt  = run_screener_optimization()

    # Darwin + Cohort + Blind Spot
    evo_results   = evaluate_evolution_results()
    evo_cycle     = run_evolution_cycle(force=False)
    evo_summary   = get_evolution_summary()
    blind_rpt     = run_weekly_blind_spot_analysis()

    # Blind spot varsa yeni agent öner
    spots = detect_blind_spots()
    for spot in spots[:1]:  # Haftalık max 1 yeni agent önerisi
        propose_new_specialist(spot)

    # Dry-run kontrolü
    dry_run_rpt   = run_dry_run_check(backtest)

    prompt = f"""
{ctx['compressed']}

{ctx['research']}

{ctx['risk']}

{learning_ctx}

{backtest_ctx}

{screener_rpt}

Son uygulanan değişiklikler:
{applied_log}

Darwin Evrim Durumu:
{evo_summary}

Blind Spot + JANUS Analizi:
{blind_rpt}

Dry-run değerlendirmesi:
{dry_run_rpt}

=== GÖREV: HAFTALIK DERİN ANALİZ + ÖĞRENME ===
1. Portföy özeti: en iyi/kötü pozisyon, genel performans
2. Risk: konsantrasyon, korelasyon, drawdown
3. Hangi K-kuralı bu hafta kritik rol oynadı?
4. JANUS: Yeni rejim mi tarihi rejim mi? Bu stratejiyi nasıl etkiler?
5. Darwin evrim sonuçları: Hangi kural güçlendi, hangisi zayıfladı?
6. Blind spot: Sistemin neyi görmediğini bulduk mu? Yeni agent gerekiyor mu?
7. Gelecek hafta için 3 kritik izleme noktası
8. Bu haftadan 2 somut ders

Detaylı Türkçe analiz. Spekülatif önerilere BACKTEST GEREKLİ işareti koy.
"""

    response = get_claude_decision(prompt, mode="weekly")
    save_daily_brief(response, "weekly")
    auto_extract_lessons(response, "weekly")

    # Önerileri kuyruğa ekle
    proposals = run_weekly_rule_review(response, backtest)
    if proposals:
        onay_beklenti = [p for p in proposals if p["durum"] == "ONAY_BEKLIYOR"]
        reddedilen    = [p for p in proposals if p["durum"] == "REDDEDILDI"]
        print(f"[Orkestratör] {len(onay_beklenti)} öneri kuyruğa eklendi, {len(reddedilen)} reddedildi.")

    msg = f"Finzora Agent — Haftalık Analiz\n{ctx['timestamp'][:16]}\n\n{response}"
    if proposals:
        msg += f"\n\n--- KURAL ÖNERİLERİ ---"
        for p in proposals:
            msg += f"\n{p['durum']}: {p['param']} = {p['new_value']} ({p['gerekce'][:60]})"
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
