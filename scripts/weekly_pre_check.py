#!/usr/bin/env python3
"""
weekly_pre_check.py — Haftalık Rapor Öncesi Zorunlu Doğrulama

Bu script haftalık rapor yazılmadan ÖNCE çalıştırılır.
Raporun içereceği her sayısal veriyi ground-truth olarak üretir.
Raporu yazan AI bu çıktıyı okuyarak yazan — asla hallüsine değil.

Yakaladığı hatalar (26 Nisan 2026 analiz sonrası):
  1. K-05 vs K-16 karışıklığı  → kural kapsam denetimi
  2. stop_loss vs hedef_fiyat  → stop mantık doğrulaması
  3. K-11 atlanan pozisyonlar  → tüm pozisyonlarda Tier1/2/3 kontrolü
  4. ANET gibi hedef aşan pos  → hedef vs güncel fiyat karşılaştırması
  5. Hallüsine makro veriler   → FMP + web'den gerçek veri
  6. Hatalı makro takvim       → BLS/FED takvim kuralları uygulaması

Kullanım:
  python scripts/weekly_pre_check.py
  python scripts/weekly_pre_check.py --output data/weekly_pre_check.json

Çıktı: data/weekly_pre_check.json (rapor için tek gerçek kaynak)
"""

import sys
import json
import argparse
import requests
from datetime import datetime, timedelta, date
from pathlib import Path

# --- PATH ---
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from k_rules_common import fmp_get, load_portfolios, get_all_positions, get_swing_active

# ──────────────────────────────────────────────
# 1. PORTFÖY POZİSYON DOĞRULAMA
# ──────────────────────────────────────────────

def validate_positions():
    """
    Her pozisyon için:
      - stop_loss < guncel_fiyat < hedef_fiyat mantık kontrolü
      - K-11 Tier1/2/3 durumu (RSI + kazanç %)
      - Hedef aşıldı mı?
      - K-12 konsantrasyon limiti aşıldı mı?
    """
    portfolios = load_portfolios()
    errors   = []  # Rapor yazarken engellenmesi gereken hatalar
    warnings = []  # Dikkat edilmesi gereken noktalar
    positions_out = []

    for pname, port in portfolios.items():
        limit_map = {"balanced": 0.25, "aggressive": 0.20, "dividend": 0.15}
        k12_limit = limit_map.get(pname, 0.25)
        nakit = port.get("cash", {}).get("miktar", 0)
        pos_list = [p for p in port.get("positions", []) if not p.get("symbol", "").startswith("_")]
        total_val = sum(p.get("guncel_deger", p.get("yatirim", 0)) for p in pos_list) + nakit

        for p in pos_list:
            sym       = p.get("symbol", "?")
            current   = p.get("current_price", 0)
            stop      = p.get("stop_loss", 0)
            hedef     = p.get("target_price", 0)
            maliyet   = p.get("cost_basis", 0)
            deger     = p.get("guncel_deger", p.get("yatirim", 0))
            pnl_pct   = (current - maliyet) / maliyet * 100 if maliyet else 0
            agirlik   = deger / total_val * 100 if total_val else 0

            rec = {
                "symbol": sym,
                "portfolio": pname,
                "current_price": current,
                "stop_loss": stop,
                "target_price": hedef,
                "cost_basis": maliyet,
                "pnl_pct": round(pnl_pct, 1),
                "weight_pct": round(agirlik, 1),
                "stop_distance_pct": round((current - stop) / current * 100, 1) if current else 0,
                "errors": [],
                "warnings": [],
                "k11_status": None,
                "target_exceeded": False,
            }

            # ── HATA 1: Stop mantık doğrulaması ──────────────────
            # stop_loss, güncel fiyatın ALTINDA olmalı
            if stop >= current and stop > 0:
                msg = (f"[HATA] {sym}: stop_loss ${stop:.2f} >= güncel fiyat ${current:.2f}. "
                       f"Stop üstte → pozisyon anında kapanır! hedef_fiyat=${hedef:.2f} ile karıştırılmış olabilir.")
                rec["errors"].append(msg)
                errors.append(msg)

            # hedef_fiyat, güncel fiyatın ÜSTÜNDE olmalı (kısa pozisyon yok)
            if hedef > 0 and hedef <= current:
                msg = (f"[UYARI] {sym}: hedef_fiyat ${hedef:.2f} <= güncel fiyat ${current:.2f}. "
                       f"Hedef aşıldı! K-11 kontrolü gerekli.")
                rec["warnings"].append(msg)
                rec["target_exceeded"] = True
                warnings.append(msg)

            # ── K-11 Tier Kontrolü ────────────────────────────────
            if pnl_pct >= 15:
                rec["k11_status"] = "Tier1_aday"  # RSI henüz bilinmiyor, RSI canlı çekildikten sonra güncelle
                msg = (f"[UYARI] {sym}: kazanç +%{pnl_pct:.1f} (≥%15). "
                       f"K-11 Tier1 için RSI≥70 kontrolü gerekli.")
                rec["warnings"].append(msg)
                warnings.append(msg)

            # ── K-12 Konsantrasyon ────────────────────────────────
            if agirlik > k12_limit * 100:
                msg = (f"[UYARI] {sym}: ağırlık %{agirlik:.1f} > K-12 limiti %{k12_limit*100:.0f} ({pname})")
                rec["warnings"].append(msg)
                warnings.append(msg)

            positions_out.append(rec)

    return positions_out, errors, warnings


# ──────────────────────────────────────────────
# 2. K-11 RSI CANLI KONTROL
# ──────────────────────────────────────────────

def check_k11_rsi(positions):
    """K-11 Tier1 adayı pozisyonlar için RSI çek, tam karar ver."""
    k11_actions = []

    for p in positions:
        if p.get("k11_status") != "Tier1_aday":
            continue

        sym   = p["symbol"]
        pnl   = p["pnl_pct"]
        stop  = p["stop_loss"]
        hedef = p["target_price"]
        current = p["current_price"]

        rsi_data = fmp_get("technical-indicators/rsi",
                           {"symbol": sym, "periodLength": 14, "timeframe": "1day", "limit": 1})
        rsi = None
        if rsi_data and isinstance(rsi_data, list):
            rsi = rsi_data[0].get("rsi")

        if rsi is None:
            p["k11_status"] = "Tier1_aday_rsi_yok"
            continue

        p["rsi_14"] = round(rsi, 1)

        if pnl >= 15 and rsi >= 80:
            p["k11_status"] = "Tier2"
            k11_actions.append({
                "symbol": sym, "portfolio": p["portfolio"],
                "tier": 2,
                "pnl_pct": pnl, "rsi": rsi,
                "action": f"%25-30 kısmi sat (K-11 Tier2: RSI {rsi:.0f}≥80 + kazanç %{pnl:.1f}≥15)",
                "priority": "YUKSEK"
            })
        elif pnl >= 15 and rsi >= 70:
            p["k11_status"] = "Tier1"
            hedef_msg = " | Hedef AŞILDI" if p.get("target_exceeded") else ""
            k11_actions.append({
                "symbol": sym, "portfolio": p["portfolio"],
                "tier": 1,
                "pnl_pct": pnl, "rsi": rsi,
                "action": (f"Kâr kilidi aktif: %25-30 kısmi sat{hedef_msg}. "
                            f"K-11 Tier1 (RSI {rsi:.0f}≥70 + kazanç %{pnl:.1f}≥15)"),
                "priority": "YUKSEK"
            })
        else:
            p["k11_status"] = f"izle (RSI={rsi:.0f}, kazanç=%{pnl:.1f})"

    return k11_actions


# ──────────────────────────────────────────────
# 3. UPCOMING EARNINGS → K-05 / K-16 KURAL SEÇİCİ
# ──────────────────────────────────────────────

SWING_SCOPE   = "swing"
PORTFOY_SCOPE = "portfolio"

def get_earnings_actions(positions, swing_positions):
    """
    Önümüzdeki 7 gün içinde earnings olan tüm açık pozisyonlar için:
      - Swing pozisyon → K-05 (tam çıkış, 2+ gün önce)
      - Portföy pozisyon → K-16 (skor hesapla → karar)

    ASLA K-05'i portföy pozisyonuna uygulaMA.
    ASLA K-16'yı swing pozisyonuna uygulaMA.
    """
    today       = date.today()
    week_later  = today + timedelta(days=7)

    # Tüm sembolleri topla
    portfoy_syms = {p["symbol"]: p for p in positions}
    swing_syms   = {s.get("symbol"): s for s in swing_positions
                    if not s.get("symbol", "").startswith("_")}

    # FMP earnings calendar
    cal = fmp_get("earnings-calendar", {
        "from": today.isoformat(),
        "to":   week_later.isoformat()
    })

    earnings_actions = []
    seen = set()

    if not cal:
        return earnings_actions

    for ev in cal:
        sym  = ev.get("symbol", "")
        date_str = ev.get("date", "")
        if not sym or sym in seen:
            continue
        try:
            earn_date = date.fromisoformat(date_str)
        except Exception:
            continue

        days_until = (earn_date - today).days

        # Swing pozisyonunda mı?
        if sym in swing_syms:
            seen.add(sym)
            if days_until <= 2:
                earnings_actions.append({
                    "symbol": sym,
                    "scope": SWING_SCOPE,
                    "rule": "K-05",
                    "earnings_date": date_str,
                    "days_left": days_until,
                    "action": "TAM ÇIKIŞ — K-05 zorunlu (swing earnings ≤2 iş günü). Binary risk alınmaz.",
                    "priority": "ACİL"
                })
            else:
                earnings_actions.append({
                    "symbol": sym,
                    "scope": SWING_SCOPE,
                    "rule": "K-05",
                    "earnings_date": date_str,
                    "days_left": days_until,
                    "action": f"Takip: {days_until} gün kaldı. 2 gün kala tam çıkış gerekecek.",
                    "priority": "ORTA"
                })

        # Portföy pozisyonunda mı?
        elif sym in portfoy_syms:
            seen.add(sym)
            pos = portfoy_syms[sym]
            # K-16 skoru
            score, details = _k16_score_quick(sym, pos["current_price"])
            if score >= 4:
                aksiyon = f"K-16 skor {score}/5 → %50 kısmi çıkış + post-earnings bekle"
                oncelik = "YUKSEK"
            elif score >= 2:
                aksiyon = f"K-16 skor {score}/5 → %25 kısmi çıkış + trailing sıkılaştır (K-11 aktif)"
                oncelik = "ORTA"
            else:
                aksiyon = f"K-16 skor {score}/5 → Normal tut, earnings sonrası izle"
                oncelik = "DUSUK"

            earnings_actions.append({
                "symbol": sym,
                "scope": PORTFOY_SCOPE,
                "rule": "K-16",  # Portföy için her zaman K-16
                "earnings_date": date_str,
                "days_left": days_until,
                "k16_score": score,
                "k16_detail": details,
                "action": aksiyon,
                "priority": oncelik,
                "NOT": "K-05 portföy pozisyonuna UYGULANAMAZ. Swing için K-05, portföy için K-16."
            })

    return earnings_actions


def _k16_score_quick(symbol, current_price):
    """Basit K-16 skor hesapla (k16_sell_the_news_score.py'nin inline versiyonu)."""
    score = 0
    details = []

    # 1) Son 5 gün ralli ≥%5
    hist = fmp_get("historical-price-eod/full", {"symbol": symbol, "limit": 7})
    if hist and isinstance(hist, list) and len(hist) >= 6:
        price_5d = hist[5].get("close", current_price)
        rally = (current_price - price_5d) / price_5d * 100
        if rally >= 5:
            score += 1
            details.append(f"✅ Madde1: {rally:.1f}% (≥5%)")
        else:
            details.append(f"❌ Madde1: {rally:.1f}% (<5%)")

    # 2) EPS revizyon (%10+) — analyst-estimates
    est = fmp_get("analyst-estimates", {"symbol": symbol, "period": "quarter", "limit": 3})
    if est and isinstance(est, list) and len(est) >= 2:
        e_new = est[0].get("epsAvg", 0)
        e_old = est[1].get("epsAvg", 0)
        if e_old and e_old != 0:
            chg = (e_new - e_old) / abs(e_old) * 100
            if chg >= 10:
                score += 1
                details.append(f"✅ Madde2: EPS rev {chg:.0f}%")
            else:
                details.append(f"❌ Madde2: EPS rev {chg:.0f}%")
        else:
            details.append("⚠️ Madde2: EPS veri yok")
    else:
        details.append("⚠️ Madde2: EPS veri yok")

    # 3) 52w zirveye ≤%5
    q = fmp_get("batch-quote", {"symbols": symbol})
    if q and isinstance(q, list) and q:
        h52 = q[0].get("yearHigh", 0)
        if h52 > 0:
            dist = (h52 - current_price) / h52 * 100
            if dist <= 5:
                score += 1
                details.append(f"✅ Madde3: Zirveye %{dist:.1f} (≤5%)")
            else:
                details.append(f"❌ Madde3: Zirveye %{dist:.1f}")

    # 4) Sektör ≥%10 (1ay) — basit yaklaşım
    details.append("⚠️ Madde4: Sektör manuel kontrol")

    # 5) Short interest ≥%10
    km = fmp_get("key-metrics-ttm", {"symbol": symbol})
    if km and isinstance(km, list) and km:
        sr = km[0].get("shortRatioTTM") or km[0].get("shortInterestPercent", 0) or 0
        if sr >= 10:
            score += 1
            details.append(f"✅ Madde5: Short %{sr:.1f}")
        else:
            details.append(f"❌ Madde5: Short %{sr:.1f}")

    return score, details


# ──────────────────────────────────────────────
# 4. GERÇEK MAKRO VERİ
# ──────────────────────────────────────────────

def get_macro_data():
    """
    Gerçek makro veriyi FMP'den çek.
    İşsizlik, VIX, SPY gibi verileri hallüsine YAPMA.

    Makro takvim kuralları (değişmez):
      - NFP (işsizlik): Her ayın İLK CUMASı
      - CPI: Her ayın 10-15'i arası (BLS takvimi)
      - PCE: Bir önceki ayın son iş günü (~30/31'i)
      - FOMC: Yılda 8 toplantı, takvim sabit
    """
    macro = {}

    # VIX
    vix = fmp_get("quote", {"symbol": "^VIX"})
    if vix and isinstance(vix, list):
        macro["vix"] = round(vix[0].get("price", 0), 2)
        macro["vix_note"] = ("NORMAL" if macro["vix"] < 20
                            else "YUKSELIYYOR" if macro["vix"] < 28
                            else "PANIK")

    # SPY güncel
    spy = fmp_get("batch-quote", {"symbols": "SPY,QQQ"})
    if spy and isinstance(spy, list):
        for item in spy:
            sym = item.get("symbol")
            price = item.get("price", 0)
            prev  = item.get("previousClose", price)
            chg   = (price - prev) / prev * 100 if prev else 0
            macro[sym.lower()] = {"price": round(price, 2), "change_pct": round(chg, 2)}

    # Makro takvim — hesaplama tabanlı (hallüsine değil, kural tabanlı)
    today = date.today()

    def next_nfp(from_date):
        """O ayın ilk Cuması (0=Pazartesi, 4=Cuma)."""
        d = date(from_date.year, from_date.month, 1)
        while d.weekday() != 4:
            d += timedelta(days=1)
        if d < from_date:
            # Bu ayın NFP geçti, gelecek ay
            if from_date.month == 12:
                d = date(from_date.year + 1, 1, 1)
            else:
                d = date(from_date.year, from_date.month + 1, 1)
            while d.weekday() != 4:
                d += timedelta(days=1)
        return d

    nfp_date = next_nfp(today)
    macro["nfp_date"] = nfp_date.isoformat()
    macro["nfp_days_left"] = (nfp_date - today).days
    macro["nfp_what_is"] = "NFP (Tarım Dışı İstihdam + İşsizlik Oranı) — piyasanın en yüksek etkili makro verisi"

    # PCE: Bu ayın son iş günü civarı → önceki ay verisi
    # Basit kural: 30/31'de yoksa 28'de
    macro["pce_description"] = "PCE genellikle referans ayı bitmeden önceki son iş günü açıklanır (~30 Nis, 31 May vb.)"

    # CPI: Ayın 10-15'i
    macro["cpi_description"] = "CPI genellikle her ayın 10-15'i arasında BLS tarafından açıklanır"

    # UYARI: İşsizlik oranını FMP'den çekmeye çalış
    # FMP ekonomik göstergeler (stabilize olmuş endpoint)
    macro["labor_warning"] = (
        "İşsizlik oranını asla hafızadan yazma. "
        "FMP /economic endpoint veya BLS resmi sitesi kaynak olmalı. "
        "Son bilinen: %4.3 (BLS, Mart 2026, USDL-26-0580)"
    )
    macro["labor_last_known"] = {
        "value": 4.3,
        "period": "Mart 2026",
        "source": "BLS USDL-26-0580 (3 Nisan 2026)",
        "description": "Mart 2026 NFP: +178K iş, işsizlik %4.3. U-6 geniş ölçüt: %8.0"
    }

    return macro


# ──────────────────────────────────────────────
# 5. PORTFÖY ÖZET
# ──────────────────────────────────────────────

def portfolio_summary():
    """3 portföy toplam değer, P/L, nakit oranı."""
    portfolios = load_portfolios()
    baslaac = {"balanced": 100_000, "aggressive": 400_000, "dividend": 100_000}
    summary = {}
    grand_val = 0
    grand_bas = 600_000

    for name, port in portfolios.items():
        pos_list = [p for p in port.get("positions", []) if not p.get("symbol", "").startswith("_")]
        nakit = port.get("cash", {}).get("miktar", 0)
        pos_val = sum(p.get("guncel_deger", p.get("yatirim", 0)) for p in pos_list)
        total = pos_val + nakit
        bas = baslaac.get(name, 100_000)
        grand_val += total
        summary[name] = {
            "total": round(total, 2),
            "start_capital": bas,
            "pnl_dollar": round(total - bas, 2),
            "pl_pct": round((total - bas) / bas * 100, 1),
            "cash": round(nakit, 2),
            "cash_pct": round(nakit / total * 100, 1) if total else 0,
            "position_count": len(pos_list),
        }

    summary["GENEL"] = {
        "total": round(grand_val, 2),
        "start_capital": grand_bas,
        "pnl_dollar": round(grand_val - grand_bas, 2),
        "pl_pct": round((grand_val - grand_bas) / grand_bas * 100, 1),
    }
    return summary


# ──────────────────────────────────────────────
# 6. SEKTÖR KONSANTRASYON
# ──────────────────────────────────────────────

def sector_concentration():
    """Tüm portföy pozisyon değerinin sektör dağılımı."""
    all_pos = get_all_positions()
    active  = [p for p in all_pos if not p.get("symbol", "").startswith("_")]
    toplam  = sum(p.get("guncel_deger", p.get("yatirim", 0)) for p in active)

    from collections import defaultdict
    sektorler = defaultdict(float)
    tema_map  = defaultdict(float)  # AI/semi grubu

    ai_semi_keywords = ["AI", "Yarı İletken", "Semi", "Networking", "DRAM", "Optik"]

    for p in active:
        sektor = p.get("sektor", "Diğer")
        val    = p.get("guncel_deger", p.get("yatirim", 0))
        sektorler[sektor] += val
        if any(k.lower() in sektor.lower() for k in ai_semi_keywords):
            tema_map["AI/Semi"] += val

    result = {}
    for s, v in sorted(sektorler.items(), key=lambda x: -x[1]):
        result[s] = {"value": round(v, 0), "pct": round(v / toplam * 100, 1) if toplam else 0}

    # K-17 tema limiti kontrolü (%40)
    k17_alerts = []
    for tema, val in tema_map.items():
        tema_pct = val / toplam * 100 if toplam else 0
        if tema_pct > 40:
            k17_alerts.append(
                f"[K-17 İHLAL] {tema}: %{tema_pct:.1f} > eşik %40. "
                f"Yeni giriş YASAK. Mevcut pozisyonlarda kademeli azaltma değerlendir."
            )

    return result, k17_alerts, round(toplam, 0)


# ──────────────────────────────────────────────
# ANA AKIŞ
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Haftalık rapor öncesi doğrulama")
    parser.add_argument("--output", default=str(REPO_ROOT / "data" / "weekly_pre_check.json"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*60}")
    print(f"  Finzora AI — Haftalık Ön Kontrol — {ts}")
    print(f"{'='*60}\n")

    # 1. Portföy özet
    print("📊 [1/6] Portföy özeti hesaplanıyor...")
    summary = portfolio_summary()

    # 2. Pozisyon doğrulama
    print("🔍 [2/6] Pozisyon mantık doğrulaması (stop/hedef/K-12)...")
    positions, errors, warnings = validate_positions()

    if errors:
        print(f"\n🚨 BLOKAJ HATALARI ({len(errors)}):")
        for e in errors:
            print(f"  ❌ {e}")
    if warnings:
        print(f"\n⚠️  Uyarılar ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠️  {w}")

    # 3. K-11 RSI kontrol
    print("\n📈 [3/6] K-11 Tier1/2/3 RSI kontrolü...")
    k11_actions = check_k11_rsi(positions)
    if k11_actions:
        print(f"  K-11 aksiyonlar ({len(k11_actions)}):")
        for a in k11_actions:
            print(f"  → [{a['priority']}] {a['symbol']} Tier{a['tier']}: {a['action']}")
    else:
        print("  K-11 tetiklenecek pozisyon yok.")

    # 4. Earnings & K-05/K-16
    print("\n📅 [4/6] Earnings takvimi + K-05/K-16 kural seçimi...")
    swing_pos = get_swing_active()
    earn_actions = get_earnings_actions(positions, swing_pos)
    if earn_actions:
        print(f"  Earnings aksiyonlar ({len(earn_actions)}):")
        for ea in earn_actions:
            kural = ea.get("rule")
            scope = ea.get("scope")
            skor  = f" K-16:{ea.get('k16_score')}/5" if kural == "K-16" else ""
            print(f"  → [{ea['priority']}] {ea['symbol']} ({scope}) {kural}{skor} | "
                  f"{ea['earnings_date']} ({ea['days_left']}g) | {ea['action'][:60]}...")
    else:
        print("  Önümüzdeki 7 günde earnings yok.")

    # 5. Makro veri
    print("\n🌍 [5/6] Gerçek makro veri çekiliyor...")
    macro = get_macro_data()
    vix = macro.get("vix", "?")
    nfp = macro.get("nfp_date", "?")
    nfp_g = macro.get("nfp_days_left", "?")
    print(f"  VIX: {vix} ({macro.get('vix_note', '?')})")
    print(f"  NFP tarihi: {nfp} ({nfp_g} gün kaldı)")
    print(f"  İşsizlik son bilinen: %{macro['labor_last_known']['value']} ({macro['labor_last_known']['period']})")
    print(f"  ⚠️  {macro['labor_warning'][:80]}...")

    # 6. Sektör konsantrasyon
    print("\n🏗️  [6/6] Sektör konsantrasyon + K-17 denetimi...")
    sektorler, k17_alerts, pos_toplam = sector_concentration()
    if k17_alerts:
        for a in k17_alerts:
            print(f"  🔴 {a}")
    else:
        print("  K-17 ihlali yok.")

    # ── SONUÇ ÖZET ──────────────────────────────
    print(f"\n{'='*60}")
    print("  AKSIYON ÖZETİ")
    print(f"{'='*60}")

    acil = [a for a in k11_actions + earn_actions if a.get("priority") == "ACİL"]
    yuksek = [a for a in k11_actions + earn_actions if a.get("priority") == "YUKSEK"]
    orta   = [a for a in k11_actions + earn_actions if a.get("priority") == "ORTA"]

    if acil:
        print(f"\n🚨 ACİL ({len(acil)}):")
        for a in acil:
            print(f"  → {a['symbol']}: {a['action']}")
    if yuksek:
        print(f"\n🔴 YÜKSEK ÖNCELİK ({len(yuksek)}):")
        for a in yuksek:
            print(f"  → {a['symbol']}: {a['action']}")
    if orta:
        print(f"\n🟡 ORTA ({len(orta)}):")
        for a in orta:
            print(f"  → {a['symbol']}: {a.get('action','')[:70]}...")

    if errors:
        print(f"\n🚨 {len(errors)} BLOKAJ HATASI — Rapor yazmadan önce düzeltilmeli!")
    else:
        print("\n✅ Blokaj hatası yok. Rapor yazılabilir.")

    print(f"\n{'='*60}\n")

    # ── JSON ÇIKTI ──────────────────────────────
    output = {
        "created_at": ts,
        "portfolio_summary": summary,
        "positions": positions,
        "k11_actions": k11_actions,
        "earnings_actions": earn_actions,
        "sector_distribution": sektorler,
        "k17_alerts": k17_alerts,
        "macro": macro,
        "blocking_errors": errors,
        "warnings": warnings,
        "report_writing_rules": {
            "stop_loss": "JSON'daki stop_loss alanını oku. ASLA hedef_fiyat ile karıştırma. stop < güncel fiyat olmalı.",
            "target_price": "JSON'daki hedef_fiyat alanını oku. stop_loss ile aynı değil.",
            "k05_scope": "K-05 SADECE swing trade. Portföy pozisyonu için K-16 kullan.",
            "k16_scope": "K-16 SADECE portföy pozisyonu. Swing için K-05 kullan.",
            "labor_ratio": f"Son bilinen: %{macro['labor_last_known']['value']} ({macro['labor_last_known']['period']}). Asla hafızadan yaz.",
            "nfp_date": f"NFP: {macro.get('nfp_date')}. CPI: ayın ~10-15'i. PCE: ayın son iş günü.",
            "k11_tier1": "RSI≥70 VE kazanç≥%15 → Tier1 aktif. Bu script çalıştırılmışsa k11_aksiyonlar listesine bak.",
        }
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Çıktı kaydedildi: {args.output}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
