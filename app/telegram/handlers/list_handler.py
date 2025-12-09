"""Handler for period list commands (/daily, /weekly, /monthly)."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import TaskPeriodType, TaskResponse
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.embedding_support import EmbeddingSupport
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram.handlers.base import BaseHandler
from config.database import get_session_factory


class ListHandler(BaseHandler):
    """Handler for period list commands."""

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()
        self.task_support = TaskSupport()

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["daily", "weekly", "monthly"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle period list commands.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        command = self.get_command_name(update)
        await self.handle_period(update, context, command)

    async def handle_period(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        period: str,
    ) -> None:
        """Handle period-based task listing.

        Args:
            update: Telegram update object.
            context: Callback context.
            period: Period type (daily, weekly, monthly).
        """
        try:
            period_type = TaskPeriodType(period)
        except ValueError:
            await self.send_message(
                update,
                self.telegram_support.format_error("Invalid period type."),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = TaskRepository(session)
            embedding_support = EmbeddingSupport()
            service = TaskService(
                repository=repository,
                embedding_support=embedding_support,
                task_support=self.task_support,
            )

            today = date.today()
            tasks = await service.get_tasks_by_period(period_type, today)

            period_label = self.task_support.get_period_label(period_type, today)
            title = f"{period_type.value.title()} Tasks - {period_label}"

            task_responses = [TaskResponse.model_validate(task) for task in tasks]

            response = self.telegram_support.format_task_list(
                task_responses,
                title=title,
                include_details=True,
            )

            await self.send_message(update, response)
