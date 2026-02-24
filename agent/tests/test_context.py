"""Tests for sliding window context management."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.main import MAX_HISTORY_MESSAGES, trim_messages


class TestTrimMessages:
    def test_no_trim_when_under_limit(self):
        messages = [HumanMessage(content=f"msg-{i}") for i in range(10)]
        result = trim_messages(messages)
        assert len(result) == 10
        assert result is messages  # same list, no copy

    def test_no_trim_at_exact_limit(self):
        messages = [HumanMessage(content=f"msg-{i}") for i in range(MAX_HISTORY_MESSAGES)]
        result = trim_messages(messages)
        assert len(result) == MAX_HISTORY_MESSAGES

    def test_trims_oldest_messages(self):
        count = MAX_HISTORY_MESSAGES + 20
        messages = [HumanMessage(content=f"msg-{i}") for i in range(count)]
        result = trim_messages(messages)
        assert len(result) == MAX_HISTORY_MESSAGES
        # Should keep the most recent messages
        assert result[0].content == f"msg-{count - MAX_HISTORY_MESSAGES}"
        assert result[-1].content == f"msg-{count - 1}"

    def test_custom_max(self):
        messages = [HumanMessage(content=f"msg-{i}") for i in range(10)]
        result = trim_messages(messages, max_messages=5)
        assert len(result) == 5
        assert result[0].content == "msg-5"
        assert result[-1].content == "msg-9"

    def test_preserves_message_types(self):
        messages = [
            HumanMessage(content="user-1"),
            AIMessage(content="agent-1"),
            HumanMessage(content="user-2"),
            AIMessage(content="agent-2"),
            HumanMessage(content="user-3"),
        ]
        result = trim_messages(messages, max_messages=3)
        assert len(result) == 3
        # Last 3: user-2, agent-2, user-3
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)
        assert isinstance(result[2], HumanMessage)
        assert result[0].content == "user-2"

    def test_empty_list(self):
        assert trim_messages([]) == []

    def test_single_message(self):
        messages = [HumanMessage(content="only")]
        result = trim_messages(messages, max_messages=1)
        assert len(result) == 1
        assert result[0].content == "only"
