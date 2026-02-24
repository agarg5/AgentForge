#!/usr/bin/env python3
"""Golden set eval runner — tests agent responses against content-quality rubrics.

Each golden case checks:
  - expected_tools: correct tools were called
  - must_contain: all required keywords appear in the response (case-insensitive)
  - must_not_contain: none of the banned phrases appear in the response

Usage:
    python -m evals.test_golden --base-url https://agent-production-b7bc.up.railway.app --token <token>
    python -m evals.test_golden --base-url http://localhost:8000 --token <token>
    python -m evals.test_golden --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import yaml

from .checks.assertions import EvalResult, must_contain_all, must_not_contain_any

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "datasets" / "golden_set.yaml"


def load_golden_set() -> list[dict]:
    """Load golden set cases from YAML."""
    with open(GOLDEN_SET_PATH) as f:
        return yaml.safe_load(f)


def check_golden_case(case: dict, response: str, tools_used: list[str]) -> dict:
    """Evaluate a single golden case against the agent response."""
    case_id = case["id"]
    query = case["query"]
    expected_tools = case.get("expected_tools", [])
    mc = case.get("must_contain", [])
    mnc = case.get("must_not_contain", [])

    checks = []
    passed = True

    # Check: expected tools called
    if expected_tools:
        called = set(tools_used)
        expected = set(expected_tools)
        if called & expected:
            checks.append(("expected_tools", True, f"Called: {called & expected}"))
        else:
            checks.append(("expected_tools", False, f"Expected one of {expected}, got {called or 'none'}"))
            passed = False
    else:
        # Guardrail cases: no tools should be called
        if tools_used:
            checks.append(("no_tools", False, f"Expected no tools, got {tools_used}"))
            passed = False
        else:
            checks.append(("no_tools", True, "No tools called (as expected)"))

    # Check: must_contain
    if mc:
        eval_result = EvalResult(
            input=query, output=response, tools_called=tools_used,
            expected_tools=expected_tools, tool_outputs=[],
        )
        mc_passed, mc_reason = must_contain_all(eval_result, mc)
        checks.append(("must_contain", mc_passed, mc_reason))
        if not mc_passed:
            passed = False

    # Check: must_not_contain
    if mnc:
        eval_result = EvalResult(
            input=query, output=response, tools_called=tools_used,
            expected_tools=expected_tools, tool_outputs=[],
        )
        mnc_passed, mnc_reason = must_not_contain_any(eval_result, mnc)
        checks.append(("must_not_contain", mnc_passed, mnc_reason))
        if not mnc_passed:
            passed = False

    return {
        "case_id": case_id,
        "category": case.get("category", "unknown"),
        "query": query[:80] + ("..." if len(query) > 80 else ""),
        "passed": passed,
        "checks": [{"name": n, "passed": p, "reason": r} for n, p, r in checks],
        "response_preview": response[:300],
        "tools_used": tools_used,
    }


async def run_golden_tests(base_url: str, auth_token: str) -> list[dict]:
    """Run all golden set cases against the live agent."""
    cases = load_golden_set()
    results = []

    async with httpx.AsyncClient() as client:
        for case in cases:
            print(f"  Testing: {case['id']} — {case.get('category', '')}...", end=" ", flush=True)
            start = time.monotonic()

            try:
                resp = await client.post(
                    f"{base_url}/chat",
                    json={"message": case["query"]},
                    headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=45,
                )
                elapsed = time.monotonic() - start

                if resp.status_code != 200:
                    results.append({
                        "case_id": case["id"],
                        "category": case.get("category", "unknown"),
                        "passed": False,
                        "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                        "latency_s": round(elapsed, 2),
                    })
                    print(f"ERROR ({resp.status_code})")
                    continue

                data = resp.json()
                content = data.get("content", "")
                metrics = data.get("metrics", {})
                tools_used = metrics.get("tools_used", [])

                result = check_golden_case(case, content, tools_used)
                result["latency_s"] = round(elapsed, 2)
                results.append(result)

                status = "PASS" if result["passed"] else "FAIL"
                print(f"{status} ({elapsed:.1f}s)")

                if not result["passed"]:
                    for chk in result["checks"]:
                        if not chk["passed"]:
                            print(f"    FAIL [{chk['name']}]: {chk['reason']}")

            except Exception as e:
                elapsed = time.monotonic() - start
                results.append({
                    "case_id": case["id"],
                    "category": case.get("category", "unknown"),
                    "passed": False,
                    "error": str(e),
                    "latency_s": round(elapsed, 2),
                })
                print(f"ERROR ({e})")

            # Small delay to avoid rate limiting
            await asyncio.sleep(1)

    return results


def print_summary(results: list[dict]) -> None:
    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    failed = total - passed_count

    print("\n" + "=" * 70)
    print("GOLDEN SET EVAL REPORT")
    print("=" * 70)
    print(f"\nTotal: {total}  |  Passed: {passed_count}  |  Failed: {failed}")
    print(f"Pass Rate: {passed_count/total:.0%}" if total else "No tests run")

    # By category
    categories: dict[str, dict] = {}
    for r in results:
        cat = r.get("category", "unknown")
        stats = categories.setdefault(cat, {"total": 0, "passed": 0})
        stats["total"] += 1
        if r.get("passed"):
            stats["passed"] += 1

    print("\n--- By Category ---")
    for cat, stats in sorted(categories.items()):
        rate = stats["passed"] / stats["total"] if stats["total"] else 0
        status = "PASS" if rate >= 0.8 else "FAIL"
        print(f"  [{status}] {cat}: {stats['passed']}/{stats['total']} ({rate:.0%})")

    if failed:
        print(f"\n--- Failed Cases ({failed}) ---")
        for r in results:
            if not r.get("passed"):
                print(f"\n  {r['case_id']}: {r.get('category', '')}")
                if r.get("error"):
                    print(f"    ERROR: {r['error']}")
                for chk in r.get("checks", []):
                    if not chk["passed"]:
                        print(f"    FAIL [{chk['name']}]: {chk['reason']}")
                if r.get("response_preview"):
                    print(f"    Response: {r['response_preview'][:150]}...")

    print("\n" + "=" * 70)


def validate_golden_set() -> None:
    """Dry run: validate that the golden set YAML is well-formed."""
    cases = load_golden_set()
    print(f"Loaded {len(cases)} golden set cases")

    categories: dict[str, int] = {}
    for case in cases:
        cat = case.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

        assert "id" in case, f"Missing 'id' in case: {case}"
        assert "query" in case, f"Missing 'query' in case {case['id']}"
        assert "expected_tools" in case, f"Missing 'expected_tools' in case {case['id']}"
        assert isinstance(case.get("must_contain", []), list), f"must_contain must be a list in {case['id']}"
        assert isinstance(case.get("must_not_contain", []), list), f"must_not_contain must be a list in {case['id']}"

    print(f"\nCategories:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print(f"\nAll {len(cases)} golden cases valid.")


def main():
    parser = argparse.ArgumentParser(description="Run golden set evals")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Agent API base URL")
    parser.add_argument("--token", help="Ghostfolio auth token")
    parser.add_argument("--output", help="Write JSON results to file")
    parser.add_argument("--dry-run", action="store_true", help="Validate golden set only")
    args = parser.parse_args()

    if args.dry_run:
        validate_golden_set()
        return

    if not args.token:
        print("Error: --token is required (Ghostfolio auth token)")
        sys.exit(1)

    print(f"Running golden set evals against {args.base_url}")
    print(f"Dataset: {GOLDEN_SET_PATH}\n")

    results = asyncio.run(run_golden_tests(args.base_url, args.token))
    print_summary(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nJSON results written to {args.output}")

    failed = sum(1 for r in results if not r.get("passed"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
