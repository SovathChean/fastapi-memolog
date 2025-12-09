"""Field mapper utility for Pydantic schema to dict conversion."""

from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel

from app.common.exceptions import ValidationError


class FieldMapper:
    """Maps Pydantic schema fields to dict with transformers and validators.

    Automatically extracts non-None fields and supports:
    - Custom transformers per field
    - Custom validators per field (sync only)
    - Method chaining for fluent API

    Example:
        mapper = (
            FieldMapper(user_update_schema)
            .validate("name", validate_name)
            .validate("email", validate_email)
            .transform("name", format_name)
            .transform("email", normalize_email)
        )
        update_data = mapper.to_dict()
    """

    def __init__(self, schema: BaseModel, exclude_none: bool = True) -> None:
        """Initialize mapper with Pydantic schema.

        Args:
            schema: Pydantic model instance to map.
            exclude_none: If True, excludes None values from mapping.
        """
        self._data: dict[str, Any] = schema.model_dump(exclude_none=exclude_none)
        self._transformers: dict[str, Callable[[Any], Any]] = {}
        self._validators: dict[str, Callable[[Any], tuple[bool, str]]] = {}

    def transform(self, field: str, transformer: Callable[[Any], Any]) -> Self:
        """Add transformer function for a field.

        Transformers are applied after validation passes.
        Only applied if the field exists in the data.

        Args:
            field: Field name to transform.
            transformer: Function that takes field value and returns transformed value.

        Returns:
            Self for method chaining.
        """
        self._transformers[field] = transformer
        return self

    def validate(
        self, field: str, validator: Callable[[Any], tuple[bool, str]]
    ) -> Self:
        """Add validator function for a field.

        Validators run before transformers.
        Only applied if the field exists in the data.

        Args:
            field: Field name to validate.
            validator: Function that returns (is_valid, error_message) tuple.

        Returns:
            Self for method chaining.
        """
        self._validators[field] = validator
        return self

    def to_dict(self) -> dict[str, Any]:
        """Apply validators and transformers, return final dict.

        Raises:
            ValidationError: If any validator returns False.

        Returns:
            Dict with validated and transformed field values.
        """
        result: dict[str, Any] = {}

        for key, value in self._data.items():
            # Run validator if exists for this field
            if key in self._validators:
                is_valid, error = self._validators[key](value)
                if not is_valid:
                    raise ValidationError(error)

            # Apply transformer if exists for this field
            if key in self._transformers:
                value = self._transformers[key](value)

            result[key] = value

        return result

    def has_field(self, field: str) -> bool:
        """Check if field exists in the data.

        Args:
            field: Field name to check.

        Returns:
            True if field exists, False otherwise.
        """
        return field in self._data

    def get_fields(self) -> list[str]:
        """Get list of all field names in the data.

        Returns:
            List of field names.
        """
        return list(self._data.keys())

    def exclude(self, *fields: str) -> Self:
        """Exclude specific fields from the mapping.

        Args:
            *fields: Field names to exclude.

        Returns:
            Self for method chaining.
        """
        for field in fields:
            self._data.pop(field, None)
        return self

    def only(self, *fields: str) -> Self:
        """Keep only specific fields in the mapping.

        Args:
            *fields: Field names to keep.

        Returns:
            Self for method chaining.
        """
        self._data = {k: v for k, v in self._data.items() if k in fields}
        return self
