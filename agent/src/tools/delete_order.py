from __future__ import annotations

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def delete_order(
    order_id: str,
    *,
    config: RunnableConfig,
) -> str:
    """Delete an existing order by its ID. The agent MUST have received
    explicit user confirmation before calling this tool.

    Use the transaction_history tool first to find order IDs.

    Args:
        order_id: The UUID of the order to delete.
    """
    client: GhostfolioClient = config["configurable"]["client"]

    if not order_id or not order_id.strip():
        return "Error: order_id is required."

    try:
        result = await client.delete_order(order_id.strip())
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: order '{order_id}' not found."
        return f"Error deleting order: {e.response.status_code} — {e.response.text}"

    if not result:
        return f"Order `{order_id}` deleted successfully."

    symbol = result.get("SymbolProfile", {}).get("symbol", "") or result.get("symbol", "N/A")
    order_type = result.get("type", "N/A")
    quantity = result.get("quantity", "N/A")

    return (
        f"Order deleted successfully.\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Order ID | {order_id} |\n"
        f"| Type | {order_type} |\n"
        f"| Symbol | {symbol} |\n"
        f"| Quantity | {quantity} |"
    )
