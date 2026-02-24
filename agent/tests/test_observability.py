"""Tests for the observability module."""

import os

import pytest

from src.observability.tracing import configure_tracing, get_run_config, is_tracing_enabled
from src.observability.metrics import extract_metrics


class TestConfigureTracing:
    def test_enabled_when_env_set(self, monkeypatch):
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_test_key")
        assert configure_tracing() is True

    def test_disabled_when_no_key(self, monkeypatch):
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
        monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
        assert configure_tracing() is False

    def test_disabled_when_tracing_off(self, monkeypatch):
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_test_key")
        assert configure_tracing() is False

    def test_disabled_when_no_env(self, monkeypatch):
        monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
        monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
        assert configure_tracing() is False


class TestGetRunConfig:
    def test_basic_config(self):
        config = get_run_config()
        assert "run_id" in config
        assert config["run_name"] == "agentforge-chat"
        assert "agentforge" in config["tags"]
        assert "run_id" in config["metadata"]

    def test_with_session_id(self):
        config = get_run_config(session_id="session-abc")
        assert config["metadata"]["session_id"] == "session-abc"

    def test_with_tags(self):
        config = get_run_config(tags=["chat", "production"])
        assert "chat" in config["tags"]
        assert "production" in config["tags"]
        assert "agentforge" in config["tags"]

    def test_with_metadata(self):
        config = get_run_config(metadata={"user": "test"})
        assert config["metadata"]["user"] == "test"

    def test_unique_run_ids(self):
        c1 = get_run_config()
        c2 = get_run_config()
        assert c1["run_id"] != c2["run_id"]


class TestExtractMetrics:
    def test_empty_result(self):
        metrics = extract_metrics({"messages": []})
        assert metrics["total_tokens"] == 0
        assert metrics["tool_call_count"] == 0
        assert metrics["tools_used"] == []
        assert metrics["message_count"] == 0

    def test_with_token_usage(self):
        class FakeAIMessage:
            response_metadata = {
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                }
            }
            tool_calls = None

        metrics = extract_metrics({"messages": [FakeAIMessage()]})
        assert metrics["input_tokens"] == 100
        assert metrics["output_tokens"] == 50
        assert metrics["total_tokens"] == 150

    def test_with_tool_calls(self):
        class FakeAIMessage:
            response_metadata = {"token_usage": {}}
            tool_calls = [
                {"name": "portfolio_analysis"},
                {"name": "market_data"},
            ]

        metrics = extract_metrics({"messages": [FakeAIMessage()]})
        assert metrics["tool_call_count"] == 2
        assert metrics["tools_used"] == ["portfolio_analysis", "market_data"]

    def test_multiple_messages(self):
        class Msg1:
            response_metadata = {
                "token_usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75}
            }
            tool_calls = [{"name": "market_data"}]

        class Msg2:
            response_metadata = {
                "token_usage": {"prompt_tokens": 80, "completion_tokens": 40, "total_tokens": 120}
            }
            tool_calls = None

        metrics = extract_metrics({"messages": [Msg1(), Msg2()]})
        assert metrics["input_tokens"] == 130
        assert metrics["output_tokens"] == 65
        assert metrics["total_tokens"] == 195
        assert metrics["tool_call_count"] == 1
        assert metrics["message_count"] == 2
