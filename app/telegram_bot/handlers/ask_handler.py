"""Handler for /ask conversational AI command."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import TaskSearchRequest
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.langchain_support import get_langchain_support
from app.support.memory_support import MemorySupport
from app.support.rag_support import get_rag_support
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram_bot.handlers.base import BaseHandler
from config.database import get_session_factory


class AskHandler(BaseHandler):
    """Handler for /ask conversational AI command.

    Provides conversational AI interface for asking questions about tasks,
    with conversation memory for context retention.
    """

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()
        self.rag_support = get_rag_support()
        self.langchain_support = get_langchain_support()

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["ask"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /ask command.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        question = self.get_command_args(update)
        await self.handle_question(update, context, question)

    async def handle_question(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        question: str,
    ) -> None:
        """Handle a question about tasks.

        Args:
            update: Telegram update object.
            context: Callback context.
            question: User's question.
        """
        if not question:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide a question. Usage: /ask <question>\n"
                    "Example: /ask what tasks do I have pending?"
                ),
            )
            return

        user_id = update.effective_user.id if update.effective_user else 0

        # Show typing indicator while processing AI query
        await self.send_typing(update)

        session_factory = get_session_factory()
        async with session_factory() as session:
            # Initialize repositories and support
            task_repository = TaskRepository(session)
            conversation_repository = ConversationRepository(session)
            task_support = TaskSupport()

            task_service = TaskService(
                repository=task_repository,
                task_support=task_support,
            )

            memory_support = MemorySupport(
                repository=conversation_repository,
            )

            try:
                # Get conversation history
                history = await memory_support.get_history(user_id)

                # Retrieve relevant tasks for context
                relevant_tasks = await self._retrieve_relevant_tasks(
                    question=question,
                    task_service=task_service,
                )

                # Generate AI response
                response = await self.rag_support.answer_question(
                    question=question,
                    tasks=relevant_tasks,
                    history=history,
                )

                # Store conversation
                await memory_support.add_message(
                    telegram_user_id=user_id,
                    human_message=question,
                    ai_message=response,
                    extra_data={"type": "ask", "task_count": len(relevant_tasks)},
                )

                # Commit the transaction to persist conversation
                await session.commit()

                # Format and send response
                formatted_response = self.telegram_support.format_ai_response(
                    response=response,
                    related_tasks=relevant_tasks[:3] if relevant_tasks else None,
                )
                await self.send_message(update, formatted_response)

            except Exception as e:
                self.logger.error(f"Failed to process question: {e}")
                await self.send_message(
                    update,
                    self.telegram_support.format_error(
                        "Sorry, I couldn't process your question. Please try again."
                    ),
                )

    async def _retrieve_relevant_tasks(
        self,
        question: str,
        task_service: TaskService,
    ) -> list:
        """Retrieve tasks relevant to the question.

        Args:
            question: User's question.
            task_service: Task service instance.

        Returns:
            List of relevant TaskResponse objects.
        """
        try:
            # Use semantic search to find relevant tasks
            search_request = TaskSearchRequest(
                query=question,
                limit=10,
            )
            results = await task_service.search_tasks(search_request)
            return [r.task for r in results]

        except Exception as e:
            self.logger.warning(f"Failed to retrieve tasks for question: {e}")
            # Fallback: get recent tasks
            try:
                from app.models.schemas.task import TaskPeriodType

                tasks = await task_service.get_tasks_by_period(
                    period_type=TaskPeriodType.DAILY,
                    period_date=date.today(),
                )
                from app.models.schemas.task import TaskResponse

                return [TaskResponse.model_validate(t) for t in tasks[:10]]
            except Exception:
                return []

    async def handle_clear_history(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle request to clear conversation history.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        user_id = update.effective_user.id if update.effective_user else 0

        session_factory = get_session_factory()
        async with session_factory() as session:
            conversation_repository = ConversationRepository(session)
            memory_support = MemorySupport(repository=conversation_repository)

            await memory_support.clear_history(user_id)

            # Commit the transaction to persist deletion
            await session.commit()

            await self.send_message(
                update,
                self.telegram_support.format_success(
                    "Conversation history cleared. Starting fresh!"
                ),
            )
