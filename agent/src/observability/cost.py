"""Cost analysis for agent API calls.

Pricing based on OpenAI GPT-4o rates (per 1M tokens).
Updated: 2025-01. Adjust MODEL_PRICING when rates change.
"""

from __future__ import annotations

# Pricing per 1M tokens (USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
}

DEFAULT_MODEL = "gpt-4o"


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Calculate the cost of a single API call.

    Returns:
        dict with input_cost, output_cost, total_cost (all in USD),
        and the model and token counts used.
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
    }


def calculate_batch_cost(requests: list[dict]) -> dict:
    """Calculate aggregate cost across multiple requests.

    Args:
        requests: List of dicts with input_tokens and output_tokens keys.

    Returns:
        Aggregate cost summary with per-request breakdown.
    """
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    per_request = []

    for req in requests:
        cost = calculate_cost(
            input_tokens=req.get("input_tokens", 0),
            output_tokens=req.get("output_tokens", 0),
            model=req.get("model", DEFAULT_MODEL),
        )
        total_input_tokens += cost["input_tokens"]
        total_output_tokens += cost["output_tokens"]
        total_cost += cost["total_cost_usd"]
        per_request.append(cost)

    avg_cost = total_cost / len(requests) if requests else 0

    return {
        "request_count": len(requests),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_per_request_usd": round(avg_cost, 6),
        "per_request": per_request,
    }
