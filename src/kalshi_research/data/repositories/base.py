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

    async def add(self, entity: T) -> T:
        """Add a new entity."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def add_many(self, entities: list[T]) -> list[T]:
        """Add multiple entities."""
        self._session.add_all(entities)
        await self._session.flush()
        for entity in entities:
            await self._session.refresh(entity)
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
