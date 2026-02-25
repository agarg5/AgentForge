"""Callback handler to track LLM vs tool execution time separately."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


class TimingCallback(BaseCallbackHandler):
    """Tracks cumulative LLM and tool execution time during an agent run."""

    def __init__(self) -> None:
        self.llm_total_seconds: float = 0.0
        self.tool_total_seconds: float = 0.0
        self._llm_starts: dict[UUID, float] = {}
        self._tool_starts: dict[UUID, float] = {}

    # --- LLM events ---
    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], *, run_id: UUID, **kwargs: Any
    ) -> None:
        self._llm_starts[run_id] = time.monotonic()

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._llm_starts.pop(run_id, None)
        if start is not None:
            self.llm_total_seconds += time.monotonic() - start

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._llm_starts.pop(run_id, None)
        if start is not None:
            self.llm_total_seconds += time.monotonic() - start

    # --- Tool events ---
    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, *, run_id: UUID, **kwargs: Any
    ) -> None:
        self._tool_starts[run_id] = time.monotonic()

    def on_tool_end(self, output: str, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._tool_starts.pop(run_id, None)
        if start is not None:
            self.tool_total_seconds += time.monotonic() - start

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._tool_starts.pop(run_id, None)
        if start is not None:
            self.tool_total_seconds += time.monotonic() - start

    def get_breakdown(self) -> dict[str, float]:
        """Return the timing breakdown as a dict."""
        return {
            "llm_seconds": round(self.llm_total_seconds, 3),
            "tool_seconds": round(self.tool_total_seconds, 3),
        }
