"""
Finzora Valuation Framework v5.2 — Archetype-Specific Tuning
==============================================================
Her arketipin kendi multiplier/WACC/growth bantları olmalı.
Generic `100/bond_yield` veya `18x P/E` tüm şirketlere uygulamak hata.

Damodaran'ın Ocak 2025 US industry datasetlerinden referans ranges.
Bu parametreler backtest ile iteratif olarak güncellenir.
"""

# ─────────────────────────────────────────────────────────────────────────────
# ARKETIP BAZLI TUNING
# ─────────────────────────────────────────────────────────────────────────────
#
# Fields:
#   wacc:            DCF için maliyet sermayesi
#   terminal_growth: DCF terminal büyüme (risk-free cap)
#   fwd_pe_fair:     NY1 forward P/E fair multiple
#   fwd_pe_ny2:      NY2 multiple (growth ayarlı)
#   ev_ebitda_fair:  Trailing EV/EBITDA
#   ev_ebitda_fwd:   Forward EV/EBITDA
#   fcf_yield_target: Target FCF yield
#   coe:             Cost of equity (banka/REIT/utility için)
#   pb_fair:         Fair P/B multiple

TUNING = {

    # ── Hyper-growth tech/semi ────────────────────────────────────────
    "hyper_growth_software": {
        "wacc": 0.11, "terminal_growth": 0.03,
        "fwd_pe_fair": 55.0, "fwd_pe_ny2": 45.0, "fwd_pe_ny3": 35.0,
        "ev_ebitda_fair": 40.0, "ev_ebitda_fwd": 35.0,
        "fcf_yield_target": 0.025,
        "pb_fair": None,  # asset-light
    },
    "hyper_growth_semi": {
        "wacc": 0.10, "terminal_growth": 0.03,
        "fwd_pe_fair": 40.0, "fwd_pe_ny2": 35.0, "fwd_pe_ny3": 28.0,
        "ev_ebitda_fair": 30.0, "ev_ebitda_fwd": 25.0,
        "fcf_yield_target": 0.03,
        "pb_fair": None,
    },
    "software_dual_channel": {
        "wacc": 0.11, "terminal_growth": 0.03,
        "fwd_pe_fair": 60.0, "fwd_pe_ny2": 50.0, "fwd_pe_ny3": 40.0,
        "ev_ebitda_fair": 50.0, "ev_ebitda_fwd": 40.0,
        "fcf_yield_target": 0.02,
        "pb_fair": None,
    },

    # ── Profitable growth tech ────────────────────────────────────────
    "profitable_growth_software": {
        "wacc": 0.09, "terminal_growth": 0.03,
        "fwd_pe_fair": 30.0, "fwd_pe_ny2": 28.0, "fwd_pe_ny3": 25.0,
        "ev_ebitda_fair": 22.0, "ev_ebitda_fwd": 20.0,
        "fcf_yield_target": 0.035,
        "pb_fair": None,
    },

    # ── Mature megacap tech (MSFT, GOOGL, META, AAPL) ────────────────
    "mature_megacap_tech": {
        "wacc": 0.08, "terminal_growth": 0.03,  # lower WACC for mature
        "fwd_pe_fair": 30.0, "fwd_pe_ny2": 28.0, "fwd_pe_ny3": 26.0,
        "ev_ebitda_fair": 20.0, "ev_ebitda_fwd": 18.0,
        "fcf_yield_target": 0.03,  # 3% FCF yield for megacap (not 5%)
        "pb_fair": None,
    },

    "mature_semi": {
        "wacc": 0.09, "terminal_growth": 0.025,
        "fwd_pe_fair": 18.0, "fwd_pe_ny2": 17.0, "fwd_pe_ny3": 16.0,
        "ev_ebitda_fair": 14.0, "ev_ebitda_fwd": 13.0,
        "fcf_yield_target": 0.05,
        "pb_fair": 3.0,
    },

    # ── Banks ─────────────────────────────────────────────────────────
    "money_center_bank": {
        "wacc": 0.10, "terminal_growth": 0.03,
        "fwd_pe_fair": 13.0, "fwd_pe_ny2": 12.0, "fwd_pe_ny3": 11.0,
        "coe": 0.095, "long_growth": 0.05,
        "pb_fair": 1.8, "p_tbv_fair": 2.0,
        "div_yield_target": 0.025,
    },
    "regional_bank": {
        "wacc": 0.10, "terminal_growth": 0.025,
        "fwd_pe_fair": 11.0, "fwd_pe_ny2": 10.5, "fwd_pe_ny3": 10.0,
        "coe": 0.10, "long_growth": 0.04,
        "pb_fair": 1.4, "p_tbv_fair": 1.6,
        "div_yield_target": 0.03,
    },
    "insurer_life": {
        "wacc": 0.09, "terminal_growth": 0.025,
        "fwd_pe_fair": 10.0, "fwd_pe_ny2": 9.5,
        "coe": 0.09, "long_growth": 0.03,
        "pb_fair": 1.0, "p_tbv_fair": 1.1,
        "div_yield_target": 0.035,
    },
    "insurer_pc": {
        "wacc": 0.09, "terminal_growth": 0.025,
        "fwd_pe_fair": 13.0, "fwd_pe_ny2": 12.5,
        "coe": 0.09, "long_growth": 0.035,
        "pb_fair": 1.5, "p_tbv_fair": 1.7,
        "div_yield_target": 0.025,
    },
    "asset_manager": {
        "wacc": 0.09, "terminal_growth": 0.03,
        "fwd_pe_fair": 18.0, "fwd_pe_ny2": 17.0,
        "ev_ebitda_fair": 14.0, "ev_ebitda_fwd": 13.0,
        "fcf_yield_target": 0.045,
        "pb_fair": 3.5,
    },

    # ── REITs ─────────────────────────────────────────────────────────
    "reit_equity": {
        "wacc": 0.07, "terminal_growth": 0.03,
        "p_ffo_fair": 18.0, "p_affo_fair": 20.0,
        "cap_rate_spread": 0.015,
        "coe": 0.08, "div_yield_target": 0.045,
    },
    "reit_net_lease": {
        "wacc": 0.065, "terminal_growth": 0.025,
        "p_ffo_fair": 17.0, "p_affo_fair": 19.0,
        "cap_rate_spread": 0.015,
        "coe": 0.075, "div_yield_target": 0.05,
    },
    "reit_mortgage": {
        "wacc": 0.10, "terminal_growth": 0.02,
        "pb_fair": 1.0, "p_tbv_fair": 1.0,
        "coe": 0.11, "div_yield_target": 0.11,
    },

    # ── Utilities ─────────────────────────────────────────────────────
    "utility_regulated": {
        "wacc": 0.06, "terminal_growth": 0.025,
        "fwd_pe_fair": 17.0, "fwd_pe_ny2": 16.5,
        "coe": 0.07, "long_growth": 0.05,
        "pb_fair": 1.8, "div_yield_target": 0.04,
    },

    # ── Energy ────────────────────────────────────────────────────────
    "energy_upstream_ep": {
        "wacc": 0.10, "terminal_growth": 0.02,
        "fwd_pe_fair": 10.0, "fwd_pe_ny2": 9.5,  # mid-cycle
        "ev_ebitda_fair": 5.0, "ev_ebitda_fwd": 5.5,  # midcycle
        "fcf_yield_target": 0.10,
        "pb_fair": 1.3,
    },
    "energy_integrated": {
        "wacc": 0.08, "terminal_growth": 0.02,
        "fwd_pe_fair": 12.0, "fwd_pe_ny2": 11.5,
        "ev_ebitda_fair": 6.0, "ev_ebitda_fwd": 6.0,
        "fcf_yield_target": 0.08, "div_yield_target": 0.04,
        "pb_fair": 1.5,
    },
    "energy_midstream": {
        "wacc": 0.075, "terminal_growth": 0.025,
        "fwd_pe_fair": 13.0, "fwd_pe_ny2": 12.0,
        "ev_ebitda_fair": 10.0, "ev_ebitda_fwd": 9.5,
        "fcf_yield_target": 0.07, "div_yield_target": 0.06,
        "pb_fair": 2.0,
    },

    # ── Pharma / Biotech ──────────────────────────────────────────────
    "biotech_preclinical": {
        "wacc": 0.14, "terminal_growth": 0.02,
        "pb_fair": 3.0,  # cash-floor proxy
    },
    "biotech_commercial": {
        "wacc": 0.10, "terminal_growth": 0.025,
        "fwd_pe_fair": 18.0, "fwd_pe_ny2": 16.0,
        "ev_ebitda_fair": 13.0, "ev_ebitda_fwd": 12.0,
        "fcf_yield_target": 0.05,
    },
    "pharma_big": {
        "wacc": 0.08, "terminal_growth": 0.025,
        "fwd_pe_fair": 15.0, "fwd_pe_ny2": 14.5,
        "ev_ebitda_fair": 12.0, "ev_ebitda_fwd": 11.0,
        "fcf_yield_target": 0.055, "div_yield_target": 0.035,
    },

    # ── Consumer ──────────────────────────────────────────────────────
    "consumer_staples_aristocrat": {
        "wacc": 0.07, "terminal_growth": 0.025,  # mature, stable, lower WACC
        "fwd_pe_fair": 24.0, "fwd_pe_ny2": 23.0,  # aristocrat premium
        "ev_ebitda_fair": 17.0, "ev_ebitda_fwd": 16.0,
        "fcf_yield_target": 0.04, "div_yield_target": 0.03,
        "coe": 0.075, "long_growth": 0.05,
    },
    "consumer_cyclical": {
        "wacc": 0.09, "terminal_growth": 0.025,
        "fwd_pe_fair": 16.0, "fwd_pe_ny2": 15.0,
        "ev_ebitda_fair": 11.0, "ev_ebitda_fwd": 10.5,
        "fcf_yield_target": 0.055,
    },

    # ── Auto ──────────────────────────────────────────────────────────
    "auto_oem_traditional": {
        "wacc": 0.09, "terminal_growth": 0.02,
        "fwd_pe_fair": 9.0, "fwd_pe_ny2": 8.5,
        "ev_ebitda_fair": 6.0, "ev_ebitda_fwd": 5.5,
        "fcf_yield_target": 0.08,
        "pb_fair": 1.0,
    },
    "auto_oem_plus_optionality": {
        # TSLA — core OEM 40%, AI/robotaxi optionality 60%
        "wacc": 0.11, "terminal_growth": 0.03,
        "fwd_pe_fair": 30.0, "fwd_pe_ny2": 28.0,  # optionality premium
        "ev_ebitda_fair": 18.0, "ev_ebitda_fwd": 16.0,
        "fcf_yield_target": 0.025,
    },

    # ── Industrials / Materials ───────────────────────────────────────
    "industrial_cyclical": {
        "wacc": 0.09, "terminal_growth": 0.025,
        "fwd_pe_fair": 17.0, "fwd_pe_ny2": 16.0,
        "ev_ebitda_fair": 12.0, "ev_ebitda_fwd": 11.0,
        "fcf_yield_target": 0.055, "div_yield_target": 0.025,
    },
    "mining_commodity": {
        "wacc": 0.10, "terminal_growth": 0.02,
        "fwd_pe_fair": 12.0, "fwd_pe_ny2": 11.5,
        "ev_ebitda_fair": 7.0, "ev_ebitda_fwd": 6.5,
        "pb_fair": 1.5,
    },
    "chemicals_commodity": {
        "wacc": 0.09, "terminal_growth": 0.02,
        "fwd_pe_fair": 13.0, "fwd_pe_ny2": 12.5,
        "ev_ebitda_fair": 8.0, "ev_ebitda_fwd": 7.5,
        "fcf_yield_target": 0.06, "div_yield_target": 0.035,
    },

    # ── Telecom / Media / Gaming ──────────────────────────────────────
    "telecom": {
        "wacc": 0.075, "terminal_growth": 0.02,
        "fwd_pe_fair": 11.0, "fwd_pe_ny2": 10.5,
        "ev_ebitda_fair": 8.0, "ev_ebitda_fwd": 7.5,
        "fcf_yield_target": 0.07, "div_yield_target": 0.06,
        "pb_fair": 1.5,
    },
    "media_traditional": {
        "wacc": 0.09, "terminal_growth": 0.02,
        "fwd_pe_fair": 13.0, "fwd_pe_ny2": 12.0,
        "ev_ebitda_fair": 9.0, "ev_ebitda_fwd": 8.5,
        "fcf_yield_target": 0.07,
    },
    "gaming_interactive": {
        "wacc": 0.09, "terminal_growth": 0.03,
        "fwd_pe_fair": 25.0, "fwd_pe_ny2": 22.0,
        "ev_ebitda_fair": 16.0, "ev_ebitda_fwd": 14.0,
        "fcf_yield_target": 0.04,
    },

    # ── Distressed / Decliner ─────────────────────────────────────────
    "turnaround_distressed": {
        "wacc": 0.14, "terminal_growth": 0.015,
        "ev_ebitda_fair": 6.0, "ev_ebitda_fwd": 6.5,
        "pb_fair": 0.7, "p_tbv_fair": 0.6,
    },
    "structural_decliner": {
        "wacc": 0.08, "terminal_growth": 0.00,  # no terminal growth
        "fwd_pe_fair": 8.0, "fwd_pe_ny2": 7.5,
        "fcf_yield_target": 0.10, "div_yield_target": 0.07,
        "pb_fair": 0.9,
    },

    # ── Generic fallback ──────────────────────────────────────────────
    "generic_equity": {
        "wacc": 0.09, "terminal_growth": 0.025,
        "fwd_pe_fair": 18.0, "fwd_pe_ny2": 17.0,
        "ev_ebitda_fair": 12.0, "ev_ebitda_fwd": 11.0,
        "fcf_yield_target": 0.05, "div_yield_target": 0.025,
        "pb_fair": 1.5,
    },
}


def get_tuning(archetype_key: str) -> dict:
    """Archetype için tuning params. Fallback: generic_equity."""
    return TUNING.get(archetype_key, TUNING["generic_equity"])


def get_param(archetype_key: str, param: str, default=None):
    """Tek bir parametre al. None dönerse default."""
    t = get_tuning(archetype_key)
    v = t.get(param)
    return v if v is not None else default
