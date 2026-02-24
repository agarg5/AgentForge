from __future__ import annotations

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioClient


@tool
async def risk_assessment(
    *,
    config: RunnableConfig,
) -> str:
    """Analyze portfolio risk using Ghostfolio's X-Ray analysis. Returns
    risk warnings about concentration, currency exposure, fees, and
    diversification issues.

    No arguments needed — analyzes the current portfolio.
    """
    client: GhostfolioClient = config["configurable"]["client"]

    try:
        report = await client.get_portfolio_report()
    except httpx.HTTPStatusError as e:
        return f"Error fetching risk report: {e.response.status_code} — {e.response.text}"
    rules = report.get("rules", {})

    if not rules:
        return "No risk analysis data available."

    lines = ["**Portfolio Risk Assessment (X-Ray)**\n"]

    for category, category_rules in rules.items():
        category_label = category.replace("_", " ").title()
        lines.append(f"### {category_label}\n")

        if not category_rules:
            lines.append("No rules evaluated.\n")
            continue

        lines.append("| Rule | Status | Value |")
        lines.append("|------|--------|-------|")

        for rule in category_rules:
            name = rule.get("name", "Unknown")
            is_active = rule.get("isActive", False)
            value = rule.get("value", "N/A")
            status = "PASS" if is_active else "WARN"
            lines.append(f"| {name} | {status} | {value} |")

        lines.append("")

    return "\n".join(lines)
