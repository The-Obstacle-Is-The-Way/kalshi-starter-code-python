"""add portfolio settlements table

Revision ID: 72eaf245a5d1
Revises: 9e54540e9c31
Create Date: 2026-01-10 12:31:01.539302

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72eaf245a5d1"
down_revision: str | Sequence[str] | None = "9e54540e9c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "portfolio_settlements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=100), nullable=False),
        sa.Column("event_ticker", sa.String(length=100), nullable=False),
        sa.Column("market_result", sa.String(length=20), nullable=False),
        sa.Column("yes_count", sa.Integer(), nullable=False),
        sa.Column("yes_total_cost", sa.Integer(), nullable=False),
        sa.Column("no_count", sa.Integer(), nullable=False),
        sa.Column("no_total_cost", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Integer(), nullable=False),
        sa.Column("fee_cost_dollars", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticker",
            "settled_at",
            name="uq_portfolio_settlements_ticker_settled_at",
        ),
    )
    op.create_index(
        "idx_portfolio_settlements_ticker",
        "portfolio_settlements",
        ["ticker"],
    )
    op.create_index(
        "idx_portfolio_settlements_event_ticker",
        "portfolio_settlements",
        ["event_ticker"],
    )
    op.create_index(
        "idx_portfolio_settlements_settled_at",
        "portfolio_settlements",
        ["settled_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_portfolio_settlements_settled_at", table_name="portfolio_settlements")
    op.drop_index("idx_portfolio_settlements_event_ticker", table_name="portfolio_settlements")
    op.drop_index("idx_portfolio_settlements_ticker", table_name="portfolio_settlements")
    op.drop_table("portfolio_settlements")
