"""
Tests for API auth module - KalshiAuth class.
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi_research.api.auth import KalshiAuth


def create_test_key_file() -> tuple[Path, rsa.RSAPrivateKey]:
    """Create a test RSA key file and return path and key."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False) as f:
        f.write(pem)
        path = Path(f.name)

    return path, private_key


class TestKalshiAuth:
    """Test KalshiAuth authentication class."""

    @pytest.fixture
    def key_file(self) -> tuple[Path, rsa.RSAPrivateKey]:
        """Create a temporary key file."""
        path, key = create_test_key_file()
        yield path, key
        path.unlink()

    def test_init_loads_key(self, key_file: tuple[Path, rsa.RSAPrivateKey]) -> None:
        """Constructor loads the private key."""
        path, original_key = key_file
        auth = KalshiAuth(key_id="test-key-123", private_key_path=str(path))

        assert auth.key_id == "test-key-123"
        assert auth.private_key is not None
        # Verify same key loaded
        assert (
            auth.private_key.public_key().public_numbers()
            == original_key.public_key().public_numbers()
        )

    def test_init_missing_file(self) -> None:
        """Constructor raises for missing key file."""
        with pytest.raises(FileNotFoundError):
            KalshiAuth(key_id="test", private_key_path="/nonexistent/key.pem")

    def test_sign_pss_text(self, key_file: tuple[Path, rsa.RSAPrivateKey]) -> None:
        """sign_pss_text produces valid base64 signature."""
        path, _ = key_file
        auth = KalshiAuth(key_id="test", private_key_path=str(path))

        signature = auth.sign_pss_text("test message")

        assert isinstance(signature, str)
        # Should be valid base64
        decoded = base64.b64decode(signature)
        assert len(decoded) > 0

    def test_get_headers_structure(self, key_file: tuple[Path, rsa.RSAPrivateKey]) -> None:
        """get_headers returns proper header structure."""
        path, _ = key_file
        auth = KalshiAuth(key_id="my-api-key", private_key_path=str(path))

        headers = auth.get_headers("GET", "/trade-api/v2/markets")

        assert headers["Content-Type"] == "application/json"
        assert headers["KALSHI-ACCESS-KEY"] == "my-api-key"
        assert "KALSHI-ACCESS-SIGNATURE" in headers
        assert "KALSHI-ACCESS-TIMESTAMP" in headers
        # Timestamp should be numeric string
        assert headers["KALSHI-ACCESS-TIMESTAMP"].isdigit()

    def test_get_headers_strips_query_params(
        self, key_file: tuple[Path, rsa.RSAPrivateKey]
    ) -> None:
        """get_headers strips query params from path."""
        path, _ = key_file
        auth = KalshiAuth(key_id="test", private_key_path=str(path))

        # Should not raise - query params are stripped for signing
        headers = auth.get_headers("GET", "/api/markets?limit=10&cursor=abc")

        assert "KALSHI-ACCESS-SIGNATURE" in headers

    def test_different_methods_different_signatures(
        self, key_file: tuple[Path, rsa.RSAPrivateKey]
    ) -> None:
        """Different HTTP methods produce different signatures."""
        path, _ = key_file
        auth = KalshiAuth(key_id="test", private_key_path=str(path))

        get_headers = auth.get_headers("GET", "/api/test")
        post_headers = auth.get_headers("POST", "/api/test")

        # Signatures should differ (method is part of signed payload)
        assert get_headers["KALSHI-ACCESS-SIGNATURE"] != post_headers["KALSHI-ACCESS-SIGNATURE"]
