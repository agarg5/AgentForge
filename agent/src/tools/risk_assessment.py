from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..client import GhostfolioAPIError, GhostfolioClient


@tool
async def risk_assessment(
    *,
    config: RunnableConfig,
) -> str:
    """Analyze portfolio risk using Ghostfolio's X-Ray analysis. Returns a
    risk score (e.g. "8 of 12 rules passed"), detailed evaluation text for
    each rule explaining what it checks and the result, and a summary of
    key warnings the user should act on.

    Covers concentration risk, currency exposure, fees, emergency fund,
    and diversification issues.

    No arguments needed — analyzes the current portfolio.
    """
    client: GhostfolioClient = config["configurable"]["client"]

    try:
        report = await client.get_portfolio_report()
    except GhostfolioAPIError as e:
        return f"Error fetching risk report: {e}"
    rules = report.get("rules", {})

    if not rules:
        return "No risk analysis data available."

    # Collect all rules across categories for summary scoring
    total_rules = 0
    passed_rules = 0
    warnings: list[dict] = []

    lines = ["**Portfolio Risk Assessment (X-Ray)**\n"]

    # First pass: count totals and collect warnings
    for _category, category_rules in rules.items():
        if not category_rules:
            continue
        for rule in category_rules:
            total_rules += 1
            value = rule.get("value", False)
            if value:
                passed_rules += 1
            else:
                warnings.append(rule)

    # Summary score
    lines.append(
        f"**Risk Score: {passed_rules} of {total_rules} rules passed**\n"
    )

    # Detailed breakdown per category
    for category, category_rules in rules.items():
        category_label = category.replace("_", " ").title()
        lines.append(f"### {category_label}\n")

        if not category_rules:
            lines.append("No rules evaluated.\n")
            continue

        lines.append("| Rule | Status | Details |")
        lines.append("|------|--------|---------|")

        for rule in category_rules:
            name = rule.get("name", "Unknown")
            value = rule.get("value", False)
            evaluation = rule.get("evaluation", "")
            status = "PASS" if value else "WARN"
            details = evaluation if evaluation else "No details available"
            # Escape pipe characters in details to avoid breaking the table
            details = details.replace("|", "\\|")
            lines.append(f"| {name} | {status} | {details} |")

        lines.append("")

    # Key Warnings section
    if warnings:
        lines.append("### Key Warnings\n")
        for rule in warnings:
            name = rule.get("name", "Unknown")
            evaluation = rule.get("evaluation", "No details available")
            lines.append(f"- **{name}**: {evaluation}")
        lines.append("")
    else:
        lines.append("All rules passed — no warnings.\n")

    return "\n".join(lines)
