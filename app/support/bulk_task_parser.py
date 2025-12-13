"""Bulk task parser for complex multi-line task input using OpenAI."""

import asyncio
import re
from dataclasses import dataclass, field
from functools import lru_cache

from pydantic import BaseModel, Field

from app.models.schemas.task import TaskPeriodType, TaskPriority
from app.support.langchain_support import get_langchain_support


class TaskItem(BaseModel):
    """A single task item extracted from bulk input."""

    category: str = Field(description="Task category (e.g., Work, Personal)")
    title: str = Field(description="Task title/description")
    priority: str = Field(
        default="normal",
        description="Task priority: low, normal, or high",
    )


class BulkTaskOutput(BaseModel):
    """Structured output from bulk task parsing."""

    period: str = Field(
        default="daily",
        description="Task period: daily, weekly, or monthly",
    )
    tasks: list[TaskItem] = Field(
        default_factory=list,
        description="List of tasks extracted from the input",
    )


@dataclass
class ParsedBulkTasks:
    """Result of bulk task parsing."""

    period: TaskPeriodType = TaskPeriodType.DAILY
    tasks: list[tuple[str, str, TaskPriority]] = field(default_factory=list)
    # List of (category, title, priority) tuples


class BulkTaskParser:
    """Parser for complex multi-line task input.

    Uses OpenAI to intelligently extract structured task data from
    natural language input with categories, bullet points, and nested structures.
    """

    # Patterns to detect bulk input
    BULLET_PATTERN = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)
    CATEGORY_HEADER_PATTERN = re.compile(r"^\s*\w+\s*:\s*$", re.MULTILINE)
    MULTILINE_PATTERN = re.compile(r"\n")

    def __init__(self) -> None:
        """Initialize the bulk task parser."""
        self.langchain_support = get_langchain_support()

    def is_bulk_input(self, text: str) -> bool:
        """Check if text appears to be bulk/complex task input.

        A message is considered bulk input if it contains:
        - Multiple lines AND
        - Bullet points (-, *, •) OR category headers (word:)

        Args:
            text: Input text to check.

        Returns:
            True if text appears to be bulk input.
        """
        if not text or not text.strip():
            return False

        # Must have multiple lines
        if not self.MULTILINE_PATTERN.search(text):
            return False

        # Must have bullet points OR category headers
        has_bullets = bool(self.BULLET_PATTERN.search(text))
        has_category_headers = bool(self.CATEGORY_HEADER_PATTERN.search(text))

        return has_bullets or has_category_headers

    async def parse_bulk_input(self, text: str) -> ParsedBulkTasks:
        """Parse bulk task input using OpenAI.

        Args:
            text: Raw user input with tasks.

        Returns:
            ParsedBulkTasks with period and list of tasks.
        """
        if not text or not text.strip():
            return ParsedBulkTasks()

        # Use LangChain structured output
        structured_llm = self.langchain_support.chat_model.with_structured_output(
            BulkTaskOutput
        )

        prompt = f"""Extract tasks from this input.

Rules:
1. Identify period (daily/weekly/monthly) from keywords. Default: daily.
2. Identify categories from headers ending with colon (work:, personal:)
3. Extract task titles from bullet points
4. Default category: "General"
5. Capitalize categories (work -> Work)
6. Priority: "urgent/important" -> high, "low priority" -> low, else normal

Input:
{text}

Extract all tasks with their categories and priorities."""

        try:
            result = await asyncio.to_thread(structured_llm.invoke, prompt)

            # Convert to ParsedBulkTasks
            period = self._parse_period(result.period)
            tasks = []

            for task_item in result.tasks:
                category = self._normalize_category(task_item.category)
                title = task_item.title.strip()
                priority = self._parse_priority(task_item.priority)

                if title:
                    tasks.append((category, title, priority))

            return ParsedBulkTasks(period=period, tasks=tasks)

        except Exception:
            # Fallback: try basic parsing
            return self._fallback_parse(text)

    def _parse_period(self, period_str: str) -> TaskPeriodType:
        """Parse period string to TaskPeriodType.

        Args:
            period_str: Period string (daily, weekly, monthly).

        Returns:
            TaskPeriodType enum value.
        """
        period_map = {
            "daily": TaskPeriodType.DAILY,
            "weekly": TaskPeriodType.WEEKLY,
            "monthly": TaskPeriodType.MONTHLY,
        }
        return period_map.get(period_str.lower(), TaskPeriodType.DAILY)

    def _parse_priority(self, priority_str: str) -> TaskPriority:
        """Parse priority string to TaskPriority.

        Args:
            priority_str: Priority string (low, normal, high).

        Returns:
            TaskPriority enum value.
        """
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
        }
        return priority_map.get(priority_str.lower(), TaskPriority.NORMAL)

    def _normalize_category(self, category: str) -> str:
        """Normalize category name (capitalize).

        Args:
            category: Raw category string.

        Returns:
            Capitalized category name.
        """
        if not category or not category.strip():
            return "General"
        return category.strip().title()

    def _fallback_parse(self, text: str) -> ParsedBulkTasks:
        """Fallback parsing when OpenAI fails.

        Basic regex-based parsing for bullet-pointed lists.

        Args:
            text: Input text.

        Returns:
            ParsedBulkTasks with basic extraction.
        """
        period = TaskPeriodType.DAILY
        tasks = []

        # Detect period
        text_lower = text.lower()
        if "weekly" in text_lower:
            period = TaskPeriodType.WEEKLY
        elif "monthly" in text_lower:
            period = TaskPeriodType.MONTHLY

        # Extract bullet items
        current_category = "General"
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if it's a category header (ends with :)
            if line.endswith(":") and not line.startswith("-"):
                # Remove period keywords from category
                category = line.rstrip(":")
                for kw in ["daily", "weekly", "monthly", "task", "tasks", "add"]:
                    category = re.sub(
                        rf"\b{kw}\b",
                        "",
                        category,
                        flags=re.IGNORECASE,
                    )
                category = category.strip()
                if category:
                    current_category = self._normalize_category(category)
                continue

            # Check if it's a bullet item
            bullet_match = self.BULLET_PATTERN.match(line)
            if bullet_match:
                title = line[bullet_match.end() :].strip()
                # Check if this bullet is a sub-category
                if title.endswith(":"):
                    current_category = self._normalize_category(title.rstrip(":"))
                elif title:
                    tasks.append((current_category, title, TaskPriority.NORMAL))

        return ParsedBulkTasks(period=period, tasks=tasks)


@lru_cache
def get_bulk_task_parser() -> BulkTaskParser:
    """Get cached bulk task parser instance."""
    return BulkTaskParser()
