from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://memoryjournal:memoryjournal_dev@localhost:5432/memoryjournal"

    @model_validator(mode="after")
    def fix_database_url(self):
        """Convert Render's postgres:// URL to asyncpg format."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            self.DATABASE_URL = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            self.DATABASE_URL = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    # EverMemOS
    EVERMEMOS_API_URL: str = "https://api.evermemos.com"
    EVERMEMOS_API_KEY: str = ""

    # LLM (OpenRouter)
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "x-ai/grok-4-fast"

    # Logging
    VERBOSE: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
