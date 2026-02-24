"""Tests for GhostfolioClient."""

import httpx
import pytest
import respx

from src.client import GhostfolioAPIError, GhostfolioClient

BASE_URL = "http://ghostfolio.test"
AUTH_TOKEN = "test-token-123"


@pytest.mark.asyncio
async def test_client_context_manager():
    """Client can be used as an async context manager."""
    async with GhostfolioClient(base_url=BASE_URL, auth_token=AUTH_TOKEN) as c:
        assert c._http is not None
    # After exit, the underlying client should be closed
    assert c._http.is_closed


@pytest.mark.asyncio
async def test_client_sends_auth_header(mock_api, client):
    mock_api.get("/api/v1/account").mock(
        return_value=httpx.Response(200, json={"accounts": []})
    )
    await client.get_accounts()
    req = mock_api.calls[0].request
    assert req.headers["authorization"] == f"Bearer {AUTH_TOKEN}"


@pytest.mark.asyncio
async def test_get_portfolio_details(mock_api, client):
    mock_api.get("/api/v1/portfolio/details").mock(
        return_value=httpx.Response(200, json={"holdings": {"AAPL": {"symbol": "AAPL"}}})
    )
    result = await client.get_portfolio_details(range="1y")
    assert "holdings" in result
    assert "AAPL" in result["holdings"]


@pytest.mark.asyncio
async def test_get_transactions(mock_api, client):
    mock_api.get("/api/v1/order").mock(
        return_value=httpx.Response(200, json={"activities": [{"id": "1", "type": "BUY"}]})
    )
    result = await client.get_transactions(take=10)
    assert len(result["activities"]) == 1


@pytest.mark.asyncio
async def test_symbol_lookup(mock_api, client):
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(200, json={"items": [{"symbol": "AAPL"}]})
    )
    result = await client.symbol_lookup("AAPL")
    assert result["items"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_get_symbol_profile(mock_api, client):
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(200, json={"symbol": "AAPL", "name": "Apple Inc."})
    )
    result = await client.get_symbol_profile("YAHOO", "AAPL")
    assert result["name"] == "Apple Inc."


@pytest.mark.asyncio
async def test_get_symbol_profile_404(mock_api, client):
    mock_api.get("/api/v1/symbol/YAHOO/FAKE").mock(
        return_value=httpx.Response(404, json={"message": "Not found"})
    )
    with pytest.raises(GhostfolioAPIError) as exc_info:
        await client.get_symbol_profile("YAHOO", "FAKE")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_order(mock_api, client):
    mock_api.post("/api/v1/order").mock(
        return_value=httpx.Response(201, json={"id": "order-123"})
    )
    result = await client.create_order({"symbol": "AAPL", "type": "BUY"})
    assert result["id"] == "order-123"


@pytest.mark.asyncio
async def test_delete_order_204(mock_api, client):
    mock_api.delete("/api/v1/order/order-123").mock(
        return_value=httpx.Response(204)
    )
    result = await client.delete_order("order-123")
    assert result == {}


@pytest.mark.asyncio
async def test_delete_order_with_body(mock_api, client):
    mock_api.delete("/api/v1/order/order-456").mock(
        return_value=httpx.Response(200, json={"id": "order-456", "type": "BUY"})
    )
    result = await client.delete_order("order-456")
    assert result["id"] == "order-456"


@pytest.mark.asyncio
async def test_raises_on_server_error(mock_api, client):
    mock_api.get("/api/v1/account").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(GhostfolioAPIError) as exc_info:
        await client.get_accounts()
    assert exc_info.value.status_code == 500
