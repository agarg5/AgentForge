"""Tests for confidence scoring verification."""

import pytest

from src.verification.confidence import (
    score_confidence,
    LOW_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_CAVEAT,
)


class TestScoreConfidence:
    # --- High / moderate confidence (Ghostfolio tools) ---

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

    # --- Conversational responses (no tools) ---

    def test_conversational_response_no_penalty(self):
        """Simple conversational responses should not get low confidence."""
        score, _ = score_confidence(
            "Hello! I'm your financial assistant. How can I help you today?",
            [],
            [],
        )
        assert score >= LOW_CONFIDENCE_THRESHOLD

    def test_greeting_no_low_confidence(self):
        """Greetings like 'hi' should never show the low-confidence caveat."""
        for greeting in ["Hi!", "Hello", "Hey, how are you?", "Good morning!"]:
            score, _ = score_confidence(greeting, [], [])
            assert score >= LOW_CONFIDENCE_THRESHOLD, (
                f"Greeting '{greeting}' got score {score}, expected >= {LOW_CONFIDENCE_THRESHOLD}"
            )

    def test_no_tools_no_penalty(self):
        """No tools called = base confidence (no penalty)."""
        score, _ = score_confidence(
            "I can help you analyze your portfolio. What would you like to know?",
            [],
            [],
        )
        assert score >= LOW_CONFIDENCE_THRESHOLD

    # --- Hedging language ---

    def test_hedging_reduces_confidence(self):
        """Hedging language reduces confidence but stays above threshold."""
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
        # Even with hedging, Ghostfolio-backed response stays above threshold
        assert score_hedged >= LOW_CONFIDENCE_THRESHOLD

    def test_hedging_without_external_tools_never_triggers_caveat(self):
        """Heavy hedging without external tools cannot drop below threshold."""
        score, _ = score_confidence(
            "I'm not sure, it might be approximately this, but it could be "
            "different. I'm not certain and it generally depends.",
            [],
            [],
        )
        assert score >= LOW_CONFIDENCE_THRESHOLD

    # --- market_news with errors (the ONLY path to the caveat) ---

    def test_market_news_with_errors_triggers_caveat(self):
        """market_news tool with error outputs should drop below threshold."""
        score, detail = score_confidence(
            "Here is the latest market news for today.",
            ["market_news"],
            ["Error: AlphaVantage API rate limit exceeded"],
        )
        assert score < LOW_CONFIDENCE_THRESHOLD
        assert "external tool data issues" in detail

    def test_market_news_with_rate_limit_triggers_caveat(self):
        """market_news with rate-limiting output drops below threshold."""
        score, _ = score_confidence(
            "I found some market news but data may be incomplete.",
            ["market_news"],
            ["Rate limit reached. Only partial results returned."],
        )
        assert score < LOW_CONFIDENCE_THRESHOLD

    def test_market_news_with_timeout_triggers_caveat(self):
        """market_news with timeout output drops below threshold."""
        score, _ = score_confidence(
            "Market news request timed out.",
            ["market_news"],
            ["Request timed out after 30 seconds"],
        )
        assert score < LOW_CONFIDENCE_THRESHOLD

    def test_market_news_successful_no_caveat(self):
        """market_news with successful outputs should NOT trigger caveat."""
        score, _ = score_confidence(
            "Here are the top market stories today: Tech stocks rallied.",
            ["market_news"],
            ["Top stories: Tech stocks rally on strong earnings reports."],
        )
        assert score >= LOW_CONFIDENCE_THRESHOLD

    def test_market_news_plus_data_tool_successful(self):
        """market_news + data tool, both successful = above threshold."""
        score, _ = score_confidence(
            "Your portfolio is up $1,200 today. Market news shows tech rally.",
            ["portfolio_analysis", "market_news"],
            ["Portfolio gain: $1,200", "Top stories: Tech rally continues"],
        )
        assert score >= LOW_CONFIDENCE_THRESHOLD

    # --- Ghostfolio tools with errors (should NOT trigger caveat) ---

    def test_ghostfolio_tool_errors_stay_above_threshold(self):
        """Ghostfolio tool errors reduce score but never trigger caveat."""
        score, _ = score_confidence(
            "I encountered an issue fetching your portfolio data.",
            ["portfolio_analysis"],
            ["Error fetching portfolio data: 500 Internal Server Error"],
        )
        # Score may be reduced, but floor ensures it stays >= threshold
        assert score >= LOW_CONFIDENCE_THRESHOLD

    def test_ghostfolio_tool_errors_reduce_relative_score(self):
        """Tool errors still reduce confidence relative to success."""
        score_err, _ = score_confidence(
            "I encountered an issue fetching your portfolio data.",
            ["portfolio_analysis"],
            ["Error fetching portfolio data: 500 Internal Server Error"],
        )
        score_ok, _ = score_confidence(
            "Your portfolio is worth $50,000.",
            ["portfolio_analysis"],
            ["Portfolio Value: $50,000"],
        )
        assert score_ok > score_err

    # --- Score clamping and detail ---

    def test_score_clamped_to_range(self):
        """Score is always between 0.0 and 1.0."""
        score_high, _ = score_confidence(
            "Portfolio: $100,000.00 with 15.50% return and $2,500.00 dividends.",
            ["portfolio_analysis", "benchmark_comparison", "dividend_analysis",
             "risk_assessment", "account_summary"],
            ["Value: $100,000", "Return: 15.50%", "Dividends: $2,500"],
        )
        assert 0.0 <= score_high <= 1.0

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

    # --- Caveat text ---

    def test_caveat_text_mentions_third_party(self):
        """LOW_CONFIDENCE_CAVEAT should mention third-party source."""
        assert "third-party" in LOW_CONFIDENCE_CAVEAT.lower()
