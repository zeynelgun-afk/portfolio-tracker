"""
Finzora Valuation Framework v5 — Methods Registry
===================================================
Her valuation metodu bağımsız bir fonksiyon:
  signature: (data: dict, archetype: str = "generic_equity") -> dict | None
  return: {"fair_value": float, "notes": str, "method": str}
          None → metot uygulanamaz (veri yetersiz)

Framework aggregator bu fonksiyonları çağırıp sonuçları ağırlıklandırır.
Tuning parametreleri agent/valuation/tuning.py içinde per-archetype.
"""

from __future__ import annotations
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from valuation.tuning import get_tuning, get_param
except ImportError:
    # Fallback — tuning yoksa generic değerlerle çalış
    def get_tuning(_): return {}
    def get_param(_, key, default): return default


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

def trailing_pe(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Trailing P/E × TTM EPS → fair value."""
    eps = d.get("eps_ttm", 0)
    if eps <= 0:
        return None
    fair_pe = get_param(archetype, "fwd_pe_fair", 18.0)
    return _ok(fair_pe * eps, f"P/E {fair_pe:.1f}×EPS ${eps:.2f} [{archetype}]", "trailing_pe")


def forward_pe_ny1(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Forward P/E NY1 × fwd EPS — archetype-specific multiplier."""
    eps = d.get("fwd_eps_ny1", 0)
    if eps <= 0:
        return None
    fair_pe = get_param(archetype, "fwd_pe_fair", 18.0)
    return _ok(fair_pe * eps, f"fwd P/E NY1 {fair_pe:.1f}×${eps:.2f} [{archetype}]", "forward_pe_ny1")


def forward_pe_ny2(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Forward P/E NY2 × fwd EPS — archetype-specific multiplier + WACC discount."""
    eps = d.get("fwd_eps_ny2", 0)
    if eps <= 0:
        return None
    fair_pe = get_param(archetype, "fwd_pe_ny2", 17.0)
    wacc = get_param(archetype, "wacc", 0.10)
    discount = 1.0 / (1.0 + wacc)  # NY2 = 2. yıl EPS, 1 yıl iskonto (NY1→NY2 arası)
    return _ok(fair_pe * eps * discount,
               f"fwd P/E NY2 {fair_pe:.1f}×${eps:.2f}×disc(wacc={wacc:.0%}) [{archetype}]",
               "forward_pe_ny2")


def forward_pe_ny3(d: dict, archetype: str = "generic_equity") -> dict | None:
    """NY3 — hyper-growth için kritik. WACC^2 iskonto."""
    eps = d.get("fwd_eps_ny3", 0)
    if eps <= 0:
        return None
    fair_pe = get_param(archetype, "fwd_pe_ny3", 16.0)
    wacc = get_param(archetype, "wacc", 0.10)
    discount = 1.0 / ((1.0 + wacc) ** 2)  # NY3 = 3. yıl EPS, 2 yıl iskonto
    return _ok(fair_pe * eps * discount,
               f"fwd P/E NY3 {fair_pe:.1f}×${eps:.2f}×disc²(wacc={wacc:.0%}) [{archetype}]",
               "forward_pe_ny3")


def forward_pe_normalized(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Normalize edilmiş P/E — bank/insurer için COE-bazlı."""
    eps = d.get("fwd_eps_ny1", 0)
    if eps <= 0:
        return None
    fair_pe = get_param(archetype, "fwd_pe_fair", 11.0)
    return _ok(fair_pe * eps, f"normalized P/E {fair_pe:.1f}×${eps:.2f} [{archetype}]",
               "forward_pe_normalized")


def normalized_pe_midcycle(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Döngüsel şirketler için 3-5 yıl ortalama EPS × fair multiple."""
    eps_annual = d.get("eps_annual", [])
    if len(eps_annual) < 2 or all(e <= 0 for e in eps_annual):
        return None
    valid = [e for e in eps_annual if e > 0]
    if not valid:
        return None
    norm_eps = sum(valid) / len(valid)
    fair_pe = get_param(archetype, "fwd_pe_fair", 15.0)
    return _ok(fair_pe * norm_eps,
               f"mid-cycle EPS avg ${norm_eps:.2f} × {fair_pe:.1f} [{archetype}]",
               "normalized_pe_midcycle")


def normalized_pe_cyclical(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Döngüsel için normalize edilmiş P/E — LTM peak/trough tespiti."""
    eps_annual = d.get("eps_annual", [])
    valid = [e for e in eps_annual if e > 0]
    if len(valid) < 2:
        return None
    avg_eps = sum(valid) / len(valid)
    ttm_eps = d.get("eps_ttm", 0)

    if ttm_eps > avg_eps * 1.5:
        used_eps = avg_eps
        notes = f"PEAK detected, normalized to avg ${avg_eps:.2f}"
    elif ttm_eps < avg_eps * 0.5:
        used_eps = avg_eps
        notes = f"TROUGH detected, normalized to avg ${avg_eps:.2f}"
    else:
        used_eps = ttm_eps
        notes = f"mid-cycle, using TTM ${ttm_eps:.2f}"

    fair_pe = get_param(archetype, "fwd_pe_fair", 14.0)
    return _ok(fair_pe * used_eps, f"{notes} × {fair_pe:.1f} [{archetype}]",
               "normalized_pe_cyclical")


# ─────────────────────────────────────────────────────────────────────────────
# EV/EBITDA FAMILY
# ─────────────────────────────────────────────────────────────────────────────

def ev_ebitda(d: dict, archetype: str = "generic_equity") -> dict | None:
    """EV/EBITDA × TTM EBITDA → EV → equity value."""
    ebitda = d.get("ttm_ebitda", 0)
    if ebitda <= 0:
        return None
    fair_multiple = get_param(archetype, "ev_ebitda_fair", 12.0)
    fair_ev = fair_multiple * ebitda
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"EV/EBITDA {fair_multiple:.1f}×${ebitda/1e9:.1f}B [{archetype}]",
               "ev_ebitda")


def ev_ebitda_forward(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Forward EV/EBITDA — growth için daha uygun."""
    ebitda = d.get("ttm_ebitda", 0)
    if ebitda <= 0:
        return None
    rev_gr = d.get("rev_growth_ttm", 0.1)
    fwd_ebitda = ebitda * (1 + min(rev_gr, 0.8))
    fair_multiple = get_param(archetype, "ev_ebitda_fwd", 15.0)
    fair_ev = fair_multiple * fwd_ebitda
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"fwd EV/EBITDA {fair_multiple:.1f}×${fwd_ebitda/1e9:.1f}B (gr={rev_gr:.0%}) [{archetype}]",
               "ev_ebitda_forward")


def ev_ebitda_midcycle(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Döngüsel şirketler için ortalama EBITDA."""
    ebitda_annual = d.get("ebitda_annual", [])
    valid = [e for e in ebitda_annual if e > 0]
    if not valid:
        return None
    norm_ebitda = sum(valid) / len(valid)
    fair_multiple = get_param(archetype, "ev_ebitda_fair", 8.0)
    fair_ev = fair_multiple * norm_ebitda
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"mid-cycle EV/EBITDA {fair_multiple:.1f}×avg${norm_ebitda/1e9:.1f}B [{archetype}]",
               "ev_ebitda_midcycle")


# ─────────────────────────────────────────────────────────────────────────────
# EV / REVENUE FAMILY
# ─────────────────────────────────────────────────────────────────────────────

def ev_revenue(d: dict, archetype: str = "generic_equity") -> dict | None:
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


def ev_rev_growth_adjusted(d: dict, archetype: str = "generic_equity") -> dict | None:
    """EV/Revenue × Revenue adjusted by growth rate (hyper-growth için)."""
    rev = d.get("ttm_rev", 0)
    growth = d.get("rev_growth_ttm", 0)
    if rev <= 0 or growth <= 0.1:
        return None
    fair_multiple = min(growth * 30, 20.0)
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

def dcf_2stage(d: dict, archetype: str = "generic_equity") -> dict | None:
    """2-stage DCF: 5 yıl yüksek büyüme + terminal. Archetype-specific WACC."""
    fcf = d.get("ttm_fcf", 0)
    if fcf <= 0:
        return None

    adj_fcf = d.get("fcf_adjusted_sbc", fcf)
    if adj_fcf <= 0:
        return None

    growth = min(max(d.get("rev_growth_ttm", 0.08), 0.02), 0.15)
    wacc = get_param(archetype, "wacc", 0.09)
    terminal_growth = get_param(archetype, "terminal_growth", 0.03)
    terminal_growth = min(terminal_growth, d.get("bond_y", 4.5) / 100)
    # Gordon growth model: WACC > terminal_growth zorunlu (pozitif discount)
    # Eğer tuning hatası ile yakınsa, minimum 1% fark garantile
    if wacc <= terminal_growth + 0.005:
        terminal_growth = wacc - 0.02  # mecburen düşür

    pv = 0
    cur_fcf = adj_fcf
    for yr in range(1, 6):
        cur_fcf *= (1 + growth)
        pv += cur_fcf / ((1 + wacc) ** yr)

    tv_fcf = cur_fcf * (1 + terminal_growth)
    tv = tv_fcf / (wacc - terminal_growth)
    pv_tv = tv / ((1 + wacc) ** 5)

    ev = pv + pv_tv
    equity = ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(equity / shares,
               f"DCF 2-stage g={growth:.0%} wacc={wacc:.0%} tg={terminal_growth:.0%} [{archetype}]",
               "dcf_2stage")


def dcf_multi_stage(d: dict, archetype: str = "generic_equity") -> dict | None:
    """3-stage DCF: yüksek → orta → terminal (mature growth için)."""
    fcf = d.get("fcf_adjusted_sbc", d.get("ttm_fcf", 0))
    if fcf <= 0:
        return None

    stage1_gr = min(max(d.get("rev_growth_ttm", 0.12), 0.05), 0.25)
    stage2_gr = 0.08
    wacc = get_param(archetype, "wacc", 0.09)
    terminal_gr = get_param(archetype, "terminal_growth", 0.025)
    # Gordon guard: wacc > terminal_gr zorunlu
    if wacc <= terminal_gr + 0.005:
        terminal_gr = wacc - 0.02

    pv = 0
    cur = fcf
    for yr in range(1, 6):
        cur *= (1 + stage1_gr)
        pv += cur / ((1 + wacc) ** yr)
    for yr in range(6, 11):
        cur *= (1 + stage2_gr)
        pv += cur / ((1 + wacc) ** yr)
    tv = (cur * (1 + terminal_gr)) / (wacc - terminal_gr)
    pv_tv = tv / ((1 + wacc) ** 10)

    ev = pv + pv_tv
    equity = ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(equity / shares,
               f"DCF 3-stage {stage1_gr:.0%}/{stage2_gr:.0%}/{terminal_gr:.1%} wacc={wacc:.0%} [{archetype}]",
               "dcf_multi_stage")


def dcf_multi_stage_aggressive(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Hyper-growth için agresif DCF — hızlı fade."""
    fcf = d.get("fcf_adjusted_sbc", d.get("ttm_fcf", 0))

    if fcf <= 0:
        rev = d.get("ttm_rev", 0)
        if rev <= 0:
            return None
        fcf = rev * 0.20  # target FCF margin %20

    stages = [(0.50, 3), (0.30, 3), (0.15, 4)]
    wacc = get_param(archetype, "wacc", 0.10)
    terminal_gr = get_param(archetype, "terminal_growth", 0.03)
    # Gordon guard
    if wacc <= terminal_gr + 0.005:
        terminal_gr = wacc - 0.02

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
               f"DCF aggressive 50→30→15→{terminal_gr:.0%} wacc={wacc:.0%} [{archetype}]",
               "dcf_multi_stage_aggressive")


# ─────────────────────────────────────────────────────────────────────────────
# BANK-SPECIFIC METHODS
# ─────────────────────────────────────────────────────────────────────────────

def justified_pb(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Justified P/B = (ROE - g) / (COE - g) × book value. Archetype-specific COE."""
    roe = d.get("roe", 0)
    bvps = d.get("bvps", 0)
    if roe <= 0 or bvps <= 0:
        return None

    growth = get_param(archetype, "long_growth", 0.05)
    coe = get_param(archetype, "coe", 0.10)

    if coe <= growth:
        return None

    justified = (roe - growth) / (coe - growth)
    justified = max(0.5, min(justified, 4.0))

    return _ok(justified * bvps,
               f"Just P/B {justified:.2f}×BV ${bvps:.2f} (ROE={roe:.0%}, COE={coe:.0%}) [{archetype}]",
               "justified_pb")


def residual_income(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Residual Income = BV + Σ PV(excess earnings)."""
    bvps = d.get("bvps", 0)
    roe = d.get("roe", 0)
    if bvps <= 0 or roe <= 0:
        return None

    coe = get_param(archetype, "coe", 0.10)
    excess_roe = roe - coe
    if excess_roe <= 0:
        return _ok(bvps, f"RI: no excess return, = BV ${bvps:.2f}", "residual_income")

    pv_excess = 0
    cur_bvps = bvps
    for yr in range(1, 11):
        fade = max(0, excess_roe * (1 - yr * 0.08))
        excess_earnings = cur_bvps * fade
        pv_excess += excess_earnings / ((1 + coe) ** yr)
        cur_bvps *= (1 + (roe * (1 - d.get("payout_ratio", 0.3))))

    return _ok(bvps + pv_excess,
               f"RI BV ${bvps:.2f} + PV ${pv_excess:.2f} (COE={coe:.0%}) [{archetype}]",
               "residual_income")


def price_to_tangible_book(d: dict, archetype: str = "generic_equity") -> dict | None:
    """P/TBV — bankalar için goodwill'den arındırılmış."""
    tbvps = d.get("tangible_bvps", 0)
    if tbvps <= 0:
        return None
    fair_ptbv = get_param(archetype, "p_tbv_fair", 1.3)
    return _ok(fair_ptbv * tbvps,
               f"P/TBV {fair_ptbv:.1f}×TBV ${tbvps:.2f} [{archetype}]",
               "price_to_tangible_book")


def price_to_book(d: dict, archetype: str = "generic_equity") -> dict | None:
    """P/B × Book value (generic)."""
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return None
    fair_pb = get_param(archetype, "pb_fair", 1.5)
    if fair_pb is None:
        return None
    return _ok(fair_pb * bvps, f"P/B {fair_pb:.1f}×BV ${bvps:.2f} [{archetype}]",
               "price_to_book")


def price_to_book_capital_intensive(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Capital-intensive için daha düşük P/B."""
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return None
    fair_pb = get_param(archetype, "pb_fair", 1.0)
    if fair_pb is None:
        return None
    return _ok(fair_pb * bvps,
               f"capital-intensive P/B {fair_pb:.1f}×BV ${bvps:.2f} [{archetype}]",
               "price_to_book_capital_intensive")


# ─────────────────────────────────────────────────────────────────────────────
# REIT-SPECIFIC METHODS
# ─────────────────────────────────────────────────────────────────────────────

def p_ffo(d: dict, archetype: str = "generic_equity") -> dict | None:
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

    fair_pffo = get_param(archetype, "p_ffo_fair", 18.0)
    return _ok(fair_pffo * ffo_ps,
               f"P/FFO {fair_pffo:.1f}×FFO/sh ${ffo_ps:.2f} [{archetype}]",
               "p_ffo")


def p_affo(d: dict, archetype: str = "generic_equity") -> dict | None:
    """P/AFFO: AFFO ≈ FFO - maintenance capex (~50% of total capex)."""
    ni = d.get("ttm_ni", 0)
    depam = d.get("ttm_depam", 0)
    capex = d.get("ttm_capex", 0)
    shares = d.get("shares", 0)

    if shares <= 0:
        return None
    ffo = ni + depam
    affo = ffo - abs(capex) * 0.5
    affo_ps = affo / shares
    if affo_ps <= 0:
        return None

    fair_paffo = get_param(archetype, "p_affo_fair", 20.0)
    return _ok(fair_paffo * affo_ps,
               f"P/AFFO {fair_paffo:.1f}×AFFO/sh ${affo_ps:.2f} [{archetype}]",
               "p_affo")


def nav_cap_rate(d: dict, archetype: str = "generic_equity") -> dict | None:
    """NAV using implied cap rate on NOI ≈ EBITDA."""
    ebitda = d.get("ttm_ebitda", 0)
    if ebitda <= 0:
        return None
    spread = get_param(archetype, "cap_rate_spread", 0.015)
    cap_rate = (d.get("bond_y", 4.5) / 100) + spread
    gross_value = ebitda / cap_rate
    equity = gross_value - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(equity / shares,
               f"NAV cap rate {cap_rate:.1%} [{archetype}]",
               "nav_cap_rate")


# ─────────────────────────────────────────────────────────────────────────────
# DIVIDEND MODELS
# ─────────────────────────────────────────────────────────────────────────────

def dividend_discount(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Gordon Growth: P = D1 / (r - g)."""
    price = d.get("price", 0)
    div_y = d.get("div_yield", 0)
    if div_y <= 0.005:
        return None
    div = price * div_y
    g = get_param(archetype, "long_growth", 0.05)
    r = get_param(archetype, "coe", 0.09)
    if r <= g:
        return None
    d1 = div * (1 + g)
    return _ok(d1 / (r - g),
               f"DDM D1=${d1:.2f} r={r:.0%} g={g:.0%} [{archetype}]",
               "dividend_discount")


def dividend_discount_gordon(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Aristocrat için Gordon — daha muhafazakar growth."""
    price = d.get("price", 0)
    div_y = d.get("div_yield", 0)
    if div_y <= 0.005:
        return None
    div = price * div_y
    g = get_param(archetype, "long_growth", 0.055)
    r = get_param(archetype, "coe", 0.08)
    if r <= g:
        return None
    d1 = div * (1 + g)
    return _ok(d1 / (r - g),
               f"Gordon DDM g={g:.1%} r={r:.0%} [{archetype}]",
               "dividend_discount_gordon")


# ─────────────────────────────────────────────────────────────────────────────
# FCF YIELD
# ─────────────────────────────────────────────────────────────────────────────

def fcf_yield(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Target FCF yield → implied price. Archetype-specific."""
    fcf = d.get("ttm_fcf", 0)
    shares = d.get("shares", 0)
    if fcf <= 0 or shares <= 0:
        return None
    fcf_ps = fcf / shares
    target_yield = get_param(archetype, "fcf_yield_target", 0.05)
    return _ok(fcf_ps / target_yield,
               f"FCF yield target {target_yield:.1%}, FCF/sh ${fcf_ps:.2f} [{archetype}]",
               "fcf_yield")


def fcf_yield_midcycle(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Döngüsel için ortalama FCF."""
    avg_fcf = (d.get("ttm_fcf", 0) + d.get("prev_ttm_fcf", 0)) / 2
    shares = d.get("shares", 0)
    if avg_fcf <= 0 or shares <= 0:
        return None
    target_yield = get_param(archetype, "fcf_yield_target", 0.07)
    return _ok((avg_fcf / shares) / target_yield,
               f"mid-cycle FCF yield {target_yield:.1%} [{archetype}]",
               "fcf_yield_midcycle")


# ─────────────────────────────────────────────────────────────────────────────
# PEG FAMILY (growth-driven, tuning bağımsız)
# ─────────────────────────────────────────────────────────────────────────────

def peg_forward(d: dict, archetype: str = "generic_equity") -> dict | None:
    """PEG fair = 1.0 → fair P/E = growth rate. P = fair P/E × EPS."""
    growth = d.get("rev_growth_ttm", 0)
    fwd_eps = d.get("fwd_eps_ny1", 0)
    if growth <= 0 or fwd_eps <= 0:
        return None
    fair_pe = min(growth * 100, 40)
    return _ok(fair_pe * fwd_eps,
               f"PEG=1 → P/E {fair_pe:.0f}×${fwd_eps:.2f}",
               "peg_forward")


def pegy(d: dict, archetype: str = "generic_equity") -> dict | None:
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

def rule_of_40_multiple(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Rule of 40 score → target EV/Revenue multiple."""
    rev_gr = d.get("rev_growth_ttm", 0) * 100
    fcf_m = d.get("fcf_margin", 0) * 100
    rof40 = rev_gr + fcf_m
    rev = d.get("ttm_rev", 0)
    if rof40 < 20 or rev <= 0:
        return None
    fair_evrev = max(4, min(rof40 / 6, 20))
    fair_ev = fair_evrev * rev
    fair_equity = fair_ev - d.get("net_debt", 0)
    shares = d.get("shares", 0)
    if shares <= 0:
        return None
    return _ok(fair_equity / shares,
               f"RoF40={rof40:.0f} → EV/Rev {fair_evrev:.1f}x",
               "rule_of_40_multiple")


def reserves_nav_pv10(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Oil/gas için reserves NAV (PV-10)."""
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return None
    return _ok(bvps * 1.5, "reserves NAV proxy (1.5× BV)", "reserves_nav_pv10")


def rnpv_pipeline(d: dict, archetype: str = "generic_equity") -> dict | None:
    """Biotech pipeline rNPV — FMP veri yok."""
    cash_per_share = d.get("cash", 0) / max(d.get("shares", 1), 1)
    bvps = d.get("bvps", 0)
    if bvps <= 0:
        return _ok(cash_per_share, "rNPV: cash-only floor", "rnpv_pipeline")
    return _ok(cash_per_share * 1.5, "rNPV proxy: cash × 1.5", "rnpv_pipeline")


# ─────────────────────────────────────────────────────────────────────────────
# PRE-REVENUE / NAV-TABANLI METOTLAR (v7)
# ─────────────────────────────────────────────────────────────────────────────

def nav_per_share_adjusted(d: dict, archetype: str = "generic_equity") -> dict | None:
    """
    Düzeltilmiş NAV per share (pre-revenue için ana metot).

    NAV = (cash + long_term_investments) - (total_liabilities - deferred_tax)
    Mantık: ertelenmiş vergi gerçek bir nakit yükümlülüğü değil, JV gain üzerine
    teorik vergidir. JV satılana kadar ödenmez. Bu nedenle NAV hesabında
    yumuşatılır (çıkarılırken).
    """
    cash = d.get("cash", 0)
    lt_inv = d.get("long_term_investments", 0)
    total_liab = d.get("total_liabilities", 0)
    deferred_tax = d.get("deferred_tax_liab", 0)
    shares = d.get("shares", 0)

    if shares <= 0 or (cash + lt_inv) <= 0:
        return None

    # Düzeltilmiş yükümlülük = total_liab - deferred_tax × 0.5
    # (yarısı diskontla, çünkü gerçekleşmesi belirsiz)
    adjusted_liab = total_liab - (deferred_tax * 0.5)
    nav = (cash + lt_inv) - adjusted_liab
    nav_ps = nav / shares
    if nav_ps <= 0:
        return None
    return _ok(nav_ps,
               f"NAV: (nakit ${cash/1e6:.0f}M + LT yatırım ${lt_inv/1e6:.0f}M "
               f"- düzelt. yükümlülük ${adjusted_liab/1e6:.0f}M) / {shares/1e6:.0f}M hisse",
               "nav_per_share_adjusted")


def cash_plus_runway(d: dict, archetype: str = "generic_equity") -> dict | None:
    """
    Nakit + 2 yıllık burn hakkı için kalan değer.
    Pre-revenue şirketin "tabanı" gibi davranır.

    fair_value = cash_per_share + (option_value × cash_per_share × 0.5)
    burn rate yüksekse penalty.
    """
    cash = d.get("cash", 0)
    fcf = d.get("ttm_fcf", 0)  # negatif olur pre-revenue'da
    shares = d.get("shares", 0)
    if shares <= 0 or cash <= 0:
        return None

    cash_ps = cash / shares
    # Burn rate negatif FCF'in mutlak değeri
    burn = abs(min(fcf, 0))
    runway_years = (cash / burn) if burn > 0 else 999

    # Runway < 1 yıl → ciddi risk, sadece nakit değeri
    # Runway 1-2 yıl → cash_ps × 1.0
    # Runway 2+ yıl → cash_ps × 1.3 (zaman var, opsiyon değeri)
    if runway_years < 1.0:
        mult = 0.85
        note = f"runway {runway_years:.1f}y (KRİTİK)"
    elif runway_years < 2.0:
        mult = 1.0
        note = f"runway {runway_years:.1f}y"
    elif runway_years < 4.0:
        mult = 1.2
        note = f"runway {runway_years:.1f}y (yeterli)"
    else:
        mult = 1.3
        note = f"runway {runway_years:.1f}y (rahat)"

    return _ok(cash_ps * mult,
               f"cash/sh ${cash_ps:.2f} × {mult:.2f} ({note})",
               "cash_plus_runway")


def analyst_target_method(d: dict, archetype: str = "generic_equity") -> dict | None:
    """
    Analist hedef fiyatı (sanity check metodu).
    Düşük güven (özellikle pre-revenue'da tek analist olabilir),
    bu yüzden sanity tier olarak kullanılmalı.
    """
    target = d.get("price_target_consensus", 0)
    if target <= 0:
        return None
    n_analysts = d.get("price_target_count", 1)
    note = f"konsensüs ${target:.2f} ({n_analysts} analist)"
    return _ok(target, note, "analyst_target_method")


def tangible_book_capped(d: dict, archetype: str = "generic_equity") -> dict | None:
    """
    Maddi defter değeri × archetype P/B çarpanı, ama dilüsyon penaltısı ile.

    Pre-revenue şirketler genelde sürekli hisse ihraç eder. Son yıldaki
    hisse büyüme oranı yüksekse (>%15) penalty uygula.
    """
    tbvps = d.get("tangible_bvps", 0)
    if tbvps <= 0:
        return None

    fair_pb = get_param(archetype, "p_b_fair", 1.2)
    base = tbvps * fair_pb

    # Dilüsyon kontrolü: shares büyümesi
    shares_growth = d.get("shares_growth_yoy", 0)
    if shares_growth > 0.15:
        penalty = 1 - min(0.30, (shares_growth - 0.15))
        base *= penalty
        note = f"TBV ${tbvps:.2f} × {fair_pb:.1f} × dilution_penalty {penalty:.2f}"
    else:
        note = f"TBV ${tbvps:.2f} × P/B {fair_pb:.1f}"
    return _ok(base, note, "tangible_book_capped")


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

    # Pre-revenue / NAV (v7)
    "nav_per_share_adjusted":    nav_per_share_adjusted,
    "cash_plus_runway":          cash_plus_runway,
    "analyst_target_method":     analyst_target_method,
    "tangible_book_capped":      tangible_book_capped,

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
