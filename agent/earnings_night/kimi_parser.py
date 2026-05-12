"""
Earnings Night Pipeline — Kimi K2 Thinking Parser

OpenRouter üzerinden Kimi K2 Thinking modelini çağırır.
JSON parse + Pydantic validation + retry + Claude fallback.

Kullanım:
    parser = KimiEarningsParser()
    result = parser.parse_8k(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        filing_date="2026-02-25",
        fiscal_period="Q4 FY2026",
        document_text=press_release_text,
    )
    print(result.results_actual.revenue_usd_b)  # 68.127
    print(result.guidance_next_quarter.revenue_mid_b)  # 78.0
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests
from pydantic import ValidationError

from .schemas import EarningsParse, TranscriptDelta
from .prompts import (
    SYSTEM_PROMPT_8K,
    USER_PROMPT_TEMPLATE_8K,
    SYSTEM_PROMPT_TRANSCRIPT,
    USER_PROMPT_TEMPLATE_TRANSCRIPT,
)


@dataclass
class ParseResult:
    """Parser sonucu - başarılı veya başarısız, ayrıntılarla."""
    success: bool
    parsed: Optional[EarningsParse] = None
    raw_response: Optional[str] = None
    attempts: int = 0
    method_used: str = ""  # "kimi" veya "claude_fallback"
    error: Optional[str] = None
    cost_usd: float = 0.0
    duration_sec: float = 0.0


class EarningsParseFailure(Exception):
    """Tüm denemelerden sonra parse başarısız."""
    pass


class KimiEarningsParser:
    """
    Kimi K2 Thinking ile earnings parsing.

    Default model: moonshotai/kimi-k2-thinking
    Fallback: anthropic/claude-3-5-sonnet (OpenRouter üzerinden) veya direkt
              Anthropic API
    """

    # kimi-k2.5: non-thinking, 262K context, daha ucuz ve hızlı
    # kimi-k2-thinking: reasoning model, content null geliyor, parsing için elverişsiz
    KIMI_MODEL = "moonshotai/kimi-k2.5"
    FALLBACK_MODEL = "anthropic/claude-3.5-sonnet"

    # Maliyet (USD per million tokens, 12 May 2026 itibarıyla)
    KIMI_INPUT_COST_PER_M = 0.40
    KIMI_OUTPUT_COST_PER_M = 1.98
    CLAUDE_INPUT_COST_PER_M = 3.00
    CLAUDE_OUTPUT_COST_PER_M = 15.00

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_fallback: bool = True,
        max_retries: int = 3,
        timeout: int = 180,
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key gerekli. OPENROUTER_API_KEY env veya constructor parametresi."
            )
        self.use_fallback = use_fallback
        self.max_retries = max_retries
        self.timeout = timeout

    def parse_8k(
        self,
        ticker: str,
        company_name: str,
        filing_date: str,
        fiscal_period: str,
        document_text: str,
        previous_guidance: Optional[dict] = None,
    ) -> ParseResult:
        """8-K Exhibit 99.1 parse eder."""
        user_prompt = USER_PROMPT_TEMPLATE_8K.format(
            ticker=ticker,
            company_name=company_name,
            filing_date=filing_date,
            fiscal_period=fiscal_period,
            previous_guidance_json=json.dumps(previous_guidance) if previous_guidance else "null",
            document_text=document_text,
        )

        return self._parse_with_retry(
            system_prompt=SYSTEM_PROMPT_8K,
            user_prompt=user_prompt,
            schema_class=EarningsParse,
            ticker=ticker,
        )

    def parse_transcript_delta(
        self,
        ticker: str,
        existing_8k_parse: EarningsParse,
        transcript_text: str,
    ) -> ParseResult:
        """Earnings call transcript delta parse eder."""
        user_prompt = USER_PROMPT_TEMPLATE_TRANSCRIPT.format(
            existing_8k_json=existing_8k_parse.model_dump_json(),
            transcript_text=transcript_text,
        )

        return self._parse_with_retry(
            system_prompt=SYSTEM_PROMPT_TRANSCRIPT,
            user_prompt=user_prompt,
            schema_class=TranscriptDelta,
            ticker=ticker,
        )

    def _parse_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_class,
        ticker: str,
    ) -> ParseResult:
        """3 denemeli parse: Kimi (2 deneme) + Claude fallback (1 deneme)."""
        start_time = time.time()
        accumulated_cost = 0.0
        last_error = None
        last_response = None

        for attempt in range(self.max_retries):
            is_fallback = attempt == self.max_retries - 1 and self.use_fallback

            try:
                if is_fallback:
                    model = self.FALLBACK_MODEL
                    input_cost = self.CLAUDE_INPUT_COST_PER_M
                    output_cost = self.CLAUDE_OUTPUT_COST_PER_M
                    method = "claude_fallback"
                else:
                    model = self.KIMI_MODEL
                    input_cost = self.KIMI_INPUT_COST_PER_M
                    output_cost = self.KIMI_OUTPUT_COST_PER_M
                    method = "kimi"

                # Hata feedback'i 2. denemede ekle
                effective_user_prompt = user_prompt
                if attempt == 1 and last_error:
                    effective_user_prompt += (
                        f"\n\n## YOUR PREVIOUS RESPONSE FAILED VALIDATION:\n"
                        f"{last_error}\n\n"
                        f"Fix these errors and respond with valid JSON matching the schema."
                    )

                response_text, usage = self._call_openrouter(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=effective_user_prompt,
                )

                # Token maliyetini hesapla
                cost = (
                    usage.get("prompt_tokens", 0) / 1_000_000 * input_cost
                    + usage.get("completion_tokens", 0) / 1_000_000 * output_cost
                )
                accumulated_cost += cost
                last_response = response_text

                # JSON parse
                parsed_dict = json.loads(response_text)
                # Pydantic validation
                validated = schema_class(**parsed_dict)

                return ParseResult(
                    success=True,
                    parsed=validated,
                    raw_response=response_text,
                    attempts=attempt + 1,
                    method_used=method,
                    cost_usd=accumulated_cost,
                    duration_sec=time.time() - start_time,
                )

            except json.JSONDecodeError as e:
                last_error = f"JSON parse hatası: {e}"
                continue
            except ValidationError as e:
                last_error = f"Pydantic validation hatası: {e}"
                continue
            except requests.HTTPError as e:
                last_error = f"HTTP hatası: {e}"
                # 503/429 için exponential backoff: 5s, 15s, 45s
                if hasattr(e, 'response') and e.response is not None and e.response.status_code in (503, 429):
                    wait_time = 5 * (3 ** attempt)
                    time.sleep(wait_time)
                continue
            except Exception as e:
                last_error = f"Beklenmedik hata: {e}"
                continue

        # Tüm denemeler başarısız
        return ParseResult(
            success=False,
            raw_response=last_response,
            attempts=self.max_retries,
            method_used="failed",
            error=last_error,
            cost_usd=accumulated_cost,
            duration_sec=time.time() - start_time,
        )

    def _call_openrouter(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, dict]:
        """OpenRouter API'ye HTTP çağrısı. Returns (response_text, usage_dict)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://finzora.ai",
            "X-Title": "Finzora AI Earnings Night",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "top_p": 0.95,
            "max_tokens": 12000,
            "response_format": {"type": "json_object"},
        }

        response = requests.post(
            self.OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Kimi K2.5 hibrit reasoning yapar, content message.content içinde
        msg = data["choices"][0]["message"]
        content = msg.get("content")
        if not content:
            # Reasoning model durumunda content null olabilir
            reasoning = msg.get("reasoning", "")
            raise ValueError(
                f"Model content yerine reasoning döndürdü. "
                f"Finish reason: {data['choices'][0].get('finish_reason')}. "
                f"Reasoning ilk 200 char: {reasoning[:200]}"
            )
        usage = data.get("usage", {})

        return content, usage


def normalize_eps_from_one_time_items(
    parse_result: EarningsParse,
    effective_tax_rate: float = 0.21,
) -> Optional[float]:
    """
    GAAP EPS'ten one-time items'ı çıkararak normalize EPS hesaplar.

    Args:
        parse_result: 8-K parse sonucu
        effective_tax_rate: Pretax kalemleri after-tax'e çevirmek için (default 21%)

    Returns:
        Normalize EPS (USD per share) veya None (veri eksikse).
    """
    gaap_eps = parse_result.results_actual.gaap_eps
    shares_m = parse_result.results_actual.diluted_share_count_m

    if gaap_eps is None or shares_m is None or shares_m <= 0:
        return None

    if not parse_result.one_time_items:
        # One-time yoksa GAAP EPS zaten "normalize"
        return gaap_eps

    after_tax_adjustment_m = 0.0
    for item in parse_result.one_time_items:
        if item.amount_usd_m is None:
            continue
        if item.pretax_or_aftertax == "aftertax":
            after_tax_adjustment_m += item.amount_usd_m
        else:  # pretax
            after_tax_adjustment_m += item.amount_usd_m * (1 - effective_tax_rate)

    eps_impact = after_tax_adjustment_m / shares_m
    return round(gaap_eps - eps_impact, 4)


def compute_multiple_revision(
    parse_result: EarningsParse,
    pre_earnings_snapshot: dict,
    sector_momentum_factor: float = 0.0,
) -> dict:
    """
    Pre-earnings zımni çarpana revize uygulanır.

    Re-rating sebepleri (cumulative, max ±%30):
    1. Tone score: +5 → +%15, +3 → +%9, 0 → 0%, -3 → -%9, -5 → -%15
    2. Revenue growth surprise: actual YoY - pre-earnings tahmin
       Her +%5 büyüme sürprizi → çarpan +%3
    3. Sector momentum factor: caller'dan gelir (-0.10 ila +0.10)
       (örn. AI/semis hot → +0.10, kömür/enerji cold → -0.10)
    4. Methodology change warning: ambiguous_items'da methodology_change varsa
       → çarpan ek -%5 (belirsizlik artışı)

    Args:
        parse_result: Kimi parse sonucu
        pre_earnings_snapshot: Pre-earnings veriler
        sector_momentum_factor: -0.10 (cold) ila +0.10 (hot)

    Returns:
        {
            "revision_pct": float (örn. +0.12 = %12 yukarı revize),
            "components": {...},
            "rationale": str,
        }
    """
    components = {}

    # 1. Tone component
    tone_score = parse_result.qualitative_signals.tone_score
    tone_component = tone_score * 0.03  # +5 → +%15
    components["tone"] = tone_component

    # 2. Revenue growth surprise
    actual_yoy = parse_result.results_actual.yoy_revenue_growth_pct
    growth_component = 0.0
    if actual_yoy is not None:
        # Pre-earnings consensus YoY'yi snapshot'tan al
        expected_yoy = pre_earnings_snapshot.get("expected_yoy_revenue_growth_pct")
        if expected_yoy is not None:
            surprise = actual_yoy - expected_yoy
            growth_component = (surprise / 5.0) * 0.03  # her +%5 sürpriz → +%3
            growth_component = max(-0.10, min(0.10, growth_component))  # cap ±%10
    components["growth_surprise"] = growth_component

    # 3. Sector momentum
    components["sector_momentum"] = sector_momentum_factor

    # 4. Methodology change penalty
    methodology_penalty = 0.0
    for ai in parse_result.ambiguous_items:
        if "methodology" in ai.field.lower():
            methodology_penalty = -0.05
            break
    components["methodology_penalty"] = methodology_penalty

    # Toplam revision (cap ±%30)
    total_revision = sum(components.values())
    total_revision = max(-0.30, min(0.30, total_revision))

    # Rationale
    parts = []
    if abs(tone_component) > 0.01:
        parts.append(f"tone {tone_score:+d} ({tone_component:+.1%})")
    if abs(growth_component) > 0.01:
        parts.append(f"growth surprise ({growth_component:+.1%})")
    if abs(sector_momentum_factor) > 0.01:
        parts.append(f"sector momentum ({sector_momentum_factor:+.1%})")
    if methodology_penalty < 0:
        parts.append(f"methodology change penalty ({methodology_penalty:.1%})")

    rationale = " + ".join(parts) if parts else "nötr (revize yok)"

    return {
        "revision_pct": round(total_revision, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "rationale": rationale,
    }


def implied_multiple_valuation(
    parse_result: EarningsParse,
    pre_earnings_snapshot: dict,
    current_price: float,
    historical_beat_rate_pct: float = 5.0,
    analyst_fwd_eps_fy1: Optional[float] = None,
    analyst_fwd_revenue_fy1_b: Optional[float] = None,
    use_normalized_eps: bool = True,
    sector_momentum_factor: float = 0.0,
    apply_multiple_revision: bool = True,
) -> dict:
    """
    Implied Multiple değerleme hesaplaması (v2.0 — no-guidance fallback dahil).

    pre_earnings_snapshot:
        {
          "target_avg_pre": 180.0,
          "target_high_pre": 220.0,
          "forward_eps_pre": 4.00,
          "forward_revenue_per_share_pre": 7.50,
        }

    Args:
        analyst_fwd_eps_fy1: Guidance yoksa fallback için FMP analyst-estimates'ten
            FY+1 yıllık EPS konsensüsü. None ise sıradaki fallback'e geçer.
        analyst_fwd_revenue_fy1_b: Aynısı revenue için (USD billions).
        use_normalized_eps: True ise GAAP EPS'ten one_time_items çıkarılıp
            annualize edilir. False ise ham GAAP EPS × 4 kullanılır.
    """
    # Zımni çarpanları hesapla (pre-earnings analist bazlı)
    fwd_eps_pre = pre_earnings_snapshot.get("forward_eps_pre")
    fwd_rps_pre = pre_earnings_snapshot.get("forward_revenue_per_share_pre")
    target_avg_pre = pre_earnings_snapshot.get("target_avg_pre")
    target_high_pre = pre_earnings_snapshot.get("target_high_pre")

    pe_avg_raw = (target_avg_pre / fwd_eps_pre) if (target_avg_pre and fwd_eps_pre and fwd_eps_pre > 0) else None
    pe_high_raw = (target_high_pre / fwd_eps_pre) if (target_high_pre and fwd_eps_pre and fwd_eps_pre > 0) else None
    ps_avg_raw = (target_avg_pre / fwd_rps_pre) if (target_avg_pre and fwd_rps_pre and fwd_rps_pre > 0) else None
    ps_high_raw = (target_high_pre / fwd_rps_pre) if (target_high_pre and fwd_rps_pre and fwd_rps_pre > 0) else None

    # Çarpan revizesi (post-earnings re-rating)
    revision_info = None
    if apply_multiple_revision:
        revision_info = compute_multiple_revision(
            parse_result=parse_result,
            pre_earnings_snapshot=pre_earnings_snapshot,
            sector_momentum_factor=sector_momentum_factor,
        )
        revision_mult = 1 + revision_info["revision_pct"]
        pe_avg = pe_avg_raw * revision_mult if pe_avg_raw else None
        pe_high = pe_high_raw * revision_mult if pe_high_raw else None
        ps_avg = ps_avg_raw * revision_mult if ps_avg_raw else None
        ps_high = ps_high_raw * revision_mult if ps_high_raw else None
    else:
        pe_avg, pe_high = pe_avg_raw, pe_high_raw
        ps_avg, ps_high = ps_avg_raw, ps_high_raw

    # Yeni forward EPS — 4 katmanlı fallback
    guidance_q = parse_result.guidance_next_quarter
    guidance_fy = parse_result.guidance_full_year

    forward_eps_source = None  # Hangi kaynaktan geldiğini takip et

    if guidance_fy.provided and guidance_fy.non_gaap_eps_mid:
        method1_eps = guidance_fy.non_gaap_eps_mid
        forward_eps_source = "company_guidance_fy"
    elif guidance_q.provided and guidance_q.non_gaap_eps_mid:
        method1_eps = guidance_q.non_gaap_eps_mid * 4
        forward_eps_source = "company_guidance_q_annualized"
    elif analyst_fwd_eps_fy1 is not None:
        # FALLBACK 1: Analist FY+1 konsensüsü
        method1_eps = analyst_fwd_eps_fy1
        forward_eps_source = "analyst_consensus_fy1"
    else:
        # FALLBACK 2: Current quarter actual EPS × 4 (normalize edilebilir)
        if use_normalized_eps:
            current_eps = normalize_eps_from_one_time_items(parse_result)
        else:
            current_eps = parse_result.results_actual.non_gaap_eps or parse_result.results_actual.gaap_eps
        if current_eps is not None:
            method1_eps = current_eps * 4
            forward_eps_source = "current_quarter_annualized_normalized" if use_normalized_eps else "current_quarter_annualized_raw"
        else:
            method1_eps = None
            forward_eps_source = "no_data"

    forward_eps_post = None
    if method1_eps is not None:
        method2_eps = method1_eps * (1 + historical_beat_rate_pct / 100)
        if fwd_eps_pre and fwd_eps_pre > 0:
            consensus_delta_pct = (method1_eps / fwd_eps_pre - 1) * 100
            method3_eps = fwd_eps_pre * (1 + consensus_delta_pct / 100 * 0.7)
            forward_eps_post = 0.4 * method1_eps + 0.3 * method2_eps + 0.3 * method3_eps
        else:
            # Pre-earnings forward EPS yok — sadece method1+method2 blend
            forward_eps_post = 0.6 * method1_eps + 0.4 * method2_eps

    # Yeni forward revenue per share — 3 katmanlı fallback
    forward_rev_per_share_post = None
    shares_m = parse_result.results_actual.diluted_share_count_m
    forward_rev_source = None

    if guidance_fy.provided and guidance_fy.revenue_mid_b and shares_m:
        forward_rev_per_share_post = guidance_fy.revenue_mid_b * 1000 / shares_m
        forward_rev_source = "company_guidance_fy"
    elif guidance_q.provided and guidance_q.revenue_mid_b and shares_m:
        forward_rev_per_share_post = guidance_q.revenue_mid_b * 1000 * 4 / shares_m
        forward_rev_source = "company_guidance_q_annualized"
    elif analyst_fwd_revenue_fy1_b is not None and shares_m:
        forward_rev_per_share_post = analyst_fwd_revenue_fy1_b * 1000 / shares_m
        forward_rev_source = "analyst_consensus_fy1"
    elif parse_result.results_actual.revenue_usd_b and shares_m:
        # FALLBACK 3: Current quarter revenue × 4 annualize
        forward_rev_per_share_post = parse_result.results_actual.revenue_usd_b * 1000 * 4 / shares_m
        forward_rev_source = "current_quarter_annualized"

    # Implied multiple uygula
    new_target_avg_eps = pe_avg * forward_eps_post if forward_eps_post else None
    new_target_high_eps = pe_high * forward_eps_post if forward_eps_post else None
    new_target_avg_rev = ps_avg * forward_rev_per_share_post if forward_rev_per_share_post else None
    new_target_high_rev = ps_high * forward_rev_per_share_post if forward_rev_per_share_post else None

    # Final blend (EPS varsa %70 EPS / %30 Rev)
    if new_target_avg_eps is not None and new_target_avg_rev is not None:
        final_avg = 0.7 * new_target_avg_eps + 0.3 * new_target_avg_rev
        final_high = 0.7 * new_target_high_eps + 0.3 * new_target_high_rev
    elif new_target_avg_eps is not None:
        final_avg = new_target_avg_eps
        final_high = new_target_high_eps
    elif new_target_avg_rev is not None:
        final_avg = new_target_avg_rev
        final_high = new_target_high_rev
    else:
        final_avg = final_high = None

    # Upside hesapla
    upside_avg = (final_avg / current_price - 1) * 100 if final_avg else None
    upside_high = (final_high / current_price - 1) * 100 if final_high else None

    # Karar matrisi
    if upside_avg is None:
        decision = "VERİ YETERSİZ"
    elif upside_avg > 20:
        decision = "AL"
    elif upside_avg > -5:
        decision = "İZLE"
    else:
        decision = "GEÇ"

    # Tone override
    if parse_result.qualitative_signals.tone_score <= -3 and decision == "AL":
        decision = "İZLE"

    return {
        "implied_multiples_raw": {
            "pe_avg": round(pe_avg_raw, 2),
            "pe_high": round(pe_high_raw, 2),
            "ps_avg": round(ps_avg_raw, 2),
            "ps_high": round(ps_high_raw, 2),
        },
        "implied_multiples": {
            "pe_avg": round(pe_avg, 2),
            "pe_high": round(pe_high, 2),
            "ps_avg": round(ps_avg, 2),
            "ps_high": round(ps_high, 2),
        },
        "multiple_revision": revision_info,
        "forward_inputs": {
            "forward_eps_post": round(forward_eps_post, 2) if forward_eps_post else None,
            "forward_eps_source": forward_eps_source,
            "forward_rev_per_share_post": round(forward_rev_per_share_post, 2) if forward_rev_per_share_post else None,
            "forward_rev_source": forward_rev_source,
        },
        "new_targets": {
            "target_avg": round(final_avg, 2) if final_avg else None,
            "target_high": round(final_high, 2) if final_high else None,
        },
        "upside_pct": {
            "avg": round(upside_avg, 1) if upside_avg else None,
            "high": round(upside_high, 1) if upside_high else None,
        },
        "current_price": current_price,
        "decision": decision,
        "tone_score": parse_result.qualitative_signals.tone_score,
        "confidence": parse_result.confidence.overall,
    }
