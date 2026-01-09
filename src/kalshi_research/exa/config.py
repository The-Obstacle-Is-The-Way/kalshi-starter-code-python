"""Configuration for the Exa API client."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ExaConfig:
    """Configuration for Exa API client."""

    api_key: str
    base_url: str = "https://api.exa.ai"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    @classmethod
    def from_env(cls) -> ExaConfig:
        """Load configuration from environment variables.

        Required:
            EXA_API_KEY: Your Exa API key

        Optional:
            EXA_BASE_URL: Override base URL (default: https://api.exa.ai)
            EXA_TIMEOUT: Request timeout in seconds (default: 30)
            EXA_MAX_RETRIES: Max retries for transient errors (default: 3)
            EXA_RETRY_DELAY: Base retry delay in seconds (default: 1)
        """
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            raise ValueError(
                "EXA_API_KEY environment variable is required. Get your API key at https://exa.ai"
            )

        timeout_seconds = float(os.environ.get("EXA_TIMEOUT", "30"))
        max_retries = int(os.environ.get("EXA_MAX_RETRIES", "3"))
        retry_delay_seconds = float(os.environ.get("EXA_RETRY_DELAY", "1"))

        return cls(
            api_key=api_key,
            base_url=os.environ.get("EXA_BASE_URL", "https://api.exa.ai"),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
        )
