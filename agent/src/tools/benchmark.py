from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def benchmark_comparison(
    range: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Compare portfolio performance against market benchmarks. Returns
    benchmark index performance alongside the user's portfolio performance
    for the specified time range.

    Args:
        range: Time range for comparison. Options: 1d, ytd, 1y, 5y, max.
               Defaults to max if not specified.
    """
    client: GhostfolioClient = config["configurable"]["client"]
    effective_range = range or "max"

    benchmarks = await client.get_benchmarks()
    performance = await client.get_portfolio_performance(range=effective_range)
    perf_summary = performance.get("performance", {})

    lines = [f"**Benchmark Comparison ({effective_range})**\n"]

    # Portfolio performance
    if perf_summary:
        net_perf = perf_summary.get("netPerformancePercentage", 0)
        lines.append(f"**Your Portfolio:** {net_perf:.2%}\n")

    # Benchmark data
    if not benchmarks:
        lines.append("No benchmarks configured.")
        return "\n".join(lines)

    lines.append("| Benchmark | Symbol | Performance |")
    lines.append("|-----------|--------|-------------|")

    for b in benchmarks:
        name = b.get("name", "N/A")
        symbol = b.get("symbol", "N/A")
        performances = b.get("performances", {})
        perf_value = performances.get(effective_range, {}).get("performancePercent")
        perf_str = f"{perf_value:.2%}" if perf_value is not None else "N/A"
        lines.append(f"| {name} | {symbol} | {perf_str} |")

    return "\n".join(lines)
