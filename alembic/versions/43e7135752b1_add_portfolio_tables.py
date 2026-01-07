"""add_portfolio_tables

Revision ID: 43e7135752b1
Revises: d4dfdc646da1
Create Date: 2026-01-06 22:58:22.344456

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "43e7135752b1"
down_revision: str | Sequence[str] | None = "d4dfdc646da1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create positions table
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=100), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("avg_price_cents", sa.Integer(), nullable=False),
        sa.Column("current_price_cents", sa.Integer(), nullable=True),
        sa.Column("unrealized_pnl_cents", sa.Integer(), nullable=True),
        sa.Column("realized_pnl_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thesis_id", sa.Integer(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("idx_positions_ticker"), "positions", ["ticker"])
    op.create_index(op.f("idx_positions_thesis"), "positions", ["thesis_id"])

    # Create trades table
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kalshi_trade_id", sa.String(length=100), nullable=False),
        sa.Column("ticker", sa.String(length=100), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("total_cost_cents", sa.Integer(), nullable=False),
        sa.Column("fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kalshi_trade_id"),
    )
    op.create_index(op.f("idx_trades_ticker"), "trades", ["ticker"])
    op.create_index(op.f("idx_trades_executed"), "trades", ["executed_at"])
    op.create_index(op.f("idx_trades_position"), "trades", ["position_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop trades table first (has FK to positions)
    op.drop_index(op.f("idx_trades_position"), table_name="trades")
    op.drop_index(op.f("idx_trades_executed"), table_name="trades")
    op.drop_index(op.f("idx_trades_ticker"), table_name="trades")
    op.drop_table("trades")

    # Drop positions table
    op.drop_index(op.f("idx_positions_thesis"), table_name="positions")
    op.drop_index(op.f("idx_positions_ticker"), table_name="positions")
    op.drop_table("positions")
