"""Tests for ticker symbol verification."""

import httpx
import pytest

from src.verification.ticker import verify_ticker

BASE_URL = "http://ghostfolio.test"


@pytest.mark.asyncio
async def test_valid_symbol_via_profile(mock_api, client):
    """Symbol found directly via profile lookup."""
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(200, json={"symbol": "AAPL", "name": "Apple Inc."})
    )
    valid, reason = await verify_ticker(client, "AAPL")
    assert valid is True
    assert reason == ""


@pytest.mark.asyncio
async def test_valid_symbol_case_insensitive(mock_api, client):
    """Symbol lookup normalizes to uppercase."""
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(200, json={"symbol": "AAPL", "name": "Apple Inc."})
    )
    valid, reason = await verify_ticker(client, "aapl")
    assert valid is True


@pytest.mark.asyncio
async def test_invalid_symbol_not_found(mock_api, client):
    """Symbol not found in profile or search."""
    mock_api.get("/api/v1/symbol/YAHOO/FAKESYM").mock(
        return_value=httpx.Response(404, json={})
    )
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    valid, reason = await verify_ticker(client, "FAKESYM")
    assert valid is False
    assert "not found" in reason.lower()


@pytest.mark.asyncio
async def test_symbol_found_via_search_fallback(mock_api, client):
    """Symbol not in profile but found via search."""
    mock_api.get("/api/v1/symbol/YAHOO/VTI").mock(
        return_value=httpx.Response(404, json={})
    )
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(200, json={"items": [
            {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "dataSource": "YAHOO"}
        ]})
    )
    valid, reason = await verify_ticker(client, "VTI")
    assert valid is True


@pytest.mark.asyncio
async def test_symbol_suggestions_on_close_match(mock_api, client):
    """Similar symbols found but not exact match — suggest alternatives."""
    mock_api.get("/api/v1/symbol/YAHOO/APPL").mock(
        return_value=httpx.Response(404, json={})
    )
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(200, json={"items": [
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "APLE", "name": "Apple Hospitality REIT"},
        ]})
    )
    valid, reason = await verify_ticker(client, "APPL")
    assert valid is False
    assert "Did you mean" in reason
    assert "AAPL" in reason


@pytest.mark.asyncio
async def test_empty_symbol():
    """Empty symbol is rejected immediately without API calls."""
    from src.client import GhostfolioClient

    # Client won't be called, but we need one for the signature
    client = GhostfolioClient(base_url="http://unused", auth_token="unused")
    try:
        valid, reason = await verify_ticker(client, "")
        assert valid is False
        assert "empty" in reason.lower()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_whitespace_symbol():
    """Whitespace-only symbol is rejected."""
    from src.client import GhostfolioClient

    client = GhostfolioClient(base_url="http://unused", auth_token="unused")
    try:
        valid, reason = await verify_ticker(client, "   ")
        assert valid is False
        assert "empty" in reason.lower()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_non_404_error_returns_error(mock_api, client):
    """Non-404 HTTP error returns False with error message."""
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    valid, reason = await verify_ticker(client, "AAPL")
    assert valid is False
    assert "500" in reason


@pytest.mark.asyncio
async def test_search_failure_allows_through(mock_api, client):
    """If both profile and search fail, allow through (don't block on network errors)."""
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(404, json={})
    )
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(500, text="Server Error")
    )
    valid, reason = await verify_ticker(client, "AAPL")
    assert valid is True  # Fail-open: don't block orders due to search outage
