"""Handler for /report command."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import TaskPeriodType, TaskReportRequest
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram_bot.handlers.base import BaseHandler
from config.database import get_session_factory


class ReportHandler(BaseHandler):
    """Handler for report command."""

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()
        self.task_support = TaskSupport()

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["report"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /report command.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        args = self.get_command_args(update)
        period = args.lower().strip() if args else "daily"
        await self.handle_report(update, context, period)

    async def handle_report(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        period: str,
    ) -> None:
        """Handle report generation for given period.

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
                self.telegram_support.format_error(
                    "Invalid period type. Use: daily, weekly, or monthly"
                ),
            )
            return

        # Show typing indicator while generating report
        await self.send_typing(update)

        session_factory = get_session_factory()
        async with session_factory() as session:
            # Get or create user
            user = await self.get_or_create_user(update, session)

            repository = TaskRepository(session)
            service = TaskService(
                repository=repository,
                task_support=self.task_support,
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
            report = await service.generate_report(user.id, report_request)

            response = self.telegram_support.format_report(
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

            await self.send_message(update, response)
