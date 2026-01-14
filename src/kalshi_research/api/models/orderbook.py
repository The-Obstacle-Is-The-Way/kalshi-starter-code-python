"""Orderbook data models for Kalshi API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .pricing import fixed_dollars_to_cents


def _dollar_to_cents(dollar_str: str) -> int:
    """
    Convert dollar string (e.g., "0.50") to cents (e.g., 50).

    This handles the Kalshi API migration from integer cents to dollar strings.
    After Jan 15, 2026, the API will only return dollar-denominated fields.
    """
    return fixed_dollars_to_cents(dollar_str, label="orderbook price")


class Orderbook(BaseModel):
    """
    Market orderbook snapshot.

    Note: API returns yes/no as list of [price, quantity] tuples, or null if empty.
    The API only returns bids (no asks) - use yes for YES bids, no for NO bids.

    IMPORTANT: As of Jan 15, 2026, Kalshi is deprecating the integer cents fields
    (yes, no) in favor of dollar-denominated strings (yes_dollars, no_dollars).
    The computed properties below handle both formats for backward compatibility.
    """

    model_config = ConfigDict(frozen=True)

    # Each level is [price_cents, quantity] - DEPRECATED Jan 15, 2026
    yes: list[tuple[int, int]] | None = None
    no: list[tuple[int, int]] | None = None
    # Dollar-denominated versions (e.g., [("0.50", 10), ("0.49", 5)])
    # These become the primary fields after Jan 15, 2026
    yes_dollars: list[tuple[str, int]] | None = None
    no_dollars: list[tuple[str, int]] | None = None

    @property
    def yes_levels(self) -> list[tuple[int, int]]:
        """
        YES bid levels as [(price_cents, quantity), ...].

        Prefers dollar-denominated `yes_dollars` when provided, falls back to legacy `yes`.
        Use this instead of accessing `yes` directly for forward compatibility.
        """
        if self.yes_dollars is not None:
            if self.yes_dollars:
                return [(_dollar_to_cents(price), qty) for price, qty in self.yes_dollars]
            if self.yes is not None:
                return list(self.yes)
            return []
        if self.yes is not None:
            return list(self.yes)
        return []

    @property
    def no_levels(self) -> list[tuple[int, int]]:
        """
        NO bid levels as [(price_cents, quantity), ...].

        Prefers dollar-denominated `no_dollars` when provided, falls back to legacy `no`.
        Use this instead of accessing `no` directly for forward compatibility.
        """
        if self.no_dollars is not None:
            if self.no_dollars:
                return [(_dollar_to_cents(price), qty) for price, qty in self.no_dollars]
            if self.no is not None:
                return list(self.no)
            return []
        if self.no is not None:
            return list(self.no)
        return []

    @property
    def best_yes_bid(self) -> int | None:
        """
        Best YES bid price in cents.

        Prefers dollar-denominated `yes_dollars` when provided, falls back to legacy `yes`.
        """
        levels = self.yes_levels
        if levels:
            return max(price for price, _ in levels)
        return None

    @property
    def best_no_bid(self) -> int | None:
        """
        Best NO bid price in cents.

        Prefers dollar-denominated `no_dollars` when provided, falls back to legacy `no`.
        """
        levels = self.no_levels
        if levels:
            return max(price for price, _ in levels)
        return None

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
