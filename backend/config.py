"""Application settings loaded from environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Shared application configuration for API, backend, and batch jobs."""

    model_config = SettingsConfigDict(
        env_file=(
            REPO_ROOT / ".env",
            REPO_ROOT / "api" / ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore")
    db_host: str = Field(default="localhost", description="Database host")
    db_user: str = Field(default="root", description="Database user")
    db_password: SecretStr = Field(
        ...,
        description="Database password (required environment variable)")
    db_name: str = Field(default="ekstrabet", description="Database name")
    db_port: int = Field(default=3306, description="Database port")
    api_title: str = Field(
        default="EkstraBet Teams API",
        description="API title")
    api_description: str = Field(
        default="API for managing team data in the EkstraBet system",
        description="API description")
    api_version: str = Field(default="1.0.0", description="API version")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    default_page_size: int = Field(
        default=50,
        description="Default pagination page size")
    max_page_size: int = Field(
        default=500,
        description="Maximum pagination page size")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string")
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["*"],
        description="Allowed CORS origins")
    cors_methods: Annotated[list[str], NoDecode] = Field(
        default=["GET", "POST", "PUT", "DELETE"],
        description="Allowed CORS methods")
    frontend_origin: str = Field(
        default="http://localhost:3000",
        description="Primary frontend origin for CORS")
    secret_key: SecretStr = Field(
        ...,
        description="Secret key (required environment variable)")
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token lifetime in minutes")
    auth_enabled: bool = Field(
        default=True,
        description="Whether API and UI require authentication")
    auth_cookie_name: str = Field(
        default="ekstrabet_token",
        description="HttpOnly cookie name for the JWT session")
    auth_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm")
    cache_ttl: int = Field(
        default=300,
        description="Cache TTL in seconds")
    enable_cache: bool = Field(
        default=False,
        description="Whether response caching is enabled")

    @field_validator("cors_origins", "cors_methods", mode="before")
    @classmethod
    def parse_list_field(cls, value: Any) -> list[str]:
        """Parse comma-separated or JSON list values from .env."""
        if isinstance(value, list):
            return value
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            return [str(item) for item in parsed]
        if stripped == "*":
            return ["*"]
        return [item.strip() for item in stripped.split(",") if item.strip()]


class _LazySettings:
    """Defer settings validation until the first attribute access."""

    def __getattr__(self, name: str) -> object:
        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        return repr(get_settings())


@lru_cache
def get_settings() -> Settings:
    """Zwraca buforowane ustawienia aplikacji."""
    return Settings()


settings = _LazySettings()


def get_database_url() -> str:
    """Return SQLAlchemy-style MySQL connection URL."""
    current = get_settings()
    password = current.db_password.get_secret_value()
    return (
        f"mysql+pymysql://{current.db_user}:{password}"
        f"@{current.db_host}:{current.db_port}/{current.db_name}"
    )


def get_database_config() -> dict[str, Any]:
    """Return mysql-connector connection parameters."""
    current = get_settings()
    return {
        "host": current.db_host,
        "user": current.db_user,
        "password": current.db_password.get_secret_value(),
        "database": current.db_name,
        "port": current.db_port,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }
