"""
Finzora Valuation Framework v5 — Methods Registry
===================================================
Her valuation metodu bağımsız bir fonksiyon:
  signature: (data: dict) -> dict | None
  return: {"fair_value": float, "notes": str, "method": str}
          None → metot uygulanamaz (veri yetersiz)

Framework aggregator bu fonksiyonları çağırıp sonuçları ağırlıklandırır.
"""

from __future__ import annotations
import math


# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────────────────────────────────────

def _ok(val, notes="", method=""):
    return {"fair_value": round(float(val), 2), "notes": notes, "method": method}


def _rule_of_40(rev_growth: float, fcf_margin: float) -> float:
    """Rule of 40 skoru (SaaS). >40 healthy."""
    return (rev_growth * 100) + (fcf_margin * 100)


# ─────────────────────────────────────────────────────────────────────────────
# TRADITIONAL MULTIPLES
# ─────────────────────────────────────────────────────────────────────────────

def trailing_pe(d: dict) -> dict | None:
    """Trailing P/E × TTM EPS → fair value."""
    eps = d.get("eps_ttm", 0)
    if eps <= 0:
        return None
    # Sektör/industry ortalama P/E yerine şimdilik 18x (S&P ~18-20 median)
    fair_pe = 18.0
    return _ok(fair_pe * eps, f"P/E {fair_pe}×EPS ${eps:.2f}", "trailing_pe")


def forward_pe_ny1(d: dict) -> dict | None:
    """Forward P/E NY1 × fwd EPS."""
    eps = d.get("fwd_eps_ny1", 0)
    if eps <= 0:
        return None
    # Faiz-nötr P/E (100 / bond yield) — muhafazakar
    rate_pe = max(10.0, min(25.0, 100.0 / max(d.get("bond_y", 4.5), 2)))
    return _ok(rate_pe * eps, f"fwd P/E {rate_pe:.1f}×NY1 EPS ${eps:.2f}", "forward_pe_ny1")


def forward_pe_ny2(d: dict) -> dict | None:
    """Forward P/E NY2 × fwd EPS — yüksek büyüme için daha uygun."""
    eps = d.get("fwd_eps_ny2", 0)
    if eps <= 0:
        return None
    # Growth'a göre multiplier: yüksek growth hak ettiği multiple premium
    growth = d.get("rev_growth_ttm", 0.1)
    if growth > 0.50:
        fair_pe = 45.0  # hyper-growth
    elif growth > 0.30:
        fair_pe = 35.0
    elif growth > 0.15:
        fair_pe = 25.0
    else:
        fair_pe = max(10.0, min(20.0, 100.0 / max(d.get("bond_y", 4.5), 2)))
    # NY2 için 1 yıl discount
    discount = 1.0 / (1.0 + 0.10)
    return _ok(fair_pe * eps * discount,
               f"fwd P/E NY2 {fair_pe:.0f}×${eps:.2f}×disc (gr={growth:.0%})",
               "forward_pe_ny2")


def forward_pe_ny3(d: dict) -> dict | None:
    """NY3 — hyper-growth için kritik."""
    eps = d.get("fwd_eps_ny3", 0)
    if eps <= 0:
        return None
    # Hyper growth için daha yüksek multiple toleransı
    fair_pe = 25.0  # growth premium
    discount = 1.0 / (1.08 ** 2)  # 2 yıl bugüne indirgeme
    return _ok(fair_pe * eps * discount,
               f"fwd P/E NY3 {fair_pe}×${eps:.2f}×disc²",
               "forward_pe_ny3")


def forward_pe_normalized(d: dict) -> dict | None:
    """Normalize edilmiş P/E — bankalar için one-time items çıkarılmış."""
    eps = d.get("fwd_eps_ny1", 0)
    if eps <= 0:
        return None
    # Bankalar için COE ~10% → fair P/E ~10
    fair_pe = 11.0
    return _ok(fair_pe * eps, f"normalized P/E {fair_pe}×${eps:.2f}", "forward_pe_normalized")


def normalized_pe_midcycle(d: dict) -> dict | None:
    """Döngüsel şirketler için 3-5 yıl ortalama EPS × fair multiple."""
    eps_annual = d.get("eps_annual", [])
    if len(eps_annual) < 2 or all(e <= 0 for e in eps_annual):
        return None
    # 3 yıl ortalama (mevcut varsa)
    valid = [e for e in eps_annual if e > 0]
    if not valid:
        return None
    norm_eps = sum(valid) / len(valid)
    fair_pe = 15.0  # cyclical uyumlu
    return _ok(fair_pe * norm_eps,
               f"mid-cycle EPS avg ${norm_eps:.2f} × {fair_pe}",
               "normalized_pe_midcycle")


def normalized_pe_cyclical(d: dict) -> dict | None:
    """Döngüsel için normalize edilmiş P/E — LTM peak/trough tespiti."""
    eps_annual = d.get("eps_annual", [])
    valid = [e for e in eps_annual if e > 0]
    if len(valid) < 2:
        return None
    avg_eps = sum(valid) / len(valid)
    ttm_eps = d.get("eps_ttm", 0)

    # LTM EPS 1.5× avg'den büyükse peak — normalize
    if ttm_eps > avg_eps * 1.5:
        used_eps = avg_eps
        notes = f"PEAK detected, normalized to avg ${avg_eps:.2f}"
    elif ttm_eps < avg_eps * 0.5:
        used_eps = avg_eps
        notes = f"TROUGH detected, normalized to avg ${avg_eps:.2f}"
    else:
        used_eps = ttm_eps
        notes = f"mid-cycle, using TTM ${ttm_eps:.2f}"

    fair_pe = 14.0  # cyclical average
    return _ok(fair_pe * used_eps, notes, "normalized_pe_cyclical")


# ─────────────────────────────────────────────────────────────────────────────
# EV/EBITDA FAMILY
# ─────────────────────────────────────────────────────────────────────────────

def ev_ebitda(d: dict) -> dict | None:
    """EV/EBITDA × TTM EBITDA → EV → equity value."""
    ebitda = d.get("ttm_ebitda", 0)
    if ebitda <= 0:
        return None
    fair_multiple = 12.0  # generic
    fair_ev = fair_multiple * ebitda
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"EV/EBITDA {fair_multiple}×${ebitda/1e9:.1f}B",
               "ev_ebitda")


def ev_ebitda_forward(d: dict) -> dict | None:
    """Forward EV/EBITDA — growth için daha uygun."""
    ebitda = d.get("ttm_ebitda", 0)
    if ebitda <= 0:
        return None
    rev_gr = d.get("rev_growth_ttm", 0.1)
    fwd_ebitda = ebitda * (1 + min(rev_gr, 0.8))  # cap %80
    # Growth'a göre multiple
    if rev_gr > 0.50:
        fair_multiple = 35.0  # hyper-growth semi
    elif rev_gr > 0.30:
        fair_multiple = 25.0
    elif rev_gr > 0.15:
        fair_multiple = 18.0
    else:
        fair_multiple = 12.0
    fair_ev = fair_multiple * fwd_ebitda
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"fwd EV/EBITDA {fair_multiple:.0f}×${fwd_ebitda/1e9:.1f}B (gr={rev_gr:.0%})",
               "ev_ebitda_forward")


def ev_ebitda_midcycle(d: dict) -> dict | None:
    """Döngüsel şirketler için ortalama EBITDA."""
    ebitda_annual = d.get("ebitda_annual", [])
    valid = [e for e in ebitda_annual if e > 0]
    if not valid:
        return None
    norm_ebitda = sum(valid) / len(valid)
    fair_multiple = 8.0  # cyclical conservative
    fair_ev = fair_multiple * norm_ebitda
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"mid-cycle EV/EBITDA {fair_multiple}×avg${norm_ebitda/1e9:.1f}B",
               "ev_ebitda_midcycle")


# ─────────────────────────────────────────────────────────────────────────────
# EV / REVENUE FAMILY
# ─────────────────────────────────────────────────────────────────────────────

def ev_revenue(d: dict) -> dict | None:
    """EV/Revenue × TTM revenue."""
    rev = d.get("ttm_rev", 0)
    if rev <= 0:
        return None
    fair_multiple = 3.0
    fair_ev = fair_multiple * rev
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"EV/Rev {fair_multiple}×${rev/1e9:.1f}B",
               "ev_revenue")


def ev_rev_growth_adjusted(d: dict) -> dict | None:
    """EV/Revenue × Revenue adjusted by growth rate (hyper-growth için)."""
    rev = d.get("ttm_rev", 0)
    growth = d.get("rev_growth_ttm", 0)
    if rev <= 0 or growth <= 0.1:
        return None
    # EV/Rev growth-adjusted: büyüme oranının 0.3-0.4 katı çoklayıcı
    fair_multiple = min(growth * 30, 20.0)  # %50 growth → 15x, capped at 20x
    fair_multiple = max(fair_multiple, 5.0)
    fair_ev = fair_multiple * rev
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"EV/Rev growth-adj {fair_multiple:.1f}×${rev/1e9:.1f}B (gr={growth:.0%})",
               "ev_rev_growth_adjusted")


# ─────────────────────────────────────────────────────────────────────────────
# DCF FAMILY
# ─────────────────────────────────────────────────────────────────────────────

def dcf_2stage(d: dict) -> dict | None:
    """2-stage DCF: 5 yıl yüksek büyüme + terminal."""
    fcf = d.get("ttm_fcf", 0)
    if fcf <= 0:
        return None

    # SBC cash expense olarak çıkar (Damodaran rule)
    adj_fcf = d.get("fcf_adjusted_sbc", fcf)
    if adj_fcf <= 0:
        return None

    # Büyüme oranı (conservative cap)
    growth = min(max(d.get("rev_growth_ttm", 0.08), 0.02), 0.15)
    wacc = 0.09
    terminal_growth = min(d.get("bond_y", 4.5) / 100, 0.03)  # risk-free cap

    pv = 0
    cur_fcf = adj_fcf
    for yr in range(1, 6):
        cur_fcf *= (1 + growth)
        pv += cur_fcf / ((1 + wacc) ** yr)

    # Terminal
    tv_fcf = cur_fcf * (1 + terminal_growth)
    tv = tv_fcf / (wacc - terminal_growth)
    pv_tv = tv / ((1 + wacc) ** 5)

    ev = pv + pv_tv
    equity = ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(equity / shares,
               f"DCF 2-stage g={growth:.0%} wacc={wacc:.0%} tg={terminal_growth:.0%}",
               "dcf_2stage")


def dcf_multi_stage(d: dict) -> dict | None:
    """3-stage DCF: yüksek → orta → terminal (mature growth için)."""
    fcf = d.get("fcf_adjusted_sbc", d.get("ttm_fcf", 0))
    if fcf <= 0:
        return None

    stage1_gr = min(max(d.get("rev_growth_ttm", 0.12), 0.05), 0.25)
    stage2_gr = 0.08
    terminal_gr = 0.025
    wacc = 0.09

    pv = 0
    cur = fcf
    # Stage 1: 5 yıl
    for yr in range(1, 6):
        cur *= (1 + stage1_gr)
        pv += cur / ((1 + wacc) ** yr)
    # Stage 2: 5 yıl (fade)
    for yr in range(6, 11):
        cur *= (1 + stage2_gr)
        pv += cur / ((1 + wacc) ** yr)
    # Terminal
    tv = (cur * (1 + terminal_gr)) / (wacc - terminal_gr)
    pv_tv = tv / ((1 + wacc) ** 10)

    ev = pv + pv_tv
    equity = ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(equity / shares,
               f"DCF 3-stage {stage1_gr:.0%}/{stage2_gr:.0%}/{terminal_gr:.1%}",
               "dcf_multi_stage")


def dcf_multi_stage_aggressive(d: dict) -> dict | None:
    """Hyper-growth için agresif DCF — hızlı fade."""
    fcf = d.get("fcf_adjusted_sbc", d.get("ttm_fcf", 0))

    # Hyper-growth FCF negatif olabilir — revenue * target margin kullan
    if fcf <= 0:
        rev = d.get("ttm_rev", 0)
        if rev <= 0:
            return None
        # Target FCF margin: %20 (hyper-growth SaaS matured)
        fcf = rev * 0.20

    # Aggressive fade: 60% → 30% → 15% → 5% terminal
    stages = [(0.50, 3), (0.30, 3), (0.15, 4)]
    terminal_gr = 0.03
    wacc = 0.10

    pv = 0
    cur = fcf
    yr = 0
    for rate, years in stages:
        for _ in range(years):
            yr += 1
            cur *= (1 + rate)
            pv += cur / ((1 + wacc) ** yr)

    tv = (cur * (1 + terminal_gr)) / (wacc - terminal_gr)
    pv_tv = tv / ((1 + wacc) ** yr)

    ev = pv + pv_tv
    equity = ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(equity / shares,
               f"DCF aggressive fade 50→30→15→{terminal_gr:.0%}",
               "dcf_multi_stage_aggressive")


# ─────────────────────────────────────────────────────────────────────────────
# BANK-SPECIFIC METHODS
# ─────────────────────────────────────────────────────────────────────────────

def justified_pb(d: dict) -> dict | None:
    """Justified P/B = (ROE - g) / (COE - g) × book value."""
    roe = d.get("roe", 0)
    bvps = d.get("bvps", 0)
    if roe <= 0 or bvps <= 0:
        return None

    growth = 0.05  # banka uzun vadeli büyüme (GDP-like)
    coe = 0.10  # cost of equity

    if coe <= growth:
        return None

    justified = (roe - growth) / (coe - growth)
    justified = max(0.5, min(justified, 3.0))  # sanity bounds

    return _ok(justified * bvps,
               f"Just P/B {justified:.2f}×BV ${bvps:.2f} (ROE={roe:.0%})",
               "justified_pb")


def residual_income(d: dict) -> dict | None:
    """Residual Income = BV + Σ PV(excess earnings)."""
    bvps = d.get("bvps", 0)
    roe = d.get("roe", 0)
    if bvps <= 0 or roe <= 0:
        return None

    coe = 0.10
    excess_roe = roe - coe
    if excess_roe <= 0:
        return _ok(bvps, f"RI: no excess return, = BV ${bvps:.2f}", "residual_income")

    # 10 yıl boyunca excess return fade et
    pv_excess = 0
    cur_bvps = bvps
    for yr in range(1, 11):
        fade = max(0, excess_roe * (1 - yr * 0.08))  # linear fade to 0 over ~12 yrs
        excess_earnings = cur_bvps * fade
        pv_excess += excess_earnings / ((1 + coe) ** yr)
        cur_bvps *= (1 + (roe * (1 - d.get("payout_ratio", 0.3))))

    return _ok(bvps + pv_excess,
               f"RI BV ${bvps:.2f} + excess PV ${pv_excess:.2f}",
               "residual_income")


def price_to_tangible_book(d: dict) -> dict | None:
    """P/TBV — bankalar için goodwill'den arındırılmış."""
    tbvps = d.get("tangible_bvps", 0)
    if tbvps <= 0:
        return None
    fair_ptbv = 1.3  # money center bank average
    return _ok(fair_ptbv * tbvps,
               f"P/TBV {fair_ptbv}×TBV ${tbvps:.2f}",
               "price_to_tangible_book")


def price_to_book(d: dict) -> dict | None:
    """P/B × Book value (generic)."""
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return None
    fair_pb = 1.5
    return _ok(fair_pb * bvps, f"P/B {fair_pb}×BV ${bvps:.2f}", "price_to_book")


def price_to_book_capital_intensive(d: dict) -> dict | None:
    """Capital-intensive için daha düşük P/B."""
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return None
    fair_pb = 1.0  # energy, utility, auto — book closer to replacement
    return _ok(fair_pb * bvps,
               f"capital-intensive P/B {fair_pb}×BV ${bvps:.2f}",
               "price_to_book_capital_intensive")


# ─────────────────────────────────────────────────────────────────────────────
# REIT-SPECIFIC METHODS
# ─────────────────────────────────────────────────────────────────────────────

def p_ffo(d: dict) -> dict | None:
    """P/FFO: FFO = NI + Depreciation (GAAP distortion düzeltmesi)."""
    ni = d.get("ttm_ni", 0)
    depam = d.get("ttm_depam", 0)
    shares = d.get("shares", 0)

    if shares <= 0:
        return None
    ffo = ni + depam
    ffo_ps = ffo / shares
    if ffo_ps <= 0:
        return None

    fair_pffo = 18.0  # REIT average
    return _ok(fair_pffo * ffo_ps,
               f"P/FFO {fair_pffo}×FFO/sh ${ffo_ps:.2f}",
               "p_ffo")


def p_affo(d: dict) -> dict | None:
    """P/AFFO: AFFO ≈ FFO - maintenance capex (~50% of total capex)."""
    ni = d.get("ttm_ni", 0)
    depam = d.get("ttm_depam", 0)
    capex = d.get("ttm_capex", 0)
    shares = d.get("shares", 0)

    if shares <= 0:
        return None
    ffo = ni + depam
    # AFFO = FFO - maintenance capex. Maintenance ≈ 50% of capex for REITs
    affo = ffo - abs(capex) * 0.5
    affo_ps = affo / shares
    if affo_ps <= 0:
        return None

    fair_paffo = 20.0  # REIT premium
    return _ok(fair_paffo * affo_ps,
               f"P/AFFO {fair_paffo}×AFFO/sh ${affo_ps:.2f}",
               "p_affo")


def nav_cap_rate(d: dict) -> dict | None:
    """NAV using implied cap rate on NOI ≈ EBITDA."""
    ebitda = d.get("ttm_ebitda", 0)
    if ebitda <= 0:
        return None
    # Cap rate — 10Y yield + 150bp spread
    cap_rate = (d.get("bond_y", 4.5) / 100) + 0.015
    gross_value = ebitda / cap_rate
    equity = gross_value - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(equity / shares,
               f"NAV cap rate {cap_rate:.1%}",
               "nav_cap_rate")


# ─────────────────────────────────────────────────────────────────────────────
# DIVIDEND MODELS
# ─────────────────────────────────────────────────────────────────────────────

def dividend_discount(d: dict) -> dict | None:
    """Gordon Growth: P = D1 / (r - g)."""
    price = d.get("price", 0)
    div_y = d.get("div_yield", 0)
    if div_y <= 0.005:
        return None
    div = price * div_y  # current div
    g = 0.05  # growth
    r = 0.09  # required return
    if r <= g:
        return None
    d1 = div * (1 + g)
    return _ok(d1 / (r - g),
               f"DDM D1=${d1:.2f} r={r:.0%} g={g:.0%}",
               "dividend_discount")


def dividend_discount_gordon(d: dict) -> dict | None:
    """Aristocrat için Gordon — daha muhafazakar growth."""
    price = d.get("price", 0)
    div_y = d.get("div_yield", 0)
    if div_y <= 0.005:
        return None
    div = price * div_y
    g = 0.055  # aristocrat avg
    r = 0.08
    if r <= g:
        return None
    d1 = div * (1 + g)
    return _ok(d1 / (r - g),
               f"Gordon DDM g={g:.1%} r={r:.0%}",
               "dividend_discount_gordon")


# ─────────────────────────────────────────────────────────────────────────────
# FCF YIELD
# ─────────────────────────────────────────────────────────────────────────────

def fcf_yield(d: dict) -> dict | None:
    """Target FCF yield (5%) → implied price."""
    fcf = d.get("ttm_fcf", 0)
    shares = d.get("shares", 0)
    if fcf <= 0 or shares <= 0:
        return None
    fcf_ps = fcf / shares
    target_yield = 0.05
    return _ok(fcf_ps / target_yield,
               f"FCF yield target {target_yield:.0%}, FCF/sh ${fcf_ps:.2f}",
               "fcf_yield")


def fcf_yield_midcycle(d: dict) -> dict | None:
    """Döngüsel için ortalama FCF."""
    # Basit: TTM FCF önceki TTM ile ortalama
    avg_fcf = (d.get("ttm_fcf", 0) + d.get("prev_ttm_fcf", 0)) / 2
    shares = d.get("shares", 0)
    if avg_fcf <= 0 or shares <= 0:
        return None
    target_yield = 0.07  # cyclical higher yield demand
    return _ok((avg_fcf / shares) / target_yield,
               f"mid-cycle FCF yield {target_yield:.0%}",
               "fcf_yield_midcycle")


# ─────────────────────────────────────────────────────────────────────────────
# PEG FAMILY
# ─────────────────────────────────────────────────────────────────────────────

def peg_forward(d: dict) -> dict | None:
    """PEG fair = 1.0 → fair P/E = growth rate. P = fair P/E × EPS."""
    growth = d.get("rev_growth_ttm", 0)  # proxy
    fwd_eps = d.get("fwd_eps_ny1", 0)
    if growth <= 0 or fwd_eps <= 0:
        return None
    # Growth %25 → fair P/E 25
    fair_pe = min(growth * 100, 40)
    return _ok(fair_pe * fwd_eps,
               f"PEG=1 → P/E {fair_pe:.0f}×${fwd_eps:.2f}",
               "peg_forward")


def pegy(d: dict) -> dict | None:
    """PEGY: fair P/E = growth + dividend yield."""
    growth = d.get("rev_growth_ttm", 0) * 100
    div_y = d.get("div_yield", 0) * 100
    fwd_eps = d.get("fwd_eps_ny1", 0)
    if fwd_eps <= 0:
        return None
    fair_pe = max(8, min(growth + div_y, 35))
    return _ok(fair_pe * fwd_eps,
               f"PEGY={fair_pe:.0f}×${fwd_eps:.2f}",
               "pegy")


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL / COMPOSITE
# ─────────────────────────────────────────────────────────────────────────────

def rule_of_40_multiple(d: dict) -> dict | None:
    """Rule of 40 score → target EV/Revenue multiple."""
    rev_gr = d.get("rev_growth_ttm", 0) * 100
    fcf_m = d.get("fcf_margin", 0) * 100
    rof40 = rev_gr + fcf_m
    rev = d.get("ttm_rev", 0)
    if rof40 < 20 or rev <= 0:
        return None
    # Rule of 40 >40 → premium; <40 → discount
    fair_evrev = max(4, min(rof40 / 6, 20))  # 40→6.7x, 80→13x, 120→20x cap
    fair_ev = fair_evrev * rev
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"RoF40={rof40:.0f} → EV/Rev {fair_evrev:.1f}x",
               "rule_of_40_multiple")


def reserves_nav_pv10(d: dict) -> dict | None:
    """Oil/gas için reserves NAV (PV-10). FMP'de reserves verisi olmayabilir."""
    # FMP'de reserves data yok — fallback: 1.5× book value
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return None
    return _ok(bvps * 1.5,
               "reserves NAV proxy (1.5× BV)",
               "reserves_nav_pv10")


def rnpv_pipeline(d: dict) -> dict | None:
    """Biotech pipeline rNPV — FMP veri yok, cash-floor + basic."""
    cash_per_share = d.get("cash", 0) / max(d.get("shares", 1), 1)
    # Pre-revenue biotech için: cash + 2x mcap as pipeline value proxy
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return _ok(cash_per_share,
                   "rNPV: cash-only floor (no book value)",
                   "rnpv_pipeline")
    # Cash floor + option value
    return _ok(cash_per_share * 1.5,
               "rNPV proxy: cash × 1.5",
               "rnpv_pipeline")


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY — name → fn lookup
# ─────────────────────────────────────────────────────────────────────────────

METHOD_REGISTRY = {
    # Multiples
    "trailing_pe":               trailing_pe,
    "forward_pe_ny1":            forward_pe_ny1,
    "forward_pe_ny2":            forward_pe_ny2,
    "forward_pe_ny3":            forward_pe_ny3,
    "forward_pe_normalized":     forward_pe_normalized,
    "forward_pe_core_auto":      forward_pe_normalized,  # alias
    "normalized_pe_midcycle":    normalized_pe_midcycle,
    "normalized_pe_cyclical":    normalized_pe_cyclical,

    # EV/EBITDA
    "ev_ebitda":                 ev_ebitda,
    "ev_ebitda_forward":         ev_ebitda_forward,
    "ev_ebitda_midcycle":        ev_ebitda_midcycle,
    "ev_ebitda_reit":            ev_ebitda,  # alias
    "normalized_ev_ebitda":      ev_ebitda_midcycle,  # alias

    # EV/Revenue
    "ev_revenue":                ev_revenue,
    "ev_rev_growth_adjusted":    ev_rev_growth_adjusted,

    # DCF
    "dcf_2stage":                dcf_2stage,
    "dcf_multi_stage":           dcf_multi_stage,
    "dcf_multi_stage_aggressive": dcf_multi_stage_aggressive,
    "dcf_multi_stage_patent_cliff": dcf_multi_stage,  # alias
    "dcf_fcfe":                  dcf_multi_stage,  # simplified
    "dcf_strip_priced":          dcf_multi_stage,  # E&P placeholder
    "scenario_dcf_weighted":     dcf_multi_stage,  # TSLA placeholder

    # Banks
    "justified_pb":              justified_pb,
    "residual_income":           residual_income,
    "price_to_tangible_book":    price_to_tangible_book,
    "price_to_book":             price_to_book,
    "price_to_book_capital_intensive": price_to_book_capital_intensive,
    "price_to_book_vs_roe":      justified_pb,  # alias

    # REIT
    "p_ffo":                     p_ffo,
    "p_affo":                    p_affo,
    "nav_cap_rate":              nav_cap_rate,
    "book_value_mark_to_market": price_to_book,  # mREIT placeholder
    "implied_cap_rate":          nav_cap_rate,
    "p_ffo_vs_history":          p_ffo,
    "p_affo_vs_history":         p_affo,

    # Dividend
    "dividend_discount":         dividend_discount,
    "dividend_discount_gordon":  dividend_discount_gordon,
    "dividend_discount_affo":    dividend_discount,
    "dividend_discount_multistage": dividend_discount,

    # Yield
    "fcf_yield":                 fcf_yield,
    "fcf_yield_midcycle":        fcf_yield_midcycle,

    # PEG
    "peg_forward":               peg_forward,
    "pegy":                      pegy,

    # Special
    "rule_of_40_multiple":       rule_of_40_multiple,
    "reserves_nav_pv10":         reserves_nav_pv10,
    "reserves_nav_mining":       reserves_nav_pv10,  # alias
    "ev_per_ounce_reserves":     reserves_nav_pv10,
    "ev_per_pipeline_asset":     rnpv_pipeline,
    "rnpv_pipeline":             rnpv_pipeline,
    "rnpv_pipeline_plus_mature": rnpv_pipeline,
    "cash_adjusted_cap_vs_rnpv": rnpv_pipeline,
    "real_options_pipeline":     rnpv_pipeline,
    "ma_comp_per_indication":    rnpv_pipeline,

    # Placeholders/simplified
    "sum_of_parts":              dcf_2stage,
    "sum_of_parts_scenario":     dcf_2stage,
    "sum_of_parts_gov_commercial": dcf_2stage,
    "reverse_dcf":               dcf_2stage,
    "ma_comp_multiples":         ev_ebitda,
    "peer_relative":              ev_ebitda,
    "peer_auto_multiples":        ev_ebitda,
    "pe_vs_history_10y":         forward_pe_ny1,
    "ev_ebitdax":                ev_ebitda,  # E&P
    "ev_production":             ev_revenue,  # proxy
    "price_to_nav":              price_to_book,
    "price_to_aum":              price_to_book,
    "spread_leverage_duration":  price_to_book,  # mREIT placeholder
    "p_distributable_earnings":  dividend_discount,
    "p_distributable_cash_flow": fcf_yield,
    "rate_base_allowed_roe":     justified_pb,  # utility proxy
    "embedded_value":            justified_pb,  # insurer proxy
    "asset_based_nav":           price_to_book,
    "merton_option_pricing":     price_to_book,
    "forward_pe_midcycle":       normalized_pe_midcycle,
}


def get_method(name: str):
    """Method name → fn. None dönerse exclude edilmiş demektir."""
    return METHOD_REGISTRY.get(name)
