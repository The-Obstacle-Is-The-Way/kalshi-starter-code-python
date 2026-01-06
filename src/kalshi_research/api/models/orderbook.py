"""Orderbook data models for Kalshi API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Orderbook(BaseModel):
    """
    Market orderbook snapshot.

    Note: API returns yes/no as list of [price, quantity] tuples, or null if empty.
    The API only returns bids (no asks) - use yes for YES bids, no for NO bids.
    """

    model_config = ConfigDict(frozen=True)

    # Each level is [price_cents, quantity]
    yes: list[tuple[int, int]] | None = None
    no: list[tuple[int, int]] | None = None
    # Dollar-denominated versions (optional in response)
    yes_dollars: list[tuple[str, int]] | None = None
    no_dollars: list[tuple[str, int]] | None = None

    @property
    def best_yes_bid(self) -> int | None:
        """Best YES bid price in cents."""
        if not self.yes:
            return None
        return max(price for price, _ in self.yes)

    @property
    def best_no_bid(self) -> int | None:
        """Best NO bid price in cents."""
        if not self.no:
            return None
        return max(price for price, _ in self.no)

    @property
    def spread(self) -> int | None:
        """
        Calculate implied spread in cents.

        Since orderbook only has bids, spread = 100 - best_yes_bid - best_no_bid.
        """
        if self.best_yes_bid is None or self.best_no_bid is None:
            return None
        return 100 - self.best_yes_bid - self.best_no_bid

    @property
    def midpoint(self) -> Decimal | None:
        """Calculate midpoint price for YES side."""
        if self.best_yes_bid is None or self.best_no_bid is None:
            return None
        # Implied YES ask = 100 - best_no_bid
        implied_yes_ask = 100 - self.best_no_bid
        return (Decimal(self.best_yes_bid) + Decimal(implied_yes_ask)) / 2
