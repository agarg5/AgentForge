"""Scope verification — detects off-topic responses that slipped past the system prompt."""

from __future__ import annotations

import re

# Keywords that strongly indicate the agent stayed on-topic (finance/portfolio)
ON_TOPIC_SIGNALS = [
    r"portfolio",
    r"holdings?",
    r"allocation",
    r"performance",
    r"dividends?",
    r"benchmark",
    r"risk",
    r"returns?",
    r"market\s+data",
    r"symbol",
    r"ticker",
    r"order",
    r"transaction",
    r"account",
    r"invest",
    r"shares?",
    r"currency",
    r"asset",
    r"stock",
    r"bond",
    r"etf",
    r"fund",
    r"balance",
    r"net\s+worth",
    r"preference",
]

# Phrases indicating the agent correctly declined an off-topic request
DECLINED_PATTERNS = [
    r"portfolio assistant",
    r"can(?:'t| not|not) help with",
    r"outside (?:my|the) scope",
    r"only (?:help|assist) with.*(?:portfolio|invest|financ)",
    r"not (?:able|designed) to",
    r"(?:unrelated|off.topic)",
]

# If none of these tools were called AND no on-topic signals found, likely off-topic
PORTFOLIO_TOOLS = {
    "portfolio_analysis",
    "transaction_history",
    "market_data",
    "risk_assessment",
    "benchmark_comparison",
    "dividend_analysis",
    "account_summary",
    "create_order",
    "delete_order",
    "get_user_preferences",
    "save_user_preference",
    "delete_user_preference",
}


def check_scope(response: str, tools_used: list[str]) -> tuple[bool, str]:
    """Check if the agent's response stays within financial/portfolio scope.

    Returns:
        (True, "") if on-topic or correctly declined.
        (False, detail) if the response appears off-topic.
    """
    response_lower = response.lower()

    # If tools were used, the agent engaged with portfolio data — on-topic
    if set(tools_used) & PORTFOLIO_TOOLS:
        return True, ""

    # If the agent declined the request, that's correct behavior
    for pattern in DECLINED_PATTERNS:
        if re.search(pattern, response_lower):
            return True, ""

    # No tools used and no decline — check for on-topic content signals
    on_topic_count = sum(
        1 for pattern in ON_TOPIC_SIGNALS
        if re.search(pattern, response_lower)
    )

    # If enough on-topic signals, it's likely a valid informational response
    if on_topic_count >= 2:
        return True, ""

    # Short responses (greetings, acknowledgements) are fine
    if len(response.split()) < 20:
        return True, ""

    return False, (
        "Response may be off-topic: no portfolio tools were called and "
        "the content lacks financial/portfolio keywords. The agent should "
        "either use tools to answer portfolio questions or decline "
        "off-topic requests."
    )
