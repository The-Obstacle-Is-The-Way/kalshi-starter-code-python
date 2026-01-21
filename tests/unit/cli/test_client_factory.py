"""Tests for the Kalshi API client factory module."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi_research.api import KalshiClient, KalshiPublicClient
from kalshi_research.api.rate_limiter import RateTier
from kalshi_research.cli.client_factory import authed_client, public_client

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


def create_test_key_file() -> tuple[Path, str]:
    """Create a test RSA key file and return path and base64-encoded key."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False) as f:
        f.write(pem)
        path = Path(f.name)

    key_b64 = base64.b64encode(pem).decode("utf-8")
    return path, key_b64


@pytest.fixture
def test_key() -> Generator[tuple[Path, str], None, None]:
    """Provide a test RSA key (path and base64)."""
    path, key_b64 = create_test_key_file()
    yield path, key_b64
    path.unlink()


class TestPublicClient:
    """Test public_client factory function."""

    def test_public_client_returns_kalshi_public_client(self) -> None:
        """Factory returns KalshiPublicClient instance."""
        client = public_client()
        assert isinstance(client, KalshiPublicClient)

    def test_public_client_default_timeout(self) -> None:
        """Factory uses default 30s timeout."""
        client = public_client()
        # Access internal httpx client to verify timeout
        assert client._client.timeout.read == 30.0

    def test_public_client_custom_timeout(self) -> None:
        """Factory accepts custom timeout."""
        client = public_client(timeout=60.0)
        assert client._client.timeout.read == 60.0

    def test_public_client_custom_rate_tier_enum(self) -> None:
        """Factory accepts RateTier enum."""
        client = public_client(rate_tier=RateTier.ADVANCED)
        assert client._rate_limiter._tier == RateTier.ADVANCED

    def test_public_client_custom_rate_tier_string(self) -> None:
        """Factory accepts rate tier as string."""
        client = public_client(rate_tier="advanced")
        assert client._rate_limiter._tier == RateTier.ADVANCED

    def test_public_client_environment_override(self) -> None:
        """Factory accepts environment override."""
        # Just verify it doesn't raise - we can't check base URL easily
        client = public_client(environment="demo")
        assert isinstance(client, KalshiPublicClient)


class TestAuthedClient:
    """Test authed_client factory function."""

    def test_authed_client_returns_kalshi_client(self, test_key: tuple[Path, str]) -> None:
        """Factory returns KalshiClient instance."""
        _, key_b64 = test_key
        client = authed_client(key_id="test_key", private_key_b64=key_b64)
        assert isinstance(client, KalshiClient)

    def test_authed_client_inherits_public_client(self, test_key: tuple[Path, str]) -> None:
        """KalshiClient is subclass of KalshiPublicClient."""
        _, key_b64 = test_key
        client = authed_client(key_id="test_key", private_key_b64=key_b64)
        assert isinstance(client, KalshiPublicClient)

    def test_authed_client_requires_key_id(self) -> None:
        """Factory requires key_id parameter (no default)."""
        with pytest.raises(TypeError, match="missing 1 required keyword-only argument: 'key_id'"):
            authed_client_noargs = cast("Callable[[], object]", authed_client)
            authed_client_noargs()

    def test_authed_client_custom_timeout(self, test_key: tuple[Path, str]) -> None:
        """Factory accepts custom timeout."""
        _, key_b64 = test_key
        client = authed_client(key_id="test_key", private_key_b64=key_b64, timeout=45.0)
        assert client._client.timeout.read == 45.0

    def test_authed_client_custom_rate_tier(self, test_key: tuple[Path, str]) -> None:
        """Factory accepts rate tier override."""
        _, key_b64 = test_key
        client = authed_client(
            key_id="test_key", private_key_b64=key_b64, rate_tier=RateTier.PREMIER
        )
        assert client._rate_limiter._tier == RateTier.PREMIER

    def test_authed_client_environment_override(self, test_key: tuple[Path, str]) -> None:
        """Factory accepts environment override."""
        _, key_b64 = test_key
        client = authed_client(key_id="test_key", private_key_b64=key_b64, environment="prod")
        assert isinstance(client, KalshiClient)
