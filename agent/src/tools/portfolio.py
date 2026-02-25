from __future__ import annotations

from collections import defaultdict
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioAPIError, GhostfolioClient


@tool
async def portfolio_analysis(
    range: Optional[str] = None,
    include_sectors: bool = False,
    include_countries: bool = False,
    include_accounts: bool = False,
    *,
    config: RunnableConfig,
) -> str:
    """Analyze the user's investment portfolio. Returns top holdings with
    allocation percentages, profit/loss, total portfolio value, and performance.

    Args:
        range: Time range for performance data. Options: 1d, ytd, 1y, 5y, max.
               Defaults to max if not specified.
        include_sectors: Include sector breakdown. Set True when user asks about
                         sectors or diversification.
        include_countries: Include country/region breakdown. Set True when user
                          asks about geographic exposure.
        include_accounts: Include account summary. Set True when user asks about
                         accounts or balances.
    """
    client: GhostfolioClient = config["configurable"]["client"]
    effective_range = range or "max"

    try:
        details = await client.get_portfolio_details(range=effective_range)
        performance = await client.get_portfolio_performance(range=effective_range)
    except GhostfolioAPIError as e:
        return f"Error fetching portfolio data: {e}"

    holdings = details.get("holdings", {})
    perf_summary = performance.get("performance", {})
    accounts = details.get("accounts", {})

    lines = []

    # --- Portfolio value and performance header ---
    if perf_summary:
        total_value = perf_summary.get("currentValue", "N/A")
        currency = perf_summary.get("currency", "")
        net_perf = perf_summary.get("netPerformancePercentage", 0)
        lines.append(f"**Portfolio Value:** {total_value} {currency}")
        lines.append(f"**Net Performance ({effective_range}):** {net_perf:.2%}")
        lines.append("")

    # --- Holdings table (top 10, compact columns) ---
    if holdings:
        holding_list = (
            holdings.values() if isinstance(holdings, dict) else holdings
        )
        sorted_holdings = sorted(
            holding_list,
            key=lambda h: h.get("allocationInPercentage", 0),
            reverse=True,
        )

        lines.append("| Name | Symbol | Allocation | P&L | P&L % |")
        lines.append("|------|--------|-----------|-----|-------|")
        for h in sorted_holdings[:10]:
            name = h.get("name", "N/A")
            symbol = h.get("symbol", "N/A")
            alloc = h.get("allocationInPercentage", 0)
            net_pl = h.get("netPerformance", 0) or 0
            net_pl_pct = h.get("netPerformancePercent", 0) or 0
            sign = "+" if net_pl >= 0 else ""
            lines.append(
                f"| {name} | {symbol} | {alloc:.2%} "
                f"| {sign}{net_pl:,.2f} | {sign}{net_pl_pct:.2%} |"
            )

        remaining = len(sorted_holdings) - 10
        if remaining > 0:
            lines.append(f"*...and {remaining} more holdings*")
        lines.append("")

        # --- Sector breakdown (opt-in) ---
        if include_sectors:
            sector_weights: dict[str, float] = defaultdict(float)
            for h in sorted_holdings:
                alloc = h.get("allocationInPercentage", 0)
                for sector in h.get("sectors", []):
                    sector_name = sector.get("name", "Unknown")
                    sector_weight = sector.get("weight", 0) or 0
                    sector_weights[sector_name] += sector_weight * alloc

            if sector_weights:
                sorted_sectors = sorted(
                    sector_weights.items(), key=lambda x: x[1], reverse=True
                )[:5]
                lines.append("**Top Sectors:**")
                for sector_name, weight in sorted_sectors:
                    lines.append(f"- {sector_name}: {weight:.2%}")
                lines.append("")

        # --- Country/region breakdown (opt-in) ---
        if include_countries:
            country_weights: dict[str, float] = defaultdict(float)
            for h in sorted_holdings:
                alloc = h.get("allocationInPercentage", 0)
                for country in h.get("countries", []):
                    country_name = country.get("name", "Unknown")
                    country_weight = country.get("weight", 0) or 0
                    country_weights[country_name] += country_weight * alloc

            if country_weights:
                sorted_countries = sorted(
                    country_weights.items(), key=lambda x: x[1], reverse=True
                )[:5]
                lines.append("**Top Countries:**")
                for country_name, weight in sorted_countries:
                    lines.append(f"- {country_name}: {weight:.2%}")
                lines.append("")
    else:
        lines.append("No holdings found in the portfolio.")

    # --- Account summary (opt-in) ---
    if include_accounts and accounts:
        account_list = (
            accounts.values() if isinstance(accounts, dict) else accounts
        )
        account_items = list(account_list)
        if account_items:
            lines.append("**Accounts:**")
            for acct in account_items:
                acct_name = acct.get("name", "N/A")
                acct_currency = acct.get("currency", "N/A")
                acct_value = acct.get("valueInBaseCurrency", 0) or 0
                lines.append(
                    f"- {acct_name}: {acct_value:,.2f} {acct_currency}"
                )
            lines.append("")

    return "\n".join(lines)
