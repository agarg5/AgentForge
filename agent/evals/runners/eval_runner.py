"""Eval runner — executes test cases against the agent and reports results.

Usage:
    # Run all evals against a live agent
    python -m evals.runners.eval_runner --base-url http://localhost:8000 --token <auth_token>

    # Run a specific category
    python -m evals.runners.eval_runner --base-url http://localhost:8000 --token <token> --category market_data

    # Dry run (validate dataset only)
    python -m evals.runners.eval_runner --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from ..checks.assertions import CHECKS, EvalResult, check_expected_patterns


DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"


@dataclass
class CaseResult:
    case_id: str
    category: str
    description: str
    passed: bool
    checks_passed: int
    checks_total: int
    check_details: list[dict] = field(default_factory=list)
    latency_ms: float = 0
    tools_called: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class EvalReport:
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    results: list[CaseResult] = field(default_factory=list)
    total_latency_ms: float = 0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0

    @property
    def avg_latency_ms(self) -> float:
        successful = [r for r in self.results if not r.error]
        return sum(r.latency_ms for r in successful) / len(successful) if successful else 0

    def summary(self) -> dict:
        by_category: dict[str, dict] = {}
        for r in self.results:
            cat = by_category.setdefault(r.category, {"total": 0, "passed": 0, "failed": 0})
            cat["total"] += 1
            if r.passed:
                cat["passed"] += 1
            else:
                cat["failed"] += 1

        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "pass_rate": f"{self.pass_rate:.1%}",
            "avg_latency_ms": round(self.avg_latency_ms),
            "by_category": by_category,
        }


def load_cases(category: str | None = None) -> list[dict]:
    """Load test cases from JSON dataset files."""
    cases = []
    for path in sorted(DATASETS_DIR.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            cases.extend(data)
        else:
            cases.append(data)

    if category:
        cases = [c for c in cases if c.get("category") == category]

    return cases


async def run_single_case(
    client: httpx.AsyncClient,
    base_url: str,
    auth_token: str,
    case: dict,
) -> CaseResult:
    """Execute a single eval case against the agent API."""
    case_id = case["id"]
    category = case.get("category", "unknown")
    description = case.get("description", "")
    expected_tools = case.get("expected_tools", [])
    checks = case.get("checks", [])
    expected_patterns = case.get("expected_patterns", [])
    user_input = case.get("input", "")

    # Handle empty input edge case
    if not user_input and "handles_empty_input" not in checks:
        return CaseResult(
            case_id=case_id,
            category=category,
            description=description,
            passed=True,
            checks_passed=0,
            checks_total=0,
        )

    start = time.monotonic()
    try:
        resp = await client.post(
            f"{base_url}/chat",
            json={"message": user_input},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        if resp.status_code != 200:
            return CaseResult(
                case_id=case_id,
                category=category,
                description=description,
                passed=False,
                checks_passed=0,
                checks_total=len(checks),
                latency_ms=elapsed_ms,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        data = resp.json()
        output = data.get("content", "")
        metrics = data.get("metrics", {})
        tools_called = metrics.get("tools_used", [])

    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000

        # For empty input, an error is expected
        if not user_input:
            eval_result = EvalResult(
                input=user_input,
                output="",
                tools_called=[],
                expected_tools=expected_tools,
                tool_outputs=[],
                error=str(e),
            )
            check_results = _run_checks(eval_result, checks, expected_patterns)
            passed_count = sum(1 for c in check_results if c["passed"])
            return CaseResult(
                case_id=case_id,
                category=category,
                description=description,
                passed=passed_count == len(check_results),
                checks_passed=passed_count,
                checks_total=len(check_results),
                check_details=check_results,
                latency_ms=elapsed_ms,
                error=str(e),
            )

        return CaseResult(
            case_id=case_id,
            category=category,
            description=description,
            passed=False,
            checks_passed=0,
            checks_total=len(checks),
            latency_ms=elapsed_ms,
            error=str(e),
        )

    # Build EvalResult for assertion checks
    eval_result = EvalResult(
        input=user_input,
        output=output,
        tools_called=tools_called,
        expected_tools=expected_tools,
        tool_outputs=[],  # We don't have raw tool outputs from the API
    )

    check_results = _run_checks(eval_result, checks, expected_patterns)
    passed_count = sum(1 for c in check_results if c["passed"])

    return CaseResult(
        case_id=case_id,
        category=category,
        description=description,
        passed=passed_count == len(check_results),
        checks_passed=passed_count,
        checks_total=len(check_results),
        check_details=check_results,
        latency_ms=elapsed_ms,
        tools_called=tools_called,
    )


def _run_checks(
    eval_result: EvalResult,
    checks: list[str],
    expected_patterns: list[str],
) -> list[dict]:
    """Run all specified checks on an eval result."""
    results = []

    for check_name in checks:
        check_fn = CHECKS.get(check_name)
        if not check_fn:
            results.append({
                "check": check_name,
                "passed": False,
                "reason": f"Unknown check: {check_name}",
            })
            continue

        try:
            passed, reason = check_fn(eval_result)
            results.append({
                "check": check_name,
                "passed": passed,
                "reason": reason,
            })
        except Exception as e:
            results.append({
                "check": check_name,
                "passed": False,
                "reason": f"Check error: {e}",
            })

    # Also check expected patterns if any
    if expected_patterns:
        passed, reason = check_expected_patterns(eval_result, expected_patterns)
        results.append({
            "check": "expected_patterns",
            "passed": passed,
            "reason": reason,
        })

    return results


async def run_eval(
    base_url: str,
    auth_token: str,
    category: str | None = None,
    concurrency: int = 3,
) -> EvalReport:
    """Run the full evaluation suite."""
    cases = load_cases(category)
    report = EvalReport(total=len(cases))

    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:

        async def bounded_run(case: dict) -> CaseResult:
            async with semaphore:
                return await run_single_case(client, base_url, auth_token, case)

        tasks = [bounded_run(case) for case in cases]
        results = await asyncio.gather(*tasks)

    for result in results:
        report.results.append(result)
        report.total_latency_ms += result.latency_ms
        if result.error:
            report.errors += 1
        if result.passed:
            report.passed += 1
        else:
            report.failed += 1

    return report


def print_report(report: EvalReport) -> None:
    """Print a human-readable eval report."""
    print("\n" + "=" * 70)
    print("EVAL REPORT")
    print("=" * 70)

    summary = report.summary()
    print(f"\nTotal: {summary['total']}  |  "
          f"Passed: {summary['passed']}  |  "
          f"Failed: {summary['failed']}  |  "
          f"Errors: {summary['errors']}")
    print(f"Pass Rate: {summary['pass_rate']}  |  "
          f"Avg Latency: {summary['avg_latency_ms']}ms")

    print("\n--- By Category ---")
    for cat, stats in summary["by_category"].items():
        rate = stats["passed"] / stats["total"] if stats["total"] else 0
        status = "PASS" if rate >= 0.8 else "FAIL"
        print(f"  [{status}] {cat}: {stats['passed']}/{stats['total']} ({rate:.0%})")

    # Print failures
    failures = [r for r in report.results if not r.passed]
    if failures:
        print(f"\n--- Failed Cases ({len(failures)}) ---")
        for r in failures:
            print(f"\n  {r.case_id}: {r.description}")
            if r.error:
                print(f"    ERROR: {r.error}")
            for detail in r.check_details:
                if not detail["passed"]:
                    print(f"    FAIL [{detail['check']}]: {detail['reason']}")

    print("\n" + "=" * 70)


def validate_dataset() -> None:
    """Dry run: validate that dataset files are well-formed."""
    cases = load_cases()
    print(f"Loaded {len(cases)} test cases")

    categories = {}
    for case in cases:
        cat = case.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

        # Validate required fields
        assert "id" in case, f"Missing 'id' in case: {case}"
        assert "input" in case, f"Missing 'input' in case {case['id']}"
        assert "checks" in case, f"Missing 'checks' in case {case['id']}"

        # Validate check names
        for check in case.get("checks", []):
            assert check in CHECKS, f"Unknown check '{check}' in case {case['id']}"

    print(f"\nCategories:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print(f"\nAll {len(cases)} cases valid.")


def main():
    parser = argparse.ArgumentParser(description="Run AgentForge evals")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Agent API base URL")
    parser.add_argument("--token", help="Ghostfolio auth token")
    parser.add_argument("--category", help="Only run cases in this category")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent requests")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset only")
    parser.add_argument("--output", help="Write JSON report to file")
    args = parser.parse_args()

    if args.dry_run:
        validate_dataset()
        return

    if not args.token:
        print("Error: --token is required (Ghostfolio auth token)")
        sys.exit(1)

    report = asyncio.run(run_eval(
        base_url=args.base_url,
        auth_token=args.token,
        category=args.category,
        concurrency=args.concurrency,
    ))

    print_report(report)

    if args.output:
        output_data = {
            "summary": report.summary(),
            "results": [
                {
                    "case_id": r.case_id,
                    "category": r.category,
                    "description": r.description,
                    "passed": r.passed,
                    "checks_passed": r.checks_passed,
                    "checks_total": r.checks_total,
                    "check_details": r.check_details,
                    "latency_ms": round(r.latency_ms),
                    "tools_called": r.tools_called,
                    "error": r.error,
                }
                for r in report.results
            ],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nJSON report written to {args.output}")

    # Exit with non-zero if pass rate < 80%
    if report.pass_rate < 0.8:
        sys.exit(1)


if __name__ == "__main__":
    main()
