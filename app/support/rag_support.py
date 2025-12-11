"""RAG support module for AI-enhanced task responses."""

import logging
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.models.domain.task import Task
from app.models.schemas.task import TaskResponse, TaskSearchResult
from app.support.langchain_support import LangChainSupport, get_langchain_support
from config.settings import get_settings

logger = logging.getLogger(__name__)


# Prompt Templates
SEARCH_SUMMARY_SYSTEM_PROMPT = """You are a helpful task management assistant. \
Based on the user's search query and the retrieved tasks, provide a concise \
summary and any relevant insights.

Guidelines:
- Keep responses brief (2-4 sentences max) for Telegram display
- Highlight pending tasks that need attention
- Note any patterns (e.g., multiple tasks in same category)
- If tasks are overdue or pending long, mention it
- Be helpful and actionable"""

SEARCH_SUMMARY_USER_TEMPLATE = """User searched for: "{query}"

Retrieved Tasks:
{task_context}

Provide a brief, helpful summary of these search results."""

QUESTION_ANSWER_SYSTEM_PROMPT = """You are a helpful task management assistant \
with access to the user's tasks. Answer questions about their tasks in a \
friendly, conversational manner.

Guidelines:
- Be concise but informative
- Reference specific tasks when relevant
- Provide actionable suggestions
- If you cannot answer based on available tasks, say so clearly
- Keep responses suitable for Telegram (not too long)"""

QUESTION_ANSWER_USER_TEMPLATE = """Context - User's Tasks:
{task_context}

Conversation History:
{history}

User Question: {question}

Provide a helpful response based on the user's tasks."""


class RAGSupport:
    """RAG chain implementation for task-aware AI responses.

    Provides AI-generated summaries and insights for task search results
    and conversational question-answering about tasks.
    """

    def __init__(
        self,
        langchain_support: LangChainSupport | None = None,
    ) -> None:
        """Initialize RAG support.

        Args:
            langchain_support: Optional LangChainSupport instance.
        """
        self.langchain_support = langchain_support or get_langchain_support()
        self.settings = get_settings()

        # Create prompt templates
        self.search_summary_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=SEARCH_SUMMARY_SYSTEM_PROMPT),
                ("human", SEARCH_SUMMARY_USER_TEMPLATE),
            ]
        )

        self.qa_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=QUESTION_ANSWER_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", QUESTION_ANSWER_USER_TEMPLATE),
            ]
        )

    async def generate_search_summary(
        self,
        query: str,
        results: list[TaskSearchResult],
    ) -> str:
        """Generate AI summary of search results.

        Args:
            query: User's search query.
            results: List of search results with similarity scores.

        Returns:
            AI-generated summary string.
        """
        if not results:
            return "No tasks found matching your search."

        try:
            # Format task context
            task_context = self._format_tasks_for_context(
                [r.task for r in results],
                include_scores=True,
                scores=[r.similarity_score for r in results],
            )

            # Generate summary using LangChain
            messages = self.search_summary_prompt.format_messages(
                query=query,
                task_context=task_context,
            )

            response = await self.langchain_support.chat_model.ainvoke(messages)
            return response.content

        except Exception as e:
            logger.error(f"Failed to generate search summary: {e}")
            return ""  # Graceful degradation - return empty, show results only

    async def answer_question(
        self,
        question: str,
        tasks: list[Task] | list[TaskResponse],
        history: list[dict] | None = None,
    ) -> str:
        """Answer user question with task context.

        Args:
            question: User's question.
            tasks: List of relevant tasks for context.
            history: Optional conversation history.

        Returns:
            AI-generated answer string.
        """
        try:
            # Format task context
            task_responses = [
                t if isinstance(t, TaskResponse) else TaskResponse.model_validate(t)
                for t in tasks
            ]
            task_context = self._format_tasks_for_context(task_responses)

            # Format history
            if history:
                history_str = self._format_history(history)
            else:
                history_str = "No previous context."

            # Generate answer using LangChain
            messages = self.qa_prompt.format_messages(
                task_context=task_context,
                history=history_str,
                question=question,
            )

            response = await self.langchain_support.chat_model.ainvoke(messages)
            return response.content

        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return "I'm sorry, I couldn't process your question. Please try again."

    async def generate_task_insights(
        self,
        tasks: list[Task] | list[TaskResponse],
        context: str = "general overview",
    ) -> str:
        """Generate insights about a collection of tasks.

        Args:
            tasks: List of tasks to analyze.
            context: Context for the analysis (e.g., "daily tasks", "this week").

        Returns:
            AI-generated insights string.
        """
        if not tasks:
            return "No tasks to analyze."

        try:
            task_responses = [
                t if isinstance(t, TaskResponse) else TaskResponse.model_validate(t)
                for t in tasks
            ]
            task_context = self._format_tasks_for_context(task_responses)

            messages = [
                SystemMessage(
                    content=(
                        "You are a task management assistant. Provide brief, "
                        "actionable insights about the user's tasks. Focus on "
                        "completion rates, priorities, and helpful suggestions. "
                        "Keep it concise for Telegram."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Context: {context}\n\n"
                        f"Tasks:\n{task_context}\n\n"
                        "Provide 2-3 brief insights or suggestions."
                    )
                ),
            ]

            response = await self.langchain_support.chat_model.ainvoke(messages)
            return response.content

        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return ""

    def _format_tasks_for_context(
        self,
        tasks: list[TaskResponse],
        include_scores: bool = False,
        scores: list[float] | None = None,
    ) -> str:
        """Format tasks into text context for LLM.

        Args:
            tasks: List of tasks to format.
            include_scores: Whether to include similarity scores.
            scores: Optional list of similarity scores.

        Returns:
            Formatted task context string.
        """
        if not tasks:
            return "No tasks available."

        lines = []
        for i, task in enumerate(tasks[: self.settings.search_result_context_limit]):
            status_emoji = "✅" if task.status == "completed" else "⏳"
            line = f"{i + 1}. {status_emoji} {task.title}"

            # Add category
            line += f" [{task.category}]"

            # Add period info
            line += f" ({task.period_type}, {task.period_date})"

            # Add similarity score if available
            if include_scores and scores and i < len(scores):
                line += f" - {scores[i]:.0%} match"

            # Add pending reason if exists
            if task.status == "pending" and task.pending_reason:
                line += f"\n   Reason: {task.pending_reason}"

            lines.append(line)

        return "\n".join(lines)

    def _format_history(self, history: list[dict]) -> str:
        """Format conversation history for context.

        Args:
            history: List of message dictionaries with 'role' and 'content'.

        Returns:
            Formatted history string.
        """
        if not history:
            return "No previous context."

        lines = []
        for msg in history[-6:]:  # Last 3 exchanges max
            role = "User" if msg.get("role") == "human" else "Assistant"
            content = msg.get("content", "")[:200]  # Truncate long messages
            lines.append(f"{role}: {content}")

        return "\n".join(lines)


@lru_cache
def get_rag_support() -> RAGSupport:
    """Get cached RAG support instance."""
    return RAGSupport()
