"""
Tests for API configuration and environment switching.
"""

from __future__ import annotations

from unittest.mock import patch

from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from kalshi_research.api.config import (
    Environment,
    get_config,
    set_environment,
)


class TestAPIConfig:
    """Test API configuration logic."""

    def teardown_method(self) -> None:
        """Reset environment to production after each test."""
        set_environment(Environment.PRODUCTION)

    def test_default_environment_is_production(self) -> None:
        """Default environment should be PROD."""
        config = get_config()
        assert config.environment == Environment.PRODUCTION
        assert "api.elections.kalshi.com" in config.base_url
        assert "api.elections.kalshi.com" in config.websocket_url

    def test_environment_switching(self) -> None:
        """Switching environment updates URLs."""
        set_environment(Environment.DEMO)
        config = get_config()
        assert config.environment == Environment.DEMO
        assert "demo-api.kalshi.co" in config.base_url
        assert "demo-api.kalshi.co" in config.websocket_url

    def test_client_respects_global_config(self) -> None:
        """Client should use global config by default."""
        set_environment(Environment.DEMO)
        client = KalshiPublicClient()
        assert "demo-api.kalshi.co" in str(client._client.base_url)

    def test_client_can_override_environment(self) -> None:
        """Client init arg should override global config."""
        set_environment(Environment.PRODUCTION)
        # Override with demo
        client = KalshiPublicClient(environment="demo")
        assert "demo-api.kalshi.co" in str(client._client.base_url)

    @patch("kalshi_research.api.client.KalshiAuth")
    def test_authenticated_client_config(self, mock_auth) -> None:
        """Authenticated client should also respect config."""
        set_environment(Environment.DEMO)
        client = KalshiClient(key_id="test", private_key_b64="dummy")
        assert "demo-api.kalshi.co" in str(client._client.base_url)

    @patch("kalshi_research.api.client.KalshiAuth")
    def test_authenticated_client_override(self, mock_auth) -> None:
        """Authenticated client override."""
        set_environment(Environment.DEMO)
        # Override back to prod
        client = KalshiClient(
            key_id="test",
            private_key_b64="dummy",
            environment="prod",
        )
        assert "api.elections.kalshi.com" in str(client._client.base_url)
