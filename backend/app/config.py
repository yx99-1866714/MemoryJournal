from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://memoryjournal:memoryjournal_dev@localhost:5432/memoryjournal"
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
