"""Tests for scope verification — off-topic detection."""

import pytest

from src.verification.scope import check_scope


class TestCheckScope:
    def test_on_topic_with_tools(self):
        """Response that used portfolio tools is always on-topic."""
        passed, _ = check_scope(
            "Your portfolio is worth $50,000.",
            ["portfolio_analysis"],
        )
        assert passed

    def test_on_topic_with_preference_tools(self):
        """Preference tools are valid portfolio-related tools."""
        passed, _ = check_scope(
            "I've saved your currency preference.",
            ["save_user_preference"],
        )
        assert passed

    def test_on_topic_no_tools_financial_keywords(self):
        """Response without tools but with financial keywords is on-topic."""
        passed, _ = check_scope(
            "Your portfolio allocation shows heavy exposure to stocks and ETFs. "
            "Consider diversifying into bonds for lower risk.",
            [],
        )
        assert passed

    def test_on_topic_decline_off_topic(self):
        """Agent correctly declining an off-topic request passes."""
        passed, _ = check_scope(
            "I'm a portfolio assistant and can only help with investment-related questions. "
            "I can't help with coding tasks.",
            [],
        )
        assert passed

    def test_on_topic_decline_outside_scope(self):
        """Agent saying 'outside my scope' passes."""
        passed, _ = check_scope(
            "That question is outside my scope. I can help with portfolio analysis, "
            "market data, and account management.",
            [],
        )
        assert passed

    def test_on_topic_short_response(self):
        """Short responses (greetings, acknowledgements) pass."""
        passed, _ = check_scope(
            "Hello! How can I help with your portfolio today?",
            [],
        )
        assert passed

    def test_off_topic_long_unrelated_response(self):
        """Long response with no financial keywords and no tools is flagged."""
        passed, detail = check_scope(
            "The capital of France is Paris. It is known for the Eiffel Tower, "
            "the Louvre museum, and its wonderful cuisine. The city has a "
            "population of approximately 2.1 million people in the city proper.",
            [],
        )
        assert not passed
        assert "off-topic" in detail.lower()

    def test_off_topic_code_response(self):
        """Agent generating code is off-topic."""
        passed, detail = check_scope(
            "Here's a Python function to sort a list: def sort_list(items): "
            "return sorted(items) This uses the built-in sorted function which "
            "implements TimSort algorithm for efficient sorting of elements.",
            [],
        )
        assert not passed

    def test_on_topic_create_order_tool(self):
        """Write operations are on-topic."""
        passed, _ = check_scope(
            "I've created a buy order for 10 shares of AAPL at $150.",
            ["create_order"],
        )
        assert passed

    def test_on_topic_market_data_tool(self):
        """Market data queries are on-topic."""
        passed, _ = check_scope(
            "AAPL is currently trading at $182.52.",
            ["market_data"],
        )
        assert passed
