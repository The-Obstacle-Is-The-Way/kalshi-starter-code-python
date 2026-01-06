from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

import requests
import websockets
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection


class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"


class KalshiBaseClient:
    """Base client class for interacting with the Kalshi API."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ) -> None:
        """Initializes the client with the provided API key and private key.

        Args:
            key_id (str): Your Kalshi API key ID.
            private_key (rsa.RSAPrivateKey): Your RSA private key.
            environment (Environment): The API environment to use (DEMO or PROD).
        """
        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment
        self.last_api_call = datetime.now()

        if self.environment == Environment.DEMO:
            self.HTTP_BASE_URL = "https://demo-api.kalshi.co"
            self.WS_BASE_URL = "wss://demo-api.kalshi.co"
        elif self.environment == Environment.PROD:
            self.HTTP_BASE_URL = "https://api.elections.kalshi.com"
            self.WS_BASE_URL = "wss://api.elections.kalshi.com"
        else:
            raise ValueError("Invalid environment")

    def request_headers(self, method: str, path: str) -> dict[str, Any]:
        """Generates the required authentication headers for API requests."""
        current_time_milliseconds = int(time.time() * 1000)
        timestamp_str = str(current_time_milliseconds)

        # Remove query params from path
        path_parts = path.split("?")

        msg_string = timestamp_str + method + path_parts[0]
        signature = self.sign_pss_text(msg_string)

        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }
        return headers

    def sign_pss_text(self, text: str) -> str:
        """Signs the text using RSA-PSS and returns the base64 encoded signature."""
        message = text.encode("utf-8")
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode("utf-8")
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e


class KalshiHttpClient(KalshiBaseClient):
    """Client for handling HTTP connections to the Kalshi API."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ) -> None:
        super().__init__(key_id, private_key, environment)
        self.host = self.HTTP_BASE_URL
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"

    def rate_limit(self) -> None:
        """Built-in rate limiter to prevent exceeding API rate limits."""
        THRESHOLD_IN_MILLISECONDS = 100
        now = datetime.now()
        threshold_in_microseconds = 1000 * THRESHOLD_IN_MILLISECONDS
        threshold_in_seconds = THRESHOLD_IN_MILLISECONDS / 1000
        if now - self.last_api_call < timedelta(microseconds=threshold_in_microseconds):
            time.sleep(threshold_in_seconds)
        self.last_api_call = datetime.now()

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """Raises an HTTPError if the response status code indicates an error."""
        if response.status_code not in range(200, 299):
            response.raise_for_status()

    def post(self, path: str, body: dict[str, Any]) -> Any:
        """Performs an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        response = requests.post(
            self.host + path, json=body, headers=self.request_headers("POST", path)
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Performs an authenticated GET request to the Kalshi API."""
        self.rate_limit()
        response = requests.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=params or {},
        )
        self.raise_if_bad_response(response)
        return response.json()

    def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Performs an authenticated DELETE request to the Kalshi API."""
        self.rate_limit()
        response = requests.delete(
            self.host + path,
            headers=self.request_headers("DELETE", path),
            params=params or {},
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get_balance(self) -> dict[str, Any]:
        """Retrieves the account balance."""
        result: dict[str, Any] = self.get(self.portfolio_url + "/balance")
        return result

    def get_exchange_status(self) -> dict[str, Any]:
        """Retrieves the exchange status."""
        result: dict[str, Any] = self.get(self.exchange_url + "/status")
        return result

    def get_trades(
        self,
        ticker: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        max_ts: int | None = None,
        min_ts: int | None = None,
    ) -> dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params: dict[str, Any] = {
            "ticker": ticker,
            "limit": limit,
            "cursor": cursor,
            "max_ts": max_ts,
            "min_ts": min_ts,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        result: dict[str, Any] = self.get(self.markets_url + "/trades", params=params)
        return result


class KalshiWebSocketClient(KalshiBaseClient):
    """Client for handling WebSocket connections to the Kalshi API."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ) -> None:
        super().__init__(key_id, private_key, environment)
        self.ws: ClientConnection | None = None
        self.url_suffix = "/trade-api/ws/v2"
        self.message_id = 1  # Add counter for message IDs

    async def connect(self) -> None:
        """Establishes a WebSocket connection using authentication."""
        host = self.WS_BASE_URL + self.url_suffix
        auth_headers = self.request_headers("GET", self.url_suffix)
        async with websockets.connect(host, additional_headers=auth_headers) as websocket:
            self.ws = websocket
            await self.on_open()
            await self.handler()

    async def on_open(self) -> None:
        """Callback when WebSocket connection is opened."""
        print("WebSocket connection opened.")
        await self.subscribe_to_tickers()

    async def subscribe_to_tickers(self) -> None:
        """Subscribe to ticker updates for all markets."""
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {"channels": ["ticker"]},
        }
        if self.ws is not None:
            await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def handler(self) -> None:
        """Handle incoming messages."""
        try:
            if self.ws is not None:
                async for message in self.ws:
                    await self.on_message(message)
        except websockets.ConnectionClosed as e:
            await self.on_close(e.code, e.reason)
        except Exception as e:
            await self.on_error(e)

    async def on_message(self, message: str | bytes) -> None:
        """Callback for handling incoming messages."""
        print("Received message:", message)

    async def on_error(self, error: Exception) -> None:
        """Callback for handling errors."""
        print("WebSocket error:", error)

    async def on_close(self, close_status_code: int | None, close_msg: str | None) -> None:
        """Callback when WebSocket connection is closed."""
        print(f"WebSocket connection closed with code: {close_status_code}, message: {close_msg}")
