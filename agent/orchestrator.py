#!/usr/bin/env python3
"""
Finzora Agent — Orkestratör
============================
Otonom karar verir ve uygular.
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

# Olay kaydı
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
try:
    from event_logger import log as _log
    _log.kaynak = "orchestrator"
except ImportError:
    class _FallbackLog:
        kaynak = "orchestrator"
        def __getattr__(self, n):
            return lambda *a, **kw: None
    _log = _FallbackLog()

# Agent modülleri
sys.path.insert(0, str(Path(__file__).parent))
from claude_agent import get_claude_decision
from tools import (
    get_portfolio_snapshot,
    get_market_context,
    get_swing_status,
    get_watchlist,
    send_private_telegram,
    send_group_telegram,
    get_rsi_batch,
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
try:
    from macro_intelligence import run_macro_intelligence
    from opportunity_finder import find_candidates
    from execution_engine import (
        buy_position, sell_position, deploy_cash,
        get_portfolio_status
    )
except ImportError as _ie:
    print(f"[Orchestrator] Modül yüklenemedi: {_ie}")
    run_macro_intelligence = find_candidates = None
    buy_position = sell_position = deploy_cash = None
    get_portfolio_status = None

try:
    from k_engine import run_entry_checks, run_exit_checks
except ImportError:
    run_entry_checks = run_exit_checks = None
from premarket_gap_scanner import scan_premarket_gaps, get_premarket_context
try:
    from conviction_scorer import batch_score as conviction_batch_score
    from tema_portfolio_tracker import tag_trade_with_theme, run as run_tema_matrix
except ImportError as _ie2:
    print(f"[Orchestrator] Yeni modül yüklenemedi: {_ie2}")
    conviction_batch_score = None
    tag_trade_with_theme = None
    run_tema_matrix = None

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

    scan_path = Path(__file__).parent.parent / "data" / "alpha_scan_aggressive.json"
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

    # Sabah ve kapanış: web + twitter + risk + portföy haberleri ekle
    research      = ""
    twitter       = ""
    risk          = ""
    portfolio_news = ""
    if mode in ("morning", "closing", "weekly"):
        research = build_research_context(symbols)
        try:
            twitter = build_twitter_context(symbols)
        except Exception as e:
            print(f"[Twitter] Hata: {e}")
            twitter = ""
        risk = build_risk_context(portfolios)
        # Portföy hisseleri için son 24s FMP haberleri
        try:
            from tools import get_portfolio_news
            portfolio_news = get_portfolio_news(saat=24)
        except Exception as e:
            print(f"[PortföyNews] Hata: {e}")
            portfolio_news = ""
    elif mode == "monitor":
        # İzleme modunda da son 4s haber — stop/çıkış kararlarında bağlam
        try:
            from tools import get_portfolio_news
            portfolio_news = get_portfolio_news(saat=4)
        except Exception as e:
            portfolio_news = ""

    return {
        "mode":           mode,
        "timestamp":      datetime.now(TR_TZ).isoformat(),
        "compressed":     compressed,
        "research":       research,
        "twitter":        twitter,
        "risk":           risk,
        "portfolio_news": portfolio_news,
        "raw": {
            "portfolios": portfolios,
            "market":     market,
            "swing":      swing,
        }
    }

# ── Mod çalıştırıcıları ───────────────────────────────────────────────────────

# ── Session State Yardımcısı ───────────────────────────────────────────────────

def _update_session_state(key: str, value) -> None:
    """data/session_state.json'ı günceller — FAZ handoff için."""
    state_path = REPO_ROOT / "data" / "session_state.json"
    try:
        state = json.load(open(state_path)) if state_path.exists() else {}
    except Exception:
        state = {}
    state[key]        = value
    state["timestamp"] = datetime.now(TR_TZ).isoformat()
    try:
        json.dump(state, open(state_path, "w"), ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SessionState] Yazma hatası: {e}")


def run_morning(ctx: dict):
    """
    Sabah analizi — piyasa açılmadan önce (UTC 13:00 = TR 16:00).
    1. Makro zeka: temalar, sektör rotasyonu, hikaye tespiti
    2. Fırsat taraması: temalara uygun hisse adayları + puanlama
    3. Buy list oluştur (seans açılışında hazır olsun)
    4. Sabah raporu yaz + git push + Telegram
    """
    print("[Orkestratör] Sabah modu çalışıyor...")

    # ── MAKRO ZİYASAL ZEKA ──────────────────────────────────────────────────
    macro_ctx = {}
    buy_candidates = []

    if run_macro_intelligence:
        try:
            print("[Sabah] Makro tema analizi...")
            # VIX al
            import requests as _req
            try:
                vix_r = _req.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
                                  headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                vix = float(vix_r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"])
            except Exception:
                vix = 20.0

            macro_ctx = run_macro_intelligence(vix=vix)

            # Fırsat taraması
            temalar = macro_ctx.get("dominant_temalar", [])
            if temalar and find_candidates:
                print(f"[Sabah] {len(temalar)} tema için hisse aranıyor...")
                # Tüm portföylerdeki mevcut sembolleri topla
                all_syms = []
                for pf in ["aggressive","balanced","dividend"]:
                    try:
                        pf_data = get_portfolio_status(pf) if get_portfolio_status else {}
                        all_syms.extend(pf_data.get("semboller", []))
                    except Exception:
                        pass

                buy_candidates = find_candidates(temalar, vix=vix,
                                                  mevcut_pozisyonlar=all_syms)
                print(f"[Sabah] {len(buy_candidates)} alım adayı hazır")
        except Exception as e:
            print(f"[Sabah] Makro zeka hatası: {e}")

    # Buy list'i session state'e yaz (monitor okuyacak)
    _update_session_state("buy_list", {
        "tarih":      datetime.now(TR_TZ).isoformat(),
        "adaylar":    buy_candidates[:10],
        "vix":        macro_ctx.get("vix", 20),
        "piyasa_mod": macro_ctx.get("piyasa_modu", "nötr"),
    })


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

    # Adversarial Debate — genişletildi (11 Nisan 2026)
    # Eski: sadece LOW güven veya SAT kararında
    # Yeni: BUY kararları dahil tüm önemli kararlar tartışılır
    cio_karar     = multi_result.get("cio", {})
    cio_karar_tip = cio_karar.get("karar", "")
    debate_msg    = ""
    debate_tetik  = (
        cio_karar.get("guven") in ("LOW", "MEDIUM") or
        cio_karar_tip in ("ACIL_CIK", "SAT", "KISMI_CIK", "AL", "KISMI_EKLE")
    )
    if debate_tetik:
        print(f"[Orkestratör] {cio_karar_tip} kararı için debate başlıyor...")
        debate_result = run_debate(
            symbol           = cio_karar.get("hedef_sembol", "SPY"),
            context          = ctx['compressed'],
            initial_decision = cio_karar,
            portfolio_data   = ctx['risk'],
        )
        debate_msg = "\n\n" + format_debate_for_telegram(debate_result)

    # JANUS cohort güncelle
    janus_ctx = get_cohort_context()

    # Uzman ağırlıklarını güncelle
    s_genome = load_specialist_genome()
    update_specialist_weights(s_genome, [])

    genome_ctx = _load_genome_context()

    # Tarih/gün bilgisini açıkça inject et
    # Kapanış gece yarısından sonra çalışır (UTC 21:30 = TR 00:30) — seans günü = önceki gün
    _now_tr  = datetime.now(TR_TZ)
    from datetime import timedelta as _td
    _seans_gun = _now_tr - _td(days=1) if _now_tr.hour < 6 else _now_tr
    _gunler  = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    _bugun_tarih = _seans_gun.strftime("%d %B %Y")
    _bugun_gun   = _gunler[_seans_gun.weekday()]
    _bugun_saat  = _now_tr.strftime("%H:%M")
    _piyasa_durumu = (
        "KAPALI (hafta sonu)" if _now_tr.weekday() >= 5
        else "AÇILIŞ ÖNCESİ" if _now_tr.hour < 16 or (_now_tr.hour == 16 and _now_tr.minute < 30)
        else "SEANS İÇİ" if _now_tr.hour < 23
        else "KAPANDI"
    )

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

{ctx['portfolio_news']}

{genome_ctx}

=== GÖREV: SABAH ANALİZİ VE RAPOR ===
BUGÜNÜN TARİHİ: {_bugun_tarih}
BUGÜNÜN GÜNÜ: {_bugun_gun}
ŞUAN SAAT: {_bugun_saat} TR
NYSE PAZARI: {_piyasa_durumu}

Yukarıdaki gerçek piyasa verileri, portföy durumu ve teknik analizleri kullanarak
docs/prompts/DAILY_PART1_SABAH.md formatında eksiksiz sabah raporu üret.
Rapor başlığında tarih ve gün bilgisini YUKARIDAN al — kendi tahminini kullanma.

Zorunlu bölümler (hepsini yaz):
0. piyasa istihbaratı (aktif temalar, haber etki zinciri)
0.5. dün seans sonu notları (session_state flag'leri)
1. piyasa görünümü (endeks tablosu, ön piyasa, sektörler, VIX/K-13)
2. haber ve analiz (portföyü etkileyen gelişmeler, analist notları)
3. portföy sağlık durumu (3 portföy tablo, uyarılar, earnings takvimi)
4. günün planı (aksiyonlar: hemen / izle / pasif)

Swing giriş kararı varsa: SWING_GİRİŞ: [SEMBOL] [ADET] adet @ ~$[FİYAT] stop:$[STOP] hedef:$[HEDEF]

FAZ_2 giriş penceresi: 17:30-21:00 TR (FAZ_1 = 16:30-17:30 TR, giriş yok)

TABLO YORUMLAMA KURALLARI (Kesin olarak uygula):
- Stop% sütunu = fiyattan stop seviyesine uzaklık. DÜŞÜK = tehlikeli.
- ⚠️ Stop% < 4 → tabloda görünür, uyarı olarak belirt.
- Bugün sütunu = o günkü hareket. P/L sütunu = giriş fiyatından toplam getiri. İKİSİNİ KARIŞTIRAMA.
- K-05 earnings uyarısı: YENI GİRİŞ yasağı. Mevcut açık pozisyon K-05'ten ETKİLENMEZ, tutulabilir.
- K-17: Aynı GÜNDE aynı sektörden YENI GİRİŞ yasağı. Portföyde mevcut tech pozisyonu K-17 tetiklemez.
- Senaryo testinde listelenen semboller stop tetiklenenlerdir — fiyat ve stop seviyesi verilmiştir, kullan.

KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan. Küçük harf Türkçe.
"""

    response = get_claude_decision(prompt, mode="morning")
    save_daily_brief(response, "morning")

    # Tam raporu reports/daily/'e kaydet
    _save_report(response, "SABAH")

    # Telegram'a 3 mesaj: multi-agent + debate (varsa) + genel analiz
    send_private_telegram(multi_summary + debate_msg)
    msg    = f"Finzora Agent — Sabah Analizi\n{ctx['timestamp'][:16]}\n\n{response}"
    result = send_private_telegram(msg)
    print(f"[Orkestratör] Telegram sonucu: {result}")

def run_closing(ctx: dict):
    """Kapanış yorumu — piyasa kapandıktan sonra."""
    print("[Orkestratör] Kapanış modu çalışıyor...")

    # Fiyat + ATR stop güncellemesi — daily_update.py mekanik hesabı
    # daily_update.yml silindi, bu görevi orchestrator closing üstlendi
    import subprocess as _sp
    _du = REPO_ROOT / "scripts" / "daily_update.py"
    if _du.exists():
        print("[Orkestratör] Fiyat + stop güncellemesi başlatılıyor...")
        _sp.run(["python3", str(_du)], timeout=180, env=os.environ.copy())

    # Swing flag'ini temizle (workflow zaten commit ediyor)
    flag = REPO_ROOT / "data" / ".swing_updated"
    if flag.exists():
        flag.unlink()

    # Swing günlük özeti
    from swing_manager import get_swing_report
    swing_ozet = get_swing_report()

    genome_ctx = _load_genome_context()

    # Tarih/gün bilgisini açıkça inject et
    # Kapanış gece yarısından sonra çalışır (UTC 21:30 = TR 00:30) — seans günü = önceki gün
    _now_tr  = datetime.now(TR_TZ)
    from datetime import timedelta as _td
    _seans_gun = _now_tr - _td(days=1) if _now_tr.hour < 6 else _now_tr
    _gunler  = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    _bugun_tarih = _seans_gun.strftime("%d %B %Y")
    _bugun_gun   = _gunler[_seans_gun.weekday()]
    _bugun_saat  = _now_tr.strftime("%H:%M")
    _piyasa_durumu = (
        "KAPALI (hafta sonu)" if _now_tr.weekday() >= 5
        else "AÇILIŞ ÖNCESİ" if _now_tr.hour < 16 or (_now_tr.hour == 16 and _now_tr.minute < 30)
        else "SEANS İÇİ" if _now_tr.hour < 23
        else "KAPANDI"
    )

    prompt = f"""
{ctx['compressed']}

{swing_ozet}

{ctx['research']}

{ctx['twitter']}

{ctx['portfolio_news']}

{genome_ctx}

=== GÖREV: KAPANIS RAPORU ===
BUGÜNÜN TARİHİ: {_bugun_tarih}
BUGÜNÜN GÜNÜ: {_bugun_gun}

Yukarıdaki verilerle docs/prompts/DAILY_PART2_CLOSING.md formatında kapanış raporu üret.
Rapor başlığında tarih ve gün bilgisini YUKARIDAN al.

Zorunlu bölümler:
1. günün özeti (endeks tablosu, sektörler, trend)
2. portföy takibi (3 portföy tablo, uyarılar, aksiyonlar)
3. swing trade durumu (chandelier stop kontrolü)
4. kazanç açıklamaları (portföy/watchlist kesişimi)
5. günün değerlendirmesi (sabah planı vs gerçekleşme, dersler)
6. yarın aksiyonları (hemen / izle / pasif)

JSON güncellemeleri (fiyat/k-z) zaten yapılıyor, rapor bölümlerine yansıt.
Kapanan trade varsa post-trade review ekle.
KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan. Küçük harf Türkçe.
"""

    response = get_claude_decision(prompt, mode="closing")
    save_daily_brief(response, "closing")
    lines = [l.strip() for l in response.split("\n") if l.strip()]
    if lines:
        append_learning(lines[-1], source="closing_analysis")

    # Tam raporu reports/daily/'e kaydet
    _save_report(response, "KAPANIS")

    msg = f"Finzora Agent — Kapanış\n{ctx['timestamp'][:16]}\n\n{response}"
    send_private_telegram(msg)
    print("[Orkestratör] Kapanış yorumu gönderildi.")

    # Gruba: ayrıntılı günlük özet
    try:
        pfs   = ctx["raw"]["portfolios"]
        _now  = datetime.now(TR_TZ)
        _gun  = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"][_now.weekday()]
        _tarih = _now.strftime("%d %B %Y")

        BASLANGIC = {"aggressive": 400000, "balanced": 100000, "dividend": 100000}
        PF_LABEL  = {"aggressive": "⚡ Agresif", "balanced": "⚖️ Dengeli", "dividend": "💰 Temettü"}

        toplam_deger   = 0
        toplam_baslangic = 600000
        ozet_lines = [
            f"<b>Finzora AI — Günlük Kapanış Özeti</b>",
            f"<i>{_tarih} {_gun}</i>",
            "",
        ]

        tum_pozlar = []   # En iyi/kötü için

        for pf_name, pf in pfs.items():
            pozlar = pf.get("pozisyonlar", [])
            nakit  = float(pf.get("nakit", {}).get("miktar", 0))
            pf_bas = BASLANGIC.get(pf_name, 0)
            pf_deg = sum(
                p.get("adet", 0) * float(p.get("guncel_fiyat") or p.get("maliyet_baz", 0))
                for p in pozlar
            ) + nakit
            toplam_deger += pf_deg
            pf_pnl = (pf_deg - pf_bas) / pf_bas * 100 if pf_bas else 0
            pf_icon = "🟢" if pf_pnl >= 0 else "🔴"
            label = PF_LABEL.get(pf_name, pf_name)
            ozet_lines.append(f"{pf_icon} <b>{label}</b> ${pf_deg:,.0f} ({pf_pnl:+.1f}%)")

            # Pozisyon detayları
            for p in pozlar:
                sym   = p.get("sembol", "")
                mal   = float(p.get("maliyet_baz") or 0)
                gun   = float(p.get("guncel_fiyat") or mal)
                pnl   = (gun - mal) / mal * 100 if mal else 0
                adet  = p.get("adet", 0)
                tutar = (gun - mal) * adet
                p_icon = "🟢" if pnl >= 0 else "🔴"
                ozet_lines.append(
                    f"  {p_icon} {sym:5} {pnl:+.1f}%  ${gun:.2f}  "
                    f"({'+'if tutar>=0 else ''}{tutar:,.0f}$)"
                )
                tum_pozlar.append((sym, pnl, pf_name))
            ozet_lines.append("")

        # Swing
        try:
            sw_data = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
            sw_pozlar = sw_data.get("aktif_pozisyonlar", [])
            if sw_pozlar:
                ozet_lines.append("🔄 <b>Swing Trade</b>")
                for sp in sw_pozlar:
                    sym    = sp.get("sembol", "")
                    pnl    = sp.get("pnl_pct", 0)
                    gun_f  = sp.get("guncel_fiyat", 0)
                    stop   = sp.get("stop_loss", 0)
                    hedef  = sp.get("hedef_fiyat", 0)
                    stop_uzak = (gun_f - stop) / gun_f * 100 if gun_f and stop else 0
                    sp_icon = "🟢" if pnl >= 0 else "🔴"
                    ozet_lines.append(
                        f"  {sp_icon} {sym:5} {pnl:+.1f}%  stop %{stop_uzak:.1f} uzak"
                    )
                ozet_lines.append("")
        except Exception:
            pass

        # Toplam
        toplam_pnl = (toplam_deger - toplam_baslangic) / toplam_baslangic * 100
        t_icon = "🟢" if toplam_pnl >= 0 else "🔴"
        ozet_lines.append("━━━━━━━━━━━━━━━")
        ozet_lines.append(f"{t_icon} <b>Toplam: ${toplam_deger:,.0f} ({toplam_pnl:+.2f}%)</b>")
        ozet_lines.append(f"   Başlangıç: ${toplam_baslangic:,.0f}")

        # En iyi / en kötü
        if tum_pozlar:
            en_iyi  = max(tum_pozlar, key=lambda x: x[1])
            en_kotu = min(tum_pozlar, key=lambda x: x[1])
            ozet_lines.append("")
            ozet_lines.append(f"🏆 Günün en iyisi: <b>{en_iyi[0]}</b> {en_iyi[1]:+.1f}%")
            ozet_lines.append(f"📉 Günün en kötüsü: <b>{en_kotu[0]}</b> {en_kotu[1]:+.1f}%")

        ozet_lines.append("")
        ozet_lines.append("<i>Detaylı analiz: finzora.ai</i>")

        send_group_telegram("\n".join(ozet_lines))
        print("[Orkestratör] Ayrıntılı günlük özet gruba gönderildi.")
    except Exception as _e:
        print(f"[Orkestratör] Grup özet hatası: {_e}")

    # ── OTOMATİK ÖZ-GELİŞİM (her 2 iş günü) ──────────────────────────────
    try:
        from darwin_evolution import run_evolution_cycle, get_evolution_summary
        from prompt_evolver import sync_all_evolutions
        evo_result = run_evolution_cycle()
        if evo_result and evo_result.get("changed"):
            sync_all_evolutions()
            evo_msg = (
                f"🧬 *Darwin Evrim*\n"
                f"Kural: {evo_result.get('rule','?')} v{evo_result.get('version','?')}\n"
                f"Değişiklik: {evo_result.get('change_summary','')[:100]}"
            )
            send_private_telegram(evo_msg)
            print(f"[Darwin] Evrim tamamlandı: {evo_result.get('rule','?')}")
    except Exception as e:
        print(f"[Darwin] Kapanış evrim hatası: {e}")

    # ── GÜN SONU PORTFÖY ÖZET ────────────────────────────────────────────────
    try:
        toplam = 0
        for pf in ["aggressive","balanced","dividend"]:
            p = REPO_ROOT / "data" / "portfolios" / f"{pf}.json"
            if p.exists():
                d = json.load(open(p))
                toplam += float(d.get("toplam_deger", 0) or 0)

        ozet_msg = (
            f"📊 *Gün Sonu Portföy*\n"
            f"Toplam: ${toplam:,.0f}\n"
            f"Tarih: {datetime.now(TR_TZ).strftime('%d %b %Y')}"
        )
        send_private_telegram(ozet_msg)
    except Exception:
        pass


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

def _load_genome_context() -> str:
    """Darwin genome'daki aktif kuralları Claude prompt'una ekler."""
    genome_path = REPO_ROOT / "agent" / "memory" / "prompt_genome.json"
    if not genome_path.exists():
        return ""
    try:
        genome = json.load(open(genome_path))
        lines = ["\n=== AKTİF K-KURALLARI (Darwin Genome) ==="]
        for name, data in sorted(genome.items()):
            w = data.get("weight", 1.0)
            f = data.get("fitness")
            flag = "🔊" if w >= 1.5 else ("🔇" if w <= 0.5 else "")
            f_str = f"fitness:{f:.2f}" if f else ""
            lines.append(f"{flag} {name} v{data['version']} {f_str}")
            lines.append(f"  {data['current_prompt'].split(chr(10))[0][:100]}")
        return "\n".join(lines)
    except Exception:
        return ""


def _run_faz1_checks(portfolios: dict, market: dict) -> list:
    """FAZ_1 açılış kontrolleri — gap analizi, stop yakınlığı uyarıları."""
    uyarilar = []
    for pf_name, pf in portfolios.items():
        for pos in pf.get("pozisyonlar", []):
            sym   = pos.get("sembol", "")
            stop  = float(pos.get("stop_loss") or 0)
            mal   = float(pos.get("maliyet_baz") or 0)
            q     = market.get(sym, {})
            price = float(q.get("price") or pos.get("guncel_fiyat") or mal)
            if stop and price and price > 0:
                pct = (price - stop) / price * 100
                if pct < 3.0:
                    uyarilar.append(
                        f"⚡ FAZ_1 uyarı [{pf_name.upper()}] {sym}: "
                        f"stop %{pct:.1f} uzakta (${price:.2f} → stop ${stop:.2f})"
                    )
    return uyarilar


def _run_faz3_checks(market: dict) -> list:
    """FAZ_3 power hour kontrolleri — trailing stop sıkılaştırma uyarıları."""
    return []  # Swing manager zaten chandelier günceller


def _get_faz(now_tr) -> str:
    """Türkiye saatine göre aktif seansı döndür."""
    # Hafta sonu kontrolü — Cumartesi(5) ve Pazar(6) piyasa kapalı
    if now_tr.weekday() >= 5:
        return "KAPALI"   # Hafta sonu

    # NYSE tatil listesi (sabit)
    NYSE_TATIL = {
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
        "2026-05-25", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    }
    if now_tr.strftime("%Y-%m-%d") in NYSE_TATIL:
        return "KAPALI"   # NYSE tatili

    h = now_tr.hour + now_tr.minute / 60
    if 16.5 <= h < 17.5:
        return "FAZ_1"   # Açılış: TR 16:30-17:30
    elif 17.5 <= h < 21.0:
        return "FAZ_2"   # Orta seans: TR 17:30-21:00
    elif 21.0 <= h < 23.0:
        return "FAZ_3"   # Power hour: TR 21:00-23:00
    else:
        return "KAPALI"


def run_monitor(ctx: dict):
    """
    Seans içi otonom yönetim — her 30 dakikada çalışır.
    FAZ-aware: açılış / orta seans / power hour için farklı mantık.

    SEN KARAR VER kuralı — onay beklemez.
    """
    portfolios = ctx["raw"]["portfolios"]
    market     = ctx["raw"]["market"]
    now_tr     = datetime.now(pytz.timezone("Europe/Istanbul"))
    saat       = now_tr.strftime("%H:%M")
    faz        = _get_faz(now_tr)

    # Hafta sonu veya piyasa dışı saatte çalıştıysa giriş yapma
    if faz == "KAPALI":
        gun = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"][now_tr.weekday()]
        print(f"[Orkestratör] {gun} {saat} TR — piyasa kapalı. Giriş yok, sadece monitoring.")
        return

    print(f"[Orkestratör] Monitor çalışıyor — {saat} TR | {faz}")

    aksiyonlar = []
    uyarilar   = []

    # ── 0. CANLI RSI FETCH — tüm aktif semboller ─────────────────────────────
    # Portföy + swing pozisyonlarının sembollerini topla
    _rsi_syms = set()
    for _pf in portfolios.values():
        for _pos in _pf.get("pozisyonlar", []):
            _sym = _pos.get("sembol") or _pos.get("symbol")
            if _sym:
                _rsi_syms.add(_sym)
    try:
        _sw = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
        for _pos in _sw.get("aktif_pozisyonlar", []):
            if _pos.get("sembol"):
                _rsi_syms.add(_pos["sembol"])
    except Exception:
        pass
    # FMP'den canlı RSI çek (sembol başına 1 çağrı)
    try:
        rsi_map = get_rsi_batch(list(_rsi_syms))
    except Exception as _e:
        print(f"[RSI] Batch fetch başarısız: {_e}")
        rsi_map = {}
    # ─────────────────────────────────────────────────────────────────────────

    # ── 1. SWING ÇIKIŞ KONTROL — her FAZ'da ─────────────────────────────────
    # K-engine ile tüm çıkış kuralları (K-06, K-07, K-09, K-11)
    if run_exit_checks:
        active_path = REPO_ROOT / "data" / "swing" / "active.json"
        if active_path.exists():
            try:
                active_data = json.load(open(active_path))
                for pos in active_data.get("aktif_pozisyonlar", []):
                    sym    = pos.get("sembol", "")
                    cur_p  = market.get(sym, {}).get("price")
                    stop   = pos.get("stop_loss")
                    entry  = pos.get("giris_fiyati")
                    if sym and cur_p and stop and entry:
                        exit_r = run_exit_checks(
                            sym, float(cur_p), float(stop), float(entry),
                            rsi=rsi_map.get(sym) or pos.get("rsi", 50),
                            highest_high=pos.get("highest_high"),
                            atr=pos.get("atr_14")
                        )
                        if exit_r["action"] in ("EXIT_NOW", "PARTIAL"):
                            aksiyonlar.append(
                                f"{'🔴' if exit_r['action']=='EXIT_NOW' else '💰'} "
                                f"*{exit_r['action']}* {sym}: {exit_r['reason']}"
                            )
                        elif exit_r["action"] == "TIGHTEN":
                            uyarilar.append(
                                f"⚡ *TRAILING GÜNCELLE* {sym}: {exit_r['reason']}"
                            )
            except Exception as _e:
                print(f"[K-Engine exit] {_e}")

    swing_exits = _check_swing_exits(market)
    aksiyonlar.extend(swing_exits)

    # ── 2. PORTFÖY ÇIKIŞ KONTROL (stop + kısmi kâr) ─────────────────────────
    portfolio_exits = _check_portfolio_exits(market, rsi_map=rsi_map)
    aksiyonlar.extend(portfolio_exits)

    # ── 3. SWING GİRİŞ KONTROL ───────────────────────────────────────────────
    # FAZ_1: İlk 30dk gap stabilizasyonu beklenir, FAZ_2'de giriş yapılır
    if faz in ("FAZ_2", "FAZ_3"):
        swing_entries = _check_swing_entries()
        aksiyonlar.extend(swing_entries)

    # ── 4. PORTFÖY FIRSAT EXECUTION (sabah buy listinden) ─────────────────
    if faz == "FAZ_2":
        portfolio_entries = _execute_portfolio_opportunities(faz, market)
        aksiyonlar.extend(portfolio_entries)

    # ── FAZ_1: AÇILIŞ KONTROL ────────────────────────────────────────────────
    if faz == "FAZ_1":
        faz1_alerts = _run_faz1_checks(portfolios, market)
        uyarilar.extend(faz1_alerts)

    # ── FAZ_3: POWER HOUR FİNAL ──────────────────────────────────────────────
    if faz == "FAZ_3":
        faz3_alerts = _run_faz3_checks(market)
        uyarilar.extend(faz3_alerts)

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

    # ── 5. PORTFÖY HABERLERİ — kritik anahtar kelime tarama ─────────────────
    # Orchestrator portfolio_news'i sadece morning/closing için çekiyor.
    # Monitor'da da 4 saatlik haber bağlamı gelirse uyarı ver.
    portfolio_news = ctx.get("portfolio_news", "")
    if portfolio_news:
        KRITIK_KW = [
            "dividend cut", "cuts dividend", "suspends dividend", "eliminates dividend",
            "bankruptcy", "bankrupt", "fraud", "sec investigation", "going concern",
            "delist", "material weakness", "restatement",
        ]
        haber_satirlari = portfolio_news.lower().split("\n")
        for satir in haber_satirlari:
            for kw in KRITIK_KW:
                if kw in satir:
                    # Orijinal satırı (küçük harf olmayan) bul
                    idx = portfolio_news.lower().find(satir[:40])
                    orj = portfolio_news[idx:idx+200] if idx >= 0 else satir
                    uyarilar.append(
                        f"🚨 *KRİTİK HABER TESPİTİ*\n"
                        f"Anahtar kelime: '{kw}'\n"
                        f"{orj[:200]}"
                    )
                    break

    # ── 6. TELEGRAM ───────────────────────────────────────────────────────────
    # Aksiyonlar (yapılan işlemler) → private + gruba
    if aksiyonlar:
        msg_private = f"🤖 *Finzora Agent — Seans Aksiyonu* ({saat})\n\n"
        msg_private += "\n\n".join(aksiyonlar)
        send_private_telegram(msg_private)

        # Gruba: sadece alım/satım aksiyonları (kısa format)
        grup_aksiyonlar = [a for a in aksiyonlar
                           if any(k in a for k in ["ALIŞ","SATIŞ","STOP","GİRİŞ","ÇIKIŞ","K-06","K-11"])]
        if grup_aksiyonlar:
            msg_grup = f"<b>Finzora AI — İşlem</b> ({saat})\n\n"
            msg_grup += "\n\n".join(grup_aksiyonlar)
            msg_grup += "\n\n<i>Detaylı analiz: finzora.ai</i>"
            send_group_telegram(msg_grup)

        print(f"[Orkestratör] {len(aksiyonlar)} aksiyon alındı.")

    # Uyarılar (acil bildirimler) → sadece private
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


def _execute_portfolio_opportunities(faz: str, market: dict) -> list:
    """
    Sabah buy listinden portföylere alım yapar.
    FAZ_1: 16:30-17:30 TR — sadece izle, giriş YOK (gap stabilizasyonu)
    FAZ_2: 17:30-21:00 TR — onaylanan fırsatları execute et (swing + portföy girişleri)
    FAZ_3: 21:00-23:00 TR — sadece mevcut pozisyon yönetimi, yeni giriş yok
    """
    if faz == "FAZ_1" or not buy_position or not get_portfolio_status:
        return []

    # Session state'ten buy list'i oku (gitignored — GitHub Actions'ta olmayabilir)
    state_path = REPO_ROOT / "data" / "session_state.json"
    state = None
    buy_list = []
    piyasa_mod = "nötr"

    if state_path.exists():
        try:
            state = json.load(open(state_path))
            buy_list = state.get("buy_list", {}).get("adaylar", [])
            piyasa_mod = state.get("buy_list", {}).get("piyasa_mod", "nötr")
        except Exception:
            pass  # fallback devam edecek

    # Fallback 1: buy_candidates.json
    if not buy_list:
        try:
            bc_path = REPO_ROOT / "data" / "buy_candidates.json"
            if bc_path.exists():
                bc = json.load(open(bc_path))
                buy_list = bc.get("adaylar", [])
                piyasa_mod = "tarama"
                if buy_list:
                    print(f"[Execution] session_state boş → buy_candidates.json'dan {len(buy_list)} aday alındı")
        except Exception as _e:
            print(f"[Execution] buy_candidates fallback hatası: {_e}")

    # Fallback 2: daily_scan dosyalarından oku (buy_candidates da boşsa)
    if not buy_list:
        _EKLE_ESIK = {"balanced": 9, "dividend": 9, "aggressive": 14}
        for _pf in ["balanced", "dividend", "aggressive"]:
            _scan_path = REPO_ROOT / "data" / f"daily_scan_{_pf}.json"
            if not _scan_path.exists():
                continue
            try:
                _scan = json.load(open(_scan_path))
                _bugun = datetime.now(TR_TZ).strftime("%Y-%m-%d")
                if _scan.get("tarih", "") != _bugun:
                    continue  # Eski tarama — atla
                _esik = _EKLE_ESIK.get(_pf, 9)
                for _s in _scan.get("sonuclar", [])[:20]:
                    if float(_s.get("score", 0)) >= _esik:
                        _fiyat = float(_s.get("price", 0))
                        if not _fiyat:
                            continue
                        _atr = _fiyat * 0.025  # %2.5 ATR proxy
                        buy_list.append({
                            "symbol":  _s["symbol"],
                            "portföy": _pf,
                            "price":   _fiyat,
                            "stop":    round(_fiyat - 2 * _atr, 2),
                            "target":  round(_fiyat + 4 * _atr, 2),
                            "reason":  f"daily_scan_{_pf} skor:{_s.get('score')} | {_s.get('sector','')}",
                            "tema":    _s.get("sector", ""),
                        })
            except Exception as _e2:
                print(f"[Execution] daily_scan_{_pf} fallback hatası: {_e2}")
        if buy_list:
            print(f"[Execution] daily_scan fallback: {len(buy_list)} aday yüklendi")

    if not buy_list:
        return []

    aksiyonlar = []

    for aday in buy_list[:5]:  # Seans başına max 5 aday değerlendir
        sym     = aday.get("symbol", "")
        portföy = aday.get("portföy", "aggressive")
        stop    = float(aday.get("stop", 0))
        target  = float(aday.get("target", 0))
        reason  = aday.get("reason", "")
        tema    = aday.get("tema", "")

        # Canlı fiyat
        q = market.get(sym, {})
        price = float(q.get("price") or q.get("previousClose") or 0)
        if not price:
            # market dict'te yoksa sabah fiyatını kullan
            price = float(aday.get("price", 0))
        if not price:
            continue

        # Fiyat sabah önerilen seviyeye yakın mı? (%2 tolerans)
        sabah_fiyat = float(aday.get("price", price))
        if abs(price - sabah_fiyat) / sabah_fiyat > 0.03:
            print(f"[Execution] {sym}: fiyat çok kaydı (sabah ${sabah_fiyat:.2f} → şimdi ${price:.2f})")
            continue

        # Stop güncelle (canlı fiyatla)
        if price < stop:
            print(f"[Execution] {sym}: fiyat stop altına geçmiş, atlandı")
            continue

        # K-engine son kontrol (canlı VIX ile)
        try:
            import requests as _req
            vix_r = _req.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
                              headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
            vix = float(vix_r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"])
        except Exception:
            vix = state.get("buy_list", {}).get("vix", 20) if state else 20

        if run_entry_checks:
            k_res = run_entry_checks(sym, vix=vix, base_size=5000)
            if not k_res["go"]:
                print(f"[Execution] {sym} K-engine veto: {k_res['fail_reason']}")
                continue

        # Portföy durumu
        status = get_portfolio_status(portföy)
        if status["slot"] <= 0:
            print(f"[Execution] {portföy} dolu, {sym} atlandı")
            continue

        # Alım miktarı: nakit / kalan slot, max $15K
        nakit = status["nakit"]
        slot  = status["slot"]
        tutar = min(nakit * 0.25, 15000, nakit / max(slot, 1))
        if tutar < 1000:
            continue

        result = buy_position(sym, portföy, tutar, price, stop, target,
                               reason, tema)
        if result["ok"]:
            aksiyonlar.append(
                f"🟢 *ALIŞ* [{portföy.upper()}]\n"
                f"{sym} {result['adet']} adet @${price:.2f}\n"
                f"Stop: ${stop:.2f} | Hedef: ${target:.2f}\n"
                f"Tema: {tema} | ${result['tutar']:,.0f}"
            )
            # Buy list'ten çıkar (bir kez execute et)
            buy_list = [a for a in buy_list if a.get("symbol") != sym]
            if state and "buy_list" in state:
                state["buy_list"]["adaylar"] = buy_list
                try:
                    json.dump(state, open(state_path,"w"), ensure_ascii=False, indent=2)
                except Exception:
                    pass

    return aksiyonlar


def _check_portfolio_exits(market: dict, rsi_map: dict = None) -> list:
    """
    K-06, K-11, K-04 SMA200 ihlali, tez bozulması için portföy çıkışları.
    """
    if not sell_position:
        return []

    aksiyonlar = []

    for pf_name in ["aggressive","balanced","dividend"]:
        pf_path = REPO_ROOT / "data" / "portfolios" / f"{pf_name}.json"
        if not pf_path.exists():
            continue

        try:
            data = json.load(open(pf_path))
        except Exception:
            continue

        for pos in data.get("pozisyonlar", []):
            sym    = pos.get("sembol","")
            stop   = float(pos.get("stop_loss") or 0)
            mal    = float(pos.get("maliyet_baz") or 0)
            q      = market.get(sym, {})
            price  = float(q.get("price") or pos.get("guncel_fiyat") or mal)

            if not price or not stop:
                continue

            pnl = (price - mal) / mal * 100 if mal else 0

            # K-06: Stop tetiklendi
            if price <= stop:
                result = sell_position(sym, pf_name,
                                       f"K-06 stop tetiklendi ${price:.2f}≤${stop:.2f}",
                                       pct=100, price=price)
                if result["ok"]:
                    aksiyonlar.append(
                        f"🔴 *K-06 STOP* [{pf_name.upper()}]\n"
                        f"{sym} @${price:.2f} | P/L: {pnl:+.1f}%\n"
                        f"→ *SATIN {result['adet']} ADET*"
                    )
                continue

            # K-11: RSI 80+ VE kâr %15+ → kısmi satış
            # rsi_map: monitor başında FMP'den çekilen canlı RSI değerleri
            rsi_live = (rsi_map or {}).get(sym)
            rsi = float(rsi_live if rsi_live is not None else pos.get("rsi") or 50)
            if rsi >= 80 and pnl >= 15:
                result = sell_position(sym, pf_name,
                                       f"K-11 katman 2: RSI {rsi:.0f} + kâr %{pnl:.1f}",
                                       pct=25, price=price)
                if result["ok"]:
                    aksiyonlar.append(
                        f"💰 *K-11 KISMİ KÂR* [{pf_name.upper()}]\n"
                        f"{sym} %25 @${price:.2f} | kâr %{pnl:.1f}%\n"
                        f"→ *SATIN {result['adet']} ADET*"
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

    # Zaten açık olanları listeden çıkar, kalan 3'ü kontrol et
    aktif_semboller = {p.get("sembol") for p in active.get("aktif_pozisyonlar", [])}
    kontrol_listesi = [s for s in giris_syms if s not in aktif_semboller][:3]

    for sym in kontrol_listesi:
        # Kapasite yeterliyse devam
        if mevcut_poz >= 5:
            break

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



def _save_report(content: str, rapor_tipi: str):
    """
    Claude yanıtını reports/daily/ klasörüne .md dosyası olarak kaydeder.
    rapor_tipi: SABAH, KAPANIS, SWING, PORTFOY
    """
    import subprocess
    from pathlib import Path
    
    _simdi = datetime.now(TR_TZ)
    # Kapanış raporu gece yarısından sonra çalışır (UTC 21:30 = TR 00:30)
    # Bu durumda rapor önceki güne ait, bir gün geri al
    if rapor_tipi == "KAPANIS" and _simdi.hour < 6:
        from datetime import timedelta
        tarih = (_simdi - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        tarih = _simdi.strftime("%Y-%m-%d")
    dosya = REPO_ROOT / "reports" / "daily" / f"DAILY_{rapor_tipi}_{tarih}.md"
    dosya.parent.mkdir(parents=True, exist_ok=True)
    
    baslik = f"# {rapor_tipi.lower()} raporu — {tarih}\n\n> finzora ai | otomatik oluşturuldu\n\n"
    dosya.write_text(baslik + content, encoding="utf-8")
    print(f"[Rapor] {dosya.name} kaydedildi")
    
    # Git commit
    try:
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name", "Finzora AI"], capture_output=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add", str(dosya)], capture_output=True)
        msg = f"[{rapor_tipi} RAPORU] {tarih}"
        result = subprocess.run(["git", "commit", "-m", msg], capture_output=True)
        if result.returncode == 0:
            subprocess.run(["git", "push"], capture_output=True)
            print(f"[Rapor] Git push başarılı: {dosya.name}")
    except Exception as e:
        print(f"[Rapor] Git hatası: {e}")

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

    # Tema × Portföy Matris Güncellemesi (11 Nisan 2026)
    tema_matrix_rpt = ""
    if run_tema_matrix:
        try:
            run_tema_matrix()
            tema_matrix_rpt = "Tema × portföy başarı matrisi güncellendi (agent/memory/tema_portfolio_matrix.json)"
            print("[Orkestratör] Tema matrisi güncellendi")
        except Exception as e:
            tema_matrix_rpt = f"Tema matrisi hata: {e}"

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

    _now_tr  = datetime.now(TR_TZ)
    _gunler  = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    _bugun_tarih = _now_tr.strftime("%d %B %Y")
    _bugun_gun   = _gunler[_now_tr.weekday()]

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

    # Raporu reports/weekly/ klasörüne kaydet + git push
    try:
        import subprocess
        tarih = datetime.now(TR_TZ).strftime("%Y-%m-%d")
        haftalik_dosya = REPO_ROOT / "reports" / "weekly" / f"WEEKLY_{tarih.replace('-','_')}.md"
        haftalik_dosya.parent.mkdir(parents=True, exist_ok=True)
        baslik = f"# haftalık rapor — {tarih}\n\n> finzora ai | otomatik oluşturuldu\n\n"
        haftalik_dosya.write_text(baslik + response, encoding="utf-8")
        print(f"[Rapor] {haftalik_dosya.name} kaydedildi")
        os.chdir(REPO_ROOT)
        subprocess.run(["git", "config", "user.name", "Finzora AI"], capture_output=True)
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add", str(haftalik_dosya)], capture_output=True)
        result = subprocess.run(["git", "commit", "-m", f"[HAFTALIK RAPOR] {tarih}"], capture_output=True)
        if result.returncode == 0:
            subprocess.run(["git", "push", "origin", "main"], capture_output=True)
            print(f"[Rapor] Git push başarılı: {haftalik_dosya.name}")
        else:
            print(f"[Rapor] Commit atlandı (değişiklik yok veya hata)")
    except Exception as e:
        print(f"[Rapor] Haftalık kayıt hatası: {e}")

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
    baslama = datetime.now(TR_TZ)
    print(f"[Finzora Agent] Başlatılıyor — {baslama.strftime('%Y-%m-%d %H:%M TR')}")

    mode = get_run_mode()
    print(f"[Finzora Agent] Mod: {mode.upper()}")
    _log.calistirma(
        f"Agent başladı — {mode.upper()}",
        f"Zaman: {baslama.strftime('%d.%m.%Y %H:%M TR')}",
        kaynak="orchestrator"
    )

    try:
        ctx = collect_context(mode)
    except Exception as e:
        _log.hata("Bağlam toplama başarısız", str(e), kaynak="orchestrator.collect_context")
        raise

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
    try:
        main()
        _log.calistirma(
            "Agent tamamlandı",
            f"Süre: {datetime.now(TR_TZ).strftime('%H:%M TR')}",
            kaynak="orchestrator"
        )
    except Exception as e:
        _log.hata(
            "Agent çöktü",
            f"Hata: {str(e)[:300]}",
            kaynak="orchestrator"
        )
        raise
