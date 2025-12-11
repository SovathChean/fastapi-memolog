"""Memory support module for conversation history management."""

import logging
from collections import OrderedDict

from app.repositories.conversation_repository import ConversationRepository
from config.settings import get_settings

logger = logging.getLogger(__name__)


class LRUCache(OrderedDict):
    """Simple LRU cache implementation using OrderedDict."""

    def __init__(self, maxsize: int = 100):
        """Initialize LRU cache with max size."""
        super().__init__()
        self.maxsize = maxsize

    def get(self, key, default=None):
        """Get item and move to end (most recently used)."""
        if key in self:
            self.move_to_end(key)
            return self[key]
        return default

    def put(self, key, value):
        """Put item and evict oldest if necessary."""
        if key in self:
            self.move_to_end(key)
        self[key] = value
        if len(self) > self.maxsize:
            self.popitem(last=False)


class MemorySupport:
    """Conversation memory management for Telegram users.

    Provides per-user conversation history with in-memory caching
    and database persistence for context retention across sessions.
    """

    def __init__(
        self,
        repository: ConversationRepository,
    ) -> None:
        """Initialize memory support.

        Args:
            repository: Conversation repository for persistence.
        """
        self.repository = repository
        self.settings = get_settings()
        self._cache: LRUCache = LRUCache(maxsize=100)

    async def get_history(
        self,
        telegram_user_id: int,
        limit: int | None = None,
    ) -> list[dict]:
        """Get conversation history for a user.

        Args:
            telegram_user_id: Telegram user ID.
            limit: Optional limit override.

        Returns:
            List of message dicts with 'role' and 'content'.
        """
        # Check cache first
        cache_key = f"history:{telegram_user_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            history = cached
        else:
            # Load from database
            messages = await self.repository.get_user_history(
                telegram_user_id=telegram_user_id,
                limit=self.settings.conversation_window_size,
            )
            history = [{"role": msg.role, "content": msg.content} for msg in messages]
            # Cache the result
            self._cache.put(cache_key, history)

        # Apply limit if specified
        effective_limit = limit or self.settings.conversation_window_size
        return history[-effective_limit:]

    async def add_message(
        self,
        telegram_user_id: int,
        human_message: str,
        ai_message: str,
        extra_data: dict | None = None,
    ) -> None:
        """Add a message exchange to history.

        Args:
            telegram_user_id: Telegram user ID.
            human_message: User's message.
            ai_message: AI's response.
            extra_data: Optional extra data.
        """
        # Persist to database
        await self.repository.add_exchange(
            telegram_user_id=telegram_user_id,
            human_message=human_message,
            ai_message=ai_message,
            extra_data=extra_data,
        )

        # Update cache
        cache_key = f"history:{telegram_user_id}"
        history = self._cache.get(cache_key, [])
        history.append({"role": "human", "content": human_message})
        history.append({"role": "ai", "content": ai_message})

        # Trim to window size
        max_messages = self.settings.conversation_window_size
        if len(history) > max_messages:
            history = history[-max_messages:]

        self._cache.put(cache_key, history)

        # Periodically trim old messages in DB
        message_count = await self.repository.get_message_count(telegram_user_id)
        if message_count > max_messages * 2:
            await self.repository.trim_old_messages(
                telegram_user_id=telegram_user_id,
                keep_count=max_messages,
            )
            logger.debug(f"Trimmed old messages for user {telegram_user_id}")

    async def clear_history(
        self,
        telegram_user_id: int,
    ) -> None:
        """Clear conversation history for a user.

        Args:
            telegram_user_id: Telegram user ID.
        """
        # Clear from database
        await self.repository.clear_user_history(telegram_user_id)

        # Clear from cache
        cache_key = f"history:{telegram_user_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]

        logger.info(f"Cleared conversation history for user {telegram_user_id}")

    def invalidate_cache(
        self,
        telegram_user_id: int,
    ) -> None:
        """Invalidate cache for a user.

        Args:
            telegram_user_id: Telegram user ID.
        """
        cache_key = f"history:{telegram_user_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]

    def format_history_for_prompt(
        self,
        history: list[dict],
        max_chars: int = 2000,
    ) -> str:
        """Format conversation history for LLM prompt.

        Args:
            history: List of message dicts.
            max_chars: Maximum total characters.

        Returns:
            Formatted history string.
        """
        if not history:
            return "No previous conversation."

        lines = []
        total_chars = 0

        # Process in reverse to prioritize recent messages
        for msg in reversed(history):
            role = "User" if msg["role"] == "human" else "Assistant"
            content = msg["content"]

            # Truncate long messages
            if len(content) > 300:
                content = content[:300] + "..."

            line = f"{role}: {content}"

            if total_chars + len(line) > max_chars:
                break

            lines.insert(0, line)
            total_chars += len(line) + 1

        return "\n".join(lines) if lines else "No previous conversation."

    async def get_formatted_history(
        self,
        telegram_user_id: int,
        max_chars: int = 2000,
    ) -> str:
        """Get formatted conversation history for a user.

        Args:
            telegram_user_id: Telegram user ID.
            max_chars: Maximum total characters.

        Returns:
            Formatted history string.
        """
        history = await self.get_history(telegram_user_id)
        return self.format_history_for_prompt(history, max_chars)
