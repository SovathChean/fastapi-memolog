"""Telegram service for handling bot interactions."""

from datetime import date

from fastapi import Depends

from app.models.schemas.task import (
    TaskCreate,
    TaskPeriodType,
    TaskReportRequest,
    TaskSearchRequest,
    TaskStatus,
    TaskStatusUpdate,
)
from app.services.base import BaseService
from app.services.task_service import TaskService
from app.support.task_support import TaskSupport
from app.support.telegram_support import (
    ParsedCommand,
    TelegramCommand,
    TelegramSupport,
)


class TelegramService(BaseService):
    """Service for Telegram bot interactions."""

    def __init__(
        self,
        task_service: TaskService = Depends(),
        task_support: TaskSupport = Depends(),
        telegram_support: TelegramSupport = Depends(),
    ):
        """Initialize service with dependencies.

        Args:
            task_service: Task service for task operations.
            task_support: Support module for task logic.
            telegram_support: Support module for Telegram formatting.
        """
        super().__init__()
        self.task_service = task_service
        self.task_support = task_support
        self.telegram_support = telegram_support

    async def handle_message(self, text: str, chat_id: int) -> str:
        """Handle incoming Telegram message.

        Args:
            text: Message text.
            chat_id: Telegram chat ID.

        Returns:
            Response message to send back.
        """
        parsed = self.telegram_support.parse_message(text)

        try:
            if parsed.command:
                return await self._handle_command(parsed)
            elif parsed.is_natural_text:
                return await self._handle_natural_text(parsed.args)
            else:
                return self.telegram_support.format_error("I didn't understand that.")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return self.telegram_support.format_error(f"Something went wrong: {e}")

    async def _handle_command(self, parsed: ParsedCommand) -> str:
        """Handle a parsed command.

        Args:
            parsed: Parsed command with arguments.

        Returns:
            Response message.
        """
        command = parsed.command
        args = parsed.args

        if command == TelegramCommand.START:
            return self.telegram_support.format_help()

        elif command == TelegramCommand.HELP:
            return self.telegram_support.format_help()

        elif command == TelegramCommand.ADD:
            return await self._handle_add(args)

        elif command in (TelegramCommand.DAILY, TelegramCommand.WEEKLY, TelegramCommand.MONTHLY):
            return await self._handle_period_list(command)

        elif command == TelegramCommand.DONE:
            return await self._handle_done(args)

        elif command == TelegramCommand.PENDING:
            return await self._handle_pending(args)

        elif command == TelegramCommand.SEARCH:
            return await self._handle_search(args)

        elif command == TelegramCommand.REPORT:
            return await self._handle_report(args)

        return self.telegram_support.format_error("Unknown command. Use /help for available commands.")

    async def _handle_add(self, args: str) -> str:
        """Handle /add command.

        Args:
            args: Task title.

        Returns:
            Response message.
        """
        if not args:
            return self.telegram_support.format_error("Please provide a task title. Usage: /add [title]")

        today = date.today()
        task_data = TaskCreate(
            title=args,
            period_type=TaskPeriodType.DAILY,
            period_date=today,
        )

        task = await self.task_service.create_task(task_data)
        return self.telegram_support.format_success(
            f"Task created: #{task.id} {task.title}"
        )

    async def _handle_period_list(self, command: TelegramCommand) -> str:
        """Handle /daily, /weekly, /monthly commands.

        Args:
            command: Period command.

        Returns:
            Response message with task list.
        """
        period_type = self.telegram_support.get_period_type_from_command(command)
        if not period_type:
            return self.telegram_support.format_error("Invalid period type.")

        today = date.today()
        tasks = await self.task_service.get_tasks_by_period(period_type, today)

        period_label = self.task_support.get_period_label(period_type, today)
        title = f"{period_type.value.title()} Tasks - {period_label}"

        from app.models.schemas.task import TaskResponse
        task_responses = [TaskResponse.model_validate(task) for task in tasks]

        return self.telegram_support.format_task_list(
            task_responses,
            title=title,
            include_details=True,
        )

    async def _handle_done(self, args: str) -> str:
        """Handle /done command.

        Args:
            args: Task ID.

        Returns:
            Response message.
        """
        if not args:
            return self.telegram_support.format_error("Please provide a task ID. Usage: /done [id]")

        try:
            task_id = int(args.strip())
        except ValueError:
            return self.telegram_support.format_error("Invalid task ID. Please provide a number.")

        status_data = TaskStatusUpdate(status=TaskStatus.COMPLETED)
        task = await self.task_service.update_task_status(task_id, status_data)

        return self.telegram_support.format_success(
            f"Task #{task.id} marked as completed! 🎉"
        )

    async def _handle_pending(self, args: str) -> str:
        """Handle /pending command.

        Args:
            args: Task ID and reason.

        Returns:
            Response message.
        """
        if not args:
            return self.telegram_support.format_error(
                "Please provide task ID and reason. Usage: /pending [id] [reason]"
            )

        parts = args.split(maxsplit=1)
        if len(parts) < 1:
            return self.telegram_support.format_error("Please provide a task ID.")

        try:
            task_id = int(parts[0])
        except ValueError:
            return self.telegram_support.format_error("Invalid task ID. Please provide a number.")

        reason = parts[1] if len(parts) > 1 else None

        status_data = TaskStatusUpdate(
            status=TaskStatus.PENDING,
            pending_reason=reason,
        )
        task = await self.task_service.update_task_status(task_id, status_data)

        return self.telegram_support.format_success(
            f"Task #{task.id} marked as pending."
        )

    async def _handle_search(self, args: str) -> str:
        """Handle /search command.

        Args:
            args: Search query.

        Returns:
            Response message with search results.
        """
        if not args:
            return self.telegram_support.format_error(
                "Please provide a search query. Usage: /search [query]"
            )

        search_request = TaskSearchRequest(query=args, limit=10)
        results = await self.task_service.search_tasks(search_request)

        return self.telegram_support.format_search_results(results)

    async def _handle_report(self, args: str) -> str:
        """Handle /report command.

        Args:
            args: Period type (daily, weekly, monthly).

        Returns:
            Response message with report.
        """
        if not args:
            args = "daily"

        args = args.lower().strip()
        try:
            period_type = TaskPeriodType(args)
        except ValueError:
            return self.telegram_support.format_error(
                "Invalid period type. Use: daily, weekly, or monthly"
            )

        today = date.today()
        start_date, end_date = self.task_support.calculate_period_bounds(
            period_type,
            today,
        )

        report_request = TaskReportRequest(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        report = await self.task_service.generate_report(report_request)

        return self.telegram_support.format_report(
            period_type=report.period_type,
            start_date=report.period_start,
            end_date=report.period_end,
            total=report.summary.total_tasks,
            completed=report.summary.completed,
            pending=report.summary.pending,
            completion_rate=report.summary.completion_rate,
            completed_tasks=report.completed_tasks,
            pending_tasks=report.pending_tasks,
        )

    async def _handle_natural_text(self, text: str) -> str:
        """Handle natural language input.

        Uses simple keyword matching for now.
        Can be enhanced with AI interpretation later.

        Args:
            text: Natural language text.

        Returns:
            Response message.
        """
        text_lower = text.lower()

        # Check for add/create intent
        if any(word in text_lower for word in ["add", "create", "new task"]):
            # Extract title from text
            for prefix in ["add task:", "create task:", "add:", "create:", "new task:"]:
                if prefix in text_lower:
                    title = text[text_lower.find(prefix) + len(prefix):].strip()
                    if title:
                        return await self._handle_add(title)

            # Try to use the text after common words
            for word in ["add", "create"]:
                if word in text_lower:
                    idx = text_lower.find(word) + len(word)
                    title = text[idx:].strip()
                    if title:
                        return await self._handle_add(title)

        # Check for list intent
        if any(word in text_lower for word in ["today", "daily", "today's"]):
            return await self._handle_period_list(TelegramCommand.DAILY)

        if any(word in text_lower for word in ["week", "weekly", "this week"]):
            return await self._handle_period_list(TelegramCommand.WEEKLY)

        if any(word in text_lower for word in ["month", "monthly", "this month"]):
            return await self._handle_period_list(TelegramCommand.MONTHLY)

        # Check for search intent
        if any(word in text_lower for word in ["search", "find", "look for", "what"]):
            return await self._handle_search(text)

        # Check for report intent
        if any(word in text_lower for word in ["report", "summary", "progress", "status"]):
            if "week" in text_lower:
                return await self._handle_report("weekly")
            elif "month" in text_lower:
                return await self._handle_report("monthly")
            return await self._handle_report("daily")

        # Default: treat as search query
        return await self._handle_search(text)
