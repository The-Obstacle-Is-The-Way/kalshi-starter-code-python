"""Fixtures for data layer tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest.fixture
async def session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session with tables for repository tests."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from kalshi_research.data.models import Base

    # Create all tables
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session

    # Cleanup
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
