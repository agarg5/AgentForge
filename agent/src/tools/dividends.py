from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioAPIError, GhostfolioClient


@tool
async def dividend_analysis(
    range: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Analyze dividend income, dividend history, and dividend payments from the
    portfolio. Returns dividend payments grouped by month, with totals and
    investment amounts. Use this tool for any questions about dividends,
    dividend yield, dividend income, or dividend history.

    Args:
        range: Time range for dividend data. Options: 1d, ytd, 1y, 5y, max.
               Defaults to max if not specified.
    """
    client: GhostfolioClient = config["configurable"]["client"]
    effective_range = range or "max"

    try:
        data = await client.get_dividends(range=effective_range)
    except GhostfolioAPIError as e:
        return f"Error fetching dividend data: {e}"
    dividends = data.get("dividends", [])

    if not dividends:
        return "No dividend data found for the selected period."

    lines = [f"**Dividend Analysis ({effective_range})**\n"]

    total_dividend = 0
    total_investment = 0

    lines.append("| Date | Dividend | Currency |")
    lines.append("|------|----------|----------|")

    for entry in dividends:
        date = entry.get("date", "")[:10]
        # Ghostfolio returns dividend amounts in the "investment" field
        amount = entry.get("investment", 0) or entry.get("dividend", 0)
        currency = entry.get("currency", "USD")
        total_dividend += amount

        if amount > 0:
            lines.append(f"| {date} | {amount:,.2f} | {currency} |")

    lines.append("")
    lines.append(f"**Total Dividends:** {total_dividend:,.2f}")

    return "\n".join(lines)
