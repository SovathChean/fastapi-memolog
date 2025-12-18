"""Telegram support module for bot interactions."""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum

from app.models.schemas.task import (
    TaskPeriodType,
    TaskPriority,
    TaskResponse,
    TaskSearchResult,
)


class TelegramCommand(str, Enum):
    """Supported Telegram bot commands."""

    ADD = "/add"
    DAILY = "/daily"
    WEEKLY = "/weekly"
    MONTHLY = "/monthly"
    DONE = "/done"
    PENDING = "/pending"
    SEARCH = "/search"
    REPORT = "/report"
    HELP = "/help"
    START = "/start"


@dataclass
class ParsedCommand:
    """Parsed Telegram command with arguments."""

    command: TelegramCommand | None
    args: str
    is_natural_text: bool = False


@dataclass
class ParsedTaskDetails:
    """Parsed task details from natural language input."""

    title: str
    priority: TaskPriority = TaskPriority.NORMAL
    duration_minutes: int | None = None
    scheduled_time: time | None = None
    scheduled_end_time: time | None = None
    scheduled_date: date | None = None
    end_date: date | None = None


class TelegramSupport:
    """Support class for Telegram bot operations.

    Provides functionality for parsing commands and formatting responses.
    """

    COMMAND_PATTERN = re.compile(r"^(/\w+)\s*(.*)?$", re.DOTALL)
    PERIOD_KEYWORDS = {"daily", "weekly", "monthly"}
    PRIORITY_KEYWORDS = {"low", "high"}  # normal is default

    # Regex patterns for parsing task details
    # Time pattern: "at 8pm", "at 20:00", "at 8:30am"
    TIME_PATTERN = re.compile(
        r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        re.IGNORECASE,
    )
    # Time range pattern: "at 8pm to 12am", "at 20:00 to 23:00"
    TIME_RANGE_PATTERN = re.compile(
        r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+to\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        re.IGNORECASE,
    )
    # Duration pattern: "30m", "2h", "1h30m", "30min", "2hours", "1hour30min"
    DURATION_PATTERN = re.compile(
        r"\b(\d+)\s*h(?:ours?|r)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?|\b(\d+)\s*m(?:in(?:utes?)?)?\b",
        re.IGNORECASE,
    )
    # Date pattern: "tomorrow", "on 2024-01-20", "on Jan 20"
    DATE_ON_PATTERN = re.compile(
        r"\bon\s+(\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2}(?:,?\s+\d{4})?)\b",
        re.IGNORECASE,
    )
    TOMORROW_PATTERN = re.compile(r"\btomorrow\b", re.IGNORECASE)

    # Due date pattern: "due 3d", "due: +3d", "due tomorrow", "due at 20-12-2025"
    # Supports: due/due:/due at + relative (3d, +3d, 3d+, 1w) or absolute dates
    DUE_DATE_PATTERN = re.compile(
        r"\bdue(?::\s*|(?:\s+at)?\s+)(\+?\d+[dw]\+?|\d{1,2}-\d{1,2}-\d{4}|\d{4}-\d{1,2}-\d{1,2}|tomorrow|next\s+\w+)",
        re.IGNORECASE,
    )

    # Day name mapping for "next tuesday" etc
    DAY_NAMES = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    def parse_add_command(self, text: str) -> tuple[TaskPeriodType, str, list[str]]:
        """Parse /add command arguments to extract period, category, and tasks.

        Supports formats:
        - "Work task1, task2" → (DAILY, "Work", ["task1", "task2"])
        - "weekly Work task1, task2" → (WEEKLY, "Work", ["task1", "task2"])
        - "monthly Personal task1" → (MONTHLY, "Personal", ["task1"])
        - "task1, task2" → (DAILY, "General", ["task1", "task2"])
        - "daily task1" → (DAILY, "General", ["task1"])

        Args:
            text: Raw arguments after /add command.

        Returns:
            Tuple of (period_type, category, list_of_task_titles).
        """
        if not text or not text.strip():
            return TaskPeriodType.DAILY, "General", []

        text = text.strip()
        words = text.split()

        period_type = TaskPeriodType.DAILY
        category = "General"
        tasks_text = text

        # Check first word for period keyword
        if words and words[0].lower() in self.PERIOD_KEYWORDS:
            period_type = TaskPeriodType(words[0].lower())
            words = words[1:]
            tasks_text = " ".join(words) if words else ""

        # Check next word for category (capitalized, single word before comma/tasks)
        if words:
            first_word = words[0]
            # Category detection: starts with uppercase, doesn't contain comma
            if (
                first_word[0].isupper()
                and "," not in first_word
                and first_word.lower() not in self.PERIOD_KEYWORDS
            ):
                category = first_word
                words = words[1:]
                tasks_text = " ".join(words) if words else ""

        # Parse comma-separated tasks
        if tasks_text:
            tasks = [t.strip() for t in tasks_text.split(",") if t.strip()]
        else:
            tasks = []

        return period_type, category, tasks

    def parse_task_details(self, task_text: str) -> ParsedTaskDetails:
        """Parse task text to extract title, priority, time, duration, date.

        Extracts scheduling information from natural language task input.

        Args:
            task_text: Raw task text (e.g., "meeting high at 2pm 1h tomorrow").

        Returns:
            ParsedTaskDetails with extracted information.
        """
        if not task_text or not task_text.strip():
            return ParsedTaskDetails(title="")

        text = task_text.strip()
        remaining = text

        # Extract priority (high, low - normal is default)
        priority = TaskPriority.NORMAL
        for kw in self.PRIORITY_KEYWORDS:
            pattern = re.compile(rf"\b{kw}\b", re.IGNORECASE)
            if pattern.search(remaining):
                priority = TaskPriority(kw)
                remaining = pattern.sub("", remaining)
                break

        # Extract due date (end_date) FIRST - before time patterns to avoid conflicts
        # e.g., "due at 24-12-2025" would otherwise match TIME_PATTERN on "at 24"
        end_date = None
        due_match = self.DUE_DATE_PATTERN.search(remaining)
        if due_match:
            end_date = self._parse_due_date(due_match.group(1))
            remaining = self.DUE_DATE_PATTERN.sub("", remaining)

        # Extract time range first (at X to Y)
        scheduled_time = None
        scheduled_end_time = None
        time_range_match = self.TIME_RANGE_PATTERN.search(remaining)
        if time_range_match:
            scheduled_time = self._parse_time_match(
                time_range_match.group(1),
                time_range_match.group(2),
                time_range_match.group(3),
            )
            scheduled_end_time = self._parse_time_match(
                time_range_match.group(4),
                time_range_match.group(5),
                time_range_match.group(6),
            )
            remaining = self.TIME_RANGE_PATTERN.sub("", remaining)
        else:
            # Extract single time (at X)
            time_match = self.TIME_PATTERN.search(remaining)
            if time_match:
                scheduled_time = self._parse_time_match(
                    time_match.group(1),
                    time_match.group(2),
                    time_match.group(3),
                )
                remaining = self.TIME_PATTERN.sub("", remaining)

        # Extract duration (e.g., 2h, 30m, 1h30m)
        duration_minutes = None
        duration_match = self.DURATION_PATTERN.search(remaining)
        if duration_match:
            duration_minutes = self._parse_duration_match(duration_match)
            remaining = self.DURATION_PATTERN.sub("", remaining)

        # Extract date
        scheduled_date = None
        if self.TOMORROW_PATTERN.search(remaining):
            scheduled_date = date.today() + timedelta(days=1)
            remaining = self.TOMORROW_PATTERN.sub("", remaining)
        else:
            date_match = self.DATE_ON_PATTERN.search(remaining)
            if date_match:
                scheduled_date = self._parse_date_match(date_match.group(1))
                remaining = self.DATE_ON_PATTERN.sub("", remaining)

        # Clean up remaining text as title
        title = " ".join(remaining.split()).strip()

        return ParsedTaskDetails(
            title=title,
            priority=priority,
            duration_minutes=duration_minutes,
            scheduled_time=scheduled_time,
            scheduled_end_time=scheduled_end_time,
            scheduled_date=scheduled_date,
            end_date=end_date,
        )

    def _parse_time_match(
        self,
        hour_str: str,
        minute_str: str | None,
        ampm: str | None,
    ) -> time | None:
        """Parse time components from regex match.

        Args:
            hour_str: Hour string (e.g., "8", "20").
            minute_str: Minute string or None (e.g., "30").
            ampm: AM/PM indicator or None.

        Returns:
            time object or None if parsing fails.
        """
        try:
            hour = int(hour_str)
            minute = int(minute_str) if minute_str else 0

            # Handle AM/PM conversion
            if ampm:
                ampm_lower = ampm.lower()
                if ampm_lower == "pm" and hour < 12:
                    hour += 12
                elif ampm_lower == "am" and hour == 12:
                    hour = 0

            # Validate hour/minute
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return time(hour=hour, minute=minute)
        except (ValueError, TypeError):
            pass
        return None

    def _parse_duration_match(self, match: re.Match) -> int | None:
        """Parse duration from regex match.

        Args:
            match: Regex match object with duration groups.

        Returns:
            Duration in minutes or None.
        """
        try:
            hours = int(match.group(1)) if match.group(1) else 0
            minutes_from_hours = int(match.group(2)) if match.group(2) else 0
            minutes_only = int(match.group(3)) if match.group(3) else 0

            if hours > 0 or minutes_from_hours > 0:
                return hours * 60 + minutes_from_hours
            elif minutes_only > 0:
                return minutes_only
        except (ValueError, TypeError):
            pass
        return None

    def _parse_date_match(self, date_str: str) -> date | None:
        """Parse date from string.

        Args:
            date_str: Date string (e.g., "2024-01-20", "Jan 20").

        Returns:
            date object or None if parsing fails.
        """
        # Try ISO format first (2024-01-20)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        # Try "Jan 20" format
        try:
            parsed = datetime.strptime(date_str, "%b %d")
            return parsed.replace(year=date.today().year).date()
        except ValueError:
            pass

        # Try "January 20" format
        try:
            parsed = datetime.strptime(date_str, "%B %d")
            return parsed.replace(year=date.today().year).date()
        except ValueError:
            pass

        # Try "Jan 20, 2024" format
        try:
            return datetime.strptime(date_str, "%b %d, %Y").date()
        except ValueError:
            pass

        return None

    def _parse_due_date(self, due_str: str) -> date | None:
        """Parse due date from various formats.

        Supports:
        - Relative: 3d, +3d, 3d+ (3 days), 1w, +1w (1 week)
        - Natural: tomorrow, next tuesday
        - Specific: 20-12-2025 (DD-MM-YYYY) or 2025-12-20 (YYYY-MM-DD)

        Args:
            due_str: Due date string from regex match.

        Returns:
            date object or None if parsing fails.
        """
        if not due_str:
            return None

        due_str = due_str.strip().lower()
        today = date.today()

        # Handle "tomorrow"
        if due_str == "tomorrow":
            return today + timedelta(days=1)

        # Handle relative format: 3d, +3d, 3d+, 1w, +1w
        # Strip leading/trailing + and check for d/w suffix
        relative_str = due_str.strip("+")
        if relative_str and relative_str[-1] in ("d", "w"):
            try:
                num = int(relative_str[:-1])
                unit = relative_str[-1]
                if unit == "d":
                    return today + timedelta(days=num)
                elif unit == "w":
                    return today + timedelta(weeks=num)
            except (ValueError, IndexError):
                pass

        # Handle "next tuesday" etc
        if due_str.startswith("next "):
            day_name = due_str[5:].strip()
            if day_name in self.DAY_NAMES:
                target_weekday = self.DAY_NAMES[day_name]
                current_weekday = today.weekday()
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                return today + timedelta(days=days_ahead)

        # Handle DD-MM-YYYY format (e.g., 20-12-2025)
        try:
            return datetime.strptime(due_str, "%d-%m-%Y").date()
        except ValueError:
            pass

        # Handle YYYY-MM-DD format (e.g., 2025-12-20)
        try:
            return datetime.strptime(due_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        return None

    def parse_message(self, text: str) -> ParsedCommand:
        """Parse incoming message to extract command and arguments.

        Args:
            text: Message text from Telegram.

        Returns:
            ParsedCommand with command type and arguments.
        """
        if not text:
            return ParsedCommand(command=None, args="", is_natural_text=True)

        text = text.strip()

        # Check if it's a command
        match = self.COMMAND_PATTERN.match(text)
        if match:
            cmd_str = match.group(1).lower()
            args = (match.group(2) or "").strip()

            # Map to command enum
            try:
                command = TelegramCommand(cmd_str)
                return ParsedCommand(command=command, args=args)
            except ValueError:
                # Unknown command, treat as natural text
                return ParsedCommand(command=None, args=text, is_natural_text=True)

        # Natural language text
        return ParsedCommand(command=None, args=text, is_natural_text=True)

    def format_task_with_number(
        self,
        task: TaskResponse,
        number: int,
        include_details: bool = False,
    ) -> str:
        """Format a single task with sequential number for Telegram display.

        Args:
            task: Task to format.
            number: Sequential number (1-based) to display.
            include_details: Whether to include full details.

        Returns:
            Formatted task string.
        """
        status_emoji = "✅" if task.status == "completed" else "⏳"

        # Build main line with compact indicators (always shown)
        line = f"{status_emoji} {number}. {task.title}"

        # Always show priority indicator (only high/low, not normal)
        if task.priority == "high":
            line += " 🔴"
        elif task.priority == "low":
            line += " 🟢"

        # Always show duration if set (compact format)
        if task.duration_minutes:
            line += f" {self._format_duration(task.duration_minutes)}"

        lines = [line]

        if include_details:
            if task.description:
                lines.append(f"   📝 {task.description}")

            # Show time if set (detailed view)
            time_parts = []
            if task.scheduled_time:
                time_str = self._format_time_display(task.scheduled_time)
                if task.scheduled_end_time:
                    end_str = self._format_time_display(task.scheduled_end_time)
                    time_parts.append(f"{time_str} - {end_str}")
                else:
                    time_parts.append(time_str)
            if time_parts:
                lines.append(f"   ⏰ {' '.join(time_parts)}")

            # Show scheduled date if different from period_date
            if task.scheduled_date and task.scheduled_date != task.period_date:
                lines.append(f"   📅 Scheduled: {task.scheduled_date}")
            else:
                lines.append(f"   📅 {task.period_date} ({task.period_type})")

            if task.status == "completed" and task.completed_at:
                completed_time = task.completed_at.strftime("%Y-%m-%d %H:%M")
                lines.append(f"   ✔️ Completed: {completed_time}")
            elif task.pending_reason:
                lines.append(f"   ⚠️ Reason: {task.pending_reason}")

        return "\n".join(lines)

    def _format_time_display(self, t: time) -> str:
        """Format time for display (12-hour format).

        Args:
            t: Time object.

        Returns:
            Formatted time string like "2:30 PM".
        """
        hour = t.hour
        minute = t.minute
        period = "AM" if hour < 12 else "PM"
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        if minute == 0:
            return f"{hour} {period}"
        return f"{hour}:{minute:02d} {period}"

    def _format_duration(self, minutes: int) -> str:
        """Format duration in minutes to human-readable string.

        Args:
            minutes: Duration in minutes.

        Returns:
            Formatted duration string like "1h 30m" or "45m".
        """
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        remaining = minutes % 60
        if remaining == 0:
            return f"{hours}h"
        return f"{hours}h {remaining}m"

    def format_task(self, task: TaskResponse, include_details: bool = False) -> str:
        """Format a single task for Telegram display (legacy, uses DB ID).

        Args:
            task: Task to format.
            include_details: Whether to include full details.

        Returns:
            Formatted task string.
        """
        status_emoji = "✅" if task.status == "completed" else "⏳"
        lines = [f"{status_emoji} #{task.id} {task.title}"]

        if include_details:
            if task.description:
                lines.append(f"   📝 {task.description}")
            lines.append(f"   📅 {task.period_date} ({task.period_type})")
            if task.status == "completed" and task.completed_at:
                completed_time = task.completed_at.strftime("%Y-%m-%d %H:%M")
                lines.append(f"   ✔️ Completed: {completed_time}")
            elif task.pending_reason:
                lines.append(f"   ⚠️ Reason: {task.pending_reason}")

        return "\n".join(lines)

    def format_task_list(
        self,
        tasks: list[TaskResponse],
        title: str = "Tasks",
        include_details: bool = False,
        group_by_category: bool = True,
    ) -> str:
        """Format a list of tasks for Telegram display with sequential numbers.

        Args:
            tasks: List of tasks to format.
            title: Title for the list.
            include_details: Whether to include full details.
            group_by_category: Whether to group tasks by category.

        Returns:
            Formatted task list string.
        """
        if not tasks:
            return f"📋 {title}\n\nNo tasks found."

        lines = [f"📋 {title}", ""]

        # Calculate stats
        completed = sum(1 for t in tasks if t.status == "completed")
        pending = len(tasks) - completed

        if group_by_category:
            # Group by category while maintaining global numbering
            # Use id as tie-breaker for deterministic ordering when created_at is same
            sorted_tasks = sorted(tasks, key=lambda t: (t.category, t.created_at, t.id))
            current_category = None
            global_number = 0

            for task in sorted_tasks:
                global_number += 1
                if task.category != current_category:
                    current_category = task.category
                    lines.append(f"📁 {current_category}:")

                formatted = self.format_task_with_number(
                    task, global_number, include_details
                )
                lines.append(f"  {formatted}")
        else:
            for i, task in enumerate(tasks, 1):
                lines.append(self.format_task_with_number(task, i, include_details))

        lines.append("")
        total = len(tasks)
        lines.append(f"Pending: {pending} | Completed: {completed} | Total: {total}")

        return "\n".join(lines)

    def format_bulk_creation_response(
        self,
        tasks: list[TaskResponse],
        period_type: str,
        category: str,
        total_in_period: int,
        completed_in_period: int,
    ) -> str:
        """Format response for bulk task creation.

        Args:
            tasks: List of created tasks.
            period_type: Period type (daily, weekly, monthly).
            category: Task category.
            total_in_period: Total tasks in the period after creation.
            completed_in_period: Completed tasks in the period.

        Returns:
            Formatted response string.
        """
        if not tasks:
            return "❌ No tasks created."

        count = len(tasks)
        period_label = self._get_period_label(period_type)

        plural = "s" if count > 1 else ""
        lines = [f"✅ Created {count} {period_type} task{plural} [{category}]:"]

        for i, task in enumerate(tasks, 1):
            lines.append(f"  {i}. {task.title}")

        pending = total_in_period - completed_in_period
        lines.append("")
        stats = f"{pending} pending, {completed_in_period} completed"
        lines.append(f"📊 {period_label}: {stats}")

        return "\n".join(lines)

    def format_task_done_response(
        self,
        task: TaskResponse,
        total_in_period: int,
        completed_in_period: int,
        period_type: str = "daily",
    ) -> str:
        """Format response for marking a task as done.

        Args:
            task: The completed task.
            total_in_period: Total tasks in the period.
            completed_in_period: Completed tasks in the period.
            period_type: Period type.

        Returns:
            Formatted response string.
        """
        period_label = self._get_period_label(period_type)
        pending = total_in_period - completed_in_period

        lines = [
            f'✅ Completed: "{task.title}" [{task.category}]',
        ]

        # Add completion note if provided
        if task.completion_note:
            lines.append(f"📝 Note: {task.completion_note}")

        lines.extend(
            [
                "",
                f"📊 {period_label}: {pending} pending, {completed_in_period} done",
            ]
        )

        return "\n".join(lines)

    def format_bulk_done_response(
        self,
        completed_tasks: list[tuple[TaskResponse, str | None]],
        failed_tasks: list[tuple[int, str]],
        total_in_period: int,
        completed_in_period: int,
        period_type: str = "daily",
    ) -> str:
        """Format response for bulk task completion.

        Args:
            completed_tasks: List of (task, note) tuples for completed tasks.
            failed_tasks: List of (task_number, error_message) tuples.
            total_in_period: Total tasks in the period.
            completed_in_period: Completed tasks in the period.
            period_type: Period type (daily, weekly, monthly).

        Returns:
            Formatted response string.
        """
        lines = []

        # Show completed tasks
        if completed_tasks:
            count = len(completed_tasks)
            plural = "s" if count > 1 else ""
            lines.append(f"✅ Completed {count} task{plural}:")
            lines.append("")

            for task, note in completed_tasks:
                lines.append(f"  • {task.title} [{task.category}]")
                if note:
                    lines.append(f"    📝 {note}")

        # Show failed tasks
        if failed_tasks:
            if lines:
                lines.append("")
            lines.append("❌ Failed:")
            for task_num, error in failed_tasks:
                lines.append(f"  #{task_num}: {error}")

        # Show stats
        if completed_tasks or failed_tasks:
            period_label = self._get_period_label(period_type)
            pending = total_in_period - completed_in_period
            lines.append("")
            lines.append(
                f"📊 {period_label}: {pending} pending, {completed_in_period} completed"
            )
        else:
            lines.append("No tasks were updated.")

        return "\n".join(lines)

    def format_bulk_pending_response(
        self,
        pending_tasks: list[tuple[TaskResponse, str | None]],
        failed_tasks: list[tuple[int, str]],
        period_type: str = "daily",
    ) -> str:
        """Format response for bulk task pending update.

        Args:
            pending_tasks: List of (task, reason) tuples.
            failed_tasks: List of (task_number, error_message) tuples.
            period_type: Period type (daily, weekly, monthly).

        Returns:
            Formatted response string.
        """
        lines = []

        if pending_tasks:
            count = len(pending_tasks)
            plural = "s" if count > 1 else ""
            lines.append(f"⏳ Marked {count} task{plural} as pending:")
            lines.append("")

            for task, reason in pending_tasks:
                lines.append(f"  • {task.title} [{task.category}]")
                if reason:
                    lines.append(f"    📝 {reason}")

        if failed_tasks:
            if lines:
                lines.append("")
            lines.append("❌ Failed:")
            for task_num, error in failed_tasks:
                lines.append(f"  #{task_num}: {error}")

        if not pending_tasks and not failed_tasks:
            lines.append("No tasks were updated.")

        return "\n".join(lines)

    def format_task_pending_response(
        self,
        task: TaskResponse,
        reason: str | None = None,
    ) -> str:
        """Format response for marking a task as pending.

        Args:
            task: The task marked as pending.
            reason: Optional reason for pending status.

        Returns:
            Formatted response string.
        """
        lines = [f'⏳ Pending: "{task.title}" [{task.category}]']

        if reason:
            lines.append(f"Reason: {reason}")

        return "\n".join(lines)

    def _get_period_label(self, period_type: str) -> str:
        """Get human-readable period label.

        Args:
            period_type: Period type string.

        Returns:
            Human-readable label.
        """
        labels = {
            "daily": "Today",
            "weekly": "This week",
            "monthly": "This month",
        }
        return labels.get(period_type, period_type.title())

    def format_search_results(
        self,
        results: list[TaskSearchResult],
    ) -> str:
        """Format search results for Telegram display.

        Args:
            results: Search results to format.

        Returns:
            Formatted search results string.
        """
        if not results:
            return "🔍 No matching tasks found."

        lines = ["🔍 Search Results", ""]
        for result in results:
            score_bar = self._score_to_bar(result.similarity_score)
            lines.append(f"{score_bar} {self.format_task(result.task)}")
            lines.append("")

        return "\n".join(lines)

    def format_report(
        self,
        period_type: str,
        start_date: date,
        end_date: date,
        total: int,
        completed: int,
        pending: int,
        completion_rate: float,
        completed_tasks: list[TaskResponse],
        pending_tasks: list[TaskResponse],
    ) -> str:
        """Format a report for Telegram display.

        Args:
            period_type: Report period type.
            start_date: Report start date.
            end_date: Report end date.
            total: Total tasks.
            completed: Completed tasks count.
            pending: Pending tasks count.
            completion_rate: Completion rate percentage.
            completed_tasks: List of completed tasks.
            pending_tasks: List of pending tasks.

        Returns:
            Formatted report string.
        """
        progress_bar = self._progress_bar(completion_rate)

        lines = [
            f"📊 {period_type.title()} Report",
            f"📅 {start_date} to {end_date}",
            "",
            "📈 Summary",
            f"   Total: {total} tasks",
            f"   ✅ Completed: {completed}",
            f"   ⏳ Pending: {pending}",
            f"   {progress_bar} {completion_rate:.1f}%",
            "",
        ]

        if completed_tasks:
            lines.append("✅ Completed Tasks:")
            for task in completed_tasks[:5]:  # Limit to 5
                lines.append(f"   • {task.title}")
            if len(completed_tasks) > 5:
                lines.append(f"   ... and {len(completed_tasks) - 5} more")
            lines.append("")

        if pending_tasks:
            lines.append("⏳ Pending Tasks:")
            for task in pending_tasks[:5]:  # Limit to 5
                reason = f" ({task.pending_reason})" if task.pending_reason else ""
                lines.append(f"   • {task.title}{reason}")
            if len(pending_tasks) > 5:
                lines.append(f"   ... and {len(pending_tasks) - 5} more")

        return "\n".join(lines)

    def format_help(self) -> str:
        """Format help message for Telegram.

        Returns:
            Help message string.
        """
        return """📝 Memolog - Task Tracking Bot

📌 Adding Tasks:
/add Category task1, task2, task3
/add weekly Category task1, task2
/add monthly Category task1

⏰ Scheduling Options:
• Priority: high, low (normal is default)
• Time: at 2pm, at 14:30
• Time range: at 8pm to 12am
• Duration: 30m, 2h, 1h30m
• Date: tomorrow, on 2024-01-20

📋 Listing Tasks:
/daily - Show today's tasks
/weekly - Show this week's tasks
/monthly - Show this month's tasks

✅ Completing Tasks:
/done [number] - Mark task as completed
/pending [number] [reason] - Mark as pending

🔍 Search & AI:
/search [query] - Search tasks
/ask [question] - Ask about your tasks
/report [daily|weekly|monthly] - Generate report
/help - Show this help message

💡 Examples:
• /add Work Review PR high at 2pm 1h
• /add meeting at 10am to 12pm
• /add weekly Personal gym low at 6am
• /add task1 tomorrow, task2 30m
• /done 1
• /pending 2 Blocked by API
"""

    def format_success(self, message: str) -> str:
        """Format success message.

        Args:
            message: Success message.

        Returns:
            Formatted success string.
        """
        return f"✅ {message}"

    def format_error(self, message: str) -> str:
        """Format error message.

        Args:
            message: Error message.

        Returns:
            Formatted error string.
        """
        return f"❌ {message}"

    def _score_to_bar(self, score: float) -> str:
        """Convert similarity score to visual bar.

        Args:
            score: Score between 0 and 1.

        Returns:
            Visual bar string.
        """
        filled = int(score * 5)
        empty = 5 - filled
        return "🟢" * filled + "⚪" * empty

    def _progress_bar(self, percentage: float) -> str:
        """Create a progress bar from percentage.

        Args:
            percentage: Percentage value (0-100).

        Returns:
            Progress bar string.
        """
        filled = int(percentage / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty

    def get_period_type_from_command(
        self,
        command: TelegramCommand,
    ) -> TaskPeriodType | None:
        """Get period type from command.

        Args:
            command: Telegram command.

        Returns:
            TaskPeriodType or None.
        """
        mapping = {
            TelegramCommand.DAILY: TaskPeriodType.DAILY,
            TelegramCommand.WEEKLY: TaskPeriodType.WEEKLY,
            TelegramCommand.MONTHLY: TaskPeriodType.MONTHLY,
        }
        return mapping.get(command)

    def format_enhanced_search_results(
        self,
        results: list[TaskSearchResult],
        ai_summary: str = "",
    ) -> str:
        """Format search results with AI summary.

        Args:
            results: Search results with similarity scores.
            ai_summary: AI-generated summary.

        Returns:
            Formatted search results string with AI summary.
        """
        lines = ["🔍 Search Results", ""]

        # Add AI summary if available
        if ai_summary:
            lines.append("🤖 AI Summary:")
            lines.append(ai_summary)
            lines.append("")

        if not results:
            lines.append("No matching tasks found.")
            return "\n".join(lines)

        lines.append("📋 Matching Tasks:")
        for result in results[:5]:  # Limit for Telegram display
            score_bar = self._score_to_bar(result.similarity_score)
            status_emoji = "✅" if result.task.status == "completed" else "⏳"
            category = f"[{result.task.category}]" if result.task.category else ""
            lines.append(f"{score_bar} {status_emoji} {result.task.title} {category}")

        if len(results) > 5:
            lines.append(f"... and {len(results) - 5} more")

        return "\n".join(lines)

    def format_ai_response(
        self,
        response: str,
        related_tasks: list[TaskResponse] | None = None,
    ) -> str:
        """Format AI conversational response.

        Args:
            response: AI-generated response text.
            related_tasks: Optional list of related tasks to show.

        Returns:
            Formatted AI response string.
        """
        lines = [f"🤖 {response}"]

        if related_tasks:
            lines.append("")
            lines.append("📋 Related Tasks:")
            for task in related_tasks[:3]:
                status_emoji = "✅" if task.status == "completed" else "⏳"
                lines.append(f"  {status_emoji} {task.title} [{task.category}]")

        return "\n".join(lines)

    def format_greeting_response(self) -> str:
        """Format greeting response for natural language greetings.

        Returns:
            Greeting response string.
        """
        return (
            "👋 Hello! I'm your task management assistant.\n\n"
            "I can help you with:\n"
            "• /add - Create new tasks\n"
            "• /daily, /weekly, /monthly - View tasks\n"
            "• /search - Find tasks\n"
            "• /ask - Ask me anything about your tasks\n"
            "• /done - Mark tasks complete\n\n"
            "Try /help for more commands!"
        )
