"""User support module with reusable user logic."""

import re


class UserSupport:
    """Support class for user-related operations.

    Provides reusable logic for validating user data,
    formatting names, and normalizing emails.
    """

    # Email regex pattern (RFC 5322 simplified)
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def format_name(self, name: str) -> str:
        """Format name with proper capitalization.

        Args:
            name: Raw name string.

        Returns:
            Formatted name with title case.
        """
        return name.strip().title()

    def normalize_email(self, email: str) -> str:
        """Normalize email address to lowercase.

        Args:
            email: Raw email string.

        Returns:
            Normalized email in lowercase.
        """
        return email.strip().lower()

    def validate_name(self, name: str) -> tuple[bool, str | None]:
        """Validate name meets business rules.

        Args:
            name: Name to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        if not name:
            return False, "Name cannot be empty"

        stripped = name.strip()
        if len(stripped) == 0:
            return False, "Name cannot be only whitespace"

        if len(stripped) > 100:
            return False, "Name exceeds maximum length of 100 characters"

        if len(stripped) < 2:
            return False, "Name must be at least 2 characters"

        return True, None

    def validate_email(self, email: str) -> tuple[bool, str | None]:
        """Validate email meets business rules.

        Args:
            email: Email to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        if not email:
            return False, "Email cannot be empty"

        stripped = email.strip()
        if len(stripped) == 0:
            return False, "Email cannot be only whitespace"

        if len(stripped) > 255:
            return False, "Email exceeds maximum length of 255 characters"

        if not self.EMAIL_PATTERN.match(stripped):
            return False, "Invalid email format"

        return True, None
