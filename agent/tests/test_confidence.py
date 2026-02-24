"""Tests for confidence scoring verification."""

import pytest

from src.verification.confidence import score_confidence, LOW_CONFIDENCE_THRESHOLD


class TestScoreConfidence:
    def test_high_confidence_with_tools_and_data(self):
        """Multiple tools + concrete data = high confidence."""
        score, _ = score_confidence(
            "Your portfolio is worth $52,450.00 USD with a return of 12.34%.",
            ["portfolio_analysis", "benchmark_comparison"],
            ["Portfolio Value: $52,450.00", "Benchmark return: 10.20%"],
        )
        assert score >= 0.8

    def test_moderate_confidence_single_tool(self):
        """Single tool with data = moderate-to-high confidence."""
        score, _ = score_confidence(
            "Your portfolio is worth $52,450.00 USD.",
            ["portfolio_analysis"],
            ["Portfolio Value: $52,450.00"],
        )
        assert 0.6 <= score <= 0.9

    def test_low_confidence_no_tools(self):
        """No tools called = low confidence."""
        score, _ = score_confidence(
            "I think your portfolio might be doing well, but I'm not sure "
            "approximately what the returns could be. It generally depends "
            "on market conditions.",
            [],
            [],
        )
        assert score < LOW_CONFIDENCE_THRESHOLD

    def test_no_tools_but_short_factual(self):
        """No tools but no hedging = moderate confidence."""
        score, _ = score_confidence(
            "I can help you analyze your portfolio. What would you like to know?",
            [],
            [],
        )
        # Base 0.5 - 0.2 (no tools) = 0.3, but no hedging
        assert score >= 0.2

    def test_hedging_reduces_confidence(self):
        """Hedging language reduces confidence."""
        score_hedged, _ = score_confidence(
            "Your portfolio might be worth approximately $50,000, "
            "but I'm not sure. It could be different.",
            ["portfolio_analysis"],
            ["Portfolio Value: $50,000"],
        )
        score_direct, _ = score_confidence(
            "Your portfolio is worth $50,000.",
            ["portfolio_analysis"],
            ["Portfolio Value: $50,000"],
        )
        assert score_direct > score_hedged

    def test_tool_errors_reduce_confidence(self):
        """Tool errors reduce confidence."""
        score, _ = score_confidence(
            "I encountered an issue fetching your portfolio data.",
            ["portfolio_analysis"],
            ["Error fetching portfolio data: 500 Internal Server Error"],
        )
        score_ok, _ = score_confidence(
            "Your portfolio is worth $50,000.",
            ["portfolio_analysis"],
            ["Portfolio Value: $50,000"],
        )
        assert score_ok > score

    def test_multiple_tools_boost_confidence(self):
        """More data tools = higher confidence."""
        score_one, _ = score_confidence(
            "Your portfolio is worth $50,000 with 12.34% returns.",
            ["portfolio_analysis"],
            ["Portfolio Value: $50,000"],
        )
        score_three, _ = score_confidence(
            "Your portfolio is worth $50,000 with 12.34% returns.",
            ["portfolio_analysis", "benchmark_comparison", "dividend_analysis"],
            ["Value: $50,000", "Benchmark: 10%", "Dividends: $500"],
        )
        assert score_three > score_one

    def test_score_clamped_to_range(self):
        """Score is always between 0.0 and 1.0."""
        # Max everything positive
        score_high, _ = score_confidence(
            "Portfolio: $100,000.00 with 15.50% return and $2,500.00 dividends.",
            ["portfolio_analysis", "benchmark_comparison", "dividend_analysis",
             "risk_assessment", "account_summary"],
            ["Value: $100,000", "Return: 15.50%", "Dividends: $2,500"],
        )
        assert 0.0 <= score_high <= 1.0

        # Max everything negative
        score_low, _ = score_confidence(
            "I'm not sure, it might be approximately this, but it could be "
            "different. I'm not certain and it generally depends.",
            [],
            [],
        )
        assert 0.0 <= score_low <= 1.0

    def test_detail_includes_factors(self):
        """Detail string includes scoring factors."""
        _, detail = score_confidence(
            "Your portfolio is worth $50,000.",
            ["portfolio_analysis"],
            ["Portfolio Value: $50,000"],
        )
        assert "confidence=" in detail
        assert "data tools called" in detail

    def test_preference_tools_dont_boost(self):
        """Preference tools are not data tools and don't boost confidence."""
        score_pref, _ = score_confidence(
            "I've saved your preference for EUR display.",
            ["save_user_preference"],
            ["Preference saved"],
        )
        score_data, _ = score_confidence(
            "Your portfolio is worth $50,000.",
            ["portfolio_analysis"],
            ["Portfolio Value: $50,000"],
        )
        assert score_data > score_pref
