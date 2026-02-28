import logging

import httpx

logger = logging.getLogger("agentforge.client")


class GhostfolioAPIError(Exception):
    """Raised when a Ghostfolio API call fails for any reason."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class GhostfolioClient:
    """Async client for the Ghostfolio REST API.

    Reuses a single httpx.AsyncClient for connection pooling.
    Call close() when done, or use as an async context manager.
    """

    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15,
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make an HTTP request with unified error handling."""
        try:
            resp = await self._http.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.TimeoutException:
            logger.error("Timeout: %s %s", method, path)
            raise GhostfolioAPIError(f"Request timed out: {method} {path}")
        except httpx.ConnectError as e:
            logger.error("Connection error: %s %s — %s", method, path, e)
            raise GhostfolioAPIError(f"Cannot connect to Ghostfolio: {e}")
        except httpx.HTTPStatusError as e:
            logger.warning(
                "HTTP %d: %s %s", e.response.status_code, method, path
            )
            raise GhostfolioAPIError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
            )

    async def close(self):
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    def _build_params(
        self, range: str | None = None, filters: dict | None = None
    ) -> dict:
        params = {}
        if range:
            params["range"] = range
        if filters:
            for key in ("accounts", "assetClasses", "dataSource", "symbol", "tags"):
                if key in filters:
                    params[key] = filters[key]
        return params

    async def get_portfolio_details(
        self, range: str | None = None, filters: dict | None = None
    ) -> dict:
        params = self._build_params(range, filters)
        resp = await self._request("GET", "/api/v1/portfolio/details", params=params)
        return resp.json()

    async def get_transactions(
        self,
        accounts: str | None = None,
        asset_classes: str | None = None,
        tags: str | None = None,
        skip: int | None = None,
        take: int | None = None,
    ) -> dict:
        params = {}
        if accounts:
            params["accounts"] = accounts
        if asset_classes:
            params["assetClasses"] = asset_classes
        if tags:
            params["tags"] = tags
        if skip is not None:
            params["skip"] = skip
        if take is not None:
            params["take"] = take
        resp = await self._request("GET", "/api/v1/order", params=params)
        return resp.json()

    async def get_portfolio_performance(
        self, range: str = "max", filters: dict | None = None
    ) -> dict:
        params = self._build_params(range, filters)
        resp = await self._request("GET", "/api/v2/portfolio/performance", params=params)
        return resp.json()

    async def symbol_lookup(self, query: str) -> dict:
        resp = await self._request("GET", "/api/v1/symbol/lookup", params={"query": query})
        return resp.json()

    async def get_symbol_profile(
        self, data_source: str, symbol: str
    ) -> dict:
        resp = await self._request("GET", f"/api/v1/symbol/{data_source}/{symbol}")
        return resp.json()

    async def get_portfolio_report(self) -> dict:
        resp = await self._request("GET", "/api/v1/portfolio/report")
        return resp.json()

    async def get_benchmarks(self) -> list:
        resp = await self._request("GET", "/api/v1/benchmarks")
        data = resp.json()
        return data.get("benchmarks", []) if isinstance(data, dict) else data

    async def get_dividends(
        self, range: str = "max", filters: dict | None = None
    ) -> dict:
        params = self._build_params(range, filters)
        resp = await self._request("GET", "/api/v1/portfolio/dividends", params=params)
        return resp.json()

    async def get_accounts(self) -> dict:
        resp = await self._request("GET", "/api/v1/account")
        return resp.json()

    async def create_order(self, order_data: dict) -> dict:
        resp = await self._request("POST", "/api/v1/order", json=order_data)
        return resp.json()

    async def delete_order(self, order_id: str) -> dict:
        resp = await self._request("DELETE", f"/api/v1/order/{order_id}")
        if resp.status_code == 204:
            return {}
        return resp.json()
