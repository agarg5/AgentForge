"""Tools for reading and writing persistent user preferences.

Preferences persist across chat sessions via Redis, allowing the agent
to remember user choices like preferred currency, risk tolerance, etc.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..memory import MemoryStore


@tool
async def get_user_preferences(
    key: Optional[str] = None,
    *,
    config: RunnableConfig,
) -> str:
    """Retrieve saved user preferences. Returns all preferences if no key
    is specified, or a single preference value if a key is given.

    Use this at the start of a conversation to personalize responses
    based on previously saved preferences (e.g., preferred currency,
    risk tolerance, favorite holdings).

    Args:
        key: Optional specific preference key to retrieve.
             If not provided, returns all saved preferences.
    """
    store: MemoryStore = config["configurable"]["memory"]
    auth_token: str = config["configurable"]["auth_token"]

    if key:
        value = await store.get(auth_token, key)
        if value is None:
            return f"No preference saved for '{key}'."
        return f"Preference '{key}': {value}"

    prefs = await store.get_all(auth_token)
    if not prefs:
        return "No preferences saved yet."

    lines = ["**Saved Preferences:**\n"]
    for k, v in sorted(prefs.items()):
        lines.append(f"- **{k}**: {v}")
    return "\n".join(lines)


@tool
async def save_user_preference(
    key: str,
    value: str,
    *,
    config: RunnableConfig,
) -> str:
    """Save a user preference that persists across chat sessions.

    Use this when the user explicitly asks you to remember something,
    or when they express a clear preference (e.g., "I prefer USD",
    "my risk tolerance is moderate", "always show me tech stocks first").

    Common preference keys:
    - preferred_currency: User's preferred display currency (e.g., "USD", "EUR")
    - risk_tolerance: low, moderate, or high
    - favorite_symbols: Comma-separated list of tickers they track
    - display_format: How they prefer data shown (e.g., "tables", "brief")
    - investment_goal: Their stated investment objective

    Args:
        key: The preference key (e.g., "preferred_currency").
        value: The preference value (e.g., "USD").
    """
    store: MemoryStore = config["configurable"]["memory"]
    auth_token: str = config["configurable"]["auth_token"]

    await store.set(auth_token, key, value)
    return f"Preference saved: {key} = {value}"


@tool
async def delete_user_preference(
    key: str,
    *,
    config: RunnableConfig,
) -> str:
    """Delete a saved user preference.

    Use this when the user asks you to forget a preference or reset
    a setting.

    Args:
        key: The preference key to delete.
    """
    store: MemoryStore = config["configurable"]["memory"]
    auth_token: str = config["configurable"]["auth_token"]

    await store.delete(auth_token, key)
    return f"Preference '{key}' deleted."
