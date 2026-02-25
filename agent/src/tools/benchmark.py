from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioAPIError, GhostfolioClient

_MARKET_CONDITION_LABELS = {
    "ALL_TIME_HIGH": "All-Time High",
    "BEAR_MARKET": "Bear Market",
    "NEUTRAL_MARKET": "Neutral",
}


@tool
async def benchmark_comparison(
    range: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Compare portfolio performance against market benchmarks. Returns
    benchmark index performance, market condition, and trend indicators
    alongside the user's portfolio performance for the specified time range.

    Use this tool when the user asks how their portfolio compares to an index
    (e.g. S&P 500), wants to know about market conditions, or asks about
    relative performance.

    Args:
        range: Time range for comparison. Options: 1d, ytd, 1y, 5y, max.
               Defaults to max if not specified.
    """
    client: GhostfolioClient = config["configurable"]["client"]
    effective_range = range or "max"

    try:
        benchmarks = await client.get_benchmarks()
        performance = await client.get_portfolio_performance(range=effective_range)
    except GhostfolioAPIError as e:
        return f"Error fetching benchmark data: {e}"
    perf_summary = performance.get("performance", {})

    lines = [f"**Benchmark Comparison ({effective_range})**\n"]

    # Portfolio performance
    portfolio_perf = None
    if perf_summary:
        portfolio_perf = perf_summary.get("netPerformancePercentage", 0)
        current_value = perf_summary.get("currentValueInBaseCurrency", perf_summary.get("currentValue", "N/A"))
        currency = perf_summary.get("currency", "")
        lines.append(f"**Your Portfolio:** {portfolio_perf:.2%} net return ({effective_range})")
        if current_value != "N/A":
            lines.append(f"**Current Value:** {current_value:,.2f} {currency}")
        lines.append("")

    # Benchmark data
    if not benchmarks:
        lines.append("No benchmarks configured.")
        return "\n".join(lines)

    lines.append("| Benchmark | Symbol | Change from ATH | Market Condition | 50d Trend | 200d Trend |")
    lines.append("|-----------|--------|-----------------|------------------|-----------|------------|")

    for b in benchmarks:
        name = b.get("name", "N/A")
        symbol = b.get("symbol", "N/A")

        # All-time-high performance
        ath = b.get("performances", {}).get("allTimeHigh", {})
        ath_perf = ath.get("performancePercent")
        ath_str = f"{ath_perf:.2%}" if ath_perf is not None else "N/A"

        # Market condition
        condition = b.get("marketCondition", "")
        condition_str = _MARKET_CONDITION_LABELS.get(condition, condition or "N/A")

        # Trend indicators
        trend_50d = b.get("trend50d", "N/A")
        trend_200d = b.get("trend200d", "N/A")

        lines.append(f"| {name} | {symbol} | {ath_str} | {condition_str} | {trend_50d} | {trend_200d} |")

    # Summary comparison
    if portfolio_perf is not None and benchmarks:
        lines.append("")
        lines.append("**Summary:**")
        for b in benchmarks:
            bname = b.get("name", b.get("symbol", "benchmark"))
            ath_perf = b.get("performances", {}).get("allTimeHigh", {}).get("performancePercent")
            condition = b.get("marketCondition", "")
            condition_str = _MARKET_CONDITION_LABELS.get(condition, condition or "Unknown")
            if ath_perf is not None:
                lines.append(
                    f"- {bname} is {ath_str} from its all-time high (market condition: {condition_str})"
                )

    return "\n".join(lines)
