#!/usr/bin/env python3
"""
Finzora Agent — Bellek Yönetimi (Memory Layer)
================================================
Claude'un çağrılar arası hafızası yok.
Bu modül dosya sistemiyle kalıcı bellek sağlar.

Mantık:
  - Her kapanış → Claude özet yazar → memory/daily_brief.json
  - Her sabah → özet okunur → Claude bağlamı hatırlamış gibi davranır
  - Tam JSON/Playbook yerine sıkıştırılmış özet gider → 10x ucuz

Bellek katmanları:
  L1 - portfolio_state.json  → Anlık kritik metrikler (her çağrıda)
  L2 - daily_brief.json      → Dünden bugüne özet (sabah/kapanış)
  L3 - k_rules_digest.md     → K-kuralları özeti (statik, haftalık güncellenir)
  L4 - learning_log.json     → Birikim hafıza (haftalık büyür)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytz

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"
TR_TZ      = pytz.timezone("Europe/Istanbul")

MEMORY_DIR.mkdir(exist_ok=True)


# ── L1: Portföy Durumu (anlık, her çağrıda yenilenir) ────────────────────────

def build_portfolio_state(portfolios: dict, market: dict) -> dict:
    """
    Tam JSON yerine sadece kritik metrikler.
    ~300 token.
    """
    state = {
        "timestamp": datetime.now(TR_TZ).isoformat(),
        "market": {
            "SPY":  market.get("SPY", {}).get("price"),
            "QQQ":  market.get("QQQ", {}).get("price"),
            "VIXY": market.get("VIXY", {}).get("price"),
            "GLD":  market.get("GLD", {}).get("price"),
            "spy_chg":  market.get("SPY", {}).get("chg"),
            "qqq_chg":  market.get("QQQ", {}).get("chg"),
        },
        "portfolios": {}
    }

    for pf_name, pf_data in portfolios.items():
        pozisyonlar = pf_data.get("pozisyonlar", [])
        pf_state    = {
            "toplam_deger":   pf_data.get("toplam_deger"),
            "getiri_yuzde":   pf_data.get("toplam_getiri_yuzde"),
            "pozisyon_sayisi": len(pozisyonlar),
            "pozisyonlar": []
        }

        for pos in pozisyonlar:
            sym        = pos.get("sembol") or pos.get("symbol", "?")
            cur_price  = pos.get("guncel_fiyat") or pos.get("son_fiyat")
            stop       = pos.get("stop_loss")
            maliyet    = pos.get("maliyet_bazis")
            hedef      = pos.get("hedef_fiyat")
            adet       = pos.get("adet") or pos.get("shares", 0)

            # Stop mesafesi hesapla
            stop_pct = None
            if stop and cur_price:
                try:
                    stop_pct = round((float(cur_price) - float(stop)) / float(stop) * 100, 1)
                except (ValueError, TypeError):
                    pass

            # Kar/zarar hesapla
            pnl_pct = None
            if maliyet and cur_price:
                try:
                    pnl_pct = round((float(cur_price) - float(maliyet)) / float(maliyet) * 100, 1)
                except (ValueError, TypeError):
                    pass

            pf_state["pozisyonlar"].append({
                "sym":       sym,
                "fiyat":     cur_price,
                "gunluk":    pos.get("gunluk_degisim"),
                "pnl_pct":   pnl_pct,
                "stop_pct":  stop_pct,   # stop'a uzaklık — negatifse geçilmiş
                "hedef":     hedef,
            })

        state["portfolios"][pf_name] = pf_state

    return state


def save_portfolio_state(state: dict):
    path = MEMORY_DIR / "portfolio_state.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_portfolio_state() -> dict:
    path = MEMORY_DIR / "portfolio_state.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── L2: Günlük Brief (Claude kendisi yazar) ───────────────────────────────────

def load_daily_brief() -> str:
    """Dünkü/bugünkü Claude özetini yükler."""
    path = MEMORY_DIR / "daily_brief.json"
    if not path.exists():
        return "Henüz brief yok — ilk çalışma."

    with open(path, encoding="utf-8") as f:
        brief = json.load(f)

    # 2 günden eskiyse geçersiz say
    ts = brief.get("timestamp", "")
    if ts:
        try:
            brief_time = datetime.fromisoformat(ts)
            if (datetime.now(TR_TZ) - brief_time).days > 2:
                return "Brief güncel değil (2+ gün eski)."
        except ValueError:
            pass

    return brief.get("content", "Brief içeriği boş.")


def save_daily_brief(claude_response: str, mode: str):
    """
    Claude'un kapanış/sabah analizini kaydeder.
    Bir sonraki çağrıda bağlam olarak kullanılır.
    """
    path = MEMORY_DIR / "daily_brief.json"

    # Mevcut brief varsa son 3'ü tut
    history = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
        history = existing.get("history", [])

    # Yeni brief
    brief = {
        "timestamp": datetime.now(TR_TZ).isoformat(),
        "mode":      mode,
        "content":   claude_response[:2000],  # Max 2000 karakter
        "history":   history[-2:]             # Son 2 brief'i tut
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)


# ── L3: K-Kuralları Özeti (statik, haftalık güncellenir) ─────────────────────

def get_k_rules_digest() -> str:
    """
    Tam TRADING_PLAYBOOK.md yerine sıkıştırılmış özet.
    İlk yoksa otomatik oluşturur.
    """
    path = MEMORY_DIR / "k_rules_digest.md"

    if path.exists():
        return path.read_text(encoding="utf-8")

    # Playbook'tan otomatik özet çıkar (ilk kez)
    playbook_path = REPO_ROOT / "docs" / "TRADING_PLAYBOOK.md"
    if not playbook_path.exists():
        return "K-kuralları bulunamadı."

    # Statik özet yaz (manuel, değişmez — haftalık Claude günceller)
    digest = """# K-KURALLARI ÖZET (Agent için)

## Giriş Kuralları
- K-02: Kriz başında momentum/AI sektörüne 3 gün giriş yok
- K-04: SMA50 üstü giriş tercih. Altıysa: RSI<30 + stabilizasyon + çeyrek pozisyon
- K-05: Swing pozisyonu earnings'ten 2+ gün önce kapat

## Kâr Alma (K-11 v3)
- Katman1: RSI 70+ VE kâr %15+ → trailing stop aktif (2×ATR veya 20SMA altı), satma
- Katman2: RSI 80+ VEYA (RSI 75+ + negatif div/20SMA altı) → %25-30 kısmi sat
- Katman3: 50SMA altı kapanış VEYA chandelier trailing → TAM ÇIK
- İstisnalar: earnings 5g içinde→70'te, VIX>28→72'de, LEAPS→80+

## VIX/Risk Kuralları (K-13 v4.1)
- Aktif kriz: jeopolitik/İran
- Faydalanıcılar (savunma, enerji, altın): VIX 28'e kadar tam pozisyon
- Duyarlılar (tech, growth, AI): VIX 22'den itibaren yarım pozisyon
- VIX>35: tüm yeni girişler dur

## Drawdown (K-14)
- SPY SMA50 altındaysa: yeni swing girişi yasak, boyut 5K max
- Yeniden başlama: VIX<22 + SPY>SMA50 + sektör rotasyonu pozitif

## Zorunlu Kontroller
- K-17: Aynı sektörden aynı gün birden fazla giriş yapma
- K-18: Her yeni girişten önce insider trading kontrol et
- K-19: XLP sektörüne swing girişi yok
- K-20: RS dead cat bounce filtresi — güçlü RS gerekli

## Stop Disiplini
- Stop seviyeleri ASLA override edilmez
- Bir kez geçilirse direkt uygula, bekleme
"""
    path.write_text(digest, encoding="utf-8")
    return digest


# ── L4: Öğrenme Logu (birikimli) ─────────────────────────────────────────────

def load_learning_log() -> str:
    """Birikmiş öğrenmeler — haftalık büyür."""
    path = MEMORY_DIR / "learning_log.json"
    if not path.exists():
        return "Henüz öğrenme kaydı yok."

    with open(path, encoding="utf-8") as f:
        log = json.load(f)

    # Son 5 kaydı döndür
    entries = log.get("entries", [])[-5:]
    if not entries:
        return "Öğrenme kaydı boş."

    lines = []
    for e in entries:
        lines.append(f"[{e.get('date','?')}] {e.get('insight','')}")
    return "\n".join(lines)


def append_learning(insight: str, source: str = "agent"):
    """Yeni öğrenme ekle."""
    path = MEMORY_DIR / "learning_log.json"

    log = {"entries": []}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            log = json.load(f)

    log["entries"].append({
        "date":    datetime.now(TR_TZ).strftime("%Y-%m-%d"),
        "source":  source,
        "insight": insight[:300]
    })

    # Max 50 kayıt tut
    log["entries"] = log["entries"][-50:]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ── Bağlam Derleyici ──────────────────────────────────────────────────────────

def build_context_for_claude(mode: str) -> str:
    """
    Claude'a gönderilecek sıkıştırılmış bağlamı derler.
    Tam JSON yerine sadece özet → ~1500 token, 10x ucuz.
    """
    state   = load_portfolio_state()
    brief   = load_daily_brief()
    rules   = get_k_rules_digest()
    learned = load_learning_log()

    now = datetime.now(TR_TZ).strftime("%Y-%m-%d %H:%M TR")

    context = f"""=== ZAMAN: {now} | MOD: {mode.upper()} ===

=== PİYASA DURUMU ===
{json.dumps(state.get('market', {}), ensure_ascii=False)}

=== PORTFÖY METRİKLERİ ===
{json.dumps(state.get('portfolios', {}), ensure_ascii=False, indent=2)}

=== DÜNKÜ/ÖNCEKİ ANALİZ (brief) ===
{brief}

=== K-KURALLARI ===
{rules}

=== ÖĞRENMELER ===
{learned}
"""
    return context
