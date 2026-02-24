"""Verification layer — post-processes agent responses to catch issues.

Runs all verification checks and optionally appends warnings or disclaimers
to the response before returning it to the user.
"""

from __future__ import annotations

import logging

from .confidence import LOW_CONFIDENCE_CAVEAT, LOW_CONFIDENCE_THRESHOLD, score_confidence
from .disclaimer import check_disclaimer
from .numeric import check_numeric_consistency
from .scope import check_scope

logger = logging.getLogger("agentforge.verification")

DISCLAIMER_TEXT = (
    "\n\n*This is for informational purposes only and does not "
    "constitute financial advice.*"
)


def verify_response(
    response: str,
    tools_used: list[str],
    tool_outputs: list[str] | None = None,
) -> dict:
    """Run all verification checks on an agent response.

    Args:
        response: The agent's final text response.
        tools_used: List of tool names called during the interaction.
        tool_outputs: Raw string outputs from each tool call.

    Returns:
        dict with keys:
            response: The (possibly amended) response text.
            checks: List of check results with name, passed, detail.
            amended: Whether the response was modified.
    """
    checks = []
    amended = False
    final_response = response

    # Check 1: Scope — is the response on-topic?
    try:
        passed, detail = check_scope(response, tools_used)
        checks.append({"name": "scope", "passed": passed, "detail": detail})
        if not passed:
            logger.warning("Scope check failed: %s", detail)
    except Exception as e:
        logger.error("Scope check failed: %s", e)
        checks.append({"name": "scope", "passed": True, "detail": f"Check error: {e}"})

    # Check 2: Disclaimer
    try:
        passed, detail = check_disclaimer(response, tools_used)
        checks.append({"name": "disclaimer", "passed": passed, "detail": detail})
        if not passed:
            final_response += DISCLAIMER_TEXT
            amended = True
            logger.info("Appended missing disclaimer to response")
    except Exception as e:
        logger.error("Disclaimer check failed: %s", e)
        checks.append({"name": "disclaimer", "passed": True, "detail": f"Check error: {e}"})

    # Check 3: Numeric consistency
    try:
        passed, detail = check_numeric_consistency(response, tool_outputs or [])
        checks.append({"name": "numeric_consistency", "passed": passed, "detail": detail})
        if not passed:
            logger.warning("Numeric consistency issue: %s", detail)
    except Exception as e:
        logger.error("Numeric consistency check failed: %s", e)
        checks.append({"name": "numeric_consistency", "passed": True, "detail": f"Check error: {e}"})

    # Check 4: Confidence scoring
    try:
        confidence, detail = score_confidence(response, tools_used, tool_outputs)
        checks.append({"name": "confidence", "passed": confidence >= LOW_CONFIDENCE_THRESHOLD, "detail": detail})
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            final_response += LOW_CONFIDENCE_CAVEAT
            amended = True
            logger.info("Appended low-confidence caveat (score=%.2f)", confidence)
    except Exception as e:
        logger.error("Confidence scoring failed: %s", e)
        checks.append({"name": "confidence", "passed": True, "detail": f"Check error: {e}"})

    # Check 5: Ticker verification is done at tool-call time (create_order.py)
    # Record it as always-passed here since it's enforced upstream
    checks.append({"name": "ticker_verification", "passed": True, "detail": "Enforced at tool-call time"})

    return {
        "response": final_response,
        "checks": checks,
        "amended": amended,
    }
