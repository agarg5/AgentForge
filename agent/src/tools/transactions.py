from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def transaction_history(
    accounts: Optional[str] = None,
    asset_classes: Optional[str] = None,
    take: int = 50,
    *,
    config: RunnableConfig,
) -> str:
    """Retrieve the user's transaction history (buy/sell orders). Returns a
    table of recent activities sorted by date (newest first).

    Args:
        accounts: Comma-separated account IDs to filter by. Optional.
        asset_classes: Comma-separated asset classes to filter by (e.g. EQUITY,FIXED_INCOME). Optional.
        take: Maximum number of transactions to return. Defaults to 50.
    """
    client: GhostfolioClient = config["configurable"]["client"]

    data = await client.get_transactions(
        accounts=accounts,
        asset_classes=asset_classes,
        take=take,
    )

    activities = data.get("activities", [])

    if not activities:
        return "No transactions found."

    # Sort by date descending
    activities.sort(key=lambda a: a.get("date", ""), reverse=True)

    lines = [
        f"**Transactions** (showing {len(activities)} activities)\n",
        "| Date | Type | Symbol | Quantity | Unit Price | Fee | Currency |",
        "|------|------|--------|----------|------------|-----|----------|",
    ]

    for a in activities:
        date = a.get("date", "")[:10]
        activity_type = a.get("type", "")
        symbol = a.get("SymbolProfile", {}).get("symbol", "") or a.get("symbol", "")
        quantity = a.get("quantity", 0)
        unit_price = a.get("unitPrice", 0)
        fee = a.get("fee", 0)
        currency = a.get("SymbolProfile", {}).get("currency", "") or a.get("currency", "")
        lines.append(
            f"| {date} | {activity_type} | {symbol} | {quantity:,.4g} | {unit_price:,.2f} | {fee:,.2f} | {currency} |"
        )

    return "\n".join(lines)
