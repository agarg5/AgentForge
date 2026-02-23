from __future__ import annotations

from typing import Optional

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def market_data(
    query: str,
    data_source: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Look up market data for a ticker symbol or search term. Returns asset
    profile information (name, sector, price, currency) for known symbols, or
    a list of search results when the exact symbol is not found.

    Args:
        query: A ticker symbol (e.g. "AAPL") or search term (e.g. "Apple").
        data_source: Data source to query. Defaults to YAHOO.
    """
    client: GhostfolioClient = config["configurable"]["client"]
    source = data_source or "YAHOO"

    # First, try a direct symbol profile lookup
    try:
        profile = await client.get_symbol_profile(source, query.upper())
        return _format_profile(profile)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise
        # 404 means symbol not found — fall through to search

    # Fallback: run a symbol search
    results = await client.symbol_lookup(query)
    items = results.get("items", [])

    if not items:
        return f"No results found for '{query}'."

    return _format_search_results(items)


def _format_profile(profile: dict) -> str:
    lines = []
    name = profile.get("name", "N/A")
    symbol = profile.get("symbol", "N/A")
    sector = profile.get("sectors", [{}])[0].get("name", "N/A") if profile.get("sectors") else "N/A"
    currency = profile.get("currency", "N/A")
    asset_class = profile.get("assetClass", "N/A")
    asset_sub_class = profile.get("assetSubClass", "N/A")

    market_price = profile.get("marketPrice", "N/A")

    lines.append(f"**{name}** ({symbol})")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Current Price | {market_price} {currency} |")
    lines.append(f"| Asset Class | {asset_class} |")
    lines.append(f"| Sub Class | {asset_sub_class} |")
    lines.append(f"| Sector | {sector} |")
    lines.append(f"| Currency | {currency} |")

    # Include countries if available
    countries = profile.get("countries", [])
    if countries:
        country_names = ", ".join(c.get("name", "N/A") for c in countries[:5])
        lines.append(f"| Countries | {country_names} |")

    return "\n".join(lines)


def _format_search_results(items: list) -> str:
    lines = []
    lines.append(f"Found {len(items)} result(s):\n")
    lines.append("| Symbol | Name | Data Source | Currency |")
    lines.append("|--------|------|-------------|----------|")
    for item in items[:20]:
        symbol = item.get("symbol", "")
        name = item.get("name", "")
        ds = item.get("dataSource", "")
        cur = item.get("currency", "")
        lines.append(f"| {symbol} | {name} | {ds} | {cur} |")

    if len(items) > 20:
        lines.append(f"*...and {len(items) - 20} more results*")

    return "\n".join(lines)
