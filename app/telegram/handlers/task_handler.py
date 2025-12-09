"""Handler for task management commands (/add, /done, /pending)."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import (
    TaskCreate,
    TaskPeriodType,
    TaskStatus,
    TaskStatusUpdate,
)
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.embedding_support import EmbeddingSupport
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram.handlers.base import BaseHandler
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
                title = text[text_lower.find(prefix) + len(prefix):].strip()
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
                    "I couldn't understand the task. Try: /add <title>"
                ),
            )

    async def _handle_add(self, update: Update, args: str) -> None:
        """Handle /add command.

        Args:
            update: Telegram update object.
            args: Task title.
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide a task title. Usage: /add <title>"
                ),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = TaskRepository(session)
            embedding_support = EmbeddingSupport()
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                embedding_support=embedding_support,
                task_support=task_support,
            )

            today = date.today()
            task_data = TaskCreate(
                title=args,
                period_type=TaskPeriodType.DAILY,
                period_date=today,
            )

            task = await service.create_task(task_data)

            await self.send_message(
                update,
                self.telegram_support.format_success(
                    f"Task created: #{task.id} {task.title}"
                ),
            )

    async def _handle_done(self, update: Update, args: str) -> None:
        """Handle /done command.

        Args:
            update: Telegram update object.
            args: Task ID.
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide a task ID. Usage: /done <id>"
                ),
            )
            return

        try:
            task_id = int(args.strip())
        except ValueError:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Invalid task ID. Please provide a number."
                ),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = TaskRepository(session)
            embedding_support = EmbeddingSupport()
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                embedding_support=embedding_support,
                task_support=task_support,
            )

            try:
                status_data = TaskStatusUpdate(status=TaskStatus.COMPLETED)
                task = await service.update_task_status(task_id, status_data)

                await self.send_message(
                    update,
                    self.telegram_support.format_success(
                        f"Task #{task.id} marked as completed! 🎉"
                    ),
                )
            except Exception as e:
                await self.send_message(
                    update,
                    self.telegram_support.format_error(f"Task not found: {e}"),
                )

    async def _handle_pending(self, update: Update, args: str) -> None:
        """Handle /pending command.

        Args:
            update: Telegram update object.
            args: Task ID and reason.
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide task ID and reason. Usage: /pending <id> <reason>"
                ),
            )
            return

        parts = args.split(maxsplit=1)

        try:
            task_id = int(parts[0])
        except ValueError:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Invalid task ID. Please provide a number."
                ),
            )
            return

        reason = parts[1] if len(parts) > 1 else None

        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = TaskRepository(session)
            embedding_support = EmbeddingSupport()
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                embedding_support=embedding_support,
                task_support=task_support,
            )

            try:
                status_data = TaskStatusUpdate(
                    status=TaskStatus.PENDING,
                    pending_reason=reason,
                )
                task = await service.update_task_status(task_id, status_data)

                await self.send_message(
                    update,
                    self.telegram_support.format_success(
                        f"Task #{task.id} marked as pending."
                    ),
                )
            except Exception as e:
                await self.send_message(
                    update,
                    self.telegram_support.format_error(f"Task not found: {e}"),
                )
