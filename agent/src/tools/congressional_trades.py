from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

_QUIVER_BASE_URL = "https://api.quiverquant.com/beta/live/congresstrading"
_MOCK_DATA_PATH = Path(__file__).resolve().parent / "mock_congressional_trades.json"


@tool
async def congressional_trades(
    query: Optional[str] = None,
    chamber: Optional[str] = None,
    ticker: Optional[str] = None,
    days: int = 90,
    *,
    config: RunnableConfig,
) -> str:
    """Fetch recent stock trades by members of the U.S. Congress. Use this when
    users ask about politician stock trades, congressional trading activity, or
    want to see what members of Congress are buying or selling.

    Args:
        query: Optional politician name to filter by (e.g. "Pelosi", "Tuberville").
        chamber: Optional chamber filter — "senate" or "house".
        ticker: Optional stock ticker to see which politicians traded it (e.g. "NVDA").
        days: How many days back to look (default 90).
    """
    if os.environ.get("MOCK_CONGRESS", "").lower() in ("1", "true", "yes"):
        with open(_MOCK_DATA_PATH) as f:
            trades = json.load(f)
    else:
        api_token = os.environ.get("QUIZER_AUTHORIZATION_TOKEN")
        if not api_token:
            return (
                "Error: QUIZER_AUTHORIZATION_TOKEN environment variable is not set. "
                "Please configure it to use the congressional trades tool."
            )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    _QUIVER_BASE_URL,
                    headers={"Authorization": f"Bearer {api_token}"},
                )
                response.raise_for_status()
                trades = response.json()
        except httpx.HTTPStatusError as e:
            return f"Error fetching congressional trades: HTTP {e.response.status_code}"
        except httpx.RequestError as e:
            return f"Error fetching congressional trades: {e}"
        except Exception as e:
            return f"Error fetching congressional trades: {e}"

    if not trades:
        return "No congressional trading data available."

    # Filter by date range
    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for trade in trades:
        trade_date_str = trade.get("Date") or trade.get("TransactionDate", "")
        if trade_date_str:
            try:
                trade_date = datetime.strptime(trade_date_str[:10], "%Y-%m-%d")
                if trade_date < cutoff:
                    continue
            except ValueError:
                pass
        filtered.append(trade)

    # Filter by politician name
    if query:
        q = query.lower()
        filtered = [
            t for t in filtered
            if q in t.get("Representative", "").lower()
        ]

    # Filter by chamber
    if chamber:
        c = chamber.lower()
        if c not in ("senate", "house"):
            return "Error: chamber must be 'senate' or 'house'."
        # Quiver uses "Senate" / "House" in the House field
        filtered = [
            t for t in filtered
            if t.get("House", "").lower() == c
        ]

    # Filter by ticker
    if ticker:
        t_upper = ticker.upper()
        filtered = [
            t for t in filtered
            if t.get("Ticker", "").upper() == t_upper
        ]

    if not filtered:
        parts = []
        if query:
            parts.append(f"politician '{query}'")
        if chamber:
            parts.append(f"chamber '{chamber}'")
        if ticker:
            parts.append(f"ticker '{ticker.upper()}'")
        filter_desc = " matching " + ", ".join(parts) if parts else ""
        return f"No congressional trades found{filter_desc} in the last {days} days."

    # Sort by date descending
    filtered.sort(
        key=lambda t: t.get("Date") or t.get("TransactionDate", ""),
        reverse=True,
    )

    # Limit to 20 most recent trades
    filtered = filtered[:20]

    lines = ["**Congressional Stock Trades**\n"]

    lines.append(
        "| Politician | Party | Chamber | Ticker | Transaction | Amount | Date | Report Date |"
    )
    lines.append(
        "|------------|-------|---------|--------|-------------|--------|------|-------------|"
    )

    for t in filtered:
        name = t.get("Representative", "N/A").replace("|", "\\|")
        party = t.get("Party", "N/A")
        house = t.get("House", "N/A")
        tick = t.get("Ticker", "N/A")
        tx_type = t.get("Transaction", "N/A")
        amount = t.get("Amount", t.get("Range", "N/A"))
        date = (t.get("Date") or t.get("TransactionDate", "N/A"))[:10]
        report_date = (t.get("ReportDate", "N/A"))[:10] if t.get("ReportDate") else "N/A"

        lines.append(
            f"| {name} | {party} | {house} | {tick} | {tx_type} | {amount} | {date} | {report_date} |"
        )

    lines.append(
        "\n*Note: Congressional trades are self-reported and may be disclosed "
        "up to 45 days after the transaction date.*"
    )

    return "\n".join(lines)
