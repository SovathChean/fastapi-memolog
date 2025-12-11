"""LangChain support module for embedding and AI operations."""

import asyncio
from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config.settings import get_settings


class LangChainSupport:
    """LangChain wrapper for embedding and AI operations.

    Drop-in replacement for EmbeddingSupport with LangChain-native implementation.
    Provides embedding generation using LangChain's OpenAIEmbeddings class
    and exposes the ChatOpenAI model for RAG operations.
    """

    def __init__(self) -> None:
        """Initialize LangChain support with OpenAI embeddings and chat model."""
        settings = get_settings()

        # Initialize OpenAI Embeddings via LangChain
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            dimensions=settings.embedding_dimension,
            openai_api_key=settings.openai_api_key,
        )

        # Initialize Chat model for RAG operations
        self.chat_model = ChatOpenAI(
            model=settings.openai_chat_model,
            temperature=settings.rag_temperature,
            max_tokens=settings.rag_max_tokens,
            openai_api_key=settings.openai_api_key,
        )

        self.dimension = settings.embedding_dimension
        self.model = settings.openai_embedding_model

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for given text.

        Args:
            text: Text to generate embedding for.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            ValueError: If text is empty.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty for embedding generation")

        # LangChain's embed_query is synchronous, wrap in asyncio
        embedding = await asyncio.to_thread(
            self.embeddings.embed_query,
            text.strip(),
        )
        return embedding

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to generate embeddings for.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        # LangChain's embed_documents is synchronous, wrap in asyncio
        embeddings = await asyncio.to_thread(
            self.embeddings.embed_documents,
            valid_texts,
        )
        return embeddings

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
def get_langchain_support() -> LangChainSupport:
    """Get cached LangChain support instance."""
    return LangChainSupport()
