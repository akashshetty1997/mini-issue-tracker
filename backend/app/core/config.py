"""Environment-driven settings. Fixed values live in ``app.core.constants``."""

from functools import lru_cache
from typing import Annotated, Literal

from limits import parse
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.constants import READ_RATE_LIMIT, WRITE_RATE_LIMIT, RateLimitBucket


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://issues:issues@localhost:5433/issue_tracker"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800

    # Comma-separated in the environment, e.g. "http://localhost:3000,https://app.example.com"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Rate limiting. Without REDIS_URL, counters are kept in process memory (fine for a
    # single process; with several workers each one counts separately).
    rate_limit_enabled: bool = True
    redis_url: str | None = None
    read_rate_limit: str = READ_RATE_LIMIT
    write_rate_limit: str = WRITE_RATE_LIMIT

    @field_validator("read_rate_limit", "write_rate_limit")
    @classmethod
    def validate_rate_limit(cls, value: str) -> str:
        parse(value)  # raises ValueError for strings like "lots/minute"
        return value

    def rate_limit_for(self, bucket: RateLimitBucket) -> str:
        return self.read_rate_limit if bucket is RateLimitBucket.READ else self.write_rate_limit

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
