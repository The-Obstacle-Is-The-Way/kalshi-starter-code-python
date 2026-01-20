"""Factory functions for constructing Kalshi API clients.

This module is the single source of truth (SSOT) for client construction in CLI
commands, avoiding repeated environment resolution logic and making testing easier
via factory function patching.
"""

from kalshi_research.api import KalshiClient, KalshiPublicClient
from kalshi_research.api.rate_limiter import RateTier


def public_client(
    *,
    environment: str | None = None,
    timeout: float = 30.0,
    max_retries: int = 5,
    rate_tier: str | RateTier = RateTier.BASIC,
) -> KalshiPublicClient:
    """Create a KalshiPublicClient with consistent defaults.

    Args:
        environment: Override global environment (demo or prod). If None, uses .env.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts on transient failures.
        rate_tier: API rate limit tier (basic/advanced/premier/prime).

    Returns:
        Configured KalshiPublicClient instance (use as async context manager).

    Example:
        ```python
        async with public_client(environment="demo") as client:
            market = await client.get_market("TICKER")
        ```
    """
    return KalshiPublicClient(
        environment=environment,
        timeout=timeout,
        max_retries=max_retries,
        rate_tier=rate_tier,
    )


def authed_client(
    *,
    key_id: str,
    private_key_path: str | None = None,
    private_key_b64: str | None = None,
    environment: str | None = None,
    timeout: float = 30.0,
    max_retries: int = 5,
    rate_tier: str | RateTier = RateTier.BASIC,
) -> KalshiClient:
    """Create a KalshiClient (authenticated) with consistent defaults.

    Args:
        key_id: Kalshi API key ID.
        private_key_path: Path to private key file (PEM format).
        private_key_b64: Base64-encoded private key (alternative to file path).
        environment: Override global environment (demo or prod). If None, uses .env.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts on transient failures.
        rate_tier: API rate limit tier (basic/advanced/premier/prime).

    Returns:
        Configured KalshiClient instance (use as async context manager).

    Example:
        ```python
        async with authed_client(
            key_id=key_id,
            private_key_path=key_path,
            environment="demo",
        ) as client:
            balance = await client.get_balance()
        ```
    """
    return KalshiClient(
        key_id=key_id,
        private_key_path=private_key_path,
        private_key_b64=private_key_b64,
        environment=environment,
        timeout=timeout,
        max_retries=max_retries,
        rate_tier=rate_tier,
    )
