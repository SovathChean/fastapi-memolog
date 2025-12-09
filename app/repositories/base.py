"""Base repository with comprehensive CRUD operations."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(ABC, Generic[ModelType]):
    """Abstract base repository defining common CRUD operations."""

    # Core CRUD operations
    @abstractmethod
    async def selectById(self, id: int) -> ModelType | None:
        """Get entity by primary key."""
        pass

    @abstractmethod
    async def selectOne(self, **filters: Any) -> ModelType | None:
        """Get first entity matching filters."""
        pass

    @abstractmethod
    async def select(
        self, skip: int = 0, limit: int = 100, **filters: Any
    ) -> list[ModelType]:
        """Get all entities with pagination and optional filters."""
        pass

    @abstractmethod
    async def insert(self, entity: ModelType) -> ModelType:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, id: int, **data: Any) -> ModelType | None:
        """Update an existing entity by ID."""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete an entity by ID."""
        pass

    # Utility operations
    @abstractmethod
    async def exists(self, id: int) -> bool:
        """Check if entity exists by ID."""
        pass

    @abstractmethod
    async def count(self, **filters: Any) -> int:
        """Count entities matching filters."""
        pass

    @abstractmethod
    async def findBy(self, **filters: Any) -> list[ModelType]:
        """Find all entities matching filters."""
        pass

    @abstractmethod
    async def bulkInsert(self, entities: list[ModelType]) -> list[ModelType]:
        """Insert multiple entities at once."""
        pass

    @abstractmethod
    async def bulkDelete(self, ids: list[int]) -> int:
        """Delete multiple entities by IDs."""
        pass

    # Backward compatibility aliases
    async def get(self, id: int) -> ModelType | None:
        """Alias for selectById - Get entity by ID."""
        return await self.selectById(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Alias for select - Get all entities with pagination."""
        return await self.select(skip=skip, limit=limit)

    async def create(self, entity: ModelType) -> ModelType:
        """Alias for insert - Create a new entity."""
        return await self.insert(entity)


class SQLAlchemyRepository(BaseRepository[ModelType]):
    """SQLAlchemy implementation of BaseRepository."""

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        """Initialize repository with session and model.

        Args:
            session: Async database session.
            model: SQLAlchemy model class.
        """
        self.session = session
        self.model = model

    def _build_filters(self, **kwargs: Any) -> list:
        """Build SQLAlchemy filter conditions from kwargs.

        Args:
            **kwargs: Field-value pairs to filter by.

        Returns:
            List of SQLAlchemy filter conditions.
        """
        conditions = []
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                conditions.append(getattr(self.model, key) == value)
        return conditions

    # Core CRUD implementations
    async def selectById(self, id: int) -> ModelType | None:
        """Get entity by primary key.

        Args:
            id: Entity primary key.

        Returns:
            Entity if found, None otherwise.
        """
        return await self.session.get(self.model, id)

    async def selectOne(self, **filters: Any) -> ModelType | None:
        """Get first entity matching filters.

        Args:
            **filters: Field-value pairs to filter by.

        Returns:
            First matching entity or None.
        """
        conditions = self._build_filters(**filters)
        stmt = select(self.model).where(*conditions).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def select(
        self, skip: int = 0, limit: int = 100, **filters: Any
    ) -> list[ModelType]:
        """Get all entities with pagination and optional filters.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            **filters: Optional field-value pairs to filter by.

        Returns:
            List of entities.
        """
        conditions = self._build_filters(**filters)
        stmt = select(self.model).where(*conditions).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def insert(self, entity: ModelType) -> ModelType:
        """Create a new entity.

        Args:
            entity: Entity to create.

        Returns:
            Created entity with generated ID.
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: int, **data: Any) -> ModelType | None:
        """Update an existing entity by ID.

        Args:
            id: Entity primary key.
            **data: Field-value pairs to update.

        Returns:
            Updated entity if found, None otherwise.
        """
        entity = await self.selectById(id)
        if entity is None:
            return None

        for key, value in data.items():
            if hasattr(entity, key) and not key.startswith("_"):
                setattr(entity, key, value)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: int) -> bool:
        """Delete an entity by ID.

        Args:
            id: Entity primary key.

        Returns:
            True if deleted, False if not found.
        """
        entity = await self.selectById(id)
        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.flush()
        return True

    # Utility implementations
    async def exists(self, id: int) -> bool:
        """Check if entity exists by ID.

        Args:
            id: Entity primary key.

        Returns:
            True if exists, False otherwise.
        """
        entity = await self.selectById(id)
        return entity is not None

    async def count(self, **filters: Any) -> int:
        """Count entities matching filters.

        Args:
            **filters: Optional field-value pairs to filter by.

        Returns:
            Number of matching entities.
        """
        conditions = self._build_filters(**filters)
        stmt = select(func.count()).select_from(self.model).where(*conditions)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def findBy(self, **filters: Any) -> list[ModelType]:
        """Find all entities matching filters (no pagination).

        Args:
            **filters: Field-value pairs to filter by.

        Returns:
            List of matching entities.
        """
        conditions = self._build_filters(**filters)
        stmt = select(self.model).where(*conditions)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulkInsert(self, entities: list[ModelType]) -> list[ModelType]:
        """Insert multiple entities at once.

        Args:
            entities: List of entities to create.

        Returns:
            List of created entities with generated IDs.
        """
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def bulkDelete(self, ids: list[int]) -> int:
        """Delete multiple entities by IDs.

        Args:
            ids: List of entity primary keys.

        Returns:
            Number of deleted entities.
        """
        if not ids:
            return 0

        # Get primary key column name (assumes 'id' or first primary key)
        pk_column = getattr(self.model, "id", None)
        if pk_column is None:
            # Fallback to inspect primary key
            from sqlalchemy import inspect

            mapper = inspect(self.model)
            pk_column = mapper.primary_key[0]

        stmt = delete(self.model).where(pk_column.in_(ids))
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
