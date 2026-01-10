"""Base repository class with common CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import select

from kalshi_research.data.models import Base

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic repository providing common CRUD operations.

    Type parameter T should be a SQLAlchemy model class.
    """

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a database session."""
        self._session = session

    async def get(self, pk: Any) -> T | None:
        """Get a single entity by primary key."""
        return await self._session.get(self.model, pk)

    async def get_all(self, limit: int | None = None) -> Sequence[T]:
        """Get all entities, optionally limited."""
        stmt = select(self.model)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def add(self, entity: T, *, flush: bool = True) -> T:
        """Add a new entity.

        Args:
            entity: Entity to add.
            flush: Flush the session immediately (default: True).

        Note:
            This method intentionally does not call `refresh()`.
            For SQLite, primary keys are populated on flush.
            Most code in this repo does not rely on server-side defaults.
        """
        self._session.add(entity)
        if flush:
            await self._session.flush()
        return entity

    async def add_many(self, entities: list[T], *, flush: bool = True) -> list[T]:
        """Add multiple entities.

        Args:
            entities: Entities to add.
            flush: Flush the session immediately (default: True).
        """
        self._session.add_all(entities)
        if flush:
            await self._session.flush()
        return entities

    async def delete(self, entity: T) -> None:
        """Delete an entity."""
        await self._session.delete(entity)
        await self._session.flush()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._session.rollback()
