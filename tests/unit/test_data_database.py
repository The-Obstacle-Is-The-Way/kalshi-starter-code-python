"""
Tests for DatabaseManager - core database functionality.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import text

from kalshi_research.data.database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager operations."""

    @pytest.fixture
    def temp_db_path(self) -> Path:
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = Path(f.name)
        # Delete so DatabaseManager creates it fresh
        path.unlink()
        return path

    @pytest.mark.asyncio
    async def test_create_tables(self, temp_db_path: Path) -> None:
        """Can create database tables."""
        manager = DatabaseManager(str(temp_db_path))
        await manager.create_tables()

        # Check DB file was created
        assert temp_db_path.exists()

        await manager.close()

    @pytest.mark.asyncio
    async def test_session_query(self, temp_db_path: Path) -> None:
        """Session can execute queries."""
        manager = DatabaseManager(str(temp_db_path))
        await manager.create_tables()

        # Session should be usable
        session = await manager.get_session()
        result = await session.execute(text("SELECT 1"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1
        await session.close()

        await manager.close()

    @pytest.mark.asyncio
    async def test_engine_property(self, temp_db_path: Path) -> None:
        """Engine property creates engine lazily."""
        manager = DatabaseManager(str(temp_db_path))

        # Access engine property
        engine = manager.engine

        assert engine is not None
        assert manager._engine is engine

        await manager.close()

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self, temp_db_path: Path) -> None:
        """Close disposes the engine."""
        manager = DatabaseManager(str(temp_db_path))
        _ = manager.engine  # Access to create engine
        await manager.close()

        assert manager._engine is None

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_db_path: Path) -> None:
        """Context manager closes on exit."""
        async with DatabaseManager(str(temp_db_path)) as manager:
            _ = manager.engine  # Access to create engine
            assert manager._engine is not None

        assert manager._engine is None

    @pytest.mark.asyncio
    async def test_session_factory_property(self, temp_db_path: Path) -> None:
        """Session factory is created lazily."""
        manager = DatabaseManager(str(temp_db_path))

        factory = manager.session_factory

        assert factory is not None
        assert manager._session_factory is factory

        await manager.close()
