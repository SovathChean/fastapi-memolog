"""Application settings using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "FastAPI Template"
    app_env: str = "development"
    debug: bool = True

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/memolog"
    )

    # Logging
    log_level: str = "INFO"

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    embedding_dimension: int = 1536

    # Telegram Bot Configuration
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""

    # Vector Search Settings
    search_top_k: int = 5

    # LangChain/RAG Settings
    rag_temperature: float = 0.7
    rag_max_tokens: int = 500
    conversation_window_size: int = 10
    search_result_context_limit: int = 5

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
