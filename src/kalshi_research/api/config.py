"""
Configuration for Kalshi API client (Environment handling).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Environment(str, Enum):
    """Kalshi API environments."""

    PRODUCTION = "prod"
    DEMO = "demo"


class APIConfig(BaseModel):
    """Configuration for Kalshi API client."""

    environment: Environment = Environment.PRODUCTION

    @property
    def base_url(self) -> str:
        """REST API base URL."""
        if self.environment == Environment.DEMO:
            return "https://demo-api.kalshi.co/trade-api/v2"
        return "https://api.elections.kalshi.com/trade-api/v2"

    @property
    def websocket_url(self) -> str:
        """WebSocket URL."""
        if self.environment == Environment.DEMO:
            return "wss://demo-api.kalshi.co/trade-api/ws/v2"
        return "wss://api.elections.kalshi.com/trade-api/ws/v2"


# Singleton for global access
_config = APIConfig()


def get_config() -> APIConfig:
    """Get the current global configuration."""
    return _config


def set_environment(env: Environment) -> None:
    """Set the global API environment."""
    global _config  # noqa: PLW0603 - intentional singleton for CLI state
    _config = APIConfig(environment=env)
