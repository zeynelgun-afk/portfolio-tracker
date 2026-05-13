#!/usr/bin/env python3
"""
adil_deger_calculator — Backward-compat shim (v5 forwarding layer)
====================================================================
Bu dosya, eski v2 API'sini v5 framework'üne yönlendiren ince bir katmandır.

Orijinal v2 (962 satır, 6 metot equal-weight) arşivlendi:
  scripts/adil_deger_calculator_v2_archived.py

v5 framework: agent/valuation/ (32 archetype, 30+ method, routing)

Korunan API (backward-compat):
  - hesapla(symbol, **kwargs) → v2-uyumlu flat dict
  - get_market_regime() → v5/market_regime modülünden re-export
  - BOGA_REJIM_MULT, AYI_REJIM_MULT sabitleri
  - CLI: --portfolio, --report, --telegram

Yeni kodlarda doğrudan v5 kullanın:
  from agent.valuation.framework import valuate
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

# v5 framework import yolu
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

from valuation.framework import valuate, format_report
from valuation.market_regime import (
    get_market_regime,
    BOGA_REJIM_MULT,
    AYI_REJIM_MULT,
    NOTR_REJIM_MULT,
)


TG_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "-1003827034395")


# ─────────────────────────────────────────────────────────────────────────────
# BACKWARD-COMPAT API
# ─────────────────────────────────────────────────────────────────────────────

def hesapla(symbol, pe_modu='average', manuel_pe=None, fwd_eps_input=None,
            sessiz=False, **kwargs):
    """
    v2-uyumlu wrapper. v5 framework'ü çağırır, sonucu flat dict'e indirir.

    Args (legacy, v5'te kullanılmıyor — sadece API uyumu için):
        pe_modu, manuel_pe, fwd_eps_input — görmezden gelinir
        sessiz: v5 verbose'un tersi
    """
    try:
        result = valuate(symbol.upper(), verbose=not sessiz)
    except Exception as e:
        if not sessiz:
            print(f"[v5 hata] {symbol}: {e}")
        return None

    if not result or result.get("error"):
        if not sessiz:
            print(f"[v5 error] {symbol}: {result.get('error') if result else 'None'}")
        return None

    # v5 → v2 flat dict dönüşümü
    cls = result["classification"]
    fv = result["fair_value"]
    conf = result["confidence"]
    snap = result.get("data_snapshot", {})

    # Metod adı mapping (v2 legacy key'leri için)
    metotlar = {}
    for m in result.get("methods_used", []):
        # v2 key'lerine yakın alias'lar
        name = m["name"]
        display = {
            "trailing_pe":         "Net Kazanç P/E",
            "forward_pe_ny1":      "Forward P/E",
            "forward_pe_ny2":      "Forward P/E NY2",
            "forward_pe_ny3":      "Forward P/E NY3",
            "forward_pe_normalized": "Forward P/E",
            "ev_ebitda":           "EV/EBITDA",
            "ev_ebitda_forward":   "EV/EBITDA fwd",
            "dcf_2stage":          "DCF (3 aşama)",
            "dcf_multi_stage":     "DCF (3 aşama)",
            "dcf_multi_stage_aggressive": "DCF (agresif)",
            "fcf_yield":           "P/FCF",
            "ev_revenue":          "EV/Ciro",
            "ev_rev_growth_adjusted": "EV/Ciro (growth-adj)",
            "justified_pb":        "Justified P/B",
            "residual_income":     "Residual Income",
            "dividend_discount":   "DDM",
            "p_ffo":               "P/FFO",
            "p_affo":              "P/AFFO",
        }.get(name, name)
        metotlar[display] = m["fair_value"]

    return {
        "symbol":       symbol.upper(),
        "price":        fv["current_price"],
        "adil_deger":   fv["point"],
        "fark_pct":     fv["upside_pct"],
        "guven":        conf["score"],
        "hisse_tipi":   cls["archetype"],
        "sector":       snap.get("sector", ""),
        "industry":     snap.get("industry", ""),
        "metotlar":     metotlar,
        "karar":        fv["karar"],
        "range_low":    fv["range_low"],
        "range_high":   fv["range_high"],
        "red_flags":    conf.get("red_flags", []),
        "excluded":     [e["name"] for e in result.get("methods_excluded", [])],
        "archetype":    cls["archetype"],
        "archetype_label": cls["archetype_label"],
        "_v5_full":     result,
        "_version":     "v5-via-shim",
    }


def tg_send(msg):
    """Legacy Telegram gönderici — group chat'e."""
    if not TG_TOKEN:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": msg,
                            "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT (backward-compat — workflow adil_deger_weekly.yml için)
# ─────────────────────────────────────────────────────────────────────────────

def _batch_ozet(sonuclar):
    """Birden fazla ticker özet tablosu."""
    print(f"\n{'='*72}")
    print(f"  {'SEMBOL':<8} {'FIYAT':>10} {'HEDEF':>10} {'FARK':>10} {'GÜVEN':>8} KARAR")
    print(f"{'='*72}")
    for s in sonuclar:
        if not s:
            continue
        yon = "🔴" if s['fark_pct'] > 15 else "🟢" if s['fark_pct'] < -15 else "🟡"
        print(f"  {yon} {s['symbol']:<6} ${s['price']:>8.2f} ${s['adil_deger']:>8.2f} "
              f"{s['fark_pct']:>+7.1f}% {s['guven']:>5}/100 {s['karar']}")


def _markdown_rapor(sonuclar) -> str:
    """Markdown rapor (haftalık)."""
    tarih = datetime.now().strftime('%Y-%m-%d')
    out = [
        f"# Adil Değer Raporu — {tarih}",
        "",
        f"v5 framework (archetype-routed valuation). Rejim: {get_market_regime()[3]}",
        "",
        "| Sembol | Fiyat | Hedef | Fark | Güven | Archetype | Karar |",
        "|--------|-------|-------|------|-------|-----------|-------|",
    ]
    for s in sonuclar:
        if not s:
            continue
        out.append(
            f"| {s['symbol']} | ${s['price']:.2f} | ${s['adil_deger']:.2f} | "
            f"{s['fark_pct']:+.1f}% | {s['guven']}/100 | {s.get('archetype_label','?')[:30]} | "
            f"{s['karar']} |"
        )
    out.append("")
    out.append("## Detaylar")
    for s in sonuclar:
        if not s:
            continue
        out.append(f"\n### {s['symbol']} — {s.get('archetype_label','?')}")
        out.append(f"- Fiyat: ${s['price']:.2f} → Hedef: ${s['adil_deger']:.2f} ({s['fark_pct']:+.1f}%)")
        out.append(f"- Aralık: ${s['range_low']:.2f} — ${s['range_high']:.2f}")
        out.append(f"- Güven: {s['guven']}/100")
        if s.get('red_flags'):
            out.append(f"- ⚠ Red flags: {', '.join(s['red_flags'])}")
        if s.get('metotlar'):
            out.append("- Metotlar:")
            for k, v in s['metotlar'].items():
                out.append(f"  - {k}: ${v:.2f}")
    return "\n".join(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Adil Değer Hesaplayıcı (v5 framework via shim)"
    )
    parser.add_argument("symbols", nargs='*', help="Sembol(ler): AMD MU PLTR")
    parser.add_argument("--portfolio", choices=['balanced','aggressive','dividend'],
                        help="Portfolio JSON'dan semboller oku")
    # Legacy args (v5'te yok, görmezden geliniyor)
    parser.add_argument("--pe-modu",   default="average",
                        choices=["rate","manuel","average"],
                        help="(legacy, v5'te kullanılmıyor)")
    parser.add_argument("--manuel-pe", type=float, help="(legacy)")
    parser.add_argument("--fwd-eps",   type=float, help="(legacy)")
    parser.add_argument("--report",    action="store_true",
                        help="Markdown rapor yaz")
    parser.add_argument("--telegram",  action="store_true",
                        help="Telegram'a gönder")
    args = parser.parse_args()

    symbols = list(args.symbols)
    if args.portfolio:
        pf_path = REPO_ROOT / "data" / "portfolios" / f"{args.portfolio}.json"
        try:
            pf = json.load(open(pf_path))
            # v5 schema: pozisyonlar[].sembol
            positions = pf.get("pozisyonlar") or pf.get("positions") or []
            symbols = [p.get("sembol") or p.get("symbol") for p in positions if (p.get("sembol") or p.get("symbol"))]
            print(f"Portfolio '{args.portfolio}': {symbols}")
        except Exception as e:
            print(f"Portfolio okunamadı: {e}")
            sys.exit(1)

    if not symbols:
        parser.print_help()
        sys.exit(1)

    # Her sembol için hesapla
    sonuclar = []
    sessiz = len(symbols) > 1
    for sym in symbols:
        if sessiz:
            print(f"\n► {sym.upper()} hesaplanıyor...")
        s = hesapla(sym.upper(), sessiz=sessiz)
        if not sessiz and s and s.get("_v5_full"):
            print(format_report(s["_v5_full"], style="terminal"))
        sonuclar.append(s)

    if sessiz:
        _batch_ozet(sonuclar)

    # Rapor
    if args.report:
        tarih = datetime.now().strftime('%Y-%m-%d')
        rp_path = REPO_ROOT / "reports" / "daily" / f"ADIL_DEGER_{tarih}.md"
        rp_path.parent.mkdir(parents=True, exist_ok=True)
        rp_path.write_text(_markdown_rapor(sonuclar))
        print(f"Rapor yazıldı: {rp_path}")

    # Telegram
    if args.telegram and any(sonuclar):
        lines = [f"<b>📊 Adil Değer v5 — {datetime.now().strftime('%d.%m.%Y')}</b>"]
        lines.append(f"<i>{get_market_regime()[3]}</i>\n")
        for s in sonuclar:
            if not s:
                continue
            yon = "🔴" if s['fark_pct'] > 15 else "🟢" if s['fark_pct'] < -15 else "🟡"
            lines.append(
                f"{yon} <b>{s['symbol']}</b> ${s['price']:.2f} → ${s['adil_deger']:.2f} "
                f"({s['fark_pct']:+.1f}%) | {s['guven']}/100 | {s['karar']}"
            )
        tg_send("\n".join(lines))
        print("Telegram bildirimi gönderildi.")
