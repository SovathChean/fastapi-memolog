"""Utility functions."""

import re
from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    """Get current UTC timestamp.

    Returns:
        Current datetime in UTC timezone.
    """
    return datetime.now(UTC)


def slugify(text: str) -> str:
    """Convert text to URL-safe slug.

    Args:
        text: Text to convert.

    Returns:
        URL-safe slug string.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length.

    Args:
        text: Text to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to append when truncated.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        snake_str: String in snake_case.

    Returns:
        String in camelCase.
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary.
        update: Dictionary to merge into base.

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
