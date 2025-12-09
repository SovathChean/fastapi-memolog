"""Handler for /search command."""

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import TaskSearchRequest
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.embedding_support import EmbeddingSupport
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram.handlers.base import BaseHandler
from config.database import get_session_factory


class SearchHandler(BaseHandler):
    """Handler for search command."""

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["search"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /search command.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        query = self.get_command_args(update)
        await self.handle_search(update, context, query)

    async def handle_search(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query: str,
    ) -> None:
        """Handle search with given query.

        Args:
            update: Telegram update object.
            context: Callback context.
            query: Search query string.
        """
        if not query:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide a search query. Usage: /search <query>"
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

            search_request = TaskSearchRequest(query=query, limit=10)
            results = await service.search_tasks(search_request)

            response = self.telegram_support.format_search_results(results)
            await self.send_message(update, response)
