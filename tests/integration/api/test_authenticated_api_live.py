from __future__ import annotations

import os

import pytest

from kalshi_research.api import KalshiClient
from kalshi_research.api.credentials import get_kalshi_auth_env_var_names, resolve_kalshi_auth_env
from kalshi_research.api.models.portfolio import PortfolioBalance

pytestmark = [pytest.mark.integration]


def _require_live_authenticated_api() -> tuple[str, str | None, str | None, str]:
    if os.getenv("KALSHI_RUN_LIVE_API") != "1":
        pytest.skip("Set KALSHI_RUN_LIVE_API=1 to run live Kalshi API tests")

    environment = os.getenv("KALSHI_ENVIRONMENT", "demo")

    try:
        key_id, private_key_path, private_key_b64 = resolve_kalshi_auth_env(environment=environment)
        key_id_var, private_key_path_var, private_key_b64_var = get_kalshi_auth_env_var_names(
            environment=environment
        )
    except ValueError:
        pytest.skip("Set KALSHI_ENVIRONMENT to demo or prod to run live Kalshi API tests")

    if not key_id:
        fallback = "" if key_id_var == "KALSHI_KEY_ID" else " (or KALSHI_KEY_ID)"
        pytest.skip(f"Set {key_id_var}{fallback} to run authenticated API tests")
    if not private_key_path and not private_key_b64:
        path_fallback = (
            ""
            if private_key_path_var == "KALSHI_PRIVATE_KEY_PATH"
            else " (or KALSHI_PRIVATE_KEY_PATH)"
        )
        b64_fallback = (
            ""
            if private_key_b64_var == "KALSHI_PRIVATE_KEY_B64"
            else " (or KALSHI_PRIVATE_KEY_B64)"
        )
        pytest.skip(
            f"Set {private_key_path_var}{path_fallback} "
            f"or {private_key_b64_var}{b64_fallback} to run authenticated API tests"
        )

    return key_id, private_key_path, private_key_b64, environment


@pytest.mark.asyncio
async def test_authenticated_balance_live() -> None:
    key_id, private_key_path, private_key_b64, environment = _require_live_authenticated_api()

    async with KalshiClient(
        key_id=key_id,
        private_key_path=private_key_path,
        private_key_b64=private_key_b64,
        environment=environment,
        timeout=10,
        max_retries=2,
    ) as client:
        balance = await client.get_balance()

    assert isinstance(balance, PortfolioBalance)
    assert balance.balance >= 0
    assert balance.portfolio_value >= 0


@pytest.mark.asyncio
async def test_authenticated_positions_live() -> None:
    key_id, private_key_path, private_key_b64, environment = _require_live_authenticated_api()

    async with KalshiClient(
        key_id=key_id,
        private_key_path=private_key_path,
        private_key_b64=private_key_b64,
        environment=environment,
        timeout=10,
        max_retries=2,
    ) as client:
        positions = await client.get_positions()

    assert isinstance(positions, list)
