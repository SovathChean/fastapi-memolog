"""Embedding support module for vector operations."""

from functools import lru_cache

from openai import AsyncOpenAI

from config.settings import get_settings


class EmbeddingSupport:
    """Support class for embedding-related operations.

    Provides functionality for generating embeddings using OpenAI API
    and preparing text for embedding generation.
    """

    def __init__(self) -> None:
        """Initialize embedding support with OpenAI client."""
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.dimension = settings.embedding_dimension

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for given text.

        Args:
            text: Text to generate embedding for.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            Exception: If embedding generation fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty for embedding generation")

        response = await self.client.embeddings.create(
            model=self.model,
            input=text.strip(),
        )
        return response.data[0].embedding

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to generate embeddings for.

        Returns:
            List of embedding vectors.

        Raises:
            Exception: If embedding generation fails.
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        response = await self.client.embeddings.create(
            model=self.model,
            input=valid_texts,
        )
        return [item.embedding for item in response.data]

    def combine_text_for_embedding(
        self,
        title: str,
        description: str | None = None,
    ) -> str:
        """Combine title and description for embedding generation.

        Args:
            title: Task title.
            description: Optional task description.

        Returns:
            Combined text suitable for embedding.
        """
        parts = [title.strip()]
        if description and description.strip():
            parts.append(description.strip())
        return ". ".join(parts)

    def validate_embedding_dimension(
        self,
        embedding: list[float],
    ) -> tuple[bool, str | None]:
        """Validate embedding has correct dimension.

        Args:
            embedding: Embedding vector to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not embedding:
            return False, "Embedding cannot be empty"

        if len(embedding) != self.dimension:
            return (
                False,
                f"Embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(embedding)}",
            )

        return True, None


@lru_cache
def get_embedding_support() -> EmbeddingSupport:
    """Get cached embedding support instance."""
    return EmbeddingSupport()
