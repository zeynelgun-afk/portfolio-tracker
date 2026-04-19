"""
Finzora Valuation Framework v5 — Archetype Taxonomy
=====================================================
32 şirket arketipi. Her arketip için:
  - detect: FMP verisine bakıp bu arketipe uyuyor mu (bool, confidence)
  - methods: hangi valuation metodları aktif (primary/secondary/sanity)
  - excluded: hangi metodlar YASAKLI (hard exclusion)

Detection precedence: REIT/bank/insurer önce (sektör bazlı)
sonra growth/margin bazlı disambiguation.

Araştırma belgesi: VALUATION_FRAMEWORK_v5.md (artifact)
"""

from dataclasses import dataclass, field


@dataclass
class MethodWeight:
    name: str
    weight: float
    tier: str  # primary / secondary / sanity


@dataclass
class Archetype:
    key: str
    label: str
    description: str
    primary: list  # [(method_name, weight), ...] — weights sum ~0.60-0.70
    secondary: list  # sum ~0.20-0.30
    sanity: list  # sum ~0.05-0.15
    excluded: dict  # {method_name: reason}
    detect_priority: int  # 1=highest (sector-based), 5=lowest (fallback)

    def all_methods(self) -> list:
        """[(name, weight, tier), ...] toplam ağırlık ~1.0."""
        r = []
        for n, w in self.primary:
            r.append((n, w, "primary"))
        for n, w in self.secondary:
            r.append((n, w, "secondary"))
        for n, w in self.sanity:
            r.append((n, w, "sanity"))
        return r


# ─────────────────────────────────────────────────────────────────────────────
# 32 ARKETIP
# ─────────────────────────────────────────────────────────────────────────────

ARCHETYPES = {

    # ── TECH / SOFTWARE ────────────────────────────────────────────────
    "hyper_growth_software": Archetype(
        key="hyper_growth_software",
        label="Hiper-büyüme SaaS/Software",
        description="Rev growth >40%, FCF margin <5%, R&D/rev >15%",
        primary=[
            ("ev_rev_growth_adjusted", 0.25),
            ("rule_of_40_multiple", 0.20),
            ("dcf_multi_stage_aggressive", 0.20),
        ],
        secondary=[
            ("forward_pe_ny3", 0.15),
            ("ma_comp_multiples", 0.10),
        ],
        sanity=[
            ("reverse_dcf", 0.10),
        ],
        excluded={
            "trailing_pe": "negative/near-zero EPS",
            "ev_ebitda": "negative/near-zero EBITDA",
            "dividend_discount": "no dividend",
            "price_to_book": "asset-light, book irrelevant",
            "fcf_yield": "negative FCF",
        },
        detect_priority=3,
    ),

    "profitable_growth_software": Archetype(
        key="profitable_growth_software",
        label="Karlı büyüme yazılım",
        description="Rev growth 20-40%, FCF margin >15%, op margin >20%",
        primary=[
            ("forward_pe_ny2", 0.25),
            ("dcf_multi_stage", 0.20),
            ("ev_ebitda_forward", 0.20),
        ],
        secondary=[
            ("fcf_yield", 0.15),
            ("pegy", 0.10),
        ],
        sanity=[
            ("ev_rev_growth_adjusted", 0.10),
        ],
        excluded={
            "price_to_book": "asset-light",
            "dividend_discount": "minimal dividend",
            "reserves_nav": "not applicable",
        },
        detect_priority=3,
    ),

    "mature_megacap_tech": Archetype(
        key="mature_megacap_tech",
        label="Olgun mega-cap tech",
        description="Market cap >$500B, rev growth 5-20%, op margin >25%",
        primary=[
            ("dcf_2stage", 0.25),
            ("forward_pe_ny1", 0.20),
            ("fcf_yield", 0.20),
        ],
        secondary=[
            ("ev_ebitda", 0.15),
            ("pegy", 0.10),
        ],
        sanity=[
            ("sum_of_parts", 0.10),
        ],
        excluded={
            "price_to_book": "asset-light",
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=3,
    ),

    # ── SEMIS ──────────────────────────────────────────────────────────
    "hyper_growth_semi": Archetype(
        key="hyper_growth_semi",
        label="Hiper-büyüme yarı iletken (AI)",
        description="Rev growth >60% (ALAB, AVGO peak), fabless, high SBC",
        primary=[
            ("forward_pe_ny2", 0.25),
            ("ev_ebitda_forward", 0.20),
            ("dcf_multi_stage_aggressive", 0.20),
        ],
        secondary=[
            ("peg_forward", 0.15),
            ("ev_rev_growth_adjusted", 0.10),
        ],
        sanity=[
            ("normalized_pe_midcycle", 0.10),
        ],
        excluded={
            "trailing_pe": "cycle-distorted, early ramp",
            "dividend_discount": "no dividend",
            "price_to_book": "asset-light fabless",
            "reserves_nav": "not applicable",
        },
        detect_priority=3,
    ),

    "mature_semi": Archetype(
        key="mature_semi",
        label="Olgun yarı iletken",
        description="INTC/TXN benzeri, cycle normalize edilmiş",
        primary=[
            ("normalized_pe_midcycle", 0.25),
            ("dcf_2stage", 0.20),
            ("ev_ebitda_midcycle", 0.20),
        ],
        secondary=[
            ("fcf_yield", 0.15),
            ("dividend_discount", 0.10),
        ],
        sanity=[
            ("price_to_book_capital_intensive", 0.10),
        ],
        excluded={
            "rnpv": "not pharma",
            "reserves_nav": "not applicable",
        },
        detect_priority=3,
    ),

    # ── FINANCIALS ─────────────────────────────────────────────────────
    "money_center_bank": Archetype(
        key="money_center_bank",
        label="Mega bankacılık (JPM, BAC, C, WFC)",
        description="Total assets >$500B, NII/rev >40%",
        primary=[
            ("justified_pb", 0.25),
            ("residual_income", 0.25),
            ("forward_pe_normalized", 0.15),
        ],
        secondary=[
            ("dividend_discount", 0.15),
            ("price_to_tangible_book", 0.10),
        ],
        sanity=[
            ("trailing_pe", 0.10),
        ],
        excluded={
            "dcf_multi_stage": "FCFF undefined for banks (debt is raw material)",
            "dcf_2stage": "FCFF undefined for banks",
            "ev_ebitda": "economically undefined for banks",
            "ev_revenue": "NII aggregation meaningless",
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=1,
    ),

    "regional_bank": Archetype(
        key="regional_bank",
        label="Bölgesel bankalar (USB, PNC, TFC)",
        description="Total assets $50B-$500B",
        primary=[
            ("justified_pb", 0.25),
            ("residual_income", 0.20),
            ("dividend_discount", 0.20),
        ],
        secondary=[
            ("forward_pe_normalized", 0.15),
            ("price_to_tangible_book", 0.10),
        ],
        sanity=[
            ("trailing_pe", 0.10),
        ],
        excluded={
            "dcf_multi_stage": "FCFF undefined for banks",
            "dcf_2stage": "FCFF undefined",
            "ev_ebitda": "undefined",
            "ev_revenue": "meaningless",
            "reserves_nav": "not applicable",
        },
        detect_priority=1,
    ),

    "insurer_life": Archetype(
        key="insurer_life",
        label="Hayat sigortası (MET, PRU)",
        description="Embedded value odaklı",
        primary=[
            ("embedded_value", 0.30),
            ("justified_pb", 0.20),
            ("residual_income", 0.15),
        ],
        secondary=[
            ("dividend_discount", 0.15),
            ("forward_pe_normalized", 0.10),
        ],
        sanity=[
            ("price_to_tangible_book", 0.10),
        ],
        excluded={
            "dcf_multi_stage": "FCFF undefined",
            "dcf_2stage": "FCFF undefined",
            "ev_ebitda": "undefined",
            "ev_revenue": "premium revenue ≠ value",
        },
        detect_priority=1,
    ),

    "insurer_pc": Archetype(
        key="insurer_pc",
        label="P&C sigorta (TRV, ALL, CB)",
        description="Combined ratio + investment yield",
        primary=[
            ("justified_pb", 0.25),
            ("residual_income", 0.25),
            ("dividend_discount", 0.15),
        ],
        secondary=[
            ("forward_pe_normalized", 0.15),
            ("price_to_tangible_book", 0.10),
        ],
        sanity=[
            ("trailing_pe", 0.10),
        ],
        excluded={
            "dcf_multi_stage": "FCFF undefined",
            "dcf_2stage": "FCFF undefined",
            "ev_ebitda": "undefined",
            "ev_revenue": "meaningless",
        },
        detect_priority=1,
    ),

    "asset_manager": Archetype(
        key="asset_manager",
        label="Asset manager (BLK, BX, KKR)",
        description="AUM leverage, management fees",
        primary=[
            ("forward_pe_ny1", 0.25),
            ("fcf_yield", 0.20),
            ("dividend_discount", 0.20),
        ],
        secondary=[
            ("ev_ebitda", 0.15),
            ("dcf_2stage", 0.10),
        ],
        sanity=[
            ("price_to_aum", 0.10),
        ],
        excluded={
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=2,
    ),

    # ── REITs ──────────────────────────────────────────────────────────
    "reit_equity": Archetype(
        key="reit_equity",
        label="Equity REIT (O, VICI, PLD)",
        description="Sahip oldukları mülkler, FFO/AFFO",
        primary=[
            ("p_ffo", 0.20),
            ("p_affo", 0.20),
            ("nav_cap_rate", 0.20),
        ],
        secondary=[
            ("dividend_discount_affo", 0.15),
            ("ev_ebitda_reit", 0.10),
        ],
        sanity=[
            ("p_ffo_vs_history", 0.10),
            ("implied_cap_rate", 0.05),
        ],
        excluded={
            "trailing_pe": "GAAP depreciation distorts net income 40-60%",
            "forward_pe_ny1": "depreciation distortion",
            "forward_pe_ny2": "depreciation distortion",
            "forward_pe_normalized": "depreciation distortion",
            "dcf_multi_stage": "FFO/AFFO framework preferred",
            "dcf_2stage": "FFO/AFFO preferred",
            "ev_revenue": "not applicable",
            "reserves_nav": "not oil/gas",
        },
        detect_priority=1,
    ),

    "reit_mortgage": Archetype(
        key="reit_mortgage",
        label="Mortgage REIT (AGNC, NLY)",
        description="MBS portföyü, spread kazancı",
        primary=[
            ("price_to_book", 0.30),
            ("dividend_discount", 0.25),
            ("book_value_mark_to_market", 0.20),
        ],
        secondary=[
            ("spread_leverage_duration", 0.15),
            ("p_distributable_earnings", 0.10),
        ],
        sanity=[],
        excluded={
            "p_ffo": "not meaningful (no property depreciation)",
            "p_affo": "not meaningful",
            "nav_cap_rate": "not real estate holdings",
            "ev_ebitda": "not applicable",
            "trailing_pe": "volatile",
        },
        detect_priority=1,
    ),

    "reit_net_lease": Archetype(
        key="reit_net_lease",
        label="Net-lease REIT (O, NNN, WPC)",
        description="Uzun vadeli kira + triple-net",
        primary=[
            ("p_affo", 0.30),
            ("p_ffo", 0.20),
            ("dividend_discount_affo", 0.20),
        ],
        secondary=[
            ("nav_cap_rate", 0.15),
            ("ev_ebitda_reit", 0.10),
        ],
        sanity=[
            ("p_affo_vs_history", 0.05),
        ],
        excluded={
            "trailing_pe": "GAAP depreciation distorts",
            "forward_pe_ny1": "depreciation",
            "forward_pe_ny2": "depreciation",
            "dcf_multi_stage": "FFO/AFFO preferred",
            "ev_revenue": "not applicable",
        },
        detect_priority=1,
    ),

    # ── UTILITIES ──────────────────────────────────────────────────────
    "utility_regulated": Archetype(
        key="utility_regulated",
        label="Regüle edilmiş utility (DUK, SO, NEE)",
        description="Rate-base × allowed ROE",
        primary=[
            ("dividend_discount_multistage", 0.25),
            ("rate_base_allowed_roe", 0.20),
            ("dcf_fcfe", 0.15),
        ],
        secondary=[
            ("forward_pe_ny1", 0.15),
            ("price_to_book_vs_roe", 0.15),
        ],
        sanity=[
            ("ev_ebitda", 0.10),
        ],
        excluded={
            "ev_revenue": "revenue = regulated, not value driver",
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=2,
    ),

    # ── ENERGY ─────────────────────────────────────────────────────────
    "energy_upstream_ep": Archetype(
        key="energy_upstream_ep",
        label="Upstream E&P (COP, EOG, PXD)",
        description="Reserves, upstream only",
        primary=[
            ("reserves_nav_pv10", 0.30),
            ("ev_ebitdax", 0.20),
            ("ev_production", 0.15),
        ],
        secondary=[
            ("dcf_strip_priced", 0.15),
            ("forward_pe_midcycle", 0.10),
        ],
        sanity=[
            ("price_to_nav", 0.10),
        ],
        excluded={
            "trailing_pe": "cyclical, undefined at trough",
            "dividend_discount": "variable dividend policy",
            "price_to_book": "asset value ≠ reserves PV",
            "ev_revenue": "commodity revenue ≠ value",
        },
        detect_priority=2,
    ),

    "energy_integrated": Archetype(
        key="energy_integrated",
        label="Entegre enerji (XOM, CVX, BP, SHEL)",
        description="Upstream + downstream + chemicals",
        primary=[
            ("normalized_pe_midcycle", 0.25),
            ("ev_ebitda_midcycle", 0.25),
            ("dividend_discount", 0.15),
        ],
        secondary=[
            ("fcf_yield_midcycle", 0.15),
            ("price_to_book_capital_intensive", 0.10),
        ],
        sanity=[
            ("reserves_nav_pv10", 0.05),
            ("sum_of_parts", 0.05),
        ],
        excluded={
            "trailing_pe": "peak×peak error at cycle top",
            "ev_revenue": "commodity revenue ≠ value",
            "rnpv": "not pharma",
        },
        detect_priority=2,
    ),

    "energy_midstream": Archetype(
        key="energy_midstream",
        label="Midstream (EPD, ET, KMI)",
        description="Pipeline, storage, fee-based",
        primary=[
            ("dividend_discount", 0.25),
            ("ev_ebitda", 0.25),
            ("p_distributable_cash_flow", 0.15),
        ],
        secondary=[
            ("fcf_yield", 0.15),
            ("forward_pe_ny1", 0.10),
        ],
        sanity=[
            ("price_to_book_capital_intensive", 0.10),
        ],
        excluded={
            "reserves_nav": "not E&P",
            "ev_revenue": "tariff revenue ≠ value",
            "rnpv": "not pharma",
        },
        detect_priority=2,
    ),

    # ── PHARMA / BIOTECH ───────────────────────────────────────────────
    "biotech_preclinical": Archetype(
        key="biotech_preclinical",
        label="Pre-kar biotech (MRNA post-COVID, BEAM)",
        description="Revenue <$100M veya rev/mcap <5%, 12+ ay cash",
        primary=[
            ("rnpv_pipeline", 0.40),
            ("cash_adjusted_cap_vs_rnpv", 0.20),
            ("real_options_pipeline", 0.15),
        ],
        secondary=[
            ("ma_comp_per_indication", 0.15),
            ("ev_per_pipeline_asset", 0.10),
        ],
        sanity=[],
        excluded={
            "trailing_pe": "negative or tiny earnings",
            "forward_pe_ny1": "pre-profitability",
            "forward_pe_ny2": "pre-profitability",
            "ev_ebitda": "negative EBITDA",
            "ev_revenue": "lumpy/unrelated to pipeline value",
            "dcf_multi_stage": "pipeline binary outcomes not continuous",
            "dcf_2stage": "pipeline binary",
            "fcf_yield": "negative",
            "dividend_discount": "no dividend",
            "price_to_book": "R&D not capitalized",
            "reserves_nav": "not oil/gas",
            "p_ffo": "not REIT",
            "p_affo": "not REIT",
        },
        detect_priority=2,
    ),

    "biotech_commercial": Archetype(
        key="biotech_commercial",
        label="Ticari biotech (REGN, VRTX, BMRN)",
        description="Approved drug revenue + pipeline",
        primary=[
            ("rnpv_pipeline_plus_mature", 0.30),
            ("forward_pe_ny2", 0.20),
            ("dcf_multi_stage_patent_cliff", 0.20),
        ],
        secondary=[
            ("ev_ebitda", 0.15),
            ("ma_comp_per_indication", 0.10),
        ],
        sanity=[
            ("sum_of_parts", 0.05),
        ],
        excluded={
            "reserves_nav": "not oil/gas",
            "p_ffo": "not REIT",
            "price_to_book": "R&D distorted",
        },
        detect_priority=2,
    ),

    "pharma_big": Archetype(
        key="pharma_big",
        label="Büyük pharma (JNJ, PFE, MRK, LLY)",
        description="Çeşitlendirilmiş portföy + pipeline",
        primary=[
            ("forward_pe_ny2", 0.25),
            ("dcf_multi_stage_patent_cliff", 0.20),
            ("sum_of_parts", 0.15),
        ],
        secondary=[
            ("dividend_discount", 0.15),
            ("ev_ebitda", 0.15),
        ],
        sanity=[
            ("peg_forward", 0.10),
        ],
        excluded={
            "reserves_nav": "not oil/gas",
            "p_ffo": "not REIT",
            "ev_revenue": "diversified, not growth multiple",
        },
        detect_priority=2,
    ),

    # ── CONSUMER ───────────────────────────────────────────────────────
    "consumer_staples_aristocrat": Archetype(
        key="consumer_staples_aristocrat",
        label="Tüketici temel aristokrat (KO, PEP, PG, KMB)",
        description="Olgun, istikrarlı, dividend aristocrat",
        primary=[
            ("forward_pe_ny1", 0.25),
            ("dividend_discount_gordon", 0.20),
            ("dcf_2stage", 0.20),
        ],
        secondary=[
            ("ev_ebitda", 0.15),
            ("pe_vs_history_10y", 0.15),
        ],
        sanity=[
            ("fcf_yield", 0.05),
        ],
        excluded={
            "ev_rev_growth_adjusted": "slow growth",
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=3,
    ),

    "consumer_cyclical": Archetype(
        key="consumer_cyclical",
        label="Tüketici döngüsel (TGT, HD, NKE)",
        description="Ekonomik döngüye bağlı",
        primary=[
            ("normalized_pe_cyclical", 0.25),
            ("forward_pe_ny2", 0.20),
            ("dcf_2stage", 0.20),
        ],
        secondary=[
            ("ev_ebitda_midcycle", 0.15),
            ("fcf_yield", 0.10),
        ],
        sanity=[
            ("peer_relative", 0.10),
        ],
        excluded={
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=3,
    ),

    # ── AUTO ───────────────────────────────────────────────────────────
    "auto_oem_traditional": Archetype(
        key="auto_oem_traditional",
        label="Geleneksel otomotiv (F, GM, Toyota)",
        description="Auto OEM, düşük optionality",
        primary=[
            ("normalized_pe_cyclical", 0.25),
            ("ev_ebitda_midcycle", 0.20),
            ("price_to_book_capital_intensive", 0.20),
        ],
        secondary=[
            ("dividend_discount", 0.15),
            ("fcf_yield_midcycle", 0.10),
        ],
        sanity=[
            ("peer_relative", 0.10),
        ],
        excluded={
            "rnpv": "not pharma",
            "reserves_nav": "not applicable",
        },
        detect_priority=3,
    ),

    "auto_oem_plus_optionality": Archetype(
        key="auto_oem_plus_optionality",
        label="Otomotiv + AI/robotaxi optionality (TSLA)",
        description="P/S >3× peer veya R&D >3× peer",
        primary=[
            ("sum_of_parts_scenario", 0.30),
            ("scenario_dcf_weighted", 0.25),
            ("forward_pe_core_auto", 0.15),
        ],
        secondary=[
            ("ev_revenue", 0.15),
            ("reverse_dcf", 0.10),
        ],
        sanity=[
            ("peer_auto_multiples", 0.05),
        ],
        excluded={
            "trailing_pe": "narrative premium distorts",
            "dividend_discount": "no dividend",
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=3,
    ),

    # ── INDUSTRIALS / MATERIALS ────────────────────────────────────────
    "industrial_cyclical": Archetype(
        key="industrial_cyclical",
        label="Endüstriyel döngüsel (CAT, DE, HON)",
        description="Ekonomik döngüye bağlı sanayi",
        primary=[
            ("normalized_pe_cyclical", 0.25),
            ("forward_pe_ny2", 0.20),
            ("ev_ebitda_midcycle", 0.20),
        ],
        secondary=[
            ("dividend_discount", 0.15),
            ("fcf_yield_midcycle", 0.10),
        ],
        sanity=[
            ("peer_relative", 0.10),
        ],
        excluded={
            "reserves_nav": "not E&P",
            "rnpv": "not pharma",
            "ev_rev_growth_adjusted": "mature business",
        },
        detect_priority=3,
    ),

    "mining_commodity": Archetype(
        key="mining_commodity",
        label="Madencilik / emtia (FCX, NEM, GOLD)",
        description="Emtia fiyatına duyarlı",
        primary=[
            ("reserves_nav_mining", 0.30),
            ("ev_ebitda_midcycle", 0.20),
            ("price_to_book_capital_intensive", 0.15),
        ],
        secondary=[
            ("fcf_yield_midcycle", 0.15),
            ("normalized_pe_cyclical", 0.10),
        ],
        sanity=[
            ("ev_per_ounce_reserves", 0.10),
        ],
        excluded={
            "trailing_pe": "peak×peak / trough×trough error",
            "dividend_discount": "variable",
            "ev_revenue": "commodity revenue ≠ value",
            "rnpv": "not pharma",
        },
        detect_priority=2,
    ),

    "chemicals_commodity": Archetype(
        key="chemicals_commodity",
        label="Emtia kimyasalları (DOW, LYB)",
        description="Emtia döngüsü, kapasite yoğun",
        primary=[
            ("normalized_pe_cyclical", 0.25),
            ("ev_ebitda_midcycle", 0.25),
            ("price_to_book_capital_intensive", 0.15),
        ],
        secondary=[
            ("dividend_discount", 0.15),
            ("fcf_yield_midcycle", 0.10),
        ],
        sanity=[
            ("peer_relative", 0.10),
        ],
        excluded={
            "rnpv": "not pharma",
            "reserves_nav": "not E&P",
            "ev_rev_growth_adjusted": "low growth commodity",
        },
        detect_priority=2,
    ),

    # ── TELECOM / MEDIA ────────────────────────────────────────────────
    "telecom": Archetype(
        key="telecom",
        label="Telekom (T, VZ, TMUS)",
        description="Capex yoğun, kablolu+kablosuz",
        primary=[
            ("dividend_discount", 0.25),
            ("forward_pe_ny1", 0.20),
            ("ev_ebitda", 0.20),
        ],
        secondary=[
            ("fcf_yield", 0.15),
            ("price_to_book_capital_intensive", 0.10),
        ],
        sanity=[
            ("sum_of_parts", 0.10),
        ],
        excluded={
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
            "ev_rev_growth_adjusted": "mature",
        },
        detect_priority=3,
    ),

    "media_traditional": Archetype(
        key="media_traditional",
        label="Geleneksel medya (DIS, PARA, WBD)",
        description="TV+studio+streaming karışımı",
        primary=[
            ("sum_of_parts", 0.30),
            ("ev_ebitda", 0.20),
            ("forward_pe_ny2", 0.15),
        ],
        secondary=[
            ("dcf_2stage", 0.15),
            ("dividend_discount", 0.10),
        ],
        sanity=[
            ("peer_relative", 0.10),
        ],
        excluded={
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=3,
    ),

    "gaming_interactive": Archetype(
        key="gaming_interactive",
        label="Interaktif oyun (EA, TTWO, RBLX)",
        description="Oyun franchise + DLC + live-service",
        primary=[
            ("forward_pe_ny2", 0.25),
            ("ev_ebitda_forward", 0.20),
            ("dcf_multi_stage", 0.20),
        ],
        secondary=[
            ("pegy", 0.15),
            ("ev_rev_growth_adjusted", 0.10),
        ],
        sanity=[
            ("fcf_yield", 0.10),
        ],
        excluded={
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
            "price_to_book": "asset-light",
        },
        detect_priority=3,
    ),

    # ── GOVERNMENT-COMMERCIAL SPLIT ───────────────────────────────────
    "software_dual_channel": Archetype(
        key="software_dual_channel",
        label="Dual-channel yazılım (PLTR)",
        description="Gov + commercial, yüksek SBC",
        primary=[
            ("dcf_multi_stage_aggressive", 0.30),
            ("ev_rev_growth_adjusted", 0.25),
            ("rule_of_40_multiple", 0.20),
        ],
        secondary=[
            ("forward_pe_ny3", 0.15),
            ("sum_of_parts_gov_commercial", 0.10),
        ],
        sanity=[],
        excluded={
            "trailing_pe": "rich multiple distorted",
            "forward_pe_ny1": "EV/Rev 50-80x means NY1 multiple meaningless",
            "forward_pe_ny2": "still too early in multiple expansion cycle",
            "dividend_discount": "no dividend",
            "price_to_book": "asset-light",
            "reserves_nav": "not applicable",
            "rnpv": "not pharma",
        },
        detect_priority=3,
    ),

    # ── TURNAROUND / DISTRESSED ───────────────────────────────────────
    "turnaround_distressed": Archetype(
        key="turnaround_distressed",
        label="Turnaround / distressed",
        description="2+ yıl negatif op margin, debt/equity >2",
        primary=[
            ("asset_based_nav", 0.25),
            ("sum_of_parts", 0.20),
            ("merton_option_pricing", 0.20),
        ],
        secondary=[
            ("normalized_ev_ebitda", 0.15),
            ("price_to_tangible_book", 0.10),
            ("ma_comp_multiples", 0.10),
        ],
        sanity=[],
        excluded={
            "dividend_discount": "cut or unreliable",
            "forward_pe_ny1": "unreliable forecasts",
            "forward_pe_ny2": "unreliable",
            "fcf_yield": "negative or volatile",
            "peg_forward": "earnings volatile",
        },
        detect_priority=2,
    ),

    "structural_decliner": Archetype(
        key="structural_decliner",
        label="Yapısal düşüş (T, IBM eski, kagıt medya)",
        description="Uzun vadeli gerileyen iş modeli",
        primary=[
            ("dividend_discount", 0.30),
            ("fcf_yield", 0.25),
            ("asset_based_nav", 0.15),
        ],
        secondary=[
            ("trailing_pe", 0.15),
            ("price_to_book", 0.10),
        ],
        sanity=[
            ("ev_ebitda", 0.05),
        ],
        excluded={
            "ev_rev_growth_adjusted": "declining",
            "peg_forward": "negative growth",
            "dcf_multi_stage": "terminal value collapses",
            "rnpv": "not pharma",
            "reserves_nav": "not applicable",
        },
        detect_priority=3,
    ),

    # ── FALLBACK ───────────────────────────────────────────────────────
    "generic_equity": Archetype(
        key="generic_equity",
        label="Genel (fallback)",
        description="Sınıflandırılamayan şirket",
        primary=[
            ("forward_pe_ny1", 0.25),
            ("dcf_2stage", 0.20),
            ("ev_ebitda", 0.20),
        ],
        secondary=[
            ("fcf_yield", 0.15),
            ("dividend_discount", 0.10),
        ],
        sanity=[
            ("trailing_pe", 0.05),
            ("price_to_book", 0.05),
        ],
        excluded={},
        detect_priority=5,
    ),
}


def get_archetype(key: str) -> Archetype:
    """Archetype'ı anahtardan al. Bulunmazsa generic_equity fallback."""
    return ARCHETYPES.get(key, ARCHETYPES["generic_equity"])


def list_archetypes() -> list:
    return list(ARCHETYPES.keys())
