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

# Swing max kapasite — tek kaynak swing_manager.SWING_MAX_POSITIONS
try:
    import sys as _sys
    if str(Path(__file__).parent) not in _sys.path:
        _sys.path.insert(0, str(Path(__file__).parent))
    from swing_manager import SWING_MAX_POSITIONS as _SWING_MAX
except Exception:
    _SWING_MAX = 5


# ── L1: Portföy Durumu (anlık, her çağrıda yenilenir) ────────────────────────

def build_portfolio_state(portfolios: dict, market: dict) -> dict:
    """
    Tam JSON yerine sadece kritik metrikler.
    ~300 token.
    """
    state = {
        "timestamp": datetime.now(TR_TZ).isoformat(),
        "market": {
            "SPY":        market.get("SPY", {}).get("price"),
            "QQQ":        market.get("QQQ", {}).get("price"),
            "GLD":        market.get("GLD", {}).get("price"),
            "TLT":        market.get("TLT", {}).get("price"),
            "spy_chg":    market.get("SPY", {}).get("chg"),
            "qqq_chg":    market.get("QQQ", {}).get("chg"),
            "VIX":        market.get("VIX", {}).get("price"),
            "VIX_chg":    market.get("VIX", {}).get("chg"),
            "VIX_seviye": market.get("VIX", {}).get("seviye"),
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
            maliyet    = pos.get("maliyet_baz") or pos.get("maliyet_bazis")
            hedef      = pos.get("hedef_fiyat")
            adet       = pos.get("adet") or pos.get("shares", 0)

            # Stop mesafesi hesapla
            stop_pct = None
            if stop and cur_price:
                try:
                    # Stop uzaklığı: fiyattan stop'a yüzde mesafe
                    stop_pct = round((float(cur_price) - float(stop)) / float(cur_price) * 100, 1)
                except (ValueError, TypeError):
                    pass

            # Kar/zarar hesapla
            pnl_pct = None
            if maliyet and cur_price:
                try:
                    pnl_pct = round((float(cur_price) - float(maliyet)) / float(maliyet) * 100, 1)
                except (ValueError, TypeError):
                    pass

            if "pozisyonlar" not in pf_state:
                pf_state["pozisyonlar"] = []
            pf_state["pozisyonlar"].append({
                "sym":       sym,
                "fiyat":     cur_price,
                "gunluk":    pos.get("gunluk_degisim"),
                "pnl_pct":   pnl_pct,
                "stop_pct":  stop_pct,   # stop'a uzaklık — negatifse geçilmiş
                "hedef":     hedef,
            })

        state["portfolios"][pf_name] = pf_state

    # Swing pozisyonları da ekle — Claude tabloda yanlış hesaplamasın
    try:
        import json as _j
        sw = _j.load(open(REPO_ROOT / "data" / "swing" / "active.json"))
        swing_pozlar = []
        for sp in sw.get("aktif_pozisyonlar", []):
            gun   = float(sp.get("guncel_fiyat", 0) or 0)
            stop_l = float(sp.get("stop_loss", 0) or 0)
            chand  = float(sp.get("chandelier_stop", 0) or 0)
            stop   = max(stop_l, chand) if chand else stop_l
            giris  = float(sp.get("giris_fiyat", sp.get("maliyet_baz", 0)) or 0)
            pnl    = round((gun - giris) / giris * 100, 2) if giris else 0
            stop_uzak = round((gun - stop) / gun * 100, 1) if gun and stop else 0
            swing_pozlar.append({
                "sym":       sp.get("sembol", ""),
                "fiyat":     gun,
                "pnl_pct":   pnl,
                "stop":      round(stop, 2),
                "stop_uzak_pct": stop_uzak,
                "hedef":     sp.get("hedef_fiyat"),
                "giris_tarihi": sp.get("giris_tarihi"),
            })
        state["swing"] = {
            "aktif_sayisi": len(swing_pozlar),
            "max_kapasite": _SWING_MAX,
            "pozisyonlar":  swing_pozlar,
        }
    except Exception:
        state["swing"] = {"aktif_sayisi": 0, "pozisyonlar": []}

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

    # Playbook'tan otomatik özet çıkar (haftalık cache, mtime tabanlı)
    playbook_path = REPO_ROOT / "docs" / "TRADING_PLAYBOOK.md"
    if not playbook_path.exists():
        return "K-kuralları bulunamadı."

    # Cache taze mi? (playbook değişmediyse ve cache <7 gün)
    if path.exists():
        try:
            cache_mtime = path.stat().st_mtime
            pb_mtime = playbook_path.stat().st_mtime
            age_days = (datetime.now().timestamp() - cache_mtime) / 86400
            if cache_mtime > pb_mtime and age_days < 7:
                return path.read_text(encoding="utf-8")
        except Exception:
            pass

    # Playbook'tan aktif K-xx bloklarını extract et
    extracted = _extract_k_rules_from_playbook(playbook_path)
    if extracted and len(extracted) > 200:
        path.write_text(extracted, encoding="utf-8")
        return extracted

    # Fallback: statik özet
    digest = """# K-KURALLARI ÖZET (Agent için)

## Giriş Kuralları
- K-02: Kriz rallisi ilk günü kovalama — min 1 gün soğuma + RSI onayı
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

## Zorunlu Kontroller
- K-17: Aynı sektörden aynı gün birden fazla giriş yapma
- K-18: Her yeni girişten önce insider trading kontrol et
- K-19: XLP sektörüne swing girişi yok
- K-20: RS dead cat bounce filtresi — güçlü RS gerekli

## Stop Disiplini
- Stop seviyeleri ASLA override edilmez
- Bir kez geçilirse direkt uygula, bekleme

## Kaldırılan Kurallar (11 Nisan 2026)
- K-01, K-03, K-08: erken kaldırıldı
- K-14 drawdown freni: kaldırıldı — normal pozisyon boyutlandırma, pre-entry psikoloji testi devrede
"""
    path.write_text(digest, encoding="utf-8")
    return digest


def _extract_k_rules_from_playbook(playbook_path: Path) -> str:
    """TRADING_PLAYBOOK.md'den aktif K-xx madde satırlarını extract et.

    Playbook `## 1. KANITLANMIŞ KURALLAR` gibi organize — K kuralları
    bölüm içinde bullet olarak geçiyor. Basit yaklaşım:
    "K-xx:" veya "K-xx " ile başlayan madde satırlarını topla,
    kaldırılmış kuralları ele.
    """
    try:
        text = playbook_path.read_text(encoding="utf-8")
    except Exception:
        return ""

    import re
    # K-xx ile başlayan bullet/madde satırlarını bul
    # Örnek: "- K-02: kriz..." veya "K-13 v4.1: VIX..."
    pattern = re.compile(
        r"^[\-\*\s]*K-(\d{2})[\s:v.\d]+(.+?)$",
        re.MULTILINE,
    )
    found: dict[str, str] = {}  # "K-xx" -> ilk bulunan açıklama (en kısa genelde baş)
    for m in pattern.finditer(text):
        num = m.group(1)
        desc = m.group(2).strip()
        key = f"K-{num}"
        # Kaldırılan kuralları atla
        if num in ("01", "03", "08", "14"):
            continue
        # İlk bulunanı al (genelde playbook'un başında özet olur)
        if key not in found and 10 < len(desc) < 300:
            found[key] = desc

    if not found:
        return ""

    out = ["# K-KURALLARI ÖZET (playbook'tan üretildi)\n"]
    for key in sorted(found.keys(), key=lambda k: int(k.split("-")[1])):
        out.append(f"- **{key}**: {found[key]}")

    out.append("\n## Kaldırılan Kurallar\n- K-01/K-03/K-08: erken kaldırıldı")
    out.append("- K-14 drawdown freni: 11 Nisan 2026'da kaldırıldı")
    return "\n".join(out)


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

    # 'dersler' formatına da uyum sağla (bootstrap formatı)
    if "entries" not in log:
        if "dersler" in log:
            log["entries"] = log["dersler"]
        else:
            log["entries"] = []

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
    Tam JSON yerine okunabilir tablo formatı → hata riski düşük.
    """
    state   = load_portfolio_state()
    brief   = load_daily_brief()
    rules   = get_k_rules_digest()
    learned = load_learning_log()

    now = datetime.now(TR_TZ).strftime("%Y-%m-%d %H:%M TR")
    _gunler = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    _gun = _gunler[datetime.now(TR_TZ).weekday()]

    # Piyasa özet satırı
    mkt = state.get("market", {})
    mkt_lines = []
    for sym in ["SPY","QQQ","GLD","TLT"]:
        p   = mkt.get(sym)
        chg = mkt.get(f"{sym.lower()}_chg") or mkt.get(f"{sym}_chg")
        if p:
            chg_str = f"{float(chg):+.2f}%" if chg is not None else "—"
            mkt_lines.append(f"  {sym:4}: ${float(p):,.2f} ({chg_str})")
    vix = mkt.get("VIX")
    vix_chg = mkt.get("VIX_chg")
    vix_sev = mkt.get("VIX_seviye","")
    if vix:
        vchg = f"{float(vix_chg):+.2f}%" if vix_chg else "—"
        mkt_lines.append(f"  VIX : {float(vix):.2f} ({vchg}) [{vix_sev}]")

    # Portföy tablosu — okunabilir format
    pf_lines = []
    PF_LABEL = {"aggressive":"Agresif","balanced":"Dengeli","dividend":"Temettü"}
    for pf_name, pf_data in state.get("portfolios", {}).items():
        label = PF_LABEL.get(pf_name, pf_name)
        deg   = pf_data.get("toplam_deger")
        getiri = pf_data.get("getiri_yuzde")
        deg_str    = f"${float(deg):,.0f}" if deg else "—"
        getiri_str = f"{float(getiri):+.1f}%" if getiri is not None else "—"
        pf_lines.append(f"\n[{label}] {deg_str} ({getiri_str})")
        pf_lines.append(f"  {'Sembol':<6} {'Fiyat':>8} {'Bugün':>7} {'P/L':>7} {'Stop%':>6} {'Hedef':>8}")
        pf_lines.append(f"  {'-'*50}")
        for pos in pf_data.get("pozisyonlar", []):
            sym      = str(pos.get("sym","?"))
            fiyat    = pos.get("fiyat")
            gunluk   = pos.get("gunluk")
            pnl_pct  = pos.get("pnl_pct")
            stop_pct = pos.get("stop_pct")
            hedef    = pos.get("hedef")
            f_str = f"${float(fiyat):,.2f}" if fiyat else "—"
            g_str = f"{float(gunluk):+.1f}%" if gunluk is not None else "—"
            p_str = f"{float(pnl_pct):+.1f}%" if pnl_pct is not None else "—"
            s_str = f"%{float(stop_pct):.1f}" if stop_pct is not None else "—"
            h_str = f"${float(hedef):,.0f}" if hedef else "—"
            # Stop yakınsa uyarı
            uyari = " ⚠️" if stop_pct is not None and float(stop_pct) < 4 else ""
            pf_lines.append(f"  {sym:<6} {f_str:>8} {g_str:>7} {p_str:>7} {s_str:>6} {h_str:>8}{uyari}")

    # Swing tablosu
    sw_lines = []
    swing = state.get("swing", {})
    sw_pozlar = swing.get("pozisyonlar", [])
    if sw_pozlar:
        akt = swing.get("aktif_sayisi", 0)
        sw_lines.append(f"\n[Swing Trade] {akt}/5 slot dolu")
        sw_lines.append(f"  {'Sembol':<6} {'Fiyat':>8} {'P/L':>7} {'Stop':>8} {'Stop%':>6} {'Hedef':>8}")
        sw_lines.append(f"  {'-'*50}")
        for sp in sw_pozlar:
            sym   = str(sp.get("sym","?"))
            fiyat = sp.get("fiyat")
            pnl   = sp.get("pnl_pct")
            stop  = sp.get("stop")
            uzak  = sp.get("stop_uzak_pct")
            hedef = sp.get("hedef")
            f_str = f"${float(fiyat):,.2f}" if fiyat else "—"
            p_str = f"{float(pnl):+.1f}%" if pnl is not None else "—"
            s_str = f"${float(stop):,.2f}" if stop else "—"
            u_str = f"%{float(uzak):.1f}" if uzak is not None else "—"
            h_str = f"${float(hedef):,.0f}" if hedef else "—"
            uyari = " ⚠️ YAKIN" if uzak is not None and float(uzak) < 5 else ""
            sw_lines.append(f"  {sym:<6} {f_str:>8} {p_str:>7} {s_str:>8} {u_str:>6} {h_str:>8}{uyari}")

    context = f"""=== ZAMAN: {now} ({_gun}) | MOD: {mode.upper()} ===

=== PİYASA DURUMU ===
{chr(10).join(mkt_lines)}

=== PORTFÖY (Sembol | Fiyat | Bugün | Giriş P/L | StopUzak% | Hedef) ===
NOT: Stop% = fiyattan stop seviyesine uzaklık. ⚠️ = Stop %4 altında (acil takip).
P/L = giriş fiyatına göre toplam getiri. Bugün = o günkü hareket.
{chr(10).join(pf_lines)}
{chr(10).join(sw_lines)}

=== DÜNKÜ/ÖNCEKİ ANALİZ (brief) ===
{brief}

=== K-KURALLARI ===
{rules}

=== ÖĞRENMELER ===
{learned}
"""
    return context
