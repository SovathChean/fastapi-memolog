"""Task repository for data access with vector search support."""

from datetime import date
from typing import Any

from fastapi import Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.task import Task, TaskPeriodType, TaskStatus
from app.repositories.base import SQLAlchemyRepository
from config.database import get_db


class TaskRepository(SQLAlchemyRepository[Task]):
    """Repository for Task entity database operations.

    Extends base repository with task-specific queries including
    period-based filtering and vector similarity search.
    """

    def __init__(self, session: AsyncSession = Depends(get_db)):
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        super().__init__(session, Task)

    async def find_by_period(
        self,
        period_type: TaskPeriodType | str,
        start_date: date,
        end_date: date,
        status: TaskStatus | str | None = None,
    ) -> list[Task]:
        """Get tasks for a specific period.

        Args:
            period_type: Type of period (daily, weekly, monthly).
            start_date: Period start date.
            end_date: Period end date.
            status: Optional status filter.

        Returns:
            List of tasks in the period.
        """
        if isinstance(period_type, TaskPeriodType):
            period_type = period_type.value

        conditions = [
            Task.period_type == period_type,
            Task.period_date >= start_date,
            Task.period_date <= end_date,
        ]

        if status is not None:
            if isinstance(status, TaskStatus):
                status = status.value
            conditions.append(Task.status == status)

        stmt = (
            select(Task)
            .where(and_(*conditions))
            .order_by(Task.period_date.desc(), Task.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_date_range(
        self,
        start_date: date,
        end_date: date,
        period_type: TaskPeriodType | str | None = None,
        status: TaskStatus | str | None = None,
    ) -> list[Task]:
        """Get tasks within a date range.

        Args:
            start_date: Range start date.
            end_date: Range end date.
            period_type: Optional period type filter.
            status: Optional status filter.

        Returns:
            List of tasks in the date range.
        """
        conditions = [
            Task.period_date >= start_date,
            Task.period_date <= end_date,
        ]

        if period_type is not None:
            if isinstance(period_type, TaskPeriodType):
                period_type = period_type.value
            conditions.append(Task.period_type == period_type)

        if status is not None:
            if isinstance(status, TaskStatus):
                status = status.value
            conditions.append(Task.status == status)

        stmt = (
            select(Task)
            .where(and_(*conditions))
            .order_by(Task.period_date.desc(), Task.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def semantic_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        period_type: TaskPeriodType | str | None = None,
        status: TaskStatus | str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[tuple[Task, float]]:
        """Search tasks by semantic similarity.

        Uses pgvector's cosine distance for similarity search.

        Args:
            query_embedding: Query vector embedding.
            limit: Maximum results to return.
            period_type: Optional period type filter.
            status: Optional status filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            List of tuples (task, similarity_score).
            Similarity score is 0-1, higher is more similar.
        """
        # Build filter conditions
        conditions = [Task.embedding.isnot(None)]

        if period_type is not None:
            if isinstance(period_type, TaskPeriodType):
                period_type = period_type.value
            conditions.append(Task.period_type == period_type)

        if status is not None:
            if isinstance(status, TaskStatus):
                status = status.value
            conditions.append(Task.status == status)

        if start_date is not None:
            conditions.append(Task.period_date >= start_date)

        if end_date is not None:
            conditions.append(Task.period_date <= end_date)

        # Calculate cosine distance (0 = identical, 2 = opposite)
        # Convert to similarity (1 = identical, 0 = opposite)
        distance = Task.embedding.cosine_distance(query_embedding)
        similarity = 1 - distance

        stmt = (
            select(Task, similarity.label("similarity"))
            .where(and_(*conditions))
            .order_by(distance)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [(row[0], float(row[1])) for row in rows]

    async def get_period_stats(
        self,
        period_type: TaskPeriodType | str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Get statistics for a period.

        Args:
            period_type: Type of period.
            start_date: Period start date.
            end_date: Period end date.

        Returns:
            Dictionary with total, completed, and pending counts.
        """
        if isinstance(period_type, TaskPeriodType):
            period_type = period_type.value

        base_conditions = [
            Task.period_type == period_type,
            Task.period_date >= start_date,
            Task.period_date <= end_date,
        ]

        # Total count
        total_stmt = (
            select(func.count()).select_from(Task).where(and_(*base_conditions))
        )
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar() or 0

        # Completed count
        completed_conditions = base_conditions + [
            Task.status == TaskStatus.COMPLETED.value
        ]
        completed_stmt = (
            select(func.count()).select_from(Task).where(and_(*completed_conditions))
        )
        completed_result = await self.session.execute(completed_stmt)
        completed = completed_result.scalar() or 0

        # Pending count
        pending = total - completed

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
        }

    async def find_by_status(
        self,
        status: TaskStatus | str,
        limit: int = 100,
    ) -> list[Task]:
        """Get tasks by status.

        Args:
            status: Task status to filter by.
            limit: Maximum results.

        Returns:
            List of tasks with the given status.
        """
        if isinstance(status, TaskStatus):
            status = status.value

        stmt = (
            select(Task)
            .where(Task.status == status)
            .order_by(Task.period_date.desc(), Task.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_embedding(
        self,
        task_id: int,
        embedding: list[float],
    ) -> Task | None:
        """Update task embedding vector.

        Args:
            task_id: Task ID.
            embedding: New embedding vector.

        Returns:
            Updated task or None if not found.
        """
        return await self.update(task_id, embedding=embedding)

    async def find_task_by_period_number(
        self,
        period_number: int,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> Task | None:
        """Find task by its position (1-based) in the period.

        Tasks are ordered by category (for grouping) then created_at,
        so the number corresponds to the display order in the list.

        Args:
            period_number: 1-based position in the period list.
            period_type: Type of period (daily, weekly, monthly).
            start_date: Period start date.
            end_date: Period end date.

        Returns:
            Task at the given position, or None if not found.
        """
        if period_number < 1:
            return None

        if isinstance(period_type, TaskPeriodType):
            period_type = period_type.value

        # Get all tasks for the period, ordered by category then created_at
        # This matches the display order in format_task_list
        stmt = (
            select(Task)
            .where(
                and_(
                    Task.period_type == period_type,
                    Task.period_date >= start_date,
                    Task.period_date <= end_date,
                )
            )
            .order_by(Task.category.asc(), Task.created_at.asc())
            .offset(period_number - 1)  # Convert 1-based to 0-based
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_period(
        self,
        period_type: str,
        start_date: date,
        end_date: date,
        status: TaskStatus | str | None = None,
    ) -> int:
        """Count tasks in a period with optional status filter.

        Args:
            period_type: Type of period.
            start_date: Period start date.
            end_date: Period end date.
            status: Optional status filter.

        Returns:
            Number of tasks matching the criteria.
        """
        if isinstance(period_type, TaskPeriodType):
            period_type = period_type.value

        conditions = [
            Task.period_type == period_type,
            Task.period_date >= start_date,
            Task.period_date <= end_date,
        ]

        if status is not None:
            if isinstance(status, TaskStatus):
                status = status.value
            conditions.append(Task.status == status)

        stmt = select(func.count()).select_from(Task).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar() or 0
