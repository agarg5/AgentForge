from __future__ import annotations

from typing import Optional

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def portfolio_analysis(
    range: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Analyze the user's investment portfolio. Returns holdings with allocation
    percentages, total portfolio value, and performance metrics.

    Args:
        range: Time range for performance data. Options: 1d, ytd, 1y, 5y, max.
               Defaults to max if not specified.
    """
    client: GhostfolioClient = config["configurable"]["client"]
    effective_range = range or "max"

    try:
        details = await client.get_portfolio_details(range=effective_range)
        performance = await client.get_portfolio_performance(range=effective_range)
    except httpx.HTTPStatusError as e:
        return f"Error fetching portfolio data: {e.response.status_code} — {e.response.text}"

    holdings = details.get("holdings", {})
    perf_summary = performance.get("performance", {})

    # Format holdings summary
    lines = []

    if perf_summary:
        total_value = perf_summary.get("currentValue", "N/A")
        currency = perf_summary.get("currency", "")
        net_perf = perf_summary.get("netPerformancePercentage", 0)
        lines.append(f"**Portfolio Value:** {total_value} {currency}")
        lines.append(f"**Net Performance ({effective_range}):** {net_perf:.2%}")
        lines.append("")

    if holdings:
        holding_list = (
            holdings.values() if isinstance(holdings, dict) else holdings
        )
        sorted_holdings = sorted(
            holding_list,
            key=lambda h: h.get("allocationInPercentage", 0),
            reverse=True,
        )
        lines.append("| Name | Symbol | Allocation | Value | Currency |")
        lines.append("|------|--------|-----------|-------|----------|")
        for h in sorted_holdings[:20]:
            name = h.get("name", "")
            symbol = h.get("symbol", "")
            alloc = h.get("allocationInPercentage", 0)
            value = h.get("value", 0)
            cur = h.get("currency", "")
            lines.append(
                f"| {name} | {symbol} | {alloc:.2%} | {value:,.2f} | {cur} |"
            )

        if len(sorted_holdings) > 20:
            lines.append(f"*...and {len(sorted_holdings) - 20} more holdings*")
    else:
        lines.append("No holdings found in the portfolio.")

    return "\n".join(lines)
