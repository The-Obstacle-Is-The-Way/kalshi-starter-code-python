"""Shared helpers for CLI database setup."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from kalshi_research.data import DatabaseManager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def open_db(db_path: Path) -> AsyncIterator[DatabaseManager]:
    """Open a database manager and ensure tables exist before yielding."""
    async with DatabaseManager(db_path) as db:
        await db.create_tables()
        yield db


@asynccontextmanager
async def open_db_session(db_path: Path) -> AsyncIterator[AsyncSession]:
    """Open a database session and ensure tables exist before yielding."""
    async with open_db(db_path) as db, db.session_factory() as session:
        yield session
