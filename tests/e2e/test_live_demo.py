"""
Live End-to-End tests against the configured Kalshi API environment.

These are skipped unless explicitly enabled via `KALSHI_RUN_LIVE_API=1` and valid
credentials are configured in the environment.
"""

import os

import pytest

from kalshi_research.api.client import KalshiClient
from kalshi_research.api.credentials import get_kalshi_auth_env_var_names, resolve_kalshi_auth_env


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_live_connection_and_balance():
    """Verify we can connect and perform read-only calls (status/balance/markets)."""

    if os.getenv("KALSHI_RUN_LIVE_API") != "1":
        pytest.skip("Set KALSHI_RUN_LIVE_API=1 to run live E2E tests")

    environment = os.getenv("KALSHI_ENVIRONMENT", "demo")

    try:
        key_id, private_key_path, private_key_b64 = resolve_kalshi_auth_env(environment=environment)
        key_id_var, private_key_path_var, private_key_b64_var = get_kalshi_auth_env_var_names(
            environment=environment
        )
    except ValueError:
        pytest.skip("Set KALSHI_ENVIRONMENT to demo or prod to run live E2E tests")

    key_id_fallback = "" if key_id_var == "KALSHI_KEY_ID" else " (or KALSHI_KEY_ID)"
    key_path_fallback = (
        "" if private_key_path_var == "KALSHI_PRIVATE_KEY_PATH" else " (or KALSHI_PRIVATE_KEY_PATH)"
    )
    key_b64_fallback = (
        "" if private_key_b64_var == "KALSHI_PRIVATE_KEY_B64" else " (or KALSHI_PRIVATE_KEY_B64)"
    )

    if not key_id:
        pytest.skip(f"Set {key_id_var}{key_id_fallback} to run live E2E tests")
    if not private_key_path and not private_key_b64:
        pytest.skip(
            f"Set {private_key_path_var}{key_path_fallback} "
            f"or {private_key_b64_var}{key_b64_fallback} to run live E2E tests"
        )

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
