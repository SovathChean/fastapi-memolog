"""Intent support module for natural language detection."""

import re
from enum import Enum


class MessageIntent(str, Enum):
    """Detected message intent types."""

    SEARCH = "search"  # Looking for specific tasks
    QUESTION = "question"  # Asking about tasks
    ADD_TASK = "add_task"  # Creating new task
    COMPLETE_TASK = "complete"  # Marking task done
    LIST_TASKS = "list"  # Viewing task list
    REPORT = "report"  # Getting report
    HELP = "help"  # Asking for help
    GREETING = "greeting"  # Saying hello
    CLEAR_HISTORY = "clear"  # Clear conversation
    UNKNOWN = "unknown"  # Fallback


class IntentSupport:
    """Natural language intent detection for Telegram messages.

    Detects user intent from free-form text to enable intelligent
    routing without explicit commands.
    """

    # Question patterns - ends with ? or starts with question words
    QUESTION_PATTERNS = [
        r"\?$",  # Ends with question mark
        r"^(what|how|when|why|which|who|where|can|could|would|should)\b",
        r"^(is|are|do|does|did|have|has|will|was|were)\b",
        r"^(tell me|show me|explain|help me understand)",
        r"^(i want to know|i need to know|i\'d like to know)",
    ]

    # Search patterns
    SEARCH_PATTERNS = [
        r"^(search|find|look for|looking for)\b",
        r"tasks? (about|related|with|containing|for)\b",
        r"^(show|get|fetch) .*(task|todo)",
        r"anything (about|related|with)",
    ]

    # Add task patterns - supports "add weekly task", "add task", etc.
    ADD_PATTERNS = [
        r"^(add|create|new|make)\s+(?:daily|weekly|monthly\s+)?(a\s+)?task",
        r"^(add|create|new|make)\s+(?:daily|weekly|monthly)\b",
        r"^(add|create|new)\s*:",
        r"^(remind me to|i need to|i have to|i should)\b",
        r"^(todo|to-do|to do)\s*:",
    ]

    # Complete task patterns
    COMPLETE_PATTERNS = [
        r"^(done|complete|finish|completed|finished)\b",
        r"^(mark|set).*(done|complete|finished)",
        r"^i (did|finished|completed)\b",
    ]

    # List patterns
    LIST_PATTERNS = [
        r"^(list|show|display|view)\s+(my\s+)?(tasks?|todos?)",
        r"^(what|show).*(tasks?|todos?).*(today|this week|this month)",
        r"^my (tasks?|todos?)",
        r"^(today|daily|weekly|monthly)\s*(tasks?|todos?)?$",
    ]

    # Report patterns
    REPORT_PATTERNS = [
        r"^(report|summary|overview|stats|statistics)",
        r"(progress|completion|status)\s+(report|summary)",
        r"how (am i|did i) doing",
    ]

    # Help patterns
    HELP_PATTERNS = [
        r"^(help|commands|how to use|what can you do)",
        r"^(i don\'t know|i\'m confused|how does this work)",
    ]

    # Greeting patterns
    GREETING_PATTERNS = [
        r"^(hi|hello|hey|good morning|good afternoon|good evening)\b",
        r"^(howdy|sup|what\'s up)",
    ]

    # Clear history patterns
    CLEAR_PATTERNS = [
        r"^(clear|reset|forget)\s+(history|conversation|chat|memory)",
        r"^(start over|new conversation|fresh start)",
    ]

    def __init__(self) -> None:
        """Initialize intent support with compiled patterns."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self._question_re = [
            re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS
        ]
        self._search_re = [re.compile(p, re.IGNORECASE) for p in self.SEARCH_PATTERNS]
        self._add_re = [re.compile(p, re.IGNORECASE) for p in self.ADD_PATTERNS]
        self._complete_re = [
            re.compile(p, re.IGNORECASE) for p in self.COMPLETE_PATTERNS
        ]
        self._list_re = [re.compile(p, re.IGNORECASE) for p in self.LIST_PATTERNS]
        self._report_re = [re.compile(p, re.IGNORECASE) for p in self.REPORT_PATTERNS]
        self._help_re = [re.compile(p, re.IGNORECASE) for p in self.HELP_PATTERNS]
        self._greeting_re = [
            re.compile(p, re.IGNORECASE) for p in self.GREETING_PATTERNS
        ]
        self._clear_re = [re.compile(p, re.IGNORECASE) for p in self.CLEAR_PATTERNS]

    def detect_intent(self, text: str) -> MessageIntent:
        """Detect intent from natural language text.

        Args:
            text: User's message text.

        Returns:
            Detected MessageIntent.
        """
        if not text or not text.strip():
            return MessageIntent.UNKNOWN

        text = text.strip()

        # Skip if it looks like a command (starts with /)
        if text.startswith("/"):
            return MessageIntent.UNKNOWN

        # Check patterns in order of specificity

        # Clear history - check first as it's specific
        if self._matches_any(text, self._clear_re):
            return MessageIntent.CLEAR_HISTORY

        # Help
        if self._matches_any(text, self._help_re):
            return MessageIntent.HELP

        # Report
        if self._matches_any(text, self._report_re):
            return MessageIntent.REPORT

        # Complete task
        if self._matches_any(text, self._complete_re):
            return MessageIntent.COMPLETE_TASK

        # Add task
        if self._matches_any(text, self._add_re):
            return MessageIntent.ADD_TASK

        # List tasks
        if self._matches_any(text, self._list_re):
            return MessageIntent.LIST_TASKS

        # Search - explicit search intent
        if self._matches_any(text, self._search_re):
            return MessageIntent.SEARCH

        # Greeting
        if self._matches_any(text, self._greeting_re):
            return MessageIntent.GREETING

        # Question - broad pattern, check last
        if self._matches_any(text, self._question_re):
            return MessageIntent.QUESTION

        return MessageIntent.UNKNOWN

    def _matches_any(
        self,
        text: str,
        patterns: list[re.Pattern],
    ) -> bool:
        """Check if text matches any pattern.

        Args:
            text: Text to check.
            patterns: List of compiled regex patterns.

        Returns:
            True if any pattern matches.
        """
        return any(p.search(text) for p in patterns)

    def is_question(self, text: str) -> bool:
        """Check if message is a question.

        Args:
            text: Message text.

        Returns:
            True if message appears to be a question.
        """
        if not text:
            return False
        text = text.strip()

        # Explicit question mark
        if text.endswith("?"):
            return True

        # Check question patterns
        return self._matches_any(text, self._question_re)

    def is_conversational(self, text: str) -> bool:
        """Check if message should be handled conversationally.

        Args:
            text: Message text.

        Returns:
            True if message should use conversational AI.
        """
        intent = self.detect_intent(text)
        return intent in {
            MessageIntent.QUESTION,
            MessageIntent.GREETING,
            MessageIntent.REPORT,
        }

    def extract_search_query(self, text: str) -> str | None:
        """Extract search query from natural text.

        Args:
            text: Message text.

        Returns:
            Extracted search query or None.
        """
        if not text:
            return None

        text = text.strip()

        # Remove common prefixes
        prefixes = [
            r"^(search|find|look for|looking for)\s+(for\s+)?",
            r"^(show|get|fetch)\s+(me\s+)?",
            r"^(tasks?|todos?)\s+(about|related to|with|containing|for)\s+",
        ]

        for prefix in prefixes:
            text = re.sub(prefix, "", text, flags=re.IGNORECASE).strip()

        return text if text else None

    def extract_task_number(self, text: str) -> int | None:
        """Extract task number from text.

        Args:
            text: Message text.

        Returns:
            Extracted task number or None.
        """
        if not text:
            return None

        # Look for patterns like "task 1", "#1", "number 1", just "1"
        patterns = [
            r"#(\d+)",
            r"task\s*#?(\d+)",
            r"number\s*(\d+)",
            r"^(\d+)$",
            r"\b(\d+)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return None

    def get_intent_description(self, intent: MessageIntent) -> str:
        """Get human-readable description of intent.

        Args:
            intent: MessageIntent enum value.

        Returns:
            Description string.
        """
        descriptions = {
            MessageIntent.SEARCH: "Search for tasks",
            MessageIntent.QUESTION: "Ask a question about tasks",
            MessageIntent.ADD_TASK: "Add a new task",
            MessageIntent.COMPLETE_TASK: "Mark a task as complete",
            MessageIntent.LIST_TASKS: "View task list",
            MessageIntent.REPORT: "Get task report or summary",
            MessageIntent.HELP: "Get help with commands",
            MessageIntent.GREETING: "Greeting",
            MessageIntent.CLEAR_HISTORY: "Clear conversation history",
            MessageIntent.UNKNOWN: "Unknown intent",
        }
        return descriptions.get(intent, "Unknown")
