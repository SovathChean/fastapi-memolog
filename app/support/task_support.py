"""Task support module with reusable task logic."""

from datetime import date, timedelta

from app.models.domain.task import TaskPeriodType


class TaskSupport:
    """Support class for task-related operations.

    Provides reusable logic for validating task data,
    calculating period boundaries, and formatting.
    """

    def validate_title(self, title: str) -> tuple[bool, str | None]:
        """Validate task title meets business rules.

        Args:
            title: Title to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        if not title:
            return False, "Title cannot be empty"

        stripped = title.strip()
        if len(stripped) == 0:
            return False, "Title cannot be only whitespace"

        if len(stripped) > 255:
            return False, "Title exceeds maximum length of 255 characters"

        if len(stripped) < 1:
            return False, "Title must be at least 1 character"

        return True, None

    def validate_description(
        self,
        description: str | None,
    ) -> tuple[bool, str | None]:
        """Validate task description meets business rules.

        Args:
            description: Description to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        if description is None:
            return True, None

        stripped = description.strip()
        if len(stripped) > 2000:
            return False, "Description exceeds maximum length of 2000 characters"

        return True, None

    def calculate_period_bounds(
        self,
        period_type: TaskPeriodType | str,
        period_date: date,
    ) -> tuple[date, date]:
        """Calculate start and end dates for a period.

        Args:
            period_type: Type of period (daily, weekly, monthly).
            period_date: A date within the period.

        Returns:
            Tuple of (start_date, end_date) for the period.
        """
        if isinstance(period_type, str):
            period_type = TaskPeriodType(period_type)

        if period_type == TaskPeriodType.DAILY:
            return period_date, period_date

        elif period_type == TaskPeriodType.WEEKLY:
            # Week starts on Monday (weekday 0)
            start = period_date - timedelta(days=period_date.weekday())
            end = start + timedelta(days=6)
            return start, end

        elif period_type == TaskPeriodType.MONTHLY:
            # First day of month
            start = period_date.replace(day=1)
            # Last day of month
            if period_date.month == 12:
                end = period_date.replace(year=period_date.year + 1, month=1, day=1)
            else:
                end = period_date.replace(month=period_date.month + 1, day=1)
            end = end - timedelta(days=1)
            return start, end

        raise ValueError(f"Unknown period type: {period_type}")

    def get_period_label(
        self,
        period_type: TaskPeriodType | str,
        period_date: date,
    ) -> str:
        """Get human-readable label for a period.

        Args:
            period_type: Type of period.
            period_date: A date within the period.

        Returns:
            Human-readable period label.
        """
        if isinstance(period_type, str):
            period_type = TaskPeriodType(period_type)

        start, end = self.calculate_period_bounds(period_type, period_date)

        if period_type == TaskPeriodType.DAILY:
            return period_date.strftime("%Y-%m-%d")

        elif period_type == TaskPeriodType.WEEKLY:
            return f"Week of {start.strftime('%Y-%m-%d')}"

        elif period_type == TaskPeriodType.MONTHLY:
            return period_date.strftime("%B %Y")

        return str(period_date)

    def normalize_period_date(
        self,
        period_type: TaskPeriodType | str,
        period_date: date,
    ) -> date:
        """Normalize date to period start date.

        For weekly tasks, returns the Monday of that week.
        For monthly tasks, returns the first day of the month.

        Args:
            period_type: Type of period.
            period_date: Date to normalize.

        Returns:
            Normalized period start date.
        """
        start, _ = self.calculate_period_bounds(period_type, period_date)
        return start

    def format_title(self, title: str) -> str:
        """Format task title.

        Args:
            title: Raw title string.

        Returns:
            Formatted title with stripped whitespace.
        """
        return title.strip()

    def format_description(self, description: str | None) -> str | None:
        """Format task description.

        Args:
            description: Raw description string.

        Returns:
            Formatted description or None.
        """
        if description is None:
            return None
        stripped = description.strip()
        return stripped if stripped else None

    def calculate_completion_rate(
        self,
        completed: int,
        total: int,
    ) -> float:
        """Calculate completion rate as percentage.

        Args:
            completed: Number of completed tasks.
            total: Total number of tasks.

        Returns:
            Completion rate as percentage (0-100).
        """
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 1)
