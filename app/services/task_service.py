"""Task service with business logic for memolog."""

from datetime import UTC, date, datetime, time

from fastapi import Depends

from app.common.exceptions import NotFoundError, ValidationError
from app.common.mapper import FieldMapper
from app.models.domain.task import Task, TaskPeriodType, TaskPriority, TaskStatus
from app.models.schemas.task import (
    TaskCreate,
    TaskReportRequest,
    TaskReportResponse,
    TaskReportSummary,
    TaskResponse,
    TaskSearchRequest,
    TaskSearchResult,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.repositories.task_repository import TaskRepository
from app.services.base import BaseService
from app.support.langchain_support import LangChainSupport, get_langchain_support
from app.support.task_support import TaskSupport


class TaskService(BaseService):
    """Service for task feature business logic."""

    def __init__(
        self,
        repository: TaskRepository = Depends(),
        task_support: TaskSupport = Depends(),
    ):
        """Initialize service with dependencies.

        Args:
            repository: Task repository for data access.
            task_support: Support module for task logic.
        """
        super().__init__()
        self.repository = repository
        self.task_support = task_support
        self._langchain_support: LangChainSupport | None = None

    @property
    def langchain_support(self) -> LangChainSupport:
        """Lazy-load LangChain support."""
        if self._langchain_support is None:
            self._langchain_support = get_langchain_support()
        return self._langchain_support

    # Backward compatibility alias
    @property
    def embedding_support(self) -> LangChainSupport:
        """Alias for langchain_support (backward compatibility)."""
        return self.langchain_support

    async def create_task(self, data: TaskCreate) -> Task:
        """Create a new task with embedding.

        Args:
            data: Task creation data.

        Returns:
            Created task entity.

        Raises:
            ValidationError: If validation fails.
        """
        # Validate and transform data
        mapper = (
            FieldMapper(data)
            .validate("title", self.task_support.validate_title)
            .validate("description", self.task_support.validate_description)
            .transform("title", self.task_support.format_title)
            .transform("description", self.task_support.format_description)
        )
        task_data = mapper.to_dict()

        # Normalize period date
        period_type = task_data.get("period_type", TaskPeriodType.DAILY)
        period_date = task_data.get("period_date")
        if period_date:
            task_data["period_date"] = self.task_support.normalize_period_date(
                period_type,
                period_date,
            )

        # Convert enum to string value for database
        if isinstance(task_data.get("period_type"), TaskPeriodType):
            task_data["period_type"] = task_data["period_type"].value

        # Convert priority enum to string value
        if isinstance(task_data.get("priority"), TaskPriority):
            task_data["priority"] = task_data["priority"].value

        # Set default status
        task_data["status"] = TaskStatus.PENDING.value

        # Create task
        task = Task(**task_data)
        created_task = await self.repository.insert(task)

        # Generate embedding asynchronously (best effort)
        try:
            await self._update_task_embedding(created_task)
        except Exception as e:
            self.logger.warning(
                f"Failed to generate embedding for task {created_task.id}: {e}"
            )

        self.logger.info(f"Created task: {created_task.id}")
        return created_task

    async def get_task(self, task_id: int) -> Task:
        """Get task by ID.

        Args:
            task_id: Task ID.

        Returns:
            Task entity.

        Raises:
            NotFoundError: If task not found.
        """
        task = await self.repository.selectById(task_id)
        if not task:
            raise NotFoundError("Task", task_id)
        return task

    async def get_tasks(
        self,
        skip: int = 0,
        limit: int = 100,
        period_type: str | None = None,
        status: str | None = None,
    ) -> list[Task]:
        """Get all tasks with pagination and optional filters.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            period_type: Optional period type filter.
            status: Optional status filter.

        Returns:
            List of task entities.
        """
        filters = {}
        if period_type:
            filters["period_type"] = period_type
        if status:
            filters["status"] = status

        return await self.repository.select(skip=skip, limit=limit, **filters)

    async def get_tasks_count(
        self,
        period_type: str | None = None,
        status: str | None = None,
    ) -> int:
        """Get total count of tasks with optional filters.

        Args:
            period_type: Optional period type filter.
            status: Optional status filter.

        Returns:
            Total number of tasks.
        """
        filters = {}
        if period_type:
            filters["period_type"] = period_type
        if status:
            filters["status"] = status

        return await self.repository.count(**filters)

    async def update_task(self, task_id: int, data: TaskUpdate) -> Task:
        """Update an existing task.

        Args:
            task_id: Task ID.
            data: Task update data.

        Returns:
            Updated task entity.

        Raises:
            NotFoundError: If task not found.
            ValidationError: If validation fails.
        """
        # Check if task exists
        existing_task = await self.repository.selectById(task_id)
        if not existing_task:
            raise NotFoundError("Task", task_id)

        # Validate and transform data
        mapper = (
            FieldMapper(data)
            .validate("title", self.task_support.validate_title)
            .validate("description", self.task_support.validate_description)
            .transform("title", self.task_support.format_title)
            .transform("description", self.task_support.format_description)
        )
        update_data = mapper.to_dict()

        if not update_data:
            return existing_task

        # Update task
        updated_task = await self.repository.update(task_id, **update_data)

        # Regenerate embedding if title or description changed
        if "title" in update_data or "description" in update_data:
            try:
                await self._update_task_embedding(updated_task)
            except Exception as e:
                self.logger.warning(
                    f"Failed to update embedding for task {task_id}: {e}"
                )

        self.logger.info(f"Updated task: {task_id}")
        return updated_task

    async def update_task_status(
        self,
        task_id: int,
        data: TaskStatusUpdate,
    ) -> Task:
        """Update task status with optional reason.

        Args:
            task_id: Task ID.
            data: Status update data.

        Returns:
            Updated task entity.

        Raises:
            NotFoundError: If task not found.
        """
        # Check if task exists
        existing_task = await self.repository.selectById(task_id)
        if not existing_task:
            raise NotFoundError("Task", task_id)

        # Convert enum to string value
        status_value = (
            data.status.value if isinstance(data.status, TaskStatus) else data.status
        )

        update_data = {"status": status_value}

        # Set completed_at and completion_note if marking as completed
        if status_value == TaskStatus.COMPLETED.value:
            update_data["completed_at"] = datetime.now(UTC)
            update_data["pending_reason"] = None
            update_data["completion_note"] = data.completion_note
        else:
            update_data["completed_at"] = None
            update_data["completion_note"] = None
            update_data["pending_reason"] = data.pending_reason

        updated_task = await self.repository.update(task_id, **update_data)
        self.logger.info(f"Updated task status: {task_id} -> {status_value}")
        return updated_task

    async def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID.

        Args:
            task_id: Task ID.

        Returns:
            True if deleted.

        Raises:
            NotFoundError: If task not found.
        """
        existing_task = await self.repository.selectById(task_id)
        if not existing_task:
            raise NotFoundError("Task", task_id)

        result = await self.repository.delete(task_id)
        self.logger.info(f"Deleted task: {task_id}")
        return result

    async def get_tasks_by_period(
        self,
        user_id: int,
        period_type: TaskPeriodType | str,
        period_date: date,
    ) -> list[Task]:
        """Get tasks for a specific period.

        Args:
            user_id: User ID to filter by.
            period_type: Type of period.
            period_date: A date within the period.

        Returns:
            List of tasks in the period.
        """
        start_date, end_date = self.task_support.calculate_period_bounds(
            period_type,
            period_date,
        )
        return await self.repository.find_by_period(
            user_id,
            period_type,
            start_date,
            end_date,
        )

    async def search_tasks(
        self,
        user_id: int,
        request: TaskSearchRequest,
    ) -> list[TaskSearchResult]:
        """Search tasks using semantic similarity.

        Args:
            user_id: User ID to filter by.
            request: Search request with query and filters.

        Returns:
            List of search results with similarity scores.
        """
        # Generate embedding for query
        try:
            query_embedding = await self.embedding_support.generate_embedding(
                request.query
            )
        except Exception as e:
            self.logger.error(f"Failed to generate query embedding: {e}")
            raise ValidationError(f"Failed to process search query: {e}")

        # Convert enums to string values
        period_type = None
        if request.period_type:
            period_type = (
                request.period_type.value
                if isinstance(request.period_type, TaskPeriodType)
                else request.period_type
            )

        status = None
        if request.status:
            status = (
                request.status.value
                if isinstance(request.status, TaskStatus)
                else request.status
            )

        # Perform semantic search
        results = await self.repository.semantic_search(
            user_id=user_id,
            query_embedding=query_embedding,
            limit=request.limit,
            period_type=period_type,
            status=status,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        # Convert to response format
        return [
            TaskSearchResult(
                task=TaskResponse.model_validate(task),
                similarity_score=score,
            )
            for task, score in results
        ]

    async def generate_report(
        self,
        user_id: int,
        request: TaskReportRequest,
    ) -> TaskReportResponse:
        """Generate a task report for a period.

        Args:
            user_id: User ID to filter by.
            request: Report request with period and date range.

        Returns:
            Report with summary and task lists.
        """
        # Get period type value
        period_type = (
            request.period_type.value
            if isinstance(request.period_type, TaskPeriodType)
            else request.period_type
        )

        # Get statistics
        stats = await self.repository.get_period_stats(
            user_id,
            period_type,
            request.start_date,
            request.end_date,
        )

        # Get completed tasks
        completed_tasks = await self.repository.find_by_period(
            user_id,
            period_type,
            request.start_date,
            request.end_date,
            status=TaskStatus.COMPLETED,
        )

        # Get pending tasks
        pending_tasks = await self.repository.find_by_period(
            user_id,
            period_type,
            request.start_date,
            request.end_date,
            status=TaskStatus.PENDING,
        )

        # Calculate completion rate
        completion_rate = self.task_support.calculate_completion_rate(
            stats["completed"],
            stats["total"],
        )

        return TaskReportResponse(
            period_type=period_type,
            period_start=request.start_date,
            period_end=request.end_date,
            summary=TaskReportSummary(
                total_tasks=stats["total"],
                completed=stats["completed"],
                pending=stats["pending"],
                completion_rate=completion_rate,
            ),
            completed_tasks=[
                TaskResponse.model_validate(task) for task in completed_tasks
            ],
            pending_tasks=[TaskResponse.model_validate(task) for task in pending_tasks],
        )

    async def _update_task_embedding(self, task: Task) -> None:
        """Generate and update embedding for a task.

        Args:
            task: Task to update embedding for.
        """
        # Combine title and description for embedding
        text = self.embedding_support.combine_text_for_embedding(
            task.title,
            task.description,
        )

        # Generate embedding
        embedding = await self.embedding_support.generate_embedding(text)

        # Update task with embedding
        await self.repository.update_embedding(task.id, embedding)
        self.logger.debug(f"Updated embedding for task: {task.id}")

    async def create_multiple_tasks(
        self,
        user_id: int,
        titles: list[str],
        category: str,
        period_type: TaskPeriodType | str,
        period_date: date,
        priorities: list[TaskPriority | str] | None = None,
        durations: list[int | None] | None = None,
        scheduled_times: list[time | None] | None = None,
        scheduled_end_times: list[time | None] | None = None,
        scheduled_dates: list[date | None] | None = None,
    ) -> list[Task]:
        """Create multiple tasks at once with optional scheduling.

        Args:
            user_id: User ID who owns these tasks.
            titles: List of task titles.
            category: Task category for all tasks.
            period_type: Period type for all tasks.
            period_date: Period date for all tasks.
            priorities: Optional list of priorities (parallel to titles).
            durations: Optional list of durations in minutes.
            scheduled_times: Optional list of start times.
            scheduled_end_times: Optional list of end times.
            scheduled_dates: Optional list of scheduled dates.

        Returns:
            List of created tasks.
        """
        # Convert period_type to enum if string
        if isinstance(period_type, str):
            period_type = TaskPeriodType(period_type)

        tasks = []
        for i, title in enumerate(titles):
            # Get scheduling fields for this task (if provided)
            priority = TaskPriority.NORMAL
            if priorities and i < len(priorities):
                p = priorities[i]
                if isinstance(p, str):
                    priority = TaskPriority(p)
                elif p:
                    priority = p

            duration = durations[i] if durations and i < len(durations) else None
            sched_time = (
                scheduled_times[i] if scheduled_times and i < len(scheduled_times)
                else None
            )
            sched_end = (
                scheduled_end_times[i]
                if scheduled_end_times and i < len(scheduled_end_times)
                else None
            )
            sched_date = (
                scheduled_dates[i] if scheduled_dates and i < len(scheduled_dates)
                else None
            )

            task_data = TaskCreate(
                user_id=user_id,
                title=title,
                category=category,
                period_type=period_type,
                period_date=period_date,
                priority=priority,
                duration_minutes=duration,
                scheduled_time=sched_time,
                scheduled_end_time=sched_end,
                scheduled_date=sched_date,
            )
            task = await self.create_task(task_data)
            tasks.append(task)

        self.logger.info(f"Created {len(tasks)} tasks in category '{category}'")
        return tasks

    async def get_task_by_period_number(
        self,
        user_id: int,
        period_number: int,
        period_type: TaskPeriodType | str,
        period_date: date,
    ) -> Task | None:
        """Get task by its position (1-based) in the period.

        Args:
            user_id: User ID to filter by.
            period_number: 1-based position in the period list.
            period_type: Type of period.
            period_date: A date within the period.

        Returns:
            Task at the given position, or None if not found.
        """
        start_date, end_date = self.task_support.calculate_period_bounds(
            period_type,
            period_date,
        )

        # Convert to string for repository
        if isinstance(period_type, TaskPeriodType):
            period_type_str = period_type.value
        else:
            period_type_str = period_type

        return await self.repository.find_task_by_period_number(
            user_id,
            period_number,
            period_type_str,
            start_date,
            end_date,
        )

    async def get_period_stats_quick(
        self,
        user_id: int,
        period_type: TaskPeriodType | str,
        period_date: date,
    ) -> dict[str, int]:
        """Get quick statistics for a period.

        Args:
            user_id: User ID to filter by.
            period_type: Type of period.
            period_date: A date within the period.

        Returns:
            Dictionary with total and completed counts.
        """
        start_date, end_date = self.task_support.calculate_period_bounds(
            period_type,
            period_date,
        )

        # Convert to string for repository
        if isinstance(period_type, TaskPeriodType):
            period_type_str = period_type.value
        else:
            period_type_str = period_type

        total = await self.repository.count_by_period(
            user_id,
            period_type_str,
            start_date,
            end_date,
        )
        completed = await self.repository.count_by_period(
            user_id,
            period_type_str,
            start_date,
            end_date,
            status=TaskStatus.COMPLETED,
        )

        return {
            "total": total,
            "completed": completed,
            "pending": total - completed,
        }
