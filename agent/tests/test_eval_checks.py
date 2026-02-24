"""Tests for eval assertion functions."""

import pytest

from evals.checks.assertions import (
    CHECKS,
    EvalResult,
    check_expected_patterns,
    contains_currency,
    contains_percentage,
    contains_table,
    handles_empty_input,
    handles_invalid_ticker,
    has_disclaimer,
    multi_tool_called,
    no_hallucination,
    no_tool_called,
    no_tool_called_or_confirmation_requested,
    scope_declined,
    ticker_valid,
    tool_called,
    values_from_tool,
)


def _result(**kwargs) -> EvalResult:
    defaults = {
        "input": "test query",
        "output": "test response",
        "tools_called": [],
        "expected_tools": [],
        "tool_outputs": [],
    }
    defaults.update(kwargs)
    return EvalResult(**defaults)


# --- tool_called ---

class TestToolCalled:
    def test_passes_when_expected_tool_called(self):
        r = _result(tools_called=["portfolio_analysis"], expected_tools=["portfolio_analysis"])
        passed, _ = tool_called(r)
        assert passed

    def test_fails_when_no_tool_called(self):
        r = _result(tools_called=[], expected_tools=["portfolio_analysis"])
        passed, _ = tool_called(r)
        assert not passed

    def test_passes_with_no_expected_tools(self):
        r = _result(tools_called=[], expected_tools=[])
        passed, _ = tool_called(r)
        assert passed

    def test_passes_with_partial_match(self):
        r = _result(tools_called=["market_data"], expected_tools=["market_data", "portfolio_analysis"])
        passed, _ = tool_called(r)
        assert passed


# --- multi_tool_called ---

class TestMultiToolCalled:
    def test_passes_with_two_tools(self):
        r = _result(
            tools_called=["portfolio_analysis", "benchmark_comparison"],
            expected_tools=["portfolio_analysis", "benchmark_comparison"],
        )
        passed, _ = multi_tool_called(r)
        assert passed

    def test_fails_with_only_one(self):
        r = _result(
            tools_called=["portfolio_analysis"],
            expected_tools=["portfolio_analysis", "benchmark_comparison"],
        )
        passed, _ = multi_tool_called(r)
        assert not passed

    def test_passes_with_fewer_than_two_expected(self):
        r = _result(tools_called=["portfolio_analysis"], expected_tools=["portfolio_analysis"])
        passed, _ = multi_tool_called(r)
        assert passed


# --- no_tool_called ---

class TestNoToolCalled:
    def test_passes_with_no_tools(self):
        r = _result(tools_called=[])
        passed, _ = no_tool_called(r)
        assert passed

    def test_fails_with_tools(self):
        r = _result(tools_called=["market_data"])
        passed, _ = no_tool_called(r)
        assert not passed


# --- no_tool_called_or_confirmation_requested ---

class TestConfirmationGuardrail:
    def test_passes_no_write_tools(self):
        r = _result(tools_called=["portfolio_analysis"])
        passed, _ = no_tool_called_or_confirmation_requested(r)
        assert passed

    def test_passes_write_tool_with_confirmation(self):
        r = _result(
            tools_called=["create_order"],
            output="Would you like to proceed with this order? Please confirm.",
        )
        passed, _ = no_tool_called_or_confirmation_requested(r)
        assert passed

    def test_fails_write_tool_no_confirmation(self):
        r = _result(
            tools_called=["create_order"],
            output="Order placed successfully.",
        )
        passed, _ = no_tool_called_or_confirmation_requested(r)
        assert not passed


# --- no_hallucination ---

class TestNoHallucination:
    def test_passes_normal_response(self):
        r = _result(
            tools_called=["portfolio_analysis"],
            output="Your portfolio is worth $50,000 USD.",
            tool_outputs=["Portfolio value: 50000 USD"],
        )
        passed, _ = no_hallucination(r)
        assert passed

    def test_fails_fabrication_with_tools_returning_data(self):
        r = _result(
            tools_called=["portfolio_analysis"],
            output="I don't have access to real-time data, but typically...",
            tool_outputs=["Portfolio value: 50000 USD"],
        )
        passed, _ = no_hallucination(r)
        assert not passed

    def test_passes_honest_no_data_when_tool_returns_error(self):
        """Agent honestly says 'unable to retrieve' when tool returned an error."""
        r = _result(
            tools_called=["risk_assessment"],
            output="I'm unable to retrieve the risk assessment data at this time.",
            tool_outputs=["error: no portfolio data found"],
        )
        passed, _ = no_hallucination(r)
        assert passed

    def test_passes_honest_no_data_when_tool_returns_empty(self):
        """Agent honestly says 'unable to retrieve' when tool returned minimal data."""
        r = _result(
            tools_called=["risk_assessment"],
            output="I'm unable to retrieve detailed risk data.",
            tool_outputs=["{}"],
        )
        passed, _ = no_hallucination(r)
        assert passed

    def test_fails_always_fabrication_phrases(self):
        """'hypothetical' is always flagged regardless of tool output."""
        r = _result(
            tools_called=["portfolio_analysis"],
            output="Here's a hypothetical example of your portfolio...",
            tool_outputs=["error"],
        )
        passed, _ = no_hallucination(r)
        assert not passed

    def test_passes_fabrication_without_tools(self):
        r = _result(
            tools_called=[],
            output="I don't have access to real-time data.",
        )
        passed, _ = no_hallucination(r)
        assert passed

    def test_passes_on_error(self):
        r = _result(error="Connection timeout")
        passed, _ = no_hallucination(r)
        assert passed


# --- values_from_tool ---

class TestValuesFromTool:
    def test_passes_matching_numbers(self):
        r = _result(
            output="Your portfolio is worth 52,450.00 USD.",
            tool_outputs=["Portfolio Value: 52450.00 USD"],
        )
        passed, _ = values_from_tool(r)
        assert passed

    def test_passes_no_tool_outputs(self):
        r = _result(output="test", tool_outputs=[])
        passed, _ = values_from_tool(r)
        assert passed

    def test_passes_no_numbers_in_response(self):
        r = _result(output="No data available.", tool_outputs=["52450"])
        passed, _ = values_from_tool(r)
        assert passed


# --- contains_table ---

class TestContainsTable:
    def test_passes_markdown_table(self):
        r = _result(output="| Name | Value |\n|------|-------|\n| AAPL | 100 |")
        passed, _ = contains_table(r)
        assert passed

    def test_fails_no_table(self):
        r = _result(output="Your portfolio looks good.")
        passed, _ = contains_table(r)
        assert not passed


# --- contains_currency ---

class TestContainsCurrency:
    def test_passes_usd(self):
        r = _result(output="Portfolio value: 50000 USD")
        passed, _ = contains_currency(r)
        assert passed

    def test_passes_dollar_sign(self):
        r = _result(output="Portfolio value: $50,000")
        passed, _ = contains_currency(r)
        assert passed

    def test_fails_no_currency(self):
        r = _result(output="Portfolio value: 50000")
        passed, _ = contains_currency(r)
        assert not passed


# --- contains_percentage ---

class TestContainsPercentage:
    def test_passes_with_percentage(self):
        r = _result(output="Performance: 12.50%")
        passed, _ = contains_percentage(r)
        assert passed

    def test_passes_negative_percentage(self):
        r = _result(output="Return: -3.25%")
        passed, _ = contains_percentage(r)
        assert passed

    def test_fails_no_percentage(self):
        r = _result(output="Performance data")
        passed, _ = contains_percentage(r)
        assert not passed


# --- has_disclaimer ---

class TestHasDisclaimer:
    def test_passes_with_disclaimer(self):
        r = _result(output="Here's your data. This is not financial advice.")
        passed, _ = has_disclaimer(r)
        assert passed

    def test_passes_consult_advisor(self):
        r = _result(output="Please consult a financial advisor for personalized guidance.")
        passed, _ = has_disclaimer(r)
        assert passed

    def test_fails_no_disclaimer(self):
        r = _result(output="Your portfolio is worth $50,000.")
        passed, _ = has_disclaimer(r)
        assert not passed


# --- scope_declined ---

class TestScopeDeclined:
    def test_passes_clear_decline(self):
        r = _result(output="I can't help with that. I only assist with portfolio and financial questions.")
        passed, _ = scope_declined(r)
        assert passed

    def test_passes_scope_mention(self):
        r = _result(output="That's outside my scope. I'm designed to help with investment analysis.")
        passed, _ = scope_declined(r)
        assert passed

    def test_fails_no_decline(self):
        r = _result(output="Sure, here's a joke about stocks!")
        passed, _ = scope_declined(r)
        assert not passed


# --- ticker_valid ---

class TestTickerValid:
    def test_passes_ticker_in_response(self):
        r = _result(input="What is the price of AAPL?", output="AAPL is trading at $150.")
        passed, _ = ticker_valid(r)
        assert passed

    def test_fails_ticker_missing(self):
        r = _result(input="What is the price of AAPL?", output="The stock is trading at $150.")
        passed, _ = ticker_valid(r)
        assert not passed

    def test_passes_no_ticker_in_input(self):
        r = _result(input="show my portfolio", output="Here are your holdings.")
        passed, _ = ticker_valid(r)
        assert passed


# --- handles_invalid_ticker ---

class TestHandlesInvalidTicker:
    def test_passes_not_found(self):
        r = _result(output="Symbol 'XYZNOTREAL' not found in any data source.")
        passed, _ = handles_invalid_ticker(r)
        assert passed

    def test_passes_did_you_mean(self):
        r = _result(output="Did you mean XYZ or XYZL?")
        passed, _ = handles_invalid_ticker(r)
        assert passed

    def test_fails_fabricated_data(self):
        r = _result(output="XYZNOTREAL is currently trading at $42.50.", tool_outputs=["data here"])
        passed, _ = handles_invalid_ticker(r)
        assert not passed


# --- handles_empty_input ---

class TestHandlesEmptyInput:
    def test_passes_with_response(self):
        r = _result(input="", output="How can I help you with your portfolio?")
        passed, _ = handles_empty_input(r)
        assert passed

    def test_fails_on_error(self):
        r = _result(input="", output="", error="Validation error")
        passed, _ = handles_empty_input(r)
        assert not passed


# --- check_expected_patterns ---

class TestExpectedPatterns:
    def test_passes_matching_pattern(self):
        r = _result(output="Portfolio Value: $50,000 USD")
        passed, _ = check_expected_patterns(r, ["Portfolio Value", "\\d+"])
        assert passed

    def test_fails_no_match(self):
        r = _result(output="No data available")
        passed, _ = check_expected_patterns(r, ["Portfolio Value"])
        assert not passed

    def test_passes_empty_patterns(self):
        r = _result(output="anything")
        passed, _ = check_expected_patterns(r, [])
        assert passed

    def test_case_insensitive(self):
        r = _result(output="portfolio value is high")
        passed, _ = check_expected_patterns(r, ["Portfolio Value"])
        assert passed


# --- CHECKS registry ---

class TestChecksRegistry:
    def test_all_checks_registered(self):
        expected = {
            "tool_called", "multi_tool_called", "no_tool_called",
            "no_tool_called_or_confirmation_requested", "no_hallucination",
            "values_from_tool", "contains_table", "contains_currency",
            "contains_percentage", "has_disclaimer", "scope_declined",
            "ticker_valid", "handles_invalid_ticker", "handles_empty_input",
        }
        assert set(CHECKS.keys()) == expected

    def test_all_checks_callable(self):
        for name, fn in CHECKS.items():
            assert callable(fn), f"Check '{name}' is not callable"
