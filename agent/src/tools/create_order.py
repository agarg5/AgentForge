from __future__ import annotations

from typing import Optional

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient

VALID_ORDER_TYPES = ("BUY", "SELL", "DIVIDEND", "FEE", "INTEREST", "LIABILITY")


@tool
async def create_order(
    symbol: str,
    order_type: str,
    quantity: float,
    unit_price: float,
    currency: str,
    date: str,
    fee: float = 0,
    account_id: Optional[str] = None,
    data_source: str = "YAHOO",
    *,
    config: RunnableConfig,
) -> str:
    """Create a new buy or sell order in the portfolio. The agent MUST
    have received explicit user confirmation before calling this tool.

    Args:
        symbol: Ticker symbol (e.g. "AAPL", "VTI").
        order_type: Order type. One of: BUY, SELL, DIVIDEND, FEE, INTEREST, LIABILITY.
        quantity: Number of shares/units. Must be positive.
        unit_price: Price per share/unit. Must be non-negative.
        currency: ISO 4217 currency code (e.g. "USD", "EUR").
        date: Order date in ISO 8601 format (e.g. "2024-01-15T00:00:00Z").
        fee: Transaction fee. Defaults to 0.
        account_id: Optional account ID to associate the order with.
        data_source: Data source for the symbol. Defaults to YAHOO.
    """
    client: GhostfolioClient = config["configurable"]["client"]

    if quantity <= 0:
        return "Error: quantity must be positive."
    if unit_price < 0:
        return "Error: unit_price must be non-negative."
    if order_type.upper() not in VALID_ORDER_TYPES:
        return f"Error: invalid order type '{order_type}'. Must be one of: {', '.join(VALID_ORDER_TYPES)}."

    order_data = {
        "symbol": symbol.upper(),
        "type": order_type.upper(),
        "quantity": quantity,
        "unitPrice": unit_price,
        "currency": currency.upper(),
        "date": date,
        "fee": fee,
        "dataSource": data_source,
    }
    if account_id:
        order_data["accountId"] = account_id

    try:
        result = await client.create_order(order_data)
    except httpx.HTTPStatusError as e:
        return f"Error creating order: {e.response.status_code} — {e.response.text}"

    order_id = result.get("id", "N/A")
    return (
        f"Order created successfully.\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Order ID | {order_id} |\n"
        f"| Type | {order_type.upper()} |\n"
        f"| Symbol | {symbol.upper()} |\n"
        f"| Quantity | {quantity} |\n"
        f"| Unit Price | {unit_price} {currency.upper()} |\n"
        f"| Fee | {fee} {currency.upper()} |\n"
        f"| Date | {date} |"
    )
