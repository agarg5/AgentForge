import httpx


class GhostfolioClient:
    """Async client for the Ghostfolio REST API."""

    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {auth_token}"}

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
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/portfolio/details",
                headers=self._headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_portfolio_performance(
        self, range: str = "max", filters: dict | None = None
    ) -> dict:
        params = self._build_params(range, filters)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v2/portfolio/performance",
                headers=self._headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
