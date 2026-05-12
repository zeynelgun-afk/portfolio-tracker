"""
Cached Test Runner — Mevcut kimi_output.json'ları üzerinden checks çalıştırır.
Kimi çağrısı yapmaz, regression test için hızlı.

Kullanım:
    python -m agent.earnings_night.test_suite_cached
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.earnings_night.schemas import EarningsParse
from agent.earnings_night.test_suite import FIXTURE_CHECKS, FIXTURES_DIR, FixtureResult, print_fixture_result


def run_cached_fixture(fixture_name: str) -> FixtureResult:
    spec = FIXTURE_CHECKS.get(fixture_name)
    if not spec:
        return FixtureResult(fixture_name, False, 0.0, 0.0, error=f"CHECKS yok: {fixture_name}")

    json_path = FIXTURES_DIR / fixture_name / "kimi_output.json"
    if not json_path.exists():
        return FixtureResult(fixture_name, False, 0.0, 0.0, error=f"kimi_output.json yok: {json_path}")

    with open(json_path) as f:
        data = json.load(f)
    try:
        parsed = EarningsParse(**data)
    except Exception as e:
        return FixtureResult(fixture_name, False, 0.0, 0.0, error=f"Validation hatası: {e}")

    checks = spec["checks"](parsed)
    return FixtureResult(
        fixture_name=fixture_name,
        parse_success=True,
        duration_sec=0.0,
        cost_usd=0.0,
        checks=checks,
    )


def main():
    print("=" * 70)
    print("CACHED TEST SUITE — Kimi çağrısı yapmadan regression")
    print("=" * 70)

    fixtures = list(FIXTURE_CHECKS.keys())
    results = []
    total_passed = 0
    total = 0

    for fname in fixtures:
        fr = run_cached_fixture(fname)
        results.append(fr)
        print_fixture_result(fr)
        total_passed += fr.pass_count
        total += fr.total_count

    print("\n" + "=" * 70)
    print("CACHED SUMMARY")
    print("=" * 70)
    print(f"Fixture sayısı: {len(results)}")
    print(f"Toplam check: {total_passed}/{total} ({total_passed/total*100 if total else 0:.1f}%)")
    
    # Fixture başına kısa özet
    print("\nFixture başına accuracy:")
    for r in results:
        emoji = "✅" if r.accuracy_pct == 100 else "⚠️" if r.accuracy_pct >= 80 else "❌"
        print(f"  {emoji} {r.fixture_name}: {r.pass_count}/{r.total_count} ({r.accuracy_pct:.0f}%)")


if __name__ == "__main__":
    main()
