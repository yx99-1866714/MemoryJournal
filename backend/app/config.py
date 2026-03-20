from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://memoryjournal:memoryjournal_dev@localhost:5432/memoryjournal"
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    EVERMEMOS_API_KEY: str = ""  # Phase 2

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
