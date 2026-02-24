from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def create_order(
    symbol: str,
    type: str,
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
        type: Order type. One of: BUY, SELL, DIVIDEND, FEE, INTEREST.
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
    if type not in ("BUY", "SELL", "DIVIDEND", "FEE", "INTEREST", "LIABILITY"):
        return f"Error: invalid order type '{type}'. Must be one of: BUY, SELL, DIVIDEND, FEE, INTEREST, LIABILITY."

    order_data = {
        "symbol": symbol.upper(),
        "type": type.upper(),
        "quantity": quantity,
        "unitPrice": unit_price,
        "currency": currency.upper(),
        "date": date,
        "fee": fee,
        "dataSource": data_source,
    }
    if account_id:
        order_data["accountId"] = account_id

    result = await client.create_order(order_data)

    order_id = result.get("id", "N/A")
    return (
        f"Order created successfully.\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Order ID | {order_id} |\n"
        f"| Type | {type} |\n"
        f"| Symbol | {symbol.upper()} |\n"
        f"| Quantity | {quantity} |\n"
        f"| Unit Price | {unit_price} {currency.upper()} |\n"
        f"| Fee | {fee} {currency.upper()} |\n"
        f"| Date | {date} |"
    )
