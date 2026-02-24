"""Shared test fixtures for agent tests."""

import pytest
import respx
import httpx

from src.client import GhostfolioClient
from src.memory import MemoryStore


BASE_URL = "http://ghostfolio.test"
AUTH_TOKEN = "test-token-123"


@pytest.fixture
def mock_api():
    """RESPX router scoped to the test Ghostfolio base URL."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture
async def client(mock_api):
    """GhostfolioClient wired to the mocked base URL."""
    async with GhostfolioClient(base_url=BASE_URL, auth_token=AUTH_TOKEN) as c:
        yield c


@pytest.fixture
def memory_store():
    """In-memory MemoryStore for testing (no Redis)."""
    return MemoryStore()


@pytest.fixture
def tool_config(client, memory_store):
    """RunnableConfig dict expected by LangChain tools."""
    return {
        "configurable": {
            "client": client,
            "memory": memory_store,
            "auth_token": AUTH_TOKEN,
        }
    }
