"""Settlement handling for P&L calculation.

Settlement handling follows Kalshi's documented behavior:
    "Settlements act as 'sells' at the settlement price (100c if won, 0c if lost)"
    - kalshi-api-reference.md:917

This means settlements are treated as synthetic closing fills at the binary outcome price,
processed through the same FIFO logic as regular trades.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import TYPE_CHECKING

from kalshi_research.portfolio._pnl_models import EffectiveTrade, Lot

if TYPE_CHECKING:
    from kalshi_research.portfolio.models import PortfolioSettlement


def get_settlement_prices_cents(
    market_result: str, settlement_value: int | None
) -> tuple[int, int] | None:
    """
    Get (yes_price_cents, no_price_cents) at settlement, or None if not supported.

    Per Kalshi docs, binary settlements are at 100c/0c. For scalar markets, the API
    provides `settlement_value` as the YES payout in cents, and NO pays (100 - value).

    Args:
        market_result: The market result ('yes', 'no', 'scalar', or 'void').
        settlement_value: The settlement value for scalar markets (YES payout in cents).

    Returns:
        Tuple of (yes_price_cents, no_price_cents) or None if void/unsupported.
    """
    if market_result == "yes":
        return 100, 0
    if market_result == "no":
        return 0, 100
    if market_result != "scalar":
        return None
    if settlement_value is None or settlement_value < 0 or settlement_value > 100:
        return None
    return settlement_value, 100 - settlement_value


def parse_settlement_fee_cents(fee_cost_dollars: str) -> int:
    """Parse trading fees from settlement `fee_cost_dollars` into integer cents.

    Args:
        fee_cost_dollars: Fee amount as a dollar string (e.g., "0.5000").

    Returns:
        Fee amount in integer cents, or 0 if parsing fails.
    """
    try:
        return int((Decimal(fee_cost_dollars) * 100).to_integral_value(rounding=ROUND_HALF_EVEN))
    except (InvalidOperation, ValueError):
        return 0


def synthesize_settlement_closes(
    settlements: list[PortfolioSettlement],
    open_lots: dict[tuple[str, str], Lot],
) -> list[EffectiveTrade]:
    """
    Convert settlements to synthetic closing fills for remaining open lots.

    Per Kalshi docs (kalshi-api-reference.md:917):
        "Settlements act as 'sells' at the settlement price (100c if won, 0c if lost)"

    This treats settlements as synthetic sells at the binary outcome price:
    - market_result='yes' -> YES contracts sell at 100c, NO contracts sell at 0c
    - market_result='no'  -> YES contracts sell at 0c, NO contracts sell at 100c
    - market_result='void' -> No P&L impact (positions refunded at cost)

    Args:
        settlements: List of portfolio settlements from Kalshi API.
        open_lots: Dict of (ticker, side) -> Lot with remaining open positions.

    Returns:
        List of synthetic closing fills.
    """
    synthetic_fills: list[EffectiveTrade] = []

    for settlement in settlements:
        prices = get_settlement_prices_cents(settlement.market_result, settlement.value)
        if prices is None:
            continue
        yes_settlement_price, no_settlement_price = prices

        yes_key = (settlement.ticker, "yes")
        yes_qty = (
            open_lots[yes_key].qty_remaining
            if yes_key in open_lots and open_lots[yes_key].qty_remaining > 0
            else 0
        )
        no_key = (settlement.ticker, "no")
        no_qty = (
            open_lots[no_key].qty_remaining
            if no_key in open_lots and open_lots[no_key].qty_remaining > 0
            else 0
        )

        total_qty = yes_qty + no_qty
        if total_qty <= 0:
            continue

        # Synthesize YES fill if open YES lots exist for this ticker
        if yes_qty > 0:
            synthetic_fills.append(
                EffectiveTrade(
                    ticker=settlement.ticker,
                    side="yes",
                    action="sell",
                    quantity=yes_qty,
                    price_cents=yes_settlement_price,
                    total_cost_cents=yes_settlement_price * yes_qty,
                    fee_cents=0,
                    executed_at=settlement.settled_at,
                )
            )

        # Synthesize NO fill if open NO lots exist for this ticker
        if no_qty > 0:
            synthetic_fills.append(
                EffectiveTrade(
                    ticker=settlement.ticker,
                    side="no",
                    action="sell",
                    quantity=no_qty,
                    price_cents=no_settlement_price,
                    total_cost_cents=no_settlement_price * no_qty,
                    fee_cents=0,
                    executed_at=settlement.settled_at,
                )
            )

    return synthetic_fills


def process_synthetic_fills(
    synthetic_fills: list[EffectiveTrade],
    open_lots: dict[tuple[str, str], Lot],
) -> list[int]:
    """
    Process synthetic settlement fills against open lots to compute P&L.

    Uses the same FIFO logic as regular trades but operates on the mutable
    open_lots dict from the initial trade processing.

    Args:
        synthetic_fills: Synthetic closing fills from settlements.
        open_lots: Mutable dict of open lots (will be consumed).

    Returns:
        List of P&L values for each synthetic close.
    """
    closed_pnls: list[int] = []

    for fill in synthetic_fills:
        key = (fill.ticker, fill.side)
        if key not in open_lots:
            continue

        lot = open_lots[key]
        if lot.qty_remaining <= 0:
            continue

        # Consume from the lot (settlement closes all remaining)
        consume_qty = min(lot.qty_remaining, fill.quantity)
        if consume_qty == 0:
            continue

        # Pro-rata cost basis
        consume_cost_cents = round(lot.cost_remaining_cents * consume_qty / lot.qty_remaining)

        # Calculate P&L: proceeds - cost - fees
        # Fee is prorated to consumed quantity
        matched_fee_cents = round(fill.fee_cents * consume_qty / fill.quantity)
        net_proceeds_cents = (fill.price_cents * consume_qty) - matched_fee_cents
        pnl = net_proceeds_cents - consume_cost_cents
        closed_pnls.append(pnl)

        # Update lot
        lot.cost_remaining_cents -= consume_cost_cents
        lot.qty_remaining -= consume_qty

    return closed_pnls
