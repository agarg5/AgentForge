"""Extract token usage and latency metrics from agent results."""

from __future__ import annotations


def extract_metrics(result: dict) -> dict:
    """Pull token counts and tool call stats from an agent invocation result.

    Args:
        result: The dict returned by agent.ainvoke().

    Returns:
        A dict with token_usage, tool_calls, and message_count fields.
    """
    messages = result.get("messages", [])

    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    tool_call_count = 0
    tools_used = []

    for msg in messages:
        # Token usage is attached to AI messages via response_metadata
        if hasattr(msg, "response_metadata"):
            usage = msg.response_metadata.get("token_usage", {})
            total_input_tokens += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)
            total_tokens += usage.get("total_tokens", 0)

        # Count tool calls from AI messages
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_call_count += len(msg.tool_calls)
            for tc in msg.tool_calls:
                tools_used.append(tc.get("name", "unknown"))

    return {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "tool_call_count": tool_call_count,
        "tools_used": tools_used,
        "message_count": len(messages),
    }
