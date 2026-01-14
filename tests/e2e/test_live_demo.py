"""
Live End-to-End tests against the configured Kalshi API environment.

These are skipped unless explicitly enabled via `KALSHI_RUN_LIVE_API=1` and valid
credentials are configured in the environment.
"""

import os

import pytest

from kalshi_research.api.client import KalshiClient


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_live_connection_and_balance():
    """Verify we can connect and perform read-only calls (status/balance/markets)."""

    if os.getenv("KALSHI_RUN_LIVE_API") != "1":
        pytest.skip("Set KALSHI_RUN_LIVE_API=1 to run live E2E tests")

    key_id = os.getenv("KALSHI_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    private_key_b64 = os.getenv("KALSHI_PRIVATE_KEY_B64")
    environment = os.getenv("KALSHI_ENVIRONMENT", "demo")

    if not key_id:
        pytest.skip("Set KALSHI_KEY_ID to run live E2E tests")
    if not private_key_path and not private_key_b64:
        pytest.skip("Set KALSHI_PRIVATE_KEY_PATH or KALSHI_PRIVATE_KEY_B64 to run live E2E tests")
    if environment not in {"demo", "prod"}:
        pytest.skip("Set KALSHI_ENVIRONMENT to demo or prod to run live E2E tests")

    client = KalshiClient(
        key_id=key_id,
        private_key_path=private_key_path,
        private_key_b64=private_key_b64,
        environment=environment,
        timeout=10,
        max_retries=2,
    )

    async with client:
        # 1. Check Exchange Status (Public)
        status = await client.get_exchange_status()
        assert "exchange_active" in status

        # 2. Check Balance (Auth)
        balance = await client.get_balance()
        assert balance.balance >= 0
        assert balance.portfolio_value >= 0

        # 3. Fetch Markets
        markets = await client.get_markets(limit=5)
        assert len(markets) > 0
