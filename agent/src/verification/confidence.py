"""Confidence scoring — quantifies certainty of agent responses.

Produces a 0.0–1.0 confidence score based on signals like whether tools
were called, whether numeric data is present, and whether the response
contains hedging language.  Low-confidence responses get a visible
caveat appended so users know to treat them with caution.
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

# Threshold below which we append a low-confidence caveat
LOW_CONFIDENCE_THRESHOLD = 0.4

LOW_CONFIDENCE_CAVEAT = (
    "\n\n> **Note:** This response has lower confidence because it is "
    "based on limited or no tool data. Please verify the information "
    "with your portfolio directly."
)


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
        - No tools called
        - Hedging language present
        - Tool called but returned an error

    Returns:
        (score, detail) where score is 0.0–1.0 and detail explains the rating.
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

    # No tools called at all
    if not tools_used:
        score -= 0.2
        factors.append("-0.20 no tools called")

    # Hedging language
    hedging_count = sum(
        1 for p in _HEDGING_PATTERNS if re.search(p, response_lower)
    )
    if hedging_count >= 2:
        penalty = min(hedging_count * 0.05, 0.15)
        score -= penalty
        factors.append(f"-{penalty:.2f} hedging language ({hedging_count} instances)")

    # Tool errors in outputs
    error_outputs = [o for o in tool_outputs if o and "error" in o.lower()[:50]]
    if error_outputs:
        penalty = min(len(error_outputs) * 0.1, 0.2)
        score -= penalty
        factors.append(f"-{penalty:.2f} tool errors ({len(error_outputs)})")

    # Clamp to [0.0, 1.0]
    score = max(0.0, min(1.0, round(score, 2)))

    detail = f"confidence={score:.2f}"
    if factors:
        detail += " (" + ", ".join(factors) + ")"

    return score, detail
