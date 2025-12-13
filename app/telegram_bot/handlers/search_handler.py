"""Handler for /search command with RAG-enhanced results."""

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import TaskSearchRequest
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.rag_support import get_rag_support
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram_bot.handlers.base import BaseHandler
from config.database import get_session_factory


class SearchHandler(BaseHandler):
    """Handler for search command with RAG-enhanced results.

    Provides semantic search with AI-generated summaries and insights.
    """

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()
        self.rag_support = get_rag_support()

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
                    "Please provide a search query. Usage: /search [query]"
                ),
            )
            return

        # Show typing indicator while searching
        await self.send_typing(update)

        session_factory = get_session_factory()
        async with session_factory() as session:
            # Get or create user
            user = await self.get_or_create_user(update, session)

            repository = TaskRepository(session)
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                task_support=task_support,
            )

            try:
                # Perform semantic search for this user
                search_request = TaskSearchRequest(query=query, limit=10)
                results = await service.search_tasks(user.id, search_request)

                # Generate AI summary using RAG
                ai_summary = ""
                if results:
                    try:
                        ai_summary = await self.rag_support.generate_search_summary(
                            query=query,
                            results=results,
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to generate AI summary: {e}")
                        # Continue without AI summary

                # Format enhanced response
                response = self.telegram_support.format_enhanced_search_results(
                    results=results,
                    ai_summary=ai_summary,
                )
                await self.send_message(update, response)

            except Exception as e:
                self.logger.error(f"Search failed: {e}")
                await self.send_message(
                    update,
                    self.telegram_support.format_error(
                        "Search failed. Please try again."
                    ),
                )
