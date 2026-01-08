"""Authentication logic for Kalshi API (RSA-PSS signing)."""

from __future__ import annotations

import base64
import binascii
import time
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey


class KalshiAuth:
    """
    Handles Kalshi API authentication (RSA-PSS signing).
    """

    def __init__(
        self,
        key_id: str,
        private_key_path: str | None = None,
        private_key_b64: str | None = None,
    ) -> None:
        self.key_id = key_id
        self.private_key = self._load_private_key(
            private_key_path=private_key_path,
            private_key_b64=private_key_b64,
        )

    def _load_private_key(
        self,
        *,
        private_key_path: str | None,
        private_key_b64: str | None,
    ) -> RSAPrivateKey:
        """Load RSA private key from PEM file or base64 string."""
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

        if private_key_b64:
            try:
                pem_bytes = base64.b64decode(private_key_b64.strip())
            except (binascii.Error, ValueError) as e:
                raise ValueError("Invalid base64 private key") from e
        else:
            if not private_key_path:
                raise ValueError("private_key_path or private_key_b64 is required")
            pem_bytes = Path(private_key_path).read_bytes()

        private_key = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(private_key, RSAPrivateKey):
            raise ValueError("Invalid key type: expected RSA private key")
        return private_key

    def sign_pss_text(self, text: str) -> str:
        """Sign text using RSA-PSS and return base64 signature."""
        message = text.encode("utf-8")
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode("utf-8")
        except InvalidSignature as e:
            raise ValueError("RSA signing failed") from e

    def get_headers(self, method: str, path: str) -> dict[str, str]:
        """
        Generate authentication headers.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Full API path (e.g., /trade-api/v2/portfolio/balance)
                  MUST exclude query parameters.
        """
        # Timestamp in milliseconds
        timestamp_str = str(int(time.time() * 1000))

        # Remove query params from path if present (safety check)
        clean_path = path.split("?")[0]

        # Signature payload: timestamp + method + path
        msg_string = timestamp_str + method + clean_path
        signature = self.sign_pss_text(msg_string)

        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }
