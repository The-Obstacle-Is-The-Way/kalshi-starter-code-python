"""
Live End-to-End tests against the Kalshi Demo API.
Only runs if KALSHI_API_KEY is present and KALSHI_ENVIRONMENT=demo.
"""

import os
import pytest
from kalshi_research.api.client import KalshiClient
from kalshi_research.api.config import Environment

# Skip unless we have credentials and explicitly targeting demo
SKIP_LIVE = True
if (
    os.getenv("KALSHI_API_KEY") 
    and os.getenv("KALSHI_PRIVATE_KEY_PATH") 
    and os.getenv("KALSHI_ENVIRONMENT") == "demo"
):
    SKIP_LIVE = False


@pytest.mark.e2e
@pytest.mark.skipif(SKIP_LIVE, reason="Requires Demo API credentials")
@pytest.mark.asyncio
async def test_live_connection_and_balance():
    """Verify we can connect to Demo API and get balance."""
    
    client = KalshiClient(
        key_id=os.getenv("KALSHI_API_KEY"),
        private_key_path=os.getenv("KALSHI_PRIVATE_KEY_PATH"),
        environment="demo"
    )
    
    async with client:
        # 1. Check Exchange Status (Public)
        status = await client.get_exchange_status()
        assert "exchange_active" in status
        
        # 2. Check Balance (Auth)
        balance = await client.get_balance()
        assert "balance" in balance
        print(f"Live Demo Balance: {balance['balance']}")
        
        # 3. Fetch Markets
        markets = await client.get_markets(limit=5)
        assert len(markets) > 0
