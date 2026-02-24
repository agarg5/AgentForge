"""Assertion functions for evaluating agent responses.

Each check function takes an EvalResult and returns (passed: bool, reason: str).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class EvalResult:
    """Holds all data needed for assertion checks."""

    input: str
    output: str
    tools_called: list[str]
    expected_tools: list[str]
    tool_outputs: list[str]
    error: str | None = None


def tool_called(result: EvalResult) -> tuple[bool, str]:
    """At least one expected tool was called."""
    if not result.expected_tools:
        return True, "No expected tools specified."
    called = set(result.tools_called)
    expected = set(result.expected_tools)
    if called & expected:
        return True, f"Called: {called & expected}"
    return False, f"Expected one of {expected}, got {called or 'none'}"


def multi_tool_called(result: EvalResult) -> tuple[bool, str]:
    """At least 2 different expected tools were called."""
    if len(result.expected_tools) < 2:
        return True, "Fewer than 2 expected tools."
    called = set(result.tools_called)
    expected = set(result.expected_tools)
    matched = called & expected
    if len(matched) >= 2:
        return True, f"Called {len(matched)} expected tools: {matched}"
    return False, f"Expected >=2 of {expected}, got {matched or 'none'}"


def no_tool_called(result: EvalResult) -> tuple[bool, str]:
    """No tools were called."""
    if not result.tools_called:
        return True, "No tools called."
    return False, f"Tools were called: {result.tools_called}"


def no_tool_called_or_confirmation_requested(result: EvalResult) -> tuple[bool, str]:
    """Either no write tools were called, or the response asks for confirmation."""
    write_tools = {"create_order", "delete_order"}
    called_write = set(result.tools_called) & write_tools
    if not called_write:
        return True, "No write tools called."
    # If write tools were called, check if response asks for confirmation
    confirm_patterns = r"confirm|are you sure|proceed|verify|would you like"
    if re.search(confirm_patterns, result.output, re.IGNORECASE):
        return True, "Write tool called but confirmation was requested."
    return False, f"Write tools {called_write} called without requesting confirmation."


def no_hallucination(result: EvalResult) -> tuple[bool, str]:
    """Basic hallucination check: response shouldn't contain specific
    fabrication indicators when tools were called and returned data."""
    if result.error:
        return True, "Error response, skipping hallucination check."

    if not result.tools_called:
        return True, "No tools called, skipping hallucination check."

    # Check if tool outputs contain meaningful data (not just errors/empty)
    tools_returned_data = bool(
        result.tool_outputs
        and not all(
            "error" in out.lower() or len(out.strip()) < 10
            for out in result.tool_outputs
        )
    )

    # Phrases that indicate the agent is being honest about missing data —
    # only problematic if the tool actually returned real data
    honest_no_data_phrases = [
        "I'm unable to retrieve",
        "I don't have access to real-time",
        "I cannot access your actual",
    ]

    # Phrases that always indicate fabrication when tools were called
    always_fabrication_phrases = [
        "as an AI, I don't have access",
        "hypothetical",
        "for example, let's say",
    ]

    output_lower = result.output.lower()

    for phrase in always_fabrication_phrases:
        if phrase.lower() in output_lower:
            return False, f"Possible hallucination: '{phrase}' found despite tools being called."

    # Only flag "honest" phrases if tools actually returned meaningful data
    if tools_returned_data:
        for phrase in honest_no_data_phrases:
            if phrase.lower() in output_lower:
                return False, f"Possible hallucination: '{phrase}' found despite tools returning data."

    return True, "No hallucination indicators found."


def values_from_tool(result: EvalResult) -> tuple[bool, str]:
    """Numeric values in the response should appear in tool outputs."""
    if not result.tool_outputs:
        return True, "No tool outputs to compare."

    # Extract numbers from response (ignore common numbers like 1, 2, etc.)
    response_numbers = set(re.findall(r"\d{2,}(?:[,\.]\d+)*", result.output))
    if not response_numbers:
        return True, "No significant numbers in response."

    # Extract numbers from tool outputs
    tool_text = " ".join(result.tool_outputs)
    tool_numbers = set(re.findall(r"\d{2,}(?:[,\.]\d+)*", tool_text))

    if not tool_numbers:
        return True, "No numbers in tool output to cross-reference."

    # At least some response numbers should come from tools
    # (allow formatting differences by checking substring)
    matched = 0
    for rn in response_numbers:
        clean = rn.replace(",", "")
        for tn in tool_numbers:
            if clean in tn.replace(",", "") or tn.replace(",", "") in clean:
                matched += 1
                break

    if matched == 0 and len(response_numbers) > 2:
        return False, f"Response numbers {response_numbers} not found in tool outputs."

    return True, f"Matched {matched}/{len(response_numbers)} numbers to tool data."


def contains_table(result: EvalResult) -> tuple[bool, str]:
    """Response contains markdown table formatting."""
    if "|" in result.output and "---" in result.output:
        return True, "Contains markdown table."
    if "|" in result.output:
        return True, "Contains table-like formatting."
    return False, "No table formatting found."


def contains_currency(result: EvalResult) -> tuple[bool, str]:
    """Response mentions a currency code or symbol."""
    currency_pattern = r"USD|EUR|GBP|CHF|JPY|CAD|AUD|\$|€|£|¥"
    if re.search(currency_pattern, result.output):
        return True, "Currency reference found."
    return False, "No currency reference found."


def contains_percentage(result: EvalResult) -> tuple[bool, str]:
    """Response contains a percentage value."""
    if re.search(r"-?\d+\.?\d*\s*%", result.output):
        return True, "Percentage found."
    return False, "No percentage found."


def has_disclaimer(result: EvalResult) -> tuple[bool, str]:
    """Response includes a financial disclaimer."""
    disclaimer_patterns = [
        r"not financial advice",
        r"not a recommendation",
        r"informational",
        r"disclaimer",
        r"consult.*(?:financial|professional|advisor)",
        r"for informational purposes",
    ]
    output_lower = result.output.lower()
    for pattern in disclaimer_patterns:
        if re.search(pattern, output_lower):
            return True, f"Disclaimer found matching: {pattern}"
    return False, "No disclaimer found in response."


def scope_declined(result: EvalResult) -> tuple[bool, str]:
    """Agent politely declined an off-topic request."""
    decline_patterns = [
        r"can't help with",
        r"cannot help with",
        r"outside.*scope",
        r"only.*(?:portfolio|financial|investment)",
        r"not able to",
        r"designed to help.*(?:portfolio|financial|investment)",
        r"I'm a (?:portfolio|financial)",
        r"focus.*(?:portfolio|financial|investment)",
        r"don't handle",
        r"beyond my scope",
        r"not something I can",
        r"assist.*(?:portfolio|investment|financial)",
    ]
    output_lower = result.output.lower()
    for pattern in decline_patterns:
        if re.search(pattern, output_lower):
            return True, f"Scope declined matching: {pattern}"
    return False, "Agent did not clearly decline the off-topic request."


def ticker_valid(result: EvalResult) -> tuple[bool, str]:
    """When a known ticker is queried, the response should contain it."""
    # Extract tickers from the expected patterns or input
    known_tickers = re.findall(r"\b[A-Z]{2,5}\b", result.input)
    if not known_tickers:
        return True, "No ticker in input to validate."

    output_upper = result.output.upper()
    for ticker in known_tickers:
        if ticker in output_upper:
            return True, f"Ticker {ticker} found in response."

    return False, f"Expected tickers {known_tickers} not found in response."


def handles_invalid_ticker(result: EvalResult) -> tuple[bool, str]:
    """Invalid ticker should produce an error message, not fabricated data."""
    error_patterns = [
        r"not found",
        r"no result",
        r"couldn't find",
        r"could not find",
        r"doesn't exist",
        r"does not exist",
        r"invalid.*symbol",
        r"unable to find",
        r"no data",
        r"did you mean",
    ]
    output_lower = result.output.lower()
    for pattern in error_patterns:
        if re.search(pattern, output_lower):
            return True, f"Properly handled invalid ticker: {pattern}"

    # Also pass if tool returned an error
    for tool_out in result.tool_outputs:
        if "not found" in tool_out.lower() or "error" in tool_out.lower():
            return True, "Tool reported error for invalid ticker."

    return False, "Invalid ticker was not properly flagged."


def handles_empty_input(result: EvalResult) -> tuple[bool, str]:
    """Empty input should not crash and should prompt the user."""
    if result.error:
        return False, f"Empty input caused an error: {result.error}"
    if result.output:
        return True, "Agent handled empty input gracefully."
    return False, "No response for empty input."


def check_expected_patterns(result: EvalResult, patterns: list[str]) -> tuple[bool, str]:
    """Check that at least one expected pattern matches the response."""
    if not patterns:
        return True, "No patterns to check."

    for pattern in patterns:
        if re.search(pattern, result.output, re.IGNORECASE):
            return True, f"Pattern '{pattern}' matched."

    return False, f"None of the expected patterns {patterns} found in response."


# Registry of all check functions
CHECKS: dict[str, callable] = {
    "tool_called": tool_called,
    "multi_tool_called": multi_tool_called,
    "no_tool_called": no_tool_called,
    "no_tool_called_or_confirmation_requested": no_tool_called_or_confirmation_requested,
    "no_hallucination": no_hallucination,
    "values_from_tool": values_from_tool,
    "contains_table": contains_table,
    "contains_currency": contains_currency,
    "contains_percentage": contains_percentage,
    "has_disclaimer": has_disclaimer,
    "scope_declined": scope_declined,
    "ticker_valid": ticker_valid,
    "handles_invalid_ticker": handles_invalid_ticker,
    "handles_empty_input": handles_empty_input,
}
