"""Utilities for full-text search operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def has_fts5_support(session: AsyncSession) -> bool:
    """Check if SQLite was compiled with FTS5 support.

    Args:
        session: Database session to check.

    Returns:
        True if FTS5 is available, False otherwise.
    """
    result = await session.execute(
        text(
            """
        SELECT 1
        FROM pragma_compile_options
        WHERE compile_options = 'ENABLE_FTS5'
        """
        )
    )
    return result.fetchone() is not None


async def fts_tables_exist(session: AsyncSession) -> bool:
    """Check if FTS5 virtual tables exist in the database.

    Args:
        session: Database session to check.

    Returns:
        True if market_fts and event_fts tables exist, False otherwise.
    """
    result = await session.execute(
        text(
            """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name IN ('market_fts', 'event_fts')
        """
        )
    )
    tables = result.fetchall()
    return len(tables) == 2
