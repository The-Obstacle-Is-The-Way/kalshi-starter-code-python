# SPEC-011: Manual Trading Support

**Status:** Draft
**Priority:** P2
**Depends On:** SPEC-002 (API Client with auth), SPEC-004 (Thesis tracking)

---

## Overview

From the original requirements:

> **Manual Trading Support** - When I find an edge through research, I place manual bets (NOT automated trading)

The platform should help track positions, calculate P&L, and connect research insights to actual trades - WITHOUT automated trading.

This is about **decision support**, not automation.

---

## Problem Statement

Currently, the user can:
- ✅ Research markets
- ✅ Track theses
- ✅ Run backtests
- ❌ See their actual positions
- ❌ Track P&L on real trades
- ❌ Connect thesis → position ("Did my thesis play out?")
- ❌ View account balance/buying power

The gap: Research tools exist, but no connection to actual trading activity.

---

## Requirements

### 1. Portfolio CLI (`kalshi portfolio`)

```bash
# Sync positions from Kalshi (requires auth)
kalshi portfolio sync

# View current positions
kalshi portfolio positions
kalshi portfolio positions --ticker SPECIFIC-TICKER

# View P&L
kalshi portfolio pnl
kalshi portfolio pnl --period today|week|month|all
kalshi portfolio pnl --ticker SPECIFIC-TICKER

# View account info
kalshi portfolio balance

# View trade history
kalshi portfolio history
kalshi portfolio history --limit 50
kalshi portfolio history --ticker SPECIFIC-TICKER
```

### 2. Position Tracking Model

New SQLAlchemy model: `Position`

```python
class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(100), index=True)
    side: Mapped[str]  # "yes" or "no"
    quantity: Mapped[int]
    avg_price_cents: Mapped[int]
    current_price_cents: Mapped[int | None]
    unrealized_pnl_cents: Mapped[int | None]
    realized_pnl_cents: Mapped[int] = mapped_column(default=0)

    # Link to thesis (optional)
    thesis_id: Mapped[int | None] = mapped_column(ForeignKey("theses.id"))

    # Timestamps
    opened_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]
    last_synced: Mapped[datetime]
```

### 3. Trade History Model

New SQLAlchemy model: `Trade`

```python
class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    kalshi_trade_id: Mapped[str] = mapped_column(unique=True)
    ticker: Mapped[str] = mapped_column(index=True)
    side: Mapped[str]  # "yes" or "no"
    action: Mapped[str]  # "buy" or "sell"
    quantity: Mapped[int]
    price_cents: Mapped[int]
    total_cost_cents: Mapped[int]

    # Fees
    fee_cents: Mapped[int] = mapped_column(default=0)

    # Link to position
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))

    executed_at: Mapped[datetime]
    synced_at: Mapped[datetime]
```

### 4. Thesis ↔ Position Linking

Connect research to reality:

```bash
# Link a position to a thesis
kalshi portfolio link TICKER --thesis THESIS_ID

# View thesis with linked positions
kalshi research thesis show THESIS_ID --with-positions

# Auto-suggest: "These positions might relate to thesis X"
kalshi portfolio suggest-links
```

### 5. P&L Calculator

```python
class PnLCalculator:
    """Calculate profit/loss on positions."""

    def calculate_unrealized(self, position: Position, current_price: int) -> int:
        """Unrealized P&L in cents."""
        if position.side == "yes":
            return (current_price - position.avg_price_cents) * position.quantity
        else:
            return (position.avg_price_cents - current_price) * position.quantity

    def calculate_realized(self, trades: list[Trade]) -> int:
        """Realized P&L from closed positions."""
        ...

    def calculate_total(self, positions: list[Position]) -> PnLSummary:
        """Total P&L summary."""
        return PnLSummary(
            unrealized=sum(...),
            realized=sum(...),
            total=...,
            win_rate=...,
            avg_win=...,
            avg_loss=...,
        )
```

### 6. Portfolio Sync Service

```python
class PortfolioSyncer:
    """Sync positions and trades from Kalshi API."""

    def __init__(self, client: KalshiClient, db: DatabaseManager):
        self.client = client  # Authenticated client
        self.db = db

    async def sync_positions(self) -> int:
        """Fetch positions from Kalshi, update local DB."""
        positions = await self.client.get_positions()
        # Upsert to database
        return len(positions)

    async def sync_trades(self, since: datetime | None = None) -> int:
        """Fetch trade history, update local DB."""
        trades = await self.client.get_fills(min_ts=since)
        # Insert new trades
        return len(trades)

    async def full_sync(self) -> SyncResult:
        """Full portfolio sync."""
        positions = await self.sync_positions()
        trades = await self.sync_trades()
        return SyncResult(positions=positions, trades=trades)
```

---

## Authentication Setup

Requires Kalshi API credentials. Document in USAGE.md:

```bash
# Set environment variables
export KALSHI_API_KEY="your-api-key"
export KALSHI_PRIVATE_KEY_PATH="/path/to/private_key.pem"

# Or use .env file
echo "KALSHI_API_KEY=your-key" >> .env
echo "KALSHI_PRIVATE_KEY_PATH=/path/to/key.pem" >> .env

# Verify auth works
kalshi portfolio balance
```

---

## CLI Output Examples

### `kalshi portfolio positions`

```
╭─────────────────────────────────────────────────────────────────────────╮
│                           Current Positions                              │
├──────────────────────┬──────┬─────┬───────────┬───────────┬─────────────┤
│ Ticker               │ Side │ Qty │ Avg Price │ Current   │ Unrealized  │
├──────────────────────┼──────┼─────┼───────────┼───────────┼─────────────┤
│ KXBTC-25JAN10-50000  │ YES  │ 100 │ 45¢       │ 52¢       │ +$7.00      │
│ PRES-24-DEM          │ NO   │ 50  │ 55¢       │ 48¢       │ +$3.50      │
│ FED-25JAN-HOLD       │ YES  │ 200 │ 72¢       │ 68¢       │ -$8.00      │
├──────────────────────┴──────┴─────┴───────────┴───────────┴─────────────┤
│ Total Unrealized P&L: +$2.50                                            │
╰─────────────────────────────────────────────────────────────────────────╯
```

### `kalshi portfolio pnl`

```
╭─────────────────────────────────────────────────────────────────────────╮
│                         P&L Summary (All Time)                          │
├─────────────────────────────────────────────────────────────────────────┤
│ Realized P&L:      +$125.50                                             │
│ Unrealized P&L:    +$2.50                                               │
│ Total P&L:         +$128.00                                             │
├─────────────────────────────────────────────────────────────────────────┤
│ Total Trades:      47                                                   │
│ Win Rate:          62% (29/47)                                          │
│ Avg Win:           +$8.25                                               │
│ Avg Loss:          -$5.10                                               │
│ Profit Factor:     1.85                                                 │
╰─────────────────────────────────────────────────────────────────────────╯
```

---

## Acceptance Criteria

- [ ] `kalshi portfolio sync` fetches positions from Kalshi API
- [ ] `kalshi portfolio positions` displays current positions with P&L
- [ ] `kalshi portfolio pnl` shows realized + unrealized P&L
- [ ] `kalshi portfolio balance` shows account balance
- [ ] `kalshi portfolio history` shows trade history
- [ ] `kalshi portfolio link` connects positions to theses
- [ ] Position and Trade models created with migrations
- [ ] Works without auth (graceful error: "Authentication required")
- [ ] P&L calculations are accurate

---

## Non-Goals

- ❌ Automated trading (user explicitly said NO)
- ❌ Order placement through CLI (manual on Kalshi website)
- ❌ Risk management / position limits (user manages manually)
- ❌ Real-time position updates (sync on demand)

---

## Testing

```bash
# Unit tests for P&L calculator
uv run pytest tests/unit/test_portfolio_pnl.py

# Integration test (requires auth)
KALSHI_API_KEY=test kalshi portfolio sync

# Mock tests for portfolio syncer
uv run pytest tests/unit/test_portfolio_syncer.py
```

---

## Notes

- This is READ-ONLY from Kalshi's perspective (no orders placed)
- All trades are made manually by user on Kalshi website
- This just TRACKS what the user has done
- Helps answer: "Is my research thesis playing out in my actual trades?"
