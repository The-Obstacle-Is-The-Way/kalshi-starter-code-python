"""add fts5 search indexes

Revision ID: cbbf8e286441
Revises: 72eaf245a5d1
Create Date: 2026-01-18 13:54:26.979207

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cbbf8e286441"
down_revision: str | Sequence[str] | None = "72eaf245a5d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Creates FTS5 virtual tables for market and event search with trigger-based
    maintenance. This migration is safe on databases without FTS5 support - the
    virtual tables simply won't be created and search will fall back to LIKE.
    """
    conn = op.get_bind()

    # Check if FTS5 is available
    result = conn.execute(
        sa.text(
            """
        SELECT 1
        FROM pragma_compile_options
        WHERE compile_options = 'ENABLE_FTS5'
        """
        )
    )
    has_fts5 = result.fetchone() is not None

    if not has_fts5:
        # FTS5 not available - skip virtual table creation
        # Search will fall back to LIKE queries
        return

    # Create market_fts virtual table
    conn.execute(
        sa.text(
            """
        CREATE VIRTUAL TABLE IF NOT EXISTS market_fts USING fts5(
          ticker UNINDEXED,
          title,
          subtitle,
          event_ticker UNINDEXED,
          series_ticker UNINDEXED
        )
        """
        )
    )

    # Create triggers to maintain market_fts
    conn.execute(
        sa.text(
            """
        CREATE TRIGGER IF NOT EXISTS market_fts_ai
        AFTER INSERT ON markets BEGIN
          INSERT INTO market_fts(ticker, title, subtitle, event_ticker, series_ticker)
          VALUES (new.ticker, new.title, new.subtitle, new.event_ticker, new.series_ticker);
        END
        """
        )
    )

    conn.execute(
        sa.text(
            """
        CREATE TRIGGER IF NOT EXISTS market_fts_ad
        AFTER DELETE ON markets BEGIN
          DELETE FROM market_fts WHERE ticker = old.ticker;
        END
        """
        )
    )

    conn.execute(
        sa.text(
            """
        CREATE TRIGGER IF NOT EXISTS market_fts_au
        AFTER UPDATE ON markets BEGIN
          DELETE FROM market_fts WHERE ticker = old.ticker;
          INSERT INTO market_fts(ticker, title, subtitle, event_ticker, series_ticker)
          VALUES (new.ticker, new.title, new.subtitle, new.event_ticker, new.series_ticker);
        END
        """
        )
    )

    # Create event_fts virtual table
    conn.execute(
        sa.text(
            """
        CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5(
          ticker UNINDEXED,
          title,
          category,
          series_ticker UNINDEXED
        )
        """
        )
    )

    # Create triggers to maintain event_fts
    conn.execute(
        sa.text(
            """
        CREATE TRIGGER IF NOT EXISTS event_fts_ai
        AFTER INSERT ON events BEGIN
          INSERT INTO event_fts(ticker, title, category, series_ticker)
          VALUES (new.ticker, new.title, new.category, new.series_ticker);
        END
        """
        )
    )

    conn.execute(
        sa.text(
            """
        CREATE TRIGGER IF NOT EXISTS event_fts_ad
        AFTER DELETE ON events BEGIN
          DELETE FROM event_fts WHERE ticker = old.ticker;
        END
        """
        )
    )

    conn.execute(
        sa.text(
            """
        CREATE TRIGGER IF NOT EXISTS event_fts_au
        AFTER UPDATE ON events BEGIN
          DELETE FROM event_fts WHERE ticker = old.ticker;
          INSERT INTO event_fts(ticker, title, category, series_ticker)
          VALUES (new.ticker, new.title, new.category, new.series_ticker);
        END
        """
        )
    )

    # Populate existing data into FTS tables
    conn.execute(
        sa.text(
            """
        INSERT INTO market_fts(ticker, title, subtitle, event_ticker, series_ticker)
        SELECT ticker, title, subtitle, event_ticker, series_ticker
        FROM markets
        """
        )
    )

    conn.execute(
        sa.text(
            """
        INSERT INTO event_fts(ticker, title, category, series_ticker)
        SELECT ticker, title, category, series_ticker
        FROM events
        """
        )
    )


def downgrade() -> None:
    """Downgrade schema.

    Drops FTS5 virtual tables and triggers.
    """
    conn = op.get_bind()

    # Check if FTS5 tables exist before trying to drop them
    result = conn.execute(
        sa.text(
            """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='market_fts'
        """
        )
    )
    has_market_fts = result.fetchone() is not None

    if has_market_fts:
        # Drop triggers first
        conn.execute(sa.text("DROP TRIGGER IF EXISTS market_fts_au"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS market_fts_ad"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS market_fts_ai"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS event_fts_au"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS event_fts_ad"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS event_fts_ai"))

        # Drop virtual tables
        conn.execute(sa.text("DROP TABLE IF EXISTS market_fts"))
        conn.execute(sa.text("DROP TABLE IF EXISTS event_fts"))
