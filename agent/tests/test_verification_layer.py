"""Tests for the verification layer (disclaimer, numeric consistency, and integration)."""

import pytest

from src.verification.disclaimer import check_disclaimer
from src.verification.numeric import check_numeric_consistency, _extract_numbers
from src.verification.layer import verify_response


# === Disclaimer checks ===


class TestCheckDisclaimer:
    def test_passes_with_disclaimer(self):
        passed, _ = check_disclaimer(
            "Your portfolio is worth $50,000. This is not financial advice.",
            ["portfolio_analysis"],
        )
        assert passed

    def test_passes_with_consult_advisor(self):
        passed, _ = check_disclaimer(
            "Please consult a financial advisor for guidance.",
            ["risk_assessment"],
        )
        assert passed

    def test_fails_missing_disclaimer(self):
        passed, detail = check_disclaimer(
            "Your portfolio is worth $50,000.",
            ["portfolio_analysis"],
        )
        assert not passed
        assert "disclaimer" in detail.lower()

    def test_passes_non_financial_tool(self):
        passed, _ = check_disclaimer(
            "Here are your transactions.",
            ["transaction_history"],
        )
        assert passed

    def test_passes_no_tools(self):
        passed, _ = check_disclaimer(
            "I can help you with portfolio questions.",
            [],
        )
        assert passed

    def test_passes_market_data_without_disclaimer(self):
        passed, _ = check_disclaimer(
            "AAPL is trading at $150.",
            ["market_data"],
        )
        assert passed

    def test_fails_benchmark_without_disclaimer(self):
        passed, _ = check_disclaimer(
            "Your portfolio returned 12% vs 10% for the S&P 500.",
            ["benchmark_comparison"],
        )
        assert not passed

    def test_fails_dividend_without_disclaimer(self):
        passed, _ = check_disclaimer(
            "You earned $500 in dividends this year.",
            ["dividend_analysis"],
        )
        assert not passed


# === Numeric consistency checks ===


class TestExtractNumbers:
    def test_extracts_integers(self):
        nums = _extract_numbers("Portfolio value: 52450 USD")
        assert "52450" in nums

    def test_extracts_decimals(self):
        nums = _extract_numbers("Return: 12.50%")
        assert "12.50" in nums

    def test_extracts_with_commas(self):
        nums = _extract_numbers("Value: 52,450.00")
        assert "52450.00" in nums

    def test_skips_single_digit(self):
        nums = _extract_numbers("Top 5 holdings: AAPL at 150")
        assert "5" not in nums
        assert "150" in nums

    def test_extracts_negative(self):
        nums = _extract_numbers("Loss: -3500")
        assert "-3500" in nums


class TestCheckNumericConsistency:
    def test_passes_matching_numbers(self):
        passed, _ = check_numeric_consistency(
            "Your portfolio is worth 52450.00 USD.",
            ["Portfolio Value: 52450.00 USD"],
        )
        assert passed

    def test_passes_no_tool_outputs(self):
        passed, _ = check_numeric_consistency(
            "Your portfolio is worth 52450 USD.",
            [],
        )
        assert passed

    def test_passes_no_numbers_in_response(self):
        passed, _ = check_numeric_consistency(
            "Your portfolio looks good.",
            ["Value: 52450"],
        )
        assert passed

    def test_passes_few_unmatched(self):
        # Only 1 unmatched out of 3 — below threshold
        passed, _ = check_numeric_consistency(
            "Portfolio: 52450, Return: 12.5%, Fee: 25",
            ["52450 USD, 12.5%"],
        )
        assert passed

    def test_fails_many_unmatched(self):
        # All numbers fabricated
        passed, detail = check_numeric_consistency(
            "Your portfolio is worth 99999 USD with 88888 in gains and 77777 in dividends.",
            ["Portfolio Value: 52450 USD"],
        )
        assert not passed
        assert "hallucination" in detail.lower()

    def test_passes_formatted_vs_raw(self):
        passed, _ = check_numeric_consistency(
            "Value: 52,450.00",
            ["value: 52450"],
        )
        assert passed


# === Verify response integration ===


class TestVerifyResponse:
    def test_appends_disclaimer_when_missing(self):
        result = verify_response(
            response="Your portfolio is worth $50,000.",
            tools_used=["portfolio_analysis"],
        )
        assert result["amended"]
        assert "informational purposes" in result["response"]
        disclaimer_check = next(c for c in result["checks"] if c["name"] == "disclaimer")
        assert not disclaimer_check["passed"]

    def test_does_not_amend_when_disclaimer_present(self):
        result = verify_response(
            response="Your portfolio is worth $50,000. This is not financial advice.",
            tools_used=["portfolio_analysis"],
        )
        assert not result["amended"]
        disclaimer_check = next(c for c in result["checks"] if c["name"] == "disclaimer")
        assert disclaimer_check["passed"]

    def test_includes_all_four_checks(self):
        result = verify_response(
            response="test",
            tools_used=[],
        )
        check_names = [c["name"] for c in result["checks"]]
        assert "scope" in check_names
        assert "disclaimer" in check_names
        assert "numeric_consistency" in check_names
        assert "ticker_verification" in check_names

    def test_ticker_always_passes(self):
        result = verify_response(
            response="test",
            tools_used=[],
        )
        ticker_check = next(c for c in result["checks"] if c["name"] == "ticker_verification")
        assert ticker_check["passed"]

    def test_numeric_consistency_check_runs(self):
        result = verify_response(
            response="Value: 99999 with 88888 in gains and 77777 in bonds.",
            tools_used=["portfolio_analysis"],
            tool_outputs=["Portfolio Value: 52450 USD"],
        )
        numeric_check = next(c for c in result["checks"] if c["name"] == "numeric_consistency")
        assert not numeric_check["passed"]

    def test_passes_all_checks(self):
        result = verify_response(
            response="Your portfolio is worth 52450 USD. This is not financial advice.",
            tools_used=["portfolio_analysis"],
            tool_outputs=["Portfolio Value: 52450 USD"],
        )
        assert not result["amended"]
        assert all(c["passed"] for c in result["checks"])

    def test_scope_check_runs(self):
        result = verify_response(
            response="Your portfolio holdings show a balanced allocation across stocks and bonds.",
            tools_used=["portfolio_analysis"],
        )
        scope_check = next(c for c in result["checks"] if c["name"] == "scope")
        assert scope_check["passed"]
