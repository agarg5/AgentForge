"""Disclaimer verification — ensures financial responses include disclaimers."""

from __future__ import annotations

import re

DISCLAIMER_PATTERNS = [
    r"not financial advice",
    r"not a recommendation",
    r"informational purposes",
    r"consult.*(?:financial|professional|advisor)",
    r"does not constitute.*advice",
    r"for informational",
    r"not intended as.*advice",
    r"disclaimer",
]

# Tool calls that produce financial data requiring a disclaimer
FINANCIAL_TOOLS = {
    "portfolio_analysis",
    "benchmark_comparison",
    "risk_assessment",
    "dividend_analysis",
}


def check_disclaimer(response: str, tools_used: list[str]) -> tuple[bool, str]:
    """Check if a response that uses financial tools includes a disclaimer.

    Returns:
        (True, "") if disclaimer is present or not needed.
        (False, suggestion) if disclaimer is missing.
    """
    # Only require disclaimers when financial analysis tools were used
    if not set(tools_used) & FINANCIAL_TOOLS:
        return True, ""

    response_lower = response.lower()
    for pattern in DISCLAIMER_PATTERNS:
        if re.search(pattern, response_lower):
            return True, ""

    return False, (
        "Response uses financial analysis tools but lacks a disclaimer. "
        "Consider adding: 'This is for informational purposes only and "
        "does not constitute financial advice.'"
    )
