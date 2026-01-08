from __future__ import annotations

import os

import pytest

from kalshi_research.api import KalshiClient

pytestmark = [pytest.mark.integration]


def _require_live_authenticated_api() -> tuple[str, str | None, str | None, str]:
    if os.getenv("KALSHI_RUN_LIVE_API") != "1":
        pytest.skip("Set KALSHI_RUN_LIVE_API=1 to run live Kalshi API tests")

    key_id = os.getenv("KALSHI_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    private_key_b64 = os.getenv("KALSHI_PRIVATE_KEY_B64")
    environment = os.getenv("KALSHI_ENVIRONMENT", "demo")

    if not key_id:
        pytest.skip("Set KALSHI_KEY_ID to run authenticated API tests")
    if not private_key_path and not private_key_b64:
        pytest.skip(
            "Set KALSHI_PRIVATE_KEY_PATH or KALSHI_PRIVATE_KEY_B64 to run authenticated API tests"
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

    assert isinstance(balance, dict)
    assert balance  # non-empty response indicates auth/signing worked


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
