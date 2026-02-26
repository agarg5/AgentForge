"""Tests for all LangChain agent tools."""

import httpx
import pytest

from src.tools.portfolio import portfolio_analysis
from src.tools.transactions import transaction_history
from src.tools.market_data import market_data
from src.tools.risk_assessment import risk_assessment
from src.tools.benchmark import benchmark_comparison
from src.tools.dividends import dividend_analysis
from src.tools.accounts import account_summary
from src.tools.create_order import create_order
from src.tools.delete_order import delete_order


# ---------------------------------------------------------------------------
# portfolio_analysis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_analysis_success(mock_api, tool_config):
    mock_api.get("/api/v1/portfolio/details").mock(
        return_value=httpx.Response(200, json={
            "holdings": [
                {"name": "Apple", "symbol": "AAPL", "allocationInPercentage": 0.6, "value": 6000, "currency": "USD"},
                {"name": "Google", "symbol": "GOOG", "allocationInPercentage": 0.4, "value": 4000, "currency": "USD"},
            ]
        })
    )
    mock_api.get("/api/v2/portfolio/performance").mock(
        return_value=httpx.Response(200, json={
            "performance": {"currentValue": 10000, "currency": "USD", "netPerformancePercentage": 0.15}
        })
    )
    result = await portfolio_analysis.ainvoke({"range": "1y"}, config=tool_config)
    assert "10000" in result
    assert "AAPL" in result
    assert "GOOG" in result


@pytest.mark.asyncio
async def test_portfolio_analysis_empty(mock_api, tool_config):
    mock_api.get("/api/v1/portfolio/details").mock(
        return_value=httpx.Response(200, json={"holdings": {}})
    )
    mock_api.get("/api/v2/portfolio/performance").mock(
        return_value=httpx.Response(200, json={"performance": {}})
    )
    result = await portfolio_analysis.ainvoke({}, config=tool_config)
    assert "No holdings" in result


@pytest.mark.asyncio
async def test_portfolio_analysis_error(mock_api, tool_config):
    mock_api.get("/api/v1/portfolio/details").mock(
        return_value=httpx.Response(500, text="Server Error")
    )
    result = await portfolio_analysis.ainvoke({}, config=tool_config)
    assert "Error" in result


# ---------------------------------------------------------------------------
# transaction_history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transaction_history_success(mock_api, tool_config):
    mock_api.get("/api/v1/order").mock(
        return_value=httpx.Response(200, json={
            "activities": [
                {
                    "id": "tx-1", "type": "BUY", "date": "2024-06-01T00:00:00Z",
                    "quantity": 10, "unitPrice": 150, "fee": 5,
                    "SymbolProfile": {"symbol": "AAPL", "currency": "USD"},
                }
            ]
        })
    )
    result = await transaction_history.ainvoke({}, config=tool_config)
    assert "AAPL" in result
    assert "BUY" in result
    assert "tx-1" in result


@pytest.mark.asyncio
async def test_transaction_history_empty(mock_api, tool_config):
    mock_api.get("/api/v1/order").mock(
        return_value=httpx.Response(200, json={"activities": []})
    )
    result = await transaction_history.ainvoke({}, config=tool_config)
    assert "No transactions" in result


@pytest.mark.asyncio
async def test_transaction_history_error(mock_api, tool_config):
    mock_api.get("/api/v1/order").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )
    result = await transaction_history.ainvoke({}, config=tool_config)
    assert "Error" in result


# ---------------------------------------------------------------------------
# market_data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_market_data_direct_lookup(mock_api, tool_config):
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(200, json={
            "symbol": "AAPL", "name": "Apple Inc.", "marketPrice": 195.5,
            "currency": "USD", "assetClass": "EQUITY", "assetSubClass": "STOCK",
            "sectors": [{"name": "Technology"}],
        })
    )
    result = await market_data.ainvoke({"query": "AAPL"}, config=tool_config)
    assert "Apple Inc." in result
    assert "195.5" in result


@pytest.mark.asyncio
async def test_market_data_fallback_to_search(mock_api, tool_config):
    mock_api.get("/api/v1/symbol/YAHOO/APPLE").mock(
        return_value=httpx.Response(404, json={})
    )
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(200, json={
            "items": [
                {"symbol": "AAPL", "name": "Apple Inc.", "dataSource": "YAHOO", "currency": "USD"}
            ]
        })
    )
    result = await market_data.ainvoke({"query": "apple"}, config=tool_config)
    assert "AAPL" in result
    assert "Apple Inc." in result


@pytest.mark.asyncio
async def test_market_data_not_found(mock_api, tool_config):
    mock_api.get("/api/v1/symbol/YAHOO/ZZZZZ").mock(
        return_value=httpx.Response(404, json={})
    )
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    result = await market_data.ainvoke({"query": "ZZZZZ"}, config=tool_config)
    assert "No results" in result


# ---------------------------------------------------------------------------
# risk_assessment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_risk_assessment_success(mock_api, tool_config):
    mock_api.get("/api/v1/portfolio/report").mock(
        return_value=httpx.Response(200, json={
            "rules": {
                "currency_cluster_risk": [
                    {"name": "USD Concentration", "isActive": True, "value": "85%"},
                    {"name": "EUR Exposure", "isActive": False, "value": "15%"},
                ]
            }
        })
    )
    result = await risk_assessment.ainvoke({}, config=tool_config)
    assert "USD Concentration" in result
    assert "PASS" in result
    assert "WARN" in result


@pytest.mark.asyncio
async def test_risk_assessment_empty(mock_api, tool_config):
    mock_api.get("/api/v1/portfolio/report").mock(
        return_value=httpx.Response(200, json={"rules": {}})
    )
    result = await risk_assessment.ainvoke({}, config=tool_config)
    assert "No risk analysis" in result


# ---------------------------------------------------------------------------
# benchmark_comparison
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_benchmark_comparison_success(mock_api, tool_config):
    mock_api.get("/api/v1/benchmarks").mock(
        return_value=httpx.Response(200, json=[
            {"name": "S&P 500", "symbol": "SPY", "performances": {"1y": {"performancePercent": 0.22}}}
        ])
    )
    mock_api.get("/api/v2/portfolio/performance").mock(
        return_value=httpx.Response(200, json={
            "performance": {"netPerformancePercentage": 0.18}
        })
    )
    result = await benchmark_comparison.ainvoke({"range": "1y"}, config=tool_config)
    assert "S&P 500" in result
    assert "SPY" in result
    assert "Your Portfolio" in result


@pytest.mark.asyncio
async def test_benchmark_comparison_no_benchmarks(mock_api, tool_config):
    mock_api.get("/api/v1/benchmarks").mock(
        return_value=httpx.Response(200, json=[])
    )
    mock_api.get("/api/v2/portfolio/performance").mock(
        return_value=httpx.Response(200, json={"performance": {}})
    )
    result = await benchmark_comparison.ainvoke({}, config=tool_config)
    assert "No benchmarks" in result


# ---------------------------------------------------------------------------
# dividend_analysis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dividend_analysis_success(mock_api, tool_config):
    mock_api.get("/api/v1/portfolio/dividends").mock(
        return_value=httpx.Response(200, json={
            "dividends": [
                {"date": "2024-06-15", "investment": 50.0},
                {"date": "2024-03-15", "investment": 45.0},
            ]
        })
    )
    result = await dividend_analysis.ainvoke({}, config=tool_config)
    assert "95.00" in result  # total dividends


@pytest.mark.asyncio
async def test_dividend_analysis_empty(mock_api, tool_config):
    mock_api.get("/api/v1/portfolio/dividends").mock(
        return_value=httpx.Response(200, json={"dividends": []})
    )
    result = await dividend_analysis.ainvoke({}, config=tool_config)
    assert "No dividend data" in result


# ---------------------------------------------------------------------------
# account_summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_account_summary_success(mock_api, tool_config):
    mock_api.get("/api/v1/account").mock(
        return_value=httpx.Response(200, json=[
            {"name": "Brokerage", "balance": 500, "value": 15000, "currency": "USD",
             "Platform": {"name": "Interactive Brokers"}},
        ])
    )
    result = await account_summary.ainvoke({}, config=tool_config)
    assert "Brokerage" in result
    assert "Interactive Brokers" in result
    assert "15,000.00" in result


@pytest.mark.asyncio
async def test_account_summary_empty(mock_api, tool_config):
    mock_api.get("/api/v1/account").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await account_summary.ainvoke({}, config=tool_config)
    assert "No accounts" in result


# ---------------------------------------------------------------------------
# create_order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_success(mock_api, tool_config):
    # Ticker verification
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(200, json={"symbol": "AAPL", "name": "Apple"})
    )
    # Order creation
    mock_api.post("/api/v1/order").mock(
        return_value=httpx.Response(201, json={"id": "order-abc"})
    )
    result = await create_order.ainvoke({
        "symbol": "AAPL",
        "order_type": "BUY",
        "quantity": 10,
        "unit_price": 150.0,
        "currency": "USD",
        "date": "2024-06-01T00:00:00Z",
    }, config=tool_config)
    assert "Order created successfully" in result
    assert "order-abc" in result


@pytest.mark.asyncio
async def test_create_order_invalid_quantity(mock_api, tool_config):
    result = await create_order.ainvoke({
        "symbol": "AAPL",
        "order_type": "BUY",
        "quantity": -5,
        "unit_price": 150.0,
        "currency": "USD",
        "date": "2024-06-01T00:00:00Z",
    }, config=tool_config)
    assert "quantity must be positive" in result


@pytest.mark.asyncio
async def test_create_order_invalid_price(mock_api, tool_config):
    result = await create_order.ainvoke({
        "symbol": "AAPL",
        "order_type": "BUY",
        "quantity": 10,
        "unit_price": -1,
        "currency": "USD",
        "date": "2024-06-01T00:00:00Z",
    }, config=tool_config)
    assert "unit_price must be non-negative" in result


@pytest.mark.asyncio
async def test_create_order_invalid_type(mock_api, tool_config):
    result = await create_order.ainvoke({
        "symbol": "AAPL",
        "order_type": "YOLO",
        "quantity": 10,
        "unit_price": 150.0,
        "currency": "USD",
        "date": "2024-06-01T00:00:00Z",
    }, config=tool_config)
    assert "invalid order type" in result


@pytest.mark.asyncio
async def test_create_order_invalid_symbol(mock_api, tool_config):
    """Order creation blocked when symbol verification fails."""
    mock_api.get("/api/v1/symbol/YAHOO/FAKESYM").mock(
        return_value=httpx.Response(404, json={})
    )
    mock_api.get("/api/v1/symbol/lookup").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    result = await create_order.ainvoke({
        "symbol": "FAKESYM",
        "order_type": "BUY",
        "quantity": 10,
        "unit_price": 100.0,
        "currency": "USD",
        "date": "2024-06-01T00:00:00Z",
    }, config=tool_config)
    assert "Error" in result
    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_create_order_api_error(mock_api, tool_config):
    """HTTP error from order API returns friendly error."""
    mock_api.get("/api/v1/symbol/YAHOO/AAPL").mock(
        return_value=httpx.Response(200, json={"symbol": "AAPL"})
    )
    mock_api.post("/api/v1/order").mock(
        return_value=httpx.Response(400, text="Bad Request")
    )
    result = await create_order.ainvoke({
        "symbol": "AAPL",
        "order_type": "BUY",
        "quantity": 10,
        "unit_price": 150.0,
        "currency": "USD",
        "date": "2024-06-01T00:00:00Z",
    }, config=tool_config)
    assert "Error creating order" in result


# ---------------------------------------------------------------------------
# delete_order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_order_success(mock_api, tool_config):
    mock_api.delete("/api/v1/order/order-123").mock(
        return_value=httpx.Response(204)
    )
    result = await delete_order.ainvoke({"order_id": "order-123"}, config=tool_config)
    assert "deleted successfully" in result


@pytest.mark.asyncio
async def test_delete_order_not_found(mock_api, tool_config):
    mock_api.delete("/api/v1/order/nonexistent").mock(
        return_value=httpx.Response(404, text="Not found")
    )
    result = await delete_order.ainvoke({"order_id": "nonexistent"}, config=tool_config)
    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_delete_order_empty_id(mock_api, tool_config):
    result = await delete_order.ainvoke({"order_id": ""}, config=tool_config)
    assert "order_id is required" in result
