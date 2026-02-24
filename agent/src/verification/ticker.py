"""Ticker symbol verification against the Ghostfolio data source."""

from __future__ import annotations

import httpx

from ..client import GhostfolioClient


async def verify_ticker(
    client: GhostfolioClient,
    symbol: str,
    data_source: str = "YAHOO",
) -> tuple[bool, str]:
    """Check whether a ticker symbol resolves to a real security.

    Returns:
        (True, "") if the symbol is valid.
        (False, reason) if the symbol cannot be found.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        return False, "Symbol is empty."

    # 1. Try direct profile lookup (fast path)
    try:
        profile = await client.get_symbol_profile(data_source, symbol)
        if profile and profile.get("symbol"):
            return True, ""
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            return False, f"Error verifying symbol: {e.response.status_code}"
        # 404 → symbol not found via profile, try search

    # 2. Fallback: search to see if the symbol exists under a different source
    try:
        results = await client.symbol_lookup(symbol)
    except httpx.HTTPStatusError:
        # If search also fails, we can't verify — allow through with warning
        return True, ""

    items = results.get("items", [])
    if not items:
        return False, f"Symbol '{symbol}' not found in any data source."

    # Check if any search result matches the exact symbol
    exact = [i for i in items if i.get("symbol", "").upper() == symbol]
    if exact:
        return True, ""

    # Symbol not exact-matched but similar results exist — suggest alternatives
    suggestions = ", ".join(
        f"{i['symbol']} ({i.get('name', '?')})" for i in items[:5]
    )
    return False, f"Symbol '{symbol}' not found. Did you mean: {suggestions}?"
