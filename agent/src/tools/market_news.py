from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

_ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

_VALID_TOPICS = [
    "blockchain",
    "earnings",
    "ipo",
    "mergers_and_acquisitions",
    "financial_markets",
    "economy_fiscal",
    "economy_monetary",
    "economy_macro",
    "energy_transportation",
    "finance",
    "life_sciences",
    "manufacturing",
    "real_estate",
    "retail_wholesale",
    "technology",
]


@tool
async def market_news(
    symbol: Optional[str] = None,
    topic: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Fetch recent financial news and market sentiment. Use this to provide
    context when users ask why their portfolio or a specific holding moved,
    or what's happening in the market. Returns headlines with sentiment scores.
    Always pair news insights with actual portfolio data — never give advice
    based on news alone.

    Args:
        symbol: Optional ticker symbol to filter news for (e.g. AAPL, MSFT).
        topic: Optional topic to filter news. Valid topics: blockchain,
               earnings, ipo, mergers_and_acquisitions, financial_markets,
               economy_fiscal, economy_monetary, economy_macro,
               energy_transportation, finance, life_sciences, manufacturing,
               real_estate, retail_wholesale, technology.
    """
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return (
            "Error: ALPHA_VANTAGE_API_KEY environment variable is not set. "
            "Please configure it to use the market news tool."
        )

    params: dict[str, str] = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key,
    }

    if symbol:
        params["tickers"] = symbol.upper()
    if topic:
        if topic.lower() not in _VALID_TOPICS:
            return (
                f"Error: Invalid topic '{topic}'. Valid topics are: "
                + ", ".join(_VALID_TOPICS)
            )
        params["topics"] = topic.lower()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(_ALPHA_VANTAGE_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return f"Error fetching news: HTTP {e.response.status_code}"
    except httpx.RequestError as e:
        return f"Error fetching news: {e}"
    except Exception as e:
        return f"Error fetching news: {e}"

    if "Error Message" in data:
        return f"Alpha Vantage API error: {data['Error Message']}"

    # Alpha Vantage returns "Note" or "Information" on rate limit (25/day free tier)
    if "Note" in data:
        return (
            "Market news is temporarily unavailable (API rate limit reached). "
            "Please try again later."
        )
    if "Information" in data:
        return (
            "Market news is temporarily unavailable (API rate limit reached). "
            "Please try again later."
        )

    feed = data.get("feed", [])
    if not feed:
        filter_desc = ""
        if symbol:
            filter_desc += f" for {symbol.upper()}"
        if topic:
            filter_desc += f" on topic '{topic}'"
        return f"No recent news found{filter_desc}."

    # Take top 5 articles
    articles = feed[:5]

    filter_label = "Market News"
    if symbol:
        filter_label = f"News for {symbol.upper()}"
    if topic:
        filter_label += f" ({topic})"

    lines = [f"**{filter_label}**\n"]

    # Markdown table
    lines.append("| Date | Headline | Source | Sentiment |")
    lines.append("|------|----------|--------|-----------|")

    for article in articles:
        title = article.get("title", "N/A").replace("|", "\\|")
        source = article.get("source", "N/A").replace("|", "\\|")
        sentiment = article.get("overall_sentiment_label", "N/A")
        time_published = article.get("time_published", "")

        # Parse date from "20231215T120000" format
        date_str = "N/A"
        if time_published:
            try:
                dt = datetime.strptime(time_published, "%Y%m%dT%H%M%S")
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                date_str = time_published[:10]

        lines.append(f"| {date_str} | {title} | {source} | {sentiment} |")

    # Article summaries
    lines.append("\n**Summaries:**")
    for i, article in enumerate(articles, 1):
        title = article.get("title", "N/A")
        summary = article.get("summary", "No summary available.")
        score = article.get("overall_sentiment_score", "N/A")
        lines.append(f"{i}. **{title}** (sentiment score: {score})")
        lines.append(f"   {summary}")

        # Per-ticker sentiment if symbol was provided
        if symbol:
            ticker_sentiments = article.get("ticker_sentiment", [])
            for ts in ticker_sentiments:
                if ts.get("ticker", "").upper() == symbol.upper():
                    relevance = ts.get("relevance_score", "N/A")
                    ticker_label = ts.get("ticker_sentiment_label", "N/A")
                    lines.append(
                        f"   *{symbol.upper()} sentiment: {ticker_label} "
                        f"(relevance: {relevance})*"
                    )
                    break

    return "\n".join(lines)
