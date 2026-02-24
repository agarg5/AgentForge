"""Tests for eval dataset validation."""

import json
from pathlib import Path

import pytest

from evals.checks.assertions import CHECKS


DATASETS_DIR = Path(__file__).resolve().parent.parent / "evals" / "datasets"


def load_all_cases() -> list[dict]:
    cases = []
    for path in sorted(DATASETS_DIR.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            cases.extend(data)
        else:
            cases.append(data)
    return cases


@pytest.fixture
def all_cases():
    return load_all_cases()


class TestDatasetStructure:
    def test_has_at_least_50_cases(self, all_cases):
        assert len(all_cases) >= 50, f"Only {len(all_cases)} cases, need 50+"

    def test_all_cases_have_required_fields(self, all_cases):
        required = {"id", "category", "input", "checks"}
        for case in all_cases:
            missing = required - set(case.keys())
            assert not missing, f"Case {case.get('id', '?')} missing fields: {missing}"

    def test_all_ids_unique(self, all_cases):
        ids = [c["id"] for c in all_cases]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_all_checks_are_valid(self, all_cases):
        for case in all_cases:
            for check in case.get("checks", []):
                assert check in CHECKS, f"Unknown check '{check}' in case {case['id']}"

    def test_categories_have_multiple_cases(self, all_cases):
        categories = {}
        for case in all_cases:
            cat = case.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        for cat, count in categories.items():
            assert count >= 2, f"Category '{cat}' has only {count} case(s)"

    def test_expected_tools_are_strings(self, all_cases):
        for case in all_cases:
            tools = case.get("expected_tools", [])
            assert isinstance(tools, list), f"expected_tools not a list in {case['id']}"
            for t in tools:
                assert isinstance(t, str), f"Non-string tool in {case['id']}: {t}"

    def test_expected_patterns_are_strings(self, all_cases):
        for case in all_cases:
            patterns = case.get("expected_patterns", [])
            assert isinstance(patterns, list), f"expected_patterns not a list in {case['id']}"
            for p in patterns:
                assert isinstance(p, str), f"Non-string pattern in {case['id']}: {p}"


class TestDatasetCoverage:
    """Ensure the dataset covers key eval dimensions."""

    def test_covers_all_tools(self, all_cases):
        all_tools = set()
        for case in all_cases:
            all_tools.update(case.get("expected_tools", []))

        expected_tools = {
            "portfolio_analysis",
            "transaction_history",
            "market_data",
            "risk_assessment",
            "benchmark_comparison",
            "dividend_analysis",
            "account_summary",
        }
        missing = expected_tools - all_tools
        assert not missing, f"No test cases for tools: {missing}"

    def test_has_multi_tool_cases(self, all_cases):
        multi = [c for c in all_cases if c.get("category") == "multi_tool"]
        assert len(multi) >= 3, f"Only {len(multi)} multi-tool cases"

    def test_has_guardrail_cases(self, all_cases):
        guardrails = [c for c in all_cases if c.get("category") == "guardrails"]
        assert len(guardrails) >= 3, f"Only {len(guardrails)} guardrail cases"

    def test_has_hallucination_cases(self, all_cases):
        hallucination = [c for c in all_cases if c.get("category") == "hallucination"]
        assert len(hallucination) >= 3, f"Only {len(hallucination)} hallucination cases"

    def test_has_verification_cases(self, all_cases):
        verification = [c for c in all_cases if c.get("category") == "verification"]
        assert len(verification) >= 2, f"Only {len(verification)} verification cases"

    def test_has_format_cases(self, all_cases):
        formatting = [c for c in all_cases if c.get("category") == "format"]
        assert len(formatting) >= 2, f"Only {len(formatting)} format cases"

    def test_has_edge_cases(self, all_cases):
        edge = [c for c in all_cases if c.get("category") == "edge_cases"]
        assert len(edge) >= 2, f"Only {len(edge)} edge cases"
