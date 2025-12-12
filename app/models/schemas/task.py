"""Task feature schemas for memolog."""

from datetime import date, datetime
from enum import Enum

from pydantic import Field, field_validator

from app.models.schemas.base import BaseSchema


class TaskPeriodType(str, Enum):
    """Task period type enumeration."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"


# ============================================================================
# Request Schemas
# ============================================================================


class TaskCreate(BaseSchema):
    """Request model for creating a task."""

    user_id: int = Field(
        ...,
        description="ID of the user who owns this task",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Task title",
        examples=["Review PR #123", "Write documentation"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Task description",
        examples=["Review the authentication changes in PR #123"],
    )
    category: str = Field(
        default="General",
        min_length=1,
        max_length=100,
        description="Task category for grouping",
        examples=["Work", "Personal", "Health", "Shopping"],
    )
    period_type: TaskPeriodType = Field(
        default=TaskPeriodType.DAILY,
        description="Task period type (daily, weekly, monthly)",
    )
    period_date: date = Field(
        ...,
        description="The date this task belongs to",
        examples=["2024-01-15"],
    )


class TaskUpdate(BaseSchema):
    """Request model for updating a task."""

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Task title",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Task description",
    )
    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Task category for grouping",
    )


class TaskStatusUpdate(BaseSchema):
    """Request model for updating task status."""

    status: TaskStatus = Field(
        ...,
        description="New task status",
    )
    pending_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Reason why task is pending (required if status is pending)",
        examples=["Waiting for API finalization", "Blocked by dependency"],
    )
    completion_note: str | None = Field(
        default=None,
        max_length=500,
        description="Optional note when completing a task",
        examples=["Finally done!", "Completed ahead of schedule"],
    )

    @field_validator("pending_reason")
    @classmethod
    def validate_pending_reason(cls, v: str | None, info) -> str | None:
        """Validate pending reason is provided when status is pending."""
        status = info.data.get("status")
        if status == TaskStatus.PENDING and not v:
            # Allow empty reason, but recommend providing one
            pass
        return v


class TaskSearchRequest(BaseSchema):
    """Request model for semantic task search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language search query",
        examples=["tasks about documentation", "what did I complete last week"],
    )
    period_type: TaskPeriodType | None = Field(
        default=None,
        description="Filter by period type",
    )
    status: TaskStatus | None = Field(
        default=None,
        description="Filter by status",
    )
    start_date: date | None = Field(
        default=None,
        description="Filter tasks from this date",
    )
    end_date: date | None = Field(
        default=None,
        description="Filter tasks until this date",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results",
    )


class TaskReportRequest(BaseSchema):
    """Request model for generating task reports."""

    period_type: TaskPeriodType = Field(
        ...,
        description="Report period type",
    )
    start_date: date = Field(
        ...,
        description="Report start date",
    )
    end_date: date = Field(
        ...,
        description="Report end date",
    )


# ============================================================================
# Response Schemas
# ============================================================================


class TaskResponse(BaseSchema):
    """Response model for task endpoints."""

    id: int = Field(..., description="Task ID")
    user_id: int = Field(..., description="Owner user ID")
    title: str = Field(..., description="Task title")
    description: str | None = Field(None, description="Task description")
    category: str = Field(default="General", description="Task category")
    period_type: str = Field(..., description="Task period type")
    period_date: date = Field(..., description="Period date")
    status: str = Field(..., description="Task status")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    pending_reason: str | None = Field(None, description="Reason for pending status")
    completion_note: str | None = Field(None, description="Note added when completing")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TaskSearchResult(BaseSchema):
    """Response model for search results with similarity score."""

    task: TaskResponse = Field(..., description="Task data")
    similarity_score: float = Field(
        ...,
        description="Similarity score (0-1, higher is more similar)",
    )


class TaskReportSummary(BaseSchema):
    """Summary statistics for a task report."""

    total_tasks: int = Field(..., description="Total number of tasks")
    completed: int = Field(..., description="Number of completed tasks")
    pending: int = Field(..., description="Number of pending tasks")
    completion_rate: float = Field(
        ...,
        description="Completion rate as percentage",
        examples=[80.0],
    )


class TaskReportResponse(BaseSchema):
    """Response model for task reports."""

    period_type: str = Field(..., description="Report period type")
    period_start: date = Field(..., description="Report start date")
    period_end: date = Field(..., description="Report end date")
    summary: TaskReportSummary = Field(..., description="Summary statistics")
    completed_tasks: list[TaskResponse] = Field(
        default_factory=list,
        description="List of completed tasks",
    )
    pending_tasks: list[TaskResponse] = Field(
        default_factory=list,
        description="List of pending tasks with reasons",
    )
