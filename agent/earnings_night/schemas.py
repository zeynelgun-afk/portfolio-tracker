"""
Earnings Night Pipeline — Pydantic Schemas

Kimi K2 Thinking'ten gelen JSON'ı validate eder.
Pydantic v2 syntax.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Optional


class Meta(BaseModel):
    ticker: str
    fiscal_period_reported: str
    filing_date: str
    parser_version: str = "v1.0"
    currency: str = "USD"


class ResultsActual(BaseModel):
    revenue_usd_b: Optional[float] = Field(None, ge=0)
    yoy_revenue_growth_pct: Optional[float] = None
    qoq_revenue_growth_pct: Optional[float] = None
    gaap_eps: Optional[float] = None
    non_gaap_eps: Optional[float] = None
    gaap_net_income_m: Optional[float] = None
    non_gaap_net_income_m: Optional[float] = None
    gross_margin_pct: Optional[float] = Field(None, ge=0, le=100)
    operating_margin_pct: Optional[float] = Field(None, ge=-50, le=100)
    operating_income_m: Optional[float] = None
    free_cash_flow_m: Optional[float] = None
    diluted_share_count_m: Optional[float] = Field(None, ge=0)


class GuidanceQuarter(BaseModel):
    provided: bool = False
    fiscal_period: Optional[str] = None
    revenue_low_b: Optional[float] = Field(None, ge=0)
    revenue_mid_b: Optional[float] = Field(None, ge=0)
    revenue_high_b: Optional[float] = Field(None, ge=0)
    non_gaap_eps_low: Optional[float] = None
    non_gaap_eps_mid: Optional[float] = None
    non_gaap_eps_high: Optional[float] = None
    gaap_eps_low: Optional[float] = None
    gaap_eps_mid: Optional[float] = None
    gaap_eps_high: Optional[float] = None
    gross_margin_low_pct: Optional[float] = Field(None, ge=0, le=100)
    gross_margin_mid_pct: Optional[float] = Field(None, ge=0, le=100)
    gross_margin_high_pct: Optional[float] = Field(None, ge=0, le=100)
    operating_margin_mid_pct: Optional[float] = Field(None, ge=-50, le=100)

    @model_validator(mode="after")
    def check_range_consistency(self):
        # Revenue range tutarlılık kontrolü
        if self.revenue_low_b is not None and self.revenue_high_b is not None:
            if self.revenue_low_b > self.revenue_high_b:
                raise ValueError(
                    f"revenue_low_b ({self.revenue_low_b}) > revenue_high_b ({self.revenue_high_b})"
                )
        # EPS range
        if self.non_gaap_eps_low is not None and self.non_gaap_eps_high is not None:
            if self.non_gaap_eps_low > self.non_gaap_eps_high:
                raise ValueError("non_gaap_eps_low > non_gaap_eps_high")
        # Gross margin range
        if (
            self.gross_margin_low_pct is not None
            and self.gross_margin_high_pct is not None
        ):
            if self.gross_margin_low_pct > self.gross_margin_high_pct:
                raise ValueError("gross_margin_low_pct > gross_margin_high_pct")
        # provided=False ise tüm sayısal alanlar null olmalı
        if not self.provided:
            numeric_fields = [
                self.revenue_low_b, self.revenue_mid_b, self.revenue_high_b,
                self.non_gaap_eps_low, self.non_gaap_eps_mid, self.non_gaap_eps_high,
                self.gaap_eps_low, self.gaap_eps_mid, self.gaap_eps_high,
                self.gross_margin_low_pct, self.gross_margin_mid_pct,
                self.gross_margin_high_pct, self.operating_margin_mid_pct,
            ]
            if any(v is not None for v in numeric_fields):
                raise ValueError("provided=False ama bazı sayılar populated")
        return self


class GuidanceFullYear(BaseModel):
    provided: bool = False
    fiscal_period: Optional[str] = None
    revenue_low_b: Optional[float] = Field(None, ge=0)
    revenue_mid_b: Optional[float] = Field(None, ge=0)
    revenue_high_b: Optional[float] = Field(None, ge=0)
    non_gaap_eps_low: Optional[float] = None
    non_gaap_eps_mid: Optional[float] = None
    non_gaap_eps_high: Optional[float] = None
    gross_margin_mid_pct: Optional[float] = Field(None, ge=0, le=100)
    capex_guidance_b: Optional[float] = None
    opex_growth_guidance_pct: Optional[float] = None


class Segment(BaseModel):
    segment_name: str
    revenue_usd_b: Optional[float] = Field(None, ge=0)
    yoy_growth_pct: Optional[float] = None
    operating_margin_pct: Optional[float] = Field(None, ge=-50, le=100)


class OneTimeItem(BaseModel):
    description: str
    amount_usd_m: Optional[float] = None
    pretax_or_aftertax: str = Field(..., pattern="^(pretax|aftertax)$")
    segment_affected: Optional[str] = None


class CapitalReturn(BaseModel):
    buyback_authorization_b: Optional[float] = Field(None, ge=0)
    buyback_executed_in_period_b: Optional[float] = Field(None, ge=0)
    dividend_per_share: Optional[float] = Field(None, ge=0)
    dividend_change_pct: Optional[float] = None


class QualitativeSignals(BaseModel):
    tone_score: int = Field(0, ge=-5, le=5)
    tone_label: str = "neutral"
    evidence_phrases: list[str] = []
    warning_phrases: list[str] = []
    guidance_color: Optional[str] = None
    approximations: list[str] = []
    ceo_quote_primary: Optional[str] = None
    cfo_quote_primary: Optional[str] = None

    @model_validator(mode="after")
    def evidence_required_for_nonzero_score(self):
        # Non-zero tone score'da en az 2 evidence phrase olmalı
        if abs(self.tone_score) >= 1 and len(self.evidence_phrases) < 2:
            raise ValueError(
                f"tone_score={self.tone_score} ama sadece {len(self.evidence_phrases)} evidence phrase var (min 2)"
            )
        return self


class ConfidenceGrades(BaseModel):
    results_actual: str = Field("high", pattern="^(high|medium|low)$")
    guidance_next_quarter: str = Field("high", pattern="^(high|medium|low)$")
    guidance_full_year: str = Field("high", pattern="^(high|medium|low)$")
    segment_breakdown: str = Field("high", pattern="^(high|medium|low)$")
    overall: str = Field("high", pattern="^(high|medium|low)$")


class AmbiguousItem(BaseModel):
    field: str
    explanation: str


class SelfCheck(BaseModel):
    no_quarterly_annual_mixup: bool = True
    all_numbers_have_source_quote: bool = True
    units_consistent: bool = True
    no_investment_language: bool = True
    json_valid: bool = True


class EarningsParse(BaseModel):
    """8-K Exhibit 99.1 parse sonucu - tam JSON şeması."""
    meta: Meta
    results_actual: ResultsActual
    guidance_next_quarter: GuidanceQuarter
    guidance_full_year: GuidanceFullYear
    segment_breakdown: list[Segment] = []
    one_time_items: list[OneTimeItem] = []
    capital_return: CapitalReturn = CapitalReturn()
    qualitative_signals: QualitativeSignals
    source_quotes: dict[str, str] = {}
    confidence: ConfidenceGrades
    ambiguous_items: list[AmbiguousItem] = []
    self_check: SelfCheck = SelfCheck()

    def implied_forward_eps(self) -> Optional[float]:
        """
        Sonraki çeyrek guidance'ından implied forward 12-month EPS.
        Sadece çeyrek guidance varsa annualize eder (sıkı non-fabrication
        kuralından farklı, post-processing).
        """
        if not self.guidance_next_quarter.provided:
            return None
        eps_mid = self.guidance_next_quarter.non_gaap_eps_mid
        if eps_mid is not None:
            return eps_mid * 4
        return None

    def implied_forward_revenue(self) -> Optional[float]:
        """Sonraki çeyrek revenue'dan annualize forward revenue."""
        if not self.guidance_next_quarter.provided:
            return None
        rev_mid = self.guidance_next_quarter.revenue_mid_b
        if rev_mid is not None:
            return rev_mid * 4
        return None


class TranscriptDelta(BaseModel):
    """Earnings call transcript delta parse sonucu (Prompt 2 çıktısı)."""
    meta: dict
    tone_delta: dict
    guidance_color: dict
    qa_concerns: list[dict]
    cfo_commentary: dict
    ceo_strategic_forward: dict
    sandbagging_signals: list[str] = []
    concern_phrases: list[str] = []
    guidance_refinement: dict
    confidence: str = "high"
