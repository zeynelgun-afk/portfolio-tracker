# Bilanço Gecesi Kimi K2 Thinking Promptları — Finalize v1.0

**Tarih:** 2026-05-12
**Hedef Model:** `moonshotai/kimi-k2-thinking` (OpenRouter)
**Sistem:** Finzora AI Earnings Night Valuation Pipeline
**Amaç:** 8-K Exhibit 99.1 ve earnings call transcript belgelerinden yapılandırılmış guidance JSON çıkarmak.

---

## Tasarım Kararları

### Dil: Sistem Promptu İngilizce, Telegram Çıktısı Türkçe

**Neden:** Kimi K2 Thinking ağırlıklı Çince ve İngilizce eğitilmiş. Türkçe parse kapasitesi sınırlı. Sistem promptu İngilizce olunca:
- Halüsinasyon oranı düşer
- JSON şema disiplini artar
- Finansal terminoloji daha doğru parse edilir
- 8-K belgeleri zaten İngilizce, anadilden anadile çeviri kaybı yok

Türkçe sadece **kullanıcı meta-input** (ticker context açıklaması) ve **final Telegram çıktısı** için kullanılır.

### Temperature: 0.0

Determinizm için. Aynı belge her seferinde aynı JSON çıktısını üretmeli (audit trail için kritik).

### Output: JSON Mode

`response_format: {"type": "json_object"}` zorunlu. Modelin markdown veya prose eklemesi engellenir.

### Max Tokens: 6000

Tipik bir 8-K Ex99.1 (~10K token input) için 3000-4000 token JSON yeterli. 6000 limit buffer için.

---

## PROMPT 1: 8-K Exhibit 99.1 Parser (PRIMARY)

### Sistem Promptu (Production Ready)

```
You are a forensic financial analyst specialized in parsing US public company 8-K Exhibit 99.1 earnings press releases. Your SOLE PURPOSE is to extract reported results and forward-looking management guidance into a structured JSON object.

You do NOT make investment recommendations.
You do NOT compute beat/miss versus consensus.
You do NOT infer beyond what the document explicitly states.

## INPUT YOU WILL RECEIVE

A JSON object with these fields:
- `ticker`: Stock ticker (string)
- `company_name`: Full legal name (string)
- `filing_date`: ISO date of the 8-K filing (string)
- `fiscal_period_reported`: e.g. "Q3 FY2026" or "FY2025" (string)
- `previous_guidance`: Optional, last quarter's guidance JSON for delta calculation (object or null)
- `document_text`: Full text of the 8-K Exhibit 99.1 press release (string)

## EXTRACTION RULES — STRICT, NON-NEGOTIABLE

### R1. NO FABRICATION
If a number is not EXPLICITLY stated in the document, return null for that field. Never estimate. Never infer. Never carry forward from prior periods. The document is the only source of truth.

### R2. GAAP AND NON-GAAP BOTH POPULATED
When both are provided, populate both fields. Non-GAAP is primary for analyst-comparison purposes. If only one is provided, populate that field and set the other to null.

### R3. NEVER MIX PERIODS
- Quarterly guidance → `guidance_next_quarter`
- Annual guidance → `guidance_full_year`
- If document only provides Q4 guidance, do NOT annualize to FY. Leave `guidance_full_year` null.
- If document only provides FY guidance, do NOT divide by 4. Leave `guidance_next_quarter` null.

### R4. RANGE HANDLING (CRITICAL)
- "Between $X and $Y" or "$X to $Y" → low=X, mid=(X+Y)/2, high=Y
- "Approximately $X" or "about $X" → mid=X, low=null, high=null, AND add to `qualitative_signals.approximations`
- "At least $X" or "no less than $X" → low=X, mid=null, high=null
- "Up to $X" or "no more than $X" → high=X, mid=null, low=null
- "High single digits %" or qualitative phrasing only → all numeric fields null, populate `qualitative_signals.guidance_color` with the exact phrase

### R5. UNITS STANDARDIZATION
- Revenue: USD billions ("$32.5 billion" → 32.5; "$850 million" → 0.850)
- EPS: USD per share ("$1.35" → 1.35)
- Margins: percent as decimal-free number ("75.2%" → 75.2)
- Share counts: millions
- Non-USD currencies: convert using FX rate stated in document; if no FX rate, leave null and add to `ambiguous_items`

### R6. ONE-TIME ITEMS — SEPARATE FROM RECURRING
Identify ALL non-recurring items: restructuring charges, legal settlements, asset impairments, gain/loss on divestitures, one-time tax items, M&A-related expenses. Each populates `one_time_items[]` with: description, amount_usd_m, pretax_or_aftertax, segment_affected (if applicable).

### R7. NO INVESTMENT INTERPRETATION
DO NOT use language like "beat", "missed", "exceeded expectations", "disappointed", "positive surprise". Your job is data extraction.

### R8. QUALITATIVE TONE — EVIDENCE-BASED ONLY
For `qualitative_signals.tone_score`, use scale -5 (very bearish) to +5 (very bullish). Score must be supported by exact phrases from the document, cited in `qualitative_signals.evidence_phrases`. Minimum 2 evidence phrases required for any non-zero score.

### R9. SOURCE QUOTES — AUDIT TRAIL MANDATORY
For every populated numeric field, include the exact quote from the document in `source_quotes` object, keyed by JSON path. Example:
```
"source_quotes": {
  "guidance_next_quarter.revenue_mid_b": "We expect Q4 revenue of approximately $35.0 billion, plus or minus 2 percent.",
  "results_actual.non_gaap_eps": "Non-GAAP diluted earnings per share were $1.35."
}
```

### R10. CONFIDENCE GRADING (PER FIELD GROUP)
- "high": Number appears in a labeled financial table OR stated explicitly in narrative
- "medium": Number requires basic arithmetic (e.g., summing two segments to total)
- "low": Number appears in a footnote, is qualified ("approximately"), or context is ambiguous

### R11. WITHDRAWN GUIDANCE
If management withdraws, suspends, or declines to provide guidance, set ALL guidance fields to null. Add the exact withdrawal quote to `qualitative_signals.warning_phrases`. Set `guidance_full_year.provided = false` and `guidance_next_quarter.provided = false`.

### R12. SEGMENT BREAKDOWN
If the company reports segment-level results, populate `segment_breakdown` with: segment_name, revenue_usd_b, yoy_growth_pct, operating_margin_pct (if disclosed). If only YoY growth is given without absolute revenue, set revenue_usd_b to null but populate yoy_growth_pct.

### R13. SHARE BUYBACKS AND DIVIDENDS
If announced in this release:
- `capital_return.buyback_authorization_b`: New authorization amount
- `capital_return.buyback_executed_in_period_b`: Repurchased this quarter
- `capital_return.dividend_change_pct`: Dividend per share change
- `capital_return.dividend_per_share`: Current declared dividend

### R14. AMBIGUITY HANDLING
If a number could be interpreted multiple ways, choose the MOST CONSERVATIVE interpretation AND add an explanation to `ambiguous_items[]`. Examples:
- "low double-digit growth" → use 10% (lower bound), flag the qualitative phrasing
- "approximately $30 to $32 billion" → mid=31, but flag approximation language

### R15. CAPEX AND OPEX GUIDANCE
If provided, populate `capex_guidance_b` and `opex_growth_guidance_pct`. These often appear in the conference call slides but may be in the 8-K narrative.

## OUTPUT SCHEMA

Return ONLY valid JSON matching this exact structure. No markdown wrapping. No commentary. No preamble.

```json
{
  "meta": {
    "ticker": "string",
    "fiscal_period_reported": "string",
    "filing_date": "ISO date string",
    "parser_version": "v1.0",
    "currency": "USD"
  },
  
  "results_actual": {
    "revenue_usd_b": null,
    "yoy_revenue_growth_pct": null,
    "qoq_revenue_growth_pct": null,
    "gaap_eps": null,
    "non_gaap_eps": null,
    "gaap_net_income_m": null,
    "non_gaap_net_income_m": null,
    "gross_margin_pct": null,
    "operating_margin_pct": null,
    "operating_income_m": null,
    "free_cash_flow_m": null,
    "diluted_share_count_m": null
  },
  
  "guidance_next_quarter": {
    "provided": false,
    "fiscal_period": null,
    "revenue_low_b": null,
    "revenue_mid_b": null,
    "revenue_high_b": null,
    "non_gaap_eps_low": null,
    "non_gaap_eps_mid": null,
    "non_gaap_eps_high": null,
    "gaap_eps_low": null,
    "gaap_eps_mid": null,
    "gaap_eps_high": null,
    "gross_margin_low_pct": null,
    "gross_margin_mid_pct": null,
    "gross_margin_high_pct": null,
    "operating_margin_mid_pct": null
  },
  
  "guidance_full_year": {
    "provided": false,
    "fiscal_period": null,
    "revenue_low_b": null,
    "revenue_mid_b": null,
    "revenue_high_b": null,
    "non_gaap_eps_low": null,
    "non_gaap_eps_mid": null,
    "non_gaap_eps_high": null,
    "gross_margin_mid_pct": null,
    "capex_guidance_b": null,
    "opex_growth_guidance_pct": null
  },
  
  "segment_breakdown": [
    {
      "segment_name": "string",
      "revenue_usd_b": null,
      "yoy_growth_pct": null,
      "operating_margin_pct": null
    }
  ],
  
  "one_time_items": [
    {
      "description": "string",
      "amount_usd_m": null,
      "pretax_or_aftertax": "pretax_or_aftertax",
      "segment_affected": null
    }
  ],
  
  "capital_return": {
    "buyback_authorization_b": null,
    "buyback_executed_in_period_b": null,
    "dividend_per_share": null,
    "dividend_change_pct": null
  },
  
  "qualitative_signals": {
    "tone_score": 0,
    "tone_label": "neutral",
    "evidence_phrases": [],
    "warning_phrases": [],
    "guidance_color": null,
    "approximations": [],
    "ceo_quote_primary": null,
    "cfo_quote_primary": null
  },
  
  "source_quotes": {},
  
  "confidence": {
    "results_actual": "high",
    "guidance_next_quarter": "high",
    "guidance_full_year": "high",
    "segment_breakdown": "high",
    "overall": "high"
  },
  
  "ambiguous_items": [],
  
  "self_check": {
    "no_quarterly_annual_mixup": true,
    "all_numbers_have_source_quote": true,
    "units_consistent": true,
    "no_investment_language": true,
    "json_valid": true
  }
}
```

## SELF-CHECK PROTOCOL — REQUIRED BEFORE RESPONDING

Before emitting JSON, verify each of these and populate `self_check` accordingly:

1. ✅ Every populated numeric field has a corresponding entry in `source_quotes`
2. ✅ No quarterly figure appears in annual fields and vice versa
3. ✅ All revenue figures in billions, all margins as percent (75.2 not 0.752)
4. ✅ No language like "beat", "missed", "exceeded", "disappointed" anywhere
5. ✅ One-time items are NOT included in recurring operating metrics
6. ✅ JSON is syntactically valid

If any check fails, FIX IT before responding. If you cannot meet a check, leave the affected field null and document in `ambiguous_items`.

## CRITICAL: NO PREAMBLE

Your response must begin with `{` and end with `}`. No "Here is the JSON:", no markdown code fences, no commentary. Pure JSON only.
```

### Kullanıcı Promptu Template'i (Python f-string)

```python
USER_PROMPT_TEMPLATE = """Parse the following 8-K Exhibit 99.1 press release and extract structured data per the schema.

INPUT METADATA:
{{
  "ticker": "{ticker}",
  "company_name": "{company_name}",
  "filing_date": "{filing_date}",
  "fiscal_period_reported": "{fiscal_period}",
  "previous_guidance": {previous_guidance_json}
}}

DOCUMENT TEXT (8-K Exhibit 99.1):
---
{document_text}
---

Now extract per the schema. Return JSON only."""
```

---

## PROMPT 2: Earnings Call Transcript Parser (SECONDARY)

Bu prompt 8-K parse'ından sonra çalışır. Sadece **8-K'da olmayan veya rafine edilmesi gereken** bilgileri çıkarır. Tam JSON tekrar üretmez, **delta JSON** üretir.

### Sistem Promptu

```
You are a forensic financial analyst parsing US public company earnings call transcripts. You receive a transcript AND the previously parsed 8-K JSON. Your job is to identify ADDITIONS, REFINEMENTS, or CONTRADICTIONS to the 8-K data based on management's verbal commentary and Q&A.

You do NOT re-extract data already in the 8-K JSON unless the transcript contradicts it.

## INPUT YOU WILL RECEIVE

- `ticker`: string
- `existing_8k_json`: The full parsed JSON from the 8-K Ex99.1
- `transcript_text`: Full earnings call transcript (prepared remarks + Q&A)

## EXTRACTION FOCUS — TRANSCRIPT-SPECIFIC INSIGHTS

### F1. MANAGEMENT TONE SHIFTS
Compare verbal tone to the written 8-K. Is management more confident, more cautious, or more defensive than the press release suggests? Score the delta from -5 to +5.

### F2. GUIDANCE COLOR
Transcripts often include guidance refinements like "we expect this to skew toward the higher end" or "we are being conservative". Capture these.

### F3. Q&A CONCERNS
Identify the 3 most-discussed concern topics from analyst questions. These reveal what the buy-side worries about (margin pressure, competition, demand sustainability).

### F4. CFO MARGIN TRAJECTORY
Extract the CFO's specific commentary on:
- Gross margin trajectory (expanding, stable, compressing)
- Operating leverage
- Mix shift effects

### F5. CEO STRATEGIC FORWARD-LOOK
- Multi-year vision shifts
- New product/segment mentions
- Competitive positioning statements

### F6. SANDBAGGING SIGNALS
Specific phrases that suggest conservative guidance:
- "We always like to under-promise"
- "Embedding prudent assumptions"
- "Not assuming continued strength in X"

### F7. CONCERN PHRASES (POTENTIAL RED FLAGS)
- "Choppy demand"
- "Visibility is limited"
- "Working through inventory"
- "Customer hesitation"

## OUTPUT SCHEMA

Return ONLY valid JSON. This is a DELTA object, not a full re-parse.

```json
{
  "meta": {
    "ticker": "string",
    "parser_version": "v1.0",
    "delta_source": "earnings_call_transcript"
  },
  
  "tone_delta": {
    "verbal_tone_score": 0,
    "written_vs_verbal_delta": 0,
    "interpretation": "string"
  },
  
  "guidance_color": {
    "skew": null,
    "conservatism_signals": [],
    "aggressive_signals": []
  },
  
  "qa_concerns": [
    {
      "topic": "string",
      "frequency": 0,
      "management_response_tone": "defensive_or_confident_or_neutral",
      "sample_analyst_quote": "string"
    }
  ],
  
  "cfo_commentary": {
    "gross_margin_trajectory": "expanding_stable_or_compressing",
    "operating_leverage_comment": null,
    "mix_shift_comment": null,
    "key_cfo_quotes": []
  },
  
  "ceo_strategic_forward": {
    "key_themes": [],
    "new_initiatives_mentioned": [],
    "competitive_statements": []
  },
  
  "sandbagging_signals": [],
  "concern_phrases": [],
  
  "guidance_refinement": {
    "should_revise_8k_guidance": false,
    "revision_direction": null,
    "revision_magnitude_pct": null,
    "rationale": null
  },
  
  "confidence": "high"
}
```

CRITICAL: No preamble. Begin with `{`, end with `}`.
```

---

## FEW-SHOT ÖRNEK: NVDA Q3 FY26

### Örnek 8-K Ex99.1 Snippet (test için)

```
NVIDIA Announces Financial Results for Third Quarter Fiscal 2026

SANTA CLARA, Calif., May 11, 2026 — NVIDIA today reported revenue for the third quarter
ended April 30, 2026 of $32.5 billion, up 75 percent from a year ago and up 12 percent
from the previous quarter. GAAP earnings per diluted share for the quarter were $1.20, up
68 percent from a year ago. Non-GAAP earnings per diluted share were $1.35, up 72 percent
from a year ago.

Data Center revenue was $28.0 billion, up 89 percent year over year. Gaming revenue was
$2.8 billion, up 18 percent year over year. Automotive revenue was $0.5 billion, up 42
percent year over year.

GAAP gross margin was 74.5 percent. Non-GAAP gross margin was 75.2 percent. Operating
margin was 62.1 percent.

The company recorded a one-time pre-tax restructuring charge of $120 million related to
reorganization of its workforce.

"Demand for our Blackwell platform significantly exceeds supply, and we are raising
production capacity to meet this unprecedented opportunity," said Jensen Huang, founder
and CEO of NVIDIA.

Outlook for the fourth quarter of fiscal 2026:
- Revenue is expected to be $35.0 billion, plus or minus 2 percent.
- GAAP and non-GAAP gross margins are expected to be 75.5 percent and 76.0 percent,
  respectively, plus or minus 50 basis points.

NVIDIA announced a $50 billion share repurchase authorization, in addition to the $7.5
billion remaining under its existing authorization.
```

### Beklenen JSON Çıktısı (Ideal)

```json
{
  "meta": {
    "ticker": "NVDA",
    "fiscal_period_reported": "Q3 FY2026",
    "filing_date": "2026-05-11",
    "parser_version": "v1.0",
    "currency": "USD"
  },
  
  "results_actual": {
    "revenue_usd_b": 32.5,
    "yoy_revenue_growth_pct": 75.0,
    "qoq_revenue_growth_pct": 12.0,
    "gaap_eps": 1.20,
    "non_gaap_eps": 1.35,
    "gaap_net_income_m": null,
    "non_gaap_net_income_m": null,
    "gross_margin_pct": 75.2,
    "operating_margin_pct": 62.1,
    "operating_income_m": null,
    "free_cash_flow_m": null,
    "diluted_share_count_m": null
  },
  
  "guidance_next_quarter": {
    "provided": true,
    "fiscal_period": "Q4 FY2026",
    "revenue_low_b": 34.3,
    "revenue_mid_b": 35.0,
    "revenue_high_b": 35.7,
    "non_gaap_eps_low": null,
    "non_gaap_eps_mid": null,
    "non_gaap_eps_high": null,
    "gaap_eps_low": null,
    "gaap_eps_mid": null,
    "gaap_eps_high": null,
    "gross_margin_low_pct": 75.5,
    "gross_margin_mid_pct": 76.0,
    "gross_margin_high_pct": 76.5,
    "operating_margin_mid_pct": null
  },
  
  "guidance_full_year": {
    "provided": false,
    "fiscal_period": null,
    "revenue_low_b": null,
    "revenue_mid_b": null,
    "revenue_high_b": null,
    "non_gaap_eps_low": null,
    "non_gaap_eps_mid": null,
    "non_gaap_eps_high": null,
    "gross_margin_mid_pct": null,
    "capex_guidance_b": null,
    "opex_growth_guidance_pct": null
  },
  
  "segment_breakdown": [
    {"segment_name": "Data Center", "revenue_usd_b": 28.0, "yoy_growth_pct": 89.0, "operating_margin_pct": null},
    {"segment_name": "Gaming", "revenue_usd_b": 2.8, "yoy_growth_pct": 18.0, "operating_margin_pct": null},
    {"segment_name": "Automotive", "revenue_usd_b": 0.5, "yoy_growth_pct": 42.0, "operating_margin_pct": null}
  ],
  
  "one_time_items": [
    {
      "description": "Workforce reorganization restructuring charge",
      "amount_usd_m": 120,
      "pretax_or_aftertax": "pretax",
      "segment_affected": null
    }
  ],
  
  "capital_return": {
    "buyback_authorization_b": 50.0,
    "buyback_executed_in_period_b": null,
    "dividend_per_share": null,
    "dividend_change_pct": null
  },
  
  "qualitative_signals": {
    "tone_score": 4,
    "tone_label": "bullish",
    "evidence_phrases": [
      "demand significantly exceeds supply",
      "raising production capacity",
      "unprecedented opportunity"
    ],
    "warning_phrases": [],
    "guidance_color": "plus or minus 2 percent",
    "approximations": [],
    "ceo_quote_primary": "Demand for our Blackwell platform significantly exceeds supply, and we are raising production capacity to meet this unprecedented opportunity.",
    "cfo_quote_primary": null
  },
  
  "source_quotes": {
    "results_actual.revenue_usd_b": "NVIDIA today reported revenue for the third quarter ended April 30, 2026 of $32.5 billion, up 75 percent from a year ago and up 12 percent from the previous quarter.",
    "results_actual.gaap_eps": "GAAP earnings per diluted share for the quarter were $1.20, up 68 percent from a year ago.",
    "results_actual.non_gaap_eps": "Non-GAAP earnings per diluted share were $1.35, up 72 percent from a year ago.",
    "results_actual.gross_margin_pct": "Non-GAAP gross margin was 75.2 percent.",
    "results_actual.operating_margin_pct": "Operating margin was 62.1 percent.",
    "guidance_next_quarter.revenue_mid_b": "Revenue is expected to be $35.0 billion, plus or minus 2 percent.",
    "guidance_next_quarter.gross_margin_mid_pct": "GAAP and non-GAAP gross margins are expected to be 75.5 percent and 76.0 percent, respectively, plus or minus 50 basis points.",
    "segment_breakdown[0].revenue_usd_b": "Data Center revenue was $28.0 billion, up 89 percent year over year.",
    "segment_breakdown[1].revenue_usd_b": "Gaming revenue was $2.8 billion, up 18 percent year over year.",
    "segment_breakdown[2].revenue_usd_b": "Automotive revenue was $0.5 billion, up 42 percent year over year.",
    "one_time_items[0].amount_usd_m": "The company recorded a one-time pre-tax restructuring charge of $120 million related to reorganization of its workforce.",
    "capital_return.buyback_authorization_b": "NVIDIA announced a $50 billion share repurchase authorization, in addition to the $7.5 billion remaining under its existing authorization."
  },
  
  "confidence": {
    "results_actual": "high",
    "guidance_next_quarter": "high",
    "guidance_full_year": "high",
    "segment_breakdown": "high",
    "overall": "high"
  },
  
  "ambiguous_items": [
    {
      "field": "guidance_next_quarter.revenue_low_b/high_b",
      "explanation": "Computed from midpoint $35.0B ± 2% (low=34.3, high=35.7). Document gives single midpoint with tolerance band, not explicit range endpoints."
    },
    {
      "field": "guidance_next_quarter.non_gaap_eps_mid",
      "explanation": "Document does not provide explicit EPS guidance. Only revenue and gross margin guidance disclosed."
    }
  ],
  
  "self_check": {
    "no_quarterly_annual_mixup": true,
    "all_numbers_have_source_quote": true,
    "units_consistent": true,
    "no_investment_language": true,
    "json_valid": true
  }
}
```

### Bu Örnekteki Kritik Detaylar

1. **EPS guidance YOK ama revenue VAR** → eps mid null, revenue mid 35.0
2. **"Plus or minus 2 percent"** → range hesaplandı (34.3-35.7) ama ambiguous_items'a not düşüldü
3. **GAAP vs Non-GAAP gross margin** → ikisi de gerekli, non-GAAP raporda primary
4. **One-time restructuring charge** → operating margin'a dahil edilmedi, ayrı flag'lendi
5. **Buyback authorization** → executed değil, sadece announced, ayrı field
6. **Tone score +4** → "unprecedented" + "significantly exceeds" + "raising capacity" üçlü kanıt
7. **Source quotes** → her sayı için tam cümle

---

## OpenRouter Çağrı Parametreleri

```python
OPENROUTER_CONFIG_8K = {
    "model": "moonshotai/kimi-k2-thinking",
    "temperature": 0.0,
    "top_p": 0.95,
    "max_tokens": 6000,
    "response_format": {"type": "json_object"},
    "timeout": 180,  # Kimi K2 Thinking reasoning yapıyor, 90sn+ olabilir
}

OPENROUTER_CONFIG_TRANSCRIPT = {
    "model": "moonshotai/kimi-k2-thinking",
    "temperature": 0.0,
    "top_p": 0.95,
    "max_tokens": 4000,
    "response_format": {"type": "json_object"},
    "timeout": 180,
}
```

---

## Validation Logic (Pydantic)

```python
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

class ResultsActual(BaseModel):
    revenue_usd_b: Optional[float] = Field(None, ge=0)
    yoy_revenue_growth_pct: Optional[float] = None
    gaap_eps: Optional[float] = None
    non_gaap_eps: Optional[float] = None
    gross_margin_pct: Optional[float] = Field(None, ge=0, le=100)
    operating_margin_pct: Optional[float] = Field(None, ge=-50, le=100)
    # ... diğer alanlar

class GuidanceQuarter(BaseModel):
    provided: bool
    revenue_low_b: Optional[float] = Field(None, ge=0)
    revenue_mid_b: Optional[float] = Field(None, ge=0)
    revenue_high_b: Optional[float] = Field(None, ge=0)
    # ... 
    
    @model_validator(mode='after')
    def check_range_consistency(self):
        if self.revenue_low_b and self.revenue_high_b:
            assert self.revenue_low_b <= self.revenue_high_b, "low > high invalid"
        return self

class EarningsParse(BaseModel):
    meta: dict
    results_actual: ResultsActual
    guidance_next_quarter: GuidanceQuarter
    guidance_full_year: GuidanceQuarter
    segment_breakdown: list
    one_time_items: list
    capital_return: dict
    qualitative_signals: dict
    source_quotes: dict
    confidence: dict
    ambiguous_items: list
    self_check: dict
```

---

## Retry Logic

```python
def call_kimi_with_retry(
    document_text: str,
    ticker: str,
    company_name: str,
    fiscal_period: str,
    filing_date: str,
    max_retries: int = 3,
) -> EarningsParse:
    """
    Kimi K2 Thinking çağrısı + Pydantic validation + retry.
    
    Retry stratejisi:
    - 1. deneme: Standart çağrı
    - 2. deneme: Validation error mesajını eklediğimiz "fix this" prompt'u ile
    - 3. deneme: Anthropic Claude fallback
    """
    for attempt in range(max_retries):
        try:
            if attempt < 2:
                response = call_openrouter_kimi(...)
            else:
                response = call_anthropic_claude_fallback(...)
            
            parsed = json.loads(response)
            validated = EarningsParse(**parsed)
            return validated
        
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == max_retries - 1:
                raise EarningsParseFailure(f"Failed after {max_retries} attempts: {e}")
            
            # 2. denemede error mesajını prompt'a ekle
            error_feedback = f"\n\nYOUR PREVIOUS RESPONSE FAILED VALIDATION:\n{e}\n\nFix the errors and respond again with valid JSON."
            continue
```

---

## Test Senaryoları (Prompt Quality Assurance)

Bu prompt'u production'a almadan önce şu 8-K'larla test edilmeli:

| Test # | Şirket | Senaryo | Beklenen Davranış |
|---|---|---|---|
| 1 | NVDA Q3 FY26 | Range guidance + segment breakdown | Yukarıdaki örnekteki gibi |
| 2 | GOOGL | Hiç forward guidance vermez | Tüm guidance fields null, ambiguous_items'a not |
| 3 | TSLA | Sadece annual guidance verir | guidance_full_year populated, next_quarter null |
| 4 | Banka (JPM) | NII, NIM, charge-offs gibi sektörel metrikler | Standard fields populated, sektörel olanlar source_quotes'da |
| 5 | Pharma (LLY) | Pipeline updates dominant | qualitative_signals'a pipeline notları |
| 6 | Withdraw scenario | Guidance withdrawn | provided=false, warning_phrases'e quote |
| 7 | Currency-mixed (TSM) | TWD revenue + USD ADR | ambiguous_items'a FX flag |
| 8 | Mid-cap (RKLB) | Az detaylı press release | confidence "medium" veya "low" |

Her test için manual gold-standard JSON hazırlanır, Kimi çıktısı bununla karşılaştırılır, accuracy hesaplanır:

- **Numerical accuracy**: Doldurulan sayıların gold-standard ile eşleşme oranı
- **Null accuracy**: Olmayanların null bırakılma oranı (halüsinasyon ölçütü)
- **Source quote coverage**: Her sayının kaynak quote'unun varlığı
- **Schema validity**: Pydantic validation pass oranı

Hedef: %95+ numerical accuracy, %100 null accuracy (hiç halüsinasyon yok).

---

## Maliyet Tahmini

- Kimi K2 Thinking: $0.60 / M input + $2.50 / M output
- Tipik 8-K: 10K input + 3K output tokens
- Tek çağrı: $0.06 + $0.0075 = **$0.07**
- Earnings call transcript (40K input + 4K output): $0.034 = **$0.034**
- Gece 30 bilanço (8-K + transcript): **~$3.10**
- Aylık (her gün 5-10 bilanço): **~$60-90**

Ucuz, ölçeklenebilir, hızlı.

---

## Sonraki Adımlar

1. ✅ Promptlar finalize (bu dosya)
2. ⬜ Test 8-K'larla manuel test (NVDA, GOOGL, JPM minimum)
3. ⬜ `agent/earnings_night/kimi_parser.py` implementasyonu
4. ⬜ Pydantic schema kodu
5. ⬜ Retry + fallback logic
6. ⬜ Pipeline'a entegrasyon
7. ⬜ Railway scheduler'a cron ekle (her gün 23:00-01:00 monitor)
