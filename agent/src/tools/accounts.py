from __future__ import annotations

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def account_summary(
    *,
    config: RunnableConfig,
) -> str:
    """Get a summary of all investment accounts. Returns account names,
    balances, currencies, and platform information.

    No arguments needed — returns all accounts.
    """
    client: GhostfolioClient = config["configurable"]["client"]

    try:
        data = await client.get_accounts()
    except httpx.HTTPStatusError as e:
        return f"Error fetching accounts: {e.response.status_code} — {e.response.text}"
    accounts = data.get("accounts", []) if isinstance(data, dict) else data

    if not accounts:
        return "No accounts found."

    lines = ["**Account Summary**\n"]

    total_value = 0
    lines.append("| Account | Platform | Balance | Value | Currency |")
    lines.append("|---------|----------|---------|-------|----------|")

    for acct in accounts:
        name = acct.get("name", "N/A")
        platform = acct.get("Platform", {}).get("name", "N/A") if acct.get("Platform") else "N/A"
        balance = acct.get("balance", 0)
        value = acct.get("value", 0)
        currency = acct.get("currency", "")
        total_value += value
        lines.append(
            f"| {name} | {platform} | {balance:,.2f} | {value:,.2f} | {currency} |"
        )

    lines.append("")
    lines.append(f"**Total Value Across Accounts:** {total_value:,.2f}")

    return "\n".join(lines)
