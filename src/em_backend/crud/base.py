from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from em_backend.database.models import Base


class CRUDBase:
    def __init__(self, model: type[Base]):
        self.model = model

    async def get(self, db: AsyncSession, id: UUID) -> Base | None:
        """Get a single record by ID."""
        result = await db.execute(
            select(self.model).where(self.model.id == id)  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[Base]:
        """Get multiple records with pagination."""
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: dict[str, Any]) -> Base:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Base, obj_in: dict[str, Any]
    ) -> Base:
        """Update an existing record."""
        for field, value in obj_in.items():
            if value is not None:
                setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: UUID) -> Base | None:
        """Delete a record by ID."""
        db_obj = await self.get(db, id)
        if db_obj:
            await db.delete(db_obj)
            await db.flush()
        return db_obj

    async def get_with_relationships(
        self, db: AsyncSession, id: UUID, relationships: list[str]
    ) -> Base | None:
        """Get a record with specific relationships loaded."""
        query = select(self.model).where(self.model.id == id)  # type: ignore
        for rel in relationships:
            query = query.options(selectinload(getattr(self.model, rel)))
        result = await db.execute(query)
        return result.scalar_one_or_none()
