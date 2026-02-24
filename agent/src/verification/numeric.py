"""Numeric consistency verification — cross-references numbers in agent
responses against the raw tool outputs to flag potential hallucinations."""

from __future__ import annotations

import re


def _extract_numbers(text: str) -> set[str]:
    """Extract significant numbers (2+ digits) from text, normalized."""
    raw = re.findall(r"-?\d[\d,]*\.?\d*", text)
    normalized = set()
    for n in raw:
        clean = n.replace(",", "")
        # Skip trivially small numbers (1-digit integers)
        if clean.lstrip("-") and len(clean.lstrip("-").split(".")[0]) >= 2:
            normalized.add(clean)
    return normalized


def check_numeric_consistency(
    response: str,
    tool_outputs: list[str],
) -> tuple[bool, str]:
    """Verify that significant numbers in the response appear in tool outputs.

    This catches hallucinated values — e.g., the agent inventing a portfolio
    value instead of using the number returned by the tool.

    Returns:
        (True, "") if consistent or not enough data to check.
        (False, details) if suspicious numbers found.
    """
    if not tool_outputs:
        return True, ""

    response_numbers = _extract_numbers(response)
    if not response_numbers:
        return True, ""

    tool_text = " ".join(tool_outputs)
    tool_numbers = _extract_numbers(tool_text)

    if not tool_numbers:
        return True, ""

    # Check each response number against tool numbers
    # Allow for formatting differences (52,450.00 vs 52450.0)
    unmatched = []
    for rn in response_numbers:
        # Try exact match and truncated match
        rn_base = rn.rstrip("0").rstrip(".")
        matched = False
        for tn in tool_numbers:
            tn_base = tn.rstrip("0").rstrip(".")
            if rn_base == tn_base or rn in tn or tn in rn:
                matched = True
                break
        if not matched:
            unmatched.append(rn)

    if not unmatched:
        return True, ""

    # Only flag if a significant fraction of numbers are unmatched
    ratio = len(unmatched) / len(response_numbers)
    if ratio > 0.5 and len(unmatched) >= 2:
        return False, (
            f"Potential hallucination: {len(unmatched)}/{len(response_numbers)} "
            f"numbers in response not found in tool outputs. "
            f"Unmatched: {unmatched[:5]}"
        )

    return True, ""
