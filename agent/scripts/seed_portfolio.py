#!/usr/bin/env python3
"""Seed a Ghostfolio instance with realistic fake portfolio data.

Creates ~35 BUY orders across US large caps, ETFs, and individual stocks
spread over 2021-2025 to simulate an organic investment history. Useful
for exercising the AgentForge agent tools (portfolio_analysis,
transaction_history, market_data, etc.).

Usage:
    # Against local Ghostfolio
    export GHOSTFOLIO_ACCESS_TOKEN="your-security-token"
    python seed_portfolio.py

    # Against Railway deployment
    python seed_portfolio.py --base-url https://ghostfolio-production-574b.up.railway.app

    # Preview without making API calls
    python seed_portfolio.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass

import httpx

# ---------------------------------------------------------------------------
# Portfolio definition
# ---------------------------------------------------------------------------

@dataclass
class Order:
    symbol: str
    date: str  # ISO 8601, e.g. "2021-03-15T00:00:00.000Z"
    quantity: float
    unit_price: float
    fee: float = 0.0
    currency: str = "USD"
    data_source: str = "YAHOO"
    order_type: str = "BUY"


# Realistic approximate historical prices at time of purchase.
ORDERS: list[Order] = [
    # --- US Large Cap ---
    Order("AAPL", "2021-03-15T00:00:00.000Z", 15, 121.03, 4.95),
    Order("AAPL", "2022-06-20T00:00:00.000Z", 10, 135.87, 4.95),
    Order("MSFT", "2021-02-10T00:00:00.000Z", 12, 242.47, 4.95),
    Order("MSFT", "2023-01-09T00:00:00.000Z", 8, 228.85, 0.00),
    Order("GOOGL", "2021-07-22T00:00:00.000Z", 10, 138.27, 4.95),
    Order("GOOGL", "2024-02-12T00:00:00.000Z", 5, 141.80, 0.00),
    Order("AMZN", "2021-11-01T00:00:00.000Z", 12, 167.37, 4.95),
    Order("AMZN", "2023-07-18T00:00:00.000Z", 8, 130.15, 0.00),
    Order("NVDA", "2022-01-18T00:00:00.000Z", 20, 243.91, 4.95),
    Order("NVDA", "2024-05-20T00:00:00.000Z", 10, 91.28, 0.00),
    Order("META", "2022-11-07T00:00:00.000Z", 15, 91.74, 4.95),
    Order("META", "2023-10-02T00:00:00.000Z", 5, 300.28, 0.00),

    # --- ETFs (heavier allocation) ---
    Order("SPY", "2021-01-11T00:00:00.000Z", 25, 380.37, 0.00),
    Order("SPY", "2022-09-12T00:00:00.000Z", 20, 407.47, 0.00),
    Order("SPY", "2024-01-08T00:00:00.000Z", 15, 472.65, 0.00),
    Order("VTI", "2021-04-05T00:00:00.000Z", 30, 211.35, 0.00),
    Order("VTI", "2023-04-17T00:00:00.000Z", 20, 205.10, 0.00),
    Order("QQQ", "2021-06-14T00:00:00.000Z", 15, 343.05, 0.00),
    Order("QQQ", "2023-09-05T00:00:00.000Z", 10, 375.19, 0.00),
    Order("VEA", "2021-05-10T00:00:00.000Z", 50, 51.73, 0.00),
    Order("VEA", "2024-03-11T00:00:00.000Z", 40, 48.95, 0.00),
    Order("BND", "2021-08-16T00:00:00.000Z", 40, 86.73, 0.00),
    Order("BND", "2023-11-13T00:00:00.000Z", 30, 71.48, 0.00),
    Order("VNQ", "2022-03-14T00:00:00.000Z", 25, 104.82, 0.00),
    Order("VNQ", "2024-06-10T00:00:00.000Z", 15, 83.20, 0.00),

    # --- Individual stocks ---
    Order("JPM", "2021-09-20T00:00:00.000Z", 10, 162.56, 4.95),
    Order("JNJ", "2022-02-07T00:00:00.000Z", 12, 171.64, 4.95),
    Order("PG", "2022-05-16T00:00:00.000Z", 10, 149.36, 4.95),
    Order("KO", "2021-12-06T00:00:00.000Z", 20, 55.50, 2.50),
    Order("DIS", "2022-08-15T00:00:00.000Z", 12, 121.26, 4.95),
    Order("TSLA", "2021-10-25T00:00:00.000Z", 8, 1024.17, 4.95),
    Order("TSLA", "2023-06-12T00:00:00.000Z", 15, 256.79, 0.00),

    # --- 2025 orders ---
    Order("AAPL", "2025-01-13T00:00:00.000Z", 5, 227.50, 0.00),
    Order("SPY", "2025-02-10T00:00:00.000Z", 10, 602.00, 0.00),
    Order("NVDA", "2025-01-27T00:00:00.000Z", 8, 118.42, 0.00),
]

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def authenticate(client: httpx.Client, base_url: str, access_token: str) -> str:
    """Exchange the security token for a JWT auth token."""
    resp = client.post(
        f"{base_url}/api/v1/auth/anonymous",
        json={"accessToken": access_token},
    )
    resp.raise_for_status()
    auth_token = resp.json()["authToken"]
    return auth_token


def get_or_create_account(client: httpx.Client, base_url: str) -> str:
    """Return the first account ID, creating one if none exist."""
    resp = client.get(f"{base_url}/api/v1/account")
    resp.raise_for_status()
    accounts = resp.json().get("accounts", resp.json()) if isinstance(resp.json(), dict) else resp.json()

    if accounts:
        account_id = accounts[0]["id"]
        print(f"  Using existing account: {accounts[0].get('name', account_id)}")
        return account_id

    # Create a new account
    resp = client.post(
        f"{base_url}/api/v1/account",
        json={"name": "Main Brokerage", "currency": "USD", "platformId": None},
    )
    resp.raise_for_status()
    account_id = resp.json()["id"]
    print(f"  Created account: Main Brokerage ({account_id})")
    return account_id


def create_order(
    client: httpx.Client,
    base_url: str,
    account_id: str,
    order: Order,
) -> None:
    """POST a single order to the Ghostfolio API."""
    payload = {
        "accountId": account_id,
        "currency": order.currency,
        "dataSource": order.data_source,
        "date": order.date,
        "fee": order.fee,
        "quantity": order.quantity,
        "symbol": order.symbol,
        "type": order.order_type,
        "unitPrice": order.unit_price,
    }
    resp = client.post(f"{base_url}/api/v1/order", json=payload)
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_order_summary(order: Order, *, prefix: str = "  ") -> None:
    total = order.quantity * order.unit_price
    date_short = order.date[:10]
    fee_str = f" + ${order.fee:.2f} fee" if order.fee > 0 else ""
    print(
        f"{prefix}Created buy: {order.quantity:g} shares of {order.symbol} "
        f"at ${order.unit_price:,.2f} on {date_short} "
        f"(${total:,.2f}{fee_str})"
    )


def run(
    base_url: str,
    access_token: str,
    dry_run: bool = False,
    delay: float = 0.3,
) -> None:
    total_invested = sum(o.quantity * o.unit_price + o.fee for o in ORDERS)
    print(f"Seed portfolio: {len(ORDERS)} orders, ~${total_invested:,.0f} total invested")
    print(f"Target: {base_url}")
    print()

    if dry_run:
        print("[DRY RUN] The following orders would be created:\n")
        for order in ORDERS:
            print_order_summary(order)
        print(f"\nTotal: {len(ORDERS)} orders, ${total_invested:,.2f} invested")
        return

    with httpx.Client(timeout=30.0) as client:
        # Authenticate
        print("Authenticating...")
        auth_token = authenticate(client, base_url, access_token)
        client.headers["Authorization"] = f"Bearer {auth_token}"
        print("  Authenticated successfully.\n")

        # Get or create account
        print("Setting up account...")
        account_id = get_or_create_account(client, base_url)
        print()

        # Create orders
        print("Creating orders...")
        created = 0
        errors = 0
        for order in ORDERS:
            try:
                create_order(client, base_url, account_id, order)
                print_order_summary(order)
                created += 1
            except httpx.HTTPStatusError as exc:
                errors += 1
                print(
                    f"  FAILED: {order.symbol} on {order.date[:10]} "
                    f"- {exc.response.status_code}: {exc.response.text[:200]}"
                )
            # Small delay to avoid hammering the API
            time.sleep(delay)

        print(f"\nDone: {created} orders created, {errors} errors.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a Ghostfolio instance with realistic portfolio data.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("GHOSTFOLIO_BASE_URL", "http://localhost:3333"),
        help="Ghostfolio base URL (default: $GHOSTFOLIO_BASE_URL or http://localhost:3333)",
    )
    parser.add_argument(
        "--access-token",
        default=os.environ.get("GHOSTFOLIO_ACCESS_TOKEN"),
        help="Ghostfolio security token (default: $GHOSTFOLIO_ACCESS_TOKEN)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without calling the API.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Seconds to wait between API calls (default: 0.3).",
    )
    args = parser.parse_args()

    if not args.access_token and not args.dry_run:
        print(
            "Error: --access-token or GHOSTFOLIO_ACCESS_TOKEN is required "
            "(or use --dry-run to preview).",
            file=sys.stderr,
        )
        sys.exit(1)

    run(
        base_url=args.base_url.rstrip("/"),
        access_token=args.access_token or "",
        dry_run=args.dry_run,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
