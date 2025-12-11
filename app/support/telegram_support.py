"""Telegram support module for bot interactions."""

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.models.schemas.task import TaskPeriodType, TaskResponse, TaskSearchResult


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


class TelegramSupport:
    """Support class for Telegram bot operations.

    Provides functionality for parsing commands and formatting responses.
    """

    COMMAND_PATTERN = re.compile(r"^(/\w+)\s*(.*)?$", re.DOTALL)
    PERIOD_KEYWORDS = {"daily", "weekly", "monthly"}

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
        lines = [f"{status_emoji} {number}. {task.title}"]

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
            sorted_tasks = sorted(tasks, key=lambda t: (t.category, t.created_at))
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
            "",
            f"📊 {period_label}: {pending} pending, {completed_in_period} completed",
        ]

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

📋 Listing Tasks:
/daily - Show today's tasks
/weekly - Show this week's tasks
/monthly - Show this month's tasks

✅ Completing Tasks:
/done <number> - Mark task as completed
/pending <number> <reason> - Mark as pending

🔍 Other:
/search <query> - Search tasks
/report <daily|weekly|monthly> - Generate report
/help - Show this help message

Examples:
• /add Work Review PR, Fix bug, Deploy
• /add weekly Personal Gym, Groceries
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
