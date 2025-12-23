"""
Application Configuration
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Job Application System"
    debug: bool = True
    sql_echo: bool = False  # Set to True to log all SQL queries (verbose)
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # Database (PostgreSQL)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "autojob"
    db_user: str = "postgres"
    db_password: str = "qweqwe123"

    # Browser Automation
    max_concurrent_browsers: int = 5
    browser_timeout: int = 300
    browser_headless: bool = False
    screenshot_on_error: bool = True

    # Storage
    storage_path: str = "./storage"
    max_resume_size_mb: int = 10

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    @property
    def database_url(self) -> str:
        """Get async PostgreSQL database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        """Get sync PostgreSQL database URL (for migrations)."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def cors_origins(self) -> list[str]:
        """Get allowed CORS origins."""
        return ["*"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
