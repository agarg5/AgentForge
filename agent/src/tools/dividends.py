from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def dividend_analysis(
    range: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Analyze dividend income from the portfolio. Returns dividend
    payments grouped by month, with totals and investment amounts.

    Args:
        range: Time range for dividend data. Options: 1d, ytd, 1y, 5y, max.
               Defaults to max if not specified.
    """
    client: GhostfolioClient = config["configurable"]["client"]
    effective_range = range or "max"

    data = await client.get_dividends(range=effective_range)
    dividends = data.get("dividends", [])

    if not dividends:
        return "No dividend data found for the selected period."

    lines = [f"**Dividend Analysis ({effective_range})**\n"]

    total_dividend = 0
    total_investment = 0

    lines.append("| Date | Dividend | Investment | Currency |")
    lines.append("|------|----------|------------|----------|")

    for entry in dividends:
        date = entry.get("date", "")[:10]
        dividend = entry.get("dividend", 0)
        investment = entry.get("investment", 0)
        currency = entry.get("currency", "")
        total_dividend += dividend
        total_investment += investment

        if dividend > 0:
            lines.append(
                f"| {date} | {dividend:,.2f} | {investment:,.2f} | {currency} |"
            )

    lines.append("")
    lines.append(f"**Total Dividends:** {total_dividend:,.2f}")
    lines.append(f"**Total Invested:** {total_investment:,.2f}")
    if total_investment > 0:
        yield_pct = total_dividend / total_investment
        lines.append(f"**Dividend Yield:** {yield_pct:.2%}")

    return "\n".join(lines)
