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
from claude_agent import get_claude_decision, get_claude_decision_with_actions
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
        get_portfolio_status, compute_atr_stop, fetch_live_price
    )
except ImportError as _ie:
    print(f"[Orchestrator] Modül yüklenemedi: {_ie}")
    run_macro_intelligence = find_candidates = None
    buy_position = sell_position = deploy_cash = None
    get_portfolio_status = None
    compute_atr_stop = fetch_live_price = None

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

# Tematik Katalist Takvimi — NVIDIA Ising (14 Nis 2026) sonrası eklendi
try:
    from thematic_calendar import build_thematic_context, check_thematic_event
except ImportError:
    build_thematic_context = lambda *a, **kw: ""
    check_thematic_event = lambda *a, **kw: (None, None)

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
    İzleme: sadece portföy + swing + piyasa (hızlı, ucuz).
    """
    print(f"[Orkestratör] Veri toplanıyor... (mod: {mode})")

    # ── PRE-SNAPSHOT: Otomatik swing kapatmaları işle ─────────────────────
    # 27 Nis 2026 bug fix: collect_context snapshot ALMADAN ÖNCE SURE/STOP/HEDEF
    # tetikli kapanışları işle. Aksi halde compressed bağlam eski state ile
    # gelir, Claude raporda zaten kapatılmış pozisyonları "açık" listeler
    # (CAT/KLAC/AMAT 27 Nis sabah raporunda hayalet pozisyon olarak göründü).
    # update_swing_positions idempotent — ikinci çağrı sadece price update yapar.
    if mode in ("morning", "closing", "monitor", "weekly"):
        try:
            from swing_manager import update_swing_positions
            uyarilar = update_swing_positions()
            print(f"[Orkestratör] Pre-snapshot swing kontrol — {len(uyarilar)} uyarı")
        except Exception as e:
            print(f"[Orkestratör] Pre-snapshot swing kontrol hatası: {e} (devam)")

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

    # Tematik katalist takvim kontrolü (ucuz, her modda çalışır)
    try:
        thematic = build_thematic_context()
    except Exception as e:
        print(f"[Thematic] Hata: {e}")
        thematic = ""

    return {
        "mode":           mode,
        "timestamp":      datetime.now(TR_TZ).isoformat(),
        "compressed":     compressed,
        "research":       research,
        "twitter":        twitter,
        "risk":           risk,
        "portfolio_news": portfolio_news,
        "thematic":       thematic,
        "raw": {
            "portfolios": portfolios,
            "market":     market,
            "swing":      swing,
        }
    }

# ── Mod çalıştırıcıları ───────────────────────────────────────────────────────

# ── K-05 Bilanço Filtresi (29 Nis 2026 reform) ────────────────────────────────
# Kapanış agent EKLE/BÜYÜT kararı verirken bilanço tarihi ≤7 gün ise
# o kararı GERİ ÇEKER. Bu sayede 'bugün al, bugün sat' (FLS örnegi) yaşanmaz.

def _filtre_k05_bilanco(kararlar: list, mode: str = "closing") -> list:
    """K-05 (bilanço öncesi 48 saat penceresi) — EKLE/BÜYÜT kararlarını filtrele.

    Bilanço ≤2 gün uzakta olan sembollere yeni giriş YASAK. Filtrelenen
    kararlar '_k05_filtered' flag'i ile işaretlenir, log basılır.

    closing mode için sıkı (≤2 gün), morning için daha esnek (≤1 gün)
    çünkü morning aynı gün execute eder, closing 12+ saat sonra.
    """
    if not kararlar:
        return kararlar

    try:
        import os as _os
        api_key = _os.environ.get("FMP_API_KEY", "")
        if not api_key:
            print("[K-05 Filtre] FMP_API_KEY yok, filtre atlandı")
            return kararlar
    except Exception:
        return kararlar

    # closing icin esik 2 gun (overnight + 1 seans), morning icin 1 gun
    esik_gun = 2 if mode == "closing" else 1

    filtreli = []
    bugun_tr = datetime.now(TR_TZ).date()

    for k in kararlar:
        tip = (k.get("tip") or "").upper()
        sembol = (k.get("sembol") or "").upper()

        # Sadece yeni giris kararlarini filtrele
        if tip not in ("EKLE", "BÜYÜT"):
            filtreli.append(k)
            continue

        if not sembol:
            filtreli.append(k)
            continue

        # FMP earnings cek
        try:
            import urllib.request as _ur, json as _j
            url = f"https://financialmodelingprep.com/stable/earnings?symbol={sembol}&apikey={api_key}"
            with _ur.urlopen(url, timeout=10) as r:
                data = _j.loads(r.read().decode())
            if not data:
                # Bilanço bilgisi yok, geç
                filtreli.append(k)
                continue

            # Yarınki/yakın bilancoyu bul
            yakin_bilanco = None
            for e in data:
                e_tarih_str = e.get("date", "")
                if not e_tarih_str:
                    continue
                try:
                    e_tarih = datetime.strptime(e_tarih_str[:10], "%Y-%m-%d").date()
                except Exception:
                    continue
                if e_tarih >= bugun_tr:
                    yakin_bilanco = e_tarih
                    break

            if not yakin_bilanco:
                filtreli.append(k)
                continue

            gun_kalan = (yakin_bilanco - bugun_tr).days
            if gun_kalan <= esik_gun:
                # FILTRELE
                k["_k05_filtered"] = True
                k["_k05_reason"] = f"Bilanço {yakin_bilanco} ({gun_kalan}g kaldı, eşik {esik_gun}g)"
                print(f"[K-05 Filtre] {tip} {sembol} ELENDI — bilanço {yakin_bilanco} ({gun_kalan}g kaldı)")
                continue

            filtreli.append(k)
        except Exception as _e:
            print(f"[K-05 Filtre] {sembol} kontrol hatası: {_e} (geçirildi)")
            filtreli.append(k)

    elenen = len(kararlar) - len(filtreli)
    if elenen > 0:
        print(f"[K-05 Filtre] {elenen}/{len(kararlar)} karar bilanço penceresinde elendi")

    return filtreli


# ── Session State Yardımcısı ───────────────────────────────────────────────────

def _update_session_state(key: str, value) -> None:
    """data/session_state.json'ı günceller — FAZ handoff için. File lock ile race condition önlenir."""
    import fcntl
    state_path = REPO_ROOT / "data" / "session_state.json"
    lock_path  = state_path.with_suffix(".lock")
    try:
        with open(lock_path, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                state = json.load(open(state_path)) if state_path.exists() else {}
            except Exception:
                state = {}
            state[key]         = value
            state["timestamp"] = datetime.now(TR_TZ).isoformat()
            with open(state_path, "w") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            fcntl.flock(lf, fcntl.LOCK_UN)
        return
    except (IOError, OSError):
        pass  # Lock alınamadı — fallback: lock'suz yaz (en kötü senaryo)
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

    # Duplicate-guard: ayni gun icin SABAH raporu zaten yazildiysa cik.
    # (Yedek cron ':12' ayni gun icinde ikinci kez tetiklenirse tekrar Claude
    # cagrisi yapmayi onler — sadece ana tetik kacirildiysa yedek devreye girer.)
    try:
        _bugun_tr = datetime.now(TR_TZ).strftime("%Y-%m-%d")
        _bugunku_rapor = REPO_ROOT / "reports" / "daily" / f"DAILY_SABAH_{_bugun_tr}.md"
        _force = os.environ.get("FORCE_MORNING", "").strip().lower() in ("1", "true", "yes")
        if _bugunku_rapor.exists() and not _force:
            print(f"[Sabah] {_bugunku_rapor.name} zaten mevcut — atlaniyor (FORCE_MORNING=1 ile zorlayabilirsin).")
            return
    except Exception as _dg:
        print(f"[Sabah] Duplicate guard uyarisi: {_dg} (devam ediliyor)")

    # ── MAKRO ZİYASAL ZEKA ──────────────────────────────────────────────────
    macro_ctx = {}
    buy_candidates = []

    if run_macro_intelligence:
        try:
            print("[Sabah] Makro tema analizi...")
            # VIX al — merkezi vix_fetcher (cache + Yahoo + FMP fallback zinciri)
            try:
                from vix_fetcher import get_vix
                vix, vix_src = get_vix()
                print(f"[Sabah] VIX={vix} (kaynak: {vix_src})")
            except Exception as _vx:
                print(f"[Sabah] VIX fetcher hatası: {_vx}, default 20.0")
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

{premarket_ctx}

{ctx['thematic']}

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
0.7. tematik katalist durumu (yukarıdaki "Tematik Durum" bloğu DOLUYSA doldur, boşsa ATLA):
     - Status: PRE-EVENT / EVENT DAY / POST-EVENT
     - Etkinlik adı, tema, birincil + ekosistem tickerlar
     - Aksiyon: PRE → izleme listesine ekle + RSI<65/50SMA üstü/son 10g <%20 filtresi | EVENT DAY → KOVALAMA YASAK + canlı takip + ertesi gün planı | POST → giriş penceresi kuralları (1.gün yasak, 2.gün RSI<75 yarım, 3-5.gün volume+RSI kontrolü, 5+ geç giriş)
     - Saf oyuncular (speculative) için: YARIM pozisyon (sermayenin max %3'ü), sabit %5 stop
     - Detaylı kurallar: docs/THEMATIC_CATALYST_CALENDAR.md + docs/THEMATIC_INTEGRATION_GUIDE.md
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

NAKİT KULLANIM KURALI (27 Nis 2026 — ZORUNLU):
- 3 portföyde nakit oranı %10'u GEÇMEMELİ. Risk bağlamındaki "NAKİT KULLANIMI" bloğuna BAK.
- 🔴 AŞIM gören portföyler için günün planında SOMUT konuşlandırma kararı üret:
  * Yükseliş bekleniyorsa → fırsat sektörlerinden EKLE/BÜYÜT (sektör+tema K-12 %40 limiti içinde).
  * Geri çekilme bekleniyorsa → defansif rotasyon (XLP/XLV/GLD/TLT) veya inverse ETF (SH/SQQQ/SDOW).
  * Hedge/inverse kuralları portföye göre değişir:
     - AGRESİF: inverse ETF + put serbest.
     - DENGELİ: önce defansif rotasyon, inverse max %10 ve sadece düşük kaldıraçlı (SH/SDOW); 3x kaldıraçlı (SQQQ) YASAK.
     - TEMETTÜ: hedge ve inverse ETF YASAK; sadece defansif temettü hisseleri.
- "Yeni giriş yasak" karar verme — nakit aşımı varsa K-02/K-17 dışında en az BİR EKLE veya BÜYÜT kararı zorunludur.
- Risk/ödül min 2:1, K-12 sektör+tema %40 limiti geçerli.
- "Nakit fazla ama bekleyelim" gerekçesi kabul EDİLMEZ — somut sektör + symbol + tutar öner.

EKSIK VERI KURALLARI (21 Nisan 2026 teshisi — ZORUNLU UYGULA):
- Endeks tablosunda HIÇ BİR hücre "—" veya boş birakilmaz. Değişim hesaplanamiyorsa:
  * Önce veri bloğundaki previousClose + current price'tan MANUEL hesapla: (price - prevClose) / prevClose * 100
  * Hala yoksa "N/A (kaynak: X)" yaz ve NEDEN eksik olduğunu parantezde belirt
  * FMP changesPercentage seans dışı 0 döner — bu durumu bil, manuel hesapla
- Ön piyasa BLOGUNUN tablo formatinda YAZILMASI ZORUNLU (prose yetmez):
  | ticker | kapanış | ön piyasa | fark% | not |
  Veri bloğundaki premarket_gaps dolu ise TÜMÜNÜ tabloda listele (12 taneyse 12'si de).
- 0.5 Dün seans sonu notları: session_state veri bloğunda görünüyorsa oradan al, YOKSA bir önceki günün KAPANIS raporunun son 5 satırından özetle. "İlk çalışma — flag yok" cevabı kabul EDİLMEZ.
- Herhangi bir bölümde hesaplama yapamiyorsan [KAYNAK_YOK] etiketi ile nedeni söyle — sessizce atlama.
- Senaryo testinde listelenen semboller stop tetiklenenlerdir — fiyat ve stop seviyesi verilmiştir, kullan.

ANLAŞILIRLIK KURALLARI: Sade Türkçe yaz. İngilizce terim kullanmaktan kaçın:
- "stop-loss" yerine "zarar kes seviyesi"
- "trailing stop" yerine "takip eden zarar kes"
- "earnings" yerine "bilanço açıklaması"
- "drawdown" yerine "zirveden geri çekilme"
- "exposure" yerine "pozisyon ağırlığı"
K-XX kural kodları zorunlu, ama anlamını parantezde Türkçe açıkla (örn: "K-05 (bilanço öncesi 48 saat çıkış)").
Sayıları binlik ayraçla yaz: $135,832.

KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan. Küçük harf Türkçe.
"""

    # ── YENİ: yapılandırılmış karar desteği (Seçenek A) ──────────────────────
    response, claude_kararlar = get_claude_decision_with_actions(prompt, mode="morning")
    save_daily_brief(response, "morning")

    # Tam raporu reports/daily/'e kaydet
    _save_report(response, "SABAH")

    # SABAH raporundan DAILY_SWING_*.md ve DAILY_PORTFOY_*.md dosyalarini
    # ayristir (ek Claude cagrisi yok, markdown parse; memory'deki v3.0 uclu
    # yapinin maliyetsiz esdegeri).
    try:
        from split_sabah_report import split as _split_sabah
        _split_result = _split_sabah()
        if not _split_result.get("skipped"):
            print(f"[Orkestratör] SWING + PORTFOY dosyalari ayristirildi.")
        else:
            print(f"[Orkestratör] Split atlandi: {_split_result.get('reason')}")
    except Exception as _spe:
        print(f"[Orkestratör] Split hatasi (tolere): {_spe}")

    # Claude kararlarını execute et (piyasa açıksa) veya session_state'e kaydet
    _now_tr2 = datetime.now(TR_TZ)
    piyasa_acik = _now_tr2.weekday() < 5 and (
        (_now_tr2.hour == 16 and _now_tr2.minute >= 30)
        or (17 <= _now_tr2.hour < 23)
    )
    if claude_kararlar and piyasa_acik:
        # K-05 filtre (morning mode): aynı gün al-sat olmasın
        try:
            claude_kararlar = _filtre_k05_bilanco(claude_kararlar, mode="morning")
        except Exception as _k05e:
            print(f"[Orkestratör] K-05 filtre hatası (morning): {_k05e} (devam)")
        try:
            market_ctx = get_market_context()
            karar_aksiyonlar = _execute_claude_decisions(claude_kararlar, market_ctx)
            for msg_k in karar_aksiyonlar:
                send_private_telegram(msg_k)
                send_group_telegram(msg_k)
        except Exception as _ce:
            print(f"[Orkestratör] Claude karar execute hatası: {_ce}")
    elif claude_kararlar and not piyasa_acik:
        # K-05 filtre — piyasa kapali olsa da
        try:
            claude_kararlar = _filtre_k05_bilanco(claude_kararlar, mode="morning")
        except Exception as _k05e:
            print(f"[Orkestratör] K-05 filtre hatası: {_k05e} (devam)")
        # Piyasa kapalı: kararları session_state'e kaydet, FAZ_2'de execute edilecek
        try:
            import json as _json_sm
            _ss_path_sm = REPO_ROOT / "data" / "session_state.json"
            _ss_sm = _json_sm.load(open(_ss_path_sm)) if _ss_path_sm.exists() else {}
            _mevcut_ck = _ss_sm.get("claude_kararlar", {})
            
            # 28 Nis 2026 düzeltme: sabah kararları ÖNCEKİ kapanış
            # kararlarının üzerine yazılır (en güncel olan, daha kaliteli context).
            # Önceki kontrol "executed bekleyen var" sabah kararlarını engelliyor,
            # CL gibi yeni tespitlerin uygulanmamasına neden oluyor.
            _eski_kaynak = _mevcut_ck.get("kaynak", "")
            _eski_executed = _mevcut_ck.get("executed", False)
            _arsiv_str = ""
            
            # Önceki kararlar execute edilmediyse ARŞIVLE (kayıt için)
            if _mevcut_ck.get("kararlar") and not _eski_executed:
                _ss_sm.setdefault("claude_kararlar_arsiv", []).append({
                    "arsivlendi_zaman": datetime.now(TR_TZ).isoformat(),
                    "uzeri_yazildi_neden": "Sabah agent yeni kararlari geldi",
                    **_mevcut_ck,
                })
                # Son 10 arşivi tut
                _ss_sm["claude_kararlar_arsiv"] = _ss_sm["claude_kararlar_arsiv"][-10:]
                _arsiv_str = f" (onceki {len(_mevcut_ck.get('kararlar', []))} karar [{_eski_kaynak}] arsivlendi)"
            
            _ss_sm["claude_kararlar"] = {
                "tarih":   datetime.now(TR_TZ).isoformat(),
                "kararlar": claude_kararlar,
                "kaynak":  "sabah_raporu",
                "executed": False,
            }
            with open(_ss_path_sm, "w") as _ff_sm:
                _json_sm.dump(_ss_sm, _ff_sm, ensure_ascii=False, indent=2)
            print(f"[Orkestratör] {len(claude_kararlar)} sabah kararı session_state'e kaydedildi{_arsiv_str}.")
        except Exception as _ce_sm:
            print(f"[Orkestratör] Sabah kararı session_state kayıt hatası: {_ce_sm}")

    # ── TEMA BAZLI DİNAMİK TARAMA (sabah raporu sonrası) ──────────────────────
    # Her sabah tüm portföyler için FMP screener + tema filtresiyle taze evren
    # oluşturulur. Sonuçlar buy_candidates.json'a yazılır, FAZ_2'de execute edilir.
    try:
        from opportunity_finder import run_theme_scan as _rts
        from vix_fetcher import get_vix as _gv_morning
        _vix_m, _ = _gv_morning()
        _vix_m = _vix_m or 20.0
        print("[Orkestratör] Tema taraması başlıyor...")
        for _pf_m in ["aggressive", "balanced", "dividend"]:
            try:
                from execution_engine import get_portfolio_status as _gps_m
                _st_m = _gps_m(_pf_m)
                if _st_m.get("slot", 0) <= 0:
                    print(f"[Orkestratör] {_pf_m} dolu, tarama atlandı")
                    continue
                _mev_m = _st_m.get("semboller", [])
                _res_m = _rts(_pf_m, vix=_vix_m, mevcut_pozlar=_mev_m,
                               min_skor=5.5, max_aday=10)
                print(f"[Orkestratör] {_pf_m}: {len(_res_m)} aday buy_candidates'a eklendi")
            except Exception as _pfe:
                print(f"[Orkestratör] {_pf_m} tema tarama hatası: {_pfe}")
    except Exception as _tse:
        print(f"[Orkestratör] Tema taraması genel hata (tolere): {_tse}")

    # Telegram'a 3 mesaj: multi-agent + debate (varsa) + genel analiz
    send_private_telegram(multi_summary + debate_msg)
    msg    = f"Finzora Agent — Sabah Analizi\n{ctx['timestamp'][:16]}\n\n{response}"
    result = send_private_telegram(msg)
    print(f"[Orkestratör] Telegram sonucu: {result}")
    
    # TEZ BOZULMA UYARI (28 Nis 2026): skor >=50 pozisyonlar DM'ye
    try:
        from thesis_erosion import tum_portfoyler as _te_tum
        te_s = _te_tum()
        kritik = [p for p in te_s.get("pozisyonlar", []) if p["skor"] >= 50]
        if kritik:
            te_msg = f"🚨 TEZ BOZULMA — {len(kritik)} pozisyon kritik\n\n"
            for p in sorted(kritik, key=lambda x: -x["skor"]):
                te_msg += f"{p['seviye']} *{p['sembol']}* ({p['portfoy']}) skor:{p['skor']}\n"
                te_msg += f"   {p['karar']}\n   → {p['aksiyon']}\n"
                for s_str in p["sebepler"][:2]:
                    te_msg += f"   • {s_str}\n"
                te_msg += "\n"
            send_private_telegram(te_msg)
            print(f"[Tez] DM uyari gonderildi: {len(kritik)} pozisyon")
        else:
            print("[Tez] Kritik pozisyon yok, uyari yok")
    except Exception as _tee:
        print(f"[Tez] Hata (tolere): {_tee}")

def run_closing(ctx: dict):
    """Kapanış yorumu — piyasa kapandıktan sonra."""
    print("[Orkestratör] Kapanış modu çalışıyor...")

    # Duplicate-guard: ayni seansin KAPANIS raporu zaten yazildiysa cik.
    # Kapanis cron 21:30 UTC = TR 00:30 (ertesi gun gece). TR < 06:00 ise
    # rapor bir onceki gunun tarihiyle yazilir (_save_report ile ayni mantik).
    try:
        from datetime import timedelta
        _simdi_tr = datetime.now(TR_TZ)
        if _simdi_tr.hour < 6:
            _rapor_tarih = (_simdi_tr - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            _rapor_tarih = _simdi_tr.strftime("%Y-%m-%d")
        _bugunku_rapor = REPO_ROOT / "reports" / "daily" / f"DAILY_KAPANIS_{_rapor_tarih}.md"
        _force = os.environ.get("FORCE_CLOSING", "").strip().lower() in ("1", "true", "yes")
        if _bugunku_rapor.exists() and not _force:
            print(f"[Kapanis] {_bugunku_rapor.name} zaten mevcut — atlaniyor (FORCE_CLOSING=1 ile zorlanir).")
            return
    except Exception as _dg:
        print(f"[Kapanis] Duplicate guard uyarisi: {_dg} (devam ediliyor)")

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

    # 5 yön zenginleştirme: işlem akışı + plan vs gerçekleşme + risk panosu
    # + erken uyarı + sektör rotasyon. closing_enrichment modülü tüm bu
    # blokları tek string olarak döndürür, prompt'a doğrudan inject edilir.
    try:
        from closing_enrichment import kapanis_zenginlestirici
        _seans_str = _seans_gun.strftime("%Y-%m-%d")
        zenginlestirici = kapanis_zenginlestirici(portfolios, _seans_str)
    except Exception as _ze:
        print(f"[Kapanış] Zenginleştirici uyarısı: {_ze}")
        zenginlestirici = ""

    prompt = f"""
{ctx['compressed']}

{ctx['risk']}

{zenginlestirici}

{swing_ozet}

{ctx['research']}

{ctx['twitter']}

{ctx['portfolio_news']}

{ctx['thematic']}

{genome_ctx}

=== GÖREV: KAPANIS RAPORU ===
BUGÜNÜN TARİHİ: {_bugun_tarih}
BUGÜNÜN GÜNÜ: {_bugun_gun}

Yukarıdaki verilerle docs/prompts/DAILY_PART2_CLOSING.md formatında kapanış raporu üret.
Rapor başlığında tarih ve gün bilgisini YUKARIDAN al.

ÖNEMLİ — RAPOR ZENGİNLEŞTİRME BLOKLARI:
Yukarıda hazır tablolarla 5 ek bölüm var, bunları RAPORA AYNEN DAHİL ET (yeniden hesaplama):
- "0. PORTFÖY ÖZETİ (PANO)" → en başta, portföy takibinden ÖNCE
- "1.2 SEKTÖR ROTASYON" → günün özeti içine, endeks tablosundan SONRA
- "1.5 GÜN İÇİ İŞLEM AKIŞI" → portföy takibinden ÖNCE
- "5.1 SABAH PLANI vs GERÇEKLEŞME" → günün değerlendirmesi içine
- "6.5 ERKEN UYARI RADARI" → yarın aksiyonlarından SONRA

Bu bloklarda zaten gerçek sayılar ve veri var — sen sadece üzerine yorum/analiz EKLE.
Tabloyu silmeden, altına "Yorum:" satırı ekleyerek ne anlama geldiğini açıkla.

Zorunlu bölümler:
0. portföy özeti panosu (yukarıdaki tabloyu aynen al + 1-2 cümle yorum)
1. günün özeti (endeks tablosu, sektör rotasyon, trend)
1.5. gün içi işlem akışı (yukarıdaki tabloyu aynen al + net etki yorumu)
2. portföy takibi (3 portföy tablo, uyarılar, aksiyonlar)
3. swing trade durumu (chandelier stop kontrolü)
4. kazanç açıklamaları (portföy/watchlist kesişimi)
4.5. tematik katalist yansıması (yukarıdaki "Tematik Durum" bloğu DOLUYSA doldur, boşsa ATLA)
5. günün değerlendirmesi (sabah planı vs gerçekleşme bloğunu ekle, dersler çıkar)
6. yarın aksiyonları (hemen / izle / pasif)
6.5. erken uyarı radarı (yukarıdaki tabloyu aynen al + öncelikli pozisyon yorumu)

ANLAŞILIRLIK KURALLARI (27 Nis 2026):
- Sade Türkçe yaz. İngilizce terim kullanmaktan kaçın. ZORUNLU karşılıklar:
  * "stop-loss" yerine "zarar kes seviyesi"
  * "trailing stop" yerine "takip eden zarar kes"
  * "earnings" yerine "bilanço açıklaması" veya "kazanç raporu"
  * "drawdown" yerine "zirveden geri çekilme"
  * "concentration" yerine "yoğunlaşma"
  * "exposure" yerine "maruziyet" veya "pozisyon ağırlığı"
  * "long/short" yerine "alış/satış pozisyonu"
  * "P/E ratio" yerine "fiyat-kazanç oranı"
- K-XX gibi kural kodları ZORUNLU yazılır (sistem referansı), ama kuralın anlamını parantezde Türkçe açıkla:
  örn: "K-05 (bilanço öncesi 48 saat çıkış kuralı)"
- Sayıları binlik ayraçla yaz: $135,832 (135832 değil)

JSON güncellemeleri (fiyat/k-z) zaten yapılıyor, rapor bölümlerine yansıt.
Kapanan işlem varsa işlem sonrası analiz ekle.

NAKİT KULLANIM KURALI (ZORUNLU):
- Risk bağlamındaki "NAKİT KULLANIMI" bloğunda 🔴 AŞIM görüyorsan, "yarın aksiyonları"
  bölümünde SOMUT konuşlandırma planı üret (sektör + sembol + tutar).
- "Bekle / pasif" yerine: yükseliş bekleniyorsa fırsat sektörü EKLE/BÜYÜT, geri çekilme
  bekleniyorsa defansif rotasyon (XLP/XLV/GLD/TLT) veya ters yönlü pozisyon (inverse ETF).
- Portföy hedge kuralları: AGRESİF ters pozisyon+put serbest; DENGELİ ters pozisyon max %10
  sadece düşük kaldıraçlı (3x kaldıraçlı YASAK); TEMETTÜ ters pozisyon YASAK.

KESİN / MUHTEMEL / SPEKÜLATİF etiket kullan. Küçük harf Türkçe.
"""

    # ── YENİ: yapılandırılmış karar desteği (Seçenek A) ──────────────────────
    response, claude_kararlar = get_claude_decision_with_actions(prompt, mode="closing")
    save_daily_brief(response, "closing")
    lines = [l.strip() for l in response.split("\n") if l.strip()]
    if lines:
        append_learning(lines[-1], source="closing_analysis")

    # Tam raporu reports/daily/'e kaydet
    _save_report(response, "KAPANIS")

    # Claude kapanış kararlarını kaydet (yarın FAZ_2'de execute edilecek)
    if claude_kararlar:
        # K-05 BILANCO FILTRESI (29 Nis 2026 — FLS bug fix)
        # Closing agent yarinki bilancosu olan sembolleri eklememeli.
        # Aksi halde sabah agent K-05 ile satar = aynı gün al-sat.
        try:
            claude_kararlar = _filtre_k05_bilanco(claude_kararlar, mode="closing")
        except Exception as _k05e:
            print(f"[Orkestratör] K-05 filtre hatası: {_k05e} (devam)")

        import json as _json2
        _ss_path = REPO_ROOT / "data" / "session_state.json"
        try:
            _ss = _json2.load(open(_ss_path)) if _ss_path.exists() else {}
        except Exception:
            _ss = {}
        _ss["claude_kararlar"] = {
            "tarih": datetime.now(TR_TZ).isoformat(),
            "kararlar": claude_kararlar,
            "kaynak": "closing"
        }
        with open(_ss_path, "w") as _f:
            _json2.dump(_ss, _f, ensure_ascii=False, indent=2)
        print(f"[Orkestratör] {len(claude_kararlar)} karar session_state'e kaydedildi.")

    # ── KAPANIS SONRASI TEMA TARAMASI (yarın için aday listesi hazırla) ──────
    try:
        from opportunity_finder import run_theme_scan as _rts_c
        from vix_fetcher import get_vix as _gv_c
        _vix_c, _ = _gv_c()
        _vix_c = _vix_c or 20.0
        print("[Kapanış] Ertesi gün için tema taraması başlıyor...")
        from execution_engine import get_portfolio_status as _gps_c
        for _pf_c in ["aggressive", "balanced", "dividend"]:
            _st_c = _gps_c(_pf_c)
            if _st_c.get("slot", 0) <= 0:
                continue
            _mev_c = _st_c.get("semboller", [])
            _res_c = _rts_c(_pf_c, vix=_vix_c, mevcut_pozlar=_mev_c, min_skor=5.5, max_aday=8)
            print(f"[Kapanış] {_pf_c}: {len(_res_c)} aday hazırlandı")
    except Exception as _tsc:
        print(f"[Kapanış] Tema taraması hatası (tolere): {_tsc}")

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
                    sp_icon = "🟢" if pnl >= 0 else "🔴"
                    # 21 Nisan 2026 politika: gruba stop uzaklik bilgisi
                    # gitmesin (stopa yakin uyari turu). Sadece sembol + P/L.
                    ozet_lines.append(
                        f"  {sp_icon} {sym:5} {pnl:+.1f}%"
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

    # RSI değerlerini JSON'lara cache et (kapanış raporu okuyabilsin)
    # 27 Nis 2026 fix: Önceki kod RSI'ı sadece anlık dict'te kullanıyordu,
    # pozisyon JSON'una yazmıyordu. Closing prompt'unda 'rsi=None' görünüyordu.
    if rsi_map:
        try:
            from datetime import datetime as _dt
            _now_iso = _dt.now(TR_TZ).isoformat()
            for _pf_n in ["balanced","aggressive","dividend"]:
                _pf_path = REPO_ROOT / "data" / "portfolios" / f"{_pf_n}.json"
                if not _pf_path.exists():
                    continue
                _pfd = json.load(open(_pf_path))
                _changed = False
                for _pos in _pfd.get("pozisyonrar" if False else "pozisyonlar", []):
                    _s = _pos.get("sembol")
                    if _s and _s != "_template" and _s in rsi_map:
                        _pos["rsi"] = rsi_map[_s]
                        _pos["rsi_son_guncelleme"] = _now_iso
                        _changed = True
                if _changed:
                    with open(_pf_path, "w", encoding="utf-8") as _f:
                        json.dump(_pfd, _f, ensure_ascii=False, indent=2)
            # Swing'i de güncelle
            _sw_path = REPO_ROOT / "data" / "swing" / "active.json"
            if _sw_path.exists():
                _sw = json.load(open(_sw_path))
                _swc = False
                for _pos in _sw.get("aktif_pozisyonlar", []):
                    _s = _pos.get("sembol")
                    if _s and _s in rsi_map:
                        _pos["rsi"] = rsi_map[_s]
                        _pos["rsi_son_guncelleme"] = _now_iso
                        _swc = True
                if _swc:
                    with open(_sw_path, "w", encoding="utf-8") as _f:
                        json.dump(_sw, _f, ensure_ascii=False, indent=2)
        except Exception as _rcache:
            print(f"[RSI cache] uyarısı: {_rcache}")
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
                    entry  = pos.get("giris_fiyat") or pos.get("giris_fiyati")
                    if sym and cur_p and stop and entry:
                        # K-15c ve K-ZST icin gerekli parametreler
                        entry_date_p = pos.get("giris_tarihi", "")
                        # is_tema_alimi: swing'de gen olmayacak ama portfoy icin geliyor
                        # Burada zaten swing'le calisiyoruz, K-15c portfoy tarafinda
                        is_tema = False
                        exit_r = run_exit_checks(
                            sym, float(cur_p), float(stop), float(entry),
                            rsi=rsi_map.get(sym) or pos.get("rsi", 50),
                            highest_high=pos.get("highest_high"),
                            atr=pos.get("atr_14"),
                            entry_date=entry_date_p,
                            is_tema_alimi=is_tema,
                        )
                        
                        # JUDGEMENT LAYER (28 Nis 2026 reform)
                        # K-06 stop kesin tetikse atla, sadece celisik durumlarda
                        # Claude'a baglam analizi sor.
                        final_action = exit_r["action"]
                        final_reason = exit_r["reason"]
                        layer_used = "kural"
                        if exit_r["action"] in ("EXIT_NOW", "PARTIAL", "WARN") and "K-06" not in exit_r.get("reason", ""):
                            try:
                                from exit_judgement import judge_exit
                                # Pozisyona portfoy bilgisi ekle
                                pos_with_pf = {**pos, "_pf": "swing"}
                                judgement = judge_exit(pos_with_pf, exit_r, "swing")
                                if judgement.get("layer_used") == "llm":
                                    final_action = judgement["action"]
                                    # Reasoning'i markdown-safe yap
                                    _raw = judgement.get("reasoning", "")[:200]
                                    _clean = _raw.replace("*", "").replace("_", "").replace("[", "(").replace("]", ")")
                                    final_reason = f"LLM-{judgement['confidence']}: {_clean}"
                                    layer_used = "llm"
                                    print(f"[Judgement] {sym}: kural={exit_r['action']} → llm={judgement['action']}")
                            except Exception as _je:
                                print(f"[Judgement] {sym} hata: {_je}")
                        
                        # Final action'a göre yaz
                        if final_action in ("EXIT_NOW", "PARTIAL"):
                            aksiyonlar.append(
                                f"{'🔴' if final_action=='EXIT_NOW' else '💰'} "
                                f"*{final_action}* {sym}: {final_reason}"
                                + (f" [{layer_used}]" if layer_used == "llm" else "")
                            )
                        elif final_action == "TIGHTEN":
                            uyarilar.append(
                                f"⚡ *TRAILING GÜNCELLE* {sym}: {final_reason}"
                            )
                        elif final_action == "WARN":
                            uyarilar.append(
                                f"🟡 *UYARI* {sym}: {final_reason}"
                            )
                        elif final_action == "HOLD" and layer_used == "llm":
                            # LLM "tut" dedi — bilgi olarak goster
                            uyarilar.append(
                                f"🤔 *LLM-TUT* {sym}: kural {exit_r['action']} ama context destegi → tut"
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

    # ── 4b. CLAUDE KARAR EXECUTE (kapanış kararları + sabah kararları) ────
    if faz == "FAZ_2":
        try:
            import json as _json3
            _ss_path2 = REPO_ROOT / "data" / "session_state.json"
            if _ss_path2.exists():
                _ss2 = _json3.load(open(_ss_path2))
                _ck  = _ss2.get("claude_kararlar", {})
                if _ck.get("kararlar"):
                    _bugun_str   = datetime.now(TR_TZ).strftime("%Y-%m-%d")
                    _dun_str     = (datetime.now(TR_TZ).date() - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d")
                    _karar_tarih = _ck.get("tarih", "")[:10]
                    # Bugün veya dün kapanış kararlarını bir kez execute et
                    if _karar_tarih in (_bugun_str, _dun_str):
                        if not _ck.get("executed"):
                            print(f"[Monitor] {len(_ck['kararlar'])} Claude kararı execute ediliyor...")
                            try:
                                karar_aks = _execute_claude_decisions(_ck["kararlar"], market)
                                for _msg in karar_aks:
                                    send_private_telegram(_msg)
                                    send_group_telegram(_msg)
                                    aksiyonlar.append(_msg)
                            except Exception as _exec_err:
                                print(f"[Monitor] _execute_claude_decisions hatası: {_exec_err}")
                                karar_aks = []
                            # Execute edildi olarak işaretle — kısmi başarı olsa da
                            # bir sonraki çalışmada çift işlem yapılmasın
                            _ck["executed"] = True
                            _ck["executed_at"] = datetime.now(TR_TZ).isoformat()
                            _ck["executed_count"] = len(karar_aks)
                            _ss2["claude_kararlar"] = _ck
                            with open(_ss_path2, "w") as _ff:
                                _json3.dump(_ss2, _ff, ensure_ascii=False, indent=2)
                            print(f"[Monitor] {len(karar_aks)} karar execute edildi, session_state güncellendi.")
        except Exception as _ce2:
            print(f"[Monitor] Claude karar execute hatası: {_ce2}")

    # ── FAZ_1: AÇILIŞ KONTROL ────────────────────────────────────────────────
    if faz == "FAZ_1":
        faz1_alerts = _run_faz1_checks(portfolios, market)
        uyarilar.extend(faz1_alerts)

    # ── FAZ_3: POWER HOUR FİNAL ──────────────────────────────────────────────
    if faz == "FAZ_3":
        faz3_alerts = _run_faz3_checks(market)
        uyarilar.extend(faz3_alerts)

    # ── 3. PORTFÖY STOP KONTROL (canlı fiyat + gerçek satış) ─────────────────
    # Not: _check_portfolio_exits() da stop kontrolü yapıyor (canlı market dict ile).
    # Bu blok sadece monitor context'teki pozisyon verisinden YAKINI uyarır.
    # Gerçek K-06 satışı _check_portfolio_exits() içinde market dict ile yapılıyor.
    for pf_name, pf_data in portfolios.items():
        for pos in pf_data.get("pozisyonlar", []):
            symbol    = pos.get("sembol", "?")
            stop      = pos.get("stop_loss")
            # Canlı fiyatı market dict'ten al, yoksa dosyadakine bak
            live_q    = market.get(symbol, {})
            cur_price = float(live_q.get("price") or 0) or float(pos.get("guncel_fiyat") or 0)

            if not stop or not cur_price:
                continue

            try:
                stop      = float(stop)
                pct       = (cur_price - stop) / stop * 100

                if cur_price <= stop:
                    # _check_portfolio_exits() canlı market dict ile bu satışı yapıyor.
                    # Burada sadece anlık uyarı loglanır — çift satış önlenir.
                    uyarilar.append(
                        f"🔴 *STOP TETİKLENDİ* [{pf_name.upper()}]\n"
                        f"{symbol}: ${cur_price:.2f} ≤ Stop ${stop:.2f}\n"
                        f"K-06 çıkışı _check_portfolio_exits tarafından işleniyor"
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

    # Uyarılar (stop yakını, trailing güncelle, kritik haber, VIX yüksek vb)
    # 21 Nisan 2026 politika degisikligi: Zeynel "stopa yakin uyari bile
    # gondermene gerek yok" dedi. Uyarilar artik sadece log'a gider,
    # Telegram'a hic gitmez. STOP TETIKLENDI mesajlari _execute_claude_decisions
    # ve _check_portfolio_exits icinde satis aksiyonu olarak zaten
    # DM + Grup'a gidiyor — uyari olarak tekrar gondermeye gerek yok.
    if uyarilar:
        print(f"[Orkestratör] {len(uyarilar)} uyari (log'da, Telegram gonderilmedi):")
        for u in uyarilar:
            # Cok uzun uyarilari kisaltarak log'a yaz
            print(f"  - {u.splitlines()[0][:120]}")

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

    # 27 Nis 2026 fix: duplicate "SWING KAPANDI" spam'ı kaldırıldı.
    # Eski kod: closed.json'daki "bugün kapanan son 3" pozisyonu okuyup her
    # monitor run'unda (30 dk'da bir) tekrar tekrar bildirim üretiyordu —
    # CAT/KLAC/AMAT 14:20'de kapandığı halde 20:33 ve 21:03'te tekrar mesaj
    # geldi (kullanıcı şikayeti, screenshot kanıtlı).
    # Yeni mantık: bildirim TEK noktadan, swing_manager._swing_notify_group
    # içinden, kapanış ANINDA üretilir (commit 50acfac). Burada tekrar
    # üretilmesine gerek yok.

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
    # 30 Nis 2026: TEHLIKELI tema filtresi eklendi (EOG petrol 2/10 alındı sorunu)
    _SEKTOR_TEMA_MAP = {
        "Energy":             "petrol_enerji",
        "Defense":            "savunma",
        "Industrials":        None,  # icinde savunma var ama hep degil
        "Healthcare":         "saglik",
        "Consumer Defensive": "tuketici_temel",
        "Basic Materials":    "altin",  # genelde altin/madencilik
        "Technology":         "ai_yari_iletken",  # bask. AI
        "Utilities":          "elektrik_altyapi",
    }
    _theme_scores_ds = {}
    try:
        import json as _jds
        _ts_path_ds = REPO_ROOT / "data" / "theme_scores.json"
        if _ts_path_ds.exists():
            _ts_data_ds = _jds.load(open(_ts_path_ds))
            _theme_scores_ds = _ts_data_ds.get("temalar", {})
    except Exception:
        pass

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
                        # TEHLIKELI TEMA FILTRESI
                        _sektor = _s.get("sector", "")
                        _tema_key = _SEKTOR_TEMA_MAP.get(_sektor)
                        if _tema_key and _tema_key in _theme_scores_ds:
                            _ts_skor = _theme_scores_ds[_tema_key].get("skor", 5)
                            if _ts_skor <= 2:
                                print(f"[Execution] daily_scan {_s['symbol']} ATLANDI — {_tema_key} TEHLIKELI (skor {_ts_skor}/10)")
                                continue
                        # stop/target boş bırakılıyor — execution buy loop canlı fiyat
                        # üzerinden compute_atr_stop ile yeniden hesaplayacak.
                        buy_list.append({
                            "symbol":  _s["symbol"],
                            "portföy": _pf,
                            "price":   _fiyat,
                            "stop":    0,
                            "target":  0,
                            "reason":  f"daily_scan_{_pf} skor:{_s.get('score')} | {_s.get('sector','')}",
                            "tema":    _s.get("sector", ""),
                        })
            except Exception as _e2:
                print(f"[Execution] daily_scan_{_pf} fallback hatası: {_e2}")
        if buy_list:
            print(f"[Execution] daily_scan fallback: {len(buy_list)} aday yüklendi")

    if not buy_list:
        # Buy list ve daily_scan boşsa → tema bazlı dinamik tarama başlat
        try:
            from opportunity_finder import run_theme_scan
            from vix_fetcher import get_vix as _gv
            _vix_ts, _ = _gv()
            _vix_ts = _vix_ts or 20.0
            print(f"[Execution] buy_list boş — tema taraması başlatılıyor (VIX:{_vix_ts:.1f})")
            for _pf in ["aggressive", "balanced", "dividend"]:
                _status_ts = get_portfolio_status(_pf) if get_portfolio_status else {}
                if _status_ts.get("slot", 0) <= 0:
                    continue
                _mevcut_ts = _status_ts.get("semboller", [])
                _scan_res  = run_theme_scan(_pf, vix=_vix_ts, mevcut_pozlar=_mevcut_ts,
                                             min_skor=5.5, max_aday=10)
                buy_list.extend(_scan_res)
                if _scan_res:
                    print(f"[Execution] {_pf}: {len(_scan_res)} yeni aday bulundu")
        except Exception as _tse:
            print(f"[Execution] Tema taraması hatası: {_tse}")

    if not buy_list:
        return []

    aksiyonlar = []

    # Bugün stop tetiklenen sembolleri ve sektörlerini topla (aynı gün yeniden alım kilidi)
    _bugun_str = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    _bugun_stop_semboller = set()
    _bugun_stop_sektorler = set()
    try:
        import csv as _csv
        _tx_path = REPO_ROOT / "data" / "transactions.csv"
        if _tx_path.exists():
            with open(_tx_path, "r", encoding="utf-8") as _f:
                _rdr = _csv.reader(_f)
                for _row in _rdr:
                    if len(_row) >= 7 and _row[0] == _bugun_str and _row[1] == "SELL":
                        _r_reason = _row[6].lower() if _row[6] else ""
                        if "stop" in _r_reason or "k-06" in _r_reason:
                            _bugun_stop_semboller.add(_row[2])
    except Exception as _e_lock:
        print(f"[Execution] stop kilidi okuma hatası: {_e_lock}")

    # Bugün stop yemiş pozisyonların sektörlerini FMP'den çek
    _FMP_KEY = os.environ.get("FMP_API_KEY", "")
    if _bugun_stop_semboller:
        import requests as _req
        for _stop_sym in _bugun_stop_semboller:
            try:
                _pr = _req.get(
                    "https://financialmodelingprep.com/stable/profile",
                    params={"symbol": _stop_sym, "apikey": _FMP_KEY},
                    timeout=6
                )
                _pd = _pr.json()
                if isinstance(_pd, list) and _pd:
                    _sec = _pd[0].get("sector", "")
                    if _sec:
                        _bugun_stop_sektorler.add(_sec)
            except Exception:
                continue
        print(f"[Execution] Bugün stop tetiklenen: {_bugun_stop_semboller} | sektörler: {_bugun_stop_sektorler}")

    for aday in buy_list[:5]:  # Seans başına max 5 aday değerlendir
        sym     = aday.get("symbol", "")
        portföy = aday.get("portföy", "aggressive")
        target  = float(aday.get("target", 0))
        reason  = aday.get("reason", "")
        tema    = aday.get("tema", "")

        # K-1: Aynı gün stop kilidi (revenge trade önleme)
        if sym in _bugun_stop_semboller:
            print(f"[Execution] {sym}: bugün stop tetiklenmişti, aynı gün yeniden alım kilidi")
            continue

        # K-2: Canlı fiyat FMP'den ZORUNLU çek (previousClose fallback kaldırıldı)
        price, prev_close = fetch_live_price(sym) if fetch_live_price else (None, None)
        if not price or not prev_close:
            print(f"[Execution] {sym}: canlı fiyat alınamadı, alım atlandı")
            continue

        # K-3: Gap-down koruması — açılış dünden %2.5+ aşağıdaysa alım yok
        gap_pct = (price - prev_close) / prev_close * 100
        if gap_pct < -2.5:
            print(f"[Execution] {sym}: gap-down %{gap_pct:.2f} — alım atlandı (gap-down koruması)")
            continue

        # K-4: Aynı sektörde bugün stop olan varsa yarım pozisyona düş
        sektor_penalty = False
        if tema and tema in _bugun_stop_sektorler:
            print(f"[Execution] {sym}: {tema} sektöründe bugün stop var, pozisyon boyutu yarıya iniyor")
            sektor_penalty = True

        # Fiyat sabah önerilen seviyeye yakın mı? (%5 tolerans)
        # Not: %3 çok katıydı — seans içi normal dalgalanmalarda tüm adayları kesiyordu.
        sabah_fiyat = float(aday.get("price", price))
        if sabah_fiyat and abs(price - sabah_fiyat) / sabah_fiyat > 0.05:
            print(f"[Execution] {sym}: fiyat cok kaydi (sabah ${sabah_fiyat:.2f} -> simdi ${price:.2f}, >5% sapma)")
            continue

        # Skor kalite kapisi — dusuk kaliteli adaylari skor uzerinden ele
        # Skor < 4.0 olan adaylar teknik VEYA fundamental cok zayif demektir.
        aday_skor = float(aday.get("score", 99))  # skor yoksa gecir (99 = N/A)
        if aday_skor < 4.0:
            print(f"[Execution] {sym}: skor {aday_skor:.2f} < 4.0 kalite esigi, atlandi")
            continue

        # K-5: ATR14 tabanlı stop — ortak compute_atr_stop helper'ı kullanılır
        _atr_stop, _atr_target, atr14 = compute_atr_stop(sym, price)
        stop = _atr_stop
        if not target or target <= price:
            target = _atr_target
        if atr14:
            print(f"[Execution] {sym}: ATR14={atr14} → stop=${stop:.2f} (-%{(price-stop)/price*100:.2f})")
        else:
            print(f"[Execution] {sym}: ATR çekilemedi, fallback stop=${stop:.2f}")

        # Canlı fiyat zaten stop altına düşmüşse atla
        if price < stop:
            print(f"[Execution] {sym}: fiyat ({price}) stop ({stop}) altına geçmiş, atlandı")
            continue

        # K-engine son kontrol (canlı VIX ile) — merkezi vix_fetcher
        try:
            from vix_fetcher import get_vix
            vix, _ = get_vix()
        except Exception:
            vix = state.get("buy_list", {}).get("vix", 20) if state else 20

        if run_entry_checks:
            _sector_p = tema if tema else ""
            k_res = run_entry_checks(sym, vix=vix, sector=_sector_p, base_size=5000, portfolio=portföy)
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
        # K-4 penalty: aynı sektörde bugün stop yedikse yarım pozisyon
        if sektor_penalty:
            tutar = tutar * 0.5
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
            # buy_candidates.json'dan da çıkar (tema taraması adayı olabilir)
            try:
                _bc_path = REPO_ROOT / "data" / "buy_candidates.json"
                if _bc_path.exists():
                    _bc = json.load(open(_bc_path))
                    _bc["adaylar"] = [a for a in _bc.get("adaylar",[]) if a.get("symbol") != sym]
                    json.dump(_bc, open(_bc_path,"w"), ensure_ascii=False, indent=2)
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

            # K-15c: Tema alimi 15g sonrasi zorunlu cikis incelemesi
            # 28 Nis 2026 backtest: tema alis 5g +%7.45, 10g +%6.39, 20g -%0.86
            # 15. gunden sonra getiri negatife dönüyor.
            try:
                neden_lower = (pos.get("giris_nedeni") or "").lower()
                is_tema = "tema" in neden_lower or "taram" in neden_lower
                if is_tema:
                    giris_t = pos.get("giris_tarihi", "")
                    if giris_t:
                        try:
                            from datetime import datetime as _dt15, timezone as _tz15, timedelta as _td15
                            _tr15 = _tz15(_td15(hours=3))
                            gd = _dt15.strptime(giris_t[:10], "%Y-%m-%d").replace(tzinfo=_tr15)
                            simdi = _dt15.now(_tr15)
                            tutus_gun = (simdi - gd).days
                            # 15+ gün ve kar zaten +%5 üstünde — kar realize et
                            # K-15c THROTTLE (29 Nis 2026): MU'da bugun 11+ kez tetiklendi
                            # cunku her monitor'de 18g+kar%20 hala sagliyor. Bir kez
                            # satildiysa ayni gun bir daha satma.
                            son_k15c = pos.get("son_k15c_tarihi", "")
                            bugun_str = datetime.now(TR_TZ).strftime("%Y-%m-%d")
                            if son_k15c == bugun_str:
                                # Bugun zaten K-15c uygulandi, atla
                                continue
                            if tutus_gun >= 15 and pnl >= 5:
                                # JUDGEMENT LAYER (28 Nis 2026) — LLM'e sor
                                # K-15c tetik ama tema GUCLU + sektor outperform varsa
                                # erken kar alma yapma, momentum binme firsatini kacima
                                k15c_result = {
                                    "action": "PARTIAL",
                                    "pct": 50,
                                    "reason": f"K-15c tema 15g+ kar — %50 cik (gun:{tutus_gun} pnl:+{pnl:.1f}%)"
                                }
                                pf_dec = "PARTIAL"  # default: kurali uygula
                                pf_reason_extra = ""
                                try:
                                    sys.path.insert(0, str(REPO_ROOT / "agent"))
                                    from exit_judgement import judge_exit
                                    pos_with_pf = {**pos, "guncel_fiyat": price}
                                    judgement = judge_exit(pos_with_pf, k15c_result, pf_name)
                                    if judgement.get("layer_used") == "llm":
                                        pf_dec = judgement["action"]
                                        # Reasoning'i temizle (markdown bozucularini kaldir)
                                        _raw_reason = judgement.get("reasoning", "")[:200]
                                        _clean = _raw_reason.replace("*", "").replace("_", "").replace("[", "(").replace("]", ")")
                                        pf_reason_extra = f"LLM-{judgement['confidence']}: {_clean}"
                                        print(f"[Judgement] {pf_name}/{sym} K-15c: kural=PARTIAL → llm={pf_dec}")
                                except Exception as _je:
                                    print(f"[Judgement] {pf_name}/{sym} hata: {_je}")
                                
                                # LLM 'HOLD' dediyse satış yapma, sadece bilgi
                                if pf_dec == "HOLD":
                                    msg = (
                                        f"🤔 *K-15c LLM-TUT* [{pf_name.upper()}]\n"
                                        f"{sym} @${price:.2f} | tutus {tutus_gun}g | P/L: {pnl:+.1f}%\n"
                                        f"→ Kural %50 satis dedi ama LLM tema/momentum destegi gordu, tut\n"
                                    )
                                    if pf_reason_extra:
                                        msg += f"_{pf_reason_extra}_"
                                    aksiyonlar.append(msg)
                                    continue
                                
                                # Yüksekli partial önerirse pct değiş
                                if pf_dec == "PARTIAL_25":
                                    pct = 25
                                elif pf_dec == "PARTIAL_50":
                                    pct = 50
                                elif pf_dec == "EXIT_NOW":
                                    pct = 100
                                else:
                                    pct = 50  # K-15c default
                                
                                # sell_position reason'da kisa ozet
                                _sat_reason = f"K-15c tema 15g cikis: tutus {tutus_gun}g, kar +%{pnl:.1f}"
                                if pf_reason_extra:
                                    _sat_reason += f" ({pf_reason_extra[:80]})"
                                result = sell_position(sym, pf_name, _sat_reason,
                                       pct=pct, price=price)
                                if result.get("ok"):
                                    # K-15c throttle: kalan pozisyona bugun tarihi yaz
                                    # (bir sonraki monitor ayni gun tekrar tetiklemesin)
                                    try:
                                        import json as _jk15
                                        _pf_path = REPO_ROOT / "data" / "portfolios" / f"{pf_name}.json"
                                        if _pf_path.exists():
                                            _pf_d = _jk15.load(open(_pf_path))
                                            for _p in _pf_d.get("pozisyonlar", []):
                                                if _p.get("sembol") == sym:
                                                    _p["son_k15c_tarihi"] = datetime.now(TR_TZ).strftime("%Y-%m-%d")
                                                    break
                                            with open(_pf_path, "w") as _ff:
                                                _jk15.dump(_pf_d, _ff, ensure_ascii=False, indent=2)
                                    except Exception as _k15e:
                                        print(f"[K-15c] Throttle yazimi hatasi: {_k15e}")
                                    msg = (
                                        f"🟡 *K-15c TEMA 15G+ CIKIS* [{pf_name.upper()}]\n"
                                        f"{sym} @${price:.2f} | tutus {tutus_gun}g | P/L: {pnl:+.1f}%\n"
                                        f"→ *%{pct} SAT*"
                                    )
                                    if pf_reason_extra:
                                        msg += f"\n_{pf_reason_extra}_"
                                    aksiyonlar.append(msg)
                                    continue
                            # 20+ gün ve kar negatif — komple cik (zaten beklemenin anlami yok)
                            elif tutus_gun >= 20 and pnl < 0:
                                result = sell_position(sym, pf_name,
                                       f"K-15c tema 20g+ negatif: tutus {tutus_gun}g, K/Z %{pnl:.1f}",
                                       pct=100, price=price)
                                if result.get("ok"):
                                    aksiyonlar.append(
                                        f"🔴 *K-15c TEMA 20G+ TAM CIKIS* [{pf_name.upper()}]\n"
                                        f"{sym} @${price:.2f} | tutus {tutus_gun}g | P/L: {pnl:+.1f}%\n"
                                        f"→ *TAM SATIS {result.get('adet','?')} adet*"
                                    )
                                    continue
                        except Exception as _k15e:
                            pass
            except Exception as _k15ee:
                pass

            # K-06: Stop tetiklendi
            if price <= stop:
                result = sell_position(sym, pf_name,
                                       f"K-06 stop tetiklendi ${price:.2f}≤${stop:.2f}",
                                       pct=100, price=price)
                if result["ok"]:
                    aksiyonlar.append(
                        f"🔴 *K-06 STOP* [{pf_name.upper()}]\n"
                        f"{sym} @${price:.2f} | P/L: {pnl:+.1f}%\n"
                        f"→ *SAT {result['adet']} ADET*"
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
                        f"→ *SAT {result['adet']} ADET*"
                    )

    return aksiyonlar


def _check_swing_entries() -> list[str]:
    """
    Swing giriş sinyallerini kontrol et.
    Uygun koşul varsa JSON'a yaz + aksiyon mesajı döndür.
    """
    import sys as _sys
    _sys.path.insert(0, str(REPO_ROOT / "scripts"))
    _sys.path.insert(0, str(REPO_ROOT / "agent"))
    try:
        from swing_manager import SWING_MAX_POSITIONS as _SWING_MAX
    except ImportError:
        _SWING_MAX = 5  # Fallback

    aksiyonlar = []

    # K-23 DRAWDOWN GUARD KONTROLU (28 Nis 2026)
    # Eger toplam veya aggressive drawdown >=%10 ise YENI SWING GIRISI YOK
    try:
        from portfolio_drawdown_guard import analiz_yap as _k23_analiz
        _k23_s = _k23_analiz()
        _agg_kod = _k23_s["portfoyler"].get("aggressive", {}).get("k23", {}).get("kod", 0)
        _toplam_kod = _k23_s["toplam"]["k23"]["kod"]
        _max_kod = max(_agg_kod, _toplam_kod)
        if _max_kod >= 2:  # DEFANSIF veya daha yuksek
            seviye = _k23_s["toplam"]["k23"]["seviye"]
            return [f"⚠️ *K-23 SWING GIRIS DURDURULDU*: {seviye} seviyesi — yeni swing girisi yok"]
    except Exception as _k23e:
        print(f"[K-23 swing check] {_k23e}")

    # Kapasite kontrol
    active = json.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
    mevcut_poz = len(active.get("aktif_pozisyonlar", []))
    if mevcut_poz >= _SWING_MAX:
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

    # Zaten açık olanları listeden çıkar
    # 27 Nis 2026 fix: Eski kod '[:3]' ile sabit ilk-3-kontrol limiti vardı.
    # 7 sinyal geldi (CAT/RPRX/TFC/NNE/UEC/LEU/DNN), aktif RPRX hariç 6 sinyal,
    # [:3] sadece CAT/TFC/NNE'yi kontrol etti. UEC/LEU/DNN hiç bakılmadı.
    # CAT bugün kapanmış (analiz reddetti), TFC+NNE açıldı (4/5). 1 slot
    # boş kaldığı halde DNN sonraki monitor'larda da hep [:3]'ün dışında
    # kalıp atlandı.
    # Yeni mantık: tüm sinyalleri sırayla kontrol et, içerideki
    # 'mevcut_poz >= 5' break'i zaten kapasiteyi koruyor.
    aktif_semboller = {p.get("sembol") for p in active.get("aktif_pozisyonlar", [])}
    kontrol_listesi = [s for s in giris_syms if s not in aktif_semboller]

    for sym in kontrol_listesi:
        # Kapasite yeterliyse devam
        if mevcut_poz >= _SWING_MAX:
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

    # NOT: Burada commit/push YAPILMAZ.
    # 21 Nisan 2026 bug: _save_report kendi commit+push'unu deniyordu ama
    # subprocess.run(..., capture_output=True) returncode kontrol edilmedigi
    # icin push sessizce basarisiz olabiliyordu. Sonra workflow'un
    # "Degisiklikleri kaydet" adimi `git reset --hard origin/main` ile
    # commit'i silip DAILY_SABAH dosyasini diskten kaldiriyordu.
    # Cozum: Raporu sadece diske yaz, commit/push'u workflow'un sonundaki
    # toplu "Degisiklikleri kaydet" adimina birak (reports/ klasoru zaten
    # `git add reports/` ile yakalaniyor).

def _flag_for_commit():
    """Swing değişikliği oldu — kapanışta commit edilecek."""
    flag = REPO_ROOT / "data" / ".swing_updated"
    flag.write_text(datetime.now().isoformat())

def run_weekly(ctx: dict):
    """Pazar günü haftalık derin analiz + öğrenme + Darwin evrimi."""
    print("[Orkestratör] Haftalık mod çalışıyor...")

    # Duplicate-guard: bugunku haftalik rapor zaten yazildiysa cik.
    # Dosya formati: reports/weekly/WEEKLY_YYYY_MM_DD.md (underscore)
    try:
        _tarih = datetime.now(TR_TZ).strftime("%Y_%m_%d")
        _bugunku_hrapor = REPO_ROOT / "reports" / "weekly" / f"WEEKLY_{_tarih}.md"
        _force = os.environ.get("FORCE_WEEKLY", "").strip().lower() in ("1", "true", "yes")
        if _bugunku_hrapor.exists() and not _force:
            print(f"[Weekly] {_bugunku_hrapor.name} zaten mevcut — atlaniyor (FORCE_WEEKLY=1 ile zorlanir).")
            return
    except Exception as _dg:
        print(f"[Weekly] Duplicate guard uyarisi: {_dg} (devam ediliyor)")

    learning_ctx  = build_weekly_learning_context()
    trade_stats   = analyze_closed_trades(days_back=7)
    update_k_rule_stats(trade_stats)
    backtest      = run_full_backtest()
    backtest_ctx  = format_backtest_for_claude(backtest)
    applied_log   = get_applied_changes_summary()
    screener_rpt  = run_screener_optimization()

    # K-Kurallari Backtest (28 Nis 2026 — haftalik otomatik update)
    # transactions.csv'yi kategoriye gore analiz eder, her K-kuralin
    # gercek getirisini olcer. Sonuc data/backtest_summary.json ve
    # reports/backtest/k_rules_YYYY-MM-DD.md'ye yazilir.
    # Morning prompt'u her sabah bunu okur (risk_engine'de).
    try:
        import subprocess
        _bt_cmd = ["python3", str(REPO_ROOT / "scripts" / "k_rules_backtest.py"), "--save"]
        _bt_proc = subprocess.run(_bt_cmd, capture_output=True, text=True, timeout=300)
        if _bt_proc.returncode == 0:
            print("[Weekly] K-kurallari backtest yenilendi")
            # Telegram'a ozet (DM, info severity)
            try:
                import json as _j_bt
                _bt_path = REPO_ROOT / "data" / "backtest_summary.json"
                if _bt_path.exists():
                    _bts = _j_bt.load(open(_bt_path))
                    _bt_lines = ["📊 K-KURALLARI HAFTALIK BACKTEST"]
                    for _r in _bts.get("raporlar", []):
                        if _r.get("sayi", 0) == 0:
                            continue
                        _g5 = _r.get("g5_avg_pct")
                        _g20 = _r.get("g20_avg_pct")
                        if _g5 is None:
                            continue
                        _g5s = f"{_g5:+.1f}%"
                        _g20s = f"{_g20:+.1f}%" if _g20 is not None else "—"
                        _bt_lines.append(f"  {_r['kategori']:14} ({_r['sayi']:>2}): 5g {_g5s} | 20g {_g20s}")
                    print("\n".join(_bt_lines))
            except Exception as _bts_e:
                print(f"[Weekly] Backtest ozet uyarisi: {_bts_e}")
        else:
            print(f"[Weekly] K-kurallari backtest hata: {_bt_proc.stderr[:200]}")
    except Exception as _bte:
        print(f"[Weekly] K-kurallari backtest exception: {_bte}")

    # Discovery Engine — kaliteli yeni adaylar (28 Nis 2026)
    # daily_full_scan'den 1240 hisseyi swing kalite filtresinden gecirir.
    # Pazar 12:00'de calisir, sonuclari data/discovery_signals.json'a yazar
    # ve Telegram DM'e en iyi 10'u gonderir.
    try:
        import subprocess
        _disc_cmd = ["python3", str(REPO_ROOT / "scripts" / "discovery_engine.py"),
                     "--save", "--telegram", "--limit", "200"]
        # 200 hisse limit (10-15 dk surer), tum 476 icin --limit kaldir
        _disc_proc = subprocess.run(_disc_cmd, capture_output=True, text=True, 
                                     timeout=1800, env=os.environ)
        if _disc_proc.returncode == 0:
            print("[Weekly] Discovery engine tamamlandi")
            # Stdout'tan ozet
            for line in _disc_proc.stdout.split("\n")[-15:]:
                if line.strip():
                    print(f"  {line}")
        else:
            print(f"[Weekly] Discovery hata: {_disc_proc.stderr[:200]}")
    except Exception as _disce:
        print(f"[Weekly] Discovery exception: {_disce}")

    # Theme Tracker — haftalik tema skorları (28 Nis 2026)
    try:
        import subprocess
        _th_proc = subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "theme_tracker.py"), "--update"],
            capture_output=True, text=True, timeout=300, env=os.environ
        )
        if _th_proc.returncode == 0:
            print("[Weekly] Tema skorları guncellendi")
            # Telegram DM'e ozet
            try:
                _th_path = REPO_ROOT / "data" / "theme_scores.json"
                if _th_path.exists():
                    _th = json.load(open(_th_path))
                    _msg_lines = ["📊 *TEMA SKORLARI HAFTALIK*"]
                    _sorted_t = sorted(_th.get("temalar", {}).values(),
                                       key=lambda x: -x["skor"])
                    for _t in _sorted_t:
                        _emoji = {"GUCLU":"🟢","ORTA":"🟡","ZAYIF":"🟠","TEHLIKELI":"🔴"}.get(_t["seviye"], "⚪")
                        _msg_lines.append(f"{_emoji} {_t['skor']:>2}/10 {_t['ad']:25} RS:{_t.get('rs_vs_spy',0):+.1f}%")
                    print("\n".join(_msg_lines))
            except Exception as _the2:
                print(f"[Weekly] Tema ozet hatasi: {_the2}")
        else:
            print(f"[Weekly] Theme tracker hata: {_th_proc.stderr[:200]}")
    except Exception as _the3:
        print(f"[Weekly] Theme tracker exception: {_the3}")

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

{ctx['thematic']}

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
6.5. Tematik katalist review (yukarıdaki "Tematik Durum" bloğu DOLUYSA veya bu hafta yaşandıysa):
     - Hafta içi tetiklenen etkinlikler ve piyasa tepkileri
     - Finzora tarafından yakalanan fırsatlar ve kaçırılanlar
     - Sıradaki 2 hafta için tematik takvim öngörüsü
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
        # NOT: Commit/push buradan kaldirildi (21 Nisan 2026 bug).
        # Workflow'un "Degisiklikleri kaydet" adimi `git add reports/`
        # ile zaten toplu commit ediyor. Burada extra commit + push
        # capture_output=True nedeniyle sessizce basarisiz olabiliyor.
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


# ═══════════════════════════════════════════════════════════════════════════
# CLAUDE KARAR EXECUTOR — Seçenek A: Yapısal Claude → Execution bağlantısı
# ═══════════════════════════════════════════════════════════════════════════

def _execute_claude_decisions(kararlar: list, market: dict) -> list:
    """
    Claude'un ürettiği yapılandırılmış kararları execute eder.
    get_claude_decision_with_actions() çıktısını alır.

    Desteklenen tipler: EKLE, BÜYÜT, ÇIK, DÖNDÜR, STOP_GÜNCELLE, İZLE

    Decision → execution loop'u kapatmak için her karar sonrası
    observability.update_decision_executed çağrılır. Böylece
    query_decision_hitrate anlamlı çalışır.
    """
    if not kararlar:
        return []
    if not buy_position or not sell_position:
        print("[Decisions] execution_engine yüklenemedi, kararlar atlandı.")
        return []

    # Observability update helper (opsiyonel — modül yoksa no-op)
    try:
        from observability import update_decision_executed as _upd_dec
    except ImportError:
        _upd_dec = lambda *a, **kw: None

    def _mark(k: dict, executed: bool, reason: str | None = None):
        did = k.get("_decision_id")
        if did:
            try:
                _upd_dec(did, executed=executed, skipped_reason=reason)
            except Exception as _e:
                print(f"[Decisions] decision update atlandı: {_e}")

    aksiyonlar = []

    for k in kararlar:
        tip       = k.get("tip", "").upper()
        portfoy   = k.get("portfoy", "")
        sembol    = k.get("sembol", "")
        pct       = float(k.get("pct", 100))
        neden     = k.get("neden", "Claude kararı")
        stop      = float(k.get("stop") or 0)
        hedef     = float(k.get("hedef_fiyat") or 0)
        tutar     = float(k.get("tutar") or 0)
        aciliyet  = k.get("aciliyet", "bugün")
        dondur_al = k.get("dondur_al")

        if not sembol or not portfoy:
            _mark(k, False, "eksik_sembol_veya_portfoy")
            continue

        # Güncel fiyat — canlı fiyat öncelikli, DNS sorunu durumunda portföy fiyatı son çare
        price = 0.0
        if fetch_live_price:
            _p, _ = fetch_live_price(sembol)
            if _p:
                price = float(_p)
        if not price:
            # Market dict'te canlı price (previousClose'u asla kabul etme)
            q = market.get(sembol, {})
            if q.get("price"):
                price = float(q["price"])
        if not price and tip == "ÇIK":
            # ÇIK kararı için son çare: portföy dosyasındaki guncel_fiyat
            # (DNS/503 durumunda satışın tamamen engellenmesini önler)
            try:
                _pf_alias = {"agresif":"aggressive","büyüme":"aggressive",
                             "temettü":"dividend","temettu":"dividend","gelir":"dividend",
                             "dengeli":"balanced"}
                _pf_key = _pf_alias.get(portfoy.lower(), portfoy.lower())
                _pf_path = REPO_ROOT / "data" / "portfolios" / f"{_pf_key}.json"
                _pf_data = json.load(open(_pf_path))
                _poz = next((p for p in _pf_data.get("pozisyonlar",[]) if p["sembol"]==sembol), None)
                if _poz and _poz.get("guncel_fiyat"):
                    price = float(_poz["guncel_fiyat"])
                    print(f"[Decisions] {sembol} portföy fiyatı kullanıldı: ${price:.2f} (FMP ulaşılamıyor)")
            except Exception as _pf_e:
                print(f"[Decisions] {sembol} portföy fiyat fallback hatası: {_pf_e}")
        if not price:
            print(f"[Decisions] {sembol} canlı fiyat alınamadı, atlandı.")
            _mark(k, False, "canli_fiyat_alinamadi")
            continue


        try:
            if tip == "ÇIK":
                result = sell_position(sembol, portfoy, f"Finzora: {neden}", pct=pct, price=price)
                if result["ok"]:
                    _mark(k, True)
                    aksiyonlar.append(
                        f"🔴 *FINZORA SAT* [{portfoy.upper()}]\n"
                        f"{sembol} %{pct:.0f} @${price:.2f} | P/L: {result.get('pnl_pct',0):+.1f}%\n"
                        f"Neden: {neden}"
                    )
                else:
                    _mark(k, False, result.get("hata", "sell_basarisiz"))

            elif tip in ("EKLE", "BÜYÜT"):
                # Nakit kontrolü
                status = get_portfolio_status(portfoy) if get_portfolio_status else {}
                nakit  = float(status.get("nakit", tutar or 10000))
                miktar = tutar if tutar > 0 else min(nakit * 0.25, 15000, nakit)
                if miktar < 500:
                    print(f"[Decisions] {portfoy} yetersiz nakit ({nakit:.0f}$), {sembol} atlandı.")
                    _mark(k, False, f"yetersiz_nakit_${nakit:.0f}")
                    continue

                # K-engine kontrolü
                # BÜYÜT için K-17 atlanir (zaten portföyde olmasi normal,
                # büyütme aslen ekleme degil adet artirma).
                if run_entry_checks:
                    try:
                        from vix_fetcher import get_vix
                        vix, _ = get_vix()
                    except Exception:
                        vix = 20.0
                    k_res = run_entry_checks(sembol, vix=vix, base_size=5000, portfolio=portfoy)
                    # BÜYÜT'te K-17 veto'sunu gormezden gel (zaten portföyde olmasi gereken durum)
                    if not k_res["go"] and tip == "BÜYÜT" and "K-17:" in k_res.get("fail_reason", "") and "zaten portföyde" in k_res.get("fail_reason", ""):
                        print(f"[Decisions] BÜYÜT için K-17 veto görmezden gelindi: {sembol}")
                        # Devam et
                    elif not k_res["go"]:
                        print(f"[Decisions] {sembol} K-engine veto: {k_res['fail_reason']}")
                        _mark(k, False, f"k_engine_veto: {k_res['fail_reason'][:80]}")
                        continue

                # Stop/hedef yoksa ATR14 bazlı hesapla (kör %8/%15 fallback yasak)
                if not stop or not hedef or stop >= price or hedef <= price:
                    try:
                        from execution_engine import compute_atr_stop as _cas
                        _stop, _hedef, _ = _cas(sembol, price)
                        if not stop or stop >= price:
                            stop = _stop
                        if not hedef or hedef <= price:
                            hedef = _hedef
                    except Exception as _e_s:
                        print(f"[Decisions] {sembol} ATR stop hesaplanamadı ({_e_s}), fallback %8")
                        if not stop or stop >= price:
                            stop = round(price * 0.92, 2)
                        if not hedef or hedef <= price:
                            hedef = round(price * 1.12, 2)

                result = buy_position(sembol, portfoy, miktar, price,
                                      stop, hedef,
                                      f"Finzora: {neden}", "")
                if result["ok"]:
                    _mark(k, True)
                    aksiyonlar.append(
                        f"🟢 *FINZORA AL* [{portfoy.upper()}]\n"
                        f"{sembol} {result['adet']} adet @${price:.2f}\n"
                        f"Stop: ${stop:.2f} | Hedef: ${hedef:.2f}\n"
                        f"Neden: {neden}"
                    )
                else:
                    _mark(k, False, result.get("hata", "buy_basarisiz"))

            elif tip == "DÖNDÜR":
                # Adım 1: Sat
                sat_r = sell_position(sembol, portfoy, f"DÖNDÜR — {neden}", pct=pct, price=price)
                if not sat_r["ok"]:
                    print(f"[Decisions] DÖNDÜR satış başarısız: {sat_r.get('hata','?')}")
                    _mark(k, False, f"dondur_sat_basarisiz: {sat_r.get('hata','?')}")
                    continue

                pnl_pct = sat_r.get("pnl_pct", 0)
                kazanilan = sat_r["tutar"]

                # Adım 2: Al (dondur_al varsa)
                if dondur_al:
                    # Canlı fiyat FMP'den ZORUNLU — previousClose fallback yasak
                    try:
                        from execution_engine import fetch_live_price as _flp
                        al_price, _al_prev = _flp(dondur_al)
                    except Exception:
                        al_price, _al_prev = None, None

                    if not al_price:
                        # Market dict'te canlı fiyat varsa kullan (previousClose'u kabul etme)
                        al_q  = market.get(dondur_al, {})
                        _p    = al_q.get("price")
                        if _p:
                            al_price = float(_p)
                            _al_prev = float(al_q.get("previousClose") or 0)

                    # Gap-down koruması (aynı sembol bug'ı tekrar yaşamasın)
                    if al_price and _al_prev:
                        _gap = (al_price - _al_prev) / _al_prev * 100
                        if _gap < -2.5:
                            print(f"[Decisions] DÖNDÜR alış {dondur_al}: gap-down %{_gap:.2f}, alım atlandı")
                            _mark(k, True, f"dondur_al_gap_down_{_gap:.1f}%")
                            aksiyonlar.append(
                                f"🔄 *DÖNDÜR SATIŞ TAMAM* [{portfoy.upper()}]\n"
                                f"{sembol} @${price:.2f} P/L:{pnl_pct:+.1f}% | ${kazanilan:,.0f}\n"
                                f"⚠️ {dondur_al} alış gap-down koruması ile atlandı (%{_gap:.2f})"
                            )
                            continue

                    if al_price:
                        # K-engine kontrolü (döndür alışı için de)
                        if run_entry_checks:
                            try:
                                from vix_fetcher import get_vix
                                vix, _ = get_vix()
                            except Exception:
                                vix = 20.0
                            k_res2 = run_entry_checks(dondur_al, vix=vix, base_size=5000, portfolio=portfoy)
                            if not k_res2["go"]:
                                print(f"[Decisions] DÖNDÜR alış {dondur_al} K-veto: {k_res2['fail_reason']}")
                                _mark(k, True, f"dondur_al_k_veto: {k_res2['fail_reason'][:80]}")
                                aksiyonlar.append(
                                    f"🔄 *DÖNDÜR SATIŞ TAMAM* [{portfoy.upper()}]\n"
                                    f"{sembol} @${price:.2f} P/L:{pnl_pct:+.1f}% | ${kazanilan:,.0f}\n"
                                    f"⚠️ {dondur_al} alış K-veto: {k_res2['fail_reason']}"
                                )
                                continue

                        # ATR14 bazlı stop/hedef (kör %8/%15 fallback yasak)
                        try:
                            from execution_engine import compute_atr_stop as _cas2
                            _al_stop, _al_tgt, _ = _cas2(dondur_al, al_price)
                        except Exception:
                            _al_stop = round(al_price * 0.92, 2)
                            _al_tgt  = round(al_price * 1.12, 2)

                        al_r = buy_position(dondur_al, portfoy, kazanilan, al_price,
                                            _al_stop, _al_tgt,
                                            f"DÖNDÜR giriş — {neden}", "")
                        if al_r["ok"]:
                            _mark(k, True)
                            aksiyonlar.append(
                                f"🔄 *DÖNDÜR* [{portfoy.upper()}]\n"
                                f"SAT: {sembol} @${price:.2f} P/L:{pnl_pct:+.1f}%\n"
                                f"AL:  {dondur_al} {al_r['adet']} adet @${al_price:.2f}\n"
                                f"Neden: {neden}"
                            )
                        else:
                            # Sat kısmı oldu, al başarısız — kısmi kabul
                            _mark(k, True, f"al_kismi_basarisiz: {al_r.get('hata','?')}")
                            aksiyonlar.append(
                                f"🔄 *DÖNDÜR — KISMÎ* [{portfoy.upper()}]\n"
                                f"SAT: {sembol} OK | AL: {dondur_al} başarısız\n"
                                f"${kazanilan:,.0f} nakite döndü"
                            )
                    else:
                        # Sat oldu, al fiyatı yok — kısmi kabul
                        _mark(k, True, f"al_fiyati_yok: {dondur_al}")
                        aksiyonlar.append(
                            f"🔄 *DÖNDÜR — KISMÎ* [{portfoy.upper()}]\n"
                            f"SAT: {sembol} @${price:.2f} OK | {dondur_al} fiyat alınamadı\n"
                            f"${kazanilan:,.0f} nakite döndü"
                        )
                else:
                    # dondur_al yok → sadece sat, bu da executed sayılır
                    _mark(k, True)
                    aksiyonlar.append(
                        f"🔄 *DÖNDÜR SATIŞ* [{portfoy.upper()}]\n"
                        f"{sembol} @${price:.2f} P/L:{pnl_pct:+.1f}% | ${kazanilan:,.0f}\n"
                        f"Neden: {neden}"
                    )

            elif tip == "STOP_GÜNCELLE":
                # JSON dosyasını doğrudan güncelle — stop_mesafe_pct, son_guncelleme de tazelensin
                pf_path = REPO_ROOT / "data" / "portfolios" / f"{portfoy}.json"
                if pf_path.exists() and stop > 0:
                    import json as _json
                    pf_data = _json.load(open(pf_path))
                    touched = False
                    for poz in pf_data.get("pozisyonlar", []):
                        if poz["sembol"] == sembol:
                            poz["stop_loss"] = stop
                            cur = float(poz.get("guncel_fiyat") or 0)
                            if cur:
                                poz["stop_mesafe_pct"] = round((cur - stop) / cur * 100, 2)
                            poz["son_guncelleme"] = datetime.now(TR_TZ).strftime("%Y-%m-%d")
                            touched = True
                    if touched:
                        with open(pf_path, "w") as f:
                            _json.dump(pf_data, f, ensure_ascii=False, indent=2)
                        _mark(k, True)
                        aksiyonlar.append(
                            f"⚡ *STOP GÜNCELLE* [{portfoy.upper()}]\n"
                            f"{sembol} stop → ${stop:.2f}\nNeden: {neden}"
                        )
                    else:
                        _mark(k, False, f"sembol_pozisyonda_yok: {sembol}")
                else:
                    _mark(k, False, "stop_degeri_gecersiz_veya_dosya_yok")

            elif tip == "İZLE":
                # İZLE bir no-op karar — "yürütüldü" sayılır (gözlem kararı verildi).
                _mark(k, True, "izle_karari")
                print(f"[Decisions] İZLE: {portfoy} {sembol} — {neden}")

        except Exception as exc:
            print(f"[Decisions] {tip} {sembol} hata: {exc}")
            _mark(k, False, f"exception: {str(exc)[:100]}")

    return aksiyonlar


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — TÜM FONKSİYONLAR TANIMLANDIKTAN SONRA
# ═══════════════════════════════════════════════════════════════════════════
# 28 Nis 2026 düzeltme: Önceden 'if __name__ == "__main__"' bloğu modulün
# ortasındaydı (2263. satır). _execute_claude_decisions 2284'te tanımlı
# olduğu için main() çağrıldığında o fonksiyon henüz tanımlanmamış oluyordu.
# Hata: "name '_execute_claude_decisions' is not defined".
# Çözüm: main entry point'i dosyanın EN SONUNA taşı.
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
