"""Telegram support module for bot interactions."""

import re
from dataclasses import dataclass
from datetime import date, datetime
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

    def format_task(self, task: TaskResponse, include_details: bool = False) -> str:
        """Format a single task for Telegram display.

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
                lines.append(f"   ✔️ Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M')}")
            elif task.pending_reason:
                lines.append(f"   ⚠️ Reason: {task.pending_reason}")

        return "\n".join(lines)

    def format_task_list(
        self,
        tasks: list[TaskResponse],
        title: str = "Tasks",
        include_details: bool = False,
    ) -> str:
        """Format a list of tasks for Telegram display.

        Args:
            tasks: List of tasks to format.
            title: Title for the list.
            include_details: Whether to include full details.

        Returns:
            Formatted task list string.
        """
        if not tasks:
            return f"📋 {title}\n\nNo tasks found."

        lines = [f"📋 {title}", ""]
        for task in tasks:
            lines.append(self.format_task(task, include_details))
            lines.append("")

        return "\n".join(lines)

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

Commands:
/add <title> - Add a daily task
/daily - Show today's tasks
/weekly - Show this week's tasks
/monthly - Show this month's tasks
/done <id> - Mark task as completed
/pending <id> <reason> - Mark task as pending
/search <query> - Search tasks
/report <daily|weekly|monthly> - Generate report
/help - Show this help message

You can also type naturally and I'll try to understand!

Examples:
• "Add task: Review PR"
• "What did I complete today?"
• "Show my weekly progress"
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
