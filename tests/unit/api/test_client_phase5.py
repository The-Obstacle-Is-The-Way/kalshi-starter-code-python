"""Unit tests for Phase 5 endpoints (SPEC-041)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response
from pydantic import ValidationError

from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.models.multivariate import TickerPair
from tests.golden_fixtures import load_golden_response


@pytest.fixture
def mock_auth() -> None:
    with patch("kalshi_research.api.client.KalshiAuth") as MockAuth:
        mock_auth_instance = MockAuth.return_value
        mock_auth_instance.get_headers.return_value = {"X-Signed": "true"}
        yield


class TestMultivariateEventCollectionsPhase5:
    """Tests for multivariate event collection endpoints (SPEC-041)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_multivariate_event_collections_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("multivariate_event_collections_list_response.json")
        multivariate_contracts = response_json.get("multivariate_contracts")
        assert isinstance(multivariate_contracts, list) and multivariate_contracts

        first = multivariate_contracts[0]
        assert isinstance(first, dict)
        associated_event_tickers = first.get("associated_event_tickers")
        assert isinstance(associated_event_tickers, list) and associated_event_tickers
        associated_event_ticker = associated_event_tickers[0]
        assert isinstance(associated_event_ticker, str)
        series_ticker = first.get("series_ticker")
        assert isinstance(series_ticker, str)

        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            page = await client.get_multivariate_event_collections(
                status="open",
                associated_event_ticker=associated_event_ticker,
                series_ticker=series_ticker,
                limit=5,
                cursor="cursor",
            )

        assert route.called
        assert page.cursor == response_json["cursor"]
        assert len(page.multivariate_contracts) == len(response_json["multivariate_contracts"])
        assert page.multivariate_contracts[0].collection_ticker == first["collection_ticker"]

        request_params = route.calls[0].request.url.params
        assert request_params["status"] == "open"
        assert request_params["associated_event_ticker"] == associated_event_ticker
        assert request_params["series_ticker"] == series_ticker
        assert request_params["limit"] == "5"
        assert request_params["cursor"] == "cursor"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_multivariate_event_collections_omits_optional_params(self) -> None:
        response_json = load_golden_response("multivariate_event_collections_list_response.json")
        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            await client.get_multivariate_event_collections(limit=999)

        assert route.called
        request_params = route.calls[0].request.url.params
        assert request_params["limit"] == "200"
        assert "status" not in request_params
        assert "associated_event_ticker" not in request_params
        assert "series_ticker" not in request_params
        assert "cursor" not in request_params

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_multivariate_event_collection_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("multivariate_event_collection_single_response.json")
        multivariate_contract = response_json.get("multivariate_contract")
        assert isinstance(multivariate_contract, dict)
        collection_ticker = multivariate_contract.get("collection_ticker")
        assert isinstance(collection_ticker, str)

        route = respx.get(
            f"https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections/{collection_ticker}"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            contract = await client.get_multivariate_event_collection(collection_ticker)

        assert route.called
        assert contract.collection_ticker == collection_ticker

    @pytest.mark.asyncio
    @respx.mock
    async def test_lookup_multivariate_event_collection_tickers_puts_payload_and_parses(
        self, mock_auth: None
    ) -> None:
        lookup_response = load_golden_response(
            "multivariate_event_collection_lookup_tickers_response.json"
        )
        single_response = load_golden_response("multivariate_event_collection_single_response.json")
        multivariate_contract = single_response.get("multivariate_contract")
        assert isinstance(multivariate_contract, dict)
        collection_ticker = multivariate_contract["collection_ticker"]

        route = respx.put(
            f"https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"
        ).mock(return_value=Response(200, json=lookup_response))

        selected_markets = [
            TickerPair(market_ticker="KXTEST-MKT1", event_ticker="KXTEST-EVT1", side="yes"),
            TickerPair(market_ticker="KXTEST-MKT2", event_ticker="KXTEST-EVT2", side="no"),
        ]

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="prod"
        ) as client:
            client._rate_limiter = AsyncMock()
            response = await client.lookup_multivariate_event_collection_tickers(
                collection_ticker=collection_ticker,
                selected_markets=selected_markets,
            )

        assert route.called
        client._rate_limiter.acquire.assert_called_with(
            "PUT", f"/multivariate_event_collections/{collection_ticker}/lookup"
        )
        assert response.event_ticker == lookup_response["event_ticker"]
        assert response.market_ticker == lookup_response["market_ticker"]

        request_json = json.loads(route.calls[0].request.content)
        assert request_json == {
            "selected_markets": [
                {"market_ticker": "KXTEST-MKT1", "event_ticker": "KXTEST-EVT1", "side": "yes"},
                {"market_ticker": "KXTEST-MKT2", "event_ticker": "KXTEST-EVT2", "side": "no"},
            ]
        }

    @pytest.mark.asyncio
    async def test_lookup_multivariate_event_collection_tickers_rejects_empty(
        self, mock_auth: None
    ) -> None:
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="prod"
        ) as client:
            with pytest.raises(ValueError, match="selected_markets must be non-empty"):
                await client.lookup_multivariate_event_collection_tickers(
                    collection_ticker="KXMV-EXAMPLE",
                    selected_markets=[],
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_lookup_multivariate_event_collection_tickers_429_raises_rate_limit_error(
        self, mock_auth: None
    ) -> None:
        collection_ticker = "KXMV-EXAMPLE"
        route = respx.put(
            f"https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"
        ).mock(return_value=Response(429, text="rate limit", headers={"Retry-After": "2"}))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="prod", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(RateLimitError) as exc_info:
                await client.lookup_multivariate_event_collection_tickers(
                    collection_ticker=collection_ticker,
                    selected_markets=[
                        TickerPair(
                            market_ticker="KXTEST-MKT1",
                            event_ticker="KXTEST-EVT1",
                            side="yes",
                        )
                    ],
                )

        assert route.called
        assert exc_info.value.retry_after == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_lookup_multivariate_event_collection_tickers_429_invalid_retry_after(
        self, mock_auth: None
    ) -> None:
        collection_ticker = "KXMV-EXAMPLE"
        route = respx.put(
            f"https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"
        ).mock(return_value=Response(429, text="rate limit", headers={"Retry-After": "abc"}))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="prod", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(RateLimitError) as exc_info:
                await client.lookup_multivariate_event_collection_tickers(
                    collection_ticker=collection_ticker,
                    selected_markets=[
                        TickerPair(
                            market_ticker="KXTEST-MKT1",
                            event_ticker="KXTEST-EVT1",
                            side="yes",
                        )
                    ],
                )

        assert route.called
        assert exc_info.value.retry_after is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_lookup_multivariate_event_collection_tickers_500_raises(
        self, mock_auth: None
    ) -> None:
        collection_ticker = "KXMV-EXAMPLE"
        route = respx.put(
            f"https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"
        ).mock(return_value=Response(500, text="internal error"))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="prod", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError) as exc_info:
                await client.lookup_multivariate_event_collection_tickers(
                    collection_ticker=collection_ticker,
                    selected_markets=[
                        TickerPair(
                            market_ticker="KXTEST-MKT1",
                            event_ticker="KXTEST-EVT1",
                            side="yes",
                        )
                    ],
                )

        assert route.called
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_lookup_multivariate_event_collection_tickers_unexpected_shape_raises(
        self, mock_auth: None
    ) -> None:
        collection_ticker = "KXMV-EXAMPLE"
        route = respx.put(
            f"https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"
        ).mock(return_value=Response(200, json=[]))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="prod", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(
                KalshiAPIError, match="Unexpected multivariate lookup response shape"
            ):
                await client.lookup_multivariate_event_collection_tickers(
                    collection_ticker=collection_ticker,
                    selected_markets=[
                        TickerPair(
                            market_ticker="KXTEST-MKT1",
                            event_ticker="KXTEST-EVT1",
                            side="yes",
                        )
                    ],
                )

        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_lookup_multivariate_event_collection_tickers_empty_body_raises_validation_error(
        self, mock_auth: None
    ) -> None:
        collection_ticker = "KXMV-EXAMPLE"
        route = respx.put(
            f"https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"
        ).mock(return_value=Response(200, content=b""))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="prod", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(ValidationError):
                await client.lookup_multivariate_event_collection_tickers(
                    collection_ticker=collection_ticker,
                    selected_markets=[
                        TickerPair(
                            market_ticker="KXTEST-MKT1",
                            event_ticker="KXTEST-EVT1",
                            side="yes",
                        )
                    ],
                )

        assert route.called
