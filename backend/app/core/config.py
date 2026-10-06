"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import List, Literal, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Core Application
    app_name: str = Field(default="Enterprise Agent Platform", alias="APP_NAME")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    debug: bool = Field(default=False, alias="DEBUG")
    version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_v1_str: str = Field(default="/api/v1", alias="API_V1_STR")

    # Network / Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # CORS
    cors_origins: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return []

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: Literal["json", "text"] = Field(default="json", alias="LOG_FORMAT")

    # Database & Connection Pooling
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_agent",
        alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, alias="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    # Security & Authentication (Phase 3)
    secret_key: str = Field(
        default="enterprise-agent-development-insecure-secret-key-change-in-prod-0987654321",
        alias="SECRET_KEY",
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""
    return Settings()
