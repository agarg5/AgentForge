"""Scope verification — detects off-topic responses that slipped past the system prompt."""

from __future__ import annotations

import re

# Keywords that strongly indicate the agent stayed on-topic (finance/portfolio).
# Split into unambiguous (always financial) and ambiguous (common in everyday
# language — require word-boundary matching and contribute less weight).
_UNAMBIGUOUS_SIGNALS = [
    r"portfolio",
    r"holdings?",
    r"allocation",
    r"dividends?",
    r"benchmark",
    r"market\s+data",
    r"ticker",
    r"invest(?:ment|ing|or)?",
    r"shares?",
    r"etf",
    r"net\s+worth",
]

_AMBIGUOUS_SIGNALS = [
    r"\brisk\b",
    r"\breturns?\b",
    r"\border\b",
    r"\btransaction\b",
    r"\baccount\b",
    r"\bcurrency\b",
    r"\bassets?\b",
    r"\bstocks?\b",
    r"\bbonds?\b",
    r"\bfunds?\b",
    r"\bbalance\b",
    r"\bperformance\b",
    r"\bsymbol\b",
    r"\bpreference\b",
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

    # No tools used and no decline — check for on-topic content signals.
    # Unambiguous financial terms count as 2, ambiguous ones count as 1.
    score = sum(
        2 for p in _UNAMBIGUOUS_SIGNALS if re.search(p, response_lower)
    ) + sum(
        1 for p in _AMBIGUOUS_SIGNALS if re.search(p, response_lower)
    )

    # Require a score of at least 3 (e.g. one unambiguous + one ambiguous,
    # or three ambiguous) to be confident the response is on-topic.
    if score >= 3:
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
