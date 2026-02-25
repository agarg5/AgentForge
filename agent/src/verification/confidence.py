"""Confidence scoring — quantifies certainty of agent responses.

Produces a 0.0–1.0 confidence score based on signals like whether tools
were called, whether numeric data is present, and whether the response
contains hedging language.  The low-confidence caveat is reserved for
responses that rely on third-party external data sources (e.g. market_news
via AlphaVantage) where data quality is less certain.
"""

from __future__ import annotations

import re

# Tools that return authoritative data from Ghostfolio
DATA_TOOLS = {
    "portfolio_analysis",
    "transaction_history",
    "market_data",
    "risk_assessment",
    "benchmark_comparison",
    "dividend_analysis",
    "account_summary",
}

# Tools that rely on third-party APIs where data quality is less certain
EXTERNAL_TOOLS = {
    "market_news",
}

# Hedging language that suggests uncertainty
_HEDGING_PATTERNS = [
    r"\bapproximately\b",
    r"\brough(?:ly)?\b",
    r"\bestimate[ds]?\b",
    r"\bmight\b",
    r"\bcould be\b",
    r"\bpossibly\b",
    r"\bunclear\b",
    r"\bnot sure\b",
    r"\bi(?:'m| am) not certain\b",
    r"\bgenerally\b",
    r"\btypically\b",
    r"\bit depends\b",
]

# Patterns indicating the response contains concrete data
_CONCRETE_DATA_PATTERNS = [
    r"\$[\d,]+\.?\d*",        # Dollar amounts
    r"\d+\.\d+%",             # Percentages with decimals
    r"\b\d{2,}(?:,\d{3})*\b", # Large numbers (100+)
]

# Patterns in tool output that indicate rate limiting or unavailability
_EXTERNAL_TOOL_ISSUE_PATTERNS = [
    r"rate.?limit",
    r"too many requests",
    r"429",
    r"unavailable",
    r"timed?\s*out",
    r"api.?key",
    r"quota",
]

# Threshold below which we append a low-confidence caveat
LOW_CONFIDENCE_THRESHOLD = 0.4

LOW_CONFIDENCE_CAVEAT = (
    "\n\n> **Note:** Market news data comes from a third-party source "
    "and may be delayed or limited. Please verify with additional sources."
)


def _has_external_tool_issues(tool_outputs: list[str]) -> bool:
    """Check if any tool outputs indicate errors or rate limiting."""
    for output in tool_outputs:
        if not output:
            continue
        output_lower = output.lower()
        # Check for explicit errors
        if "error" in output_lower[:50]:
            return True
        # Check for rate limiting / unavailability patterns
        for pattern in _EXTERNAL_TOOL_ISSUE_PATTERNS:
            if re.search(pattern, output_lower):
                return True
    return False


def score_confidence(
    response: str,
    tools_used: list[str],
    tool_outputs: list[str] | None = None,
) -> tuple[float, str]:
    """Score the confidence of an agent response from 0.0 to 1.0.

    Signals that increase confidence:
        - Data tools were called and returned output
        - Response contains concrete numeric data
        - Multiple tools corroborate the answer

    Signals that decrease confidence:
        - External tools (market_news) returned errors or rate-limited data
        - Hedging language present

    The low-confidence caveat is ONLY appended when market_news (or other
    external tools) were used and encountered issues.  Conversational
    responses and Ghostfolio-backed responses never trigger the caveat.

    Returns:
        (score, detail) where score is 0.0-1.0 and detail explains the rating.
    """
    response_lower = response.lower()
    tool_outputs = tool_outputs or []

    # Start with a base score
    score = 0.5
    factors: list[str] = []

    # --- Positive signals ---

    # Data tools used (strong signal)
    data_tools_used = set(tools_used) & DATA_TOOLS
    if data_tools_used:
        tool_bonus = min(len(data_tools_used) * 0.15, 0.3)
        score += tool_bonus
        factors.append(f"+{tool_bonus:.2f} data tools called ({len(data_tools_used)})")

    # Tool outputs present and non-empty (data was actually returned)
    successful_outputs = [o for o in tool_outputs if o and "error" not in o.lower()[:50]]
    if successful_outputs:
        score += 0.1
        factors.append("+0.10 tool outputs received")

    # Concrete data in response (numbers, dollar amounts, percentages)
    concrete_count = sum(
        1 for p in _CONCRETE_DATA_PATTERNS if re.search(p, response)
    )
    if concrete_count >= 2:
        score += 0.1
        factors.append("+0.10 concrete numeric data present")

    # --- Negative signals ---

    # External tool (market_news) with issues — the only path to the caveat
    external_tools_used = set(tools_used) & EXTERNAL_TOOLS
    if external_tools_used and _has_external_tool_issues(tool_outputs):
        score -= 0.3
        factors.append("-0.30 external tool data issues (market_news)")

    # Hedging language (informational only — cannot push below threshold
    # unless external tool issues are also present)
    hedging_count = sum(
        1 for p in _HEDGING_PATTERNS if re.search(p, response_lower)
    )
    if hedging_count >= 2:
        penalty = min(hedging_count * 0.05, 0.15)
        score -= penalty
        factors.append(f"-{penalty:.2f} hedging language ({hedging_count} instances)")

    # Clamp to [0.0, 1.0]
    score = max(0.0, min(1.0, round(score, 2)))

    # Floor: score cannot drop below the threshold unless external tools
    # were involved with issues.  This ensures conversational responses,
    # Ghostfolio-backed responses, and even hedged responses without
    # external-tool problems never trigger the caveat.
    if not (external_tools_used and _has_external_tool_issues(tool_outputs)):
        score = max(score, LOW_CONFIDENCE_THRESHOLD)

    detail = f"confidence={score:.2f}"
    if factors:
        detail += " (" + ", ".join(factors) + ")"

    return score, detail
