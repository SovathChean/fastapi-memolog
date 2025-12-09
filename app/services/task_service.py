"""Task service with business logic for memolog."""

from datetime import date, datetime, timezone

from fastapi import Depends

from app.common.exceptions import NotFoundError, ValidationError
from app.common.mapper import FieldMapper
from app.models.domain.task import Task, TaskPeriodType, TaskStatus
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
from app.support.embedding_support import EmbeddingSupport, get_embedding_support
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
        self._embedding_support: EmbeddingSupport | None = None

    @property
    def embedding_support(self) -> EmbeddingSupport:
        """Lazy-load embedding support."""
        if self._embedding_support is None:
            self._embedding_support = get_embedding_support()
        return self._embedding_support

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

        # Set default status
        task_data["status"] = TaskStatus.PENDING.value

        # Create task
        task = Task(**task_data)
        created_task = await self.repository.insert(task)

        # Generate embedding asynchronously (best effort)
        try:
            await self._update_task_embedding(created_task)
        except Exception as e:
            self.logger.warning(f"Failed to generate embedding for task {created_task.id}: {e}")

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
                self.logger.warning(f"Failed to update embedding for task {task_id}: {e}")

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
        status_value = data.status.value if isinstance(data.status, TaskStatus) else data.status

        update_data = {"status": status_value}

        # Set completed_at if marking as completed
        if status_value == TaskStatus.COMPLETED.value:
            update_data["completed_at"] = datetime.now(timezone.utc)
            update_data["pending_reason"] = None
        else:
            update_data["completed_at"] = None
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
        period_type: TaskPeriodType | str,
        period_date: date,
    ) -> list[Task]:
        """Get tasks for a specific period.

        Args:
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
            period_type,
            start_date,
            end_date,
        )

    async def search_tasks(
        self,
        request: TaskSearchRequest,
    ) -> list[TaskSearchResult]:
        """Search tasks using semantic similarity.

        Args:
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
        request: TaskReportRequest,
    ) -> TaskReportResponse:
        """Generate a task report for a period.

        Args:
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
            period_type,
            request.start_date,
            request.end_date,
        )

        # Get completed tasks
        completed_tasks = await self.repository.find_by_period(
            period_type,
            request.start_date,
            request.end_date,
            status=TaskStatus.COMPLETED,
        )

        # Get pending tasks
        pending_tasks = await self.repository.find_by_period(
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
            pending_tasks=[
                TaskResponse.model_validate(task) for task in pending_tasks
            ],
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
