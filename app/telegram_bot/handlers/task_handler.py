"""Handler for task management commands (/add, /done, /pending)."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import (
    TaskPeriodType,
    TaskResponse,
    TaskStatus,
    TaskStatusUpdate,
)
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram_bot.handlers.base import BaseHandler
from config.database import get_session_factory


class TaskHandler(BaseHandler):
    """Handler for task management commands."""

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["add", "done", "pending"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle task management commands.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        command = self.get_command_name(update)
        args = self.get_command_args(update)

        if command == "add":
            await self._handle_add(update, args)
        elif command == "done":
            await self._handle_done(update, args)
        elif command == "pending":
            await self._handle_pending(update, args)

    async def handle_add_natural(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle natural language add command.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text
        text_lower = text.lower()

        # Extract title from natural text
        title = None
        for prefix in ["add task:", "create task:", "add:", "create:", "new task:"]:
            if prefix in text_lower:
                title = text[text_lower.find(prefix) + len(prefix) :].strip()
                break

        if not title:
            for word in ["add", "create"]:
                if word in text_lower:
                    idx = text_lower.find(word) + len(word)
                    title = text[idx:].strip()
                    break

        if title:
            await self._handle_add(update, title)
        else:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "I couldn't understand the task. Try: /add [title]"
                ),
            )

    async def handle_complete_natural(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle natural language task completion.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        import re

        if not update.message or not update.message.text:
            return

        text = update.message.text

        # Extract task number from natural text
        # Patterns: "complete task 3", "done with 5", "finish #2", "mark 1 as done"
        patterns = [
            r"(?:complete|done|finish|mark)\s+(?:task\s+)?#?(\d+)",
            r"#(\d+)\s+(?:is\s+)?(?:done|complete|finished)",
            r"task\s+#?(\d+)\s+(?:is\s+)?(?:done|complete|finished)",
        ]

        task_number = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                task_number = int(match.group(1))
                break

        if task_number:
            await self._handle_done(update, str(task_number))
        else:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "I couldn't understand which task to complete.\n"
                    'Try: /done [number] or "complete task 3"'
                ),
            )

    async def _handle_add(self, update: Update, args: str) -> None:
        """Handle /add command with support for multiple tasks and categories.

        Supports formats:
        - /add Work task1, task2, task3
        - /add weekly Work task1, task2
        - /add monthly Personal task1
        - /add task1, task2 (defaults to daily, General)

        Args:
            update: Telegram update object.
            args: Command arguments.
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide task(s). Usage:\n"
                    "/add Work task1, task2, task3\n"
                    "/add weekly Personal task1, task2"
                ),
            )
            return

        # Parse the command arguments
        period_type, category, titles = self.telegram_support.parse_add_command(args)

        if not titles:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "No tasks found. Usage:\n"
                    "/add Work task1, task2, task3\n"
                    "/add weekly Personal task1, task2"
                ),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = TaskRepository(session)
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                task_support=task_support,
            )

            today = date.today()

            # Create multiple tasks
            tasks = await service.create_multiple_tasks(
                titles=titles,
                category=category,
                period_type=period_type,
                period_date=today,
            )

            # Get period stats
            stats = await service.get_period_stats_quick(period_type, today)

            # Convert tasks to response format
            task_responses = [TaskResponse.model_validate(task) for task in tasks]

            # Format and send response
            # Get period type string
            period_str = (
                period_type.value
                if isinstance(period_type, TaskPeriodType)
                else period_type
            )

            # Commit the transaction to persist tasks
            await session.commit()

            response = self.telegram_support.format_bulk_creation_response(
                tasks=task_responses,
                period_type=period_str,
                category=category,
                total_in_period=stats["total"],
                completed_in_period=stats["completed"],
            )

            await self.send_message(update, response)

    async def _handle_done(self, update: Update, args: str) -> None:
        """Handle /done command using period-based task number.

        Supports formats:
        - /done 1
        - /done 1 I am happy to finish this!

        Args:
            update: Telegram update object.
            args: Task number and optional completion note.
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide a task number. Usage: /done [number] [note]\n"
                    "Use /daily to see task numbers."
                ),
            )
            return

        # Parse task number and optional note
        parts = args.split(maxsplit=1)

        try:
            task_number = int(parts[0])
        except ValueError:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Invalid task number. Please provide a number."
                ),
            )
            return

        completion_note = parts[1] if len(parts) > 1 else None

        if task_number < 1:
            await self.send_message(
                update,
                self.telegram_support.format_error("Task number must be positive."),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = TaskRepository(session)
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                task_support=task_support,
            )

            today = date.today()
            period_type = TaskPeriodType.DAILY

            # Find task by period number
            task = await service.get_task_by_period_number(
                period_number=task_number,
                period_type=period_type,
                period_date=today,
            )

            if not task:
                await self.send_message(
                    update,
                    self.telegram_support.format_error(
                        f"Task #{task_number} not found today.\n"
                        "Use /daily to see available tasks."
                    ),
                )
                return

            try:
                # Mark as completed using actual task ID with optional note
                status_data = TaskStatusUpdate(
                    status=TaskStatus.COMPLETED,
                    completion_note=completion_note,
                )
                updated_task = await service.update_task_status(task.id, status_data)

                # Commit the transaction to persist changes
                await session.commit()

                # Get updated stats
                stats = await service.get_period_stats_quick(period_type, today)

                # Format response
                task_response = TaskResponse.model_validate(updated_task)
                response = self.telegram_support.format_task_done_response(
                    task=task_response,
                    total_in_period=stats["total"],
                    completed_in_period=stats["completed"],
                    period_type=period_type.value,
                )

                await self.send_message(update, response)

            except Exception as e:
                await self.send_message(
                    update,
                    self.telegram_support.format_error(f"Failed to update task: {e}"),
                )

    async def _handle_pending(self, update: Update, args: str) -> None:
        """Handle /pending command using period-based task number.

        Args:
            update: Telegram update object.
            args: Task number and optional reason.
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide task number and reason.\n"
                    "Usage: /pending [number] [reason]\n"
                    "Use /daily to see task numbers."
                ),
            )
            return

        parts = args.split(maxsplit=1)

        try:
            task_number = int(parts[0])
        except ValueError:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Invalid task number. Please provide a number."
                ),
            )
            return

        if task_number < 1:
            await self.send_message(
                update,
                self.telegram_support.format_error("Task number must be positive."),
            )
            return

        reason = parts[1] if len(parts) > 1 else None

        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = TaskRepository(session)
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                task_support=task_support,
            )

            today = date.today()
            period_type = TaskPeriodType.DAILY

            # Find task by period number
            task = await service.get_task_by_period_number(
                period_number=task_number,
                period_type=period_type,
                period_date=today,
            )

            if not task:
                await self.send_message(
                    update,
                    self.telegram_support.format_error(
                        f"Task #{task_number} not found today.\n"
                        "Use /daily to see available tasks."
                    ),
                )
                return

            try:
                # Mark as pending using actual task ID
                status_data = TaskStatusUpdate(
                    status=TaskStatus.PENDING,
                    pending_reason=reason,
                )
                updated_task = await service.update_task_status(task.id, status_data)

                # Commit the transaction to persist changes
                await session.commit()

                # Format response
                task_response = TaskResponse.model_validate(updated_task)
                response = self.telegram_support.format_task_pending_response(
                    task=task_response,
                    reason=reason,
                )

                await self.send_message(update, response)

            except Exception as e:
                await self.send_message(
                    update,
                    self.telegram_support.format_error(f"Failed to update task: {e}"),
                )
