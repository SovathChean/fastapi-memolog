"""Task feature routes for memolog."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.v1.controllers.task_controller import TaskController
from app.common.response import PaginatedResponse, ResponseMessage
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

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "/",
    response_model=ResponseMessage[TaskResponse],
    summary="Create a new task",
    description="Create a new task with title, description, and period",
    status_code=201,
)
async def create_task(
    request: TaskCreate,
    controller: TaskController = Depends(),
) -> ResponseMessage[TaskResponse]:
    """Create a new task.

    Args:
        request: Task creation request body.
        controller: Task controller instance.

    Returns:
        ResponseMessage containing created TaskResponse.
    """
    return await controller.create(request)


@router.get(
    "/{task_id}",
    response_model=ResponseMessage[TaskResponse],
    summary="Get task by ID",
    description="Retrieve a task by its ID",
)
async def get_task(
    task_id: Annotated[int, Path(description="Task ID", ge=1)],
    controller: TaskController = Depends(),
) -> ResponseMessage[TaskResponse]:
    """Get task by ID.

    Args:
        task_id: Task ID.
        controller: Task controller instance.

    Returns:
        ResponseMessage containing TaskResponse.
    """
    return await controller.get_by_id(task_id)


@router.get(
    "/",
    response_model=PaginatedResponse[TaskResponse],
    summary="List all tasks",
    description="Retrieve all tasks with pagination and optional filters",
)
async def list_tasks(
    skip: Annotated[
        int,
        Query(ge=0, description="Number of records to skip"),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of records to return"),
    ] = 20,
    period_type: Annotated[
        TaskPeriodType | None,
        Query(description="Filter by period type"),
    ] = None,
    status: Annotated[
        TaskStatus | None,
        Query(description="Filter by status"),
    ] = None,
    controller: TaskController = Depends(),
) -> PaginatedResponse[TaskResponse]:
    """List all tasks with pagination and filters.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        period_type: Optional period type filter.
        status: Optional status filter.
        controller: Task controller instance.

    Returns:
        PaginatedResponse containing list of TaskResponse.
    """
    period_type_value = period_type.value if period_type else None
    status_value = status.value if status else None

    return await controller.get_all(
        skip=skip,
        limit=limit,
        period_type=period_type_value,
        status=status_value,
    )


@router.put(
    "/{task_id}",
    response_model=ResponseMessage[TaskResponse],
    summary="Update a task",
    description="Update an existing task by ID",
)
async def update_task(
    task_id: Annotated[int, Path(description="Task ID", ge=1)],
    request: TaskUpdate,
    controller: TaskController = Depends(),
) -> ResponseMessage[TaskResponse]:
    """Update an existing task.

    Args:
        task_id: Task ID.
        request: Task update request body.
        controller: Task controller instance.

    Returns:
        ResponseMessage containing updated TaskResponse.
    """
    return await controller.update(task_id, request)


@router.patch(
    "/{task_id}/status",
    response_model=ResponseMessage[TaskResponse],
    summary="Update task status",
    description="Update task status with optional pending reason",
)
async def update_task_status(
    task_id: Annotated[int, Path(description="Task ID", ge=1)],
    request: TaskStatusUpdate,
    controller: TaskController = Depends(),
) -> ResponseMessage[TaskResponse]:
    """Update task status.

    Args:
        task_id: Task ID.
        request: Status update request body.
        controller: Task controller instance.

    Returns:
        ResponseMessage containing updated TaskResponse.
    """
    return await controller.update_status(task_id, request)


@router.delete(
    "/{task_id}",
    response_model=ResponseMessage[None],
    summary="Delete a task",
    description="Delete a task by ID",
)
async def delete_task(
    task_id: Annotated[int, Path(description="Task ID", ge=1)],
    controller: TaskController = Depends(),
) -> ResponseMessage[None]:
    """Delete a task by ID.

    Args:
        task_id: Task ID.
        controller: Task controller instance.

    Returns:
        ResponseMessage with success or error.
    """
    return await controller.delete(task_id)


@router.get(
    "/period/{period_type}",
    response_model=ResponseMessage[list[TaskResponse]],
    summary="Get tasks by period",
    description="Get all tasks for a specific period type and date",
)
async def get_tasks_by_period(
    period_type: Annotated[
        TaskPeriodType,
        Path(description="Period type (daily, weekly, monthly)"),
    ],
    period_date: Annotated[
        date,
        Query(description="A date within the period"),
    ],
    controller: TaskController = Depends(),
) -> ResponseMessage[list[TaskResponse]]:
    """Get tasks for a specific period.

    Args:
        period_type: Type of period.
        period_date: A date within the period.
        controller: Task controller instance.

    Returns:
        ResponseMessage containing list of TaskResponse.
    """
    return await controller.get_by_period(period_type, period_date)


@router.post(
    "/search",
    response_model=ResponseMessage[list[TaskSearchResult]],
    summary="Search tasks",
    description="Search tasks using natural language (semantic search)",
)
async def search_tasks(
    request: TaskSearchRequest,
    controller: TaskController = Depends(),
) -> ResponseMessage[list[TaskSearchResult]]:
    """Search tasks using semantic similarity.

    Args:
        request: Search request with query and filters.
        controller: Task controller instance.

    Returns:
        ResponseMessage containing list of TaskSearchResult.
    """
    return await controller.search(request)


@router.post(
    "/reports",
    response_model=ResponseMessage[TaskReportResponse],
    summary="Generate task report",
    description="Generate a report for tasks in a specific period",
)
async def generate_report(
    request: TaskReportRequest,
    controller: TaskController = Depends(),
) -> ResponseMessage[TaskReportResponse]:
    """Generate a task report for a period.

    Args:
        request: Report request with period and date range.
        controller: Task controller instance.

    Returns:
        ResponseMessage containing TaskReportResponse.
    """
    return await controller.generate_report(request)
