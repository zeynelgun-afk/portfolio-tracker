"""
Earnings Night Pipeline — Multi-Fixture Test Suite

Her fixture için:
1. press_release.txt → Kimi K2.5 parse
2. Pydantic validation
3. Beklenen check'lerle karşılaştırma
4. Accuracy raporu

Kullanım:
    export OPENROUTER_API_KEY="sk-or-v1-..."
    python -m agent.earnings_night.test_suite

Yeni fixture eklemek:
    1. fixtures/{ticker}_{period}/press_release.txt ekle
    2. CHECKS dict'ine beklenen değerleri ekle
"""
from __future__ import annotations
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.earnings_night import KimiEarningsParser, EarningsParse


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@dataclass
class CheckResult:
    name: str
    expected: Any
    actual: Any
    passed: bool
    tolerance: Optional[float] = None


@dataclass
class FixtureResult:
    fixture_name: str
    parse_success: bool
    duration_sec: float
    cost_usd: float
    checks: list[CheckResult] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def pass_count(self):
        return sum(1 for c in self.checks if c.passed)

    @property
    def total_count(self):
        return len(self.checks)

    @property
    def accuracy_pct(self):
        if not self.checks:
            return 0.0
        return self.pass_count / self.total_count * 100


def check_eq(name, expected, actual, tolerance=None):
    """Eşitlik check'i. Tolerance ile sayısal yakınlık."""
    if expected is None and actual is None:
        return CheckResult(name, expected, actual, True)
    if expected is None or actual is None:
        return CheckResult(name, expected, actual, False)
    if tolerance and isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        passed = abs(expected - actual) <= tolerance
    else:
        passed = expected == actual
    return CheckResult(name, expected, actual, passed, tolerance)


# Fixture beklentileri — gold-standard'a göre key checks
FIXTURE_CHECKS = {
    "nvda_q4fy26": {
        "filing_date": "2026-02-25",
        "fiscal_period": "Q4 FY2026",
        "company_name": "NVIDIA Corporation",
        "ticker": "NVDA",
        "checks": lambda p: [
            check_eq("revenue_usd_b", 68.127, p.results_actual.revenue_usd_b, 0.1),
            check_eq("yoy_revenue_growth_pct", 73.0, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("gaap_eps", 1.76, p.results_actual.gaap_eps, 0.02),
            check_eq("non_gaap_eps", 1.62, p.results_actual.non_gaap_eps, 0.02),
            check_eq("gross_margin_pct (Non-GAAP)", 75.2, p.results_actual.gross_margin_pct, 0.5),
            check_eq("operating_margin_pct (Non-GAAP)", 67.7, p.results_actual.operating_margin_pct, 1.0),
            check_eq("diluted_share_count_m", 24432.0, p.results_actual.diluted_share_count_m, 100.0),
            check_eq("guidance_q1_provided", True, p.guidance_next_quarter.provided),
            check_eq("guidance_q1_revenue_mid_b", 78.0, p.guidance_next_quarter.revenue_mid_b, 0.5),
            check_eq("guidance_q1_revenue_low_b", 76.44, p.guidance_next_quarter.revenue_low_b, 0.5),
            check_eq("guidance_q1_revenue_high_b", 79.56, p.guidance_next_quarter.revenue_high_b, 0.5),
            check_eq("guidance_fy_provided", False, p.guidance_full_year.provided),
            check_eq("segment_count", 4, len(p.segment_breakdown)),
            check_eq("tone_score (very_bullish)", True, p.qualitative_signals.tone_score >= 4),
            check_eq("evidence_phrases_min", True, len(p.qualitative_signals.evidence_phrases) >= 2),
            check_eq("buyback_auth_remaining_b", 58.5, p.capital_return.buyback_authorization_b, 1.0),
        ],
    },
    "googl_q1_2026": {
        "filing_date": "2026-04-29",
        "fiscal_period": "Q1 2026",
        "company_name": "Alphabet Inc.",
        "ticker": "GOOGL",
        "checks": lambda p: [
            check_eq("revenue_usd_b", 109.896, p.results_actual.revenue_usd_b, 0.2),
            check_eq("yoy_revenue_growth_pct", 22.0, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("gaap_eps", 5.11, p.results_actual.gaap_eps, 0.02),
            check_eq("non_gaap_eps (GOOGL non-GAAP yok)", None, p.results_actual.non_gaap_eps),
            check_eq("operating_margin_pct", 36.0, p.results_actual.operating_margin_pct, 1.0),
            check_eq("diluted_share_count_m", 12238.0, p.results_actual.diluted_share_count_m, 100.0),
            check_eq("guidance_q_provided (GOOGL guidance vermez)", False, p.guidance_next_quarter.provided),
            check_eq("guidance_fy_provided", False, p.guidance_full_year.provided),
            check_eq("segment_count", 3, len(p.segment_breakdown)),
            check_eq("equity_gains_one_time_flagged", True, len(p.one_time_items) >= 1),
            check_eq("dividend_per_share", 0.22, p.capital_return.dividend_per_share, 0.01),
            check_eq("dividend_change_pct", 5.0, p.capital_return.dividend_change_pct, 0.5),
            check_eq("tone_score (very_bullish)", True, p.qualitative_signals.tone_score >= 4),
        ],
    },
    "tsla_q1_2026": {
        "filing_date": "2026-04-22",
        "fiscal_period": "Q1 2026",
        "company_name": "Tesla, Inc.",
        "ticker": "TSLA",
        "checks": lambda p: [
            check_eq("revenue_usd_b", 22.387, p.results_actual.revenue_usd_b, 0.1),
            check_eq("yoy_revenue_growth_pct", 16.0, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("gaap_eps", 0.13, p.results_actual.gaap_eps, 0.02),
            check_eq("non_gaap_eps", 0.41, p.results_actual.non_gaap_eps, 0.02),
            check_eq("gross_margin_pct (GAAP)", 21.1, p.results_actual.gross_margin_pct, 0.5),
            check_eq("operating_margin_pct", 4.2, p.results_actual.operating_margin_pct, 0.3),
            check_eq("free_cash_flow_m", 1444.0, p.results_actual.free_cash_flow_m, 50),
            check_eq("guidance_q_provided (TSLA qualitative only)", False, p.guidance_next_quarter.provided),
            check_eq("guidance_fy_provided (qualitative only)", False, p.guidance_full_year.provided),
            check_eq("segment_count_min", True, len(p.segment_breakdown) >= 3),
            check_eq("tone_score (bullish AI/Optimus narrative)", True, p.qualitative_signals.tone_score >= 2),
        ],
    },
    "jpm_q1_2026": {
        "filing_date": "2026-04-14",
        "fiscal_period": "Q1 2026",
        "company_name": "JPMorgan Chase & Co.",
        "ticker": "JPM",
        "checks": lambda p: [
            # JPM banka — revenue "managed" vs "reported" ayrımı, ikisi de kabul edilebilir
            check_eq("revenue_usd_b (50.5 managed veya 49.8 reported)", True,
                     p.results_actual.revenue_usd_b is not None
                     and abs(p.results_actual.revenue_usd_b - 50.0) < 1.0),
            check_eq("gaap_eps", 5.94, p.results_actual.gaap_eps, 0.02),
            check_eq("gaap_net_income_m", 16500.0, p.results_actual.gaap_net_income_m, 200),
            check_eq("guidance_q_provided (banka çeyrek guide vermez)", False, p.guidance_next_quarter.provided),
            # JPM bazen NII outlook verir → guidance_full_year provided olabilir, bu OK
            check_eq("tone_score reasonable", True, -2 <= p.qualitative_signals.tone_score <= 5),
        ],
    },
    "lly_q1_2026": {
        "filing_date": "2026-04-30",
        "fiscal_period": "Q1 2026",
        "company_name": "Eli Lilly and Company",
        "ticker": "LLY",
        "checks": lambda p: [
            check_eq("revenue_usd_b", 19.799, p.results_actual.revenue_usd_b, 0.1),
            check_eq("yoy_revenue_growth_pct", 56.0, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("gaap_eps", 8.26, p.results_actual.gaap_eps, 0.02),
            check_eq("non_gaap_eps", 8.55, p.results_actual.non_gaap_eps, 0.02),
            # FULL YEAR GUIDANCE RAISED → provided=True KRITIK
            check_eq("guidance_fy_provided (LLY YILLIK guide verir)", True, p.guidance_full_year.provided),
            check_eq("guidance_fy_revenue_low_b", 82.0, p.guidance_full_year.revenue_low_b, 0.5),
            check_eq("guidance_fy_revenue_high_b", 85.0, p.guidance_full_year.revenue_high_b, 0.5),
            check_eq("guidance_fy_eps_low", 35.50, p.guidance_full_year.non_gaap_eps_low, 0.5),
            check_eq("guidance_fy_eps_high", 37.00, p.guidance_full_year.non_gaap_eps_high, 0.5),
            check_eq("IPR&D_one_time_flagged", True, len(p.one_time_items) >= 1),
            check_eq("tone_score (very_bullish guidance RAISE)", True, p.qualitative_signals.tone_score >= 3),
        ],
    },
    "amzn_q1_2026": {
        "filing_date": "2026-04-29",
        "fiscal_period": "Q1 2026",
        "company_name": "Amazon.com, Inc.",
        "ticker": "AMZN",
        "checks": lambda p: [
            check_eq("revenue_usd_b", 181.5, p.results_actual.revenue_usd_b, 0.5),
            check_eq("yoy_revenue_growth_pct", 17.0, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("gaap_eps", 2.78, p.results_actual.gaap_eps, 0.02),
            check_eq("gaap_net_income_m", 30300.0, p.results_actual.gaap_net_income_m, 200),
            check_eq("operating_income_m", 23900.0, p.results_actual.operating_income_m, 200),
            # AWS, NA, International segmentleri
            check_eq("segment_count", 3, len(p.segment_breakdown)),
            # Anthropic $16.8B pre-tax one-time (KRİTİK — R6 yeni eklendi)
            check_eq("anthropic_gains_one_time_flagged", True, len(p.one_time_items) >= 1),
            # AMZN guidance verir — Q2 revenue range
            check_eq("guidance_q_provided", True, p.guidance_next_quarter.provided),
            check_eq("tone_score (very_bullish AWS acc)", True, p.qualitative_signals.tone_score >= 3),
        ],
    },
    "meta_q1_2026": {
        "filing_date": "2026-04-29",
        "fiscal_period": "Q1 2026",
        "company_name": "Meta Platforms, Inc.",
        "ticker": "META",
        "checks": lambda p: [
            check_eq("revenue_usd_b", 56.311, p.results_actual.revenue_usd_b, 0.1),
            check_eq("yoy_revenue_growth_pct", 33.0, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("operating_margin_pct", 41.0, p.results_actual.operating_margin_pct, 1.0),
            check_eq("operating_income_m", 22872.0, p.results_actual.operating_income_m, 100),
            # META Q2 revenue guidance + FY capex guidance verir
            check_eq("guidance_q_or_fy_provided", True,
                     p.guidance_next_quarter.provided or p.guidance_full_year.provided),
            check_eq("tone_score (Superintelligence narrative)", True, p.qualitative_signals.tone_score >= 3),
        ],
    },
    "aaoi_q1_2026": {
        "filing_date": "2026-05-07",
        "fiscal_period": "Q1 2026",
        "company_name": "Applied Optoelectronics, Inc.",
        "ticker": "AAOI",
        "checks": lambda p: [
            # Mid-cap, zarar eden momentum hissesi senaryosu (AI optical)
            check_eq("revenue_usd_b (151.1M)", 0.1511, p.results_actual.revenue_usd_b, 0.005),
            check_eq("yoy_revenue_growth_pct (+51%)", 51.3, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("qoq_revenue_growth_pct (+12.5%)", 12.5, p.results_actual.qoq_revenue_growth_pct, 1.0),
            check_eq("gaap_eps (zararda)", -0.19, p.results_actual.gaap_eps, 0.02),
            check_eq("non_gaap_eps (zararda)", -0.07, p.results_actual.non_gaap_eps, 0.02),
            check_eq("gross_margin_pct", 29.2, p.results_actual.gross_margin_pct, 0.5),
            check_eq("diluted_share_count_m (76M)", 75.98, p.results_actual.diluted_share_count_m, 1.0),
            check_eq("guidance_q_provided", True, p.guidance_next_quarter.provided),
            check_eq("guidance_q_revenue_mid_b (189M)", 0.189, p.guidance_next_quarter.revenue_mid_b, 0.01),
            check_eq("guidance_q_gross_margin (29.5%)", 29.5, p.guidance_next_quarter.gross_margin_mid_pct, 0.5),
            check_eq("guidance_fy_provided (yok)", False, p.guidance_full_year.provided),
            check_eq("segment_count_min_3", True, len(p.segment_breakdown) >= 3),
            check_eq("datacenter_segment_var",  True,
                     any("datacenter" in s.segment_name.lower() or "data center" in s.segment_name.lower()
                         for s in p.segment_breakdown)),
            check_eq("one_time_items_min_2", True, len(p.one_time_items) >= 2),
            check_eq("tone_score_bullish", True, p.qualitative_signals.tone_score >= 2),
        ],
    },
    "mu_q2_fy26": {
        "filing_date": "2026-03-18",
        "fiscal_period": "Q2 FY2026",
        "company_name": "Micron Technology, Inc.",
        "ticker": "MU",
        "checks": lambda p: [
            # Memory cycle peak + AI memory boom senaryosu
            check_eq("revenue_usd_b ($23.86B)", 23.86, p.results_actual.revenue_usd_b, 0.05),
            check_eq("yoy_revenue_growth (~+196%)", 196.4, p.results_actual.yoy_revenue_growth_pct, 1.0),
            check_eq("qoq_revenue_growth (~+75%)", 74.9, p.results_actual.qoq_revenue_growth_pct, 1.0),
            check_eq("gaap_eps ($12.07)", 12.07, p.results_actual.gaap_eps, 0.02),
            check_eq("non_gaap_eps ($12.20)", 12.20, p.results_actual.non_gaap_eps, 0.02),
            check_eq("gaap_net_income_m ($13,790M)", 13790.0, p.results_actual.gaap_net_income_m, 50),
            check_eq("gross_margin_pct", 74.9, p.results_actual.gross_margin_pct, 1.0),
            check_eq("guidance_q_provided (Q3 FY26)", True, p.guidance_next_quarter.provided),
            # Q3 guidance: revenue $32.75-34.25B (mid $33.5B), EPS $18.75-19.55
            check_eq("guidance_q_revenue_mid_b ($33.5B)", 33.5, p.guidance_next_quarter.revenue_mid_b, 0.5),
            check_eq("guidance_q_revenue_low_b", 32.75, p.guidance_next_quarter.revenue_low_b, 0.5),
            check_eq("guidance_q_revenue_high_b", 34.25, p.guidance_next_quarter.revenue_high_b, 0.5),
            check_eq("guidance_q_eps_mid ($19.15)", 19.15, p.guidance_next_quarter.non_gaap_eps_mid, 0.2),
            check_eq("guidance_q_gross_margin (81%)", 81.0, p.guidance_next_quarter.gross_margin_mid_pct, 1.0),
            # Segment breakdown
            check_eq("segment_count (4: Cloud/Core DC/Mobile/Auto)", 4, len(p.segment_breakdown)),
            # Tone
            check_eq("tone_score_very_bullish (5)", True, p.qualitative_signals.tone_score >= 4),
        ],
    },
}


def run_fixture(parser: KimiEarningsParser, fixture_name: str) -> FixtureResult:
    """Tek bir fixture'ı çalıştır ve check'leri uygula."""
    fixture_dir = FIXTURES_DIR / fixture_name
    pr_path = fixture_dir / "press_release.txt"

    if not pr_path.exists():
        return FixtureResult(
            fixture_name=fixture_name,
            parse_success=False,
            duration_sec=0.0,
            cost_usd=0.0,
            error=f"Fixture dosyası yok: {pr_path}",
        )

    spec = FIXTURE_CHECKS.get(fixture_name)
    if not spec:
        return FixtureResult(
            fixture_name=fixture_name,
            parse_success=False,
            duration_sec=0.0,
            cost_usd=0.0,
            error=f"FIXTURE_CHECKS'te tanım yok: {fixture_name}",
        )

    with open(pr_path) as f:
        doc_text = f.read()

    t0 = time.time()
    result = parser.parse_8k(
        ticker=spec["ticker"],
        company_name=spec["company_name"],
        filing_date=spec["filing_date"],
        fiscal_period=spec["fiscal_period"],
        document_text=doc_text,
    )
    elapsed = time.time() - t0

    if not result.success:
        return FixtureResult(
            fixture_name=fixture_name,
            parse_success=False,
            duration_sec=elapsed,
            cost_usd=result.cost_usd,
            error=result.error,
        )

    parsed = result.parsed
    checks = spec["checks"](parsed)

    return FixtureResult(
        fixture_name=fixture_name,
        parse_success=True,
        duration_sec=elapsed,
        cost_usd=result.cost_usd,
        checks=checks,
    )


def print_fixture_result(fr: FixtureResult):
    status = "✅" if fr.parse_success else "❌"
    print(f"\n{status} {fr.fixture_name}")
    print(f"   Süre: {fr.duration_sec:.1f}s | Maliyet: ${fr.cost_usd:.4f}")

    if not fr.parse_success:
        print(f"   HATA: {fr.error}")
        return

    print(f"   Accuracy: {fr.pass_count}/{fr.total_count} ({fr.accuracy_pct:.0f}%)")
    failed = [c for c in fr.checks if not c.passed]
    if failed:
        print(f"   Başarısız check'ler:")
        for c in failed:
            tol_str = f" (±{c.tolerance})" if c.tolerance else ""
            print(f"     ❌ {c.name}{tol_str}: expected={c.expected}, actual={c.actual}")


def run_all_fixtures(fixtures: Optional[list[str]] = None) -> dict:
    """Tüm fixture'ları çalıştır ve özet rapor üret."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY environment variable yok.")
        sys.exit(1)

    fixtures = fixtures or list(FIXTURE_CHECKS.keys())
    parser = KimiEarningsParser(api_key=api_key)

    print("=" * 70)
    print(f"EARNINGS NIGHT TEST SUITE — {len(fixtures)} fixture")
    print("=" * 70)

    results = []
    total_cost = 0.0
    total_time = 0.0
    total_checks_passed = 0
    total_checks = 0

    for fname in fixtures:
        print(f"\n▶ {fname} çalışıyor...")
        fr = run_fixture(parser, fname)
        results.append(fr)
        print_fixture_result(fr)
        total_cost += fr.cost_usd
        total_time += fr.duration_sec
        total_checks_passed += fr.pass_count
        total_checks += fr.total_count

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Toplam fixture: {len(results)}")
    print(f"Parse başarılı: {sum(1 for r in results if r.parse_success)}/{len(results)}")
    print(f"Toplam check: {total_checks_passed}/{total_checks} ({total_checks_passed/total_checks*100 if total_checks else 0:.1f}%)")
    print(f"Toplam süre: {total_time:.1f}s")
    print(f"Toplam maliyet: ${total_cost:.4f}")

    return {
        "results": results,
        "total_cost_usd": round(total_cost, 4),
        "total_time_sec": round(total_time, 1),
        "overall_accuracy_pct": round(total_checks_passed / total_checks * 100, 1) if total_checks else 0,
    }


if __name__ == "__main__":
    fixtures = sys.argv[1:] if len(sys.argv) > 1 else None
    summary = run_all_fixtures(fixtures)
    if summary["overall_accuracy_pct"] < 90:
        sys.exit(1)
