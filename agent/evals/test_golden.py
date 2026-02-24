#!/usr/bin/env python3
"""Golden set eval runner — tests agent with must_contain / must_not_contain rubrics.

Usage:
    python -m evals.test_golden --base-url https://agent-production-b7bc.up.railway.app --token <token>
    python -m evals.test_golden --base-url http://localhost:8000 --token <token>
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

from .checks.assertions import (
    must_contain_all,
    must_not_contain_any,
    EvalResult,
)

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "datasets" / "golden_set.yaml"


def load_golden_set() -> list[dict]:
    with open(GOLDEN_SET_PATH) as f:
        return yaml.safe_load(f)


def check_case(case: dict, response: str, metrics: dict) -> dict:
    """Evaluate a single golden set case."""
    tools_used = metrics.get("tools_used", [])
    expected_tools = case.get("expected_tools", [])

    eval_result = EvalResult(
        input=case["query"],
        output=response,
        tools_called=tools_used,
        expected_tools=expected_tools,
        tool_outputs=[],
    )

    checks = []
    passed = True

    # Check: expected tools called
    if expected_tools:
        called = set(tools_used)
        expected = set(expected_tools)
        if len(expected_tools) >= 2:
            matched = called & expected
            ok = len(matched) >= 2
            reason = f"Called {matched}" if ok else f"Expected >=2 of {expected}, got {matched or 'none'}"
        else:
            ok = bool(called & expected)
            reason = f"Called {called & expected}" if ok else f"Expected {expected}, got {called or 'none'}"
        checks.append({"name": "expected_tools", "passed": ok, "reason": reason})
        if not ok:
            passed = False
    else:
        # Guardrail cases: no tools should be called
        ok = len(tools_used) == 0
        reason = "No tools called" if ok else f"Unexpected tools called: {tools_used}"
        checks.append({"name": "no_tools_expected", "passed": ok, "reason": reason})
        if not ok:
            passed = False

    # Check: must_contain
    mc = case.get("must_contain", [])
    if mc:
        ok, reason = must_contain_all(eval_result, mc)
        checks.append({"name": "must_contain", "passed": ok, "reason": reason})
        if not ok:
            passed = False

    # Check: must_not_contain
    mnc = case.get("must_not_contain", [])
    if mnc:
        ok, reason = must_not_contain_any(eval_result, mnc)
        checks.append({"name": "must_not_contain", "passed": ok, "reason": reason})
        if not ok:
            passed = False

    return {
        "case_id": case["id"],
        "category": case["category"],
        "query": case["query"][:80] + ("..." if len(case["query"]) > 80 else ""),
        "passed": passed,
        "checks": checks,
        "tools_used": tools_used,
        "response_preview": response[:300],
        "expected_behavior": case.get("expected_behavior", "").strip(),
    }


async def run_golden_eval(base_url: str, auth_token: str) -> list[dict]:
    cases = load_golden_set()
    results = []

    async with httpx.AsyncClient() as client:
        for case in cases:
            label = f"{case['id']} — {case['category']}"
            print(f"  {label}...", end=" ", flush=True)
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
                        "category": case["category"],
                        "passed": False,
                        "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                        "latency_s": round(elapsed, 2),
                    })
                    print(f"ERROR ({resp.status_code})")
                    continue

                data = resp.json()
                content = data.get("content", "")
                metrics = data.get("metrics", {})

                result = check_case(case, content, metrics)
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
                    "category": case["category"],
                    "passed": False,
                    "error": str(e),
                    "latency_s": round(elapsed, 2),
                })
                print(f"ERROR ({e})")

            await asyncio.sleep(1)

    return results


def print_summary(results: list[dict]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    failed = total - passed

    print("\n" + "=" * 70)
    print("GOLDEN SET EVAL REPORT")
    print("=" * 70)
    print(f"\nTotal: {total}  |  Passed: {passed}  |  Failed: {failed}")
    print(f"Pass Rate: {passed/total:.0%}" if total else "No tests run")

    # By category
    categories: dict[str, dict] = {}
    for r in results:
        cat = categories.setdefault(r.get("category", "unknown"), {"total": 0, "passed": 0})
        cat["total"] += 1
        if r.get("passed"):
            cat["passed"] += 1

    print("\n--- By Category ---")
    for cat, stats in sorted(categories.items()):
        rate = stats["passed"] / stats["total"] if stats["total"] else 0
        icon = "PASS" if rate >= 0.8 else "FAIL"
        print(f"  [{icon}] {cat}: {stats['passed']}/{stats['total']} ({rate:.0%})")

    if failed:
        print(f"\n--- Failed Cases ({failed}) ---")
        for r in results:
            if not r.get("passed"):
                print(f"\n  {r['case_id']}")
                if r.get("error"):
                    print(f"    ERROR: {r['error']}")
                for chk in r.get("checks", []):
                    if not chk["passed"]:
                        print(f"    FAIL [{chk['name']}]: {chk['reason']}")
                if r.get("response_preview"):
                    print(f"    Response: {r['response_preview'][:150]}...")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Run golden set evals")
    parser.add_argument("--base-url", required=True, help="Agent API base URL")
    parser.add_argument("--token", required=True, help="Ghostfolio auth token")
    parser.add_argument("--output", help="Write JSON results to file")
    args = parser.parse_args()

    print(f"Running golden set evals against {args.base_url}")
    print(f"Dataset: {GOLDEN_SET_PATH}\n")

    results = asyncio.run(run_golden_eval(args.base_url, args.token))
    print_summary(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nJSON results written to {args.output}")

    failed = sum(1 for r in results if not r.get("passed"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
