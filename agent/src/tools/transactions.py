from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioAPIError, GhostfolioClient


@tool
async def transaction_history(
    accounts: Optional[str] = None,
    asset_classes: Optional[str] = None,
    symbol: Optional[str] = None,
    activity_type: Optional[str] = None,
    take: int = 50,
    *,
    config: RunnableConfig,
) -> str:
    """Retrieve the user's transaction history (buy/sell orders, dividends, fees).
    Returns a table of recent activities sorted by date (newest first).

    Use this tool when the user asks about their trades, purchases, sales,
    dividends received, or any past transaction activity. You can filter by
    symbol to answer questions like "when did I buy AAPL?" or by activity type
    to answer "show my dividends".

    Args:
        accounts: Comma-separated account IDs to filter by. Optional.
        asset_classes: Comma-separated asset classes to filter by (e.g. EQUITY,FIXED_INCOME). Optional.
        symbol: Ticker symbol to filter by (e.g. "AAPL", "MSFT"). Case-insensitive. Optional.
            Use this when the user asks about transactions for a specific stock or asset.
        activity_type: Filter by transaction type. One of: BUY, SELL, DIVIDEND, FEE, INTEREST, ITEM, LIABILITY. Optional.
            Use this when the user asks to see only buys, sells, dividends, etc.
        take: Maximum number of transactions to fetch from the API. Defaults to 50.
    """
    client: GhostfolioClient = config["configurable"]["client"]

    try:
        data = await client.get_transactions(
            accounts=accounts,
            asset_classes=asset_classes,
            take=take,
        )
    except GhostfolioAPIError as e:
        return f"Error fetching transactions: {e}"

    activities = data.get("activities", [])

    if not activities:
        return "No transactions found."

    # Client-side filtering by symbol
    if symbol:
        symbol_upper = symbol.upper()
        activities = [
            a for a in activities
            if (a.get("SymbolProfile", {}).get("symbol", "") or a.get("symbol", "")).upper() == symbol_upper
        ]

    # Client-side filtering by activity type
    if activity_type:
        type_upper = activity_type.upper()
        activities = [
            a for a in activities
            if (a.get("type", "")).upper() == type_upper
        ]

    if not activities:
        filters = []
        if symbol:
            filters.append(f"symbol={symbol}")
        if activity_type:
            filters.append(f"type={activity_type}")
        return f"No transactions found matching filters: {', '.join(filters)}."

    # Sort by date descending
    activities.sort(key=lambda a: a.get("date", ""), reverse=True)

    lines = [
        f"**Transactions** (showing {len(activities)} activities)\n",
        "| Date | Type | Symbol | Name | Quantity | Unit Price | Value | Fee | Currency | Account |",
        "|------|------|--------|------|----------|------------|-------|-----|----------|---------|",
    ]

    for a in activities:
        date = a.get("date", "")[:10]
        a_type = a.get("type", "")
        a_symbol = a.get("SymbolProfile", {}).get("symbol", "") or a.get("symbol", "")
        name = a.get("SymbolProfile", {}).get("name", "")
        quantity = a.get("quantity", 0)
        unit_price = a.get("unitPrice", 0)
        value = quantity * unit_price
        fee = a.get("fee", 0)
        currency = a.get("SymbolProfile", {}).get("currency", "") or a.get("currency", "")
        account_name = a.get("Account", {}).get("name", "") if a.get("Account") else ""
        lines.append(
            f"| {date} | {a_type} | {a_symbol} | {name} | {quantity:,.4g} | {unit_price:,.2f} | {value:,.2f} | {fee:,.2f} | {currency} | {account_name} |"
        )

    return "\n".join(lines)
