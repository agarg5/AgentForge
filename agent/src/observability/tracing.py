"""LangSmith tracing configuration.

Tracing is automatically enabled when these env vars are set:
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_API_KEY=<key>
  LANGCHAIN_PROJECT=<project>

This module provides helpers for per-request run configuration
(metadata, tags, run names) so traces are searchable in the dashboard.
"""

from __future__ import annotations

import os
import uuid

_TRACING_ENABLED: bool | None = None


def configure_tracing() -> bool:
    """Check if LangSmith tracing is properly configured.

    Returns True if tracing is active, False otherwise.
    Called once at startup to log status.
    """
    global _TRACING_ENABLED
    enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    has_key = bool(os.getenv("LANGCHAIN_API_KEY"))
    _TRACING_ENABLED = enabled and has_key
    return _TRACING_ENABLED


def is_tracing_enabled() -> bool:
    if _TRACING_ENABLED is None:
        return configure_tracing()
    return _TRACING_ENABLED


def get_run_config(
    *,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    """Build a LangChain RunnableConfig with LangSmith metadata.

    Args:
        session_id: Groups traces into a conversation thread.
        tags: Filterable tags (e.g. ["production", "portfolio"]).
        metadata: Arbitrary key-value pairs attached to the trace.

    Returns:
        A config dict compatible with agent.ainvoke(..., config=config).
    """
    run_id = str(uuid.uuid4())

    config: dict = {
        "run_id": run_id,
        "run_name": "agentforge-chat",
    }

    all_tags = ["agentforge"]
    if tags:
        all_tags.extend(tags)
    config["tags"] = all_tags

    all_metadata = {"run_id": run_id}
    if session_id:
        all_metadata["session_id"] = session_id
    if metadata:
        all_metadata.update(metadata)
    config["metadata"] = all_metadata

    return config
