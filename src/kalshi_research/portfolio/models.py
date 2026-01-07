"""SQLAlchemy models for portfolio tracking (Position, Trade)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from kalshi_research.data.models import Base


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(UTC)


class Position(Base):
    """Current or historical position in a Kalshi market."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # "yes" or "no"
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    current_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unrealized_pnl_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    realized_pnl_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Link to thesis (optional)
    thesis_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timestamps
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_positions_ticker", "ticker"),
        Index("idx_positions_thesis", "thesis_id"),
    )


class Trade(Base):
    """Individual trade (fill) from Kalshi."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kalshi_trade_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # "yes" or "no"
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # "buy" or "sell"
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # Fees
    fee_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Link to position (optional)
    position_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("positions.id"), nullable=True
    )

    # Timestamps
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_trades_ticker", "ticker"),
        Index("idx_trades_executed", "executed_at"),
        Index("idx_trades_position", "position_id"),
    )
