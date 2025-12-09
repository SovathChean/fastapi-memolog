"""Task controller for handling HTTP requests."""

from datetime import date

from fastapi import Depends

from app.common.constants import ErrorCodes
from app.common.response import (
    PaginatedResponse,
    ResponseBuilder,
    ResponseMessage,
    handle_request,
)
from app.models.schemas.task import (
    TaskCreate,
    TaskPeriodType,
    TaskReportRequest,
    TaskReportResponse,
    TaskResponse,
    TaskSearchRequest,
    TaskSearchResult,
    TaskStatus,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task_service import TaskService


class TaskController:
    """Controller for task feature endpoints.

    Handles HTTP request/response processing and coordinates with services.
    """

    def __init__(
        self,
        service: TaskService = Depends(),
    ):
        """Initialize controller with dependencies.

        Args:
            service: Task service for business logic.
        """
        self.service = service

    async def create(self, data: TaskCreate) -> ResponseMessage[TaskResponse]:
        """Create a new task.

        Args:
            data: Task creation request data.

        Returns:
            ResponseMessage containing TaskResponse or error.
        """
        return await handle_request(
            action=lambda: self.service.create_task(data),
            response_model=TaskResponse,
            success_message="Task created successfully",
        )

    async def get_by_id(self, task_id: int) -> ResponseMessage[TaskResponse]:
        """Get task by ID.

        Args:
            task_id: Task ID.

        Returns:
            ResponseMessage containing TaskResponse or error.
        """
        return await handle_request(
            action=lambda: self.service.get_task(task_id),
            response_model=TaskResponse,
        )

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        period_type: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[TaskResponse]:
        """Get all tasks with pagination and filters.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            period_type: Optional period type filter.
            status: Optional status filter.

        Returns:
            PaginatedResponse containing list of TaskResponse.
        """
        try:
            tasks = await self.service.get_tasks(
                skip=skip,
                limit=limit,
                period_type=period_type,
                status=status,
            )
            total = await self.service.get_tasks_count(
                period_type=period_type,
                status=status,
            )

            task_responses = [TaskResponse.model_validate(task) for task in tasks]

            total_pages = (total + limit - 1) // limit if limit > 0 else 0
            current_page = (skip // limit) + 1 if limit > 0 else 1

            return (
                ResponseBuilder[list[TaskResponse]]()
                .success()
                .add_data(task_responses)
                .add_page(
                    total_pages=total_pages,
                    page=current_page,
                    page_size=limit,
                    total_items=total,
                )
                .build_paginated()
            )
        except Exception as e:
            return (
                ResponseBuilder[list[TaskResponse]]()
                .fail()
                .add_error_code(ErrorCodes.INTERNAL_ERROR)
                .add_error_message(str(e))
                .build()
            )

    async def update(
        self,
        task_id: int,
        data: TaskUpdate,
    ) -> ResponseMessage[TaskResponse]:
        """Update an existing task.

        Args:
            task_id: Task ID.
            data: Task update request data.

        Returns:
            ResponseMessage containing TaskResponse or error.
        """
        return await handle_request(
            action=lambda: self.service.update_task(task_id, data),
            response_model=TaskResponse,
            success_message="Task updated successfully",
        )

    async def update_status(
        self,
        task_id: int,
        data: TaskStatusUpdate,
    ) -> ResponseMessage[TaskResponse]:
        """Update task status.

        Args:
            task_id: Task ID.
            data: Status update request data.

        Returns:
            ResponseMessage containing TaskResponse or error.
        """
        return await handle_request(
            action=lambda: self.service.update_task_status(task_id, data),
            response_model=TaskResponse,
            success_message="Task status updated successfully",
        )

    async def delete(self, task_id: int) -> ResponseMessage[None]:
        """Delete a task by ID.

        Args:
            task_id: Task ID.

        Returns:
            ResponseMessage with success or error.
        """
        return await handle_request(
            action=lambda: self.service.delete_task(task_id),
            success_message="Task deleted successfully",
        )

    async def get_by_period(
        self,
        period_type: TaskPeriodType,
        period_date: date,
    ) -> ResponseMessage[list[TaskResponse]]:
        """Get tasks for a specific period.

        Args:
            period_type: Type of period.
            period_date: A date within the period.

        Returns:
            ResponseMessage containing list of TaskResponse.
        """
        try:
            tasks = await self.service.get_tasks_by_period(period_type, period_date)
            task_responses = [TaskResponse.model_validate(task) for task in tasks]

            return (
                ResponseBuilder[list[TaskResponse]]()
                .success()
                .add_data(task_responses)
                .build()
            )
        except Exception as e:
            return (
                ResponseBuilder[list[TaskResponse]]()
                .fail()
                .add_error_code(ErrorCodes.INTERNAL_ERROR)
                .add_error_message(str(e))
                .build()
            )

    async def search(
        self,
        request: TaskSearchRequest,
    ) -> ResponseMessage[list[TaskSearchResult]]:
        """Search tasks using semantic similarity.

        Args:
            request: Search request with query and filters.

        Returns:
            ResponseMessage containing list of TaskSearchResult.
        """
        return await handle_request(
            action=lambda: self.service.search_tasks(request),
            success_message="Search completed",
        )

    async def generate_report(
        self,
        request: TaskReportRequest,
    ) -> ResponseMessage[TaskReportResponse]:
        """Generate a task report for a period.

        Args:
            request: Report request with period and date range.

        Returns:
            ResponseMessage containing TaskReportResponse.
        """
        return await handle_request(
            action=lambda: self.service.generate_report(request),
            success_message="Report generated successfully",
        )
